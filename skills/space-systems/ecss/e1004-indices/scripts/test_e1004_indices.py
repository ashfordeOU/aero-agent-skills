#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 6.2.2 / Annex A solar
and geomagnetic activity index selection.

Exercises scripts/e1004_indices_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the required index set is
determined from the analysis purpose; an indices dict is complete only
when every required index is present and not None; an 81-day-average
F10.7 value at or below the solar-minimum reference determines
solar_minimum, at or above the solar-maximum reference determines
solar_maximum, otherwise solar_mean; a drag_worst_case case is
compliant only when its indices are complete and its solar epoch is
solar_maximum; a deorbit_lifetime_worst_case case is compliant only
when its indices are complete and its solar epoch is solar_minimum; an
em_radiation_reference or geomagnetic_field_epoch case is compliant
when its indices are complete regardless of solar epoch; the
assessment record covers every case with no duplicates and is reported
all-compliant only when every case is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_indices_logic as il  # noqa: E402


class RequiredIndicesTest(unittest.TestCase):
    def test_drag_worst_case_requires_f107_and_ap(self):
        self.assertEqual(
            il.required_indices("drag_worst_case"),
            ("f107_daily", "f107_81day_avg", "ap_daily"),
        )

    def test_em_radiation_reference_requires_f107_average_only(self):
        self.assertEqual(
            il.required_indices("em_radiation_reference"), ("f107_81day_avg",)
        )

    def test_geomagnetic_field_epoch_requires_kp(self):
        self.assertEqual(
            il.required_indices("geomagnetic_field_epoch"), ("kp_3hourly",)
        )

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            il.required_indices("charging_worst_case")


class MissingAndCompleteIndicesTest(unittest.TestCase):
    def test_complete_indices_reports_no_missing(self):
        indices = {"f107_daily": 150.0, "f107_81day_avg": 140.0, "ap_daily": 12.0}
        self.assertEqual(il.missing_indices("drag_worst_case", indices), [])
        self.assertTrue(il.indices_complete("drag_worst_case", indices))

    def test_missing_index_is_reported_by_name(self):
        indices = {"f107_daily": 150.0, "ap_daily": 12.0}
        self.assertEqual(
            il.missing_indices("drag_worst_case", indices), ["f107_81day_avg"]
        )
        self.assertFalse(il.indices_complete("drag_worst_case", indices))

    def test_none_value_counts_as_missing(self):
        indices = {"f107_daily": 150.0, "f107_81day_avg": None, "ap_daily": 12.0}
        self.assertFalse(il.indices_complete("drag_worst_case", indices))

    def test_empty_indices_dict_reports_all_required_missing(self):
        self.assertEqual(
            il.missing_indices("em_radiation_reference", {}), ["f107_81day_avg"]
        )


class RequiredSolarConditionTest(unittest.TestCase):
    def test_drag_worst_case_requires_solar_maximum(self):
        self.assertEqual(il.required_solar_condition("drag_worst_case"), "solar_maximum")

    def test_deorbit_lifetime_worst_case_requires_solar_minimum(self):
        self.assertEqual(
            il.required_solar_condition("deorbit_lifetime_worst_case"), "solar_minimum"
        )

    def test_em_radiation_reference_has_no_fixed_condition(self):
        self.assertIsNone(il.required_solar_condition("em_radiation_reference"))

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            il.required_solar_condition("charging_worst_case")


class DetermineSolarEpochTest(unittest.TestCase):
    def test_at_or_below_minimum_reference_is_solar_minimum(self):
        self.assertEqual(il.determine_solar_epoch(70.0), "solar_minimum")
        self.assertEqual(il.determine_solar_epoch(65.0), "solar_minimum")

    def test_at_or_above_maximum_reference_is_solar_maximum(self):
        self.assertEqual(il.determine_solar_epoch(200.0), "solar_maximum")
        self.assertEqual(il.determine_solar_epoch(260.0), "solar_maximum")

    def test_between_references_is_solar_mean(self):
        self.assertEqual(il.determine_solar_epoch(140.0), "solar_mean")

    def test_non_positive_value_raises(self):
        with self.assertRaises(ValueError):
            il.determine_solar_epoch(0.0)
        with self.assertRaises(ValueError):
            il.determine_solar_epoch(-10.0)


