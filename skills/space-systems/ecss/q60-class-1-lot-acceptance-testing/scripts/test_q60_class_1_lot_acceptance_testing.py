"""Contract tests for the clause 4.3.5 Class 1 lot acceptance submission logic.

The cases walk the workflow one step at a time: date-code normalisation, the
split of a delivery into submission units, the exact rounding of the draw, the
coverage test an existing record has to pass, and the plan that names every
unit still owing a submission. Each step is exercised on both sides of its
limit so the record shows what was judged, not only the verdict.
"""

import unittest

from q60_class_1_lot_acceptance_testing_logic import (
    DEFAULT_MINIMUM_SAMPLE,
    DEFAULT_VALIDITY_MONTHS,
    assess_lot_acceptance_submission,
    group_delivery,
    months_elapsed,
    normalize_date_code,
    parse_day,
    record_covers_unit,
    submission_sample_size,
)


def _unit(part="RHFL4913", code="2514", lot_id="L-88", quantity=400):
    return {
        "part_number": part,
        "date_code": code,
        "lot_id": lot_id,
        "quantity": quantity,
    }


def _record(part="RHFL4913", code="2514", day="2025-06-02", **extra):
    record = {"part_number": part, "date_code": code, "day": day}
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "units": [_unit()],
        "submission_day": "2025-09-01",
        "sample_percent": 2,
        "records": [],
    }
    spec.update(overrides)
    return spec


class DateCodeTests(unittest.TestCase):
    def test_canonical_code_returned(self):
        self.assertEqual(normalize_date_code("2514"), "2514")

    def test_surrounding_space_stripped(self):
        self.assertEqual(normalize_date_code("  2514 "), "2514")

    def test_week_fifty_three_admissible(self):
        self.assertEqual(normalize_date_code("2453"), "2453")

    def test_week_zero_refused(self):
        with self.assertRaises(ValueError):
            normalize_date_code("2500")

    def test_week_above_fifty_three_refused(self):
        with self.assertRaises(ValueError):
            normalize_date_code("2554")

    def test_non_digit_code_refused(self):
        with self.assertRaises(ValueError):
            normalize_date_code("25W4")

    def test_short_code_refused(self):
        with self.assertRaises(ValueError):
            normalize_date_code("251")

    def test_non_string_code_refused(self):
        with self.assertRaises(ValueError):
            normalize_date_code(2514)


class DayArithmeticTests(unittest.TestCase):
    def test_iso_day_parsed(self):
        self.assertEqual(parse_day("day", "2025-09-01").month, 9)

    def test_malformed_day_refused(self):
        with self.assertRaises(ValueError):
            parse_day("day", "01-09-2025")

    def test_whole_months_counted(self):
        self.assertEqual(months_elapsed("2024-09-01", "2025-09-01"), 12)

    def test_incomplete_month_not_counted(self):
        self.assertEqual(months_elapsed("2024-09-15", "2025-09-14"), 11)

    def test_reversed_days_refused(self):
        with self.assertRaises(ValueError):
            months_elapsed("2025-09-02", "2025-09-01")


class DeliveryGroupingTests(unittest.TestCase):
    def test_single_unit_kept_whole(self):
        grouped = group_delivery([_unit(quantity=400)])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["quantity"], 400)

    def test_two_date_codes_are_two_units(self):
        grouped = group_delivery([_unit(code="2514"), _unit(code="2520")])
        self.assertEqual(len(grouped), 2)
        self.assertEqual(
            sorted(entry["date_code"] for entry in grouped), ["2514", "2520"]
        )

    def test_same_triple_quantities_add(self):
        grouped = group_delivery([_unit(quantity=120), _unit(quantity=80)])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["quantity"], 200)

    def test_same_date_code_different_lot_stays_split(self):
        grouped = group_delivery([_unit(lot_id="L-88"), _unit(lot_id="L-90")])
        self.assertEqual(len(grouped), 2)

    def test_missing_lot_id_is_admissible(self):
        grouped = group_delivery([{"part_number": "RHFL4913", "date_code": "2514", "quantity": 9}])
        self.assertEqual(grouped[0]["lot_id"], "")

    def test_zero_quantity_refused(self):
        with self.assertRaises(ValueError):
            group_delivery([_unit(quantity=0)])

    def test_empty_delivery_refused(self):
        with self.assertRaises(ValueError):
            group_delivery([])

    def test_non_mapping_delivery_record_refused(self):
        with self.assertRaises(ValueError):
            group_delivery(["RHFL4913"])


