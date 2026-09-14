#!/usr/bin/env python3
"""A process identification document has to describe processes, not list their names.

Anchor: ECSS-E-ST-20-08C Annex F. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

The process identification document is where an assembly's production
processes are written down in enough detail that somebody who did not run them
can tell what was run. A document that lists process names has identified
nothing: two suppliers can both write "interconnector welding" and build
different hardware. This module reads such a document and answers four
questions:

    sections    does the document carry the headings it is written to -- its
                own identity, the product it applies to, the process list, the
                flow the processes run in, change control and approval
    description does every process record carry the fields that make a process
                re-runnable: where it runs, on what equipment, with which
                materials, under which control parameters, with what in-process
                inspection
    parameters  does every control parameter carry a band that brackets its
                nominal, is not zero wide, and is not so wide it controls
                nothing
    sequence    do the stated sequence numbers form one run from first to last,
                with no number used twice and none skipped, and does every
                process in the list have a record and every record a list entry

The arms are ranked rather than merged. A field that is absent outranks a
control parameter written down wrong, and a process with no parameters at all
outranks one whose parameters are unusable, because a missing commitment and a
badly drafted commitment ask different people for different work.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_DOCUMENT_SECTIONS = (
    "document_identifier",
    "issue_and_date",
    "preparing_organisation",
    "product_applicability",
    "process_list",
    "process_flow_sequence",
    "change_control_statement",
    "approval_record",
)

REQUIRED_PROCESS_FIELDS = (
    "process_id",
    "description",
    "sequence",
    "facility_or_line",
    "equipment",
    "materials_and_consumables",
    "control_parameters",
    "in_process_inspection",
)

POLICY_GATED_PROCESS_FIELDS = (
    ("operator_qualification", "require_operator_qualification"),
    ("work_instruction_ref", "require_work_instruction_reference"),
)

PARAMETER_USABLE = "parameter-usable"
PARAMETER_UNBOUNDED = "parameter-unbounded"
PARAMETER_UNBRACKETED = "parameter-unbracketed"
PARAMETER_BAND_DEGENERATE = "parameter-band-degenerate"
PARAMETER_BAND_TOO_WIDE = "parameter-band-too-wide"

PROCESS_DESCRIBED = "process-described"
PROCESS_FIELDS_MISSING = "process-fields-missing"
PROCESS_PARAMETERS_THIN = "process-parameters-thin"
PROCESS_PARAMETER_UNUSABLE = "process-parameter-unusable"
PROCESS_UNINSTRUCTED = "process-uninstructed"

SEQUENCE_ORDERED = "sequence-ordered"
SEQUENCE_DUPLICATED = "sequence-duplicated"
SEQUENCE_GAPPED = "sequence-gapped"

DOCUMENT_ACCEPTABLE = "document-acceptable"
DOCUMENT_NOT_ACCEPTABLE = "document-not-acceptable"

DEFAULT_PID_CONTENT_POLICY = {
    "require_operator_qualification": True,
    "require_work_instruction_reference": True,
    "min_control_parameters_per_process": 1,
    "max_parameter_band_fraction": 0.50,
    "require_contiguous_sequence": True,
    "min_section_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_number(name, value)
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_count(name, value, floor=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < floor:
        raise ValueError("%s must be at least %d, got %r" % (name, floor, value))
    return value


def validate_pid_content_policy(policy):
    """Check a document-review policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag(
        "require_operator_qualification",
        policy.get("require_operator_qualification"),
    )
    _require_flag(
        "require_work_instruction_reference",
        policy.get("require_work_instruction_reference"),
    )
    _require_count(
        "min_control_parameters_per_process",
        policy.get("min_control_parameters_per_process"),
        1,
    )
    band = _require_number(
        "max_parameter_band_fraction", policy.get("max_parameter_band_fraction")
    )
    if band <= 0.0:
        raise ValueError(
            "max_parameter_band_fraction must be greater than 0, got %r" % (band,)
        )
    _require_flag(
        "require_contiguous_sequence", policy.get("require_contiguous_sequence")
    )
    _require_fraction("min_section_fraction", policy.get("min_section_fraction"))
    return policy


def required_document_sections():
    """The headings a process identification document is written to."""
    return tuple(REQUIRED_DOCUMENT_SECTIONS)


def required_process_fields():
    """The fields that make a described process re-runnable by somebody else."""
    return tuple(REQUIRED_PROCESS_FIELDS)


