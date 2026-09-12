#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.3.10 acoustic test of
structure.

Exercises scripts/acoustic_test_logic.py (stdlib unittest, offline).
Contract: SPL-to-pressure conversion is exact and pressure-to-SPL
inverts it; OASPL power-sums band levels so two equal bands produce
OASPL = single-band + 10*log10(2) dB (3.0103 dB, of which "+3 dB" is
only a rounding); apply_qualification_margin adds the margin
per band without mutating the input; categorize_test returns the type
string for known categories and raises for unknown; frequency coverage
flags a low-end gap or high-end gap and passes when both endpoints are
met; duration check flags a shortfall for the correct category minimum
and passes at the boundary; spectrum compliance emits underdrive when
measured is below required minus tolerance, overdrive when above
required plus tolerance, and no finding when within tolerance;
and the full review aggregates all findings and is compliant only when
every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import acoustic_test_logic as at  # noqa: E402


class SplPressureConversionTest(unittest.TestCase):
    def test_94_db_is_1_0024_pa(self):
        # "94 dB re 20 μPa = 1 Pa" is an engineering rounding, not an
        # identity: 20e-6 * 10**(94/20) = 1.00237446725454457 Pa exactly.
        # Pinned here to places=9 (was places=3 against the rounded 1.0,
        # an assertion no correct 20 μPa implementation can satisfy).
        self.assertAlmostEqual(
            at.spl_to_pressure(94.0), 1.0023744672545446, places=9
        )

    def test_one_pascal_is_93_979_db(self):
        # Absolute pin on the 20 μPa reference itself: 20*log10(1/20e-6)
        # = 93.97940008672038 dB. A round-trip test cannot catch a wrong
        # reference pressure; this can.
        self.assertAlmostEqual(at.pressure_to_spl(1.0), 93.97940008672038, places=9)

    def test_pressure_to_spl_round_trip(self):
        for level in [60.0, 94.0, 120.0, 140.0]:
            p = at.spl_to_pressure(level)
            self.assertAlmostEqual(at.pressure_to_spl(p), level, places=10)

    def test_pressure_to_spl_zero_raises(self):
        with self.assertRaises(ValueError):
            at.pressure_to_spl(0.0)

    def test_pressure_to_spl_negative_raises(self):
        with self.assertRaises(ValueError):
            at.pressure_to_spl(-1.0)

    def test_spl_to_pressure_non_finite_raises(self):
        with self.assertRaises(ValueError):
            at.spl_to_pressure(float("inf"))


class OasplTest(unittest.TestCase):
    def test_single_band_oaspl_equals_band_level(self):
        self.assertAlmostEqual(at.compute_oaspl([100.0]), 100.0, places=10)

    def test_two_equal_bands_add_10_log10_2_db(self):
        # Doubling acoustic power adds 10*log10(2) = 3.0102999566398120 dB.
        # The shop-floor "+3 dB" is a rounding 0.0103 dB away from that, so
        # the previous 103.0-at-places=5 assertion was unsatisfiable.
        result = at.compute_oaspl([100.0, 100.0])
        self.assertAlmostEqual(result, 103.01029995663981, places=9)

    def test_four_equal_bands_add_10_log10_4_db(self):
        # Quadrupling power adds 10*log10(4) = 6.0205999132796240 dB.
        result = at.compute_oaspl([100.0, 100.0, 100.0, 100.0])
        self.assertAlmostEqual(result, 106.02059991327962, places=9)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            at.compute_oaspl([])

    def test_non_finite_band_raises(self):
        with self.assertRaises(ValueError):
            at.compute_oaspl([100.0, float("nan")])

    def test_oaspl_increases_with_more_bands(self):
        oaspl_2 = at.compute_oaspl([100.0, 100.0])
        oaspl_4 = at.compute_oaspl([100.0, 100.0, 100.0, 100.0])
        self.assertGreater(oaspl_4, oaspl_2)


