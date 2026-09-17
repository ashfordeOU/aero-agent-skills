#!/usr/bin/env python3
"""Structure and required entries of a declared components list.

Anchor: ECSS-Q-ST-60-13C Annex B, the data item fixing how the declared
components list of a commercial-parts programme is built and what every
line of it has to carry. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

The list is the only place where the project, the customer and the
supplier look at the same part. It is therefore graded line by line, and
four things follow.

A line that cannot be traced is not a declaration. A part identifier, a
manufacturer, a quality level, a procurement route, radiation evidence
and an application reference are what let a reader take the line back to
a purchase and forward to a circuit; a line missing any of them is
incomplete however confident its approval column looks.

A part number declared twice under different data is worse than a part
number declared once badly. Two lines carrying the same identifier but a
different manufacturer or quality level mean two different parts are
being bought under one name, and no later audit can separate them.

Approval state is a grouping, not a score. Approved, conditional,
pending and rejected lines are counted apart so that a list which is
ninety per cent complete and entirely pending is not read as ninety per
cent done.

Radiation evidence is not optional for a commercial part. A part with no
evidence reference in a radiation environment is the risk the whole
standard exists to manage, so it stops the list rather than lowering a
percentage.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_IDENTIFIER = "part_identifier"
MANUFACTURER = "manufacturer"
QUALITY_LEVEL = "quality_level"
PROCUREMENT_ROUTE = "procurement_route"
RADIATION_EVIDENCE_REFERENCE = "radiation_evidence_reference"
APPLICATION_REFERENCE = "application_reference"

REQUIRED_ENTRY_FIELDS = (
    PART_IDENTIFIER,
    MANUFACTURER,
    QUALITY_LEVEL,
    PROCUREMENT_ROUTE,
    RADIATION_EVIDENCE_REFERENCE,
    APPLICATION_REFERENCE,
)

SPACE_QUALIFIED = "space-qualified"
AUTOMOTIVE_GRADE = "automotive-grade"
INDUSTRIAL_GRADE = "industrial-grade"
COMMERCIAL_GRADE = "commercial-grade"

RECOGNISED_QUALITY_LEVELS = (
    SPACE_QUALIFIED,
    AUTOMOTIVE_GRADE,
    INDUSTRIAL_GRADE,
    COMMERCIAL_GRADE,
)

MANUFACTURER_DIRECT = "manufacturer-direct"
FRANCHISED_DISTRIBUTOR = "franchised-distributor"
INDEPENDENT_BROKER = "independent-broker"

RECOGNISED_PROCUREMENT_ROUTES = (
    MANUFACTURER_DIRECT,
    FRANCHISED_DISTRIBUTOR,
    INDEPENDENT_BROKER,
)

APPROVED = "approved"
CONDITIONALLY_APPROVED = "conditionally-approved"
PENDING = "pending"
REJECTED = "rejected"

RECOGNISED_APPROVAL_STATES = (
    APPROVED,
    CONDITIONALLY_APPROVED,
    PENDING,
    REJECTED,
)

LIST_NOT_ESTABLISHED = "declared-components-list-not-established"
ENTRY_COMPLETENESS_SHORT = "declared-components-list-entry-completeness-short"
DUPLICATE_PART_CONFLICT = "declared-components-list-duplicate-part-conflict"
RADIATION_EVIDENCE_MISSING = "declared-components-list-radiation-evidence-missing"
BROKER_ROUTE_UNJUSTIFIED = "declared-components-list-broker-route-unjustified"
APPROVAL_STATE_OUTSTANDING = "declared-components-list-approval-state-outstanding"
LIST_SUBMITTABLE = "declared-components-list-satisfies-the-data-item"

DEFAULT_LIST_DRD_POLICY = {
    "min_entry_completeness": 1.0,
    "max_pending_share": 0.0,
    "allow_rejected_entries": False,
    "require_radiation_evidence": True,
    "require_broker_justification": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_list_drd_policy(policy):
    """Check the data-item policy the list is graded against is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_entry_completeness", policy.get("min_entry_completeness"))
    _require_fraction("max_pending_share", policy.get("max_pending_share"))
    _require_flag("allow_rejected_entries", policy.get("allow_rejected_entries"))
    _require_flag(
        "require_radiation_evidence", policy.get("require_radiation_evidence")
    )
    _require_flag(
        "require_broker_justification", policy.get("require_broker_justification")
    )
    return policy


