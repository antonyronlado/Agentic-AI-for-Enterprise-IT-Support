import logging
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger("nexusdesk.services.kb")


def _extract_tags(title: str, description: str, category: str) -> list[str]:
    tags = [category]
    stop_words = {
        "the", "a", "an", "is", "in", "on", "at", "to", "for", "of",
        "and", "or", "but", "not", "with", "this", "that", "it", "my",
        "our", "can", "we", "i", "me", "be", "are", "was", "were"
    }
    words = f"{title} {description}".lower().split()
    seen = set(tags)
    for w in words:
        w = w.strip(".,;:!?\"'()")
        if len(w) > 4 and w not in stop_words and w not in seen:
            tags.append(w)
            seen.add(w)
        if len(tags) >= 8:
            break
    return tags


class KBService:
    def __init__(self, model_loader, kb_loader):
        self.model_loader = model_loader
        self.kb_loader = kb_loader

    async def generate_from_ticket(self, ticket: dict, db) -> dict | None:
        resolution = ticket.get("resolution") or {}
        steps = resolution.get("steps") or []
        if not steps:
            return None

        title = ticket.get("title", "")
        description = ticket.get("description", "")
        category = ticket.get("category", "other")
        ticket_id = str(ticket.get("_id", ""))

        existing = await db.kb_articles.find_one({"source_ticket_id": ticket_id})
        if existing:
            return existing

        tags = _extract_tags(title, description, category)

        related = self._find_related(f"{title}. {description}", ticket_id)

        now = int(datetime.now().timestamp() * 1000)
        article = {
            "_id": ObjectId(),
            "title": f"[{category.upper()}] {title}",
            "problem_statement": description[:500],
            "solution_steps": steps,
            "tags": tags,
            "related_ticket_ids": related,
            "source_ticket_id": ticket_id,
            "effectiveness_score": None,
            "positive_feedback": 0,
            "negative_feedback": 0,
            "created_at": now,
            "updated_at": now,
        }

        await db.kb_articles.insert_one(article)
        logger.info("KBService: generated article '%s' from ticket %s", article["title"], ticket_id)
        return article

    def _find_related(self, query: str, exclude_id: str) -> list[str]:
        import numpy as np
        try:
            emb = self.model_loader.embedder.encode([query], normalize_embeddings=True)
            emb = np.array(emb, dtype=np.float32)
            distances, indices = self.kb_loader.index.search(emb, 5)
            related = []
            for score, idx in zip(distances[0], indices[0]):
                if idx == -1 or score < 0.4:
                    continue
                entry = self.kb_loader.entries[int(idx)]
                eid = entry.get("id", "")
                if eid and f"learned-{exclude_id}" not in eid:
                    related.append(eid)
                if len(related) >= 3:
                    break
            return related
        except Exception:
            return []
