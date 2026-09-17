"""Contract tests for the clause 6.5.3 class 3 alert and advisory logic."""

import unittest

from q60_class_3_alert_handling_logic import (
    APPLICABILITY_STATES,
    PROCUREMENT_STAGES,
    SEVERITIES,
    SEVERITY_ACK_DAYS,
    acknowledgement_state,
    closing_evidence,
    date_code_in_range,
    dissemination_list,
    effective_applicability,
    entry_applicability,
    exposed_share,
    exposure_counts,
    parse_date_code,
    priority_band,
    priority_score,
    stage_action,
    supply_route,
    triage_class_3_advisory,
    working_days_between,
)


def advisory(**overrides):
    """Return an alert naming a manufacturer and a date-code window."""
    record = {
        "advisory_id": "ADV-2026-071",
        "part_number": "lmv321-sot23",
        "manufacturer": "Northgate Semiconductor",
        "date_code_start": "2401",
        "date_code_end": "2426",
        "severity": "alert",
        "issued_date": "2026-09-07",
        "acknowledged_date": "2026-09-11",
        "procurable": True,
        "replacement_approved": True,
    }
    record.update(overrides)
    return record


def entries():
    return [
        {
            "entry_id": "DCL-001",
            "part_number": "LMV321-SOT23",
            "manufacturer": "Northgate Semiconductor",
            "date_code": "2412",
            "stage": "kitted",
            "quantity": 24,
        },
        {
            "entry_id": "DCL-002",
            "part_number": "LMV321-SOT23",
            "manufacturer": "Northgate Semiconductor",
            "date_code": "2451",
            "stage": "received",
            "quantity": 8,
        },
        {
            "entry_id": "DCL-003",
            "part_number": "LMV321-SOT23",
            "stage": "installed",
            "quantity": 4,
        },
        {
            "entry_id": "DCL-004",
            "part_number": "OPA333-SOT23",
            "manufacturer": "Northgate Semiconductor",
            "date_code": "2412",
            "stage": "kitted",
            "quantity": 100,
        },
    ]


def programmes():
    return [
        {"programme": "beta-sat", "part_numbers": ["LMV321-SOT23", "OPA333-SOT23"]},
        {"programme": "alpha-sat", "part_numbers": ["lmv321-sot23"]},
        {"programme": "gamma-sat", "part_numbers": ["AD8628-SOIC"]},
    ]


class DateCodeTests(unittest.TestCase):
    def test_a_four_digit_code_becomes_an_ordered_year_week_pair(self):
        self.assertEqual(parse_date_code("2412"), (2024, 12))

    def test_a_week_of_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2400")

    def test_a_week_past_fifty_three_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2454")

    def test_a_non_numeric_code_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("24Q2")

    def test_a_code_inside_the_window_is_inside_it(self):
        self.assertTrue(date_code_in_range("2412", "2401", "2426"))

    def test_the_window_endpoints_are_inclusive(self):
        self.assertTrue(date_code_in_range("2401", "2401", "2426"))
        self.assertTrue(date_code_in_range("2426", "2401", "2426"))

    def test_a_window_that_runs_backwards_is_rejected(self):
        with self.assertRaises(ValueError):
            date_code_in_range("2412", "2426", "2401")


class ApplicabilityTests(unittest.TestCase):
    def test_a_different_part_number_is_excluded(self):
        self.assertEqual(entry_applicability(entries()[3], advisory()), "excluded")

    def test_a_confirmed_match_applies(self):
        self.assertEqual(entry_applicability(entries()[0], advisory()), "applies")

    def test_a_date_code_outside_the_window_is_excluded(self):
        self.assertEqual(entry_applicability(entries()[1], advisory()), "excluded")

    def test_an_entry_recording_neither_axis_is_indeterminate(self):
        self.assertEqual(entry_applicability(entries()[2], advisory()), "indeterminate")

    def test_a_second_source_manufacturer_is_excluded(self):
        entry = dict(entries()[0], manufacturer="Southbank Devices")
        self.assertEqual(entry_applicability(entry, advisory()), "excluded")

    def test_an_indeterminate_entry_is_worked_as_if_it_applied(self):
        self.assertEqual(effective_applicability("indeterminate"), "applies")

    def test_an_excluded_entry_stays_excluded_when_worked(self):
        self.assertEqual(effective_applicability("excluded"), "excluded")

    def test_an_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_applicability("probably")

    def test_the_evidence_that_would_close_an_entry_is_named(self):
        wanted = closing_evidence(entries()[2], advisory())
        self.assertEqual(len(wanted), 2)
        self.assertTrue(any("manufacturer" in w for w in wanted))
        self.assertTrue(any("date code" in w for w in wanted))

    def test_a_decided_entry_needs_no_closing_evidence(self):
        self.assertEqual(closing_evidence(entries()[0], advisory()), ())

    def test_an_entry_without_a_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            entry_applicability({"entry_id": "DCL-009"}, advisory())


