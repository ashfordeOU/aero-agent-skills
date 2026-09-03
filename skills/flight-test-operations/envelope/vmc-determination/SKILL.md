---
name: vmc-determination
description: "Use when you must predict and check the minimum control speed Vmc of a multi-engine airplane for the engine-inoperative flight test: identify the critical engine from the engine-out yawing moment geometry, build the asymmetric yawing moment from the operating-engine thrust at the failed engine lateral arm plus the windmilling drag contribution, solve the rudder authority limited speed, apply the rudder pedal force criterion with the boost factor against the 150 lbf pedal limit, and apply the stall protection guard on the reference stall speed. Produces the predicted Vmc in m/s and knots, the governing limit label, the asymmetric moment model, and the flight test go verdict. Trigger: minimum control speed, Vmc determination, critical engine, rudder pedal force, asymmetric yawing moment, engine inoperative flight test, 150 lbf pedal limit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: envelope
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [vmc-determination, minimum-control-speed, critical-engine, rudder-pedal-force, asymmetric-yawing-moment, engine-inoperative-flight-test, rudder-authority, windmilling-drag]
  version: 0.1.0
  author: AeroSkills
---

# Minimum Control Speed Vmc (flight-test-operations/envelope/vmc-determination)

Use when the task is the Vmc prediction and demonstration check for a
multi-engine airplane in the spirit of the FAR/CS 25.149
minimum-control-speed method, summary-only. This leaf identifies the
critical engine from the engine-out yawing-moment geometry, builds the
asymmetric yawing moment (operating-engine thrust at the failed-engine
lateral arm plus the failed-engine windmilling drag contribution),
computes the rudder deflection required to balance it at each airspeed,
solves the authority-limited speed where the required deflection
reaches the rudder limit, evaluates the rudder pedal-force criterion at
that speed with the boost factor, applies the stall-protection guard on
the reference stall speed, and returns the predicted Vmc with the
governing-limit label and the flight-test go verdict. Model
simplifications: first-order yaw balance without sideslip coupling,
sea-level density for the dynamic pressure, operating engines at
maximum takeoff thrust. It pairs with flight-test-operations v-speeds
(Vmc sits beside the V-speed set), flight-mechanics oei-climb-gradient
(the engine-out performance sibling), and vehicle-design
control-surface-sizing (the rudder sizing sibling).

## Domain quick reference

- Critical engine: the engine whose failure gives the largest adverse
  yawing moment, ranked by the |thrust * y_m| product of its lateral
  arm about the CG; ties resolve to the lower index.
- Asymmetric yawing moment: N_asym = T_op * y_fail + 0.5 * RHO_SL *
  V^2 * S_f * Cd * y_fail, where T_op is the sum of the operating
  (non-failed) engine thrusts and y_fail the signed lateral arm of the
  failed engine.
- Rudder deflection required: delta = |N_asym| / (q * S_v * l_v *
  C_Lv_delta_r), with q = 0.5 * RHO_SL * V^2, S_v the fin area, l_v the
  CG-to-fin arm and C_Lv_delta_r the effective fin lift slope per
  rudder deflection (includes the rudder-to-fin area ratio).
- Rudder-authority limit: the speed where delta reaches delta_r_max.
  Closed form q* = T_op * |y_fail| / (S_v * l_v * C_Lv_delta_r *
  delta_r_max_rad - S_f * Cd * |y_fail|); V_auth = sqrt(2 * q* /
  RHO_SL). If the denominator is not positive the configuration is
  never authority limited (V_auth = None).
- Rudder pedal force: F = q * S_r * c_r * |C_h_delta_r| *
  min(delta_req, delta_r_max_rad) * boost_factor / pedal_arm_m, with
  C_h_delta_r the hinge moment coefficient per radian (magnitude used,
  negative for a restoring hinge), S_r and c_r the rudder area and
  chord, and the boost factor scaling felt force (1.0 manual, smaller
  for power-boosted systems).
- Pedal-force limit: F_lim = 667 N (150 lbf criterion of the test
  condition, paraphrased). The force-limited speed V_force follows from
  the quadratic F(V) at the deflection limit, V_force = sqrt(2 * q_F /
  RHO_SL).
- Vmc: vmc = max(V_auth, V_force); the governing limit label is
  "rudder-authority" when V_auth >= V_force else "pedal-force".
- Stall guard: stall_guard_speed = stall_guard * v_s1g (default guard
  factor 1.05). When vmc falls below it the flight test must
  demonstrate above the guard; vmc is reported unchanged with the
  guard_verdict "stall-guard-governs".
- Units are SI: N, m, m/s, rad, deg, N m; knots = m/s * 1.94384.
- FAR/CS 25.149 frames the minimum-control-speed test condition; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Collect the engine layout: engines as a list of {thrust_N, y_m}
   dicts (y_m positive on the right), the failed engine index, and the
   failed-engine windmilling drag area S_f * Cd at speed.
2. Confirm the critical engine with critical_engine_index; the failed
   engine is usually the critical one (the leaf reports whichever index
   is given).
3. Build the geometry set: S_v, l_v, C_Lv_delta_r, delta_r_max, S_r,
   c_r, C_h_delta_r, pedal arm, boost factor, v_s1g, and the pedal
   force limit and stall guard defaults.
