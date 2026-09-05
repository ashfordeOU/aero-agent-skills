# Wave-41 leaf spec: air-cycle-machine-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/air-cycle-machine-sizing/
- Pack: sizing (verified present at prep with environmental-control-sizing,
  bleed-air-system-sizing, ice-protection-sizing, cabin-outflow-valve-sizing,
  battery-sizing, hydraulic-system-sizing and the rest of the wave-1 sizing
  pack). Closest siblings and their fences:
  - environmental-control-sizing owns the ECS cabin side and STOPS at the
    pack airflow with no pack-internal thermodynamics: its frontmatter claim
    is "compute the cabin ventilation fresh air flow from the occupant count
    and per-occupant rate, roll up the cabin heat load from occupants, solar,
    equipment and skin with a design margin, derive the pack cooling airflow
    from the heat load and the supply air temperature rise, take the pack
    airflow as the governing maximum of fresh and cooling flow, and build the
    cabin pressurization schedule that holds the design cabin pressure
    altitude until the design differential pressure binds", and its Domain
    quick reference gives the whole pack model as "Pack cooling flow: m_cool
    = Q_design / (cp * dT_supply), with default cp 1.005 kJ/(kg K) and
    default supply temperature rise 20 K. Pack flow is the governing
    maximum: m_pack = max(m_fresh, m_cool)". The pack is a black box in that
    leaf: no bleed pressure or temperature, no compressor, no heat
    exchanger, no turbine, no shaft appear anywhere in its body, so it
    stops at cabin heat load and pack airflow without pack-internal
    thermodynamics (its own boundary statement: the pack air "derives from
    the heat load and the supply temperature rise; the two answer different
    questions" for fresh versus cooling flow). It also embeds its own ISA
    and pressurization schedule, which this leaf does not touch.
  - bleed-air-system-sizing owns the bleed distribution manifold upstream:
    its body states "The pack flows, the wing anti-ice flow and the trim
    flow are INPUTS here (values computed by the sibling environmental-
    control and ice-protection leaves); nothing downstream of the offtakes
    is recomputed", with a bleed thermal budget q = m * CP_AIR * (T_bleed -
    T_supply) that the precooler rejects toward a consumer supply
    temperature (288 K default). Its claim covers offtake rollup, per-engine
    split, precooler rejection budget and duct diameters; it never enters
    the pack. This leaf consumes the pack-inlet bleed condition (pressure
    and temperature after upstream conditioning) as an input, so the bleed
    supply context comes from that sibling.
  - ice-protection-sizing owns the surface anti-icing bleed demand: its
    claim sizes "the electrothermal power or bleed air mass flow" for
    surface heat with "bleed mass flow m_dot = P_req / (cp_air * (T_bleed -
    T_inf)) for a pneumatic system". That bleed heats a surface; the pack
    bleed here is cooled and delivered to the cabin, a different consumer.
  - cabin-outflow-valve-sizing (wave-36) takes the pack inflow as an input
    to size the outflow valve; it does not model pack thermodynamics either.
  Whole-tree greps at prep: "air-cycle", "bootstrap", "cooling turbine" and
  "air cycle machine" = 0 hits in skills/vehicle-design and 0 ECS-adjacent
  hits in eval/hit1-corpus.yaml (the only tree hits for "bootstrap" are the
  gnc-autonomy particle-filter files, a different bootstrap entirely; the
  corpus "compressor exit temperature" and "turbine exit temperature" tasks
  at eval/hit1-corpus.yaml lines 719, 724, 1970, 3555 and 4919 all belong
  to propulsion gas-turbine-cycle, free-turbine and afterburner tasks).
  No leaf sizes the pack-internal air cycle: GENUINE gap between the cabin
  heat load and pack airflow of environmental-control-sizing and the bleed
  supply of bleed-air-system-sizing sits the bootstrap ACM, whose
  compressor and turbine exit states, heat-exchanger exit, shaft balance
  and delivered cooling no existing leaf computes.
