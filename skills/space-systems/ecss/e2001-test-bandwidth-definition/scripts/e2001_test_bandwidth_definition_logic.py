#!/usr/bin/env python3
"""Multipactor test bandwidth definition -- ECSS-E-ST-20-01C clause 6.4.1.

Paraphrased, implementable procedure (no standard text is reproduced):

A multipactor test is run at one radio-frequency point, yet the verification
statement is made about a band. This module makes the covered band explicit
and checkable.

Physical basis used for the extrapolation: for a fixed critical gap the
multipactor onset threshold of a component tracks the frequency-gap product,
and in the parallel-plate first-order description the threshold power grows
with that product raised to a fixed exponent (2.0 by default, project
configurable). A test passed at power ``p_test`` and frequency ``f_test``
therefore verifies a *higher* equivalent power above ``f_test`` and a lower
one below it, so the covered band is bounded from below by the point where
the verified margin falls to the value the activity demands, and from above
by the ratio beyond which extrapolating one field map to another resonance
picture stops being defensible.

Two activities are distinguished, each with its own margin provision and its
own band-edge allowance for build and environment spread:

* qualification -- larger margin, band widened by a band-edge allowance;
* acceptance    -- smaller margin, band taken as declared.

Every public helper validates its inputs and raises ValueError on data that
cannot carry an engineering conclusion. Standard library only, offline,
deterministic.
"""

import math

# --- engineering parameters (project configurable, not standard text) -------

DEFAULT_THRESHOLD_EXPONENT = 2.0
"""Exponent relating multipactor threshold power to the frequency-gap product."""

DEFAULT_UPPER_VALIDITY_RATIO = 1.25
"""Highest f/f_test ratio over which one measured field map is extrapolated."""

REL_TOLERANCE = 1e-9
"""Relative tolerance absorbing floating-point representation error at band
edges. It never widens an engineering limit: it only stops a comparison that
is exact in real arithmetic from failing by a few units in the last place."""

MAX_TILING_STEPS = 1000
"""Guard against a non-advancing tiling loop."""

ACTIVITY_PROVISIONS = {
    "qualification": {"required_margin_db": 6.0, "band_edge_allowance": 0.02},
    "acceptance": {"required_margin_db": 3.0, "band_edge_allowance": 0.0},
}

RESPONSE_ACTIVITIES = tuple(sorted(ACTIVITY_PROVISIONS))


# --- validation helpers -----------------------------------------------------


def _require_positive(value, label):
    """Return ``value`` as a float, or raise ValueError when unusable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return value


def _require_fraction(value, label):
    """Return a non-negative fraction below 1.0, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0 or value >= 1.0:
        raise ValueError("%s must lie in [0.0, 1.0), got %r" % (label, value))
    return value


def validate_operating_band(f_low_hz, f_high_hz):
    """Validate a declared operating band and return it as a float pair."""
    low = _require_positive(f_low_hz, "f_low_hz")
    high = _require_positive(f_high_hz, "f_high_hz")
    if high < low:
        raise ValueError(
            "operating band is inverted: f_high_hz %g below f_low_hz %g" % (high, low)
        )
    return low, high


def activity_provision(activity):
    """Return the margin and band-edge allowance provision for an activity."""
    if not isinstance(activity, str):
        raise ValueError("activity must be a string, got %r" % (activity,))
    key = activity.strip().lower()
    if key not in ACTIVITY_PROVISIONS:
        raise ValueError(
            "unknown test activity %r; expected one of %s"
            % (activity, ", ".join(RESPONSE_ACTIVITIES))
        )
    provision = dict(ACTIVITY_PROVISIONS[key])
    provision["activity"] = key
    return provision


# --- threshold extrapolation ------------------------------------------------


def threshold_scaling_factor(f_hz, f_test_hz, exponent=DEFAULT_THRESHOLD_EXPONENT):
    """Ratio of the onset threshold at ``f_hz`` to the one held at ``f_test_hz``."""
    f_hz = _require_positive(f_hz, "f_hz")
    f_test_hz = _require_positive(f_test_hz, "f_test_hz")
    if isinstance(exponent, bool) or not isinstance(exponent, (int, float)):
        raise ValueError("exponent must be a real number, got %r" % (exponent,))
    exponent = float(exponent)
    if exponent <= 0.0:
        raise ValueError("exponent must be strictly positive, got %r" % (exponent,))
    return (f_hz / f_test_hz) ** exponent


