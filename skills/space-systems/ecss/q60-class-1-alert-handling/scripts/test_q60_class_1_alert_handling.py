"""Contract tests for the clause 4.5.3 advisory handling logic."""

import unittest

from q60_class_1_alert_handling_logic import (
    PROCUREMENT_STAGES,
    SEVERITIES,
    SEVERITY_ACK_DAYS,
    acknowledgement_deadline,
    assess_advisory,
    dissemination_list,
    match_declared_entry,
    requires_part_reapproval,
    stage_action,
    working_days_between,
)


def base_advisory(**overrides):
    """Return an errata advisory received on a Monday and acknowledged Wednesday."""
    advisory = {
        "advisory_id": "ADV-2026-217",
        "severity": "errata",
        "part_numbers": ["ad590jh"],
        "manufacturer": "Example Semiconductor",
        "programme": "SAT-ALPHA",
        "received_date": "2026-09-07",
        "acknowledged_date": "2026-09-09",
    }
    advisory.update(overrides)
    return advisory


def declared_list():
    return [
        {
            "entry_id": "DCL-011",
            "part_number": "AD590JH",
            "manufacturer": "Example Semiconductor",
            "stage": "selected",
            "quantity": 4,
            "programme": "SAT-ALPHA",
            "approval_reference": "PAD-011",
        },
        {
            "entry_id": "DCL-012",
            "part_number": "AD590JH",
            "manufacturer": "Second Source Devices",
            "stage": "received",
            "quantity": 10,
            "programme": "SAT-ALPHA",
            "approval_reference": "PAD-012",
        },
        {
            "entry_id": "DCL-013",
            "part_number": "LM139AJ",
            "manufacturer": "Example Semiconductor",
            "stage": "in-build",
            "quantity": 6,
            "programme": "SAT-ALPHA",
            "approval_reference": "PAD-013",
        },
    ]


def portfolio():
    return [
        {
            "entry_id": "DCL-201",
            "part_number": "AD590JH",
            "manufacturer": "Example Semiconductor",
            "stage": "ordered",
            "programme": "SAT-BETA",
        },
        {
            "entry_id": "DCL-301",
            "part_number": "AD590JH",
            "manufacturer": "Example Semiconductor",
            "stage": "in-orbit",
            "programme": "SAT-ALPHA",
        },
        {
            "entry_id": "DCL-401",
            "part_number": "LM139AJ",
            "manufacturer": "Example Semiconductor",
            "stage": "selected",
            "programme": "SAT-GAMMA",
        },
    ]


class DeadlineTests(unittest.TestCase):
    def test_safety_gets_the_shortest_deadline(self):
        self.assertEqual(
            acknowledgement_deadline("safety"), min(SEVERITY_ACK_DAYS.values())
        )

    def test_informational_gets_the_longest_deadline(self):
        self.assertEqual(
            acknowledgement_deadline("informational"), max(SEVERITY_ACK_DAYS.values())
        )

    def test_every_severity_has_a_deadline(self):
        for severity in SEVERITIES:
            self.assertGreater(acknowledgement_deadline(severity), 0)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            acknowledgement_deadline("urgent")


class StageActionTests(unittest.TestCase):
    def test_a_part_only_selected_is_swapped_out(self):
        self.assertEqual(stage_action("selected"), "deselect-and-choose-alternative")

    def test_a_received_part_is_quarantined(self):
        self.assertEqual(stage_action("received"), "quarantine-and-re-verify-incoming")

    def test_a_part_in_build_raises_a_nonconformance(self):
        self.assertEqual(
            stage_action("in-build"), "raise-nonconformance-and-assess-retrofit"
        )

    def test_a_flying_part_owes_an_in_orbit_statement(self):
        self.assertEqual(stage_action("in-orbit"), "in-orbit-impact-statement")

    def test_every_stage_has_an_action(self):
        for stage in PROCUREMENT_STAGES:
            self.assertTrue(stage_action(stage))

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_action("on-the-shelf")


