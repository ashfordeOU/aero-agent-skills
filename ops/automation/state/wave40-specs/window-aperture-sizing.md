# Wave-40 leaf spec: window-aperture-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/window-aperture-sizing/
- Pack: sizing. Closest siblings: fuselage-sizing (its quick reference
  covers cabin length from seat pitch, cabin width and fuselage diameter
  from seats abreast, the length-to-diameter sanity band and the
  passenger-baggage volume check; ZERO window, pane, aperture or
  pressure-differential stress content anywhere in the leaf), 
  structures-integration/fuselage-skin-stringer (sizes the barrel skin from
  the pressure membrane state "hoop stress sigma_h = p * r / t and
  longitudinal stress sigma_l = p * r / (2 * t)" and the stringer/frame
  grid; it does not size window panes or treat apertures),
  structures/fem/pressure-bulkhead (closes a pressurized barrel with a
  dome: membrane theory with "cabin differential pressure p (Pa), barrel
  radius a (m), dome thickness t (m)"; no aperture content),
  cabin-outflow-valve-sizing (passes the ECS inflow through a choked
  valve at "75262 Pa for the 8000 ft cabin at 39,000 ft"; it owns the
  outflow/relief discharge step, not cabin structure), bird-strike
  (impact energy and windshield/leading-edge damage per its description,
  "FAR 25.631 context"). Whole-tree greps at prep: "window pane",
  "window-pane", "pane thickness" = 0 hits in skills/; no leaf sizes the
  pressurized-cabin window pane or its aperture. GENUINE VEHICLE gap
  (fresh probe).
- Standards id: far-25 (reference-only; sizing pack convention). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size a pressurized-cabin passenger window aperture as a flat circular pane
clamped at its edge under a uniform pressure differential: compute the
design differential from the ISA pressures at the cabin and flight
altitudes with the certification pressure factor applied, compute the
clamped-edge plate bending stress with the documented closed-form constant
sigma_max = (3/4) * p * (r/t)^2 (Roark flat-circular-plate case,
edge clamped, uniform load; the maximum stress sits at the clamped edge and
the constant is independent of Poisson ratio, verified numerically at
prep), invert the relation for the required pane thickness, compute the
margin against a designer-supplied allowable stress, and roll up the pane
mass for a window count. Produces the design differential, the pane stress,
the required thickness, the margin and the weight that gate the window
aperture layout. Does NOT do: sizing of the fuselage framing around the
window and the skin cutout reinforcement (the window-frame structural
interaction context of the certification rules is out of scope; the
surrounding barrel belongs to fuselage-skin-stringer); impact loading of
the window (bird-strike); dome and bulkhead pressure structure
(pressure-bulkhead); outflow valve and relief sizing
(cabin-outflow-valve-sizing); pressurization scheduling
(environmental-control-sizing).

## Model (implement exactly)

ISA atmosphere (the standard pressure formula owned at
cross-cutting/units-atmos/isa-atmosphere; implemented here with module
constants for the pressure ratio): troposphere (0-11 km)
P(h) = P0 * (1 - L*h/T0)^e with e = g0/(R*L), isothermal stratosphere
(11-20 km) P(h) = P_tropo * exp(-g0*(h - 11 km)/(R*T_tropo)); altitude
range 0-20000 m.

Plate result (Roark's Formulas for Stress and Strain, flat circular plate
case, clamped edge, uniform pressure; paraphrased, constant deterministic):
for the exact clamped-plate deflection w = p*(a^2 - r^2)^2/(64*D) the edge
radial moment is p*a^2/8, giving sigma_max = 6*(p*a^2/8)/t^2 =
(3/4)*p*(a/t)^2 at the clamped edge, independent of Poisson ratio; the
center stress 3*(1+nu)*p*(a/t)^2/8 is lower for nu = 0.33 (0.49875 vs
0.75), so the clamped edge governs. The spec constant was checked
numerically at prep on the normalized solution (finite-difference residual
of the axisymmetric plate equation below 2e-5 on a 600-node grid, edge
second derivative 7.960039 against the closed form 8 a^2 = 8.000000).

Functions (pure stdlib):
- isa_pressure_pa(altitude_m) -> float: the pressure ratio formula above;
  ValueError outside 0-20000 m.
- design_pressure_differential(cabin_altitude_m, flight_altitude_m,
  certification_factor=CERT_PRESSURE_FACTOR) -> dict with keys
  cabin_pressure_pa, ambient_pressure_pa, limit_differential_pa,
  design_differential_pa (limit * certification_factor). ValueError if the
  flight altitude does not exceed the cabin altitude.
- plate_max_stress_clamped_circular(pressure_pa, radius_m, thickness_m)
  -> float (3/4)*p*(r/t)^2 in Pa; ValueError on non-positive arguments.
- pane_thickness(pressure_pa, radius_m, allowable_stress_pa) -> float
  r * sqrt((3/4)*p/sigma_allow); ValueError on non-positive arguments.
- pane_margin(pressure_pa, radius_m, thickness_m, allowable_stress_pa)
  -> float allowable / computed_stress - 1 (negative margin means the pane
  fails); ValueError on non-positive thickness or allowable.
- window_weight(radius_m, thickness_m, material_density_kg_m3, n_windows)
  -> dict with keys per_window_kg and total_kg: n * rho * pi * r^2 * t
  (weight is a function of the pane volume, not of the load, so no pressure
  argument); ValueError if any argument non-positive or n_windows < 1.
Module constants: P0_PA = 101325.0, T0_K = 288.15,
LAPSE_K_PER_M = 0.0065, TROPOPAUSE_M = 11000.0, TROPOPAUSE_TEMP_K = 216.65,
G0_M_S2 = 9.80665, R_GAS = 287.05, TROPOSPHERIC_EXPONENT = 5.25588
(g0/(R*L) evaluated), CLAMPED_PLATE_STRESS_COEF = 0.75,
CERT_PRESSURE_FACTOR = 1.33 (certification pressure factor: the ultimate
check applies 1.33 times the normal operating differential pressure, a
paraphrase of the FAR 25.365 cabin pressure rule; verify the SKILL body
wording stays a paraphrase, never a quote of the regulation).

Identities to test: plate stress scales as pressure, as radius squared and
as inverse thickness squared; pane_thickness inverts the stress formula
exactly (round trip through plate_max_stress_clamped_circular returns the
allowable); doubling the certification factor multiplies the required
thickness by sqrt(2); at nu = 0.33 the clamped-edge stress exceeds the
center stress.

## Worked example

Cabin altitude 8000 ft (2438.40 m), flight altitude 12000 m, pane radius
0.15 m, acrylic pane (material density 1190 kg/m3, an input allowable of
50 MPa chosen by the designer; the leaf hard-codes no material). Real
module outputs (anchor script run at prep):

- Cabin pressure 75262.136558 Pa (ratio 0.742780 of sea level; the repo
  outflow-valve leaf quotes 75262 Pa for the same cabin, cross-consistent);
  ambient at 12 km 19330.062329 Pa; limit differential 55932.074230 Pa;
  design differential (x 1.33) 74389.658725 Pa (about 0.744 bar).
- plate_max_stress_clamped_circular at t = 6 mm: 34.870153 MPa; margin
  against 50 MPa: 0.433891. At t = 5 mm: 50.213020 MPa, margin -0.004242.
- pane_thickness(74389.66, 0.15, 50e6) = 0.005011 m (5.010640 mm), so a
  6 mm pane is the first standard gauge with positive margin.
- Limit-pressure (no factor) stress at t = 6 mm: 26.218160 MPa, margin
  0.907075.
- window_weight(0.15, 0.006, 1190, 100): per window 0.504697 kg, 100
  windows 50.469686 kg.
- Sweep check r = 0.10 m: required thickness 3.340426 mm; at t = 10 mm the
  stress is 5.579224 MPa.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (reproduced at prep with stdlib math).
Disclosed regime note: the linear small-deflection plate stress is the
conceptual sizing standard; a very thin, highly loaded pane can leave the
small-deflection regime (deflection of the order of the thickness), where
membrane stiffening alters the load path. The leaf documents this in its
Pitfalls and keeps the linear closed form.

## Validation list (contract test must include)

- design_pressure_differential(2438.40, 12000): cabin 75262.136558,
  ambient 19330.062329, limit 55932.074230, design 74389.658725, each
  within 1 Pa.
- plate stress at t = 6 mm = 34.870153 MPa within 1e-3; margin 0.433891
  within 1e-4.
- pane_thickness = 5.010640 mm within 1e-5 m.
- Round trip: plate stress at pane_thickness(p, r, allow) equals allow
  within 1e-6 relative.
- Scaling: stress at t/2 is 4x the stress at t; doubling the pressure
  doubles the stress; pane_thickness scales as sqrt of pressure.
- window_weight: per window 0.504697 kg within 1e-4; total scales with
  n_windows.
- isa anchors: sea level 101325.0; tropopause 11000 m = 22631.700910 Pa
  within 0.5 Pa; cabin/12 km values above.
- ValueErrors: flight altitude below cabin altitude, negative altitude,
  altitude above 20000 m, non-positive pressure/radius/thickness/
  allowable/density, n_windows 0.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave40-window-aperture-sizing.yaml)

