"""Rated temperature range against the mission case for Class 3 commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 6.2.2.6 (the rated temperature limits a
commercial EEE part carries, checked against the conditions the application
imposes, at the lowest assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Offline, deterministic, python3 standard library only.

Procedure implemented here
--------------------------
* A commercial part arrives with a temperature grade, and the grade names a
  rated band. The band is a property of the part type, not of the programme,
  so it is resolved first and never adjusted to suit the application.
* The application case is not the predicted extremes. The thermal analysis
  behind those extremes carries an uncertainty, and the uncertainty widens
  the case outwards at both ends before anything is compared.
* This class lets a correlated thermal model buy part of that uncertainty
  back. Where the model has been correlated against a thermal balance test,
  the declared uncertainty is reduced by a fixed credit, with a floor that is
  never crossed -- correlation narrows the unknown, it does not remove it.
* The two ends are graded separately. A cold end and a hot end fail for
  different reasons and are repaired in different ways, so a single
  worst-case number would hide which end is the problem.
* Each end owes a margin, and the margin owed at this class is the thinnest
  of the three. An end inside the rated band but short of the margin is a
  finding, not a pass.
* Two credits may move an end, and neither is free. An uprating evaluation
  may extend a rated end, bounded and evidenced. An approved mounting and
  conduction-path repair may pull the hot extreme back in, bounded, and at
  the hot end alone -- a cold extreme is set by the environment the part
  sits in and no mounting change reaches it.
"""

from __future__ import annotations

import math

# Rated bands in degrees Celsius, keyed by the temperature grade a commercial
# part type is sold under.
TEMPERATURE_GRADE_BANDS = {
    "commercial-grade": (0.0, 70.0),
    "industrial-grade": (-40.0, 85.0),
    "automotive-grade": (-40.0, 125.0),
    "extended-industrial-grade": (-55.0, 105.0),
    "military-grade": (-55.0, 125.0),
}

# Margin each end owes at the lowest assurance class, in kelvin.
CLASS_3_END_MARGIN_K = 5.0

# The furthest an uprating evaluation may push a rated end, in kelvin.
MAX_UPRATING_EXTENSION_K = 25.0

# The furthest an approved mounting and conduction-path repair may pull the
# hot extreme back in, in kelvin.
MAX_HOT_END_MOUNTING_CREDIT_K = 8.0

# What a correlated thermal model leaves of the declared analysis uncertainty,
# and the floor that credit never crosses.
CORRELATED_UNCERTAINTY_CREDIT = 0.5
MIN_RETAINED_UNCERTAINTY_K = 2.0

THERMAL_MODEL_STATES = (
    "model-uncorrelated",
    "model-correlated-by-thermal-balance-test",
)

UPRATING_STATES = (
    "uprating-not-claimed",
    "uprating-evaluated-and-approved",
    "uprating-claimed-without-evaluation",
)

MOUNTING_STATES = (
    "mounting-repair-not-claimed",
    "mounting-repair-approved",
    "mounting-repair-claimed-without-approval",
)

ENDS = ("cold", "hot")

END_DISPOSITIONS = (
    "end-covered-with-margin",
    "end-margin-short",
    "end-not-covered",
)

VERDICTS = (
    "rated-range-covers-application",
    "rated-range-margin-short",
    "rated-range-not-covering-application",
)

# Margins are differences of decimal temperatures; a value that should sit on
# a bound can land a few units in the last place away from it.
MARGIN_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite, non-negative float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def grade_band(grade):
    """Rated band of one temperature grade; unknown grade names are rejected."""
    if grade not in TEMPERATURE_GRADE_BANDS:
        raise ValueError(
            "unknown temperature grade %r (known: %s)"
            % (grade, ", ".join(sorted(TEMPERATURE_GRADE_BANDS)))
        )
    return TEMPERATURE_GRADE_BANDS[grade]


def rated_limits(part):
    """Resolve the rated band of a part declaration.

    The band comes either from a named temperature grade or from explicit
    rated limits, never from both, because two sources that disagree is the
    defect this check exists to catch.
    """
    if not isinstance(part, dict):
        raise ValueError("part declaration must be a mapping, got %r" % (type(part).__name__,))
    grade = part.get("temperature_grade")
    has_explicit = "rated_min_c" in part or "rated_max_c" in part
    if grade is not None and has_explicit:
        raise ValueError("part declares both a temperature grade and explicit rated limits")
    if grade is not None:
        return grade_band(grade)
    if not has_explicit:
        raise ValueError("part declares neither a temperature grade nor explicit rated limits")
    low = _real(part.get("rated_min_c"), "rated_min_c")
    high = _real(part.get("rated_max_c"), "rated_max_c")
    if not high > low:
        raise ValueError("rated_max_c must sit above rated_min_c, got %r and %r" % (high, low))
    return (low, high)


