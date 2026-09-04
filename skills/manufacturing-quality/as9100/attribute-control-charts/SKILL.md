---
name: attribute-control-charts
description: "Use when you must build attribute control charts for conformance and defect count data: the p-chart for fraction nonconforming of subgroups with constant sample size, the np-chart for count nonconforming, the c-chart for defect counts per constant inspection area, and the u-chart for defect counts per unit with variable inspection area. Computes the grand average, the 3-sigma control limits from the binomial or Poisson normal-approximation standard error, floors the lower limit at zero, flags the subgroups whose statistic falls outside the limits, and returns the in-control or out-of-control stability verdict. Produces the per-chart central line, control limits, flagged subgroup list, and the verdict that gates the attribute process review. Trigger: p-chart, np-chart, c-chart, u-chart, fraction-nonconforming, defects-per-unit, count-data, conformance-data, attribute-chart-limits."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: as9100
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [attribute-control-charts, p-chart, np-chart, c-chart, u-chart, fraction-nonconforming, defects-per-unit]
  version: 0.1.0
  author: AeroSkills
---

# Attribute Control Charts (manufacturing-quality/as9100/attribute-control-charts)

Use when the task is monitoring the conformance and defect count side of
an aerospace production process: subgroup data that classify units as
conforming or nonconforming, or count defects per unit or per
inspection area, feeds the p, np, c, and u attribute control charts.
This leaf implements all four charts in pure Python, stdlib only: the
p-chart for fraction nonconforming at constant sample size, the np-chart
for count nonconforming, the c-chart for defect counts per constant
inspection area, and the u-chart for defect counts per unit with
variable inspection area. It pairs with the variable-data charting leaf
in the same as9100 pack for measured key characteristics, and with the
measurement-system study scope judgment that decides whether attribute
or variable data will be collected at all.

Does NOT do: variable-data chart methods (sibling
statistical-process-control leaf), sequential monitoring of variable
data for small mean shifts (sibling cusum-ewma-monitoring leaf), or
measurement-system study planning and scope judgment (sibling
measurement-systems-analysis leaf). Repo-wide ownership of p-chart,
np-chart, c-chart, u-chart, fraction nonconforming charting, and
defects-per-unit charting lives here.

## Domain quick reference

Attribute data come in two forms: conformance counts (units judged
conforming or nonconforming, modeled by the binomial distribution) and
defect counts (defects found per unit or per area, modeled by the
Poisson distribution). The 3-sigma control limits use the normal
approximation of each model, with the module constant SIGMA_FACTOR =
3.0.

- p-chart, constant subgroup sample size n: pbar = sum(x_i) / (k * n)
  over k subgroups, sigma_p = sqrt(pbar * (1 - pbar) / n), UCL/LCL =
  pbar +/- 3 * sigma_p with LCL floored at 0. Flag subgroup i when its
  fraction x_i / n falls outside [LCL, UCL].
- np-chart, same constant n: npbar = n * pbar and UCL/LCL = n * (pbar
  +/- 3 * sigma_p) with LCL floored at 0, so the np limits are exactly
  n times the p limits. Flag subgroup i when the raw count x_i falls
  outside [LCL, UCL], which matches the p-chart fraction flagging.
- c-chart, constant inspection area per subgroup: cbar = mean(x_i),
  sigma_c = sqrt(cbar), UCL/LCL = cbar +/- 3 * sigma_c with LCL floored
  at 0. Flag subgroup i when the raw defect count x_i falls outside
  [LCL, UCL].
- u-chart, variable area a_i per subgroup: ubar = sum(x_i) / sum(a_i),
  per-subgroup UCL_i/LCL_i = ubar +/- 3 * sqrt(ubar / a_i) with LCL
  floored at 0, so the limits vary with the subgroup area. Flag
  subgroup i when the rate x_i / a_i falls outside [LCL_i, UCL_i]. With
  equal areas the limits collapse to the constant c-chart style limits.
