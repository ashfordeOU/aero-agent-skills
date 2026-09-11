"""
ECSS-E-ST-10C §4.3.2 — Test Review logic (TRR and close-out reviews).
Paraphrased from ECSS-E-ST-10C; standard + clause cited as anchor only.
Stdlib only; deterministic; offline.
"""

REVIEW_TYPE_TRR = "TRR"
REVIEW_TYPE_TCR = "TCR"
VALID_REVIEW_TYPES = frozenset({REVIEW_TYPE_TRR, REVIEW_TYPE_TCR})

CATEGORY_MANDATORY = "mandatory"
CATEGORY_ADVISORY = "advisory"
VALID_CATEGORIES = frozenset({CATEGORY_MANDATORY, CATEGORY_ADVISORY})

OUTCOME_PASS = "PASS"
OUTCOME_CONDITIONAL = "CONDITIONAL_PASS"
OUTCOME_FAIL = "FAIL"

# Dispositions that block a close-out review from passing.
BLOCKING_DISPOSITIONS = frozenset({"OPEN", "NCR_OPEN", "PENDING"})

REQUIRED_RECORD_FIELDS = frozenset({
    "review_type", "date", "chair", "attendees",
    "criteria", "outcome", "action_items",
})


class ReviewError(Exception):
    """Raised when input data violates a structural or completeness rule."""


def validate_criterion(criterion: dict) -> tuple:
    """
    Validates a single criterion entry.
    Returns (ok: bool, issues: list[str]).
    """
    if not isinstance(criterion, dict):
        return False, ["criterion must be a dict"]

    issues = []
    name = criterion.get("name", "")
    if not isinstance(name, str) or not name.strip():
        issues.append("criterion missing or blank 'name'")

    category = criterion.get("category", "")
    if category not in VALID_CATEGORIES:
        issues.append(
            f"unknown category '{category}'; must be one of "
            f"{sorted(VALID_CATEGORIES)}"
        )

    if "met" not in criterion:
        issues.append("criterion missing 'met' boolean")
    elif not isinstance(criterion["met"], bool):
        issues.append("'met' must be a boolean")

    # An unmet criterion must carry evidence or rationale.
    if criterion.get("met") is False:
        evidence = criterion.get("evidence", "")
        if not isinstance(evidence, str) or not evidence.strip():
            issues.append(
                f"criterion '{name.strip()}' is not met but lacks "
                f"evidence/rationale"
            )

    return len(issues) == 0, issues


def categorize_criteria(criteria: list) -> dict:
    """
    Splits a list of criteria into mandatory and advisory groups.
    Returns {'mandatory': [...], 'advisory': [...]}.
    Entries with an unrecognized category are silently excluded from
    both groups (validate_criterion catches them before this is called).
    """
    result = {CATEGORY_MANDATORY: [], CATEGORY_ADVISORY: []}
    for c in criteria:
        cat = c.get("category")
        if cat in VALID_CATEGORIES:
            result[cat].append(c)
    return result


def _derive_outcome(open_mandatory: list, open_advisory: list) -> str:
    if open_mandatory:
        return OUTCOME_FAIL
    if open_advisory:
        return OUTCOME_CONDITIONAL
    return OUTCOME_PASS


def _validate_criteria_list(criteria: list) -> None:
    """Raises ReviewError on the first structural problem found."""
    if not isinstance(criteria, list) or len(criteria) == 0:
        raise ReviewError("criteria must be a non-empty list")
    all_issues = []
    for c in criteria:
        ok, issues = validate_criterion(c)
        if not ok:
            all_issues.extend(issues)
    if all_issues:
        raise ReviewError(f"Invalid criteria: {'; '.join(all_issues)}")


def assess_readiness_review(criteria: list) -> dict:
    """
    Evaluates TRR criteria and derives an outcome.

    Returns:
        {
            'outcome': str,           # PASS | CONDITIONAL_PASS | FAIL
            'open_mandatory': list,   # names of unmet mandatory criteria
            'open_advisory': list,    # names of unmet advisory criteria
        }
    Raises:
        ReviewError if criteria are structurally invalid.
    """
    _validate_criteria_list(criteria)

    grouped = categorize_criteria(criteria)
    open_mandatory = [c["name"] for c in grouped[CATEGORY_MANDATORY] if not c["met"]]
    open_advisory = [c["name"] for c in grouped[CATEGORY_ADVISORY] if not c["met"]]

    return {
        "outcome": _derive_outcome(open_mandatory, open_advisory),
        "open_mandatory": open_mandatory,
        "open_advisory": open_advisory,
    }


