#!/usr/bin/env python3
"""ADCS pointing error budget assembly (pure stdlib, offline).

Combines independent 1-sigma pointing error contributors from the
attitude determination and control system (star tracker determination
noise, gyro propagation, control deadband, jitter, thermal distortion)
with the root-sum-square convention, converts to 3-sigma, judges the
result against a pointing requirement, allocates the remaining budget
to a not-yet-sized contributor, and ranks contributors by variance
share. All functions are unit-agnostic; the ADCS convention is arcsec.

Functions
---------
rss_pointing_error(components_1sigma) -> float
three_sigma_error(components_1sigma) -> float
three_sigma_verdict(components_1sigma, requirement_3sigma) -> bool
allocate_error_budget(requirement_3sigma, fixed_components_1sigma) -> float
dominant_error_source(components_1sigma) -> tuple
pointing_error_budget(components_1sigma, requirement_3sigma) -> dict

ValueError is raised for an empty contributor list, any negative
contributor, a non-positive requirement, a negative radicand in the
allocation (fixed contributors already exceed the 1-sigma budget), and
an all-zero contributor list in the dominant-source ranking (no
variance to rank).
"""

from math import sqrt

__all__ = [
    "rss_pointing_error",
    "three_sigma_error",
    "three_sigma_verdict",
    "allocate_error_budget",
    "dominant_error_source",
    "pointing_error_budget",
]


def _as_pairs(components_1sigma, allow_empty=False):
    """Return (key, value) pairs with sign checks.

    A dict input keeps insertion order and yields (name, value) pairs;
    any other sequence yields (index, value) pairs. Every value must be
    non-negative. An empty input raises unless allow_empty is True.
    """
    if isinstance(components_1sigma, dict):
        items = list(components_1sigma.items())
    else:
        items = list(enumerate(components_1sigma))
    if not items and not allow_empty:
        raise ValueError("components_1sigma must not be empty")
    for key, value in items:
        if value < 0:
            raise ValueError(
                "component %r must be non-negative, got %r" % (key, value)
            )
    return items


def _total_variance(components_1sigma):
    """Sum of squared 1-sigma values after validation."""
    items = _as_pairs(components_1sigma)
    return sum(value * value for _, value in items), items


def rss_pointing_error(components_1sigma):
    """Root-sum-square of independent 1-sigma error contributors.

    rss = sqrt(sum(c_i^2)). Accepts a sequence of 1-sigma values or a
    dict of {name: 1-sigma value}.
    """
    variance, _ = _total_variance(components_1sigma)
    return sqrt(variance)


def three_sigma_error(components_1sigma):
    """3-sigma pointing error: 3 times the RSS 1-sigma value."""
    return 3.0 * rss_pointing_error(components_1sigma)


def three_sigma_verdict(components_1sigma, requirement_3sigma):
    """True when the 3-sigma error meets the 3-sigma requirement."""
    if requirement_3sigma <= 0:
        raise ValueError(
            "requirement_3sigma must be positive, got %r" % (requirement_3sigma,)
        )
    return three_sigma_error(components_1sigma) <= requirement_3sigma


def allocate_error_budget(requirement_3sigma, fixed_components_1sigma):
    """1-sigma budget left for ONE remaining contributor.

    sqrt((requirement_3sigma / 3)^2 - sum(fixed^2)). Raises ValueError
    when the fixed contributors already exceed the 1-sigma budget (the
    radicand would be negative). An empty fixed list returns the full
    1-sigma budget requirement_3sigma / 3.
    """
    if requirement_3sigma <= 0:
        raise ValueError(
            "requirement_3sigma must be positive, got %r" % (requirement_3sigma,)
        )
    items = _as_pairs(fixed_components_1sigma, allow_empty=True)
    one_sigma_budget = requirement_3sigma / 3.0
    fixed_variance = sum(value * value for _, value in items)
    radicand = one_sigma_budget * one_sigma_budget - fixed_variance
    if radicand < 0:
        raise ValueError(
            "fixed contributors already exceed the 1-sigma budget of %r"
            % (one_sigma_budget,)
        )
    return sqrt(radicand)


def dominant_error_source(components_1sigma):
    """Largest-variance contributor and its share of total variance.

    Returns (index, name or None, variance_share). Index is the 0-based
    position in the input order; name is the dict key when a dict is
    passed and None for a plain sequence. The share is c_i^2 divided by
    the sum of squared values. On a variance tie the first contributor
    in input order wins.
    """
    variance, items = _total_variance(components_1sigma)
    if variance == 0:
        raise ValueError("components_1sigma must not be all zero")
    best = max(range(len(items)), key=lambda i: items[i][1] * items[i][1])
    key, value = items[best]
    name = key if isinstance(components_1sigma, dict) else None
    share = value * value / variance
    return (best, name, share)


def pointing_error_budget(components_1sigma, requirement_3sigma):
    """Assemble the full pointing error budget as a dict.

    Keys: rss_1sigma, rss_3sigma, requirement_met, dominant_index,
    dominant_variance_share, component_variance_shares (a list aligned
    with the input order).
    """
    rss_1 = rss_pointing_error(components_1sigma)
    variance, items = _total_variance(components_1sigma)
    shares = [value * value / variance for _, value in items]
    dom_index, _, dom_share = dominant_error_source(components_1sigma)
    return {
        "rss_1sigma": rss_1,
        "rss_3sigma": 3.0 * rss_1,
        "requirement_met": three_sigma_verdict(
            components_1sigma, requirement_3sigma
        ),
        "dominant_index": dom_index,
        "dominant_variance_share": dom_share,
        "component_variance_shares": shares,
    }
