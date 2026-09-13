#!/usr/bin/env python3
"""Contract test for the post-cycling substrate integrity survey (offline).

This is the gate 3 behaviour contract: every workflow step of the leaf
(policy validation, sequencing readiness, zone and method coverage,
indication capture and the completeness verdict) is exercised here,
including the refusals that stop an unusable survey reaching the
disposition step.
"""

import copy
import unittest

from e2008_substrate_integrity_inspection_process_logic import (
    DEFAULT_INSPECTION_POLICY,
    INDICATION_KINDS,
    INSPECTION_COMPLETE,
    INSPECTION_INCOMPLETE,
    INSPECTION_INVALID,
    INSPECTION_METHODS,
    SUBSTRATE_ZONES,
    check_readiness,
    normalise_indication,
    run_substrate_integrity_inspection,
    summarise_indications,
    validate_inspection_policy,
    zone_coverage,
)

READY_STATE = {
    "coupon_id": "K1",
    "required_cycles": 200,
    "credited_cycles": 200,
    "hours_since_cycling_end": 6.0,
}

FULL_COVERAGE = {
    "front-facesheet": ["visual"],
    "rear-facesheet": ["visual"],
    "honeycomb-core": ["ultrasonic"],
    "facesheet-core-bondline": ["tap-test", "ultrasonic"],
    "edge-closeout": ["visual"],
    "insert-region": ["tap-test", "ultrasonic"],
}

DISBOND = {
    "indication_id": "I1",
    "kind": "facesheet-core-disbond",
    "zone": "facesheet-core-bondline",
    "method": "ultrasonic",
    "size_mm": 8.0,
    "area_mm2": 50.0,
}


def _state(**overrides):
    state = dict(READY_STATE)
    state.update(overrides)
    return state


def _coverage(**overrides):
    coverage = copy.deepcopy(FULL_COVERAGE)
    coverage.update(overrides)
    return coverage


def _indication(**overrides):
    indication = dict(DISBOND)
    indication.update(overrides)
    return indication


def _case(**overrides):
    case = {
        "coupon_state": _state(),
        "applied_methods": _coverage(),
        "indications": [_indication()],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_inspection_policy(DEFAULT_INSPECTION_POLICY),
            DEFAULT_INSPECTION_POLICY,
        )

    def test_every_required_zone_has_admissible_methods(self):
        for zone in DEFAULT_INSPECTION_POLICY["required_zones"]:
            self.assertIn(zone, DEFAULT_INSPECTION_POLICY["admissible_methods"])
            self.assertTrue(DEFAULT_INSPECTION_POLICY["admissible_methods"][zone])

    def test_every_method_carries_a_detection_threshold(self):
        for method in INSPECTION_METHODS:
            self.assertIn(
                method, DEFAULT_INSPECTION_POLICY["method_detection_threshold_mm"]
            )

    def test_subsurface_zones_demand_corroboration(self):
        self.assertGreater(
            DEFAULT_INSPECTION_POLICY["minimum_methods_per_zone"][
                "facesheet-core-bondline"
            ],
            1,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_policy("default")

    def test_policy_with_an_unknown_zone_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        broken["required_zones"] = tuple(broken["required_zones"]) + ("radiator-fin",)
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)

    def test_zone_demanding_more_methods_than_exist_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        broken["minimum_methods_per_zone"]["honeycomb-core"] = 5
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)

    def test_delay_window_inside_the_stabilisation_period_rejected(self):
        broken = copy.deepcopy(DEFAULT_INSPECTION_POLICY)
        broken["maximum_delay_h"] = 1.0
        with self.assertRaises(ValueError):
            validate_inspection_policy(broken)


