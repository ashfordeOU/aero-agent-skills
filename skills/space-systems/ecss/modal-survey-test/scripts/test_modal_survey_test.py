#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32-11C clause 4.6.3.8 modal survey test.

Exercises scripts/modal_survey_test_logic.py (stdlib unittest, offline).
Contract: a valid excitation method is accepted and an unrecognised method
raises; the MAC is 1.0 for identical shapes, 0.0 for orthogonal shapes, and
scale-invariant; mismatched or empty shape vectors raise; frequency correlation
passes within tolerance and fails outside; damping plausibility holds within the
structural range and fails outside; mode coverage reports missing target modes;
measurement adequacy passes when the point count meets the minimum and reports the
shortfall when it does not; the full compliance verdict is True only when every
finding container is empty and False when any finding is present.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modal_survey_test_logic as ms  # noqa: E402


class ValidateExcitationMethodTest(unittest.TestCase):
    def test_sine_sweep_accepted(self):
        ms.validate_excitation_method("sine_sweep")

    def test_stepped_sine_accepted(self):
        ms.validate_excitation_method("stepped_sine")

    def test_broadband_random_accepted(self):
        ms.validate_excitation_method("broadband_random")

    def test_impact_accepted(self):
        ms.validate_excitation_method("impact")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            ms.validate_excitation_method("electromagnetic_pulse")


