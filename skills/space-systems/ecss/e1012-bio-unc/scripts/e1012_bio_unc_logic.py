#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §11.6 — biological-effects uncertainty assessment (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the space
radiation standard's biological-uncertainty clause requires identifying five
independent uncertainty sources — radiation quality factor, dose-and-dose-rate
effectiveness factor (DDREF), cancer-risk coefficient from epidemiology,
inter-population transfer model, and dosimetry and transport — expressing each
as a log-space sigma (geometric standard deviation), combining them in quadrature
in natural-log space to obtain the total uncertainty, and deriving the 95%
confidence interval around the point-estimate risk using the lognormal model.
This module implements component validation, quadrature combination, 95% CI
derivation, qualitative level labelling, completeness checking, and a one-call
full-assessment entry point.  It does not implement radiation transport, risk-
coefficient derivation, or epidemiological modelling.
"""

import math
from collections import namedtuple

# ---------------------------------------------------------------------------
# Required uncertainty source types per §11.6
# Each source must appear in the uncertainty budget for the assessment to be
# considered complete.  Unknown source types are rejected.
# ---------------------------------------------------------------------------
REQUIRED_SOURCES = frozenset([
    "quality_factor",    # radiation quality factor Q(L) uncertainty (high-LET)
    "ddref",             # dose-and-dose-rate effectiveness factor uncertainty
    "risk_coefficient",  # cancer-risk coefficient statistical uncertainty
    "transfer_model",    # inter-population cancer-risk transfer uncertainty
    "dosimetry",         # radiation transport and physical dosimetry uncertainty
])

# ---------------------------------------------------------------------------
# Sigma-log thresholds that map combined uncertainty to a qualitative level.
# Each threshold is derived from the 95th-percentile CI factor at z = 1.645:
#   threshold = ln(factor) / 1.645
# Boundaries: ×2 → low/moderate; ×4 → moderate/high; ×8 → high/very_high.
# ---------------------------------------------------------------------------
_Z95 = 1.6449  # standard normal quantile at 95th percentile (A&S 26.2.17)
_SIGMA_LOW      = math.log(2.0) / _Z95   # ~0.4214 — upper 95th pct factor < 2
_SIGMA_MODERATE = math.log(4.0) / _Z95   # ~0.8428 — upper 95th pct factor < 4
_SIGMA_HIGH     = math.log(8.0) / _Z95   # ~1.2641 — upper 95th pct factor < 8


UncertaintyComponent = namedtuple(
    "UncertaintyComponent",
    ["source_type", "sigma_log", "label"],
)
"""Named container for one uncertainty source.

Fields:
  source_type (str): one of the five identifiers in REQUIRED_SOURCES.
  sigma_log   (float): positive natural-log-space sigma (ln of the GSD).
  label       (str): free-text description of the source and its basis.
