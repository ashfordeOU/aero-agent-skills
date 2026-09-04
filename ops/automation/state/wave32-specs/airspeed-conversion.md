# Wave-32 leaf spec: airspeed-conversion (cross-cutting, units-atmos pack)

- Path: skills/cross-cutting/units-atmos/airspeed-conversion/
- Pack: units-atmos. Siblings: isa-atmosphere (ISA T/p/rho at altitude),
  unit-conversion (unit factor table incl. Mach from a passed speed of
  sound), dimensional-analysis, temperature-conversion.
- Standards id: naca-tr-824 (reference-only; pack convention, verified
  across all numerics/units-atmos siblings). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compute the compressibility-corrected airspeed conversion chain of a
subsonic aircraft air-data system: calibrated airspeed from impact
pressure, calibrated airspeed from true airspeed at altitude, true
airspeed from calibrated airspeed at altitude (the compressible
inversion through the local static pressure), equivalent airspeed from
true airspeed and the density ratio, Mach number from calibrated or
true airspeed, and impact pressure from Mach number or calibrated
airspeed. Produces the full CAS/EAS/TAS/Mach set plus the impact
pressure that gates air-data reduction and performance work.

Does NOT do: the ISA atmosphere state itself (cross-cutting/units-atmos/
isa-atmosphere owns T/p/rho/a at altitude); unit factor conversion of
length/speed/temperature/pressure between SI and imperial
(unit-conversion owns knots-to-m/s factors and Mach from a passed speed
of sound); position-error calibration from flight-test measurements
(flight-test-operations/planning/position-error-calibration owns
IAS-to-CAS from tower fly-by and trailing-cone runs); post-flight
corrected-airspeed reduction of measured channels
(flight-test-operations/planning/flight-test-data-reduction); the
aeronautical compressibility correction to aerodynamic COEFFICIENTS
(Prandtl-Glauert / Karman-Tsien, aerodynamics/high-speed/
transonic-similarity owns coefficient corrections - do not use
coefficient-correction tokens). This leaf owns the airspeed-indicator
compressibility chain only: qc -> CAS, CAS -> M -> TAS -> EAS, all
directions, subsonic.

## Model (implement exactly)

Constants (module level, SI):
- GAMMA = 1.4
- R_GAS = 287.05287 (J/kg/K)
- T0_ISA = 288.15 (K), P0_ISA = 101325.0 (Pa), RHO0_ISA = 1.225 (kg/m3)
- A0_ISA = sqrt(GAMMA * R_GAS * T0_ISA) = 340.294 (m/s)
- G0 = 9.80665, LAPSE = 0.0065 (K/m), TROPOPAUSE = 11000.0 (m)
- KT_TO_MS = 0.514444 (kt to m/s)

Functions (pure stdlib, subsonic M < 1 domain):

- wrap: none needed (all formulas scalar).

