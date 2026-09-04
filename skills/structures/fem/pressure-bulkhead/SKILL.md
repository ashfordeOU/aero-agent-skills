---
name: pressure-bulkhead
description: "Use when you must size a fuselage pressure-bulkhead dome: compute the membrane stresses of a spherical cap, a hemisphere, or a 2:1 ellipsoid closing a pressurized cylindrical barrel with membrane theory, including the apex and equator meridional and circumferential stresses of an ellipsoidal dome, the dome margin against ultimate strength under the FAR 25.303 1.5 factor of safety, the spherical-cap rise, and the unbalanced meridional-resultant junction ring load at the dome-barrel interface with the ring area required. Produces the dome stresses, the margin, and the junction ring area that gate the bulkhead design. Trigger: pressure bulkhead, ellipsoidal bulkhead, spherical cap dome, dome margin, junction ring, dome to barrel ring, pressurized fuselage dome, 2:1 ellipsoid."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [pressure-bulkhead, membrane-theory-dome, bulkhead-dome-stress, ellipsoidal-bulkhead, junction-ring-load, dome-margin, pressure-dome-sizing]
  version: 0.1.0
  author: AeroSkills
---

# Pressure Bulkhead Dome (structures/fem/pressure-bulkhead)

Use when the task is the membrane-theory sizing of the fuselage
pressure-bulkhead dome that closes a pressurized cylindrical barrel.
This leaf implements the closed-form dome stress field for the three
standard bulkhead geometries, a spherical cap, a hemisphere, and a
2:1 ellipsoid, the apex and equator meridional and circumferential
membrane stresses of an ellipsoidal dome (including the known 2:1
knuckle compression), the dome margin against ultimate under the FAR
25.303 factor of safety of 1.5, the spherical-cap rise where the cap
cuts the barrel, and the unbalanced meridional-resultant junction
ring load at the dome-barrel interface with the ring area required.
It is pure Python, stdlib only, deterministic and offline. It pairs
with vehicle-design/structures-integration/fuselage-skin-stringer,
which sizes the barrel skin and stringers that this dome closes, and
with structures/fem/cylindrical-shell-buckling for the stability
check of the same barrel. Standalone spacecraft tank walls sized from
burst pressure are covered by the space-systems tank leaf, not here.

## Domain quick reference

Conventions: cabin differential pressure p (Pa), barrel radius a (m),
dome thickness t (m). SI throughout: Pa, m, N/m, N, m^2.

- Barrel membrane cross-check (barrel sizing itself belongs to
  vehicle-design): circumferential sigma_theta = p*a/t and
  longitudinal sigma_long = p*a/(2*t).
- Spherical dome radius R: sigma = p*R/(2*t) everywhere, equal
  meridional and circumferential membrane resultants.
- Ellipsoid, semi-axes a (barrel radius) and b (dome depth):
  - Apex, both directions equal: sigma = p*a^2/(2*b*t).
  - Equator meridional: sigma_phi = p*a/(2*t).
  - Equator circumferential: sigma_theta = (p*a/t)*(1 - a^2/(2*b^2)).
  For b = a the three collapse to p*a/(2*t), the sphere limit. For
  the 2:1 dome (b = a/2) the equator circumferential stress is
  (p*a/t)*(1 - 2) = -p*a/t, compressive: the known 2:1 knuckle
  compression that drives the knuckle check.
- Dome-cap rise of a spherical cap cutting the barrel at radius a:
  h = R - sqrt(R^2 - a^2); h = a for the hemisphere.
- Junction ring: the spherical cap meridional resultant p*R/2 acts at
  the dome-barrel interface with the radial component (R - h)/R, so
  the unbalanced radial line load is q = (p*R/2)*(R - h)/R [N/m] and
  the ring tension is F_ring = q*a [N]. The ring area against the
  material ultimate at the factor of safety is A_ring =
  F_ring*FS/sigma_ultimate. The hemisphere (h = R = a) carries zero
  unbalanced ring load and needs no ring.
- Margin: allowable = sigma_ultimate/FS; margin_of_safety =
  allowable/sigma_max - 1 and reserve_factor = allowable/sigma_max,
  where sigma_max is the largest absolute dome membrane stress.

## Workflow

1. Fix the load case and geometry: cabin differential pressure p, the
   barrel radius a the dome must close, and the dome thickness t.
2. Cross-check the barrel membrane level with
   cylinder_membrane_stresses, which returns (sigma_hoop,
   sigma_longitudinal) = (p*a/t, p*a/(2*t)); the dome cannot be
   lighter than the pressure loads feeding the barrel.
3. Choose the dome type. Spherical cap: set the sphere radius R and
   read the uniform stress p*R/(2*t) from spherical_dome_stress.
   Hemisphere: R = a by geometry, same function. Ellipsoid: pass the
   semi-axes to ellipsoid_dome_stresses for the apex and equator
   meridional and circumferential stresses.
4. Get the cap geometry with dome_cap_rise(R, a) when the cap cuts
   the barrel below its equator; the rise h places the junction and
   sets the ring load.
