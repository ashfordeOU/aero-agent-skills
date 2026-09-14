"""Supplier data package travelling with a bare solar cell delivery.

Anchor: ECSS-E-ST-20-08C clause 7.7. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The package a bare-cell delivery is released against stands on two tiers,
and the usual way it goes wrong is to walk them as one list of documents.

    qualification tier   the supplier records standing behind the cell
                         type's qualification. Issued once, cited by
                         every lot, governing for the whole campaign
    lot tier             one data file per delivered lot. A lot with no
                         file is not a lot with a thin file: it is a
                         lot whose evidence never arrived

Running them as one tier produces the two defects this check exists to
catch. A package holding every qualification record and one immaculate
lot file passes a family-by-family sweep while three delivered lots have
no paperwork at all, because nothing in a family sweep names the lots
that were supposed to be there. And a bare-cell lot file can carry every
owed family and still not carry the cells: the measured data table is
the only record that descends to the individual cell, so a table holding
forty rows for a lot of four hundred delivered cells looks complete at
family level and is ninety per cent empty at cell level.

So two reconciliations run, and both run in both directions. The lot
files are reconciled against the lots the delivery declares -- a declared
lot with no file is missing, a file for a lot that never shipped is the
package and the delivery record disagreeing. And inside each lot the
measured data rows are reconciled against the cells that lot delivered --
a delivered cell with no row is uncovered, a row for a cell the lot never
held is foreign data.

Within a family the familiar rules hold: a family can hold several
issues, the highest issue governs and the lower ones are superseded
rather than missing; and an approval is a state, so a record sitting in
draft or in review is in the package and is still not evidence.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

__all__ = [
    "APPROVAL_STATES",
    "LOT_DATA_FAMILIES",
    "LOT_FILE_ACCEPTED",
    "LOT_FILE_REJECTED",
    "PACKAGE_RELEASABLE",
    "PACKAGE_WITHHELD",
    "QUALIFICATION_FAMILIES",
    "assess_lot_data_file",
    "conditional_lot_families",
    "evaluate_data_package",
    "governing_records",
    "mandatory_lot_families",
    "normalize_approval_state",
    "normalize_family",
    "parse_date",
    "reconcile_cell_rows",
    "reconcile_lot_files",
    "required_lot_families",
    "resolve_qualification_tier",
    "validate_lot_context",
    "validate_record",
    "validate_records",
]

# Tier one. Issued once for the bare cell type and cited by every lot.
QUALIFICATION_FAMILIES = (
    "bare-cell-qualification-test-report",
    "bare-cell-process-identification-document",
    "bare-cell-qualification-approval-statement",
    "bare-cell-declared-materials-and-processes-list",
)

# Tier two. One data file per delivered lot. A family whose trigger is
# None is owed by every lot; the rest are owed only when the lot context
# says the triggering event happened.
LOT_DATA_FAMILIES = {
    "bare-cell-lot-identification-and-traceability": None,
    "bare-cell-lot-acceptance-test-report": None,
    "bare-cell-measured-electrical-data-table": None,
    "bare-cell-certificate-of-conformity": None,
    "bare-cell-nonconformance-records": "nonconformances_raised",
    "bare-cell-waiver-and-deviation-records": "waivers_granted",
}

_ALL_FAMILIES = tuple(QUALIFICATION_FAMILIES) + tuple(LOT_DATA_FAMILIES)

# Where a submitted record stands. Only one of these is an approval.
APPROVAL_STATES = ("approved", "in-review", "draft", "withdrawn")

_GOVERNING_APPROVAL_FAMILY = "bare-cell-qualification-approval-statement"

LOT_FILE_ACCEPTED = "lot-data-file-accepted"
LOT_FILE_REJECTED = "lot-data-file-rejected"

PACKAGE_RELEASABLE = "data-package-releasable"
PACKAGE_WITHHELD = "data-package-withheld"


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _issue(value, label):
    """Return an issue number as a non-negative integer, refusing a bool."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def parse_date(value, label="date"):
    """Return an ISO calendar date, refusing anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))


def normalize_family(family, allowed=None):
    """Return a recognized record family, refusing anything else."""
    catalogue = _ALL_FAMILIES if allowed is None else tuple(allowed)
    if not isinstance(family, str):
        raise ValueError("family must be a string, got %r" % (family,))
    cleaned = family.strip().lower()
    if cleaned not in catalogue:
        raise ValueError(
            "unrecognized record family %r; recognized: %s"
            % (family, ", ".join(sorted(catalogue)))
        )
    return cleaned


def normalize_approval_state(state):
    """Return a recognized approval state, refusing anything else."""
    if not isinstance(state, str):
        raise ValueError("approval_state must be a string, got %r" % (state,))
    cleaned = state.strip().lower()
    if cleaned not in APPROVAL_STATES:
        raise ValueError(
            "unrecognized approval_state %r; recognized: %s"
            % (state, ", ".join(APPROVAL_STATES))
        )
    return cleaned


def mandatory_lot_families():
    """Return the data families every delivered lot owes."""
    return tuple(f for f, trigger in LOT_DATA_FAMILIES.items() if trigger is None)


def conditional_lot_families():
    """Return the data families owed only because something happened."""
    return tuple(f for f, trigger in LOT_DATA_FAMILIES.items() if trigger is not None)


def validate_lot_context(context):
    """Return the lot context with every conditional flag stated."""
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping of conditional flags")
    triggers = set(LOT_DATA_FAMILIES[f] for f in conditional_lot_families())
    unknown = sorted(set(context) - triggers)
    if unknown:
        raise ValueError("unrecognized context flag(s): %s" % ", ".join(unknown))
    resolved = {}
    for trigger in sorted(triggers):
        if trigger not in context:
            raise ValueError(
                "context missing flag '%s'; an unstated flag is not a false flag"
                % trigger
            )
        if not isinstance(context[trigger], bool):
            raise ValueError(
                "context flag '%s' must be a boolean, got %r"
                % (trigger, context[trigger])
            )
        resolved[trigger] = context[trigger]
    return resolved


def required_lot_families(context):
    """Return the data families this lot owes, in catalogue order."""
    resolved = validate_lot_context(context)
    return tuple(
        family
        for family, trigger in LOT_DATA_FAMILIES.items()
        if trigger is None or resolved[trigger]
    )


def validate_record(record, allowed=None, label="record"):
    """Return one submitted record as a validated entry."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("family", "reference", "issue", "approval_state"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (label, key))
    state = normalize_approval_state(record["approval_state"])
    entry = {
        "family": normalize_family(record["family"], allowed),
        "reference": _identifier(record["reference"], "%s reference" % label),
        "issue": _issue(record["issue"], "%s issue" % label),
        "approval_state": state,
        "approval_date": None,
    }
    if state == "approved":
        if record.get("approval_date") is None:
            raise ValueError("%s is approved but carries no approval_date" % label)
        entry["approval_date"] = parse_date(
            record["approval_date"], "%s approval_date" % label
        )
    elif record.get("approval_date") is not None:
        raise ValueError("%s is '%s' yet carries an approval_date" % (label, state))
    return entry


