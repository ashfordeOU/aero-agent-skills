#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C / ECSS-E-ST-32-11 test-analysis
correlation assessment.

Exercises scripts/test_analysis_correlation_logic.py (stdlib unittest,
offline). Contract: frequency_deviation returns (f_test - f_analysis) /
f_analysis and raises for negative f_test or non-positive f_analysis;
frequency_within_tolerance passes for deviations at or below the tolerance
and fails above it; mac_value yields 1.0 for identical mode shapes, 0.0
for orthogonal shapes, and raises for mismatched lengths or zero-norm
vectors; pair_modes performs greedy one-to-one pairing by highest MAC and
records NO_PAIR when no analysis candidate meets the threshold;
frequency_correlation_violations flags unmatched modes and paired modes
whose deviation exceeds tolerance; mac_correlation_violations flags paired
modes whose MAC falls below the threshold; correlation_review aggregates
all findings; is_correlation_compliant is True only when both violation
lists are empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_analysis_correlation_logic as tac  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mode(mode_id, frequency_hz, shape):
    return {"mode_id": mode_id, "frequency_hz": frequency_hz, "shape": shape}


# ---------------------------------------------------------------------------
# FrequencyDeviationTest
# ---------------------------------------------------------------------------

class FrequencyDeviationTest(unittest.TestCase):
    def test_positive_deviation(self):
        dev = tac.frequency_deviation(105.0, 100.0)
        self.assertAlmostEqual(dev, 0.05)

    def test_negative_deviation(self):
        dev = tac.frequency_deviation(95.0, 100.0)
        self.assertAlmostEqual(dev, -0.05)

    def test_zero_deviation(self):
        dev = tac.frequency_deviation(100.0, 100.0)
        self.assertAlmostEqual(dev, 0.0)

    def test_negative_f_test_raises(self):
        with self.assertRaises(ValueError):
            tac.frequency_deviation(-1.0, 100.0)

    def test_zero_f_analysis_raises(self):
        with self.assertRaises(ValueError):
            tac.frequency_deviation(100.0, 0.0)

    def test_negative_f_analysis_raises(self):
        with self.assertRaises(ValueError):
            tac.frequency_deviation(100.0, -10.0)


# ---------------------------------------------------------------------------
# FrequencyWithinToleranceTest
# ---------------------------------------------------------------------------

class FrequencyWithinToleranceTest(unittest.TestCase):
    def test_exact_match_passes(self):
        self.assertTrue(tac.frequency_within_tolerance(100.0, 100.0, 0.05))

    def test_at_positive_boundary_passes(self):
        # 5 % above analysis frequency — should pass at 0.05 tolerance
        self.assertTrue(tac.frequency_within_tolerance(105.0, 100.0, 0.05))

    def test_exceeds_positive_boundary_fails(self):
        self.assertFalse(tac.frequency_within_tolerance(106.0, 100.0, 0.05))

    def test_at_negative_boundary_passes(self):
        self.assertTrue(tac.frequency_within_tolerance(95.0, 100.0, 0.05))

    def test_exceeds_negative_boundary_fails(self):
        self.assertFalse(tac.frequency_within_tolerance(94.0, 100.0, 0.05))

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            tac.frequency_within_tolerance(100.0, 100.0, 0.0)


# ---------------------------------------------------------------------------
# MacValueTest
# ---------------------------------------------------------------------------

