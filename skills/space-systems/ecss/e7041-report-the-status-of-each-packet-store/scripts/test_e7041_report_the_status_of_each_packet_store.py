"""Contract test for the e7041 packet-store status report leaf."""

import unittest

from e7041_report_the_status_of_each_packet_store_logic import (
    ACTIVITY_BOTH,
    ACTIVITY_IDLE,
    ACTIVITY_RETRIEVING,
    ACTIVITY_STORING,
    OPEN_INACTIVE,
    OPEN_IN_PROGRESS,
    OPEN_SUSPENDED,
    RANGE_INACTIVE,
    RANGE_IN_PROGRESS,
    STORAGE_OFF,
    STORAGE_ON,
    VALID_ACTIVITIES,
    VERDICT_CONSISTENT,
    VERDICT_INCONSISTENT,
    assess_packet_store_status,
    build_status_report,
    check_status_consistency,
    derive_activity,
    is_retrieving,
    report_is_complete,
    status_report_entry,
    validate_packet_store,
    validate_store,
)


def store(store_id="PS-SCIENCE", storage=STORAGE_OFF, open_state=OPEN_INACTIVE,
          range_state=RANGE_INACTIVE, packets=0, **kw):
    record = {
        "id": store_id,
        "storage_status": storage,
        "open_retrieval_state": open_state,
        "range_retrieval_state": range_state,
        "packet_count": packets,
    }
    record.update(kw)
    return record


def stores():
    return [
        store("PS-SCIENCE", STORAGE_ON, packets=120),
        store("PS-EVENTS", STORAGE_ON, open_state=OPEN_IN_PROGRESS, packets=40),
        store("PS-DIAG", STORAGE_OFF, range_state=RANGE_IN_PROGRESS, packets=7),
    ]


class TestValidation(unittest.TestCase):
    def test_a_valid_store_normalizes(self):
        record = validate_packet_store(store())
        self.assertEqual(record["id"], "PS-SCIENCE")
        self.assertEqual(record["packet_count"], 0)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store("PS-SCIENCE")

    def test_a_missing_storage_status_raises(self):
        record = store()
        del record["storage_status"]
        with self.assertRaises(ValueError):
            validate_packet_store(record)

    def test_an_unknown_storage_status_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(storage="paused"))

    def test_an_unknown_open_retrieval_state_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(open_state="draining"))

    def test_both_retrieval_kinds_at_once_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(
                store(open_state=OPEN_IN_PROGRESS, range_state=RANGE_IN_PROGRESS)
            )

    def test_a_negative_packet_count_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(packets=-1))

    def test_a_boolean_packet_count_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(packets=True))

    def test_an_unknown_declared_activity_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(declared_activity="recording"))

    def test_a_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store([store("PS-A"), store("PS-A")])

    def test_an_empty_store_set_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_set_raises(self):
        with self.assertRaises(ValueError):
            validate_store(store())


class TestActivityDerivation(unittest.TestCase):
    def test_storage_off_and_no_retrieval_is_idle(self):
        self.assertEqual(derive_activity(store())["activity"], ACTIVITY_IDLE)

    def test_storage_on_and_no_retrieval_is_storing(self):
        self.assertEqual(
            derive_activity(store(storage=STORAGE_ON))["activity"], ACTIVITY_STORING
        )

    def test_storage_off_with_a_range_retrieval_is_retrieving(self):
        result = derive_activity(store(range_state=RANGE_IN_PROGRESS))
        self.assertEqual(result["activity"], ACTIVITY_RETRIEVING)

    def test_storage_on_with_an_open_retrieval_is_both(self):
        result = derive_activity(
            store(storage=STORAGE_ON, open_state=OPEN_IN_PROGRESS)
        )
        self.assertEqual(result["activity"], ACTIVITY_BOTH)

    def test_a_suspended_open_retrieval_still_counts_as_retrieving(self):
        self.assertTrue(is_retrieving(store(open_state=OPEN_SUSPENDED)))

    def test_every_derived_activity_is_a_known_activity(self):
        for record in stores():
            self.assertIn(derive_activity(record)["activity"], VALID_ACTIVITIES)


