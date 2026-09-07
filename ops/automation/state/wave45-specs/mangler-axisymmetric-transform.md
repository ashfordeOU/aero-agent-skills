# Wave-45 leaf spec: mangler-axisymmetric-transform (aerodynamics,
# boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/mangler-axisymmetric-transform/
- Pack: boundary-layer (present siblings boundary-layer-separation,
  boundary-layer-theory, boundary-layer-transition, rough-wall-skin-friction,
  stagnation-flow-boundary-layer, stokes-creeping-flow-drag,
  unsteady-laminar-stokes-layers; adjacent fences in
  aerodynamics/high-speed/flat-plate-skin-friction-heating, the compressible
  2-D plate-station skin-friction and Reynolds-analogy heating leaf, and
  aerodynamics/high-speed/hypersonic-flow, whose Newtonian cone axial force at
  Mach well above 5 is the pressure side, not the viscous side, of cone flow).
- Provenance: wave-45 recon receipt (ops/automation/state/wave45-recon/
  task-8-receipt.md, GO-4 rank 4, LOW confidence) dispatches this leaf:
  "Mangler transformation mapping a steady laminar boundary layer on an
  axisymmetric body to an equivalent 2-D flow, with the sharp-cone closed-form
  ratios: laminar boundary-layer thickness, wall shear and skin friction on a
  cone sqrt(3) times the flat-plate values at the same running length, plus
  the transformed coordinate machinery for slender axisymmetric bodies
  (quoted handover); Schlichting bodies-of-revolution chapter, White Viscous
  Fluid Flow Mangler section; naca-tr-824; LOW because the wave-42
  van-Driest-II/Chapman-Rubesin adjudication shows the adjudicator fences
  Cf-producing neighbors to flat-plate-skin-friction-heating, mitigated by a
  spec-time boundary sentence stating the leaf consumes sibling Cf machinery
  and outputs only the transform ratios". SPEC-TIME TRIAGE DONE FIRST: every
  boundary-layer pack sibling SKILL.md body plus flat-plate-skin-friction-
  heating and boundary-layer-theory read at prep (see fences below); greps
  re-run at spec time: "mangler" returns 0 files under skills/ and 0 files
  under eval/ (both exit 1), "mangler" appears in 0 corpus tasks, and the
  only axisymmetric-body content in the pack is the Homann stagnation-point
  attachment region of stagnation-flow-boundary-layer, which has no running
  length, no cone surface and no transform content. No leaf in the tree owns
  the Mangler geometry mapping or cone-surface laminar values. GO.
  RECORDED DEVIATION, receipt gate (d) as written: the probe receipt claims
  the pair delta_cone = sqrt(3)*delta_plate with tau_w,cone = sqrt(3)*
  tau_w,plate at equal running length. That pair is not self-consistent: the
  axisymmetric zero-pressure-gradient momentum integral d(theta*r0)/dx =
  r0*Cf/2 forces the laminar cone factor pair to be Cf and wall shear times
  sqrt(3) with momentum, displacement and 99-percent thickness divided by
  sqrt(3) at equal running length (verified exactly in the anchor, identity
  "momentum-integral closure", and by the Mangler inversion below). The
  standard published Mangler result is implemented here: shear and skin
  friction on the cone sqrt(3) times the flat-plate values at equal running
  length (this half of the receipt claim is reproduced exactly), and the cone
  layer thinner by 1/sqrt(3) at the same station. The corpus queries in gate
  (e) only require "the sqrt-3 cone factor" on thickness and shear without
  pinning a direction, so they remain verbatim.
