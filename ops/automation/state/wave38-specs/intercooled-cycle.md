# Wave-38 leaf spec: intercooled-cycle (propulsion, gas-turbine-cycle pack)

- Path: skills/propulsion/gas-turbine-cycle/intercooled-cycle/
- Pack: gas-turbine-cycle. Closest siblings: gas-turbine-cycle (simple
  ideal Brayton cycle: efficiency, station temperatures, specific work
  from pressure ratio and temperature limits), regenerative-cycle (regener-
  ator effectiveness and optimum pressure ratio), afterburner-cycle (reheat),
  real-cycle-effects (component losses), propelling-nozzle (nozzle
  expansion). Whole-tree grep: "intercool" = ZERO hits in any leaf or
  router; the pack already encodes the Brayton-variant pattern (regener-
  ative, afterburner, real-cycle) that this leaf extends. ZERO owners.
  GENUINE PROP gap (fresh probe).
- Standards id: far-33 (reference-only; family spine - aircraft engine
  cycle analysis context). Ledger Standard: far-33.
- Family: propulsion

## Claim

Analyze a gas turbine cycle with intercooling: split the total pressure
ratio into two compression stages with an intercooler between them,
compute the intercooler exit temperature from the stage pressure ratio and
the intercooler effectiveness, determine the optimum intercooler pressure
ratio that minimizes the total compressor work, and quantify the net
specific work and thermal efficiency against the simple (non-intercooled)
cycle. Produces the intercooled cycle efficiency, the simple cycle
efficiency for comparison, the optimum intercooler pressure ratio, the
specific work gain, and the station temperatures that gate an engine cycle
comparison. Does NOT do: the simple Brayton cycle (gas-turbine-cycle);
regenerator heat recovery (regenerative-cycle); reheat (afterburner-cycle);
component loss modeling (real-cycle-effects).

## Model (implement exactly)

Conventions: SI units (K, J/kg, W/kg as specific work). A perfect-gas
analysis with constant CP and gamma. The compressor is split into two
stages with pressure ratio pi_1 between ambient and the intercooler and
pi_2 between the intercooler and the combustor inlet; pi_1 * pi_2 =
pi_total. The intercooler cools the stage-1 discharge toward the ambient
temperature with effectiveness eps_ic: T_ic_exit = T_2a - eps_ic *
(T_2a - T_1) where T_2a is the stage-1 discharge temperature. Each
compressor stage has isentropic efficiency eta_c; the turbine has eta_t.

Module constants: GAMMA = 1.4, CP = 1005.0, and the assumption that the
optimum intercooler pressure ratio for a fixed total ratio is
sqrt(pi_total) (equal stage work split, documented optimum).

Functions (pure stdlib):
- stage_exit_temperature(T_in, pi_stage, eta_c) -> float (isentropic
  stage discharge with efficiency: T_in * (1 + (pi_stage**((GAMMA-1)/
  GAMMA) - 1) / eta_c)).
- intercooler_exit_temperature(T_in_hot, T_coolant, eps_ic) -> float:
  T_in_hot - eps_ic * (T_in_hot - T_coolant). ValueErrors: eps_ic outside
  [0, 1]; T_coolant >= T_in_hot (no cooling).
- optimum_intercooler_pressure_ratio(pi_total) -> float = sqrt(pi_total).
  ValueError: pi_total <= 1.
- compressor_work_total(T_1, pi_total, eps_ic, eta_c) -> dict with
  {pi_1, pi_2, T_2a, T_ic_exit, T_2b, w_c1, w_c2, w_c_total}: stage
  works cp * (T_exit - T_in) / eta_c per stage (work per unit mass).
- turbine_work(T_3, pi_total, eta_t) -> float: cp * eta_t * T_3 *
  (1 - pi_total**(-(GAMMA-1)/GAMMA)).
- intercooled_cycle(T_1, T_3, pi_total, eps_ic, eta_c, eta_t) -> dict
  {pi_1, pi_2, T_2a, T_ic_exit, T_2b, w_c1, w_c2, w_c_total, w_t, w_net,
  q_in, eta_th}: q_in = cp * (T_3 - T_2b); eta_th = w_net / q_in.
