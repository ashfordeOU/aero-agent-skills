"""Judging radiation damage in a part from measured parameter drift data.

Anchor: ECSS-Q-ST-60-15C clause 4.3 (the basis on which a part is judged
damaged by radiation: the drift of its measured electrical parameters away
from their pre-irradiation values and out of their limits). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the parameter under evaluation: its name, its pre-irradiation
   value, the limit it has to stay inside and the direction in which drift
   takes it out. A part already outside its limit before exposure is an input
   error, not a zero-level failure.
2. Reduce every reading to one excursion quantity that rises toward failure,
   whichever way the parameter drifts, so a rising parameter, a falling one
   and a two-sided drift band are all judged the same way.
3. Validate each sample's readings: exposure levels ascending, values finite,
   and at least one level actually applied.
4. Derive the exposure level at which the parameter leaves its limit by
   interpolating between the last reading inside and the first reading
   outside. A reading sitting exactly on the limit is inside it, and its own
   level is returned rather than an interpolated neighbour.
5. Report a sample that never left its limit as censored at the highest level
   applied, because the data supports "at least this much", not a number.
6. Take the worst sample as the part's demonstrated capability, compare it
   with the level the part is specified to, and flag drift that recovered
   between steps, since a non-monotonic run weakens what the crossing means.
"""

import math

__all__ = [
    "DRIFT_DIRECTIONS",
    "DEFAULT_REQUIRED_MARGIN",
    "LIMIT_TOLERANCE",
    "normalize_token",
    "validate_direction",
    "validate_parameter",
    "excursion",
    "limit_threshold",
    "within_limit",
    "relative_drift",
    "validate_readings",
    "recovery_findings",
    "crossing_level",
    "evaluate_sample",
    "capability_margin",
    "margin_holds",
    "assess_parameter_drift",
]

# How a parameter leaves its limit: upward, downward, or either way out of a
# two-sided drift band measured from the pre-irradiation value.
DRIFT_DIRECTIONS = ("increase", "decrease", "either")

# The margin between demonstrated capability and specified level a part is
# expected to hold unless the project declares another.
DEFAULT_REQUIRED_MARGIN = 2.0

# Limit and margin comparisons are between measured quantities; a reading
# sitting exactly on its limit must not be pushed outside by representation
# alone.
LIMIT_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _finite_number(value, label):
    """Return a finite real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive_number(value, label):
    """Return a strictly positive finite real number."""
    number = _finite_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %g" % (label, number))
    return number


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_direction(value):
    """Return the validated drift direction token."""
    token = normalize_token(value, "drift direction")
    if token not in DRIFT_DIRECTIONS:
        raise ValueError(
            "drift direction '%s' is not recognized; expected one of %s"
            % (token, ", ".join(DRIFT_DIRECTIONS))
        )
    return token


def validate_parameter(parameter):
    """Return the validated parameter under evaluation.

    For a two-sided band the limit is the width of the band measured from the
    pre-irradiation value, so it has to be positive. For a one-sided limit the
    pre-irradiation value has to already be inside it, or the reading that
    established the limit and the reading that measured the part disagree.
    """
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    for key in ("name", "pre_value", "limit", "direction"):
        if key not in parameter:
            raise ValueError("parameter missing required key '%s'" % key)

    entry = {
        "name": _require_text(parameter["name"], "parameter name"),
        "pre_value": _finite_number(parameter["pre_value"], "pre_value"),
        "limit": _finite_number(parameter["limit"], "limit"),
        "direction": validate_direction(parameter["direction"]),
    }

    if entry["direction"] == "either":
        if entry["limit"] <= 0.0:
            raise ValueError(
                "a two-sided drift band must be positive, got %g" % entry["limit"]
            )
    elif not within_limit(entry["pre_value"], entry):
        raise ValueError(
            "parameter '%s' is outside its limit before exposure" % entry["name"]
        )
    return entry


def excursion(value, parameter):
    """Return a quantity that rises toward failure for any drift direction."""
    reading = _finite_number(value, "reading value")
    direction = parameter["direction"]
    if direction == "increase":
        return reading
    if direction == "decrease":
        return -reading
    return abs(reading - parameter["pre_value"])


def limit_threshold(parameter):
    """Return the excursion value the parameter's limit corresponds to."""
    direction = parameter["direction"]
    if direction == "increase":
        return parameter["limit"]
    if direction == "decrease":
        return -parameter["limit"]
    return parameter["limit"]


def within_limit(value, parameter):
    """Return whether a reading is still inside its limit, equality included."""
    reading_excursion = excursion(value, parameter)
    threshold = limit_threshold(parameter)
    if math.isclose(
        reading_excursion, threshold, rel_tol=LIMIT_TOLERANCE, abs_tol=LIMIT_TOLERANCE
    ):
        return True
    return reading_excursion < threshold


def relative_drift(pre_value, value):
    """Return a reading's drift as a fraction of its pre-irradiation value."""
    pre = _finite_number(pre_value, "pre_value")
    reading = _finite_number(value, "reading value")
    if pre == 0.0:
        raise ValueError(
            "relative drift is undefined against a zero pre-irradiation value"
        )
    return (reading - pre) / pre