class ComputeMacTest(unittest.TestCase):
    def test_identical_vectors_mac_is_one(self):
        shape = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(ms.compute_mac(shape, shape), 1.0)

    def test_orthogonal_vectors_mac_is_zero(self):
        self.assertAlmostEqual(ms.compute_mac([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_scale_invariant(self):
        a = [1.0, 2.0, 3.0]
        b = [2.0, 4.0, 6.0]
        self.assertAlmostEqual(ms.compute_mac(a, b), 1.0)

    def test_partial_correlation_between_zero_and_one(self):
        mac = ms.compute_mac([1.0, 0.0, 0.0], [1.0, 1.0, 0.0])
        self.assertGreater(mac, 0.0)
        self.assertLess(mac, 1.0)

    def test_mismatched_length_raises(self):
        with self.assertRaises(ValueError):
            ms.compute_mac([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_empty_vectors_raise(self):
        with self.assertRaises(ValueError):
            ms.compute_mac([], [])

    def test_zero_test_shape_raises(self):
        with self.assertRaises(ValueError):
            ms.compute_mac([0.0, 0.0], [1.0, 2.0])

    def test_zero_fem_shape_raises(self):
        with self.assertRaises(ValueError):
            ms.compute_mac([1.0, 2.0], [0.0, 0.0])


class CheckFrequencyCorrelationTest(unittest.TestCase):
    def test_exact_match_passes(self):
        self.assertTrue(ms.check_frequency_correlation(10.0, 10.0))

    def test_within_five_percent_passes(self):
        self.assertTrue(ms.check_frequency_correlation(10.4, 10.0))

    def test_exactly_at_tolerance_passes(self):
        self.assertTrue(ms.check_frequency_correlation(10.5, 10.0, 0.05))

    def test_outside_tolerance_fails(self):
        self.assertFalse(ms.check_frequency_correlation(10.6, 10.0, 0.05))

    def test_non_positive_fem_freq_raises(self):
        with self.assertRaises(ValueError):
            ms.check_frequency_correlation(10.0, 0.0)

    def test_negative_test_freq_raises(self):
        with self.assertRaises(ValueError):
            ms.check_frequency_correlation(-1.0, 10.0)


class CheckDampingPlausibleTest(unittest.TestCase):
    def test_typical_structural_damping_passes(self):
        self.assertTrue(ms.check_damping_plausible(0.02))

    def test_minimum_boundary_passes(self):
        self.assertTrue(ms.check_damping_plausible(ms.DAMPING_RATIO_MIN))

    def test_maximum_boundary_passes(self):
        self.assertTrue(ms.check_damping_plausible(ms.DAMPING_RATIO_MAX))

    def test_below_minimum_fails(self):
        self.assertFalse(ms.check_damping_plausible(0.0))

    def test_above_maximum_fails(self):
        self.assertFalse(ms.check_damping_plausible(0.20))


class CheckModeCoverageTest(unittest.TestCase):
    def test_all_modes_covered_returns_empty(self):
        self.assertEqual(ms.check_mode_coverage(["M1", "M2", "M3"], ["M1", "M2", "M3"]), [])

    def test_missing_mode_returned(self):
        missing = ms.check_mode_coverage(["M1", "M3"], ["M1", "M2", "M3"])
        self.assertIn("M2", missing)
        self.assertEqual(len(missing), 1)

    def test_no_target_modes_returns_empty(self):
        self.assertEqual(ms.check_mode_coverage(["M1"], []), [])

    def test_all_missing_returns_all_targets(self):
        missing = ms.check_mode_coverage([], ["M1", "M2"])
        self.assertEqual(sorted(missing), ["M1", "M2"])


class CheckMeasurementAdequacyTest(unittest.TestCase):
    def test_meeting_minimum_is_adequate(self):
        result = ms.check_measurement_adequacy(30, 30)
        self.assertTrue(result["adequate"])

    def test_exceeding_minimum_is_adequate(self):
        result = ms.check_measurement_adequacy(50, 30)
        self.assertTrue(result["adequate"])

    def test_below_minimum_not_adequate(self):
        result = ms.check_measurement_adequacy(20, 30)
        self.assertFalse(result["adequate"])
        self.assertEqual(result["shortfall"], 10)

    def test_zero_points_below_nonzero_minimum(self):
        result = ms.check_measurement_adequacy(0, 5)
        self.assertFalse(result["adequate"])
        self.assertEqual(result["shortfall"], 5)


class ModalModeVerdictTest(unittest.TestCase):
    def _good_shape(self):
        return [1.0, 0.5, -0.5]

    def test_passing_mode_has_no_findings(self):
        findings = ms.modal_mode_verdict(
            "M1", 10.0, 10.0, self._good_shape(), self._good_shape(), 0.02
        )
        self.assertEqual(findings, [])

    def test_low_mac_flagged(self):
        test_shape = [1.0, 0.0, 0.0]
        fem_shape = [0.0, 1.0, 0.0]
        findings = ms.modal_mode_verdict("M1", 10.0, 10.0, test_shape, fem_shape, 0.02)
        issues = [f["issue"] for f in findings]
        self.assertIn("mac_below_threshold", issues)

    def test_frequency_deviation_flagged(self):
        findings = ms.modal_mode_verdict(
            "M2", 12.0, 10.0, self._good_shape(), self._good_shape(), 0.02
        )
        issues = [f["issue"] for f in findings]
        self.assertIn("frequency_outside_tolerance", issues)

    def test_damping_anomaly_flagged(self):
        findings = ms.modal_mode_verdict(
            "M3", 10.0, 10.0, self._good_shape(), self._good_shape(), 0.0
        )
        issues = [f["issue"] for f in findings]
        self.assertIn("damping_outside_plausible_range", issues)

    def test_multiple_findings_accumulated(self):
        test_shape = [1.0, 0.0]
        fem_shape = [0.0, 1.0]
        findings = ms.modal_mode_verdict("M4", 15.0, 10.0, test_shape, fem_shape, 0.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("mac_below_threshold", issues)
        self.assertIn("frequency_outside_tolerance", issues)
        self.assertIn("damping_outside_plausible_range", issues)


class ModalSurveyComplianceTest(unittest.TestCase):
    def _good_shape(self):
        return [1.0, 0.5, -0.5, 0.2]

    def _passing_survey(self):
        return {
            "excitation_method": "sine_sweep",
            "num_measurement_points": 40,
            "min_measurement_points": 30,
            "target_mode_ids": ["M1", "M2"],
            "modes": [
                {
                    "mode_id": "M1",
                    "test_freq_hz": 10.0,
                    "fem_freq_hz": 10.0,
                    "test_shape": self._good_shape(),
                    "fem_shape": self._good_shape(),
                    "damping_ratio": 0.02,
                },
                {
                    "mode_id": "M2",
                    "test_freq_hz": 25.0,
                    "fem_freq_hz": 25.0,
                    "test_shape": self._good_shape(),
                    "fem_shape": self._good_shape(),
                    "damping_ratio": 0.015,
                },
            ],
        }

    def test_fully_passing_survey_is_compliant(self):
        result = ms.modal_survey_compliance(self._passing_survey())
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["excitation_finding"])
        self.assertIsNone(result["measurement_finding"])
        self.assertEqual(result["coverage_finding"], [])
        self.assertEqual(result["mode_findings"], {})

    def test_invalid_excitation_method_not_compliant(self):
        survey = self._passing_survey()
        survey["excitation_method"] = "tuning_fork"
        result = ms.modal_survey_compliance(survey)
        self.assertFalse(result["compliant"])
        self.assertIsNotNone(result["excitation_finding"])

    def test_insufficient_measurement_points_not_compliant(self):
        survey = self._passing_survey()
        survey["num_measurement_points"] = 10
        result = ms.modal_survey_compliance(survey)
        self.assertFalse(result["compliant"])
        self.assertIsNotNone(result["measurement_finding"])
        self.assertEqual(result["measurement_finding"]["shortfall"], 20)

    def test_missing_target_mode_not_compliant(self):
        survey = self._passing_survey()
        survey["target_mode_ids"] = ["M1", "M2", "M3"]
        result = ms.modal_survey_compliance(survey)
        self.assertFalse(result["compliant"])
        self.assertIn("M3", result["coverage_finding"])

    def test_non_correlating_mode_not_compliant(self):
        survey = self._passing_survey()
        survey["modes"][0]["test_shape"] = [1.0, 0.0, 0.0, 0.0]
        survey["modes"][0]["fem_shape"] = [0.0, 1.0, 0.0, 0.0]
        result = ms.modal_survey_compliance(survey)
        self.assertFalse(result["compliant"])
        self.assertIn("M1", result["mode_findings"])

    def test_custom_mac_threshold_applied(self):
        survey = self._passing_survey()
        survey["mac_threshold"] = 0.999
        survey["modes"][0]["test_shape"] = [1.0, 0.5, -0.5, 0.3]
        survey["modes"][0]["fem_shape"] = [1.0, 0.5, -0.5, 0.2]
        result = ms.modal_survey_compliance(survey)
        self.assertFalse(result["compliant"])
        self.assertIn("M1", result["mode_findings"])


if __name__ == "__main__":
    unittest.main()
