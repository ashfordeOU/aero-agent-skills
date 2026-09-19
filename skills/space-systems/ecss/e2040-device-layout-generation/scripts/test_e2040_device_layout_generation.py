#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-layout-generation.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_layout_generation.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_layout_generation_logic import (  # noqa: E402
    IMPLEMENTATION_STYLES,
    REQUIRED_DOCUMENTATION,
    evaluate_layout_generation,
    missing_documentation,
    normalize_style,
    routing_completion,
    setup_slack_ns,
    timing_is_met,
    utilization,
    validate_run,
    within_utilization_ceiling,
)


def base_run():
    return {
        "style": "pnr",
        "core_area_mm2": 8.0,
        "placed_cell_area_mm2": 5.0,
        "target_period_ns": 10.0,
        "achieved_period_ns": 9.4,
        "total_nets": 42000,
        "unrouted_nets": 0,
        "open_geometry_violations": 0,
        "documentation": list(REQUIRED_DOCUMENTATION),
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestStyle(unittest.TestCase):
    def test_pnr_folds_to_place_and_route(self):
        self.assertEqual(normalize_style("PnR"), "place-and-route")

    def test_analogue_folds_to_full_custom(self):
        self.assertEqual(normalize_style("analogue"), "full-custom")

    def test_sea_of_gates_folds_to_structured_array(self):
        self.assertEqual(normalize_style("sea of gates"), "structured-array")

    def test_unknown_style_rejected(self):
        with self.assertRaises(ValueError):
            normalize_style("hand drawn")

    def test_the_style_vocabulary_is_closed(self):
        self.assertEqual(len(IMPLEMENTATION_STYLES), 3)


class TestUtilization(unittest.TestCase):
    def test_utilization_is_cell_area_over_core_area(self):
        self.assertAlmostEqual(utilization(5.0, 8.0), 0.625, places=9)

    def test_a_zero_core_area_rejected(self):
        with self.assertRaises(ValueError):
            utilization(5.0, 0.0)

    def test_a_negative_cell_area_rejected(self):
        with self.assertRaises(ValueError):
            utilization(-1.0, 8.0)

    def test_a_boolean_area_rejected(self):
        with self.assertRaises(ValueError):
            utilization(True, 8.0)

    def test_utilization_under_the_ceiling_is_within_it(self):
        self.assertTrue(within_utilization_ceiling(0.625, 0.75))

    def test_utilization_exactly_on_the_ceiling_is_within_it(self):
        self.assertTrue(within_utilization_ceiling(utilization(6.0, 8.0), 0.75))

    def test_utilization_over_the_ceiling_is_not(self):
        self.assertFalse(within_utilization_ceiling(0.9, 0.75))

    def test_a_ceiling_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            within_utilization_ceiling(0.5, 1.4)


class TestTiming(unittest.TestCase):
    def test_slack_is_target_minus_achieved(self):
        self.assertAlmostEqual(setup_slack_ns(10.0, 9.4), 0.6, places=9)

    def test_slack_is_negative_when_the_path_is_too_slow(self):
        self.assertAlmostEqual(setup_slack_ns(10.0, 11.0), -1.0, places=9)

    def test_a_run_inside_the_target_meets_it(self):
        self.assertTrue(timing_is_met(10.0, 9.4))

    def test_a_run_exactly_on_target_meets_it(self):
        self.assertTrue(timing_is_met(0.3, 3 * 0.1))

    def test_a_run_outside_the_target_misses_it(self):
        self.assertFalse(timing_is_met(10.0, 10.5))

    def test_a_zero_target_period_rejected(self):
        with self.assertRaises(ValueError):
            timing_is_met(0.0, 1.0)

    def test_a_negative_achieved_period_rejected(self):
        with self.assertRaises(ValueError):
            setup_slack_ns(10.0, -1.0)


class TestRouting(unittest.TestCase):
    def test_a_fully_routed_run_completes(self):
        self.assertAlmostEqual(routing_completion(1000, 0), 1.0, places=9)

    def test_completion_rounds_high_with_a_few_nets_open(self):
        self.assertAlmostEqual(routing_completion(1000, 3), 0.997, places=9)

    def test_more_unrouted_than_total_rejected(self):
        with self.assertRaises(ValueError):
            routing_completion(10, 11)

    def test_a_zero_net_list_rejected(self):
        with self.assertRaises(ValueError):
            routing_completion(0, 0)

    def test_a_non_integer_net_count_rejected(self):
        with self.assertRaises(ValueError):
            routing_completion(10.5, 0)

    def test_a_negative_unrouted_count_rejected(self):
        with self.assertRaises(ValueError):
            routing_completion(10, -1)


class TestDocumentation(unittest.TestCase):
    def test_a_complete_record_has_no_gap(self):
        self.assertEqual(missing_documentation(REQUIRED_DOCUMENTATION), [])

    def test_a_missing_tool_version_is_reported(self):
        items = [i for i in REQUIRED_DOCUMENTATION if i != "tool-and-version"]
        self.assertEqual(missing_documentation(items), ["tool-and-version"])

    def test_documentation_names_fold_on_spacing(self):
        items = ["Floorplan Description", "layer_stack", "pin-assignment",
                 "layout rule deviations", "tool-and-version"]
        self.assertEqual(missing_documentation(items), [])

    def test_an_unknown_documentation_item_rejected(self):
        with self.assertRaises(ValueError):
            missing_documentation(["marketing-brief"])

    def test_a_non_list_documentation_set_rejected(self):
        with self.assertRaises(ValueError):
            missing_documentation("floorplan-description")


class TestValidation(unittest.TestCase):
    def test_the_run_resolves(self):
        resolved = validate_run(base_run())
        self.assertEqual(resolved["style"], "place-and-route")
        self.assertEqual(resolved["total_nets"], 42000)

    def test_unknown_run_key_rejected(self):
        run = base_run()
        run["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_run(run)

    def test_a_run_without_a_core_area_rejected(self):
        run = base_run()
        del run["core_area_mm2"]
        with self.assertRaises(ValueError):
            validate_run(run)

    def test_a_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            validate_run([("core_area_mm2", 8.0)])


class TestEvaluateRun(unittest.TestCase):
    def test_a_clean_run_is_releasable(self):
        result = evaluate_layout_generation(base_run())
        self.assertTrue(result["releasable"])
        self.assertEqual(result["findings"], [])

    def test_the_figures_reach_the_result(self):
        result = evaluate_layout_generation(base_run())
        self.assertAlmostEqual(result["utilization"], 0.625, places=9)
        self.assertAlmostEqual(result["setup_slack_ns"], 0.6, places=9)
        self.assertAlmostEqual(result["routing_completion"], 1.0, places=9)

    def test_utilization_exactly_on_the_ceiling_does_not_fault_the_run(self):
        run = base_run()
        run["placed_cell_area_mm2"] = 6.0
        result = evaluate_layout_generation(run, utilization_ceiling=0.75)
        self.assertNotIn("utilization-over-ceiling", codes(result))

    def test_utilization_over_the_ceiling_is_reported(self):
        run = base_run()
        run["placed_cell_area_mm2"] = 7.2
        result = evaluate_layout_generation(run)
        self.assertIn("utilization-over-ceiling", codes(result))

    def test_a_missed_target_period_is_reported(self):
        run = base_run()
        run["achieved_period_ns"] = 10.8
        result = evaluate_layout_generation(run)
        self.assertIn("target-period-not-met", codes(result))
        self.assertFalse(result["timing_met"])

    def test_a_run_exactly_on_the_target_period_is_not_reported(self):
        run = base_run()
        run["achieved_period_ns"] = 10.0
        result = evaluate_layout_generation(run)
        self.assertNotIn("target-period-not-met", codes(result))

    def test_a_single_unrouted_net_is_reported(self):
        run = base_run()
        run["unrouted_nets"] = 1
        result = evaluate_layout_generation(run)
        self.assertIn("nets-left-unrouted", codes(result))
        self.assertFalse(result["releasable"])

    def test_open_geometry_violations_are_reported(self):
        run = base_run()
        run["open_geometry_violations"] = 4
        result = evaluate_layout_generation(run)
        self.assertIn("geometry-violations-open", codes(result))

    def test_a_documentation_gap_is_reported(self):
        run = base_run()
        run["documentation"] = [
            i for i in REQUIRED_DOCUMENTATION if i != "layout-rule-deviations"
        ]
        result = evaluate_layout_generation(run)
        self.assertIn("documentation-item-missing", codes(result))
        self.assertEqual(result["missing_documentation"], ["layout-rule-deviations"])

    def test_an_undocumented_run_reports_every_item(self):
        run = base_run()
        run["documentation"] = []
        result = evaluate_layout_generation(run)
        self.assertEqual(
            len(result["missing_documentation"]), len(REQUIRED_DOCUMENTATION)
        )

    def test_a_ceiling_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_layout_generation(base_run(), utilization_ceiling=1.9)


if __name__ == "__main__":
    unittest.main()