- Claim fences (quoted from the sibling frontmatter and body at prep, none
  owns the Mangler geometry transform or cone-surface laminar layer):
  - flat-plate-skin-friction-heating (aerodynamics/high-speed, the adjacent
    Cf owner) opens "Use when you must estimate the surface skin friction
    heating on a flat plate or vehicle skin at high Mach... local skin
    friction coefficient and Reynolds-analogy heat transfer coefficient...
    for a laminar or turbulent boundary layer" and its body carries the
    plate-station forms "Local skin friction: laminar Cf = 0.664 /
    sqrt(Re_star); turbulent Cf = 0.0592 / Re_star**0.2 (1/7-power law
    form)" with the Eckert reference-temperature compressibility machinery.
    That leaf computes a 2-D plate station in a high-Mach compressible
    stream with heating content; it contains zero bodies of revolution, zero
    geometry transform and zero incompressible cone-surface content. The new
    leaf is a GEOMETRY MAPPING with no thermodynamic or compressibility
    content: it must not claim recovery factor, adiabatic wall temperature,
    reference-temperature method, Reynolds-analogy heat transfer or any
    heat-flux output, and it must not re-derive a competing Cf formula.
  - stagnation-flow-boundary-layer (this pack) opens "Use when you must size
    the laminar boundary layer, wall shear and skin friction at a low-speed
    2-D or axisymmetric stagnation point or leading edge", with the
    axisymmetric content confined to the attachment region: "Axisymmetric
    regime (Homann, flow_type sphere/axisymmetric/axi): a = 1.5 * u_inf / R,
    from u_e = 1.5 u_inf sin(s / R) on a sphere". Its delta = 2.4 sqrt(nu/a)
    is the constant-thickness similarity layer of the stagnation point, with
    no running length x and no cone or body surface. The new leaf must not
    claim Hiemenz or Homann stagnation-point content, stagnation velocity
    gradients or attachment-line layers.
  - boundary-layer-theory (this pack) owns the flat-plate baseline this leaf
    CONSUMES: "Use when the task is boundary-layer thickness estimation,
    displacement or momentum thickness, skin-friction coefficient on a
    surface, Reynolds-number regime classification, or transition location on
    a smooth surface", with the Blasius relations delta = 5.0 x / sqrt(Re_x),
    delta* = 1.7208 x / sqrt(Re_x), theta = 0.664 x / sqrt(Re_x), local
    Cf = 0.664 / sqrt(Re_x). Flat plate only, no axisymmetric body. The new
    leaf takes those flat-plate values as INPUTS at the worked example and
    returns only the cone-scaled values and the transform coordinates; it
    implements no Blasius correlation of its own and no pressure-gradient
    method (the Thwaites traverse machinery stays with boundary-layer-
    separation and boundary-layer-transition, which own the layer evolution
    of 2-D layers and stop at the separation flag and Michel onset).
  - hypersonic-flow (aerodynamics/high-speed) owns the pressure side of cone
    flow at Mach well above 5: modified Newtonian cone axial force
    (corpus task w28-hypersonic-flow-2 routes there); no viscous cone
    content. Whole-tree greps at prep: "mangler" = 0 hits under skills/ and
    0 in eval (both exit 1); "axisymmetric body|bodies of revolution" hits
    only stagnation-flow-boundary-layer and its test file; "cone" under
    skills/aerodynamics hits only the Newtonian hypersonic pressure-side
    leaves plus the Homann sphere-geometry test file, none of which owns a
    cone-surface or axisymmetric-body boundary-layer transform. GENUINE
    aerodynamics gap (fresh probe, GO): no leaf owns the Mangler
    transformation of a laminar axisymmetric-body boundary layer or the
    sharp-cone closed-form ratios.
- Standards id: naca-tr-824 (reference-only, present in standards-map.yaml
  line 171, the sibling precedent for the whole boundary-layer pack; the
  classical transform treatment follows Schlichting Boundary-Layer Theory
  (boundary layers on bodies of revolution, Mangler transformation) and
  White Viscous Fluid Flow (Mangler transformation section), whose material
  is cited through the report). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Map the steady laminar incompressible boundary layer on a slender
axisymmetric body of revolution to an equivalent 2-D flow with the Mangler
transformation, and produce the sharp-cone closed-form values at equal
running length from flat-plate baseline values. For a body with surface
radius r0(x) at running length x measured from the nose or apex, the
transformation of Mangler (1948): the equivalent 2-D running length
xi = integral_0^x (r0(t)/L)^2 dt, the transformed normal coordinate
ybar = (r0(x)/L) * y, and the transformed streamwise velocity ubar(xi, ybar)
= u(x, y), where L is a reference length, carries the steady laminar
axisymmetric boundary-layer equations into the plane 2-D boundary-layer
equations for the same edge-velocity history. The sharp cone, r0(x) =
x*tan(alpha) with alpha the semi-vertex angle, has a constant edge velocity
(the conical potential flow has no streamwise pressure gradient), so its
transformed flow is the Blasius zero-pressure-gradient layer and the
mapping closes in closed form: at the same running length x and the same
edge velocity u_e, the cone wall shear and local skin-friction coefficient
are tau_w,cone = sqrt(3)*tau_w,flat and Cf,cone = sqrt(3)*Cf,flat, while
the 99-percent, displacement and momentum thicknesses on the cone are
1/sqrt(3) times the flat-plate values, delta_cone = delta_flat/sqrt(3),
delta*_cone = delta*_flat/sqrt(3), theta_cone = theta_flat/sqrt(3); the
cone layer is thinner and more strongly sheared than the plate layer at the
same station, the pair that satisfies the axisymmetric momentum integral
d(theta*r0)/dx = r0*Cf/2 exactly. Produces the cone-surface radius and the
equivalent 2-D running length for the cone and for general slender
power-law bodies r0(x) = A*x^n, the transformed normal-coordinate mapping,
the Blasius station-scaling helpers used to evaluate the equivalent 2-D
layer, and the cone values (skin friction, wall shear, 99-percent,
displacement and momentum thickness) from flat-plate baseline values passed
in as arguments, in SI units, that anchor laminar cone-surface and
body-of-revolution boundary-layer estimates. Does NOT do: any skin-friction
or thickness formula of its own, the flat-plate Blasius and 1/7-power
correlations, displacement or momentum thickness definitions or Reynolds-
number-regime classification (boundary-layer-theory owns the flat-plate
machinery, whose values this leaf consumes as inputs at the same running
length); the Hiemenz and Homann stagnation-point layers, stagnation
velocity gradients or attachment-line content of the nose region
(stagnation-flow-boundary-layer); compressible-flow content of any kind,
the Eckert reference-temperature method, recovery factor, adiabatic wall
temperature, Reynolds-analogy heat transfer, heat flux, or the compressible
plate-station Cf of the high-Mach leaf (flat-plate-skin-friction-heating);
the Thwaites, Michel, Stratford or roughness machinery of the layer-evolution
siblings (boundary-layer-separation, boundary-layer-transition,
rough-wall-skin-friction); the Newtonian cone axial force of modified
impact theory at Mach well above 5 (hypersonic-flow); turbulent layers and
the turbulent cone rule, which has no exact closed-form factor (the sqrt(3)
family is laminar only). Laminar incompressible steady flow only, constant
nu; the edge velocity on the cone is treated as constant, and the general
slender-body mapping returns only the transformed coordinates and lengths,
leaving the 2-D pressure-gradient layer solution (when u_e varies) to the
layer-evolution siblings. No heat transfer, no compressibility, no
thermodynamics anywhere in this leaf.

