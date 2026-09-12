---
name: insert-analysis
description: "Use when determine the structural adequacy of mechanical inserts embedded in metallic, honeycomb sandwich, or composite structures per ECSS-E-ST-32C clause 4.6.2.16: categorize each insert by substrate type (metal, honeycomb core, composite laminate), select the governing failure mode (pull-out for metal threads, core shear and potting failure for honeycomb potted inserts, bearing and pull-through for composites), compute the allowable strength for each mode, apply the quadratic interaction equation when axial and shear loads act simultaneously, and derive the margin of safety with the project factor of safety applied. Flag any insert with a negative margin or a missing strength allowable. Trigger: ecss, e-st-32-structures-scope, insert-analysis, honeycomb, potted-insert, composite-bearing, margin-of-safety, structural-fastener."
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
  tags: [ecss, e-st-32-structures-scope, insert-analysis, honeycomb, potted-insert, composite-bearing, margin-of-safety, structural-fastener]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Insert Analysis (space-systems/ecss/insert-analysis)

Use when the task is the structural assessment of mechanical inserts per
ECSS-E-ST-32C clause 4.6.2.16 — covering potted inserts in honeycomb
sandwich panels, threaded inserts in solid metal, and inserts in composite
laminates. The analysis categorizes each insert by substrate, identifies the
governing failure mode, computes allowable strengths, and evaluates the
combined-load interaction equation to derive a margin of safety.

## Domain quick reference

- Three substrate families are addressed. For **metal**, the governing
  failure modes are thread stripping under axial load (pull-out) and
  cross-section shear. For **honeycomb sandwich**, the dominant axial failure
  is shear of the potting cylinder perimeter against the surrounding core
  (core shear pull-out); lateral load is carried by the potting cross-section.
  For **composite laminates**, axial load drives pull-through failure (shear
  around the fastener perimeter through the laminate thickness) and lateral
  load drives bearing failure (contact pressure on the projected area).
- Combined-load interaction follows the quadratic form widely used for
  fastener analysis: R = (P/F_pullout)² + (V/F_shear)², where R ≤ 1.0 is
  within the envelope. Margin of safety is derived as MS = 1/√R − 1; a
  negative MS indicates exceedance.
- The project factor of safety is applied to the applied loads before
  evaluating R, not to the allowable strengths. When the factor of safety
  scales both load components, the interaction surface contracts uniformly.
- Every strength allowable (core shear, potting shear, thread material,
  laminate bearing, interlaminar shear) must be on record before the
  assessment can proceed. A missing allowable is itself a finding, not a
  default pass.

## Workflow

1. Inventory every insert in the structure and categorize each one by
   substrate type: metal, honeycomb, or composite. Reject any insert whose
   substrate cannot be identified before it enters the strength calculation.
2. For each insert, determine the applied axial load P (pull-out direction)
   and lateral load V (shear direction) from the design load case. Apply the
   project factor of safety to obtain the factored loads P_f and V_f.
3. Compute the pull-out allowable for the identified substrate:
   - Metal: F_pullout = π × d_nom × L_engage × τ_material
   - Honeycomb potted: F_pullout = π × d_pot × t_core × τ_core
   - Composite: F_pullout = π × d_bolt × t_lam × τ_ILS (pull-through)
4. Compute the shear allowable for the identified substrate:
   - Metal: F_shear = (π/4) × d_nom² × τ_material
   - Honeycomb potted: F_shear = (π/4) × d_pot² × τ_pot
   - Composite: F_shear = d_bolt × t_lam × σ_bearing
5. Evaluate the quadratic interaction ratio R = (P_f/F_pullout)² + (V_f/F_shear)².
   Compute MS = 1/√R − 1. When P_f and V_f are both zero, MS is unbounded
   (no load applied). An insert is structurally adequate when MS ≥ 0.
6. For each insert with MS < 0, record the dominant failure mode: pull-out
   if P_f/F_pullout ≥ V_f/F_shear, otherwise shear (or bearing for composite).
   Report every insert with a negative MS or a missing allowable as a finding
   requiring resolution before the structure is considered compliant.

## Pitfalls

- Applying the factor of safety to the allowable rather than the load. The
  standard practice is to scale the applied load upward, not the allowable
  downward. Reversing this changes nothing when only one load component is
  non-zero, but it changes the interaction surface shape when both components
  are non-zero.
- Using the pull-out formula for honeycomb without verifying that the potting
  diameter is the potting cylinder outer diameter, not the fastener shank
  diameter. Using the shank diameter understates the shear perimeter and
  produces an unconservative pull-out allowable.
- Treating a potted insert in honeycomb as if it were a threaded insert in
  solid metal and applying the thread-stripping formula. The governing failure
  mechanism is different (core shear perimeter, not thread engagement length),
  so the formula and the required inputs differ.
- Omitting the pull-through check for composite inserts when the axial load
  is small but non-zero. The pull-through strength for thin laminates can be
  low, and the interaction with bearing load is non-negligible.
- Reading a zero factored load as a pass without confirming the load case is
  complete. A missing load component is not the same as a demonstrated
  zero-load condition.

## Behavior contract (gate 3)

The substrate categorization, strength calculations, interaction ratio,
margin-of-safety derivation, and error-path logic are exercised by the
gate 3 contract test:
scripts/test_insert_analysis.py against scripts/insert_analysis_logic.py
(stdlib unittest, offline, deterministic). Run:
python3 scripts/test_insert_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
