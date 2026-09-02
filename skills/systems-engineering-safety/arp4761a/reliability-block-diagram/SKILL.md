---
name: reliability-block-diagram
description: "Use when you must analyze aircraft system reliability with a reliability block diagram (RBD) per ARP4761A: evaluate a structure of blocks in series from constant failure-rate components, compute component and system mission reliability R(t) = exp(-lambda t), combine series, active parallel, k-out-of-n voting and cold standby redundancy blocks, derive exact block and system MTBF, convert a non-exponential block to an equivalent failure rate -ln(R)/t, and identify the dominant component whose failure rate drives system reliability by one-at-a-time sensitivity analysis. Parses a block structure of rates and returns system reliability, MTBF, per-block reliabilities and the dominant component. Produces the quantitative series-parallel reliability view that complements the fault tree logic view. Trigger: reliability block diagram, RBD, series parallel reliability, redundancy, k-out-of-n, standby, MTBF, mission reliability, failure rate."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [reliability-block-diagram, series-parallel-reliability, rbd, redundancy-modeling, k-out-of-n-reliability, cold-standby, mtbf, mission-reliability, failure-rate, dominant-component]
  version: 0.1.0
  author: AeroSkills
---

# Reliability Block Diagram (systems-engineering-safety/arp4761a/reliability-block-diagram)

Use when the task is evaluating a system architecture as a reliability
block diagram (RBD): success logic expressed as blocks in series whose
internal redundancy is active parallel, k-out-of-n voting, or cold
standby. This leaf computes the quantitative reliability view of the
architecture over a mission: it complements the fta-fmea leaf, which
derives the failure logic and cut sets for the same system. All logic
is deterministic offline stdlib; no repair is modeled (use
markov-analysis for repairable and state-space models).

## Domain quick reference

- Constant-rate component model: R(t) = exp(-lambda * t), MTBF =
  1 / lambda. Mission time t in hours; rates in failures per hour.
- Series blocks (all items must work): R_s = product(R_i), and for
  exponentials the block stays exponential with lambda_s =
  sum(lambda_i), MTBF_s = 1 / lambda_s.
- Active parallel (1 of n, rates may differ): R_p = 1 - product(1 -
  R_i). Identical units at rate lambda give the closed form
  R_p = 1 - (1 - exp(-lambda t))^n and MTBF = (1/lambda) * H_n with
  H_n the n-th harmonic number, for example 3/(2 lambda) for a pair.
- k-out-of-n voting (identical units, rate lambda): R = sum_{j=k..n}
  C(n, j) R_u^j (1 - R_u)^(n - j) with R_u = exp(-lambda t); MTBF =
  (1/lambda) * sum_{j=k..n} 1/j. 2 of 3 gives R = 3 R_u^2 - 2 R_u^3.
- Cold standby (1 of 2 identical units, perfect switching):
  R_standby(t) = exp(-lambda t) * (1 + lambda t), MTBF = 2 / lambda.
  Imperfect switching folds the switch failure rate into the standby
  gain: R = exp(-lambda t) * (1 + (lambda + switch_rate) t). That
  simplified form is a leading-order approximation; it stays accurate
  while the switch hazard switch_rate * t is small, and for a
  state-space or repairable treatment of switching use the
  markov-analysis leaf.
- Equivalent block failure rate for a non-exponential block over
  mission t: lambda_block = -ln(R_block(t)) / t (exact sum for a pure
  series block). System mission rate is -ln(R_sys(t)) / t.
- Dominant component: one-at-a-time sensitivity scales each rate by
  (1 + pct/100) and reports the elasticity
  e = (R - R_perturbed) / (R * pct/100), which approximates
  -(dR/dlambda) * lambda / R at the operating point. The component
  with the largest elasticity drives system reliability.

## Workflow

1. Lay out the architecture as a block structure: a list of block
   dicts connected in series. Each block is one of the four types:
   series, parallel, kofn, standby (see evaluate_rbd docstring).
2. Collect a constant failure rate per component from the
   failure-rate-estimation leaf or data sources, plus the mission
   time t at which reliability is wanted (design life or flight
   duration).
3. Evaluate the structure with evaluate_rbd(structure, t) to get the
   system mission reliability, the exact system MTBF, the per-block
   reliabilities, and the dominant component.
4. Drill into any single block with block_reliability, block_mtbf and
   block_equivalent_rate, or evaluate bare primitives
   (series_reliability, parallel_reliability, kofn_reliability,
   standby_reliability) for a quick configuration comparison.
5. Rank architectures: same components as active parallel, 2-of-3
   voting, or cold standby rarely have the same reliability or MTBF;
   compare mission reliability at the design life and the sensitivity
   report.
6. Convert per-block or system mission reliabilities into equivalent
   failure rates when feeding PSSA/SSA probability allocations or
   comparing against the FHA probability requirement for the failure
   condition.

## Worked example

Dual hydraulic actuators (each lambda = 1e-4 per hour) in active
parallel, in series with a controller (lambda = 5e-5), mission t = 10
h.

