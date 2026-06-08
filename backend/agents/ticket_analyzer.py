import asyncio
import re
from models.model_loader import ModelLoader

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
# Keyword maps — ordered by specificity (most specific first)
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "access": [
        "password", "login", "log in", "sign in", "signin", "logout",
        "locked out", "lock out", "account locked", "2fa", "mfa",
        "authentication", "authorization", "permission", "access denied",
        "credentials", "reset password", "forgot password", "otp",
        "vpn", "sso", "single sign-on", "active directory", "ldap",
        "user account", "privilege", "role", "access request",
        "suspicious login", "unauthorized access", "login attempt",
    ],
    "network": [
        "network", "internet", "connectivity", "connection", "offline",
        "wifi", "wi-fi", "wireless", "ethernet", "bandwidth", "latency",
        "ping", "dns", "ip address", "firewall", "proxy", "vpn connectivity",
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

_BART_FALLBACK_THRESHOLD = 0.45  # below this, use BART for reclassification


def _keyword_classify_category(text: str) -> tuple[str, float]:
    """Return (category, confidence) based on keyword matching."""
    lower = text.lower()
    scores: dict[str, int] = {cat: 0 for cat in _CATEGORY_KEYWORDS}
    for cat, kws in _CATEGORY_KEYWORDS.items():
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                # longer keyword phrases worth more
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


class TicketAnalyzerAgent:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader

    async def run(self, title: str, description: str) -> dict:
        text = f"{title}. {description}".strip()
        loop = asyncio.get_running_loop()

        # --- Fast keyword pass (synchronous, microseconds) ---
        kw_category, kw_cat_conf = _keyword_classify_category(text)
        kw_priority, kw_pri_conf = _keyword_classify_priority(text)

        # --- Decide if BART fallback is needed ---
        need_bart_cat = kw_cat_conf < _BART_FALLBACK_THRESHOLD
        need_bart_pri = kw_pri_conf < _BART_FALLBACK_THRESHOLD

        category = kw_category
        priority = kw_priority
        confidence = kw_cat_conf

        if need_bart_cat or need_bart_pri:
            # Only run BART for the dimensions that need it
            bart_tasks = []
            if need_bart_cat:
                bart_tasks.append(("cat", loop.run_in_executor(None, self._classify, text, CATEGORY_LABELS)))
            if need_bart_pri:
                bart_tasks.append(("pri", loop.run_in_executor(None, self._classify, text, PRIORITY_LABELS)))

            results = await asyncio.gather(*[t for _, t in bart_tasks], return_exceptions=True)

            for (dim, _), result in zip(bart_tasks, results):
                if isinstance(result, Exception):
                    # BART failed — stick with keyword result
                    continue
                if dim == "cat":
                    category = result["labels"][0]
                    confidence = round(result["scores"][0], 3)
                elif dim == "pri":
                    priority = result["labels"][0]
        else:
            confidence = round(kw_cat_conf, 3)

        return {
            "intent":             INTENT_MAP.get(category, "General IT Support Request"),
            "summary":            self._summarize(description),
            "suggestedPriority":  priority,
            "suggestedCategory":  category,
            "confidenceScore":    confidence,
        }

    def _classify(self, text: str, labels: list) -> dict:
        return self.model_loader.classifier(text, labels)

    def _summarize(self, description: str) -> str:
        sentences = description.replace("\n", ". ").split(". ")
        first = sentences[0].strip() if sentences else description
        return (first[:197] + "...") if len(first) > 200 else first