def verified_margin_db(
    f_hz,
    f_test_hz,
    p_test_w,
    p_operating_w,
    exponent=DEFAULT_THRESHOLD_EXPONENT,
):
    """Margin in dB that a pass at (f_test_hz, p_test_w) verifies at ``f_hz``."""
    p_test_w = _require_positive(p_test_w, "p_test_w")
    p_operating_w = _require_positive(p_operating_w, "p_operating_w")
    scale = threshold_scaling_factor(f_hz, f_test_hz, exponent)
    return 10.0 * math.log10(p_test_w * scale / p_operating_w)


def lower_covered_edge_hz(
    f_test_hz,
    p_test_w,
    p_operating_w,
    required_margin_db,
    exponent=DEFAULT_THRESHOLD_EXPONENT,
):
    """Lowest frequency at which the verified margin still meets the provision."""
    f_test_hz = _require_positive(f_test_hz, "f_test_hz")
    p_test_w = _require_positive(p_test_w, "p_test_w")
    p_operating_w = _require_positive(p_operating_w, "p_operating_w")
    if isinstance(required_margin_db, bool) or not isinstance(
        required_margin_db, (int, float)
    ):
        raise ValueError(
            "required_margin_db must be a real number, got %r" % (required_margin_db,)
        )
    required_margin_db = float(required_margin_db)
    if required_margin_db < 0.0:
        raise ValueError(
            "required_margin_db must not be negative, got %r" % (required_margin_db,)
        )
    if p_test_w <= p_operating_w:
        raise ValueError(
            "p_test_w %g does not exceed p_operating_w %g; a test at or below the "
            "operating power verifies no multipactor margin" % (p_test_w, p_operating_w)
        )
    if isinstance(exponent, bool) or not isinstance(exponent, (int, float)):
        raise ValueError("exponent must be a real number, got %r" % (exponent,))
    exponent = float(exponent)
    if exponent <= 0.0:
        raise ValueError("exponent must be strictly positive, got %r" % (exponent,))
    ratio = (p_operating_w * 10.0 ** (required_margin_db / 10.0) / p_test_w) ** (
        1.0 / exponent
    )
    return f_test_hz * ratio


def covered_band(
    f_test_hz,
    p_test_w,
    p_operating_w,
    required_margin_db,
    exponent=DEFAULT_THRESHOLD_EXPONENT,
    upper_validity_ratio=DEFAULT_UPPER_VALIDITY_RATIO,
):
    """Band a single passed test point covers, as a dictionary.

    Keys: lower_hz, upper_hz, span_hz, covers_test_point, exponent.
    ``span_hz`` is zero when the provision is not met anywhere inside the
    extrapolation-validity window.
    """
    if isinstance(upper_validity_ratio, bool) or not isinstance(
        upper_validity_ratio, (int, float)
    ):
        raise ValueError(
            "upper_validity_ratio must be a real number, got %r" % (upper_validity_ratio,)
        )
    upper_validity_ratio = float(upper_validity_ratio)
    if upper_validity_ratio < 1.0:
        raise ValueError(
            "upper_validity_ratio must be at least 1.0, got %r" % (upper_validity_ratio,)
        )
    lower = lower_covered_edge_hz(
        f_test_hz, p_test_w, p_operating_w, required_margin_db, exponent
    )
    upper = float(f_test_hz) * upper_validity_ratio
    span = upper - lower
    if span < 0.0 or math.isclose(span, 0.0, rel_tol=0.0, abs_tol=REL_TOLERANCE * upper):
        span = 0.0
    return {
        "lower_hz": lower,
        "upper_hz": upper,
        "span_hz": span,
        "covers_test_point": lower <= float(f_test_hz) * (1.0 + REL_TOLERANCE),
        "exponent": float(exponent),
    }


# --- band coverage assessment ----------------------------------------------


def required_coverage_band(f_low_hz, f_high_hz, activity):
    """Declared band widened by the activity's band-edge allowance."""
    low, high = validate_operating_band(f_low_hz, f_high_hz)
    provision = activity_provision(activity)
    allowance = _require_fraction(provision["band_edge_allowance"], "band_edge_allowance")
    return low * (1.0 - allowance), high * (1.0 + allowance)


def _at_or_below(value, limit):
    """True when ``value <= limit`` up to representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOLERANCE)


def _at_or_above(value, limit):
    """True when ``value >= limit`` up to representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOLERANCE)


