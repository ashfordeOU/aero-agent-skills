---
name: hardware-planning
description: "Use when you must plan DO-254 design assurance for airborne electronic hardware: classify an item as simple or complex AEH, scope the plan for hardware aspects of certification (PHAC) and the hardware design assurance data, and plan requirements capture, verification, and configuration management for the item. Complex AEH (programmable logic, processors, or designs whose correct behavior cannot be fully established from top-level data alone) follows the full design assurance process; simple AEH uses a reduced but still planned process. Trigger: DO-254 hardware planning, airborne electronic hardware, PHAC, simple vs complex hardware, hardware design assurance, programmable logic."
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
  tags: [do-254, hardware, phac, certification, verification, planning]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-254 Hardware Planning (avionics/do254/hardware-planning)

Use when the task is DO-254 design assurance planning for airborne
electronic hardware: classifying the item and scoping its assurance
data.

## Domain quick reference

- DO-254 distinguishes simple from complex airborne electronic hardware
  (AEH). Complex AEH (programmable logic, processors, significant
  internal state, or hardware whose correct behavior cannot be fully
  established from top-level data alone) follows the full design
  assurance process.
- Safety-significant items are treated as complex unless a documented
  justification shows a reduced process is adequate.
- Complex AEH planning: PHAC plus requirements capture, conceptual and
  detailed design, verification, configuration management, and process
  assurance data.
- Simple AEH uses a reduced but still planned process: a hardware plan,
  verification, and configuration management.
- DO-254 is accepted via FAA AC 20-152A.

## Workflow

1. Classify the item: simple or complex AEH.
2. Complex: scope the PHAC and the full design assurance data set.
3. Simple: scope the reduced process (still planned, still verified).
4. Plan requirements capture, verification, and configuration
   management for the item.
5. Confirm the classification with the certification authority early.

## Pitfalls

- Calling an FPGA or processor item "simple" without justification.
- Skipping verification for simple AEH (reduced is not none).
- No PHAC for complex AEH.
- Classification made without authority agreement.

## Behavior contract (gate 3)

The AEH classification and planning-artifact logic is exercised by the
gate 3 contract test: scripts/test_hardware_planning.py against
scripts/hardware_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_hardware_planning.py

## Compliance

- Standards referenced, not reproduced: DO-254 text is proprietary
  (RTCA/EUROCAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
