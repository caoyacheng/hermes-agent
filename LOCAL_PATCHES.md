## Local patches (do not lose on upstream sync)

This repo is periodically synced with upstream. The following changes are **local customizations** and must be preserved across pulls/merges/rebases.

### Custom GIS platform tools

- **File**: `tools/gis_platform_tool.py`
- **What**: Adds `gis_*` tool handlers (HTTP client to GIS backend) and registers them under toolset `gis_platform`.
- **Config / env**:
  - `GIS_API_URL` (base URL)
  - `GIS_API_TOKEN` (JWT)
  - `GIS_TOOLS_ALLOW_WRITE` (`true` enables write operations)
  - `GIS_ALLOW_ANON` (dev-only)

### Toolset wiring (API server enablement)

- **File**: `toolsets.py`
- **What**:
  - Adds a new toolset `gis_platform`.
  - Adds all `gis_*` tools to `hermes-api-server` tool list so they are available via the OpenAI-compatible API server.

### Dashboard: show non-configurable toolsets (e.g. `gis_platform`)

- **File**: `hermes_cli/web_server.py`
- **What**:
  - Extends `GET /api/tools/toolsets` to include toolsets beyond the built-in configurable ones, so custom toolsets like `gis_platform` appear in the web UI.
  - Marks a toolset as **enabled** if it is enabled for **any** platform (not only CLI), so toolsets enabled on `api_server` show as Active.

### Config/env metadata for GIS keys

- **File**: `hermes_cli/config.py`
- **What**:
  - Adds `GIS_*` env vars to `OPTIONAL_ENV_VARS` + `ENV_VARS_BY_VERSION` and bumps `_config_version`.
  - This makes setup/doctor/dashboard env pages aware of GIS variables.

### MCP client reliability (stdio servers, Qdrant, etc.)

Upstream keeps `mcp` as an optional extra; this fork makes MCP usable out of the box when `mcp_servers` is configured, and fixes common macOS / first-boot timeouts.

- **`pyproject.toml`**
  - Adds `mcp>=1.2.0,<2` to **core** `dependencies` (still listed under `[project.optional-dependencies] mcp` for compatibility).
  - Removes duplicate `mcp` from the `dev` extra (it is now in core).

- **`model_tools.py`**
  - After MCP discovery: if `mcp_servers` is non-empty but the `mcp` package is missing, logs a **warning** with install instructions.

- **`tools/mcp_tool.py`**
  - **macOS**: prepends `/opt/homebrew/bin` and `/usr/local/bin` to the subprocess `PATH` so `uvx` / `npx` work when the parent process has a minimal PATH (launchd, some gateway supervisors).
  - **Discovery timeout**: outer `_run_on_mcp_loop` timeout scales from each server’s `connect_timeout` (cap 900s) so first-time `uvx mcp-server-qdrant` + embedding warmup is less likely to hit a hard 120s wall.

- **`tests/tools/test_mcp_tool.py`**
  - `TestBuildSafeEnv` uses `monkeypatch` to force `sys.platform == "linux"` for PATH equality assertions (Darwin intentionally mutates PATH).

### Notes (outside git)

These are runtime/user config changes and won’t be preserved by upstream sync automatically:

- `~/.hermes/.env`: set `GIS_API_URL`, `GIS_API_TOKEN`, etc.
- `~/.hermes/config.yaml`: ensure `platform_toolsets.api_server` includes:
  - `hermes-api-server`
  - `gis_platform`

### Recommended upstream sync workflow

Keep these local patches on a dedicated branch and rebase it on top of upstream:

```bash
git fetch upstream
git checkout local/gis-tools
git rebase upstream/main
```

If upstream introduces conflicts in these files, resolve carefully and keep the behavior described above.

