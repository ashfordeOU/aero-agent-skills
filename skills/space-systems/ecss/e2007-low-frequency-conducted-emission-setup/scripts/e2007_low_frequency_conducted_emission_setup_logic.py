#!/usr/bin/env python3
"""Low-frequency conducted-emission bench setup, ECSS-E-ST-20-07C 5.4.2.3.

Paraphrased procedure, no verbatim standard text. The clause builds the
low-frequency conducted-emission arrangement on top of the standard test
configuration: the unit sits on a bonded ground plane, each power lead runs
through its stabilisation network at a controlled height above the plane,
and the current probe is clamped at a fixed offset from the unit connector.
This module turns that arrangement into a deterministic conformance check:

  ground plane -> footprint margin and bond resistance
  lead runs    -> probe offset, harness height, separation, network present
  deviations   -> findings (out of window) and limitations (at the edge)

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Millimetre comparison tolerance. Window edges are sums and differences of
# float dimensions, so an exactly-met edge can land a few units in the last
# place outside. The tolerance absorbs representation error only; it never
# widens the engineering window.
MM_TOL = 1e-9

# Ohm-side tolerance, same reasoning on the bond resistance.
MOHM_TOL = 1e-9

# Nominal offset of the current probe from the unit connector, millimetre,
# with the arrangement tolerance the clause is built around.
DEFAULT_PROBE_OFFSET_MM = 50.0
DEFAULT_PROBE_OFFSET_TOL_MM = 5.0

# Nominal height of the measured harness above the ground plane, millimetre.
DEFAULT_HARNESS_HEIGHT_MM = 50.0
DEFAULT_HARNESS_HEIGHT_TOL_MM = 5.0

# Largest acceptable unit-to-plane bond resistance, milliohm.
DEFAULT_MAX_BOND_RESISTANCE_MOHM = 2.5

# Smallest acceptable separation between the measured harness and any other
# harness routed over the same plane, millimetre.
DEFAULT_MIN_SEPARATION_MM = 100.0

# The plane must extend beyond the unit footprint on every side, millimetre.
DEFAULT_PLANE_MARGIN_MM = 100.0

# Fraction of a window half-width inside which a value is called marginal
# rather than conforming.
DEFAULT_MARGINAL_FRACTION = 0.2

RECOGNIZED_LEADS = (
    "primary-positive",
    "primary-return",
    "secondary-positive",
    "secondary-return",
)

STATUS_CONFORMING = "conforming"
STATUS_MARGINAL = "marginal"
STATUS_DEVIATION = "deviation"

VERDICT_CONFORMING = "setup-conforming"
VERDICT_DEVIATIONS = "setup-deviations"


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


def within(value, low, high, tol=MM_TOL):
    """True when value sits inside the window, absorbing float error only."""
    if low <= value <= high:
        return True
    if math.isclose(value, low, rel_tol=0.0, abs_tol=tol):
        return True
    return math.isclose(value, high, rel_tol=0.0, abs_tol=tol)


def normalize_lead(lead):
    """Return the recognized lead designation for a raw designation."""
    if not isinstance(lead, str):
        raise ValueError("lead designation must be a string, got %r" % (lead,))
    key = lead.strip().lower()
    if key not in RECOGNIZED_LEADS:
        raise ValueError(
            "unrecognized lead %r; recognized: %s" % (lead, ", ".join(RECOGNIZED_LEADS))
        )
    return key


def dimension_window(nominal_mm, tolerance_mm):
    """Return the acceptable window around a nominal arrangement dimension."""
    nominal = _number({"v": nominal_mm}, "v", "nominal_mm")
    tolerance = _number({"v": tolerance_mm}, "v", "tolerance_mm")
    if nominal <= 0.0:
        raise ValueError("nominal_mm must be > 0, got %g" % nominal)
    if tolerance <= 0.0:
        raise ValueError("tolerance_mm must be > 0, got %g" % tolerance)
    if tolerance >= nominal:
        raise ValueError(
            "tolerance_mm %g must stay below the nominal %g" % (tolerance, nominal)
        )
    return (nominal - tolerance, nominal + tolerance)


def grade_dimension(
    value_mm, nominal_mm, tolerance_mm, marginal_fraction=DEFAULT_MARGINAL_FRACTION
):
    """Grade one arrangement dimension against its window."""
    value = _number({"v": value_mm}, "v", "value_mm")
    fraction = _number({"v": marginal_fraction}, "v", "marginal_fraction")
    if not 0.0 <= fraction < 1.0:
        raise ValueError("marginal_fraction must lie in [0, 1), got %g" % fraction)
    low, high = dimension_window(nominal_mm, tolerance_mm)
    deviation = value - float(nominal_mm)
    if not within(value, low, high):
        status = STATUS_DEVIATION
    elif abs(deviation) >= float(tolerance_mm) * (1.0 - fraction):
        status = STATUS_MARGINAL
    else:
        status = STATUS_CONFORMING
    return {
        "value_mm": value,
        "window_mm": (low, high),
        "deviation_mm": deviation,
        "status": status,
    }


def plane_margins_mm(plane, unit):
    """Ground-plane overhang beyond the unit footprint, per axis."""
    if not isinstance(plane, dict):
        raise ValueError("plane: record must be a mapping")
    if not isinstance(unit, dict):
        raise ValueError("unit: record must be a mapping")
    plane_length = _number(plane, "length_mm", "plane")
    plane_width = _number(plane, "width_mm", "plane")
    unit_length = _number(unit, "length_mm", "unit")
    unit_width = _number(unit, "width_mm", "unit")
    for name, value in (
        ("plane.length_mm", plane_length),
        ("plane.width_mm", plane_width),
        ("unit.length_mm", unit_length),
        ("unit.width_mm", unit_width),
    ):
        if value <= 0.0:
            raise ValueError("%s must be > 0, got %g" % (name, value))
    if unit_length > plane_length or unit_width > plane_width:
        raise ValueError(
            "unit footprint %gx%g mm does not fit the plane %gx%g mm"
            % (unit_length, unit_width, plane_length, plane_width)
        )
    return (
        (plane_length - unit_length) / 2.0,
        (plane_width - unit_width) / 2.0,
    )


def validate_ground_plane(
    plane,
    unit,
    required_margin_mm=DEFAULT_PLANE_MARGIN_MM,
    max_bond_resistance_mohm=DEFAULT_MAX_BOND_RESISTANCE_MOHM,
):
    """Validate the plane and the unit bond, returning a normalized record."""
    margin_required = _number(
        {"v": required_margin_mm}, "v", "required_margin_mm"
    )
    if margin_required < 0.0:
        raise ValueError("required_margin_mm must be >= 0")
    bond_limit = _number(
        {"v": max_bond_resistance_mohm}, "v", "max_bond_resistance_mohm"
    )
    if bond_limit <= 0.0:
        raise ValueError("max_bond_resistance_mohm must be > 0")
    length_margin, width_margin = plane_margins_mm(plane, unit)
    bond = _number(plane, "bond_resistance_mohm", "plane")
    if bond < 0.0:
        raise ValueError("plane: bond_resistance_mohm must be >= 0, got %g" % bond)
    bonded = _flag(plane, "unit_bonded", "plane")
    return {
        "length_margin_mm": length_margin,
        "width_margin_mm": width_margin,
        "required_margin_mm": margin_required,
        "margin_met": (
            length_margin >= margin_required - MM_TOL
            and width_margin >= margin_required - MM_TOL
        ),
        "bond_resistance_mohm": bond,
        "bond_limit_mohm": bond_limit,
        "bond_headroom_mohm": bond_limit - bond,
        "bond_met": bond <= bond_limit + MOHM_TOL,
        "unit_bonded": bonded,
    }


def validate_lead_run(record):
    """Validate one measured lead run and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("lead_run: record must be a mapping")
    where = "lead_run"
    lead = normalize_lead(record.get("lead"))
    where = "lead_run[%s]" % lead
    offset = _number(record, "probe_offset_mm", where)
    if offset <= 0.0:
        raise ValueError("%s: probe_offset_mm must be > 0, got %g" % (where, offset))
    height = _number(record, "harness_height_mm", where)
    if height <= 0.0:
        raise ValueError("%s: harness_height_mm must be > 0, got %g" % (where, height))
    separation = _number(record, "separation_mm", where)
    if separation < 0.0:
        raise ValueError("%s: separation_mm must be >= 0, got %g" % (where, separation))
    return {
        "lead": lead,
        "probe_offset_mm": offset,
        "harness_height_mm": height,
        "separation_mm": separation,
        "stabilisation_network_present": _flag(
            record, "stabilisation_network_present", where
        ),
    }


