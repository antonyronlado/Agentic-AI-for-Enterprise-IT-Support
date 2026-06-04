import os
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
HF_CACHE_DIR = PROJECT_ROOT / "hf_cache"
HF_CACHE_DIR.mkdir(exist_ok=True)

os.environ["HF_HOME"]                    = str(HF_CACHE_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"]     = str(HF_CACHE_DIR / "hub")
os.environ["TRANSFORMERS_CACHE"]        = str(HF_CACHE_DIR / "hub")
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(HF_CACHE_DIR / "sentence_transformers")

print(f"[Config] HF cache -> {HF_CACHE_DIR}")

# ── Environment variable documentation ────────────────────────────────────
# Copy these to your .env file and customise for your environment:
#
#   MONGO_URI        = mongodb://localhost:27017/agentic_ai
#   ALLOWED_ORIGINS  = http://localhost:5173,https://your-production-domain.com
#   TESSERACT_CMD    = /usr/bin/tesseract          (Linux)
#                    = C:\Program Files\Tesseract-OCR\tesseract.exe  (Windows)
