#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.4 test stimulus point accessibility
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires that the
stimulus and measurement points needed to verify an equipment item be
reachable during test without changing the electrical configuration of
the unit under test. Access that breaks a flight interface (demating a
flight connector, cutting or splicing a wire, tapping a solder lug,
lifting a board-level component) changes the very configuration the
test is meant to characterize, so the provision must be a dedicated,
non-intrusive one. Reaching a node is also not the same as measuring
it correctly: the probing instrument loads the node through the source
impedance, and a point connected to a node whose failure would hurt
the mission needs a series isolation element so a short or overload on
the test side cannot propagate inward.

This module implements access-method categorization, instrument
loading-error accounting against an allowable, minimum instrument
input impedance derivation, series-isolation adequacy per node
criticality, stimulus coverage of the verification plan, and the
aggregated per-point and per-equipment review. It does not define the
verification plan itself, the instrument calibration chain, or any
connector qualification requirement.
"""

# Access provisions that leave the flight electrical configuration
# intact while the point is being driven or observed.
NON_INTRUSIVE_ACCESS_METHODS = frozenset(
    {
        "dedicated_test_connector",
        "buffered_monitor_pin",
        "harness_breakout_box",
        "bench_test_adapter",
    }
)

# Access provisions that reach the node only by breaking, bypassing or
# rebuilding part of the flight electrical configuration.
INTRUSIVE_ACCESS_METHODS = frozenset(
    {
        "connector_demate",
        "wire_cut_splice",
        "solder_lug_tap",
        "board_probe_removal",
    }
)

# Minimum series isolation (ohm) required between a test point and the
# node it observes, by the consequence of a fault propagating inward
# from the test equipment.
MIN_SERIES_ISOLATION_OHM = {
    "routine": 0.0,
    "mission_critical": 1000.0,
    "catastrophic": 10000.0,
}

_REQUIRED_POINT_KEYS = (
    "point_id",
    "access_method",
    "node_criticality",
    "source_impedance_ohm",
    "instrument_input_impedance_ohm",
    "allowable_loading_error_percent",
    "series_isolation_ohm",
)


def _require_keys(mapping, keys, what):
    """Raise ValueError naming the first missing key of a record."""
    for key in keys:
        if key not in mapping:
            raise ValueError("%s record is missing required key %r" % (what, key))


def categorize_access_method(access_method):
    """Access category for a test-point provision: "non_intrusive" or
    "intrusive". Raises ValueError for a provision outside both known
    sets -- an unrecognized access method cannot be assessed against
    clause 4.2.4 and must not be silently accepted."""
    if access_method in NON_INTRUSIVE_ACCESS_METHODS:
        return "non_intrusive"
    if access_method in INTRUSIVE_ACCESS_METHODS:
        return "intrusive"
    raise ValueError(
        "unrecognized test point access method %r under "
        "E-ST-20C clause 4.2.4" % (access_method,)
    )


def loading_error_percent(source_impedance_ohm, instrument_input_impedance_ohm):
    """Fractional measurement error, in percent, introduced by loading a
    node of source impedance Zs with an instrument of input impedance
    Zin: 100 * Zs / (Zs + Zin). Raises ValueError for a negative source
    impedance or a non-positive input impedance (a zero input impedance
    is a short across the node, not a measurement)."""
    if source_impedance_ohm < 0:
        raise ValueError("source_impedance_ohm must be >= 0")
    if instrument_input_impedance_ohm <= 0:
        raise ValueError("instrument_input_impedance_ohm must be > 0")
    return 100.0 * source_impedance_ohm / (
        source_impedance_ohm + instrument_input_impedance_ohm
    )


def required_input_impedance_ohm(source_impedance_ohm, allowable_loading_error_percent):
    """Minimum instrument input impedance (ohm) that holds the loading
    error at or below the allowable: Zs * (100 - e) / e. Returns 0.0 for
    a source impedance of zero (an ideal source cannot be loaded).
    Raises ValueError for a negative source impedance or an allowable
    outside the open interval (0, 100)."""
    if source_impedance_ohm < 0:
        raise ValueError("source_impedance_ohm must be >= 0")
    if not 0 < allowable_loading_error_percent < 100:
        raise ValueError(
            "allowable_loading_error_percent must be > 0 and < 100"
        )
    return (
        source_impedance_ohm
        * (100.0 - allowable_loading_error_percent)
        / allowable_loading_error_percent
    )


def access_findings(point_id, access_method, requires_flight_connector_demate):
    """Finding list (empty when compliant) for the accessibility of one
    point. An intrusive provision alters the electrical configuration of
    the unit under test; a provision that is nominally non-intrusive but
    still needs a flight connector demated to reach the point is the
    same defect arriving by a different route, and both are reported."""
    findings = []
    if categorize_access_method(access_method) == "intrusive":
        findings.append(
            {
                "issue": "access_alters_electrical_configuration",
                "point": point_id,
                "access_method": access_method,
            }
        )
    if requires_flight_connector_demate:
        findings.append(
            {
                "issue": "flight_connector_demate_required_for_access",
                "point": point_id,
            }
        )
    return findings


def loading_findings(
    point_id,
    source_impedance_ohm,
    instrument_input_impedance_ohm,
    allowable_loading_error_percent,
):
    """Finding list (empty when compliant) for the loading a probing
    instrument imposes on one point. Reports the computed error and the
    minimum input impedance that would have met the allowable."""
    error = loading_error_percent(
        source_impedance_ohm, instrument_input_impedance_ohm
    )
    if error <= allowable_loading_error_percent:
        return []
    return [
        {
            "issue": "instrument_loading_error_exceeded",
            "point": point_id,
            "loading_error_percent": error,
            "allowable_percent": allowable_loading_error_percent,
            "required_input_impedance_ohm": required_input_impedance_ohm(
                source_impedance_ohm, allowable_loading_error_percent
            ),
        }
    ]


def isolation_findings(point_id, node_criticality, series_isolation_ohm):
    """Finding list (empty when compliant) for the series isolation
    between a test point and the node it observes. Raises ValueError for
    an unrecognized criticality or a negative isolation value."""
    if node_criticality not in MIN_SERIES_ISOLATION_OHM:
        raise ValueError("unrecognized node criticality %r" % (node_criticality,))
    if series_isolation_ohm < 0:
        raise ValueError("series_isolation_ohm must be >= 0")
    minimum = MIN_SERIES_ISOLATION_OHM[node_criticality]
    if series_isolation_ohm >= minimum:
        return []
    return [
        {
            "issue": "insufficient_test_point_series_isolation",
            "point": point_id,
            "series_isolation_ohm": series_isolation_ohm,
            "required_isolation_ohm": minimum,
        }
    ]


def stimulus_coverage_findings(required_stimuli, points):
    """Finding list (empty when complete) for the mapping between the
    stimulus and measurement signals the verification plan demands and
    the points actually provided. A point covers a signal only when it
    is non-intrusive and reachable in the integrated configuration, so a
    signal reachable solely through an intrusive provision counts as
    uncovered. Raises ValueError if a point record lacks the keys needed
    to judge coverage."""
    covered = set()
    for point in points:
        _require_keys(
            point,
            ("point_id", "access_method", "signals"),
            "test point",
        )
        if categorize_access_method(point["access_method"]) != "non_intrusive":
            continue
        if point.get("requires_flight_connector_demate"):
            continue
        covered.update(point["signals"])
    return [
        {"issue": "stimulus_signal_without_accessible_point", "signal": signal}
        for signal in sorted(set(required_stimuli) - covered)
    ]


def review_test_point(point):
    """Full clause 4.2.4 review of one test point.

    point: mapping with point_id, access_method, node_criticality,
    source_impedance_ohm, instrument_input_impedance_ohm,
    allowable_loading_error_percent, series_isolation_ohm and the
    optional requires_flight_connector_demate flag. Returns
    {"access": [...], "loading": [...], "isolation": [...]}, each a
    finding list. Raises ValueError for a missing key, an unrecognized
    access method or criticality, or an out-of-range impedance."""
    _require_keys(point, _REQUIRED_POINT_KEYS, "test point")
    point_id = point["point_id"]
    return {
        "access": access_findings(
            point_id,
            point["access_method"],
            point.get("requires_flight_connector_demate", False),
        ),
        "loading": loading_findings(
            point_id,
            point["source_impedance_ohm"],
            point["instrument_input_impedance_ohm"],
            point["allowable_loading_error_percent"],
        ),
        "isolation": isolation_findings(
            point_id,
            point["node_criticality"],
            point["series_isolation_ohm"],
        ),
    }


def review_equipment(equipment):
    """Clause 4.2.4 review of one equipment item: the per-point reviews
    keyed by point id, plus the coverage findings for the stimulus and
    measurement signals its verification plan requires.

    equipment: {"equipment_id": str, "test_points": [point, ...],
    "required_stimuli": [signal, ...]}. Raises ValueError for a missing
    key or a duplicate point id."""
    _require_keys(equipment, ("equipment_id", "test_points"), "equipment")
    points = equipment["test_points"]
    reviews = {}
    for point in points:
        _require_keys(point, ("point_id",), "test point")
        if point["point_id"] in reviews:
            raise ValueError("duplicate test point id %r" % (point["point_id"],))
        reviews[point["point_id"]] = review_test_point(point)
    return {
        "equipment_id": equipment["equipment_id"],
        "points": reviews,
        "coverage": stimulus_coverage_findings(
            equipment.get("required_stimuli", ()), points
        ),
    }


def is_test_point_compliant(review):
    """True when every finding list in a review_test_point result is
    empty -- the point satisfies clause 4.2.4 for this assessment."""
    return all(len(findings) == 0 for findings in review.values())


def is_equipment_compliant(equipment_review):
    """True when every point review is compliant and no required
    stimulus signal is left without an accessible point."""
    if equipment_review["coverage"]:
        return False
    return all(
        is_test_point_compliant(review)
        for review in equipment_review["points"].values()
    )
