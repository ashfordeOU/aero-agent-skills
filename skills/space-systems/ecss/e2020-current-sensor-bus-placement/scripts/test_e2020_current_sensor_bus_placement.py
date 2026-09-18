#!/usr/bin/env python3
"""Contract test for the current sensor bus placement leaf (offline)."""

import copy
import unittest

from e2020_current_sensor_bus_placement_logic import (
    ORIGINS,
    ORIGIN_DEVICE_INTERNAL,
    ORIGIN_LOAD,
    ORIGIN_UPSTREAM_STUB,
    POSITION_AFTER_SWITCH,
    POSITION_BUS_INTERFACE,
    RETURN_ROUTES,
    RETURN_VIA_BUS,
    RETURN_VIA_CHASSIS_BOND,
    RETURN_VIA_STRUCTURE,
    SENSOR_PLACEMENT_COMPLIANT,
    SENSOR_PLACEMENT_NON_COMPLIANT,
    SENSOR_RAIL_ENERGISED,
    SENSOR_RAIL_RETURN,
    assess_sensor_placement,
    effective_trip_current_a,
    harness_margin_fraction,
    measurement_band_a,
    path_is_sensed,
    sensed_current_a,
    sensed_fraction,
    total_current_a,
    unsensed_paths,
    validate_path,
    validate_paths,
    validate_sensor_placement,
)

LOAD_PATH = {
    "id": "unit-load-draw",
    "originates_at": ORIGIN_LOAD,
    "returns_via": RETURN_VIA_BUS,
    "current_a": 3.0,
}
HOUSEKEEPING_PATH = {
    "id": "device-housekeeping",
    "originates_at": ORIGIN_DEVICE_INTERNAL,
    "returns_via": RETURN_VIA_BUS,
    "current_a": 0.25,
}
STRUCTURE_FAULT_PATH = {
    "id": "load-short-to-structure",
    "originates_at": ORIGIN_LOAD,
    "returns_via": RETURN_VIA_STRUCTURE,
    "current_a": 1.75,
    "is_fault": True,
}

HEALTHY_PATHS = [copy.deepcopy(LOAD_PATH), copy.deepcopy(HOUSEKEEPING_PATH)]
FAULTED_PATHS = [
    copy.deepcopy(LOAD_PATH),
    copy.deepcopy(HOUSEKEEPING_PATH),
    copy.deepcopy(STRUCTURE_FAULT_PATH),
]


def _case(**overrides):
    case = {
        "sensor_rail": SENSOR_RAIL_ENERGISED,
        "sensor_position": POSITION_BUS_INTERFACE,
        "current_paths": copy.deepcopy(HEALTHY_PATHS),
        "trip_threshold_a": 5.0,
        "harness_rating_a": 8.0,
        "nominal_load_current_a": 3.25,
        "sensor_accuracy_fraction": 0.02,
    }
    case.update(overrides)
    return case


class PlacementVocabularyTests(unittest.TestCase):
    def test_the_two_rails_are_the_only_accepted_rails(self):
        self.assertEqual(
            validate_sensor_placement(SENSOR_RAIL_ENERGISED, POSITION_BUS_INTERFACE),
            (SENSOR_RAIL_ENERGISED, POSITION_BUS_INTERFACE),
        )
        with self.assertRaises(ValueError):
            validate_sensor_placement("middle", POSITION_BUS_INTERFACE)

    def test_an_unknown_position_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sensor_placement(SENSOR_RAIL_ENERGISED, "somewhere-inside")

    def test_the_origin_and_route_vocabularies_are_disjoint(self):
        self.assertEqual(set(ORIGINS) & set(RETURN_ROUTES), set())


class PathValidationTests(unittest.TestCase):
    def test_a_well_formed_path_is_normalised(self):
        item = validate_path(LOAD_PATH)
        self.assertEqual(item["id"], "unit-load-draw")
        self.assertFalse(item["is_fault"])

    def test_a_path_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            validate_path("unit-load-draw")

    def test_a_path_with_an_unknown_origin_is_refused(self):
        bad = dict(LOAD_PATH, originates_at="somewhere")
        with self.assertRaises(ValueError):
            validate_path(bad)

    def test_a_path_with_an_unknown_return_route_is_refused(self):
        bad = dict(LOAD_PATH, returns_via="thin-air")
        with self.assertRaises(ValueError):
            validate_path(bad)

    def test_a_negative_current_is_refused(self):
        bad = dict(LOAD_PATH, current_a=-1.0)
        with self.assertRaises(ValueError):
            validate_path(bad)

    def test_a_nameless_path_is_refused(self):
        bad = dict(LOAD_PATH, id="")
        with self.assertRaises(ValueError):
            validate_path(bad)

    def test_an_empty_path_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_paths([])

    def test_a_duplicate_path_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_paths([LOAD_PATH, dict(HOUSEKEEPING_PATH, id="unit-load-draw")])


