# Harness integration verification (P3.4 REWORK, track 2)

Status: verified against official docs on 2026-08-31. Every mechanism below
was checked against the cited source on that date; sources are listed in the
Source table at the end. This file is the evidence base for README v0.2:
it documents how an Aero Agent Skills SKILL.md is actually consumed by each host.

## Headline finding

Every harness consumes a FLAT set of `<skill-name>/SKILL.md` folders per the
Agent Skills open standard (agentskills.io). The repo's nested authoring
layout (`skills/<pack>/<standard>/<activity>/SKILL.md`, e.g.
`skills/avionics/do178c/planning/SKILL.md`) is NOT consumed as-is by
any harness. Installation requires flattening - or symlinking - each skill
folder into the harness's skills root, with the folder named to match the
frontmatter `name`.

Domain packs (2026-08-31 restructure, expanded in P3.5 and Wave 5): the
authoring tree is organized into twelve installable domain packs
(aerodynamics, avionics, cross-cutting, flight-mechanics,
flight-test-operations, gnc-autonomy, manufacturing-quality,
propulsion, space-systems, structures, systems-engineering-safety,
vehicle-design). The
install unit stays the leaf folder; installing a pack means copying or
symlinking each leaf folder under `skills/<pack>/`. The pack-level
`skills/<pack>/SKILL.md` is a router document for agents (domain
description + sub-skill list + routing guidance), not a consumable
skill itself. `scripts/pack_inventory.py` (`make packs`) lists every
leaf by pack from frontmatter so an installer can enumerate a pack's
folders deterministically.

README v0.1's install line ("Add skills/<path> to your host's skills
directory (Claude Code, Hermes, OpenClaw, Codex, or any agentskills.io
host)") is imprecise for Codex, Gemini CLI, OpenCode, and Cursor, which use
`.agents/skills/` or their own roots; and Codex additionally consumes the
repo's AGENTS.md directly. README v0.2 must document the flatten step and
per-harness roots below.

## 1. Claude Code

Sources: docs.anthropic.com/en/docs/claude-code/skills;
docs.anthropic.com/en/docs/claude-code/plugins (retrieved 2026-08-31).

Mechanism: Agent Skills open standard. A skill is a directory with SKILL.md
(YAML frontmatter with name + description, markdown body). Custom slash
commands were merged into skills: `.claude/commands/deploy.md` and
`.claude/skills/deploy/SKILL.md` both create `/deploy`.

Locations, in priority order:

| Scope | Path | Notes |
|---|---|---|
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | Available across all projects |
| Project | `.claude/skills/<skill-name>/SKILL.md` | Repo root and every parent up to the repo root; nested `.claude/skills/` below CWD are discovered when Claude reads/edits files there |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | Invoked as `/plugin-name:skill-name`; namespaced, cannot collide |
| claude.ai sync | `~/.claude/skills/synced/` | Downloaded when `CLAUDE_CODE_SYNC_SKILLS` is set |

Exact commands:

```
mkdir -p ~/.claude/skills/<skill-name>     # create the skill directory
# write SKILL.md inside it; directory name becomes the slash command,
# the description drives automatic invocation
claude plugin init <name>                  # scaffolds ~/.claude/skills/<name>/ with
                                           # .claude-plugin/plugin.json; loads as <name>@skills-dir
claude plugin marketplace add anthropics/claude-plugins-official   # official marketplace
# community: /plugin marketplace add anthropics/claude-plugins-community
claude --plugin-dir ./my-plugin            # load a plugin locally for testing
claude plugin validate ./your-plugin       # pre-submission validation
```

Notes: Claude Code extends the open standard with invocation control,
subagent execution, and dynamic context injection. Skills directories are
watched for live reload (SKILL.md text only). A `.claude-plugin/plugin.json`
manifest inside a skill folder turns it into a plugin that can bundle
agents, hooks, and MCP servers. Workspace trust is required for project
plugin loading.

## 2. OpenAI Codex

Sources: developers.openai.com/codex/guides/agents-md;
developers.openai.com/codex/skills; github.com/openai/codex docs/skills.md
(retrieved 2026-08-31).

Codex has two consumption mechanisms.

Mechanism 1 - AGENTS.md (instructions, always loaded, no progressive
disclosure):

