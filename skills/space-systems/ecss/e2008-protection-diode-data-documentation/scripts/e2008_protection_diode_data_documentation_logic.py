#!/usr/bin/env python3
"""The data package a protection diode delivery is released against.

Anchor: ECSS-E-ST-20-08C clause 9.8. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

The package carries two tiers that are graded together but never merged:

    qualification   the record set standing behind the protection diode type
                    -- the qualification test report, the source control
                    drawing, the construction and materials list, the process
                    document, and the approval that closed the qualification.
                    Written once, cited by every later delivery, governed by
                    an issue.
    production      one data file for each delivered component batch, holding
                    the characterisation data for the parts that batch
                    delivered and the inspection outcome that went with them.

Four things decide whether the package can go out with the diodes: is every
qualification family present, does every record cite the issue that actually
governs this delivery, do the delivered batches and the batch data files
agree in both directions, and does each file carry a characterisation row for
every part its batch delivered. A package satisfying three of the four is not
three quarters releasable; it is short one thing somebody downstream will
need, and the four ask for four different pieces of work.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_QUALIFICATION_RECORDS = (
    "protection-diode-qualification-test-report",
    "protection-diode-source-control-drawing",
    "protection-diode-construction-materials-list",
    "protection-diode-process-document",
    "protection-diode-qualification-approval",
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
    "characterisation_rows",
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
FILE_ROWS_FOREIGN = "batch-file-rows-foreign"
FILE_FIELDS_MISSING = "batch-file-fields-missing"
FILE_ROWS_MISSING = "batch-file-rows-missing"
FILE_UNAPPROVED = "batch-file-unapproved"

PACKAGE_RELEASABLE = "package-releasable"
PACKAGE_NOT_RELEASABLE = "package-not-releasable"

DEFAULT_DOCUMENTATION_POLICY = {
    "require_per_part_rows": True,
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
    """The qualification families the package owes for the diode type."""
    return tuple(REQUIRED_QUALIFICATION_RECORDS)


def required_batch_file_fields():
    """The fields a component batch data file has to carry to be readable."""
    return tuple(REQUIRED_BATCH_FILE_FIELDS)


def validate_documentation_policy(policy):
    """Check a documentation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("require_per_part_rows", policy.get("require_per_part_rows"))
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

    if (
        policy["require_governing_issue_match"]
        and "issue" not in missing
        and not issue_matches
    ):
        verdict = RECORD_SUPERSEDED_ISSUE
        findings.append(
            "record %s cites issue %s of %s while %s governs this delivery"
            % (record_id, cited.strip(), family, governing.strip())
        )
    elif missing:
        verdict = RECORD_FIELDS_MISSING
        findings.append(
            "record %s for %s carries no %s" % (record_id, family, ", ".join(missing))
        )
    elif policy["require_approved_records"] and not approved:
        verdict = RECORD_UNAPPROVED
        findings.append(
            "record %s for %s is %s at delivery, so the approval step has moved "
            "past the point anybody could act on it" % (record_id, family, state)
        )
    else:
        verdict = RECORD_COMPLETE

    return {
        "record_id": record_id,
        "family": family,
        "verdict": verdict,
        "complete": verdict == RECORD_COMPLETE,
        "missing_fields": missing,
        "issue_matches_governing": issue_matches,
        "approval_state": state,
        "findings": findings,
    }


def audit_batch_file_fields(data_file):
    """Which required fields this batch data file does not carry."""
    if not isinstance(data_file, dict):
        raise ValueError("data_file must be a mapping, got %r" % (data_file,))
    missing = []
    for field in REQUIRED_BATCH_FILE_FIELDS:
        value = data_file.get(field)
        if field == "characterisation_rows":
            if not isinstance(value, (list, tuple)) or not value:
                missing.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def row_coverage(data_file, delivered_part_ids):
    """Which delivered parts have a characterisation row, and which rows are foreign."""
    if not isinstance(data_file, dict):
        raise ValueError("data_file must be a mapping, got %r" % (data_file,))
    delivered = _require_id_set("delivered_part_ids", delivered_part_ids)
    rows = data_file.get("characterisation_rows")
    if not isinstance(rows, (list, tuple)):
        raise ValueError("characterisation_rows must be a sequence of mappings")
    carried = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("characterisation row must be a mapping, got %r" % (row,))
        carried.add(_require_text("row part_id", row.get("part_id")))
    missing = sorted(delivered - carried)
    foreign = sorted(carried - delivered)
    covered = len(delivered & carried)
    return {
        "delivered_count": len(delivered),
        "covered_count": covered,
        "coverage_fraction": covered / float(len(delivered)),
        "missing_row_part_ids": missing,
        "foreign_row_part_ids": foreign,
    }


