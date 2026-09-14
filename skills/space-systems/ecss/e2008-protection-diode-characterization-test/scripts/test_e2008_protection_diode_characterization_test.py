"""Contract tests for the clause 9.6.15 bracketed characterization logic."""

import unittest

from e2008_protection_diode_characterization_test_logic import (
    CHARACTERIZATION_ACCEPTED,
    CHARACTERIZATION_VERDICTS,
    DEFAULT_CHARACTERIZATION_POLICY,
    DEGRADATION_DETECTED,
    MEASUREMENT_SET_INCOMPLETE,
    REFERENCE_CONDITION_MISMATCH,
    REFERENCE_CONDITION_FIELDS,
    REQUIRED_PARAMETERS,
    assess_diode_characterization,
    drop_fraction,
    growth_fraction,
    growth_ratio,
    missing_parameters,
    missing_reference_conditions,
    parameter_drifts,
    reference_condition_deltas,
    relative_drift,
    validate_characterization_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CHARACTERIZATION_POLICY)
    policy.update(overrides)
    return policy


def _baseline(**overrides):
    measurement = {
        "junction_temperature_c": 25.0,
        "test_current_a": 2.0,
        "forward_voltage_v": 0.520,
        "reverse_leakage_a": 1.0e-9,
        "breakdown_voltage_v": 60.0,
        "series_resistance_ohm": 0.0100,
    }
    measurement.update(overrides)
    return measurement


def _followup(**overrides):
    measurement = {
        "junction_temperature_c": 25.5,
        "test_current_a": 2.0,
        "forward_voltage_v": 0.524,
        "reverse_leakage_a": 3.0e-9,
        "breakdown_voltage_v": 59.5,
        "series_resistance_ohm": 0.0105,
    }
    measurement.update(overrides)
    return measurement


def _case(**overrides):
    case = {
        "characterized_devices": 6,
        "baseline": _baseline(),
        "followup": _followup(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_characterization_policy(DEFAULT_CHARACTERIZATION_POLICY),
            DEFAULT_CHARACTERIZATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy("bracket")

    def test_a_leakage_growth_ceiling_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(max_reverse_leakage_growth_ratio=1.0)
            )

    def test_a_forward_drift_ceiling_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(max_forward_voltage_drift_fraction=1.0)
            )

    def test_a_zero_temperature_gap_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(max_junction_temperature_delta_k=0.0)
            )

    def test_a_fractional_device_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(_policy(min_characterized_devices=4.5))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(CHARACTERIZATION_VERDICTS)), 4)

    def test_the_required_parameter_set_is_declared(self):
        self.assertEqual(len(set(REQUIRED_PARAMETERS)), 4)
        self.assertEqual(len(set(REFERENCE_CONDITION_FIELDS)), 2)


class CompletenessTests(unittest.TestCase):
    def test_a_full_measurement_is_missing_nothing(self):
        self.assertEqual(missing_parameters(_baseline()), ())

    def test_an_absent_parameter_is_reported_missing(self):
        measurement = _baseline()
        del measurement["breakdown_voltage_v"]
        self.assertEqual(missing_parameters(measurement), ("breakdown_voltage_v",))

    def test_a_zero_parameter_is_reported_missing(self):
        measurement = _baseline()
        measurement["reverse_leakage_a"] = 0.0
        self.assertEqual(missing_parameters(measurement), ("reverse_leakage_a",))

    def test_a_non_numeric_parameter_is_reported_missing(self):
        measurement = _baseline()
        measurement["forward_voltage_v"] = "0.52"
        self.assertEqual(missing_parameters(measurement), ("forward_voltage_v",))

    def test_several_absent_parameters_are_all_reported(self):
        measurement = _baseline()
        del measurement["forward_voltage_v"]
        del measurement["series_resistance_ohm"]
        self.assertEqual(
            missing_parameters(measurement),
            ("forward_voltage_v", "series_resistance_ohm"),
        )

    def test_a_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            missing_parameters([0.52, 1.0e-9])

    def test_a_full_measurement_carries_its_reference_conditions(self):
        self.assertEqual(missing_reference_conditions(_baseline()), ())

    def test_an_absent_reference_condition_is_reported(self):
        measurement = _baseline()
        del measurement["test_current_a"]
        self.assertEqual(
            missing_reference_conditions(measurement), ("test_current_a",)
        )