class MatchTests(unittest.TestCase):
    def test_part_number_match_is_case_insensitive(self):
        self.assertTrue(
            match_declared_entry(["ad590jh"], None, declared_list()[0])
        )

    def test_a_part_number_not_named_does_not_match(self):
        self.assertFalse(
            match_declared_entry(["AD590JH"], None, declared_list()[2])
        )

    def test_a_named_manufacturer_excludes_a_second_source(self):
        self.assertFalse(
            match_declared_entry(
                ["AD590JH"], "Example Semiconductor", declared_list()[1]
            )
        )

    def test_no_named_manufacturer_sweeps_in_every_source(self):
        self.assertTrue(match_declared_entry(["AD590JH"], None, declared_list()[1]))

    def test_an_entry_with_no_manufacturer_fails_a_manufacturer_test(self):
        entry = {"entry_id": "DCL-099", "part_number": "AD590JH", "stage": "selected"}
        self.assertFalse(
            match_declared_entry(["AD590JH"], "Example Semiconductor", entry)
        )

    def test_empty_part_number_list_rejected(self):
        with self.assertRaises(ValueError):
            match_declared_entry([], None, declared_list()[0])

    def test_entry_missing_a_stage_rejected(self):
        with self.assertRaises(ValueError):
            match_declared_entry(
                ["AD590JH"], None, {"entry_id": "X", "part_number": "AD590JH"}
            )


class ReapprovalTests(unittest.TestCase):
    def test_a_part_only_selected_is_swapped_not_reapproved(self):
        self.assertFalse(requires_part_reapproval("safety", "selected"))

    def test_a_safety_advisory_on_a_received_part_needs_reapproval(self):
        self.assertTrue(requires_part_reapproval("safety", "received"))

    def test_a_withdrawal_needs_reapproval(self):
        self.assertTrue(requires_part_reapproval("withdrawal", "in-build"))

    def test_an_informational_note_does_not(self):
        self.assertFalse(requires_part_reapproval("informational", "in-build"))

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            requires_part_reapproval("catastrophic", "in-build")


class DisseminationTests(unittest.TestCase):
    def test_another_programme_holding_the_part_is_listed(self):
        reached = dissemination_list(
            ["AD590JH"], "Example Semiconductor", portfolio(), "SAT-ALPHA"
        )
        self.assertIn("SAT-BETA", reached)

    def test_the_originating_programme_is_not_listed(self):
        reached = dissemination_list(
            ["AD590JH"], "Example Semiconductor", portfolio(), "SAT-ALPHA"
        )
        self.assertNotIn("SAT-ALPHA", reached)

    def test_a_programme_holding_another_part_is_not_listed(self):
        reached = dissemination_list(
            ["AD590JH"], "Example Semiconductor", portfolio(), "SAT-ALPHA"
        )
        self.assertNotIn("SAT-GAMMA", reached)

    def test_portfolio_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            dissemination_list(["AD590JH"], None, portfolio()[0], "SAT-ALPHA")

    def test_blank_originating_programme_rejected(self):
        with self.assertRaises(ValueError):
            dissemination_list(["AD590JH"], None, portfolio(), "  ")


class WorkingDayTests(unittest.TestCase):
    def test_monday_to_wednesday_is_two_working_days(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-09"), 2)

    def test_a_weekend_adds_nothing(self):
        self.assertEqual(working_days_between("2026-09-11", "2026-09-13"), 0)

    def test_reversed_dates_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-13", "2026-09-11")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-13-01", "2026-09-11")


