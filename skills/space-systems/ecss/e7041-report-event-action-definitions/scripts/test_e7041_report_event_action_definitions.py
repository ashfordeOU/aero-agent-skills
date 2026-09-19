"""Contract test for the e7041 event-action definition report leaf."""

import unittest

from e7041_report_event_action_definitions_logic import (
    VERDICT_FAILED_START,
    VERDICT_INCOMPLETE,
    VERDICT_REPORTED,
    assess_definition_report,
    build_definition_report,
    definition_report_entry,
    failure_notifications,
    grade_received_report,
    report_is_complete,
    resolve_request,
    scoped_store,
    validate_action,
    validate_event_action_definition,
    validate_request,
    validate_store,
)


def action(tc_id="TC-SAFE-MODE", target="AP-AOCS", arguments=()):
    return {
        "telecommand_id": tc_id,
        "target_application_process_id": target,
        "arguments": list(arguments),
    }


def definition(apid="AP-PWR", event_id="EV-UNDERVOLT", enabled=True, act=None):
    return {
        "application_process_id": apid,
        "event_definition_id": event_id,
        "enabled": enabled,
        "action": act if act is not None else action(),
    }


def store():
    return [
        definition("AP-PWR", "EV-UNDERVOLT", True, action("TC-SHED-LOAD")),
        definition("AP-PWR", "EV-OVERCURRENT", False, action("TC-OPEN-RELAY")),
        definition("AP-THM", "EV-UNDERVOLT", True, action("TC-HEATER-ON")),
    ]


class TestValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_event_action_definition(definition())
        self.assertEqual(record["action"]["telecommand_id"], "TC-SAFE-MODE")

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_event_action_definition("AP-PWR")

    def test_a_definition_with_no_action_raises(self):
        record = definition()
        del record["action"]
        with self.assertRaises(ValueError):
            validate_event_action_definition(record)

    def test_an_action_without_a_telecommand_raises(self):
        with self.assertRaises(ValueError):
            validate_action({"target_application_process_id": "AP-AOCS"}, "AP-PWR/EV-X")

    def test_an_action_with_non_list_arguments_raises(self):
        with self.assertRaises(ValueError):
            validate_action(
                {
                    "telecommand_id": "TC-X",
                    "target_application_process_id": "AP-AOCS",
                    "arguments": "one",
                },
                "AP-PWR/EV-X",
            )

    def test_a_missing_enable_flag_raises(self):
        record = definition()
        del record["enabled"]
        with self.assertRaises(ValueError):
            validate_event_action_definition(record)

    def test_a_repeated_process_and_event_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition("AP-PWR", "EV-X"), definition("AP-PWR", "EV-X")])

    def test_the_same_event_under_two_processes_is_two_definitions(self):
        self.assertEqual(
            len(validate_store([definition("AP-PWR", "EV-X"), definition("AP-THM", "EV-X")])),
            2,
        )

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(definition())


class TestRequestNormalization(unittest.TestCase):
    def test_an_empty_request_means_the_whole_store(self):
        request = validate_request([])
        self.assertTrue(request["whole_store"])
        self.assertEqual(request["identifiers"], [])

    def test_a_named_request_is_not_a_whole_store_request(self):
        request = validate_request(["EV-UNDERVOLT"])
        self.assertFalse(request["whole_store"])

    def test_a_repeated_identifier_collapses_and_is_recorded(self):
        request = validate_request(["EV-A", "EV-B", "EV-A"])
        self.assertEqual(request["identifiers"], ["EV-A", "EV-B"])
        self.assertEqual(request["repeated"], ["EV-A"])

    def test_request_order_is_preserved(self):
        request = validate_request(["EV-C", "EV-A", "EV-B"])
        self.assertEqual(request["identifiers"], ["EV-C", "EV-A", "EV-B"])

    def test_a_non_list_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request("EV-A")

    def test_a_non_string_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["EV-A", 7])


class TestResolution(unittest.TestCase):
    def test_the_scope_keeps_only_the_named_application_process(self):
        scoped = scoped_store(store(), "AP-PWR")
        self.assertEqual(len(scoped), 2)

    def test_an_empty_request_resolves_to_the_scoped_store(self):
        resolution = resolve_request(store(), "AP-PWR", [])
        self.assertEqual(len(resolution["resolved"]), 2)
        self.assertEqual(resolution["unknown"], [])

    def test_a_known_identifier_resolves(self):
        resolution = resolve_request(store(), "AP-PWR", ["EV-OVERCURRENT"])
        self.assertEqual(len(resolution["resolved"]), 1)

    def test_an_unknown_identifier_is_separated_not_dropped(self):
        resolution = resolve_request(store(), "AP-PWR", ["EV-UNDERVOLT", "EV-GHOST"])
        self.assertEqual(len(resolution["resolved"]), 1)
        self.assertEqual(resolution["unknown"], ["EV-GHOST"])

    def test_an_identifier_belonging_to_another_process_does_not_resolve(self):
        resolution = resolve_request(store(), "AP-THM", ["EV-OVERCURRENT"])
        self.assertEqual(resolution["unknown"], ["EV-OVERCURRENT"])

    def test_resolution_keeps_request_order(self):
        resolution = resolve_request(
            store(), "AP-PWR", ["EV-OVERCURRENT", "EV-UNDERVOLT"]
        )
        self.assertEqual(
            [r["event_definition_id"] for r in resolution["resolved"]],
            ["EV-OVERCURRENT", "EV-UNDERVOLT"],
        )

    def test_one_notification_is_raised_per_unknown_identifier(self):
        resolution = resolve_request(store(), "AP-PWR", ["EV-G1", "EV-G2"])
        notifications = failure_notifications(resolution)
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[0]["failure"], "no-such-event-action-definition")

    def test_a_non_mapping_resolution_raises(self):
        with self.assertRaises(ValueError):
            failure_notifications(["EV-A"])


