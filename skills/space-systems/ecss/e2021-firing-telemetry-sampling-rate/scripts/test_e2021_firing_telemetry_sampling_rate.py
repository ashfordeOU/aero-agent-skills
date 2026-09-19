#!/usr/bin/env python3
"""Gate 3 contract test for e2021-firing-telemetry-sampling-rate.

Stdlib unittest only, offline, deterministic. Rates and coverage fractions are
products and quotients of decimal inputs, so every case landing on a limit is
asserted with assertAlmostEqual against the limit and on the decision the logic
then takes, never with a strict inequality that would turn on the last bit.
"""

import unittest

from e2021_firing_telemetry_sampling_rate_logic import (
    APPLICABLE,
    DEFAULT_SAMPLING_SPEC,
    NOT_APPLICABLE,
    RATE_EPS,
    covered_duration_s,
    evaluate_actuator,
    evaluate_plan,
    feature_driven_rate_hz,
    is_long_duration,
    required_rate_hz,
    resolve_spec,
    sample_interval_s,
    samples_over_firing,
    sampling_status,
    worst_actuator,
)


def nominal_actuator():
    return {
        "name": "deployment-motor-primary",
        "firing_duration_s": 5.0,
        "shortest_feature_s": 0.05,
        "declared_rate_hz": 200.0,
        "telemetry_buffer_samples": 4000.0,
    }


def slow_feature_actuator():
    return {
        "name": "deployment-motor-redundant",
        "firing_duration_s": 5.0,
        "shortest_feature_s": 0.5,
        "declared_rate_hz": 100.0,
        "telemetry_buffer_samples": 4000.0,
    }


def nominal_config():
    return {"actuators": [nominal_actuator(), slow_feature_actuator()]}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["recommended_min_rate_hz"], 100.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_SAMPLING_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"oversampling_factor": 20.0})
        self.assertAlmostEqual(spec["oversampling_factor"], 20.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"oversampling_factor": 20.0})
        self.assertAlmostEqual(
            DEFAULT_SAMPLING_SPEC["oversampling_factor"], 10.0, places=9
        )

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"recommended_bit_depth": 12.0})

    def test_an_oversampling_factor_below_nyquist_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"oversampling_factor": 1.5})

    def test_a_fractional_channel_count_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"monitored_channels": 0.5})

    def test_a_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("oversampling_factor", 10.0)])


class TestApplicability(unittest.TestCase):
    def test_a_long_firing_is_long_duration(self):
        self.assertTrue(is_long_duration(5.0, 1.0))

    def test_a_firing_exactly_at_the_threshold_counts(self):
        self.assertTrue(is_long_duration(1.0, 1.0))

    def test_a_short_firing_is_not_long_duration(self):
        self.assertFalse(is_long_duration(0.05, 1.0))

    def test_a_zero_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            is_long_duration(0.0, 1.0)

    def test_a_non_positive_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            is_long_duration(5.0, 0.0)


class TestRateSizing(unittest.TestCase):
    def test_the_feature_driven_rate_puts_the_factor_inside_the_feature(self):
        self.assertAlmostEqual(feature_driven_rate_hz(0.05, 10.0), 200.0, places=9)

    def test_a_bare_nyquist_factor_is_the_lowest_accepted(self):
        self.assertAlmostEqual(feature_driven_rate_hz(0.05, 2.0), 40.0, places=9)

    def test_a_factor_below_nyquist_is_rejected(self):
        with self.assertRaises(ValueError):
            feature_driven_rate_hz(0.05, 1.0)

    def test_a_non_positive_feature_is_rejected(self):
        with self.assertRaises(ValueError):
            feature_driven_rate_hz(0.0, 10.0)

    def test_a_fast_feature_lifts_the_rate_above_the_floor(self):
        self.assertAlmostEqual(required_rate_hz(0.05), 200.0, places=9)

    def test_a_slow_feature_does_not_pull_the_rate_below_the_floor(self):
        self.assertAlmostEqual(required_rate_hz(0.5), 100.0, places=9)

    def test_the_interval_is_the_reciprocal_of_the_rate(self):
        self.assertAlmostEqual(sample_interval_s(200.0), 0.005, places=9)

    def test_a_non_positive_rate_has_no_interval(self):
        with self.assertRaises(ValueError):
            sample_interval_s(0.0)


class TestSampleBudget(unittest.TestCase):
    def test_both_monitored_channels_are_counted(self):
        self.assertAlmostEqual(samples_over_firing(5.0, 200.0, 2.0), 2000.0, places=9)

    def test_counting_one_channel_halves_the_budget(self):
        self.assertAlmostEqual(samples_over_firing(5.0, 200.0, 1.0), 1000.0, places=9)

    def test_a_zero_channel_count_is_rejected(self):
        with self.assertRaises(ValueError):
            samples_over_firing(5.0, 200.0, 0.0)

    def test_the_covered_duration_follows_from_the_buffer_depth(self):
        self.assertAlmostEqual(covered_duration_s(4000.0, 200.0, 2.0), 10.0, places=9)

    def test_a_negative_buffer_depth_is_rejected(self):
        with self.assertRaises(ValueError):
            covered_duration_s(-1.0, 200.0, 2.0)

    def test_a_zero_rate_has_no_covered_duration(self):
        with self.assertRaises(ValueError):
            covered_duration_s(4000.0, 0.0, 2.0)


