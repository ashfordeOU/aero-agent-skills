#!/usr/bin/env python3
"""CMH-17 composite allowables logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml: mmpsd gated true, far-25
public domain; CMH-17 referenced by name only): composite material
design allowables follow the same statistical basis methodology as
metallic allowables: A-basis (95% confidence, 99% content) and B-basis
(95% confidence, 90% content) are derived from the sample mean minus a
one-sided normal tolerance k-factor times the sample standard
deviation. The CMH-17 approach adds coupon pooling across batches and
environments (a larger effective sample shrinks the k-factor) and
laminate-level knockdown factors for environmental conditioning,
barely visible impact damage, and open hole features applied to lamina
allowables. Where the strength data follow a two-parameter Weibull
distribution the content quantile is used instead of the normal
tolerance method. Design-value tables are never reproduced here.
"""

import math
import statistics

CONF_95_Z = 1.6448536269514722  # z for 95% confidence (one-sided)
BASIS_CONTENT_Z = {
    "A": 2.3263478740408408,  # z for 99% content
    "B": 1.2815515655446004,  # z for 90% content
}
BASIS_CONTENT_P = {"A": 0.99, "B": 0.90}
MIN_SAMPLES = {"A": 10, "B": 6}


def k_factor_one_sided(n, basis, conf=0.95):
    """One-sided normal tolerance k-factor (Owen/Odeh approximation).

    n: sample count (integer >= 2); basis: 'A' or 'B'; conf:
    confidence level (only 0.95 supported here). Formula:
    a = 1 - z_c^2/(2(n-1)); b = z_p^2 - z_c^2/n;
    k = (z_p + sqrt(z_p^2 - a*b))/a.
    Invalid inputs raise ValueError.
    """
    if not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer >= 2: %r" % (n,))
    if basis not in BASIS_CONTENT_Z:
        raise ValueError("basis must be 'A' or 'B': %r" % (basis,))
    if conf != 0.95:
        raise ValueError("only 0.95 confidence supported: %r" % (conf,))
    z_c = CONF_95_Z
    z_p = BASIS_CONTENT_Z[basis]
    a = 1.0 - z_c ** 2 / (2.0 * (n - 1))
    b = z_p ** 2 - z_c ** 2 / n
    return (z_p + math.sqrt(z_p ** 2 - a * b)) / a


def min_samples(basis):
    """Common minimum sample counts: 10 for A-basis, 6 for B-basis.

    Verify against the current CMH-17 edition. Unknown basis raises
    ValueError.
    """
    if basis not in BASIS_CONTENT_Z:
        raise ValueError("basis must be 'A' or 'B': %r" % (basis,))
    return MIN_SAMPLES[basis]


def check_sample_count(n, basis):
    """Return (ok, required): whether n meets the basis minimum."""
    required = min_samples(basis)
    return n >= required, required


def allowable_from_sample(values, basis):
    """Design allowable from a coupon sample: mean - k * standard deviation.

    Raises ValueError if the sample is below the minimum count for
    the basis, the basis is unknown, or the standard deviation is
    zero (constant sample).
    """
    n = len(values)
    min_n = min_samples(basis)
    if n < min_n:
        raise ValueError(
            "sample of %d below minimum %d for %s-basis" % (n, min_n, basis)
        )
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    if sd == 0.0:
        raise ValueError("zero sample standard deviation: %r" % (values,))
    k = k_factor_one_sided(n, basis)
    return mean - k * sd


def pooled_allowable(batches, basis):
    """Pool coupon batches (batches, environments) into one allowable.

    batches: list of value lists, one per coupon batch. The pooled
    mean is the mean of all values; the pooled standard deviation is
    the within-batch pooled standard deviation
    (sum((n_i - 1) s_i^2) / sum(n_i - 1))^0.5; the effective sample
    count is the total across batches and drives the k-factor.

    Returns a dict with n, batches, mean, sd, k, allowable. Raises
    ValueError on empty input, single-value batches, unknown basis, or
    a total below the basis minimum.
    """
    if basis not in BASIS_CONTENT_Z:
        raise ValueError("basis must be 'A' or 'B': %r" % (basis,))
    if not batches:
        raise ValueError("no batches to pool")
    ns = []
    for i, batch in enumerate(batches):
        if len(batch) < 2:
            raise ValueError("batch %d needs at least 2 values" % i)
        ns.append(len(batch))
    total_n = sum(ns)
    min_n = min_samples(basis)
    if total_n < min_n:
        raise ValueError(
            "pooled sample of %d below minimum %d for %s-basis"
            % (total_n, min_n, basis)
        )
    all_values = [v for batch in batches for v in batch]
    pooled_mean = statistics.mean(all_values)
    num = 0.0
    den = 0.0
    for batch in batches:
        n_i = len(batch)
        s_i = statistics.stdev(batch)
        num += (n_i - 1) * s_i * s_i
        den += n_i - 1
    pooled_sd = math.sqrt(num / den)
    k = k_factor_one_sided(total_n, basis)
    return {
        "n": total_n,
        "batches": ns,
        "mean": pooled_mean,
        "sd": pooled_sd,
        "k": k,
        "allowable": pooled_mean - k * pooled_sd,
    }


