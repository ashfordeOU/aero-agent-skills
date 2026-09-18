#!/usr/bin/env python3
"""Deciding whether a retriggerable latching current limiter turns on only
when the bus really has come up, and not on a brief excursion above the
enable point.

Anchor: ECSS-E-ST-20-20C clause 5.4.4.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable limiter watches the bus and enables itself when the bus
rises past an enable point. A bus is a noisy place: a neighbouring load
switching off, a transient on the primary side or the tail of a fault
recovery can all push the rail briefly past that point without the bus
having actually come back. The clause exists so that those excursions
leave the limiter off.

The mechanism that delivers it is a confirmation time -- the enable
condition has to hold continuously for a declared interval before the
output is allowed on. That makes the sizing a two-sided problem, and
both sides are graded here:

    too short    a nuisance excursion outlasts the confirmation time and
                 the limiter turns on into a bus that is not there
    too long     a genuine enable request is swallowed and the load
                 never comes up, which is the failure the designer does
                 not see in a noise test

So the feasible confirmation window is bounded below by the longest
nuisance excursion the design has to ride through and above by the
shortest genuine request it has to honour, each with its own margin. An
empty window is a real finding: it says no confirmation time satisfies
both duties and the thresholds or the hysteresis have to move instead.

Dwell is measured from the sampled waveform by interpolating the
crossings of the enable point rather than by counting samples, because
a sample-counted dwell is quantised by the logging rate and reports an
excursion that is one sample-interval shorter or longer than the one the
hardware saw.

The margins, the hysteresis floor and the recovery rule below are a
declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

EXCURSION_NUISANCE = "enable-excursion-nuisance"
EXCURSION_REQUEST = "enable-request-genuine"

EXCURSION_KINDS = (EXCURSION_NUISANCE, EXCURSION_REQUEST)

EVENT_BLANKED = "enable-excursion-blanked"
EVENT_ADMITTED = "enable-excursion-admitted"
EVENT_HONOURED = "enable-request-honoured"
EVENT_SUPPRESSED = "enable-request-suppressed"
EVENT_MARGIN_THIN = "enable-confirmation-margin-thin"
EVENT_UNRESOLVED = "enable-excursion-unresolved"

EVENT_STANDINGS = (
    EVENT_BLANKED,
    EVENT_ADMITTED,
    EVENT_HONOURED,
    EVENT_SUPPRESSED,
    EVENT_MARGIN_THIN,
    EVENT_UNRESOLVED,
)

_STANDING_SEVERITY = {
    EVENT_UNRESOLVED: 4,
    EVENT_ADMITTED: 3,
    EVENT_SUPPRESSED: 2,
    EVENT_MARGIN_THIN: 1,
    EVENT_HONOURED: 0,
    EVENT_BLANKED: 0,
}

BLANKING_NOT_EVALUATED = "rlcl-enable-blanking-not-evaluated"
BLANKING_TRANSIENT_ADMITTED = "rlcl-enable-blanking-transient-admitted"
BLANKING_REQUEST_SUPPRESSED = "rlcl-enable-blanking-request-suppressed"
BLANKING_MARGIN_THIN = "rlcl-enable-blanking-margin-thin"
BLANKING_ADEQUATE = "rlcl-enable-blanking-adequate"

BLANKING_VERDICTS = (
    BLANKING_NOT_EVALUATED,
    BLANKING_TRANSIENT_ADMITTED,
    BLANKING_REQUEST_SUPPRESSED,
    BLANKING_MARGIN_THIN,
    BLANKING_ADEQUATE,
)

DEFAULT_ENABLE_BLANKING_POLICY = {
    "nuisance_margin_fraction": 0.25,
    "request_margin_fraction": 0.20,
    "min_enable_hysteresis_v": 0.5,
    "require_recovery_below_release": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_unit_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number < 1.0:
        raise ValueError(
            "%s must be at least zero and below one, got %r" % (name, value)
        )
    return number


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or _close(value, bound)


def _at_most(value, bound):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or _close(value, bound)


def validate_enable_blanking_policy(policy):
    """Check a blanking policy is usable before any excursion is judged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_unit_fraction(
        "nuisance_margin_fraction", policy.get("nuisance_margin_fraction")
    )
    _require_unit_fraction(
        "request_margin_fraction", policy.get("request_margin_fraction")
    )
    _require_non_negative(
        "min_enable_hysteresis_v", policy.get("min_enable_hysteresis_v")
    )
    if not isinstance(policy.get("require_recovery_below_release"), bool):
        raise ValueError(
            "require_recovery_below_release must be a boolean, got %r"
            % (policy.get("require_recovery_below_release"),)
        )
    return policy


