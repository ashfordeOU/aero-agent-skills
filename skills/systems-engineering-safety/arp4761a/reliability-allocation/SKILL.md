---
name: reliability-allocation
description: "Use when you must allocate a system reliability requirement down to the design items: flow one top-level failure rate per flight hour, or its MTBF equivalent, into per-item target rates by equal split or by complexity-weighted apportionment from design-team complexity weights, produce the per-item failure-rate and MTBF targets for the item development specifications, verify the series-sum closure of the item budgets against the system rate, and report each item capability margin against its predicted capability rate to flag overruns and slack for rebalancing. Produces the per-item failure-rate and MTBF targets, the closure result and the margin report. Trigger: reliability allocation, failure-rate budget, MTBF target flow-down, complexity weights, apportionment, item development specification, series-sum closure, capability margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [reliability-allocation, mtbf-target-flow-down, complexity-weighted-apportionment, item-failure-rate-budget, series-sum-closure, capability-margin-report]
  version: 0.1.0
  author: AeroSkills
---

# Reliability Allocation (systems-engineering-safety/arp4761a/reliability-allocation)

Use when you must allocate a system reliability requirement down to the
design items: flow one top-level reliability budget, expressed as a
system failure rate per flight hour or as an MTBF, into per-item target
rates and MTBF values by deterministic apportionment, then verify that
the item budgets close against the system rate and report the item
margins against predicted capability rates. This leaf implements the
equal split and complexity-weighted apportionment schemes in pure
Python, stdlib only, with no RNG and no base-rate tables: the weights
are design-team inputs. It pairs with the rate-estimation leaf for the
predicted item capability rates the margin report consumes and with the
block-evaluation leaf that later consumes the per-item targets this
leaf hands down.

Out of scope, owned by sibling leaves: apportioning failure-condition
severity probability targets across channels and assigning item
assurance levels (preliminary-system-safety-assessment); evaluating
series or parallel block structures from given rates
(reliability-block-diagram); assigning requirement statements to items
with coverage registers (requirements-allocation in the arp4754a pack);
estimating item rates from test or service data
(failure-rate-estimation); repair-time statistics (maintainability-
prediction).

## Domain quick reference

- MTBF to failure rate: rate = 1 / MTBF. An MTBF system requirement
  enters the flow-down as its rate equivalent (mtbf_to_rate).
- Equal split: item target i = system_rate / n_items. For a
  non-redundant series chain the item rates sum to the system rate, so
  every item carries the same share and the same MTBF target,
  n_items x system MTBF.
- Complexity-weighted apportionment: item target i = system_rate x
  w_i / sum(w), with w the item complexity or part-count weights
  chosen by the design team (complexity_weighted_alloc). The
  normalized weighted split also sums to the system rate.
- Series-sum closure: total = sum(item rates), relative_error =
  (total - system_rate) / system_rate, exact when total matches the
  system rate within rel_tol 1e-12 (closure_check). The allocated
  item budgets must add back up to the system budget.
- Capability margin: margin = capability / target - 1 (margin_report).
  A negative margin means the predicted capability rate is better,
  lower, than the budget (slack); a positive margin means the
  predicted rate exceeds the budget (deficit, an overrun).
- Item MTBF target: MTBF_i = 1 / rate_i, the reciprocal of the item
  target rate, is the value recorded in the item development
  specification.
- Units: failure rate in failures per flight hour, MTBF in hours.
- ARP4761A frames the safety assessment process and ARP4754A the
  allocated-requirements practice that carries numeric targets into
  item development specifications; both are reference-only here.

## Workflow

1. Fix the top-level reliability budget: state the system requirement
   as system_rate failures per flight hour. If the requirement is an
   MTBF, convert it with mtbf_to_rate so the budget is a rate.
2. Choose the apportionment scheme: equal_split when the items are
   comparable, or complexity_weighted_alloc with the design-team
   complexity weights when part counts differ. The weights are item
   complexity or part-count estimates, design data, not table lookups.
3. Produce the per-item failure-rate and MTBF targets: take the item
   target rates from the chosen split and convert each to its MTBF
   target with mtbf_to_rate.
4. Verify the series-sum closure: run closure_check on the allocated
   item rates against the system rate and confirm the relative error
   sits at float noise with the exact flag True.
5. Report the capability margins: run margin_report with the item
   target rates and the predicted item capability rates, then flag the
   items with positive margin (budget overrun) and negative margin
   (slack) and weigh the rebalancing trade between them.
6. Record the per-item targets in the item development specifications:
   one failure-rate target and one MTBF target per item, per ARP4754A
   allocated-requirements practice.
7. Confirm the deterministic checks with the contract test
   scripts/test_reliability_allocation.py.

## Worked example

Wing flap actuation system. Top-level reliability requirement: the
system shall fail at no more than 1e-4 per flight hour, the equivalent
of a 10000 h MTBF target, flowed down across six items: pump, valve,
sensor, computer, actuator, wiring, with design-team complexity weights
[1, 2, 1, 3, 2, 1] (sum 10). The dual-redundant computer is the most
complex item, the wiring run and the sensor the least.

- Equal split, equal_split(1e-4, 6): every item budget is
  1.6666666666666667e-05 per flight hour, an MTBF target of 60000 h.
  closure_check reports total 0.00010000000000000002 against system
  rate 0.0001, relative error 1.36e-16, exact True: the budgets sum to
  the system rate. Equal split asks the simple wiring run and the
  complex computer to meet the same 60000 h MTBF, ignoring their
  different part counts.
