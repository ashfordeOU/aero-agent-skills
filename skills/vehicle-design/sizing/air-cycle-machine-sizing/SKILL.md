---
name: air-cycle-machine-sizing
description: 'Use when you must size the bootstrap air-cycle cooling pack thermodynamics for the ECS cooling load: compute the compressor exit state from the pack-inlet bleed condition, pressure ratio and isentropic efficiency, cool the discharge through the ram-air heat exchanger at a given effectiveness, expand through the cooling turbine to cabin pressure, close the two-wheel ACM shaft balance, and turn the turbine exit temperature into delivered cooling against the cabin design temperature. Produces compressor and turbine exit temperatures and pressures, heat-exchanger exit temperature, shaft powers, the balance verdict with work deficit or closing effectiveness, delivered cooling power versus the load and the required bleed flow. Trigger: air cycle machine, bootstrap air cycle, ACM shaft balance, cooling turbine exit, compressor exit state, heat exchanger effectiveness, required bleed flow, delivered cooling power.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: far-25
  reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags:
  - air-cycle-machine-sizing
  - bootstrap-air-cycle
  - acm-shaft-balance
  - cooling-turbine-exit
  - compressor-exit-state
  - heat-exchanger-effectiveness
  - required-bleed-flow
  - delivered-cooling-power
  version: 0.1.0
  author: AeroSkills
---

# Bootstrap Air Cycle Machine Sizing (vehicle-design/sizing/air-cycle-machine-sizing)

Use when the task is sizing the bootstrap air-cycle cooling pack
thermodynamics that sits inside the ECS, between the cabin heat load
and pack airflow of the environmental-control-sizing leaf and the bleed
supply of the bleed-air-system-sizing leaf: compress the pack-inlet
bleed, reject heat to the ram sink, expand through the cooling turbine
to cabin pressure, and check that the turbine on the shared shaft can
drive the compressor before quoting any delivered cooling. This leaf
implements the two-wheel bootstrap in pure Python, stdlib only. It
pairs with environmental-control-sizing for the cabin heat load and
pack airflow that demand the cooling, and with bleed-air-system-sizing
for the pack-inlet bleed condition after upstream conditioning.

## Domain quick reference

Perfect-gas dry air at constant cp. Stations: 1 = pack-inlet bleed, 2
= compressor exit, 3 = heat-exchanger exit (constant pressure, p3 =
p2), 4 = cooling turbine exit at cabin pressure p4 = p_cabin.

- Compressor exit: T2 = T1 * (1 + (pr_c^EXP - 1) / eta_c), p2 = p1 *
  pr_c, with EXP = (GAMMA - 1) / GAMMA, GAMMA = 1.4.
- Heat exchanger (NTU-style effectiveness, convention pinned): T3 =
  T2 - effectiveness * (T2 - t_sink). A cooling exchanger needs T2
  above the sink.
- Cooling turbine: pr_t = p3 / p4 is the design expansion ratio, p4 =
  p_cabin, and the leaf validates p3 / pr_t against p_cabin at REL_TOL
  1e-9; T4 = T3 * (1 - eta_t * (1 - (p4 / p3)^EXP)).
- Shaft powers: W_c = m_dot * CP_AIR * (T2 - T1),
  W_t = m_dot * CP_AIR * (T3 - T4), CP_AIR = 1005.0 J/(kg K).
- Shaft balance: balanced when W_t + BALANCE_TOL_W >= W_c
  (BALANCE_TOL_W = 1.0 W absorbs float noise); deficit_w =
  max(W_c - W_t, 0); power_ratio = W_t / W_c.
- Closure temperature: W_t = W_c requires the compressor delta-T to
  equal the turbine delta-T, so T3_req = (T2 - T1) / (eta_t * (1 -
  (p_cabin / p3)^EXP)), and the exchanger effectiveness that lands T3
  there is eff = (T2 - T3_req) / (T2 - t_sink).
- Delivered cooling: Q = m_dot * CP_AIR * (T_target - T4), signed W,
  positive only when the turbine exit is below the cabin design
  temperature; required bleed flow m_dot_req = q_load / (CP_AIR *
  (T_target - T4)).
- Units are SI throughout: Pa, K, kg/s, W.
- FAR 25.831 and the air-conditioning context frame the ECS design; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the pack-inlet bleed condition: p1, T1 and the bleed mass flow
   m_dot, the conditioned state delivered by the upstream precooler.
   A production bootstrap pack places a primary ram heat exchanger
   ahead of the pack compressor, so T1 is the precooled value and is
   never re-derived from the raw engine bleed temperature.
2. Compute the compressor exit state with compressor_exit(bleed_p1,
   bleed_t1, pr_c, eta_c), giving T2 and p2.
3. Cool the compressor discharge through the ram-air heat exchanger
   with heat_exchanger_exit(t2, effectiveness, t_sink), giving T3 at
   p3 = p2.
4. Expand through the cooling turbine to cabin pressure with
   turbine_exit(p3, t3, pr_t, eta_t, p_cabin), where pr_t = p3 /
   p_cabin and the pack discharges at p_cabin; get T4.