class SensingCoverageTests(unittest.TestCase):
    def test_a_bus_interface_element_sees_every_path(self):
        for path in FAULTED_PATHS:
            self.assertTrue(
                path_is_sensed(path, SENSOR_RAIL_ENERGISED, POSITION_BUS_INTERFACE)
            )

    def test_a_return_rail_element_misses_a_structure_return(self):
        self.assertFalse(
            path_is_sensed(
                STRUCTURE_FAULT_PATH, SENSOR_RAIL_RETURN, POSITION_BUS_INTERFACE
            )
        )
        self.assertTrue(
            path_is_sensed(LOAD_PATH, SENSOR_RAIL_RETURN, POSITION_BUS_INTERFACE)
        )

    def test_a_return_rail_element_also_misses_a_chassis_bond_return(self):
        bonded = dict(LOAD_PATH, id="bonded-leak", returns_via=RETURN_VIA_CHASSIS_BOND)
        self.assertFalse(
            path_is_sensed(bonded, SENSOR_RAIL_RETURN, POSITION_BUS_INTERFACE)
        )

    def test_an_element_behind_the_switch_misses_the_housekeeping_tap(self):
        self.assertFalse(
            path_is_sensed(
                HOUSEKEEPING_PATH, SENSOR_RAIL_ENERGISED, POSITION_AFTER_SWITCH
            )
        )
        self.assertTrue(
            path_is_sensed(LOAD_PATH, SENSOR_RAIL_ENERGISED, POSITION_AFTER_SWITCH)
        )

    def test_an_element_behind_the_switch_misses_an_upstream_stub_draw(self):
        stub = dict(LOAD_PATH, id="stub-leak", originates_at=ORIGIN_UPSTREAM_STUB)
        self.assertFalse(
            path_is_sensed(stub, SENSOR_RAIL_ENERGISED, POSITION_AFTER_SWITCH)
        )

    def test_the_branch_total_is_the_sum_of_its_paths(self):
        self.assertAlmostEqual(total_current_a(FAULTED_PATHS), 5.0, places=9)

    def test_the_bus_interface_element_reads_the_whole_branch(self):
        self.assertAlmostEqual(
            sensed_current_a(
                FAULTED_PATHS, SENSOR_RAIL_ENERGISED, POSITION_BUS_INTERFACE
            ),
            5.0,
            places=9,
        )

    def test_the_return_rail_element_reads_only_the_bus_returns(self):
        self.assertAlmostEqual(
            sensed_current_a(FAULTED_PATHS, SENSOR_RAIL_RETURN, POSITION_BUS_INTERFACE),
            3.25,
            places=9,
        )

    def test_the_sensed_share_is_one_at_the_bus_interface(self):
        self.assertAlmostEqual(
            sensed_fraction(
                FAULTED_PATHS, SENSOR_RAIL_ENERGISED, POSITION_BUS_INTERFACE
            ),
            1.0,
            places=9,
        )

    def test_the_sensed_share_falls_on_the_return_rail(self):
        self.assertAlmostEqual(
            sensed_fraction(FAULTED_PATHS, SENSOR_RAIL_RETURN, POSITION_BUS_INTERFACE),
            0.65,
            places=9,
        )

    def test_the_bypassing_path_is_named_not_only_counted(self):
        self.assertEqual(
            unsensed_paths(FAULTED_PATHS, SENSOR_RAIL_RETURN, POSITION_BUS_INTERFACE),
            ("load-short-to-structure",),
        )

    def test_a_branch_carrying_no_current_has_no_defined_share(self):
        idle = [dict(LOAD_PATH, current_a=0.0)]
        with self.assertRaises(ValueError):
            sensed_fraction(idle, SENSOR_RAIL_ENERGISED, POSITION_BUS_INTERFACE)


