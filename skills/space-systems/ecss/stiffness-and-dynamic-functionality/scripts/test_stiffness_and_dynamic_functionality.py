#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clauses 4.3.5-4.3.6 stiffness,
alignment stability, and dynamic-behaviour (frequency separation)
assessment.

Exercises scripts/stiffness_and_dynamic_functionality_logic.py (stdlib
unittest, offline). Contract: the fundamental natural frequency on each
axis is compared against the minimum required and a shortfall is flagged;
an unrecognized axis or a non-positive frequency raises; the fractional
frequency separation margin between a structural mode and an excitation
frequency is computed correctly and a margin below the required threshold
is flagged; a non-positive excitation frequency raises; the modal
effective mass fraction in each direction is compared against the
required coverage and a shortfall is flagged; an unrecognized direction
or a fraction outside [0, 1] raises; alignment drift at a structural
interface is compared against the allowable and an exceedance is flagged;
a negative drift or non-positive allowable raises; the full review
aggregates all four categories and the compliance helper returns true
only when all four are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stiffness_and_dynamic_functionality_logic as sd  # noqa: E402


class TestFundamentalFrequency(unittest.TestCase):
    def test_axial_freq_meets_minimum(self):
        self.assertEqual(
            sd.check_fundamental_frequency("axial", 35.0, 30.0), []
        )

    def test_lateral_freq_meets_minimum(self):
        self.assertEqual(
            sd.check_fundamental_frequency("lateral", 12.0, 10.0), []
        )

    def test_axial_freq_exactly_at_minimum_passes(self):
        self.assertEqual(
            sd.check_fundamental_frequency("axial", 30.0, 30.0), []
        )

    def test_axial_freq_below_minimum_flagged(self):
        violations = sd.check_fundamental_frequency("axial", 25.0, 30.0)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["issue"], "fundamental_frequency_below_minimum")
        self.assertEqual(v["axis"], "axial")
        self.assertAlmostEqual(v["shortfall_hz"], 5.0)

    def test_lateral_freq_below_minimum_flagged(self):
        violations = sd.check_fundamental_frequency("lateral", 8.0, 10.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "fundamental_frequency_below_minimum")

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            sd.check_fundamental_frequency("diagonal", 20.0, 15.0)

    def test_non_positive_fundamental_freq_raises(self):
        with self.assertRaises(ValueError):
            sd.check_fundamental_frequency("axial", 0.0, 30.0)

    def test_non_positive_minimum_freq_raises(self):
        with self.assertRaises(ValueError):
            sd.check_fundamental_frequency("axial", 30.0, -5.0)

    def test_rotational_axis_accepted(self):
        self.assertEqual(
            sd.check_fundamental_frequency("rotational", 50.0, 40.0), []
        )


class TestFrequencySeparationMargin(unittest.TestCase):
    def test_structure_above_excitation_positive_margin(self):
        margin = sd.compute_frequency_separation_margin(110.0, 100.0)
        self.assertAlmostEqual(margin, 0.10)

    def test_structure_below_excitation_negative_margin(self):
        margin = sd.compute_frequency_separation_margin(90.0, 100.0)
        self.assertAlmostEqual(margin, -0.10)

    def test_structure_equal_excitation_zero_margin(self):
        margin = sd.compute_frequency_separation_margin(100.0, 100.0)
        self.assertAlmostEqual(margin, 0.0)

    def test_non_positive_excitation_raises(self):
        with self.assertRaises(ValueError):
            sd.compute_frequency_separation_margin(100.0, 0.0)

    def test_non_positive_structure_freq_raises(self):
        with self.assertRaises(ValueError):
            sd.compute_frequency_separation_margin(-5.0, 100.0)


class TestFrequencySeparationCheck(unittest.TestCase):
    def test_margin_above_required_passes(self):
        self.assertEqual(
            sd.check_frequency_separation("mode-1", 120.0, 100.0, 0.15), []
        )

    def test_margin_exactly_at_required_passes(self):
        self.assertEqual(
            sd.check_frequency_separation("mode-1", 115.0, 100.0, 0.15), []
        )

    def test_margin_below_required_flagged(self):
        violations = sd.check_frequency_separation("mode-2", 105.0, 100.0, 0.15)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["issue"], "insufficient_frequency_separation")
        self.assertEqual(v["mode_id"], "mode-2")
        self.assertAlmostEqual(v["computed_margin"], 0.05)
        self.assertAlmostEqual(v["required_margin"], 0.15)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            sd.check_frequency_separation("mode-1", 110.0, 100.0, -0.05)

    def test_structural_freq_below_excitation_flagged(self):
        violations = sd.check_frequency_separation("mode-3", 85.0, 100.0, 0.10)
        self.assertEqual(len(violations), 1)
        self.assertLess(violations[0]["computed_margin"], 0)


