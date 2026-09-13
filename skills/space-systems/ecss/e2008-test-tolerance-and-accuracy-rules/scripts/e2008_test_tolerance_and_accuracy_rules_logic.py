#!/usr/bin/env python3
"""Test tolerance and accuracy logic (ECSS-E-ST-20-08C, 4.3.2).

Offline, deterministic, standard-library only. The module fixes the
precision an instrument has to hold relative to the tolerance of the
photovoltaic-assembly test parameter it controls or measures:

* derivation of the governing tolerance half-band from the declared
  two-sided, asymmetric or one-sided limits,
* the largest instrument uncertainty that half-band will carry,
* the same statement expressed as a test-accuracy-ratio,
* the reading resolution a displayed value has to resolve to,
* the set-point drift a controlled parameter is additionally allowed,
* guard-banded acceptance limits when the ratio is only marginal,
* per-parameter and whole-list acceptance of the instrumentation.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "PRECISION_FRACTION",
    "RESOLUTION_FRACTION",
    "MINIMUM_TEST_ACCURACY_RATIO",
    "GUARD_BAND_RATIO",
    "DRIFT_FRACTION",
    "PARAMETER_ROLES",
    "tolerance_band",
    "required_instrument_precision",
    "test_accuracy_ratio",
    "check_instrument_precision",
    "required_reading_resolution",
    "check_reading_resolution",
    "check_set_point_drift",
    "guard_banded_limits",
    "evaluate_test_parameter",
    "assess_test_instrumentation",
]

# Absorbs binary-representation error when a limit computed as a product or
# a ratio lands a few ULPs outside an exactly-met bound. It never widens the
# bound itself.
REL_TOL = 1e-9

# An instrument may consume at most this fraction of the governing tolerance
# half-band with its own uncertainty.
PRECISION_FRACTION = 1.0 / 3.0

# A displayed or logged reading has to resolve at least this finely against
# the same half-band.
RESOLUTION_FRACTION = 0.1

# The precision rule restated as a ratio of half-band to uncertainty.
MINIMUM_TEST_ACCURACY_RATIO = 1.0 / PRECISION_FRACTION

# At or above this ratio the instrument uncertainty is small enough that the
# acceptance limits are used as declared; below it they are guard-banded.
GUARD_BAND_RATIO = 4.0

# A controlled parameter may additionally drift by this fraction of the
# half-band across the dwell, over and above the instrument uncertainty.
DRIFT_FRACTION = 0.5

# A parameter is either held at a set point by the facility (controlled) or
# only read back from the article (measured).
PARAMETER_ROLES = ("controlled", "measured")

_PARAMETER_KEYS = (
    "id",
    "role",
    "unit",
    "nominal",
    "upper_tolerance",
    "lower_tolerance",
    "instrument_uncertainty",
    "reading_resolution",
    "set_point_drift",
)

_REQUIRED_KEYS = (
    "id",
    "role",
    "nominal",
    "upper_tolerance",
    "lower_tolerance",
    "instrument_uncertainty",
)


def _finding(code, subject, detail):
    """Build one instrumentation finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _as_non_negative_float(value, label):
    number = _as_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _within(value, allowed):
    """Upper-bound comparison that absorbs binary-representation error."""
    return value <= allowed or math.isclose(
        value, allowed, rel_tol=REL_TOL, abs_tol=0.0
    )


def _at_least(value, required):
    """Lower-bound comparison that absorbs binary-representation error."""
    return value >= required or math.isclose(
        value, required, rel_tol=REL_TOL, abs_tol=0.0
    )


def tolerance_band(nominal, upper_tolerance, lower_tolerance):
    """Resolve the declared limits into the half-band the instrument must serve.

    The tolerances are magnitudes away from the nominal, upward and
    downward. Either may be zero, which makes the band one-sided. The
    governing half-band is the tighter of the two non-zero sides, because
    that is the side an instrument error first pushes a reading across.
    """
    centre = _as_float(nominal, "nominal")
    upper = _as_non_negative_float(upper_tolerance, "upper_tolerance")
    lower = _as_non_negative_float(lower_tolerance, "lower_tolerance")
    if upper == 0.0 and lower == 0.0:
        raise ValueError("a test parameter needs a tolerance on at least one side")
    sides = [side for side in (upper, lower) if side > 0.0]
    governing = min(sides)
    return {
        "nominal": centre,
        "upper_tolerance": upper,
        "lower_tolerance": lower,
        "upper_limit": centre + upper,
        "lower_limit": centre - lower,
        "width": upper + lower,
        "governing_half_width": governing,
        "one_sided": len(sides) == 1,
        "asymmetric": upper != lower,
    }


