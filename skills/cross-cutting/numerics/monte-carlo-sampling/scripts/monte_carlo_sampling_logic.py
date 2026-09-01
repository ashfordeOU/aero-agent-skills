"""Monte Carlo sampling logic (seeded random draws, sample statistics).

Paraphrase of the standard Monte Carlo uncertainty evaluation method
(JCGM 101, GUM supplement 1), which estimates the distribution of an
output quantity by drawing many random input samples and applying the
model function to each draw. NACA Report 824 is the pack's
public-domain anchor (standards-map.yaml); the Monte Carlo method
itself is generic numerical methodology, not RTCA or SAE content.

Conventions: draw_samples draws n independent pseudo-random numbers
from a uniform distribution on [low, high] with a fixed seed so the
draw is reproducible. sample_mean and sample_stddev are the sample
mean and the sample standard deviation (n - 1 denominator).
percentile returns the p-th percentile with linear interpolation
between order statistics (numpy-style linear method). confidence_interval
returns the two-tailed percentile interval for a level such as 0.95
(percentiles 2.5 and 97.5). histogram bins the samples into k
equal-width bins over the sample range and returns the counts and the
bin edges. propagate_samples draws uniform inputs, applies func to
each draw, and reports the sample statistics of the transformed
outputs.

Raises ValueError on an empty sample list, a sample size below 1, a
high bound at or below the low bound, a percentile outside [0, 100],
a confidence level outside (0, 1), a bin count below 1, or a constant
sample set passed to histogram (zero range cannot be binned).
"""

import math
import random


def draw_samples(seed, n, low=0.0, high=1.0):
    """Draw n uniform pseudo-random samples on [low, high] with a seed.

    Reproducible: the same seed always yields the same sequence.
    Raises ValueError when n < 1 or high <= low.
    """
    if n < 1:
        raise ValueError("sample size n must be >= 1: got n=%r" % (n,))
    if high <= low:
        raise ValueError(
            "high bound must exceed low bound: got low=%r high=%r" % (low, high)
        )
    rng = random.Random(seed)
    return [rng.uniform(low, high) for _ in range(n)]


def sample_mean(samples):
    """Arithmetic mean of the samples. Raises ValueError when empty."""
    if not samples:
        raise ValueError("samples must be non-empty")
    return sum(samples) / len(samples)


def sample_stddev(samples):
    """Sample standard deviation (n - 1 denominator)."""

    if len(samples) < 2:
        raise ValueError("sample standard deviation needs at least 2 samples")
    mean = sample_mean(samples)
    var = sum((x - mean) ** 2 for x in samples) / (len(samples) - 1)
    return math.sqrt(var)


def percentile(samples, p):
    """p-th percentile of the samples, linear interpolation method.

    Sorts a copy; the interpolation index is p / 100 * (n - 1) with
    linear interpolation between the neighboring order statistics.
    Raises ValueError when the sample list is empty or p is outside
    [0, 100].
    """
    if not samples:
        raise ValueError("samples must be non-empty")
    if not (0.0 <= p <= 100.0):
        raise ValueError("percentile p must be in [0, 100]: got p=%r" % (p,))
    ordered = sorted(samples)
    n = len(ordered)
    idx = (p / 100.0) * (n - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    frac = idx - lo
    return ordered[lo] + frac * (ordered[hi] - ordered[lo])


def confidence_interval(samples, level=0.95):
    """Two-tailed percentile confidence interval for a level.

    Returns (low, high): the percentiles at (1 - level) / 2 and
    1 - (1 - level) / 2. Raises ValueError when the sample list is
    empty or level is outside (0, 1).
    """
    if not samples:
        raise ValueError("samples must be non-empty")
    if not (0.0 < level < 1.0):
        raise ValueError("confidence level must be in (0, 1): got level=%r" % (level,))
    tail = (1.0 - level) / 2.0
    return (percentile(samples, tail * 100.0), percentile(samples, (1.0 - tail) * 100.0))


def histogram(samples, bins=10):
    """Equal-width histogram of the samples: (counts, edges).

    Edges span the sample range with bins equal-width intervals;
    counts are the number of samples per bin, last edge inclusive.
    Raises ValueError on an empty sample list, bins below 1, or a
    constant sample set (zero range).
    """
    if not samples:
        raise ValueError("samples must be non-empty")
    if bins < 1:
        raise ValueError("bins must be >= 1: got bins=%r" % (bins,))
    lo = min(samples)
    hi = max(samples)
    if lo == hi:
        raise ValueError("cannot histogram a constant sample set")
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins + 1)]
    counts = [0] * bins
    for x in samples:
        idx = int((x - lo) / width)
        if idx >= bins:
            idx = bins - 1  # the maximum sample lands in the last bin
        counts[idx] += 1
    return (counts, edges)


def propagate_samples(seed, n, low, high, func, level=0.95):
    """Draw uniform inputs, apply func, and summarize the outputs.

    Returns a dict with 'samples' (the transformed draws), 'mean',
    'stddev', and the confidence interval 'low' / 'high' at the given
    level. Raises ValueError for the same conditions as the underlying
    functions.
    """
    draws = draw_samples(seed, n, low, high)
    outputs = [func(x) for x in draws]
    lo, hi = confidence_interval(outputs, level)
    return {
        "samples": outputs,
        "mean": sample_mean(outputs),
        "stddev": sample_stddev(outputs),
        "low": lo,
        "high": hi,
    }
