"""Contract tests for the clause 6.22.4 orbit position determination logic."""

import unittest

from e7041_determining_orbit_positions_logic import (
    DEGREES_PER_REVOLUTION,
    angle_within_revolution,
    angular_distance_degrees,
    group_scheduled_positions,
    has_been_passed,
    normalise_position,
    orbit_number_ceiling,
    position_key,
    positions_equal,
)


class AngleTests(unittest.TestCase):
    def test_zero_is_the_ascending_node(self):
        self.assertAlmostEqual(angle_within_revolution(0), 0.0, places=9)

    def test_angle_just_below_a_revolution_is_accepted(self):
        self.assertAlmostEqual(angle_within_revolution(359.5), 359.5, places=9)

    def test_a_whole_revolution_is_refused(self):
        with self.assertRaises(ValueError):
            angle_within_revolution(DEGREES_PER_REVOLUTION)

    def test_negative_angle_is_refused(self):
        with self.assertRaises(ValueError):
            angle_within_revolution(-0.5)

    def test_non_finite_angle_is_refused(self):
        with self.assertRaises(ValueError):
            angle_within_revolution(float("inf"))

    def test_boolean_angle_is_refused(self):
        with self.assertRaises(ValueError):
            angle_within_revolution(True)


class PositionTests(unittest.TestCase):
    def test_valid_position_is_normalised_to_a_pair(self):
        self.assertEqual(normalise_position((12, 90)), (12, 90.0))

    def test_orbit_number_outside_the_field_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_position((70000, 10), orbit_number_bits=16)

    def test_negative_orbit_number_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_position((-1, 10))

    def test_three_item_position_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_position((1, 2, 3))

    def test_orbit_number_field_ceiling_is_two_to_the_width(self):
        self.assertEqual(orbit_number_ceiling(16), 65536)

    def test_orbit_number_field_wider_than_the_model_limit_is_refused(self):
        with self.assertRaises(ValueError):
            orbit_number_ceiling(64)


class OrderingTests(unittest.TestCase):
    def test_key_counts_whole_revolutions_then_the_angle(self):
        self.assertAlmostEqual(position_key((2, 90.0)), 810.0, places=9)

    def test_ascending_node_of_the_next_orbit_outranks_the_end_of_this_one(self):
        self.assertLess(position_key((2, 359.0)), position_key((3, 0.0)))

    def test_same_point_compares_equal(self):
        self.assertTrue(positions_equal((5, 120.0), (5, 120.0)))

    def test_same_angle_on_another_orbit_is_not_the_same_position(self):
        self.assertFalse(positions_equal((5, 120.0), (6, 120.0)))

    def test_float_noise_below_tolerance_still_compares_equal(self):
        self.assertTrue(positions_equal((5, 120.0), (5, 120.0 + 1e-12)))


class DistanceTests(unittest.TestCase):
    def test_forward_distance_within_one_orbit(self):
        self.assertAlmostEqual(
            angular_distance_degrees((4, 30.0), (4, 100.0)), 70.0, places=9
        )

    def test_distance_crosses_the_ascending_node(self):
        self.assertAlmostEqual(
            angular_distance_degrees((4, 350.0), (5, 10.0)), 20.0, places=9
        )

    def test_distance_to_the_same_position_is_nothing(self):
        self.assertAlmostEqual(
            angular_distance_degrees((4, 30.0), (4, 30.0)), 0.0, places=9
        )

    def test_a_target_behind_the_origin_is_reached_after_the_counter_wraps(self):
        # 4 bit field: 16 orbits of 360 degrees = 5760 degrees around.
        self.assertAlmostEqual(
            angular_distance_degrees((10, 0.0), (2, 0.0), orbit_number_bits=4),
            5760.0 - 2880.0,
            places=9,
        )

    def test_distance_spans_whole_orbits(self):
        self.assertAlmostEqual(
            angular_distance_degrees((4, 0.0), (7, 0.0)), 1080.0, places=9
        )


class PassedTests(unittest.TestCase):
    def test_a_position_behind_the_current_one_has_been_passed(self):
        self.assertTrue(has_been_passed((9, 100.0), (9, 40.0)))

    def test_a_position_ahead_has_not_been_passed(self):
        self.assertFalse(has_been_passed((9, 100.0), (9, 140.0)))

    def test_the_current_position_counts_as_passed(self):
        self.assertTrue(has_been_passed((9, 100.0), (9, 100.0)))

    def test_an_earlier_orbit_has_been_passed_whatever_the_angle(self):
        self.assertTrue(has_been_passed((9, 10.0), (8, 350.0)))


class GroupingTests(unittest.TestCase):
    def _positions(self):
        return {
            "apogee-burn": (9, 40.0),
            "ground-pass": (9, 200.0),
            "eclipse-entry": (10, 15.0),
        }

    def test_passed_and_pending_are_separated(self):
        result = group_scheduled_positions((9, 100.0), self._positions())
        self.assertEqual([label for label, _ in result["passed"]], ["apogee-burn"])
        self.assertEqual(
            sorted(label for label, _ in result["pending"]),
            ["eclipse-entry", "ground-pass"],
        )

    def test_nearest_pending_position_is_named(self):
        result = group_scheduled_positions((9, 100.0), self._positions())
        self.assertEqual(result["next_position_label"], "ground-pass")

    def test_degrees_to_go_are_measured_forward(self):
        result = group_scheduled_positions((9, 100.0), self._positions())
        self.assertAlmostEqual(result["degrees_to_go"]["ground-pass"], 100.0, places=9)
        self.assertAlmostEqual(
            result["degrees_to_go"]["eclipse-entry"], 275.0, places=9
        )

    def test_everything_passed_leaves_no_next_position(self):
        result = group_scheduled_positions((12, 0.0), self._positions())
        self.assertEqual(result["pending"], ())
        self.assertIsNone(result["next_position_label"])

    def test_empty_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            group_scheduled_positions((9, 100.0), {})

    def test_non_mapping_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            group_scheduled_positions((9, 100.0), [(9, 40.0)])

    def test_blank_label_is_refused(self):
        with self.assertRaises(ValueError):
            group_scheduled_positions((9, 100.0), {"  ": (9, 40.0)})


if __name__ == "__main__":
    unittest.main()
