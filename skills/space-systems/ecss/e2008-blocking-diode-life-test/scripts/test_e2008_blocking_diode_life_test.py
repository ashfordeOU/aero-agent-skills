"""Contract tests for the clause 12.6.8 blocking diode life test logic."""

import unittest

from e2008_blocking_diode_life_test_logic import (
    BLOCKING_DIODE_LIFE_PARAMETERS,
    DEFAULT_LIFE_TEST_POLICY,
    LIFE_TEST_CONDITIONS_NOT_EXTREME,
    LIFE_TEST_COVERAGE_SHORT,
    LIFE_TEST_NOT_PERFORMED,
    LIFE_TEST_PARAMETER_UNSTABLE,
    LIFE_TEST_PROJECTED_DRIFT_EXCEEDED,
    LIFE_TEST_STABILITY_DEMONSTRATED,
    arrhenius_acceleration_factor,
    assess_blocking_diode_life_test,
    conditions_are_extreme,
    drift_fraction,
    equivalent_mission_hours,
    kelvin,
    measured_drifts,
    mission_coverage_ratio,
    parameter_inventory,
    projected_end_of_life_drift,
    projected_unstable_parameters,
    stress_ratio,
    unstable_parameters,
    validate_life_test_policy,
)

MISSION_HOURS = 131400.0


def _policy(**overrides):
    policy = dict(DEFAULT_LIFE_TEST_POLICY)
    policy["drift_limits"] = dict(DEFAULT_LIFE_TEST_POLICY["drift_limits"])
    policy.update(overrides)
    return policy


def _run(**overrides):
    run = {
        "case_temperature_c": 150.0,
        "use_temperature_c": 85.0,
        "activation_energy_ev": 0.7,
        "test_hours": 2500.0,
        "applied_current_a": 2.7,
        "rated_current_a": 3.0,
    }
    run.update(overrides)
    return run


def _measurements(**overrides):
    values = {
        "blocking-diode-forward-voltage": (0.80, 0.84),
        "blocking-diode-reverse-leakage": (1.0e-6, 1.3e-6),
        "blocking-diode-thermal-resistance": (4.0, 4.2),
        "blocking-diode-junction-capacitance": (200.0e-12, 190.0e-12),
    }
    values.update(overrides)
    return [
        {"parameter": name, "initial_value": pair[0], "final_value": pair[1]}
        for name, pair in values.items()
    ]


def _case(**overrides):
    case = {"run": _run(), "measurements": _measurements()}
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_life_test_policy(DEFAULT_LIFE_TEST_POLICY),
            DEFAULT_LIFE_TEST_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy("one thousand hours")

    def test_a_zero_test_hours_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(min_test_hours=0.0))

    def test_a_coverage_floor_above_the_whole_mission_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(min_mission_coverage_ratio=1.5))

    def test_a_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(mission_hours=0.0))

    def test_an_empty_drift_limit_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(drift_limits={}))

    def test_a_drift_limit_on_an_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(drift_limits={"coverglass-haze": 0.1}))

    def test_a_case_floor_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(min_case_temperature_c=-300.0))

    def test_every_recognised_parameter_carries_a_default_limit(self):
        self.assertEqual(len(BLOCKING_DIODE_LIFE_PARAMETERS), 4)
        for limit in BLOCKING_DIODE_LIFE_PARAMETERS.values():
            self.assertGreater(limit, 0.0)


