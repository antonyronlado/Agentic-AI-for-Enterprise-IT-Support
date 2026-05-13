import logging
from datetime import datetime

logger = logging.getLogger("nexusdesk.agent.explain")

_SENTIMENT_NEGATIVE = [
    "cannot", "broken", "failed", "error", "crash", "down", "not working",
    "urgent", "critical", "blocked", "unable", "issue", "problem", "stuck",
    "outage", "lost", "missing", "corrupted", "denied", "freeze", "hung"
]
_SENTIMENT_POSITIVE = [
    "working", "resolved", "fixed", "great", "thank", "appreciated", "restored"
]

_BUSINESS_CRITICAL_KEYWORDS = [
    "vpn", "production", "server", "database", "authentication", "login",
    "network", "firewall", "domain controller", "active directory", "email",
    "payment", "customer", "client", "outage", "sla"
]

_MULTI_USER_KEYWORDS = [
    "everyone", "team", "all users", "department", "multiple", "colleagues",
    "whole office", "entire floor", "all staff"
]


def _detect_sentiment(text: str) -> tuple[str, int]:
    t = text.lower()
    neg = sum(1 for w in _SENTIMENT_NEGATIVE if w in t)
    pos = sum(1 for w in _SENTIMENT_POSITIVE if w in t)
    if neg > pos:
        return "negative", min(100, 50 + neg * 8)
    if pos > neg:
        return "positive", min(100, 50 + pos * 8)
    return "neutral", 50


def _is_business_critical(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _BUSINESS_CRITICAL_KEYWORDS)


def _affects_multiple_users(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _MULTI_USER_KEYWORDS)


def _build_priority_explanation(analysis: dict, sentiment: str, text: str) -> tuple[list[str], int]:
    cat = analysis.get("suggestedCategory", "other")
    pri = analysis.get("suggestedPriority", "medium")
    conf = round(analysis.get("confidenceScore", 0) * 100)
    reasons = []

    reasons.append(
        f"BART zero-shot classifier assigned '{cat.upper()}' category with {pri.upper()} "
        f"priority at {conf}% confidence"
    )
    if _affects_multiple_users(text):
        reasons.append("Multiple employees affected — detected group-impact keywords")
    if sentiment == "negative":
        reasons.append("Negative sentiment signals urgency (frustration/urgency language detected)")
    if _is_business_critical(text):
        reasons.append("Business-critical infrastructure keyword detected (VPN / Auth / Network / DB)")
    if cat in ("hardware", "network"):
        reasons.append(f"Category '{cat}' historically correlates with elevated operational impact")
    if pri in ("critical", "high") and conf >= 80:
        reasons.append(f"High classifier confidence ({conf}%) reinforces {pri.upper()} priority decision")

    return reasons, conf


def _build_risk_explanation(risk: dict) -> tuple[list[str], int]:
    rl = risk.get("risk_level", "low")
    rs = round(risk.get("riskScore", 0) * 100)
    conf = risk.get("confidence_score", 60)
    reasons = []

    if risk.get("securityRisk"):
        reasons.append("Security-related keywords detected — possible authentication or access breach")
    if not risk.get("complianceCheck", True):
        reasons.append("Compliance flags triggered — potential GDPR / HIPAA / PCI DSS implications")
    if rs >= 70:
        reasons.append(f"Risk score {rs}% exceeds high-risk threshold (≥70%) — immediate attention required")
    elif rs >= 40:
        reasons.append(f"Risk score {rs}% falls in moderate-risk band (40–70%) — elevated monitoring")
    else:
        reasons.append(f"Risk score {rs}% within low-risk operational range")

    sensitivity = risk.get("dataSensitivity")
    if sensitivity and sensitivity != "none":
        reasons.append(f"Sensitive data classification: {sensitivity.upper()} — handling protocols apply")

    if not reasons:
        reasons.append(f"Risk level '{rl.upper()}' determined with {conf}% confidence via keyword signals")

    return reasons, conf


