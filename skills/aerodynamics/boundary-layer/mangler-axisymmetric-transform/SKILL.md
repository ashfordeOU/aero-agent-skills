---
name: mangler-axisymmetric-transform
description: "Use when you must map the steady laminar boundary layer on a slender axisymmetric body of revolution or a sharp cone into an equivalent 2-D flow with the mangler-transformation: evaluate the Mangler transformed running length xi = integral (r0/L)^2 dx and the transformed normal coordinate from the body radius distribution, the cone-surface radius and the equivalent 2-D length for power-law bodies, and the sharp-cone values at equal running length from flat-plate baseline values passed in: skin friction and wall shear times the sqrt-3 laminar cone factor, the 99-percent, displacement and momentum thicknesses divided by sqrt-3, the thinner higher-shear cone layer at the same station. Produces the cone boundary-layer values and the coordinate mapping in SI units that anchor laminar cone-surface and body-of-revolution boundary-layer estimates. Trigger: mangler-transformation, cone-boundary-layer, axisymmetric-body-boundary-layer, laminar-cone-factor, body-of-revolution-bl."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: boundary-layer
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: boundary-layer
  tags: [mangler-transformation, cone-boundary-layer, axisymmetric-body-boundary-layer, laminar-cone-factor, body-of-revolution-bl]
  version: 0.1.0
  author: AeroSkills
---

# Mangler Axisymmetric-Body Transform (aerodynamics/boundary-layer/mangler-axisymmetric-transform)

Use when you must map the steady laminar incompressible boundary layer on a
slender axisymmetric body of revolution or a sharp cone into an equivalent
2-D flow with the Mangler transformation (Mangler, 1948, in the form
Schlichting Boundary-Layer Theory, boundary layers on bodies of revolution,
and White Viscous Fluid Flow present it). This leaf implements the geometry
mapping: the transformed running length xi = integral (r0/L)^2 dx, the
transformed normal coordinate ybar = (r0/L)*y, the power-law body closed
forms, and the sharp-cone closed-form ratios at equal running length, in
pure Python stdlib, closed form, no iteration. On a sharp cone the
transformed flow is the Blasius zero-pressure-gradient layer, so the
mapping closes: wall shear and skin friction are sqrt(3) times the
flat-plate values at the same running length, and the 99-percent,
displacement and momentum thicknesses are 1/sqrt(3) times the flat-plate
values, the thinner higher-shear cone layer. It consumes the flat-plate
baseline values as arguments from the sibling boundary-layer-theory
correlations and outputs only the cone-scaled values and the transform
coordinates: it owns no skin-friction or thickness correlation, no
stagnation-point layer, no compressible flow and no heat transfer, which
stay with the sibling leaves listed below. Laminar incompressible steady
flow only, constant nu; the cone edge velocity is constant, and for general
slender bodies with varying edge velocity this leaf returns only the
transformed coordinates and lengths, leaving the 2-D pressure-gradient
layer solution to the layer-evolution siblings.

## Domain quick reference

Geometry convention: x is the running length along the surface from the
apex (cone) or nose (general body), y is the distance normal to the
surface, r0(x) is the body radius at station x, alpha is the cone
semi-vertex angle in degrees, L is the Mangler reference length in m. The
transform is invariant to L: xi scales as L^-2 and ybar as L^-1, so every
physical output is L-free. Module constants: SQRT3 = 1.7320508075688772,
INV_SQRT3 = 0.5773502691896258, RHO_AIR = 1.225 kg/m3, NU_AIR = 1.5e-5
m2/s with dynamic viscosity always derived MU_AIR = RHO_AIR*NU_AIR =
1.8375e-05 Pa s, never an input.

- Cone geometry: r0(x) = x*tan(alpha), m, exact tan, never the
  small-angle approximation.
- Mangler transformed running length, cone closed form:
  xi = integral_0^x (r0(t)/L)^2 dt = r0(x)^2*x/(3*L^2), m, so xi scales as
  x^3 along a cone: the half-length station carries one eighth of the
  full-station xi.
- Transformed normal coordinate: ybar = (r0(x)/L)*y, m, wall to wall
  (y = 0 maps to ybar = 0); inverse map y = ybar*L/r0(x).
- General slender power-law body r0(x) = A*x^n (exponent 0 the cylinder,
  exponent 1 the cone): xi = A^2*x^(2n+1)/((2n+1)*L^2), closed form.
