#!/usr/bin/env python3
"""Contract test for the clause 7.2.2 solar-array arc-characterization logic."""

import unittest

from e2006_solar_array_arc_general_requirement_logic import (
    BOND_PATH_RESISTANCE_LIMIT_OHM,
    MINIMUM_INCEPTION_VOLTAGE_V,
    UNGROUNDED_DIELECTRIC_AREA_LIMIT_CM2,
    arc_characterization_scope,
    assess_grounding_provisions,
    assess_solar_array_arc_requirement,
    element_grounding_finding,
    inception_margin,
    predicted_primary_arc_count,
    primary_arc_inception_threshold,
    validate_surface_element,
    worst_case_differential_potential,
)


def bonded_interconnect(element_id="ic-1", segments=(1.0e4, 2.0e4)):
    return {
        "id": element_id,
        "type": "interconnect",
        "exposed_area_cm2": 2.0,
        "bond_path_segments_ohm": list(segments),
    }


def bare_coverglass(element_id="cg-1", area=4.0):
    return {"id": element_id, "type": "coverglass", "exposed_area_cm2": area}


class SurfaceElementValidationTests(unittest.TestCase):
    def test_conductive_element_is_categorized_as_conductive(self):
        item = validate_surface_element(bonded_interconnect())
        self.assertEqual(item["category"], "conductive")

    def test_dielectric_element_is_categorized_as_dielectric(self):
        item = validate_surface_element(bare_coverglass())
        self.assertEqual(item["category"], "dielectric")

    def test_bond_path_segments_are_summed(self):
        item = validate_surface_element(bonded_interconnect(segments=(1.0e4, 2.0e4, 3.0e4)))
        self.assertAlmostEqual(item["bond_path_ohm"], 6.0e4, places=6)

    def test_unknown_element_type_is_rejected(self):
        bad = {"id": "x-1", "type": "sunshade-fabric", "exposed_area_cm2": 1.0}
        with self.assertRaises(ValueError):
            validate_surface_element(bad)

    def test_missing_id_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_element({"type": "coverglass", "exposed_area_cm2": 1.0})

    def test_non_mapping_element_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_element(["coverglass", 1.0])

    def test_zero_exposed_area_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_element(bare_coverglass(area=0.0))

    def test_negative_bond_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_element(bonded_interconnect(segments=(1.0e4, -5.0)))

    def test_empty_bond_segment_list_is_rejected(self):
        bad = {
            "id": "ic-2",
            "type": "interconnect",
            "exposed_area_cm2": 1.0,
            "bond_path_segments_ohm": [],
        }
        with self.assertRaises(ValueError):
            validate_surface_element(bad)


class GroundingProvisionTests(unittest.TestCase):
    def test_bonded_conductor_passes(self):
        finding = element_grounding_finding(bonded_interconnect())
        self.assertTrue(finding["compliant"])

    def test_floating_conductor_fails(self):
        floating = {"id": "bb-1", "type": "busbar", "exposed_area_cm2": 3.0}
        finding = element_grounding_finding(floating)
        self.assertFalse(finding["compliant"])
        self.assertIn("floating", finding["reason"])

    def test_bond_path_above_limit_fails(self):
        finding = element_grounding_finding(
            bonded_interconnect(segments=(9.0e5, 9.0e5))
        )
        self.assertFalse(finding["compliant"])

    def test_bond_path_summed_to_the_limit_is_absorbed(self):
        # Eleven equal series segments total the limit exactly in exact
        # arithmetic but land two ULP above it in binary floating point.
        segments = [BOND_PATH_RESISTANCE_LIMIT_OHM / 11.0] * 11
        accumulated = 0.0
        for segment in segments:
            accumulated += segment
        self.assertGreater(accumulated, BOND_PATH_RESISTANCE_LIMIT_OHM)
        finding = element_grounding_finding(
            bonded_interconnect(segments=tuple(segments))
        )
        self.assertTrue(finding["compliant"])

    def test_small_ungrounded_dielectric_passes(self):
        finding = element_grounding_finding(bare_coverglass(area=4.0))
        self.assertTrue(finding["compliant"])

    def test_dielectric_at_the_area_allowance_passes(self):
        finding = element_grounding_finding(
            bare_coverglass(area=UNGROUNDED_DIELECTRIC_AREA_LIMIT_CM2)
        )
        self.assertTrue(finding["compliant"])

    def test_large_ungrounded_dielectric_fails(self):
        finding = element_grounding_finding(bare_coverglass(area=250.0))
        self.assertFalse(finding["compliant"])
        self.assertIn("exceeds", finding["reason"])

    def test_coated_dielectric_with_bleed_path_passes(self):
        coated = {
            "id": "cg-2",
            "type": "coverglass",
            "exposed_area_cm2": 400.0,
            "surface_resistivity_ohm_per_square": 5.0e7,
            "bond_path_segments_ohm": [2.0e4],
        }
        self.assertTrue(element_grounding_finding(coated)["compliant"])

    def test_coated_dielectric_without_bleed_path_fails(self):
        coated = {
            "id": "cg-3",
            "type": "coverglass",
            "exposed_area_cm2": 400.0,
            "surface_resistivity_ohm_per_square": 5.0e7,
        }
        finding = element_grounding_finding(coated)
        self.assertFalse(finding["compliant"])
        self.assertIn("bleed path", finding["reason"])

    def test_aggregate_reports_deficient_ids(self):
        result = assess_grounding_provisions(
            [bonded_interconnect(), bare_coverglass(area=90.0)]
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["deficient_ids"], ["cg-1"])
        self.assertEqual(result["element_count"], 2)

    def test_aggregate_rejects_empty_inventory(self):
        with self.assertRaises(ValueError):
            assess_grounding_provisions([])

    def test_aggregate_rejects_duplicate_ids(self):
        with self.assertRaises(ValueError):
            assess_grounding_provisions([bare_coverglass(), bare_coverglass()])


