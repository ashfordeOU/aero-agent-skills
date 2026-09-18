---
name: q6012-mmic-design-principles
description: "Assess how a monolithic microwave circuit is conceived and refined against the design principles of ECSS-Q-ST-60-12C clause 7.1: turn each specification line into a parametric margin in standard deviations of process spread and a predicted yield, combine those lines into one figure, grade channel temperature, metal current density and RF power density against derated rather than absolute limits, weigh proven library cells against novel structures needing a test vehicle, and require design-rule cleanliness and on-wafer test provision before mask release. Use when an MMIC design concept, iteration or design review package is judged. Trigger: ecss, q-st-60-12c-clause-7-1, mmic-design-principles, mmic-parametric-margin-sigma, mmic-predicted-parametric-yield, mmic-device-derating-limits, mmic-proven-cell-reuse, mmic-on-wafer-test-structures."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-mmic-design-principles, mmic-parametric-margin-sigma, mmic-predicted-parametric-yield, mmic-device-derating-limits, mmic-proven-cell-reuse, mmic-on-wafer-test-structures]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Design Principles (space-systems/ecss/q6012-mmic-design-principles)

Use when the task is the clause 7.1 step of ECSS-Q-ST-60-12C: judging the
way a monolithic microwave circuit has been conceived, not the way it was
simulated. A microwave die is committed to a mask set months before the
first measurement, so the principles are the ones that decide whether the
first wafer is usable, and they are applied while the topology is still
movable.

## Domain quick reference

- A nominal simulation that meets the specification means nothing on its
  own. The design is reproduced across a wafer, a lot and a process
  window, so the quantity that matters is how many standard deviations of
  process spread sit between the nominal prediction and the limit. Three
  sigma on every line is a different design from a nominal that just
  clears it.
- Margins multiply. Each specification line has its own parametric yield,
  and a part is sold against all of them at once, so eight lines at
  ninety-five percent do not make a ninety-five percent part. The
  combined figure is the one the programme plans wafer starts from.
- Derating is not conservatism, it is the design limit. Channel
  temperature, metal current density, RF power density and gate voltage
  are graded against a fraction of the absolute rating, because the
  absolute rating is where the device fails and the derated one is where
  it lives long enough to matter.
- Reuse buys margin nothing else can. A proven library cell carries
  measured silicon behind its model; a novel structure carries a
  simulation. A design that is mostly novel is not wrong, but it owes a
  test vehicle before the flight mask, and the ratio is the cheapest
  early indicator of that debt.
- A design-rule violation is not a style note. The foundry rules are the
  boundary of what its process can reproduce, so an open violation means
  the layout has left the region the models were extracted in.
- On-wafer test structures are the only way a delivered wafer speaks for
  itself. Without process-control monitors on the mask, an out-of-family
  lot can only be diagnosed by destroying parts from it.

## Workflow

1. Take each specification line with its nominal prediction, its limit,
   the sense of that limit and the process sigma, and compute the margin
   in sigma and the fraction of parts it leaves inside the limit.
2. Combine the per-line fractions into one predicted parametric yield and
   compare it with the figure the programme plans against.
3. Grade every device stress against its derated limit, taking the
   programme's derating factor where one is declared and the default
   fraction otherwise.
4. Compute the proven-cell fraction and require a planned test vehicle
   whenever the novel share is above what reuse policy allows.
5. Confirm the layout is design-rule clean and that on-wafer test
   structures are on the mask set.
6. Absorb representation error at every boundary with a named tolerance,
   so a case sitting exactly on a limit is decided by the limit and not
   by the last bit of a division.
7. Report one verdict naming the most severe finding, with the worst
   margin, the predicted yield and the per-stress ratios behind it.

## Pitfalls

- Reviewing the nominal corner and calling it a design. The nominal
  corner is the one corner that will not be manufactured; the spread is
  the design.
- Reporting the best line's yield as the circuit's yield. The circuit
  meets its specification only where every line does at once, and the
  product falls faster than any single line suggests.
- Grading a stress against its absolute rating because the datasheet
  prints that number. The absolute rating is a destruction limit, and a
  design sitting just inside it has no life margin at all.
- Counting novel structures as proven because they simulate well. A
  simulation is the thing being trusted; the test vehicle is what turns
  it into evidence, and it has to be planned before the mask, not after
  the first wafer disappoints.
- Carrying design-rule violations into a review as waivers to be argued
  later. They are the process boundary, and every model in the kit was
  extracted inside it.
- Leaving test structures off to save die area. The area saved is
  recovered once and the diagnostic ability is lost for the life of the
  programme.

## Behavior contract (gate 3)

The parameter validation, margin-in-sigma and yield computation, the
combined-yield product, the derating grading, the proven-cell ratio, the
design-rule and on-wafer test checks, the boundary tolerance and the
precedence of the reported verdict are exercised by the gate 3 contract
test: scripts/test_q6012_mmic_design_principles.py against
scripts/q6012_mmic_design_principles_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_mmic_design_principles.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
