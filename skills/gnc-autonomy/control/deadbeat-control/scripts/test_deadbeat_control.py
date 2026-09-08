"""Contract test for deadbeat-control (gnc-autonomy/control/deadbeat-control).

Exercises the SKILL.md workflow steps: step 1 fixes the plant pulse
transfer function; step 2 verifies admissibility; step 3 solves the
deadbeat design equation and checks the pole-placement identity; step 4
forms the finite-settling-time controller difference equation; step 5
simulates the closed loop; step 6 reads the settling sample and
settling time from settling_report; step 7 checks the steady-state
tracking with steady_control and control_effort; step 8 confirms the
pure-delay identity with closed_loop_impulse. Stdlib unittest, offline,
deterministic. No imports beyond math (via the logic module) and
unittest.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import deadbeat_control_logic as dc


class TestPolynomialPrimitives(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fix the plant polynomials."""

    def test_polyval_desc_horner(self):
        self.assertAlmostEqual(dc.polyval_desc([1.0, -0.5], 0.5), 0.0, delta=1e-12)
        self.assertAlmostEqual(dc.polyval_desc([2.0, 3.0, 4.0], 1.0), 9.0, delta=1e-12)

    def test_poly_mul_desc(self):
        result = dc.poly_mul_desc([1.0, -0.5], [0.5])
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0], 0.5, delta=1e-12)
        self.assertAlmostEqual(result[1], -0.25, delta=1e-12)

    def test_roots_moduli_desc_degrees(self):
        self.assertEqual(dc.roots_moduli_desc([1.0]), [])
        deg1 = dc.roots_moduli_desc(dc.FIRST_ORDER_A)
        self.assertAlmostEqual(deg1[0], 0.5, delta=1e-9)
        deg2_real = sorted(dc.roots_moduli_desc(dc.SECOND_ORDER_A))
        self.assertAlmostEqual(deg2_real[0], 0.3, delta=1e-9)
        self.assertAlmostEqual(deg2_real[1], 0.8, delta=1e-9)
        deg2_complex = dc.roots_moduli_desc(dc.COMPLEX_POLE_A)
        expected = math.sqrt(0.65)
        self.assertAlmostEqual(deg2_complex[0], expected, delta=1e-9)
        self.assertAlmostEqual(deg2_complex[1], expected, delta=1e-9)

    def test_polynomial_primitives_reject_bad_input(self):
        with self.assertRaises(ValueError):
            dc.polyval_desc([], 1.0)
        with self.assertRaises(ValueError):
            dc.poly_mul_desc([], [1.0])
        with self.assertRaises(ValueError):
            dc.poly_mul_desc([1.0], [])
        with self.assertRaises(ValueError):
            dc.roots_moduli_desc(dc.DEG3_A)
        with self.assertRaises(ValueError):
            dc.roots_moduli_desc([])


