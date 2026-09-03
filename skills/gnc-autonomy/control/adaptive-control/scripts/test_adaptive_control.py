"""Contract test for adaptive_control_logic (MRAC, first-order plant).

Deterministic, offline, stdlib unittest. Run from the repo root:

    python3 skills/gnc-autonomy/control/adaptive-control/scripts/test_adaptive_control.py
"""

import unittest

import adaptive_control_logic as m

# Worked example parameters (spec): unstable plant a_p = 1.0, b_p = 2.0,
# reference model a_m = -1.0, b_m = 1.0, dt = 0.01, gamma_x = gamma_r = 10,
# command = 1.0, x0 = 0.0.
PLANT_A = 1.0
PLANT_B = 2.0
MODEL_A = -1.0
MODEL_B = 1.0
DT = 0.01
GAMMA_X = 10.0
GAMMA_R = 10.0
COMMAND = 1.0
X0 = 0.0

THETA_X_STAR = (MODEL_A - PLANT_A) / PLANT_B  # -1.0 exactly
THETA_R_STAR = MODEL_B / PLANT_B              # 0.5 exactly


def worked_run(steps=3000):
    return m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, GAMMA_X,
                      GAMMA_R, command=COMMAND, x0=X0, steps=steps)


class TestReferenceStep(unittest.TestCase):
    def test_reference_step_first_euler_value(self):
        # xm_next = 0 + dt * (-1 * 0 + 1 * 1) = 0.01
        self.assertEqual(m.reference_step(0.0, 1.0, -1.0, 1.0, 0.01), 0.01)

    def test_reference_step_moves_toward_steady_command(self):
        # From xm = 0.5 the step pulls toward 1.0: 0.5 + 0.01 * (-0.5 + 1).
        self.assertEqual(m.reference_step(0.5, 1.0, -1.0, 1.0, 0.01), 0.505)

    def test_reference_step_unstable_model_raises(self):
        with self.assertRaises(ValueError):
            m.reference_step(0.0, 1.0, 0.0, 1.0, 0.01)
        with self.assertRaises(ValueError):
            m.reference_step(0.0, 1.0, 0.5, 1.0, 0.01)


class TestPlantStep(unittest.TestCase):
    def test_plant_step_open_loop_growth(self):
        # Unstable plant, zero control: x_next = 1 + 0.01 * (1 * 1 + 0) = 1.01
        self.assertEqual(m.plant_step(1.0, 0.0, 1.0, 2.0, 0.01), 1.01)

    def test_plant_step_control_effect(self):
        # Zero state, control 1: x_next = 0 + 0.01 * (0 + 2 * 1) = 0.02
        self.assertEqual(m.plant_step(0.0, 1.0, 1.0, 2.0, 0.01), 0.02)


class TestControlOutput(unittest.TestCase):
    def test_control_output_rule(self):
        # u = theta_x * x + theta_r * command = -1.0 * 0.8 + 0.5 * 1.0
        self.assertAlmostEqual(m.control_output(-1.0, 0.5, 0.8, 1.0), -0.3)

    def test_control_output_zero_gains(self):
        self.assertEqual(m.control_output(0.0, 0.0, 0.8, 1.0), 0.0)


class TestIdealGains(unittest.TestCase):
    def test_ideal_gains_worked_example_exact(self):
        self.assertEqual(m.ideal_gains(PLANT_A, PLANT_B, MODEL_A, MODEL_B),
                         {"theta_x_star": -1.0, "theta_r_star": 0.5})

    def test_ideal_gains_general_formula(self):
        # theta_x_star = (a_m - a_p) / b_p = (-4 - (-2)) / 3 = -2/3,
        # theta_r_star = b_m / b_p = 6 / 3 = 2.
        gains = m.ideal_gains(-2.0, 3.0, -4.0, 6.0)
        self.assertAlmostEqual(gains["theta_x_star"], -2.0 / 3.0)
        self.assertAlmostEqual(gains["theta_r_star"], 2.0)

    def test_ideal_gains_zero_bp_raises(self):
        with self.assertRaises(ValueError):
            m.ideal_gains(1.0, 0.0, -1.0, 1.0)