def assess_batch_file(
    data_file, delivered_part_ids, governing_issue, policy=DEFAULT_DOCUMENTATION_POLICY
):
    """Verdict for one component batch data file against its own batch."""
    validate_documentation_policy(policy)
    missing = audit_batch_file_fields(data_file)
    batch_id = _require_text("batch_id", data_file.get("batch_id"))
    file_id = _require_text("file_id", data_file.get("file_id"))
    coverage = row_coverage(data_file, delivered_part_ids)
    state = approval_state(data_file)
    findings = []

    issue_matches = True
    if policy["require_governing_issue_match"]:
        governing = _require_text("governing_issue", governing_issue)
        cited = data_file.get("issue")
        issue_matches = (
            isinstance(cited, str) and cited.strip() == governing
        )

    if coverage["foreign_row_part_ids"]:
        verdict = FILE_ROWS_FOREIGN
        findings.append(
            "file %s reports on %s, which batch %s never delivered"
            % (file_id, ", ".join(coverage["foreign_row_part_ids"]), batch_id)
        )
    elif missing:
        verdict = FILE_FIELDS_MISSING
        findings.append(
            "file %s for batch %s carries no %s"
            % (file_id, batch_id, ", ".join(missing))
        )
    elif policy["require_per_part_rows"] and coverage["missing_row_part_ids"]:
        verdict = FILE_ROWS_MISSING
        findings.append(
            "file %s leaves %s of batch %s with no characterisation row"
            % (file_id, ", ".join(coverage["missing_row_part_ids"]), batch_id)
        )
    elif policy["require_approved_records"] and state != "approved":
        verdict = FILE_UNAPPROVED
        findings.append(
            "file %s for batch %s is %s at delivery" % (file_id, batch_id, state)
        )
    else:
        verdict = FILE_COMPLETE

    if policy["require_governing_issue_match"] and not issue_matches:
        findings.append(
            "file %s for batch %s does not cite the issue governing this delivery"
            % (file_id, batch_id)
        )

    return {
        "file_id": file_id,
        "batch_id": batch_id,
        "verdict": verdict,
        "complete": verdict == FILE_COMPLETE and issue_matches,
        "missing_fields": missing,
        "issue_matches_governing": issue_matches,
        "approval_state": state,
        "coverage": coverage,
        "findings": findings,
    }


def reconcile_batches(delivered_batch_ids, batch_files):
    """Batches against files, in both directions."""
    delivered = []
    seen = set()
    for batch_id in _require_id_set("delivered_batch_ids", delivered_batch_ids):
        delivered.append(batch_id)
    if not isinstance(batch_files, (list, tuple)):
        raise ValueError("batch_files must be a sequence of mappings")
    filed = set()
    for data_file in batch_files:
        if not isinstance(data_file, dict):
            raise ValueError("batch file must be a mapping, got %r" % (data_file,))
        batch_id = _require_text("batch_id", data_file.get("batch_id"))
        if batch_id in filed:
            raise ValueError("batch %s is declared by two data files" % batch_id)
        filed.add(batch_id)
    delivered_set = set(delivered)
    if len(delivered_set) != len(delivered):
        raise ValueError("delivered_batch_ids repeats a batch")
    seen.update(delivered_set)
    return {
        "delivered_batch_ids": sorted(delivered_set),
        "filed_batch_ids": sorted(filed),
        "batches_without_a_file": sorted(delivered_set - filed),
        "files_without_a_batch": sorted(filed - delivered_set),
        "reconciled": delivered_set == filed,
    }


