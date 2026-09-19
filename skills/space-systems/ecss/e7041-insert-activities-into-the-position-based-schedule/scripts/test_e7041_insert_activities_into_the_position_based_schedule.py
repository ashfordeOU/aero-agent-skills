"""Contract tests for the clause 6.22.6.6 position-based insertion logic."""

import unittest

from e7041_insert_activities_into_the_position_based_schedule_logic import (
    DEFAULT_MIN_LEAD_DEG,
    FULL_REVOLUTION_DEG,
    REJECTION_REASONS,
    assess_insertion_request,
    capacity_remaining,
    check_instruction,
    forward_arc_deg,
    insert_activities,
    normalize_position_deg,
    release_order,
    validate_instruction,
    validate_schedule_state,
)


def sample_state(enabled=True, capacity=None, eclipse_enabled=True):
    return {
        "enabled": enabled,
        "capacity": capacity,
        "sub_schedules": {"routine": True, "eclipse": eclipse_enabled},
        "groups": {"payload": True, "comms": True},
        "activities": [
            {
                "activity_id": "held1",
                "sub_schedule": "routine",
                "group": "payload",
                "release_position_deg": 120.0,
                "request": "tc-held",
            }
        ],
    }


def instruction(activity_id="n1", sub_schedule="routine", group="payload",
                position=250.0, request="tc-new"):
    return {
        "activity_id": activity_id,
        "sub_schedule": sub_schedule,
        "group": group,
        "release_position_deg": position,
        "request": request,
    }


class PositionArithmeticTests(unittest.TestCase):
    def test_position_wraps_into_one_revolution(self):
        self.assertAlmostEqual(normalize_position_deg(725.0), 5.0, places=9)

    def test_negative_position_wraps_forward(self):
        self.assertAlmostEqual(normalize_position_deg(-90.0), 270.0, places=9)

    def test_forward_arc_crosses_the_wrap_point(self):
        self.assertAlmostEqual(forward_arc_deg(340.0, 20.0), 40.0, places=9)

    def test_forward_arc_to_the_same_position_is_zero(self):
        self.assertAlmostEqual(forward_arc_deg(15.0, 15.0), 0.0, places=9)


class ValidationTests(unittest.TestCase):
    def test_instruction_is_normalized(self):
        record = validate_instruction(instruction(position=-10.0))
        self.assertAlmostEqual(record["release_position_deg"], 350.0, places=9)

    def test_instruction_missing_position_rejected(self):
        bad = instruction()
        del bad["release_position_deg"]
        with self.assertRaises(ValueError):
            validate_instruction(bad)

    def test_instruction_with_blank_sub_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_instruction(instruction(sub_schedule=""))

    def test_state_without_sub_schedules_rejected(self):
        state = sample_state()
        state["sub_schedules"] = {}
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_state_over_capacity_rejected(self):
        state = sample_state(capacity=0)
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_negative_capacity_rejected(self):
        state = sample_state()
        state["capacity"] = -1
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_held_activity_in_undeclared_sub_schedule_rejected(self):
        state = sample_state()
        state["activities"][0]["sub_schedule"] = "ghost"
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_empty_request_body_rejected_as_instruction(self):
        with self.assertRaises(ValueError):
            insert_activities(sample_state(), [])


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.state = validate_schedule_state(sample_state())
        self.held = {"held1"}

    def test_good_instruction_passes(self):
        self.assertIsNone(check_instruction(instruction(), self.state, self.held))

    def test_unknown_sub_schedule_rejected(self):
        self.assertEqual(
            check_instruction(instruction(sub_schedule="ghost"), self.state, self.held),
            "unknown-sub-schedule",
        )

    def test_unknown_group_rejected(self):
        self.assertEqual(
            check_instruction(instruction(group="ghost"), self.state, self.held),
            "unknown-group",
        )

    def test_missing_request_body_rejected(self):
        self.assertEqual(
            check_instruction(instruction(request="   "), self.state, self.held),
            "missing-request",
        )

    def test_duplicate_activity_id_rejected(self):
        self.assertEqual(
            check_instruction(instruction(activity_id="held1"), self.state, self.held),
            "duplicate-activity-id",
        )

    def test_no_room_left_rejected(self):
        self.assertEqual(
            check_instruction(instruction(), self.state, self.held, room_left=0),
            "schedule-full",
        )

    def test_release_position_too_close_ahead_rejected(self):
        self.assertEqual(
            check_instruction(instruction(position=100.5), self.state, self.held,
                              current_position_deg=100.0, min_lead_deg=2.0),
            "insufficient-lead-arc",
        )

    def test_release_position_exactly_at_the_lead_bound_accepted(self):
        self.assertIsNone(
            check_instruction(instruction(position=102.0), self.state, self.held,
                              current_position_deg=100.0, min_lead_deg=2.0)
        )

    def test_lead_arc_measured_forward_not_absolute(self):
        self.assertIsNone(
            check_instruction(instruction(position=99.0), self.state, self.held,
                              current_position_deg=100.0, min_lead_deg=2.0)
        )

    def test_ungrouped_instruction_accepted(self):
        self.assertIsNone(
            check_instruction(instruction(group=None), self.state, self.held)
        )

    def test_negative_lead_rejected_as_input_error(self):
        with self.assertRaises(ValueError):
            check_instruction(instruction(), self.state, self.held,
                              current_position_deg=0.0, min_lead_deg=-1.0)