def _build_escalation_explanation(risk: dict) -> tuple[list[str], int, bool]:
    triggered = risk.get("escalate", False)
    conf = risk.get("confidence_score", 70)
    raw = risk.get("escalationReason", "")
    low_conf = risk.get("low_confidence", False)
    reasons = []

    if raw:
        reasons = [r.strip() for r in raw.split("|") if r.strip()]

    if low_conf and triggered:
        reasons.append(f"AI confidence ({conf}%) below automatic-resolution threshold — human review triggered")
    if risk.get("risk_level") == "high" and triggered:
        reasons.append("High risk classification mandates mandatory human-agent review")
    if risk.get("securityRisk") and triggered:
        reasons.append("Security risk flag triggers mandatory escalation per IT security policy")

    if not triggered:
        reasons = [
            "All automated risk thresholds passed successfully",
            f"AI confidence at {conf}% — within autonomous resolution range",
            "No compliance or security flags raised — proceeding with automated workflow",
        ]

    return reasons, conf, triggered


def _build_remediation_explanation(remediation: dict | None) -> dict | None:
    if not remediation:
        return None
    action_id = remediation.get("action_id", "")
    name = remediation.get("name", "")
    status = remediation.get("status", "")
    needs_approval = remediation.get("needs_approval", False)
    reasons = []

    reasons.append(f"CARS matched '{name}' action based on ticket category and keyword signals")
    if needs_approval:
        reasons.append("Medium-risk action gate triggered — human approval required before execution")
    else:
        reasons.append("Low-risk classification — action executed automatically within policy bounds")
    if status == "executed":
        reasons.append("Remediation completed successfully — user notified")
    elif status == "pending_approval":
        reasons.append("Awaiting administrator sign-off before proceeding")
    elif status == "rejected":
        reasons.append("Action rejected by administrator — manual resolution path selected")

    return {
        "action": name,
        "action_id": action_id,
        "status": status,
        "needs_approval": needs_approval,
        "reasons": reasons,
        "confidence": 85 if not needs_approval else 70,
    }


def _build_dedup_explanation(dedup_result: dict | None) -> dict | None:
    if not dedup_result or not dedup_result.get("is_duplicate"):
        return None
    sim = dedup_result.get("similarity_score", 0)
    conf = dedup_result.get("confidence", 0)
    canonical_id = dedup_result.get("duplicate_of", "")
    reasons = [
        f"Semantic embedding similarity of {round(sim * 100)}% detected vs canonical incident #{canonical_id[:8]}",
        f"Score exceeds deduplication threshold of 85% — ticket linked as duplicate",
        "Workaround retrieved from canonical incident's resolution context",
        "User subscribed to incident resolution updates",
    ]
    return {
        "is_duplicate": True,
        "canonical_id": canonical_id,
        "similarity_score": sim,
        "confidence": conf,
        "reasons": reasons,
    }


def _build_reasoning_trace(
    analysis: dict | None,
    risk: dict | None,
    dedup_result: dict | None,
    resolution: dict | None,
    remediation: dict | None,
    sentiment: str,
) -> list[dict]:
    now_ms = int(datetime.now().timestamp() * 1000)
    trace = []

    trace.append({
        "step": 1,
        "agent": "Preprocessor",
        "action": "Ticket text ingested, tokenized, and normalized",
        "detail": f"Sentiment detected: {sentiment.upper()}",
        "status": "completed",
    })

    if dedup_result and dedup_result.get("is_duplicate"):
        trace.append({
            "step": 2,
            "agent": "DedupAgent",
            "action": "Semantic duplicate detection via FAISS vector search",
            "detail": f"Matched canonical incident at {round(dedup_result.get('similarity_score', 0) * 100)}% similarity — ticket linked",
            "status": "completed",
        })

    if analysis:
        cat = analysis.get("suggestedCategory", "other")
        pri = analysis.get("suggestedPriority", "medium")
        conf = round(analysis.get("confidenceScore", 0) * 100)
        trace.append({
            "step": 3,
            "agent": "TicketAnalyzer (BART)",
            "action": f"Zero-shot classification → {cat.upper()} · {pri.upper()} priority",
            "detail": f"Classifier confidence: {conf}% using facebook/bart-large-mnli",
            "status": "completed",
        })

    if risk:
        rl = risk.get("risk_level", "low").upper()
        rs = round(risk.get("riskScore", 0) * 100)
        trace.append({
            "step": 4,
            "agent": "RiskAgent",
            "action": f"Risk assessment → {rl} ({rs}% risk score)",
            "detail": f"Security risk: {risk.get('securityRisk', False)} · Compliance check: {risk.get('complianceCheck', True)}",
            "status": "completed",
        })

        esc = risk.get("escalate", False)
        trace.append({
            "step": 5,
            "agent": "EscalationAgent",
            "action": f"Escalation gate evaluation → {'ESCALATED' if esc else 'PASSED'}",
            "detail": risk.get("escalationReason") or ("Human review not required — thresholds met" if not esc else "Escalated to IT agent queue"),
            "status": "completed",
        })

    if resolution:
        kb_title = resolution.get("kbTitle") or resolution.get("retrievedFrom") or "KB"
        trace.append({
            "step": 6,
            "agent": "ResolutionAgent (RAG)",
            "action": f"KB retrieval → matched '{kb_title}'",
            "detail": f"Automated: {resolution.get('automated', False)} · Steps: {len(resolution.get('steps', []))}",
            "status": "completed",
        })

    if remediation:
        trace.append({
            "step": 7,
            "agent": "CARS (RemediationAgent)",
            "action": f"Remediation action → {remediation.get('name', 'N/A')}",
            "detail": f"Status: {remediation.get('status', 'N/A')} · Needs approval: {remediation.get('needs_approval', False)}",
            "status": "completed",
        })

    trace.append({
        "step": len(trace) + 1,
        "agent": "ExplainAgent",
        "action": "Explainability report compiled from all agent outputs",
        "detail": "Confidence map generated · Reasoning trace assembled · Decision cards structured",
        "status": "completed",
    })

    return trace


