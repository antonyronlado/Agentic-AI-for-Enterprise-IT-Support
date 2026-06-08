import io
import os
import re
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from dotenv import load_dotenv

load_dotenv()

from auth_deps import require_auth

logger = logging.getLogger("nexusdesk.router.multimodal")

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])

_TESSERACT_DEFAULT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"D:\Applications\Tesseract OCR\tesseract.exe",
    "tesseract",
]


def _resolve_tesseract_path() -> str | None:
    # Re-read env var every call so .env changes are picked up without restart
    env_cmd = os.getenv("TESSERACT_CMD", "").strip()
    candidates = ([env_cmd] if env_cmd else []) + _TESSERACT_DEFAULT_CANDIDATES
    for candidate in candidates:
        if not candidate:
            continue
        if candidate == "tesseract" or os.path.isfile(candidate):
            return candidate
    return None

_MAX_FILE_BYTES = 5 * 1024 * 1024

_MAGIC_SIGNATURES: dict[bytes, str] = {
    b"\x89PNG\r\n\x1a\n":  "image",
    b"\xff\xd8\xff":       "image",
    b"BM":                 "image",
    b"RIFF":               "image",
}

_ALLOWED_TEXT_EXTENSIONS = {".log", ".txt", ".csv"}
_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

def _detect_mime(content: bytes) -> str | None:

    for sig, mime in _MAGIC_SIGNATURES.items():
        if content[:len(sig)] == sig:

            if sig == b"RIFF":
                if len(content) >= 12 and content[8:12] == b"WEBP":
                    return "image"
                return None
            return mime

    return None

def _looks_like_text(content: bytes) -> bool:

    if not content:
        return False
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        pass

    printable = sum(1 for b in content[:2000] if 0x09 <= b <= 0x7E or b in (0x0A, 0x0D))
    return printable / min(len(content), 2000) > 0.90

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
    "folder in use": "File or folder is locked by another program — close the app using it and retry",
    "open in another program": "File or folder is locked by another program — close the app using it and retry",
    "can't be completed": "Windows blocked the action — a file lock or permission issue is likely",
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


_UI_NOISE_PHRASES = (
    "try again", "cancel", "fewer details", "ok", "yes", "no",
)


def _clean_ocr_line(line: str) -> str:
    return line.strip()


def _is_ui_noise_line(line: str) -> bool:
    ll = line.lower().strip()
    if not ll:
        return True
    if ll.startswith("date created"):
        return True
    if ll in {"try again", "cancel", "ok", "yes", "no"}:
        return True
    if "try again" in ll and "cancel" in ll:
        return True
    if any(phrase == ll for phrase in _UI_NOISE_PHRASES):
        return True
    # Standalone folder/file label (e.g. TEST-MES) — metadata, not the error message
    if re.match(r"^[A-Z][A-Z0-9_-]{1,15}$", line.strip()):
        return True
    return False


def _clean_extracted_text(text: str) -> str:
    if not text or text.startswith("["):
        return text
    kept = [_clean_ocr_line(line) for line in text.splitlines()]
    kept = [line for line in kept if line and not _is_ui_noise_line(line)]
    return "\n\n".join(kept)


def _suggest_title(text: str, file_type: str) -> str:
    t = text.lower()
    if "folder in use" in t:
        return "Folder In Use Error"
    if "access denied" in t:
        return "Access Denied Error"

    for line in text.splitlines():
        cleaned = re.sub(r"^[^\w]+", "", line).strip()
        if len(cleaned) >= 8 and not _is_ui_noise_line(cleaned):
            if any(kw in cleaned.lower() for kw in ("error", "failed", "exception", "cannot", "can't", "unable")):
                return cleaned[:100]
    return "Screenshot issue" if file_type == "image" else "Log file issue"

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
            from PIL import Image, ImageEnhance
            from pytesseract import TesseractNotFoundError

            tesseract_path = _resolve_tesseract_path()
            if not tesseract_path:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Tesseract OCR is not installed. Install it from "
                        "https://github.com/UB-Mannheim/tesseract/wiki and set TESSERACT_CMD in backend/.env"
                    ),
                )

            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            img = Image.open(io.BytesIO(content_bytes))
            
            # --- OCR Enhancement Pipeline ---
            # 1. Convert to grayscale
            img = img.convert("L")
            # 2. Enhance contrast to make text pop against background
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Use psm 3 (Fully automatic page segmentation) 
            custom_config = r'--oem 3 --psm 3'
            extracted_text = pytesseract.image_to_string(img, config=custom_config).strip()
            if not extracted_text:
                extracted_text = (
                    "[OCR ran but extracted no text — image may be low resolution or non-text content]"
                )
        except HTTPException:
            raise
        except ImportError:
            raise HTTPException(status_code=503, detail="OCR libraries not installed")
        except TesseractNotFoundError:
            logger.error("Tesseract binary not found")
            raise HTTPException(
                status_code=503,
                detail=(
                    "Tesseract OCR binary not found. Set TESSERACT_CMD in backend/.env "
                    "(e.g. C:\\Program Files\\Tesseract-OCR\\tesseract.exe)"
                ),
            )
        except Exception as exc:
            logger.error("OCR error: %s", exc)
            raise HTTPException(status_code=422, detail="OCR processing failed. Please try a clearer image.")

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
    cleaned_extracted_text = _clean_extracted_text(extracted_text)
    suggested_title = _suggest_title(extracted_text, file_type)

    analysis = None
    try:
        from main import _analyzer
        if _analyzer and extracted_text and not extracted_text.startswith("["):
            analysis = await _analyzer.run(suggested_title, extracted_text)
    except Exception as exc:
        logger.warning("AI triage after multimodal upload failed: %s", exc)

    logger.info(
        "Multimodal upload: file_type=%s errors=%d confidence=%d analyzed=%s",
        file_type, len(errors), confidence, bool(analysis),
    )

    return {
        "extracted_text":         extracted_text[:3000],
        "cleaned_extracted_text": cleaned_extracted_text[:3000],
        "detected_errors":        errors,
        "probable_cause":         probable_cause,
        "confidence":             confidence,
        "file_type":              file_type,
        "suggested_title":        suggested_title,
        "analysis":               analysis,
    }