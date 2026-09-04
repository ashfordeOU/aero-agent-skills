---
name: rotorcraft-axial-descent-flow-states
description: "Use when you must classify the axial flow state of a rotor in vertical descent: hover at zero rate, the vortex-ring band from zero to twice the hover induced velocity, and the windmill-brake momentum state at and above that boundary. Computes the band limits, the windmill-brake induced velocity from the momentum-theory closed form, the signed rotor power and torque in descent (negative when the rotor absorbs power from the airstream), and the torque-reversal condition c = P_profile over k T versus v_h that decides whether the zero-shaft-power autorotative equilibrium is reachable on the momentum branch. Produces the flow-state verdict, the descent induced velocity, signed power and torque, and the momentum reachability verdict. Trigger: vortex-ring state, windmill-brake state, axial descent, descent induced velocity, torque reversal, rotor descent power."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [rotorcraft-axial-descent-flow-states, axial-descent-flow, vortex-ring-state, windmill-brake-state, descent-induced-velocity, torque-reversal, momentum-theory-reachability]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Axial Descent Flow States (flight-mechanics/performance/rotorcraft-axial-descent-flow-states)

Use when you must categorize the axial flow state of a helicopter
rotor in vertical descent from the descent-rate ratio w = Vd / v_h and
evaluate the windmill-brake state with momentum theory: the
vortex-ring / turbulent-wake band 0 < w < 2 versus the windmill-brake
state w >= 2, the band induced velocity from the momentum closed form,
the signed rotor power and torque in descent, and whether momentum
theory can close to the zero-shaft-power autorotative equilibrium. It
pairs with flight-mechanics/performance/rotorcraft-hover-performance
(the hover state at zero rate) and with
flight-mechanics/performance/rotorcraft-vertical-climb-performance (the
climb-only momentum leaf). It implements the windmill-brake momentum
model in pure Python, stdlib only, and never computes empirical inflow:
inside the vortex-ring band the flow is momentum-invalid and the
induced velocity is left None.

Scope: this leaf owns the windmill-brake momentum-theory branch and
the vortex-ring band boundary. Power-off descent estimation is owned by
the empirical leaf
flight-mechanics/performance/rotorcraft-autorotative-descent (which
explicitly excludes momentum theory in descent, the vortex-ring state
and vertical zero-airspeed descent); induced velocity at hover and in
climb belongs to the hover and vertical-climb leaves; inflow in level
flight belongs to the forward-flight leaf. Momentum theory is applied
only where it is valid, Vd >= 2 v_h.

## Domain quick reference

All quantities are SI (m/s, N, W, N m). Module constants are
RHO_SL = 1.225 kg/m^3, G = 9.80665 m/s^2, K_INDUCED_DEFAULT = 1.15,
PI = math.pi.

- Hover induced velocity from thrust and disk area:
  v_h = sqrt(T / (2 rho A)), A = PI R^2. The reference rotor
  (R = 5.0 m, m = 2200 kg, T = m G) gives v_h = 10.5887 m/s.
- Flow-state bands: Vd = 0 is hover, 0 < Vd < 2 v_h is the
  vortex-ring / turbulent-wake band (momentum invalid, empirical
  inflow, NASA TP-2005-213477 public-domain context), Vd >= 2 v_h is
  the windmill-brake state where momentum theory applies.
- Band limits: vortex_ring_band_limits(v_h) returns (0, 2 v_h); the
  worked rotor gives (0, 21.18) m/s.
- Windmill-brake induced velocity (physical branch):
  v_i = Vd/2 - sqrt((Vd/2)^2 - v_h^2), valid only for Vd >= 2 v_h.
  The boundary identity v_i(2 v_h) = v_h holds exactly, v_i never
  exceeds v_h, and v_i falls like v_h^2 / Vd as Vd grows (at
  Vd = 5 v_h, v_i / v_h = 0.2087, near the 1 / w asymptote).
- Signed descent power: P = k T (-Vd + v_i) + P_profile. Negative P
  means the rotor absorbs power from the airstream (windmill-brake
  working state); positive P means the shaft drives the rotor.
- Signed torque: Q = P / Omega. Negative torque opposes the engine
  drive while the rotor absorbs power.
