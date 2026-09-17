"""Contract tests for the clause 5.5.3 class 2 alert and advisory logic."""

import unittest

from q60_class_2_alert_handling_logic import (
    PROCUREMENT_STAGES,
    REAPPROVAL_SEVERITIES,
    SEVERITIES,
    SEVERITY_ACK_DAYS,
    acknowledgement_state,
    advisory_applicability,
    affected_fraction,
    date_code_in_window,
    dissemination_list,
    impact_score,
    parse_date_code,
    priority_band,
    quantity_band,
    requires_reselection,
    stage_action,
    triage_advisory,
    working_days_between,
)


def _advisory(**over):
    base = {
        "severity": "reliability",
        "part_number": "LM139J",
        "manufacturer": "Northgate Semiconductor",
        "date_code_from": "2401",
        "date_code_to": "2452",
        "received_on": "2026-04-06",
        "raised_by": "Aurora Bus",
    }
    base.update(over)
    return base


def _entry(**over):
    base = {
        "entry_id": "DCL-001",
        "part_number": "LM139J",
        "manufacturer": "Northgate Semiconductor",
        "date_code": "2418",
        "stage": "in-build",
        "quantity": 40,
    }
    base.update(over)
    return base


class DateCodeTests(unittest.TestCase):
    def test_a_well_formed_date_code_parses(self):
        self.assertEqual(parse_date_code("2418"), 2418)

    def test_a_short_date_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("418")

    def test_a_non_numeric_date_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("24Q2")

    def test_a_week_outside_the_year_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2499")

    def test_a_code_inside_the_window_matches(self):
        self.assertTrue(date_code_in_window("2418", "2401", "2452"))

    def test_a_code_below_the_window_does_not(self):
        self.assertFalse(date_code_in_window("2350", "2401", "2452"))

    def test_a_code_above_the_window_does_not(self):
        self.assertFalse(date_code_in_window("2510", "2401", "2452"))

    def test_a_code_on_the_lower_bound_matches(self):
        self.assertTrue(date_code_in_window("2401", "2401", "2452"))

    def test_a_code_on_the_upper_bound_matches(self):
        self.assertTrue(date_code_in_window("2452", "2401", "2452"))

    def test_an_advisory_with_no_window_covers_every_code(self):
        self.assertTrue(date_code_in_window("1905"))

    def test_an_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            date_code_in_window("2418", "2452", "2401")


class ApplicabilityTests(unittest.TestCase):
    def test_a_matching_entry_applies(self):
        self.assertEqual(advisory_applicability(_advisory(), _entry()), "applies")

    def test_another_part_number_is_ruled_out(self):
        self.assertEqual(
            advisory_applicability(_advisory(), _entry(part_number="LM124J")),
            "not-applicable-part-number",
        )

    def test_a_second_source_manufacturer_is_ruled_out(self):
        self.assertEqual(
            advisory_applicability(_advisory(),
                                   _entry(manufacturer="Eastvale Devices")),
            "not-applicable-manufacturer",
        )

    def test_an_advisory_naming_no_manufacturer_reaches_every_source(self):
        advisory = _advisory()
        advisory.pop("manufacturer")
        self.assertEqual(
            advisory_applicability(advisory, _entry(manufacturer="Eastvale Devices")),
            "applies",
        )

    def test_a_date_code_outside_the_window_is_ruled_out(self):
        self.assertEqual(
            advisory_applicability(_advisory(), _entry(date_code="2510")),
            "not-applicable-date-code",
        )

    def test_an_entry_with_no_date_code_is_flagged_not_dismissed(self):
        entry = _entry()
        entry.pop("date_code")
        self.assertEqual(advisory_applicability(_advisory(), entry),
                         "date-code-unknown")

    def test_part_numbers_compare_case_insensitively(self):
        self.assertEqual(
            advisory_applicability(_advisory(), _entry(part_number="lm139j")),
            "applies",
        )

    def test_the_entry_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            advisory_applicability(_advisory(), "LM139J")


