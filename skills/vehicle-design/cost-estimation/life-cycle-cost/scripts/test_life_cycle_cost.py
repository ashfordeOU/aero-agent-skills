#!/usr/bin/env python3
"""Gate 3 contract test: life-cycle cost estimation.

Exercises scripts/life_cycle_cost_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - power-law CER, Nth unit
cost, exact cumulative average unit cost, present value, annuity,
inflation escalation, LCC phase rollup, and uncertainty range;
invalid inputs raise ValueError. Units: costs in program currency
units, discount rate i and inflation rate f dimensionless fractions
per year, learning curve lc dimensionless (0.85 typical).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import life_cycle_cost_logic as lcc  # noqa: E402


class CerCostTest(unittest.TestCase):
    def test_analytic_cer(self):
        # 100000 * 10000**0.6 = 100000 * 251.188643 = 25118864.315
        self.assertAlmostEqual(
            lcc.cer_cost(100000.0, 10000.0, 0.6), 25118864.315, places=3
        )

    def test_larger_driver_raises_cost(self):
        self.assertGreater(
            lcc.cer_cost(100000.0, 20000.0, 0.6),
            lcc.cer_cost(100000.0, 10000.0, 0.6),
        )

    def test_invalid_inputs_raise(self):
        for args in ((0, 10000.0, 0.6), (100000.0, 0, 0.6), (100000.0, 10000.0, 0)):
            with self.assertRaises(ValueError):
                lcc.cer_cost(*args)


class LearningCurveTest(unittest.TestCase):
    def test_second_unit_is_lc_times_first(self):
        # c2 = 1000 * 2**-0.234465 = 1000 * 0.85 = 850.0 (defining property)
        self.assertAlmostEqual(lcc.unit_cost(1000.0, 2, 0.85), 850.0, places=6)

    def test_analytic_unit_cost(self):
        # c4 = 1000 * 4**-0.234465 = 1000 * 0.85**2 = 722.5
        self.assertAlmostEqual(lcc.unit_cost(1000.0, 4, 0.85), 722.5, places=3)
        self.assertAlmostEqual(lcc.unit_cost(1000.0, 1, 0.85), 1000.0, places=6)

    def test_unit_cost_decreases_with_unit_number(self):
        self.assertLess(lcc.unit_cost(1000.0, 4, 0.85), lcc.unit_cost(1000.0, 2, 0.85))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lcc.unit_cost(0, 2, 0.85)
        with self.assertRaises(ValueError):
            lcc.unit_cost(1000.0, 0, 0.85)
        with self.assertRaises(ValueError):
            lcc.unit_cost(1000.0, 2, 1.0)
        with self.assertRaises(ValueError):
            lcc.unit_cost(1000.0, 2, 0.0)


class CumulativeAverageTest(unittest.TestCase):
    def test_analytic_average_two_units(self):
        # (1000 + 850) / 2 = 925.0 (exact discrete average)
        self.assertAlmostEqual(
            lcc.cumulative_average_unit_cost(1000.0, 2, 0.85), 925.0, places=6
        )

    def test_average_is_mean_of_unit_costs(self):
        # definitional check: average over 4 units equals the mean of
        # the four unit costs, never below the last unit cost
        avg = lcc.cumulative_average_unit_cost(1000.0, 4, 0.85)
        units = [lcc.unit_cost(1000.0, k, 0.85) for k in range(1, 5)]
        self.assertAlmostEqual(avg, sum(units) / 4.0, places=9)
        self.assertGreater(avg, lcc.unit_cost(1000.0, 4, 0.85))

    def test_average_decreases_with_n(self):
        self.assertLess(
            lcc.cumulative_average_unit_cost(1000.0, 4, 0.85),
            lcc.cumulative_average_unit_cost(1000.0, 2, 0.85),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lcc.cumulative_average_unit_cost(0, 2, 0.85)
        with self.assertRaises(ValueError):
            lcc.cumulative_average_unit_cost(1000.0, 0, 0.85)


class PresentValueTest(unittest.TestCase):
    def test_analytic_present_value(self):
        # 1000 / 1.05**10 = 1000 / 1.628895 = 613.913
        self.assertAlmostEqual(lcc.present_value(1000.0, 0.05, 10), 613.913, places=3)

    def test_pv_decreases_with_years_and_rate(self):
        self.assertLess(lcc.present_value(1000.0, 0.05, 10), lcc.present_value(1000.0, 0.05, 5))
        self.assertLess(lcc.present_value(1000.0, 0.08, 10), lcc.present_value(1000.0, 0.05, 10))

    def test_year_zero_is_face_value(self):
        self.assertAlmostEqual(lcc.present_value(1000.0, 0.05, 0), 1000.0, places=9)

    def test_analytic_annuity(self):
        # 100 * (1 - 1.05**-10) / 0.05 = 100 * 7.721735 = 772.173
        self.assertAlmostEqual(
            lcc.annuity_present_value(100.0, 0.05, 10), 772.173, places=3
        )

    def test_annuity_increases_with_years(self):
        self.assertGreater(
            lcc.annuity_present_value(100.0, 0.05, 20),
            lcc.annuity_present_value(100.0, 0.05, 10),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lcc.present_value(0, 0.05, 10)
        with self.assertRaises(ValueError):
            lcc.present_value(1000.0, 0, 10)
        with self.assertRaises(ValueError):
            lcc.present_value(1000.0, 0.05, -1)
        with self.assertRaises(ValueError):
            lcc.annuity_present_value(100.0, 0, 10)
        with self.assertRaises(ValueError):
            lcc.annuity_present_value(100.0, 0.05, 0)


class InflationTest(unittest.TestCase):
    def test_analytic_escalation(self):
        # 1000 * 1.03**5 = 1000 * 1.159274 = 1159.274
        self.assertAlmostEqual(lcc.escalated_cost(1000.0, 0.03, 5), 1159.274, places=3)

    def test_zero_inflation_is_face_value(self):
        self.assertAlmostEqual(lcc.escalated_cost(1000.0, 0.0, 5), 1000.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lcc.escalated_cost(0, 0.03, 5)
        with self.assertRaises(ValueError):
            lcc.escalated_cost(1000.0, -0.01, 5)
        with self.assertRaises(ValueError):
            lcc.escalated_cost(1000.0, 0.03, -1)


class LccTotalTest(unittest.TestCase):
    def test_analytic_rollup(self):
        # O&S PV = 200000 * 7.721735 = 1544346.986
        # disposal PV = 50000 / 1.05**10 = 30695.663
        # total = 100000 + 500000 + 1544346.986 + 30695.663 = 2175042.649
        result = lcc.lcc_total(100000.0, 500000.0, 200000.0, 10, 0.05, 50000.0)
        self.assertAlmostEqual(result["os_present_value"], 1544346.986, places=3)
        self.assertAlmostEqual(result["disposal_present_value"], 30695.663, places=3)
        self.assertAlmostEqual(result["total"], 2175042.649, places=3)

    def test_total_is_sum_of_discounted_phases(self):
        result = lcc.lcc_total(100000.0, 500000.0, 200000.0, 10, 0.05, 50000.0)
        self.assertAlmostEqual(
            result["total"],
            result["rdte"]
            + result["production"]
            + result["os_present_value"]
            + result["disposal_present_value"],
            places=9,
        )

    def test_zero_os_and_disposal_leave_undiscounted_phases(self):
        result = lcc.lcc_total(100000.0, 500000.0, 0.0, 10, 0.05, 0.0)
        self.assertAlmostEqual(result["total"], 600000.0, places=6)
        self.assertAlmostEqual(result["os_present_value"], 0.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lcc.lcc_total(-1.0, 500000.0, 200000.0, 10, 0.05, 50000.0)
        with self.assertRaises(ValueError):
            lcc.lcc_total(100000.0, 500000.0, 200000.0, 10, 0.0, 50000.0)
        with self.assertRaises(ValueError):
            lcc.lcc_total(100000.0, 500000.0, 200000.0, 0, 0.05, 50000.0)


class UncertaintyRangeTest(unittest.TestCase):
    def test_analytic_band(self):
        # 1000 * (1-0.2), 1000 * (1+0.3) = (800, 1300)
        self.assertEqual(lcc.uncertainty_range(1000.0, 0.2, 0.3), (800.0, 1300.0))

    def test_point_lies_inside_band(self):
        low, high = lcc.uncertainty_range(1000.0, 0.2, 0.3)
        self.assertLess(low, 1000.0)
        self.assertGreater(high, 1000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lcc.uncertainty_range(0, 0.2, 0.3)
        with self.assertRaises(ValueError):
            lcc.uncertainty_range(1000.0, -0.1, 0.3)
        with self.assertRaises(ValueError):
            lcc.uncertainty_range(1000.0, 1.0, 0.3)
        with self.assertRaises(ValueError):
            lcc.uncertainty_range(1000.0, 0.2, -0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
