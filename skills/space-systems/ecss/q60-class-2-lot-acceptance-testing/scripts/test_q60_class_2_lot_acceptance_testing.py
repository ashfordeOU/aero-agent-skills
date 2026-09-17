"""Contract tests for the clause 5.3.5 Class 2 lot acceptance submission logic.

The cases walk the workflow one step at a time: date-code normalisation, the
split of a delivery into submission units, the exact per-group draw, the
coverage test an acceptance record has to pass for the group it is offered
against, the Class 2 family-evidence relaxation, and the plan that names every
group still owing a submission. Each step is exercised on both sides of its
limit so the record shows what was judged, not only the verdict.
"""

import unittest

from q60_class_2_lot_acceptance_testing_logic import (
    DEFAULT_GROUP_DRAW,
    DEFAULT_GROUP_VALIDITY_MONTHS,
    FAMILY_CREDITABLE_GROUPS,
    TEST_GROUPS,
    assess_lot_acceptance_submission,
    evidence_covers_group,
    group_draw,
    months_elapsed,
    normalize_date_code,
    parse_day,
    submission_units,
    unit_route,
)

DAY = "2025-09-01"


def _line(part="RHFX2010", code="2514", lot_id="L-12", quantity=400, family="bipolar-linear"):
    return {
        "part_number": part,
        "date_code": code,
        "lot_id": lot_id,
        "quantity": quantity,
        "family": family,
    }


def _unit(**overrides):
    unit = {
        "part_number": "RHFX2010",
        "date_code": "2514",
        "lot_id": "L-12",
        "family": "bipolar-linear",
        "quantity": 400,
    }
    unit.update(overrides)
    return unit


def _record(groups=("electrical-endpoint",), day="2025-06-02", **extra):
    record = {
        "part_number": "RHFX2010",
        "date_code": "2514",
        "lot_id": "L-12",
        "day": day,
        "groups": list(groups),
    }
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "lines": [_line()],
        "submission_day": DAY,
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

    def test_non_string_code_refused(self):
        with self.assertRaises(ValueError):
            normalize_date_code(2514)


class DayArithmeticTests(unittest.TestCase):
    def test_iso_day_parsed(self):
        self.assertEqual(parse_day("day", DAY).month, 9)

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


class SubmissionUnitTests(unittest.TestCase):
    def test_single_line_kept_whole(self):
        units = submission_units([_line(quantity=400)])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["quantity"], 400)

    def test_two_date_codes_are_two_units(self):
        units = submission_units([_line(code="2514"), _line(code="2520", lot_id="L-13")])
        self.assertEqual(len(units), 2)

    def test_same_triple_quantities_add(self):
        units = submission_units([_line(quantity=120), _line(quantity=80)])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["quantity"], 200)

    def test_same_date_code_different_lot_stays_split(self):
        units = submission_units([_line(lot_id="L-12"), _line(lot_id="L-14")])
        self.assertEqual(len(units), 2)

    def test_family_travels_with_the_unit(self):
        units = submission_units([_line(family="bipolar-linear")])
        self.assertEqual(units[0]["family"], "bipolar-linear")

    def test_missing_lot_id_is_admissible(self):
        units = submission_units(
            [{"part_number": "RHFX2010", "date_code": "2514", "quantity": 9}]
        )
        self.assertEqual(units[0]["lot_id"], "")

    def test_conflicting_family_for_one_lot_refused(self):
        with self.assertRaises(ValueError):
            submission_units([_line(family="bipolar-linear"), _line(family="cmos-soi")])

    def test_zero_quantity_refused(self):
        with self.assertRaises(ValueError):
            submission_units([_line(quantity=0)])

    def test_empty_delivery_refused(self):
        with self.assertRaises(ValueError):
            submission_units([])

    def test_non_mapping_line_refused(self):
        with self.assertRaises(ValueError):
            submission_units(["RHFX2010"])


