"""Contract test for the event-action definition leaf (stdlib unittest)."""

import unittest

from e7041_event_action_definition_logic import (
    APID_MAX,
    EVENT_ACTION_SERVICE_TYPE,
    FINDING_ACTION_MANAGES_THE_TABLE,
    FINDING_ACTION_RAISES_UNDEFINED_EVENT,
    FINDING_CYCLE,
    FINDING_DUPLICATE_KEY,
    FINDING_SELF_TRIGGERING,
    FINDING_TABLE_FULL,
    action_graph,
    assess_event_action_definitions,
    build_definition_table,
    check_action_scope,
    event_key,
    find_cycles,
    normalise_action,
    normalise_definition,
)


def action(service_type=8, subtype=1, target=25, raises=None):
    spec = {
        "service_type": service_type,
        "message_subtype": subtype,
        "target_apid": target,
    }
    if raises is not None:
        spec["raises_event"] = raises
    return spec


def definition(apid=17, event_id=4001, enabled=True, **kwargs):
    return {
        "apid": apid,
        "event_definition_id": event_id,
        "enabled": enabled,
        "action": action(**kwargs),
    }


def findings_of(report):
    return [f["finding"] for f in report["findings"]]


class TestEventKey(unittest.TestCase):
    def test_the_key_is_the_source_and_the_event_identifier_together(self):
        self.assertEqual(event_key(17, 4001), (17, 4001))

    def test_two_sources_may_use_the_same_event_identifier(self):
        self.assertNotEqual(event_key(17, 4001), event_key(18, 4001))

    def test_an_apid_past_the_field_raises(self):
        with self.assertRaises(ValueError):
            event_key(APID_MAX + 1, 4001)

    def test_a_negative_event_identifier_raises(self):
        with self.assertRaises(ValueError):
            event_key(17, -1)

    def test_a_boolean_apid_raises(self):
        with self.assertRaises(ValueError):
            event_key(True, 4001)


class TestAction(unittest.TestCase):
    def test_a_well_formed_action_normalises(self):
        normalised = normalise_action(action())
        self.assertEqual(normalised["service_type"], 8)
        self.assertIsNone(normalised["raises_event"])

    def test_a_list_of_requests_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_action([action(), action(subtype=2)])

    def test_an_action_without_a_service_type_raises(self):
        with self.assertRaises(ValueError):
            normalise_action({"message_subtype": 1, "target_apid": 25})

    def test_a_service_type_outside_the_field_raises(self):
        with self.assertRaises(ValueError):
            normalise_action(action(service_type=0))

    def test_a_malformed_raises_event_pair_raises(self):
        with self.assertRaises(ValueError):
            normalise_action(action(raises=(17,)))

    def test_a_definition_without_an_action_raises(self):
        with self.assertRaises(ValueError):
            normalise_definition({"apid": 17, "event_definition_id": 4001})

    def test_a_definition_defaults_to_disabled(self):
        normalised = normalise_definition(
            {"apid": 17, "event_definition_id": 4001, "action": action()}
        )
        self.assertFalse(normalised["enabled"])


class TestTableConstruction(unittest.TestCase):
    def test_distinct_events_build_distinct_entries(self):
        built = build_definition_table(
            [definition(event_id=4001), definition(event_id=4002)]
        )
        self.assertEqual(sorted(built["table"]), [(17, 4001), (17, 4002)])
        self.assertEqual(built["findings"], [])

    def test_the_same_identifier_from_two_sources_is_not_a_duplicate(self):
        built = build_definition_table(
            [definition(apid=17), definition(apid=18)]
        )
        self.assertEqual(built["findings"], [])
        self.assertEqual(len(built["table"]), 2)

    def test_a_repeated_key_is_a_duplicate_finding_and_does_not_overwrite(self):
        built = build_definition_table(
            [definition(subtype=1), definition(subtype=9)]
        )
        self.assertEqual(built["findings"][0]["finding"], FINDING_DUPLICATE_KEY)
        self.assertEqual(built["table"][(17, 4001)]["action"]["message_subtype"], 1)

    def test_a_full_table_refuses_the_next_definition(self):
        built = build_definition_table(
            [definition(event_id=4001), definition(event_id=4002)], capacity=1
        )
        self.assertEqual(built["findings"][0]["finding"], FINDING_TABLE_FULL)
        self.assertEqual(len(built["table"]), 1)

    def test_a_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            build_definition_table([definition()], capacity=0)

    def test_definitions_must_be_a_list(self):
        with self.assertRaises(ValueError):
            build_definition_table(definition())


