#!/usr/bin/env python3
"""Gate 3 contract test: key characteristic management (AS9103 workflow).

Exercises scripts/key_characteristic_management_logic.py (stdlib unittest,
offline, deterministic). Contract: the five-rule KC decision table (safety
flag, customer designation, fit/function with mate/seal/performance
downstream, tight position/profile tolerance at or below 0.1 mm, two or
more historical failures), the 0-100 weighted risk score with default and
override weight sets, the risk-ranked KC list, the per-KC variation
management plan (control method, Cpk target 1.33 default and 1.67 for
safety-critical, sampling frequency, verification gate), the change
revalidation rule table with evidence, and the markdown-ish KC report.
Non-physical inputs (negative tolerance, unknown feature type, empty batch,
unknown change type, malformed records, invalid weights) raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import key_characteristic_management_logic as kcl  # noqa: E402


def bore_record():
    """Safety-critical bearing bore: the obvious KC in the worked example."""
    return {
        "id": "BRG-BORE-01",
        "name": "bearing bore",
        "feature_type": "hole",
        "tolerance_mm": 0.025,
        "drawing_callout": True,
        "safety_critical": True,
        "fit_function_impact": True,
        "customer_designated": False,
        "downstream_impact": "performance",
        "process_capability_known": True,
        "historical_failures": 0,
    }


def pos_record():
    """Mount hole position at 0.05 mm: the borderline tight-tolerance KC."""
    return {
        "id": "HSNG-POS-02",
        "name": "mount hole position",
        "feature_type": "position",
        "tolerance_mm": 0.05,
        "drawing_callout": True,
        "safety_critical": False,
        "fit_function_impact": True,
        "customer_designated": False,
        "downstream_impact": "mate",
        "process_capability_known": False,
        "historical_failures": 0,
    }


def edge_record():
    """Cosmetic edge break: the clear non-KC in the worked example."""
    return {
        "id": "CASE-EDGE-03",
        "name": "cosmetic edge break",
        "feature_type": "other",
        "tolerance_mm": 0.8,
        "drawing_callout": False,
        "safety_critical": False,
        "fit_function_impact": False,
        "customer_designated": False,
        "downstream_impact": "none",
        "process_capability_known": False,
        "historical_failures": 0,
    }


def seal_record():
    """Seal face flatness with seal downstream impact."""
    return {
        "id": "SEAL-FACE-04",
        "name": "seal face flatness",
        "feature_type": "flatness",
        "tolerance_mm": 0.05,
        "drawing_callout": True,
        "safety_critical": False,
        "fit_function_impact": True,
        "customer_designated": False,
        "downstream_impact": "seal",
        "process_capability_known": True,
        "historical_failures": 0,
    }


def groove_record():
    """O-ring groove width: KC on the customer-designated flag alone."""
    return {
        "id": "GROOVE-W-05",
        "name": "o-ring groove width",
        "feature_type": "thickness",
        "tolerance_mm": 0.15,
        "drawing_callout": True,
        "safety_critical": False,
        "fit_function_impact": False,
        "customer_designated": True,
        "downstream_impact": "none",
        "process_capability_known": True,
        "historical_failures": 0,
    }


def pin_record():
    """Pivot pin diameter: assembly-mate with repeated historical escapes."""
    return {
        "id": "PIVOT-PIN-06",
        "name": "pivot pin diameter",
        "feature_type": "assembly-mate",
        "tolerance_mm": 0.02,
        "drawing_callout": True,
        "safety_critical": False,
        "fit_function_impact": True,
        "customer_designated": False,
        "downstream_impact": "mate",
        "process_capability_known": True,
        "historical_failures": 3,
    }


WORKED_EXAMPLE = [
    bore_record(),
    pos_record(),
    edge_record(),
    seal_record(),
    groove_record(),
    pin_record(),
]


class WorkedExampleTest(unittest.TestCase):
    def test_worked_example_verdicts_all_six(self):
        expected = {
            "BRG-BORE-01": "KC",
            "HSNG-POS-02": "KC",
            "CASE-EDGE-03": "non-KC",
            "SEAL-FACE-04": "KC",
            "GROOVE-W-05": "KC",
            "PIVOT-PIN-06": "KC",
        }
        for rec in WORKED_EXAMPLE:
            verdict = kcl.classify_characteristic(rec)
            self.assertEqual(verdict["verdict"], expected[verdict["id"]], verdict["id"])
            self.assertEqual(verdict["name"], rec["name"])

    def test_safety_reason_on_safety_flag(self):
        verdict = kcl.classify_characteristic(bore_record())
        self.assertEqual(verdict["verdict"], "KC")
        self.assertIn(kcl.REASON_SAFETY, verdict["reasons"])

    def test_customer_designated_alone_kc(self):
        verdict = kcl.classify_characteristic(groove_record())
        self.assertEqual(verdict["verdict"], "KC")
        self.assertEqual(verdict["reasons"], [kcl.REASON_CUSTOMER])

    def test_fit_plus_mate_kc(self):
        rec = dict(edge_record(), feature_type="hole", tolerance_mm=0.4,
                   fit_function_impact=True, downstream_impact="mate")
        verdict = kcl.classify_characteristic(rec)
        self.assertEqual(verdict["verdict"], "KC")
        self.assertTrue(
            any("fit/function impact with mate downstream impact" in r
                for r in verdict["reasons"])
        )

    def test_fit_without_downstream_not_kc(self):
        rec = dict(edge_record(), feature_type="hole", tolerance_mm=0.4,
                   fit_function_impact=True, downstream_impact="none")
        self.assertEqual(kcl.classify_characteristic(rec)["verdict"], "non-KC")

    def test_tight_position_kc_and_boundary(self):
        tight = dict(pos_record(), tolerance_mm=0.05)
        boundary = dict(pos_record(), tolerance_mm=0.1)
        for rec in (tight, boundary):
            verdict = kcl.classify_characteristic(rec)
            self.assertEqual(verdict["verdict"], "KC", rec["tolerance_mm"])
            self.assertTrue(
                any("tight tolerance threshold of 0.1 mm" in r
                    for r in verdict["reasons"])
            )

    def test_wide_position_tolerance_not_kc(self):
        rec = dict(pos_record(), tolerance_mm=0.25, fit_function_impact=False,
                   downstream_impact="none")
        self.assertEqual(kcl.classify_characteristic(rec)["verdict"], "non-KC")

    def test_historical_failures_kc(self):
        rec = dict(edge_record(), historical_failures=2)
        verdict = kcl.classify_characteristic(rec)
        self.assertEqual(verdict["verdict"], "KC")
        self.assertTrue(
            any("2 historical failures at or above" in r for r in verdict["reasons"])
        )

    def test_no_rule_no_kc_with_explanation(self):
        verdict = kcl.classify_characteristic(edge_record())
        self.assertEqual(verdict["verdict"], "non-KC")
        self.assertEqual(verdict["reasons"], [kcl.REASON_NONE])

    def test_kc_reasons_follow_table_order(self):
        verdict = kcl.classify_characteristic(pin_record())
        self.assertEqual(verdict["verdict"], "KC")
        self.assertEqual(len(verdict["reasons"]), 2)
        self.assertIn("fit/function impact with mate downstream impact",
                      verdict["reasons"][0])
        self.assertIn("3 historical failures", verdict["reasons"][1])


class RiskScoreTest(unittest.TestCase):
    def test_risk_worked_example_values(self):
        expected = {
            "BRG-BORE-01": 65,
            "HSNG-POS-02": 55,
            "SEAL-FACE-04": 35,
            "PIVOT-PIN-06": 50,
            "GROOVE-W-05": 0,
        }
        for rec in WORKED_EXAMPLE:
            score = kcl.kc_risk_score(rec)
            if rec["id"] in expected:
                self.assertEqual(score, expected[rec["id"]], rec["id"])
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)

    def test_risk_full_stack_100(self):
        rec = dict(pos_record(), tolerance_mm=0.05, safety_critical=True,
                   downstream_impact="mate", historical_failures=2)
        self.assertEqual(kcl.kc_risk_score(rec), 100)

    def test_risk_customer_only_zero_and_still_kc(self):
        self.assertEqual(kcl.kc_risk_score(groove_record()), 0)
        self.assertEqual(kcl.classify_characteristic(groove_record())["verdict"], "KC")

    def test_risk_override_weights_change_score(self):
        weights = {"safety": 40, "fit_function": 25, "tight_tolerance": 15,
                   "historical": 10, "downstream": 10}
        self.assertEqual(kcl.kc_risk_score(bore_record(), weights), 75)
        self.assertEqual(kcl.kc_risk_score(bore_record()), 65)

    def test_risk_float_override_rounds(self):
        weights = {"safety": 40.0, "fit_function": 20.0, "tight_tolerance": 15.0,
                   "historical": 10.0, "downstream": 15.0}
        self.assertEqual(kcl.kc_risk_score(bore_record(), weights), 75.0)


class RankAndPlanTest(unittest.TestCase):
    def test_rank_order_worked_example(self):
        rows = kcl.rank_key_characteristics(WORKED_EXAMPLE)
        self.assertEqual([r["id"] for r in rows],
                         ["BRG-BORE-01", "HSNG-POS-02", "PIVOT-PIN-06",
                          "SEAL-FACE-04", "GROOVE-W-05"])
        self.assertEqual(rows[0]["score"], 65)
        self.assertEqual(rows[-1]["score"], 0)

    def test_rank_skips_non_kc_and_ties_break_by_id(self):
        rows = kcl.rank_key_characteristics(
            [dict(groove_record(), id="b-customer"), dict(groove_record(), id="a-customer")]
        )
        self.assertEqual([r["id"] for r in rows], ["a-customer", "b-customer"])
        self.assertTrue(all(r["score"] == 0 for r in rows))

    def test_plan_cpk_safety_167_and_default_133(self):
        plan = kcl.variation_management_plan(WORKED_EXAMPLE)
        by_id = {row["id"]: row for row in plan}
        self.assertEqual(by_id["BRG-BORE-01"]["cpk_target"], 1.67)
        for cid in ("HSNG-POS-02", "SEAL-FACE-04", "PIVOT-PIN-06", "GROOVE-W-05"):
            self.assertEqual(by_id[cid]["cpk_target"], 1.33, cid)

    def test_plan_method_selection_table(self):
        plan = {row["id"]: row["control_method"] for row in
                kcl.variation_management_plan(WORKED_EXAMPLE)}
        self.assertEqual(plan["BRG-BORE-01"], "SPC variable chart Xbar-R")
        self.assertEqual(plan["HSNG-POS-02"], "gage study")
        self.assertEqual(plan["PIVOT-PIN-06"], "attribute")
        electrical = dict(edge_record(), id="SOL-ELEC-07", name="solenoid coil",
                          feature_type="electrical", customer_designated=True)
        hist = dict(edge_record(), id="HSNG-WALL-08", name="housing wall",
                    feature_type="hole", tolerance_mm=0.3,
                    historical_failures=2, process_capability_known=True)
        plan2 = {row["id"]: row["control_method"] for row in
                 kcl.variation_management_plan([electrical, hist])}
        self.assertEqual(plan2["SOL-ELEC-07"], "100 percent inspection")
        self.assertEqual(plan2["HSNG-WALL-08"], "100 percent inspection")

    def test_plan_rows_risk_sorted_and_non_kc_skipped(self):
        plan = kcl.variation_management_plan(WORKED_EXAMPLE)
        ids = [row["id"] for row in plan]
        self.assertEqual(ids, ["BRG-BORE-01", "HSNG-POS-02", "PIVOT-PIN-06",
                               "SEAL-FACE-04", "GROOVE-W-05"])
        self.assertNotIn("CASE-EDGE-03", ids)
        for row in plan:
            self.assertTrue(row["sampling_frequency"])
            self.assertTrue(row["verification_gate"])


class ChangeTriggerTest(unittest.TestCase):
    def test_change_tooling_process_design_trigger_with_evidence(self):
        for change_type in ("tooling", "process", "design"):
            result = kcl.change_trigger(bore_record(), change_type)
            self.assertTrue(result["verdict"], change_type)
            self.assertTrue(result["evidence"], change_type)
            self.assertIn("delta FAI", result["action"])
            for item in result["evidence"]:
                self.assertIsInstance(item, str)
                self.assertTrue(item)
            self.assertTrue(
                any("capability re-study" in item for item in result["evidence"]),
                change_type,
            )

    def test_change_supplier_personnel_no_trigger(self):
        for change_type in ("supplier", "personnel"):
            result = kcl.change_trigger(bore_record(), change_type)
            self.assertFalse(result["verdict"], change_type)
            self.assertEqual(result["evidence"], [], change_type)

    def test_change_non_kc_no_trigger(self):
        result = kcl.change_trigger(edge_record(), "tooling")
        self.assertFalse(result["verdict"])
        self.assertEqual(result["evidence"], [])
        self.assertIn("not a key characteristic", result["action"])

    def test_change_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            kcl.change_trigger(bore_record(), "material")


class ValidationTest(unittest.TestCase):
    def test_plan_and_rank_empty_list_raises(self):
        with self.assertRaises(ValueError):
            kcl.variation_management_plan([])
        with self.assertRaises(ValueError):
            kcl.rank_key_characteristics([])
        with self.assertRaises(ValueError):
            kcl.rank_key_characteristics(())
        with self.assertRaises(ValueError):
            kcl.variation_management_plan("not a list")

    def test_report_empty_list_raises(self):
        with self.assertRaises(ValueError):
            kcl.produce_kc_report([])

    def test_negative_tolerance_raises(self):
        for rec in (bore_record(), edge_record()):
            rec["tolerance_mm"] = -0.1
            with self.assertRaises(ValueError):
                kcl.classify_characteristic(rec)
            with self.assertRaises(ValueError):
                kcl.kc_risk_score(rec)

    def test_unknown_feature_type_raises(self):
        rec = edge_record()
        rec["feature_type"] = "weld"
        with self.assertRaises(ValueError):
            kcl.classify_characteristic(rec)
        rec["feature_type"] = "Position"
        with self.assertRaises(ValueError):
            kcl.classify_characteristic(rec)

    def test_non_numeric_and_missing_tolerance_raises(self):
        for tol in ("0.1", None, True):
            rec = edge_record()
            rec["tolerance_mm"] = tol
            with self.assertRaises(ValueError):
                kcl.classify_characteristic(rec)

    def test_unknown_downstream_impact_raises(self):
        rec = edge_record()
        rec["downstream_impact"] = "crash"
        with self.assertRaises(ValueError):
            kcl.classify_characteristic(rec)

    def test_negative_or_non_int_failures_raise(self):
        for hist in (-1, 1.5, True):
            rec = edge_record()
            rec["historical_failures"] = hist
            with self.assertRaises(ValueError):
                kcl.classify_characteristic(rec)

    def test_missing_or_non_string_id_raises(self):
        with self.assertRaises(ValueError):
            kcl.classify_characteristic({})
        rec = edge_record()
        rec["id"] = 7
        with self.assertRaises(ValueError):
            kcl.classify_characteristic(rec)
        with self.assertRaises(ValueError):
            kcl.classify_characteristic("edge break")

    def test_duplicate_ids_raise(self):
        batch = [bore_record(), bore_record()]
        with self.assertRaises(ValueError):
            kcl.rank_key_characteristics(batch)
        with self.assertRaises(ValueError):
            kcl.variation_management_plan(batch)
        with self.assertRaises(ValueError):
            kcl.produce_kc_report(batch)

    def test_invalid_weights_raise(self):
        with self.assertRaises(ValueError):
            kcl.kc_risk_score(bore_record(), {"safety": 50})
        with self.assertRaises(ValueError):
            kcl.kc_risk_score(bore_record(), {"customer": 10})
        with self.assertRaises(ValueError):
            kcl.kc_risk_score(bore_record(), {"safety": -5, "fit_function": 25,
                                              "tight_tolerance": 20,
                                              "historical": 15,
                                              "downstream": 10})
        with self.assertRaises(ValueError):
            kcl.kc_risk_score(bore_record(), "weights")
        with self.assertRaises(ValueError):
            kcl.kc_risk_score(bore_record(), {"safety": True})


class ReportTest(unittest.TestCase):
    def test_report_content_contract(self):
        lines = kcl.produce_kc_report(WORKED_EXAMPLE)
        joined = "\n".join(lines)
        self.assertEqual(lines[0],
                         "KC report: 6 characteristics evaluated, 5 key characteristics")
        first_kc = next(line for line in lines if line.startswith("- 1. "))
        self.assertIn("BRG-BORE-01", first_kc)
        self.assertIn("risk 65/100", first_kc)
        non_kc = next(line for line in lines if "CASE-EDGE-03" in line)
        self.assertIn("non-KC", non_kc)
        plan_line = next(line for line in lines if "BRG-BORE-01:" in line)
        self.assertIn("Cpk target 1.67", plan_line)
        self.assertIn("Key characteristic count: 5", lines)
        self.assertIn("tooling, process, and design changes trigger KC revalidation",
                      joined)
        self.assertEqual(lines.count(""), 4)  # one blank separator per section gap


if __name__ == "__main__":
    unittest.main(verbosity=2)
