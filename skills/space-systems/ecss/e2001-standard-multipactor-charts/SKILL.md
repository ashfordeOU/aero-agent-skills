---
name: e2001-standard-multipactor-charts
description: "Use when compute a first-level multipactor threshold from the tabulated susceptibility-charts of ECSS-E-ST-20-01C clause 5.3.3.4: form the frequency-gap-product of each multipactor-critical gap, select the chart tabulated for that electrode base-material and surface-treatment, interpolate the parallel-plate threshold-voltage logarithmically between tabulated points, refuse any read-out outside the chart validity-range and escalate that gap to a dedicated second-level-analysis instead of extrapolating, convert peak-operating-power and line-impedance into the equivalent gap-voltage, and grade the resulting multipactor-margin in decibel against the first-level requirement. Trigger: ecss, e-st-20-electrical-scope, multipactor-susceptibility-chart, frequency-gap-product, multipactor-threshold-voltage, first-level-multipactor-analysis, chart-validity-range, parallel-plate-breakdown-voltage, multipactor-margin-decibel."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-standard-multipactor-charts, multipactor-susceptibility-chart, frequency-gap-product, multipactor-threshold-voltage, first-level-multipactor-analysis, chart-validity-range, parallel-plate-breakdown-voltage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Standard Multipactor Charts (space-systems/ecss/e2001-standard-multipactor-charts)

Use when the task is the chart read-out of ECSS-E-ST-20-01C clause
5.3.3.4 -- taking a multipactor threshold for a gap from the
tabulated parallel-plate susceptibility-charts during a first-level
analysis, instead of solving the electron dynamics of that geometry.

## Domain quick reference

- A first-level analysis is a screening step: it treats every critical
  gap as an equivalent parallel-plate region, reads a threshold off a
  tabulated chart, and asks whether the operating voltage sits far
  enough below it. Geometry detail, field shaping and multi-surface
  effects are deliberately outside the model, which is why a gap that
  passes screening comfortably is closed and a gap that does not moves
  to a dedicated analysis or to a seeded multipactor-test.
- Charts are tabulated against the frequency-gap-product -- operating
  frequency times electrode separation, in gigahertz-millimetre -- and
  are specific to the emitting surface: the electrode base-material
  and its surface-treatment. Silver-plated, alodine-conversion-coated
  and bare aluminium-alloy each have their own table, because the
  threshold follows the secondary-electron-yield of the outermost
  layer.
- Each table entry pairs a frequency-gap-product with a threshold
  voltage. Between entries the charts behave like a power law, so the
  read-out is interpolated logarithmically on both axes; interpolating
  on linear axes across a decade under-reads the threshold and quietly
  flatters the margin.
- Every chart has a validity-range, the span it was tabulated over.
  Outside that span there is no first-level answer at all. A gap whose
  frequency-gap-product falls beyond either end is escalated to a
  dedicated analysis -- that is an outcome of screening, not a failure
  of the gap and not an invitation to extrapolate the last two points.
- The quantity compared against the chart is the peak voltage across
  the gap. Where only power is known, the matched-line relation
  converts peak-operating-power and the local impedance into that
  voltage. The margin is then twenty times the base-ten logarithm of
  the threshold-to-operating voltage ratio, in decibel, and it is
  graded against the first-level requirement of the programme.

## Workflow

1. For each multipactor-critical gap, form the frequency-gap-product
   from the operating frequency and the derived worst-case separation.
2. Select the tabulated chart whose base-material and
   surface-treatment match the electrode surface. A surface with no
   tabulated chart has no first-level threshold; say so rather than
   borrowing the table of a different metal.
3. Validate the table before reading it: at least two points, strictly
   increasing frequency-gap-product, strictly positive voltages.
4. Check the frequency-gap-product against the chart validity-range.
   Beyond either end, return a chart-range-exceeded verdict and mark
   the gap for a dedicated second-level-analysis.
5. Inside the range, interpolate the threshold-voltage logarithmically
   between the two bracketing points.
6. Establish the operating voltage, either directly or from
   peak-operating-power and line-impedance through the matched-line
   relation.
7. Compute the margin in decibel and grade it against the first-level
   requirement; a margin sitting exactly on the requirement is
   compliant.
8. Summarise the campaign: which gaps first level closed, which failed
   on margin, which escalated beyond the charts, and the worst margin
   carried forward.

## Pitfalls

- Extrapolating the chart past its last tabulated point because the
  gap is only slightly outside the range -- the curve shape there is
  not knowledge the table carries, and the answer is an escalation.
- Interpolating linearly between two points that span a decade, which
  under-reads the threshold and overstates the margin.
- Reading the chart of a differently-treated surface because the base
  metal matches; the threshold tracks the outer layer, not the bulk.
- Entering the chart with the drawing nominal separation instead of
  the worst-case separation derived from manufacturing accuracy and
  in-service stability.
- Comparing an average or root-mean-square voltage against a chart
  plotted for peak voltage, which inflates the margin by a fixed and
  invisible factor.
- Reporting a chart-range-exceeded gap as a pass because no failing
  margin was produced; no margin was produced at all.

## Behavior contract (gate 3)

The frequency-gap-product, chart validation, surface-based chart
selection, logarithmic threshold interpolation, validity-range
refusal, matched-line voltage conversion and decibel margin grading
are exercised by the gate 3 contract test:
scripts/test_e2001_standard_multipactor_charts.py against
scripts/e2001_standard_multipactor_charts_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_standard_multipactor_charts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