def validate_enable_thresholds(thresholds, policy=DEFAULT_ENABLE_BLANKING_POLICY):
    """Check the enable and release points make a usable hysteresis band."""
    validate_enable_blanking_policy(policy)
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be a mapping, got %r" % (thresholds,))
    enable_v = _require_positive(
        "enable_threshold_v", thresholds.get("enable_threshold_v")
    )
    release_v = _require_non_negative(
        "release_threshold_v", thresholds.get("release_threshold_v")
    )
    if release_v >= enable_v:
        raise ValueError(
            "release_threshold_v %r must sit below enable_threshold_v %r; a "
            "band that is the wrong way up chatters instead of latching"
            % (release_v, enable_v)
        )
    hysteresis_v = enable_v - release_v
    floor_v = float(policy["min_enable_hysteresis_v"])
    if hysteresis_v < floor_v and not _close(hysteresis_v, floor_v):
        raise ValueError(
            "hysteresis of %.4f V is below the %.4f V floor a retriggerable "
            "enable needs to stay out of chatter" % (hysteresis_v, floor_v)
        )
    return {
        "enable_threshold_v": enable_v,
        "release_threshold_v": release_v,
        "hysteresis_v": hysteresis_v,
    }


def validate_waveform(samples):
    """Check a sampled bus-voltage trace before any dwell is taken from it."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError(
            "samples must be a sequence of at least two (time, volt) pairs, "
            "got %r" % (samples,)
        )
    points = []
    last_t = None
    for entry in samples:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("sample must be a (time, volt) pair, got %r" % (entry,))
        time_s = _require_non_negative("sample time_s", entry[0])
        volt_v = _require_number("sample volt_v", entry[1])
        if last_t is not None and time_s <= last_t:
            raise ValueError(
                "sample times must strictly increase; %r follows %r"
                % (time_s, last_t)
            )
        last_t = time_s
        points.append((time_s, volt_v))
    return tuple(points)


def _crossing_time(t0, v0, t1, v1, level):
    """Interpolated instant the trace passes a level between two samples."""
    span = v1 - v0
    if span == 0.0:
        raise ValueError(
            "a level crossing cannot be interpolated across a flat segment"
        )
    return t0 + (level - v0) * (t1 - t0) / span


def excursions_above(samples, level_v):
    """Every interval the trace spends above a level, with dwell and peak."""
    points = validate_waveform(samples)
    level = _require_number("level_v", level_v)
    found = []
    start_t = None
    peak_v = None
    prev_t, prev_v = points[0]
    if prev_v > level:
        start_t = prev_t
        peak_v = prev_v
    for time_s, volt_v in points[1:]:
        above = volt_v > level
        was_above = prev_v > level
        if above and not was_above:
            start_t = _crossing_time(prev_t, prev_v, time_s, volt_v, level)
            peak_v = volt_v
        elif above and was_above:
            peak_v = max(peak_v, volt_v)
        elif was_above and not above:
            end_t = _crossing_time(prev_t, prev_v, time_s, volt_v, level)
            found.append(
                {
                    "start_s": start_t,
                    "end_s": end_t,
                    "dwell_s": end_t - start_t,
                    "peak_v": peak_v,
                    "closed": True,
                }
            )
            start_t = None
            peak_v = None
        prev_t, prev_v = time_s, volt_v
    if start_t is not None:
        end_t = points[-1][0]
        found.append(
            {
                "start_s": start_t,
                "end_s": end_t,
                "dwell_s": end_t - start_t,
                "peak_v": peak_v,
                "closed": False,
            }
        )
    return tuple(found)


def longest_dwell_above(samples, level_v):
    """Dwell of the longest excursion above a level; zero when there is none."""
    found = excursions_above(samples, level_v)
    if not found:
        return 0.0
    return max(entry["dwell_s"] for entry in found)


def categorize_excursion_kind(kind):
    """Name an excursion kind and refuse one this clause does not grade."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("excursion kind must be a non-empty string, got %r" % (kind,))
    name = kind.strip()
    if name not in EXCURSION_KINDS:
        raise ValueError(
            "unrecognised excursion kind %r; known kinds are %s"
            % (name, ", ".join(EXCURSION_KINDS))
        )
    return name


