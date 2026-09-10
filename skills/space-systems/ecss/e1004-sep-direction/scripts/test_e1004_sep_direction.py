#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2.2.5 directional
solar particle flux.

Exercises scripts/e1004_sep_direction_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the Parker
spiral angle grows as solar wind speed falls and a non-positive speed
raises; a source heliolongitude within tolerance of the spiral angle
is well connected, otherwise poorly connected, and a negative
tolerance raises; elapsed time below the onset window is anisotropic
onset, at or above it is quasi-isotropic diffusive, and a negative
elapsed time raises; cone angle geometry wraps and returns the
smaller angular separation; the anisotropy factor is 1.0 for the
diffusive phase, peaks at the peak ratio on-axis and decays with cone
angle for the onset phase (floored, never below the floor), and an
out-of-range cone angle, unrecognized phase, or missing/sub-1.0 peak
ratio for the onset phase raises; directional flux multiplies the
omni-equivalent flux by that factor and a negative omni flux raises;
cone angle sorts into the three entry channels at the stated
boundaries, and an out-of-range cone angle raises; only the
field-aligned channel skips the Stormer cutoff-rigidity gate, and an
unrecognized channel raises; a case's violation list flags a missing
cone angle or peak ratio during onset and a missing cutoff-rigidity
check for a non-field-aligned channel; compliance is true only when
the violation list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_sep_direction_logic as sd  # noqa: E402


class ParkerSpiralAngleTest(unittest.TestCase):
    def test_nominal_speed_near_45_degrees(self):
        angle = sd.parker_spiral_angle_deg(400.0)
        self.assertGreater(angle, 40.0)
        self.assertLess(angle, 55.0)

    def test_slower_wind_winds_tighter_larger_angle(self):
        slow = sd.parker_spiral_angle_deg(300.0)
        fast = sd.parker_spiral_angle_deg(600.0)
        self.assertGreater(slow, fast)

    def test_zero_speed_raises(self):
        with self.assertRaises(ValueError):
            sd.parker_spiral_angle_deg(0.0)

    def test_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            sd.parker_spiral_angle_deg(-100.0)


class ClassifyMagneticConnectionTest(unittest.TestCase):
    def test_source_at_spiral_angle_is_well_connected(self):
        spiral = sd.parker_spiral_angle_deg(400.0)
        self.assertEqual(
            sd.classify_magnetic_connection(spiral, 400.0), "well_connected"
        )

    def test_source_far_from_spiral_angle_is_poorly_connected(self):
        spiral = sd.parker_spiral_angle_deg(400.0)
        self.assertEqual(
            sd.classify_magnetic_connection(spiral + 90.0, 400.0), "poorly_connected"
        )

    def test_within_tolerance_boundary_is_well_connected(self):
        spiral = sd.parker_spiral_angle_deg(400.0)
        self.assertEqual(
            sd.classify_magnetic_connection(spiral + 20.0, 400.0, tolerance_deg=20.0),
            "well_connected",
        )

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            sd.classify_magnetic_connection(45.0, 400.0, tolerance_deg=-1.0)


class ClassifyArrivalPhaseTest(unittest.TestCase):
    def test_zero_hours_is_anisotropic_onset(self):
        self.assertEqual(sd.classify_arrival_phase(0.0), sd.ANISOTROPIC_ONSET)

    def test_just_below_window_is_anisotropic_onset(self):
        self.assertEqual(
            sd.classify_arrival_phase(sd.ONSET_ANISOTROPIC_MAX_HR - 0.01),
            sd.ANISOTROPIC_ONSET,
        )

    def test_at_window_boundary_is_isotropic_diffusive(self):
        self.assertEqual(
            sd.classify_arrival_phase(sd.ONSET_ANISOTROPIC_MAX_HR),
            sd.ISOTROPIC_DIFFUSIVE,
        )

    def test_well_past_window_is_isotropic_diffusive(self):
        self.assertEqual(sd.classify_arrival_phase(200.0), sd.ISOTROPIC_DIFFUSIVE)

    def test_negative_hours_raises(self):
        with self.assertRaises(ValueError):
            sd.classify_arrival_phase(-1.0)


class ConeAngleBetweenTest(unittest.TestCase):
    def test_identical_directions_zero(self):
        self.assertAlmostEqual(sd.cone_angle_between(45.0, 45.0), 0.0)

    def test_simple_separation(self):
        self.assertAlmostEqual(sd.cone_angle_between(10.0, 70.0), 60.0)

    def test_wraps_across_zero(self):
        self.assertAlmostEqual(sd.cone_angle_between(350.0, 10.0), 20.0)

    def test_opposite_directions_is_180(self):
        self.assertAlmostEqual(sd.cone_angle_between(0.0, 180.0), 180.0)

    def test_normalizes_out_of_range_inputs(self):
        self.assertAlmostEqual(sd.cone_angle_between(370.0, -10.0), 20.0)


