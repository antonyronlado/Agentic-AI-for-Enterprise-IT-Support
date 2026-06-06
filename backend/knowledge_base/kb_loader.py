import json
import threading
import numpy as np
import faiss
from pathlib import Path
from models.model_loader import ModelLoader

KB_PATH      = Path(__file__).parent / "it_knowledge_base.json"
INDEX_DIR    = Path(__file__).parent.parent / "faiss_index"
INDEX_PATH   = INDEX_DIR / "index.faiss"
ENTRIES_PATH = INDEX_DIR / "entries.json"
LEARNED_PATH = INDEX_DIR / "learned_entries.json"

class KnowledgeBaseLoader:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader
        self.index: faiss.IndexFlatIP | None = None
        self.entries: list[dict] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        INDEX_DIR.mkdir(exist_ok=True)

        with open(KB_PATH, "r", encoding="utf-8") as f:
            self.entries = json.load(f)

        if LEARNED_PATH.exists():
            with open(LEARNED_PATH, "r", encoding="utf-8") as f:
                learned = json.load(f)
            self.entries.extend(learned)
            print(f"[KnowledgeBase] Loaded {len(learned)} learned entries from previous sessions.")

        if INDEX_PATH.exists():
            print(f"[KnowledgeBase] Loading FAISS index from {INDEX_PATH}...")
            self.index = faiss.read_index(str(INDEX_PATH))
            print(f"[KnowledgeBase] Index loaded with {self.index.ntotal} entries.")

            if self.index.ntotal != len(self.entries):
                print("[KnowledgeBase] Entry count mismatch — rebuilding index...")
                self._build_index()
        else:
            print("[KnowledgeBase] Building FAISS index from knowledge base...")
            self._build_index()

    def _build_index(self):
        texts = [
            f"{e['title']}. {e['description']}" for e in self.entries
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

    def add_resolved_ticket(
        self,
        ticket_id: str,
        title: str,
        description: str,
        steps: list[str],
        result: str,
        category: str = "other",
    ) -> bool:
        with self._lock:
            existing_ids = {e.get("id") for e in self.entries}
            learned_id   = f"learned-{ticket_id}"
            if learned_id in existing_ids:
                return False

            new_entry = {
                "id":          learned_id,
                "title":       title,
                "category":    category,
                "description": description,
                "steps":       steps,
                "automated":   True,
                "result":      result,
                "escalationReason": None,
                "source":      "learned",
            }

            text = f"{title}. {description}"
            embedding = self.model_loader.embedder.encode(
                [text], normalize_embeddings=True
            )
            embedding = np.array(embedding, dtype=np.float32)
            self.index.add(embedding)
            self.entries.append(new_entry)

            learned: list[dict] = []
            if LEARNED_PATH.exists():
                with open(LEARNED_PATH, "r", encoding="utf-8") as f:
                    learned = json.load(f)
            learned.append(new_entry)
            with open(LEARNED_PATH, "w", encoding="utf-8") as f:
                json.dump(learned, f, indent=2)

            print(
                f"[KnowledgeBase] Learned from ticket {ticket_id}: '{title}' "
                f"(total entries: {len(self.entries)})"
            )
            return True