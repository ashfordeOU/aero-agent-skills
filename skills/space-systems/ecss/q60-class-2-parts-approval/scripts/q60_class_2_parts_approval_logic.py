"""Justification, documents and gates controlling Class 2 part approval.

Anchor: ECSS-Q-ST-60C clause 5.2.4 (the justification record, the approval
documents and the project gates every part proposed for Class 2 flight use
has to clear before it may be built into flight hardware).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Approval is per part. A supplier approved before carries no approval for a
  part number nobody ever submitted, so a proposed part with no approval
  record at all is the first thing the check looks for.
* The justification record is what the approval is granted against. It has to
  say what the part does, why this assurance class is adequate for that use,
  what evaluation or qualification stands behind it, what derating and
  worst-case work covers it, and what is actually being bought. An absent
  field is named as a gap in its own right.
* The approval documents are a separate set from the justification. A complete
  justification inside an incomplete document set is still not an approval
  anybody can audit later.
* Approval has to exist by the gate that governs the part, and which gate
  governs comes from how the part is procured. An approval granted after its
  governing gate is late even when it is otherwise perfect, because the
  decisions it was supposed to inform were already taken.
* An approval outside its validity window is not an approval. A conditional
  approval releases nothing until every condition carries a closure record.
"""

from __future__ import annotations

import math

# What the justification record has to say before an approval means anything.
REQUIRED_JUSTIFICATION_FIELDS = (
    "application-and-circuit-function",
    "reason-this-assurance-class-is-adequate",
    "evaluation-or-qualification-reference",
    "derating-and-worst-case-analysis-reference",
    "procurement-specification-reference",
)

# The documents the approval itself is carried on.
REQUIRED_APPROVAL_DOCUMENTS = (
    "declared-components-list-entry",
    "part-approval-request",
    "evaluation-summary-report",
    "open-nonconformance-statement",
)

# Project gates in the order they occur.
PROJECT_GATES = (
    "preliminary-design-review",
    "critical-design-review",
    "qualification-review",
    "flight-acceptance-review",
)

GATE_ORDER = {gate: index for index, gate in enumerate(PROJECT_GATES)}

# The gate a part's approval has to exist by, read from how it is procured.
GOVERNING_GATE = {
    "long-lead-procurement": "preliminary-design-review",
    "standard-catalogue-procurement": "critical-design-review",
    "late-substitution": "qualification-review",
}

PROCUREMENT_ROLES = tuple(sorted(GOVERNING_GATE))

# The assurance category this leaf releases parts for.
TARGET_CATEGORY = "class-2"

# An approval older than this is outside its validity window.
APPROVAL_VALIDITY_MONTHS = 24.0

# Ages are declared quantities; a case meant to sit on the window edge can
# land a few units in the last place away from it.
VALIDITY_TOLERANCE = 1e-9