class ReadinessTests(unittest.TestCase):
    def test_settled_coupon_is_ready(self):
        result = check_readiness(_state())
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])

    def test_survey_before_cycling_completes_is_refused(self):
        with self.assertRaises(ValueError):
            check_readiness(_state(credited_cycles=150))

    def test_survey_inside_the_stabilisation_period_is_not_ready(self):
        result = check_readiness(_state(hours_since_cycling_end=0.5))
        self.assertFalse(result["ready"])

    def test_survey_exactly_on_the_stabilisation_bound_is_ready(self):
        result = check_readiness(
            _state(
                hours_since_cycling_end=DEFAULT_INSPECTION_POLICY[
                    "minimum_stabilisation_h"
                ]
            )
        )
        self.assertTrue(result["ready"])

    def test_survey_past_the_window_stays_ready_but_is_flagged(self):
        result = check_readiness(_state(hours_since_cycling_end=200.0))
        self.assertTrue(result["ready"])
        self.assertTrue(any("window" in note for note in result["findings"]))

    def test_survey_exactly_on_the_window_bound_is_not_flagged(self):
        result = check_readiness(
            _state(hours_since_cycling_end=DEFAULT_INSPECTION_POLICY["maximum_delay_h"])
        )
        self.assertEqual(result["findings"], [])

    def test_negative_elapsed_time_rejected(self):
        with self.assertRaises(ValueError):
            check_readiness(_state(hours_since_cycling_end=-3.0))

    def test_missing_coupon_identifier_rejected(self):
        state = _state()
        del state["coupon_id"]
        with self.assertRaises(ValueError):
            check_readiness(state)