def measure_event(event, thresholds, policy=DEFAULT_ENABLE_BLANKING_POLICY):
    """Reduce one declared event to a dwell above the enable point."""
    validate_enable_blanking_policy(policy)
    if not isinstance(event, dict):
        raise ValueError("event must be a mapping, got %r" % (event,))
    identifier = event.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("event is missing a non-empty id, got %r" % (identifier,))
    kind = categorize_excursion_kind(event.get("kind"))

    record = {
        "id": identifier.strip(),
        "kind": kind,
        "gaps": [],
        "recovered": True,
        "peak_v": None,
    }

    if "samples" in event:
        found = excursions_above(event["samples"], thresholds["enable_threshold_v"])
        if not found:
            record["dwell_s"] = 0.0
            record["peak_v"] = max(v for _, v in validate_waveform(event["samples"]))
        else:
            worst = max(found, key=lambda entry: entry["dwell_s"])
            record["dwell_s"] = worst["dwell_s"]
            record["peak_v"] = worst["peak_v"]
            if not worst["closed"]:
                record["recovered"] = False
        if kind == EXCURSION_NUISANCE and policy["require_recovery_below_release"]:
            tail_v = validate_waveform(event["samples"])[-1][1]
            if tail_v > thresholds["release_threshold_v"]:
                record["recovered"] = False
    elif "dwell_s" in event:
        record["dwell_s"] = _require_non_negative("dwell_s", event.get("dwell_s"))
    else:
        raise ValueError(
            "event %r declares neither a sampled waveform nor a dwell_s, so "
            "there is nothing to measure" % (record["id"],)
        )

    if not record["recovered"]:
        record["gaps"].append(
            "the excursion never settles back below the release point, so the "
            "enable condition has no resolved state to grade"
        )
    return record


def grade_event(record, confirmation_time_s, policy=DEFAULT_ENABLE_BLANKING_POLICY):
    """Say what one measured event does to a candidate confirmation time."""
    validate_enable_blanking_policy(policy)
    if not isinstance(record, dict) or "dwell_s" not in record:
        raise ValueError("record must be a measured event mapping, got %r" % (record,))
    confirmation = _require_positive("confirmation_time_s", confirmation_time_s)
    dwell = _require_non_negative("dwell_s", record.get("dwell_s"))

    if not record.get("recovered", True):
        return EVENT_UNRESOLVED

    if record["kind"] == EXCURSION_NUISANCE:
        if _at_least(dwell, confirmation):
            return EVENT_ADMITTED
        margin = float(policy["nuisance_margin_fraction"])
        if not _at_most(dwell * (1.0 + margin), confirmation):
            return EVENT_MARGIN_THIN
        return EVENT_BLANKED

    if not _at_least(dwell, confirmation):
        return EVENT_SUPPRESSED
    margin = float(policy["request_margin_fraction"])
    if not _at_least(dwell * (1.0 - margin), confirmation):
        return EVENT_MARGIN_THIN
    return EVENT_HONOURED


def feasible_confirmation_window(records, policy=DEFAULT_ENABLE_BLANKING_POLICY):
    """Bounds a confirmation time has to sit between to serve both duties."""
    validate_enable_blanking_policy(policy)
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    nuisance = [r["dwell_s"] for r in records if r["kind"] == EXCURSION_NUISANCE]
    requests = [r["dwell_s"] for r in records if r["kind"] == EXCURSION_REQUEST]
    lower_s = None
    upper_s = None
    if nuisance:
        lower_s = max(nuisance) * (1.0 + float(policy["nuisance_margin_fraction"]))
    if requests:
        upper_s = min(requests) * (1.0 - float(policy["request_margin_fraction"]))
    is_open = True
    if lower_s is not None and upper_s is not None:
        is_open = _at_most(lower_s, upper_s)
    return {"lower_s": lower_s, "upper_s": upper_s, "open": is_open}


