# Wave-41 leaf spec: polytropic-efficiency (propulsion, axial-compressor pack)

- Path: skills/propulsion/axial-compressor/polytropic-efficiency/
- Pack: axial-compressor (present siblings axial-compressor-stage,
  compressor-map, multi-stage-compressor, turbine-blade-cooling,
  turbine-stage; adjacent fences in propulsion/gas-turbine-cycle/
  real-cycle-effects and propulsion/turboprop/free-turbine).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the conversion):
  - real-cycle-effects (gas-turbine-cycle pack) computes the real cycle
    from component efficiencies given AS ISENTROPIC: its description
    reads "compute the real-cycle gas turbine performance with component
    losses: the compressor exit temperature and the turbine exit
    temperature from the pressure ratio and the component-efficiency
    (isentropic-efficiency) of each machine, the real-cycle thermal
    efficiency of the non-ideal Brayton cycle..." with the whole-drop
    forms T2 = T1 * (1 + (PR**((gamma-1)/gamma) - 1)/eta_c) and
    T4 = T3 - eta_t * (T3 - T4s). It consumes isentropic efficiencies
    over the full machine ratio and never converts between the
    isentropic and polytropic senses; its model is the isentropic
    (whole-drop) cycle view, and its Pitfalls already warn "Passing
    eta_c or eta_t above 1: non-physical (the exit would be colder than
    isentropic)".
  - free-turbine (turboprop pack) CONSUMES a polytropic efficiency as an
    input: its description reads "compute the power-turbine exit
    temperature and shaft power from the gas generator exhaust state
    (mass flow, inlet temperature, expansion ratio, polytropic
    efficiency)..." with t06 = t05 * (1 - eta_pt *
    (1 - pr**((1-gamma)/gamma))). It takes eta_pt as given for the
    power-section matching and does not derive, convert or validate it
    against an isentropic value.
  - multi-stage-compressor (this pack) owns the stage-count arithmetic:
    "compute the overall pressure ratio as the product of the stage
    pressure ratios, size the stage count required to reach the target
    pressure ratio from a design stage pressure ratio, account for the
    reheat factor that inflates the actual work split..." with the
    work-based reheat factor "RF = W_actual / W_ideal_sum ... typical
    values run from 1.01 to 1.06 and grow with the stage count". Its RF
    is a WORK-split quantity; it performs no isentropic-to-polytropic
    efficiency conversion.
  - axial-compressor-stage (this pack) analyzes ONE stage by velocity
    triangles: specific work, flow coefficient, work coefficient, degree
    of reaction, and the stage pressure ratio
    pi = (1 + eta*w/(cp*t01))**(gamma/(gamma-1)) with a single
    efficiency eta (default 0.9) applied to the stage work. It relates
    no per-stage efficiency to an overall efficiency and converts
    nothing.
  Whole-tree greps at prep: "polytropic" hits only the free-turbine
  SKILL/script (input consumption) and the axial-compressor-stage script
  internals; "stage-count-independent" = 0 hits in skills/. GENUINE
  propulsion gap (fresh probe): no leaf converts between isentropic and
  polytropic efficiency, states the stage-count independence of eta_p,
  or cross-checks per-stage against overall pressure ratio on the log
  scale; real-cycle-effects takes its efficiencies as isentropic
  (whole-drop) and free-turbine takes eta_pt as given.
- Standards id: far-33 (reference-only, present in standards-map.yaml).
  Ledger Standard: far-33.
- Family: propulsion

## Claim