- Torque-reversal condition: c = P_profile / (k T) versus v_h. The
  zero-power condition P = 0 combined with the momentum quadratic
  v_i^2 - Vd v_i + v_h^2 = 0 gives the formal crossing at
  Vd = c + v_h^2 / c with v_i = v_h^2 / c. That root is physical only
  when v_i <= v_h, i.e. c >= v_h (then Vd >= 2 v_h by AM-GM). When
  c < v_h no momentum root exists and the equilibrium is
  momentum-unreachable.

## Workflow

1. Fix the operating point: descent rate Vd (m/s, positive downward),
   thrust T (N) and disk area A = PI R^2 (or the mass, radius, density
   that imply them). The sibling vertical-climb leaf owns climb, so
   Vd < 0 raises ValueError here.
2. Get the hover induced velocity from the thrust, density and area:
   v_h = sqrt(T / (2 rho A)); call axial_flow_state(Vd, v_h) for the
   verdict "hover", "vortex-ring-band" or "windmill-brake", and
   vortex_ring_band_limits(v_h) for the band in m/s.
3. In the windmill-brake state only, get the induced velocity with
   windmill_brake_induced_velocity(Vd, v_h); the function refuses Vd
   below 2 v_h because momentum theory does not apply in the band.
4. Compute the signed power with rotor_descent_power(T, Vd, v_i,
   P_profile, k) and, with the rotor speed Omega, the signed torque
   with rotor_descent_torque(P, Omega).
5. Decide zero-shaft-power reachability with
   torque_reversal_condition(P_profile, T, k, v_h): c >= v_h reports
   the momentum root Vd = c + v_h^2 / c on the windmill-brake branch;
   c < v_h returns momentum_root_Vd None with the
   momentum-unreachable verdict (the equilibrium lies in the empirical
   vortex-ring / turbulent-wake regime).
6. Bundle everything with descent_summary(T, R, P_profile, Vd, rho, k,
   rotor_speed_rad_s): it returns flow_state, v_h, band_limits,
   induced_velocity, power_W, torque_Nm and momentum_root_reachable,
   with the momentum fields None in the band and at hover.
7. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_axial_descent_flow_states.py.

## Worked example

Reference rotor (shared with the hover and blade-element siblings):
R = 5.0 m, m = 2200 kg (T = m G = 21574.63 N), rho = 1.225 kg/m^3,
A = PI R^2 = 78.540 m^2, P_profile = 122935 W, k = 1.15. Real module
outputs:

- v_h = 10.5887 m/s, vortex_ring_band_limits -> (0, 21.177) m/s.
- At Vd = 2 v_h (21.177 m/s): windmill_brake_induced_velocity returns
  v_i = 10.5887 m/s, the boundary identity with diff 0.0; the signed
  power is -139780.0 W (the rotor absorbs power from the airstream).
- At Vd = 25 m/s: v_i = 5.8570 m/s (0.553 v_h), P = -352017.6 W
  (spec magnitude about -352019 W).
- At Vd = 30 m/s: v_i = 4.3756 m/s (0.413 v_h), P = -512828.7 W
  (about -512829 W); with Omega = Vtip / R = 220 / 5 = 44 rad/s,
  Q = P / Omega = -11655.2 N m (about -11655 N m), torque opposing the
  engine drive.
- At Vd = 40 m/s: P = -794246.6 W (about -794247 W); P stays negative
  across the whole windmill-brake band for this rotor.
- torque_reversal_condition: c = P_profile / (k T) = 4.9549 m/s
  (about 4.955), c < v_h (4.955 < 10.589), verdict
  momentum-unreachable, momentum_root_Vd None. The formal crossing
  would sit at Vd = c + v_h^2 / c = 27.58 m/s only on the
  non-physical branch: it demands v_i = v_h^2 / c = 22.63 m/s, above
  v_h, impossible on the windmill-brake branch, so 27.6 m/s is never a
  momentum root of this rotor.

## Verification

- Confirm axial_flow_state boundaries: Vd = 0 -> "hover", Vd just
  below 2 v_h -> "vortex-ring-band", Vd = 2 v_h and above ->
  "windmill-brake".
- Confirm windmill_brake_induced_velocity(2 v_h, v_h) equals v_h to
  1e-9, and that v_i satisfies the momentum quadratic identity
  v_i (Vd - v_i) = v_h^2 exactly on the physical branch.
