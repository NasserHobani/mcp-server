"""MCP tools: schema metadata, Odoo mcp/query, Odoo ai/query."""

from __future__ import annotations

from typing import Any

from . import config
from . import llm_client
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
    name="mcp_create",
    description=(
        "Create one Odoo record via POST /cs_ai_bridge/mcp/create "
        "(requires Allow Create + whitelisted writable fields). "
        "Invoices typically need invoice_line_ids with Odoo Command tuples."
    ),
)
def mcp_create(
    model: str,
    vals: dict[str, Any],
    tenant: str | None = None,
    reuse_cached_schema: bool = False,
    validate_with_schema: bool | None = None,
) -> dict[str, Any]:
    schema_redis.maybe_start_schema_helpers()
    t_schema = schema_redis.tenant_for_schema_hints(tenant)

    validation_on = validate_with_schema
    if validation_on is None:
        validation_on = schema_validation.ai_hints_validation_enabled(None)

    if validation_on and config.redis_url_configured() and t_schema:
        use_cache = schema_validation.normalize_ai_reuse_cached(reuse_cached_schema)
        if not use_cache:
            schema_redis.invalidate_schema_cache_tenant(t_schema)
        cached = schema_redis.get_cached_schema(t_schema) if use_cache else None
        snapshot = cached or schema_redis.read_schema_metadata(t_schema)
        schema_redis.put_cached_schema(t_schema, snapshot)
        schema_validation.validate_create_vals_with_schema(
            snapshot,
            tenant=t_schema,
            model=model,
            vals=vals,
        )

    payload: dict[str, Any] = {"model": model, "vals": vals}
    if tenant is not None:
        payload["tenant"] = tenant
    return odoo_client.post_json("/cs_ai_bridge/mcp/create", payload)


@mcp.tool(
    name="mcp_write",
    description=(
        "Update one record via POST /cs_ai_bridge/mcp/write "
        "(Allow Write + whitelisted writable fields per schema mutation)."
    ),
)
def mcp_write(
    model: str,
    record_id: int,
    vals: dict[str, Any],
    tenant: str | None = None,
    reuse_cached_schema: bool = False,
    validate_with_schema: bool | None = None,
) -> dict[str, Any]:
    schema_redis.maybe_start_schema_helpers()
    t_schema = schema_redis.tenant_for_schema_hints(tenant)

    validation_on = validate_with_schema
    if validation_on is None:
        validation_on = schema_validation.ai_hints_validation_enabled(None)

    if validation_on and config.redis_url_configured() and t_schema:
        use_cache = schema_validation.normalize_ai_reuse_cached(reuse_cached_schema)
        if not use_cache:
            schema_redis.invalidate_schema_cache_tenant(t_schema)
        cached = schema_redis.get_cached_schema(t_schema) if use_cache else None
        snapshot = cached or schema_redis.read_schema_metadata(t_schema)
        schema_redis.put_cached_schema(t_schema, snapshot)
        schema_validation.validate_write_vals_with_schema(
            snapshot,
            tenant=t_schema,
            model=model,
            vals=vals,
        )

    payload: dict[str, Any] = {"model": model, "record_id": record_id, "vals": vals}
    if tenant is not None:
        payload["tenant"] = tenant
    return odoo_client.post_json("/cs_ai_bridge/mcp/write", payload)


@mcp.tool(
    name="llm_chat_completion",
    description=(
        "Call the configured AI model through the CS AI Bridge LLM API. "
        "Redis AI config is selected by tenant when provided."
    ),
)
def llm_chat_completion(
    prompt: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    tenant: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    extra_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if messages is None:
        if prompt is None or not prompt.strip():
            raise ValueError("Provide either 'messages' or a non-empty 'prompt'.")
        messages = [{"role": "user", "content": prompt}]
    elif not messages:
        raise ValueError("'messages' must not be empty.")

    payload: dict[str, Any] = dict(extra_body or {})
    payload["messages"] = messages
    if tenant is not None:
        payload["tenant"] = tenant
    if provider is not None:
        payload["provider"] = provider
    if model is not None:
        payload["model"] = model
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    return llm_client.chat_completion(payload)


@mcp.tool(
    name="ai_query",
    description=(
        "POST /cs_ai_bridge/ai/query. For MCP mutation use route=mcp with action "
        "'create' or 'write', non-empty values, plus record_id when writing. "
        "Otherwise MCP runs search_read."
    ),
)
def ai_query(
    query: str,
    tenant: str | None = None,
    route: str = "auto",
    model: str | None = None,
    domain: list[Any] | None = None,
    fields: list[str] | None = None,
    action: str | None = None,
    values: dict[str, Any] | None = None,
    record_id: int | None = None,
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

        validation_on = schema_validation.ai_hints_validation_enabled(
            validate_hints_with_schema
        )

        act = (action or "").strip().lower()
        creating = (
            act == "create"
            and isinstance(values, dict)
            and len(values) > 0
            and model is not None
        )
        writing = (
            act == "write"
            and isinstance(values, dict)
            and len(values) > 0
            and model is not None
            and record_id is not None
        )
        if validation_on and creating:
            schema_validation.validate_create_vals_with_schema(
                snapshot,
                tenant=t_schema,
                model=model,
                vals=values,
            )
        elif validation_on and writing:
            schema_validation.validate_write_vals_with_schema(
                snapshot,
                tenant=t_schema,
                model=model,
                vals=values,
            )
        elif validation_on and (model or fields or domain):
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
    if action is not None:
        payload["action"] = action
    if values is not None:
        payload["values"] = values
    if record_id is not None:
        payload["record_id"] = record_id

    return odoo_client.post_json("/cs_ai_bridge/ai/query", payload)
