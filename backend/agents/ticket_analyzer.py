"""
ticket_analyzer.py — NLP-based ticket classification with sub-category detection.

Improvements:
  - Two-level classification: category + sub_category (e.g. network/slow vs network/disconnected)
  - BART classifier confidence is passed through to callers instead of being discarded
  - Summarisation uses meaningful first-error-sentence, not just split()[0]
"""

import asyncio
import re
from models.model_loader import ModelLoader

# ---------------------------------------------------------------------------
# Top-level categories (unchanged)
# ---------------------------------------------------------------------------
CATEGORY_LABELS = ["software", "hardware", "access", "network", "other"]
PRIORITY_LABELS = ["critical", "high", "medium", "low"]

INTENT_MAP = {
    "software": "Software Issue / Application Error",
    "hardware": "Hardware Malfunction / Device Problem",
    "access":   "Access & Authentication Request",
    "network":  "Network / Connectivity Issue",
    "other":    "General IT Support Request",
}

# ---------------------------------------------------------------------------
# Top-level keyword maps (unchanged from original)
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "access": [
        "password", "login", "log in", "sign in", "signin", "logout",
        "locked out", "lock out", "account locked", "2fa", "mfa",
        "authentication", "authorization", "permission", "access denied",
        "credentials", "reset password", "forgot password", "otp",
        "sso", "single sign-on", "active directory", "ldap",
        "user account", "privilege", "role", "access request",
        "suspicious login", "unauthorized access", "login attempt",
    ],
    "network": [
        "network", "internet", "connectivity", "connection", "offline",
        "wifi", "wi-fi", "wireless", "ethernet", "bandwidth", "latency",
        "ping", "dns", "ip address", "firewall", "proxy", "vpn",
        "slow internet", "no internet", "packet loss", "network drive",
        "mapped drive", "share", "remote desktop", "rdp", "ssh",
    ],
    "hardware": [
        "hardware", "keyboard", "mouse", "monitor", "screen", "display",
        "printer", "scanner", "headset", "headphone", "speaker", "microphone",
        "laptop", "desktop", "computer", "device", "usb", "hard drive",
        "ssd", "ram", "memory", "battery", "charger", "dock", "docking",
        "cable", "port", "webcam", "camera", "phone", "mobile device",
        "broken", "damaged", "physical", "overheating", "fan",
    ],
    "software": [
        "software", "application", "app", "error", "crash", "freeze",
        "not responding", "blue screen", "bsod", "install", "uninstall",
        "update", "upgrade", "patch", "bug", "glitch", "issue",
        "microsoft office", "excel", "word", "outlook", "teams", "zoom",
        "browser", "chrome", "firefox", "edge", "antivirus", "malware",
        "virus", "ransomware", "license", "activation", "windows",
        "operating system", "os", "driver", "java", "python", "database",
    ],
}

_PRIORITY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "critical", "urgent", "emergency", "down", "outage", "production down",
        "not working at all", "completely broken", "ransomware", "breach",
        "data loss", "system failure", "cannot work", "business stopped",
        "security incident", "hacked", "compromised", "all users affected",
        "multiple users", "entire team", "company-wide",
    ],
    "high": [
        "high priority", "asap", "immediately", "important", "significant",
        "major", "serious", "blocked", "blocking", "cannot", "unable to",
        "not able to", "failing", "suspicious", "unauthorized",
        "deadline", "client facing", "customer impacted",
    ],
    "low": [
        "low priority", "minor", "cosmetic", "whenever", "no rush",
        "not urgent", "informational", "question", "how to", "how do i",
        "request", "feature request", "suggestion", "nice to have",
        "when possible", "at your convenience",
    ],
}