- Equal-running-length cone ratios (laminar, incompressible, constant
  u_e): tau_w,cone = SQRT3*tau_w,flat and Cf,cone = SQRT3*Cf,flat at the
  same x (identical ratios, both use the same 0.5*rho*u_e^2
  normalization); delta_cone = INV_SQRT3*delta_flat, delta*_cone =
  INV_SQRT3*delta*_flat, theta_cone = INV_SQRT3*theta_flat at the same x.
- Momentum-integral closure: the pair satisfies the axisymmetric
  zero-pressure-gradient balance d(theta*r0)/dx = r0*Cf/2 exactly; the
  reversed pair (both factors sqrt(3)) fails by a factor of 3.
- Shape factor: H = delta*/theta is preserved by the transform,
  H_cone = H_flat = 2.591566265 at the Blasius baseline.
- Blasius station scaling (consumption helpers, no constants inside):
  local Cf ~ 1/sqrt(x), cf(x2) = cf(x1)*sqrt(x1/x2); 99-percent thickness
  ~ sqrt(x), delta(x2) = delta(x1)*sqrt(x2/x1).
- Mangler plane-to-physical scaling for the cone: physical shear is the
  transformed shear times r0(x)/L and physical thickness is the
  transformed thickness times L/r0(x); composed with the Blasius station
  scaling these reduce exactly to the SQRT3 and INV_SQRT3 closed forms.

## Workflow

1. Fix the cone state and run the geometry traverse: the semi-vertex angle
   alpha, the running length x and the reference length L. Read the cone
   surface radius with cone_radius(x, half_angle_deg) and the equivalent
   2-D running length with mangler_xi(x, half_angle_deg, ref_length),
   where xi = cone_radius^2*x/(3*L^2) carries the x^3 content of the
   transformation.
2. Map the layer coordinates: the transformed normal coordinate ybar with
   transformed_normal_coordinate(x, y, half_angle_deg, ref_length), and
   the equivalent 2-D length of a general slender power-law body with
   powerlaw_mangler_xi(x, amplitude, exponent, ref_length) (exponent 0 the
   cylinder, exponent 1 the cone).
3. Consume the flat-plate baseline: take the sibling
   boundary-layer-theory values at the same running length x and edge
   velocity (local skin-friction coefficient, wall shear, 99-percent,
   displacement and momentum thicknesses) as inputs. This leaf derives
   none of them; they are passed in as arguments.
4. Scale the cone skin friction and wall shear: cone_skin_friction
   (cf_flat) and cone_wall_shear(tau_w_flat) multiply the flat-plate
   values by the sqrt-3 laminar cone factor at the same running length.
5. Scale the cone thicknesses: cone_boundary_layer_thickness(delta_flat),
   cone_displacement_thickness(delta_star_flat) and
   cone_momentum_thickness(theta_flat) divide the flat-plate values by
   sqrt-3 (the inverse sqrt-3 factor) at the same running length.
6. Check the shape factor: the cone displacement-to-momentum ratio equals
   the flat-plate shape factor 2.591566265 on the Blasius baseline; the
   transformation scales the layer, it does not reshape it.
7. Evaluate the equivalent 2-D layer at the Mangler length xi with the
   Blasius station-scaling helpers blasius_cf_at_station(cf_at_x1, x1, x2)
   and blasius_delta_at_station(delta_at_x1, x1, x2), then apply the
   plane-to-physical scalings (r0/L on shear, L/r0 on thickness); the
   composed pipeline closes on the cone closed forms within float noise.
8. Confirm the deterministic checks: the momentum-integral closure of the
   factor pair and the input-rejection traverse of non-physical inputs,
   with the contract test scripts/test_mangler_axisymmetric_transform.py.

## Worked example

Slender cone at half_angle 5.0 deg in standard air nu = 1.5e-5 m2/s,
rho = 1.225 kg/m3, constant edge velocity u_e = 30.0 m/s, running length
x = 2.0 m, reference length L = 1.0 m. All values below are real outputs
of the module.

- Reynolds number at the station: Re_x = u_e*x/nu = 4.0000000e6,
  sqrt(Re_x) = 2000.0 exactly.
- Geometry: cone surface radius cone_radius(2.0, 5.0) = 1.749773271e-01 m;
  Mangler equivalent 2-D running length mangler_xi(2.0, 5.0, 1.0) =
  2.041137665e-02 m, the 2 m cone surface maps to a 2 cm flat plate;
  transformed normal coordinate at the flat-plate layer top
  transformed_normal_coordinate(2.0, 5.0e-3, 5.0, 1.0) =
  8.748866353e-04 m.
