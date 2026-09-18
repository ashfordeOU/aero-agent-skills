#!/usr/bin/env python3
"""Output current limitation range against its protection thresholds.

Anchor: ECSS-E-ST-20-20C clause 5.2.3.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A current limiter does not hold one current. It holds a current that
moves with temperature, with the tolerance of the sense element and the
reference, with ageing and with total dose, and it differs from unit to
unit. The clause fixes a window: wherever the limitation current lands
across all of that, it has to stay between a defined minimum protection
threshold and a defined maximum protection threshold.

    threshold_min_a   below this the protection is too eager: a healthy
                      load can be limited, and the downstream equipment
                      is denied current it was designed to draw
    threshold_max_a   above this the protection is too slack: the fault
                      current the harness and the load carry is larger
                      than the design assumed

So the object of the check is a RANGE, not a number. The range is built
by stacking every contributor onto the nominal setpoint, either
arithmetically (each contributor at its own worst case simultaneously)
or by root-sum-square (independent contributors combined statistically).
Arithmetic is the bounding stack; root-sum-square is admissible only
when the contributors really are independent, and it always reports a
narrower band, so the method is declared with the result.

Two further separations matter and are not implied by the thresholds:

    the LOWER edge of the range has to stay above the highest healthy
    load current, or a good load provokes limitation

    the UPPER edge has to stay under the rating of the harness being
    protected, or the protection does not protect

When the stacked band is wider than the threshold window, no nominal
setpoint can satisfy the clause and the answer is to tighten a
contributor, not to move the setpoint. When it does fit but sits off
centre, the setpoint that recentres it is reported.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTRIBUTOR_FIELDS = ("name", "kind", "minus", "plus")
KINDS = ("relative", "absolute")
METHODS = ("arithmetic", "rss")
DEFAULT_METHOD = "arithmetic"

VERDICT_WITHIN = "limitation-range-within-thresholds"
VERDICT_OUTSIDE = "limitation-range-outside-thresholds"

FINDING_BELOW_MIN = "lower-edge-below-the-minimum-protection-threshold"
FINDING_ABOVE_MAX = "upper-edge-above-the-maximum-protection-threshold"
FINDING_LOAD_OVERLAP = "lower-edge-at-or-below-the-healthy-load-current"
FINDING_HARNESS = "upper-edge-above-the-protected-harness-rating"
FINDING_BAND_TOO_WIDE = "stacked-band-wider-than-the-threshold-window"
ADVISORY_BAND_USE = "stacked-band-consumes-most-of-the-threshold-window"

# Placeholder contributor set: the shape a project's own stack has to take.
DEFAULT_CONTRIBUTORS = (
    {"name": "initial-setting", "kind": "relative", "minus": 0.02, "plus": 0.02},
    {"name": "temperature-drift", "kind": "relative", "minus": 0.03, "plus": 0.03},
    {"name": "reference-drift", "kind": "relative", "minus": 0.01, "plus": 0.01},
    {"name": "ageing", "kind": "relative", "minus": 0.015, "plus": 0.005},
    {"name": "total-dose", "kind": "relative", "minus": 0.01, "plus": 0.03},
    {"name": "sense-offset", "kind": "absolute", "minus": 0.010, "plus": 0.010},
)

DEFAULT_ASSESSMENT_POLICY = {"band_advisory_fraction": 0.80}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A stacked edge is built from sums, products and a square root, so a
    case meant to sit exactly on a threshold can land a few units in the
    last place outside it. The threshold is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_assessment_policy(policy):
    """Check the band advisory fraction is a usable share of the window."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_positive(
        "band_advisory_fraction", policy.get("band_advisory_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "band_advisory_fraction must not exceed one, got %r" % (fraction,)
        )
    return policy


