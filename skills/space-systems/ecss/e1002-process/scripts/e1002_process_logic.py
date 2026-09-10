"""Deterministic logic for the ECSS-E-ST-10-02C clause 5.1 verification
process: responsibility assignment between customer and supplier, and
the documentation set required per product level and process phase.

Stdlib only. No network, no randomness.
"""

from __future__ import annotations

# Verification levels, consistent with the sibling e1002-levels leaf.
PRODUCT_LEVELS = ("equipment", "subsystem", "element", "segment", "system")

# Aggregation levels where cross-supplier integration happens; the
# customer retains verification closure approval here by default
# because no single supplier owns the integrated product.
CUSTOMER_RETAINED_LEVELS = frozenset({"element", "segment", "system"})

PARTIES = ("customer", "supplier")

PROCESS_PHASES = ("planning", "execution", "closure")

DOC_TYPES = (
    "verification-plan",
    "verification-control-document",
    "verification-report",
)

# Documents that must be on record before a phase can be considered
# entered/complete. Planning needs the plan; execution needs the live
# tracking matrix; closure needs the matrix fully reflected plus the
# closing report.
REQUIRED_DOCS_BY_PHASE = {
    "planning": ("verification-plan",),
    "execution": ("verification-control-document",),
    "closure": ("verification-control-document", "verification-report"),
}

ACTIVITY_STATUSES = ("open", "in-progress", "closed", "waived")

# Statuses that represent a resolved activity for roll-up purposes.
RESOLVED_STATUSES = frozenset({"closed", "waived"})


def validate_product_level(product_level):
    if product_level not in PRODUCT_LEVELS:
        raise ValueError(
            "unknown product level %r; expected one of %s"
            % (product_level, PRODUCT_LEVELS)
        )
    return product_level


def validate_phase(phase):
    if phase not in PROCESS_PHASES:
        raise ValueError(
            "unknown process phase %r; expected one of %s" % (phase, PROCESS_PHASES)
        )
    return phase


def validate_status(status):
    if status not in ACTIVITY_STATUSES:
        raise ValueError(
            "unknown activity status %r; expected one of %s"
            % (status, ACTIVITY_STATUSES)
        )
    return status


def validate_doc_type(doc_type):
    if doc_type not in DOC_TYPES:
        raise ValueError(
            "unknown document type %r; expected one of %s" % (doc_type, DOC_TYPES)
        )
    return doc_type


def assign_responsibility(product_level, safety_critical, delegation_agreement=False):
    """Assign the executor and closure-approver for a verification
    activity at a given product level.

    The supplier always plans and executes the verification activity --
    this is a customer-supplier activity, not a customer-only one. The
    closure approver depends on risk and level:
      - a safety-critical activity is always approved by the customer;
        delegation cannot waive that regardless of level or agreement.
      - a customer-retained level (element, segment, system) defaults
        to customer approval, since integration across suppliers
        happens there.
      - an equipment/subsystem-level activity may be delegated to the
        supplier only with an explicit delegation agreement on record;
        without one, the customer approves by default.
    """
    validate_product_level(product_level)
    executor = "supplier"
    if safety_critical:
        approver = "customer"
    elif product_level in CUSTOMER_RETAINED_LEVELS:
        approver = "customer"
    elif delegation_agreement:
        approver = "supplier"
    else:
        approver = "customer"
    return {"executor": executor, "approver": approver}


def check_documentation(phase, docs_on_record):
    """Return the list of documents still missing for a phase to be
    considered entered/complete. Raises on an unrecognised phase or an
    unrecognised document type in the input set."""
    validate_phase(phase)
    seen = set()
    for doc_type in docs_on_record:
        validate_doc_type(doc_type)
        seen.add(doc_type)
    return [doc for doc in REQUIRED_DOCS_BY_PHASE[phase] if doc not in seen]


def rollup_activity_status(statuses):
    """Roll a list of individual verification-activity statuses up to
    a single product-level status. Raises on an empty list (a product
    level with no verification activities on record is a data error,
    not an implicit pass) or an unrecognised status."""
    if not statuses:
        raise ValueError("cannot roll up status: no verification activities on record")
    for status in statuses:
        validate_status(status)
    if any(status == "open" for status in statuses):
        return "open"
    if any(status == "in-progress" for status in statuses):
        return "in-progress"
    return "closed"


def validate_closure(activity):
    """Check a single verification activity's closure sign-off against
    the responsibility rule.

    activity: dict with keys:
      - status: one of ACTIVITY_STATUSES
      - product_level: one of PRODUCT_LEVELS
      - safety_critical: bool
      - delegation_agreement: bool
      - approved_by: party that signed off closure, or None if not
        yet closed/waived.

    Returns a dict with the required approver and a 'valid' flag. An
    activity that is not yet resolved (open/in-progress) is always
    valid -- there is nothing to check yet. A resolved activity
    (closed/waived) is valid only if approved_by matches the required
    approver.
    """
    status = validate_status(activity["status"])
    required = assign_responsibility(
        activity["product_level"],
        activity["safety_critical"],
        activity.get("delegation_agreement", False),
    )
    required_approver = required["approver"]
    if status not in RESOLVED_STATUSES:
        return {"required_approver": required_approver, "valid": True}
    valid = activity.get("approved_by") == required_approver
    return {"required_approver": required_approver, "valid": valid}


def evaluate_process_record(record):
    """Evaluate the full clause 5.1 process record for one product
    level: documentation completeness for the declared phase, the
    rolled-up activity status, and per-activity closure sign-off.

    record: dict with keys:
      - product_level: one of PRODUCT_LEVELS
      - phase: one of PROCESS_PHASES
      - docs_on_record: iterable of document type strings
      - activities: non-empty list of activity dicts (see
        validate_closure for the shape)

    Returns a dict:
      - missing_docs: list of required-but-absent document types
      - overall_status: rolled-up activity status
      - closure_findings: list of activities whose sign-off does not
        match the required approver (each tagged with its index)
      - compliant: True only if no missing docs, overall_status is
        'closed', and closure_findings is empty
    """
    validate_product_level(record["product_level"])
    missing_docs = check_documentation(record["phase"], record["docs_on_record"])
    activities = record["activities"]
    overall_status = rollup_activity_status([a["status"] for a in activities])
    closure_findings = []
    for index, activity in enumerate(activities):
        result = validate_closure(activity)
        if not result["valid"]:
            closure_findings.append(
                {
                    "index": index,
                    "required_approver": result["required_approver"],
                    "approved_by": activity.get("approved_by"),
                }
            )
    compliant = (
        not missing_docs and overall_status == "closed" and not closure_findings
    )
    return {
        "missing_docs": missing_docs,
        "overall_status": overall_status,
        "closure_findings": closure_findings,
        "compliant": compliant,
    }
