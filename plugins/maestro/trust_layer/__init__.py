"""Trust Layer — Sécurité IA et Confidentialité des données.

Deux modules indépendants :
- security : TOUJOURS actif (injection, secrets, obfuscation)
- confidentiality : actif uniquement si LLM externe (anonymisation, tokenisation)
"""

from .confidentiality import ConfidentialityLayer, ConfidentialityResult
from .orchestrator import TrustLayer, TrustLayerConfig, TrustLayerResult
from .security import SecurityLayer, SecurityResult, ThreatSeverity

__all__ = [
    "ConfidentialityLayer",
    "ConfidentialityResult",
    "SecurityLayer",
    "SecurityResult",
    "ThreatSeverity",
    "TrustLayer",
    "TrustLayerConfig",
    "TrustLayerResult",
]
