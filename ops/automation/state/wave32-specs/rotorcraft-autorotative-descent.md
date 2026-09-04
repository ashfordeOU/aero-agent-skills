# Wave-32 leaf spec: rotorcraft-autorotative-descent (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-autorotative-descent/
- Pack: performance. Rotorcraft siblings: rotorcraft-hover-performance,
  rotorcraft-vertical-climb-performance, rotorcraft-forward-flight-
  performance (power leaves), rotorcraft-tail-rotor-sizing.
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Estimate the power-off autorotative descent performance of a single-
rotor helicopter with the empirical energy method: the classical
energy-balance sink rate from the minimum level-flight power and the
weight, and the empirical minimum-autorotative-descent-rate estimate
from the Talbot-Schoers correlation of NASA TM 78452 (public domain),
including the equivalent power-based entry form. Produces the energy-
method sink rate, the empirical minimum descent rate and the
power-to-thrust ratio entry that gate an autorotative descent
assessment after engine failure.

CONTEXT (must be stated in the SKILL body): the wave-31 review
declined a MOMENTUM-THEORY autorotation model because momentum theory
is inapplicable in the vertical-descent vortex-ring/windmill
transition range (Leishman receipts). THIS leaf is the empirical
reopen: it never evaluates momentum theory in descent; it uses the
energy balance W*V = P_min and the flight-test-validated empirical
correlation of NASA TM 78452 (Talbot and Schroers 1978, "A Simple
Method for Estimating Minimum Autorotative Descent Rate of Single
Rotor Helicopters", NTRS 19780012170, public domain). The correlation
is a least-squares fit through measured minimum-descent-rate data of
multiple single-rotor helicopters and is deterministic with pinned
coefficients.

Does NOT do: fixed-wing spin autorotation (flight-mechanics/stability-
control/spin-recovery owns the stalled-wing autorotative band);
vertical climb or hover power (rotorcraft-vertical-climb-performance,
rotorcraft-hover-performance own momentum-theory power); forward
flight power (rotorcraft-forward-flight-performance); measured-power
flight test reduction (flight-test-operations/performance/
rotorcraft-performance-flight-test); vortex-ring state modeling,
vertical zero-airspeed descent, or the momentum-theory descent
solution (explicitly out of scope per the wave-31 receipt).

## Model (implement exactly)

Module constants (NASA TM 78452 eq. 14; public-domain NASA values):
- M0_TALBOT_MPS = 2.30 (m/s intercept of the empirical correlation).
- M1_TALBOT = 0.66 (slope of the empirical correlation).
- G0 = 9.80665 (m/s2).

Functions (pure stdlib):

- energy_method_sink_rate(p_min_level_w, weight_n) -> V = p_min_w /
  weight_n [m/s]. The classical energy balance W*V = P_min for steady
  descent (the paper's simple method), documented to overestimate the
  measured minimum descent rate. ValueErrors on non-positive inputs.
- talbot_min_descent_rate_mps(cp_min, c_t, tip_speed_mps) ->
  V_est = M1_TALBOT * tip_speed_mps * (cp_min / c_t) + M0_TALBOT.
  ValueErrors if c_t <= 0 or tip_speed_mps <= 0 or cp_min < 0.
- talbot_min_descent_rate_from_power(p_min_level_w, weight_n,
  tip_speed_mps) -> V_est = M1_TALBOT * tip_speed_mps *
  (p_min_level_w / (weight_n * tip_speed_mps)) + M0_TALBOT =
  M1_TALBOT * p_min_level_w / weight_n + M0_TALBOT, valid because in
  level flight T = W so OmegaR * C_PMIN / C_T = P_min / T =
  P_min / W.  ValueErrors on non-positive weight, tip speed or power.
- autorotative_descent_assessment(weight_n, p_min_level_w,
  tip_speed_mps) -> dict {energy_method_sink_rate_mps,
  talbot_min_descent_rate_mps, talbot_min_descent_rate_ft_per_min,
  power_to_weight_ratio_mps (p_min_level_w / weight_n),
  validity_note}.  ValueErrors propagate.  validity_note is the fixed
  string: "steady minimum-rate autorotative glide of a single main
  rotor helicopter; not the vortex-ring vertical-descent regime".

ALL functions deterministic, no RNG, stdlib only.

## Worked example

UH-1H-scale helicopter: weight W = 42 270 N, minimum level-flight
power P_min = 380 000 W, rotor tip speed OmegaR = 208 m/s.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds:
- energy_method_sink_rate in 8.5-9.5 m/s (about 8.99).
- power_to_weight_ratio_mps = 380000/42270 about 8.99 m/s.
- talbot_min_descent_rate_mps in 7.5-9.0 m/s (about 8.23) and in
  ft/min about 1620 (published single-rotor measured minimum
  autorotative descent band roughly 1500-2000 ft/min).
- talbot_min_descent_rate_from_power equals the cp/c_t entry to float
  precision.
- talbot_min_descent_rate_ft_per_min = mps * 60.0 / 0.3048.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive weight, power, tip speed, c_t; negative
  cp_min.
- Cross-entry consistency: talbot_min_descent_rate_from_power(W, P,
  OmegaR) equals talbot_min_descent_rate_mps(cp_min, c_t, OmegaR) with
  cp_min/c_t = P/(W*OmegaR) to 1e-9.
- Magnitude bounds from the worked example (energy method above the
  empirical estimate; the correlation's intercept 2.30 m/s makes the
  empirical value lower than the pure energy balance for typical
  helicopters - assert V_empirical < V_energy for the worked case).
- ft/min conversion: 8.233 m/s * 60 / 0.3048 about 1621 ft/min.
- Determinism: no RNG, identical floats run-to-run.
- Convenience dict contains exactly the documented keys and the
  fixed validity_note.

## Corpus fragment (eval/hit1-wave32-rotorcraft-autorotative-descent.yaml)

Query 1 (copy verbatim):
  "estimate the minimum autorotative descent rate of a single-rotor helicopter after engine failure with the empirical Talbot correlation from the minimum level power and the weight"
  intent: "flight-mechanics; rotorcraft empirical autorotative minimum descent rate"
  expected_skill: "flight-mechanics/performance/rotorcraft-autorotative-descent"
Query 2 (copy verbatim):
  "compute the power-off sink rate of a helicopter in the autorotative glide by the energy balance method and convert the empirical descent rate to feet per minute"
  intent: "flight-mechanics; rotorcraft autorotative descent energy balance and unit conversion"
  expected_skill: "flight-mechanics/performance/rotorcraft-autorotative-descent"
Task ids: w32-rotorcraft-autorotative-descent-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the power-off
autorotative descent performance of a single-rotor helicopter:" and
include the outputs in the Claim. First tag:
rotorcraft-autorotative-descent. Additional tags ONLY:
autorotative-descent, power-off-descent, minimum-descent-rate,
rotor-energy-balance, engine-failure-descent, descent-rate-estimate.
NEVER single generic words (autorotation, descent, rotorcraft, power,
helicopter, rate). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): spin, flat spin, stall
penetration, post-stall, incipient (spin-recovery owns the FIXED-WING
autorotative band); momentum theory, induced velocity, climb induced
velocity, vortex-ring state solution (rotorcraft-vertical-climb and
the wave-31 decline receipt - this leaf is the empirical method);
hover, figure of merit (rotorcraft-hover-performance); measured,
flight test reduction (rotorcraft-performance-flight-test). You may
reference "energy method" and "empirical correlation", never
"momentum theory in descent".

Tags: [rotorcraft-autorotative-descent, autorotative-descent,
power-off-descent, minimum-descent-rate, rotor-energy-balance,
engine-failure-descent, descent-rate-estimate]

Sibling-citation lines for Related leaves:
flight-mechanics/performance/rotorcraft-vertical-climb-performance
(the climb-only momentum leaf that does not descend),
flight-mechanics/performance/rotorcraft-hover-performance,
flight-mechanics/stability-control/spin-recovery (fixed-wing
autorotation is a different regime),
flight-test-operations/performance/rotorcraft-performance-flight-test.
References: NASA TM 78452 (public domain) named in the body with the
energy method and correlation coefficients.

Ledger Standard: far-29.
