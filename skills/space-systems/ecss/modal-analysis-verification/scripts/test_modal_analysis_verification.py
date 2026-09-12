#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.2.4 modal analysis
verification.

Exercises scripts/modal_analysis_verification_logic.py (stdlib unittest,
offline). Contract: fundamental frequency in an axis is the lowest
natural frequency among modes with non-zero effective mass in that axis,
and None when no such mode exists; frequency margin is (f_mode/f_req)-1,
positive for a pass, negative for a violation, and non-positive inputs
raise; cumulative effective mass participation is the sum of per-mode
fractions across all modes in an axis, and must reach the required
threshold; an axis with no effective mass produces a no_mode issue and
compliant=False; the aggregated verification is compliant only when every
frequency check and every mass participation check passes; unrecognized
axes and invalid thresholds raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modal_analysis_verification_logic as ma  # noqa: E402


def _make_mode(mode_id, frequency_hz, lateral_x=0.0, lateral_y=0.0, axial_z=0.0):
    return {
        "mode_id": mode_id,
        "frequency_hz": frequency_hz,
        "effective_mass_fraction": {
            "lateral_x": lateral_x,
            "lateral_y": lateral_y,
            "axial_z": axial_z,
        },
    }


class FrequencyMarginTest(unittest.TestCase):
    def test_margin_above_requirement_is_positive(self):
        margin = ma.compute_frequency_margin(20.0, 10.0)
        self.assertAlmostEqual(margin, 1.0)

    def test_margin_exactly_at_requirement_is_zero(self):
        margin = ma.compute_frequency_margin(10.0, 10.0)
        self.assertAlmostEqual(margin, 0.0)

    def test_margin_below_requirement_is_negative(self):
        margin = ma.compute_frequency_margin(8.0, 10.0)
        self.assertLess(margin, 0.0)

    def test_zero_mode_frequency_raises(self):
        with self.assertRaises(ValueError):
            ma.compute_frequency_margin(0.0, 10.0)

    def test_negative_mode_frequency_raises(self):
        with self.assertRaises(ValueError):
            ma.compute_frequency_margin(-5.0, 10.0)

    def test_zero_required_frequency_raises(self):
        with self.assertRaises(ValueError):
            ma.compute_frequency_margin(10.0, 0.0)


class FundamentalFrequencyTest(unittest.TestCase):
    def test_lowest_effective_mass_mode_is_fundamental(self):
        modes = [
            _make_mode("m1", 12.0, lateral_x=0.5),
            _make_mode("m2", 8.0, lateral_x=0.3),
            _make_mode("m3", 20.0, lateral_x=0.1),
        ]
        self.assertAlmostEqual(ma.fundamental_frequency(modes, "lateral_x"), 8.0)

    def test_zero_effective_mass_mode_excluded(self):
        modes = [
            _make_mode("m1", 5.0, lateral_x=0.0),
            _make_mode("m2", 15.0, lateral_x=0.6),
        ]
        self.assertAlmostEqual(ma.fundamental_frequency(modes, "lateral_x"), 15.0)

    def test_no_effective_mass_returns_none(self):
        modes = [_make_mode("m1", 10.0, lateral_x=0.0)]
        self.assertIsNone(ma.fundamental_frequency(modes, "lateral_x"))

    def test_empty_mode_list_returns_none(self):
        self.assertIsNone(ma.fundamental_frequency([], "axial_z"))

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            ma.fundamental_frequency([], "radial_q")


class CheckFrequencyRequirementTest(unittest.TestCase):
    def test_compliant_when_fundamental_above_requirement(self):
        modes = [_make_mode("m1", 15.0, lateral_x=0.9)]
        result = ma.check_frequency_requirement(modes, "lateral_x", 10.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["fundamental_hz"], 15.0)
        self.assertAlmostEqual(result["margin"], 0.5)

    def test_violation_when_fundamental_below_requirement(self):
        modes = [_make_mode("m1", 8.0, lateral_y=0.8)]
        result = ma.check_frequency_requirement(modes, "lateral_y", 10.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["issue"], "frequency_requirement_violated")
        self.assertLess(result["margin"], 0.0)

    def test_no_effective_mass_produces_issue_and_not_compliant(self):
        modes = [_make_mode("m1", 10.0, lateral_x=0.0)]
        result = ma.check_frequency_requirement(modes, "lateral_x", 5.0)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["fundamental_hz"])
        self.assertIsNone(result["margin"])
        self.assertEqual(result["issue"], "no_mode_with_effective_mass_in_axis")

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            ma.check_frequency_requirement([], "roll_theta", 10.0)

    def test_non_positive_required_hz_raises(self):
        with self.assertRaises(ValueError):
            ma.check_frequency_requirement([], "axial_z", 0.0)


