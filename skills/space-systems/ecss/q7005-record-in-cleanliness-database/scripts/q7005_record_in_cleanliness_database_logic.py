"""Recording IR contamination results in a cleanliness verification history.

Anchor: ECSS-Q-ST-70-05C, the provision on recording analysis results
into the cleanliness verification history a programme keeps for its
hardware (paraphrased into an implementable procedure; no standard text
is reproduced).

Procedure implemented here:

1. An entry is identified by what was verified, not by what it was
   called. Hardware item, surface zone and measurement method together
   form the key; a free-text description names nothing a later query
   can find.
2. A history is a history. A newer result does not delete an older one;
   it becomes the current level while the older entry stays where it
   is, because a cleanliness trend is the reason the record exists.
3. Values are held at the resolution the history is written at. Two
   analyses of the same surface differ in the sixth decimal of a
   quotient neither of them published, and comparing raw floats makes
   every resubmission look like a new result.
4. A second reading on a different day with the same value is a
   confirmation and is worth keeping as one. A second reading on the
   same day with a different value is a conflict, and it is held
   unresolved rather than overwritten by whichever arrived last.
5. A non-detect is stored as its quantitation bound. Storing a zero
   invents a measurement, and storing nothing loses the verification.
6. The trend across the last two entries is the output the record was
   kept for. A rise beyond a stated fraction is reported, and a trend
   taken across a bound is marked indicative, because a bound and a
   value are not the same kind of number.

Stdlib only, offline, deterministic.
"""

import datetime
import math

DISPOSITION_RECORDED = "recorded"
DISPOSITION_CONFIRMATION = "confirmation-recorded"
DISPOSITION_DUPLICATE = "duplicate-ignored"
DISPOSITION_CONFLICT = "conflict-unresolved"
DISPOSITION_REFUSED = "refused"

TREND_IMPROVING = "improving"
TREND_STABLE = "stable"
TREND_DEGRADING = "degrading"
TREND_UNKNOWN = "no-trend-yet"

DEFAULT_POLICY = {
    "level_resolution_mg_m2": 0.01,
    "degradation_fraction": 0.20,
}

LEVEL_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _identity(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def parse_date(text):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(text, datetime.date):
        return text
    if not isinstance(text, str):
        raise ValueError("date must be an ISO yyyy-mm-dd string, got %r" % (text,))
    parts = text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("date %r is not in yyyy-mm-dd form" % (text,))
    try:
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("date %r is not a real calendar date" % (text,))


def resolved_policy(policy=None):
    """Merge a caller policy over the defaults and validate it."""
    merged = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict):
            raise ValueError("policy must be a mapping")
        unknown = sorted(set(policy) - set(DEFAULT_POLICY))
        if unknown:
            raise ValueError("unknown policy keys: %s" % ", ".join(unknown))
        merged.update(policy)
    resolution = _numeric(
        "level_resolution_mg_m2", merged["level_resolution_mg_m2"], 0.0
    )
    if resolution <= 0.0:
        raise ValueError("level_resolution_mg_m2 must be greater than zero")
    _numeric("degradation_fraction", merged["degradation_fraction"], 0.0)
    return merged


def quantize(value, resolution):
    """Round a level onto the resolution the history is written at."""
    val = _numeric("value", value, 0.0)
    step = _numeric("resolution", resolution, 0.0)
    if step <= 0.0:
        raise ValueError("resolution must be greater than zero")
    return math.floor(val / step + 0.5) * step


