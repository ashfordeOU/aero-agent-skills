#!/usr/bin/env python3
"""The data package a coverglass delivery is released against.

Anchor: ECSS-E-ST-20-08C clause 8.9. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The package carries two tiers that are graded together but never merged:

    qualification   the record set standing behind the coverglass type --
                    the qualification test report, the material and coating
                    specifications, the process document, and the approval
                    that closed the qualification. Written once, cited by
                    every later delivery, and governed by an issue.
    production      one data file per delivered batch, carrying the measured
                    data for the pieces that batch delivered and the
                    inspection outcome that went with them.

Four things decide whether the package can go out with the glass: is every
qualification family present, does every record cite the issue that actually
governs, do the delivered batches and the batch files agree in both
directions, and does each batch file carry a row for every piece its batch
delivered. A package that satisfies three of the four is not three quarters
releasable; it is short one thing somebody downstream will need.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_QUALIFICATION_RECORDS = (
    "coverglass-qualification-test-report",
    "coverglass-material-specification",
    "coverglass-coating-specification",
    "coverglass-process-document",
    "coverglass-qualification-approval",
)

REQUIRED_QUALIFICATION_FIELDS = (
    "record_id",
    "family",
    "issue",
    "reference",
    "approval_status",
)

REQUIRED_BATCH_FILE_FIELDS = (
    "file_id",
    "batch_id",
    "measured_data_rows",
    "inspection_summary",
    "issue",
    "approval_status",
)

APPROVAL_STATES = ("approved", "pending", "withdrawn")

RECORD_COMPLETE = "record-complete"
RECORD_SUPERSEDED_ISSUE = "record-superseded-issue"
RECORD_FIELDS_MISSING = "record-fields-missing"
RECORD_UNAPPROVED = "record-unapproved"

FILE_COMPLETE = "batch-file-complete"
FILE_FIELDS_MISSING = "batch-file-fields-missing"
FILE_ROWS_FOREIGN = "batch-file-rows-foreign"
FILE_ROWS_MISSING = "batch-file-rows-missing"
FILE_UNAPPROVED = "batch-file-unapproved"

PACKAGE_RELEASABLE = "package-releasable"
PACKAGE_NOT_RELEASABLE = "package-not-releasable"

DEFAULT_DOCUMENTATION_POLICY = {
    "require_per_piece_rows": True,
    "require_approved_records": True,
    "require_governing_issue_match": True,
    "min_recorded_family_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_id_set(name, value):
    if not isinstance(value, (list, tuple, set, frozenset)) or not value:
        raise ValueError("%s must be a non-empty sequence of identifiers" % name)
    read = set()
    for item in value:
        read.add(_require_text("%s entry" % name, item))
    return read


def required_qualification_records():
    """The qualification families the package owes for the coverglass type."""
    return tuple(REQUIRED_QUALIFICATION_RECORDS)


def required_batch_file_fields():
    """The fields a production batch data file has to carry to be readable."""
    return tuple(REQUIRED_BATCH_FILE_FIELDS)


def validate_documentation_policy(policy):
    """Check a documentation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("require_per_piece_rows", policy.get("require_per_piece_rows"))
    _require_flag("require_approved_records", policy.get("require_approved_records"))
    _require_flag(
        "require_governing_issue_match", policy.get("require_governing_issue_match")
    )
    _require_fraction(
        "min_recorded_family_fraction", policy.get("min_recorded_family_fraction")
    )
    return policy


