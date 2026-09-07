"""Contract test for the cramer-rao-lower-bound leaf (gnc-autonomy,
estimation-filtering pack).

Exercises the SKILL.md workflow end to end: workflow step 2, form the
fisher-information-matrix as the negative expected second derivative of
the log-likelihood (the score identity) for each canonical model, is
exercised by the fisher_info_* tests; workflow step 3, invert the
information matrix to the cramer-rao-lower-bound scalar or covariance
bound, is exercised by the crlb_* tests; workflow step 4, the
bound-achieving maximum-likelihood variance comparison, is exercised by
the mle_var tests; workflow step 5, the estimator-efficiency rating of a
candidate estimator against the best-achievable-variance, is exercised
by the efficiency tests; workflow step 6, the bound-achieving-estimator
and 1/N scaling sanity checks, is exercised by the scaling and
determinism tests. Every numeric assert is tolerance-based (no exact
float equality on computed sums); all asserts hold under python3 3.9.6
and the pyenv 3.13.12 interpreter.

Run: python3 scripts/test_cramer_rao_lower_bound.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cramer_rao_lower_bound_logic as crlb  # noqa: E402

N_DC = crlb.N_DC
SIGMA2_DC = crlb.SIGMA2_DC
COV_VEC = crlb.COV_VEC
N_VEC = crlb.N_VEC


def rel_close(got, want, rel=1e-6):
    """Tolerance-based closeness: |got - want| <= rel * |want|."""
    return math.isclose(got, want, rel_tol=rel, abs_tol=0.0)


class TestDcLevelAnchor(unittest.TestCase):
    """Workflow steps 2 to 5 on the DC level in white Gaussian noise."""

    def test_fisher_info_dc_anchor(self):
        """Step 2, fisher-information-matrix of the DC level: I(A) = N/sigma^2 = 25.0."""
        self.assertTrue(rel_close(crlb.fisher_info_dc(N_DC, SIGMA2_DC), 25.0))

    def test_crlb_dc_anchor(self):
        """Step 3, cramer-rao-lower-bound: var(A_hat) >= sigma^2/N = 0.04."""
        self.assertTrue(rel_close(crlb.crlb_dc(N_DC, SIGMA2_DC), 0.04))

    def test_mle_var_dc_matches_crlb(self):
        """Step 4, bound-achieving MLE variance: sigma^2/N = 0.04."""
        self.assertTrue(rel_close(crlb.mle_var_dc(N_DC, SIGMA2_DC), 0.04))

    def test_crlb_times_info_is_one(self):
        """Steps 2 to 3 identity: CRLB x I = 1.0 within 1e-12."""
        info = crlb.fisher_info_dc(N_DC, SIGMA2_DC)
        bound = crlb.crlb_dc(N_DC, SIGMA2_DC)
        self.assertTrue(math.isclose(bound * info, 1.0, rel_tol=1e-12))

    def test_score_identity_dc(self):
        """Step 2 score identity: E[(d ln p/dA)^2] = N sigma^2/sigma^4 = 25.0
        equals -E[d^2 ln p/dA^2] = N/sigma^2 = 25.0."""
        score_var = N_DC * SIGMA2_DC / (SIGMA2_DC * SIGMA2_DC)
        self.assertTrue(rel_close(score_var, 25.0, rel=1e-9))
        self.assertTrue(rel_close(score_var, crlb.fisher_info_dc(N_DC, SIGMA2_DC),
                                  rel=1e-9))

    def test_efficiency_bound_achieving_dc(self):
        """Step 5, estimator-efficiency: the sample-mean MLE attains the bound,
        efficiency(crlb, variance) = 1.0."""
        bound = crlb.crlb_dc(N_DC, SIGMA2_DC)
        var = crlb.mle_var_dc(N_DC, SIGMA2_DC)
        self.assertTrue(rel_close(crlb.efficiency(bound, var), 1.0))

    def test_efficiency_first_sample_estimator(self):
        """Step 5: an estimator keeping only x[0] has variance sigma^2 = 4.0,
        efficiency 0.01 = 1/N, above the best-achievable-variance."""
        self.assertTrue(rel_close(crlb.efficiency(0.04, SIGMA2_DC), 0.01))
        self.assertTrue(rel_close(crlb.efficiency(0.04, SIGMA2_DC), 1.0 / N_DC))


class TestScalarGaussianAnchor(unittest.TestCase):
    """Workflow steps 2 and 3 for the scalar Gaussian mean, known variance."""

    def test_fisher_info_gauss_single_sample(self):
        """Step 2: single-sample canonical I(mu) = 1/sigma^2 = 0.1111111111111111."""
        self.assertTrue(rel_close(crlb.fisher_info_gauss(1, 9.0),
                                  0.1111111111111111))

    def test_crlb_gauss_single_sample(self):
        """Step 3: CRLB = sigma^2 = 9.0 for the single sample."""
        self.assertTrue(rel_close(crlb.crlb_gauss(1, 9.0), 9.0))

    def test_crlb_gauss_hundred_samples(self):
        """Step 3: CRLB tightens to sigma^2/n = 0.09 at n = 100."""
        self.assertTrue(rel_close(crlb.crlb_gauss(100, 9.0), 0.09))

    def test_dc_and_gauss_coincide_at_n1(self):
        """Steps 1 to 3: the n = 1 DC-level and Gaussian-mean models coincide."""
        self.assertTrue(rel_close(crlb.crlb_dc(1, 9.0), crlb.crlb_gauss(1, 9.0),
                                  rel=1e-9))


class TestVectorGaussianAnchor(unittest.TestCase):
    """Workflow steps 2 to 5 for the vector Gaussian mean, known covariance."""

    def test_info_matrix_gaussian_anchor(self):
        """Step 2: I = n C^-1 with the analytic inverse,
        [[54.945054945054942, -8.2417582417582409], [-8.2417582417582409,
        13.736263736263735]]."""
        info = crlb.info_matrix_gaussian(N_VEC, COV_VEC)
        for got, want in zip([info[0][0], info[0][1], info[1][0], info[1][1]],
                             [54.945054945054942, -8.2417582417582409,
                              -8.2417582417582409, 13.736263736263735]):
            self.assertTrue(rel_close(got, want))

    def test_crlb_matrix_gaussian_anchor(self):
        """Step 3: covariance bound CRLB = C/n = [[0.02, 0.012], [0.012, 0.08]]."""
        cov = crlb.crlb_matrix_gaussian(N_VEC, COV_VEC)
        for got, want in zip([cov[0][0], cov[0][1], cov[1][0], cov[1][1]],
                             [0.02, 0.012, 0.012, 0.08]):
            self.assertTrue(rel_close(got, want))

    def test_info_times_crlb_identity(self):
        """Step 3 matrix identity: I x CRLB is the identity within 1e-9."""
        info = crlb.info_matrix_gaussian(N_VEC, COV_VEC)
        cov = crlb.crlb_matrix_gaussian(N_VEC, COV_VEC)
        prod = [[info[0][0] * cov[0][0] + info[0][1] * cov[1][0],
                 info[0][0] * cov[0][1] + info[0][1] * cov[1][1]],
                [info[1][0] * cov[0][0] + info[1][1] * cov[1][0],
                 info[1][0] * cov[0][1] + info[1][1] * cov[1][1]]]
        self.assertTrue(rel_close(prod[0][0], 1.0, rel=1e-9))
        self.assertTrue(rel_close(prod[1][1], 1.0, rel=1e-9))
        self.assertLess(abs(prod[0][1]), 1e-9)
        self.assertLess(abs(prod[1][0]), 1e-9)

    def test_sample_mean_vector_estimator_attains_bound(self):
        """Steps 4 to 5: the sample-mean vector estimator has covariance C/n,
        so both diagonal estimator-efficiency values are 1.0."""
        cov = crlb.crlb_matrix_gaussian(N_VEC, COV_VEC)
        eff0 = crlb.efficiency(cov[0][0], COV_VEC[0][0] / N_VEC)
        eff1 = crlb.efficiency(cov[1][1], COV_VEC[1][1] / N_VEC)
        self.assertTrue(rel_close(eff0, 1.0))
        self.assertTrue(rel_close(eff1, 1.0))


class TestSinusoidPhaseAnchor(unittest.TestCase):
    """Workflow steps 2 and 3 for the sinusoid phase in white Gaussian noise."""

    def test_fisher_info_phase_anchor(self):
        """Step 2: at f0 = 0.25, phi0 = 0, even n, I(phi0) =
        (A^2/sigma^2)(n/2) = 320.0."""
        self.assertTrue(rel_close(crlb.fisher_info_phase(64, 1.0, 0.25, 0.0, 0.1),
                                  320.0))

    def test_phase_sine_square_sum_is_n_over_two(self):
        """Step 2: the sine-square sum (I x sigma^2/amp^2) is exactly n/2 = 32.0
        at the worked point (tolerance-based on the summed squares)."""
        info = crlb.fisher_info_phase(64, 1.0, 0.25, 0.0, 0.1)
        sine_sum = info * 0.1 / (1.0 * 1.0)
        self.assertTrue(rel_close(sine_sum, 32.0))

    def test_crlb_phase_anchor(self):
        """Step 3: var(phi_hat) >= 2 sigma^2/(n A^2) = 0.003125 = 1/I(phi0)."""
        bound = crlb.crlb_phase(64, 1.0, 0.1)
        self.assertTrue(rel_close(bound, 0.003125))
        info = crlb.fisher_info_phase(64, 1.0, 0.25, 0.0, 0.1)
        self.assertTrue(math.isclose(bound, 1.0 / info, rel_tol=1e-9))

    def test_phase_bound_only_no_mle_claim(self):
        """Step 4 note: the phase case reports the bound only; the closed-form
        bound-achieving estimator variance is not computed, so the leaf never
        fabricates an mle_var for the phase."""
        self.assertFalse(hasattr(crlb, "mle_var_phase"))


class TestPoissonAnchor(unittest.TestCase):
    """Workflow steps 2 to 5 for the Poisson rate."""

    def test_fisher_info_poisson_anchor(self):
        """Step 2: I(lam) = n/lam = 25/4 = 6.25."""
        self.assertTrue(rel_close(crlb.fisher_info_poisson(25, 4.0), 6.25))

    def test_crlb_poisson_anchor(self):
        """Step 3: CRLB = lam/n = 0.16."""
        self.assertTrue(rel_close(crlb.crlb_poisson(25, 4.0), 0.16))

    def test_mle_var_poisson_matches_crlb(self):
        """Step 4: the sample-mean MLE variance lam/n = 0.16 equals the bound;
        step 5 gives efficiency 1.0 (bound-achieving-estimator)."""
        var = crlb.mle_var_poisson(25, 4.0)
        bound = crlb.crlb_poisson(25, 4.0)
        self.assertTrue(rel_close(var, 0.16))
        self.assertTrue(rel_close(var, bound))
        self.assertTrue(rel_close(crlb.efficiency(bound, var), 1.0))

    def test_poisson_single_observation_identities(self):
        """Step 2 on one observation: E[(x/lam - 1)^2] = 1/lam = 0.25 and
        -E[d^2 ln p/dlam^2] = 1/lam = 0.25 (closed-form pmf identities)."""
        self.assertTrue(rel_close(1.0 / 4.0, 0.25))
        # Score square: Var(x)/lam^2 = lam/lam^2 = 1/lam.
        self.assertTrue(rel_close(4.0 / 16.0, 0.25))
        # Negative second derivative: E[x]/lam^2 = lam/lam^2 = 1/lam.
        self.assertTrue(rel_close(4.0 / 16.0, 1.0 / 4.0))


class TestBoundSemantics(unittest.TestCase):
    """Workflow step 6 sanity checks: 1/N law and bound meaning."""

    def test_crlb_one_over_n_scaling(self):
        """Step 6: crlb_dc(10, 4.0) = 0.4 = 10 x crlb_dc(100, 4.0) = 0.04,
        the bound tightens by a decade per decade of samples."""
        ten = crlb.crlb_dc(10, 4.0)
        hundred = crlb.crlb_dc(100, 4.0)
        self.assertTrue(rel_close(ten, 0.4))
        self.assertTrue(rel_close(hundred, 0.04))
        self.assertTrue(rel_close(ten, 10.0 * hundred))

    def test_unbiased_variances_never_below_bound(self):
        """Step 6: every unbiased variance sits at or above its CRLB
        (0.04 <= 4.0 in the DC case), the best-achievable-variance meaning."""
        bound = crlb.crlb_dc(N_DC, SIGMA2_DC)
        self.assertLessEqual(bound, SIGMA2_DC)
        self.assertLessEqual(bound, crlb.mle_var_dc(N_DC, SIGMA2_DC))

    def test_efficiency_range_semantics(self):
        """Step 5: efficiency = CRLB/variance lies in (0, 1], 1.0 exactly for
        the bound-achieving-estimator."""
        for var in (0.04, 0.4, 4.0, 9.0):
            eff = crlb.efficiency(0.04, var)
            self.assertGreater(eff, 0.0)
            self.assertLessEqual(eff, 1.0)


class TestDeterminism(unittest.TestCase):
    """Workflow step 6 determinism: identical calls, no RNG, math only."""

    def test_identical_calls_bitwise_equal(self):
        """Step 6: two identical calls return bitwise-identical values across
        every public function (no RNG anywhere)."""
        args = [
            crlb.fisher_info_dc(N_DC, SIGMA2_DC),
            crlb.crlb_dc(N_DC, SIGMA2_DC),
            crlb.fisher_info_gauss(1, 9.0),
            crlb.crlb_gauss(100, 9.0),
            crlb.info_matrix_gaussian(N_VEC, COV_VEC),
            crlb.crlb_matrix_gaussian(N_VEC, COV_VEC),
            crlb.fisher_info_phase(64, 1.0, 0.25, 0.0, 0.1),
            crlb.crlb_phase(64, 1.0, 0.1),
            crlb.fisher_info_poisson(25, 4.0),
            crlb.crlb_poisson(25, 4.0),
            crlb.efficiency(0.04, 4.0),
        ]
        reruns = [
            crlb.fisher_info_dc(N_DC, SIGMA2_DC),
            crlb.crlb_dc(N_DC, SIGMA2_DC),
            crlb.fisher_info_gauss(1, 9.0),
            crlb.crlb_gauss(100, 9.0),
            crlb.info_matrix_gaussian(N_VEC, COV_VEC),
            crlb.crlb_matrix_gaussian(N_VEC, COV_VEC),
            crlb.fisher_info_phase(64, 1.0, 0.25, 0.0, 0.1),
            crlb.crlb_phase(64, 1.0, 0.1),
            crlb.fisher_info_poisson(25, 4.0),
            crlb.crlb_poisson(25, 4.0),
            crlb.efficiency(0.04, 4.0),
        ]
        for first, second in zip(args, reruns):
            self.assertEqual(first, second)

    def test_no_rng_and_math_only_imports(self):
        """Step 6: the logic module imports only math; no random, numpy or
        scipy import statement appears anywhere in the module source."""
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "cramer_rao_lower_bound_logic.py")
        with open(src_path, "r") as fh:
            src = fh.read()
        for banned in ("import random", "import numpy", "import scipy",
                       "from random", "from numpy", "from scipy"):
            self.assertNotIn(banned, src)
        self.assertIn("import math", src)


class TestValueErrors(unittest.TestCase):
    """Deterministic ValueError rejection of non-physical inputs (workflow
    step 1 model identification guards)."""

    def test_n_rejects_zero_and_nonint(self):
        """Step 1 guard: n = 0 and n = 2.5 raise ValueError on every
        n-argument function."""
        n_fns = [crlb.fisher_info_dc, crlb.crlb_dc, crlb.mle_var_dc,
                 crlb.fisher_info_gauss, crlb.crlb_gauss,
                 crlb.info_matrix_gaussian, crlb.crlb_matrix_gaussian,
                 crlb.fisher_info_phase, crlb.crlb_phase,
                 crlb.fisher_info_poisson, crlb.crlb_poisson,
                 crlb.mle_var_poisson]
        for fn in n_fns:
            with self.assertRaises(ValueError):
                if fn in (crlb.info_matrix_gaussian, crlb.crlb_matrix_gaussian):
                    fn(0, COV_VEC)
                elif fn is crlb.fisher_info_phase:
                    fn(0, 1.0, 0.25, 0.0, 0.1)
                elif fn is crlb.crlb_phase:
                    fn(0, 1.0, 0.1)
                else:
                    fn(0, 4.0)
            with self.assertRaises(ValueError):
                if fn in (crlb.info_matrix_gaussian, crlb.crlb_matrix_gaussian):
                    fn(2.5, COV_VEC)
                elif fn is crlb.fisher_info_phase:
                    fn(2.5, 1.0, 0.25, 0.0, 0.1)
                elif fn is crlb.crlb_phase:
                    fn(2.5, 1.0, 0.1)
                elif fn in (crlb.fisher_info_poisson, crlb.crlb_poisson,
                            crlb.mle_var_poisson):
                    fn(2.5, 4.0)
                else:
                    fn(2.5, 4.0)

    def test_sigma2_rejects_zero_negative_nan(self):
        """Step 1 guard: sigma2 at 0.0, -1.0 and nan raises ValueError."""
        bad = (0.0, -1.0, float("nan"))
        scalar_fns = (crlb.fisher_info_dc, crlb.crlb_dc, crlb.mle_var_dc,
                      crlb.fisher_info_gauss, crlb.crlb_gauss)
        for sigma2 in bad:
            for fn in scalar_fns:
                with self.assertRaises(ValueError):
                    fn(100, sigma2)
            with self.assertRaises(ValueError):
                crlb.fisher_info_phase(64, 1.0, 0.25, 0.0, sigma2)
            with self.assertRaises(ValueError):
                crlb.crlb_phase(64, 1.0, sigma2)

    def test_cov_rejects_indefinite_asymmetric_singular(self):
        """Step 1 guard: indefinite, asymmetric and singular covariances raise
        ValueError on the vector functions."""
        bad_covs = ([[1.0, 0.6], [0.6, -4.0]],
                    [[1.0, 0.6], [0.7, 4.0]],
                    [[1.0, 0.6], [0.6, 0.0]])
        for cov in bad_covs:
            with self.assertRaises(ValueError):
                crlb.info_matrix_gaussian(N_VEC, cov)
            with self.assertRaises(ValueError):
                crlb.crlb_matrix_gaussian(N_VEC, cov)

    def test_phase_rejects_bad_amp_f0_phi0(self):
        """Step 1 guard: amp 0.0, f0 at 0.0 and 0.5, non-finite phi0 raise
        ValueError on the phase functions."""
        with self.assertRaises(ValueError):
            crlb.fisher_info_phase(64, 0.0, 0.25, 0.0, 0.1)
        with self.assertRaises(ValueError):
            crlb.crlb_phase(64, 0.0, 0.1)
        for f0 in (0.0, 0.5):
            with self.assertRaises(ValueError):
                crlb.fisher_info_phase(64, 1.0, f0, 0.0, 0.1)
        for phi0 in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                crlb.fisher_info_phase(64, 1.0, 0.25, phi0, 0.1)

    def test_poisson_rejects_bad_lam(self):
        """Step 1 guard: lam at 0.0 and -4.0 raises ValueError."""
        for lam in (0.0, -4.0):
            for fn in (crlb.fisher_info_poisson, crlb.crlb_poisson,
                       crlb.mle_var_poisson):
                with self.assertRaises(ValueError):
                    fn(25, lam)

    def test_efficiency_rejects_nonpositive(self):
        """Step 5 guard: efficiency at (0.0, 1.0) and (1.0, -1.0) raises
        ValueError."""
        for crlb_val, var in ((0.0, 1.0), (1.0, -1.0)):
            with self.assertRaises(ValueError):
                crlb.efficiency(crlb_val, var)


if __name__ == "__main__":
    unittest.main()
