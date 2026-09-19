"""Contract tests for the clause 6.22.6.5 position-based schedule reset logic."""

import unittest

from e7041_reset_the_position_based_schedule_logic import (
    DEFAULT_IMMINENT_ARC_DEG,
    FULL_REVOLUTION_DEG,
    assess_reset_request,
    census_by_group,
    census_by_sub_schedule,
    forward_arc_deg,
    imminent_activities,
    normalize_position_deg,
    reset_schedule,
    validate_activity,
    validate_schedule_state,
    verify_reset,
)


def sample_state(enabled=True):
    return {
        "enabled": enabled,
        "sub_schedules": {"routine": True, "eclipse": False},
        "groups": {"payload": True, "comms": False},
        "activities": [
            {
                "activity_id": "a1",
                "sub_schedule": "routine",
                "group": "payload",
                "release_position_deg": 10.0,
            },
            {
                "activity_id": "a2",
                "sub_schedule": "routine",
                "group": "comms",
                "release_position_deg": 95.0,
            },
            {
                "activity_id": "a3",
                "sub_schedule": "eclipse",
                "group": None,
                "release_position_deg": 200.0,
            },
        ],
    }


class PositionArithmeticTests(unittest.TestCase):
    def test_wrap_keeps_in_range_value(self):
        self.assertAlmostEqual(normalize_position_deg(123.25), 123.25, places=9)

    def test_wrap_folds_a_full_revolution(self):
        self.assertAlmostEqual(normalize_position_deg(400.0), 40.0, places=9)

    def test_wrap_folds_a_negative_position(self):
        self.assertAlmostEqual(normalize_position_deg(-30.0), 330.0, places=9)

    def test_wrap_of_exactly_one_revolution_is_zero(self):
        self.assertAlmostEqual(normalize_position_deg(FULL_REVOLUTION_DEG), 0.0, places=9)

    def test_non_numeric_position_rejected(self):
        with self.assertRaises(ValueError):
            normalize_position_deg("30")

    def test_boolean_position_rejected(self):
        with self.assertRaises(ValueError):
            normalize_position_deg(True)

    def test_forward_arc_crosses_the_wrap_point(self):
        self.assertAlmostEqual(forward_arc_deg(350.0, 10.0), 20.0, places=9)

    def test_forward_arc_to_the_same_position_is_zero(self):
        self.assertAlmostEqual(forward_arc_deg(77.0, 77.0), 0.0, places=9)


class ValidationTests(unittest.TestCase):
    def test_activity_is_normalized(self):
        record = validate_activity(
            {"activity_id": "x", "sub_schedule": "s", "release_position_deg": 370.0}
        )
        self.assertAlmostEqual(record["release_position_deg"], 10.0, places=9)
        self.assertIsNone(record["group"])

    def test_activity_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"activity_id": "x", "sub_schedule": "s"})

    def test_empty_activity_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(
                {"activity_id": "  ", "sub_schedule": "s", "release_position_deg": 1.0}
            )

    def test_duplicate_activity_id_rejected(self):
        state = sample_state()
        state["activities"].append(dict(state["activities"][0]))
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_undeclared_sub_schedule_rejected(self):
        state = sample_state()
        state["activities"][0]["sub_schedule"] = "ghost"
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_undeclared_group_rejected(self):
        state = sample_state()
        state["activities"][0]["group"] = "ghost"
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_non_boolean_enabled_rejected(self):
        state = sample_state()
        state["enabled"] = "yes"
        with self.assertRaises(ValueError):
            validate_schedule_state(state)

    def test_activities_are_ordered_by_release_position(self):
        state = validate_schedule_state(sample_state())
        positions = [rec["release_position_deg"] for rec in state["activities"]]
        self.assertEqual(positions, sorted(positions))


class CensusTests(unittest.TestCase):
    def test_sub_schedule_census_counts_every_activity(self):
        self.assertEqual(
            census_by_sub_schedule(sample_state()), {"routine": 2, "eclipse": 1}
        )

    def test_group_census_counts_ungrouped_under_none(self):
        counts = census_by_group(sample_state())
        self.assertEqual(counts[None], 1)
        self.assertEqual(counts["payload"], 1)

    def test_census_of_an_empty_schedule_is_empty(self):
        state = sample_state()
        state["activities"] = []
        self.assertEqual(census_by_sub_schedule(state), {})