class ConditionTests(unittest.TestCase):
    def test_the_stress_ratio_is_the_applied_share_of_the_rating(self):
        self.assertAlmostEqual(stress_ratio(2.7, 3.0), 0.9, places=9)

    def test_a_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(2.7, 0.0)

    def test_a_negative_applied_loading_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(-1.0, 3.0)

    def test_a_hot_hard_run_is_extreme(self):
        self.assertTrue(conditions_are_extreme(150.0, 2.7, 3.0, 125.0, 0.9))

    def test_a_stress_ratio_exactly_on_the_floor_is_extreme_enough(self):
        self.assertTrue(conditions_are_extreme(125.0, 0.9, 1.0, 125.0, 0.9))

    def test_a_cool_run_is_not_extreme_however_hard_it_is_driven(self):
        self.assertFalse(conditions_are_extreme(60.0, 3.0, 3.0, 125.0, 0.9))

    def test_a_lightly_loaded_run_is_not_extreme_however_hot_it_is(self):
        self.assertFalse(conditions_are_extreme(180.0, 0.6, 3.0, 125.0, 0.9))

    def test_a_case_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            conditions_are_extreme(-300.0, 2.7, 3.0, 125.0, 0.9)


class CoverageTests(unittest.TestCase):
    def test_a_hotter_bench_ages_faster_than_use(self):
        self.assertGreater(arrhenius_acceleration_factor(150.0, 85.0, 0.7), 10.0)

    def test_a_bench_at_the_use_temperature_accelerates_nothing(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(85.0, 85.0, 0.7), 1.0, places=9
        )

    def test_a_larger_activation_energy_raises_the_factor(self):
        self.assertGreater(
            arrhenius_acceleration_factor(150.0, 85.0, 0.9),
            arrhenius_acceleration_factor(150.0, 85.0, 0.7),
        )

    def test_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(150.0, 85.0, 0.0)

    def test_equivalent_hours_are_the_bench_hours_times_the_factor(self):
        factor = arrhenius_acceleration_factor(150.0, 85.0, 0.7)
        self.assertAlmostEqual(
            _ratio(equivalent_mission_hours(2500.0, factor), 2500.0 * factor),
            1.0,
            places=12,
        )

    def test_a_zero_length_run_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_mission_hours(0.0, 32.6)

    def test_coverage_is_the_equivalent_hours_over_the_mission(self):
        self.assertAlmostEqual(
            mission_coverage_ratio(65700.0, MISSION_HOURS), 0.5, places=12
        )

    def test_a_zero_mission_rejected(self):
        with self.assertRaises(ValueError):
            mission_coverage_ratio(65700.0, 0.0)


class DriftTests(unittest.TestCase):
    def test_a_parameter_that_rose_has_a_positive_drift(self):
        self.assertAlmostEqual(drift_fraction(0.80, 0.84), 0.05, places=9)

    def test_a_parameter_that_fell_has_a_negative_drift(self):
        self.assertAlmostEqual(drift_fraction(0.80, 0.76), -0.05, places=9)

    def test_a_parameter_that_did_not_move_has_zero_drift(self):
        self.assertAlmostEqual(drift_fraction(0.80, 0.80), 0.0, places=12)

    def test_a_zero_starting_value_rejected(self):
        with self.assertRaises(ValueError):
            drift_fraction(0.0, 0.84)

    def test_a_negative_final_value_rejected(self):
        with self.assertRaises(ValueError):
            drift_fraction(0.80, -0.1)

    def test_a_part_covered_mission_projects_the_drift_further(self):
        self.assertAlmostEqual(
            projected_end_of_life_drift(0.05, 65700.0, MISSION_HOURS),
            0.10,
            places=9,
        )

    def test_a_fully_covered_mission_leaves_the_drift_where_it_is(self):
        self.assertAlmostEqual(
            projected_end_of_life_drift(0.05, MISSION_HOURS, MISSION_HOURS),
            0.05,
            places=12,
        )

    def test_the_sign_of_the_drift_survives_the_projection(self):
        self.assertLess(
            projected_end_of_life_drift(-0.05, 65700.0, MISSION_HOURS), 0.0
        )

    def test_a_zero_equivalent_hours_projection_rejected(self):
        with self.assertRaises(ValueError):
            projected_end_of_life_drift(0.05, 0.0, MISSION_HOURS)


