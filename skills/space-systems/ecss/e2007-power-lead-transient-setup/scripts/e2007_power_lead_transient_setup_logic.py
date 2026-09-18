#!/usr/bin/env python3
"""Power-lead transient setup, ECSS-E-ST-20-07C clause 5.4.9.3.

Paraphrased arrangement, no verbatim standard text. The clause adds a
differential-mode injection arrangement on top of the standard test bench:
the pulse is driven between a supply lead and its own return, the injection
point sits in a window down the harness from the unit connector, a separate
monitoring probe watches the lead without sitting on top of the injector,
and a series isolation keeps the facility bus supply from swallowing the
pulse before the unit sees it.

This module turns that into a deterministic conformance decision:

  bench      -> valid transient bench or rejection
  lead paths -> windowed dimensions -> category per dimension
  generator  -> amplitude actually delivered into the loaded lead
  paths      -> governing path -> bench verdict

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. A dimension written to the exact edge of its window
# is a difference of two floats and can land a few units in the last place
# short. The tolerance absorbs that representation error only; it never
# widens a window.
TOL = 1e-9

MODE_DIFFERENTIAL = "differential-mode"

# Clause 5.4.9.3 describes the differential arrangement. A common-mode
# arrangement is a different setup and must not be graded against this one.
RECOGNIZED_MODES = (MODE_DIFFERENTIAL,)

RECOGNIZED_LEADS = (
    "primary-positive",
    "primary-return",
    "secondary-positive",
    "secondary-return",
)

# The return that closes the differential loop for each supply lead.
RETURN_FOR_SUPPLY = {
    "primary-positive": "primary-return",
    "secondary-positive": "secondary-return",
}

RECOGNIZED_INJECTION_DEVICES = (
    "series-injection-transformer",
    "series-coupling-capacitor",
    "clamp-injection-probe",
)

# Offset of the injection point from the unit connector, millimetre.
DEFAULT_INJECTION_OFFSET_WINDOW_MM = (40.0, 60.0)

# Height of the injected harness above the ground plane, millimetre.
DEFAULT_HARNESS_HEIGHT_WINDOW_MM = (40.0, 60.0)

# Minimum separation between the injection device and the monitoring probe.
DEFAULT_PROBE_SEPARATION_MIN_MM = 50.0

# Unit-to-plane bond resistance ceiling, milliohm.
DEFAULT_BOND_RESISTANCE_LIMIT_MOHM = 2.5

# Series inductance isolating the bus supply from the injected pulse.
DEFAULT_SOURCE_ISOLATION_MIN_UH = 5.0

# Share of a window's width, measured in from either edge, inside which a
# dimension is carried as a limitation rather than raised as a deviation.
DEFAULT_MARGINAL_FRACTION = 0.10

CATEGORY_CONFORMING = "conforming"
CATEGORY_MARGINAL = "marginal"
CATEGORY_DEVIATION = "deviation"
CATEGORIES = (CATEGORY_CONFORMING, CATEGORY_MARGINAL, CATEGORY_DEVIATION)

VERDICT_CONFORMING = "bench-conforming"
VERDICT_REJECTED = "bench-rejected"


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


def at_least(value, requirement, tol=TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def at_most(value, limit, tol=TOL):
    """True when value stays under the limit, absorbing float error only."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def normalize_injection_mode(mode):
    """Return the recognized injection mode for a raw designation."""
    if not isinstance(mode, str):
        raise ValueError("injection mode must be a string, got %r" % (mode,))
    key = mode.strip().lower()
    if key not in RECOGNIZED_MODES:
        raise ValueError(
            "clause 5.4.9.3 arranges a %s injection; got %r"
            % (MODE_DIFFERENTIAL, mode)
        )
    return key


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


