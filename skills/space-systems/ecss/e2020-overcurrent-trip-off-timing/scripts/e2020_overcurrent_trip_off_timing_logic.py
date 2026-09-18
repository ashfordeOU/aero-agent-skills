#!/usr/bin/env python3
"""Switch-off timing of a current limiter against the tabulated trip-time band.

Anchor: ECSS-E-ST-20C clause 5.2.4.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Once the load current passes the limiter's declared limit, the limiter
has to switch off -- and it has to do it inside a window, not merely
eventually. The window is tabulated against how far the current has gone
past the limit: a small excursion is given a long window, a hard fault a
very short one. Both edges of that window are requirements, and this is
the part that gets lost.

The late edge is the one everybody checks. A limiter that takes longer
than the tabulated maximum leaves the harness, the connector and the
upstream source carrying fault current for longer than the design
assumed, and the protection is not protecting.

The early edge is a requirement too. A limiter faster than the tabulated
minimum opens on things that were never faults -- a capacitive inrush, a
motor start, a transient the bus is expected to absorb -- and a unit that
sheds a healthy load on every switch-on has failed this clause just as
surely as a slow one, while looking impressively quick on the bench.

Four rules follow from the shape of the table.

The abscissa is a ratio, not a current. The window is fixed by the
measured current divided by the limiter's declared limit, so a
measurement quoted without the limit it was taken against cannot be
placed in the table at all.

Between tabulated rows the window is interpolated, not rounded to the
nearest row. Rounding down borrows a window the design was never granted
and rounding up refuses one it was.

Past the last tabulated row the window does not keep shrinking. The
table ends, so the last row governs and the result says it was clamped,
because a fault far beyond the table is being judged against an
extrapolation nobody tabulated.

Below the first tabulated row no switch-off is demanded. A limiter that
opens there is not non-compliant on timing, but it is worth naming: it
tripped where the table asked for nothing.

The comparison sense is inclusive at both edges. A trip landing exactly
on the minimum or exactly on the maximum meets the requirement, and the
tolerance below exists to absorb representation error rather than to
widen the window.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TRIP_NOT_REQUIRED = "trip-not-required-below-table"
WITHIN_TRIP_TIME_BAND = "within-tabulated-trip-time-band"
TRIPPED_TOO_EARLY = "switched-off-before-minimum-trip-time"
TRIPPED_TOO_LATE = "switched-off-after-maximum-trip-time"
DID_NOT_SWITCH_OFF = "did-not-switch-off"

TRIP_TIME_TABLE_NOT_ESTABLISHED = "trip-time-table-not-established"
CURRENT_LIMIT_NOT_ESTABLISHED = "declared-current-limit-not-established"
TRIP_TIMING_OUT_OF_BAND = "trip-timing-outside-tabulated-band"
TRIP_TIMING_WITHIN_BAND = "trip-timing-within-tabulated-band"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_trip_time_row(row):
    """Read one tabulated row: an overcurrent ratio and its two time edges."""
    if not isinstance(row, dict):
        raise ValueError("trip-time row must be a mapping, got %r" % (row,))
    ratio = _require_positive("current_ratio", row.get("current_ratio"))
    if not ratio > 1.0:
        raise ValueError(
            "current_ratio %g is not above one; the table starts where the "
            "current has already passed the limit" % ratio
        )
    minimum = _require_positive("min_trip_time_s", row.get("min_trip_time_s"))
    maximum = _require_positive("max_trip_time_s", row.get("max_trip_time_s"))
    if not _at_least(maximum, minimum):
        raise ValueError(
            "the row at ratio %g gives a maximum trip time %g s below its "
            "minimum %g s, which is not a window" % (ratio, maximum, minimum)
        )
    return {
        "current_ratio": ratio,
        "min_trip_time_s": minimum,
        "max_trip_time_s": maximum,
    }


def validate_trip_time_table(table):
    """Check the tabulated windows rise in ratio and never slow down."""
    if not isinstance(table, (list, tuple)):
        raise ValueError("table must be a sequence of trip-time rows")
    if len(table) < 2:
        raise ValueError(
            "a trip-time table needs at least two rows; one row is a single "
            "delay and cannot be interpolated"
        )
    rows = [validate_trip_time_row(row) for row in table]
    for earlier, later in zip(rows, rows[1:]):
        if not later["current_ratio"] > earlier["current_ratio"]:
            raise ValueError(
                "the table repeats or reverses at ratio %g; rows must rise in "
                "overcurrent ratio" % later["current_ratio"]
            )
        if later["max_trip_time_s"] > earlier["max_trip_time_s"]:
            raise ValueError(
                "the table allows a longer maximum trip time at ratio %g than "
                "at ratio %g; a harder overcurrent cannot buy more time"
                % (later["current_ratio"], earlier["current_ratio"])
            )
        if later["min_trip_time_s"] > earlier["min_trip_time_s"]:
            raise ValueError(
                "the table demands a longer minimum trip time at ratio %g than "
                "at ratio %g" % (later["current_ratio"], earlier["current_ratio"])
            )
    return tuple(rows)


def overcurrent_ratio(measured_current_a, limit_current_a):
    """How far the load current has gone past the limiter's declared limit."""
    measured = _require_positive("measured_current_a", measured_current_a)
    limit = _require_positive("limit_current_a", limit_current_a)
    return measured / limit


