"""Contract test for avionics/fsw/virtual-deadline-scheduling.

Exercises the SKILL.md workflow steps: step 1 (build the priority-free
task list), step 2 (the per-mode demand sums via utilizations), step 3
(the virtual-deadline factor x), step 4 (the per-HI-task virtual
deadlines x*T), step 5 (the lo-criticality-mode demand condition),
step 6 (the hi-criticality-mode demand condition after the criticality
mode change), step 7 (the whole edf_vd_report) and step 8 (the
feasible convenience verdict and ValueError rejection of non-physical
inputs).

Stdlib unittest, offline, deterministic. No exact-float equality on any
computed sum; every numeric assert uses assertAlmostEqual or
math.isclose.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import virtual_deadline_scheduling_logic as vds

SET_A = [
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 2.0, "T": 5.0},
    {"name": "health-monitor", "criticality": "HI", "C_LO": 2.0, "C_HI": 4.0, "T": 10.0},
    {"name": "guidance", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 10.0},
]

SET_A_COLLAPSE = [
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 1.0, "T": 5.0},
    {"name": "health-monitor", "criticality": "HI", "C_LO": 2.0, "C_HI": 2.0, "T": 10.0},
    {"name": "guidance", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 10.0},
]

SET_B = [
    {"name": "guidance", "criticality": "LO", "C_LO": 3.0, "C_HI": 3.0, "T": 10.0},
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 3.0, "T": 10.0},
    {"name": "health-monitor", "criticality": "HI", "C_LO": 2.0, "C_HI": 6.0, "T": 10.0},
]

SET_C = [
    {"name": "guidance", "criticality": "LO", "C_LO": 8.0, "C_HI": 8.0, "T": 10.0},
    {"name": "trim", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 5.0},
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 2.0, "T": 10.0},
]

ALL_LO_SET_1 = [
    {"name": "t0", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 3.0},
    {"name": "t1", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 4.0},
    {"name": "t2", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 8.0},
]

ALL_LO_SET_2 = [
    {"name": "t0", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 3.0},
    {"name": "t1", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 5.0},
    {"name": "t2", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 7.0},
]

HI_ONLY_SET = [
    {"name": "h0", "criticality": "HI", "C_LO": 1.0, "C_HI": 2.0, "T": 5.0},
    {"name": "h1", "criticality": "HI", "C_LO": 2.0, "C_HI": 4.0, "T": 10.0},
]

HI_ONLY_OVERLOAD = [
    {"name": "h0", "criticality": "HI", "C_LO": 1.0, "C_HI": 6.0, "T": 5.0},
    {"name": "h1", "criticality": "HI", "C_LO": 2.0, "C_HI": 4.0, "T": 10.0},
]

SINGLE_HI = [
    {"name": "solo-hi", "criticality": "HI", "C_LO": 1.5, "C_HI": 4.0, "T": 10.0},
]

SINGLE_LO = [
    {"name": "solo-lo", "criticality": "LO", "C_LO": 2.5, "C_HI": 2.5, "T": 8.0},
]


def _valid_task(**overrides):
    task = {"name": "x", "criticality": "HI", "C_LO": 1.0, "C_HI": 2.0, "T": 10.0}
    task.update(overrides)
    return task


class UtilizationsTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the per-mode demand sums."""

    def test_set_a_demand_sums(self):
        u = vds.utilizations(SET_A)
        self.assertAlmostEqual(u["u_lo_lo"], 0.2, delta=1e-9)
        self.assertAlmostEqual(u["u_hi_lo"], 0.4, delta=1e-9)
        self.assertAlmostEqual(u["u_hi_hi"], 0.8, delta=1e-9)
        self.assertAlmostEqual(u["u_lo"], 0.6, delta=1e-6)
        self.assertAlmostEqual(u["u_hi"], 0.8, delta=1e-9)

    def test_set_b_demand_sums(self):
        u = vds.utilizations(SET_B)
        self.assertAlmostEqual(u["u_lo_lo"], 0.3, delta=1e-9)
        self.assertAlmostEqual(u["u_hi_lo"], 0.3, delta=1e-6)
        self.assertAlmostEqual(u["u_hi_hi"], 0.9, delta=1e-6)

    def test_set_c_demand_sums(self):
        u = vds.utilizations(SET_C)
        self.assertAlmostEqual(u["u_lo_lo"], 1.0, delta=1e-9)
        self.assertAlmostEqual(u["u_hi_lo"], 0.1, delta=1e-9)
        self.assertAlmostEqual(u["u_hi_hi"], 0.2, delta=1e-9)

    def test_all_lo_identity(self):
        u = vds.utilizations(ALL_LO_SET_1)
        self.assertAlmostEqual(u["u_lo"], 0.8333333333333333, delta=1e-9)
        self.assertAlmostEqual(u["u_hi_lo"], 0.0, delta=1e-12)

    def test_hi_only_identity(self):
        u = vds.utilizations(HI_ONLY_SET)
        self.assertAlmostEqual(u["u_lo_lo"], 0.0, delta=1e-12)
        self.assertAlmostEqual(u["u_hi"], 0.8, delta=1e-9)


class VirtualDeadlineFactorTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the virtual-deadline factor x."""

    def test_set_a_factor(self):
        x = vds.virtual_deadline_factor(SET_A)
        self.assertAlmostEqual(x, 0.5, delta=1e-9)

    def test_set_b_factor(self):
        x = vds.virtual_deadline_factor(SET_B)
        self.assertAlmostEqual(x, 0.42857142857142866, delta=1e-9)

    def test_set_c_factor_is_none(self):
        self.assertIsNone(vds.virtual_deadline_factor(SET_C))

    def test_all_lo_factor_is_one(self):
        self.assertAlmostEqual(vds.virtual_deadline_factor(ALL_LO_SET_1), 1.0, delta=1e-12)

    def test_hi_only_factor(self):
        x = vds.virtual_deadline_factor(HI_ONLY_SET)
        self.assertAlmostEqual(x, 0.4, delta=1e-9)

    def test_factor_bounds_on_hi_bearing_sets(self):
        for tasks in (SET_A, SET_B, HI_ONLY_SET, SET_A_COLLAPSE):
            x = vds.virtual_deadline_factor(tasks)
            self.assertIsNotNone(x)
            self.assertGreater(x, 0.0)
            u = vds.utilizations(tasks)
            if x <= 1.0 + 1e-9:
                self.assertLessEqual(u["u_lo"], 1.0 + 1e-6)


class VirtualDeadlinesTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the per-HI-task virtual deadlines."""

    def test_set_a_virtual_deadlines(self):
        vd = vds.virtual_deadlines(SET_A)
        self.assertAlmostEqual(vd["flight-control"], 2.5, delta=1e-9)
        self.assertAlmostEqual(vd["health-monitor"], 5.0, delta=1e-9)
        self.assertNotIn("guidance", vd)

    def test_set_b_virtual_deadlines(self):
        vd = vds.virtual_deadlines(SET_B)
        for name in ("flight-control", "health-monitor"):
            self.assertAlmostEqual(vd[name], 4.2857142857142865, delta=1e-9)

    def test_set_c_virtual_deadlines_none(self):
        self.assertIsNone(vds.virtual_deadlines(SET_C))

    def test_all_lo_virtual_deadlines_empty(self):
        self.assertEqual(vds.virtual_deadlines(ALL_LO_SET_1), {})

    def test_unnamed_task_keyed_task(self):
        tasks = [{"criticality": "HI", "C_LO": 1.0, "C_HI": 2.0, "T": 5.0}]
        vd = vds.virtual_deadlines(tasks)
        self.assertIn("task", vd)


class LoModeFeasibleTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the lo-criticality-mode condition."""

    def test_set_a_lo_feasible(self):
        self.assertTrue(vds.lo_mode_feasible(SET_A))

    def test_set_b_lo_feasible(self):
        self.assertTrue(vds.lo_mode_feasible(SET_B))

    def test_set_c_lo_infeasible(self):
        self.assertFalse(vds.lo_mode_feasible(SET_C))

    def test_all_lo_overload_infeasible(self):
        self.assertFalse(vds.lo_mode_feasible(ALL_LO_SET_2))

    def test_all_lo_ok_feasible(self):
        self.assertTrue(vds.lo_mode_feasible(ALL_LO_SET_1))

    def test_lo_density_identity_set_a(self):
        """LO-mode density a + b/x prints 1 at the canonical factor."""
        u = vds.utilizations(SET_A)
        x = vds.virtual_deadline_factor(SET_A)
        density = u["u_lo_lo"] + u["u_hi_lo"] / x
        self.assertAlmostEqual(density, 1.0, delta=1e-9)


class HiModeFeasibleTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the hi-criticality-mode condition
    after the criticality mode change."""

    def test_set_a_hi_feasible(self):
        self.assertTrue(vds.hi_mode_feasible(SET_A))

    def test_set_b_hi_infeasible(self):
        self.assertFalse(vds.hi_mode_feasible(SET_B))

    def test_set_c_hi_infeasible(self):
        self.assertFalse(vds.hi_mode_feasible(SET_C))

    def test_hi_only_overload_infeasible(self):
        self.assertFalse(vds.hi_mode_feasible(HI_ONLY_OVERLOAD))

    def test_all_lo_vacuously_true(self):
        self.assertTrue(vds.hi_mode_feasible(ALL_LO_SET_1))

    def test_all_lo_overload_still_vacuously_true(self):
        # No HI task to guarantee, so hi_mode_feasible is True even when
        # the LO tasks alone saturate the processor (a > 1).
        self.assertTrue(vds.hi_mode_feasible(ALL_LO_SET_2))

    def test_set_b_hi_demand_value(self):
        u = vds.utilizations(SET_B)
        x = vds.virtual_deadline_factor(SET_B)
        demand = u["u_hi_hi"] + u["u_lo_lo"] * x
        self.assertAlmostEqual(demand, 1.0285714285714285, delta=1e-9)
        self.assertGreater(demand, 1.0)


class EdfVdReportTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the whole edf-vd report."""

    def test_set_a_report(self):
        r = vds.edf_vd_report(SET_A)
        self.assertAlmostEqual(r["u_lo_lo"], 0.2, delta=1e-9)
        self.assertAlmostEqual(r["u_hi_lo"], 0.4, delta=1e-9)
        self.assertAlmostEqual(r["u_hi_hi"], 0.8, delta=1e-9)
        self.assertAlmostEqual(r["u_lo"], 0.6, delta=1e-6)
        self.assertAlmostEqual(r["u_hi"], 0.8, delta=1e-9)
        self.assertAlmostEqual(r["x"], 0.5, delta=1e-9)
        self.assertTrue(r["lo_feasible"])
        self.assertTrue(r["hi_feasible"])
        self.assertTrue(r["feasible"])
        self.assertAlmostEqual(r["virtual_deadlines"]["flight-control"], 2.5, delta=1e-9)
        self.assertAlmostEqual(r["virtual_deadlines"]["health-monitor"], 5.0, delta=1e-9)

    def test_set_b_report(self):
        r = vds.edf_vd_report(SET_B)
        self.assertAlmostEqual(r["x"], 0.42857142857142866, delta=1e-9)
        self.assertTrue(r["lo_feasible"])
        self.assertFalse(r["hi_feasible"])
        self.assertFalse(r["feasible"])

    def test_set_c_report(self):
        r = vds.edf_vd_report(SET_C)
        self.assertIsNone(r["x"])
        self.assertFalse(r["lo_feasible"])
        self.assertFalse(r["hi_feasible"])
        self.assertFalse(r["feasible"])
        self.assertIsNone(r["virtual_deadlines"])

    def test_no_overrun_collapse(self):
        r = vds.edf_vd_report(SET_A_COLLAPSE)
        self.assertAlmostEqual(r["u_lo"], 0.6, delta=1e-6)
        self.assertAlmostEqual(r["x"], 0.5, delta=1e-9)
        hi_demand = r["u_hi_hi"] + r["u_lo_lo"] * r["x"]
        self.assertAlmostEqual(hi_demand, 0.5, delta=1e-9)
        self.assertTrue(r["feasible"])

    def test_all_lo_identity_sibling_reduction(self):
        r = vds.edf_vd_report(ALL_LO_SET_1)
        self.assertAlmostEqual(r["u_lo"], 0.8333333333333333, delta=1e-9)
        self.assertAlmostEqual(r["x"], 1.0, delta=1e-12)
        self.assertEqual(r["virtual_deadlines"], {})
        self.assertTrue(r["feasible"])

    def test_all_lo_overload_identity(self):
        r = vds.edf_vd_report(ALL_LO_SET_2)
        self.assertAlmostEqual(r["u_lo"], 1.3523809523809525, delta=1e-9)
        self.assertFalse(r["feasible"])

    def test_hi_only_reduction(self):
        r = vds.edf_vd_report(HI_ONLY_SET)
        self.assertAlmostEqual(r["u_lo_lo"], 0.0, delta=1e-12)
        self.assertAlmostEqual(r["u_hi"], 0.8, delta=1e-9)
        self.assertAlmostEqual(r["x"], 0.4, delta=1e-9)
        self.assertTrue(r["feasible"])

    def test_multiprocessor_form_equivalence_set_a(self):
        r = vds.edf_vd_report(SET_A)
        c, b, a = r["u_hi_hi"], r["u_hi_lo"], r["u_lo_lo"]
        restated = (1.0 - c) / (1.0 - c + b)
        self.assertAlmostEqual(restated, 0.33333333333333326, delta=1e-9)
        self.assertGreaterEqual(restated, a)
        self.assertTrue(r["hi_feasible"])

    def test_multiprocessor_form_equivalence_all_hi_bearing_sets(self):
        # Restricted to sets where 1 - c + b > 0, the denominator sign the
        # spec anchors the restatement direction against.
        for tasks in (SET_A, SET_B, HI_ONLY_SET, SET_A_COLLAPSE):
            r = vds.edf_vd_report(tasks)
            c, b, a = r["u_hi_hi"], r["u_hi_lo"], r["u_lo_lo"]
            restated_holds = a <= (1.0 - c) / (1.0 - c + b) + 1e-9
            self.assertEqual(restated_holds, r["hi_feasible"])

    def test_single_hi_report(self):
        # a = 0 (no LO tasks), so x = b / (1 - a) = b = C_LO / T = 0.15.
        r = vds.edf_vd_report(SINGLE_HI)
        self.assertAlmostEqual(r["x"], 0.15, delta=1e-9)
        self.assertTrue(r["feasible"])

    def test_single_lo_report(self):
        r = vds.edf_vd_report(SINGLE_LO)
        self.assertAlmostEqual(r["x"], 1.0, delta=1e-12)
        self.assertEqual(r["virtual_deadlines"], {})
        self.assertTrue(r["feasible"])


class FeasibleConvenienceTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the whole-set convenience verdict."""

    def test_set_a_feasible(self):
        self.assertTrue(vds.feasible(SET_A))

    def test_set_b_infeasible(self):
        self.assertFalse(vds.feasible(SET_B))

    def test_set_c_infeasible(self):
        self.assertFalse(vds.feasible(SET_C))

    def test_matches_report_feasible(self):
        for tasks in (SET_A, SET_B, SET_C, ALL_LO_SET_1, HI_ONLY_SET):
            self.assertEqual(vds.feasible(tasks), vds.edf_vd_report(tasks)["feasible"])


