"""Contract tests for the clause 6.3.5 Class 3 lot acceptance submission logic.

The cases follow a Class 3 delivery from the goods-in note to the submission
plan: the date codes that split it into populations, the manufacturer report
that may or may not discharge a population, the reduction a preferred source
earns, the exact rational sizing of every outstanding draw, and the spares the
delivery has left to give those draws up.
"""

import unittest

from q60_class_3_lot_acceptance_testing_logic import (
    DEFAULT_DRAW_FRACTION,
    DEFAULT_EVIDENCE_VALIDITY_MONTHS,
    DEFAULT_PRODUCTION_WINDOW_WEEKS,
    LARGE_DRAW_THRESHOLD,
    MAXIMUM_DRAW,
    MINIMUM_DRAW,
    REDUCED_QUANTITY_CEILING,
    ROUTES,
    acceptance_number,
    assess_lot_acceptance_submission,
    date_code_week_start,
    evidence_covers_unit,
    months_elapsed,
    parse_day,
    reduced_draw,
    share,
    submission_draw,
    submission_units,
    unit_route,
    week_distance,
)


def _line(**overrides):
    line = {
        "part_number": "RC0805-10K",
        "date_code": "2514",
        "quantity": 400,
        "build_demand": 120,
        "preferred_source": False,
    }
    line.update(overrides)
    return line


def _record(**overrides):
    record = {
        "part_number": "RC0805-10K",
        "date_code": "2514",
        "issued_day": "2025-05-01",
    }
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "delivery": [_line()],
        "as_of_day": "2025-09-01",
        "evidence": [_record()],
    }
    spec.update(overrides)
    return spec


class DateCodeTests(unittest.TestCase):
    def test_build_week_starts_on_a_monday(self):
        self.assertEqual(date_code_week_start("2514").weekday(), 0)

    def test_week_a_year_does_not_have_is_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2553")

    def test_week_zero_is_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2500")

    def test_non_digit_date_code_is_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("25W4")

    def test_partial_century_base_is_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2514", century_base=2010)

    def test_week_distance_is_unsigned_and_whole(self):
        self.assertEqual(week_distance("2514", "2501"), 13)
        self.assertEqual(week_distance("2501", "2514"), 13)

    def test_week_distance_spans_a_year_boundary(self):
        self.assertEqual(week_distance("2601", "2551"), 2)

    def test_parse_day_refuses_a_non_iso_day(self):
        with self.assertRaises(ValueError):
            parse_day("as_of_day", "01/09/2025")

    def test_months_elapsed_does_not_count_a_part_month(self):
        self.assertEqual(months_elapsed("2025-01-31", "2025-02-28"), 0)

    def test_months_elapsed_refuses_a_reversed_pair(self):
        with self.assertRaises(ValueError):
            months_elapsed("2025-09-01", "2025-05-01")


class SubmissionUnitTests(unittest.TestCase):
    def test_one_unit_per_part_number_and_date_code(self):
        units = submission_units(
            [_line(), _line(date_code="2520"), _line(part_number="CC0603-100N")]
        )
        self.assertEqual(len(units), 3)

    def test_lines_sharing_a_population_are_merged(self):
        units = submission_units(
            [_line(quantity=400), _line(quantity=100, build_demand=50)]
        )
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["quantity"], 500)

    def test_spare_is_the_quantity_left_after_the_build_demand(self):
        units = submission_units([_line(quantity=400, build_demand=120)])
        self.assertEqual(units[0]["spare"], 280)

    def test_preferred_source_needs_every_contributing_line(self):
        units = submission_units(
            [
                _line(preferred_source=True),
                _line(preferred_source=False, quantity=50, build_demand=0),
            ]
        )
        self.assertFalse(units[0]["preferred_source"])

    def test_build_demand_above_the_delivered_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            submission_units([_line(quantity=100, build_demand=101)])

    def test_zero_quantity_line_is_refused(self):
        with self.assertRaises(ValueError):
            submission_units([_line(quantity=0)])

    def test_empty_delivery_is_refused(self):
        with self.assertRaises(ValueError):
            submission_units([])

    def test_line_missing_a_required_key_is_refused(self):
        line = _line()
        del line["date_code"]
        with self.assertRaises(ValueError):
            submission_units([line])


