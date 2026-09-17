---
name: q6013-legacy-class-2-acceptance-table
description: "Determine whether a screened legacy lot passes the ECSS-Q-ST-60-13C Table 8-14 acceptance list. Use when an intermediate-assurance lot of legacy commercial active parts has completed lot acceptance and the campaign has to become an accept-or-hold verdict: size every group from the banded sampling plan keyed on the lot, judge each group accept-on-zero because acceptance consumes what it tests, confirm the devices sampled came from the lot being accepted, subtract the consumed devices from the population left to deliver, and admit a single resubmission only once the failure mechanism is found and screened out. Trigger: ecss, q-st-60-13c-table-8-14, legacy-class-2-lot-acceptance-list, acceptance-banded-sampling-plan, acceptance-group-accept-on-zero, acceptance-sample-provenance, acceptance-device-consumption-balance, legacy-lot-resubmission-limit."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-2-acceptance-table, q-st-60-13c-table-8-14, legacy-class-2-lot-acceptance-list, acceptance-banded-sampling-plan, acceptance-sample-provenance, acceptance-device-consumption-balance, legacy-lot-resubmission-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Legacy Class 2 Acceptance Table (space-systems/ecss/q6013-legacy-class-2-acceptance-table)

Use when the task is the legacy lot acceptance test list of ECSS-Q-ST-60-13C
Table 8-14 — taking the groups, the sampling plan and the acceptance limits
the table sets for an active commercial part at the intermediate assurance
class and turning an executed acceptance campaign on one screened lot into an
accept-or-hold verdict.

## Domain quick reference

- The sample is sized from the lot, not chosen. A banded plan keyed on the lot
  size fixes the devices per group, so a small lot accepted on a sample sized
  for a large one has been accepted on a confidence it never had.
- A lot can be too small to yield its own plan. That is a reportable state,
  not a rounding problem: the answer is a different route to acceptance, never
  a quietly reduced sample.
- Every acceptance group consumes what it tests. There is no rate to tolerate
  on devices taken apart, so each group is accept-on-zero and an accept number
  above zero is a specification error rather than a looser limit.
- The sample has to come from the lot being accepted. Devices pulled from a
  neighbouring build test that build; the date codes behind the sample are
  checked before its result is allowed to stand for the lot.
- Acceptance is paid for in hardware. The samples never come back, so the
  population left after the campaign is compared with the quantity to be
  delivered, and a lot that passes but can no longer fill the order is
  reported rather than discovered at delivery.
- A failed lot comes back once. Resubmission at this assurance class is a
  single, conditioned route: the failure mechanism has to be identified and
  screened out of the lot first, and there is no second attempt after it.

## Workflow

1. Read the per-group sample out of the banded plan for the declared lot size
   and record whether the lot is even large enough to yield it.
2. Validate each group: an unknown group name, a sample larger than the lot,
   more failures than devices sampled, a repeated group or an accept number
   above zero is an input error, not a degenerate case to clamp.
3. Judge each group accept-on-zero and carry any sample shortfall against the
   planned devices rather than accepting the reduced run.
4. Check the date codes behind the sample against the lot's own code and name
   every foreign code rather than reporting a bare provenance failure.
5. Sum the devices the campaign consumed, subtract them from the screened
   population, and compare what is left with the quantity to be delivered.
6. Apply the resubmission rule to the attempt number, requiring an identified
   mechanism and a re-screen for the one admissible resubmission, then hold
   the lot when any single check rejects rather than averaging the groups
   into one rate a clean group can carry.

## Pitfalls

- Carrying one sample size across every lot. The plan is banded for a reason,
  and a fixed sample makes a small lot look as well tested as a large one.
- Reducing the sample so a small lot can be accepted by test. The reduction
  is the finding; shrinking the plan to fit the lot removes the confidence
  the acceptance was supposed to buy.
- Tolerating a failure on a group that destroys its devices. A rate on a
  sample of five taken apart is not a rate, and honouring it doubles the
  acceptable defect population without anyone deciding to.
- Filling a short sample from a neighbouring date code. The campaign then
  accepts a lot partly on the evidence of a different build, and the two are
  indistinguishable in the record afterwards.
- Forgetting that acceptance consumes hardware, then discovering at delivery
  that the accepted lot is short. The remaining population is part of the
  verdict, not an administrative detail after it.
- Resubmitting a failed lot on the strength of a re-screen alone. Without the
  mechanism identified, the re-screen is removing an unknown, and the second
  attempt is the same test on the same uncertainty.

## Behavior contract (gate 3)

The banded sampling plan and the lot too small to yield it, group validation
under the accept-on-zero rule, the sample shortfall, sample provenance
against the lot date code, the consumption balance against the deliverable
quantity, the single conditioned resubmission and the overall accept-or-hold
disposition are exercised by the gate 3 contract test:
scripts/test_q6013_legacy_class_2_acceptance_table.py against
scripts/q6013_legacy_class_2_acceptance_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_2_acceptance_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