def validate_records(records, allowed=None, label="records"):
    """Return the validated records, refusing a repeated issue."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("%s must be a sequence of submitted records" % label)
    seen = set()
    out = []
    for index, record in enumerate(records):
        entry = validate_record(record, allowed, "%s[%d]" % (label, index))
        key = (entry["family"], entry["reference"], entry["issue"])
        if key in seen:
            raise ValueError(
                "record %s issue %d submitted twice"
                % (entry["reference"], entry["issue"])
            )
        seen.add(key)
        out.append(entry)
    return out


def governing_records(records, allowed=None, label="records"):
    """Return, per family, the highest-issue record and what it superseded."""
    validated = validate_records(records, allowed, label)
    grouped = {}
    for entry in validated:
        grouped.setdefault(entry["family"], []).append(entry)
    governing = {}
    for family, entries in grouped.items():
        ordered = sorted(entries, key=lambda e: (e["issue"], e["reference"]))
        top = ordered[-1]
        governing[family] = {
            "family": family,
            "reference": top["reference"],
            "issue": top["issue"],
            "approval_state": top["approval_state"],
            "approval_date": top["approval_date"],
            "superseded_issues": tuple(e["issue"] for e in ordered[:-1]),
        }
    return governing


def resolve_qualification_tier(records):
    """Grade the tier every delivered lot cites and name its approval."""
    governing = governing_records(
        records, QUALIFICATION_FAMILIES, "qualification_records"
    )
    findings = []
    families = []
    for family in QUALIFICATION_FAMILIES:
        entry = governing.get(family)
        if entry is None:
            findings.append(
                "the qualification tier owes '%s' and no record of that family "
                "was submitted" % family
            )
            families.append({"family": family, "present": False, "accepted": False})
            continue
        issues = []
        if entry["approval_state"] != "approved":
            issues.append(
                "qualification record '%s' is '%s' rather than approved"
                % (family, entry["approval_state"])
            )
        findings.extend(issues)
        families.append(
            {
                "family": family,
                "present": True,
                "reference": entry["reference"],
                "issue": entry["issue"],
                "approval_state": entry["approval_state"],
                "approval_date": entry["approval_date"],
                "superseded_issues": entry["superseded_issues"],
                "accepted": not issues,
            }
        )

    approval = governing.get(_GOVERNING_APPROVAL_FAMILY)
    if approval is not None and approval["approval_state"] == "approved":
        reference = approval["reference"]
        approval_date = approval["approval_date"]
    else:
        reference = None
        approval_date = None

    return {
        "families": tuple(families),
        "governing_approval_reference": reference,
        "governing_approval_date": approval_date,
        "findings": findings,
        "accepted": not findings,
    }


def reconcile_cell_rows(delivered_cell_ids, data_row_cell_ids, lot_id="lot"):
    """Match the measured data rows against the cells the lot delivered.

    The family sweep cannot see this: the measured data table is the only
    record that descends to the individual cell, so a table can be present,
    approved, at the governing issue and still cover a tenth of the lot.
    """
    if not isinstance(delivered_cell_ids, (list, tuple)) or not delivered_cell_ids:
        raise ValueError(
            "lot %s must declare a non-empty sequence of delivered cell ids" % lot_id
        )
    delivered = []
    for index, cell in enumerate(delivered_cell_ids):
        cleaned = _identifier(cell, "lot %s delivered_cell_ids[%d]" % (lot_id, index))
        if cleaned in delivered:
            raise ValueError("lot %s delivers cell %s twice" % (lot_id, cleaned))
        delivered.append(cleaned)
    if not isinstance(data_row_cell_ids, (list, tuple)):
        raise ValueError("lot %s data rows must be a sequence of cell ids" % lot_id)
    rows = []
    for index, cell in enumerate(data_row_cell_ids):
        cleaned = _identifier(cell, "lot %s data row[%d] cell id" % (lot_id, index))
        if cleaned in rows:
            raise ValueError(
                "lot %s measured data table holds two rows for cell %s"
                % (lot_id, cleaned)
            )
        rows.append(cleaned)
    covered = [c for c in delivered if c in rows]
    uncovered = tuple(c for c in delivered if c not in rows)
    foreign = tuple(c for c in rows if c not in delivered)
    return {
        "lot_id": lot_id,
        "delivered_count": len(delivered),
        "row_count": len(rows),
        "covered_count": len(covered),
        "uncovered_cells": uncovered,
        "foreign_rows": foreign,
        "coverage_fraction": len(covered) / float(len(delivered)),
        "fully_covered": not uncovered and not foreign,
    }


def reconcile_lot_files(declared_lots, submitted_lots):
    """Match the lot data files submitted against the lots declared."""
    if not isinstance(declared_lots, (list, tuple)) or not declared_lots:
        raise ValueError("declared_lots must be a non-empty sequence of lot ids")
    declared = []
    for index, lot in enumerate(declared_lots):
        cleaned = _identifier(lot, "declared_lots[%d]" % index)
        if cleaned in declared:
            raise ValueError("lot %s is declared twice in the delivery" % cleaned)
        declared.append(cleaned)
    if not isinstance(submitted_lots, (list, tuple)):
        raise ValueError("submitted_lots must be a sequence of lot ids")
    submitted = []
    for index, lot in enumerate(submitted_lots):
        cleaned = _identifier(lot, "submitted_lots[%d]" % index)
        if cleaned in submitted:
            raise ValueError("lot %s has two data files in the package" % cleaned)
        submitted.append(cleaned)
    return {
        "declared_lots": tuple(declared),
        "submitted_lots": tuple(submitted),
        "missing_lots": tuple(l for l in declared if l not in submitted),
        "undeclared_lots": tuple(l for l in submitted if l not in declared),
    }


def assess_lot_data_file(lot, tier):
    """Grade one lot's data file against its owed families and its cells.

    lot keys: lot_id, context, records, delivered_cell_ids,
    measured_data_rows; optional cited_approval_reference.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    for key in (
        "lot_id",
        "context",
        "records",
        "delivered_cell_ids",
        "measured_data_rows",
    ):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    if not isinstance(tier, dict):
        raise ValueError("tier must be the resolved qualification tier mapping")
    lot_id = _identifier(lot["lot_id"], "lot_id")
    owed = required_lot_families(lot["context"])
    governing = governing_records(
        lot["records"], tuple(LOT_DATA_FAMILIES), "lot %s records" % lot_id
    )

    findings = []
    families = []
    for family in owed:
        entry = governing.get(family)
        if entry is None:
            findings.append(
                "lot %s owes '%s' and no record of that family was submitted"
                % (lot_id, family)
            )
            families.append({"family": family, "present": False, "accepted": False})
            continue
        problems = []
        if entry["approval_state"] != "approved":
            problems.append(
                "lot %s record '%s' is '%s' rather than approved"
                % (lot_id, family, entry["approval_state"])
            )
        findings.extend(problems)
        families.append(
            {
                "family": family,
                "present": True,
                "reference": entry["reference"],
                "issue": entry["issue"],
                "approval_state": entry["approval_state"],
                "superseded_issues": entry["superseded_issues"],
                "accepted": not problems,
            }
        )

    undeclared_families = tuple(f for f in governing if f not in owed)
    for family in undeclared_families:
        findings.append(
            "lot %s submitted '%s' although its context says that family is not "
            "owed" % (lot_id, family)
        )

    coverage = reconcile_cell_rows(
        lot["delivered_cell_ids"], lot["measured_data_rows"], lot_id
    )
    for cell in coverage["uncovered_cells"]:
        findings.append(
            "lot %s delivered cell %s and the measured data table carries no row "
            "for it" % (lot_id, cell)
        )
    for cell in coverage["foreign_rows"]:
        findings.append(
            "lot %s measured data table carries a row for cell %s, which this lot "
            "never delivered" % (lot_id, cell)
        )

    cited = lot.get("cited_approval_reference")
    governing_reference = tier.get("governing_approval_reference")
    if cited is None:
        findings.append(
            "lot %s cites no qualification approval, so nothing ties its cells to "
            "the type they shipped under" % lot_id
        )
        citation_matches = False
    else:
        cited = _identifier(cited, "cited_approval_reference")
        if governing_reference is None:
            findings.append(
                "lot %s cites approval %s but the package carries no approved "
                "qualification approval statement to match it against"
                % (lot_id, cited)
            )
            citation_matches = False
        elif cited != governing_reference:
            findings.append(
                "lot %s cites approval %s while the governing approval is %s; a "
                "superseded citation is a real reference and still the wrong one"
                % (lot_id, cited, governing_reference)
            )
            citation_matches = False
        else:
            citation_matches = True

    return {
        "lot_id": lot_id,
        "required_families": owed,
        "families": tuple(families),
        "undeclared_families": undeclared_families,
        "missing_families": tuple(f["family"] for f in families if not f["present"]),
        "cell_coverage": coverage,
        "cited_approval_reference": cited,
        "citation_matches_governing": citation_matches,
        "verdict": LOT_FILE_ACCEPTED if not findings else LOT_FILE_REJECTED,
        "findings": findings,
        "accepted": not findings,
    }


