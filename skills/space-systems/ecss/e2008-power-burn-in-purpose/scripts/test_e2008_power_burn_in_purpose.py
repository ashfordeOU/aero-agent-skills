"""Contract tests for the clause 12.6.7.2.1 power burn purpose logic."""

import unittest

from e2008_power_burn_in_purpose_logic import (
    AXIS_CATEGORIES,
    DEFAULT_POWER_BURN_POLICY,
    FORWARD_CURRENT,
    OPERATION_SIMULATED,
    PURPOSE_MET,
    PURPOSE_NOT_EVALUATED,
    PURPOSE_UNMET,
    REVERSE_VOLTAGE,
    STAGE_VERDICTS,
    STRESS_AXES,
    STRESS_BELOW_OPERATION,
    STRESS_BEYOND_REGIME,
    STRESS_NOT_REPRESENTATIVE,
    assess_power_burn_purpose,
    axis_acceleration,
    categorize_stress_axis,
    combined_acceleration,
    simulated_field_hours,
    stress_ratio,
    validate_power_burn_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_POWER_BURN_POLICY)
    policy.update(overrides)
    return policy


def _axes(forward_applied=2.0, reverse_applied=1.5):
    return {
        FORWARD_CURRENT: {"applied": forward_applied, "in_service": 1.0},
        REVERSE_VOLTAGE: {"applied": reverse_applied, "in_service": 1.0},
    }


def _stage(**overrides):
    stage = {
        "duration_h": 168.0,
        "duty_fraction": 0.8,
        "axes": _axes(),
    }
    stage.update(overrides)
    return stage


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_power_burn_policy(DEFAULT_POWER_BURN_POLICY),
            DEFAULT_POWER_BURN_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_policy("burn")

    def test_a_ceiling_at_the_operating_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_policy(_policy(max_stress_ratio=1.0))

    def test_a_ceiling_below_the_operating_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_policy(_policy(max_stress_ratio=0.5))

    def test_an_acceleration_floor_under_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_policy(_policy(min_combined_acceleration=0.5))

    def test_a_duty_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_policy(_policy(min_duty_fraction=1.5))

    def test_a_negative_exponent_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_policy(_policy(reverse_voltage_exponent=-2.0))

    def test_every_verdict_axis_and_category_is_declared(self):
        self.assertEqual(len(set(STAGE_VERDICTS)), 4)
        self.assertEqual(len(set(AXIS_CATEGORIES)), 3)
        self.assertEqual(len(set(STRESS_AXES)), 2)


class StressRatioTests(unittest.TestCase):
    def test_the_operating_point_itself_is_unity(self):
        self.assertAlmostEqual(stress_ratio(1.0, 1.0), 1.0, places=12)

    def test_a_driven_axis_reports_its_multiple(self):
        self.assertAlmostEqual(stress_ratio(3.0, 1.2), 2.5, places=9)

    def test_a_zero_in_service_point_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(2.0, 0.0)

    def test_a_negative_applied_point_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(-2.0, 1.0)


class AccelerationTests(unittest.TestCase):
    def test_an_axis_earns_its_ratio_raised_to_the_exponent(self):
        self.assertAlmostEqual(axis_acceleration(2.0, 2.0), 4.0, places=9)

    def test_an_axis_at_the_operating_point_earns_nothing(self):
        self.assertAlmostEqual(axis_acceleration(1.0, 3.0), 1.0, places=12)

    def test_a_zero_ratio_rejected(self):
        with self.assertRaises(ValueError):
            axis_acceleration(0.0, 2.0)

    def test_a_zero_exponent_rejected(self):
        with self.assertRaises(ValueError):
            axis_acceleration(2.0, 0.0)

    def test_the_axes_multiply_into_one_acceleration(self):
        self.assertAlmostEqual(combined_acceleration(_axes()), 13.5, places=9)

    def test_an_unstressed_axis_rejected(self):
        with self.assertRaises(ValueError):
            combined_acceleration(
                {FORWARD_CURRENT: {"applied": 2.0, "in_service": 1.0}}
            )

    def test_an_unrecognised_axis_rejected(self):
        axes = _axes()
        axes["case-temperature"] = {"applied": 2.0, "in_service": 1.0}
        with self.assertRaises(ValueError):
            combined_acceleration(axes)

    def test_a_malformed_axis_pair_rejected(self):
        axes = _axes()
        axes[REVERSE_VOLTAGE] = 1.5
        with self.assertRaises(ValueError):
            combined_acceleration(axes)

    def test_an_empty_axes_mapping_rejected(self):
        with self.assertRaises(ValueError):
            combined_acceleration({})


