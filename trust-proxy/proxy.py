"""Trust Proxy — FastAPI micro-service between Hermes Agent and cloud LLM providers.

Handles security scanning (prompt injection, secret detection) and PII
anonymization before forwarding requests to OpenAI / Anthropic APIs.

Run: uvicorn proxy:app --port 8888
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from confidentiality import ConfidentialityLayer
from security import Action, SecurityScanner

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("trust-proxy")

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
scanner = SecurityScanner()
confidentiality = ConfidentialityLayer()

OPENAI_BASE = "https://api.openai.com"
ANTHROPIC_BASE = "https://api.anthropic.com"

# Providers considered "local" (no anonymization needed)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"}


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    log.info("Trust proxy started on port 8888")
    yield
    await app.state.client.aclose()
    log.info("Trust proxy stopped")


app = FastAPI(title="Hermes Trust Proxy", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_local(url: str) -> bool:
    """Return True if the target URL points to a local/ollama provider."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return hostname in LOCAL_HOSTS


def _extract_user_text_openai(body: dict) -> str:
    """Concatenate all user message contents from an OpenAI-style payload."""
    parts = []
    for msg in body.get("messages", []):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block["text"])
    return "\n".join(parts)


def _extract_user_text_anthropic(body: dict) -> str:
    """Concatenate all user message contents from an Anthropic-style payload."""
    parts = []
    for msg in body.get("messages", []):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block["text"])
    return "\n".join(parts)


def _anonymize_messages(messages: list, entity_map_out: dict) -> list:
    """Anonymize user messages in-place, accumulate entity_map."""
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            result = confidentiality.anonymize(content)
            msg["content"] = result.anonymized_text
            entity_map_out.update(result.entity_map)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    result = confidentiality.anonymize(block["text"])
                    block["text"] = result.anonymized_text
                    entity_map_out.update(result.entity_map)
    return messages


def _deanonymize_openai_response(data: dict, entity_map: dict) -> dict:
    """Deanonymize assistant content in OpenAI response."""
    if not entity_map:
        return data
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content")
        if content and isinstance(content, str):
            msg["content"] = confidentiality.deanonymize(content, entity_map)
    return data


def _deanonymize_anthropic_response(data: dict, entity_map: dict) -> dict:
    """Deanonymize assistant content in Anthropic response."""
    if not entity_map:
        return data
    for block in data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            block["text"] = confidentiality.deanonymize(block["text"], entity_map)
    return data


def _resolve_target(request: Request, api_format: str) -> tuple[str, dict]:
    """Resolve target URL and auth headers for the request.

    Returns (base_url, extra_headers).
    """
    target_url = request.headers.get("X-Trust-Target-URL")
    api_key = request.headers.get("X-Trust-Api-Key")

    if target_url:
        # Explicit target — use as-is
        headers = {}
        if api_key:
            if api_format == "anthropic":
                headers["x-api-key"] = api_key
            else:
                headers["Authorization"] = f"Bearer {api_key}"
        return target_url, headers

    # Fallback: detect from env
    if api_format == "anthropic":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        return ANTHROPIC_BASE, {"x-api-key": key} if key else {}
    else:
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        return OPENAI_BASE, {"Authorization": f"Bearer {key}"} if key else {}


# ---------------------------------------------------------------------------
# Security gate (shared logic)
# ---------------------------------------------------------------------------
def _security_gate(user_text: str) -> JSONResponse | None:
    """Run security scan, return a 403 JSONResponse if blocked, else None."""
    scan = scanner.scan(user_text)

    if scan.action == Action.BLOCK:
        threat_names = [t.pattern_name for t in scan.threats]
        log.warning(
            "BLOCKED request — score=%d threats=%s", scan.risk_score, threat_names
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "message": "Request blocked by trust proxy",
                    "type": "trust_proxy_block",
                    "risk_score": scan.risk_score,
                    "threats": threat_names,
                }
            },
        )

    if scan.action == Action.WARN:
        log.warning(
            "WARN — score=%d threats=%s (continuing)",
            scan.risk_score,
            [t.pattern_name for t in scan.threats],
        )

    return None


# ---------------------------------------------------------------------------
# SSE streaming passthrough
# ---------------------------------------------------------------------------
async def _stream_sse(
    response: httpx.Response, entity_map: dict, api_format: str
):
    """Yield SSE chunks, deanonymizing text deltas on the fly."""
    async for line in response.aiter_lines():
        if not line:
            yield "\n"
            continue

        if not line.startswith("data: "):
            yield f"{line}\n"
            continue

        payload = line[6:]
        if payload.strip() == "[DONE]":
            yield f"{line}\n"
            continue

        # Deanonymize streamed deltas
        if entity_map:
            try:
                chunk = json.loads(payload)
                if api_format == "openai":
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta", {})
                        if "content" in delta and delta["content"]:
                            delta["content"] = confidentiality.deanonymize(
                                delta["content"], entity_map
                            )
                elif api_format == "anthropic":
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta" and "text" in delta:
                            delta["text"] = confidentiality.deanonymize(
                                delta["text"], entity_map
                            )
                payload = json.dumps(chunk)
            except (json.JSONDecodeError, KeyError):
                pass

        yield f"data: {payload}\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "trust-proxy"}


