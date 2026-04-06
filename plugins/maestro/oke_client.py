"""OKE API Client — authenticated HTTP client for OKE backend."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


class OkeClient:
    """HTTP client for OKE API with tenant-scoped authentication."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OKE_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("OKE_API_KEY", "")
        self.tenant_id = tenant_id or os.getenv("OKE_TENANT_ID", "")
        self.company_id = company_id or os.getenv("OKE_COMPANY_ID", "")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=_DEFAULT_TIMEOUT,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self.tenant_id:
            h["X-Tenant-ID"] = self.tenant_id
        return h

    def get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: Optional[dict] = None) -> dict[str, Any]:
        resp = self._client.post(path, json=body or {})
        resp.raise_for_status()
        return resp.json()

    def patch(self, path: str, body: Optional[dict] = None) -> dict[str, Any]:
        resp = self._client.patch(path, json=body or {})
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()


# Singleton
_instance: Optional[OkeClient] = None


def get_client() -> OkeClient:
    global _instance
    if _instance is None:
        _instance = OkeClient()
    return _instance