class AxisGroupingTests(unittest.TestCase):
    def test_a_driven_axis_simulates_operation(self):
        self.assertEqual(categorize_stress_axis(2.0), OPERATION_SIMULATED)

    def test_an_axis_exactly_at_the_operating_point_still_simulates_it(self):
        self.assertEqual(categorize_stress_axis(1.0), OPERATION_SIMULATED)

    def test_an_axis_exactly_at_the_regime_ceiling_is_accepted(self):
        policy = _policy()
        ceiling = float(policy["max_stress_ratio"])
        self.assertAlmostEqual(ceiling, policy["max_stress_ratio"], places=9)
        self.assertEqual(
            categorize_stress_axis(ceiling, policy), OPERATION_SIMULATED
        )

    def test_an_axis_under_its_operating_point_is_below_operation(self):
        self.assertEqual(categorize_stress_axis(0.5), STRESS_BELOW_OPERATION)

    def test_an_axis_past_the_ceiling_leaves_the_regime(self):
        self.assertEqual(categorize_stress_axis(5.0), STRESS_BEYOND_REGIME)

    def test_a_zero_ratio_rejected(self):
        with self.assertRaises(ValueError):
            categorize_stress_axis(0.0)


class SimulatedHoursTests(unittest.TestCase):
    def test_hours_are_duty_time_times_acceleration(self):
        self.assertAlmostEqual(
            simulated_field_hours(100.0, 1.0, 4.0), 400.0, places=9
        )

    def test_a_part_idle_half_the_soak_buys_half_the_hours(self):
        self.assertAlmostEqual(
            simulated_field_hours(100.0, 0.5, 4.0), 200.0, places=9
        )

    def test_a_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            simulated_field_hours(0.0, 1.0, 4.0)

    def test_a_zero_duty_rejected(self):
        with self.assertRaises(ValueError):
            simulated_field_hours(100.0, 0.0, 4.0)

    def test_a_zero_acceleration_rejected(self):
        with self.assertRaises(ValueError):
            simulated_field_hours(100.0, 1.0, 0.0)


