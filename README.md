# CS AI Bridge FastMCP Server

FastMCP server compatible with `cs_ai_bridge` API:

- `POST /cs_ai_bridge/mcp/query`
- `POST /cs_ai_bridge/ai/query`

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

### `ai_query`

Arguments:

- `query` (required)
- `tenant` (optional)
- `route` (optional, default `auto`) - `auto | mcp | rag | hybrid`
- `model` (optional)
- `domain` (optional)
- `fields` (optional)
