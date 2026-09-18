"""Blanking time that keeps a short dip from tripping an undervoltage protection.

Anchor: ECSS-E-ST-20-20C clause 5.4.3.3.1 (a dip below the undervoltage
threshold shorter than a defined time produces no trip). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
The blanking time is not a free parameter. It is squeezed between two figures
that come from opposite ends of the design:

* the lower bound is the longest disturbance the bus is allowed to impose and
  the load is expected to ride out -- a load step, a heater turning on, a
  limiter elsewhere going into limitation. The blanking time has to outlast
  that, with margin, or the protection trips on events that are part of normal
  operation.
* the upper bound is how long the load can actually sit below its threshold
  before the undervoltage does harm, less the time the detection chain and the
  switching element themselves consume. The blanking time has to fit inside
  what is left, with margin, or the protection is still counting when the
  event it was supposed to catch has already done its damage.

The two bounds can cross. When they do, no blanking time exists and the answer
is not a number but a finding: the transient envelope and the hold-up are
incompatible and one of them has to move.

Declared dip events are then walked against the chosen time. An event arms the
timer only while the bus actually sits below the trip threshold, so a dip that
never reaches the threshold is absorbed however long it lasts. Of the events
that do arm it, those longer than the blanking time trip. Each event carries
what it actually is -- a transient the bus is allowed to impose, or a real
undervoltage the protection exists to catch -- and the walk names both kinds of
wrong answer: a transient that trips, and a real undervoltage that is absorbed.
"""

import math

__all__ = [
    "TIME_TOLERANCE_S",
    "DEFAULT_BOUND_MARGIN",
    "EVENT_KINDS",
    "validate_timing",
    "lower_bound_s",
    "upper_bound_s",
    "blanking_window",
    "validate_events",
    "event_response",
    "walk_events",
    "assess_blanking_time",
]

# Two durations a design can place exactly on top of each other; absorb the
# representation error here rather than relaxing the engineering limit.
TIME_TOLERANCE_S = 1e-12

# Fraction of each bound held back so the blanking time is not sized onto the
# edge of a figure that is itself an estimate.
DEFAULT_BOUND_MARGIN = 0.2

# What a declared dip event actually is. The verdict compares what the
# protection does against what the event deserves.
EVENT_KINDS = ("transient", "undervoltage")


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def validate_timing(spec):
    """Return the timing budget as a mapping of floats, or raise.

    spec keys: blanking_time_s, longest_transient_s, hold_up_time_s,
    detection_latency_s, switching_latency_s, trip_threshold_v and optionally
    bound_margin.
    """
    if not isinstance(spec, dict):
        raise ValueError("timing spec must be a mapping")
    required = (
        "blanking_time_s",
        "longest_transient_s",
        "hold_up_time_s",
        "detection_latency_s",
        "switching_latency_s",
        "trip_threshold_v",
    )
    for key in required:
        if key not in spec:
            raise ValueError("timing spec missing required key '%s'" % key)

    margin = spec.get("bound_margin", DEFAULT_BOUND_MARGIN)
    margin = _non_negative("bound_margin", margin)
    if margin >= 1.0:
        raise ValueError("bound_margin must stay below one, got %r" % (margin,))

    timing = {
        "blanking_time_s": _positive("blanking_time_s", spec["blanking_time_s"]),
        "longest_transient_s": _positive(
            "longest_transient_s", spec["longest_transient_s"]
        ),
        "hold_up_time_s": _positive("hold_up_time_s", spec["hold_up_time_s"]),
        "detection_latency_s": _non_negative(
            "detection_latency_s", spec["detection_latency_s"]
        ),
        "switching_latency_s": _non_negative(
            "switching_latency_s", spec["switching_latency_s"]
        ),
        "trip_threshold_v": _positive("trip_threshold_v", spec["trip_threshold_v"]),
        "bound_margin": margin,
    }
    return timing


def lower_bound_s(timing):
    """Return the shortest blanking time that still rides out the transients."""
    return timing["longest_transient_s"] * (1.0 + timing["bound_margin"])


def upper_bound_s(timing):
    """Return the longest blanking time the hold-up budget still leaves.

    What remains of the hold-up after the detection chain and the switching
    element have taken their share is all the time the blanking may consume,
    and the margin is held back from the hold-up itself because that is the
    figure the load owns.
    """
    usable = timing["hold_up_time_s"] * (1.0 - timing["bound_margin"])
    return usable - timing["detection_latency_s"] - timing["switching_latency_s"]


def blanking_window(timing):
    """Return (lower_s, upper_s, feasible) for the blanking time."""
    lower = lower_bound_s(timing)
    upper = upper_bound_s(timing)
    feasible = upper >= lower - TIME_TOLERANCE_S
    return (lower, upper, feasible)


