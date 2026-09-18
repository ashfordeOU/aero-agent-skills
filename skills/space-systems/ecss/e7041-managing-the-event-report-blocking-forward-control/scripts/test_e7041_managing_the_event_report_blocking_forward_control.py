"""Contract test for the event report blocking forward-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_event_report_blocking_forward_control_logic import (
    ACCEPTED,
    FINDING_HIGH_SEVERITY_BLOCKED,
    MAX_EVENTS_PER_APPLICATION_PROCESS,
    REASON_ALREADY_BLOCKED,
    REASON_APPLICATION_PROCESS_NOT_CONTROLLED,
    REASON_EVENT_CAPACITY,
    REASON_EVENT_NOT_BLOCKABLE,
    REASON_EVENT_NOT_DEFINED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_WILDCARD_COVERS_UNBLOCKABLE,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    SEVERITY_HIGH,
    SEVERITY_INFORMATIVE,
    SEVERITY_LOW,
    add_blocked_events,
    assess_event_blocking_forward_control,
    blocked_events,
    delete_blocked_events,
    empty_configuration,
    event_is_blockable,
    event_is_defined,
    is_event_report_blocked,
    is_event_report_forwarded,
    normalize_configuration,
    report_configuration,
    severity_census,
    validate_event_catalogue,
    validate_selection,
)

CONTROLLED = [10, 11]
CATALOGUE = {
    10: {
        100: {"severity": SEVERITY_INFORMATIVE, "blockable": True},
        101: {"severity": SEVERITY_LOW, "blockable": True},
        102: {"severity": SEVERITY_HIGH, "blockable": True},
        103: {"severity": SEVERITY_HIGH, "blockable": False},
    },
    11: {
        200: {"severity": SEVERITY_INFORMATIVE, "blockable": True},
        201: {"severity": SEVERITY_LOW, "blockable": True},
    },
}


def sel(apid=10, event_id=100):
    return {"apid": apid, "event_id": event_id}


class TestCatalogue(unittest.TestCase):
    def test_event_defined_under_its_own_application_process(self):
        self.assertTrue(event_is_defined(CATALOGUE, 10, 100))

    def test_event_of_another_application_process_is_not_defined_here(self):
        self.assertFalse(event_is_defined(CATALOGUE, 11, 100))

    def test_blockable_flag_is_read_from_the_catalogue(self):
        self.assertTrue(event_is_blockable(CATALOGUE, 10, 102))
        self.assertFalse(event_is_blockable(CATALOGUE, 10, 103))

    def test_blockable_of_an_undefined_event_raises(self):
        with self.assertRaises(ValueError):
            event_is_blockable(CATALOGUE, 10, 999)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_event_catalogue({10: {100: {"severity": "urgent"}}})

    def test_non_boolean_blockable_raises(self):
        with self.assertRaises(ValueError):
            validate_event_catalogue(
                {10: {100: {"severity": SEVERITY_LOW, "blockable": 1}}}
            )

    def test_empty_catalogue_raises(self):
        with self.assertRaises(ValueError):
            validate_event_catalogue({})

    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_selection([10, 100])


class TestInvertedSense(unittest.TestCase):
    def test_empty_configuration_forwards_every_event_report(self):
        config = empty_configuration()
        self.assertFalse(is_event_report_blocked(config, 10, 100))
        self.assertTrue(is_event_report_forwarded(config, 10, 102))
        self.assertTrue(report_configuration(config)["blocks_nothing"])

    def test_blocking_an_event_stops_it_being_forwarded(self):
        config, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel()]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_event_report_blocked(config, 10, 100))
        self.assertFalse(is_event_report_forwarded(config, 10, 100))

    def test_an_unnamed_event_stays_forwarded(self):
        config, _ = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel()]
        )
        self.assertTrue(is_event_report_forwarded(config, 10, 101))

    def test_wildcard_and_explicit_events_together_raise(self):
        with self.assertRaises(ValueError):
            normalize_configuration(
                {10: {"block_all_events": True, "event_ids": [100]}}
            )


class TestBlockRequests(unittest.TestCase):
    def test_not_blockable_event_is_rejected(self):
        config, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(event_id=103)]
        )
        self.assertEqual(disp[0]["reason"], REASON_EVENT_NOT_BLOCKABLE)
        self.assertEqual(config, {})
        self.assertTrue(is_event_report_forwarded(config, 10, 103))

    def test_undefined_event_is_rejected(self):
        _, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(event_id=999)]
        )
        self.assertEqual(disp[0]["reason"], REASON_EVENT_NOT_DEFINED)

    def test_uncontrolled_application_process_is_rejected(self):
        _, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(apid=12)]
        )
        self.assertEqual(disp[0]["reason"], REASON_APPLICATION_PROCESS_NOT_CONTROLLED)

    def test_blocking_a_high_severity_event_is_accepted_with_a_finding(self):
        config, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(event_id=102)]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(disp[0]["findings"], [FINDING_HIGH_SEVERITY_BLOCKED])
        self.assertTrue(is_event_report_blocked(config, 10, 102))

    def test_blocking_a_low_severity_event_carries_no_finding(self):
        _, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(event_id=101)]
        )
        self.assertEqual(disp[0]["findings"], [])

    def test_block_all_wildcard_is_refused_when_it_would_cover_an_unblockable_event(self):
        config, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 10}]
        )
        self.assertEqual(disp[0]["reason"], REASON_WILDCARD_COVERS_UNBLOCKABLE)
        self.assertEqual(config, {})

    def test_block_all_wildcard_is_accepted_when_every_event_is_blockable(self):
        config, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 11}]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_event_report_blocked(config, 11, 200))
        self.assertTrue(is_event_report_blocked(config, 11, 201))

    def test_duplicate_block_is_rejected(self):
        _, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel()]
        )
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_BLOCKED)

    def test_event_under_a_live_wildcard_is_subsumed(self):
        config, _ = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 11}]
        )
        _, disp = add_blocked_events(
            config, CONTROLLED, CATALOGUE, [sel(apid=11, event_id=200)]
        )
        self.assertEqual(disp[0]["reason"], REASON_SUBSUMED_BY_WILDCARD)

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = add_blocked_events(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(event_id=103), sel(event_id=101)],
        )
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertTrue(is_event_report_blocked(config, 10, 101))

    def test_event_capacity_is_a_rejection(self):
        catalogue = {
            10: {
                n: {"severity": SEVERITY_LOW, "blockable": True}
                for n in range(0, MAX_EVENTS_PER_APPLICATION_PROCESS + 2)
            }
        }
        items = [
            sel(event_id=n)
            for n in range(0, MAX_EVENTS_PER_APPLICATION_PROCESS + 2)
        ]
        _, disp = add_blocked_events(
            empty_configuration(), CONTROLLED, catalogue, items
        )
        self.assertEqual(disp[-1]["reason"], REASON_EVENT_CAPACITY)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            add_blocked_events(empty_configuration(), CONTROLLED, CATALOGUE, sel())


class TestUnblockRequests(unittest.TestCase):
    def test_unblocking_restores_forwarding(self):
        config, _ = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(event_id=101)]
        )
        config, disp = delete_blocked_events(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_event_report_forwarded(config, 10, 100))
        self.assertTrue(is_event_report_blocked(config, 10, 101))

    def test_unblocking_the_application_process_clears_every_block(self):
        config, _ = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(event_id=101)]
        )
        config, disp = delete_blocked_events(config, [{"apid": 10}])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(config, {})

    def test_unblocking_an_event_that_was_never_blocked_is_rejected(self):
        _, disp = delete_blocked_events(empty_configuration(), [sel()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_wildcard_cannot_be_partially_unblocked(self):
        config, _ = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [{"apid": 11}]
        )
        _, disp = delete_blocked_events(config, [sel(apid=11, event_id=200)])
        self.assertEqual(disp[0]["reason"], REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)


class TestCensusAndAssessment(unittest.TestCase):
    def test_blocked_events_are_intersected_with_the_catalogue(self):
        config, _ = add_blocked_events(
            empty_configuration(), CONTROLLED, CATALOGUE, [sel(), sel(event_id=101)]
        )
        self.assertEqual(blocked_events(config, CATALOGUE, 10), [100, 101])
        self.assertEqual(blocked_events(config, CATALOGUE, 11), [])

    def test_severity_census_counts_what_is_held_back(self):
        config, _ = add_blocked_events(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(), sel(event_id=101), sel(event_id=102)],
        )
        census = severity_census(config, CATALOGUE)
        self.assertEqual(census[SEVERITY_INFORMATIVE], 1)
        self.assertEqual(census[SEVERITY_LOW], 1)
        self.assertEqual(census[SEVERITY_HIGH], 1)

    def test_report_is_sorted(self):
        config, _ = add_blocked_events(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [sel(apid=11, event_id=201), sel(event_id=101), sel(event_id=100)],
        )
        report = report_configuration(config)
        self.assertEqual([e["apid"] for e in report["application_processes"]], [10, 11])
        self.assertEqual(report["application_processes"][0]["event_ids"], [100, 101])

    def test_assessment_is_clean_when_nothing_was_rejected_or_flagged(self):
        result = assess_event_blocking_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [{"operation": "block", "items": [sel(), sel(event_id=101)]}],
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["findings"], [])

    def test_assessment_surfaces_the_high_severity_finding(self):
        result = assess_event_blocking_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [{"operation": "block", "items": [sel(event_id=102)]}],
        )
        self.assertEqual(result["findings"], [FINDING_HIGH_SEVERITY_BLOCKED])
        self.assertFalse(result["clean"])

    def test_assessment_round_trips_block_then_unblock(self):
        result = assess_event_blocking_forward_control(
            empty_configuration(),
            CONTROLLED,
            CATALOGUE,
            [
                {"operation": "block", "items": [sel()]},
                {"operation": "unblock", "items": [sel()]},
            ],
        )
        self.assertEqual(result["configuration"][10]["event_ids"], set())
        self.assertEqual(result["rejected_total"], 0)

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            assess_event_blocking_forward_control(
                empty_configuration(), CONTROLLED, CATALOGUE, [{"operation": "mute"}]
            )

    def test_empty_request_list_raises(self):
        with self.assertRaises(ValueError):
            assess_event_blocking_forward_control(
                empty_configuration(), CONTROLLED, CATALOGUE, []
            )


if __name__ == "__main__":
    unittest.main()
