---
name: q7045-statistical-treatment
description: "Derive the A-basis or B-basis value a set of mechanical test results actually supports, and hand it to the allowables process with its findings. Use when results from a test campaign under ECSS-Q-ST-70-45 have to become a design number: screen one extreme result with the maximum normed residual against its tabulated critical value, report the scatter as a coefficient of variation, compute the one-sided normal tolerance factor for the coverage and confidence the basis demands, take mean less factor times sample deviation, refuse a basis drawn from too few results, and compare against the design allowable already in use. Trigger: ecss, q-st-70-45-mechanical-testing, mechanical-test-basis-value-derivation, mechanical-test-tolerance-factor, mechanical-test-outlier-screening, mechanical-test-scatter-coefficient-of-variation, mechanical-test-design-allowable-support."
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
  tags: [ecss, q-st-70-45-mechanical-testing, q7045-statistical-treatment, mechanical-test-basis-value-derivation, mechanical-test-tolerance-factor, mechanical-test-outlier-screening, mechanical-test-scatter-coefficient-of-variation, mechanical-test-design-allowable-support]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing — Statistical Treatment (space-systems/ecss/q7045-statistical-treatment)

Use when the task is the statistical step between a set of mechanical
test results and the allowables process under ECSS-Q-ST-70-45: several
specimens have been tested, and the question is what single number the
design is entitled to use, with what coverage and what confidence.

## Domain quick reference

- A basis value is a statement about the population, not about the
  sample. An A-basis covers ninety-nine percent of the population at
  ninety-five percent confidence, a B-basis ninety percent at the same
  confidence, and both are lower one-sided limits.
- The tolerance factor is the whole of the small-sample penalty. It
  falls steeply with sample size, so five specimens produce a value
  driven mostly by how few there were, which is why each basis carries a
  minimum sample size of its own.
- A factor read off a printed table carries the table's rounding. The
  exact factor is defined by the sampling distribution of the mean and
  the standard deviation together, and solving that numerically removes
  an interpolation error from the middle of an allowable.
- Scatter and level are separate questions. A sample can sit high on
  average and still be unusable because its coefficient of variation is
  wide; the basis value falls as the scatter grows, which is exactly
  what the factor times the deviation expresses.
- An extreme result is a question, not a verdict. A normed residual past
  its critical value says the result deserves a cause; deleting it
  because it is inconvenient moves the allowable up without evidence,
  and keeping a known bad test moves it down without cause.
- The critical-value table covers the sample sizes it covers. A sample
  outside it is refused rather than screened against an extrapolated
  limit that nobody tabulated.

## Workflow

1. Screen the sample: form each normed residual, take the largest, and
   compare it with the tabulated critical value for that sample size,
   refusing a size the table does not cover.
2. Report a flagged result with its position and value, and set it aside
   only when the caller says a cause was established.
3. Compute the sample size, mean, sample standard deviation and
   coefficient of variation from the results being kept.
4. Grade the scatter against the limit the property allows, absorbing an
   exact equality at the limit as representation error.
5. Solve the one-sided normal tolerance factor for the coverage and
   confidence the basis demands, at the sample size in hand.
6. Take the basis value as the mean less the factor times the sample
   standard deviation, and mark the sample insufficient when it falls
   under the floor the basis owes.
7. Compare the value obtained with the design allowable already in use
   and report the margin, raising a finding when the allowable sits
   above what the sample supports.

## Pitfalls

- Quoting a mean as an allowable. The mean is exceeded by half the
  population; the whole point of the basis value is the distance below
  it that coverage and confidence buy.
- Reading the tolerance factor for the wrong sample size after dropping
  a result. Dropping one specimen changes the factor as well as the
  mean and the deviation, and all three move the value.
- Deleting an extreme result without a cause. It is the fastest way to
  raise an allowable and the hardest to defend at a review.
- Treating a small sample as merely approximate. Below the floor for the
  basis, the value is not a rough allowable, it is not an allowable.
- Reporting a basis value without its scatter. Two samples with the same
  basis value and very different coefficients of variation behave
  differently as soon as one more specimen is added.

## Behavior contract (gate 3)

The sample statistics, normed-residual screening against the tabulated
critical values, numerical solution of the one-sided tolerance factor,
basis-value arithmetic, minimum-sample floors, scatter grading and the
design-allowable comparison are exercised by the gate 3 contract test:
scripts/test_q7045_statistical_treatment.py against
scripts/q7045_statistical_treatment_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_statistical_treatment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
