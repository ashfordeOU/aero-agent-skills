#!/usr/bin/env python3
"""Offline stdlib unittest for microvibration_analysis_logic.py.

ECSS-E-ST-32C clause 4.6.2.21 micro-vibration analysis.
Run: python3 test_microvibration_analysis.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import microvibration_analysis_logic as mv


class TestCategorizeSource(unittest.TestCase):

    def test_reaction_wheel_is_rotating(self):
        self.assertEqual(mv.categorize_source("reaction_wheel"), "rotating")

    def test_cryocooler_is_rotating(self):
        self.assertEqual(mv.categorize_source("cryocooler"), "rotating")

    def test_solar_array_drive_is_periodic(self):
        self.assertEqual(
            mv.categorize_source("solar_array_drive"), "periodic_low_frequency"
        )

    def test_thruster_valve_is_impulsive(self):
        self.assertEqual(mv.categorize_source("thruster_valve"), "impulsive")

    def test_unrecognized_source_raises(self):
        with self.assertRaises(ValueError):
            mv.categorize_source("unknown_device")


class TestComputeHarmonicFrequencies(unittest.TestCase):

    def test_reaction_wheel_harmonics_at_10hz(self):
        freqs = mv.compute_harmonic_frequencies("reaction_wheel", 10.0)
        # orders: 1, 2, 3, 4, 6, 8
        self.assertEqual(freqs, [10.0, 20.0, 30.0, 40.0, 60.0, 80.0])

    def test_cryocooler_harmonics_at_50hz(self):
        freqs = mv.compute_harmonic_frequencies("cryocooler", 50.0)
        # orders: 1, 2, 3
        self.assertEqual(freqs, [50.0, 100.0, 150.0])

    def test_solar_array_drive_returns_fundamental_only(self):
        freqs = mv.compute_harmonic_frequencies("solar_array_drive", 0.1)
        self.assertEqual(len(freqs), 1)
        self.assertAlmostEqual(freqs[0], 0.1, places=5)

    def test_impulsive_source_raises(self):
        with self.assertRaises(ValueError):
            mv.compute_harmonic_frequencies("thruster_valve", 5.0)

    def test_nonpositive_spin_freq_raises(self):
        with self.assertRaises(ValueError):
            mv.compute_harmonic_frequencies("reaction_wheel", 0.0)

    def test_negative_spin_freq_raises(self):
        with self.assertRaises(ValueError):
            mv.compute_harmonic_frequencies("pump", -1.0)


class TestComputeTransmissibility(unittest.TestCase):

    def test_below_isolation_freq_returns_unity(self):
        t = mv.compute_transmissibility(5.0, 10.0)
        self.assertAlmostEqual(t, 1.0)

    def test_at_isolation_freq_returns_unity(self):
        t = mv.compute_transmissibility(10.0, 10.0)
        self.assertAlmostEqual(t, 1.0)

    def test_above_isolation_freq_rolls_off(self):
        # T = (10/20)^2 = 0.25
        t = mv.compute_transmissibility(20.0, 10.0)
        self.assertAlmostEqual(t, 0.25)

    def test_high_frequency_deep_rolloff(self):
        # T = (5/50)^2 = 0.01
        t = mv.compute_transmissibility(50.0, 5.0)
        self.assertAlmostEqual(t, 0.01)

    def test_zero_freq_raises(self):
        with self.assertRaises(ValueError):
            mv.compute_transmissibility(0.0, 10.0)

    def test_zero_isolation_freq_raises(self):
        with self.assertRaises(ValueError):
            mv.compute_transmissibility(10.0, 0.0)


class TestCheckFrequencyBandOverlap(unittest.TestCase):

    def test_single_harmonic_in_band(self):
        result = mv.check_frequency_band_overlap([10.0, 20.0, 30.0], 15.0, 25.0)
        self.assertEqual(result, [20.0])

    def test_no_harmonic_in_band(self):
        result = mv.check_frequency_band_overlap([5.0, 50.0, 100.0], 10.0, 40.0)
        self.assertEqual(result, [])

    def test_multiple_harmonics_in_band(self):
        result = mv.check_frequency_band_overlap(
            [10.0, 20.0, 30.0, 40.0], 15.0, 45.0
        )
        self.assertEqual(result, [20.0, 30.0, 40.0])

    def test_boundary_frequencies_included(self):
        result = mv.check_frequency_band_overlap([10.0, 30.0], 10.0, 30.0)
        self.assertEqual(result, [10.0, 30.0])

    def test_invalid_band_raises(self):
        with self.assertRaises(ValueError):
            mv.check_frequency_band_overlap([10.0], 30.0, 10.0)


class TestComputeInducedAmplitude(unittest.TestCase):

    def test_unity_transmissibility(self):
        self.assertAlmostEqual(mv.compute_induced_amplitude(5.0, 1.0), 5.0)

    def test_attenuated_amplitude(self):
        self.assertAlmostEqual(mv.compute_induced_amplitude(4.0, 0.25), 1.0)

    def test_zero_source_amplitude(self):
        self.assertAlmostEqual(mv.compute_induced_amplitude(0.0, 0.5), 0.0)

    def test_negative_source_amplitude_raises(self):
        with self.assertRaises(ValueError):
            mv.compute_induced_amplitude(-1.0, 0.5)


class TestAssessSourceAtInstrument(unittest.TestCase):

    def test_no_in_band_harmonic_is_compliant(self):
        result = mv.assess_source_at_instrument(
            source_type="reaction_wheel",
            spin_freq_hz=10.0,
            source_amplitude=1.0,
            isolation_freq_hz=5.0,
            instrument_band_hz=(200.0, 300.0),
            instrument_allowable=0.5,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["finding"], mv.NO_IN_BAND_HARMONIC)
        self.assertEqual(result["in_band_freqs"], [])

    def test_in_band_harmonic_within_allowable(self):
        # reaction_wheel at 5 Hz, 3rd harmonic = 15 Hz; band 10–20 Hz
        # isolation at 100 Hz => T = 1.0 for all harmonics
        # induced = 0.1 * 1.0 = 0.1 <= 0.5 allowable => compliant
        result = mv.assess_source_at_instrument(
            source_type="reaction_wheel",
            spin_freq_hz=5.0,
            source_amplitude=0.1,
            isolation_freq_hz=100.0,
            instrument_band_hz=(10.0, 20.0),
            instrument_allowable=0.5,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["finding"], "within_allowable")
        self.assertIn(15.0, result["in_band_freqs"])

    def test_in_band_harmonic_exceeds_allowable(self):
        # reaction_wheel at 10 Hz; 1st harmonic = 10 Hz in band 5–15 Hz
        # isolation at 100 Hz => T = 1.0; induced = 2.0 > 0.5 => exceedance
        result = mv.assess_source_at_instrument(
            source_type="reaction_wheel",
            spin_freq_hz=10.0,
            source_amplitude=2.0,
            isolation_freq_hz=100.0,
            instrument_band_hz=(5.0, 15.0),
            instrument_allowable=0.5,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(result["exceeds_allowable"])
        self.assertEqual(result["finding"], "exceedance")

    def test_missing_allowable_is_finding(self):
        # in-band harmonic exists but no allowable => missing_allowable finding
        result = mv.assess_source_at_instrument(
            source_type="cryocooler",
            spin_freq_hz=50.0,
            source_amplitude=0.05,
            isolation_freq_hz=200.0,
            instrument_band_hz=(40.0, 60.0),
            instrument_allowable=None,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(result["missing_allowable"])
        self.assertEqual(result["finding"], "missing_instrument_allowable")

    def test_impulsive_source_raises(self):
        with self.assertRaises(ValueError):
            mv.assess_source_at_instrument(
                source_type="thruster_valve",
                spin_freq_hz=1.0,
                source_amplitude=1.0,
                isolation_freq_hz=10.0,
                instrument_band_hz=(1.0, 100.0),
                instrument_allowable=0.1,
            )

    def test_isolation_rolloff_reduces_induced_amplitude(self):
        # reaction_wheel at 5 Hz; 1st harmonic = 5 Hz in band 4–6 Hz
        # isolation_freq = 5 Hz => T(5) = 1.0
        # 2nd harmonic = 10 Hz in band? No, band is 4–6 Hz so only 5 Hz in band
        # source_amplitude = 2.0, T = 1.0, induced = 2.0 vs allowable 3.0 => compliant
        result = mv.assess_source_at_instrument(
            source_type="reaction_wheel",
            spin_freq_hz=5.0,
            source_amplitude=2.0,
            isolation_freq_hz=5.0,
            instrument_band_hz=(4.0, 6.0),
            instrument_allowable=3.0,
        )
        self.assertTrue(result["compliant"])

    def test_high_frequency_harmonic_attenuated_by_isolation(self):
        # reaction_wheel at 5 Hz; harmonics 5,10,15,20,30,40 Hz; band 35–45 Hz
        # 40 Hz in band; isolation_freq = 10 Hz => T(40) = (10/40)^2 = 0.0625
        # induced = 8.0 * 0.0625 = 0.5 <= 1.0 allowable => compliant
        result = mv.assess_source_at_instrument(
            source_type="reaction_wheel",
            spin_freq_hz=5.0,
            source_amplitude=8.0,
            isolation_freq_hz=10.0,
            instrument_band_hz=(35.0, 45.0),
            instrument_allowable=1.0,
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["worst_transmissibility"], 0.0625)
        self.assertAlmostEqual(result["worst_induced_amplitude"], 0.5)


class TestAggregateInstrumentFindings(unittest.TestCase):

    def test_all_compliant(self):
        findings = [
            {"compliant": True, "finding": "within_allowable"},
            {"compliant": True, "finding": mv.NO_IN_BAND_HARMONIC},
        ]
        summary = mv.aggregate_instrument_findings("CAM_1", findings)
        self.assertTrue(summary["overall_compliant"])
        self.assertEqual(summary["non_compliant_findings"], [])
        self.assertEqual(summary["total_sources_assessed"], 2)

    def test_one_non_compliant(self):
        findings = [
            {"compliant": True, "finding": "within_allowable"},
            {"compliant": False, "finding": "exceedance"},
        ]
        summary = mv.aggregate_instrument_findings("STR_2", findings)
        self.assertFalse(summary["overall_compliant"])
        self.assertEqual(len(summary["non_compliant_findings"]), 1)
        self.assertEqual(summary["instrument_id"], "STR_2")

    def test_empty_assessments(self):
        summary = mv.aggregate_instrument_findings("OPT_3", [])
        self.assertTrue(summary["overall_compliant"])
        self.assertEqual(summary["total_sources_assessed"], 0)


if __name__ == "__main__":
    unittest.main()
