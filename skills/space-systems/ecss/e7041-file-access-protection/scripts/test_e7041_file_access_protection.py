"""Contract test for the file access protection leaf (stdlib unittest)."""

import unittest

from e7041_file_access_protection_logic import (
    HANDLE_DOWNLINK,
    HANDLE_NONE,
    HANDLE_UPLINK,
    LOCK_ALREADY_SET,
    LOCK_APPLIED,
    LOCK_REFUSED_UNKNOWN_FILE,
    MAX_NAME_OCTETS,
    OP_COPY_DESTINATION,
    OP_DELETE,
    OP_DOWNLINK,
    OP_MOVE,
    OP_OVERWRITE,
    OP_READ,
    OP_RENAME,
    PERMITTED,
    REFUSED_HELD,
    REFUSED_LOCKED,
    REFUSED_UNKNOWN_FILE,
    UNLOCK_APPLIED,
    UNLOCK_WAS_NOT_LOCKED,
    assess_operation,
    build_protection_table,
    is_destructive,
    is_held,
    lock_file,
    report_protection_state,
    screen_operation_plan,
    set_handle,
    unlock_file,
    validate_file_name,
    validate_operation,
    validate_protected_file,
)


def record(name="EVT-001.DAT", locked=False, handle=HANDLE_NONE):
    return {"name": name, "locked": locked, "handle": handle}


def sample_records():
    return [
        record("EVT-001.DAT"),
        record("EVT-002.DAT", locked=True),
        record("DUMP.BIN", handle=HANDLE_DOWNLINK),
        record("PATCH.IMG", locked=True, handle=HANDLE_UPLINK),
    ]


def sample_table():
    return build_protection_table(sample_records())


class TestValidation(unittest.TestCase):
    def test_empty_file_name_raises(self):
        with self.assertRaises(ValueError):
            validate_file_name("")

    def test_file_name_with_a_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_file_name("logs/EVT.DAT")

    def test_over_long_file_name_raises(self):
        with self.assertRaises(ValueError):
            validate_file_name("A" * (MAX_NAME_OCTETS + 1))

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            validate_operation("defragment")

    def test_unknown_handle_state_raises(self):
        with self.assertRaises(ValueError):
            validate_protected_file(record(handle="busy"))

    def test_non_boolean_lock_raises(self):
        with self.assertRaises(ValueError):
            validate_protected_file(record(locked=1))

    def test_duplicate_file_names_raise(self):
        with self.assertRaises(ValueError):
            build_protection_table([record("A.DAT"), record("A.DAT")])

    def test_lock_and_handle_default_to_unprotected(self):
        parsed = validate_protected_file({"name": "A.DAT"})
        self.assertFalse(parsed["locked"])
        self.assertEqual(parsed["handle"], HANDLE_NONE)


class TestOperationCategories(unittest.TestCase):
    def test_delete_is_destructive(self):
        self.assertTrue(is_destructive(OP_DELETE))

    def test_copy_destination_is_destructive(self):
        self.assertTrue(is_destructive(OP_COPY_DESTINATION))

    def test_read_is_not_destructive(self):
        self.assertFalse(is_destructive(OP_READ))

    def test_downlink_is_not_destructive(self):
        self.assertFalse(is_destructive(OP_DOWNLINK))

    def test_a_handle_means_held(self):
        self.assertTrue(is_held(record(handle=HANDLE_UPLINK)))
        self.assertFalse(is_held(record()))


class TestSingleOperationVerdicts(unittest.TestCase):
    def test_delete_of_an_unprotected_file_is_permitted(self):
        verdict = assess_operation(sample_table(), "EVT-001.DAT", OP_DELETE)
        self.assertEqual(verdict["verdict"], PERMITTED)

    def test_delete_of_a_locked_file_is_refused_by_the_lock(self):
        verdict = assess_operation(sample_table(), "EVT-002.DAT", OP_DELETE)
        self.assertEqual(verdict["verdict"], REFUSED_LOCKED)
        self.assertTrue(verdict["blocked_by_lock"])

    def test_a_locked_file_is_still_readable(self):
        verdict = assess_operation(sample_table(), "EVT-002.DAT", OP_READ)
        self.assertEqual(verdict["verdict"], PERMITTED)

    def test_a_locked_file_is_still_downlinkable(self):
        verdict = assess_operation(sample_table(), "EVT-002.DAT", OP_DOWNLINK)
        self.assertEqual(verdict["verdict"], PERMITTED)

    def test_an_unlocked_but_held_file_refuses_a_rename(self):
        verdict = assess_operation(sample_table(), "DUMP.BIN", OP_RENAME)
        self.assertEqual(verdict["verdict"], REFUSED_HELD)
        self.assertFalse(verdict["blocked_by_lock"])
        self.assertTrue(verdict["blocked_by_handle"])

    def test_a_locked_and_held_file_reports_both_blockers(self):
        verdict = assess_operation(sample_table(), "PATCH.IMG", OP_OVERWRITE)
        self.assertEqual(verdict["verdict"], REFUSED_LOCKED)
        self.assertTrue(verdict["blocked_by_lock"])
        self.assertTrue(verdict["blocked_by_handle"])

    def test_a_move_of_a_held_file_is_refused(self):
        verdict = assess_operation(sample_table(), "DUMP.BIN", OP_MOVE)
        self.assertEqual(verdict["verdict"], REFUSED_HELD)

    def test_an_unknown_file_has_its_own_verdict(self):
        verdict = assess_operation(sample_table(), "GONE.DAT", OP_DELETE)
        self.assertEqual(verdict["verdict"], REFUSED_UNKNOWN_FILE)

    def test_a_refusal_names_a_remedy(self):
        self.assertIn(
            "unlock", assess_operation(sample_table(), "EVT-002.DAT", OP_DELETE)["remedy"]
        )
        self.assertIn(
            "wait", assess_operation(sample_table(), "DUMP.BIN", OP_DELETE)["remedy"]
        )


