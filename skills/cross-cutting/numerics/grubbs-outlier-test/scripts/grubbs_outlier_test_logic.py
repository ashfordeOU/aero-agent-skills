"""Grubbs outlier test logic (pure stdlib).

Single-outlier test for a normally distributed sample: form G as the
largest absolute deviation from the sample mean divided by the sample
standard deviation (n-1 denominator) and compare it with the two-sided
0.05 critical value for the sample size from an embedded reference
table, with linear interpolation between listed sample sizes.
"""

import math

# Two-sided alpha 0.05 critical G values (documented reference table,
# listed by sample size n). n below 3 or above 50 has no table support.
GRUBBS_CRIT_05 = {
    3: 1.155,
    4: 1.481,
    5: 1.715,
    6: 1.887,
    7: 2.020,
    8: 2.032,
    9: 2.215,
    10: 2.290,
    12: 2.412,
    15: 2.549,
    20: 2.709,
    30: 2.908,
    40: 3.036,
    50: 3.128,
}

# Sorted table keys, precomputed once for interpolation lookups.
GRUBBS_SORTED_SIZES = tuple(sorted(GRUBBS_CRIT_05))

# Default two-sided significance level (alpha) of the test.
SIGNIFICANCE = 0.05

# Smallest and largest supported sample sizes.
MIN_SAMPLE_SIZE = 3
MAX_SAMPLE_SIZE = 50


def _as_numbers(sample):
    """Return the sample as a list of floats; reject non-numeric values."""
    try:
        return [float(x) for x in sample]
    except (TypeError, ValueError):
        raise ValueError("sample values must be numeric") from None


def _sample_std(data, mean):
    """Sample standard deviation (n-1 denominator) of a float list."""
    n = len(data)
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    return math.sqrt(variance)


def grubbs_statistic(sample):
    """Return (g, mean, std, candidate, candidate_idx) for one sample.

    g is the Grubbs statistic max(|x - mean|) / std with the sample
    standard deviation (n-1 denominator). candidate is the observation
    farthest from the mean (first occurrence on a tie) and
    candidate_idx its position. Raises ValueError for fewer than 3
    values, non-numeric values, or a zero standard deviation (all
    values identical).
    """
    data = _as_numbers(sample)
    n = len(data)
    if n < MIN_SAMPLE_SIZE:
        raise ValueError("grubbs statistic needs at least 3 values")
    mean = sum(data) / n
    std = _sample_std(data, mean)
    if std == 0.0:
        raise ValueError("zero standard deviation: all sample values are identical")
    deviations = [abs(x - mean) for x in data]
    max_dev = max(deviations)
    candidate_idx = deviations.index(max_dev)
    candidate = data[candidate_idx]
    g = max_dev / std
    return g, mean, std, candidate, candidate_idx


def grubbs_critical(n, alpha=SIGNIFICANCE):
    """Two-sided critical G for sample size n at the given alpha.

    Exact table hit for a listed n; linear interpolation between the
    nearest listed sample sizes otherwise. Only alpha 0.05 is
    supported. Raises ValueError for alpha other than 0.05, a
    non-integral sample size, or n outside [3, 50].
    """
    if alpha != SIGNIFICANCE:
        raise ValueError("only alpha 0.05 is supported by the embedded table")
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        raise ValueError("sample size n must be an integer")
    if not float(n).is_integer():
        raise ValueError("sample size n must be an integer")
    n_int = int(n)
    if n_int < MIN_SAMPLE_SIZE or n_int > MAX_SAMPLE_SIZE:
        raise ValueError("sample size n must be between 3 and 50")
    if n_int in GRUBBS_CRIT_05:
        return GRUBBS_CRIT_05[n_int]
    for lo, hi in zip(GRUBBS_SORTED_SIZES, GRUBBS_SORTED_SIZES[1:]):
        if lo < n_int < hi:
            crit_lo = GRUBBS_CRIT_05[lo]
            crit_hi = GRUBBS_CRIT_05[hi]
            return crit_lo + (crit_hi - crit_lo) * (n_int - lo) / (hi - lo)
    raise ValueError("sample size n must be a listed or interpolable size")


def grubbs_test(sample, alpha=SIGNIFICANCE):
    """Run the Grubbs single-outlier test; return the result dict.

    Dict keys: g, critical, verdict ("reject" or "no-outlier"),
    rejected_value, rejected_index, mean, std. The verdict is "reject"
    when g > critical; rejected_value and rejected_index are then the
    flagged observation and its position, otherwise None. Raises
    ValueError on non-physical inputs as documented in
    grubbs_statistic and grubbs_critical.
    """
    g, mean, std, candidate, candidate_idx = grubbs_statistic(sample)
    n = len(_as_numbers(sample))
    critical = grubbs_critical(n, alpha)
    reject = g > critical
    return {
        "g": g,
        "critical": critical,
        "verdict": "reject" if reject else "no-outlier",
        "rejected_value": candidate if reject else None,
        "rejected_index": candidate_idx if reject else None,
        "mean": mean,
        "std": std,
    }


def grubbs_remove_outliers(sample, alpha=SIGNIFICANCE):
    """Remove flagged outliers iteratively; return (clean_list, removed_list).

    Each pass applies grubbs_test to the current sample, removes the
    flagged value when the verdict is "reject", and repeats until no
    outlier remains or fewer than 3 values are left. An all-identical
    remainder (zero standard deviation) carries no outlier and stops
    the loop. Raises ValueError when the input has fewer than 3 values
    or contains non-numeric entries.
    """
    data = _as_numbers(sample)
    if len(data) < MIN_SAMPLE_SIZE:
        raise ValueError("outlier removal needs at least 3 values")
    removed = []
    while len(data) >= MIN_SAMPLE_SIZE:
        mean = sum(data) / len(data)
        if _sample_std(data, mean) == 0.0:
            break
        result = grubbs_test(data, alpha)
        if result["verdict"] != "reject":
            break
        index = result["rejected_index"]
        removed.append(data[index])
        del data[index]
    return data, removed
