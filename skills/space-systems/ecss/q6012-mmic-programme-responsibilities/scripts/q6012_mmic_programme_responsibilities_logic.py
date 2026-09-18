"""Allocating MMIC programme duties between the customer and the supplier.

Anchor: ECSS-Q-ST-60-12C clause 6 (how the duties of a monolithic microwave
circuit programme divide between the two parties, and how that division moves
with the procurement mode). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the procurement mode: a foundry-led development, where the circuit is
   designed and fabricated for this programme, or a catalogue selection, where
   an already developed part is bought.
2. Read the duties that apply in that mode and the party each one defaults to.
3. Read the proposed responsibility matrix and find, in order of severity:
   a non-transferable duty handed to the wrong party, an applicable duty
   nobody owns, a duty two parties both claim, a duty carried over from a mode
   it does not belong to, and an agreed departure with no deviation record.
4. Report the duty coverage, the share each party carries, one verdict naming
   the most severe finding, and every finding behind it.
"""

__all__ = [
    "CUSTOMER",
    "SUPPLIER",
    "PARTIES",
    "MODES",
    "FOUNDRY_LED",
    "CATALOGUE_BASED",
    "DUTY_CATALOGUE",
    "DEFAULT_ALLOCATION_POLICY",
    "STATUS_PRECEDENCE",
    "RESPONSIBILITY_MATRIX_COMPLETE",
    "NON_TRANSFERABLE_DUTY_MISALLOCATED",
    "DUTY_UNASSIGNED",
    "DUTY_ACCOUNTABILITY_CONFLICT",
    "DUTY_NOT_APPLICABLE_TO_MODE",
    "UNRECORDED_RESPONSIBILITY_DEVIATION",
    "validate_mode",
    "validate_party",
    "validate_allocation_policy",
    "applicable_duties",
    "default_owner",
    "is_transferable",
    "validate_assignment_entry",
    "group_assignments",
    "unassigned_duties",
    "duty_coverage",
    "party_share",
    "assess_duty",
    "assess_responsibility_matrix",
]

CUSTOMER = "customer"
SUPPLIER = "supplier"
PARTIES = (CUSTOMER, SUPPLIER)

FOUNDRY_LED = "foundry-led"
CATALOGUE_BASED = "catalogue-based"
MODES = (FOUNDRY_LED, CATALOGUE_BASED)

RESPONSIBILITY_MATRIX_COMPLETE = "responsibility-matrix-complete"
NON_TRANSFERABLE_DUTY_MISALLOCATED = "non-transferable-duty-misallocated"
DUTY_UNASSIGNED = "programme-duty-unassigned"
DUTY_ACCOUNTABILITY_CONFLICT = "duty-accountability-conflict"
DUTY_NOT_APPLICABLE_TO_MODE = "duty-not-applicable-to-mode"
UNRECORDED_RESPONSIBILITY_DEVIATION = "unrecorded-responsibility-deviation"

# Most severe first: a matrix with several defects reports the worst of them.
STATUS_PRECEDENCE = (
    NON_TRANSFERABLE_DUTY_MISALLOCATED,
    DUTY_UNASSIGNED,
    DUTY_ACCOUNTABILITY_CONFLICT,
    DUTY_NOT_APPLICABLE_TO_MODE,
    UNRECORDED_RESPONSIBILITY_DEVIATION,
)

# The programme duties, the party each mode defaults them to, and whether the
# default may be moved by agreement. A duty whose owner is None in a mode does
# not arise in that mode at all: nothing is designed when a catalogue part is
# selected, so no party owns the design of it.
DUTY_CATALOGUE = {
    "mission-requirement-definition": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: CUSTOMER},
        "transferable": False,
    },
    "procurement-specification-issue": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: CUSTOMER},
        "transferable": True,
    },
    "circuit-design": {
        "owner": {FOUNDRY_LED: SUPPLIER, CATALOGUE_BASED: None},
        "transferable": True,
    },
    "design-rule-compliance": {
        "owner": {FOUNDRY_LED: SUPPLIER, CATALOGUE_BASED: None},
        "transferable": False,
    },
    "mask-set-procurement": {
        "owner": {FOUNDRY_LED: SUPPLIER, CATALOGUE_BASED: None},
        "transferable": True,
    },
    "process-qualification": {
        "owner": {FOUNDRY_LED: SUPPLIER, CATALOGUE_BASED: SUPPLIER},
        "transferable": False,
    },
    "evaluation-testing": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: SUPPLIER},
        "transferable": True,
    },
    "screening-and-lot-acceptance": {
        "owner": {FOUNDRY_LED: SUPPLIER, CATALOGUE_BASED: SUPPLIER},
        "transferable": True,
    },
    "radiation-characterization": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: CUSTOMER},
        "transferable": True,
    },
    "part-approval-for-flight": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: CUSTOMER},
        "transferable": False,
    },
    "nonconformance-disposition": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: CUSTOMER},
        "transferable": False,
    },
    "delivery-documentation": {
        "owner": {FOUNDRY_LED: SUPPLIER, CATALOGUE_BASED: SUPPLIER},
        "transferable": True,
    },
    "obsolescence-and-mask-retention": {
        "owner": {FOUNDRY_LED: CUSTOMER, CATALOGUE_BASED: SUPPLIER},
        "transferable": True,
    },
}

