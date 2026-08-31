---
name: environmental-qualification
description: "Use when planning or reviewing DO-160 environmental qualification of airborne equipment: map equipment categories to applicable test-condition sections (temperature, altitude, humidity, vibration, EMC, lightning, and others), verify that the planned test matrix covers every required section, and check operating-temperature ranges per equipment category. Section names and typical category temperature ranges are provided as reference data, with category-specific exclusions to be confirmed against the current revision; all logic is deterministic, offline stdlib. Trigger: DO-160, environmental qualification, test conditions, temperature, altitude, vibration, EMC, lightning, humidity, equipment category."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-160
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do160
  tags: [do-160, environmental-qualification, test-conditions, temperature, altitude, vibration, emc, lightning, humidity, equipment-category]
  version: 0.1.0
  author: AeroSkills
---

# DO-160 Environmental Qualification (avionics/do160/environmental-qualification)

Use when the task is DO-160 environmental qualification of airborne
equipment: scoping the applicable test-condition sections, checking
the planned test matrix for completeness, and validating
operating-temperature ranges per equipment category.

## Domain quick reference

- DO-160G (RTCA, EUROCAE twin ED-14G) defines environmental test
  conditions and procedures for airborne equipment, organized by
  numbered sections.
- Core sections include: 4 Temperature and altitude, 5 Temperature
  variation, 6 Humidity, 7 Operational shocks and crash safety,
  8 Vibration, 9 Explosion proofness, 10 Waterproofness, 11 Fluids
  susceptibility, 16 Power input, 19 Induced signal susceptibility,
  20 Radio frequency susceptibility, 21 Emission of radio frequency
  energy, 22 Lightning induced transient susceptibility,
  23 Lightning direct effects, 24 Icing, 25 Electrostatic discharge.
- Equipment categories (e.g. A1, B2) carry typical operating
  temperature ranges; category-specific section exclusions must be
  confirmed against the current revision.
- The qualification test matrix should cover every applicable
  section for the equipment category.

## Workflow

1. Confirm the applicable DO-160 revision and the equipment category.
2. Map the category to the required test-condition sections.
3. Compare the planned test matrix against the required sections and
   list what is missing.
4. Validate the operating-temperature range for the category.
5. Confirm category-specific exclusions against the current
   revision before freezing the matrix.

## Pitfalls

- Planning a matrix without section 22 (lightning induced transient
  susceptibility) or section 8 (vibration) for equipment that needs
  them.
- Relying on typical temperature ranges without checking the current
  revision's category table.
- Assuming every section applies to every category (exclusions
  exist; confirm them).
- Confusing section numbers (power input is 16, ESD is 25).

## Behavior contract (gate 3)

The logic is exercised by the gate 3 contract test:
scripts/test_environmental_qualification.py against
scripts/environmental_qualification_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_environmental_qualification.py

## Compliance

- Standards referenced, not reproduced: DO-160 text is proprietary
  (RTCA); summary-only per standards-map.yaml and brief 06.
- Section names and temperature ranges are typical reference data;
  verify against the current revision (e.g. DO-160G) before use.
- compliance: STANDARDS-REF, gated: false.