class TestReportAssembly(unittest.TestCase):
    def test_an_entry_carries_the_action_the_definition_holds(self):
        entry = definition_report_entry(
            definition("AP-PWR", "EV-UNDERVOLT", True, action("TC-SHED-LOAD"))
        )
        self.assertEqual(entry["action"]["telecommand_id"], "TC-SHED-LOAD")

    def test_an_entry_carries_the_enable_state(self):
        entry = definition_report_entry(definition(enabled=False))
        self.assertFalse(entry["enabled"])

    def test_a_whole_store_request_reports_the_scoped_store(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        self.assertTrue(outcome["generated"])
        self.assertEqual(outcome["report"]["reported_count"], 2)

    def test_a_partly_unknown_request_still_reports_the_known_ones(self):
        outcome = build_definition_report(
            store(), "AP-PWR", ["EV-UNDERVOLT", "EV-GHOST"]
        )
        self.assertTrue(outcome["generated"])
        self.assertEqual(outcome["report"]["reported_count"], 1)
        self.assertEqual(outcome["report"]["unknown_count"], 1)

    def test_an_all_unknown_request_generates_no_report(self):
        outcome = build_definition_report(store(), "AP-PWR", ["EV-G1", "EV-G2"])
        self.assertFalse(outcome["generated"])
        self.assertIsNone(outcome["report"])
        self.assertEqual(len(outcome["notifications"]), 2)

    def test_a_repeated_identifier_produces_one_entry(self):
        outcome = build_definition_report(
            store(), "AP-PWR", ["EV-UNDERVOLT", "EV-UNDERVOLT"]
        )
        self.assertEqual(outcome["report"]["reported_count"], 1)

    def test_a_scoped_request_on_an_empty_process_reports_nothing(self):
        outcome = build_definition_report(store(), "AP-COMMS", [])
        self.assertTrue(outcome["generated"])
        self.assertEqual(outcome["report"]["entries"], [])

    def test_the_entry_action_is_read_from_the_store_not_a_cached_copy(self):
        records = store()
        outcome = build_definition_report(records, "AP-PWR", ["EV-UNDERVOLT"])
        outcome["report"]["entries"][0]["action"]["telecommand_id"] = "TC-MUTATED"
        again = build_definition_report(records, "AP-PWR", ["EV-UNDERVOLT"])
        self.assertEqual(
            again["report"]["entries"][0]["action"]["telecommand_id"], "TC-SHED-LOAD"
        )


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        self.assertTrue(report_is_complete(outcome["report"])["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        outcome["report"]["entries"] = outcome["report"]["entries"][:1]
        self.assertFalse(report_is_complete(outcome["report"])["complete"])

    def test_a_duplicated_entry_is_detected(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        report = outcome["report"]
        report["entries"].append(report["entries"][0])
        report["reported_count"] = len(report["entries"])
        self.assertFalse(report_is_complete(report)["complete"])

    def test_an_entry_missing_its_action_is_detected(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        outcome["report"]["entries"][0]["action"] = None
        self.assertFalse(report_is_complete(outcome["report"])["complete"])

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        outcome["report"]["reported_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(outcome["report"])


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_whole_store_request_is_reported(self):
        result = assess_definition_report(store(), "AP-PWR", [])
        self.assertEqual(result["verdict"], VERDICT_REPORTED)
        self.assertEqual(result["findings"], [])

    def test_the_reported_identifiers_follow_request_order(self):
        result = assess_definition_report(
            store(), "AP-PWR", ["EV-OVERCURRENT", "EV-UNDERVOLT"]
        )
        self.assertEqual(result["reported_ids"], ["EV-OVERCURRENT", "EV-UNDERVOLT"])

    def test_an_unknown_identifier_is_named_in_the_findings(self):
        result = assess_definition_report(store(), "AP-PWR", ["EV-UNDERVOLT", "EV-GHOST"])
        self.assertEqual(result["unknown_ids"], ["EV-GHOST"])
        self.assertEqual(len(result["findings"]), 1)

    def test_an_all_unknown_request_fails_at_start(self):
        result = assess_definition_report(store(), "AP-PWR", ["EV-G1"])
        self.assertEqual(result["verdict"], VERDICT_FAILED_START)
        self.assertIsNone(result["report"])

    def test_a_repeated_identifier_is_raised_as_a_finding(self):
        result = assess_definition_report(
            store(), "AP-PWR", ["EV-UNDERVOLT", "EV-UNDERVOLT"]
        )
        self.assertEqual(result["verdict"], VERDICT_REPORTED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_received_report_with_a_wrong_total_is_graded_incomplete(self):
        outcome = build_definition_report(store(), "AP-PWR", [])
        self.assertEqual(grade_received_report(outcome["report"])["verdict"],
                         VERDICT_REPORTED)
        outcome["report"]["reported_count"] = 5
        graded = grade_received_report(outcome["report"])
        self.assertEqual(graded["verdict"], VERDICT_INCOMPLETE)
        self.assertEqual(len(graded["findings"]), 1)

    def test_an_invalid_store_entry_raises_before_any_report(self):
        broken = store()
        broken[0]["action"] = {"target_application_process_id": "AP-AOCS"}
        with self.assertRaises(ValueError):
            assess_definition_report(broken, "AP-PWR", [])

    def test_an_empty_store_answers_a_whole_store_request_with_nothing(self):
        result = assess_definition_report([], "AP-PWR", [])
        self.assertEqual(result["verdict"], VERDICT_REPORTED)
        self.assertEqual(result["reported_ids"], [])


if __name__ == "__main__":
    unittest.main()
