---
name: hypersonic-flow
description: "Use when you must estimate aerodynamic forces on a body in hypersonic flow with modified Newtonian impact theory: stagnation pressure behind the normal shock (Rayleigh pitot relation), the finite-Mach stagnation pressure coefficient, local pressure by the Newtonian sine-squared law, the hypersonic vacuum limit on shadowed surfaces, and integrals over a sphere, cone and flat plate giving sphere drag, cone axial force, and flat plate lift, drag and lift-to-drag ratio. Produces the stagnation Cp and body force coefficients. Trigger: hypersonic flow, modified Newtonian theory, Newtonian impact pressure, stagnation pressure coefficient, blunt body drag, sphere drag coefficient, cone axial force, hypersonic vacuum limit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [hypersonic-flow, modified-newtonian-theory, newtonian-impact-pressure, stagnation-pressure-coefficient, blunt-body-drag, sphere-drag-coefficient, cone-axial-force, hypersonic-vacuum-limit]
  version: 0.1.0
  author: AeroSkills
---

# Hypersonic Flow Forces (aerodynamics/high-speed/hypersonic-flow)

Use when the task is estimating the aerodynamic forces on a body in
hypersonic continuum flow with the classical modified Newtonian impact
theory: the flow is fast enough (Mach well above 5) that the bow shock
sits close to the body, so the surface pressure is set by the impact of
freestream particles rather than by isentropic turning. The leaf
computes the stagnation pressure behind the normal shock with the
Rayleigh pitot relation, the finite-Mach stagnation pressure
coefficient, the local pressure coefficient of a windward surface from
its inclination (sine-squared law), the vacuum limit on shadowed
surfaces, and the integrated force coefficients of a sphere, a sharp
cone at zero incidence and an inclined flat plate. It pairs with
aerodynamics/high-speed/normal-shock, the pitot-relation neighbor for
the shock itself, and with the supersonic high-speed leaves, which own
the regime below Mach ~ 5 where Newtonian methods hand over to
shock-expansion and oblique-shock estimates. The method is the
classical engineering estimate for hypersonic continuum flow, not a CFD
replacement. Pure Python, stdlib only.

## Domain quick reference

- Rayleigh pitot relation: p02/p1 = ((gamma+1)^2 * M^2 / (4*gamma*M^2
  - 2*(gamma-1)))^(gamma/(gamma-1)) * (2*gamma*M^2 - gamma + 1) /
  (gamma+1). Stagnation pressure behind the normal shock over upstream
  static pressure at freestream Mach M, gamma = 1.4 by default.
- Stagnation pressure coefficient: Cp_max(M) = 2/(gamma*M^2) *
  (p02/p1 - 1). This is the finite-Mach modified Newtonian limit; as M
  grows it approaches 1.839 from below for gamma = 1.4 (the modified
  Newtonian limit quoted for blunt-body estimates).
- Newtonian sine-squared impact law: Cp = Cp_max * sin(theta)^2 for a
  surface inclined theta (0 to 90 degrees) to the freestream. A
  surface normal to the flow sees the full stagnation Cp.
- Hypersonic vacuum limit: Cp_vacuum = -2/(gamma*M^2), the most
  negative coefficient a shadowed surface can carry as its pressure
  tends to zero.
- Sphere drag coefficient: Cd = Cp_max / 2, the modified Newtonian
  pressure integral over the windward hemisphere with frontal-area
  reference. The classic blunt-body drag estimate.
- Cone axial-force coefficient: CA = Cp_max * sin(half_angle)^2 for a
  sharp cone at zero incidence, base-area reference. The conical
  surface pressure projected on the base gives the axial force.
- Flat plate, unit planform area: windward Cp = Cp_max * sin(alpha)^2,
  leeward Cp = 0 (Newtonian shadow); normal-force CN = Cp_windward -
  Cp_leeward, then CL = CN*cos(alpha) and CD = CN*sin(alpha). The
  lift-to-drag ratio CL/CD equals cot(alpha) and is reported as None at
  zero incidence where the division is undefined.
- All inputs unitless (Mach, angles in degrees, gamma); gamma defaults
  to 1.4. SI units never appear because every output is a
  coefficient.
- NACA TR-824 frames the classic compressible-flow data context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the flight state: freestream Mach M (must exceed 1) and the
   specific heat ratio gamma (1.4 default).
2. Get the shock-side anchor with rayleigh_pitot_ratio(M, gamma) and
   the stagnation coefficient with cp_stagnation(M, gamma); check the
   M -> infinity limit 1.839 to confirm the finite-Mach value.
3. For a local surface at inclination theta, evaluate
   newtonian_cp(theta_deg, M, gamma); for a shadowed surface take
   cp_vacuum(M, gamma) as the most negative bound or 0.0 in the
   Newtonian-shadow convention used on the flat plate.
4. For a blunt body, sphere_drag_coefficient(M, gamma) gives the
   drag coefficient from the hemisphere pressure integral.
5. For a sharp cone at zero incidence,
   cone_axial_force_coefficient(half_angle_deg, M, gamma) gives the
   axial-force coefficient on the base-area reference.
6. For an inclined flat plate, flat_plate_coefficients(alpha_deg, M,
   gamma) returns the windward and leeward Cp, CN, CL, CD and the
   lift-to-drag ratio.
7. For a complete estimate, analyze_body(body_type, params, M, gamma)
   dispatches to the sphere, cone or flat-plate model and returns the
   body coefficient set plus the stagnation Cp and the pitot ratio
   that drive it.
8. Confirm the deterministic checks with the contract test
   scripts/test_hypersonic_flow.py.

## Worked example

Freestream Mach 8, gamma 1.4, the classic modified Newtonian anchors:

