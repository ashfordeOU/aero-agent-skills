---
name: alignment-geometry-checks
description: "Use when verifying that structural components meet alignment accuracy, dimensional stability, and geometrical form requirements per ECSS-E-ST-32C clauses 4.6.3.19–4.6.3.21. Check each component's measured alignment (angular and translational) against its specified tolerance; assess dimensional change from baseline against the stability budget across thermal, hygroscopic, creep, and other drivers; verify geometrical form deviations (flatness, straightness, circularity, parallelism, perpendicularity, angularity, runout) against interface control drawing allowables; and aggregate findings to determine overall compliance. Trigger: ecss, e-st-32-structures-scope, alignment-checks, dimensional-stability, geometrical-control, tolerance-verification, structural-geometry, interface-control."
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
  tags: [ecss, e-st-32-structures-scope, alignment-checks, dimensional-stability, geometrical-control, tolerance-verification, structural-geometry, interface-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Verification — Alignment and Geometry Checks (space-systems/ecss/alignment-geometry-checks)

Use when the task is to verify alignment accuracy, dimensional stability, and
geometrical form control of structural components under ECSS-E-ST-32C clauses
4.6.3.19–4.6.3.21. The checks cover three distinct but related disciplines:
angular and translational alignment of components against their specified
tolerances, dimensional change from a baseline measurement against a
stability budget, and form deviations (flatness, straightness, circularity,
and similar) against interface-control-drawing allowables. A component is
only fully compliant when all three checks pass.

## Domain quick reference

- Clause 4.6.3.19 governs alignment checks: every component with a pointing
  or positional requirement must have a measured alignment value (angular
  in arcseconds or translational in millimetres) compared against the
  signed tolerance band specified in the interface control document (ICD).
  The check is per axis (tip, tilt, roll, and three translational axes) and
  a deviation that exceeds the half-band on any single axis constitutes a
  non-conformance requiring disposition.
- Clause 4.6.3.20 governs dimensional stability: a component's baseline
  dimension is measured before the environmental cycle, and the post-cycle
  dimension is compared against the allowable change (the stability budget).
  The four recognised stability drivers are thermal (CTE-driven expansion or
  contraction), hygroscopic (moisture absorption or desorption in composites),
  creep (time-dependent plastic flow under sustained load), and other
  (catch-all for documented but non-standard drivers). Each driver is
  tracked separately to support root-cause disposition.
- Clause 4.6.3.21 governs geometrical control: the form of surfaces and
  features is compared against allowables stated in the ICD. Recognised form
  types are flatness, straightness, circularity, cylindricity, parallelism,
  perpendicularity, angularity, and runout. Deviations are always non-negative
  (magnitude of form error); an allowable of zero or below is an input error,
  not a compliant state.

## Workflow

1. Collect all alignment measurements for each component: component ID,
   axis, measured value, allowable tolerance (symmetric half-band), and unit.
   Reject any entry with a non-positive tolerance before it enters the
   comparison — a zero or negative tolerance is an input error that must be
   resolved against the ICD before proceeding.
2. For each alignment entry, compute the margin as (allowable − |measured|).
   A non-negative margin is a pass; a negative margin is a fail. Record the
   magnitude of exceedance for every fail so that the non-conformance report
   has a quantified delta.
3. Collect dimensional stability measurements: component ID, baseline
   dimension, post-environment dimension, stability budget, and driver.
   Validate that the driver is one of the four recognised types before
   computing the dimensional change. A non-positive stability budget is an
   input error.
4. For each stability entry, compute the absolute dimensional change from
   baseline and compare against the budget. Flag exceedances with the
   signed delta and the driver so the disposition team can target the correct
   physical mechanism.
5. Collect geometry control measurements: component ID, geometry type,
   measured deviation (non-negative), and allowable deviation. Reject any
   geometry type that is not in the set of eight recognised types — an
   unknown type indicates a missing ICD entry, not a new compliant state.
6. For each geometry entry, compute the margin as (allowable − measured).
   Non-negative margin is a pass; negative margin is a fail.
7. Aggregate all alignment, stability, and geometry results into a single
   compliance summary. The component assembly is compliant only when the
   total failure count is zero across all three check types.

## Pitfalls

- Applying the alignment tolerance as a full-band rather than a half-band
  (symmetric ±): the ICD tolerance is the half-band, so a measured value of
  +8 arcsec against a ±10 arcsec tolerance has 2 arcsec margin, not 18.
  Using the full band doubles the apparent margin and masks real exceedances.
- Omitting the driver field for dimensional stability and reporting a single
  aggregate change: thermal and hygroscopic mechanisms require different
  corrective actions, and lumping them prevents root-cause disposition.
- Treating a missing stability budget as a pass: an unrecorded budget means
  the stability requirement was never captured in the ICD, which is itself a
  finding, not a compliant condition.
- Accepting a negative measured deviation for a geometry check as meaning
  "within tolerance in the other direction": form deviations are magnitudes
  (non-negative by definition); a negative input is a data error that must
  be resolved before the check is run.
- Allowing an unrecognised geometry type to pass through as a default pass:
  a type not in the ICD-recognised set indicates an incomplete interface
  definition, not a compliant surface.

## Behavior contract (gate 3)

The alignment comparison, dimensional stability, and geometry control logic is
exercised by the gate 3 contract test:
scripts/test_alignment_geometry_checks.py against
scripts/alignment_geometry_checks_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_alignment_geometry_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
