import asyncio


SECURITY_KEYWORDS = [
    "malware", "ransomware", "virus", "phishing", "breach", "hack",
    "unauthorized", "admin", "root", "sudo", "privilege escalation",
    "credentials", "password leak", "data loss", "vpn bypass",
    "firewall", "suspicious activity", "intrusion", "exploit", "zero-day",
]

COMPLIANCE_KEYWORDS = [
    "gdpr", "hipaa", "pci dss", "audit", "compliance", "financial",
    "pii", "personal data", "sensitive", "confidential", "regulated", "sox",
]

CRITICAL_KEYWORDS = [
    "server down", "production down", "outage", "system crash", "critical",
    "emergency", "all users affected", "entire department", "cannot work",
    "business impact", "service unavailable",
]

PRIORITY_WEIGHTS = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}


class RiskAgent:
    def run(
        self,
        title: str,
        description: str,
        category: str = "other",
        priority: str = "medium",
    ) -> dict:
        text = f"{title} {description}".lower()

        sec_hits  = sum(1 for kw in SECURITY_KEYWORDS  if kw in text)
        comp_hits = sum(1 for kw in COMPLIANCE_KEYWORDS if kw in text)
        crit_hits = sum(1 for kw in CRITICAL_KEYWORDS   if kw in text)

        security_risk    = sec_hits > 0
        compliance_check = comp_hits == 0

        p_weight = PRIORITY_WEIGHTS.get(priority, 0.4)
        raw = (
            p_weight                      * 0.40
            + min(sec_hits  / 3, 1.0)    * 0.35
            + min(crit_hits / 2, 1.0)    * 0.15
            + min(comp_hits / 2, 1.0)    * 0.10
        )
        risk_score = round(min(raw, 1.0), 3)

        if risk_score >= 0.70 or security_risk:
            risk_level = "high"
        elif risk_score >= 0.40 or comp_hits > 0:
            risk_level = "medium"
        else:
            risk_level = "low"

        if risk_level == "high":
            confidence_score = int(min(100, 60 + round(risk_score * 40)))
        elif risk_level == "medium":
            confidence_score = int(50 + round(abs(risk_score - 0.55) * 80))
            confidence_score = min(85, confidence_score)
        else:
            confidence_score = int(min(100, 70 + round((0.40 - risk_score) * 75)))

        notes = self._build_notes(sec_hits, comp_hits, crit_hits, risk_level)

        return {
            "risk_level":       risk_level,
            "confidence_score": confidence_score,
            "impact":           risk_level,
            "riskScore":        risk_score,
            "securityRisk":     security_risk,
            "complianceCheck":  compliance_check,
            "notes":            notes,
        }

    def _build_notes(self, sec_hits, comp_hits, crit_hits, risk_level):
        parts = []
        if sec_hits:
            parts.append(
                f"Security indicators detected ({sec_hits} keyword(s)). "
                "Immediate admin review required."
            )
        if comp_hits:
            parts.append(
                "Compliance flags present — manual review and regulatory "
                "assessment required before resolution."
            )
        if crit_hits:
            parts.append(
                "High business-impact language detected. "
                "Potential service-disruption event."
            )
        if not parts:
            if risk_level == "low":
                parts.append(
                    "No elevated risk indicators detected. "
                    "Ticket eligible for automated resolution via knowledge base."
                )
            else:
                parts.append(
                    "Moderate risk indicators. "
                    "Guided resolution recommended with agent oversight."
                )
        return " ".join(parts)