def approval_state(record):
    """Has this record been released, or is it still sitting in draft."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    state = record.get("approval_status")
    if state is None:
        return "pending"
    state = _require_text("approval_status", state).lower()
    if state not in APPROVAL_STATES:
        raise ValueError(
            "approval_status must be one of %s, got %r"
            % (", ".join(APPROVAL_STATES), state)
        )
    return state


def audit_qualification_fields(record):
    """Which required fields this qualification record does not carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = []
    for field in REQUIRED_QUALIFICATION_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def assess_qualification_record(
    record, governing_issues, policy=DEFAULT_DOCUMENTATION_POLICY
):
    """Verdict for one qualification record, with the arms ranked."""
    validate_documentation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    if not isinstance(governing_issues, dict) or not governing_issues:
        raise ValueError("governing_issues must be a non-empty mapping")
    family = _require_text("family", record.get("family"))
    if family not in REQUIRED_QUALIFICATION_RECORDS:
        raise ValueError("record names an unknown qualification family %s" % family)
    record_id = _require_text("record_id", record.get("record_id"))

    missing = audit_qualification_fields(record)
    findings = []
    governing = governing_issues.get(family)
    cited = record.get("issue")
    issue_matches = True
    if policy["require_governing_issue_match"]:
        if not isinstance(governing, str) or not governing.strip():
            raise ValueError("no governing issue declared for family %s" % family)
        if isinstance(cited, str) and cited.strip():
            issue_matches = cited.strip() == governing.strip()
        else:
            issue_matches = False

    state = approval_state(record)
    approved = state == "approved"

    if policy["require_governing_issue_match"] and "issue" not in missing and not issue_matches:
        verdict = RECORD_SUPERSEDED_ISSUE
        findings.append(
            "record %s cites %s of %s while %s governs this delivery"
            % (record_id, cited, family, governing)
        )
    elif missing:
        verdict = RECORD_FIELDS_MISSING
        findings.append(
            "record %s for %s does not carry %s"
            % (record_id, family, ", ".join(missing))
        )
    elif policy["require_approved_records"] and not approved:
        verdict = RECORD_UNAPPROVED
        findings.append(
            "record %s is still %s, so the qualification tier has not been released"
            % (record_id, state)
        )
    else:
        verdict = RECORD_COMPLETE

    return {
        "record_id": record_id,
        "family": family,
        "cited_issue": cited.strip() if isinstance(cited, str) and cited.strip() else None,
        "governing_issue": governing,
        "issue_matches": issue_matches,
        "missing_fields": missing,
        "approval_status": state,
        "approved": approved,
        "verdict": verdict,
        "complete": verdict == RECORD_COMPLETE,
        "findings": findings,
    }


def audit_batch_file_fields(batch_file):
    """Which required fields this batch data file does not carry."""
    if not isinstance(batch_file, dict):
        raise ValueError("batch_file must be a mapping, got %r" % (batch_file,))
    missing = []
    for field in REQUIRED_BATCH_FILE_FIELDS:
        value = batch_file.get(field)
        if field == "measured_data_rows":
            if not isinstance(value, (list, tuple)) or not value:
                missing.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def row_piece_ids(batch_file):
    """The pieces the measured data table actually carries a row for."""
    if not isinstance(batch_file, dict):
        raise ValueError("batch_file must be a mapping, got %r" % (batch_file,))
    rows = batch_file.get("measured_data_rows")
    if not isinstance(rows, (list, tuple)):
        raise ValueError("measured_data_rows must be a sequence, got %r" % (rows,))
    read = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("measured data row must be a mapping, got %r" % (row,))
        read.append(_require_text("row piece_id", row.get("piece_id")))
    return sorted(set(read))


