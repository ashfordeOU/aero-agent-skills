#!/usr/bin/env python3
"""Radiated magnetic susceptibility purpose, ECSS-E-ST-20-07C clause 5.4.10.1.

Paraphrased aim, no verbatim standard text. The clause states why the test
exists rather than what the limit is: to show that a unit keeps working
while a magnetic field radiated from a loop held close to it washes over
its enclosure and its harness. A plan can run flawlessly and still not
produce that evidence -- the loop too far away, the band too narrow, no
required field strength on record, or nothing watching the unit while the
field is applied.

This module turns the aim into a deterministic grading:

  plan       -> valid or rejected
  loop       -> axial field actually produced at the declared standoff
  band       -> swept share of the aim band, worked across decades
  objectives -> the aims a plan serves and the ones it leaves unserved
  plan set   -> mean coverage, the plans that miss the aim, a set verdict

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance for values that should land exactly on a bound.
TOL = 1e-9

# Permeability of free space, henry per metre. Carried so a caller can move
# from field strength to flux density without a second constant.
VACUUM_PERMEABILITY_H_PER_M = 4.0e-7 * math.pi

# The aim's band: the low-frequency magnetic region where a nearby loop,
# rather than free space, is the coupling path. Hertz.
DEFAULT_AIM_BAND_HZ = (30.0, 50.0e3)

# Standoff between the radiating loop and the unit face the clause has in
# mind, metre. A loop held further away tests a weaker coupling than the aim.
DEFAULT_MAX_STANDOFF_M = 0.07

# Relative tolerance when deciding whether a sweep reaches a band edge.
BAND_EDGE_REL_TOL = 1e-9

OBJECTIVE_RADIATING_LOOP = "radiating-loop-source"
OBJECTIVE_LOOP_STANDOFF = "loop-standoff-distance"
OBJECTIVE_BAND_SPAN = "aim-band-span"
OBJECTIVE_FIELD_LEVEL = "required-field-strength"
OBJECTIVE_PERFORMANCE_WATCH = "performance-monitoring"

# Reported in this fixed order so two reviews of one plan read alike.
AIM_OBJECTIVES = (
    OBJECTIVE_RADIATING_LOOP,
    OBJECTIVE_LOOP_STANDOFF,
    OBJECTIVE_BAND_SPAN,
    OBJECTIVE_FIELD_LEVEL,
    OBJECTIVE_PERFORMANCE_WATCH,
)

RECOGNIZED_SOURCES = ("radiating-loop", "helmholtz-pair")

VERDICT_SERVED = "aim-served"
VERDICT_UNSERVED = "aim-unserved"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_most(value, limit, tol=TOL):
    """True when value stays under the limit, absorbing float error only."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def normalize_source(source):
    """Return the recognized radiating source for a raw designation."""
    if not isinstance(source, str):
        raise ValueError("source must be a string, got %r" % (source,))
    key = source.strip().lower()
    if key not in RECOGNIZED_SOURCES:
        raise ValueError(
            "unrecognized radiating source %r; the aim is a field radiated "
            "from a loop, recognized: %s" % (source, ", ".join(RECOGNIZED_SOURCES))
        )
    return key


def loop_axial_field_a_per_m(turns, current_a, radius_m, distance_m):
    """Magnetic field strength on the axis of a current-carrying loop.

    The loop's own turns and current set the field at its centre; the
    standoff divides it down by the cube of the slant distance. Written with
    a square root rather than a fractional power so the value does not move
    between platforms.
    """
    if isinstance(turns, bool) or not isinstance(turns, int):
        raise ValueError("turns must be a whole count, got %r" % (turns,))
    if turns <= 0:
        raise ValueError("turns must be > 0, got %d" % turns)
    current = _number({"v": current_a}, "v", "current_a")
    radius = _number({"v": radius_m}, "v", "radius_m")
    distance = _number({"v": distance_m}, "v", "distance_m")
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    if radius <= 0.0:
        raise ValueError("radius_m must be > 0, got %g" % radius)
    if distance < 0.0:
        raise ValueError("distance_m must be >= 0, got %g" % distance)
    slant_squared = radius * radius + distance * distance
    denominator = 2.0 * slant_squared * math.sqrt(slant_squared)
    return turns * current * radius * radius / denominator


def field_to_flux_density_t(field_a_per_m):
    """Convert a field strength in ampere per metre to a flux density."""
    field = _number({"v": field_a_per_m}, "v", "field_a_per_m")
    if field < 0.0:
        raise ValueError("field_a_per_m must be >= 0, got %g" % field)
    return VACUUM_PERMEABILITY_H_PER_M * field


def validate_plan(plan):
    """Validate one radiated magnetic susceptibility plan record."""
    where = "plan"
    if not isinstance(plan, dict):
        raise ValueError("%s: record must be a mapping" % where)
    identifier = plan.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("%s: id must be a non-empty string" % where)
    source = normalize_source(plan.get("source", ""))
    start = _number(plan, "sweep_start_hz", where)
    stop = _number(plan, "sweep_stop_hz", where)
    if start <= 0.0:
        raise ValueError("%s: sweep_start_hz must be > 0, got %g" % (where, start))
    if stop <= start:
        raise ValueError(
            "%s: sweep_stop_hz %g must exceed sweep_start_hz %g" % (where, stop, start)
        )
    standoff = _number(plan, "standoff_m", where)
    if standoff < 0.0:
        raise ValueError("%s: standoff_m must be >= 0, got %g" % (where, standoff))
    field = _number(plan, "required_field_a_per_m", where)
    if field < 0.0:
        raise ValueError(
            "%s: required_field_a_per_m must be >= 0, got %g" % (where, field)
        )
    monitored = _flag(plan, "performance_monitored", where)
    return {
        "id": identifier.strip(),
        "source": source,
        "sweep_start_hz": start,
        "sweep_stop_hz": stop,
        "standoff_m": standoff,
        "required_field_a_per_m": field,
        "performance_monitored": monitored,
    }


