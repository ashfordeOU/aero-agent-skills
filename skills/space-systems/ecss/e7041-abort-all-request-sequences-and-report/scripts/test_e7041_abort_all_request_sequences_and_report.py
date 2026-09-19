"""Contract test for the e7041 abort-all-request-sequences-and-report leaf."""

import unittest

from e7041_abort_all_request_sequences_and_report_logic import (
    OUTCOME_ABORTED,
    OUTCOME_ABORT_FAILED,
    VERDICT_SWEEP_COMPLETE,
    VERDICT_SWEEP_PARTIAL,
    abort_one,
    apply_abort_all,
    assess_abort_all,
    build_abort_all_report,
    executing_sequences,
    reject_selector,
    report_is_complete,
    validate_sequence,
    validate_store,
)


def sequence(sid="RS-SLEW", load_state="loaded", execution_state="executing",
             request_count=10, released_count=4, **kw):
    record = {
        "id": sid,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "released_count": released_count,
    }
    record.update(kw)
    return record


def store():
    return [
        sequence("RS-SLEW", request_count=10, released_count=4),
        sequence("RS-IDLE", execution_state="inactive", request_count=5,
                 released_count=0),
        sequence("RS-THERMAL", request_count=6, released_count=0),
        sequence("RS-DONE", execution_state="completed", request_count=3,
                 released_count=3),
    ]


def store_with_fault():
    records = store()
    records[0]["abort_fault"] = "engine channel unresponsive"
    return records


class TestValidation(unittest.TestCase):
    def test_a_valid_sequence_normalizes(self):
        self.assertEqual(validate_sequence(sequence())["released_count"], 4)

    def test_a_non_mapping_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(42)

    def test_an_unknown_execution_state_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(execution_state="stalling"))

    def test_releasing_more_than_the_body_holds_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(request_count=2, released_count=5))

    def test_executing_while_not_loaded_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="empty", request_count=0,
                                       released_count=0))

    def test_an_inactive_sequence_with_released_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(execution_state="inactive",
                                       released_count=3))

    def test_a_blank_abort_fault_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(abort_fault="   "))

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence("RS-A"), sequence("RS-A")])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(sequence())


class TestCoverage(unittest.TestCase):
    def test_an_identifier_list_is_refused(self):
        with self.assertRaises(ValueError):
            reject_selector(["RS-SLEW"])

    def test_an_empty_identifier_list_is_still_a_list(self):
        with self.assertRaises(ValueError):
            reject_selector([])

    def test_no_selector_is_accepted(self):
        self.assertIsNone(reject_selector(None))

    def test_the_report_builder_refuses_a_selector(self):
        with self.assertRaises(ValueError):
            build_abort_all_report(store(), selector=["RS-SLEW"])

    def test_the_assessment_refuses_a_selector(self):
        with self.assertRaises(ValueError):
            assess_abort_all(store(), selector=["RS-THERMAL"])

    def test_only_executing_sequences_are_in_scope(self):
        self.assertEqual(
            [record["id"] for record in executing_sequences(store())],
            ["RS-SLEW", "RS-THERMAL"],
        )

    def test_the_sweep_covers_every_executing_sequence(self):
        result = assess_abort_all(store())
        self.assertTrue(result["covers_every_executing_sequence"])
        self.assertEqual(result["executing_before"], 2)


class TestAbortOne(unittest.TestCase):
    def test_a_clean_abort_discards_the_pending_requests(self):
        self.assertEqual(abort_one(sequence())["discarded_count"], 6)

    def test_a_clean_abort_reports_the_step_reached(self):
        self.assertEqual(abort_one(sequence())["step_reached"], 4)

    def test_a_faulted_abort_discards_nothing(self):
        item = abort_one(sequence(abort_fault="engine channel unresponsive"))
        self.assertEqual(item["outcome"], OUTCOME_ABORT_FAILED)
        self.assertEqual(item["discarded_count"], 0)

    def test_a_faulted_abort_names_the_fault(self):
        item = abort_one(sequence(abort_fault="engine channel unresponsive"))
        self.assertEqual(item["fault"], "engine channel unresponsive")

    def test_a_non_executing_sequence_is_not_part_of_the_sweep(self):
        with self.assertRaises(ValueError):
            abort_one(sequence(execution_state="inactive", released_count=0))