## Model (implement exactly)

Pure stdlib, math only, closed form. Geometry convention: x is the running
length along the surface from the apex (cone) or nose (general body), y is
the distance normal to the surface, r0(x) is the body radius at station x,
alpha is the cone semi-vertex angle in degrees, L is the Mangler reference
length in m (the transform is invariant to L: xi scales as L^-2 and ybar as
L^-1, so every physical output is L-free). All formulas pinned exactly as
written; every function below derives from them.

Module constants:
- SQRT3 = 1.7320508075688772, sqrt(3), the laminar cone shear and
  skin-friction factor at equal running length.
- INV_SQRT3 = 0.5773502691896258, 1/sqrt(3), the laminar cone thickness
  factor (99-percent, displacement and momentum thickness all divide by
  sqrt(3) at equal running length).
- Worked-example air (boundary-layer pack convention, shared with
  stagnation-flow-boundary-layer): RHO_AIR = 1.225 kg/m3, NU_AIR = 1.5e-5
  m2/s; dynamic viscosity derived MU_AIR = RHO_AIR*NU_AIR = 1.8375e-05 Pa s,
  never an input.
- Worked-example geometry: HALF_ANGLE_DEG = 5.0 deg, X_RUN = 2.0 m,
  U_E = 30.0 m/s (constant cone edge velocity), REF_LENGTH = 1.0 m.
- Worked-example flat-plate baseline (values CONSUMED from the sibling
  boundary-layer-theory correlations at Re_x = 4.0e6, held only so the
  worked example is reproducible; the cone functions never see them):
  BLASIUS_DELTA_COEFF = 5.0, BLASIUS_DSTAR_COEFF = 1.7208,
  BLASIUS_THETA_COEFF = 0.664, BLASIUS_CF_COEFF = 0.664,
  BLASIUS_TAU_COEFF = 0.332. These are inputs, not owned formulas.

Defining relations:
- Cone geometry: r0(x) = x*tan(alpha), radius proportional to running
  length. Slender-cone exactness: tan(alpha) is used, never the small-angle
  approximation.
- Mangler transformed running length: xi(x) = integral_0^x (r0(t)/L)^2 dt.
  Cone closed form: xi = tan(alpha)^2 * x^3 / (3*L^2) = r0(x)^2*x/(3*L^2),
  so xi scales as x^3 along a cone (the half-length station has one eighth
  of the xi of the full station).
- Transformed normal coordinate: ybar = (r0(x)/L)*y; the inverse map is
  y = ybar*L/r0(x).
- General slender power-law body r0(x) = A*x^n (exponent 0 the cylinder,
  exponent 1 the cone): xi = A^2 * x^(2n+1) / ((2n+1)*L^2), closed form;
  the cone closed form above is the n = 1 case with A = tan(alpha).
