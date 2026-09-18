---
name: q6012-design-trade-off-analysis
description: "Evaluate the candidate MMIC architectures against performance, yield, die size and dc power together. Use when ECSS-Q-ST-60-12C clause 7.1.4 settles a microwave circuit architecture: eliminate the candidates that miss a requirement threshold and name every criterion each one missed, normalise the survivors onto a clamped threshold-to-goal utility so over-delivery on one axis cannot buy a shortfall on another, weight and rank them, report scores inside the tie tolerance as ties rather than a preference, then perturb each weight and flag a lead that changes under it. Refuses a weight set that does not partition one. Trigger: ecss, q-st-60-12c-clause-7-1-4, mmic-architecture-trade-off, mmic-performance-yield-size-power-trade, mmic-threshold-goal-utility, mmic-trade-weight-sensitivity-flip, mmic-architecture-preference-tie."
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
  tags: [ecss, q-st-60-12-mmic-design-scope, q6012-design-trade-off-analysis, mmic-architecture-trade-off, mmic-performance-yield-size-power-trade, mmic-threshold-goal-utility, mmic-trade-weight-sensitivity-flip, mmic-architecture-preference-tie]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Design — Architecture Trade-Off (space-systems/ecss/q6012-design-trade-off-analysis)

Use when the task is the trade-off branch of ECSS-Q-ST-60-12C clause
7.1.4 — weighing what the candidate microwave circuit architectures cost
each other in performance, yield, die size and dc power, and settling
which architecture the design goes forward with.

## Domain quick reference

- The four axes pull against each other by construction. Gain bought
  with more stages costs die area and dc power; die area bought back by
  shrinking the cell costs yield, because defect density acts on area
  and process spread acts on the smaller geometry. A trade that improves
  one axis without moving another has usually mis-stated a metric.
- Each axis carries two numbers, not one. The requirement threshold is
  the value below which the architecture is not offerable at all; the
  goal is the value beyond which further improvement buys nothing. Both
  are needed, because a score built from the threshold alone rewards
  unbounded over-delivery on whichever axis is cheapest to improve.
- Two of the axes improve downwards. Die area and dc power are better
  when smaller, so their utility runs from the threshold down to the
  goal. Getting a direction wrong inverts a whole axis and the trade
  still returns a confident answer, which is why direction is validated
  rather than inferred from the numbers.
- Threshold failures eliminate rather than score. A candidate below a
  requirement is not a low-scoring option, it is not an option, and
  every criterion it missed is named — a single-axis near miss is a
  rework instruction, a four-axis miss is a dead architecture.
- Utilities are clamped at both ends. Without the clamp, an architecture
  far past the goal on performance can buy a shortfall on yield, which
  is exactly the trade the thresholds exist to forbid.
- A weighted score separates two architectures only when the separation
  survives the weights. Two scores inside the tie tolerance are a tie,
  reported as one, and a lead that changes when a weight is moved a
  little means the trade settled the weighting rather than the
  architecture. Both are findings, not preferences.

## Workflow

1. Validate the weight set: one weight per criterion, none negative,
   summing to one within the named tolerance. A weight set that does not
   partition one makes the scores incomparable and is an input error.
2. Validate the threshold and goal pair per criterion, checking that the
   goal sits on the improving side of the threshold for that axis'
   direction. A goal on the wrong side is refused rather than absorbed.
3. Evaluate each candidate against the thresholds and collect every
   criterion it misses. Candidates with any miss are eliminated with
   their reasons and take no further part in the ranking.
4. Normalise each surviving candidate's four metrics onto a zero-to-one
   utility between threshold and goal, clamped at both ends, and take
   the weighted sum as the trade score.
5. Order the survivors best first, falling back to the candidate name so
   a re-run of the same inputs gives the same order. Report any score
   inside the tie tolerance of the leader as tied.
6. Move each weight up and down by the perturbation, renormalise the
   remaining weights proportionally, and re-rank. Record every move that
   hands the lead to a different architecture.
7. Report the preference as decision-supporting only when it is
   untied and survives every weight perturbation; otherwise return the
   ties and flips as findings against the trade, not against the
   architectures.

## Pitfalls

- Scoring a candidate that misses a requirement. A below-threshold
  architecture ranked low still appears in the ranking, and a later
  reader takes its presence as offerability.
- Stopping at the first threshold miss. Naming only one of four missed
  criteria makes a dead architecture look like a near miss and sends
  rework after the wrong axis.
- Leaving the utilities unclamped. An architecture far beyond the
  performance goal then outscores one that meets every requirement
  comfortably, which is the trade the thresholds were written to stop.
- Inferring a criterion's direction from the candidate numbers. Die area
  and dc power improve downwards; an inferred direction inverts the axis
  silently and the ranking still looks well formed.
- Breaking a tie on float noise. Two architectures whose scores differ
  in the last bits are tied, and picking one of them presents an
  arbitrary choice as a trade result.
- Reporting the preferred architecture without the weight sensitivity. A
  lead that flips on a small weight move is a statement about the
  weighting, and shipping it as the architecture decision hides the
  choice that was actually made.

## Behavior contract (gate 3)

The weight validation, threshold and goal direction checks, the clamped
threshold-to-goal normalisation, threshold elimination with every missed
criterion named, the weighted ranking with its reproducible tie-break,
the tie report and the weight-perturbation sensitivity are exercised by
the gate 3 contract test:
scripts/test_q6012_design_trade_off_analysis.py against
scripts/q6012_design_trade_off_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_design_trade_off_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