class SampleSizeTests(unittest.TestCase):
    def test_percentage_rounds_up(self):
        self.assertEqual(submission_sample_size(401, 2, minimum_sample=1), 9)

    def test_exact_percentage_does_not_round_up(self):
        self.assertEqual(submission_sample_size(30, 10.0, minimum_sample=1), 3)

    def test_float_percentage_uses_decimal_text(self):
        self.assertEqual(submission_sample_size(100, 2.9, minimum_sample=1), 3)

    def test_declared_floor_raises_a_small_draw(self):
        self.assertEqual(submission_sample_size(50, 2, minimum_sample=5), 5)

    def test_draw_never_exceeds_the_unit(self):
        self.assertEqual(submission_sample_size(3, 100, minimum_sample=5), 3)

    def test_default_floor_is_small_and_positive(self):
        self.assertGreaterEqual(DEFAULT_MINIMUM_SAMPLE, 1)

    def test_negative_percent_refused(self):
        with self.assertRaises(ValueError):
            submission_sample_size(100, -1)

    def test_percent_above_hundred_refused(self):
        with self.assertRaises(ValueError):
            submission_sample_size(100, 101)

    def test_zero_quantity_refused(self):
        with self.assertRaises(ValueError):
            submission_sample_size(0, 2)


class RecordCoverageTests(unittest.TestCase):
    def test_matching_record_covers_the_unit(self):
        covered, reason = record_covers_unit(_record(), _unit(), "2025-09-01", 24)
        self.assertTrue(covered)
        self.assertIn("covers the unit", reason)

    def test_neighbouring_date_code_does_not_cover(self):
        covered, reason = record_covers_unit(_record(code="2515"), _unit(), "2025-09-01", 24)
        self.assertFalse(covered)
        self.assertIn("date code", reason)

    def test_other_part_number_does_not_cover(self):
        covered, _ = record_covers_unit(_record(part="RHFL4911"), _unit(), "2025-09-01", 24)
        self.assertFalse(covered)

    def test_other_lot_identifier_does_not_cover(self):
        covered, _ = record_covers_unit(
            _record(lot_id="L-90"), _unit(lot_id="L-88"), "2025-09-01", 24
        )
        self.assertFalse(covered)

    def test_record_later_than_submission_day_refused(self):
        covered, reason = record_covers_unit(
            _record(day="2025-09-02"), _unit(), "2025-09-01", 24
        )
        self.assertFalse(covered)
        self.assertIn("later", reason)

    def test_record_outside_validity_window_refused(self):
        covered, reason = record_covers_unit(
            _record(day="2022-01-10"), _unit(), "2025-09-01", 24
        )
        self.assertFalse(covered)
        self.assertIn("months old", reason)

    def test_record_exactly_at_the_window_still_covers(self):
        covered, _ = record_covers_unit(
            _record(day="2023-09-01"), _unit(), "2025-09-01", 24
        )
        self.assertTrue(covered)

    def test_zero_validity_window_refused(self):
        with self.assertRaises(ValueError):
            record_covers_unit(_record(), _unit(), "2025-09-01", 0)

    def test_default_window_is_whole_months(self):
        self.assertIsInstance(DEFAULT_VALIDITY_MONTHS, int)


class SubmissionPlanTests(unittest.TestCase):
    def test_uncovered_unit_owes_a_submission(self):
        result = assess_lot_acceptance_submission(_spec())
        self.assertFalse(result["complete"])
        self.assertEqual(result["disposition"], "submit-outstanding-units")
        self.assertEqual(result["outstanding"], ["2514"])

    def test_covered_unit_closes_the_plan(self):
        result = assess_lot_acceptance_submission(
            _spec(records=[_record(lot_id="L-88", reference="LAT-2025-014")])
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["disposition"], "all-units-covered")
        self.assertEqual(result["units"][0]["covered_by"], "LAT-2025-014")

    def test_second_date_code_kept_outstanding(self):
        result = assess_lot_acceptance_submission(
            _spec(
                units=[_unit(code="2514"), _unit(code="2520", lot_id="L-90")],
                records=[_record(code="2514", lot_id="L-88")],
            )
        )
        self.assertEqual(result["outstanding"], ["2520"])
        self.assertFalse(result["complete"])

    def test_outstanding_pieces_sum_the_draws(self):
        result = assess_lot_acceptance_submission(_spec(sample_percent=2, units=[_unit(quantity=400)]))
        self.assertEqual(result["outstanding_pieces"], result["units"][0]["sample_size"])

    def test_multi_unit_delivery_is_reported_as_such(self):
        result = assess_lot_acceptance_submission(
            _spec(units=[_unit(code="2514"), _unit(code="2520")])
        )
        self.assertTrue(any("submission units" in item for item in result["findings"]))

    def test_expired_record_leaves_the_unit_outstanding(self):
        result = assess_lot_acceptance_submission(
            _spec(records=[_record(day="2021-01-04", lot_id="L-88")])
        )
        self.assertFalse(result["complete"])
        self.assertIn("months old", result["units"][0]["reason"])

    def test_missing_units_key_refused(self):
        spec = _spec()
        del spec["units"]
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(["units"])

    def test_records_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(_spec(records="LAT-2025-014"))

    def test_units_are_grouped_not_pooled(self):
        result = assess_lot_acceptance_submission(
            _spec(units=[_unit(code="2514", quantity=100), _unit(code="2520", quantity=100)])
        )
        self.assertEqual(len(result["units"]), 2)
        self.assertEqual([entry["quantity"] for entry in result["units"]], [100, 100])


if __name__ == "__main__":
    unittest.main()
