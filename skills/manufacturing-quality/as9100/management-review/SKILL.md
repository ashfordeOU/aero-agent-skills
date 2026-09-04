---
name: management-review
description: "Use when you must plan and score the periodic top-management review process under an AS9100-style quality management system: compute the management review due date from the last review date and the base interval, check the mandatory review input coverage against the presented input set, track the action items from the review decisions, and issue the review verdict from the interval compliance, the input coverage ratio and the overdue action count. Produces the due date, the input coverage ratio with the missing input list, the action tracking summary and the review verdict that gate the top-management review record. Trigger: management-review, top-management, review-interval, review-inputs, action-item-tracking, review-verdict, qms-review."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: as9100
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [management-review, top-management, review-interval, review-inputs, action-item-tracking, review-verdict, qms-review]
  version: 0.1.0
  author: AeroSkills
---

# Management Review (manufacturing-quality/as9100/management-review)

Use when the task is planning and scoring the periodic top-management
review process of an AS9100-style quality management system: computing
the review due date from the last review date and the base interval,
checking the coverage of the mandatory review inputs against the
presented input set, tracking the action items with owners and due
dates from the review decisions, and issuing the review verdict that
gates the top-management review record. This leaf implements the
review process mechanics in pure Python, stdlib only, with no
randomness. It pairs with manufacturing-quality/as9100/
internal-quality-audit, whose audit program results are one of the
input families reviewed here, and with manufacturing-quality/as9100/
corrective-action and risk-management, whose records feed other review
inputs. AS9100 is referenced, not reproduced; the input families below
are paraphrased leaf-owned constants per the organization's QMS
documentation.

## Domain quick reference

- Review cadence: the due date is the last review date plus
  base_interval_months (12.0 declared default) in calendar months with
  the day clamped to the target month end, so 2025-11-30 plus 12
  months is due 2026-11-30, while 2026-01-31 plus 1 month clamps to
  2026-02-28 and 2024-01-31 clamps to 2024-02-29 in the leap year.
- Interval compliance: interval_compliant = today <= due date, meaning
  the review is being planned no later than its due date. It is an
  informational flag only, not a verdict failure: a review that is not
  yet due with no other finding still returns the "compliant" verdict.
- Mandatory input families: MANDATORY_INPUT_FAMILIES =
  (audit-results, customer-feedback, process-performance,
  product-conformity, corrective-action-status, risk-register,
  resource-adequacy, changes, external-provider-performance). These
  are paraphrased leaf-owned constants per the organization's QMS
  documentation, not a reproduced standard clause list.
- Input coverage: coverage_ratio = present required families / 9
  required families. Only required families count, so an extra
  documented input never pushes the ratio above 1.0; missing_inputs is
  the sorted list of required families not presented.
- Coverage threshold: COVERAGE_PASS_THRESHOLD = 0.85, the declared
  leaf methodology; a ratio at or above 0.85 passes the input coverage
  check.
- Action tracking: an action is overdue when its status is "open" and
  its due date is strictly before the passed today; overdue_ratio =
  overdue count / total (0.0 when there are no actions).
- Verdict ladder: coverage below 0.85 and overdue actions together
  give "incomplete-inputs-and-overdue-actions"; coverage below 0.85
  alone gives "incomplete-inputs"; overdue actions alone give
  "overdue-actions"; otherwise the verdict is "compliant".

## Workflow

1. Plan the review date: management_review_due_date(last_review_iso,
   base_interval_months) returns the due date ISO string, with the day
   clamped to the target month end.
2. Score the inputs: review_input_coverage(present_inputs) returns
   {coverage_ratio, present_count, required_count, missing_inputs}
   over the nine required families.
3. Track the decisions: track_actions(actions, today_iso) returns
   {total, open_count, overdue_count, overdue_ratio,
   overdue_actions} from the action list {id, owner, due_date_iso,
   status}.
4. Issue the verdict: review_verdict(interval_compliant,
   coverage_ratio, overdue_count) returns the verdict string from the
   coverage threshold and the overdue action count; the interval flag
   is informational.
5. Chain the whole process: management_review_review(last_review_iso,
   today_iso, present_inputs, actions) returns due_date_iso,
   interval_months, coverage_ratio, missing_inputs, total_actions,
   open_actions, overdue_actions and verdict in one dict.
6. Confirm the deterministic checks with the contract test
   scripts/test_management_review.py.

## Worked example

