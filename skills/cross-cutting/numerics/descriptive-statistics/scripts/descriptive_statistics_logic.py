"""Descriptive statistics for a sample of engineering measurements.

Pure stdlib summary statistics: location (mean, median), spread (range,
sample and population variance and standard deviation), rank positions
(quartiles and interquartile range by linear interpolation, five-number
summary), relative spread (coefficient of variation), and 1.5-IQR outlier
flagging. No model fitting, no inference, no sampling, no RNG: inputs are
full samples and every function is deterministic.
"""

from math import floor, ceil, sqrt

# Outlier rule factor: fences sit at q1 - IQR_FACTOR * iqr and
# q3 + IQR_FACTOR * iqr; values strictly outside the fences are flagged.
IQR_FACTOR = 1.5


def mean(sample):
    """Arithmetic mean of the sample. ValueError on an empty sample."""
    if len(sample) == 0:
        raise ValueError("sample must not be empty")
    return sum(sample) / len(sample)


def median(sample):
    """Median of the sample; even counts average the two middle values."""
    if len(sample) == 0:
        raise ValueError("sample must not be empty")
    ordered = sorted(sample)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def data_range(sample):
    """Range of the sample: max - min. ValueError on an empty sample."""
    if len(sample) == 0:
        raise ValueError("sample must not be empty")
    return max(sample) - min(sample)


def variance(sample, ddof=1):
    """Sample variance sum((x - mean)^2) / (n - ddof), ddof default 1."""
    n = len(sample)
    if n == 0:
        raise ValueError("sample must not be empty")
    if n - ddof <= 0:
        raise ValueError("n - ddof must be positive")
    m = mean(sample)
    return sum((x - m) ** 2 for x in sample) / (n - ddof)


def std_dev(sample, ddof=1):
    """Standard deviation: square root of the variance at the given ddof."""
    return sqrt(variance(sample, ddof))


def percentile(sample, p):
    """Linear-interpolation percentile at rank p * (n - 1) on the sample.

    The sample is ordered internally, the rank r = p * (n - 1) splits
    into a lower index floor(r), an upper index ceil(r) and a fraction
    r - floor(r); the value is the linear blend of the two ranked
    entries. ValueError when p is outside [0, 1] or the sample is empty.
    """
    n = len(sample)
    if n == 0:
        raise ValueError("sample must not be empty")
    if p < 0.0 or p > 1.0:
        raise ValueError("p must lie in [0, 1]")
    ordered = sorted(sample)
    rank = p * (n - 1)
    lower = floor(rank)
    upper = ceil(rank)
    frac = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * frac


def quartiles(sample):
    """Quartiles {q1, q2, q3} by percentile at 0.25, 0.5 and 0.75."""
    return {
        "q1": percentile(sample, 0.25),
        "q2": percentile(sample, 0.5),
        "q3": percentile(sample, 0.75),
    }


def interquartile_range(sample):
    """Interquartile range: q3 - q1 by the linear-interpolation quartiles."""
    q = quartiles(sample)
    return q["q3"] - q["q1"]


def five_number_summary(sample):
    """Five-number summary {min, q1, median, q3, max} of the sample."""
    if len(sample) == 0:
        raise ValueError("sample must not be empty")
    return {
        "min": min(sample),
        "q1": percentile(sample, 0.25),
        "median": median(sample),
        "q3": percentile(sample, 0.75),
        "max": max(sample),
    }


def coefficient_of_variation(sample):
    """Relative spread as a fraction: std (ddof=1) / mean.

    ValueError when the mean is zero (division guard) or the sample is
    too small for a ddof=1 standard deviation (n < 2).
    """
    m = mean(sample)
    if m == 0.0:
        raise ValueError("coefficient of variation is undefined for zero mean")
    return std_dev(sample, 1) / m


def outlier_indices_iqr(sample):
    """Indices (original order) of values outside the 1.5-IQR fences.

    A value is an outlier when it is strictly below q1 - IQR_FACTOR * iqr
    or strictly above q3 + IQR_FACTOR * iqr; a value exactly on a fence
    is not flagged.
    """
    q = quartiles(sample)
    iqr = q["q3"] - q["q1"]
    lower_fence = q["q1"] - IQR_FACTOR * iqr
    upper_fence = q["q3"] + IQR_FACTOR * iqr
    return [
        i for i, x in enumerate(sample)
        if x < lower_fence or x > upper_fence
    ]


def summary(sample):
    """Full descriptive-statistics report as a dict.

    Keys: n, mean, median, min, max, range, sample_variance, sample_std,
    q1, q3, iqr, five_number_summary, coefficient_of_variation,
    outlier_indices, outlier_values. ValueErrors from the individual
    measures propagate unchanged.
    """
    q = quartiles(sample)
    iqr = q["q3"] - q["q1"]
    outliers = outlier_indices_iqr(sample)
    return {
        "n": len(sample),
        "mean": mean(sample),
        "median": q["q2"],
        "min": min(sample),
        "max": max(sample),
        "range": max(sample) - min(sample),
        "sample_variance": variance(sample, 1),
        "sample_std": std_dev(sample, 1),
        "q1": q["q1"],
        "q3": q["q3"],
        "iqr": iqr,
        "five_number_summary": five_number_summary(sample),
        "coefficient_of_variation": coefficient_of_variation(sample),
        "outlier_indices": outliers,
        "outlier_values": [sample[i] for i in outliers],
    }
