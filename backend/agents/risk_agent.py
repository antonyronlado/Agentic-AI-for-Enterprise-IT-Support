import asyncio

SECURITY_KEYWORDS = [
    "malware", "ransomware", "virus", "phishing", "breach", "hacked",
    "unauthorized access", "privilege escalation", "credentials stolen",
    "password leak", "data loss", "data breach", "vpn bypass",
    "suspicious activity", "intrusion", "exploit", "zero-day",
    "account compromised", "identity theft",
]

COMPLIANCE_KEYWORDS = [
    "gdpr", "hipaa", "pci dss", "audit", "compliance", "financial",
    "pii", "personal data", "sensitive", "confidential", "regulated", "sox",
]

CRITICAL_KEYWORDS = [
    "server down", "production down", "outage", "system crash",
    "emergency", "all users affected", "entire department",
    "business impact", "service unavailable", "complete outage",
    "cannot work at all", "nothing works", "total failure",
]

HIGH_PRIORITY_KEYWORDS = [
    "cannot work", "not working", "completely broken", "failed",
    "unable to access", "blocked", "no access", "connection refused",
    "account locked", "locked out",
]

PERFORMANCE_KEYWORDS = [
    "slow", "laggy", "lag", "unresponsive", "intermittent", "timeout",
    "latency", "freezing", "hanging", "stuttering", "delayed", "sluggish",
    "sometimes", "occasionally", "irresponsive",
]

PRIORITY_WEIGHTS = {"critical": 1.0, "high": 0.75, "medium": 0.45, "low": 0.15}


class RiskAgent:
    def run(self, title: str, description: str, category: str = "other", priority: str = "medium") -> dict:
        text = f"{title} {description}".lower()

        sec_hits  = sum(1 for kw in SECURITY_KEYWORDS      if kw in text)
        comp_hits = sum(1 for kw in COMPLIANCE_KEYWORDS    if kw in text)
        crit_hits = sum(1 for kw in CRITICAL_KEYWORDS      if kw in text)
        high_hits = sum(1 for kw in HIGH_PRIORITY_KEYWORDS if kw in text)
        perf_hits = sum(1 for kw in PERFORMANCE_KEYWORDS   if kw in text)

        security_risk    = sec_hits > 0
        compliance_check = comp_hits == 0

        p_weight   = PRIORITY_WEIGHTS.get(priority, 0.45)
        raw        = (
            p_weight                      * 0.35
            + min(sec_hits  / 3, 1.0)    * 0.30
            + min(crit_hits / 2, 1.0)    * 0.20
            + min(high_hits / 3, 1.0)    * 0.10
            + min(comp_hits / 2, 1.0)    * 0.05
        )
        risk_score = round(min(raw, 1.0), 3)

        if security_risk or crit_hits > 0:
            risk_level = "high"
        elif risk_score >= 0.55 or (high_hits > 0 and priority in ("high", "critical")):
            risk_level = "high"
        elif risk_score >= 0.35 or comp_hits > 0 or (high_hits > 0 and priority == "medium"):
            risk_level = "medium"
        elif perf_hits > 0 and risk_score < 0.20:
            risk_level = "low"
        else:
            risk_level = "low"

        if risk_level == "high":
            confidence_score = int(min(100, 65 + round(risk_score * 35)))
        elif risk_level == "medium":
            confidence_score = int(min(85, 55 + round(risk_score * 60)))
        else:
            confidence_score = int(min(95, 75 + round((0.35 - min(risk_score, 0.35)) * 57)))

        return {
            "risk_level":       risk_level,
            "confidence_score": confidence_score,
            "impact":           risk_level,
            "riskScore":        risk_score,
            "securityRisk":     security_risk,
            "complianceCheck":  compliance_check,
            "notes":            self._build_notes(sec_hits, comp_hits, crit_hits, high_hits, perf_hits, risk_level),
        }

    def _build_notes(self, sec_hits, comp_hits, crit_hits, high_hits, perf_hits, risk_level):
        parts = []
        if sec_hits:
            parts.append(
                f"Security breach indicators detected ({sec_hits} signal(s)). "
                "Immediate admin review and SOC notification required."
            )
        if crit_hits:
            parts.append(
                "Critical business-impact language detected. "
                "Potential widespread service disruption — treat as P1."
            )
        if comp_hits:
            parts.append(
                "Compliance flags present — regulatory review required before resolution."
            )
        if high_hits and not sec_hits and not crit_hits:
            parts.append(
                "User reports complete inability to perform work tasks. "
                "Prioritize for same-day resolution."
            )
        if perf_hits and not parts:
            parts.append(
                "Performance degradation reported. "
                "Low security risk — guide user through optimization steps."
            )
        if not parts:
            if risk_level == "low":
                parts.append(
                    "No elevated risk indicators. "
                    "Ticket eligible for automated resolution via knowledge base."
                )
            else:
                parts.append(
                    "Moderate risk indicators detected. "
                    "Guided resolution recommended with agent oversight."
                )
        return " ".join(parts)
