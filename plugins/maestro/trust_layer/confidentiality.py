"""Trust Layer — Module Confidentialité (ACTIF SI LLM EXTERNE).

Anonymise les PII avant envoi au LLM externe.
Utilise Presidio si disponible (OKE Cloud), sinon fallback sur le trust
layer regex de maestro_core (CLI).

Désactivé quand le LLM est local (Gemma, Ollama) car les données
ne quittent pas le serveur.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ConfidentialityResult:
    """Résultat de l'anonymisation."""

    anonymized_text: str
    entity_map: dict[str, dict] = field(default_factory=dict)
    entities_found: int = 0
    processing_time_ms: int = 0
    skipped: bool = False
    skip_reason: str = ""


class ConfidentialityLayer:
    """Module de confidentialité du Trust Layer.

    Actif uniquement quand les données quittent le périmètre souverain.
    Utilise Presidio (OKE) ou le trust regex (CLI) selon la disponibilité.
    """

    def __init__(self, tenant_id: Optional[UUID] = None, session_key: str = "") -> None:
        self.tenant_id = tenant_id
        self.session_key = session_key
        self._presidio_anonymizer = None
        self._regex_anonymizer = None

        # Try Presidio first (OKE Cloud)
        try:
            from services.privacy.anonymizer import TextAnonymizer
            self._presidio_anonymizer = TextAnonymizer(
                tenant_id=tenant_id,
                session_key=session_key,
            )
            logger.debug("Confidentiality: using Presidio anonymizer")
        except ImportError:
            pass

        # Fallback to maestro_core regex anonymizer (CLI)
        if self._presidio_anonymizer is None:
            try:
                from maestro_core.trust.anonymizer import Anonymizer, TrustMode
                self._regex_anonymizer = Anonymizer(TrustMode.FULL)
                logger.debug("Confidentiality: using regex anonymizer (fallback)")
            except ImportError:
                logger.warning("Confidentiality: no anonymizer available")

    async def anonymize(self, text: str, language: str = "fr") -> ConfidentialityResult:
        """Anonymise le texte en remplaçant les PII."""
        start = time.monotonic()

        if self._presidio_anonymizer:
            result = await self._presidio_anonymizer.anonymize(text=text, language=language)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ConfidentialityResult(
                anonymized_text=result.anonymized_text,
                entity_map=result.entity_map,
                entities_found=result.entities_found,
                processing_time_ms=elapsed_ms,
            )

        if self._regex_anonymizer:
            anonymized = self._regex_anonymizer.anonymize_text(text)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            # Build entity map from vault
            entity_map = {}
            for entry in self._regex_anonymizer.vault.entries:
                entity_map[entry.placeholder] = {
                    "original": entry.original,
                    "category": entry.category.value,
                }
            return ConfidentialityResult(
                anonymized_text=anonymized,
                entity_map=entity_map,
                entities_found=len(entity_map),
                processing_time_ms=elapsed_ms,
            )

        return self.skip(text, reason="Aucun anonymizer disponible")

    async def deanonymize(self, text: str, entity_map: dict[str, dict]) -> str:
        """Dé-anonymise le texte."""
        if self._presidio_anonymizer:
            return await self._presidio_anonymizer.deanonymize(text=text, entity_map=entity_map)

        if self._regex_anonymizer:
            return self._regex_anonymizer.deanonymize_text(text)

        # Manual deanonymization from entity_map
        result = text
        for placeholder, meta in entity_map.items():
            original = meta.get("original", placeholder)
            result = result.replace(placeholder, original)
        return result

    @staticmethod
    def skip(text: str, reason: str = "LLM local") -> ConfidentialityResult:
        """Retourne un résultat skip (module désactivé)."""
        logger.debug("Confidentiality skipped: %s", reason)
        return ConfidentialityResult(
            anonymized_text=text,
            skipped=True,
            skip_reason=reason,
        )
