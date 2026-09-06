# Wave-42 leaf spec: reliability-allocation (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/reliability-allocation/
- Pack: arp4761a (verified present at prep under
  skills/systems-engineering-safety/arp4761a/ with
  beta-factor-analysis, common-cause-analysis, event-tree-analysis,
  failure-mode-criticality, failure-rate-estimation,
  fault-tree-importance-measures, fault-tree-uncertainty-analysis,
  fmes-coverage-analysis, fta-fmea, functional-hazard-assessment,
  maintainability-prediction, markov-analysis,
  operating-support-hazard-analysis, particular-risk-analysis,
  preliminary-system-safety-assessment, reliability-block-diagram,
  reliability-growth-analysis, safety-assessment, ssa-closure,
  zonal-safety-analysis; leaf reliability-allocation absent at prep).
  GENUINE zero-owner gap (fresh probe receipt, /tmp/w42probe/ses.md):
  whole-repo grep "reliability allocation|reliability apportionment|
  mtbf allocation|failure rate budget|failure-rate budget" across all
  skills/**/SKILL.md = 0 hits repo-wide. No leaf flows a top-level
  reliability/MTBF requirement into per-item budgets; the closest
  producers split per-condition severity probability targets (PSSA)
  and the closest consumers take rates as given (reliability-block-
  diagram).
  Fences within the pack and across the family (quoted from the
  sibling leaves read in full at prep):
  - preliminary-system-safety-assessment (per-condition probability
    apportionment, one level, equal schemes only): its description
    claims it will "derive safety requirements from FHA outcomes,
    allocate function and item development assurance levels
    (FDAL/IDAL) to the proposed system architecture, and apportion
    the quantitative safety target for each failure condition across
    the contributing channels and functions"; its body fixes the
    scope "the top-level failure condition target is apportioned
    across the contributing architecture. Independent contributors
    that combine by OR (any contributor failure causes the condition)
    share the target by sum; redundant channels that must all fail
    combine by AND and share the target by product. Equal allocation
    is the simplest scheme: target / n for OR gates,
    target ** (1 / n) for AND gates", with inputs "FHA outcomes
    (failure conditions with severity categories, qualitative
    requirements, and quantitative targets such as Catastrophic at no
    more than 1e-9 per flight hour)"; its logic module
    allocate_safety_target documents "Equal allocation: 'or' gives
    target / n per contributor; 'and' gives target ** (1 / n) per
    contributor". Per-condition severity targets, OR/AND product
    logic, assurance levels and channel structures stay there.
  - reliability-block-diagram (rate consumer, never a budget
    producer): its description covers "evaluate a structure of blocks
    in series from constant failure-rate components, compute
    component and system mission reliability R(t) = exp(-lambda t)",
    its body states "Series blocks (all items must work):
    R_s = product(R_i) ... lambda_s = sum(lambda_i), MTBF_s =
    1 / lambda_s" and its workflow says to "Collect a constant
    failure rate per component from the failure-rate-estimation leaf
    or data sources"; its pitfall section reads "this leaf consumes
    component failure rates; demonstrating or estimating those rates
    from test or service data is the failure-rate-estimation job".
    Evaluating an RBD from given rates is its role; this leaf is the
    upstream flow-down that produces the per-item rates an RBD then
    consumes.
  - requirements-allocation (arp4754a pack, qualitative register
    owner): its description claims it will "assign each system
    requirement to a design item or function, check the allocation
    coverage to find the unallocated requirements"; its body states
    "The allocation register maps every requirement id to one item"
    and "Coverage review finds the unallocated requirements and the
    share of the requirement set that is allocated". It allocates
    requirement statements to items with coverage scores, never
    quantitative reliability values; this leaf allocates one numeric
    budget quantity and hands each item a numeric target that rides
    inside the item development specification.
  - maintainability-prediction (maintenance-time owner per the probe
    receipt: lambda-weighted MTTR, lognormal t50/t95, downtime
    rollup): repair-time statistics from given rates, no budgeting of
    a top-level failure-rate requirement; not read in full here,
    ownership noted from the receipt only.
  - failure-rate-estimation (rate estimator per the probe receipt:
    Poisson chi-square demonstration): demonstrates or estimates item
    rates from test and service data; this leaf takes rates (system
    target and item capability predictions) as analyst inputs and
    never estimates one from data.
