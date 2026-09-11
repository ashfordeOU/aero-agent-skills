#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.4.1.3 design method, tool and model selection
and validation (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard requires that the
design methods, tools and models used to produce a design output
(design rules, analyses, simulations) are selected as appropriate to
that output and shown to be adequate before the output is relied on.
A method is either model-based (an analytical derivation or a
numerical simulation, whose credibility rests on a validation record
against reference or test data) or rule-based (an empirical
correlation or a heritage design rule carried over from a prior
product, whose credibility rests on a documented precedent whose
original bounding conditions cover the current design case). A
model-based method applied outside the domain its validation record
covers is an extrapolation, not a full confirmation, and a rule-based
method applied outside its precedent's bounding conditions is an
unbounded extrapolation of that precedent -- both still contribute
partial engineering confidence but cannot alone confirm a design
output without a recorded rationale for relying on them. This module
implements the method-family classification, the per-method
validation/bounding status, the per-output confirmation-weight
accounting against a required independent-confirmation threshold, and
the traceability check that an out-of-domain or unbounded method
carries a recorded rationale; it does not set what confirmation
weight or precedent-bounding conditions a given project requires --
those come from the project's method-selection plan.
"""

MODEL_BASED_METHOD_TYPES = frozenset({"analytical", "numerical_simulation"})
RULE_BASED_METHOD_TYPES = frozenset({"empirical_correlation", "heritage_design_rule"})

# Confirmation weight a model-based method contributes per unit of its
# base confidence, by validation status. A method validated within the
# domain its validation record covers contributes full confidence; one
# validated but applied outside that domain is an extrapolation and
# contributes reduced confidence; an unvalidated method contributes none.
CONFIRMATION_WEIGHT_BY_STATUS = {
    "validated_in_domain": 1.0,
    "validated_out_of_domain": 0.5,
    "unvalidated": 0.0,
}


def classify_design_method(method_type):
    """Method family for a method type: "model_based" or "rule_based".
    Raises ValueError for a method type outside both known sets."""
    if method_type in MODEL_BASED_METHOD_TYPES:
        return "model_based"
    if method_type in RULE_BASED_METHOD_TYPES:
        return "rule_based"
    raise ValueError(
        "unrecognized design method type %r under E-ST-10C clause "
        "5.4.1.3" % (method_type,)
    )


def model_validation_status(is_validated, within_domain_of_applicability):
    """Validation status of a model-based method: "validated_in_domain"
    if it has a validation record and the current design case falls
    within the domain that record covers, "validated_out_of_domain" if
    it has a validation record but the case falls outside that domain,
    otherwise "unvalidated" (no validation record, domain is moot)."""
    if not is_validated:
        return "unvalidated"
    if within_domain_of_applicability:
        return "validated_in_domain"
    return "validated_out_of_domain"


def rule_precedent_bounded(has_documented_precedent, precedent_conditions_bound_case):
    """True when a rule-based method's documented precedent conditions
    bound the current design case (both conditions hold). False when
    there is no documented precedent at all, or the precedent exists
    but its original bounding conditions do not cover this case."""
    return bool(has_documented_precedent) and bool(precedent_conditions_bound_case)


def design_method_confirmation_weight(base_confidence, validation_status):
    """Confirmation weight one model-based method contributes:
    base_confidence x the weight for validation_status. Raises
    ValueError for a negative base_confidence or an unrecognized
    validation_status."""
    if base_confidence < 0:
        raise ValueError("base_confidence must be >= 0")
    if validation_status not in CONFIRMATION_WEIGHT_BY_STATUS:
        raise ValueError("unrecognized validation status %r" % (validation_status,))
    return base_confidence * CONFIRMATION_WEIGHT_BY_STATUS[validation_status]


def model_confirmation_violations(output_id, model_based_methods, required_confirmation_weight):
    """Violation list (empty if adequately confirmed) for the
    model-based methods behind one design output. model_based_methods:
    iterable of dicts with keys "base_confidence", "validation_status".
    required_confirmation_weight: the output's method-selection-plan
    threshold, or None if no threshold has been captured yet (itself a
    finding once methods contribute nonzero weight). Does not mutate
    model_based_methods."""
    total = sum(
        design_method_confirmation_weight(
            method["base_confidence"], method["validation_status"]
        )
        for method in model_based_methods
    )
    if required_confirmation_weight is None:
        if total > 0:
            return [
                {
                    "issue": "missing_required_confirmation_weight",
                    "output": output_id,
                    "total_weight": total,
                }
            ]
        return []
    if total < required_confirmation_weight:
        return [
            {
                "issue": "insufficient_design_method_confirmation",
                "output": output_id,
                "total_weight": total,
                "required_weight": required_confirmation_weight,
            }
        ]
    return []


def rule_based_traceability_violations(output_id, has_unbounded_rule_based_method, rationale_on_record):
    """Violation list (empty if traceable) for the rule-based methods
    behind one design output. A design output with at least one
    rule-based method whose precedent does not bound the case
    (has_unbounded_rule_based_method True) must carry a recorded
    rationale for relying on it; its absence is flagged."""
    if has_unbounded_rule_based_method and not rationale_on_record:
        return [
            {
                "issue": "missing_rationale_for_unbounded_design_rule",
                "output": output_id,
            }
        ]
    return []


def design_methods_review(design_output):
    """Full clause 5.4.1.3 method selection and validation review for
    one design output.

    design_output: {"output_id": str, "methods": [{"method_type": str,
    ... model-based fields "is_validated", "within_domain_of_applicability",
    "base_confidence", or rule-based fields "has_documented_precedent",
    "precedent_conditions_bound_case"}], "required_confirmation_weight":
    float | None, "rationale_on_record": bool}. Returns {"selection":
    [...], "traceability": [...]}, each a violation list. Raises
    ValueError for an unrecognized method_type."""
    output_id = design_output["output_id"]
    model_based_methods = []
    has_unbounded_rule_based_method = False
    for method in design_output.get("methods", []):
        family = classify_design_method(method["method_type"])
        if family == "model_based":
            status = model_validation_status(
                method["is_validated"], method["within_domain_of_applicability"]
            )
            model_based_methods.append(
                {"base_confidence": method["base_confidence"], "validation_status": status}
            )
        else:
            if not rule_precedent_bounded(
                method["has_documented_precedent"],
                method["precedent_conditions_bound_case"],
            ):
                has_unbounded_rule_based_method = True
    return {
        "selection": model_confirmation_violations(
            output_id, model_based_methods, design_output.get("required_confirmation_weight")
        ),
        "traceability": rule_based_traceability_violations(
            output_id, has_unbounded_rule_based_method, design_output.get("rationale_on_record")
        ),
    }


def is_design_methods_compliant(review):
    """True when both categories in a design_methods_review result are
    empty -- the design output satisfies clause 5.4.1.3 for this
    assessment."""
    return all(len(violations) == 0 for violations in review.values())
