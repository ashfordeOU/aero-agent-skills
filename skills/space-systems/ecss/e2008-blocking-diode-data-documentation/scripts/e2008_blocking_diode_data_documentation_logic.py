"""Supplier data package behind a blocking diode delivery.

Anchor: ECSS-E-ST-20-08C clause 12.8. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A blocking diode data package stands on two tiers, and grading them as one
list is the failure this module exists to catch.

    qualification tier  issued once for the diode type. Every delivered
                        batch cites it. It is not re-issued per batch, so
                        a sweep that walks it once and stops has walked
                        the cheap half of the package
    batch tier          one data file per delivered batch. This is where a
                        package silently loses most of a delivery: four
                        batches went out, one file came in, and a
                        family-by-family sweep finds every family present
                        somewhere and reports green

So the batch set is reconciled against the declared delivery rather than
inspected. It is reconciled BOTH ways: a declared batch with no file is
missing, and a file for a batch the delivery never declares is not a
bonus, it is the package and the delivery record contradicting each other.

Blocking diodes are delivered as serialized parts, which adds a second
reconciliation an unserialized article never needs. The electrical
screening record is the only document that descends to the individual
diode, so it can be present, approved and at the governing issue while
holding forty rows for a batch of four hundred delivered diodes. That
check runs both ways too: a delivered serial with no screening row is
uncovered, and a row for a serial the batch never held is foreign data.

Finally the package carries dates that have to sit in order. Screening
that predates the completion of the batch it screened did not screen that
batch, and screening dated after the delivery it released was not
available when the delivery went out. Both read as ordinary dates until
somebody puts them on a line.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

__all__ = [
    "APPROVAL_STATES",
    "BATCH_CONDITIONAL_FAMILIES",
    "BATCH_REQUIRED_FAMILIES",
    "COVERAGE_TOLERANCE",
    "FAMILY_NOT_APPROVED",
    "FAMILY_MISSING",
    "FAMILY_PRESENT",
    "KNOWN_FAMILIES",
    "PACKAGE_HELD",
    "PACKAGE_RELEASABLE",
    "QUALIFICATION_FAMILIES",
    "QUALIFICATION_APPROVAL_FAMILY",
    "SCREENING_FAMILY",
    "evaluate_batch_file",
    "evaluate_data_package",
    "evaluate_qualification_tier",
    "governing_record",
    "grade_family",
    "group_records",
    "normalize_approval_state",
    "normalize_family",
    "parse_package_date",
    "reconcile_batch_set",
    "reconcile_screening_serials",
    "resolve_batch_families",
    "validate_record",
    "verify_date_order",
]

# Issued once for the diode type and cited by every delivered batch.
QUALIFICATION_FAMILIES = (
    "diode-type-qualification-test-report",
    "diode-design-and-construction-data",
    "diode-materials-and-process-declaration",
    "diode-type-qualification-approval-statement",
)

QUALIFICATION_APPROVAL_FAMILY = "diode-type-qualification-approval-statement"

# One data file per delivered batch carries these unconditionally.
BATCH_REQUIRED_FAMILIES = (
    "batch-identification-record",
    "batch-electrical-screening-record",
    "batch-visual-inspection-record",
    "batch-acceptance-certificate",
)

SCREENING_FAMILY = "batch-electrical-screening-record"

# Owed only because something happened. The flag has to be STATED: if it
# is inferred from what was submitted, a missing family becomes invisible
# because nothing came in, so nothing looks owed.
BATCH_CONDITIONAL_FAMILIES = {
    "nonconformance_raised": "batch-nonconformance-report",
    "waiver_granted": "batch-waiver-record",
    "rework_performed": "batch-rework-and-retest-record",
}

KNOWN_FAMILIES = (
    QUALIFICATION_FAMILIES
    + BATCH_REQUIRED_FAMILIES
    + tuple(sorted(BATCH_CONDITIONAL_FAMILIES.values()))
)

# An approval is a state, not a presence. Only one of these is evidence.
APPROVAL_STATES = ("approved", "in-review", "draft", "withdrawn")

FAMILY_PRESENT = "family-present-and-approved"
FAMILY_MISSING = "family-missing"
FAMILY_NOT_APPROVED = "family-present-but-not-approved"

PACKAGE_RELEASABLE = "data-package-releasable"
PACKAGE_HELD = "data-package-held"

# Coverage is a ratio of two integers but it is compared against declared
# decimal thresholds, so the comparison absorbs representation error at a
# named tolerance rather than landing differently on two platforms.
COVERAGE_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _issue(value, label):
    """Return a positive integer issue number, refusing a bool or a float."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def parse_package_date(value, label):
    """Return an ISO-8601 calendar date, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO-8601 date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO-8601 date: %r" % (label, value))


def normalize_family(family, label="record family"):
    """Return a recognized document family name."""
    if not isinstance(family, str):
        raise ValueError("%s must be a string, got %r" % (label, family))
    cleaned = family.strip().lower()
    if cleaned not in KNOWN_FAMILIES:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, family, ", ".join(KNOWN_FAMILIES))
        )
    return cleaned


def normalize_approval_state(state, label="approval state"):
    """Return a recognized approval state."""
    if not isinstance(state, str):
        raise ValueError("%s must be a string, got %r" % (label, state))
    cleaned = state.strip().lower()
    if cleaned not in APPROVAL_STATES:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, state, ", ".join(APPROVAL_STATES))
        )
    return cleaned


def validate_record(record, label="record"):
    """Return one validated package record."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("family", "reference", "issue", "approval_state", "approval_date"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (label, key))
    state = normalize_approval_state(
        record["approval_state"], "%s approval_state" % label
    )
    date_value = record["approval_date"]
    approval_date = None
    if date_value is not None:
        approval_date = parse_package_date(date_value, "%s approval_date" % label)
    if state == "approved" and approval_date is None:
        raise ValueError(
            "%s is approved but carries no approval_date" % label
        )
    return {
        "family": normalize_family(record["family"], "%s family" % label),
        "reference": _identifier(record["reference"], "%s reference" % label),
        "issue": _issue(record["issue"], "%s issue" % label),
        "approval_state": state,
        "approval_date": approval_date,
        "approved": state == "approved",
    }


