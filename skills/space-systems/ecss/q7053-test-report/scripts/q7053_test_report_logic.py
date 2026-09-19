#!/usr/bin/env python3
"""Reporting for a sterilization-compatibility test.

Anchor: ECSS-Q-ST-70-53C, reporting clauses. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the identification block for every required field.
2. Validate each cycle record and check the logged cycles against the planned
   count, with no gap and no repeat in the indices.
3. Grade each achieved cycle parameter against its declared window and pair
   an out-of-window value with the cycle's deviation reference; flag a
   deviation reference recorded against a clean cycle.
4. Require a pre and a post value for every declared property and carry the
   property verdicts through.
5. Score the completeness of the record and test the stated conclusion
   against the property verdicts and the cycle findings.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "BOUND_TOLERANCE",
    "REQUIRED_IDENTIFICATION_FIELDS",
    "COMPATIBLE",
    "COMPATIBLE_WITH_LIMITATIONS",
    "NOT_COMPATIBLE",
    "CONCLUSIONS",
    "identification_findings",
    "validate_cycle_record",
    "cycle_sequence_findings",
    "grade_cycle_parameters",
    "degradation_findings",
    "completeness_score",
    "conclusion_conflicts",
    "compile_test_report",
]

# Window grading compares an achieved value with a specified bound: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the specified window.
BOUND_TOLERANCE = 1e-12

REQUIRED_IDENTIFICATION_FIELDS = (
    "material_designation",
    "batch_or_lot",
    "processing_state",
    "sterilization_process",
    "test_facility",
)

COMPATIBLE = "compatible"
COMPATIBLE_WITH_LIMITATIONS = "compatible-with-limitations"
NOT_COMPATIBLE = "not-compatible"
CONCLUSIONS = (COMPATIBLE, COMPATIBLE_WITH_LIMITATIONS, NOT_COMPATIBLE)


def _real(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _filled(value):
    """Return True when a field carries something a reviewer can use."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def identification_findings(identification):
    """Return the list of required identification fields that are missing."""
    if not isinstance(identification, dict):
        raise ValueError("identification must be a mapping")
    return [
        field
        for field in REQUIRED_IDENTIFICATION_FIELDS
        if not _filled(identification.get(field))
    ]


def validate_cycle_record(record):
    """Return a normalised cycle record, or raise on a malformed one."""
    if not isinstance(record, dict):
        raise ValueError("cycle record must be a mapping, got %r" % (record,))
    index = record.get("index")
    if not isinstance(index, int) or isinstance(index, bool):
        raise ValueError("cycle index must be an integer, got %r" % (index,))
    if index < 1:
        raise ValueError("cycle index must be at least 1, got %d" % index)
    achieved = record.get("achieved")
    if not isinstance(achieved, dict) or not achieved:
        raise ValueError("cycle %d needs a non-empty 'achieved' mapping" % index)
    normalised = {}
    for name, value in achieved.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("cycle %d has an unnamed achieved parameter" % index)
        normalised[name.strip()] = _real(value, "cycle %d parameter %r" % (index, name))
    reference = record.get("deviation_reference")
    if reference is not None and not (isinstance(reference, str) and reference.strip()):
        raise ValueError("cycle %d deviation_reference must be a non-empty string" % index)
    return {
        "index": index,
        "achieved": normalised,
        "deviation_reference": reference.strip() if isinstance(reference, str) else None,
    }


def cycle_sequence_findings(cycles, planned_cycles):
    """Return findings about the count and the numbering of the logged cycles."""
    if not isinstance(cycles, (list, tuple)) or not cycles:
        raise ValueError("cycles must be a non-empty sequence of cycle records")
    if not isinstance(planned_cycles, int) or isinstance(planned_cycles, bool):
        raise ValueError("planned_cycles must be an integer")
    if planned_cycles < 1:
        raise ValueError("planned_cycles must be at least 1, got %d" % planned_cycles)
    records = [validate_cycle_record(record) for record in cycles]
    indices = [record["index"] for record in records]
    findings = []
    if len(indices) != planned_cycles:
        findings.append(
            "cycle log holds %d cycles against a planned %d"
            % (len(indices), planned_cycles)
        )
    repeated = sorted({i for i in indices if indices.count(i) > 1})
    for index in repeated:
        findings.append("cycle index %d is logged more than once" % index)
    expected = set(range(1, len(indices) + 1))
    missing = sorted(expected - set(indices))
    for index in missing:
        findings.append("cycle index %d is missing from the log" % index)
    return findings


def grade_cycle_parameters(cycle, windows):
    """Grade one cycle's achieved parameters against the declared windows."""
    record = validate_cycle_record(cycle)
    if not isinstance(windows, dict) or not windows:
        raise ValueError("windows must be a non-empty mapping")
    graded = {}
    findings = []
    breaches = 0
    for name in sorted(windows):
        window = windows[name]
        if not isinstance(window, dict):
            raise ValueError("window %r must be a mapping" % name)
        lower = window.get("min")
        upper = window.get("max")
        if lower is None and upper is None:
            raise ValueError("window %r needs at least one of 'min' or 'max'" % name)
        if lower is not None:
            lower = _real(lower, "window %r min" % name)
        if upper is not None:
            upper = _real(upper, "window %r max" % name)
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("window %r has min above max" % name)
        if name not in record["achieved"]:
            findings.append(
                "cycle %d never recorded the achieved '%s'" % (record["index"], name)
            )
            graded[name] = {"recorded": False, "within_window": False, "value": None}
            continue
        value = record["achieved"][name]
        within = True
        if lower is not None and value < lower and not math.isclose(
            value, lower, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
        ):
            within = False
        if upper is not None and value > upper and not math.isclose(
            value, upper, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
        ):
            within = False
        graded[name] = {"recorded": True, "within_window": within, "value": value}
        if not within:
            breaches += 1
            if record["deviation_reference"] is None:
                findings.append(
                    "cycle %d achieved '%s' of %.6g outside its window with no deviation recorded"
                    % (record["index"], name, value)
                )
    for name in sorted(record["achieved"]):
        if name not in windows:
            findings.append(
                "cycle %d recorded '%s', which no window declares"
                % (record["index"], name)
            )
    if record["deviation_reference"] is not None and breaches == 0:
        findings.append(
            "cycle %d carries deviation '%s' but nothing in it left its window"
            % (record["index"], record["deviation_reference"])
        )
    return {
        "index": record["index"],
        "parameters": graded,
        "breaches": breaches,
        "deviation_reference": record["deviation_reference"],
        "findings": findings,
    }