class ExplainAgent:
    def build(
        self,
        title: str,
        description: str,
        analysis: dict | None,
        risk: dict | None,
        dedup_result: dict | None = None,
        resolution: dict | None = None,
        remediation: dict | None = None,
    ) -> dict:
        text = f"{title} {description}"
        sentiment, sentiment_conf = _detect_sentiment(text)

        priority_data = {"value": "MEDIUM", "reasons": [], "confidence": 60}
        if analysis:
            reasons, conf = _build_priority_explanation(analysis, sentiment, text)
            priority_data = {
                "value": analysis.get("suggestedPriority", "medium").upper(),
                "reasons": reasons,
                "confidence": conf,
            }

        risk_data = {"value": "LOW", "reasons": [], "confidence": 60}
        if risk:
            reasons, conf = _build_risk_explanation(risk)
            risk_data = {
                "value": risk.get("risk_level", "low").upper(),
                "reasons": reasons,
                "confidence": conf,
            }

        escalation_data = {"triggered": False, "reasons": [], "confidence": 70}
        if risk:
            reasons, conf, triggered = _build_escalation_explanation(risk)
            escalation_data = {
                "triggered": triggered,
                "reasons": reasons,
                "confidence": conf,
            }

        dedup_data = _build_dedup_explanation(dedup_result)
        remediation_data = _build_remediation_explanation(remediation)
        reasoning_trace = _build_reasoning_trace(
            analysis, risk, dedup_result, resolution, remediation, sentiment
        )

        confidence_map = {
            "classification": priority_data["confidence"],
            "sentiment": sentiment_conf,
            "risk_scoring": risk_data["confidence"] if risk else None,
            "escalation": escalation_data["confidence"] if risk else None,
            "deduplication": dedup_data["confidence"] if dedup_data else None,
            "kb_retrieval": round(resolution.get("score", 0.7) * 100) if resolution else None,
            "remediation": remediation_data["confidence"] if remediation_data else None,
        }

        active = [v for v in confidence_map.values() if v is not None]
        overall_confidence = round(sum(active) / len(active)) if active else 70

        logger.info(
            "ExplainAgent: overall=%d sentiment=%s escalation=%s dedup=%s",
            overall_confidence, sentiment, escalation_data["triggered"],
            dedup_data is not None,
        )

        return {
            "priority": priority_data,
            "risk": risk_data,
            "escalation": escalation_data,
            "deduplication": dedup_data,
            "remediation": remediation_data,
            "sentiment": sentiment,
            "sentiment_confidence": sentiment_conf,
            "reasoning_trace": reasoning_trace,
            "overall_ai_confidence": overall_confidence,
            "confidence_map": confidence_map,
            "business_critical": _is_business_critical(text),
            "multi_user_impact": _affects_multiple_users(text),
        }