class GroupDrawTests(unittest.TestCase):
    def test_exact_percentage_does_not_round_up(self):
        self.assertEqual(group_draw(400, "electrical-endpoint"), 8)

    def test_percentage_rounds_up(self):
        self.assertEqual(group_draw(401, "electrical-endpoint"), 9)

    def test_group_floor_raises_a_small_draw(self):
        self.assertEqual(group_draw(100, "endurance"), 2)

    def test_draw_never_exceeds_the_unit(self):
        self.assertEqual(group_draw(1, "electrical-endpoint"), 1)

    def test_environmental_group_draws_its_own_rate(self):
        self.assertEqual(group_draw(300, "environmental"), 3)

    def test_float_percentage_uses_decimal_text(self):
        table = dict(DEFAULT_GROUP_DRAW)
        table["environmental"] = (2.9, 1)
        self.assertEqual(group_draw(100, "environmental", table), 3)

    def test_unknown_group_refused(self):
        with self.assertRaises(ValueError):
            group_draw(400, "radiation")

    def test_zero_quantity_refused(self):
        with self.assertRaises(ValueError):
            group_draw(0, "endurance")

    def test_malformed_draw_entry_refused(self):
        with self.assertRaises(ValueError):
            group_draw(400, "endurance", {"endurance": 5})

    def test_percent_above_hundred_refused(self):
        with self.assertRaises(ValueError):
            group_draw(400, "endurance", {"endurance": (101, 2)})


class EvidenceCoverageTests(unittest.TestCase):
    def test_lot_record_closes_the_endpoint_group(self):
        covered, reason = evidence_covers_group(_record(), _unit(), "electrical-endpoint", DAY)
        self.assertTrue(covered)
        self.assertIn("closes the electrical-endpoint group", reason)

    def test_record_without_the_group_does_not_close_it(self):
        covered, reason = evidence_covers_group(_record(), _unit(), "endurance", DAY)
        self.assertFalse(covered)
        self.assertIn("does not carry", reason)

    def test_family_evidence_closes_the_endurance_group(self):
        record = _record(
            groups=("endurance",), scope="family", family="bipolar-linear", lot_id="L-99", date_code="2402"
        )
        covered, reason = evidence_covers_group(record, _unit(), "endurance", DAY)
        self.assertTrue(covered)
        self.assertIn("family evidence", reason)

    def test_family_evidence_cannot_close_the_endpoint_group(self):
        record = _record(scope="family", family="bipolar-linear")
        covered, reason = evidence_covers_group(record, _unit(), "electrical-endpoint", DAY)
        self.assertFalse(covered)
        self.assertIn("cannot discharge", reason)

    def test_other_family_does_not_close_the_endurance_group(self):
        record = _record(groups=("endurance",), scope="family", family="cmos-soi")
        covered, reason = evidence_covers_group(record, _unit(), "endurance", DAY)
        self.assertFalse(covered)
        self.assertIn("covers family", reason)

    def test_neighbouring_date_code_does_not_close_a_lot_group(self):
        covered, reason = evidence_covers_group(
            _record(date_code="2515"), _unit(), "electrical-endpoint", DAY
        )
        self.assertFalse(covered)
        self.assertIn("date code", reason)

    def test_other_part_number_does_not_close_a_lot_group(self):
        covered, _ = evidence_covers_group(
            _record(part_number="RHFX2011"), _unit(), "electrical-endpoint", DAY
        )
        self.assertFalse(covered)

    def test_other_lot_identifier_does_not_close_a_lot_group(self):
        covered, _ = evidence_covers_group(
            _record(lot_id="L-14"), _unit(), "electrical-endpoint", DAY
        )
        self.assertFalse(covered)

    def test_record_later_than_submission_day_refused(self):
        covered, reason = evidence_covers_group(
            _record(day="2025-09-02"), _unit(), "electrical-endpoint", DAY
        )
        self.assertFalse(covered)
        self.assertIn("later than", reason)

    def test_record_outside_its_window_refused(self):
        covered, reason = evidence_covers_group(
            _record(day="2022-01-10"), _unit(), "electrical-endpoint", DAY
        )
        self.assertFalse(covered)
        self.assertIn("months old", reason)

    def test_endurance_window_is_longer_than_the_endpoint_window(self):
        record = _record(groups=("endurance",), day="2022-09-01")
        covered, _ = evidence_covers_group(record, _unit(), "endurance", DAY)
        self.assertTrue(covered)
        stale = _record(day="2022-09-01")
        covered_endpoint, _ = evidence_covers_group(stale, _unit(), "electrical-endpoint", DAY)
        self.assertFalse(covered_endpoint)

    def test_unknown_record_scope_refused(self):
        with self.assertRaises(ValueError):
            evidence_covers_group(_record(scope="wafer"), _unit(), "electrical-endpoint", DAY)

    def test_record_groups_must_be_a_sequence(self):
        record = _record()
        record["groups"] = "electrical-endpoint"
        with self.assertRaises(ValueError):
            evidence_covers_group(record, _unit(), "electrical-endpoint", DAY)

    def test_missing_record_key_refused(self):
        record = _record()
        del record["day"]
        with self.assertRaises(ValueError):
            evidence_covers_group(record, _unit(), "electrical-endpoint", DAY)