- Equal-running-length cone ratios (laminar, incompressible, constant
  u_e): tau_w,cone = SQRT3*tau_w,flat and Cf,cone = SQRT3*Cf,flat at the
  same x (Cf uses the same 0.5*rho*u_e^2 normalization, so the shear ratio
  and the Cf ratio are identical); delta_cone = delta_flat*INV_SQRT3,
  delta*_cone = delta*_flat*INV_SQRT3, theta_cone = theta_flat*INV_SQRT3 at
  the same x. The pair satisfies the axisymmetric zero-pressure-gradient
  momentum integral d(theta*r0)/dx = r0*Cf/2 exactly (identity check
  below); the shape factor H = delta*/theta is preserved by the transform
  (the factors cancel), H_cone = H_flat = 2.591566265 at the Blasius
  baseline.
- Blasius station scaling (consumption helpers, no constants of their own):
  local Cf scales as 1/sqrt(x), so cf(x2) = cf(x1)*sqrt(x1/x2); the
  99-percent thickness scales as sqrt(x), so delta(x2) =
  delta(x1)*sqrt(x2/x1). These evaluate the equivalent 2-D layer at xi from
  the flat-plate value at x.
- Mangler plane-to-physical scaling for the cone (the derivation identities
  the ratio functions to): physical shear is the transformed shear times
  r0(x)/L, tau_w,cone(x) = (r0(x)/L)*tau_w,2D(xi(x)) with tau_w,2D the wall
  shear of the equivalent 2-D layer; the physical thickness is the
  transformed thickness times L/r0(x), delta_cone(x) = (L/r0(x))*
  delta_2D(xi(x)). Composed with the Blasius station scaling these reduce
  exactly to the SQRT3 and INV_SQRT3 closed forms above.

Functions (signatures and validation pinned; module holds no other
functions):
- cone_radius(x, half_angle_deg) -> float
  x*math.tan(math.radians(half_angle_deg)) in m, the cone surface radius at
  running length x. ValueError if x <= 0 or half_angle_deg <= 0 or
  half_angle_deg >= 90.
- mangler_xi(x, half_angle_deg, ref_length) -> float
  The Mangler-transformed (equivalent 2-D) running length for the cone,
  cone_radius(x, half_angle_deg)**2 * x / (3.0*ref_length**2), in m.
  ValueError set as cone_radius plus ref_length <= 0.
- transformed_normal_coordinate(x, y, half_angle_deg, ref_length) -> float
  (cone_radius(x, half_angle_deg)/ref_length)*y in m, the transformed normal
  coordinate ybar; the wall y = 0 maps to 0. ValueError if y < 0 plus the
  mangler_xi set.
- powerlaw_mangler_xi(x, amplitude, exponent, ref_length) -> float
  amplitude**2 * x**(2.0*exponent + 1.0) / ((2.0*exponent + 1.0)*
  ref_length**2) in m, the Mangler xi for the slender body
  r0(x) = amplitude*x^exponent; exponent 0 is the cylinder, exponent 1 is
  the cone (identity check against mangler_xi with amplitude = tan(alpha)).
  ValueError if x <= 0 or amplitude <= 0 or exponent < 0 or ref_length <= 0.
- blasius_cf_at_station(cf_at_x1, x1, x2) -> float
  cf_at_x1*math.sqrt(x1/x2), the local flat-plate Cf at station x2 from its
  value at x1 (Cf ~ 1/sqrt(x) Blasius scaling). Consumption helper, no
  Blasius constant inside. ValueError if cf_at_x1 <= 0 or x1 <= 0 or
  x2 <= 0.
- blasius_delta_at_station(delta_at_x1, x1, x2) -> float
  delta_at_x1*math.sqrt(x2/x1), the 99-percent flat-plate thickness at
  station x2 from its value at x1 (delta ~ sqrt(x) Blasius scaling).
  Consumption helper, no Blasius constant inside. ValueError set as
  blasius_cf_at_station.
- cone_skin_friction(cf_flat) -> float
  SQRT3*cf_flat, the local skin-friction coefficient on the cone at running
  length x from the flat-plate value at the same x and edge velocity.
  ValueError if cf_flat <= 0.
- cone_wall_shear(tau_w_flat) -> float
  SQRT3*tau_w_flat in Pa, the wall shear on the cone at running length x
  from the flat-plate value at the same x and edge velocity. ValueError if
  tau_w_flat <= 0.
- cone_boundary_layer_thickness(delta_flat) -> float
  INV_SQRT3*delta_flat in m, the 99-percent laminar thickness on the cone at
  running length x from the flat-plate value at the same x. ValueError if
  delta_flat <= 0.
- cone_displacement_thickness(delta_star_flat) -> float
  INV_SQRT3*delta_star_flat in m, the displacement thickness on the cone at
  running length x from the flat-plate value at the same x. ValueError set
  as cone_boundary_layer_thickness.
