---
name: validation
description: "Use when you must run requirements validation for an aircraft or system program per ARP4754A: select the validation method, confirm independence is provided where the development assurance level requires it, and score validation closure before the requirements are released to design. Produces the method verdict, the independence flag, and the closure score that gate the validation phase. Trigger: requirements validation, arp4754a, validation method, independent validation, development assurance, closure."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4754a
  tags: [requirements-validation, validation-method, independent-validation, development-assurance, validation-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ARP4754A Requirements Validation (systems-engineering-safety/arp4754a/validation)

Use when the task is requirements validation per ARP4754A: method
selection, independence, and closure scoring before requirements
move to design.

## Domain quick reference

- Validation asks whether the right requirements were captured;
  verification asks whether they were built right.
- Validation methods: analysis, simulation, test, demonstration,
  and inspection.
- Development assurance levels A and B require independent
  validation of the requirements.
- Closure: every requirement validated by a recognized method
  before release; project thresholds typically require near-full
  closure.

## Workflow

1. Collect each requirement with its validation status and method.
2. Confirm the method is recognized with validate_method_ok.
3. Check independence with independence_required.
4. Score closure with validation_closure.
5. Gate the requirements release on the closure verdict.

## Pitfalls

- Calling review a validation method and closing without analysis.
- Missing independent validation at level A or B.
- Releasing requirements with open validation items.

## Behavior contract (gate 3)

The method, independence, and closure logic is exercised by the
gate 3 contract test: scripts/test_validation.py against
scripts/validation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_validation.py

## Compliance

- Standards referenced, not reproduced: ARP4754A and ARP4761A text
  is proprietary (SAE); summary-only per standards-map.yaml and
  brief 06.
- compliance: STANDARDS-REF, gated: false.
