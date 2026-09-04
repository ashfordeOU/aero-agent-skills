---
name: airspeed-conversion
description: "Use when you must convert airspeeds through the compressibility-corrected air-data chain: calibrated airspeed from impact pressure, calibrated airspeed from true airspeed at altitude, true airspeed from calibrated airspeed at altitude through the compressible inversion on the local static pressure, equivalent airspeed from true airspeed and the density ratio, Mach number from calibrated or true airspeed, and impact pressure from Mach number or calibrated airspeed. Produces the full calibrated, equivalent, true and Mach set plus the impact pressure that gates air-data reduction and performance work. Trigger: calibrated airspeed, equivalent airspeed, true airspeed, mach-airspeed, impact pressure, airspeed-indicator compressibility correction, air-data chain, knots calibrated."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: units-atmos
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: units-atmos
  tags: [airspeed-conversion, calibrated-airspeed, equivalent-airspeed, true-airspeed, mach-airspeed, impact-pressure, airspeed-indicator]
  version: 0.1.0
  author: Aero Agent Skills
---

# Airspeed Conversion (cross-cutting/units-atmos/airspeed-conversion)

Use when the task is converting airspeeds through the
compressibility-corrected air-data chain of a subsonic aircraft:
calibrated airspeed from impact pressure, calibrated airspeed from true
airspeed at altitude, true airspeed from calibrated airspeed at altitude
(the compressible inversion through the local static pressure),
equivalent airspeed from true airspeed and the density ratio, Mach
number from calibrated or true airspeed, and impact pressure from Mach
number or calibrated airspeed. This leaf implements the full
qc -> CAS, CAS -> M -> TAS -> EAS chain in all directions, subsonic, in
pure Python, stdlib only, with the ISA state leg computed internally. It
pairs with cross-cutting/units-atmos/unit-conversion for unit factor
handling and cross-cutting/units-atmos/isa-atmosphere for the standalone
ISA state leaf.

## Domain quick reference

- ISA state leg at altitude h (internal, same numbers as isa-atmosphere):
  troposphere below 11000 m: T = T0 - LAPSE*h with T0 = 288.15 K, LAPSE =
  0.0065 K/m; p = P0*(T/T0)^(G0/(LAPSE*R)); rho = p/(R*T); a =
  sqrt(GAMMA*R*T). Above the tropopause T = 216.65 K constant and p decays
  exponentially with the scale height R*T/G0. Sea level: P0 = 101325 Pa,
  rho0 = 1.225 kg/m3, A0 = 340.294 m/s, GAMMA = 1.4, R = 287.05287.
- Impact pressure from Mach: qc = p*((1 + 0.2*M^2)^3.5 - 1), the isentropic
  pitot relation, subsonic.
- Calibrated airspeed from qc: CAS = A0*sqrt(5*((qc/P0 + 1)^(2/7) - 1)),
  the airspeed-indicator compressibility correction evaluated at sea level.
- Mach from qc at altitude: M = sqrt(5*((qc/p + 1)^(1/3.5) - 1)). The
  inversion is non-unique past M = 1, so qc/p >= 0.8929 is rejected.
- True airspeed: TAS = M*a with the local speed of sound.
- Equivalent airspeed: EAS = TAS*sqrt(rho/rho0). At sea level the density
  ratio is 1 and 1/3.5 equals 2/7, so the whole chain collapses to the
  identity CAS = EAS = TAS.
- Knots: 1 kt = 0.514444 m/s (module constant KT_TO_MS).

## Workflow

1. Fix the flight condition: pressure altitude in m and exactly one speed
   input among calibrated airspeed in kt, true airspeed in m/s,
   equivalent airspeed in kt, or Mach number.
2. Get the whole air-data set with airspeed_chain(altitude_m, cas_kt=...,
   tas_ms=..., eas_kt=..., mach=...): it returns the dict {altitude_m, p,
   rho, a, mach, cas_kt, eas_kt, tas_ms, qc_Pa} with every quantity filled
   by the appropriate chain leg. Exactly one speed input is required.
3. For a single leg, call the scalar functions directly: calibrated
   airspeed from measured qc with calibrated_from_impact_pressure(qc).
4. Calibrated from a true airspeed at altitude (the step no unit table
   owns): calibrated_from_true_airspeed(tas_ms, altitude_m) runs the
   two-step chain M = TAS/a, qc = p*((1 + 0.2*M^2)^3.5 - 1), then the CAS
   calibration.
