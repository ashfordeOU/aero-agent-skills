"""Contract tests for the per-unit painting record logic.

The cases cover what the record has to survive on: the fields and the
application parameters it must state, the pot life the mixed material was used
inside, the shelf life each lot was inside when it was mixed, the traceability
chain back to the received-lots register, and the retention date the record
itself carries.
"""

import unittest

from q7031_painting_records_logic import (
    DEFAULT_RETENTION_YEARS,
    REQUIRED_FIELDS,
    REQUIRED_PARAMETERS,
    add_months,
    assess_record_set,
    assess_unit_record,
    day_number,
    lot_shelf_life_findings,
    minutes_between,
    missing_fields,
    missing_parameters,
    parse_day,
    parse_timestamp,
    pot_life_findings,
    retention_end_day,
    shelf_life_expiry_day,
    traceability_gaps,
)


def _parameters(**overrides):
    params = {
        "mix_ratio": "4:1:1",
        "spray_pressure_bar": 2.8,
        "gun_distance_mm": 200.0,
        "pass_count": 3,
        "flash_off_minutes": 10.0,
        "cure_temperature_c": 40.0,
        "cure_duration_minutes": 120.0,
    }
    params.update(overrides)
    return params


def _record(**overrides):
    record = {
        "unit_id": "SN-012",
        "drawing_issue": "C",
        "primer_lot_id": "PR-5581",
        "topcoat_lot_id": "TC-9034",
        "mix_timestamp": "2026-04-14T08:30",
        "application_end_timestamp": "2026-04-14T10:00",
        "operator_id": "SPR-04",
        "inspection_result": "accepted",
        "record_day": "2026-04-15",
        "pot_life_minutes": 240.0,
        "parameters": _parameters(),
        "lots": [
            {"lot_id": "PR-5581", "manufacture_day": "2025-10-01", "shelf_months": 12},
            {"lot_id": "TC-9034", "manufacture_day": "2025-11-15", "shelf_months": 12},
        ],
        "applied_lot_ids": ["PR-5581", "TC-9034"],
        "received_register": ["PR-5581", "TC-9034", "PR-5582"],
        "retention_years": 10,
    }
    record.update(overrides)
    return record


class CalendarTests(unittest.TestCase):
    def test_a_day_number_advances_by_one_across_a_month_end(self):
        self.assertEqual(day_number((2026, 5, 1)) - day_number((2026, 4, 30)), 1)

    def test_a_leap_day_is_counted(self):
        self.assertEqual(day_number((2024, 3, 1)) - day_number((2024, 2, 28)), 2)

    def test_a_common_year_february_has_no_twenty_ninth(self):
        with self.assertRaises(ValueError):
            parse_day("mix_day", "2026-02-29")

    def test_months_clamp_to_the_shorter_month(self):
        self.assertEqual(add_months((2025, 1, 31), 1), (2025, 2, 28))

    def test_a_timestamp_carries_an_hour_and_a_minute(self):
        self.assertEqual(parse_timestamp("mix", "2026-04-14T08:30"), ((2026, 4, 14), 8, 30))

    def test_a_date_with_no_time_is_refused_not_taken_as_midnight(self):
        with self.assertRaises(ValueError):
            parse_timestamp("mix", "2026-04-14")

    def test_an_hour_off_the_clock_is_refused(self):
        with self.assertRaises(ValueError):
            parse_timestamp("mix", "2026-04-14T25:00")

    def test_minutes_span_a_day_boundary(self):
        start = parse_timestamp("mix", "2026-04-14T23:30")
        end = parse_timestamp("end", "2026-04-15T00:30")
        self.assertEqual(minutes_between(start, end), 60)

    def test_a_reversed_pair_is_refused(self):
        start = parse_timestamp("mix", "2026-04-14T10:00")
        end = parse_timestamp("end", "2026-04-14T08:00")
        with self.assertRaises(ValueError):
            minutes_between(start, end)