class QualificationMarginTest(unittest.TestCase):
    def test_margin_added_to_each_band(self):
        acceptance = [100.0, 105.0, 110.0]
        qual = at.apply_qualification_margin(acceptance, margin_db=3.0)
        self.assertEqual(qual, [103.0, 108.0, 113.0])

    def test_default_margin_is_3_db(self):
        acceptance = [120.0]
        qual = at.apply_qualification_margin(acceptance)
        self.assertAlmostEqual(qual[0], 123.0)

    def test_does_not_mutate_input(self):
        acceptance = [100.0, 102.0]
        original = list(acceptance)
        at.apply_qualification_margin(acceptance, margin_db=3.0)
        self.assertEqual(acceptance, original)

    def test_zero_margin_raises(self):
        with self.assertRaises(ValueError):
            at.apply_qualification_margin([100.0], margin_db=0.0)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            at.apply_qualification_margin([100.0], margin_db=-1.0)


class CategorizationTest(unittest.TestCase):
    def test_qualification_accepted(self):
        self.assertEqual(at.categorize_test("qualification"), "qualification")

    def test_acceptance_accepted(self):
        self.assertEqual(at.categorize_test("acceptance"), "acceptance")

    def test_protoflight_accepted(self):
        self.assertEqual(at.categorize_test("protoflight"), "protoflight")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            at.categorize_test("development")


class FrequencyCoverageTest(unittest.TestCase):
    def _full_range(self):
        return [31.5, 40.0, 50.0, 63.0, 80.0, 100.0, 125.0, 160.0,
                200.0, 250.0, 315.0, 400.0, 500.0, 630.0, 800.0, 1000.0,
                1250.0, 1600.0, 2000.0, 2500.0, 3150.0, 4000.0, 5000.0,
                6300.0, 8000.0, 10000.0]

    def test_full_range_no_findings(self):
        self.assertEqual(at.check_frequency_coverage(self._full_range()), [])

    def test_low_end_gap_flagged(self):
        freqs = [63.0, 125.0, 1000.0, 10000.0]
        findings = at.check_frequency_coverage(freqs)
        issues = [f["issue"] for f in findings]
        self.assertIn("low_frequency_coverage_gap", issues)

    def test_high_end_gap_flagged(self):
        freqs = [31.5, 125.0, 1000.0, 8000.0]
        findings = at.check_frequency_coverage(freqs)
        issues = [f["issue"] for f in findings]
        self.assertIn("high_frequency_coverage_gap", issues)

    def test_both_ends_missing_two_findings(self):
        freqs = [63.0, 500.0, 4000.0]
        findings = at.check_frequency_coverage(freqs)
        self.assertEqual(len(findings), 2)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            at.check_frequency_coverage([])


class DurationCheckTest(unittest.TestCase):
    def test_qualification_at_minimum_passes(self):
        self.assertEqual(at.check_test_duration(120, "qualification"), [])

    def test_qualification_above_minimum_passes(self):
        self.assertEqual(at.check_test_duration(180, "qualification"), [])

    def test_qualification_below_minimum_flagged(self):
        findings = at.check_test_duration(60, "qualification")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "test_duration_below_minimum")
        self.assertEqual(findings[0]["minimum_s"], 120)

    def test_acceptance_at_minimum_passes(self):
        self.assertEqual(at.check_test_duration(60, "acceptance"), [])

    def test_acceptance_below_minimum_flagged(self):
        findings = at.check_test_duration(30, "acceptance")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["minimum_s"], 60)

    def test_protoflight_minimum_equals_qualification(self):
        self.assertEqual(at.check_test_duration(120, "protoflight"), [])
        findings = at.check_test_duration(60, "protoflight")
        self.assertEqual(findings[0]["minimum_s"], 120)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            at.check_test_duration(-1, "acceptance")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            at.check_test_duration(120, "proto")


class SpectrumComplianceTest(unittest.TestCase):
    def test_within_tolerance_no_findings(self):
        required = [120.0, 125.0, 130.0]
        measured = [120.0, 125.0, 130.0]
        self.assertEqual(at.check_spectrum_compliance(measured, required), [])

    def test_exactly_at_tolerance_boundary_no_findings(self):
        required = [120.0]
        measured = [119.0]  # exactly at -1 dB boundary
        self.assertEqual(at.check_spectrum_compliance(measured, required, 1.0), [])

    def test_underdrive_flagged(self):
        required = [120.0]
        measured = [118.5]  # 1.5 dB below, exceeds default 1 dB tolerance
        findings = at.check_spectrum_compliance(measured, required)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "spectrum_underdrive")
        self.assertEqual(findings[0]["band_index"], 0)

    def test_overdrive_flagged(self):
        required = [120.0]
        measured = [121.5]  # 1.5 dB above, exceeds default 1 dB tolerance
        findings = at.check_spectrum_compliance(measured, required)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "spectrum_overdrive")

    def test_multiple_band_violations(self):
        required = [100.0, 110.0, 120.0]
        measured = [98.0, 110.0, 122.5]  # band 0 under, band 2 over
        findings = at.check_spectrum_compliance(measured, required)
        issues = [f["issue"] for f in findings]
        self.assertIn("spectrum_underdrive", issues)
        self.assertIn("spectrum_overdrive", issues)

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            at.check_spectrum_compliance([100.0, 110.0], [100.0])

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            at.check_spectrum_compliance([100.0], [100.0], tolerance_db=0.0)