class MacValueTest(unittest.TestCase):
    def test_identical_vectors_mac_is_one(self):
        phi = [1.0, 0.5, -0.3]
        self.assertAlmostEqual(tac.mac_value(phi, phi), 1.0)

    def test_scaled_vector_mac_is_one(self):
        # Scaling a vector by a constant does not change MAC
        phi = [1.0, 2.0, 3.0]
        phi_scaled = [2.0, 4.0, 6.0]
        self.assertAlmostEqual(tac.mac_value(phi, phi_scaled), 1.0)

    def test_orthogonal_vectors_mac_is_zero(self):
        phi_t = [1.0, 0.0]
        phi_a = [0.0, 1.0]
        self.assertAlmostEqual(tac.mac_value(phi_t, phi_a), 0.0)

    def test_partial_correlation(self):
        phi_t = [1.0, 0.0]
        phi_a = [1.0, 1.0]
        mac = tac.mac_value(phi_t, phi_a)
        self.assertGreater(mac, 0.0)
        self.assertLess(mac, 1.0)

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            tac.mac_value([1.0, 0.0], [1.0, 0.0, 0.0])

    def test_zero_norm_test_vector_raises(self):
        with self.assertRaises(ValueError):
            tac.mac_value([0.0, 0.0], [1.0, 0.0])

    def test_zero_norm_analysis_vector_raises(self):
        with self.assertRaises(ValueError):
            tac.mac_value([1.0, 0.0], [0.0, 0.0])


# ---------------------------------------------------------------------------
# PairModesTest
# ---------------------------------------------------------------------------

class PairModesTest(unittest.TestCase):
    def _make_pair(self):
        """One test mode and one analysis mode with identical shapes."""
        tm = [_mode("T1", 10.0, [1.0, 0.0, 0.0])]
        am = [_mode("A1", 10.2, [1.0, 0.0, 0.0])]
        return tm, am

    def test_identical_shape_is_paired(self):
        tm, am = self._make_pair()
        pairs = tac.pair_modes(tm, am)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["analysis_mode_id"], "A1")
        self.assertAlmostEqual(pairs[0]["mac"], 1.0)

    def test_orthogonal_shape_is_unpaired(self):
        tm = [_mode("T1", 10.0, [1.0, 0.0])]
        am = [_mode("A1", 10.0, [0.0, 1.0])]
        pairs = tac.pair_modes(tm, am, mac_threshold=0.90)
        self.assertEqual(pairs[0]["analysis_mode_id"], tac.NO_PAIR)

    def test_one_to_one_no_reuse(self):
        # Two test modes, one analysis mode — second test mode must be unpaired
        phi = [1.0, 0.0, 0.0]
        tm = [_mode("T1", 10.0, phi), _mode("T2", 10.5, phi)]
        am = [_mode("A1", 10.0, phi)]
        pairs = tac.pair_modes(tm, am)
        paired = [p for p in pairs if p["analysis_mode_id"] != tac.NO_PAIR]
        unpaired = [p for p in pairs if p["analysis_mode_id"] == tac.NO_PAIR]
        self.assertEqual(len(paired), 1)
        self.assertEqual(len(unpaired), 1)

    def test_f_analysis_hz_none_for_unpaired(self):
        tm = [_mode("T1", 10.0, [1.0, 0.0])]
        am = [_mode("A1", 10.0, [0.0, 1.0])]
        pairs = tac.pair_modes(tm, am)
        self.assertIsNone(pairs[0]["f_analysis_hz"])


# ---------------------------------------------------------------------------
# FrequencyCorrelationViolationsTest
# ---------------------------------------------------------------------------

class FrequencyCorrelationViolationsTest(unittest.TestCase):
    def _paired(self, f_test, f_analysis, mac=0.95):
        return {
            "test_mode_id": "T1",
            "analysis_mode_id": "A1",
            "mac": mac,
            "f_test_hz": f_test,
            "f_analysis_hz": f_analysis,
        }

    def _unpaired(self):
        return {
            "test_mode_id": "T2",
            "analysis_mode_id": tac.NO_PAIR,
            "mac": 0.0,
            "f_test_hz": 10.0,
            "f_analysis_hz": None,
        }

    def test_within_tolerance_no_violation(self):
        pairs = [self._paired(102.0, 100.0)]
        self.assertEqual(tac.frequency_correlation_violations(pairs, 0.05), [])

    def test_exceeding_tolerance_flagged(self):
        pairs = [self._paired(110.0, 100.0)]
        violations = tac.frequency_correlation_violations(pairs, 0.05)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "frequency_deviation_exceeded")

    def test_unpaired_mode_flagged(self):
        pairs = [self._unpaired()]
        violations = tac.frequency_correlation_violations(pairs, 0.05)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unmatched_test_mode")

    def test_deviation_value_stored_in_violation(self):
        pairs = [self._paired(110.0, 100.0)]
        v = tac.frequency_correlation_violations(pairs, 0.05)[0]
        self.assertAlmostEqual(v["deviation"], 0.10)

    def test_empty_pairs_no_violation(self):
        self.assertEqual(tac.frequency_correlation_violations([]), [])