- Confirm the worked powers -139780.0, -352017.6, -512828.7 and
  -794246.6 W and the torque -11655.2 N m at Omega = 44 rad/s, all
  within the spec magnitude bounds, and that P is negative across the
  windmill-brake band.
- Confirm the torque-reversal split: c >= v_h reports the momentum
  root Vd = c + v_h^2 / c (>= 2 v_h) as reachable; the worked rotor
  with c = 4.955 < v_h reports momentum-unreachable with no root, and
  the required v_i = v_h^2 / c = 22.63 m/s exceeding v_h is the reason
  the formal 27.58 m/s crossing is non-physical.
- Confirm ValueError on Vd < 0 (climb), v_h <= 0, a windmill-brake
  call below 2 v_h, non-positive thrust, non-positive k, negative
  profile power or induced velocity, and Omega <= 0.
- Confirm the descent_summary dict contains exactly the seven
  documented keys with momentum fields None in the band and at hover.
- Confirm determinism: identical inputs give identical floats run to
  run (no RNG).
- Run the contract test offline: python3
  scripts/test_rotorcraft_axial_descent_flow_states.py (34 tests,
  deterministic).

## Pitfalls

- Evaluating momentum theory inside the vortex-ring band:
  windmill_brake_induced_velocity refuses Vd below 2*v_h with ValueError
  because momentum theory is invalid there, and the band induced velocity is
  None; do not fill the band with the closed form.
- Signing Vd wrong: descent rate is positive downward in this leaf and a
  negative Vd (climb) raises ValueError - vertical climb is owned by the
  sibling climb leaf.
- Reading the signed power without its sign: negative P means the rotor
  absorbs power from the airstream (windmill-brake working state) and the
  torque opposes the engine drive; flipping the sign for a 'magnitude'
  erases the physical verdict.
- Reporting the formal torque-reversal root as reachable: when c < v_h the
  momentum root Vd = c + v_h^2/c would demand v_i = v_h^2/c above v_h and is
  non-physical; the function returns momentum_root_Vd None with the
  momentum-unreachable verdict, as in the worked rotor (c = 4.955 < v_h =
  10.589).
- Reading descent_summary momentum fields at hover or in the band: the
  induced velocity, power and torque momentum fields are None outside the
  windmill-brake state by contract.
- Non-positive thrust, k, or rotor speed and negative profile power raise
  ValueError; determinism is pinned (no RNG).

## Related leaves

- flight-mechanics/performance/rotorcraft-autorotative-descent: the
  empirical power-off descent sibling; this leaf's torque-reversal
  verdict explains why momentum theory cannot close to the autorotative
  equilibrium.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  the climb-only momentum leaf (Vc < 0 raises ValueError there).
- flight-mechanics/performance/rotorcraft-hover-performance: the hover
  state at zero descent rate and its induced power terms.
- flight-mechanics/performance/rotorcraft-blade-element-hover-performance:
  the coefficient-polar blade-element model sharing the reference
  rotor.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_axial_descent_flow_states.py

The test covers the reference-rotor worked example (v_h 10.5887 m/s,
band (0, 21.18) m/s, v_i(2 v_h) = v_h identity, powers about -139780 /
-352019 / -512829 / -794247 W, torque about -11655 N m at Omega 44),
the flow-state boundaries at 0, just below, at and above 2 v_h, the
momentum quadratic identity v_i (Vd - v_i) = v_h^2, the 1 / w
asymptote at 5 v_h, the torque-reversal split (c >= v_h reachable with
root at c + v_h^2 / c, c < v_h momentum-unreachable), the exact
descent_summary keys with momentum fields None in the band, the pinned
module constants, determinism run to run, and ValueError rejection of
climb rates, non-positive v_h, windmill calls below 2 v_h,
non-positive thrust, k, profile power and Omega.

## Compliance

- Standards referenced, not reproduced: FAR-29 is named reference-only
  per standards-map.yaml. NASA TP-2005-213477 (public domain) is named
  in the body as the empirical-inflow context that marks the
  vortex-ring band momentum-invalid; the momentum relations above are
  summary-only standard engineering methodology.
- compliance: STANDARDS-REF, gated: false.
