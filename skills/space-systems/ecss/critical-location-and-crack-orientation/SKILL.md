---
name: critical-location-and-crack-orientation
description: "Use when determine the most critical crack location and orientation for a structural item under ECSS-E-ST-32C clause 7.2.2: enumerate candidate crack initiation sites (stress concentrations, fastener holes, weld toes, surface defects), pair each site with all plausible crack orientations (axial, circumferential, radial, oblique, transverse), compute the stress intensity factor for each pair using net-section stress and a geometry correction factor, evaluate the fracture margin against material toughness, and select the pair with the lowest margin as the governing combination for subsequent crack-growth life and critical-crack-size calculations. Trigger: ecss, e-st-32c, fracture-control, crack-location, crack-orientation, stress-intensity-factor, fracture-margin, critical-crack, fracture-assessment."
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
  tags: [ecss, e-st-32c, fracture-control, crack-location, crack-orientation, stress-intensity-factor, fracture-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Critical Crack Location and Orientation (space-systems/ecss/critical-location-and-crack-orientation)

Use when the task is to determine the most critical crack location and orientation
for a structural item under ECSS-E-ST-32C clause 7.2.2 — enumerating candidate
initiation sites, pairing each with plausible crack orientations, computing the
stress intensity factor for every pair, and selecting the pair with the lowest
fracture margin as the governing combination for crack-growth life and
critical-crack-size calculations.

## Domain quick reference

- Clause 7.2.2 requires that for each item subject to fracture control, the
  single most critical combination of crack location and crack orientation is
  identified before any subsequent fracture calculation proceeds. Choosing a
  non-conservative location or orientation propagates an unconservative error
  through the entire fracture-control analysis.
- Candidate crack initiation sites include geometric discontinuities (fastener
  holes, countersinks, fillet radii, weld toes, ply drop-offs), surface
  machining marks, and regions of peak net-section stress identified from
  the structural stress analysis.
- Plausible orientations at each site are those consistent with the local stress
  field: a crack tends to propagate perpendicular to the maximum principal
  stress, so the first orientation to assess is always perpendicular to the
  peak stress direction. Secondary orientations (angled, through-thickness,
  longitudinal) are required when the stress field is biaxial or when geometry
  constrains propagation direction.
- The stress intensity factor (SIF) for each candidate is computed as
  K = F × σ × √(π a), where F is a dimensionless geometry and
  boundary-correction factor (e.g. 1.12 for a surface crack in a semi-infinite
  body), σ is the net-section stress at the site, and a is the assumed half
  crack length derived from the initial flaw size in the fracture-control plan.
- The fracture margin for a candidate is MoS = K_c / K − 1, where K_c is the
  plane-strain fracture toughness of the material at the applicable temperature.
  The candidate with the lowest MoS is the critical location-orientation.

## Workflow

1. Retrieve the fracture-control plan for the item to obtain the initial flaw
   size (a) for each candidate site and the applicable material fracture
   toughness (K_c). Reject any candidate whose flaw size or toughness is not
   on record before it enters the assessment.
2. For each candidate site, list every plausible crack orientation (at minimum:
   perpendicular to the maximum principal stress; additional orientations where
   loading is multiaxial or geometry constrains propagation). Reject an
   orientation whose associated net-section stress is zero or negative as
   non-contributing to fracture.
3. For each (site, orientation) pair, compute K using the applicable geometry-
   correction factor F. Use the conservative F = 1.12 surface-crack value when
   a more precise factor is not available from a stress-intensity handbook or
   finite-element analysis.
4. Compute MoS = K_c / K − 1 for each pair. A negative margin indicates that
   the assumed initial flaw would cause immediate fracture under the applied
   stress; flag this as a critical finding requiring immediate design or
   material review before proceeding.
5. Rank all pairs by ascending MoS and identify the pair with the lowest value
   as the critical location-orientation for the item.
6. Record the critical pair (site identifier, orientation label, K, K_c, MoS)
   in the fracture-control analysis report. This pair is the sole basis for
   the crack-growth life calculation and critical-crack-size derivation in
   subsequent assessment steps.

## Pitfalls

- Assessing only the highest-stress location without also varying orientation:
  a site with moderate stress and an unfavorable geometry factor can produce a
  higher K than the nominally highest-stress site, and will be missed if only
  one orientation is checked per site.
- Using fracture toughness without temperature and thickness corrections:
  K_c is strongly thickness-dependent (plane-stress versus plane-strain
  transition) and temperature-dependent; using the ambient room-temperature,
  thick-panel value for a thin sheet at a cryogenic condition can be
  unconservative.
- Treating a zero or compressive net-section stress as precluding crack
  extension: ECSS fracture control requires the most conservative credible
  loading condition; secondary loads and residual-stress fields must be
  included before concluding a site has no tensile stress.
- Rounding a slightly negative MoS to zero and recording the item as passing:
  a negative margin is a fracture prediction under the assumed flaw and load
  — it must be documented as a finding and resolved, not silently discarded.

## Behavior contract (gate 3)

The stress-intensity-factor calculation, fracture-margin derivation,
critical-candidate selection, ranking, and all input-validation error paths are
exercised by the gate 3 contract test:
scripts/test_critical_location_and_crack_orientation.py against
scripts/critical_location_and_crack_orientation_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_critical_location_and_crack_orientation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