- Complexity-weighted split, complexity_weighted_alloc(1e-4,
  [1, 2, 1, 3, 2, 1]): pump 1e-05 per flight hour (100000 h MTBF),
  valve 2e-05 (50000 h), sensor 1e-05 (100000 h), computer 3e-05
  (33333.3 h), actuator 2e-05 (50000 h), wiring 1e-05 (100000 h).
  closure_check reports relative error 0 and exact True: the
  normalized weighted split sums exactly to the target. The computer
  carries the largest budget, 3e-05, and the light items the smallest,
  1e-05, matching the weight ratio.
- Margin report against predicted capability rates [9e-6, 1.6e-5,
  1.2e-5, 2.8e-5, 1.8e-5, 1.1e-5] per flight hour: margins -0.1000
  (pump), -0.2000 (valve), +0.2000 (sensor), -0.0667 (computer),
  -0.1000 (actuator), +0.1000 (wiring). The sensor and wiring
  predictions overrun their budgets while the valve and actuator hold
  slack. The capability rates sum to 9.4e-05 against the 1e-4 system
  target, so the item-level prediction still closes at system level
  with headroom, and the report flags the rebalancing trade: tighten
  the valve budget or relax the sensor budget and the system
  requirement stays met. A capability sum above the system rate would
  mean the item budgets as predicted cannot meet the top-level
  requirement and the design or the requirement must be revisited.

## Verification

- Confirm equal_split(1e-4, 6) returns six budgets each
  1.6666666666666667e-05 per flight hour and that 1.0 / budget is
  60000 h within 1e-9.
- Confirm complexity_weighted_alloc(1e-4, [1, 2, 1, 3, 2, 1]) returns
  [1e-05, 2e-05, 1e-05, 3e-05, 2e-05, 1e-05] and that the computer
  share, 3e-05, is the largest budget.
- Confirm the closure identities: every equal and weighted split of a
  positive system rate closes with relative error at float noise and
  the exact flag True; mtbf_to_rate round-trips (rate x MTBF = 1.0).
- Confirm margin_report margins equal capability / target - 1.0 with
  input order preserved and that a capability sum below the system
  rate leaves headroom while a sum above it flags a requirement that
  cannot be met.
- Confirm every non-positive rate, weight, MTBF or capability, empty
  input list, item count outside 1..ITEMS_MAX, and length mismatch
  raises ValueError.
- Run the contract test offline: python3
  skills/systems-engineering-safety/arp4761a/reliability-allocation/
  scripts/test_reliability_allocation.py (33 tests, deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/reliability-block-diagram: the
  downstream consumer that evaluates a series chain of blocks from the
  per-item target and capability rates this leaf allocates.
- systems-engineering-safety/arp4761a/preliminary-system-safety-
  assessment: the sibling that apportions failure-condition severity
  probability targets and assigns item assurance levels, the
  per-condition side of the safety requirement flow.
- systems-engineering-safety/arp4761a/failure-rate-estimation:
  demonstrates or estimates item rates from test and service data, the
  source of the predicted capability rates the margin report needs.
- systems-engineering-safety/arp4754a/requirements-allocation: the
  qualitative register that assigns requirement statements to design
  items, complementing the numeric targets this leaf hands to items.

## Pitfalls

- Equal splitting ignores part counts: the simple wiring run and the
  complex dual computer receive the same 60000 h MTBF budget, so use
  complexity_weighted_alloc whenever the item complexities differ.
- Reading the margin sign backwards: a negative margin is slack (the
  predicted capability is better than the budget) and a positive
  margin is a deficit (the predicted rate overruns the budget), the
  inverse of the intuitive reading.
- Treating the closure check as a design endorsement: closure only
  confirms the arithmetic split sums to the system rate; the design
  still fails the requirement if the predicted capability sum exceeds
  the system rate, and then the design or the requirement must change.
- Confusing the MTBF target with a demonstrated MTBF: the targets are
  budgets flowed down for the item development specifications;
  demonstrating rates from test or service data is the
  failure-rate-estimation job.
- Inventing weights on the fly: the apportionment is only as good as
  the design-team complexity weights, which should reflect part count
  or complexity estimates agreed with the design team, not analyst
  guesses.
- Applying the series-sum identity to redundant chains: the identity
  holds for a non-redundant series item chain; evaluating redundant or
  parallel structures from given rates is the
  reliability-block-diagram scope.

## Contract test

Run the deterministic contract test (stdlib unittest, offline, <20 s):

    python3 skills/systems-engineering-safety/arp4761a/
    reliability-allocation/scripts/test_reliability_allocation.py

The test covers the flap actuation worked example (six-item equal and
weighted target rates, closure relative error 1.36e-16 and exact True,
item MTBF targets 60000 h and 33333.3 h, margin report values), the
MTBF rate round trip, the share identity rate_i = system_rate x
w_i / sum(w), the largest-complexity-item largest-budget check, the
closure identity over arbitrary positive weights, the capability-sum
headroom check, ITEMS_MAX and single-item boundaries, and ValueError
rejection of every non-physical input.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/systems-engineering-safety/arp4761a/
    reliability-allocation/scripts/test_reliability_allocation.py

The test covers the 1e-4 per flight hour six-item flow-down contract
(equal and complexity-weighted target rates, MTBF targets, series-sum
closure, capability margins), the MTBF rate round trip, the weighted
share identity, deterministic repeatability, and ValueError rejection
of non-positive rates, weights, MTBF values and capabilities, invalid
item counts, empty lists and length mismatches. All numeric asserts
are tolerance-based (assertAlmostEqual / math.isclose), never exact
equality on computed sums.

## Compliance

- Standards referenced, not reproduced: ARP4761A and ARP4754A are
  proprietary SAE documents (sae.org/standards); the apportionment
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml, with both ids marked reference-only.
- compliance: STANDARDS-REF, gated: false.
