# Wave-35 leaf spec: attribute-control-charts (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/attribute-control-charts/
- Pack: as9100. Closest siblings: statistical-process-control
  (VARIABLES SPC: X-bar and R charts with A2/D3/D4, d2 sigma
  estimate, Cp/Cpk capability, Western Electric rules - no count
  data, no p/np/c/u charts), cusum-ewma-monitoring (variables
  CUSUM/EWMA monitoring), measurement-systems-analysis (gage R and R
  and the variable-versus-attribute STUDY SCOPE judgment, no control
  chart math). Repo-wide grep proves ZERO owners for p-chart,
  np-chart, c-chart, u-chart, fraction nonconforming charting,
  defects-per-unit charting.
- Standards id: as9100 (reference-only; sibling SPC convention).
  Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Build the four attribute (count and conformance) control charts for
aerospace production quality data: the p-chart for the fraction
nonconforming of subgroups with constant sample size, the np-chart
for the count nonconforming, the c-chart for defect counts per
constant inspection area, and the u-chart for defect counts per unit
with variable inspection area. For each chart compute the grand
average, the 3-sigma control limits from the binomial or Poisson
normal-approximation standard error, floor the lower limit at zero,
flag the subgroups whose statistic falls outside the limits, and
return the stability verdict for the attribute process. Produces the
per-chart central line, control limits, flagged subgroups, and the
in-control or out-of-control verdict that gate the attribute process
review.

Does NOT do: X-bar/R variables charts, d2/A2/D3/D4 constants, Cp/Cpk
capability indices, Western Electric run rules (statistical-process-
control); variables CUSUM/EWMA (cusum-ewma-monitoring); gage R and R
studies and %GRR (measurement-systems-analysis).

## Model (implement exactly)

Module constants:
- SIGMA_FACTOR = 3.0 (3-sigma control limits).

Conventions: input data are raw counts; every chart function takes
the subgroup statistics and derives its own grand average. The
p-chart assumes a constant subgroup sample size n (np-chart shares
the same underlying p-bar). The c-chart assumes each subgroup is a
constant inspection area. The u-chart allows variable area/units per
subgroup, so its limits vary per subgroup.

Functions (pure stdlib):
- p_chart(nonconforming_counts, sample_size) -> dict {pbar,
  sigma_p, UCL, LCL, flagged_subgroups, verdict}: pbar =
  sum(counts) / (len * n); sigma_p = sqrt(pbar (1 - pbar) / n);
  UCL/LCL = pbar +/- 3 sigma_p with LCL floored at 0;
  flagged_subgroups = indices i where counts[i]/n outside
  [LCL, UCL]. ValueErrors: empty counts; sample_size <= 0; any
  count < 0 or count > sample_size.
- np_chart(nonconforming_counts, sample_size) -> dict {npbar, UCL,
  LCL, flagged_subgroups, verdict}: npbar = pbar * n with pbar from
  p_chart internals; UCL/LCL = n * (pbar +/- 3 sigma_p), LCL
  floored at 0; flag on the raw count outside [LCL, UCL]. Same
  ValueErrors as p_chart.
- c_chart(defect_counts) -> dict {cbar, sigma_c, UCL, LCL,
  flagged_subgroups, verdict}: cbar = mean(counts); sigma_c =
  sqrt(cbar); UCL/LCL = cbar +/- 3 sigma_c with LCL floored at 0;
  flag raw counts outside. ValueErrors: empty; negative counts.
- u_chart(defect_counts, areas) -> dict {ubar, UCLs, LCLs,
  flagged_subgroups, verdict}: ubar = sum(counts)/sum(areas);
  per-subgroup UCL_i/LCL_i = ubar +/- 3 sqrt(ubar / area_i), LCL
  floored at 0; flag where count_i/area_i outside. ValueErrors:
  empty; length mismatch; negative counts; area <= 0.
- attribute_verdict(any_flags) -> "in-control" when no flags else
  "out-of-control" (helper returning the shared verdict string).

Identity to test: np limits equal n times the p limits; with LCL
below zero the p-chart lower limit floors to exactly 0.0; the u-chart
with equal areas reduces to constant limits ubar +/- 3 sqrt(ubar/n).

## Worked example

