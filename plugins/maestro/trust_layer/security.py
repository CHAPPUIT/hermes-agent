"""Trust Layer — Module Sécurité (TOUJOURS ACTIF).

Trois couches de protection :
1. Détection d'obfuscation (Base64, Unicode homoglyphes, chars invisibles)
2. Détection de secrets (API keys, tokens, mots de passe)
3. Détection d'injection de prompt (patterns YARA-like)

Ce module est actif quel que soit le LLM cible (local ou externe).
"""

import base64
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatSeverity(str, Enum):
    """Sévérité d'une menace détectée."""

    CRITICAL = "critical"  # Score >= 85 → BLOCK
    HIGH = "high"  # Score >= 70 → WARN
    MEDIUM = "medium"  # Score >= 50 → LOG
    LOW = "low"  # Score < 50 → PASS


class ThreatCategory(str, Enum):
    """Catégories de menaces détectées."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_EXFILTRATION = "data_exfiltration"
    ROLE_MANIPULATION = "role_manipulation"
    ENCODING_ATTACK = "encoding_attack"
    SECRET_LEAK = "secret_leak"
    INVISIBLE_CHARS = "invisible_chars"
    UNICODE_HOMOGLYPH = "unicode_homoglyph"


@dataclass
class ThreatMatch:
    """Une menace détectée dans le texte."""

    category: ThreatCategory
    severity: ThreatSeverity
    score: int  # 0-100
    pattern_name: str
    matched_text: str = ""
    detail: str = ""


@dataclass
class SecurityResult:
    """Résultat de l'analyse de sécurité.

    Attributes:
        safe: True si aucune menace critique/haute détectée.
        risk_score: Score de risque global 0-100 (max des menaces).
        action: Action recommandée (BLOCK, WARN, LOG, PASS).
        threats: Liste des menaces détectées.
        cleaned_text: Texte nettoyé (obfuscation décodée, chars invisibles retirés).
        processing_time_ms: Durée du scan en ms.
    """

    safe: bool = True
    risk_score: int = 0
    action: str = "PASS"
    threats: list[ThreatMatch] = field(default_factory=list)
    cleaned_text: str = ""
    processing_time_ms: int = 0


# ============================================================================
# Patterns d'injection de prompt (FR + EN)
# ============================================================================

_INJECTION_PATTERNS: list[tuple[str, str, int, ThreatCategory]] = [
    # --- Direct Override ---
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?|guidelines?)",
     "direct_override_en", 90, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|rules?|programming|training)",
     "direct_override_en_2", 90, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)oublie\s+(toutes?\s+)?(tes|les|vos)\s+(instructions?|consignes?|règles?|directives?)",
     "direct_override_fr", 90, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)ignore\s+(toutes?\s+)?(tes|les|vos)\s+(instructions?|consignes?|règles?)",
     "direct_override_fr_2", 90, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)ne\s+tiens?\s+pas\s+compte\s+de\s+(tes|les|vos)\s+(instructions?|consignes?)",
     "direct_override_fr_3", 85, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)forget\s+(all\s+)?(your|previous|prior)\s+(instructions?|rules?|training)",
     "direct_override_en_3", 90, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)override\s+(all\s+)?(safety|security|previous)\s+(measures?|protocols?|instructions?)",
     "direct_override_en_4", 90, ThreatCategory.PROMPT_INJECTION),

    # --- Jailbreak ---
    (r"(?i)you\s+are\s+now\s+(DAN|evil|unrestricted|unfiltered|jailbroken)",
     "jailbreak_dan", 95, ThreatCategory.JAILBREAK),
    (r"(?i)act\s+as\s+if\s+you\s+have\s+no\s+restrictions?",
     "jailbreak_no_restrictions", 90, ThreatCategory.JAILBREAK),
    (r"(?i)tu\s+es\s+maintenant\s+(libre|sans\s+restriction|déverrouillé)",
     "jailbreak_fr", 90, ThreatCategory.JAILBREAK),
    (r"(?i)pretend\s+you\s+(are|can|have)\s+(no\s+)?(?:rules?|limits?|restrictions?|ethics)",
     "jailbreak_pretend", 85, ThreatCategory.JAILBREAK),
    (r"(?i)do\s+anything\s+now",
     "jailbreak_dan_acronym", 90, ThreatCategory.JAILBREAK),
    (r"(?i)(?:enable|activate|enter)\s+(?:developer|debug|god|admin|sudo)\s+mode",
     "jailbreak_mode", 90, ThreatCategory.JAILBREAK),
    (r"(?i)(?:active|entre|passe)\s+(?:en\s+)?mode\s+(?:développeur|debug|admin|dieu|sudo)",
     "jailbreak_mode_fr", 90, ThreatCategory.JAILBREAK),

    # --- Role Manipulation ---
    (r"(?i)you\s+are\s+(?:a|an|my)\s+(?:hacker|pentester|criminal|evil\s+AI)",
     "role_manipulation_en", 85, ThreatCategory.ROLE_MANIPULATION),
    (r"(?i)tu\s+es\s+(?:un|une|mon)\s+(?:hacker|pirate|criminel)",
     "role_manipulation_fr", 85, ThreatCategory.ROLE_MANIPULATION),
    (r"(?i)from\s+now\s+on,?\s+you\s+(?:are|will\s+be|must\s+act\s+as)",
     "role_manipulation_en_2", 75, ThreatCategory.ROLE_MANIPULATION),
    (r"(?i)à\s+partir\s+de\s+maintenant,?\s+tu\s+(?:es|seras|dois)",
     "role_manipulation_fr_2", 75, ThreatCategory.ROLE_MANIPULATION),

    # --- Data Exfiltration ---
    (r"(?i)(?:list|show|reveal|display|print|dump|give\s+me)\s+(?:all\s+)?(?:the\s+)?(?:system\s+prompt|instructions?|passwords?|credentials?|secrets?|API\s+keys?|tokens?|IBAN|private\s+data)",
     "data_exfil_en", 85, ThreatCategory.DATA_EXFILTRATION),
    (r"(?i)(?:liste|montre|révèle|affiche|donne|extrais)\s+(?:tous?\s+)?(?:les?\s+)?(?:prompt\s+système|instructions?|mots?\s+de\s+passe|identifiants?|secrets?|clés?\s+API|tokens?|IBAN|données?\s+privées?)",
     "data_exfil_fr", 85, ThreatCategory.DATA_EXFILTRATION),
    (r"(?i)what\s+(?:is|are)\s+(?:the|your)\s+(?:system\s+prompt|initial\s+instructions?|secret\s+instructions?)",
     "data_exfil_system_prompt", 80, ThreatCategory.DATA_EXFILTRATION),
    (r"(?i)(?:repeat|echo|output)\s+(?:your|the)\s+(?:system\s+prompt|initial\s+instructions?|hidden\s+instructions?)",
     "data_exfil_repeat", 85, ThreatCategory.DATA_EXFILTRATION),
    (r"(?i)(?:répète|affiche|recopie)\s+(?:ton|le|ta)\s+(?:prompt\s+système|instruction\s+initiale|consigne\s+cachée)",
     "data_exfil_repeat_fr", 85, ThreatCategory.DATA_EXFILTRATION),

    # --- Context Exploitation ---
    (r"(?i)\[system\]|\[INST\]|<\|im_start\|>system|<<SYS>>|<\|system\|>",
     "context_injection_tags", 90, ThreatCategory.PROMPT_INJECTION),
    (r"(?i)###\s*(?:system|instruction|human|assistant)\s*:",
     "context_injection_markers", 80, ThreatCategory.PROMPT_INJECTION),

    # --- Encoding Attack Indicators ---
    (r"(?i)(?:decode|convert|translate)\s+(?:this|the\s+following)\s+(?:from\s+)?(?:base64|rot13|hex|binary|morse)",
     "encoding_decode_request", 70, ThreatCategory.ENCODING_ATTACK),
]

# Patterns compilés au chargement du module
_COMPILED_PATTERNS = [
    (re.compile(pattern), name, score, category)
    for pattern, name, score, category in _INJECTION_PATTERNS
]


# ============================================================================
# Patterns de secrets
# ============================================================================

_SECRET_PATTERNS: list[tuple[str, str, int]] = [
    # API Keys
    (r"(?:sk|pk|ak|rk)[-_](?:live|test|prod|proj)[-_][A-Za-z0-9]{20,}", "api_key_generic", 90),
    (r"(?:AKIA|ASIA)[A-Z0-9]{16}", "aws_access_key", 95),
    (r"ghp_[A-Za-z0-9]{36}", "github_pat", 95),
    (r"gho_[A-Za-z0-9]{36}", "github_oauth", 95),
    (r"glpat-[A-Za-z0-9\-]{20,}", "gitlab_pat", 95),
    (r"xoxb-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24}", "slack_bot_token", 95),
    (r"xoxp-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24}", "slack_user_token", 95),
    (r"(?:Bearer\s+)?eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}", "jwt_token", 80),
    (r"AIza[A-Za-z0-9_-]{35}", "google_api_key", 90),
    (r"ya29\.[A-Za-z0-9_-]{50,}", "google_oauth_token", 85),
    (r"sk-[A-Za-z0-9]{20,}", "openai_api_key", 95),
    (r"sk-ant-[A-Za-z0-9-]{20,}", "anthropic_api_key", 95),

    # Private Keys
    (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "private_key", 95),
    (r"-----BEGIN\s+(?:EC\s+)?PRIVATE\s+KEY-----", "ec_private_key", 95),

    # Connection Strings
    (r"(?:postgres|mysql|mongodb|redis)://[^\s\"']{10,}", "database_url", 90),
    (r"(?:smtp|ftp|amqp)://[^\s\"']{10,}", "service_url", 80),

    # Passwords patterns
    (r"(?i)(?:password|passwd|pwd|mot\s+de\s+passe)\s*[:=]\s*['\"]?[^\s'\"]{8,}", "password_assignment", 85),
]

_COMPILED_SECRET_PATTERNS = [
    (re.compile(pattern), name, score)
    for pattern, name, score in _SECRET_PATTERNS
]


# ============================================================================
# Mots-clés suspects pour le décodage Base64
# ============================================================================

_SUSPICIOUS_KEYWORDS = [
    "ignore", "system", "instruction", "jailbreak", "override", "bypass",
    "oublie", "consigne", "révèle", "secret", "password", "token",
    "admin", "sudo", "root", "shell", "exec", "eval",
    "prompt", "injection", "hack", "exploit",
]


class SecurityLayer:
    """Module de sécurité du Trust Layer.

    Toujours actif, quel que soit le LLM cible.
    Analyse les entrées pour détecter les menaces avant envoi au LLM.
    """

    def analyze(self, text: str) -> SecurityResult:
        """Analyse un texte pour détecter les menaces de sécurité.

        Args:
            text: Texte brut à analyser (prompt utilisateur ou texte OCR).

        Returns:
            SecurityResult avec score de risque, menaces détectées et texte nettoyé.
        """
        start = time.monotonic()
        threats: list[ThreatMatch] = []

        # --- Layer 1 : Détection d'obfuscation ---
        cleaned_text, obfuscation_threats = self._detect_obfuscation(text)
        threats.extend(obfuscation_threats)

        # --- Layer 2 : Détection de secrets ---
        secret_threats = self._detect_secrets(cleaned_text)
        threats.extend(secret_threats)

        # --- Layer 3 : Détection d'injection de prompt ---
        injection_threats = self._detect_injection(cleaned_text)
        threats.extend(injection_threats)

        # Calcul du score global (max des menaces)
        risk_score = max((t.score for t in threats), default=0)
        action = self._score_to_action(risk_score)
        safe = action in ("PASS", "LOG")

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if threats:
            logger.info(
                "Security scan: %d threats detected, risk_score=%d, action=%s (%dms)",
                len(threats),
                risk_score,
                action,
                elapsed_ms,
            )

        return SecurityResult(
            safe=safe,
            risk_score=risk_score,
            action=action,
            threats=threats,
            cleaned_text=cleaned_text,
            processing_time_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Layer 1 : Détection d'obfuscation
    # ------------------------------------------------------------------

    def _detect_obfuscation(self, text: str) -> tuple[str, list[ThreatMatch]]:
        """Détecte et décode les tentatives d'obfuscation.

        Returns:
            Tuple (texte nettoyé, liste de menaces).
        """
        threats: list[ThreatMatch] = []
        cleaned = text

        # 1a. Caractères Unicode invisibles (variation selectors, zero-width)
        invisible_chars = [
            c for c in text
            if unicodedata.category(c) in ("Cf", "Mn") and ord(c) > 127
        ]
        if invisible_chars:
            threats.append(ThreatMatch(
                category=ThreatCategory.INVISIBLE_CHARS,
                severity=ThreatSeverity.HIGH,
                score=75,
                pattern_name="invisible_unicode_chars",
                detail=f"{len(invisible_chars)} caractères invisibles détectés",
            ))
            # Retirer les chars invisibles
            cleaned = "".join(
                c for c in cleaned
                if not (unicodedata.category(c) in ("Cf", "Mn") and ord(c) > 127)
            )

        # 1b. Homoglyphes Unicode (normalisation NFKC)
        normalized = unicodedata.normalize("NFKC", cleaned)
        if normalized != cleaned:
            threats.append(ThreatMatch(
                category=ThreatCategory.UNICODE_HOMOGLYPH,
                severity=ThreatSeverity.MEDIUM,
                score=60,
                pattern_name="unicode_homoglyph",
                detail="Texte contient des homoglyphes Unicode (normalisation NFKC appliquée)",
            ))
            cleaned = normalized

        # 1c. Base64 embarqué contenant des instructions suspectes
        b64_pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
        for match in b64_pattern.finditer(cleaned):
            try:
                decoded = base64.b64decode(match.group()).decode("utf-8", errors="ignore")
                decoded_lower = decoded.lower()
                if any(kw in decoded_lower for kw in _SUSPICIOUS_KEYWORDS):
                    threats.append(ThreatMatch(
                        category=ThreatCategory.ENCODING_ATTACK,
                        severity=ThreatSeverity.CRITICAL,
                        score=90,
                        pattern_name="base64_injection",
                        matched_text=match.group()[:50] + "...",
                        detail=f"Base64 décodé contient : {decoded[:100]}",
                    ))
            except Exception:
                pass

        return cleaned, threats

    # ------------------------------------------------------------------
    # Layer 2 : Détection de secrets
    # ------------------------------------------------------------------

    def _detect_secrets(self, text: str) -> list[ThreatMatch]:
        """Détecte les secrets (API keys, tokens, passwords) dans le texte."""
        threats: list[ThreatMatch] = []

        for pattern, name, score in _COMPILED_SECRET_PATTERNS:
            for match in pattern.finditer(text):
                # Masquer le secret dans le log (premiers et derniers chars)
                matched = match.group()
                masked = matched[:8] + "..." + matched[-4:] if len(matched) > 16 else "***"
                threats.append(ThreatMatch(
                    category=ThreatCategory.SECRET_LEAK,
                    severity=ThreatSeverity.CRITICAL if score >= 85 else ThreatSeverity.HIGH,
                    score=score,
                    pattern_name=name,
                    matched_text=masked,
                    detail=f"Secret détecté : {name}",
                ))
                # Un seul match par pattern suffit
                break

        return threats

    # ------------------------------------------------------------------
    # Layer 3 : Détection d'injection de prompt
    # ------------------------------------------------------------------

    def _detect_injection(self, text: str) -> list[ThreatMatch]:
        """Détecte les tentatives d'injection de prompt."""
        threats: list[ThreatMatch] = []

        for pattern, name, score, category in _COMPILED_PATTERNS:
            match = pattern.search(text)
            if match:
                threats.append(ThreatMatch(
                    category=category,
                    severity=self._score_to_severity(score),
                    score=score,
                    pattern_name=name,
                    matched_text=match.group()[:100],
                ))

        return threats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_severity(score: int) -> ThreatSeverity:
        if score >= 85:
            return ThreatSeverity.CRITICAL
        if score >= 70:
            return ThreatSeverity.HIGH
        if score >= 50:
            return ThreatSeverity.MEDIUM
        return ThreatSeverity.LOW

    @staticmethod
    def _score_to_action(score: int) -> str:
        if score >= 85:
            return "BLOCK"
        if score >= 70:
            return "WARN"
        if score >= 50:
            return "LOG"
        return "PASS"