Last management review 2025-11-30, today 2026-09-04 (planning the
next review). The presented set holds 8 of the 9 required families
(all but resource-adequacy) plus the extra documented input
management-changes, and the decision log has 4 actions, 3 open with 1
overdue (a3, due 2026-08-15). Running the module prints:

- due_date_iso "2026-11-30" (12 calendar months from 2025-11-30; the
  month end clamp keeps the 30th).
- interval_months 12.0; today 2026-09-04 <= 2026-11-30, so
  interval_compliant is True.
- coverage_ratio 0.889 (8/9); missing_inputs ["resource-adequacy"].
- Action tracking: total 4, open 3, overdue 1, overdue_ratio 0.25,
  overdue_actions ["a3"].
- verdict "overdue-actions": coverage 0.889 is at or above the 0.85
  threshold so the coverage check passes, and the 1 overdue action
  drives the verdict.
- Full chain dict keys: {due_date_iso, interval_months,
  coverage_ratio, missing_inputs, total_actions, open_actions,
  overdue_actions, verdict}.

## Verification

- management_review_due_date clamps month ends: 2026-01-31 plus 1
  month gives 2026-02-28, 2024-01-31 gives 2024-02-29, and 2026-08-31
  plus 1 month gives 2026-09-30.
- Malformed dates, intervals at or below 0, empty mandatory input
  sets, and actions with an unknown status or an empty owner all raise
  ValueError.
- Coverage: all required families present gives ratio 1.0 with no
  missing inputs; none present gives ratio 0.0 with all 9 missing
  sorted; extras and duplicates never raise the ratio above the true
  required count.
- Overdue detection is relative to the passed today: an open action
  due after (or on) today is not overdue, and a closed action is never
  overdue.
- Verdict truth table: (True, 8/9, 1) -> "overdue-actions"; (True,
  0.8, 0) -> "incomplete-inputs"; (True, 0.7, 2) ->
  "incomplete-inputs-and-overdue-actions"; (True, 0.9, 0) ->
  "compliant"; (False, 0.9, 0) -> "compliant" because the interval
  flag is informational.
- Determinism: no RNG anywhere, run-to-run identical output.
- Run the contract test offline: python3
  scripts/test_management_review.py (35 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/internal-quality-audit: runs the
  periodic audit program whose results feed the audit-results input
  family of the management review.
- manufacturing-quality/as9100/quality: the clause mapping companion
  for audit evidence planning in the same pack.
- manufacturing-quality/as9100/corrective-action: owns the corrective
  action records whose status is one of the review input families.
- manufacturing-quality/as9100/risk-management: owns the risk
  register reviewed as an input family here.
- manufacturing-quality/as9100/supplier-control: external provider
  performance monitoring that feeds the review inputs.

## Pitfalls

- Reading the interval flag as a verdict input: interval_compliant is
  informational only, so (False, 0.9, 0) still returns "compliant" —
  a review planned late but with full inputs and no overdue actions is
  not failed on schedule alone.
- Reporting the coverage ratio against everything presented: only the
  nine required families count, so extra documented inputs and
  duplicates never push the ratio above the true required count, and
  missing_inputs names only required families.
- Applying the verdict ladder out of order: coverage below 0.85 with
  overdue actions returns "incomplete-inputs-and-overdue-actions"
  (not just "incomplete-inputs"), while overdue actions alone drive
  "overdue-actions" even when coverage passes — as in the worked
  example at 8/9 with one overdue action.
- Judging overdue against the wrong reference date: overdue is
  relative to the passed today, an open action due on or after today
  is not overdue, and a closed action is never overdue.
- Computing due dates without the month-end clamp: 2026-01-31 plus 1
  month is 2026-02-28 (2024-02-29 in the leap year) and 2026-08-31
  plus 1 month is 2026-09-30 — naive month arithmetic lands in the
  wrong month.
- Treating the nine input families as reproduced standard text: they
  are paraphrased leaf-owned constants per the organization's QMS
  documentation, and non-physical inputs (malformed dates, intervals
  at or below 0, empty mandatory sets, actions with unknown status or
  empty owner) raise ValueError rather than scoring.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_management_review.py

The test covers due date planning with month end clamping including
the leap year, the coverage ratio with extras and duplicates excluded,
the sorted missing input list, overdue detection relative to the
passed today, the full verdict truth table, the worked example outputs
inside the spec magnitude bounds, the exact convenience dict keys,
ValueError rejection of every non-physical input, and run-to-run
determinism.

## Compliance

- Standards referenced, not reproduced: AS9100 is a commercial SAE
  standard; the mandatory input families above are paraphrased
  leaf-owned constants per the organization's QMS documentation,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
