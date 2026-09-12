---
name: metallic-special-pressurized-equipment
description: "Use when assess metallic special pressurized equipment (MSPE) under ECSS-E-ST-32 clause 4.6.1: categorize each item as battery, heat pipe, loop heat pipe (LHP), capillary pumped loop (CPL), cryostat, sealed container, or hazardous container; verify that the demonstrated proof pressure meets the 1.5× MAWP factor and the burst pressure meets the 2.0× MAWP factor; check the operating temperature against the allowable range for the equipment family; confirm the metallic wall thickness is above the structural minimum; and derive the hazard level based on working fluid nature and pressure. Trigger: ecss, e-st-32-structures-scope, mspe, pressurized-equipment, batteries, heat-pipes, cryostats, hazardous-containers, pressure-factors."
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
  tags: [ecss, e-st-32-structures-scope, mspe, pressurized-equipment, batteries, heat-pipes, cryostats, hazardous-containers, pressure-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Metallic Special Pressurized Equipment (space-systems/ecss/metallic-special-pressurized-equipment)

Use when the task is the structural assessment of metallic special pressurized
equipment under ECSS-E-ST-32 clause 4.6.1 — covering batteries, heat pipes,
loop heat pipes (LHP), capillary pumped loops (CPL), cryostats, sealed
containers, and hazardous containers.  The workflow categorizes each item by
type, verifies proof and burst pressure margins, checks operating temperature
limits, and assigns a hazard level.

## Domain quick reference

- Clause 4.6.1 groups non-standard pressure vessels into seven families, each
  with its own temperature operating window and structural verification
  requirements.  Batteries add electrolyte-vapour pressure; heat pipes and
  LHP/CPL operate with a two-phase working fluid; cryostats must handle
  cryogenic implosion and thermal-cycling fatigue; hazardous containers require
  elevated scrutiny regardless of pressure level.
- Two pressure factors govern metallic MSPE: the proof factor (demonstrated
  proof pressure ≥ 1.5 × MAWP) and the burst factor (burst pressure ≥ 2.0 ×
  MAWP for fracture-controlled metallic hardware).  Both must be satisfied
  independently; passing one does not compensate for failing the other.
- Hazard level is derived from working fluid nature (hazardous vs. inert) and
  pressure magnitude: a hazardous fluid at > 5 bar MAWP reaches CRITICAL; a
  cryostat is always HIGH regardless of pressure; a battery without hazardous
  content is MEDIUM; low-pressure inert containers are LOW.
- Leak-before-burst (LBB) applicability is determined by the ratio of fracture
  toughness to yield strength relative to wall thickness: a small (K_Ic/σ_y)²
  compared with t/10 confirms that a through-wall crack remains stable long
  enough to produce a detectable leak before catastrophic fracture.

## Workflow

1. Receive the MSPE inventory.  For each item, confirm the equipment type is
   one of the seven accepted families.  Reject unrecognized types before they
   enter the assessment pipeline.
2. Check the operating temperature against the family-specific allowable range.
   Flag an out-of-range condition as an error before proceeding to pressure
   checks, because temperature directly affects material allowables and fluid
   state.
3. Verify the metallic wall thickness is at or above the minimum (0.5 mm).
   Sub-minimum walls cannot sustain the required proof or burst loading in the
   fracture-controlled regime.
4. Confirm the demonstrated proof pressure is at least 1.5 × MAWP.  A margin
   below this threshold is a blocking error.  Warn if the proof pressure
   exceeds 3.0 × MAWP, which signals a potential over-test condition that
   could damage the vessel.
5. Confirm the burst pressure is at least 2.0 × MAWP.  A margin below this
   threshold is a blocking error independent of the proof check.
6. Derive the hazard level (CRITICAL / HIGH / MEDIUM / LOW) from fluid nature
   and MAWP magnitude.  Record the hazard level in the result for use in
   safety category assignment and proximity-to-personnel constraints.
7. For items where LBB is invoked as a design rationale, apply the LBB check:
   compute (K_Ic / σ_y)² and compare it with t/10.  LBB is applicable only
   when the crack-tip length scale is smaller than this threshold.
8. Aggregate findings per item.  An item is compliant when it carries no
   error-level findings.  Report the overall inventory pass/fail flag.

## Pitfalls

- Treating proof margin and burst margin as interchangeable — a high proof
  factor does not compensate for a burst factor below 2.0; each threshold is
  verified independently.
- Applying generic pressure-vessel temperature limits to cryostats — the
  cryogenic family has a distinct operating window (4 K to 120 K) that is far
  below the room-temperature envelope used for batteries and sealed containers.
- Invoking LBB without checking the material criterion — LBB is a
  demonstration-based rationale, not a default; it must be supported by
  K_Ic / σ_y data specific to the wall material and thickness.
- Reading an absent hazard-level assignment as LOW — an unassigned hazard level
  means the fluid nature and pressure have not yet been evaluated, which is
  itself a finding, not a default pass.
- Conflating the MSPE hazardous-container category with non-metallic or
  composite-overwrapped designs — this leaf covers metallic pressure boundaries
  only; composite-overwrapped pressure vessels (COPV) follow a separate clause.

## Behavior contract (gate 3)

The equipment categorization, pressure factor, temperature range, wall
thickness, hazard level, and LBB logic are exercised by the gate 3 contract
test: scripts/test_metallic_special_pressurized_equipment.py against
scripts/metallic_special_pressurized_equipment_logic.py (stdlib unittest,
offline).  Run:

```
python3 scripts/test_metallic_special_pressurized_equipment.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
