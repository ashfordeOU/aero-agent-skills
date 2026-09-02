---
name: configuration-management
description: "Use when you must determine the DO-254 configuration management action for a hardware change: classify the change class, decide whether a formal engineering change order (ECR/ECO) with reverification applies, and produce the hardware configuration index (HCI) entry against the current baseline. A change to form, fit, or function, any safety effect, or complex hardware is class 1 with baseline update, reverification, and independent review; otherwise class 2 uses documented but lighter review. Trigger: do 254 hardware configuration, change class, engineering change order, ecr, eco, configuration baseline, hardware configuration index, hci."
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
  tags: [do-254, configuration, change-class, ecr, eco, hci, hardware, review-independence]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-254 Configuration Management (avionics/do254/configuration-management)

Use when the task is DO-254 configuration management for airborne
electronic hardware: classifying a hardware change, deciding the
ECR/ECO path, and maintaining the hardware configuration index.
The logic handles nominal categories and identifiers only, so no
physical quantities and no unit conversions apply.

## Domain quick reference

- DO-254 hardware configuration management keeps baselines of
  hardware lifecycle data and controls changes through engineering
  change requests and orders (ECR/ECO).
- The hardware configuration index (HCI) identifies each item, its
  revision, and the baseline it belongs to.
- A change class (1 or 2) sets the depth of control: class 1
  requires a formal ECR/ECO, a baseline update, and reverification.
- Class 1 applies when form, fit, or function changes, when any
  safety effect is present, or when the item is complex AEH.
- Class 2 changes are documented and reviewed, but do not force
  reverification or independent review.
- Complex hardware changes are reviewed independently of the design
  activity that proposed them.
- DO-254 is accepted via FAA AC 20-152A.

## Workflow

1. Collect the change attributes: hardware class, safety effect,
   and whether form, fit, or function changes.
2. Classify with change_class to get the change class and its
   rationale.
3. Map the class with cm_actions to the CM actions: baseline
   update, ECR/ECO, reverification, independent review.
4. Record the item in the HCI with hci_entry (item, revision,
   baseline).
5. Attach every ECR/ECO and its disposition to the baseline.

## Pitfalls

- Treating a simple item's change as class 2 when a safety effect
  exists; safety effect alone forces class 1.
- Skipping reverification on a class 1 change.
- Reviewing a complex hardware change with the same people who
  proposed it, which breaks independence.
- Recording an HCI entry without the baseline identifier.

## Behavior contract (gate 3)

The change classification, CM action mapping, and HCI formatting
logic is exercised by the gate 3 contract test:
scripts/test_config_mgmt_logic.py against
scripts/config_mgmt_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_config_mgmt_logic.py

## Compliance

- Standards referenced, not reproduced: DO-254 text is proprietary
  (RTCA/EUROCAE); summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
