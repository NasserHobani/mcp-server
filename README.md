# CS AI Bridge FastMCP Server

FastMCP server compatible with `cs_ai_bridge` API:

- `POST /cs_ai_bridge/mcp/query` (read / `search_read`)
- `POST /cs_ai_bridge/mcp/create` (create; requires `Allow Create` + whitelisted writable fields in Odoo)
- `POST /cs_ai_bridge/ai/query` (router): `route=mcp` still uses **read** unless the orchestrator returns `mcp_operation` / `mcp` + `operation: create` and `vals`; use **`mcp_create`** for direct creates.

## Requirements

- Python 3.10+
- Reachable Odoo instance with `cs_ai_bridge` installed
- Authenticated Odoo session (for `auth="user"` routes), usually via `session_id` cookie

## Install

```bash
cd mcp-server
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Configure

Copy `.env.example` to `.env` and fill values:

- `CS_AI_BRIDGE_BASE_URL` - Odoo base URL (default `http://localhost:8069`)
- `CS_AI_BRIDGE_TIMEOUT` - request timeout in seconds
- `CS_AI_BRIDGE_REDIS_URL` - Redis URL for schema metadata (example `redis://localhost:6379/0`)
- `CS_AI_BRIDGE_SCHEMA_KEY_PREFIX` - metadata key prefix (default `cs_ai_bridge:schema`)
- `CS_AI_BRIDGE_SCHEMA_CACHE_TTL_SECONDS` - optional in-process TTL (seconds); `0` means always bypass cache on reads that skip TTL (see tools)
- `CS_AI_BRIDGE_REDIS_SCHEMA_CHANNEL` - Redis Pub/Sub channel Odoo publishes schema on (default `odoo.mcp.schema`)
- `CS_AI_BRIDGE_SCHEMA_PUBSUB` - set `1` to subscribe and invalidate cached schema when Odoo publishes updates
- `CS_AI_BRIDGE_TENANT` - fallback tenant/database name when a tool omits `tenant`
- `CS_AI_BRIDGE_AI_VALIDATE_SCHEMA` - validate `model`/`fields`/`domain` against Redis schema before `ai_query` (`true` by default)
- `CS_AI_BRIDGE_AI_REUSE_SCHEMA_CACHE` - set `true`/`1` to allow `ai_query` to reuse a warm in-process snapshot when `CS_AI_BRIDGE_SCHEMA_CACHE_TTL_SECONDS` > 0 (default tool behavior still bypasses TTL cache unless this is enabled or `reuse_cached_schema=true` on the tool)
- `CS_AI_BRIDGE_ODOO_EMAIL` - Odoo user login email
- `CS_AI_BRIDGE_ODOO_DB_NAME` - Odoo database name
- `CS_AI_BRIDGE_ODOO_PASSWORD` - Odoo user password
- `CS_AI_BRIDGE_COOKIE` - optional raw cookie header (for Odoo session)
- `CS_AI_BRIDGE_HEADERS_JSON` - optional extra headers as JSON object

Auth precedence:

- If `CS_AI_BRIDGE_COOKIE` is set, it is used directly.
- If cookie is empty and all `CS_AI_BRIDGE_ODOO_*` values are set, server authenticates via `/web/session/authenticate` and then calls bridge endpoints.

## Run

```bash
cd mcp-server
set CS_AI_BRIDGE_BASE_URL=http://localhost:8069
set CS_AI_BRIDGE_ODOO_EMAIL=admin@example.com
set CS_AI_BRIDGE_ODOO_DB_NAME=odoo_db
set CS_AI_BRIDGE_ODOO_PASSWORD=your_password
python -m cs_ai_bridge_mcp.server
```

Or via script entrypoint after install:

```bash
cs-ai-bridge-mcp
```

## Exposed MCP tools

### `mcp_query`

Arguments:

- `model` (required)
- `tenant` (optional)
- `domain` (optional)
- `fields` (optional)
- `limit` (optional, default `80`)
- `order` (optional)

### `get_schema_metadata`

Arguments:

- `tenant` (required)

Reads Redis key `cs_ai_bridge:schema:<tenant>` (or custom prefix from `CS_AI_BRIDGE_SCHEMA_KEY_PREFIX`) and returns parsed JSON metadata.

### `mcp_create`

Arguments:

- `model` (required)
- `vals` (required): Odoo-style `create` dictionary (e.g. `invoice_line_ids` with `[Command.create({...})]` or legacy `(0, 0, vals)` tuples—match your Odoo version)
- `tenant` (optional)
- `reuse_cached_schema` (optional)
- `validate_with_schema` (optional): default follows `CS_AI_BRIDGE_AI_VALIDATE_SCHEMA`

Natural-language “create an invoice” flows should resolve **partner/product names to numeric IDs** before calling this (e.g. via `mcp_query` on `res.partner` / `product.product`).

### `ai_query`

Arguments:

- `query` (required)
- `tenant` (optional)
- `route` (optional, default `auto`) - `auto | mcp | rag | hybrid`
- `model` (optional)
- `domain` (optional)
- `fields` (optional)
- `reuse_cached_schema` (optional, default `false`) - when `true` (or when `CS_AI_BRIDGE_AI_REUSE_SCHEMA_CACHE` is enabled), use a warm in-process snapshot whenever `CS_AI_BRIDGE_SCHEMA_CACHE_TTL_SECONDS` > 0
- `validate_hints_with_schema` (optional) - override `CS_AI_BRIDGE_AI_VALIDATE_SCHEMA` when not `null`

Before calling Odoo, the server resolves the tenant (`tenant` argument, then `CS_AI_BRIDGE_TENANT`, then `CS_AI_BRIDGE_ODOO_DB_NAME`) and pulls the schema JSON from Redis (`cs_ai_bridge:schema:<tenant>`). With the default (`reuse_cached_schema=false` and no reuse env), cached entries for that tenant are cleared so each `ai_query` reads Redis again immediately after Odoo publishes an update.
