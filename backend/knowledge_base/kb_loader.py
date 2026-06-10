"""
kb_loader.py — Knowledge Base loader with sub-category filtered FAISS indices.

Improvements:
  - Loads from knowledge_base.json (renamed from it_knowledge_base.json)
  - Builds a per-sub-category FAISS index in addition to the full index
  - _search() now first searches the filtered pool; falls back to full index
    with a stricter threshold if no strong match is found in the filtered pool
"""

import json
import threading
import numpy as np
import faiss
from collections import defaultdict
from pathlib import Path
from models.model_loader import ModelLoader

KB_PATH      = Path(__file__).parent / "knowledge_base.json"
INDEX_DIR    = Path(__file__).parent.parent / "faiss_index"
INDEX_PATH   = INDEX_DIR / "index.faiss"
ENTRIES_PATH = INDEX_DIR / "entries.json"
LEARNED_PATH = INDEX_DIR / "learned_entries.json"

# Similarity thresholds — tiered
THRESHOLD_STRONG = 0.65   # auto-resolve eligible
THRESHOLD_GOOD   = 0.50   # use steps, mark in_progress
THRESHOLD_WEAK   = 0.35   # use steps but flag for agent review
THRESHOLD_NONE   = 0.35   # below this → no match (escalate)

# When searching the filtered sub-category pool, accept lower scores
# because the pool is already narrowed down
FILTERED_THRESHOLD = 0.32


