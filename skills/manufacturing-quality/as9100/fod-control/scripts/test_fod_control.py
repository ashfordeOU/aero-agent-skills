"""Deterministic contract test for the FOD prevention program logic.

Covers the wave-28 worked example (score 19, zone A, sweep 8 h, missing
drill-7), zone B and C boundaries and sets, sweep intervals, tool
reconciliation exact/partial/extra cases, audit pass and fail verdicts,
completeness values, findings contents, and ValueError rejection of
non-physical inputs. Runs offline via: python3 test_fod_control.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fod_control_logic import (  # noqa: E402
    CONTROL_SET,
    reconcile_tools,
    required_controls,
    risk_score,
    sweep_interval_h,
    zone_class,
    program_audit,
)

ISSUED = {"torque-wrench-1": 1, "drill-7": 2}
RETURNED = {"torque-wrench-1": 1}
ALL_A = list(CONTROL_SET["A"])


class RiskScoreTests(unittest.TestCase):
    def test_risk_score_worked_example(self):
        self.assertEqual(risk_score(3, 3, 2), 19)

    def test_risk_score_zone_b_example(self):
        self.assertEqual(risk_score(2, 2, 1), 12)

    def test_risk_score_zone_c_example(self):
        self.assertEqual(risk_score(1, 1, 0), 5)

    def test_risk_score_bounds(self):
        self.assertEqual(risk_score(1, 1, 0), 5)
        self.assertEqual(risk_score(3, 3, 2), 19)

    def test_risk_score_out_of_band_valueerrors(self):
        for bad in (0, 4, 7, -2):
            with self.assertRaises(ValueError):
                risk_score(bad, 2, 1)
            with self.assertRaises(ValueError):
                risk_score(2, bad, 1)
        with self.assertRaises(ValueError):
            risk_score(2, 2, -1)
        with self.assertRaises(ValueError):
            risk_score(2, 2, 3)


class ZoneClassTests(unittest.TestCase):
    def test_zone_class_boundary_14_is_A(self):
        self.assertEqual(zone_class(14), "A")

    def test_zone_class_13_is_B(self):
        self.assertEqual(zone_class(13), "B")

    def test_zone_class_boundary_10_is_B(self):
        self.assertEqual(zone_class(10), "B")

    def test_zone_class_9_is_C(self):
        self.assertEqual(zone_class(9), "C")

    def test_zone_class_worked_scores(self):
        self.assertEqual(zone_class(19), "A")
        self.assertEqual(zone_class(12), "B")
        self.assertEqual(zone_class(5), "C")

    def test_zone_class_negative_score_valueerror(self):
        with self.assertRaises(ValueError):
            zone_class(-1)


class SweepIntervalTests(unittest.TestCase):
    def test_sweep_interval_zone_a_8h(self):
        self.assertEqual(sweep_interval_h("A"), 8)

    def test_sweep_interval_zone_b_40h(self):
        self.assertEqual(sweep_interval_h("B"), 40)

    def test_sweep_interval_zone_c_160h(self):
        self.assertEqual(sweep_interval_h("C"), 160)

    def test_sweep_interval_unknown_zone_valueerror(self):
        with self.assertRaises(ValueError):
            sweep_interval_h("D")


class RequiredControlsTests(unittest.TestCase):
    def test_required_controls_zone_a_six_items(self):
        self.assertEqual(
            required_controls("A"),
            ["tool-control", "count-reconcile", "sweep-log",
             "tethering", "fod-mats", "training"],
        )

    def test_required_controls_zone_b_four_items(self):
        self.assertEqual(
            required_controls("B"),
            ["tool-control", "count-reconcile", "sweep-log", "fod-mats"],
        )

    def test_required_controls_zone_c_two_items(self):
        self.assertEqual(
            required_controls("C"),
            ["tool-control", "sweep-log"],
        )

    def test_required_controls_return_fresh_copy(self):
        copy_a = required_controls("A")
        copy_a.append("intruder-control")
        self.assertNotIn("intruder-control", required_controls("A"))

    def test_required_controls_unknown_zone_valueerror(self):
        with self.assertRaises(ValueError):
            required_controls("X")


class ReconcileTests(unittest.TestCase):
    def test_reconcile_exact_full_return(self):
        result = reconcile_tools({"torque-wrench-1": 1},
                                 {"torque-wrench-1": 1})
        self.assertEqual(result["missing"], {})
        self.assertTrue(result["reconciled"])

    def test_reconcile_worked_example_missing_drill_7(self):
        result = reconcile_tools(ISSUED, RETURNED)
        self.assertEqual(result["missing"], {"drill-7": 2})
        self.assertFalse(result["reconciled"])

    def test_reconcile_partial_shortfall_value(self):
        result = reconcile_tools({"drill-7": 5}, {"drill-7": 3})
        self.assertEqual(result["missing"], {"drill-7": 2})
        self.assertFalse(result["reconciled"])

    def test_reconcile_extra_unissued_return_ignored(self):
        result = reconcile_tools({"torque-wrench-1": 1},
                                 {"torque-wrench-1": 1, "hammer-9": 1})
        self.assertEqual(result["missing"], {})
        self.assertTrue(result["reconciled"])

    def test_reconcile_over_return_of_issued_tool_ok(self):
        result = reconcile_tools({"drill-7": 2}, {"drill-7": 3})
        self.assertEqual(result["missing"], {})
        self.assertTrue(result["reconciled"])

    def test_reconcile_negative_issued_qty_valueerror(self):
        with self.assertRaises(ValueError):
            reconcile_tools({"drill-7": -1}, {})

    def test_reconcile_negative_returned_qty_valueerror(self):
        with self.assertRaises(ValueError):
            reconcile_tools({}, {"drill-7": -2})


class ProgramAuditTests(unittest.TestCase):
    A_CONTROLS_MISSING_TETHERING = ["tool-control", "count-reconcile",
                                    "sweep-log", "fod-mats", "training"]

    def test_audit_worked_example_all_fields(self):
        result = program_audit(3, 3, 2, ISSUED, RETURNED,
                               self.A_CONTROLS_MISSING_TETHERING)
        self.assertEqual(result["score"], 19)
        self.assertEqual(result["zone"], "A")
        self.assertEqual(result["sweep_interval_h"], 8)
        self.assertEqual(result["required"], ALL_A)
        self.assertEqual(result["present"], self.A_CONTROLS_MISSING_TETHERING)
        self.assertEqual(result["missing_controls"], ["tethering"])
        self.assertAlmostEqual(result["completeness"], 5 / 6.0, places=4)
        self.assertEqual(result["reconciliation"]["missing"],
                         {"drill-7": 2})
        self.assertFalse(result["reconciliation"]["reconciled"])
        self.assertEqual(result["findings"], ["tethering", "missing-tool"])
        self.assertEqual(result["verdict"], "fod-fail")

    def test_audit_clean_case_pass(self):
        returned = {"torque-wrench-1": 1, "drill-7": 2}
        result = program_audit(3, 3, 2, ISSUED, returned, ALL_A)
        self.assertEqual(result["completeness"], 1.0)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["verdict"], "fod-pass")

    def test_audit_zone_b_case(self):
        required_b = required_controls("B")
        result = program_audit(2, 2, 1, {"reamer-4": 1}, {"reamer-4": 1},
                               required_b)
        self.assertEqual(result["score"], 12)
        self.assertEqual(result["zone"], "B")
        self.assertEqual(result["sweep_interval_h"], 40)
        self.assertEqual(result["required"], required_b)
        self.assertEqual(result["completeness"], 1.0)
        self.assertEqual(result["verdict"], "fod-pass")

    def test_audit_zone_c_case(self):
        required_c = required_controls("C")
        result = program_audit(1, 1, 0, {"file-2": 1}, {"file-2": 1},
                               required_c)
        self.assertEqual(result["score"], 5)
        self.assertEqual(result["zone"], "C")
        self.assertEqual(result["sweep_interval_h"], 160)
        self.assertEqual(result["required"], required_c)
        self.assertEqual(result["completeness"], 1.0)
        self.assertEqual(result["verdict"], "fod-pass")

    def test_audit_missing_tool_only_fails(self):
        result = program_audit(1, 1, 0, {"file-2": 1}, {},
                               required_controls("C"))
        self.assertEqual(result["completeness"], 1.0)
        self.assertEqual(result["findings"], ["missing-tool"])
        self.assertEqual(result["verdict"], "fod-fail")

    def test_audit_incomplete_controls_fail(self):
        result = program_audit(3, 3, 2, {"torque-wrench-1": 1},
                               {"torque-wrench-1": 1},
                               ["tool-control", "sweep-log"])
        self.assertEqual(result["completeness"], 2 / 6.0)
        self.assertEqual(result["verdict"], "fod-fail")
        self.assertEqual(result["missing_controls"],
                         ["count-reconcile", "tethering", "fod-mats",
                          "training"])

    def test_audit_unknown_control_valueerror(self):
        with self.assertRaises(ValueError):
            program_audit(3, 3, 2, ISSUED, RETURNED,
                          ["tool-control", "laser-guard"])

    def test_audit_negative_tool_qty_valueerror(self):
        with self.assertRaises(ValueError):
            program_audit(3, 3, 2, {"drill-7": -1}, {}, ALL_A)


if __name__ == "__main__":
    unittest.main()