- Power-law bodies at x = 2.0 m: r0 = 0.05*x^0.5 gives
  powerlaw_mangler_xi = 5.00000000e-03 m, the cylinder r0 = 0.1 m gives
  2.00000000e-02 m, and the cone (amplitude tan(5 deg), exponent 1)
  reproduces xi = 2.041137665e-02 m.
- Flat-plate baseline at x = 2.0 m (inputs consumed from the sibling
  boundary-layer-theory Blasius correlations): cf_flat =
  0.664/sqrt(Re_x) = 3.32000000e-04, tau_w,flat = 0.332*rho*u_e^2/
  sqrt(Re_x) = 1.83015000e-01 Pa, delta_flat = 5.0*x/sqrt(Re_x) =
  5.00000000e-03 m, delta*_flat = 1.72080000e-03 m, theta_flat =
  6.64000000e-04 m.
- Cone values at the SAME running length x = 2.0 m: cf_cone =
  cone_skin_friction(3.32e-4) = 5.750408681e-04, ratio to the plate value
  1.732050808 = sqrt(3); tau_w,cone = cone_wall_shear(0.183015) =
  3.169912785e-01 Pa, ratio sqrt(3), equal to the Cf ratio; delta_cone =
  cone_boundary_layer_thickness(5.0e-3) = 2.886751346e-03 m, ratio
  0.5773502692 = 1/sqrt(3); delta*_cone =
  cone_displacement_thickness(1.7208e-3) = 9.935043432e-04 m and
  theta_cone = cone_momentum_thickness(6.64e-4) = 3.833605787e-04 m, both
  at ratio 1/sqrt(3).
- Shape factor on the cone: H_cone = delta*_cone/theta_cone =
  2.591566265, identical to H_flat (the transform scales the layer, it
  does not reshape it). Momentum-integral closure at the worked station:
  the analytic d(theta_cone*r0)/dx equals r0*Cf,cone/2 to float noise
  (ratio 1), the consistency check that the sqrt(3) and 1/sqrt(3) factor
  pair obeys the axisymmetric boundary-layer momentum balance.

Read-off: a 5 deg half-angle cone at 2 m running length in a 30 m/s stream
(Re_x = 4e6) carries a laminar skin friction of 5.75e-4, exactly sqrt(3)
times the 3.32e-4 of the flat plate at the same station, with its boundary
layer squeezed from 5.0 mm to 2.89 mm; the equivalent 2-D flow lives on a
2 cm plate, and it is on that short equivalent plate that the flat-plate
correlations of boundary-layer-theory are evaluated before the mapping
scales the values back to the cone surface. The sqrt(3) family is the
laminar cone signature: thinner layer, higher wall shear. This momentum-
only leaf computes no heat transfer; the wall-shear rise is why a laminar
sharp-cone surface runs hotter than the flat plate at the same Reynolds
number in the heat-transfer analogy, which the high-speed heating leaf
owns.

## Verification

- Confirm cone_radius(2.0, 5.0) returns 1.749773271e-01 m, equal to
  2.0*math.tan(math.radians(5.0)), and mangler_xi(2.0, 5.0, 1.0) returns
  2.041137665e-02 m with the x^3 scaling (the half-length station carries
  one eighth of the xi) and the L^-2 scaling.
- Confirm the power-law family: powerlaw_mangler_xi(2.0,
  math.tan(math.radians(5.0)), 1.0, 1.0) reproduces mangler_xi, the
  cylinder returns 2.0e-02 m and the r0 = 0.05*x^0.5 body returns 5.0e-03
  m.
- Confirm the cone closed forms at the worked station: cone_skin_friction
  (3.32e-4) = 5.750408681e-04 (between 4.0e-4 and 8.0e-4) with ratio
  SQRT3, cone_wall_shear(0.183015) = 3.169912785e-01 Pa with ratio SQRT3
  equal to the Cf ratio, cone_boundary_layer_thickness(5.0e-3) =
  2.886751346e-03 m (between 2.0e-3 and 3.5e-3 m, below the 5.0e-3 m
  plate layer), cone_displacement_thickness(1.7208e-3) = 9.935043432e-04
  m and cone_momentum_thickness(6.64e-4) = 3.833605787e-04 m, each with
  ratio INV_SQRT3.
- Confirm the shape factor H_cone = 2.591566265 equals 1.7208/0.664, the
  Mangler shear and thickness pipelines (the composed plane-to-physical
  and Blasius station-scaled values) close on the closed forms within
  1e-9 relative, and the momentum-integral closure ratio is 1.