class TestActuatorPlan(unittest.TestCase):
    def test_a_nominal_plan_is_adequate(self):
        result = evaluate_actuator(nominal_actuator())
        self.assertTrue(result["adequate"])
        self.assertEqual(result["applicability"], APPLICABLE)
        self.assertAlmostEqual(result["required_rate_hz"], 200.0, places=9)

    def test_a_short_firing_is_marked_not_applicable(self):
        actuator = nominal_actuator()
        actuator["firing_duration_s"] = 0.5
        actuator["shortest_feature_s"] = 0.005
        result = evaluate_actuator(actuator)
        self.assertEqual(result["applicability"], NOT_APPLICABLE)
        self.assertTrue(result["adequate"])

    def test_a_declared_rate_exactly_on_the_requirement_is_adequate(self):
        result = evaluate_actuator(nominal_actuator())
        self.assertAlmostEqual(result["adopted_rate_hz"], 200.0, places=9)
        self.assertAlmostEqual(result["required_rate_hz"], 200.0, places=9)
        self.assertTrue(result["rate_adequate"])

    def test_a_declared_rate_under_the_requirement_is_not_adequate(self):
        actuator = nominal_actuator()
        actuator["declared_rate_hz"] = 100.0
        result = evaluate_actuator(actuator)
        self.assertFalse(result["rate_adequate"])
        self.assertFalse(result["adequate"])

    def test_an_absent_declared_rate_adopts_the_requirement(self):
        actuator = nominal_actuator()
        del actuator["declared_rate_hz"]
        result = evaluate_actuator(actuator)
        self.assertAlmostEqual(result["adopted_rate_hz"], 200.0, places=9)
        self.assertTrue(result["rate_adequate"])

    def test_a_buffer_holding_exactly_the_firing_covers_it(self):
        actuator = nominal_actuator()
        actuator["telemetry_buffer_samples"] = 2000.0
        result = evaluate_actuator(actuator)
        self.assertAlmostEqual(result["samples_over_firing"], 2000.0, places=9)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertTrue(result["buffer_covers_firing"])

    def test_a_short_buffer_truncates_the_record(self):
        actuator = nominal_actuator()
        actuator["telemetry_buffer_samples"] = 1000.0
        result = evaluate_actuator(actuator)
        self.assertFalse(result["buffer_covers_firing"])
        self.assertAlmostEqual(result["covered_duration_s"], 2.5, places=9)

    def test_a_feature_longer_than_the_firing_is_rejected(self):
        actuator = nominal_actuator()
        actuator["shortest_feature_s"] = 6.0
        with self.assertRaises(ValueError):
            evaluate_actuator(actuator)

    def test_a_non_positive_declared_rate_is_rejected(self):
        actuator = nominal_actuator()
        actuator["declared_rate_hz"] = 0.0
        with self.assertRaises(ValueError):
            evaluate_actuator(actuator)

    def test_an_actuator_without_a_name_is_rejected(self):
        actuator = nominal_actuator()
        actuator["name"] = "  "
        with self.assertRaises(ValueError):
            evaluate_actuator(actuator)

    def test_a_non_mapping_actuator_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_actuator(["deployment-motor-primary"])


class TestWorstActuator(unittest.TestCase):
    def test_the_worst_actuator_covers_the_least_of_its_firing(self):
        actuators = nominal_config()["actuators"]
        actuators[0]["telemetry_buffer_samples"] = 1000.0
        results = [evaluate_actuator(a) for a in actuators]
        self.assertEqual(worst_actuator(results)["name"], "deployment-motor-primary")

    def test_worst_actuator_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_actuator([])


class TestEndToEnd(unittest.TestCase):
    def test_an_adequate_plan_reports_no_findings(self):
        report = evaluate_plan(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "sampling-plan-adequate")
        self.assertTrue(report["adequate"])

    def test_a_slow_rate_holds_the_plan(self):
        config = nominal_config()
        config["actuators"][0]["declared_rate_hz"] = 100.0
        report = evaluate_plan(config)
        self.assertFalse(report["adequate"])
        self.assertEqual(report["status"], "hold-sampling-plan")
        self.assertTrue(
            any("deployment-motor-primary" in f for f in report["findings"])
        )

    def test_a_short_buffer_holds_the_plan(self):
        config = nominal_config()
        config["actuators"][1]["telemetry_buffer_samples"] = 200.0
        report = evaluate_plan(config)
        self.assertFalse(report["adequate"])
        self.assertTrue(any("housekeeping for" in f for f in report["findings"]))

    def test_a_short_firing_raises_no_finding_even_when_undersampled(self):
        config = nominal_config()
        short = config["actuators"][0]
        short["firing_duration_s"] = 0.2
        short["shortest_feature_s"] = 0.002
        short["declared_rate_hz"] = 10.0
        short["telemetry_buffer_samples"] = 4.0
        self.assertTrue(evaluate_plan(config)["adequate"])

    def test_a_larger_oversampling_factor_can_hold_a_passing_plan(self):
        config = nominal_config()
        self.assertTrue(evaluate_plan(config)["adequate"])
        config["spec"] = {"oversampling_factor": 40.0}
        self.assertFalse(evaluate_plan(config)["adequate"])

    def test_duplicate_actuator_names_are_rejected(self):
        config = nominal_config()
        config["actuators"][1]["name"] = config["actuators"][0]["name"]
        with self.assertRaises(ValueError):
            evaluate_plan(config)

    def test_an_empty_actuator_set_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_plan({"actuators": []})

    def test_a_missing_actuator_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_plan({"spec": {}})

    def test_the_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_plan([("actuators", [])])

    def test_the_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            sampling_status("hold")

    def test_the_named_tolerance_is_far_below_any_recommended_rate(self):
        self.assertLess(RATE_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
