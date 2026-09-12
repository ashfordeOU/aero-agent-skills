"""
Stdlib unittest suite for qualification_test_programme_logic.py.
Offline, deterministic. Run: python3 test_qualification_test_programme.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qualification_test_programme_logic import (
    PROOF_FACTOR_METALLIC,
    PROOF_FACTOR_COMPOSITE,
    BURST_FACTOR_METALLIC,
    BURST_FACTOR_COMPOSITE,
    QualificationProgrammeError,
    compute_proof_pressure,
    compute_burst_pressure,
    compute_design_burst_pressure,
    required_tests,
    categorize_test,
    validate_test_result,
    check_sequence,
    build_qualification_report,
)


class TestComputeProofPressure(unittest.TestCase):
    def test_metallic_proof_uses_correct_factor(self):
        self.assertAlmostEqual(
            compute_proof_pressure(100.0, "metallic"),
            100.0 * PROOF_FACTOR_METALLIC,
        )

    def test_composite_proof_uses_correct_factor(self):
        self.assertAlmostEqual(
            compute_proof_pressure(200.0, "composite"),
            200.0 * PROOF_FACTOR_COMPOSITE,
        )

    def test_proof_scales_linearly_with_meop(self):
        self.assertAlmostEqual(
            compute_proof_pressure(50.0, "metallic"),
            compute_proof_pressure(100.0, "metallic") / 2,
        )

    def test_zero_meop_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            compute_proof_pressure(0.0, "metallic")

    def test_negative_meop_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            compute_proof_pressure(-5.0, "composite")

    def test_unknown_material_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            compute_proof_pressure(100.0, "ceramic")

    def test_case_insensitive_material(self):
        self.assertAlmostEqual(
            compute_proof_pressure(100.0, "Metallic"),
            compute_proof_pressure(100.0, "metallic"),
        )


class TestComputeBurstPressure(unittest.TestCase):
    def test_metallic_burst_uses_correct_factor(self):
        self.assertAlmostEqual(
            compute_burst_pressure(100.0, "metallic"),
            100.0 * BURST_FACTOR_METALLIC,
        )

    def test_composite_burst_uses_correct_factor(self):
        self.assertAlmostEqual(
            compute_burst_pressure(100.0, "composite"),
            100.0 * BURST_FACTOR_COMPOSITE,
        )

    def test_composite_burst_exceeds_metallic_burst(self):
        meop = 80.0
        self.assertGreater(
            compute_burst_pressure(meop, "composite"),
            compute_burst_pressure(meop, "metallic"),
        )

    def test_design_burst_equals_burst_metallic(self):
        meop = 120.0
        self.assertAlmostEqual(
            compute_design_burst_pressure(meop, "metallic"),
            compute_burst_pressure(meop, "metallic"),
        )

    def test_design_burst_equals_burst_composite(self):
        meop = 120.0
        self.assertAlmostEqual(
            compute_design_burst_pressure(meop, "composite"),
            compute_burst_pressure(meop, "composite"),
        )


class TestRequiredTests(unittest.TestCase):
    def test_composite_requires_all_six_tests(self):
        tests = required_tests("composite")
        self.assertEqual(len(tests), 6)

    def test_metallic_requires_proof_leak_burst(self):
        tests = required_tests("metallic")
        for t in ("proof", "leak", "burst"):
            self.assertIn(t, tests)

    def test_metallic_excludes_vibration(self):
        tests = required_tests("metallic")
        self.assertNotIn("vibration", tests)

    def test_composite_vibration_comes_before_proof(self):
        tests = required_tests("composite")
        self.assertLess(tests.index("vibration"), tests.index("proof"))

    def test_unknown_material_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            required_tests("titanium_undefined")


class TestCategorizeTest(unittest.TestCase):
    def test_proof_is_pressure(self):
        self.assertEqual(categorize_test("proof"), "pressure")

    def test_leak_is_pressure(self):
        self.assertEqual(categorize_test("leak"), "pressure")

    def test_burst_is_pressure(self):
        self.assertEqual(categorize_test("burst"), "pressure")

    def test_pressure_cycling_is_pressure(self):
        self.assertEqual(categorize_test("pressure_cycling"), "pressure")

    def test_design_burst_is_pressure(self):
        self.assertEqual(categorize_test("design_burst"), "pressure")

    def test_vibration_is_dynamic(self):
        self.assertEqual(categorize_test("vibration"), "dynamic")

    def test_unrecognized_test_is_unknown(self):
        self.assertEqual(categorize_test("thermal_vacuum"), "unknown")


class TestValidateTestResult(unittest.TestCase):
    def test_proof_passes_when_pressure_met_and_no_leak(self):
        result = validate_test_result("proof", 155.0, 150.0, leak_detected=False)
        self.assertTrue(result["pass"])

    def test_proof_fails_when_pressure_below_required(self):
        result = validate_test_result("proof", 140.0, 150.0, leak_detected=False)
        self.assertFalse(result["pass"])

    def test_proof_fails_when_leak_detected_even_at_correct_pressure(self):
        result = validate_test_result("proof", 155.0, 150.0, leak_detected=True)
        self.assertFalse(result["pass"])

    def test_burst_passes_when_at_exact_required(self):
        result = validate_test_result("burst", 200.0, 200.0)
        self.assertTrue(result["pass"])

    def test_burst_fails_when_below_required(self):
        result = validate_test_result("burst", 195.0, 200.0)
        self.assertFalse(result["pass"])

    def test_vibration_passes_with_no_anomaly(self):
        result = validate_test_result("vibration", 0.0, 0.0, structural_anomaly=False)
        self.assertTrue(result["pass"])

    def test_vibration_fails_with_structural_anomaly(self):
        result = validate_test_result("vibration", 0.0, 0.0, structural_anomaly=True)
        self.assertFalse(result["pass"])

    def test_leak_test_fails_when_leak_detected(self):
        result = validate_test_result("leak", 0.0, 0.0, leak_detected=True)
        self.assertFalse(result["pass"])

    def test_unknown_test_type_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            validate_test_result("hydrostatic", 100.0, 100.0)

    def test_negative_applied_pressure_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            validate_test_result("proof", -1.0, 150.0)

    def test_finding_string_present_on_pass(self):
        result = validate_test_result("proof", 155.0, 150.0)
        self.assertIn("PASS", result["finding"])

    def test_finding_string_present_on_failure(self):
        result = validate_test_result("proof", 100.0, 150.0)
        self.assertIn("proof", result["finding"])


class TestCheckSequence(unittest.TestCase):
    def test_complete_metallic_set(self):
        result = check_sequence(["proof", "leak", "burst"], "metallic")
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_incomplete_composite_missing_vibration(self):
        executed = ["proof", "leak", "burst", "pressure_cycling", "design_burst"]
        result = check_sequence(executed, "composite")
        self.assertFalse(result["complete"])
        self.assertIn("vibration", result["missing"])

    def test_empty_executed_returns_all_mandatory_as_missing(self):
        result = check_sequence([], "metallic")
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["missing"]), 3)

    def test_extra_tests_do_not_break_completeness(self):
        executed = ["proof", "leak", "burst", "vibration"]
        result = check_sequence(executed, "metallic")
        self.assertTrue(result["complete"])


class TestBuildQualificationReport(unittest.TestCase):
    def _metallic_full_results(self, meop):
        return [
            {"name": "proof", "applied_pressure": meop * 1.5, "leak_detected": False},
            {"name": "leak", "applied_pressure": meop * 1.5, "leak_detected": False},
            {"name": "burst", "applied_pressure": meop * 2.0, "leak_detected": False},
        ]

    def test_fully_qualified_metallic_component(self):
        report = build_qualification_report("TANK-001", "metallic", 100.0, self._metallic_full_results(100.0))
        self.assertTrue(report["qualified"])
        self.assertEqual(report["findings"], [])

    def test_missing_burst_test_leaves_unqualified(self):
        results = [
            {"name": "proof", "applied_pressure": 150.0, "leak_detected": False},
            {"name": "leak", "applied_pressure": 150.0, "leak_detected": False},
        ]
        report = build_qualification_report("TANK-002", "metallic", 100.0, results)
        self.assertFalse(report["qualified"])
        self.assertTrue(any("burst" in f for f in report["findings"]))

    def test_leak_during_proof_leaves_unqualified(self):
        results = [
            {"name": "proof", "applied_pressure": 155.0, "leak_detected": True},
            {"name": "leak", "applied_pressure": 155.0, "leak_detected": False},
            {"name": "burst", "applied_pressure": 200.0, "leak_detected": False},
        ]
        report = build_qualification_report("TANK-003", "metallic", 100.0, results)
        self.assertFalse(report["qualified"])

    def test_low_burst_pressure_leaves_unqualified(self):
        results = [
            {"name": "proof", "applied_pressure": 150.0, "leak_detected": False},
            {"name": "leak", "applied_pressure": 150.0, "leak_detected": False},
            {"name": "burst", "applied_pressure": 180.0, "leak_detected": False},
        ]
        report = build_qualification_report("TANK-004", "metallic", 100.0, results)
        self.assertFalse(report["qualified"])

    def test_unrecognized_test_entry_recorded_as_finding(self):
        results = [
            {"name": "thermal_vacuum", "applied_pressure": 0.0},
            {"name": "proof", "applied_pressure": 150.0},
            {"name": "leak", "applied_pressure": 150.0},
            {"name": "burst", "applied_pressure": 200.0},
        ]
        report = build_qualification_report("TANK-005", "metallic", 100.0, results)
        self.assertTrue(any("Unrecognized" in f for f in report["findings"]))

    def test_empty_component_id_raises(self):
        with self.assertRaises(QualificationProgrammeError):
            build_qualification_report("", "metallic", 100.0, [])

    def test_report_preserves_component_id(self):
        report = build_qualification_report("TANK-001", "metallic", 100.0, self._metallic_full_results(100.0))
        self.assertEqual(report["component_id"], "TANK-001")

    def test_report_preserves_meop(self):
        report = build_qualification_report("TANK-001", "metallic", 75.0, self._metallic_full_results(75.0))
        self.assertAlmostEqual(report["meop"], 75.0)

    def test_report_normalises_material_to_lowercase(self):
        report = build_qualification_report("TANK-001", "Metallic", 100.0, self._metallic_full_results(100.0))
        self.assertEqual(report["material"], "metallic")

    def test_vibration_anomaly_in_composite_leaves_unqualified(self):
        results = [
            {"name": "vibration", "applied_pressure": 0.0, "structural_anomaly": True},
            {"name": "proof", "applied_pressure": 150.0, "leak_detected": False},
            {"name": "leak", "applied_pressure": 150.0, "leak_detected": False},
            {"name": "pressure_cycling", "applied_pressure": 100.0},
            {"name": "design_burst", "applied_pressure": 225.0},
            {"name": "burst", "applied_pressure": 225.0},
        ]
        report = build_qualification_report("COPV-001", "composite", 100.0, results)
        self.assertFalse(report["qualified"])

    def test_fully_qualified_composite_component(self):
        meop = 80.0
        results = [
            {"name": "vibration", "applied_pressure": 0.0, "structural_anomaly": False},
            {"name": "proof", "applied_pressure": meop * 1.5, "leak_detected": False},
            {"name": "leak", "applied_pressure": meop * 1.5, "leak_detected": False},
            {"name": "pressure_cycling", "applied_pressure": meop},
            {"name": "design_burst", "applied_pressure": meop * 2.25},
            {"name": "burst", "applied_pressure": meop * 2.25},
        ]
        report = build_qualification_report("COPV-002", "composite", meop, results)
        self.assertTrue(report["qualified"])
        self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