class TestReport(unittest.TestCase):
    def test_one_entry_per_executing_sequence(self):
        report = build_abort_all_report(store())
        self.assertEqual(report["entry_count"], 2)

    def test_a_non_executing_sequence_gets_no_entry(self):
        ids = [item["sequence_id"] for item in build_abort_all_report(store())["entries"]]
        self.assertNotIn("RS-IDLE", ids)

    def test_the_entries_follow_store_order(self):
        report = build_abort_all_report(store())
        self.assertEqual(
            [item["sequence_id"] for item in report["entries"]],
            ["RS-SLEW", "RS-THERMAL"],
        )

    def test_the_totals_come_from_the_entries(self):
        report = build_abort_all_report(store())
        self.assertEqual(report["aborted_count"], 2)
        self.assertEqual(report["discarded_total"], 12)

    def test_a_fault_on_one_sequence_does_not_stop_the_others(self):
        report = build_abort_all_report(store_with_fault())
        self.assertEqual(report["entry_count"], 2)
        self.assertEqual(report["aborted_count"], 1)
        self.assertEqual(report["failed_count"], 1)

    def test_an_empty_store_gives_an_empty_report(self):
        report = build_abort_all_report([])
        self.assertEqual(report["entry_count"], 0)
        self.assertEqual(report["aborted_count"], 0)

    def test_a_consistent_report_is_complete(self):
        self.assertTrue(report_is_complete(build_abort_all_report(store()))["complete"])

    def test_a_truncated_report_is_caught(self):
        report = build_abort_all_report(store())
        report["entries"] = report["entries"][:1]
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_miscounted_failure_total_is_caught(self):
        report = build_abort_all_report(store_with_fault())
        report["failed_count"] = 0
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete("abort-all")

    def test_a_report_without_a_count_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete({"entries": []})


class TestApply(unittest.TestCase):
    def test_every_aborted_sequence_leaves_the_executing_state(self):
        updated = apply_abort_all(store())
        self.assertEqual(updated[0]["execution_state"], "aborted")
        self.assertEqual(updated[2]["execution_state"], "aborted")

    def test_a_non_executing_sequence_is_untouched(self):
        updated = apply_abort_all(store())
        self.assertEqual(updated[1]["execution_state"], "inactive")
        self.assertEqual(updated[3]["execution_state"], "completed")

    def test_a_faulted_sequence_stays_executing(self):
        updated = apply_abort_all(store_with_fault())
        self.assertEqual(updated[0]["execution_state"], "executing")

    def test_an_aborted_sequence_keeps_its_body(self):
        updated = apply_abort_all(store())
        self.assertTrue(updated[0]["reactivatable"])

    def test_apply_refuses_a_selector(self):
        with self.assertRaises(ValueError):
            apply_abort_all(store(), selector=["RS-SLEW"])


class TestAssessment(unittest.TestCase):
    def test_a_clean_sweep_is_complete(self):
        result = assess_abort_all(store())
        self.assertEqual(result["verdict"], VERDICT_SWEEP_COMPLETE)
        self.assertTrue(result["swept"])

    def test_a_clean_sweep_leaves_nothing_executing(self):
        self.assertEqual(assess_abort_all(store())["still_executing"], [])

    def test_a_faulted_sweep_is_partial(self):
        result = assess_abort_all(store_with_fault())
        self.assertEqual(result["verdict"], VERDICT_SWEEP_PARTIAL)
        self.assertFalse(result["swept"])

    def test_a_faulted_sweep_names_what_is_still_running(self):
        self.assertEqual(assess_abort_all(store_with_fault())["still_executing"],
                         ["RS-SLEW"])

    def test_a_faulted_sweep_still_aborts_the_rest(self):
        updated = assess_abort_all(store_with_fault())["resulting_store"]
        self.assertEqual(updated[2]["execution_state"], "aborted")

    def test_a_fault_reaches_the_findings(self):
        findings = assess_abort_all(store_with_fault())["findings"]
        self.assertTrue(any("did not abort" in text for text in findings))

    def test_released_requests_raise_a_recovery_finding(self):
        findings = assess_abort_all(store())["findings"]
        self.assertTrue(any("does not recall" in text for text in findings))

    def test_a_sweep_with_nothing_released_raises_no_recovery_finding(self):
        records = [sequence("RS-CLEAN", released_count=0)]
        self.assertEqual(assess_abort_all(records)["findings"], [])

    def test_the_swept_identifiers_follow_store_order(self):
        self.assertEqual(assess_abort_all(store())["swept_ids"],
                         ["RS-SLEW", "RS-THERMAL"])

    def test_an_empty_store_is_a_complete_empty_sweep(self):
        result = assess_abort_all([])
        self.assertEqual(result["verdict"], VERDICT_SWEEP_COMPLETE)
        self.assertEqual(result["swept_ids"], [])

    def test_an_invalid_store_raises_before_any_sweep(self):
        broken = store()
        broken[0]["released_count"] = 99
        with self.assertRaises(ValueError):
            assess_abort_all(broken)


if __name__ == "__main__":
    unittest.main()