class CheckMassParticipationTest(unittest.TestCase):
    def test_compliant_when_cumulative_meets_threshold(self):
        modes = [
            _make_mode("m1", 10.0, axial_z=0.5),
            _make_mode("m2", 20.0, axial_z=0.45),
        ]
        result = ma.check_mass_participation(modes, "axial_z", threshold=0.90)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["cumulative_fraction"], 0.95)

    def test_not_compliant_when_cumulative_below_threshold(self):
        modes = [_make_mode("m1", 10.0, lateral_x=0.5)]
        result = ma.check_mass_participation(modes, "lateral_x", threshold=0.90)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["issue"], "insufficient_mass_participation")

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            ma.check_mass_participation([], "axial_z", threshold=0.0)

    def test_threshold_above_one_raises(self):
        with self.assertRaises(ValueError):
            ma.check_mass_participation([], "axial_z", threshold=1.1)

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            ma.check_mass_participation([], "pitch_phi")

    def test_missing_effective_mass_fraction_key_treated_as_zero(self):
        modes = [{"mode_id": "m1", "frequency_hz": 10.0}]
        result = ma.check_mass_participation(modes, "lateral_y", threshold=0.90)
        self.assertAlmostEqual(result["cumulative_fraction"], 0.0)
        self.assertFalse(result["compliant"])


class VerifyModalAnalysisTest(unittest.TestCase):
    def _make_compliant_modes(self):
        # m1 drives lateral axes (12 Hz > 10 Hz req); m2 drives axial (25 Hz > 20 Hz req)
        return [
            _make_mode("m1", 12.0, lateral_x=0.50, lateral_y=0.50, axial_z=0.0),
            _make_mode("m2", 25.0, lateral_x=0.45, lateral_y=0.45, axial_z=0.95),
        ]

    def test_fully_compliant_result(self):
        modes = self._make_compliant_modes()
        reqs = {"lateral_x": 10.0, "lateral_y": 10.0, "axial_z": 20.0}
        result = ma.verify_modal_analysis(modes, reqs, mass_participation_threshold=0.90)
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["frequency_checks"]), 3)
        self.assertEqual(len(result["mass_participation_checks"]), 3)
        for chk in result["frequency_checks"] + result["mass_participation_checks"]:
            self.assertTrue(chk["compliant"])

    def test_frequency_violation_makes_overall_not_compliant(self):
        modes = [
            _make_mode("m1", 8.0, lateral_x=0.95),
        ]
        reqs = {"lateral_x": 10.0}
        result = ma.verify_modal_analysis(modes, reqs, mass_participation_threshold=0.90)
        self.assertFalse(result["compliant"])
        freq_check = result["frequency_checks"][0]
        self.assertFalse(freq_check["compliant"])

    def test_mass_participation_failure_makes_overall_not_compliant(self):
        modes = [_make_mode("m1", 15.0, axial_z=0.3)]
        reqs = {"axial_z": 10.0}
        result = ma.verify_modal_analysis(modes, reqs, mass_participation_threshold=0.90)
        self.assertFalse(result["compliant"])
        mass_check = result["mass_participation_checks"][0]
        self.assertFalse(mass_check["compliant"])

    def test_invalid_axis_in_requirements_raises(self):
        modes = [_make_mode("m1", 10.0, lateral_x=0.9)]
        with self.assertRaises(ValueError):
            ma.verify_modal_analysis(modes, {"diagonal_d": 10.0})

    def test_empty_modes_produces_no_effective_mass_issue(self):
        reqs = {"axial_z": 35.0}
        result = ma.verify_modal_analysis([], reqs)
        self.assertFalse(result["compliant"])
        freq_check = result["frequency_checks"][0]
        self.assertEqual(freq_check["issue"], "no_mode_with_effective_mass_in_axis")


if __name__ == "__main__":
    unittest.main()