def entry_key(record):
    """Identity of the thing verified: item, surface zone and method."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    return (
        _identity("item", record.get("item")),
        _identity("surface_zone", record.get("surface_zone")),
        _identity("method", record.get("method")),
    )


def validate_entry(record, policy=None):
    """Validate one verification record and return a normalized copy."""
    rules = resolved_policy(policy)
    key = entry_key(record)
    date = parse_date(record.get("verification_date"))
    detected = record.get("detected", True)
    if not isinstance(detected, bool):
        raise ValueError("detected must be a boolean")
    level = record.get("level_mg_m2")
    bound = record.get("quantitation_limit_mg_m2")
    if detected:
        if level is None:
            raise ValueError("a detection needs a level_mg_m2")
        stored = quantize(
            _numeric("level_mg_m2", level, 0.0), rules["level_resolution_mg_m2"]
        )
        stored_bound = None
    else:
        if level is not None:
            raise ValueError("a non-detect must not carry a level_mg_m2")
        if bound is None:
            raise ValueError("a non-detect needs a quantitation_limit_mg_m2")
        stored = None
        stored_bound = quantize(
            _numeric("quantitation_limit_mg_m2", bound, 0.0),
            rules["level_resolution_mg_m2"],
        )
    report = record.get("report_reference")
    if report is not None and (not isinstance(report, str) or not report.strip()):
        raise ValueError("report_reference must be a non-empty string when present")
    reportable = record.get("analysis_reportable", True)
    if not isinstance(reportable, bool):
        raise ValueError("analysis_reportable must be a boolean")
    return {
        "item": key[0],
        "surface_zone": key[1],
        "method": key[2],
        "verification_date": date,
        "detected": detected,
        "level_mg_m2": stored,
        "quantitation_limit_mg_m2": stored_bound,
        "report_reference": report.strip() if report else None,
        "analysis_reportable": reportable,
    }


def effective_level(entry):
    """The number an entry contributes: its level, or its bound."""
    if entry.get("detected", True):
        return entry["level_mg_m2"]
    return entry["quantitation_limit_mg_m2"]


def same_value(left, right):
    """True when two normalized entries hold the same stored result."""
    if left["detected"] != right["detected"]:
        return False
    return abs(effective_level(left) - effective_level(right)) <= LEVEL_TOLERANCE


def entries_for(history, key):
    """Entries in the history matching one identity key, oldest first."""
    if not isinstance(history, list):
        raise ValueError("history must be a list")
    matched = [
        e
        for e in history
        if (e["item"], e["surface_zone"], e["method"]) == tuple(key)
    ]
    return sorted(matched, key=lambda e: e["verification_date"])


def current_entry(history, key):
    """The newest entry held for one identity key, or None."""
    matched = entries_for(history, key)
    return matched[-1] if matched else None


def post_entry(history, record, policy=None):
    """Post one verification result into the history and say what happened."""
    if not isinstance(history, list):
        raise ValueError("history must be a list")
    rules = resolved_policy(policy)
    entry = validate_entry(record, rules)
    key = (entry["item"], entry["surface_zone"], entry["method"])
    findings = []

    if not entry["analysis_reportable"]:
        return {
            "disposition": DISPOSITION_REFUSED,
            "findings": ["source-analysis-was-never-reportable"],
            "history": list(history),
            "entry": entry,
            "becomes_current": False,
            "back_dated": False,
        }
    if not entry["report_reference"]:
        return {
            "disposition": DISPOSITION_REFUSED,
            "findings": ["entry-does-not-point-at-an-analysis-report"],
            "history": list(history),
            "entry": entry,
            "becomes_current": False,
            "back_dated": False,
        }

    held = entries_for(history, key)
    same_day = [
        e for e in held if e["verification_date"] == entry["verification_date"]
    ]
    if same_day:
        if all(same_value(e, entry) for e in same_day):
            return {
                "disposition": DISPOSITION_DUPLICATE,
                "findings": ["already-held-for-this-verification-date"],
                "history": list(history),
                "entry": entry,
                "becomes_current": False,
                "back_dated": False,
            }
        return {
            "disposition": DISPOSITION_CONFLICT,
            "findings": ["same-date-entry-disagrees-with-the-one-held"],
            "history": list(history),
            "entry": entry,
            "becomes_current": False,
            "back_dated": False,
        }

    earlier = [
        e for e in held if e["verification_date"] < entry["verification_date"]
    ]
    becomes_current = not held or entry["verification_date"] > held[-1][
        "verification_date"
    ]
    back_dated = bool(held) and not becomes_current
    if back_dated:
        findings.append("entry-is-back-dated-behind-the-current-record")

    disposition = DISPOSITION_RECORDED
    if earlier and same_value(earlier[-1], entry):
        disposition = DISPOSITION_CONFIRMATION

    updated = list(history)
    updated.append(entry)
    return {
        "disposition": disposition,
        "findings": findings,
        "history": updated,
        "entry": entry,
        "becomes_current": becomes_current,
        "back_dated": back_dated,
    }


def verification_trend(history, key, policy=None):
    """Trend across the last two entries held for one identity key."""
    rules = resolved_policy(policy)
    held = entries_for(history, key)
    if len(held) < 2:
        return {
            "key": tuple(key),
            "trend": TREND_UNKNOWN,
            "findings": [],
            "previous_level_mg_m2": None,
            "current_level_mg_m2": effective_level(held[-1]) if held else None,
        }
    previous, latest = held[-2], held[-1]
    before = effective_level(previous)
    after = effective_level(latest)
    findings = []
    if not previous["detected"] or not latest["detected"]:
        findings.append("trend-taken-across-a-bound-is-indicative-only")
    if abs(after - before) <= LEVEL_TOLERANCE:
        trend = TREND_STABLE
    elif after < before:
        trend = TREND_IMPROVING
    else:
        trend = TREND_DEGRADING
        if before > 0.0:
            rise = (after - before) / before
            if rise > rules["degradation_fraction"] + LEVEL_TOLERANCE:
                findings.append("rise-beyond-the-permitted-degradation-fraction")
    return {
        "key": tuple(key),
        "trend": trend,
        "findings": findings,
        "previous_level_mg_m2": before,
        "current_level_mg_m2": after,
    }


def build_history(records, policy=None):
    """Post a sequence of records and report every disposition in order."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    rules = resolved_policy(policy)
    history = []
    dispositions = []
    for record in records:
        result = post_entry(history, record, rules)
        history = result["history"]
        dispositions.append(
            {
                "item": result["entry"]["item"],
                "surface_zone": result["entry"]["surface_zone"],
                "method": result["entry"]["method"],
                "verification_date": result["entry"][
                    "verification_date"
                ].isoformat(),
                "disposition": result["disposition"],
                "findings": result["findings"],
            }
        )
    keys = []
    for entry in history:
        key = (entry["item"], entry["surface_zone"], entry["method"])
        if key not in keys:
            keys.append(key)
    return {
        "history": history,
        "dispositions": dispositions,
        "keys": keys,
        "accepted": sum(
            1
            for d in dispositions
            if d["disposition"]
            in (DISPOSITION_RECORDED, DISPOSITION_CONFIRMATION)
        ),
        "refused": [
            d for d in dispositions if d["disposition"] == DISPOSITION_REFUSED
        ],
        "conflicts": [
            d for d in dispositions if d["disposition"] == DISPOSITION_CONFLICT
        ],
    }
