"""Fault tree uncertainty analysis (systems-engineering-safety, arp4761a pack).

Quantify the epistemic uncertainty band around an already-quantified
fault-tree top probability from lognormal basic-event error factors.
Pure stdlib, deterministic, offline.

Model (spec wave-40):
- Each basic-event error factor EF is converted to a lognormal sigma
  with sigma = ln(EF) / NORMAL_QUANTILE_90, where NORMAL_QUANTILE_90 is
  the two-sided 90 percent normal quantile (1.645).
- The per-event sigmas are combined into the lognormal sigma of the top
  probability with the Fussell-Vesely fractions from
  fault-tree-importance-measures as weights:
  sigma_lnq = sqrt(sum_i (fv_i * sigma_i)^2). Weights are used as-is,
  never renormalized: a partial set is the analyst's stated
  representation of the tree.
- The two-sided 90 percent lognormal-confidence-band around the top
  probability q_top is multiplicative and geometric-mean centered at
  q_top: lower = q_top * exp(-1.645 * sigma_lnq), upper = q_top *
  exp(+1.645 * sigma_lnq).
- The exceedance probability of the true value above a target
  probability is 1 - Phi((ln(target) - ln(q_top)) / sigma_lnq) with Phi
  the standard normal CDF via math.erf.
- The variance of the lognormal spread decomposes into per-event shares
  (fv_i * sigma_i)^2 / sum_j (fv_j * sigma_j)^2.

Non-physical inputs raise ValueError: an error factor below 1.0, a
negative weight or sigma, mismatched list lengths, a top probability
outside (0, 1], a negative lognormal sigma, and a non-positive target.
"""

import math

NORMAL_QUANTILE_90 = 1.645

ZERO_TOLERANCE = 1e-15


def error_factor_to_sigma(ef):
    """Convert a lognormal error factor EF to its lognormal sigma.

    sigma = ln(EF) / NORMAL_QUANTILE_90. An error factor below 1.0
    would reverse the band, so it raises ValueError.
    """
    if ef < 1.0:
        raise ValueError("error factor must be >= 1.0, got %r" % (ef,))
    return math.log(ef) / NORMAL_QUANTILE_90


def _validate_weight_sigma_lists(fv_weights, sigmas):
    """Check the weight and sigma lists are physical and aligned."""
    if len(fv_weights) != len(sigmas):
        raise ValueError(
            "fv_weights and sigmas must have equal length: %d vs %d"
            % (len(fv_weights), len(sigmas))
        )
    for weight in fv_weights:
        if weight < 0.0:
            raise ValueError("Fussell-Vesely weight must be >= 0, got %r" % (weight,))
    for sigma in sigmas:
        if sigma < 0.0:
            raise ValueError("basic-event sigma must be >= 0, got %r" % (sigma,))


def combined_log_sigma(fv_weights, sigmas):
    """Fussell-Vesely-weighted first-order lognormal combination.

    sigma_lnq = sqrt(sum_i (fv_i * sigma_i)^2). Every weight and sigma
    must be non-negative and the lists must have equal length.
    """
    _validate_weight_sigma_lists(fv_weights, sigmas)
    total = 0.0
    for weight, sigma in zip(fv_weights, sigmas):
        term = weight * sigma
        total += term * term
    return math.sqrt(total)


def confidence_band(q_top, sigma_lnq):
    """Two-sided 90 percent lognormal-confidence-band around q_top.

    Returns {"lower": q_top * exp(-1.645 * sigma_lnq), "upper": q_top *
    exp(+1.645 * sigma_lnq)}. At sigma_lnq = 0 the band collapses to
    [q_top, q_top].
    """
    if not (0.0 < q_top <= 1.0):
        raise ValueError("top probability must lie in (0, 1], got %r" % (q_top,))
    if sigma_lnq < 0.0:
        raise ValueError("lognormal sigma must be >= 0, got %r" % (sigma_lnq,))
    lower = q_top * math.exp(-NORMAL_QUANTILE_90 * sigma_lnq)
    upper = q_top * math.exp(+NORMAL_QUANTILE_90 * sigma_lnq)
    return {"lower": lower, "upper": upper}


def _normal_cdf(z):
    """Standard normal CDF Phi(z) via math.erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def exceedance_probability(q_top, sigma_lnq, target):
    """Probability the true top probability exceeds the target.

    1 - Phi((ln(target) - ln(q_top)) / sigma_lnq). Requires a strictly
    positive sigma_lnq, q_top in (0, 1] and a positive target.
    """
    if sigma_lnq <= 0.0:
        raise ValueError("lognormal sigma must be > 0, got %r" % (sigma_lnq,))
    if not (0.0 < q_top <= 1.0):
        raise ValueError("top probability must lie in (0, 1], got %r" % (q_top,))
    if target <= 0.0:
        raise ValueError("target probability must be > 0, got %r" % (target,))
    z = (math.log(target) - math.log(q_top)) / sigma_lnq
    return 1.0 - _normal_cdf(z)


def variance_decomposition(fv_weights, sigmas):
    """Per-event shares of the lognormal variance, aligned to input order.

    Share_i = (fv_i * sigma_i)^2 / sum_j (fv_j * sigma_j)^2, summing to
    1.0. Zero total variance (every sigma zero or every weight zero)
    returns a list of zeros.
    """
    _validate_weight_sigma_lists(fv_weights, sigmas)
    terms = [weight * sigma for weight, sigma in zip(fv_weights, sigmas)]
    total = sum(term * term for term in terms)
    if total <= ZERO_TOLERANCE:
        return [0.0 for _ in terms]
    return [(term * term) / total for term in terms]