- Global: `~/.codex/AGENTS.md`; `~/.codex/AGENTS.override.md` wins when
  present; `CODEX_HOME` redirects the whole profile.
- Project: `AGENTS.md` at the repo root, walked down to the current
  directory; `AGENTS.override.md` takes precedence in each directory.
  Files merge root-down; combined size capped at 32 KiB
  (`project_doc_max_bytes`); fallback filenames configurable
  (`project_doc_fallback_filenames`).
- Aero Agent Skills ships a root `AGENTS.md`; Codex consumes it automatically.

Mechanism 2 - Skills (progressive disclosure: only name, description, and
file path are injected; the SKILL.md body loads on demand):

| Scope | Path |
|---|---|
| REPO | `.agents/skills` in `$CWD`, every parent up to `$REPO_ROOT` |
| USER | `$HOME/.agents/skills` |
| ADMIN | `/etc/codex/skills` |
| SYSTEM | Bundled with Codex |

- Mention a skill with `$skill-name` in a message; browse with `/skills`
  in the TUI.
- Legacy experimental location (docs/skills.md): `~/.codex/skills/**/SKILL.md`
  behind `[features] skills = true` in `~/.codex/config.toml`, or
  `codex --enable skills` for a single run.
- Disable without deleting: `[[skills.config]] path = "/path/SKILL.md"
  enabled = false` in `~/.codex/config.toml`, then restart.
- Symlinks: a symlink to the skill DIRECTORY is followed; a symlink to the
  SKILL.md file alone is dropped by the loader (openai/codex issues 9365,
  17344).

## 3. DeepSeek (via harness)

Sources: deepseek.com/harness/en/; github.com/deepseek-ai/deepseek-harness
(retrieved 2026-08-31).

Fact: the DeepSeek model and chat have NO native skill loader. A SKILL.md is
consumed only through a harness that (a) reads the Agent Skills format and
(b) is pointed at a DeepSeek model.

First-party harness - DeepSeek Harness (dsh):

- Open-source agent harness by DeepSeek AI, MIT, built on the Cordis
  plugin system: "everything is a plugin" (models, tools, skills, sessions,
  sandboxes, storage, loops, scheduling, UI).
- Status: developer preview; compatibility-breaking changes expected.
- Run: `npx @deepseek-ai/dsh web` (Web UI at 127.0.0.1:3080 by default);
  or `git clone https://github.com/deepseek-ai/deepseek-harness` then
  `pnpm install && pnpm run build && pnpm dsh web`.
- Skills are a plugin capability. The repo itself ships skills under
  `.agents/skills/` (plus `.agents/notes`) - the cross-client convention
  (see section 7). Exact skill-dir semantics live in the project docs
  (deepseek-harness.github.io/deepseek-harness/, JS-rendered); verify at
  authoring time before claiming a specific path.

Third-party path: any SKILL.md-capable harness with DeepSeek as the model
provider - OpenCode, Cline/Roo Code (VS Code), Continue, and the showcase
entry "Deep Code" (open-source terminal coding assistant for the DeepSeek
model with Skills + MCP). Practical install: drop skill folders into the
harness's skills root (e.g. `.agents/skills/<name>/SKILL.md`) and configure
DeepSeek as the model.

## 4. Gemini CLI

Source: geminicli.com/docs/cli/skills/ (retrieved 2026-08-31).

Mechanism: Agent Skills open standard. Discovery tiers, lowest to highest:

1. Built-in skills (bundled).
2. Extension skills (bundled within installed extensions).
3. User skills: `~/.gemini/skills/` or the `~/.agents/skills/` alias.
4. Workspace skills: `.gemini/skills/` or the `.agents/skills/` alias
   (version-controlled, shared with the team).

Precedence: higher tier wins; within a tier, the `.agents/skills/` alias
takes precedence over `.gemini/skills/`. The alias exists for
cross-tool interoperability.

Activation: the model calls an `activate_skill` tool when a task matches a
skill's description; the user sees a consent prompt; on approval the
SKILL.md body and folder structure are injected and the skill directory is
added to the agent's allowed file paths (bundled assets become readable).

Manage:

