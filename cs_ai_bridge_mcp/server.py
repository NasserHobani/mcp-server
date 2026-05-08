from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastmcp import FastMCP


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def _load_extra_headers() -> dict[str, str]:
    raw = os.getenv("CS_AI_BRIDGE_HEADERS_JSON", "").strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("CS_AI_BRIDGE_HEADERS_JSON must be a JSON object.")
    return {str(k): str(v) for k, v in parsed.items()}


def _load_cookie_header() -> dict[str, str]:
    cookie = os.getenv("CS_AI_BRIDGE_COOKIE", "").strip()
    if not cookie:
        return {}
    return {"Cookie": cookie}


def _load_odoo_credentials() -> dict[str, str] | None:
    email = os.getenv("CS_AI_BRIDGE_ODOO_EMAIL", "").strip()
    db_name = os.getenv("CS_AI_BRIDGE_ODOO_DB_NAME", "").strip()
    password = os.getenv("CS_AI_BRIDGE_ODOO_PASSWORD", "").strip()
    if not email or not db_name or not password:
        return None
    return {"email": email, "db_name": db_name, "password": password}


def _authenticate_odoo(client: httpx.Client, base_url: str) -> None:
    creds = _load_odoo_credentials()
    if creds is None:
        return

    response = client.post(
        f"{base_url}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": creds["db_name"],
                "login": creds["email"],
                "password": creds["password"],
            },
        },
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Odoo authentication response must be a JSON object.")
    result = body.get("result", {})
    if not isinstance(result, dict) or not result.get("uid"):
        raise ValueError("Odoo authentication failed. Check email/db/password.")


def _request(
    endpoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    base_url = _normalize_base_url(
        os.getenv("CS_AI_BRIDGE_BASE_URL", "http://localhost:8069")
    )
    timeout_seconds = float(os.getenv("CS_AI_BRIDGE_TIMEOUT", "30"))

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    headers.update(_load_cookie_header())
    headers.update(_load_extra_headers())

    with httpx.Client(timeout=timeout_seconds) as client:
        # If no explicit cookie was provided, try credential login to create session.
        if "Cookie" not in headers:
            _authenticate_odoo(client, base_url)
        response = client.post(f"{base_url}{endpoint}", json=payload, headers=headers)
        response.raise_for_status()

    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("API response must be a JSON object.")
    return data


mcp = FastMCP("cs-ai-bridge")


@mcp.tool(
    name="mcp_query",
    description=(
        "Read real-time Odoo records from /cs_ai_bridge/mcp/query "
        "using model/domain/fields hints."
    ),
)
def mcp_query(
    model: str,
    tenant: str | None = None,
    domain: list[Any] | None = None,
    fields: list[str] | None = None,
    limit: int = 80,
    order: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "limit": limit}
    if tenant is not None:
        payload["tenant"] = tenant
    if domain is not None:
        payload["domain"] = domain
    if fields is not None:
        payload["fields"] = fields
    if order is not None:
        payload["order"] = order

    return _request("/cs_ai_bridge/mcp/query", payload)


@mcp.tool(
    name="ai_query",
    description=(
        "Send natural-language prompt to /cs_ai_bridge/ai/query and let "
        "the bridge route between mcp/rag/hybrid."
    ),
)
def ai_query(
    query: str,
    tenant: str | None = None,
    route: str = "auto",
    model: str | None = None,
    domain: list[Any] | None = None,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query, "route": route}
    if tenant is not None:
        payload["tenant"] = tenant
    if model is not None:
        payload["model"] = model
    if domain is not None:
        payload["domain"] = domain
    if fields is not None:
        payload["fields"] = fields

    return _request("/cs_ai_bridge/ai/query", payload)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