@app.post("/v1/chat/completions")
async def openai_proxy(request: Request):
    """Proxy for OpenAI-compatible /v1/chat/completions."""
    t0 = time.monotonic()
    body = await request.json()
    user_text = _extract_user_text_openai(body)

    # Security gate
    blocked = _security_gate(user_text)
    if blocked:
        return blocked

    # Resolve target
    base_url, auth_headers = _resolve_target(request, "openai")
    is_local = _is_local(base_url)

    # Anonymize if cloud
    entity_map: dict = {}
    if not is_local:
        body["messages"] = _anonymize_messages(body.get("messages", []), entity_map)
        if entity_map:
            log.info("Anonymized %d entities before forwarding", len(entity_map))

    # Build upstream request
    base = base_url.rstrip("/")
    target = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        **auth_headers,
    }

    is_stream = body.get("stream", False)
    client: httpx.AsyncClient = request.app.state.client

    try:
        if is_stream:
            upstream = await client.send(
                client.build_request("POST", target, json=body, headers=headers),
                stream=True,
            )
            if upstream.status_code != 200:
                error_body = await upstream.aread()
                return JSONResponse(
                    status_code=upstream.status_code,
                    content=json.loads(error_body),
                )
            return StreamingResponse(
                _stream_sse(upstream, entity_map, "openai"),
                status_code=upstream.status_code,
                media_type="text/event-stream",
            )
        else:
            resp = await client.post(target, json=body, headers=headers)
            elapsed = time.monotonic() - t0
            log.info(
                "OpenAI proxy — %s — %dms", resp.status_code, int(elapsed * 1000)
            )
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=resp.status_code, content=resp.json()
                )
            data = resp.json()
            data = _deanonymize_openai_response(data, entity_map)
            return JSONResponse(content=data)

    except httpx.ConnectError as exc:
        log.error("Connection error to %s: %s", target, exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": f"Cannot reach upstream: {exc}"}},
        )
    except httpx.ReadTimeout:
        return JSONResponse(
            status_code=504,
            content={"error": {"message": "Upstream timeout"}},
        )


@app.post("/v1/messages")
async def anthropic_proxy(request: Request):
    """Proxy for Anthropic /v1/messages."""
    t0 = time.monotonic()
    body = await request.json()
    user_text = _extract_user_text_anthropic(body)

    # Security gate
    blocked = _security_gate(user_text)
    if blocked:
        return blocked

    # Resolve target
    base_url, auth_headers = _resolve_target(request, "anthropic")
    is_local = _is_local(base_url)

    # Anonymize if cloud
    entity_map: dict = {}
    if not is_local:
        body["messages"] = _anonymize_messages(body.get("messages", []), entity_map)
        if entity_map:
            log.info("Anonymized %d entities before forwarding", len(entity_map))

    # Build upstream request
    base = base_url.rstrip("/")
    target = f"{base}/messages" if base.endswith("/v1") else f"{base}/v1/messages"

    # Anthropic requires specific headers
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": request.headers.get(
            "anthropic-version", "2023-06-01"
        ),
        **auth_headers,
    }

    is_stream = body.get("stream", False)
    client: httpx.AsyncClient = request.app.state.client

    try:
        if is_stream:
            upstream = await client.send(
                client.build_request("POST", target, json=body, headers=headers),
                stream=True,
            )
            if upstream.status_code != 200:
                error_body = await upstream.aread()
                return JSONResponse(
                    status_code=upstream.status_code,
                    content=json.loads(error_body),
                )
            return StreamingResponse(
                _stream_sse(upstream, entity_map, "anthropic"),
                status_code=upstream.status_code,
                media_type="text/event-stream",
            )
        else:
            resp = await client.post(target, json=body, headers=headers)
            elapsed = time.monotonic() - t0
            log.info(
                "Anthropic proxy — %s — %dms",
                resp.status_code,
                int(elapsed * 1000),
            )
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=resp.status_code, content=resp.json()
                )
            data = resp.json()
            data = _deanonymize_anthropic_response(data, entity_map)
            return JSONResponse(content=data)

    except httpx.ConnectError as exc:
        log.error("Connection error to %s: %s", target, exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": f"Cannot reach upstream: {exc}"}},
        )
    except httpx.ReadTimeout:
        return JSONResponse(
            status_code=504,
            content={"error": {"message": "Upstream timeout"}},
        )
