"""Deterministic logic for ECSS-E-ST-10-03C 5.3 equipment acceptance
test baseline (Tables 5-3/5-4).

Offline, stdlib-only module backing the e1003-eq-acceptance skill
leaf: deriving per-test-type acceptance levels and durations from an
equipment's qualification baseline (sibling e1003-eq-qual leaf) and
its margin/duration reduction rules, guarding against a derived
acceptance value that fails to sit below its qualification
counterpart, and checking the baseline for test-type coverage gaps
before release. Uses the same test-path vocabulary as the sibling
e1003-objectives leaf (acceptance vs protoflight).
"""

TEST_PATHS = frozenset({"acceptance", "protoflight"})

STATUSES = frozenset({"ok", "flagged_level_not_reduced", "flagged_duration_exceeds_qualification"})


def check_test_path(test_path: str) -> bool:
    """Gate: this leaf's baseline only applies to the acceptance path.

    Equipment on the protoflight path is covered by the protoflight
    test baseline (sibling e1003-eq-protoflight leaf) instead of a
    separate acceptance campaign.
    """
    if test_path not in TEST_PATHS:
        raise ValueError(f"unknown test path: {test_path!r}")
    return test_path == "acceptance"


def derive_acceptance_level(qualification_level: float, margin_factor: float) -> float:
    """Acceptance level derived from the qualification level.

    margin_factor is how much the qualification level exceeds the
    acceptance (flight-limit) level for this test type; it must be
    greater than 1, since qualification always carries a margin above
    the level the acceptance test is run at.
    """
    if margin_factor <= 1:
        raise ValueError(f"margin_factor must be > 1, got {margin_factor!r}")
    return qualification_level / margin_factor


def derive_acceptance_duration(qualification_duration: float, duration_factor: float) -> float:
    """Acceptance duration/cycle-count derived from the qualification value.

    duration_factor is the fraction of the qualification duration used
    for acceptance; it must be in (0, 1], since the acceptance test
    only needs to precipitate workmanship defects, not demonstrate
    life margin over the full qualification duration.
    """
    if not 0 < duration_factor <= 1:
        raise ValueError(f"duration_factor must be in (0, 1], got {duration_factor!r}")
    return qualification_duration * duration_factor


def check_level_consistency(acceptance_level: float, qualification_level: float) -> bool:
    """True when the acceptance level sits strictly below qualification."""
    return acceptance_level < qualification_level


def check_duration_consistency(acceptance_duration: float, qualification_duration: float) -> bool:
    """True when the acceptance duration does not exceed qualification."""
    return acceptance_duration <= qualification_duration


def define_test_baseline(test: dict) -> dict:
    """Acceptance baseline entry for one test type dict.

    Required keys: test_type, qualification_level, qualification_duration,
    margin_factor, duration_factor. Derives the acceptance level and
    duration, then validates both against their qualification
    counterparts. Returns a new dict; does not mutate the input.
    Raises ValueError if 'test_type' is missing.
    """
    if "test_type" not in test:
        raise ValueError("test is missing a test_type")

    acceptance_level = derive_acceptance_level(
        test["qualification_level"], test["margin_factor"]
    )
    acceptance_duration = derive_acceptance_duration(
        test["qualification_duration"], test["duration_factor"]
    )

    if not check_level_consistency(acceptance_level, test["qualification_level"]):
        status = "flagged_level_not_reduced"
    elif not check_duration_consistency(acceptance_duration, test["qualification_duration"]):
        status = "flagged_duration_exceeds_qualification"
    else:
        status = "ok"

    return {
        "test_type": test["test_type"],
        "acceptance_level": acceptance_level,
        "acceptance_duration": acceptance_duration,
        "status": status,
    }


def build_equipment_acceptance_baseline(test_path: str, tests: list) -> list:
    """Baseline entries for every test type, in input order.

    Raises ValueError if the equipment is not on the acceptance test
    path (see check_test_path), or on a duplicate test_type.
    """
    if not check_test_path(test_path):
        raise ValueError(
            "equipment is not on the acceptance test path; "
            "use the e1003-eq-protoflight baseline instead"
        )

    entries = []
    seen_types = set()
    for test in tests:
        entry = define_test_baseline(test)
        if entry["test_type"] in seen_types:
            raise ValueError(f"duplicate test_type: {entry['test_type']!r}")
        seen_types.add(entry["test_type"])
        entries.append(entry)
    return entries


def missing_test_types(required_test_types: list, entries: list) -> list:
    """Test types expected in the baseline but absent from entries,
    in required_test_types order -- a baseline cannot be released
    while a mandatory test type was never defined.
    """
    defined_types = {entry["test_type"] for entry in entries}
    return [t for t in required_test_types if t not in defined_types]


def close_out_acceptance_baseline(required_test_types: list, entries: list) -> tuple:
    """Baseline-release verdict across a set of entries.

    Returns (ready_for_release, open_items): ready_for_release is True
    only when every required test type is present and every entry has
    status 'ok'; open_items lists missing test types and flagged
    entries (test_type/status pairs), in a stable order: missing types
    first (in required_test_types order), then flagged entries (in
    entries order).
    """
    missing = missing_test_types(required_test_types, entries)
    open_items = [{"test_type": t, "status": "missing"} for t in missing]
    open_items.extend(
        {"test_type": entry["test_type"], "status": entry["status"]}
        for entry in entries
        if entry["status"] != "ok"
    )
    return (len(open_items) == 0, open_items)