Convert between the isentropic and the polytropic efficiency of a
compressor or a turbine for performance sizing: recover the polytropic
efficiency from the isentropic efficiency at any overall pressure
ratio, and the reverse; recover either efficiency from measured inlet
and exit total states; restate the same polytropic efficiency at the
per-stage pressure ratio to show it is stage-count independent while
the isentropic efficiency depends on the pressure ratio it is quoted
at (falls as overall pressure ratio grows for a compressor at fixed
eta_p, rises toward 1 for a turbine); and cross-check the per-stage
pressure ratio list against the overall ratio with the log-sum
identity R = sum(ln pr_i)/ln(pr_overall), the pressure-ratio-side
statement of the reheat-factor discussion, which equals 1 exactly when
the stage product matches the overall ratio and flags inconsistent
stage data otherwise. Produces the converted efficiencies, the
per-stage and overall efficiency pair at a fixed eta_p, the stage-count
independence verdict and the reheat-factor log-sum check value, in the
air-standard gamma = 1.4 closed forms that gate compressor and turbine
performance sizing. Does NOT do: actual station temperatures, real
cycle thermal efficiency or actual SFC from component efficiencies
(real-cycle-effects, isentropic whole-drop cycle view); the power
turbine exit temperature, shaft power or spool matching that consume an
eta_pt input (free-turbine); the overall-pressure-ratio product, stage
count or the WORK-based reheat factor RF = W_actual/W_ideal_sum that
inflates with stage count (multi-stage-compressor); single-stage
velocity-triangle parameters or a stage pressure ratio from stage work
(axial-compressor-stage). Air-standard gamma only; the temperature
dependence of specific heat is out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants: GAMMA = 1.4
(air) and KAPPA = (GAMMA - 1) / GAMMA (= 2/7, about 0.285714).

Defining relations (pin these exactly; every function below derives
from them):
- Compressor polytropic relation: t02/t01 = pr**((GAMMA-1)/
  (GAMMA*eta_p)) = pr**(KAPPA/eta_p), so on the log scale
  ln(t02/t01) = (KAPPA/eta_p)*ln(pr). The polytropic efficiency sits
  in the DENOMINATOR of the exponent because the actual temperature
  RISE exceeds the isentropic rise at every small stage.
- Turbine polytropic relation mirrors the compressor with the
  temperature ratio inverted: ln(t03/t04) = eta_p*KAPPA*ln(pr), so
  t04/t03 = pr**(-KAPPA*eta_p). The efficiency MULTIPLIES the exponent
  on the turbine side because the actual temperature DROP falls short
  of the isentropic drop, the exact mirror of the compressor sign
  convention. Resolving eta_p from states on this relation gives
  eta_p = ln(t03/t04)/(KAPPA*ln(pr)).
- Isentropic whole-drop parametrization of the same exit states
  (consistent with the real-cycle-effects fence forms):
  compressor t02/t01 = 1 + (pr**KAPPA - 1)/eta_s;
  turbine t04/t03 = 1 - eta_s*(1 - pr**(-KAPPA)).
  The two parametrizations describe the SAME actual exit temperature,
  and the conversions below are the exact algebra between them, so the
  eta_p they imply IS the small-stage polytropic efficiency: the
  exponent form pr**(KAPPA/eta_p) is the exact integral of the
  small-stage relation dT/T = (KAPPA/eta_p)*dp/p.

Functions:
- compressor_polytropic_from_states(t01, t02, pr) -> float
  KAPPA*ln(pr)/ln(t02/t01), the closed form resolved from the defining
  relation t02/t01 = pr**(KAPPA/eta_p) (both states are required).
  ValueError if t01 <= 0, t02 <= 0, t02 <= t01 (no compression), or
  pr <= 1.
- compressor_isentropic_from_polytropic(eta_p, pr) -> float
  (pr**KAPPA - 1)/(pr**(KAPPA/eta_p) - 1), from eta_s =
  (t02s - t01)/(t02 - t01) with the polytropic and isentropic ratios.
  ValueError if eta_p outside (0, 1] or pr <= 1.
- compressor_polytropic_from_isentropic(eta_s, pr) -> float
  KAPPA*ln(pr)/ln(1 + (pr**KAPPA - 1)/eta_s), the exact inverse of the
  previous function at fixed pr. ValueError if eta_s outside (0, 1] or
  pr <= 1.
- turbine_polytropic_from_states(t03, t04, pr) -> float
  ln(t03/t04)/(KAPPA*ln(pr)), resolved from t04/t03 = pr**(-KAPPA*
  eta_p) (both states required; pr is the expansion ratio p03/p04 > 1).
  ValueError if t03 <= 0, t04 <= 0, t04 >= t03 (no expansion), or
  pr <= 1.
