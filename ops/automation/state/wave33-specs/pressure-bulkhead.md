# Wave-33 leaf spec: pressure-bulkhead (structures, fem pack)

- Path: skills/structures/fem/pressure-bulkhead/
- Pack: fem (closed-form analysis methods precedent:
  cylindrical-shell-buckling). Alternate name considered:
  shell-membrane-stresses. Sibling scope check: vehicle-design/
  structures-integration/fuselage-skin-stringer owns the BARREL only
  (hoop and longitudinal membrane stresses, skin thickness, stringer
  spacing); grep shows zero bulkhead/dome/meridional/ellipsoid content
  in vehicle-design; space-systems propellant-tank-sizing owns the
  standalone-spacecraft sphere from burst pressure (no ellipsoid/ring/
  junction).
- Standards id: far-25 (reference-only) + cs-25 (reference-only).
  Ledger Standard: far-25.
- Family: structures

## Claim

Size a fuselage pressure-bulkhead dome closing a pressurized cylindrical
barrel with membrane theory: compute the apex and equator meridional and
hoop stresses for a spherical cap, a hemisphere, and a 2:1 ellipsoid,
the dome margin under the FAR 25.303 1.5 factor of safety, the dome-cap
rise, and the unbalanced meridional-resultant junction-ring load at the
dome-barrel interface with the ring area required. Produces the dome
stresses, the margin, and the junction-ring area that gate the
bulkhead design.

Does NOT do: barrel skin/stringer/frame sizing (vehicle-design owns the
cylinder); standalone spacecraft tank walls (space-systems); stiffened
plate or curved-shell buckling (plate-buckling / cylindrical-shell-
buckling); thermal stress; composite layups.

## Model (implement exactly)

Conventions: cabin differential pressure p (Pa), barrel radius a (m),
dome thickness t (m). Cylinder membrane: hoop sigma_theta = p a / t,
longitudinal sigma_long = p a / (2 t). Spherical dome radius R_sph:
sigma = p R_sph / (2 t) everywhere. Ellipsoid semi-axes a (barrel
radius) and b (dome depth): apex (both meridional and hoop equal)
sigma = p a^2 / (2 b t); equator meridional sigma_phi = p a / (2 t);
equator hoop sigma_theta = (p a / t) (1 - a^2 / (2 b^2)). For b = a
(sphere) these reduce to p a / (2 t) everywhere; for a 2:1 ellipsoid
b = a/2 the equator hoop becomes compressive: (p a / t)(1 - 2) = -p a/t
(known 2:1 knuckle compression). Dome-cap rise for a spherical cap
cutting the barrel at radius a: h = R_sph - sqrt(R_sph^2 - a^2).
Junction ring: the spherical cap's meridional resultant has a radial
component at the barrel interface; unbalanced radial line load
q = (p R_sph / 2) (R_sph - h) / R_sph [N/m]; ring tension
F_ring = q a; ring area A_ring = F_ring * FS / sigma_allow (with FS the
1.5 factor against the material ultimate). Hemisphere (h = R_sph = a)
has zero unbalanced ring load.

Functions (pure stdlib):

- cylinder_membrane_stresses(p, radius_m, thickness_m) ->
  (sigma_hoop, sigma_longitudinal) = (p r / t, p r / (2 t)).
  ValueErrors on non-positive inputs.
- spherical_dome_stress(p, radius_sphere_m, thickness_m) -> p R / (2t).
- ellipsoid_dome_stresses(p, semi_axis_a_m, semi_axis_b_m,
  thickness_m) -> dict {sigma_apex, sigma_equator_meridional,
  sigma_equator_hoop} with the formulas above. ValueErrors on
  non-positive inputs.
- dome_cap_rise(radius_sphere_m, barrel_radius_m) -> h. ValueError if
  barrel radius > sphere radius.
- junction_ring_load(p, barrel_radius_m, radius_sphere_m, rise_m) ->
  q [N/m] radial line load at the interface; ring_tension =
  q * barrel_radius; dict {q_n_per_m, ring_tension_N}. Return the dict.
- junction_ring_area(ring_tension_N, sigma_ultimate_pa, fs) ->
  A_ring_m2 = ring_tension * fs / sigma_ultimate. ValueErrors on
  non-positive inputs.
