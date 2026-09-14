"""Contract tests for the clause 6.4.3.19.2 angular sweep process logic."""

import math
import unittest

from e2008_angular_performance_test_process_logic import (
    ANGULAR_SWEEP_ACCEPTED,
    ANGULAR_SWEEP_NOT_PLANNED,
    ANGULAR_SWEEP_TRUNCATED,
    ANGULAR_SWEEP_UNDERSAMPLED,
    DEFAULT_SWEEP_POLICY,
    assess_angular_sweep,
    interpolation_error_bound,
    largest_gap_deg,
    missing_schedule_angles,
    normalise_measured_angles,
    planned_angle_schedule,
    step_for_angle,
    sweep_reaches_maximum,
    validate_sweep_policy,
    worst_interpolation_error,
)

FULL_SWEEP = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0]


def _policy(**overrides):
    policy = dict(DEFAULT_SWEEP_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {"measured_angles_deg": list(FULL_SWEEP)}
    case.update(overrides)
    return case


def _without(*dropped):
    return [angle for angle in FULL_SWEEP if angle not in dropped]


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_sweep_policy(DEFAULT_SWEEP_POLICY), DEFAULT_SWEEP_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy("breakpoint")

    def test_a_refined_step_wider_than_the_coarse_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(coarse_step_deg=5.0, refined_step_deg=10.0))

    def test_equal_steps_rejected_because_nothing_refines(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(coarse_step_deg=10.0, refined_step_deg=10.0))

    def test_a_ceiling_below_the_breakpoint_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(max_sweep_angle_deg=45.0))

    def test_a_breakpoint_at_normal_incidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(step_breakpoint_deg=0.0))

    def test_an_error_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(max_interpolation_error_fraction=1.5))

    def test_a_negative_match_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(angle_match_tolerance_deg=-0.1))


class ScheduleTests(unittest.TestCase):
    def test_the_default_schedule_is_the_expected_series(self):
        self.assertEqual(planned_angle_schedule(), tuple(FULL_SWEEP))

    def test_the_schedule_starts_at_normal_incidence(self):
        self.assertAlmostEqual(planned_angle_schedule()[0], 0.0, places=9)

    def test_the_schedule_ends_at_the_declared_maximum(self):
        policy = _policy()
        self.assertAlmostEqual(
            planned_angle_schedule(policy)[-1], policy["max_sweep_angle_deg"], places=9
        )

    def test_the_breakpoint_is_always_measured(self):
        self.assertIn(60.0, planned_angle_schedule())

    def test_steps_up_to_the_breakpoint_are_coarse(self):
        schedule = planned_angle_schedule()
        coarse = [a for a in schedule if a <= 60.0]
        for earlier, later in zip(coarse, coarse[1:]):
            self.assertAlmostEqual(later - earlier, 10.0, places=9)

    def test_steps_past_the_breakpoint_are_refined(self):
        schedule = planned_angle_schedule()
        refined = [a for a in schedule if a >= 60.0]
        for earlier, later in zip(refined, refined[1:]):
            self.assertAlmostEqual(later - earlier, 5.0, places=9)

    def test_a_breakpoint_off_the_coarse_grid_is_still_scheduled(self):
        schedule = planned_angle_schedule(_policy(step_breakpoint_deg=55.0))
        self.assertIn(55.0, schedule)
        self.assertIn(50.0, schedule)

    def test_a_ceiling_off_the_refined_grid_is_still_scheduled(self):
        schedule = planned_angle_schedule(_policy(max_sweep_angle_deg=83.0))
        self.assertAlmostEqual(schedule[-1], 83.0, places=9)

    def test_the_step_at_the_breakpoint_is_the_refined_one(self):
        self.assertAlmostEqual(step_for_angle(60.0), 5.0, places=9)

    def test_the_step_below_the_breakpoint_is_the_coarse_one(self):
        self.assertAlmostEqual(step_for_angle(50.0), 10.0, places=9)

    def test_the_step_past_the_breakpoint_is_the_refined_one(self):
        self.assertAlmostEqual(step_for_angle(70.0), 5.0, places=9)

    def test_an_edge_on_angle_rejected(self):
        with self.assertRaises(ValueError):
            step_for_angle(90.0)


