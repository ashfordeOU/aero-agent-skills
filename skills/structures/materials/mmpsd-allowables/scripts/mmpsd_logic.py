#!/usr/bin/env python3
"""MMPDS metallic allowables logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, mmpsd: gated true):
MMPDS (successor to MIL-HDBK-5) publishes statistically based
metallic material design allowables. A-basis: 95% confidence that
99% of the population exceeds the value; B-basis: 95% confidence
that 90% exceeds the value. The allowable is the sample mean minus
a one-sided normal tolerance k-factor times the sample standard
deviation. This module implements the Owen/Odeh k-factor
approximation, common minimum sample counts, and design-value
sanity checks. Design-value tables are never reproduced here.
"""

import math
import statistics

CONF_95_Z = 1.6448536269514722  # z for 95% confidence (one-sided)
BASIS_CONTENT_Z = {
    "A": 2.3263478740408408,  # z for 99% content
    "B": 1.2815515655446004,  # z for 90% content
}


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

    Verify against the current MMPDS edition. Unknown basis raises
    ValueError.
    """
    if basis not in BASIS_CONTENT_Z:
        raise ValueError("basis must be 'A' or 'B': %r" % (basis,))
    return {"A": 10, "B": 6}[basis]


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


def design_value_sanity(allowable, mean, basis):
    """Sanity check: the allowable must be positive and below the mean."""
    return 0.0 < allowable < mean