def validate_list_identity(declared_list):
    """Check the list can be referred to and its issue read."""
    if not isinstance(declared_list, dict):
        raise ValueError("declared list must be a mapping, got %r" % (declared_list,))
    return {
        "list_reference": _require_label(
            "list_reference", declared_list.get("list_reference")
        ),
        "issue": _require_label("issue", declared_list.get("issue")),
    }


def validate_entry(entry):
    """Read one declared line and the controlled values it carries."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    record = {}
    for field in REQUIRED_ENTRY_FIELDS:
        record[field] = _require_label(field, entry.get(field, ""))
    if record[QUALITY_LEVEL] and record[QUALITY_LEVEL] not in RECOGNISED_QUALITY_LEVELS:
        raise ValueError(
            "unrecognised quality level %r; the data item fixes the grades"
            % record[QUALITY_LEVEL]
        )
    if (
        record[PROCUREMENT_ROUTE]
        and record[PROCUREMENT_ROUTE] not in RECOGNISED_PROCUREMENT_ROUTES
    ):
        raise ValueError(
            "unrecognised procurement route %r; the data item fixes the routes"
            % record[PROCUREMENT_ROUTE]
        )
    state = _require_label("approval_state", entry.get("approval_state"))
    if state not in RECOGNISED_APPROVAL_STATES:
        raise ValueError(
            "unrecognised approval state %r; the state names are fixed" % state
        )
    record["approval_state"] = state
    record["radiation_environment"] = _require_flag(
        "radiation_environment", entry.get("radiation_environment", True)
    )
    record["broker_justification"] = _require_label(
        "broker_justification", entry.get("broker_justification", "")
    )
    return record


def validate_entries(entries):
    """Read every declared line of the list."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of entry records")
    return tuple(validate_entry(entry) for entry in entries)


def missing_fields(entry):
    """Required fields of one line that are blank."""
    record = validate_entry(entry)
    return tuple(field for field in REQUIRED_ENTRY_FIELDS if not record[field])


def entry_is_complete(entry):
    """True when a line carries every field the data item requires."""
    return not missing_fields(entry)


def entry_completeness(entries):
    """Share of the declared lines carrying every required field."""
    checked = validate_entries(entries)
    if not checked:
        return 0.0
    complete = sum(1 for record in checked if entry_is_complete(record))
    return complete / float(len(checked))


def incomplete_entries(entries):
    """Line identifiers, or their position, for lines missing a field."""
    checked = validate_entries(entries)
    incomplete = []
    for index, record in enumerate(checked):
        if not entry_is_complete(record):
            incomplete.append(record[PART_IDENTIFIER] or "line %d" % (index + 1))
    return tuple(incomplete)


def conflicting_part_identifiers(entries):
    """Part identifiers declared twice under a different part."""
    checked = validate_entries(entries)
    seen = {}
    conflicting = []
    for record in checked:
        identifier = record[PART_IDENTIFIER]
        if not identifier:
            continue
        signature = (record[MANUFACTURER], record[QUALITY_LEVEL])
        if identifier in seen:
            if seen[identifier] != signature and identifier not in conflicting:
                conflicting.append(identifier)
        else:
            seen[identifier] = signature
    return tuple(conflicting)


def entries_grouped_by_approval_state(entries):
    """Group the declared lines by the approval state each carries."""
    checked = validate_entries(entries)
    grouped = {state: [] for state in RECOGNISED_APPROVAL_STATES}
    for index, record in enumerate(checked):
        label = record[PART_IDENTIFIER] or "line %d" % (index + 1)
        grouped[record["approval_state"]].append(label)
    return {state: tuple(names) for state, names in grouped.items()}


def pending_share(entries):
    """Share of the declared lines still waiting on an approval decision."""
    checked = validate_entries(entries)
    if not checked:
        return 0.0
    grouped = entries_grouped_by_approval_state(checked)
    return len(grouped[PENDING]) / float(len(checked))


def entries_without_radiation_evidence(entries):
    """Lines sitting in a radiation environment with no evidence reference."""
    checked = validate_entries(entries)
    exposed = []
    for index, record in enumerate(checked):
        if not record["radiation_environment"]:
            continue
        if not record[RADIATION_EVIDENCE_REFERENCE]:
            exposed.append(record[PART_IDENTIFIER] or "line %d" % (index + 1))
    return tuple(exposed)


def unjustified_broker_entries(entries):
    """Lines bought through an independent broker with no justification."""
    checked = validate_entries(entries)
    unjustified = []
    for index, record in enumerate(checked):
        if record[PROCUREMENT_ROUTE] != INDEPENDENT_BROKER:
            continue
        if not record["broker_justification"]:
            unjustified.append(record[PART_IDENTIFIER] or "line %d" % (index + 1))
    return tuple(unjustified)


