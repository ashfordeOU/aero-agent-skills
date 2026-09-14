"""Contract tests for the clause 4.5.3 manufacturer alert handling logic."""

import unittest

from q6013_class_1_alert_handling_logic import (
    ALERT_CATEGORIES,
    HOLDING_ACTIONS,
    assess_alert,
    assess_response,
    date_code_in_range,
    date_code_ordinal,
    parse_date_code,
    required_action,
    response_deadlines,
    screen_holding,
    working_days_between,
)


def base_alert(**overrides):
    """Return an errata alert received on a Monday, not yet dispositioned."""
    alert = {
        "alert_id": "ALT-2026-041",
        "category": "errata",
        "affected_part_numbers": ["XC7A35T-1CPG236C"],
        "first_affected_date_code": "2310",
        "last_affected_date_code": "2402",
        "received_date": "2026-09-07",
        "acknowledged_date": "2026-09-09",
        "disposition_date": "2026-09-18",
    }
    alert.update(overrides)
    return alert


def holding(**overrides):
    record = {
        "lot_id": "LOT-A",
        "part_number": "XC7A35T-1CPG236C",
        "quantity": 20,
        "state": "stores",
        "date_code": "2336",
    }
    record.update(overrides)
    return record


class ParseDateCodeTests(unittest.TestCase):
    def test_parses_year_and_week(self):
        self.assertEqual(parse_date_code("2336"), {"year": 2023, "week": 36})

    def test_week_one_accepted(self):
        self.assertEqual(parse_date_code("2401")["week"], 1)

    def test_week_fifty_three_accepted(self):
        self.assertEqual(parse_date_code("2053")["week"], 53)

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2300")

    def test_week_fifty_four_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2354")

    def test_short_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("233")

    def test_non_digit_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("23W6")

    def test_non_string_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code(2336)


class DateCodeRangeTests(unittest.TestCase):
    def test_ordinal_increases_with_the_week(self):
        self.assertLess(date_code_ordinal("2310"), date_code_ordinal("2311"))

    def test_ordinal_crosses_the_year_boundary_correctly(self):
        self.assertLess(date_code_ordinal("2353"), date_code_ordinal("2401"))

    def test_code_inside_the_range(self):
        self.assertTrue(date_code_in_range("2336", "2310", "2402"))

    def test_lower_bound_is_inclusive(self):
        self.assertTrue(date_code_in_range("2310", "2310", "2402"))

    def test_upper_bound_is_inclusive(self):
        self.assertTrue(date_code_in_range("2402", "2310", "2402"))

    def test_code_below_the_range(self):
        self.assertFalse(date_code_in_range("2309", "2310", "2402"))

    def test_code_above_the_range(self):
        self.assertFalse(date_code_in_range("2403", "2310", "2402"))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            date_code_in_range("2336", "2402", "2310")


