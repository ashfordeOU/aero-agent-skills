#!/usr/bin/env python3
"""Visual examination of the cell bypass diodes on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause looks at each bypass diode fitted to the cells and asks one
narrow question: has the diode body cracked, or has any of its material
separated. Neither is permitted, because the diode is the part that
carries a shadowed or open string past the cells it protects, and a
body that has cracked or lifted no longer guarantees it.

Observation kinds

    body-crack                    a crack in the diode body material
    body-separation               body material lifted or parted
    terminal-interface-separation separation where the body meets a
                                  terminal
    unresolved-surface-mark       a mark the magnification used could
                                  not resolve into either of the above

Two facts about the examination itself are graded alongside the
observations. The magnification has to be high enough for an absence of
findings to mean anything -- seeing a crack at low magnification is
conclusive, seeing nothing is not -- and every declared diode has to
carry a record before the assembly can be closed.

Dispositions are accept, refer-for-review, examination-invalid and
reject. The criteria below are a declared assembly criteria set, not a
physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIODE_OBSERVATION_KINDS = (
    "body-crack",
    "body-separation",
    "terminal-interface-separation",
    "unresolved-surface-mark",
)

ACCEPT = "accept"
REFER = "refer-for-review"
EXAMINATION_INVALID = "examination-invalid"
REJECT = "reject"
DIODE_DISPOSITIONS = (ACCEPT, REFER, EXAMINATION_INVALID, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, EXAMINATION_INVALID: 2, REJECT: 3}

REQUIRED_OBSERVATION_FIELDS = {
    "body-crack": ("extent_mm", "through_body"),
    "body-separation": ("separated_length_mm", "bonded_length_mm"),
    "terminal-interface-separation": ("separated_length_mm", "bonded_length_mm"),
    "unresolved-surface-mark": ("length_mm",),
}

DEFAULT_DIODE_CRITERIA = {
    "min_inspection_magnification": 10.0,
    "crack_always_rejects": True,
    "separation_always_rejects": True,
    "max_unresolved_mark_length_mm": 0.10,
    "min_body_dimension_mm": 0.30,
    "max_unprotected_cells_per_string": 0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A magnification or a length is compared against a declared limit
    that may itself have been derived, so a measurement sitting exactly
    on the limit can evaluate a few units in the last place below it.
    The limit is never lowered; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_diode_criteria(criteria):
    """Check a bypass diode criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive(
        "criteria min_inspection_magnification",
        criteria.get("min_inspection_magnification"),
    )
    _require_positive(
        "criteria max_unresolved_mark_length_mm",
        criteria.get("max_unresolved_mark_length_mm"),
    )
    _require_positive(
        "criteria min_body_dimension_mm", criteria.get("min_body_dimension_mm")
    )
    _require_count(
        "criteria max_unprotected_cells_per_string",
        criteria.get("max_unprotected_cells_per_string"),
    )
    for key in ("crack_always_rejects", "separation_always_rejects"):
        _require_flag("criteria %s" % key, criteria.get(key))
    return criteria


def body_geometry(body_length_mm, body_width_mm, criteria=DEFAULT_DIODE_CRITERIA):
    """Working dimensions of one diode body.

    The smallest side is the distance a crack has to run to cross the
    body, and the diagonal is the longest a crack can physically be; a
    reported extent beyond it is a measurement error, not a worse
    defect.
    """
    validate_diode_criteria(criteria)
    length = _require_positive("body_length_mm", body_length_mm)
    width = _require_positive("body_width_mm", body_width_mm)
    smallest = min(length, width)
    if smallest < criteria["min_body_dimension_mm"]:
        raise ValueError(
            "a body side of %.3f mm is below the %.3f mm smallest credible "
            "dimension; check the record before grading it"
            % (smallest, criteria["min_body_dimension_mm"])
        )
    return {
        "length_mm": length,
        "width_mm": width,
        "smallest_side_mm": smallest,
        "diagonal_mm": math.hypot(length, width),
        "footprint_mm2": length * width,
    }


