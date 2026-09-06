---
name: rayleigh-flow
description: "Use when you must compute the rayleigh-flow state change of a perfect gas heated or cooled in a constant-area frictionless duct: convert the inlet Mach number into the Rayleigh-line ratios against the sonic state T/T*, p/p*, rho/rho*, T0/T0*, p0/p0*; find the maximum heat addition that thermally chokes the duct from a subsonic or supersonic inlet Mach number, q_max = cp*T1*(1 - M^2)^2/(2*(gamma+1)*M^2); recover the exit Mach number after a given heat addition per unit mass on the inlet branch; and report the entropy rise from the second law. Produces the station ratio set, the choking heat addition, the exit Mach and stagnation pressure ratio, and the entropy rise, in SI units, that gate the heat-addition duct assessment. Trigger: heat addition duct, thermal choking, rayleigh flow, rayleigh line, constant area frictionless duct."
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
  tags: [rayleigh-flow, heat-addition-duct, thermal-choking, rayleigh-line]
  version: 0.1.0
  author: AeroSkills
---

# Rayleigh Flow (aerodynamics/high-speed/rayleigh-flow)

Use when you must compute the state change of a perfect gas heated or
cooled in a constant-area frictionless duct, the Rayleigh flow that
closes the pair with the Fanno friction duct of the same wave. This
leaf implements the closed-form Rayleigh-line station relations
against the thermal-choking sonic state (the star state of the
same-mass-flow duct, reached at M = 1), the maximum heat addition that
thermally chokes the duct on either inlet branch, the exit Mach number
after a prescribed heat addition recovered from the quadratic
total-temperature balance, and the second-law entropy rise, in pure
Python stdlib. It pairs with the same-pack isentropic-flow-relations
(frictionless duct WITHOUT heat: total temperature frozen, isentropic
throat A*) and the same-pack fanno-flow (adiabatic duct WITH wall
friction) as the two non-isentropic constant-area duct mechanisms of
the wave; heat in, no friction here.

## Domain quick reference

Air at gamma = 1.4, R = 287.0 J/(kg K), cp = gamma*R/(gamma - 1) =
1004.5 J/(kg K), constant specific heat only. The star denotes the
state of the same-mass-flow constant-area frictionless duct at M = 1,
i.e. thermal choking, and f = 1 + gamma*M^2:

- Static ratios: T/T* = M^2*(1+gamma)^2/f^2, p/p* = (1+gamma)/f,
  rho/rho* = f/(M^2*(1+gamma)) = (p/p*)/(T/T*) exactly. T/T* peaks at
  (1+gamma)^2/(4*gamma) = 36/35 = 1.02857142857 at M = 1/sqrt(gamma).
- Total ratios: T0/T0* = (T/T*)*(1 + (gamma-1)*M^2/2)*2/(gamma+1);
  p0/p0* = (p/p*)*((1 + (gamma-1)*M^2/2)*2/(gamma+1))^(gamma/(gamma-1)).
  All five ratios equal 1 at M = 1.
- Heat balance: T0_2 = T0_1 + q/cp, so T0_2/T0_1 = 1 + q/(cp*T0_1);
  T0* of the duct is fixed, so every state ratio between two stations
  of one duct is the ratio of the station Rayleigh ratios at their
  Mach numbers.
- Thermal choking: q_max = cp*T1*(1 - M1^2)^2/(2*(gamma+1)*M1^2) =
  cp*(T0* - T0_1), zero at M1 = 1 and symmetric under M1 to 1/M1 at
  equal static temperature (a Mach 0.5 inlet and a Mach 2.0 inlet at
  the same T1 choke on the same heat per kilogram).
- Exit Mach: with g(M) = T0/T0*(M), g2 = g(M1)*(1 + q/(cp*T0_1)), and
  g(M2) = g2 is a quadratic in x = M2^2 solved by the quadratic
  formula: (gamma^2 - 1 - g2*gamma^2)*x^2 + (2*(1+gamma) -
  2*g2*gamma)*x - g2 = 0. Subsonic inlet: smaller positive root, M2 in
  (0, 1]. Supersonic inlet: larger positive root, M2 in [1, inf),
  which exists only above the branch floor g2 = (gamma^2 - 1)/gamma^2
  reached asymptotically as M goes to infinity.
- Entropy: ds = cp*ln(T2/T1) - R*ln(p2/p1); on the T-s plane the
  Rayleigh curve offset (s - s*)/cp = ln(T/T*) - ((gamma-1)/gamma)*
  ln(p/p*) is strictly negative off M = 1 and zero at M = 1, the
  entropy maximum of the Rayleigh line. Heat addition always raises
  the stagnation temperature and always lowers the stagnation
  pressure ratio p0_2/p0_1 = p0/p0*(M2)/p0/p0*(M1) below 1 (0.8976 at
  thermal choke from a Mach 0.5 inlet).
- Units SI throughout: Pa, K, kg/m3, J/kg, J/(kg K).

