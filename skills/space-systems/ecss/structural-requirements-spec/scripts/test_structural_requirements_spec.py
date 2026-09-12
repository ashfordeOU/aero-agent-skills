import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from structural_requirements_spec_logic import (
    categorize_requirement,
    compute_design_limit_load,
    compute_design_loads,
    compute_margin_of_safety,
    validate_requirement,
    validate_requirement_set,
    assess_requirement_baseline,
    FUNCTIONAL_REQ_TYPES,
    PERFORMANCE_REQ_TYPES,
    VALID_VERIFICATION_METHODS,
)


class TestCategorizeRequirement(unittest.TestCase):

    def test_stiffness_is_functional(self):
        self.assertEqual(categorize_requirement("stiffness"), "functional")

    def test_strength_is_functional(self):
        self.assertEqual(categorize_requirement("strength"), "functional")

    def test_buckling_is_functional(self):
        self.assertEqual(categorize_requirement("buckling"), "functional")

    def test_fracture_control_is_functional(self):
        self.assertEqual(categorize_requirement("fracture_control"), "functional")

    def test_margin_of_safety_is_performance(self):
        self.assertEqual(categorize_requirement("margin_of_safety"), "performance")

    def test_mass_budget_is_performance(self):
        self.assertEqual(categorize_requirement("mass_budget"), "performance")

    def test_deflection_limit_is_performance(self):
        self.assertEqual(categorize_requirement("deflection_limit"), "performance")

    def test_case_insensitive_functional(self):
        self.assertEqual(categorize_requirement("STIFFNESS"), "functional")

    def test_space_normalized_performance(self):
        self.assertEqual(categorize_requirement("Margin Of Safety"), "performance")

    def test_hyphen_normalized_functional(self):
        self.assertEqual(categorize_requirement("fracture-control"), "functional")

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_requirement("vibration_isolation")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_requirement("")


class TestComputeDesignLimitLoad(unittest.TestCase):

    def test_nominal_load_no_amplification(self):
        self.assertAlmostEqual(compute_design_limit_load(200.0), 200.0)

    def test_with_dynamic_factor(self):
        self.assertAlmostEqual(compute_design_limit_load(100.0, dynamic_factor=1.25), 125.0)

    def test_with_both_factors(self):
        # 100 * 1.25 * 1.2 = 150.0
        self.assertAlmostEqual(compute_design_limit_load(100.0, 1.25, 1.2), 150.0)

    def test_zero_nominal_load_allowed(self):
        self.assertAlmostEqual(compute_design_limit_load(0.0, 1.5, 1.2), 0.0)

    def test_dynamic_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_design_limit_load(100.0, dynamic_factor=0.9)

    def test_quasi_static_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_design_limit_load(100.0, quasi_static_factor=0.5)

    def test_negative_nominal_load_raises(self):
        with self.assertRaises(ValueError):
            compute_design_limit_load(-50.0)


class TestComputeDesignLoads(unittest.TestCase):

    def test_standard_metallic_factors(self):
        result = compute_design_loads(1000.0, 1.0, 1.25)
        self.assertAlmostEqual(result["dll"], 1000.0)
        self.assertAlmostEqual(result["dyl"], 1000.0)
        self.assertAlmostEqual(result["dul"], 1250.0)

    def test_higher_yield_factor(self):
        result = compute_design_loads(800.0, 1.1, 1.5)
        self.assertAlmostEqual(result["dyl"], 880.0)
        self.assertAlmostEqual(result["dul"], 1200.0)

    def test_all_keys_present(self):
        result = compute_design_loads(500.0, 1.0, 1.25)
        for key in ("dll", "dyl", "dul", "yield_fs", "ultimate_fs"):
            self.assertIn(key, result)

    def test_yield_fs_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(1000.0, 0.9, 1.25)

    def test_ultimate_fs_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(1000.0, 1.0, 0.8)

    def test_ultimate_fs_less_than_yield_fs_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(1000.0, 1.5, 1.1)

    def test_negative_dll_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(-100.0, 1.0, 1.25)


