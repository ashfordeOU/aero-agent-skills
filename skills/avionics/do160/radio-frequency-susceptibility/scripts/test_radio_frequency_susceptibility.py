#!/usr/bin/env python3
"""Gate 3 contract test: DO-160 radio frequency susceptibility.

Exercises scripts/radio_frequency_susceptibility_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 (field
strength from amplifier power, gain, and distance; dB unit conversions;
power flux density; AM peak and average levels; calibration margins;
CS114 category current-limit steps; invalid inputs raise ValueError).

Anchors:
- vm_from_dbu_vm(120) = 1.0 V/m; dbu_vm_from_vm(1.0) = 120 dBuV/m
- amp_from_dbu_a(120) = 1.0 A; dbu_a_from_amp(1.0) = 120 dBuA
- watt_from_dbm(30) = 1.0 W; dbm_from_watt(1.0) = 30 dBm
- field_strength_from_power(100, 1, 10) = 5.4772 V/m
- power_for_field_strength(100, 2, 3) = 1500 W
- power_flux_density(100) = 26.5252 W/m2
- am_peak_field(100, 0.8) = 180 V/m; am_average_power(100, 0.8) = 132 W
- apply_margin_db(100, 6) = 398.107 W
- cs114_limit_dbu_a('J') = 135.7 dBuA
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import radio_frequency_susceptibility_logic as rfs  # noqa: E402


class DbuFieldConversionTest(unittest.TestCase):
    def test_anchor_120_dbu_vm_is_one_vm(self):
        self.assertAlmostEqual(rfs.vm_from_dbu_vm(120.0), 1.0, places=6)

    def test_anchor_one_vm_is_120_dbu_vm(self):
        self.assertAlmostEqual(rfs.dbu_vm_from_vm(1.0), 120.0, places=6)

    def test_round_trip_field(self):
        for e in (0.01, 0.1, 1.0, 5.4772, 100.0):
            self.assertAlmostEqual(rfs.vm_from_dbu_vm(rfs.dbu_vm_from_vm(e)), e, places=6)

    def test_100_vm_is_160_dbu_vm(self):
        self.assertAlmostEqual(rfs.dbu_vm_from_vm(100.0), 160.0, places=6)

    def test_invalid_field_raises(self):
        with self.assertRaises(ValueError):
            rfs.dbu_vm_from_vm(0)
        with self.assertRaises(ValueError):
            rfs.dbu_vm_from_vm(-1.0)


class DbuCurrentConversionTest(unittest.TestCase):
    def test_anchor_120_dbu_a_is_one_amp(self):
        self.assertAlmostEqual(rfs.amp_from_dbu_a(120.0), 1.0, places=6)

    def test_anchor_one_amp_is_120_dbu_a(self):
        self.assertAlmostEqual(rfs.dbu_a_from_amp(1.0), 120.0, places=6)

    def test_round_trip_current(self):
        for i in (1e-6, 0.001, 0.61, 1.0):
            self.assertAlmostEqual(rfs.amp_from_dbu_a(rfs.dbu_a_from_amp(i)), i, places=6)

    def test_invalid_current_raises(self):
        with self.assertRaises(ValueError):
            rfs.dbu_a_from_amp(0)
        with self.assertRaises(ValueError):
            rfs.dbu_a_from_amp(-0.5)


class DbmPowerConversionTest(unittest.TestCase):
    def test_anchor_30_dbm_is_one_watt(self):
        self.assertAlmostEqual(rfs.watt_from_dbm(30.0), 1.0, places=6)

    def test_anchor_one_watt_is_30_dbm(self):
        self.assertAlmostEqual(rfs.dbm_from_watt(1.0), 30.0, places=6)

    def test_round_trip_power(self):
        for p in (1e-3, 0.1, 1.0, 1500.0):
            self.assertAlmostEqual(rfs.watt_from_dbm(rfs.dbm_from_watt(p)), p, places=6)

    def test_invalid_power_raises(self):
        with self.assertRaises(ValueError):
            rfs.dbm_from_watt(0)
        with self.assertRaises(ValueError):
            rfs.dbm_from_watt(-2.0)


class AntennaGainTest(unittest.TestCase):
    def test_anchor_3_db_is_about_two_linear(self):
        self.assertAlmostEqual(rfs.gain_db_to_linear(3.0), 1.9953, places=3)

    def test_anchor_two_linear_is_about_three_db(self):
        self.assertAlmostEqual(rfs.gain_linear_to_db(2.0), 3.0103, places=3)

    def test_round_trip_gain(self):
        for g in (1.0, 2.0, 10.0):
            self.assertAlmostEqual(rfs.gain_db_to_linear(rfs.gain_linear_to_db(g)), g, places=6)

    def test_invalid_gain_raises(self):
        with self.assertRaises(ValueError):
            rfs.gain_linear_to_db(0)
        with self.assertRaises(ValueError):
            rfs.gain_linear_to_db(-1.0)


class FarFieldRelationTest(unittest.TestCase):
    def test_anchor_100w_10m_unity_gain(self):
        self.assertAlmostEqual(rfs.field_strength_from_power(100.0, 1.0, 10.0), 5.4772, places=3)

    def test_anchor_1500w_2x_gain_3m_is_100vm(self):
        self.assertAlmostEqual(rfs.field_strength_from_power(1500.0, 2.0, 3.0), 100.0, places=3)

    def test_power_round_trip(self):
        e = rfs.field_strength_from_power(250.0, 2.0, 5.0)
        p = rfs.power_for_field_strength(e, 2.0, 5.0)
        self.assertAlmostEqual(p, 250.0, places=3)

    def test_anchor_100vm_2x_gain_3m_needs_1500w(self):
        self.assertAlmostEqual(rfs.power_for_field_strength(100.0, 2.0, 3.0), 1500.0, places=1)

    def test_field_times_distance_invariant(self):
        p = 400.0
        g = 1.5
        e1 = rfs.field_strength_from_power(p, g, 3.0)
        e2 = rfs.field_strength_from_power(p, g, 6.0)
        self.assertAlmostEqual(e1 * 3.0, e2 * 6.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rfs.field_strength_from_power(-1.0, 1.0, 10.0)
        with self.assertRaises(ValueError):
            rfs.field_strength_from_power(100.0, -1.0, 10.0)
        with self.assertRaises(ValueError):
            rfs.field_strength_from_power(100.0, 1.0, 0)
        with self.assertRaises(ValueError):
            rfs.power_for_field_strength(100.0, 0, 3.0)
        with self.assertRaises(ValueError):
            rfs.power_for_field_strength(-1.0, 1.0, 3.0)
        with self.assertRaises(ValueError):
            rfs.power_for_field_strength(100.0, 1.0, 0)


class PowerFluxDensityTest(unittest.TestCase):
    def test_anchor_100vm_flux(self):
        self.assertAlmostEqual(rfs.power_flux_density(100.0), 26.5252, places=3)

    def test_anchor_flux_round_trip(self):
        s = rfs.power_flux_density(50.0)
        self.assertAlmostEqual(rfs.field_from_power_flux_density(s), 50.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rfs.power_flux_density(-1.0)
        with self.assertRaises(ValueError):
            rfs.field_from_power_flux_density(-1.0)


class AmplitudeModulationTest(unittest.TestCase):
    def test_anchor_80pct_peak(self):
        self.assertAlmostEqual(rfs.am_peak_field(100.0, 0.8), 180.0, places=6)

    def test_anchor_80pct_average_power(self):
        self.assertAlmostEqual(rfs.am_average_power(100.0, 0.8), 132.0, places=6)

    def test_unmodulated_peak_equals_carrier(self):
        self.assertAlmostEqual(rfs.am_peak_field(100.0, 0.0), 100.0, places=6)

    def test_full_depth_average_is_1p5x(self):
        self.assertAlmostEqual(rfs.am_average_power(100.0, 1.0), 150.0, places=6)

    def test_invalid_depth_raises(self):
        with self.assertRaises(ValueError):
            rfs.am_peak_field(100.0, 1.1)
        with self.assertRaises(ValueError):
            rfs.am_peak_field(100.0, -0.1)
        with self.assertRaises(ValueError):
            rfs.am_average_power(100.0, 1.5)
        with self.assertRaises(ValueError):
            rfs.am_average_power(-100.0, 0.5)


class CalibrationMarginTest(unittest.TestCase):
    def test_anchor_6db_power_margin(self):
        self.assertAlmostEqual(rfs.apply_margin_db(100.0, 6.0), 398.107, places=2)

    def test_anchor_6db_field_margin(self):
        self.assertAlmostEqual(rfs.field_with_margin_db(100.0, 6.0), 199.526, places=2)

    def test_zero_margin_is_identity(self):
        self.assertAlmostEqual(rfs.apply_margin_db(500.0, 0.0), 500.0, places=6)
        self.assertAlmostEqual(rfs.field_with_margin_db(50.0, 0.0), 50.0, places=6)

    def test_invalid_power_raises(self):
        with self.assertRaises(ValueError):
            rfs.apply_margin_db(-1.0, 6.0)
        with self.assertRaises(ValueError):
            rfs.field_with_margin_db(-1.0, 6.0)


class AmplifierBudgetTest(unittest.TestCase):
    def test_anchor_cable_loss_3db(self):
        self.assertAlmostEqual(rfs.amplifier_power_with_cable_loss(1500.0, 3.0), 2992.893, places=2)

    def test_anchor_full_budget_100vm_3m(self):
        p = rfs.required_amp_power_for_test(100.0, 3.0, 3.0, 3.0, 6.0)
        self.assertTrue(11500.0 <= p <= 12500.0)

    def test_zero_margin_budget_equals_ideal(self):
        # 0 dB gain (unity), no cable loss, no margin: the budget equals
        # the bare far-field power for 100 V/m at 3 m, 3000 W.
        p = rfs.required_amp_power_for_test(100.0, 3.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(p, 3000.0, places=1)

    def test_budget_grows_with_margin(self):
        plain = rfs.required_amp_power_for_test(100.0, 3.0, 0.0, 0.0, 0.0)
        margined = rfs.required_amp_power_for_test(100.0, 3.0, 0.0, 0.0, 6.0)
        self.assertGreater(margined, plain)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rfs.required_amp_power_for_test(100.0, 0, 3.0, 3.0, 6.0)
        with self.assertRaises(ValueError):
            rfs.amplifier_power_with_cable_loss(-1.0, 3.0)


class Cs114CategoryTest(unittest.TestCase):
    def test_anchor_category_a_offset(self):
        self.assertAlmostEqual(rfs.cs114_category_offset("A"), 0.0)

    def test_anchor_category_j_offset(self):
        self.assertAlmostEqual(rfs.cs114_category_offset("J"), 80.0)

    def test_case_insensitive_category(self):
        self.assertAlmostEqual(rfs.cs114_category_offset("e"), 40.0)

    def test_category_step_is_ten_dbu_a(self):
        # Adjacent published categories (A through H, then J) step by
        # 10 dBuA; the set skips the letter I.
        for cat in ("A", "B", "C", "D", "E", "F", "G", "H"):
            self.assertAlmostEqual(rfs.cs114_category_offset(cat), 10.0 * (ord(cat) - ord("A")))
        self.assertAlmostEqual(rfs.cs114_category_offset("J"), 80.0)

    def test_anchor_category_j_limit(self):
        self.assertAlmostEqual(rfs.cs114_limit_dbu_a("J"), 135.7, places=6)

    def test_anchor_category_a_limit(self):
        self.assertAlmostEqual(rfs.cs114_limit_dbu_a("A"), 55.7, places=6)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            rfs.cs114_category_offset("K")
        with self.assertRaises(ValueError):
            rfs.cs114_category_offset("Z")


class MarginVerdictTest(unittest.TestCase):
    def test_pass_verdict_positive_margin(self):
        margin, verdict = rfs.margin_check_dbu(50.0, 55.7)
        self.assertAlmostEqual(margin, 5.7, places=6)
        self.assertTrue(verdict)

    def test_fail_verdict_negative_margin(self):
        margin, verdict = rfs.margin_check_dbu(60.0, 55.7)
        self.assertAlmostEqual(margin, -4.3, places=6)
        self.assertFalse(verdict)

    def test_exact_limit_is_pass(self):
        margin, verdict = rfs.margin_check_dbu(55.7, 55.7)
        self.assertAlmostEqual(margin, 0.0, places=6)
        self.assertTrue(verdict)


class FrequencyBandTest(unittest.TestCase):
    def test_in_band_includes_low_edge(self):
        self.assertTrue(rfs.in_frequency_band(1e8, 1e8, 18e9))

    def test_below_band_is_out(self):
        self.assertFalse(rfs.in_frequency_band(1e7, 1e8, 18e9))

    def test_high_edge_excluded(self):
        self.assertFalse(rfs.in_frequency_band(18e9, 1e8, 18e9))

    def test_mid_band_is_in(self):
        self.assertTrue(rfs.in_frequency_band(1e9, 1e8, 18e9))


class WavelengthAndFarFieldTest(unittest.TestCase):
    def test_anchor_wavelength_1ghz(self):
        self.assertAlmostEqual(rfs.wavelength_from_frequency(1e9), 0.299792458, places=6)

    def test_anchor_wavelength_100mhz(self):
        self.assertAlmostEqual(rfs.wavelength_from_frequency(100e6), 2.99792458, places=6)

    def test_higher_frequency_shorter_wavelength(self):
        hi = rfs.wavelength_from_frequency(10e9)
        lo = rfs.wavelength_from_frequency(1e9)
        self.assertLess(hi, lo)

    def test_anchor_far_field_boundary(self):
        self.assertAlmostEqual(rfs.far_field_boundary(1.0, 0.3), 6.6667, places=3)

    def test_far_field_boundary_grows_with_aperture(self):
        big = rfs.far_field_boundary(2.0, 0.3)
        small = rfs.far_field_boundary(1.0, 0.3)
        self.assertGreater(big, small)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rfs.wavelength_from_frequency(0)
        with self.assertRaises(ValueError):
            rfs.wavelength_from_frequency(-1e9)
        with self.assertRaises(ValueError):
            rfs.far_field_boundary(-1.0, 0.3)
        with self.assertRaises(ValueError):
            rfs.far_field_boundary(1.0, 0)


class Rs103ScenarioTest(unittest.TestCase):
    def test_100vm_setup_budget(self):
        # 100 V/m at 3 m with a 3 dB gain antenna, 3 dB cable loss, and
        # a 6 dB calibration margin. The budget must cover the ideal
        # 1500 W far-field power by the loss and margin factors.
        budget = rfs.required_amp_power_for_test(100.0, 3.0, 3.0, 3.0, 6.0)
        ideal = rfs.power_for_field_strength(100.0, 2.0, 3.0)
        self.assertGreater(budget, ideal * 7.0)
        self.assertLess(budget, ideal * 8.0)

    def test_measured_current_against_category_j(self):
        # A measured 90 dBuA on the harness with a category J limit of
        # 135.7 dBuA leaves 45.7 dB of conducted immunity margin.
        margin, verdict = rfs.margin_check_dbu(90.0, rfs.cs114_limit_dbu_a("J"))
        self.assertAlmostEqual(margin, 45.7, places=6)
        self.assertTrue(verdict)

    def test_modulated_field_exceeds_continuous_level(self):
        # The AM-modulated RS103 field peaks above the unmodulated
        # calibration level; the peak drives receiver desensitization.
        peak = rfs.am_peak_field(100.0, 0.8)
        self.assertGreater(peak, 100.0)
        self.assertAlmostEqual(peak, 180.0, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
