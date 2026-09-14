"""Rated temperature range against the mission case for Class 2 commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 5.2.2.6 (the rated temperature limits a
commercial EEE part carries, reconciled with the operating conditions the
mission imposes, at the intermediate assurance class).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A commercial part arrives with a temperature grade, and the grade names a
  rated band. The band is a property of the part type, not of the programme,
  so it is resolved first and never adjusted to suit the mission.
* The mission case is not the predicted extremes. The thermal analysis behind
  those extremes carries an uncertainty, and the uncertainty widens the case
  outwards at both ends before anything is compared. Comparing a datasheet
  band against an un-widened prediction is the usual way a part looks covered
  and is not.
* The two ends are graded separately. A cold end and a hot end fail for
  different reasons and are repaired in different ways, so a single
  worst-case number would hide which end is the problem.
* Each end owes a margin at the intermediate class, not merely containment.
  An end inside the rated band but short of the margin is a finding, not a
  pass, because the margin is what absorbs the drift the analysis did not.
* An uprating claim may extend the rated band at a named end, but only when
  the extension is bounded and an uprating evaluation stands behind it. An
  unevidenced claim earns nothing and is reported; an evidenced one earns its
  extension and still leaves a finding, because the credit travels with the
  part.
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

# Margin each end owes at the intermediate assurance class, in kelvin.
CLASS_2_END_MARGIN_K = 10.0

# The furthest an uprating evaluation may push a rated end, in kelvin.
MAX_UPRATING_EXTENSION_K = 15.0

# States an uprating declaration may be in.
UPRATING_STATES = (
    "uprating-not-claimed",
    "uprating-evaluated-and-approved",
    "uprating-claimed-without-evaluation",
)

ENDS = ("cold", "hot")

END_DISPOSITIONS = (
    "end-covered-with-margin",
    "end-margin-short",
    "end-not-covered",
)

VERDICTS = (
    "rated-range-covers-mission",
    "rated-range-margin-short",
    "rated-range-not-covering-mission",
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
        raise ValueError(
            "part declares both a temperature grade and explicit rated limits"
        )
    if grade is not None:
        return grade_band(grade)
    if not has_explicit:
        raise ValueError(
            "part declares neither a temperature grade nor explicit rated limits"
        )
    low = _real(part.get("rated_min_c"), "rated_min_c")
    high = _real(part.get("rated_max_c"), "rated_max_c")
    if not high > low:
        raise ValueError(
            "rated_max_c must sit above rated_min_c, got %r and %r" % (high, low)
        )
    return (low, high)


def widened_mission_extremes(mission_min_c, mission_max_c, uncertainty_k):
    """Widen the predicted mission extremes by the thermal analysis uncertainty."""
    low = _real(mission_min_c, "mission_min_c")
    high = _real(mission_max_c, "mission_max_c")
    band = _real(uncertainty_k, "thermal_uncertainty_k")
    if not high >= low:
        raise ValueError(
            "mission_max_c must not sit below mission_min_c, got %r and %r" % (high, low)
        )
    if band < 0.0:
        raise ValueError("thermal_uncertainty_k must not be negative, got %r" % (band,))
    return (low - band, high + band)


def end_margin(end, rated_limit_c, mission_extreme_c):
    """Margin one end holds, positive when the rated limit sits beyond the case."""
    if end not in ENDS:
        raise ValueError("unknown end %r (known: %s)" % (end, ", ".join(ENDS)))
    rated = _real(rated_limit_c, "rated_limit_c")
    extreme = _real(mission_extreme_c, "mission_extreme_c")
    if end == "cold":
        return extreme - rated
    return rated - extreme


def end_disposition(margin_k, required_margin_k=CLASS_2_END_MARGIN_K):
    """Grade one end from its margin against the margin the class requires."""
    margin = _real(margin_k, "margin_k")
    required = _real(required_margin_k, "required_margin_k")
    if required < 0.0:
        raise ValueError("required_margin_k must not be negative, got %r" % (required,))
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
    extension = _real(raw.get("extension_k", 0.0), "extension_k")
    if extension < 0.0:
        raise ValueError("extension_k must not be negative, got %r" % (extension,))
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


def assess_temperature_range(
    part_id,
    part,
    mission_min_c,
    mission_max_c,
    thermal_uncertainty_k=0.0,
    uprating=None,
    required_margin_k=CLASS_2_END_MARGIN_K,
):
    """Reconcile a rated temperature band with the mission case at Class 2."""
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    rated_min, rated_max = rated_limits(part)
    cold_extreme, hot_extreme = widened_mission_extremes(
        mission_min_c, mission_max_c, thermal_uncertainty_k
    )
    declared = normalize_uprating(uprating)
    credited, findings = uprating_credit(uprating)
    effective = {"cold": rated_min, "hot": rated_max}
    for end in declared["ends"]:
        if credited > 0.0:
            if end == "cold":
                effective["cold"] = rated_min - credited
            else:
                effective["hot"] = rated_max + credited
    extremes = {"cold": cold_extreme, "hot": hot_extreme}
    required = _real(required_margin_k, "required_margin_k")
    ends = {}
    shortfalls = []
    for end in ENDS:
        margin = end_margin(end, effective[end], extremes[end])
        disposition = end_disposition(margin, required)
        ends[end] = {
            "end": end,
            "rated_limit_c": effective[end],
            "mission_extreme_c": extremes[end],
            "margin_k": margin,
            "disposition": disposition,
        }
        if disposition != "end-covered-with-margin":
            shortfalls.append(
                {
                    "end": end,
                    "disposition": disposition,
                    "shortfall_k": required - margin,
                }
            )
            findings.append("%s-end-%s" % (end, disposition[4:]))
    shortfalls.sort(key=lambda row: (-row["shortfall_k"], row["end"]))
    dispositions = [ends[end]["disposition"] for end in ENDS]
    if "end-not-covered" in dispositions:
        verdict = "rated-range-not-covering-mission"
    elif "end-margin-short" in dispositions:
        verdict = "rated-range-margin-short"
    else:
        verdict = "rated-range-covers-mission"
    # An uprating credit, a capped extension or an unevidenced claim are all
    # open actions against the part, so a covered range that carries one is
    # not the same as a clean one.
    usable = verdict == "rated-range-covers-mission" and not findings
    return {
        "part_id": part_id,
        "rated_min_c": rated_min,
        "rated_max_c": rated_max,
        "effective_rated_min_c": effective["cold"],
        "effective_rated_max_c": effective["hot"],
        "mission_cold_extreme_c": cold_extreme,
        "mission_hot_extreme_c": hot_extreme,
        "required_margin_k": required,
        "credited_uprating_k": credited,
        "ends": ends,
        "shortfalls": shortfalls,
        "findings": findings,
        "verdict": verdict,
        "usable_at_class_2": usable,
    }
