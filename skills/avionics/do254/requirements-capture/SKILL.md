---
name: requirements-capture
description: "Use when you must capture and review DO-254 hardware requirements for a complex airborne electronic hardware item: check each requirement for vague terms, missing identifiers, and missing trace links, classify derived requirements from allocated ones, and score capture readiness before the requirements review. Produces the requirement issue list, the derived-versus-allocated classification, and the readiness verdict the design phase consumes. Trigger: hardware requirements, requirements capture, derived requirements, traceability, do-254, requirement characteristics."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-254
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do254
  tags: [hardware-requirements, requirements-capture, derived-requirements, traceability, requirement-characteristics, hardware, derived, requirements, capture]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-254 Hardware Requirements Capture (avionics/do254/requirements-capture)

Use when the task is DO-254 hardware requirements capture: checking
requirement characteristics, identifying derived requirements, and
gating the requirements review for airborne electronic hardware.

## Domain quick reference

- DO-254 hardware requirements must be complete, correct, and
  verifiable, with unique identifiers and trace links.
- Derived requirements: added during design or safety analysis with
  no direct higher-level source; they must be identified and
  justified, and they count as requirements for verification.
- Allocated requirements trace upward to a system requirement;
  derived requirements do not.
- Vague wording (suitable, adequate, approximately, and similar)
  fails the verifiability test at the requirements review.

## Workflow

1. Collect each hardware requirement with its identifier, text, and
   trace status.
2. Run the characteristic check with req_issues.
3. Classify each requirement as derived or allocated with
   classify_derived.
4. Score capture readiness with capture_readiness.
5. Gate the requirements review on the issue list and readiness.

## Pitfalls

- Accepting vague wording because the design intent is clear.
- Missing trace links on allocated requirements.
- Letting derived requirements appear without a justification note.

## Behavior contract (gate 3)

The requirement-characteristic, classification, and readiness logic
is exercised by the gate 3 contract test:
scripts/test_requirements_capture.py against
scripts/requirements_capture_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_requirements_capture.py

## Compliance

- Standards referenced, not reproduced: DO-254 text is proprietary
  (RTCA); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
