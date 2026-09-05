"""Contract test for the reliability-growth-analysis leaf (arp4761a pack).

Exercises the numbered SKILL.md workflow end to end: step 2, the quick
Duane growth check over the log cumulative failure rate, returns the
growth slope, beta_duane and the current MTBF of the fitted line; step
3, the Crow-AMSAA MLE fit, returns the amsaa shape beta by bisection of
the profile-likelihood equation, the lambda scale and the standard
current MTBF at the truncation time; step 4 reads the growth verdict
off the fitted shape against the exact 1.0 boundary; step 5 projects
the fitted MTBF to a target cumulative test time; step 6 inverts the
projection for the test hours at which the fitted MTBF reaches a
target; step 7 confirms the identities and the deterministic rejection
of non-physical inputs. Every assertion targets the real outputs of
scripts/reliability_growth_analysis_logic.py on the spec worked sets
within the spec tolerances. Offline, deterministic, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reliability_growth_analysis_logic import (  # noqa: E402
    BISECT_HI,
    BISECT_LO,
    BISECT_MAX_ITER,
    BISECT_TOL,
    MIN_FAILURES,
    amsaa_mle,
    duane_fit,
    growth_verdict,
    projected_mtbf,
    test_hours_to_target_mtbf,
)

IMPROVING_TIMES = [200.0, 420.0, 800.0, 1500.0, 3000.0, 5000.0]
IMPROVING_TOTAL = 8000.0
DEGRADING_TIMES = [500.0, 800.0, 1050.0, 1250.0, 1400.0, 1500.0]
DEGRADING_TOTAL = 1600.0


class DuaneFitTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the quick Duane growth check."""

    def test_duane_worked_example_slope_intercept_beta(self):
        """The quick Duane growth check on the improving set returns the
        growth slope, intercept and beta_duane of the spec worked example
        within 1e-9."""
        fit = duane_fit(IMPROVING_TIMES, evaluation_time=8000.0)
        self.assertAlmostEqual(fit["slope"], -0.465700634065, delta=1e-9)
        self.assertAlmostEqual(fit["intercept"], -2.63108358662, delta=1e-9)
        self.assertAlmostEqual(fit["beta_duane"], 0.534299365935, delta=1e-9)

    def test_duane_worked_example_current_mtbf(self):
        """The Duane growth check current MTBF at 8000 h of the fitted line
        matches the spec anchor within 1e-3."""
        fit = duane_fit(IMPROVING_TIMES, evaluation_time=8000.0)
        self.assertAlmostEqual(fit["current_mtbf"], 1708.25187489, delta=1e-3)

    def test_duane_default_evaluation_time_and_result_keys(self):
        """The Duane growth check defaults the evaluation time to the last
        failure time and returns exactly the slope, intercept, beta_duane,
        evaluation_time and current_mtbf keys."""
        fit = duane_fit(IMPROVING_TIMES)
        self.assertEqual(fit["evaluation_time"], 5000.0)
        self.assertEqual(
            set(fit.keys()),
            {"slope", "intercept", "beta_duane", "evaluation_time",
             "current_mtbf"})

    def test_duane_improving_signature_negative_slope(self):
        """On the improving set the Duane growth check slope is negative
        and beta_duane sits below 1.0, the growth signature."""
        fit = duane_fit(IMPROVING_TIMES, evaluation_time=8000.0)
        self.assertLess(fit["slope"], 0.0)
        self.assertLess(fit["beta_duane"], 1.0)

    def test_duane_degrading_set_positive_slope(self):
        """The quick Duane growth check on the wear-out style set gives the
        positive slope 0.595086501988 within 1e-9 and a beta_duane above
        1.0, flagging degrading data."""
        fit = duane_fit(DEGRADING_TIMES, evaluation_time=1600.0)
        self.assertAlmostEqual(fit["slope"], 0.595086501988, delta=1e-9)
        self.assertGreater(fit["beta_duane"], 1.0)
        self.assertAlmostEqual(fit["beta_duane"], 1.595086501988, delta=1e-9)

    def test_duane_rejects_fewer_than_two_failures(self):
        """The Duane growth check guard clause rejects a single failure
        event as a non-physical input."""
        with self.assertRaises(ValueError):
            duane_fit([100.0])

    def test_duane_rejects_nonpositive_failure_time(self):
        """The quick Duane growth check rejects a zero or negative failure
        time as non-physical."""
        for bad in ([0.0, 500.0], [-10.0, 500.0]):
            with self.assertRaises(ValueError):
                duane_fit(bad)

    def test_duane_rejects_decreasing_failure_times(self):
        """The quick Duane growth check rejects decreasing failure times,
        which cannot be cumulative event times."""
        with self.assertRaises(ValueError):
            duane_fit([5000.0, 3000.0, 1500.0])

    def test_duane_rejects_evaluation_below_last_failure(self):
        """The Duane growth check rejects an evaluation_time below the last
        failure time as non-physical."""
        with self.assertRaises(ValueError):
            duane_fit(IMPROVING_TIMES, evaluation_time=100.0)

    def test_duane_rejects_all_equal_times(self):
        """The quick Duane growth check rejects all-equal failure times,
        where the ln-time variance is zero and the OLS slope is
        undefined."""
        with self.assertRaises(ValueError):
            duane_fit([400.0, 400.0, 400.0])

    def test_duane_rejects_nonpositive_evaluation_time(self):
        """The Duane growth check rejects a non-positive evaluation_time as
        non-physical."""
        with self.assertRaises(ValueError):
            duane_fit(IMPROVING_TIMES, evaluation_time=0.0)


class AmSaaMleTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the Crow-AMSAA MLE fit."""

    def test_amsaa_worked_beta_lambda_mtbf(self):
        """The Crow-AMSAA MLE fit on the improving set returns the amsaa
        shape beta 0.497379804338 within 1e-9, lambda_hat 0.0686804475182
        within 1e-9 and the current MTBF 2680.71466051 within 1e-3."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        self.assertAlmostEqual(mle["beta_hat"], 0.497379804338, delta=1e-9)
        self.assertAlmostEqual(mle["lambda_hat"], 0.0686804475182, delta=1e-9)
        self.assertAlmostEqual(mle["current_mtbf"], 2680.71466051, delta=1e-3)

    def test_amsaa_bisection_root_matches_closed_form(self):
        """The Crow-AMSAA bisection root equals the closed form N / S of
        the profile-likelihood equation within 1e-9."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        s_total = sum(math.log(8000.0 / t) for t in IMPROVING_TIMES)
        self.assertAlmostEqual(mle["beta_hat"], 6.0 / s_total, delta=1e-9)
        self.assertAlmostEqual(
            mle["beta_hat"], 0.4973798043379676, delta=1e-9)

    def test_amsaa_bisection_iteration_count(self):
        """The deterministic bisection of the MLE equation converges in 43
        passes on the worked set, within the 200 pass cap."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        self.assertEqual(mle["bisection_iterations"], 43)
        self.assertLessEqual(mle["bisection_iterations"], BISECT_MAX_ITER)

    def test_amsaa_scale_identity(self):
        """The Crow-AMSAA scale identity holds: lambda_hat times
        total_time**beta_hat equals the failure count 6 within 1e-9."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        self.assertAlmostEqual(
            mle["lambda_hat"] * 8000.0 ** mle["beta_hat"], 6.0, delta=1e-9)

    def test_amsaa_current_mtbf_identity(self):
        """The Crow-AMSAA current MTBF identity holds: current_mtbf times
        the failure count times beta_hat equals the truncation time within
        1e-9."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        self.assertAlmostEqual(
            mle["current_mtbf"] * 6.0 * mle["beta_hat"], 8000.0, delta=1e-9)

    def test_amsaa_degrading_set_fit(self):
        """The Crow-AMSAA MLE fit on the wear-out set returns the amsaa
        shape beta 2.20390414872 within 1e-9 and the current MTBF
        120.997397651 within 1e-3, both above and below their improving-set
        counterparts."""
        mle = amsaa_mle(DEGRADING_TIMES, DEGRADING_TOTAL)
        self.assertAlmostEqual(mle["beta_hat"], 2.20390414872, delta=1e-9)
        self.assertAlmostEqual(mle["current_mtbf"], 120.997397651, delta=1e-3)
        self.assertEqual(mle["n_failures"], 6)

    def test_amsaa_rejects_failure_at_or_above_truncation(self):
        """The Crow-AMSAA MLE fit guard clause rejects a failure time at or
        above the truncation time as non-physical."""
        with self.assertRaises(ValueError):
            amsaa_mle([200.0, 420.0, 800.0], 800.0)
        with self.assertRaises(ValueError):
            amsaa_mle([200.0, 420.0, 900.0], 800.0)

    def test_amsaa_rejects_root_outside_fixed_bracket(self):
        """The Crow-AMSAA MLE fit rejects the extreme set whose N / S root
        of 16.56 lies above the fixed bracket top 10.0."""
        with self.assertRaises(ValueError):
            amsaa_mle([1000.0, 1100.0, 1150.0, 1175.0, 1180.0, 1185.0],
                      1200.0)

    def test_amsaa_rejects_fewer_than_two_failures(self):
        """The Crow-AMSAA MLE fit guard clause rejects a single failure
        event as a non-physical input."""
        with self.assertRaises(ValueError):
            amsaa_mle([100.0], 500.0)

    def test_amsaa_rejects_decreasing_times_and_bad_truncation(self):
        """The Crow-AMSAA MLE fit rejects decreasing failure times and a
        non-positive truncation time as non-physical inputs."""
        with self.assertRaises(ValueError):
            amsaa_mle([500.0, 300.0], 800.0)
        with self.assertRaises(ValueError):
            amsaa_mle(IMPROVING_TIMES, 0.0)


class ProjectionTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the MTBF projection."""

    def test_projected_mtbf_worked_value(self):
        """The MTBF projection to 12000 cumulative test hours under the
        fitted improving shape returns 3286.68144148 within 1e-3."""
        value = projected_mtbf(12000.0, 8000.0, 6, 0.497379804338)
        self.assertAlmostEqual(value, 3286.68144148, delta=1e-3)

    def test_projected_mtbf_at_truncation_exact(self):
        """The MTBF projection at a target_time equal to the truncation
        time returns the current MTBF exactly."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        value = projected_mtbf(8000.0, 8000.0, 6, mle["beta_hat"])
        self.assertEqual(value, mle["current_mtbf"])

    def test_projected_mtbf_monotone_while_below_one(self):
        """The MTBF projection is monotone increasing in the target time
        while the fitted shape beta stays below 1.0."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        p8 = projected_mtbf(8000.0, 8000.0, 6, mle["beta_hat"])
        p12 = projected_mtbf(12000.0, 8000.0, 6, mle["beta_hat"])
        p16 = projected_mtbf(16000.0, 8000.0, 6, mle["beta_hat"])
        self.assertLess(p8, p12)
        self.assertLess(p12, p16)

    def test_projected_mtbf_rejects_nonphysical_inputs(self):
        """The MTBF projection rejects a non-positive target time and a
        failure count below the two-event minimum as non-physical."""
        with self.assertRaises(ValueError):
            projected_mtbf(0.0, 8000.0, 6, 0.497379804338)
        with self.assertRaises(ValueError):
            projected_mtbf(-5000.0, 8000.0, 6, 0.497379804338)
        with self.assertRaises(ValueError):
            projected_mtbf(12000.0, 8000.0, 1, 0.497379804338)


class TargetHoursTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the test-hours inversion."""

    def test_target_hours_worked_value(self):
        """The test-hours inversion to a 5000 h target MTBF under the
        fitted improving shape returns 27650.7080495 cumulative test hours
        within 1e-3."""
        value = test_hours_to_target_mtbf(5000.0, 8000.0, 6, 0.497379804338)
        self.assertAlmostEqual(value, 27650.7080495, delta=1e-3)

    def test_target_hours_round_trip(self):
        """Inverting the MTBF projection at the computed tau returns the
        target MTBF 5000.0 within 1e-6, the round-trip identity."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        tau = test_hours_to_target_mtbf(5000.0, 8000.0, 6, mle["beta_hat"])
        back = projected_mtbf(tau, 8000.0, 6, mle["beta_hat"])
        self.assertAlmostEqual(back, 5000.0, delta=1e-6)

    def test_target_hours_below_current_mtbf_stays_below_truncation(self):
        """A target MTBF below the current MTBF returns the closed-form tau
        below the truncation time and still round-trips to the target."""
        mle = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        self.assertGreater(mle["current_mtbf"], 2000.0)
        tau = test_hours_to_target_mtbf(2000.0, 8000.0, 6, mle["beta_hat"])
        self.assertLess(tau, 8000.0)
        back = projected_mtbf(tau, 8000.0, 6, mle["beta_hat"])
        self.assertAlmostEqual(back, 2000.0, delta=1e-6)

    def test_target_hours_rejects_no_growth_beta(self):
        """The test-hours inversion rejects a shape beta at or above 1.0,
        where the target MTBF is unreachable by continued testing."""
        for beta in (1.0, 1.3, 2.20390414872):
            with self.assertRaises(ValueError):
                test_hours_to_target_mtbf(5000.0, 8000.0, 6, beta)

    def test_target_hours_rejects_nonpositive_target(self):
        """The test-hours inversion rejects a non-positive target MTBF as
        non-physical."""
        with self.assertRaises(ValueError):
            test_hours_to_target_mtbf(0.0, 8000.0, 6, 0.497379804338)


class GrowthVerdictTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the growth verdict."""

    def test_verdict_improving_branch(self):
        """The growth verdict rates a shape beta of 0.7 improving and its
        dict keys are exactly beta and verdict."""
        result = growth_verdict(0.7)
        self.assertEqual(set(result.keys()), {"beta", "verdict"})
        self.assertEqual(result["verdict"], "improving")
        self.assertEqual(result["beta"], 0.7)

    def test_verdict_hpp_constant_boundary(self):
        """The growth verdict rates a shape beta of exactly 1.0
        hpp-constant, the constant-rate boundary read off the returned
        float without tolerance."""
        result = growth_verdict(1.0)
        self.assertEqual(result["verdict"], "hpp-constant")

    def test_verdict_degrading_branch(self):
        """The growth verdict rates a shape beta of 1.3 degrading."""
        result = growth_verdict(1.3)
        self.assertEqual(result["verdict"], "degrading")

    def test_verdict_follows_amsaa_both_sides(self):
        """The growth verdict applied to the fitted amsaa shape beta rates
        the improving set improving and the degrading set degrading."""
        improving = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        degrading = amsaa_mle(DEGRADING_TIMES, DEGRADING_TOTAL)
        self.assertEqual(growth_verdict(improving["beta_hat"])["verdict"],
                         "improving")
        self.assertEqual(growth_verdict(degrading["beta_hat"])["verdict"],
                         "degrading")


class DeterminismTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, contract confirmation."""

    def test_repeated_runs_bit_identical(self):
        """Repeated Duane growth checks and Crow-AMSAA fits return
        bit-identical dicts and the module constants anchor the workflow:
        the two-failure minimum, the fixed bisection bracket and its
        tolerance and cap, so step 7 confirmation is deterministic."""
        first = duane_fit(IMPROVING_TIMES, evaluation_time=8000.0)
        second = duane_fit(IMPROVING_TIMES, evaluation_time=8000.0)
        self.assertEqual(first, second)
        mle_first = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        mle_second = amsaa_mle(IMPROVING_TIMES, IMPROVING_TOTAL)
        self.assertEqual(mle_first, mle_second)
        self.assertEqual(MIN_FAILURES, 2)
        self.assertEqual(BISECT_LO, 1e-6)
        self.assertEqual(BISECT_HI, 10.0)
        self.assertEqual(BISECT_TOL, 1e-12)
        self.assertEqual(BISECT_MAX_ITER, 200)


if __name__ == "__main__":
    unittest.main()
