---
name: q40-verification-critical-functions
description: "Verify a safety-critical function against ECSS-Q-ST-40C: read off the activities its criticality category owes — validation, qualification, failure testing, design and operational characteristic verification, safety verification testing — then discharge each one only on a passed record with an evidence reference, refuse a waiver at the top category, and grade failure testing by the fraction of declared failure modes it actually reaches rather than by whether a failure test happened. Use when a safety-critical function is being closed out. Trigger: ecss, q-st-40c, safety-critical-function-verification, safety-verification-testing, safety-failure-mode-test-coverage, safety-activity-waiver, safety-qualification-evidence."
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
  tags: [ecss, q-st-40c-safety, q-st-40c, q40-verification-critical-functions, safety-critical-function-verification, safety-verification-testing, safety-failure-mode-test-coverage, safety-activity-waiver, safety-qualification-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety — Verification of Safety-Critical Functions (space-systems/ecss/q40-verification-critical-functions)

Use when the task is the safety-critical-function clause of ECSS-Q-ST-40C: a
function has been identified as safety critical and somebody has to say whether
the verification actually done discharges what that criticality owes.

## Domain quick reference

- The criticality category fixes the owed activity set. It is a lookup, not a
  negotiation, and the set only grows as criticality rises — a catastrophic
  function owes every activity, a major one owes the design-facing three.
- Validation and qualification answer different questions. Validation asks
  whether the function is the right one for the safety requirement;
  qualification asks whether this implementation withstands its environment.
  A programme that does one twice has not done the other.
- Failure testing is graded by coverage of the declared failure modes, not by
  its existence. One failure test against one mode on a function with five
  modes is a data point, and reporting it as "failure testing done" is how
  four uncovered modes reach flight.
- A failed activity record is not a gap to be filled later. It is a result,
  and it stops the function until it is superseded by a passed one.
- A waiver is a narrow escape hatch. It needs its own reference, and it is not
  available at the top category at all: nothing is waivable when the
  consequence is catastrophic.
- Operational characteristic verification is the one most often skipped,
  because it needs the operational context to exist. That is a schedule
  problem, not a reason to drop the activity from the owed set.
- Activities the category does not owe are still evidence. Report them as
  supplementary rather than dropping them, or the next reviewer redoes them.

## Workflow

1. Validate the function record: identity, criticality, declared failure modes,
   and one activity entry per recorded activity with a known name and status.
2. Reject a record whose failure test covers a mode the function never
   declared; the coverage denominator has to mean something.
3. Look up the owed activity set for the criticality category.
4. For each owed activity find its record: absent, failed, not-run, waived
   without a reference, waived at a category that allows no waiver, or passed
   without an evidence reference are each an outstanding item with its reason.
5. Compute failure-mode coverage from passed failure tests only, and compare
   it against the fraction the category demands with a tolerance, so a value
   that lands on the bound counts as meeting it.
6. List the recorded activities the category does not owe as supplementary.
7. Close the function: not-verified when an owed activity was not discharged
   or coverage falls short, verified-with-open-actions when only an evidence
   reference is missing, verified otherwise.
8. Roll a set of functions up, carrying the unverified ones to the top.

## Pitfalls

- Counting a failure test rather than measuring what it covered. The question
  is which modes were exercised, and the answer is usually fewer than assumed.
- Letting qualification stand in for validation. Environmental survival says
  nothing about whether the function was the right response to the hazard.
- Waiving an activity on a catastrophic function. There is no category of
  evidence that a waiver supplies there, which is why the route is closed.
- Accepting a passed record with no evidence reference. It is an assertion
  until something is cited, and the close-out will come back for it.
- Comparing a coverage fraction with a bare equality. The ratio is a division
  and a value that should sit on the bound can land a bit under it.
- Dropping supplementary activities from the report because they were not
  owed. The next reviewer then commissions them again.
- Reporting the first outstanding activity only, so the function is resubmitted
  once per defect.

## Behavior contract (gate 3)

The function record validation, criticality-to-activity table, discharge rules
for failed, not-run, waived and unevidenced records, the waiver ceiling,
failure-mode coverage with its tolerance, supplementary activities and the
verified / verified-with-open-actions / not-verified disposition plus the set
rollup are exercised by the gate 3 contract test:
scripts/test_q40_verification_critical_functions.py against
scripts/q40_verification_critical_functions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q40_verification_critical_functions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
