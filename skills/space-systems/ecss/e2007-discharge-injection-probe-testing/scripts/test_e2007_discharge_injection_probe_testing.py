#!/usr/bin/env python3
"""Contract tests for the clause 5.4.13.4 discharge-injection arrangement."""

import unittest

from e2007_discharge_injection_probe_testing_logic import (
    DEFAULT_CLAMP_MAX_DISTANCE_M,
    DEFAULT_CLAMP_MIN_DISTANCE_M,
    GROUP_ADEQUATE,
    GROUP_INADEQUATE,
    GROUP_MARGINAL,
    MIN_LADDER_STEPS,
    assess_discharge_injection,
    assess_injection_point,
    assess_monitoring,
    clamp_window,
    governing_shortfall,
    injection_duration_s,
    max_monitor_interval_s,
    min_repetition_interval_s,
    normalize_injection_points,
    total_pulse_count,
    validate_injection_point,
    validate_level_ladder,
)


def a_point(**overrides):
    point = {
        "name": "power-bundle",
        "coupling": "harness-injection-clamp",
        "bundle_length_m": 1.5,
        "clamp_length_m": 0.12,
        "distance_to_connector_m": 0.15,
    }
    point.update(overrides)
    return point


def a_plan(**overrides):
    plan = {
        "injection_points": [
            a_point(),
            a_point(name="signal-bundle", distance_to_connector_m=0.18),
        ],
        "level_ladder": [1.0, 2.0, 4.0],
        "required_level_kv": 4.0,
        "pulses_per_polarity": 10,
        "repetition_interval_s": 1.0,
        "generator_recharge_s": 0.5,
        "eut_recovery_s": 0.2,
        "shortest_upset_s": 0.01,
        "monitoring": {
            "continuous": True,
            "sample_interval_s": 0.001,
            "records_pulse_index": True,
        },
        "eut_powered": True,
        "eut_operating_mode": "worst-case",
    }
    plan.update(overrides)
    return plan


class ClampWindowTests(unittest.TestCase):
    def test_defaults_are_returned_when_no_plan_is_given(self):
        self.assertEqual(
            clamp_window(), (DEFAULT_CLAMP_MIN_DISTANCE_M, DEFAULT_CLAMP_MAX_DISTANCE_M)
        )

    def test_plan_overrides_both_edges(self):
        self.assertEqual(
            clamp_window({"clamp_min_distance_m": 0.1, "clamp_max_distance_m": 0.4}),
            (0.1, 0.4),
        )

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            clamp_window({"clamp_min_distance_m": 0.4, "clamp_max_distance_m": 0.1})

    def test_non_positive_edge_rejected(self):
        with self.assertRaises(ValueError):
            clamp_window({"clamp_min_distance_m": 0.0})


class InjectionPointValidationTests(unittest.TestCase):
    def test_valid_point_is_normalized(self):
        record = validate_injection_point(a_point())
        self.assertEqual(record["name"], "power-bundle")
        self.assertEqual(record["coupling"], "harness-injection-clamp")
        self.assertTrue(record["bundle_sufficient"])

    def test_bundle_needed_is_clamp_plus_distance(self):
        record = validate_injection_point(a_point())
        self.assertAlmostEqual(record["bundle_needed_m"], 0.27, places=9)

    def test_unrecognized_coupling_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(a_point(coupling="alligator-clip"))

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(a_point(name="   "))

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(a_point(distance_to_connector_m=0.0))

    def test_boolean_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(a_point(bundle_length_m=True))

    def test_repeated_point_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_injection_points([a_point(), a_point()])

    def test_empty_point_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_injection_points([])


class PlacementGroupingTests(unittest.TestCase):
    def test_mid_window_placement_is_adequate(self):
        record = assess_injection_point(validate_injection_point(a_point()))
        self.assertEqual(record["group"], GROUP_ADEQUATE)
        self.assertAlmostEqual(record["shortfall_factor"], 1.0, places=9)

    def test_placement_on_the_lower_edge_is_marginal(self):
        record = assess_injection_point(
            validate_injection_point(a_point(distance_to_connector_m=0.05))
        )
        self.assertEqual(record["group"], GROUP_MARGINAL)

    def test_placement_near_the_upper_edge_is_marginal(self):
        record = assess_injection_point(
            validate_injection_point(a_point(distance_to_connector_m=0.29))
        )
        self.assertEqual(record["group"], GROUP_MARGINAL)

    def test_placement_too_close_is_inadequate(self):
        record = assess_injection_point(
            validate_injection_point(a_point(distance_to_connector_m=0.01))
        )
        self.assertEqual(record["group"], GROUP_INADEQUATE)
        self.assertAlmostEqual(record["shortfall_factor"], 5.0, places=9)

    def test_placement_too_far_is_inadequate(self):
        record = assess_injection_point(
            validate_injection_point(
                a_point(bundle_length_m=2.0, distance_to_connector_m=0.60)
            )
        )
        self.assertEqual(record["group"], GROUP_INADEQUATE)
        self.assertAlmostEqual(record["shortfall_factor"], 2.0, places=9)

    def test_bundle_too_short_for_the_clamp_is_inadequate(self):
        record = assess_injection_point(
            validate_injection_point(
                a_point(bundle_length_m=0.20, clamp_length_m=0.12,
                        distance_to_connector_m=0.15)
            )
        )
        self.assertEqual(record["group"], GROUP_INADEQUATE)
        self.assertAlmostEqual(record["shortfall_factor"], 0.27 / 0.20, places=9)

    def test_marginal_band_at_or_above_half_rejected(self):
        with self.assertRaises(ValueError):
            assess_injection_point(validate_injection_point(a_point()), None, 0.5)

    def test_governing_shortfall_picks_the_largest_factor(self):
        records = [
            assess_injection_point(
                validate_injection_point(a_point(distance_to_connector_m=0.01))
            ),
            assess_injection_point(
                validate_injection_point(
                    a_point(name="b", bundle_length_m=2.0, distance_to_connector_m=0.60)
                )
            ),
        ]
        worst = governing_shortfall(records)
        self.assertEqual(worst["name"], "power-bundle")

    def test_governing_shortfall_is_none_when_every_point_is_placeable(self):
        records = [assess_injection_point(validate_injection_point(a_point()))]
        self.assertIsNone(governing_shortfall(records))