def governing_record(records):
    """Return the highest-issue record of one family; the rest are superseded.

    Inside a family several issues can sit together. The highest governs
    and the lower ones are superseded rather than missing, so a package can
    hold exactly the right document at the wrong issue and pass a check
    that only asks whether the name is there.
    """
    if not records:
        raise ValueError("governing_record needs at least one record")
    ordered = sorted(records, key=lambda r: (r["issue"], r["reference"]))
    return ordered[-1]


def group_records(records):
    """Group validated records by family, naming the governing issue of each."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of record mappings")
    validated = []
    for index, record in enumerate(records):
        validated.append(validate_record(record, "records[%d]" % index))
    grouped = {}
    for record in validated:
        grouped.setdefault(record["family"], []).append(record)
    out = {}
    for family, members in grouped.items():
        governing = governing_record(members)
        out[family] = {
            "governing": governing,
            "superseded": tuple(
                r for r in sorted(members, key=lambda r: (r["issue"], r["reference"]))
                if r is not governing
            ),
            "issue_count": len(members),
        }
    return out


def grade_family(family, grouped, label="package"):
    """Grade one owed family on presence and on approval state."""
    family = normalize_family(family)
    entry = grouped.get(family)
    if entry is None:
        return {
            "family": family,
            "status": FAMILY_MISSING,
            "reference": None,
            "issue": None,
            "approval_state": None,
            "finding": "%s owes family %s and no record of it was submitted"
            % (label, family),
        }
    governing = entry["governing"]
    if not governing["approved"]:
        return {
            "family": family,
            "status": FAMILY_NOT_APPROVED,
            "reference": governing["reference"],
            "issue": governing["issue"],
            "approval_state": governing["approval_state"],
            "finding": "%s holds family %s at issue %d in state '%s', which is in "
            "the package and is still not evidence"
            % (label, family, governing["issue"], governing["approval_state"]),
        }
    return {
        "family": family,
        "status": FAMILY_PRESENT,
        "reference": governing["reference"],
        "issue": governing["issue"],
        "approval_state": governing["approval_state"],
        "finding": None,
    }


def evaluate_qualification_tier(records):
    """Grade the type-level tier and read off the approval every batch cites."""
    grouped = group_records(records)
    families = tuple(
        grade_family(family, grouped, "qualification tier")
        for family in QUALIFICATION_FAMILIES
    )
    findings = [f["finding"] for f in families if f["finding"]]
    approval = grouped.get(QUALIFICATION_APPROVAL_FAMILY)
    governing_approval = None
    if approval is not None and approval["governing"]["approved"]:
        governing_approval = {
            "reference": approval["governing"]["reference"],
            "issue": approval["governing"]["issue"],
            "approval_date": approval["governing"]["approval_date"],
        }
    return {
        "families": families,
        "governing_approval": governing_approval,
        "findings": findings,
        "accepted": not findings,
    }


def resolve_batch_families(context, label="batch"):
    """Return the families this batch owes, from its STATED context.

    Every conditional flag has to be present and boolean. Defaulting an
    absent flag to False is what makes a missing family invisible.
    """
    if not isinstance(context, dict):
        raise ValueError("%s context must be a mapping" % label)
    owed = list(BATCH_REQUIRED_FAMILIES)
    for flag in sorted(BATCH_CONDITIONAL_FAMILIES):
        if flag not in context:
            raise ValueError(
                "%s context must state '%s' explicitly rather than leaving it to "
                "be inferred from what was submitted" % (label, flag)
            )
        value = context[flag]
        if not isinstance(value, bool):
            raise ValueError(
                "%s context flag '%s' must be a boolean, got %r" % (label, flag, value)
            )
        if value:
            owed.append(BATCH_CONDITIONAL_FAMILIES[flag])
    return tuple(owed)


def reconcile_screening_serials(delivered_serials, screened_serials, label="batch"):
    """Reconcile screening rows against the diodes the batch delivered.

    Both directions. A delivered serial with no row is uncovered; a row for
    a serial the batch never held means the screening record and the batch
    identification disagree, and one of them is wrong.
    """
    if not isinstance(delivered_serials, (list, tuple)) or not delivered_serials:
        raise ValueError("%s must declare at least one delivered serial" % label)
    if not isinstance(screened_serials, (list, tuple)):
        raise ValueError("%s screened serials must be a sequence" % label)
    delivered = []
    seen = set()
    for index, serial in enumerate(delivered_serials):
        value = _identifier(serial, "%s delivered serial[%d]" % (label, index))
        if value in seen:
            raise ValueError("%s delivers serial %s twice" % (label, value))
        seen.add(value)
        delivered.append(value)
    screened = []
    seen_rows = set()
    for index, serial in enumerate(screened_serials):
        value = _identifier(serial, "%s screening row[%d]" % (label, index))
        if value in seen_rows:
            raise ValueError("%s screening record holds serial %s twice" % (label, value))
        seen_rows.add(value)
        screened.append(value)
    uncovered = tuple(s for s in delivered if s not in seen_rows)
    foreign = tuple(s for s in screened if s not in seen)
    covered = len(delivered) - len(uncovered)
    findings = []
    if uncovered:
        findings.append(
            "%s delivered %d diodes with no screening row: %s"
            % (label, len(uncovered), ", ".join(uncovered))
        )
    if foreign:
        findings.append(
            "%s screening record holds %d rows for serials the batch never "
            "delivered: %s" % (label, len(foreign), ", ".join(foreign))
        )
    return {
        "delivered_count": len(delivered),
        "covered_count": covered,
        "uncovered_serials": uncovered,
        "foreign_serials": foreign,
        "coverage_fraction": covered / float(len(delivered)),
        "findings": findings,
        "accepted": not findings,
    }


def verify_date_order(manufacture_date, screening_date, delivery_date, label="batch"):
    """Check the batch dates sit in the only order that makes them mean anything.

    Screening that predates the completion of the batch it screened did not
    screen that batch; screening dated after the delivery it released was
    not available when the delivery went out. A same-day pair is allowed:
    the order is not-before, not strictly-after.
    """
    made = parse_package_date(manufacture_date, "%s manufacture_date" % label)
    screened = parse_package_date(screening_date, "%s screening_date" % label)
    delivered = parse_package_date(delivery_date, "%s delivery_date" % label)
    findings = []
    if screened < made:
        findings.append(
            "%s screening is dated %s, before the batch completed on %s, so it "
            "did not screen this batch" % (label, screened, made)
        )
    if delivered < screened:
        findings.append(
            "%s was delivered %s, before its screening record was dated %s, so "
            "the record was not available at delivery" % (label, delivered, screened)
        )
    return {
        "manufacture_date": made,
        "screening_date": screened,
        "delivery_date": delivered,
        "findings": findings,
        "accepted": not findings,
    }


def evaluate_batch_file(batch, governing_approval):
    """Grade one delivered batch's data file against the type-level tier."""
    if not isinstance(batch, dict):
        raise ValueError("batch must be a mapping")
    for key in (
        "batch_id",
        "context",
        "records",
        "delivered_serials",
        "screened_serials",
        "cited_approval_reference",
        "manufacture_date",
        "screening_date",
        "delivery_date",
    ):
        if key not in batch:
            raise ValueError("batch missing required key '%s'" % key)
    batch_id = _identifier(batch["batch_id"], "batch_id")
    label = "batch %s" % batch_id
    owed = resolve_batch_families(batch["context"], label)
    grouped = group_records(batch["records"])
    families = tuple(grade_family(family, grouped, label) for family in owed)
    findings = [f["finding"] for f in families if f["finding"]]

    owed_set = set(owed)
    unowed = tuple(sorted(f for f in grouped if f not in owed_set))
    for family in unowed:
        findings.append(
            "%s submits family %s, which its stated context does not owe"
            % (label, family)
        )

    coverage = reconcile_screening_serials(
        batch["delivered_serials"], batch["screened_serials"], label
    )
    findings.extend(coverage["findings"])

    dates = verify_date_order(
        batch["manufacture_date"],
        batch["screening_date"],
        batch["delivery_date"],
        label,
    )
    findings.extend(dates["findings"])

    cited = batch["cited_approval_reference"]
    citation_ok = False
    if cited is None:
        findings.append(
            "%s cites no type qualification approval, so nothing ties it to the "
            "qualification tier" % label
        )
    else:
        cited = _identifier(cited, "%s cited_approval_reference" % label)
        if governing_approval is None:
            findings.append(
                "%s cites approval %s but the qualification tier has no approved "
                "governing approval statement to match it against" % (label, cited)
            )
        elif cited != governing_approval["reference"]:
            findings.append(
                "%s cites approval %s, which is a real reference but not the "
                "governing one (%s)"
                % (label, cited, governing_approval["reference"])
            )
        else:
            citation_ok = True

    return {
        "batch_id": batch_id,
        "owed_families": owed,
        "families": families,
        "unowed_families": unowed,
        "coverage": coverage,
        "dates": dates,
        "cited_approval_reference": cited,
        "citation_matches_governing": citation_ok,
        "findings": findings,
        "accepted": not findings,
    }


