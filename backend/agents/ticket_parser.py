"""
ticket_parser.py — Entity extraction from raw ticket text.

Extracts structured facts so agents can personalise responses per ticket,
filter irrelevant KB steps, and skip suggestions the user already tried.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# System / tool name patterns
# ---------------------------------------------------------------------------
_SYSTEM_PATTERNS: list[tuple[str, str]] = [
    # Collaboration & email
    (r"\boutlook\b",           "Outlook"),
    (r"\bmicrosoft\s*teams?\b","Microsoft Teams"),
    (r"\bteams\b",             "Microsoft Teams"),
    (r"\bzoom\b",              "Zoom"),
    (r"\bslack\b",             "Slack"),
    (r"\bwebex\b",             "Webex"),
    (r"\bgoogle\s*meet\b",     "Google Meet"),
    (r"\bonedrive\b",          "OneDrive"),
    (r"\bsharepoint\b",        "SharePoint"),
    # Networking / access
    (r"\bvpn\b",               "VPN"),
    (r"\bwifi\b|wi[-\s]?fi\b", "Wi-Fi"),
    (r"\bwireless\b",          "Wi-Fi"),
    (r"\bethernet\b",          "Ethernet"),
    (r"\brdp\b|remote\s*desktop", "Remote Desktop"),
    (r"\binternet\b",          "internet connection"),
    (r"\bdns\b",               "DNS"),
    # Hardware
    (r"\bprinter\b",           "printer"),
    (r"\bscanner\b",           "scanner"),
    (r"\bkeyboard\b",          "keyboard"),
    (r"\bmouse\b",             "mouse"),
    (r"\bmonitor\b|\bdisplay\b|\bscreen\b", "display"),
    (r"\bwebcam\b|\bcamera\b", "webcam"),
    (r"\bmicrophone\b|\bmic\b","microphone"),
    (r"\bheadset\b|\bheadphone\b", "headset"),
    (r"\bprojector\b",         "projector"),
    (r"\busb\b",               "USB device"),
    (r"\blaptop\b",            "laptop"),
    (r"\bdesktop\b",           "desktop PC"),
    (r"\bbattery\b",           "battery"),
    # Software / OS
    (r"\bwindows\b",           "Windows"),
    (r"\boffice\b|microsoft\s*office", "Microsoft Office"),
    (r"\bexcel\b",             "Excel"),
    (r"\bword\b",              "Word"),
    (r"\bpowerpoint\b",        "PowerPoint"),
    (r"\bantivirus\b|av\s+agent|endpoint\s+security", "antivirus"),
    (r"\bbitlocker\b",         "BitLocker"),
    (r"\bsap\b",               "SAP"),
    (r"\boracle\b",            "Oracle"),
    (r"\berp\b",               "ERP system"),
    (r"\bchrome\b",            "Chrome"),
    (r"\bedge\b",              "Edge"),
    (r"\bfirefox\b",           "Firefox"),
    # Auth / identity
    (r"\bmfa\b|multi.factor|authenticator\s*app", "MFA/Authenticator"),
    (r"\bactive\s*directory\b|\bad\b", "Active Directory"),
    (r"\bsso\b|single\s*sign.on", "SSO"),
    (r"\bokta\b",              "Okta"),
    (r"\bazure\s*ad\b",        "Azure AD"),
]

# ---------------------------------------------------------------------------
# Symptom verb patterns (the core problem word)
# ---------------------------------------------------------------------------
_SYMPTOM_PATTERNS: list[tuple[str, str]] = [
    (r"\b(completely\s+)?disconnected?\b|no\s+(internet|network|connection|signal|bars?)\b|dropped?\s+(connection|network)|\bdead\b|\bno\s+bars?\b", "disconnected"),
    (r"\bslow\b|\blaggy?\b|\bsluggish\b|\bhigh\s+latency\b|\bpoor\s+(speed|throughput|performance)\b", "slow"),
    (r"\bcrash(ing|ed)?\b|\bcrashes?\b|\bcrash\b",       "crashing"),
    (r"\bfroze?n?\b|\bfreezing\b|\bhung?\b|\bhanging\b|\bnot\s+responding\b", "frozen"),
    (r"\bnot\s+(loading|starting|opening|launching|working)\b|\bfails?\s+to\s+(open|start|load|launch)\b", "not_opening"),
    (r"\block(ed)?\s*out\b|\baccount\s+lock\b",           "locked_out"),
    (r"\bexpired?\b|\bexpir(ation|y)\b",                  "expired"),
    (r"\bnot\s+(syncing|sync)\b|\bsync\s+(issue|error|fail)\b|\bstuck\b", "not_syncing"),
    (r"\bnot\s+(detected|recognized|showing|found)\b|\bmissing\b", "not_detected"),
    (r"\bblack\s+screen\b|\bblank\s+screen\b|\bno\s+display\b", "black_screen"),
    (r"\bflicker(ing)?\b|\bartifact(s)?\b|\bglitch(ing)?\b", "flickering"),
    (r"\b(not\s+)?charg(ing|ed)?\b|\bdying?\b",  "not_charging"),
    (r"\boverheating?\b|\bhot\b|\bfan\s+(loud|noise|full\s+speed)\b", "overheating"),
    (r"\bencrypt(ed|ion)?\b|\bransom\b",                  "ransomware"),
    (r"\bphish(ing)?\b|\bsuspicious\s+email\b",           "phishing"),
    (r"\binstall(ation)?\s+fail\b|\bwon'?t\s+install\b",  "install_fail"),
    (r"\blicense\s+(expired?|error|invalid)\b|\bactivation\s+error\b", "license_error"),
    (r"\bno\s+(audio|sound)\b|\baudio\s+not\s+working\b", "no_audio"),
    (r"\b(cannot|can'?t|unable to)\s+(print|scan)\b|\boffline\b", "device_offline"),
    (r"\bdeleted?\b|\brecovery\b|\bmissing\s+files?\b",   "data_loss"),
    (r"\baccess\s+denied\b|\bpermission\s+denied\b|\bforbidden\b", "access_denied"),
]

# ---------------------------------------------------------------------------
# Scope / impact patterns
# ---------------------------------------------------------------------------
_SCOPE_PATTERNS: list[tuple[str, str]] = [
    (r"\beveryone\b|\ball\s+(?:users?|staff|employees?|of\s+us)\b|company.?wide\b|entire\s+company\b", "company"),
    (r"\bentire\s+(?:department|floor|team|office)\b|\ball\s+(?:of\s+)?(?:my\s+)?team\b|multiple\s+users?\b", "department"),
    (r"\bmy\s+team\b|\bour\s+team\b|\ba\s+few\s+(?:users?|people|colleagues?)\b|\bsome\s+users?\b", "small_team"),
    (r"\bjust\s+me\b|\bonly\s+(?:me|I|my)\b|\bmy\s+(?:laptop|pc|computer|account|device)\b|\bI\s+(?:cannot|can'?t|am unable)\b", "just_me"),
]

# ---------------------------------------------------------------------------
# Temporal urgency patterns
# ---------------------------------------------------------------------------
_URGENCY_PATTERNS: list[tuple[str, str]] = [
    (r"\bright\s+now\b|\bimmediately\b|\burgent\b|\bemergency\b|\basap\b|\bcritical\b", "immediate"),
    (r"\bclient\s+(?:meeting|call|demo|presentation)\b|\bdeadline\b|\bpresentation\b|\bmeeting\s+in\b", "deadline"),
    (r"\bjust\s+(?:now|started|happened|occurred)\b|\btoday\b|\bthis\s+morning\b|\bsince\s+this\b", "recent"),
    (r"\ba\s+few\s+(?:days?|hours?)\b|\bsince\s+(?:yesterday|monday|tuesday|wednesday|thursday|friday)\b", "ongoing"),
    (r"\bweeks?\b|\bmonths?\b|\blong\s+time\b|\bfor\s+a\s+while\b", "chronic"),
]

# ---------------------------------------------------------------------------
# "Already tried" patterns
# ---------------------------------------------------------------------------
_TRIED_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:already\s+)?(?:tried|attempted)\s+restart(?:ing)?\b|restarted?\s+(?:my|the)?\s*(?:laptop|pc|computer|device|machine)\b", "restart"),
    (r"\b(?:already\s+)?reinstalled?\b",        "reinstall"),
    (r"\b(?:already\s+)?cleared?\s+(?:cache|cookies|temp)\b", "cleared_cache"),
    (r"\b(?:already\s+)?(?:updated?|upgraded?)\b", "updated_drivers"),
    (r"\b(?:already\s+)?changed?\s+(?:password|credentials)\b", "changed_password"),
    (r"\b(?:already\s+)?reset\b",               "reset"),
    (r"\b(?:already\s+)?flushed?\s+dns\b",       "flushed_dns"),
    (r"\b(?:already\s+)?disconnected?\s+(?:and\s+)?reconnected?\b|reconnected?\b", "reconnected"),
    (r"\b(?:already\s+)?unplugged?\s+(?:and\s+)?plugged?\b", "replugged"),
    (r"\b(?:already\s+)?contacted?\s+(?:IT|support|helpdesk)\b", "contacted_it"),
    (r"\b(?:already\s+)?checked?\s+(?:cables?|connections?|settings?)\b", "checked_settings"),
    (r"\b(?:already\s+)?called?\s+(?:IT|support|helpdesk)\b", "called_it"),
    (r"\b(?:already\s+)?ipconfig\b|(?:already\s+)?ran?\s+(?:ipconfig|ping|tracert)\b", "ran_network_cmd"),
]

# ---------------------------------------------------------------------------
# Error code extraction
# ---------------------------------------------------------------------------
_STOP_CODE_RE = re.compile(
    r"\b[A-Z_]{3,}\s+(?:ERROR\s+)?[\w\-:]+\b"
)

_ERROR_CODE_RE = re.compile(
    r"""
    (?:
        0x[0-9A-Fa-f]{4,}               |   # hex codes: 0x80070005
        error\s+(?:code\s+)?            |   # "error code"
        event\s+id\s+                   |   # event IDs
        kb\d{6,}                        |   # knowledge base IDs
        caa\w+                          |   # Office/AAD error codes: caa20004
        BSOD:\s*\S+
    )
    [\w\-:]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_entities(title: str, description: str) -> dict:
    """
    Parse the ticket title + description and return a structured entity dict.

    Returns:
        {
            "affected_system":  str | None,   # e.g. "Outlook", "VPN"
            "symptom_verb":     str | None,   # e.g. "slow", "disconnected"
            "scope":            str,          # "just_me" | "small_team" | "department" | "company"
            "urgency":          str,          # "immediate" | "deadline" | "recent" | "ongoing" | "chronic" | "unknown"
            "tried_steps":      list[str],    # steps the user says they already tried
            "error_codes":      list[str],    # raw error code strings found
        }
    """
    text = f"{title}. {description}".lower()
    raw_text = f"{title}. {description}"  # preserve case for readability

    affected_system = _first_match(_SYSTEM_PATTERNS,  text)
    symptom_verb    = _first_match(_SYMPTOM_PATTERNS, text)
    scope           = _first_match(_SCOPE_PATTERNS,   text) or "just_me"
    urgency         = _first_match(_URGENCY_PATTERNS, text) or "unknown"
    tried_steps     = _all_matches(_TRIED_PATTERNS,   text)
    error_codes     = [m.strip() for m in _ERROR_CODE_RE.findall(raw_text)]
    error_codes    += [m.strip() for m in _STOP_CODE_RE.findall(raw_text)]
    error_codes     = error_codes[:5]

    return {
        "affected_system": affected_system,
        "symptom_verb":    symptom_verb,
        "scope":           scope,
        "urgency":         urgency,
        "tried_steps":     tried_steps,
        "error_codes":     error_codes,
    }


def _first_match(patterns: list[tuple[str, str]], text: str) -> Optional[str]:
    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None


def _all_matches(patterns: list[tuple[str, str]], text: str) -> list[str]:
    found = []
    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE) and label not in found:
            found.append(label)
    return found