def evaluate_data_package(spec):
    """Run the clause 7.7 release check over one supplier data package.

    spec keys: delivery_id, declared_lots, qualification_records, lot_files.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("delivery_id", "declared_lots", "qualification_records", "lot_files"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    delivery_id = _identifier(spec["delivery_id"], "delivery_id")
    tier = resolve_qualification_tier(spec["qualification_records"])

    lot_files = spec["lot_files"]
    if not isinstance(lot_files, (list, tuple)):
        raise ValueError("lot_files must be a sequence of lot data file mappings")
    results = [assess_lot_data_file(lot, tier) for lot in lot_files]
    reconciliation = reconcile_lot_files(
        spec["declared_lots"], [r["lot_id"] for r in results]
    )

    findings = list(tier["findings"])
    for result in results:
        findings.extend(result["findings"])
    for lot in reconciliation["missing_lots"]:
        findings.append(
            "delivery %s declares lot %s and the package carries no data file for "
            "it" % (delivery_id, lot)
        )
    for lot in reconciliation["undeclared_lots"]:
        findings.append(
            "the package carries a data file for lot %s, which delivery %s does "
            "not declare" % (lot, delivery_id)
        )

    delivered = sum(r["cell_coverage"]["delivered_count"] for r in results)
    covered = sum(r["cell_coverage"]["covered_count"] for r in results)
    return {
        "delivery_id": delivery_id,
        "qualification_tier": tier,
        "lots": tuple(results),
        "reconciliation": reconciliation,
        "accepted_lot_count": sum(1 for r in results if r["accepted"]),
        "delivered_cell_count": delivered,
        "covered_cell_count": covered,
        "package_cell_coverage_fraction": (
            covered / float(delivered) if delivered else 0.0
        ),
        "findings": findings,
        "verdict": PACKAGE_RELEASABLE if not findings else PACKAGE_WITHHELD,
        "accepted": not findings,
    }
