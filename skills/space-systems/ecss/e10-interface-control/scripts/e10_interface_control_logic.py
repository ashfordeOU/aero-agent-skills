#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.4 system-level interface management/control
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general-requirements standard requires every
interface between two interfacing elements to be identified, assigned
to a physical domain, and controlled through a fixed sequence of
control documents defined by ECSS-E-ST-10-24 -- an interface
requirement document (IRD) capturing the needed characteristics before
design commitment, followed by a baselined interface control document
(ICD) once the interface has matured (or a lighter-weight interface
control note for an interface that stays inside one responsible
owner). This module implements interface domain classification,
responsibility-boundary/required-document determination, control-
status transition validation, and side-to-side interface parameter
consistency checking; it does not define the ICD/IRD content templates
themselves or the configuration-management baselining process around
them.
"""

INTERFACE_DOMAINS = frozenset(
    {"mechanical", "electrical", "thermal", "data", "fluid"}
)

# Fixed control-status sequence; a status may only advance exactly one
# step at a time along this list.
STATUS_SEQUENCE = ["identified", "ird_drafted", "ird_agreed", "icd_baselined", "verified"]

INTERNAL_CONTROL_DOCUMENT = "interface_control_note"
EXTERNAL_CONTROL_DOCUMENT = "ICD"


def classify_interface_domain(domain):
    """Physical domain of an interface, echoed back unchanged when
    recognized. Raises ValueError for a domain outside the five known
    physical domains under E-ST-10C clause 5.6.4."""
    if domain in INTERFACE_DOMAINS:
        return domain
    raise ValueError(
        "unrecognized interface domain %r under E-ST-10C clause 5.6.4" % (domain,)
    )


def interface_boundary(side_a_owner, side_b_owner):
    """Responsibility boundary for an interface: "internal" when both
    interfacing elements share the same responsible owner, "external"
    when the owners differ. Raises ValueError if either owner is
    empty/falsy (an interface cannot be assessed without a declared
    owner on each side)."""
    if not side_a_owner or not side_b_owner:
        raise ValueError("both side_a_owner and side_b_owner must be provided")
    return "internal" if side_a_owner == side_b_owner else "external"


def required_control_document(boundary):
    """Control document ECSS-E-ST-10-24 requires once an interface with
    the given boundary reaches baselining: the formal ICD for an
    external interface, the lighter-weight interface control note for
    an internal one. Raises ValueError for an unrecognized boundary."""
    if boundary == "external":
        return EXTERNAL_CONTROL_DOCUMENT
    if boundary == "internal":
        return INTERNAL_CONTROL_DOCUMENT
    raise ValueError("unrecognized interface boundary %r" % (boundary,))


def validate_status_transition(current_status, next_status):
    """Validates that next_status is exactly one step forward from
    current_status along STATUS_SEQUENCE. Returns next_status on
    success. Raises ValueError for an unrecognized status name, a
    skipped step, a backward move, or a no-op (same status)."""
    if current_status not in STATUS_SEQUENCE:
        raise ValueError("unrecognized interface status %r" % (current_status,))
    if next_status not in STATUS_SEQUENCE:
        raise ValueError("unrecognized interface status %r" % (next_status,))
    current_index = STATUS_SEQUENCE.index(current_status)
    next_index = STATUS_SEQUENCE.index(next_status)
    if next_index != current_index + 1:
        raise ValueError(
            "invalid interface status transition from %r to %r; a status "
            "advances exactly one step at a time along %r"
            % (current_status, next_status, STATUS_SEQUENCE)
        )
    return next_status


def interface_document_violations(interface_id, status, boundary, control_documents):
    """Violation list (empty if compliant) for the control documents on
    record for one interface, given its current status and
    responsibility boundary. control_documents: iterable of document
    names already on record (e.g. ["IRD"], ["IRD", "ICD"]). Raises
    ValueError for an unrecognized status or boundary."""
    if status not in STATUS_SEQUENCE:
        raise ValueError("unrecognized interface status %r" % (status,))
    required_document = required_control_document(boundary)
    documents_on_record = set(control_documents or [])
    status_index = STATUS_SEQUENCE.index(status)
    violations = []
    if status_index >= STATUS_SEQUENCE.index("ird_drafted") and "IRD" not in documents_on_record:
        violations.append({"issue": "missing_ird", "interface": interface_id})
    if status_index >= STATUS_SEQUENCE.index("icd_baselined") and required_document not in documents_on_record:
        violations.append(
            {
                "issue": "missing_required_control_document",
                "interface": interface_id,
                "required_document": required_document,
            }
        )
    return violations


def interface_parameter_violations(interface_id, side_a_parameters, side_b_parameters):
    """Violation list (empty if compliant) comparing the two sides'
    declared interface parameters key by key. Flags a parameter present
    on only one side, and a parameter present on both sides with
    different values. Does not mutate either parameter mapping."""
    violations = []
    all_keys = set(side_a_parameters) | set(side_b_parameters)
    for key in sorted(all_keys):
        if key not in side_a_parameters:
            violations.append(
                {"issue": "parameter_missing_side_a", "interface": interface_id, "parameter": key}
            )
        elif key not in side_b_parameters:
            violations.append(
                {"issue": "parameter_missing_side_b", "interface": interface_id, "parameter": key}
            )
        elif side_a_parameters[key] != side_b_parameters[key]:
            violations.append(
                {
                    "issue": "parameter_mismatch",
                    "interface": interface_id,
                    "parameter": key,
                    "side_a": side_a_parameters[key],
                    "side_b": side_b_parameters[key],
                }
            )
    return violations


def interface_control_review(interface):
    """Full clause 5.6.4 interface control review for one interface.

    interface: {"interface_id": str, "domain": str, "side_a_owner":
    str, "side_b_owner": str, "status": str, "control_documents":
    [str, ...], "side_a_parameters": {...}, "side_b_parameters": {...}}.
    Returns {"documentation": [...], "parameters": [...]}, each a
    violation list. Raises ValueError for an unrecognized domain,
    status, or a missing owner on either side."""
    interface_id = interface["interface_id"]
    classify_interface_domain(interface["domain"])
    boundary = interface_boundary(interface["side_a_owner"], interface["side_b_owner"])
    return {
        "documentation": interface_document_violations(
            interface_id,
            interface["status"],
            boundary,
            interface.get("control_documents"),
        ),
        "parameters": interface_parameter_violations(
            interface_id,
            interface.get("side_a_parameters", {}),
            interface.get("side_b_parameters", {}),
        ),
    }


def is_interface_controlled(review):
    """True when both categories in an interface_control_review result
    are empty -- the interface is under control for this assessment."""
    return all(len(violations) == 0 for violations in review.values())
