"""
Gate 3 contract tests for acoustic_analysis_logic.py.

stdlib unittest only — deterministic, offline, no network.
Run: python3 test_acoustic_analysis.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from acoustic_analysis_logic import (
    REFERENCE_PRESSURE_PA,
    aggregate_findings,
    categorize_frequency_regime,
    check_acoustic_fatigue_risk,
    check_diffuse_field,
    compute_acoustic_force,
    compute_margin_of_safety,
    compute_oaspl,
    compute_radiation_efficiency,
    compute_third_octave_center_frequency,
    pressure_to_spl,
    spl_to_pressure,
)


class TestSplPressureConversion(unittest.TestCase):
    def test_zero_db_equals_reference_pressure(self):
        """0 dB SPL must return the reference pressure (20 µPa)."""
        result = spl_to_pressure(0.0)
        self.assertAlmostEqual(result, REFERENCE_PRESSURE_PA, places=12)

    def test_spl_to_pressure_known_value(self):
        """120 dB SPL → 20 Pa (a well-known calibration point)."""
        result = spl_to_pressure(120.0)
        self.assertAlmostEqual(result, 20.0, places=8)

    def test_pressure_to_spl_known_value(self):
        """20 Pa → 120 dB SPL."""
        result = pressure_to_spl(20.0)
        self.assertAlmostEqual(result, 120.0, places=8)

    def test_roundtrip_spl_pressure(self):
        """Converting SPL → pressure → SPL must recover the original value."""
        original_spl = 140.0
        recovered = pressure_to_spl(spl_to_pressure(original_spl))
        self.assertAlmostEqual(recovered, original_spl, places=10)

    def test_pressure_to_spl_rejects_zero(self):
        with self.assertRaises(ValueError):
            pressure_to_spl(0.0)

    def test_pressure_to_spl_rejects_negative(self):
        with self.assertRaises(ValueError):
            pressure_to_spl(-1.0)


class TestOaspl(unittest.TestCase):
    def test_two_equal_bands_adds_3db(self):
        """Two bands at the same SPL combine to SPL + 3.01 dB."""
        spl = 100.0
        result = compute_oaspl([spl, spl])
        self.assertAlmostEqual(result, spl + 10.0 * math.log10(2.0), places=8)

    def test_single_band_returns_itself(self):
        """A single-band spectrum must return the band level unchanged."""
        result = compute_oaspl([115.0])
        self.assertAlmostEqual(result, 115.0, places=10)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            compute_oaspl([])

    def test_oaspl_dominated_by_highest_band(self):
        """Adding a band 20 dB below the dominant band barely changes OASPL."""
        dominant = 140.0
        result = compute_oaspl([dominant, dominant - 20.0])
        self.assertLess(abs(result - dominant), 0.5)


class TestFrequencyRegime(unittest.TestCase):
    def test_low_frequency_below_200(self):
        self.assertEqual(categorize_frequency_regime(50.0), "low")

    def test_high_frequency_above_200(self):
        self.assertEqual(categorize_frequency_regime(500.0), "high")

    def test_boundary_200hz_is_high(self):
        self.assertEqual(categorize_frequency_regime(200.0), "high")

    def test_rejects_zero_frequency(self):
        with self.assertRaises(ValueError):
            categorize_frequency_regime(0.0)

    def test_rejects_negative_frequency(self):
        with self.assertRaises(ValueError):
            categorize_frequency_regime(-10.0)


class TestAcousticForce(unittest.TestCase):
    def test_force_is_pressure_times_area(self):
        """Acoustic force = p_rms × panel_area."""
        spl_db = 120.0
        area = 0.5
        expected = spl_to_pressure(spl_db) * area
        self.assertAlmostEqual(compute_acoustic_force(spl_db, area), expected, places=10)

    def test_rejects_zero_area(self):
        with self.assertRaises(ValueError):
            compute_acoustic_force(120.0, 0.0)

    def test_rejects_negative_area(self):
        with self.assertRaises(ValueError):
            compute_acoustic_force(120.0, -1.0)


class TestMarginOfSafety(unittest.TestCase):
    def test_positive_margin_when_allowable_exceeds_response(self):
        ms = compute_margin_of_safety(allowable=200.0, response=100.0)
        self.assertAlmostEqual(ms, 1.0, places=10)

    def test_zero_margin_when_equal(self):
        ms = compute_margin_of_safety(allowable=150.0, response=150.0)
        self.assertAlmostEqual(ms, 0.0, places=10)

    def test_negative_margin_when_response_exceeds_allowable(self):
        ms = compute_margin_of_safety(allowable=80.0, response=100.0)
        self.assertLess(ms, 0.0)

    def test_rejects_zero_response(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, 0.0)

    def test_rejects_zero_allowable(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 100.0)


class TestDiffuseField(unittest.TestCase):
    def test_valid_diffuse_field_above_schroeder(self):
        """High analysis frequency in a large volume → diffuse field holds."""
        result = check_diffuse_field(
            frequency_hz=500.0, reverb_time_s=1.0, volume_m3=1000.0
        )
        self.assertTrue(result["diffuse_field_valid"])

    def test_invalid_below_schroeder(self):
        """Low frequency in a small room → diffuse field does not hold."""
        result = check_diffuse_field(
            frequency_hz=10.0, reverb_time_s=2.0, volume_m3=50.0
        )
        self.assertFalse(result["diffuse_field_valid"])

    def test_schroeder_formula(self):
        """Schroeder frequency = 2000 × √(T60 / V)."""
        t60, vol = 2.0, 200.0
        expected = 2000.0 * math.sqrt(t60 / vol)
        result = check_diffuse_field(1000.0, t60, vol)
        self.assertAlmostEqual(result["schroeder_frequency_hz"], expected, places=8)

    def test_rejects_nonpositive_volume(self):
        with self.assertRaises(ValueError):
            check_diffuse_field(100.0, 1.0, 0.0)


class TestRadiationEfficiency(unittest.TestCase):
    def test_unity_at_critical_frequency(self):
        sigma = compute_radiation_efficiency(1000.0, 1000.0)
        self.assertAlmostEqual(sigma, 1.0, places=10)

    def test_unity_above_critical_frequency(self):
        sigma = compute_radiation_efficiency(2000.0, 1000.0)
        self.assertAlmostEqual(sigma, 1.0, places=10)

    def test_less_than_unity_below_critical(self):
        sigma = compute_radiation_efficiency(250.0, 1000.0)
        self.assertLess(sigma, 1.0)
        self.assertAlmostEqual(sigma, math.sqrt(250.0 / 1000.0), places=10)

    def test_rejects_zero_critical_frequency(self):
        with self.assertRaises(ValueError):
            compute_radiation_efficiency(100.0, 0.0)


class TestThirdOctaveCenterFrequency(unittest.TestCase):
    def test_band_30_is_1000hz(self):
        """Band number 30 must return exactly 1000 Hz."""
        result = compute_third_octave_center_frequency(30)
        self.assertAlmostEqual(result, 1000.0, places=8)

    def test_band_33_is_2000hz(self):
        """Band 33 = 2000 Hz (three bands above 1000 Hz = one octave)."""
        result = compute_third_octave_center_frequency(33)
        self.assertAlmostEqual(result, 2000.0, places=6)

    def test_rejects_float_band_number(self):
        with self.assertRaises(TypeError):
            compute_third_octave_center_frequency(30.5)


class TestAcousticFatigueRisk(unittest.TestCase):
    def test_risk_flagged_when_both_conditions_met(self):
        result = check_acoustic_fatigue_risk(
            oaspl_db=145.0, exposure_duration_s=120.0
        )
        self.assertTrue(result["acoustic_fatigue_risk"])

    def test_no_risk_when_level_below_threshold(self):
        result = check_acoustic_fatigue_risk(
            oaspl_db=130.0, exposure_duration_s=120.0
        )
        self.assertFalse(result["acoustic_fatigue_risk"])

    def test_no_risk_when_duration_below_60s(self):
        result = check_acoustic_fatigue_risk(
            oaspl_db=145.0, exposure_duration_s=10.0
        )
        self.assertFalse(result["acoustic_fatigue_risk"])

    def test_boundary_exactly_60s_is_long_exposure(self):
        result = check_acoustic_fatigue_risk(
            oaspl_db=145.0, exposure_duration_s=60.0
        )
        self.assertTrue(result["long_exposure"])

    def test_custom_threshold_respected(self):
        result = check_acoustic_fatigue_risk(
            oaspl_db=135.0, exposure_duration_s=120.0, threshold_db=135.0
        )
        self.assertTrue(result["acoustic_fatigue_risk"])

    def test_rejects_negative_duration(self):
        with self.assertRaises(ValueError):
            check_acoustic_fatigue_risk(140.0, -1.0)


class TestAggregateFindings(unittest.TestCase):
    def test_all_compliant(self):
        findings = [
            {"surface_id": "P1", "compliant": True},
            {"surface_id": "P2", "compliant": True},
        ]
        result = aggregate_findings(findings)
        self.assertTrue(result["all_compliant"])
        self.assertEqual(result["compliant_count"], 2)
        self.assertEqual(result["non_compliant_surfaces"], [])

    def test_partial_non_compliance(self):
        findings = [
            {"surface_id": "P1", "compliant": True},
            {"surface_id": "P2", "compliant": False},
            {"surface_id": "P3", "compliant": False},
        ]
        result = aggregate_findings(findings)
        self.assertFalse(result["all_compliant"])
        self.assertEqual(result["compliant_count"], 1)
        self.assertIn("P2", result["non_compliant_surfaces"])
        self.assertIn("P3", result["non_compliant_surfaces"])

    def test_empty_list_returns_all_compliant(self):
        result = aggregate_findings([])
        self.assertTrue(result["all_compliant"])
        self.assertEqual(result["total_surfaces"], 0)

    def test_missing_surface_id_raises(self):
        with self.assertRaises(ValueError):
            aggregate_findings([{"compliant": True}])

    def test_missing_compliant_raises(self):
        with self.assertRaises(ValueError):
            aggregate_findings([{"surface_id": "P1"}])

    def test_non_list_input_raises(self):
        with self.assertRaises(TypeError):
            aggregate_findings("not-a-list")


if __name__ == "__main__":
    unittest.main()