def normalize_injection_device(device):
    """Return the recognized injection device for a raw designation."""
    if not isinstance(device, str):
        raise ValueError("injection device must be a string, got %r" % (device,))
    key = device.strip().lower()
    if key not in RECOGNIZED_INJECTION_DEVICES:
        raise ValueError(
            "unrecognized injection device %r; recognized: %s"
            % (device, ", ".join(RECOGNIZED_INJECTION_DEVICES))
        )
    return key


def paired_return(supply_lead):
    """Return the lead that closes the differential loop for a supply lead."""
    lead = normalize_lead(supply_lead)
    if lead not in RETURN_FOR_SUPPLY:
        raise ValueError(
            "%r is a return lead; the differential pulse is injected on a "
            "supply lead against its own return" % supply_lead
        )
    return RETURN_FOR_SUPPLY[lead]


def bond_headroom_mohm(measured_mohm, limit_mohm=DEFAULT_BOND_RESISTANCE_LIMIT_MOHM):
    """Headroom left by the unit-to-plane bond: limit minus measured."""
    measured = _number({"v": measured_mohm}, "v", "bond_resistance_mohm")
    limit = _number({"v": limit_mohm}, "v", "bond_limit_mohm")
    if measured < 0.0:
        raise ValueError("bond_resistance_mohm must be >= 0, got %g" % measured)
    if limit <= 0.0:
        raise ValueError("bond_limit_mohm must be > 0, got %g" % limit)
    return limit - measured


def categorize_window(value, window, marginal_fraction=DEFAULT_MARGINAL_FRACTION):
    """Categorize a dimension against a two-sided window.

    Inside the window and clear of both edges: conforming. Inside but within
    the marginal band of an edge: marginal, carried as a limitation. Outside:
    deviation.
    """
    reading = _number({"v": value}, "v", "windowed_dimension")
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("window must be a (low, high) pair, got %r" % (window,))
    low = _number({"v": window[0]}, "v", "window.low")
    high = _number({"v": window[1]}, "v", "window.high")
    if high <= low:
        raise ValueError("window high %g must exceed low %g" % (high, low))
    fraction = _number({"v": marginal_fraction}, "v", "marginal_fraction")
    if not 0.0 <= fraction < 0.5:
        raise ValueError(
            "marginal_fraction must lie in [0, 0.5), got %g" % fraction
        )
    if not (at_least(reading, low) and at_most(reading, high)):
        return CATEGORY_DEVIATION
    band = (high - low) * fraction
    if at_most(reading - low, band) or at_most(high - reading, band):
        return CATEGORY_MARGINAL
    return CATEGORY_CONFORMING


def categorize_minimum(value, minimum, marginal_fraction=DEFAULT_MARGINAL_FRACTION):
    """Categorize a dimension against a one-sided floor."""
    reading = _number({"v": value}, "v", "floored_dimension")
    floor = _number({"v": minimum}, "v", "minimum")
    if floor <= 0.0:
        raise ValueError("minimum must be > 0, got %g" % floor)
    fraction = _number({"v": marginal_fraction}, "v", "marginal_fraction")
    if not 0.0 <= fraction < 0.5:
        raise ValueError(
            "marginal_fraction must lie in [0, 0.5), got %g" % fraction
        )
    if not at_least(reading, floor):
        return CATEGORY_DEVIATION
    if at_most(reading - floor, floor * fraction):
        return CATEGORY_MARGINAL
    return CATEGORY_CONFORMING


def delivered_pulse_amplitude_v(open_circuit_v, source_impedance_ohm, load_impedance_ohm):
    """Pulse amplitude the generator actually drives into the loaded lead.

    The generator is a source behind its own impedance, so the amplitude the
    unit sees is the open-circuit amplitude divided down by the series pair.
    A bench graded on the generator dial rather than this value overstates
    every applied level.
    """
    open_circuit = _number({"v": open_circuit_v}, "v", "open_circuit_v")
    source = _number({"v": source_impedance_ohm}, "v", "source_impedance_ohm")
    load = _number({"v": load_impedance_ohm}, "v", "load_impedance_ohm")
    if open_circuit <= 0.0:
        raise ValueError("open_circuit_v must be > 0, got %g" % open_circuit)
    if source <= 0.0:
        raise ValueError("source_impedance_ohm must be > 0, got %g" % source)
    if load <= 0.0:
        raise ValueError("load_impedance_ohm must be > 0, got %g" % load)
    return open_circuit * load / (source + load)


