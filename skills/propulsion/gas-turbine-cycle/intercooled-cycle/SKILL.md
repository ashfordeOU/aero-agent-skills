---
name: intercooled-cycle
description: "Use when you must analyze a gas turbine cycle with intercooling: split the total pressure ratio into two compression stages with an intercooler between them, compute the intercooler exit temperature from the stage pressure ratio and effectiveness, determine the optimum intercooler pressure ratio minimizing total compressor work, and quantify net specific work and thermal efficiency against the simple non-intercooled cycle. Produces the intercooled cycle efficiency, the simple cycle baseline efficiency, the optimum intercooler pressure ratio, the specific work gain, and the station temperatures that gate an engine cycle comparison. Trigger: intercooled cycle, two-stage compression, intercooler effectiveness, intercooler pressure ratio, compression work split, cycle work gain."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: gas-turbine-cycle
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [intercooled-cycle, intercooler-effectiveness, intercooler-pressure-ratio, two-stage-compression, compression-work-split, cycle-work-gain]
  version: 0.1.0
  author: AeroSkills
---

# Intercooled Cycle (propulsion/gas-turbine-cycle/intercooled-cycle)

Use when the task is intercooled gas turbine cycle analysis: splitting the
total pressure ratio into two compression stages around an intercooler,
computing the intercooler exit temperature from its effectiveness, taking
the equal-split optimum pi_1 = pi_2 = sqrt(pi_total), and comparing net
specific work and thermal efficiency against the simple single-stage
cycle. This leaf implements the air-standard two-stage analysis in pure
Python, stdlib only. It pairs with propulsion/gas-turbine-cycle/
gas-turbine-cycle for the simple cycle baseline and with
propulsion/gas-turbine-cycle/regenerative-cycle, the heat-recovery
variant that recovers the efficiency penalty this cycle accepts. It does
not cover the single-stage baseline analysis, heat recovery, exhaust
augmentation, or non-ideal component behavior; those belong to the
sibling leaves above.

## Domain quick reference

- Cycle layout: stage 1 compresses from T_1 to the intercooler at
  pressure ratio pi_1, the intercooler cools the discharge toward T_1,
  stage 2 compresses from the intercooler exit to the combustor at pi_2,
  with pi_1 * pi_2 = pi_total.
- Optimum pressure split: pi_1 = pi_2 = sqrt(pi_total) minimizes the
  total compressor work for a fixed total ratio when intercooling
  returns the air to the ambient temperature (equal stage split).
- Stage discharge temperature: T_exit = T_in * (1 + (pi_stage**((GAMMA-1)/
  GAMMA) - 1) / eta_c), the real discharge with the stage isentropic
  efficiency applied once (stage_exit_temperature).
- Intercooler exit: T_ic_exit = T_2a - eps_ic * (T_2a - T_1); eps_ic = 0
  leaves the discharge uncooled, eps_ic = 1 returns the ambient
  temperature (intercooler_exit_temperature).
- Compressor work: per stage w_c = cp * (T_exit - T_in), equal to
  cp * T_in * (pi_stage**((GAMMA-1)/GAMMA) - 1) / eta_c; the total is the
  sum over the two stages (compressor_work_total).
- Turbine work: w_t = cp * eta_t * T_3 * (1 - pi_total**(-(GAMMA-1)/
  GAMMA)) expands through the FULL total ratio (turbine_work).
- Cycle: q_in = cp * (T_3 - T_2b), w_net = w_t - w_c_total,
  eta_th = w_net / q_in (intercooled_cycle).
- Comparison baseline: the simple cycle with one compression stage at
  pi_total (simple_cycle); gain = (w_net_i - w_net_s)/w_net_s * 100
  percent and eta_delta = (eta_th_i - eta_th_s) * 100 percentage points
  (cycle_comparison).
- Trade: intercooling lowers the compressor work and raises the net
  specific work, but at fixed T_3 it also raises q_in through the lower
  T_2b, so the thermal efficiency falls slightly when no heat recovery
  is present. Units are SI: K, J/kg for specific work, dimensionless
  ratios and efficiencies.
- FAR-33 frames the aircraft engine certification context (reference
  only, standards-map.yaml); the relations above are standard
  air-standard methodology, summary-only.

## Workflow

1. Fix the operating point: inlet temperature T_1, turbine inlet
   temperature T_3, total pressure ratio pi_total, intercooler
   effectiveness eps_ic, and efficiencies eta_c and eta_t.
2. Take the optimum split with optimum_intercooler_pressure_ratio:
   pi_1 = pi_2 = sqrt(pi_total).
3. Run compressor_work_total(T_1, pi_total, eps_ic, eta_c) to get the
   station temperatures T_2a, T_ic_exit, T_2b and the stage works w_c1,
   w_c2, w_c_total.
4. Get the expansion side with turbine_work(T_3, pi_total, eta_t).
5. Assemble the intercooled cycle with intercooled_cycle(T_1, T_3,
   pi_total, eps_ic, eta_c, eta_t) for w_net, q_in and eta_th.
6. Run the baseline with simple_cycle(T_1, T_3, pi_total, eta_c,
   eta_t) and compare with cycle_comparison to get the specific work
   gain in percent and the efficiency change in percentage points.
7. Judge the trade: accept the efficiency slip only when the work gain
   or the downstream heat-recovery option justifies it.
8. Confirm the deterministic checks with the contract test
   scripts/test_intercooled_cycle.py.

## Worked example

Air-standard intercooled cycle at T_1 = 288 K, T_3 = 1500 K,
pi_total = 30, eps_ic = 0.8, eta_c = 0.85, eta_t = 0.9 (GAMMA 1.4,
cp 1005 J/(kg K)). Module real outputs:

