"""Security scanning for trust proxy — prompt injection & secret detection."""

from dataclasses import dataclass
from enum import Enum
import re


class Action(Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass
class Threat:
    pattern_name: str
    score: int


@dataclass
class ScanResult:
    action: Action
    risk_score: int
    threats: list[Threat]


class SecurityScanner:
    PATTERNS = [
        # Injection (EN)
        (r"(?i)ignore\s+(all\s+)?previous\s+instructions", "injection_ignore", 80),
        (r"(?i)you\s+are\s+now\s+(?:a|an)\s+", "injection_roleplay", 60),
        (r"(?i)system\s*prompt", "injection_system", 40),
        (r"(?i)jailbreak", "injection_jailbreak", 90),
        (r"(?i)DAN\s+mode", "injection_dan", 90),
        # Injection (FR)
        (r"(?i)oublie\s+(tes|les|toutes)\s+instructions", "injection_oublie", 80),
        (r"(?i)ignore\s+(tes|les|toutes)\s+(consignes|directives)", "injection_ignore_fr", 80),
        # Secrets
        (r"(?:sk|pk)[-_][a-zA-Z0-9]{20,}", "secret_api_key", 70),
        (r"(?i)password\s*[:=]\s*\S+", "secret_password", 50),
        (r"\b[A-Za-z0-9+/]{40,}={0,2}\b", "secret_base64_long", 30),
    ]
    BLOCK_THRESHOLD = 70
    WARN_THRESHOLD = 30

    def scan(self, text: str) -> ScanResult:
        threats = []
        for pattern, name, score in self.PATTERNS:
            if re.search(pattern, text):
                threats.append(Threat(pattern_name=name, score=score))
        total = sum(t.score for t in threats)
        if total >= self.BLOCK_THRESHOLD:
            action = Action.BLOCK
        elif total >= self.WARN_THRESHOLD:
            action = Action.WARN
        else:
            action = Action.ALLOW
        return ScanResult(action=action, risk_score=total, threats=threats)
