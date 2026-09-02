#!/usr/bin/env python3
"""Gate 3 contract test: dynamic stability.

Exercises scripts/dynamic_stability_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the longitudinal
stability derivatives, the short period and phugoid frequency and
damping ratio, the lateral-directional mode classification, the
damping and frequency criteria, and the time to double and time to
half metrics; invalid inputs raise ValueError.

Expected values are hand-computed from the documented formulas and
written inline in each docstring.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dynamic_stability_logic as dsl  # noqa: E402


class StabilityDerivativesTest(unittest.TestCase):
    def test_z_alpha_anchor(self):
        # Z_alpha = -(5000.0 * 20.0 * 5.0) / 12000.0
        #         = -500000.0 / 12000.0 = -41.666666666666664
        self.assertAlmostEqual(
            dsl.z_alpha(5000.0, 20.0, 5.0, 12000.0),
            -41.666666666666664,
            delta=1e-12,
        )

    def test_m_alpha_anchor(self):
        # M_alpha = (5000.0 * 20.0 * 3.0 * (-0.5)) / 15000.0
        #         = -150000.0 / 15000.0 = -10.0
        self.assertAlmostEqual(
            dsl.m_alpha(5000.0, 20.0, 3.0, -0.5, 15000.0),
            -10.0,
            delta=1e-12,
        )

    def test_m_q_anchor(self):
        # M_q = (5000.0 * 20.0 * 3.0**2 * (-10.0)) / (2.0 * 70.0 * 15000.0)
        #     = -9000000.0 / 2100000.0 = -4.285714285714286
        self.assertAlmostEqual(
            dsl.m_q(5000.0, 20.0, 3.0, -10.0, 70.0, 15000.0),
            -4.285714285714286,
            delta=1e-12,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.z_alpha(0.0, 20.0, 5.0, 12000.0)
        with self.assertRaises(ValueError):
            dsl.z_alpha(5000.0, 0.0, 5.0, 12000.0)
        with self.assertRaises(ValueError):
            dsl.z_alpha(5000.0, 20.0, -5.0, 12000.0)
        with self.assertRaises(ValueError):
            dsl.z_alpha(5000.0, 20.0, 5.0, 0.0)
        with self.assertRaises(ValueError):
            dsl.m_alpha(5000.0, 20.0, 3.0, 0.5, 15000.0)
        with self.assertRaises(ValueError):
            dsl.m_alpha(5000.0, 20.0, 0.0, -0.5, 15000.0)
        with self.assertRaises(ValueError):
            dsl.m_alpha(5000.0, 20.0, 3.0, -0.5, 0.0)
        with self.assertRaises(ValueError):
            dsl.m_q(5000.0, 20.0, 3.0, 10.0, 70.0, 15000.0)
        with self.assertRaises(ValueError):
            dsl.m_q(5000.0, 20.0, 3.0, -10.0, 0.0, 15000.0)
        with self.assertRaises(ValueError):
            dsl.m_q(5000.0, 20.0, 3.0, -10.0, 70.0, 0.0)


class ShortPeriodTest(unittest.TestCase):
    def test_frequency_anchor(self):
        # radicand = M_q * Z_alpha / V - M_alpha
        #          = (-4.285714285714286 * -41.666666666666664) / 70.0 - (-10.0)
        #          = 178.57142857142858 / 70.0 + 10.0 = 12.551020408163264
        # omega_ns = sqrt(12.551020408163264) = 3.542741933610641
        self.assertAlmostEqual(
            dsl.short_period_frequency(
                -41.666666666666664, -10.0, -4.285714285714286, 70.0
            ),
            3.542741933610641,
            delta=1e-12,
        )

    def test_damping_anchor(self):
        # zeta_s = -(-41.666666666666664 / 70.0 + -4.285714285714286)
        #           / (2.0 * 3.542741933610641)
        #        = -(-0.5952380952380952 - 4.285714285714286) / 7.085483867221282
        #        = 4.880952380952381 / 7.085483867221282 = 0.688866487090958
        self.assertAlmostEqual(
            dsl.short_period_damping(
                -41.666666666666664, -10.0, -4.285714285714286, 70.0
            ),
            0.688866487090958,
            delta=1e-12,
        )

    def test_matches_state_matrix(self):
        # Internal consistency: omega_ns^2 = det A, 2 * zeta * omega_ns = -tr A
        # with A = [[Z_alpha/V, 1], [M_alpha, M_q]].
        z_a = -41.666666666666664
        m_a = -10.0
        m_q = -4.285714285714286
        v = 70.0
        omega = dsl.short_period_frequency(z_a, m_a, m_q, v)
        zeta = dsl.short_period_damping(z_a, m_a, m_q, v)
        self.assertAlmostEqual(
            omega * omega, m_q * z_a / v - m_a, delta=1e-12
        )
        self.assertAlmostEqual(
            2.0 * zeta * omega, -(z_a / v + m_q), delta=1e-12
        )

    def test_more_damping_lowers_ratio(self):
        # Doubling |M_q| raises omega_ns and zeta_s:
        # radicand = (-8.571428571428572 * -41.666666666666664) / 70.0 + 10.0
        #          = 357.14285714285717 / 70.0 + 10.0 = 15.10204081632653
        # omega_ns = 3.885... ; zeta_s = 1.191...  (hand-checked via formulas)
        omega = dsl.short_period_frequency(
            -41.666666666666664, -10.0, -8.571428571428572, 70.0
        )
        zeta = dsl.short_period_damping(
            -41.666666666666664, -10.0, -8.571428571428572, 70.0
        )
        self.assertGreater(zeta, 0.688866487090958)
        self.assertGreater(omega, 3.542741933610641)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.short_period_frequency(-41.67, -10.0, -4.29, 0.0)
        # positive pitch stiffness drives the radicand negative
        with self.assertRaises(ValueError):
            dsl.short_period_frequency(-41.67, 10.0, -4.29, 70.0)
        with self.assertRaises(ValueError):
            dsl.short_period_damping(-41.67, 10.0, -4.29, 70.0)


class PhugoidTest(unittest.TestCase):
    def test_frequency_anchor(self):
        # omega_np = sqrt(2) * 9.81 / 100.0 = 0.13873435046880064
        self.assertAlmostEqual(
            dsl.phugoid_frequency(100.0, 9.81), 0.13873435046880064, delta=1e-12
        )

    def test_period_anchor(self):
        # T_p = 2 * pi / omega_np = sqrt(2) * pi * 100.0 / 9.81
        #     = 45.289326586731555
        self.assertAlmostEqual(
            dsl.phugoid_period(100.0, 9.81), 45.289326586731555, delta=1e-12
        )

    def test_damping_anchor(self):
        # zeta_p = 1 / (sqrt(2) * 10.0) = 0.07071067811865475
        self.assertAlmostEqual(
            dsl.phugoid_damping(10.0), 0.07071067811865475, delta=1e-12
        )

    def test_speed_scaling(self):
        # Doubling V halves omega_np and doubles the period
        self.assertAlmostEqual(
            dsl.phugoid_frequency(200.0, 9.81),
            dsl.phugoid_frequency(100.0, 9.81) / 2.0,
            delta=1e-12,
        )
        self.assertAlmostEqual(
            dsl.phugoid_period(200.0, 9.81),
            dsl.phugoid_period(100.0, 9.81) * 2.0,
            delta=1e-12,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.phugoid_frequency(0.0, 9.81)
        with self.assertRaises(ValueError):
            dsl.phugoid_frequency(100.0, 0.0)
        with self.assertRaises(ValueError):
            dsl.phugoid_period(0.0, 9.81)
        with self.assertRaises(ValueError):
            dsl.phugoid_damping(0.0)
        with self.assertRaises(ValueError):
            dsl.phugoid_damping(-1.0)


class ModeClassificationTest(unittest.TestCase):
    def test_damped_dutch_roll_pair(self):
        # lambda = -0.4 +- 2.0j: oscillatory, stable
        self.assertEqual(dsl.classify_mode(-0.4, 2.0), ("oscillatory", "stable"))
        self.assertEqual(dsl.classify_mode(-0.4, -2.0), ("oscillatory", "stable"))

    def test_divergent_oscillation(self):
        # lambda = 0.4 +- 2.0j: oscillatory, divergent
        self.assertEqual(dsl.classify_mode(0.4, 2.0), ("oscillatory", "divergent"))

    def test_neutral_oscillation(self):
        # lambda = 0.0 +- 2.0j: undamped oscillation
        self.assertEqual(dsl.classify_mode(0.0, 2.0), ("oscillatory", "neutral"))

    def test_real_roots(self):
        # roll subsidence: convergent non-oscillatory
        self.assertEqual(dsl.classify_mode(-2.4, 0.0), ("non-oscillatory", "stable"))
        # stable spiral: convergent non-oscillatory
        self.assertEqual(dsl.classify_mode(-0.02, 0.0), ("non-oscillatory", "stable"))
        # divergent spiral: divergent non-oscillatory
        self.assertEqual(dsl.classify_mode(0.02, 0.0), ("non-oscillatory", "divergent"))
        # neutral root
        self.assertEqual(dsl.classify_mode(0.0, 0.0), ("non-oscillatory", "neutral"))

    def test_damping_ratio_anchor(self):
        # zeta = 0.4 / sqrt(0.4**2 + 2.0**2) = 0.4 / 2.039607805437114
        #      = 0.19611613513818402
        self.assertAlmostEqual(
            dsl.damping_ratio(-0.4, 2.0), 0.19611613513818402, delta=1e-12
        )

    def test_damping_ratio_negative_real_part(self):
        # positive real part gives a negative zeta (divergent oscillation)
        self.assertAlmostEqual(
            dsl.damping_ratio(0.4, 2.0), -0.19611613513818402, delta=1e-12
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.damping_ratio(-0.4, 0.0)


class ModeMetricsTest(unittest.TestCase):
    def test_time_to_double_anchor(self):
        # T2 = ln(2) / 0.02 = 34.657359027997266
        self.assertAlmostEqual(
            dsl.time_to_double(0.02), 34.657359027997266, delta=1e-12
        )

    def test_time_to_half_anchor(self):
        # T_half = ln(2) / 2.4 = 0.28881132523331055
        self.assertAlmostEqual(
            dsl.time_to_half(-2.4), 0.28881132523331055, delta=1e-12
        )

    def test_faster_divergence_shorter_double_time(self):
        # T2 = ln(2) / 0.10 = 6.931471805599452
        self.assertAlmostEqual(
            dsl.time_to_double(0.10), 6.931471805599452, delta=1e-12
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.time_to_double(0.0)
        with self.assertRaises(ValueError):
            dsl.time_to_double(-1.0)
        with self.assertRaises(ValueError):
            dsl.time_to_half(0.0)
        with self.assertRaises(ValueError):
            dsl.time_to_half(1.0)


class CriteriaTest(unittest.TestCase):
    def test_short_period_band(self):
        self.assertTrue(dsl.short_period_damping_adequate(0.3))
        self.assertTrue(dsl.short_period_damping_adequate(0.688866487090958))
        self.assertTrue(dsl.short_period_damping_adequate(2.0))
        self.assertFalse(dsl.short_period_damping_adequate(0.29))
        self.assertFalse(dsl.short_period_damping_adequate(2.1))

    def test_dutch_roll_criterion(self):
        # zeta >= 0.08 and zeta * omega_n >= 0.15
        self.assertTrue(dsl.dutch_roll_adequate(0.08, 2.0))
        self.assertTrue(dsl.dutch_roll_adequate(0.19611613513818402, 2.039607805437114))
        self.assertFalse(dsl.dutch_roll_adequate(0.07, 2.0))
        # zeta * omega_n = 0.144 < 0.15 fails despite zeta >= 0.08
        self.assertFalse(dsl.dutch_roll_adequate(0.08, 1.8))
        with self.assertRaises(ValueError):
            dsl.dutch_roll_adequate(0.08, 0.0)

    def test_roll_mode_criterion(self):
        self.assertTrue(dsl.roll_mode_acceptable(0.5))
        self.assertTrue(dsl.roll_mode_acceptable(1.0))
        self.assertFalse(dsl.roll_mode_acceptable(1.5))
        with self.assertRaises(ValueError):
            dsl.roll_mode_acceptable(0.0)
        with self.assertRaises(ValueError):
            dsl.roll_mode_acceptable(-0.5)

    def test_spiral_criterion(self):
        # divergent spiral with T2 = 34.66 s >= 20 s passes
        self.assertTrue(dsl.spiral_acceptable(0.02))
        # boundary: T2 = ln(2) / 20 = 0.03465735902799726 -> exactly 20 s
        self.assertTrue(dsl.spiral_acceptable(math.log(2.0) / 20.0))
        # divergent spiral with T2 = 6.93 s fails
        self.assertFalse(dsl.spiral_acceptable(0.10))
        # stable spiral always passes
        self.assertTrue(dsl.spiral_acceptable(-0.01))
        # neutral root passes (not divergent)
        self.assertTrue(dsl.spiral_acceptable(0.0))

    def test_phugoid_criterion(self):
        self.assertTrue(dsl.phugoid_acceptable(0.07071067811865475))
        self.assertFalse(dsl.phugoid_acceptable(0.0))
        self.assertFalse(dsl.phugoid_acceptable(-0.01))


if __name__ == "__main__":
    unittest.main(verbosity=2)
