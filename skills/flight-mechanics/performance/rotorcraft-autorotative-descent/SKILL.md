---
name: rotorcraft-autorotative-descent
description: "Use when you must estimate the power-off autorotative descent performance of a single-rotor helicopter: the energy-method sink rate from the minimum level-flight power and the weight, the empirical minimum descent rate from the Talbot-Schoers correlation of NASA TM 78452 (public domain), its equivalent power-based entry, and the feet-per-minute conversion. Produces the energy-method sink rate, the empirical minimum descent rate and the power-to-weight ratio entry that gate an autorotative descent assessment after engine failure. Trigger: rotorcraft autorotative descent, autorotative descent rate, power-off descent, minimum descent rate, rotor energy balance, engine failure descent, descent rate estimate."
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
  tags: [rotorcraft-autorotative-descent, autorotative-descent, power-off-descent, minimum-descent-rate, rotor-energy-balance, engine-failure-descent, descent-rate-estimate]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Autorotative Descent (flight-mechanics/performance/rotorcraft-autorotative-descent)

Use when you must estimate the power-off autorotative descent
performance of a single-rotor helicopter after engine failure: the
descent rate that the airframe reaches in a steady autorotative glide,
before any flare. This leaf pairs with
flight-mechanics/performance/rotorcraft-hover-performance (which owns
the hover power terms at zero rate), with
flight-mechanics/performance/rotorcraft-vertical-climb-performance (the
climb-only momentum leaf that does not descend) and with
flight-mechanics/performance/rotorcraft-forward-flight-performance (the
speed-dependent level-flight power split whose minimum feeds this
energy method). It implements the empirical energy method in pure
Python, stdlib only.

Context: the wave-31 review declined a momentum-theory autorotation
model because momentum theory is inapplicable in the vertical-descent
vortex-ring and windmill transition range (Leishman receipts). This
leaf is the empirical reopen: it never evaluates momentum theory in
descent and uses the energy balance W*V = P_min together with the
flight-test-validated empirical correlation of NASA TM 78452 (Talbot
and Schroers 1978, "A Simple Method for Estimating Minimum
Autorotative Descent Rate of Single Rotor Helicopters", NTRS
19780012170, public domain). The correlation is a least-squares fit
through measured minimum-descent-rate data of multiple single-rotor
helicopters and is deterministic with pinned coefficients.

## Domain quick reference

All quantities are SI (N, W, m/s). Module constants are the
public-domain NASA values: M0_TALBOT_MPS = 2.30 m/s (intercept),
M1_TALBOT = 0.66 (slope), G0 = 9.80665 m/s^2.

