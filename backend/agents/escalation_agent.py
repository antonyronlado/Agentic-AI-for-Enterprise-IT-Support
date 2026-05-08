class EscalationAgent:
    RISK_SCORE_THRESHOLD     = 0.70
    LOW_CONFIDENCE_THRESHOLD = 50
    MEDIUM_CONF_THRESHOLD    = 65

    def apply(self, risk: dict, automated: bool = False) -> dict:
        risk_level       = risk.get("risk_level", risk.get("impact", "low"))
        risk_score       = risk.get("riskScore", 0)
        security_risk    = risk.get("securityRisk", False)
        compliance_check = risk.get("complianceCheck", True)
        confidence_score = risk.get("confidence_score", 100)

        reasons = []
        low_confidence = confidence_score < self.LOW_CONFIDENCE_THRESHOLD

        if risk_level == "high":
            reasons.append("High risk level — immediate admin escalation required")

        if risk_score >= self.RISK_SCORE_THRESHOLD:
            reasons.append(f"Risk score {risk_score:.0%} exceeds threshold")

        if security_risk:
            reasons.append("Security threat detected")

        if not compliance_check:
            reasons.append("Compliance check failed — regulatory review mandatory")

        if low_confidence:
            reasons.append(
                f"AI confidence score too low ({confidence_score}%) — "
                "human review required before automated action"
            )

        if (
            risk_level == "medium"
            and confidence_score < self.MEDIUM_CONF_THRESHOLD
            and not low_confidence
        ):
            reasons.append(
                f"Medium risk with insufficient confidence ({confidence_score}%) — "
                "escalating for agent review"
            )

        should_escalate = bool(reasons)

        if should_escalate or risk_level == "high":
            final_status    = "escalated"
            should_escalate = True
        elif risk_level == "low" and automated:
            final_status = "resolved"
        elif risk_level == "medium" and automated and confidence_score >= self.MEDIUM_CONF_THRESHOLD:
            final_status = "resolved"
        else:
            final_status = "in_progress"

        risk["escalate"]         = should_escalate
        risk["escalationReason"] = " | ".join(reasons) if should_escalate else None
        risk["final_status"]     = final_status
        risk["low_confidence"]   = low_confidence
        return risk
