# Wave-33 leaf spec: density-altitude (cross-cutting, units-atmos pack)

- Path: skills/cross-cutting/units-atmos/density-altitude/
- Pack: units-atmos. Sibling scope check: isa-atmosphere owns the
  FORWARD ISA state (T/p/rho at altitude; getters + sea-level anchor);
  unit-conversion owns pressure_altitude_m (inverse pressure) +
  geometric/geopotential conversion; airspeed-conversion takes pressure
  altitude as INPUT and owns CAS/EAS/TAS/Mach; temperature-conversion
  owns unit scaling. Zero "density altitude" content in cross-cutting;
  the duplication proof: flight-test-operations/performance/climb-
  performance-flight-test implements its OWN density_altitude_ft with
  duplicated ISA helpers - the exact foundation gap this leaf fills.
  This leaf owns the inverse-density step (pressure altitude + OAT ->
  density altitude on a non-standard day).
- Standards id: ecss (reference-only; same anchor as isa-atmosphere
  convention per the probe - verify against the sibling; if isa uses a
  different id, match it. Check skills/cross-cutting/units-atmos/
  isa-atmosphere/SKILL.md standards block.)
  Ledger Standard: ecss.
- Family: cross-cutting

## Claim

Compute the density altitude from the pressure altitude and the outside
air temperature on a non-standard day: the ISA deviation, the
density ratio sigma from the pressure ratio and the temperature ratio,
and the density altitude via the troposphere closed-form inverse, with
the stratosphere branch. Produces the density altitude in meters and
feet for hot-day and cold-day takeoff and performance checks.

Does NOT do: forward ISA state at altitude (isa-atmosphere); pressure
altitude from static pressure (unit-conversion owns pressure_altitude_m
and the geometric/geopotential pair); CAS/EAS/TAS/Mach conversion
(airspeed-conversion); temperature unit conversion
(temperature-conversion).

## Model (implement exactly)

Conventions: standard sea level T0 = 288.15 K, lapse L = 0.0065 K/m,
tropopause 11000 m (ISA), exponent g/(R L) = 5.25588... (use the exact
g = 9.80665, R = 287.0 J/kg/K; document the constants). Troposphere
density ratio from hydrostatics + perfect gas:
sigma(h) = (1 - L h / T0)^(g/(R L) - 1) = (1 - L h / T0)^4.25588.
Inverse: h_rho = (T0 / L) (1 - sigma^(R L / g)) with
sigma = (p(hp)/p0) (T0 / T_oat) = delta(hp) * T0 / T_oat.
delta(hp) = p_ISA(hp)/p0 via the forward ISA pressure (troposphere or
stratosphere branch). The T_ISA(hp) function gives the ISA temperature
at the pressure altitude; the deviation is DeltaT = T_oat - T_ISA(hp).

Functions (pure stdlib):

- isa_temperature_k(hp_m) -> T_ISA at pressure altitude (troposphere
  linear, stratosphere 216.65 K).
- isa_pressure_ratio(hp_m) -> delta = p/p0 (troposphere power law,
  stratosphere exponential from the tropopause state).
- isa_deviation_k(hp_m, oat_k) -> oat_k - isa_temperature_k(hp_m).
- density_ratio_from_pressure_temperature(p_pa, t_k) ->
  (p/p0) * (T0/t_k).
- density_altitude_m(hp_m, oat_k) -> the inverse-density altitude:
  sigma = isa_pressure_ratio(hp_m) * T0 / oat_k; if sigma corresponds
  to the troposphere (density altitude <= 11000 m, equivalently
  sigma >= sigma_tropopause), h_rho = (T0/L)(1 - sigma^(R L/g));
  else the stratosphere closed form (exponential inverse: h_rho =
  11000 - (R T_strat/g) ln(sigma/sigma_trop)). Verify the branch and
  both closed forms at prep.
- density_altitude_ft(hp_ft, oat_deg_c) -> wrapper: hp_m = hp_ft *
  0.3048; oat_k = oat_deg_c + 273.15; returns h_rho / 0.3048.
- density_altitude_summary(hp_m, oat_k) -> dict {hp_m, oat_k,
  isa_temp_k, deviation_k, density_ratio, density_altitude_m,
  density_altitude_ft}.

## Worked example

ISA day: identity h_rho = h_p. Hot day: sea level +15 C. 10000 ft
pressure altitude with +10 C and -10 C.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep; closed form vs
200-iteration bisection agree to ~1e-9):
- ISA identity: density_altitude_m(0, 288.15) = 0.00 m; at hp = 3048 m
  (10000 ft) with the ISA temperature, h_rho about 3048.00 m (the
  identity holds to ~0.1 m at 10000 ft with the documented constants).
- Sea level +15 C: h_rho about 525.46 m = 1723.94 ft.
- 10000 ft +10 C: about 11159.44 ft (warm day RAISES density
  altitude).
- 10000 ft -10 C: about 8785.93 ft (cold day LOWERS it).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: hp_m < -1000 (allow small negative geopotential; reject
  nonsense), oat_k <= 0.
- ISA identity: h_rho = h_p on the standard day at 0 m and 3048 m (to
  ~0.2 m).
- Monotonicity: at fixed hp, warmer OAT raises density altitude, colder
  lowers it; at fixed OAT, higher hp raises density altitude.
- Worked magnitudes: sea level +15 C about 525.46 m / 1723.94 ft;
  10000 ft +10 C about 11159 ft; -10 C about 8786 ft.
- Cross-check: the leaf's density_altitude_ft reproduces the domain
  precedent's bisection result for the climb-performance-flight-test
  example (if the numbers are accessible; otherwise assert the closed
  form against an internal bisection to 1e-6).
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-density-altitude.yaml)

Query 1 (copy verbatim):
  "compute the density altitude from the pressure altitude and the outside air temperature for a hot day takeoff performance check"
  intent: "cross-cutting; density altitude from pressure altitude and OAT on a non-standard day"
  expected_skill: "cross-cutting/units-atmos/density-altitude"
Query 2 (copy verbatim):
  "convert pressure altitude and oat to density altitude in feet on a non standard day for performance reduction"
  intent: "cross-cutting; pressure-altitude and OAT to density-altitude conversion"
  expected_skill: "cross-cutting/units-atmos/density-altitude"
Task ids: w33-density-altitude-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the density altitude
from the pressure altitude and the outside temperature:" and include
the outputs in the Claim. First tag: density-altitude. Additional tags
ONLY: non-standard-day, isa-deviation, hot-day-performance,
density-ratio, inverse-isa, performance-reduction. NEVER single generic
words (altitude, density, temperature, atmosphere, pressure, isa,
performance). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): lapse rate table, ISA
temperature profile getter (isa-atmosphere); calibrated airspeed,
equivalent airspeed, true airspeed, Mach, impact pressure
(airspeed-conversion); pressure altitude from static pressure
(unit-conversion). The tokens "density altitude", "non-standard day",
"ISA deviation" are this leaf's own.

Tags: [density-altitude, non-standard-day, isa-deviation,
hot-day-performance, density-ratio, inverse-isa,
performance-reduction]

Sibling-citation lines for Related leaves:
cross-cutting/units-atmos/isa-atmosphere (the forward ISA model this
leaf inverts),
cross-cutting/units-atmos/airspeed-conversion (takes pressure altitude
as input),
flight-test-operations/performance/climb-performance-flight-test (the
domain consumer that previously duplicated this function).

Ledger Standard: ecss.