class DriftArithmeticTests(unittest.TestCase):
    def test_relative_drift_is_the_move_over_the_baseline(self):
        self.assertAlmostEqual(relative_drift(0.500, 0.525), 0.05, places=9)

    def test_relative_drift_is_unsigned(self):
        self.assertAlmostEqual(
            relative_drift(0.500, 0.475), relative_drift(0.500, 0.525), places=9
        )

    def test_a_zero_baseline_rejected(self):
        with self.assertRaises(ValueError):
            relative_drift(0.0, 0.5)

    def test_a_fallen_breakdown_voltage_gives_a_positive_drop(self):
        self.assertAlmostEqual(drop_fraction(60.0, 57.0), 0.05, places=9)

    def test_a_risen_breakdown_voltage_gives_a_negative_drop(self):
        self.assertLess(drop_fraction(60.0, 63.0), 0.0)

    def test_a_grown_series_resistance_gives_a_positive_growth(self):
        self.assertAlmostEqual(growth_fraction(0.010, 0.012), 0.2, places=9)

    def test_a_fallen_series_resistance_gives_a_negative_growth(self):
        self.assertLess(growth_fraction(0.010, 0.008), 0.0)

    def test_the_leakage_ratio_is_a_multiple_not_a_percentage(self):
        self.assertAlmostEqual(growth_ratio(1.0e-9, 4.0e-9), 4.0, places=9)

    def test_a_zero_baseline_leakage_rejected(self):
        with self.assertRaises(ValueError):
            growth_ratio(0.0, 1.0e-9)


class ReferenceConditionTests(unittest.TestCase):
    def test_the_temperature_gap_is_unsigned(self):
        deltas = reference_condition_deltas(
            _baseline(), _followup(junction_temperature_c=20.0)
        )
        self.assertAlmostEqual(deltas["junction_temperature_delta_k"], 5.0, places=9)

    def test_the_current_gap_is_a_share_of_the_baseline_current(self):
        deltas = reference_condition_deltas(_baseline(), _followup(test_current_a=2.1))
        self.assertAlmostEqual(deltas["test_current_delta_fraction"], 0.05, places=9)

    def test_matching_conditions_give_no_gap(self):
        deltas = reference_condition_deltas(
            _baseline(), _followup(junction_temperature_c=25.0)
        )
        self.assertAlmostEqual(deltas["junction_temperature_delta_k"], 0.0, places=12)
        self.assertAlmostEqual(deltas["test_current_delta_fraction"], 0.0, places=12)

    def test_absent_reference_conditions_rejected(self):
        followup = _followup()
        del followup["junction_temperature_c"]
        with self.assertRaises(ValueError):
            reference_condition_deltas(_baseline(), followup)

    def test_a_zero_test_current_rejected(self):
        with self.assertRaises(ValueError):
            reference_condition_deltas(_baseline(), _followup(test_current_a=0.0))


class ParameterDriftTests(unittest.TestCase):
    def test_every_required_drift_is_derived(self):
        drifts = parameter_drifts(_baseline(), _followup())
        self.assertEqual(
            sorted(drifts),
            [
                "breakdown_voltage_drop_fraction",
                "forward_voltage_drift_fraction",
                "reverse_leakage_growth_ratio",
                "series_resistance_growth_fraction",
            ],
        )

    def test_an_unchanged_device_drifts_by_nothing(self):
        drifts = parameter_drifts(_baseline(), _baseline())
        self.assertAlmostEqual(drifts["forward_voltage_drift_fraction"], 0.0, places=12)
        self.assertAlmostEqual(drifts["reverse_leakage_growth_ratio"], 1.0, places=12)
        self.assertAlmostEqual(drifts["breakdown_voltage_drop_fraction"], 0.0, places=12)
        self.assertAlmostEqual(
            drifts["series_resistance_growth_fraction"], 0.0, places=12
        )

    def test_a_follow_up_missing_a_parameter_rejected(self):
        followup = _followup()
        del followup["series_resistance_ohm"]
        with self.assertRaises(ValueError):
            parameter_drifts(_baseline(), followup)