def required_instrument_precision(governing_half_width, fraction=PRECISION_FRACTION):
    """Largest instrument uncertainty the governing half-band will carry."""
    half_width = _as_positive_float(governing_half_width, "governing_half_width")
    share = _as_positive_float(fraction, "fraction")
    if share >= 1.0:
        raise ValueError(
            "the instrument may not consume the whole half-band, got %r" % (fraction,)
        )
    return half_width * share


def test_accuracy_ratio(governing_half_width, instrument_uncertainty):
    """Ratio of the governing half-band to the instrument uncertainty."""
    half_width = _as_positive_float(governing_half_width, "governing_half_width")
    uncertainty = _as_positive_float(
        instrument_uncertainty, "instrument_uncertainty"
    )
    return half_width / uncertainty


def check_instrument_precision(
    governing_half_width, instrument_uncertainty, fraction=PRECISION_FRACTION
):
    """Check one instrument uncertainty against the precision the band demands."""
    required = required_instrument_precision(governing_half_width, fraction)
    uncertainty = _as_positive_float(
        instrument_uncertainty, "instrument_uncertainty"
    )
    ratio = test_accuracy_ratio(governing_half_width, uncertainty)
    return {
        "quantity": "instrument-precision",
        "required": required,
        "actual": uncertainty,
        "ratio": ratio,
        "minimum_ratio": 1.0 / _as_positive_float(fraction, "fraction"),
        "margin": required - uncertainty,
        "adequate": _within(uncertainty, required),
    }


def required_reading_resolution(governing_half_width):
    """Coarsest reading step the governing half-band will carry."""
    half_width = _as_positive_float(governing_half_width, "governing_half_width")
    return half_width * RESOLUTION_FRACTION


def check_reading_resolution(governing_half_width, reading_resolution):
    """Check that a displayed or logged value resolves finely enough."""
    required = required_reading_resolution(governing_half_width)
    resolution = _as_positive_float(reading_resolution, "reading_resolution")
    return {
        "quantity": "reading-resolution",
        "required": required,
        "actual": resolution,
        "margin": required - resolution,
        "adequate": _within(resolution, required),
    }


def check_set_point_drift(governing_half_width, set_point_drift):
    """Check the drift a controlled parameter shows across its dwell."""
    half_width = _as_positive_float(governing_half_width, "governing_half_width")
    drift = _as_non_negative_float(set_point_drift, "set_point_drift")
    allowed = half_width * DRIFT_FRACTION
    return {
        "quantity": "set-point-drift",
        "allowed": allowed,
        "actual": drift,
        "margin": allowed - drift,
        "adequate": _within(drift, allowed),
    }


def guard_banded_limits(band, instrument_uncertainty):
    """Shrink the acceptance limits when the accuracy ratio is only marginal.

    At or above the guard-band ratio the declared limits are used as they
    stand. Below it the instrument uncertainty is subtracted from each
    toleranced side, so that a reading inside the reduced window is inside
    the real limit whichever way the instrument erred.
    """
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %s" % type(band).__name__)
    for key in ("nominal", "upper_tolerance", "lower_tolerance", "governing_half_width"):
        if key not in band:
            raise ValueError("band is missing required key %r" % key)
    uncertainty = _as_positive_float(
        instrument_uncertainty, "instrument_uncertainty"
    )
    ratio = test_accuracy_ratio(band["governing_half_width"], uncertainty)
    applied = not _at_least(ratio, GUARD_BAND_RATIO)
    guard = uncertainty if applied else 0.0
    upper = _as_non_negative_float(band["upper_tolerance"], "upper_tolerance")
    lower = _as_non_negative_float(band["lower_tolerance"], "lower_tolerance")
    centre = _as_float(band["nominal"], "nominal")
    accept_upper = centre + (upper - guard if upper > 0.0 else 0.0)
    accept_lower = centre - (lower - guard if lower > 0.0 else 0.0)
    collapsed = accept_upper < accept_lower or (
        applied
        and (
            (upper > 0.0 and not _at_least(upper, guard))
            or (lower > 0.0 and not _at_least(lower, guard))
        )
    )
    return {
        "quantity": "guard-band",
        "applied": applied,
        "ratio": ratio,
        "guard": guard,
        "accept_upper": accept_upper,
        "accept_lower": accept_lower,
        "collapsed": collapsed,
    }


