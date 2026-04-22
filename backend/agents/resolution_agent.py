import asyncio
import numpy as np
from models.model_loader import ModelLoader
from knowledge_base.kb_loader import KnowledgeBaseLoader

SIMILARITY_THRESHOLD = 0.30


class ResolutionAgent:
    def __init__(self, model_loader: ModelLoader, kb_loader: KnowledgeBaseLoader):
        self.model_loader = model_loader
        self.kb_loader = kb_loader

    async def run(
        self,
        title: str,
        description: str,
        analysis: dict = None,
        risk: dict = None,
    ) -> dict:
        query = f"{title}. {description}"
        loop = asyncio.get_event_loop()

        best_match = await loop.run_in_executor(None, self._search_kb, query)

        if best_match is None:
            return {
                "steps": [
                    "No matching resolution found in the knowledge base.",
                    "Please escalate to Level-2 support for manual investigation.",
                    "Attach system logs and screenshots to the ticket before escalating.",
                ],
                "automated": False,
                "result": "No KB match found. Manual review required.",
                "escalationReason": "No knowledge base match above similarity threshold.",
                "retrievedFrom": None,
                "kbTitle": None,
            }

        automated = best_match.get("automated", False)
        if risk and risk.get("riskScore", 0) > 0.65:
            automated = False

        return {
            "steps": best_match["steps"],
            "automated": automated,
            "result": best_match.get("result", "Resolution applied from knowledge base."),
            "escalationReason": best_match.get("escalationReason"),
            "retrievedFrom": best_match.get("id"),
            "kbTitle": best_match.get("title"),
        }

    def _search_kb(self, query: str) -> dict | None:
        embedding = self.model_loader.embedder.encode(
            [query], normalize_embeddings=True
        )
        embedding = np.array(embedding, dtype=np.float32)

        distances, indices = self.kb_loader.index.search(embedding, 3)

        if not len(indices[0]) or indices[0][0] == -1:
            return None

        best_idx = int(indices[0][0])
        best_score = float(distances[0][0])

        if best_score < SIMILARITY_THRESHOLD:
            return None

        return self.kb_loader.entries[best_idx]
