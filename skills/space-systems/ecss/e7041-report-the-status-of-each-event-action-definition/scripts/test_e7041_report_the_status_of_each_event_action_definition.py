"""Contract test for the e7041 event-action status report leaf."""

import unittest

from e7041_report_the_status_of_each_event_action_definition_logic import (
    EFFECTIVE_STATES,
    VERDICT_CONSISTENT,
    VERDICT_INCONSISTENT,
    assess_status_report,
    build_status_report,
    check_status_consistency,
    definition_key,
    derive_effective_state,
    function_enabled,
    report_is_complete,
    status_report_entry,
    validate_event_action_definition,
    validate_function_states,
    validate_store,
)


def definition(apid="AP-PWR", event_id="EV-UNDERVOLT", enabled=True, **kw):
    record = {
        "application_process_id": apid,
        "event_definition_id": event_id,
        "enabled": enabled,
    }
    record.update(kw)
    return record


def store():
    return [
        definition("AP-PWR", "EV-UNDERVOLT", True),
        definition("AP-PWR", "EV-OVERCURRENT", False),
        definition("AP-THM", "EV-UNDERVOLT", True),
    ]


def states(pwr=True, thm=True):
    return {"AP-PWR": pwr, "AP-THM": thm}


class TestValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_event_action_definition(definition())
        self.assertEqual(record["application_process_id"], "AP-PWR")
        self.assertEqual(record["event_definition_id"], "EV-UNDERVOLT")

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_event_action_definition("AP-PWR")

    def test_a_missing_application_process_raises(self):
        record = definition()
        del record["application_process_id"]
        with self.assertRaises(ValueError):
            validate_event_action_definition(record)

    def test_an_empty_event_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_event_action_definition(definition(event_id="   "))

    def test_a_missing_enable_flag_raises(self):
        record = definition()
        del record["enabled"]
        with self.assertRaises(ValueError):
            validate_event_action_definition(record)

    def test_a_non_boolean_enable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_event_action_definition(definition(enabled=1))

    def test_an_unknown_declared_effective_state_raises(self):
        with self.assertRaises(ValueError):
            validate_event_action_definition(
                definition(declared_effective_state="standby")
            )

    def test_the_same_event_under_two_processes_is_two_definitions(self):
        normalized = validate_store(
            [definition("AP-PWR", "EV-X"), definition("AP-THM", "EV-X")]
        )
        self.assertEqual(len(normalized), 2)

    def test_a_repeated_process_and_event_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition("AP-PWR", "EV-X"), definition("AP-PWR", "EV-X")])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(definition())

    def test_the_definition_key_is_the_process_and_event_pair(self):
        record = validate_event_action_definition(definition())
        self.assertEqual(definition_key(record), ("AP-PWR", "EV-UNDERVOLT"))


class TestFunctionStates(unittest.TestCase):
    def test_declared_function_states_normalize(self):
        self.assertEqual(validate_function_states(states()), states())

    def test_a_non_mapping_function_state_raises(self):
        with self.assertRaises(ValueError):
            validate_function_states(["AP-PWR"])

    def test_a_non_boolean_function_state_raises(self):
        with self.assertRaises(ValueError):
            validate_function_states({"AP-PWR": "on"})

    def test_an_undeclared_function_state_raises_rather_than_defaulting_on(self):
        with self.assertRaises(ValueError):
            function_enabled({"AP-PWR": True}, "AP-THM")

    def test_a_declared_function_state_is_returned(self):
        self.assertFalse(function_enabled(states(pwr=False), "AP-PWR"))


class TestEffectiveState(unittest.TestCase):
    def test_both_flags_set_is_armed(self):
        result = derive_effective_state(definition(), states())
        self.assertEqual(result["effective_state"], "armed")

    def test_a_clear_definition_flag_is_disabled(self):
        result = derive_effective_state(definition(enabled=False), states())
        self.assertEqual(result["effective_state"], "disabled")

    def test_an_enabled_definition_under_a_disabled_function_is_inhibited(self):
        result = derive_effective_state(definition(), states(pwr=False))
        self.assertEqual(result["effective_state"], "inhibited")

    def test_a_disabled_definition_under_a_disabled_function_stays_disabled(self):
        result = derive_effective_state(definition(enabled=False), states(pwr=False))
        self.assertEqual(result["effective_state"], "disabled")

    def test_every_derived_state_is_a_known_state(self):
        for record in store():
            derived = derive_effective_state(record, states())
            self.assertIn(derived["effective_state"], EFFECTIVE_STATES)

    def test_the_function_flag_is_carried_alongside_the_definition_flag(self):
        result = derive_effective_state(definition(), states(pwr=False))
        self.assertTrue(result["enabled"])
        self.assertFalse(result["function_enabled"])


class TestReportEntry(unittest.TestCase):
    def test_an_entry_carries_the_definitions_own_flag_not_the_effective_state(self):
        entry = status_report_entry(definition(), states(pwr=False))
        self.assertTrue(entry["enabled"])

    def test_an_entry_carries_both_identifiers(self):
        entry = status_report_entry(definition(), states())
        self.assertEqual(entry["application_process_id"], "AP-PWR")
        self.assertEqual(entry["event_definition_id"], "EV-UNDERVOLT")

    def test_an_entry_does_not_leak_the_function_flag_into_the_enable_field(self):
        entry = status_report_entry(definition(enabled=False), states())
        self.assertFalse(entry["enabled"])


