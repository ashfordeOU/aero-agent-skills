"""Contract tests for the mechanical test report content audit."""

import math
import unittest

from q7045_test_report_content_logic import (
    BASE_SECTIONS,
    REPRODUCTION_REL_TOL,
    assess_test_report,
    completeness_ratio,
    derive_tensile_properties,
    known_methods,
    missing_sections,
    normalise_sections,
    original_area_mm2,
    reproduction_findings,
    required_sections,
    specimen_audit,
)

RAW = {
    "original_diameter_mm": 10.0,
    "original_gauge_length_mm": 50.0,
    "yield_force_kn": 30.0,
    "max_force_kn": 40.0,
    "final_gauge_length_mm": 57.5,
    "final_diameter_mm": 7.0,
}


def _full_sections(method):
    return list(required_sections(method))


class RequiredSectionTests(unittest.TestCase):
    def test_base_sections_are_always_required(self):
        for name in BASE_SECTIONS:
            self.assertIn(name, required_sections("hardness"))

    def test_fatigue_adds_its_own_sections(self):
        sections = required_sections("fatigue")
        self.assertIn("run-out-criterion", sections)
        self.assertIn("loading-spectrum", sections)

    def test_fracture_adds_the_precrack_record(self):
        self.assertIn("precrack-record", required_sections("fracture"))

    def test_shear_adds_nothing_beyond_the_base_set(self):
        self.assertEqual(required_sections("shear"), tuple(BASE_SECTIONS))

    def test_method_token_is_case_insensitive(self):
        self.assertEqual(required_sections("Tensile"), required_sections("tensile"))

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            required_sections("creep")

    def test_blank_method_rejected(self):
        with self.assertRaises(ValueError):
            required_sections("   ")

    def test_non_string_method_rejected(self):
        with self.assertRaises(ValueError):
            required_sections(7)

    def test_known_methods_are_sorted(self):
        methods = known_methods()
        self.assertEqual(methods, sorted(methods))


class SectionComparisonTests(unittest.TestCase):
    def test_complete_report_has_no_gaps(self):
        self.assertEqual(missing_sections(_full_sections("impact"), "impact"), [])

    def test_gaps_come_back_in_required_order(self):
        delivered = [s for s in _full_sections("fatigue")
                     if s not in ("results-table", "loading-spectrum")]
        self.assertEqual(
            missing_sections(delivered, "fatigue"), ["results-table", "loading-spectrum"]
        )

    def test_duplicate_delivered_section_is_collapsed(self):
        delivered = _full_sections("shear") + ["results-table"]
        self.assertEqual(missing_sections(delivered, "shear"), [])

    def test_completeness_ratio_is_one_when_complete(self):
        self.assertAlmostEqual(completeness_ratio(_full_sections("shear"), "shear"), 1.0)

    def test_completeness_ratio_counts_the_gaps(self):
        required = _full_sections("shear")
        ratio = completeness_ratio(required[:-2], "shear")
        self.assertAlmostEqual(ratio, (len(required) - 2) / float(len(required)))

    def test_empty_report_has_zero_completeness(self):
        self.assertAlmostEqual(completeness_ratio([], "tensile"), 0.0)

    def test_non_sequence_sections_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sections("results-table")


class SpecimenAuditTests(unittest.TestCase):
    def test_matched_register_and_results(self):
        audit = specimen_audit(["a1", "a2"], [{"specimen": "a1"}, {"specimen": "a2"}])
        self.assertEqual(audit["orphaned_results"], [])
        self.assertEqual(audit["unreported_specimens"], [])

    def test_orphaned_result_is_named(self):
        audit = specimen_audit(["a1"], [{"specimen": "a1"}, {"specimen": "a9"}])
        self.assertEqual(audit["orphaned_results"], ["a9"])

    def test_unreported_specimen_is_named(self):
        audit = specimen_audit(["a1", "a2"], [{"specimen": "a1"}])
        self.assertEqual(audit["unreported_specimens"], ["a2"])

    def test_duplicate_registration_rejected(self):
        with self.assertRaises(ValueError):
            specimen_audit(["a1", "A1"], [{"specimen": "a1"}])

    def test_result_without_a_specimen_rejected(self):
        with self.assertRaises(ValueError):
            specimen_audit(["a1"], [{"value": 12.0}])

    def test_non_mapping_result_rejected(self):
        with self.assertRaises(ValueError):
            specimen_audit(["a1"], ["a1"])