# ---------------------------------------------------------------------------
# Sub-category keyword maps (new — second classification pass)
# ---------------------------------------------------------------------------
_SUB_CATEGORY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "network": {
        "slow":           ["slow", "sluggish", "laggy", "lag", "latency", "latent", "intermittent", "poor speed", "throughput", "bandwidth"],
        "disconnected":   ["disconnected", "no internet", "no connection", "dropped", "offline", "not connecting", "cannot connect", "no access", "lost connection"],
        "vpn_down":       ["vpn dead", "vpn not connecting", "vpn failed", "vpn won't connect", "vpn connection dead",
                           "cannot connect to vpn", "vpn not working", "vpn signal", "no bars", "no vpn"],
        "vpn_slow":       ["vpn slow", "vpn lag", "vpn laggy", "vpn speed", "vpn performance", "vpn throughput",
                           "slow vpn", "laggy vpn", "vpn latency", "vpn intermittent"],
        "vpn_access":     ["vpn connected but", "connected to vpn but cannot", "vpn shows connected", "connected vpn no access"],
        "vpn":            ["vpn", "remote access", "cisco anyconnect", "globalprotect", "openvpn", "wireguard"],
        "dns":            ["dns", "name resolution", "cannot resolve", "domain not found"],
        "drive_mapping":  ["network drive", "mapped drive", "shared folder", "file server", "unc path", "map drive"],
        "remote_desktop": ["rdp", "remote desktop", "remote connection", "mstsc"],
        "outage":         ["outage", "server down", "service down", "production down", "all users", "everyone affected"],
        "firewall":       ["firewall", "blocked", "port", "traffic blocked", "connection refused", "access blocked"],
    },
    "access": {
        "password_reset": ["forgot password", "reset password", "password reset", "change password", "expired password"],
        "locked_out":     ["locked out", "account locked", "too many attempts", "lockout", "account expired"],
        "mfa":            ["mfa", "2fa", "two factor", "authenticator", "otp", "one time password", "verification code"],
        "permission":     ["permission", "access denied", "forbidden", "no permission", "privilege", "access request", "role"],
        "new_account":    ["new employee", "new user", "onboarding", "create account", "new account", "new hire"],
        "offboarding":    ["offboarding", "leaving", "termination", "disable account", "revoke access", "employee leaving"],
    },
    "software": {
        "crash":          ["crash", "crashes", "crashing", "not responding", "stopped working", "application error", "force close"],
        "performance":    ["slow", "sluggish", "high cpu", "high memory", "freezing", "lagging", "taking long"],
        "install":        ["install", "installation", "cannot install", "deployment", "setup failed"],
        "update":         ["update", "patch", "upgrade", "windows update", "software version"],
        "license":        ["license", "activation", "not activated", "license expired", "product key", "unlicensed"],
        "office":         ["outlook", "excel", "word", "sharepoint", "onedrive", "teams", "office", "microsoft 365"],
        "antivirus":      ["antivirus", "malware", "virus", "ransomware", "phishing", "security alert", "endpoint", "sophos", "crowdstrike"],
        "collaboration":  ["teams", "zoom", "slack", "webex", "google meet", "video call", "screen share"],
        "data_recovery":  ["deleted", "recover", "missing files", "lost data", "backup", "restore"],
        "database":       ["database", "sql", "db", "cannot connect to database", "query", "db server"],
        "configuration":  ["group policy", "gpo", "domain", "registry", "bitlocker", "encryption", "compliance"],
    },
    "hardware": {
        "peripheral":     ["printer", "scanner", "keyboard", "mouse", "usb", "headset", "speaker"],
        "display":        ["monitor", "screen", "display", "resolution", "hdmi", "displayport", "flicker", "artifact", "projector"],
        "audio_video":    ["webcam", "camera", "microphone", "mic", "audio", "video call", "no sound", "voip", "phone"],
        "system_crash":   ["blue screen", "bsod", "kernel", "crash", "stop error", "reboot loop", "bios"],
        "storage":        ["hard drive", "ssd", "disk", "storage", "hdd", "bad sector", "smart"],
        "overheating":    ["overheating", "hot", "fan", "thermal", "temperature", "heat"],
        "power":          ["battery", "charging", "power", "not turning on", "won't start", "dead", "ups"],
    },
    "other": {
        "escalation":     ["sla", "breach", "deadline", "escalat", "overdue"],
    },
}

_BART_FALLBACK_THRESHOLD = 0.45


def _keyword_classify_category(text: str) -> tuple[str, float]:
    """Return (category, confidence) based on keyword matching."""
    lower = text.lower()
    scores: dict[str, int] = {cat: 0 for cat in _CATEGORY_KEYWORDS}
    for cat, kws in _CATEGORY_KEYWORDS.items():
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                scores[cat] += len(kw.split())

    total = sum(scores.values())
    if total == 0:
        return "other", 0.0

    best = max(scores, key=scores.get)
    confidence = scores[best] / total
    return best, confidence


