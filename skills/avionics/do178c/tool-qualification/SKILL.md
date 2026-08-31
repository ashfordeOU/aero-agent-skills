---
name: tool-qualification
description: "Use when assessing software tool qualification per DO-330 and DO-178C: determine the tool qualification level (TQL-1 through TQL-5) from the applicable tool criteria, check that a qualification level meets the required rigor, select the governing criterion when several apply, and validate that tool operational requirements (TOR) and qualification artifacts are complete. DO-330 tool criteria 1-5 map to TQL-1..TQL-5 with lower numbers meaning stricter rigor; all logic is deterministic, offline stdlib. Trigger: tool qualification, DO-330, TQL, tool criteria, qualification level, tool operational requirements, TOR, tool credit, verification tool."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-330
    reference-only: true
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [do-330, do-178c, tql, tool-criteria, tor, tool-qualification, tool-credit]
  version: 0.1.0
  author: AeroSkills
---

# DO-330 Tool Qualification (avionics/do178c/tool-qualification)

Use when the task is software tool qualification for a DO-178C
program: mapping tool criteria to tool qualification levels,
checking TQL rigor against requirements, and scoping the DO-330
qualification artifacts.

## Domain quick reference

- DO-330 (Software Tool Qualification Considerations) defines the
  tool qualification process referenced by DO-178C section 12.2 for
  tool credit.
- Tool criteria 1-5 map to TQL-1..TQL-5: criterion 1 (tool output
  part of the airborne software and not verified by another means)
  demands the highest rigor, TQL-1; criterion 5 (tool could fail to
  detect an error but its output is verified by another means)
  demands the lowest rigor, TQL-5.
- Lower TQL numbers are stricter: TQL-1 satisfies a TQL-4
  requirement; TQL-4 does not satisfy a TQL-1 requirement.
- When several criteria apply, the highest criterion number is the
  governing one.
- Key artifacts: tool operational requirements (TOR), qualification
  plan, and tool accomplishment summary.

## Workflow

1. Identify the applicable DO-330 tool criteria for the tool.
2. Map each criterion to its TQL and select the governing one.
3. Check the resulting TQL against the required rigor for the
   intended credit.
4. Confirm the TOR and qualification artifacts are complete.
5. Record the TQL and evidence in the tool qualification documents.

## Pitfalls

- Treating TQL-5 as more rigorous than TQL-1 (reversed ordering).
- Ignoring a higher criterion number when several apply (the
  governing criterion drives the TQL).
- Claiming tool credit without a TOR or accomplishment summary.
- Applying DO-330 criteria without the DO-178C context that
  12.2 references.

## Behavior contract (gate 3)

The logic is exercised by the gate 3 contract test:
scripts/test_tool_qualification.py against
scripts/tool_qualification_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_tool_qualification.py

## Compliance

- Standards referenced, not reproduced: DO-330 / DO-178C text is
  proprietary (RTCA); summary-only per standards-map.yaml and brief 06.
- DO-330 is the tool-qualification companion to DO-178C / DO-254;
  tool credit is accepted via AC 20-115D.
- compliance: STANDARDS-REF, gated: false.
