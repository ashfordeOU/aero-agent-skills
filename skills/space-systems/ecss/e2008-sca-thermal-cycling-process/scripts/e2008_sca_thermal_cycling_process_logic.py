#!/usr/bin/env python3
"""Thermal cycling of a solar cell assembly run to its control drawing.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.7.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The cycling parameters of a solar cell assembly are not chosen at the
chamber. The number of cycles and the hot and cold extremes are properties
of the assembly, fixed on its control drawing at a stated issue, and the
run is judged against that record rather than against whatever the chamber
happened to do. Two assemblies of different build therefore carry different
cycling, and a run is meaningful only when the drawing it was run to can be
named.

What the process step decides:

    is the record usable     a drawing number, an issue, a cycle count, an
                             ordered pair of extremes, a dwell and a control
                             tolerance; an absent field is not a default
    was a cycle delivered    a cycle counts only when it reached both the
                             hot and the cold extreme inside the drawing
                             tolerance and held each of them for the dwell
                             the drawing fixes
    was the sample overstressed
                             a peak beyond the tolerance band is not a
                             generous cycle, it is an excursion outside the
                             drawing, and it outranks a shortfall

The tolerance band is symmetric about each extreme: the lower edge of the
hot band is the coldest a hot dwell may be and still count, the upper edge
is the hottest the sample may legally see. Both edges belong to the band.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DRAWING_FIELDS = (
    "drawing_number",
    "issue",
    "cycle_count",
    "hot_extreme_c",
    "cold_extreme_c",
    "dwell_minutes",
    "tolerance_k",
)

CYCLE_CREDITED = "credited"
CYCLE_OVERSTRESS = "overstress-excursion"
CYCLE_HOT_NOT_REACHED = "hot-extreme-not-reached"
CYCLE_COLD_NOT_REACHED = "cold-extreme-not-reached"
CYCLE_HOT_DWELL_SHORT = "hot-dwell-short"
CYCLE_COLD_DWELL_SHORT = "cold-dwell-short"

RUN_MEETS_CONTROL_DRAWING = "run-meets-control-drawing"
RUN_SHORT_OF_DRAWING_CYCLES = "run-short-of-drawing-cycles"
RUN_OUTSIDE_DRAWING_EXTREMES = "run-outside-drawing-extremes"

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


def _require_temperature(name, value):
    number = _require_number(name, value)
    if number <= -273.15:
        raise ValueError("%s %g C is at or below absolute zero" % (name, number))
    return number


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "%s must be a non-empty identifier taken from the control "
            "drawing, got %r" % (name, value)
        )
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


def validate_control_drawing(drawing):
    """Check the control drawing record carries every cycling parameter."""
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    missing = [field for field in DRAWING_FIELDS if field not in drawing]
    if missing:
        raise ValueError(
            "control drawing record is missing %s; a cycling parameter is "
            "taken from the drawing, never assumed" % ", ".join(missing)
        )
    number = _require_identifier("drawing_number", drawing["drawing_number"])
    issue = _require_identifier("issue", drawing["issue"])
    raw_count = drawing["cycle_count"]
    if isinstance(raw_count, bool) or not isinstance(raw_count, int):
        raise ValueError(
            "cycle_count must be a whole number of cycles, got %r" % (raw_count,)
        )
    if raw_count <= 0:
        raise ValueError("cycle_count must be at least one cycle, got %d" % raw_count)
    hot = _require_temperature("hot_extreme_c", drawing["hot_extreme_c"])
    cold = _require_temperature("cold_extreme_c", drawing["cold_extreme_c"])
    if not cold < hot:
        raise ValueError(
            "cold_extreme_c %g C must be below hot_extreme_c %g C" % (cold, hot)
        )
    dwell = _require_positive("dwell_minutes", drawing["dwell_minutes"])
    tolerance = _require_non_negative("tolerance_k", drawing["tolerance_k"])
    if tolerance * 2.0 >= hot - cold:
        raise ValueError(
            "tolerance_k %g K is so wide that the hot and cold bands overlap"
            % tolerance
        )
    return {
        "drawing_number": number,
        "issue": issue,
        "cycle_count": raw_count,
        "hot_extreme_c": hot,
        "cold_extreme_c": cold,
        "dwell_minutes": dwell,
        "tolerance_k": tolerance,
    }


def drawing_temperature_bands(drawing):
    """The hot and cold acceptance bands the control drawing fixes."""
    record = validate_control_drawing(drawing)
    tolerance = record["tolerance_k"]
    return {
        "hot_minimum_c": record["hot_extreme_c"] - tolerance,
        "hot_maximum_c": record["hot_extreme_c"] + tolerance,
        "cold_maximum_c": record["cold_extreme_c"] + tolerance,
        "cold_minimum_c": record["cold_extreme_c"] - tolerance,
        "range_k": record["hot_extreme_c"] - record["cold_extreme_c"],
    }


def cycle_disposition(cycle, drawing, index=1):
    """Decide what one recorded cycle is worth against the drawing."""
    record = validate_control_drawing(drawing)
    bands = drawing_temperature_bands(record)
    if not isinstance(cycle, dict):
        raise ValueError("cycle %d must be a mapping, got %r" % (index, cycle))
    peak_hot = _require_temperature(
        "cycle %d peak_hot_c" % index, cycle.get("peak_hot_c")
    )
    peak_cold = _require_temperature(
        "cycle %d peak_cold_c" % index, cycle.get("peak_cold_c")
    )
    hot_dwell = _require_non_negative(
        "cycle %d hot_dwell_minutes" % index, cycle.get("hot_dwell_minutes")
    )
    cold_dwell = _require_non_negative(
        "cycle %d cold_dwell_minutes" % index, cycle.get("cold_dwell_minutes")
    )
    if not peak_cold < peak_hot:
        raise ValueError(
            "cycle %d peak_cold_c %g C must be below peak_hot_c %g C"
            % (index, peak_cold, peak_hot)
        )
    disposition = CYCLE_CREDITED
    detail = ""
    if not _at_most(peak_hot, bands["hot_maximum_c"]):
        disposition = CYCLE_OVERSTRESS
        detail = "hot peak %.1f C is above the %.1f C band edge" % (
            peak_hot,
            bands["hot_maximum_c"],
        )
    elif not _at_least(peak_cold, bands["cold_minimum_c"]):
        disposition = CYCLE_OVERSTRESS
        detail = "cold peak %.1f C is below the %.1f C band edge" % (
            peak_cold,
            bands["cold_minimum_c"],
        )
    elif not _at_least(peak_hot, bands["hot_minimum_c"]):
        disposition = CYCLE_HOT_NOT_REACHED
        detail = "hot peak %.1f C never reached the %.1f C band" % (
            peak_hot,
            bands["hot_minimum_c"],
        )
    elif not _at_most(peak_cold, bands["cold_maximum_c"]):
        disposition = CYCLE_COLD_NOT_REACHED
        detail = "cold peak %.1f C never reached the %.1f C band" % (
            peak_cold,
            bands["cold_maximum_c"],
        )
    elif not _at_least(hot_dwell, record["dwell_minutes"]):
        disposition = CYCLE_HOT_DWELL_SHORT
        detail = "hot dwell %.1f min is below the %.1f min the drawing fixes" % (
            hot_dwell,
            record["dwell_minutes"],
        )
    elif not _at_least(cold_dwell, record["dwell_minutes"]):
        disposition = CYCLE_COLD_DWELL_SHORT
        detail = "cold dwell %.1f min is below the %.1f min the drawing fixes" % (
            cold_dwell,
            record["dwell_minutes"],
        )
    return {
        "index": index,
        "disposition": disposition,
        "credited": disposition == CYCLE_CREDITED,
        "overstress": disposition == CYCLE_OVERSTRESS,
        "peak_hot_c": peak_hot,
        "peak_cold_c": peak_cold,
        "achieved_range_k": peak_hot - peak_cold,
        "detail": detail,
    }


def audit_cycling_run(drawing, cycles):
    """Walk the recorded cycles and reconcile them with the drawing."""
    record = validate_control_drawing(drawing)
    if not isinstance(cycles, (list, tuple)) or not cycles:
        raise ValueError("cycles must be a non-empty list of recorded cycles")
    dispositions = []
    credited = 0
    overstress = 0
    findings = []
    for index, cycle in enumerate(cycles, 1):
        result = cycle_disposition(cycle, record, index)
        dispositions.append(result)
        if result["credited"]:
            credited += 1
        if result["overstress"]:
            overstress += 1
        if result["detail"]:
            findings.append("cycle %d %s: %s" % (index, result["disposition"], result["detail"]))
    shortfall = record["cycle_count"] - credited
    if shortfall > 0:
        findings.append(
            "%d credited cycles against the %d the control drawing fixes"
            % (credited, record["cycle_count"])
        )
    return {
        "drawing_number": record["drawing_number"],
        "issue": record["issue"],
        "required_cycles": record["cycle_count"],
        "recorded_cycles": len(dispositions),
        "credited_cycles": credited,
        "shortfall_cycles": max(shortfall, 0),
        "overstress_cycles": overstress,
        "dispositions": tuple(dispositions),
        "findings": findings,
    }


def assess_sca_thermal_cycling_process(case):
    """Full clause 6.4.3.7.2 audit of one solar cell assembly cycling run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    if "control_drawing" not in case:
        raise ValueError(
            "case is missing control_drawing; the cycle count and the extremes "
            "come from the drawing of the assembly under test"
        )
    audit = audit_cycling_run(case["control_drawing"], case.get("recorded_cycles"))
    if audit["overstress_cycles"] > 0:
        verdict = RUN_OUTSIDE_DRAWING_EXTREMES
    elif audit["shortfall_cycles"] > 0:
        verdict = RUN_SHORT_OF_DRAWING_CYCLES
    else:
        verdict = RUN_MEETS_CONTROL_DRAWING
    result = dict(audit)
    result["verdict"] = verdict
    result["meets_drawing"] = verdict == RUN_MEETS_CONTROL_DRAWING
    return result
