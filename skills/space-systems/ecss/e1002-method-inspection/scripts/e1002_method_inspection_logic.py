#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.2.5 inspection method (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
verification standard offers a small set of verification methods
(review-of-design/analysis, test, inspection, demonstration) that a
verification plan assigns per requirement. Inspection confirms
conformance by visual examination or by a simple measurement taken
with standard equipment -- it does not cover requirements that need
special test equipment/procedures or that require the item to be
operated (those belong to test or demonstration instead). This module
implements inspection-method applicability, verification-plan entry
completeness, per-item (visual/measurement) evaluation against a
reference or a tolerance band, and roll-up of item outcomes to an
overall inspection status; it does not implement the test or
demonstration methods themselves.
"""

INSPECTION_TECHNIQUES = frozenset({"visual", "measurement"})

REQUIRED_PLAN_FIELDS = ("requirement_id", "technique", "acceptance_criteria", "checklist")

ITEM_STATUSES = frozenset({"pass", "fail", "pending"})

NOT_APPLICABLE = "not_applicable"


def classify_inspection_technique(technique):
    """Inspection technique for a checklist item: "visual" or
    "measurement". Raises ValueError for a technique outside both
    known sets."""
    if technique in INSPECTION_TECHNIQUES:
        return technique
    raise ValueError(
        "unrecognized inspection technique %r under E-ST-10-02C "
        "clause 5.2.2.5" % (technique,)
    )


def is_inspection_method_applicable(requires_special_equipment, requires_functional_operation):
    """True when clause 5.2.2.5 inspection may be used for a
    requirement: conformance can be confirmed by visual examination or
    a simple measurement with standard equipment, without special test
    equipment/procedures and without operating the item. Either
    condition being True routes the requirement to test or
    demonstration instead."""
    return not requires_special_equipment and not requires_functional_operation


def evaluate_visual_item(conforms_to_reference):
    """Outcome of one visual checklist item: "pass" when the observed
    condition conforms to the reference, else "fail". Raises
    ValueError when conforms_to_reference is not a bool."""
    if not isinstance(conforms_to_reference, bool):
        raise ValueError("conforms_to_reference must be a bool")
    return "pass" if conforms_to_reference else "fail"


def evaluate_measurement_item(measured_value, nominal_value, tolerance):
    """Outcome of one measurement checklist item: "pass" when
    measured_value falls within nominal_value +/- tolerance, else
    "fail". Raises ValueError for a negative tolerance."""
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    lower = nominal_value - tolerance
    upper = nominal_value + tolerance
    return "pass" if lower <= measured_value <= upper else "fail"


def evaluate_checklist_item(item):
    """Outcome of one checklist item dict. A "visual" item requires
    "conforms_to_reference"; a "measurement" item requires
    "measured_value", "nominal_value", "tolerance". Raises ValueError
    for an unrecognized technique or a missing required key."""
    technique = classify_inspection_technique(item["technique"])
    if technique == "visual":
        return evaluate_visual_item(item["conforms_to_reference"])
    return evaluate_measurement_item(
        item["measured_value"], item["nominal_value"], item["tolerance"]
    )


def plan_completeness_violations(entry):
    """Violation list (empty if complete) for a verification plan
    entry missing any of REQUIRED_PLAN_FIELDS. Does not mutate entry."""
    violations = []
    for field in REQUIRED_PLAN_FIELDS:
        if not entry.get(field):
            violations.append(
                {
                    "issue": "missing_plan_field",
                    "field": field,
                    "requirement_id": entry.get("requirement_id"),
                }
            )
    return violations


def rollup_status(item_statuses):
    """Aggregate a non-empty list of per-item statuses into one
    overall status: "fail" if any item failed, else "pending" if any
    item is still pending, else "pass". Raises ValueError for an empty
    list or an unrecognized status value."""
    if not item_statuses:
        raise ValueError("item_statuses must not be empty")
    for status in item_statuses:
        if status not in ITEM_STATUSES:
            raise ValueError("unrecognized item status %r" % (status,))
    if "fail" in item_statuses:
        return "fail"
    if "pending" in item_statuses:
        return "pending"
    return "pass"


def inspection_review(entry):
    """Full clause 5.2.2.5 inspection review for one verification plan
    entry.

    entry: {"requirement_id": str, "technique": "visual"|"measurement",
    "acceptance_criteria": str, "requires_special_equipment": bool,
    "requires_functional_operation": bool, "checklist": [item, ...]}.
    Each checklist item is evaluated by evaluate_checklist_item.

    Returns {"applicability": bool, "plan_violations": [...],
    "item_statuses": [...], "status": "pass"|"fail"|"pending"|
    NOT_APPLICABLE}. When the method does not apply, or the plan entry
    is incomplete, the checklist is not evaluated and item_statuses is
    empty. Raises ValueError propagated from evaluate_checklist_item
    for a malformed checklist item once the plan is complete and the
    method applies."""
    plan_violations = plan_completeness_violations(entry)
    applicable = is_inspection_method_applicable(
        entry.get("requires_special_equipment", False),
        entry.get("requires_functional_operation", False),
    )
    if not applicable:
        return {
            "applicability": False,
            "plan_violations": plan_violations,
            "item_statuses": [],
            "status": NOT_APPLICABLE,
        }
    if plan_violations:
        return {
            "applicability": True,
            "plan_violations": plan_violations,
            "item_statuses": [],
            "status": "pending",
        }
    item_statuses = [evaluate_checklist_item(item) for item in entry["checklist"]]
    return {
        "applicability": True,
        "plan_violations": [],
        "item_statuses": item_statuses,
        "status": rollup_status(item_statuses),
    }


def is_inspection_compliant(review):
    """True when an inspection_review result carries an overall
    "pass" status."""
    return review["status"] == "pass"
