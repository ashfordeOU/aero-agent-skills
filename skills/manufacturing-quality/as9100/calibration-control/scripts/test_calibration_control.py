#!/usr/bin/env python3
"""Gate 3 contract test: AS9100-style calibration control.

Exercises scripts/calibration_control_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the calibration
decision functions (TAR verdict, due-date verdict, tolerance check,
out-of-tolerance impact verdict) return the analytic values below;
invalid inputs raise ValueError.

Analytic expected values (hand-computed):
- tar_verdict(0.004, 0.001): TAR = 0.004/0.001 = 4.0, >= 4.0 -> 'ok'
  (boundary case passes).
- tar_verdict(0.005, 0.001): TAR = 5.0 -> 'ok'.
- tar_verdict(0.002, 0.001): TAR = 2.0 -> 'insufficient'.
- tar_verdict(0.0005, 0.0002): TAR = 2.5 -> 'insufficient'.
- tar_verdict(0.0001, 0.0001): TAR = 1.0 -> 'insufficient'.
- calibration_due_verdict(30): due in 30 days -> 'ok'.
- calibration_due_verdict(0): due today, still within interval -> 'ok'.
- calibration_due_verdict(-1): due date passed -> 'overdue'.
- calibration_due_verdict(-90): 90 days overdue -> 'overdue'.
- tolerance_check(10.004, 10.0, 0.005): |0.004| <= 0.005 ->
  'in-tolerance'.
- tolerance_check(10.005, 10.0, 0.005): |0.005| <= 0.005 ->
  'in-tolerance' (boundary case passes).
- tolerance_check(10.006, 10.0, 0.005): |0.006| > 0.005 -> 'out'.
- tolerance_check(9.994, 10.0, 0.005): |9.994 - 10.0| = 0.006 > 0.005
  -> 'out'.
- tolerance_check(9.995, 10.0, 0.005): |0.005| <= 0.005 ->
  'in-tolerance'.
- oot_impact_verdict(0): no product released in the affected period ->
  'review'.
- oot_impact_verdict(1): one item released with the drifted standard ->
  'recall'.
- oot_impact_verdict(25): 25 items released -> 'recall'.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibration_control_logic as ccl  # noqa: E402


class TarVerdictTest(unittest.TestCase):
    def test_tar_boundary_four_ok(self):
        # TAR = 0.004/0.001 = 4.0, exactly at the 4:1 floor -> ok.
        self.assertEqual(ccl.tar_verdict(0.004, 0.001), "ok")

    def test_tar_five_ok(self):
        # TAR = 0.005/0.001 = 5.0 -> ok.
        self.assertEqual(ccl.tar_verdict(0.005, 0.001), "ok")

    def test_tar_two_insufficient(self):
        # TAR = 0.002/0.001 = 2.0 -> insufficient.
        self.assertEqual(ccl.tar_verdict(0.002, 0.001), "insufficient")

    def test_tar_two_point_five_insufficient(self):
        # TAR = 0.0005/0.0002 = 2.5 -> insufficient.
        self.assertEqual(ccl.tar_verdict(0.0005, 0.0002), "insufficient")

    def test_tar_one_insufficient(self):
        # TAR = 0.0001/0.0001 = 1.0 -> insufficient.
        self.assertEqual(ccl.tar_verdict(0.0001, 0.0001), "insufficient")

    def test_tar_same_unit_engineering(self):
        # Same engineering unit, e.g. mm: 0.010/0.002 = 5.0 -> ok.
        self.assertEqual(ccl.tar_verdict(0.010, 0.002), "ok")

    def test_tar_zero_standard_raises(self):
        with self.assertRaises(ValueError):
            ccl.tar_verdict(0.0, 0.001)

    def test_tar_negative_unit_raises(self):
        with self.assertRaises(ValueError):
            ccl.tar_verdict(0.004, -0.001)

    def test_tar_non_number_raises(self):
        with self.assertRaises(ValueError):
            ccl.tar_verdict("0.004", 0.001)

    def test_tar_bool_raises(self):
        with self.assertRaises(ValueError):
            ccl.tar_verdict(True, 0.001)


class DueVerdictTest(unittest.TestCase):
    def test_due_in_thirty_days_ok(self):
        self.assertEqual(ccl.calibration_due_verdict(30), "ok")

    def test_due_today_ok(self):
        # Due today: still within the interval until end of day.
        self.assertEqual(ccl.calibration_due_verdict(0), "ok")

    def test_one_day_overdue(self):
        self.assertEqual(ccl.calibration_due_verdict(-1), "overdue")

    def test_ninety_days_overdue(self):
        self.assertEqual(ccl.calibration_due_verdict(-90), "overdue")

    def test_float_days_raises(self):
        with self.assertRaises(ValueError):
            ccl.calibration_due_verdict(1.5)

    def test_bool_days_raises(self):
        with self.assertRaises(ValueError):
            ccl.calibration_due_verdict(True)


class ToleranceCheckTest(unittest.TestCase):
    def test_within_tolerance(self):
        # |10.004 - 10.0| = 0.004 <= 0.005 -> in-tolerance.
        self.assertEqual(ccl.tolerance_check(10.004, 10.0, 0.005), "in-tolerance")

    def test_boundary_in_tolerance(self):
        # |10.005 - 10.0| = 0.005 <= 0.005 -> in-tolerance.
        self.assertEqual(ccl.tolerance_check(10.005, 10.0, 0.005), "in-tolerance")

    def test_above_tolerance_out(self):
        # |10.006 - 10.0| = 0.006 > 0.005 -> out.
        self.assertEqual(ccl.tolerance_check(10.006, 10.0, 0.005), "out")

    def test_below_nominal_out(self):
        # |9.994 - 10.0| = 0.006 > 0.005 -> out.
        self.assertEqual(ccl.tolerance_check(9.994, 10.0, 0.005), "out")

    def test_lower_boundary_in_tolerance(self):
        # |9.995 - 10.0| = 0.005 <= 0.005 -> in-tolerance.
        self.assertEqual(ccl.tolerance_check(9.995, 10.0, 0.005), "in-tolerance")

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            ccl.tolerance_check(10.0, 10.0, -0.001)


class OotImpactVerdictTest(unittest.TestCase):
    def test_no_released_product_review(self):
        # No product released in the affected period -> review only.
        self.assertEqual(ccl.oot_impact_verdict(0), "review")

    def test_single_released_item_recall(self):
        # One item released with the drifted standard -> recall.
        self.assertEqual(ccl.oot_impact_verdict(1), "recall")

    def test_many_released_items_recall(self):
        # 25 items released in the affected period -> recall.
        self.assertEqual(ccl.oot_impact_verdict(25), "recall")

    def test_negative_period_raises(self):
        with self.assertRaises(ValueError):
            ccl.oot_impact_verdict(-1)

    def test_float_period_raises(self):
        with self.assertRaises(ValueError):
            ccl.oot_impact_verdict(2.5)

    def test_bool_period_raises(self):
        with self.assertRaises(ValueError):
            ccl.oot_impact_verdict(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
