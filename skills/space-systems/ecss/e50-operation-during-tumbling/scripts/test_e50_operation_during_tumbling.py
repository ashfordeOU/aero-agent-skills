"""Contract tests for the clause 5.6.11.2 tumbling operation logic."""

import unittest

from e50_operation_during_tumbling_logic import (
    NEVER_VISIBLE,
    OPERABLE,
    OUTAGE_TOO_LONG,
    WINDOW_TOO_SHORT,
    assess_tumbling_link,
    beam_separation_deg,
    duty_fraction,
    max_tumble_rate_deg_s,
    messages_per_window,
    outage_duration_s,
    required_beamwidth_deg,
    rotation_period_s,
    validate_angle_deg,
    validate_beamwidth_deg,
    validate_duration,
    validate_rate_deg_s,
    visibility_arc_deg,
    window_duration_s,
)

# An equatorial geometry: station and boresight both ninety degrees off the
# spin axis. There the separation equals the rotation phase, so the visibility
# arc is exactly the beam width and every expectation below is arithmetic done
# by hand rather than by the code under test.
ASPECT = 90.0
CONE = 90.0
BEAM = 60.0
RATE = 6.0


class ValidationTests(unittest.TestCase):
    def test_zero_angle_accepted(self):
        self.assertAlmostEqual(validate_angle_deg(0), 0.0, places=9)

    def test_angle_beyond_a_half_turn_rejected(self):
        with self.assertRaises(ValueError):
            validate_angle_deg(181.0)

    def test_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            validate_angle_deg(-1.0)

    def test_boolean_angle_rejected(self):
        with self.assertRaises(ValueError):
            validate_angle_deg(True)

    def test_text_angle_rejected(self):
        with self.assertRaises(ValueError):
            validate_angle_deg("90")

    def test_zero_beamwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_beamwidth_deg(0.0)

    def test_beamwidth_beyond_a_full_turn_rejected(self):
        with self.assertRaises(ValueError):
            validate_beamwidth_deg(361.0)

    def test_zero_tumble_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate_deg_s(0.0)

    def test_infinite_tumble_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate_deg_s(float("inf"))

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(-1.0)


class GeometryTests(unittest.TestCase):
    def test_equatorial_separation_equals_the_phase(self):
        self.assertAlmostEqual(beam_separation_deg(ASPECT, CONE, 30.0), 30.0, places=9)

    def test_separation_is_zero_when_the_beam_points_at_the_station(self):
        self.assertAlmostEqual(beam_separation_deg(ASPECT, CONE, 0.0), 0.0, places=9)

    def test_separation_is_a_half_turn_on_the_far_side(self):
        self.assertAlmostEqual(beam_separation_deg(ASPECT, CONE, 180.0), 180.0, places=9)

    def test_equatorial_arc_equals_the_beam_width(self):
        self.assertAlmostEqual(visibility_arc_deg(ASPECT, CONE, BEAM), BEAM, places=9)

    def test_a_wider_beam_widens_the_arc(self):
        self.assertGreater(visibility_arc_deg(ASPECT, CONE, 120.0), visibility_arc_deg(ASPECT, CONE, BEAM))

    def test_station_on_the_spin_axis_with_an_aligned_beam_is_always_visible(self):
        self.assertAlmostEqual(visibility_arc_deg(0.0, 0.0, BEAM), 360.0, places=9)

    def test_station_on_the_spin_axis_with_a_side_beam_is_never_visible(self):
        self.assertAlmostEqual(visibility_arc_deg(0.0, 90.0, BEAM), 0.0, places=9)

    def test_a_station_inside_a_fixed_beam_is_always_visible(self):
        self.assertAlmostEqual(visibility_arc_deg(10.0, 0.0, BEAM), 360.0, places=9)

    def test_a_full_sphere_beam_is_always_visible(self):
        self.assertAlmostEqual(visibility_arc_deg(ASPECT, CONE, 360.0), 360.0, places=9)

    def test_duty_fraction_is_the_arc_over_a_full_turn(self):
        self.assertAlmostEqual(duty_fraction(90.0), 0.25, places=9)

    def test_arc_beyond_a_full_turn_rejected(self):
        with self.assertRaises(ValueError):
            duty_fraction(400.0)


class TimingTests(unittest.TestCase):
    def test_rotation_period_from_the_tumble_rate(self):
        self.assertAlmostEqual(rotation_period_s(RATE), 60.0, places=9)

    def test_window_is_the_arc_over_the_rate(self):
        self.assertAlmostEqual(window_duration_s(BEAM, RATE), 10.0, places=9)

    def test_outage_is_the_rest_of_the_rotation(self):
        self.assertAlmostEqual(outage_duration_s(BEAM, RATE), 50.0, places=9)

    def test_no_arc_means_no_next_window(self):
        self.assertIsNone(outage_duration_s(0.0, RATE))

    def test_continuous_visibility_leaves_no_outage(self):
        self.assertAlmostEqual(outage_duration_s(360.0, RATE), 0.0, places=9)

    def test_faster_tumble_shortens_the_window(self):
        self.assertAlmostEqual(window_duration_s(BEAM, 12.0), 5.0, places=9)

    def test_messages_fit_after_setup_is_paid(self):
        self.assertEqual(messages_per_window(10.0, 4.0, 2.0), 3)

    def test_a_window_shorter_than_setup_carries_nothing(self):
        self.assertEqual(messages_per_window(3.0, 4.0, 2.0), 0)

    def test_zero_message_length_rejected(self):
        with self.assertRaises(ValueError):
            messages_per_window(10.0, 4.0, 0.0)