class AnisotropyFactorTest(unittest.TestCase):
    def test_isotropic_diffusive_always_one(self):
        self.assertEqual(
            sd.anisotropy_factor(0.0, sd.ISOTROPIC_DIFFUSIVE), 1.0
        )
        self.assertEqual(
            sd.anisotropy_factor(180.0, sd.ISOTROPIC_DIFFUSIVE), 1.0
        )

    def test_onset_on_axis_peaks_at_ratio(self):
        factor = sd.anisotropy_factor(0.0, sd.ANISOTROPIC_ONSET, peak_anisotropy_ratio=5.0)
        self.assertAlmostEqual(factor, 5.0)

    def test_onset_perpendicular_is_below_peak(self):
        factor = sd.anisotropy_factor(90.0, sd.ANISOTROPIC_ONSET, peak_anisotropy_ratio=5.0)
        self.assertLess(factor, 5.0)

    def test_onset_floored_not_below_minimum(self):
        factor = sd.anisotropy_factor(180.0, sd.ANISOTROPIC_ONSET, peak_anisotropy_ratio=5.0)
        self.assertEqual(factor, sd.MIN_ANISOTROPY_FACTOR)

    def test_cone_angle_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            sd.anisotropy_factor(200.0, sd.ISOTROPIC_DIFFUSIVE)

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            sd.anisotropy_factor(0.0, "sideways_phase")

    def test_onset_missing_ratio_raises(self):
        with self.assertRaises(ValueError):
            sd.anisotropy_factor(0.0, sd.ANISOTROPIC_ONSET)

    def test_onset_sub_one_ratio_raises(self):
        with self.assertRaises(ValueError):
            sd.anisotropy_factor(0.0, sd.ANISOTROPIC_ONSET, peak_anisotropy_ratio=0.5)


class DirectionalFluxTest(unittest.TestCase):
    def test_onset_on_axis_scales_up(self):
        flux = sd.directional_flux(10.0, 0.0, 1.0, peak_anisotropy_ratio=4.0)
        self.assertAlmostEqual(flux, 40.0)

    def test_diffusive_phase_unscaled(self):
        flux = sd.directional_flux(10.0, 90.0, 100.0)
        self.assertAlmostEqual(flux, 10.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            sd.directional_flux(-1.0, 0.0, 1.0, peak_anisotropy_ratio=4.0)


class EntryChannelForConeAngleTest(unittest.TestCase):
    def test_small_angle_is_field_aligned(self):
        self.assertEqual(
            sd.entry_channel_for_cone_angle(10.0), sd.FIELD_ALIGNED_POLAR_ACCESS
        )

    def test_boundary_is_field_aligned(self):
        self.assertEqual(
            sd.entry_channel_for_cone_angle(sd.FIELD_ALIGNED_CONE_ANGLE_MAX_DEG),
            sd.FIELD_ALIGNED_POLAR_ACCESS,
        )

    def test_mid_angle_is_oblique(self):
        self.assertEqual(
            sd.entry_channel_for_cone_angle(45.0), sd.OBLIQUE_TRANSITIONAL
        )

    def test_large_angle_is_quasi_perpendicular(self):
        self.assertEqual(
            sd.entry_channel_for_cone_angle(90.0), sd.QUASI_PERPENDICULAR_ACCESS
        )

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            sd.entry_channel_for_cone_angle(-5.0)


class RequiresStormerCutoffCheckTest(unittest.TestCase):
    def test_field_aligned_does_not_require_check(self):
        self.assertFalse(
            sd.requires_stormer_cutoff_check(sd.FIELD_ALIGNED_POLAR_ACCESS)
        )

    def test_oblique_requires_check(self):
        self.assertTrue(
            sd.requires_stormer_cutoff_check(sd.OBLIQUE_TRANSITIONAL)
        )

    def test_quasi_perpendicular_requires_check(self):
        self.assertTrue(
            sd.requires_stormer_cutoff_check(sd.QUASI_PERPENDICULAR_ACCESS)
        )

    def test_unrecognized_channel_raises(self):
        with self.assertRaises(ValueError):
            sd.requires_stormer_cutoff_check("sideways_channel")


class DirectionalCaseViolationsTest(unittest.TestCase):
    def test_fully_specified_onset_case_no_violations(self):
        case = {
            "case_id": "sep-1",
            "hours_since_onset": 2.0,
            "cone_angle_deg": 10.0,
            "peak_anisotropy_ratio": 4.0,
            "stormer_cutoff_checked": True,
        }
        violations = sd.directional_case_violations(case)
        self.assertEqual(violations, [])
        self.assertTrue(sd.is_directional_compliant(violations))

    def test_onset_missing_cone_angle_and_ratio_flagged(self):
        case = {
            "case_id": "sep-2",
            "hours_since_onset": 1.0,
            "cone_angle_deg": None,
            "peak_anisotropy_ratio": None,
            "stormer_cutoff_checked": False,
        }
        violations = sd.directional_case_violations(case)
        issues = {v["issue"] for v in violations}
        self.assertIn("missing_cone_angle_for_anisotropic_case", issues)
        self.assertIn("missing_peak_anisotropy_ratio", issues)
        self.assertFalse(sd.is_directional_compliant(violations))

    def test_diffusive_phase_does_not_require_cone_angle_or_ratio(self):
        case = {
            "case_id": "sep-3",
            "hours_since_onset": 100.0,
            "cone_angle_deg": None,
            "peak_anisotropy_ratio": None,
            "stormer_cutoff_checked": False,
        }
        violations = sd.directional_case_violations(case)
        self.assertEqual(violations, [])

    def test_non_field_aligned_channel_without_cutoff_check_flagged(self):
        case = {
            "case_id": "sep-4",
            "hours_since_onset": 100.0,
            "cone_angle_deg": 90.0,
            "peak_anisotropy_ratio": None,
            "stormer_cutoff_checked": False,
        }
        violations = sd.directional_case_violations(case)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_stormer_cutoff_check")
        self.assertEqual(violations[0]["entry_channel"], sd.QUASI_PERPENDICULAR_ACCESS)

    def test_field_aligned_channel_never_needs_cutoff_check(self):
        case = {
            "case_id": "sep-5",
            "hours_since_onset": 100.0,
            "cone_angle_deg": 5.0,
            "peak_anisotropy_ratio": None,
            "stormer_cutoff_checked": False,
        }
        violations = sd.directional_case_violations(case)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