def effective_uncertainty_k(thermal_uncertainty_k, thermal_model_state="model-uncorrelated"):
    """Analysis uncertainty left after any correlation credit this class allows."""
    declared = _non_negative(thermal_uncertainty_k, "thermal_uncertainty_k")
    if thermal_model_state not in THERMAL_MODEL_STATES:
        raise ValueError(
            "unknown thermal model state %r (known: %s)"
            % (thermal_model_state, ", ".join(THERMAL_MODEL_STATES))
        )
    if thermal_model_state == "model-uncorrelated":
        return declared
    credited = declared * CORRELATED_UNCERTAINTY_CREDIT
    floor = min(declared, MIN_RETAINED_UNCERTAINTY_K)
    return credited if credited > floor else floor


def widened_application_extremes(application_min_c, application_max_c, uncertainty_k):
    """Widen the predicted application extremes by the analysis uncertainty."""
    low = _real(application_min_c, "application_min_c")
    high = _real(application_max_c, "application_max_c")
    band = _non_negative(uncertainty_k, "uncertainty_k")
    if not high >= low:
        raise ValueError(
            "application_max_c must not sit below application_min_c, got %r and %r"
            % (high, low)
        )
    return (low - band, high + band)


def end_margin(end, rated_limit_c, application_extreme_c):
    """Margin one end holds, positive when the rated limit sits beyond the case."""
    if end not in ENDS:
        raise ValueError("unknown end %r (known: %s)" % (end, ", ".join(ENDS)))
    rated = _real(rated_limit_c, "rated_limit_c")
    extreme = _real(application_extreme_c, "application_extreme_c")
    if end == "cold":
        return extreme - rated
    return rated - extreme


def end_disposition(margin_k, required_margin_k=CLASS_3_END_MARGIN_K):
    """Grade one end from its margin against the margin the class requires."""
    margin = _real(margin_k, "margin_k")
    required = _non_negative(required_margin_k, "required_margin_k")
    if margin < -MARGIN_TOLERANCE:
        return "end-not-covered"
    if margin < required - MARGIN_TOLERANCE:
        return "end-margin-short"
    return "end-covered-with-margin"


def normalize_uprating(raw):
    """Validate an uprating declaration and fill its defaults."""
    if raw is None:
        return {"state": "uprating-not-claimed", "extension_k": 0.0, "ends": ()}
    if not isinstance(raw, dict):
        raise ValueError("uprating declaration must be a mapping, got %r" % (type(raw).__name__,))
    state = raw.get("state", "uprating-not-claimed")
    if state not in UPRATING_STATES:
        raise ValueError(
            "unknown uprating state %r (known: %s)" % (state, ", ".join(UPRATING_STATES))
        )
    extension = _non_negative(raw.get("extension_k", 0.0), "extension_k")
    ends = raw.get("ends", ())
    if isinstance(ends, str):
        raise ValueError("uprating ends must be a sequence of end names, got a string")
    if not isinstance(ends, (list, tuple)):
        raise ValueError("uprating ends must be a list or tuple, got %r" % (type(ends).__name__,))
    for end in ends:
        if end not in ENDS:
            raise ValueError("unknown uprating end %r (known: %s)" % (end, ", ".join(ENDS)))
    if len(set(ends)) != len(ends):
        raise ValueError("uprating names the same end twice")
    if state != "uprating-not-claimed" and not ends:
        raise ValueError("an uprating claim must name the end or ends it applies to")
    return {"state": state, "extension_k": extension, "ends": tuple(ends)}


def uprating_credit(uprating):
    """Decide how much of an uprating extension may be credited, and why.

    Returns ``(credited_extension_k, findings)``. An unevidenced claim earns
    nothing; an evidenced claim is capped at the bounded extension and still
    leaves a finding, because the credit travels with the part.
    """
    declared = normalize_uprating(uprating)
    state = declared["state"]
    findings = []
    if state == "uprating-not-claimed":
        return (0.0, findings)
    if state == "uprating-claimed-without-evaluation":
        findings.append("uprating-claimed-without-evaluation")
        return (0.0, findings)
    extension = declared["extension_k"]
    if extension > MAX_UPRATING_EXTENSION_K + MARGIN_TOLERANCE:
        findings.append("uprating-extension-beyond-bound")
        extension = MAX_UPRATING_EXTENSION_K
    findings.append("uprating-credit-taken")
    return (extension, findings)