def validate_transient_bench(bench, bond_limit_mohm=DEFAULT_BOND_RESISTANCE_LIMIT_MOHM):
    """Validate the bench the injection arrangement is built on."""
    where = "bench"
    if not isinstance(bench, dict):
        raise ValueError("%s: record must be a mapping" % where)
    mode = normalize_injection_mode(bench.get("injection_mode", ""))
    if not _flag(bench, "ground_plane_bonded", where):
        raise ValueError(
            "%s: the unit must stay bonded to the ground plane; an unbonded "
            "unit returns the pulse through whatever path it finds" % where
        )
    if not _flag(bench, "support_equipment_powered", where):
        raise ValueError(
            "%s: the support-equipment must operate as it does in the graded "
            "configuration" % where
        )
    bond = _number(bench, "bond_resistance_mohm", where)
    headroom = bond_headroom_mohm(bond, bond_limit_mohm)
    if not at_least(headroom, 0.0):
        raise ValueError(
            "%s: bond resistance %g mOhm exceeds the %g mOhm ceiling"
            % (where, bond, bond_limit_mohm)
        )
    isolation = _number(bench, "source_isolation_uh", where)
    if isolation <= 0.0:
        raise ValueError(
            "%s: source_isolation_uh must be > 0, got %g" % (where, isolation)
        )
    return {
        "injection_mode": mode,
        "bond_resistance_mohm": bond,
        "bond_headroom_mohm": headroom,
        "source_isolation_uh": isolation,
        "ground_plane_bonded": True,
        "support_equipment_powered": True,
    }


def grade_injection_path(
    path,
    offset_window_mm=DEFAULT_INJECTION_OFFSET_WINDOW_MM,
    height_window_mm=DEFAULT_HARNESS_HEIGHT_WINDOW_MM,
    probe_separation_min_mm=DEFAULT_PROBE_SEPARATION_MIN_MM,
    source_isolation_min_uh=DEFAULT_SOURCE_ISOLATION_MIN_UH,
    marginal_fraction=DEFAULT_MARGINAL_FRACTION,
):
    """Grade one differential injection path down to its dimension categories."""
    where = "injection_path"
    if not isinstance(path, dict):
        raise ValueError("%s: record must be a mapping" % where)
    supply = normalize_lead(path.get("supply_lead", ""))
    expected_return = paired_return(supply)
    declared_return = normalize_lead(path.get("return_lead", ""))
    if declared_return != expected_return:
        raise ValueError(
            "%s: differential injection on %s must close through %s, not %s"
            % (where, supply, expected_return, declared_return)
        )
    device = normalize_injection_device(path.get("injection_device", ""))
    if not _flag(path, "monitor_probe_fitted", where):
        raise ValueError(
            "%s: a monitoring probe must watch the injected lead; without it "
            "the applied pulse is a generator setting rather than a reading"
            % where
        )

    offset = _number(path, "injection_offset_mm", where)
    if offset <= 0.0:
        raise ValueError(
            "%s: injection_offset_mm must be > 0, got %g" % (where, offset)
        )
    height = _number(path, "harness_height_mm", where)
    if height <= 0.0:
        raise ValueError(
            "%s: harness_height_mm must be > 0, got %g" % (where, height)
        )
    separation = _number(path, "probe_separation_mm", where)
    if separation <= 0.0:
        raise ValueError(
            "%s: probe_separation_mm must be > 0, got %g" % (where, separation)
        )
    isolation = _number(path, "source_isolation_uh", where)
    if isolation <= 0.0:
        raise ValueError(
            "%s: source_isolation_uh must be > 0, got %g" % (where, isolation)
        )

    dimensions = {
        "injection_offset_mm": categorize_window(
            offset, offset_window_mm, marginal_fraction
        ),
        "harness_height_mm": categorize_window(
            height, height_window_mm, marginal_fraction
        ),
        "probe_separation_mm": categorize_minimum(
            separation, probe_separation_min_mm, marginal_fraction
        ),
        "source_isolation_uh": categorize_minimum(
            isolation, source_isolation_min_uh, marginal_fraction
        ),
    }
    counts = dict((category, 0) for category in CATEGORIES)
    for category in dimensions.values():
        counts[category] += 1
    return {
        "supply_lead": supply,
        "return_lead": declared_return,
        "injection_device": device,
        "injection_offset_mm": offset,
        "harness_height_mm": height,
        "probe_separation_mm": separation,
        "source_isolation_uh": isolation,
        "dimensions": dimensions,
        "counts": counts,
        "conforming": counts[CATEGORY_DEVIATION] == 0,
    }