- cone_momentum_thickness(theta_flat) -> float
  INV_SQRT3*theta_flat in m, the momentum thickness on the cone at running
  length x from the flat-plate value at the same x. ValueError set as
  cone_boundary_layer_thickness.

Identities to test (closed form):
- Mangler end-to-end pipeline for shear, module-only (no Blasius constant):
  with xi = mangler_xi(x, alpha, L), cf_2D = blasius_cf_at_station(cf_flat,
  x, xi) and cone_radius r0(x), the composed value (r0(x)/L)*cf_2D equals
  cone_skin_friction(cf_flat) to float noise (anchor residual ratio 1 within
  1e-12). The equivalent statement for thickness: (L/r0(x))*
  blasius_delta_at_station(delta_flat, x, xi) equals
  cone_boundary_layer_thickness(delta_flat) within 1e-12 relative.
- Equal-running-length ratios: cone_wall_shear(tau_flat)/tau_flat and
  cone_skin_friction(cf_flat)/cf_flat equal SQRT3 = 1.7320508075688772
  within 1e-12; cone_boundary_layer_thickness(delta_flat)/delta_flat,
  cone_displacement_thickness(delta_star_flat)/delta_star_flat and
  cone_momentum_thickness(theta_flat)/theta_flat equal INV_SQRT3 =
  0.5773502691896258 within 1e-12.
- Shape factor preservation: cone_displacement_thickness(delta_star_flat) /
  cone_momentum_thickness(theta_flat) equals delta_star_flat/theta_flat =
  2.591566265 (1.7208/0.664) within 1e-9: the transform does not change the
  layer shape, only its scale.
- Axisymmetric momentum-integral closure (analytic, no module call needed):
  with the cone factor pair, d(theta_cone*r0)/dx = r0*Cf,cone/2 identically
  at every x; in closed form (0.664/sqrt(3))*tan(alpha)*sqrt(nu/u_e)*1.5*
  sqrt(x) equals x*tan(alpha)*(sqrt(3)*0.664*sqrt(nu/(u_e*x)))/2, the anchor
  ratio is 1 to float noise. The reversed pair (both sqrt(3)) fails this
  integral by a factor of 3, which is why the receipt's gate (d) thickness
  direction is recorded as a deviation above.
- Power-law identity: mangler_xi(x, alpha, L) equals powerlaw_mangler_xi(x,
  tan(alpha), 1.0, L) within 1e-12 relative; mangler_xi(x/2, alpha, L)
  equals mangler_xi(x, alpha, L)/8 within 1e-12 (xi ~ x^3).
- Consumption-helper round trips: blasius_cf_at_station(
  blasius_cf_at_station(cf, x1, x2), x2, x1) equals cf, and the delta
  helper likewise, within 1e-12; blasius_cf_at_station(cf, x, 2*x) equals
  cf/sqrt(2) within 1e-12.
- Cone thickness ratio bound: delta_cone at the worked station is between
  2.0e-3 m and 3.5e-3 m, below delta_flat = 5.0e-3 m (thinner layer, higher
  shear, the laminar cone signature).
- ValueErrors across the module: x at 0 and -1.0 on cone_radius and
  mangler_xi; half_angle_deg at 0 and 90 on cone_radius, mangler_xi and
  transformed_normal_coordinate; y at -1e-6 on
  transformed_normal_coordinate; ref_length at 0 and -1.0 on mangler_xi,
  transformed_normal_coordinate and powerlaw_mangler_xi; amplitude at 0 and
  exponent at -0.5 on powerlaw_mangler_xi; cf_at_x1 at 0, x1 at 0 and x2 at
  0 on both station helpers; cf_flat at 0 and -1e-4 on cone_skin_friction;
  tau_w_flat at 0 on cone_wall_shear; delta_flat at -1e-3 on
  cone_boundary_layer_thickness; delta_star_flat at 0 on
  cone_displacement_thickness; theta_flat at -1e-5 on
  cone_momentum_thickness.
- Determinism; no imports beyond math; closed form, no iteration and no ODE
  or quadrature loop anywhere (the power-law family makes every integral
  analytic).

## Worked example

Slender cone at half_angle 5.0 deg in standard air nu = 1.5e-5 m2/s,
rho = 1.225 kg/m3, constant edge velocity u_e = 30.0 m/s, running length
x = 2.0 m, reference length L = 1.0 m. All values below are REAL outputs of
the prep anchor /tmp/w45spec/anchor_mangler_axisymmetric_transform.py
(stdlib math, closed form, exit 0; 15 identities PASS, 18 ValueError cases
PASS under both /usr/bin/python3 3.9.6 and 3.13.12).
- Reynolds number at the station: Re_x = u_e*x/nu = 4.0000000e6,
  sqrt(Re_x) = 2000.0 exactly.