class MeasuredAngleTests(unittest.TestCase):
    def test_measured_angles_come_back_sorted(self):
        self.assertEqual(
            normalise_measured_angles([30.0, 0.0, 10.0]), (0.0, 10.0, 30.0)
        )

    def test_a_repeat_inside_the_tolerance_is_grouped_away(self):
        self.assertEqual(normalise_measured_angles([30.0, 30.2]), (30.0,))

    def test_two_distinct_angles_survive(self):
        self.assertEqual(normalise_measured_angles([30.0, 31.0]), (30.0, 31.0))

    def test_a_non_collection_angle_list_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measured_angles(30.0)

    def test_a_negative_measured_angle_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measured_angles([-5.0, 10.0])

    def test_a_boolean_measured_angle_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measured_angles([True, 10.0])

    def test_the_full_sweep_misses_no_scheduled_angle(self):
        self.assertEqual(missing_schedule_angles(FULL_SWEEP), ())

    def test_a_dropped_angle_is_reported_missing(self):
        self.assertEqual(missing_schedule_angles(_without(70.0)), (70.0,))

    def test_an_angle_inside_the_match_tolerance_is_not_missing(self):
        measured = _without(70.0) + [70.3]
        self.assertEqual(missing_schedule_angles(measured), ())


class GapTests(unittest.TestCase):
    def test_the_full_coarse_region_gap_is_the_coarse_step(self):
        self.assertAlmostEqual(largest_gap_deg(FULL_SWEEP, 0.0, 60.0), 10.0, places=9)

    def test_the_full_refined_region_gap_is_the_refined_step(self):
        self.assertAlmostEqual(largest_gap_deg(FULL_SWEEP, 60.0, 85.0), 5.0, places=9)

    def test_a_dropped_point_widens_the_gap(self):
        self.assertAlmostEqual(
            largest_gap_deg(_without(30.0), 0.0, 60.0), 20.0, places=9
        )

    def test_a_region_with_one_point_rejected(self):
        with self.assertRaises(ValueError):
            largest_gap_deg([0.0, 85.0], 60.0, 80.0)

    def test_an_inverted_region_rejected(self):
        with self.assertRaises(ValueError):
            largest_gap_deg(FULL_SWEEP, 60.0, 10.0)

    def test_the_error_bound_follows_the_interpolation_formula(self):
        step_rad = math.radians(10.0)
        expected = step_rad * step_rad / 8.0 * math.cos(math.radians(20.0))
        self.assertAlmostEqual(
            _ratio(interpolation_error_bound(10.0, 20.0), expected), 1.0, places=12
        )

    def test_a_wider_step_admits_more_error(self):
        self.assertLess(
            interpolation_error_bound(5.0, 20.0), interpolation_error_bound(20.0, 20.0)
        )

    def test_the_cosine_term_shrinks_the_bound_at_a_wide_angle(self):
        self.assertLess(
            interpolation_error_bound(10.0, 80.0), interpolation_error_bound(10.0, 10.0)
        )

    def test_a_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            interpolation_error_bound(0.0, 20.0)

    def test_the_worst_error_comes_from_the_widest_early_gap(self):
        expected = interpolation_error_bound(10.0, 0.0)
        self.assertAlmostEqual(
            _ratio(worst_interpolation_error(FULL_SWEEP), expected), 1.0, places=12
        )

    def test_a_single_angle_has_no_interpolation_error(self):
        with self.assertRaises(ValueError):
            worst_interpolation_error([0.0])