class AcousticTestReviewTest(unittest.TestCase):
    def _full_freqs(self):
        return [31.5, 40.0, 50.0, 63.0, 80.0, 100.0, 125.0, 160.0,
                200.0, 250.0, 315.0, 400.0, 500.0, 630.0, 800.0, 1000.0,
                1250.0, 1600.0, 2000.0, 2500.0, 3150.0, 4000.0, 5000.0,
                6300.0, 8000.0, 10000.0]

    def _flat_spectrum(self, level_db, n=26):
        return [level_db] * n

    def test_fully_compliant_qualification_review(self):
        required = self._flat_spectrum(130.0)
        measured = self._flat_spectrum(130.0)
        record = {
            "test_type": "qualification",
            "duration_s": 120,
            "band_center_freqs_hz": self._full_freqs(),
            "required_levels_db": required,
            "measured_levels_db": measured,
        }
        review = at.acoustic_test_review(record)
        self.assertEqual(review["test_type"], "qualification")
        self.assertTrue(at.is_acoustic_test_compliant(review))

    def test_review_flags_duration_shortfall(self):
        required = self._flat_spectrum(130.0)
        measured = self._flat_spectrum(130.0)
        record = {
            "test_type": "qualification",
            "duration_s": 60,  # below 120 s minimum
            "band_center_freqs_hz": self._full_freqs(),
            "required_levels_db": required,
            "measured_levels_db": measured,
        }
        review = at.acoustic_test_review(record)
        self.assertTrue(review["findings"]["duration"])
        self.assertFalse(at.is_acoustic_test_compliant(review))

    def test_review_flags_frequency_gap(self):
        required = self._flat_spectrum(130.0, n=3)
        measured = self._flat_spectrum(130.0, n=3)
        record = {
            "test_type": "acceptance",
            "duration_s": 60,
            "band_center_freqs_hz": [63.0, 1000.0, 8000.0],  # missing both ends
            "required_levels_db": required,
            "measured_levels_db": measured,
        }
        review = at.acoustic_test_review(record)
        self.assertEqual(len(review["findings"]["frequency_coverage"]), 2)

    def test_review_oaspl_fields_populated(self):
        required = self._flat_spectrum(130.0)
        measured = self._flat_spectrum(130.0)
        record = {
            "test_type": "acceptance",
            "duration_s": 60,
            "band_center_freqs_hz": self._full_freqs(),
            "required_levels_db": required,
            "measured_levels_db": measured,
        }
        review = at.acoustic_test_review(record)
        self.assertIn("oaspl_required_db", review)
        self.assertIn("oaspl_measured_db", review)
        self.assertAlmostEqual(
            review["oaspl_required_db"], review["oaspl_measured_db"], places=5
        )

    def test_review_raises_on_unknown_test_type(self):
        required = self._flat_spectrum(130.0)
        measured = self._flat_spectrum(130.0)
        record = {
            "test_type": "development",
            "duration_s": 60,
            "band_center_freqs_hz": self._full_freqs(),
            "required_levels_db": required,
            "measured_levels_db": measured,
        }
        with self.assertRaises(ValueError):
            at.acoustic_test_review(record)

    def test_is_compliant_false_when_spectrum_findings_present(self):
        required = self._flat_spectrum(130.0)
        measured = self._flat_spectrum(127.0)  # 3 dB under, exceeds 1 dB tolerance
        record = {
            "test_type": "acceptance",
            "duration_s": 60,
            "band_center_freqs_hz": self._full_freqs(),
            "required_levels_db": required,
            "measured_levels_db": measured,
        }
        review = at.acoustic_test_review(record)
        self.assertFalse(at.is_acoustic_test_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