class FieldTests(unittest.TestCase):
    def test_a_complete_record_has_no_missing_fields(self):
        self.assertEqual(missing_fields(_record()), [])

    def test_each_required_field_is_named_when_absent(self):
        for field in REQUIRED_FIELDS:
            self.assertIn(field, missing_fields(_record(**{field: None})))

    def test_a_blank_string_counts_as_missing(self):
        self.assertIn("operator_id", missing_fields(_record(operator_id="   ")))

    def test_a_complete_parameter_set_has_no_gaps(self):
        self.assertEqual(missing_parameters(_parameters()), [])

    def test_each_required_parameter_is_named_when_absent(self):
        for name in REQUIRED_PARAMETERS:
            params = _parameters()
            del params[name]
            self.assertIn(name, missing_parameters(params))

    def test_a_non_numeric_cure_temperature_is_missing_not_zero(self):
        self.assertIn("cure_temperature_c", missing_parameters(_parameters(cure_temperature_c="warm")))

    def test_a_blank_mix_ratio_is_missing(self):
        self.assertIn("mix_ratio", missing_parameters(_parameters(mix_ratio="  ")))

    def test_a_non_mapping_parameter_set_is_refused(self):
        with self.assertRaises(ValueError):
            missing_parameters(["mix_ratio"])


class PotLifeTests(unittest.TestCase):
    def test_material_used_inside_its_pot_life_raises_nothing(self):
        result = pot_life_findings("2026-04-14T08:30", "2026-04-14T10:00", 240.0)
        self.assertEqual(result["minutes_used"], 90)
        self.assertEqual(result["findings"], [])

    def test_material_used_right_to_the_stated_minute_is_inside_it(self):
        result = pot_life_findings("2026-04-14T08:00", "2026-04-14T12:00", 240.0)
        self.assertEqual(result["minutes_used"], 240)
        self.assertEqual(result["findings"], [])

    def test_material_still_going_on_afterwards_is_raised(self):
        result = pot_life_findings("2026-04-14T08:00", "2026-04-14T16:00", 240.0)
        self.assertEqual(result["findings"], ["pot-life-exceeded"])

    def test_a_non_positive_pot_life_is_refused(self):
        with self.assertRaises(ValueError):
            pot_life_findings("2026-04-14T08:00", "2026-04-14T09:00", 0.0)


class ShelfLifeAndTraceTests(unittest.TestCase):
    def test_expiry_follows_the_manufacture_day_and_shelf_months(self):
        self.assertEqual(shelf_life_expiry_day("2025-10-01", 12), (2026, 10, 1))

    def test_a_lot_mixed_on_its_expiry_day_is_still_usable(self):
        findings = lot_shelf_life_findings(
            [{"lot_id": "PR-1", "manufacture_day": "2025-04-14", "shelf_months": 12}],
            "2026-04-14",
        )
        self.assertEqual(findings, [])

    def test_a_lot_mixed_after_expiry_is_named(self):
        findings = lot_shelf_life_findings(
            [{"lot_id": "PR-1", "manufacture_day": "2024-01-01", "shelf_months": 12}],
            "2026-04-14",
        )
        self.assertEqual(findings, ["lot-past-shelf-life:PR-1"])

    def test_a_zero_shelf_life_is_refused(self):
        with self.assertRaises(ValueError):
            shelf_life_expiry_day("2025-10-01", 0)

    def test_a_lot_without_an_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            lot_shelf_life_findings([{"manufacture_day": "2025-10-01", "shelf_months": 12}],
                                    "2026-04-14")

    def test_a_closed_chain_has_no_gaps(self):
        self.assertEqual(traceability_gaps(["PR-5581"], ["PR-5581", "TC-9034"]), [])

    def test_case_is_not_significant_in_a_lot_identifier(self):
        self.assertEqual(traceability_gaps(["pr-5581"], ["PR-5581"]), [])

    def test_a_lot_absent_from_the_register_is_a_gap(self):
        self.assertEqual(traceability_gaps(["PR-9999"], ["PR-5581"]), ["PR-9999"])

    def test_an_empty_applied_lot_list_is_refused(self):
        with self.assertRaises(ValueError):
            traceability_gaps([], ["PR-5581"])

    def test_retention_runs_from_the_record_day(self):
        self.assertEqual(retention_end_day("2026-04-15", 10), (2036, 4, 15))

    def test_the_default_retention_is_a_positive_number_of_years(self):
        self.assertGreaterEqual(DEFAULT_RETENTION_YEARS, 1)

    def test_a_zero_retention_period_is_refused(self):
        with self.assertRaises(ValueError):
            retention_end_day("2026-04-15", 0)


