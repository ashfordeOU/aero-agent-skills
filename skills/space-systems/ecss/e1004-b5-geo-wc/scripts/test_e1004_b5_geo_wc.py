#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.5 NASA worst-case
geosynchronous (GEO) electron environment spectrum.

Exercises scripts/e1004_b5_geo_wc_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - an energy selects the
model band whose sub-range contains it (surface below the boundary,
internal at/above it, both bounded by the model's overall valid
range); differential flux follows each band's exponential fit;
integral flux above a threshold energy sums the partial integral of
the threshold's own band with the full integral of every band above
it; worst-case fluence scales integral flux by the full exposure
duration with no duty-cycle reduction; a case is compliant only when
its worst-case fluence does not exceed its qualified fluence limit;
the assessment record covers every case with no duplicates and is
reported all-compliant only when every case is compliant.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b5_geo_wc_logic as gw  # noqa: E402


def _band_integral(band, lo_mev, hi_mev):
    """Independent re-derivation of the analytic exponential-flux
    integral, used to compute expected values without calling the
    module under test."""
    j0 = band["j0"]
    e0 = band["e0_mev"]
    return j0 * e0 * (math.exp(-lo_mev / e0) - math.exp(-hi_mev / e0))


class BandForEnergyTest(unittest.TestCase):
    def test_energy_in_surface_band(self):
        self.assertEqual(gw.band_for_energy(0.05)["name"], "surface")

    def test_boundary_energy_selects_internal_band(self):
        self.assertEqual(gw.band_for_energy(0.15)["name"], "internal")

    def test_upper_edge_selects_internal_band(self):
        self.assertEqual(gw.band_for_energy(gw.MODEL_MAX_MEV)["name"], "internal")

    def test_below_valid_range_raises(self):
        with self.assertRaises(ValueError):
            gw.band_for_energy(gw.MODEL_MIN_MEV - 0.01)

    def test_above_valid_range_raises(self):
        with self.assertRaises(ValueError):
            gw.band_for_energy(gw.MODEL_MAX_MEV + 0.01)


class DifferentialFluxTest(unittest.TestCase):
    def test_matches_exponential_fit(self):
        band = gw.band_for_energy(0.05)
        expected = band["j0"] * math.exp(-0.05 / band["e0_mev"])
        self.assertAlmostEqual(gw.differential_flux(0.05), expected)

    def test_flux_decreases_with_energy_within_band(self):
        self.assertGreater(gw.differential_flux(0.02), gw.differential_flux(0.10))

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            gw.differential_flux(10.0)


class IntegralFluxAboveTest(unittest.TestCase):
    def test_zero_at_upper_edge(self):
        self.assertEqual(gw.integral_flux_above(gw.MODEL_MAX_MEV), 0.0)

    def test_at_band_boundary_counts_only_upper_band(self):
        internal_band = gw.BANDS[1]
        expected = _band_integral(
            internal_band, internal_band["min_mev"], internal_band["max_mev"]
        )
        self.assertAlmostEqual(gw.integral_flux_above(0.15), expected)

    def test_at_model_minimum_sums_both_bands(self):
        surface_band, internal_band = gw.BANDS
        expected = _band_integral(
            surface_band, surface_band["min_mev"], surface_band["max_mev"]
        ) + _band_integral(
            internal_band, internal_band["min_mev"], internal_band["max_mev"]
        )
        self.assertAlmostEqual(gw.integral_flux_above(gw.MODEL_MIN_MEV), expected)

    def test_decreases_as_threshold_rises(self):
        self.assertGreater(
            gw.integral_flux_above(gw.MODEL_MIN_MEV), gw.integral_flux_above(0.15)
        )
        self.assertGreater(gw.integral_flux_above(0.15), gw.integral_flux_above(1.0))

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            gw.integral_flux_above(gw.MODEL_MIN_MEV - 0.01)


class WorstCaseFluenceTest(unittest.TestCase):
    def test_scales_flux_by_duration(self):
        flux = gw.integral_flux_above(0.15)
        self.assertAlmostEqual(
            gw.worst_case_fluence(0.15, 1.0), flux * gw.SECONDS_PER_DAY
        )
        self.assertAlmostEqual(
            gw.worst_case_fluence(0.15, 2.0), flux * 2.0 * gw.SECONDS_PER_DAY
        )

    def test_non_positive_duration_raises(self):
        with self.assertRaises(ValueError):
            gw.worst_case_fluence(0.15, 0.0)
        with self.assertRaises(ValueError):
            gw.worst_case_fluence(0.15, -1.0)

    def test_out_of_range_energy_raises(self):
        with self.assertRaises(ValueError):
            gw.worst_case_fluence(10.0, 1.0)


class AssessCaseTest(unittest.TestCase):
    def _reference_fluence(self, energy_mev=0.15, duration_days=1.0):
        return gw.worst_case_fluence(energy_mev, duration_days)

    def test_compliant_case_within_qualified_limit(self):
        fluence = self._reference_fluence()
        case = {
            "id": "GEOWC-001",
            "energy_threshold_mev": 0.15,
            "duration_days": 1.0,
            "qualified_fluence_limit": fluence * 2.0,
        }
        result = gw.assess_case(case)
        self.assertAlmostEqual(result["worst_case_fluence"], fluence)
        self.assertTrue(result["compliant"])
        self.assertGreater(result["margin"], 1.0)

    def test_noncompliant_case_exceeding_qualified_limit(self):
        fluence = self._reference_fluence()
        case = {
            "id": "GEOWC-002",
            "energy_threshold_mev": 0.15,
            "duration_days": 1.0,
            "qualified_fluence_limit": fluence * 0.5,
        }
        result = gw.assess_case(case)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin"], 1.0)

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            gw.assess_case({
                "energy_threshold_mev": 0.15,
                "duration_days": 1.0,
                "qualified_fluence_limit": 1.0,
            })

    def test_invalid_duration_raises(self):
        with self.assertRaises(ValueError):
            gw.assess_case({
                "id": "GEOWC-003",
                "energy_threshold_mev": 0.15,
                "duration_days": 0.0,
                "qualified_fluence_limit": 1.0,
            })


class BuildGeoWcAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "GEOWC-001",
            "energy_threshold_mev": 0.15,
            "duration_days": 1.0,
            "qualified_fluence_limit": 1.0e12,
        },
        {
            "id": "GEOWC-002",
            "energy_threshold_mev": 0.15,
            "duration_days": 1.0,
            "qualified_fluence_limit": 1.0,
        },
    ]

    def test_record_order_and_status(self):
        record = gw.build_geo_wc_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "GEOWC-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "GEOWC-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            gw.build_geo_wc_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        gw.build_geo_wc_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = gw.build_geo_wc_assessment(BuildGeoWcAssessmentTest.CASES)
        self.assertEqual(gw.noncompliant_items(record), ["GEOWC-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = gw.build_geo_wc_assessment([BuildGeoWcAssessmentTest.CASES[0]])
        self.assertTrue(gw.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = gw.build_geo_wc_assessment(BuildGeoWcAssessmentTest.CASES)
        self.assertFalse(gw.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
