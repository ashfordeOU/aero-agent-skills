---
name: skill-authoring
description: "Use when you must author a NEW conformant SKILL.md for the agentskills.io format under SEP-2640-style delivery: build the frontmatter template from the required fields (name kebab-case matching the folder, description with action and use-when and trigger clauses, Apache-2.0 license, compliance flag, standards references, gated boolean, metadata version and author), then run the deterministic pre-publish conformance check that reports missing or invalid required fields before a leaf is published. SEP-2640 stays an emerging spec, so the authoring discipline targets the stable agentskills.io content surface. Trigger: skill authoring, SKILL.md template, frontmatter, kebab-case name, pre-publish conformance check, SEP-2640, agentskills.io."
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
  tags: [sep-2640, skill-authoring, skill-md-template, frontmatter, kebab-case, conformance-check, pre-publish]
  version: 0.1.0
  author: AeroSkills
---

# SEP-2640 Skill Authoring (cross-cutting/sep2640/skill-authoring)

Use when the task is authoring a new conformant SKILL.md: building the
frontmatter template, checking the kebab-case name rule, writing the
router description, and running the pre-publish conformance check.

## Domain quick reference

- SEP-2640 delivery is skills over MCP in the agentskills.io content
  form; the spec is emerging, so authoring targets the stable
  conformance surface: required frontmatter fields, name shape,
  description discipline, license, compliance, standards, gated, and
  metadata.
- The required top-level fields are name, description, license,
  compliance, standards, gated, and metadata. A candidate missing any
  of them fails the pre-publish check.
- The name must be kebab-case (lowercase letters, digits, single
  hyphens) and equal the leaf folder name; the description must carry
  an action clause, a 'Use when' clause, and a 'Trigger' keyword with
  at least two trigger keywords, within the 50-150 word and 1024 char
  budgets.
- The license must equal Apache-2.0; compliance must be one of none,
  ITAR-GATED, EAR-GATED, STANDARDS-REF; standards must be non-empty;
  gated must be a boolean; metadata must carry version and author.
- The pre-publish conformance check is deterministic, offline, and
  stdlib-only: same candidate, same findings.

## Workflow

1. Draft the frontmatter from the template: name (kebab-case, matching
   the folder), description (action + use-when + trigger), license,
   compliance, standards, gated, metadata.
2. Run the conformance check on the candidate SKILL.md text.
3. Read the findings list: every problem is a missing or invalid
   required field (name shape, folder match, description budgets and
   clauses, license, compliance, standards, gated, metadata).
4. Fix the candidate until the findings list is empty.
5. Publish only a candidate with zero findings.

## Pitfalls

- A name that is not kebab-case (uppercase, spaces, double hyphens).
- A name that does not match the leaf folder (the router resolves
  skills by folder path).
- A description without a 'Use when' clause or fewer than two trigger
  keywords (the description is the router; a weak one routes poorly).
- Claiming conformance while a required field is missing; the check
  is boolean per field and one failure fails the candidate.

## Behavior contract (gate 3)

The authoring logic is exercised by the gate 3 contract test:
scripts/test_authoring.py against scripts/authoring_logic.py (stdlib
unittest, offline). Run:

    python3 scripts/test_authoring.py
