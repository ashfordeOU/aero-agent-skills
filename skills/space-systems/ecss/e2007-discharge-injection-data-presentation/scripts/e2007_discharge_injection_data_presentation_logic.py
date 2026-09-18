#!/usr/bin/env python3
"""Discharge-injection data package, ECSS-E-ST-20-07C clause 5.4.13.5.

Paraphrased procedure, no verbatim standard text. The clause asks the
discharge-injection test to hand over the generator settings it was run at,
a compliance table covering what was applied, and the oscilloscope records
taken at calibration and during the test. This module turns that package
into a deterministic completeness and consistency audit:

  generator settings  -> is every setting that defines the applied pulse there
  planned matrix      -> which point, level and polarity cells were to be run
  test captures       -> does every planned cell carry an oscilloscope record
  compliance table    -> does every planned cell carry an observed unit status
  calibration records -> does a calibration bracket the run, and did the
                         generator hold its amplitude from one end to the other

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "DEFAULT_ALLOWED_STATUSES",
    "DEFAULT_CALIBRATION_VALIDITY_H",
    "DEFAULT_DRIFT_ALLOWANCE",
    "EUT_STATUSES",
    "MANDATORY_GENERATOR_FIELDS",
    "POLARITIES",
    "STATUS_SEVERITY",
    "amplitude_reversals",
    "assess_discharge_injection_data",
    "audit_calibration",
    "audit_compliance_table",
    "audit_test_captures",
    "build_required_matrix",
    "cell_key",
    "coverage",
    "level_key",
    "status_counts",
    "validate_calibration_record",
    "validate_compliance_row",
    "validate_generator_settings",
    "validate_test_capture",
    "worst_status",
]

REL_TOL = 1e-12
ABS_TOL_H = 1e-9
ABS_TOL_A = 1e-12

# A level in kV is quantized to microvolts before it is used as a matrix key,
# so a cell written 4.0 in one file and 4.000000 in another is one cell and no
# float equality is ever relied on.
LEVEL_QUANTUM_PER_KV = 1.0e6

POLARITIES = ("positive", "negative")

# Settings without which the applied pulse cannot be reconstructed from the
# package, so the record does not say what the unit was subjected to.
MANDATORY_GENERATOR_FIELDS = (
    "charge_voltage_kv",
    "storage_capacitance_pf",
    "discharge_resistance_ohm",
    "pulses_per_polarity",
    "repetition_interval_s",
)

EUT_STATUSES = (
    "no-effect",
    "self-recovering",
    "operator-recoverable",
    "degraded",
    "damage",
)

STATUS_SEVERITY = {name: rank for rank, name in enumerate(EUT_STATUSES)}

DEFAULT_ALLOWED_STATUSES = ("no-effect", "self-recovering")

# Hours either side of the run within which a calibration still speaks for it.
DEFAULT_CALIBRATION_VALIDITY_H = 24.0

# Fraction by which the closing calibration amplitude may differ from the
# opening one before the run is no longer traceable to a known pulse.
DEFAULT_DRIFT_ALLOWANCE = 0.10

# Only a genuine reversal counts; an equal reading is not a reversal.
MONOTONIC_REL_TOL = 1e-9


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


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be positive, got %r" % (where, key, value))
    return value


def _text(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty string" % (where, key))
    return value.strip()


def _token(record, key, where, recognized):
    value = _text(record, key, where)
    token = value.lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def _positive_scalar(value, name):
    return _positive({name: value}, name, "argument")


def _finite_scalar(value, name):
    return _number({name: value}, name, "argument")


def level_key(level_kv):
    """Return the quantized integer key for an injection level in kV."""
    level = _positive_scalar(level_kv, "level_kv")
    return int(round(level * LEVEL_QUANTUM_PER_KV))


def cell_key(point, level_kv, polarity):
    """Return the (point, level, polarity) key that identifies a matrix cell."""
    if not isinstance(point, str) or not point.strip():
        raise ValueError("cell key: point must be a non-empty string")
    if not isinstance(polarity, str):
        raise ValueError("cell key: polarity must be a string")
    token = polarity.strip().lower()
    if token not in POLARITIES:
        raise ValueError("cell key: unrecognized polarity %r" % (polarity,))
    return (point.strip().lower(), level_key(level_kv), token)


def build_required_matrix(points, levels_kv, polarities):
    """Return the sorted list of cells the package has to account for."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("matrix: points must be a non-empty sequence")
    if not isinstance(levels_kv, (list, tuple)) or not levels_kv:
        raise ValueError("matrix: levels_kv must be a non-empty sequence")
    if not isinstance(polarities, (list, tuple)) or not polarities:
        raise ValueError("matrix: polarities must be a non-empty sequence")
    seen_points = []
    for point in points:
        if not isinstance(point, str) or not point.strip():
            raise ValueError("matrix: every point must be a non-empty string")
        token = point.strip().lower()
        if token in seen_points:
            raise ValueError("matrix: point %r declared twice" % point)
        seen_points.append(token)
    seen_levels = []
    for level in levels_kv:
        key = level_key(level)
        if key in seen_levels:
            raise ValueError("matrix: level %r declared twice" % (level,))
        seen_levels.append(key)
    seen_polarities = []
    for polarity in polarities:
        if not isinstance(polarity, str) or polarity.strip().lower() not in POLARITIES:
            raise ValueError("matrix: unrecognized polarity %r" % (polarity,))
        token = polarity.strip().lower()
        if token in seen_polarities:
            raise ValueError("matrix: polarity %r declared twice" % (polarity,))
        seen_polarities.append(token)
    cells = []
    for point in seen_points:
        for level in seen_levels:
            for polarity in seen_polarities:
                cells.append((point, level, polarity))
    return sorted(cells)


