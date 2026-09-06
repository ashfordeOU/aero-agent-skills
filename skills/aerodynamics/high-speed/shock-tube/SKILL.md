---
name: shock-tube
description: "Use when you must determine the four-region state of a shock-tube run from the driver-to-driven diaphragm pressure ratio and driver sound-speed ratio: recover the incident-shock Mach number by deterministic bisection of the implicit diaphragm-match equation, then the post-shock pressure, temperature and density ratios with the region-2 absolute state, the contact-surface velocity shared by shocked driven gas and expanded driver gas with the region-2 and region-3 flow Mach numbers, the driver expansion wave ratios with the region-3 absolute state, and the fan head and tail wave speeds. Produces the incident-shock Mach number, the four-region state table and the contact checks that gate shock-tube facility design, driver-gas selection and gas-dynamics coursework. Trigger: shock tube, shock-tube run, diaphragm pressure ratio, contact surface, driver gas, driven gas, incident shock, driver sound-speed ratio, post-shock state, fan head wave, fan tail wave, four-region state table."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: naca-tr-824
  reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags:
  - shock-tube
  - diaphragm-pressure-ratio
  - incident-shock-mach-number
  - contact-surface-velocity
  version: 0.1.0
  author: AeroSkills
---

# Shock-Tube Wave System (aerodynamics/high-speed/shock-tube)

Use when the task is the classical one-dimensional shock-tube problem:
a high-pressure driver gas (region 4) separated by a diaphragm from a
low-pressure driven gas (region 1), both initially at rest, with the
diaphragm burst releasing an incident shock into the driven gas, a
contact surface between the two gases, and a centered expansion wave
running back into the driver gas. This leaf recovers the incident-shock
Mach number from the diaphragm pressure state alone, then resolves the
four-region state. It pairs with normal-shock for the stationary-shock
ratio context at a given upstream Mach number and with prandtl-meyer
for the steady turning-fan context; the moving-shock, contact-surface
and unsteady-wave content here has no other home in the high-speed
pack. Pure stdlib, deterministic, offline.

## Domain quick reference

- Incident shock into gas at rest at shock Mach Ms: p2/p1 = 1 + 2
  gamma1 (Ms^2 - 1) / (gamma1 + 1), rho2/rho1 = (gamma1 + 1) Ms^2 /
  (2 + (gamma1 - 1) Ms^2), T2/T1 = (p2/p1) / (rho2/rho1); the shock
  speed is Ws = Ms a1 with a1 = sqrt(gamma1 R t1).
- Induced flow behind the shock (contact-surface velocity): u2 =
  2 a1 (Ms - 1/Ms) / (gamma1 + 1). The shock-frame downstream Mach
  number Mn2 = sqrt((1 + (gamma1 - 1) Ms^2 / 2) / (gamma1 Ms^2 -
  (gamma1 - 1) / 2)) stays below one; u2 = Ms a1 - Mn2 a2 links the
  frames.
- Unsteady centered expansion into the driver gas: p3/p4 = (1 -
  (gamma4 - 1) u3 / (2 a4)) ** (2 gamma4 / (gamma4 - 1)), T3/T4 =
  (1 - (gamma4 - 1) u3 / (2 a4))^2, rho3/rho4 = (p3/p4) / (T3/T4).
- Implicit shock-tube equation (the diaphragm match p2 = p3): the
  normal-shock ratio p2/p1 at Ms equals p4/p1 times the expansion
  ratio at the shared contact velocity, with u2/a4 = 2 (Ms - 1/Ms) /
  ((gamma1 + 1) a4/a1). The residual is strictly increasing in Ms, so
  the root is unique.
- Expansion bracket ceiling: the driver expansion stays physical only
  while (Ms - 1/Ms) < C = (gamma1 + 1) (a4/a1) / (gamma4 - 1), which
  caps Ms at Ms_lim = (C + sqrt(C^2 + 4)) / 2 (6.162277660 for
  air/air at a4/a1 = 1).
- Both fan boundaries are Mach waves: the head runs leftward at speed
  a4 into the quiescent driver gas and the tail runs at u3 - a3 in
  the lab frame, right-positive.
- Absolute driver state: same specific gas constant R for both gases
  (documented assumption), so T4 = t1 (a4/a1)^2 gamma1 / gamma4.
- Module constants: GAMMA_AIR = 1.4, R_AIR = 287.0 J/(kg K),
  BISECT_TOL = 1e-12, MAX_ITER = 200. Units are SI (Pa, K, kg/m3,
  m/s); ratios are unitless.
- NACA-TR-824 frames the compressible-flow relations; the equations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the diaphragm state: driver-to-driven pressure ratio p4_p1,
   driver sound-speed ratio a4_a1, specific heat ratios gamma1 and
   gamma4, and the driven-gas absolute state p1, t1, r_gas;
   shock_tube_state validates every input and rejects non-physical
   values with ValueError.
