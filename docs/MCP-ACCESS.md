# MCP Access Policy (skills + roles)

Aero Agent Skills (`SKILL.md`) and Aero Agent Roles (`ROLE.md`) share one
MCP access grammar, enforced by `scripts/spec_lint.py` (gate 1 here) and
`scripts/role-lint.py` (roles repo).

## Default: offline-only

Absent `mcp_allowed` = offline-only. Skills are content + stdlib logic
files; roles are deterministic workers. No live MCP server is implied by
any role/skill unless it declares `mcp_allowed`.

## Grammar

```yaml
mcp_allowed:
  - aero-agent-roles:read
  - github:read
mcp_blocked:
  - worldintel
```

- `mcp_allowed`: non-empty list of `<server>:<read|write>`.
- `mcp_blocked`: hard-deny server names; wins over `mcp_allowed`.
- Servers not in `mcp_allowed` are blocked by default.
- `mcp_blocked` alone is rejected (redundant — absence already blocks).

## SEP-2640 delivery

The delivery servers expose BOTH tool calls and the SEP-2640 resources
model so a skill is reachable two ways:

- Tools: `search_skills`, `get_skill`, `list_families`, `list_skills`,
  `get_standards` (AeroSkills); `search_roles`, `get_role`,
  `list_domains`, `list_roles`, `get_standards` (roles).
- Resources: `skill://<family>[/<pack>[/<leaf>]]` and
  `role://<domain-or-slug>` via `resources/list` + `resources/read`.

Full spec: `docs/MCP-ACCESS.md` in the roles repo (same content
canonicalized for both trees).
