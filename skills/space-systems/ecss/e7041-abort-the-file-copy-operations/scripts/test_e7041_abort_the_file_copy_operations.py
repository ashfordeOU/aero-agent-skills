"""Contract tests for the clause 6.23.5.4 file copy abort logic."""

import unittest

from e7041_abort_the_file_copy_operations_logic import (
    ABORTABLE_STATES,
    abort_all,
    abort_operation,
    abort_report,
    assess_abort_campaign,
    build_operation_list,
    find_operation,
    new_copy_operation,
    partial_target_disposition,
    reclaimed_octets,
)

KEY_A = ("mass-memory", "housekeeping.dat", "downlink-buffer", "housekeeping.dat")
KEY_B = ("mass-memory", "event-log.dat", "downlink-buffer", "event-log.dat")
KEY_C = ("payload-store", "image-042.raw", "downlink-buffer", "image-042.raw")
KEY_ABSENT = ("mass-memory", "absent.dat", "downlink-buffer", "absent.dat")


def op(key, total=1000, copied=0, state="running"):
    return new_copy_operation(key[0], key[1], key[2], key[3], total, copied, state)


def a_list():
    return build_operation_list(
        [op(KEY_A, 1000, 400), op(KEY_B, 800, 0), op(KEY_C, 2000, 1500, "suspended")]
    )


def free_space():
    return {"downlink-buffer": 5000}


class ConstructionTests(unittest.TestCase):
    def test_both_live_states_are_abortable(self):
        self.assertEqual(ABORTABLE_STATES, ("running", "suspended"))

    def test_suspended_operation_is_accepted(self):
        self.assertEqual(op(KEY_A, 100, 10, "suspended")["state"], "suspended")

    def test_fully_copied_operation_rejected_as_no_longer_in_the_list(self):
        with self.assertRaises(ValueError):
            op(KEY_A, total=100, copied=100)

    def test_completed_state_rejected(self):
        with self.assertRaises(ValueError):
            op(KEY_A, 100, 10, "completed")

    def test_blank_repository_rejected(self):
        with self.assertRaises(ValueError):
            new_copy_operation("", "a.dat", "downlink-buffer", "a.dat", 100)

    def test_negative_octets_copied_rejected(self):
        with self.assertRaises(ValueError):
            op(KEY_A, 100, -1)

    def test_duplicate_key_in_list_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_list([op(KEY_A), op(KEY_A)])

    def test_malformed_entry_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_list([{"key": KEY_A}])

    def test_find_needs_a_four_part_key(self):
        with self.assertRaises(ValueError):
            find_operation(a_list(), ("mass-memory",))


class DispositionTests(unittest.TestCase):
    def test_untouched_target_needs_no_deletion(self):
        disposition = partial_target_disposition(op(KEY_B, 800, 0))
        self.assertEqual(disposition["action"], "none")
        self.assertEqual(disposition["octets_reclaimed"], 0)

    def test_partial_target_is_deleted(self):
        disposition = partial_target_disposition(op(KEY_A, 1000, 400))
        self.assertEqual(disposition["action"], "delete-partial-target")
        self.assertEqual(disposition["octets_reclaimed"], 400)

    def test_disposition_needs_the_octet_count(self):
        with self.assertRaises(ValueError):
            partial_target_disposition({"key": KEY_A})


class AbortOneTests(unittest.TestCase):
    def test_abort_removes_the_entry(self):
        ops = a_list()
        outcome = abort_operation(ops, KEY_A)
        self.assertEqual(outcome["outcome"], "aborted")
        self.assertIsNone(find_operation(ops, KEY_A))
        self.assertEqual(len(ops), 2)

    def test_abort_reports_the_octets_discarded(self):
        self.assertEqual(abort_operation(a_list(), KEY_A)["octets_discarded"], 400)

    def test_abort_of_a_suspended_operation_is_allowed(self):
        ops = a_list()
        self.assertEqual(abort_operation(ops, KEY_C)["outcome"], "aborted")

    def test_abort_of_an_unknown_operation_is_refused(self):
        ops = a_list()
        outcome = abort_operation(ops, KEY_ABSENT)
        self.assertEqual(outcome["outcome"], "refused")
        self.assertIn("no copy operation", outcome["reason"])
        self.assertEqual(len(ops), 3)

    def test_refused_abort_discards_no_octets(self):
        self.assertEqual(abort_operation(a_list(), KEY_ABSENT)["octets_discarded"], 0)

    def test_abort_returns_the_partial_octets_to_free_space(self):
        ops = a_list()
        repos = free_space()
        abort_operation(ops, KEY_A, repos)
        self.assertEqual(repos["downlink-buffer"], 5400)

    def test_abort_of_an_untouched_target_returns_nothing(self):
        repos = free_space()
        abort_operation(a_list(), KEY_B, repos)
        self.assertEqual(repos["downlink-buffer"], 5000)

    def test_abort_against_an_unknown_repository_rejected(self):
        with self.assertRaises(ValueError):
            abort_operation(a_list(), KEY_A, {"payload-store": 10})

    def test_abort_twice_is_refused_the_second_time(self):
        ops = a_list()
        abort_operation(ops, KEY_A)
        self.assertEqual(abort_operation(ops, KEY_A)["outcome"], "refused")