- Component: R_each = exp(-1e-3) = 0.9990005 (0.99900 within 1%).
- Actuator pair: R_par = 1 - (1 - 0.9990005)^2 = 0.9999990 (within 1%
  of 0.999999), block MTBF = 3 / (2 * 1e-4) = 15000 h, equivalent
  block rate at t = 10 is about 1e-7 per hour.
- System: R_sys = 0.9999990 * exp(-5e-4) = 0.9994991 (0.9994995
  within 1%); exact system MTBF = 2/1.5e-4 - 1/2.5e-4 = 9333.33 h.
- Dominant component at t = 10 h: the controller (series single item,
  elasticity 5.0e-4) rather than an actuator (elasticity 1.0e-6):
  redundancy masks each actuator, the controller is a single point.

2 of 3 voting computers at lambda = 1e-4 per hour, t = 100 h:
R_u = exp(-0.01) = 0.99005, R_2of3 = 3 R_u^2 - 2 R_u^3 =
0.99970495, MTBF = (1e4) * (1/2 + 1/3) = 8333.33 h. Same components
and mission, reliability ranking: cold standby 0.9999503 > active
parallel pair 0.9999010 > 2 of 3 voting 0.9997050 > single 0.99005.
Voting exists for fault masking and integrity, not for peak
reliability; standby saves the dormant unit from wear so it wins on
long missions, while active parallel wins when the switch hazard is
significant.

## Verification

- Confirm R_each, R_par and R_sys of the worked example within 1% of
  0.99900, 0.999999 and 0.9994995.
- Confirm the 2 of 3 mission reliability 0.99970495 and MTBF 8333.33 h.
- Confirm evaluate_rbd returns the dominant component dict pointing at
  the controller block (block_index 1).
- Confirm exact identities: k-of-n with k = 1 equals active parallel;
  k = n equals series; series block MTBF is 1 / sum(rates); cold
  standby MTBF is 2 / lambda.
- Confirm every non-physical input raises ValueError: negative or zero
  rates, negative time, k outside 1..n, non-identical units in kofn or
  standby blocks, standby without exactly 2 items, an empty structure,
  an unknown block type, an empty items list.
- Run the contract test offline: python3
  scripts/test_reliability_block_diagram.py (33 tests, deterministic).

## Pitfalls

- Routing here, not to fta-fmea: RBD gives the quantitative
  series-parallel reliability and MTBF view; fault tree analysis
  derives minimal cut sets and the failure logic for the same
  architecture.
- Routing here, not to markov-analysis: this leaf models non-repairable
  blocks with constant rates and exact closed forms; repairable
  systems, availability, and state-space standby or non-identical
  standby belong to the Markov leaf.
- Routing here, not to failure-rate-estimation: this leaf consumes
  component failure rates; demonstrating or estimating those rates
  from test or service data is the failure-rate-estimation job.
- Reading k-of-n as active parallel: 2 of 3 voting is less reliable
  than a parallel pair of the same units but masks a single failed
  unit's output, which is why voting architectures exist.
- Applying the imperfect-switch standby form with a large switch_rate:
  the simplified form drifts above unity once switch_rate * t is not
  small; keep it to the low switch hazard regime.
- Quoting the exact per-block MTBF for an active parallel block with
  very many items: exact evaluation uses an exponential-term expansion
  that caps at 16 items per parallel block; pre-combine series paths
  into single rates for larger structures.
- Assuming blocks are independent when they share power, cooling or
  installation: common cause failures need the common-cause-analysis
  leaf, which is outside the plain RBD model.

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: the logic view of the
  same architecture, minimal cut sets over failure events; RBD
  provides the quantitative series-parallel reliability counterpart.
- systems-engineering-safety/arp4761a/failure-rate-estimation: the
  source of the component failure rates and MTBF bounds fed into the
  block structure.
- systems-engineering-safety/arp4761a/markov-analysis: repairable,
  state-space and non-identical standby modeling when the static RBD
  assumptions do not hold.
- systems-engineering-safety/arp4761a/common-cause-analysis: checks
  that the independence assumption behind series-parallel math holds.
- systems-engineering-safety/arp4761a/zonal-safety-analysis: physical
  separation and installation-level independence that the RBD
  reliability numbers assume.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_reliability_block_diagram.py

The test covers the worked-example numbers within 1%, the series and
parallel closed forms, k-of-n edges, cold standby with perfect and
simplified imperfect switching, exact MTBF values, block and system
equivalent rates, one-at-a-time sensitivity ranking, round-trip
identities, and ValueError rejection of non-physical structures and
inputs.

## Compliance

- Standards referenced, not reproduced: ARP4761A text is proprietary
  (SAE); the reliability block diagram method and the constant-rate
  series-parallel formulas are common engineering methodology,
  summary-only per standards-map.yaml.
- The leaf is a static, non-repairable constant-rate model with stated
  assumptions; it does not reproduce standard tables or sections.
- compliance: STANDARDS-REF, gated: false.