class LevelLadderTests(unittest.TestCase):
    def test_rising_ladder_reaching_the_required_level(self):
        ladder = validate_level_ladder([1.0, 2.0, 4.0], 4.0)
        self.assertTrue(ladder["reaches_required"])
        self.assertFalse(ladder["overtests"])
        self.assertTrue(ladder["stepped"])

    def test_ladder_short_of_the_required_level(self):
        ladder = validate_level_ladder([1.0, 2.0, 3.0], 4.0)
        self.assertFalse(ladder["reaches_required"])

    def test_ladder_exactly_at_the_required_level_counts_as_reaching_it(self):
        ladder = validate_level_ladder([1.0, 2.0, 4.0], 4.0)
        self.assertAlmostEqual(ladder["overtest_ratio"], 1.0, places=9)
        self.assertTrue(ladder["reaches_required"])

    def test_ladder_at_the_overtest_allowance_is_not_an_overtest(self):
        ladder = validate_level_ladder([1.0, 2.0, 4.4], 4.0, 0.10)
        self.assertFalse(ladder["overtests"])

    def test_ladder_beyond_the_overtest_allowance(self):
        ladder = validate_level_ladder([1.0, 2.0, 6.0], 4.0, 0.10)
        self.assertTrue(ladder["overtests"])

    def test_two_step_ladder_is_not_a_walk_up(self):
        ladder = validate_level_ladder([2.0, 4.0], 4.0)
        self.assertFalse(ladder["stepped"])
        self.assertLess(ladder["steps"], MIN_LADDER_STEPS)

    def test_non_rising_ladder_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([1.0, 2.0, 2.0], 4.0)

    def test_single_level_ladder_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([4.0], 4.0)

    def test_negative_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([-1.0, 2.0], 4.0)


class PulseBudgetTests(unittest.TestCase):
    def test_pulse_count_is_the_product_of_the_matrix(self):
        self.assertEqual(total_pulse_count(2, 3, 10, 2), 120)

    def test_single_polarity_halves_the_count(self):
        self.assertEqual(total_pulse_count(2, 3, 10, 1), 60)

    def test_zero_points_rejected(self):
        with self.assertRaises(ValueError):
            total_pulse_count(0, 3, 10)

    def test_boolean_pulse_count_rejected(self):
        with self.assertRaises(ValueError):
            total_pulse_count(2, 3, True)

    def test_duration_adds_the_per_point_setup(self):
        self.assertAlmostEqual(injection_duration_s(120, 1.0, 2, 30.0), 180.0, places=9)

    def test_duration_without_setup_is_pulses_times_interval(self):
        self.assertAlmostEqual(injection_duration_s(120, 0.5, 2), 60.0, places=9)

    def test_duration_rejects_a_zero_interval(self):
        with self.assertRaises(ValueError):
            injection_duration_s(120, 0.0, 2)

    def test_duration_rejects_a_negative_setup(self):
        with self.assertRaises(ValueError):
            injection_duration_s(120, 1.0, 2, -1.0)


class RepetitionIntervalTests(unittest.TestCase):
    def test_recharge_governs_when_it_is_the_slower(self):
        self.assertAlmostEqual(min_repetition_interval_s(0.5, 0.2), 0.6, places=9)

    def test_recovery_governs_when_it_is_the_slower(self):
        self.assertAlmostEqual(min_repetition_interval_s(0.2, 2.0), 2.4, places=9)

    def test_guard_below_one_rejected(self):
        with self.assertRaises(ValueError):
            min_repetition_interval_s(0.5, 0.2, 0.9)

    def test_zero_recharge_rejected(self):
        with self.assertRaises(ValueError):
            min_repetition_interval_s(0.0, 0.2)

    def test_negative_recovery_rejected(self):
        with self.assertRaises(ValueError):
            min_repetition_interval_s(0.5, -0.1)


