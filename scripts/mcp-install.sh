#!/usr/bin/env bash
# mcp-install.sh — register this repo's MCP server with the hosts found on
# this machine. Keeps MCP usable from INSIDE the repo on any clone: editors
# read .mcp.json at the project root (committed), Claude Code gets a
# project-scope registration, Hermes gets a config snippet. Everything is
# idempotent. Run:  bash scripts/mcp-install.sh [--verify-only]
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
server="node packages/aero-agent-skills/bin/aero-agent-skills.js mcp"
name="aero-agent-skills"
mcp_json="$repo_root/.mcp.json"

echo "== Aero Agent Skills — MCP installer =="
echo "repo:  $repo_root"

# 1. .mcp.json is the portable discovery file (VS Code, Cursor, Windsurf,
#    Claude Desktop project scope, Gemini CLI all read it). Already
#    committed at the repo root with repo-relative paths.
if [ -f "$mcp_json" ]; then
  echo "ok    .mcp.json present (repo-relative paths, portable)"
else
  echo "FAIL  .mcp.json missing at repo root — refusing to continue"
  exit 1
fi

# 2. Claude Code — project-scope registration (only touches this repo).
if command -v claude >/dev/null 2>&1; then
  out="$(claude mcp add --scope project "$name" -- node "packages/aero-agent-skills/bin/aero-agent-skills.js" mcp 2>&1 || true)"
  case "$out" in
    *"already exists in .mcp.json"*) echo "ok    claude code: '$name' already in .mcp.json (project scope)";;
    *"Added"*|*"updated"*) echo "ok    claude code: registered '$name' (project scope)";;
    *) echo "warn  claude code: $out";;
  esac
else
  echo "skip  claude code CLI not found"
fi

# 3. Hermes — report the config to add (Hermes config is user-global;
#    write it from the repo only if HERMES_CONFIG_TARGET is set).
if [ "${HERMES_CONFIG_TARGET:-}" = "write" ] && command -v hermes >/dev/null 2>&1; then
  hermes config set "mcp_servers.$name.command" node
  hermes config set "mcp_servers.$name.args" "[\"$repo_root/packages/aero-agent-skills/bin/aero-agent-skills.js\", \"mcp\"]"
  hermes config set "mcp_servers.$name.enabled" true
  echo "ok    hermes: wrote mcp_servers.$name into hermes config"
else
  echo "hint  hermes: add this to ~/.hermes/config.yaml under mcp_servers:"
  cat <<EOF
  $name:
    command: node
    args:
      - $repo_root/packages/aero-agent-skills/bin/aero-agent-skills.js
      - mcp
    enabled: true
EOF
fi

# 4. Self-verify: initialize + tools/list round-trip against the same
#    command the hosts will run.
echo "== self-verify =="
if (cd "$repo_root" && printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"installer","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | node packages/aero-agent-skills/bin/aero-agent-skills.js mcp 2>/dev/null \
  | python3 -c 'import json,sys
lines=[json.loads(l) for l in sys.stdin if l.strip()]
tools=lines[-1].get("result",{}).get("tools",[]) if lines else []
print(f"tools: {len(tools)}") if tools else print("FAIL no tools") or sys.exit(1)'); then
  echo "PASS  MCP server reachable and answering tools/list"
else
  echo "FAIL  MCP server did not answer — check node and the package path"
  exit 1
fi
echo "== done =="
