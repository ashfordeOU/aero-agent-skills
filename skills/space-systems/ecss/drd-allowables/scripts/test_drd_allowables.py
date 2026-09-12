"""
Gate 3 contract tests — drd-allowables (ECSS-E-ST-32C Annex H MMPA).
stdlib unittest only. Offline. Deterministic.
Run: python3 test_drd_allowables.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import drd_allowables_logic as logic


class TestValidateBasis(unittest.TestCase):

    def test_a_basis_accepted(self):
        self.assertTrue(logic.validate_basis("A"))

    def test_b_basis_accepted(self):
        self.assertTrue(logic.validate_basis("B"))

    def test_s_basis_accepted(self):
        self.assertTrue(logic.validate_basis("S"))

    def test_typical_basis_accepted(self):
        self.assertTrue(logic.validate_basis("TYPICAL"))

    def test_lowercase_basis_accepted(self):
        self.assertTrue(logic.validate_basis("a"))

    def test_invalid_basis_rejected(self):
        self.assertFalse(logic.validate_basis("X"))

    def test_empty_basis_rejected(self):
        self.assertFalse(logic.validate_basis(""))


class TestCategorizeMaterial(unittest.TestCase):

    def test_metallic_normalised(self):
        self.assertEqual(logic.categorize_material("metallic"), "metallic")

    def test_composite_normalised(self):
        self.assertEqual(logic.categorize_material("composite"), "composite")

    def test_adhesive_normalised(self):
        self.assertEqual(logic.categorize_material("adhesive"), "adhesive")

    def test_fastener_normalised(self):
        self.assertEqual(logic.categorize_material("fastener"), "fastener")

    def test_mixed_case_accepted(self):
        self.assertEqual(logic.categorize_material("Metallic"), "metallic")

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_material("polymer")

    def test_empty_family_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_material("")


class TestPropertyCompleteness(unittest.TestCase):

    def test_metallic_complete(self):
        props = {"Ftu", "Fty", "Fcy", "Fsu", "E", "density"}
        result = logic.check_property_completeness("metallic", props)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_metallic_missing_ftu(self):
        props = {"Fty", "Fcy", "Fsu", "E", "density"}
        result = logic.check_property_completeness("metallic", props)
        self.assertFalse(result["complete"])
        self.assertIn("Ftu", result["missing"])

    def test_composite_complete(self):
        props = {"F1tu", "F1cu", "F2tu", "F2cu", "F12su", "E11", "E22", "G12", "nu12"}
        result = logic.check_property_completeness("composite", props)
        self.assertTrue(result["complete"])

    def test_fastener_complete(self):
        props = {"Fstu", "Fsbru", "diameter"}
        result = logic.check_property_completeness("fastener", props)
        self.assertTrue(result["complete"])

    def test_fastener_missing_diameter(self):
        props = {"Fstu", "Fsbru"}
        result = logic.check_property_completeness("fastener", props)
        self.assertFalse(result["complete"])
        self.assertIn("diameter", result["missing"])

    def test_adhesive_complete(self):
        props = {"shear_strength", "peel_strength", "E"}
        result = logic.check_property_completeness("adhesive", props)
        self.assertTrue(result["complete"])

    def test_extra_props_still_complete(self):
        props = {"Ftu", "Fty", "Fcy", "Fsu", "E", "density", "extra_prop"}
        result = logic.check_property_completeness("metallic", props)
        self.assertTrue(result["complete"])

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            logic.check_property_completeness("ceramic", {"E"})


class TestMetallicPlausibility(unittest.TestCase):

    def test_valid_metallic_no_findings(self):
        props = {"Ftu": 500.0, "Fty": 350.0, "Fcy": 340.0, "Fsu": 300.0, "E": 70000.0}
        self.assertEqual(logic.validate_allowable_values_metallic(props), [])

    def test_fty_exceeds_ftu_flagged(self):
        props = {"Ftu": 300.0, "Fty": 400.0}
        findings = logic.validate_allowable_values_metallic(props)
        self.assertTrue(any("Fty" in f and "Ftu" in f for f in findings))

    def test_negative_ftu_flagged(self):
        props = {"Ftu": -100.0}
        findings = logic.validate_allowable_values_metallic(props)
        self.assertTrue(any("Ftu" in f for f in findings))

    def test_fsu_exceeds_ftu_flagged(self):
        props = {"Ftu": 200.0, "Fsu": 250.0}
        findings = logic.validate_allowable_values_metallic(props)
        self.assertTrue(any("Fsu" in f for f in findings))

    def test_zero_e_flagged(self):
        props = {"E": 0.0}
        findings = logic.validate_allowable_values_metallic(props)
        self.assertTrue(any("E" in f for f in findings))

    def test_empty_props_no_findings(self):
        self.assertEqual(logic.validate_allowable_values_metallic({}), [])


class TestCompositePlausibility(unittest.TestCase):

    def test_valid_composite_no_findings(self):
        props = {
            "F1tu": 1200.0, "F1cu": 900.0, "F2tu": 50.0, "F2cu": 150.0,
            "F12su": 80.0, "E11": 140000.0, "E22": 10000.0, "G12": 5000.0,
            "nu12": 0.3,
        }
        self.assertEqual(logic.validate_allowable_values_composite(props), [])

    def test_negative_f1tu_flagged(self):
        props = {"F1tu": -500.0}
        findings = logic.validate_allowable_values_composite(props)
        self.assertTrue(any("F1tu" in f for f in findings))

    def test_nu12_out_of_range_flagged(self):
        props = {"nu12": 1.5}
        findings = logic.validate_allowable_values_composite(props)
        self.assertTrue(any("nu12" in f for f in findings))

    def test_nu12_exactly_one_flagged(self):
        props = {"nu12": 1.0}
        findings = logic.validate_allowable_values_composite(props)
        self.assertTrue(any("nu12" in f for f in findings))

    def test_nu12_negative_valid(self):
        props = {"nu12": -0.1}
        findings = logic.validate_allowable_values_composite(props)
        self.assertEqual(findings, [])


class TestTemperatureRange(unittest.TestCase):

    def test_valid_range_kelvin(self):
        result = logic.check_temperature_range(200.0, 400.0, "K")
        self.assertTrue(result["valid"])

    def test_valid_range_celsius(self):
        result = logic.check_temperature_range(-55.0, 125.0, "degC")
        self.assertTrue(result["valid"])

    def test_min_equals_max_flagged(self):
        result = logic.check_temperature_range(300.0, 300.0, "K")
        self.assertFalse(result["valid"])

    def test_min_greater_than_max_flagged(self):
        result = logic.check_temperature_range(400.0, 200.0, "K")
        self.assertFalse(result["valid"])

    def test_below_absolute_zero_kelvin(self):
        result = logic.check_temperature_range(-1.0, 300.0, "K")
        self.assertFalse(result["valid"])

    def test_below_absolute_zero_celsius(self):
        result = logic.check_temperature_range(-280.0, 0.0, "degC")
        self.assertFalse(result["valid"])

    def test_unrecognised_unit_flagged(self):
        result = logic.check_temperature_range(0.0, 100.0, "Rankine")
        self.assertFalse(result["valid"])
        self.assertTrue(any("Rankine" in issue for issue in result["issues"]))


class TestSourceTraceability(unittest.TestCase):

    def test_mmpds_approved(self):
        self.assertTrue(logic.check_source_traceability("MMPDS"))

    def test_cmh17_approved(self):
        self.assertTrue(logic.check_source_traceability("CMH-17"))

    def test_test_data_approved(self):
        self.assertTrue(logic.check_source_traceability("test_data"))

    def test_unknown_source_rejected(self):
        self.assertFalse(logic.check_source_traceability("wikipedia"))

    def test_empty_source_rejected(self):
        self.assertFalse(logic.check_source_traceability(""))


class TestEnvironmentalKnockdown(unittest.TestCase):

    def test_full_knockdown(self):
        self.assertAlmostEqual(logic.apply_environmental_knockdown(500.0, 1.0), 500.0)

    def test_partial_knockdown(self):
        self.assertAlmostEqual(logic.apply_environmental_knockdown(500.0, 0.85), 425.0)

    def test_zero_kdf_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_environmental_knockdown(500.0, 0.0)

    def test_negative_kdf_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_environmental_knockdown(500.0, -0.1)

    def test_kdf_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_environmental_knockdown(500.0, 1.01)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_environmental_knockdown(-100.0, 0.9)

    def test_zero_allowable_allowed(self):
        self.assertAlmostEqual(logic.apply_environmental_knockdown(0.0, 0.9), 0.0)


class TestAssessDrdSections(unittest.TestCase):

    def test_all_sections_present(self):
        full = {
            "scope", "applicable_documents", "material_identification",
            "allowable_basis", "property_tables", "source_traceability",
            "environmental_conditions", "statistical_derivation",
            "limitations_and_applicability",
        }
        result = logic.assess_drd_sections(full)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_missing_statistical_derivation(self):
        partial = {
            "scope", "applicable_documents", "material_identification",
            "allowable_basis", "property_tables", "source_traceability",
            "environmental_conditions", "limitations_and_applicability",
        }
        result = logic.assess_drd_sections(partial)
        self.assertFalse(result["complete"])
        self.assertIn("statistical_derivation", result["missing"])

    def test_empty_sections_all_missing(self):
        result = logic.assess_drd_sections(set())
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["missing"]), len(result["mandatory"]))

    def test_extra_sections_accepted(self):
        full = {
            "scope", "applicable_documents", "material_identification",
            "allowable_basis", "property_tables", "source_traceability",
            "environmental_conditions", "statistical_derivation",
            "limitations_and_applicability", "appendix_a",
        }
        result = logic.assess_drd_sections(full)
        self.assertTrue(result["complete"])


class TestSummarizeMaterialRecord(unittest.TestCase):

    def _valid_metallic(self):
        return {
            "id": "AL2024-T3",
            "family": "metallic",
            "basis": "B",
            "properties": {
                "Ftu": 483.0, "Fty": 345.0, "Fcy": 310.0,
                "Fsu": 290.0, "E": 73100.0, "density": 2.78,
            },
            "source": "MMPDS",
            "temp_min": -55.0,
            "temp_max": 125.0,
            "temp_unit": "degC",
        }

    def test_valid_metallic_record_passes(self):
        result = logic.summarize_material_record(self._valid_metallic())
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_invalid_basis_flagged(self):
        rec = self._valid_metallic()
        rec["basis"] = "Z"
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("basis" in f.lower() for f in result["findings"]))

    def test_missing_property_flagged(self):
        rec = self._valid_metallic()
        del rec["properties"]["Ftu"]
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Ftu" in f for f in result["findings"]))

    def test_unapproved_source_flagged(self):
        rec = self._valid_metallic()
        rec["source"] = "internet_forum"
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("internet_forum" in f for f in result["findings"]))

    def test_bad_temperature_range_flagged(self):
        rec = self._valid_metallic()
        rec["temp_min"] = 200.0
        rec["temp_max"] = 100.0
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])

    def test_unknown_family_flagged(self):
        rec = self._valid_metallic()
        rec["family"] = "ceramic"
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("ceramic" in f for f in result["findings"]))

    def test_plausibility_fty_exceeds_ftu_flagged(self):
        rec = self._valid_metallic()
        rec["properties"]["Fty"] = 600.0  # exceeds Ftu=483
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Fty" in f and "Ftu" in f for f in result["findings"]))

    def _valid_composite(self):
        return {
            "id": "CFRP-T300-5208",
            "family": "composite",
            "basis": "B",
            "properties": {
                "F1tu": 1500.0, "F1cu": 1200.0, "F2tu": 50.0, "F2cu": 200.0,
                "F12su": 90.0, "E11": 145000.0, "E22": 10500.0, "G12": 5800.0,
                "nu12": 0.27,
            },
            "source": "CMH-17",
            "temp_min": -55.0,
            "temp_max": 150.0,
            "temp_unit": "degC",
        }

    def test_valid_composite_record_passes(self):
        result = logic.summarize_material_record(self._valid_composite())
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_composite_invalid_nu12_flagged(self):
        rec = self._valid_composite()
        rec["properties"]["nu12"] = 2.0
        result = logic.summarize_material_record(rec)
        self.assertFalse(result["valid"])
        self.assertTrue(any("nu12" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
