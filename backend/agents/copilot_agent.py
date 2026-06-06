import asyncio
import logging
import numpy as np

logger = logging.getLogger("nexusdesk.agent.copilot")

class CopilotAgent:
    def __init__(self, model_loader, kb_loader):
        self.model_loader = model_loader
        self.kb_loader = kb_loader

    async def suggest(self, title: str, description: str, analysis: dict | None, risk: dict | None) -> dict:
        query = f"{title}. {description}"
        loop = asyncio.get_running_loop()
        matches = await loop.run_in_executor(None, self._search_kb_top3, query)

        if not matches:
            return self._empty_suggestions(analysis, risk)

        best_fix_conf = round(float(matches[0]["score"]) * 100)
        fix_confidences = [round(float(m["score"]) * 100) for m in matches]

        suggested_fixes = []
        for i, m in enumerate(matches):
            suggested_fixes.append({
                "source_title": m["entry"].get("title", f"KB Match {i+1}"),
                "steps": m["entry"].get("steps", []),
                "confidence": fix_confidences[i],
            })

        similar_tickets = [
            {
                "title": m["entry"].get("title"),
                "category": m["entry"].get("category"),
                "confidence": fix_confidences[i],
            }
            for i, m in enumerate(matches)
        ]

        draft = self._build_draft(matches[0]["entry"], risk)

        esc_priority = "low"
        esc_reason = "Risk profile within normal operational parameters."
        if risk:
            rl = risk.get("risk_level", "low")
            if rl == "high":
                esc_priority = "high"
                esc_reason = risk.get("escalationReason") or "High risk — immediate escalation recommended."
            elif rl == "medium":
                esc_priority = "medium"
                esc_reason = "Medium risk — review before closing."

        overall_conf = round(sum(fix_confidences) / len(fix_confidences)) if fix_confidences else 60

        logger.info("CopilotAgent: %d KB matches, overall_confidence=%d", len(matches), overall_conf)

        return {
            "suggested_fixes": suggested_fixes,
            "similar_tickets": similar_tickets,
            "draft_response": draft,
            "escalation_priority": esc_priority,
            "escalation_reason": esc_reason,
            "overall_confidence": overall_conf,
            "fix_confidences": fix_confidences,
        }

    def _search_kb_top3(self, query: str) -> list[dict]:
        embedding = self.model_loader.embedder.encode([query], normalize_embeddings=True)
        embedding = np.array(embedding, dtype=np.float32)
        distances, indices = self.kb_loader.index.search(embedding, 3)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx == -1 or score < 0.25:
                continue
            results.append({"entry": self.kb_loader.entries[int(idx)], "score": float(score)})
        return results

    def _build_draft(self, kb_entry: dict, risk: dict | None) -> str:
        steps = kb_entry.get("steps", [])
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps[:4]))
        rl = (risk or {}).get("risk_level", "low")
        if rl == "high":
            return (
                "Hi,\n\nThank you for contacting IT Support. We have reviewed your ticket and it has been "
                "escalated to our Level-2 team for immediate investigation. A specialist will be in touch "
                "with you shortly.\n\nPlease do not take any further action until contacted.\n\nIT Support Team"
            )
        intro = "Hi,\n\nThank you for reaching out. Based on similar resolved cases, here are the recommended steps:\n\n"
        outro = "\n\nPlease follow these steps and let us know if the issue persists. We are happy to assist further.\n\nIT Support Team"
        return intro + steps_text + outro

    def _empty_suggestions(self, analysis: dict | None, risk: dict | None) -> dict:
        return {
            "suggested_fixes": [],
            "similar_tickets": [],
            "draft_response": "Hi,\n\nThank you for your ticket. Our team is reviewing your request and will respond shortly.\n\nIT Support Team",
            "escalation_priority": (risk or {}).get("risk_level", "low"),
            "escalation_reason": "No KB match found — manual investigation recommended.",
            "overall_confidence": 30,
            "fix_confidences": [],
        }