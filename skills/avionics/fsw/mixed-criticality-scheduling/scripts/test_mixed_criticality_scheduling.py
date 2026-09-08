"""Contract test for avionics/fsw/mixed-criticality-scheduling.

Exercises the SKILL.md workflow steps: step 1 (build the task list in
deadline-monotonic priority order), step 2 (the lo-criticality-mode
fixed-point response-time iteration over the C_LO estimates), step 3
(the hi-criticality-mode AMC-rtb fixed point for the HI tasks after the
criticality-mode change), step 4 (HI-mode analysis guarantees HI tasks
only), step 5 (the AMC-rtb interference sum, higher-priority LO tasks
charged at C_LO and higher-priority HI tasks charged at C_HI), step 6
(the whole-set feasible verdict), step 7 (utilization context U_LO and
U_HI) and step 8 (ValueError rejection of non-physical inputs).

Stdlib unittest, offline, deterministic. No exact-float equality on any
computed sum; every numeric assert uses assertAlmostEqual or
math.isclose.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mixed_criticality_scheduling_logic as mcs

SET_A = [
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 3.0,
     "T": 10.0, "D": 10.0},
    {"name": "guidance", "criticality": "LO", "C_LO": 3.0, "C_HI": 3.0,
     "T": 20.0, "D": 20.0},
    {"name": "health-monitor", "criticality": "HI", "C_LO": 4.0, "C_HI": 10.0,
     "T": 50.0, "D": 50.0},
]

SET_A_COLLAPSE = [
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 1.0,
     "T": 10.0, "D": 10.0},
    {"name": "guidance", "criticality": "LO", "C_LO": 3.0, "C_HI": 3.0,
     "T": 20.0, "D": 20.0},
    {"name": "health-monitor", "criticality": "HI", "C_LO": 4.0, "C_HI": 4.0,
     "T": 50.0, "D": 50.0},
]

SET_B = [
    {"name": "flight-control", "criticality": "HI", "C_LO": 1.0, "C_HI": 6.0,
     "T": 10.0, "D": 10.0},
    {"name": "guidance", "criticality": "LO", "C_LO": 3.0, "C_HI": 3.0,
     "T": 20.0, "D": 20.0},
    {"name": "health-monitor", "criticality": "HI", "C_LO": 4.0, "C_HI": 30.0,
     "T": 50.0, "D": 50.0},
]

ALL_LO_SET_1 = [
    {"name": "t0", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 3.0, "D": 3.0},
    {"name": "t1", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 4.0, "D": 4.0},
    {"name": "t2", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 8.0, "D": 8.0},
]

ALL_LO_SET_2 = [
    {"name": "t0", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 5.0, "D": 5.0},
    {"name": "t1", "criticality": "LO", "C_LO": 1.0, "C_HI": 1.0, "T": 6.0, "D": 6.0},
    {"name": "t2", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 10.0, "D": 10.0},
]

LO_OVERLOAD_SET = [
    {"name": "t0", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 3.0, "D": 3.0},
    {"name": "t1", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 5.0, "D": 5.0},
    {"name": "t2", "criticality": "LO", "C_LO": 2.0, "C_HI": 2.0, "T": 7.0, "D": 7.0},
]

SINGLE_HI = [
    {"name": "solo-hi", "criticality": "HI", "C_LO": 1.5, "C_HI": 4.0,
     "T": 10.0, "D": 10.0},
]

SINGLE_LO = [
    {"name": "solo-lo", "criticality": "LO", "C_LO": 2.5, "C_HI": 2.5,
     "T": 8.0, "D": 8.0},
]


def _valid_task(**overrides):
    task = {"name": "x", "criticality": "HI", "C_LO": 1.0, "C_HI": 2.0,
            "T": 10.0, "D": 10.0}
    task.update(overrides)
    return task


class LoResponseTimesTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the LO-mode fixed-point RTA."""

    def test_set_a_lo_response_times(self):
        result = mcs.lo_response_times(SET_A)
        self.assertEqual(result["names"],
                          ["flight-control", "guidance", "health-monitor"])
        for got, want in zip(result["response_times"], [1.0, 4.0, 8.0]):
            self.assertAlmostEqual(got, want, delta=1e-6)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["utilization"], 0.33, delta=1e-6)

    def test_set_a_deadlines_respected(self):
        result = mcs.lo_response_times(SET_A)
        deadlines = [10.0, 20.0, 50.0]
        for r, d in zip(result["response_times"], deadlines):
            self.assertLessEqual(r, d + 1e-9)

    def test_all_lo_set_1_reproduces_sibling(self):
        result = mcs.lo_response_times(ALL_LO_SET_1)
        for got, want in zip(result["response_times"], [1.0, 2.0, 6.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertTrue(result["feasible"])

    def test_all_lo_set_2_reproduces_sibling(self):
        result = mcs.lo_response_times(ALL_LO_SET_2)
        for got, want in zip(result["response_times"], [1.0, 2.0, 4.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertTrue(result["feasible"])

    def test_lo_overload_diverges(self):
        result = mcs.lo_response_times(LO_OVERLOAD_SET)
        self.assertAlmostEqual(result["response_times"][0], 2.0, delta=1e-9)
        self.assertIsNone(result["response_times"][1])
        self.assertIsNone(result["response_times"][2])
        self.assertFalse(result["feasible"])

    def test_single_hi_task_lo_response(self):
        result = mcs.lo_response_times(SINGLE_HI)
        self.assertAlmostEqual(result["response_times"][0], 1.5, delta=1e-9)
        self.assertTrue(result["feasible"])

    def test_single_lo_task_lo_response(self):
        result = mcs.lo_response_times(SINGLE_LO)
        self.assertAlmostEqual(result["response_times"][0], 2.5, delta=1e-9)
        self.assertTrue(result["feasible"])


class HiResponseTimesTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the AMC-rtb HI-mode fixed point."""

    def test_set_a_hi_response_times(self):
        result = mcs.hi_response_times(SET_A)
        self.assertEqual(result["names"], ["flight-control", "health-monitor"])
        self.assertNotIn("guidance", result["names"])
        for got, want in zip(result["response_times"], [3.0, 19.0]):
            self.assertAlmostEqual(got, want, delta=1e-6)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["utilization"], 0.5, delta=1e-6)

    def test_amc_rtb_arm_structure_health_monitor(self):
        """Step 5 of the SKILL.md workflow: both interference arms."""
        r = mcs.hi_response_time(SET_A, 2)
        self.assertAlmostEqual(r, 19.0, delta=1e-9)
        # Plug-back identity: R = C_HI + ceil(R/T_flight)*C_HI_flight
        #                        + ceil(R/T_guidance)*C_LO_guidance.
        plug_back = 10.0 + math.ceil(r / 10.0) * 3.0 + math.ceil(r / 20.0) * 3.0
        self.assertAlmostEqual(plug_back, r, delta=1e-9)
        self.assertEqual(math.ceil(r / 10.0), 2)
        self.assertEqual(math.ceil(r / 20.0), 1)

    def test_all_lo_set_has_empty_hi_guarantee(self):
        result = mcs.hi_response_times(ALL_LO_SET_1)
        self.assertEqual(result["names"], [])
        self.assertEqual(result["response_times"], [])
        self.assertTrue(result["feasible"])

    def test_single_hi_task_hi_response(self):
        result = mcs.hi_response_times(SINGLE_HI)
        self.assertAlmostEqual(result["response_times"][0], 4.0, delta=1e-9)
        self.assertTrue(result["feasible"])

    def test_hi_mode_guarantees_hi_tasks_only(self):
        """Step 4 of the SKILL.md workflow: HI-mode rejects a LO index."""
        with self.assertRaises(ValueError) as ctx:
            mcs.hi_response_time(SET_A, 1)
        self.assertIn("LO-criticality", str(ctx.exception))
        self.assertIn("HI-mode analysis guarantees HI tasks only",
                       str(ctx.exception))

    def test_set_b_hi_overload_diverges(self):
        result = mcs.hi_response_times(SET_B)
        self.assertAlmostEqual(result["response_times"][0], 6.0, delta=1e-9)
        self.assertIsNone(result["response_times"][1])
        self.assertFalse(result["feasible"])
        self.assertAlmostEqual(result["utilization"], 1.2, delta=1e-6)

    def test_set_b_first_pass_divergence_value(self):
        # health-monitor's first AMC-rtb pass: 30 + ceil(30/10)*6 + ceil(30/20)*3 = 54.
        r = 30.0 + math.ceil(30.0 / 10.0) * 6.0 + math.ceil(30.0 / 20.0) * 3.0
        self.assertAlmostEqual(r, 54.0, delta=1e-9)
        self.assertGreater(r, 50.0)


class NoOverrunCollapseTest(unittest.TestCase):
    """Mode-monotonicity and the no-overrun identity checks."""

    def test_collapse_hi_equals_lo(self):
        lo = mcs.lo_response_times(SET_A_COLLAPSE)
        hi = mcs.hi_response_times(SET_A_COLLAPSE)
        for got, want in zip(lo["response_times"], [1.0, 4.0, 8.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        for got, want in zip(hi["response_times"], [1.0, 8.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)

    def test_mode_monotonicity_set_a(self):
        lo = mcs.lo_response_times(SET_A)
        hi = mcs.hi_response_times(SET_A)
        # flight-control (index 0) and health-monitor (index 2).
        self.assertGreaterEqual(hi["response_times"][0] + 1e-9,
                                 lo["response_times"][0])
        self.assertGreaterEqual(hi["response_times"][1] + 1e-9,
                                 lo["response_times"][2])


class FeasibleWholeSetTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the whole-set verdict."""

    def test_set_a_feasible(self):
        self.assertTrue(mcs.feasible(SET_A))

    def test_set_b_infeasible(self):
        self.assertFalse(mcs.feasible(SET_B))

    def test_lo_overload_infeasible(self):
        self.assertFalse(mcs.feasible(LO_OVERLOAD_SET))

    def test_single_hi_feasible(self):
        self.assertTrue(mcs.feasible(SINGLE_HI))

    def test_single_lo_feasible(self):
        self.assertTrue(mcs.feasible(SINGLE_LO))


class ValueErrorTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: rejection of non-physical inputs."""

    def test_empty_list(self):
        with self.assertRaises(ValueError):
            mcs.lo_response_times([])

    def test_missing_key(self):
        bad = {"name": "x", "criticality": "HI", "C_LO": 1.0, "C_HI": 2.0,
               "T": 10.0}
        with self.assertRaises(ValueError) as ctx:
            mcs.lo_response_times([bad])
        self.assertIn("missing key(s)", str(ctx.exception))

    def test_non_dict_entry(self):
        with self.assertRaises(ValueError):
            mcs.lo_response_times([(1.0, 2.0)])

    def test_boolean_or_non_positive_fields_rejected(self):
        bad_overrides = [
            {"C_LO": True}, {"C_LO": 0.0}, {"C_HI": 0.0},
            {"T": 0.0}, {"T": -5.0}, {"D": -1.0},
        ]
        for overrides in bad_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    mcs.lo_response_times([_valid_task(**overrides)])

    def test_c_hi_below_c_lo(self):
        with self.assertRaises(ValueError) as ctx:
            mcs.lo_response_times([_valid_task(C_LO=1.0, C_HI=0.5)])
        self.assertIn("C_HI must be at least C_LO", str(ctx.exception))

    def test_lo_task_c_hi_above_c_lo(self):
        with self.assertRaises(ValueError) as ctx:
            mcs.lo_response_times(
                [_valid_task(criticality="LO", C_LO=3.0, C_HI=5.0)]
            )
        self.assertIn("carries no high estimate", str(ctx.exception))

    def test_deadline_above_period(self):
        with self.assertRaises(ValueError) as ctx:
            mcs.lo_response_times([_valid_task(T=10.0, D=15.0)])
        self.assertIn("D must be no greater than T", str(ctx.exception))

    def test_unknown_criticality(self):
        with self.assertRaises(ValueError) as ctx:
            mcs.lo_response_times([_valid_task(criticality="MED")])
        self.assertIn("criticality must be 'LO' or 'HI'", str(ctx.exception))

    def test_non_deadline_monotonic_order(self):
        with self.assertRaises(ValueError) as ctx:
            mcs.lo_response_times([
                _valid_task(name="a", T=10.0, D=10.0),
                _valid_task(name="b", T=5.0, D=5.0),
            ])
        self.assertIn("deadline-monotonic priority order", str(ctx.exception))

    def test_index_out_of_range(self):
        with self.assertRaises(ValueError):
            mcs.lo_response_time(SET_A, 5)
        with self.assertRaises(ValueError):
            mcs.hi_response_time(SET_A, -1)

    def test_hi_mode_call_on_lo_index(self):
        with self.assertRaises(ValueError):
            mcs.hi_response_time(SET_A, 1)


class DeterminismAndConvergenceTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow and determinism across runs."""

    def test_response_times_deterministic(self):
        self.assertEqual(mcs.lo_response_times(SET_A), mcs.lo_response_times(SET_A))
        self.assertEqual(mcs.hi_response_times(SET_A), mcs.hi_response_times(SET_A))

    def test_module_constants(self):
        self.assertEqual(mcs.MAX_RTA_ITERATIONS, 100)
        self.assertAlmostEqual(mcs.CONVERGENCE_TOL, 1e-12, delta=1e-20)

    def test_utilization_context(self):
        lo = mcs.lo_response_times(SET_A)
        hi = mcs.hi_response_times(SET_A)
        expected_lo = sum(t["C_LO"] / t["T"] for t in SET_A)
        expected_hi = sum(t["C_HI"] / t["T"] for t in SET_A
                           if t["criticality"] == "HI")
        self.assertTrue(math.isclose(lo["utilization"], expected_lo, rel_tol=1e-9))
        self.assertTrue(math.isclose(hi["utilization"], expected_hi, rel_tol=1e-9))


if __name__ == "__main__":
    unittest.main()
