"""Absolute maximum ratings and die robustness evidence for a MMIC.

Anchor: ECSS-Q-ST-60-12C clause 7.2.9 (setting the absolute limits of a die and
demonstrating that it survives stress at those boundary conditions). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each declared rating: a name, a positive boundary value expressed as
   a magnitude, the measured degradation onset it was drawn from, and the safety
   factor the design rules require between the two.
2. Confirm the declared boundary sits below the onset by at least that factor.
   A rating drawn level with the onset is not a rating, it is the failure point.
3. Confirm every rating carries a robustness demonstration driven at or above
   its own boundary, on at least the required sample size, for at least the
   required duration, with no device lost and no parameter drift beyond the
   allowed fraction.
4. Confirm the worst-case applied stress of the application - nominal inflated
   by its tolerance and by any transient factor - stays inside the derated
   envelope, which is the declared boundary reduced by the derating factor.
5. Group every rating by its outcome and return the per-rating margins together
   with the findings that block acceptance.

Ratings are magnitudes. A negative boundary such as a gate-source floor is
entered as its absolute value, and the applied stress alongside it likewise.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "validate_rating",
    "validate_demonstration",
    "validate_requirements",
    "derated_limit",
    "worst_case_stress",
    "usage_ratio",
    "onset_headroom",
    "rating_supported_by_onset",
    "assess_demonstrations",
    "assess_rating",
    "group_outcomes",
    "assess_maximum_ratings",
]

# Every comparison below is a ratio of two floats that a physically exact case
# lands on. Absorb the representation error with a named tolerance instead of
# loosening the engineering limit.
RATIO_TOLERANCE = 1e-9

_OUTCOME_ORDER = (
    "onset-margin-short",
    "no-robustness-demonstration",
    "demonstration-below-boundary",
    "demonstration-undersized",
    "demonstration-too-short",
    "demonstration-lost-device",
    "demonstration-drift-excessive",
    "application-over-derated-limit",
    "accepted",
)


def _positive(label, value, allow_zero=False):
    """Return value as a float, raising when it is not a usable magnitude."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, number))
    elif number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _name(label, value):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def validate_rating(rating):
    """Return a normalised absolute-maximum-rating record.

    Keys: name, boundary (the declared maximum, a magnitude), onset (the
    measured degradation onset), safety_factor (>= 1, how far the boundary must
    sit below the onset), derating_factor (0 < f <= 1), applied_nominal,
    optional applied_tolerance_fraction and applied_transient_factor, unit.
    """
    if not isinstance(rating, dict):
        raise ValueError("rating must be a mapping")
    for key in ("name", "boundary", "onset", "safety_factor", "derating_factor",
                "applied_nominal"):
        if key not in rating:
            raise ValueError("rating missing required key '%s'" % key)
    name = _name("rating['name']", rating["name"])
    boundary = _positive("rating['boundary']", rating["boundary"])
    onset = _positive("rating['onset']", rating["onset"])
    safety = _positive("rating['safety_factor']", rating["safety_factor"])
    if safety < 1.0:
        raise ValueError(
            "rating['safety_factor'] must be at least 1.0, got %g" % safety
        )
    derating = _positive("rating['derating_factor']", rating["derating_factor"])
    if derating > 1.0:
        raise ValueError(
            "rating['derating_factor'] must not exceed 1.0, got %g" % derating
        )
    applied = _positive("rating['applied_nominal']", rating["applied_nominal"],
                        allow_zero=True)
    tol = _positive("rating['applied_tolerance_fraction']",
                    rating.get("applied_tolerance_fraction", 0.0), allow_zero=True)
    if tol >= 1.0:
        raise ValueError(
            "rating['applied_tolerance_fraction'] must be below 1.0, got %g" % tol
        )
    transient = _positive("rating['applied_transient_factor']",
                          rating.get("applied_transient_factor", 1.0))
    if transient < 1.0:
        raise ValueError(
            "rating['applied_transient_factor'] must be at least 1.0, got %g"
            % transient
        )
    unit = rating.get("unit", "")
    if not isinstance(unit, str):
        raise ValueError("rating['unit'] must be a string when present")
    return {
        "name": name,
        "boundary": boundary,
        "onset": onset,
        "safety_factor": safety,
        "derating_factor": derating,
        "applied_nominal": applied,
        "applied_tolerance_fraction": tol,
        "applied_transient_factor": transient,
        "unit": unit,
    }