def _weibull_ll(beta, values):
    """Newton step helper for the two-parameter Weibull MLE shape."""
    n = len(values)
    xb = [v ** beta for v in values]
    sum_xb = sum(xb)
    sum_xb_ln = sum(x * math.log(v) for x, v in zip(xb, values))
    mean_ln = sum(math.log(v) for v in values) / n
    f = sum_xb_ln / sum_xb - 1.0 / beta - mean_ln
    sum_xb_ln2 = sum(x * (math.log(v) ** 2) for x, v in zip(xb, values))
    df = (sum_xb_ln2 * sum_xb - sum_xb_ln ** 2) / (sum_xb ** 2) + 1.0 / beta ** 2
    return f, df


def weibull_mle(values, max_iter=100, tol=1e-12):
    """Two-parameter Weibull MLE: returns (shape beta, scale eta).

    Solves the standard MLE equation for beta by Newton iteration
    (deterministic, stdlib only). Requires at least 2 positive
    values; raises ValueError otherwise.
    """
    if len(values) < 2:
        raise ValueError("Weibull fit needs at least 2 values")
    if any(v <= 0.0 for v in values):
        raise ValueError("Weibull fit needs strictly positive values")
    beta = 1.5
    for _ in range(max_iter):
        f, df = _weibull_ll(beta, values)
        if df == 0.0:
            break
        step = f / df
        beta -= step
        if beta <= 0.0:
            beta = 0.5
        if abs(step) < tol:
            break
    n = len(values)
    eta = (sum(v ** beta for v in values) / n) ** (1.0 / beta)
    return beta, eta


def weibull_content_value(values, p):
    """Content quantile from a two-parameter Weibull fit.

    The value exceeded by fraction p of the population:
    eta * (-ln(p))^(1/beta) (the Weibull quantile at u = 1 - p).
    p must be in (0, 1).
    """
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0, 1): %r" % (p,))
    beta, eta = weibull_mle(values)
    return eta * (-math.log(p)) ** (1.0 / beta)


def weibull_basis(values, basis):
    """Weibull basis value: content quantile with a conservative
    sample-size confidence shrink (1 - 1/n).

    The authoritative confidence adjustment uses the published CMH-17
    factors (referenced, not reproduced); this simple factor keeps the
    result below the raw content quantile and is documented as an
    engineering approximation. Unknown basis raises ValueError.
    """
    if basis not in BASIS_CONTENT_Z:
        raise ValueError("basis must be 'A' or 'B': %r" % (basis,))
    n = len(values)
    if n < 2:
        raise ValueError("Weibull basis needs at least 2 values")
    content = weibull_content_value(values, BASIS_CONTENT_P[basis])
    return content * (1.0 - 1.0 / n)


def knockdown(lamina_allowable, env_factor=1.0, bvid_factor=1.0, hole_factor=1.0):
    """Apply laminate knockdown factors to a lamina allowable.

    Each factor must be in (0, 1]; factors below 0 or above 1 raise
    ValueError. Returns (laminate_allowable, combined_factor) where
    the combined factor is the product of the three inputs.
    """
    factors = (env_factor, bvid_factor, hole_factor)
    for name, f in zip(("env", "bvid", "hole"), factors):
        if not (0.0 < f <= 1.0):
            raise ValueError(
                "%s factor must be in (0, 1], got %r" % (name, f)
            )
    combined = env_factor * bvid_factor * hole_factor
    return lamina_allowable * combined, combined


def basis_statement(basis):
    """Confidence/content statement for a basis designation."""
    if basis not in BASIS_CONTENT_Z:
        raise ValueError("basis must be 'A' or 'B': %r" % (basis,))
    pct = "99%" if basis == "A" else "90%"
    return "%s-basis: 95%% confidence, %s content" % (basis, pct)


def build_allowable_table(props, basis, env_factor=1.0, bvid_factor=1.0,
                          hole_factor=1.0):
    """Lamina and laminate allowable table for named properties.

    props: ordered dict-like iterable of (name, coupon_values). For
    each property computes the lamina allowable from the sample, the
    laminate allowable after knockdowns, and the basis statement.
    Returns a list of dicts with deterministic keys.
    """
    rows = []
    for name, values in props:
        lamina = allowable_from_sample(values, basis)
        laminate, combined = knockdown(
            lamina, env_factor, bvid_factor, hole_factor
        )
        rows.append({
            "property": name,
            "basis": basis,
            "lamina_allowable": lamina,
            "combined_knockdown": combined,
            "laminate_allowable": laminate,
            "statement": basis_statement(basis),
        })
    return rows
