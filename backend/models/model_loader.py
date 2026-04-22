from pathlib import Path
from huggingface_hub import snapshot_download
from transformers import pipeline
from sentence_transformers import SentenceTransformer

_CACHE_DIR = Path(__file__).parent.parent.parent / "hf_cache"
_MINILM_DIR = _CACHE_DIR / "all-MiniLM-L6-v2"
_BART_DIR = _CACHE_DIR / "bart-large-mnli"
_CACHE_DIR.mkdir(exist_ok=True)


def _ensure_minilm() -> str:
    if not (_MINILM_DIR / "config.json").exists():
        snapshot_download(
            repo_id="sentence-transformers/all-MiniLM-L6-v2",
            local_dir=str(_MINILM_DIR),
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
        )
    return str(_MINILM_DIR)


def _ensure_bart() -> str:
    if not (_BART_DIR / "config.json").exists():
        snapshot_download(
            repo_id="facebook/bart-large-mnli",
            local_dir=str(_BART_DIR),
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*", "*.ot"],
        )
    return str(_BART_DIR)


class ModelLoader:
    def __init__(self):
        self._classifier = None
        self._embedder = None

    @property
    def classifier(self):
        if self._classifier is None:
            model_path = _ensure_bart()
            self._classifier = pipeline(
                "zero-shot-classification",
                model=model_path,
                device=-1,
            )
        return self._classifier

    @property
    def embedder(self):
        if self._embedder is None:
            model_path = _ensure_minilm()
            self._embedder = SentenceTransformer(model_path)
        return self._embedder