class StageAssessmentTests(unittest.TestCase):
    def test_a_stage_that_accelerates_real_operation_meets_its_purpose(self):
        result = assess_power_burn_purpose(_stage())
        self.assertEqual(result["verdict"], PURPOSE_MET)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["combined_acceleration"], 13.5, places=9)

    def test_a_stage_too_short_to_judge_is_not_evaluated(self):
        result = assess_power_burn_purpose(_stage(duration_h=5.0))
        self.assertEqual(result["verdict"], PURPOSE_NOT_EVALUATED)

    def test_a_duration_exactly_at_the_floor_clears_the_not_run_gate(self):
        policy = _policy()
        floor = float(policy["min_stage_duration_h"])
        result = assess_power_burn_purpose(_stage(duration_h=floor), policy)
        self.assertAlmostEqual(result["duration_h"], floor, places=9)
        self.assertNotEqual(result["verdict"], PURPOSE_NOT_EVALUATED)

    def test_a_short_stage_outranks_an_unrepresentative_axis(self):
        result = assess_power_burn_purpose(
            _stage(duration_h=5.0, axes=_axes(forward_applied=0.5))
        )
        self.assertEqual(result["verdict"], PURPOSE_NOT_EVALUATED)

    def test_an_axis_below_operation_is_not_representative(self):
        result = assess_power_burn_purpose(
            _stage(axes=_axes(forward_applied=0.5))
        )
        self.assertEqual(result["verdict"], STRESS_NOT_REPRESENTATIVE)
        self.assertEqual(
            result["axis_categories"][FORWARD_CURRENT], STRESS_BELOW_OPERATION
        )

    def test_an_axis_past_the_regime_ceiling_is_not_representative(self):
        result = assess_power_burn_purpose(
            _stage(axes=_axes(forward_applied=9.0))
        )
        self.assertEqual(result["verdict"], STRESS_NOT_REPRESENTATIVE)
        self.assertEqual(
            result["axis_categories"][FORWARD_CURRENT], STRESS_BEYOND_REGIME
        )

    def test_a_mostly_idle_soak_is_not_representative(self):
        result = assess_power_burn_purpose(_stage(duty_fraction=0.2))
        self.assertEqual(result["verdict"], STRESS_NOT_REPRESENTATIVE)

    def test_a_stage_that_only_reproduces_operation_is_not_accelerated(self):
        result = assess_power_burn_purpose(
            _stage(axes=_axes(forward_applied=1.0, reverse_applied=1.0))
        )
        self.assertEqual(result["verdict"], STRESS_NOT_REPRESENTATIVE)
        self.assertAlmostEqual(result["combined_acceleration"], 1.0, places=12)

    def test_an_acceleration_exactly_at_its_floor_is_representative(self):
        policy = _policy(min_combined_acceleration=4.0, min_simulated_field_hours=400.0)
        stage = _stage(
            duration_h=100.0,
            duty_fraction=1.0,
            axes=_axes(forward_applied=2.0, reverse_applied=1.0),
        )
        result = assess_power_burn_purpose(stage, policy)
        self.assertAlmostEqual(
            result["combined_acceleration"],
            policy["min_combined_acceleration"],
            places=9,
        )
        self.assertEqual(result["verdict"], PURPOSE_MET)

    def test_field_hours_exactly_at_the_floor_meet_the_purpose(self):
        policy = _policy(min_simulated_field_hours=400.0)
        stage = _stage(
            duration_h=100.0,
            duty_fraction=1.0,
            axes=_axes(forward_applied=2.0, reverse_applied=1.0),
        )
        result = assess_power_burn_purpose(stage, policy)
        self.assertAlmostEqual(
            result["simulated_field_hours"],
            policy["min_simulated_field_hours"],
            places=9,
        )
        self.assertEqual(result["verdict"], PURPOSE_MET)

    def test_an_unrepresentative_stress_outranks_a_thin_field_equivalence(self):
        result = assess_power_burn_purpose(
            _stage(duration_h=30.0, axes=_axes(forward_applied=0.5))
        )
        self.assertEqual(result["verdict"], STRESS_NOT_REPRESENTATIVE)

    def test_a_representative_but_thin_stage_leaves_the_purpose_unmet(self):
        result = assess_power_burn_purpose(_stage(duration_h=30.0))
        self.assertEqual(result["verdict"], PURPOSE_UNMET)
        self.assertEqual(len(result["findings"]), 1)

    def test_the_ratio_of_every_axis_is_reported(self):
        result = assess_power_burn_purpose(_stage())
        self.assertAlmostEqual(
            result["stress_ratios"][FORWARD_CURRENT], 2.0, places=9
        )
        self.assertAlmostEqual(
            result["stress_ratios"][REVERSE_VOLTAGE], 1.5, places=9
        )

    def test_a_non_mapping_stage_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_burn_purpose(["duration"])

    def test_a_stage_with_no_axes_rejected(self):
        stage = _stage()
        stage["axes"] = {}
        with self.assertRaises(ValueError):
            assess_power_burn_purpose(stage)

    def test_a_stage_leaving_the_reverse_axis_out_rejected(self):
        stage = _stage()
        del stage["axes"][REVERSE_VOLTAGE]
        with self.assertRaises(ValueError):
            assess_power_burn_purpose(stage)

    def test_a_stage_carrying_an_unrecognised_axis_rejected(self):
        stage = _stage()
        stage["axes"]["case-temperature"] = {"applied": 2.0, "in_service": 1.0}
        with self.assertRaises(ValueError):
            assess_power_burn_purpose(stage)

    def test_a_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_burn_purpose(_stage(duration_h=0.0))

    def test_a_duty_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_burn_purpose(_stage(duty_fraction=1.4))


if __name__ == "__main__":
    unittest.main()