def normalize_mounting_repair(raw):
    """Validate a mounting and conduction-path repair declaration."""
    if raw is None:
        return {"state": "mounting-repair-not-claimed", "credit_k": 0.0}
    if not isinstance(raw, dict):
        raise ValueError("mounting repair must be a mapping, got %r" % (type(raw).__name__,))
    state = raw.get("state", "mounting-repair-not-claimed")
    if state not in MOUNTING_STATES:
        raise ValueError(
            "unknown mounting repair state %r (known: %s)" % (state, ", ".join(MOUNTING_STATES))
        )
    credit = _non_negative(raw.get("credit_k", 0.0), "credit_k")
    end = raw.get("end", "hot")
    if end != "hot":
        raise ValueError(
            "a mounting and conduction-path repair reaches the hot end only, got %r" % (end,)
        )
    return {"state": state, "credit_k": credit}


def mounting_repair_credit(mounting_repair):
    """Kelvin a mounting repair pulls the hot extreme back by, and why.

    Returns ``(credited_k, findings)``. An unapproved claim earns nothing; an
    approved one is capped at the bounded credit and still leaves a finding,
    because the repair is an open action against the design.
    """
    declared = normalize_mounting_repair(mounting_repair)
    state = declared["state"]
    findings = []
    if state == "mounting-repair-not-claimed":
        return (0.0, findings)
    if state == "mounting-repair-claimed-without-approval":
        findings.append("mounting-repair-claimed-without-approval")
        return (0.0, findings)
    credit = declared["credit_k"]
    if credit > MAX_HOT_END_MOUNTING_CREDIT_K + MARGIN_TOLERANCE:
        findings.append("mounting-repair-credit-beyond-bound")
        credit = MAX_HOT_END_MOUNTING_CREDIT_K
    findings.append("hot-end-mounting-repair-credit-taken")
    return (credit, findings)


def assess_temperature_range(
    part_id,
    part,
    application_min_c,
    application_max_c,
    thermal_uncertainty_k=0.0,
    thermal_model_state="model-uncorrelated",
    uprating=None,
    mounting_repair=None,
    required_margin_k=CLASS_3_END_MARGIN_K,
):
    """Check a rated temperature band against the application case at Class 3."""
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    rated_min, rated_max = rated_limits(part)
    uncertainty = effective_uncertainty_k(thermal_uncertainty_k, thermal_model_state)
    cold_extreme, hot_extreme = widened_application_extremes(
        application_min_c, application_max_c, uncertainty
    )

    declared_uprating = normalize_uprating(uprating)
    credited_uprating, findings = uprating_credit(uprating)
    credited_mounting, mounting_findings = mounting_repair_credit(mounting_repair)
    findings = list(findings) + list(mounting_findings)

    effective_limits = {"cold": rated_min, "hot": rated_max}
    if credited_uprating > 0.0:
        for end in declared_uprating["ends"]:
            if end == "cold":
                effective_limits["cold"] = rated_min - credited_uprating
            else:
                effective_limits["hot"] = rated_max + credited_uprating

    effective_extremes = {"cold": cold_extreme, "hot": hot_extreme - credited_mounting}
    required = _non_negative(required_margin_k, "required_margin_k")

    ends = {}
    shortfalls = []
    for end in ENDS:
        margin = end_margin(end, effective_limits[end], effective_extremes[end])
        disposition = end_disposition(margin, required)
        ends[end] = {
            "end": end,
            "rated_limit_c": effective_limits[end],
            "application_extreme_c": effective_extremes[end],
            "margin_k": margin,
            "disposition": disposition,
        }
        if disposition != "end-covered-with-margin":
            shortfalls.append(
                {"end": end, "disposition": disposition, "shortfall_k": required - margin}
            )
            findings.append("%s-end-%s" % (end, disposition[4:]))
    shortfalls.sort(key=lambda row: (-row["shortfall_k"], row["end"]))

    dispositions = [ends[end]["disposition"] for end in ENDS]
    if "end-not-covered" in dispositions:
        verdict = "rated-range-not-covering-application"
    elif "end-margin-short" in dispositions:
        verdict = "rated-range-margin-short"
    else:
        verdict = "rated-range-covers-application"

    # Every credit taken, capped or refused is an open action against the
    # part, so a covered range that carries one is not a clean one.
    usable = verdict == "rated-range-covers-application" and not findings
    return {
        "part_id": part_id,
        "rated_min_c": rated_min,
        "rated_max_c": rated_max,
        "effective_rated_min_c": effective_limits["cold"],
        "effective_rated_max_c": effective_limits["hot"],
        "declared_uncertainty_k": _non_negative(thermal_uncertainty_k, "thermal_uncertainty_k"),
        "effective_uncertainty_k": uncertainty,
        "application_cold_extreme_c": effective_extremes["cold"],
        "application_hot_extreme_c": effective_extremes["hot"],
        "required_margin_k": required,
        "credited_uprating_k": credited_uprating,
        "credited_mounting_k": credited_mounting,
        "ends": ends,
        "shortfalls": shortfalls,
        "findings": findings,
        "verdict": verdict,
        "usable_at_class_3": usable,
    }
