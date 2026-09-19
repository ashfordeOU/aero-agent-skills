"""Contract tests for the clause 6.23.5.3 copy suspension and resumption logic."""

import unittest

from e7041_suspending_and_resuming_the_file_copy_operations_logic import (
    OPERATION_STATES,
    advance_operation,
    apply_directive,
    assess_directive_campaign,
    build_list,
    find_operation,
    list_summary,
    new_operation,
    resume_all,
    resume_operation,
    suspend_all,
    suspend_operation,
    validate_operation,
)

KEY_A = ("mass-memory", "housekeeping.dat", "downlink-buffer", "housekeeping.dat")
KEY_B = ("mass-memory", "event-log.dat", "downlink-buffer", "event-log.dat")
KEY_C = ("payload-store", "image-042.raw", "downlink-buffer", "image-042.raw")
KEY_ABSENT = ("mass-memory", "absent.dat", "downlink-buffer", "absent.dat")


def op(key, total=1000, copied=0, state="running"):
    return new_operation(key[0], key[1], key[2], key[3], total, copied, state)


def a_list():
    return build_list([op(KEY_A, 1000, 400), op(KEY_B, 800, 0), op(KEY_C, 2000, 2000, "completed")])


class ConstructionTests(unittest.TestCase):
    def test_new_operation_defaults_to_running(self):
        entry = op(KEY_A)
        self.assertEqual(entry["state"], "running")
        self.assertEqual(entry["octets_copied"], 0)

    def test_states_are_the_three_lifecycle_values(self):
        self.assertEqual(OPERATION_STATES, ("running", "suspended", "completed"))

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            new_operation("mass-memory", "  ", "downlink-buffer", "x.dat", 100)

    def test_zero_total_rejected(self):
        with self.assertRaises(ValueError):
            op(KEY_A, total=0)

    def test_copied_beyond_total_rejected(self):
        with self.assertRaises(ValueError):
            op(KEY_A, total=100, copied=200)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            op(KEY_A, state="paused")

    def test_completed_with_octets_outstanding_rejected(self):
        with self.assertRaises(ValueError):
            op(KEY_A, total=100, copied=50, state="completed")

    def test_duplicate_key_in_list_rejected(self):
        with self.assertRaises(ValueError):
            build_list([op(KEY_A), op(KEY_A)])

    def test_malformed_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation({"key": KEY_A, "octets_total": 10})

    def test_find_needs_a_four_part_key(self):
        with self.assertRaises(ValueError):
            find_operation(a_list(), ("mass-memory", "housekeeping.dat"))


class SuspendTests(unittest.TestCase):
    def test_running_operation_suspends(self):
        ops = a_list()
        outcome = suspend_operation(ops, KEY_A)
        self.assertEqual(outcome["outcome"], "changed")
        self.assertEqual(find_operation(ops, KEY_A)["state"], "suspended")

    def test_suspending_twice_is_redundant_not_an_error(self):
        ops = a_list()
        suspend_operation(ops, KEY_A)
        outcome = suspend_operation(ops, KEY_A)
        self.assertEqual(outcome["outcome"], "redundant")
        self.assertEqual(find_operation(ops, KEY_A)["state"], "suspended")

    def test_suspending_a_completed_operation_is_refused(self):
        outcome = suspend_operation(a_list(), KEY_C)
        self.assertEqual(outcome["outcome"], "refused")
        self.assertIn("completed", outcome["reason"])

    def test_suspending_an_unknown_operation_is_refused(self):
        outcome = suspend_operation(a_list(), KEY_ABSENT)
        self.assertEqual(outcome["outcome"], "refused")
        self.assertIn("no copy operation", outcome["reason"])

    def test_suspension_preserves_the_octets_already_moved(self):
        ops = a_list()
        suspend_operation(ops, KEY_A)
        self.assertEqual(find_operation(ops, KEY_A)["octets_copied"], 400)

    def test_suspend_all_touches_every_running_entry(self):
        ops = a_list()
        outcomes = suspend_all(ops)
        changed = [o for o in outcomes if o["outcome"] == "changed"]
        self.assertEqual(len(changed), 2)
        self.assertEqual(list_summary(ops)["suspended"], 2)

    def test_suspend_all_leaves_a_completed_entry_alone(self):
        ops = a_list()
        suspend_all(ops)
        self.assertEqual(find_operation(ops, KEY_C)["state"], "completed")


