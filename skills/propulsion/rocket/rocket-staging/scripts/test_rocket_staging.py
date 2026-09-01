#!/usr/bin/env python3
"""Gate 3 contract test: rocket staging (per-stage delta-v, mass ratio
and payload fraction allocation, stage optimization).

Exercises scripts/rocket_staging_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - ideal delta-v per stage
from the rocket equation, stage mass ratio from a delta-v requirement,
payload fraction and structural index allocation, the equal-mass-ratio
optimum split for a target total delta-v, and the minimum stage count
for a payload target; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rocket_staging_logic as rsl  # noqa: E402


class StageDeltaVTest(unittest.TestCase):
    def test_anchor_delta_v(self):
        # 9.80665 * 300 * ln(2) = 2039.24 m/s
        self.assertAlmostEqual(
            rsl.stage_delta_v(300, 100000, 50000), 2039.24, delta=0.1
        )

    def test_delta_v_grows_with_isp(self):
        d1 = rsl.stage_delta_v(300, 100000, 50000)
        d2 = rsl.stage_delta_v(350, 100000, 50000)
        self.assertGreater(d2, d1)

    def test_delta_v_grows_with_mass_ratio(self):
        d1 = rsl.stage_delta_v(300, 100000, 50000)
        d2 = rsl.stage_delta_v(300, 100000, 25000)
        self.assertGreater(d2, d1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.stage_delta_v(0, 100000, 50000)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.stage_delta_v(-10, 100000, 50000)
        with self.assertRaises(ValueError):
            rsl.stage_delta_v(300, 0, 50000)  # m0 <= 0
        with self.assertRaises(ValueError):
            rsl.stage_delta_v(300, 100000, 0)  # mf <= 0
        with self.assertRaises(ValueError):
            rsl.stage_delta_v(300, 100000, 100000)  # mf >= m0
        with self.assertRaises(ValueError):
            rsl.stage_delta_v(300, 100000, 150000)


class MassRatioTest(unittest.TestCase):
    def test_anchor_mass_ratio(self):
        # exp(2039.24 / (9.80665 * 300)) = 2.0
        self.assertAlmostEqual(
            rsl.mass_ratio_from_delta_v(2039.24, 300), 2.0, delta=1e-3
        )

    def test_zero_delta_v_unit_ratio(self):
        self.assertAlmostEqual(rsl.mass_ratio_from_delta_v(0.0, 300), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_delta_v(-1.0, 300)  # delta_v < 0
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_delta_v(1000, 0)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_delta_v(1000, -300)


class PayloadFractionTest(unittest.TestCase):
    def test_anchor_payload_fraction(self):
        self.assertAlmostEqual(rsl.payload_fraction(5000, 100000), 0.05)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.payload_fraction(0, 100000)  # payload <= 0
        with self.assertRaises(ValueError):
            rsl.payload_fraction(-5, 100000)
        with self.assertRaises(ValueError):
            rsl.payload_fraction(5000, 0)  # m0 <= 0
        with self.assertRaises(ValueError):
            rsl.payload_fraction(100000, 100000)  # payload >= m0
        with self.assertRaises(ValueError):
            rsl.payload_fraction(120000, 100000)


class StructuralIndexTest(unittest.TestCase):
    def test_anchor_structural_index(self):
        self.assertAlmostEqual(rsl.structural_index(10000, 90000), 0.1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.structural_index(0, 90000)  # structure <= 0
        with self.assertRaises(ValueError):
            rsl.structural_index(10000, 0)  # propellant <= 0
        with self.assertRaises(ValueError):
            rsl.structural_index(-1, 90000)


class MassRatioFromIndicesTest(unittest.TestCase):
    def test_anchor_mass_ratio_from_indices(self):
        # 1 / (0.05 + 0.1 * 0.95) = 6.8966
        self.assertAlmostEqual(
            rsl.mass_ratio_from_indices(0.1, 0.05), 6.8966, delta=1e-3
        )

    def test_lower_structural_index_gives_higher_ratio(self):
        r1 = rsl.mass_ratio_from_indices(0.2, 0.05)
        r2 = rsl.mass_ratio_from_indices(0.1, 0.05)
        self.assertGreater(r2, r1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_indices(0.0, 0.05)  # eps <= 0
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_indices(1.0, 0.05)  # eps >= 1
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_indices(0.1, 0.0)  # lam <= 0
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_indices(0.1, 1.0)  # lam >= 1


class PayloadFractionFromMassRatioTest(unittest.TestCase):
    def test_round_trip(self):
        # inverse of the 6.8966 / 0.05 anchor
        self.assertAlmostEqual(
            rsl.payload_fraction_from_mass_ratio(0.1, 6.8966), 0.05, delta=1e-3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.payload_fraction_from_mass_ratio(0.0, 4.0)  # eps <= 0
        with self.assertRaises(ValueError):
            rsl.payload_fraction_from_mass_ratio(0.1, 1.0)  # r <= 1
        with self.assertRaises(ValueError):
            rsl.payload_fraction_from_mass_ratio(0.1, 0.5)
        # unreachable: r >= 1/eps = 1.1111 leaves no payload mass
        with self.assertRaises(ValueError):
            rsl.payload_fraction_from_mass_ratio(0.9, 1.2)


class StageDeltaVFromIndicesTest(unittest.TestCase):
    def test_anchor_delta_v_from_indices(self):
        # ln(6.8966) at Isp 300 -> 5681.06 m/s
        self.assertAlmostEqual(
            rsl.stage_delta_v_from_indices(300, 0.1, 0.05), 5681.06, delta=0.1
        )

    def test_matches_rocket_equation(self):
        # 5000 kg payload, 9500 kg structure, 85500 kg propellant on
        # m0 = 100000 kg gives mf = 14500 kg and the same mass ratio
        dv_indices = rsl.stage_delta_v_from_indices(300, 0.1, 0.05)
        dv_direct = rsl.stage_delta_v(300, 100000, 14500)
        self.assertAlmostEqual(dv_indices, dv_direct, delta=1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.stage_delta_v_from_indices(0, 0.1, 0.05)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.stage_delta_v_from_indices(300, 1.0, 0.05)  # eps >= 1
        with self.assertRaises(ValueError):
            rsl.stage_delta_v_from_indices(300, 0.1, 0.0)  # lam <= 0


class OptimalEqualStageSplitTest(unittest.TestCase):
    def test_anchor_two_stage_split(self):
        # r* = exp(9000 / (2 * 2941.995)) = 4.6162, lam_total = 0.01679
        r_star, lam_stage, lam_total = rsl.optimal_equal_stage_split(
            9000, 2, 300, 0.1
        )
        self.assertAlmostEqual(r_star, 4.6162, delta=1e-3)
        self.assertAlmostEqual(lam_stage, 0.12959, delta=1e-3)
        self.assertAlmostEqual(lam_total, 0.01679, delta=1e-3)

    def test_more_stages_more_payload(self):
        _, _, lam2 = rsl.optimal_equal_stage_split(9000, 2, 300, 0.1)
        _, _, lam3 = rsl.optimal_equal_stage_split(9000, 3, 300, 0.1)
        self.assertGreater(lam3, lam2)

    def test_higher_isp_more_payload(self):
        _, _, lam300 = rsl.optimal_equal_stage_split(9000, 2, 300, 0.1)
        _, _, lam350 = rsl.optimal_equal_stage_split(9000, 2, 350, 0.1)
        self.assertGreater(lam350, lam300)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.optimal_equal_stage_split(0, 2, 300, 0.1)  # dv <= 0
        with self.assertRaises(ValueError):
            rsl.optimal_equal_stage_split(9000, 0, 300, 0.1)  # n < 1
        with self.assertRaises(ValueError):
            rsl.optimal_equal_stage_split(9000, 2, 0, 0.1)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.optimal_equal_stage_split(9000, 2, 300, 0.0)  # eps <= 0
        with self.assertRaises(ValueError):
            rsl.optimal_equal_stage_split(9000, 2, 300, 1.0)
        # unreachable: a single stage at eps 0.1 cannot deliver 9000 m/s
        with self.assertRaises(ValueError):
            rsl.optimal_equal_stage_split(9000, 1, 300, 0.1)


class StageCountForDeltaVTest(unittest.TestCase):
    def test_anchor_stage_count(self):
        # two stages give 0.01679 < 0.02; three give 0.0243 >= 0.02
        n, lam_total = rsl.stage_count_for_delta_v(9000, 300, 0.1, 0.02)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(lam_total, 0.0243, delta=1e-3)

    def test_harder_target_more_stages(self):
        n1, _ = rsl.stage_count_for_delta_v(9000, 300, 0.1, 0.01)
        n2, _ = rsl.stage_count_for_delta_v(9000, 300, 0.1, 0.02)
        self.assertGreaterEqual(n2, n1)

    def test_infeasible_target_raises(self):
        # asymptotic limit is exp(-9000 / (2941.995 * 0.9)) = 0.0334
        with self.assertRaises(ValueError):
            rsl.stage_count_for_delta_v(9000, 300, 0.1, 0.05)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.stage_count_for_delta_v(0, 300, 0.1, 0.02)  # dv <= 0
        with self.assertRaises(ValueError):
            rsl.stage_count_for_delta_v(9000, 0, 0.1, 0.02)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.stage_count_for_delta_v(9000, 300, 0.0, 0.02)  # eps <= 0
        with self.assertRaises(ValueError):
            rsl.stage_count_for_delta_v(9000, 300, 0.1, 0.0)  # target <= 0
        with self.assertRaises(ValueError):
            rsl.stage_count_for_delta_v(9000, 300, 0.1, 1.0)  # target >= 1


class TotalStagedDeltaVTest(unittest.TestCase):
    def test_anchor_stage_sum(self):
        self.assertEqual(rsl.total_staged_delta_v([2000.0, 1500.0]), 3500.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.total_staged_delta_v([])  # empty list
        with self.assertRaises(ValueError):
            rsl.total_staged_delta_v([2000.0, -100.0])  # negative element


if __name__ == "__main__":
    unittest.main(verbosity=2)