class ActionTests(unittest.TestCase):
    def test_an_informational_advisory_never_stops_a_build(self):
        self.assertEqual(stage_action("informational", "in-build"),
                         "record-and-monitor")

    def test_a_safety_advisory_stops_the_build(self):
        self.assertEqual(stage_action("safety", "in-build"),
                         "stop-build-and-raise-nonconformance")

    def test_a_withdrawal_cancels_an_open_order(self):
        self.assertEqual(stage_action("withdrawal", "ordered"), "cancel-order")

    def test_a_reliability_advisory_holds_an_open_order(self):
        self.assertEqual(stage_action("reliability", "ordered"),
                         "hold-order-pending-assessment")

    def test_a_part_only_selected_is_deselected(self):
        self.assertEqual(stage_action("withdrawal", "selected"),
                         "deselect-and-choose-alternative")

    def test_a_flying_part_earns_an_impact_statement(self):
        self.assertEqual(stage_action("safety", "in-orbit"),
                         "in-orbit-safety-impact-statement")

    def test_every_severity_and_stage_pair_has_an_action(self):
        for severity in SEVERITIES:
            for stage in PROCUREMENT_STAGES:
                self.assertTrue(stage_action(severity, stage))

    def test_an_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            stage_action("annoying", "in-build")

    def test_an_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_action("safety", "on-a-shelf")


class ReapprovalTests(unittest.TestCase):
    def test_an_informational_advisory_leaves_the_approval_alone(self):
        self.assertFalse(requires_reselection("informational"))

    def test_an_erratum_leaves_the_approval_alone(self):
        self.assertFalse(requires_reselection("errata"))

    def test_a_safety_advisory_reopens_the_approval(self):
        self.assertTrue(requires_reselection("safety"))

    def test_every_reapproval_severity_is_a_known_severity(self):
        self.assertTrue(set(REAPPROVAL_SEVERITIES) <= set(SEVERITIES))


class ScoringTests(unittest.TestCase):
    def test_a_larger_holding_scores_higher(self):
        self.assertGreater(impact_score("safety", "in-build", 400),
                           impact_score("safety", "in-build", 4))

    def test_a_later_stage_scores_higher(self):
        self.assertGreater(impact_score("safety", "in-orbit", 40),
                           impact_score("safety", "selected", 40))

    def test_a_harder_severity_scores_higher(self):
        self.assertGreater(impact_score("withdrawal", "selected", 40),
                           impact_score("informational", "selected", 40))

    def test_the_quantity_band_is_flat_inside_a_band(self):
        self.assertEqual(quantity_band(11), quantity_band(100))

    def test_a_zero_quantity_bands_at_zero(self):
        self.assertEqual(quantity_band(0), 0)

    def test_a_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            quantity_band(-1)

    def test_a_quiet_advisory_lands_in_the_watch_band(self):
        self.assertEqual(priority_band(impact_score("informational", "selected", 0)),
                         "watch")

    def test_a_withdrawal_lands_in_the_act_now_band(self):
        self.assertEqual(priority_band(impact_score("withdrawal", "in-build", 400)),
                         "act-now")

    def test_a_negative_score_rejected(self):
        with self.assertRaises(ValueError):
            priority_band(-3)


class HoldingTests(unittest.TestCase):
    def test_none_affected_reads_zero(self):
        self.assertAlmostEqual(affected_fraction(0, 50), 0.0, places=9)

    def test_all_affected_reads_one(self):
        self.assertAlmostEqual(affected_fraction(50, 50), 1.0, places=9)

    def test_a_fifth_affected_reads_a_fifth(self):
        self.assertAlmostEqual(affected_fraction(10, 50), 0.2, places=9)

    def test_more_affected_than_held_rejected(self):
        with self.assertRaises(ValueError):
            affected_fraction(51, 50)

    def test_an_empty_holding_rejected(self):
        with self.assertRaises(ValueError):
            affected_fraction(0, 0)


class DisseminationTests(unittest.TestCase):
    def _programmes(self):
        return [
            {"programme": "Aurora Bus", "declared_entries": [_entry()]},
            {"programme": "Kestrel Lander", "declared_entries": [_entry()]},
            {"programme": "Halcyon Relay",
             "declared_entries": [_entry(part_number="LM124J")]},
        ]

    def test_another_holder_is_listed(self):
        self.assertIn("Kestrel Lander",
                      dissemination_list(_advisory(), self._programmes()))

    def test_the_raising_programme_is_not_listed_again(self):
        self.assertNotIn("Aurora Bus",
                         dissemination_list(_advisory(), self._programmes()))

    def test_a_programme_holding_another_part_is_not_listed(self):
        self.assertNotIn("Halcyon Relay",
                         dissemination_list(_advisory(), self._programmes()))

    def test_the_list_is_returned_in_name_order(self):
        programmes = self._programmes()
        programmes.append({"programme": "Auriga Probe",
                           "declared_entries": [_entry()]})
        names = dissemination_list(_advisory(), programmes)
        self.assertEqual(names, sorted(names))

    def test_programmes_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            dissemination_list(_advisory(), "Kestrel Lander")