- Geometry:
  - Cone surface radius r0 = cone_radius(2.0, 5.0) = 1.749773271e-01 m
    (0.1749773271 m = x*tan(5 deg)).
  - Mangler equivalent 2-D running length xi = mangler_xi(2.0, 5.0, 1.0) =
    2.041137665e-02 m: the 2 m cone surface maps to a 2 cm flat plate, the
    geometric content of the transformation.
  - Transformed normal coordinate at the flat-plate layer top:
    transformed_normal_coordinate(2.0, 5.0e-3, 5.0, 1.0) =
    8.748866353e-04 m.
  - Power-law bodies at x = 2.0 m: r0 = 0.05*x^0.5 gives xi =
    5.00000000e-03 m, the cylinder r0 = 0.1 m gives xi = 2.00000000e-02 m,
    and the cone (amplitude tan(5 deg), exponent 1) reproduces xi =
    2.041137665e-02 m.
- Flat-plate baseline at x = 2.0 m (consumed from the boundary-layer-theory
  Blasius correlations, the sibling values that this leaf takes as inputs):
  - cf_flat = 0.664/sqrt(Re_x) = 3.32000000e-04.
  - tau_w,flat = 0.332*rho*u_e^2/sqrt(Re_x) = 1.83015000e-01 Pa.
  - delta_flat = 5.0*x/sqrt(Re_x) = 5.00000000e-03 m (5 mm).
  - delta*_flat = 1.7208*x/sqrt(Re_x) = 1.72080000e-03 m.
  - theta_flat = 0.664*x/sqrt(Re_x) = 6.64000000e-04 m.
- Cone values at the SAME running length x = 2.0 m:
  - cf_cone = cone_skin_friction(cf_flat) = 5.750408681e-04, ratio to the
    plate value 1.732050808 = sqrt(3) exactly.
  - tau_w,cone = cone_wall_shear(tau_w_flat) = 3.169912785e-01 Pa, ratio
    1.732050808 = sqrt(3); the shear ratio equals the Cf ratio because both
    use the same 0.5*rho*u_e^2 normalization.
  - delta_cone = cone_boundary_layer_thickness(delta_flat) =
    2.886751346e-03 m, ratio 0.5773502692 = 1/sqrt(3): the cone layer is
    thinner than the plate layer at the same station.
  - delta*_cone = cone_displacement_thickness(delta*_flat) =
    9.935043432e-04 m, ratio 0.5773502692.
  - theta_cone = cone_momentum_thickness(theta_flat) = 3.833605787e-04 m,
    ratio 0.5773502692.
  - Shape factor on the cone: H_cone = delta*_cone/theta_cone =
    2.591566265, identical to H_flat = 2.591566265 (the transform scales
    the layer, it does not reshape it).
  - Momentum-integral closure at the worked station: the analytic
    d(theta_cone*r0)/dx equals r0*Cf,cone/2 to float noise (identity PASS),
    the consistency check that the sqrt(3) and 1/sqrt(3) factor pair obey
    the axisymmetric boundary-layer momentum balance.
- Read-off: a 5 deg half-angle cone at 2 m running length in a 30 m/s
  stream (Re_x = 4e6) carries a laminar skin friction of 5.75e-4, exactly
  sqrt(3) times the 3.32e-4 of the flat plate at the same station, with its
  boundary layer squeezed from 5.0 mm to 2.89 mm; the equivalent 2-D flow
  lives on a 2 cm plate, and it is on that short equivalent plate that the
  flat-plate correlations of boundary-layer-theory are evaluated before the
  mapping scales the values back to the cone surface. The sqrt(3) family is
  the laminar cone signature: thinner layer, higher wall shear, the reason
  a laminar sharp-cone surface runs hotter than the flat plate at the same
  Reynolds number in the heat-transfer analogy, which this momentum-only
  leaf does not compute.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w45spec/anchor_mangler_axisymmetric_