def assess_band_coverage(
    f_low_hz,
    f_high_hz,
    f_test_hz,
    p_test_w,
    p_operating_w,
    activity,
    exponent=DEFAULT_THRESHOLD_EXPONENT,
    upper_validity_ratio=DEFAULT_UPPER_VALIDITY_RATIO,
):
    """Assess whether one test frequency covers the band for an activity."""
    provision = activity_provision(activity)
    required_low, required_high = required_coverage_band(f_low_hz, f_high_hz, activity)
    band = covered_band(
        f_test_hz,
        p_test_w,
        p_operating_w,
        provision["required_margin_db"],
        exponent,
        upper_validity_ratio,
    )
    findings = []
    if band["span_hz"] <= 0.0:
        findings.append(
            "test point verifies no band: the required %.1f dB margin is not met "
            "inside the extrapolation-validity window" % provision["required_margin_db"]
        )
    if not _at_or_below(band["lower_hz"], required_low):
        findings.append(
            "low band edge uncovered: covered from %.6g Hz, band starts at %.6g Hz"
            % (band["lower_hz"], required_low)
        )
    if not _at_or_above(band["upper_hz"], required_high):
        findings.append(
            "high band edge uncovered: covered to %.6g Hz, band ends at %.6g Hz"
            % (band["upper_hz"], required_high)
        )
    return {
        "activity": provision["activity"],
        "required_margin_db": provision["required_margin_db"],
        "required_low_hz": required_low,
        "required_high_hz": required_high,
        "covered": band,
        "findings": findings,
        "compliant": not findings,
    }


def minimum_test_frequency_set(
    f_low_hz,
    f_high_hz,
    p_test_w,
    p_operating_w,
    activity,
    exponent=DEFAULT_THRESHOLD_EXPONENT,
    upper_validity_ratio=DEFAULT_UPPER_VALIDITY_RATIO,
):
    """Ordered minimum set of test frequencies tiling the band for an activity."""
    provision = activity_provision(activity)
    required_low, required_high = required_coverage_band(f_low_hz, f_high_hz, activity)
    reference = lower_covered_edge_hz(
        1.0, p_test_w, p_operating_w, provision["required_margin_db"], exponent
    )
    if isinstance(upper_validity_ratio, bool) or not isinstance(
        upper_validity_ratio, (int, float)
    ):
        raise ValueError(
            "upper_validity_ratio must be a real number, got %r" % (upper_validity_ratio,)
        )
    upper_validity_ratio = float(upper_validity_ratio)
    if upper_validity_ratio < 1.0:
        raise ValueError(
            "upper_validity_ratio must be at least 1.0, got %r" % (upper_validity_ratio,)
        )
    coverage_ratio = upper_validity_ratio / reference
    if coverage_ratio <= 1.0 + REL_TOLERANCE:
        raise ValueError(
            "a single test point covers no net bandwidth (coverage ratio %.6g); "
            "raise p_test_w or relax the extrapolation window" % coverage_ratio
        )
    frequencies = []
    edge = required_low
    steps = 0
    while not _at_or_above(edge, required_high):
        steps += 1
        if steps > MAX_TILING_STEPS:
            raise ValueError(
                "band tiling did not converge within %d steps" % MAX_TILING_STEPS
            )
        f_test = edge / reference
        frequencies.append(f_test)
        edge = f_test * upper_validity_ratio
    if not frequencies:
        f_test = required_low / reference
        frequencies.append(f_test)
    return frequencies


def summarize_bandwidth_definition(assessment):
    """Render an assessment dictionary as ordered human-readable lines."""
    if not isinstance(assessment, dict) or "covered" not in assessment:
        raise ValueError("assessment must be the mapping returned by assess_band_coverage")
    covered = assessment["covered"]
    lines = [
        "activity: %s (required margin %.1f dB)"
        % (assessment["activity"], assessment["required_margin_db"]),
        "band to cover: %.6g Hz to %.6g Hz"
        % (assessment["required_low_hz"], assessment["required_high_hz"]),
        "covered by test point: %.6g Hz to %.6g Hz (span %.6g Hz)"
        % (covered["lower_hz"], covered["upper_hz"], covered["span_hz"]),
        "verdict: %s" % ("covered" if assessment["compliant"] else "not covered"),
    ]
    lines.extend("finding: %s" % item for item in assessment["findings"])
    return lines
