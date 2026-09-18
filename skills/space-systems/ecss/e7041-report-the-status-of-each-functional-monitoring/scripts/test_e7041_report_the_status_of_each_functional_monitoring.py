"""Contract test for the e7041 functional-monitoring status report leaf."""

import unittest

from e7041_report_the_status_of_each_functional_monitoring_logic import (
    FUNCTIONAL_STATUSES,
    VERDICT_CONSISTENT,
    VERDICT_INCONSISTENT,
    assess_status_report,
    build_status_report,
    check_status_consistency,
    constituent_tally,
    derive_functional_status,
    report_is_complete,
    status_report_entry,
    validate_definition_status,
    validate_store,
)


def constituent(pmid="PM-1", status="within-limits"):
    return {"parameter_monitoring_id": pmid, "checking_status": status}


def definition(fid="FM-POWER", statuses=("within-limits", "within-limits"),
               threshold=2, enabled=True, **kw):
    record = {
        "id": fid,
        "enabled": enabled,
        "constituents": [
            constituent("PM-%d" % (i + 1), status) for i, status in enumerate(statuses)
        ],
        "failing_threshold": threshold,
    }
    record.update(kw)
    return record


def store():
    return [
        definition("FM-POWER", ("within-limits", "within-limits"), 2),
        definition(
            "FM-THERMAL", ("out-of-limits", "within-limits", "unchecked"), 1
        ),
        definition("FM-COMMS", ("unchecked", "unchecked"), 1, enabled=False),
    ]


class TestValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_definition_status(definition())
        self.assertEqual(record["id"], "FM-POWER")
        self.assertEqual(len(record["constituents"]), 2)

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_status("FM-POWER")

    def test_a_missing_enable_flag_raises(self):
        record = definition()
        del record["enabled"]
        with self.assertRaises(ValueError):
            validate_definition_status(record)

    def test_an_empty_constituent_list_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_status(definition(statuses=(), threshold=1))

    def test_a_repeated_constituent_raises(self):
        record = definition()
        record["constituents"][1]["parameter_monitoring_id"] = "PM-1"
        with self.assertRaises(ValueError):
            validate_definition_status(record)

    def test_an_unknown_checking_status_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_status(definition(statuses=("maybe-ok",), threshold=1))

    def test_a_threshold_above_the_constituent_count_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_status(definition(threshold=7))

    def test_an_unknown_declared_status_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_status(definition(declared_status="degraded"))

    def test_a_duplicate_definition_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition("FM-A"), definition("FM-A")])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(definition())


class TestTally(unittest.TestCase):
    def test_a_clean_group_tallies_as_checking(self):
        tally = constituent_tally(definition())
        self.assertEqual(tally["checking"], 2)
        self.assertEqual(tally["out-of-limits"], 0)

    def test_an_invalid_constituent_is_not_checking(self):
        tally = constituent_tally(
            definition(statuses=("invalid", "within-limits"), threshold=1)
        )
        self.assertEqual(tally["invalid"], 1)
        self.assertEqual(tally["checking"], 1)

    def test_unchecked_constituents_are_counted_separately(self):
        tally = constituent_tally(
            definition(statuses=("unchecked", "unchecked"), threshold=1)
        )
        self.assertEqual(tally["unchecked"], 2)
        self.assertEqual(tally["checking"], 0)

    def test_the_total_matches_the_constituent_count(self):
        tally = constituent_tally(
            definition(statuses=("out-of-limits", "invalid", "unchecked"), threshold=1)
        )
        self.assertEqual(tally["total"], 3)


class TestStatusDerivation(unittest.TestCase):
    def test_a_healthy_enabled_group_is_running(self):
        self.assertEqual(derive_functional_status(definition())["status"], "running")

    def test_reaching_the_threshold_makes_the_group_failed(self):
        result = derive_functional_status(
            definition(statuses=("out-of-limits", "out-of-limits"), threshold=2)
        )
        self.assertEqual(result["status"], "failed")

    def test_one_short_of_the_threshold_is_still_running(self):
        result = derive_functional_status(
            definition(statuses=("out-of-limits", "within-limits"), threshold=2)
        )
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["failing_count"], 1)

    def test_a_disabled_group_is_unchecked_however_its_constituents_read(self):
        result = derive_functional_status(
            definition(
                statuses=("out-of-limits", "out-of-limits"), threshold=1, enabled=False
            )
        )
        self.assertEqual(result["status"], "unchecked")
        self.assertEqual(result["failing_count"], 2)

    def test_an_enabled_group_with_nothing_checking_is_unchecked(self):
        result = derive_functional_status(
            definition(statuses=("unchecked", "invalid"), threshold=1)
        )
        self.assertEqual(result["status"], "unchecked")

    def test_an_invalid_constituent_cannot_reach_the_threshold(self):
        result = derive_functional_status(
            definition(statuses=("invalid", "within-limits"), threshold=1)
        )
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["invalid_count"], 1)

    def test_every_derived_status_is_a_known_status(self):
        for record in store():
            self.assertIn(derive_functional_status(record)["status"], FUNCTIONAL_STATUSES)