class TensileDerivationTests(unittest.TestCase):
    def test_original_area_of_a_ten_millimetre_round(self):
        self.assertAlmostEqual(original_area_mm2(10.0), math.pi * 25.0, places=9)

    def test_tensile_strength_from_force_and_area(self):
        derived = derive_tensile_properties(RAW)
        self.assertAlmostEqual(
            derived["tensile_strength_mpa"], 40.0 * 1000.0 / (math.pi * 25.0), places=9
        )

    def test_yield_strength_is_below_tensile_strength(self):
        derived = derive_tensile_properties(RAW)
        self.assertLess(
            derived["yield_strength_mpa"], derived["tensile_strength_mpa"] - 1.0
        )

    def test_elongation_is_the_gauge_length_change(self):
        self.assertAlmostEqual(
            derive_tensile_properties(RAW)["elongation_percent"], 15.0, places=9
        )

    def test_reduction_of_area_uses_the_diameter_ratio(self):
        expected = (1.0 - (7.0 / 10.0) ** 2) * 100.0
        self.assertAlmostEqual(
            derive_tensile_properties(RAW)["reduction_of_area_percent"], expected, places=9
        )

    def test_yield_above_maximum_force_rejected(self):
        raw = dict(RAW, yield_force_kn=50.0)
        with self.assertRaises(ValueError):
            derive_tensile_properties(raw)

    def test_shrinking_gauge_length_rejected(self):
        raw = dict(RAW, final_gauge_length_mm=49.0)
        with self.assertRaises(ValueError):
            derive_tensile_properties(raw)

    def test_growing_diameter_rejected(self):
        raw = dict(RAW, final_diameter_mm=11.0)
        with self.assertRaises(ValueError):
            derive_tensile_properties(raw)

    def test_missing_measurement_rejected(self):
        raw = dict(RAW)
        del raw["max_force_kn"]
        with self.assertRaises(ValueError):
            derive_tensile_properties(raw)

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            derive_tensile_properties(dict(RAW, original_diameter_mm=-10.0))


class ReproductionTests(unittest.TestCase):
    def test_rounded_report_reproduces(self):
        derived = derive_tensile_properties(RAW)
        printed = {"elongation_percent": 15.0}
        self.assertEqual(reproduction_findings(printed, derived), [])

    def test_wrong_printed_value_is_flagged(self):
        derived = derive_tensile_properties(RAW)
        findings = reproduction_findings({"elongation_percent": 22.0}, derived)
        self.assertEqual(len(findings), 1)

    def test_value_at_the_tolerance_edge_reproduces(self):
        derived = {"x": 100.0}
        edge = 100.0 * (1.0 + REPRODUCTION_REL_TOL)
        self.assertEqual(reproduction_findings({"x": edge}, derived), [])

    def test_property_with_no_raw_basis_is_flagged(self):
        findings = reproduction_findings({"modulus_gpa": 210.0}, {"x": 1.0})
        self.assertEqual(len(findings), 1)

    def test_non_numeric_printed_value_rejected(self):
        with self.assertRaises(ValueError):
            reproduction_findings({"x": "100"}, {"x": 100.0})

    def test_non_positive_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            reproduction_findings({"x": 100.0}, {"x": 100.0}, rel_tol=0.0)


class AssessmentTests(unittest.TestCase):
    def _report(self, **overrides):
        report = {
            "method": "tensile",
            "sections": _full_sections("tensile"),
            "specimens": ["t1"],
            "results": [{"specimen": "t1"}],
            "raw_data": RAW,
            "reported_properties": {"elongation_percent": 15.0},
        }
        report.update(overrides)
        return report

    def test_clean_report_is_acceptable(self):
        result = assess_test_report(self._report())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_missing_section_makes_the_report_unacceptable(self):
        sections = [s for s in _full_sections("tensile") if s != "raw-data-retention"]
        result = assess_test_report(self._report(sections=sections))
        self.assertFalse(result["acceptable"])
        self.assertIn("raw-data-retention", result["missing_sections"])

    def test_orphaned_result_is_a_finding(self):
        result = assess_test_report(self._report(results=[{"specimen": "t9"}]))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("t9" in f for f in result["findings"]))

    def test_printed_values_without_raw_data_are_flagged(self):
        report = self._report()
        del report["raw_data"]
        result = assess_test_report(report)
        self.assertFalse(result["acceptable"])

    def test_report_without_the_optional_reproduction_block_still_audits(self):
        report = self._report()
        del report["raw_data"]
        del report["reported_properties"]
        self.assertTrue(assess_test_report(report)["acceptable"])

    def test_derived_properties_are_returned_for_review(self):
        result = assess_test_report(self._report())
        self.assertAlmostEqual(result["derived_properties"]["elongation_percent"], 15.0)

    def test_missing_key_rejected(self):
        report = self._report()
        del report["results"]
        with self.assertRaises(ValueError):
            assess_test_report(report)

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_report(["method"])


if __name__ == "__main__":
    unittest.main()
