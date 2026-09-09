"""Contract test for gnc-autonomy/control/h-infinity-synthesis.

Exercises every numbered step of the SKILL.md Workflow: (1) fixing the
generalized plant, (2) solving are_x_inf and are_y_inf, (3) the
gamma_feasible verdict and its spectral-radius-coupling check, (4) the
gamma_iteration bisection over the Riccati feasibility of the plant,
(5) central_controller assembly at the declared working level, (6) the
closed_loop_peak achievement scan, and (7) this deterministic contract
test itself. Offline, stdlib unittest, no network, no exact-float
equality on computed sums.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_infinity_synthesis_logic as hinf


A = [[0.0, 1.0], [-4.0, -2.0]]
B1 = [[1.0, 0.0], [0.0, 0.0]]
B2 = [[0.0], [1.0]]
C1 = [[2.0, 0.0], [0.0, 0.0]]
C2 = [[1.0, 0.0]]


def routh_first_column(coeffs):
    """Classical Routh-Hurwitz first column of a descending-power polynomial."""
    n = len(coeffs) - 1
    row_even = list(coeffs[0::2])
    row_odd = list(coeffs[1::2])
    while len(row_odd) < len(row_even):
        row_odd.append(0.0)
    rows = [row_even, row_odd]
    first_col = [row_even[0], row_odd[0]]
    for _ in range(n - 1):
        prev, cur = rows[-2], rows[-1]
        pivot = cur[0]
        new_row = [((cur[0] * (prev[j] if j < len(prev) else 0.0))
                    - (prev[0] * (cur[j] if j < len(cur) else 0.0))) / pivot
                   for j in range(1, len(prev))]
        new_row.append(0.0)
        rows.append(new_row)
        first_col.append(new_row[0])
    return first_col


class TestModuleConstants(unittest.TestCase):
    """Step 1 of the Workflow: the pinned generalized-plant and search constants."""

    def test_pinned_constants(self):
        self.assertEqual(hinf.N_STATES, 2)
        self.assertEqual(hinf.GAMMA_BISECT_ITER, 80)
        self.assertEqual(hinf.GAMMA_HI_START, 1.0)
        self.assertEqual(hinf.GAMMA_HI_CEIL, 1e6)
        self.assertEqual(hinf.GAMMA_FLOOR, 1e-6)
        self.assertEqual(hinf.PSD_EPS, 1e-9)
        self.assertEqual(hinf.IMAG_AXIS_EPS, 1e-9)
        self.assertEqual(hinf.DEFECT_EPS, 1e-12)
        self.assertEqual(hinf.COUPLING_REL_EPS, 1e-9)
        self.assertEqual(hinf.PEAK_W_MIN, 1e-3)
        self.assertEqual(hinf.PEAK_W_MAX, 1e3)
        self.assertEqual(hinf.PEAK_GRID_POINTS, 4001)


class TestRiccatiSolutions(unittest.TestCase):
    """Step 2 of the Workflow: are_x_inf and are_y_inf, the two stabilizing AREs."""

    def test_x_inf_positive_semidefinite_at_working_level(self):
        x_inf = hinf.are_x_inf(A, B1, B2, C1, 1.5)
        for e in hinf.eigs2x2(x_inf):
            self.assertGreaterEqual(e[0], -hinf.PSD_EPS)
            self.assertAlmostEqual(e[1], 0.0, delta=1e-9)

    def test_y_inf_positive_semidefinite_at_working_level(self):
        y_inf = hinf.are_y_inf(A, B1, B2, C1, C2, 1.5)
        for e in hinf.eigs2x2(y_inf):
            self.assertGreaterEqual(e[0], -hinf.PSD_EPS)
            self.assertAlmostEqual(e[1], 0.0, delta=1e-9)

    def test_x_inf_are_residual_at_working_level(self):
        x_inf = hinf.are_x_inf(A, B1, B2, C1, 1.5)
        s_x = hinf.mat_sub(hinf.mat_scale(hinf.mat_mult(B1, hinf.mat_transpose(B1)), 1.5 ** -2),
                            hinf.mat_mult(B2, hinf.mat_transpose(B2)))
        residual = hinf.mat_add(
            hinf.mat_add(hinf.mat_mult(hinf.mat_transpose(A), x_inf), hinf.mat_mult(x_inf, A)),
            hinf.mat_add(hinf.mat_mult(x_inf, hinf.mat_mult(s_x, x_inf)), hinf.mat_mult(hinf.mat_transpose(C1), C1)),
        )
        frob = math.sqrt(sum(v * v for row in residual for v in row))
        self.assertLess(frob, 1e-9)

    def test_y_inf_are_residual_at_working_level(self):
        y_inf = hinf.are_y_inf(A, B1, B2, C1, C2, 1.5)
        s_y = hinf.mat_sub(hinf.mat_scale(hinf.mat_mult(hinf.mat_transpose(C1), C1), 1.5 ** -2),
                            hinf.mat_mult(hinf.mat_transpose(C2), C2))
        residual = hinf.mat_add(
            hinf.mat_add(hinf.mat_mult(A, y_inf), hinf.mat_mult(y_inf, hinf.mat_transpose(A))),
            hinf.mat_add(hinf.mat_mult(y_inf, hinf.mat_mult(s_y, y_inf)), hinf.mat_mult(B1, hinf.mat_transpose(B1))),
        )
        frob = math.sqrt(sum(v * v for row in residual for v in row))
        self.assertLess(frob, 1e-9)

    def test_x_inf_y_inf_symmetry(self):
        x_inf = hinf.are_x_inf(A, B1, B2, C1, 1.5)
        y_inf = hinf.are_y_inf(A, B1, B2, C1, C2, 1.5)
        self.assertAlmostEqual(x_inf[0][1], x_inf[1][0], delta=1e-12)
        self.assertAlmostEqual(y_inf[0][1], y_inf[1][0], delta=1e-12)

    def test_x_inf_stabilizing_eigenvalues_at_working_level(self):
        x_inf = hinf.are_x_inf(A, B1, B2, C1, 1.5)
        s_x = hinf.mat_sub(hinf.mat_scale(hinf.mat_mult(B1, hinf.mat_transpose(B1)), 1.5 ** -2),
                            hinf.mat_mult(B2, hinf.mat_transpose(B2)))
        eigs = hinf.eigs2x2(hinf.mat_add(A, hinf.mat_mult(s_x, x_inf)))
        for e in eigs:
            self.assertLess(e[0], -1e-3)

    def test_y_inf_stabilizing_eigenvalues_at_working_level(self):
        y_inf = hinf.are_y_inf(A, B1, B2, C1, C2, 1.5)
        s_y = hinf.mat_sub(hinf.mat_scale(hinf.mat_mult(hinf.mat_transpose(C1), C1), 1.5 ** -2),
                            hinf.mat_mult(hinf.mat_transpose(C2), C2))
        eigs = hinf.eigs2x2(hinf.mat_add(hinf.mat_transpose(A), hinf.mat_mult(s_y, y_inf)))
        for e in eigs:
            self.assertLess(e[0], -1e-3)

    def test_x_inf_gamma_rejection(self):
        with self.assertRaisesRegex(ValueError, "gamma level must be strictly positive: received gamma = 0.0"):
            hinf.are_x_inf(A, B1, B2, C1, 0.0)
        with self.assertRaisesRegex(ValueError, "gamma level must be strictly positive: received gamma = -2.0"):
            hinf.are_x_inf(A, B1, B2, C1, -2.0)

    def test_x_inf_no_stabilizing_solution_rejection(self):
        with self.assertRaisesRegex(ValueError, "no stabilizing PSD solution of the X_inf algebraic Riccati equation at gamma = 1.28"):
            hinf.are_x_inf(A, B1, B2, C1, 1.28)

    def test_shape_rejection(self):
        with self.assertRaises(ValueError):
            hinf.are_x_inf([[0.0, 1.0]], B1, B2, C1, 1.5)
        with self.assertRaises(ValueError):
            hinf.are_y_inf(A, B1, B2, C1, [[1.0, 0.0, 0.0]], 1.5)


class TestGammaFeasible(unittest.TestCase):
    """Step 3 of the Workflow: the gamma-level feasibility verdict and coupling check."""

    def test_infeasible_below_gamma_inf(self):
        for gamma in (1.00, 1.24, 1.25, 1.26, 1.28):
            result = hinf.gamma_feasible(A, B1, B2, C1, C2, gamma)
            self.assertFalse(result["feasible"])
            self.assertEqual(result["reason"], "x-are-no-stabilizing-solution")
            self.assertIsNone(result["rho"])

    def test_coupling_fails_just_below_gamma_inf(self):
        result = hinf.gamma_feasible(A, B1, B2, C1, C2, 1.2885)
        self.assertFalse(result["feasible"])
        self.assertEqual(result["reason"], "spectral-radius-coupling-fails")
        self.assertAlmostEqual(result["rho"] / (1.2885 ** 2), 1.0226955372337125, delta=1e-6)

    def test_feasible_above_gamma_inf(self):
        expected_rho = {
            1.29: 1.6627132282952146, 1.30: 1.5207128718101464,
            1.40: 1.1109308083000942, 2.00: 0.73205080756887764, 4.00: 0.60910023020016668,
        }
        for gamma, rho in expected_rho.items():
            result = hinf.gamma_feasible(A, B1, B2, C1, C2, gamma)
            self.assertTrue(result["feasible"])
            self.assertEqual(result["reason"], "")
            self.assertAlmostEqual(result["rho"], rho, delta=1e-6 * abs(rho))


class TestGammaIteration(unittest.TestCase):
    """Step 4 of the Workflow: the gamma-level bisection to the infimum feasible level."""

    def test_gamma_inf_and_bracket(self):
        result = hinf.gamma_iteration(A, B1, B2, C1, C2)
        self.assertAlmostEqual(result["gamma_inf"], 1.2899416380818218, delta=1e-6)
        self.assertAlmostEqual(result["gamma_lo"], 1.2899416380818216, delta=1e-6)
        self.assertLess((result["gamma_inf"] - result["gamma_lo"]) / result["gamma_inf"], 1e-9)
        self.assertGreater(result["gamma_inf"], 1.28)
        self.assertLess(result["gamma_inf"], 1.29)

    def test_x_inf_y_inf_at_gamma_inf(self):
        result = hinf.gamma_iteration(A, B1, B2, C1, C2)
        expected_x = [[4.8550497046046912, 1.8451689460791623], [1.8451689460791623, 1.1203305657836022]]
        expected_y = [[0.69782803015344119, -0.84182902900864276], [-0.84182902900864276, 1.9323890607421939]]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(result["x_inf"][i][j], expected_x[i][j], delta=1e-6 * abs(expected_x[i][j]))
                self.assertAlmostEqual(result["y_inf"][i][j], expected_y[i][j], delta=1e-6 * abs(expected_y[i][j]))

    def test_tight_coupling_identity_at_gamma_inf(self):
        result = hinf.gamma_iteration(A, B1, B2, C1, C2)
        self.assertAlmostEqual(result["rho"], 1.6639494279932627, delta=1e-6)
        ratio = result["rho"] / (result["gamma_inf"] ** 2)
        self.assertAlmostEqual(ratio, 0.99999999899999903, delta=1e-6)
        self.assertAlmostEqual(1.0 - ratio, 1e-9, delta=1e-3 * 1e-9)

    def test_determinism(self):
        first = hinf.gamma_iteration(A, B1, B2, C1, C2)
        second = hinf.gamma_iteration(A, B1, B2, C1, C2)
        self.assertEqual(first["gamma_inf"], second["gamma_inf"])
        self.assertEqual(first["gamma_lo"], second["gamma_lo"])

    def test_no_imports_beyond_math(self):
        self.assertEqual(hinf.math.__name__, "math")


class TestCentralController(unittest.TestCase):
    """Step 5 of the Workflow: the central controller assembled at the working level."""

    def setUp(self):
        self.ctrl = hinf.central_controller(A, B1, B2, C1, C2, 1.5)

    def test_x_inf_y_inf_rho_at_working_level(self):
        expected_x = [[2.8767170729927769, 0.86600457222455551], [0.86600457222455551, 0.46278834694194487]]
        expected_y = [[0.57859549850415914, -0.63018940312360749], [-0.63018940312360749, 1.33760021698791]]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(self.ctrl["x_inf"][i][j], expected_x[i][j], delta=1e-6 * abs(expected_x[i][j]))
                self.assertAlmostEqual(self.ctrl["y_inf"][i][j], expected_y[i][j], delta=1e-6 * abs(expected_y[i][j]))
        self.assertAlmostEqual(self.ctrl["rho"], 0.96499552430796154, delta=1e-6)
        self.assertAlmostEqual(1.0 - self.ctrl["rho"] / 2.25, 0.57111310030757267, delta=1e-6)

    def test_gains_and_correction_at_working_level(self):
        expected_f = [-0.86600457222455551, -0.46278834694194487]
        expected_h = [-0.57859549850415914, 0.63018940312360749]
        expected_z = [[1.8840094153375413, 0.18126028353826662], [-0.56649451713616139, 0.97916244503312322]]
        self.assertAlmostEqual(self.ctrl["f_inf"][0][0], expected_f[0], delta=1e-6)
        self.assertAlmostEqual(self.ctrl["f_inf"][0][1], expected_f[1], delta=1e-6)
        self.assertAlmostEqual(self.ctrl["h_inf"][0][0], expected_h[0], delta=1e-6)
        self.assertAlmostEqual(self.ctrl["h_inf"][1][0], expected_h[1], delta=1e-6)
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(self.ctrl["z_inf"][i][j], expected_z[i][j], delta=1e-6 * abs(expected_z[i][j]))

    def test_central_controller_state_matrices(self):
        expected_a_k = [[-0.53140661251631349, 1.0], [-3.9211755978858096, -2.4627883469419447]]
        expected_b_k = [0.97585105696075791, -0.94482897433874635]
        expected_c_k = [-0.86600457222455551, -0.46278834694194487]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(self.ctrl["a_k"][i][j], expected_a_k[i][j], delta=1e-6 * max(1.0, abs(expected_a_k[i][j])))
            self.assertAlmostEqual(self.ctrl["b_k"][i][0], expected_b_k[i], delta=1e-6)
            self.assertAlmostEqual(self.ctrl["c_k"][0][i], expected_c_k[i], delta=1e-6)
        self.assertEqual(self.ctrl["d_k"], [[0.0]])

    def test_gain_identity_recompute(self):
        """Module-independent identity: F_inf, H_inf, Z_inf recomputed from X_inf, Y_inf."""
        x, y = self.ctrl["x_inf"], self.ctrl["y_inf"]
        f_check = hinf.mat_scale(hinf.mat_mult(hinf.mat_transpose(B2), x), -1.0)
        h_check = hinf.mat_scale(hinf.mat_mult(y, hinf.mat_transpose(C2)), -1.0)
        z_check = hinf.mat2_inv(hinf.mat_sub(hinf.mat_eye(2), hinf.mat_scale(hinf.mat_mult(y, x), 1.5 ** -2)))
        self.assertAlmostEqual(f_check[0][0], self.ctrl["f_inf"][0][0], delta=1e-9)
        self.assertAlmostEqual(h_check[0][0], self.ctrl["h_inf"][0][0], delta=1e-9)
        self.assertAlmostEqual(z_check[0][0], self.ctrl["z_inf"][0][0], delta=1e-9)

    def test_assembly_identity_recompute(self):
        """Module-independent identity: A_k, B_k assembled from X_inf, F_inf, H_inf, Z_inf."""
        b1b1t = hinf.mat_mult(B1, hinf.mat_transpose(B1))
        a_k_check = hinf.mat_add(
            hinf.mat_add(hinf.mat_add(A, hinf.mat_scale(b1b1t, 1.5 ** -2)), hinf.mat_mult(B2, self.ctrl["f_inf"])),
            hinf.mat_mult(self.ctrl["z_inf"], hinf.mat_mult(self.ctrl["h_inf"], C2)),
        )
        b_k_check = hinf.mat_scale(hinf.mat_mult(self.ctrl["z_inf"], self.ctrl["h_inf"]), -1.0)
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(a_k_check[i][j], self.ctrl["a_k"][i][j], delta=1e-9 * max(1.0, abs(a_k_check[i][j])))
            self.assertAlmostEqual(b_k_check[i][0], self.ctrl["b_k"][i][0], delta=1e-9)

    def test_controller_poles_and_dc_gain(self):
        poles = hinf.eigs2x2(self.ctrl["a_k"])
        real_parts = sorted(p[0] for p in poles)
        imag_parts = sorted(abs(p[1]) for p in poles)
        self.assertAlmostEqual(real_parts[0], -1.497097479729129, delta=1e-6)
        self.assertAlmostEqual(real_parts[1], -1.497097479729129, delta=1e-6)
        self.assertAlmostEqual(imag_parts[0], 1.7287616223376692, delta=1e-6)
        for p in poles:
            self.assertLess(p[0], 0.0)
        a_k_inv = hinf.mat2_inv(self.ctrl["a_k"])
        dc = hinf.mat_mult(hinf.mat_scale(self.ctrl["c_k"], -1.0), hinf.mat_mult(a_k_inv, self.ctrl["b_k"]))
        self.assertAlmostEqual(dc[0][0], 0.14152370536133152, delta=1e-6)

    def test_gamma_nonpositive_rejection(self):
        with self.assertRaisesRegex(ValueError, "gamma level must be strictly positive: received gamma = 0.0"):
            hinf.central_controller(A, B1, B2, C1, C2, 0.0)
        with self.assertRaisesRegex(ValueError, "gamma level must be strictly positive: received gamma = -2.0"):
            hinf.central_controller(A, B1, B2, C1, C2, -2.0)

    def test_coupling_rejection_below_gamma_inf(self):
        with self.assertRaises(ValueError) as ctx:
            hinf.central_controller(A, B1, B2, C1, C2, 1.2885)
        message = str(ctx.exception)
        self.assertIn("spectral-radius coupling condition rho(X_inf Y_inf) < gamma^2 fails", message)
        self.assertIn("gamma = 1.2885", message)

    def test_are_rejection_below_x_are_threshold(self):
        with self.assertRaisesRegex(ValueError, "no stabilizing PSD solution of the X_inf algebraic Riccati equation at gamma = 1.28"):
            hinf.central_controller(A, B1, B2, C1, C2, 1.28)


class TestClosedLoopAchievement(unittest.TestCase):
    """Step 6 of the Workflow: the closed-loop achievement scan of the synthesized loop."""

    def setUp(self):
        self.ctrl = hinf.central_controller(A, B1, B2, C1, C2, 1.5)

    def test_closed_loop_characteristic_polynomial_and_hurwitz(self):
        a_cl = hinf.vstack(
            hinf.hstack(A, hinf.mat_mult(B2, self.ctrl["c_k"])),
            hinf.hstack(hinf.mat_mult(self.ctrl["b_k"], C2), self.ctrl["a_k"]),
        )
        coeffs = [1.0] + hinf.fl_char_poly(a_cl)
        expected = [1.0, 4.994194959458258, 15.218307529595396, 22.844450697151888, 20.179513123717761]
        for got, want in zip(coeffs, expected):
            self.assertAlmostEqual(got, want, delta=1e-6 * max(1.0, abs(want)))
        first_column = routh_first_column(coeffs)
        for entry in first_column:
            self.assertGreater(entry, 0.0)

    def test_achievement_scan_peak(self):
        result = hinf.closed_loop_peak(A, B1, B2, C1, C2, self.ctrl)
        self.assertAlmostEqual(result["peak"], 1.4055693346768514, delta=1e-6 * 1.4055693346768514)
        self.assertAlmostEqual(result["w_peak"], 1.7318090307501135, delta=1e-3 * 1.7318090307501135)
        self.assertLess(result["peak"], 1.5)
        self.assertAlmostEqual(result["peak"] / 1.5, 0.93704622311790098, delta=1e-6)


class TestGeneralizedPlantFixture(unittest.TestCase):
    """Step 1 of the Workflow: the given generalized-plant state matrices are consumed unchanged."""

    def test_plant_shapes(self):
        self.assertEqual(len(A), 2)
        self.assertEqual(len(B2[0]), 1)
        self.assertEqual(len(C2), 1)


if __name__ == "__main__":
    unittest.main()