def bracket_rows(ratio, table):
    """The two tabulated rows an overcurrent ratio falls between.

    Returns None below the first row, where no switch-off is demanded, and
    the last row twice above the table, where the window stops shrinking.
    """
    rows = validate_trip_time_table(table)
    value = _require_positive("ratio", ratio)
    if value < rows[0]["current_ratio"] and not math.isclose(
        value, rows[0]["current_ratio"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return None
    if _at_least(value, rows[-1]["current_ratio"]):
        return rows[-1], rows[-1]
    for earlier, later in zip(rows, rows[1:]):
        if _at_most(value, later["current_ratio"]):
            return earlier, later
    return rows[-1], rows[-1]


def trip_time_band(ratio, table):
    """The minimum and maximum switch-off time tabulated for this ratio.

    Interpolates linearly between the bracketing rows; reports whether the
    ratio ran past the end of the table and was held at the last row.
    """
    bracket = bracket_rows(ratio, table)
    if bracket is None:
        return None
    earlier, later = bracket
    value = float(ratio)
    rows = validate_trip_time_table(table)
    clamped = bool(value > rows[-1]["current_ratio"]) and not math.isclose(
        value, rows[-1]["current_ratio"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    if later["current_ratio"] == earlier["current_ratio"]:
        return {
            "min_trip_time_s": later["min_trip_time_s"],
            "max_trip_time_s": later["max_trip_time_s"],
            "clamped_to_last_row": clamped,
        }
    span = later["current_ratio"] - earlier["current_ratio"]
    fraction = (value - earlier["current_ratio"]) / span
    return {
        "min_trip_time_s": earlier["min_trip_time_s"]
        + fraction * (later["min_trip_time_s"] - earlier["min_trip_time_s"]),
        "max_trip_time_s": earlier["max_trip_time_s"]
        + fraction * (later["max_trip_time_s"] - earlier["max_trip_time_s"]),
        "clamped_to_last_row": clamped,
    }


def validate_measurement(measurement):
    """Read one observed overcurrent event and what the limiter did about it."""
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    identifier = _require_label("measurement id", measurement.get("id"))
    if not identifier:
        raise ValueError("measurement id must not be blank")
    current = _require_positive(
        "measured_current_a on %s" % identifier,
        measurement.get("measured_current_a"),
    )
    switched_off = measurement.get("switched_off", True)
    if not isinstance(switched_off, bool):
        raise ValueError(
            "switched_off on %s must be true or false, got %r"
            % (identifier, switched_off)
        )
    trip_time = measurement.get("measured_trip_time_s")
    if switched_off:
        trip_time = _require_positive(
            "measured_trip_time_s on %s" % identifier, trip_time
        )
    elif trip_time is not None:
        raise ValueError(
            "%s reports a trip time but says it never switched off" % identifier
        )
    return {
        "id": identifier,
        "measured_current_a": current,
        "switched_off": switched_off,
        "measured_trip_time_s": trip_time,
    }


def deviation_fraction(trip_time_s, band):
    """How far outside its window a switch-off landed, relative to the edge it missed."""
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %r" % (band,))
    time_s = _require_positive("trip_time_s", trip_time_s)
    minimum = _require_positive("min_trip_time_s", band.get("min_trip_time_s"))
    maximum = _require_positive("max_trip_time_s", band.get("max_trip_time_s"))
    if not _at_least(time_s, minimum):
        return (minimum - time_s) / minimum
    if not _at_most(time_s, maximum):
        return (time_s - maximum) / maximum
    return 0.0


def switch_off_verdict(measurement, limit_current_a, table):
    """Place one observed event in the table and judge the switch-off it produced."""
    record = validate_measurement(measurement)
    ratio = overcurrent_ratio(record["measured_current_a"], limit_current_a)
    band = trip_time_band(ratio, table)
    verdict = {
        "id": record["id"],
        "measured_current_a": record["measured_current_a"],
        "overcurrent_ratio": ratio,
        "min_trip_time_s": None,
        "max_trip_time_s": None,
        "clamped_to_last_row": False,
        "measured_trip_time_s": record["measured_trip_time_s"],
        "deviation_fraction": 0.0,
    }
    if band is None:
        verdict["outcome"] = TRIP_NOT_REQUIRED
        verdict["compliant"] = True
        return verdict
    verdict["min_trip_time_s"] = band["min_trip_time_s"]
    verdict["max_trip_time_s"] = band["max_trip_time_s"]
    verdict["clamped_to_last_row"] = band["clamped_to_last_row"]
    if not record["switched_off"]:
        verdict["outcome"] = DID_NOT_SWITCH_OFF
        verdict["compliant"] = False
        return verdict
    time_s = record["measured_trip_time_s"]
    verdict["deviation_fraction"] = deviation_fraction(time_s, band)
    if not _at_least(time_s, band["min_trip_time_s"]):
        verdict["outcome"] = TRIPPED_TOO_EARLY
        verdict["compliant"] = False
    elif not _at_most(time_s, band["max_trip_time_s"]):
        verdict["outcome"] = TRIPPED_TOO_LATE
        verdict["compliant"] = False
    else:
        verdict["outcome"] = WITHIN_TRIP_TIME_BAND
        verdict["compliant"] = True
    return verdict


def measurement_verdicts(measurements, limit_current_a, table):
    """Judge every observed overcurrent event, in record order."""
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("measurements must be a sequence of event records")
    if not measurements:
        raise ValueError(
            "no overcurrent event was recorded, so the switch-off timing has "
            "not been demonstrated at any point"
        )
    verdicts = []
    seen = set()
    for measurement in measurements:
        verdict = switch_off_verdict(measurement, limit_current_a, table)
        if verdict["id"] in seen:
            raise ValueError("duplicate measurement id %r" % verdict["id"])
        seen.add(verdict["id"])
        verdicts.append(verdict)
    return tuple(verdicts)


def worst_measurement(verdicts):
    """The event that missed its window by the widest relative margin."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    return max(verdicts, key=lambda verdict: verdict["deviation_fraction"])


def assess_overcurrent_trip_timing(case):
    """Full clause 5.2.4.1.1 switch-off timing decision for one limiter."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "limit_current_a": None,
        "measurement_verdicts": (),
        "worst_measurement_id": None,
        "worst_deviation_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    table = case.get("trip_time_table")
    if table is None:
        findings.append(
            "no trip-time table is declared, so there is no window any "
            "switch-off time can be judged against"
        )
        result["verdict"] = TRIP_TIME_TABLE_NOT_ESTABLISHED
        return result
    rows = validate_trip_time_table(table)

    limit = case.get("limit_current_a")
    if limit is None:
        findings.append(
            "no declared current limit is given, so a measured current cannot "
            "be turned into the overcurrent ratio the table is indexed on"
        )
        result["verdict"] = CURRENT_LIMIT_NOT_ESTABLISHED
        return result
    result["limit_current_a"] = _require_positive("limit_current_a", limit)

    verdicts = measurement_verdicts(case.get("measurements"), limit, table)
    result["measurement_verdicts"] = verdicts

    worst = worst_measurement(verdicts)
    result["worst_measurement_id"] = worst["id"]
    result["worst_deviation_fraction"] = worst["deviation_fraction"]

    for verdict in verdicts:
        if verdict["clamped_to_last_row"]:
            advisories.append(
                "event %s sits at a ratio of %.3g, past the last tabulated row "
                "at %.3g; it is judged against that row rather than an "
                "extrapolation"
                % (
                    verdict["id"],
                    verdict["overcurrent_ratio"],
                    rows[-1]["current_ratio"],
                )
            )
        if verdict["outcome"] == TRIP_NOT_REQUIRED and verdict[
            "measured_trip_time_s"
        ] is not None:
            advisories.append(
                "event %s switched off at a ratio of %.3g, below the first "
                "tabulated row at %.3g, where no switch-off was demanded"
                % (
                    verdict["id"],
                    verdict["overcurrent_ratio"],
                    rows[0]["current_ratio"],
                )
            )
        if verdict["compliant"]:
            continue
        if verdict["outcome"] == DID_NOT_SWITCH_OFF:
            findings.append(
                "event %s left the limiter conducting at a ratio of %.3g, where "
                "the table demands a switch-off within %.3g s"
                % (
                    verdict["id"],
                    verdict["overcurrent_ratio"],
                    verdict["max_trip_time_s"],
                )
            )
            continue
        findings.append(
            "event %s switched off in %.3g s at a ratio of %.3g, outside the "
            "tabulated %.3g s to %.3g s window by %.3g per cent"
            % (
                verdict["id"],
                verdict["measured_trip_time_s"],
                verdict["overcurrent_ratio"],
                verdict["min_trip_time_s"],
                verdict["max_trip_time_s"],
                verdict["deviation_fraction"] * 100.0,
            )
        )

    if findings:
        result["verdict"] = TRIP_TIMING_OUT_OF_BAND
        return result

    result["verdict"] = TRIP_TIMING_WITHIN_BAND
    return result