- turbine_isentropic_from_polytropic(eta_p, pr) -> float
  (1 - pr**(-KAPPA*eta_p))/(1 - pr**(-KAPPA)), from eta_s =
  (t03 - t04)/(t03 - t04s). ValueError if eta_p outside (0, 1] or
  pr <= 1.
- turbine_polytropic_from_isentropic(eta_s, pr) -> float
  ln(1 - eta_s*(1 - pr**(-KAPPA)))/(-KAPPA*ln(pr)), the exact inverse
  of the previous function at fixed pr (numerator and denominator are
  both negative for pr > 1 and eta_s in (0, 1]). ValueError if eta_s
  outside (0, 1] or pr <= 1.
- reheat_factor_check(stage_prs, overall_pr) -> float
  sum(ln(pi) for pi in stage_prs)/ln(overall_pr), the log-sum
  consistency ratio on the pressure-ratio side. Because the polytropic
  stage terms are additive on the log scale, R = 1 exactly when the
  product of the stage ratios equals the overall ratio (equal-stage
  identity); R below or above 1 flags stage data inconsistent with the
  quoted overall ratio. This is NOT the work-based reheat factor
  RF = W_actual/W_ideal_sum >= 1 of the multi-stage-compressor leaf
  (that quantity inflates with the stage count and is not computed
  here); R is the identity behind the classic reheat discussion in the
  efficiency sense, restating stage-count independence on the pressure
  side. ValueError if stage_prs is empty, any stage pr <= 1, or
  overall_pr <= 1.

Identities to test (closed form, exact):
- Round trips at fixed pr: isentropic_from_polytropic(
  polytropic_from_isentropic(eta_s, pr), pr) == eta_s and the turbine
  mirror, both within float noise (1e-12).
- from-states consistency: building t02 = t01*(1 + (pr**KAPPA - 1)/
  eta_s) and calling compressor_polytropic_from_states returns exactly
  compressor_polytropic_from_isentropic(eta_s, pr); the turbine mirror
  with t04 = t03*(1 - eta_s*(1 - pr**(-KAPPA))).
- Stage-count independence: for a stage ratio list whose product equals
  the overall ratio, eta_p recovered from the overall states equals
  eta_p recovered from one stage's states (log additivity), while the
  isentropic efficiency differs between the stage ratio and the overall
  ratio at that fixed eta_p.
- Ordering: for pr > 1 the compressor isentropic efficiency is BELOW
  its polytropic efficiency, the turbine isentropic efficiency is ABOVE
  its polytropic efficiency, and both coincide with eta_p as pr
  approaches 1 from above.
- Monotonicity: at fixed eta_p the compressor eta_s falls as pr grows
  (toward 0), the turbine eta_s rises as the expansion ratio grows
  (toward 1); neither ever leaves (0, 1).
- reheat_factor_check returns 1 (within 1e-12) for any stage list whose
  product equals overall_pr, and deviates from 1 otherwise.
- ValueErrors across the module: pr <= 1 (all pr arguments), eta <= 0
  or eta > 1 (all eta arguments), t02 <= t01, t04 >= t03, non-positive
  temperatures, empty stage_prs, any stage pr <= 1.

## Worked example

Multistage compressor: overall pressure ratio 20, design stage pressure
ratio 1.2, isentropic efficiency 0.85 quoted at the overall ratio (the
same PR 20 / eta_c 0.85 / T1 288.15 point the real-cycle-effects leaf
works, where it reports T2 about 747 K). All values below are REAL
outputs of the prep anchor /tmp/w41spec/anchor_polytropic.py (stdlib
math, closed form).
- Effective stage count implied by the two ratios:
  ln(20)/ln(1.2) = 16.431, matching the multi-stage-compressor
  stage-count arithmetic (its ceil gives 17 stages).
- compressor_polytropic_from_isentropic(0.85, 20) = 0.898525: the
  stage-count-independent polytropic efficiency behind an isentropic
  0.85 at overall PR 20. eta_s = 0.85 sits below eta_p = 0.8985 as
  expected for a compressor at pr > 1.
