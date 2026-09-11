#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex C -- Test Procedure DRD validation
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS testing standard's Annex C defines a Document Requirements
Definition (DRD) for the Test Procedure (TPRO) document. A TPRO must
carry: a header section identifying the document and its objective; an
ordered body of numbered steps each with an explicit action, expected
result, and optional data-recording entries (parameter, unit, acceptance
range); and a pass/fail criteria section listing measurable acceptance
conditions. This module validates a candidate TPRO record against those
requirements, grades each gap as CRITICAL (missing section or header
field), MAJOR (structural defect in a step or criterion), or MINOR
(sequencing or formatting deviation), and returns the full finding list.
"""

REQUIRED_HEADER_FIELDS = (
    "doc_id",
    "title",
    "revision",
    "objective",
    "test_level",
    "applicable_standard",
    "safety_requirements",
)

VALID_TEST_LEVELS = frozenset(
    {"unit", "subsystem", "system", "acceptance", "qualification", "protoflight"}
)

REQUIRED_STEP_FIELDS = ("action", "expected_result")

REQUIRED_DATA_RECORD_FIELDS = ("parameter", "unit", "acceptance_range")

REQUIRED_CRITERION_FIELDS = ("parameter", "condition", "acceptance_value")


def _finding(severity, location, issue):
    """Return a finding dict. Does not mutate any input."""
    return {"severity": severity, "location": location, "issue": issue}


def validate_header(header):
    """Validate the TPRO header against DRD Annex C required fields.

    Returns a list of finding dicts; empty means the header is
    structurally complete. Does not mutate header.
    """
    findings = []
    for field in REQUIRED_HEADER_FIELDS:
        value = header.get(field)
        if value is None or str(value).strip() == "":
            findings.append(
                _finding(
                    "CRITICAL",
                    "header.%s" % field,
                    "required header field '%s' is missing or empty" % field,
                )
            )
    test_level = header.get("test_level", "")
    if test_level and test_level not in VALID_TEST_LEVELS:
        findings.append(
            _finding(
                "MAJOR",
                "header.test_level",
                "test_level '%s' is not one of the recognized levels: %s"
                % (test_level, ", ".join(sorted(VALID_TEST_LEVELS))),
            )
        )
    return findings


def validate_data_record(record, step_idx, rec_idx):
    """Validate one data-recording entry within a procedure step.

    Returns a list of finding dicts; empty means the entry is complete.
    Does not mutate record.
    """
    findings = []
    for field in REQUIRED_DATA_RECORD_FIELDS:
        value = record.get(field)
        if value is None or str(value).strip() == "":
            findings.append(
                _finding(
                    "MAJOR",
                    "procedure[%d].data_to_record[%d].%s" % (step_idx, rec_idx, field),
                    "data record field '%s' is missing or empty in step %d, "
                    "record %d" % (field, step_idx + 1, rec_idx + 1),
                )
            )
    return findings


def validate_step(step, step_idx):
    """Validate one procedure step against DRD Annex C requirements.

    step_idx is the zero-based position in the procedure list; the
    expected step_number is step_idx + 1. Returns a list of finding
    dicts; empty means the step is structurally complete. Does not
    mutate step.
    """
    findings = []
    expected_number = step_idx + 1
    actual_number = step.get("step_number")
    if actual_number != expected_number:
        findings.append(
            _finding(
                "MINOR",
                "procedure[%d].step_number" % step_idx,
                "step_number %r does not match expected sequential value %d"
                % (actual_number, expected_number),
            )
        )
    for field in REQUIRED_STEP_FIELDS:
        value = step.get(field)
        if value is None or str(value).strip() == "":
            findings.append(
                _finding(
                    "MAJOR",
                    "procedure[%d].%s" % (step_idx, field),
                    "required step field '%s' is missing or empty in step %d"
                    % (field, step_idx + 1),
                )
            )
    for rec_idx, record in enumerate(step.get("data_to_record", [])):
        findings.extend(validate_data_record(record, step_idx, rec_idx))
    return findings


def validate_procedure(steps):
    """Validate the full ordered list of procedure steps.

    Returns a list of finding dicts. A CRITICAL finding is raised when
    the step list is empty. Does not mutate steps.
    """
    if not steps:
        return [
            _finding(
                "CRITICAL",
                "procedure",
                "procedure contains no steps; at least one step is required",
            )
        ]
    findings = []
    for idx, step in enumerate(steps):
        findings.extend(validate_step(step, idx))
    return findings


def validate_pass_fail_criteria(criteria):
    """Validate the pass/fail criteria section.

    Returns a list of finding dicts. A CRITICAL finding is raised when
    the criteria list is empty. Does not mutate criteria.
    """
    if not criteria:
        return [
            _finding(
                "CRITICAL",
                "pass_fail_criteria",
                "no pass/fail criteria defined; at least one criterion is required",
            )
        ]
    findings = []
    for ci, criterion in enumerate(criteria):
        for field in REQUIRED_CRITERION_FIELDS:
            value = criterion.get(field)
            if value is None or str(value).strip() == "":
                findings.append(
                    _finding(
                        "MAJOR",
                        "pass_fail_criteria[%d].%s" % (ci, field),
                        "criterion field '%s' is missing or empty in criterion %d"
                        % (field, ci + 1),
                    )
                )
    return findings


def validate_tpro(tpro):
    """Full TPRO document validation against ECSS-E-ST-10C Annex C DRD.

    tpro: dict with keys 'header' (dict), 'procedure' (list of step
    dicts), 'pass_fail_criteria' (list of criterion dicts).

    Returns a list of finding dicts (empty means structurally compliant).
    Does not mutate tpro or any nested value.
    """
    findings = []
    findings.extend(validate_header(tpro.get("header") or {}))
    findings.extend(validate_procedure(tpro.get("procedure") or []))
    findings.extend(validate_pass_fail_criteria(tpro.get("pass_fail_criteria") or []))
    return findings


def is_tpro_compliant(findings):
    """Return True when no CRITICAL or MAJOR finding is present.

    A TPRO with only MINOR findings is considered DRD-compliant for
    approval purposes; MINOR findings should still be resolved before
    operational use.
    """
    return all(f["severity"] not in ("CRITICAL", "MAJOR") for f in findings)