def reconcile_batch_set(declared_batch_ids, submitted_batch_ids):
    """Reconcile the submitted batch files against the declared delivery.

    Both directions. A declared batch with no file is missing; a file for a
    batch the delivery never declares is the package and the delivery
    record contradicting each other, not a bonus.
    """
    if not isinstance(declared_batch_ids, (list, tuple)) or not declared_batch_ids:
        raise ValueError("the delivery must declare at least one batch")
    if not isinstance(submitted_batch_ids, (list, tuple)):
        raise ValueError("submitted batch ids must be a sequence")
    declared = []
    seen = set()
    for index, value in enumerate(declared_batch_ids):
        batch_id = _identifier(value, "declared batch[%d]" % index)
        if batch_id in seen:
            raise ValueError("batch %s is declared twice" % batch_id)
        seen.add(batch_id)
        declared.append(batch_id)
    submitted = [
        _identifier(v, "submitted batch[%d]" % i)
        for i, v in enumerate(submitted_batch_ids)
    ]
    submitted_set = set(submitted)
    missing = tuple(b for b in declared if b not in submitted_set)
    undeclared = tuple(sorted(b for b in submitted_set if b not in seen))
    findings = []
    if missing:
        findings.append(
            "the delivery declares %d batches with no data file: %s"
            % (len(missing), ", ".join(missing))
        )
    if undeclared:
        findings.append(
            "the package submits data files for %d batches the delivery never "
            "declares: %s" % (len(undeclared), ", ".join(undeclared))
        )
    return {
        "declared_batch_ids": tuple(declared),
        "missing_batch_ids": missing,
        "undeclared_batch_ids": undeclared,
        "findings": findings,
        "accepted": not findings,
    }