```
# interactive
/skills list [all] [nodesc]        /skills link <path> [--scope user|workspace]
/skills disable <name>             /skills enable <name>
/skills reload                     (alias: /skills refresh)

# terminal
gemini skills list --all
gemini skills install https://github.com/user/repo.git [--scope user|workspace] [--path <subdir>] [--consent]
gemini skills uninstall my-skill --scope workspace
```

Notes: project context file is GEMINI.md, not AGENTS.md. The docs pages
carry a banner (2026-04-30) that unpaid/Google One Gemini CLI is being
replaced by Antigravity CLI on 2026-06-18; confirm current status before
README v0.2 documents Gemini-CLI-only support.

## 5. OpenCode

Sources: opencode.ai/docs/skills; opencode.ai/v2/docs/skills (retrieved
2026-08-31).

Mechanism: skills discovered into a native `skill` tool; the agent sees the
catalog and loads full content on demand. Locations:

| Scope | Path |
|---|---|
| Project | `.opencode/skills/<name>/SKILL.md` |
| Global | `~/.config/opencode/skills/<name>/SKILL.md` |
| Project Claude-compatible | `.claude/skills/<name>/SKILL.md` |
| Global Claude-compatible | `~/.claude/skills/<name>/SKILL.md` |
| Project agent-compatible | `.agents/skills/<name>/SKILL.md` |
| Global agent-compatible | `~/.agents/skills/<name>/SKILL.md` |

Discovery walks up from the current directory to the git worktree and loads
matching skill dirs at every level. Frontmatter honored: `name` (required;
regex `^[a-z0-9]+(-[a-z0-9]+)*$`, 1-64 chars, must match the directory),
`description` (required; 1-1024 chars), `license`, `compatibility`,
`metadata`; unknown fields are ignored.

V2 additions: a `skills` array in `opencode.json`/`opencode.jsonc` adds
local directories or HTTP catalogs (base URL with `index.json`); precedence
from lowest to highest is built-in, `.claude/skills`, `.agents/skills`,
`~/.config/opencode/skills`, project `.opencode/skills`. Skill permissions
are configurable (`permission.skill` allow/deny patterns; `tools.skill:
false` disables the skill tool).

AGENTS.md rules: project root `AGENTS.md`, global
`~/.config/opencode/AGENTS.md`, with `CLAUDE.md` fallbacks;
`OPENCODE_DISABLE_CLAUDE_CODE*` env vars disable the compatibility paths.

## 6. Cursor

Source: cursor.com/docs/skills (retrieved 2026-08-31).

Mechanism: Agent Skills open standard; skills discovered at startup and
decided on by the agent from context (or invoked explicitly with
`/skill-name`). Skill directories:

