"""
risk_agent.py — Phrase-aware risk scoring with scope multiplier and real confidence.

Improvements over previous version:
  - Uses regex phrase patterns instead of plain keyword substring matching
    to avoid false positives (e.g. "forgot password" ≠ security breach).
  - Applies a scope multiplier so company-wide issues score much higher than
    single-user issues.
  - Applies a temporal urgency boost for time-critical tickets.
  - Confidence is derived from how many independent signals agree,
    rather than being derived from the risk score itself.
"""

import re
from agents.ticket_parser import extract_entities

# ---------------------------------------------------------------------------
# Phrase-level pattern lists  (compiled once at import time)
# ---------------------------------------------------------------------------

_SECURITY_PHRASES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"password\s+(stolen|leaked|compromised|exposed)",
        r"credentials?\s+(stolen|compromised|leaked|exposed)",
        r"account\s+(hacked|compromised|taken\s+over|breached)",
        r"(ransomware|malware|virus|trojan|spyware)\s+(detected|found|infected|running|attack)",
        r"unauthorized\s+access",
        r"privilege\s+escalation",
        r"suspicious\s+(login|activity|access|traffic)",
        r"(data\s+)?breach",
        r"phishing\s+(email|link|site|attack)",
        r"intrusion\s+detected",
        r"zero.?day",
        r"vpn\s+bypass",
        r"identity\s+theft",
        r"(clicked?|opened?)\s+(suspicious|malicious|phishing)\s+(link|email|attachment)",
    ]
]

_COMPLIANCE_PHRASES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(gdpr|hipaa|pci\s*dss|sox|iso\s*27001)\b",
        r"(personal|sensitive|confidential)\s+(data|information|records?)",
        r"audit\s+(trail|log|finding|requirement)",
        r"regulatory\s+(requirement|obligation|breach|review)",
        r"data\s+(retention|classification|handling)",
        r"pii\b",
    ]
]

_CRITICAL_PHRASES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(production|live)\s+(server|system|environment|database)\s+(down|crash|fail|unavailable)",
        r"(complete|total|full)\s+(outage|failure|blackout)",
        r"(all|entire)\s+(users?|staff|company|organization|department|team)\s+(affected|cannot|can'?t|impacted)",
        r"(business|operations?)\s+(stopped?|halted?|down|disrupted?|impacted)",
        r"service\s+unavailable",
        r"emergency\s+(shutdown|restart|escalation)",
        r"critical\s+(system|server|service|failure|outage)",
        r"nothing\s+works?\b",
    ]
]

_HIGH_PRIORITY_PHRASES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(completely|totally)\s+(broken|down|unusable|inaccessible)",
        r"(cannot|can'?t|unable\s+to)\s+(work|access|use|connect|log\s+in|open|start)",
        r"(account|device|system)\s+locked\s+out",
        r"(connection|network|service)\s+refused",
        r"no\s+(access|internet|network|connection)",
        r"(blocked|denied)\s+(from|access)",
        r"(client|customer|executive|ceo|director)\s+(facing|impacted|affected|waiting)",
        r"(deadline|presentation|meeting|demo)\s+(in|at|by)\s+\d+",
    ]
]

_PERFORMANCE_PHRASES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(running|loading|starting|opening)\s+slowly?\b",
        r"(high|excessive)\s+(cpu|memory|ram|disk|latency)\s+usage",
        r"(intermittent|occasional|sometimes)\s+(disconnect|drop|slow|lag)",
        r"(timeout|time.?out)\s+(error|issue|problem)",
        r"(freezes?|hangs?|stutters?)\s+(occasionally|sometimes|every|when)",
        r"slight(ly)?\s+(slow|sluggish|laggy|delayed)",
    ]
]

# ---------------------------------------------------------------------------
# Scope multiplier
# ---------------------------------------------------------------------------
_SCOPE_MULTIPLIERS = {
    "company":    2.0,
    "department": 1.6,
    "small_team": 1.25,
    "just_me":    1.0,
}

# ---------------------------------------------------------------------------
# Urgency boost (added to raw score before capping)
# ---------------------------------------------------------------------------
_URGENCY_BOOSTS = {
    "immediate": 0.12,
    "deadline":  0.10,
    "recent":    0.02,
    "ongoing":   0.00,
    "chronic":  -0.03,
    "unknown":   0.00,
}

_PRIORITY_WEIGHTS = {"critical": 1.0, "high": 0.75, "medium": 0.45, "low": 0.15}


def _count(patterns: list[re.Pattern], text: str) -> int:
    return sum(1 for p in patterns if p.search(text))