- isa_state(altitude_m) -> dict {T, p, rho, a}: troposphere below
  11000 m: T = T0 - LAPSE*h, p = P0*(T/T0)**(G0/(LAPSE*R_GAS)),
  rho = p/(R_GAS*T), a = sqrt(GAMMA*R_GAS*T). Above the tropopause:
  T = 216.65 K constant, p = p_tropo * exp(-G0*(h-11000)/(R_GAS*T)),
  rho = p/(R_GAS*T), a constant. ValueError for altitude < 0. (This is
  the pack's standard ISA leg; reuse the same numbers as isa-atmosphere.)

- impact_pressure_from_mach(M, p) -> qc = p * ((1 + 0.2*M**2)**3.5 - 1).
  ValueError if M < 0 or M >= 1 or p <= 0.

- mach_from_impact_pressure(qc, p) -> M = sqrt(5 * ((qc/p + 1)**(1/3.5)
  - 1)). ValueError if qc < 0 or p <= 0. Subsonic branch only: the
  inversion is non-unique past M = 1; reject qc that implies M >= 1
  (qc/p >= (1.2**3.5 - 1) = 1.267... actually (1+0.2)^3.5-1 = 1.2^3.5-1
  = 1.8929-1 = 0.8929; reject qc/p >= 0.8929).

- calibrated_from_impact_pressure(qc) -> CAS = A0_ISA *
  sqrt(5 * ((qc/P0_ISA + 1)**(2/7) - 1)). ValueError if qc < 0.

- calibrated_from_true_airspeed(tas, altitude_m) -> the two-step chain:
  (T,p,rho,a) = isa_state(altitude); M = tas/a; qc =
  impact_pressure_from_mach(M, p); CAS = calibrated_from_impact_pressure(qc).
  ValueError if tas < 0 or M >= 1. This is the step NO existing leaf
  owns: converting TAS back to CAS needs the local static pressure and
  the compressible inversion.

- true_from_calibrated(cas, altitude_m) -> inverse chain:
  qc = inverse of calibrated_from_impact_pressure: qc = P0_ISA *
  ((1 + (cas/A0_ISA)**2 / 5)**3.5 - 1)  [exact algebraic inverse of the
  CAS formula]; (T,p,rho,a) = isa_state(altitude); M =
  mach_from_impact_pressure(qc, p); TAS = M*a. ValueError if cas < 0.
  Round trip: true_from_calibrated(calibrated_from_true_airspeed(tas, h), h)
  returns tas to < 1e-9 m/s.

- equivalent_from_true(tas, rho) -> EAS = tas * sqrt(rho/RHO0_ISA).
  ValueError if tas < 0 or rho <= 0.
- true_from_equivalent(eas, rho) -> TAS = eas / sqrt(rho/RHO0_ISA).
- mach_from_true_airspeed(tas, a) -> M = tas/a. (Unit conversion leaf
  computes Mach from a passed speed of sound; this is the same
  arithmetic inside the chain, exposed for completeness.)
- airspeed_chain(altitude_m, cas_kt=None, tas_ms=None, eas_kt=None,
  mach=None) -> dict convenience: exactly one speed input required (the
  others None); returns {altitude_m, p, rho, a, mach, cas_kt, eas_kt,
  tas_ms, qc_Pa} with every quantity filled by the appropriate chain.
  ValueError if zero or more than one input is given, or any input is
  negative.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

ISA 30,000 ft (9144.0 m): T = 228.71 K, p = 30092 Pa (30089-30100 band),
rho = 0.4583 kg/m3, a = 303.17 m/s. Run your module and take real
outputs as assert targets to 4 significant figures, then check the
magnitude bounds:

- 250 KCAS at 30,000 ft: qc in 10 400-10 600 Pa (about 10 499);
  M in 0.66-0.68 (about 0.668); TAS in 200-205 m/s (about 202.6) =
  393-394 kt; EAS in 239-242 kt (about 240.9).
- M = 0.8 at the tropopause 11 000 m (ISA p = 22 632 Pa, a = 295.07 m/s):
  qc in 11 800-11 950 Pa (about 11 864); CAS in 265-266 kt (about
  265.2); EAS in 249-251 kt (about 250.1); TAS = 236.06 m/s = 458.86 kt
  exactly (M*a).
- Sea level 100 m/s CAS: EAS == TAS == 100.000 to < 0.001 kt (the
  density ratio is 1 and compressibility is evaluated at SL conditions,
  so the chain collapses to identity).
- 10,000 ft (3048 m), sigma = rho/rho0 = 0.7385: TAS 150.0 m/s -> EAS =
  150.0*sqrt(0.7385) = 128.9 m/s.
- Round trip: CAS -> M -> TAS -> CAS error < 1e-9 m/s.

If a value falls OUTSIDE its bound, your implementation has a bug: find
it before writing tests. Show your module's real outputs in the SKILL.md
worked example (do not invent them).

## Validation list (contract test must include)

- ValueError: altitude < 0; M < 0 or M >= 1; qc < 0; p <= 0; rho <= 0;
  tas < 0; cas < 0; eas < 0; qc/p >= 0.8929 in mach_from_impact_pressure
  (supersonic rejection); zero or multiple speed inputs to the chain.
- Monotonicity: CAS increases with qc; M increases with qc at fixed p;
  TAS at fixed CAS increases with altitude (lower density needs higher
  TAS for the same qc) - assert TAS(250 KCAS at 9144 m) > TAS(250 KCAS
  at sea level).
- EAS < CAS < TAS ordering at altitude for a subsonic cruise point
  (EAS = TAS*sqrt(rho/rho0) < TAS; CAS < TAS because the compressible
  inversion yields M from a lower static pressure, giving a higher TAS
  than the CAS value in m/s at altitude).
- Sea-level identity CAS == EAS == TAS within 1e-3 kt.
- Round trip identities at 3 altitudes (0, 3048, 9144 m): CAS->TAS->CAS
  and TAS->CAS->TAS error < 1e-9 m/s; EAS<->TAS round trip exact to
  1e-9.
- Determinism: no RNG, identical floats run-to-run.
- Chain dict contains exactly the documented keys; exactly-one-input
  rule enforced.

## Corpus fragment (eval/hit1-wave32-airspeed-conversion.yaml)

Query 1 (copy verbatim):
  "convert 250 knots calibrated airspeed to true airspeed and Mach at 30000 feet pressure altitude using the compressible impact-pressure inversion and the ISA speed of sound"
  intent: "cross-cutting; calibrated to true airspeed conversion at altitude"
  expected_skill: "cross-cutting/units-atmos/airspeed-conversion"
Query 2 (copy verbatim):
  "determine the equivalent airspeed and calibrated airspeed from a true airspeed of 236 meters per second at 11000 meters altitude with the airspeed-indicator compressibility correction"
  intent: "cross-cutting; true to equivalent and calibrated airspeed chain"
  expected_skill: "cross-cutting/units-atmos/airspeed-conversion"
Task ids: w32-airspeed-conversion-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must convert airspeeds through the
compressibility-corrected air-data chain:" and include the outputs listed
in the Claim. First tag: airspeed-conversion. Additional tags ONLY:
calibrated-airspeed, equivalent-airspeed, true-airspeed, mach-airspeed,
impact-pressure, airspeed-indicator (see tag list below; do not add
others). NEVER single generic words (airspeed, speed, conversion,
atmosphere). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): position-error-calibration,
tower fly-by, trailing cone, PEC curve, IAS (indicated airspeed belongs
to the FTO PEC leaf; this leaf starts from CALIBRATED airspeed or qc);
Prandtl-Glauert, Karman-Tsien, coefficient correction, transonic
similarity (aerodynamics compressibility-coefficient territory);
pressure altitude to geometric altitude conversion (unit-conversion);
temperature/pressure/density AT altitude output (isa-atmosphere owns the
state leaf; here the ISA state is internal to the chain). You may say
"compressibility correction" ONLY as "airspeed-indicator compressibility
correction" - never as a bare phrase.

Tags: [airspeed-conversion, calibrated-airspeed, equivalent-airspeed,
true-airspeed, mach-airspeed, impact-pressure, airspeed-indicator]

Sibling-citation lines for Related leaves: isa-atmosphere,
unit-conversion, dimensional-analysis (units-atmos pack),
flight-test-operations/planning/position-error-calibration and
flight-test-operations/performance/level-acceleration-test (consumers
that embed one chain leg), aerodynamics/high-speed/transonic-similarity
(the COEFFICIENT correction sibling that must not be confused).

Ledger Standard: naca-tr-824.
