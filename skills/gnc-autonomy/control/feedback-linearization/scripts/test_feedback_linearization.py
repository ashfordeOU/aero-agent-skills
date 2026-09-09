"""Contract test for gnc-autonomy/control/feedback-linearization.

Exercises the SKILL.md Workflow steps: step 2 (Lie derivatives and the
relative-degree probe), step 3 (establishing the relative degree), step 4
(the decoupling scalar and the linearizing control that cancels the
nonlinear terms), step 5 (the outer linear command at the assigned
closed-loop pole rate), step 6 (the RK4 closed-loop simulation against
the exact closed form and the measured pole witness), and step 7 (the
zero-dynamics stability check of the internal dynamics that gates the
design). Deterministic, offline, stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feedback_linearization_logic as fl

X0 = (0.5, 0.0)


class TestLieDerivativesAndRelativeDegree(unittest.TestCase):
    """Step 2 and step 3: Lie derivatives along the drift field, the
    control-channel probe, and the relative-degree defining property."""

    def test_f_and_g_vector_fields_and_lie_derivatives(self):
        f1, f2 = fl.f(X0)
        self.assertAlmostEqual(f1, -0.5, delta=1e-12)
        self.assertAlmostEqual(f2, 0.125, delta=1e-12)
        self.assertEqual(fl.g(X0), (0.0, 0.5))
        self.assertAlmostEqual(fl.Lf_power_h("x2", X0, 1), 0.125, delta=1e-12)
        self.assertAlmostEqual(fl.Lf_power_h("x1", X0, 2), 0.625, delta=1e-12)

    def test_relative_degree_x2_at_x0(self):
        r, table = fl.relative_degree("x2", X0)
        self.assertEqual(r, 1)
        self.assertEqual(len(table), 1)
        self.assertAlmostEqual(table[0][1], 0.5, delta=1e-12)

    def test_relative_degree_x1_at_x0_includes_zero_probe(self):
        r, table = fl.relative_degree("x1", X0)
        self.assertEqual(r, 2)
        self.assertEqual(len(table), 2)
        self.assertEqual(fl.Lg_Lf_power_h("x1", X0, 0), 0.0)
        self.assertAlmostEqual(table[0][1], 0.0, delta=1e-12)
        self.assertAlmostEqual(table[1][1], 0.5, delta=1e-12)


class TestDecouplingAndLinearizingControl(unittest.TestCase):
    """Step 4: invert the decoupling scalar to form the linearizing
    control that cancels the nonlinear terms exactly."""

    def test_decoupling_scalar_at_x0_both_outputs(self):
        self.assertAlmostEqual(fl.decoupling_scalar("x2", X0), 0.5, delta=1e-12)
        self.assertAlmostEqual(fl.decoupling_scalar("x1", X0), 0.5, delta=1e-12)

    def test_decoupling_scalar_at_probe_state(self):
        self.assertAlmostEqual(fl.decoupling_scalar("x2", (1.0, 0.75)), 1.0, delta=1e-12)

    def test_linearizing_control_r1_at_x0(self):
        u = fl.linearizing_control("x2", X0, 2.0)
        self.assertAlmostEqual(u, 3.75, delta=1e-9)

    def test_linearizing_control_r2_at_x0(self):
        u = fl.linearizing_control("x1", X0, 4.0)
        self.assertAlmostEqual(u, 6.75, delta=1e-9)

    def test_cancellation_identity_at_several_states(self):
        for x, v in ((X0, 2.0), ((1.0, 0.75), 3.0)):
            with self.subTest(x=x):
                _, f2 = fl.f(x)
                a = fl.decoupling_scalar("x2", x)
                u = fl.linearizing_control("x2", x, v)
                residual = f2 + a * u - v
                self.assertAlmostEqual(residual, 0.0, delta=1e-12)

    def test_linearizing_control_from_zero_decoupling_raises(self):
        with self.assertRaises(ValueError) as cm:
            fl.linearizing_control_from(1.0, 0.0, 1.0)
        self.assertEqual(
            str(cm.exception),
            "decoupling scalar a(x) = 0.0 is zero (|a| <= INV_EPS = 1e-12): the "
            "linearizing control u = (v - L_f^r h) / a(x) is not defined",
        )


class TestOuterCommandAndClosedLoop(unittest.TestCase):
    """Step 5 and step 6: the outer linear tracking loop at the assigned
    closed-loop pole rate, run through the RK4 closed-loop simulation and
    checked against the exact closed form."""

    def test_outer_command_values_at_x0(self):
        self.assertAlmostEqual(fl.outer_command("x2", X0), 2.0, delta=1e-12)
        self.assertAlmostEqual(fl.outer_command("x1", X0), 4.0, delta=1e-12)

    def test_closed_loop_r1_matches_closed_form(self):
        sim = fl.closed_loop_sim("x2")
        self.assertEqual(len(sim["t"]), 10001)
        err = fl.series_max_abs_error(sim["y"], fl.closed_form_r1, sim["t"])
        self.assertLess(err, 1e-9)

    def test_closed_loop_r1_sample_values(self):
        sim = fl.closed_loop_sim("x2")
        expected = {
            0.5: 0.632120558829,
            1.0: 0.864664716763,
            2.0: 0.981684361111,
            3.0: 0.997521247823,
            5.0: 0.999954600070,
        }
        for t, y_expected in expected.items():
            with self.subTest(t=t):
                (y_val,) = fl.sample_series(sim["t"], sim["y"], [t])
                self.assertAlmostEqual(y_val, y_expected, delta=1e-9)

    def test_closed_loop_r1_settling_time(self):
        sim = fl.closed_loop_sim("x2")
        band = 1e-3
        settle_t = None
        for t, y in zip(sim["t"], sim["y"]):
            if abs(y - fl.Y_REF) <= band:
                settle_t = t
                break
        self.assertIsNotNone(settle_t)
        self.assertAlmostEqual(settle_t, 3.453878, delta=0.02)

    def test_measured_decay_rate_pole_witness(self):
        sim = fl.closed_loop_sim("x2")
        rate = fl.measured_decay_rate(sim["y"], sim["t"], 0.5, 1.0)
        self.assertAlmostEqual(rate, fl.CL_RATE_K, delta=1e-3)

    def test_closed_loop_r2_matches_closed_form_and_double_pole(self):
        sim = fl.closed_loop_sim("x1")
        err = fl.series_max_abs_error(sim["y"], fl.closed_form_r2, sim["t"])
        self.assertLess(err, 1e-9)
        y0 = X0[0]
        ydot0 = -fl.A11 * X0[0] + X0[1]
        b_coeff = ydot0 + fl.CL_RATE_K * (y0 - fl.Y_REF)
        self.assertAlmostEqual(b_coeff, -1.5, delta=1e-12)
        self.assertNotAlmostEqual(b_coeff, 0.0, delta=1e-9)

    def test_closed_loop_r2_sample_values(self):
        sim = fl.closed_loop_sim("x1")
        expected = {1.0: 0.72932943352683755, 3.0: 0.98760623911666501, 6.0: 0.9999416299826438}
        for t, y_expected in expected.items():
            with self.subTest(t=t):
                (y_val,) = fl.sample_series(sim["t"], sim["y"], [t])
                self.assertAlmostEqual(y_val, y_expected, delta=1e-9)

    def test_steady_state_and_control_history_r1(self):
        sim = fl.closed_loop_sim("x2")
        self.assertAlmostEqual(sim["u"][0], 3.75, delta=1e-9)
        self.assertAlmostEqual(sim["u"][-1], -1.999931903196, delta=1e-6)
        closed_form_final = fl.closed_form_r1(fl.SIM_TIME)
        self.assertAlmostEqual(sim["y"][-1], closed_form_final, delta=1e-9)
        self.assertAlmostEqual(sim["y"][-1], 0.999999997939, delta=1e-9)
        self.assertAlmostEqual(sim["x1"][-1], 0.999931902167, delta=1e-9)


class TestInternalDynamicsAndZeroDynamics(unittest.TestCase):
    """Step 7: the internal-dynamics history of the r = 1 design and the
    zero-dynamics stability verdict that gates acceptance."""

    def test_internal_state_matches_closed_form_and_final_value(self):
        sim = fl.closed_loop_sim("x2")

        def x1_closed_form(t):
            return 1.0 - 1.5 * math.exp(-t) + math.exp(-2.0 * t)

        err = fl.series_max_abs_error(sim["x1"], x1_closed_form, sim["t"])
        self.assertLess(err, 1e-9)
        self.assertAlmostEqual(sim["x1"][-1], x1_closed_form(fl.SIM_TIME), delta=1e-9)

    def test_internal_state_minimum(self):
        sim = fl.closed_loop_sim("x2")
        min_x1 = min(sim["x1"])
        min_t = sim["t"][sim["x1"].index(min_x1)]
        self.assertAlmostEqual(min_x1, 0.4375, delta=1e-6)
        self.assertAlmostEqual(min_t, math.log(4.0 / 3.0), delta=0.01)

    def test_zero_dynamics_verdict_and_constrained_samples(self):
        zd = fl.zero_dynamics_analysis()
        self.assertAlmostEqual(zd["eigenvalue"], -1.0, delta=1e-12)
        self.assertEqual(zd["verdict"], "asymptotically stable")
        expected = {1: 0.18393972058572117, 2: 0.067667641618306351, 5: 0.0033689734995427335}
        for t, x1_expected in expected.items():
            with self.subTest(t=t):
                (x1_val,) = fl.sample_series(zd["t"], zd["x1"], [t])
                self.assertAlmostEqual(x1_val, x1_expected, delta=1e-12)


class TestRelativeDegreeFailureCases(unittest.TestCase):
    """Step 3 rejection path: no finite relative degree exists and the
    decoupling inversion of step 4 is undefined."""

    def test_relative_degree_fails_at_x1_zero(self):
        with self.assertRaises(ValueError) as cm:
            fl.relative_degree("x2", (0.0, 0.5))
        self.assertEqual(
            str(cm.exception),
            "no finite relative degree at state x = (0.0, 0.5) for output 'x2': "
            "L_g L_f^k h = 0 for every k up to the system order N = 2, so the "
            "control channel never reaches the output at this state",
        )

    def test_relative_degree_fails_for_const_output(self):
        with self.assertRaises(ValueError) as cm:
            fl.relative_degree("const", X0)
        self.assertIn("no finite relative degree", str(cm.exception))
        self.assertIn("'const'", str(cm.exception))

    def test_relative_degree_fails_for_unknown_output(self):
        with self.assertRaises(ValueError) as cm:
            fl.relative_degree("bogus", X0)
        self.assertEqual(
            str(cm.exception),
            "unknown output 'bogus': registered outputs are x1, x2, const",
        )

    def test_decoupling_singularity_matches_relative_degree_failure(self):
        with self.assertRaises(ValueError):
            fl.decoupling_scalar("x2", (0.0, 0.3))


class TestGuardsAndDeterminism(unittest.TestCase):
    """Boundary and non-physical input rejection across the module, and
    determinism of the closed-loop simulation used in steps 6 and 7."""

    def test_state_validation_guards(self):
        with self.assertRaises(ValueError) as cm:
            fl.f((0.5, 0.0, 1.0))
        self.assertIn("length", str(cm.exception))
        with self.assertRaises(ValueError):
            fl.f((0.5, "a"))

    def test_closed_loop_sim_scalar_guards(self):
        cases = [
            (dict(k=0.0), "closed-loop rate k must be positive, got 0.0"),
            (dict(dt=0.0), "sample time dt must be positive, got 0.0"),
            (dict(sim_time=0.0), "simulation time sim_time must be positive, got 0.0"),
            (dict(y_ref=0.0), "reference y_ref must be positive, got 0.0"),
        ]
        for kwargs, message in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError) as cm:
                    fl.closed_loop_sim("x2", **kwargs)
                self.assertEqual(str(cm.exception), message)

    def test_unknown_output_guards(self):
        with self.assertRaises(ValueError):
            fl.closed_loop_sim("const")
        with self.assertRaises(ValueError):
            fl.outer_command("bogus", X0)

    def test_module_constants_fixed(self):
        self.assertEqual(fl.A11, 1.0)
        self.assertEqual(fl.CUBIC, 1.0)
        self.assertEqual(fl.QUAD, 1.0)
        self.assertEqual(fl.CL_RATE_K, 2.0)
        self.assertEqual(fl.N, 2)

    def test_determinism_repeated_runs(self):
        sim_a = fl.closed_loop_sim("x2")
        sim_b = fl.closed_loop_sim("x2")
        self.assertEqual(sim_a["y"], sim_b["y"])
        self.assertEqual(sim_a["u"], sim_b["u"])


if __name__ == "__main__":
    unittest.main()
