# Wave-35 leaf spec: attribute-agreement-analysis (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/attribute-agreement-analysis/
- Pack: as9100. Closest siblings: measurement-systems-analysis (the
  VARIABLE gage R and R leaf. Its own body says attribute gage
  studies "need agreement and Kappa analysis, not the range method"
  and its pitfall list repeats that attribute go/no-go results need
  agreement and Kappa analysis - it computes EV/AV/GRR/PV/TV/%GRR
  and distinct categories only, never kappa), attribute-control-
  charts (wave-35: p/np/c/u process MONITORING charts, not inspector
  agreement). Whole-tree grep proves ZERO owners for kappa, Cohen,
  Fleiss, inter-rater agreement.
- Standards id: as9100 (reference-only; MSA sibling convention).
  Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Analyze inspector agreement on attribute (go/no-go or
accept/rework/reject) judgments: compute the percent agreement, the
Cohen kappa for two inspectors and the Fleiss kappa for three or
more inspectors with the chance-agreement correction, classify the
kappa against the attribute-MSA acceptance bands (0.75 and above
good, 0.40 to 0.75 marginal, below 0.40 poor), and return the
agreement verdict that gates the attribute gage study. Produces the
observed agreement, the chance agreement, the kappa, the band
verdict, and the flagged need for inspector retraining or study
rework when the kappa is poor.

Does NOT do: variable gage R and R (EV/AV/GRR, percent GRR, distinct
categories - measurement-systems-analysis); p/np/c/u attribute
process control charts (attribute-control-charts); a test of
marginal homogeneity; pass-rate reporting as a substitute for the
chance-corrected agreement.

## Model (implement exactly)

Module constants:
- KAPPA_GOOD = 0.75, KAPPA_MARGINAL = 0.40 (band thresholds).

Conventions: two-inspector tables are square agreement tables of
counts (rows inspector A category, columns inspector B category).
Multi-inspector data are per-part rating vectors: each part has n
raters and one count per category (counts sum to n).

Functions (pure stdlib):
- percent_agreement(table) -> sum of the diagonal / total count.
  ValueError: empty/non-square table; negative counts; zero total.
- cohen_kappa(table) -> dict {kappa, observed_agreement,
  chance_agreement}: kappa = (po - pe)/(1 - pe) with po the diagonal
  fraction and pe = sum over categories of (row_total *
  col_total)/N^2. ValueErrors as percent_agreement.
- fleiss_kappa(ratings_matrix) -> dict {kappa, pbar, pe} where
  ratings_matrix is a list of per-part category-count rows (each row
  sums to the rater count): Pi = (sum_j x_ij^2 - n)/(n (n - 1)),
  Pbar = mean(Pi), p_j = column total/(parts * n), pe = sum p_j^2,
  kappa = (Pbar - pe)/(1 - pe). ValueErrors: empty matrix; rows of
  unequal length; any row sum < 2 (need at least two ratings per
  part); negative counts; pe == 1.
- kappa_verdict(kappa) -> "good" when kappa >= 0.75, "marginal"
  when 0.40 <= kappa < 0.75, "poor" when kappa < 0.40. ValueError:
  kappa outside [-1, 1] (allow -1 boundary).
- agreement_summary(...) -> dict with the applicable statistic and
  the verdict (helper on top of the pair functions).

Identity to test: a diagonal-only table gives kappa exactly 1.0; a
table with counts exactly at independence gives kappa 0.0 (within
float tolerance); percent agreement equals the diagonal fraction.

## Worked example

Cohen fixture: 40 parts rated pass/fail by two inspectors with the
agreement table a = [[24, 3], [5, 8]] (rows inspector A, columns
inspector B).
Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- percent_agreement: (24 + 8)/40 = 0.8000 (80%).
- chance_agreement: row totals 27 and 13, column totals 29 and 11:
  (27*29 + 13*11)/1600 = (783 + 143)/1600 = 0.57875.
- cohen_kappa: (0.8000 - 0.57875)/(1 - 0.57875) = 0.22125/0.42125
  = 0.5252 -> "marginal" (the 80% raw agreement overstates
  agreement because chance agreement is high).

Fleiss fixture: 20 parts rated by 3 inspectors into
accept/rework/reject with per-part category counts (each row sums to
3):
[[3,0,0],[3,0,0],[2,1,0],[3,0,0],[0,2,1],[2,1,0],[3,0,0],[1,2,0],
 [3,0,0],[0,3,0],[2,1,0],[3,0,0],[1,2,0],[0,2,1],[2,1,0],[3,0,0],
 [1,2,0],[3,0,0],[0,3,0],[2,1,0]]
- p_j = [0.6167, 0.3500, 0.0333]; pe = 0.50389.
- Pbar = 0.6667.
- fleiss_kappa = (0.6667 - 0.50389)/(1 - 0.50389) = 0.3281 ->
  "poor" (drives retraining or attribute study rework).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-square table; negative counts; zero total; empty
  matrix; ragged rows; row sum < 2; pe == 1.
- Diagonal table [[10,0],[0,10]]: po = 1, pe = 0.5, kappa = 1.0.
- Independence table [[5,5],[5,5]]: po = 0.5, pe = 0.5, kappa =
  0.0 within 1e-12.
- Worked Cohen case: kappa 0.5252 within 1e-4, verdict marginal.
- Worked Fleiss case: kappa 0.3281 within 1e-4, verdict poor.
- Verdict bands: 0.80 -> good; 0.60 -> marginal; 0.20 -> poor;
  -0.2 -> poor; ValueError outside [-1, 1].
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-attribute-agreement-analysis.yaml)

Query 1 (copy verbatim):
  "analyze inspector agreement for an attribute gage study with the Cohen kappa chance corrected agreement"
  intent: "manufacturing-quality; attribute gage study inspector agreement with Cohen kappa"
  expected_skill: "manufacturing-quality/as9100/attribute-agreement-analysis"
Query 2 (copy verbatim):
  "compute the Fleiss kappa for multiple inspectors classifying parts as accept rework or reject"
  intent: "manufacturing-quality; Fleiss kappa for multiple inspectors on attribute judgments"
  expected_skill: "manufacturing-quality/as9100/attribute-agreement-analysis"
Task ids: w35-attribute-agreement-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze inspector agreement
on attribute judgments:" and include the outputs in the Claim. First
tag: attribute-agreement-analysis. Additional tags ONLY:
cohen-kappa-agreement, fleiss-kappa-agreement, inter-rater-agreement,
chance-corrected-agreement, inspector-agreement. NEVER single
generic words (kappa, agreement, inspector, attribute, gage, rater).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): gage r and r, grr, percent
grr, repeatability, reproducibility, equipment variation, appraiser
variation, distinct categories (measurement-systems-analysis);
p-chart, np-chart, c-chart, u-chart, control limits
(attribute-control-charts); capability index.