def grade_lead_run(
    record,
    probe_offset_mm=DEFAULT_PROBE_OFFSET_MM,
    probe_offset_tol_mm=DEFAULT_PROBE_OFFSET_TOL_MM,
    harness_height_mm=DEFAULT_HARNESS_HEIGHT_MM,
    harness_height_tol_mm=DEFAULT_HARNESS_HEIGHT_TOL_MM,
    min_separation_mm=DEFAULT_MIN_SEPARATION_MM,
    marginal_fraction=DEFAULT_MARGINAL_FRACTION,
):
    """Grade one lead run against the arrangement the clause is built on."""
    run = validate_lead_run(record)
    minimum_separation = _number(
        {"v": min_separation_mm}, "v", "min_separation_mm"
    )
    if minimum_separation < 0.0:
        raise ValueError("min_separation_mm must be >= 0")
    offset = grade_dimension(
        run["probe_offset_mm"], probe_offset_mm, probe_offset_tol_mm, marginal_fraction
    )
    height = grade_dimension(
        run["harness_height_mm"],
        harness_height_mm,
        harness_height_tol_mm,
        marginal_fraction,
    )
    separation_met = (
        run["separation_mm"] >= minimum_separation
        or math.isclose(
            run["separation_mm"], minimum_separation, rel_tol=0.0, abs_tol=MM_TOL
        )
    )
    deviations = []
    if offset["status"] == STATUS_DEVIATION:
        deviations.append(
            "probe offset %g mm on %s is outside %g-%g mm"
            % (
                offset["value_mm"],
                run["lead"],
                offset["window_mm"][0],
                offset["window_mm"][1],
            )
        )
    if height["status"] == STATUS_DEVIATION:
        deviations.append(
            "harness height %g mm on %s is outside %g-%g mm"
            % (
                height["value_mm"],
                run["lead"],
                height["window_mm"][0],
                height["window_mm"][1],
            )
        )
    if not separation_met:
        deviations.append(
            "separation %g mm on %s is below the %g mm minimum"
            % (run["separation_mm"], run["lead"], minimum_separation)
        )
    if not run["stabilisation_network_present"]:
        deviations.append(
            "no stabilisation network in the %s lead" % run["lead"]
        )
    marginals = [
        "%s %s is at the edge of its window on %s"
        % (name, "%g mm" % graded["value_mm"], run["lead"])
        for name, graded in (("probe offset", offset), ("harness height", height))
        if graded["status"] == STATUS_MARGINAL
    ]
    return {
        "lead": run["lead"],
        "probe_offset": offset,
        "harness_height": height,
        "separation_mm": run["separation_mm"],
        "separation_met": separation_met,
        "stabilisation_network_present": run["stabilisation_network_present"],
        "deviations": deviations,
        "marginals": marginals,
        "conforming": len(deviations) == 0,
    }