class TestAdaptationStep(unittest.TestCase):
    def test_adaptation_step_exact_rule(self):
        tx, tr = m.adaptation_step(0.1, 0.2, 0.05, 0.5, 1.0, 10.0, 10.0, 0.01)
        # theta_x_new = 0.1 - 10 * 0.05 * 0.5 * 0.01; theta_r_new = 0.2 - 10 * 0.05 * 1 * 0.01
        self.assertEqual(tx, 0.1 - GAMMA_X * 0.05 * 0.5 * 0.01)
        self.assertEqual(tr, 0.2 - GAMMA_R * 0.05 * 1.0 * 0.01)

    def test_adaptation_step_zero_gamma_keeps_gains(self):
        tx, tr = m.adaptation_step(0.3, 0.7, 0.1, 0.5, 1.0, 0.0, 0.0, 0.01)
        self.assertEqual((tx, tr), (0.3, 0.7))

    def test_adaptation_step_single_zero_rate(self):
        # gamma_r = 0 freezes theta_r while theta_x still adapts.
        tx, tr = m.adaptation_step(0.3, 0.7, 0.1, 0.5, 1.0, 10.0, 0.0, 0.01)
        self.assertNotEqual(tx, 0.3)
        self.assertEqual(tr, 0.7)

    def test_adaptation_step_negative_gamma_x_raises(self):
        with self.assertRaises(ValueError):
            m.adaptation_step(0.0, 0.0, 0.1, 0.5, 1.0, -1.0, 10.0, 0.01)

    def test_adaptation_step_negative_gamma_r_raises(self):
        with self.assertRaises(ValueError):
            m.adaptation_step(0.0, 0.0, 0.1, 0.5, 1.0, 10.0, -0.5, 0.01)


class TestSimulateWorkedExample(unittest.TestCase):
    def test_simulate_worked_example_converged(self):
        self.assertTrue(worked_run(3000)["converged"])

    def test_simulate_worked_example_gain_bands(self):
        res = worked_run(3000)
        tx, tr = res["theta_x_list"][-1], res["theta_r_list"][-1]
        self.assertGreaterEqual(tx, -1.1)
        self.assertLessEqual(tx, -0.9)
        self.assertGreaterEqual(tr, 0.45)
        self.assertLessEqual(tr, 0.55)

    def test_simulate_worked_example_gains_within_tolerance(self):
        res = worked_run(3000)
        tx, tr = res["theta_x_list"][-1], res["theta_r_list"][-1]
        self.assertLess(abs(tx - THETA_X_STAR), 0.05)
        self.assertLess(abs(tr - THETA_R_STAR), 0.05)

    def test_simulate_worked_example_tracking(self):
        res = worked_run(3000)
        self.assertLess(abs(res["error_final"]), 1e-3)
        self.assertGreaterEqual(res["x_list"][-1], 0.99)
        self.assertLessEqual(res["x_list"][-1], 1.01)

    def test_simulate_worked_example_tail_window(self):
        res = worked_run(3000)
        errors = [xi - mi for xi, mi in zip(res["x_list"], res["xm_list"])]
        self.assertLess(max(abs(e) for e in errors[-200:]), 1e-4)

    def test_simulate_2000_step_soft_bounds(self):
        # Spec anchor: after 2000 steps the tracking error magnitude is below
        # 1e-3 and the final gains already sit inside the worked bands; the
        # strict converged verdict needs about 2070 steps, so the example runs
        # 3000 steps (documented in SKILL.md).
        res = worked_run(2000)
        self.assertLess(abs(res["error_final"]), 1e-3)
        tx, tr = res["theta_x_list"][-1], res["theta_r_list"][-1]
        self.assertGreaterEqual(tx, -1.1)
        self.assertLessEqual(tx, -0.9)
        self.assertGreaterEqual(tr, 0.45)
        self.assertLessEqual(tr, 0.55)


