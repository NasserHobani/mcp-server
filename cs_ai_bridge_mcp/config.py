"""Environment-backed configuration for CS AI Bridge MCP."""

from __future__ import annotations

import json
import os


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def get_base_url() -> str:
    return normalize_base_url(
        os.getenv("CS_AI_BRIDGE_BASE_URL", "http://localhost:8069")
    )


def get_timeout_seconds() -> float:
    return float(os.getenv("CS_AI_BRIDGE_TIMEOUT", "30"))


def load_extra_headers() -> dict[str, str]:
    raw = os.getenv("CS_AI_BRIDGE_HEADERS_JSON", "").strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("CS_AI_BRIDGE_HEADERS_JSON must be a JSON object.")
    return {str(k): str(v) for k, v in parsed.items()}


def load_cookie_header() -> dict[str, str]:
    cookie = os.getenv("CS_AI_BRIDGE_COOKIE", "").strip()
    if not cookie:
        return {}
    return {"Cookie": cookie}


def redis_url() -> str | None:
    url = os.getenv("CS_AI_BRIDGE_REDIS_URL", "").strip()
    return url or None


def redis_url_configured() -> bool:
    return redis_url() is not None


def schema_key_prefix() -> str:
    return os.getenv("CS_AI_BRIDGE_SCHEMA_KEY_PREFIX", "cs_ai_bridge:schema")


def schema_key_for_tenant(tenant: str) -> str:
    return f"{schema_key_prefix()}:{tenant}"


def schema_cache_ttl_seconds() -> float:
    return float(os.getenv("CS_AI_BRIDGE_SCHEMA_CACHE_TTL_SECONDS", "0"))


def schema_pubsub_channel() -> str:
    ch = os.getenv("CS_AI_BRIDGE_REDIS_SCHEMA_CHANNEL", "odoo.mcp.schema").strip()
    return ch or "odoo.mcp.schema"


def schema_pubsub_enabled() -> bool:
    flag = os.getenv("CS_AI_BRIDGE_SCHEMA_PUBSUB", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def resolve_tenant(tenant_hint: str | None) -> str | None:
    if tenant_hint and str(tenant_hint).strip():
        return str(tenant_hint).strip()
    fallback = (
        os.getenv("CS_AI_BRIDGE_TENANT", "").strip()
        or os.getenv("CS_AI_BRIDGE_ODOO_DB_NAME", "").strip()
        or ""
    )
    return fallback or None


def ai_validate_schema_default() -> bool:
    env = os.getenv("CS_AI_BRIDGE_AI_VALIDATE_SCHEMA", "true").strip().lower()
    return env not in {"0", "false", "no", "off"}


def ai_reuse_schema_cache_from_env() -> bool:
    env = os.getenv("CS_AI_BRIDGE_AI_REUSE_SCHEMA_CACHE", "").strip().lower()
    return env in {"1", "true", "yes", "on"}