DEFAULT_ALLOCATION_POLICY = {
    # Whether a departure from the default owner needs a recorded deviation.
    "require_deviation_record": True,
    # Whether a duty belonging to another mode may sit in the matrix.
    "allow_non_applicable_duties": False,
}


def validate_mode(mode):
    """Return the validated procurement mode."""
    if not isinstance(mode, str):
        raise ValueError("procurement mode must be a string, got %r" % (mode,))
    value = mode.strip()
    if value not in MODES:
        raise ValueError("unknown procurement mode %r" % (mode,))
    return value


def validate_party(party):
    """Return the validated party name."""
    if not isinstance(party, str):
        raise ValueError("party must be a string, got %r" % (party,))
    value = party.strip()
    if value not in PARTIES:
        raise ValueError("unknown party %r" % (party,))
    return value


def validate_allocation_policy(policy=None):
    """Return a complete allocation policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_ALLOCATION_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("allocation policy must be a mapping")
    merged = dict(DEFAULT_ALLOCATION_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_ALLOCATION_POLICY:
            raise ValueError("unknown allocation policy key %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % key)
        merged[key] = value
    return merged


def applicable_duties(mode):
    """Return the duties that arise in this procurement mode, in catalogue order."""
    value = validate_mode(mode)
    return tuple(
        duty for duty, entry in DUTY_CATALOGUE.items() if entry["owner"][value] is not None
    )


def default_owner(duty, mode):
    """Return the party a duty defaults to in this mode."""
    if duty not in DUTY_CATALOGUE:
        raise ValueError("unknown programme duty %r" % (duty,))
    value = validate_mode(mode)
    owner = DUTY_CATALOGUE[duty]["owner"][value]
    if owner is None:
        raise ValueError("duty %r does not arise in the %s mode" % (duty, value))
    return owner


def is_transferable(duty):
    """Return whether a duty's default owner may be changed by agreement."""
    if duty not in DUTY_CATALOGUE:
        raise ValueError("unknown programme duty %r" % (duty,))
    return bool(DUTY_CATALOGUE[duty]["transferable"])


def validate_assignment_entry(entry):
    """Return a validated responsibility-matrix entry."""
    if not isinstance(entry, dict):
        raise ValueError("assignment entry must be a mapping")
    for key in ("duty", "owner"):
        if key not in entry:
            raise ValueError("assignment entry missing required key '%s'" % key)
    duty = entry["duty"]
    if not isinstance(duty, str) or duty.strip() not in DUTY_CATALOGUE:
        raise ValueError("unknown programme duty %r" % (duty,))
    recorded = entry.get("deviation_recorded", False)
    if not isinstance(recorded, bool):
        raise ValueError("deviation_recorded must be a boolean")
    return {
        "duty": duty.strip(),
        "owner": validate_party(entry["owner"]),
        "deviation_recorded": recorded,
    }