- Standards id: arp4761a (guidance, SAE, proprietary-sold,
  reference-only per standards-map.yaml) and arp4754a (same status;
  the flow-down lands in item development specifications per ARP4754A
  allocated-requirements practice). Both ids verified present in
  standards-map.yaml at prep. Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Flow a top-level system reliability requirement down to the design
items by deterministic apportionment: split the system failure rate
per flight hour (or its MTBF equivalent) into per-item target rates
by equal split, where every item receives the same share and the
per-item rates sum to the system rate, or by complexity-weighted
apportionment, where each item receives system rate x w_i / sum(w)
with w an item complexity or part-count weight chosen by the design
team, produce the per-item failure-rate and MTBF targets for the item
development specifications, verify closure by summing the allocated
item rates against the system rate (the series-sum identity of a
non-redundant item chain, returning the relative error), and report
the per-item margin capability / target - 1 against predicted item
capability rates to flag which items overrun their budget and which
hold slack that can be traded. The apportionment schemes are pure
weighted splits of one top-level budget; the weights are design-team
inputs, so no external base-rate table is needed. Does NOT do:
apportioning per-condition severity probability targets (1e-9 /
1e-7 class) across architecture channels, OR/AND gate product
splits, or FDAL/IDAL assignment (preliminary-system-safety-
assessment); evaluating series-parallel or k-of-n block structures,
mission reliability or block MTBF from given rates (reliability-
block-diagram); assigning requirement statements to items with
coverage registers or unallocated-requirement lists (requirements-
allocation); repair-time statistics or downtime rollups
(maintainability-prediction); estimating rates from test or service
data (failure-rate-estimation). Deterministic closed-form splits
only: no RNG, no solvers, no standard data tables, no time
integration.

## Model (implement exactly)

Functions (pure stdlib, deterministic, no RNG):
- mtbf_to_rate(mtbf) -> float 1.0 / mtbf, the constant failure rate
  equivalent of an MTBF target in hours. ValueErrors: mtbf not a
  positive number. This is the (e) MTBF support: an MTBF system
  requirement enters the flow-down as rate = 1 / MTBF.
- equal_split(system_rate, n_items) -> list of n_items identical
  per-item target rates, each system_rate / n_items. For a
  non-redundant series chain the sum of the item rates equals the
  system rate, so equal split divides the system failure rate evenly.
  ValueErrors: system_rate not a positive number; n_items not an
  integer in 1..ITEMS_MAX.
- complexity_weighted_alloc(system_rate, weights) -> list of
  per-item target rates system_rate x w_i / sum(weights) in weights
  order, the w_i being item complexity or part-count weights (design
  data). ValueErrors: system_rate not a positive number; empty
  weights; any weight not a positive number; more than ITEMS_MAX
  weights.
- closure_check(item_rates, system_rate) -> dict {"total",
  "system_rate", "relative_error", "exact"} with total =
  sum(item_rates), relative_error = (total - system_rate) /
  system_rate, and exact = math.isclose(total, system_rate,
  rel_tol=1e-12, abs_tol=1e-12): the series-sum closure identity
  that the allocated item budgets add up to the system budget.
  ValueErrors: empty item_rates; any item rate not positive;
  system_rate not a positive number.
- margin_report(item_rates, item_capabilities) -> list of dicts
  {"item", "target", "capability", "margin"} in input order with
  margin = capability / target - 1.0. A margin below 0.0 means the
  predicted capability rate is better (lower) than the budget
  (slack); a margin above 0.0 means the predicted rate exceeds the
  budget (deficit). ValueErrors: empty lists, mismatched lengths,
  any entry not positive.
