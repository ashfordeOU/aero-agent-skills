---
name: special-item-fracture-control
description: "Use when evaluate fracture control compliance for special structural items under ECSS-E-ST-32C §8.5–8.9: categorize each item as non-metallic, rotating machinery, glass, fastener, or EDM-treated alloy; apply the category-specific acceptance method (proof-test factor ≥ 1.5 for non-metallics, burst-speed margin ≥ 1.25 for rotating parts, proof-stress ratio ≥ 1.3 for glass, grade-and-installation exemption check for fasteners, recast-layer removal ≥ 0.1 mm for EDM alloys); and confirm each item meets its threshold before structural release. Trigger: ecss, e-st-32-structures-scope, fracture-control, special-items, non-metallics, rotating-machinery, glass, fasteners, edm-alloys."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, fracture-control, special-items, non-metallics, rotating-machinery, glass, fasteners, edm-alloys]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Special-Item Fracture Control (space-systems/ecss/special-item-fracture-control)

Use when the task is the fracture control assessment of special structural
items per ECSS-E-ST-32C clauses 8.5–8.9, covering non-metallics, rotating
machinery, glass items, fasteners, and EDM-treated alloys. Each item category
carries its own acceptance method and threshold that replaces the standard
metallic fracture-mechanics workflow.

## Domain quick reference

- **Non-metallics (§8.5):** Standard linear elastic fracture mechanics does
  not apply. Compliance is demonstrated by one of three methods: proof test
  (minimum proof factor 1.5× the design load), analysis using
  material-specific failure criteria, or similarity to a previously qualified
  item. The failure mode must be identified before the method is selected.

- **Rotating machinery (§8.6):** Fracture-critical rotating parts must reach
  a burst speed that is at least 1.25× the maximum operating speed. The burst
  margin is the ratio burst_speed / operating_speed and must be ≥ 1.25. Items
  that fall short must be redesigned or dispositioned via formal waiver with
  residual-risk justification.

- **Glass (§8.7):** Glass items are treated as inherently flawed. Compliance
  is via proof loading imposing a proof stress at least 1.3× the maximum
  design stress. Items that survive the proof load are cleared; those that
  fracture during proof are screened out. Abraded glass uses the same ratio
  but starts from a lower characteristic strength, so the proof load must
  account for the abraded surface condition.

- **Fasteners (§8.8):** Standard aerospace fasteners installed under torque
  control and meeting the applicable material grade (A or B) may qualify for
  a fracture-control exemption, provided they are not in tension-critical
  joints. Non-standard fasteners, those in fracture-susceptible alloys, or
  those in tension-critical joints require a full fracture analysis or an
  elevated proof test.

- **EDM-treated alloys (§8.9):** Electrical discharge machining leaves a
  brittle recast layer (typically 10–50 µm). The layer must be removed to a
  depth of at least 0.1 mm by etching, grinding, or an equivalent approved
  process before any fracture assessment proceeds. An approved removal process
  must be documented; the removal depth and process together constitute the
  EDM compliance record.

## Workflow

1. Identify each structural item by category — non-metallic, rotating
   machinery, glass, fastener, or EDM-treated alloy. Reject any item whose
   category is not one of the five defined types before it enters the
   assessment.

2. For non-metallic items, record the failure mode and the chosen compliance
   method (proof test, analysis, or similarity). If proof test, verify the
   applied proof factor is ≥ 1.5; if the factor falls short, flag a
   compliance gap. Analysis and similarity methods proceed to documentary
   review rather than numeric threshold check.

3. For rotating machinery, compute the burst margin as burst_speed divided by
   operating_speed. Flag any item where the computed margin is < 1.25.

4. For glass items, compute the proof stress ratio as proof_stress divided by
   design_stress. Flag any item where the ratio is < 1.3.

5. For fasteners, confirm that the grade is A or B, that installation is
   torque-controlled, and that the joint is not tension-critical. A fastener
   failing any of the three conditions is not exempt and is forwarded to the
   standard fracture analysis workflow.

6. For EDM-treated alloys, confirm that the recast-layer removal depth on
   record is ≥ 0.1 mm and that an approved removal process is documented.
   Flag items where either the depth is insufficient or the process is absent.

7. Aggregate findings per item; an item is fracture-control compliant only
   when its specific acceptance check returns no findings.

## Pitfalls

- Applying the metallic fracture-mechanics workflow (crack size, K_Ic, crack
  growth rate) to a non-metallic item — the material fracture response is
  different and the standard metallic thresholds do not transfer.

- Treating a burst-margin shortfall as a minor deviation — a rotating part
  that fails to reach 1.25× operating speed can shed fragments with
  catastrophic kinetic energy and must be dispositioned before flight.

- Accepting an EDM part without confirming recast-layer removal — the
  recast layer nucleates cracks under cycling; the absence of confirmed
  removal voids any subsequent fracture analysis regardless of the computed
  crack-growth result.

- Using a glass proof-test ratio below 1.3 and reading the test as passing
  — a ratio below 1.3 does not bound the flaw population at the design stress
  and leaves undetected critical flaws that can propagate in service.

- Granting a fastener exemption based solely on diameter or material grade
  without also checking installation method and joint type — the exemption is
  conditional on all three criteria simultaneously.

## Behavior contract (gate 3)

The item-categorization, proof-factor, burst-margin, proof-stress-ratio,
fastener-exemption, and EDM-removal logic is exercised by the gate 3 contract
test: scripts/test_special_item_fracture_control.py against
scripts/special_item_fracture_control_logic.py (stdlib unittest, offline).
Run:

python3 scripts/test_special_item_fracture_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
