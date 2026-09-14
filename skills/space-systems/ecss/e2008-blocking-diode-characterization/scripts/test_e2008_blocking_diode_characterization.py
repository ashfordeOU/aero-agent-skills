"""Contract tests for the clause 12.6.3 blocking diode characterization logic."""

import copy
import unittest

from e2008_blocking_diode_characterization_logic import (
    CHARACTERIZATION_CONDITIONS_INCOMPARABLE,
    CHARACTERIZATION_CUMULATIVE_BUDGET_EXCEEDED,
    CHARACTERIZATION_POPULATION_BROKEN,
    CHARACTERIZATION_SEQUENCE_INCOMPLETE,
    CHARACTERIZATION_STEP_LIMIT_EXCEEDED,
    CHARACTERIZATION_TRAJECTORY_NON_MONOTONIC,
    CHARACTERIZATION_WITHIN_BUDGET,
    DEFAULT_CHARACTERIZATION_POLICY,
    PARAMETERS,
    PARAMETER_SENSE,
    REFERENCE_CONDITIONS,
    SENSE_FALLS,
    SENSE_RISES,
    assess_blocking_diode_characterization,
    condition_deltas,
    conditions_comparable,
    cumulative_degradation,
    degradation_fraction,
    limits_for,
    step_degradations,
    validate_characterization_policy,
    visit_parameter_series,
    worst_step,
)

_CONDITIONS = {
    "junction_temperature_c": 25.0,
    "test_current_a": 3.0,
    "reverse_bias_v": 50.0,
}


def _policy(**overrides):
    policy = copy.deepcopy(DEFAULT_CHARACTERIZATION_POLICY)
    policy.update(overrides)
    return policy


def _conditions(**overrides):
    conditions = dict(_CONDITIONS)
    conditions.update(overrides)
    return conditions


def _visits():
    return [
        {
            "label": "baseline",
            "after_test": None,
            "device_count": 6,
            "conditions": _conditions(),
            "parameters": {
                "forward_voltage_v": 0.900,
                "reverse_leakage_a": 1.0e-8,
                "series_resistance_ohm": 0.0200,
                "blocking_voltage_v": 200.0,
            },
        },
        {
            "label": "post-thermal-vacuum",
            "after_test": "thermal-vacuum",
            "device_count": 6,
            "conditions": _conditions(),
            "parameters": {
                "forward_voltage_v": 0.905,
                "reverse_leakage_a": 1.2e-8,
                "series_resistance_ohm": 0.0205,
                "blocking_voltage_v": 199.0,
            },
        },
        {
            "label": "post-thermal-cycling",
            "after_test": "thermal-cycling",
            "device_count": 6,
            "conditions": _conditions(),
            "parameters": {
                "forward_voltage_v": 0.912,
                "reverse_leakage_a": 1.5e-8,
                "series_resistance_ohm": 0.0212,
                "blocking_voltage_v": 197.5,
            },
        },
        {
            "label": "post-life-test",
            "after_test": "life-test",
            "device_count": 6,
            "conditions": _conditions(),
            "parameters": {
                "forward_voltage_v": 0.918,
                "reverse_leakage_a": 1.9e-8,
                "series_resistance_ohm": 0.0218,
                "blocking_voltage_v": 196.0,
            },
        },
    ]


def _case(**overrides):
    case = {"visits": _visits(), "declared_device_count": 6}
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
            validate_characterization_policy("drift")

    def test_a_single_visit_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(_policy(min_visits=1))

    def test_a_zero_visit_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(_policy(min_visits=0))

    def test_a_step_limit_above_the_cumulative_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(
                    max_step_degradation_fraction=0.4,
                    max_cumulative_degradation_fraction=0.15,
                )
            )

    def test_a_step_limit_equal_to_the_budget_accepted(self):
        policy = _policy(
            max_step_degradation_fraction=0.15,
            max_cumulative_degradation_fraction=0.15,
        )
        self.assertIs(validate_characterization_policy(policy), policy)

    def test_zero_recovery_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(_policy(recovery_tolerance_fraction=0.0))

    def test_negative_temperature_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(max_junction_temperature_delta_c=-1.0)
            )

    def test_an_override_naming_an_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(parameter_overrides={"junction_depth_um": {"step": 0.1, "cumulative": 0.2}})
            )

    def test_an_override_whose_step_beats_its_own_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(parameter_overrides={"reverse_leakage_a": {"step": 3.0, "cumulative": 2.0}})
            )

    def test_a_non_mapping_override_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(parameter_overrides={"reverse_leakage_a": 0.5})
            )


