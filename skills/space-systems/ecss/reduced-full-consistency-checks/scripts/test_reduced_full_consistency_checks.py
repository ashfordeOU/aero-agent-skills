"""
Tests for reduced_full_consistency_checks_logic.py.
Offline, deterministic, stdlib unittest only.
Run: python3 test_reduced_full_consistency_checks.py
"""
import math
import unittest

from reduced_full_consistency_checks_logic import (
    build_mac_matrix,
    check_mac_diagonal,
    compare_cg,
    compare_frequencies,
    compare_inertia,
    compare_mass,
    compare_static_stiffness,
    compute_mac,
    run_consistency_checks,
)


class TestCompareMass(unittest.TestCase):
    def test_mass_within_tolerance_passes(self):
        result = compare_mass(1000.0, 1015.0, 2.0)
        self.assertTrue(result["passed"])   # 1.5% within 2% tol
        result2 = compare_mass(1000.0, 1010.0, 2.0)
        self.assertTrue(result2["passed"])  # 1.0% within 2% tol

    def test_mass_exactly_at_tolerance_passes(self):
        result = compare_mass(1000.0, 1020.0, 2.0)
        self.assertTrue(result["passed"])   # 2.0% == tolerance, passes (<=)
        result2 = compare_mass(1000.0, 980.0, 2.0)
        self.assertTrue(result2["passed"])  # -2.0% == tolerance, passes (<=)

    def test_mass_exceeds_tolerance_fails(self):
        result = compare_mass(1000.0, 1025.0, 2.0)
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["delta_pct"], 2.5, places=6)

    def test_mass_negative_deviation_fails(self):
        result = compare_mass(1000.0, 960.0, 3.0)
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["delta_pct"], -4.0, places=6)

    def test_mass_zero_reduced_extreme_deviation(self):
        result = compare_mass(500.0, 0.0, 2.0)
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["delta_pct"], -100.0, places=6)

    def test_mass_invalid_full_mass_raises(self):
        with self.assertRaises(ValueError):
            compare_mass(0.0, 100.0, 2.0)

    def test_mass_invalid_negative_reduced_raises(self):
        with self.assertRaises(ValueError):
            compare_mass(100.0, -1.0, 2.0)


class TestCompareCG(unittest.TestCase):
    def test_cg_identical_passes(self):
        result = compare_cg([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], 0.001)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["distance_m"], 0.0, places=10)

    def test_cg_within_tolerance_passes(self):
        result = compare_cg([0.0, 0.0, 0.0], [0.003, 0.0, 0.0], 0.005)
        self.assertTrue(result["passed"])

    def test_cg_exceeds_tolerance_fails(self):
        result = compare_cg([0.0, 0.0, 0.0], [0.01, 0.01, 0.01], 0.005)
        self.assertFalse(result["passed"])
        expected_dist = math.sqrt(3) * 0.01
        self.assertAlmostEqual(result["distance_m"], expected_dist, places=8)

    def test_cg_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            compare_cg([1.0, 2.0], [1.0, 2.0, 3.0], 0.01)


class TestCompareInertia(unittest.TestCase):
    def _make_inertia(self, scale=1.0):
        return {"Ixx": 100.0 * scale, "Iyy": 200.0 * scale, "Izz": 300.0 * scale,
                "Ixy": 10.0 * scale, "Ixz": 5.0 * scale, "Iyz": 8.0 * scale}

    def test_inertia_exact_match_passes(self):
        base = self._make_inertia()
        result = compare_inertia(base, base, 2.0)
        self.assertTrue(result["passed"])

    def test_inertia_within_tolerance_passes(self):
        full = self._make_inertia(1.0)
        reduced = self._make_inertia(1.015)  # 1.5% increase on all
        result = compare_inertia(full, reduced, 2.0)
        self.assertTrue(result["passed"])

    def test_inertia_exceeds_tolerance_fails(self):
        full = self._make_inertia(1.0)
        reduced = dict(self._make_inertia(1.0))
        reduced["Izz"] = 330.0  # 10% deviation on Izz
        result = compare_inertia(full, reduced, 2.0)
        self.assertFalse(result["passed"])
        self.assertFalse(result["components"]["Izz"]["passed"])
        self.assertAlmostEqual(result["components"]["Izz"]["delta_pct"], 10.0, places=6)

    def test_inertia_zero_reference_zero_value_passes(self):
        full = {"Ixx": 100.0, "Iyy": 200.0, "Izz": 300.0,
                "Ixy": 0.0, "Ixz": 0.0, "Iyz": 0.0}
        reduced = dict(full)
        result = compare_inertia(full, reduced, 2.0)
        self.assertTrue(result["passed"])

    def test_inertia_missing_key_raises(self):
        full = {"Ixx": 100.0, "Iyy": 200.0}
        with self.assertRaises(ValueError):
            compare_inertia(full, full, 2.0)


class TestComputeMAC(unittest.TestCase):
    def test_mac_identical_vectors_is_one(self):
        v = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(compute_mac(v, v), 1.0, places=10)

    def test_mac_opposite_vectors_is_one(self):
        v = [1.0, 2.0, 3.0]
        neg_v = [-1.0, -2.0, -3.0]
        self.assertAlmostEqual(compute_mac(v, neg_v), 1.0, places=10)

    def test_mac_orthogonal_vectors_is_zero(self):
        self.assertAlmostEqual(compute_mac([1.0, 0.0], [0.0, 1.0]), 0.0, places=10)

    def test_mac_partial_correlation(self):
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        mac_val = compute_mac(a, b)
        self.assertGreater(mac_val, 0.0)
        self.assertLess(mac_val, 1.0)

    def test_mac_zero_vector_returns_zero(self):
        self.assertEqual(compute_mac([0.0, 0.0], [1.0, 0.0]), 0.0)

    def test_mac_mismatched_length_raises(self):
        with self.assertRaises(ValueError):
            compute_mac([1.0, 2.0], [1.0, 2.0, 3.0])


