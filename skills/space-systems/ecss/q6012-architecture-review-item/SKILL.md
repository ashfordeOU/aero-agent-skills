---
name: q6012-architecture-review-item
description: "Verify a proposed MMIC block architecture against its electrical design requirements. Use when the review item is the chosen topology of ECSS-Q-ST-60-12C clause 7.3.2: validate every declared block, add the chain gain in decibels, propagate noise figure through the Friis contribution of each stage divided by the gain ahead of it, combine the output third-order intercepts as reciprocals referred to the chain output, sum the DC draw, check the topology realises every required function, then turn each computed figure into a signed margin against its minimum or maximum limit. Trigger: ecss, q-st-60-12c-clause-7-3-2, mmic-architecture-review-item, mmic-block-topology-coverage, mmic-cascaded-noise-figure, mmic-cascaded-output-ip3, mmic-electrical-requirement-margin."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-architecture-review-item, mmic-block-topology-coverage, mmic-cascaded-noise-figure, mmic-cascaded-output-ip3, mmic-electrical-requirement-margin, mmic-dc-power-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Architecture Review Item (space-systems/ecss/q6012-architecture-review-item)

Use when the task is the clause 7.3.2 review item of ECSS-Q-ST-60-12C: a
block structure has been proposed for a microwave monolithic circuit and the
review has to decide whether that topology, as drawn, can meet the electrical
design requirements — before anyone spends a layout cycle on it.

## Domain quick reference

- The architecture item is answered with a cascade, not an opinion. Gain adds
  in decibels, noise figure follows the Friis contribution of each stage
  divided by the gain ahead of it, and the output intercepts add as
  reciprocals once each is referred forward to the chain output.
- The front end owns the noise figure. A four decibel rise in the second
  stage moves a chain with fifteen decibels of gain ahead of it by a fraction
  of a decibel; the same rise in the first stage moves it almost one for one.
  A topology that puts the lossy element before the low-noise block has
  already lost the requirement, whatever the later stages do.
- Linearity works the other way round. Each stage's output intercept is
  referred to the chain output through the gain that follows it, so the last
  high-power stage usually sets the chain intercept and the reciprocal sum
  always lands below the weakest referred contributor.
- A block structure has to be complete as well as adequate. A chain that
  meets every number but has no output matching block is not a chain, so the
  declared functions are checked against the required ones and a block nobody
  asked for is reported rather than quietly accepted.
- DC draw is an electrical requirement like any other. It sums over the
  blocks, it competes with the gain and linearity the same blocks buy, and
  the architecture is where that trade is still cheap to change.
- A margin carries a sense. Gain and intercept clear a minimum, noise figure
  and DC power clear a maximum, and reporting a bare difference without the
  sense turns a compliant design and a failing one into the same number.

## Workflow

1. Validate every declared block: a name, a function label, a gain in dB, a
   non-negative noise figure, an output intercept and a non-negative DC draw.
   Refuse a duplicate block name and an empty chain.
2. Sum the gains in decibels to get the small-signal chain gain.
3. Walk the chain front to back accumulating the Friis noise factor, dividing
   each stage's excess factor by the linear gain accumulated ahead of it, and
   convert the total back to decibels.
4. Refer each stage's output intercept forward through the linear gain of the
   stages after it, sum the reciprocals, and invert to get the chain output
   intercept.
5. Sum the DC draw over the blocks to close the electrical figure set.
6. Compare the declared block functions with the required ones; name the
   functions no block realises and the functions no requirement asked for.
7. Turn each computed figure into a signed margin against its minimum or
   maximum limit, absorbing floating-point representation error at the
   boundary with a named tolerance, and report every shortfall as a finding.

## Pitfalls

- Averaging the block noise figures. Noise figure does not average; a chain
  whose stages read 1.5, 4.0 and 1.0 dB does not have a 2.2 dB noise figure,
  and the Friis weighting by preceding gain is the whole content of the item.
- Adding the output intercepts, or taking the minimum. Two identical stages in
  cascade lose three decibels of output intercept relative to one, and a chain
  can sit below its own weakest stage once the gain referral is applied.
- Referring the intercepts to the input while comparing against an output
  requirement. Both conventions are in use; mixing them shifts the answer by
  the full chain gain and the error is invisible in a single-stage check.
- Grading a topology on numbers alone. A chain meeting gain, noise and
  linearity with no output matching block cannot be built, so the function
  coverage check is part of the verdict, not a formality beside it.
- Reporting a bare margin without its sense. Minus two decibels of noise
  figure margin and minus two decibels of gain margin are both shortfalls, but
  a signed difference with no direction cannot say which way either one runs.
- Widening a limit to make an exact-equality case pass. An equality at the
  limit is a representation question — log conversions round differently
  across platforms — handled by the tolerance inside the comparison; the
  required value stays as specified.

## Behavior contract (gate 3)

The block validation, decibel conversions, cascaded gain, Friis noise figure,
referred output intercept, DC summation, topology coverage and signed margin
verdict are exercised by the gate 3 contract test:
scripts/test_q6012_architecture_review_item.py against
scripts/q6012_architecture_review_item_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_architecture_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