class RouteTests(unittest.TestCase):
    def test_no_open_group_is_evidence_accepted(self):
        self.assertEqual(unit_route([], TEST_GROUPS), "evidence-accepted")

    def test_every_group_open_is_a_full_submission(self):
        self.assertEqual(unit_route(TEST_GROUPS, TEST_GROUPS), "full-submission")

    def test_some_group_open_is_a_partial_submission(self):
        self.assertEqual(unit_route(["endurance"], TEST_GROUPS), "partial-submission")

    def test_open_group_outside_the_required_set_refused(self):
        with self.assertRaises(ValueError):
            unit_route(["endurance"], ["electrical-endpoint"])

    def test_empty_required_set_refused(self):
        with self.assertRaises(ValueError):
            unit_route([], [])


class SubmissionPlanTests(unittest.TestCase):
    def test_delivery_without_records_owes_every_group(self):
        result = assess_lot_acceptance_submission(_spec())
        self.assertFalse(result["complete"])
        self.assertEqual(result["units"][0]["route"], "full-submission")
        self.assertEqual(result["disposition"], "submit-outstanding-groups")

    def test_outstanding_pieces_sum_the_group_draws(self):
        result = assess_lot_acceptance_submission(_spec())
        self.assertEqual(result["outstanding_pieces"], 8 + 4 + 2)

    def test_endpoint_record_leaves_a_partial_submission(self):
        result = assess_lot_acceptance_submission(
            _spec(records=[_record(reference="LAT-2025-007")])
        )
        unit = result["units"][0]
        self.assertEqual(unit["route"], "partial-submission")
        self.assertEqual(unit["open_groups"], ["environmental", "endurance"])
        self.assertEqual(unit["groups"]["electrical-endpoint"]["covered_by"], "LAT-2025-007")
        self.assertEqual(unit["groups"]["electrical-endpoint"]["draw"], 0)

    def test_every_group_covered_closes_the_plan(self):
        records = [
            _record(groups=("electrical-endpoint", "environmental")),
            _record(groups=("endurance",), scope="family", family="bipolar-linear", date_code="2402"),
        ]
        result = assess_lot_acceptance_submission(_spec(records=records))
        self.assertTrue(result["complete"])
        self.assertEqual(result["disposition"], "all-units-covered")
        self.assertEqual(result["units"][0]["route"], "evidence-accepted")
        self.assertEqual(result["outstanding_pieces"], 0)

    def test_second_date_code_kept_outstanding(self):
        result = assess_lot_acceptance_submission(
            _spec(
                lines=[_line(code="2514"), _line(code="2520", lot_id="L-13")],
                records=[_record(groups=TEST_GROUPS)],
            )
        )
        self.assertEqual(result["outstanding"], ["2520"])
        self.assertFalse(result["complete"])

    def test_multi_unit_delivery_is_reported_as_such(self):
        result = assess_lot_acceptance_submission(
            _spec(lines=[_line(code="2514"), _line(code="2520", lot_id="L-13")])
        )
        self.assertTrue(any("submission units" in item for item in result["findings"]))

    def test_expired_record_leaves_the_group_open(self):
        result = assess_lot_acceptance_submission(
            _spec(records=[_record(day="2021-01-04")])
        )
        reason = result["units"][0]["groups"]["electrical-endpoint"]["reason"]
        self.assertIn("months old", reason)

    def test_required_groups_may_be_narrowed(self):
        result = assess_lot_acceptance_submission(
            _spec(required_groups=["electrical-endpoint"], records=[_record()])
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["required_groups"], ["electrical-endpoint"])

    def test_missing_lines_key_refused(self):
        spec = _spec()
        del spec["lines"]
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(["lines"])

    def test_records_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(_spec(records="LAT-2025-007"))

    def test_empty_required_groups_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(_spec(required_groups=[]))


class TableTests(unittest.TestCase):
    def test_every_group_has_a_draw_rule(self):
        self.assertEqual(set(DEFAULT_GROUP_DRAW), set(TEST_GROUPS))

    def test_every_group_has_a_validity_window(self):
        self.assertEqual(set(DEFAULT_GROUP_VALIDITY_MONTHS), set(TEST_GROUPS))

    def test_family_credit_is_the_narrow_exception(self):
        self.assertTrue(set(FAMILY_CREDITABLE_GROUPS) < set(TEST_GROUPS))


if __name__ == "__main__":
    unittest.main()