p/np fixture: 20 subgroups of n = 200 with total nonconforming 90
(sum of counts), with subgroup 12 carrying 14 nonconforming.
Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- pbar = 90 / (20 * 200) = 0.0225.
- sigma_p = sqrt(0.0225 * 0.9775 / 200) = 0.01049.
- UCL_p = 0.0225 + 3 * 0.01049 = 0.05396 (0.0540); LCL_p = 0.0225 -
  3 * 0.01049 = -0.00896 -> floored 0.0.
- Subgroup 12 fraction 14/200 = 0.0700 > 0.0540 -> flagged.
- np: npbar = 4.5; UCL_np = 200 * 0.05396 = 10.79; LCL_np = 0.0;
  subgroup 12 raw 14 > 10.79 -> flagged.

c fixture: 25 units with total defects 83, unit 12 carrying 11.
- cbar = 3.32; sigma_c = sqrt(3.32) = 1.8221.
- UCL_c = 3.32 + 3 * 1.8221 = 8.786; LCL_c = 3.32 - 5.466 =
  -2.146 -> floored 0.0.
- Unit 12 raw 11 > 8.786 -> flagged.

u fixture: 9 subgroups with counts [2, 5, 3, 4, 1, 6, 2, 3, 9] over
areas [1.0, 1.5, 1.0, 2.0, 1.0, 1.5, 1.0, 1.0, 1.0]: total 35 defects
over 11.0 area units.
- ubar = 35 / 11.0 = 3.1818.
- Subgroup 5 (count 6 over area 1.5): rate 4.0; UCL_5 = 3.1818 +
  3 sqrt(3.1818/1.5) = 3.1818 + 3 * 1.4564 = 7.5511 -> not flagged.
- Subgroup 8 (count 9 over area 1.0): rate 9.0; UCL_8 = 3.1818 + 3 *
  sqrt(3.1818) = 3.1818 + 5.3513 = 8.5331 -> 9.0 above the limit,
  flagged (the only flag in the u fixture).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty counts; sample_size <= 0; count < 0; count >
  sample_size; negative defect count; area <= 0; u-chart length
  mismatch.
- p-chart: worked example limits 0.0540 / 0.0 within 1e-4; flagged
  subgroup exactly [12]; all-conforming fixture (all zero counts) ->
  pbar 0, limits 0, verdict in-control.
- np-chart: np limits equal n * p limits (10.79 / 0.0); raw count
  flagging matches p-chart fraction flagging.
- c-chart: worked example UCL 8.786 within 1e-3; a 25-unit zero-
  defect fixture -> cbar 0, limits 0; single defect in one unit
  flags nothing when UCL >= 1? no: cbar = 1/25 = 0.04, UCL = 0.04 +
  3*sqrt(0.04) = 0.04 + 0.6 = 0.64 < 1 -> the unit with 1 defect IS
  flagged; assert that behavior.
- u-chart: equal areas -> constant limits equal to c-chart style
  ubar +/- 3 sqrt(ubar/n); variable-area fixture above -> no flags,
  in-control.
- LCL floor: an all-but-one-conforming p fixture with small pbar
  gives LCL exactly 0.0.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-attribute-control-charts.yaml)

Query 1 (copy verbatim):
  "build the attribute control charts p chart np chart c chart and u chart for fraction nonconforming and defects per unit"
  intent: "manufacturing-quality; attribute p np c u control charts for conformance data"
  expected_skill: "manufacturing-quality/as9100/attribute-control-charts"
Query 2 (copy verbatim):
  "compute the 3 sigma control limits for count data with the binomial and Poisson normal approximation in aerospace production"
  intent: "manufacturing-quality; binomial and Poisson 3-sigma limits for attribute charts"
  expected_skill: "manufacturing-quality/as9100/attribute-control-charts"
Task ids: w35-attribute-control-charts-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must build attribute control
charts for conformance and defect count data:" and include the
outputs in the Claim. First tag: attribute-control-charts.
Additional tags ONLY: p-chart, np-chart, c-chart, u-chart,
fraction-nonconforming, defects-per-unit. NEVER single generic words
(attribute, chart, control, count, defect, conformance). 50-150
words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): X-bar, R chart, d2, A2, D3,
D4, Cp, Cpk, capability index, Western Electric rules
(statistical-process-control); CUSUM, EWMA (cusum-ewma-monitoring);
gage R and R, %GRR, repeatability, reproducibility, distinct
categories (measurement-systems-analysis).
