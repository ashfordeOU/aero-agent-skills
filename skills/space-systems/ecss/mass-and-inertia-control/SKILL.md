---
name: mass-and-inertia-control
description: "Use when derive spacecraft mass and inertia property budgets, track
  current best estimate (CBE) against allocated mass at every design phase, compute
  system-level center of mass and moments of inertia from component contributions,
  and verify that phase-appropriate mass margins are maintained to feed the Structural
  Mechanics Summary (SMS) document requirements definition (DRD). Apply at each
  design review to roll up subsystem mass entries, flag budget exceedances, confirm
  margin compliance against phase-specific minimums (20 % Phase A through 5 % Phase D),
  and confirm all inertia properties are traceable to the system reference frame.
  Trigger: ecss, e-st-32-structures-scope, mass-budget, inertia-properties,
  center-of-mass, moments-of-inertia, sms-drd, mass-margin, phase-margin."
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
  tags: [ecss, e-st-32-structures-scope, mass-budget, inertia-properties, center-of-mass, moments-of-inertia, sms-drd, mass-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mass and Inertia Property Control (space-systems/ecss/mass-and-inertia-control)

Use when the task is building or updating the spacecraft mass and inertia
property budget per ECSS-E-ST-32 clause 4.5.5, rolling it up across
subsystems, checking that design-phase mass margins are met, and producing
the properties needed to populate the Structural Mechanics Summary (SMS) DRD.

## Domain quick reference

- ECSS-E-ST-32 clause 4.5.5 requires that mass and inertia properties be
  tracked at every design phase through a formal budget, with a phase-specific
  minimum margin reserved between the current best estimate (CBE) and the
  allocated (budgeted) mass. Margins tighten as design matures: 20 % in Phase
  A, 15 % in Phase B, 10 % in Phase C, 5 % in Phase D.
- The budget is hierarchical: component-level CBE values roll up to subsystem
  totals, which roll up to the system total. Each level carries its own CBE,
  allocation, and margin.
- The center of mass (CoM) and moments of inertia (Ixx, Iyy, Izz) about a
  defined system reference point are derived from the same component mass entries
  and their positions in the system coordinate frame. All inertia properties
  must be explicitly tied to that reference frame.
- Budget exceedances (CBE > allocation) and margin violations (margin below
  the phase minimum) are both non-compliances that block design review passage.
  An unset allocation is itself a finding; "no allocation recorded" is not a pass.
- The SMS DRD collects total mass, CoM coordinates, principal moments of inertia,
  and the margin status for the current phase.

## Workflow

1. Collect every component or assembly with its name, CBE mass (kg),
   allocated mass (kg), and (x, y, z) position in the system reference frame
   (m). Reject entries with missing fields, negative CBE, zero or negative
   allocation, or non-numeric position coordinates before they enter the budget.
2. Roll up component entries to the subsystem level, then aggregate subsystem
   totals to the system level. Record total CBE, total allocation, margin in
   kg, and margin as a percentage of allocation at each level.
3. Check the system-level margin percentage against the minimum required for
   the current design phase (A → 20 %, B → 15 %, C → 10 %, D → 5 %). Flag
   any shortfall as a budget non-compliance.
4. Compute the system center of mass by calculating the mass-weighted average
   of component positions using CBE masses. Flag if total CBE mass is zero
   (undefined CoM).
5. Compute moments of inertia about the system reference point using the
   point-mass approximation: Ixx = Σ m_i (Δy_i² + Δz_i²), and equivalently
   for Iyy and Izz, where Δx_i, Δy_i, Δz_i are offsets from the reference point.
   Carry the reference point coordinates explicitly in the output.
6. Assemble the SMS DRD fields: total CBE, total allocation, margin (kg and %),
   phase margin requirement, compliance flag, CoM (x, y, z) in metres, and
   Ixx / Iyy / Izz in kg·m².
7. Flag every finding (allocation exceedance, margin shortfall, missing
   allocation) as a separate entry; a budget is compliant only when the
   finding list is empty.

## Pitfalls

- Treating an allocation-exceedance entry as a margin shortfall — they are
  distinct: an exceedance means CBE > allocation, a margin shortfall means
  (allocation − CBE) / allocation < phase minimum. Both must be flagged, but
  separately.
- Computing CoM from allocated mass instead of CBE mass — the center of mass
  reflects actual estimated mass, not the budget envelope; using allocated
  values displaces the CoM from the design truth.
- Dropping the reference point coordinates from the inertia output — any MoI
  value is meaningless without the point about which it is computed. Always
  carry the reference point in the report.
- Reading a zero margin as compliant in Phase D — the requirement is ≥ 5 %;
  a zero-margin condition fails Phase D regardless of whether CBE equals
  allocation exactly.
- Rolling up inertia values arithmetically across subsystems — moments of
  inertia do not add directly unless all subsystem values share the same
  reference point; always compute from component-level positions.

## Behavior contract (gate 3)

The mass budget, margin check, CoM, MoI, subsystem roll-up, and SMS DRD
field generation logic is exercised by the gate 3 contract test:
scripts/test_mass_and_inertia_control.py against
scripts/mass_and_inertia_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_mass_and_inertia_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
