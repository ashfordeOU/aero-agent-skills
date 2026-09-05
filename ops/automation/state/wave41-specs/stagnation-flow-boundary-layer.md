# Wave-41 leaf spec: stagnation-flow-boundary-layer (aerodynamics, boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/stagnation-flow-boundary-layer/
- Pack: boundary-layer (verified present at prep with boundary-layer-theory,
  boundary-layer-transition, boundary-layer-separation and
  rough-wall-skin-friction). Closest siblings: boundary-layer-theory (smooth
  FLAT PLATE only; its claim is "Compute laminar and turbulent
  boundary-layer thicknesses for a smooth flat plate: estimate the 99-percent
  thickness, displacement thickness, and momentum thickness from the local
  Reynolds number with the Blasius and 1/7 power-law correlations"; no
  pressure-gradient, stagnation-point or curved-surface input exists in its
  functions), boundary-layer-transition (natural transition only on a clean
  two-dimensional surface via the Thwaites integral and Michel criterion),
  boundary-layer-separation (Thwaites-lambda and Stratford separation
  criteria), rough-wall-skin-friction (turbulent flat plate with sand
  roughness), flat-plate-skin-friction-heating (high-speed pack; smooth-wall
  friction feeding non-stagnation heating: its claim is "estimate the surface
  skin friction heating on a flat plate or vehicle skin at high Mach" and its
  body states it "Produces the non-stagnation heating report",
  aerodynamic-heating (high-speed pack; the hypersonic stagnation-flux owner:
  its claim is "stagnation-point convective heat flux from the Sutton-Graves
  correlation using freestream density, flight velocity and nose radius" at
  flight conditions where the stagnation point sits behind a bow shock),
  ice-protection-sizing (vehicle-design pack; reachable leading-edge fence:
  its claim includes "compute the protected area from the icing-critical
  geometry, estimate the droplet catch efficiency from MVD and airspeed,
  compute the evaporative heat flux", an icing-catch and thermal-power model
  at the leading edge with no momentum boundary layer). Whole-tree greps at
  prep: "hiemenz", "homann", "stagnation-flow", "stagnation.*boundary" and
  "stagnation-point boundary layer" = 0 hits in skills/ at HEAD 8eaf728e.
  GENUINE AERO gap (fresh probe): no leaf sizes the low-speed laminar
  boundary layer, wall shear or skin friction at a 2-D or axisymmetric
  stagnation point or leading edge (spinner, radome, wing or fin leading
  edge); every stagnation-point skill in the tree is either hypersonic
  heating (aerodynamic-heating), icing catch (ice-protection-sizing) or
  inviscid shock-layer stagnation pressure (normal-shock, oblique-shock).
- Standards id: naca-tr-824 (reference-only). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Size the laminar boundary layer, wall shear and skin friction at a low-speed
2-D or axisymmetric stagnation point or leading edge using the Hiemenz (2-D)
or Homann (axisymmetric) exact similarity solution of the stagnation-flow
boundary layer: compute the potential-flow stagnation velocity gradient a
from the body radius and freestream speed (2 u_inf / R on a circular cylinder
or 2-D leading edge, 1.5 u_inf / R on a sphere or axisymmetric nose), the
99-percent laminar boundary-layer thickness delta about 2.4 sqrt(nu / a),
which is constant along the attachment region because the similarity layer
does not grow in the streamwise direction, the wall shear
tau_w = mu * u_inf * sqrt(a / nu) * fpp with the classical similarity
wall-shear constants fpp = 1.2326 (Hiemenz 2-D) or 1.3119 (Homann
axisymmetric), and the skin-friction coefficient Cf = tau_w / (0.5 rho
u_inf^2); optionally treat an infinite yawed cylinder or swept leading edge
with the chordwise velocity gradient driven by the velocity component normal
to the leading edge. Produces a, delta, tau_w, Cf and the flow-type treatment
note that gate spinner, radome, and wing or fin leading-edge boundary-layer
sizing at low speed. Does NOT do: flat-plate thickness, displacement or
momentum thickness, shape factor or flat-plate skin friction
(boundary-layer-theory); natural transition location (boundary-layer-
transition); separation criteria (boundary-layer-separation); rough-wall
turbulent friction (rough-wall-skin-friction); high-speed non-stagnation
skin-friction heating with recovery factor and reference temperature
(flat-plate-skin-friction-heating); stagnation-point heat flux at hypersonic
conditions, Sutton-Graves correlation or radiation-equilibrium temperature
(aerodynamic-heating); icing catch efficiency or anti-ice power at the
leading edge (ice-protection-sizing). Deterministic closed-form core only:
the similarity ODE is not integrated, the classical wall-shear and thickness
constants are module constants, and displacement and momentum thicknesses of
the similarity layer are out of scope.

## Model (implement exactly)

Functions (pure stdlib, math only):
- stagnation_velocity_gradient(flow_type, u_inf, radius) -> float a, the
  potential-flow stagnation velocity gradient du_e / ds at the attachment
  point: 2.0 * u_inf / radius for a circular cylinder or 2-D leading edge
  (flow_type "cylinder", "2d" or "two-dimensional", from the inviscid
  surface speed u_e = 2 u_inf sin(s / R) on a cylinder) and
  1.5 * u_inf / radius for a sphere or axisymmetric nose (flow_type "sphere",
  "axisymmetric" or "axi", from u_e = 1.5 u_inf sin(s / R) on a sphere).
  ValueError if u_inf <= 0, radius <= 0 or flow_type is not one of the
  accepted strings (case-insensitive).
- boundary_layer_thickness(nu, a) -> float delta = BL_DELTA_COEF *
  sqrt(nu / a), the 99-percent laminar boundary-layer thickness of the
  stagnation layer, constant along the attachment region because the Hiemenz
  and Homann similarity solutions do not grow in the streamwise direction
  (standard similarity-layer result; no streamwise station input exists).
  BL_DELTA_COEF = 2.4 is the classical Hiemenz 99-percent thickness
  coefficient (paraphrase of the standard tabulated similarity results in
  Schlichting and White). ValueError if nu <= 0 or a <= 0.
- wall_shear_stress(rho, nu, a, u_inf, flow_type) -> float tau_w in Pa from
  the exact closed form tau_w = mu * u_inf * sqrt(a / nu) * fpp with
  mu = rho * nu computed from the inputs and fpp the regime constant FPP_2D =
  1.2326 (Hiemenz 2-D, flow_type cylinder/2d/two-dimensional) or FPP_AXISYM =
  1.3119 (Homann axisymmetric, flow_type sphere/axisymmetric/axi); the form
  is dimensionally consistent (Pa s * m/s * sqrt((1/s) / (m2/s))) and equals
  the algebraic identity rho * u_inf * sqrt(a * nu) * fpp; it is the wall
  shear at the attachment-line station where the inviscid edge velocity
  reaches u_inf (u_e = a s = u_inf), and because tau_w scales linearly with
  u_e in the similarity layer, values at other near-stagnation stations scale
  with u_e / u_inf. ValueError if rho <= 0, nu <= 0, a <= 0, u_inf <= 0 or
  flow_type is invalid.
- skin_friction_coefficient(rho, u_inf, tau_w) -> float Cf = 2.0 * tau_w /
  (rho * u_inf * u_inf), the local skin-friction coefficient based on the
  freestream dynamic pressure 0.5 rho u_inf^2. ValueError if rho <= 0,
  u_inf <= 0 or tau_w < 0.
- swept_stagnation_gradient(u_inf, radius, sweep_deg) -> float a = 2.0 *
  u_inf * cos(sweep_deg in radians) / radius, the chordwise stagnation
  velocity gradient of an infinite yawed cylinder or swept leading edge of
  radius radius at sweep angle sweep_deg. Documented approximation: the
  swept (infinite yawed) stagnation line obeys the 2-D Hiemenz solution in
  the crossflow plane, with the chordwise pressure gradient driven by the
  velocity component normal to the leading edge u_n = u_inf cos(sweep)
  (independence-principle paraphrase; standard engineering methodology), so
  the 2-D Hiemenz constants apply in that plane. sweep_deg 0 reproduces the
  unswept cylinder gradient 2 u_inf / radius. ValueError if u_inf <= 0,
  radius <= 0 or abs(sweep_deg) > 90.0.
Module constants: FPP_2D = 1.2326, FPP_AXISYM = 1.3119 (classical Hiemenz
and Homann similarity wall-shear constants, standard tabulated values),
BL_DELTA_COEF = 2.4.
Regime note carried in the report-style result: 2-D cases use the Hiemenz
constants and axisymmetric cases the Homann constants; the delta function
returns the 2-D coefficient for both flow types (the axisymmetric layer at
equal a is somewhat thinner in the standard tabulations, so the module value
is a conservative documented approximation for the Homann case). Pitfall to
record in the SKILL body: the full similarity ODEs f''' + f f'' + 1 - f'^2 =
0 (Hiemenz) and 2 f''' + 2 f f'' + 1 - f'^2 = 0 (Homann) are NOT integrated;
only their classical constants enter, keeping the leaf deterministic.
Heat transfer is out of scope: no heat-flux function exists here, and the
body must state that stagnation-point convective heat flux at hypersonic
conditions belongs to aerodynamic-heating while this leaf covers the
low-speed laminar momentum boundary layer only.

Identity to test: tau_w at fixed rho, nu, a scales linearly with u_inf (doubling
u_inf doubles tau_w); delta is independent of u_inf at fixed a and scales as
sqrt(nu / a); tau_sph / tau_cyl = (FPP_AXISYM / FPP_2D) * sqrt(1.5 / 2) at
equal u_inf and radius; delta_sph / delta_cyl = sqrt(2 / 1.5) at equal u_inf
and radius; swept_stagnation_gradient at sweep 0 equals the cylinder gradient
2 u_inf / radius at the same radius; the closed forms tau_w = mu * u_inf *
sqrt(a / nu) * fpp and rho * u_inf * sqrt(a * nu) * fpp agree exactly.

## Worked example

Standard air rho = 1.225 kg/m3, u_inf = 30 m/s, nu = 1.5e-5 m2/s so mu =
rho * nu = 1.8375e-5 Pa s, circular-cylinder spinner or leading-edge radius
R = 0.15 m: a = 2 u_inf / R = 400.0 1/s, delta = 2.4 sqrt(nu / a) =
4.647580e-4 m (0.4648 mm), tau_w = mu u_inf sqrt(a / nu) FPP_2D =
1.8375e-5 * 30 * sqrt(400 / 1.5e-5) * 1.2326 = 3.508772 Pa, Cf = 2 tau_w /
(rho u_inf^2) = 6.365119e-3. Same radius as an axisymmetric nose (sphere):
a = 1.5 u_inf / R = 300.0 1/s, delta = 5.366563e-4 m (0.5367 mm), tau_w =
3.234181 Pa, Cf = 5.866995e-3. The ratio checks: delta_sph / delta_cyl =
sqrt(2 / 1.5) = 1.1547005 and tau_sph / tau_cyl = (1.3119 / 1.2326) *
sqrt(1.5 / 2) = 0.9217416. Swept leading edge, R = 0.02 m at sweep 30 deg:
a = 2 * 30 * cos(30 deg) / 0.02 = 2598.0762 1/s, delta = 1.823606e-4 m, and
with the normal component u_n = 30 cos(30 deg) = 25.9808 m/s the 2-D form
gives tau_w = 7.744292 Pa and Cf = 1.873147e-2. Magnitude bounds for the
contract test: at low-speed leading edges (R of order 0.02 to 0.5 m, u_inf of
order 20 to 100 m/s) delta sits in the 0.1 to 1 mm range and the stagnation
Cf in the 1e-3 to 2e-2 range, an order of magnitude above the Blasius
flat-plate local value at a comparable length scale, the expected leading-
edge penalty. Run your module and take the real outputs as assert targets;
the anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w41spec/anchor_stagnation_bl.py (prep-verified by stdlib
math, no ODE integration).

## Validation list (contract test must include)

- stagnation_velocity_gradient("cylinder", 30.0, 0.15) = 400.0 within 1e-9;
  ("sphere", 30.0, 0.15) = 300.0 within 1e-9; synonyms "2d",
  "two-dimensional", "axisymmetric", "axi" accepted case-insensitively.
- stagnation_velocity_gradient ValueErrors: u_inf 0 and negative, radius 0
  and negative, flow_type "cone".
- boundary_layer_thickness(1.5e-5, 400.0) = 4.647580e-4 within 1e-9 and
  (1.5e-5, 300.0) = 5.366563e-4 within 1e-9; monotone decreasing in a;
  ValueErrors at nu 0 and a 0.
- wall_shear_stress(1.225, 1.5e-5, 400.0, 30.0, "cylinder") = 3.508772 within
  1e-5; ("sphere" form) = 3.234181 within 1e-5; ratio identity 0.9217416
  within 1e-9; closed-form identity tau = rho * u_inf * sqrt(a * nu) * fpp =
  3.508771865 agrees with the mu form within 1e-12.
- wall_shear_stress linearity: doubling u_inf to 60 m/s at fixed rho, nu, a
  doubles tau_w to 7.017544 within 1e-9.
- wall_shear_stress ValueErrors: rho 0, nu 0, a 0, u_inf 0, flow_type "cone".
- skin_friction_coefficient(1.225, 30.0, 3.508772) = 6.365119e-3 within
  1e-7; sphere value 5.866995e-3 within 1e-7; identity Cf = 2 tau_w / (rho
  u_inf^2); ValueErrors at rho 0, u_inf 0 and negative tau_w.
- swept_stagnation_gradient(30.0, 0.02, 30.0) = 2598.0762 within 1e-4;
  (30.0, 0.02, 0.0) = 3000.0 within 1e-9, equal to the unswept cylinder
  gradient 2 u_inf / R at R = 0.02 m.
- swept_stagnation_gradient ValueErrors: radius 0, u_inf 0, sweep 95 deg and
  sweep -95 deg.
- Determinism; no RNG; no ODE integration anywhere in the module.
- Magnitude bounds: worked-example delta within 4.6e-4 to 5.4e-4 m and
  stagnation Cf within 5.8e-3 to 6.4e-3 for the cylinder and sphere cases.

## Corpus fragment (eval/hit1-wave41-stagnation-flow-boundary-layer.yaml)

Query 1 (copy verbatim):
  "size the stagnation-flow-boundary-layer on the wing leading edge with the hiemenz-similarity solution from the stagnation-velocity-gradient and report the laminar boundary-layer thickness and the stagnation-wall-shear"
  intent: "aerodynamics; low-speed 2-D laminar stagnation boundary layer, wall shear and skin friction from the Hiemenz similarity solution"
  expected_skill: "aerodynamics/boundary-layer/stagnation-flow-boundary-layer"
Query 2 (copy verbatim):
  "estimate the homann-similarity boundary-layer thickness and wall shear at the axisymmetric nose stagnation point of the radome at low speed and report the skin-friction coefficient"
  intent: "aerodynamics; axisymmetric laminar stagnation boundary layer and skin friction from the Homann similarity solution"
  expected_skill: "aerodynamics/boundary-layer/stagnation-flow-boundary-layer"
Task ids: w41-stagnation-flow-boundary-layer-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the laminar boundary layer,
wall shear and skin friction at a low-speed 2-D or axisymmetric stagnation
point or leading edge:" and include the outputs in the Claim. First tag:
stagnation-flow-boundary-layer. Additional tags ONLY: hiemenz-similarity,
homann-similarity, stagnation-velocity-gradient, stagnation-wall-shear.
NEVER single generic words (stagnation, boundary, layer, shear, friction,
leading, edge, thickness, reynolds). 50-150 words, <=1000 chars, no em dash,
no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): blasius, flat-plate, displacement-
thickness, momentum-thickness, shape-factor, transition-reynolds-number,
skin-friction alone as a tag (boundary-layer-theory); thwaites-integral,
michel-criterion, natural-transition, transition-location, e-n-envelope
(boundary-layer-transition); stratford-separation-criterion, thwaites-lambda-
criterion, separation-point, separation-margin (boundary-layer-separation);
sand-roughness, fully-rough-cf, k-plus-regime, trip-criterion (rough-wall-
skin-friction); recovery-factor, adiabatic-wall-temperature, cold-wall-heat-
flux, reference-temperature-method, reynolds-analogy, sutherland-viscosity,
non-stagnation-heating (flat-plate-skin-friction-heating); sutton-graves,
stagnation-point-heating, radiation-equilibrium-temperature, nose-radius-
bluntness, thermal-protection (aerodynamic-heating); catch-efficiency, mvd,
electrothermal-power, anti-ice, de-ice, freezing-fraction
(ice-protection-sizing); stagnation-pressure (normal-shock, oblique-shock).