class AssessAdvisoryTests(unittest.TestCase):
    def test_only_the_named_manufacturer_entry_is_impacted(self):
        result = assess_advisory(
            base_advisory(), declared_list(), [], "2026-09-14"
        )
        self.assertEqual(
            [item["entry_id"] for item in result["impacted_entries"]], ["DCL-011"]
        )

    def test_a_second_source_entry_stays_untouched(self):
        result = assess_advisory(
            base_advisory(), declared_list(), [], "2026-09-14"
        )
        self.assertIn(
            "DCL-012", [entry["entry_id"] for entry in result["untouched_entries"]]
        )

    def test_dropping_the_manufacturer_widens_the_match(self):
        result = assess_advisory(
            base_advisory(manufacturer=None), declared_list(), [], "2026-09-14"
        )
        self.assertEqual(len(result["impacted_entries"]), 2)

    def test_impacted_quantity_sums_the_matched_entries(self):
        result = assess_advisory(
            base_advisory(manufacturer=None), declared_list(), [], "2026-09-14"
        )
        self.assertEqual(result["impacted_quantity"], 14)

    def test_the_stage_action_is_attached_to_each_entry(self):
        result = assess_advisory(
            base_advisory(), declared_list(), [], "2026-09-14"
        )
        self.assertEqual(
            result["impacted_entries"][0]["action"], "deselect-and-choose-alternative"
        )

    def test_a_safety_advisory_flags_reapproval_past_selection(self):
        result = assess_advisory(
            base_advisory(severity="safety", manufacturer=None),
            declared_list(),
            [],
            "2026-09-08",
        )
        self.assertEqual(result["reapproval_entries"], ("DCL-012",))

    def test_an_unacknowledged_advisory_keeps_accruing(self):
        result = assess_advisory(
            base_advisory(acknowledged_date=None), declared_list(), [], "2026-09-25"
        )
        self.assertEqual(result["acknowledgement_state"], "open")
        self.assertEqual(result["acknowledgement_working_days"], 14)
        self.assertFalse(result["acknowledgement_within_deadline"])

    def test_a_late_acknowledgement_raises_a_finding(self):
        result = assess_advisory(
            base_advisory(severity="safety", acknowledged_date="2026-09-14"),
            declared_list(),
            [],
            "2026-09-14",
        )
        self.assertTrue(
            any("acknowledgement" in finding for finding in result["findings"])
        )

    def test_a_clean_advisory_with_no_spread_is_closeable(self):
        result = assess_advisory(
            base_advisory(), declared_list(), [], "2026-09-14"
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["closeable"])

    def test_other_programmes_holding_the_part_raise_a_finding(self):
        result = assess_advisory(
            base_advisory(), declared_list(), portfolio(), "2026-09-14"
        )
        self.assertEqual(result["dissemination"], ("SAT-BETA",))
        self.assertFalse(result["closeable"])

    def test_a_flying_entry_owes_an_in_orbit_statement(self):
        entries = declared_list() + [
            {
                "entry_id": "DCL-014",
                "part_number": "AD590JH",
                "manufacturer": "Example Semiconductor",
                "stage": "in-orbit",
                "quantity": 2,
                "programme": "SAT-ALPHA",
                "approval_reference": "PAD-014",
            }
        ]
        result = assess_advisory(base_advisory(), entries, [], "2026-09-14")
        self.assertTrue(
            any("already flying" in finding for finding in result["findings"])
        )

    def test_a_reapproval_entry_without_an_approval_reference_is_flagged(self):
        entries = [
            {
                "entry_id": "DCL-020",
                "part_number": "AD590JH",
                "manufacturer": "Example Semiconductor",
                "stage": "in-build",
                "quantity": 3,
                "programme": "SAT-ALPHA",
            }
        ]
        result = assess_advisory(
            base_advisory(severity="withdrawal"), entries, [], "2026-09-09"
        )
        self.assertTrue(
            any("no approval reference" in finding for finding in result["findings"])
        )

    def test_as_of_before_receipt_rejected(self):
        with self.assertRaises(ValueError):
            assess_advisory(base_advisory(), declared_list(), [], "2026-09-01")

    def test_empty_part_number_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_advisory(
                base_advisory(part_numbers=[]), declared_list(), [], "2026-09-14"
            )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            assess_advisory(
                base_advisory(severity="urgent"), declared_list(), [], "2026-09-14"
            )

    def test_declared_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_advisory(base_advisory(), declared_list()[0], [], "2026-09-14")

    def test_zero_quantity_entry_rejected(self):
        entries = declared_list()
        entries[0]["quantity"] = 0
        with self.assertRaises(ValueError):
            assess_advisory(base_advisory(), entries, [], "2026-09-14")


if __name__ == "__main__":
    unittest.main()