- Standards id: far-25 (present in standards-map.yaml; all vehicle-design
  sizing siblings carry far-25 reference-only). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the bootstrap air-cycle cooling pack thermodynamics for the ECS
cooling load: take the pack-inlet bleed condition, compressor pressure
ratio and isentropic efficiency, compute the compressor exit state, cool
the discharge through the ram-air heat exchanger at a given effectiveness,
expand through the cooling turbine to the cabin pressure with its
isentropic efficiency to get the turbine exit state, close the two-wheel
ACM shaft energy balance (the turbine drives the compressor on one shaft;
W_t must cover W_c), and turn the turbine exit temperature into the
delivered cooling power against the cabin design temperature and the
required bleed flow for the cabin cooling load, with the pack flagged when
the balance cannot close. Produces the compressor and turbine exit
temperatures and pressures, the heat-exchanger exit temperature, the
compressor and turbine shaft powers, the balance verdict with the work
deficit or the heat-exchanger effectiveness that closes the balance, the
delivered cooling power versus the load and the required bleed flow. Does
NOT do: cabin ventilation fresh airflow, cabin heat load rollup,
pressurization scheduling or the pack airflow verdict
(environmental-control-sizing); bleed offtake rollup, precooler rejection
budget or duct sizing (bleed-air-system-sizing); surface anti-ice bleed
demand (ice-protection-sizing). Two-wheel bootstrap only; the 3-wheel
arrangement that adds a fan wheel on the same shaft is documented, not
modeled.

## Model (implement exactly)

Pure stdlib, math only. Perfect-gas dry air, constant cp. Stations: 1 =
pack inlet bleed, compressor exit 2, heat-exchanger exit 3 (constant
pressure, p3 = p2), cooling turbine exit 4 at cabin pressure p4 =
p_cabin. Bleed assumption documented in the SKILL body: p1 and T1 are the
conditions at the pack inlet after upstream bleed conditioning (the
precooler context of bleed-air-system-sizing); a production bootstrap pack
places a primary ram heat exchanger ahead of the pack compressor, so the
pack-inlet temperature is already the precooled value and this leaf never
re-derives it from the raw engine bleed temperature.

Module constants: GAMMA = 1.4, CP_AIR = 1005.0 (J/kg K), EXP =
(GAMMA - 1.0) / GAMMA, REL_TOL = 1e-9 (turbine pressure-ratio
consistency), BALANCE_TOL_W = 1.0 (shaft equality band, W).

Functions:
- compressor_exit(bleed_p1, bleed_t1, pr_c, eta_c) -> dict {"t2", "p2"}:
  T2 = T1 * (1 + (pr_c^EXP - 1) / eta_c), p2 = p1 * pr_c. ValueError if
  bleed_p1 <= 0, bleed_t1 <= 0, pr_c <= 1.0 or eta_c outside (0, 1).
- heat_exchanger_exit(t_hot_in, effectiveness, t_sink) -> float:
  T3 = t_hot_in - effectiveness * (t_hot_in - t_sink). Convention PINNED:
  the effectiveness (NTU-style) form, not a fixed temperature drop; a
  cooling heat exchanger needs t_hot_in > t_sink. ValueError if t_hot_in
  <= 0, t_sink <= 0, effectiveness outside (0, 1] or t_hot_in <= t_sink.
- turbine_exit(p3, t3, pr_t, eta_t, p_cabin) -> dict {"t4", "p4", "pr_t"}:
  pr_t = p3 / p4 is the design expansion ratio and p4 = p_cabin; the pack
  discharges at cabin pressure, so the leaf validates p3 / pr_t against
  p_cabin (relative tolerance REL_TOL) and raises ValueError on mismatch;
  T4 = T3 * (1 - eta_t * (1 - (p4 / p3)^EXP)). ValueError if p3 <= 0,
  t3 <= 0, p_cabin <= 0, pr_t <= 1.0, eta_t outside (0, 1) or the
  consistency check fails.