def check_open_anomalies(anomalies: list) -> list:
    """
    Returns the list of anomaly ids whose disposition blocks close-out.
    An anomaly with a disposition in BLOCKING_DISPOSITIONS, or missing
    its 'disposition' key entirely, is blocking.

    Raises:
        ReviewError if any anomaly entry is not a dict or lacks 'disposition'.
    """
    blocking = []
    for a in anomalies:
        if not isinstance(a, dict):
            raise ReviewError("each anomaly must be a dict")
        if "disposition" not in a:
            aid = a.get("id", "<no-id>")
            raise ReviewError(
                f"anomaly '{aid}' is missing a 'disposition' field"
            )
        if a["disposition"] in BLOCKING_DISPOSITIONS:
            blocking.append(a.get("id", "<no-id>"))
    return blocking


def assess_closeout_review(criteria: list, anomalies: list) -> dict:
    """
    Evaluates TCR criteria and anomaly dispositions.

    Returns:
        {
            'outcome': str,
            'open_mandatory': list,
            'open_advisory': list,
            'blocking_anomalies': list,
        }
    Raises:
        ReviewError if criteria or anomalies are structurally invalid.
    """
    _validate_criteria_list(criteria)

    blocking_anomalies = check_open_anomalies(anomalies)

    grouped = categorize_criteria(criteria)
    open_mandatory = [c["name"] for c in grouped[CATEGORY_MANDATORY] if not c["met"]]
    open_advisory = [c["name"] for c in grouped[CATEGORY_ADVISORY] if not c["met"]]

    # Each blocking anomaly is treated as an unmet mandatory criterion.
    effective_mandatory = open_mandatory + [
        f"anomaly:{aid}" for aid in blocking_anomalies
    ]

    return {
        "outcome": _derive_outcome(effective_mandatory, open_advisory),
        "open_mandatory": effective_mandatory,
        "open_advisory": open_advisory,
        "blocking_anomalies": blocking_anomalies,
    }


def validate_review_record(record: dict) -> tuple:
    """
    Checks a review record for completeness.
    Returns (valid: bool, issues: list[str]).
    """
    if not isinstance(record, dict):
        return False, ["record must be a dict"]

    missing = sorted(f for f in REQUIRED_RECORD_FIELDS if f not in record)
    if missing:
        return False, [f"missing fields: {missing}"]

    issues = []
    if record["review_type"] not in VALID_REVIEW_TYPES:
        issues.append(
            f"invalid review_type '{record['review_type']}'; "
            f"must be one of {sorted(VALID_REVIEW_TYPES)}"
        )
    if not isinstance(record["attendees"], list) or len(record["attendees"]) == 0:
        issues.append("'attendees' must be a non-empty list")
    if not isinstance(record["criteria"], list) or len(record["criteria"]) == 0:
        issues.append("'criteria' must be a non-empty list")
    if not isinstance(record["action_items"], list):
        issues.append("'action_items' must be a list")

    return len(issues) == 0, issues


def aggregate_review_status(trr_outcome: str, tcr_outcome: str) -> str:
    """
    Derives overall test-activity status from individual review outcomes.
    Any FAIL propagates; any CONDITIONAL_PASS (with no FAIL) propagates;
    only two PASS verdicts yield an overall PASS.

    Raises:
        ReviewError if either outcome string is not recognised.
    """
    valid_outcomes = {OUTCOME_PASS, OUTCOME_CONDITIONAL, OUTCOME_FAIL}
    for label, o in (("trr_outcome", trr_outcome), ("tcr_outcome", tcr_outcome)):
        if o not in valid_outcomes:
            raise ReviewError(
                f"'{label}' has unknown value '{o}'; "
                f"must be one of {sorted(valid_outcomes)}"
            )

    if OUTCOME_FAIL in (trr_outcome, tcr_outcome):
        return OUTCOME_FAIL
    if OUTCOME_CONDITIONAL in (trr_outcome, tcr_outcome):
        return OUTCOME_CONDITIONAL
    return OUTCOME_PASS
