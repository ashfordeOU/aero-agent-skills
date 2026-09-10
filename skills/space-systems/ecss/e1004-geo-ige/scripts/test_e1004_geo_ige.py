#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.2 GEO trapped
environment via IGE-2006.

Exercises scripts/e1004_geo_ige_logic.py (stdlib unittest, offline).
Contract: an orbit L-shell is only accepted near the fixed GEO value
(L ~= 6.6, within tolerance) and rejected otherwise; a magnetic local
time categorizes into exactly one of midnight/dawn/noon/dusk with
circular wraparound at 24h; differential flux interpolates linearly
in local time (circular) against log10(flux) and log-log in energy,
scaled by a percentile multiplier, and raises for a non-positive
energy or an unrecognized percentile; a dwell-weighted local-time
spectrum and mission fluence require at least one dwell segment and
non-negative dwell durations; total fluence categorizes into a
benign/elevated/severe severity band and raises for a negative value.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_geo_ige_logic as ige  # noqa: E402


class ValidateGeoLShellTest(unittest.TestCase):
    def test_exact_geo_l_shell_accepted(self):
        ige.validate_geo_l_shell(6.6)  # should not raise

    def test_within_tolerance_accepted(self):
        ige.validate_geo_l_shell(6.3)
        ige.validate_geo_l_shell(6.9)

    def test_outside_tolerance_raises(self):
        with self.assertRaises(ValueError):
            ige.validate_geo_l_shell(6.95)

    def test_meo_l_shell_raises(self):
        with self.assertRaises(ValueError):
            ige.validate_geo_l_shell(3.0)

    def test_leo_l_shell_raises(self):
        with self.assertRaises(ValueError):
            ige.validate_geo_l_shell(1.2)


class ClassifyLocalTimeSectorTest(unittest.TestCase):
    def test_midnight_start(self):
        self.assertEqual(ige.classify_local_time_sector(0.0), "midnight")

    def test_midnight_just_before_dawn(self):
        self.assertEqual(ige.classify_local_time_sector(2.9), "midnight")

    def test_dawn_start(self):
        self.assertEqual(ige.classify_local_time_sector(3.0), "dawn")

    def test_dawn_just_before_noon(self):
        self.assertEqual(ige.classify_local_time_sector(8.9), "dawn")

    def test_noon_start(self):
        self.assertEqual(ige.classify_local_time_sector(9.0), "noon")

    def test_noon_just_before_dusk(self):
        self.assertEqual(ige.classify_local_time_sector(14.9), "noon")

    def test_dusk_start(self):
        self.assertEqual(ige.classify_local_time_sector(15.0), "dusk")

    def test_dusk_just_before_midnight(self):
        self.assertEqual(ige.classify_local_time_sector(20.9), "dusk")

    def test_midnight_wraps_at_21(self):
        self.assertEqual(ige.classify_local_time_sector(21.0), "midnight")

    def test_midnight_wraps_past_24(self):
        self.assertEqual(ige.classify_local_time_sector(24.5), "midnight")

    def test_negative_local_time_wraps(self):
        self.assertEqual(ige.classify_local_time_sector(-1.0), "midnight")


class InterpolateFluxTest(unittest.TestCase):
    def test_unknown_percentile_raises(self):
        with self.assertRaises(ValueError):
            ige.interpolate_flux(0.0, 1.0, percentile="p50")

    def test_nonpositive_energy_raises(self):
        with self.assertRaises(ValueError):
            ige.interpolate_flux(0.0, 0.0)
        with self.assertRaises(ValueError):
            ige.interpolate_flux(0.0, -1.0)

    def test_exact_grid_point_matches_table(self):
        # LT=3h (index 1), energy=1.0 MeV (index 2) -> table value 4.5.
        flux = ige.interpolate_flux(3.0, 1.0, percentile="mean")
        self.assertAlmostEqual(flux, 10.0**4.5)

    def test_percentile_scales_linearly(self):
        mean_flux = ige.interpolate_flux(3.0, 1.0, percentile="mean")
        p90_flux = ige.interpolate_flux(3.0, 1.0, percentile="p90")
        self.assertAlmostEqual(p90_flux, mean_flux * 3.0)

    def test_local_time_wraps_at_24(self):
        flux_0 = ige.interpolate_flux(0.0, 1.0)
        flux_24 = ige.interpolate_flux(24.0, 1.0)
        self.assertAlmostEqual(flux_0, flux_24)

    def test_negative_local_time_wraps_to_equivalent(self):
        flux_neg = ige.interpolate_flux(-3.0, 1.0)
        flux_21 = ige.interpolate_flux(21.0, 1.0)
        self.assertAlmostEqual(flux_neg, flux_21)

    def test_energy_above_grid_clamps(self):
        flux_high = ige.interpolate_flux(0.0, 100.0)
        flux_edge = ige.interpolate_flux(0.0, ige.ENERGY_GRID[-1])
        self.assertAlmostEqual(flux_high, flux_edge)

    def test_energy_below_grid_clamps(self):
        flux_low = ige.interpolate_flux(0.0, 0.001)
        flux_edge = ige.interpolate_flux(0.0, ige.ENERGY_GRID[0])
        self.assertAlmostEqual(flux_low, flux_edge)

    def test_dayside_minimum_below_dawn_peak(self):
        dawn_flux = ige.interpolate_flux(3.0, 1.0)
        noon_flux = ige.interpolate_flux(12.0, 1.0)
        self.assertGreater(dawn_flux, noon_flux)