class InceptionThresholdTests(unittest.TestCase):
    def test_reference_geometry_returns_base_threshold(self):
        self.assertAlmostEqual(
            primary_arc_inception_threshold(100.0, 0.90, 20.0), 120.0, places=9
        )

    def test_thicker_coverglass_raises_the_threshold(self):
        thin = primary_arc_inception_threshold(100.0, 0.90, 20.0)
        thick = primary_arc_inception_threshold(400.0, 0.90, 20.0)
        self.assertGreater(thick, thin)
        self.assertAlmostEqual(thick, 240.0, places=9)

    def test_wider_gap_raises_the_threshold(self):
        narrow = primary_arc_inception_threshold(100.0, 0.90, 20.0)
        wide = primary_arc_inception_threshold(100.0, 1.90, 20.0)
        self.assertAlmostEqual(wide, narrow * 1.35, places=9)

    def test_cold_surface_lowers_the_threshold(self):
        cold = primary_arc_inception_threshold(100.0, 0.90, -100.0)
        warm = primary_arc_inception_threshold(100.0, 0.90, 20.0)
        self.assertLess(cold, warm)

    def test_threshold_is_clamped_at_the_floor(self):
        value = primary_arc_inception_threshold(1.0, 0.90, -200.0)
        self.assertAlmostEqual(value, MINIMUM_INCEPTION_VOLTAGE_V, places=9)

    def test_zero_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            primary_arc_inception_threshold(0.0, 0.90, 20.0)

    def test_negative_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            primary_arc_inception_threshold(100.0, -0.1, 20.0)

    def test_temperature_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            primary_arc_inception_threshold(100.0, 0.90, -300.0)


class DifferentialPotentialTests(unittest.TestCase):
    def test_differential_is_a_magnitude(self):
        self.assertAlmostEqual(
            worst_case_differential_potential(-180.0, 20.0), 200.0, places=9
        )

    def test_string_bias_shifts_the_conductor(self):
        self.assertAlmostEqual(
            worst_case_differential_potential(-100.0, 10.0, 40.0), 150.0, places=9
        )

    def test_non_numeric_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_differential_potential("-180", 20.0)

    def test_margin_below_threshold_is_not_inception(self):
        margin = inception_margin(90.0, 120.0)
        self.assertFalse(margin["inception_reached"])
        self.assertAlmostEqual(margin["margin_v"], 30.0, places=9)
        self.assertAlmostEqual(margin["ratio"], 0.75, places=9)

    def test_margin_above_threshold_is_inception(self):
        self.assertTrue(inception_margin(200.0, 120.0)["inception_reached"])

    def test_summed_potential_at_the_threshold_is_inception(self):
        # -0.02 V surface against a 0.02 V conductor on a 119.96 V string bias
        # is exactly 120 V physically, but sums one ULP low in binary.
        differential = worst_case_differential_potential(-0.02, 0.02, 119.96)
        threshold = primary_arc_inception_threshold(100.0, 0.90, 20.0)
        self.assertLess(differential, threshold)
        self.assertTrue(inception_margin(differential, threshold)["inception_reached"])

    def test_negative_differential_is_rejected(self):
        with self.assertRaises(ValueError):
            inception_margin(-5.0, 120.0)

    def test_zero_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            inception_margin(90.0, 0.0)