def validate_generator_settings(settings):
    """Audit the generator settings that define the applied pulse.

    A field that is absent, or present but empty, is reported as missing; a
    field that is present with a value of the wrong kind is an input error.
    """
    where = "generator settings"
    if not isinstance(settings, dict):
        raise ValueError("%s: record must be a mapping" % where)
    present = {}
    missing = []
    for field in MANDATORY_GENERATOR_FIELDS:
        if field not in settings or settings[field] is None or settings[field] == "":
            missing.append(field)
            continue
        if field == "pulses_per_polarity":
            value = settings[field]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("%s: %r must be an integer" % (where, field))
            if value < 1:
                raise ValueError("%s: %r must be at least 1" % (where, field))
            present[field] = value
        else:
            present[field] = _positive(settings, field, where)
    polarity_field = settings.get("polarities")
    if polarity_field is None:
        missing.append("polarities")
        polarities = []
    else:
        if not isinstance(polarity_field, (list, tuple)) or not polarity_field:
            raise ValueError("%s: 'polarities' must be a non-empty sequence" % where)
        polarities = []
        for value in polarity_field:
            if not isinstance(value, str) or value.strip().lower() not in POLARITIES:
                raise ValueError("%s: unrecognized polarity %r" % (where, value))
            polarities.append(value.strip().lower())
        present["polarities"] = polarities
    return {
        "present": present,
        "missing": sorted(missing),
        "complete": not missing,
        "polarities": polarities,
    }


def validate_test_capture(record, index=0):
    """Validate one oscilloscope record taken during the injection run."""
    where = "test capture %d" % index
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    point = _text(record, "point", where)
    polarity = _token(record, "polarity", where, POLARITIES)
    level = _positive(record, "level_kv", where)
    peak = _positive(record, "peak_current_a", where)
    capture_id = _text(record, "capture_id", where)
    return {
        "key": cell_key(point, level, polarity),
        "point": point.lower(),
        "level_kv": level,
        "polarity": polarity,
        "peak_current_a": peak,
        "capture_id": capture_id,
    }


def validate_compliance_row(row, index=0, allowed_statuses=None):
    """Validate one compliance-table row and return it normalized."""
    where = "compliance row %d" % index
    if not isinstance(row, dict):
        raise ValueError("%s: row must be a mapping" % where)
    point = _text(row, "point", where)
    polarity = _token(row, "polarity", where, POLARITIES)
    level = _positive(row, "level_kv", where)
    status = _token(row, "eut_status", where, EUT_STATUSES)
    allowed = tuple(allowed_statuses or DEFAULT_ALLOWED_STATUSES)
    for name in allowed:
        if name not in EUT_STATUSES:
            raise ValueError("%s: unrecognized allowed status %r" % (where, name))
    return {
        "key": cell_key(point, level, polarity),
        "point": point.lower(),
        "level_kv": level,
        "polarity": polarity,
        "eut_status": status,
        "within_allowed": status in allowed,
    }


