---
name: e10-tradeoffs
description: "Use when comparing candidate solutions to a system engineering decision under ECSS-E-ST-10C clause 5.3.3 and Annex L: define the evaluation criteria and their weights, score each candidate against every criterion on a common scale, gate any candidate that fails a mandatory pass/fail criterion, rank the remaining candidates by weighted score, and flag when the recommendation is a close call sensitive to the weighting assumptions rather than a clear-cut winner -- then record the result as a trade-off report. Trigger: ecss, e-st-10-system-scope, trade-off analysis, tradeoff, evaluation criteria, weighted scoring, candidate solution, annex l, trade-off report."
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
  tags: [ecss, e-st-10-system-scope, tradeoffs, trade-off-analysis, weighted-scoring, annex-l, decision-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Trade-off Analysis (space-systems/ecss/e10-tradeoffs)

Use when the task is choosing between candidate solutions to a system
engineering decision under ECSS-E-ST-10C clause 5.3.3 -- running a
documented trade-off analysis against a fixed set of weighted
criteria and recording the outcome as an Annex L trade-off report.

## Domain quick reference

- A trade-off analysis compares two or more candidate solutions to
  the same decision (a design option, a technology, a supplier, an
  architecture) against a fixed set of evaluation criteria agreed
  before scoring starts. Each criterion carries a weight expressing
  its relative importance; weights are normalized to a common total
  so studies with different numbers of criteria stay comparable.
- Some criteria are mandatory (pass/fail) rather than weighted: a
  safety, regulatory, or interface-compatibility criterion below its
  pass threshold disqualifies the candidate outright, no matter how
  well it scores elsewhere. Weighted scoring only ranks candidates
  that clear every mandatory criterion.
- Every candidate is scored against every criterion on the same fixed
  scale so scores are comparable across candidates; a candidate
  missing a score for a criterion, or scored on a criterion outside
  the agreed set, is a broken trade-off study and is rejected before
  ranking.
- The trade-off report (Annex L) does not just declare a winner: it
  records the ranking, the rationale (criteria, weights, scores), and
  whether the outcome is a close call -- a thin margin or a tie at
  the top means the recommendation is sensitive to the weighting
  assumptions and must be reported as such, not smoothed into a false
  single winner.

## Workflow

1. Define the criteria set and each criterion's weight before scoring
   any candidate; mark any pass/fail criterion as mandatory with its
   pass threshold. Reject a criteria set that is empty, carries a
   non-positive weight, or marks a criterion mandatory without a pass
   threshold -- the study cannot proceed.
2. Score every candidate against every criterion on the fixed scale.
   Reject a candidate whose scores do not cover exactly the agreed
   criteria set (missing or extra criterion) or that carries a score
   outside the scale -- fix the input before ranking.
3. For each candidate, check every mandatory criterion's pass
   threshold. A candidate below any mandatory threshold is
   disqualified and is not weighted-scored.
4. Weighted-score every qualified candidate: normalize the criteria
   weights to sum to one, then sum weight x score per criterion.
5. Rank the qualified candidates by descending weighted score, using
   competition ranking so tied scores share a rank and the next
   distinct score resumes at its true position (not the next integer).
6. Check whether the top of the ranking is a close call: the top two
   qualified candidates are tied, or the leader's score is within a
   small margin of the runner-up's. Report a single winner only when
   the ranking is not a close call and exactly one candidate holds
   rank 1; otherwise report the ranking with the close-call flag set
   and withhold a single recommendation.

## Pitfalls

- Scoring candidates before the criteria and weights are agreed --
  criteria chosen or reweighted after seeing the scores bias the
  outcome toward whichever candidate was already favored.
- Letting a high weighted score on other criteria compensate for a
  failed mandatory criterion -- mandatory criteria are a gate, not
  another weighted input; a disqualified candidate stays disqualified
  regardless of its other scores.
- Declaring a single winner when the leader and runner-up are tied or
  within a thin margin -- a razor-thin or tied result is itself a
  finding (the decision is sensitive to the input assumptions) and
  belongs in the trade-off report, not hidden behind a confident
  recommendation.
- Comparing candidates whose scores were assessed against different
  criteria sets or scales -- a candidate that skipped a criterion, or
  was scored on a scale the others weren't, produces a ranking that
  looks complete but is not actually comparable.

## Behavior contract (gate 3)

The criteria/weight validation, candidate-score validation, mandatory
pass/fail gating, weighted ranking, and close-call sensitivity logic
is exercised by the gate 3 contract test:
scripts/test_e10_tradeoffs.py against scripts/e10_tradeoffs_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e10_tradeoffs.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
