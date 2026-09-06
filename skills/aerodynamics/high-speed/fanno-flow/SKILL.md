---
name: fanno-flow
description: "Use when you must solve the Fanno flow of a steady adiabatic constant-area duct with wall friction: evaluate the fanno-line integral fL*/D that chokes the duct from a Mach number, compute the friction-duct-choking length from the inlet Mach, recover the downstream Mach number for a given friction parameter fL/D on the subsonic or the supersonic branch, find the friction required to choke a duct of given length, and report the total-pressure loss ratio p0/p0* and the static pressure, temperature and density ratios to the sonic state along the duct. Produces the fL*/D values, choke lengths, downstream Mach numbers, friction to choke and the loss ratios that gate duct sizing and gas-dynamics coursework. Trigger: fanno flow, fanno line, friction duct, choking length, adiabatic duct friction, fL*/D."
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
  tags: [fanno-flow, fanno-line, friction-duct-choking, fld-star, fanno-choking-length]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fanno Flow in a Constant-Area Adiabatic Duct (aerodynamics/high-speed/fanno-flow)

Use when the task is the Fanno flow of a steady adiabatic perfect-gas
flow in a constant-area duct with wall friction: the Fanno-line integral
fL*/D, the friction-duct choking length, the downstream Mach number
recovered on the inlet branch for a given friction parameter, the
friction required to choke a duct of given length and diameter, and the
total-pressure and static ratios along the duct to its sonic reference
state. This leaf implements the standard Fanno relations (the same
compressible-flow framework that NACA TR-824 tabulates) in pure Python,
stdlib only, with a deterministic 1-D bisection for the branch
inversion. It pairs with aerodynamics/high-speed/isentropic-flow-relations
as the frictionless complement (that leaf's area-Mach and choked mass
flow have no wall-friction term and no Fanno line), with
aerodynamics/high-speed/normal-shock for shock-jump stagnation loss at a
station, and with aerodynamics/high-speed/shock-tube, which supplies the
deterministic-bisection precedent. It does NOT do Rayleigh heat-addition
flow of a frictionless duct (rayleigh-flow, same wave; friction with heat
addition is out of scope), boundary-layer skin friction and heating on
surfaces (flat-plate-skin-friction-heating), or the unsteady shock-tube
wave system (shock-tube).

## Domain quick reference

- Fanno-line integral: phi(M) = fL*/D = (1 - M^2)/(gamma M^2) +
  ((gamma + 1)/(2 gamma)) ln((gamma + 1) M^2 / (2 + (gamma - 1) M^2)).
  phi is the friction parameter that chokes the duct from the Mach number
  M: its only zero and minimum sit at M = 1, it falls from infinity at
  M = 0 to 0 at M = 1 and rises toward the plateau ((gamma + 1)/(2
  gamma)) ln((gamma + 1)/(gamma - 1)) - 1/gamma (0.8215 at gamma 1.4).
- Segment rule: a segment of friction parameter fL/D strictly below
  phi(M1) moves the Mach number toward 1 on the same branch, consuming
  fL/D = phi(M1) - phi(M2) of the choke margin. Subsonic friction
  accelerates the flow (M2 in (M1, 1)); supersonic friction decelerates
  it (M2 in (1, M1)). At fL/D = phi(M1) the exit is exactly sonic and
  beyond it the duct chokes internally (out of scope, the module raises).
- Choking length: L* = (D/f) fL*/D from the inlet Mach and Fanning
  factor; the friction factor that makes a duct of length L exactly
  choked is f_req = (D/L) fL*/D(M1).
- Starred total-pressure ratio: p0/p0* = (1/M) (2 (1 + (gamma - 1) M^2 /
  2)/(gamma + 1))^((gamma + 1)/(2 (gamma - 1))), equal to 1 at M = 1 and
  growing on both branches away from it.
- Starred static ratios: T/T* = (gamma + 1)/(2 + (gamma - 1) M^2),
  p/p* = (1/M) sqrt((gamma + 1)/(2 + (gamma - 1) M^2)), rho/rho* = (1/M)
  sqrt((2 + (gamma - 1) M^2)/(gamma + 1)), all 1.0 at M = 1 and
  consistent with p/p* = (rho/rho*)(T/T*).
- Station ratios across a segment (one duct, one sonic reference):
  p02/p01 = (p0/p0*)2/(p0/p0*)1 below 1 on both branches, and for X in
  p, T, rho: X2/X1 = (X/X*)2/(X/X*)1. Entropy rise ds/R = -ln(p02/p01)
  > 0; the duct is adiabatic so T02/T01 = 1.
- Conventions: f is the Fanning (skin-friction) factor f = tau_w / (rho
  u^2 / 2); Darcy-factor tables tabulate (4 f) L/D, so divide f_D by 4
  before calling. D is the hydraulic diameter. gamma = 1.4 air by
  default and a parameter elsewhere.

