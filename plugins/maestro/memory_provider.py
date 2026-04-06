"""OKE Memory Provider for Hermes Agent.

Provides accounting-aware context by fetching relevant company data
from OKE before each agent turn, and persisting decisions after sessions.

Implements the Hermes Memory Provider Plugin interface:
- prefetch(user_message, session_id) → context string
- sync(conversation_history, session_id) → None
- extract(session_id) → None
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OkeMemoryProvider:
    """Hermes Memory Provider connected to OKE backend."""

    name = "oke"

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}
        self._client = None
        self._company_cache: dict[str, Any] = {}
        logger.info("OKE Memory Provider initialized")

    def _get_client(self):
        if self._client is None:
            from .oke_client import OkeClient
            self._client = OkeClient()
        return self._client

    def _get_company_context(self) -> str:
        """Fetch active company info from OKE."""
        company_id = os.getenv("OKE_COMPANY_ID", "")
        if not company_id:
            return ""

        if company_id in self._company_cache:
            return self._company_cache[company_id]

        try:
            client = self._get_client()
            # Fetch company basics
            info_parts = []

            # Try to get dashboard for quick overview
            try:
                dashboard = client.get(f"/payroll/dashboard/{company_id}")
                if dashboard:
                    info_parts.append(
                        f"Tableau de bord paie: "
                        f"{dashboard.get('employee_count', '?')} salaries, "
                        f"masse salariale: {dashboard.get('total_gross', '?')} EUR"
                    )
            except Exception:
                pass

            # Try to get fiscal alerts
            try:
                alerts = client.post(f"/fiscal/alerts/company/{company_id}/scan")
                if alerts and isinstance(alerts, list) and len(alerts) > 0:
                    critical = [a for a in alerts if a.get("priority") == "critical"]
                    if critical:
                        info_parts.append(
                            f"ALERTES FISCALES: {len(critical)} alerte(s) critique(s)"
                        )
            except Exception:
                pass

            context = "\n".join(info_parts) if info_parts else ""
            self._company_cache[company_id] = context
            return context

        except Exception as e:
            logger.warning("OKE Memory Provider: failed to fetch company context: %s", e)
            return ""

    def prefetch(self, user_message: str = "", session_id: str = "", **kwargs) -> str:
        """Called before each agent turn. Returns context to inject.

        Analyzes the user message to fetch relevant OKE data:
        - Mentions of 'paie/bulletins/salarie' → payroll context
        - Mentions of 'TVA/fiscal/declaration' → fiscal context
        - Mentions of 'balance/bilan/ecriture' → accounting context
        - Always includes company overview if available
        """
        if not os.getenv("OKE_API_URL"):
            return ""

        context_parts = []

        # Company overview (cached)
        company_ctx = self._get_company_context()
        if company_ctx:
            context_parts.append(f"[Contexte OKE]\n{company_ctx}")

        # Keyword-based context enrichment
        msg_lower = user_message.lower() if user_message else ""

        if any(kw in msg_lower for kw in ("paie", "bulletin", "salari", "dsn", "cotisation")):
            context_parts.append("[Mode: Paie — utilise les tools oke_* pour la paie]")

        if any(kw in msg_lower for kw in ("tva", "fiscal", "liasse", "declaration", "dgfip")):
            context_parts.append("[Mode: Fiscal — utilise les tools oke_* pour le fiscal]")

        if any(kw in msg_lower for kw in ("balance", "bilan", "ecriture", "journal", "lettrage", "grand livre")):
            context_parts.append("[Mode: Comptabilite — utilise les tools oke_* pour la compta]")

        return "\n".join(context_parts) if context_parts else ""

    def sync(self, conversation_history: list = None, session_id: str = "", **kwargs) -> None:
        """Called after each agent response. Persist decisions if needed."""
        # Future: extract validated entries, decisions from conversation
        # and persist them in OKE audit trail
        pass

    def extract(self, session_id: str = "", **kwargs) -> None:
        """Called at session end. Final cleanup."""
        # Clear company cache at session end
        self._company_cache.clear()

    def get_tools(self) -> list[dict]:
        """Return additional memory-specific tools (optional)."""
        return []

    def get_status(self) -> dict:
        """Return provider status for hermes memory status."""
        return {
            "name": "oke",
            "active": bool(os.getenv("OKE_API_URL")),
            "company_id": os.getenv("OKE_COMPANY_ID", "not set"),
            "cache_size": len(self._company_cache),
        }