class LocalTimeAveragedSpectrumTest(unittest.TestCase):
    def test_empty_dwells_raises(self):
        with self.assertRaises(ValueError):
            ige.local_time_averaged_spectrum([])

    def test_zero_total_dwell_raises(self):
        dwells = [ige.LocalTimeDwell(local_time_hours=0.0, dwell_seconds=0.0)]
        with self.assertRaises(ValueError):
            ige.local_time_averaged_spectrum(dwells)

    def test_single_dwell_matches_interpolate_flux(self):
        dwells = [ige.LocalTimeDwell(local_time_hours=6.0, dwell_seconds=100.0)]
        spectrum = ige.local_time_averaged_spectrum(dwells, energies_mev=(1.0,))
        self.assertAlmostEqual(spectrum[1.0], ige.interpolate_flux(6.0, 1.0))

    def test_weighted_average_of_two_dwells(self):
        dwells = [
            ige.LocalTimeDwell(local_time_hours=0.0, dwell_seconds=1.0),
            ige.LocalTimeDwell(local_time_hours=12.0, dwell_seconds=3.0),
        ]
        spectrum = ige.local_time_averaged_spectrum(dwells, energies_mev=(1.0,))
        expected = (
            ige.interpolate_flux(0.0, 1.0) * 1.0 + ige.interpolate_flux(12.0, 1.0) * 3.0
        ) / 4.0
        self.assertAlmostEqual(spectrum[1.0], expected)


class IntegrateFluenceTest(unittest.TestCase):
    def test_empty_dwells_raises(self):
        with self.assertRaises(ValueError):
            ige.integrate_fluence([], energy_mev=1.0)

    def test_negative_dwell_raises(self):
        dwells = [ige.LocalTimeDwell(local_time_hours=0.0, dwell_seconds=-1.0)]
        with self.assertRaises(ValueError):
            ige.integrate_fluence(dwells, energy_mev=1.0)

    def test_single_dwell_fluence(self):
        dwells = [ige.LocalTimeDwell(local_time_hours=6.0, dwell_seconds=100.0)]
        fluence = ige.integrate_fluence(dwells, energy_mev=1.0)
        self.assertAlmostEqual(fluence, ige.interpolate_flux(6.0, 1.0) * 100.0)

    def test_sums_multiple_dwells(self):
        dwells = [
            ige.LocalTimeDwell(local_time_hours=0.0, dwell_seconds=10.0),
            ige.LocalTimeDwell(local_time_hours=12.0, dwell_seconds=20.0),
        ]
        fluence = ige.integrate_fluence(dwells, energy_mev=1.0)
        expected = (
            ige.interpolate_flux(0.0, 1.0) * 10.0 + ige.interpolate_flux(12.0, 1.0) * 20.0
        )
        self.assertAlmostEqual(fluence, expected)


class CategorizeSeverityTest(unittest.TestCase):
    def test_negative_fluence_raises(self):
        with self.assertRaises(ValueError):
            ige.categorize_severity(-1.0)

    def test_benign_at_and_below_threshold(self):
        self.assertEqual(ige.categorize_severity(0.0), "benign")
        self.assertEqual(ige.categorize_severity(1.0e10), "benign")

    def test_elevated_above_benign_threshold(self):
        self.assertEqual(ige.categorize_severity(1.0e10 + 1.0), "elevated")
        self.assertEqual(ige.categorize_severity(1.0e12), "elevated")

    def test_severe_above_elevated_threshold(self):
        self.assertEqual(ige.categorize_severity(1.0e12 + 1.0), "severe")
        self.assertEqual(ige.categorize_severity(math.inf), "severe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