class TestActionScope(unittest.TestCase):
    def test_an_action_that_rewrites_the_table_is_flagged(self):
        normalised = normalise_definition(
            definition(service_type=EVENT_ACTION_SERVICE_TYPE)
        )
        self.assertEqual(
            [f["finding"] for f in check_action_scope(normalised)],
            [FINDING_ACTION_MANAGES_THE_TABLE],
        )

    def test_an_ordinary_action_is_in_scope(self):
        self.assertEqual(check_action_scope(normalise_definition(definition())), [])

    def test_an_action_raising_its_own_trigger_is_self_triggering(self):
        normalised = normalise_definition(definition(raises=(17, 4001)))
        self.assertIn(
            FINDING_SELF_TRIGGERING,
            [f["finding"] for f in check_action_scope(normalised)],
        )


class TestGraphAndCycles(unittest.TestCase):
    def test_a_definition_with_no_raised_event_has_no_edge(self):
        built = build_definition_table([definition()])
        self.assertEqual(action_graph(built["table"]), {(17, 4001): []})

    def test_a_chain_of_two_definitions_is_not_a_cycle(self):
        built = build_definition_table(
            [
                definition(event_id=4001, raises=(17, 4002)),
                definition(event_id=4002),
            ]
        )
        self.assertEqual(find_cycles(action_graph(built["table"])), [])

    def test_two_definitions_releasing_each_other_form_a_cycle(self):
        built = build_definition_table(
            [
                definition(event_id=4001, raises=(17, 4002)),
                definition(event_id=4002, raises=(17, 4001)),
            ]
        )
        cycles = find_cycles(action_graph(built["table"]))
        self.assertEqual(len(cycles), 1)
        self.assertEqual(sorted(cycles[0]), [(17, 4001), (17, 4002)])

    def test_a_three_definition_loop_is_reported_once(self):
        built = build_definition_table(
            [
                definition(event_id=1, raises=(17, 2)),
                definition(event_id=2, raises=(17, 3)),
                definition(event_id=3, raises=(17, 1)),
            ]
        )
        self.assertEqual(len(find_cycles(action_graph(built["table"]))), 1)

    def test_the_graph_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            action_graph([(17, 4001)])

    def test_find_cycles_needs_edges(self):
        with self.assertRaises(ValueError):
            find_cycles([(17, 4001)])


class TestAssessment(unittest.TestCase):
    def test_a_sound_table_reports_no_findings(self):
        report = assess_event_action_definitions(
            [definition(event_id=4001), definition(event_id=4002, enabled=False)]
        )
        self.assertTrue(report["table_sound"])
        self.assertEqual(report["definition_count"], 2)
        self.assertEqual(report["enabled_count"], 1)

    def test_a_self_triggering_definition_makes_the_table_unsound(self):
        report = assess_event_action_definitions([definition(raises=(17, 4001))])
        self.assertFalse(report["table_sound"])
        self.assertIn(FINDING_SELF_TRIGGERING, findings_of(report))
        self.assertIn(FINDING_CYCLE, findings_of(report))

    def test_an_action_raising_an_uncovered_event_is_named(self):
        report = assess_event_action_definitions([definition(raises=(17, 9999))])
        self.assertIn(FINDING_ACTION_RAISES_UNDEFINED_EVENT, findings_of(report))

    def test_a_table_rewriting_action_is_carried_into_the_assessment(self):
        report = assess_event_action_definitions(
            [definition(service_type=EVENT_ACTION_SERVICE_TYPE)]
        )
        self.assertIn(FINDING_ACTION_MANAGES_THE_TABLE, findings_of(report))

    def test_the_reported_keys_are_sorted_for_a_stable_comparison(self):
        report = assess_event_action_definitions(
            [definition(event_id=4002), definition(event_id=4001)]
        )
        self.assertEqual(report["keys"], [(17, 4001), (17, 4002)])


if __name__ == "__main__":
    unittest.main()