class ParameterSenseTests(unittest.TestCase):
    def test_every_parameter_carries_a_sense(self):
        self.assertEqual(sorted(PARAMETER_SENSE), sorted(PARAMETERS))

    def test_the_blocking_voltage_falls_with_degradation(self):
        self.assertEqual(PARAMETER_SENSE["blocking_voltage_v"], SENSE_FALLS)

    def test_the_leakage_rises_with_degradation(self):
        self.assertEqual(PARAMETER_SENSE["reverse_leakage_a"], SENSE_RISES)

    def test_three_reference_conditions_are_required(self):
        self.assertEqual(
            sorted(REFERENCE_CONDITIONS),
            ["junction_temperature_c", "reverse_bias_v", "test_current_a"],
        )

    def test_the_general_limits_bind_a_parameter_with_no_override(self):
        step, cumulative = limits_for("forward_voltage_v")
        self.assertAlmostEqual(step, 0.05, places=9)
        self.assertAlmostEqual(cumulative, 0.15, places=9)

    def test_an_override_replaces_the_general_limits(self):
        step, cumulative = limits_for("reverse_leakage_a")
        self.assertAlmostEqual(step, 0.5, places=9)
        self.assertAlmostEqual(cumulative, 2.0, places=9)

    def test_limits_for_an_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            limits_for("junction_depth_um")


class DegradationFractionTests(unittest.TestCase):
    def test_a_rising_parameter_degrades_when_it_rises(self):
        self.assertAlmostEqual(
            degradation_fraction(0.900, 0.918, "forward_voltage_v"), 0.02, places=9
        )

    def test_a_rising_parameter_that_falls_reads_negative(self):
        self.assertAlmostEqual(
            degradation_fraction(0.900, 0.882, "forward_voltage_v"), -0.02, places=9
        )

    def test_a_falling_parameter_degrades_when_it_falls(self):
        self.assertAlmostEqual(
            degradation_fraction(200.0, 196.0, "blocking_voltage_v"), 0.02, places=9
        )

    def test_a_falling_parameter_that_rises_reads_negative(self):
        self.assertAlmostEqual(
            degradation_fraction(200.0, 204.0, "blocking_voltage_v"), -0.02, places=9
        )

    def test_an_unchanged_parameter_degrades_by_nothing(self):
        self.assertAlmostEqual(
            degradation_fraction(0.900, 0.900, "forward_voltage_v"), 0.0, places=12
        )

    def test_a_zero_baseline_rejected(self):
        with self.assertRaises(ValueError):
            degradation_fraction(0.0, 0.918, "forward_voltage_v")

    def test_a_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            degradation_fraction(0.900, True, "forward_voltage_v")

    def test_an_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            degradation_fraction(0.900, 0.918, "junction_depth_um")


class SeriesTests(unittest.TestCase):
    def test_the_series_follows_programme_order(self):
        series = visit_parameter_series(_visits(), "forward_voltage_v")
        self.assertEqual(len(series), 4)
        self.assertAlmostEqual(series[0], 0.900, places=9)
        self.assertAlmostEqual(series[-1], 0.918, places=9)

    def test_a_visit_missing_the_parameter_rejected(self):
        visits = _visits()
        del visits[2]["parameters"]["series_resistance_ohm"]
        with self.assertRaises(ValueError):
            visit_parameter_series(visits, "series_resistance_ohm")

    def test_a_non_mapping_visit_rejected(self):
        with self.assertRaises(ValueError):
            visit_parameter_series(["baseline"], "forward_voltage_v")

    def test_an_empty_visit_sequence_rejected(self):
        with self.assertRaises(ValueError):
            visit_parameter_series([], "forward_voltage_v")

    def test_there_is_one_step_fewer_than_there_are_visits(self):
        series = visit_parameter_series(_visits(), "forward_voltage_v")
        self.assertEqual(len(step_degradations(series, "forward_voltage_v")), 3)

    def test_each_step_is_read_against_the_visit_before_it(self):
        steps = step_degradations([0.900, 0.905, 0.912], "forward_voltage_v")
        self.assertAlmostEqual(steps[1], (0.912 - 0.905) / 0.905, places=9)

    def test_the_cumulative_is_read_against_the_baseline(self):
        total = cumulative_degradation([0.900, 0.905, 0.918], "forward_voltage_v")
        self.assertAlmostEqual(total, 0.02, places=9)

    def test_the_steps_do_not_add_up_to_the_cumulative(self):
        # Each step is read against a moving start, so a compounding rise
        # always leaves the cumulative above the sum of its own steps.
        series = visit_parameter_series(_visits(), "forward_voltage_v")
        steps = step_degradations(series, "forward_voltage_v")
        self.assertGreater(
            cumulative_degradation(series, "forward_voltage_v"), sum(steps)
        )

    def test_one_visit_cannot_make_a_step(self):
        with self.assertRaises(ValueError):
            step_degradations([0.900], "forward_voltage_v")

    def test_one_visit_cannot_make_a_cumulative_reading(self):
        with self.assertRaises(ValueError):
            cumulative_degradation([0.900], "forward_voltage_v")