def recommended_confirmation_time_s(records, policy=DEFAULT_ENABLE_BLANKING_POLICY):
    """A confirmation time inside the window, balanced between its ends."""
    window = feasible_confirmation_window(records, policy)
    if not window["open"]:
        raise ValueError(
            "no confirmation time serves both duties: the nuisance floor of "
            "%.6f s sits above the request ceiling of %.6f s"
            % (window["lower_s"], window["upper_s"])
        )
    if window["lower_s"] is None and window["upper_s"] is None:
        raise ValueError("neither bound is constrained, so nothing can be recommended")
    if window["lower_s"] is None:
        return window["upper_s"]
    if window["upper_s"] is None:
        return window["lower_s"]
    if window["lower_s"] == 0.0:
        return window["upper_s"]
    return math.sqrt(window["lower_s"] * window["upper_s"])


def assess_enable_blanking(design, policy=DEFAULT_ENABLE_BLANKING_POLICY):
    """Full clause 5.4.4.3.1 judgement of a retriggerable enable design."""
    validate_enable_blanking_policy(policy)
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (design,))
    thresholds = validate_enable_thresholds(design.get("thresholds"), policy)
    confirmation = _require_positive(
        "confirmation_time_s", design.get("confirmation_time_s")
    )
    events = design.get("events")
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("design is missing a non-empty events sequence")

    records = [measure_event(event, thresholds, policy) for event in events]
    identifiers = [record["id"] for record in records]
    duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
    if duplicates:
        raise ValueError("event declared twice: %s" % (", ".join(duplicates),))

    for record in records:
        record["standing"] = grade_event(record, confirmation, policy)

    grouped = {standing: [] for standing in EVENT_STANDINGS}
    for record in records:
        grouped[record["standing"]].append(record["id"])

    window = feasible_confirmation_window(records, policy)

    findings = []
    for record in records:
        for gap in record["gaps"]:
            findings.append("%s: %s" % (record["id"], gap))
    for identifier in grouped[EVENT_ADMITTED]:
        findings.append(
            "%s: the excursion outlasts the %.6f s confirmation time, so the "
            "limiter turns on into a bus that has not come back"
            % (identifier, confirmation)
        )
    for identifier in grouped[EVENT_SUPPRESSED]:
        findings.append(
            "%s: the request is shorter than the %.6f s confirmation time, so "
            "a real turn-on is swallowed" % (identifier, confirmation)
        )
    if not window["open"]:
        findings.append(
            "no confirmation time serves both duties: the nuisance floor of "
            "%.6f s sits above the request ceiling of %.6f s, so the "
            "thresholds or the hysteresis have to move"
            % (window["lower_s"], window["upper_s"])
        )

    result = {
        "thresholds": thresholds,
        "confirmation_time_s": confirmation,
        "events": records,
        "standings": grouped,
        "window": window,
        "findings": findings,
    }

    if grouped[EVENT_UNRESOLVED]:
        result["verdict"] = BLANKING_NOT_EVALUATED
    elif grouped[EVENT_ADMITTED]:
        result["verdict"] = BLANKING_TRANSIENT_ADMITTED
    elif grouped[EVENT_SUPPRESSED]:
        result["verdict"] = BLANKING_REQUEST_SUPPRESSED
    elif grouped[EVENT_MARGIN_THIN] or not window["open"]:
        result["verdict"] = BLANKING_MARGIN_THIN
    else:
        result["verdict"] = BLANKING_ADEQUATE
    return result


def worst_standing(records):
    """The standing a set of events is reported at: the worst one present."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict) or record.get("standing") not in (
            _STANDING_SEVERITY
        ):
            raise ValueError("record carries no known standing: %r" % (record,))
        if worst is None or (
            _STANDING_SEVERITY[record["standing"]] > _STANDING_SEVERITY[worst]
        ):
            worst = record["standing"]
    return worst