class InsertionTests(unittest.TestCase):
    def test_single_good_instruction_is_inserted(self):
        result = insert_activities(sample_state(), [instruction()])
        self.assertEqual([rec["activity_id"] for rec in result["accepted"]], ["n1"])

    def test_bad_instruction_does_not_withdraw_the_good_ones(self):
        result = insert_activities(
            sample_state(),
            [instruction("n1"), instruction("n2", sub_schedule="ghost"), instruction("n3")],
        )
        self.assertEqual([rec["activity_id"] for rec in result["accepted"]], ["n1", "n3"])
        self.assertEqual(result["rejected"][0]["reason"], "unknown-sub-schedule")

    def test_rejection_carries_the_instruction_index(self):
        result = insert_activities(
            sample_state(), [instruction("n1"), instruction("n2", group="ghost")]
        )
        self.assertEqual(result["rejected"][0]["index"], 1)

    def test_identifier_repeated_inside_one_request_rejected_once(self):
        result = insert_activities(sample_state(), [instruction("n1"), instruction("n1")])
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(result["rejected"][0]["reason"], "repeated-in-request")

    def test_capacity_is_consumed_across_the_request(self):
        result = insert_activities(
            sample_state(capacity=2), [instruction("n1"), instruction("n2")]
        )
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(result["rejected"][0]["reason"], "schedule-full")

    def test_schedule_is_held_in_release_position_order(self):
        result = insert_activities(
            sample_state(), [instruction("n1", position=30.0), instruction("n2", position=200.0)]
        )
        positions = [rec["release_position_deg"] for rec in result["state_after"]["activities"]]
        self.assertEqual(positions, sorted(positions))

    def test_insertion_into_a_disabled_schedule_is_still_accepted(self):
        result = insert_activities(sample_state(enabled=False), [instruction()])
        self.assertEqual(len(result["accepted"]), 1)

    def test_insertion_into_a_disabled_sub_schedule_is_still_accepted(self):
        result = insert_activities(
            sample_state(eclipse_enabled=False), [instruction(sub_schedule="eclipse")]
        )
        self.assertEqual(len(result["accepted"]), 1)

    def test_input_state_is_not_mutated(self):
        state = sample_state()
        insert_activities(state, [instruction()])
        self.assertEqual(len(state["activities"]), 1)

    def test_all_rejection_reasons_are_declared(self):
        result = insert_activities(
            sample_state(),
            [instruction("n1", sub_schedule="ghost"), instruction("held1")],
        )
        for entry in result["rejected"]:
            self.assertIn(entry["reason"], REJECTION_REASONS)


class CapacityAndOrderTests(unittest.TestCase):
    def test_capacity_remaining_is_none_when_unbounded(self):
        self.assertIsNone(capacity_remaining(sample_state()))

    def test_capacity_remaining_counts_held_activities(self):
        self.assertEqual(capacity_remaining(sample_state(capacity=4)), 3)

    def test_release_order_starts_from_the_current_position(self):
        state = insert_activities(
            sample_state(), [instruction("n1", position=10.0)]
        )["state_after"]
        self.assertEqual(release_order(state, 130.0), ["n1", "held1"])

    def test_release_order_wraps_past_the_revolution_boundary(self):
        state = insert_activities(
            sample_state(), [instruction("n1", position=350.0)]
        )["state_after"]
        self.assertEqual(release_order(state, 300.0), ["n1", "held1"])


class AssessmentTests(unittest.TestCase):
    def test_clean_request_has_no_findings(self):
        result = assess_insertion_request(sample_state(), [instruction()])
        self.assertEqual(result["findings"], [])

    def test_partial_rejection_is_reported(self):
        result = assess_insertion_request(
            sample_state(), [instruction("n1"), instruction("n2", group="ghost")]
        )
        self.assertTrue(any("were rejected" in note for note in result["findings"]))

    def test_total_rejection_is_reported(self):
        result = assess_insertion_request(
            sample_state(), [instruction("n1", sub_schedule="ghost")]
        )
        self.assertEqual(result["accepted_count"], 0)
        self.assertTrue(any("nothing was inserted" in note for note in result["findings"]))

    def test_filling_the_schedule_is_reported(self):
        result = assess_insertion_request(sample_state(capacity=2), [instruction()])
        self.assertEqual(result["capacity_remaining"], 0)
        self.assertTrue(any("now full" in note for note in result["findings"]))

    def test_disabled_sub_schedule_parking_is_reported(self):
        result = assess_insertion_request(
            sample_state(eclipse_enabled=False), [instruction(sub_schedule="eclipse")]
        )
        self.assertTrue(any("disabled sub-schedule" in note for note in result["findings"]))

    def test_disabled_schedule_is_reported(self):
        result = assess_insertion_request(sample_state(enabled=False), [instruction()])
        self.assertTrue(any("schedule is disabled" in note for note in result["findings"]))

    def test_release_order_omitted_without_a_position(self):
        self.assertIsNone(assess_insertion_request(sample_state(), [instruction()])["release_order"])

    def test_default_lead_is_a_small_arc(self):
        self.assertLess(DEFAULT_MIN_LEAD_DEG, FULL_REVOLUTION_DEG / 36.0)


if __name__ == "__main__":
    unittest.main()