def assess_observation(observation, body, criteria=DEFAULT_DIODE_CRITERIA):
    """Disposition one diode observation against the criteria set."""
    validate_diode_criteria(criteria)
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping, got %r" % (observation,))
    if not isinstance(body, dict) or "smallest_side_mm" not in body:
        raise ValueError("body must be the mapping returned by body_geometry")
    kind = _require_choice("kind", observation.get("kind"), DIODE_OBSERVATION_KINDS)
    for field in REQUIRED_OBSERVATION_FIELDS[kind]:
        if observation.get(field) is None:
            raise ValueError("a %s observation needs %s" % (kind, field))

    reasons = []
    severity = 0.0
    re_examine = False

    if kind == "body-crack":
        extent = _require_positive("extent_mm", observation.get("extent_mm"))
        through = _require_flag("through_body", observation.get("through_body"))
        if not _at_most(extent, body["diagonal_mm"]):
            raise ValueError(
                "a crack of %.3f mm cannot fit on a body whose diagonal is "
                "%.3f mm" % (extent, body["diagonal_mm"])
            )
        severity = extent / body["smallest_side_mm"]
        if criteria["crack_always_rejects"]:
            disposition = REJECT
        else:
            disposition = REFER
        if through:
            reasons.append(
                "crack runs through the body over %.3f mm; the diode can no "
                "longer be relied on to carry the string" % extent
            )
        else:
            reasons.append(
                "crack in the body material over %.3f mm, %.2f of the smallest "
                "body side" % (extent, severity)
            )
    elif kind in ("body-separation", "terminal-interface-separation"):
        separated = _require_positive(
            "separated_length_mm", observation.get("separated_length_mm")
        )
        bonded = _require_positive(
            "bonded_length_mm", observation.get("bonded_length_mm")
        )
        if not _at_most(separated, bonded):
            raise ValueError(
                "a separated length of %.3f mm exceeds the %.3f mm that was "
                "bonded" % (separated, bonded)
            )
        severity = separated / bonded
        disposition = REJECT if criteria["separation_always_rejects"] else REFER
        where = "body material" if kind == "body-separation" else "terminal interface"
        reasons.append(
            "%.2f of the %s has separated over %.3f mm" % (severity, where, separated)
        )
    else:  # unresolved-surface-mark
        length = _require_positive("length_mm", observation.get("length_mm"))
        severity = length / body["smallest_side_mm"]
        disposition = REFER
        re_examine = True
        if _at_most(length, criteria["max_unresolved_mark_length_mm"]):
            reasons.append(
                "mark of %.3f mm was not resolved into a crack or a separation; "
                "re-examine it at higher magnification before accepting the "
                "diode" % length
            )
        else:
            reasons.append(
                "mark of %.3f mm is longer than the %.3f mm a surface artefact "
                "is expected to reach and stays unresolved; re-examine it at "
                "higher magnification"
                % (length, criteria["max_unresolved_mark_length_mm"])
            )

    return {
        "id": observation.get("id"),
        "kind": kind,
        "disposition": disposition,
        "severity_fraction": severity,
        "needs_re_examination": re_examine,
        "reasons": reasons,
    }