class WorkingDayTests(unittest.TestCase):
    def test_same_day_is_zero(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-07"), 0)

    def test_monday_to_friday_is_four(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-11"), 4)

    def test_weekend_is_not_counted(self):
        self.assertEqual(working_days_between("2026-09-11", "2026-09-14"), 1)

    def test_a_full_week_is_five(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-14"), 5)

    def test_backwards_range_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-14", "2026-09-07")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("07/09/2026", "2026-09-14")


class CategoryTests(unittest.TestCase):
    def test_safety_advisory_has_the_shortest_acknowledgement(self):
        ack, _ = response_deadlines("safety-advisory")
        self.assertEqual(ack, min(days[0] for days in ALERT_CATEGORIES.values()))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            response_deadlines("rumour")

    def test_every_action_state_is_mapped(self):
        for state in HOLDING_ACTIONS:
            self.assertTrue(required_action(state))

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            required_action("in-transit")

    def test_delivered_state_earns_an_in_service_assessment(self):
        self.assertEqual(required_action("delivered"), "in-service-assessment")


class ScreenHoldingTests(unittest.TestCase):
    def test_matching_part_and_date_code_is_affected(self):
        verdict = screen_holding(base_alert(), holding())
        self.assertEqual(verdict["verdict"], "affected")

    def test_other_part_number_is_not_affected(self):
        verdict = screen_holding(base_alert(), holding(part_number="LM117H"))
        self.assertEqual(verdict["verdict"], "not-affected")

    def test_part_number_match_is_case_insensitive(self):
        verdict = screen_holding(base_alert(), holding(part_number="xc7a35t-1cpg236c"))
        self.assertEqual(verdict["verdict"], "affected")

    def test_date_code_outside_the_range_is_not_affected(self):
        verdict = screen_holding(base_alert(), holding(date_code="2409"))
        self.assertEqual(verdict["verdict"], "not-affected")

    def test_missing_date_code_is_unscreenable_not_clear(self):
        verdict = screen_holding(base_alert(), holding(date_code=None))
        self.assertEqual(verdict["verdict"], "unscreenable")

    def test_blank_date_code_is_unscreenable(self):
        verdict = screen_holding(base_alert(), holding(date_code="   "))
        self.assertEqual(verdict["verdict"], "unscreenable")

    def test_unreadable_date_code_is_unscreenable(self):
        verdict = screen_holding(base_alert(), holding(date_code="23W6"))
        self.assertEqual(verdict["verdict"], "unscreenable")

    def test_non_mapping_alert_rejected(self):
        with self.assertRaises(ValueError):
            screen_holding("ALT-2026-041", holding())

    def test_zero_quantity_holding_rejected(self):
        with self.assertRaises(ValueError):
            screen_holding(base_alert(), holding(quantity=0))

    def test_unknown_holding_state_rejected(self):
        with self.assertRaises(ValueError):
            screen_holding(base_alert(), holding(state="in-transit"))


class ResponseTimingTests(unittest.TestCase):
    def test_acknowledgement_exactly_on_the_deadline_is_within(self):
        result = assess_response(
            "errata", "2026-09-07", "2026-09-14", "2026-09-18", "2026-09-20"
        )
        self.assertEqual(result["acknowledgement_working_days"], 5)
        self.assertTrue(result["acknowledgement_within_deadline"])

    def test_late_acknowledgement_is_flagged(self):
        result = assess_response(
            "safety-advisory", "2026-09-07", "2026-09-14", None, "2026-09-20"
        )
        self.assertFalse(result["acknowledgement_within_deadline"])

    def test_open_disposition_counts_up_to_today(self):
        result = assess_response(
            "errata", "2026-09-07", "2026-09-08", None, "2026-09-21"
        )
        self.assertEqual(result["disposition_state"], "open")
        self.assertEqual(result["disposition_working_days"], 10)

    def test_as_of_before_receipt_rejected(self):
        with self.assertRaises(ValueError):
            assess_response("errata", "2026-09-07", None, None, "2026-09-01")


class AssessAlertTests(unittest.TestCase):
    def test_affected_stock_is_quarantined(self):
        result = assess_alert(base_alert(), [holding()], "2026-09-21")
        self.assertEqual(result["affected_quantity"], 20)
        self.assertIn("quarantine-stock", result["actions"])
        self.assertTrue(result["closeable"])

    def test_delivered_lot_raises_an_in_service_finding(self):
        result = assess_alert(
            base_alert(), [holding(state="delivered")], "2026-09-21"
        )
        self.assertTrue(any("in-service" in f for f in result["findings"]))

    def test_unscreenable_lot_blocks_closure(self):
        result = assess_alert(
            base_alert(),
            [holding(), holding(lot_id="LOT-B", date_code=None, quantity=7)],
            "2026-09-21",
        )
        self.assertEqual(result["unscreenable_quantity"], 7)
        self.assertFalse(result["closeable"])

    def test_untouched_lots_are_reported_separately(self):
        result = assess_alert(
            base_alert(), [holding(lot_id="LOT-C", date_code="2409")], "2026-09-21"
        )
        self.assertEqual(len(result["not_affected"]), 1)
        self.assertEqual(result["affected_quantity"], 0)

    def test_open_disposition_past_deadline_blocks_closure(self):
        result = assess_alert(
            base_alert(disposition_date=None), [holding()], "2026-11-30"
        )
        self.assertFalse(result["closeable"])
        self.assertTrue(any("no disposition" in f for f in result["findings"]))

    def test_missing_alert_key_rejected(self):
        alert = base_alert()
        del alert["category"]
        with self.assertRaises(ValueError):
            assess_alert(alert, [holding()], "2026-09-21")

    def test_inverted_alert_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert(
                base_alert(first_affected_date_code="2402",
                           last_affected_date_code="2310"),
                [holding()],
                "2026-09-21",
            )

    def test_empty_part_number_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert(base_alert(affected_part_numbers=[]), [holding()], "2026-09-21")

    def test_holdings_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_alert(base_alert(), holding(), "2026-09-21")


if __name__ == "__main__":
    unittest.main()
