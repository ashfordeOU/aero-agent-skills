#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.3.7 static structural
test assessment.

Exercises scripts/static_test_logic.py (stdlib unittest, offline).
Contract: categorize_load_case accepts recognized load-case types and
rejects unrecognized types; compute_test_load applies the correct load
factor for each factor_type and rejects invalid inputs; margin_of_safety
returns (allowable/applied)-1 and raises on non-positive applied load;
generate_load_steps produces evenly-spaced steps up to the target and
rejects too-few steps; check_residual_deformation returns True within
allowable and False above it; check_stiffness_correlation returns
(within_tolerance, deviation_pct) and raises on invalid inputs;
evaluate_load_case aggregates margin, deformation, and stiffness
violations per load case; assess_static_test drives the full assessment
and returns compliant=True only when all load cases pass.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import static_test_logic as st  # noqa: E402


class CategorizeLoadCaseTest(unittest.TestCase):
    def test_tension_accepted(self):
        self.assertEqual(st.categorize_load_case("tension"), "tension")

    def test_compression_accepted(self):
        self.assertEqual(st.categorize_load_case("compression"), "compression")

    def test_shear_accepted(self):
        self.assertEqual(st.categorize_load_case("shear"), "shear")

    def test_bending_accepted(self):
        self.assertEqual(st.categorize_load_case("bending"), "bending")

    def test_torsion_accepted(self):
        self.assertEqual(st.categorize_load_case("torsion"), "torsion")

    def test_combined_accepted(self):
        self.assertEqual(st.categorize_load_case("combined"), "combined")

    def test_pressure_accepted(self):
        self.assertEqual(st.categorize_load_case("pressure"), "pressure")

    def test_thermal_mechanical_accepted(self):
        self.assertEqual(
            st.categorize_load_case("thermal_mechanical"), "thermal_mechanical"
        )

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            st.categorize_load_case("impact")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            st.categorize_load_case("")


class ComputeTestLoadTest(unittest.TestCase):
    def test_qualification_ultimate_factor(self):
        result = st.compute_test_load(10000.0, "qualification_ultimate")
        self.assertAlmostEqual(result, 15000.0)

    def test_qualification_yield_factor(self):
        result = st.compute_test_load(10000.0, "qualification_yield")
        self.assertAlmostEqual(result, 11000.0)

    def test_acceptance_proof_factor(self):
        result = st.compute_test_load(10000.0, "acceptance_proof")
        self.assertAlmostEqual(result, 11000.0)

    def test_unrecognized_factor_type_raises(self):
        with self.assertRaises(ValueError):
            st.compute_test_load(10000.0, "safety_factor_x")

    def test_zero_dll_raises(self):
        with self.assertRaises(ValueError):
            st.compute_test_load(0.0, "qualification_ultimate")

    def test_negative_dll_raises(self):
        with self.assertRaises(ValueError):
            st.compute_test_load(-500.0, "acceptance_proof")