- Energy method (the paper's simple method): V = P_min / W follows from
  the steady-descent energy balance W*V = P_min, where P_min is the
  minimum level-flight power and W the weight. The paper documents that
  this overestimates the measured minimum descent rate.
- Empirical correlation (NASA TM 78452 eq. 14): V_est = M1_TALBOT *
  OmegaR * (C_PMIN / C_T) + M0_TALBOT_MPS, with OmegaR the rotor tip
  speed and C_PMIN / C_T the minimum power coefficient over thrust
  coefficient ratio.
- Power-based entry: in level flight T = W, so OmegaR * C_PMIN / C_T =
  P_min / T = P_min / W and V_est = M1_TALBOT * P_min / W +
  M0_TALBOT_MPS. The tip speed cancels in level flight but is still
  validated as an input for dimensional consistency.
- Unit conversion: ft/min = m/s * 60.0 / 0.3048, so 8.233 m/s converts
  to about 1621 ft/min, inside the published single-rotor measured
  minimum-descent band of roughly 1500-2000 ft/min.
- Validity: steady minimum-rate autorotative glide of a single main
  rotor helicopter; not the vortex-ring vertical-descent regime.
- Scope: this leaf never evaluates momentum theory in descent, does not
  model vortex-ring state or vertical zero-airspeed descent, and does
  not cover fixed-wing spin autorotation (the stalled-wing
  autorotative band is owned by
  flight-mechanics/stability-control/spin-recovery).

## Workflow

1. Fix the operating point: weight W (N), minimum level-flight power
   P_min (W), rotor tip speed OmegaR (m/s). P_min comes from the level
   flight power curve, e.g. the output of the
   rotorcraft-forward-flight-performance leaf.
2. Get the energy-balance sink rate with energy_method_sink_rate(P_min,
   W) = P_min / W. Treat this as the conservative upper estimate.
3. Get the empirical estimate with
   talbot_min_descent_rate_from_power(P_min, W, OmegaR); the power
   entry is valid because T = W in level flight.
4. When power coefficients are on hand, cross-check with
   talbot_min_descent_rate_mps(cp_min, c_t, OmegaR); both entries must
   agree to 1e-9.
5. Bundle the assessment with autorotative_descent_assessment(W, P_min,
   OmegaR): it returns energy_method_sink_rate_mps,
   talbot_min_descent_rate_mps, talbot_min_descent_rate_ft_per_min,
   power_to_weight_ratio_mps and the fixed validity_note.
6. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_autorotative_descent.py.

## Worked example

UH-1H-scale helicopter: W = 42270 N, P_min = 380000 W, rotor tip speed
OmegaR = 208 m/s. Real module outputs:

- energy_method_sink_rate(380000, 42270) = 8.9898 m/s, within the
  8.5-9.5 m/s bound and equal to the power-to-weight ratio
  380000/42270 m/s.
- talbot_min_descent_rate_from_power(380000, 42270, 208) = 8.2333 m/s,
  within the 7.5-9.0 m/s bound.
- talbot_min_descent_rate_ft_per_min = 1620.7 ft/min, about 1621 ft/min
  (m/s * 60 / 0.3048).
- Cross-entry consistency: the power entry and the coefficient entry
  talbot_min_descent_rate_mps(cp_min, 1.0, 208) with cp_min = P_min /
  (W * OmegaR) agree to 1.8e-15, below the 1e-9 threshold.
- The empirical estimate 8.2333 m/s sits below the energy-balance
  estimate 8.9898 m/s, as expected: the correlation intercept of
  2.30 m/s scales the pure energy balance down to the measured
  minimum-descent band.

## Verification

- Confirm energy_method_sink_rate(380000, 42270) returns 8.9898 m/s and
  that talbot_min_descent_rate_from_power(380000, 42270, 208) returns
  8.2333 m/s, with the empirical value below the energy value for the
  worked case.
- Confirm the ft/min conversion identity: talbot_min_descent_rate_ft_per_min
  equals talbot_min_descent_rate_mps * 60.0 / 0.3048, and 8.233 m/s
  converts to about 1621 ft/min.
- Confirm the cross-entry identity: talbot_min_descent_rate_from_power
  equals talbot_min_descent_rate_mps with cp_min / c_t = P_min / (W *
  OmegaR) to 1e-9.
- Confirm every non-positive weight, power and tip speed, c_t <= 0 and
  negative cp_min raises ValueError, and that the assessment dictionary
  contains exactly the five documented keys with the fixed validity_note.
- Confirm determinism: identical inputs give identical floats run to
  run (no RNG).
- Run the contract test offline: python3
  scripts/test_rotorcraft_autorotative_descent.py (34 tests,
  deterministic).

## Pitfalls

- Quoting the energy-balance sink rate as the predicted descent rate:
  P_min/W overestimates the measured minimum descent rate by design (the
  paper documents it), so treat energy_method_sink_rate as the conservative
  upper bound and the Talbot correlation as the estimate.
- Applying the correlation outside its validity: it is fit to steady
  minimum-rate autorotative glide of single main-rotor helicopters and is
  not valid in the vortex-ring vertical-descent regime or for fixed-wing
  autorotation (spin recovery owns that band).
- Using the power entry without level flight: the power-based entry relies
  on T = W in level flight, so P_min must be a level-flight minimum power; a
  power from another flight state breaks the OmegaR*C_PMIN/C_T = P_min/W
  identity.
- Assuming the coefficient entry needs c_t = 1.0 only: the two entries agree
  to 1e-9 only when cp_min/c_t = P_min/(W*OmegaR); passing an arbitrary
  cp_min with c_t = 1.0 silently violates the cross-entry identity.
- Unit slips: all inputs are SI (W in N, P_min in W, OmegaR in m/s) and the
  ft/min output is m/s * 60 / 0.3048; mixing knots or kg-force shifts the
  sink rate off the measured 1500-2000 ft/min band.
- Non-positive weight, power or tip speed (and c_t <= 0, negative cp_min)
  raise ValueError by contract.

## Related leaves

- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  the climb-only momentum leaf that does not descend.
- flight-mechanics/performance/rotorcraft-hover-performance: the hover
  state at zero descent rate.
- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the level-flight power split that supplies P_min.
- flight-mechanics/stability-control/spin-recovery: fixed-wing
  autorotation is a different regime.
- flight-test-operations/performance/rotorcraft-performance-flight-test:
  flight-test reduction of rotorcraft performance, not to be confused
  with this analytic estimate.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_autorotative_descent.py

The test covers the UH-1H-scale worked example (energy sink rate within
8.5-9.5 m/s, empirical rate within 7.5-9.0 m/s and about 1621 ft/min),
the empirical-below-energy ordering for the worked case, the cross-entry
consistency of the power-based and coefficient-based correlation entries
to 1e-9, the exact assessment dictionary keys and fixed validity note,
the pinned module constants (M0 = 2.30 m/s, M1 = 0.66, G0 = 9.80665),
determinism run to run, and ValueError rejection of non-positive
weight, power, tip speed, c_t and negative cp_min.

## Compliance

- Standards referenced, not reproduced: FAR-29 is named reference-only
  per standards-map.yaml. NASA TM 78452 (public domain, NTRS
  19780012170) is named in the body with its energy method and
  correlation coefficients; the relations above are summary-only
  standard engineering methodology, not reproduced text.
- compliance: STANDARDS-REF, gated: false.
