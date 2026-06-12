"""
resolution_agent.py — Ticket resolution with tailored, entity-aware responses.

Improvements:
  - Uses kb_loader.search() with category + sub_category pre-filtering
  - Tiered match quality (strong/good/weak) drives response tone and automation
  - Tailored employee response: injects affected system, symptom verb, scope,
    filters already-tried steps, and adjusts tone to urgency
  - Admin response: includes match quality, similarity score, and BART confidence
"""

import asyncio
import re
import numpy as np
from models.model_loader import ModelLoader
from knowledge_base.kb_loader import KnowledgeBaseLoader
from agents.ticket_parser import extract_entities

# Match quality → whether auto-resolution is allowed (before escalation override)
_QUALITY_AUTO_ELIGIBLE = {"strong"}

_NO_KB_ADMIN = (
    "No knowledge base match found above similarity threshold. "
    "Manual investigation required. "
    "Recommend: review system logs, contact vendor support if applicable, "
    "and assign to a Level-2 engineer."
)


class ResolutionAgent:
    def __init__(self, model_loader: ModelLoader, kb_loader: KnowledgeBaseLoader):
        self.model_loader = model_loader
        self.kb_loader    = kb_loader

    # ------------------------------------------------------------------
    async def run(
        self,
        title:       str,
        description: str,
        analysis:    dict | None = None,
        risk:        dict | None = None,
    ) -> dict:
        query    = f"{title}. {description}"
        entities = extract_entities(title, description)

        # Prefer category/sub_category from analysis (NLP) over entities (regex)
        category     = (analysis or {}).get("suggestedCategory") or "other"
        sub_category = (analysis or {}).get("sub_category") or "general"

        loop      = asyncio.get_running_loop()
        best_match = await loop.run_in_executor(
            None,
            lambda: self.kb_loader.search(query, category=category, sub_category=sub_category),
        )

        risk_level   = (risk or {}).get("risk_level", (risk or {}).get("impact", "low"))
        escalate     = (risk or {}).get("escalate", False)
        final_status = (risk or {}).get("final_status", "in_progress")

        if best_match is None:
            return {
                "employee_response": self._no_kb_employee(title, entities, risk_level, escalate),
                "admin_response":    self._no_kb_admin(analysis, risk),
                "steps": [
                    "No matching resolution found in the knowledge base.",
                    "Please escalate to Level-2 support for manual investigation.",
                    "Attach system logs and screenshots to the ticket before escalating.",
                ],
                "automated":        False,
                "result":           "No KB match found. Manual review required.",
                "escalationReason": "No knowledge base match above similarity threshold.",
                "retrievedFrom":    None,
                "kbTitle":          None,
                "matchQuality":     None,
            }

        match_quality = best_match.get("match_quality", "weak")
        automated     = match_quality in _QUALITY_AUTO_ELIGIBLE and best_match.get("automated", False)

        # Escalation or high risk overrides automation
        if escalate or risk_level == "high":
            automated = False
        if risk and risk.get("riskScore", 0) > 0.65 and risk_level != "low":
            automated = False

        # Derive final_status from match quality if not already escalated
        if not escalate and risk_level != "high":
            if match_quality in ("strong", "good", "weak"):
                final_status = "resolved"

        return {
            "employee_response": self._build_employee_response(
                title, entities, risk_level, final_status,
                escalate, automated, best_match, match_quality,
            ),
            "admin_response": self._build_admin_response(
                best_match, analysis, risk, automated, entities,
            ),
            "steps":            best_match["steps"],
            "automated":        automated,
            "result":           best_match.get("result", "Resolution applied from knowledge base."),
            "escalationReason": best_match.get("escalationReason"),
            "retrievedFrom":    best_match.get("id"),
            "kbTitle":          best_match.get("title"),
            "matchQuality":     match_quality,
            # Authoritative status decided by resolution quality — read by orchestrator
            "_final_status":    final_status,
        }

    # ------------------------------------------------------------------
    # Employee (user-facing) response
    # ------------------------------------------------------------------
    def _build_employee_response(
        self,
        title:        str,
        entities:     dict,
        risk_level:   str,
        final_status: str,
        escalate:     bool,
        automated:    bool,
        kb:           dict,
        match_quality: str,
    ) -> str:
        steps        = kb.get("steps", [])
        sys_name     = entities.get("affected_system")
        symptom      = entities.get("symptom_verb")
        scope        = entities.get("scope", "just_me")
        urgency      = entities.get("urgency", "unknown")
        tried        = set(entities.get("tried_steps", []))

        # Filter steps the user already tried
        relevant_steps = self._filter_steps(steps, tried)

        # Build contextual intro
        if escalate or risk_level == "high":
            return self._escalated_response(title, sys_name, symptom, scope, urgency, relevant_steps)

        if automated and match_quality == "strong":
            return self._resolved_response(title, sys_name, symptom, scope, urgency, relevant_steps)

        return self._in_progress_response(title, sys_name, symptom, scope, urgency, relevant_steps, match_quality)

    # ------------------------------------------------------------------
    def _escalated_response(self, title, sys_name, symptom, scope, urgency, steps) -> str:
        sys_phrase    = f" with your **{sys_name}**" if sys_name else ""
        symptom_phrase = f" that is **{symptom.replace('_', ' ')}**" if symptom else ""
        scope_phrase  = self._scope_phrase(scope)
        urgency_line  = self._urgency_line(urgency)

        intro = (
            f"We've received your report about the issue{sys_phrase}{symptom_phrase}{scope_phrase}. "
            f"Given the severity of this situation, your ticket has been **escalated to a specialist** "
            f"who will contact you directly.{urgency_line}"
        )
        if steps:
            step_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
            return (
                f"{intro}\n\n"
                f"While you wait for a specialist, here are some preliminary steps you can try:\n{step_list}"
            )
        return intro

    def _resolved_response(self, title, sys_name, symptom, scope, urgency, steps) -> str:
        sys_phrase     = f" with your **{sys_name}**" if sys_name else ""
        symptom_phrase = f" that has been **{symptom.replace('_', ' ')}**" if symptom else ""
        urgency_line   = self._urgency_line(urgency)

        intro = (
            f"We can see the issue{sys_phrase}{symptom_phrase}. "
            f"Our AI agent has identified and applied a resolution for this.{urgency_line}"
        )
        if steps:
            step_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
            return f"{intro}\n\nHere's what was done / what you need to do:\n{step_list}"
        return intro

    def _in_progress_response(self, title, sys_name, symptom, scope, urgency, steps, match_quality) -> str:
        sys_phrase     = f" with your **{sys_name}**" if sys_name else ""
        symptom_phrase = f" that is **{symptom.replace('_', ' ')}**" if symptom else ""
        scope_phrase   = self._scope_phrase(scope)
        urgency_line   = self._urgency_line(urgency)

        if match_quality == "weak":
            confidence_note = (
                " Our system found a potentially related resolution — please review the steps carefully "
                "and let us know if they do not apply to your exact situation."
            )
        else:
            confidence_note = ""

        intro = (
            f"We've identified the issue{sys_phrase}{symptom_phrase}{scope_phrase}. "
            f"Here are the recommended resolution steps for your specific situation.{urgency_line}"
            f"{confidence_note}"
        )
        if steps:
            step_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
            return f"{intro}\n\nResolution steps:\n{step_list}"
        return intro

    def _no_kb_employee(self, title, entities, risk_level, escalate) -> str:
        sys_name   = entities.get("affected_system")
        symptom    = entities.get("symptom_verb")
        sys_phrase = f" with your **{sys_name}**" if sys_name else ""
        symptom_phrase = f" ({symptom.replace('_', ' ')})" if symptom else ""

        if escalate or risk_level == "high":
            return (
                f"We've received your report about the issue{sys_phrase}{symptom_phrase}. "
                "Due to the severity, this has been escalated to a specialist who will contact you shortly."
            )
        return (
            f"We've received your report about the issue{sys_phrase}{symptom_phrase}. "
            "Our team is reviewing this and a support specialist will reach out with next steps shortly."
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _scope_phrase(self, scope: str) -> str:
        return {
            "company":    " affecting the **entire company**",
            "department": " affecting your **department**",
            "small_team": " affecting **your team**",
            "just_me":    "",
        }.get(scope, "")

    def _urgency_line(self, urgency: str) -> str:
        return {
            "immediate": " We understand this is **urgent** and are treating it as a high priority.",
            "deadline":  " We note you have an upcoming **deadline or meeting** and are prioritising accordingly.",
            "recent":    " Since this just started, these steps should resolve it quickly.",
            "chronic":   " Since this has been ongoing for some time, please follow all steps carefully.",
            "unknown":   "",
        }.get(urgency, "")

    def _filter_steps(self, steps: list[str], tried: set[str]) -> list[str]:
        """
        Remove steps that the user has explicitly already tried.
        Maps tried_step labels to keywords found in step text.
        """
        tried_keyword_map = {
            "restart":          ["restart", "reboot", "power off", "turn off"],
            "reinstall":        ["reinstall", "re-install", "uninstall and install"],
            "cleared_cache":    ["clear cache", "delete cache", "clear cookies", "clear temp"],
            "updated_drivers":  ["update driver", "update the driver", "update graphics", "update network"],
            "changed_password": ["reset password", "change password", "new password"],
            "reset":            ["reset", "factory reset"],
            "flushed_dns":      ["flushdns", "flush dns"],
            "reconnected":      ["reconnect", "disconnect and reconnect"],
            "replugged":        ["unplug", "replug", "plug back in"],
            "ran_network_cmd":  ["ipconfig", "ping 8.8.8.8", "tracert"],
            "checked_settings": ["check settings", "verify settings", "check the settings"],
        }

        if not tried:
            return self._tailor_pronouns(steps)

        filtered = []
        for step in steps:
            step_lower = step.lower()
            already_done = False
            for tried_label in tried:
                keywords = tried_keyword_map.get(tried_label, [])
                if any(kw in step_lower for kw in keywords):
                    already_done = True
                    break
            if not already_done:
                filtered.append(step)

        # If all steps are filtered (user tried everything), return original
        result = filtered if filtered else steps
        return self._tailor_pronouns(result)

    def _tailor_pronouns(self, steps: list[str]) -> list[str]:
        """Reword admin-perspective steps to user-perspective."""
        tailored = []
        for step in steps:
            s = step
            s = re.sub(r'(?i)\buser\'s\b',         'your',              s)
            s = re.sub(r'(?i)\bthe user\b',         'you',               s)
            s = re.sub(r'(?i)\buser identity\b',    'your identity',     s)
            s = re.sub(r'(?i)\bfor the user\b',     'for you',           s)
            s = re.sub(r'(?i)\bnotify user\b',      'you will be notified', s)
            s = re.sub(r'(?i)\bsend the user\b',    'you will receive',  s)
            s = re.sub(r'(?i)\bguide the user\b',   'follow these steps', s)
            s = re.sub(r'(?i)\bask the user\b',     'please',            s)
            s = re.sub(r'(?i)\bAdmin:\s*',          'An IT admin will ', s)
            s = re.sub(r'(?i)\bselect user\b',      'select your account', s)
            s = re.sub(r'\s+', ' ', s).strip()
            tailored.append(s)
        return tailored

    # ------------------------------------------------------------------
    # Admin (internal) response
    # ------------------------------------------------------------------
    def _build_admin_response(
        self,
        kb:       dict,
        analysis: dict | None,
        risk:     dict | None,
        automated: bool,
        entities: dict,
    ) -> str:
        sections = []

        # --- NLP Analysis ---
        if analysis:
            intent    = analysis.get("intent", "N/A")
            category  = analysis.get("suggestedCategory", "N/A")
            sub_cat   = analysis.get("sub_category", "N/A")
            priority  = analysis.get("suggestedPriority", "N/A")
            conf      = round(analysis.get("confidenceScore", 0) * 100)
            bart_conf = analysis.get("_bart_confidence")
            bart_str  = f" | BART Confidence: {round(bart_conf * 100)}%" if bart_conf else ""
            sections.append(
                f"[NLP ANALYSIS]\n"
                f"Detected Intent: {intent}\n"
                f"Category: {category} → Sub-Category: {sub_cat} | Priority: {priority} | "
                f"Confidence: {conf}%{bart_str}"
            )

        # --- Entity extraction summary ---
        sys_name   = entities.get("affected_system", "N/A")
        symptom    = entities.get("symptom_verb", "N/A")
        scope      = entities.get("scope", "N/A")
        urgency    = entities.get("urgency", "N/A")
        tried      = entities.get("tried_steps", [])
        err_codes  = entities.get("error_codes", [])

        sections.append(
            f"[TICKET ENTITIES]\n"
            f"Affected System: {sys_name} | Symptom: {symptom} | "
            f"Scope: {scope} | Urgency: {urgency}\n"
            + (f"Error Codes Detected: {', '.join(err_codes)}\n" if err_codes else "")
            + (f"Already Tried: {', '.join(tried)}" if tried else "No prior steps mentioned")
        )

        # --- Risk Assessment ---
        if risk:
            risk_level  = risk.get("risk_level", risk.get("impact", "N/A"))
            conf_score  = risk.get("confidence_score", "N/A")
            risk_score  = risk.get("riskScore", 0)
            sec_risk    = "YES — IMMEDIATE ATTENTION REQUIRED" if risk.get("securityRisk") else "No"
            compliance  = "FAILED — Regulatory review required" if not risk.get("complianceCheck", True) else "Passed"
            notes       = risk.get("notes", "")
            esc         = risk.get("escalate", False)
            esc_reason  = risk.get("escalationReason", "")
            sections.append(
                f"[RISK ASSESSMENT]\n"
                f"Risk Level: {risk_level.upper()} | Raw Score: {round(risk_score * 100)}% | "
                f"Confidence: {conf_score}%\n"
                f"Security Risk: {sec_risk}\n"
                f"Compliance: {compliance}\n"
                f"Scope: {risk.get('scope', 'N/A')} | Urgency: {risk.get('urgency', 'N/A')}\n"
                f"Notes: {notes}"
                + (f"\nEscalation Triggered: YES — {esc_reason}" if esc else "")
            )

        # --- Resolution Path ---
        kb_title      = kb.get("title", "Unknown")
        kb_result     = kb.get("result", "")
        match_quality = kb.get("match_quality", "N/A")
        similarity    = kb.get("similarity_score", 0)
        sub_cat_kb    = kb.get("sub_category", "N/A")
        steps_str     = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(kb.get("steps", [])))
        sections.append(
            f"[RESOLUTION PATH]\n"
            f"Source: {kb_title} (sub_category: {sub_cat_kb})\n"
            f"Match Quality: {match_quality.upper()} | Similarity Score: {round(similarity * 100)}%\n"
            f"Automated: {'Yes' if automated else 'No — manual agent action required'}\n"
            f"Recommended Steps:\n{steps_str}"
            + (f"\nExpected Result: {kb_result}" if kb_result else "")
        )

        # --- Recommended Actions ---
        actions = self._recommend_actions(risk, automated, match_quality)
        if actions:
            sections.append(f"[RECOMMENDED ACTIONS]\n{actions}")

        return "\n\n".join(sections)

    def _no_kb_admin(self, analysis: dict | None, risk: dict | None) -> str:
        sections = []
        if analysis:
            sections.append(
                f"[NLP ANALYSIS]\nDetected Intent: {analysis.get('intent', 'N/A')}\n"
                f"Category: {analysis.get('suggestedCategory','N/A')} → "
                f"Sub-Category: {analysis.get('sub_category','N/A')} | "
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

    def _recommend_actions(self, risk: dict | None, automated: bool, match_quality: str) -> str:
        if not risk:
            return ""
        risk_level = risk.get("risk_level", risk.get("impact", "low"))
        actions    = []
        if risk_level == "high" or risk.get("escalate"):
            actions.append("1. Assign to Level-3 engineer immediately.")
            actions.append("2. Notify IT Security team if securityRisk is active.")
            actions.append("3. Do NOT share resolution steps with user until admin approval.")
            actions.append("4. Document all findings for compliance audit trail.")
        elif risk_level == "medium" or match_quality == "weak":
            actions.append("1. Review KB steps for applicability before sending to user.")
            actions.append("2. Monitor ticket for recurrence within 48 hours.")
            actions.append("3. Escalate if not resolved within SLA window.")
            if match_quality == "weak":
                actions.append("4. NOTE: KB match quality is WEAK — manually verify the resolution steps apply to this ticket.")
        else:
            if automated:
                actions.append("1. KB resolution auto-applied (strong match). Verify system confirms success.")
                actions.append("2. Close ticket if user confirms resolution within 24 hours.")
            else:
                actions.append("1. Send KB steps to user and await confirmation.")
                actions.append("2. Close ticket upon user confirmation.")
        return "\n".join(actions)