5. Size the junction ring with junction_ring_load(p, a, R, h) for the
   radial line load and ring tension, then junction_ring_area for the
   cross-section area at the chosen ultimate and factor of safety.
6. Run bulkhead_summary for the consolidated dict (geometry, all
   stresses, sigma_max, allowable, margin_of_safety, reserve_factor,
   and the ring q, tension and area) and confirm it against the
   individual function results.
7. Confirm the deterministic checks with the contract test
   scripts/test_pressure_bulkhead.py.

## Worked example

Narrowbody barrel: a = 1.88 m, DeltaP = 0.0593 MPa, 7075 dome
t = 2 mm, Ftu = 469 MPa, FS = 1.5. Real module outputs:

- cylinder_membrane_stresses: barrel hoop 55.742 MPa, longitudinal
  27.871 MPa (magnitudes 55.7 and 27.9 MPa).
- Spherical cap R = 3.76 m (2*a): 55.742 MPa everywhere;
  bulkhead_summary margin_of_safety 4.609 (about 4.61) and
  reserve_factor 5.609 against 469/1.5 = 312.7 MPa allowable.
- 2:1 ellipsoid b = 0.94 m: apex +55.742 MPa, equator meridional
  +27.871 MPa, equator circumferential -55.742 MPa (compression).
- Hemisphere R = 1.88 m: 27.871 MPa everywhere, junction q = 0,
  ring tension 0, ring area 0 exactly.
- Cap rise dome_cap_rise(3.76, 1.88) = 0.503744 m (about 0.504 m).
- Junction ring for the cap: q = 96.548 kN/m (about 96.5 kN/m),
  ring tension 181.510 kN (about 181.5 kN), ring area 5.805e-4 m^2
  = 580.5 mm^2 (about 581 mm^2) at 1.5 x 469 MPa.

The ellipsoidal dome matches the spherical-cap peak stress at the
apex but trades the junction ring for a compressive knuckle band at
the equator, which is why the margin and the knuckle check, not the
ring, tend to gate the 2:1 design.

## Verification

- Confirm the worked magnitudes: barrel hoop and spherical cap
  55.742 MPa (55.7 MPa), ellipsoid apex 55.742 MPa, equator
  meridional 27.871 MPa, equator circumferential -55.742 MPa,
  hemisphere 27.871 MPa, cap rise 0.503744 m, q 96.548 kN/m, ring
  tension 181.510 kN, ring area 580.5 mm^2, margin about 4.61.
- Confirm the identities: barrel hoop is exactly twice the
  longitudinal stress; a spherical cap with R = 2*a reproduces the
  barrel hoop stress exactly; the ellipsoid with b = a returns
  p*a/(2*t) at the apex and equator in both directions (sphere
  limit); the hemisphere junction ring load and tension are exactly
  zero; the cap rise obeys h = R - sqrt(R^2 - a^2).
- Confirm the 2:1 equator circumferential stress is negative
  (compressive) for b < a/sqrt(2).
- Confirm every non-positive pressure, radius, thickness, ultimate or
  factor of safety raises ValueError, as does a barrel radius larger
  than the sphere radius and an unknown dome type.
- Confirm dict key contracts: ellipsoid_dome_stresses returns exactly
  sigma_apex, sigma_equator_meridional and sigma_equator_hoop;
  junction_ring_load returns exactly q_n_per_m and ring_tension_N;
  bulkhead_summary returns the documented ten keys.
- Deterministic: no RNG, identical float results run to run.
- Run the contract test offline: python3
  scripts/test_pressure_bulkhead.py (32 tests).

## Related leaves

- vehicle-design/structures-integration/fuselage-skin-stringer: the
  barrel skin and stringer sizing this dome closes.
- structures/fem/cylindrical-shell-buckling: buckling check of the
  same barrel wall.
- structures/fem/plate-buckling: flat panel stability, the
  alternative stability check for the dome knuckle region when it is
  treated as a curved panel.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_pressure_bulkhead.py

The 32 tests cover the worked example within the spec magnitude
bounds (55.7 MPa barrel and spherical cap, 27.9 MPa hemisphere, 2:1
apex +55.7 and equator -55.7 MPa compressive, rise 0.504 m, q 96.5
kN/m, ring tension 181.5 kN, ring area 581 mm^2, spherical-cap margin
4.61), the cylinder hoop-to-longitudinal identity, the sphere limit
of the ellipsoid, the hemisphere zero-ring case, the cap-rise
closed-form identity, dict key contracts, ValueError rejection of
non-positive inputs and of barrel radius above sphere radius, the
ellipsoid axes tuple contract, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: FAR 25.303 (factor of safety
  of 1.5 on the limit loads) and CS-25 provide the airworthiness
  context; the membrane and junction-ring relations above are
  standard engineering methodology, summary-only per
  standards-map.yaml. No regulatory text is reproduced.
- compliance: STANDARDS-REF, gated: false.
