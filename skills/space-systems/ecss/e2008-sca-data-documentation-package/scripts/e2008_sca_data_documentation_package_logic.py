"""Data documentation package for delivered solar cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.6. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The package this clause asks for stands on two tiers, and the usual way
it goes wrong is to run them as one.

    qualification tier   the records behind the approval the cell
                         assembly type holds. Submitted once, cited by
                         every lot, and governing for the campaign
    lot tier             the records a single delivery lot owes. One
                         set per lot that left, and a lot with no set
                         is not a lot with a thin set -- it is absent

Running them as one tier produces the two defects the check exists to
catch. A package holding the qualification records and one immaculate
lot file passes a family-by-family sweep while three delivered lots have
no paperwork at all, because nothing names the lots that were supposed
to be there. And a lot file citing a qualification approval that has
since been superseded looks complete, because the reference it carries
is a real reference to a real record.

So the lot set is reconciled against the lots the delivery declares,
both ways: a declared lot with no file is missing, and a submitted file
for a lot that never shipped is a contradiction rather than a bonus.

Two rules cross the tiers. Every lot cites the governing qualification
approval, and a lot citing a superseded or withdrawn one is a finding.
And a lot whose manufacture closed before the qualification approval was
signed was built against an approval that did not yet exist, which is a
different defect from citing the wrong one.

Within a tier the familiar rules hold: a family can hold several
revisions and the highest governs, the lower ones being superseded
rather than missing; and an approval is a state, so a record sitting in
draft or in review is in the package and is still not evidence.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

__all__ = [
    "APPROVAL_STATES",
    "LOT_ACCEPTED",
    "LOT_FAMILIES",
    "LOT_REJECTED",
    "PACKAGE_ACCEPTED",
    "PACKAGE_REJECTED",
    "QUALIFICATION_FAMILIES",
    "assess_lot_file",
    "conditional_lot_families",
    "evaluate_documentation_package",
    "governing_records",
    "mandatory_lot_families",
    "normalize_approval_state",
    "normalize_family",
    "parse_date",
    "reconcile_lot_files",
    "required_lot_families",
    "resolve_qualification_tier",
    "validate_lot_context",
    "validate_record",
    "validate_records",
]

# Tier one. Submitted once for the cell assembly type and cited by every
# delivery lot that leaves under it.
QUALIFICATION_FAMILIES = (
    "qualification-test-report",
    "qualification-approval-statement",
    "process-identification-document",
    "qualified-parts-and-materials-list",
)

# Tier two. One set per delivery lot. A family whose trigger is None is
# owed by every lot; the others are owed only when the named lot context
# flag is true.
LOT_FAMILIES = {
    "lot-identification-and-traceability": None,
    "lot-acceptance-test-report": None,
    "lot-inspection-report": None,
    "certificate-of-conformity": None,
    "nonconformance-records": "nonconformances_raised",
    "waiver-and-deviation-records": "waivers_granted",
}

_ALL_FAMILIES = tuple(QUALIFICATION_FAMILIES) + tuple(LOT_FAMILIES)

# Where a submitted record stands. Only one of these is an approval.
APPROVAL_STATES = ("approved", "in-review", "draft", "withdrawn")

_GOVERNING_APPROVAL_FAMILY = "qualification-approval-statement"

LOT_ACCEPTED = "lot-file-accepted"
LOT_REJECTED = "lot-file-rejected"

PACKAGE_ACCEPTED = "package-accepted"
PACKAGE_REJECTED = "package-rejected"


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _revision(value, label):
    """Return a revision as a non-negative integer, refusing a float or a bool."""
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
    """Return the lot families every delivery lot owes."""
    return tuple(f for f, trigger in LOT_FAMILIES.items() if trigger is None)


def conditional_lot_families():
    """Return the lot families owed only because something happened."""
    return tuple(f for f, trigger in LOT_FAMILIES.items() if trigger is not None)


def validate_lot_context(context):
    """Return the lot context with every conditional flag stated."""
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping of conditional flags")
    triggers = set(LOT_FAMILIES[f] for f in conditional_lot_families())
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
    """Return the families this lot owes, in catalogue order."""
    resolved = validate_lot_context(context)
    return tuple(
        family
        for family, trigger in LOT_FAMILIES.items()
        if trigger is None or resolved[trigger]
    )


def validate_record(record, allowed=None, label="record"):
    """Return one submitted record as a validated entry."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("family", "reference", "revision", "approval_state"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (label, key))
    state = normalize_approval_state(record["approval_state"])
    entry = {
        "family": normalize_family(record["family"], allowed),
        "reference": _identifier(record["reference"], "%s reference" % label),
        "revision": _revision(record["revision"], "%s revision" % label),
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
    """Return the validated records, refusing a repeated revision."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("%s must be a sequence of submitted records" % label)
    seen = set()
    out = []
    for index, record in enumerate(records):
        entry = validate_record(record, allowed, "%s[%d]" % (label, index))
        key = (entry["family"], entry["reference"], entry["revision"])
        if key in seen:
            raise ValueError(
                "record %s revision %d submitted twice"
                % (entry["reference"], entry["revision"])
            )
        seen.add(key)
        out.append(entry)
    return out


def governing_records(records, allowed=None, label="records"):
    """Return, per family, the highest-revision record and what it superseded."""
    validated = validate_records(records, allowed, label)
    grouped = {}
    for entry in validated:
        grouped.setdefault(entry["family"], []).append(entry)
    governing = {}
    for family, entries in grouped.items():
        ordered = sorted(entries, key=lambda e: (e["revision"], e["reference"]))
        top = ordered[-1]
        governing[family] = {
            "family": family,
            "reference": top["reference"],
            "revision": top["revision"],
            "approval_state": top["approval_state"],
            "approval_date": top["approval_date"],
            "superseded_revisions": tuple(e["revision"] for e in ordered[:-1]),
        }
    return governing


def resolve_qualification_tier(records):
    """Grade the tier the whole campaign rests on and name its approval."""
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
                "revision": entry["revision"],
                "approval_state": entry["approval_state"],
                "approval_date": entry["approval_date"],
                "superseded_revisions": entry["superseded_revisions"],
                "accepted": not issues,
            }
        )

    approval = governing.get(_GOVERNING_APPROVAL_FAMILY)
    if approval is not None and approval["approval_state"] == "approved":
        governing_reference = approval["reference"]
        governing_revision = approval["revision"]
        approval_date = approval["approval_date"]
    else:
        governing_reference = None
        governing_revision = None
        approval_date = None

    return {
        "families": tuple(families),
        "governing_approval_reference": governing_reference,
        "governing_approval_revision": governing_revision,
        "governing_approval_date": approval_date,
        "findings": findings,
        "accepted": not findings,
    }


def reconcile_lot_files(declared_lots, submitted_lots):
    """Match the lot files submitted against the lots the delivery declares."""
    if not isinstance(declared_lots, (list, tuple)) or not declared_lots:
        raise ValueError("declared_lots must be a non-empty sequence of lot ids")
    declared = []
    for index, lot in enumerate(declared_lots):
        cleaned = _identifier(lot, "declared_lots[%d]" % index)
        if cleaned in declared:
            raise ValueError("lot %s is declared twice in the delivery" % cleaned)
        declared.append(cleaned)
    submitted = []
    for index, lot in enumerate(submitted_lots):
        cleaned = _identifier(lot, "submitted_lots[%d]" % index)
        if cleaned in submitted:
            raise ValueError("lot %s has two files in the package" % cleaned)
        submitted.append(cleaned)
    return {
        "declared_lots": tuple(declared),
        "submitted_lots": tuple(submitted),
        "missing_lots": tuple(l for l in declared if l not in submitted),
        "unexpected_lots": tuple(l for l in submitted if l not in declared),
    }


def assess_lot_file(lot, tier):
    """Grade one delivery lot's file against its owed families and the tier.

    lot keys: lot_id, context, records; optional manufacture_completed
    and cited_approval_reference.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    for key in ("lot_id", "context", "records"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    if not isinstance(tier, dict):
        raise ValueError("tier must be the resolved qualification tier mapping")
    lot_id = _identifier(lot["lot_id"], "lot_id")
    owed = required_lot_families(lot["context"])
    governing = governing_records(
        lot["records"], tuple(LOT_FAMILIES), "lot %s records" % lot_id
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
        issues = []
        if entry["approval_state"] != "approved":
            issues.append(
                "lot %s record '%s' is '%s' rather than approved"
                % (lot_id, family, entry["approval_state"])
            )
        findings.extend(issues)
        families.append(
            {
                "family": family,
                "present": True,
                "reference": entry["reference"],
                "revision": entry["revision"],
                "approval_state": entry["approval_state"],
                "superseded_revisions": entry["superseded_revisions"],
                "accepted": not issues,
            }
        )

    unexpected = tuple(family for family in governing if family not in owed)
    for family in unexpected:
        findings.append(
            "lot %s submitted '%s' although its context says that family is not "
            "owed" % (lot_id, family)
        )

    cited = lot.get("cited_approval_reference")
    governing_reference = tier.get("governing_approval_reference")
    if cited is None:
        findings.append(
            "lot %s cites no qualification approval, so nothing ties it to the "
            "tier it shipped under" % lot_id
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
                "superseded citation is not a missing one but it is still wrong"
                % (lot_id, cited, governing_reference)
            )
            citation_matches = False
        else:
            citation_matches = True

    manufacture = lot.get("manufacture_completed")
    built_before_approval = None
    if manufacture is not None:
        manufacture = parse_date(manufacture, "lot %s manufacture_completed" % lot_id)
        approval_date = tier.get("governing_approval_date")
        if approval_date is not None:
            built_before_approval = manufacture < approval_date
            if built_before_approval:
                findings.append(
                    "lot %s closed manufacture on %s, before the qualification "
                    "approval of %s was signed"
                    % (lot_id, manufacture.isoformat(), approval_date.isoformat())
                )

    return {
        "lot_id": lot_id,
        "required_families": owed,
        "families": tuple(families),
        "unexpected_families": unexpected,
        "missing_families": tuple(
            f["family"] for f in families if not f["present"]
        ),
        "cited_approval_reference": cited,
        "citation_matches_governing": citation_matches,
        "manufacture_completed": manufacture,
        "built_before_approval": built_before_approval,
        "verdict": LOT_ACCEPTED if not findings else LOT_REJECTED,
        "findings": findings,
        "accepted": not findings,
    }


def evaluate_documentation_package(spec):
    """Run the full clause 6.6 acceptance check of one documentation package.

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
        raise ValueError("lot_files must be a sequence of lot file mappings")
    results = [assess_lot_file(lot, tier) for lot in lot_files]
    reconciliation = reconcile_lot_files(
        spec["declared_lots"], [r["lot_id"] for r in results]
    )

    findings = list(tier["findings"])
    for result in results:
        findings.extend(result["findings"])
    for lot in reconciliation["missing_lots"]:
        findings.append(
            "delivery %s declares lot %s and the package carries no file for it"
            % (delivery_id, lot)
        )
    for lot in reconciliation["unexpected_lots"]:
        findings.append(
            "the package carries a file for lot %s, which delivery %s does not "
            "declare" % (lot, delivery_id)
        )

    return {
        "delivery_id": delivery_id,
        "qualification_tier": tier,
        "lots": tuple(results),
        "reconciliation": reconciliation,
        "accepted_lot_count": sum(1 for r in results if r["accepted"]),
        "findings": findings,
        "verdict": PACKAGE_ACCEPTED if not findings else PACKAGE_REJECTED,
        "accepted": not findings,
    }
