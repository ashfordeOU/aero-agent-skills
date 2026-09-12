"""
Gate 3 contract tests — static-analysis-verification leaf.
stdlib unittest only. Deterministic, offline. Run:
  python3 test_static_analysis_verification.py
Must print OK.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from static_analysis_verification_logic import (
    AnalysisMethod,
    LoadType,
    StabilityResult,
    StressResult,
    VerificationStatus,
    categorize_load,
    compute_margin_of_safety,
    run_analysis_verification,
    verify_stability,
    verify_stress,
)


class TestComputeMarginOfSafety(unittest.TestCase):
    def test_exact_match_gives_zero_mos(self):
        self.assertAlmostEqual(compute_margin_of_safety(100.0, 100.0), 0.0)

    def test_positive_mos_when_allowable_exceeds_applied(self):
        self.assertAlmostEqual(compute_margin_of_safety(200.0, 100.0), 1.0)

    def test_negative_mos_when_applied_exceeds_allowable(self):
        mos = compute_margin_of_safety(50.0, 100.0)
        self.assertAlmostEqual(mos, -0.5)
        self.assertLess(mos, 0.0)

    def test_compressive_stress_uses_absolute_value(self):
        # applied is negative (compression); allowable is tensile/compressive magnitude
        self.assertAlmostEqual(compute_margin_of_safety(100.0, -100.0), 0.0)

    def test_small_applied_stress_gives_large_positive_mos(self):
        self.assertAlmostEqual(compute_margin_of_safety(100.0, 10.0), 9.0)

    def test_zero_applied_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, 0.0)

    def test_zero_allowable_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 100.0)

    def test_negative_allowable_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(-50.0, 100.0)


class TestCategorizeLoad(unittest.TestCase):
    def test_dyl_returns_correct_factor_and_label(self):
        result = categorize_load(LoadType.DYL, 1.25, 1.5)
        self.assertEqual(result["label"], "DYL")
        self.assertAlmostEqual(result["factor"], 1.25)

    def test_dul_returns_correct_factor_and_label(self):
        result = categorize_load(LoadType.DUL, 1.25, 1.5)
        self.assertEqual(result["label"], "DUL")
        self.assertAlmostEqual(result["factor"], 1.5)

    def test_min_mos_is_zero_for_both_load_types(self):
        for lt in (LoadType.DYL, LoadType.DUL):
            self.assertEqual(categorize_load(lt, 1.25, 1.5)["min_mos"], 0.0)

    def test_unknown_load_type_raises_value_error(self):
        with self.assertRaises((ValueError, AttributeError)):
            categorize_load("UNKNOWN", 1.25, 1.5)  # type: ignore[arg-type]


class TestVerifyStress(unittest.TestCase):
    def _stress(self, applied, allowable, load_type=LoadType.DUL,
                method=AnalysisMethod.CALCULIX_LINEAR, elem="E1"):
        return StressResult(
            element_id=elem,
            applied_stress=applied,
            allowable_stress=allowable,
            load_type=load_type,
            analysis_method=method,
        )

    def test_passes_when_allowable_exceeds_applied(self):
        r = verify_stress(self._stress(80.0, 100.0))
        self.assertEqual(r.status, VerificationStatus.PASS)
        self.assertGreaterEqual(r.margin_of_safety, 0.0)

    def test_fails_when_applied_exceeds_allowable(self):
        r = verify_stress(self._stress(120.0, 100.0))
        self.assertEqual(r.status, VerificationStatus.FAIL)
        self.assertLess(r.margin_of_safety, 0.0)

    def test_exactly_at_allowable_is_pass(self):
        r = verify_stress(self._stress(100.0, 100.0))
        self.assertEqual(r.status, VerificationStatus.PASS)
        self.assertAlmostEqual(r.margin_of_safety, 0.0)

    def test_invalid_allowable_returns_error(self):
        r = verify_stress(self._stress(80.0, -10.0))
        self.assertEqual(r.status, VerificationStatus.ERROR)

    def test_zero_allowable_returns_error(self):
        r = verify_stress(self._stress(80.0, 0.0))
        self.assertEqual(r.status, VerificationStatus.ERROR)

    def test_dyl_load_type_preserved_in_result(self):
        r = verify_stress(self._stress(50.0, 100.0, LoadType.DYL))
        self.assertEqual(r.load_type, LoadType.DYL)

    def test_element_id_preserved_in_result(self):
        r = verify_stress(self._stress(50.0, 100.0, elem="BRACKET-7"))
        self.assertEqual(r.element_id, "BRACKET-7")

    def test_compressive_applied_stress_handled(self):
        # Compressive applied (-80 MPa), allowable 100 MPa → should pass
        r = verify_stress(self._stress(-80.0, 100.0))
        self.assertEqual(r.status, VerificationStatus.PASS)
        self.assertAlmostEqual(r.margin_of_safety, 0.25)

    def test_hand_beam_method_recorded(self):
        r = verify_stress(self._stress(60.0, 100.0, method=AnalysisMethod.HAND_BEAM))
        self.assertIn("hand-beam", r.finding)


class TestVerifyStability(unittest.TestCase):
    def _stab(self, critical, applied, load_type=LoadType.DUL,
              method=AnalysisMethod.HAND_TRUSS, elem="COL1"):
        return StabilityResult(
            element_id=elem,
            critical_load=critical,
            applied_load=applied,
            load_type=load_type,
            analysis_method=method,
        )

    def test_passes_when_critical_exceeds_applied(self):
        r = verify_stability(self._stab(1500.0, 1000.0))
        self.assertEqual(r.status, VerificationStatus.PASS)
        self.assertAlmostEqual(r.margin_of_safety, 0.5)

    def test_fails_when_applied_exceeds_critical(self):
        r = verify_stability(self._stab(800.0, 1000.0))
        self.assertEqual(r.status, VerificationStatus.FAIL)
        self.assertAlmostEqual(r.margin_of_safety, -0.2)

    def test_exactly_at_critical_load_is_pass(self):
        r = verify_stability(self._stab(1000.0, 1000.0))
        self.assertEqual(r.status, VerificationStatus.PASS)
        self.assertAlmostEqual(r.margin_of_safety, 0.0)

    def test_zero_critical_load_returns_error(self):
        r = verify_stability(self._stab(0.0, 1000.0))
        self.assertEqual(r.status, VerificationStatus.ERROR)

    def test_negative_critical_load_returns_error(self):
        r = verify_stability(self._stab(-500.0, 1000.0))
        self.assertEqual(r.status, VerificationStatus.ERROR)

    def test_zero_applied_load_returns_error(self):
        r = verify_stability(self._stab(1000.0, 0.0))
        self.assertEqual(r.status, VerificationStatus.ERROR)

    def test_element_id_preserved_in_stability_result(self):
        r = verify_stability(self._stab(2000.0, 1000.0, elem="PANEL-3"))
        self.assertEqual(r.element_id, "PANEL-3")

    def test_calculix_nonlinear_method_recorded(self):
        r = verify_stability(
            self._stab(1500.0, 1000.0, method=AnalysisMethod.CALCULIX_NONLINEAR)
        )
        self.assertIn("calculix-nonlinear", r.finding)


class TestRunAnalysisVerification(unittest.TestCase):
    def _stress(self, elem, applied, allowable):
        return StressResult(
            element_id=elem,
            applied_stress=applied,
            allowable_stress=allowable,
            load_type=LoadType.DUL,
            analysis_method=AnalysisMethod.CALCULIX_LINEAR,
        )

    def _stab(self, elem, critical, applied):
        return StabilityResult(
            element_id=elem,
            critical_load=critical,
            applied_load=applied,
            load_type=LoadType.DUL,
            analysis_method=AnalysisMethod.HAND_BEAM,
        )

    def test_all_pass_gives_overall_pass(self):
        summary = run_analysis_verification(
            [self._stress("E1", 80.0, 100.0)],
            [self._stab("C1", 2000.0, 1000.0)],
        )
        self.assertEqual(summary["overall_status"], VerificationStatus.PASS)
        self.assertEqual(summary["failure_count"], 0)

    def test_one_stress_failure_gives_overall_fail(self):
        summary = run_analysis_verification(
            [self._stress("E1", 80.0, 100.0), self._stress("E2", 150.0, 100.0)],
            [],
        )
        self.assertEqual(summary["overall_status"], VerificationStatus.FAIL)
        self.assertEqual(summary["failure_count"], 1)

    def test_stability_failure_gives_overall_fail(self):
        summary = run_analysis_verification(
            [],
            [self._stab("C1", 500.0, 1000.0)],
        )
        self.assertEqual(summary["overall_status"], VerificationStatus.FAIL)

    def test_error_in_stress_gives_overall_error(self):
        summary = run_analysis_verification(
            [self._stress("E1", 80.0, 0.0)],
            [],
        )
        self.assertEqual(summary["overall_status"], VerificationStatus.ERROR)

    def test_empty_inputs_give_overall_pass(self):
        summary = run_analysis_verification([], [])
        self.assertEqual(summary["overall_status"], VerificationStatus.PASS)
        self.assertEqual(summary["total_checks"], 0)

    def test_total_checks_counts_all_records(self):
        summary = run_analysis_verification(
            [self._stress("E1", 80.0, 100.0), self._stress("E2", 50.0, 100.0)],
            [self._stab("C1", 2000.0, 1000.0)],
        )
        self.assertEqual(summary["total_checks"], 3)

    def test_multiple_failures_counted_correctly(self):
        summary = run_analysis_verification(
            [self._stress("E1", 150.0, 100.0), self._stress("E2", 200.0, 100.0)],
            [self._stab("C1", 500.0, 1000.0)],
        )
        self.assertEqual(summary["failure_count"], 3)

    def test_margins_list_length_matches_total_checks(self):
        summary = run_analysis_verification(
            [self._stress("E1", 80.0, 100.0)],
            [self._stab("C1", 2000.0, 1000.0)],
        )
        self.assertEqual(len(summary["margins"]), summary["total_checks"])


if __name__ == "__main__":
    unittest.main()
