#!/usr/bin/env python3
"""Gate 3 contract test: full-order Luenberger observer design.

Exercises scripts/observer_design_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the deterministic
full-order state observer design for the plant x_dot = A x + B u,
y = C x: observability matrix O = [C; C A; ...; C A^(n-1)] and the
rank verdict, the Ackermann estimator gain L = phi(A) O^{-1} e_n that
places eig(A - L C) at the desired observer poles, the characteristic
polynomial by Faddeev-LeVerrier, the Routh-Hurwitz stability verdict,
the separation principle factorization of the output feedback closed
loop, and the 2% settling time.

Analytic checks (pinned):
  double integrator A = [[0,1],[0,0]], C = [[1,0]], poles [-4, -5]:
    O = I2, phi = s^2 + 9s + 20, L = [9, 20], A - L C = [[-9,1],[-20,0]],
    char poly [1, 9, 20] (trace -9, det 20), Hurwitz, t_s = 4/4 = 1.0 s
  complex conjugate poles [-2 +/- 3j]: phi = s^2 + 4s + 13, L = [4, 13],
    char poly [1, 4, 13], t_s = 4/2 = 2.0 s
  3x3 plant A = [[-1,0,1],[0,-2,0],[0,1,-3]], C = [[1,0,0]],
    poles [-10, -11, -12]: L = [27, 720, 216], char poly
    [1, 33, 362, 1320] = (s+10)(s+11)(s+12), Hurwitz
  separation principle with K = [1, 1] on the double integrator:
    controller poly [1, 1, 1], observer poly [1, 9, 20], closed loop
    poly [1, 10, 30, 29, 20] = their product, factorizes True
  characteristic polynomial of diag(-1, -2, -3) = [1, 6, 11, 6]
  1x1 plant A = [[-1]], C = [[1]], pole [-5]: L = [4], error pole -5
Asserted with places=4. Units: poles in rad/s, settling time in s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import observer_design_logic as od  # noqa: E402

# Pinned reference plants
A_DI = [[0.0, 1.0], [0.0, 0.0]]        # double integrator
C_DI = [[1.0, 0.0]]                    # position measured only
B_DI = [[0.0], [1.0]]                  # acceleration input
A3 = [[-1.0, 0.0, 1.0], [0.0, -2.0, 0.0], [0.0, 1.0, -3.0]]
C3 = [[1.0, 0.0, 0.0]]


class ObservabilityTest(unittest.TestCase):
    def test_double_integrator_matrix_is_identity(self):
        O = od.observability_matrix(A_DI, C_DI)
        self.assertAlmostEqual(O[0][0], 1.0, places=4)
        self.assertAlmostEqual(O[0][1], 0.0, places=4)
        self.assertAlmostEqual(O[1][0], 0.0, places=4)
        self.assertAlmostEqual(O[1][1], 1.0, places=4)

    def test_double_integrator_observable(self):
        self.assertTrue(od.is_observable(A_DI, C_DI))

    def test_position_only_measurement_not_observable(self):
        # C = [0, 1] sees only velocity: O = [[0,1],[0,0]], rank 1 < 2
        self.assertFalse(od.is_observable(A_DI, [[0.0, 1.0]]))

    def test_three_state_matrix_shape(self):
        O = od.observability_matrix(A3, C3)
        self.assertEqual(len(O), 3)
        self.assertEqual(len(O[0]), 3)
        self.assertTrue(od.is_observable(A3, C3))

    def test_width_mismatch_raises(self):
        with self.assertRaises(ValueError):
            od.observability_matrix(A_DI, [[1.0, 0.0, 0.0]])

    def test_non_numeric_entry_raises(self):
        with self.assertRaises(ValueError):
            od.observability_matrix([["a", 1.0], [0.0, 0.0]], C_DI)


class AckermannGainTest(unittest.TestCase):
    def test_double_integrator_analytic_gain(self):
        # phi(s) = s^2 + 9s + 20, O = I2: L = [9, 20]
        L = od.observer_gain_ackermann(A_DI, C_DI, [-4.0, -5.0])
        self.assertAlmostEqual(L[0], 9.0, places=4)
        self.assertAlmostEqual(L[1], 20.0, places=4)

    def test_gain_places_error_poles(self):
        L = od.observer_gain_ackermann(A_DI, C_DI, [-4.0, -5.0])
        ed = od.error_dynamics(A_DI, C_DI, L)
        self.assertEqual(len(ed["char_poly"]), 3)
        self.assertAlmostEqual(ed["char_poly"][1], 9.0, places=4)
        self.assertAlmostEqual(ed["char_poly"][2], 20.0, places=4)
        self.assertTrue(ed["stable"])

    def test_complex_conjugate_poles(self):
        # phi = s^2 + 4s + 13: L = [4, 13]
        L = od.observer_gain_ackermann(A_DI, C_DI, [-2.0 + 3.0j, -2.0 - 3.0j])
        self.assertAlmostEqual(L[0], 4.0, places=4)
        self.assertAlmostEqual(L[1], 13.0, places=4)

    def test_three_state_reference_gain(self):
        # Pinned: L = [27, 720, 216] for poles [-10, -11, -12]
        L = od.observer_gain_ackermann(A3, C3, [-10.0, -11.0, -12.0])
        self.assertAlmostEqual(L[0], 27.0, places=4)
        self.assertAlmostEqual(L[1], 720.0, places=4)
        self.assertAlmostEqual(L[2], 216.0, places=4)

    def test_three_state_error_polynomial(self):
        L = od.observer_gain_ackermann(A3, C3, [-10.0, -11.0, -12.0])
        ed = od.error_dynamics(A3, C3, L)
        # (s+10)(s+11)(s+12) = s^3 + 33 s^2 + 362 s + 1320
        self.assertAlmostEqual(ed["char_poly"][0], 1.0, places=4)
        self.assertAlmostEqual(ed["char_poly"][1], 33.0, places=4)
        self.assertAlmostEqual(ed["char_poly"][2], 362.0, places=4)
        self.assertAlmostEqual(ed["char_poly"][3], 1320.0, places=4)
        self.assertTrue(ed["stable"])

    def test_single_state_system(self):
        L = od.observer_gain_ackermann([[-1.0]], [[1.0]], [-5.0])
        self.assertAlmostEqual(L[0], 4.0, places=4)
        ed = od.error_dynamics([[-1.0]], [[1.0]], L)
        # error pole at -5: char poly s + 5
        self.assertAlmostEqual(ed["char_poly"][1], 5.0, places=4)
        self.assertTrue(ed["stable"])

    def test_not_observable_raises(self):
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, [[0.0, 1.0]], [-4.0, -5.0])

    def test_multi_output_row_raises(self):
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, [[1.0, 0.0], [0.0, 1.0]],
                                       [-4.0, -5.0])

    def test_pole_count_mismatch_raises(self):
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, C_DI, [-4.0])
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, C_DI, [-4.0, -5.0, -6.0])

    def test_unstable_pole_raises(self):
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, C_DI, [4.0, -5.0])
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, C_DI, [-4.0, 0.0])

    def test_non_square_a_raises(self):
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                                       C_DI, [-4.0, -5.0])

    def test_non_numeric_pole_raises(self):
        with self.assertRaises(ValueError):
            od.observer_gain_ackermann(A_DI, C_DI, ["fast", -5.0])


class CharacteristicPolynomialTest(unittest.TestCase):
    def test_double_integrator(self):
        cp = od.characteristic_polynomial(A_DI)
        self.assertAlmostEqual(cp[0], 1.0, places=4)
        self.assertAlmostEqual(cp[1], 0.0, places=4)
        self.assertAlmostEqual(cp[2], 0.0, places=4)

    def test_diagonal_three_state(self):
        cp = od.characteristic_polynomial(
            [[-1.0, 0.0, 0.0], [0.0, -2.0, 0.0], [0.0, 0.0, -3.0]])
        # (s+1)(s+2)(s+3) = s^3 + 6 s^2 + 11 s + 6
        self.assertAlmostEqual(cp[1], 6.0, places=4)
        self.assertAlmostEqual(cp[2], 11.0, places=4)
        self.assertAlmostEqual(cp[3], 6.0, places=4)

    def test_damped_oscillator(self):
        # A = [[0,1],[-1,-1]]: char poly s^2 + s + 1
        cp = od.characteristic_polynomial([[0.0, 1.0], [-1.0, -1.0]])
        self.assertAlmostEqual(cp[1], 1.0, places=4)
        self.assertAlmostEqual(cp[2], 1.0, places=4)


class HurwitzTest(unittest.TestCase):
    def test_stable_quadratic(self):
        self.assertTrue(od.is_hurwitz([1.0, 9.0, 20.0]))
        self.assertTrue(od.is_hurwitz([1.0, 2.0, 3.0]))

    def test_damped_oscillator_stable(self):
        self.assertTrue(od.is_hurwitz([1.0, 1.0, 1.0]))

    def test_unstable_negative_coefficient(self):
        # s^2 + s - 2 has a positive root: not Hurwitz
        self.assertFalse(od.is_hurwitz([1.0, 1.0, -2.0]))

    def test_marginal_zero_coefficient(self):
        # s^2 + 1 has roots on the imaginary axis: not strictly stable
        self.assertFalse(od.is_hurwitz([1.0, 0.0, 1.0]))

    def test_first_order(self):
        self.assertTrue(od.is_hurwitz([1.0, 5.0]))
        self.assertFalse(od.is_hurwitz([1.0, -5.0]))


class SeparationPrincipleTest(unittest.TestCase):
    def test_double_integrator_factorization(self):
        L = od.observer_gain_ackermann(A_DI, C_DI, [-4.0, -5.0])
        sep = od.separation_closed_loop(A_DI, B_DI, C_DI, [1.0, 1.0], L)
        # controller: A - B K = [[0,1],[-1,-1]] -> s^2 + s + 1
        self.assertAlmostEqual(sep["controller_poly"][1], 1.0, places=4)
        self.assertAlmostEqual(sep["controller_poly"][2], 1.0, places=4)
        # observer: A - L C -> s^2 + 9s + 20
        self.assertAlmostEqual(sep["observer_poly"][1], 9.0, places=4)
        self.assertAlmostEqual(sep["observer_poly"][2], 20.0, places=4)
        # product: s^4 + 10 s^3 + 30 s^2 + 29 s + 20
        self.assertAlmostEqual(sep["closed_loop_poly"][1], 10.0, places=4)
        self.assertAlmostEqual(sep["closed_loop_poly"][2], 30.0, places=4)
        self.assertAlmostEqual(sep["closed_loop_poly"][3], 29.0, places=4)
        self.assertAlmostEqual(sep["closed_loop_poly"][4], 20.0, places=4)
        self.assertTrue(sep["factorizes"])

    def test_gain_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            od.separation_closed_loop(A_DI, B_DI, C_DI, [1.0], [9.0, 20.0])
        with self.assertRaises(ValueError):
            od.separation_closed_loop(A_DI, B_DI, C_DI, [1.0, 1.0], [9.0])

    def test_b_column_shape_raises(self):
        with self.assertRaises(ValueError):
            od.separation_closed_loop(A_DI, [[0.0, 1.0]], C_DI,
                                      [1.0, 1.0], [9.0, 20.0])


class SettlingTimeTest(unittest.TestCase):
    def test_analytic_two_percent_band(self):
        # sigma = 4 rad/s: t_s = 4/4 = 1.0 s
        self.assertAlmostEqual(od.settling_time([-4.0, -5.0]), 1.0, places=4)

    def test_slowest_pole_dominates(self):
        self.assertAlmostEqual(od.settling_time([-2.0, -3.0, -4.0]), 2.0,
                               places=4)

    def test_complex_pair_uses_real_part(self):
        self.assertAlmostEqual(od.settling_time([-2.0 + 3.0j, -2.0 - 3.0j]),
                               2.0, places=4)

    def test_unstable_pole_raises(self):
        with self.assertRaises(ValueError):
            od.settling_time([1.0, -2.0])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            od.settling_time([])


class ErrorDynamicsTest(unittest.TestCase):
    def test_matrix_is_a_minus_lc(self):
        L = od.observer_gain_ackermann(A_DI, C_DI, [-4.0, -5.0])
        ed = od.error_dynamics(A_DI, C_DI, L)
        # A - L C = [[-9, 1], [-20, 0]]
        self.assertAlmostEqual(ed["matrix"][0][0], -9.0, places=4)
        self.assertAlmostEqual(ed["matrix"][0][1], 1.0, places=4)
        self.assertAlmostEqual(ed["matrix"][1][0], -20.0, places=4)
        self.assertAlmostEqual(ed["matrix"][1][1], 0.0, places=4)

    def test_gain_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            od.error_dynamics(A_DI, C_DI, [9.0])

    def test_non_numeric_gain_raises(self):
        with self.assertRaises(ValueError):
            od.error_dynamics(A_DI, C_DI, ["high", 20.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