class TestModalMassFraction(unittest.TestCase):
    def test_fraction_meets_default_requirement(self):
        self.assertEqual(sd.check_modal_mass_fraction("x", 0.92), [])

    def test_fraction_exactly_at_required_passes(self):
        self.assertEqual(sd.check_modal_mass_fraction("y", 0.90), [])

    def test_fraction_below_required_flagged(self):
        violations = sd.check_modal_mass_fraction("z", 0.82)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["issue"], "insufficient_modal_mass_fraction")
        self.assertEqual(v["direction"], "z")
        self.assertAlmostEqual(v["shortfall"], 0.08)

    def test_custom_required_fraction_respected(self):
        self.assertEqual(sd.check_modal_mass_fraction("x", 0.85, required_fraction=0.80), [])

    def test_invalid_direction_raises(self):
        with self.assertRaises(ValueError):
            sd.check_modal_mass_fraction("w", 0.95)

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            sd.check_modal_mass_fraction("x", 1.05)

    def test_fraction_below_zero_raises(self):
        with self.assertRaises(ValueError):
            sd.check_modal_mass_fraction("x", -0.1)

    def test_zero_required_fraction_raises(self):
        with self.assertRaises(ValueError):
            sd.check_modal_mass_fraction("x", 0.5, required_fraction=0.0)


class TestAlignmentStability(unittest.TestCase):
    def test_drift_within_allowable_passes(self):
        self.assertEqual(sd.check_alignment_stability("optical-bench", 3.0, 5.0), [])

    def test_drift_exactly_at_allowable_passes(self):
        self.assertEqual(sd.check_alignment_stability("reflector", 5.0, 5.0), [])

    def test_drift_exceeds_allowable_flagged(self):
        violations = sd.check_alignment_stability("antenna", 7.5, 5.0)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["issue"], "alignment_stability_exceeded")
        self.assertEqual(v["component_id"], "antenna")
        self.assertAlmostEqual(v["excess_arcsec"], 2.5)

    def test_negative_drift_raises(self):
        with self.assertRaises(ValueError):
            sd.check_alignment_stability("sensor-mount", -1.0, 5.0)

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(ValueError):
            sd.check_alignment_stability("sensor-mount", 1.0, 0.0)


class TestStiffnessDynamicReview(unittest.TestCase):
    def test_fully_compliant_review(self):
        assessment = {
            "structure_id": "primary-panel",
            "fundamental_frequencies": [
                {"axis": "axial", "freq_hz": 35.0, "minimum_hz": 30.0},
                {"axis": "lateral", "freq_hz": 12.0, "minimum_hz": 10.0},
            ],
            "frequency_separation_checks": [
                {
                    "mode_id": "mode-1",
                    "structure_freq_hz": 120.0,
                    "excitation_freq_hz": 100.0,
                    "required_margin": 0.15,
                }
            ],
            "modal_mass_fractions": [
                {"direction": "x", "fraction": 0.93, "required_fraction": 0.90},
                {"direction": "y", "fraction": 0.91, "required_fraction": 0.90},
                {"direction": "z", "fraction": 0.95, "required_fraction": 0.90},
            ],
            "alignment_checks": [
                {"component_id": "optical-bench", "error_arcsec": 2.0, "allowable_arcsec": 5.0}
            ],
        }
        review = sd.stiffness_dynamic_review(assessment)
        self.assertEqual(review["fundamental_frequency"], [])
        self.assertEqual(review["frequency_separation"], [])
        self.assertEqual(review["modal_mass"], [])
        self.assertEqual(review["alignment"], [])
        self.assertTrue(sd.is_stiffness_dynamic_compliant(review))

    def test_review_with_multiple_violations(self):
        assessment = {
            "structure_id": "antenna-boom",
            "fundamental_frequencies": [
                {"axis": "lateral", "freq_hz": 7.0, "minimum_hz": 10.0},
            ],
            "frequency_separation_checks": [
                {
                    "mode_id": "mode-2",
                    "structure_freq_hz": 103.0,
                    "excitation_freq_hz": 100.0,
                    "required_margin": 0.15,
                }
            ],
            "modal_mass_fractions": [
                {"direction": "z", "fraction": 0.75, "required_fraction": 0.90},
            ],
            "alignment_checks": [
                {"component_id": "feed-arm", "error_arcsec": 8.0, "allowable_arcsec": 5.0}
            ],
        }
        review = sd.stiffness_dynamic_review(assessment)
        self.assertEqual(len(review["fundamental_frequency"]), 1)
        self.assertEqual(len(review["frequency_separation"]), 1)
        self.assertEqual(len(review["modal_mass"]), 1)
        self.assertEqual(len(review["alignment"]), 1)
        self.assertFalse(sd.is_stiffness_dynamic_compliant(review))

    def test_review_empty_sections_are_compliant(self):
        assessment = {"structure_id": "bracket"}
        review = sd.stiffness_dynamic_review(assessment)
        self.assertTrue(sd.is_stiffness_dynamic_compliant(review))

    def test_is_compliant_false_when_any_category_has_violation(self):
        assessment = {
            "structure_id": "strut",
            "fundamental_frequencies": [
                {"axis": "axial", "freq_hz": 20.0, "minimum_hz": 30.0},
            ],
            "frequency_separation_checks": [],
            "modal_mass_fractions": [],
            "alignment_checks": [],
        }
        review = sd.stiffness_dynamic_review(assessment)
        self.assertFalse(sd.is_stiffness_dynamic_compliant(review))


if __name__ == "__main__":
    unittest.main()