| Scope | Path |
|---|---|
| Project | `.agents/skills/`, `.cursor/skills/` |
| User | `~/.agents/skills/`, `~/.cursor/skills/` |
| Compatibility | `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, `~/.codex/skills/` |

Cursor walks the skills root recursively (category subdirectories are
organizational; identity comes from the folder containing SKILL.md).
Nested `.cursor/skills/` inside a monorepo are scoped to that directory.

Frontmatter: `name` (required; lowercase letters/numbers/hyphens; must
match the parent folder), `description` (required), `paths` (glob scoping),
`disable-model-invocation`, `icon`, `color`, `metadata`.

Install and management:

- GitHub import for rules: Customize -> Rules -> Add Rule -> Remote Rule
  (Github) -> repo URL -> `.mdc` files land in `.cursor/rules/imported/`.
- `/migrate-to-skills` converts eligible dynamic rules and slash commands
  into skills under `.cursor/skills/`.
- Any skill can back a Custom Mode (Option+Enter / Alt+Enter).
- Claude skills/plugins can be imported via Settings -> Rules -> Import
  Settings (agent-decided rules).

Notes: user-level skills are not copied to Cloud Agents or remote SSH
sessions; those environments need project skills in the repo or skills
baked into the worker image. Rules still live at `.cursor/rules/*.mdc` and
AGENTS.md is supported.

## 7. Generic agentskills.io consumers

Sources: agentskills.io/specification; agentskills.io client showcase
(rendered 2026-08-31); agentskills.io/llms-full.txt (implementor guide).

Spec (what every consumer reads): SKILL.md with YAML frontmatter - `name`
(1-64 chars, kebab-case, must match parent dir), `description` (1-1024,
what + when), `license`, `compatibility` (max 500 chars), `metadata`
(string map), `allowed-tools` (experimental). Body <500 lines recommended;
optional `scripts/`, `references/`, `assets/`; relative file references one
level deep; validation via `skills-ref validate ./my-skill`.

Progressive disclosure (all consumers): tier 1 metadata (~100 tokens per
skill at startup), tier 2 full SKILL.md body (<5000 tokens) on activation,
tier 3 resources on demand.

Cross-client convention: `.agents/skills/` (project and user level) has
emerged as the widely-adopted path for cross-client sharing; many clients
also scan `.claude/skills/` for pragmatic compatibility. The spec does not
mandate a location - it defines only what is inside a skill.

Client showcase (rendered 2026-08-31) includes: Claude Code, ChatGPT &
Codex, Gemini CLI, Cursor, OpenCode, GitHub Copilot, VS Code, Roo Code,
OpenHands, Goose, pi, Letta, OpenClaw, ZeroClaw, Mistral AI Vibe,
Deep Code, TRAE, Junie, Tabnine, Factory, Qodo, Amp, Mux, Snowflake Cortex
Code, Databricks Genie Code, Hermes Agent, and others. The list is
JS-rendered on the page; re-render at README v0.2 time for the current set.

Implementor guide (for consumers we might build): discovery scopes
(project/user/admin), lenient parsing (warn and load on cosmetic issues),
catalog disclosure (system-prompt section or tool description), activation
via file-read or a dedicated `activate_skill` tool, user-explicit
activation (`/skill-name` or `$skill-name`), permission allowlisting of
skill directories, and protection of skill content from context
compaction.

## 8. MCP hosts (JetBrains AI Assistant / Junie, Claude Desktop, VS Code, Windsurf, Gemini CLI)

Added 2026-09-02. Distribution channel two: the `aero-agent-skills` npm
package ships an MCP server (`aero-skills mcp`, stdio, newline-delimited
JSON-RPC 2.0, zero dependencies, no network) so hosts that speak the Model
Context Protocol but do not read SKILL.md folders still get the library.
Tools: `search_skills` (a 1:1 JS port of the gate-5 router — parity replayed
on the FULL Hit@1 corpus by `make package-test`, wired into `.ci-native`),
`get_skill` (full SKILL.md), `list_families`, `list_skills`, `get_standards`
(the standards-map register).

Universal config (same JSON in every host):

```json
{"mcpServers": {"aero-agent-skills": {"command": "npx", "args": ["-y", "aero-agent-skills", "mcp"]}}}
```

Per-host entry points:

| Host | Where the config goes |
|---|---|
| JetBrains AI Assistant | Settings > Tools > AI Assistant > Model Context Protocol (MCP) > Add; paste the JSON or add command `npx`, args `-y aero-agent-skills mcp` |
| JetBrains Junie | Settings > Tools > Junie > MCP Settings (same shape) |
| Claude Desktop | `claude_desktop_config.json` > `mcpServers` |
| Claude Code | `claude mcp add aero-agent-skills -- npx -y aero-agent-skills mcp` (skills install is still the better channel here — see section 1) |
| VS Code (Copilot agent mode) | `.vscode/mcp.json` with the server under `servers` |
| Cursor | `.cursor/mcp.json` > `mcpServers` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` > `mcpServers` |
| Gemini CLI | `gemini mcp add aero-agent-skills npx -y aero-agent-skills mcp` |

Verification status (honest split): the server protocol itself is
smoke-tested locally on every push — initialize handshake, tools/list,
tools/call round-trip over stdio (`packages/aero-agent-skills/test/smoke.mjs`).
The per-host config locations above are transcribed from the hosts' official
MCP documentation as of 2026-09-02 and have NOT each been exercised against
a live IDE install; exercise before citing any specific host in marketing.

## 9. npm package + Claude Code plugin (distribution channels)

Added 2026-09-02. Three first-party channels beyond `npx skills`:

1. **npm CLI** — `aero-agent-skills` (bins: `aero-agent-skills`,
   `aero-skills`): `list`, `search` (deterministic router), `show`,
   `install` (flattens per the headline finding, with progressive
   folder-name qualification when a selection contains duplicate
   frontmatter names — the tree currently has a few, e.g.
   configuration-management), `where`, `mcp`. Zero runtime dependencies;
   the tarball bundles the skills tree + standards-map at pack time
   (`scripts/prepack.js`); `manifest.json` is GENERATED by
   `scripts/gen_manifest.py` and freshness-gated by `make visuals-check`.
2. **MCP server** — section 8 above; same binary, `mcp` subcommand.
3. **Claude Code plugin** — `.claude-plugin/plugin.json` +
   `.claude-plugin/marketplace.json` at repo root; both pass
   `claude plugin validate --strict`. VERIFIED by local install
   2026-09-02: plugin discovery is top-level-only, so the twelve family
   router SKILL.md docs load as the plugin's skills (~4.7k tokens
   always-on total, per `claude plugin details`) and their sub-skill
   tables route the agent to leaf SKILL.md files inside the installed
   plugin directory on demand. This is the hierarchical design working
   as intended, not a gap: the full 330-leaf catalog stays out of
   always-on context.

## Cross-cutting findings (Ops lens)

1. Repo layout vs consumption: the nested authoring tree
   (skills/<pack>/<standard>/<activity>/SKILL.md, organized into domain
   packs) is the source of truth; every harness needs a flat
   `<name>/SKILL.md` per skill. Prefer symlinking the skill DIRECTORY
   (supported by Codex dir symlinks, Gemini CLI `/skills link`, Cursor's
   recursive walk) over copying, to keep one canonical source. The
   SEP-2640 skill-delivery skill already covers MCP packaging; the flat
   install step is the remaining gap, and `make packs` enumerates the
   leaf folders per pack for it.
2. Name must match folder: gate 1 enforces this in the authoring tree;
   after flattening, the harness folder must be named the frontmatter name
   or the harness warns or skips the skill.
3. Trust: project-level skills from untrusted repos are prompt-injection
   surface; harnesses gate on workspace trust (Claude Code trust dialog,
   Cursor trusted project, agentskills.io implementor guidance). Skills
   from this repo are methodology text only; still, install into trusted
   projects.
4. No external sends: all harnesses consume local files; installing a
   skill requires no telemetry and no network. Nothing here changes the
   repo's no-publish rule.
5. README v0.2 should cite this file as the install evidence base and
   replace the v0.1 one-line install claim with the per-harness table.

## Source table

| Harness | Source | Retrieved |
|---|---|---|
| Claude Code skills | https://docs.anthropic.com/en/docs/claude-code/skills | 2026-08-31 |
| Claude Code plugins | https://docs.anthropic.com/en/docs/claude-code/plugins | 2026-08-31 |
| Codex AGENTS.md | https://developers.openai.com/codex/guides/agents-md | 2026-08-31 |
| Codex skills | https://developers.openai.com/codex/skills + github.com/openai/codex docs/skills.md | 2026-08-31 |
| DeepSeek Harness | https://deepseek.com/harness/en/ + github.com/deepseek-ai/deepseek-harness | 2026-08-31 |
| Gemini CLI skills | https://geminicli.com/docs/cli/skills/ | 2026-08-31 |
| OpenCode skills | https://opencode.ai/docs/skills + /v2/docs/skills | 2026-08-31 |
| Cursor skills | https://cursor.com/docs/skills | 2026-08-31 |
| Agent Skills spec | https://agentskills.io/specification | 2026-08-31 |
| Client showcase | https://agentskills.io/clients (rendered) | 2026-08-31 |
| Implementor guide | https://agentskills.io (llms-full.txt) | 2026-08-31 |
| MCP spec (stdio transport, tools) | https://modelcontextprotocol.io/specification | 2026-09-02 (from working knowledge; server smoke-tested locally against the JSON-RPC contract) |
| JetBrains AI Assistant MCP | https://www.jetbrains.com/help/ai-assistant/mcp.html | 2026-09-02 (transcribed, not live-exercised) |
| Claude Code plugin manifests | `claude plugin validate --strict` + local install + `claude plugin details` | 2026-09-02 (exercised) |