def validate_calibration_record(record, index=0):
    """Validate one oscilloscope record taken while calibrating the generator."""
    where = "calibration record %d" % index
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    timestamp = _finite_scalar(record.get("timestamp_h"), "timestamp_h") \
        if "timestamp_h" in record else None
    if timestamp is None:
        raise ValueError("%s: missing required field 'timestamp_h'" % where)
    level = _positive(record, "level_kv", where)
    peak = _positive(record, "peak_current_a", where)
    rise = _positive(record, "rise_time_ns", where)
    duration = _positive(record, "duration_ns", where)
    if duration < rise:
        raise ValueError(
            "%s: duration %g ns is shorter than the rise time %g ns" % (where, duration, rise)
        )
    capture_id = _text(record, "capture_id", where)
    return {
        "timestamp_h": timestamp,
        "level_kv": level,
        "peak_current_a": peak,
        "rise_time_ns": rise,
        "duration_ns": duration,
        "capture_id": capture_id,
    }


def coverage(required, supplied):
    """Compare a supplied cell list with the required matrix."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("coverage: required matrix must be a non-empty sequence")
    if not isinstance(supplied, (list, tuple)):
        raise ValueError("coverage: supplied must be a sequence")
    required_set = set(required)
    if len(required_set) != len(required):
        raise ValueError("coverage: required matrix contains a repeated cell")
    seen = []
    duplicates = []
    for key in supplied:
        if key in seen:
            if key not in duplicates:
                duplicates.append(key)
        else:
            seen.append(key)
    covered = sorted(k for k in seen if k in required_set)
    missing = sorted(k for k in required_set if k not in seen)
    extra = sorted(k for k in seen if k not in required_set)
    return {
        "required": len(required_set),
        "covered": covered,
        "missing": missing,
        "extra": extra,
        "duplicates": sorted(duplicates),
        "ratio": len(covered) / float(len(required_set)),
    }


def amplitude_reversals(captures):
    """Return the level pairs where a higher level recorded a lower peak.

    Grouped per point and polarity; only a genuine reversal is reported, an
    equal reading at two levels is not.
    """
    if not isinstance(captures, (list, tuple)):
        raise ValueError("amplitude reversals: captures must be a sequence")
    grouped = {}
    for capture in captures:
        if not isinstance(capture, dict) or "key" not in capture:
            raise ValueError("amplitude reversals: expected normalized captures")
        point, level, polarity = capture["key"]
        grouped.setdefault((point, polarity), []).append((level, capture))
    reversals = []
    for (point, polarity), entries in sorted(grouped.items()):
        entries.sort(key=lambda item: item[0])
        for index in range(1, len(entries)):
            lower = entries[index - 1][1]
            upper = entries[index][1]
            low_peak = lower["peak_current_a"]
            high_peak = upper["peak_current_a"]
            if high_peak >= low_peak:
                continue
            if math.isclose(high_peak, low_peak, rel_tol=MONOTONIC_REL_TOL, abs_tol=ABS_TOL_A):
                continue
            reversals.append(
                {
                    "point": point,
                    "polarity": polarity,
                    "lower_level_kv": lower["level_kv"],
                    "upper_level_kv": upper["level_kv"],
                    "lower_peak_current_a": low_peak,
                    "upper_peak_current_a": high_peak,
                }
            )
    return reversals


def audit_test_captures(captures, required):
    """Normalize the run captures and compare them with the required matrix."""
    if not isinstance(captures, (list, tuple)):
        raise ValueError("test captures: expected a sequence of records")
    normalized = [validate_test_capture(record, index)
                  for index, record in enumerate(captures)]
    identifiers = []
    repeated_ids = []
    for capture in normalized:
        if capture["capture_id"] in identifiers:
            if capture["capture_id"] not in repeated_ids:
                repeated_ids.append(capture["capture_id"])
        else:
            identifiers.append(capture["capture_id"])
    report = coverage(required, [c["key"] for c in normalized])
    report["captures"] = normalized
    report["repeated_capture_ids"] = sorted(repeated_ids)
    report["amplitude_reversals"] = amplitude_reversals(normalized)
    return report


def status_counts(rows):
    """Return the count of compliance rows carrying each observed status."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("status counts: rows must be a sequence")
    counts = {name: 0 for name in EUT_STATUSES}
    for row in rows:
        if not isinstance(row, dict) or "eut_status" not in row:
            raise ValueError("status counts: expected normalized compliance rows")
        counts[row["eut_status"]] += 1
    return counts