- compressor_power(m_dot, t1, t2) -> float W_c = m_dot * CP_AIR * (T2 -
  T1). turbine_power(m_dot, t3, t4) -> float W_t = m_dot * CP_AIR * (T3 -
  T4). ValueError if m_dot <= 0; compressor_power also if t2 < t1 and
  turbine_power if t4 > t3.
- shaft_balance(w_compressor, w_turbine) -> dict {"balanced",
  "w_compressor", "w_turbine", "deficit_w", "power_ratio"}: balanced is
  True when w_turbine + BALANCE_TOL_W >= w_compressor (the tolerance
  absorbs float noise; anything beyond 1 W is a real deficit),
  deficit_w = max(w_compressor - w_turbine, 0.0), power_ratio =
  w_turbine / w_compressor. Balanced False means the turbine cannot drive
  the compressor and the pack cannot bootstrap: the SKILL body documents
  that the closure is set by the turbine inlet temperature T3 after the
  heat exchanger, that over-effective heat exchange cools T3 so far the
  turbine work collapses, and that the 3-wheel bootstrap adds a fan wheel
  on the same shaft and so makes closure harder, not easier (motor-assisted
  or two-turbine arrangements are out of scope). ValueError if
  w_compressor <= 0 or w_turbine < 0.
- t3_required_for_balance(t1, t2, eta_t, p3, p_cabin) -> float: solves the
  implied balance relation for the turbine inlet temperature that makes
  W_t = W_c: compressor delta-T (T2 - T1) must equal the turbine delta-T
  eta_t * (1 - (p4 / p3)^EXP) * T3, so T3 = (T2 - T1) / (eta_t * (1 -
  (p_cabin / p3)^EXP)). ValueError if t1 <= 0, t2 <= t1, p3 <= p_cabin or
  eta_t outside (0, 1).
- hx_effectiveness_for_balance(t2, t_sink, t3_required) -> float: the heat
  exchanger effectiveness that lands T3 on the balance value, eff = (T2 -
  T3_req) / (T2 - t_sink). ValueError if t2 <= t_sink or the required
  temperature is infeasible for a cooling exchanger (t3_required <= t_sink
  or t3_required > t2): no heat exchanger can close the pack, and the SKILL
  body guidance is to precool the bleed (lower T1 through the upstream
  primary exchanger) or raise the bleed pressure.
- cooling_capacity(m_dot, t_turbine_out, t_cabin_supply_target) -> float:
  Q = m_dot * CP_AIR * (T_target - T4), signed W: positive when the
  turbine exit arrives below the cabin design temperature (cooling
  capability), zero or negative when the supply is not cold enough.
  ValueError if m_dot <= 0 or either temperature <= 0.
- required_bleed_flow(q_load, t4_effective, target_t) -> float: m_dot_req
  = q_load / (CP_AIR * (T_target - T4)), the bleed flow that carries the
  cabin cooling load at the actual turbine exit temperature. ValueError if
  q_load <= 0 (a cooling demand must be positive) or t4_effective >=
  target_t (the air cannot cool; raising the flow never helps).

Identity to test: the shaft balance ratio W_t / W_c is independent of the
bleed flow because both powers scale linearly with m_dot, so closure is a
purely thermodynamic statement about temperatures (delta-T compressor
equals delta-T turbine), and a closing pack stays closed at any flow.

## Worked example

Run your module and take the real outputs as assert targets; the anchors
below are prep-verified by running /tmp/w41spec/anchor_acm.py (stdlib
math). Shared inputs: bleed p1 = 240000 Pa, pr_c = 3.0, eta_c = 0.78,
ram sink 320 K, eta_t = 0.85, p_cabin = 101325 Pa, m_dot = 0.9 kg/s,
cabin design temperature 294 K, ECS cabin cooling load 12000 W.