Module constants: ITEMS_MAX = 64. No severity-target constants: this
leaf allocates one system reliability budget, not per-condition
probability targets, so no target table exists in the module.

Identity to test: for equal and weighted splits the allocated item
rates sum to the system rate (relative error at float noise, exact
flag True); every weighted share equals system_rate x w_i / sum(w);
margin is exactly capability / target - 1; mtbf_to_rate round-trips
(mtbf_to_rate(mtbf) x mtbf = 1.0); the weighted share of the largest
complexity item is the largest budget.

## Worked example

Wing flap actuation system. Top-level reliability requirement: the
system shall fail at no more than system_rate = 1e-4 per flight hour
(equivalent MTBF target 10000 h), to be flowed down across six items
- pump, valve, sensor, computer, actuator, wiring - with design-team
complexity weights [1, 2, 1, 3, 2, 1] (sum 10: the dual-redundant
computer is the most complex item, the wiring run and the sensor the
least). Real module outputs from the anchor run
(/tmp/w42spec/anchor_reliability_allocation.py, stdlib math, run at
prep, exit 0):

Equal split (equal_split(1e-4, 6)): every item budget is
1.6666666666666668e-05 per flight hour (printed 1.66667e-05), MTBF
60000 h. closure_check reports total 0.0001 vs system 0.0001,
relative_error 1.36e-16, exact True: the budgets sum to the system
rate. Equal split asks the simple wiring run and the complex computer
to meet the same 60000 h MTBF, which ignores their different part
counts.

Complexity-weighted split (complexity_weighted_alloc(1e-4,
[1, 2, 1, 3, 2, 1])) per-item target rates (real anchor output):
- pump rate 1e-05 per flight hour, MTBF 100000 h
- valve rate 2e-05 per flight hour, MTBF 50000 h
- sensor rate 1e-05 per flight hour, MTBF 100000 h
- computer rate 3e-05 per flight hour, MTBF 33333.3 h
- actuator rate 2e-05 per flight hour, MTBF 50000 h
- wiring rate 1e-05 per flight hour, MTBF 100000 h
closure_check(weighted) reports total 0.0001 vs system 0.0001,
relative_error 0, exact True: the normalized weighted split sums
exactly to the target. The computer carries the largest budget
(3e-05, 33333.3 h MTBF) and the light items the smallest (1e-05,
100000 h), matching the weight ratio.

Margin report against predicted item capability rates
[9e-6, 1.6e-5, 1.2e-5, 2.8e-5, 1.8e-5, 1.1e-5] per flight hour
(margin_report(weighted, capabilities), real anchor output):
- pump target 1e-05 capability 9e-06 margin -0.1000 (slack)
- valve target 2e-05 capability 1.6e-05 margin -0.2000 (slack)
- sensor target 1e-05 capability 1.2e-05 margin +0.2000 (deficit)
- computer target 3e-05 capability 2.8e-05 margin -0.0667 (slack)
- actuator target 2e-05 capability 1.8e-05 margin -0.1000 (slack)
- wiring target 1e-05 capability 1.1e-05 margin +0.1000 (deficit)
The sensor and wiring predictions overrun their budgets while the
valve and actuator hold slack; the sum of the capability rates is
9.4e-05 against the 1e-4 system target, so the item-level prediction
still closes at system level with headroom, and the report flags the
rebalancing trade: tightening the valve budget or relaxing the sensor
budget keeps the system requirement met. A capability sum above the
system rate would mean the item budgets as predicted cannot meet the
top-level requirement and the design or the requirement must be
revisited.

Run your module and take the real outputs as assert targets; the
anchors above are prep-verified by running
/tmp/w42spec/anchor_reliability_allocation.py (stdlib math,
python3, macOS, exit 0).

## Validation list (contract test must include)

- equal_split(1e-4, 6): six entries each within 1e-15 of
  1.6666666666666668e-05; closure_check relative_error 1.36e-16,
  exact True; 1.0 / budget within 1e-9 of 60000.
