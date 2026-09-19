"""Contract test for the fastener manufacturing-control leaf (stdlib unittest)."""

import unittest

from q7046_manufacturing_process_control_logic import (
    CAPABLE,
    CAPABLE_FLOOR,
    CONTROL_ACTION,
    CONTROLLED,
    MARGINAL,
    MARGINAL_FLOOR,
    NOT_CAPABLE,
    NOT_CONTROLLED,
    RELIEF_BAKE_WINDOW_HOURS,
    assess_parameter,
    assess_route,
    assess_shop_routes,
    capability_index,
    capability_rating,
    missing_mandatory_operations,
    operation_position,
    relief_bake_finding,
    requalification_required,
    validate_parameter,
    validate_route,
    validate_route_record,
)

BASE_ROUTE = [
    "cold-heading",
    "rough-machining",
    "heat-treatment",
    "finish-machining",
    "thread-forming",
    "final-inspection",
]


def parameter(**kw):
    record = {
        "name": "austenitizing-temperature",
        "operation": "heat-treatment",
        "lower": 830.0,
        "upper": 870.0,
        "mean": 850.0,
        "sigma": 4.0,
    }
    record.update(kw)
    return record


def route(**kw):
    record = {
        "part_number": "fs-3001",
        "property_class": "10.9",
        "operations": list(BASE_ROUTE),
        "electroplated": False,
        "relief_bake_delay_hours": 0.0,
        "parameters": [parameter()],
    }
    record.update(kw)
    return record


class TestOperationOrder(unittest.TestCase):
    def test_an_admitted_operation_has_a_position(self):
        self.assertEqual(operation_position("heat-treatment"), 40)

    def test_an_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            operation_position("polishing-by-eye")

    def test_a_non_string_operation_raises(self):
        with self.assertRaises(ValueError):
            operation_position(40)

    def test_a_forward_route_validates(self):
        self.assertEqual(validate_route(BASE_ROUTE), BASE_ROUTE)

    def test_a_route_running_backwards_raises(self):
        with self.assertRaises(ValueError):
            validate_route(["thread-forming", "heat-treatment", "final-inspection"])

    def test_a_route_repeating_an_operation_raises(self):
        with self.assertRaises(ValueError):
            validate_route(["cold-heading", "cold-heading", "final-inspection"])

    def test_an_empty_route_raises(self):
        with self.assertRaises(ValueError):
            validate_route([])

    def test_the_two_blank_making_routes_share_a_position(self):
        self.assertEqual(
            operation_position("cold-heading"), operation_position("hot-forging")
        )


class TestMandatoryOperations(unittest.TestCase):
    def test_a_complete_route_leaves_nothing_out(self):
        self.assertEqual(missing_mandatory_operations(BASE_ROUTE, "10.9"), [])

    def test_a_quenched_class_owes_a_heat_treatment(self):
        thin = ["cold-heading", "thread-forming", "final-inspection"]
        self.assertIn("heat-treatment", missing_mandatory_operations(thin, "10.9"))

    def test_an_unhardened_class_does_not(self):
        thin = ["cold-heading", "thread-forming", "final-inspection"]
        self.assertEqual(missing_mandatory_operations(thin, "4.6"), [])

    def test_an_electroplated_route_owes_the_relief_bake(self):
        missing = missing_mandatory_operations(BASE_ROUTE, "10.9", electroplated=True)
        self.assertIn("embrittlement-relief-bake", missing)
        self.assertIn("surface-treatment", missing)

    def test_every_route_owes_a_final_inspection(self):
        thin = ["cold-heading", "heat-treatment", "thread-forming"]
        self.assertIn("final-inspection", missing_mandatory_operations(thin, "10.9"))

    def test_an_empty_property_class_raises(self):
        with self.assertRaises(ValueError):
            missing_mandatory_operations(BASE_ROUTE, "  ")