## Workflow

1. Fix the duct state: inlet Mach number M1, Fanning friction factor f,
   hydraulic diameter D and gas gamma (fanno_flow_logic constants and
   guards).
2. Evaluate the Fanno-line integral with fanno_function(M1): the
   friction parameter fL*/D that would choke the duct from the inlet
   Mach.
3. Compute the friction-duct choking length with choke_length(M1, f, D):
   the duct run that brings the exit exactly to M = 1 (0.0 when the
   inlet is already sonic).
4. Form the segment friction parameter fL/D = f L / D for the duct
   length L and recover the downstream Mach number with
   downstream_mach(M1, fL/D) on the inlet branch: subsonic flow
   accelerates toward M = 1, supersonic flow decelerates toward M = 1.
5. Read the starred reference ratios at each station with
   total_pressure_ratio(M) and static_ratios(M): p0/p0*, T/T*, p/p* and
   rho/rho* to the sonic state of the same duct.
6. Assemble the station-to-station duct state with duct_state(M1, fL/D):
   the p02/p01 total-pressure loss and the p2/p1, T2/T1, rho2/rho1
   quotients, then verify the entropy rise -ln(p02/p01) > 0 and the
   adiabatic identity T02/T01 = 1.
7. Find the friction required to choke with friction_to_choke(M1, L, D):
   the Fanning factor f_req that makes the given duct exactly choked,
   and compare it with the actual f to read the choke margin.
8. Confirm the deterministic checks with the contract test
   scripts/test_fanno_flow.py.

## Worked example

Representative duct: D = 0.1 m, Fanning f = 0.005 (friction parameter
gradient f/D = 0.05 per metre), gamma = 1.4. All values are real module
outputs.

- Fanno-line integral: fL*/D(0.3) = 5.299253105091 and fL*/D(2.0) =
  0.304996502581, so the 0.005-friction duct chokes from M = 0.3 in
  L* = 105.985062101823 m and from M = 2.0 in L* = 6.099930051630 m:
  the supersonic duct chokes about 17.4 times sooner at the same
  friction.
- Starred references: p0/p0* = 2.035065262346 at M = 0.3, 1.6875 at
  M = 2.0 and 1.0 at M = 1. At M = 0.3: T/T* = 1.178781925344,
  p/p* = 3.619057466836, rho/rho* = 3.070167084366. At M = 2.0:
  T/T* = 0.666666666667, p/p* = 0.408248290464, rho/rho* =
  0.612372435696, the standard Fanno table row.
- Subsonic branch: M1 = 0.3 through L = 50 m gives fL/D = 0.005 * 50 /
  0.1 = 2.5, below the choke value 5.299253105091. downstream_mach(0.3,
  2.5) = 0.375749134774, the subsonic flow accelerated toward M = 1; the
  round-trip residual phi(M2) + fL/D - phi(M1) is 2.498e-12 and the
  margin left to sonic is phi(0.3) - 2.5 = 2.799253105091 = phi(M2).
  duct_state(0.3, 2.5): p02/p01 = 0.822735477531 (17.7% total-pressure
  loss), p2/p1 = 0.794420493240, T2/T1 = 0.990043659533, rho2/rho1 =
  0.802409555973; the static pressure falls most and the static
  temperature almost stays (T02/T01 = 1.000000000000). Exit reference
  p0/p0* = 1.674320390423; ds/R = -ln(p02/p01) = 0.195120542447.
  friction_to_choke(0.3, 50, 0.1) = 0.010598506210, about double the
  actual 0.005, so the duct is not choked. downstream_mach(0.3, 0.0) =
  0.300000000000 in the zero-friction limit.
- Supersonic branch: M1 = 2.0 through L = 3 m gives fL/D = 0.15, below
  the choke value 0.304996502581. downstream_mach(2.0, 0.15) =
  1.552005392004, the supersonic flow decelerated toward M = 1; residual
  -8.171e-14, margin phi(2.0) - 0.15 = 0.154996502581. duct_state(2.0,
  0.15): p02/p01 = 0.718851057841 (28.1% loss), p2/p1 = 1.420320685669,
  T2/T1 = 1.214784619331, rho2/rho1 = 1.169195479649: the static
  pressure, temperature and density all rise as supersonic flow slows,
  the mirror image of the subsonic branch. Exit p0/p0* = 1.213061160106;
  ds/R = 0.330101094541. friction_to_choke(2.0, 3, 0.1) =
  0.010166550086.
- Read-off: friction pulls both branches toward M = 1 and spends total
  pressure doing it. A Mach-0.3 duct run must stay below fL/D 5.299 to
  avoid choking, a Mach-2.0 run below fL/D 0.305, and a duct above the
  choke parameter at its inlet is physically over-length for that inlet
  state (the module raises ValueError).

