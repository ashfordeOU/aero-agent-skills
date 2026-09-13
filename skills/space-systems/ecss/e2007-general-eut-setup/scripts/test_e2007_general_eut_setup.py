#!/usr/bin/env python3
"""Gate 3 contract test for e2007-general-eut-setup.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_general_eut_setup_logic import (
    DEFAULT_SETUP_SPEC,
    GEOM_EPS,
    categorize_bench,
    categorize_bench_item,
    check_dimension,
    check_ground_plane,
    check_harness_routing,
    check_minimum,
    check_standoff,
    evaluate_setup,
    required_bench_length_mm,
    required_ground_plane_area_m2,
    resolve_spec,
    setup_readiness,
)


def nominal_items():
    return [
        {"name": "flight-unit", "role": "tested-unit"},
        {"name": "stimulus-generator", "role": "stimulus-source"},
        {"name": "resistive-load-bank", "role": "load-simulator"},
        {"name": "flight-harness", "role": "interconnecting-harness"},
        {"name": "line-coupling-network", "role": "coupling-network"},
    ]


def nominal_config():
    return {
        "items": nominal_items(),
        "tested_unit_footprint_mm": (400.0, 300.0),
        "ground_plane_area_m2": 2.0,
        "front_edge_setback_mm": 100.0,
        "enclosure_wall_clearance_mm": 1200.0,
        "item_separation_mm": 150.0,
        "standoff": {"height_mm": 50.0, "relative_permittivity": 1.1},
        "harness": {
            "total_length_mm": 2500.0,
            "exposed_length_mm": 2000.0,
            "routing_height_mm": 50.0,
        },
    }


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["standoff_height_mm"], 50.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_SETUP_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"standoff_height_mm": 80.0})
        self.assertAlmostEqual(spec["standoff_height_mm"], 80.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"standoff_height_mm": 80.0})
        self.assertAlmostEqual(DEFAULT_SETUP_SPEC["standoff_height_mm"], 50.0, places=9)

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"bench_colour": 3.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("standoff_height_mm", 80.0)])

    def test_non_numeric_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"standoff_height_mm": "80"})


class TestItemCategorization(unittest.TestCase):
    def test_tested_unit_role(self):
        self.assertEqual(
            categorize_bench_item({"name": "u", "role": "tested-unit"}), "tested-unit"
        )

    def test_stimulus_source_is_support_equipment(self):
        self.assertEqual(
            categorize_bench_item({"name": "g", "role": "stimulus-source"}),
            "support-equipment",
        )

    def test_monitor_instrument_is_support_equipment(self):
        self.assertEqual(
            categorize_bench_item({"name": "m", "role": "monitor-instrument"}),
            "support-equipment",
        )

    def test_harness_keeps_its_own_category(self):
        self.assertEqual(
            categorize_bench_item({"name": "h", "role": "interconnecting-harness"}),
            "interconnecting-harness",
        )

    def test_coupling_network_keeps_its_own_category(self):
        self.assertEqual(
            categorize_bench_item({"name": "c", "role": "coupling-network"}),
            "coupling-network",
        )

    def test_unrecognized_role_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_bench_item({"name": "x", "role": "coffee-machine"})

    def test_item_without_a_name_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_bench_item({"role": "tested-unit"})

    def test_item_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_bench_item(("flight-unit", "tested-unit"))

    def test_whole_bench_is_categorized(self):
        bench = categorize_bench(nominal_items())
        self.assertEqual(len(bench), 5)
        self.assertEqual(
            sum(1 for b in bench if b["category"] == "support-equipment"), 2
        )

    def test_empty_bench_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_bench([])

    def test_duplicate_item_names_are_rejected(self):
        items = nominal_items()
        items[1]["name"] = items[0]["name"]
        with self.assertRaises(ValueError):
            categorize_bench(items)

    def test_two_tested_units_are_rejected(self):
        items = nominal_items()
        items[1]["role"] = "tested-unit"
        with self.assertRaises(ValueError):
            categorize_bench(items)

    def test_bench_without_a_tested_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_bench(nominal_items()[1:])


class TestDimensionCheck(unittest.TestCase):
    def test_dimension_inside_the_band_is_compliant(self):
        result = check_dimension("standoff-height", 52.0, 50.0, 5.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["deviation_mm"], 2.0, places=9)

    def test_dimension_outside_the_band_is_not_compliant(self):
        result = check_dimension("standoff-height", 60.0, 50.0, 5.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["deviation_mm"], 10.0, places=9)

    def test_stack_up_representation_error_at_the_band_edge_is_absorbed(self):
        measured = 50.0 + 0.1 + 0.2
        self.assertGreater(abs(measured - 50.0), 0.3)
        result = check_dimension("shim-stack", measured, 50.0, 0.3)
        self.assertTrue(result["compliant"])

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("standoff-height", 50.0, 50.0, -1.0)

    def test_empty_label_is_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("  ", 50.0, 50.0, 5.0)

    def test_non_numeric_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("standoff-height", "50", 50.0, 5.0)


class TestMinimumCheck(unittest.TestCase):
    def test_clearance_above_the_minimum_is_compliant(self):
        result = check_minimum("enclosure-wall-clearance", 1200.0, 1000.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["shortfall_mm"], 0.0, places=9)

    def test_clearance_below_the_minimum_reports_a_shortfall(self):
        result = check_minimum("enclosure-wall-clearance", 800.0, 1000.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["shortfall_mm"], 200.0, places=9)

    def test_clearance_exactly_at_the_minimum_is_compliant(self):
        self.assertTrue(check_minimum("item-separation", 100.0, 100.0)["compliant"])

    def test_representation_error_at_the_minimum_is_absorbed(self):
        minimum = 50.0 + 0.1 + 0.2
        self.assertGreater(minimum, 50.3)
        self.assertTrue(check_minimum("item-separation", 50.3, minimum)["compliant"])

    def test_negative_minimum_is_rejected(self):
        with self.assertRaises(ValueError):
            check_minimum("item-separation", 100.0, -1.0)

    def test_non_string_label_is_rejected(self):
        with self.assertRaises(ValueError):
            check_minimum(7, 100.0, 50.0)


class TestReferencePlane(unittest.TestCase):
    def test_required_area_adds_the_margin_on_every_side(self):
        self.assertAlmostEqual(
            required_ground_plane_area_m2(400.0, 300.0, 100.0), 0.3, places=9
        )

    def test_zero_margin_is_the_bare_footprint(self):
        self.assertAlmostEqual(
            required_ground_plane_area_m2(1000.0, 1000.0, 0.0), 1.0, places=9
        )

    def test_non_positive_footprint_is_rejected(self):
        with self.assertRaises(ValueError):
            required_ground_plane_area_m2(0.0, 300.0, 100.0)

    def test_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            required_ground_plane_area_m2(400.0, 300.0, -10.0)

    def test_adequate_plane_is_compliant(self):
        result = check_ground_plane(2.0, 0.3)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["shortfall_m2"], 0.0, places=9)

    def test_small_plane_reports_a_shortfall(self):
        result = check_ground_plane(0.2, 0.5)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["shortfall_m2"], 0.3, places=9)

    def test_representation_error_at_the_area_boundary_is_absorbed(self):
        required = 0.1 + 0.2
        self.assertGreater(required, 0.3)
        self.assertTrue(check_ground_plane(0.3, required)["compliant"])

    def test_non_positive_available_area_is_rejected(self):
        with self.assertRaises(ValueError):
            check_ground_plane(0.0, 0.3)

    def test_non_positive_required_area_is_rejected(self):
        with self.assertRaises(ValueError):
            check_ground_plane(2.0, 0.0)


class TestStandoff(unittest.TestCase):
    def test_nominal_standoff_passes(self):
        result = check_standoff({"height_mm": 50.0, "relative_permittivity": 1.1})
        self.assertTrue(result["height"]["compliant"])
        self.assertTrue(result["low_permittivity"])

    def test_tall_standoff_fails_the_band(self):
        result = check_standoff({"height_mm": 90.0, "relative_permittivity": 1.1})
        self.assertFalse(result["height"]["compliant"])

    def test_dense_dielectric_is_flagged(self):
        result = check_standoff({"height_mm": 50.0, "relative_permittivity": 3.5})
        self.assertFalse(result["low_permittivity"])

    def test_permittivity_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            check_standoff({"height_mm": 50.0, "relative_permittivity": 0.5})

    def test_non_positive_height_is_rejected(self):
        with self.assertRaises(ValueError):
            check_standoff({"height_mm": 0.0, "relative_permittivity": 1.1})

    def test_standoff_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            check_standoff([50.0, 1.1])

    def test_spec_override_raises_the_permittivity_cap(self):
        result = check_standoff(
            {"height_mm": 50.0, "relative_permittivity": 3.5},
            {"standoff_max_relative_permittivity": 4.0},
        )
        self.assertTrue(result["low_permittivity"])


class TestHarnessRouting(unittest.TestCase):
    def test_nominal_harness_passes(self):
        result = check_harness_routing(
            {"total_length_mm": 2500.0, "exposed_length_mm": 2000.0, "routing_height_mm": 50.0}
        )
        self.assertTrue(result["exposed_length"]["compliant"])
        self.assertTrue(result["routing_height"]["compliant"])
        self.assertAlmostEqual(result["stowed_length_mm"], 500.0, places=9)

    def test_short_exposed_run_fails_the_band(self):
        result = check_harness_routing(
            {"total_length_mm": 2500.0, "exposed_length_mm": 1500.0, "routing_height_mm": 50.0}
        )
        self.assertFalse(result["exposed_length"]["compliant"])

    def test_high_routing_fails_the_band(self):
        result = check_harness_routing(
            {"total_length_mm": 2500.0, "exposed_length_mm": 2000.0, "routing_height_mm": 200.0}
        )
        self.assertFalse(result["routing_height"]["compliant"])

    def test_exposed_run_longer_than_the_harness_is_rejected(self):
        with self.assertRaises(ValueError):
            check_harness_routing(
                {
                    "total_length_mm": 1800.0,
                    "exposed_length_mm": 2000.0,
                    "routing_height_mm": 50.0,
                }
            )

    def test_exposed_run_equal_to_the_harness_is_accepted(self):
        result = check_harness_routing(
            {"total_length_mm": 2000.0, "exposed_length_mm": 2000.0, "routing_height_mm": 50.0}
        )
        self.assertAlmostEqual(result["stowed_length_mm"], 0.0, places=9)

    def test_non_positive_total_length_is_rejected(self):
        with self.assertRaises(ValueError):
            check_harness_routing(
                {"total_length_mm": 0.0, "exposed_length_mm": 2000.0, "routing_height_mm": 50.0}
            )

    def test_non_positive_exposed_length_is_rejected(self):
        with self.assertRaises(ValueError):
            check_harness_routing(
                {"total_length_mm": 2500.0, "exposed_length_mm": 0.0, "routing_height_mm": 50.0}
            )

    def test_negative_routing_height_is_rejected(self):
        with self.assertRaises(ValueError):
            check_harness_routing(
                {
                    "total_length_mm": 2500.0,
                    "exposed_length_mm": 2000.0,
                    "routing_height_mm": -5.0,
                }
            )

    def test_harness_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            check_harness_routing("2000 mm")


class TestBenchLength(unittest.TestCase):
    def test_run_includes_separations_and_margins(self):
        self.assertAlmostEqual(
            required_bench_length_mm([400.0, 300.0, 200.0], 100.0, 100.0), 1300.0, places=9
        )

    def test_single_item_has_no_separation_term(self):
        self.assertAlmostEqual(
            required_bench_length_mm([400.0], 100.0, 50.0), 500.0, places=9
        )

    def test_empty_footprint_list_is_rejected(self):
        with self.assertRaises(ValueError):
            required_bench_length_mm([], 100.0, 100.0)

    def test_non_positive_footprint_is_rejected(self):
        with self.assertRaises(ValueError):
            required_bench_length_mm([400.0, -1.0], 100.0, 100.0)

    def test_negative_separation_is_rejected(self):
        with self.assertRaises(ValueError):
            required_bench_length_mm([400.0, 300.0], -10.0, 100.0)

    def test_negative_perimeter_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            required_bench_length_mm([400.0, 300.0], 100.0, -10.0)


class TestReadinessGate(unittest.TestCase):
    def test_clean_finding_list_is_ready(self):
        self.assertEqual(setup_readiness([]), "ready-for-measurement")

    def test_any_finding_holds_the_setup(self):
        self.assertEqual(setup_readiness(["plane too small"]), "hold-setup")

    def test_non_sequence_finding_list_is_rejected(self):
        with self.assertRaises(ValueError):
            setup_readiness(None)


class TestEndToEndSetup(unittest.TestCase):
    def test_nominal_bench_is_ready(self):
        report = evaluate_setup(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "ready-for-measurement")
        self.assertAlmostEqual(report["required_plane_area_m2"], 0.3, places=9)

    def test_small_reference_plane_is_a_finding(self):
        config = nominal_config()
        config["ground_plane_area_m2"] = 0.1
        report = evaluate_setup(config)
        self.assertFalse(report["ready"])
        self.assertTrue(any("reference plane" in f for f in report["findings"]))

    def test_setback_outside_the_band_is_a_finding(self):
        config = nominal_config()
        config["front_edge_setback_mm"] = 400.0
        report = evaluate_setup(config)
        self.assertIn("front-edge-setback outside the arrangement band", report["findings"])

    def test_wall_clearance_below_the_minimum_is_a_finding(self):
        config = nominal_config()
        config["enclosure_wall_clearance_mm"] = 400.0
        report = evaluate_setup(config)
        self.assertIn(
            "enclosure-wall-clearance below the arrangement minimum", report["findings"]
        )

    def test_item_separation_below_the_minimum_is_a_finding(self):
        config = nominal_config()
        config["item_separation_mm"] = 20.0
        report = evaluate_setup(config)
        self.assertIn("item-separation below the arrangement minimum", report["findings"])

    def test_dense_standoff_dielectric_is_a_finding(self):
        config = nominal_config()
        config["standoff"]["relative_permittivity"] = 4.2
        report = evaluate_setup(config)
        self.assertTrue(any("standoff dielectric" in f for f in report["findings"]))

    def test_missing_harness_item_is_a_finding(self):
        config = nominal_config()
        config["items"] = [i for i in config["items"] if i["role"] != "interconnecting-harness"]
        report = evaluate_setup(config)
        self.assertIn("no interconnecting harness on the arrangement record", report["findings"])

    def test_spec_override_can_requalify_a_bench(self):
        config = nominal_config()
        config["enclosure_wall_clearance_mm"] = 600.0
        self.assertFalse(evaluate_setup(config)["ready"])
        config["spec"] = {"min_enclosure_wall_clearance_mm": 500.0}
        self.assertTrue(evaluate_setup(config)["ready"])

    def test_missing_required_key_is_rejected(self):
        config = nominal_config()
        del config["standoff"]
        with self.assertRaises(ValueError):
            evaluate_setup(config)

    def test_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_setup([("items", [])])

    def test_footprint_must_be_a_length_width_pair(self):
        config = nominal_config()
        config["tested_unit_footprint_mm"] = (400.0,)
        with self.assertRaises(ValueError):
            evaluate_setup(config)

    def test_missing_plane_area_is_rejected(self):
        config = nominal_config()
        del config["ground_plane_area_m2"]
        with self.assertRaises(ValueError):
            evaluate_setup(config)

    def test_named_tolerance_is_far_below_any_geometric_limit(self):
        self.assertLess(GEOM_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