"""


def validate_component(component):
    """Check that a component is structurally and numerically valid.

    Returns (True, None) on success or (False, reason_string) on the first
    detected failure.  Does not raise.
    """
    if not isinstance(component, UncertaintyComponent):
        return False, "component must be an UncertaintyComponent namedtuple"
    if component.source_type not in REQUIRED_SOURCES:
        return (
            False,
            "unrecognized source_type %r — must be one of: %s"
            % (component.source_type, ", ".join(sorted(REQUIRED_SOURCES))),
        )
    if not isinstance(component.sigma_log, (int, float)):
        return False, "sigma_log must be a numeric value; got %r" % type(component.sigma_log)
    if not math.isfinite(component.sigma_log):
        return False, "sigma_log must be finite; got %r" % component.sigma_log
    if component.sigma_log <= 0:
        return False, "sigma_log must be positive; got %r" % component.sigma_log
    return True, None


def check_completeness(components):
    """Return the set of required source types not covered by the provided list.

    An empty set means all five required sources are present.  Any element in
    the returned set represents a source omitted from the uncertainty budget,
    which makes the combined confidence interval narrower than §11.6 requires.
    Does not raise; performs no structural validation.
    """
    provided = {c.source_type for c in components}
    return REQUIRED_SOURCES - provided


def combine_uncertainties(components):
    """Combine independent uncertainty components in quadrature in log space.

    Each component's sigma_log is squared, summed, and the square root taken.
    This is the correct rule for independent lognormal variables: the combined
    geometric standard deviation's ln equals the root-sum-square of the
    individual ln(GSD) values.

    Returns the combined sigma_log (float, > 0).
    Raises ValueError if the list is empty or any component fails validation.
    """
    if not components:
        raise ValueError("at least one uncertainty component is required")
    for c in components:
        ok, reason = validate_component(c)
        if not ok:
            raise ValueError("invalid component: " + reason)
    return math.sqrt(sum(c.sigma_log ** 2 for c in components))


def _normal_quantile(p):
    """Standard normal quantile via Abramowitz & Stegun rational approximation 26.2.17.

    Accurate to ~4.5 × 10⁻⁴ absolute error for 0 < p < 1.
    """
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be in the open interval (0, 1); got %r" % p)
    if p < 0.5:
        return -_normal_quantile(1.0 - p)
    t = math.sqrt(-2.0 * math.log(1.0 - p))
    c = (2.515517, 0.802853, 0.010328)
    d = (1.432788, 0.189269, 0.001308)
    num = c[0] + c[1] * t + c[2] * t * t
    den = 1.0 + d[0] * t + d[1] * t * t + d[2] * t * t * t
    return t - num / den


def confidence_interval(point_estimate, sigma_log, percentile=0.95):
    """Lognormal two-sided confidence interval around a positive point estimate.

    The upper bound is point_estimate × exp(z × sigma_log) and the lower
    bound is point_estimate / exp(z × sigma_log), where z is the one-sided
    standard normal quantile at the given percentile.  For percentile = 0.95,
    this gives the 5th–95th percentile range.

    Args:
        point_estimate (float): positive risk value (e.g. lifetime cancer risk).
        sigma_log      (float): positive combined log-space sigma.
        percentile     (float): desired one-sided percentile, default 0.95.

    Returns:
        (lower, upper) tuple of floats.

    Raises ValueError for non-positive or out-of-range inputs.
    """
    if not isinstance(point_estimate, (int, float)) or not math.isfinite(point_estimate):
        raise ValueError("point_estimate must be a finite number; got %r" % point_estimate)
    if point_estimate <= 0:
        raise ValueError("point_estimate must be positive; got %r" % point_estimate)
    if not isinstance(sigma_log, (int, float)) or not math.isfinite(sigma_log):
        raise ValueError("sigma_log must be a finite number; got %r" % sigma_log)
    if sigma_log <= 0:
        raise ValueError("sigma_log must be positive; got %r" % sigma_log)
    if not (0.0 < percentile < 1.0):
        raise ValueError("percentile must be in the open interval (0, 1); got %r" % percentile)
    z = _normal_quantile(percentile)
    factor = math.exp(z * sigma_log)
    return point_estimate / factor, point_estimate * factor


def label_uncertainty_level(sigma_log):
    """Map a combined sigma_log to a qualitative uncertainty level string.

    Boundaries are anchored to 95th-percentile CI factors of 2, 4, and 8:
      sigma_log < ln(2)/1.645 → 'low'        (upper bound < 2× median)
      sigma_log < ln(4)/1.645 → 'moderate'   (upper bound 2–4× median)
      sigma_log < ln(8)/1.645 → 'high'       (upper bound 4–8× median)
      sigma_log >= ln(8)/1.645 → 'very_high' (upper bound ≥ 8× median)

    sigma_log must be a positive finite number; otherwise raises ValueError.
    """
    if not isinstance(sigma_log, (int, float)) or not math.isfinite(sigma_log):
        raise ValueError("sigma_log must be a finite number; got %r" % sigma_log)
    if sigma_log <= 0:
        raise ValueError("sigma_log must be positive; got %r" % sigma_log)
    if sigma_log < _SIGMA_LOW:
        return "low"
    if sigma_log < _SIGMA_MODERATE:
        return "moderate"
    if sigma_log < _SIGMA_HIGH:
        return "high"
    return "very_high"


def full_assessment(point_estimate, components, percentile=0.95):
    """Run a complete §11.6 biological-effects uncertainty assessment.

    Combines all components in quadrature, derives the confidence interval,
    labels the uncertainty level, and checks for missing required sources.

    Args:
        point_estimate (float): positive risk point estimate.
        components     (list of UncertaintyComponent): uncertainty sources.
        percentile     (float): one-sided CI percentile, default 0.95.

    Returns a dict with keys:
        combined_sigma_log  (float)  — root-sum-square of component sigmas
        lower_ci            (float)  — lower confidence bound
        upper_ci            (float)  — upper confidence bound
        uncertainty_level   (str)    — 'low'|'moderate'|'high'|'very_high'
        missing_sources     (frozenset[str]) — required sources not provided

    Raises ValueError for invalid inputs (delegated to sub-functions).
    """
    combined = combine_uncertainties(components)
    lower, upper = confidence_interval(point_estimate, combined, percentile)
    missing = check_completeness(components)
    return {
        "combined_sigma_log": combined,
        "lower_ci": lower,
        "upper_ci": upper,
        "uncertainty_level": label_uncertainty_level(combined),
        "missing_sources": missing,
    }
