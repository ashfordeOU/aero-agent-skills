---
name: skill-delivery
description: "Use when packaging or delivering domain skills over MCP per SEP-2640: check that a skill package carries a conformant SKILL.md (kebab-case name, description), build the skill URI (skill:// namespace and path), and verify the MCP server exposes the delivery model (resources/read and directory listing behind the directoryRead capability). SEP-2640 serves skills as resources and stays an adapter over the agentskills.io content format, an emerging spec not yet stable. Trigger: SEP-2640, skills over MCP, skill delivery, skill URI, MCP resources, directory read, skill packaging, agentskills.io."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: sep2640
  tags: [sep-2640, skills-over-mcp, mcp, skill-delivery, resources, skill-uri]
  version: 0.1.0
  author: AeroSkills
---

# SEP-2640 Skill Delivery (cross-cutting/sep2640/skill-delivery)

Use when the task is delivering skills over MCP per SEP-2640:
package conformance, skill URIs, and server readiness.

## Domain quick reference

- SEP-2640 (Skills-over-MCP, MCP working group) is an emerging
  extension that serves skills as resources: skill:// URIs,
  resources/read, and directory listing behind the directoryRead
  capability.
- The agentskills.io SKILL.md format remains the canonical content
  form; SEP-2640 is an adapter layer for discovery and delivery.
- A deliverable package carries a conformant SKILL.md at its root:
  kebab-case name and a description.
- Status: draft, not yet stable; pin the spec revision you build
  against.

## Workflow

1. Check the skill package for conformance (SKILL.md present,
   kebab-case name, description).
2. Build the skill URI from the namespace and skill path.
3. Verify the MCP server exposes the delivery model: skill URIs,
   resources/read, and directory listing.
4. Pin the SEP-2640 revision and note the emerging status.

## Pitfalls

- Shipping a package without a root SKILL.md.
- A server without directoryRead claiming directory discovery.
- Treating SEP-2640 as stable while the spec is still a draft.
- Using the MCP layer as the source of truth instead of the
  SKILL.md files.

## Behavior contract (gate 3)

The package-conformance, URI, and readiness logic is exercised by the
gate 3 contract test: scripts/test_delivery.py against
scripts/delivery_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_delivery.py

## Compliance

- SEP-2640 is an open specification; quote with citation and note the
  status (emerging, not yet stable) per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