class ResumeTests(unittest.TestCase):
    def test_suspended_operation_resumes(self):
        ops = a_list()
        suspend_operation(ops, KEY_A)
        outcome = resume_operation(ops, KEY_A)
        self.assertEqual(outcome["outcome"], "changed")
        self.assertEqual(find_operation(ops, KEY_A)["state"], "running")

    def test_resuming_a_running_operation_is_redundant(self):
        outcome = resume_operation(a_list(), KEY_B)
        self.assertEqual(outcome["outcome"], "redundant")

    def test_resuming_a_completed_operation_is_refused(self):
        outcome = resume_operation(a_list(), KEY_C)
        self.assertEqual(outcome["outcome"], "refused")

    def test_resuming_an_unknown_operation_is_refused(self):
        outcome = resume_operation(a_list(), KEY_ABSENT)
        self.assertEqual(outcome["outcome"], "refused")

    def test_resume_continues_from_the_suspension_point(self):
        ops = a_list()
        suspend_operation(ops, KEY_A)
        resume_operation(ops, KEY_A)
        advance_operation(ops, KEY_A, 100)
        self.assertEqual(find_operation(ops, KEY_A)["octets_copied"], 500)

    def test_resume_all_restarts_every_suspended_entry(self):
        ops = a_list()
        suspend_all(ops)
        resume_all(ops)
        summary = list_summary(ops)
        self.assertEqual(summary["running"], 2)
        self.assertEqual(summary["suspended"], 0)


class AdvanceTests(unittest.TestCase):
    def test_running_operation_moves_octets(self):
        ops = a_list()
        advance_operation(ops, KEY_B, 300)
        self.assertEqual(find_operation(ops, KEY_B)["octets_copied"], 300)

    def test_suspended_operation_refuses_to_move_octets(self):
        ops = a_list()
        suspend_operation(ops, KEY_B)
        with self.assertRaises(ValueError):
            advance_operation(ops, KEY_B, 100)

    def test_completed_operation_refuses_to_move_octets(self):
        with self.assertRaises(ValueError):
            advance_operation(a_list(), KEY_C, 1)

    def test_last_octet_completes_the_operation(self):
        ops = a_list()
        advance_operation(ops, KEY_A, 600)
        self.assertEqual(find_operation(ops, KEY_A)["state"], "completed")

    def test_overshoot_rejected(self):
        with self.assertRaises(ValueError):
            advance_operation(a_list(), KEY_A, 601)

    def test_zero_octet_advance_rejected(self):
        with self.assertRaises(ValueError):
            advance_operation(a_list(), KEY_A, 0)

    def test_advance_of_an_unknown_operation_rejected(self):
        with self.assertRaises(ValueError):
            advance_operation(a_list(), KEY_ABSENT, 10)


class DirectiveTests(unittest.TestCase):
    def test_single_directive_needs_a_key(self):
        with self.assertRaises(ValueError):
            apply_directive(a_list(), "suspend")

    def test_all_directive_rejects_a_key(self):
        with self.assertRaises(ValueError):
            apply_directive(a_list(), "suspend-all", KEY_A)

    def test_unknown_directive_rejected(self):
        with self.assertRaises(ValueError):
            apply_directive(a_list(), "halt", KEY_A)

    def test_suspend_all_returns_one_outcome_per_entry(self):
        self.assertEqual(len(apply_directive(a_list(), "suspend-all")), 3)


class SummaryTests(unittest.TestCase):
    def test_summary_counts_each_state(self):
        summary = list_summary(a_list())
        self.assertEqual(summary["running"], 2)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["total"], 3)

    def test_pending_octets_exclude_completed_entries(self):
        self.assertEqual(list_summary(a_list())["octets_pending"], 600 + 800)

    def test_pending_octets_survive_a_suspension(self):
        ops = a_list()
        suspend_all(ops)
        self.assertEqual(list_summary(ops)["octets_pending"], 1400)


class CampaignTests(unittest.TestCase):
    def test_campaign_applies_directives_in_order(self):
        result = assess_directive_campaign(
            {
                "operations": [op(KEY_A, 1000, 400), op(KEY_B, 800, 0)],
                "directives": [
                    {"directive": "suspend", "key": KEY_A},
                    {"directive": "resume", "key": KEY_A},
                ],
            }
        )
        self.assertEqual([o["outcome"] for o in result["outcomes"]], ["changed", "changed"])

    def test_campaign_flags_a_fully_suspended_list(self):
        result = assess_directive_campaign(
            {
                "operations": [op(KEY_A, 1000, 400), op(KEY_B, 800, 0)],
                "directives": [{"directive": "suspend-all"}],
            }
        )
        self.assertTrue(any("nothing is progressing" in f for f in result["findings"]))

    def test_campaign_counts_redundant_outcomes(self):
        result = assess_directive_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [
                    {"directive": "suspend", "key": KEY_A},
                    {"directive": "suspend", "key": KEY_A},
                ],
            }
        )
        self.assertTrue(any("changed nothing" in f for f in result["findings"]))

    def test_campaign_counts_refused_outcomes(self):
        result = assess_directive_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [{"directive": "resume", "key": KEY_ABSENT}],
            }
        )
        self.assertTrue(any("refused" in f for f in result["findings"]))

    def test_campaign_tags_each_outcome_with_its_directive(self):
        result = assess_directive_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [{"directive": "suspend-all"}],
            }
        )
        self.assertEqual(result["outcomes"][0]["directive"], "suspend-all")

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_directive_campaign({"operations": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_directive_campaign(["operations"])

    def test_malformed_directive_rejected(self):
        with self.assertRaises(ValueError):
            assess_directive_campaign({"operations": [], "directives": ["suspend"]})


if __name__ == "__main__":
    unittest.main()