5. Close the ACM shaft balance with shaft_balance over
   compressor_power(m_dot, t1, t2) and turbine_power(m_dot, t3, t4):
   balanced True means the turbine drives the compressor and the pack
   bootstraps.
6. Resolve an open balance through the closure temperature: the
   balance is set by the turbine inlet temperature T3 after the heat
   exchanger. Solve T3 with t3_required_for_balance(t1, t2, eta_t,
   p3, p_cabin) and the exchanger effectiveness that lands it with
   hx_effectiveness_for_balance(t2, t_sink, t3_required). Over-
   effective heat exchange cools T3 so far that the turbine work
   collapses, and the 3-wheel bootstrap that adds a fan wheel on the
   same shaft makes closure harder, not easier; motor-assisted or
   two-turbine arrangements are out of scope. If no exchanger can
   deliver the closure T3 (t3_required at or below the sink, or above
   the exchanger hot inlet), flag the pack: precool the bleed (lower
   T1 through the upstream primary exchanger) or raise the bleed
   pressure.
7. Quote the delivered cooling with cooling_capacity(m_dot, t4,
   t_cabin_supply_target) against the cabin design temperature, size
   the bleed with required_bleed_flow(q_load, t4, target_t) for the
   ECS cooling load, and confirm the balance stays closed at that
   lower flow (the power ratio is invariant in m_dot). A two-wheel
   pack that must close and cool simultaneously may be infeasible at a
   hot pack-inlet temperature: the leaf flags it and the design routes
   to the precooled arrangement.
8. Confirm the deterministic checks with the contract test
   scripts/test_air_cycle_machine_sizing.py.

## Worked example

Shared inputs: bleed p1 = 240000 Pa, pr_c = 3.0, eta_c = 0.78, ram
sink 320 K, eta_t = 0.85, p_cabin = 101325 Pa, m_dot = 0.9 kg/s, cabin
design temperature 294 K, ECS cabin cooling load 12000 W.

Case A (unprecooled bleed, T1 = 460 K, heat exchanger effectiveness
0.8, the nominal design point):

- Compressor exit: T2 = 677.460935 K, p2 = 720000 Pa.
- Heat-exchanger exit: T3 = 391.492187 K.
- Turbine exit at pr_t = 7.105848 (p2 / p_cabin): T4 = 248.754280 K,
  p4 = 101325 Pa.
- Shaft powers: W_c = 196693.4 W versus W_t = 129106.4 W, so
  shaft_balance reports balanced False with deficit 67587.0 W and
  power ratio 0.6564: the turbine cannot drive the compressor and the
  pack cannot bootstrap, even though the raw turbine exit is very
  cold. The cooling capability of the un-driven expansion would be
  40924.8 W against the 294 K cabin.
- Closing that pack needs T3 = 596.437615 K, which the heat exchanger
  can only deliver at effectiveness 0.226663, and the balanced turbine
  exit then lands at 378.976680 K, above the 294 K cabin: at a 460 K
  pack-inlet temperature the two-wheel bootstrap cannot both close and
  cool. The leaf flags the pack and routes the design to Case B.

Case B (precooled pack inlet, T1 = 340 K, the standard bootstrap
arrangement with the primary ram heat exchanger ahead of the pack
compressor; the single pack heat exchanger is sized for closure):

- Compressor exit: T2 = 500.731995 K, p2 = 720000 Pa.
- Balance solve: T3_required = 440.845194 K and the closing
  effectiveness eff = 0.331357, so T3 = 440.845194 K.
- Turbine exit at pr_t = 7.105848: T4 = 280.113199 K.
- Shaft powers: W_c = W_t = 145382.1 W, balanced True with zero
  deficit and power ratio 1.0 (delta-T compressor = delta-T turbine =
  160.731995 K).
- Delivered cooling: 12560.6 W against the 294 K cabin versus the
  12000 W load, margin 1.0467; required bleed flow 0.859831 kg/s for
  the 12 kW load at the actual turbine exit temperature. The balance
  stays closed at that lower flow (ratio invariant in m_dot), so the
  bleed-flow and balance are one design: sizing the pack for a bigger
  load at the same T4 scales m_dot linearly and the shaft powers with
  it, which is why the two-wheel ACM is rated in delivered cooling at
  a stated bleed flow.

## Verification

- Confirm compressor_exit(240000.0, 460.0, 3.0, 0.78) returns t2 =
  677.460935 K and p2 = 720000.0 Pa exactly.
- Confirm heat_exchanger_exit(677.460935, 0.8, 320.0) returns
  391.492187 K and that T3 is monotone decreasing in effectiveness.
- Confirm turbine_exit(720000.0, 391.492187, 7.105848, 0.85,
  101325.0) returns t4 = 248.754280 K, p4 = 101325 Pa, and that pr_t
  7.0 against p_cabin 101325 Pa raises ValueError (REL_TOL breach).
