#!/usr/bin/env python3
"""Contract test for the level-one multipactor geometry screen.

Offline, deterministic, stdlib unittest. Run: python3 test_e2001_level_one_geometry_criteria.py
"""

import unittest

import e2001_level_one_geometry_criteria_logic as logic


def plate(**over):
    geometry = {
        "region_id": "plate-1",
        "shape": "parallel-plate",
        "gap_mm": 1.0,
        "surface_extent_mm": 40.0,
        "tilt_deg": 0.5,
    }
    geometry.update(over)
    return geometry


def coax(**over):
    geometry = {
        "region_id": "coax-1",
        "shape": "coaxial",
        "inner_radius_mm": 1.5,
        "outer_radius_mm": 3.45,
    }
    geometry.update(over)
    return geometry


class TestShapeCategorization(unittest.TestCase):
    def test_plate_alias_maps_to_parallel_family(self):
        self.assertEqual(
            logic.categorize_gap_shape({"shape": "waveguide-height-gap"}),
            logic.PARALLEL_PLATE,
        )

    def test_coaxial_alias_maps_to_coaxial_family(self):
        self.assertEqual(
            logic.categorize_gap_shape({"shape": "Annular-Gap"}), logic.COAXIAL
        )

    def test_out_of_scope_shape_is_uncategorized(self):
        self.assertEqual(
            logic.categorize_gap_shape({"shape": "stepped-iris"}), logic.UNCATEGORIZED
        )

    def test_unknown_shape_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gap_shape({"shape": "trapezoid-thing"})

    def test_missing_shape_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gap_shape({"gap_mm": 1.0})

    def test_blank_shape_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gap_shape({"shape": "   "})

    def test_non_mapping_geometry_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gap_shape(["parallel-plate"])


class TestEffectiveGap(unittest.TestCase):
    def test_plane_gap_is_the_plate_separation(self):
        self.assertAlmostEqual(logic.effective_gap_mm(plate(gap_mm=0.8)), 0.8, places=12)

    def test_annular_gap_is_the_radial_difference(self):
        self.assertAlmostEqual(logic.effective_gap_mm(coax()), 1.95, places=12)

    def test_outer_radius_not_larger_raises(self):
        with self.assertRaises(ValueError):
            logic.effective_gap_mm(coax(outer_radius_mm=1.5))

    def test_uncategorized_shape_has_no_effective_gap(self):
        with self.assertRaises(ValueError):
            logic.effective_gap_mm({"shape": "helix-gap"})

    def test_non_positive_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.effective_gap_mm(plate(gap_mm=0.0))

    def test_boolean_gap_is_rejected_as_non_numeric(self):
        with self.assertRaises(ValueError):
            logic.effective_gap_mm(plate(gap_mm=True))