def validate_requirements(requirements):
    """Return the normalised robustness-demonstration requirements."""
    if requirements is None:
        requirements = {}
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be a mapping")
    sample = requirements.get("min_sample_size", 5)
    if isinstance(sample, bool) or not isinstance(sample, int):
        raise ValueError("requirements['min_sample_size'] must be an integer")
    if sample < 1:
        raise ValueError(
            "requirements['min_sample_size'] must be at least 1, got %d" % sample
        )
    hours = _positive("requirements['min_duration_h']",
                      requirements.get("min_duration_h", 168.0))
    drift = _positive("requirements['max_drift_fraction']",
                      requirements.get("max_drift_fraction", 0.10))
    if drift >= 1.0:
        raise ValueError(
            "requirements['max_drift_fraction'] must be below 1.0, got %g" % drift
        )
    return {
        "min_sample_size": sample,
        "min_duration_h": hours,
        "max_drift_fraction": drift,
    }


def validate_demonstration(demonstration):
    """Return a normalised robustness-demonstration record."""
    if not isinstance(demonstration, dict):
        raise ValueError("demonstration must be a mapping")
    for key in ("rating", "stress_level", "sample_size", "duration_h"):
        if key not in demonstration:
            raise ValueError("demonstration missing required key '%s'" % key)
    rating_name = _name("demonstration['rating']", demonstration["rating"])
    stress = _positive("demonstration['stress_level']",
                       demonstration["stress_level"])
    sample = demonstration["sample_size"]
    if isinstance(sample, bool) or not isinstance(sample, int):
        raise ValueError("demonstration['sample_size'] must be an integer")
    if sample < 1:
        raise ValueError(
            "demonstration['sample_size'] must be at least 1, got %d" % sample
        )
    hours = _positive("demonstration['duration_h']",
                      demonstration["duration_h"])
    lost = demonstration.get("devices_lost", 0)
    if isinstance(lost, bool) or not isinstance(lost, int):
        raise ValueError("demonstration['devices_lost'] must be an integer")
    if lost < 0:
        raise ValueError("demonstration['devices_lost'] must not be negative")
    if lost > sample:
        raise ValueError(
            "demonstration['devices_lost'] %d exceeds the sample size %d"
            % (lost, sample)
        )
    drift = _positive("demonstration['drift_fraction']",
                      demonstration.get("drift_fraction", 0.0), allow_zero=True)
    return {
        "rating": rating_name,
        "stress_level": stress,
        "sample_size": sample,
        "duration_h": hours,
        "devices_lost": lost,
        "drift_fraction": drift,
    }


def derated_limit(boundary, derating_factor):
    """Return the derated envelope the application is allowed to reach."""
    value = _positive("boundary", boundary)
    factor = _positive("derating_factor", derating_factor)
    if factor > 1.0:
        raise ValueError("derating_factor must not exceed 1.0, got %g" % factor)
    return value * factor


def worst_case_stress(nominal, tolerance_fraction=0.0, transient_factor=1.0):
    """Return the worst-case applied stress a nominal condition can reach."""
    base = _positive("nominal", nominal, allow_zero=True)
    tol = _positive("tolerance_fraction", tolerance_fraction, allow_zero=True)
    if tol >= 1.0:
        raise ValueError("tolerance_fraction must be below 1.0, got %g" % tol)
    transient = _positive("transient_factor", transient_factor)
    if transient < 1.0:
        raise ValueError("transient_factor must be at least 1.0, got %g" % transient)
    return base * (1.0 + tol) * transient


def usage_ratio(applied, limit):
    """Return how much of a limit an applied stress consumes."""
    stress = _positive("applied", applied, allow_zero=True)
    bound = _positive("limit", limit)
    return stress / bound


def onset_headroom(onset, boundary):
    """Return how many times the declared boundary fits under the onset."""
    top = _positive("onset", onset)
    bound = _positive("boundary", boundary)
    return top / bound


def rating_supported_by_onset(onset, boundary, safety_factor):
    """Return True when the boundary sits below the onset by the safety factor."""
    headroom = onset_headroom(onset, boundary)
    factor = _positive("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1.0, got %g" % factor)
    return headroom >= factor - RATIO_TOLERANCE * max(1.0, factor)


