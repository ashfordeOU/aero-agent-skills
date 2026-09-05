# Wave-40 leaf spec: fault-tree-uncertainty-analysis (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/fault-tree-uncertainty-analysis/
- Pack: arp4761a. Closest siblings: fault-tree-importance-measures (its
  frontmatter description limits the claim to point ranking: "rank basic
  events of a fault tree by importance: compute the Birnbaum measure, the
  Fussell-Vesely measure, the risk achievement worth (RAW) and the risk
  reduction worth (RRW) of each basic event from the minimal cut sets and
  the basic-event probabilities, sort the events by each measure, and flag
  the dominant contributors above a Fussell-Vesely threshold"; its Pitfalls
  call Birnbaum "a raw sensitivity, not a fractional contribution". The
  file contains zero distributional math: prep grep for lognormal, sigma
  and error-factor in that SKILL.md returns no lines; it supplies the
  Fussell-Vesely weights this leaf consumes as inputs, it never combines
  them into a spread. Its trigger "top event sensitivity" stays reserved to
  that leaf), fta-fmea (owns minimal cut sets and the top event
  probability: "compute minimal cut sets from AND/OR gate structures,
  check cut-set probability sanity against the top event probability", plus
  severity-to-DAL mapping), failure-rate-estimation (demonstration
  statistics from test or service data: "derive the exact poisson
  chi-square upper-bound on the failure-rate at a stated confidence", no
  lognormal error-factor treatment), cross-cutting/numerics/
  uncertainty-propagation (generic GUM first-order combination of measured
  quantities with coverage factors; no fault-tree composition with
  importance weights). Whole-tree greps at prep: "lognormal" and
  "error factor"/"error-factor" = 0 hits in skills/systems-engineering-
  safety/; the only lognormal/uncertainty corpus tasks in eval route to
  cross-cutting/numerics/uncertainty-propagation. GENUINE SES gap (fresh
  probe): the quantified fault-tree probability is delivered with no
  uncertainty band.
- Standards id: arp4761a (reference-only). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Quantify the epistemic uncertainty band around an already-quantified
fault-tree top probability from lognormal basic-event error factors:
convert each error factor EF to a lognormal sigma with the 90 percent
normal quantile, combine the per-event sigmas into the lognormal sigma of
the tree probability using the Fussell-Vesely fractions from
fault-tree-importance-measures as weights, form the two-sided
lognormal-confidence-band around the top probability, compute the
exceedance-probability of the true value above a target probability, and
decompose the variance of the lognormal spread into per-event shares.
Produces the per-event sigmas, the combined lognormal sigma, the 90
percent band bounds, the exceedance probability and the variance shares
that gate how much confidence to place in a top-event number. Does NOT
do: point ranking of events by Birnbaum, Fussell-Vesely, RAW or RRW, or
any dominance flags (fault-tree-importance-measures); minimal cut set
derivation, gate algebra or severity-to-DAL mapping (fta-fmea);
chi-square confidence bounds or zero-failure demonstrations from test
hours (failure-rate-estimation); generic GUM measurement-uncertainty
combination (cross-cutting/numerics/uncertainty-propagation).

## Model (implement exactly)

Functions (pure stdlib, math only):
- error_factor_to_sigma(ef) -> float sigma = ln(ef) / 1.645, where 1.645
  is the two-sided 90 percent normal quantile (module constant
  NORMAL_QUANTILE_90); ValueError if ef < 1.0 (an error factor below 1
  would reverse the band).
- combined_log_sigma(fv_weights, sigmas) -> float
  sigma_lnq = sqrt(sum_i (fv_i * sigma_i)^2), the Fussell-Vesely-weighted
  first-order lognormal combination of the basic-event sigmas. Weights are
  used as-is, never renormalized: the analyst supplies the Fussell-Vesely
  fractions from fault-tree-importance-measures and a partial set is the
  analyst's stated representation of the tree; the module only requires
  every weight and every sigma to be non-negative and the two lists to
  have equal length, ValueError otherwise.
- confidence_band(q_top, sigma_lnq) -> dict {"lower":
  q_top * exp(-1.645 * sigma_lnq), "upper": q_top * exp(+1.645 *
  sigma_lnq)}, the 90 percent two-sided lognormal band around the top
  probability (multiplicative, geometric-mean centered at q_top);
  ValueError if q_top outside (0, 1] or sigma_lnq < 0. At sigma_lnq = 0
  the band collapses to [q_top, q_top].
- exceedance_probability(q_top, sigma_lnq, target) -> float
  1 - Phi((ln(target) - ln(q_top)) / sigma_lnq), with Phi the standard
  normal CDF via math.erf, Phi(z) = 0.5 * (1 + erf(z / sqrt(2))); the
  probability that the true top probability exceeds the target. ValueError
  if sigma_lnq <= 0, q_top outside (0, 1] or target <= 0.
- variance_decomposition(fv_weights, sigmas) -> list of per-event shares
  (fv_i * sigma_i)^2 / sum_j (fv_j * sigma_j)^2, aligned to the input
  order, summing to 1.0; the uncertainty contribution of each event to the
  spread, NOT a Birnbaum sensitivity (see fence). Zero total variance
  (every sigma zero or every weight zero) returns a list of zeros.
  ValueError if the lengths differ or any weight or sigma is negative.