class TestParallelPlateLimits(unittest.TestCase):
    def test_compliant_plate_has_no_findings(self):
        self.assertEqual(logic.check_parallel_plate_geometry(plate()), [])

    def test_extent_ratio_exactly_at_limit_passes_despite_representation_error(self):
        gap = 0.47
        extent = gap * logic.MIN_EXTENT_TO_GAP_RATIO
        # The extent is exactly ten gaps, yet the quotient lands a few units in
        # the last place under the limit: a compliant shape must still pass.
        self.assertLess(extent / gap, logic.MIN_EXTENT_TO_GAP_RATIO)
        geometry = plate(gap_mm=gap, surface_extent_mm=extent)
        self.assertEqual(logic.check_parallel_plate_geometry(geometry), [])

    def test_extent_ratio_below_limit_is_flagged(self):
        findings = logic.check_parallel_plate_geometry(
            plate(gap_mm=2.0, surface_extent_mm=12.0)
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("edge-effect", findings[0])

    def test_tilt_at_limit_passes(self):
        self.assertEqual(logic.check_parallel_plate_geometry(plate(tilt_deg=5.0)), [])

    def test_tilt_over_limit_is_flagged(self):
        findings = logic.check_parallel_plate_geometry(plate(tilt_deg=8.0))
        self.assertEqual(len(findings), 1)
        self.assertIn("quasi-parallel", findings[0])

    def test_two_violations_report_two_findings(self):
        findings = logic.check_parallel_plate_geometry(
            plate(gap_mm=2.0, surface_extent_mm=8.0, tilt_deg=20.0)
        )
        self.assertEqual(len(findings), 2)

    def test_negative_tilt_raises(self):
        with self.assertRaises(ValueError):
            logic.check_parallel_plate_geometry(plate(tilt_deg=-1.0))

    def test_tilt_of_ninety_degrees_raises(self):
        with self.assertRaises(ValueError):
            logic.check_parallel_plate_geometry(plate(tilt_deg=90.0))

    def test_missing_surface_extent_raises(self):
        geometry = plate()
        del geometry["surface_extent_mm"]
        with self.assertRaises(ValueError):
            logic.check_parallel_plate_geometry(geometry)


class TestCoaxialLimits(unittest.TestCase):
    def test_ratio_inside_band_has_no_findings(self):
        self.assertEqual(logic.check_coaxial_geometry(coax()), [])

    def test_ratio_at_band_floor_passes_despite_representation_error(self):
        inner = 1.19
        outer = inner + inner * 0.05
        self.assertLess(outer / inner, logic.MIN_COAXIAL_RADIUS_RATIO)
        geometry = coax(inner_radius_mm=inner, outer_radius_mm=outer)
        self.assertEqual(logic.check_coaxial_geometry(geometry), [])

    def test_ratio_at_band_ceiling_passes_despite_representation_error(self):
        inner = 0.98
        outer = 4.9
        self.assertGreater(outer / inner, logic.MAX_COAXIAL_RADIUS_RATIO)
        geometry = coax(inner_radius_mm=inner, outer_radius_mm=outer)
        self.assertEqual(logic.check_coaxial_geometry(geometry), [])

    def test_ratio_below_band_floor_is_flagged(self):
        findings = logic.check_coaxial_geometry(
            coax(inner_radius_mm=10.0, outer_radius_mm=10.2)
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("floor", findings[0])

    def test_ratio_above_band_ceiling_is_flagged(self):
        findings = logic.check_coaxial_geometry(
            coax(inner_radius_mm=1.0, outer_radius_mm=9.0)
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("ceiling", findings[0])

    def test_ratio_exactly_at_ceiling_passes(self):
        self.assertEqual(
            logic.check_coaxial_geometry(coax(inner_radius_mm=2.0, outer_radius_mm=10.0)),
            [],
        )

    def test_negative_inner_radius_raises(self):
        with self.assertRaises(ValueError):
            logic.check_coaxial_geometry(coax(inner_radius_mm=-1.0))


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(
            logic.frequency_gap_product_ghz_mm(12.5, 0.4), 5.0, places=12
        )

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product_ghz_mm(0.0, 1.0)

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product_ghz_mm(1.0, -2.0)

    def test_product_below_charted_floor_is_flagged(self):
        findings = logic.check_chart_range(0.005)
        self.assertEqual(len(findings), 1)
        self.assertIn("below", findings[0])

    def test_product_above_charted_ceiling_is_flagged(self):
        findings = logic.check_chart_range(250.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("above", findings[0])

    def test_product_exactly_at_floor_and_ceiling_pass(self):
        self.assertEqual(logic.check_chart_range(logic.FD_MIN_GHZ_MM), [])
        self.assertEqual(logic.check_chart_range(logic.FD_MAX_GHZ_MM), [])

    def test_product_at_ceiling_passes_despite_representation_error(self):
        frequency_ghz = 11.0
        gap_mm = logic.FD_MAX_GHZ_MM / frequency_ghz
        product = logic.frequency_gap_product_ghz_mm(frequency_ghz, gap_mm)
        self.assertGreater(product, logic.FD_MAX_GHZ_MM)
        self.assertEqual(logic.check_chart_range(product), [])


class TestEvaluateLevelOneGeometry(unittest.TestCase):
    def test_eligible_plate_returns_chart_lookup(self):
        record = logic.evaluate_level_one_geometry(plate(), 4.0)
        self.assertTrue(record["level_one_eligible"])
        self.assertEqual(record["next_step"], logic.NEXT_STEP_CHART)
        self.assertAlmostEqual(record["frequency_gap_product_ghz_mm"], 4.0, places=12)
        self.assertEqual(record["shape"], logic.PARALLEL_PLATE)

    def test_eligible_coax_carries_radial_gap(self):
        record = logic.evaluate_level_one_geometry(coax(), 2.0)
        self.assertTrue(record["level_one_eligible"])
        self.assertAlmostEqual(record["effective_gap_mm"], 1.95, places=12)
        self.assertAlmostEqual(record["frequency_gap_product_ghz_mm"], 3.9, places=12)

    def test_uncategorized_shape_escalates_without_a_gap(self):
        record = logic.evaluate_level_one_geometry(
            {"region_id": "iris-1", "shape": "stepped-iris"}, 6.0
        )
        self.assertFalse(record["level_one_eligible"])
        self.assertIsNone(record["effective_gap_mm"])
        self.assertEqual(record["next_step"], logic.NEXT_STEP_ESCALATE)
        self.assertEqual(len(record["findings"]), 1)

    def test_edge_effect_violation_escalates(self):
        record = logic.evaluate_level_one_geometry(
            plate(gap_mm=2.0, surface_extent_mm=6.0), 4.0
        )
        self.assertFalse(record["level_one_eligible"])
        self.assertEqual(record["next_step"], logic.NEXT_STEP_ESCALATE)

    def test_out_of_chart_product_escalates_an_otherwise_clean_shape(self):
        record = logic.evaluate_level_one_geometry(
            plate(gap_mm=40.0, surface_extent_mm=800.0), 8.0
        )
        self.assertFalse(record["level_one_eligible"])
        self.assertIn("above", record["findings"][0])

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_level_one_geometry(plate(), 0.0)


class TestInventoryScreen(unittest.TestCase):
    def setUp(self):
        self.inventory = [
            plate(region_id="plate-a", gap_mm=1.0, surface_extent_mm=40.0),
            plate(region_id="plate-b", gap_mm=0.4, surface_extent_mm=40.0),
            coax(region_id="coax-a"),
            {"region_id": "iris-a", "shape": "corrugated-surface"},
        ]

    def test_driving_region_is_the_smallest_product(self):
        summary = logic.screen_gap_inventory(self.inventory, 5.0)
        self.assertEqual(summary["driving_region_id"], "plate-b")
        self.assertEqual(summary["eligible_count"], 3)

    def test_escalated_regions_are_listed(self):
        summary = logic.screen_gap_inventory(self.inventory, 5.0)
        self.assertEqual(summary["escalated_region_ids"], ["iris-a"])
        self.assertFalse(summary["inventory_level_one_eligible"])

    def test_clean_inventory_is_eligible(self):
        summary = logic.screen_gap_inventory(self.inventory[:3], 5.0)
        self.assertTrue(summary["inventory_level_one_eligible"])
        self.assertEqual(summary["escalated_region_ids"], [])

    def test_duplicate_region_id_raises(self):
        with self.assertRaises(ValueError):
            logic.screen_gap_inventory([plate(), plate()], 5.0)

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            logic.screen_gap_inventory([], 5.0)

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            logic.screen_gap_inventory([plate(), "coax"], 5.0)

    def test_select_driving_region_requires_an_eligible_record(self):
        records = [logic.evaluate_level_one_geometry(self.inventory[3], 5.0)]
        with self.assertRaises(ValueError):
            logic.select_driving_region(records)

    def test_select_driving_region_rejects_empty_sequence(self):
        with self.assertRaises(ValueError):
            logic.select_driving_region([])


if __name__ == "__main__":
    unittest.main()