def assess_demonstrations(rating, demonstrations, requirements=None):
    """Return the robustness-evidence outcome for one validated rating."""
    checked = validate_requirements(requirements)
    if demonstrations is None:
        demonstrations = []
    if not isinstance(demonstrations, (list, tuple)):
        raise ValueError("demonstrations must be a sequence")
    mine = []
    for item in demonstrations:
        record = validate_demonstration(item)
        if record["rating"] == rating["name"]:
            mine.append(record)
    if not mine:
        return {
            "outcome": "no-robustness-demonstration",
            "used": None,
            "count": 0,
            "stress_ratio": None,
        }
    boundary = rating["boundary"]
    # Strongest evidence first: the highest stress level, then the largest
    # sample, then the longest soak. Ordering is total, so the step is stable.
    mine.sort(key=lambda r: (r["stress_level"], r["sample_size"], r["duration_h"]),
              reverse=True)
    best = mine[0]
    ratio = best["stress_level"] / boundary
    if ratio < 1.0 - RATIO_TOLERANCE:
        outcome = "demonstration-below-boundary"
    elif best["sample_size"] < checked["min_sample_size"]:
        outcome = "demonstration-undersized"
    elif best["duration_h"] < checked["min_duration_h"] * (1.0 - RATIO_TOLERANCE):
        outcome = "demonstration-too-short"
    elif best["devices_lost"] > 0:
        outcome = "demonstration-lost-device"
    elif best["drift_fraction"] > checked["max_drift_fraction"] * (1.0 + RATIO_TOLERANCE):
        outcome = "demonstration-drift-excessive"
    else:
        outcome = "accepted"
    return {
        "outcome": outcome,
        "used": best,
        "count": len(mine),
        "stress_ratio": ratio,
    }


def assess_rating(rating, demonstrations=None, requirements=None):
    """Return the full per-rating record: onset margin, evidence and derating."""
    checked = validate_rating(rating)
    envelope = derated_limit(checked["boundary"], checked["derating_factor"])
    applied = worst_case_stress(
        checked["applied_nominal"],
        checked["applied_tolerance_fraction"],
        checked["applied_transient_factor"],
    )
    headroom = onset_headroom(checked["onset"], checked["boundary"])
    evidence = assess_demonstrations(checked, demonstrations, requirements)
    findings = []
    outcome = "accepted"
    if not rating_supported_by_onset(checked["onset"], checked["boundary"],
                                     checked["safety_factor"]):
        outcome = "onset-margin-short"
        findings.append(
            "%s: boundary %g%s sits only %.4fx under the onset, %.4fx required"
            % (checked["name"], checked["boundary"], checked["unit"], headroom,
               checked["safety_factor"])
        )
    if evidence["outcome"] != "accepted":
        if outcome == "accepted":
            outcome = evidence["outcome"]
        findings.append(
            "%s: robustness evidence is %s" % (checked["name"], evidence["outcome"])
        )
    usage = usage_ratio(applied, envelope)
    if usage > 1.0 + RATIO_TOLERANCE:
        if outcome == "accepted":
            outcome = "application-over-derated-limit"
        findings.append(
            "%s: worst-case stress %g%s exceeds the derated envelope %g%s"
            % (checked["name"], applied, checked["unit"], envelope, checked["unit"])
        )
    return {
        "name": checked["name"],
        "unit": checked["unit"],
        "boundary": checked["boundary"],
        "onset": checked["onset"],
        "onset_headroom": headroom,
        "required_headroom": checked["safety_factor"],
        "derated_limit": envelope,
        "worst_case_stress": applied,
        "derated_usage_ratio": usage,
        "evidence": evidence,
        "outcome": outcome,
        "accepted": outcome == "accepted",
        "findings": findings,
    }


def group_outcomes(records):
    """Return the record count grouped by outcome, in a fixed reporting order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    grouped = {}
    for record in records:
        if not isinstance(record, dict) or "outcome" not in record:
            raise ValueError("each record must be a mapping carrying 'outcome'")
        key = record["outcome"]
        grouped[key] = grouped.get(key, 0) + 1
    ordered = {}
    for key in _OUTCOME_ORDER:
        if key in grouped:
            ordered[key] = grouped[key]
    for key in sorted(grouped):
        if key not in ordered:
            ordered[key] = grouped[key]
    return ordered


def assess_maximum_ratings(spec):
    """Run the clause 7.2.9 maximum-rating and robustness assessment.

    spec keys: ratings (non-empty sequence), optional demonstrations and
    requirements.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "ratings" not in spec:
        raise ValueError("spec missing required key 'ratings'")
    ratings = spec["ratings"]
    if not isinstance(ratings, (list, tuple)) or not ratings:
        raise ValueError("spec['ratings'] must be a non-empty sequence")
    demonstrations = spec.get("demonstrations", [])
    requirements = validate_requirements(spec.get("requirements"))
    seen = set()
    records = []
    findings = []
    for entry in ratings:
        record = assess_rating(entry, demonstrations, requirements)
        if record["name"] in seen:
            raise ValueError("rating '%s' is declared twice" % record["name"])
        seen.add(record["name"])
        records.append(record)
        findings.extend(record["findings"])
    records.sort(key=lambda r: r["name"])
    accepted = all(r["accepted"] for r in records)
    return {
        "records": records,
        "grouped": group_outcomes(records),
        "requirements": requirements,
        "accepted": accepted,
        "findings": findings,
    }