def degradation_findings(properties):
    """Return findings about the pre and post values of the declared properties."""
    if not isinstance(properties, (list, tuple)) or not properties:
        raise ValueError("properties must be a non-empty sequence")
    findings = []
    evidenced = []
    failed = []
    seen = set()
    for index, item in enumerate(properties):
        if not isinstance(item, dict):
            raise ValueError("properties[%d] must be a mapping" % index)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("properties[%d] needs a non-empty name" % index)
        name = name.strip()
        if name in seen:
            raise ValueError("property %r is declared more than once" % name)
        seen.add(name)
        has_pre = _filled(item.get("pre"))
        has_post = _filled(item.get("post"))
        if has_pre and has_post:
            _real(item["pre"], "property %r pre" % name)
            _real(item["post"], "property %r post" % name)
            evidenced.append(name)
        else:
            missing = []
            if not has_pre:
                missing.append("pre")
            if not has_post:
                missing.append("post")
            findings.append(
                "property '%s' is unevidenced: no %s value" % (name, " and no ".join(missing))
            )
        if item.get("acceptable") is False:
            failed.append(name)
    return {"findings": findings, "evidenced": evidenced, "failed": failed}


def completeness_score(present, required):
    """Return the share of required record elements that are present."""
    if not isinstance(required, int) or isinstance(required, bool):
        raise ValueError("required must be an integer")
    if required < 1:
        raise ValueError("required must be at least 1, got %d" % required)
    if not isinstance(present, int) or isinstance(present, bool):
        raise ValueError("present must be an integer")
    if present < 0 or present > required:
        raise ValueError("present must lie in [0, %d], got %d" % (required, present))
    return present / required


def conclusion_conflicts(conclusion, failed_properties, record_findings):
    """Return the conflicts between a stated conclusion and the data behind it."""
    if conclusion not in CONCLUSIONS:
        raise ValueError(
            "conclusion must be one of %s, got %r" % (", ".join(CONCLUSIONS), conclusion)
        )
    if not isinstance(failed_properties, (list, tuple)):
        raise ValueError("failed_properties must be a sequence")
    if not isinstance(record_findings, (list, tuple)):
        raise ValueError("record_findings must be a sequence")
    conflicts = []
    if conclusion == COMPATIBLE and failed_properties:
        conflicts.append(
            "conclusion states compatibility while %d propert%s failed: %s"
            % (
                len(failed_properties),
                "y" if len(failed_properties) == 1 else "ies",
                ", ".join(sorted(failed_properties)),
            )
        )
    if conclusion == COMPATIBLE and record_findings:
        conflicts.append(
            "conclusion states compatibility over a record carrying %d finding%s"
            % (len(record_findings), "" if len(record_findings) == 1 else "s")
        )
    if conclusion == NOT_COMPATIBLE and not failed_properties:
        conflicts.append(
            "conclusion states incompatibility but no declared property failed"
        )
    return conflicts


def compile_test_report(spec):
    """Compile and grade an ECSS-Q-ST-70-53C compatibility test report.

    spec keys: identification, planned_cycles, parameter_windows, cycles,
    properties, conclusion. Optional: report_id.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("identification", "planned_cycles", "parameter_windows",
                "cycles", "properties", "conclusion"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    missing_fields = identification_findings(spec["identification"])
    findings = ["identification field '%s' is missing" % field for field in missing_fields]
    findings.extend(cycle_sequence_findings(spec["cycles"], spec["planned_cycles"]))
    graded_cycles = [
        grade_cycle_parameters(cycle, spec["parameter_windows"]) for cycle in spec["cycles"]
    ]
    for graded in graded_cycles:
        findings.extend(graded["findings"])
    degradation = degradation_findings(spec["properties"])
    findings.extend(degradation["findings"])

    required_elements = (
        len(REQUIRED_IDENTIFICATION_FIELDS)
        + spec["planned_cycles"]
        + len(spec["properties"])
    )
    present_elements = (
        len(REQUIRED_IDENTIFICATION_FIELDS)
        - len(missing_fields)
        + min(len(spec["cycles"]), spec["planned_cycles"])
        + len(degradation["evidenced"])
    )
    score = completeness_score(present_elements, required_elements)
    conflicts = conclusion_conflicts(
        spec["conclusion"], degradation["failed"], findings
    )
    findings.extend(conflicts)
    return {
        "report_id": spec.get("report_id"),
        "missing_identification_fields": missing_fields,
        "graded_cycles": graded_cycles,
        "evidenced_properties": degradation["evidenced"],
        "failed_properties": degradation["failed"],
        "completeness_score": score,
        "conclusion": spec["conclusion"],
        "conclusion_conflicts": conflicts,
        "report_complete": score >= 1.0 and not findings,
        "findings": findings,
    }