- simple_cycle(T_1, T_3, pi_total, eta_c, eta_t) -> dict {w_c, w_t,
  w_net, q_in, eta_th} (single compression stage, no intercooler).
- cycle_comparison(intercooled, simple) -> dict {work_gain_pct, eta_delta_pp}
  (gain of intercooled over simple: (w_net_i - w_net_s)/w_net_s * 100,
  and (eta_i - eta_s) * 100 in percentage points).
ValueErrors: T_1 <= 0, T_3 <= T_1, pi_total <= 1, eta_c/eta_t not in
(0, 1], eps_ic outside [0, 1].

Identity to test: with eps_ic = 0 the intercooled cycle degenerates toward
the two-stage cycle without intercooling whose total work equals the
single-stage work (approximately, for the same eta_c); optimum intercooler
pressure ratio of pi_total = 36 is 6.0; a higher-effectiveness intercooler
reduces total compressor work for fixed pi_total.

## Worked example

Verified at prep: T_1 = 288 K, T_3 = 1500 K, pi_total = 30, eps_ic = 0.8,
eta_c = 0.85, eta_t = 0.9:
- pi_1 = pi_2 = 5.4772 (sqrt of 30).
- T_2a = 499.97 K; T_ic_exit = 330.39 K; T_2b = 573.57 K.
- w_c1 = 213.03 kJ/kg; w_c2 = 244.39 kJ/kg; w_c_total = 457.42 kJ/kg.
- w_t = 843.34 kJ/kg; w_net = 385.91 kJ/kg; q_in = 931.06 kJ/kg;
  eta_th = 0.4145.
- Simple cycle: w_net = 283.99 kJ/kg; eta = 0.4311.
- Comparison: work_gain_pct = +35.9 percent; eta_delta_pp = -1.66
  percentage points (intercooling raises specific work while slightly
  reducing thermal efficiency without regeneration - the documented
  intercooling trade).
Run your module and take the real outputs as assert targets; anchors above
prep-verified (closed-form stage relations).

## Validation list (contract test must include)

- optimum_intercooler_pressure_ratio(36) == 6.0 and of 30 == 5.4772.
- Stage exit temperature rises with pi_stage and falls with eta_c.
- Intercooler exit temperature: eps_ic 0 returns the hot inlet; eps_ic 1
  returns the coolant temperature.
- Worked-example anchors within 1 percent (w_c_total 457.4 kJ/kg, w_net
  385.9 kJ/kg, eta 0.4145, gain +35.9 percent).
- epsilon = 0 comparison: two-stage no-cooling total work approximates the
  single-stage work within a small tolerance (no-cooling two-stage with
  same eta_c does the same total work).
- eta_th strictly between 0 and 1 for the example.
- ValueErrors for non-physical inputs.
- Determinism.

## Corpus fragment (eval/hit1-wave38-intercooled-cycle.yaml)

Query 1 (copy verbatim):
  "analyze the intercooled-brayton-cycle with two-stage compression and the optimum intercooler-pressure-ratio to minimize compressor work"
  intent: "propulsion; intercooled gas turbine cycle with optimum pressure split"
  expected_skill: "propulsion/gas-turbine-cycle/intercooled-cycle"
Query 2 (copy verbatim):
  "compute the intercooler-effectiveness exit temperature and the specific-work gain of the intercooled cycle over the simple cycle"
  intent: "propulsion; intercooler effectiveness and cycle comparison"
  expected_skill: "propulsion/gas-turbine-cycle/intercooled-cycle"
Task ids: w38-intercooled-cycle-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze a gas turbine cycle with
intercooling:" and include the outputs in the Claim. First tag:
intercooled-cycle. Additional tags ONLY: intercooler-effectiveness,
intercooler-pressure-ratio, two-stage-compression, compression-work-split,
cycle-work-gain. NEVER single generic words (intercooler, cycle,
efficiency, work, compression, stage). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): regenerator effectiveness,
recuperator (regenerative-cycle); afterburner, reheat (afterburner-cycle);
pressure ratio of the simple ideal Brayton cycle alone (gas-turbine-cycle);
component loss, polytropic efficiency (real-cycle-effects).
