"""Contract tests for the clause 6.22.6.4 set orbit number logic."""

import unittest

from e7041_set_the_orbit_number_logic import (
    JUMP_BACKWARD,
    JUMP_FORWARD,
    JUMP_NONE,
    SKIPPED_DISCARD,
    SKIPPED_KEEP,
    apply_set_orbit_number,
    group_activities_against_position,
    jump_direction,
    jump_magnitude,
    orbit_number_ceiling,
    validate_orbit_number,
)


def activity(request_id, orbit, angle):
    return {"request_id": request_id, "orbit_number": orbit, "angle_degrees": angle}


ACTIVITIES = [
    activity("beacon", 100, 90.0),
    activity("burn", 102, 90.0),
    activity("survey", 105, 90.0),
]


class OrbitNumberValidationTests(unittest.TestCase):
    def test_field_ceiling_is_two_to_the_width(self):
        self.assertEqual(orbit_number_ceiling(16), 65536)

    def test_an_orbit_number_inside_the_field_is_accepted(self):
        self.assertEqual(validate_orbit_number(65535, 16), 65535)

    def test_an_orbit_number_past_the_field_is_refused(self):
        with self.assertRaises(ValueError):
            validate_orbit_number(65536, 16)

    def test_a_negative_orbit_number_is_refused(self):
        with self.assertRaises(ValueError):
            validate_orbit_number(-1, 16)

    def test_a_non_integer_orbit_number_is_refused(self):
        with self.assertRaises(ValueError):
            validate_orbit_number(100.0, 16)

    def test_a_boolean_orbit_number_is_refused(self):
        with self.assertRaises(ValueError):
            validate_orbit_number(True, 16)

    def test_a_field_wider_than_the_model_limit_is_refused(self):
        with self.assertRaises(ValueError):
            orbit_number_ceiling(64)


class JumpTests(unittest.TestCase):
    def test_a_higher_orbit_number_is_a_forward_jump(self):
        self.assertEqual(jump_direction(100, 104), JUMP_FORWARD)

    def test_a_lower_orbit_number_is_a_backward_jump(self):
        self.assertEqual(jump_direction(100, 96), JUMP_BACKWARD)

    def test_the_same_orbit_number_is_no_jump(self):
        self.assertEqual(jump_direction(100, 100), JUMP_NONE)

    def test_the_magnitude_is_the_orbit_count_either_way(self):
        self.assertEqual(jump_magnitude(100, 104), 4)
        self.assertEqual(jump_magnitude(104, 100), 4)


class GroupingTests(unittest.TestCase):
    def test_activities_behind_the_position_are_past(self):
        grouped = group_activities_against_position(ACTIVITIES, 103, 90.0)
        self.assertEqual(grouped["past"], ("beacon", "burn"))

    def test_an_activity_at_the_position_is_due(self):
        grouped = group_activities_against_position(ACTIVITIES, 102, 90.0)
        self.assertEqual(grouped["due"], ("burn",))

    def test_activities_in_front_of_the_position_are_ahead(self):
        grouped = group_activities_against_position(ACTIVITIES, 101, 90.0)
        self.assertEqual(grouped["ahead"], ("burn", "survey"))

    def test_the_angle_separates_two_activities_on_one_orbit(self):
        pair = [activity("early", 100, 10.0), activity("late", 100, 300.0)]
        grouped = group_activities_against_position(pair, 100, 100.0)
        self.assertEqual(grouped["past"], ("early",))
        self.assertEqual(grouped["ahead"], ("late",))

    def test_a_duplicate_request_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            group_activities_against_position(
                [activity("beacon", 100, 10.0), activity("beacon", 101, 10.0)],
                100,
                0.0,
            )

    def test_an_angle_outside_a_revolution_is_refused(self):
        with self.assertRaises(ValueError):
            group_activities_against_position(ACTIVITIES, 100, 360.0)

    def test_a_non_sequence_activity_list_is_refused(self):
        with self.assertRaises(ValueError):
            group_activities_against_position({"beacon": 1}, 100, 0.0)


class SetOrbitNumberTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "current_orbit_number": 100,
            "new_orbit_number": 101,
            "angle_degrees": 90.0,
            "activities": ACTIVITIES,
            "orbit_number_bits": 16,
        }
        spec.update(overrides)
        return spec

    def test_a_small_forward_step_skipping_nothing_is_accepted(self):
        result = apply_set_orbit_number(self._spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["newly_skipped"], ())

    def test_the_jump_is_measured_and_named(self):
        result = apply_set_orbit_number(self._spec(new_orbit_number=104))
        self.assertEqual(result["jump_direction"], JUMP_FORWARD)
        self.assertEqual(result["jump_magnitude"], 4)

    def test_a_forward_jump_over_an_activity_names_it_skipped(self):
        result = apply_set_orbit_number(self._spec(new_orbit_number=104))
        self.assertEqual(result["newly_skipped"], ("burn",))
        self.assertFalse(result["accepted"])

    def test_a_skipped_activity_raises_a_finding(self):
        result = apply_set_orbit_number(self._spec(new_orbit_number=104))
        self.assertTrue(any("skipped by the change" in f for f in result["findings"]))

    def test_discarding_skipped_activities_drops_them_from_the_schedule(self):
        result = apply_set_orbit_number(
            self._spec(new_orbit_number=104, skipped_disposition=SKIPPED_DISCARD)
        )
        self.assertNotIn("burn", result["retained_activities"])
        self.assertIn("survey", result["retained_activities"])

    def test_keeping_skipped_activities_leaves_them_in_the_schedule(self):
        result = apply_set_orbit_number(
            self._spec(new_orbit_number=104, skipped_disposition=SKIPPED_KEEP)
        )
        self.assertIn("burn", result["retained_activities"])

    def test_a_backward_jump_returns_activities_to_the_future(self):
        result = apply_set_orbit_number(
            self._spec(current_orbit_number=103, new_orbit_number=100)
        )
        self.assertEqual(result["jump_direction"], JUMP_BACKWARD)
        self.assertEqual(result["returned_to_future"], ("burn",))
        self.assertFalse(result["accepted"])

    def test_a_backward_jump_raises_a_finding(self):
        result = apply_set_orbit_number(
            self._spec(current_orbit_number=103, new_orbit_number=100)
        )
        self.assertTrue(any("moves back by" in f for f in result["findings"]))

    def test_setting_the_number_already_held_is_reported_as_no_change(self):
        result = apply_set_orbit_number(self._spec(new_orbit_number=100))
        self.assertEqual(result["jump_direction"], JUMP_NONE)
        self.assertTrue(any("equals the one held" in f for f in result["findings"]))

    def test_an_activity_at_the_new_position_is_reported_due(self):
        result = apply_set_orbit_number(self._spec(new_orbit_number=102))
        self.assertEqual(result["due_activities"], ("burn",))

    def test_an_orbit_number_past_the_field_is_refused(self):
        with self.assertRaises(ValueError):
            apply_set_orbit_number(
                self._spec(new_orbit_number=300, orbit_number_bits=8)
            )

    def test_an_unknown_disposition_is_refused(self):
        with self.assertRaises(ValueError):
            apply_set_orbit_number(self._spec(skipped_disposition="defer"))

    def test_a_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["angle_degrees"]
        with self.assertRaises(ValueError):
            apply_set_orbit_number(spec)

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            apply_set_orbit_number(["activities"])


if __name__ == "__main__":
    unittest.main()
