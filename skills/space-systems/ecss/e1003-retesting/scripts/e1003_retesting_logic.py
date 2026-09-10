"""Deterministic logic for ECSS-E-ST-10-03C clause 4.6 retesting rules.

Offline, stdlib-only module backing the e1003-retesting skill leaf:
classifying whether an article must be retested under each of the four
clause 4.6 triggers (design modification after qualification, storage
after a protoflight/acceptance test, a re-flown article, or flight use
of a qualification article), and confirming a retesting review covers
every case in its intended scope.
"""

TRIGGERS = frozenset(
    {
        "design_modification",
        "storage_after_test",
        "reflown_article",
        "qualification_article_for_flight",
    }
)

STATUSES = frozenset(
    {
        "no_retest_required",
        "requalification_required",
        "retest_required",
        "repair_and_requalify",
        "acceptance_retest_required",
        "disallowed_for_flight",
    }
)


def evaluate_design_modification(affects_qualified_envelope: bool) -> str:
    """Retest outcome for a design change made after qualification.

    A modification that touches the qualified envelope (form, fit,
    function, or any previously verified qualified parameter) means the
    prior qualification evidence no longer covers the modified design,
    so the affected requirements must be requalified. A modification
    kept outside that envelope does not by itself invalidate the
    qualification and needs no new test (it still needs a documented
    engineering justification, tracked outside this leaf).
    """
    if affects_qualified_envelope:
        return "requalification_required"
    return "no_retest_required"


def evaluate_storage_retest(
    storage_duration_months: float,
    qualified_shelf_life_months: float,
    storage_conditions_within_spec: bool,
) -> str:
    """Retest outcome for storage after a protoflight/acceptance test.

    Storage outside the qualified/specified conditions invalidates the
    prior acceptance disposition regardless of how long the article was
    stored, so it forces a retest. Storage kept within spec but held
    longer than the qualified shelf life also forces a retest. Only
    storage that stays within both the specified conditions and the
    qualified shelf life needs no retest.
    """
    if not storage_conditions_within_spec:
        return "retest_required"
    if storage_duration_months > qualified_shelf_life_months:
        return "retest_required"
    return "no_retest_required"


def evaluate_reflown_article(inspection_damage_found: bool) -> str:
    """Retest outcome for an article proposed for a second flight.

    A re-flown article is never re-accepted on its prior flight record
    alone. Damage or degradation found during post-flight inspection
    routes to repair and requalification of the affected areas; a clean
    inspection still requires a fresh acceptance-level retest before
    the next flight.
    """
    if inspection_damage_found:
        return "repair_and_requalify"
    return "acceptance_retest_required"


def evaluate_qualification_article_for_flight(
    margin_consumed_exceeds_limit: bool,
    damage_found: bool,
) -> str:
    """Retest outcome for flying the qualification-model article.

    Qualification testing is deliberately run above flight levels to
    demonstrate design margin, which can consume life/margin on the
    specific article or leave damage; either finding disallows that
    article from flight outright. A qualification article that is
    clean on both counts is still not flown as-is: qualification
    evidence proves the design, not this article's workmanship, so it
    still needs an acceptance-level retest first.
    """
    if margin_consumed_exceeds_limit or damage_found:
        return "disallowed_for_flight"
    return "acceptance_retest_required"


def evaluate_retesting_case(case: dict) -> dict:
    """Dispatch one retesting case dict to its trigger-specific rule.

    Required keys: id, trigger, plus the trigger-specific evidence
    fields (design_modification: affects_qualified_envelope;
    storage_after_test: storage_duration_months,
    qualified_shelf_life_months, storage_conditions_within_spec;
    reflown_article: inspection_damage_found;
    qualification_article_for_flight: margin_consumed_exceeds_limit,
    damage_found). Returns a new dict {id, trigger, status}; does not
    mutate the input. Raises ValueError if 'id' is missing or 'trigger'
    is not a known trigger.
    """
    if "id" not in case:
        raise ValueError("case is missing an id")
    trigger = case.get("trigger")
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown retesting trigger: {trigger!r}")

    if trigger == "design_modification":
        status = evaluate_design_modification(case["affects_qualified_envelope"])
    elif trigger == "storage_after_test":
        status = evaluate_storage_retest(
            case["storage_duration_months"],
            case["qualified_shelf_life_months"],
            case["storage_conditions_within_spec"],
        )
    elif trigger == "reflown_article":
        status = evaluate_reflown_article(case["inspection_damage_found"])
    else:
        status = evaluate_qualification_article_for_flight(
            case["margin_consumed_exceeds_limit"],
            case["damage_found"],
        )

    return {"id": case["id"], "trigger": trigger, "status": status}


def build_retesting_dispositions(cases: list) -> list:
    """Disposition for every retesting case, in input order.

    Raises ValueError on a duplicate case id.
    """
    dispositions = []
    seen_ids = set()
    for case in cases:
        result = evaluate_retesting_case(case)
        if result["id"] in seen_ids:
            raise ValueError(f"duplicate case id: {result['id']!r}")
        seen_ids.add(result["id"])
        dispositions.append(result)
    return dispositions


def missing_retesting_dispositions(all_case_ids: list, dispositions: list) -> list:
    """Case ids expected in the retesting review but absent from
    dispositions, in all_case_ids order -- a retesting review cannot
    claim completeness while an intended case was never dispositioned.
    """
    dispositioned_ids = {entry["id"] for entry in dispositions}
    return [cid for cid in all_case_ids if cid not in dispositioned_ids]


def close_out_retesting_review(all_case_ids: list, dispositions: list) -> tuple:
    """Retesting-review closure verdict across a set of dispositions.

    Returns (complete, missing_ids): complete is True only when every
    case id in all_case_ids has a recorded disposition; missing_ids
    lists the case ids still lacking one, in all_case_ids order. This
    checks review coverage, not the retest outcome itself -- a
    dispositioned case can legitimately resolve to any status in
    STATUSES and still count as complete.
    """
    missing_ids = missing_retesting_dispositions(all_case_ids, dispositions)
    return (len(missing_ids) == 0, missing_ids)
