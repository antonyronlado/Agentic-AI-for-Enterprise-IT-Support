import json
import numpy as np
import faiss
from pathlib import Path
from models.model_loader import ModelLoader

KB_PATH = Path(__file__).parent / "it_knowledge_base.json"
INDEX_DIR = Path(__file__).parent.parent / "faiss_index"
INDEX_PATH = INDEX_DIR / "index.faiss"
ENTRIES_PATH = INDEX_DIR / "entries.json"


class KnowledgeBaseLoader:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader
        self.index: faiss.IndexFlatIP | None = None
        self.entries: list[dict] = []
        self._load()

    def _load(self):
        INDEX_DIR.mkdir(exist_ok=True)

        with open(KB_PATH, "r", encoding="utf-8") as f:
            self.entries = json.load(f)

        if INDEX_PATH.exists():
            print(f"[KnowledgeBase] Loading FAISS index from {INDEX_PATH}...")
            self.index = faiss.read_index(str(INDEX_PATH))
            print(f"[KnowledgeBase] Index loaded with {self.index.ntotal} entries.")
        else:
            print("[KnowledgeBase] Building FAISS index from knowledge base...")
            self._build_index()

    def _build_index(self):
        texts = [
            f"{entry['title']}. {entry['description']}" for entry in self.entries
        ]
        embeddings = self.model_loader.embedder.encode(
            texts, normalize_embeddings=True, show_progress_bar=True
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        faiss.write_index(self.index, str(INDEX_PATH))
        with open(ENTRIES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)

        print(
            f"[KnowledgeBase] Indexed {len(self.entries)} entries. "
            f"Saved to {INDEX_PATH}"
        )
