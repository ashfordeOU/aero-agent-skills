#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.2.3 verification-by-analysis method
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
verification process specification's analysis clause is used when the
evidence needed to close a requirement is produced by calculation,
modeling, or comparison rather than by a physical test, inspection, or
review of design. The clause recognizes several analysis techniques
(worst-case, qualitative, statistical/probabilistic, classical
calculation, and similarity) and, for the similarity technique, sets
heritage conditions that must all hold before a requirement can be
closed on the strength of a previously verified reference item: the
reference item must itself have been verified, the new item's design
and manufacturing process must be identical or their differences must
be explicitly assessed, and the new item's operating environment must
be enveloped by (no more severe than) the environment the reference
item was verified against. This module implements analysis-technique
selection, the similarity heritage/validation checks, analysis-plan
completeness checking, and a per-case status roll-up; it does not
define the numeric analysis methods (worst-case margins, statistical
distributions) themselves.
"""

ANALYSIS_TECHNIQUES = frozenset(
    {
        "similarity",
        "worst_case",
        "statistical",
        "qualitative",
        "classical_calculation",
    }
)

REQUIRED_PLAN_FIELDS = (
    "requirement_id",
    "technique",
    "input_data_sources",
    "acceptance_criteria",
    "verified_by",
)


def validate_analysis_technique(technique):
    """Confirm technique is one of ANALYSIS_TECHNIQUES. Raises ValueError
    for an unrecognized technique."""
    if technique not in ANALYSIS_TECHNIQUES:
        raise ValueError(
            "unrecognized analysis technique %r under E-ST-10-02C "
            "clause 5.2.2.3" % (technique,)
        )
    return technique


def select_analysis_technique(case):
    """Select the analysis technique for a case under a fixed priority
    order. case: dict of bool flags -- "has_verified_reference_item",
    "requires_probabilistic_treatment", "requires_bounding_worst_case",
    "requires_engineering_judgement_only". Heritage (similarity) takes
    precedence when a verified reference item is available and offered;
    otherwise the case falls through probabilistic, then worst-case,
    then qualitative, defaulting to classical_calculation when none of
    the flags apply. Raises ValueError if case is not a dict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a dict of bool flags")
    if case.get("has_verified_reference_item"):
        return "similarity"
    if case.get("requires_probabilistic_treatment"):
        return "statistical"
    if case.get("requires_bounding_worst_case"):
        return "worst_case"
    if case.get("requires_engineering_judgement_only"):
        return "qualitative"
    return "classical_calculation"


def environment_envelope_check(new_environment, reference_environment):
    """Parameters (keys) of new_environment whose value exceeds the
    matching reference_environment value -- the new item's environment
    is enveloped only when this list is empty. Both arguments are dicts
    mapping an environment parameter name to a numeric severity value
    (higher is more severe, e.g. peak temperature, random-vibration
    Grms). Raises ValueError if new_environment names a parameter that
    reference_environment does not carry -- heritage cannot be claimed
    against an environment that was never characterized for it."""
    exceeded = []
    for parameter, new_value in new_environment.items():
        if parameter not in reference_environment:
            raise ValueError(
                "reference environment has no recorded value for "
                "parameter %r; heritage cannot be claimed" % (parameter,)
            )
        if new_value > reference_environment[parameter]:
            exceeded.append(parameter)
    return exceeded


def similarity_validation(item):
    """Heritage findings (empty list if the similarity technique is
    valid) for one item. item: {"reference_item_id": str | None,
    "reference_previously_verified": bool, "design_identical": bool,
    "design_differences_assessed": bool,
    "manufacturing_process_equivalent": bool, "new_environment": dict,
    "reference_environment": dict}. Each unmet heritage condition
    produces one finding dict with an "issue" key; does not mutate
    item."""
    findings = []
    if not item.get("reference_item_id") or not item.get(
        "reference_previously_verified"
    ):
        findings.append({"issue": "no_verified_reference_item"})
    if not item.get("design_identical") and not item.get(
        "design_differences_assessed"
    ):
        findings.append({"issue": "design_differences_not_assessed"})
    if not item.get("manufacturing_process_equivalent"):
        findings.append({"issue": "manufacturing_process_not_equivalent"})
    exceeded = environment_envelope_check(
        item.get("new_environment", {}), item.get("reference_environment", {})
    )
    if exceeded:
        findings.append(
            {"issue": "environment_not_enveloped", "parameters": exceeded}
        )
    return findings


def verification_by_similarity_status(item):
    """{"status": "verified_by_similarity" | "not_verified", "findings":
    [...]} for one item -- "verified_by_similarity" only when
    similarity_validation(item) returns no findings."""
    findings = similarity_validation(item)
    status = "not_verified" if findings else "verified_by_similarity"
    return {"status": status, "findings": findings}


def analysis_plan_completeness(plan):
    """Missing-field findings (empty list if complete) for an analysis
    plan. plan: dict expected to carry every field in
    REQUIRED_PLAN_FIELDS plus, when plan["technique"] == "similarity",
    a non-empty "reference_item_id". Raises ValueError if plan["technique"]
    is set but not a recognized ANALYSIS_TECHNIQUES member."""
    findings = []
    for field in REQUIRED_PLAN_FIELDS:
        if not plan.get(field):
            findings.append({"issue": "missing_plan_field", "field": field})
    technique = plan.get("technique")
    if technique is not None:
        validate_analysis_technique(technique)
        if technique == "similarity" and not plan.get("reference_item_id"):
            findings.append(
                {"issue": "missing_plan_field", "field": "reference_item_id"}
            )
    return findings


def analysis_case_rollup(cases):
    """Roll up a list of {"case_id": str, "findings": [...]} dicts into
    {"total": int, "closed": int, "open": int, "open_case_ids": [...]}.
    A case with an empty findings list is closed; any other case is
    open. Raises ValueError for an empty cases list."""
    if not cases:
        raise ValueError("cases must be a non-empty list")
    open_case_ids = [
        case["case_id"] for case in cases if case.get("findings")
    ]
    total = len(cases)
    open_count = len(open_case_ids)
    return {
        "total": total,
        "closed": total - open_count,
        "open": open_count,
        "open_case_ids": open_case_ids,
    }