- Optimum split: pi_1 = pi_2 = 5.4772 (sqrt of 30).
- Stations: T_2a = 499.97 K; T_ic_exit = 330.39 K (cooled 169.6 K
  toward ambient); T_2b = 573.57 K.
- Compressor: w_c1 = 213.03 kJ/kg; w_c2 = 244.39 kJ/kg;
  w_c_total = 457.42 kJ/kg.
- Turbine: w_t = 843.34 kJ/kg (full pi_total expansion).
- Cycle: w_net = 385.91 kJ/kg; q_in = 931.06 kJ/kg;
  eta_th = 0.4145.
- Simple cycle baseline: w_net = 284.0 kJ/kg; eta_th = 0.4311.
- Comparison: work_gain_pct = +35.9 percent;
  eta_delta_pp = -1.66 percentage points. Intercooling raises the
  specific work by about a third while the thermal efficiency slips by
  1.66 points without heat recovery, the documented intercooling trade.

## Verification

- Confirm the anchors: T_2a = 499.97 K, T_ic_exit = 330.39 K,
  T_2b = 573.57 K, w_c_total = 457.42 kJ/kg, w_net = 385.91 kJ/kg,
  q_in = 931.06 kJ/kg, eta_th = 0.4145, gain +35.9 percent,
  eta_delta -1.66 pp, each within 1 percent of the module output.
- Confirm optimum_intercooler_pressure_ratio(36) == 6.0 and (30) ==
  5.4772; the exit temperature rises with pi_stage and falls with
  eta_c; eps_ic = 0 returns the hot inlet and eps_ic = 1 the coolant.
- Confirm a higher-effectiveness intercooler reduces w_c_total at fixed
  pi_total, and that eta_th sits strictly between 0 and 1 here.
- Confirm the eps_ic = 0 degeneration: the no-cooling two-stage total
  work approximates the single-stage work (the two differ by the
  stage-2 cascade term, which vanishes as eta_c -> 1).
- Confirm every non-physical input raises ValueError: T_1 <= 0,
  T_3 <= T_1, pi_total <= 1, eta_c or eta_t outside (0, 1], eps_ic
  outside [0, 1], and coolant at or above the intercooler hot inlet.
- Run the contract test offline: python3
  scripts/test_intercooled_cycle.py (33 tests, deterministic).

## Related leaves

- propulsion/gas-turbine-cycle/gas-turbine-cycle: the single-stage
  cycle analysis that supplies the comparison baseline.
- propulsion/gas-turbine-cycle/regenerative-cycle: the heat-recovery
  variant that recovers the efficiency this cycle gives up.
- propulsion/gas-turbine-cycle/propelling-nozzle: nozzle expansion
  downstream of the turbine.
- propulsion/gas-turbine-cycle/afterburner-cycle: the augmentation
  variant for thrust beyond the turbine limit.
- propulsion/gas-turbine-cycle/real-cycle-effects: loss accounting
  beyond the constant-efficiency assumption used here.

## Pitfalls

- Quoting the pressure split as the work split: pi_1 = pi_2 =
  sqrt(pi_total) is the optimum only for the ideal case; with eps_ic =
  0.8 the second stage still does more work (244.39 against 213.03
  kJ/kg) because its inlet sits at 330.39 K, above ambient.
- Reporting the work gain without the efficiency cost: at the worked
  point the net work rises +35.9 percent while eta_th falls 1.66
  points, and the gain alone is what sells an intercooled design.
- Dividing the efficiency in twice: stage_exit_temperature already
  applies eta_c to return the real discharge, so the stage work is
  cp * (T_exit - T_in) and not that value divided by eta_c again;
  the spec anchors pin the single application.
- Reading the eps_ic = 0 case as a free win: without intercooling the
  two-stage chain charges the stage-2 inefficiency on the real stage-1
  discharge, so its work (582.9 kJ/kg) slightly exceeds the
  single-stage value (559.3 kJ/kg); the two coincide only as eta_c
  tends to 1. This is a modeling artifact, not a physical gain.
- Expanding the turbine at the stage ratio: the turbine sees the full
  pi_total (843.34 kJ/kg here), never the per-stage sqrt value, so
  mixing the two ratios understates the expansion work.
- Mixing units: the module returns specific work in J/kg; the worked
  example tables divide by 1000 to quote kJ/kg.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_intercooled_cycle.py

The test covers the module constants, the optimum pressure ratio (36 ->
6.0, 30 -> 5.4772), stage and intercooler exit temperatures with their
limits (eps_ic 0 and 1) and monotonicity, the worked-example anchors
within 1 percent, the compressor total as the stage-work sum, the
effectiveness work-reduction relation, the full cycle and simple-cycle
baseline dicts with their identities (w_net = w_t - w_c_total,
eta_th = w_net / q_in), the comparison signs and closed forms, the
eps_ic = 0 degeneration identity, determinism, and ValueError rejection
of every non-physical input class.

## Contract test

Run from the leaf root: python3 scripts/test_intercooled_cycle.py.
The logic module is scripts/intercooled_cycle_logic.py, pure stdlib with
module constants GAMMA = 1.4 and CP = 1005.0. The test file is stdlib
unittest, offline and deterministic, 33 methods, and asserts the module
outputs against the prep-verified worked-example anchors plus the
magnitude bounds of the spec (works within 1 percent, eta_th between 0
and 1). Exit code 0 means the leaf contract holds.

## Compliance

- Standards referenced, not reproduced: FAR-33 (14 CFR Part 33) frames
  aircraft engine certification context; the intercooled cycle
  relations above are standard air-standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