def assess_declared_components_list_drd(case):
    """Grade a declared components list against its Annex B data item."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_list_drd_policy(case.get("policy") or DEFAULT_LIST_DRD_POLICY)

    findings = []
    advisories = []
    result = {
        "list_reference": None,
        "issue": None,
        "entry_count": 0,
        "entry_completeness": 0.0,
        "incomplete_entries": (),
        "conflicting_part_identifiers": (),
        "entries_by_approval_state": {},
        "pending_share": 0.0,
        "entries_without_radiation_evidence": (),
        "unjustified_broker_entries": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    declared_list = case.get("declared_list")
    if declared_list is None:
        findings.append(
            "no declared components list is submitted, so nothing states which "
            "commercial parts the design intends to use"
        )
        result["verdict"] = LIST_NOT_ESTABLISHED
        return result

    identity = validate_list_identity(declared_list)
    result["list_reference"] = identity["list_reference"]
    result["issue"] = identity["issue"]
    if not identity["list_reference"] or not identity["issue"]:
        findings.append(
            "the list carries no reference or no issue label, so no reviewer "
            "can say which revision was assessed"
        )
        result["verdict"] = LIST_NOT_ESTABLISHED
        return result

    entries = declared_list.get("entries")
    if entries is None:
        raise ValueError("the list declares no entries sequence to assess")
    checked = validate_entries(entries)
    if not checked:
        findings.append(
            "the list carries no entries, so it declares nothing to procure"
        )
        result["verdict"] = LIST_NOT_ESTABLISHED
        return result

    completeness = entry_completeness(checked)
    incomplete = incomplete_entries(checked)
    conflicting = conflicting_part_identifiers(checked)
    grouped = entries_grouped_by_approval_state(checked)
    pending = pending_share(checked)
    exposed = entries_without_radiation_evidence(checked)
    unjustified = unjustified_broker_entries(checked)

    result["entry_count"] = len(checked)
    result["entry_completeness"] = completeness
    result["incomplete_entries"] = incomplete
    result["conflicting_part_identifiers"] = conflicting
    result["entries_by_approval_state"] = grouped
    result["pending_share"] = pending
    result["entries_without_radiation_evidence"] = exposed
    result["unjustified_broker_entries"] = unjustified

    for label in incomplete:
        findings.append("entry %s is missing a field the data item requires" % label)
    for identifier in conflicting:
        findings.append(
            "part identifier %s is declared twice under a different "
            "manufacturer or grade" % identifier
        )
    if grouped[CONDITIONALLY_APPROVED]:
        advisories.append(
            "%d entry(s) are approved subject to a condition that has to be "
            "closed before flight build" % len(grouped[CONDITIONALLY_APPROVED])
        )

    if not _at_least(completeness, float(policy["min_entry_completeness"])):
        findings.append(
            "entry completeness is %.3g per cent against the %.3g per cent the "
            "data item demands"
            % (completeness * 100.0, float(policy["min_entry_completeness"]) * 100.0)
        )
        result["verdict"] = ENTRY_COMPLETENESS_SHORT
        return result

    if conflicting:
        result["verdict"] = DUPLICATE_PART_CONFLICT
        return result

    if policy["require_radiation_evidence"] and exposed:
        findings.append(
            "%d entry(s) sit in a radiation environment with no evidence "
            "reference: %s" % (len(exposed), ", ".join(exposed))
        )
        result["verdict"] = RADIATION_EVIDENCE_MISSING
        return result

    if policy["require_broker_justification"] and unjustified:
        findings.append(
            "%d entry(s) are bought through an independent broker with no "
            "justification recorded: %s" % (len(unjustified), ", ".join(unjustified))
        )
        result["verdict"] = BROKER_ROUTE_UNJUSTIFIED
        return result

    if grouped[REJECTED] and not policy["allow_rejected_entries"]:
        findings.append(
            "the list still carries rejected entries: %s"
            % ", ".join(grouped[REJECTED])
        )
        result["verdict"] = APPROVAL_STATE_OUTSTANDING
        return result

    if not _at_most(pending, float(policy["max_pending_share"])):
        findings.append(
            "%.3g per cent of the entries are still pending against the %.3g "
            "per cent the data item allows"
            % (pending * 100.0, float(policy["max_pending_share"]) * 100.0)
        )
        result["verdict"] = APPROVAL_STATE_OUTSTANDING
        return result

    result["verdict"] = LIST_SUBMITTABLE
    return result
