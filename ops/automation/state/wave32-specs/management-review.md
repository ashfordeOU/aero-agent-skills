# Wave-32 leaf spec: management-review (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/management-review/
- Pack: as9100. Siblings: quality (clause-to-evidence audit mapping),
  internal-quality-audit (wave-31, audit program mechanics),
  corrective-action, document-control, nonconformance-control,
  risk-management, supplier-control.
- Standards id: as9100 (reference-only; gated - paraphrase only, never
  verbatim clause text). Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Plan and score the periodic top-management review process of an
AS9100-style quality management system: compute the management review
due date from the last review date and the base interval, check the
coverage of the mandatory review inputs against the presented input
set, track the action items with owners and due dates from the review
decisions, and issue the review verdict from the interval compliance,
the input coverage ratio and the overdue action count. Produces the due
date, the input coverage ratio with the missing input list, the action
tracking summary and the review verdict that gate the top-management
review record.

Does NOT do: internal audit program mechanics (internal-quality-audit
owns audit scheduling, auditor independence, sampling, finding
classification - the clause 9.2 audit process); corrective action
records (corrective-action owns the 8D/CAPA response record);
mapping audit focus areas to clauses (quality owns clause-to-evidence
mapping for the aerospace additions); clause-text reproduction
(AS9100 is gated; input/output families are leaf-owned paraphrased
constants per the organization's QMS documentation).

## Model (implement exactly)

Constants:
- BASE_INTERVAL_MONTHS = 12.0 (declared default cadence).
- COVERAGE_PASS_THRESHOLD = 0.85 (coverage ratio at or above which
  the input coverage check passes, declared leaf methodology).
- MANDATORY_INPUT_FAMILIES = ("audit-results", "customer-feedback",
  "process-performance", "product-conformity", "corrective-action-
  status", "risk-register", "resource-adequacy", "changes",
  "external-provider-performance") - leaf-owned paraphrased families
  (per the organization's QMS documentation; NOT a verbatim AS9100
  clause list).

Functions (pure stdlib datetime/arithmetic, no randomness):

- management_review_due_date(last_review_iso, base_interval_months =
  BASE_INTERVAL_MONTHS) -> ISO due date string: last review date plus
  the interval in calendar months with the day clamped to the target
  month end (same clamp rule as internal-quality-audit: 2025-11-30 +
  12 months -> 2026-11-30; 2026-01-31 + 1 month -> 2026-02-28).
  ValueError on malformed dates or interval <= 0.
- review_input_coverage(present_inputs, mandatory_inputs =
  MANDATORY_INPUT_FAMILIES) -> dict {coverage_ratio, present_count,
  required_count, missing_inputs (sorted list)}.  present_inputs and
  mandatory_inputs are collections of family names; coverage_ratio =
  present_count / required_count (0.0 when mandatory_inputs empty).
  ValueError if required_count == 0.
- track_actions(actions) -> dict {total, open_count, overdue_count,
  overdue_ratio, overdue_actions (sorted list of action ids)}.
  actions: list of dicts {id, owner, due_date_iso, status} where
  status in {"open", "closed"}; overdue when status == "open" and
  due_date_iso < today_iso (today passed as an argument for
  determinism).  ValueError on malformed dates, unknown status, empty
  owner.
- review_verdict(interval_compliant, coverage_ratio, overdue_count,
  coverage_threshold = COVERAGE_PASS_THRESHOLD) -> string: one of
  "compliant", "incomplete-inputs" (coverage < threshold), "overdue-
  actions" (overdue_count > 0), "incomplete-inputs-and-overdue-actions"
  (both).  Order of checks: when both conditions hold return the
  combined string; else return the single applicable condition;
  "compliant" only when interval_compliant True and neither condition
  holds.  NOTE: interval_compliant False alone (review not yet due, no
  other finding) still returns "compliant" - the interval flag is an
  informational input (whether the review is due now), not a failure;
  document this in the SKILL body.
- management_review_review(last_review_iso, today_iso,
  present_inputs, actions, base_interval_months = BASE_INTERVAL_MONTHS)
  -> dict {due_date_iso, interval_months, coverage_ratio,
  missing_inputs, total_actions, open_actions, overdue_actions,
  verdict}.  interval_compliant computed as today_iso <= due_date_iso
  (the review is being planned no later than its due date).  ValueErrors
  propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Last management review 2025-11-30, today 2026-09-04 (planning the next
review).  Present inputs: 10 of the 9 mandatory families plus an extra
documented input ("resource-adequacy" absent): {audit-results,
customer-feedback, process-performance, product-conformity,
corrective-action-status, risk-register, changes,
external-provider-performance, management-changes} - 9 present of 9
required?  Count carefully: required families = 9; present = all except
resource-adequacy, plus the extra "management-changes" which is not a
required family.  present_count of REQUIRED = 8, required_count = 9,
coverage_ratio = 8/9 = 0.889.  Actions: 3 open of 4 total, 1 overdue
(action a3 due 2026-08-15).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds:
- due_date "2026-11-30" (12 calendar months from 2025-11-30, month-end
  clamp keeps the 30th).
- coverage_ratio 0.889 (8/9), missing_inputs ["resource-adequacy"].
- track_actions: total 4, open 3, overdue 1, overdue_ratio 0.25,
  overdue_actions ["a3"].
- review_verdict(True, 0.889, 1) -> "overdue-actions" (coverage 0.889
  >= 0.85 passes; the overdue action drives the verdict).
- review_verdict(True, 0.8, 0) -> "incomplete-inputs"; (True, 0.7, 2)
  -> "incomplete-inputs-and-overdue-actions"; (True, 0.9, 0) ->
  "compliant".
- management_review_review returns the full dict with verdict
  "overdue-actions".

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: malformed date, interval <= 0, empty mandatory inputs,
  action with unknown status or empty owner.
- Due-date clamping: 2026-01-31 + 1 month -> 2026-02-28; 2024-01-31 +
  1 month -> 2024-02-29 (leap year); 2026-08-31 + 1 month -> 2026-09-30.
- Coverage edge: all required present -> ratio 1.0 missing empty;
  none present -> ratio 0.0 missing all 9 sorted.
- Coverage counts only REQUIRED families (an extra non-required input
  does not raise the ratio above 1.0).
- Overdue detection is relative to the passed today: an action due
  after today is not overdue.
- Verdict truth table: all four output strings reachable as in the
  worked example; combined string used when both conditions hold.
- Determinism: no RNG, run-to-run identical.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-management-review.yaml)

