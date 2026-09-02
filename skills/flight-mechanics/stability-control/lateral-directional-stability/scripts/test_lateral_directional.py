#!/usr/bin/env python3
"""Gate 3 contract test: lateral-directional stability.

Exercises scripts/lateral_directional_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - directional
stability derivative from the vertical tail volume and fin lift slope,
the dihedral contribution to the roll stability derivative, the roll
mode time constant, the Dutch roll frequency and damping ratio, and
the spiral mode classification; invalid inputs raise ValueError.

Expected values are hand-computed from the documented formulas and
written inline in each docstring.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lateral_directional_logic as lds  # noqa: E402


class VerticalTailVolumeTest(unittest.TestCase):
    def test_anchor_value(self):
        # V_v = (S_vt * l_vt) / (S * b) = (4.0 * 8.0) / (20.0 * 12.0)
        #     = 32.0 / 240.0 = 0.13333333333333333
        self.assertAlmostEqual(
            lds.vertical_tail_volume(4.0, 8.0, 20.0, 12.0),
            0.13333333333333333,
            delta=1e-12,
        )

    def test_symmetric_units(self):
        # Doubling every dimension leaves the ratio unchanged:
        # (8.0 * 16.0) / (40.0 * 24.0) = 128.0 / 960.0 = 0.13333333333333333
        self.assertAlmostEqual(
            lds.vertical_tail_volume(8.0, 16.0, 40.0, 24.0),
            0.13333333333333333,
            delta=1e-12,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lds.vertical_tail_volume(0.0, 8.0, 20.0, 12.0)
        with self.assertRaises(ValueError):
            lds.vertical_tail_volume(4.0, -1.0, 20.0, 12.0)
        with self.assertRaises(ValueError):
            lds.vertical_tail_volume(4.0, 8.0, 0.0, 12.0)
        with self.assertRaises(ValueError):
            lds.vertical_tail_volume(4.0, 8.0, 20.0, 0.0)


class DirectionalStabilityTest(unittest.TestCase):
    def test_fin_contribution_anchor(self):
        # C_n_beta_vt = 1.0 * 0.1 * 4.0 * (1 + 0.0) = 0.4
        self.assertAlmostEqual(
            lds.cn_beta_vertical_tail(1.0, 0.1, 4.0, 0.0), 0.4, delta=1e-12
        )

    def test_fin_contribution_with_sidewash(self):
        # C_n_beta_vt = 0.8 * 0.2 * 3.0 * (1 + 0.25) = 0.48 * 1.25 = 0.6
        self.assertAlmostEqual(
            lds.cn_beta_vertical_tail(0.8, 0.2, 3.0, 0.25), 0.6, delta=1e-12
        )

    def test_total_with_fuselage(self):
        # 0.6 + (-0.2) = 0.4, the fuselage term is destabilizing
        self.assertAlmostEqual(
            lds.cn_beta_total(0.6, -0.2), 0.4, delta=1e-12
        )

    def test_directionally_stable_verdicts(self):
        self.assertTrue(lds.directionally_stable(0.4))
        self.assertFalse(lds.directionally_stable(-0.05))
        self.assertFalse(lds.directionally_stable(0.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(0.0, 0.1, 4.0)
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(1.5, 0.1, 4.0)
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(0.8, 0.0, 4.0)
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(0.8, -0.1, 4.0)
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(0.8, 0.2, 0.0)
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(0.8, 0.2, -3.0)
        with self.assertRaises(ValueError):
            lds.cn_beta_vertical_tail(0.8, 0.2, 3.0, -0.1)


class LateralStabilityTest(unittest.TestCase):
    def test_dihedral_contribution_anchor(self):
        # gamma = radians(5.0) = 0.08726646259971647
        # C_l_beta_gamma = -0.5 * 0.08726646259971647 = -0.043633231299858236
        self.assertAlmostEqual(
            lds.cl_beta_dihedral(0.5, 5.0), -0.043633231299858236, delta=1e-12
        )

    def test_dihedral_contribution_doubles(self):
        # gamma = radians(10.0) = 0.17453292519943295
        # C_l_beta_gamma = -0.3 * 0.17453292519943295 = -0.052359877559829885
        self.assertAlmostEqual(
            lds.cl_beta_dihedral(0.3, 10.0), -0.052359877559829885, delta=1e-12
        )

    def test_anhedral_destabilizes(self):
        # Negative dihedral flips the sign: -0.5 * radians(-5.0) = +0.04363...
        self.assertAlmostEqual(
            lds.cl_beta_dihedral(0.5, -5.0), 0.043633231299858236, delta=1e-12
        )

    def test_laterally_stable_verdicts(self):
        self.assertTrue(lds.laterally_stable(-0.043633231299858236))
        self.assertFalse(lds.laterally_stable(0.02))
        self.assertFalse(lds.laterally_stable(0.0))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            lds.cl_beta_dihedral(-0.2, 5.0)


class RollModeTest(unittest.TestCase):
    def test_roll_damping_derivative_anchor(self):
        # L_p = (5000.0 * 20.0 * 12.0**2 * (-0.35)) / (2.0 * 70.0 * 15000.0)
        #     = -5040000.0 / 2100000.0 = -2.4
        self.assertAlmostEqual(
            lds.roll_damping_derivative(-0.35, 5000.0, 20.0, 12.0, 70.0, 15000.0),
            -2.4,
            delta=1e-12,
        )

    def test_roll_mode_time_constant(self):
        # tau = -1.0 / (-2.4) = 0.4166666666666667
        self.assertAlmostEqual(
            lds.roll_mode_time_constant(-2.4), 0.4166666666666667, delta=1e-12
        )

    def test_more_damping_faster_roll(self):
        # tau = -1.0 / (-4.8) = 0.20833333333333334
        self.assertAlmostEqual(
            lds.roll_mode_time_constant(-4.8), 0.20833333333333334, delta=1e-12
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lds.roll_damping_derivative(0.1, 5000.0, 20.0, 12.0, 70.0, 15000.0)
        with self.assertRaises(ValueError):
            lds.roll_damping_derivative(-0.35, 0.0, 20.0, 12.0, 70.0, 15000.0)
        with self.assertRaises(ValueError):
            lds.roll_damping_derivative(-0.35, 5000.0, 20.0, 12.0, 70.0, -1.0)
        with self.assertRaises(ValueError):
            lds.roll_mode_time_constant(0.0)
        with self.assertRaises(ValueError):
            lds.roll_mode_time_constant(2.4)


class DutchRollTest(unittest.TestCase):
    def test_frequency_anchor(self):
        # omega_n = sqrt(3.5 + ((-1.0) * (-50.0) - 3.5 * 0.0) / 100.0)
        #         = sqrt(3.5 + 0.5) = sqrt(4.0) = 2.0
        self.assertAlmostEqual(
            lds.dutch_roll_frequency(3.5, -1.0, -50.0, 0.0, 100.0),
            2.0,
            delta=1e-12,
        )

    def test_damping_ratio_anchor(self):
        # zeta = -((-50.0 / 100.0) + (-1.0)) / (2.0 * 2.0)
        #      = -(-0.5 - 1.0) / 4.0 = 1.5 / 4.0 = 0.375
        self.assertAlmostEqual(
            lds.dutch_roll_damping_ratio(3.5, -1.0, -50.0, 0.0, 100.0),
            0.375,
            delta=1e-12,
        )

    def test_weak_yaw_stiffness_lowers_frequency(self):
        # omega_n = sqrt(1.5 + 0.5) = sqrt(2.0) = 1.4142135623730951
        self.assertAlmostEqual(
            lds.dutch_roll_frequency(1.5, -1.0, -50.0, 0.0, 100.0),
            1.4142135623730951,
            delta=1e-12,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lds.dutch_roll_frequency(-2.0, -1.0, 0.0, 0.0, 100.0)
        with self.assertRaises(ValueError):
            lds.dutch_roll_frequency(3.5, -1.0, -50.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            lds.dutch_roll_damping_ratio(-2.0, -1.0, 0.0, 0.0, 100.0)
        with self.assertRaises(ValueError):
            lds.dutch_roll_damping_ratio(3.5, -1.0, -50.0, 0.0, 0.0)


class SpiralModeTest(unittest.TestCase):
    def test_stable_criterion(self):
        # L_beta * N_r - L_r * N_beta = (-2.0)(-1.0) - (0.1)(4.0)
        #     = 2.0 - 0.4 = 1.6 > 0, convergent spiral
        self.assertAlmostEqual(
            lds.spiral_stability_parameter(-2.0, 0.1, 4.0, -1.0), 1.6, delta=1e-12
        )
        self.assertTrue(lds.spiral_mode_stable(-2.0, 0.1, 4.0, -1.0))

    def test_unstable_criterion(self):
        # L_beta * N_r - L_r * N_beta = (-0.5)(-1.0) - (0.3)(4.0)
        #     = 0.5 - 1.2 = -0.7 < 0, divergent spiral
        self.assertAlmostEqual(
            lds.spiral_stability_parameter(-0.5, 0.3, 4.0, -1.0), -0.7, delta=1e-12
        )
        self.assertFalse(lds.spiral_mode_stable(-0.5, 0.3, 4.0, -1.0))

    def test_eigenvalue_anchor(self):
        # lambda_s = (9.81 / 100.0) * 1.6 / (4.0 * (-2.4))
        #          = 0.0981 * (-1.0 / 6.0) = -0.01635 = -9.81 / 600.0
        self.assertAlmostEqual(
            lds.spiral_eigenvalue(-2.0, 0.1, 4.0, -1.0, -2.4, 9.81, 100.0),
            -9.81 / 600.0,
            delta=1e-12,
        )

    def test_unstable_eigenvalue_is_positive(self):
        # lambda_s = (9.81 / 100.0) * (-0.7) / (4.0 * (-2.4)) = +0.007153125
        self.assertAlmostEqual(
            lds.spiral_eigenvalue(-0.5, 0.3, 4.0, -1.0, -2.4, 9.81, 100.0),
            0.007153125,
            delta=1e-12,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lds.spiral_eigenvalue(-2.0, 0.1, 0.0, -1.0, -2.4, 9.81, 100.0)
        with self.assertRaises(ValueError):
            lds.spiral_eigenvalue(-2.0, 0.1, 4.0, -1.0, 0.0, 9.81, 100.0)
        with self.assertRaises(ValueError):
            lds.spiral_eigenvalue(-2.0, 0.1, 4.0, -1.0, 2.4, 9.81, 100.0)
        with self.assertRaises(ValueError):
            lds.spiral_eigenvalue(-2.0, 0.1, 4.0, -1.0, -2.4, 0.0, 100.0)
        with self.assertRaises(ValueError):
            lds.spiral_eigenvalue(-2.0, 0.1, 4.0, -1.0, -2.4, 9.81, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