class MarginOfSafetyTest(unittest.TestCase):
    def test_positive_margin(self):
        ms = st.margin_of_safety(200.0, 100.0)
        self.assertAlmostEqual(ms, 1.0)

    def test_zero_margin(self):
        ms = st.margin_of_safety(100.0, 100.0)
        self.assertAlmostEqual(ms, 0.0)

    def test_negative_margin(self):
        ms = st.margin_of_safety(80.0, 100.0)
        self.assertAlmostEqual(ms, -0.2)

    def test_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            st.margin_of_safety(100.0, 0.0)

    def test_negative_applied_raises(self):
        with self.assertRaises(ValueError):
            st.margin_of_safety(100.0, -50.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            st.margin_of_safety(-10.0, 100.0)


class GenerateLoadStepsTest(unittest.TestCase):
    def test_three_steps_values(self):
        steps = st.generate_load_steps(300.0, 3)
        self.assertEqual(len(steps), 3)
        self.assertAlmostEqual(steps[0], 100.0)
        self.assertAlmostEqual(steps[1], 200.0)
        self.assertAlmostEqual(steps[2], 300.0)

    def test_five_steps_last_equals_target(self):
        steps = st.generate_load_steps(1000.0, 5)
        self.assertEqual(len(steps), 5)
        self.assertAlmostEqual(steps[-1], 1000.0)

    def test_fewer_than_min_steps_raises(self):
        with self.assertRaises(ValueError):
            st.generate_load_steps(500.0, 2)

    def test_zero_target_raises(self):
        with self.assertRaises(ValueError):
            st.generate_load_steps(0.0, 3)

    def test_negative_target_raises(self):
        with self.assertRaises(ValueError):
            st.generate_load_steps(-100.0, 3)

    def test_steps_are_evenly_spaced(self):
        steps = st.generate_load_steps(120.0, 4)
        self.assertAlmostEqual(steps[1] - steps[0], steps[2] - steps[1])


class CheckResidualDeformationTest(unittest.TestCase):
    def test_within_allowable_returns_true(self):
        self.assertTrue(st.check_residual_deformation(0.5, 1.0))

    def test_exactly_at_allowable_returns_true(self):
        self.assertTrue(st.check_residual_deformation(1.0, 1.0))

    def test_exceeds_allowable_returns_false(self):
        self.assertFalse(st.check_residual_deformation(1.5, 1.0))

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            st.check_residual_deformation(-0.1, 1.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            st.check_residual_deformation(0.5, -1.0)


class CheckStiffnessCorrelationTest(unittest.TestCase):
    def test_within_tolerance_returns_true(self):
        within, deviation = st.check_stiffness_correlation(5000.0, 5000.0)
        self.assertTrue(within)
        self.assertAlmostEqual(deviation, 0.0)

    def test_deviation_above_tolerance_returns_false(self):
        within, deviation = st.check_stiffness_correlation(5600.0, 5000.0)
        self.assertFalse(within)
        self.assertAlmostEqual(deviation, 12.0)

    def test_deviation_exactly_at_tolerance_returns_true(self):
        within, deviation = st.check_stiffness_correlation(5500.0, 5000.0)
        self.assertTrue(within)
        self.assertAlmostEqual(deviation, 10.0)

    def test_negative_deviation_outside_band(self):
        within, deviation = st.check_stiffness_correlation(4400.0, 5000.0)
        self.assertFalse(within)
        self.assertAlmostEqual(deviation, -12.0)

    def test_zero_measured_raises(self):
        with self.assertRaises(ValueError):
            st.check_stiffness_correlation(0.0, 5000.0)

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            st.check_stiffness_correlation(5000.0, 0.0)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            st.check_stiffness_correlation(5000.0, 5000.0, tolerance_pct=-1.0)

    def test_custom_tight_tolerance(self):
        within, _ = st.check_stiffness_correlation(5030.0, 5000.0, tolerance_pct=0.5)
        self.assertFalse(within)


class EvaluateLoadCaseTest(unittest.TestCase):
    def test_compliant_ms_only(self):
        violations = st.evaluate_load_case(
            "LC-001", allowable_n=20000.0, applied_n=15000.0
        )
        self.assertEqual(violations, [])

    def test_negative_ms_flagged(self):
        violations = st.evaluate_load_case(
            "LC-002", allowable_n=10000.0, applied_n=15000.0
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "negative_margin_of_safety")
        self.assertEqual(violations[0]["load_case_id"], "LC-002")

    def test_residual_deformation_violation_flagged(self):
        violations = st.evaluate_load_case(
            "LC-003",
            allowable_n=20000.0,
            applied_n=15000.0,
            residual_mm=2.0,
            allowable_residual_mm=1.0,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "residual_deformation_exceeded")

    def test_stiffness_out_of_band_flagged(self):
        violations = st.evaluate_load_case(
            "LC-004",
            allowable_n=20000.0,
            applied_n=15000.0,
            measured_stiffness_n_per_mm=5600.0,
            predicted_stiffness_n_per_mm=5000.0,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "stiffness_correlation_out_of_band")

    def test_multiple_violations_aggregated(self):
        violations = st.evaluate_load_case(
            "LC-005",
            allowable_n=10000.0,
            applied_n=15000.0,
            residual_mm=3.0,
            allowable_residual_mm=1.0,
        )
        self.assertEqual(len(violations), 2)

    def test_partial_stiffness_data_skipped(self):
        violations = st.evaluate_load_case(
            "LC-006",
            allowable_n=20000.0,
            applied_n=15000.0,
            measured_stiffness_n_per_mm=6000.0,
            predicted_stiffness_n_per_mm=None,
        )
        self.assertEqual(violations, [])


class AssessStaticTestTest(unittest.TestCase):
    def _make_test_data(self, test_type, load_cases):
        return {
            "test_type": test_type,
            "design_limit_load_n": 10000.0,
            "load_cases": load_cases,
        }

    def test_qualification_all_pass(self):
        result = st.assess_static_test(self._make_test_data(
            "qualification",
            [{"load_case_id": "LC-001", "load_case_type": "compression",
              "allowable_n": 20000.0, "applied_n": 15000.0}],
        ))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertAlmostEqual(result["target_test_load_n"], 15000.0)

    def test_acceptance_all_pass(self):
        result = st.assess_static_test(self._make_test_data(
            "acceptance",
            [{"load_case_id": "LC-001", "load_case_type": "bending",
              "allowable_n": 15000.0, "applied_n": 11000.0}],
        ))
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["target_test_load_n"], 11000.0)

    def test_violation_makes_non_compliant(self):
        result = st.assess_static_test(self._make_test_data(
            "qualification",
            [{"load_case_id": "LC-001", "load_case_type": "tension",
              "allowable_n": 10000.0, "applied_n": 15000.0}],
        ))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["violations"]), 1)

    def test_unrecognized_test_type_raises(self):
        with self.assertRaises(ValueError):
            st.assess_static_test(self._make_test_data("protoflight", []))

    def test_unrecognized_load_case_type_raises(self):
        with self.assertRaises(ValueError):
            st.assess_static_test(self._make_test_data(
                "qualification",
                [{"load_case_id": "LC-X", "load_case_type": "impact_shock",
                  "allowable_n": 20000.0, "applied_n": 15000.0}],
            ))

    def test_factor_type_recorded_in_result(self):
        result = st.assess_static_test(self._make_test_data("qualification", []))
        self.assertEqual(result["factor_type"], "qualification_ultimate")

    def test_multiple_load_cases_all_pass(self):
        result = st.assess_static_test(self._make_test_data(
            "qualification",
            [
                {"load_case_id": "LC-001", "load_case_type": "compression",
                 "allowable_n": 20000.0, "applied_n": 15000.0},
                {"load_case_id": "LC-002", "load_case_type": "shear",
                 "allowable_n": 8000.0, "applied_n": 5000.0},
                {"load_case_id": "LC-003", "load_case_type": "bending",
                 "allowable_n": 12000.0, "applied_n": 11000.0},
            ],
        ))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])

    def test_multiple_load_cases_one_fails(self):
        result = st.assess_static_test(self._make_test_data(
            "acceptance",
            [
                {"load_case_id": "LC-001", "load_case_type": "tension",
                 "allowable_n": 15000.0, "applied_n": 11000.0},
                {"load_case_id": "LC-002", "load_case_type": "torsion",
                 "allowable_n": 8000.0, "applied_n": 11000.0},
            ],
        ))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(result["violations"][0]["load_case_id"], "LC-002")

    def test_empty_load_cases_compliant(self):
        result = st.assess_static_test(self._make_test_data("acceptance", []))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
