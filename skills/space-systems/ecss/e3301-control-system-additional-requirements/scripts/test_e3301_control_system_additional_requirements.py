"""Contract tests for the clause 4.7.8.5 additional control-requirement logic."""

import math
import unittest

from e3301_control_system_additional_requirements_logic import (
    COMPARISON_TOLERANCE,
    DOMINANCE_FRACTION,
    accuracy_budget,
    actuator_margin,
    apply_command_limits,
    assess_accuracy,
    assess_additional_requirements,
    combine_random,
    combine_systematic,
    dominant_contributor,
    limit_command,
    noise_sigma_in_band,
    quantization_sigma,
    validate_non_negative,
    validate_positive,
    validate_terms,
)


def nominal_spec(**overrides):
    spec = {
        "allocated_accuracy": 0.05,
        "systematic_terms": {"alignment-offset": 0.008, "thermal-drift": 0.005},
        "random_terms": {"disturbance-response": 0.002},
        "sensor_quantization_step": 0.004,
        "sensor_noise_density": 0.0005,
        "noise_bandwidth_hz": 4.0,
        "coverage_factor": 3.0,
        "command_profile": {
            "commands": [0.0, 0.5, 1.0, 1.5],
            "initial_command": 0.0,
            "magnitude_limit": 2.0,
            "rate_limit": 10.0,
            "sample_time_s": 0.1,
        },
        "required_effort": 0.6,
        "available_effort": 1.2,
        "required_actuator_margin": 0.5,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(2, "x"), 2.0)

    def test_zero_rejected_as_positive(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "allocated_accuracy")

    def test_zero_accepted_as_non_negative(self):
        self.assertEqual(validate_non_negative(0, "term"), 0.0)

    def test_negative_rejected_as_non_negative(self):
        with self.assertRaises(ValueError):
            validate_non_negative(-1.0, "term")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(True, "term")

    def test_terms_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_terms([0.1, 0.2], "systematic_terms")

    def test_empty_term_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_terms({"": 0.1}, "systematic_terms")

    def test_absent_terms_become_an_empty_mapping(self):
        self.assertEqual(validate_terms(None, "random_terms"), {})


class ContributorTests(unittest.TestCase):
    def test_quantization_sigma_is_the_step_over_root_twelve(self):
        self.assertAlmostEqual(quantization_sigma(0.012), 0.012 / math.sqrt(12.0), places=12)

    def test_noise_scales_with_the_square_root_of_bandwidth(self):
        narrow = noise_sigma_in_band(0.001, 4.0)
        wide = noise_sigma_in_band(0.001, 16.0)
        self.assertAlmostEqual(wide / narrow, 2.0, places=9)

    def test_zero_noise_density_is_allowed(self):
        self.assertAlmostEqual(noise_sigma_in_band(0.0, 10.0), 0.0)

    def test_zero_noise_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            noise_sigma_in_band(0.001, 0.0)

    def test_systematic_terms_add_directly(self):
        self.assertAlmostEqual(
            combine_systematic({"a": 0.01, "b": 0.02, "c": 0.03}), 0.06, places=12
        )

    def test_random_terms_combine_in_quadrature(self):
        self.assertAlmostEqual(combine_random({"a": 3.0, "b": 4.0}), 5.0, places=12)

    def test_budget_expands_the_random_part_only(self):
        budget = accuracy_budget({"bias": 0.01}, {"noise": 0.002}, coverage_factor=3.0)
        self.assertAlmostEqual(budget["systematic_total"], 0.01, places=12)
        self.assertAlmostEqual(budget["random_sigma"], 0.002, places=12)
        self.assertAlmostEqual(budget["expanded_total"], 0.016, places=12)

    def test_zero_coverage_factor_rejected(self):
        with self.assertRaises(ValueError):
            accuracy_budget({"bias": 0.01}, {"noise": 0.002}, coverage_factor=0.0)

    def test_driver_is_the_largest_expanded_share(self):
        driver = dominant_contributor({"bias": 0.01}, {"noise": 0.02}, coverage_factor=3.0)
        self.assertEqual(driver["name"], "noise")
        self.assertAlmostEqual(driver["contribution"], 0.06, places=12)

    def test_contributor_named_on_both_sides_rejected(self):
        with self.assertRaises(ValueError):
            dominant_contributor({"drift": 0.01}, {"drift": 0.01})

    def test_no_contributors_rejected(self):
        with self.assertRaises(ValueError):
            dominant_contributor({}, {})


class AccuracyTests(unittest.TestCase):
    def test_nominal_budget_fits_the_allocation(self):
        accuracy = assess_accuracy(nominal_spec())
        self.assertTrue(accuracy["accuracy_met"])
        self.assertLess(accuracy["utilisation"], 1.0)

    def test_sensor_terms_enter_the_random_part(self):
        accuracy = assess_accuracy(nominal_spec())
        self.assertIn("sensor-quantization", accuracy["random_terms"])
        self.assertIn("sensor-noise", accuracy["random_terms"])
        self.assertAlmostEqual(
            accuracy["random_terms"]["sensor-noise"], 0.001, places=12
        )

    def test_noise_density_without_a_bandwidth_rejected(self):
        spec = nominal_spec()
        del spec["noise_bandwidth_hz"]
        with self.assertRaises(ValueError):
            assess_accuracy(spec)

    def test_budget_exactly_on_the_allocation_is_met(self):
        spec = {
            "allocated_accuracy": 0.016,
            "systematic_terms": {"bias": 0.01},
            "random_terms": {"noise": 0.002},
            "coverage_factor": 3.0,
        }
        accuracy = assess_accuracy(spec)
        self.assertTrue(accuracy["accuracy_met"])
        self.assertAlmostEqual(
            accuracy["expanded_total"], accuracy["allocated_accuracy"], places=9
        )

    def test_budget_over_the_allocation_is_not_met(self):
        accuracy = assess_accuracy(nominal_spec(allocated_accuracy=0.01))
        self.assertFalse(accuracy["accuracy_met"])
        self.assertGreater(accuracy["utilisation"], 1.0)

    def test_missing_allocation_rejected(self):
        spec = nominal_spec()
        del spec["allocated_accuracy"]
        with self.assertRaises(ValueError):
            assess_accuracy(spec)

    def test_no_contributors_at_all_rejected(self):
        with self.assertRaises(ValueError):
            assess_accuracy({"allocated_accuracy": 0.05})