def assess_setup(
    plane,
    unit,
    lead_runs,
    required_margin_mm=DEFAULT_PLANE_MARGIN_MM,
    max_bond_resistance_mohm=DEFAULT_MAX_BOND_RESISTANCE_MOHM,
    probe_offset_mm=DEFAULT_PROBE_OFFSET_MM,
    probe_offset_tol_mm=DEFAULT_PROBE_OFFSET_TOL_MM,
    harness_height_mm=DEFAULT_HARNESS_HEIGHT_MM,
    harness_height_tol_mm=DEFAULT_HARNESS_HEIGHT_TOL_MM,
    min_separation_mm=DEFAULT_MIN_SEPARATION_MM,
    marginal_fraction=DEFAULT_MARGINAL_FRACTION,
):
    """Full clause 5.4.2.3 conformance assessment of the bench arrangement."""
    plane_record = validate_ground_plane(
        plane, unit, required_margin_mm, max_bond_resistance_mohm
    )
    if not isinstance(lead_runs, (list, tuple)):
        raise ValueError("lead_runs: must be a list of lead-run records")
    if len(lead_runs) == 0:
        raise ValueError("lead_runs: at least one measured lead is required")

    findings = []
    limitations = []
    if not plane_record["unit_bonded"]:
        findings.append("the unit is not bonded to the ground plane")
    if not plane_record["margin_met"]:
        findings.append(
            "plane overhang %g x %g mm is short of the %g mm required on every side"
            % (
                plane_record["length_margin_mm"],
                plane_record["width_margin_mm"],
                plane_record["required_margin_mm"],
            )
        )
    if not plane_record["bond_met"]:
        findings.append(
            "bond resistance %g mohm exceeds the %g mohm limit"
            % (plane_record["bond_resistance_mohm"], plane_record["bond_limit_mohm"])
        )

    graded = []
    seen = set()
    for record in lead_runs:
        report = grade_lead_run(
            record,
            probe_offset_mm,
            probe_offset_tol_mm,
            harness_height_mm,
            harness_height_tol_mm,
            min_separation_mm,
            marginal_fraction,
        )
        if report["lead"] in seen:
            raise ValueError(
                "lead_runs: lead %r appears twice" % report["lead"]
            )
        seen.add(report["lead"])
        graded.append(report)
        findings.extend(report["deviations"])
        limitations.extend(report["marginals"])

    graded.sort(key=lambda r: r["lead"])
    return {
        "ground_plane": plane_record,
        "leads": graded,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_CONFORMING if not findings else VERDICT_DEVIATIONS,
    }