class DrawSizingTests(unittest.TestCase):
    def test_share_refuses_a_non_integer_numerator(self):
        with self.assertRaises(ValueError):
            share(1.0, 20)

    def test_share_refuses_a_zero_denominator(self):
        with self.assertRaises(ValueError):
            share(1, 0)

    def test_full_draw_rounds_the_share_up(self):
        self.assertEqual(submission_draw(410, share(1, 20)), 21)

    def test_full_draw_is_raised_to_the_floor(self):
        self.assertEqual(submission_draw(40, DEFAULT_DRAW_FRACTION), MINIMUM_DRAW)

    def test_full_draw_is_held_under_the_cap(self):
        self.assertEqual(submission_draw(100000, DEFAULT_DRAW_FRACTION), MAXIMUM_DRAW)

    def test_full_draw_never_exceeds_the_unit(self):
        self.assertEqual(submission_draw(2, DEFAULT_DRAW_FRACTION), 2)

    def test_draw_share_outside_the_unit_interval_is_refused(self):
        with self.assertRaises(ValueError):
            submission_draw(400, share(3, 2))

    def test_zero_draw_share_is_refused(self):
        with self.assertRaises(ValueError):
            submission_draw(400, share(0, 1))

    def test_cap_below_the_floor_is_refused(self):
        with self.assertRaises(ValueError):
            submission_draw(400, DEFAULT_DRAW_FRACTION, minimum=10, maximum=4)

    def test_reduced_draw_halves_and_rounds_up(self):
        self.assertEqual(reduced_draw(21, share(1, 2), minimum=1), 11)

    def test_reduced_draw_is_raised_to_the_floor(self):
        self.assertEqual(reduced_draw(6, share(1, 2)), MINIMUM_DRAW)

    def test_reduced_draw_never_exceeds_the_full_draw(self):
        self.assertEqual(reduced_draw(3, share(1, 1), minimum=8), 3)

    def test_acceptance_number_is_zero_below_the_threshold(self):
        self.assertEqual(acceptance_number(LARGE_DRAW_THRESHOLD - 1), 0)

    def test_acceptance_number_is_one_at_the_threshold(self):
        self.assertEqual(acceptance_number(LARGE_DRAW_THRESHOLD), 1)

    def test_acceptance_number_refuses_an_empty_draw(self):
        with self.assertRaises(ValueError):
            acceptance_number(0)


class EvidenceCreditTests(unittest.TestCase):
    def setUp(self):
        self.unit = submission_units([_line()])[0]

    def test_a_matching_report_credits_the_unit(self):
        verdict = evidence_covers_unit(self.unit, _record(), "2025-09-01")
        self.assertTrue(verdict["credited"])
        self.assertEqual(verdict["reasons"], [])

    def test_a_report_for_another_part_is_refused_with_a_reason(self):
        verdict = evidence_covers_unit(
            self.unit, _record(part_number="CC0603-100N"), "2025-09-01"
        )
        self.assertFalse(verdict["credited"])
        self.assertEqual(len(verdict["reasons"]), 1)

    def test_a_report_at_the_window_edge_still_credits(self):
        verdict = evidence_covers_unit(self.unit, _record(date_code="2501"), "2025-09-01")
        self.assertEqual(verdict["week_distance"], DEFAULT_PRODUCTION_WINDOW_WEEKS)
        self.assertTrue(verdict["credited"])

    def test_a_report_one_week_outside_the_window_is_refused(self):
        verdict = evidence_covers_unit(self.unit, _record(date_code="2452"), "2025-09-01")
        self.assertFalse(verdict["credited"])

    def test_a_report_past_its_validity_is_refused(self):
        verdict = evidence_covers_unit(
            self.unit, _record(issued_day="2020-01-01"), "2025-09-01"
        )
        self.assertFalse(verdict["credited"])
        self.assertGreater(verdict["age_months"], DEFAULT_EVIDENCE_VALIDITY_MONTHS)

    def test_every_failed_test_is_named_not_just_the_first(self):
        verdict = evidence_covers_unit(
            self.unit,
            _record(part_number="OTHER", date_code="2352", issued_day="2019-01-01"),
            "2025-09-01",
        )
        self.assertEqual(len(verdict["reasons"]), 3)

    def test_a_record_missing_its_issue_day_is_refused(self):
        record = _record()
        del record["issued_day"]
        with self.assertRaises(ValueError):
            evidence_covers_unit(self.unit, record, "2025-09-01")