- Rayleigh pitot: rayleigh_pitot_ratio(8.0) = 82.87 (p02/p1 behind the
  normal shock; the spec walk-through base 368.64/357.6 = 1.03087,
  raised to 3.5 gives 1.1124, times 74.5).
- Stagnation coefficient: cp_stagnation(8.0) = 2/(1.4*64) * (82.87 -
  1) = 1.8275, approaching the gamma-1.4 limit 1.839 from below.
- Sphere drag: sphere_drag_coefficient(8.0) = 1.8275/2 = 0.9137. At
   M 5 the same estimate gives cp_stagnation(5.0) = 1.8086 and Cd =
  0.9043.
- Cone at 20 degrees: sin(20 deg) = 0.34202, squared 0.11698; CA =
  1.8275 * 0.11698 = 0.2138 (cone_axial_force_coefficient(20.0, 8.0)).
- Flat plate at 10 degrees: cp_windward = 1.8275 * sin(10 deg)^2 =
  0.05511; CN = 0.05511, CL = 0.05511 * cos(10 deg) = 0.05427,
  CD = 0.05511 * sin(10 deg) = 0.009570, LD = 5.671.
- Vacuum limit: cp_vacuum(8.0) = -2/(1.4*64) = -0.02232.
- Pitot anchors across the regime: 5.640 at M 2, 32.65 at M 5; both
  are the standard Rayleigh pitot values quoted for pitot-static
  probes in supersonic and hypersonic test work.

## Verification

- Confirm rayleigh_pitot_ratio(2.0) = 5.640, (5.0) = 32.65 and (8.0) =
  82.87 within the tolerances in the contract test.
- Confirm cp_stagnation(8.0) = 1.8275 and that cp_stagnation(40.0)
  still sits below 1.839, with the coefficient rising monotonically
  toward the limit.
- Confirm sphere_drag_coefficient(8.0) = 0.9137 and the identity
  Cd = Cp_max/2 at every Mach.
- Confirm cone_axial_force_coefficient(20.0, 8.0) = 0.2138 and the
  sine-squared scaling with the half angle.
- Confirm flat_plate_coefficients(10.0, 8.0) returns cl = 0.05427,
  cd = 0.009570 and ld_ratio = 5.671, that ld_ratio equals cot(alpha)
  at every angle, and that zero incidence returns all-zero forces with
  ld_ratio None.
- Confirm every non-supersonic Mach (M = 1.0, M = 0.8), gamma at or
  below 1, theta outside [0, 90], alpha outside [0, 45], and cone
  half-angles outside (0, 90) raise ValueError, in the leaf functions
  and through analyze_body dispatch.
- Run the contract test offline: python3
  scripts/test_hypersonic_flow.py (35 tests, deterministic).

## Related leaves

- aerodynamics/high-speed/normal-shock: the shock-relations neighbor
  behind the Rayleigh pitot formula used here.
- aerodynamics/high-speed/oblique-shock and prandtl-meyer: the
  supersonic turning methods that hand over to Newtonian estimates as
  Mach passes ~ 5.
- aerodynamics/high-speed/shock-expansion-airfoil: supersonic airfoil
  patches, the neighboring claim below the hypersonic regime.
- aerodynamics/high-speed/swept-wing-aerodynamics, transonic-similarity
  and supercritical-airfoil: transonic and swept effects that sit
  outside the hypersonic blunt-body claim.
- aerodynamics/high-speed/wave-drag-area-rule: slender-body wave drag,
  the low-Mach complement to the blunt-body estimate here.

## Pitfalls

- Applying modified Newtonian theory below the hypersonic regime: the
  sine-squared impact law is a continuum hypersonic estimate (Mach well
  above 5); the module rejects M at or below 1 with ValueError, and for
  M below ~5 the supersonic shock-expansion and oblique-shock leaves
  own the estimate.
- Reading the stagnation coefficient above 1.839: cp_stagnation
  approaches the gamma-1.4 limit 1.839 monotonically from below at
  finite Mach, so a value above the limit signals an input error, not a
  stronger shock.
- Dividing by zero at zero incidence: the flat-plate lift-to-drag ratio
  is undefined at alpha = 0 and is returned as None with all-zero
  forces — handle the None rather than forcing a ratio.
- Mixing the shadow conventions: the flat plate uses the Newtonian
  shadow Cp = 0 on the leeward side while cp_vacuum gives the most
  negative bound a shadowed surface can carry; pick one convention for
  the analysis and do not subtract the vacuum value from a
  Newtonian-shadow plate.
- Trusting impact theory where the flow is rarefied or detached far from
  the body: Newtonian pressure integrals assume the shock hugs the
  surface, so they are an engineering estimate for blunt hypersonic
  bodies, not a CFD replacement and not valid at low density.
- Forgetting the angle bounds: theta must lie in [0, 90], alpha in [0,
  45] and cone half-angles in (0, 90); every out-of-range angle raises
  ValueError, including through analyze_body dispatch.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hypersonic_flow.py

The test covers the Rayleigh pitot ratio at M 2, 5 and 8 with the
spec anchors (5.640, 32.65, 82.87), the M 1.2 weak-shock bound above
1.89 and monotonic growth in Mach, the stagnation pressure coefficient
at M 5 and 8 and its approach to the 1.839 limit from below, the
sphere drag coefficient at M 5 and 8 with the half-Cp_max identity,
cone axial force at 20 and 40 degrees with sine-squared scaling,
flat-plate coefficients at 0, 10 and 30 degrees with the cot(alpha)
lift-to-drag identity, the vacuum limit, analyze_body dispatch for all
three body types, and ValueError rejection of non-supersonic Mach,
gamma at or below 1 and out-of-range angles.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named as the
  classic compressible-flow data source; the modified Newtonian
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