def evaluate_test_parameter(parameter):
    """Evaluate one controlled or measured parameter against the accuracy rule."""
    if not isinstance(parameter, dict):
        raise ValueError(
            "parameter must be a mapping, got %s" % type(parameter).__name__
        )
    unknown = [key for key in parameter if key not in _PARAMETER_KEYS]
    if unknown:
        raise ValueError(
            "parameter carries unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    missing = [key for key in _REQUIRED_KEYS if key not in parameter]
    if missing:
        raise ValueError(
            "parameter is missing required key(s): %s" % ", ".join(missing)
        )
    if not isinstance(parameter["id"], str) or not parameter["id"].strip():
        raise ValueError("parameter id must be a non-blank string")
    identifier = parameter["id"].strip()
    role = parameter["role"]
    if role not in PARAMETER_ROLES:
        raise ValueError(
            "parameter %s has role %r, expected one of %s"
            % (identifier, role, ", ".join(PARAMETER_ROLES))
        )
    band = tolerance_band(
        parameter["nominal"],
        parameter["upper_tolerance"],
        parameter["lower_tolerance"],
    )
    half_width = band["governing_half_width"]
    checks = {}
    findings = []

    precision = check_instrument_precision(
        half_width, parameter["instrument_uncertainty"]
    )
    checks["precision"] = precision
    if not precision["adequate"]:
        findings.append(
            _finding(
                "instrument-precision-insufficient",
                identifier,
                "instrument holds %.6g against the %.6g the %.6g half-band allows "
                "(ratio %.3f, minimum %.3f)"
                % (
                    precision["actual"],
                    precision["required"],
                    half_width,
                    precision["ratio"],
                    MINIMUM_TEST_ACCURACY_RATIO,
                ),
            )
        )

    if "reading_resolution" in parameter:
        resolution = check_reading_resolution(
            half_width, parameter["reading_resolution"]
        )
        checks["resolution"] = resolution
        if not resolution["adequate"]:
            findings.append(
                _finding(
                    "reading-resolution-too-coarse",
                    identifier,
                    "reads in steps of %.6g against the %.6g the half-band allows"
                    % (resolution["actual"], resolution["required"]),
                )
            )

    if "set_point_drift" in parameter:
        if role != "controlled":
            raise ValueError(
                "parameter %s is measured, not controlled, so it cannot declare a "
                "set-point drift" % identifier
            )
        drift = check_set_point_drift(half_width, parameter["set_point_drift"])
        checks["drift"] = drift
        if not drift["adequate"]:
            findings.append(
                _finding(
                    "set-point-drift-excessive",
                    identifier,
                    "drifts %.6g across the dwell against the %.6g allowed"
                    % (drift["actual"], drift["allowed"]),
                )
            )

    guard = guard_banded_limits(band, parameter["instrument_uncertainty"])
    checks["guard_band"] = guard
    if guard["collapsed"]:
        findings.append(
            _finding(
                "acceptance-window-collapsed",
                identifier,
                "guard-banding by %.6g leaves no acceptance window inside the "
                "declared limits" % (guard["guard"],),
            )
        )

    return {
        "id": identifier,
        "role": role,
        "unit": parameter.get("unit"),
        "band": band,
        "checks": checks,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_test_instrumentation(parameters):
    """Assess a whole instrumentation list parameter by parameter."""
    if isinstance(parameters, (str, bytes)) or not hasattr(parameters, "__iter__"):
        raise ValueError("parameters must be an iterable of parameter mappings")
    evaluated = [evaluate_test_parameter(entry) for entry in parameters]
    if not evaluated:
        raise ValueError("an instrumentation list must carry at least one parameter")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("test parameter %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    guard_banded = [
        record["id"]
        for record in evaluated
        if record["checks"]["guard_band"]["applied"]
    ]
    accepted = not findings
    return {
        "verdict": "instrumentation-adequate" if accepted else "instrumentation-inadequate",
        "accepted": accepted,
        "findings": findings,
        "parameters": evaluated,
        "parameter_count": len(evaluated),
        "controlled_count": sum(
            1 for record in evaluated if record["role"] == "controlled"
        ),
        "measured_count": sum(
            1 for record in evaluated if record["role"] == "measured"
        ),
        "guard_banded": guard_banded,
        "conforming_fraction": sum(
            1 for record in evaluated if record["acceptable"]
        )
        / float(len(evaluated)),
    }
