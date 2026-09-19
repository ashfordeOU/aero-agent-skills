"""Contract tests for the threaded-fastener specification check."""

import math
import unittest

from q7046_fastener_specifications_logic import (
    COARSE_PITCH_MM,
    EMBRITTLEMENT_RISK_CLASS_MPA,
    REQUIRED_FIELDS,
    STRESS_AREA_PITCH_COEFFICIENT,
    assess_specification,
    coarse_pitch_for,
    coating_class_consistency,
    material_class_consistency,
    missing_fields,
    parse_property_class,
    parse_thread_designation,
    proof_load_kn,
    tensile_stress_area_mm2,
)


def _spec(**overrides):
    specification = {
        "standard_reference": "EN ISO 4762",
        "thread_designation": "M6",
        "nominal_length_mm": 20.0,
        "property_class": "A2-70",
        "material_family": "austenitic-stainless",
        "coating": "passivated",
        "head_type": "hexagon-socket",
        "locking_feature": "none",
    }
    specification.update(overrides)
    return specification


class ThreadTests(unittest.TestCase):
    def test_coarse_pitch_comes_from_the_table(self):
        parsed = parse_thread_designation("M6")
        self.assertAlmostEqual(parsed["pitch_mm"], COARSE_PITCH_MM[6.0], places=9)
        self.assertEqual(parsed["series"], "coarse")

    def test_stated_fine_pitch_is_recognised(self):
        parsed = parse_thread_designation("M8x1")
        self.assertEqual(parsed["series"], "fine")
        self.assertTrue(parsed["pitch_stated"])

    def test_untabulated_diameter_needs_a_stated_pitch(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("M7")
        self.assertAlmostEqual(
            parse_thread_designation("M7x1")["pitch_mm"], 1.0, places=9
        )

    def test_non_metric_designation_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("10-32 UNF")

    def test_pitch_larger_than_diameter_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("M3x4")

    def test_coarse_pitch_lookup_rejects_an_untabulated_size(self):
        with self.assertRaises(ValueError):
            coarse_pitch_for(7.0)


class PropertyClassTests(unittest.TestCase):
    def test_steel_class_encodes_its_tensile_strength(self):
        self.assertAlmostEqual(
            parse_property_class("10.9")["tensile_strength_mpa"], 1000.0, places=9
        )

    def test_steel_class_encodes_its_yield_ratio(self):
        self.assertAlmostEqual(
            parse_property_class("8.8")["yield_strength_mpa"], 640.0, places=9
        )

    def test_highest_common_class_is_read_the_same_way(self):
        strengths = parse_property_class("12.9")
        self.assertAlmostEqual(strengths["tensile_strength_mpa"], 1200.0, places=9)
        self.assertAlmostEqual(strengths["yield_strength_mpa"], 1080.0, places=9)

    def test_stainless_class_is_tabulated(self):
        strengths = parse_property_class("A2-70")
        self.assertEqual(strengths["family_group"], "austenitic-stainless")
        self.assertAlmostEqual(strengths["tensile_strength_mpa"], 700.0, places=9)

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            parse_property_class("super-strong")

    def test_out_of_range_strength_figure_rejected(self):
        with self.assertRaises(ValueError):
            parse_property_class("99.9")

    def test_out_of_range_ratio_figure_rejected(self):
        with self.assertRaises(ValueError):
            parse_property_class("10.0")


class StressAreaTests(unittest.TestCase):
    def test_m6_coarse_stress_area(self):
        expected = math.pi * (6.0 - STRESS_AREA_PITCH_COEFFICIENT * 1.0) ** 2 / 4.0
        self.assertAlmostEqual(tensile_stress_area_mm2(6.0, 1.0), expected, places=9)

    def test_finer_pitch_gives_a_larger_area(self):
        self.assertGreater(
            tensile_stress_area_mm2(8.0, 1.0), tensile_stress_area_mm2(8.0, 1.25) + 0.1
        )

    def test_area_grows_with_diameter(self):
        self.assertGreater(
            tensile_stress_area_mm2(10.0, 1.5), tensile_stress_area_mm2(8.0, 1.25) + 1.0
        )

    def test_pitch_at_the_diameter_rejected(self):
        with self.assertRaises(ValueError):
            tensile_stress_area_mm2(3.0, 3.0)

    def test_negative_diameter_rejected(self):
        with self.assertRaises(ValueError):
            tensile_stress_area_mm2(-6.0, 1.0)


class ProofLoadTests(unittest.TestCase):
    def test_proof_load_follows_area_and_proof_stress(self):
        result = proof_load_kn("10.9", 6.0, 1.0)
        self.assertAlmostEqual(
            result["proof_load_kn"],
            result["stress_area_mm2"] * result["proof_stress_mpa"] / 1000.0,
            places=9,
        )

    def test_proof_stress_is_the_ratio_of_the_yield_strength(self):
        result = proof_load_kn("10.9", 6.0, 1.0, proof_ratio=0.9)
        self.assertAlmostEqual(result["proof_stress_mpa"], 810.0, places=9)

    def test_tensile_load_exceeds_the_proof_load(self):
        result = proof_load_kn("8.8", 8.0, 1.25)
        self.assertGreater(result["tensile_load_kn"], result["proof_load_kn"] + 1.0)

    def test_higher_class_carries_more(self):
        low = proof_load_kn("8.8", 6.0, 1.0)["proof_load_kn"]
        high = proof_load_kn("12.9", 6.0, 1.0)["proof_load_kn"]
        self.assertGreater(high, low + 1.0)

    def test_proof_ratio_of_one_reaches_the_yield_strength(self):
        result = proof_load_kn("10.9", 6.0, 1.0, proof_ratio=1.0)
        self.assertAlmostEqual(result["proof_stress_mpa"], 900.0, places=9)

    def test_proof_ratio_above_one_rejected(self):
        with self.assertRaises(ValueError):
            proof_load_kn("10.9", 6.0, 1.0, proof_ratio=1.2)


class ConsistencyTests(unittest.TestCase):
    def test_matched_stainless_class_and_material_is_clean(self):
        self.assertEqual(
            material_class_consistency("austenitic-stainless", "A2-70"), []
        )

    def test_stainless_class_on_alloy_steel_is_flagged(self):
        self.assertEqual(
            len(material_class_consistency("alloy-steel", "A4-80")), 1
        )

    def test_steel_class_on_titanium_is_flagged(self):
        self.assertEqual(len(material_class_consistency("titanium", "10.9")), 1)

    def test_high_class_on_plain_carbon_steel_is_flagged(self):
        findings = material_class_consistency("carbon-steel", "12.9")
        self.assertTrue(any("carbon steel" in f for f in findings))

    def test_unknown_material_family_rejected(self):
        with self.assertRaises(ValueError):
            material_class_consistency("unobtainium", "10.9")

    def test_electroplating_a_high_class_is_flagged(self):
        findings = coating_class_consistency("electroplated-zinc", "12.9")
        self.assertTrue(any("hydrogen" in f for f in findings))

    def test_electroplating_at_the_risk_threshold_is_flagged(self):
        strengths = parse_property_class("10.9")
        self.assertAlmostEqual(
            strengths["tensile_strength_mpa"], EMBRITTLEMENT_RISK_CLASS_MPA, places=9
        )
        self.assertTrue(
            any("hydrogen" in f for f in coating_class_consistency("electroplated-zinc", "10.9"))
        )

    def test_electroplating_a_low_class_raises_no_hydrogen_finding(self):
        self.assertEqual(coating_class_consistency("electroplated-zinc", "8.8"), [])

    def test_cadmium_is_always_flagged(self):
        self.assertTrue(coating_class_consistency("electroplated-cadmium", "8.8"))

    def test_anodising_a_steel_class_is_flagged(self):
        self.assertEqual(len(coating_class_consistency("anodised", "8.8")), 1)

    def test_unknown_coating_rejected(self):
        with self.assertRaises(ValueError):
            coating_class_consistency("gold-leaf", "8.8")


class SpecificationTests(unittest.TestCase):
    def test_complete_description_is_buyable(self):
        result = assess_specification(_spec())
        self.assertTrue(result["buyable"])
        self.assertEqual(result["findings"], [])

    def test_every_required_field_is_checked(self):
        for field in REQUIRED_FIELDS:
            specification = _spec()
            del specification[field]
            self.assertIn(field, missing_fields(specification))

    def test_blank_field_counts_as_missing(self):
        self.assertIn("head_type", missing_fields(_spec(head_type="   ")))

    def test_gaps_short_circuit_the_numeric_work(self):
        result = assess_specification(_spec(standard_reference=None))
        self.assertFalse(result["buyable"])
        self.assertIsNone(result["loads"])

    def test_loads_are_computed_for_a_complete_description(self):
        result = assess_specification(_spec(property_class="10.9",
                                            material_family="alloy-steel"))
        self.assertAlmostEqual(
            result["loads"]["stress_area_mm2"],
            tensile_stress_area_mm2(6.0, COARSE_PITCH_MM[6.0]),
            places=9,
        )

    def test_length_shorter_than_the_diameter_is_flagged(self):
        result = assess_specification(_spec(nominal_length_mm=4.0))
        self.assertFalse(result["buyable"])

    def test_material_mismatch_reaches_the_verdict(self):
        result = assess_specification(_spec(material_family="titanium"))
        self.assertFalse(result["buyable"])

    def test_coating_mismatch_reaches_the_verdict(self):
        result = assess_specification(
            _spec(property_class="12.9", material_family="alloy-steel",
                  coating="electroplated-zinc")
        )
        self.assertFalse(result["buyable"])

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            missing_fields(["standard_reference"])

    def test_bad_thread_designation_is_refused(self):
        with self.assertRaises(ValueError):
            assess_specification(_spec(thread_designation="M7"))

    def test_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_specification(_spec(nominal_length_mm=-20.0))


if __name__ == "__main__":
    unittest.main()