class TestConsistency(unittest.TestCase):
    def test_a_definition_with_no_declared_status_is_consistent(self):
        self.assertTrue(check_status_consistency(definition())["consistent"])

    def test_an_agreeing_declared_status_is_consistent(self):
        result = check_status_consistency(definition(declared_status="running"))
        self.assertTrue(result["consistent"])

    def test_a_disagreeing_declared_status_is_a_defect(self):
        result = check_status_consistency(definition(declared_status="failed"))
        self.assertFalse(result["consistent"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_disabled_group_hiding_failures_is_reported(self):
        result = check_status_consistency(
            definition(
                statuses=("out-of-limits", "within-limits"), threshold=1, enabled=False
            )
        )
        self.assertFalse(result["consistent"])

    def test_an_enabled_group_with_an_invalid_constituent_is_reported(self):
        result = check_status_consistency(
            definition(statuses=("invalid", "within-limits"), threshold=1)
        )
        self.assertFalse(result["consistent"])

    def test_the_derived_status_is_carried_alongside_the_declared_one(self):
        result = check_status_consistency(definition(declared_status="failed"))
        self.assertEqual(result["declared_status"], "failed")
        self.assertEqual(result["derived_status"], "running")


class TestReportAssembly(unittest.TestCase):
    def test_the_report_covers_every_definition_held(self):
        report = build_status_report(store())
        self.assertEqual(report["definition_count"], 3)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["FM-POWER", "FM-THERMAL", "FM-COMMS"],
        )

    def test_each_entry_carries_the_enable_state(self):
        report = build_status_report(store())
        self.assertEqual(report["enabled_count"], 2)
        self.assertEqual(report["disabled_count"], 1)

    def test_the_status_counts_add_up_to_the_definition_count(self):
        report = build_status_report(store())
        self.assertEqual(sum(report["status_counts"].values()), 3)

    def test_a_failed_group_is_counted_as_failed(self):
        report = build_status_report(store())
        self.assertEqual(report["status_counts"]["failed"], 1)

    def test_an_entry_carries_its_threshold_and_failing_count(self):
        entry = status_report_entry(
            definition(statuses=("out-of-limits", "within-limits"), threshold=2)
        )
        self.assertEqual(entry["failing_threshold"], 2)
        self.assertEqual(entry["failing_count"], 1)

    def test_an_empty_store_reports_nothing(self):
        report = build_status_report([])
        self.assertEqual(report["entries"], [])
        self.assertEqual(report["definition_count"], 0)


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        self.assertTrue(report_is_complete(build_status_report(store()))["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        report = build_status_report(store())
        report["entries"] = report["entries"][:2]
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_wrong_enabled_total_is_detected(self):
        report = build_status_report(store())
        report["enabled_count"] = 9
        result = report_is_complete(report)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        report = build_status_report(store())
        report["definition_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(report)


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_store_reports_consistently(self):
        records = [
            definition("FM-POWER", ("within-limits", "within-limits"), 2),
            definition("FM-THERMAL", ("out-of-limits", "within-limits"), 1),
        ]
        result = assess_status_report(records)
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["findings"], [])

    def test_the_report_always_covers_the_whole_store(self):
        result = assess_status_report(store())
        self.assertTrue(result["covers_whole_store"])
        self.assertEqual(result["held_count"], 3)

    def test_a_disabled_group_hiding_failures_makes_the_report_inconsistent(self):
        records = [
            definition(
                "FM-POWER", ("out-of-limits", "within-limits"), 1, enabled=False
            )
        ]
        result = assess_status_report(records)
        self.assertEqual(result["verdict"], VERDICT_INCONSISTENT)
        self.assertEqual(result["inconsistent_ids"], ["FM-POWER"])

    def test_several_inconsistent_definitions_are_all_named(self):
        records = [
            definition("FM-A", ("out-of-limits",), 1, enabled=False),
            definition("FM-B", ("invalid", "within-limits"), 1),
            definition("FM-C", ("within-limits", "within-limits"), 2),
        ]
        result = assess_status_report(records)
        self.assertEqual(result["inconsistent_ids"], ["FM-A", "FM-B"])

    def test_the_reported_identifiers_follow_store_order(self):
        result = assess_status_report(store())
        self.assertEqual(
            result["reported_ids"], ["FM-POWER", "FM-THERMAL", "FM-COMMS"]
        )

    def test_an_invalid_store_entry_raises_before_any_report(self):
        broken = store()
        broken[0]["failing_threshold"] = 9
        with self.assertRaises(ValueError):
            assess_status_report(broken)

    def test_an_empty_store_is_a_consistent_empty_report(self):
        result = assess_status_report([])
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["reported_ids"], [])


if __name__ == "__main__":
    unittest.main()