def band_edges_reached(sweep, band=DEFAULT_AIM_BAND_HZ):
    """Whether the sweep reaches the bottom and the top of the aim band."""
    if not isinstance(sweep, (list, tuple)) or len(sweep) != 2:
        raise ValueError("sweep must be a (start, stop) pair, got %r" % (sweep,))
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("band must be a (low, high) pair, got %r" % (band,))
    start = _number({"v": sweep[0]}, "v", "sweep.start")
    stop = _number({"v": sweep[1]}, "v", "sweep.stop")
    low = _number({"v": band[0]}, "v", "band.low")
    high = _number({"v": band[1]}, "v", "band.high")
    if start <= 0.0 or stop <= start:
        raise ValueError("sweep must be a positive increasing pair, got %r" % (sweep,))
    if low <= 0.0 or high <= low:
        raise ValueError("band must be a positive increasing pair, got %r" % (band,))
    reaches_bottom = start <= low or math.isclose(
        start, low, rel_tol=BAND_EDGE_REL_TOL, abs_tol=0.0
    )
    reaches_top = stop >= high or math.isclose(
        stop, high, rel_tol=BAND_EDGE_REL_TOL, abs_tol=0.0
    )
    return {
        "reaches_bottom": reaches_bottom,
        "reaches_top": reaches_top,
        "spans_band": reaches_bottom and reaches_top,
    }


def band_coverage_fraction(sweep, band=DEFAULT_AIM_BAND_HZ):
    """Swept share of the aim band, worked in the logarithmic domain.

    The band runs over several decades, so a linear share is dominated by
    the top of the sweep and a plan that skipped the bottom decade scores
    as nearly complete. Decades keep the two ends comparable.
    """
    band_edges_reached(sweep, band)  # validates both pairs, result unused here
    start = float(sweep[0])
    stop = float(sweep[1])
    low = float(band[0])
    high = float(band[1])
    overlap_low = max(start, low)
    overlap_high = min(stop, high)
    if overlap_high <= overlap_low:
        return 0.0
    band_decades = math.log10(high) - math.log10(low)
    overlap_decades = math.log10(overlap_high) - math.log10(overlap_low)
    if band_decades <= 0.0:
        raise ValueError("band must span at least one point in the log domain")
    return overlap_decades / band_decades


def grade_objectives(
    plan, band=DEFAULT_AIM_BAND_HZ, max_standoff_m=DEFAULT_MAX_STANDOFF_M
):
    """Grade the five aims of clause 5.4.10.1 against one validated plan."""
    record = validate_plan(plan)
    limit = _number({"v": max_standoff_m}, "v", "max_standoff_m")
    if limit <= 0.0:
        raise ValueError("max_standoff_m must be > 0, got %g" % limit)
    spans = band_edges_reached(
        (record["sweep_start_hz"], record["sweep_stop_hz"]), band
    )
    served = {
        OBJECTIVE_RADIATING_LOOP: record["source"] in RECOGNIZED_SOURCES,
        OBJECTIVE_LOOP_STANDOFF: at_most(record["standoff_m"], limit),
        OBJECTIVE_BAND_SPAN: spans["spans_band"],
        OBJECTIVE_FIELD_LEVEL: record["required_field_a_per_m"] > 0.0,
        OBJECTIVE_PERFORMANCE_WATCH: record["performance_monitored"],
    }
    unserved = [name for name in AIM_OBJECTIVES if not served[name]]
    return {
        "plan": record,
        "served": served,
        "unserved": unserved,
        "band_edges": spans,
        "coverage_fraction": band_coverage_fraction(
            (record["sweep_start_hz"], record["sweep_stop_hz"]), band
        ),
        "serves_aim": not unserved,
    }


def assess_plan_set(
    plans, band=DEFAULT_AIM_BAND_HZ, max_standoff_m=DEFAULT_MAX_STANDOFF_M
):
    """Aggregate the aim grading over a set of plans."""
    if not isinstance(plans, (list, tuple)) or len(plans) == 0:
        raise ValueError("plans: at least one plan is required")
    reports = []
    seen = set()
    for plan in plans:
        report = grade_objectives(plan, band, max_standoff_m)
        identifier = report["plan"]["id"]
        if identifier in seen:
            raise ValueError("plans: plan id %r appears twice" % identifier)
        seen.add(identifier)
        reports.append(report)

    missing = [r["plan"]["id"] for r in reports if not r["serves_aim"]]
    mean_coverage = sum(r["coverage_fraction"] for r in reports) / len(reports)
    findings = []
    for report in reports:
        for objective in report["unserved"]:
            findings.append(
                "plan %s leaves %s unserved" % (report["plan"]["id"], objective)
            )
    return {
        "plans": reports,
        "mean_coverage_fraction": mean_coverage,
        "plans_missing_the_aim": missing,
        "findings": findings,
        "verdict": VERDICT_SERVED if not findings else VERDICT_UNSERVED,
    }