class TestSimulateBehaviour(unittest.TestCase):
    def test_simulate_no_adaptation_instability_guard(self):
        # With gamma 0 the controller is inert and the unstable plant blows
        # up: |x| at step 500 must exceed 10, proving the adaptation does
        # the stabilization work in the converged run.
        res = m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, 0.0, 0.0,
                         command=COMMAND, x0=1.0, steps=600)
        self.assertGreater(abs(res["x_list"][500]), 10.0)

    def test_simulate_zero_gamma_gains_stay_zero(self):
        res = m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, 0.0, 0.0,
                         command=COMMAND, x0=X0, steps=500)
        self.assertTrue(all(tx == 0.0 for tx in res["theta_x_list"]))
        self.assertTrue(all(tr == 0.0 for tr in res["theta_r_list"]))

    def test_simulate_determinism(self):
        a = worked_run(3000)
        b = worked_run(3000)
        self.assertEqual(a["x_list"], b["x_list"])
        self.assertEqual(a["xm_list"], b["xm_list"])
        self.assertEqual(a["theta_x_list"], b["theta_x_list"])
        self.assertEqual(a["theta_r_list"], b["theta_r_list"])

    def test_simulate_history_lengths(self):
        res = worked_run(1000)
        n = 1001
        self.assertEqual(len(res["t_list"]), n)
        self.assertEqual(len(res["x_list"]), n)
        self.assertEqual(len(res["xm_list"]), n)
        self.assertEqual(len(res["u_list"]), n)
        self.assertEqual(len(res["theta_x_list"]), n)
        self.assertEqual(len(res["theta_r_list"]), n)
        self.assertEqual(res["t_list"][0], 0.0)
        self.assertEqual(res["t_list"][-1], 10.0)

    def test_reference_closed_form_identity(self):
        # xm_k = (b_m / -a_m) * command * (1 - (1 + a_m*dt)^k) for xm_0 = 0.
        res = worked_run(2000)
        q = 1.0 + MODEL_A * DT
        for k in (10, 500, 2000):
            closed = (MODEL_B / -MODEL_A) * COMMAND * (1.0 - q ** k)
            self.assertAlmostEqual(res["xm_list"][k], closed, places=9)

    def test_gain_convergence_report_worked_example(self):
        rep = m.gain_convergence_report(PLANT_A, PLANT_B, MODEL_A, MODEL_B,
                                        DT, GAMMA_X, GAMMA_R, command=COMMAND,
                                        x0=X0, steps=3000)
        self.assertEqual(rep["theta_x_star"], -1.0)
        self.assertEqual(rep["theta_r_star"], 0.5)
        self.assertAlmostEqual(rep["theta_x_error"],
                               rep["theta_x_final"] - rep["theta_x_star"])
        self.assertAlmostEqual(rep["theta_r_error"],
                               rep["theta_r_final"] - rep["theta_r_star"])
        self.assertLess(abs(rep["theta_x_error"]), 0.05)
        self.assertLess(abs(rep["theta_r_error"]), 0.05)
        self.assertLess(rep["tracking_rmse"], 1e-3)

    def test_simulate_control_effort_equilibrium(self):
        # At the converged steady state u = -b_m * command / b_p + ... the
        # control cancels the unstable pole: u_final about -0.5 for command 1.
        res = worked_run(3000)
        self.assertAlmostEqual(res["u_list"][-1], -0.5, places=2)


class TestSimulateValidation(unittest.TestCase):
    def test_simulate_invalid_model_a_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, 0.0, MODEL_B, DT, GAMMA_X, GAMMA_R)
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, 1.0, MODEL_B, DT, GAMMA_X, GAMMA_R)

    def test_simulate_invalid_dt_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, 0.0, GAMMA_X, GAMMA_R)
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, -0.01, GAMMA_X, GAMMA_R)

    def test_simulate_invalid_steps_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, GAMMA_X, GAMMA_R,
                       steps=1)
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, GAMMA_X, GAMMA_R,
                       steps=0)

    def test_simulate_invalid_gamma_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, -1.0, GAMMA_R)
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, PLANT_B, MODEL_A, MODEL_B, DT, GAMMA_X, -0.5)

    def test_simulate_zero_plant_b_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(PLANT_A, 0.0, MODEL_A, MODEL_B, DT, GAMMA_X, GAMMA_R)


if __name__ == "__main__":
    unittest.main()