class CoverageTests(unittest.TestCase):
    def test_full_coverage_covers_every_required_zone(self):
        result = zone_coverage(_coverage())
        self.assertEqual(result["uncovered_zones"], [])
        self.assertEqual(result["under_covered_zones"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_unsurveyed_zone_is_uncovered(self):
        coverage = _coverage()
        del coverage["honeycomb-core"]
        result = zone_coverage(coverage)
        self.assertIn("honeycomb-core", result["uncovered_zones"])

    def test_bondline_surveyed_by_eye_alone_is_uncovered(self):
        result = zone_coverage(_coverage(**{"facesheet-core-bondline": ["visual"]}))
        self.assertIn("facesheet-core-bondline", result["uncovered_zones"])
        self.assertTrue(result["inadmissible_applications"])

    def test_one_method_where_two_are_owed_is_under_covered(self):
        result = zone_coverage(_coverage(**{"insert-region": ["tap-test"]}))
        zones = [entry["zone"] for entry in result["under_covered_zones"]]
        self.assertIn("insert-region", zones)

    def test_coverage_fraction_counts_only_fully_covered_zones(self):
        coverage = _coverage()
        del coverage["front-facesheet"]
        del coverage["rear-facesheet"]
        result = zone_coverage(coverage)
        self.assertAlmostEqual(result["coverage_fraction"], 4.0 / 6.0, places=9)

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_coverage(_coverage(**{"radiator-fin": ["visual"]}))

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            zone_coverage(_coverage(**{"front-facesheet": ["taste-test"]}))

    def test_method_listed_twice_for_one_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_coverage(_coverage(**{"front-facesheet": ["visual", "visual"]}))

    def test_non_mapping_application_rejected(self):
        with self.assertRaises(ValueError):
            zone_coverage(["visual"])


class IndicationTests(unittest.TestCase):
    def test_indication_from_an_admissible_method_is_confirmed(self):
        record = normalise_indication(_indication())
        self.assertTrue(record["confirmed"])
        self.assertAlmostEqual(record["size_mm"], 8.0, places=9)

    def test_indication_from_an_inadmissible_method_is_unconfirmed(self):
        record = normalise_indication(
            _indication(zone="honeycomb-core", method="visual", size_mm=4.0)
        )
        self.assertFalse(record["confirmed"])

    def test_size_below_the_method_detection_threshold_rejected(self):
        with self.assertRaises(ValueError):
            normalise_indication(_indication(method="tap-test", size_mm=1.0))

    def test_size_exactly_on_the_detection_threshold_accepted(self):
        record = normalise_indication(_indication(method="ultrasonic", size_mm=2.0))
        self.assertAlmostEqual(record["size_mm"], 2.0, places=9)

    def test_zero_size_rejected(self):
        with self.assertRaises(ValueError):
            normalise_indication(_indication(size_mm=0.0))

    def test_unknown_indication_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalise_indication(_indication(kind="paint-blister"))

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            normalise_indication(_indication(area_mm2=-1.0))

    def test_missing_indication_identifier_rejected(self):
        indication = _indication()
        del indication["indication_id"]
        with self.assertRaises(ValueError):
            normalise_indication(indication)

    def test_every_declared_kind_is_accepted_somewhere(self):
        for kind in INDICATION_KINDS:
            record = normalise_indication(_indication(kind=kind))
            self.assertEqual(record["kind"], kind)


class SummaryTests(unittest.TestCase):
    def test_summary_groups_by_zone_and_kind(self):
        summary = summarise_indications(
            [
                _indication(),
                _indication(
                    indication_id="I2",
                    kind="core-crush",
                    zone="honeycomb-core",
                    method="ultrasonic",
                    size_mm=4.0,
                    area_mm2=10.0,
                ),
            ]
        )
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["by_kind"]["core-crush"], 1)
        self.assertEqual(summary["by_zone"]["facesheet-core-bondline"], 1)

    def test_summary_totals_area_and_takes_the_largest_size(self):
        summary = summarise_indications(
            [_indication(), _indication(indication_id="I2", size_mm=12.0, area_mm2=30.0)]
        )
        self.assertAlmostEqual(summary["total_area_mm2"], 80.0, places=9)
        self.assertAlmostEqual(summary["largest_size_mm"], 12.0, places=9)

    def test_indication_without_area_does_not_break_the_total(self):
        summary = summarise_indications([_indication(area_mm2=None)])
        self.assertAlmostEqual(summary["total_area_mm2"], 0.0, places=9)

    def test_duplicate_indication_identifier_rejected(self):
        with self.assertRaises(ValueError):
            summarise_indications([_indication(), _indication()])

    def test_empty_survey_summarises_to_nothing(self):
        summary = summarise_indications([])
        self.assertEqual(summary["count"], 0)
        self.assertEqual(summary["unconfirmed"], [])

    def test_non_list_survey_rejected(self):
        with self.assertRaises(ValueError):
            summarise_indications({"indication_id": "I1"})


class InspectionRunTests(unittest.TestCase):
    def test_covered_settled_survey_is_complete(self):
        result = run_substrate_integrity_inspection(_case())
        self.assertEqual(result["verdict"], INSPECTION_COMPLETE)
        self.assertTrue(result["disposition_deferred"])

    def test_survey_inside_the_stabilisation_period_is_invalid(self):
        result = run_substrate_integrity_inspection(
            _case(coupon_state=_state(hours_since_cycling_end=0.25))
        )
        self.assertEqual(result["verdict"], INSPECTION_INVALID)

    def test_missing_zone_leaves_the_survey_incomplete(self):
        coverage = _coverage()
        del coverage["edge-closeout"]
        result = run_substrate_integrity_inspection(_case(applied_methods=coverage))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertTrue(any("edge-closeout" in note for note in result["findings"]))

    def test_unconfirmed_indication_leaves_the_survey_incomplete(self):
        result = run_substrate_integrity_inspection(
            _case(
                indications=[
                    _indication(
                        indication_id="I9",
                        zone="honeycomb-core",
                        kind="core-crush",
                        method="visual",
                        size_mm=3.0,
                    )
                ]
            )
        )
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)

    def test_a_clean_survey_says_so_rather_than_staying_silent(self):
        result = run_substrate_integrity_inspection(_case(indications=[]))
        self.assertEqual(result["verdict"], INSPECTION_COMPLETE)
        self.assertTrue(any("no indications" in note for note in result["findings"]))

    def test_invalid_sequence_outranks_a_coverage_gap(self):
        coverage = _coverage()
        del coverage["edge-closeout"]
        result = run_substrate_integrity_inspection(
            _case(
                coupon_state=_state(hours_since_cycling_end=0.1),
                applied_methods=coverage,
            )
        )
        self.assertEqual(result["verdict"], INSPECTION_INVALID)

    def test_survey_never_returns_an_accept_or_reject(self):
        result = run_substrate_integrity_inspection(_case())
        self.assertNotIn("accept", result)
        self.assertNotIn("reject", result)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            run_substrate_integrity_inspection(["K1"])

    def test_every_declared_zone_name_is_usable(self):
        for zone in SUBSTRATE_ZONES:
            self.assertIn(zone, DEFAULT_INSPECTION_POLICY["admissible_methods"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
