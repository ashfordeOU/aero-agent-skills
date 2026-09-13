#!/usr/bin/env python3
"""Gate 3 contract test for e2001-analysis-level-two-requirements.

stdlib unittest, offline, deterministic.  Run: python3 test_...py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2001_analysis_level_two_requirements_logic as L  # noqa: E402


def base_item(**over):
    item = {
        "item_id": "RF-001",
        "equipment_type": "uniform-waveguide-section",
        "frequency_ghz": 12.0,
        "gap_mm": 2.0,
        "peak_field_v_per_m": 1000.0,
        "mean_field_v_per_m": 1000.0,
        "first_level_margin_db": 6.0,
        "required_margin_db": 4.0,
        "secondary_emission_dataset": "SEY-AG-AIR",
        "field_model_id": "FM-3D-001",
        "tracking_solver_validation": "VAL-2024-07",
    }
    item.update(over)
    return item


class TestNormalizeEquipmentType(unittest.TestCase):
    def test_known_key_passes_through(self):
        self.assertEqual(
            L.normalize_equipment_type("coaxial-connector"), "coaxial-connector"
        )

    def test_alias_is_folded(self):
        self.assertEqual(
            L.normalize_equipment_type("waveguide"), "uniform-waveguide-section"
        )

    def test_case_and_separator_are_normalized(self):
        self.assertEqual(
            L.normalize_equipment_type("  Rotary_Joint "), "rotary-joint"
        )

    def test_microstrip_alias_is_the_dielectric_exposed_profile(self):
        self.assertEqual(
            L.normalize_equipment_type("microstrip"), "exposed-dielectric-printed-line"
        )

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_equipment_type("plasma-thruster")

    def test_blank_type_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_equipment_type("   ")

    def test_non_string_type_raises(self):
        with self.assertRaises(ValueError):
            L.normalize_equipment_type(7)


class TestEquipmentProfile(unittest.TestCase):
    def test_profile_carries_the_normalized_key(self):
        profile = L.equipment_profile("iris-filter")
        self.assertEqual(profile["equipment_type"], "waveguide-iris-filter")
        self.assertFalse(profile["chart_representable"])
        self.assertTrue(profile["second_level_admissible"])

    def test_profile_is_a_copy(self):
        profile = L.equipment_profile("coax")
        profile["chart_representable"] = False
        self.assertTrue(
            L.EQUIPMENT_PROFILES["coaxial-line-section"]["chart_representable"]
        )

    def test_dielectric_exposed_profile_is_not_admissible(self):
        profile = L.equipment_profile("dielectric-loaded-resonator")
        self.assertFalse(profile["second_level_admissible"])


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_value(self):
        self.assertAlmostEqual(L.frequency_gap_product(12.0, 2.5), 30.0, places=9)

    def test_zero_gap_raises(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product(12.0, 0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product(-1.0, 2.0)

    def test_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product(True, 2.0)

    def test_non_finite_raises(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product(float("inf"), 2.0)


class TestChartBand(unittest.TestCase):
    def test_inside_band(self):
        self.assertTrue(L.within_chart_band(24.0))

    def test_lower_boundary_absorbs_representation_error(self):
        product = math.nextafter(L.CHART_BAND_GHZ_MM[0], 0.0)
        self.assertLess(product, L.CHART_BAND_GHZ_MM[0])
        self.assertTrue(L.within_chart_band(product))

    def test_upper_boundary_is_inclusive(self):
        self.assertTrue(L.within_chart_band(100.0))

    def test_upper_boundary_absorbs_representation_error(self):
        product = math.nextafter(L.CHART_BAND_GHZ_MM[1], 1000.0)
        self.assertGreater(product, L.CHART_BAND_GHZ_MM[1])
        self.assertTrue(L.within_chart_band(product))

    def test_below_band(self):
        self.assertFalse(L.within_chart_band(0.02))

    def test_above_band(self):
        self.assertFalse(L.within_chart_band(180.0))

    def test_zero_product_raises(self):
        with self.assertRaises(ValueError):
            L.within_chart_band(0.0)


class TestFieldUniformityRatio(unittest.TestCase):
    def test_ratio_value(self):
        self.assertAlmostEqual(L.field_uniformity_ratio(1500.0, 1000.0), 1.5, places=9)

    def test_uniform_field_is_unity(self):
        self.assertAlmostEqual(L.field_uniformity_ratio(800.0, 800.0), 1.0, places=12)

    def test_one_ulp_below_unity_is_absorbed(self):
        peak = 0.3 - 0.1
        self.assertLess(peak, 0.2)
        self.assertAlmostEqual(L.field_uniformity_ratio(peak, 0.2), 1.0, places=12)

    def test_peak_below_mean_raises(self):
        with self.assertRaises(ValueError):
            L.field_uniformity_ratio(500.0, 900.0)

    def test_zero_mean_raises(self):
        with self.assertRaises(ValueError):
            L.field_uniformity_ratio(500.0, 0.0)


class TestFirstLevelOutcome(unittest.TestCase):
    def test_adequate(self):
        self.assertEqual(L.first_level_outcome(6.0, 4.0), "adequate")

    def test_shortfall(self):
        self.assertEqual(L.first_level_outcome(2.0, 4.0), "shortfall")

    def test_exact_equality_is_adequate(self):
        self.assertEqual(L.first_level_outcome(4.0, 4.0), "adequate")

    def test_one_ulp_below_the_limit_is_still_adequate(self):
        margin = 0.3 - 0.1
        self.assertLess(margin, 0.2)
        self.assertEqual(L.first_level_outcome(margin, 0.2), "adequate")

    def test_non_numeric_margin_raises(self):
        with self.assertRaises(ValueError):
            L.first_level_outcome("6 dB", 4.0)

    def test_non_finite_margin_raises(self):
        with self.assertRaises(ValueError):
            L.first_level_outcome(float("nan"), 4.0)

    def test_non_positive_requirement_raises(self):
        with self.assertRaises(ValueError):
            L.first_level_outcome(6.0, 0.0)


class TestDetermineAnalysisLevel(unittest.TestCase):
    def test_chart_representable_with_margin_stays_at_first_level(self):
        verdict = L.determine_analysis_level(base_item())
        self.assertEqual(verdict["level"], "first-level-sufficient")
        self.assertEqual(verdict["drivers"], [])
        self.assertTrue(verdict["chart_applicable"])
        self.assertEqual(verdict["first_level_margin_state"], "adequate")

    def test_margin_shortfall_drives_the_second_level(self):
        verdict = L.determine_analysis_level(base_item(first_level_margin_db=1.0))
        self.assertEqual(verdict["level"], "second-level-required")
        self.assertIn("first-level-margin-shortfall", verdict["drivers"])

    def test_non_representable_geometry_drives_the_second_level(self):
        verdict = L.determine_analysis_level(base_item(equipment_type="iris-filter"))
        self.assertEqual(verdict["level"], "second-level-required")
        self.assertIn("geometry-not-chart-representable", verdict["drivers"])
        self.assertFalse(verdict["chart_applicable"])
        self.assertEqual(verdict["first_level_margin_state"], "not-evaluated")

    def test_product_outside_the_band_drives_the_second_level(self):
        verdict = L.determine_analysis_level(base_item(gap_mm=40.0))
        self.assertIn("frequency-gap-product-outside-chart-band", verdict["drivers"])
        self.assertEqual(verdict["level"], "second-level-required")

    def test_field_non_uniformity_drives_the_second_level(self):
        verdict = L.determine_analysis_level(base_item(peak_field_v_per_m=2000.0))
        self.assertIn("field-non-uniformity-above-limit", verdict["drivers"])
        self.assertAlmostEqual(verdict["field_uniformity_ratio"], 2.0, places=9)

    def test_uniformity_exactly_at_the_limit_is_accepted(self):
        verdict = L.determine_analysis_level(base_item(peak_field_v_per_m=1200.0))
        self.assertNotIn("field-non-uniformity-above-limit", verdict["drivers"])
        self.assertEqual(verdict["level"], "first-level-sufficient")

    def test_missing_margin_record_is_a_driver(self):
        item = base_item()
        del item["first_level_margin_db"]
        verdict = L.determine_analysis_level(item)
        self.assertIn("first-level-margin-not-on-record", verdict["drivers"])
        self.assertEqual(verdict["level"], "second-level-required")

    def test_dielectric_exposed_item_routes_to_hardware(self):
        verdict = L.determine_analysis_level(
            base_item(equipment_type="dielectric-loaded-resonator")
        )
        self.assertEqual(verdict["level"], "multipactor-test-required")
        self.assertIn("second-level-model-not-admissible", verdict["drivers"])

    def test_custom_uniformity_limit_is_honoured(self):
        item = base_item(peak_field_v_per_m=1300.0)
        verdict = L.determine_analysis_level(item, uniformity_limit=1.5)
        self.assertEqual(verdict["level"], "first-level-sufficient")

    def test_invalid_uniformity_limit_raises(self):
        with self.assertRaises(ValueError):
            L.determine_analysis_level(base_item(), uniformity_limit=0.0)

    def test_missing_required_key_raises(self):
        item = base_item()
        del item["gap_mm"]
        with self.assertRaises(ValueError):
            L.determine_analysis_level(item)

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            L.determine_analysis_level(["RF-001"])

    def test_blank_item_id_raises(self):
        with self.assertRaises(ValueError):
            L.determine_analysis_level(base_item(item_id="  "))


class TestSecondLevelPrerequisites(unittest.TestCase):
    def test_complete_record_has_nothing_missing(self):
        self.assertEqual(L.second_level_prerequisites(base_item()), [])

    def test_absent_key_is_missing(self):
        item = base_item()
        del item["field_model_id"]
        self.assertEqual(L.second_level_prerequisites(item), ["field_model_id"])

    def test_blank_string_counts_as_missing(self):
        item = base_item(tracking_solver_validation="   ")
        self.assertIn("tracking_solver_validation", L.second_level_prerequisites(item))

    def test_all_three_can_be_missing(self):
        item = base_item()
        for key in L.SECOND_LEVEL_PREREQUISITES:
            item[key] = None
        self.assertEqual(
            L.second_level_prerequisites(item), list(L.SECOND_LEVEL_PREREQUISITES)
        )

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            L.second_level_prerequisites("RF-001")


class TestAssessEquipmentItem(unittest.TestCase):
    def test_ready_for_the_second_level(self):
        result = L.assess_equipment_item(base_item(equipment_type="rotary-joint"))
        self.assertEqual(result["level"], "second-level-required")
        self.assertTrue(result["ready_for_second_level"])
        self.assertTrue(result["compliant"])

    def test_missing_prerequisite_is_a_finding(self):
        item = base_item(equipment_type="rotary-joint", field_model_id=None)
        result = L.assess_equipment_item(item)
        self.assertIn("second-level-prerequisite-missing", result["findings"])
        self.assertFalse(result["ready_for_second_level"])
        self.assertFalse(result["compliant"])

    def test_hardware_route_is_a_finding(self):
        result = L.assess_equipment_item(
            base_item(equipment_type="exposed-dielectric-printed-line")
        )
        self.assertIn("route-to-seeded-multipactor-test", result["findings"])

    def test_first_level_item_needs_no_prerequisites(self):
        item = base_item()
        for key in L.SECOND_LEVEL_PREREQUISITES:
            item[key] = None
        result = L.assess_equipment_item(item)
        self.assertEqual(result["level"], "first-level-sufficient")
        self.assertTrue(result["compliant"])


class TestAssessEquipmentInventory(unittest.TestCase):
    def test_counts_across_the_inventory(self):
        report = L.assess_equipment_inventory(
            [
                base_item(item_id="RF-001"),
                base_item(item_id="RF-002", equipment_type="iris-filter"),
                base_item(item_id="RF-003", equipment_type="dielectric-loaded-resonator"),
            ]
        )
        self.assertEqual(report["counts"]["first-level-sufficient"], 1)
        self.assertEqual(report["counts"]["second-level-required"], 1)
        self.assertEqual(report["counts"]["multipactor-test-required"], 1)
        self.assertEqual(report["open_findings"], ["RF-003"])
        self.assertFalse(report["compliant"])

    def test_all_clean_inventory_is_compliant(self):
        report = L.assess_equipment_inventory(
            [base_item(item_id="RF-001"), base_item(item_id="RF-002")]
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["open_findings"], [])

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            L.assess_equipment_inventory([])

    def test_non_list_inventory_raises(self):
        with self.assertRaises(ValueError):
            L.assess_equipment_inventory(base_item())

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            L.assess_equipment_inventory([base_item(), base_item()])


if __name__ == "__main__":
    unittest.main()