class ReferenceIndicesTest(unittest.TestCase):
    def test_reference_values_for_each_epoch(self):
        self.assertEqual(
            il.reference_indices_for_epoch("solar_minimum"),
            {"f107_81day_avg": 70.0, "ap_daily": 5.0},
        )
        self.assertEqual(
            il.reference_indices_for_epoch("solar_maximum"),
            {"f107_81day_avg": 200.0, "ap_daily": 30.0},
        )

    def test_returned_dict_is_a_copy(self):
        result = il.reference_indices_for_epoch("solar_mean")
        result["f107_81day_avg"] = 999.0
        self.assertEqual(
            il.reference_indices_for_epoch("solar_mean")["f107_81day_avg"], 140.0
        )

    def test_unknown_epoch_raises(self):
        with self.assertRaises(ValueError):
            il.reference_indices_for_epoch("solar_storm")

    def test_select_reference_indices_uses_purpose_condition(self):
        self.assertEqual(
            il.select_reference_indices("drag_worst_case"),
            il.reference_indices_for_epoch("solar_maximum"),
        )
        self.assertEqual(
            il.select_reference_indices("deorbit_lifetime_worst_case"),
            il.reference_indices_for_epoch("solar_minimum"),
        )

    def test_select_reference_indices_defaults_to_solar_mean(self):
        self.assertEqual(
            il.select_reference_indices("em_radiation_reference"),
            il.reference_indices_for_epoch("solar_mean"),
        )


class AssessEpochCaseTest(unittest.TestCase):
    def test_compliant_drag_case_at_solar_maximum(self):
        case = {
            "id": "IDX-001",
            "purpose": "drag_worst_case",
            "indices": {
                "f107_daily": 210.0,
                "f107_81day_avg": 205.0,
                "ap_daily": 28.0,
            },
        }
        result = il.assess_epoch_case(case)
        self.assertTrue(result["complete"])
        self.assertEqual(result["solar_epoch"], "solar_maximum")
        self.assertTrue(result["condition_adequate"])
        self.assertTrue(result["compliant"])

    def test_noncompliant_drag_case_at_solar_minimum(self):
        case = {
            "id": "IDX-002",
            "purpose": "drag_worst_case",
            "indices": {
                "f107_daily": 68.0,
                "f107_81day_avg": 68.0,
                "ap_daily": 4.0,
            },
        }
        result = il.assess_epoch_case(case)
        self.assertTrue(result["complete"])
        self.assertEqual(result["solar_epoch"], "solar_minimum")
        self.assertFalse(result["condition_adequate"])
        self.assertFalse(result["compliant"])

    def test_compliant_deorbit_lifetime_case_at_solar_minimum(self):
        case = {
            "id": "IDX-003",
            "purpose": "deorbit_lifetime_worst_case",
            "indices": {
                "f107_daily": 65.0,
                "f107_81day_avg": 70.0,
                "ap_daily": 5.0,
            },
        }
        result = il.assess_epoch_case(case)
        self.assertEqual(result["solar_epoch"], "solar_minimum")
        self.assertTrue(result["condition_adequate"])
        self.assertTrue(result["compliant"])

    def test_noncompliant_case_with_missing_index(self):
        case = {
            "id": "IDX-004",
            "purpose": "drag_worst_case",
            "indices": {"f107_daily": 210.0, "ap_daily": 28.0},
        }
        result = il.assess_epoch_case(case)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_indices"], ["f107_81day_avg"])
        self.assertFalse(result["compliant"])

    def test_purpose_without_fixed_condition_is_compliant_when_complete(self):
        case = {
            "id": "IDX-005",
            "purpose": "em_radiation_reference",
            "indices": {"f107_81day_avg": 90.0},
        }
        result = il.assess_epoch_case(case)
        self.assertEqual(result["solar_epoch"], "solar_mean")
        self.assertTrue(result["condition_adequate"])
        self.assertTrue(result["compliant"])

    def test_geomagnetic_field_epoch_case_has_no_solar_epoch(self):
        case = {
            "id": "IDX-006",
            "purpose": "geomagnetic_field_epoch",
            "indices": {"kp_3hourly": 4.0},
        }
        result = il.assess_epoch_case(case)
        self.assertIsNone(result["solar_epoch"])
        self.assertTrue(result["condition_adequate"])
        self.assertTrue(result["compliant"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            il.assess_epoch_case({
                "purpose": "em_radiation_reference",
                "indices": {"f107_81day_avg": 100.0},
            })

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            il.assess_epoch_case({
                "id": "IDX-007",
                "purpose": "charging_worst_case",
                "indices": {"f107_81day_avg": 100.0},
            })


class BuildEpochAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "IDX-001",
            "purpose": "drag_worst_case",
            "indices": {
                "f107_daily": 210.0,
                "f107_81day_avg": 205.0,
                "ap_daily": 28.0,
            },
        },
        {
            "id": "IDX-002",
            "purpose": "drag_worst_case",
            "indices": {
                "f107_daily": 68.0,
                "f107_81day_avg": 68.0,
                "ap_daily": 4.0,
            },
        },
    ]

    def test_record_order_and_status(self):
        record = il.build_epoch_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "IDX-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "IDX-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            il.build_epoch_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        il.build_epoch_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = il.build_epoch_assessment(BuildEpochAssessmentTest.CASES)
        self.assertEqual(il.noncompliant_items(record), ["IDX-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = il.build_epoch_assessment([BuildEpochAssessmentTest.CASES[0]])
        self.assertTrue(il.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = il.build_epoch_assessment(BuildEpochAssessmentTest.CASES)
        self.assertFalse(il.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
