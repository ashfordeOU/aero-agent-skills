---
name: e1009-parameterisation
description: "Use when define the parameterisation of a coordinate system per ECSS-E-ST-10-09C §5.4.7: categorize the geometry as Cartesian, spherical, or cylindrical; confirm the origin and orientation convention are documented; verify Cartesian axes form a right-hand triad; and check that spherical or cylindrical coordinate parameters fall within their valid ranges. Trigger: ecss, e-st-10-system-scope, coordinate-systems, parameterisation, spherical-coordinates, cylindrical-coordinates, cartesian-coordinates, orientation-convention."
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
  tags: [ecss, e-st-10-system-scope, coordinate-systems, parameterisation, spherical-coordinates, cylindrical-coordinates, cartesian-coordinates, orientation-convention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Reference Frames — Coordinate System Parameterisation (space-systems/ecss/e1009-parameterisation)

Use when the task is defining and verifying the parameterisation of a
coordinate system under ECSS-E-ST-10-09C §5.4.7 — confirming the
geometry family, origin, axis orientation, and coordinate parameter
ranges are all consistently and completely defined.

## Domain quick reference

- §5.4.7 requires that every coordinate system used in a space-system
  analysis be parameterised by stating: (1) the geometry (Cartesian,
  spherical, or cylindrical), (2) the origin expressed in a parent
  frame, (3) the orientation convention (e.g. ECI, LVLH, body-fixed),
  and (4) the parameter ranges that distinguish valid coordinate values
  from invalid ones.
- Cartesian systems use three mutually orthogonal axes (x, y, z) that
  must form a right-hand triad: the cross product of the x-axis unit
  vector with the y-axis unit vector must align with the z-axis unit
  vector. Left-hand triads are not permitted unless explicitly
  documented as an exception.
- Spherical systems use radial distance r (≥ 0), polar angle θ
  (colatitude, in [0, π] radians), and azimuth φ (in [0, 2π) radians).
  The sign convention for θ and φ must match the orientation convention
  on record; a system with any parameter outside these bounds is
  ill-parameterised and must not be used until corrected.
- Cylindrical systems use radial distance ρ (≥ 0), azimuth φ (in
  [0, 2π) radians), and axial coordinate z (unconstrained). As with
  spherical, the sign convention for φ must agree with the documented
  orientation convention.
- Every coordinate system must carry a documented orientation
  convention string; its absence is a finding under §5.4.7 regardless
  of whether the numeric parameters are otherwise valid.

## Workflow

1. Identify the geometry family for each coordinate system under
   review. Accept "cartesian", "spherical", or "cylindrical"; reject
   any geometry string outside this set before proceeding.
2. Verify the origin is fully specified: all three Cartesian components
   of the origin (expressed in the parent frame) must be present and
   finite. Flag any missing or non-finite component as an origin
   violation.
3. For Cartesian systems, verify the axis triad: x_axis, y_axis, and
   z_axis unit vectors must be present and must satisfy the right-hand
   rule (x_axis × y_axis ≈ z_axis within a small numerical tolerance).
   Flag non-right-hand triads as an axis-handedness violation.
4. For spherical or cylindrical systems, validate that any coordinate
   sample supplied falls within its valid range (r ≥ 0, θ ∈ [0, π],
   φ ∈ [0, 2π) for spherical; ρ ≥ 0, φ ∈ [0, 2π) for cylindrical).
   Raise on non-numeric inputs; return a violation list for out-of-range
   values.
5. Verify the orientation convention is documented: a missing or empty
   convention string is flagged as a convention violation under §5.4.7.
6. Aggregate origin, axes, and convention findings per coordinate
   system; a system is fully parameterised only when all three violation
   lists are empty.

## Pitfalls

- Accepting a left-hand axis triad without a documented exception —
  §5.4.7 requires right-hand convention by default; a left-hand system
  must be explicitly justified and flagged, not silently accepted.
- Treating a missing orientation convention as a minor documentation
  gap — without a stated convention, coordinate values are ambiguous
  and cannot be correctly interpreted by downstream analysis tools.
- Applying Cartesian axis checks to spherical or cylindrical systems
  (or vice versa) — the validation logic is geometry-specific;
  cross-applying it will either miss real errors or generate spurious
  ones.
- Ignoring the boundary conditions of spherical ranges: θ = 0 (north
  pole) and θ = π (south pole) are valid; θ slightly above π is not.
  Floating-point rounding near boundaries requires a deliberate
  tolerance policy to avoid false violations.
- Conflating "no sample coordinates provided" with "ranges validated" —
  range validation applies only when coordinate samples are present;
  the absence of a sample does not constitute a passing range check.

## Behavior contract (gate 3)

The geometry categorization, origin validation, axis-handedness check,
spherical/cylindrical range validation, orientation-convention check,
and aggregate review logic are exercised by the gate 3 contract test:
scripts/test_e1009_parameterisation.py against
scripts/e1009_parameterisation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e1009_parameterisation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