Case A (unprecooled bleed, T1 = 460 K, heat exchanger effectiveness 0.8,
the nominal design point): compressor exit T2 = 677.460935 K, p2 =
720000 Pa; heat-exchanger exit T3 = 391.492187 K; expansion ratio pr_t =
7.105848 (p2 / p_cabin); turbine exit T4 = 248.754280 K, p4 = 101325 Pa.
Shaft powers at 0.9 kg/s: W_c = 196693.4 W versus W_t = 129106.4 W, so
shaft_balance reports balanced False with deficit 67587.0 W and power
ratio 0.6564: the turbine cannot drive the compressor and the pack cannot
bootstrap, even though the raw turbine exit is very cold (the cooling
capability of the un-driven expansion would be 40924.8 W against the
294 K cabin). Closing that pack would need T3 = 596.437615 K, which the
heat exchanger can only deliver at effectiveness 0.226663, and the
balanced turbine exit then lands at 378.976680 K, above the 294 K cabin:
at a 460 K pack-inlet temperature the two-wheel bootstrap cannot both
close and cool. The leaf flags the pack and the SKILL body routes the
design to Case B.

Case B (precooled pack inlet, T1 = 340 K, the standard bootstrap
arrangement with the primary ram heat exchanger ahead of the pack
compressor, documented note; the single pack heat exchanger is sized for
closure): compressor exit T2 = 500.731995 K, p2 = 720000 Pa. The balance
solve gives T3_required = 440.845194 K and the closing effectiveness eff
= 0.331357, so T3 = 440.845194 K; turbine exit T4 = 280.113199 K at pr_t
= 7.105848. Shaft powers W_c = W_t = 145382.1 W: balanced True with zero
deficit and power ratio 1.0 (delta-T compressor = delta-T turbine =
160.731995 K). Delivered cooling power against the 294 K cabin is
12560.6 W versus the 12000 W load, margin 1.0467, and the required bleed
flow for the 12 kW load is 0.859831 kg/s at the actual turbine exit
temperature; the balance stays closed at that lower flow (ratio invariant
in m_dot). The bleed-flow and balance are one design: sizing the pack for
a bigger load at the same T4 scales m_dot linearly and the shaft powers
with it, which is why the two-wheel ACM is rated in delivered cooling at a
stated bleed flow.

## Validation list (contract test must include)

- compressor_exit(240000.0, 460.0, 3.0, 0.78): t2 = 677.460935 K within
  1e-6, p2 = 720000.0 Pa exactly; compressor_exit(240000.0, 340.0, 3.0,
  0.78): t2 = 500.731995 K within 1e-6. ValueErrors: pr_c 1.0 and 0.5,
  eta_c 0 and 1, p1 0, T1 0.
- heat_exchanger_exit(677.460935, 0.8, 320.0) = 391.492187 K within 1e-6;
  T3 is monotone decreasing in effectiveness; ValueErrors at effectiveness
  0 and 1.01 and at t_hot_in 320.0 with t_sink 320.0 (not above sink).
- turbine_exit(720000.0, 391.492187, 7.105848, 0.85, 101325.0): t4 =
  248.754280 K within 1e-6, p4 = 101325.0, pr_t = 7.105848 within 1e-6;
  turbine_exit(720000.0, 440.845194, 7.105848, 0.85, 101325.0): t4 =
  280.113199 K within 1e-6. T4 falls as pr_t rises at fixed T3 and falls
  as eta_t rises. ValueErrors: pr_t 1.0, eta_t 0 and 1, and the
  consistency check (pr_t 7.0 with p_cabin 101325.0 fails REL_TOL).
- compressor_power(0.9, 460.0, 677.460935) = 196693.4 W within 0.1;
  turbine_power(0.9, 391.492187, 248.754280) = 129106.4 W within 0.1;
  case B powers both 145382.1 W within 0.1.
- shaft_balance(196693.4, 129106.4): balanced False, deficit 67587.0 W
  within 0.1, power_ratio 0.6564 within 1e-4; shaft_balance(145382.1,
  145382.1): balanced True, deficit 0.0, ratio 1.0.