class ConditionTests(unittest.TestCase):
    def test_identical_conditions_give_no_offsets(self):
        deltas = condition_deltas(_conditions(), _conditions())
        self.assertAlmostEqual(deltas["junction_temperature_delta_c"], 0.0, places=12)
        self.assertAlmostEqual(deltas["test_current_delta_fraction"], 0.0, places=12)
        self.assertAlmostEqual(deltas["reverse_bias_delta_fraction"], 0.0, places=12)

    def test_the_temperature_offset_is_absolute(self):
        deltas = condition_deltas(
            _conditions(), _conditions(junction_temperature_c=28.0)
        )
        self.assertAlmostEqual(deltas["junction_temperature_delta_c"], 3.0, places=9)

    def test_the_current_offset_is_relative(self):
        deltas = condition_deltas(_conditions(), _conditions(test_current_a=3.03))
        self.assertAlmostEqual(deltas["test_current_delta_fraction"], 0.01, places=9)

    def test_the_bias_offset_is_relative(self):
        deltas = condition_deltas(_conditions(), _conditions(reverse_bias_v=55.0))
        self.assertAlmostEqual(deltas["reverse_bias_delta_fraction"], 0.1, places=9)

    def test_a_visit_inside_the_tolerances_is_comparable(self):
        self.assertTrue(
            conditions_comparable(
                _conditions(), _conditions(junction_temperature_c=26.5)
            )
        )

    def test_a_drifted_temperature_is_not_comparable(self):
        self.assertFalse(
            conditions_comparable(
                _conditions(), _conditions(junction_temperature_c=40.0)
            )
        )

    def test_a_drifted_reverse_bias_is_not_comparable(self):
        self.assertFalse(
            conditions_comparable(_conditions(), _conditions(reverse_bias_v=55.0))
        )

    def test_a_missing_condition_rejected(self):
        broken = _conditions()
        del broken["reverse_bias_v"]
        with self.assertRaises(ValueError):
            condition_deltas(_conditions(), broken)

    def test_non_mapping_conditions_rejected(self):
        with self.assertRaises(ValueError):
            condition_deltas(_conditions(), "25 C")


class WorstStepTests(unittest.TestCase):
    def test_the_worst_step_is_ranked_on_its_own_limit(self):
        # The leakage moved the larger raw fraction, but the resistance used
        # more of the limit that binds it, so the resistance is the worst.
        result = assess_blocking_diode_characterization(_case())
        worst = result["worst_step"]
        self.assertEqual(worst["parameter"], "series_resistance_ohm")
        self.assertGreater(
            max(result["step_degradations"]["reverse_leakage_a"]),
            worst["degradation_fraction"],
        )

    def test_the_worst_step_names_the_test_it_followed(self):
        worst = assess_blocking_diode_characterization(_case())["worst_step"]
        self.assertEqual(worst["attributed_test"], "thermal-cycling")
        self.assertEqual(worst["step_index"], 1)

    def test_an_empty_step_map_rejected(self):
        with self.assertRaises(ValueError):
            worst_step({}, _visits())