class InverseTests(unittest.TestCase):
    def test_required_beamwidth_reproduces_the_arc(self):
        self.assertAlmostEqual(required_beamwidth_deg(ASPECT, CONE, BEAM), BEAM, places=9)

    def test_required_beamwidth_round_trips_through_the_arc(self):
        width = required_beamwidth_deg(ASPECT, CONE, 120.0)
        self.assertAlmostEqual(visibility_arc_deg(ASPECT, CONE, width), 120.0, places=6)

    def test_a_degenerate_cone_cannot_deliver_a_partial_arc(self):
        self.assertIsNone(required_beamwidth_deg(0.0, 0.0, 120.0))

    def test_zero_arc_rejected_by_the_beamwidth_inverse(self):
        with self.assertRaises(ValueError):
            required_beamwidth_deg(ASPECT, CONE, 0.0)

    def test_max_rate_is_the_arc_over_the_needed_window(self):
        self.assertAlmostEqual(max_tumble_rate_deg_s(BEAM, 10.0), 6.0, places=9)

    def test_zero_required_window_rejected(self):
        with self.assertRaises(ValueError):
            max_tumble_rate_deg_s(BEAM, 0.0)


class AssessTests(unittest.TestCase):
    def test_a_workable_tumbling_geometry_passes(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 60.0)
        self.assertEqual(result["verdict"], OPERABLE)
        self.assertTrue(result["reachable"])

    def test_a_beam_that_never_sweeps_the_station_is_reported_as_geometry(self):
        result = assess_tumbling_link(0.0, 90.0, BEAM, RATE, 4.0, 2.0, 60.0)
        self.assertEqual(result["verdict"], NEVER_VISIBLE)
        self.assertTrue(any("not the problem" in f for f in result["findings"]))

    def test_a_fast_tumble_shortens_the_window_below_the_need(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, 30.0, 4.0, 2.0, 600.0)
        self.assertEqual(result["verdict"], WINDOW_TOO_SHORT)
        self.assertFalse(result["window_ok"])

    def test_a_window_exactly_equal_to_the_need_is_accepted(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 8.0, 2.0, 60.0)
        self.assertAlmostEqual(result["window_s"], result["required_window_s"], places=9)
        self.assertTrue(result["window_ok"])

    def test_a_long_outage_fails_even_with_a_good_window(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 10.0)
        self.assertEqual(result["verdict"], OUTAGE_TOO_LONG)
        self.assertTrue(result["window_ok"])

    def test_an_outage_exactly_on_the_budget_is_accepted(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 50.0)
        self.assertAlmostEqual(result["outage_s"], 50.0, places=9)
        self.assertEqual(result["verdict"], OPERABLE)

    def test_a_short_window_names_the_tolerable_tumble_rate(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, 30.0, 4.0, 2.0, 600.0)
        self.assertTrue(any("deg/s would" in f for f in result["findings"]))

    def test_a_long_outage_names_the_budget(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 10.0)
        self.assertTrue(any("operations" in f for f in result["findings"]))

    def test_a_compliant_geometry_reports_no_findings(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 60.0)
        self.assertEqual(result["findings"], [])

    def test_the_message_count_is_carried_in_the_result(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 60.0)
        self.assertEqual(result["messages_per_window"], 3)

    def test_duty_fraction_is_carried_in_the_result(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 2.0, 60.0)
        self.assertAlmostEqual(result["duty_fraction"], 1.0 / 6.0, places=9)

    def test_an_unreachable_station_reports_no_tolerable_rate(self):
        result = assess_tumbling_link(0.0, 90.0, BEAM, RATE, 4.0, 2.0, 60.0)
        self.assertIsNone(result["max_tumble_rate_deg_s"])
        self.assertIsNone(result["outage_s"])

    def test_stated_tolerable_rate_actually_gives_a_long_enough_window(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, 30.0, 4.0, 2.0, 600.0)
        fixed = assess_tumbling_link(
            ASPECT, CONE, BEAM, result["max_tumble_rate_deg_s"], 4.0, 2.0, 600.0
        )
        self.assertTrue(fixed["window_ok"])

    def test_stated_required_beamwidth_actually_gives_a_long_enough_window(self):
        result = assess_tumbling_link(ASPECT, CONE, BEAM, 30.0, 4.0, 2.0, 600.0)
        fixed = assess_tumbling_link(
            ASPECT, CONE, result["required_beamwidth_deg"], 30.0, 4.0, 2.0, 600.0
        )
        self.assertTrue(fixed["window_ok"])

    def test_zero_message_length_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_tumbling_link(ASPECT, CONE, BEAM, RATE, 4.0, 0.0, 60.0)

    def test_zero_tumble_rate_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_tumbling_link(ASPECT, CONE, BEAM, 0.0, 4.0, 2.0, 60.0)


if __name__ == "__main__":
    unittest.main()