class ReachTests(unittest.TestCase):
    def test_the_full_sweep_reaches_the_maximum(self):
        self.assertTrue(sweep_reaches_maximum(FULL_SWEEP))

    def test_a_sweep_inside_the_match_tolerance_reaches_the_maximum(self):
        self.assertTrue(sweep_reaches_maximum(_without(85.0) + [84.7]))

    def test_a_sweep_stopping_at_the_breakpoint_does_not_reach_it(self):
        self.assertFalse(sweep_reaches_maximum([a for a in FULL_SWEEP if a <= 60.0]))

    def test_an_empty_sweep_does_not_reach_it(self):
        self.assertFalse(sweep_reaches_maximum([]))


class SweepAssessmentTests(unittest.TestCase):
    def test_the_scheduled_sweep_is_accepted(self):
        result = assess_angular_sweep(_case())
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_region_gaps_are_reported(self):
        result = assess_angular_sweep(_case())
        self.assertAlmostEqual(result["coarse_region_gap_deg"], 10.0, places=9)
        self.assertAlmostEqual(result["refined_region_gap_deg"], 5.0, places=9)

    def test_the_point_count_is_reported(self):
        result = assess_angular_sweep(_case())
        self.assertEqual(result["point_count"], len(FULL_SWEEP))

    def test_a_single_measured_angle_is_not_a_sweep(self):
        result = assess_angular_sweep(_case(measured_angles_deg=[0.0]))
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_NOT_PLANNED)

    def test_a_sweep_stopping_at_the_breakpoint_is_truncated(self):
        result = assess_angular_sweep(
            _case(measured_angles_deg=[a for a in FULL_SWEEP if a <= 60.0])
        )
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_TRUNCATED)
        self.assertIsNone(result["refined_region_gap_deg"])

    def test_a_coarse_gap_wider_than_the_step_is_undersampled(self):
        result = assess_angular_sweep(_case(measured_angles_deg=_without(30.0)))
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_UNDERSAMPLED)
        self.assertAlmostEqual(result["coarse_region_gap_deg"], 20.0, places=9)

    def test_a_refined_gap_wider_than_the_step_is_undersampled(self):
        result = assess_angular_sweep(_case(measured_angles_deg=_without(70.0, 75.0)))
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_UNDERSAMPLED)
        self.assertAlmostEqual(result["refined_region_gap_deg"], 15.0, places=9)

    def test_a_coarse_step_carried_past_the_breakpoint_is_undersampled(self):
        measured = [a for a in FULL_SWEEP if a <= 60.0] + [70.0, 80.0, 85.0]
        result = assess_angular_sweep(_case(measured_angles_deg=measured))
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_UNDERSAMPLED)
        self.assertAlmostEqual(result["refined_region_gap_deg"], 10.0, places=9)

    def test_a_sweep_starting_at_the_breakpoint_loses_the_coarse_region(self):
        measured = [a for a in FULL_SWEEP if a >= 60.0]
        result = assess_angular_sweep(_case(measured_angles_deg=measured))
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_UNDERSAMPLED)
        self.assertIsNone(result["coarse_region_gap_deg"])

    def test_missing_scheduled_angles_are_listed(self):
        result = assess_angular_sweep(_case(measured_angles_deg=_without(70.0, 75.0)))
        self.assertEqual(result["missing_angles_deg"], (70.0, 75.0))

    def test_a_tight_error_allowance_rejects_the_default_schedule(self):
        result = assess_angular_sweep(
            _case(), _policy(max_interpolation_error_fraction=1.0e-4)
        )
        self.assertEqual(result["verdict"], ANGULAR_SWEEP_UNDERSAMPLED)

    def test_the_worst_interpolation_error_is_reported(self):
        result = assess_angular_sweep(_case())
        expected = interpolation_error_bound(10.0, 0.0)
        self.assertAlmostEqual(
            _ratio(result["worst_interpolation_error_fraction"], expected),
            1.0,
            places=12,
        )

    def test_both_a_gap_and_a_missing_angle_are_reported(self):
        result = assess_angular_sweep(_case(measured_angles_deg=_without(70.0, 75.0)))
        self.assertEqual(len(result["findings"]), 2)

    def test_absent_angle_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_angular_sweep({})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_angular_sweep(list(FULL_SWEEP))


if __name__ == "__main__":
    unittest.main()