Query 1 (copy verbatim):
  "compute the window-aperture-sizing pane thickness for the pressurized cabin window from the pressure-differential-stress at the certified cabin pressure differential"
  intent: "vehicle-design; circular window pane thickness from clamped plate pressure stress"
  expected_skill: "vehicle-design/sizing/window-aperture-sizing"
Query 2 (copy verbatim):
  "check the window-pane-thickness margin and pane weight for the circular passenger window against the design pressure differential and the material allowable"
  intent: "vehicle-design; window pane margin and mass rollup"
  expected_skill: "vehicle-design/sizing/window-aperture-sizing"
Task ids: w40-window-aperture-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size a pressurized-cabin passenger
window aperture as a flat circular pane:" and include the outputs in the
Claim. First tag: window-aperture-sizing. Additional tags ONLY:
window-pane-thickness, pressure-differential-stress,
clamped-circular-plate, pane-margin-check, cabin-pressure-load.
NEVER single generic words (window, pane, pressure, cabin, glass, acrylic,
stress, thickness, aperture). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): hoop-stress, stringer-spacing,
frame-pitch, effective-skin-width (fuselage-skin-stringer); ellipsoidal-
dome, junction-ring, membrane-theory (pressure-bulkhead); choked-flow,
relief-valve, effective-area (cabin-outflow-valve-sizing); impact-energy,
soft-body, leading-edge (bird-strike); seats-abreast, seat-pitch,
baggage-volume (fuselage-sizing).