def validate_contributor(contributor):
    """Check one setpoint contributor is a usable two-sided tolerance."""
    if not isinstance(contributor, dict):
        raise ValueError("contributor must be a mapping, got %r" % (contributor,))
    missing = [f for f in CONTRIBUTOR_FIELDS if f not in contributor]
    if missing:
        raise ValueError(
            "contributor is missing fields: %s" % ", ".join(sorted(missing))
        )
    name = contributor["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("contributor name must be a non-empty string, got %r" % (name,))
    kind = _require_choice("kind", contributor["kind"], KINDS)
    minus = _require_non_negative("minus", contributor["minus"])
    plus = _require_non_negative("plus", contributor["plus"])
    if kind == "relative":
        for side, value in (("minus", minus), ("plus", plus)):
            if value >= 1.0:
                raise ValueError(
                    "relative contributor %s has a %s side of %g; a relative "
                    "tolerance at or beyond unity is not a tolerance"
                    % (name, side, value)
                )
    if minus == 0.0 and plus == 0.0:
        raise ValueError(
            "contributor %s has no tolerance on either side; drop it rather "
            "than stacking a zero" % (name,)
        )
    return {"name": name, "kind": kind, "minus": minus, "plus": plus}


def validate_contributors(contributors):
    """Normalise a contributor set and require unique names."""
    if isinstance(contributors, dict) or not hasattr(contributors, "__iter__"):
        raise ValueError("contributors must be a sequence of mappings")
    rows = [validate_contributor(c) for c in contributors]
    if not rows:
        raise ValueError("contributor set is empty; nothing can be stacked")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("contributor set repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def contributor_amperes(contributor, nominal_a):
    """Both sides of one contributor expressed in amperes."""
    row = validate_contributor(contributor)
    nominal = _require_positive("nominal_a", nominal_a)
    if row["kind"] == "relative":
        return (row["minus"] * nominal, row["plus"] * nominal)
    return (row["minus"], row["plus"])


def stack_tolerances(nominal_a, contributors, method=DEFAULT_METHOD):
    """Combine every contributor into one downward and one upward span.

    Arithmetic stacking puts every contributor at its own worst case at
    the same instant and is the bounding answer. Root-sum-square assumes
    the contributors are independent and always reports a narrower span,
    so it is only admissible when that independence is argued.
    """
    nominal = _require_positive("nominal_a", nominal_a)
    rows = validate_contributors(contributors)
    _require_choice("method", method, METHODS)
    minus_terms = []
    plus_terms = []
    for row in rows:
        low, high = contributor_amperes(row, nominal)
        minus_terms.append(low)
        plus_terms.append(high)
    if method == "arithmetic":
        return (math.fsum(minus_terms), math.fsum(plus_terms))
    return (
        math.sqrt(math.fsum(t * t for t in minus_terms)),
        math.sqrt(math.fsum(t * t for t in plus_terms)),
    )


def limitation_range(nominal_a, contributors, method=DEFAULT_METHOD):
    """Worst-case limitation current range around the nominal setpoint."""
    nominal = _require_positive("nominal_a", nominal_a)
    minus_a, plus_a = stack_tolerances(nominal, contributors, method)
    low = nominal - minus_a
    if low <= 0.0:
        raise ValueError(
            "the downward stack of %g A consumes the nominal setpoint of %g A"
            % (minus_a, nominal)
        )
    return {
        "nominal_a": nominal,
        "method": method,
        "minus_a": minus_a,
        "plus_a": plus_a,
        "min_a": low,
        "max_a": nominal + plus_a,
        "band_width_a": minus_a + plus_a,
    }


def verify_within_thresholds(current_range, threshold_min_a, threshold_max_a):
    """Compare both edges of the range with the protection thresholds."""
    if not isinstance(current_range, dict):
        raise ValueError("current_range must be a mapping, got %r" % (current_range,))
    for field in ("min_a", "max_a", "band_width_a"):
        if field not in current_range:
            raise ValueError("current_range is missing %s" % field)
    low_limit = _require_positive("threshold_min_a", threshold_min_a)
    high_limit = _require_positive("threshold_max_a", threshold_max_a)
    if high_limit <= low_limit:
        raise ValueError(
            "threshold window is inverted or empty (%g A .. %g A)"
            % (low_limit, high_limit)
        )
    low = float(current_range["min_a"])
    high = float(current_range["max_a"])
    above_floor = _at_least(low, low_limit)
    below_ceiling = _at_most(high, high_limit)
    window = high_limit - low_limit
    return {
        "threshold_min_a": low_limit,
        "threshold_max_a": high_limit,
        "window_width_a": window,
        "band_width_a": float(current_range["band_width_a"]),
        "window_usage": float(current_range["band_width_a"]) / window,
        "lower_margin_a": low - low_limit,
        "upper_margin_a": high_limit - high,
        "above_floor": above_floor,
        "below_ceiling": below_ceiling,
        "within": bool(above_floor and below_ceiling),
    }


def recentred_nominal_a(current_range, threshold_min_a, threshold_max_a):
    """Setpoint that centres the stacked band inside the threshold window.

    Returns None when the band is wider than the window: no setpoint can
    then satisfy the clause and a contributor has to be tightened.
    """
    low_limit = _require_positive("threshold_min_a", threshold_min_a)
    high_limit = _require_positive("threshold_max_a", threshold_max_a)
    if high_limit <= low_limit:
        raise ValueError(
            "threshold window is inverted or empty (%g A .. %g A)"
            % (low_limit, high_limit)
        )
    minus_a = _require_non_negative("minus_a", current_range.get("minus_a"))
    plus_a = _require_non_negative("plus_a", current_range.get("plus_a"))
    window = high_limit - low_limit
    if not _at_most(minus_a + plus_a, window):
        return None
    slack = window - (minus_a + plus_a)
    return low_limit + minus_a + slack / 2.0


def assess_functional_separation(current_range, healthy_load_current_a, harness_rating_a):
    """Check the range clears the healthy load and stays under the harness."""
    load = _require_positive("healthy_load_current_a", healthy_load_current_a)
    harness = _require_positive("harness_rating_a", harness_rating_a)
    low = float(current_range["min_a"])
    high = float(current_range["max_a"])
    clears_load = low > load and not math.isclose(
        low, load, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    protects = _at_most(high, harness)
    return {
        "healthy_load_current_a": load,
        "harness_rating_a": harness,
        "load_headroom_a": low - load,
        "harness_headroom_a": harness - high,
        "clears_healthy_load": clears_load,
        "protects_harness": protects,
    }


def assess_limitation_range(case, policy=DEFAULT_ASSESSMENT_POLICY):
    """Full clause 5.2.3.1.1 range check with a compliance verdict."""
    validate_assessment_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    required = (
        "nominal_a",
        "contributors",
        "threshold_min_a",
        "threshold_max_a",
        "healthy_load_current_a",
        "harness_rating_a",
    )
    missing = [f for f in required if f not in case]
    if missing:
        raise ValueError("case is missing fields: %s" % ", ".join(sorted(missing)))
    method = _require_choice("method", case.get("method", DEFAULT_METHOD), METHODS)
    current_range = limitation_range(case["nominal_a"], case["contributors"], method)
    thresholds = verify_within_thresholds(
        current_range, case["threshold_min_a"], case["threshold_max_a"]
    )
    separation = assess_functional_separation(
        current_range, case["healthy_load_current_a"], case["harness_rating_a"]
    )
    recentred = recentred_nominal_a(
        current_range, case["threshold_min_a"], case["threshold_max_a"]
    )

    findings = []
    advisories = []
    if not thresholds["above_floor"]:
        findings.append(
            "%s: %.4f A against a floor of %.4f A"
            % (
                FINDING_BELOW_MIN,
                current_range["min_a"],
                thresholds["threshold_min_a"],
            )
        )
    if not thresholds["below_ceiling"]:
        findings.append(
            "%s: %.4f A against a ceiling of %.4f A"
            % (
                FINDING_ABOVE_MAX,
                current_range["max_a"],
                thresholds["threshold_max_a"],
            )
        )
    if recentred is None:
        findings.append(
            "%s: %.4f A of stack against a %.4f A window; tighten a contributor"
            % (
                FINDING_BAND_TOO_WIDE,
                current_range["band_width_a"],
                thresholds["window_width_a"],
            )
        )
    if not separation["clears_healthy_load"]:
        findings.append(
            "%s: %.4f A against a healthy load of %.4f A"
            % (
                FINDING_LOAD_OVERLAP,
                current_range["min_a"],
                separation["healthy_load_current_a"],
            )
        )
    if not separation["protects_harness"]:
        findings.append(
            "%s: %.4f A against a harness rating of %.4f A"
            % (
                FINDING_HARNESS,
                current_range["max_a"],
                separation["harness_rating_a"],
            )
        )
    if not findings and thresholds["window_usage"] > float(
        policy["band_advisory_fraction"]
    ):
        advisories.append(
            "%s: the stack uses %.1f%% of the window"
            % (ADVISORY_BAND_USE, 100.0 * thresholds["window_usage"])
        )

    compliant = not findings
    return {
        "verdict": VERDICT_WITHIN if compliant else VERDICT_OUTSIDE,
        "compliant": compliant,
        "range": current_range,
        "thresholds": thresholds,
        "separation": separation,
        "recentred_nominal_a": recentred,
        "findings": findings,
        "advisories": advisories,
    }
