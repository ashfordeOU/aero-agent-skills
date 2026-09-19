"""Contract test for the e7041 execution-status-report leaf."""

import unittest

from e7041_report_the_execution_status_of_each_request_sequence_logic import (
    EXECUTION_STATUSES,
    VERDICT_CONSISTENT,
    VERDICT_INCONSISTENT,
    assess_execution_status_report,
    build_execution_status_report,
    check_status_consistency,
    derive_execution_status,
    reject_selector,
    report_is_complete,
    status_report_entry,
    validate_engine,
    validate_sequence,
    validate_store,
)


def sequence(sid="RS-SLEW", load_state="loaded", request_count=10,
             released_count=0, **kw):
    record = {
        "id": sid,
        "load_state": load_state,
        "request_count": request_count,
        "released_count": released_count,
    }
    record.update(kw)
    return record


def store():
    return [
        sequence("RS-SLEW", "loaded", 10, 3),
        sequence("RS-IDLE", "loaded", 5, 0),
        sequence("RS-STOPPED", "loaded", 8, 2),
        sequence("RS-DONE", "loaded", 4, 4),
        sequence("RS-BLANK", "empty", 0, 0),
        sequence("RS-ARRIVING", "under-load", 6, 0),
    ]


def engine(running=("RS-SLEW",)):
    return {"running_ids": list(running)}


class TestValidation(unittest.TestCase):
    def test_a_valid_sequence_normalizes(self):
        self.assertEqual(validate_sequence(sequence())["request_count"], 10)

    def test_a_non_mapping_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(None)

    def test_a_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(sid=" "))

    def test_an_unknown_load_state_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="thawing"))

    def test_releasing_more_than_the_body_holds_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(request_count=2, released_count=3))

    def test_an_empty_slot_carrying_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="empty", request_count=4))

    def test_a_loaded_slot_with_no_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(request_count=0))

    def test_an_unloaded_slot_reporting_releases_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="under-load", released_count=2))

    def test_an_unknown_declared_status_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(declared_status="warming"))

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence("RS-A"), sequence("RS-A")])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(sequence())


class TestEngine(unittest.TestCase):
    def test_a_valid_running_set_normalizes(self):
        self.assertEqual(validate_engine(engine(), store())["running_ids"],
                         ("RS-SLEW",))

    def test_a_non_mapping_engine_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(["RS-SLEW"], store())

    def test_a_non_list_running_set_raises(self):
        with self.assertRaises(ValueError):
            validate_engine({"running_ids": "RS-SLEW"}, store())

    def test_running_a_sequence_the_store_lacks_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(("RS-GHOST",)), store())

    def test_running_a_sequence_that_is_not_loaded_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(("RS-BLANK",)), store())

    def test_a_repeated_running_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(("RS-SLEW", "RS-SLEW")), store())

    def test_an_empty_running_set_is_valid(self):
        self.assertEqual(validate_engine(engine(()), store())["running_ids"], ())


class TestCoverage(unittest.TestCase):
    def test_an_identifier_list_is_refused(self):
        with self.assertRaises(ValueError):
            reject_selector(["RS-SLEW"])

    def test_no_selector_is_accepted(self):
        self.assertIsNone(reject_selector(None))

    def test_the_report_builder_refuses_a_selector(self):
        with self.assertRaises(ValueError):
            build_execution_status_report(store(), engine(), selector=["RS-SLEW"])

    def test_the_assessment_refuses_a_selector(self):
        with self.assertRaises(ValueError):
            assess_execution_status_report(store(), engine(), selector=[])

    def test_the_report_covers_every_sequence_held(self):
        result = assess_execution_status_report(store(), engine())
        self.assertTrue(result["covers_whole_store"])
        self.assertEqual(result["held_count"], 6)


class TestDerivation(unittest.TestCase):
    def test_a_sequence_the_engine_runs_is_executing(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-SLEW", "loaded", 10, 3), ("RS-SLEW",)),
            "executing",
        )

    def test_a_loaded_sequence_with_no_releases_is_inactive(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-IDLE", "loaded", 5, 0), ()),
            "inactive",
        )

    def test_a_part_released_sequence_that_stopped_is_aborted(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-STOPPED", "loaded", 8, 2), ()),
            "aborted",
        )

    def test_a_fully_released_sequence_that_stopped_is_completed(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-DONE", "loaded", 4, 4), ()),
            "completed",
        )

    def test_an_empty_slot_is_not_loaded(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-BLANK", "empty", 0, 0), ()),
            "not-loaded",
        )

    def test_a_slot_under_load_is_loading(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-ARRIVING", "under-load", 6, 0), ()),
            "loading",
        )

    def test_the_engine_outranks_the_progress_counters(self):
        self.assertEqual(
            derive_execution_status(sequence("RS-DONE", "loaded", 4, 4), ("RS-DONE",)),
            "executing",
        )

    def test_every_derived_status_is_a_known_status(self):
        for record in store():
            self.assertIn(derive_execution_status(record, ("RS-SLEW",)),
                          EXECUTION_STATUSES)

    def test_a_non_list_running_set_raises(self):
        with self.assertRaises(ValueError):
            derive_execution_status(sequence(), "RS-SLEW")


