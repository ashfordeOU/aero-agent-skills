"""
Offline deterministic unit tests for thermo_elastic_and_thermal_cycling_test_logic.
stdlib unittest only.  Run: python3 test_thermo_elastic_and_thermal_cycling_test.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from thermo_elastic_and_thermal_cycling_test_logic import (
    assess_test_result,
    categorize_test_type,
    check_cycle_count_sufficient,
    check_deformation_within_allowable,
    check_rate_within_limit,
    compute_required_test_cycles,
    compute_temperature_delta,
    compute_thermal_strain,
    compute_thermo_elastic_distortion,
    validate_soak_duration,
    validate_thermal_profile,
)


# ---------------------------------------------------------------------------
# categorize_test_type
# ---------------------------------------------------------------------------

class TestCategorizeTestType(unittest.TestCase):

    def test_thermo_elastic_accepted(self):
        self.assertEqual(categorize_test_type("thermo-elastic"), "thermo-elastic")

    def test_thermal_cycling_accepted(self):
        self.assertEqual(categorize_test_type("thermal-cycling"), "thermal-cycling")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_test_type("thermal-shock")

    def test_whitespace_stripped(self):
        self.assertEqual(categorize_test_type("  thermo-elastic  "), "thermo-elastic")

    def test_case_normalized(self):
        self.assertEqual(categorize_test_type("THERMAL-CYCLING"), "thermal-cycling")


# ---------------------------------------------------------------------------
# validate_thermal_profile
# ---------------------------------------------------------------------------

class TestValidateThermalProfile(unittest.TestCase):

    def test_valid_profile_returns_no_findings(self):
        findings = validate_thermal_profile(213.0, 373.0, 2.0, 30.0)
        self.assertEqual(findings, [])

    def test_min_greater_than_max_flagged(self):
        findings = validate_thermal_profile(400.0, 213.0, 2.0, 30.0)
        self.assertTrue(any("T_min_K" in f for f in findings))

    def test_equal_temperatures_flagged(self):
        findings = validate_thermal_profile(300.0, 300.0, 2.0, 30.0)
        self.assertGreater(len(findings), 0)

    def test_negative_ramp_rate_flagged(self):
        findings = validate_thermal_profile(213.0, 373.0, -1.0, 30.0)
        self.assertTrue(any("rate_K_per_min" in f for f in findings))

    def test_zero_soak_duration_flagged(self):
        findings = validate_thermal_profile(213.0, 373.0, 2.0, 0.0)
        self.assertTrue(any("soak_min" in f for f in findings))

    def test_sub_absolute_zero_tmin_flagged(self):
        findings = validate_thermal_profile(-5.0, 373.0, 2.0, 30.0)
        self.assertTrue(any("T_min_K" in f and "absolute zero" in f for f in findings))


# ---------------------------------------------------------------------------
# compute_temperature_delta
# ---------------------------------------------------------------------------

class TestComputeTemperatureDelta(unittest.TestCase):

    def test_known_delta(self):
        self.assertAlmostEqual(compute_temperature_delta(373.0, 213.0), 160.0)

    def test_inverted_inputs_raise(self):
        with self.assertRaises(ValueError):
            compute_temperature_delta(213.0, 373.0)

    def test_equal_inputs_raise(self):
        with self.assertRaises(ValueError):
            compute_temperature_delta(300.0, 300.0)


# ---------------------------------------------------------------------------
# compute_thermal_strain
# ---------------------------------------------------------------------------

class TestComputeThermalStrain(unittest.TestCase):

    def test_aluminium_alloy_100K(self):
        # CTE = 23e-6 /K, ΔT = 100 K → strain = 2.3e-3
        result = compute_thermal_strain(23e-6, 100.0)
        self.assertAlmostEqual(result, 2.3e-3, places=10)

    def test_zero_delta_T_gives_zero(self):
        self.assertEqual(compute_thermal_strain(23e-6, 0.0), 0.0)

    def test_zero_CTE_gives_zero(self):
        self.assertEqual(compute_thermal_strain(0.0, 100.0), 0.0)

    def test_negative_CTE_raises(self):
        with self.assertRaises(ValueError):
            compute_thermal_strain(-1e-6, 100.0)

    def test_negative_delta_T_raises(self):
        with self.assertRaises(ValueError):
            compute_thermal_strain(23e-6, -10.0)


# ---------------------------------------------------------------------------
# compute_thermo_elastic_distortion
# ---------------------------------------------------------------------------

class TestComputeThermoElasticDistortion(unittest.TestCase):

    def test_known_values(self):
        strain = compute_thermal_strain(23e-6, 100.0)
        distortion = compute_thermo_elastic_distortion(strain, 1.0)
        self.assertAlmostEqual(distortion, 2.3e-3, places=10)

    def test_two_metre_member(self):
        strain = compute_thermal_strain(10e-6, 50.0)  # 5e-4
        distortion = compute_thermo_elastic_distortion(strain, 2.0)
        self.assertAlmostEqual(distortion, 1.0e-3, places=12)

    def test_zero_length_raises(self):
        with self.assertRaises(ValueError):
            compute_thermo_elastic_distortion(1e-3, 0.0)

    def test_negative_strain_raises(self):
        with self.assertRaises(ValueError):
            compute_thermo_elastic_distortion(-1e-4, 1.0)


# ---------------------------------------------------------------------------
# check_deformation_within_allowable
# ---------------------------------------------------------------------------

class TestCheckDeformationWithinAllowable(unittest.TestCase):

    def test_within_allowable_passes(self):
        self.assertTrue(check_deformation_within_allowable(0.001, 0.005))

    def test_exceeds_allowable_fails(self):
        self.assertFalse(check_deformation_within_allowable(0.010, 0.005))

    def test_exactly_at_allowable_passes(self):
        self.assertTrue(check_deformation_within_allowable(0.005, 0.005))

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            check_deformation_within_allowable(0.001, 0.0)


# ---------------------------------------------------------------------------
# compute_required_test_cycles
# ---------------------------------------------------------------------------

class TestComputeRequiredTestCycles(unittest.TestCase):

    def test_standard_50_cycle_life(self):
        # 50 design cycles × factor 2 = 100 > floor 3
        self.assertEqual(compute_required_test_cycles(50, 2), 100)

    def test_floor_applied_for_short_life(self):
        # 1 design cycle × factor 2 = 2 → floor raises to 3
        self.assertEqual(compute_required_test_cycles(1, 2), 3)

    def test_custom_qualification_factor(self):
        self.assertEqual(compute_required_test_cycles(10, 3), 30)

    def test_zero_design_life_raises(self):
        with self.assertRaises(ValueError):
            compute_required_test_cycles(0, 2)

    def test_zero_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_required_test_cycles(10, 0)


# ---------------------------------------------------------------------------
# check_cycle_count_sufficient
# ---------------------------------------------------------------------------

class TestCheckCycleCountSufficient(unittest.TestCase):

    def test_exact_match_passes(self):
        self.assertTrue(check_cycle_count_sufficient(100, 100))

    def test_surplus_passes(self):
        self.assertTrue(check_cycle_count_sufficient(110, 100))

    def test_shortfall_fails(self):
        self.assertFalse(check_cycle_count_sufficient(99, 100))

    def test_negative_actual_raises(self):
        with self.assertRaises(ValueError):
            check_cycle_count_sufficient(-1, 100)


# ---------------------------------------------------------------------------
# validate_soak_duration
# ---------------------------------------------------------------------------

class TestValidateSoakDuration(unittest.TestCase):

    def test_sufficient_soak_passes(self):
        self.assertTrue(validate_soak_duration(30.0, 10.0))

    def test_insufficient_soak_fails(self):
        self.assertFalse(validate_soak_duration(5.0, 10.0))

    def test_exact_minimum_passes(self):
        self.assertTrue(validate_soak_duration(10.0, 10.0))

    def test_zero_minimum_raises(self):
        with self.assertRaises(ValueError):
            validate_soak_duration(30.0, 0.0)


# ---------------------------------------------------------------------------
# check_rate_within_limit
# ---------------------------------------------------------------------------

class TestCheckRateWithinLimit(unittest.TestCase):

    def test_within_limit_passes(self):
        self.assertTrue(check_rate_within_limit(2.0, 5.0))

    def test_exceeds_limit_fails(self):
        self.assertFalse(check_rate_within_limit(6.0, 5.0))

    def test_exactly_at_limit_passes(self):
        self.assertTrue(check_rate_within_limit(5.0, 5.0))

    def test_zero_max_rate_raises(self):
        with self.assertRaises(ValueError):
            check_rate_within_limit(2.0, 0.0)

    def test_zero_actual_rate_raises(self):
        with self.assertRaises(ValueError):
            check_rate_within_limit(0.0, 5.0)


# ---------------------------------------------------------------------------
# assess_test_result
# ---------------------------------------------------------------------------

class TestAssessTestResult(unittest.TestCase):

    def test_empty_findings_gives_pass(self):
        result = assess_test_result([])
        self.assertEqual(result["status"], "PASS")

    def test_findings_give_fail(self):
        result = assess_test_result(["Distortion exceeds allowable."])
        self.assertEqual(result["status"], "FAIL")

    def test_finding_count_correct(self):
        result = assess_test_result(["A", "B", "C"])
        self.assertEqual(result["finding_count"], 3)

    def test_findings_list_preserved(self):
        raw = ["Finding 1", "Finding 2"]
        result = assess_test_result(raw)
        self.assertEqual(result["findings"], raw)

    def test_empty_list_finding_count_zero(self):
        result = assess_test_result([])
        self.assertEqual(result["finding_count"], 0)


# ---------------------------------------------------------------------------
# end-to-end scenario: full thermo-elastic check
# ---------------------------------------------------------------------------

class TestEndToEndThermoElastic(unittest.TestCase):

    def test_compliant_scenario(self):
        test_type = categorize_test_type("thermo-elastic")
        self.assertEqual(test_type, "thermo-elastic")

        profile_findings = validate_thermal_profile(213.0, 373.0, 1.5, 30.0)
        self.assertEqual(profile_findings, [])

        delta_T = compute_temperature_delta(373.0, 213.0)
        strain = compute_thermal_strain(23e-6, delta_T)
        distortion = compute_thermo_elastic_distortion(strain, 0.5)
        within = check_deformation_within_allowable(distortion, 0.01)
        self.assertTrue(within)

        findings = []
        if not within:
            findings.append("Distortion exceeds allowable.")
        result = assess_test_result(findings)
        self.assertEqual(result["status"], "PASS")

    def test_non_compliant_scenario(self):
        strain = compute_thermal_strain(50e-6, 200.0)
        distortion = compute_thermo_elastic_distortion(strain, 2.0)
        within = check_deformation_within_allowable(distortion, 0.005)
        self.assertFalse(within)

        findings = ["Distortion {:.4f} m exceeds allowable 0.0050 m.".format(distortion)]
        result = assess_test_result(findings)
        self.assertEqual(result["status"], "FAIL")


# ---------------------------------------------------------------------------
# end-to-end scenario: full thermal-cycling check
# ---------------------------------------------------------------------------

class TestEndToEndThermalCycling(unittest.TestCase):

    def test_compliant_cycling_campaign(self):
        test_type = categorize_test_type("thermal-cycling")
        self.assertEqual(test_type, "thermal-cycling")

        required = compute_required_test_cycles(50, 2)
        self.assertEqual(required, 100)

        sufficient = check_cycle_count_sufficient(105, required)
        self.assertTrue(sufficient)

        soak_ok = validate_soak_duration(30.0, 10.0)
        self.assertTrue(soak_ok)

        rate_ok = check_rate_within_limit(1.5, 3.0)
        self.assertTrue(rate_ok)

        findings = []
        if not sufficient:
            findings.append("Cycle count insufficient.")
        if not soak_ok:
            findings.append("Soak duration below minimum.")
        if not rate_ok:
            findings.append("Ramp rate exceeds limit.")

        result = assess_test_result(findings)
        self.assertEqual(result["status"], "PASS")

    def test_short_cycle_count_fails(self):
        required = compute_required_test_cycles(50, 2)
        sufficient = check_cycle_count_sufficient(80, required)
        self.assertFalse(sufficient)

        findings = ["Actual cycles 80 below required {}.".format(required)]
        result = assess_test_result(findings)
        self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
