# MCP Tool Naming Audit

Day 1 of the Agent Action Trace work found two local MCP definitions:

- `backend/core/mcp_bootstrap.py` exposes the deployed Streamable HTTP FastMCP app and registers `get_pantry_items` and `update_pantry_items`.
- `backend/mcp/tools.py` was an older helper that only registered `get_pantry`.

The API routes already call `get_pantry_items` and `update_pantry_items`, and `backend/agent/agent.py` instructs the agent to call `get_pantry_items`. The canonical chat-agent tool names are therefore:

- `get_pantry_items`
- `update_pantry_items`

For backward compatibility, `backend/mcp/tools.py` now registers the canonical names and keeps `get_pantry` as a legacy alias.

## Deployed server check

I attempted a direct Streamable HTTP MCP `initialize` + `tools/list` request against the default deployed MCP URL (`https://smartcart-mcp-505176174078.us-central1.run.app/mcp`) from this environment. The request could not reach Cloud Run because the environment proxy returned `Tunnel connection failed: 403 Forbidden`. Since `/debug/tools` requires the authenticated API runtime and no user token is available in this non-interactive shell, the deployed server could not be introspected live here.

The local deployed-entrypoint source (`backend/core/mcp_bootstrap.py`) is the source of truth for this change.
