import io
import re
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

logger = logging.getLogger("nexusdesk.router.multimodal")

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])

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
async def upload_file(file: UploadFile = File(...)):
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 5 MB allowed.")

    filename = (file.filename or "").lower()
    content_bytes = await file.read()

    extracted_text = ""
    file_type = "unknown"

    if filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        file_type = "image"
        try:
            import pytesseract
            from PIL import Image
            pytesseract.pytesseract.tesseract_cmd = r"D:\Applications\Tesseract OCR\tesseract.exe"
            img = Image.open(io.BytesIO(content_bytes))
            extracted_text = pytesseract.image_to_string(img).strip()
            if not extracted_text:
                extracted_text = "[OCR ran but extracted no text — image may be low resolution or non-text content]"
        except ImportError:
            raise HTTPException(status_code=503, detail="OCR libraries not installed")
        except Exception as exc:
            logger.error("OCR error: %s", exc)
            raise HTTPException(status_code=422, detail=f"OCR processing failed: {str(exc)}")

    elif filename.endswith((".log", ".txt", ".csv")):
        file_type = "log"
        try:
            raw = content_bytes.decode("utf-8", errors="replace")
            extracted_text = _parse_log(raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Log parsing failed: {str(exc)}")

    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Accepted: PNG, JPG, WEBP, LOG, TXT"
        )

    errors = _extract_errors(extracted_text)
    probable_cause, confidence = _derive_cause(extracted_text, errors)

    logger.info("Multimodal upload: file_type=%s errors=%d confidence=%d", file_type, len(errors), confidence)

    return {
        "extracted_text": extracted_text[:3000],
        "detected_errors": errors,
        "probable_cause": probable_cause,
        "confidence": confidence,
        "file_type": file_type,
    }
