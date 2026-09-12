---
name: structural-engineering-load-cases
description: "Use when define and audit structural engineering load cases for a space structure under ECSS-E-ST-32C clause 5.2: categorize each load case by type (limit, yield, ultimate, proof, fatigue, or creep-rupture), combine multi-source loads using absolute-sum or SRSS methods, apply scatter factors to account for load environment variability per clause 5.2h, identify sustained loading conditions that trigger creep deformation and creep-rupture assessments, and compute design loads by applying the appropriate safety factor for each category. Trigger: ecss, e-st-32c, e-st-32-structures-scope, structural-loads, combined-loads, scatter-factor, sustained-loading, creep-rupture, load-case-definition."
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
  tags: [ecss, e-st-32c, e-st-32-structures-scope, structural-loads, combined-loads, scatter-factor, sustained-loading, creep-rupture, load-case-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Engineering — Load Case Definition (space-systems/ecss/structural-engineering-load-cases)

Use when the task is defining, categorizing, or auditing structural
engineering load cases for a space structure in accordance with
ECSS-E-ST-32C clause 5.2 — covering load case types, combined loads,
scatter factors, and sustained-loading / creep-rupture assessments.

## Domain quick reference

- Clause 5.2 defines six recognized load case types: limit (the
  maximum load the structure must carry without permanent deformation),
  yield (limit load scaled by a yield factor to check first yield),
  ultimate (limit load scaled by an ultimate factor to check strength),
  proof (verification load for pressurized or sealed structures),
  fatigue (cyclic load history driving life assessment via S-N or
  fracture mechanics), and creep-rupture (sustained stress held for a
  duration sufficient to cause time-dependent fracture).  Every load
  case is assigned to exactly one of these categories before any
  calculation proceeds.
- Combined loads (clause 5.2d) arise when a structure is simultaneously
  exposed to mechanical, thermal, pressure, acoustic, shock, or
  vibration sources.  The combination method is either arithmetic
  absolute-sum (conservative, used when loads are correlated or their
  phase relationship is unknown) or square-root-of-sum-of-squares
  (SRSS, used when loads are statistically independent and random).
  The chosen method must be documented and justified.
- Scatter factors (clause 5.2h) account for statistical variability in
  the load environment — for example, ±3-sigma dispersions on thrust
  levels, vibration spectra, or thermal gradients.  A scatter factor
  >= 1.0 is applied to the limit load before the safety factor, so the
  design load = limit_load × scatter_factor × safety_factor.
- Sustained loading triggers creep assessment when the applied load is
  held for a duration that allows time-dependent deformation.  For
  creep-sensitive materials (aluminium alloys, titanium alloys, CFRP,
  GFRP, polymers, adhesives) a sustained duration >= 1 hour mandates
  both a creep deformation analysis and a creep-rupture check.  The
  creep-rupture margin of safety is allowable_stress / applied_stress - 1
  and must be >= 0.

## Workflow

1. Inventory every load event for the mission (launch, transfer-orbit,
   on-orbit, re-entry, landing, ground-handling, transportation,
   storage) and assign each to a recognized design situation.  Reject
   any situation not in the recognized set before proceeding.
2. For each design situation, identify all load sources (mechanical,
   thermal, pressure, acoustic, shock, vibration) and combine them into
   a scalar resultant.  Choose absolute-sum when loads are correlated or
   when the relative phase is unknown; choose SRSS when loads are
   demonstrably independent and random.  Document the justification.
3. Apply the scatter factor (>= 1.0) to each combined limit load per
   clause 5.2h.  A scatter factor of 1.0 is permitted only when the
   load characterization already contains the full statistical envelope.
4. Assign every load case to its category (limit, yield, ultimate,
   proof, fatigue, or creep-rupture).  Compute the design load by
   multiplying the scattered limit load by the safety factor for that
   category (yield: 1.1; ultimate: 1.25; proof: 1.0; fatigue: factor
   on life; creep-rupture: 1.25).
5. For each load case with a sustained duration, check whether the
   material is creep-sensitive and the duration meets or exceeds the
   creep threshold (1 hour by default).  If so, mandate both a creep
   deformation analysis and a creep-rupture check.
6. For each creep-rupture check, compute the margin of safety
   (allowable_creep_rupture_stress / applied_stress - 1) and flag any
   case where the margin is negative.
7. Validate every load case record: type, design situation, limit load,
   scatter factor, and (where applicable) duration and material must all
   be present and within their permitted ranges.  Collect all findings
   before reporting; an empty findings list indicates a compliant record.

## Pitfalls

- Applying the safety factor directly to the un-scattered limit load —
  the scatter factor must be applied first (scattered limit load =
  limit_load × scatter_factor); the safety factor then multiplies the
  already-scattered value.
- Combining correlated loads by SRSS — when the relative phase between
  two load sources is unknown or unfavorable, absolute-sum must be used;
  SRSS underestimates the resultant for partially correlated loads.
- Treating "no permanent deformation at limit load" as equivalent to
  "passes yield" — the yield check uses limit_load × yield_safety_factor
  and must be compared against the material's 0.2 % proof stress, not
  against the limit load directly.
- Omitting the creep-rupture check for a sustained load case on a
  creep-sensitive material because "no creep deformation was observed in
  short-term tests" — clause 5.2 requires a separate creep-rupture check
  even when elastic deformation is within limits; the two failure modes
  are independent.
- Setting scatter factor to 1.0 for a load environment that has not been
  statistically bounded — a scatter factor of 1.0 is only permissible
  when the load characterization already represents the full statistical
  envelope; using 1.0 otherwise underestimates the true design load.

## Behavior contract (gate 3)

The load-case categorization, combination, scatter, sustained-loading,
creep-rupture, design-load, and validation logic is exercised by the
gate 3 contract test: scripts/test_structural_engineering_load_cases.py
against scripts/structural_engineering_load_cases_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_structural_engineering_load_cases.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
