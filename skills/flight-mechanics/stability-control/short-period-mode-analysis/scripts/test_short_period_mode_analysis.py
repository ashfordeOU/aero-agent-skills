#!/usr/bin/env python3
"""Gate 3 contract test: short-period mode analysis logic.

Exercises scripts/short_period_mode_analysis_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3. Covers
the dimensionless-to-dimensional stability derivative conversion, the
short-period natural frequency and damping ratio from the two-DOF
pitch model, the Level 1 flying qualities check with boundary cases
(zero damping, negative damping, unstable non-oscillatory modes),
the phugoid separation assumption, the Z_q negligibility check, and
invalid-input edge cases.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import short_period_mode_analysis_logic as spm  # noqa: E402


class DimensionlessConversionTest(unittest.TestCase):
    """Worked-example transport configuration:
    q_bar = 14000 Pa, S = 30 m^2, c_bar = 2.5 m, V = 150 m/s,
    m = 12000 kg, I_yy = 85000 kg m^2, C_Z_alpha = -5.0,
    C_Z_q = -3.0, C_m_alpha = -0.6, C_m_q = -12.0,
    C_m_alphadot = -3.0.
    """

    def test_worked_example_conversion(self):
        d = spm.dimensionless_derivative_conversion(
            14000.0, 30.0, 2.5, 150.0, 12000.0, 85000.0,
            -5.0, -3.0, -0.6, -12.0, -3.0,
        )
        self.assertAlmostEqual(d["timescale"], 2.5 / (2.0 * 150.0))
        self.assertAlmostEqual(d["z_alpha"], -175.0)
        self.assertAlmostEqual(d["z_q"], -0.875)
        self.assertAlmostEqual(d["m_alpha"], -7.411764705882353)
        self.assertAlmostEqual(d["m_q"], -1.2352941176470589)
        self.assertAlmostEqual(d["m_alphadot"], -0.3088235294117647)

    def test_timescale_scales_inversely_with_speed(self):
        d1 = spm.dimensionless_derivative_conversion(
            14000.0, 30.0, 2.5, 150.0, 12000.0, 85000.0,
            -5.0, -3.0, -0.6, -12.0, -3.0,
        )
        d2 = spm.dimensionless_derivative_conversion(
            14000.0, 30.0, 2.5, 300.0, 12000.0, 85000.0,
            -5.0, -3.0, -0.6, -12.0, -3.0,
        )
        self.assertAlmostEqual(d1["timescale"], 2.0 * d2["timescale"])
        # damping-type derivatives halve when speed doubles
        self.assertAlmostEqual(d1["m_q"], 2.0 * d2["m_q"])

    def test_unstable_sign_conventions_raise(self):
        with self.assertRaises(ValueError):
            spm.dimensionless_derivative_conversion(
                14000.0, 30.0, 2.5, 150.0, 12000.0, 85000.0,
                -5.0, -3.0, 0.6, -12.0, -3.0,
            )
        with self.assertRaises(ValueError):
            spm.dimensionless_derivative_conversion(
                14000.0, 30.0, 2.5, 150.0, 12000.0, 85000.0,
                -5.0, -3.0, -0.6, 12.0, -3.0,
            )
        with self.assertRaises(ValueError):
            spm.dimensionless_derivative_conversion(
                14000.0, 30.0, 2.5, 150.0, 12000.0, 85000.0,
                5.0, -3.0, -0.6, -12.0, -3.0,
            )

    def test_non_positive_inputs_raise(self):
        for kwargs in (
            dict(q_bar=0.0),
            dict(s=0.0),
            dict(c_bar=-1.0),
            dict(v=0.0),
            dict(mass=0.0),
            dict(i_yy=-5.0),
        ):
            base = dict(
                q_bar=14000.0, s=30.0, c_bar=2.5, v=150.0,
                mass=12000.0, i_yy=85000.0,
                c_z_alpha=-5.0, c_z_q=-3.0, c_m_alpha=-0.6,
                c_m_q=-12.0, c_m_alphadot=-3.0,
            )
            base.update(kwargs)
            with self.assertRaises(ValueError):
                spm.dimensionless_derivative_conversion(**base)


class ShortPeriodFrequencyTest(unittest.TestCase):
    def test_worked_example_frequency(self):
        omega = spm.short_period_frequency(-175.0, -7.411764705882353,
                                           -1.2352941176470589, 150.0)
        self.assertAlmostEqual(omega, 2.975389247891877, places=6)

    def test_stronger_pitch_stiffness_raises_frequency(self):
        f1 = spm.short_period_frequency(-175.0, -7.411764705882353,
                                        -1.2352941176470589, 150.0)
        f2 = spm.short_period_frequency(-175.0, -14.0,
                                        -1.2352941176470589, 150.0)
        self.assertGreater(f2, f1)

    def test_unstable_mode_radicand_raises(self):
        with self.assertRaises(ValueError):
            spm.short_period_frequency(-10.0, 0.5, -1.0, 50.0)

    def test_zero_radicand_raises(self):
        # M_q * Z_alpha / V = 0.5 and M_alpha = 0.5 -> radicand exactly 0
        with self.assertRaises(ValueError):
            spm.short_period_frequency(-50.0, 0.5, -1.0, 100.0)

    def test_non_positive_speed_raises(self):
        with self.assertRaises(ValueError):
            spm.short_period_frequency(-175.0, -7.0, -1.2, 0.0)


class ShortPeriodDampingTest(unittest.TestCase):
    def test_worked_example_damping(self):
        zeta = spm.short_period_damping(
            -175.0, -7.411764705882353, -1.2352941176470589,
            -0.3088235294117647, 150.0)
        self.assertAlmostEqual(zeta, 0.45553440035553927, places=6)

    def test_more_negative_alphadot_increases_damping(self):
        z1 = spm.short_period_damping(-175.0, -7.411764705882353,
                                      -1.2352941176470589, -0.3, 150.0)
        z2 = spm.short_period_damping(-175.0, -7.411764705882353,
                                      -1.2352941176470589, -0.6, 150.0)
        self.assertGreater(z2, z1)

    def test_zero_damping_is_undamped_oscillation(self):
        # Z_alpha / V + M_q + M_alphadot = 0 exactly
        zeta = spm.short_period_damping(-50.0, -2.0, -0.5, 1.0, 100.0)
        self.assertEqual(zeta, 0.0)

    def test_negative_damping_is_divergent_oscillation(self):
        zeta = spm.short_period_damping(-50.0, -2.0, -0.5, 2.0, 100.0)
        self.assertLess(zeta, 0.0)
        self.assertAlmostEqual(zeta, -1.0 / 3.0)

    def test_alphadot_cancels_from_frequency(self):
        omega = spm.short_period_frequency(-50.0, -2.0, -0.5, 100.0)
        self.assertAlmostEqual(omega, 1.5)


class Level1QualityCheckTest(unittest.TestCase):
    def test_level1_band_boundaries_inclusive(self):
        self.assertEqual(spm.level1_quality_check(0.35, 0.28, "A")[0], 1)
        self.assertEqual(spm.level1_quality_check(1.30, 0.28, "A")[0], 1)
        self.assertEqual(spm.level1_quality_check(0.5, 0.28, "A")[0], 1)

    def test_level2_just_outside_band(self):
        self.assertEqual(spm.level1_quality_check(0.3499, 0.28, "A")[0], 2)
        self.assertEqual(spm.level1_quality_check(1.3001, 0.28, "A")[0], 2)

    def test_level2_below_frequency_floor(self):
        self.assertEqual(spm.level1_quality_check(0.5, 0.2799, "A")[0], 2)

    def test_level3_zero_or_negative_damping(self):
        self.assertEqual(spm.level1_quality_check(0.0, 0.5, "A")[0], 3)
        self.assertEqual(spm.level1_quality_check(-0.5, 0.5, "A")[0], 3)

    def test_category_bands_differ(self):
        # 0.32 is Level 1 for B (0.30-2.00) but Level 2 for A (0.35-1.30)
        self.assertEqual(spm.level1_quality_check(0.32, 0.28, "B")[0], 1)
        self.assertEqual(spm.level1_quality_check(0.32, 0.28, "A")[0], 2)
        # B frequency floor is 0.10 rad/s
        self.assertEqual(spm.level1_quality_check(0.5, 0.10, "B")[0], 1)
        # 0.26 is Level 1 for C (0.25-2.00) but Level 2 for A
        self.assertEqual(spm.level1_quality_check(0.26, 0.28, "C")[0], 1)
        self.assertEqual(spm.level1_quality_check(0.26, 0.28, "A")[0], 2)

    def test_invalid_category_raises(self):
        with self.assertRaises(ValueError):
            spm.level1_quality_check(0.5, 0.5, "D")

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            spm.level1_quality_check(0.5, 0.0, "A")


class ShortPeriodAnalysisTest(unittest.TestCase):
    def test_stable_mode_level1(self):
        a = spm.short_period_analysis(
            -175.0, -7.411764705882353, -1.2352941176470589,
            -0.3088235294117647, 150.0, "A")
        self.assertTrue(a["stable"])
        self.assertTrue(a["oscillatory"])
        self.assertAlmostEqual(a["omega_n"], 2.975389247891877)
        self.assertAlmostEqual(a["zeta"], 0.45553440035553927)
        self.assertEqual(a["level"], 1)

    def test_unstable_mode_level3(self):
        a = spm.short_period_analysis(-10.0, 0.5, -1.0, -0.2, 50.0)
        self.assertFalse(a["stable"])
        self.assertFalse(a["oscillatory"])
        self.assertIsNone(a["omega_n"])
        self.assertIsNone(a["zeta"])
        self.assertEqual(a["level"], 3)
        self.assertTrue(a["level_reasons"])

    def test_zero_damping_level3(self):
        a = spm.short_period_analysis(-50.0, -2.0, -0.5, 1.0, 100.0)
        self.assertFalse(a["stable"])
        self.assertTrue(a["oscillatory"])
        self.assertEqual(a["zeta"], 0.0)
        self.assertEqual(a["level"], 3)

    def test_divergent_oscillation_level3(self):
        a = spm.short_period_analysis(-50.0, -2.0, -0.5, 2.0, 100.0)
        self.assertFalse(a["stable"])
        self.assertEqual(a["level"], 3)

    def test_analysis_validates_category_and_speed(self):
        with self.assertRaises(ValueError):
            spm.short_period_analysis(-175.0, -7.0, -1.2, -0.3, 0.0)
        with self.assertRaises(ValueError):
            spm.short_period_analysis(-175.0, -7.0, -1.2, -0.3, 150.0, "D")


class PhugoidSeparationTest(unittest.TestCase):
    def test_worked_example_separated(self):
        ratio, separated = spm.phugoid_separation(2.975389247891877, 150.0)
        self.assertAlmostEqual(ratio, 32.18098811297264, places=6)
        self.assertTrue(separated)

    def test_min_ratio_boundary_inclusive(self):
        # omega_nsp = omega_np * min_ratio exactly
        omega_np = math.sqrt(2.0) * 9.80665 / 100.0
        ratio, separated = spm.phugoid_separation(omega_np * 5.0, 100.0,
                                                  min_ratio=5.0)
        self.assertAlmostEqual(ratio, 5.0)
        self.assertTrue(separated)

    def test_slow_mode_not_separated(self):
        ratio, separated = spm.phugoid_separation(0.2, 100.0)
        self.assertFalse(separated)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            spm.phugoid_separation(0.0, 100.0)
        with self.assertRaises(ValueError):
            spm.phugoid_separation(2.0, 0.0)
        with self.assertRaises(ValueError):
            spm.phugoid_separation(2.0, 100.0, min_ratio=0.0)


class ZQNegligibleTest(unittest.TestCase):
    def test_worked_example_negligible(self):
        self.assertTrue(spm.z_q_negligible(-0.875, 150.0))

    def test_large_zq_not_negligible(self):
        self.assertFalse(spm.z_q_negligible(-20.0, 100.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            spm.z_q_negligible(-0.875, 0.0)
        with self.assertRaises(ValueError):
            spm.z_q_negligible(-0.875, 150.0, tol=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