4. Compute the authority-limited speed with authority_limited_speed and
   the force-limited speed from the pedal-force quadratic (inside
   vmc_predict as v_force_m_s).
5. Run the full prediction with vmc_predict and read vmc_m_s, vmc_kt,
   governing, force_at_vmc_N, force_ok, guard_verdict and
   flight_test_go.
6. Inspect the asymmetric moment model at Vmc with
   asymmetric_yaw_moment_Nm for the moment value carried by the
   rudder.
7. If force_ok is False or guard_verdict is "stall-guard-governs", the
   engine-inoperative flight test cannot clear the Vmc demonstration as
   configured; revisit the boost factor or the demonstration speed.
8. Confirm the deterministic checks with the contract test
   scripts/test_vmc_determination.py.

## Worked example

Twin jet, 65000 N engines at y = +-8.0 m, S_v 25 m^2, l_v 16 m, rudder
effectiveness 0.8/rad, delta_r_max 30 deg (0.52360 rad), S_r 8.5 m^2,
c_r 1.3 m, C_h_delta_r -0.045, pedal arm 0.35 m, boost factor 0.15
(power-boosted), v_s1g 66 m/s, windmilling drag neglected.

- Critical engine: index 0 (tie, lower index).
- T_op * y_fail = 65000 * 8.0 = 520000 N m.
- Authority limit: q* = 520000 / (25 * 16 * 0.8 * 0.52360) = 3103.5 Pa,
  V_auth = sqrt(2 * 3103.5 / 1.225) = 71.18 m/s.
- Force limit: q_F = 667.0 * 0.35 / (8.5 * 1.3 * 0.045 * 0.52360 *
  0.15) = 5977.6 Pa, V_force = sqrt(2 * 5977.6 / 1.225) = 98.79 m/s.
- Vmc = max(71.18, 98.79) = 98.79 m/s = 192.0 kt, governing
  "pedal-force".
- Pedal force at Vmc: delta_req = 520000 / (5977.6 * 320) = 0.2718 rad
  (below the limit), F = 346.2 N, force_ok True (below 667 N).
- Stall guard: 1.05 * 66 = 69.3 m/s below Vmc, guard_verdict
  "stall-guard-ok"; flight_test_go True.
- Manual-rudder case (boost 1.0): force at V_auth 71.18 m/s reaches
  2308.6 N above the 667 N limit, force_ok False and flight_test_go
  False; V_force drops to 38.26 m/s so Vmc = 71.18 m/s governed by
  "rudder-authority".
- Windmilling variant (S_f * Cd = 1.5 m^2): the denominator shrinks and
  V_auth rises to 73.87 m/s; the pedal-force limit still binds at
  98.79 m/s.

## Verification

- Confirm vmc_predict on the worked twin returns vmc 98.79 m/s within
  0.05, vmc_kt 192.0 within 0.2, v_auth_m_s 71.18 within 0.05, and
  governing "pedal-force".
- Confirm force_at_vmc_N is within 2 N of 346.2, force_ok True, and
  the manual-rudder case (boost 1.0) gives 2308.6 N within 5 with
  force_ok False and flight_test_go False.
- Confirm the windmilling case (1.5 m^2) gives v_auth_m_s 73.87 within
  0.1 and above the no-windmilling 71.18.
- Confirm every non-physical input raises ValueError: empty engine
  list, thrust_N <= 0, negative windmilling area, S_v <= 0, l_v <= 0,
  effectiveness <= 0, delta_r_max outside (0, 60] deg, S_r <= 0,
  c_r <= 0, zero hinge moment coefficient, pedal arm <= 0, boost
  factor outside (0, 1], v_s1g <= 0, out-of-range failed index, and
  non-positive airspeed for the moment and deflection functions.
- Run the contract test offline: python3
  scripts/test_vmc_determination.py (46 tests, deterministic).

## Related leaves

- flight-test-operations/envelope/v-speeds: the V-speed set beside
  which the Vmc result sits.
- flight-mechanics/performance/oei-climb-gradient: the engine-out
  climb performance sibling; this leaf does not compute climb
  gradients.
- vehicle-design/sizing/control-surface-sizing: sizing the rudder area
  from the yaw moment requirement, upstream of this check.
- flight-mechanics/stability-control/control-surface-effectiveness:
  elevator hinge moments and stick force, out of scope here.
- flight-test-operations/envelope/stall-characteristics-testing:
  stall demonstration testing behind the stall-protection guard.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_vmc_determination.py

The test covers the critical-engine ranking (tie, outboard, left-side
asymmetric and magnitude cases), the asymmetric yawing moment values
including the windmilling contribution and the negative-side failure,
the required deflection at fixed speeds with the inverse-q scaling and
the deflection-to-moment round trip, the authority-limited and
force-limited closed forms against the worked anchors (71.18 and
98.79 m/s), the Vmc value and governing label, the pedal force at Vmc
(346.2 N boosted, 2308.6 N manual), the force-ok and flight-test-go
flags, the stall-guard verdicts, the knots conversion (192.0 kt), the
windmilling shift of V_auth to 73.87 m/s, and ValueError rejection of
every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR/CS 25.149 frames the
  minimum-control-speed method and its 150 lbf pedal-force test
  condition; the relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