class TestConsistency(unittest.TestCase):
    def test_a_store_with_no_declared_activity_is_consistent(self):
        self.assertTrue(check_status_consistency(store())["consistent"])

    def test_an_agreeing_declared_activity_is_consistent(self):
        record = store(storage=STORAGE_ON, declared_activity=ACTIVITY_STORING)
        self.assertTrue(check_status_consistency(record)["consistent"])

    def test_a_disagreeing_declared_activity_is_a_defect(self):
        record = store(storage=STORAGE_ON, declared_activity=ACTIVITY_IDLE)
        result = check_status_consistency(record)
        self.assertFalse(result["consistent"])
        self.assertEqual(result["derived_activity"], ACTIVITY_STORING)

    def test_a_dormant_store_holding_packets_is_surfaced(self):
        result = check_status_consistency(store(packets=500))
        self.assertFalse(result["consistent"])
        self.assertIn("dormant", result["findings"][0])

    def test_a_dormant_empty_store_is_not_surfaced(self):
        self.assertTrue(check_status_consistency(store(packets=0))["consistent"])

    def test_storage_off_with_a_suspended_retrieval_is_surfaced(self):
        result = check_status_consistency(store(open_state=OPEN_SUSPENDED))
        self.assertFalse(result["consistent"])


class TestReportAssembly(unittest.TestCase):
    def test_the_report_covers_every_store_held(self):
        report = build_status_report(stores())
        self.assertEqual(report["store_count"], 3)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"],
        )

    def test_each_entry_carries_both_retrieval_states(self):
        entry = status_report_entry(stores()[2])
        self.assertEqual(entry["open_retrieval_state"], OPEN_INACTIVE)
        self.assertEqual(entry["range_retrieval_state"], RANGE_IN_PROGRESS)

    def test_the_storing_total_counts_only_stores_switched_on(self):
        self.assertEqual(build_status_report(stores())["storing_count"], 2)

    def test_the_retrieving_total_counts_either_retrieval_kind(self):
        self.assertEqual(build_status_report(stores())["retrieving_count"], 2)

    def test_the_activity_counts_add_up_to_the_store_count(self):
        report = build_status_report(stores())
        self.assertEqual(sum(report["activity_counts"].values()), 3)

    def test_an_empty_store_set_reports_nothing(self):
        report = build_status_report([])
        self.assertEqual(report["entries"], [])
        self.assertEqual(report["store_count"], 0)


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        self.assertTrue(report_is_complete(build_status_report(stores()))["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        report = build_status_report(stores())
        report["entries"] = report["entries"][:1]
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_wrong_storing_total_is_detected(self):
        report = build_status_report(stores())
        report["storing_count"] = 9
        result = report_is_complete(report)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        report = build_status_report(stores())
        report["store_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(report)


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_store_set_reports_consistently(self):
        records = [
            store("PS-SCIENCE", STORAGE_ON, packets=120),
            store("PS-EVENTS", STORAGE_ON, open_state=OPEN_IN_PROGRESS, packets=40),
        ]
        result = assess_packet_store_status(records)
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["findings"], [])

    def test_the_report_always_covers_every_store(self):
        result = assess_packet_store_status(stores())
        self.assertTrue(result["covers_every_store"])
        self.assertEqual(result["held_count"], 3)

    def test_a_dormant_loaded_store_makes_the_report_inconsistent(self):
        result = assess_packet_store_status([store("PS-OLD", packets=90)])
        self.assertEqual(result["verdict"], VERDICT_INCONSISTENT)
        self.assertEqual(result["inconsistent_ids"], ["PS-OLD"])

    def test_several_inconsistent_stores_are_all_named(self):
        records = [
            store("PS-A", packets=10),
            store("PS-B", STORAGE_ON, declared_activity=ACTIVITY_IDLE),
            store("PS-C", STORAGE_ON, packets=3),
        ]
        result = assess_packet_store_status(records)
        self.assertEqual(result["inconsistent_ids"], ["PS-A", "PS-B"])

    def test_the_reported_identifiers_follow_the_held_order(self):
        result = assess_packet_store_status(stores())
        self.assertEqual(
            result["reported_ids"], ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"]
        )

    def test_an_invalid_store_raises_before_any_report(self):
        broken = stores()
        broken[0]["storage_status"] = "paused"
        with self.assertRaises(ValueError):
            assess_packet_store_status(broken)

    def test_an_empty_store_set_is_a_consistent_empty_report(self):
        result = assess_packet_store_status([])
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["reported_ids"], [])


if __name__ == "__main__":
    unittest.main()