def evaluate_data_package(spec):
    """Run the clause 12.8 package check over one offered delivery.

    spec keys: package_id, qualification_records, declared_batch_ids,
    batch_files.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "package_id",
        "qualification_records",
        "declared_batch_ids",
        "batch_files",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    package_id = _identifier(spec["package_id"], "package_id")
    tier = evaluate_qualification_tier(spec["qualification_records"])

    batch_files = spec["batch_files"]
    if not isinstance(batch_files, (list, tuple)) or not batch_files:
        raise ValueError("the package must carry at least one batch data file")
    graded = []
    seen = set()
    for batch in batch_files:
        result = evaluate_batch_file(batch, tier["governing_approval"])
        if result["batch_id"] in seen:
            raise ValueError("batch %s has two data files" % result["batch_id"])
        seen.add(result["batch_id"])
        graded.append(result)

    reconciliation = reconcile_batch_set(
        spec["declared_batch_ids"], [b["batch_id"] for b in graded]
    )

    findings = list(tier["findings"])
    for batch in graded:
        findings.extend(batch["findings"])
    findings.extend(reconciliation["findings"])

    delivered_total = sum(b["coverage"]["delivered_count"] for b in graded)
    covered_total = sum(b["coverage"]["covered_count"] for b in graded)
    return {
        "package_id": package_id,
        "qualification_tier": tier,
        "batches": tuple(graded),
        "batch_reconciliation": reconciliation,
        "delivered_serial_total": delivered_total,
        "screened_serial_total": covered_total,
        "package_coverage_fraction": covered_total / float(delivered_total),
        "blocking_batch_ids": tuple(b["batch_id"] for b in graded if not b["accepted"]),
        "findings": findings,
        "verdict": PACKAGE_RELEASABLE if not findings else PACKAGE_HELD,
        "accepted": not findings,
    }
