"""MCP tools: schema metadata, Odoo mcp/query, Odoo ai/query."""

from __future__ import annotations

from typing import Any

from . import config
from .app import mcp
from . import odoo_client
from . import schema_redis
from . import schema_validation


@mcp.tool(
    name="get_schema_metadata",
    description=(
        "Read tenant schema metadata JSON from Redis key "
        "`cs_ai_bridge:schema:<tenant>`."
    ),
)
def get_schema_metadata(tenant: str) -> dict[str, Any]:
    schema_redis.maybe_start_schema_helpers()
    t = tenant.strip()
    cached = schema_redis.get_cached_schema(t)
    if cached is not None:
        return cached
    snapshot = schema_redis.read_schema_metadata(t)
    schema_redis.put_cached_schema(t, snapshot)
    return snapshot


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

    return odoo_client.post_json("/cs_ai_bridge/mcp/query", payload)


@mcp.tool(
    name="ai_query",
    description=(
        "Send natural-language prompt to /cs_ai_bridge/ai/query. "
        "Loads latest MCP schema snapshot from Redis for the tenant (unless reuse_cached_schema), "
        "optionally validating model/domain/fields against that schema before forwarding to Odoo."
    ),
)
def ai_query(
    query: str,
    tenant: str | None = None,
    route: str = "auto",
    model: str | None = None,
    domain: list[Any] | None = None,
    fields: list[str] | None = None,
    reuse_cached_schema: bool = False,
    validate_hints_with_schema: bool | None = None,
) -> dict[str, Any]:
    schema_redis.maybe_start_schema_helpers()
    t_schema = schema_redis.tenant_for_schema_hints(tenant)
    if config.redis_url_configured() and t_schema:
        use_cache = schema_validation.normalize_ai_reuse_cached(reuse_cached_schema)
        if not use_cache:
            schema_redis.invalidate_schema_cache_tenant(t_schema)
        cached = schema_redis.get_cached_schema(t_schema) if use_cache else None
        snapshot = cached or schema_redis.read_schema_metadata(t_schema)
        schema_redis.put_cached_schema(t_schema, snapshot)
        if schema_validation.ai_hints_validation_enabled(
            validate_hints_with_schema
        ) and (model or fields or domain):
            schema_validation.validate_hints_with_schema(
                snapshot,
                tenant=t_schema,
                model=model,
                fields=fields or [],
                domain=domain or [],
            )

    payload: dict[str, Any] = {"query": query, "route": route}
    if tenant is not None:
        payload["tenant"] = tenant
    if model is not None:
        payload["model"] = model
    if domain is not None:
        payload["domain"] = domain
    if fields is not None:
        payload["fields"] = fields

    return odoo_client.post_json("/cs_ai_bridge/ai/query", payload)