2. Recover the incident-shock Mach number Ms with incident_shock_mach,
   the deterministic bisection of the shock_tube_residual
   diaphragm-match equation on the bracket below the ceiling Ms_lim.
3. Build the post-shock driven-gas state: normal_shock_ratios at Ms
   returns p2_p1, rho2_rho1, T2_T1, and multiplying by the region-1
   absolute state gives p2, T2, rho2, a2 and the shock speed Ws =
   Ms a1.
4. Compute the contact-surface velocity u2 = u3 with
   induced_velocity from Ms and a1, then the region-2 lab-frame flow
   Mach number M2_lab = u2 / a2 (just subsonic for a moderate run).
5. Expand the driver gas: expansion_pressure_ratio at u3 / a4 gives
   p3_p4, T3_T4 = bracket squared, rho3_rho4, and the region-3
   absolute state with a3 and M3_lab = u3 / a3 (supersonic in the lab
   frame for a moderate run).
6. Read the fan wave speeds from shock_tube_state: fan_head_speed = a4
   into the quiescent driver gas and fan_tail_speed = u3 - a3, and
   assemble the full four-region state table.
7. Close the contact: check the residual at Ms, p3 - p2 and u3 - u2,
   plus the closed-form identities (ideal gas p = rho R T, the
   shock-frame Mn2 recovery of u2, and p3_p4 times p4_p1 equals
   p2_p1).
8. Confirm determinism (bit-identical reruns) and ValueError rejection
   of every non-physical input: p4_p1 <= 1, a4_a1 <= 0, gamma <= 1,
   p1/t1/r_gas <= 0, and expansion velocities at or beyond the
   full-expansion limit.
9. Run the contract test offline: python3
   scripts/test_shock_tube.py.

## Worked example

Air driver and driven gas, gamma1 = gamma4 = 1.4, R = 287.0, a4/a1 = 1
(T4 = T1), p1 = 101325 Pa, T1 = 288.15 K, p4/p1 = 40:

- Ms = 2.057576505, shock speed Ws = Ms a1 = 700.1164 m/s; sound
  speeds a1 = a4 = 340.2626 m/s.
- Post-shock ratios: p2/p1 = 4.772557918, T2/T1 = 1.734842373,
  rho2/rho1 = 2.751003776. Region 2: p2 = 483579.43 Pa, T2 = 499.89
  K, rho2 = 3.370600480 kg/m3, a2 = 448.1716 m/s.
- Contact velocity: u2 = u3 = 445.6215 m/s, identical to the closed
  form 2 a1 (Ms - 1/Ms) / (gamma1 + 1); M2_lab = 0.994310161 with
  Mn2 = 0.567851523; M3_lab = 1.774406595 (shocked driven stream just
  subsonic, expanded driver stream supersonic, meeting at the contact
  surface).
- Driver expansion ratios: p3/p4 = 0.119313948, T3/T4 = 0.544750315,
  rho3/rho4 = 0.219025019. Region 3: p3 = 483579.43 Pa (p3 - p2 =
  -6.04e-8 Pa at the bisected root), T3 = 156.97 K, rho3 =
  10.734203118 kg/m3, a3 = 251.1383 m/s.
- Fan boundaries: head speed 340.2626 m/s leftward into the quiescent
  driver gas (a Mach wave, M_head = 1.0 relative to region 4); tail
  speed u3 - a3 = 194.4832 m/s rightward in the lab frame. Region 4:
  p4 = 4053000.00 Pa, T4 = 288.15 K, rho4 = 49.009027310 kg/m3.
- Four-region state table (p Pa, T K, rho kg/m3, u m/s): region 1:
  101325.00, 288.15, 1.225225683, u = 0; region 2: 483579.43, 499.89,
  3.370600480, u = 445.6215, M = 0.994310161; region 3: 483579.43,
  156.97, 10.734203118, u = 445.6215, M = 1.774406595; region 4:
  4053000.00, 288.15, 49.009027310, u = 0.
- Contact checks from the state dict: p3 - p2 = -6.041955e-08 Pa,
  u3 - u2 = 0.000000e+00 m/s, pressure-match residual at Ms =
  5.959677e-13.
- Driver-strength family (air/air, a4/a1 = 1): p4/p1 = 1.2 gives
  Ms = 1.039831292, u2 = 22.1559 m/s, T2 = 295.71 K; 2.0 gives
  1.159478862, 84.2214 m/s, 317.70 K; 5.0 gives 1.402408030,
  195.4664 m/s, 361.99 K; 10.0 gives 1.607525211, 279.4268 m/s,
  401.44 K; 100.0 gives 2.371054059, 552.7285 m/s, 580.01 K; 1000.0
  gives 3.150486214, 803.3246 m/s, 824.23 K. Ms and u2 grow
  monotonically with the driver overpressure, always below the
  air/air ceiling Ms_lim = 6.162277660.