class ValueErrorTest(unittest.TestCase):
    """Step 1/8 of the SKILL.md workflow: rejection of non-physical inputs."""

    def test_empty_list(self):
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([])
        self.assertIn("non-empty list", str(ctx.exception))

    def test_missing_key(self):
        bad = {"criticality": "HI", "C_LO": 1.0, "T": 5.0}
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([bad])
        self.assertIn("missing key(s)", str(ctx.exception))
        self.assertIn("C_HI", str(ctx.exception))

    def test_non_dict_entry(self):
        with self.assertRaises(ValueError):
            vds.utilizations([(1.0, 2.0, 5.0)])

    def test_boolean_or_non_positive_fields_rejected(self):
        bad_overrides = [
            {"C_LO": True}, {"C_LO": 0.0}, {"C_HI": 0.0},
            {"T": 0.0}, {"T": -5.0}, {"C_LO": -1.0},
        ]
        for overrides in bad_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    vds.utilizations([_valid_task(**overrides)])

    def test_c_lo_zero_message(self):
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([_valid_task(C_LO=0.0)])
        self.assertIn("C_LO must be a positive number, got 0.0", str(ctx.exception))

    def test_boolean_c_lo_message(self):
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([_valid_task(C_LO=True)])
        self.assertIn("C_LO must be a positive number, got True", str(ctx.exception))

    def test_c_hi_below_c_lo(self):
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([_valid_task(C_LO=1.0, C_HI=0.5)])
        self.assertIn(
            "C_HI must be at least C_LO, got C_HI 0.5 with C_LO 1.0",
            str(ctx.exception),
        )

    def test_lo_task_c_hi_above_c_lo(self):
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([_valid_task(criticality="LO", C_LO=1.0, C_HI=5.0)])
        self.assertIn(
            "a LO-criticality task carries no high estimate: "
            "C_HI must equal C_LO, got C_HI 5.0 with C_LO 1.0",
            str(ctx.exception),
        )

    def test_unknown_criticality(self):
        with self.assertRaises(ValueError) as ctx:
            vds.utilizations([_valid_task(criticality="MED")])
        self.assertIn("criticality must be 'LO' or 'HI', got 'MED'", str(ctx.exception))

    def test_errors_raised_from_every_public_function(self):
        empty = []
        for fn in (
            vds.utilizations,
            vds.virtual_deadline_factor,
            vds.virtual_deadlines,
            vds.lo_mode_feasible,
            vds.hi_mode_feasible,
            vds.edf_vd_report,
            vds.feasible,
        ):
            with self.assertRaises(ValueError):
                fn(empty)


class DeterminismTest(unittest.TestCase):
    """Determinism across runs and module constant checks."""

    def test_report_deterministic(self):
        self.assertEqual(vds.edf_vd_report(SET_A), vds.edf_vd_report(SET_A))
        self.assertEqual(vds.edf_vd_report(SET_B), vds.edf_vd_report(SET_B))

    def test_tol_constant(self):
        self.assertAlmostEqual(vds.TOL, 1e-12, delta=1e-20)

    def test_no_randomness_module(self):
        import inspect
        src = inspect.getsource(vds)
        self.assertNotIn("random", src.lower())

    def test_isclose_cross_check(self):
        r = vds.edf_vd_report(SET_A)
        self.assertTrue(math.isclose(r["u_lo"], 0.6, rel_tol=1e-6))


if __name__ == "__main__":
    unittest.main()