def governing_path(path_reports):
    """Return the path holding the most deviations, ties broken by lead name."""
    if not isinstance(path_reports, (list, tuple)) or len(path_reports) == 0:
        raise ValueError("governing_path: at least one graded path is required")
    return min(
        path_reports,
        key=lambda r: (-r["counts"][CATEGORY_DEVIATION], r["supply_lead"]),
    )


def assess_transient_setup(
    bench,
    injection_paths,
    offset_window_mm=DEFAULT_INJECTION_OFFSET_WINDOW_MM,
    height_window_mm=DEFAULT_HARNESS_HEIGHT_WINDOW_MM,
    probe_separation_min_mm=DEFAULT_PROBE_SEPARATION_MIN_MM,
    source_isolation_min_uh=DEFAULT_SOURCE_ISOLATION_MIN_UH,
    bond_limit_mohm=DEFAULT_BOND_RESISTANCE_LIMIT_MOHM,
    marginal_fraction=DEFAULT_MARGINAL_FRACTION,
    generator=None,
):
    """Full clause 5.4.9.3 differential injection arrangement assessment."""
    configuration = validate_transient_bench(bench, bond_limit_mohm)
    if not isinstance(injection_paths, (list, tuple)):
        raise ValueError("injection_paths: must be a list of path records")
    if len(injection_paths) == 0:
        raise ValueError("injection_paths: at least one injected lead is required")

    reports = []
    seen = set()
    for path in injection_paths:
        report = grade_injection_path(
            path,
            offset_window_mm,
            height_window_mm,
            probe_separation_min_mm,
            source_isolation_min_uh,
            marginal_fraction,
        )
        if report["supply_lead"] in seen:
            raise ValueError(
                "injection_paths: supply lead %s appears twice; two runs have "
                "been merged into one arrangement" % report["supply_lead"]
            )
        seen.add(report["supply_lead"])
        reports.append(report)

    findings = []
    limitations = []
    for report in reports:
        for name in sorted(report["dimensions"]):
            category = report["dimensions"][name]
            if category == CATEGORY_DEVIATION:
                findings.append(
                    "%s on %s is outside its window at %g"
                    % (name, report["supply_lead"], report[name])
                )
            elif category == CATEGORY_MARGINAL:
                limitations.append(
                    "%s on %s sits at the edge of its window at %g"
                    % (name, report["supply_lead"], report[name])
                )

    delivered = None
    if generator is not None:
        if not isinstance(generator, dict):
            raise ValueError("generator: record must be a mapping")
        delivered = delivered_pulse_amplitude_v(
            _number(generator, "open_circuit_v", "generator"),
            _number(generator, "source_impedance_ohm", "generator"),
            _number(generator, "load_impedance_ohm", "generator"),
        )

    return {
        "configuration": configuration,
        "paths": reports,
        "governing_path": governing_path(reports)["supply_lead"],
        "delivered_amplitude_v": delivered,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_CONFORMING if not findings else VERDICT_REJECTED,
    }