class InventoryTests(unittest.TestCase):
    def test_every_watched_parameter_is_grouped(self):
        self.assertEqual(len(parameter_inventory(_measurements())), 4)

    def test_an_unknown_parameter_rejected(self):
        measurements = _measurements()
        measurements[0]["parameter"] = "coverglass-haze"
        with self.assertRaises(ValueError):
            parameter_inventory(measurements)

    def test_a_parameter_measured_twice_rejected(self):
        measurements = _measurements()
        measurements[1]["parameter"] = measurements[0]["parameter"]
        with self.assertRaises(ValueError):
            parameter_inventory(measurements)

    def test_an_empty_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            parameter_inventory([])

    def test_a_non_sequence_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            parameter_inventory("blocking-diode-forward-voltage")

    def test_a_measurement_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            parameter_inventory([0.84])

    def test_the_drift_of_every_parameter_is_reported(self):
        drifts = measured_drifts(_measurements())
        self.assertEqual(len(drifts), 4)
        self.assertAlmostEqual(
            drifts["blocking-diode-forward-voltage"], 0.05, places=9
        )

    def test_a_parameter_inside_its_limit_is_not_named_unstable(self):
        self.assertEqual(
            unstable_parameters(
                _measurements(), DEFAULT_LIFE_TEST_POLICY["drift_limits"]
            ),
            (),
        )

    def test_a_parameter_past_its_limit_is_named_unstable(self):
        measurements = _measurements(
            **{"blocking-diode-forward-voltage": (0.80, 0.92)}
        )
        self.assertEqual(
            unstable_parameters(
                measurements, DEFAULT_LIFE_TEST_POLICY["drift_limits"]
            ),
            ("blocking-diode-forward-voltage",),
        )

    def test_a_parameter_that_fell_past_its_limit_is_also_unstable(self):
        measurements = _measurements(
            **{"blocking-diode-forward-voltage": (0.80, 0.68)}
        )
        self.assertEqual(
            unstable_parameters(
                measurements, DEFAULT_LIFE_TEST_POLICY["drift_limits"]
            ),
            ("blocking-diode-forward-voltage",),
        )

    def test_a_missing_drift_limit_rejected(self):
        with self.assertRaises(ValueError):
            unstable_parameters(_measurements(), {"blocking-diode-forward-voltage": 0.1})

    def test_a_non_mapping_limit_set_rejected(self):
        with self.assertRaises(ValueError):
            unstable_parameters(_measurements(), [0.1])

    def test_a_short_run_projects_a_parameter_past_its_limit(self):
        measurements = _measurements(
            **{"blocking-diode-forward-voltage": (0.80, 0.856)}
        )
        projected = projected_unstable_parameters(
            measurements,
            DEFAULT_LIFE_TEST_POLICY["drift_limits"],
            81475.0,
            MISSION_HOURS,
        )
        self.assertEqual(projected, ("blocking-diode-forward-voltage",))

    def test_a_fully_covered_mission_projects_nothing_new(self):
        self.assertEqual(
            projected_unstable_parameters(
                _measurements(),
                DEFAULT_LIFE_TEST_POLICY["drift_limits"],
                MISSION_HOURS,
                MISSION_HOURS,
            ),
            (),
        )


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_life_test_demonstrates_stability(self):
        result = assess_blocking_diode_life_test(_case())
        self.assertEqual(result["verdict"], LIFE_TEST_STABILITY_DEMONSTRATED)
        self.assertEqual(result["findings"], [])

    def test_the_conditions_are_reported_as_extreme(self):
        result = assess_blocking_diode_life_test(_case())
        self.assertTrue(result["conditions_extreme"])
        self.assertAlmostEqual(result["current_stress_ratio"], 0.9, places=9)

    def test_the_equivalent_hours_are_derived_from_the_acceleration(self):
        result = assess_blocking_diode_life_test(_case())
        factor = arrhenius_acceleration_factor(150.0, 85.0, 0.7)
        self.assertAlmostEqual(
            _ratio(result["equivalent_mission_hours"], 2500.0 * factor),
            1.0,
            places=12,
        )

    def test_the_run_covers_more_than_the_coverage_floor(self):
        result = assess_blocking_diode_life_test(_case())
        self.assertTrue(result["mission_covered"])
        self.assertGreater(result["mission_coverage_ratio"], 0.5)

    def test_an_unplanned_life_test_is_its_own_verdict(self):
        case = _case()
        del case["run"]
        result = assess_blocking_diode_life_test(case)
        self.assertEqual(result["verdict"], LIFE_TEST_NOT_PERFORMED)
        self.assertIsNone(result["equivalent_mission_hours"])

    def test_a_benign_run_is_not_the_extreme_condition_test(self):
        result = assess_blocking_diode_life_test(
            _case(run=_run(case_temperature_c=60.0))
        )
        self.assertEqual(result["verdict"], LIFE_TEST_CONDITIONS_NOT_EXTREME)
        self.assertFalse(result["conditions_extreme"])

    def test_a_short_run_falls_under_the_hours_floor(self):
        result = assess_blocking_diode_life_test(
            _case(run=_run(test_hours=200.0))
        )
        self.assertEqual(result["verdict"], LIFE_TEST_COVERAGE_SHORT)
        self.assertFalse(result["test_hours_met"])

    def test_a_weakly_accelerated_run_fails_the_coverage_floor(self):
        result = assess_blocking_diode_life_test(
            _case(run=_run(use_temperature_c=145.0, test_hours=1200.0))
        )
        self.assertEqual(result["verdict"], LIFE_TEST_COVERAGE_SHORT)
        self.assertFalse(result["mission_covered"])

    def test_a_parameter_that_already_moved_too_far_is_unstable(self):
        result = assess_blocking_diode_life_test(
            _case(
                measurements=_measurements(
                    **{"blocking-diode-thermal-resistance": (4.0, 5.0)}
                )
            )
        )
        self.assertEqual(result["verdict"], LIFE_TEST_PARAMETER_UNSTABLE)
        self.assertIn(
            "blocking-diode-thermal-resistance", result["unstable_parameters"]
        )

    def test_a_parameter_reaching_its_limit_only_at_end_of_mission_is_caught(self):
        result = assess_blocking_diode_life_test(
            _case(
                measurements=_measurements(
                    **{"blocking-diode-forward-voltage": (0.80, 0.856)}
                )
            )
        )
        self.assertEqual(result["verdict"], LIFE_TEST_PROJECTED_DRIFT_EXCEEDED)
        self.assertEqual(result["unstable_parameters"], ())
        self.assertIn(
            "blocking-diode-forward-voltage",
            result["projected_unstable_parameters"],
        )

    def test_a_falling_parameter_is_judged_on_its_magnitude(self):
        result = assess_blocking_diode_life_test(
            _case(
                measurements=_measurements(
                    **{"blocking-diode-junction-capacitance": (200.0e-12, 140.0e-12)}
                )
            )
        )
        self.assertEqual(result["verdict"], LIFE_TEST_PARAMETER_UNSTABLE)

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_blocking_diode_life_test(
            _case(
                run=_run(case_temperature_c=60.0, test_hours=200.0),
                measurements=_measurements(
                    **{"blocking-diode-thermal-resistance": (4.0, 5.0)}
                ),
            )
        )
        self.assertEqual(result["verdict"], LIFE_TEST_CONDITIONS_NOT_EXTREME)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_absent_measurements_rejected(self):
        case = _case()
        del case["measurements"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_life_test(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_life_test(["run"])

    def test_a_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_life_test(_case(run=[2500.0]))

    def test_a_missing_current_rating_rejected(self):
        run = _run()
        del run["rated_current_a"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_life_test(_case(run=run))


if __name__ == "__main__":
    unittest.main()