class TestReliefBakeWindow(unittest.TestCase):
    def test_a_prompt_bake_is_inside_its_window(self):
        self.assertTrue(relief_bake_finding(1.5)["inside_window"])

    def test_a_bake_exactly_on_the_window_is_inside_it(self):
        result = relief_bake_finding(RELIEF_BAKE_WINDOW_HOURS)
        self.assertTrue(result["inside_window"])
        self.assertAlmostEqual(result["overrun_hours"], 0.0, places=9)

    def test_a_late_bake_reports_its_overrun(self):
        result = relief_bake_finding(6.5)
        self.assertFalse(result["inside_window"])
        self.assertAlmostEqual(result["overrun_hours"], 2.5, places=9)

    def test_a_zero_window_raises(self):
        with self.assertRaises(ValueError):
            relief_bake_finding(1.0, 0.0)


class TestCapability(unittest.TestCase):
    def test_a_centred_tight_process_is_capable(self):
        index = capability_index(850.0, 4.0, 830.0, 870.0)
        self.assertAlmostEqual(index, 20.0 / 12.0, places=9)
        self.assertEqual(capability_rating(index), CAPABLE)

    def test_an_off_centre_process_is_graded_on_the_nearer_edge(self):
        index = capability_index(865.0, 4.0, 830.0, 870.0)
        self.assertAlmostEqual(index, 5.0 / 12.0, places=9)
        self.assertEqual(capability_rating(index), NOT_CAPABLE)

    def test_a_wide_spread_beats_a_centred_mean(self):
        self.assertLess(
            capability_index(850.0, 12.0, 830.0, 870.0),
            capability_index(850.0, 4.0, 830.0, 870.0),
        )

    def test_an_index_exactly_on_the_capable_floor_is_capable(self):
        self.assertEqual(capability_rating(CAPABLE_FLOOR), CAPABLE)

    def test_an_index_exactly_on_the_marginal_floor_is_marginal(self):
        self.assertEqual(capability_rating(MARGINAL_FLOOR), MARGINAL)

    def test_a_computed_index_on_the_capable_floor_is_capable(self):
        index = capability_index(0.0, 1.0, -3.99, 3.99)
        self.assertAlmostEqual(index, 1.33, places=9)
        self.assertEqual(capability_rating(index), CAPABLE)

    def test_an_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            capability_index(850.0, 4.0, 870.0, 830.0)

    def test_a_zero_sigma_raises(self):
        with self.assertRaises(ValueError):
            capability_index(850.0, 0.0, 830.0, 870.0)


class TestRequalification(unittest.TestCase):
    def test_a_small_change_keeps_the_qualification(self):
        result = requalification_required(850.0, 870.0, 0.05)
        self.assertFalse(result["requalification_required"])

    def test_a_change_exactly_on_the_tolerance_keeps_it(self):
        result = requalification_required(800.0, 840.0, 0.05)
        self.assertAlmostEqual(result["drift_fraction"], 0.05, places=9)
        self.assertFalse(result["requalification_required"])

    def test_a_larger_change_retires_it(self):
        self.assertTrue(
            requalification_required(800.0, 900.0, 0.05)["requalification_required"]
        )

    def test_a_downward_change_counts_the_same(self):
        self.assertTrue(
            requalification_required(800.0, 700.0, 0.05)["requalification_required"]
        )

    def test_a_zero_qualified_value_raises(self):
        with self.assertRaises(ValueError):
            requalification_required(0.0, 10.0, 0.05)