def validate_events(raw, trip_threshold_v):
    """Return the declared dip events as a list of mappings, or raise.

    Each event needs name, duration_s, minimum_voltage_v and kind.
    """
    if not isinstance(raw, (list, tuple)):
        raise ValueError("events must be a sequence")
    events = []
    seen = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("events[%d] must be a mapping" % i)
        for key in ("name", "duration_s", "minimum_voltage_v", "kind"):
            if key not in item:
                raise ValueError("events[%d] missing required key '%s'" % (i, key))
        name = item["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("events[%d]['name'] must be a non-empty string" % i)
        name = name.strip()
        if name in seen:
            raise ValueError("event name %r is used twice" % name)
        seen.add(name)

        kind = item["kind"]
        if not isinstance(kind, str) or kind.strip().lower() not in EVENT_KINDS:
            raise ValueError(
                "event %r kind must be one of %s" % (name, ", ".join(EVENT_KINDS))
            )
        kind = kind.strip().lower()

        duration = _positive("event %r duration_s" % name, item["duration_s"])
        minimum = _non_negative(
            "event %r minimum_voltage_v" % name, item["minimum_voltage_v"]
        )
        arms = minimum < trip_threshold_v - TIME_TOLERANCE_S
        if kind == "undervoltage" and not arms:
            raise ValueError(
                "event %r is declared an undervoltage but never reaches the "
                "trip threshold (%r V against %r V)"
                % (name, minimum, trip_threshold_v)
            )
        events.append(
            {
                "name": name,
                "duration_s": duration,
                "minimum_voltage_v": minimum,
                "kind": kind,
                "arms_timer": arms,
            }
        )
    if not events:
        raise ValueError("events must not be empty")
    return events


def event_response(event, blanking_time_s):
    """Return what the protection does with one declared dip event."""
    if not event["arms_timer"]:
        tripped = False
        reason = "never reaches the trip threshold, so the timer never arms"
    elif event["duration_s"] > blanking_time_s + TIME_TOLERANCE_S:
        tripped = True
        reason = "sits below the threshold for longer than the blanking time"
    else:
        tripped = False
        reason = "absorbed by the blanking time"
    expected = event["kind"] == "undervoltage"
    return {
        "name": event["name"],
        "kind": event["kind"],
        "duration_s": event["duration_s"],
        "arms_timer": event["arms_timer"],
        "tripped": tripped,
        "expected_trip": expected,
        "correct": tripped == expected,
        "reason": reason,
    }


def walk_events(events, blanking_time_s):
    """Return one response record per declared dip event."""
    return [event_response(event, blanking_time_s) for event in events]


def assess_blanking_time(spec):
    """Grade a declared undervoltage blanking time against clause 5.4.3.3.1."""
    if not isinstance(spec, dict):
        raise ValueError("blanking spec must be a mapping")
    timing = validate_timing(spec)
    lower, upper, feasible = blanking_window(timing)
    blanking = timing["blanking_time_s"]

    findings = []
    if not feasible:
        findings.append(
            "no blanking time exists: the transient envelope needs at least "
            "%.6f s and the hold-up budget leaves only %.6f s; the envelope or "
            "the hold-up has to move" % (lower, upper)
        )
    if blanking < lower - TIME_TOLERANCE_S:
        findings.append(
            "blanking time %.6f s is shorter than the %.6f s the longest "
            "permitted transient needs" % (blanking, lower)
        )
    if blanking > upper + TIME_TOLERANCE_S:
        findings.append(
            "blanking time %.6f s overruns the %.6f s the hold-up budget "
            "leaves once detection and switching are paid for"
            % (blanking, upper)
        )

    events = None
    walk = []
    if "events" in spec:
        events = validate_events(spec["events"], timing["trip_threshold_v"])
        walk = walk_events(events, blanking)
        for record in walk:
            if record["correct"]:
                continue
            if record["tripped"]:
                findings.append(
                    "transient %r trips: it %s" % (record["name"], record["reason"])
                )
            else:
                findings.append(
                    "undervoltage %r is not caught: it %s"
                    % (record["name"], record["reason"])
                )

    inside = (
        feasible
        and blanking >= lower - TIME_TOLERANCE_S
        and blanking <= upper + TIME_TOLERANCE_S
    )
    mishandled = [record["name"] for record in walk if not record["correct"]]
    compliant = inside and not mishandled
    return {
        "blanking_time_s": blanking,
        "lower_bound_s": lower,
        "upper_bound_s": upper,
        "window_feasible": feasible,
        "inside_window": inside,
        "lower_margin_s": blanking - lower,
        "upper_margin_s": upper - blanking,
        "event_count": len(walk),
        "tripped_events": [record["name"] for record in walk if record["tripped"]],
        "mishandled_events": mishandled,
        "events": walk,
        "verdict": "compliant" if compliant else "non-compliant",
        "findings": findings,
    }