def group_assignments(entries):
    """Group validated entries by duty, keeping every distinct owner claimed."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("assignments must be a sequence of entries")
    grouped = {}
    for entry in entries:
        record = validate_assignment_entry(entry)
        bucket = grouped.setdefault(record["duty"], [])
        for existing in bucket:
            if existing["owner"] == record["owner"]:
                existing["deviation_recorded"] = (
                    existing["deviation_recorded"] or record["deviation_recorded"]
                )
                break
        else:
            bucket.append(record)
    return grouped


def unassigned_duties(grouped, mode):
    """Return the applicable duties that no party has taken."""
    if not isinstance(grouped, dict):
        raise ValueError("grouped assignments must be a mapping")
    return tuple(duty for duty in applicable_duties(mode) if duty not in grouped)


def duty_coverage(grouped, mode):
    """Return the fraction of applicable duties that carry an owner."""
    duties = applicable_duties(mode)
    if not duties:
        raise ValueError("no duties are defined for this mode")
    owned = sum(1 for duty in duties if duty in grouped)
    return owned / float(len(duties))


def party_share(grouped, mode, party):
    """Return the fraction of the owned applicable duties one party carries."""
    who = validate_party(party)
    duties = applicable_duties(mode)
    owned = [duty for duty in duties if duty in grouped]
    if not owned:
        return 0.0
    held = 0
    for duty in owned:
        owners = {record["owner"] for record in grouped[duty]}
        if who in owners:
            held += 1
    return held / float(len(owned))


def assess_duty(duty, records, mode, policy=None):
    """Assess one duty's ownership and return its record."""
    rules = validate_allocation_policy(policy)
    value = validate_mode(mode)
    if duty not in DUTY_CATALOGUE:
        raise ValueError("unknown programme duty %r" % (duty,))
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence for duty %r" % (duty,))
    statuses = []
    findings = []
    expected = DUTY_CATALOGUE[duty]["owner"][value]
    owners = [record["owner"] for record in records]
    if expected is None:
        if not rules["allow_non_applicable_duties"]:
            statuses.append(DUTY_NOT_APPLICABLE_TO_MODE)
            findings.append(
                "duty %s does not arise in a %s procurement, yet it is allocated to %s"
                % (duty, value, ", ".join(sorted(set(owners))))
            )
        return {
            "duty": duty,
            "mode": value,
            "expected_owner": None,
            "owners": tuple(owners),
            "statuses": statuses,
            "findings": findings,
            "acceptable": not statuses,
        }
    if len(set(owners)) > 1:
        statuses.append(DUTY_ACCOUNTABILITY_CONFLICT)
        findings.append(
            "duty %s is held accountable on both sides (%s); one party carries it"
            % (duty, ", ".join(sorted(set(owners))))
        )
    for record in records:
        if record["owner"] == expected:
            continue
        if not is_transferable(duty):
            statuses.append(NON_TRANSFERABLE_DUTY_MISALLOCATED)
            findings.append(
                "duty %s cannot be moved off the %s in a %s procurement, it is allocated to the %s"
                % (duty, expected, value, record["owner"])
            )
        elif rules["require_deviation_record"] and not record["deviation_recorded"]:
            statuses.append(UNRECORDED_RESPONSIBILITY_DEVIATION)
            findings.append(
                "duty %s defaults to the %s in a %s procurement and sits with the %s "
                "with no recorded deviation" % (duty, expected, value, record["owner"])
            )
    return {
        "duty": duty,
        "mode": value,
        "expected_owner": expected,
        "owners": tuple(owners),
        "statuses": statuses,
        "findings": findings,
        "acceptable": not statuses,
    }


def _worst_status(statuses):
    for status in STATUS_PRECEDENCE:
        if status in statuses:
            return status
    return RESPONSIBILITY_MATRIX_COMPLETE


def assess_responsibility_matrix(spec):
    """Run the full clause 6 responsibility allocation review.

    spec keys: mode, assignments (sequence of {duty, owner, deviation_recorded}),
    optional policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mode", "assignments"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    mode = validate_mode(spec["mode"])
    rules = validate_allocation_policy(spec.get("policy"))
    grouped = group_assignments(spec["assignments"])
    duty_records = [
        assess_duty(duty, records, mode, rules) for duty, records in sorted(grouped.items())
    ]
    statuses = []
    findings = []
    for record in duty_records:
        statuses.extend(record["statuses"])
        findings.extend(record["findings"])
    missing = unassigned_duties(grouped, mode)
    for duty in missing:
        statuses.append(DUTY_UNASSIGNED)
        findings.append(
            "duty %s applies to a %s procurement and no party has taken it "
            "(it defaults to the %s)" % (duty, mode, default_owner(duty, mode))
        )
    verdict = _worst_status(statuses)
    return {
        "mode": mode,
        "duties": duty_records,
        "unassigned": missing,
        "duty_coverage": duty_coverage(grouped, mode),
        "customer_share": party_share(grouped, mode, CUSTOMER),
        "supplier_share": party_share(grouped, mode, SUPPLIER),
        "verdict": verdict,
        "findings": findings,
        "complete": verdict == RESPONSIBILITY_MATRIX_COMPLETE,
    }
