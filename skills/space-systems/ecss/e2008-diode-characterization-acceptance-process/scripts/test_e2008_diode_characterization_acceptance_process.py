"""Contract tests for the clause 9.4.5.2.2 dark current-voltage recording logic."""

import unittest

from e2008_diode_characterization_acceptance_process_logic import (
    CURVE_RECORDING_INVALID,
    DARK_CONDITION_NOT_MET,
    DEFAULT_RECORDING_POLICY,
    IV_CURVES_RECORDED,
    SUPPLY_LIMIT_INSUFFICIENT,
    SUPPLY_LIMIT_UNSAFE,
    SWEEP_SCHEDULE_INADEQUATE,
    compliance_fraction_of_rating,
    compliance_headroom_fraction,
    curve_rises_across_range,
    dark_condition_met,
    point_is_supply_limited,
    record_diode_iv_curves,
    schedule_meets_step_rule,
    supply_limit_is_adequate,
    supply_limit_is_safe,
    supply_limited_points,
    sweep_schedule,
    validate_curve,
    validate_recording_policy,
    widest_gap_v,
)

GOOD_CURVE = [
    (0.00, 0.0),
    (0.20, 1.0e-9),
    (0.40, 4.0e-7),
    (0.60, 2.0e-2),
    (0.80, 1.1e0),
]


def _policy(**overrides):
    policy = dict(DEFAULT_RECORDING_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "bench": {
            "stray_irradiance_w_m2": 0.02,
            "compliance_limit_a": 2.0,
            "absolute_max_current_a": 6.0,
        },
        "forward": {
            "start_v": 0.0,
            "stop_v": 0.8,
            "step_v": 0.02,
            "max_test_current_a": 1.5,
        },
        "reverse": {"start_v": 0.0, "stop_v": 40.0, "step_v": 1.0},
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_recording_policy(DEFAULT_RECORDING_POLICY),
            DEFAULT_RECORDING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_recording_policy(("max_dark_irradiance_w_m2",))

    def test_zero_dark_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_recording_policy(_policy(max_dark_irradiance_w_m2=0.0))

    def test_zero_rating_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_recording_policy(_policy(max_compliance_fraction_of_rating=0.0))

    def test_rating_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_recording_policy(_policy(max_compliance_fraction_of_rating=1.5))

    def test_zero_forward_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_recording_policy(_policy(max_forward_step_v=0.0))


class DarkConditionTests(unittest.TestCase):
    def test_a_shuttered_bench_is_dark(self):
        self.assertTrue(dark_condition_met(0.01))

    def test_room_light_is_not_dark(self):
        self.assertFalse(dark_condition_met(8.0))

    def test_irradiance_exactly_on_the_floor_counts_as_dark(self):
        floor = float(DEFAULT_RECORDING_POLICY["max_dark_irradiance_w_m2"])
        self.assertAlmostEqual(floor, 1.0, places=9)
        self.assertTrue(dark_condition_met(floor))

    def test_negative_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            dark_condition_met(-0.1)


class SupplySizingTests(unittest.TestCase):
    def test_headroom_is_relative_to_the_demand(self):
        self.assertAlmostEqual(compliance_headroom_fraction(2.0, 1.6), 0.25, places=9)

    def test_rating_share_is_limit_over_rating(self):
        self.assertAlmostEqual(compliance_fraction_of_rating(2.0, 8.0), 0.25, places=9)

    def test_limit_below_the_sweep_top_is_inadequate(self):
        self.assertFalse(supply_limit_is_adequate(1.4, 1.5))

    def test_headroom_exactly_on_the_floor_is_adequate(self):
        floor = float(DEFAULT_RECORDING_POLICY["min_compliance_headroom_fraction"])
        headroom = compliance_headroom_fraction(1.1, 1.0)
        self.assertAlmostEqual(headroom, floor, places=9)
        self.assertTrue(supply_limit_is_adequate(1.1, 1.0))

    def test_share_exactly_on_the_rating_cap_is_safe(self):
        cap = float(DEFAULT_RECORDING_POLICY["max_compliance_fraction_of_rating"])
        share = compliance_fraction_of_rating(4.0, 5.0)
        self.assertAlmostEqual(share, cap, places=9)
        self.assertTrue(supply_limit_is_safe(4.0, 5.0))

    def test_limit_above_the_part_rating_is_unsafe(self):
        self.assertFalse(supply_limit_is_safe(7.0, 6.0))

    def test_zero_compliance_limit_rejected(self):
        with self.assertRaises(ValueError):
            compliance_headroom_fraction(0.0, 1.0)


class SweepScheduleTests(unittest.TestCase):
    def test_schedule_starts_and_stops_where_asked(self):
        points = sweep_schedule(0.0, 0.8, 0.2)
        self.assertAlmostEqual(points[0], 0.0, places=12)
        self.assertAlmostEqual(points[-1], 0.8, places=12)

    def test_an_uneven_span_still_reaches_the_stop(self):
        points = sweep_schedule(0.0, 0.75, 0.2)
        self.assertAlmostEqual(points[-1], 0.75, places=12)

    def test_step_wider_than_the_span_rejected(self):
        with self.assertRaises(ValueError):
            sweep_schedule(0.0, 0.1, 0.5)

    def test_a_branch_sweeping_backwards_rejected(self):
        with self.assertRaises(ValueError):
            sweep_schedule(0.8, 0.0, 0.05)

    def test_widest_gap_of_an_even_schedule_is_the_step(self):
        self.assertAlmostEqual(widest_gap_v(sweep_schedule(0.0, 1.0, 0.25)), 0.25,
                               places=9)

    def test_single_point_schedule_rejected(self):
        with self.assertRaises(ValueError):
            widest_gap_v([0.4])

    def test_non_advancing_points_rejected(self):
        with self.assertRaises(ValueError):
            widest_gap_v([0.0, 0.2, 0.2])

    def test_gap_exactly_on_the_step_rule_passes(self):
        rule = float(DEFAULT_RECORDING_POLICY["max_forward_step_v"])
        points = sweep_schedule(0.0, 0.5, rule)
        self.assertAlmostEqual(widest_gap_v(points), rule, places=9)
        self.assertTrue(schedule_meets_step_rule(points, rule))

    def test_a_coarse_schedule_fails_the_step_rule(self):
        self.assertFalse(schedule_meets_step_rule(sweep_schedule(0.0, 0.8, 0.4), 0.05))


class RecordedCurveTests(unittest.TestCase):
    def test_a_good_curve_validates(self):
        self.assertEqual(len(validate_curve(GOOD_CURVE)), len(GOOD_CURVE))

    def test_a_reading_that_is_not_a_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.0, 0.0), (0.2,)])

    def test_a_curve_that_does_not_advance_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.2, 1.0e-9), (0.2, 2.0e-9)])

    def test_a_one_reading_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.2, 1.0e-9)])

    def test_a_rising_curve_rises(self):
        self.assertTrue(curve_rises_across_range(GOOD_CURVE))

    def test_a_falling_point_is_caught(self):
        broken = list(GOOD_CURVE)
        broken[3] = (0.60, 1.0e-9)
        self.assertFalse(curve_rises_across_range(broken))

    def test_a_flat_pair_still_counts_as_rising(self):
        flat = [(0.0, 0.0), (0.2, 0.0), (0.4, 1.0e-7)]
        self.assertTrue(curve_rises_across_range(flat))

    def test_a_point_at_the_limit_is_supply_limited(self):
        self.assertTrue(point_is_supply_limited(2.0, 2.0))

    def test_a_point_below_the_limit_is_a_diode_datum(self):
        self.assertFalse(point_is_supply_limited(1.1, 2.0))

    def test_supply_limited_indices_name_the_clipped_points(self):
        clipped = list(GOOD_CURVE) + [(1.0, 2.0)]
        self.assertEqual(supply_limited_points(clipped, 2.0), (len(clipped) - 1,))