- The SAME eta_p quoted at the per-stage ratio 1.2:
  compressor_isentropic_from_polytropic(0.898525, 1.2) = 0.895862, the
  per-stage isentropic efficiency, ABOVE the overall 0.85: the overall
  machine re-compresses each stage's reheat loss, so the overall
  isentropic efficiency at fixed eta_p falls as the overall pressure
  ratio grows.
- Reverse round trip at the overall ratio recovers the input exactly:
  compressor_isentropic_from_polytropic(0.898525, 20) = 0.85.
- From-states view (t01 = 288.15 K): the whole-drop exit ratio
  t02/t01 = 1 + (20**KAPPA - 1)/0.85 = 2.592408 gives
  t02 = 747.002 K (the real-cycle-effects anchor value), and
  compressor_polytropic_from_states(288.15, 747.002, 20) = 0.898525,
  identical to the from-isentropic result. Per stage the ratio is
  1.2**(KAPPA/0.898525) = 1.059688, and
  compressor_polytropic_from_states(288.15, 288.15*1.059688, 1.2) =
  0.898525: the SAME eta_p at the stage level and the overall level,
  stage-count independence verified (the two values agree to 1e-12).
- Fixed eta_p = 0.898525, isentropic efficiency versus pressure ratio:
  PR 1.2 -> 0.895862, PR 2 -> 0.888187, PR 5 -> 0.873663, PR 10 ->
  0.862070, PR 20 -> 0.850000, PR 40 -> 0.837497. eta_s falls as PR
  grows for fixed eta_p, the headline sizing behavior.
- reheat_factor_check cross-checks: 16 stages at 1.2 against their own
  product 1.2**16 = 18.49 gives R = 1 (0.9999999999999999, the
  equal-stage identity); the same 16 stages claimed against overall 20
  give R = 0.973767 and 17 stages claimed against overall 20 give
  R = 1.034627, both flagging stage data inconsistent with the quoted
  overall ratio (the consistent picture is the 16.431 effective stages
  of ln(20)/ln(1.2)).
- Turbine mirror (expansion ratio 3, TIT 1500 K):
  turbine_polytropic_from_isentropic(0.88, 3) = 0.862061 (BELOW the
  isentropic 0.88, the reverse of the compressor ordering), round trip
  turbine_isentropic_from_polytropic(0.862061, 3) = 0.88, and with
  t04 = 1500*(1 - 0.88*(1 - 3**(-KAPPA))) = 1144.392 K,
  turbine_polytropic_from_states(1500, 1144.392, 3) = 0.862061, the
  exponent form t04/t03 = 3**(-KAPPA*0.862061) = 0.762928 agreeing
  with the whole-drop form to all printed digits. At the same eta_p
  the turbine isentropic efficiency RISES with the expansion ratio:
  eta_s = 0.88 at ratio 3 becomes 0.897934 at ratio 10.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified, computed by running the prep anchor
script /tmp/w41spec/anchor_polytropic.py (prep-verified by stdlib
math).

## Validation list (contract test must include)

- compressor_polytropic_from_isentropic(0.85, 20) = 0.898525 within
  1e-6; round trip to 0.85 within 1e-12.
- compressor_isentropic_from_polytropic(0.898525, 1.2) = 0.895862
  within 1e-6.
- compressor_polytropic_from_states(288.15, 747.002, 20) = 0.898525
  within 1e-6, and per-stage (288.15, 288.15*1.059688, 1.2) =
  0.898525 within 1e-6 (stage-count independence to 1e-12 between the
  two from-states values).
- Fixed eta_p 0.898525 monotone fall: eta_s at PR 10 = 0.862070, at
  PR 40 = 0.837497 within 1e-6; ordering eta_s_stage > eta_s_overall.
- turbine_polytropic_from_isentropic(0.88, 3) = 0.862061 within 1e-6;
  round trip to 0.88 within 1e-12; turbine_polytropic_from_states(
  1500, 1144.392, 3) = 0.862061 within 1e-6; turbine
  isentropic_from_polytropic(0.862061, 10) = 0.897934 within 1e-6,
  turbine ordering eta_s > eta_p at ratio 3.
