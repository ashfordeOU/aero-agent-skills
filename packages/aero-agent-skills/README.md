# aero-agent-skills

**The aerospace knowledge layer for AI agents** — standards-mapped `SKILL.md` workflows with verification gates and human sign-off stops, shipped as an npm CLI and an MCP server. Built and maintained by [Ashforde OÜ](https://ashforde.org).

Full library, figures, and provenance: [github.com/ashfordeOU/aero-agent-skills](https://github.com/ashfordeOU/aero-agent-skills) · [ashforde.org/aeroagentskills](https://ashforde.org/aeroagentskills) · **JetBrains IDE plugin**: [Aero Agent Skills on the JetBrains Marketplace](https://plugins.jetbrains.com/plugin/34041-aero-agent-skills)

Every skill follows the open [agentskills.io](https://agentskills.io) format and is gated by a replayable offline battery (spec lint, description lint, behavior contracts, no-verbatim sweep, Hit@1 router corpus). This package bundles the tree at the released commit; live counts come from `aero-skills list`, never from this README.

## CLI

```bash
npm i -g aero-agent-skills   # or: npx aero-agent-skills <command>

aero-skills list                          # families, packs, skills
aero-skills search "draft a PSAC for a DAL B system"
aero-skills show avionics/do178c/planning
aero-skills install avionics/do178c --harness claude
aero-skills install all --harness cursor
```

`install` flattens the nested authoring tree into the flat `<skill-name>/` folders agent harnesses consume (`--harness claude|codex|gemini|cursor|opencode|agents|claude-project`, or `--dest <dir>`; `--link` symlinks instead of copying). `search` uses the same deterministic token-overlap router the repository's Hit@1 gate proves — no network, no model, no telemetry.

## MCP server

Works in any Model Context Protocol host: [JetBrains AI Assistant and Junie](https://plugins.jetbrains.com/plugin/34041-aero-agent-skills) (via the IDE plugin or the MCP config below), Claude Desktop, Claude Code, VS Code, Cursor, Windsurf, Gemini CLI.

```json
{
  "mcpServers": {
    "aero-agent-skills": {
      "command": "npx",
      "args": ["-y", "aero-agent-skills", "mcp"]
    }
  }
}
```

Tools: `search_skills` (deterministic router), `get_skill` (full SKILL.md), `list_families`, `list_skills`, `get_standards` (the machine-readable standards register: publisher, status, gated flag).

## What a skill is

A folder with a `SKILL.md`: YAML frontmatter a router reads (what + when + trigger), a body the agent follows (workflow, verification gates, and the point where the agent must stop and let a human sign), plus an offline behavior contract test. Standards are referenced and summarized, never reproduced: see the repository's `STANDARDS.md`.

Verified means the full gate battery passes on the bundled commit — nothing more. It is not certification, not approval, not airworthy.

## License

Apache-2.0 © Ashforde OÜ (Estonia). Not affiliated with or endorsed by RTCA, EUROCAE, SAE International, IAQG, EASA, FAA, or any government.
