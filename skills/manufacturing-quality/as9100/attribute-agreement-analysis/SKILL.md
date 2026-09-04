---
name: attribute-agreement-analysis
description: "Use when you must analyze inspector agreement on attribute judgments: percent agreement on go/no-go or accept/rework/reject results, the Cohen kappa for two inspectors and the Fleiss kappa for three or more inspectors with the chance-agreement correction, the kappa verdict against the attribute measurement system acceptance bands (0.75 and up good, 0.40 to 0.75 marginal, under 0.40 poor), and the retraining or study rework flag when agreement is poor. Produces observed agreement, chance agreement, kappa, band verdict, and the verdict gating the attribute gage study. Trigger: inspector agreement, cohen kappa, fleiss kappa, inter-rater agreement, chance-corrected agreement, kappa analysis, attribute gage study, attribute judgments."
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
  tags: [attribute-agreement-analysis, cohen-kappa-agreement, fleiss-kappa-agreement, inter-rater-agreement, chance-corrected-agreement, inspector-agreement]
  version: 0.1.0
  author: Aero Agent Skills
---

# Attribute Agreement Analysis (manufacturing-quality/as9100/attribute-agreement-analysis)

Use when the task is judging whether inspectors agree on attribute
(go/no-go or accept/rework/reject) judgments: the observed percent
agreement, the chance agreement implied by the inspectors' marginal
tendencies, the chance-corrected Cohen kappa for two inspectors and the
Fleiss kappa for three or more inspectors, and the verdict that gates
the attribute gage study. The raw percent agreement can look strong
while the chance-corrected kappa is only marginal or poor, which is why
the attribute study needs the kappa, not the pass rate alone. This leaf
implements both kappa forms in pure Python, stdlib only. It pairs with
manufacturing-quality/as9100/measurement-systems-analysis, which covers
variable-data gage studies with the range method and explicitly routes
attribute go/no-go results here.

## Domain quick reference

- Conventions: two-inspector data are square agreement tables of counts
  (rows inspector A category, columns inspector B category).
  Multi-inspector data are per-part rating vectors: each part row holds
  the count of raters choosing each category, and the row sums to the
  rater count n.
- Observed agreement: po = sum of the diagonal / total count. This is
  the raw percent agreement; it includes agreements that happen by
  chance.
- Cohen kappa (two inspectors): pe = sum over categories of
  (row_total * col_total) / N^2, kappa = (po - pe) / (1 - pe). Kappa is
  1.0 for perfect agreement, 0.0 when the agreement is exactly what
  chance predicts, negative when agreement is below chance.
- Fleiss kappa (three or more inspectors): for part i with n ratings,
  Pi = (sum_j x_ij^2 - n) / (n (n - 1)) is the part's agreement
  fraction; Pbar is the mean of Pi over parts; p_j is the column total
  over the total rating count; pe = sum_j p_j^2;
  kappa = (Pbar - pe) / (1 - pe).
- Acceptance bands: kappa at or above 0.75 is good, 0.40 to 0.75 is
  marginal, below 0.40 is poor. A poor kappa flags inspector
  retraining or attribute gage study rework; a marginal kappa needs
  judgment before the study is accepted.
- Reading the raw rate alone misleads: when both inspectors share a
  strong category tendency, the chance agreement is high and a high
  percent agreement can hide a mediocre kappa.
- AS9100 frames monitoring and measuring resources as controlled and
  fit for purpose (paraphrase of clause 7.1.5 practice); the attribute
  gage study with the kappa verdict is the aerospace evidence that an
  inspection process agrees, summarized here without clause text.

## Workflow

1. Collect the attribute judgments: two inspectors give a square
   agreement table of counts; three or more inspectors give per-part
   rating vectors (each row sums to the rater count).
2. Get the raw agreement rate with percent_agreement(table).
3. For two inspectors run cohen_kappa(table) to get the kappa plus the
   observed and chance agreement terms.
4. For three or more inspectors run fleiss_kappa(ratings_matrix) to get
   the kappa plus Pbar and pe.
5. Score the kappa with kappa_verdict(kappa): good, marginal, or poor,
   or run agreement_summary(table=...) or
   agreement_summary(ratings_matrix=...) for the applicable statistic
   and the verdict in one dict.
6. Act on the verdict: poor drives inspector retraining or attribute
   gage study rework; compare the observed agreement against the chance
   agreement to explain the gap.
7. Confirm the deterministic checks with the contract test
   scripts/test_attribute_agreement_analysis.py.

## Worked example

Cohen fixture: 40 parts rated pass/fail by two inspectors with the
agreement table [[24, 3], [5, 8]] (rows inspector A, columns inspector
B). Real module outputs:

- percent_agreement: 0.8 (80% raw agreement).
- chance_agreement: (27 * 29 + 13 * 11) / 1600 = 0.57875.
- cohen_kappa: kappa 0.5252 = (0.8 - 0.57875) / (1 - 0.57875),
  verdict marginal. The 80% raw rate overstates agreement because the
  chance agreement is high.

Fleiss fixture: 20 parts rated by 3 inspectors into
accept/rework/reject with per-part category counts (each row sums to
3). Real module outputs:

- p_j = [0.6167, 0.3500, 0.0333]; pe = 0.50389.
- Pbar = 0.6667.
- fleiss_kappa: kappa 0.3281 = (0.6667 - 0.50389) / (1 - 0.50389),
  verdict poor, which drives retraining or attribute gage study rework.

## Verification

- Confirm cohen_kappa([[24, 3], [5, 8]]) returns kappa 0.5252 with
  observed agreement 0.8 and chance agreement 0.57875.
- Confirm fleiss_kappa on the 20-part fixture returns kappa 0.3281,
  Pbar 0.6667, pe 0.50389.
- Confirm the identities: a diagonal-only table [[10, 0], [0, 10]]
  gives kappa exactly 1.0 with chance agreement 0.5; an independence
  table [[5, 5], [5, 5]] gives kappa 0.0 within float tolerance.
- Confirm the verdict bands: 0.80 good, 0.60 and 0.40 marginal, 0.20
  and -0.2 poor, and kappa outside [-1, 1] raises ValueError.
- Confirm every non-physical input raises ValueError: empty or
  non-square agreement tables, negative counts, zero totals, an empty
  ratings matrix, ragged rows, a part row with fewer than two ratings,
  and a chance agreement of exactly 1.0.
- Run the contract test offline: python3
  scripts/test_attribute_agreement_analysis.py (34 tests,
  deterministic).

## Related leaves

- manufacturing-quality/as9100/measurement-systems-analysis: the
  variable-data gage study sibling; its body routes attribute go/no-go
  results here because they need agreement and kappa analysis, not the
  range method.
- manufacturing-quality/as9100/calibration-control: instrument
  calibration state and traceability, the precondition that the
  attribute judgments are made on a controlled basis.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_attribute_agreement_analysis.py

The test covers the Cohen worked example (kappa 0.5252, verdict
marginal), the Fleiss worked example (kappa 0.3281, verdict poor), the
diagonal-table kappa-1.0 and independence kappa-0.0 identities, the
observed and chance agreement terms, the verdict bands and their 0.75
and 0.40 thresholds, dict key shapes, determinism, and ValueError
rejection of empty, non-square, negative, zero-total, ragged, and
low-rating inputs.

## Compliance

- Standards referenced, not reproduced: AS9100 clause 7.1.5 frames
  monitoring and measuring resources; the kappa statistics and the
  0.75/0.40 acceptance bands are common attribute MSA methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
