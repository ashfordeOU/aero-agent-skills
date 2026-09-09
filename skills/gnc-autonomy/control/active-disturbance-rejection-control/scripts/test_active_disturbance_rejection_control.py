#!/usr/bin/env python3
"""Contract test for active-disturbance-rejection-control (gnc-autonomy/control).

Exercises the SKILL.md workflow steps: step 1 fixing the design plant and
the bandwidth-parameterized gains with observer_gains and controller_gains,
step 2 confirming the linear-extended-state-observer characteristic-
polynomial identity with char_poly_residual, step 3 running the closed-loop
adrc simulation with simulate_adrc so the total-disturbance-estimate z3 is
formed from the measured output alone, step 4 auditing the
disturbance-rejection-term u = (u0 - z3)/b0 with cancellation_residual at
the phase fixed points, step 5 reading the tracking-error, command and
total-disturbance-estimate histories across the reference start and the
disturbance step, step 6 comparing against the ideal perfect-cancellation
loop with simulate_ideal to isolate the observer-lag cost, and step 7
running the mismatch robustness case and confirming the fixed estimate
bias. Stdlib unittest, deterministic, offline, no network, no imports
beyond math (test harness also uses importlib and os for the portable
module load).
"""

import importlib.util
import math
import os
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "active_disturbance_rejection_control_logic",
    os.path.join(_SCRIPTS, "active_disturbance_rejection_control_logic.py"),
)
adrc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(adrc)


class TestBandwidthParameterization(unittest.TestCase):
    """Step 1 and step 2 of the SKILL.md workflow: bandwidth-parameterization
    of the observer-gain-parameterization and the controller gains."""

    def test_observer_gains_worked(self):
        beta1, beta2, beta3 = adrc.observer_gains(30.0)
        self.assertAlmostEqual(beta1, 90.0, delta=1e-9)
        self.assertAlmostEqual(beta2, 2700.0, delta=1e-9)
        self.assertAlmostEqual(beta3, 27000.0, delta=1e-9)

    def test_controller_gains_worked(self):
        kp, kd = adrc.controller_gains(5.0)
        self.assertAlmostEqual(kp, 25.0, delta=1e-9)
        self.assertAlmostEqual(kd, 10.0, delta=1e-9)

    def test_char_poly_residual_at_pole(self):
        self.assertLess(abs(adrc.char_poly_residual(-30.0, 30.0)), 1e-9)

    def test_char_poly_residual_off_pole_samples(self):
        for lam in (-3.0, -1.0, 0.5):
            self.assertLess(abs(adrc.char_poly_residual(lam, 30.0)), 1e-9)

    def test_observer_gains_rejects_nonpositive_bandwidth(self):
        with self.assertRaises(ValueError):
            adrc.observer_gains(0.0)

    def test_controller_gains_rejects_nonpositive_bandwidth(self):
        with self.assertRaises(ValueError):
            adrc.controller_gains(0.0)

    def test_char_poly_residual_rejects_nonpositive_bandwidth(self):
        with self.assertRaises(ValueError):
            adrc.char_poly_residual(-1.0, 0.0)