class TestLockAndUnlock(unittest.TestCase):
    def test_locking_an_unlocked_file_applies_the_lock(self):
        table, outcome = lock_file(sample_table(), "EVT-001.DAT")
        self.assertEqual(outcome, LOCK_APPLIED)
        self.assertTrue(table["EVT-001.DAT"]["locked"])

    def test_locking_an_already_locked_file_is_idempotent(self):
        table, outcome = lock_file(sample_table(), "EVT-002.DAT")
        self.assertEqual(outcome, LOCK_ALREADY_SET)
        self.assertTrue(table["EVT-002.DAT"]["locked"])

    def test_unlocking_a_locked_file_clears_it(self):
        table, outcome = unlock_file(sample_table(), "EVT-002.DAT")
        self.assertEqual(outcome, UNLOCK_APPLIED)
        self.assertFalse(table["EVT-002.DAT"]["locked"])

    def test_unlocking_a_file_that_was_not_locked_is_reported(self):
        _, outcome = unlock_file(sample_table(), "EVT-001.DAT")
        self.assertEqual(outcome, UNLOCK_WAS_NOT_LOCKED)

    def test_locking_an_unknown_file_is_refused(self):
        _, outcome = lock_file(sample_table(), "GONE.DAT")
        self.assertEqual(outcome, LOCK_REFUSED_UNKNOWN_FILE)

    def test_lock_does_not_mutate_the_table_it_was_given(self):
        original = sample_table()
        lock_file(original, "EVT-001.DAT")
        self.assertFalse(original["EVT-001.DAT"]["locked"])

    def test_unlocking_does_not_release_a_transfer_handle(self):
        table, _ = unlock_file(sample_table(), "PATCH.IMG")
        verdict = assess_operation(table, "PATCH.IMG", OP_DELETE)
        self.assertEqual(verdict["verdict"], REFUSED_HELD)

    def test_releasing_the_handle_of_an_unlocked_file_permits_a_delete(self):
        table = set_handle(sample_table(), "DUMP.BIN", HANDLE_NONE)
        self.assertEqual(
            assess_operation(table, "DUMP.BIN", OP_DELETE)["verdict"], PERMITTED
        )

    def test_setting_an_unknown_handle_raises(self):
        with self.assertRaises(ValueError):
            set_handle(sample_table(), "DUMP.BIN", "parked")

    def test_setting_a_handle_on_an_unknown_file_raises(self):
        with self.assertRaises(ValueError):
            set_handle(sample_table(), "GONE.DAT", HANDLE_UPLINK)


class TestReportAndPlan(unittest.TestCase):
    def test_report_counts_locked_held_and_protected(self):
        report = report_protection_state(sample_table())
        self.assertEqual(report["file_count"], 4)
        self.assertEqual(report["locked_count"], 2)
        self.assertEqual(report["held_count"], 2)
        self.assertEqual(report["protected_count"], 3)
        self.assertFalse(report["fully_unprotected"])

    def test_report_rows_are_in_name_order(self):
        names = [r["file_name"] for r in report_protection_state(sample_table())["files"]]
        self.assertEqual(names, sorted(names))

    def test_an_all_clear_repository_reports_fully_unprotected(self):
        report = report_protection_state(build_protection_table([record("A.DAT")]))
        self.assertTrue(report["fully_unprotected"])

    def test_plan_screening_separates_the_two_remedies(self):
        result = screen_operation_plan(
            sample_records(),
            [
                {"file_name": "EVT-001.DAT", "operation": OP_DELETE},
                {"file_name": "EVT-002.DAT", "operation": OP_DELETE},
                {"file_name": "DUMP.BIN", "operation": OP_DELETE},
                {"file_name": "EVT-002.DAT", "operation": OP_READ},
                {"file_name": "GONE.DAT", "operation": OP_DELETE},
            ],
        )
        self.assertEqual(result["permitted_count"], 2)
        self.assertEqual(result["refused_count"], 3)
        self.assertEqual(result["unlock_would_clear"], 1)
        self.assertEqual(result["waiting_would_clear"], 1)
        self.assertFalse(result["plan_executable"])

    def test_a_clean_plan_is_executable(self):
        result = screen_operation_plan(
            [record("A.DAT")], [{"file_name": "A.DAT", "operation": OP_DELETE}]
        )
        self.assertTrue(result["plan_executable"])
        self.assertEqual(result["refusals_by_reason"], {})

    def test_plan_must_be_a_list(self):
        with self.assertRaises(ValueError):
            screen_operation_plan(sample_records(), {"file_name": "A.DAT"})


if __name__ == "__main__":
    unittest.main()