class ActionTests(unittest.TestCase):
    def test_a_safety_alert_on_an_installed_part_removes_it(self):
        self.assertEqual(stage_action("safety-alert", "installed"), "remove-and-replace")

    def test_an_alert_on_an_installed_part_assesses_the_application(self):
        self.assertEqual(stage_action("alert", "installed"), "assess-application-impact")

    def test_an_alert_on_delivered_hardware_reaches_the_customer(self):
        self.assertEqual(stage_action("alert", "delivered"), "notify-customer")

    def test_information_never_moves_hardware(self):
        for stage in PROCUREMENT_STAGES:
            self.assertEqual(
                stage_action("information", stage), "record-against-selection"
            )

    def test_every_severity_covers_every_stage(self):
        for severity in SEVERITIES:
            for stage in PROCUREMENT_STAGES:
                self.assertTrue(stage_action(severity, stage))

    def test_an_unknown_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_action("alert", "in-the-post")


class SupplyRouteTests(unittest.TestCase):
    def test_an_available_part_with_an_approved_equivalent_comes_from_stock(self):
        self.assertEqual(
            supply_route(True, "alert", True), "replace-from-approved-stock"
        )

    def test_an_available_part_without_one_earns_a_last_time_buy(self):
        self.assertEqual(
            supply_route(True, "alert", False), "last-time-buy-and-screen"
        )

    def test_an_unbuyable_part_moves_the_response_into_the_design(self):
        self.assertEqual(
            supply_route(False, "alert", True), "design-change-required"
        )

    def test_an_information_advisory_does_not_force_a_design_change(self):
        self.assertEqual(
            supply_route(False, "information", True), "replace-from-approved-stock"
        )

    def test_a_non_boolean_availability_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            supply_route("yes", "alert", True)


class PriorityTests(unittest.TestCase):
    def test_a_higher_severity_outranks_a_later_stage(self):
        self.assertGreater(
            priority_score("safety-alert", "selected", 1, "applies"),
            priority_score("alert", "delivered", 99, "applies"),
        )

    def test_an_indeterminate_match_sits_under_a_decided_one(self):
        self.assertLess(
            priority_score("alert", "kitted", 10, "indeterminate"),
            priority_score("alert", "kitted", 10, "applies"),
        )

    def test_an_excluded_entry_scores_nothing(self):
        self.assertEqual(priority_score("safety-alert", "delivered", 99, "excluded"), 0)

    def test_quantity_only_separates_a_tie(self):
        self.assertGreater(
            priority_score("alert", "kitted", 40, "applies"),
            priority_score("alert", "kitted", 4, "applies"),
        )

    def test_a_negative_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            priority_score("alert", "kitted", -1, "applies")

    def test_bands_rise_with_the_score(self):
        self.assertEqual(priority_band(0), "routine")
        self.assertEqual(priority_band(1500), "routine")
        self.assertEqual(priority_band(2500), "elevated")
        self.assertEqual(priority_band(3500), "urgent")
        self.assertEqual(priority_band(4500), "immediate")

    def test_a_negative_score_is_rejected(self):
        with self.assertRaises(ValueError):
            priority_band(-5)


class ExposureTests(unittest.TestCase):
    def test_the_states_are_counted_across_the_whole_list(self):
        counts = exposure_counts(entries(), advisory())
        self.assertEqual(counts["applies"], 1)
        self.assertEqual(counts["indeterminate"], 1)
        self.assertEqual(counts["excluded"], 2)

    def test_the_worked_share_counts_indeterminate_entries_in(self):
        share = exposed_share(exposure_counts(entries(), advisory()))
        self.assertEqual(share["numerator"], 2)
        self.assertEqual(share["denominator"], 4)
        self.assertAlmostEqual(share["fraction"], 0.5, places=9)

    def test_an_empty_list_has_no_share_rather_than_a_division(self):
        share = exposed_share({state: 0 for state in APPLICABILITY_STATES})
        self.assertEqual(share["denominator"], 0)
        self.assertAlmostEqual(share["fraction"], 0.0, places=9)

    def test_counts_missing_a_state_are_rejected(self):
        with self.assertRaises(ValueError):
            exposed_share({"applies": 1})


