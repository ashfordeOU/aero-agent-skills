---
name: e50-error-rates
description: "Compute the error-rate budget of a ground network data path against ECSS-E-ST-50C clause 5.8.4, which asks the ground figure to sit well under the rates carried by the space link and by the space network rather than under an absolute number of its own. Convert a bit error rate into a block or frame error rate, compose the segments of a path into one end-to-end figure, and invert that composition into the rate each hop has to hold. Report errored bits, errored blocks and errored seconds over a pass, and the headroom as a ratio and in decibels. Use when apportioning an error budget across ground segments, or grading a measured path against one. Trigger: ecss, e-st-50-ground-network, ground-network-error-rate, bit-error-rate-to-frame-error-rate, end-to-end-error-budget-apportionment, errored-seconds-per-pass, ground-segment-error-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.8.4
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-ground-network, e50-error-rates, ground-network-error-rate, bit-error-rate-to-frame-error-rate, end-to-end-error-budget-apportionment, errored-seconds-per-pass, ground-segment-error-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Error Rates (space-systems/ecss/e50-error-rates)

Use when a ground network path carries a stated error-rate requirement per
ECSS-E-ST-50C clause 5.8.4, which asks the ground figure to sit well under
the rates carried by the space link and by the space network — turning those
into a budget the segments of the path can be held to, and turning a
measured path back into a verdict against them.

## Domain quick reference

- An error rate without its unit is not a requirement. A rate per bit and
  a rate per frame are different numbers by four orders of magnitude on a
  normal transfer frame, and a document that quotes one and a test report
  that measures the other agree only by accident.
- The conversion between them is not multiplication. The probability a
  block carries an error is one minus the probability every bit survives,
  and the linear estimate a reviewer reaches for is an upper bound that
  stops being usable as soon as the product of rate and length approaches
  one.
- A path is a chain, and the chain composes the same way. End to end is
  one minus the product of the per-segment survival probabilities, which
  for small rates is close to the sum and for large ones is a long way
  under it.
- The useful inverse is apportionment. A network is procured segment by
  segment, so the number each supplier can be held to is the per-segment
  rate that composes to the end-to-end target, not the target itself.
- Headroom belongs in the report next to the verdict. A path that meets
  its requirement with nothing to spare passes today and fails on the
  first degraded hop, and the factor it holds says which of those it is.
- Volume figures are what an operator compares with a log. Errored bits
  and errored seconds over a pass make an abstract rate checkable against
  what the station actually recorded.

## Workflow

1. State the requirement with its unit and the granularity it is written
   at, and state the measured or predicted rate of every segment on the
   path in the same unit.
2. Compose the segments into one end-to-end rate. Do not sum them; the
   sum is an upper bound that overstates a lossy path.
3. Convert to the granularity the requirement is written at before
   comparing. A frame-level requirement against a bit-level measurement
   is not a comparison.
4. Grade against the requirement with a relative tolerance, and grade
   again against the requirement divided by the headroom factor the
   project asks for, so a path that only just passes is reported as
   only just passing rather than as compliant.
5. Grade the path against the clause's own comparison as well: the
   composed ground-network rate beside the rate the space link carries
   and the rate the space network carries, all three at one granularity.
   The clause asks the ground figure to sit well under both and does not
   say by how much, so state the factor the project treats as clearly
   lower and report the ratio to each.
6. Where the path does not reach the target, compute the per-segment
   allocation that would, and name the worst segment so the effort goes
   where the budget is being spent.
7. Report the headroom as a ratio and in decibels, and report it as
   undefined rather than infinite where a path shows no errors at all.
8. Add the volume figures for the pass — errored bits, errored blocks,
   errored seconds — so the prediction can be reconciled against the
   station log.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.8.4a | 5 |

## Pitfalls

- Multiplying a bit error rate by a frame length and calling it the frame
  error rate. It is a bound, not the value, and it can exceed one.
- Summing segment error rates. The sum overstates the path, and for a
  chain of degraded hops it can exceed one and stop being a probability
  at all.
- Apportioning an end-to-end target by dividing it by the segment count.
  Equal division is the right idea in the wrong algebra; the composition
  is multiplicative in the survival probability.
- Reporting an error-free measurement as infinite headroom. It means the
  observation window was too short to see an error, and a finite margin
  figure there is an invention.
- Deciding compliance with a bare inequality against the requirement. A
  path sized to land exactly on its bound is decided by rounding, and two
  build hosts can disagree.
- Quoting a rate with no observation window. A rate measured over one
  pass and a rate measured over a month are different claims.

## Behavior contract (gate 3)

Probability, bit-count and headroom-factor validation, the block-rate and
chain compositions, the apportionment inverse and its round trip, the
undefined headroom of an error-free path, the verdict bands at the exact
requirement and at the exact headroom bound, and the per-pass volume
figures are exercised by the gate 3 contract test:
scripts/test_e50_error_rates.py against
scripts/e50_error_rates_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_error_rates.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
