---
name: e1004-ref-gravity
description: "Use when defining Earth and third-body gravitational reference constants (GM, J2 oblateness coefficient) per ECSS-E-ST-10-04C Annex A for a space mission: compute point-mass, J2 zonal-harmonic, and third-body tidal perturbation accelerations at a given orbit radius, and determine which gravity-model terms the mission's environment specification must carry for the orbit regime and mission duration. Trigger: gravity constants, GM, J2 oblateness, zonal harmonic, third-body tidal acceleration, gravity environment specification, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, gravity, gm, j2, zonal-harmonic, third-body, tidal, annex-a]
  version: 0.1.0
  author: Aero Agent Skills
---

# E1004 Annex A Gravity Environment Reference Data

## Overview

ECSS-E-ST-10-04C Annex A provides the gravity-environment reference
constants and tables (gravitational parameters, Earth oblateness
coefficients) that every orbit-dependent environment or dynamics
analysis draws on: orbit lifetime, station-keeping budgets, attitude
disturbance-torque, and the trapped-radiation/meteoroid geometry used
by sibling leaves all assume a consistent gravity model as their
starting point. This is a reference-data leaf: it does not size a
mission, it categorizes and supplies the constants and the checks
needed to decide which gravity terms a given orbit case must model.

The environment has three parts that must be categorized and combined
separately:

1. **Point-mass (two-body) gravity** — the dominant `GM/r^2`
   attraction of the central body, using its gravitational parameter
   (`GM`, km^3/s^2).
2. **Earth oblateness (J2 zonal harmonic)** — the correction from
   Earth's equatorial bulge, which is latitude-dependent and falls off
   faster with radius than the point-mass term, so it matters most for
   low orbits and drops toward negligible at high altitude.
3. **Third-body tidal perturbation** — the differential pull of the
   Moon and Sun across the orbit, which grows with orbit radius (it is
   negligible in LEO and becomes significant approaching GEO and
   beyond).

This leaf computes:
1. The point-mass gravitational acceleration for a body's `GM` at a
   given radius, plus the derived circular-orbit and escape velocities.
2. The J2 zonal-harmonic perturbation acceleration at a given radius
   and geocentric latitude.
3. The third-body tidal perturbation acceleration for the Moon or Sun
   at a given orbit radius and body distance.
4. Which of the J2 and third-body terms are significant enough
   (relative to the point-mass term) that an orbit case's gravity model
   must include them, and whether a case's modeled term set is
   compliant with that requirement.

## When to invoke this skill

- Populating the gravity-constant and gravity-model-term inputs to an
  orbit lifetime, station-keeping, or perturbation-budget analysis.
- Deciding whether a mission's orbit propagator configuration (which
  zonal harmonics, which third bodies) is adequate for its orbit
  regime, rather than carrying every term everywhere by default.
- Cross-checking a vendor-supplied gravity-model configuration (e.g.
  from STK, GMAT, or an in-house propagator) against an independent
  order-of-magnitude estimate of which terms actually matter.

Not for higher-order geopotential tesseral/sectoral terms beyond J2,
full trapped-radiation or meteoroid environments (`e1004-trapped-leo`,
`e1004-annex-c-flux`, and siblings), or atmospheric drag — those are
separate leaves in this family.

## Data provenance and fidelity notice

The gravitational parameters (`GM_SUN_KM3_S2`, `GM_EARTH_KM3_S2`,
`GM_MOON_KM3_S2`), Earth equatorial radius, and the J2 coefficient
embedded in `scripts/e1004_ref_gravity_logic.py` are **widely published
astrodynamics reference constants** (the same order used by WGS84/
EGM96-class Earth gravity models), not a transcription of the
standard's Annex A tables. The J2 perturbation-acceleration formula is
the standard two-term (radial/meridional) zonal-harmonic approximation
found in general astrodynamics references (e.g. Vallado); the
third-body term uses the standard near-field tidal-acceleration
approximation (`2 * GM_third * r / d^3`, valid for orbit radius `r`
much smaller than the third-body distance `d`). For mission-grade,
traceable analysis, replace the constants with the specific gravity
model (e.g. EGM2008, DE440 planetary ephemeris) called out by the
project's applicable-documents list, keeping the same function
interface (`point_mass_gravity_accel_km_s2`,
`j2_perturbation_acceleration_km_s2`, `tidal_acceleration_km_s2`). The
significance-threshold and compliance logic are model-independent and
do not need to change when the constants are swapped.

## Steps

1. **Get the reference constant.** `gm_for_body(body_name)` looks up
   the gravitational parameter (km^3/s^2) for `"sun"`, `"earth"`, or
   `"moon"`; raises `ValueError` for any other name.
2. **Compute the point-mass term.** `point_mass_gravity_accel_km_s2(gm_km3_s2,
   radius_km)` returns `GM/r^2`. `circular_orbit_velocity_km_s()` and
   `escape_velocity_km_s()` derive the companion reference velocities
   for the same `GM`/radius pair.
3. **Compute the J2 term.** `j2_perturbation_acceleration_km_s2(radius_km,
   geocentric_latitude_deg)` returns the Earth oblateness perturbation
   acceleration magnitude at that radius and latitude; rejects a radius
   below the Earth's surface or a latitude outside `[-90, 90]`.
4. **Compute the third-body term.** `tidal_acceleration_km_s2(gm_third_km3_s2,
   orbit_radius_km, distance_to_third_km)` returns the Moon's or Sun's
   tidal perturbation acceleration for the case's orbit radius and
   current body distance; rejects a third body no farther away than the
   orbit radius itself.
5. **Decide which terms are required.** `significant_gravity_terms(radius_km,
   geocentric_latitude_deg, distance_to_moon_km, distance_to_sun_km,
   threshold_fraction=1e-6)` computes the point-mass term and all three
   perturbation terms together, and flags each perturbation term
   `required` when its acceleration is at least `threshold_fraction` of
   the point-mass term.
6. **Check compliance.** `missing_gravity_model_terms(term_assessment,
   modeled_terms)` returns the required term names absent from a case's
   modeled term set (empty list when compliant);
   `is_gravity_model_compliant(missing_terms)` reduces that to a single
   boolean. Do not close the gravity-environment input while any orbit
   case has non-empty missing terms.

## Script reference

- `scripts/e1004_ref_gravity_logic.py` — gravitational-parameter table,
  point-mass/J2/tidal acceleration formulas, and the significance and
  compliance checks.
- `scripts/test_e1004_ref_gravity.py` — unit tests for the constant
  lookup, acceleration formulas' bounds and monotonicity, and the
  significance/compliance logic.