class RiskAgent:
    def run(
        self,
        title: str,
        description: str,
        category: str = "other",
        priority: str = "medium",
    ) -> dict:
        full_text = f"{title} {description}"

        # --- Phrase-level hit counts ---
        sec_hits  = _count(_SECURITY_PHRASES,    full_text)
        comp_hits = _count(_COMPLIANCE_PHRASES,  full_text)
        crit_hits = _count(_CRITICAL_PHRASES,    full_text)
        high_hits = _count(_HIGH_PRIORITY_PHRASES, full_text)
        perf_hits = _count(_PERFORMANCE_PHRASES, full_text)

        security_risk    = sec_hits > 0
        compliance_check = comp_hits == 0   # True = passed, False = needs review

        # --- Extract scope & urgency ---
        entities = extract_entities(title, description)
        scope    = entities.get("scope", "just_me")
        urgency  = entities.get("urgency", "unknown")

        scope_mult    = _SCOPE_MULTIPLIERS.get(scope, 1.0)
        urgency_boost = _URGENCY_BOOSTS.get(urgency, 0.0)
        p_weight      = _PRIORITY_WEIGHTS.get(priority, 0.45)

        # --- Raw score (0–1) ---
        base = (
            p_weight                       * 0.30
            + min(sec_hits  / 3, 1.0)     * 0.28
            + min(crit_hits / 2, 1.0)     * 0.22
            + min(high_hits / 3, 1.0)     * 0.12
            + min(comp_hits / 2, 1.0)     * 0.08
        )
        raw_score  = min((base * scope_mult) + urgency_boost, 1.0)
        risk_score = round(max(raw_score, 0.0), 3)

        # --- Risk level ---
        if security_risk or crit_hits > 0 or risk_score >= 0.70:
            risk_level = "high"
        elif (
            risk_score >= 0.40
            or comp_hits > 0
            or (high_hits > 0 and priority in ("high", "critical"))
            or scope in ("department", "company")
        ):
            risk_level = "medium"
        elif perf_hits > 0 and risk_score < 0.20:
            risk_level = "low"
        else:
            risk_level = "low"

        # --- Multi-signal confidence score ---
        # Starts at 50, then each independent positive signal adds points.
        confidence_score = self._compute_confidence(
            sec_hits, comp_hits, crit_hits, high_hits, perf_hits,
            risk_score, risk_level, scope, urgency,
        )

        notes = self._build_notes(
            sec_hits, comp_hits, crit_hits, high_hits, perf_hits,
            risk_level, scope, entities.get("affected_system"),
        )

        return {
            "risk_level":       risk_level,
            "confidence_score": confidence_score,
            "impact":           risk_level,
            "riskScore":        risk_score,
            "securityRisk":     security_risk,
            "complianceCheck":  compliance_check,
            "scope":            scope,
            "urgency":          urgency,
            "notes":            notes,
            # Pass entities through so ResolutionAgent can personalise responses
            "_entities":        entities,
        }

    # ------------------------------------------------------------------
    def _compute_confidence(
        self,
        sec_hits, comp_hits, crit_hits, high_hits, perf_hits,
        risk_score, risk_level, scope, urgency,
    ) -> int:
        """
        Multi-signal confidence: each corroborating signal adds to base.
        This is NOT derived from risk_score — it represents how certain
        the assessment is, not how severe.
        """
        base = 50

        # Pattern hit density — more signals → higher confidence
        total_hits = sec_hits + comp_hits + crit_hits + high_hits + perf_hits
        base += min(total_hits * 6, 25)

        # Scope corroborates severity
        if scope in ("department", "company") and risk_level == "high":
            base += 8
        elif scope == "just_me" and risk_level == "low":
            base += 6

        # Urgency corroborates
        if urgency in ("immediate", "deadline") and risk_level in ("high", "medium"):
            base += 5

        # Risk score corroborates level
        if risk_level == "high"   and risk_score >= 0.60: base += 7
        if risk_level == "medium" and 0.30 <= risk_score < 0.65: base += 5
        if risk_level == "low"    and risk_score < 0.25: base += 7

        return min(int(base), 98)

    # ------------------------------------------------------------------
    def _build_notes(
        self,
        sec_hits, comp_hits, crit_hits, high_hits, perf_hits,
        risk_level, scope, affected_system,
    ) -> str:
        parts = []
        sys_str = f" related to {affected_system}" if affected_system else ""

        if sec_hits:
            parts.append(
                f"Security breach indicators detected ({sec_hits} phrase pattern(s)){sys_str}. "
                "Immediate admin review and SOC notification required."
            )
        if crit_hits:
            scope_note = {
                "company":    " — entire company affected.",
                "department": " — department-wide impact.",
                "small_team": " — team-level impact.",
                "just_me":    ".",
            }.get(scope, ".")
            parts.append(
                f"Critical business-impact language detected{scope_note} "
                "Treat as P1 — initiate major incident process."
            )
        if comp_hits:
            parts.append(
                "Compliance/regulatory flags present. "
                "Legal and compliance review required before resolution."
            )
        if high_hits and not sec_hits and not crit_hits:
            parts.append(
                f"User reports complete inability to perform work tasks{sys_str}. "
                "Prioritise for same-day resolution."
            )
        if perf_hits and not parts:
            parts.append(
                f"Performance degradation reported{sys_str}. "
                "Low security risk — guide user through optimisation steps."
            )
        if not parts:
            if risk_level == "low":
                parts.append(
                    "No elevated risk indicators detected. "
                    "Ticket eligible for automated resolution via knowledge base."
                )
            else:
                parts.append(
                    "Moderate risk indicators detected. "
                    "Guided resolution with agent oversight recommended."
                )
        return " ".join(parts)