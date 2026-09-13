---
name: e20-emc-verification-plan-and-report
description: "Use when prepare and check the paired electromagnetic compatibility verification plan and verification report a supplier owes under ECSS-E-ST-20C clause 6.4.1: confirm each document declares the content its own mandatory section set demands, trace every planned verification activity into a report entry and reject an orphan entry no plan activity foresaw, hold the plan issue date far enough ahead of the first activity and the report issue date after the last one and inside the review data-package date, close a non-compliant activity through a named repeat run or an accepted deviation record, and sum the declared requirement-set shares of the closed activities against the coverage the programme demands. Trigger: ecss, e-st-20-electrical-scope, emc-verification-plan-and-report, verification-plan-report-pairing, emc-verification-activity-traceability, verification-report-issue-lead, non-compliance-deviation-closure, requirement-set-coverage-share."
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
  tags: [ecss, e-st-20-electrical-scope, e20-emc-verification-plan-and-report, emc-verification-plan-and-report, verification-plan-report-pairing, emc-verification-activity-traceability, verification-report-issue-lead, requirement-set-coverage-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- EMC Verification Plan and Report (space-systems/ecss/e20-emc-verification-plan-and-report)

Use when the task is the clause 6.4.1 document pair of ECSS-E-ST-20C --
the electromagnetic compatibility verification plan the supplier issues
before the campaign and the verification report the supplier issues
after it -- and the question is whether the two documents, taken
together, actually close the compatibility verification they promise.

## Domain quick reference

- The pair is two documents with two different jobs and two different
  mandatory content sets. The plan is forward-looking: it owes the
  verification approach, the matrix that maps each compatibility
  requirement onto an activity, the schedule, the facility and setup
  definition, the criteria a result is judged against, and the route a
  deviation takes. The report is backward-looking: it owes the as-run
  configuration, the measured results, the deviation record, the
  disposition and conclusion, and the index of the evidence. Checking
  the report against the plan's section set, or the reverse, passes a
  document that is missing everything it actually owes.
- Traceability runs in both directions and both directions are
  findings. A planned activity with no entry in the report is
  verification that was promised and never evidenced. An entry in the
  report that no planned activity foresaw is evidence with no
  requirement behind it: it was either run against an activity that
  never entered the plan, or it names an activity identifier that is
  wrong. Neither is a silent skip.
- An activity can carry several entries, because a repeat run after a
  non-compliant result is itself an entry. The activity is settled by
  its latest entry, with the identifier as the tie-break so the result
  does not depend on record order. A non-compliant latest entry with
  no later repeat and no accepted deviation leaves the activity open.
- Acceptance with a deviation is a real disposition, but only when the
  entry names the deviation record that carries the acceptance. An
  entry that declares acceptance-with-deviation and names nothing is
  an unsupported acceptance, not a pass. A repeat run that names a
  predecessor entry absent from the report has lost its own history.
- The two issue dates bracket the campaign. The plan is issued far
  enough ahead of the first activity that it can still steer the
  setup -- the lead is a project number, and a plan issued after the
  first activity ran is a plan written to match the results. The
  report is issued after the last activity and no later than the date
  the review data package closes.
- Each planned activity carries a declared share of the compatibility
  requirement set. The coverage the campaign reaches is the sum of the
  shares of the closed activities, compared against the coverage the
  programme demands -- which is how a campaign that closed every
  activity it planned can still be short, if the plan never covered
  the whole requirement set.

## Workflow

1. Normalise the plan: reject an activity with an empty identifier, an
   activity naming no requirement, an unknown verification method, a
   share outside nought to a hundred percent, a malformed planned date
   and a repeated activity identifier. An empty plan is an error, not
   an empty result.
2. Normalise the report the same way: reject an empty entry
   identifier, an entry naming no activity, an unknown disposition, a
   malformed execution date, an empty deviation reference and an entry
   that declares itself its own predecessor.
3. Check each document against its own mandatory section set, and
   report the gaps in the order the set fixes so two runs read the
   same.
4. Trace the pair in both directions: list the planned activities with
   no entry, and list the entries whose activity is not in the plan.
5. Settle each activity on its latest entry and collect the closure
   findings: an open non-compliance, an acceptance-with-deviation that
   names no deviation record, and a repeat run whose predecessor is
   not an entry in the report.
6. Place the two issue dates: plan issue against the first execution
   and the demanded lead, report issue against the last execution and
   against the review data-package date.
7. Sum the declared shares of the closed activities and compare that
   against the demanded coverage, absorbing the representation error a
   sum of decimal percentages carries.
8. The pair is compliant only when every list is empty and the
   coverage is met.

## Pitfalls

- Checking one section set against both documents. The plan and the
  report owe disjoint content, and a report graded against the plan's
  set sails through with no as-run configuration and no evidence
  index.
- Tracing the plan into the report and stopping there. The orphan
  direction is where a mislabelled entry and an unplanned activity
  both surface, and it costs nothing to look.
- Settling an activity on the first entry, or on whichever entry the
  loop saw last. The disposition belongs to the latest execution; an
  unordered scan turns a closed non-compliance back into an open one,
  or worse, hides a later failure behind an earlier pass.
- Reading acceptance-with-deviation as a pass without opening the
  deviation reference. An acceptance nobody recorded is not an
  acceptance, and it is exactly the case that survives to the review.
- Comparing the accumulated coverage against the demand with a bare
  greater-or-equal test. The accumulated value is a sum of decimal
  percentages and a case that covers the whole set in engineering
  terms can land a few units in the last place below the demand:
  33.4 plus 33.3 plus 33.3 sums to 99.99999999999999, not 100. Absorb
  that representation error in the comparison; never lower the
  demanded coverage to make the sum pass.
- Treating a report issued inside the data-package window as
  sufficient without checking it is also after the last activity. A
  report that predates its own last measurement was written from
  expectations.

## Behavior contract (gate 3)

The plan and report normalisation, mandatory-section checks,
two-direction traceability, latest-entry settlement, deviation and
repeat-run closure logic, issue-date placement, share accumulation,
tolerance-absorbing coverage comparison and the aggregate review are
exercised by the gate 3 contract test:
scripts/test_e20_emc_verification_plan_and_report.py against
scripts/e20_emc_verification_plan_and_report_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_emc_verification_plan_and_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