class CharacterizationAssessmentTests(unittest.TestCase):
    def test_a_nominal_bracket_is_accepted(self):
        result = assess_diode_characterization(_case())
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_derived_drifts_are_reported(self):
        result = assess_diode_characterization(_case())
        self.assertAlmostEqual(
            result["reverse_leakage_growth_ratio"], 3.0, places=9
        )
        self.assertAlmostEqual(
            result["junction_temperature_delta_k"], 0.5, places=9
        )

    def test_a_baseline_missing_a_parameter_leaves_the_set_incomplete(self):
        baseline = _baseline()
        del baseline["breakdown_voltage_v"]
        result = assess_diode_characterization(_case(baseline=baseline))
        self.assertEqual(result["verdict"], MEASUREMENT_SET_INCOMPLETE)
        self.assertEqual(result["baseline_missing"], ("breakdown_voltage_v",))

    def test_a_follow_up_missing_a_parameter_leaves_the_set_incomplete(self):
        followup = _followup()
        del followup["reverse_leakage_a"]
        result = assess_diode_characterization(_case(followup=followup))
        self.assertEqual(result["verdict"], MEASUREMENT_SET_INCOMPLETE)
        self.assertEqual(result["followup_missing"], ("reverse_leakage_a",))

    def test_an_absent_parameter_does_not_read_as_a_pass(self):
        followup = _followup()
        del followup["reverse_leakage_a"]
        result = assess_diode_characterization(_case(followup=followup))
        self.assertNotEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)
        self.assertNotIn("reverse_leakage_growth_ratio", result)

    def test_too_few_bracketed_devices_leaves_the_set_incomplete(self):
        result = assess_diode_characterization(_case(characterized_devices=2))
        self.assertEqual(result["verdict"], MEASUREMENT_SET_INCOMPLETE)

    def test_a_device_count_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_diode_characterization(
            _case(characterized_devices=int(policy["min_characterized_devices"])),
            policy,
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)

    def test_an_incomplete_set_outranks_a_condition_mismatch(self):
        followup = _followup(junction_temperature_c=85.0)
        del followup["breakdown_voltage_v"]
        result = assess_diode_characterization(_case(followup=followup))
        self.assertEqual(result["verdict"], MEASUREMENT_SET_INCOMPLETE)

    def test_a_warm_follow_up_is_a_condition_mismatch(self):
        result = assess_diode_characterization(
            _case(followup=_followup(junction_temperature_c=85.0))
        )
        self.assertEqual(result["verdict"], REFERENCE_CONDITION_MISMATCH)

    def test_a_temperature_gap_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        gap = policy["max_junction_temperature_delta_k"]
        result = assess_diode_characterization(
            _case(followup=_followup(junction_temperature_c=25.0 + gap)), policy
        )
        self.assertAlmostEqual(
            result["junction_temperature_delta_k"], gap, places=9
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)

    def test_a_different_test_current_is_a_condition_mismatch(self):
        result = assess_diode_characterization(
            _case(followup=_followup(test_current_a=3.0))
        )
        self.assertEqual(result["verdict"], REFERENCE_CONDITION_MISMATCH)

    def test_a_condition_mismatch_outranks_the_drift_it_would_produce(self):
        result = assess_diode_characterization(
            _case(
                followup=_followup(
                    junction_temperature_c=85.0, forward_voltage_v=0.400
                )
            )
        )
        self.assertEqual(result["verdict"], REFERENCE_CONDITION_MISMATCH)
        self.assertIn("forward_voltage_drift_fraction", result)

    def test_a_walked_forward_voltage_is_degradation(self):
        result = assess_diode_characterization(
            _case(followup=_followup(forward_voltage_v=0.620))
        )
        self.assertEqual(result["verdict"], DEGRADATION_DETECTED)

    def test_a_forward_drift_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        limit = policy["max_forward_voltage_drift_fraction"]
        result = assess_diode_characterization(
            _case(followup=_followup(forward_voltage_v=0.520 * (1.0 + limit))),
            policy,
        )
        self.assertAlmostEqual(
            result["forward_voltage_drift_fraction"], limit, places=9
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)

    def test_runaway_reverse_leakage_is_degradation(self):
        result = assess_diode_characterization(
            _case(followup=_followup(reverse_leakage_a=1.0e-6))
        )
        self.assertEqual(result["verdict"], DEGRADATION_DETECTED)

    def test_a_leakage_ratio_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        result = assess_diode_characterization(
            _case(
                followup=_followup(
                    reverse_leakage_a=1.0e-9
                    * policy["max_reverse_leakage_growth_ratio"]
                )
            ),
            policy,
        )
        self.assertAlmostEqual(
            result["reverse_leakage_growth_ratio"],
            policy["max_reverse_leakage_growth_ratio"],
            places=9,
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)

    def test_a_collapsed_breakdown_voltage_is_degradation(self):
        result = assess_diode_characterization(
            _case(followup=_followup(breakdown_voltage_v=40.0))
        )
        self.assertEqual(result["verdict"], DEGRADATION_DETECTED)

    def test_a_risen_breakdown_voltage_is_not_degradation(self):
        result = assess_diode_characterization(
            _case(followup=_followup(breakdown_voltage_v=66.0))
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)
        self.assertLess(result["breakdown_voltage_drop_fraction"], 0.0)

    def test_a_grown_series_resistance_is_degradation(self):
        result = assess_diode_characterization(
            _case(followup=_followup(series_resistance_ohm=0.030))
        )
        self.assertEqual(result["verdict"], DEGRADATION_DETECTED)

    def test_a_fallen_series_resistance_is_not_degradation(self):
        result = assess_diode_characterization(
            _case(followup=_followup(series_resistance_ohm=0.0080))
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_ACCEPTED)
        self.assertLess(result["series_resistance_growth_fraction"], 0.0)

    def test_every_degradation_finding_is_reported_not_only_the_first(self):
        result = assess_diode_characterization(
            _case(
                followup=_followup(
                    forward_voltage_v=0.620,
                    reverse_leakage_a=1.0e-6,
                    breakdown_voltage_v=40.0,
                    series_resistance_ohm=0.030,
                )
            )
        )
        self.assertEqual(result["verdict"], DEGRADATION_DETECTED)
        self.assertEqual(len(result["findings"]), 4)

    def test_a_missing_baseline_block_rejected(self):
        case = _case()
        del case["baseline"]
        with self.assertRaises(ValueError):
            assess_diode_characterization(case)

    def test_a_missing_followup_block_rejected(self):
        case = _case()
        del case["followup"]
        with self.assertRaises(ValueError):
            assess_diode_characterization(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_characterization(["baseline"])

    def test_a_zero_device_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_characterization(_case(characterized_devices=0))

    def test_a_boolean_device_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_characterization(_case(characterized_devices=True))


if __name__ == "__main__":
    unittest.main()