- General-gamma case, helium driver (gamma4 = 5/3) at p4/p1 = 40,
  a4/a1 = 2.4 over air: Ms = 2.698174185, p2/p1 = 8.326834585, T2/T1
  = 2.340950220, u2 = 659.9828 m/s, p3/p4 = 0.208170865, T3 = 744.20
  K. The light fast driver nearly doubles the contact velocity of the
  air/air case at the same pressure ratio.

## Verification

- Confirm incident_shock_mach(40.0, 1.0) returns Ms 2.057576505 with
  the residual shock_tube_residual at that root below 1e-10, and that
  the driver-strength and helium-driver anchors above all reproduce
  within the tolerances listed in the contract test.
- Confirm the contact-surface match at the root: p3 - p2 below 1e-6
  Pa and u3 - u2 exactly 0.0 in the state dict, with p3_p4 * p4_p1
  equal to p2_p1 within 1e-9.
- Confirm the identities: p2 / (rho2 R T2) = 1.0 (ideal gas), u2
  recovered from 2 a1 (Ms - 1/Ms) / (gamma1 + 1) and from the
  shock-frame Ms a1 - Mn2 a2, and p2_p1 from the closed form.
- Confirm ValueError rejection of non-physical inputs: p4_p1 <= 1, a4
  /a1 <= 0, gamma <= 1, p1/t1/r_gas <= 0, shock_mach <= 1, and
  expansion velocities at or beyond 2 / (gamma4 - 1).
- Confirm determinism: rerunning incident_shock_mach on the same input
  returns identical bits; no RNG, pure stdlib math only.
- Run the contract test offline: python3
  scripts/test_shock_tube.py (31 tests, deterministic).

## Related leaves

- aerodynamics/high-speed/normal-shock: stationary-shock ratios given
  the upstream Mach number only; it never determines the shock Mach
  number from a diaphragm pressure state and has no driver gas or
  moving-shock content.
- aerodynamics/high-speed/oblique-shock: steady single-turn waves with
  the theta-beta-M solve; its implicit-solve precedent is the pattern
  this leaf follows for the diaphragm-match bisection.
- aerodynamics/high-speed/prandtl-meyer: steady turning fans; the
  unsteady driver expansion wave here is the moving counterpart.
- aerodynamics/high-speed/isentropic-flow-relations: steady area-Mach
  and choked-flow inversions, no unsteady diaphragm wave motion.
- aerodynamics/high-speed/regular-shock-reflection: wall interactions
  after the incident shock reflects, beyond this leaf's single-transit
  scope.

## Pitfalls

- Solving the stationary-shock problem instead of the shock-tube
  problem: this leaf's post-shock ratios are evaluated at the
  incident-shock Mach number recovered from the diaphragm pressure
  state, not at a Mach number you supply; feed a given upstream Mach
  number to normal-shock instead.
- Forgetting the driver gas: the expansion side depends on gamma4 and
  a4/a1, so an air/air answer is wrong for a helium driver at the
  same p4/p1; the worked example shows u2 rising from 445.62 to
  659.98 m/s when the light fast driver replaces air.
- Treating region-2 flow as always subsonic in the lab frame: M2_lab
  = u2/a2 approaches one at p4/p1 = 40 and exceeds it for stronger
  runs; the invariant is the shock-frame Mn2 below one, checked via
  u2 = Ms a1 - Mn2 a2.
- Reading the fan head as the fastest wave in the lab frame: the head
  (speed a4 leftward) and tail (u3 - a3 rightward) are both Mach
  waves relative to the gas they move through; a strong driver sweeps
  the tail downstream, so the two boundaries travel in opposite
  directions in the lab frame.
- Extrapolating past the full-expansion limit: (Ms - 1/Ms) must stay
  below C = (gamma1 + 1) (a4/a1) / (gamma4 - 1); beyond it the
  driver expansion is unphysical and the solver raises ValueError.
- Modeling wall reflections: the classical single-transit solution
  stops at the first arrival of the incident shock and expansion wave
  at the end walls; regular-shock-reflection covers the interactions
  that follow.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_shock_tube.py

The 31 tests cover the air/air worked example at p4/p1 = 40 (Ms,
post-shock ratios and region-2 absolute state, contact-surface
velocity, driver expansion ratios and region-3 absolute state, fan
head and tail speeds, four-region state table keys), the contact
close-out identities (residual below 1e-10, p3 - p2 below 1e-6 Pa,
u3 - u2 exactly 0, p3_p4 * p4_p1 equal to p2_p1, ideal gas, shock-
frame Mn2 recovery), the driver-strength family anchors from p4/p1 =
1.2 to 1000 with monotonic Ms and u2 below the Ms_lim ceiling, the
helium-driver general-gamma case, ValueError rejection of every
non-physical input, and bit-identical determinism reruns. All numeric
asserts are order-safe (assertAlmostEqual with delta or math.isclose).

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames the
  normal-shock and compressible-flow relations; only names and summary
  equations appear above, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