- Verdict: attribute_verdict flags any subgroup, returning
  "out-of-control" when at least one subgroup statistic lies outside
  its limits, else "in-control".
- AS9100 clause 8.5.1 frames production process control; attribute
  control charts are the standard aerospace evidence that a conformance
  or defect-count process stays in statistical control, paraphrased
  here without clause text.

## Workflow

1. Classify the attribute data: fraction or count nonconforming at
   constant subgroup size (p or np), defect counts per constant
   inspection area (c), or defect counts over variable areas (u).
2. Run p_chart(nonconforming_counts, sample_size) for the fraction
   nonconforming, with limits from the binomial normal approximation.
3. Run np_chart(nonconforming_counts, sample_size) when the raw count
   nonconforming is the charted statistic; the center line and limits
   are the p-chart values scaled by the sample size.
4. Run c_chart(defect_counts) for defect counts per constant inspection
   area, with Poisson normal-approximation limits.
5. Run u_chart(defect_counts, areas) for defects per unit over variable
   areas; read the per-subgroup UCLs and LCLs arrays.
6. Read flagged_subgroups and verdict from each chart; an
   out-of-control verdict sends the flagged subgroups to the process
   review before the process is released.
7. Validate inputs first: empty data, non-positive sample size or
   area, negative counts, a count above the sample size, and a
   u-chart length mismatch raise ValueError.
8. Confirm the deterministic checks with the contract test
   scripts/test_attribute_control_charts.py.

## Worked example

p/np fixture: 20 subgroups of n = 200, total 90 nonconforming, subgroup
index 12 carrying 14. Module outputs (p_chart, np_chart):

- pbar = 90 / (20 * 200) = 0.0225; sigma_p = sqrt(0.0225 * 0.9775 /
  200) = 0.01049.
- UCL_p = 0.0225 + 3 * 0.01049 = 0.05396 (spec bound 0.0540 within
  1e-4); LCL_p = -0.00896 floored to exactly 0.0.
- Subgroup 12 fraction 14 / 200 = 0.0700 > 0.05396, so
  flagged_subgroups = [12] and the verdict is out-of-control.
- np_chart: npbar = 4.5, UCL_np = 200 * 0.05396 = 10.792, LCL_np = 0.0;
  raw count 14 > 10.792 flags subgroup 12 again.

c fixture: 25 units, total 83 defects, unit index 12 carrying 11.
Module outputs (c_chart):

- cbar = 83 / 25 = 3.32; sigma_c = sqrt(3.32) = 1.8221.
- UCL_c = 3.32 + 3 * 1.8221 = 8.786 (spec bound 8.786 within 1e-3);
  LCL_c = 3.32 - 5.466 = -2.146 floored to exactly 0.0.
- Unit 12 raw 11 > 8.786, so flagged_subgroups = [12] and the verdict
  is out-of-control.

u fixture: 9 subgroups, counts [2, 5, 3, 4, 1, 6, 2, 3, 9] over areas
[1.0, 1.5, 1.0, 2.0, 1.0, 1.5, 1.0, 1.0, 1.0]. Module outputs
(u_chart):

- ubar = 35 / 11.0 = 3.1818.
- Subgroup 5 (rate 6 / 1.5 = 4.0): UCL_5 = 3.1818 + 3 * sqrt(3.1818 /
  1.5) = 7.5511, not flagged.
- Subgroup 8 (rate 9 / 1.0 = 9.0): UCL_8 = 3.1818 + 3 * sqrt(3.1818) =
  8.5331, so 9.0 lies above the limit; flagged_subgroups = [8], the
  only flag, and the verdict is out-of-control.

## Verification

- Confirm p_chart on the p fixture returns pbar 0.0225, UCL 0.05396
  (within 1e-4 of 0.0540), LCL exactly 0.0, flagged_subgroups [12].
- Confirm np limits equal n times the p limits exactly, and np raw
  count flagging equals p fraction flagging.
