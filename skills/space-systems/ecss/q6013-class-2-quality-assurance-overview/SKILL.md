---
name: q6013-class-2-quality-assurance-overview
description: "Assess the quality assurance duties a programme owes for commercial EEE parts at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.5.1: dispose every catalogue duty as established, waived or short of an owner, a procedure or an evidence record, refuse a waiver against a duty the class makes mandatory, accept a discretionary waiver only against a recorded rationale and approval, carry a plain coverage beside an evidenced coverage, read the quality plan against its revalidation interval, and price a quality function reporting inside a function it grades. Use when a declared assurance arrangement must become one verdict before parts are bought. Trigger: ecss, q-st-60-13c-clause-5-5-1, class-two-commercial-eee-quality-assurance, mandatory-quality-duty-waiver-refusal, evidenced-duty-coverage-floor, quality-plan-revalidation-interval, quality-function-escalation-route, commercial-eee-assurance-duty-catalogue."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-quality-assurance-overview, class-two-commercial-eee-quality-assurance, mandatory-quality-duty-waiver-refusal, evidenced-duty-coverage-floor, quality-plan-revalidation-interval, quality-function-escalation-route, commercial-eee-assurance-duty-catalogue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Quality Assurance Overview (space-systems/ecss/q6013-class-2-quality-assurance-overview)

Use when the task is the clause 5.5.1 framing question of ECSS-Q-ST-60-13C at
the intermediate assurance class: before a single commercial part is bought,
which quality assurance duties does the programme owe, and can each of them
be shown to be held by somebody against a procedure and a record.

## Domain quick reference

- The intermediate class buys its relief in a specific currency. It lets a
  programme stand down a discretionary duty, and it charges a recorded
  rationale and a named approval for doing so. A duty dropped without that
  record is not a relaxed duty; it is an unassigned one wearing the same
  word.
- Some duties do not move at any price. Procurement document review, incoming
  inspection, nonconformance processing, traceability, alert dissemination
  and records retention are what the class is, so a waiver against one of
  them is refused before its rationale is read.
- Two coverage figures are carried rather than one. The plain coverage counts
  an admissibly waived duty as disposed; the evidenced coverage counts only
  the duties carrying a real record. A programme running on waivers reaches
  full plain coverage and thin evidence, and the difference is visible in
  advance rather than at the audit.
- The first missing element is the one reported. A duty with no owner is not
  also graded on the procedure it does not have, because chasing three
  findings where there is one gap sends three actions to the same empty box.
- A quality plan that exists is not a quality plan that is current. The
  revalidation interval runs from issue, and a plan written for the previous
  build standard describes a programme that is no longer the one buying
  parts.
- Independence here is structural, not personal. A quality function reporting
  inside design, production, procurement or integration grades its own line
  management's output, and the intermediate class tolerates that only where
  an escalation route exists for a refusal to travel along.
- A duty declared but never exercised leaves no evidence reference, which is
  exactly why the evidence field is separate from the procedure field. One
  says the programme knows how; the other says it did.

## Workflow

1. Validate the assurance policy first: both coverage floors inside the unit
   interval, the evidenced floor not above the plain floor, a positive plan
   revalidation interval and a boolean escalation requirement. An unknown
   policy key is refused rather than ignored.
2. Validate every declared duty record: a duty name drawn from the
   catalogue, no duty declared twice, and reference fields that are strings
   where present. A blank reference counts as absent, not as present.
3. Dispose each duty in the catalogue, including the ones the programme never
   declared, so the report length always matches the catalogue length and a
   silent omission cannot read as coverage.
4. Test every waiver before it is credited. A mandatory duty refuses the
   waiver outright; a discretionary duty accepts it only with both a recorded
   rationale and a named approval, and a refused waiver leaves the duty
   unowned.
5. Take the plain coverage and the evidenced coverage over the whole
   catalogue and compare both with their floors under a named tolerance, so a
   count landing exactly on a floor is not read as short.
6. Read the quality plan: its presence first, then its age against the
   revalidation interval, with an age equal to the interval still inside it.
7. Read the reporting line against the functions the quality role grades and
   require a declared escalation route where it is embedded and the policy
   asks for one.
8. Close on the first blocking condition in order — no plan, a mandatory duty
   waived, a mandatory duty unassigned, coverage short, no escalation route,
   plan revalidation overdue — or on the intermediate class being met, and
   report both coverages and every gap beside the verdict.

## Pitfalls

- Reading a waiver as a decision rather than a record. The class accepts the
  decision and asks for the paper; without the rationale and the approval the
  duty is simply not held.
- Waiving an incoming inspection because the parts are catalogue parts. The
  commercial origin is the reason the duty exists, so the argument for
  dropping it is the argument for keeping it.
- Quoting the plain coverage alone. A programme that waived two duties and
  one that performs them reach the same plain figure and are not the same
  programme, which is what the evidenced figure exists to show.
- Accepting a procedure reference as evidence. The procedure says the
  programme knows how to do the duty; only the record says it did, and the
  two fields stay separate for that reason.
- Treating an embedded quality function as acceptable because the people are
  experienced. The test is structural: with no escalation route a refusal
  cannot survive its own reporting line, whatever the staffing.
- Letting an undeclared duty vanish from the report. A catalogue duty nobody
  mentioned is the most likely gap in the arrangement, so it is reported
  unowned rather than dropped from the denominator.

## Behavior contract (gate 3)

The policy validation, duty record validation, duty disposition, waiver
admissibility, plain and evidenced coverage against their floors, the quality
plan presence and revalidation reading, the independence and escalation route
reading and the closing verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_quality_assurance_overview.py against
scripts/q6013_class_2_quality_assurance_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_quality_assurance_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