## Workflow

1. Fix the duct inlet state: static temperature t_static (K), static
   pressure p_static (Pa), inlet Mach number mach, and the heat
   addition per unit mass q in J/kg (positive heats, negative rejects).
2. Convert the inlet Mach number into the five Rayleigh-line station
   ratios with rayleigh_ratios; every ratio equals 1 at the
   thermal-choking sonic state M = 1.
3. Find the maximum heat addition that thermally chokes the duct with
   heat_addition_maximum: q_max in J/kg from the static-temperature
   closed form, valid on both branches and symmetric under mach to
   1/mach.
4. Recover the exit Mach number after the given heat addition on the
   inlet's own branch with exit_mach: smaller positive root for a
   subsonic inlet, larger positive root for a supersonic inlet; q at
   q_max returns 1.0 (thermally choked), q above q_max and supersonic
   rejection past the branch floor raise ValueError.
5. Build the downstream station with heat_addition: the absolute exit
   state (m2, t2, p2, rho2, t02, p02), the station ratios
   t2_over_t1, p2_over_p1, rho2_over_rho1, t02_over_t01,
   p02_over_p01, the second-law entropy rise ds and ds_over_cp, and
   the choked flag; entropy_rise gives ds between any two gas states.
6. Check the Rayleigh T-s curve offset identity with
   rayleigh_curve_offset: ds/cp between two stations of one duct
   equals the curve-offset difference at their Mach numbers, and the
   sonic point M = 1 is the entropy maximum of the Rayleigh line.
7. Confirm the deterministic contract with the offline test
   scripts/test_rayleigh_flow.py.

## Worked example

Air at T1 = 300 K, p1 = 101325 Pa, run at the dual inlet pair
M1 = 0.5 (subsonic branch) and M1 = 2.0 (supersonic branch). Real
module outputs:

- Station ratios at the inlet: M1 = 0.5 gives T/T* = 0.790123456790,
  p/p* = 1.777777777778, rho/rho* = 2.25, T0/T0* = 0.691358024691,
  p0/p0* = 1.11405250318, with T0_1 = 315.000 K and T0* = 455.625 K;
  M1 = 2.0 gives 0.528925619835, 0.363636363636, 0.6875,
  0.793388429752, 1.50309597853, with T0_1 = 540.000 K and
  T0* = 680.625 K.
- Maximum heat addition: q_max = heat_addition_maximum(300, 0.5) =
  heat_addition_maximum(300, 2.0) = 141257.8125 J/kg in both cases
  (141.3 kJ/kg chokes either duct): q_max/(cp*T1) = 0.46875, and
  q_max = cp*(T0* - T0_1) = cp*140.625 J/kg on both branches.
- Subsonic inlet M1 = 0.5, q = q_max/2 = 70628.90625 J/kg:
  heat_addition gives exit M2 = 0.625879453912 (heating accelerates
  the subsonic flow toward 1), T2 = 357.318 K, p2 = 88341.135 Pa,
  T2/T1 = 1.19106128221, p2/p1 = 0.871859216769,
  rho2/rho1 = 0.732001979908, T0_2/T0_1 = 1.22321428571 (stagnation
  temperature rises 22.3%), p0_2/p0_1 = 0.957052789099 (stagnation
  pressure falls 4.3%), ds = 214.987 J/(kg K), ds/cp = 0.214023976827.
- At q = q_max the exit reaches M2 = 1 exactly with
  p0_2/p0_1 = 0.897623762925 = 1/1.11405250318, the minimum
  stagnation pressure ratio the heating duct can deliver.
- Supersonic inlet M1 = 2.0, same q = 70628.90625 J/kg: exit
  M2 = 1.54998945381 (heating decelerates the supersonic flow toward
  1), T2 = 412.236 K, p2 = 153260.459 Pa, T2/T1 = 1.37411954397,
  p2/p1 = 1.51256313292, rho2/rho1 = 1.10075076042,
  T0_2/T0_1 = 1.13020833333, p0_2/p0_1 = 0.763277518128 (the same
  heat costs 23.7% of the stagnation pressure), ds = 200.481 J/(kg K).
- Heat rejection: q = -50000 J/kg at M1 = 0.5 drives the exit to
  M2 = 0.430803500026 with ds/cp = -0.17940496639 (cooling lowers
  entropy); q = -200000 J/kg at M1 = 2.0 accelerates the exit to
  M2 = 12.5126628564; rejection past the supersonic branch floor
  (roughly -207.6 kJ/kg here) has no steady Rayleigh state and raises.
- Read-off: adding 70.6 kJ/kg to the Mach 0.5 duct accelerates it to
  M 0.626 with a 4.3% stagnation pressure loss and ds = 215 J/(kg K);
  the identical heat input to the Mach 2 duct decelerates it to
  M 1.55 with a 23.7% loss and ds = 200 J/(kg K).

## Verification

