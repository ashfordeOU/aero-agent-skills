---
name: q6012-test-matrix-review-item
description: "Evaluate the planned measurement coverage a design review is shown, requirement by requirement, and decide whether the matrix closes. Use when an ECSS-Q-ST-60-12C clause 7.3.8 test matrix review item has to reach a verdict: trace each requirement forwards to an activity whose method it permits, that carries measurable pass criteria, and whose conditions between them span every corner the requirement is specified over; trace each activity backwards so one closing nothing and one citing a requirement the matrix never listed stay separate findings; then report the coverage reached overall and over the requirements grouped as critical. Trigger: ecss, q-st-60-12c-clause-7-3-8, verification-matrix-review-item, requirement-to-activity-trace, verification-method-admissibility, test-condition-corner-coverage, orphan-verification-activity, verification-coverage-fraction."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-test-matrix-review-item, q-st-60-12c-clause-7-3-8, verification-matrix-review-item, requirement-to-activity-trace, verification-method-admissibility, test-condition-corner-coverage, orphan-verification-activity, verification-coverage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Design Review -- Test Matrix Review Item (space-systems/ecss/q6012-test-matrix-review-item)

Use when the task is the test matrix review item of ECSS-Q-ST-60-12C clause
7.3.8: a design review has been shown the planned measurement coverage, and
the question is whether every requirement is actually mapped to work that
can close it.

## Domain quick reference

- The matrix is a two-way trace, not a list. Forwards, every requirement has
  to reach an activity that can close it; backwards, every activity has to
  reach a requirement that exists. A matrix that is complete in one
  direction and not the other is the usual state of a first draft, and the
  two directions produce different actions.
- A row in the matrix is not coverage by itself. An activity closes a
  requirement only when the requirement permits that verification method,
  and only when the activity carries measurable pass criteria. A
  performance requirement discharged by review of design, or a test with no
  written criteria, is planned work that cannot produce a verdict.
- Conditions are the third axis and the one most often lost. A requirement
  specified over a set of corners is closed only when the admissible
  activities covering it span that whole set between them. One activity at
  ambient does not close a requirement written across temperature, and the
  union has to be taken over admissible activities alone -- an inadmissible
  activity contributes no corners.
- Backwards, two defects look alike and are not. An activity that closes
  nothing is surplus planned work; an activity citing an identifier the
  matrix never listed is a broken reference, which usually means a
  requirement was deleted or renumbered without the matrix following.
- Coverage is reported as a fraction, and reported twice: over all
  requirements, and over the subset grouped as critical. A comfortable
  overall figure hiding an uncovered critical requirement is the failure the
  second figure exists to expose.

## Workflow

1. Validate both sides first: repeated requirement identifiers, repeated
   activity identifiers, an unknown verification method or an empty
   condition set are input errors that stop the item.
2. Normalise identifiers, methods and condition names to one case so a
   trace is not lost to spelling.
3. For each requirement, collect every activity naming it, then narrow to
   the admissible ones: method permitted by the requirement, measurable pass
   criteria present.
4. Take the union of the conditions of those admissible activities and
   report the corners the requirement is specified over that it misses.
5. Record the requirement as open with its reason -- nothing names it, every
   activity naming it is inadmissible, or conditions are missing -- so the
   action goes to the right owner.
6. Trace backwards, separating activities that close nothing from activities
   citing an identifier the matrix does not list.
7. Report coverage over all requirements and over the critical subset, and
   close the item only when nothing is open in either direction.

## Pitfalls

- Counting a row as coverage. The row is a claim; the method has to be one
  the requirement permits and the activity has to carry criteria before the
  claim is coverage.
- Taking the condition union over every activity naming the requirement. An
  inadmissible activity contributes no corners, so including it closes a
  requirement on work that cannot produce a verdict.
- Treating an activity that closes nothing as harmless. It is either surplus
  cost or a trace that was never written, and only asking can tell which.
- Reading a broken reference as an orphan. An activity citing a requirement
  the matrix never listed usually means a renumbering the matrix did not
  follow, and the fix is upstream of the activity.
- Reporting one coverage figure. An overall fraction near one can sit on top
  of an uncovered critical requirement, which is exactly the case the review
  item exists to catch.
- Closing the item on a first-draft matrix because every requirement appears
  somewhere. Appearing is the forward trace only; the backward trace and the
  condition union are still outstanding.

## Behavior contract (gate 3)

The requirement and activity validation, identifier normalisation, the
forward trace with method admissibility and pass-criteria filtering, the
condition-union gap report, the backward trace separating surplus activities
from broken references, and the overall and critical coverage fractions are
exercised by the gate 3 contract test:
scripts/test_q6012_test_matrix_review_item.py against
scripts/q6012_test_matrix_review_item_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6012_test_matrix_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