transform.py (stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- cone_radius(2.0, 5.0) = 1.749773271e-01 m within 1e-6 relative and equal
  to 2.0*math.tan(math.radians(5.0)) within 1e-12 (the degrees-to-radians
  conversion is internal to the module).
- mangler_xi(2.0, 5.0, 1.0) = 2.041137665e-02 m within 1e-6 relative;
  equal to cone_radius(2.0, 5.0)**2*2.0/3.0 within 1e-12; mangler_xi(1.0,
  5.0, 1.0) = mangler_xi(2.0, 5.0, 1.0)/8 within 1e-9 (xi ~ x^3); doubling
  ref_length quarters xi.
- powerlaw_mangler_xi(2.0, math.tan(math.radians(5.0)), 1.0, 1.0) equals
  mangler_xi(2.0, 5.0, 1.0) within 1e-12 relative;
  powerlaw_mangler_xi(2.0, 0.1, 0.0, 1.0) = 2.00000000e-02 m (cylinder)
  within 1e-12; powerlaw_mangler_xi(2.0, 0.05, 0.5, 1.0) = 5.00000000e-03 m
  within 1e-12.
- transformed_normal_coordinate(2.0, 5.0e-3, 5.0, 1.0) = 8.748866353e-04 m
  within 1e-6 relative; the inverse y = ybar*ref_length/cone_radius round
  trips within 1e-12; transformed_normal_coordinate(2.0, 0.0, 5.0, 1.0) =
  0.0 exactly (the wall maps to the wall).
- Mangler pipeline for shear: cf_2D = blasius_cf_at_station(3.32e-4, 2.0,
  2.041137665e-2), then (cone_radius(2.0, 5.0)/1.0)*cf_2D equals
  cone_skin_friction(3.32e-4) = 5.750408681e-04 within 1e-9 relative.
- Mangler pipeline for thickness: delta_2D = blasius_delta_at_station(5.0e-3,
  2.0, 2.041137665e-2), then (1.0/cone_radius(2.0, 5.0))*delta_2D equals
  cone_boundary_layer_thickness(5.0e-3) = 2.886751346e-03 m within 1e-9
  relative.
- cone_skin_friction(3.32e-4) = 5.750408681e-04 within 1e-9 relative;
  ratio to input = SQRT3 = 1.7320508075688772 within 1e-12; magnitude bound
  between 4.0e-4 and 8.0e-4.
- cone_wall_shear(0.183015) = 3.169912785e-01 Pa within 1e-6 relative;
  ratio = SQRT3 within 1e-12; cone_wall_shear(0.183015)/cone_skin_friction
  ratio consistency: both equal SQRT3 within 1e-9 (same 0.5*rho*u_e^2
  normalization).
- cone_boundary_layer_thickness(5.0e-3) = 2.886751346e-03 m within 1e-9
  relative; ratio = INV_SQRT3 = 0.5773502691896258 within 1e-12; magnitude
  bound between 2.0e-3 and 3.5e-3 m and strictly below 5.0e-3 (cone layer
  thinner than the plate layer).
- cone_displacement_thickness(1.7208e-3) = 9.935043432e-04 m within 1e-9
  relative; cone_momentum_thickness(6.64e-4) = 3.833605787e-04 m within
  1e-9 relative; each ratio = INV_SQRT3 within 1e-12.
- Shape factor: cone_displacement_thickness(1.7208e-3)/
  cone_momentum_thickness(6.64e-4) = 2.591566265 within 1e-9, equal to
  1.7208/0.664 within 1e-9.
- Momentum-integral closure at the worked station: (0.664/sqrt(3))*
  tan(5 deg)*sqrt(1.5e-5/30.0)*1.5*sqrt(2.0) equals 2.0*tan(5 deg)*
  (sqrt(3)*0.664*sqrt(1.5e-5/(30.0*2.0)))/2 within 1e-9 relative (anchor
  ratio 1).
- Consumption helpers: blasius_cf_at_station(3.32e-4, 2.0, 4.0) =
  2.3475945135e-04 (cf(2x) = cf(x)/sqrt(2)) within 1e-9; both helpers round
  trip over (x1, x2) and back within 1e-12.
- Determinism: two identical calls return bitwise-equal floats; the module
  imports math only and contains no loop, no random import and no ODE or
  quadrature call.
- ValueErrors: x at 0 and -1.0 on cone_radius and mangler_xi;
  half_angle_deg at 0 and 90 on cone_radius, mangler_xi and
  transformed_normal_coordinate; y at -1e-6 on
  transformed_normal_coordinate; ref_length at 0 and -1.0 on mangler_xi,
  transformed_normal_coordinate and powerlaw_mangler_xi; amplitude at 0 and
  exponent at -0.5 on powerlaw_mangler_xi; cf_at_x1 at 0, x1 at 0 and x2
  at 0 on blasius_cf_at_station and blasius_delta_at_station; cf_flat at 0
  and -1e-4 on cone_skin_friction; tau_w_flat at 0 on cone_wall_shear;
  delta_flat at -1e-3 on cone_boundary_layer_thickness; delta_star_flat at
  0 on cone_displacement_thickness; theta_flat at -1e-5 on
  cone_momentum_thickness.
- Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
  computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave45-mangler-axisymmetric-transform.yaml)