- complexity_weighted_alloc(1e-4, [1, 2, 1, 3, 2, 1]): rates
  [1e-05, 2e-05, 1e-05, 3e-05, 2e-05, 1e-05] within 1e-15;
  closure_check relative_error 0, exact True; per-share identity
  rate_i = 1e-4 x w_i / 10; the computer share 3e-05 is the largest.
- mtbf_to_rate: mtbf_to_rate(10000.0) = 1e-4 within 1e-15;
  mtbf_to_rate(1e4) x 1e4 = 1.0; 1 / 3e-05 = 33333.3 h within 1e-9.
- margin_report(weighted, capabilities): margins -0.1, -0.2, +0.2,
  -0.0667, -0.1, +0.1 each within 1e-9 of capability / target - 1;
  dict keys exactly item, target, capability, margin; input order
  preserved; sum(capabilities) = 9.4e-05 < 1e-4.
- Boundary: equal_split of 64 items (ITEMS_MAX) runs and sums to the
  system rate; single item equal and weighted splits return the
  system rate itself.
- ValueErrors: system_rate 0 and -1e-4 (equal, weighted, closure);
  n_items 0, 65 and 2.5; empty weights; weight 0 and -1; empty
  item_rates; item rate 0 and -1e-5; margin_report with empty lists
  and mismatched lengths; mtbf 0 and negative.
- Determinism: two calls return equal structures; floats stable.
- Closure identity: for any non-empty positive weights and positive
  system rate, complexity_weighted_alloc followed by closure_check
  has exact True.

## Corpus fragment (eval/hit1-wave42-reliability-allocation.yaml)

Query 1 (copy verbatim):
  "flow down the system reliability requirement: allocate the 1e-4 per flight hour failure-rate budget across the six items by their complexity weights and check that the item failure-rate targets sum to the system rate"
  intent: "systems safety; complexity-weighted reliability budget flow-down and series-sum closure check"
  expected_skill: "systems-engineering-safety/arp4761a/reliability-allocation"
Query 2 (copy verbatim):
  "split the 10000 hour MTBF system target equally and by complexity weight into per-item MTBF targets for the item development specifications and report each item margin against its predicted capability rate"
  intent: "systems safety; equal and weighted MTBF target allocation to items with margin report"
  expected_skill: "systems-engineering-safety/arp4761a/reliability-allocation"
Task ids: w42-reliability-allocation-1 and -2. Whole-corpus grep at
prep (probe receipt): "reliability allocation|reliability
apportionment|mtbf allocation|failure rate budget|failure-rate
budget" = 0 hits repo-wide, so both queries are collision-free
against existing tasks; tasks that route on "fault tree", "cut set",
"Markov", "RBD", "rotor burst", "FDAL/IDAL" or "safety target" stay
with their own leaves because the queries name the flow-down of one
system reliability budget to items.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must allocate a system
reliability requirement down to the design items:" and include the
outputs in the Claim (per-item failure-rate and MTBF targets, closure
check, margin report). First tag: reliability-allocation. Additional
tags ONLY: mtbf-target-flow-down, complexity-weighted-apportionment,
item-failure-rate-budget, series-sum-closure,
capability-margin-report. NEVER single generic words (reliability,
allocation, requirement, target, rate, budget, item, margin, system,
split, weight, closure, MTBF). 50-150 words, <=1000 chars, no em
dash, no restricted content-policy wording, action verb present.

FORBIDDEN TOKENS (belong to siblings): safety-target,
per-condition, fdal, idal, dal, development-assurance,
architecture-channel, redundant-channel, OR/AND gate apportionment,
failure-condition probability (preliminary-system-safety-assessment);
series/parallel/kofn block evaluation, standby, mission-reliability,
block-structure, reliability-block-diagram (reliability-block-
diagram); mttr, maintainability, repair-time, downtime-rollup
(maintainability-prediction); allocation-coverage,
unallocated-requirements, double-allocation, requirements register
(arp4754a requirements-allocation). The series-sum closure identity
wording is the leaf's own and stays; block evaluation and per-
condition probability language never appears in the description or
tags.