class TestComputeMarginOfSafety(unittest.TestCase):

    def test_positive_mos(self):
        # allowable 1500, applied 1000 -> MoS = 0.5
        self.assertAlmostEqual(compute_margin_of_safety(1500.0, 1000.0), 0.5)

    def test_zero_mos_boundary(self):
        self.assertAlmostEqual(compute_margin_of_safety(1000.0, 1000.0), 0.0)

    def test_negative_mos(self):
        # allowable 800, applied 1000 -> MoS = -0.2
        self.assertAlmostEqual(compute_margin_of_safety(800.0, 1000.0), -0.2)

    def test_large_margin(self):
        self.assertAlmostEqual(compute_margin_of_safety(3000.0, 1000.0), 2.0)

    def test_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(1000.0, 0.0)

    def test_negative_applied_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(1000.0, -100.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 500.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(-100.0, 500.0)


class TestValidateRequirement(unittest.TestCase):

    def _req(self, req_id="SR-001", req_type="stiffness",
             threshold="f > 40 Hz", vm="analysis"):
        return {"id": req_id, "type": req_type,
                "threshold": threshold, "verification_method": vm}

    def test_complete_requirement_no_findings(self):
        self.assertEqual(validate_requirement(self._req()), [])

    def test_missing_threshold_flagged(self):
        req = self._req(threshold="")
        findings = validate_requirement(req)
        self.assertTrue(any("threshold" in f for f in findings))

    def test_missing_id_flagged(self):
        req = self._req(req_id="")
        findings = validate_requirement(req)
        self.assertTrue(any("'id'" in f for f in findings))

    def test_unknown_type_flagged(self):
        req = self._req(req_type="magic_constraint")
        findings = validate_requirement(req)
        self.assertGreater(len(findings), 0)

    def test_unknown_verification_method_flagged(self):
        req = self._req(vm="estimation")
        findings = validate_requirement(req)
        self.assertTrue(any("verification_method" in f for f in findings))

    def test_none_threshold_flagged(self):
        req = self._req()
        req["threshold"] = None
        findings = validate_requirement(req)
        self.assertTrue(any("threshold" in f for f in findings))


class TestValidateRequirementSet(unittest.TestCase):

    def _req(self, req_id, req_type="stiffness",
             threshold="f > 40 Hz", vm="analysis"):
        return {"id": req_id, "type": req_type,
                "threshold": threshold, "verification_method": vm}

    def test_valid_set_is_compliant(self):
        reqs = [
            self._req("SR-001"),
            self._req("SR-002", req_type="strength", threshold="MoS >= 0"),
            self._req("SR-003", req_type="mass_budget", threshold="< 50 kg", vm="review"),
        ]
        result = validate_requirement_set(reqs)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_empty_set_not_compliant(self):
        result = validate_requirement_set([])
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_missing_threshold_makes_set_non_compliant(self):
        reqs = [{"id": "SR-001", "type": "stiffness",
                 "threshold": "", "verification_method": "analysis"}]
        result = validate_requirement_set(reqs)
        self.assertFalse(result["compliant"])

    def test_duplicate_id_flagged(self):
        reqs = [self._req("SR-001"), self._req("SR-001", req_type="strength")]
        result = validate_requirement_set(reqs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Duplicate" in f for f in result["findings"]))

    def test_single_invalid_req_makes_set_non_compliant(self):
        reqs = [
            self._req("SR-001"),
            {"id": "SR-002", "type": "bad_type",
             "threshold": "x", "verification_method": "analysis"},
        ]
        result = validate_requirement_set(reqs)
        self.assertFalse(result["compliant"])


class TestAssessRequirementBaseline(unittest.TestCase):

    def _base_reqs(self):
        return [
            {"id": "SR-001", "type": "stiffness",
             "threshold": "f > 35 Hz", "verification_method": "analysis"},
            {"id": "SR-002", "type": "strength",
             "threshold": "MoS >= 0", "verification_method": "analysis"},
        ]

    def test_fully_compliant_baseline(self):
        lcs = [{"id": "LC-01", "dll": 1000.0, "yield_fs": 1.0, "ultimate_fs": 1.25}]
        allowables = {"LC-01": 1500.0}  # MoS = 1500/1250 - 1 = 0.2
        result = assess_requirement_baseline(self._base_reqs(), lcs, allowables)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["mos_findings"], [])
        self.assertEqual(result["load_findings"], [])

    def test_mos_failure_makes_baseline_non_compliant(self):
        lcs = [{"id": "LC-01", "dll": 1000.0, "yield_fs": 1.0, "ultimate_fs": 1.25}]
        allowables = {"LC-01": 1200.0}  # DUL=1250, allowable=1200 -> MoS < 0
        result = assess_requirement_baseline(self._base_reqs(), lcs, allowables)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("MoS" in f for f in result["mos_findings"]))

    def test_missing_allowable_makes_baseline_non_compliant(self):
        lcs = [{"id": "LC-01", "dll": 1000.0, "yield_fs": 1.0, "ultimate_fs": 1.25}]
        result = assess_requirement_baseline(self._base_reqs(), lcs, {})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no allowable" in f for f in result["mos_findings"]))

    def test_bad_load_case_key_flagged(self):
        lcs = [{"id": "LC-01", "dll": 1000.0, "yield_fs": 1.0}]  # missing ultimate_fs
        result = assess_requirement_baseline(self._base_reqs(), lcs, {"LC-01": 2000.0})
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["load_findings"]) > 0)

    def test_invalid_requirements_propagate(self):
        bad_reqs = [{"id": "SR-001", "type": "stiffness",
                     "threshold": "", "verification_method": "analysis"}]
        lcs = [{"id": "LC-01", "dll": 500.0, "yield_fs": 1.0, "ultimate_fs": 1.25}]
        allowables = {"LC-01": 1000.0}
        result = assess_requirement_baseline(bad_reqs, lcs, allowables)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["req_validation"]["compliant"])

    def test_exact_mos_zero_is_compliant(self):
        lcs = [{"id": "LC-01", "dll": 1000.0, "yield_fs": 1.0, "ultimate_fs": 1.25}]
        allowables = {"LC-01": 1250.0}  # DUL=1250, allowable=1250 -> MoS = 0.0
        result = assess_requirement_baseline(self._base_reqs(), lcs, allowables)
        self.assertTrue(result["compliant"])

    def test_multiple_load_cases(self):
        lcs = [
            {"id": "LC-01", "dll": 800.0, "yield_fs": 1.0, "ultimate_fs": 1.25},
            {"id": "LC-02", "dll": 600.0, "yield_fs": 1.1, "ultimate_fs": 1.5},
        ]
        allowables = {"LC-01": 2000.0, "LC-02": 1500.0}
        result = assess_requirement_baseline(self._base_reqs(), lcs, allowables)
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
