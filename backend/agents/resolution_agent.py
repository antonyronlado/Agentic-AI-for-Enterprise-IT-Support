import asyncio
import numpy as np
from models.model_loader import ModelLoader
from knowledge_base.kb_loader import KnowledgeBaseLoader

SIMILARITY_THRESHOLD = 0.30

_EMPLOYEE_STATUS = {
    "escalated": (
        "Your request has been escalated to our IT admin team. "
        "A specialist will contact you shortly with further guidance. "
        "No action is required from your side at this time."
    ),
    "in_progress": (
        "Your ticket is currently being reviewed by our support team. "
        "We are working on a resolution and will keep you updated."
    ),
    "resolved": (
        "Great news — your issue has been resolved automatically. "
        "Please follow the instructions below to restore normal operation."
    ),
}

_NO_KB_EMPLOYEE = (
    "Your request has been received and is under review by our support team. "
    "A specialist will reach out with next steps shortly."
)

_NO_KB_ADMIN = (
    "No knowledge base match found above the similarity threshold. "
    "Manual investigation required. "
    "Recommend: review system logs, contact vendor support if applicable, "
    "and assign to a Level-2 engineer."
)


class ResolutionAgent:
    def __init__(self, model_loader: ModelLoader, kb_loader: KnowledgeBaseLoader):
        self.model_loader = model_loader
        self.kb_loader    = kb_loader

    async def run(self, title, description, analysis=None, risk=None):
        query = f"{title}. {description}"
        loop  = asyncio.get_running_loop()
        best_match = await loop.run_in_executor(None, self._search_kb, query)

        risk_level   = (risk or {}).get("risk_level", (risk or {}).get("impact", "low"))
        escalate     = (risk or {}).get("escalate", False)
        final_status = (risk or {}).get("final_status", "in_progress")

        if best_match is None:
            return {
                "employee_response": self._build_no_kb_employee(risk_level, final_status, escalate),
                "admin_response":    self._build_no_kb_admin(analysis, risk),
                "steps":            [
                    "No matching resolution found in the knowledge base.",
                    "Please escalate to Level-2 support for manual investigation.",
                    "Attach system logs and screenshots to the ticket before escalating.",
                ],
                "automated":        False,
                "result":           "No KB match found. Manual review required.",
                "escalationReason": "No knowledge base match above similarity threshold.",
                "retrievedFrom":    None,
                "kbTitle":         None,
            }

        automated = best_match.get("automated", False)

        if escalate or risk_level == "high":
            automated = False

        if risk and risk.get("riskScore", 0) > 0.65 and risk_level != "low":
            automated = False

        return {
            "employee_response": self._build_employee_response(risk_level, final_status, escalate, automated, best_match),
            "admin_response":    self._build_admin_response(best_match, analysis, risk, automated),
            "steps":            best_match["steps"],
            "automated":        automated,
            "result":           best_match.get("result", "Resolution applied from knowledge base."),
            "escalationReason": best_match.get("escalationReason"),
            "retrievedFrom":    best_match.get("id"),
            "kbTitle":         best_match.get("title"),
        }

    def _search_kb(self, query):
        embedding = self.model_loader.embedder.encode([query], normalize_embeddings=True)
        embedding = np.array(embedding, dtype=np.float32)
        distances, indices = self.kb_loader.index.search(embedding, 3)
        if not len(indices[0]) or indices[0][0] == -1:
            return None
        best_idx   = int(indices[0][0])
        best_score = float(distances[0][0])
        if best_score < SIMILARITY_THRESHOLD:
            return None
        return self.kb_loader.entries[best_idx]

    def _build_employee_response(self, risk_level, final_status, escalate, automated, kb):
        if escalate or risk_level == "high":
            return _EMPLOYEE_STATUS["escalated"]
        if automated and risk_level == "low":
            status_msg = _EMPLOYEE_STATUS["resolved"]
        elif final_status == "resolved":
            status_msg = _EMPLOYEE_STATUS["resolved"]
        else:
            status_msg = _EMPLOYEE_STATUS["in_progress"]
        steps = kb.get("steps", [])
        if steps:
            numbered = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
            return f"{status_msg}\n\nSteps to resolve your issue:\n{numbered}"
        return status_msg

    def _build_no_kb_employee(self, risk_level, final_status, escalate):
        if escalate or risk_level == "high":
            return _EMPLOYEE_STATUS["escalated"]
        return _NO_KB_EMPLOYEE

    def _build_admin_response(self, kb, analysis, risk, automated):
        sections = []
        if analysis:
            intent   = analysis.get("intent", "N/A")
            category = analysis.get("suggestedCategory", "N/A")
            priority = analysis.get("suggestedPriority", "N/A")
            conf     = round(analysis.get("confidenceScore", 0) * 100)
            sections.append(
                f"[NLP ANALYSIS]\n"
                f"Detected Intent: {intent}\n"
                f"Category: {category} | Priority: {priority} | Confidence: {conf}%"
            )
        if risk:
            risk_level  = risk.get("risk_level", risk.get("impact", "N/A"))
            conf_score  = risk.get("confidence_score", "N/A")
            risk_score  = risk.get("riskScore", 0)
            sec_risk    = "YES — IMMEDIATE ATTENTION REQUIRED" if risk.get("securityRisk") else "No"
            compliance  = "FAILED — Regulatory review required" if not risk.get("complianceCheck", True) else "Passed"
            notes       = risk.get("notes", "")
            escalate    = risk.get("escalate", False)
            esc_reason  = risk.get("escalationReason", "")
            sections.append(
                f"[RISK ASSESSMENT]\n"
                f"Risk Level: {risk_level.upper()} | Raw Score: {round(risk_score * 100)}% | "
                f"Confidence: {conf_score}%\n"
                f"Security Risk: {sec_risk}\n"
                f"Compliance: {compliance}\n"
                f"Notes: {notes}"
                + (f"\nEscalation Triggered: YES — {esc_reason}" if escalate else "")
            )
        kb_title  = kb.get("title", "Unknown")
        kb_result = kb.get("result", "")
        steps     = kb.get("steps", [])
        steps_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        sections.append(
            f"[RESOLUTION PATH]\n"
            f"Source: {kb_title}\n"
            f"Automated: {'Yes' if automated else 'No — manual agent action required'}\n"
            f"Recommended Steps:\n{steps_str}"
            + (f"\nExpected Result: {kb_result}" if kb_result else "")
        )
        actions = self._recommend_actions(risk, automated)
        if actions:
            sections.append(f"[RECOMMENDED ACTIONS]\n{actions}")
        return "\n\n".join(sections)

    def _build_no_kb_admin(self, analysis, risk):
        sections = []
        if analysis:
            sections.append(
                f"[NLP ANALYSIS]\nDetected Intent: {analysis.get('intent', 'N/A')}\n"
                f"Category: {analysis.get('suggestedCategory','N/A')} | "
                f"Priority: {analysis.get('suggestedPriority','N/A')}"
            )
        if risk:
            risk_level = risk.get("risk_level", risk.get("impact", "N/A"))
            sections.append(
                f"[RISK ASSESSMENT]\n"
                f"Risk Level: {risk_level.upper()} | "
                f"Notes: {risk.get('notes', 'N/A')}"
            )
        sections.append(
            "[RESOLUTION PATH]\n"
            "No knowledge base match found above similarity threshold.\n"
            + _NO_KB_ADMIN
        )
        return "\n\n".join(sections)

    def _recommend_actions(self, risk, automated):
        if not risk:
            return ""
        risk_level = risk.get("risk_level", risk.get("impact", "low"))
        actions = []
        if risk_level == "high" or risk.get("escalate"):
            actions.append("1. Assign to Level-3 engineer immediately.")
            actions.append("2. Notify IT Security team if securityRisk is active.")
            actions.append("3. Do NOT share resolution steps with the user until admin approval.")
            actions.append("4. Document all findings for compliance audit trail.")
        elif risk_level == "medium":
            actions.append("1. Review the KB steps before sending to user.")
            actions.append("2. Monitor ticket for recurrence within 48 hours.")
            actions.append("3. Escalate if not resolved within SLA window.")
        else:
            if automated:
                actions.append("1. KB resolution auto-applied. Verify system confirms success.")
                actions.append("2. Close ticket if user confirms resolution within 24 hours.")
            else:
                actions.append("1. Send KB steps to user and await confirmation.")
                actions.append("2. Close ticket upon user confirmation.")
        return "\n".join(actions)
