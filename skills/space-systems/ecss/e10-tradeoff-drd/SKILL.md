---
name: e10-tradeoff-drd
description: "Use when produce or review a trade-off report against the ECSS-E-ST-10C Annex L Document Requirements Definition: validate that the criterion weights form a normalized set, confirm every option carries a score against every criterion rather than defaulting a gap to zero, compute the weighted ranking and the margin to the runner-up, test whether shifting any single weight flips the winner, and decide whether the report reaches a defensible recommendation. Trigger: ecss, e-st-10-system-scope, trade-off-report, annex-l-drd, weighted-criteria, option-ranking, sensitivity-analysis, decision-margin."
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
  tags: [ecss, e-st-10-system-scope, trade-off-report, annex-l-drd, weighted-criteria, sensitivity-analysis, decision-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Trade-off Report DRD (space-systems/ecss/e10-tradeoff-drd)

Use when the task is to produce or check a trade-off report against the
Document Requirements Definition of ECSS-E-ST-10C Annex L -- the weighted
criteria, the options, the scores, the resulting ranking, and the
sensitivity statement that says whether the recommendation would survive a
plausible change in the weighting.

## Domain quick reference

- A trade-off needs at least two options. One option is a proposal with
  a scoring table attached, and reporting it as a trade-off lends a
  decision authority it never earned.
- Weights must form a normalized set summing to one. An unnormalized
  weighting still produces numbers, but they are not comparable between
  reports or against a threshold, so the set is rejected rather than
  silently scaled.
- A criterion carrying zero weight cannot affect the outcome. It is
  surfaced rather than quietly carried, because it usually means a
  weighting nobody finished.
- A missing score is reported, never defaulted. Treating an absent
  score as zero ranks an option that was never assessed last, and that
  looks exactly like a decision.
- Ranking ties break on the option identifier, not input order, so the
  same table always yields the same recommendation.
- The margin to the runner-up is part of the result. A winner ahead by
  a sliver is inside the noise of any subjective scoring, and the
  report should say so rather than present a rank order as decisive.
- Sensitivity asks a specific question: shift one weight by a plausible
  amount, renormalize, does the winner change? A criterion that flips
  it is named. That statement is the substance of Annex L's sensitivity
  requirement -- a recommendation nobody has stress-tested is an
  opinion.
- The report is conclusive only when it reaches a ranked winner with no
  findings.

## Workflow

1. Validate the criterion weighting: non-empty, non-negative, summing
   to one; record a finding for each zero-weight criterion.
2. Confirm option identifiers are present and unique.
3. Check that every option carries a score for every criterion; report
   each gap and stop before ranking if any exist.
4. Compute each option's weighted score and rank them, breaking ties on
   identifier.
5. Compute the margin between the top two and flag a margin too small
   to discriminate.
6. Shift each weight up and down by the sensitivity delta, renormalize,
   and record any criterion whose shift changes the winner.
7. The recommendation stands only when the finding list is empty.

## Pitfalls

- Letting a missing score fall through as zero. The unassessed option
  drops to last and the report reads as though it lost on merit.
- Normalizing the weights silently when they do not sum to one. The
  arithmetic succeeds, and the reader has no way to know the weighting
  they see is not the weighting that was applied.
- Presenting a rank order without the margin. A 0.05 gap on a
  ten-point scale is not a finding about the options, it is a finding
  about the method.
- Skipping sensitivity because the winner "obviously" leads. Obvious
  leads survive the test cheaply; the ones that do not are exactly the
  recommendations worth catching before a review.
- Shifting a weight without renormalizing, which changes the total and
  makes the trial scores incomparable with the baseline.
- Breaking a tie by input order, so re-sorting the option table
  silently changes the recommendation.

## Behavior contract (gate 3)

The weight validation, zero-weight, score-range, missing-score,
weighted-score, ranking, margin and weight-sensitivity logic is
exercised by the gate 3 contract test:
scripts/test_e10_tradeoff_drd.py against
scripts/e10_tradeoff_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_tradeoff_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