Query 1 (copy verbatim):
  "apply the mangler-transformation to the laminar boundary layer on the
  sharp cone: report the cone boundary-layer thickness and skin friction
  versus the flat-plate values at the same running length with the sqrt-3
  cone factor"
  intent: "aerodynamics; geometry transform of a steady laminar
  incompressible boundary layer on an axisymmetric body of revolution into
  an equivalent 2-D flow, with the sharp-cone closed-form ratios at equal
  running length: the sqrt(3) laminar cone factor on wall shear and skin
  friction, the inverse sqrt(3) factor on the cone boundary-layer
  thickness, and the Mangler transformed coordinate machinery for slender
  axisymmetric bodies"
  expected_skill: "aerodynamics/boundary-layer/
  mangler-axisymmetric-transform"
Query 2 (copy verbatim):
  "transform the axisymmetric-body boundary layer into the equivalent 2-D
  flow with the mangler-transformation coordinate mapping and compute the
  cone wall-shear ratio against the flat plate for the laminar case"
  intent: "aerodynamics; Mangler mapping of an axisymmetric-body laminar
  boundary layer to an equivalent 2-D flow through the transformed running
  length xi = integral (r0/L)^2 dx and the transformed normal coordinate,
  with the laminar cone wall-shear ratio sqrt(3) against the flat plate at
  the same running length"
  expected_skill: "aerodynamics/boundary-layer/
  mangler-axisymmetric-transform"
Task ids: w45-mangler-axisymmetric-transform-1 and -2. The queries stay
inside the aerodynamics viscous boundary-layer vein and carry the
distinctive leaf tokens (mangler-transformation, cone-boundary-layer,
axisymmetric-body, sqrt-3 cone factor, cone wall-shear ratio) so no other
task can capture them: the corpus greps at prep found "mangler" in NO
existing task (whole-file grep, exit 1); the single cone task in the
corpus, w28-hypersonic-flow-2, sizes a Newtonian cone axial force from
modified impact pressure and routes to hypersonic-flow with no viscous
content; the boundary-layer pack tasks route on the flat-plate and
transition tokens of boundary-layer-theory and the pack siblings, none of
which carries an axisymmetric-body or cone-surface claim. Query wording
keeps "skin friction" and "thickness" attached to the flat-plate comparison
and to the mangler/cone compounds rather than standing alone, so the
flat-plate leaf boundary-layer-theory and the Cf-owning high-Mach leaf
cannot capture them.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must map the steady laminar boundary
layer on a slender axisymmetric body of revolution or a sharp cone into an
equivalent 2-D flow with the mangler-transformation:" and include the
outputs in the Claim. First tag: mangler-transformation. Additional tags
ONLY: cone-boundary-layer, axisymmetric-body-boundary-layer,
laminar-cone-factor, body-of-revolution-bl. NEVER single generic words
(cone, transformation, boundary-layer, mapping, friction, shear,
thickness, axisymmetric, body) and NEVER the sibling-owned tokens
hiemenz-similarity, homann-similarity, stagnation-velocity-gradient,
stagnation-wall-shear, attachment-line-flow, nose-boundary-layer
(stagnation-flow-boundary-layer); recovery-factor, adiabatic-wall-
temperature, cold-wall-heat-flux, reference-temperature-method,
reynolds-analogy-factor, turbulent-plate-heating, flat-plate-heating,
eckert-reference-temperature (flat-plate-skin-friction-heating); blasius,
displacement-thickness, momentum-thickness, reynolds-number-regime,
transition-location, skin-friction-coefficient (boundary-layer-theory and
the pack siblings, whose flat-plate values this leaf consumes as inputs);
thwaites-integral, michel-criterion, stratford-criterion, k-plus,
sand-roughness (layer-evolution siblings); cone-axial-force,
newtonian-impact-pressure, sphere-drag-coefficient (hypersonic-flow).
50-150 words, <=1000 chars, no em dash, action verb present. The
description must not assign flow regimes, transition classes or any
categorical verdict, and must not claim compressible or heat-transfer
outputs. Recommended wording:
"Use when you must map the steady laminar boundary layer on a slender
axisymmetric body of revolution or a sharp cone into an equivalent 2-D flow
with the mangler-transformation: evaluate the Mangler transformed running
length xi = integral (r0/L)^2 dx and the transformed normal coordinate from
the body radius distribution, the cone-surface radius and the equivalent
2-D length for power-law bodies, and the sharp-cone values at equal running
length from flat-plate baseline values passed in: skin friction and wall
shear times the sqrt-3 laminar cone factor, and the 99-percent,
displacement and momentum thicknesses divided by sqrt-3, so the thinner
higher-shear cone layer is reported against the plate layer at the same
station. Produces the cone boundary-layer values and the coordinate mapping
in SI units that anchor laminar cone-surface and body-of-revolution
boundary-layer estimates. Trigger: mangler-transformation,
cone-boundary-layer, axisymmetric-body-boundary-layer, laminar-cone-factor,
body-of-revolution-bl."
