"""
Equipment mission-specific test evaluation — ECSS-E-ST-10-03C §5.5.6.
Paraphrased procedure; cite ECSS-E-ST-10-03C §5.5.6 as anchor only.
Stdlib only. Offline, deterministic.
"""

MISSION_TEST_TYPES = frozenset({
    "acoustic",    # §5.5.6.1 airborne sound pressure measurement
    "vibration",   # dynamic mission-environment structural response
    "emc",         # electromagnetic compatibility in mission configuration
    "thermal",     # thermal environment representative of mission profile
    "functional",  # functional performance under mission loads
})

LEVEL_ACCEPTANCE = "acceptance"
LEVEL_QUALIFICATION = "qualification"
VALID_LEVELS = frozenset({LEVEL_ACCEPTANCE, LEVEL_QUALIFICATION})

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_INCOMPLETE = "incomplete"
STATUS_ERROR = "error"

_CATEGORY_LABELS = {
    "acoustic":   "Acoustic / Sound Pressure",
    "vibration":  "Dynamic / Vibration",
    "emc":        "Electromagnetic Compatibility",
    "thermal":    "Thermal Environment",
    "functional": "Functional Performance",
}


class MissionTestError(ValueError):
    """Raised when a test record or input value is invalid."""


def validate_test_record(record):
    """
    Verify that a test record dict has all required keys with valid values.
    Raises MissionTestError for any violation; returns None on success.
    """
    required_keys = {"test_id", "test_type", "level", "measured", "limit"}
    missing = required_keys - set(record.keys())
    if missing:
        raise MissionTestError(f"Missing required fields: {sorted(missing)}")
    if record["test_type"] not in MISSION_TEST_TYPES:
        raise MissionTestError(
            f"Unrecognized test type {record['test_type']!r}; "
            f"must be one of {sorted(MISSION_TEST_TYPES)}"
        )
    if record["level"] not in VALID_LEVELS:
        raise MissionTestError(
            f"Invalid test level {record['level']!r}; "
            f"must be one of {sorted(VALID_LEVELS)}"
        )
    if not isinstance(record["measured"], (int, float)):
        raise MissionTestError("'measured' must be a numeric value")
    if not isinstance(record["limit"], (int, float)):
        raise MissionTestError("'limit' must be a numeric value")
    if record["limit"] <= 0:
        raise MissionTestError("'limit' must be a positive number")


def compute_margin(measured, limit, higher_is_worse=True):
    """
    Return the signed margin between a measured value and its limit.

    Positive result = passing margin (measurement on the correct side of limit).
    Negative result = exceedance (measurement on the wrong side of limit).

    higher_is_worse=True  (default): pass when measured <= limit; margin = limit - measured.
    higher_is_worse=False           : pass when measured >= limit; margin = measured - limit.
    """
    if higher_is_worse:
        return limit - measured
    return measured - limit


def evaluate_test_record(record):
    """
    Evaluate a single mission-specific test record against its limit.

    record keys (required): test_id, test_type, level, measured, limit.
    record key  (optional): higher_is_worse (bool, default True).

    Returns a result dict with:
        test_id, test_type, level, status, margin, note.
    Raises MissionTestError when the record is invalid.
    """
    validate_test_record(record)
    higher_is_worse = record.get("higher_is_worse", True)
    margin = compute_margin(record["measured"], record["limit"], higher_is_worse)

    if margin >= 0:
        status = STATUS_PASS
        note = f"Margin {margin:.4f} — within limit"
    else:
        status = STATUS_FAIL
        note = f"Exceedance {abs(margin):.4f} above limit"

    return {
        "test_id":   record["test_id"],
        "test_type": record["test_type"],
        "level":     record["level"],
        "status":    status,
        "margin":    margin,
        "note":      note,
    }


def check_test_completeness(submitted_types, required_types):
    """
    Verify that all required mission-specific test types appear in the campaign.

    submitted_types: iterable of test-type strings actually submitted.
    required_types:  iterable of test-type strings that the specification demands.

    Returns (is_complete: bool, missing_types: sorted list of str).
    """
    submitted = set(submitted_types)
    required = set(required_types)
    missing = sorted(required - submitted)
    return (len(missing) == 0, missing)


def categorize_test(test_type):
    """
    Return a human-readable category label for a mission-specific test type.
    Raises MissionTestError for an unrecognized type.
    """
    if test_type not in _CATEGORY_LABELS:
        raise MissionTestError(
            f"Unrecognized test type {test_type!r}; "
            f"known types: {sorted(_CATEGORY_LABELS)}"
        )
    return _CATEGORY_LABELS[test_type]


def evaluate_sound_pressure(measured_db, limit_db, test_level=LEVEL_ACCEPTANCE):
    """
    Evaluate an airborne sound pressure measurement per ECSS-E-ST-10-03C §5.5.6.1.

    measured_db: overall SPL of the measured acoustic field (dB).
    limit_db:    SPL limit from the test specification (dB).
    test_level:  "acceptance" or "qualification" (informational; does not
                 alter the margin formula — the caller supplies the correct limit).

    Returns (status: str, margin_db: float).
    Raises MissionTestError for non-numeric inputs.
    """
    if not isinstance(measured_db, (int, float)):
        raise MissionTestError("measured_db must be a numeric value")
    if not isinstance(limit_db, (int, float)):
        raise MissionTestError("limit_db must be a numeric value")
    if test_level not in VALID_LEVELS:
        raise MissionTestError(f"Invalid test_level {test_level!r}")

    margin = round(limit_db - measured_db, 6)
    status = STATUS_PASS if margin >= 0 else STATUS_FAIL
    return status, margin


def compile_results(records):
    """
    Evaluate every record in the campaign and return a summary dict.

    Returns:
        total:          int — number of records submitted.
        passed:         int — records that passed.
        failed:         int — records that failed.
        errors:         list of {test_id, error} for records that could not be parsed.
        overall_status: STATUS_PASS | STATUS_FAIL | STATUS_ERROR | STATUS_INCOMPLETE.
        results:        list of per-record result dicts (only for valid records).
    """
    results = []
    errors = []

    for rec in records:
        try:
            results.append(evaluate_test_record(rec))
        except MissionTestError as exc:
            errors.append({"test_id": rec.get("test_id", "?"), "error": str(exc)})

    passed = sum(1 for r in results if r["status"] == STATUS_PASS)
    failed = sum(1 for r in results if r["status"] == STATUS_FAIL)

    if errors:
        overall = STATUS_ERROR
    elif failed > 0:
        overall = STATUS_FAIL
    elif passed > 0:
        overall = STATUS_PASS
    else:
        overall = STATUS_INCOMPLETE

    return {
        "total":          len(records),
        "passed":         passed,
        "failed":         failed,
        "errors":         errors,
        "overall_status": overall,
        "results":        results,
    }