# ---------------------------------------------------------------------------
# MacCorrelationViolationsTest
# ---------------------------------------------------------------------------

class MacCorrelationViolationsTest(unittest.TestCase):
    def _pair(self, mac, mode_id="T1", am_id="A1"):
        return {
            "test_mode_id": mode_id,
            "analysis_mode_id": am_id,
            "mac": mac,
            "f_test_hz": 10.0,
            "f_analysis_hz": 10.0,
        }

    def _unpaired(self):
        return {
            "test_mode_id": "T2",
            "analysis_mode_id": tac.NO_PAIR,
            "mac": 0.0,
            "f_test_hz": 10.0,
            "f_analysis_hz": None,
        }

    def test_mac_at_threshold_no_violation(self):
        pairs = [self._pair(0.90)]
        self.assertEqual(tac.mac_correlation_violations(pairs, 0.90), [])

    def test_mac_above_threshold_no_violation(self):
        pairs = [self._pair(0.95)]
        self.assertEqual(tac.mac_correlation_violations(pairs, 0.90), [])

    def test_mac_below_threshold_flagged(self):
        pairs = [self._pair(0.80)]
        violations = tac.mac_correlation_violations(pairs, 0.90)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "mac_below_threshold")

    def test_unpaired_not_double_counted(self):
        # Unpaired modes must not appear in mac_correlation_violations
        pairs = [self._unpaired()]
        self.assertEqual(tac.mac_correlation_violations(pairs, 0.90), [])

    def test_mac_value_stored_in_violation(self):
        pairs = [self._pair(0.75)]
        v = tac.mac_correlation_violations(pairs, 0.90)[0]
        self.assertAlmostEqual(v["mac"], 0.75)
        self.assertAlmostEqual(v["mac_threshold"], 0.90)


# ---------------------------------------------------------------------------
# CorrelationReviewTest
# ---------------------------------------------------------------------------

class CorrelationReviewTest(unittest.TestCase):
    def _make_modes(self, freq_t, freq_a, same_shape=True):
        shape_t = [1.0, 0.0, 0.0]
        shape_a = [1.0, 0.0, 0.0] if same_shape else [0.0, 1.0, 0.0]
        tm = [_mode("T1", freq_t, shape_t)]
        am = [_mode("A1", freq_a, shape_a)]
        return tm, am

    def test_fully_compliant_review(self):
        tm, am = self._make_modes(10.0, 10.0)
        review = tac.correlation_review(tm, am)
        self.assertEqual(review["frequency_violations"], [])
        self.assertEqual(review["mac_violations"], [])
        self.assertTrue(tac.is_correlation_compliant(review))

    def test_frequency_violation_detected(self):
        tm, am = self._make_modes(12.0, 10.0)  # 20 % deviation
        review = tac.correlation_review(tm, am, freq_tolerance=0.05)
        self.assertTrue(len(review["frequency_violations"]) > 0)
        self.assertFalse(tac.is_correlation_compliant(review))

    def test_unmatched_mode_detected(self):
        tm = [_mode("T1", 10.0, [1.0, 0.0])]
        am = [_mode("A1", 10.0, [0.0, 1.0])]  # orthogonal — will not pair
        review = tac.correlation_review(tm, am, mac_threshold=0.90)
        self.assertEqual(review["frequency_violations"][0]["issue"], "unmatched_test_mode")
        self.assertFalse(tac.is_correlation_compliant(review))

    def test_pairs_list_returned(self):
        tm, am = self._make_modes(10.0, 10.0)
        review = tac.correlation_review(tm, am)
        self.assertIn("pairs", review)
        self.assertEqual(len(review["pairs"]), 1)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