- Confirm c_chart returns UCL 8.786 (within 1e-3) and LCL exactly 0.0;
  a single defect in one of 25 units gives UCL 0.64 < 1 and flags that
  unit.
- Confirm u_chart with unit areas reduces to the constant c-chart style
  limits ubar +/- 3 * sqrt(ubar / 1.0), and a benign low-defect-density
  variable-area dataset stays in-control.
- Confirm an all-conforming p fixture (all zero counts) and a zero
  defect-count fixture give center line 0, limits 0, and verdict
  in-control.
- Confirm an all-but-one-conforming p fixture with small pbar floors
  LCL to exactly 0.0.
- Confirm empty data, sample_size <= 0, count < 0, count > sample_size,
  negative defect counts, area <= 0, and u-chart length mismatch all
  raise ValueError.
- Confirm identical inputs produce identical outputs (determinism).
- Run the contract test offline: python3
  scripts/test_attribute_control_charts.py (31 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/statistical-process-control: the
  variable-data charting leaf for measured key characteristics, the
  complement to count and conformance charting.
- manufacturing-quality/as9100/cusum-ewma-monitoring: sequential
  variable-data monitoring for small mean shifts, complementary to the
  point-wise attribute verdicts here.
- manufacturing-quality/as9100/measurement-systems-analysis: the study
  scope judgment that decides between attribute and variable data
  collection before charting.

## Pitfalls

- Charting the wrong statistic for the chart type: the np-chart flags
  raw counts x_i while the p-chart flags fractions x_i / n — charting
  raw counts on the p scale (or vice versa) misplaces subgroups against
  limits that differ by the sample-size factor n.
- Using the c-chart where the inspection area varies: the c-chart
  assumes a constant area per subgroup, and only the u-chart builds the
  per-subgroup limits ubar +/- 3 * sqrt(ubar / a_i) that a variable-area
  process needs.
- Treating the floored LCL as a real lower limit: computed limits below
  zero (small-pbar and low-defect-count fixtures) are floored to exactly
  0.0, so a zero LCL carries no information about low-side excursions.
- Releasing the process while flagged subgroups are unresolved: any
  subgroup statistic outside its limits returns an out-of-control
  verdict, and the flagged subgroups are the input to the process review
  before release.
- Skipping input validation: empty data, sample_size or area <= 0,
  negative counts, a count above the sample size, and a u-chart
  length mismatch all raise ValueError rather than producing a plausible
  but wrong chart.
- Reading the normal-approximation limits as exact spec bounds: the
  3-sigma UCL/LCL come from the binomial or Poisson normal approximation
  (SIGMA_FACTOR = 3.0), and worked-example values carry explicit
  tolerances rather than exact agreement with the arithmetic.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_attribute_control_charts.py

The test covers the p-chart contract (worked-example pbar 0.0225,
sigma_p 0.01049, UCL 0.0540 within 1e-4, LCL floor at exactly 0.0,
flagged subgroup 12), the np-chart contract (npbar 4.5, UCL 10.79
within 1e-2, np limits exactly n times the p limits, flagging parity
with the p-chart), the c-chart contract (cbar 3.32, UCL 8.786 within
1e-3, single-defect flagging below UCL 1.0), the u-chart contract
(ubar 3.1818, variable per-subgroup limits 7.5511 and 8.5331 within
1e-4, only flag at index 8, equal-area reduction to constant c-chart
style limits, benign in-control variable-area fixture), the all-zero
and small-pbar LCL floor cases, ValueError rejection of every
non-physical input, exact dict key sets, the verdict helper, and
determinism.

## Compliance

- Standards referenced, not reproduced: AS9100 (standards-map id
  as9100) is available from SAE International; the attribute control
  chart relations above are standard statistical quality control
  methodology, summary-only, and no standard text is reproduced.
- compliance: STANDARDS-REF, gated: false.