class AbortAllTests(unittest.TestCase):
    def test_abort_all_empties_the_list(self):
        ops = a_list()
        outcomes = abort_all(ops)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual(ops, [])

    def test_abort_all_returns_every_partial_octet(self):
        ops = a_list()
        repos = free_space()
        abort_all(ops, repos)
        self.assertEqual(repos["downlink-buffer"], 5000 + 400 + 1500)

    def test_abort_all_on_an_empty_list_does_nothing(self):
        ops = []
        self.assertEqual(abort_all(ops), [])

    def test_reclaimed_octets_sums_the_dispositions(self):
        self.assertEqual(reclaimed_octets(abort_all(a_list())), 1900)

    def test_reclaimed_octets_rejects_a_malformed_outcome(self):
        with self.assertRaises(ValueError):
            reclaimed_octets([{"outcome": "aborted"}])


class ReportTests(unittest.TestCase):
    def test_report_counts_aborted_and_remaining(self):
        ops = a_list()
        outcomes = [abort_operation(ops, KEY_A)]
        report = abort_report(outcomes, ops)
        self.assertEqual(report["aborted"], 1)
        self.assertEqual(report["remaining"], 2)

    def test_report_names_the_partial_targets_deleted(self):
        ops = a_list()
        outcomes = abort_all(ops)
        report = abort_report(outcomes, ops)
        self.assertEqual(sorted(report["partial_targets_deleted"]), sorted([KEY_A, KEY_C]))

    def test_report_separates_discarded_from_reclaimed(self):
        ops = a_list()
        outcomes = abort_all(ops)
        report = abort_report(outcomes, ops)
        self.assertEqual(report["octets_discarded"], 1900)
        self.assertEqual(report["octets_reclaimed"], 1900)

    def test_report_counts_refusals(self):
        ops = a_list()
        outcomes = [abort_operation(ops, KEY_ABSENT)]
        self.assertEqual(abort_report(outcomes, ops)["refused"], 1)

    def test_report_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            abort_report({"outcome": "aborted"}, [])


class CampaignTests(unittest.TestCase):
    def test_campaign_aborts_one_named_operation(self):
        result = assess_abort_campaign(
            {
                "operations": [op(KEY_A, 1000, 400), op(KEY_B, 800, 0)],
                "directives": [{"directive": "abort", "key": KEY_A}],
            }
        )
        self.assertEqual(result["report"]["aborted"], 1)
        self.assertEqual(result["report"]["remaining"], 1)

    def test_campaign_abort_all_clears_the_list(self):
        result = assess_abort_campaign(
            {
                "operations": [op(KEY_A, 1000, 400), op(KEY_B, 800, 0)],
                "directives": [{"directive": "abort-all"}],
            }
        )
        self.assertEqual(result["operations"], [])

    def test_campaign_flags_discarded_effort(self):
        result = assess_abort_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [{"directive": "abort", "key": KEY_A}],
            }
        )
        self.assertTrue(any("discarded" in f for f in result["findings"]))

    def test_campaign_flags_deleted_partial_targets(self):
        result = assess_abort_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [{"directive": "abort-all"}],
            }
        )
        self.assertTrue(any("partial target file" in f for f in result["findings"]))

    def test_campaign_flags_an_unheld_operation(self):
        result = assess_abort_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [{"directive": "abort", "key": KEY_ABSENT}],
            }
        )
        self.assertTrue(any("does not hold" in f for f in result["findings"]))

    def test_campaign_updates_the_repository_free_space(self):
        result = assess_abort_campaign(
            {
                "operations": [op(KEY_A, 1000, 400)],
                "directives": [{"directive": "abort-all"}],
                "repositories": free_space(),
            }
        )
        self.assertEqual(result["repositories"]["downlink-buffer"], 5400)

    def test_abort_directive_without_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_abort_campaign(
                {"operations": [op(KEY_A)], "directives": [{"directive": "abort"}]}
            )

    def test_abort_all_with_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_abort_campaign(
                {
                    "operations": [op(KEY_A)],
                    "directives": [{"directive": "abort-all", "key": KEY_A}],
                }
            )

    def test_unknown_directive_rejected(self):
        with self.assertRaises(ValueError):
            assess_abort_campaign(
                {"operations": [op(KEY_A)], "directives": [{"directive": "suspend", "key": KEY_A}]}
            )

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_abort_campaign({"operations": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_abort_campaign(["operations"])

    def test_non_sequence_directives_rejected(self):
        with self.assertRaises(ValueError):
            assess_abort_campaign({"operations": [], "directives": {"directive": "abort-all"}})


if __name__ == "__main__":
    unittest.main()