def worst_status(rows):
    """Return the most severe status recorded in the table, or None."""
    worst = None
    for row in rows or []:
        if not isinstance(row, dict) or "eut_status" not in row:
            raise ValueError("worst status: expected normalized compliance rows")
        status = row["eut_status"]
        if worst is None or STATUS_SEVERITY[status] > STATUS_SEVERITY[worst]:
            worst = status
    return worst


def audit_compliance_table(rows, required, allowed_statuses=None):
    """Normalize the compliance table and compare it with the required matrix."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("compliance table: expected a sequence of rows")
    normalized = [validate_compliance_row(row, index, allowed_statuses)
                  for index, row in enumerate(rows)]
    report = coverage(required, [r["key"] for r in normalized])
    report["rows"] = normalized
    report["counts"] = status_counts(normalized)
    report["worst_status"] = worst_status(normalized)
    report["exceedances"] = [r for r in normalized if not r["within_allowed"]]
    return report


def audit_calibration(records, test_start_h, test_stop_h,
                      validity_h=DEFAULT_CALIBRATION_VALIDITY_H,
                      drift_allowance=DEFAULT_DRIFT_ALLOWANCE):
    """Check a calibration brackets the run and that the amplitude held.

    An opening record is the latest calibration at or before the run start and
    within the validity window; a closing record is the earliest at or after
    the run stop and within the same window.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("calibration: expected a non-empty sequence of records")
    normalized = [validate_calibration_record(record, index)
                  for index, record in enumerate(records)]
    start = _finite_scalar(test_start_h, "test_start_h")
    stop = _finite_scalar(test_stop_h, "test_stop_h")
    if stop < start:
        raise ValueError("calibration: run stop %g h precedes its start %g h" % (stop, start))
    validity = _positive_scalar(validity_h, "validity_h")
    allowance = _finite_scalar(drift_allowance, "drift_allowance")
    if allowance < 0.0:
        raise ValueError("drift_allowance must not be negative, got %r" % (drift_allowance,))

    opening = None
    closing = None
    for record in normalized:
        stamp = record["timestamp_h"]
        if stamp <= start or math.isclose(stamp, start, rel_tol=REL_TOL, abs_tol=ABS_TOL_H):
            if start - stamp <= validity or math.isclose(
                start - stamp, validity, rel_tol=REL_TOL, abs_tol=ABS_TOL_H
            ):
                if opening is None or stamp > opening["timestamp_h"]:
                    opening = record
        if stamp >= stop or math.isclose(stamp, stop, rel_tol=REL_TOL, abs_tol=ABS_TOL_H):
            if stamp - stop <= validity or math.isclose(
                stamp - stop, validity, rel_tol=REL_TOL, abs_tol=ABS_TOL_H
            ):
                if closing is None or stamp < closing["timestamp_h"]:
                    closing = record

    findings = []
    if opening is None:
        findings.append(
            "no calibration record within %g h before the run, so the applied "
            "pulse is not traceable to a measured waveform" % validity
        )
    if closing is None:
        findings.append(
            "no calibration record within %g h after the run, so nothing shows "
            "the generator still delivered the set pulse at the end" % validity
        )
    drift_ratio = None
    within_drift = None
    if opening is not None and closing is not None:
        low = min(opening["peak_current_a"], closing["peak_current_a"])
        high = max(opening["peak_current_a"], closing["peak_current_a"])
        drift_ratio = high / low
        bound = 1.0 + allowance
        within_drift = drift_ratio <= bound or math.isclose(
            drift_ratio, bound, rel_tol=REL_TOL, abs_tol=0.0
        )
        if not within_drift:
            findings.append(
                "calibration amplitude moved by %.1f%% across the run, beyond the "
                "%.1f%% allowance" % ((drift_ratio - 1.0) * 100.0, allowance * 100.0)
            )
    return {
        "records": normalized,
        "opening": opening,
        "closing": closing,
        "drift_ratio": drift_ratio,
        "within_drift": within_drift,
        "findings": findings,
    }


