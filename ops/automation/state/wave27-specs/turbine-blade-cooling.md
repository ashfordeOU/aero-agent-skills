# Wave-27 leaf spec: turbine-blade-cooling (propulsion, axial-compressor pack)

- Path: skills/propulsion/axial-compressor/turbine-blade-cooling/
- Pack: axial-compressor (existing siblings: axial-compressor-stage,
  multi-stage-compressor, turbine-stage, compressor-map)
- Standards ids: far-33  (Ledger Standard: far-33)
- Family: propulsion

## Claim

Estimate the cooling flow required to protect a gas turbine blade row:
from the hot gas temperature, the allowable blade metal temperature,
and the coolant supply temperature, compute the cooling effectiveness,
convert it into a required coolant-to-gas mass flow ratio with a
documented simplified energy balance, check the ratio against a
practical bleed limit, and estimate the metal temperature achieved
with a film-cooling effectiveness improvement. Produces the cooling
effectiveness, the required coolant fraction, the bleed-limit verdict,
and the achievable metal temperature that gate turbine hot-section
cooling design.

Does NOT do: design the turbine stage velocity triangles, stage
loading, or blade row losses (turbine-stage owns the aerodynamic
design); compute the compressor map or bleed extraction thermodynamics
(compressor-map); or analyze the full engine cycle with cooling-air
thermodynamics (gas-turbine-cycle, real-cycle-effects in the
gas-turbine-cycle pack). This leaf is the heat-transfer cooling
effectiveness estimate only.

## Model (implement exactly)

Module constants (documented typicals):
- CP_RATIO = 1.0 (coolant and gas specific heat ratio, documented
  simplification),
- BLEED_LIMIT = 0.20 (practical coolant-to-gas limit for a blade row,
  documented typical),
- FILM_IMPROVEMENT = 0.15 (effectiveness gain available from film
  cooling at the leading edge, documented typical; the baseline model
  is internal convection only).

Inputs:
- t_gas_k (float, hot gas total temperature),
- t_metal_allow_k (float, allowable blade metal temperature),
- t_coolant_k (float, coolant supply temperature),
- film_cooling (bool, default False).

Functions:
- effectiveness(t_gas_k, t_metal_allow_k, t_coolant_k) -> float:
  phi = (t_gas - t_metal_allow) / (t_gas - t_coolant).
  ValueError when t_gas <= t_coolant or t_metal_allow >= t_gas or
  t_metal_allow <= t_coolant.
- coolant_fraction(phi) -> float: phi / (1 - phi) * CP_RATIO.
  (Documented simplified energy balance: the coolant heat capacity
  rate must offset the blade heat load implied by the effectiveness.)
- bleed_verdict(coolant_fraction) -> str: "within bleed limit" when
  fraction <= BLEED_LIMIT else "exceeds bleed limit".
- metal_temp_with_film(t_gas_k, t_coolant_k, phi_base, film_cooling)
  -> float: phi_eff = min(0.95, phi_base + FILM_IMPROVEMENT) when film
  else phi_base; Tm = t_gas - phi_eff * (t_gas - t_coolant).
- analyze(...) -> dict {effectiveness, coolant_fraction, verdict,
  metal_temp_k (with the requested film setting), margin_k =
  t_metal_allow - metal_temp}.

ValueError on the conditions in effectiveness() plus t_gas <= 0.

## Worked example

Case 1: t_gas 1500 K, allowable metal 1200 K, coolant 800 K.
- phi = (1500-1200)/(1500-800) = 300/700 = 0.4286 (assert within 1e-4),
- coolant_fraction = 0.4286/0.5714 = 0.75 (assert within 1e-3),
- verdict "exceeds bleed limit" (0.75 > 0.20) - assert.
- with film: phi_eff = 0.4286+0.15 = 0.5786; Tm = 1500 - 0.5786*700 =
  1095.0 K (assert within 1.0); margin +105 K.
Case 2: t_gas 1600, allowable 1250, coolant 900 (film True):
- phi = (1600-1250)/(1600-900) = 350/700 = 0.5 (assert),
- fraction 1.0 -> exceeds bleed limit,
- phi_eff = 0.65; Tm = 1600 - 0.65*700 = 1145 K (assert within 1.0).
Case 3: t_gas 1600, allowable 1350, coolant 900:
- phi = 250/700 = 0.3571; fraction 0.5556 -> exceeds bleed limit.
Sensitivity: increasing t_metal_allow (or lowering t_gas) lowers the
required fraction; assert fraction falls below 0.2 for an allowable
within ~160 K of the gas temperature at coolant 800 (run the module
and assert the monotonic trend and the boundary crossing; record the
exact boundary metal temperature in the test header).
Keep at least 15 test methods (effectiveness, fractions, verdicts,
film metal temps, margins, ValueErrors).

## Corpus tasks (ids w27-turbine-blade-cooling-1/2)

Distinctive tokens: turbine blade cooling, cooling effectiveness,
coolant flow fraction, film cooling, allowable metal temperature,
coolant supply temperature, bleed limit, hot section cooling. Avoid:
stage loading, velocity triangle, degree of reaction (turbine-stage);
compressor map surge line (compressor-map); recuperator
(regenerative-cycle).

1. "estimate the coolant flow fraction needed for the first turbine
   blade row with 1500 K gas, 1200 K allowable metal, and 800 K
   coolant, and check it against the bleed limit"
2. "compute the film cooled metal temperature for the high pressure
   turbine blade: 1600 K gas, 1250 K allowable, 900 K coolant, and
   report the margin"

## SKILL body notes

Pair with turbine-stage (aero design of the same blade row) and
gas-turbine-cycle leaves (cycle impact of bleed). The effectiveness-
to-flow conversion and the film improvement constant are documented
simplified correlations for conceptual design; real cooling design
needs 3D conjugate heat transfer. Standards referenced (FAR-33
hot-section context) not reproduced.
