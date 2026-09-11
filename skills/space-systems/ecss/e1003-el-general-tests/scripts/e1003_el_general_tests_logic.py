"""Deterministic logic for ECSS-E-ST-10-03C §6.5.1 element general tests.

Offline, stdlib-only module backing the e1003-el-general-tests skill leaf:
test-type categorization, measurement limit evaluation, inspection gating
(pre-test and post-test), test-suite completeness check, and element
release-readiness determination for mechanical-functional and
electrical-functional tests at the element level.
"""

MECHANICAL_FUNCTIONAL = "mechanical_functional"
ELECTRICAL_FUNCTIONAL = "electrical_functional"

VALID_TEST_TYPES = frozenset({MECHANICAL_FUNCTIONAL, ELECTRICAL_FUNCTIONAL})

VERDICTS = frozenset(
    {
        "pass",
        "pre_inspection_fail",
        "out_of_limits",
        "post_inspection_fail",
        "not_performed",
    }
)


def categorize_test(test_type: str) -> str:
    """Validate and return the test category for a test item.

    Raises ValueError for any type not in the two recognized families so
    an unrecognized item never silently enters the evaluation path.
    """
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(
            f"unknown test type: {test_type!r}. "
            f"Expected one of {sorted(VALID_TEST_TYPES)}"
        )
    return test_type


def evaluate_measurement(
    value: float, lower_limit: float, upper_limit: float
) -> dict:
    """Check whether a measured value satisfies both acceptance limits.

    Both limits are inclusive. Raises ValueError when lower_limit exceeds
    upper_limit, which would make the acceptance band undefined.
    Returns a new dict; does not mutate any input.
    """
    if lower_limit > upper_limit:
        raise ValueError(
            f"lower_limit ({lower_limit}) must not exceed upper_limit ({upper_limit})"
        )
    within = lower_limit <= value <= upper_limit
    return {
        "value": value,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "within_limits": within,
    }


def evaluate_test_item(record: dict) -> dict:
    """Disposition one test record through the full evaluation chain.

    Required keys: test_id, test_type, pre_inspection_passed,
    measured_value, lower_limit, upper_limit, post_inspection_passed.

    Evaluation gating order:
      1. pre-test inspection — halt with pre_inspection_fail if it failed
      2. measurement limits — flag out_of_limits if outside the band
      3. post-test inspection — flag post_inspection_fail if it failed
      4. pass — only when all three checks are clear

    Returns a new dict; does not mutate the input.
    """
    test_id = record["test_id"]
    test_type = categorize_test(record["test_type"])

    if not record["pre_inspection_passed"]:
        return {
            "test_id": test_id,
            "test_type": test_type,
            "verdict": "pre_inspection_fail",
            "within_limits": None,
        }

    measurement = evaluate_measurement(
        record["measured_value"],
        record["lower_limit"],
        record["upper_limit"],
    )

    if not measurement["within_limits"]:
        return {
            "test_id": test_id,
            "test_type": test_type,
            "verdict": "out_of_limits",
            "within_limits": False,
        }

    if not record["post_inspection_passed"]:
        return {
            "test_id": test_id,
            "test_type": test_type,
            "verdict": "post_inspection_fail",
            "within_limits": True,
        }

    return {
        "test_id": test_id,
        "test_type": test_type,
        "verdict": "pass",
        "within_limits": True,
    }


def evaluate_test_suite(records: list) -> list:
    """Disposition every test record, in input order."""
    return [evaluate_test_item(record) for record in records]


def find_missing_required_tests(
    required_test_ids: list, results: list
) -> list:
    """Required test identifiers that have no result entry.

    A required test with no result is open — it is neither a pass nor a
    failure and must be dispositioned before element release. Returns a
    sorted list for a deterministic result.
    """
    performed_ids = {result["test_id"] for result in results}
    return sorted(tid for tid in required_test_ids if tid not in performed_ids)


def determine_element_release_readiness(
    required_test_ids: list, results: list
) -> tuple:
    """Go/no-go for releasing the element to integration.

    Returns (ready, missing_tests, failed_items):
      ready         -- True only when no required test is missing and
                       every result verdict is "pass"
      missing_tests -- sorted list of required test IDs with no result
      failed_items  -- list of {test_id, verdict} for every non-pass result,
                       in the order they appear in results

    An element with any missing test or any non-pass verdict is not ready.
    """
    missing_tests = find_missing_required_tests(required_test_ids, results)
    failed_items = [
        {"test_id": r["test_id"], "verdict": r["verdict"]}
        for r in results
        if r["verdict"] != "pass"
    ]
    ready = not missing_tests and not failed_items
    return (ready, missing_tests, failed_items)