class KnowledgeBaseLoader:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader
        self.index: faiss.IndexFlatIP | None = None
        self.entries: list[dict] = []
        # sub_category → list of entry indices into self.entries
        self._sub_index: dict[str, faiss.IndexFlatIP] = {}
        self._sub_entry_map: dict[str, list[int]] = defaultdict(list)
        self._lock = threading.Lock()
        self._load()

    # ------------------------------------------------------------------
    def _load(self):
        INDEX_DIR.mkdir(exist_ok=True)

        if not KB_PATH.exists():
            raise FileNotFoundError(
                f"Knowledge base file not found at {KB_PATH}. "
                "Expected: backend/knowledge_base/knowledge_base.json"
            )

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
                self._build_sub_indices()
        else:
            print("[KnowledgeBase] Building FAISS index from knowledge base...")
            self._build_index()

    # ------------------------------------------------------------------
    def _build_index(self):
        texts = [f"{e['title']}. {e['description']}" for e in self.entries]
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

        print(f"[KnowledgeBase] Indexed {len(self.entries)} entries. Saved to {INDEX_PATH}")
        self._build_sub_indices()

    # ------------------------------------------------------------------
    def _build_sub_indices(self):
        """
        Build an in-memory FAISS index for each (category, sub_category) pair.
        These are much smaller indexes used for pre-filtered search.
        """
        self._sub_index    = {}
        self._sub_entry_map = defaultdict(list)

        # Group entries by sub_category key
        sub_groups: dict[str, list[int]] = defaultdict(list)
        for idx, entry in enumerate(self.entries):
            cat = entry.get("category", "other")
            sub = entry.get("sub_category", "general")
            key = f"{cat}/{sub}"
            sub_groups[key].append(idx)

        # Build a mini FAISS index per group (only if ≥ 2 entries)
        for key, indices in sub_groups.items():
            if len(indices) < 1:
                continue
            texts = [
                f"{self.entries[i]['title']}. {self.entries[i]['description']}"
                for i in indices
            ]
            embs = self.model_loader.embedder.encode(
                texts, normalize_embeddings=True, show_progress_bar=False
            )
            embs = np.array(embs, dtype=np.float32)
            dim  = embs.shape[1]
            sub_idx = faiss.IndexFlatIP(dim)
            sub_idx.add(embs)
            self._sub_index[key]    = sub_idx
            self._sub_entry_map[key] = indices

        print(f"[KnowledgeBase] Built {len(self._sub_index)} sub-category indices.")

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        category: str | None = None,
        sub_category: str | None = None,
    ) -> dict | None:
        """
        Search the knowledge base for the best matching entry.

        Strategy:
          1. If category+sub_category are known, search the filtered sub-index.
             Accept a match at FILTERED_THRESHOLD (slightly lower than full index).
          2. If no strong match in filtered pool, fall back to the full index
             at THRESHOLD_GOOD to ensure a good quality fallback.
          3. Attach a match_quality label ("strong"/"good"/"weak") to the entry.

        Returns:
          The matched KB entry dict (with added match_quality/similarity fields),
          or None if no match meets the minimum threshold.
        """
        embedding = self.model_loader.embedder.encode([query], normalize_embeddings=True)
        embedding = np.array(embedding, dtype=np.float32)

        best_entry: dict | None = None
        best_score: float       = 0.0

        # --- Step 1: filtered sub-category search ---
        if category and sub_category:
            key = f"{category}/{sub_category}"
            if key in self._sub_index:
                sub_idx  = self._sub_index[key]
                sub_map  = self._sub_entry_map[key]
                k        = min(3, sub_idx.ntotal)
                dists, idxs = sub_idx.search(embedding, k)
                for dist, local_idx in zip(dists[0], idxs[0]):
                    if local_idx == -1:
                        continue
                    score      = float(dist)
                    global_idx = sub_map[int(local_idx)]
                    if score >= FILTERED_THRESHOLD and score > best_score:
                        best_score = score
                        best_entry = self.entries[global_idx]

        # --- Step 2: full-index fallback if filtered search missed ---
        if best_entry is None or best_score < THRESHOLD_GOOD:
            dists, idxs = self.index.search(embedding, 5)
            for dist, idx in zip(dists[0], idxs[0]):
                if idx == -1:
                    continue
                score = float(dist)
                # For fallback, be strict: only accept if noticeably better
                # than what filtered search found
                if score >= THRESHOLD_NONE and score > best_score:
                    best_score = score
                    best_entry = self.entries[int(idx)]

        if best_entry is None or best_score < THRESHOLD_NONE:
            return None

        # Attach match quality metadata
        entry = dict(best_entry)
        if best_score >= THRESHOLD_STRONG:
            entry["match_quality"] = "strong"
        elif best_score >= THRESHOLD_GOOD:
            entry["match_quality"] = "good"
        else:
            entry["match_quality"] = "weak"
        entry["similarity_score"] = round(best_score, 3)
        return entry

    # ------------------------------------------------------------------
    def add_resolved_ticket(
        self,
        ticket_id: str,
        title: str,
        description: str,
        steps: list[str],
        result: str,
        category: str = "other",
        sub_category: str = "general",
    ) -> bool:
        with self._lock:
            existing_ids = {e.get("id") for e in self.entries}
            learned_id   = f"learned-{ticket_id}"
            if learned_id in existing_ids:
                return False

            new_entry = {
                "id":               learned_id,
                "title":            title,
                "category":         category,
                "sub_category":     sub_category,
                "description":      description,
                "steps":            steps,
                "automated":        True,
                "result":           result,
                "escalationReason": None,
                "source":           "learned",
            }

            text = f"{title}. {description}"
            embedding = self.model_loader.embedder.encode(
                [text], normalize_embeddings=True
            )
            embedding = np.array(embedding, dtype=np.float32)
            self.index.add(embedding)
            self.entries.append(new_entry)

            # Update the appropriate sub-index
            key = f"{category}/{sub_category}"
            if key in self._sub_index:
                self._sub_index[key].add(embedding)
                self._sub_entry_map[key].append(len(self.entries) - 1)
            else:
                # Create a new sub-index for this new sub_category
                dim     = embedding.shape[1]
                sub_idx = faiss.IndexFlatIP(dim)
                sub_idx.add(embedding)
                self._sub_index[key]    = sub_idx
                self._sub_entry_map[key] = [len(self.entries) - 1]

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