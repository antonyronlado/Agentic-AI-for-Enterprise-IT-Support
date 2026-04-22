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

        sec_hits = sum(1 for kw in SECURITY_KEYWORDS if kw in text)
        comp_hits = sum(1 for kw in COMPLIANCE_KEYWORDS if kw in text)
        crit_hits = sum(1 for kw in CRITICAL_KEYWORDS if kw in text)

        security_risk = sec_hits > 0
        compliance_check = comp_hits == 0  # True = passed (no compliance flags found)

        p_weight = PRIORITY_WEIGHTS.get(priority, 0.4)
        raw = (
            p_weight * 0.40
            + min(sec_hits / 3, 1.0) * 0.35
            + min(crit_hits / 2, 1.0) * 0.15
            + min(comp_hits / 2, 1.0) * 0.10
        )
        risk_score = round(min(raw, 1.0), 3)

        if risk_score >= 0.70:
            impact = "high"
        elif risk_score >= 0.40:
            impact = "medium"
        else:
            impact = "low"

        notes = self._build_notes(sec_hits, comp_hits, crit_hits)

        return {
            "impact": impact,
            "securityRisk": security_risk,
            "complianceCheck": compliance_check,
            "notes": notes,
            "riskScore": risk_score,
        }

    def _build_notes(self, sec_hits: int, comp_hits: int, crit_hits: int) -> str:
        parts = []
        if sec_hits:
            parts.append(f"Security indicators detected ({sec_hits} keyword(s)).")
        if comp_hits:
            parts.append("Compliance flags present — manual review required.")
        if crit_hits:
            parts.append("High business-impact language detected.")
        if not parts:
            parts.append(
                "No elevated risk indicators. Ticket eligible for automated resolution."
            )
        return " ".join(parts)
