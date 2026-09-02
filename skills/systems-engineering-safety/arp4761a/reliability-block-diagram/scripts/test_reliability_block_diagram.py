#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A reliability block diagram evaluation.

Exercises scripts/reliability_block_diagram_logic.py (stdlib unittest,
offline). Contract: components fail at constant rate lambda with
R(t) = exp(-lambda t); series blocks multiply reliabilities and sum
rates; active parallel is 1 - product(1 - R_i); k-out-of-n uses the
identical-unit binomial sum; cold standby is exp(-lambda t) (1 +
lambda t) with perfect switching; mission reliability, exact MTBF and
the dominant rate are returned by evaluate_rbd; non-physical inputs
raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reliability_block_diagram_logic as rbd  # noqa: E402


def within(actual, expected, tol=0.01):
    return abs(actual - expected) <= tol * abs(expected)


class ComponentTest(unittest.TestCase):
    def test_component_reliability_is_exponential(self):
        # lambda = 1e-4 /h, t = 10 h: R = exp(-1e-3) = 0.9990005,
        # within 1% of the worked-spec value 0.99900; R(0) = 1
        self.assertAlmostEqual(rbd.component_reliability(1e-4, 10.0), 0.999000499833375)
        self.assertTrue(within(rbd.component_reliability(1e-4, 10.0), 0.99900))
        self.assertEqual(rbd.component_reliability(1e-4, 0.0), 1.0)

    def test_series_block_mtbf_is_inverse_rate(self):
        block = {"type": "series", "items": [2e-4]}
        self.assertAlmostEqual(rbd.block_mtbf(block), 5000.0)

    def test_non_physical_component_inputs_raise(self):
        for kwargs in (
            {"rate": -1e-4, "t": 10.0},
            {"rate": 0.0, "t": 10.0},
            {"rate": 1e-4, "t": -10.0},
            {"rate": "1e-4", "t": 10.0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    rbd.component_reliability(**kwargs)


class SeriesBlockTest(unittest.TestCase):
    def test_series_reliability_is_exponential_with_summed_rate(self):
        # two items at lambda = 1e-4 and 5e-5, t = 10 h
        expected = math.exp(-1e-3) * math.exp(-5e-4)
        self.assertAlmostEqual(rbd.series_reliability([1e-4, 5e-5], 10.0), expected)
        self.assertAlmostEqual(rbd.series_reliability([1e-4, 5e-5], 10.0), math.exp(-1.5e-3))

    def test_series_block_mtbf_and_rate_exact(self):
        block = {"type": "series", "items": [1e-4, 5e-5]}
        self.assertAlmostEqual(rbd.block_mtbf(block), 1.0 / 1.5e-4)
        self.assertAlmostEqual(rbd.block_equivalent_rate(block, 10.0), 1.5e-4)

    def test_single_item_series_matches_component(self):
        block = {"type": "series", "items": [1e-4]}
        self.assertAlmostEqual(
            rbd.block_reliability(block, 10.0),
            rbd.component_reliability(1e-4, 10.0),
        )


class ParallelBlockTest(unittest.TestCase):
    def test_parallel_identical_pair_matches_workspec(self):
        r_each = math.exp(-1e-3)
        expected = 1 - (1 - r_each) ** 2
        self.assertAlmostEqual(rbd.parallel_reliability([1e-4, 1e-4], 10.0), expected)
        self.assertTrue(within(rbd.parallel_reliability([1e-4, 1e-4], 10.0), 0.999999))

    def test_parallel_heterogeneous_items(self):
        r1, r2 = math.exp(-1e-3), math.exp(-2e-4 * 10.0)
        expected = 1 - (1 - r1) * (1 - r2)
        self.assertAlmostEqual(rbd.parallel_reliability([1e-4, 2e-4], 10.0), expected)

    def test_parallel_mtbf_closed_forms(self):
        # n identical exponential units in parallel: MTBF = (1/lambda) H_n
        cases = (
            ([1e-4, 1e-4], 3.0 / (2.0 * 1e-4)),
            ([1e-4, 1e-4, 1e-4], (11.0 / 6.0) / 1e-4),
        )
        for items, expected in cases:
            with self.subTest(n=len(items)):
                self.assertAlmostEqual(rbd.block_mtbf({"type": "parallel", "items": items}), expected)

    def test_parallel_beats_single_and_single_item_is_component(self):
        self.assertGreater(
            rbd.parallel_reliability([1e-4, 1e-4], 100.0),
            rbd.component_reliability(1e-4, 100.0),
        )
        block = {"type": "parallel", "items": [1e-4]}
        self.assertAlmostEqual(
            rbd.block_reliability(block, 10.0),
            rbd.component_reliability(1e-4, 10.0),
        )

    def test_parallel_structure_errors_raise(self):
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd([{"type": "parallel", "items": []}], 10.0)
        items = [1e-4 + i * 1e-6 for i in range(17)]
        with self.assertRaises(ValueError):
            rbd.block_mtbf({"type": "parallel", "items": items})


class KofnBlockTest(unittest.TestCase):
    def test_two_of_three_matches_binomial_and_expansion(self):
        # lambda = 1e-4/h, t = 100 h: 3e^-0.02 - 2e^-0.03
        r_u = math.exp(-1e-4 * 100.0)
        expected = 3 * r_u ** 2 * (1 - r_u) + r_u ** 3
        self.assertAlmostEqual(rbd.kofn_reliability(1e-4, 3, 2, 100.0), expected)
        self.assertAlmostEqual(
            rbd.kofn_reliability(1e-4, 3, 2, 100.0), 3 * math.exp(-0.02) - 2 * math.exp(-0.03)
        )

    def test_two_of_three_block_reliability_and_mtbf(self):
        block = {"type": "kofn", "items": [1e-4, 1e-4, 1e-4], "k": 2}
        self.assertAlmostEqual(rbd.block_reliability(block, 100.0), 0.9997049528232493)
        self.assertAlmostEqual(rbd.block_mtbf(block), 8333.333333333334)

    def test_k_of_n_edges_parallel_and_series(self):
        # k = 1 is active parallel; k = n is series
        self.assertAlmostEqual(
            rbd.kofn_reliability(1e-4, 3, 1, 100.0),
            rbd.parallel_reliability([1e-4, 1e-4, 1e-4], 100.0),
        )
        self.assertAlmostEqual(
            rbd.kofn_reliability(1e-4, 3, 3, 100.0),
            math.exp(-1e-4 * 100.0) ** 3,
        )

    def test_k_of_n_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            rbd.kofn_reliability(1e-4, 2, 3, 100.0)  # k > n
        with self.assertRaises(ValueError):
            rbd.kofn_reliability(1e-4, 3, 0, 100.0)
        with self.assertRaises(ValueError):
            rbd.kofn_reliability(1e-4, 3, 2.5, 100.0)
        block = {"type": "kofn", "items": [1e-4, 2e-4, 1e-4], "k": 2}
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd([block], 100.0)


class StandbyBlockTest(unittest.TestCase):
    def test_standby_perfect_switching_reliability_and_mtbf(self):
        lam, t = 1e-4, 100.0
        expected = math.exp(-lam * t) * (1 + lam * t)
        self.assertAlmostEqual(rbd.standby_reliability(lam, 0.0, t), expected)
        block = {"type": "standby", "items": [lam, lam]}
        self.assertAlmostEqual(rbd.block_mtbf(block), 2.0 / lam)
        self.assertAlmostEqual(rbd.block_reliability(block, t), expected)

    def test_standby_imperfect_switch_matches_simplified_form(self):
        # switch rate folded into standby gain: R = exp(-lambda t) (1 +
        # (lambda + switch_rate) t), valid while switch hazard is small
        lam, sw, t = 1e-4, 1e-7, 10.0
        expected = math.exp(-lam * t) * (1 + (lam + sw) * t)
        self.assertAlmostEqual(rbd.standby_reliability(lam, sw, t), expected)

    def test_standby_beats_single_component(self):
        lam, t = 1e-4, 100.0
        standby = rbd.standby_reliability(lam, 0.0, t)
        single = rbd.component_reliability(lam, t)
        self.assertGreater(standby, single)

    def test_standby_structure_errors_raise(self):
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd([{"type": "standby", "items": [1e-4]}], 100.0)
        with self.assertRaises(ValueError):
            rbd.standby_reliability(1e-4, -1e-5, 100.0)
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd([{"type": "standby", "items": [1e-4, 2e-4]}], 100.0)


class EvaluateRbdTest(unittest.TestCase):
    def setUp(self):
        # dual hydraulic actuators in active parallel, controller in series
        self.structure = [
            {"type": "parallel", "items": [1e-4, 1e-4], "name": "actuators"},
            {"type": "series", "items": [5e-5], "name": "controller"},
        ]

    def test_workspec_system_and_block_reliabilities(self):
        res = rbd.evaluate_rbd(self.structure, 10.0)
        expected = (1 - (1 - math.exp(-1e-3)) ** 2) * math.exp(-5e-4)
        self.assertAlmostEqual(res["system_reliability"], expected)
        self.assertTrue(within(res["system_reliability"], 0.9994995))
        self.assertAlmostEqual(res["block_reliabilities"][0], 1 - (1 - math.exp(-1e-3)) ** 2)
        self.assertAlmostEqual(res["block_reliabilities"][1], math.exp(-5e-4))

    def test_workspec_mtbf(self):
        # integral of (2e^-lam t - e^-2 lam t) * e^-lam_c t over t
        res = rbd.evaluate_rbd(self.structure, 10.0)
        self.assertAlmostEqual(res["mtbf"], 2.0 / 1.5e-4 - 1.0 / 2.5e-4)  # 9333.33 h

    def test_dominant_component_is_series_controller(self):
        # the single series item dominates at t = 10 h even at lower rate
        res = rbd.evaluate_rbd(self.structure, 10.0)
        self.assertEqual(res["dominant_component"]["block_index"], 1)
        self.assertIn("controller", res["dominant_component"]["label"])

    def test_system_equivalent_rate_approximation(self):
        expected = -math.log((1 - (1 - math.exp(-1e-3)) ** 2) * math.exp(-5e-4)) / 10.0
        self.assertAlmostEqual(rbd.system_equivalent_rate(self.structure, 10.0), expected)

    def test_series_only_structure_mtbf_is_inverse_sum(self):
        structure = [
            {"type": "series", "items": [1e-4]},
            {"type": "series", "items": [5e-5]},
        ]
        self.assertAlmostEqual(rbd.evaluate_rbd(structure, 10.0)["mtbf"], 1.0 / 1.5e-4)

    def test_kofn_block_inside_structure(self):
        structure = [{"type": "kofn", "items": [1e-4, 1e-4, 1e-4], "k": 2}]
        res = rbd.evaluate_rbd(structure, 100.0)
        self.assertAlmostEqual(res["system_reliability"], 0.9997049528232493)
        self.assertAlmostEqual(res["mtbf"], 8333.333333333334)

    def test_structure_errors_raise(self):
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd([], 10.0)
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd({"type": "series", "items": [1e-4]}, 10.0)
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd([{"type": "bridge", "items": [1e-4]}], 10.0)

    def test_time_bounds_in_evaluate(self):
        with self.assertRaises(ValueError):
            rbd.evaluate_rbd(self.structure, -10.0)
        self.assertEqual(rbd.evaluate_rbd(self.structure, 0.0)["system_reliability"], 1.0)


class SensitivityTest(unittest.TestCase):
    def test_one_at_a_time_elasticity_matches_manual_ratio(self):
        structure = [
            {"type": "parallel", "items": [1e-4, 1e-4], "name": "actuators"},
            {"type": "series", "items": [5e-5], "name": "controller"},
        ]
        base = rbd.system_reliability(structure, 10.0)
        bump = [
            {"type": "parallel", "items": [1e-4, 1e-4], "name": "actuators"},
            {"type": "series", "items": [5e-5 * 1.01], "name": "controller"},
        ]
        expected = (base - rbd.system_reliability(bump, 10.0)) / (base * 0.01)
        rows = rbd.sensitivity_report(structure, 10.0)
        self.assertAlmostEqual(rows[0]["elasticity"], expected)
        elasticities = [r["elasticity"] for r in rows]
        self.assertEqual(elasticities, sorted(elasticities, reverse=True))

    def test_series_item_more_sensitive_than_redundant_item_at_short_time(self):
        structure = [
            {"type": "parallel", "items": [1e-4, 1e-4], "name": "actuators"},
            {"type": "series", "items": [5e-5], "name": "controller"},
        ]
        rows = rbd.sensitivity_report(structure, 10.0)
        self.assertEqual(rows[0]["block_index"], 1)

    def test_redundancy_sensitivity_grows_with_time(self):
        block = [{"type": "parallel", "items": [1e-4, 1e-4]}]
        early = rbd.sensitivity_report(block, 1.0)[0]["elasticity"]
        late = rbd.sensitivity_report(block, 1000.0)[0]["elasticity"]
        self.assertGreater(late, early)

    def test_reliability_monotone_decreasing_in_rate(self):
        lo = rbd.system_reliability([{"type": "series", "items": [1e-4]}], 100.0)
        hi = rbd.system_reliability([{"type": "series", "items": [2e-4]}], 100.0)
        self.assertGreater(lo, hi)


class RoundTripTest(unittest.TestCase):
    def test_structure_matches_hand_closed_forms(self):
        lam, t = 1e-4, 10.0
        res = rbd.evaluate_rbd([{"type": "parallel", "items": [lam, lam]}], t)
        self.assertAlmostEqual(res["system_reliability"], 2 * math.exp(-lam * t) - math.exp(-2 * lam * t))
        self.assertAlmostEqual(
            rbd.parallel_reliability([lam, lam, lam], t),
            rbd.kofn_reliability(lam, 3, 1, t),
        )
        structure = [{"type": "series", "items": [lam]}, {"type": "series", "items": [lam]}]
        self.assertAlmostEqual(rbd.system_reliability(structure, t), math.exp(-lam * t) ** 2)

    def test_cold_standby_beats_active_parallel_at_long_mission(self):
        # the dormant spare is not worn out, so standby wins on long missions
        lam, t = 1e-4, 5000.0
        standby = rbd.standby_reliability(lam, 0.0, t)
        parallel = rbd.parallel_reliability([lam, lam], t)
        self.assertGreater(standby, parallel)


if __name__ == "__main__":
    unittest.main(verbosity=1)