class TestDisturbanceCancellationIdentity(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the disturbance-rejection-term
    audit of the total-disturbance-estimate cancellation."""

    def test_cancellation_residual_zero_when_estimate_matches(self):
        for f, u0 in ((0.0, 0.0), (1.0, -5.0), (0.5, 25.0)):
            res = adrc.cancellation_residual(f, u0, f, 1.0)
            self.assertAlmostEqual(res, 0.0, delta=1e-12)

    def test_control_law_matches_cancellation_residual_arithmetic(self):
        u = adrc.control_law(1.0, 0.2, 0.1, 0.5, 1.0, 25.0, 10.0)
        u0 = 25.0 * (1.0 - 0.2) - 10.0 * 0.1
        self.assertAlmostEqual(u, (u0 - 0.5) / 1.0, delta=1e-12)

    def test_control_law_rejects_zero_b0(self):
        with self.assertRaises(ValueError):
            adrc.control_law(1.0, 0.0, 0.0, 0.0, 0.0, 25.0, 10.0)

    def test_cancellation_residual_rejects_zero_b0(self):
        with self.assertRaises(ValueError):
            adrc.cancellation_residual(0.5, 0.0, 0.5, 0.0)


class TestFixedPointArithmetic(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: phase fixed points of the cancelled
    loop where the total-disturbance-estimate balances the adrc law."""

    def test_total_disturbance_phase_one(self):
        self.assertAlmostEqual(adrc.total_disturbance(1.0, 0.0, 0.5), 0.0, delta=1e-12)

    def test_total_disturbance_phase_two(self):
        self.assertAlmostEqual(adrc.total_disturbance(1.0, 0.0, 1.5), 1.0, delta=1e-12)


class TestIdealClosedForm(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the exact ideal double-integrator
    step response reproduced by the ideal comparison loop."""

    def test_ideal_euler_matches_closed_form_at_one_second(self):
        result = adrc.simulate_ideal()
        idx = round(1.0 / result["dt"])
        exact = 1.0 - 6.0 * math.exp(-5.0)
        self.assertAlmostEqual(result["y"][idx], exact, delta=1e-3)

    def test_ideal_euler_matches_closed_form_at_quarter_second(self):
        result = adrc.simulate_ideal()
        idx = round(0.2 / result["dt"])
        exact = 1.0 - 2.0 * math.exp(-1.0)
        self.assertAlmostEqual(result["y"][idx], exact, delta=1e-3)

    def test_ideal_euler_matches_closed_form_at_half_second(self):
        result = adrc.simulate_ideal()
        idx = round(0.5 / result["dt"])
        exact = 1.0 - 3.5 * math.exp(-2.5)
        self.assertAlmostEqual(result["y"][idx], exact, delta=1e-3)


class TestWorkedAdrcRun(unittest.TestCase):
    """Step 3 and step 5 of the SKILL.md workflow: the closed-loop adrc
    simulation and its tracking-error, command and total-disturbance-
    estimate histories across the reference start and the disturbance
    step."""

    @classmethod
    def setUpClass(cls):
        cls.result = adrc.simulate_adrc()

    def _at(self, t_target):
        idx = round(t_target / self.result["dt"])
        return idx

    def test_sample_points_phase_one(self):
        expected = {
            0.2: 0.259669337601,
            0.5: 0.705882336870,
            1.0: 0.963564880347,
            2.0: 1.000073982338,
            3.0: 1.000006249016,
        }
        for t_target, y_expected in expected.items():
            idx = self._at(t_target)
            self.assertTrue(
                math.isclose(self.result["y"][idx], y_expected, rel_tol=1e-6)
            )

    def test_sample_points_phase_two(self):
        expected = {
            3.05: 1.001168788483,
            3.25: 1.008944174201,
            3.5: 1.006876632387,
            4.0: 1.001300603879,
            5.0: 1.000005228706,
            6.0: 0.999999797512,
        }
        for t_target, y_expected in expected.items():
            idx = self._at(t_target)
            self.assertTrue(
                math.isclose(self.result["y"][idx], y_expected, rel_tol=1e-6)
            )

    def test_final_command_and_estimate(self):
        idx = self._at(6.0)
        self.assertAlmostEqual(self.result["u"][idx], -1.000001803850, delta=1e-4)
        self.assertAlmostEqual(self.result["z3"][idx], 0.999999402193, delta=1e-4)

    def test_final_tracking_error_small(self):
        idx = self._at(6.0)
        self.assertLess(abs(self.result["e"][idx]), 1e-5)

    def test_peak_step_excursion(self):
        self.assertTrue(
            math.isclose(self.result["max_abs_e_rec"], 9.161e-03, rel_tol=1e-2)
        )

    def test_settled_window_residuals(self):
        self.assertLess(self.result["max_abs_e_settle"], 1e-5)
        self.assertLess(self.result["max_z3_res_settle"], 1e-4)

    def test_beta_and_gains_reported(self):
        self.assertEqual(len(self.result["beta"]), 3)
        self.assertAlmostEqual(self.result["kp"], 25.0, delta=1e-9)
        self.assertAlmostEqual(self.result["kd"], 10.0, delta=1e-9)

    def test_sample_count(self):
        self.assertEqual(self.result["n"], 60001)


class TestIdealLoopComparison(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the observer-lag cost of the finite
    bandwidth against the ideal perfect-cancellation loop."""

    @classmethod
    def setUpClass(cls):
        cls.adrc_run = adrc.simulate_adrc()
        cls.ideal_run = adrc.simulate_ideal()

    def test_max_deviation_over_full_horizon(self):
        d_full = max(
            abs(a - b) for a, b in zip(self.adrc_run["y"], self.ideal_run["y"])
        )
        self.assertLess(d_full, 2e-2)
        self.assertTrue(math.isclose(d_full, 9.172e-03, rel_tol=5e-2))

    def test_max_deviation_over_settled_window(self):
        dt = self.adrc_run["dt"]
        idx0 = round(5.5 / dt)
        d_settle = max(
            abs(a - b)
            for a, b in zip(self.adrc_run["y"][idx0:], self.ideal_run["y"][idx0:])
        )
        self.assertLess(d_settle, 1e-5)

    def test_observer_lag_deficit_at_one_second(self):
        idx1 = round(1.0 / self.adrc_run["dt"])
        deficit = self.adrc_run["y"][idx1] - self.ideal_run["y"][idx1]
        self.assertGreater(deficit, 0.0)
        self.assertTrue(math.isclose(deficit, 0.003958874713, rel_tol=1e-2))


class TestMismatchRobustness(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the mismatch robustness run where
    the control-effectiveness estimate b0 over-models the true plant gain."""

    @classmethod
    def setUpClass(cls):
        cls.result = adrc.simulate_adrc(plant_b=adrc.PLANT_B_MISMATCH)

    def test_output_still_settles_at_reference(self):
        idx6 = round(6.0 / self.result["dt"])
        self.assertAlmostEqual(self.result["y"][idx6], 1.0, delta=1e-4)

    def test_command_and_estimate_carry_bias(self):
        idx6 = round(6.0 / self.result["dt"])
        self.assertAlmostEqual(self.result["u"][idx6], -1.25, delta=1e-3)
        self.assertAlmostEqual(self.result["z3"][idx6], 1.25, delta=1e-3)

    def test_bias_equals_gain_mismatch_times_command(self):
        idx6 = round(6.0 / self.result["dt"])
        f_truth = self.result["f"][idx6]
        z3 = self.result["z3"][idx6]
        expected_bias = (adrc.PLANT_B_MISMATCH - adrc.B0) * self.result["u"][idx6]
        self.assertAlmostEqual(z3 - f_truth, expected_bias, delta=1e-2)
        self.assertAlmostEqual(z3 - f_truth, 0.25, delta=1e-3)

    def test_settled_window_error_small(self):
        self.assertLess(self.result["max_abs_e_settle"], 1e-4)


class TestSimulateAdrcValueErrors(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the design-input guards that keep
    the bandwidth-parameterization and the adrc law well posed."""

    def test_rejects_zero_b0(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(b0=0.0)

    def test_rejects_zero_omega_c(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(omega_c=0.0)

    def test_rejects_zero_omega_o(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(omega_o=0.0)

    def test_rejects_omega_o_not_exceeding_omega_c(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(omega_c=5.0, omega_o=5.0)

    def test_rejects_nonpositive_dt(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(dt=0.0)

    def test_rejects_nonpositive_sim_time(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(sim_time=0.0)

    def test_rejects_t_step_outside_horizon(self):
        with self.assertRaises(ValueError):
            adrc.simulate_adrc(t_step=6.0)


class TestDeterminism(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the adrc simulation is deterministic
    run to run, with no randomness anywhere in the module."""

    def test_repeated_runs_are_identical(self):
        run1 = adrc.simulate_adrc()
        run2 = adrc.simulate_adrc()
        self.assertEqual(run1["y"], run2["y"])
        self.assertEqual(run1["z3"], run2["z3"])

    def test_module_constants_pinned(self):
        self.assertAlmostEqual(adrc.OMEGA_C, 5.0, delta=1e-12)
        self.assertAlmostEqual(adrc.OMEGA_O, 30.0, delta=1e-12)
        self.assertAlmostEqual(adrc.B0, 1.0, delta=1e-12)
        self.assertAlmostEqual(adrc.PLANT_B_MISMATCH, 0.8, delta=1e-12)


if __name__ == "__main__":
    unittest.main()