class CommandLimitingTests(unittest.TestCase):
    def test_magnitude_clamp_applies_before_the_rate_clamp(self):
        record = limit_command(9.0, 0.0, 2.0, 100.0, 0.1)
        self.assertTrue(record["magnitude_saturated"])
        self.assertAlmostEqual(record["applied"], 2.0, places=12)

    def test_rate_clamp_holds_the_step_to_the_interval_product(self):
        record = limit_command(5.0, 0.0, 10.0, 10.0, 0.1)
        self.assertTrue(record["rate_saturated"])
        self.assertAlmostEqual(record["applied"], 1.0, places=12)

    def test_command_exactly_on_the_magnitude_limit_is_not_saturated(self):
        record = limit_command(2.0, 2.0, 2.0, 10.0, 0.1)
        self.assertFalse(record["magnitude_saturated"])
        self.assertAlmostEqual(record["applied"], 2.0, places=12)

    def test_negative_command_is_clamped_symmetrically(self):
        record = limit_command(-9.0, 0.0, 2.0, 100.0, 0.1)
        self.assertAlmostEqual(record["applied"], -2.0, places=12)

    def test_non_finite_command_rejected(self):
        with self.assertRaises(ValueError):
            limit_command(float("inf"), 0.0, 2.0, 10.0, 0.1)

    def test_zero_sample_time_rejected(self):
        with self.assertRaises(ValueError):
            limit_command(1.0, 0.0, 2.0, 10.0, 0.0)

    def test_profile_carries_state_between_samples(self):
        records = apply_command_limits([5.0, 5.0, 5.0], 0.0, 10.0, 10.0, 0.1)
        applied = [record["applied"] for record in records]
        for index, expected in enumerate((1.0, 2.0, 3.0)):
            self.assertAlmostEqual(applied[index], expected, places=12)

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            apply_command_limits([], 0.0, 10.0, 10.0, 0.1)


class CapabilityTests(unittest.TestCase):
    def test_margin_is_the_spare_effort_over_the_demand(self):
        self.assertAlmostEqual(actuator_margin(0.6, 1.2), 1.0, places=12)

    def test_zero_available_effort_rejected(self):
        with self.assertRaises(ValueError):
            actuator_margin(0.6, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_nominal_specification_is_compliant(self):
        result = assess_additional_requirements(nominal_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_absent_limiter_is_a_finding(self):
        spec = nominal_spec()
        del spec["command_profile"]
        result = assess_additional_requirements(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("limiter" in f for f in result["findings"]))

    def test_saturated_samples_are_named(self):
        spec = nominal_spec()
        spec["command_profile"] = dict(spec["command_profile"], commands=[0.0, 9.0])
        result = assess_additional_requirements(spec)
        self.assertEqual(result["limiting"]["magnitude_saturated_samples"], [1])
        self.assertTrue(any("magnitude limit" in f for f in result["findings"]))

    def test_dominant_sensor_noise_is_a_finding(self):
        spec = {
            "allocated_accuracy": 0.5,
            "systematic_terms": {"alignment-offset": 0.001},
            "random_terms": {"disturbance-response": 0.02},
            "command_profile": nominal_spec()["command_profile"],
        }
        result = assess_additional_requirements(spec)
        driver = result["accuracy"]["driver"]
        self.assertEqual(driver["name"], "disturbance-response")
        self.assertGreater(driver["fraction"], DOMINANCE_FRACTION)
        self.assertTrue(any("holds" in f for f in result["findings"]))

    def test_actuator_margin_shortfall_is_a_finding(self):
        result = assess_additional_requirements(
            nominal_spec(available_effort=0.7, required_actuator_margin=0.5)
        )
        self.assertFalse(result["capability"]["margin_met"])
        self.assertTrue(any("actuator margin" in f for f in result["findings"]))

    def test_actuator_margin_exactly_on_the_requirement_is_met(self):
        result = assess_additional_requirements(
            nominal_spec(
                required_effort=1.0, available_effort=1.5, required_actuator_margin=0.5
            )
        )
        self.assertTrue(result["capability"]["margin_met"])
        self.assertAlmostEqual(
            result["capability"]["achieved_margin"],
            result["capability"]["required_margin"],
            places=9,
        )

    def test_required_effort_without_available_effort_rejected(self):
        spec = nominal_spec()
        del spec["available_effort"]
        with self.assertRaises(ValueError):
            assess_additional_requirements(spec)

    def test_malformed_command_profile_rejected(self):
        spec = nominal_spec()
        spec["command_profile"] = {"commands": [1.0]}
        with self.assertRaises(ValueError):
            assess_additional_requirements(spec)

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            assess_additional_requirements(["allocated_accuracy"])

    def test_tolerance_is_small_enough_to_be_a_representation_allowance(self):
        self.assertLess(COMPARISON_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
