"""Deterministic logic for ECSS-E-ST-10-03C 5.5.5 equipment electrical/RF tests.

Offline, stdlib-only module backing the e1003-eq-electrical skill leaf:
determining which of the six electrical/RF tests (EMC, magnetic, ESD,
passive intermodulation, multipactor, corona/arc discharge) apply to a
given equipment item, dispositioning each applicable test's status,
rolling up one equipment item's overall electrical/RF test status, and
building the campaign disposition across a set of equipment items.
"""

TEST_TYPES = frozenset(
    {"emc", "magnetic", "esd", "pim", "multipactor", "corona_arc"}
)

RESULT_VALUES = frozenset({"passed", "failed"})

TEST_STATUSES = frozenset({"not_applicable", "missing", "passed", "failed"})

OVERALL_STATUSES = frozenset({"complete", "incomplete", "failed"})


def determine_applicability(equipment: dict) -> dict:
    """Which of the six 5.5.5 tests apply to this equipment item.

    Equipment with no electrical interfaces is out of scope for the
    entire set. Otherwise EMC is always applicable; the remaining five
    each follow their own risk/requirement flag on the equipment dict:
    magnetic_cleanliness_required, esd_susceptible, pim_risk_present,
    multipactor_risk_present, corona_arc_risk_present.
    """
    if not equipment.get("has_electrical_interfaces"):
        return {test: False for test in TEST_TYPES}

    return {
        "emc": True,
        "magnetic": bool(equipment.get("magnetic_cleanliness_required")),
        "esd": bool(equipment.get("esd_susceptible")),
        "pim": bool(equipment.get("pim_risk_present")),
        "multipactor": bool(equipment.get("multipactor_risk_present")),
        "corona_arc": bool(equipment.get("corona_arc_risk_present")),
    }


def test_status(applicable: bool, result) -> str:
    """Status for one test given its applicability and recorded result.

    Returns 'not_applicable' when the test is out of scope, 'missing'
    when it is applicable but has no recorded result yet, otherwise
    the result itself ('passed' or 'failed'). Raises ValueError for a
    result outside RESULT_VALUES.
    """
    if not applicable:
        return "not_applicable"
    if result is None:
        return "missing"
    if result not in RESULT_VALUES:
        raise ValueError(f"unknown test result: {result!r}")
    return result


def roll_up_overall_status(statuses: dict) -> str:
    """Overall electrical/RF status for one equipment item.

    'failed' if any applicable test failed (checked first -- a single
    failure fails the equipment item regardless of other results),
    'incomplete' if none failed but at least one applicable test is
    still missing, 'complete' only when every applicable test passed.
    """
    values = statuses.values()
    if "failed" in values:
        return "failed"
    if "missing" in values:
        return "incomplete"
    return "complete"


def disposition_equipment(equipment: dict, results: dict) -> dict:
    """Electrical/RF test disposition for one equipment dict.

    Required equipment key: id. results maps test type to 'passed' or
    'failed' for tests that have a recorded outcome; tests not yet run
    should be absent from results (or mapped to None). Returns a new
    dict; does not mutate the inputs. Raises ValueError if 'id' is
    missing.
    """
    if "id" not in equipment:
        raise ValueError("equipment is missing an id")

    applicability = determine_applicability(equipment)
    statuses = {
        test: test_status(applicability[test], results.get(test))
        for test in TEST_TYPES
    }
    overall = roll_up_overall_status(statuses)
    return {"id": equipment["id"], "tests": statuses, "overall": overall}


def build_campaign_disposition(equipment_list: list, results_by_id: dict) -> list:
    """Disposition for every equipment item, in input order.

    results_by_id maps equipment id to its results dict (missing ids
    are treated as no recorded results at all). Raises ValueError on a
    duplicate equipment id.
    """
    dispositions = []
    seen_ids = set()
    for equipment in equipment_list:
        results = results_by_id.get(equipment.get("id"), {})
        result = disposition_equipment(equipment, results)
        if result["id"] in seen_ids:
            raise ValueError(f"duplicate equipment id: {result['id']!r}")
        seen_ids.add(result["id"])
        dispositions.append(result)
    return dispositions


def missing_dispositions(all_equipment_ids: list, dispositions: list) -> list:
    """Equipment ids expected in the campaign scope but absent from
    dispositions, in all_equipment_ids order -- a campaign closure
    cannot claim completeness while an intended equipment item was
    never dispositioned.
    """
    dispositioned_ids = {entry["id"] for entry in dispositions}
    return [eid for eid in all_equipment_ids if eid not in dispositioned_ids]


def close_out_campaign(dispositions: list) -> tuple:
    """Campaign closure verdict across a set of equipment dispositions.

    Returns (all_complete, open_items): all_complete is True only when
    every disposition's overall status is 'complete'; open_items lists
    the id/overall pairs still blocking closure, in input order.
    """
    open_items = [
        {"id": entry["id"], "overall": entry["overall"]}
        for entry in dispositions
        if entry["overall"] != "complete"
    ]
    return (len(open_items) == 0, open_items)
