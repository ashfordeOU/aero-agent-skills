---
name: trade-study-analysis
description: "Use when you must run a trade study or alternative selection for an aerospace system or subsystem: set decision criteria with weights that sum to 1.0, score each candidate, build a Pugh matrix with plus/zero/minus marks against a baseline concept, compute weighted scores, judge the selection margin between the best and runner-up alternative, perturb the weights to test sensitivity, and confirm every candidate traces to requirement ids. Produces the ranked alternative list, the Pugh verdict, the sensitivity ranking, and the selection decision with margin and tie handling. Trigger: trade study, trade-off, Pugh matrix, decision criteria, weighted scoring, sensitivity analysis, alternative selection, selection margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: mbse
  tags: [trade-study-analysis, trade-study, trade-off, pugh-matrix, decision-criteria, weighted-scoring, sensitivity-analysis, alternative-selection, selection-margin, mbse]
  version: 0.1.0
  author: AeroSkills
---

# Trade Study Analysis (systems-engineering-safety/mbse/trade-study-analysis)

Use when the task is a trade study or alternative selection for an
aerospace system or subsystem: weighted scoring of candidate
concepts, Pugh matrix comparison against a baseline, sensitivity of
the ranking to the criterion weights, and the selection decision
with margin and traceability.

## Domain quick reference

- Weighted scoring: score(A) = sum over criteria i of w_i * s_i(A),
  with the weights summing to 1.0. Example: criteria mass, cost,
  reliability with weights 0.5, 0.3, 0.2 and scores 8, 6, 9 give
  8*0.5 + 6*0.3 + 9*0.2 = 7.6.
- Weight validation: weights must sum to 1.0 within a small
  tolerance (about 1e-9). A set that does not sum to 1.0 raises
  ValueError instead of silently skewing the ranking.
- Pugh matrix: rows are criteria, columns are alternatives, and each
  cell is +1 (better than the baseline), 0 (same as the baseline),
  or -1 (worse than the baseline). The baseline column scores 0 on
  every row by definition. Net score of an alternative = sum over
  rows of (cell - baseline cell); rank the alternatives by net score
  descending.
- Selection margin: margin = best_score - runner_up_score. A margin
  at or below the numerical tolerance is a tie; a margin below the
  configured threshold (default 0.05 on the weighted score scale)
  flags a weak decision that needs more discrimination between the
  candidates.
- Sensitivity analysis: perturb each weight upward by a fixed
  amount and renormalize the remaining weights so the set still sums
  to 1.0, then re-rank. If the winner changes under a single weight
  perturbation, the decision is sensitive to that criterion and the
  weight needs justification.
- Traceability: every alternative's rationale should cite
  requirement ids. The check flags alternatives that cite no
  requirements and requirements that no alternative covers.
- ARP4754A sets the development-planning context: alternative
  concepts are evaluated and the chosen concept is justified as part
  of the development plan, and the selection rationale traces back
  to the requirements. The scoring relations above are common
  decision-analysis methodology.

## Workflow

1. Define the decision criteria and the weights; verify the weights
   sum to 1.0 (the module raises ValueError otherwise).
2. Score each candidate on each criterion on one common scale
   (normalize any mixed scales first).
3. Compute the weighted score of each alternative with
   weighted_score(weights, scores).
4. Build the Pugh matrix with entries in {-1, 0, +1} and get the
   ranking with pugh_matrix_verdict(pugh_matrix, baseline_index).
5. Test the stability of the ranking with
   sensitivity_ranking(weights, scores, perturbation); rework the
   weights if a single perturbation flips the winner.
6. Apply selection_verdict(best_score, runner_up_score) and read
   the margin and the tie handling before declaring a winner.
7. Close the trade study with traceability_check(alternatives,
   requirement_ids) so every candidate and requirement is covered.

## Pitfalls

- Weights that do not sum to 1.0: the ranking is skewed toward the
  criteria with the larger raw weights; the module rejects the set
  with ValueError instead.
- Scoring on mixed scales: a 0 to 10 scale for one criterion and a
  0 to 100 scale for another makes the wide scale dominate the
  weighted sum; normalize every criterion to one scale first.
- Forgetting the baseline column: the Pugh matrix is meaningless
  without the reference concept that every cell is judged against.
- Using raw sums instead of relative-to-baseline differences: a
  candidate that beats the baseline on every row must rank above the
  baseline, which only holds when each cell is compared with the
  baseline cell.
- Treating a tie as a win: selection_verdict returns a tie verdict
  when the margin is at or below the tolerance; add a discriminating
  criterion or revisit the weights instead of picking arbitrarily.
- Skipping the sensitivity check: a decision that flips under one
  weight perturbation rests on a single judgment and is not robust
  to review.
- Closing without traceability: an alternative with no requirement
  ids cannot be justified in the certification context; run
  traceability_check before the selection is recorded.
- Treating a small margin as a confident win: a margin below the
  threshold flags a weak decision even when the best score is the
  largest.

## Behavior contract (gate 3)

The weighted scoring, Pugh matrix verdict, sensitivity ranking,
selection verdict, and traceability check relations are exercised by
the gate 3 contract test: scripts/test_trade_study_analysis.py
against scripts/trade_study_analysis.py (stdlib unittest, offline).
Run: python3 scripts/test_trade_study_analysis.py

## Compliance

- Standards referenced, not reproduced: ARP4754A is a commercial SAE
  standard (purchase required); the trade study relations (weighted
  scoring, Pugh matrix, sensitivity analysis) are common
  decision-analysis methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
