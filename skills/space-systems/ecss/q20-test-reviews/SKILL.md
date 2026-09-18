---
name: q20-test-reviews
description: "Perform the readiness and post-test reviews of ECSS-Q-ST-20C clause 5.6.5 as graded decisions rather than meetings: grade each review against the criterion list its own kind owns, refuse a waiver on a criterion that kind holds mandatory and demand a reference and an approver on the waivers it does allow, check the chair and product assurance were present with minutes referenced and no blocking action left open, and check a readiness review closed before the test started and a post-test review was held after it ended. Use when deciding go or no-go, or whether a finished test can be called closed. Trigger: ecss, q-st-20c-clause-5-6-5, test-readiness-review-criteria, post-test-review-closure, review-waiver-admissibility, review-blocking-action, trr-ptr-schedule-order."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-test-reviews, test-readiness-review-criteria, post-test-review-closure, review-waiver-admissibility, review-blocking-action, trr-ptr-schedule-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance -- Test Readiness and Post-Test Reviews (space-systems/ecss/q20-test-reviews)

Use when the task is the test-review requirement of ECSS-Q-ST-20C
clause 5.6.5: a review is held before a test to decide whether it may
start, and another after it to decide whether it is finished, and the
question is whether either of them actually reached a decision that can
be defended.

## Domain quick reference

- The two reviews grade different lists. A readiness review settles the
  procedure, the article configuration, the facility and ground support
  equipment calibration, the safety clearance, the disposition of open
  nonconformances and the assignment of personnel. A post-test review
  settles data completeness, the disposition of discrepancies, whether
  the objectives were met, whether the report issued, and the post-test
  inspection of the article. A criterion from one list graded at the
  other review is an error, not a bonus.
- A criterion is met, not met, or waived, and waiving is the interesting
  case. Some criteria exist precisely because they cannot be traded
  away -- an uncalibrated facility or an undisposed nonconformance
  defeats the point of holding the review -- so a waiver on those is
  refused outright. Where a waiver is admissible it still carries a
  reference and an approver, because an unattributed waiver is an
  opinion.
- A review that is not recorded did not happen. The chair and product
  assurance in the room, a minutes reference, and no action raised as
  blocking left open: these are what make the decision auditable later.
  A non-blocking action may stay open; that is what the distinction is
  for.
- The dates are part of the decision. A readiness review held after the
  test has already started is a rubber stamp, and a post-test review
  held before the test ended reviewed something that had not finished.
- The pair has a joint outcome. A no-go readiness review means the test
  should never have started, whatever the post-test review says; a clean
  readiness review with an open post-test review means the test ran but
  is not closed.

## Workflow

1. Normalise the review: its kind, its criteria and their states, its
   attendance, its action items, its minutes reference and its date.
   Reject a criterion foreign to the kind, a duplicate criterion, an
   unrecognised state or a duplicate action before grading.
2. Grade the criteria: name the ones the review never addressed, the
   ones not met, the waivers on mandatory criteria, and the waivers
   missing a reference or an approver.
3. Grade the record: the chair and product assurance present, a minutes
   reference, and no open blocking action.
4. Grade the schedule against the test window, in the direction that
   belongs to the kind of review.
5. Compute the cleared fraction of the kind's criteria as evidence, so a
   no-go carries a number rather than only a verdict.
6. Combine the pair: the test is closed only when the readiness review
   was a go and the post-test review is clean; a missing post-test
   review leaves a test that ran but is not closed.

## Pitfalls

- Grading both reviews against one merged checklist. The lists differ
  because the questions differ, and merging them lets a post-test item
  clear a readiness gap.
- Accepting a waiver because somebody senior agreed in the room. The
  waiver has to name a reference and an approver, and on a mandatory
  criterion no approver is enough.
- Closing a review with a blocking action open on the grounds that it is
  nearly done. Blocking is a property the review itself assigned; if it
  was not blocking, it should not have been raised as blocking.
- Holding the readiness review after the article is already in the
  chamber. The review decides whether to commit the article, so a date
  after the test start inverts the decision it was meant to make.
- Reporting a verdict with no fraction behind it. The cleared fraction
  is what tells a programme whether a no-go is one open item or half the
  list.

## Behavior contract (gate 3)

The kind-specific criterion lists, the waiver admissibility rule, the
attendance and minutes record check, the blocking-action rule, the
schedule direction per kind, the cleared fraction and the joint pair
verdict are exercised by the gate 3 contract test:
scripts/test_q20_test_reviews.py against
scripts/q20_test_reviews_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_test_reviews.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
