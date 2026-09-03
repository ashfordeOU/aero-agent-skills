"""Contract test for gnss_raim_fde_logic (GNSS RAIM FDE, wave-29).

Deterministic, offline, stdlib only.  Reproduces the spec worked
example: six satellites, noise drawn with random.seed(42) at
sigma = SIGMA0, and a 200 m bias on satellite 1 (index 0).  Asserts the
spec anchors within their stated tolerances plus boundary cases and
ValueError rejections.

Run: python3 scripts/test_gnss_raim_fde.py
"""

import math
import random
import unittest

import gnss_raim_fde_logic as raim

DIRS = [
    [0.4082, 0.8165, 0.4082],
    [-0.4082, 0.8165, 0.4082],
    [0.0, -0.7071, 0.7071],
    [0.7071, 0.0, 0.7071],
    [-0.7071, 0.0, 0.7071],
    [0.0, 0.7071, -0.7071],
]
X_TRUE = [10.0, -20.0, 30.0, 0.0]


def _mat_vec_mul(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v)))
            for i in range(len(A))]


def _mat_mul(A, B):
    k = len(B)
    return [[sum(A[i][t] * B[t][j] for t in range(k))
             for j in range(len(B[0]))]
            for i in range(len(A))]


def _scenario(bias_m):
    """Build (H, y) for the worked-example six-satellite geometry.

    Measurement vector y = H x_true + noise + bias, with the noise drawn
    by a fresh random.Random(42) generator (gauss, sigma = SIGMA0) and
    bias_m added to satellite 1 (index 0) when nonzero.
    """
    H = raim.geometry_matrix(DIRS)
    rng = random.Random(42)
    noise = [rng.gauss(0.0, raim.SIGMA0) for _ in range(len(H))]
    y = [m + n for m, n in zip(_mat_vec_mul(H, X_TRUE), noise)]
    if bias_m:
        y[0] += bias_m
    return H, y


class TestModuleConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(raim.PFA, 1e-5)
        self.assertEqual(raim.SIGMA0, 6.0)
        self.assertEqual(raim.G0, 9.80665)


class TestGeometryMatrix(unittest.TestCase):
    def test_shape_and_clock_column(self):
        H = raim.geometry_matrix(DIRS)
        self.assertEqual(len(H), 6)
        for row in H:
            self.assertEqual(len(row), 4)
            self.assertEqual(row[3], 1.0)

    def test_rows_are_renormalized_unit_vectors(self):
        H = raim.geometry_matrix(DIRS)
        for row in H:
            nrm = math.sqrt(sum(row[j] ** 2 for j in range(3)))
            self.assertAlmostEqual(nrm, 1.0, places=9)

    def test_fewer_than_five_satellites_raises(self):
        with self.assertRaises(ValueError):
            raim.geometry_matrix(DIRS[:4])

    def test_bad_vector_length_raises(self):
        with self.assertRaises(ValueError):
            raim.geometry_matrix(DIRS[:4] + [[0.5, 0.5]])

    def test_non_unit_vector_raises(self):
        with self.assertRaises(ValueError):
            raim.geometry_matrix(DIRS[:4] + [[0.5, 0.5, 0.5]])

    def test_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            raim.geometry_matrix(DIRS[:4] + [[0.0, 0.0, 0.0]])


class TestLsqSolve(unittest.TestCase):
    def test_exact_roundtrip(self):
        H = raim.geometry_matrix(DIRS)
        x = [3.0, -4.0, 5.0, 2.0]
        y = _mat_vec_mul(H, x)
        x_hat, residuals, sse = raim.lsq_solve(H, y)
        for i in range(4):
            self.assertAlmostEqual(x_hat[i], x[i], places=9)
        self.assertLess(sse, 1e-18)
        self.assertTrue(all(abs(r) < 1e-9 for r in residuals))

    def test_residuals_orthogonal_to_columns(self):
        H, y = _scenario(bias_m=200.0)
        _, residuals, _ = raim.lsq_solve(H, y)
        for j in range(4):
            dot = sum(residuals[i] * H[i][j] for i in range(len(H)))
            self.assertLess(abs(dot), 1e-6)

    def test_length_mismatch_raises(self):
        H = raim.geometry_matrix(DIRS)
        with self.assertRaises(ValueError):
            raim.lsq_solve(H, [1.0, 2.0, 3.0])


