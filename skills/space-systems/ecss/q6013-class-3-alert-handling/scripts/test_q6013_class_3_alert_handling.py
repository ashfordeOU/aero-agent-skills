"""Contract tests for the clause 6.5.3 class 3 alert watch and response logic."""

import unittest

from q6013_class_3_alert_handling_logic import (
    ALERT_CATEGORIES,
    ALERT_SOURCES,
    COVERAGE_TOLERANCE,
    HOLDING_RESPONSES,
    SOURCE_COVERAGE_FLOOR,
    TRACEABILITY_GRADES,
    WATCH_REVIEW_INTERVAL_DAYS,
    assess_alert,
    assess_alert_response,
    assess_alert_watch,
    corrective_response,
    date_code_in_range,
    date_code_ordinal,
    parse_date_code,
    response_deadlines,
    screen_holding,
    screening_resolution,
    working_days_between,
)


def base_alert(**overrides):
    """Return an errata alert received on a Monday and fully responded to."""
    alert = {
        "alert_id": "ALT-2026-077",
        "category": "errata",
        "source": "manufacturer-pcn-service",
        "affected_part_numbers": ["LM2596S-ADJ"],
        "first_affected_date_code": "2310",
        "last_affected_date_code": "2402",
        "received_date": "2026-09-07",
        "acknowledged_date": "2026-09-09",
        "corrective_action_date": "2026-09-18",
    }
    alert.update(overrides)
    return alert


def holding(**overrides):
    record = {
        "lot_id": "LOT-A",
        "part_number": "LM2596S-ADJ",
        "quantity": 25,
        "state": "stores",
        "traceability_grade": "lot-traced",
        "date_code": "2336",
        "criticality": 4,
    }
    record.update(overrides)
    return record


def base_watch(**overrides):
    watch = {
        "subscribed_sources": [
            "manufacturer-pcn-service",
            "agency-alert-system",
            "distributor-notice-feed",
        ],
        "last_review_date": "2026-09-01",
    }
    watch.update(overrides)
    return watch


class DateCodeTests(unittest.TestCase):
    def test_parses_year_and_week(self):
        self.assertEqual(parse_date_code("2336"), {"year": 2023, "week": 36})

    def test_week_fifty_three_accepted(self):
        self.assertEqual(parse_date_code("2053")["week"], 53)

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2300")

    def test_non_digit_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("23W6")

    def test_ordinal_crosses_the_year_boundary_correctly(self):
        self.assertLess(date_code_ordinal("2353"), date_code_ordinal("2401"))

    def test_lower_bound_is_inclusive(self):
        self.assertTrue(date_code_in_range("2310", "2310", "2402"))

    def test_upper_bound_is_inclusive(self):
        self.assertTrue(date_code_in_range("2402", "2310", "2402"))

    def test_code_outside_the_range(self):
        self.assertFalse(date_code_in_range("2403", "2310", "2402"))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            date_code_in_range("2336", "2402", "2310")


