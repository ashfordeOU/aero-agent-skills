# Wave-36 leaf spec: ram-air-turbine-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/ram-air-turbine-sizing/
- Pack: sizing. Closest siblings: hydraulic-system-sizing (its emergency
  trigger is the emergency ACCUMULATOR adiabatic storage, the consumption
  side; zero "ram air turbine" tokens in its description), aircraft-
  electrical-load-analysis (owns the essential-load rollup that supplies
  the required power P_req, an INPUT here), bleed-air-system-sizing
  (engine bleed pneumatic, unrelated to ram-air power extraction).
  Whole-tree grep: "ram air turbine" / "rat" as a power device appears
  NOWHERE in skills/ (no leaf sizes the aero power-extraction device).
  ZERO owners.
- Standards id: far-25 (reference-only; 25.1351 emergency electrical /
  essential power context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the emergency ram air turbine rotor at the conceptual level from
the required emergency power at a fixed emergency airspeed: compute the
required rotor swept area from the wind-power relation P = 0.5 rho V^3 A
Cp with a fixed design overall power coefficient, derive the rotor disk
diameter, and round-trip the power check. Produces the required swept
area, disk diameter, and the round-trip available power at the stated
condition, plus a fit verdict against a stowage diameter limit.

Does NOT do: the essential electrical load rollup and margin
(aircraft-electrical-load-analysis supplies P_req); the emergency
hydraulic accumulator volume and pressure (hydraulic-system-sizing);
RAT generator/control details (out of scope, empirical).

## Model (implement exactly)

Module constants:
- RHO_SL_DEFAULT = 1.225 (kg/m3, ISA sea level density).
- CP_RAT_DEFAULT = 0.10 (overall RAT power coefficient including
  efficiency and losses, fixed design value).
- BETZ_LIMIT = 16.0/27.0 (0.592593, ideal actuator-disk upper bound).
- PI = math.pi.

Conventions: required power in W; airspeed in m/s at the fixed emergency
condition (a user input; the classic anchor is a minimum controllable
descent speed); density default ISA sea level.

Functions (pure stdlib):
- rat_swept_area(p_req_w, v_m_s, rho = RHO_SL_DEFAULT, cp =
  CP_RAT_DEFAULT) -> float m2 = p/(0.5*rho*v^3*cp). ValueErrors:
  p <= 0; v <= 0; rho <= 0; cp <= 0 or cp >= BETZ_LIMIT.
- disk_diameter(area_m2) -> float m = sqrt(4A/pi). ValueError: area <= 0.
- rat_available_power(area_m2, v_m_s, rho = RHO_SL_DEFAULT, cp =
  CP_RAT_DEFAULT) -> float W = 0.5*rho*v^3*A*cp. ValueErrors as above.
- rat_sizing_summary(p_req_w, v_m_s, max_stowage_diameter_m, rho =
  RHO_SL_DEFAULT, cp = CP_RAT_DEFAULT) -> dict {area_m2, diameter_m,
  available_w, margin_w, stowage_verdict} where margin = available -
  required and stowage_verdict PASS when diameter <= max diameter.

Identity to test: rat_available_power(rat_swept_area(P)) == P within
1e-6 (round-trip); disk diameter area round trip A == pi D^2/4.

## Worked example

Reference installation: emergency RAT must supply 5000 W at the fixed
emergency descent speed of 100 m/s at ISA sea level with the design
power coefficient 0.10.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- area = 5000/(0.5*1.225*100^3*0.10) = 5000/61250 = 0.081633 m2.
- diameter = sqrt(4*0.081633/pi) = 0.3224 m (322.4 mm).
- round-trip power = 0.5*1.225*100^3*0.081633*0.10 = 5000.00 W exact.
- stowage verdict vs 0.40 m limit: PASS (0.3224 <= 0.40).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: p <= 0; v <= 0; rho <= 0; cp <= 0 or cp >= 0.592593
  (a 0.60 cp input must raise); area <= 0 in disk_diameter.
- Area: 0.081633 within 1e-6; diameter 0.3224 within 1e-4.
- Round-trip power == 5000.00 within 1e-6.
- Scaling: doubling v at fixed area multiplies power by 8.
- Stowage verdict PASS at 0.40 limit, FAIL at 0.30 limit.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-ram-air-turbine-sizing.yaml)

Query 1 (copy verbatim):
  "size the ram air turbine rotor disk diameter for 5 kw of emergency power at 100 meters per second"
  intent: "vehicle-design; RAT swept area and disk diameter from emergency power"
  expected_skill: "vehicle-design/sizing/ram-air-turbine-sizing"
Query 2 (copy verbatim):
  "determine the ram air turbine swept area required for the essential load at the emergency descent airspeed"
  intent: "vehicle-design; RAT wind-power swept area sizing at fixed airspeed"
  expected_skill: "vehicle-design/sizing/ram-air-turbine-sizing"
Task ids: w36-ram-air-turbine-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the ram air turbine:" and
include the outputs in the Claim. First tag: ram-air-turbine-sizing.
Additional tags ONLY: ram-air-turbine-rotor, rat-disk-diameter,
emergency-power-extraction, rat-swept-area, wind-power-rotor-sizing.
NEVER single generic words (rat, rotor, turbine, power, emergency, disk,
wind). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): accumulator, reservoir, pump
flow (hydraulic-system-sizing); essential load rollup, duty cycle,
generator rating (aircraft-electrical-load-analysis); bleed duct,
offtake (bleed-air-system-sizing).