class AssessmentTests(unittest.TestCase):
    def test_a_sound_sequence_stays_within_budget(self):
        result = assess_blocking_diode_characterization(_case())
        self.assertEqual(result["verdict"], CHARACTERIZATION_WITHIN_BUDGET)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["trajectory_monotonic"])

    def test_every_parameter_gets_a_step_list_and_a_total(self):
        result = assess_blocking_diode_characterization(_case())
        self.assertEqual(sorted(result["step_degradations"]), sorted(PARAMETERS))
        self.assertEqual(sorted(result["cumulative_degradation"]), sorted(PARAMETERS))

    def test_too_few_visits_is_an_incomplete_sequence(self):
        result = assess_blocking_diode_characterization(
            _case(visits=_visits()[:2])
        )
        self.assertEqual(result["verdict"], CHARACTERIZATION_SEQUENCE_INCOMPLETE)
        self.assertFalse(result["sequence_complete"])

    def test_a_missing_parameter_is_an_incomplete_sequence(self):
        visits = _visits()
        del visits[1]["parameters"]["blocking_voltage_v"]
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertEqual(result["verdict"], CHARACTERIZATION_SEQUENCE_INCOMPLETE)

    def test_a_changed_device_count_breaks_the_population(self):
        visits = _visits()
        visits[2]["device_count"] = 5
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertEqual(result["verdict"], CHARACTERIZATION_POPULATION_BROKEN)
        self.assertFalse(result["population_intact"])

    def test_drifted_conditions_make_the_visits_incomparable(self):
        visits = _visits()
        visits[3]["conditions"] = _conditions(junction_temperature_c=45.0)
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertEqual(result["verdict"], CHARACTERIZATION_CONDITIONS_INCOMPARABLE)
        self.assertFalse(result["conditions_comparable"])

    def test_a_recovering_parameter_is_a_non_monotonic_trajectory(self):
        visits = _visits()
        visits[3]["parameters"]["forward_voltage_v"] = 0.890
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertEqual(
            result["verdict"], CHARACTERIZATION_TRAJECTORY_NON_MONOTONIC
        )
        self.assertFalse(result["trajectory_monotonic"])

    def test_measurement_noise_below_the_tolerance_is_not_a_recovery(self):
        visits = _visits()
        visits[3]["parameters"]["forward_voltage_v"] = 0.9115
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertTrue(result["trajectory_monotonic"])
        self.assertEqual(result["verdict"], CHARACTERIZATION_WITHIN_BUDGET)

    def test_small_steps_can_still_spend_the_cumulative_budget(self):
        policy = _policy(
            max_step_degradation_fraction=0.05,
            max_cumulative_degradation_fraction=0.05,
        )
        result = assess_blocking_diode_characterization(_case(), policy)
        self.assertEqual(
            result["verdict"], CHARACTERIZATION_CUMULATIVE_BUDGET_EXCEEDED
        )
        self.assertTrue(result["step_limits_met"])
        self.assertFalse(result["cumulative_budget_met"])

    def test_one_harsh_test_can_blow_a_step_limit_alone(self):
        visits = _visits()
        visits[3]["parameters"]["forward_voltage_v"] = 0.975
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertEqual(result["verdict"], CHARACTERIZATION_STEP_LIMIT_EXCEEDED)
        self.assertFalse(result["step_limits_met"])
        self.assertTrue(result["cumulative_budget_met"])

    def test_the_cumulative_budget_outranks_a_blown_step(self):
        visits = _visits()
        visits[3]["parameters"]["forward_voltage_v"] = 1.100
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertEqual(
            result["verdict"], CHARACTERIZATION_CUMULATIVE_BUDGET_EXCEEDED
        )
        self.assertFalse(result["step_limits_met"])

    def test_every_departure_is_reported_not_only_the_first(self):
        visits = _visits()
        visits[3]["parameters"]["forward_voltage_v"] = 1.100
        visits[3]["parameters"]["series_resistance_ohm"] = 0.030
        result = assess_blocking_diode_characterization(_case(visits=visits))
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_a_condition_delta_is_reported_for_every_visit(self):
        result = assess_blocking_diode_characterization(_case())
        self.assertEqual(len(result["condition_deltas"]), 4)

    def test_a_missing_device_count_declaration_rejected(self):
        case = _case()
        del case["declared_device_count"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_characterization(case)

    def test_a_missing_visits_sequence_rejected(self):
        case = _case()
        del case["visits"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_characterization(case)

    def test_a_visit_with_no_conditions_rejected(self):
        visits = _visits()
        del visits[2]["conditions"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_characterization(_case(visits=visits))

    def test_a_visit_with_no_device_count_rejected(self):
        visits = _visits()
        del visits[1]["device_count"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_characterization(_case(visits=visits))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_characterization(["baseline"])


if __name__ == "__main__":
    unittest.main()