def inspect_bypass_diode(record, criteria=DEFAULT_DIODE_CRITERIA):
    """Examine one bypass diode, magnification included."""
    validate_diode_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    diode_id = record.get("diode_id")
    if not isinstance(diode_id, str) or not diode_id.strip():
        raise ValueError("each diode record needs a non-empty diode_id")
    string_id = record.get("string_id")
    if not isinstance(string_id, str) or not string_id.strip():
        raise ValueError("diode %s needs a non-empty string_id" % diode_id)
    protected = _require_count(
        "protected_cell_count on %s" % diode_id, record.get("protected_cell_count")
    )
    if protected == 0:
        raise ValueError(
            "diode %s protects no cells; a bypass diode that protects nothing "
            "is a record error" % diode_id
        )
    magnification = _require_positive(
        "magnification on %s" % diode_id, record.get("magnification")
    )
    body = body_geometry(
        record.get("body_length_mm"), record.get("body_width_mm"), criteria
    )
    observations = record.get("observations", [])
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a list on diode %s" % diode_id)

    seen = set()
    assessed = []
    for observation in observations:
        result = assess_observation(observation, body, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate observation id %r on diode %s" % (marker, diode_id)
                )
            seen.add(marker)
        assessed.append(result)

    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])
    magnification_adequate = _at_least(
        magnification, criteria["min_inspection_magnification"]
    )
    if not magnification_adequate:
        if verdict == REJECT:
            findings.append(
                "examined at x%.1f against a x%.1f minimum; the finding still "
                "stands because a defect seen at low magnification is there"
                % (magnification, criteria["min_inspection_magnification"])
            )
        else:
            verdict = _worst((verdict, EXAMINATION_INVALID))
            findings.append(
                "examined at x%.1f against a x%.1f minimum; an absence of "
                "findings at this magnification says nothing about the body"
                % (magnification, criteria["min_inspection_magnification"])
            )
    return {
        "diode_id": diode_id,
        "string_id": string_id,
        "protected_cell_count": protected,
        "verdict": verdict,
        "magnification_adequate": magnification_adequate,
        "body": body,
        "observations": assessed,
        "max_severity_fraction": max(
            [result["severity_fraction"] for result in assessed] or [0.0]
        ),
        "re_examination_required": any(
            result["needs_re_examination"] for result in assessed
        ),
        "findings": findings,
    }


def inspect_bypass_diode_set(assembly, criteria=DEFAULT_DIODE_CRITERIA):
    """Clause 5.5.3.2.9 examination over every bypass diode on the assembly."""
    validate_diode_criteria(criteria)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = assembly.get("assembly_id")
    if not isinstance(assembly_id, str) or not assembly_id.strip():
        raise ValueError("assembly needs a non-empty assembly_id")
    declared = assembly.get("declared_diode_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_diode_count must be a positive integer, got %r" % (declared,)
        )
    records = assembly.get("diodes")
    if not isinstance(records, (list, tuple)):
        raise ValueError("diodes must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d diode records against a declared count of %d on %s"
            % (len(records), declared, assembly_id)
        )

    seen = set()
    examined = []
    for record in records:
        result = inspect_bypass_diode(record, criteria)
        if result["diode_id"] in seen:
            raise ValueError(
                "duplicate diode id %r on assembly %s"
                % (result["diode_id"], assembly_id)
            )
        seen.add(result["diode_id"])
        examined.append(result)

    findings = []
    counts = dict((state, 0) for state in DIODE_DISPOSITIONS)
    unprotected = {}
    for result in examined:
        counts[result["verdict"]] += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["diode_id"], finding))
        if result["verdict"] != ACCEPT:
            unprotected[result["string_id"]] = (
                unprotected.get(result["string_id"], 0)
                + result["protected_cell_count"]
            )

    verdict = _worst([result["verdict"] for result in examined] or [ACCEPT])
    allowance = criteria["max_unprotected_cells_per_string"]
    strings_over_allowance = sorted(
        string_id for string_id, cells in unprotected.items() if cells > allowance
    )
    for string_id in strings_over_allowance:
        findings.append(
            "string %s has %d cells whose bypass protection is not established "
            "against an allowance of %d"
            % (string_id, unprotected[string_id], allowance)
        )

    missing = declared - len(examined)
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d bypass diodes carry no examination record; the clause "
            "asks for each one" % (missing, declared)
        )
    return {
        "assembly_id": assembly_id,
        "verdict": verdict,
        "inspection_complete": complete,
        "missing_record_count": missing,
        "examined_count": len(examined),
        "disposition_counts": counts,
        "unprotected_cells_by_string": unprotected,
        "strings_over_allowance": strings_over_allowance,
        "re_examination_ids": [
            result["diode_id"] for result in examined if result["re_examination_required"]
        ],
        "not_accepted_ids": [
            result["diode_id"] for result in examined if result["verdict"] != ACCEPT
        ],
        "diodes": examined,
        "findings": findings,
    }
