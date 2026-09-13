#!/usr/bin/env python3
"""Response steps for a discharge or event during a multipactor run.

Anchor: ECSS-E-ST-20-01C clause 8.5.3 (actions taken when a discharge or an
event appears during a multipactor qualification run). Paraphrased into an
implementable procedure; no standard text is reproduced.

Deterministic, offline, Python standard library only.
"""

import math

# Chamber-pressure at or below which the bench counts as a clean vacuum (Pa).
VACUUM_LIMIT_PA = 1.0e-4

# Default drive step-back, in decibels, for the repeat run.
DEFAULT_BACKOFF_DB = 3.0

# Default allowed spread between repeat onsets, in decibels.
DEFAULT_SPREAD_DB = 1.0

# Step-back applied to the lowest onset when capping the declarable level.
ONSET_CAP_FRACTION = 0.99

# Representation tolerance. It absorbs floating-point error at an inclusive
# limit; it never widens the allowed spread itself.
REL_TOL = 1e-12
ABS_TOL = 1e-15

ATTR_FACILITY = "facility-conditioning"
ATTR_UNIT = "unit-under-test"
ATTR_UNDETERMINED = "undetermined"

DISPOSITION_REPEAT = "corrected-and-repeat"
DISPOSITION_NONCONFORMANCE = "nonconformance-raised"
DISPOSITION_INVESTIGATION = "unexplained-event-investigation"

VERDICT_REPRODUCIBLE = "reproducible"
VERDICT_NOT_REPRODUCIBLE = "not-reproducible"

_REQUIRED_FLAGS = ("outgassing_burst", "fixture_fault", "seeding_active")


def _positive_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _at_or_below(value, limit):
    """Inclusive comparison that absorbs floating-point representation error."""
    return value < limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def validate_event_record(record):
    """Validate one bench event record and return a normalised copy."""
    if not isinstance(record, dict):
        raise ValueError("event record must be a mapping, got %r" % (record,))
    ident = record.get("event_id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("event_id must be a non-empty string")
    channels = record.get("channels_crossed")
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("event %s: channels_crossed must be a non-empty list" % ident)
    for name in channels:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "event %s: every crossed channel must be a non-empty string" % ident
            )
    normalised = {
        "event_id": ident,
        "channels_crossed": sorted(channels),
        "onset_level_w": _positive_float(
            record.get("onset_level_w"), "onset_level_w"
        ),
        "chamber_pressure_pa": _positive_float(
            record.get("chamber_pressure_pa"), "chamber_pressure_pa"
        ),
    }
    for flag in _REQUIRED_FLAGS:
        value = record.get(flag)
        if not isinstance(value, bool):
            raise ValueError(
                "event %s: %s must be a boolean, got %r" % (ident, flag, value)
            )
        normalised[flag] = value
    return normalised


def immediate_actions(record):
    """Ordered actions taken at the bench before anything is adjusted."""
    rec = validate_event_record(record)
    return [
        "remove the drive from the article and stop the ramp",
        "capture the onset state: %.4f W, %.3e Pa, channels %s, timestamp"
        % (
            rec["onset_level_w"],
            rec["chamber_pressure_pa"],
            ", ".join(rec["channels_crossed"]),
        ),
        "enter event %s in the run log before any bench adjustment" % rec["event_id"],
    ]


def attribute_event(record):
    """Attribute the excursion to the bench, to the unit, or leave it open."""
    rec = validate_event_record(record)
    clean_vacuum = _at_or_below(rec["chamber_pressure_pa"], VACUUM_LIMIT_PA)
    reasons = []
    if not clean_vacuum:
        reasons.append(
            "chamber-pressure %.3e Pa above the vacuum limit %.3e Pa"
            % (rec["chamber_pressure_pa"], VACUUM_LIMIT_PA)
        )
    if rec["outgassing_burst"]:
        reasons.append("outgassing-burst indicated at onset")
    if rec["fixture_fault"]:
        reasons.append("fixture-fault indicated at onset")
    if reasons:
        return {"attribution": ATTR_FACILITY, "reasons": reasons}
    if not rec["seeding_active"]:
        return {
            "attribution": ATTR_UNDETERMINED,
            "reasons": [
                "clean vacuum with no bench indication, but electron-seeding "
                "was inactive so the onset cannot be tied to the unit"
            ],
        }
    return {
        "attribution": ATTR_UNIT,
        "reasons": [
            "clean vacuum at %.3e Pa, no bench indication, seeding active"
            % rec["chamber_pressure_pa"]
        ],
    }


def drive_backoff_level_w(onset_level_w, backoff_db=DEFAULT_BACKOFF_DB):
    """Level the repeat run restarts from: the onset taken down by the backoff."""
    onset = _positive_float(onset_level_w, "onset_level_w")
    if isinstance(backoff_db, bool) or not isinstance(backoff_db, (int, float)):
        raise ValueError("backoff_db must be a number, got %r" % (backoff_db,))
    backoff = float(backoff_db)
    if not math.isfinite(backoff):
        raise ValueError("backoff_db must be finite, got %r" % (backoff_db,))
    if backoff <= 0.0:
        raise ValueError(
            "backoff_db must be > 0 -- a repeat never restarts at the onset level"
        )
    return onset / (10.0 ** (backoff / 10.0))


