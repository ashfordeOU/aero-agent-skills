---
name: q2007-lessons-learned
description: "Run the lessons-learned review that closes a test campaign at a space test centre under ECSS-Q-ST-20-07C clause 5.8.3: validate each register entry against its source event, rank it by the product of recurrence, consequence and detectability, place it in a priority band, route it to the procedure, facility, instrumentation, training, interface or planning baseline that must absorb it, then grade the register at a review day on closure, overdue entries and entries captured per campaign anomaly. Use when a post-test lessons-learned register, review minutes or improvement actions have to be assessed. Trigger: ecss, q-st-20-07c, test-campaign-lessons-learned, lessons-learned-register, lesson-priority-index, lesson-feedback-route, lessons-capture-ratio, post-test-review-closure."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-lessons-learned, test-campaign-lessons-learned, lessons-learned-register, lesson-priority-index, lesson-feedback-route, post-test-review-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Lessons Learned from Test Campaigns (space-systems/ecss/q2007-lessons-learned)

Use when the task is the lessons-learned step of ECSS-Q-ST-20-07C clause
5.8.3 — turning what a finished test campaign taught the centre into ranked,
owned, routed changes rather than a list of observations that nothing
absorbs.

## Domain quick reference

- A lesson that changes no controlled item is a note. What makes an entry a
  lesson is its route: the procedure, the facility baseline, the measurement
  chain, the training syllabus, the customer interface agreement or the
  programme plan that has to be revised because of it. The route is a
  property of the category, not of the person who raised the entry.
- Ranking is needed because a register is always longer than the change
  budget. Three ordinals carry most of the signal: how often the event
  recurs, how bad its consequence was, and how hard it was to notice. Their
  product spreads a small register across a wide range, which is what makes
  a band boundary meaningful.
- Detectability is the ordinal most often dropped, and it is the one that
  distinguishes a nuisance from a latent hazard. A mild consequence that
  nobody can see coming outranks a visible one that always announces itself.
- An entry that is closed needs neither an owner nor a target; an entry that
  is open needs both, and an open entry past its target is the register's
  own failure mode, because nothing decays a lessons process faster than a
  list of actions nobody is accountable for.
- Capture is measured against the campaign, not against the register. Entries
  per anomaly says whether the review looked at what happened; a beautifully
  managed register of two entries after twelve anomalies has a capture
  problem, not a closure problem.
- Feedback is a loop only once the routed item is actually revised. Routing
  is the step the review owes; the revision is tracked by whichever baseline
  owns the routed item.

## Workflow

1. Validate each register entry: identifier, source event, category,
   recommendation and the three ordinals are required; owner, target day and
   status carry the accountability.
2. Rank each entry by the product of the three ordinals and place it in its
   priority band on integer boundaries, so no entry sits ambiguously between
   bands.
3. Route each entry from its category to the controlled item that has to
   absorb it, and reject a category with no route rather than filing the
   entry as general.
4. Grade each entry at the review day: an open entry with no owner or no
   target day is a finding, and an open entry past its target is counted as
   overdue with the days named.
5. Treat a high-band entry left unowned as a review-level finding, not an
   entry-level one, because it blocks the review from being complete.
6. Compute the register metrics — total, closed fraction, band counts,
   overdue count — and the capture ratio against the campaign anomaly count,
   refusing a ratio when there were no anomalies.
7. Conclude the review complete only when the finding list is empty, and
   report the distinct routes so each owning baseline can be notified.

## Pitfalls

- Filing entries without routes. A register whose entries name no controlled
  item produces no change, and the next campaign reproduces the same event
  with the lesson already written down.
- Ranking on consequence alone. Two entries with the same consequence differ
  entirely in priority once recurrence and detectability are applied, and
  dropping detectability systematically under-ranks latent problems.
- Reading a high closure fraction as a healthy review. Closure is measured
  over the entries that were captured, so a register that missed most of the
  campaign's anomalies can close every entry it holds.
- Computing a capture ratio with no anomalies in the denominator. That is not
  a perfect score; it is an undefined ratio, and the count is what should be
  reported.
- Leaving a target day on an entry that has been closed, or demanding one on
  an entry that has not been opened. The accountability fields are graded
  against the status, not in the abstract.
- Re-baselining an overdue target to clear the overdue count. The slip is the
  finding; a revised target is a decision that has to be recorded with its
  own owner.

## Behavior contract (gate 3)

The entry validation, ordinal ranking, band placement, category routing,
overdue arithmetic, register metrics, capture ratio and review verdict are
exercised by the gate 3 contract test:
scripts/test_q2007_lessons_learned.py against
scripts/q2007_lessons_learned_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_lessons_learned.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