- rayleigh_ratios(0.5) returns the five ratios above; rayleigh_ratios(2.0)
  the supersonic set; all five ratios return 1 within 1e-12 at M = 1.
- rho/rho* equals (p/p*)/(T/T*) within 1e-12 at M = 0.5 and M = 2.
- heat_addition_maximum(300, 0.5) equals heat_addition_maximum(300, 2.0)
  = 141257.8125 J/kg within 1e-12 relative (the M to 1/M duality),
  equals cp*(T0* - T0_1) within 1e-12, and is 0 within 1e-15 at M = 1.
- exit_mach chokes at the module q_max (exit 1.0 within 1e-9) and the
  half-choke exits match the worked example within 1e-9 relative.
- ds equals cp*ln(T2/T1) - R*ln(p2/p1) within 1e-9 and ds/cp equals
  rayleigh_curve_offset(m2) - rayleigh_curve_offset(m1) within 1e-12.
- Rejection gives ds < 0; q above q_max raises ValueError naming the
  thermal choking limit; supersonic rejection past the branch floor
  raises ValueError naming the branch limit; q at or below -cp*T0_1 on
  a subsonic inlet raises; non-positive mach, temperature, pressure
  and density-driving inputs raise ValueError across the module.
- Run the contract test offline: python3 scripts/test_rayleigh_flow.py
  (32 tests, deterministic, identical under both interpreters).

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rayleigh_flow.py

The test covers the published gamma-1.4 Rayleigh table agreement at
M = 0.5 and M = 2.0 (fractional values 64/81, 16/9, 9/4, 56/81 and
64/121, 4/11, 11/16, 96/121), unity of all five ratios at the sonic
state, the density round trip, the T/T* peak 36/35 at M = 1/sqrt(gamma),
the q_max closed form with its M to 1/M duality and the cp*(T0* - T0_1)
equivalence, thermal choking at the module q_max on both branches, the
subsonic and supersonic half-choke exit states with the full
downstream ratio and entropy set, the second-law entropy identity, the
Rayleigh curve-offset identity, heat rejection on both branches, and
ValueError rejection of every non-physical input class.

## Related leaves

- aerodynamics/high-speed/isentropic-flow-relations: the frictionless
  ADIABATIC complement (total temperature frozen across the duct, the
  isentropic throat A*), for the no-heat conversion of Mach number
  into total to static ratios and choked mass flow.
- aerodynamics/high-speed/fanno-flow: the adiabatic constant-area duct
  WITH wall friction (Fanno line, choking length), the complementary
  non-isentropic constant-area duct mechanism to this leaf.
- propulsion/gas-turbine-cycle/combustor-design: the burner
  thermochemistry that produces the heat addition from fuel flow, the
  upstream source of q for a real heat-addition duct.
- aerodynamics/high-speed/hypersonic-flow: the Rayleigh pitot relation
  for stagnation pressure behind a normal or bow shock, a shock
  relation distinct from this Rayleigh flow duct model.

## Pitfalls

- Using the isentropic throat for the heated duct: with heat addition
  the total temperature changes, T0_2 = T0_1 + q/cp, and the sonic
  state is the thermal-choking state of the same-mass-flow duct (a
  different star), not the isentropic area throat A*.
- Adding heat at the sonic point: a duct already at M = 1 is
  thermally choked; any further heat addition has no steady Rayleigh
  state, and the module raises rather than returning a spurious exit.
- Rejecting heat past the supersonic branch floor: the balance g2 =
  g(M1)*(1 + q/(cp*T0_1)) falls below (gamma^2 - 1)/gamma^2 only when
  the exit would exceed infinite Mach, so the branch limit raises;
  q = -cp*T0_1 on the subsonic side is the mirror limit as M2 tends
  to 0.
- Reading the exit Mach off the wrong branch root: the balance
  quadratic has a root on each branch, the subsonic inlet takes the
  smaller positive root and the supersonic inlet the larger one;
  mixing the branches returns a Mach number on the wrong side of 1.
- Treating heat addition as always raising the static temperature:
  static temperature rises only up to M = 1/sqrt(gamma), where
  T/T* peaks at 36/35; heating a supersonic duct raises its static
  temperature and pressure while its Mach number falls toward 1.
- Quoting the entropy change sign from the Mach drift alone: ds is
  negative under heat rejection even though rejection accelerates a
  supersonic flow, and ds/cp is always the curve-offset difference
  ln(T/T*) - ((gamma-1)/gamma)*ln(p/p*) between the two stations.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rayleigh_flow.py

The test exercises the five Rayleigh-line station ratios, the
thermal-choking heat addition with the M to 1/M duality, the exit
Mach recovery on each inlet branch, the full downstream state with
stagnation temperature rise and stagnation pressure fall, the
second-law entropy rise, the T-s curve offset identity, heat
rejection, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames the
  one-dimensional compressible-flow methodology; the Rayleigh-line
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml (reference-only).
- compliance: STANDARDS-REF, gated: false.
