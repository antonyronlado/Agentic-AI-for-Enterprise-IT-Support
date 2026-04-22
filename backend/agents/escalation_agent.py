class EscalationAgent:
    RISK_THRESHOLD = 0.70

    def apply(self, risk: dict) -> dict:
        risk_score = risk.get("riskScore", 0)
        security_risk = risk.get("securityRisk", False)
        compliance_check = risk.get("complianceCheck", True)
        impact = risk.get("impact", "low")

        reasons = []
        if risk_score > self.RISK_THRESHOLD:
            reasons.append(f"Risk score {risk_score:.0%} exceeds threshold")
        if security_risk:
            reasons.append("Security risk detected")
        if not compliance_check:
            reasons.append("Compliance check failed")
        if impact == "high":
            reasons.append("High business impact")

        should_escalate = bool(reasons)
        risk["escalate"] = should_escalate
        risk["escalationReason"] = " | ".join(reasons) if should_escalate else None
        return risk