def validate_readings(readings):
    """Return validated (level, value) readings, ascending in exposure level."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence")
    points = []
    for index, reading in enumerate(readings):
        if not isinstance(reading, (list, tuple)) or len(reading) != 2:
            raise ValueError("reading %d must be a (level, value) pair" % index)
        level = _positive_number(reading[0], "reading %d level" % index)
        value = _finite_number(reading[1], "reading %d value" % index)
        points.append((level, value))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError(
                "reading levels must ascend; reading %d is %g after %g"
                % (index, points[index][0], points[index - 1][0])
            )
    return points


def recovery_findings(readings, parameter):
    """Return the steps where the drift moved back toward its starting value.

    Damage that partly recovers between steps is real, but it means the run no
    longer supports reading the crossing as a single monotonic degradation, so
    each recovery is reported rather than smoothed away.
    """
    points = validate_readings(readings)
    findings = []
    previous = excursion(parameter["pre_value"], parameter)
    previous_level = 0.0
    for level, value in points:
        current = excursion(value, parameter)
        if current < previous and not math.isclose(
            current, previous, rel_tol=LIMIT_TOLERANCE, abs_tol=LIMIT_TOLERANCE
        ):
            findings.append(
                "parameter '%s' recovered between %g and %g"
                % (parameter["name"], previous_level, level)
            )
        previous = current
        previous_level = level
    return findings


def crossing_level(parameter, readings):
    """Return the exposure level at which the parameter leaves its limit.

    A run whose readings all stay inside the limit is censored: the data
    supports a capability of at least the highest level applied, and no
    crossing level is invented for it.
    """
    entry = validate_parameter(parameter)
    points = validate_readings(readings)
    threshold = limit_threshold(entry)

    previous_level = 0.0
    previous_excursion = excursion(entry["pre_value"], entry)
    for level, value in points:
        current = excursion(value, entry)
        if within_limit(value, entry):
            previous_level = level
            previous_excursion = current
            continue
        if math.isclose(
            current, threshold, rel_tol=LIMIT_TOLERANCE, abs_tol=LIMIT_TOLERANCE
        ):
            return {"crossed": True, "level": level, "censored": False,
                    "highest_level": points[-1][0]}
        span = current - previous_excursion
        if span <= 0.0:
            return {"crossed": True, "level": level, "censored": False,
                    "highest_level": points[-1][0]}
        frac = (threshold - previous_excursion) / span
        crossed_at = previous_level + frac * (level - previous_level)
        return {"crossed": True, "level": crossed_at, "censored": False,
                "highest_level": points[-1][0]}

    return {"crossed": False, "level": None, "censored": True,
            "highest_level": points[-1][0]}


def evaluate_sample(parameter, sample):
    """Return one sample's drift evaluation against the parameter limit."""
    entry = validate_parameter(parameter)
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    for key in ("sample_id", "readings"):
        if key not in sample:
            raise ValueError("sample missing required key '%s'" % key)

    sample_id = _require_text(sample["sample_id"], "sample_id")
    points = validate_readings(sample["readings"])
    crossing = crossing_level(entry, points)
    findings = recovery_findings(points, entry)

    drifts = []
    if entry["pre_value"] != 0.0:
        drifts = [relative_drift(entry["pre_value"], value) for _, value in points]

    return {
        "sample_id": sample_id,
        "readings": points,
        "relative_drifts": drifts,
        "crossed": crossing["crossed"],
        "crossing_level": crossing["level"],
        "censored": crossing["censored"],
        "highest_level": crossing["highest_level"],
        "findings": findings,
    }


def capability_margin(capability, specified):
    """Return the margin a demonstrated capability holds over a specified level."""
    cap = _positive_number(capability, "capability")
    spec = _positive_number(specified, "specified level")
    return cap / spec


def margin_holds(margin, required):
    """Return whether a margin meets its requirement, equality included."""
    value = _positive_number(margin, "margin")
    needed = _positive_number(required, "required margin")
    if math.isclose(value, needed, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0):
        return True
    return value > needed


def assess_parameter_drift(dataset):
    """Run the full clause 4.3 evaluation of one parameter across its samples.

    dataset keys: parameter, samples, specified_level, and optionally
    required_margin.
    """
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be a mapping")
    for key in ("parameter", "samples", "specified_level"):
        if key not in dataset:
            raise ValueError("dataset missing required key '%s'" % key)

    parameter = validate_parameter(dataset["parameter"])
    specified = _positive_number(dataset["specified_level"], "specified_level")
    needed = (
        DEFAULT_REQUIRED_MARGIN
        if dataset.get("required_margin") is None
        else _positive_number(dataset["required_margin"], "required_margin")
    )

    raw_samples = dataset["samples"]
    if not isinstance(raw_samples, (list, tuple)) or not raw_samples:
        raise ValueError("samples must be a non-empty sequence")

    findings = []
    samples = []
    seen = set()
    for raw in raw_samples:
        evaluated = evaluate_sample(parameter, raw)
        if evaluated["sample_id"] in seen:
            raise ValueError(
                "sample '%s' is evaluated twice" % evaluated["sample_id"]
            )
        seen.add(evaluated["sample_id"])
        samples.append(evaluated)
        findings.extend(evaluated["findings"])

    crossed = [s for s in samples if s["crossed"]]
    if crossed:
        worst = min(crossed, key=lambda s: s["crossing_level"])
        capability = worst["crossing_level"]
        worst_id = worst["sample_id"]
        censored = False
    else:
        worst = min(samples, key=lambda s: s["highest_level"])
        capability = worst["highest_level"]
        worst_id = worst["sample_id"]
        censored = True

    margin = capability_margin(capability, specified)
    holds = margin_holds(margin, needed)
    if not holds:
        findings.append(
            "parameter '%s' demonstrates a margin of %.4g against a required %.4g"
            % (parameter["name"], margin, needed)
        )

    return {
        "parameter": parameter,
        "samples": samples,
        "worst_case_sample": worst_id,
        "capability": capability,
        "capability_censored": censored,
        "specified_level": specified,
        "margin": margin,
        "required_margin": needed,
        "margin_holds": holds,
        "findings": findings,
        "acceptable": not findings,
    }
