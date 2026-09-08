# Aero Agent Skills — MCP server (in-repo)

This repo IS an MCP server. The delivery server ships inside the repo and
registers with any host from the repo itself — no external install
required.

## What the server provides

Run it directly:

```bash
node packages/aero-agent-skills/bin/aero-agent-skills.js mcp
# or
npm --prefix packages/aero-agent-skills run mcp
```

Zero dependencies, stdio newline-delimited JSON-RPC 2.0. Tools:

| Tool | What it answers |
|---|---|
| `search_skills` | deterministic Hit@1 router over the whole library |
| `get_skill` | full SKILL.md body + `skill files:` footer (references/scripts/assets) |
| `list_families` / `list_skills` | browse |
| `get_standards` | standards register |

Resources (SEP-2640): `skill://<family>[/<pack>[/<leaf>]]` and
`skill://<family>/<pack>/<leaf>/references/<file>` via `resources/list`
+ `resources/read`. Reference files under `references/` are served too.

## Register from this repo (any host)

```bash
bash scripts/mcp-install.sh
```

The installer (idempotent):
1. Confirms `.mcp.json` exists at the repo root — **that file IS the
   registration** for VS Code, Cursor, Windsurf, Claude Desktop project
   scope, and Gemini CLI. It is committed with repo-relative paths so any
   clone works.
2. Registers project-scope with Claude Code if the CLI is present.
3. Prints the exact Hermes config block (set `HERMES_CONFIG_TARGET=write`
   to have it written for you).
4. Self-verifies with a live `initialize` + `tools/list` round-trip.

## Register a published copy (consumers)

The npm package carries the same server, so users who do not clone the
repo can add it to any MCP host:

```json
{ "mcpServers": { "aero-agent-skills": { "command": "npx", "args": ["-y", "aero-agent-skills", "mcp"] } } }
```

## MCP access policy

Skills may declare `mcp_allowed` / `mcp_blocked` in frontmatter (default:
offline-only). Enforced by gate 1 `spec_lint.py`. See
[docs/MCP-ACCESS.md](docs/MCP-ACCESS.md).

## Smoke coverage

`packages/aero-agent-skills/test/smoke.mjs` covers handshake, tools,
resources/list, resources/read (skill body + reference file), and the CLI
in one offline battery: `npm --prefix packages/aero-agent-skills test`.