def audit_document_sections(document):
    """Which required headings the document does not actually carry."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping, got %r" % (document,))
    missing = []
    for section in REQUIRED_DOCUMENT_SECTIONS:
        value = document.get(section)
        if value is None:
            missing.append(section)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(section)
            continue
        if isinstance(value, (list, tuple, dict)) and not value:
            missing.append(section)
    return sorted(missing)


def audit_process_fields(process, policy=DEFAULT_PID_CONTENT_POLICY):
    """Which required fields this process record does not actually carry."""
    validate_pid_content_policy(policy)
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping, got %r" % (process,))
    missing = []
    for field in REQUIRED_PROCESS_FIELDS:
        value = process.get(field)
        if field == "control_parameters":
            if not isinstance(value, (list, tuple)) or not value:
                missing.append(field)
            continue
        if field == "sequence":
            if isinstance(value, bool) or not isinstance(value, int):
                missing.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def absent_gated_fields(process, policy=DEFAULT_PID_CONTENT_POLICY):
    """Which policy-gated fields the record leaves out for this review."""
    validate_pid_content_policy(policy)
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping, got %r" % (process,))
    absent = []
    for field, switch in POLICY_GATED_PROCESS_FIELDS:
        if not policy[switch]:
            continue
        value = process.get(field)
        if not isinstance(value, str) or not value.strip():
            absent.append(field)
    return sorted(absent)


def assess_control_parameter(parameter, policy=DEFAULT_PID_CONTENT_POLICY):
    """Does a control parameter carry a band that could actually control a process."""
    validate_pid_content_policy(policy)
    if not isinstance(parameter, dict):
        raise ValueError("control parameter must be a mapping, got %r" % (parameter,))
    name = _require_text("parameter name", parameter.get("name"))
    nominal = _require_number("%s nominal" % name, parameter.get("nominal"))
    minimum = parameter.get("minimum")
    maximum = parameter.get("maximum")
    if minimum is None or maximum is None:
        return {
            "name": name,
            "nominal": nominal,
            "minimum": None,
            "maximum": None,
            "band_width": None,
            "band_fraction": None,
            "verdict": PARAMETER_UNBOUNDED,
            "usable": False,
        }
    minimum = _require_number("%s minimum" % name, minimum)
    maximum = _require_number("%s maximum" % name, maximum)
    if not _at_most(minimum, maximum):
        raise ValueError(
            "%s declares a minimum above its maximum (%r > %r)"
            % (name, minimum, maximum)
        )
    band_width = maximum - minimum
    band_fraction = None
    if not _close(nominal, 0.0):
        band_fraction = band_width / abs(nominal)
    brackets = _at_most(minimum, nominal) and _at_least(maximum, nominal)
    degenerate = _close(band_width, 0.0)
    too_wide = band_fraction is not None and not _at_most(
        band_fraction, float(policy["max_parameter_band_fraction"])
    )
    if not brackets:
        verdict = PARAMETER_UNBRACKETED
    elif degenerate:
        verdict = PARAMETER_BAND_DEGENERATE
    elif too_wide:
        verdict = PARAMETER_BAND_TOO_WIDE
    else:
        verdict = PARAMETER_USABLE
    return {
        "name": name,
        "nominal": nominal,
        "minimum": minimum,
        "maximum": maximum,
        "band_width": band_width,
        "band_fraction": band_fraction,
        "verdict": verdict,
        "usable": verdict == PARAMETER_USABLE,
    }


def assess_process_sequence(processes, policy=DEFAULT_PID_CONTENT_POLICY):
    """Do the stated sequence numbers form one run from first to last."""
    validate_pid_content_policy(policy)
    if not isinstance(processes, (list, tuple)) or not processes:
        raise ValueError("processes must be a non-empty sequence of mappings")
    numbers = []
    for process in processes:
        if not isinstance(process, dict):
            raise ValueError("process must be a mapping, got %r" % (process,))
        value = process.get("sequence")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("process sequence must be an integer, got %r" % (value,))
        numbers.append(value)
    count = len(numbers)
    expected = set(range(1, count + 1))
    seen = set()
    repeated = set()
    for number in numbers:
        if number in seen:
            repeated.add(number)
        seen.add(number)
    duplicates = sorted(repeated)
    gaps = sorted(expected - seen)
    strays = sorted(number for number in seen if number not in expected)
    if duplicates:
        verdict = SEQUENCE_DUPLICATED
    elif gaps or strays:
        verdict = SEQUENCE_GAPPED
    else:
        verdict = SEQUENCE_ORDERED
    return {
        "stated_sequence": sorted(numbers),
        "expected_length": count,
        "duplicate_positions": duplicates,
        "missing_positions": gaps,
        "out_of_range_positions": strays,
        "verdict": verdict,
        "ordered": verdict == SEQUENCE_ORDERED,
    }


def assess_process_record(process, policy=DEFAULT_PID_CONTENT_POLICY):
    """Verdict for one described process, with the arms ranked."""
    validate_pid_content_policy(policy)
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping, got %r" % (process,))
    process_id = _require_text("process_id", process.get("process_id"))
    missing = audit_process_fields(process, policy)
    gated = absent_gated_fields(process, policy)
    findings = []

    parameters = []
    if "control_parameters" not in missing:
        for parameter in process["control_parameters"]:
            parameters.append(assess_control_parameter(parameter, policy))
    unusable = sorted(
        entry["name"] for entry in parameters if not entry["usable"]
    )
    thin = len(parameters) < int(policy["min_control_parameters_per_process"])

    if missing:
        verdict = PROCESS_FIELDS_MISSING
        findings.append(
            "process %s does not carry %s" % (process_id, ", ".join(missing))
        )
    elif thin:
        verdict = PROCESS_PARAMETERS_THIN
        findings.append(
            "process %s states %d control parameters against a floor of %d"
            % (
                process_id,
                len(parameters),
                int(policy["min_control_parameters_per_process"]),
            )
        )
    elif unusable:
        verdict = PROCESS_PARAMETER_UNUSABLE
        findings.append(
            "process %s carries unusable control parameters: %s"
            % (process_id, ", ".join(unusable))
        )
    elif gated:
        verdict = PROCESS_UNINSTRUCTED
        findings.append(
            "process %s leaves out %s, so nobody can tell who may run it or "
            "against what" % (process_id, ", ".join(gated))
        )
    else:
        verdict = PROCESS_DESCRIBED
    return {
        "process_id": process_id,
        "missing_fields": missing,
        "absent_gated_fields": gated,
        "parameter_assessments": parameters,
        "unusable_parameters": unusable,
        "verdict": verdict,
        "described": verdict == PROCESS_DESCRIBED,
        "findings": findings,
    }


def assess_process_identification_document(
    document, policy=DEFAULT_PID_CONTENT_POLICY
):
    """Full Annex F sweep over a process identification document."""
    validate_pid_content_policy(policy)
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping, got %r" % (document,))
    document_id = _require_text("document_identifier", document.get("document_identifier"))
    missing_sections = audit_document_sections(document)
    findings = [
        "document %s carries no %s section" % (document_id, section)
        for section in missing_sections
    ]

    processes = document.get("processes")
    if not isinstance(processes, (list, tuple)) or not processes:
        raise ValueError("document processes must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for process in processes:
        assessed = assess_process_record(process, policy)
        if assessed["process_id"] in seen:
            raise ValueError("document describes process %s twice" % assessed["process_id"])
        seen.add(assessed["process_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["process_id"])
    for entry in assessments:
        findings.extend(entry["findings"])

    declared = document.get("process_list")
    undescribed = []
    unlisted = []
    if isinstance(declared, (list, tuple)) and declared:
        declared_ids = {
            _require_text("process_list entry", item) for item in declared
        }
        undescribed = sorted(declared_ids - seen)
        unlisted = sorted(seen - declared_ids)
        for process_id in undescribed:
            findings.append(
                "document %s lists process %s and never describes it"
                % (document_id, process_id)
            )
        for process_id in unlisted:
            findings.append(
                "document %s describes process %s without listing it"
                % (document_id, process_id)
            )

    sequence = assess_process_sequence(processes, policy)
    sequence_ok = sequence["ordered"] or not policy["require_contiguous_sequence"]
    if not sequence_ok:
        findings.append(
            "the process flow in document %s is %s" % (document_id, sequence["verdict"])
        )

    total = len(REQUIRED_DOCUMENT_SECTIONS)
    stated = total - len(missing_sections)
    section_fraction = stated / float(total)
    minimum = float(policy["min_section_fraction"])
    sections_ok = _at_least(section_fraction, minimum)
    if not sections_ok:
        findings.append(
            "document %s carries %d of %d required sections against a required "
            "share of %.3f" % (document_id, stated, total, minimum)
        )

    open_processes = sorted(
        entry["process_id"] for entry in assessments if not entry["described"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["process_id"])
    acceptable = (
        sections_ok
        and sequence_ok
        and not missing_sections
        and not open_processes
        and not undescribed
        and not unlisted
    )
    return {
        "verdict": DOCUMENT_ACCEPTABLE if acceptable else DOCUMENT_NOT_ACCEPTABLE,
        "document_identifier": document_id,
        "missing_sections": missing_sections,
        "stated_section_fraction": section_fraction,
        "required_section_fraction": minimum,
        "process_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "open_process_ids": open_processes,
        "listed_but_undescribed": undescribed,
        "described_but_unlisted": unlisted,
        "process_sequence": sequence,
        "every_section_present": not missing_sections,
        "findings": findings,
    }