Module constants: NORMAL_QUANTILE_90 = 1.645.

Identity to test: EF = 1 gives sigma 0; a single event with fv weight 1.0
makes combined_log_sigma return that event sigma; exceedance at target ==
q_top is exactly 0.5 (the median property of the lognormal); the band is
geometric-mean centered, q_top sits strictly inside the band for sigma >
0; variance shares sum to 1.0 and with one contributing event equal 1.0.

## Worked example

q_top = 2.5e-6 with three basic events, FV weights [0.62, 0.31, 0.07] and
error factors [3, 5, 10]:
- Per-event sigmas ln(EF)/1.645: 0.667849, 0.978382, 1.399748.
- combined_log_sigma = 0.522534 (sqrt of the FV-weighted squared sum).
- 90 percent band multipliers exp(+-1.645 * 0.522534): lower 0.423345,
  upper 2.362140, giving confidence_band bounds 1.05836e-6 and
  5.90535e-6; the point estimate 2.5e-6 sits inside the band.
- variance_decomposition shares: 0.627931 (event 1, EF 3), 0.336908
  (event 2, EF 5), 0.035161 (event 3, EF 10); sum 1.0.
- exceedance_probability vs target 1e-7: 0.99999999964 (above the 50
  percent line, the true value almost surely exceeds a target 25 times
  below the estimate); vs target 1e-5: 0.00398872 (below the 50 percent
  line); the two targets straddle the 0.5 line because 1e-7 < q_top <
  1e-5, and the identity check at target = q_top returns exactly 0.5.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor script
/tmp/w40spec/anchor_fault_tree_uncertainty.py (prep-verified by stdlib
math).

## Validation list (contract test must include)

- error_factor_to_sigma(3) = 0.667849 within 1e-6; EF 5 -> 0.978382; EF
  10 -> 1.399748 (ln 10 / 1.645).
- EF 1.0 -> 0.0 exactly; ValueError at ef 0.999 and at ef 0.
- combined_log_sigma on the worked example = 0.522534 within 1e-6.
- Single-event identity: combined_log_sigma([1.0], [0.667849]) = 0.667849.
- ValueErrors: length mismatch, negative FV weight, negative sigma.
- confidence_band(2.5e-6, 0.522534) lower = 1.05836e-6 within 1e-10 and
  upper = 5.90535e-6 within 1e-10; q_top inside the band.
- Band multiplier identity: lower * upper = q_top^2 (geometric center);
  at sigma 0 the band is [q, q].
- ValueErrors: q_top 0, q_top 1.5, sigma_lnq -0.1.
- exceedance_probability(2.5e-6, 0.522534, 1e-7) = 0.99999999964 within
  1e-10; vs 1e-5 = 0.00398872 within 1e-8.
- Median identity: exceedance at target = q_top is 0.5 exactly; target
  below q_top gives exceedance above 0.5, target above q_top below 0.5.
- ValueErrors: sigma_lnq 0, target 0, target negative, q_top outside (0,
  1].
- variance_decomposition shares 0.627931, 0.336908, 0.035161 within 1e-6,
  summing to 1.0 within 1e-12.
- Single-event decomposition: one event returns [1.0]; equal weights and
  equal sigmas return equal shares; all-zero inputs return zeros.
- Determinism; dict keys exactly lower/upper; list order preserved.

## Corpus fragment (eval/hit1-wave40-fault-tree-uncertainty-analysis.yaml)

Query 1 (copy verbatim):
  "apply the fault-tree-uncertainty-analysis to propagate the lognormal error-factor of each basic event into the lognormal-confidence-band around the fault-tree top probability"
  intent: "systems-engineering-safety; lognormal error-factor propagation to a fault-tree probability band"
  expected_skill: "systems-engineering-safety/arp4761a/fault-tree-uncertainty-analysis"
Query 2 (copy verbatim):
  "compute the lognormal-confidence-band and the exceedance-probability against a target probability from the lognormal error-factor inputs, then read the uncertainty-variance-share of each event from the fault-tree-uncertainty-analysis"
  intent: "systems-engineering-safety; lognormal-confidence-band and exceedance against a target"
  expected_skill: "systems-engineering-safety/arp4761a/fault-tree-uncertainty-analysis"
Task ids: w40-fault-tree-uncertainty-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must quantify the epistemic
uncertainty band around a quantified fault-tree probability:" and include
the outputs in the Claim. First tag: fault-tree-uncertainty-analysis.
Additional tags ONLY: lognormal-error-factor, lognormal-confidence-band,
uncertainty-variance-share. NEVER single generic words (uncertainty,
probability, band, variance, sigma, error, factor, fault, tree,
lognormal, event). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): birnbaum, fussell-vesely-importance,
raw, rrw, risk-achievement-worth, risk-reduction-worth, top-event-
sensitivity, dominant-contributor, basic-event-ranking, rank-list
(fault-tree-importance-measures); minimal-cut-set, cut-set-probability,
and-or-gate, severity-to-dal (fta-fmea); chi-square, zero-failure-rule,
test-hours, confidence-upper-bound, mtbf (failure-rate-estimation); gum,
coverage-factor, combined-standard-uncertainty, measurement-uncertainty
(cross-cutting/numerics/uncertainty-propagation).