- reheat_factor_check([1.2]*16, 1.2**16) = 1 within 1e-12;
  reheat_factor_check([1.2]*16, 20) = 0.973767 within 1e-6;
  reheat_factor_check([1.2]*17, 20) = 1.034627 within 1e-6.
- ValueErrors: compressor and turbine eta arguments at 0, 1.5 and 1.01;
  pr at 1.0 and 0.5; compressor_polytropic_from_states with t02 == t01
  and with t02 < t01; turbine_polytropic_from_states with t04 == t03
  and t04 > t03; non-positive temperatures; reheat_factor_check with an
  empty list and with a stage pr of 1.0.
- Determinism; no imports beyond math; gamma fixed at 1.4.

## Corpus fragment (eval/hit1-wave41-polytropic-efficiency.yaml)

Query 1 (copy verbatim):
  "convert the polytropic-efficiency of the multistage axial compressor to the isentropic-efficiency at the overall pressure ratio, and recover the per-stage isentropic-efficiency from the same stage-count-independent polytropic-efficiency for the performance sizing"
  intent: "propulsion; compressor polytropic-to-isentropic efficiency conversion at overall and per-stage pressure ratio, stage-count-independent polytropic efficiency"
  expected_skill: "propulsion/axial-compressor/polytropic-efficiency"
Query 2 (copy verbatim):
  "convert the turbine isentropic-efficiency to the polytropic-efficiency at the expansion ratio, then run the reheat-factor cross-check on the per-stage pressure ratios against the overall pressure ratio of the compressor"
  intent: "propulsion; turbine isentropic-to-polytropic efficiency conversion and the log-sum reheat-factor cross-check on per-stage pressure ratios"
  expected_skill: "propulsion/axial-compressor/polytropic-efficiency"
Task ids: w41-polytropic-efficiency-1 and -2. Prep grep: none of the
distinctive phrases (polytropic-efficiency, stage-count-independent,
isentropic-to-polytropic, reheat-factor-cross-check, "per-stage
pressure ratio", "convert between") appears in any existing
hit1-corpus.yaml task; the free-turbine task that mentions "polytropic
efficiency" routes on power-turbine exit temperature and shaft power
from gas generator exhaust, and the real-cycle tasks route on the
Brayton cycle efficiency and actual-SFC wording, so the queries above
are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must convert between the isentropic
and the polytropic efficiency of a compressor or a turbine for
performance sizing:" and include the outputs in the Claim. First tag:
polytropic-efficiency. Additional tags ONLY:
isentropic-to-polytropic-conversion, polytropic-to-isentropic-
conversion, stage-count-independent-efficiency,
reheat-factor-cross-check. NEVER single generic words (efficiency,
conversion, compressor, turbine, pressure, ratio, stage, polytropic,
isentropic, sizing). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term (the banned word from the builder kit),
action verb present.

FORBIDDEN TOKENS (belong to siblings): brayton-cycle, real-cycle,
thermal-efficiency, actual-sfc, combustor-pressure-loss,
component-losses, off-ideal-brayton, station-temperature
(real-cycle-effects); free-turbine, power-turbine, gas-generator,
shaft-power, gear-ratio, spool-matching, flow-function, torque,
reduction-gearbox (free-turbine); overall-pressure-ratio-product,
stage-count (as a computed deliverable), annulus-area, work-
distribution, corrected-speed, equal-work-scheme, rising-work-scheme,
work-based-reheat-factor (multi-stage-compressor); velocity-triangle,
degree-of-reaction, flow-coefficient, work-coefficient, blade-speed,
axial-velocity (axial-compressor-stage); total-to-total-efficiency,
blade-row-loss, stage-loading (turbine-stage); surge-margin,
operating-line, surge-line (compressor-map); impeller-tip-speed,
slip-factor (centrifugal-compressor); mach-number, area-ratio,
isentropic-flow-relations (isentropic-flow-relations).