def onset_spread_db(onset_levels_w):
    """Decibel spread between the highest and the lowest repeat onset."""
    if not isinstance(onset_levels_w, (list, tuple)) or len(onset_levels_w) < 2:
        raise ValueError(
            "onset_levels_w needs at least two repeat onsets to judge a spread"
        )
    levels = [
        _positive_float(v, "onset_levels_w[%d]" % i)
        for i, v in enumerate(onset_levels_w)
    ]
    return 10.0 * math.log10(max(levels) / min(levels))


def reproducibility_verdict(onset_levels_w, allowed_spread_db=DEFAULT_SPREAD_DB):
    """Judge whether the repeat onsets land inside the allowed spread."""
    if isinstance(allowed_spread_db, bool) or not isinstance(
        allowed_spread_db, (int, float)
    ):
        raise ValueError("allowed_spread_db must be a number, got %r" % (allowed_spread_db,))
    allowed = float(allowed_spread_db)
    if not math.isfinite(allowed) or allowed <= 0.0:
        raise ValueError("allowed_spread_db must be a finite value > 0")
    spread = onset_spread_db(onset_levels_w)
    verdict = (
        VERDICT_REPRODUCIBLE
        if _at_or_below(spread, allowed)
        else VERDICT_NOT_REPRODUCIBLE
    )
    return {
        "spread_db": spread,
        "allowed_spread_db": allowed,
        "verdict": verdict,
        "lowest_onset_level_w": min(float(v) for v in onset_levels_w),
    }


def declarable_cap_w(lowest_onset_level_w):
    """Level the declaration is capped at once an onset is confirmed."""
    onset = _positive_float(lowest_onset_level_w, "lowest_onset_level_w")
    return onset * ONSET_CAP_FRACTION


def response_plan(record, backoff_db=DEFAULT_BACKOFF_DB):
    """Full ordered response for one event, from bench action to next step."""
    rec = validate_event_record(record)
    attribution = attribute_event(rec)
    steps = immediate_actions(rec)
    backoff_level = drive_backoff_level_w(rec["onset_level_w"], backoff_db)
    if attribution["attribution"] == ATTR_FACILITY:
        steps.append(
            "correct the bench condition (extend pump-down, bake out, repair "
            "the fixture) before any repeat"
        )
    elif attribution["attribution"] == ATTR_UNDETERMINED:
        steps.append(
            "restore the missing prerequisite (electron-seeding or a stable "
            "vacuum) before any repeat"
        )
    else:
        steps.append(
            "hold the bench condition unchanged so the onset can be re-approached"
        )
    steps.append(
        "restart the repeat run from %.4f W (%.2f dB below the onset)"
        % (backoff_level, float(backoff_db))
    )
    steps.append("re-approach the onset with every detection-channel armed")
    steps.append("carry the captured onset state into the report for event %s" % rec["event_id"])
    return {
        "event_id": rec["event_id"],
        "attribution": attribution["attribution"],
        "attribution_reasons": attribution["reasons"],
        "backoff_level_w": backoff_level,
        "steps": steps,
    }


def disposition(record, repeat_onsets_w=None, allowed_spread_db=DEFAULT_SPREAD_DB):
    """Close out one event: attribution plus repeat evidence give the disposition."""
    rec = validate_event_record(record)
    plan = response_plan(rec)
    result = {
        "event_id": rec["event_id"],
        "attribution": plan["attribution"],
        "backoff_level_w": plan["backoff_level_w"],
        "reproducibility": None,
        "declarable_cap_w": None,
    }
    if plan["attribution"] == ATTR_FACILITY:
        result["disposition"] = DISPOSITION_REPEAT
        result["rationale"] = (
            "excursion attributed to the bench; correct the condition and repeat"
        )
        return result
    if repeat_onsets_w is None:
        result["disposition"] = DISPOSITION_INVESTIGATION
        result["rationale"] = (
            "no repeat evidence on record; the onset stays an unexplained event"
        )
        return result
    if not isinstance(repeat_onsets_w, (list, tuple)) or not repeat_onsets_w:
        raise ValueError("repeat_onsets_w must be a non-empty list when given")
    if len(repeat_onsets_w) == 1:
        result["disposition"] = DISPOSITION_INVESTIGATION
        result["rationale"] = (
            "a single repeat cannot establish onset-reproducibility"
        )
        return result
    verdict = reproducibility_verdict(repeat_onsets_w, allowed_spread_db)
    result["reproducibility"] = verdict
    if (
        plan["attribution"] == ATTR_UNIT
        and verdict["verdict"] == VERDICT_REPRODUCIBLE
    ):
        result["disposition"] = DISPOSITION_NONCONFORMANCE
        result["declarable_cap_w"] = declarable_cap_w(
            min(verdict["lowest_onset_level_w"], rec["onset_level_w"])
        )
        result["rationale"] = (
            "onset repeated within %.2f dB in a clean vacuum; the finding "
            "belongs to the unit" % verdict["allowed_spread_db"]
        )
        return result
    result["disposition"] = DISPOSITION_INVESTIGATION
    result["rationale"] = (
        "onset not pinned down (attribution %s, repeat spread %.3f dB)"
        % (plan["attribution"], verdict["spread_db"])
    )
    return result