- Confirm compressor_power(0.9, 460.0, 677.460935) = 196693.4 W and
  turbine_power(0.9, 391.492187, 248.754280) = 129106.4 W, with
  shaft_balance reporting balanced False, deficit 67587.0 W and ratio
  0.6564.
- Confirm the Case B closure: t3_required_for_balance(340.0,
  500.731995, 0.85, 720000.0, 101325.0) = 440.845194 K,
  hx_effectiveness_for_balance(500.731995, 320.0, 440.845194) =
  0.331357, and heat_exchanger_exit at that effectiveness round-trips
  to 440.845194 K.
- Confirm cooling_capacity(0.9, 280.113199, 294.0) = 12560.6 W
  (margin 1.0467 over 12000 W) and required_bleed_flow(12000.0,
  280.113199, 294.0) = 0.859831 kg/s.
- Confirm the balance identity: the power ratio at 0.45 kg/s equals
  the ratio at 0.9 kg/s (1.0 in Case B) and delta-T compressor equals
  delta-T turbine (160.731995 K both).
- Confirm every non-positive pressure, temperature, mass flow and load
  and every efficiency or effectiveness outside its stated range
  raises ValueError.
- Run the contract test offline: python3
  scripts/test_air_cycle_machine_sizing.py (34 tests, deterministic).

## Related leaves

- vehicle-design/sizing/environmental-control-sizing: the cabin heat
  load, fresh-air ventilation flow and the pack airflow verdict that
  demand the pack cooling; stops at the pack as a black box.
- vehicle-design/sizing/bleed-air-system-sizing: the bleed offtake
  rollup, precooler rejection budget and the pack-inlet bleed
  condition consumed here.
- vehicle-design/sizing/ice-protection-sizing: surface anti-icing
  bleed demand, a different bleed consumer (surface heating, not
  cabin cooling).
- vehicle-design/sizing/cabin-outflow-valve-sizing: takes the pack
  inflow as an input to size the outflow valve.

## Pitfalls

- Sizing on the raw engine bleed temperature: a production bootstrap
  pack places a primary ram heat exchanger ahead of the pack
  compressor, so the pack-inlet temperature T1 is the precooled value
  and this leaf never re-derives it from the raw bleed temperature.
  Feeding the 460 K unprecooled bleed into the balance checks shows a
  pack that cannot both close and cool (Case A).
- Quoting cooling from the un-driven expansion: the raw turbine exit
  of Case A is 248.75 K and the un-driven cooling capability 40924.8
  W, but the pack cannot bootstrap with a 67587.0 W shaft deficit, so
  delivered cooling must always follow a closed shaft balance.
- Over-cooling the heat exchanger: effectiveness is NTU-style, not a
  fixed temperature drop, and over-effective heat exchange cools the
  turbine inlet T3 so far that the turbine work collapses; closure is
  set by T3, not by how cold the exchanger can make the discharge.
- Expecting the 3-wheel arrangement to close easier: the 3-wheel
  bootstrap adds a fan wheel on the same shaft and so makes closure
  harder, not easier; motor-assisted or two-turbine arrangements are
  out of scope for this two-wheel leaf.
- Treating the balance as flow-dependent: both shaft powers scale
  linearly with m_dot, so the power ratio and the closure verdict are
  purely thermodynamic statements about temperatures; a pack sized at
  0.9 kg/s stays closed at the 0.859831 kg/s required flow.
- Reading the pressure-ratio consistency loosely: p3 / pr_t must equal
  p_cabin at REL_TOL 1e-9, because the pack discharges at cabin
  pressure; a pr_t of 7.0 against 101325 Pa cabin pressure is a
  genuine mismatch, not a rounding matter.

## Contract test

Run the deterministic contract test offline (stdlib unittest, no
network, no external packages):

    python3 scripts/test_air_cycle_machine_sizing.py

The 34 tests cover the Case A and Case B compressor exit anchors, the
heat-exchanger exit and its monotone effectiveness behavior, the
cooling turbine exit anchors and the pressure-ratio consistency check,
the compressor and turbine shaft powers, the shaft balance verdicts
with the 1 W tolerance band, the closure temperature solve with the
heat-exchanger effectiveness round trip, the feasible-but-uncooled
Case A path, the delivered cooling power and required bleed flow, the
mass-flow invariance identity and the dict-key and determinism checks,
plus ValueError rejection of every non-physical input class.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_air_cycle_machine_sizing.py

The test covers the sizing contract (Case A open with a 67587.0 W
deficit and Case B closed with ratio 1.0), every station anchor within
spec tolerance, the shaft balance tolerance band and identity, the
closure temperature and effectiveness solve with round trip, the
delivered cooling margin and required bleed flow, and ValueError
rejection of non-positive pressures, temperatures, mass flows and
loads and of out-of-range efficiencies and effectivenesses.

## Compliance

- Standards referenced, not reproduced: FAR 25 (airworthiness
  standards, 25.831 ventilation context) is reference-only per
  standards-map.yaml; the bootstrap air-cycle relations above are
  standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