- bulkhead_summary(p, barrel_radius_m, thickness_m, dome_type,
  sigma_ultimate_pa, fs, sphere_or_axes) -> dict with the geometry
  (dome type, radius/depth), the stresses, the margin
  (MS = sigma_ultimate/fs / sigma_max - 1 or reserve factor
  sigma_ultimate/(fs sigma_max)), the ring load, and the ring area.

## Worked example

Narrowbody barrel: a = 1.88 m, cabin differential pressure DeltaP =
0.0593 MPa, aluminum 7075 dome t = 2 mm, Ftu = 469 MPa, FS = 1.5.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- Barrel hoop: p a / t = 55.7 MPa (matches the vehicle-design leaf
  formula cross-check).
- Spherical cap R = 3.76 m (2a): sigma = p R / (2 t) about 55.7 MPa;
  margin MS = Ftu/1.5 / sigma - 1 = 313/55.7 - 1 about 4.61.
- 2:1 ellipsoid (b = a/2 = 0.94 m): apex about +55.7 MPa; equator
  meridional about +27.9 MPa; equator hoop about -55.7 MPa (the known
  knuckle compression).
- Hemisphere (R = a): about 27.9 MPa everywhere; ring load zero.
- Spherical cap rise: h = 3.76 - sqrt(3.76^2 - 1.88^2) about 0.504 m.
- Junction ring: q about 96.5 kN/m, ring tension about 181.5 kN, ring
  area = 181.5e3 * 1.5 / 469e6 about 581 mm^2.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive p/radius/thickness/ultimate/fs; barrel
  radius > sphere radius.
- Cylinder identity: hoop = 2 * longitudinal.
- Sphere limit: ellipsoid with b = a returns p a/(2t) at apex AND
  equator (both directions).
- Hemisphere ring load = 0 exactly (q -> 0 when rise = sphere radius).
- 2:1 ellipsoid equator hoop is negative (compressive).
- Worked magnitudes: 55.7 MPa barrel/spherical; apex/equator values
  above; ring area about 581 mm^2.
- Determinism: identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-pressure-bulkhead.yaml)

Query 1 (copy verbatim):
  "size the ellipsoidal aft pressure bulkhead dome of the pressurized fuselage with membrane theory computing apex and equator meridional and hoop stresses and the junction ring load"
  intent: "structures; fuselage pressure-bulkhead dome membrane stresses and junction ring load"
  expected_skill: "structures/fem/pressure-bulkhead"
Query 2 (copy verbatim):
  "check the spherical cap bulkhead dome margin under the cabin differential pressure with the 1.5 factor of safety and size the dome to barrel junction ring area"
  intent: "structures; spherical-cap bulkhead margin and dome-barrel junction ring sizing"
  expected_skill: "structures/fem/pressure-bulkhead"
Task ids: w33-pressure-bulkhead-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size a fuselage pressure-
bulkhead dome:" and include the outputs in the Claim. First tag:
pressure-bulkhead. Additional tags ONLY: membrane-theory-dome,
bulkhead-dome-stress, ellipsoidal-bulkhead, junction-ring-load,
dome-margin, pressure-dome-sizing. NEVER single generic words (dome,
bulkhead, pressure, stress, ring, fuselage, membrane). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): hoop stress, longitudinal
stress, skin thickness, stringer spacing, frame pitch (vehicle-design
fuselage-skin-stringer barrel); burst pressure, tank wall (space
propellant-tank); buckling, knockdown (cylindrical-shell-buckling /
plate-buckling). The tokens "bulkhead", "dome", "meridional",
"junction ring", "ellipsoid" are this leaf's own.

Tags: [pressure-bulkhead, membrane-theory-dome, bulkhead-dome-stress,
ellipsoidal-bulkhead, junction-ring-load, dome-margin,
pressure-dome-sizing]

Sibling-citation lines for Related leaves:
vehicle-design/structures-integration/fuselage-skin-stringer (barrel
sizing; this leaf closes the dome),
structures/fem/cylindrical-shell-buckling (buckling check of the same
barrel),
structures/fem/plate-buckling.

Ledger Standard: far-25.
