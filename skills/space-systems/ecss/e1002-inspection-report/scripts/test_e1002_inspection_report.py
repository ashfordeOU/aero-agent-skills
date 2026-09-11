#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-inspection-report (stdlib, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_inspection_report_logic import (  # noqa: E402
    ATTRIBUTE_RESULTS, CHARACTERISTIC_KINDS, calibration_valid,
    characteristic_result, equipment_violations, inspection_report_review,
    inspector_violations, is_inspection_acceptable, tolerance_band,
    validate_kind, within_tolerance,
)

DAY = 100
ROSTER = ["inspector.q"]
GAUGE = {"equipment_id": "CMM-1", "calibration_due_day": 120}


def variable(cid="V1", measured=10.0, nominal=10.0, lo=0.1, hi=0.1, eq=None):
    return {"characteristic_id": cid, "kind": "variable", "measured": measured,
            "nominal": nominal, "lower_tolerance": lo, "upper_tolerance": hi,
            "equipment": dict(GAUGE) if eq is None else eq}


def attribute(cid="A1", result="conforming"):
    return {"characteristic_id": cid, "kind": "attribute", "result": result}


def report(**over):
    r = {"article_id": "SN003", "inspector": "inspector.q",
         "inspection_day": DAY, "characteristics": [variable(), attribute()]}
    r.update(over)
    return r


class KindTest(unittest.TestCase):
    def test_every_kind_validates(self):
        for k in CHARACTERISTIC_KINDS:
            self.assertEqual(validate_kind(k), k)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_kind("vibe")

    def test_attribute_results_are_declared(self):
        self.assertIn("nonconforming", ATTRIBUTE_RESULTS)


class ToleranceTest(unittest.TestCase):
    def test_band_is_nominal_plus_minus_tolerances(self):
        self.assertEqual(tolerance_band(10.0, 0.2, 0.3), (9.8, 10.3))

    def test_asymmetric_band_is_supported(self):
        self.assertEqual(tolerance_band(5.0, 0.0, 1.0), (5.0, 6.0))

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            tolerance_band(10.0, -0.1, 0.1)

    def test_value_inside_band_conforms(self):
        self.assertTrue(within_tolerance(10.05, 10.0, 0.1, 0.1))

    def test_value_on_the_limit_conforms(self):
        self.assertTrue(within_tolerance(10.1, 10.0, 0.1, 0.1))
        self.assertTrue(within_tolerance(9.9, 10.0, 0.1, 0.1))

    def test_value_outside_band_does_not_conform(self):
        self.assertFalse(within_tolerance(10.11, 10.0, 0.1, 0.1))


class CalibrationTest(unittest.TestCase):
    def test_calibration_covering_the_day_is_valid(self):
        self.assertTrue(calibration_valid(GAUGE, DAY))

    def test_calibration_expiring_on_the_day_is_still_valid(self):
        self.assertTrue(calibration_valid({"calibration_due_day": DAY}, DAY))

    def test_calibration_lapsed_before_the_measurement_is_invalid(self):
        self.assertFalse(calibration_valid({"calibration_due_day": DAY - 1}, DAY))

    def test_unknown_calibration_date_is_invalid(self):
        self.assertFalse(calibration_valid({"equipment_id": "X"}, DAY))

    def test_lapsed_equipment_is_reported(self):
        ch = variable(eq={"equipment_id": "CMM-9", "calibration_due_day": DAY - 5})
        f = equipment_violations(ch, DAY)
        self.assertEqual(f[0]["issue"], "calibration_not_valid_at_inspection")

    def test_absent_equipment_is_reported(self):
        f = equipment_violations(variable(eq={}), DAY)
        self.assertEqual(f[0]["issue"], "no_measuring_equipment")

    def test_calibrated_equipment_is_clean(self):
        self.assertEqual(equipment_violations(variable(), DAY), [])


class ResultTest(unittest.TestCase):
    def test_in_tolerance_variable_conforms(self):
        self.assertEqual(characteristic_result(variable(), DAY), "conforming")

    def test_out_of_tolerance_variable_does_not_conform(self):
        self.assertEqual(characteristic_result(variable(measured=11.0), DAY),
                         "nonconforming")

    def test_variable_without_reading_is_not_inspected(self):
        self.assertEqual(characteristic_result(variable(measured=None), DAY),
                         "not_inspected")

    def test_attribute_carries_its_own_result(self):
        self.assertEqual(characteristic_result(attribute("A1", "nonconforming"),
                                               DAY), "nonconforming")

    def test_attribute_without_result_is_not_inspected(self):
        self.assertEqual(characteristic_result({"characteristic_id": "A1",
                                                "kind": "attribute"}, DAY),
                         "not_inspected")

    def test_unknown_attribute_result_raises(self):
        with self.assertRaises(ValueError):
            characteristic_result(attribute("A1", "probably"), DAY)


class InspectorTest(unittest.TestCase):
    def test_qualified_inspector_is_clean(self):
        self.assertEqual(inspector_violations(report(), ROSTER), [])

    def test_unrecorded_inspector_is_reported(self):
        f = inspector_violations(report(inspector=""), ROSTER)
        self.assertEqual(f[0]["issue"], "no_inspector_recorded")

    def test_unqualified_inspector_is_reported(self):
        f = inspector_violations(report(inspector="passerby"), ROSTER)
        self.assertEqual(f[0]["issue"], "inspector_not_qualified")


class ReviewTest(unittest.TestCase):
    def test_clean_report_is_acceptable(self):
        r = inspection_report_review(report(), ROSTER)
        self.assertEqual(sorted(r["conforming"]), ["A1", "V1"])
        self.assertTrue(is_inspection_acceptable(r))

    def test_nonconforming_characteristic_blocks_acceptance(self):
        rep = report(characteristics=[variable(measured=99.0)])
        r = inspection_report_review(rep, ROSTER)
        self.assertEqual(r["nonconforming"], ["V1"])
        self.assertFalse(is_inspection_acceptable(r))

    def test_uninspected_characteristic_blocks_acceptance(self):
        rep = report(characteristics=[variable(measured=None)])
        r = inspection_report_review(rep, ROSTER)
        self.assertEqual(r["not_inspected"], ["V1"])
        self.assertFalse(is_inspection_acceptable(r))

    def test_lapsed_calibration_blocks_acceptance_even_when_conforming(self):
        ch = variable(eq={"equipment_id": "CMM-9", "calibration_due_day": DAY - 1})
        r = inspection_report_review(report(characteristics=[ch]), ROSTER)
        self.assertEqual(r["conforming"], ["V1"])
        self.assertFalse(is_inspection_acceptable(r))

    def test_attribute_needs_no_measuring_equipment(self):
        r = inspection_report_review(report(characteristics=[attribute()]), ROSTER)
        self.assertEqual(r["findings"], [])

    def test_duplicate_characteristic_id_raises(self):
        with self.assertRaises(ValueError):
            inspection_report_review(report(characteristics=[variable(), variable()]),
                                     ROSTER)

    def test_report_without_article_raises(self):
        with self.assertRaises(ValueError):
            inspection_report_review(report(article_id=""), ROSTER)

    def test_report_without_inspection_day_raises(self):
        rep = report()
        del rep["inspection_day"]
        with self.assertRaises(ValueError):
            inspection_report_review(rep, ROSTER)

    def test_review_does_not_mutate_input(self):
        rep = report()
        before = copy.deepcopy(rep)
        inspection_report_review(rep, ROSTER)
        self.assertEqual(rep, before)


if __name__ == "__main__":
    unittest.main()