- t3_required_for_balance(340.0, 500.731995, 0.85, 720000.0, 101325.0) =
  440.845194 K within 1e-6; hx_effectiveness_for_balance(500.731995,
  320.0, 440.845194) = 0.331357 within 1e-6; heat_exchanger_exit with
  that effectiveness returns 440.845194 K within 1e-6 (round trip);
  hx_effectiveness_for_balance raises when t3_required <= t_sink or >
  t2 (the infeasible-pack path of Case A closure at eff 0.226663 is
  feasible, but the balanced T4 378.976680 K >= 294 K shows no cooling).
- cooling_capacity(0.9, 280.113199, 294.0) = 12560.6 W within 0.1,
  margin 1.0467 against 12000 W; cooling_capacity(0.9, 310.0, 294.0) =
  -14472.0 W within 0.1 (signed, no cooling).
- required_bleed_flow(12000.0, 280.113199, 294.0) = 0.859831 kg/s within
  1e-6; ValueErrors at q_load 0 and -5 and at t4 300.0 with target 294.0
  (no cooling possible).
- Balance identity: ratio at 0.45 kg/s equals the ratio at 0.9 kg/s
  (1.0 in Case B); a closing pack stays closed at any flow; delta-T
  compressor equals delta-T turbine in Case B (160.731995 K both).
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave41-air-cycle-machine-sizing.yaml)

Query 1 (copy verbatim):
  "size the bootstrap-air-cycle cooling pack for the cabin cooling load: compute the compressor-exit state and the heat-exchanger-exit temperature, expand through the cooling-turbine to cabin pressure with isentropic efficiencies, and confirm the acm-shaft-balance closes before quoting the delivered-cooling-power"
  intent: "vehicle-design; bootstrap ACM pack thermodynamics, shaft balance closure and delivered cooling power"
  expected_skill: "vehicle-design/sizing/air-cycle-machine-sizing"
Query 2 (copy verbatim):
  "check the bootstrap closure of the two-wheel air-cycle-machine before sizing the required-bleed-flow: compare the cooling-turbine power against the pack-compressor power on the shared shaft and flag the pack when the turbine cannot drive the compressor"
  intent: "vehicle-design; two-wheel ACM bootstrap balance verdict and required bleed flow"
  expected_skill: "vehicle-design/sizing/air-cycle-machine-sizing"
Task ids: w41-air-cycle-machine-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the bootstrap air-cycle
cooling pack thermodynamics for the ECS cooling load:" and include the
outputs in the Claim. First tag: air-cycle-machine-sizing. Additional tags
ONLY: bootstrap-air-cycle, acm-shaft-balance, cooling-turbine-exit,
compressor-exit-state, heat-exchanger-effectiveness, required-bleed-flow,
delivered-cooling-power. NEVER single generic words (pack, bleed, cabin,
cooling, compressor, turbine, heat, air, flow, sizing). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): cabin-ventilation, fresh-air-flow,
occupant-rate, cabin-heat-load, pack-cooling-flow, pack-airflow,
supply-temperature-rise, pressurization-schedule, cabin-pressure-altitude,
differential-pressure-limit (environmental-control-sizing);
bleed-offtake-mass-flow, bleed-duct-diameter, bleed-thermal-budget,
precooler-heat-load, pneumatic-bleed-manifold, per-engine-offtake,
duct-mach-sizing (bleed-air-system-sizing); evaporative-anti-icing,
running-wet-anti-ice, cyclic-de-icing, catch-efficiency, freezing-
fraction, electrothermal-power, protected-area, mvd, icing-critical
(ice-protection-sizing); outflow-valve-area (cabin-outflow-valve-sizing);
ram-air-turbine (ram-air-turbine-sizing, the RAT power device; the ACM ram
air appears only as the heat-exchanger sink temperature);
brayton-cycle, gas-generator, power-turbine, turbojet, afterburner,
engine-cycle (propulsion gas-turbine corpus tasks at eval/hit1-corpus.yaml
lines 719, 724, 1970, 3555 and 4919, which own engine compressor and
turbine exit temperatures); particle-filter, sir-filter,
importance-weights (the gnc-autonomy bootstrap particle filter, the only
other "bootstrap" in the tree).