- Confirm the consumption helpers: blasius_cf_at_station(3.32e-4, 2.0,
  4.0) = 2.3475945135e-04 (cf at twice the station is cf/sqrt(2)) and the
  round trips over (x1, x2) and back hold within float noise.
- Confirm every non-physical input raises ValueError: x at 0 or negative
  on the geometry functions, half_angle_deg at 0 or 90, y negative on the
  transformed normal coordinate, ref_length at 0 or negative, amplitude 0
  or exponent negative on the power-law body, zero baselines or stations
  on the helpers, and non-positive flat-plate baselines on the cone
  functions.
- Run the contract test offline: python3
  scripts/test_mangler_axisymmetric_transform.py (34 tests,
  deterministic, passes under /usr/bin/python3 and the pyenv 3.13.12
  interpreter).

## Pitfalls

- Reversing the cone factor pair: wall shear and skin friction carry
  sqrt(3) but the thicknesses carry 1/sqrt(3). Putting sqrt(3) on the
  thickness as well breaks the axisymmetric momentum integral
  d(theta*r0)/dx = r0*Cf/2 by a factor of 3; the cone layer is thinner
  and more strongly sheared than the plate layer at the same station.
- Comparing at equal running length versus equal transformed length: the
  sqrt(3) family is the equal-x comparison. At equal xi the equivalent
  2-D layer and the physical layer are identical by construction (ratios
  of 1); the factor appears only when two physical stations at the same x
  are compared.
- Applying the factor family to turbulent cone layers: the sqrt(3) and
  1/sqrt(3) factors are laminar-only closed forms; the turbulent cone
  rule has no exact factor and this leaf does not claim one.
- Feeding a baseline from the wrong station or edge velocity: the cone
  functions multiply whatever flat-plate values are passed in, so the
  baseline must come from the same running length x and the same edge
  velocity u_e; mixing stations silently corrupts the cone values.
- Using the small-angle approximation: the module uses tan(alpha) exactly;
  replacing it with alpha in radians shifts the radius and hence every
  transformed length.
- Taking the mapping for compressible or heat-transfer work: this leaf is
  momentum-only laminar incompressible content. The Eckert
  reference-temperature method, recovery factor and Reynolds-analogy
  heating belong to flat-plate-skin-friction-heating, and stagnation-
  point attachment layers belong to stagnation-flow-boundary-layer.

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: owns the flat-plate
  Blasius and 1/7-power correlations whose values this leaf consumes as
  baseline inputs at the same running length.
- aerodynamics/boundary-layer/stagnation-flow-boundary-layer: the Homann
  axisymmetric attachment-region layer of the nose, a constant-thickness
  similarity layer with no running length, no cone surface and no
  transform content.
- aerodynamics/boundary-layer/boundary-layer-separation and
  aerodynamics/boundary-layer/boundary-layer-transition: the Thwaites
  traverse layer evolution of 2-D flows with varying edge velocity, which
  this leaf leaves to them for general slender bodies.
- aerodynamics/high-speed/flat-plate-skin-friction-heating: the
  compressible plate-station skin friction and Reynolds-analogy heat
  transfer of a 2-D high-Mach stream, the regime fence of this
  incompressible momentum-only geometry mapping.
- aerodynamics/high-speed/hypersonic-flow: the Newtonian cone axial force
  at Mach well above 5, the pressure side of cone flow, not the viscous
  side.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mangler_axisymmetric_transform.py

The 34 tests cover the worked-example anchors with magnitude bounds (cone
radius, Mangler xi with its x^3 and L^-2 scalings, transformed normal
coordinate, power-law bodies), the sqrt(3) cone factor on skin friction
and wall shear with ratio checks, the inverse sqrt(3) factor on the three
cone thicknesses with the thinner-than-plate bound, the shape-factor
preservation, the Mangler shear and thickness pipelines closing on the
closed forms, the Blasius station-scaling helpers with round trips, the
momentum-integral closure (including the failure of the reversed factor
pair), deterministic repeat calls, module stdlib hygiene, and the
input-rejection traverse of non-physical running lengths, angles, normal
distances, reference lengths, power-law amplitudes and exponents, station
helpers and flat-plate baselines.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the cited
  reference for the viscous boundary-layer family (the sibling precedent
  for this pack in standards-map.yaml); the classical transform treatment
  follows Mangler 1948 as presented by Schlichting Boundary-Layer Theory
  (boundary layers on bodies of revolution) and White Viscous Fluid Flow
  (Mangler transformation section), whose material is cited through the
  report. Summary-only methodology per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
