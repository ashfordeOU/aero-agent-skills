---
name: q6012-mmic-layout-optimization
description: "Optimize the arrangement of active cells and combining interconnect on a MMIC die by trading die area against thermal spreading against insertion loss, under ECSS-Q-ST-60-12C clause 7.2.10: score each candidate placement, reject the ones that break a channel-temperature ceiling, an area budget or a loss allowance, and keep the best weighted survivor. Use when several cell pitches or die outlines are on the table and one arrangement has to be chosen and defended. Refuses a pitch that walks a cell off the die and weights that do not sum to one. Trigger: ecss, q-st-60-12c, mmic-cell-placement-pitch, mmic-thermal-spreading-resistance, mmic-die-area-budget, mmic-combining-interconnect-loss, peak-channel-temperature, mmic-layout-trade."
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
  tags: [ecss, q-st-60-12-mmic-die-scope, q6012-mmic-layout-optimization, mmic-cell-placement-pitch, mmic-thermal-spreading-resistance, mmic-die-area-budget, mmic-combining-interconnect-loss, peak-channel-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Die -- Layout Arrangement Trade (space-systems/ecss/q6012-mmic-layout-optimization)

Use when the task is the layout step of ECSS-Q-ST-60-12C clause 7.2.10: a MMIC
has several candidate arrangements of its active cells and combining network,
and the question is which placement balances die area, heat spreading and
electrical performance rather than winning one of them outright.

## Domain quick reference

- The placement pitch is the single variable that moves all three metrics at
  once, and it moves them against each other. Opening the pitch spreads the
  heat, so the centre cell runs cooler; it also lengthens the combining run and
  widens the die, so loss and area both rise. That opposition is the trade.
- The hot cell is not the average cell. A centre cell carries its own
  self-heating plus a share of every neighbour's, the share falling off with
  pitch and with how many cells away the neighbour sits, so peak channel
  temperature is what the arrangement is judged on, not the mean rise.
- A constraint and an objective are different instruments. A channel
  temperature ceiling, a die area budget and a loss allowance are pass or fail;
  the weighted score only ranks what already passed. Scoring an arrangement
  that breaks a ceiling produces a winner nobody can build.
- Weights only mean something on normalised metrics. Square millimetres,
  degrees and decibels do not add, so each metric is first expressed as a
  multiple of the best value any surviving candidate achieved for it, and the
  weights are applied to those pure ratios.
- One survivor is a result, not a trade. When constraints leave a single
  feasible arrangement there is nothing to weigh it against, and that is worth
  reporting rather than presenting the survivor as an optimum.

## Workflow

1. Validate each candidate: a name, a cell count, a placement pitch, the die
   outline, the dissipated power and the combining feed. A pitch that walks the
   outermost cell past the die edge is an input error, not a compact layout.
2. Derive the three metrics per candidate: die area from the outline; effective
   thermal resistance of the centre cell from self-heating plus mutual heating;
   peak channel temperature from the baseplate, the per-cell power and that
   resistance; insertion loss from the combining length and the loss per
   millimetre of the technology.
3. Apply every hard constraint, absorbing floating-point representation error
   at the limit with a named tolerance so an exactly-sized candidate is kept,
   and retain each rejected candidate together with the reason it fell.
4. Normalise the surviving candidates metric by metric against the best value
   seen, apply the validated weights, and rank by the weighted score with the
   candidate name breaking ties so the run is reproducible.
5. Report the selection, the full ranking, the rejected candidates with reasons
   and any finding, so the arrangement can be defended and not just named.

## Pitfalls

- Trading on average die temperature. The failure mechanism follows the hottest
  channel, and an arrangement that looks comfortable on the mean can be well
  past its ceiling at the centre cell.
- Treating a ceiling as a heavy weight. Weighting a constraint lets a candidate
  buy its way past a limit with area or loss, which is how an infeasible
  arrangement reaches a review as the recommended one.
- Adding raw metrics. Millimetres squared, degrees and decibels summed directly
  produce a score dominated by whichever unit happens to have the largest
  numbers, and the weights then mean nothing.
- Tightening the pitch to recover die area without re-running the thermal step.
  Mutual heating rises as the pitch closes, so an area saving taken alone is an
  undeclared temperature rise.
- Presenting a lone survivor as the optimum. When only one arrangement cleared
  the constraints the trade was never performed, and a reader needs to be told
  that rather than shown a ranking of one.

## Behavior contract (gate 3)

The candidate validation, the area, thermal-spreading and loss metrics, the
constraint gate, the normalisation and the weighted selection are exercised by
the gate 3 contract test:
scripts/test_q6012_mmic_layout_optimization.py against
scripts/q6012_mmic_layout_optimization_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6012_mmic_layout_optimization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