class TestAdmissibility(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: verify admissibility before synthesis."""

    def test_admissibility_dict_keys(self):
        result = dc.admissibility_check(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B)
        self.assertEqual(
            set(result.keys()), {"admissible", "pole_moduli", "zero_moduli", "reason"}
        )

    def test_admissibility_scenarios_a_b_c_and_complex_pole(self):
        a = dc.admissibility_check(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B)
        self.assertTrue(a["admissible"])
        self.assertAlmostEqual(a["pole_moduli"][0], 0.5, delta=1e-9)
        self.assertEqual(a["zero_moduli"], [])

        b = dc.admissibility_check(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B)
        self.assertTrue(b["admissible"])
        moduli = sorted(b["pole_moduli"])
        self.assertAlmostEqual(moduli[0], 0.3, delta=1e-9)
        self.assertAlmostEqual(moduli[1], 0.8, delta=1e-9)

        c = dc.admissibility_check(dc.ZERO_A, dc.ZERO_B)
        self.assertTrue(c["admissible"])
        self.assertAlmostEqual(c["zero_moduli"][0], 0.5, delta=1e-9)

        complex_pole = dc.admissibility_check(dc.COMPLEX_POLE_A, dc.COMPLEX_POLE_B)
        self.assertTrue(complex_pole["admissible"])
        expected = math.sqrt(0.65)
        self.assertAlmostEqual(complex_pole["pole_moduli"][0], expected, delta=1e-9)

    def test_admissibility_rejects_unstable_and_boundary_pole(self):
        unstable = dc.admissibility_check(dc.UNSTABLE_A, [0.5])
        self.assertFalse(unstable["admissible"])
        self.assertIn("unstable", unstable["reason"])
        boundary = dc.admissibility_check(dc.BOUNDARY_A, [0.5])
        self.assertFalse(boundary["admissible"])

    def test_admissibility_rejects_nonminimum_and_boundary_zero(self):
        nonmin = dc.admissibility_check(dc.SECOND_ORDER_A, dc.NONMINIMUM_PHASE_B)
        self.assertFalse(nonmin["admissible"])
        self.assertIn("non-minimum-phase", nonmin["reason"])
        boundary_zero = dc.admissibility_check(dc.SECOND_ORDER_A, dc.BOUNDARY_ZERO_B)
        self.assertFalse(boundary_zero["admissible"])


class TestDeadbeatDesign(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: solve the deadbeat design equation."""

    def test_design_dict_keys(self):
        design = dc.deadbeat_design(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B)
        expected_keys = {
            "n", "m", "d", "a_desc", "b_desc", "num_e", "den_u", "mu0",
            "d_num_desc", "d_den_desc", "char_poly_desc", "u_star",
            "plant_dc_gain",
        }
        self.assertEqual(set(design.keys()), expected_keys)

    def test_design_scenario_a(self):
        design = dc.deadbeat_design(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B)
        self.assertEqual(design["n"], 1)
        self.assertEqual(design["m"], 0)
        self.assertEqual(design["d"], 1)
        self.assertAlmostEqual(design["num_e"][0], 2.0, delta=1e-9)
        self.assertAlmostEqual(design["num_e"][1], -1.0, delta=1e-9)
        self.assertAlmostEqual(design["den_u"][0], 1.0, delta=1e-9)
        self.assertAlmostEqual(design["u_star"], 1.0, delta=1e-9)

    def test_design_scenario_b(self):
        design = dc.deadbeat_design(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B)
        self.assertEqual(design["d"], 2)
        for got, want in zip(design["num_e"], [5.0, -5.5, 1.2]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        for got, want in zip(design["den_u"], [0.0, 1.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(design["u_star"], 0.7, delta=1e-6)
        self.assertAlmostEqual(design["plant_dc_gain"], 10.0 / 7.0, delta=1e-6)
        for got, want in zip(design["char_poly_desc"], [0.2, -0.22, 0.048, 0.0, 0.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)

    def test_design_scenario_c_interior_zero(self):
        design = dc.deadbeat_design(dc.ZERO_A, dc.ZERO_B)
        self.assertEqual(design["n"], 2)
        self.assertEqual(design["m"], 1)
        self.assertEqual(design["d"], 1)
        for got, want in zip(design["num_e"], [10.0, -11.0, 2.4]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        for got, want in zip(design["den_u"], [0.5, 0.5]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(design["u_star"], 14.0 / 15.0, delta=1e-6)

    def test_design_pole_placement_identity(self):
        """Step 3: char_poly_desc equals A*D_c + B*N_c, constant-end aligned."""
        design = dc.deadbeat_design(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B)
        a_dc = dc.poly_mul_desc(design["a_desc"], design["d_den_desc"])
        b_nc = dc.poly_mul_desc(design["b_desc"], design["d_num_desc"])
        pad = len(a_dc) - len(b_nc)
        b_nc_aligned = [0.0] * pad + b_nc
        char = design["char_poly_desc"]
        max_diff = max(abs(a_dc[i] + b_nc_aligned[i] - char[i]) for i in range(len(char)))
        self.assertLess(max_diff, 1e-9)

    def test_design_rejects_unstable_and_boundary_pole(self):
        with self.assertRaises(ValueError):
            dc.deadbeat_design(dc.UNSTABLE_A, [0.5])
        with self.assertRaises(ValueError):
            dc.deadbeat_design(dc.BOUNDARY_A, [0.5])

    def test_design_rejects_nonminimum_and_boundary_zero(self):
        with self.assertRaises(ValueError):
            dc.deadbeat_design(dc.SECOND_ORDER_A, dc.NONMINIMUM_PHASE_B)
        with self.assertRaises(ValueError):
            dc.deadbeat_design(dc.SECOND_ORDER_A, dc.BOUNDARY_ZERO_B)

    def test_design_rejects_structural_errors(self):
        with self.assertRaises(ValueError):
            dc.deadbeat_design(dc.DEG3_A, [0.5])
        with self.assertRaises(ValueError):
            dc.deadbeat_design(*dc.NOT_STRICTLY_PROPER)
        with self.assertRaises(ValueError):
            dc.deadbeat_design([], [0.5])
        with self.assertRaises(ValueError):
            dc.deadbeat_design([0.0, -0.5], [0.5])


class TestClosedLoopSimulation(unittest.TestCase):
    """Steps 4 and 5 of the SKILL.md workflow: the controller recursion and the closed-loop simulation."""

    def test_simulate_dict_keys(self):
        res = dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=dc.FIRST_ORDER_TS)
        self.assertEqual(set(res.keys()), {"y", "e", "u", "k"})
        self.assertEqual(res["k"], list(range(dc.N_STEPS)))

    def test_simulate_scenario_a_step_response(self):
        res = dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=dc.FIRST_ORDER_TS)
        for k in range(1, dc.N_STEPS):
            self.assertAlmostEqual(res["y"][k], 1.0, delta=1e-9)
        self.assertAlmostEqual(res["e"][0], 1.0, delta=1e-9)
        for k in range(1, dc.N_STEPS):
            self.assertLessEqual(abs(res["e"][k]), 1e-9)
        self.assertAlmostEqual(res["u"][0], 2.0, delta=1e-9)
        for k in range(1, dc.N_STEPS):
            self.assertAlmostEqual(res["u"][k], 1.0, delta=1e-9)

    def test_simulate_scenario_b_step_response_and_error_area(self):
        res = dc.simulate(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B, ts=dc.SECOND_ORDER_TS)
        for k in range(2, dc.N_STEPS):
            self.assertAlmostEqual(res["y"][k], 1.0, delta=1e-9)
        self.assertAlmostEqual(res["e"][0], 1.0, delta=1e-9)
        self.assertAlmostEqual(res["e"][1], 1.0, delta=1e-9)
        for k in range(2, dc.N_STEPS):
            self.assertLessEqual(abs(res["e"][k]), 1e-9)
        self.assertAlmostEqual(res["u"][0], 5.0, delta=1e-9)
        self.assertAlmostEqual(res["u"][1], -0.5, delta=1e-9)
        for k in range(2, dc.N_STEPS):
            self.assertAlmostEqual(res["u"][k], 0.7, delta=1e-9)
        self.assertTrue(math.isclose(sum(res["e"]), 2.0, rel_tol=1e-6))

    def test_simulate_scenario_c_step_response_and_control_convergence(self):
        design = dc.deadbeat_design(dc.ZERO_A, dc.ZERO_B)
        res = dc.simulate(dc.ZERO_A, dc.ZERO_B, ts=dc.ZERO_TS)
        for k in range(1, dc.N_STEPS):
            self.assertAlmostEqual(res["y"][k], 1.0, delta=1e-9)
        self.assertAlmostEqual(res["u"][0], 10.0, delta=1e-9)
        self.assertAlmostEqual(res["u"][1], -6.0, delta=1e-9)
        self.assertTrue(math.isclose(sum(res["e"]), 1.0, rel_tol=1e-6))
        self.assertTrue(math.isclose(res["u"][39], 14.0 / 15.0, rel_tol=1e-6))
        self.assertAlmostEqual(res["u"][39], design["u_star"], delta=1e-6)

    def test_simulate_rejects_bad_arguments_and_inadmissible_plant(self):
        with self.assertRaises(ValueError):
            dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=0.0)
        with self.assertRaises(ValueError):
            dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=-0.01)
        with self.assertRaises(ValueError):
            dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, reference="ramp")
        with self.assertRaises(ValueError):
            dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, steps=1)
        with self.assertRaises(ValueError):
            dc.simulate(dc.UNSTABLE_A, [0.5])

    def test_simulate_determinism(self):
        res1 = dc.simulate(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B, ts=dc.SECOND_ORDER_TS)
        res2 = dc.simulate(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B, ts=dc.SECOND_ORDER_TS)
        self.assertEqual(res1["y"], res2["y"])
        self.assertEqual(res1["e"], res2["e"])
        self.assertEqual(res1["u"], res2["u"])


class TestSettlingAndSteadyState(unittest.TestCase):
    """Steps 6 and 7 of the SKILL.md workflow: settling report and steady-state tracking."""

    def test_settling_report_scenario_a(self):
        res = dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=dc.FIRST_ORDER_TS)
        report = dc.settling_report(res, 1, dc.FIRST_ORDER_TS)
        self.assertEqual(set(report.keys()), {
            "settling_sample", "settling_time_s", "y_at_settling",
            "max_dev_after_settling", "settled",
        })
        self.assertEqual(report["settling_sample"], 1)
        self.assertAlmostEqual(report["settling_time_s"], 0.1, delta=1e-12)
        self.assertAlmostEqual(report["y_at_settling"], 1.0, delta=1e-9)
        self.assertAlmostEqual(report["max_dev_after_settling"], 0.0, delta=1e-9)
        self.assertTrue(report["settled"])

    def test_settling_report_scenarios_b_and_c(self):
        res_b = dc.simulate(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B, ts=dc.SECOND_ORDER_TS)
        report_b = dc.settling_report(res_b, 2, dc.SECOND_ORDER_TS)
        self.assertEqual(report_b["settling_sample"], 2)
        self.assertAlmostEqual(report_b["settling_time_s"], 0.04, delta=1e-12)
        self.assertLess(report_b["max_dev_after_settling"], dc.SETTLE_TOL * 1e6)
        self.assertTrue(report_b["settled"])

        res_c = dc.simulate(dc.ZERO_A, dc.ZERO_B, ts=dc.ZERO_TS)
        report_c = dc.settling_report(res_c, 1, dc.ZERO_TS)
        self.assertEqual(report_c["settling_sample"], 1)
        self.assertAlmostEqual(report_c["settling_time_s"], 0.02, delta=1e-12)
        self.assertTrue(report_c["settled"])

    def test_settling_report_rejects_short_history_and_bad_ts(self):
        res = dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=dc.FIRST_ORDER_TS, steps=2)
        with self.assertRaises(ValueError):
            dc.settling_report(res, 5, dc.FIRST_ORDER_TS)
        with self.assertRaises(ValueError):
            dc.settling_report(res, 1, 0.0)

    def test_steady_control_identity(self):
        for A, B in ((dc.FIRST_ORDER_A, dc.FIRST_ORDER_B),
                     (dc.SECOND_ORDER_A, dc.SECOND_ORDER_B),
                     (dc.ZERO_A, dc.ZERO_B)):
            design = dc.deadbeat_design(A, B)
            u_star = dc.steady_control(A, B)
            self.assertAlmostEqual(u_star, design["u_star"], delta=1e-9)
            residual = u_star * design["plant_dc_gain"] - 1.0
            self.assertAlmostEqual(residual, 0.0, delta=1e-9)

    def test_steady_control_rejects_zero_b1(self):
        with self.assertRaises(ValueError):
            dc.steady_control(dc.SECOND_ORDER_A, dc.BOUNDARY_ZERO_B)

    def test_control_effort_scenario_a(self):
        res = dc.simulate(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B, ts=dc.FIRST_ORDER_TS)
        effort = dc.control_effort(res["u"])
        self.assertEqual(set(effort.keys()), {"u0", "max_abs_u", "u_final"})
        self.assertAlmostEqual(effort["u0"], 2.0, delta=1e-9)
        self.assertAlmostEqual(effort["max_abs_u"], 2.0, delta=1e-9)
        self.assertAlmostEqual(effort["u_final"], 1.0, delta=1e-9)

    def test_control_effort_scenario_b(self):
        res = dc.simulate(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B, ts=dc.SECOND_ORDER_TS)
        effort = dc.control_effort(res["u"])
        self.assertAlmostEqual(effort["u0"], 5.0, delta=1e-9)
        self.assertAlmostEqual(effort["max_abs_u"], 5.0, delta=1e-9)
        self.assertAlmostEqual(effort["u_final"], 0.7, delta=1e-6)


class TestPureDelayIdentity(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: confirm the pure-delay impulse identity."""

    def test_closed_loop_impulse_scenario_b(self):
        res = dc.closed_loop_impulse(dc.SECOND_ORDER_A, dc.SECOND_ORDER_B)
        self.assertAlmostEqual(res["y"][2], 1.0, delta=1e-9)
        for k in range(dc.N_STEPS):
            if k != 2:
                self.assertLessEqual(abs(res["y"][k]), 1e-9)

    def test_closed_loop_impulse_scenario_a(self):
        res = dc.closed_loop_impulse(dc.FIRST_ORDER_A, dc.FIRST_ORDER_B)
        self.assertAlmostEqual(res["y"][1], 1.0, delta=1e-9)
        for k in range(dc.N_STEPS):
            if k != 1:
                self.assertLessEqual(abs(res["y"][k]), 1e-9)


if __name__ == "__main__":
    unittest.main()