Query 1 (copy verbatim):
  "compute the management review due date and check the input coverage of the top management review against the required input families of the quality management system"
  intent: "manufacturing-quality; AS9100 top management review scheduling and input coverage"
  expected_skill: "manufacturing-quality/as9100/management-review"
Query 2 (copy verbatim):
  "track the action items from a management review decision log and issue the review verdict from the input coverage ratio and the overdue action count"
  intent: "manufacturing-quality; management review action tracking and verdict"
  expected_skill: "manufacturing-quality/as9100/management-review"
Task ids: w32-management-review-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must plan and score the periodic
top-management review process under an AS9100-style quality management
system:" and include the outputs in the Claim. First tag:
management-review. Additional tags ONLY: top-management,
review-interval, review-inputs, action-item-tracking, review-verdict,
qms-review. NEVER single generic words (management, review, quality,
audit, input, action). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): audit-schedule, auditor-
independence, audit-sample-size, finding-classification,
closure-verification (internal-quality-audit owns audit program
mechanics); corrective action response, root cause, 8D (corrective-
action); clause-to-evidence, audit focus area, AS9100 aerospace
additions 8.1.x mapping (quality). Keep "audit" out of the description
except when naming the audit-results INPUT family.

Tags: [management-review, top-management, review-interval,
review-inputs, action-item-tracking, review-verdict, qms-review]

Sibling-citation lines for Related leaves:
manufacturing-quality/as9100/internal-quality-audit (9.2 audit
program), manufacturing-quality/as9100/quality (clause mapping),
manufacturing-quality/as9100/corrective-action (CAPA records that feed
review inputs), manufacturing-quality/as9100/risk-management.

Ledger Standard: as9100.
