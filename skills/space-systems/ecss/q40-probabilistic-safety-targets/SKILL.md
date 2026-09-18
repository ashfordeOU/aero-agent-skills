---
name: q40-probabilistic-safety-targets
description: "Allocate probabilistic safety targets across severity categories for an ECSS-Q-ST-40C clause 6.4.4 and Annex E safety case: refuse a target set that is not stricter as severity rises, split each severity's per-mission limit over the hazards contributing to it by declared weight, aggregate a group as a union of independent contributions rather than a naive sum, and place every predicted probability on the Annex E severity-probability acceptance matrix. Use when a quantitative safety target is set, apportioned to subsystems, or re-argued after a probability update. Trigger: ecss, q-st-40c, ecss-probabilistic-safety-target, severity-category-probability-limit, hazard-probability-allocation, annex-e-acceptance-matrix, per-mission-probability-band."
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
  tags: [ecss, q-st-40c-safety-assurance-scope, q40-probabilistic-safety-targets, ecss-probabilistic-safety-target, severity-category-probability-limit, hazard-probability-allocation, annex-e-acceptance-matrix, per-mission-probability-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Probabilistic Safety Targets (space-systems/ecss/q40-probabilistic-safety-targets)

Use when the task is the quantitative half of ECSS-Q-ST-40C clause 6.4.4 with
the Annex E criteria: a per-mission probability limit has to be fixed for each
severity category, pushed down to the hazards that consume it, and the
resulting predictions argued back up against the limit they were cut from.

## Domain quick reference

- A target set is a shape, not four numbers. The limit has to tighten as
  severity rises, so a set where the catastrophic limit is no stricter than
  the critical one is a tailoring error caught on entry rather than a
  conservative choice.
- A hazard is not graded against the whole target. The severity's limit is
  the budget for every hazard in that category together, so each hazard is
  compared with its allocated share; grading each one against the full figure
  passes a set that busts the target in aggregate.
- Weights carry the engineering judgement. An allocation in proportion to
  declared weights lets a dominant contributor take the larger share openly,
  and the shares still sum back to the target.
- Contributions combine as a union, not a sum. One minus the product of the
  survivals stays below one however many contributors there are; a naive sum
  can exceed one and is then not a probability at all.
- Being inside the budget is not the whole verdict. The Annex E matrix reads
  severity against a probability band, so a catastrophic hazard sitting in an
  occasional band is refused even where a generous programme target would
  have admitted it.
- The band edges are boundaries, not approximations. A probability landing
  exactly on a bound belongs to the band that bound closes, and the equality
  is absorbed by a named tolerance rather than by nudging the bound.

## Workflow

1. Validate the target set: every severity category present, every limit a
   probability in range, and the set strictly stricter as severity rises.
2. Normalise the hazard contributions, refusing an unknown key, a repeated
   hazard identifier, a non-positive weight or a probability outside range.
3. Group the hazards by severity category and allocate that category's limit
   over the group in proportion to the declared weights.
4. Compare each hazard's predicted per-mission probability with its allocated
   budget, absorbing an exact equality with the named tolerance.
5. Place each prediction in a probability band and read the acceptance verdict
   for the band and severity pair off the Annex E matrix.
6. Aggregate each group as a union of independent contributions and compare
   that with the group's own limit.
7. Report the per-hazard budgets, margins, bands and verdicts, the per-group
   roll-up, and the findings: a hazard over budget, a group over its target,
   and any pair the matrix refuses outright.

## Pitfalls

- Grading every hazard against the undivided severity target. Ten hazards
  each at the limit then pass individually and miss the target tenfold.
- Summing contributions. The sum is only an approximation of the union for
  small probabilities and stops being a probability at all once it passes one.
- Treating the acceptance matrix as advisory once the numbers fit. The matrix
  is the second gate; a generous programme target does not license a
  catastrophic hazard in an occasional band.
- Widening a limit to clear an exact equality. The equality is a
  representation question handled inside the comparison; the limit stays as
  the programme set it.
- Allocating with weights that are not declared. An implicit equal split is a
  decision too, and it should be visible in the record as weights of one.

## Behavior contract (gate 3)

The target-set validation and monotonicity rule, the weighted allocation and
its sum-back property, the union aggregation, the probability banding at and
between bounds, the Annex E acceptance lookup, the budget comparison with its
tolerance and the group roll-up are exercised by the gate 3 contract test:
scripts/test_q40_probabilistic_safety_targets.py against
scripts/q40_probabilistic_safety_targets_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q40_probabilistic_safety_targets.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