class TestNormalQuantile(unittest.TestCase):
    def test_upper_tail_anchor(self):
        z = raim.normal_quantile(0.99999)
        self.assertAlmostEqual(z, 4.2649, delta=1e-3)

    def test_midpoint_and_symmetry(self):
        self.assertAlmostEqual(raim.normal_quantile(0.5), 0.0, places=12)
        zl = raim.normal_quantile(0.025)
        zu = raim.normal_quantile(0.975)
        self.assertAlmostEqual(zl, -zu, places=9)
        self.assertAlmostEqual(zu, 1.959964, delta=1e-3)

    def test_out_of_range_raises(self):
        for bad in (0.0, 1.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                raim.normal_quantile(bad)


class TestChi2Quantile(unittest.TestCase):
    def test_df2_anchor(self):
        self.assertAlmostEqual(raim.chi2_quantile(2, 0.99999), 24.669,
                               delta=0.01)

    def test_df6_anchor(self):
        self.assertAlmostEqual(raim.chi2_quantile(6, 0.99999), 34.052,
                               delta=0.05)

    def test_df1_is_positive(self):
        x = raim.chi2_quantile(1, 0.99999)
        self.assertGreater(x, 0.0)
        self.assertGreater(x, 10.0)

    def test_df_below_one_raises(self):
        for bad in (0.0, 0.5, -2.0):
            with self.assertRaises(ValueError):
                raim.chi2_quantile(bad, 0.999)

    def test_monotonic_in_probability(self):
        low = raim.chi2_quantile(2, 0.99)
        high = raim.chi2_quantile(2, 0.99999)
        self.assertGreater(high, low)


class TestFaultDetect(unittest.TestCase):
    def test_clean_case_no_alarm(self):
        H, y = _scenario(bias_m=0.0)
        _, _, sse = raim.lsq_solve(H, y)
        fd = raim.fault_detect(sse, len(H), raim.SIGMA0)
        self.assertAlmostEqual(fd["test_statistic"], 0.143, delta=0.01)
        self.assertFalse(fd["detected"])

    def test_bias_case_alarm(self):
        H, y = _scenario(bias_m=200.0)
        _, _, sse = raim.lsq_solve(H, y)
        fd = raim.fault_detect(sse, len(H), raim.SIGMA0)
        self.assertAlmostEqual(fd["test_statistic"], 495.2, delta=0.5)
        self.assertTrue(fd["detected"])
        self.assertGreater(fd["test_statistic"], fd["threshold"])

    def test_threshold_monotonic_in_pfa(self):
        H, y = _scenario(bias_m=0.0)
        _, _, sse = raim.lsq_solve(H, y)
        strict = raim.fault_detect(sse, 6, raim.SIGMA0, pfa=1e-7)
        loose = raim.fault_detect(sse, 6, raim.SIGMA0, pfa=1e-3)
        self.assertGreater(strict["threshold"], loose["threshold"])

    def test_pfa_out_of_range_raises(self):
        for bad in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                raim.fault_detect(1.0, 6, raim.SIGMA0, pfa=bad)

    def test_fewer_than_five_satellites_raises(self):
        with self.assertRaises(ValueError):
            raim.fault_detect(1.0, 4, raim.SIGMA0)

    def test_nonpositive_sigma_raises(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                raim.fault_detect(1.0, 6, bad)


class TestResidualSensitivity(unittest.TestCase):
    def test_idempotent_and_annihilates_geometry(self):
        H = raim.geometry_matrix(DIRS)
        S = raim.residual_sensitivity(H)
        self.assertEqual(len(S), 6)
        for row in S:
            self.assertEqual(len(row), 6)
        S2 = _mat_mul(S, S)
        SH = _mat_mul(S, H)
        for i in range(6):
            for j in range(6):
                self.assertAlmostEqual(S2[i][j], S[i][j], places=9)
            for j in range(4):
                self.assertLess(abs(SH[i][j]), 1e-9)


class TestRaimHpl(unittest.TestCase):
    def test_hpl_anchor(self):
        H = raim.geometry_matrix(DIRS)
        hpl = raim.raim_hpl(H, raim.SIGMA0)
        self.assertAlmostEqual(hpl, 44.5, delta=0.3)
        self.assertGreater(hpl, 0.0)

    def test_hpl_scales_with_sigma(self):
        H = raim.geometry_matrix(DIRS)
        hpl6 = raim.raim_hpl(H, 6.0)
        hpl12 = raim.raim_hpl(H, 12.0)
        self.assertAlmostEqual(hpl12 / hpl6, 2.0, places=9)

    def test_degenerate_geometry_raises(self):
        degenerate = [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0],
                      [0.0, 1.0, 0.0], [0.0, -1.0, 0.0],
                      [0.0, 0.0, 1.0]]
        H = raim.geometry_matrix(degenerate)
        with self.assertRaises(ValueError):
            raim.raim_hpl(H, raim.SIGMA0)


class TestExcludeFaulty(unittest.TestCase):
    def test_identifies_biased_satellite(self):
        H, y = _scenario(bias_m=200.0)
        ex = raim.exclude_faulty(H, y)
        self.assertEqual(ex["worst_sat"], 0)
        self.assertTrue(ex["recommended_exclusion"])
        nrs = ex["normalized_residuals"]
        self.assertEqual(len(nrs), 6)
        self.assertTrue(all(nr >= 0.0 for nr in nrs))
        self.assertAlmostEqual(nrs[0], 22.3, delta=0.5)
        ordered = sorted(nrs, reverse=True)
        self.assertAlmostEqual(ordered[1], 19.3, delta=0.5)
        self.assertGreater(ordered[0], 1.10 * ordered[1])

    def test_fewer_than_six_satellites_raises(self):
        H5 = raim.geometry_matrix(DIRS[:5])
        y5 = [1.0] * 5
        with self.assertRaises(ValueError):
            raim.exclude_faulty(H5, y5)

    def test_exclusion_rerun_clean(self):
        H, y = _scenario(bias_m=200.0)
        ex = raim.exclude_faulty(H, y)
        worst = ex["worst_sat"]
        H_rem = [row for i, row in enumerate(H) if i != worst]
        y_rem = [v for i, v in enumerate(y) if i != worst]
        _, _, sse = raim.lsq_solve(H_rem, y_rem)
        fd = raim.fault_detect(sse, len(H_rem), raim.SIGMA0)
        self.assertAlmostEqual(fd["test_statistic"], 0.013, delta=0.01)
        self.assertFalse(fd["detected"])


class TestAvailabilityVerdict(unittest.TestCase):
    def test_available_when_hpl_below_hal(self):
        self.assertEqual(raim.availability_verdict(44.5, 556.0),
                         "available")

    def test_unavailable_when_hpl_exceeds_hal(self):
        self.assertEqual(raim.availability_verdict(44.5, 30.0),
                         "unavailable")

    def test_boundary_hpl_equals_hal(self):
        self.assertEqual(raim.availability_verdict(44.5, 44.5),
                         "available")


if __name__ == "__main__":
    unittest.main()