class TestConsistency(unittest.TestCase):
    def test_a_definition_with_no_declared_state_under_a_live_function_is_consistent(self):
        self.assertTrue(check_status_consistency(definition(), states())["consistent"])

    def test_an_agreeing_declared_state_is_consistent(self):
        result = check_status_consistency(
            definition(declared_effective_state="armed"), states()
        )
        self.assertTrue(result["consistent"])

    def test_a_disagreeing_declared_state_is_a_defect(self):
        result = check_status_consistency(
            definition(declared_effective_state="disabled"), states()
        )
        self.assertFalse(result["consistent"])
        self.assertEqual(len(result["findings"]), 1)

    def test_an_inhibited_definition_is_reported_as_a_finding(self):
        result = check_status_consistency(definition(), states(pwr=False))
        self.assertFalse(result["consistent"])
        self.assertEqual(result["derived_effective_state"], "inhibited")

    def test_a_disabled_definition_under_a_disabled_function_raises_no_finding(self):
        result = check_status_consistency(
            definition(enabled=False), states(pwr=False)
        )
        self.assertTrue(result["consistent"])


class TestReportAssembly(unittest.TestCase):
    def test_the_report_covers_every_definition_held(self):
        report = build_status_report(store(), states())
        self.assertEqual(report["definition_count"], 3)

    def test_the_entries_follow_store_order(self):
        report = build_status_report(store(), states())
        self.assertEqual(
            [entry["event_definition_id"] for entry in report["entries"]],
            ["EV-UNDERVOLT", "EV-OVERCURRENT", "EV-UNDERVOLT"],
        )

    def test_the_enabled_and_disabled_totals_split_the_store(self):
        report = build_status_report(store(), states())
        self.assertEqual(report["enabled_count"], 2)
        self.assertEqual(report["disabled_count"], 1)

    def test_a_disabled_function_moves_definitions_to_inhibited_not_disabled(self):
        report = build_status_report(store(), states(pwr=False))
        self.assertEqual(report["effective_counts"]["inhibited"], 1)
        self.assertEqual(report["effective_counts"]["armed"], 1)
        self.assertEqual(report["enabled_count"], 2)

    def test_the_effective_counts_add_up_to_the_definition_count(self):
        report = build_status_report(store(), states())
        self.assertEqual(sum(report["effective_counts"].values()), 3)

    def test_an_empty_store_reports_nothing(self):
        report = build_status_report([], {})
        self.assertEqual(report["entries"], [])
        self.assertEqual(report["definition_count"], 0)


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        report = build_status_report(store(), states())
        self.assertTrue(report_is_complete(report)["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        report = build_status_report(store(), states())
        report["entries"] = report["entries"][:2]
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_wrong_enabled_total_is_detected(self):
        report = build_status_report(store(), states())
        report["enabled_count"] = 9
        result = report_is_complete(report)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        report = build_status_report(store(), states())
        report["definition_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(report)


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_store_under_live_functions_is_consistent(self):
        result = assess_status_report(store(), states())
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["findings"], [])

    def test_the_report_always_covers_the_whole_store(self):
        result = assess_status_report(store(), states())
        self.assertTrue(result["covers_whole_store"])
        self.assertEqual(result["held_count"], 3)

    def test_a_disabled_function_makes_the_report_inconsistent(self):
        result = assess_status_report(store(), states(pwr=False))
        self.assertEqual(result["verdict"], VERDICT_INCONSISTENT)
        self.assertEqual(result["inhibited_keys"], [("AP-PWR", "EV-UNDERVOLT")])

    def test_several_inconsistent_definitions_are_all_named(self):
        records = [
            definition("AP-PWR", "EV-A", True),
            definition("AP-PWR", "EV-B", True),
            definition("AP-THM", "EV-C", False),
        ]
        result = assess_status_report(records, states(pwr=False))
        self.assertEqual(
            result["inconsistent_keys"], [("AP-PWR", "EV-A"), ("AP-PWR", "EV-B")]
        )

    def test_the_reported_keys_follow_store_order(self):
        result = assess_status_report(store(), states())
        self.assertEqual(
            result["reported_keys"],
            [("AP-PWR", "EV-UNDERVOLT"), ("AP-PWR", "EV-OVERCURRENT"),
             ("AP-THM", "EV-UNDERVOLT")],
        )

    def test_an_undeclared_function_state_stops_the_whole_report(self):
        with self.assertRaises(ValueError):
            assess_status_report(store(), {"AP-PWR": True})

    def test_an_invalid_store_entry_raises_before_any_report(self):
        broken = store()
        broken[0]["enabled"] = "yes"
        with self.assertRaises(ValueError):
            assess_status_report(broken, states())

    def test_an_empty_store_is_a_consistent_empty_report(self):
        result = assess_status_report([], {})
        self.assertEqual(result["verdict"], VERDICT_CONSISTENT)
        self.assertEqual(result["reported_keys"], [])


if __name__ == "__main__":
    unittest.main()
