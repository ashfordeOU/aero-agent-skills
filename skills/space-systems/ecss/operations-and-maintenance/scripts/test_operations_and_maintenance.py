"""
Offline deterministic unittest suite for operations_and_maintenance_logic.
Run: python3 test_operations_and_maintenance.py
stdlib only, no network access.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from operations_and_maintenance_logic import (
    compute_max_allowable_operating_pressure,
    check_operating_pressure,
    assess_damage,
    compute_maintenance_interval,
    check_inspection_finding,
    check_service_life,
    VALID_DAMAGE_TYPES,
    VALID_FINDING_TYPES,
)


class TestComputeMAOP(unittest.TestCase):

    def test_nominal_maop_with_typical_safety_factor(self):
        maop = compute_max_allowable_operating_pressure(1_500_000, 1.5)
        self.assertAlmostEqual(maop, 1_000_000.0)

    def test_unity_safety_factor_returns_proof_pressure(self):
        maop = compute_max_allowable_operating_pressure(1_000_000, 1.0)
        self.assertAlmostEqual(maop, 1_000_000.0)

    def test_higher_safety_factor_lowers_maop(self):
        maop = compute_max_allowable_operating_pressure(2_000_000, 2.0)
        self.assertAlmostEqual(maop, 1_000_000.0)

    def test_invalid_zero_proof_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_max_allowable_operating_pressure(0, 1.5)

    def test_invalid_negative_proof_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_max_allowable_operating_pressure(-100, 1.5)

    def test_safety_factor_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            compute_max_allowable_operating_pressure(1_000_000, 0.5)


class TestCheckOperatingPressure(unittest.TestCase):

    def test_pressure_well_below_maop_passes(self):
        result = check_operating_pressure(800_000, 1_000_000)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["margin_fraction"], 0.2)

    def test_pressure_exceeding_maop_fails(self):
        result = check_operating_pressure(1_200_000, 1_000_000)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["status"], "EXCEED")
        self.assertAlmostEqual(result["margin_fraction"], -0.2)

    def test_pressure_exactly_at_maop_passes(self):
        result = check_operating_pressure(1_000_000, 1_000_000)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_fraction"], 0.0)

    def test_invalid_zero_operating_pressure_raises(self):
        with self.assertRaises(ValueError):
            check_operating_pressure(0, 1_000_000)

    def test_invalid_zero_maop_raises(self):
        with self.assertRaises(ValueError):
            check_operating_pressure(800_000, 0)


class TestAssessDamage(unittest.TestCase):

    def test_small_dent_well_below_adl_is_accepted(self):
        result = assess_damage(2.0, 10.0, "dent")
        self.assertEqual(result["disposition"], "ACCEPT")
        self.assertAlmostEqual(result["ratio"], 0.2)

    def test_dent_at_exact_accept_threshold_is_accepted(self):
        result = assess_damage(7.5, 10.0, "dent")
        self.assertEqual(result["disposition"], "ACCEPT")

    def test_dent_just_above_accept_threshold_is_conditional(self):
        result = assess_damage(7.6, 10.0, "dent")
        self.assertEqual(result["disposition"], "CONDITIONAL")

    def test_damage_near_adl_is_conditional(self):
        result = assess_damage(8.0, 10.0, "scratch")
        self.assertEqual(result["disposition"], "CONDITIONAL")

    def test_damage_at_adl_is_conditional(self):
        result = assess_damage(10.0, 10.0, "delamination")
        self.assertEqual(result["disposition"], "CONDITIONAL")

    def test_crack_beyond_adl_is_rejected(self):
        result = assess_damage(15.0, 10.0, "crack")
        self.assertEqual(result["disposition"], "REJECT")
        self.assertAlmostEqual(result["ratio"], 1.5)

    def test_zero_observed_size_is_accepted(self):
        result = assess_damage(0.0, 10.0, "corrosion")
        self.assertEqual(result["disposition"], "ACCEPT")
        self.assertAlmostEqual(result["ratio"], 0.0)

    def test_unrecognized_damage_type_raises(self):
        with self.assertRaises(ValueError):
            assess_damage(5.0, 10.0, "gouging")

    def test_negative_observed_size_raises(self):
        with self.assertRaises(ValueError):
            assess_damage(-1.0, 10.0, "dent")

    def test_zero_adl_raises(self):
        with self.assertRaises(ValueError):
            assess_damage(5.0, 0.0, "dent")


class TestComputeMaintenanceInterval(unittest.TestCase):

    def test_first_interval_from_zero_cycles(self):
        result = compute_maintenance_interval(1000, 0.25, 0)
        self.assertAlmostEqual(result["interval_cycles"], 250.0)
        self.assertAlmostEqual(result["next_due_cycle"], 250.0)
        self.assertFalse(result["overdue_at_design_life"])

    def test_subsequent_interval_from_prior_inspection(self):
        result = compute_maintenance_interval(1000, 0.25, 250)
        self.assertAlmostEqual(result["next_due_cycle"], 500.0)
        self.assertFalse(result["overdue_at_design_life"])

    def test_next_due_beyond_design_life_flags_overdue(self):
        result = compute_maintenance_interval(1000, 0.9, 200)
        self.assertTrue(result["overdue_at_design_life"])

    def test_next_due_exactly_at_design_life_is_not_overdue(self):
        result = compute_maintenance_interval(1000, 0.75, 250)
        self.assertAlmostEqual(result["next_due_cycle"], 1000.0)
        self.assertFalse(result["overdue_at_design_life"])

    def test_invalid_zero_design_life_raises(self):
        with self.assertRaises(ValueError):
            compute_maintenance_interval(0, 0.25, 0)

    def test_invalid_zero_fraction_raises(self):
        with self.assertRaises(ValueError):
            compute_maintenance_interval(1000, 0.0, 0)

    def test_invalid_negative_last_inspection_raises(self):
        with self.assertRaises(ValueError):
            compute_maintenance_interval(1000, 0.25, -10)


class TestCheckInspectionFinding(unittest.TestCase):

    def test_dimensional_measurement_in_band_passes(self):
        result = check_inspection_finding("dimensional", 10.5, 10.0, 11.0)
        self.assertEqual(result["status"], "PASS")

    def test_measurement_at_lower_limit_passes(self):
        result = check_inspection_finding("dimensional", 10.0, 10.0, 11.0)
        self.assertEqual(result["status"], "PASS")

    def test_measurement_at_upper_limit_passes(self):
        result = check_inspection_finding("torque", 50.0, 40.0, 50.0)
        self.assertEqual(result["status"], "PASS")

    def test_measurement_below_lower_limit_fails(self):
        result = check_inspection_finding("dimensional", 9.5, 10.0, 11.0)
        self.assertEqual(result["status"], "FAIL")

    def test_measurement_above_upper_limit_fails(self):
        result = check_inspection_finding("torque", 55.0, 40.0, 50.0)
        self.assertEqual(result["status"], "FAIL")

    def test_pressure_test_finding_in_band_passes(self):
        result = check_inspection_finding("pressure_test", 300.0, 250.0, 350.0)
        self.assertEqual(result["status"], "PASS")

    def test_visual_finding_in_band_passes(self):
        result = check_inspection_finding("visual", 0.0, 0.0, 1.0)
        self.assertEqual(result["status"], "PASS")

    def test_unrecognized_finding_type_raises(self):
        with self.assertRaises(ValueError):
            check_inspection_finding("ultrasonic", 10.0, 5.0, 15.0)

    def test_inverted_limits_raise(self):
        with self.assertRaises(ValueError):
            check_inspection_finding("dimensional", 10.0, 15.0, 5.0)


class TestCheckServiceLife(unittest.TestCase):

    def test_low_usage_is_in_service(self):
        result = check_service_life(400, 1000)
        self.assertEqual(result["status"], "IN_SERVICE")
        self.assertAlmostEqual(result["fraction_used"], 0.4)
        self.assertEqual(result["remaining_cycles"], 600)

    def test_at_near_limit_threshold_is_near_limit(self):
        result = check_service_life(900, 1000)
        self.assertEqual(result["status"], "NEAR_LIMIT")

    def test_above_near_limit_threshold_is_near_limit(self):
        result = check_service_life(950, 1000)
        self.assertEqual(result["status"], "NEAR_LIMIT")

    def test_beyond_design_life_is_expired(self):
        result = check_service_life(1050, 1000)
        self.assertEqual(result["status"], "EXPIRED")
        self.assertAlmostEqual(result["fraction_used"], 1.05)

    def test_zero_accumulated_cycles_is_in_service(self):
        result = check_service_life(0, 1000)
        self.assertEqual(result["status"], "IN_SERVICE")
        self.assertEqual(result["remaining_cycles"], 1000)

    def test_custom_near_limit_fraction_respected(self):
        result = check_service_life(800, 1000, life_fraction_limit=0.8)
        self.assertEqual(result["status"], "NEAR_LIMIT")

    def test_negative_accumulated_cycles_raises(self):
        with self.assertRaises(ValueError):
            check_service_life(-10, 1000)

    def test_invalid_zero_design_life_raises(self):
        with self.assertRaises(ValueError):
            check_service_life(100, 0)

    def test_invalid_life_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            check_service_life(500, 1000, life_fraction_limit=1.5)


if __name__ == "__main__":
    unittest.main()
