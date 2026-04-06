"""Trust Layer — Orchestrateur.

Décide quels modules activer selon le provider LLM :
- LLM local (Ollama/Gemma) → Security ON, Confidentiality OFF
- LLM externe (Claude/GPT/Gemini API) → Security ON, Confidentiality ON

Module identique CLI et Cloud.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from .confidentiality import ConfidentialityLayer, ConfidentialityResult
from .security import SecurityLayer, SecurityResult

logger = logging.getLogger(__name__)

LOCAL_PROVIDERS = frozenset({"ollama", "local"})
EU_PROVIDERS = frozenset({"vertex_gemini", "vertex_claude", "mistral"})


@dataclass
class TrustLayerConfig:
    force_confidentiality: bool = False
    skip_confidentiality: bool = False
    block_on_threat: bool = True
    language: str = "fr"


@dataclass
class TrustLayerResult:
    text: str
    security: SecurityResult = field(default_factory=SecurityResult)
    confidentiality: ConfidentialityResult = field(default_factory=ConfidentialityResult)
    blocked: bool = False
    block_reason: str = ""
    total_processing_time_ms: int = 0

    @property
    def entity_map(self) -> dict[str, dict]:
        return self.confidentiality.entity_map


class TrustLayer:
    """Orchestrateur Security + Confidentiality. Identique CLI et Cloud."""

    def __init__(self, tenant_id: Optional[UUID] = None, session_key: str = "") -> None:
        self.tenant_id = tenant_id
        self.session_key = session_key or f"session-{id(self)}"
        self._security = SecurityLayer()
        self._confidentiality = ConfidentialityLayer(tenant_id=tenant_id, session_key=self.session_key)

    async def process(self, text: str, provider: str = "ollama", config: TrustLayerConfig | None = None) -> TrustLayerResult:
        start = time.monotonic()
        cfg = config or TrustLayerConfig()

        security_result = self._security.analyze(text)

        if cfg.block_on_threat and security_result.action == "BLOCK":
            elapsed_ms = int((time.monotonic() - start) * 1000)
            threat_names = ", ".join(t.pattern_name for t in security_result.threats)
            return TrustLayerResult(text="", security=security_result,
                confidentiality=ConfidentialityLayer.skip(text, "Bloqué par Security"),
                blocked=True, block_reason=f"Menace : {threat_names}", total_processing_time_ms=elapsed_ms)

        working_text = security_result.cleaned_text or text
        needs_conf = self._needs_confidentiality(provider, cfg)

        if needs_conf:
            conf_result = await self._confidentiality.anonymize(text=working_text, language=cfg.language)
            final_text = conf_result.anonymized_text
        else:
            conf_result = ConfidentialityLayer.skip(working_text, self._skip_reason(provider, cfg))
            final_text = working_text

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return TrustLayerResult(text=final_text, security=security_result, confidentiality=conf_result, total_processing_time_ms=elapsed_ms)

    async def deanonymize(self, text: str, entity_map: dict[str, dict]) -> str:
        if not entity_map:
            return text
        return await self._confidentiality.deanonymize(text=text, entity_map=entity_map)

    @staticmethod
    def _needs_confidentiality(provider: str, config: TrustLayerConfig) -> bool:
        if config.force_confidentiality: return True
        if config.skip_confidentiality: return False
        if provider.lower() in LOCAL_PROVIDERS: return False
        if provider.lower() in EU_PROVIDERS: return False
        return True

    @staticmethod
    def _skip_reason(provider: str, config: TrustLayerConfig) -> str:
        if config.skip_confidentiality: return "Désactivé par configuration"
        if provider.lower() in LOCAL_PROVIDERS: return f"LLM local ({provider})"
        if provider.lower() in EU_PROVIDERS: return f"LLM EU ({provider})"
        return "Non requis"