class UnitRecordTests(unittest.TestCase):
    def test_a_complete_record_closes(self):
        result = assess_unit_record(_record())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["state"], "record-complete")
        self.assertTrue(result["complete"])

    def test_the_retention_end_day_is_reported(self):
        self.assertEqual(assess_unit_record(_record())["retention_end_day"], (2036, 4, 15))

    def test_a_missing_field_leaves_the_record_incomplete(self):
        result = assess_unit_record(_record(operator_id=None))
        self.assertIn("record-field-missing:operator_id", result["findings"])
        self.assertEqual(result["state"], "record-incomplete")

    def test_an_unstated_cure_temperature_is_named(self):
        result = assess_unit_record(_record(parameters=_parameters(cure_temperature_c=None)))
        self.assertIn("application-parameter-missing:cure_temperature_c", result["findings"])

    def test_an_exceeded_pot_life_invalidates_the_record(self):
        result = assess_unit_record(_record(application_end_timestamp="2026-04-14T20:00"))
        self.assertIn("pot-life-exceeded", result["findings"])
        self.assertEqual(result["state"], "record-invalid")

    def test_a_lot_mixed_past_its_shelf_life_invalidates_the_record(self):
        result = assess_unit_record(_record(lots=[
            {"lot_id": "PR-5581", "manufacture_day": "2020-01-01", "shelf_months": 12},
            {"lot_id": "TC-9034", "manufacture_day": "2025-11-15", "shelf_months": 12},
        ]))
        self.assertIn("lot-past-shelf-life:PR-5581", result["findings"])
        self.assertEqual(result["state"], "record-invalid")

    def test_a_lot_outside_the_register_is_a_traceability_gap(self):
        result = assess_unit_record(_record(applied_lot_ids=["PR-5581", "TC-0000"]))
        self.assertIn("traceability-gap:TC-0000", result["findings"])
        self.assertEqual(result["state"], "record-invalid")

    def test_a_missing_mix_stamp_leaves_the_pot_life_unevaluated(self):
        result = assess_unit_record(_record(mix_timestamp=None))
        self.assertIn("pot-life-not-evaluated", result["findings"])

    def test_an_unrecognized_inspection_result_is_refused(self):
        with self.assertRaises(ValueError):
            assess_unit_record(_record(inspection_result="probably-fine"))

    def test_a_non_mapping_record_is_refused(self):
        with self.assertRaises(ValueError):
            assess_unit_record(["SN-012"])


class RecordSetTests(unittest.TestCase):
    def test_a_set_of_complete_records_closes(self):
        result = assess_record_set([_record(), _record(unit_id="SN-013")])
        self.assertTrue(result["set_closed"])
        self.assertEqual(result["invalid_records"], [])

    def test_one_invalid_record_keeps_the_set_open(self):
        result = assess_record_set([
            _record(),
            _record(unit_id="SN-013", applied_lot_ids=["PR-0001"]),
        ])
        self.assertFalse(result["set_closed"])
        self.assertEqual(result["invalid_records"], ["SN-013"])

    def test_duplicate_unit_ids_are_refused(self):
        with self.assertRaises(ValueError):
            assess_record_set([_record(), _record()])

    def test_an_empty_record_set_is_refused(self):
        with self.assertRaises(ValueError):
            assess_record_set([])


if __name__ == "__main__":
    unittest.main()