class WorkingDayTests(unittest.TestCase):
    def test_monday_to_friday_is_four(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-11"), 4)

    def test_weekend_is_not_counted(self):
        self.assertEqual(working_days_between("2026-09-11", "2026-09-14"), 1)

    def test_backwards_range_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-14", "2026-09-07")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("Monday", "2026-09-14")


class ResolutionTests(unittest.TestCase):
    def test_lot_traced_is_definitive(self):
        self.assertEqual(screening_resolution("lot-traced"), "definitive")

    def test_part_number_only_is_presumptive(self):
        self.assertEqual(screening_resolution("part-number-only"), "presumptive")

    def test_untraced_has_no_resolution(self):
        self.assertEqual(screening_resolution("untraced"), "none")

    def test_every_grade_resolves(self):
        for grade in TRACEABILITY_GRADES:
            self.assertTrue(screening_resolution(grade))

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            screening_resolution("probably-fine")


class WatchTests(unittest.TestCase):
    def test_full_subscription_is_adequate(self):
        result = assess_alert_watch(sorted(ALERT_SOURCES), "2026-09-01", "2026-09-14")
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["source_coverage"], 1.0, places=9)

    def test_missing_mandatory_source_is_reported(self):
        result = assess_alert_watch(
            ["distributor-notice-feed", "industry-advisory-exchange"],
            "2026-09-01",
            "2026-09-14",
        )
        self.assertIn("agency-alert-system", result["missing_mandatory_sources"])
        self.assertFalse(result["adequate"])

    def test_coverage_landing_exactly_on_the_floor_is_met(self):
        result = assess_alert_watch(
            ["manufacturer-pcn-service", "agency-alert-system"],
            "2026-09-01",
            "2026-09-14",
        )
        self.assertAlmostEqual(
            result["source_coverage"], SOURCE_COVERAGE_FLOOR, places=9
        )
        self.assertTrue(result["source_coverage_met"])

    def test_single_source_is_short_of_the_floor(self):
        result = assess_alert_watch(
            ["manufacturer-pcn-service"], "2026-09-01", "2026-09-14"
        )
        self.assertFalse(result["source_coverage_met"])

    def test_review_exactly_on_the_interval_is_current(self):
        result = assess_alert_watch(
            sorted(ALERT_SOURCES), "2026-08-15", "2026-09-14"
        )
        self.assertEqual(result["days_since_review"], WATCH_REVIEW_INTERVAL_DAYS)
        self.assertTrue(result["review_current"])

    def test_stale_review_is_reported(self):
        result = assess_alert_watch(sorted(ALERT_SOURCES), "2026-06-01", "2026-09-14")
        self.assertFalse(result["review_current"])

    def test_duplicate_subscription_is_not_double_counted(self):
        result = assess_alert_watch(
            ["manufacturer-pcn-service", "manufacturer-pcn-service"],
            "2026-09-01",
            "2026-09-14",
        )
        self.assertEqual(len(result["subscribed_sources"]), 1)

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert_watch(["a-friend-at-the-fab"], "2026-09-01", "2026-09-14")

    def test_review_date_after_the_assessment_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert_watch(sorted(ALERT_SOURCES), "2026-09-20", "2026-09-14")

    def test_tolerance_is_small_enough_to_matter(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class ScreenTests(unittest.TestCase):
    def test_traced_lot_inside_the_range_is_affected(self):
        verdict = screen_holding(base_alert(), holding())
        self.assertEqual(verdict["verdict"], "affected")

    def test_traced_lot_outside_the_range_is_not_affected(self):
        verdict = screen_holding(base_alert(), holding(date_code="2405"))
        self.assertEqual(verdict["verdict"], "not-affected")

    def test_other_part_number_is_not_affected(self):
        verdict = screen_holding(base_alert(), holding(part_number="TPS7A4501"))
        self.assertEqual(verdict["verdict"], "not-affected")

    def test_part_number_match_is_case_insensitive(self):
        verdict = screen_holding(base_alert(), holding(part_number="lm2596s-adj"))
        self.assertEqual(verdict["verdict"], "affected")

    def test_part_number_only_lot_is_presumed_affected(self):
        verdict = screen_holding(
            base_alert(),
            holding(traceability_grade="part-number-only", date_code=None),
        )
        self.assertEqual(verdict["verdict"], "presumed-affected")

    def test_missing_date_code_is_never_read_as_cleared(self):
        verdict = screen_holding(base_alert(), holding(date_code=None))
        self.assertNotEqual(verdict["verdict"], "not-affected")

    def test_unresolvable_date_code_is_presumed_affected(self):
        verdict = screen_holding(base_alert(), holding(date_code="23XX"))
        self.assertEqual(verdict["verdict"], "presumed-affected")

    def test_untraced_lot_is_unscreenable(self):
        verdict = screen_holding(
            base_alert(),
            holding(traceability_grade="untraced", date_code=None),
        )
        self.assertEqual(verdict["verdict"], "unscreenable")

    def test_date_code_only_grade_still_screens_definitively(self):
        verdict = screen_holding(
            base_alert(), holding(traceability_grade="date-code-only")
        )
        self.assertEqual(verdict["verdict"], "affected")

    def test_unknown_holding_key_rejected(self):
        with self.assertRaises(ValueError):
            screen_holding(base_alert(), dict(holding(), shelf="B4"))

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            screen_holding(base_alert(), holding(quantity=0))

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            screen_holding(base_alert(), holding(state="in-transit"))


class CorrectiveResponseTests(unittest.TestCase):
    def test_every_state_maps_to_a_response(self):
        for state in HOLDING_RESPONSES:
            self.assertTrue(corrective_response(state, "affected", 4))

    def test_stores_is_quarantined(self):
        self.assertEqual(corrective_response("stores", "affected", 4), "quarantine-stock")

    def test_delivered_earns_an_in_service_assessment(self):
        self.assertEqual(
            corrective_response("delivered", "affected", 4), "in-service-assessment"
        )

    def test_not_affected_earns_no_action(self):
        self.assertEqual(corrective_response("stores", "not-affected", 4), "no-action")

    def test_unscreenable_lot_is_escalated(self):
        self.assertEqual(
            corrective_response("stores", "unscreenable", 4),
            "escalate-for-traceability-recovery",
        )

    def test_presumed_affected_critical_item_is_escalated(self):
        self.assertEqual(
            corrective_response("stores", "presumed-affected", 1),
            "escalate-for-traceability-recovery",
        )

    def test_presumed_affected_low_criticality_takes_the_routine_response(self):
        self.assertEqual(
            corrective_response("stores", "presumed-affected", 4), "quarantine-stock"
        )

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            corrective_response("stores", "affected", 0)

    def test_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            corrective_response("stores", "probably-ok", 4)


class ResponseTimingTests(unittest.TestCase):
    def test_safety_advisory_has_the_shortest_acknowledgement(self):
        ack, _ = response_deadlines("safety-advisory")
        self.assertEqual(ack, min(days[0] for days in ALERT_CATEGORIES.values()))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            response_deadlines("hearsay")

    def test_prompt_response_is_inside_both_deadlines(self):
        result = assess_alert_response(
            "errata", "2026-09-07", "2026-09-09", "2026-09-18", "2026-09-21"
        )
        self.assertTrue(result["acknowledgement_within_deadline"])
        self.assertTrue(result["corrective_within_deadline"])

    def test_open_corrective_action_keeps_accruing(self):
        result = assess_alert_response(
            "errata", "2026-09-07", "2026-09-09", None, "2026-11-30"
        )
        self.assertEqual(result["corrective_state"], "open")
        self.assertFalse(result["corrective_within_deadline"])

    def test_acknowledgement_exactly_on_its_deadline_is_inside(self):
        result = assess_alert_response(
            "errata", "2026-09-07", "2026-09-14", "2026-09-18", "2026-09-21"
        )
        self.assertEqual(result["acknowledgement_working_days"], 5)
        self.assertTrue(result["acknowledgement_within_deadline"])

    def test_assessment_before_receipt_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert_response(
                "errata", "2026-09-07", None, None, "2026-09-01"
            )


class AssessAlertTests(unittest.TestCase):
    def test_clean_alert_closes(self):
        result = assess_alert(
            base_alert(), [holding()], base_watch(), "2026-09-21"
        )
        self.assertEqual(result["verdict"], "closed")
        self.assertTrue(result["closeable"])

    def test_affected_quantity_is_carried(self):
        result = assess_alert(
            base_alert(), [holding()], base_watch(), "2026-09-21"
        )
        self.assertEqual(result["affected_quantity"], 25)

    def test_inadequate_watch_blocks_first(self):
        watch = base_watch(subscribed_sources=["distributor-notice-feed"])
        result = assess_alert(base_alert(), [holding()], watch, "2026-09-21")
        self.assertEqual(result["verdict"], "alert-watch-inadequate")

    def test_untraced_holding_blocks_the_close(self):
        untraced = holding(
            lot_id="LOT-B", traceability_grade="untraced", date_code=None
        )
        result = assess_alert(
            base_alert(), [holding(), untraced], base_watch(), "2026-09-21"
        )
        self.assertEqual(result["verdict"], "holdings-untraceable")

    def test_presumed_affected_lot_closes_on_presumption(self):
        presumed = holding(
            lot_id="LOT-C", traceability_grade="part-number-only", date_code=None
        )
        result = assess_alert(
            base_alert(), [presumed], base_watch(), "2026-09-21"
        )
        self.assertEqual(result["verdict"], "closed-on-presumption")
        self.assertEqual(result["presumed_affected_quantity"], 25)

    def test_late_acknowledgement_is_reported(self):
        alert = base_alert(acknowledged_date="2026-09-25", corrective_action_date=None)
        result = assess_alert(alert, [holding()], base_watch(), "2026-09-28")
        self.assertEqual(result["verdict"], "acknowledgement-late")

    def test_late_corrective_action_is_reported(self):
        alert = base_alert(corrective_action_date=None)
        watch = base_watch(last_review_date="2026-11-20")
        result = assess_alert(alert, [holding()], watch, "2026-11-30")
        self.assertEqual(result["verdict"], "corrective-action-late")

    def test_alert_from_an_unsubscribed_source_is_a_finding(self):
        watch = base_watch(
            subscribed_sources=["agency-alert-system", "distributor-notice-feed"]
        )
        result = assess_alert(base_alert(), [holding()], watch, "2026-09-21")
        self.assertTrue(
            any("does not subscribe" in finding for finding in result["findings"])
        )

    def test_delivered_holding_raises_an_in_service_finding(self):
        result = assess_alert(
            base_alert(), [holding(state="delivered")], base_watch(), "2026-09-21"
        )
        self.assertTrue(
            any("in-service assessment" in finding for finding in result["findings"])
        )

    def test_unaffected_holding_earns_no_action(self):
        result = assess_alert(
            base_alert(), [holding(date_code="2405")], base_watch(), "2026-09-21"
        )
        self.assertEqual(result["responses"], ())
        self.assertEqual(len(result["not_affected"]), 1)

    def test_inverted_alert_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert(
                base_alert(
                    first_affected_date_code="2402", last_affected_date_code="2310"
                ),
                [holding()],
                base_watch(),
                "2026-09-21",
            )

    def test_empty_part_number_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert(
                base_alert(affected_part_numbers=[]),
                [holding()],
                base_watch(),
                "2026-09-21",
            )

    def test_unknown_alert_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert(
                dict(base_alert(), severity="bad"),
                [holding()],
                base_watch(),
                "2026-09-21",
            )

    def test_holdings_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_alert(base_alert(), holding(), base_watch(), "2026-09-21")

    def test_watch_must_carry_its_review_date(self):
        with self.assertRaises(ValueError):
            assess_alert(
                base_alert(),
                [holding()],
                {"subscribed_sources": sorted(ALERT_SOURCES)},
                "2026-09-21",
            )

    def test_blank_alert_identity_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert(
                base_alert(alert_id="   "), [holding()], base_watch(), "2026-09-21"
            )


if __name__ == "__main__":
    unittest.main()