class RecordingVerdictTests(unittest.TestCase):
    def test_nominal_case_records_both_curves(self):
        result = record_diode_iv_curves(_case())
        self.assertEqual(result["verdict"], IV_CURVES_RECORDED)
        self.assertEqual(result["findings"], [])

    def test_a_lit_bench_stops_before_anything_else(self):
        case = _case()
        case["bench"]["stray_irradiance_w_m2"] = 40.0
        case["forward"]["step_v"] = 0.5
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], DARK_CONDITION_NOT_MET)
        self.assertIsNone(result["forward_points"])

    def test_an_unprotective_limit_is_reported_as_unsafe(self):
        case = _case()
        case["bench"]["compliance_limit_a"] = 5.5
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], SUPPLY_LIMIT_UNSAFE)

    def test_a_limit_under_the_sweep_top_is_insufficient(self):
        case = _case()
        case["bench"]["compliance_limit_a"] = 1.55
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], SUPPLY_LIMIT_INSUFFICIENT)

    def test_a_coarse_forward_schedule_is_inadequate(self):
        case = _case()
        case["forward"]["step_v"] = 0.4
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], SWEEP_SCHEDULE_INADEQUATE)

    def test_a_coarse_reverse_schedule_is_inadequate(self):
        case = _case()
        case["reverse"]["step_v"] = 10.0
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], SWEEP_SCHEDULE_INADEQUATE)

    def test_both_coarse_schedules_report_two_findings(self):
        case = _case()
        case["forward"]["step_v"] = 0.4
        case["reverse"]["step_v"] = 10.0
        result = record_diode_iv_curves(case)
        self.assertEqual(len(result["findings"]), 2)

    def test_a_clipped_recorded_curve_is_invalid(self):
        case = _case()
        case["forward"]["recorded_curve"] = list(GOOD_CURVE) + [(1.0, 2.0)]
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], CURVE_RECORDING_INVALID)
        self.assertTrue(result["supply_limited_indices"])

    def test_a_falling_recorded_curve_is_invalid(self):
        case = _case()
        broken = list(GOOD_CURVE)
        broken[3] = (0.60, 1.0e-9)
        case["forward"]["recorded_curve"] = broken
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], CURVE_RECORDING_INVALID)
        self.assertFalse(result["forward_curve_rises"])

    def test_a_clean_recorded_curve_passes(self):
        case = _case()
        case["forward"]["recorded_curve"] = list(GOOD_CURVE)
        result = record_diode_iv_curves(case)
        self.assertEqual(result["verdict"], IV_CURVES_RECORDED)
        self.assertEqual(result["supply_limited_indices"], ())

    def test_missing_bench_block_rejected(self):
        case = _case()
        del case["bench"]
        with self.assertRaises(ValueError):
            record_diode_iv_curves(case)

    def test_missing_reverse_block_rejected(self):
        case = _case()
        del case["reverse"]
        with self.assertRaises(ValueError):
            record_diode_iv_curves(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            record_diode_iv_curves(["bench"])


if __name__ == "__main__":
    unittest.main()
