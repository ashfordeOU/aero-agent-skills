---
name: q7045-link-to-e-st-32-08
description: "Determine which design allowable a metallic mechanical test data set actually supports, and compute it. Use when test results have to feed an ECSS-E-ST-32-08C allowables derivation or the metallic properties assessment behind it: census the specimens, the distinct heats and the thinnest heat's contribution, judge whether the heats may be pooled at all by measuring the worst heat offset against the within-heat scatter rather than the total, interpolate the one-sided tolerance factor from its tabulated curve, then grant the basis the evidence carries and downgrade with reasons when it does not. Trigger: ecss, q-st-70-45-metallic-mechanical-testing, e-st-32-08c-design-allowables, a-basis-b-basis-derivation, metallic-allowable-heat-pooling, tolerance-limit-factor-interpolation, allowables-basis-downgrade."
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
  tags: [ecss, q-st-70-45-metallic-mechanical-testing, q7045-link-to-e-st-32-08, e-st-32-08c-design-allowables, a-basis-b-basis-derivation, metallic-allowable-heat-pooling, tolerance-limit-factor-interpolation, allowables-basis-downgrade]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Allowables Interface (space-systems/ecss/q7045-link-to-e-st-32-08)

Use when the task is the allowables interface of ECSS-Q-ST-70-45:
deciding whether a set of mechanical test results is enough to derive a
design allowable for ECSS-E-ST-32-08C and the metallic properties
assessment of the 32 series, and what that allowable is.

## Domain quick reference

- The basis is a statement about the population, not about the test. An
  A-basis value is one essentially all of the material is expected to
  exceed, a B-basis value is one most of it is expected to exceed, and a
  specification minimum is asserted by the procurement document rather
  than derived from anything.
- The stronger the statement, the more evidence it costs: more
  specimens, more distinct heats, and a floor on what the thinnest heat
  contributes. That last one is the condition a large data set fails
  most often, because a set of thirty specimens with twenty-eight from
  one melt describes that melt.
- The heats have to be one population before they can be pooled into one
  allowable. A heat sitting far from the rest is a different material
  condition, and absorbing it as scatter both lowers the allowable and
  hides the reason it moved.
- The offset is measured against the scatter *inside* the heats, never
  against the scatter of the whole set. The total scatter contains the
  offset being tested, so an offset heat inflates the yardstick it is
  then measured with, and the further out it sits the more it appears to
  agree.
- A heat that contributes one specimen contributes no scatter. With no
  replicate anywhere, the within-heat yardstick does not exist and the
  pooling question cannot be answered — which is a refusal, not a pass.
- The tolerance factor is tabulated against sample size and interpolated
  between the tabulated points. Reading it off a table keeps the same
  factor on every platform; computing it from an inverse normal makes
  the allowable depend on which library rounded it.
- Below the start of the factor curve there is no factor. A sample that
  small does not support a statistically derived value at all, and
  extrapolating the curve invents one.
- Failing the request is not failing. The output is the strongest basis
  the evidence carries, with the findings that stopped it going higher,
  so the programme can decide between more testing and a lower basis.

## Workflow

1. Census the data set: specimen count, distinct heats, per-heat counts
   and the thinnest heat's contribution.
2. Compare the census against the minima the requested basis carries and
   record each shortfall as its own finding.
3. Compute the within-heat pooled scatter, then the worst heat-mean
   offset in units of it, and compare with the pooling limit.
4. Grant the strongest basis whose preconditions the census meets, at or
   below the one requested; an unpoolable set falls to the specification
   minimum whatever its size.
5. For a granted statistical basis, interpolate the tolerance factor at
   the sample size and return the mean less the factor times the sample
   standard deviation.
6. Report the requested basis, the granted basis, whether it was
   downgraded, the census, the pooling result and every finding.

## Pitfalls

- Judging a heat offset against the scatter of the whole set. It is the
  single failure that lets a genuinely different melt into an allowable,
  and the arithmetic looks right the whole way through.
- Counting specimens and stopping there. Thirty specimens from two heats
  buy less than fifteen from three, and only the per-heat census shows
  it.
- Computing the tolerance factor from an inverse normal at run time. The
  factor then differs in the last digits between platforms, and two
  reviewers recompute two allowables from one data set.
- Extrapolating the factor curve below its first point to rescue a small
  sample. The factor grows sharply there; a straight line through it
  produces a value that is not conservative at all.
- Reporting the mean less one standard deviation as a B-basis value. The
  factor depends on sample size precisely because a small sample knows
  its own scatter badly.
- Treating a downgrade as a failed run. The downgraded basis with its
  findings is the deliverable; silently returning the requested basis
  anyway is what a downstream margin will not survive.

## Behavior contract (gate 3)

The per-heat census, the basis minima, the within-heat pooled scatter,
the offset-against-pooled-scatter pooling test with its no-replicate
refusal, the tabulated tolerance-factor interpolation with its
below-table refusal, the mean-less-factor-times-scatter value and the
basis downgrade with findings are exercised by the gate 3 contract test:
scripts/test_q7045_link_to_e_st_32_08.py against
scripts/q7045_link_to_e_st_32_08_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_link_to_e_st_32_08.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
