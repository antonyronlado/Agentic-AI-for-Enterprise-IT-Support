import io
import os
import re
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from auth_deps import require_auth

logger = logging.getLogger("nexusdesk.router.multimodal")

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])

# ── Tesseract path — configurable via environment variable ────────────────
_TESSERACT_PATH = os.getenv(
    "TESSERACT_CMD",
    r"D:\Applications\Tesseract OCR\tesseract.exe",  # default fallback
)

# ── File constraints ──────────────────────────────────────────────────────
_MAX_FILE_BYTES = 5 * 1024 * 1024   # 5 MB

# ── Magic-byte signatures for real MIME validation ────────────────────────
_MAGIC_SIGNATURES: dict[bytes, str] = {
    b"\x89PNG\r\n\x1a\n":  "image",   # PNG
    b"\xff\xd8\xff":       "image",   # JPEG / JPG / WEBP (JPEG container)
    b"BM":                 "image",   # BMP
    b"RIFF":               "image",   # WEBP (RIFF container — needs extra check)
}

_ALLOWED_TEXT_EXTENSIONS = {".log", ".txt", ".csv"}
_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _detect_mime(content: bytes) -> str | None:
    """Return 'image' or 'text' based on magic bytes, or None if unknown/unsafe."""
    for sig, mime in _MAGIC_SIGNATURES.items():
        if content[:len(sig)] == sig:
            # Extra check for WEBP: RIFF....WEBP
            if sig == b"RIFF":
                if len(content) >= 12 and content[8:12] == b"WEBP":
                    return "image"
                return None   # RIFF but not WEBP — reject
            return mime
    # For text files we check the extension after confirming no binary magic
    return None


def _looks_like_text(content: bytes) -> bool:
    """Heuristic: if >95% of bytes are printable ASCII/UTF-8, treat as text."""
    if not content:
        return False
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        pass
    # Fallback: check proportion of printable bytes
    printable = sum(1 for b in content[:2000] if 0x09 <= b <= 0x7E or b in (0x0A, 0x0D))
    return printable / min(len(content), 2000) > 0.90


# ── Error patterns ────────────────────────────────────────────────────────
_ERROR_PATTERNS = [
    re.compile(r'\b(4\d{2}|5\d{2})\b'),
    re.compile(r'0x[0-9A-Fa-f]{4,}'),
    re.compile(r'Error\s+\w+', re.IGNORECASE),
    re.compile(r'Exception\s+\w+', re.IGNORECASE),
    re.compile(r'FAILED|CRITICAL|FATAL', re.IGNORECASE),
    re.compile(r'Event ID\s*:\s*\d+', re.IGNORECASE),
    re.compile(r'\b(errno|ERRNO)\s*[:=]\s*\d+'),
]

_CAUSE_MAP = {
    "401": "Authentication failure — credentials invalid or session expired",
    "403": "Authorisation denied — insufficient permissions",
    "404": "Resource not found — check endpoint or file path",
    "500": "Internal server error — application-level failure",
    "503": "Service unavailable — possible downtime or overload",
    "timeout": "Network or service timeout — check connectivity",
    "connection refused": "Service not listening on expected port",
    "out of memory": "Memory exhaustion — possible resource leak",
    "disk full": "Storage capacity reached — cleanup or expand volume",
    "access denied": "Permission error — check user rights",
}


def _extract_errors(text: str) -> list[str]:
    found = set()
    for pattern in _ERROR_PATTERNS:
        for match in pattern.findall(text):
            found.add(match.strip())
    return list(found)[:15]


def _derive_cause(text: str, errors: list[str]) -> tuple[str, int]:
    t = text.lower()
    for keyword, cause in _CAUSE_MAP.items():
        if keyword in t:
            return cause, 82
    if errors:
        return f"Detected {len(errors)} error indicator(s): {', '.join(errors[:3])}. Manual investigation recommended.", 65
    if len(text) > 100:
        return "Log content parsed successfully. No specific error pattern matched — review full log for anomalies.", 45
    return "Insufficient content for automated cause detection.", 30


def _parse_log(content: str) -> str:
    lines = content.splitlines()
    relevant = []
    for line in lines:
        ll = line.lower()
        if any(kw in ll for kw in ["error", "warn", "fatal", "critical", "exception", "failed", "traceback"]):
            relevant.append(line.strip())
    return "\n".join(relevant[:50]) if relevant else content[:2000]


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    _user=Depends(require_auth),
):
    if file.size and file.size > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum 5 MB allowed.")

    filename  = (file.filename or "").lower().strip()
    ext       = os.path.splitext(filename)[1]
    content_bytes = await file.read(min(file.size or _MAX_FILE_BYTES, _MAX_FILE_BYTES))

    extracted_text = ""
    file_type      = "unknown"

    # ── Image processing (magic-byte verified) ─────────────────────────
    if ext in _ALLOWED_IMAGE_EXTENSIONS:
        detected = _detect_mime(content_bytes)
        if detected != "image":
            raise HTTPException(
                status_code=415,
                detail="File content does not match the declared image extension. Upload rejected.",
            )
        file_type = "image"
        try:
            import pytesseract
            from PIL import Image
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH
            img = Image.open(io.BytesIO(content_bytes))
            extracted_text = pytesseract.image_to_string(img).strip()
            if not extracted_text:
                extracted_text = (
                    "[OCR ran but extracted no text — image may be low resolution or non-text content]"
                )
        except ImportError:
            raise HTTPException(status_code=503, detail="OCR libraries not installed")
        except Exception as exc:
            logger.error("OCR error: %s", exc)
            raise HTTPException(status_code=422, detail="OCR processing failed. Please try a clearer image.")

    # ── Text / log processing ──────────────────────────────────────────
    elif ext in _ALLOWED_TEXT_EXTENSIONS:
        if not _looks_like_text(content_bytes):
            raise HTTPException(
                status_code=415,
                detail="File does not appear to be a valid text file. Binary content detected.",
            )
        file_type = "log"
        try:
            raw = content_bytes.decode("utf-8", errors="replace")
            extracted_text = _parse_log(raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Log parsing failed.")

    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Accepted: PNG, JPG, WEBP, BMP, LOG, TXT, CSV",
        )

    errors = _extract_errors(extracted_text)
    probable_cause, confidence = _derive_cause(extracted_text, errors)

    logger.info(
        "Multimodal upload: file_type=%s errors=%d confidence=%d",
        file_type, len(errors), confidence,
    )

    return {
        "extracted_text":  extracted_text[:3000],
        "detected_errors": errors,
        "probable_cause":  probable_cause,
        "confidence":      confidence,
        "file_type":       file_type,
    }