5. Inverse leg: true_from_calibrated(cas_ms, altitude_m) inverts the CAS
   formula algebraically to qc, then applies the subsonic qc inversion at
   the local static pressure and multiplies by the local speed of sound.
6. Density legs: equivalent_from_true(tas_ms, rho) and
   true_from_equivalent(eas_ms, rho) carry the sqrt(rho/rho0) factor;
   mach_from_true_airspeed(tas_ms, a) exposes the M = TAS/a arithmetic.
7. Confirm the deterministic checks with the contract test
   scripts/test_airspeed_conversion.py.

## Worked example

- ISA 30,000 ft (9144 m): module isa_state returns T = 228.71 K, p =
  30089.6 Pa (spec band 30089-30100), rho = 0.45831 kg/m3, a = 303.17 m/s.
- 250 KCAS at 30,000 ft: airspeed_chain(9144.0, cas_kt=250.0) returns qc =
  10498.2 Pa (bound 10400-10600), M = 0.6681 (bound 0.66-0.68), TAS =
  202.55 m/s = 393.73 kt (bound 200-205 m/s, 393-394 kt), EAS = 240.83 kt
  (bound 239-242 kt).
- M = 0.8 at the tropopause 11000 m (p = 22632.0 Pa, a = 295.07 m/s):
  qc = 11866.9 Pa (bound 11800-11950), CAS = 265.21 kt (bound 265-266),
  EAS = 250.10 kt (bound 249-251), TAS = 236.06 m/s = 458.86 kt exactly
  (M*a).
- Sea level 100 m/s CAS: EAS, TAS and CAS all equal 100.000 m/s to below
  1e-6 kt (the density ratio is 1 and 1/3.5 = 2/7, so the chain collapses
  to identity).
- 10,000 ft (3048 m), sigma = rho/rho0 = 0.73848: TAS 150.0 m/s maps to
  EAS = 150.0*sqrt(0.73848) = 128.90 m/s.
- Round trips: CAS -> TAS -> CAS and TAS -> CAS -> TAS at 0, 3048 and
  9144 m recover the input to below 2e-13 m/s (spec: < 1e-9).

## Verification

- Worked-example outputs sit inside the spec magnitude bounds above;
  take the module outputs as the contract test targets to 4 significant
  figures.
- Monotonicity: CAS increases with qc; M increases with qc at fixed p;
  TAS at fixed CAS increases with altitude (TAS at 250 KCAS and 9144 m
  exceeds TAS at 250 KCAS and sea level).
- Ordering at altitude: EAS < CAS < TAS for a subsonic cruise point.
- Sea-level identity: CAS == EAS == TAS within 1e-3 kt.
- ValueError rejection: altitude < 0; M < 0 or M >= 1; qc < 0; p <= 0;
  rho <= 0; tas < 0; cas < 0; eas < 0; qc/p >= 0.8929 in the subsonic
  qc inversion; zero or multiple speed inputs to airspeed_chain.
- Deterministic: no RNG, bit-identical floats run to run.
- Run the contract test offline: python3 scripts/test_airspeed_conversion.py
  (35 tests, deterministic, stdlib only).

## Related leaves

- cross-cutting/units-atmos/isa-atmosphere: the standalone ISA T/p/rho/a
  state leaf at altitude; this leaf uses the same leg internally.
- cross-cutting/units-atmos/unit-conversion: unit factor table including
  knots and Mach from a passed speed of sound.
- cross-cutting/units-atmos/dimensional-analysis: dimensional consistency
  checks for speed and pressure relations.
- flight-test-operations/planning/position-error-calibration: calibrates
  measured flight-test channels into calibrated airspeed, upstream of this
  chain.
- flight-test-operations/performance/level-acceleration-test: embeds one
  leg of this chain in the acceleration survey.
- aerodynamics/high-speed/transonic-similarity: the coefficient
  correction sibling (Prandtl-Glauert family); do not confuse it with the
  airspeed-indicator compressibility correction owned here.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_airspeed_conversion.py

The test covers the worked-example magnitude bounds (250 KCAS at 30,000
ft, M = 0.8 at the tropopause, sea-level identity, 10,000 ft EAS),
calibrated airspeed from qc and the algebraic inverse, the CAS <-> TAS
chains through the local static pressure, EAS legs, round-trip
identities at 0, 3048 and 9144 m below 1e-9 m/s, monotonicity, EAS < CAS
< TAS ordering, chain dict shape with the exactly-one-input rule, and
ValueError rejection of every non-physical input listed in Verification.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the historical
  reference for the airspeed-indicator compressibility correction; the
  relations above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
