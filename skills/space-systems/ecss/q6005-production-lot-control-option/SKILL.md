---
name: q6005-production-lot-control-option
description: "Plan the per-batch acceptance scheme an approved hybrid line operates under ECSS-Q-ST-60-05C clause 12.2.1: validate the production lot and its acceptance groups, allocate units from the lot to each group without letting samples share units, separate the units destroyed from the units returned to stock, disposition each group against its own acceptance number and then the lot against its groups, and track resubmissions and consecutive rejected lots to the point where the option itself is suspended. Use when running or auditing hybrid lot-by-lot acceptance. Trigger: ecss, q-st-60-05c, hybrid-production-lot-control, hybrid-per-lot-acceptance-groups, hybrid-destructive-sample-accounting, hybrid-lot-resubmission-limit, hybrid-consecutive-lot-rejection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-production-lot-control-option, hybrid-production-lot-control, hybrid-per-lot-acceptance-groups, hybrid-destructive-sample-accounting, hybrid-lot-resubmission-limit, hybrid-consecutive-lot-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Production Lot Control Option (space-systems/ecss/q6005-production-lot-control-option)

Use when the task is operating or auditing the acceptance option under
ECSS-Q-ST-60-05C clause 12.2.1 in which every production batch earns its
own acceptance by feeding samples to a set of test groups — how many
units each group takes, what survives, what the lot's disposition is,
and what happens to the line when lots keep failing.

## Domain quick reference

- Under this option the lot is the unit of evidence. Nothing carries
  over between batches: a lot accepted last month says nothing about
  this one, which is exactly the property a project buys when it
  chooses per-lot control over line monitoring.
- Acceptance groups do not share units. Electrical, environmental and
  destructive analysis each draw their own sample, so the commitment
  against the lot is the sum, not the largest group. Sizing the build
  against the biggest group is the most common way a lot arrives too
  small to accept.
- Committed is not the same as destroyed. Non-destructive samples come
  back to stock and still ship; only the destructive groups come off the
  deliverable quantity. Treating the whole commitment as lost
  overbuilds, and treating none of it as lost ships short.
- Every group has to report. A group with no result is not a pass by
  default and not a rounding error: the property it was drawn to
  demonstrate is unverified, and the lot's disposition is refusal until
  it reports.
- One failing group refuses the lot. The groups are not scored and
  averaged — they are separate conditions, and a lot that passed
  electrical acceptance while failing environmental has still not shown
  what it needed to show.
- Rejection has two scopes. A rejected lot may be reworked and
  resubmitted a limited number of times; a run of consecutive rejected
  lots is a statement about the line rather than the batch, and
  suspends the entitlement to operate this option at all.

## Workflow

1. Validate the lot as a positive count of built units, and the group
   set for unique names, positive samples and acceptance numbers below
   their own sample sizes.
2. Sum the group samples into the commitment against the lot, and refuse
   outright a lot that cannot cover it — under this option a lot feeds
   its own acceptance tests or it has no plan.
3. Split the commitment into destroyed and returned-to-stock, and carry
   the deliverable quantity after acceptance from the destroyed count
   alone.
4. Compare the deliverable after acceptance with the order, and report
   any shortfall in units.
5. Disposition each group against its own acceptance number, refusing a
   result that reports more failures than units drawn or names a group
   outside the plan.
6. Disposition the lot: accept only when every group reported and every
   group accepted, and name the failing and the silent groups
   separately.
7. Read the lot history for consecutive rejects, apply the resubmission
   limit to this lot, and report the line's entitlement alongside the
   lot's disposition.

## Pitfalls

- Sizing the production lot to the order. The lot feeds its own
  acceptance tests, and the destructive groups are consumed, so a lot
  built to the order ships short by exactly the destructive sample.
- Reusing one sample across two groups to save units. The groups test
  different things on units that have been through different histories;
  a unit that has been through environmental acceptance is no longer a
  fresh sample for anything else.
- Reading a missing group result as an accept. The report distinguishes
  failing groups from silent ones precisely because they need different
  responses: one is a nonconformance, the other is an incomplete test
  campaign.
- Averaging group outcomes into a lot score. They are independent
  conditions and the lot takes the worst of them, not the mean.
- Treating consecutive rejections as a run of unlucky batches. Two in a
  row is evidence about the line, and the correct response is the
  review that suspension triggers, not a third submission.
- Resubmitting a reworked lot without counting prior submissions. The
  limit exists so a batch cannot be screened repeatedly until a sample
  finally passes.

## Behavior contract (gate 3)

The lot and group validation, the per-group allocation, the destructive
accounting, the per-group and per-lot disposition, the resubmission
limit and the consecutive-reject suspension are exercised by the gate 3
contract test: scripts/test_q6005_production_lot_control_option.py
against scripts/q6005_production_lot_control_option_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_production_lot_control_option.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
