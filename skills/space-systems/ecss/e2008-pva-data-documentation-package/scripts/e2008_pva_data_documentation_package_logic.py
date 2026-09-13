"""Documentation package delivered with a photovoltaic-assembly coupon.

Anchor: ECSS-E-ST-20-08C clause 5.7 (the data package that accompanies each
coupon, carrying the records behind its qualification approval). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve which record families this particular coupon owes. Most are owed
   always; a few are owed only because something happened - a nonconformance
   was raised, a waiver was granted - and the context flag for each of those
   has to be stated rather than inferred from what was submitted.
2. Validate every submitted record: family, reference, revision, approval
   state and, when approved, the date it was approved.
3. Take the governing record of each family, which is its highest revision,
   and keep the lower revisions visible as superseded rather than as missing.
4. Check each owed family: present at all, at or above the revision the
   coupon's configuration calls for, and carrying an approval rather than a
   draft or an open review.
5. Flag a record whose approval is dated after the coupon left, and flag a
   submitted family the context says should not exist, because both mean the
   package and the story told about it disagree.
"""

import datetime

__all__ = [
    "APPROVAL_STATES",
    "CONDITIONAL_FAMILIES",
    "MANDATORY_FAMILIES",
    "RECORD_FAMILIES",
    "evaluate_package",
    "governing_records",
    "normalize_approval_state",
    "normalize_family",
    "parse_date",
    "required_families",
    "validate_context",
    "validate_record",
]

# The record families a coupon data package is built from. A family whose
# trigger is None is owed by every coupon; the others are owed only when the
# named context flag is true.
RECORD_FAMILIES = {
    "identification-and-traceability": None,
    "parts-and-materials-list": None,
    "manufacturing-process-records": None,
    "inspection-records": None,
    "test-records-and-conditions": None,
    "qualification-approval-statement": None,
    "nonconformance-records": "nonconformances_raised",
    "waiver-and-deviation-records": "waivers_granted",
}

MANDATORY_FAMILIES = tuple(
    family for family, trigger in RECORD_FAMILIES.items() if trigger is None
)
CONDITIONAL_FAMILIES = tuple(
    family for family, trigger in RECORD_FAMILIES.items() if trigger is not None
)

# Where a submitted record stands. Only one of these is an approval.
APPROVAL_STATES = ("approved", "in-review", "draft", "withdrawn")


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


def normalize_family(family):
    """Return a recognized record family, refusing anything else."""
    if not isinstance(family, str):
        raise ValueError("family must be a string, got %r" % (family,))
    cleaned = family.strip().lower()
    if cleaned not in RECORD_FAMILIES:
        raise ValueError(
            "unrecognized record family %r; recognized: %s"
            % (family, ", ".join(sorted(RECORD_FAMILIES)))
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


def validate_context(context):
    """Return the coupon context with every conditional flag stated."""
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping of conditional flags")
    triggers = set(RECORD_FAMILIES[f] for f in CONDITIONAL_FAMILIES)
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


def required_families(context):
    """Return the record families this coupon owes, in catalogue order."""
    resolved = validate_context(context)
    owed = []
    for family, trigger in RECORD_FAMILIES.items():
        if trigger is None or resolved[trigger]:
            owed.append(family)
    return tuple(owed)


def validate_record(record, label="record"):
    """Return one submitted documentation record as a validated entry."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("family", "reference", "revision", "approval_state"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (label, key))
    state = normalize_approval_state(record["approval_state"])
    entry = {
        "family": normalize_family(record["family"]),
        "reference": _identifier(record["reference"], "%s reference" % label),
        "revision": _revision(record["revision"], "%s revision" % label),
        "approval_state": state,
        "approval_date": None,
    }
    if state == "approved":
        if record.get("approval_date") is None:
            raise ValueError(
                "%s is approved but carries no approval_date" % label
            )
        entry["approval_date"] = parse_date(
            record["approval_date"], "%s approval_date" % label
        )
    elif record.get("approval_date") is not None:
        raise ValueError(
            "%s is '%s' yet carries an approval_date" % (label, state)
        )
    return entry


def validate_records(records):
    """Return the validated submitted records, refusing a repeated revision."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of submitted records")
    seen = set()
    out = []
    for index, record in enumerate(records):
        entry = validate_record(record, "records[%d]" % index)
        key = (entry["family"], entry["reference"], entry["revision"])
        if key in seen:
            raise ValueError(
                "record %s revision %d submitted twice"
                % (entry["reference"], entry["revision"])
            )
        seen.add(key)
        out.append(entry)
    return out


def governing_records(records):
    """Return, per family, the highest-revision record and what it superseded."""
    validated = validate_records(records)
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


def evaluate_package(spec):
    """Run the full clause 5.7 acceptance check of one coupon data package.

    spec keys: coupon_id, delivery_date, records, context;
    optional applicable_revisions (family -> minimum revision, default 0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("coupon_id", "delivery_date", "records", "context"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    coupon_id = _identifier(spec["coupon_id"], "coupon_id")
    delivery = parse_date(spec["delivery_date"], "delivery_date")
    owed = required_families(spec["context"])
    governing = governing_records(spec["records"])

    applicable = spec.get("applicable_revisions") or {}
    if not isinstance(applicable, dict):
        raise ValueError("applicable_revisions must be a mapping of family to revision")
    minimums = {}
    for family, revision in applicable.items():
        cleaned = normalize_family(family)
        minimums[cleaned] = _revision(
            revision, "applicable_revisions['%s']" % cleaned
        )

    findings = []
    family_records = []
    for family in owed:
        wanted = minimums.get(family, 0)
        entry = governing.get(family)
        if entry is None:
            findings.append(
                "coupon %s owes '%s' and no record of that family was submitted"
                % (coupon_id, family)
            )
            family_records.append({
                "family": family,
                "present": False,
                "required_revision": wanted,
                "accepted": False,
            })
            continue
        issues = []
        if entry["revision"] < wanted:
            issues.append(
                "'%s' was submitted at revision %d, below the revision %d this "
                "coupon calls for" % (family, entry["revision"], wanted)
            )
        if entry["approval_state"] != "approved":
            issues.append(
                "'%s' is '%s' rather than approved" % (family, entry["approval_state"])
            )
        elif entry["approval_date"] > delivery:
            issues.append(
                "'%s' was approved on %s, after coupon %s was delivered on %s"
                % (family, entry["approval_date"].isoformat(), coupon_id,
                   delivery.isoformat())
            )
        findings.extend(issues)
        family_records.append({
            "family": family,
            "present": True,
            "reference": entry["reference"],
            "revision": entry["revision"],
            "required_revision": wanted,
            "approval_state": entry["approval_state"],
            "superseded_revisions": entry["superseded_revisions"],
            "accepted": not issues,
        })

    unexpected = tuple(family for family in governing if family not in owed)
    for family in unexpected:
        findings.append(
            "'%s' records were submitted although the coupon context says that "
            "family is not owed" % family
        )

    return {
        "coupon_id": coupon_id,
        "delivery_date": delivery,
        "required_families": owed,
        "families": family_records,
        "unexpected_families": unexpected,
        "missing_families": tuple(
            r["family"] for r in family_records if not r["present"]
        ),
        "accepted_family_count": sum(1 for r in family_records if r["accepted"]),
        "findings": findings,
        "accepted": not findings,
    }