## Verification

- Confirm fanno_function returns the Fanno table anchors: 5.299253105091
  at M = 0.3, 1.069060312718 at 0.5, 0.304996502581 at 2.0 and
  0.786830832907 at 10.0, with the gamma parameter honored
  (fanno_function(2.0, 1.3) = 0.357277365682).
- Confirm p0/p0* is minimal at M = 1 and the starred static ratios all
  equal 1.0 there, with p/p* = (rho/rho*)(T/T*) at every Mach.
- Confirm downstream_mach round-trips: phi(M2) + fL/D - phi(M1) is below
  1e-9 on both branches and the zero-friction limit returns the inlet
  Mach within 1e-9.
- Confirm every non-physical input raises ValueError: Mach at 0 and
  negative, a sonic inlet, gamma at 1.0, friction factor, diameter and
  duct length at 0 and negative, and fL/D negative or at/above phi(M1)
  (the duct chokes at or before the exit; the module never returns a
  fake Mach below the branch floor).
- Confirm determinism: identical inputs give identical bits, no RNG, no
  imports beyond math.
- Run the contract test offline: python3 scripts/test_fanno_flow.py
  (41 tests, deterministic).

## Related leaves

- aerodynamics/high-speed/isentropic-flow-relations: the frictionless
  complement of this leaf, the isentropic total-to-static ratios,
  area-Mach inversion and choked mass flow at a geometric throat.
- aerodynamics/high-speed/normal-shock: shock-jump stagnation loss at a
  station, the discontinuous counterpart of the integrated friction
  loss here.
- aerodynamics/high-speed/shock-tube: the unsteady diaphragm wave system
  and the deterministic-bisection precedent reused by the branch
  inversion.
- aerodynamics/high-speed/flat-plate-skin-friction-heating:
  boundary-layer skin friction, drag and heating on surfaces, a
  different quantity from the duct-averaged Fanning factor of a confined
  channel.

## Pitfalls

- Mixing Fanning and Darcy friction factors: f here is the Fanning
  factor; tables that tabulate the Darcy factor f_D = 4 f give (4 f)
  L/D, so a caller converting table values must divide f_D by 4 before
  calling or the computed lengths come out four times too short.
- Confusing fL/D with fL*/D: fL*/D(M1) is the total choke parameter from
  the inlet, while fL/D is what a finite duct of length L actually
  consumes; a segment is only legal while fL/D stays strictly below
  fL*/D(M1), and the margin left to sonic is phi(M2) = phi(M1) - fL/D.
- Feeding an over-length duct: at fL/D = phi(M1) the exit is exactly
  sonic and beyond that the duct chokes internally, which has no
  steady-state solution on the Fanno line; the module raises ValueError
  instead of returning a fake Mach below the branch floor.
- Expecting friction to always slow the flow: in a constant-area
  adiabatic duct friction accelerates the subsonic branch (M2 above M1)
  and decelerates the supersonic branch (M2 below M1); both move toward
  M = 1, and the static temperature falls on the subsonic side but rises
  on the supersonic side.
- Reading p0/p0* as a loss along the duct: p0/p0* is the ratio to the
  sonic reference and grows away from M = 1 on both branches; the loss
  along the duct is the quotient p02/p01 = (p0/p0*)2/(p0/p0*)1, always
  below 1.
- Inverting a sonic inlet: downstream_mach raises at M1 = 1 because a
  sonic inlet is already choked; there is no duct inversion to perform.
- Adding heat: this leaf is adiabatic by claim (T0 constant). Friction
  with heat addition belongs to neither this leaf nor its rayleigh-flow
  sibling; it needs a combined Fanno-Rayleigh treatment that is out of
  scope.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fanno_flow.py

The test covers the Fanno table anchors of the fanno_function Fanno-line
integral on both branches and the gamma parameter, branch monotonicity,
the p0/p0* total-pressure-ratio anchors and its minimum at the sonic
state, the starred static-ratio rows with the p/p* = (rho/rho*)(T/T*)
identity, the friction-duct choking lengths and their closed-form
identity, the branch-preserving downstream Mach inversion with round-trip
residuals, the zero-friction limit and deterministic bits, the friction
required to choke and its consistency, the duct_state loss ratios with
entropy rise and the adiabatic T02/T01 check on both branches, and
ValueError rejection of every non-physical input (the 12 anchor cases:
Mach at 0 and negative, a sonic inlet, gamma at 1.0, zero friction
factor, diameter and duct length, fL/D negative and at/above the choke
value at M1 = 0.3 and M1 = 2.0).

## Compliance

- Standards referenced, not reproduced: NACA TR-824 (Equations, Tables
  and Charts for Compressible Flow) frames the compressible-flow
  context; the Fanno relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