def _keyword_classify_priority(text: str) -> tuple[str, float]:
    """Return (priority, confidence) based on keyword matching."""
    lower = text.lower()
    scores: dict[str, int] = {pri: 0 for pri in _PRIORITY_KEYWORDS}
    for pri, kws in _PRIORITY_KEYWORDS.items():
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                scores[pri] += len(kw.split())

    total = sum(scores.values())
    if total == 0:
        return "medium", 0.0

    best = max(scores, key=scores.get)
    confidence = scores[best] / total
    return best, confidence


def _classify_sub_category(text: str, category: str) -> str:
    """
    Second-level classification within the given category.
    Returns the best sub_category string or 'general' if nothing matches.
    """
    sub_map = _SUB_CATEGORY_KEYWORDS.get(category, {})
    if not sub_map:
        return "general"

    lower = text.lower()
    scores: dict[str, int] = {sub: 0 for sub in sub_map}
    for sub, kws in sub_map.items():
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                scores[sub] += len(kw.split())

    total = sum(scores.values())
    if total == 0:
        return "general"

    return max(scores, key=scores.get)


def _smart_summarize(description: str) -> str:
    """
    Return the first meaningful sentence from the description.
    Prefers sentences containing an error keyword.
    """
    sentences = re.split(r'(?<=[.!?])\s+', description.replace("\n", ". ").strip())
    # Prefer a sentence that contains an indicator word
    indicators = ("error", "fail", "crash", "cannot", "can't", "not working", "broken",
                  "slow", "disconnect", "issue", "problem", "unable")
    for s in sentences:
        sl = s.lower()
        if any(ind in sl for ind in indicators) and len(s) >= 15:
            return (s[:197] + "...") if len(s) > 200 else s
    # Fallback: first non-trivial sentence
    first = sentences[0].strip() if sentences else description
    return (first[:197] + "...") if len(first) > 200 else first


class TicketAnalyzerAgent:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader

    async def run(self, title: str, description: str) -> dict:
        text = f"{title}. {description}".strip()
        loop = asyncio.get_running_loop()

        # --- Fast keyword pass ---
        kw_category, kw_cat_conf = _keyword_classify_category(text)
        kw_priority, kw_pri_conf = _keyword_classify_priority(text)

        # --- Decide if BART fallback is needed ---
        need_bart_cat = kw_cat_conf < _BART_FALLBACK_THRESHOLD
        need_bart_pri = kw_pri_conf < _BART_FALLBACK_THRESHOLD

        category   = kw_category
        priority   = kw_priority
        confidence = kw_cat_conf
        bart_cat_score: float | None = None

        if need_bart_cat or need_bart_pri:
            bart_tasks = []
            if need_bart_cat:
                bart_tasks.append(("cat", loop.run_in_executor(None, self._classify, text, CATEGORY_LABELS)))
            if need_bart_pri:
                bart_tasks.append(("pri", loop.run_in_executor(None, self._classify, text, PRIORITY_LABELS)))

            results = await asyncio.gather(*[t for _, t in bart_tasks], return_exceptions=True)

            for (dim, _), result in zip(bart_tasks, results):
                if isinstance(result, Exception):
                    continue
                if dim == "cat":
                    category       = result["labels"][0]
                    confidence     = round(result["scores"][0], 3)
                    bart_cat_score = confidence
                elif dim == "pri":
                    priority = result["labels"][0]
        else:
            confidence = round(kw_cat_conf, 3)

        # --- Sub-category detection (new) ---
        sub_category = _classify_sub_category(text, category)

        return {
            "intent":            INTENT_MAP.get(category, "General IT Support Request"),
            "summary":           _smart_summarize(description),
            "suggestedPriority": priority,
            "suggestedCategory": category,
            "sub_category":      sub_category,
            "confidenceScore":   confidence,
            # Expose BART score for downstream confidence calculations
            "_bart_confidence":  bart_cat_score,
        }

    def _classify(self, text: str, labels: list) -> dict:
        return self.model_loader.classifier(text, labels)