class MonitoringTests(unittest.TestCase):
    def test_max_interval_divides_the_upset(self):
        self.assertAlmostEqual(max_monitor_interval_s(0.012, 3.0), 0.004, places=9)

    def test_fewer_than_two_samples_rejected(self):
        with self.assertRaises(ValueError):
            max_monitor_interval_s(0.012, 1.0)

    def test_fast_continuous_monitoring_has_no_finding(self):
        report = assess_monitoring(
            {"continuous": True, "sample_interval_s": 0.001, "records_pulse_index": True},
            0.01,
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["fast_enough"])

    def test_interval_exactly_at_the_bound_is_fast_enough(self):
        report = assess_monitoring(
            {"continuous": True, "sample_interval_s": 0.004, "records_pulse_index": True},
            0.012,
        )
        self.assertTrue(report["fast_enough"])
        self.assertAlmostEqual(report["max_interval_s"], 0.004, places=9)

    def test_slow_monitoring_is_a_finding(self):
        report = assess_monitoring(
            {"continuous": True, "sample_interval_s": 0.05, "records_pulse_index": True},
            0.01,
        )
        self.assertEqual(len(report["findings"]), 1)

    def test_sampled_monitoring_is_a_finding(self):
        report = assess_monitoring(
            {"continuous": False, "sample_interval_s": 0.001, "records_pulse_index": True},
            0.01,
        )
        self.assertEqual(len(report["findings"]), 1)

    def test_missing_pulse_index_is_a_limitation_not_a_finding(self):
        report = assess_monitoring(
            {"continuous": True, "sample_interval_s": 0.001, "records_pulse_index": False},
            0.01,
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["limitations"]), 1)

    def test_non_boolean_continuous_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring(
                {"continuous": "yes", "sample_interval_s": 0.001,
                 "records_pulse_index": True},
                0.01,
            )


class ArrangementAssessmentTests(unittest.TestCase):
    def test_a_sound_arrangement_is_acceptable(self):
        report = assess_discharge_injection(a_plan())
        self.assertTrue(report["arrangement_acceptable"])
        self.assertEqual(report["findings"], [])

    def test_pulse_budget_and_duration_are_reported(self):
        report = assess_discharge_injection(a_plan())
        self.assertEqual(report["total_pulses"], 120)
        self.assertAlmostEqual(report["injection_duration_s"], 120.0, places=9)

    def test_unpowered_unit_is_a_finding(self):
        report = assess_discharge_injection(a_plan(eut_powered=False))
        self.assertFalse(report["arrangement_acceptable"])
        self.assertTrue(any("unpowered" in f for f in report["findings"]))

    def test_safe_mode_is_a_limitation_only(self):
        report = assess_discharge_injection(a_plan(eut_operating_mode="safe"))
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["limitations"])

    def test_short_repetition_interval_is_a_finding(self):
        report = assess_discharge_injection(a_plan(repetition_interval_s=0.1))
        self.assertFalse(report["repetition_interval_adequate"])
        self.assertFalse(report["arrangement_acceptable"])

    def test_interval_exactly_at_the_minimum_is_adequate(self):
        report = assess_discharge_injection(a_plan(repetition_interval_s=0.6))
        self.assertTrue(report["repetition_interval_adequate"])
        self.assertAlmostEqual(report["min_repetition_interval_s"], 0.6, places=9)

    def test_ladder_short_of_the_level_is_a_finding(self):
        report = assess_discharge_injection(a_plan(level_ladder=[1.0, 2.0, 3.0]))
        self.assertFalse(report["arrangement_acceptable"])

    def test_misplaced_point_names_the_governing_shortfall(self):
        plan = a_plan(
            injection_points=[
                a_point(distance_to_connector_m=0.01),
                a_point(name="signal-bundle", distance_to_connector_m=0.18),
            ]
        )
        report = assess_discharge_injection(plan)
        self.assertIsNotNone(report["governing_shortfall"])
        self.assertEqual(report["governing_shortfall"]["name"], "power-bundle")

    def test_single_polarity_is_reflected_in_the_budget(self):
        report = assess_discharge_injection(a_plan(polarities=["positive"]))
        self.assertEqual(report["polarities"], ["positive"])
        self.assertEqual(report["total_pulses"], 60)

    def test_repeated_polarity_rejected(self):
        with self.assertRaises(ValueError):
            assess_discharge_injection(a_plan(polarities=["positive", "positive"]))

    def test_missing_plan_field_rejected(self):
        plan = a_plan()
        del plan["monitoring"]
        with self.assertRaises(ValueError):
            assess_discharge_injection(plan)

    def test_unrecognized_operating_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_discharge_injection(a_plan(eut_operating_mode="cruise"))

    def test_plan_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_discharge_injection(["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()
