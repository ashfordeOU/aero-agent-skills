---
name: q6013-class-3-lot-homogeneity
description: "Assess whether a commercial EEE delivery may be treated as one uniform batch for reduced sampling at the lowest assurance class, under ECSS-Q-ST-60-13C clause 6.5.5: end uniformity outright where part number or package code differ, weight the remaining supply attributes into a uniformity score held as an exact integer ratio, relax the threshold only where a supplier batch declaration covers every unit, take the date-code window in whole weeks against the admitted limit, size the reduced sample by exact integer square root, and require the drawn units to reach both ends of the window. Use when sampling rests on procurement evidence rather than wafer lots. Trigger: ecss, q-st-60-13c-clause-6-5-5, class-three-batch-uniformity, supply-attribute-uniformity-score, supplier-batch-declaration-relief, date-code-window-endpoints, integer-root-reduced-sample, package-code-conflict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-lot-homogeneity, class-three-batch-uniformity, supply-attribute-uniformity-score, supplier-batch-declaration-relief, date-code-window-endpoints, integer-root-reduced-sample, package-code-conflict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Lot Homogeneity (space-systems/ecss/q6013-class-3-lot-homogeneity)

Use when the task is the clause 6.5.5 uniformity precondition of
ECSS-Q-ST-60-13C at the lowest assurance class: a commercial delivery is
about to be sampled, the manufacturer publishes no wafer or assembly lot
behind it, and the only evidence of one production run is what the
procurement paperwork and the parts themselves carry.

## Domain quick reference

- Uniformity here is assembled out of supply evidence, not out of a
  traceability tuple. Part number, package code, manufacturer, marking
  style, origin and the distributor reference are what a commercial
  delivery actually offers, and the question is how many of them hold
  across the whole box.
- Two of those attributes are not scored at all. A delivery carrying two
  part numbers or two package codes is two different articles, and no
  weighting of the remainder makes one sample speak for both. That is a
  stop, taken before any score is computed.
- The rest are weighted and summed into a score held as an exact integer
  ratio of matched weight to total weight. Weights are a declared input,
  so a programme that values origin above marking style says so in the
  policy rather than in the reading of the result.
- A supplier batch declaration is the relief this class admits. Where
  the supplier names one production batch and that declaration covers
  every unit in the delivery, the score threshold drops to the declared
  relaxed figure. A declaration missing even one unit gives no relief at
  all; it is a statement about a different population.
- The date-code window is an independent axis. Parts that agree on every
  supply attribute can still have been made months apart, so the window
  in whole weeks is compared with the limit whatever the score says.
- The reduced sample this class permits is sized by exact integer square
  root of the delivery, bounded by a floor, a cap and the delivery
  itself, and it has to reach both ends of the date-code window. A
  sample drawn entirely from the middle of the window has tested the
  middle of the window.

## Workflow

1. Validate every unit: a non-empty identifier, the two decisive supply
   attributes, the weighted attributes, and a four-digit date code. A
   duplicate identifier is an input error.
2. Refuse a population whose two-digit years straddle a century
   rollover, because the window cannot be ordered from the codes alone.
3. Compare the decisive attributes across the population and stop on any
   that carries more than one value.
4. Score the weighted attributes: sum the weights of those holding one
   value across every unit, against the sum of all weights.
5. Validate any supplier batch declaration and check it names every unit
   before letting it lower the threshold.
6. Take the date-code window in whole weeks between the oldest and
   newest unit and compare it with the admitted limit.
7. Size the reduced sample by integer square root of the delivery,
   bounded by the floor, the cap and the delivery size.
8. Map the drawn units onto the window: count them, and confirm one sits
   at the oldest code and one at the newest.
9. Return one verdict in precedence order: a decisive attribute
   conflict, a window wider than admitted, a score below the applicable
   threshold, a sample that is undersized or does not span the window,
   otherwise a uniform batch.

## Pitfalls

- Averaging a package-code difference into the score. Two package codes
  are two articles; a score of ninety per cent over two articles is a
  number about nothing.
- Taking a supplier batch declaration at face value. The relief comes
  from the declaration covering the delivery, so a declaration that
  names ninety of a hundred units is evidence about ninety units and the
  delivery is still judged on its own score.
- Reading a high score as a narrow date-code window. The axes are
  independent: one distributor, one marking and one origin say nothing
  about how far apart the parts were made.
- Sizing the reduced sample with a floating-point square root. A
  delivery of exactly a hundred sits on the boundary, and that boundary
  is the one number two sites compare.
- Drawing the sample from whatever was on top of the box. Units near one
  date code cluster together in a reel, so a sample that never reaches
  the far end of the window has left the oldest material untested.
- Reporting uniformity as a single yes. The useful output is which
  attributes held, which did not, and how wide the window was, because
  that is what the next delivery gets compared against.

## Behavior contract (gate 3)

The unit validation, century-rollover refusal, decisive-attribute stop,
weighted uniformity scoring, declaration relief, date-code window,
integer-root sample sizing, window endpoint coverage and verdict
precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_lot_homogeneity.py against
scripts/q6013_class_3_lot_homogeneity_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_3_lot_homogeneity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