class TestMACMatrix(unittest.TestCase):
    def test_mac_diagonal_all_pass(self):
        modes = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        matrix = build_mac_matrix(modes, modes)
        findings = check_mac_diagonal(matrix, 0.9, 3)
        self.assertTrue(all(f["passed"] for f in findings))

    def test_mac_diagonal_low_value_fails(self):
        full_modes = [[1.0, 0.0], [0.0, 1.0]]
        reduced_modes = [[0.707, 0.707], [0.0, 1.0]]
        matrix = build_mac_matrix(full_modes, reduced_modes)
        findings = check_mac_diagonal(matrix, 0.9, 2)
        diag_findings = [f for f in findings if f.get("check_type") == "diagonal"]
        self.assertFalse(diag_findings[0]["passed"])  # first diagonal should fail


class TestCompareFrequencies(unittest.TestCase):
    def test_frequencies_within_tolerance_all_pass(self):
        full = [10.0, 25.0, 50.0]
        reduced = [10.2, 25.5, 50.8]  # all within 3%
        results = compare_frequencies(full, reduced, 3.0)
        self.assertTrue(all(r["passed"] for r in results))

    def test_frequencies_one_exceeds_tolerance_fails(self):
        full = [10.0, 25.0, 50.0]
        reduced = [10.5, 25.0, 52.0]  # 5% and 4% deviations
        results = compare_frequencies(full, reduced, 3.0)
        failed = [r for r in results if not r["passed"]]
        self.assertEqual(len(failed), 2)

    def test_frequencies_mismatched_length_raises(self):
        with self.assertRaises(ValueError):
            compare_frequencies([10.0, 20.0], [10.0], 3.0)

    def test_frequencies_zero_full_freq_raises(self):
        with self.assertRaises(ValueError):
            compare_frequencies([0.0, 20.0], [0.0, 20.0], 3.0)


class TestCompareStaticStiffness(unittest.TestCase):
    def test_stiffness_within_tolerance_passes(self):
        full = [1e6, 2e6, 3e6]
        reduced = [1.04e6, 2.05e6, 2.97e6]  # within 5%
        results = compare_static_stiffness(full, reduced, 5.0)
        self.assertTrue(all(r["passed"] for r in results))

    def test_stiffness_exceeds_tolerance_fails(self):
        full = [1e6]
        reduced = [1.1e6]  # 10% deviation
        results = compare_static_stiffness(full, reduced, 5.0)
        self.assertFalse(results[0]["passed"])
        self.assertAlmostEqual(results[0]["delta_pct"], 10.0, places=4)

    def test_stiffness_mismatched_length_raises(self):
        with self.assertRaises(ValueError):
            compare_static_stiffness([1e6, 2e6], [1e6], 5.0)


class TestRunConsistencyChecks(unittest.TestCase):
    def _make_models(self, mass_scale=1.0, freq_scale=1.0):
        inertia = {"Ixx": 100.0, "Iyy": 200.0, "Izz": 300.0,
                   "Ixy": 10.0, "Ixz": 5.0, "Iyz": 8.0}
        full = {
            "mass": 1000.0,
            "cg": [0.5, 0.0, 1.2],
            "inertia": inertia,
            "frequencies": [5.0, 12.0, 25.0],
            "mode_shapes": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "static_stiffness": [1e7, 2e7, 5e7],
        }
        inertia_r = {k: v * mass_scale for k, v in inertia.items()}
        reduced = {
            "mass": 1000.0 * mass_scale,
            "cg": [0.501, 0.0, 1.2],
            "inertia": inertia_r,
            "frequencies": [f * freq_scale for f in full["frequencies"]],
            "mode_shapes": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "static_stiffness": [1.02e7, 2.01e7, 5.03e7],
        }
        return full, reduced

    def _default_criteria(self):
        return {
            "mass_tolerance_pct": 2.0,
            "cg_tolerance_m": 0.01,
            "inertia_tolerance_pct": 2.0,
            "freq_tolerance_pct": 3.0,
            "mac_threshold": 0.9,
            "stiffness_tolerance_pct": 5.0,
        }

    def test_all_checks_pass_when_models_consistent(self):
        full, reduced = self._make_models()
        result = run_consistency_checks(full, reduced, self._default_criteria())
        self.assertTrue(result["overall_passed"])
        self.assertTrue(result["summary"]["mass_passed"])
        self.assertTrue(result["summary"]["mac_passed"])

    def test_overall_fails_when_mass_exceeds_tolerance(self):
        full, reduced = self._make_models(mass_scale=1.05)  # 5% mass deviation
        result = run_consistency_checks(full, reduced, self._default_criteria())
        self.assertFalse(result["overall_passed"])
        self.assertFalse(result["summary"]["mass_passed"])

    def test_overall_fails_when_frequencies_deviate(self):
        full, reduced = self._make_models(freq_scale=1.08)  # 8% freq deviation
        result = run_consistency_checks(full, reduced, self._default_criteria())
        self.assertFalse(result["overall_passed"])
        self.assertFalse(result["summary"]["frequencies_passed"])
        self.assertEqual(result["summary"]["freq_failures"], 3)

    def test_summary_keys_present(self):
        full, reduced = self._make_models()
        result = run_consistency_checks(full, reduced, self._default_criteria())
        for key in ("overall_passed", "mass", "cg", "inertia",
                    "frequencies", "mac_findings", "static_stiffness", "summary"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
