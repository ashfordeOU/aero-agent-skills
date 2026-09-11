---
name: e1003-test-reviews
description: "Use when perform test readiness reviews and close-out reviews for a spacecraft test campaign under ECSS-E-ST-10C §4.3.2: verify each review has defined entry criteria grouped as mandatory or advisory, determine the outcome (pass, conditional pass, or fail) from which criteria are met, confirm all test anomalies carry a disposition before close-out, and ensure every review produces a complete record capturing review type, chair, attendees, criteria verdicts, outcome, and open action items. Apply the Test Readiness Review to gate entry to testing and the close-out review to gate release of results. Trigger: ecss, e-st-10-system-scope, test-readiness-review, close-out-review, review-criteria, anomaly-disposition, test-records, review-outcome."
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
  tags: [ecss, e-st-10-system-scope, test-readiness-review, close-out-review, review-criteria, anomaly-disposition, test-records]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Reviews — Readiness and Close-out (space-systems/ecss/e1003-test-reviews)

Use when the task is to perform the test readiness review or the
test close-out review of a spacecraft test campaign, following
ECSS-E-ST-10C §4.3.2. The two review types gate the beginning
and the end of a test activity: the Test Readiness Review (TRR)
confirms preconditions are met before testing starts; the close-out
review confirms all objectives, data, and anomaly dispositions are
complete before test results are formally released.

## Domain quick reference

- ECSS-E-ST-10C §4.3.2 requires that each review be structured
  around explicit criteria that are assessed as met or not met.
  Criteria fall into two groups: mandatory (must all be satisfied
  for the review to pass) and advisory (open items that are
  documented and tracked but do not block the review, provided a
  rationale is on record). A review with all mandatory criteria met
  and any advisory items open is a conditional pass; any unmet
  mandatory criterion produces a fail.
- The Test Readiness Review (TRR) gates entry to the test. Typical
  mandatory criteria: the test procedure has been reviewed and
  approved, the test item has a current accepted status with no open
  critical non-conformances, all test equipment calibration is
  current, a safety review has been completed, and test resources
  (facility and personnel) are allocated. These are paraphrased
  preconditions; the project tailors the exact list.
- The close-out review gates release of test results. Typical
  mandatory criteria: all test objectives have been completed or
  formally waived, test data has been recorded and archived, all
  anomalies raised during testing have a disposition on record, and
  the test summary report has been drafted. An anomaly with no
  disposition, or with a blocking disposition (open, NCR open,
  pending), prevents the close-out review from passing.
- Every review must produce a record with: review type, date, chair,
  attendee list, criteria list with verdicts and evidence, overall
  outcome, and a list of action items. A record missing any of these
  fields is incomplete and must not be filed as final.

## Workflow

1. Confirm the review type (TRR or close-out) and retrieve the
   applicable mandatory and advisory criteria from the test plan.
   Reject a review whose criteria list is empty or contains entries
   with no name or no category.
2. For each criterion, record whether it is met (boolean) and, if
   not met, capture the evidence or rationale explaining the gap.
   An unmet criterion with no evidence is flagged as an error before
   the outcome is derived.
3. Determine the review outcome from the criteria verdicts: if any
   mandatory criterion is not met, the outcome is FAIL; if all
   mandatory criteria are met but one or more advisory criteria are
   not met, the outcome is CONDITIONAL_PASS (requires documented
   waiver); if all criteria are met, the outcome is PASS.
4. For a close-out review, additionally check every anomaly raised
   during the test. Each anomaly must carry a disposition; anomalies
   with blocking dispositions (open, NCR open, pending) are treated
   as unmet mandatory criteria and force a FAIL outcome regardless
   of the formal criteria list.
5. Assemble the review record: review type, date, chair, non-empty
   attendee list, the full criteria list with verdicts, the derived
   outcome, and an action-items list (may be empty if all criteria
   are met and no anomalies are blocking). Validate the record for
   completeness before filing.
6. Aggregate TRR and close-out outcomes to produce an overall test
   activity status: any FAIL in either review produces a FAIL
   overall; any CONDITIONAL_PASS (with no FAIL) produces a
   CONDITIONAL_PASS; only two PASS verdicts produce an overall PASS.

## Pitfalls

- Treating an empty evidence field as acceptable for an unmet
  criterion — a criterion recorded as not met must carry a
  rationale or corrective-action reference; without it the
  review record cannot be audited.
- Conflating mandatory and advisory criteria — an advisory criterion
  open at TRR must be documented with a waiver or action item, not
  silently dropped; collapsing both groups makes conditional passes
  indistinguishable from clean passes.
- Filing the close-out review without checking anomaly dispositions
  — an anomaly with a blocking disposition is not a bookkeeping item;
  it represents an unresolved finding that the test result cannot
  absorb until the disposition is closed.
- Aggregating review outcomes by simple majority — one FAIL in either
  the TRR or the close-out review is a programme blocker; averaging
  or majority-voting outcomes masks that.

## Behavior contract (gate 3)

The criterion categorization, outcome derivation, anomaly check,
record validation, and aggregation logic is exercised by the gate 3
contract test: scripts/test_e1003_test_reviews.py against
scripts/e1003_test_reviews_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_test_reviews.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
