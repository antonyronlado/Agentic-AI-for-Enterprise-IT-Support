import re
import logging

logger = logging.getLogger("nexusdesk.agent.sanitization")

class SanitizationAgent:
    def __init__(self):

        self.patterns = {
            "EMAIL": r'[\w\.-]+@[\w\.-]+\.\w+',
            "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
            "PHONE": r'\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b',
            "PASSWORD": r'(?i)(password|pwd|secret|key|token)[:=\s]+(\S+)',
            "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        }

    def sanitize(self, text: str) -> str:
        if not text:
            return text

        sanitized_text = text

        sanitized_text = re.sub(self.patterns["PASSWORD"], r'\1: [SECURED]', sanitized_text)

        for label, pattern in self.patterns.items():
            if label == "PASSWORD":
                continue

            sanitized_text = re.sub(pattern, f'[{label}_SECURED]', sanitized_text)

        return sanitized_text