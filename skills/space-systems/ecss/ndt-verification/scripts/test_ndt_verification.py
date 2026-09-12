import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ndt_verification_logic import (
    get_applicable_methods,
    check_coverage,
    evaluate_indication,
    assess_component,
    COVERAGE_MINIMUMS,
    VALID_MATERIAL_FAMILIES,
    VALID_DEFECT_FAMILIES,
    VALID_CRITICALITY_LEVELS,
)


class TestGetApplicableMethods(unittest.TestCase):

    def test_metallic_surface_includes_pt_and_mt(self):
        methods = get_applicable_methods("metallic", "surface")
        self.assertIn("PT", methods)
        self.assertIn("MT", methods)

    def test_metallic_surface_excludes_ut(self):
        methods = get_applicable_methods("metallic", "surface")
        self.assertNotIn("UT", methods)

    def test_composite_delamination_returns_rt_and_ut(self):
        methods = get_applicable_methods("composite", "delamination")
        self.assertIn("UT", methods)
        self.assertIn("RT", methods)

    def test_composite_surface_excludes_mt(self):
        # MT requires ferromagnetic material
        methods = get_applicable_methods("composite", "surface")
        self.assertNotIn("MT", methods)

    def test_weld_subsurface_returns_rt_and_ut(self):
        methods = get_applicable_methods("weld", "subsurface")
        self.assertIn("RT", methods)
        self.assertIn("UT", methods)

    def test_bond_subsurface_returns_ut_only(self):
        methods = get_applicable_methods("bond", "subsurface")
        self.assertEqual(methods, ["UT"])

    def test_invalid_material_family_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_applicable_methods("ceramic", "surface")

    def test_invalid_defect_family_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_applicable_methods("metallic", "corrosion")

    def test_return_value_is_list(self):
        result = get_applicable_methods("weld", "surface")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestCheckCoverage(unittest.TestCase):

    def test_primary_full_coverage_passes(self):
        result = check_coverage("primary", 1.0)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["shortfall"], 0.0)
        self.assertEqual(result["required"], 1.0)

    def test_primary_partial_coverage_fails(self):
        result = check_coverage("primary", 0.9)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["shortfall"], 0.1, places=6)

    def test_secondary_sufficient_coverage_passes(self):
        result = check_coverage("secondary", 0.6)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["shortfall"], 0.0)

    def test_secondary_exact_minimum_passes(self):
        result = check_coverage("secondary", 0.5)
        self.assertTrue(result["adequate"])

    def test_secondary_insufficient_coverage_fails(self):
        result = check_coverage("secondary", 0.4)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["shortfall"], 0.1, places=6)

    def test_tertiary_minimum_coverage_passes(self):
        result = check_coverage("tertiary", 0.2)
        self.assertTrue(result["adequate"])

    def test_tertiary_zero_coverage_fails(self):
        result = check_coverage("tertiary", 0.0)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["shortfall"], 0.2, places=6)

    def test_invalid_criticality_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_coverage("critical", 1.0)

    def test_fraction_above_one_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_coverage("primary", 1.5)

    def test_negative_fraction_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_coverage("secondary", -0.1)

    def test_result_contains_actual_field(self):
        result = check_coverage("tertiary", 0.25)
        self.assertEqual(result["actual"], 0.25)


class TestEvaluateIndication(unittest.TestCase):

    def test_below_limit_is_acceptable_and_passes(self):
        result = evaluate_indication(2.0, 5.0)
        self.assertEqual(result["severity"], "acceptable")
        self.assertTrue(result["passes"])

    def test_at_limit_is_marginal_and_does_not_pass(self):
        result = evaluate_indication(5.0, 5.0)
        self.assertEqual(result["severity"], "marginal")
        self.assertFalse(result["passes"])

    def test_above_limit_is_rejectable_and_does_not_pass(self):
        result = evaluate_indication(7.0, 5.0)
        self.assertEqual(result["severity"], "rejectable")
        self.assertFalse(result["passes"])

    def test_zero_indication_is_acceptable(self):
        result = evaluate_indication(0.0, 5.0)
        self.assertEqual(result["severity"], "acceptable")
        self.assertTrue(result["passes"])

    def test_negative_indication_size_raises_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_indication(-1.0, 5.0)

    def test_zero_acceptance_limit_raises_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_indication(2.0, 0.0)

    def test_negative_acceptance_limit_raises_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_indication(2.0, -3.0)


class TestAssessComponent(unittest.TestCase):

    def _make_component(self, **overrides):
        base = {
            "element_id": "STRUT-01",
            "material_family": "metallic",
            "defect_families": ["surface"],
            "criticality": "primary",
            "inspected_fraction": 1.0,
            "ndt_method": "PT",
            "indications": [],
        }
        base.update(overrides)
        return base

    def test_clean_component_passes(self):
        result = assess_component(self._make_component())
        self.assertTrue(result["passes"])
        self.assertEqual(result["findings"], [])

    def test_coverage_shortfall_fails_component(self):
        result = assess_component(self._make_component(inspected_fraction=0.8))
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("Coverage" in f for f in result["findings"])
        )

    def test_rejectable_indication_fails_component(self):
        result = assess_component(self._make_component(
            indications=[{"indication_size": 10.0, "acceptance_limit": 5.0}]
        ))
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("rejectable" in f for f in result["findings"])
        )

    def test_marginal_indication_fails_component(self):
        result = assess_component(self._make_component(
            indications=[{"indication_size": 5.0, "acceptance_limit": 5.0}]
        ))
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("marginal" in f for f in result["findings"])
        )

    def test_acceptable_indication_does_not_add_finding(self):
        result = assess_component(self._make_component(
            indications=[{"indication_size": 2.0, "acceptance_limit": 5.0}]
        ))
        self.assertTrue(result["passes"])

    def test_inapplicable_method_flagged(self):
        # UT is not applicable for metallic/surface
        result = assess_component(self._make_component(ndt_method="UT"))
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("not applicable" in f for f in result["findings"])
        )

    def test_applicable_methods_populated(self):
        result = assess_component(self._make_component())
        self.assertIn("PT", result["applicable_methods"])

    def test_composite_delamination_ut_passes(self):
        component = self._make_component(
            element_id="PANEL-02",
            material_family="composite",
            defect_families=["delamination"],
            criticality="secondary",
            inspected_fraction=0.6,
            ndt_method="UT",
        )
        result = assess_component(component)
        self.assertTrue(result["passes"])

    def test_multiple_indications_mixed_results(self):
        result = assess_component(self._make_component(
            indications=[
                {"indication_size": 2.0, "acceptance_limit": 5.0},
                {"indication_size": 6.0, "acceptance_limit": 5.0},
            ]
        ))
        self.assertFalse(result["passes"])
        self.assertEqual(len(result["indications_summary"]), 2)

    def test_element_id_preserved_in_result(self):
        result = assess_component(self._make_component(element_id="FRAME-99"))
        self.assertEqual(result["element_id"], "FRAME-99")


if __name__ == "__main__":
    unittest.main()