class TestAssessParameter(unittest.TestCase):
    def test_a_capable_parameter_is_controlled(self):
        result = assess_parameter(parameter())
        self.assertEqual(result["disposition"], CONTROLLED)
        self.assertEqual(result["capability_rating"], CAPABLE)

    def test_a_marginal_parameter_asks_for_a_control_action(self):
        result = assess_parameter(parameter(sigma=5.5))
        self.assertEqual(result["capability_rating"], MARGINAL)
        self.assertEqual(result["disposition"], CONTROL_ACTION)

    def test_a_mean_outside_its_window_is_not_controlled(self):
        result = assess_parameter(parameter(mean=880.0))
        self.assertFalse(result["mean_inside_window"])
        self.assertEqual(result["disposition"], NOT_CONTROLLED)

    def test_a_retiring_change_is_reported_on_a_capable_parameter(self):
        result = assess_parameter(
            parameter(qualified_value=850.0, proposed_value=950.0)
        )
        self.assertEqual(result["disposition"], CONTROL_ACTION)
        self.assertIn(
            "austenitizing-temperature-change-retires-the-qualification",
            result["findings"],
        )

    def test_a_parameter_with_an_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(operation="wishful-thinking"))

    def test_a_parameter_with_an_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(lower=900.0))

    def test_a_nameless_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(name=""))


class TestAssessRoute(unittest.TestCase):
    def test_a_complete_capable_route_is_controlled(self):
        result = assess_route(route())
        self.assertEqual(result["disposition"], CONTROLLED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_mandatory_operation_is_not_controlled(self):
        result = assess_route(
            route(operations=["cold-heading", "thread-forming", "final-inspection"])
        )
        self.assertEqual(result["disposition"], NOT_CONTROLLED)
        self.assertIn("route-missing-heat-treatment", result["findings"])

    def test_a_late_relief_bake_is_not_controlled(self):
        plated = list(BASE_ROUTE)
        plated.insert(5, "surface-treatment")
        plated.insert(6, "embrittlement-relief-bake")
        result = assess_route(
            route(operations=plated, electroplated=True,
                  relief_bake_delay_hours=9.0)
        )
        self.assertEqual(result["disposition"], NOT_CONTROLLED)
        self.assertIn("relief-bake-started-outside-its-window", result["findings"])

    def test_the_same_route_baked_promptly_is_controlled(self):
        plated = list(BASE_ROUTE)
        plated.insert(5, "surface-treatment")
        plated.insert(6, "embrittlement-relief-bake")
        result = assess_route(
            route(operations=plated, electroplated=True,
                  relief_bake_delay_hours=2.0)
        )
        self.assertEqual(result["disposition"], CONTROLLED)

    def test_operations_needing_requalification_are_named(self):
        result = assess_route(
            route(parameters=[parameter(qualified_value=850.0,
                                        proposed_value=950.0)])
        )
        self.assertEqual(
            result["operations_needing_requalification"], ["heat-treatment"]
        )

    def test_a_route_record_without_a_part_number_raises(self):
        with self.assertRaises(ValueError):
            validate_route_record(route(part_number=""))

    def test_a_route_record_with_a_backwards_route_raises(self):
        with self.assertRaises(ValueError):
            validate_route_record(
                route(operations=["final-inspection", "heat-treatment"])
            )


class TestAssessShopRoutes(unittest.TestCase):
    def test_a_clean_order_is_controlled(self):
        report = assess_shop_routes([route(), route(part_number="fs-3002")])
        self.assertEqual(report["order_disposition"], CONTROLLED)
        self.assertEqual(report["uncontrolled_parts"], [])

    def test_the_worst_route_sets_the_order_disposition(self):
        report = assess_shop_routes(
            [
                route(),
                route(part_number="fs-3003",
                      operations=["cold-heading", "thread-forming",
                                  "final-inspection"]),
            ]
        )
        self.assertEqual(report["order_disposition"], NOT_CONTROLLED)
        self.assertEqual(report["uncontrolled_parts"], ["fs-3003"])

    def test_parts_needing_requalification_are_listed(self):
        report = assess_shop_routes(
            [
                route(part_number="fs-3004",
                      parameters=[parameter(qualified_value=850.0,
                                            proposed_value=950.0)]),
            ]
        )
        self.assertEqual(report["parts_needing_requalification"], ["fs-3004"])

    def test_a_duplicate_part_raises(self):
        with self.assertRaises(ValueError):
            assess_shop_routes([route(), route()])

    def test_an_empty_order_raises(self):
        with self.assertRaises(ValueError):
            assess_shop_routes([])


if __name__ == "__main__":
    unittest.main()