class UnitRouteTests(unittest.TestCase):
    def test_credit_takes_precedence_and_draws_nothing(self):
        unit = submission_units([_line(preferred_source=True)])[0]
        routed = unit_route(unit, [_record()], "2025-09-01")
        self.assertEqual(routed["route"], "manufacturer-data-credit")
        self.assertEqual(routed["draw"], 0)

    def test_a_preferred_source_unit_under_the_ceiling_is_reduced(self):
        unit = submission_units([_line(quantity=200, preferred_source=True)])[0]
        routed = unit_route(unit, [], "2025-09-01")
        self.assertEqual(routed["route"], "reduced-submission")
        self.assertLess(routed["draw"], routed["full_draw"])

    def test_a_preferred_source_unit_over_the_ceiling_draws_in_full(self):
        unit = submission_units(
            [_line(quantity=REDUCED_QUANTITY_CEILING + 1, preferred_source=True)]
        )[0]
        routed = unit_route(unit, [], "2025-09-01")
        self.assertEqual(routed["route"], "full-submission")
        self.assertEqual(routed["draw"], routed["full_draw"])

    def test_an_uncredited_ordinary_unit_draws_in_full(self):
        unit = submission_units([_line()])[0]
        routed = unit_route(unit, [_record(part_number="OTHER")], "2025-09-01")
        self.assertEqual(routed["route"], "full-submission")

    def test_every_route_is_one_of_the_declared_routes(self):
        unit = submission_units([_line()])[0]
        routed = unit_route(unit, [], "2025-09-01")
        self.assertIn(routed["route"], ROUTES)

    def test_a_unit_without_spares_for_its_draw_is_infeasible(self):
        unit = submission_units([_line(quantity=400, build_demand=398)])[0]
        routed = unit_route(unit, [], "2025-09-01")
        self.assertFalse(routed["feasible"])
        self.assertEqual(len(routed["findings"]), 1)

    def test_records_must_be_a_sequence(self):
        unit = submission_units([_line()])[0]
        with self.assertRaises(ValueError):
            unit_route(unit, _record(), "2025-09-01")


class PlanTests(unittest.TestCase):
    def test_a_fully_credited_delivery_draws_nothing(self):
        result = assess_lot_acceptance_submission(_spec())
        self.assertEqual(result["total_draw"], 0)
        self.assertEqual(result["outstanding_units"], 0)

    def test_an_uncredited_delivery_raises_the_no_credit_finding(self):
        result = assess_lot_acceptance_submission(_spec(evidence=[]))
        self.assertEqual(result["credited_units"], 0)
        self.assertTrue(any("no manufacturer" in f for f in result["findings"]))

    def test_date_codes_are_planned_separately(self):
        result = assess_lot_acceptance_submission(
            _spec(delivery=[_line(), _line(date_code="2540")], evidence=[_record()])
        )
        self.assertEqual(result["unit_count"], 2)
        self.assertEqual(result["credited_units"], 1)
        self.assertEqual(result["outstanding_units"], 1)

    def test_total_draw_sums_only_the_outstanding_units(self):
        result = assess_lot_acceptance_submission(
            _spec(delivery=[_line(), _line(date_code="2540")], evidence=[_record()])
        )
        outstanding = [u for u in result["units"] if u["draw"]]
        self.assertEqual(result["total_draw"], sum(u["draw"] for u in outstanding))

    def test_an_infeasible_unit_makes_the_plan_incomplete(self):
        result = assess_lot_acceptance_submission(
            _spec(delivery=[_line(quantity=400, build_demand=399)], evidence=[])
        )
        self.assertFalse(result["plan_complete"])

    def test_spec_missing_a_required_key_is_refused(self):
        spec = _spec()
        del spec["as_of_day"]
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_submission(["delivery"])


if __name__ == "__main__":
    unittest.main()