class AcknowledgementTests(unittest.TestCase):
    def test_working_days_skip_the_weekend(self):
        self.assertEqual(working_days_between("2026-04-03", "2026-04-06"), 1)

    def test_a_same_day_acknowledgement_uses_no_working_day(self):
        self.assertEqual(working_days_between("2026-04-06", "2026-04-06"), 0)

    def test_an_endpoint_before_the_receipt_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-04-06", "2026-04-03")

    def test_a_safety_advisory_has_the_shortest_window(self):
        self.assertLess(SEVERITY_ACK_DAYS["safety"],
                        SEVERITY_ACK_DAYS["informational"])

    def test_a_prompt_acknowledgement_is_within_the_deadline(self):
        state = acknowledgement_state("safety", "2026-04-06", "2026-04-08")
        self.assertTrue(state["within_deadline"])
        self.assertTrue(state["acknowledged"])

    def test_an_unacknowledged_advisory_keeps_accruing(self):
        state = acknowledgement_state("safety", "2026-04-06", None, "2026-05-06")
        self.assertFalse(state["acknowledged"])
        self.assertFalse(state["within_deadline"])
        self.assertGreater(state["overdue_by"], 0)

    def test_an_acknowledgement_state_needs_an_endpoint(self):
        with self.assertRaises(ValueError):
            acknowledgement_state("errata", "2026-04-06")


class TriageTests(unittest.TestCase):
    def _list(self):
        return [
            _entry(entry_id="DCL-001", stage="in-build", quantity=40),
            _entry(entry_id="DCL-002", stage="selected", quantity=5),
            _entry(entry_id="DCL-003", date_code="2510", stage="in-orbit",
                   quantity=12),
            _entry(entry_id="DCL-004", part_number="LM124J", stage="ordered",
                   quantity=200),
        ]

    def test_only_the_matching_entries_earn_actions(self):
        result = triage_advisory(_advisory(), self._list(), [], "2026-04-06")
        self.assertEqual([item["entry_id"] for item in result["matched_entries"]],
                         ["DCL-001", "DCL-002"])

    def test_the_ruled_out_entries_keep_their_reason(self):
        result = triage_advisory(_advisory(), self._list(), [], "2026-04-06")
        reasons = {item["entry_id"]: item["applicability"]
                   for item in result["skipped_entries"]}
        self.assertEqual(reasons["DCL-003"], "not-applicable-date-code")
        self.assertEqual(reasons["DCL-004"], "not-applicable-part-number")

    def test_the_queue_is_ordered_by_impact(self):
        result = triage_advisory(_advisory(), self._list(), [], "2026-04-06")
        scores = [item["impact_score"] for item in result["matched_entries"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_the_highest_priority_is_reported(self):
        result = triage_advisory(_advisory(severity="withdrawal"), self._list(),
                                 [], "2026-04-06")
        self.assertEqual(result["highest_priority"], "act-now")

    def test_a_reliability_advisory_with_matches_reopens_the_approval(self):
        result = triage_advisory(_advisory(), self._list(), [], "2026-04-06")
        self.assertTrue(result["requires_reselection"])

    def test_an_advisory_with_no_match_reopens_nothing(self):
        result = triage_advisory(_advisory(part_number="AD8021"), self._list(),
                                 [], "2026-04-06")
        self.assertEqual(result["matched_entries"], [])
        self.assertFalse(result["requires_reselection"])
        self.assertEqual(result["highest_priority"], "none")

    def test_the_affected_fraction_uses_the_whole_holding(self):
        result = triage_advisory(_advisory(), self._list(), [], "2026-04-06")
        self.assertAlmostEqual(result["affected_fraction"], 45.0 / 257.0, places=9)

    def test_the_acknowledgement_clock_is_reported(self):
        result = triage_advisory(_advisory(), self._list(), [], "2026-05-06")
        self.assertFalse(result["acknowledgement"]["within_deadline"])

    def test_the_declared_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            triage_advisory(_advisory(), "DCL-001", [], "2026-04-06")

    def test_the_advisory_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            triage_advisory([_advisory()], self._list(), [], "2026-04-06")


if __name__ == "__main__":
    unittest.main(verbosity=1)