class DisseminationTests(unittest.TestCase):
    def test_every_programme_holding_the_selection_is_reached(self):
        self.assertEqual(
            dissemination_list(programmes(), advisory()), ("alpha-sat", "beta-sat")
        )

    def test_a_programme_not_holding_the_part_is_left_alone(self):
        self.assertNotIn("gamma-sat", dissemination_list(programmes(), advisory()))

    def test_a_programme_record_missing_its_part_list_is_rejected(self):
        with self.assertRaises(ValueError):
            dissemination_list([{"programme": "delta-sat"}], advisory())


class AcknowledgementTests(unittest.TestCase):
    def test_an_acknowledged_advisory_reports_its_working_days(self):
        state = acknowledgement_state(
            "alert", "2026-09-07", "2026-09-11", "2026-09-21"
        )
        self.assertEqual(state["state"], "acknowledged")
        self.assertEqual(state["working_days"], 4)
        self.assertTrue(state["within_deadline"])

    def test_an_open_advisory_keeps_accruing(self):
        state = acknowledgement_state("safety-alert", "2026-09-07", None, "2026-09-21")
        self.assertEqual(state["state"], "open")
        self.assertFalse(state["within_deadline"])

    def test_a_safety_alert_has_the_shortest_deadline(self):
        self.assertEqual(
            SEVERITY_ACK_DAYS["safety-alert"], min(SEVERITY_ACK_DAYS.values())
        )

    def test_an_as_of_before_the_issue_date_is_rejected(self):
        with self.assertRaises(ValueError):
            acknowledgement_state("alert", "2026-09-07", None, "2026-09-01")

    def test_a_full_week_is_five_working_days(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-14"), 5)


class TriageTests(unittest.TestCase):
    def test_a_clean_advisory_closes(self):
        result = triage_class_3_advisory(
            advisory(date_code_start=None, date_code_end=None),
            [entries()[0]],
            programmes(),
            "2026-09-21",
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["closed"])

    def test_excluded_entries_never_reach_the_queue(self):
        result = triage_class_3_advisory(
            advisory(), entries(), programmes(), "2026-09-21"
        )
        self.assertEqual(result["match_count"], 2)
        self.assertNotIn("DCL-004", [m["entry_id"] for m in result["matches"]])

    def test_an_indeterminate_entry_raises_a_finding_and_is_still_worked(self):
        result = triage_class_3_advisory(
            advisory(), entries(), programmes(), "2026-09-21"
        )
        indeterminate = [m for m in result["matches"] if m["entry_id"] == "DCL-003"][0]
        self.assertEqual(indeterminate["worked_as"], "applies")
        self.assertTrue(any("cannot be ruled out" in f for f in result["findings"]))

    def test_the_queue_is_ordered_by_score(self):
        result = triage_class_3_advisory(
            advisory(), entries(), programmes(), "2026-09-21"
        )
        scores = [m["priority_score"] for m in result["matches"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_an_obsolete_part_puts_the_response_in_the_design(self):
        result = triage_class_3_advisory(
            advisory(procurable=False), entries(), programmes(), "2026-09-21"
        )
        self.assertEqual(result["supply_route"], "design-change-required")
        self.assertTrue(any("design change" in f for f in result["findings"]))

    def test_an_unacknowledged_advisory_is_a_finding(self):
        result = triage_class_3_advisory(
            advisory(acknowledged_date=None), entries(), programmes(), "2026-10-05"
        )
        self.assertTrue(any("acknowledgement limit" in f for f in result["findings"]))
        self.assertFalse(result["closed"])

    def test_a_half_specified_date_code_range_is_rejected(self):
        with self.assertRaises(ValueError):
            triage_class_3_advisory(
                advisory(date_code_end=None), entries(), programmes(), "2026-09-21"
            )

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            triage_class_3_advisory(
                advisory(severity="urgent-ish"), entries(), programmes(), "2026-09-21"
            )

    def test_an_entry_with_an_unknown_stage_is_rejected(self):
        bad = entries()
        bad[0] = dict(bad[0], stage="somewhere")
        with self.assertRaises(ValueError):
            triage_class_3_advisory(advisory(), bad, programmes(), "2026-09-21")

    def test_an_advisory_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            triage_class_3_advisory("ADV-1", entries(), programmes(), "2026-09-21")


if __name__ == "__main__":
    unittest.main()
