#!/usr/bin/env python3
"""Gate 3 contract test: special process qualification.

Exercises scripts/special_process_qualification_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
assess_change() classifies a proposed process change against the
qualification: a parameter outside the qualified range is
requalify-required, an in-range repeat run stays qualified, equipment
and personnel changes are requalify-required, and a time-interval
change past the validity is requalify-required. range_status() reports
the fine-grained in-range/out-of-range verdict. build_record_checklist()
builds and validates the process qualification record (process id,
parameters with ranges, variables, qualification date, validity) and
validate_record() flags missing fields. Invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import special_process_qualification_logic as spql  # noqa: E402


class AssessChangeTest(unittest.TestCase):
    def test_parameter_out_of_range_requalifies(self):
        self.assertEqual(
            spql.assess_change("parameter", value=560, qualified_range=(500, 550)),
            "requalify-required",
        )

    def test_parameter_in_range_repeat_run_stays_qualified(self):
        self.assertEqual(
            spql.assess_change("parameter", value=525, qualified_range=(500, 550)),
            "qualified",
        )

    def test_parameter_at_upper_bound_stays_qualified(self):
        self.assertEqual(
            spql.assess_change("parameter", value=550, qualified_range=(500, 550)),
            "qualified",
        )

    def test_equipment_change_requalifies(self):
        self.assertEqual(spql.assess_change("equipment"), "requalify-required")

    def test_personnel_change_requalifies(self):
        self.assertEqual(spql.assess_change("personnel"), "requalify-required")

    def test_time_interval_expiry_requalifies(self):
        self.assertEqual(
            spql.assess_change(
                "time-interval", elapsed_days=400, validity_days=365
            ),
            "requalify-required",
        )

    def test_time_interval_within_validity_stays_qualified(self):
        self.assertEqual(
            spql.assess_change(
                "time-interval", elapsed_days=100, validity_days=365
            ),
            "qualified",
        )

    def test_unknown_change_type(self):
        with self.assertRaises(ValueError):
            spql.assess_change("recipe-change", value=525, qualified_range=(500, 550))

    def test_parameter_change_missing_range(self):
        with self.assertRaises(ValueError):
            spql.assess_change("parameter", value=525)

    def test_time_interval_missing_days(self):
        with self.assertRaises(ValueError):
            spql.assess_change("time-interval", elapsed_days=10)

    def test_non_numeric_value(self):
        with self.assertRaises(ValueError):
            spql.assess_change("parameter", value="hot", qualified_range=(500, 550))


class RangeStatusTest(unittest.TestCase):
    def test_in_range(self):
        self.assertEqual(spql.range_status(525, (500, 550)), "in-range")

    def test_out_of_range(self):
        self.assertEqual(spql.range_status(560, (500, 550)), "out-of-range")

    def test_boundary_inclusive(self):
        self.assertEqual(spql.range_status(500, (500, 550)), "in-range")
        self.assertEqual(spql.range_status(550, (500, 550)), "in-range")

    def test_bad_range_shape(self):
        with self.assertRaises(ValueError):
            spql.range_status(525, (500,))
        with self.assertRaises(ValueError):
            spql.range_status(525, 550)

    def test_inverted_range(self):
        with self.assertRaises(ValueError):
            spql.range_status(525, (550, 500))

    def test_non_numeric(self):
        with self.assertRaises(ValueError):
            spql.range_status("hot", (500, 550))
        with self.assertRaises(ValueError):
            spql.range_status(525, ("low", 550))


class RecordChecklistTest(unittest.TestCase):
    COMPLETE = dict(
        process_id="HT-101 solution heat treat",
        parameters=[
            {"name": "soak temp", "min": 490, "max": 500},
            {"name": "soak time", "min": 30, "max": 60},
        ],
        variables=["part alloy", "furnace atmosphere"],
        qualification_date="2026-03-01",
        validity=365,
    )

    def test_complete_record(self):
        record = spql.build_record_checklist(**self.COMPLETE)
        self.assertTrue(record["complete"])
        self.assertEqual(record["missing"], [])
        self.assertEqual(len(record["checklist"]), 5)
        for item in record["checklist"]:
            self.assertTrue(item["present"])
        self.assertEqual(record["process_id"], "HT-101 solution heat treat")
        self.assertEqual(record["validity"], 365)
        self.assertEqual(record["parameters"][0]["name"], "soak temp")

    def test_missing_field_flagged(self):
        record = dict(self.COMPLETE)
        del record["qualification_date"]
        missing = spql.validate_record(record)
        self.assertIn("qualification_date", missing)
        self.assertEqual(len(missing), 1)

    def test_empty_parameters_flagged_missing(self):
        record = dict(self.COMPLETE)
        record["parameters"] = []
        missing = spql.validate_record(record)
        self.assertIn("parameters", missing)

    def test_validate_record_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            spql.validate_record("HT-101")

    def test_invalid_parameter_range(self):
        bad = dict(self.COMPLETE)
        bad["parameters"] = [{"name": "soak temp", "min": 500, "max": 490}]
        with self.assertRaises(ValueError):
            spql.build_record_checklist(**bad)

    def test_empty_parameters_rejected(self):
        bad = dict(self.COMPLETE)
        bad["parameters"] = []
        with self.assertRaises(ValueError):
            spql.build_record_checklist(**bad)

    def test_malformed_parameter_rejected(self):
        bad = dict(self.COMPLETE)
        bad["parameters"] = [{"name": "soak temp"}]
        with self.assertRaises(ValueError):
            spql.build_record_checklist(**bad)

    def test_invalid_validity_rejected(self):
        bad = dict(self.COMPLETE)
        bad["validity"] = 0
        with self.assertRaises(ValueError):
            spql.build_record_checklist(**bad)

    def test_invalid_variables_rejected(self):
        bad = dict(self.COMPLETE)
        bad["variables"] = [42]
        with self.assertRaises(ValueError):
            spql.build_record_checklist(**bad)


if __name__ == "__main__":
    unittest.main()