def audit_data_package(package, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Full clause 9.8 sweep over one protection diode data package."""
    validate_documentation_policy(policy)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    package_id = _require_text("package_id", package.get("package_id"))

    governing_issues = package.get("governing_issues")
    if not isinstance(governing_issues, dict) or not governing_issues:
        raise ValueError("governing_issues must be a non-empty mapping")

    records = package.get("qualification_records")
    if not isinstance(records, (list, tuple)):
        raise ValueError("qualification_records must be a sequence of mappings")

    findings = []
    record_assessments = []
    families_present = set()
    for record in records:
        assessed = assess_qualification_record(record, governing_issues, policy)
        record_assessments.append(assessed)
        families_present.add(assessed["family"])
    record_assessments.sort(key=lambda entry: (entry["family"], entry["record_id"]))

    unrecorded_families = sorted(
        set(REQUIRED_QUALIFICATION_RECORDS) - families_present
    )
    for family in unrecorded_families:
        findings.append(
            "package %s carries no record at all for %s" % (package_id, family)
        )
    recorded_fraction = len(families_present & set(REQUIRED_QUALIFICATION_RECORDS)) / float(
        len(REQUIRED_QUALIFICATION_RECORDS)
    )
    family_share_ok = _at_least(
        recorded_fraction, float(policy["min_recorded_family_fraction"])
    )

    batches = package.get("delivered_batches")
    if not isinstance(batches, (list, tuple)) or not batches:
        raise ValueError("delivered_batches must be a non-empty sequence of mappings")
    delivered_parts = {}
    batch_ids = []
    for batch in batches:
        if not isinstance(batch, dict):
            raise ValueError("delivered batch must be a mapping, got %r" % (batch,))
        batch_id = _require_text("batch_id", batch.get("batch_id"))
        batch_ids.append(batch_id)
        delivered_parts[batch_id] = _require_id_set(
            "delivered_part_ids for %s" % batch_id, batch.get("delivered_part_ids")
        )

    batch_files = package.get("batch_data_files")
    if not isinstance(batch_files, (list, tuple)):
        raise ValueError("batch_data_files must be a sequence of mappings")
    reconciliation = reconcile_batches(batch_ids, batch_files)
    for batch_id in reconciliation["batches_without_a_file"]:
        findings.append(
            "batch %s was delivered with no data file in package %s"
            % (batch_id, package_id)
        )
    for batch_id in reconciliation["files_without_a_batch"]:
        findings.append(
            "package %s carries a data file for batch %s, which this delivery "
            "does not contain" % (package_id, batch_id)
        )

    batch_governing = governing_issues.get("batch-data-file")
    file_assessments = []
    for data_file in batch_files:
        batch_id = _require_text("batch_id", data_file.get("batch_id"))
        if batch_id not in delivered_parts:
            continue
        assessed = assess_batch_file(
            data_file, delivered_parts[batch_id], batch_governing, policy
        )
        file_assessments.append(assessed)
    file_assessments.sort(key=lambda entry: entry["batch_id"])

    for entry in record_assessments:
        findings.extend(entry["findings"])
    for entry in file_assessments:
        findings.extend(entry["findings"])

    records_complete = all(entry["complete"] for entry in record_assessments)
    files_complete = all(entry["complete"] for entry in file_assessments)
    releasable = (
        not unrecorded_families
        and family_share_ok
        and records_complete
        and files_complete
        and reconciliation["reconciled"]
    )
    return {
        "verdict": PACKAGE_RELEASABLE if releasable else PACKAGE_NOT_RELEASABLE,
        "package_id": package_id,
        "record_assessments": record_assessments,
        "file_assessments": file_assessments,
        "unrecorded_families": unrecorded_families,
        "recorded_family_fraction": recorded_fraction,
        "recorded_family_share_ok": family_share_ok,
        "reconciliation": reconciliation,
        "records_complete": records_complete,
        "files_complete": files_complete,
        "findings": findings,
    }