def assess_discharge_injection_data(package):
    """Audit a complete clause 5.4.13.5 discharge-injection data package.

    Required keys: injection_points, level_ladder_kv, polarities,
    generator_settings, calibration_records, test_captures, compliance_rows,
    test_start_h, test_stop_h. Optional: calibration_validity_h,
    drift_allowance, allowed_statuses.
    """
    where = "data package"
    if not isinstance(package, dict):
        raise ValueError("%s: package must be a mapping" % where)
    required_keys = (
        "injection_points",
        "level_ladder_kv",
        "polarities",
        "generator_settings",
        "calibration_records",
        "test_captures",
        "compliance_rows",
        "test_start_h",
        "test_stop_h",
    )
    for key in required_keys:
        if key not in package:
            raise ValueError("%s: missing required field %r" % (where, key))

    matrix = build_required_matrix(
        package["injection_points"], package["level_ladder_kv"], package["polarities"]
    )
    settings = validate_generator_settings(package["generator_settings"])
    captures = audit_test_captures(package["test_captures"], matrix)
    allowed = package.get("allowed_statuses")
    table = audit_compliance_table(package["compliance_rows"], matrix, allowed)
    calibration = audit_calibration(
        package["calibration_records"],
        package["test_start_h"],
        package["test_stop_h"],
        package.get("calibration_validity_h", DEFAULT_CALIBRATION_VALIDITY_H),
        package.get("drift_allowance", DEFAULT_DRIFT_ALLOWANCE),
    )

    findings = []
    limitations = []
    if settings["missing"]:
        findings.append(
            "generator settings incomplete: %s absent, so the applied pulse "
            "cannot be reconstructed" % ", ".join(settings["missing"])
        )
    if captures["missing"]:
        findings.append(
            "%d of %d planned cells carry no oscilloscope record"
            % (len(captures["missing"]), captures["required"])
        )
    if captures["duplicates"]:
        findings.append(
            "%d planned cells carry more than one oscilloscope record, so the "
            "record for the cell is ambiguous" % len(captures["duplicates"])
        )
    if captures["repeated_capture_ids"]:
        findings.append(
            "capture identifiers reused: %s" % ", ".join(captures["repeated_capture_ids"])
        )
    if table["missing"]:
        findings.append(
            "%d of %d planned cells carry no compliance-table row"
            % (len(table["missing"]), table["required"])
        )
    if table["duplicates"]:
        findings.append(
            "%d planned cells carry more than one compliance row, so the observed "
            "status for the cell is ambiguous" % len(table["duplicates"])
        )
    if table["exceedances"]:
        findings.append(
            "%d cells record a unit status outside the agreed set, worst is %s"
            % (len(table["exceedances"]), table["worst_status"])
        )
    findings.extend(calibration["findings"])

    if captures["extra"]:
        limitations.append(
            "%d oscilloscope records fall outside the planned matrix and are "
            "carried unreferenced" % len(captures["extra"])
        )
    if table["extra"]:
        limitations.append(
            "%d compliance rows fall outside the planned matrix" % len(table["extra"])
        )
    if captures["amplitude_reversals"]:
        limitations.append(
            "%d level pairs record a lower peak current at the higher level, "
            "which the package does not explain"
            % len(captures["amplitude_reversals"])
        )

    return {
        "matrix": matrix,
        "generator_settings": settings,
        "captures": captures,
        "compliance_table": table,
        "calibration": calibration,
        "capture_completeness": captures["ratio"],
        "table_completeness": table["ratio"],
        "findings": findings,
        "limitations": limitations,
        "package_acceptable": not findings,
    }