class ArcCountTests(unittest.TestCase):
    def test_below_inception_predicts_no_arcs(self):
        self.assertAlmostEqual(
            predicted_primary_arc_count(90.0, 120.0, 2.0, 1000.0), 0.0, places=12
        )

    def test_overdrive_predicts_arcs(self):
        count = predicted_primary_arc_count(240.0, 120.0, 2.0, 100.0)
        self.assertAlmostEqual(count, 0.02 * 2.0 * (1.0 ** 1.6) * 100.0, places=9)

    def test_arc_count_grows_with_junction_length(self):
        short = predicted_primary_arc_count(240.0, 120.0, 1.0, 100.0)
        long = predicted_primary_arc_count(240.0, 120.0, 4.0, 100.0)
        self.assertGreater(long, short)

    def test_zero_exposure_predicts_no_arcs(self):
        self.assertAlmostEqual(
            predicted_primary_arc_count(240.0, 120.0, 2.0, 0.0), 0.0, places=12
        )

    def test_negative_exposure_is_rejected(self):
        with self.assertRaises(ValueError):
            predicted_primary_arc_count(240.0, 120.0, 2.0, -1.0)

    def test_zero_junction_length_is_rejected(self):
        with self.assertRaises(ValueError):
            predicted_primary_arc_count(240.0, 120.0, 0.0, 10.0)


class ScopeAndAssessmentTests(unittest.TestCase):
    def test_compliant_array_below_inception_needs_no_scope(self):
        self.assertEqual(arc_characterization_scope(True, False, 28.0), [])

    def test_grounding_deficiency_drives_scope(self):
        scope = arc_characterization_scope(False, False, 28.0)
        self.assertIn("grounding-deficiency-justification", scope)
        self.assertIn("inception-threshold-determination", scope)

    def test_inception_drives_rate_prediction(self):
        scope = arc_characterization_scope(True, True, 28.0)
        self.assertIn("primary-arc-rate-prediction", scope)
        self.assertNotIn("grounding-deficiency-justification", scope)

    def test_high_string_voltage_adds_sustained_review(self):
        scope = arc_characterization_scope(False, True, 100.0)
        self.assertIn("sustained-arc-susceptibility-review", scope)

    def test_scope_rejects_non_boolean_flag(self):
        with self.assertRaises(ValueError):
            arc_characterization_scope("yes", True, 100.0)

    def test_assessment_of_compliant_array(self):
        design = {
            "surface_elements": [bonded_interconnect(), bare_coverglass(area=5.0)],
            "coverglass_thickness_um": 100.0,
            "interconnect_gap_mm": 0.90,
            "temperature_c": 20.0,
            "coverglass_potential_v": -40.0,
            "interconnect_potential_v": 10.0,
            "string_voltage_v": 28.0,
            "triple_junction_length_m": 3.0,
            "exposure_hours": 5000.0,
        }
        result = assess_solar_array_arc_requirement(design)
        self.assertTrue(result["compliant_without_characterization"])
        self.assertEqual(result["drivers"], [])
        self.assertAlmostEqual(result["predicted_primary_arcs"], 0.0, places=12)

    def test_assessment_of_ungrounded_high_voltage_array(self):
        design = {
            "surface_elements": [
                {"id": "bb-9", "type": "busbar", "exposed_area_cm2": 6.0},
                bare_coverglass(area=800.0),
            ],
            "coverglass_thickness_um": 100.0,
            "interconnect_gap_mm": 0.90,
            "temperature_c": -90.0,
            "coverglass_potential_v": -300.0,
            "interconnect_potential_v": 0.0,
            "string_bias_v": 60.0,
            "string_voltage_v": 100.0,
            "triple_junction_length_m": 12.0,
            "exposure_hours": 8760.0,
        }
        result = assess_solar_array_arc_requirement(design)
        self.assertTrue(result["characterization_required"])
        self.assertIn("grounding-provisions-not-satisfied", result["drivers"])
        self.assertIn("differential-potential-at-or-above-inception", result["drivers"])
        self.assertIn("sustained-arc-susceptibility-review", result["characterization_scope"])
        self.assertGreater(result["predicted_primary_arcs"], 0.0)

    def test_assessment_rejects_missing_key(self):
        with self.assertRaises(ValueError):
            assess_solar_array_arc_requirement({"surface_elements": [bare_coverglass()]})

    def test_assessment_rejects_non_mapping_design(self):
        with self.assertRaises(ValueError):
            assess_solar_array_arc_requirement("array-1")


if __name__ == "__main__":
    unittest.main()