def assess_batch_file(batch_file, batch, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Verdict for one production batch data file against its delivered batch."""
    validate_documentation_policy(policy)
    if not isinstance(batch_file, dict):
        raise ValueError("batch_file must be a mapping, got %r" % (batch_file,))
    if not isinstance(batch, dict):
        raise ValueError("batch must be a mapping, got %r" % (batch,))
    file_id = _require_text("file_id", batch_file.get("file_id"))
    batch_id = _require_text("batch_id", batch.get("batch_id"))
    delivered = _require_id_set("piece_ids", batch.get("piece_ids"))

    if _require_text("batch_id", batch_file.get("batch_id")) != batch_id:
        raise ValueError(
            "file %s is being read against batch %s it does not name" % (file_id, batch_id)
        )

    missing = audit_batch_file_fields(batch_file)
    findings = []
    covered = []
    foreign = []
    uncovered = sorted(delivered)
    if "measured_data_rows" not in missing:
        rows = set(row_piece_ids(batch_file))
        covered = sorted(rows & delivered)
        foreign = sorted(rows - delivered)
        uncovered = sorted(delivered - rows)

    state = approval_state(batch_file)
    approved = state == "approved"

    if foreign:
        verdict = FILE_ROWS_FOREIGN
        findings.append(
            "file %s carries rows for %s, which batch %s did not deliver"
            % (file_id, ", ".join(foreign), batch_id)
        )
    elif missing:
        verdict = FILE_FIELDS_MISSING
        findings.append(
            "file %s for batch %s does not carry %s"
            % (file_id, batch_id, ", ".join(missing))
        )
    elif policy["require_per_piece_rows"] and uncovered:
        verdict = FILE_ROWS_MISSING
        findings.append(
            "file %s leaves %s of batch %s with no measured row of their own"
            % (file_id, ", ".join(uncovered), batch_id)
        )
    elif policy["require_approved_records"] and not approved:
        verdict = FILE_UNAPPROVED
        findings.append(
            "file %s for batch %s is still %s at delivery" % (file_id, batch_id, state)
        )
    else:
        verdict = FILE_COMPLETE

    delivered_count = len(delivered)
    return {
        "file_id": file_id,
        "batch_id": batch_id,
        "missing_fields": missing,
        "covered_piece_ids": covered,
        "uncovered_piece_ids": uncovered,
        "foreign_piece_ids": foreign,
        "row_coverage_fraction": len(covered) / float(delivered_count),
        "approval_status": state,
        "approved": approved,
        "verdict": verdict,
        "complete": verdict == FILE_COMPLETE,
        "findings": findings,
    }


def reconcile_batches(delivered_batches, batch_files):
    """Do the delivered batches and the batch files agree in both directions."""
    if not isinstance(delivered_batches, (list, tuple)) or not delivered_batches:
        raise ValueError("delivered_batches must be a non-empty sequence of mappings")
    if not isinstance(batch_files, (list, tuple)):
        raise ValueError("batch_files must be a sequence, got %r" % (batch_files,))
    declared = []
    for batch in delivered_batches:
        if not isinstance(batch, dict):
            raise ValueError("batch must be a mapping, got %r" % (batch,))
        batch_id = _require_text("batch_id", batch.get("batch_id"))
        if batch_id in declared:
            raise ValueError("delivery declares batch %s twice" % batch_id)
        declared.append(batch_id)
    filed = []
    for batch_file in batch_files:
        if not isinstance(batch_file, dict):
            raise ValueError("batch_file must be a mapping, got %r" % (batch_file,))
        filed.append(_require_text("batch_id", batch_file.get("batch_id")))
    return {
        "declared_batch_ids": sorted(declared),
        "filed_batch_ids": sorted(set(filed)),
        "batches_without_a_file": sorted(set(declared) - set(filed)),
        "files_without_a_batch": sorted(set(filed) - set(declared)),
        "reconciled": sorted(set(declared)) == sorted(set(filed)),
    }


def assess_data_package(package, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Full clause 8.9 sweep over a coverglass delivery data package."""
    validate_documentation_policy(policy)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    package_id = _require_text("package_id", package.get("package_id"))
    governing_issues = package.get("governing_issues")
    if not isinstance(governing_issues, dict) or not governing_issues:
        raise ValueError("package must declare the governing issue of each family")

    records = package.get("qualification_records")
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("qualification_records must be a non-empty sequence")
    batches = package.get("delivered_batches")
    if not isinstance(batches, (list, tuple)) or not batches:
        raise ValueError("delivered_batches must be a non-empty sequence")
    files = package.get("batch_files")
    if not isinstance(files, (list, tuple)):
        raise ValueError("batch_files must be a sequence, got %r" % (files,))

    seen_records = set()
    record_assessments = []
    for record in records:
        assessed = assess_qualification_record(record, governing_issues, policy)
        if assessed["record_id"] in seen_records:
            raise ValueError("package declares record %s twice" % assessed["record_id"])
        seen_records.add(assessed["record_id"])
        record_assessments.append(assessed)
    record_assessments.sort(key=lambda entry: entry["record_id"])

    reconciliation = reconcile_batches(batches, files)
    batch_index = {
        _require_text("batch_id", batch.get("batch_id")): batch for batch in batches
    }

    seen_files = set()
    file_assessments = []
    for batch_file in files:
        file_id = _require_text("file_id", batch_file.get("file_id"))
        if file_id in seen_files:
            raise ValueError("package declares file %s twice" % file_id)
        seen_files.add(file_id)
        batch_id = _require_text("batch_id", batch_file.get("batch_id"))
        batch = batch_index.get(batch_id)
        if batch is None:
            continue
        file_assessments.append(assess_batch_file(batch_file, batch, policy))
    file_assessments.sort(key=lambda entry: entry["file_id"])

    findings = []
    recorded_families = {entry["family"] for entry in record_assessments}
    missing_families = sorted(set(REQUIRED_QUALIFICATION_RECORDS) - recorded_families)
    for family in missing_families:
        findings.append(
            "package %s carries no %s at all" % (package_id, family)
        )
    for entry in record_assessments:
        findings.extend(entry["findings"])
    for batch_id in reconciliation["batches_without_a_file"]:
        findings.append(
            "batch %s is delivered with no data file of its own" % batch_id
        )
    for batch_id in reconciliation["files_without_a_batch"]:
        findings.append(
            "a data file reports on batch %s, which this delivery does not contain"
            % batch_id
        )
    for entry in file_assessments:
        findings.extend(entry["findings"])

    total_families = len(REQUIRED_QUALIFICATION_RECORDS)
    recorded_fraction = len(recorded_families) / float(total_families)
    minimum = float(policy["min_recorded_family_fraction"])
    families_ok = _at_least(recorded_fraction, minimum)
    if not families_ok:
        findings.append(
            "package %s carries %d of %d qualification families against a required "
            "share of %.3f"
            % (package_id, len(recorded_families), total_families, minimum)
        )

    open_records = sorted(
        entry["record_id"] for entry in record_assessments if not entry["complete"]
    )
    open_files = sorted(
        entry["file_id"] for entry in file_assessments if not entry["complete"]
    )
    grouped_records = {}
    for entry in record_assessments:
        grouped_records.setdefault(entry["verdict"], []).append(entry["record_id"])
    grouped_files = {}
    for entry in file_assessments:
        grouped_files.setdefault(entry["verdict"], []).append(entry["file_id"])

    releasable = (
        families_ok
        and not missing_families
        and not open_records
        and not open_files
        and reconciliation["reconciled"]
    )
    return {
        "verdict": PACKAGE_RELEASABLE if releasable else PACKAGE_NOT_RELEASABLE,
        "package_id": package_id,
        "qualification_assessments": record_assessments,
        "batch_file_assessments": file_assessments,
        "grouped_records_by_verdict": {k: sorted(v) for k, v in grouped_records.items()},
        "grouped_files_by_verdict": {k: sorted(v) for k, v in grouped_files.items()},
        "missing_qualification_families": missing_families,
        "recorded_family_fraction": recorded_fraction,
        "required_family_fraction": minimum,
        "batch_reconciliation": reconciliation,
        "open_record_ids": open_records,
        "open_file_ids": open_files,
        "every_family_recorded": not missing_families,
        "findings": findings,
    }