class TripArithmeticTests(unittest.TestCase):
    def test_a_fully_sensed_branch_trips_at_its_threshold(self):
        self.assertAlmostEqual(effective_trip_current_a(5.0, 1.0), 5.0, places=9)

    def test_a_partly_blind_element_needs_more_real_current(self):
        self.assertAlmostEqual(effective_trip_current_a(5.0, 0.65), 5.0 / 0.65, places=9)

    def test_a_blind_element_can_never_reach_its_threshold(self):
        with self.assertRaises(ValueError):
            effective_trip_current_a(5.0, 0.0)

    def test_a_share_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            effective_trip_current_a(5.0, 1.2)

    def test_a_non_positive_threshold_is_refused(self):
        with self.assertRaises(ValueError):
            effective_trip_current_a(0.0, 1.0)

    def test_the_measurement_band_straddles_the_reading(self):
        low, high = measurement_band_a(3.25, 0.02)
        self.assertAlmostEqual(low, 3.25 * 0.98, places=9)
        self.assertAlmostEqual(high, 3.25 * 1.02, places=9)

    def test_a_perfect_element_has_no_band(self):
        low, high = measurement_band_a(3.25, 0.0)
        self.assertAlmostEqual(low, 3.25, places=9)
        self.assertAlmostEqual(high, 3.25, places=9)

    def test_the_harness_margin_is_positive_while_the_trip_stays_under_the_rating(self):
        self.assertAlmostEqual(harness_margin_fraction(5.0, 8.0), 0.375, places=9)

    def test_the_harness_margin_goes_negative_once_the_trip_passes_the_rating(self):
        self.assertLess(harness_margin_fraction(10.0, 8.0), 0.0)

    def test_a_zero_harness_rating_is_refused(self):
        with self.assertRaises(ValueError):
            harness_margin_fraction(5.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_an_element_at_the_bus_interface_is_compliant(self):
        result = assess_sensor_placement(_case())
        self.assertEqual(result["verdict"], SENSOR_PLACEMENT_COMPLIANT)
        self.assertTrue(result["on_energised_bus_side"])
        self.assertEqual(result["findings"], [])

    def test_the_compliant_case_sees_the_whole_branch(self):
        result = assess_sensor_placement(_case())
        self.assertAlmostEqual(result["sensed_fraction"], 1.0, places=9)
        self.assertAlmostEqual(
            result["effective_trip_current_a"], result["trip_threshold_a"], places=9
        )

    def test_a_return_rail_element_is_not_compliant(self):
        result = assess_sensor_placement(
            _case(sensor_rail=SENSOR_RAIL_RETURN, current_paths=copy.deepcopy(FAULTED_PATHS))
        )
        self.assertEqual(result["verdict"], SENSOR_PLACEMENT_NON_COMPLIANT)
        self.assertFalse(result["on_energised_bus_side"])
        self.assertTrue(any("energised main bus side" in f for f in result["findings"]))

    def test_a_return_rail_element_reports_the_fault_it_cannot_see(self):
        result = assess_sensor_placement(
            _case(sensor_rail=SENSOR_RAIL_RETURN, current_paths=copy.deepcopy(FAULTED_PATHS))
        )
        self.assertEqual(result["unsensed_fault_paths"], ("load-short-to-structure",))
        self.assertTrue(any("never trip it" in f for f in result["findings"]))

    def test_a_return_rail_element_pushes_the_real_trip_current_up(self):
        result = assess_sensor_placement(
            _case(sensor_rail=SENSOR_RAIL_RETURN, current_paths=copy.deepcopy(FAULTED_PATHS))
        )
        self.assertAlmostEqual(result["effective_trip_current_a"], 5.0 / 0.65, places=9)

    def test_a_blind_return_rail_element_reaches_no_trip_at_all(self):
        only_structure = [
            dict(STRUCTURE_FAULT_PATH, id="everything-returns-through-structure", current_a=4.0)
        ]
        result = assess_sensor_placement(
            _case(sensor_rail=SENSOR_RAIL_RETURN, current_paths=only_structure)
        )
        self.assertIsNone(result["effective_trip_current_a"])
        self.assertTrue(any("unreachable" in f for f in result["findings"]))

    def test_an_element_behind_the_switch_is_flagged_for_its_position(self):
        result = assess_sensor_placement(_case(sensor_position=POSITION_AFTER_SWITCH))
        self.assertEqual(result["verdict"], SENSOR_PLACEMENT_NON_COMPLIANT)
        self.assertTrue(any("in series" in f for f in result["findings"]))
        self.assertEqual(result["unsensed_paths"], ("device-housekeeping",))

    def test_a_trip_threshold_inside_the_nominal_band_is_flagged(self):
        result = assess_sensor_placement(_case(trip_threshold_a=3.3))
        self.assertTrue(any("nuisance trips" in f for f in result["findings"]))

    def test_a_threshold_exactly_at_the_top_of_the_band_is_accepted(self):
        result = assess_sensor_placement(_case(trip_threshold_a=3.25 * 1.02))
        self.assertFalse(any("nuisance trips" in f for f in result["findings"]))

    def test_an_effective_trip_above_the_harness_rating_is_flagged(self):
        result = assess_sensor_placement(
            _case(
                sensor_rail=SENSOR_RAIL_RETURN,
                current_paths=copy.deepcopy(FAULTED_PATHS),
                harness_rating_a=6.0,
            )
        )
        self.assertTrue(any("harness rating" in f for f in result["findings"]))
        self.assertLess(result["harness_margin_fraction"], 0.0)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_sensor_placement(HEALTHY_PATHS)

    def test_a_missing_harness_rating_is_refused(self):
        case = _case()
        del case["harness_rating_a"]
        with self.assertRaises(ValueError):
            assess_sensor_placement(case)

    def test_the_assessment_does_not_mutate_the_caller_case(self):
        case = _case()
        before = copy.deepcopy(case)
        assess_sensor_placement(case)
        self.assertEqual(case, before)


if __name__ == "__main__":
    unittest.main()
