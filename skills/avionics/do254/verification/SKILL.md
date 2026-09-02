---
name: verification
description: "Use when verifying DO-254 airborne electronic hardware: determine the verification methods that apply to a simple or complex AEH item, check whether independent verification is expected at the hardware design assurance level, validate requirements-based test coverage against the A/B and C/D ratios, review hardware/software integration evidence, and confirm the verification effort is complete against the required method set. Methods scale from reduced verification for simple AEH to test, analysis, and review for complex AEH. Trigger: do-254, verification, airborne electronic hardware, aehl, hardware design assurance, requirements-based test, hardware/software integration, review, analysis."
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
  tags: [do-254, verification, aehl, hardware-design-assurance, requirements-based-test, hwsw-integration]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-254 Verification (avionics/do254/verification)

Use when the task is verification of DO-254 airborne electronic
hardware: method selection, independence, coverage, and completeness
for the hardware item.

## Domain quick reference

- Verification is the DO-254 process that shows the hardware item
  satisfies its requirements; the methods are test, analysis, and
  review, selected per item and design assurance level.
- Complex AEH (programmable logic, processors, significant internal
  state) is verified by test, analysis, and review; simple AEH uses
  reduced verification (review-based).
- Independent verification is expected at the higher hardware design
  assurance levels (A/B); independence is separate from the methods
  themselves.
- Requirements-based testing measures coverage against the item's
  requirements: use a 0.98 ratio at levels A/B and 0.95 at C/D.
- Hardware/software integration evidence ties the hardware item to
  the airborne software it hosts.

## Workflow

1. Classify the item as simple or complex AEH and note its hardware
   design assurance level (A-D).
2. Determine the verification methods for the item (full set for
   complex AEH, reduced for simple AEH).
3. Check whether independent verification is expected at the level.
4. Validate requirements-based test coverage against the level's
   ratio (0.98 for A/B, 0.95 for C/D).
5. Review the hardware/software integration evidence, then confirm
   the verification effort is complete against the required method
   set.

## Pitfalls

- Applying the full test/analysis/review set to simple AEH (or
  dropping test from complex AEH).
- Treating independence as optional at levels A/B.
- Passing coverage below the level's ratio (0.97 at A/B is not
  sufficient).
- Declaring verification complete while a required method is
  missing from the evidence.

## Behavior contract (gate 3)

The method-selection, independence, coverage, and completeness logic
is exercised by the gate 3 contract test:
scripts/test_verification.py against scripts/verification_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_verification.py

## Compliance

- Standards referenced, not reproduced: DO-254 text is proprietary
  (RTCA/EUROCAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