PART_STATUSES = (
    "class-2-part-released-for-flight",
    "class-2-part-conditionally-approved",
    "class-2-part-approval-incomplete",
    "class-2-part-not-approved",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _label(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _name_set(raw, allowed, label):
    """Validate a declared collection of names drawn from a closed set."""
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError(
            "%s must be a list or tuple of names, got %r" % (label, raw)
        )
    names = []
    for name in raw:
        if name not in allowed:
            raise ValueError(
                "unknown %s %r (known: %s)" % (label, name, ", ".join(allowed))
            )
        if name not in names:
            names.append(name)
    return tuple(names)


def governing_gate(procurement_role):
    """Gate a part's approval has to exist by, from how it is procured."""
    if procurement_role not in GOVERNING_GATE:
        raise ValueError(
            "unknown procurement_role %r (known: %s)"
            % (procurement_role, ", ".join(PROCUREMENT_ROLES))
        )
    return GOVERNING_GATE[procurement_role]


def gate_index(gate):
    """Position of a gate in the project sequence."""
    if gate not in GATE_ORDER:
        raise ValueError(
            "unknown project gate %r (known: %s)" % (gate, ", ".join(PROJECT_GATES))
        )
    return GATE_ORDER[gate]


def approval_is_timely(granted_at_gate, procurement_role):
    """True when the approval existed by the gate that governs the part."""
    return gate_index(granted_at_gate) <= gate_index(governing_gate(procurement_role))


def missing_justification_fields(declared_fields):
    """Justification fields the record never supplied."""
    present = _name_set(
        declared_fields, REQUIRED_JUSTIFICATION_FIELDS, "justification field"
    )
    return tuple(
        field for field in REQUIRED_JUSTIFICATION_FIELDS if field not in present
    )


def missing_approval_documents(declared_documents):
    """Approval documents the submission never carried."""
    present = _name_set(
        declared_documents, REQUIRED_APPROVAL_DOCUMENTS, "approval document"
    )
    return tuple(
        document
        for document in REQUIRED_APPROVAL_DOCUMENTS
        if document not in present
    )


def normalize_conditions(conditions):
    """Validate the conditions attached to a conditional approval."""
    if isinstance(conditions, str) or not isinstance(conditions, (list, tuple)):
        raise ValueError(
            "conditions must be a list or tuple of mappings, got %r" % (conditions,)
        )
    normalized = []
    seen = set()
    for condition in conditions:
        if not isinstance(condition, dict):
            raise ValueError(
                "each condition must be a mapping, got %r"
                % (type(condition).__name__,)
            )
        condition_id = _label(condition.get("condition_id"), "condition_id")
        if condition_id in seen:
            raise ValueError("duplicate condition_id %r" % (condition_id,))
        seen.add(condition_id)
        normalized.append(
            {
                "condition_id": condition_id,
                "closure_record_present": _flag(condition, "closure_record_present"),
            }
        )
    return normalized


def open_conditions(conditions):
    """Conditions still without a closure record."""
    return tuple(
        condition["condition_id"]
        for condition in normalize_conditions(conditions)
        if not condition["closure_record_present"]
    )


def normalize_approval(approval):
    """Validate one approval record."""
    if not isinstance(approval, dict):
        raise ValueError(
            "approval must be a mapping, got %r" % (type(approval).__name__,)
        )
    age = _real(approval.get("approval_age_months"), "approval_age_months")
    if age < 0.0:
        raise ValueError("approval_age_months must not be negative, got %r" % (age,))
    granted_at_gate = approval.get("granted_at_gate")
    gate_index(granted_at_gate)
    conditional = _flag(approval, "conditional")
    conditions = normalize_conditions(approval.get("conditions", []))
    if conditional and not conditions:
        raise ValueError("a conditional approval must carry at least one condition")
    if conditions and not conditional:
        raise ValueError("conditions were attached to an unconditional approval")
    return {
        "granted_at_gate": granted_at_gate,
        "approval_age_months": age,
        "conditional": conditional,
        "conditions": conditions,
        "justification_fields": _name_set(
            approval.get("justification_fields", []),
            REQUIRED_JUSTIFICATION_FIELDS,
            "justification field",
        ),
        "documents": _name_set(
            approval.get("documents", []),
            REQUIRED_APPROVAL_DOCUMENTS,
            "approval document",
        ),
    }


def assess_part_approval(part):
    """Read one proposed part and return its release status with findings."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    part_number = _label(part.get("part_number"), "part_number")
    role = part.get("procurement_role")
    required_gate = governing_gate(role)
    category = _label(part.get("declared_category"), "declared_category")
    approval = part.get("approval")

    findings = []
    if approval is None:
        findings.append(
            {
                "part_number": part_number,
                "finding": "proposed-part-never-submitted-for-approval",
                "detail": role,
            }
        )
        return {
            "part_number": part_number,
            "procurement_role": role,
            "governing_gate": required_gate,
            "declared_category": category,
            "status": "class-2-part-not-approved",
            "missing_justification_fields": list(REQUIRED_JUSTIFICATION_FIELDS),
            "missing_approval_documents": list(REQUIRED_APPROVAL_DOCUMENTS),
            "open_conditions": [],
            "findings": findings,
            "released": False,
        }

    record = normalize_approval(approval)
    missing_fields = missing_justification_fields(record["justification_fields"])
    missing_documents = missing_approval_documents(record["documents"])
    still_open = open_conditions(record["conditions"])

    blocked = False
    if category != TARGET_CATEGORY:
        blocked = True
        findings.append(
            {
                "part_number": part_number,
                "finding": "declared-category-is-not-the-one-being-released",
                "detail": category,
            }
        )
    for field in missing_fields:
        blocked = True
        findings.append(
            {
                "part_number": part_number,
                "finding": "justification-record-incomplete",
                "detail": field,
            }
        )
    for document in missing_documents:
        blocked = True
        findings.append(
            {
                "part_number": part_number,
                "finding": "approval-document-missing",
                "detail": document,
            }
        )
    if not approval_is_timely(record["granted_at_gate"], role):
        blocked = True
        findings.append(
            {
                "part_number": part_number,
                "finding": "approval-later-than-governing-gate",
                "detail": "%s after %s" % (record["granted_at_gate"], required_gate),
            }
        )
    if record["approval_age_months"] > APPROVAL_VALIDITY_MONTHS + VALIDITY_TOLERANCE:
        blocked = True
        findings.append(
            {
                "part_number": part_number,
                "finding": "approval-outside-validity-window",
                "detail": "%.1f months" % record["approval_age_months"],
            }
        )
    for condition_id in still_open:
        findings.append(
            {
                "part_number": part_number,
                "finding": "conditional-approval-condition-not-closed",
                "detail": condition_id,
            }
        )

    if blocked:
        status = "class-2-part-approval-incomplete"
    elif still_open:
        status = "class-2-part-conditionally-approved"
    else:
        status = "class-2-part-released-for-flight"

    return {
        "part_number": part_number,
        "procurement_role": role,
        "governing_gate": required_gate,
        "granted_at_gate": record["granted_at_gate"],
        "declared_category": category,
        "status": status,
        "missing_justification_fields": list(missing_fields),
        "missing_approval_documents": list(missing_documents),
        "open_conditions": list(still_open),
        "findings": findings,
        "released": status == "class-2-part-released-for-flight",
    }


def assess_class_2_parts_approval(programme_id, proposed_parts):
    """Turn a proposed parts list into a released flight parts list."""
    _label(programme_id, "programme_id")
    if isinstance(proposed_parts, str) or not isinstance(
        proposed_parts, (list, tuple)
    ):
        raise ValueError(
            "proposed_parts must be a list or tuple of mappings, got %r"
            % (proposed_parts,)
        )
    if not proposed_parts:
        raise ValueError("at least one proposed part is required")

    records = []
    seen = set()
    for part in proposed_parts:
        record = assess_part_approval(part)
        if record["part_number"] in seen:
            raise ValueError("duplicate part_number %r" % (record["part_number"],))
        seen.add(record["part_number"])
        records.append(record)

    released = [r["part_number"] for r in records if r["released"]]
    blocked = [r["part_number"] for r in records if not r["released"]]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    counts = {status: 0 for status in PART_STATUSES}
    for record in records:
        counts[record["status"]] += 1

    return {
        "programme_id": programme_id,
        "part_records": records,
        "released_parts": released,
        "blocked_parts": blocked,
        "status_counts": counts,
        "findings": findings,
        "list_releasable": not blocked,
    }
