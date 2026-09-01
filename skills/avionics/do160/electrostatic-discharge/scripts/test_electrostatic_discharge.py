#!/usr/bin/env python3
"""Gate 3 contract test: DO-160 Section 25 electrostatic discharge.

Exercises scripts/electrostatic_discharge_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - category A
single-level check (15 kV air discharge), stored energy and discharge
waveform currents from the 150 pF / 330 ohm generator model, rise time
window 0.7-1.0 ns, 10 positive and 10 negative discharges per test
point, test point applicability from personnel accessibility with
connector pins excluded, and the pass verdict over operation and
permanent degradation; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import electrostatic_discharge_logic as esd  # noqa: E402


class CategoryLevelTest(unittest.TestCase):
    def test_category_a_level(self):
        self.assertEqual(esd.category_test_level_kv("A"), 15.0)

    def test_category_a_lowercase(self):
        self.assertEqual(esd.category_test_level_kv("a"), 15.0)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            esd.category_test_level_kv("B")

    def test_non_string_category_raises(self):
        with self.assertRaises(ValueError):
            esd.category_test_level_kv(5)


class StoredEnergyTest(unittest.TestCase):
    def test_anchor_150pf_15kv(self):
        self.assertAlmostEqual(esd.stored_energy_joules(150.0, 15.0), 0.016875, places=6)

    def test_anchor_150pf_8kv(self):
        self.assertAlmostEqual(esd.stored_energy_joules(150.0, 8.0), 0.0048, places=6)

    def test_energy_scales_with_voltage_squared(self):
        e4 = esd.stored_energy_joules(150.0, 4.0)
        e8 = esd.stored_energy_joules(150.0, 8.0)
        self.assertAlmostEqual(e8, 4.0 * e4, places=9)

    def test_zero_voltage_zero_energy(self):
        self.assertEqual(esd.stored_energy_joules(150.0, 0.0), 0.0)

    def test_negative_capacitance_raises(self):
        with self.assertRaises(ValueError):
            esd.stored_energy_joules(-150.0, 15.0)

    def test_negative_voltage_raises(self):
        with self.assertRaises(ValueError):
            esd.stored_energy_joules(150.0, -15.0)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            esd.stored_energy_joules("150", 15.0)


class PeakCurrentTest(unittest.TestCase):
    def test_anchor_15kv(self):
        self.assertAlmostEqual(esd.peak_current_amps(15.0), 56.25, places=4)

    def test_anchor_2kv(self):
        self.assertAlmostEqual(esd.peak_current_amps(2.0), 7.5, places=4)

    def test_peak_scales_linearly(self):
        self.assertAlmostEqual(esd.peak_current_amps(8.0), 30.0, places=4)

    def test_non_positive_voltage_raises(self):
        with self.assertRaises(ValueError):
            esd.peak_current_amps(0.0)
        with self.assertRaises(ValueError):
            esd.peak_current_amps(-2.0)


class CurrentAtTimeTest(unittest.TestCase):
    def test_current_30ns_anchor(self):
        self.assertAlmostEqual(esd.current_at_30ns_amps(15.0), 30.0, places=4)

    def test_current_60ns_anchor(self):
        self.assertAlmostEqual(esd.current_at_60ns_amps(15.0), 15.0, places=4)

    def test_30ns_is_twice_60ns(self):
        self.assertAlmostEqual(
            esd.current_at_30ns_amps(15.0), 2.0 * esd.current_at_60ns_amps(15.0), places=4
        )

    def test_30ns_non_positive_raises(self):
        with self.assertRaises(ValueError):
            esd.current_at_30ns_amps(0.0)

    def test_60ns_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            esd.current_at_60ns_amps("15")


class RiseTimeTest(unittest.TestCase):
    def test_within_window(self):
        self.assertTrue(esd.rise_time_valid_ns(0.8))

    def test_edges_valid(self):
        self.assertTrue(esd.rise_time_valid_ns(0.7))
        self.assertTrue(esd.rise_time_valid_ns(1.0))

    def test_below_window(self):
        self.assertFalse(esd.rise_time_valid_ns(0.5))

    def test_above_window(self):
        self.assertFalse(esd.rise_time_valid_ns(1.2))

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            esd.rise_time_valid_ns("fast")


class RcTimeConstantTest(unittest.TestCase):
    def test_anchor_330_150(self):
        self.assertAlmostEqual(esd.rc_time_constant_ns(330.0, 150.0), 49.5, places=4)

    def test_zero_resistance_raises(self):
        with self.assertRaises(ValueError):
            esd.rc_time_constant_ns(0.0, 150.0)

    def test_negative_capacitance_raises(self):
        with self.assertRaises(ValueError):
            esd.rc_time_constant_ns(330.0, -1.0)


class DischargeCountTest(unittest.TestCase):
    def test_minimum_counts_valid(self):
        self.assertTrue(esd.discharge_count_valid(10, 10))

    def test_above_minimum_valid(self):
        self.assertTrue(esd.discharge_count_valid(25, 25))

    def test_short_positive_invalid(self):
        self.assertFalse(esd.discharge_count_valid(9, 10))

    def test_short_negative_invalid(self):
        self.assertFalse(esd.discharge_count_valid(10, 9))

    def test_zero_invalid(self):
        self.assertFalse(esd.discharge_count_valid(0, 0))

    def test_float_raises(self):
        with self.assertRaises(ValueError):
            esd.discharge_count_valid(10.0, 10)

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            esd.discharge_count_valid(-1, 10)


class TestPointApplicabilityTest(unittest.TestCase):
    def test_normal_operation_surface(self):
        self.assertTrue(esd.test_point_applicable(True, False, False))

    def test_maintenance_surface(self):
        self.assertTrue(esd.test_point_applicable(False, True, False))

    def test_inaccessible_surface(self):
        self.assertFalse(esd.test_point_applicable(False, False, False))

    def test_connector_pin_excluded(self):
        self.assertFalse(esd.test_point_applicable(True, False, True))

    def test_connector_pin_excluded_under_maintenance(self):
        self.assertFalse(esd.test_point_applicable(False, True, True))

    def test_non_bool_raises(self):
        with self.assertRaises(ValueError):
            esd.test_point_applicable("yes", False, False)


class PassVerdictTest(unittest.TestCase):
    def test_clean_pass(self):
        self.assertTrue(esd.pass_verdict(True, True))

    def test_operation_failure_fails(self):
        self.assertFalse(esd.pass_verdict(False, True))

    def test_degradation_fails(self):
        self.assertFalse(esd.pass_verdict(True, False))

    def test_both_fail(self):
        self.assertFalse(esd.pass_verdict(False, False))

    def test_non_bool_raises(self):
        with self.assertRaises(ValueError):
            esd.pass_verdict(1, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
