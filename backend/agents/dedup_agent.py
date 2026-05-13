import asyncio
import logging
import numpy as np

logger = logging.getLogger("nexusdesk.agent.dedup")

DEDUP_THRESHOLD = 0.85


class DedupAgent:
    def __init__(self, model_loader, kb_loader):
        self.model_loader = model_loader
        self.kb_loader = kb_loader

    async def check(self, title: str, description: str, db) -> dict:
        query = f"{title}. {description}"
        loop = asyncio.get_running_loop()

        open_tickets = []
        cursor = db.tickets.find(
            {"status": {"$in": ["open", "in_progress", "linked"]}},
            {"_id": 1, "title": 1, "description": 1, "userId": 1, "affected_users": 1}
        )
        async for t in cursor:
            open_tickets.append(t)

        if not open_tickets:
            return {"is_duplicate": False}

        result = await loop.run_in_executor(
            None, self._find_duplicate, query, open_tickets
        )
        return result

    def _find_duplicate(self, query: str, candidates: list) -> dict:
        query_emb = self.model_loader.embedder.encode(
            [query], normalize_embeddings=True
        )
        query_emb = np.array(query_emb, dtype=np.float32)

        texts = [
            f"{c.get('title', '')}. {c.get('description', '')}"
            for c in candidates
        ]
        cand_embs = self.model_loader.embedder.encode(
            texts, normalize_embeddings=True
        )
        cand_embs = np.array(cand_embs, dtype=np.float32)

        similarities = (cand_embs @ query_emb.T).flatten()
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        if best_score >= DEDUP_THRESHOLD:
            match = candidates[best_idx]
            logger.info(
                "Duplicate detected: similarity=%.3f canonical=%s",
                best_score, str(match["_id"])
            )
            return {
                "is_duplicate": True,
                "duplicate_of": str(match["_id"]),
                "similarity_score": round(best_score, 4),
                "confidence": round(best_score * 100),
            }

        return {"is_duplicate": False, "similarity_score": round(best_score, 4)}