class TestEntries(unittest.TestCase):
    def test_an_entry_carries_the_identifier_and_status(self):
        entry = status_report_entry(sequence("RS-SLEW", "loaded", 10, 3), ("RS-SLEW",))
        self.assertEqual(entry["id"], "RS-SLEW")
        self.assertEqual(entry["status"], "executing")

    def test_an_entry_carries_what_is_still_pending(self):
        entry = status_report_entry(sequence("RS-SLEW", "loaded", 10, 3), ("RS-SLEW",))
        self.assertEqual(entry["pending_count"], 7)

    def test_only_a_running_entry_is_marked_running(self):
        entry = status_report_entry(sequence("RS-IDLE", "loaded", 5, 0), ("RS-SLEW",))
        self.assertFalse(entry["running"])


class TestConsistency(unittest.TestCase):
    def test_a_matching_declared_status_is_consistent(self):
        record = sequence("RS-IDLE", "loaded", 5, 0, declared_status="inactive")
        self.assertTrue(check_status_consistency(record, ())["consistent"])

    def test_a_drifted_declared_status_is_caught(self):
        record = sequence("RS-IDLE", "loaded", 5, 0, declared_status="executing")
        result = check_status_consistency(record, ())
        self.assertFalse(result["consistent"])
        self.assertEqual(result["derived_status"], "inactive")

    def test_no_declared_status_is_consistent_by_default(self):
        self.assertTrue(check_status_consistency(sequence(), ())["consistent"])

    def test_an_aborted_sequence_raises_a_recovery_finding(self):
        record = sequence("RS-STOPPED", "loaded", 8, 2)
        findings = check_status_consistency(record, ())["findings"]
        self.assertTrue(any("not recalled" in text for text in findings))


class TestReport(unittest.TestCase):
    def test_one_entry_per_sequence_held(self):
        self.assertEqual(build_execution_status_report(store(), engine())["sequence_count"], 6)

    def test_the_entries_follow_store_order(self):
        report = build_execution_status_report(store(), engine())
        self.assertEqual(report["entries"][0]["id"], "RS-SLEW")
        self.assertEqual(report["entries"][-1]["id"], "RS-ARRIVING")

    def test_the_status_counts_add_up_to_the_sequence_count(self):
        report = build_execution_status_report(store(), engine())
        self.assertEqual(sum(report["status_counts"].values()), report["sequence_count"])

    def test_the_executing_total_matches_the_engine(self):
        self.assertEqual(build_execution_status_report(store(), engine())["executing_count"], 1)

    def test_an_empty_store_gives_an_empty_report(self):
        report = build_execution_status_report([], {"running_ids": []})
        self.assertEqual(report["sequence_count"], 0)

    def test_a_consistent_report_is_complete(self):
        self.assertTrue(report_is_complete(build_execution_status_report(store(), engine()))["complete"])

    def test_a_truncated_report_is_caught(self):
        report = build_execution_status_report(store(), engine())
        report["entries"] = report["entries"][:3]
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_miscounted_executing_total_is_caught(self):
        report = build_execution_status_report(store(), engine())
        report["executing_count"] = 4
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete("status")

    def test_a_report_without_a_count_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete({"entries": []})


class TestAssessment(unittest.TestCase):
    def test_a_clean_store_reports_consistent(self):
        records = [sequence("RS-IDLE", "loaded", 5, 0)]
        result = assess_execution_status_report(records, {"running_ids": []})
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)

    def test_a_drifted_declared_status_makes_the_report_inconsistent(self):
        records = [sequence("RS-IDLE", "loaded", 5, 0, declared_status="completed")]
        result = assess_execution_status_report(records, {"running_ids": []})
        self.assertEqual(result["verdict"], VERDICT_INCONSISTENT)
        self.assertEqual(result["inconsistent_ids"], ["RS-IDLE"])

    def test_the_reported_identifiers_follow_store_order(self):
        result = assess_execution_status_report(store(), engine())
        self.assertEqual(result["reported_ids"][:2], ["RS-SLEW", "RS-IDLE"])

    def test_the_running_identifiers_are_carried_through(self):
        self.assertEqual(assess_execution_status_report(store(), engine())["running_ids"],
                         ["RS-SLEW"])

    def test_an_invalid_store_raises_before_any_report(self):
        broken = store()
        broken[0]["released_count"] = 99
        with self.assertRaises(ValueError):
            assess_execution_status_report(broken, engine())

    def test_an_engine_disagreeing_with_the_store_raises(self):
        with self.assertRaises(ValueError):
            assess_execution_status_report(store(), engine(("RS-ARRIVING",)))

    def test_an_empty_store_is_a_consistent_empty_report(self):
        result = assess_execution_status_report([], {"running_ids": []})
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["reported_ids"], [])


if __name__ == "__main__":
    unittest.main()