class ImminentArcTests(unittest.TestCase):
    def test_activity_just_ahead_is_imminent(self):
        ahead = imminent_activities(sample_state(), 5.0, 10.0)
        self.assertEqual([rec["activity_id"] for rec in ahead], ["a1"])

    def test_activity_exactly_on_the_arc_bound_is_included(self):
        ahead = imminent_activities(sample_state(), 0.0, 10.0)
        self.assertIn("a1", [rec["activity_id"] for rec in ahead])

    def test_activity_just_behind_is_not_imminent(self):
        ahead = imminent_activities(sample_state(), 20.0, 5.0)
        self.assertEqual(ahead, [])

    def test_arc_wraps_across_the_revolution_boundary(self):
        ahead = imminent_activities(sample_state(), 355.0, 20.0)
        self.assertEqual([rec["activity_id"] for rec in ahead], ["a1"])

    def test_full_revolution_arc_catches_everything(self):
        ahead = imminent_activities(sample_state(), 0.0, FULL_REVOLUTION_DEG)
        self.assertEqual(len(ahead), 3)

    def test_negative_arc_rejected(self):
        with self.assertRaises(ValueError):
            imminent_activities(sample_state(), 0.0, -1.0)

    def test_arc_beyond_a_revolution_rejected(self):
        with self.assertRaises(ValueError):
            imminent_activities(sample_state(), 0.0, 400.0)


class ResetTests(unittest.TestCase):
    def test_reset_empties_every_sub_schedule(self):
        after = reset_schedule(sample_state())
        self.assertEqual(after["activities"], [])

    def test_reset_preserves_the_enabled_state_when_enabled(self):
        self.assertTrue(reset_schedule(sample_state(True))["enabled"])

    def test_reset_preserves_the_enabled_state_when_disabled(self):
        self.assertFalse(reset_schedule(sample_state(False))["enabled"])

    def test_reset_preserves_sub_schedule_and_group_definitions(self):
        before = validate_schedule_state(sample_state())
        after = reset_schedule(before)
        self.assertEqual(after["sub_schedules"], before["sub_schedules"])
        self.assertEqual(after["groups"], before["groups"])

    def test_reset_does_not_mutate_the_input_state(self):
        state = sample_state()
        reset_schedule(state)
        self.assertEqual(len(state["activities"]), 3)

    def test_reset_is_idempotent(self):
        once = reset_schedule(sample_state())
        twice = reset_schedule(once)
        self.assertEqual(once, twice)


class VerifyResetTests(unittest.TestCase):
    def test_correct_reset_has_no_findings(self):
        before = sample_state()
        self.assertEqual(verify_reset(before, reset_schedule(before)), [])

    def test_leftover_activity_is_a_finding(self):
        before = sample_state()
        after = reset_schedule(before)
        after["activities"] = [before["activities"][0]]
        self.assertTrue(
            any("deletes all" in note for note in verify_reset(before, after))
        )

    def test_flipped_enabled_state_is_a_finding(self):
        before = sample_state(True)
        after = reset_schedule(before)
        after["enabled"] = False
        self.assertTrue(
            any("enabled state" in note for note in verify_reset(before, after))
        )

    def test_dropped_sub_schedule_definition_is_a_finding(self):
        before = sample_state()
        after = reset_schedule(before)
        after["sub_schedules"] = {}
        self.assertTrue(
            any("sub-schedule definitions" in note for note in verify_reset(before, after))
        )


class AssessResetRequestTests(unittest.TestCase):
    def test_discarded_total_matches_the_schedule_content(self):
        result = assess_reset_request(sample_state())
        self.assertEqual(result["discarded_total"], 3)

    def test_enabled_schedule_reset_reports_unreleased_discards(self):
        result = assess_reset_request(sample_state(True))
        self.assertTrue(any("without release" in note for note in result["findings"]))

    def test_disabled_schedule_reset_has_no_unreleased_finding(self):
        result = assess_reset_request(sample_state(False))
        self.assertFalse(any("without release" in note for note in result["findings"]))

    def test_imminent_finding_raised_when_position_supplied(self):
        result = assess_reset_request(sample_state(), current_position_deg=5.0, arc_deg=10.0)
        self.assertEqual(len(result["imminent_discarded"]), 1)
        self.assertTrue(any("dropped unexecuted" in note for note in result["findings"]))

    def test_no_imminent_census_without_a_position(self):
        result = assess_reset_request(sample_state())
        self.assertEqual(result["imminent_discarded"], [])

    def test_invariants_reported_as_preserved(self):
        result = assess_reset_request(sample_state())
        self.assertTrue(result["enabled_state_preserved"])
        self.assertTrue(result["definitions_preserved"])

    def test_default_arc_is_a_fraction_of_a_revolution(self):
        self.assertLess(DEFAULT_IMMINENT_ARC_DEG, FULL_REVOLUTION_DEG / 4.0)

    def test_empty_schedule_reset_is_clean(self):
        state = sample_state()
        state["activities"] = []
        result = assess_reset_request(state, current_position_deg=0.0)
        self.assertEqual(result["discarded_total"], 0)
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
