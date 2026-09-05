---
name: fault-tree-uncertainty-analysis
description: "Use when you must quantify the epistemic uncertainty band around a quantified fault-tree probability: convert each basic-event lognormal error factor to a lognormal sigma with the 90 percent normal quantile, combine the per-event sigmas into the lognormal sigma of the tree probability weighted by the Fussell-Vesely fractions, form the two-sided 90 percent lognormal-confidence-band around the top probability, compute the exceedance-probability of the true value above a target probability, and decompose the variance of the spread into per-event uncertainty-variance-shares. Produces the per-event sigmas, the combined sigma, the band bounds, the exceedance probability and the variance shares that gate confidence in a top-event number. Trigger: fault-tree uncertainty analysis, lognormal error factor, lognormal confidence band, uncertainty variance share."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [fault-tree-uncertainty-analysis, lognormal-error-factor, lognormal-confidence-band, uncertainty-variance-share]
  version: 0.1.0
  author: AeroSkills
---

# Fault Tree Uncertainty Analysis (systems-engineering-safety/arp4761a/fault-tree-uncertainty-analysis)

Use when you must quantify the epistemic uncertainty band around an
already-quantified fault-tree top probability. Each basic event carries
a lognormal error factor EF from the failure data; the leaf converts
each EF into a lognormal sigma with the 90 percent normal quantile,
combines the per-event sigmas into the lognormal sigma of the tree
probability using the Fussell-Vesely fractions as weights, forms the
two-sided 90 percent lognormal-confidence-band around the top
probability, computes the exceedance probability of the true value
above a target probability, and decomposes the variance of the spread
into per-event shares. The band bounds and shares gate how much
confidence to place in a top-event number. It consumes the quantified
top probability from systems-engineering-safety/arp4761a/fta-fmea and
the Fussell-Vesely fractions from systems-engineering-safety/arp4761a/
fault-tree-importance-measures; it never derives either input itself.

## Domain quick reference

- Lognormal error factor: EF is the multiplicative factor such that
  the 90 percent band of the event probability runs from q / EF to
  q * EF in the underlying lognormal model; EF >= 1.0 by definition.
- Error factor to sigma: sigma = ln(EF) / NORMAL_QUANTILE_90 with
  NORMAL_QUANTILE_90 = 1.645, the two-sided 90 percent normal
  quantile (error_factor_to_sigma).
- Combined lognormal sigma: sigma_lnq = sqrt(sum_i (fv_i * sigma_i)^2),
  the Fussell-Vesely-weighted first-order lognormal combination of the
  basic-event sigmas (combined_log_sigma). Weights are used as-is and
  never renormalized: a partial set is the analyst's stated
  representation of the tree.
- 90 percent lognormal-confidence-band: multiplicative and
  geometric-mean centered at q_top, lower = q_top * exp(-1.645 *
  sigma_lnq) and upper = q_top * exp(+1.645 * sigma_lnq)
  (confidence_band). At sigma_lnq = 0 the band collapses to
  [q_top, q_top].
- Exceedance probability: 1 - Phi((ln(target) - ln(q_top)) / sigma_lnq)
  with Phi the standard normal CDF via math.erf; the chance the true
  top probability exceeds the target (exceedance_probability). At
  target = q_top it is exactly 0.5, the median property of the
  lognormal.
- Variance shares: share_i = (fv_i * sigma_i)^2 / sum_j (fv_j *
  sigma_j)^2, aligned to the input order and summing to 1.0; zero total
  variance returns all-zero shares (variance_decomposition).
- This leaf quantifies the spread of an already-quantified tree. It
  does not rank basic events by importance measures (owned by
  fault-tree-importance-measures), derive the top probability from the
  tree structure (fta-fmea), fit statistical bounds to demonstration
  data (failure-rate-estimation), or combine measured quantities under
  a generic metrology recipe (cross-cutting/numerics/
  uncertainty-propagation).
- ARP4761A frames the safety assessment context; the lognormal
  error-factor model and combination are implemented summary-only.

## Workflow

1. Gather the tree inputs: the quantified top probability q_top from
   the fta-fmea quantification, the Fussell-Vesely fraction of every
   basic event from fault-tree-importance-measures, and the lognormal
   error factor EF of every basic event from the failure data.
2. Convert each error factor to a lognormal sigma with
   error_factor_to_sigma(ef): sigma = ln(EF) / NORMAL_QUANTILE_90, so
   an EF of 3 gives sigma 0.667849.
3. Combine the per-event sigmas into the lognormal sigma of the tree
   probability with combined_log_sigma(fv_weights, sigmas): sigma_lnq
   = sqrt of the Fussell-Vesely-weighted squared sum.
4. Form the two-sided 90 percent lognormal-confidence-band around the
   top probability with confidence_band(q_top, sigma_lnq): read the
   lower and upper band bounds that frame the epistemic uncertainty.
5. Compute the exceedance probability of the true value above a target
   probability with exceedance_probability(q_top, sigma_lnq, target).
6. Decompose the variance of the lognormal spread into per-event
   uncertainty-variance-shares with variance_decomposition(fv_weights,
   sigmas), read which events drive the band, and gate the confidence
   placed in the top-event number.
7. Confirm the deterministic checks with the contract test: python3
   scripts/test_fault_tree_uncertainty_analysis.py.

## Worked example

Aircraft function with quantified top probability q_top = 2.5e-6 and
three basic events carrying FV fractions [0.62, 0.31, 0.07] and error
factors [3, 5, 10]:

- Step 2 sigmas: EF 3 gives 0.667849, EF 5 gives 0.978382, EF 10 gives
  1.399748.
- Step 3 combined lognormal sigma: 0.522534.
- Step 4 band: lower 1.05836e-6 and upper 5.90535e-6, multipliers
  0.423345 and 2.362140; the point estimate 2.5e-6 sits strictly
  inside the band, geometric-mean centered (lower * upper = q_top^2).
- Step 5 exceedance: against target 1e-7 (25 times below the estimate)
  0.99999999964, against target 1e-5 (4 times above) 0.00398872; the
  targets straddle the 50 percent line because 1e-7 < q_top < 1e-5,
  and at target = q_top the exceedance is exactly 0.5.
- Step 6 shares: event 1 (EF 3) 0.627931, event 2 (EF 5) 0.336908,
  event 3 (EF 10) 0.035161, summing to 1.0: the largest share is the
  small-EF event with the big FV fraction, not the widest-EF event.

## Verification

- Confirm error_factor_to_sigma returns 0.667849, 0.978382 and
  1.399748 for EFs 3, 5 and 10 within 1e-6, and exactly 0.0 for EF
  1.0; EFs below 1.0 (0.999, 0.0) raise ValueError because they would
  reverse the band.
- Confirm combined_log_sigma on the worked example gives 0.522534
  within 1e-6, the single-event identity (FV weight 1.0 returns that
  event sigma), and all-zero inputs give 0.0; length mismatch, a
  negative weight and a negative sigma raise ValueError.
- Confirm confidence_band gives lower 1.05836e-6 within 1e-10 and
  upper 5.90535e-6 within 1e-10 with keys exactly lower and upper, the
  geometric-center identity lower * upper = q_top^2, and the collapse
  to [q_top, q_top] at sigma 0; q_top 0, q_top 1.5 and sigma -0.1
  raise ValueError.
- Confirm exceedance_probability gives 0.99999999964 within 1e-10 and
  0.00398872 within 1e-8 on the two worked targets, exactly 0.5 at
  target = q_top, and that targets below q_top exceed 0.5 while targets
  above sit below; sigma 0, target 0 or negative, and q_top outside
  (0, 1] raise ValueError.
- Confirm variance_decomposition shares 0.627931, 0.336908, 0.035161
  within 1e-6 summing to 1.0 within 1e-12, order-preserving under
  permutation, equal for equal weights and sigmas, and all-zero for
  zero total variance; a length mismatch or negative input raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_fault_tree_uncertainty_analysis.py (35 tests,
  deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: derives the minimal
  cut-set structure and the quantified top event probability q_top
  this leaf frames with a band.
- systems-engineering-safety/arp4761a/fault-tree-importance-measures:
  supplies the Fussell-Vesely fractions used as weights here; its
  point importance measures rank events, a different question from the
  spread decomposition this leaf computes.
- systems-engineering-safety/arp4761a/failure-rate-estimation: the
  demonstration statistics and error-factor style inputs behind each
  basic-event EF.
- systems-engineering-safety/arp4761a/common-cause-analysis: the
  shared-cause dependency modeling that the independence assumption of
  the combination can break.
- cross-cutting/numerics/uncertainty-propagation: generic first-order
  combination of spreads on measured quantities; it never composes
  fault-tree structure with importance weights.

## Pitfalls

- Reading the largest variance share as the most probable driver of
  the top event: the share is a fractional contribution to the spread
  of the lognormal model, weighted by the FV fraction squared; a
  wide-EF event with a tiny FV fraction (EF 10 at 0.035161 in the
  example) contributes little band even though its sigma is the
  largest.
- Renormalizing a partial weight set: the FV fractions from
  fault-tree-importance-measures are used as-is; a partial set is the
  analyst's stated representation of the tree, and renormalizing would
  overstate the spread of the events actually included.
- Treating the band as a frequentist confidence interval: the band
  quantifies epistemic uncertainty from the stated error factors, so
  its width is only as good as the EFs and the FV representation
  behind it.
- Quoting the exceedance probability without its target: the number is
  a comparison of the lognormal model against one stated target
  probability, and it moves from 0.99999999964 at 1e-7 to 0.00398872
  at 1e-5 in the worked example.
- Reporting sigma_lnq = 0 as proof of certainty: an EF of 1.0 only
  records that no spread was stated for the event; the band then
  collapses by convention, not by evidence.
- Forgetting the model edge at q_top near 1: the multiplicative band
  is geometric-mean centered on the estimate and can push the upper
  bound past 1.0 for probabilities close to 1; the band is a spread
  statement around the estimate, not a re-bounding of the probability
  scale.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fault_tree_uncertainty_analysis.py

The test covers the worked sigmas 0.667849, 0.978382 and 1.399748
within 1e-6, the combined sigma 0.522534, the band bounds 1.05836e-6
and 5.90535e-6, the geometric-center and collapse identities, the
exceedance anchors 0.99999999964 and 0.00398872 with the exact 0.5
median identity at target = q_top, the variance shares 0.627931,
0.336908 and 0.035161 summing to 1.0, order preservation, the zero
total variance convention, determinism across calls, and ValueError
rejection of every non-physical input listed in the spec.

## Compliance

- Standards referenced, not reproduced: ARP4761A is a SAE standard
  (sae.org/standards); the lognormal error-factor uncertainty model is
  implemented summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
