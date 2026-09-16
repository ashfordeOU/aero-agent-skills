---
name: q6013-class-3-lot-acceptance
description: "Use when a commercial batch needs an accept-or-hold verdict. Determine which lot acceptance route a batch of commercial EEE parts sits on at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.3.5, and whether its evidence closes that route: escalate an uncontrolled supply channel, a dead quality system certificate or a single-point-failure function to a full purchaser campaign, escalate an open process change notice or a batch past the shelf-age limit to a reduced one, let the strictest trigger govern while still reporting the lighter ones, credit manufacturer data only where it names a document, an issue and the build month it covers, and judge each subgroup on the accept number and the percent defective together. Trigger: ecss, q-st-60-13c-clause-6-3-5, class-three-lot-acceptance-route, lat-route-escalation-trigger, commercial-batch-shelf-age-limit, manufacturer-conformance-data-credit, lat-subgroup-accept-number-and-rate."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-lot-acceptance, class-three-lot-acceptance-route, lat-route-escalation-trigger, commercial-batch-shelf-age-limit, manufacturer-conformance-data-credit, lat-subgroup-accept-number-and-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Lot Acceptance (space-systems/ecss/q6013-class-3-lot-acceptance)

Use when the task is the clause 6.3.5 lot acceptance question of
ECSS-Q-ST-60-13C at the lowest assurance class: a batch of a commercial part
has arrived, and the question is not first whether it passed its tests but
which tests it was ever owed.

## Domain quick reference

- At this class the default is not a purchaser test campaign. A batch bought
  through a controlled channel from a manufacturer running a live quality
  system is accepted on that manufacturer's own routine conformance data, and
  that is the whole point of buying commercial: the testing already happened,
  once, for everybody.
- The route is escalated by conditions, not chosen by preference. An
  uncontrolled channel, a manufacturer with no live certificate and a part
  sitting in a single-point-failure function each escalate to a full purchaser
  campaign. An open process change notice against the build, and a batch that
  has sat past the shelf-age limit, each escalate to a reduced one.
- The strictest triggered route governs, and the lighter triggers still get
  reported. A batch held for its channel may also be carrying an open change
  notice, and closing only the reason that was printed sends it straight back.
- Manufacturer data counts only where it names a document, that document's
  issue, and the build month it covers. A reference with no issue points at
  whatever the report says today, and a report covering another month
  describes another batch of parts entirely.
- Where an escalation puts a subgroup on the list, the manufacturer's data
  does not fill it. The escalation exists precisely because that data is no
  longer being trusted on its own, so crediting it back is circular.
- A performed subgroup carries two limits on one sample: the accept number, an
  integer count of failures the subgroup tolerates, and the allowable percent
  defective, a rate applied to the sample size. A small sample can meet its
  accept number while sitting far above the rate.

## Workflow

1. Validate the batch record: a named lot reference, a parsable build month
   and assessment month, and real booleans rather than absent declarations.
2. Age the batch in whole months and refuse an assessment that precedes the
   build rather than reading it as an age of zero.
3. Collect every route trigger the batch raises, each with the route it forces
   and the reason it forces it, ordered lightest route first.
4. Take the strictest triggered route as the governing one and keep the rest
   of the triggers in the record.
5. Read the manufacturer's conformance data and credit it only against a
   document, an issue and a covered build month that matches this batch.
6. On a data-only route, accept the batch on that credit alone and name what
   is missing where it fails.
7. On a purchaser route, list the subgroups the route owes, name every one the
   campaign left uncovered, and judge the rest on the accept number and the
   percent defective together, absorbing representation error at the rate
   boundary with a named tolerance rather than by widening the rate.
8. Accept the batch only when nothing is uncovered and nothing rejects;
   otherwise hold it and report every failing subgroup.

## Pitfalls

- Running a full campaign on every commercial batch. The lowest class exists
  to buy parts the market already tested, and testing everything at purchaser
  expense abandons the only advantage the class offers.
- Accepting a broker batch on the manufacturer's report. The report may be
  perfectly real and still describe material that never went through the hands
  this batch went through.
- Closing only the governing trigger. The strictest route governs the tests,
  but the lighter triggers are still findings against the batch.
- Crediting a reference with no issue. That points at whatever the document
  says today rather than at the evidence somebody actually reviewed.
- Taking the accept number as the whole criterion. The allowable percent
  defective is a second, independent limit on the same sample, and a twenty
  piece sample clears counts it has no business clearing.
- Reading an age exactly on the shelf-age limit as past it. The limit is a
  bound the batch may sit on; the escalation starts the month after.

## Behavior contract (gate 3)

The month parsing, whole-month age arithmetic, each route escalation trigger
and the strictest-route rule, the manufacturer data credit, the per-subgroup
accept-number and percent-defective comparisons, the uncovered-subgroup list
and the accept-or-hold disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_lot_acceptance.py against
scripts/q6013_class_3_lot_acceptance_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_lot_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
