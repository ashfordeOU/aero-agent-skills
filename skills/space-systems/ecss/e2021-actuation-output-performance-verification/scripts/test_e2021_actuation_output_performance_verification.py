#!/usr/bin/env python3
"""Gate 3 contract test for e2021-actuation-output-performance-verification.

Stdlib unittest only, offline, deterministic. Every reading that lands exactly
on a declared limit is asserted with assertAlmostEqual against the limit and on
the decision the logic then takes, never with a strict inequality whose truth
would depend on the last bit of a sum.
"""

import unittest

from e2021_actuation_output_performance_verification_logic import (
    DEFAULT_PERFORMANCE_SPEC,
    FIRING_CURRENT,
    LIMIT_EPS,
    OUTPUT_VOLTAGE,
    TOWARD_CEILING,
    TOWARD_FLOOR,
    apply_uncertainty,
    channel_headroom_fraction,
    evaluate_channel,
    evaluate_verification,
    grade_quantity,
    plateau_value,
    resolve_spec,
    verification_status,
    worst_channel,
)


def nominal_channel():
    return {
        "name": "pin-puller-a",
        "current_samples_a": [0.2, 3.9, 4.0, 4.1, 4.0, 0.1],
        "current_uncertainty_a": 0.2,
        "output_voltage_v": 28.0,
        "voltage_uncertainty_v": 0.5,
    }


def roomy_channel():
    return {
        "name": "pin-puller-b",
        "firing_current_a": 6.0,
        "current_uncertainty_a": 0.1,
        "output_voltage_v": 28.0,
        "voltage_uncertainty_v": 0.5,
    }


def nominal_config():
    return {"channels": [nominal_channel(), roomy_channel()]}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["min_firing_current_a"], 3.5, places=9)
        self.assertEqual(set(spec), set(DEFAULT_PERFORMANCE_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"max_output_voltage_v": 40.0})
        self.assertAlmostEqual(spec["max_output_voltage_v"], 40.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"max_output_voltage_v": 40.0})
        self.assertAlmostEqual(
            DEFAULT_PERFORMANCE_SPEC["max_output_voltage_v"], 34.0, places=9
        )

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_firing_energy_j": 1.0})

    def test_a_plateau_fraction_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"plateau_fraction": 1.5})

    def test_inverted_current_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_firing_current_a": 9.0})

    def test_inverted_voltage_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_output_voltage_v": 40.0})

    def test_a_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("plateau_fraction", 0.9)])


class TestPlateau(unittest.TestCase):
    def test_the_held_part_is_the_delivered_value(self):
        self.assertAlmostEqual(
            plateau_value([0.2, 3.9, 4.0, 4.1, 4.0, 0.1]), 4.0, places=9
        )

    def test_a_flat_pulse_returns_its_own_level(self):
        self.assertAlmostEqual(plateau_value([1.0, 1.0, 1.0]), 1.0, places=9)

    def test_an_overshoot_is_not_read_as_the_delivered_value(self):
        self.assertAlmostEqual(
            plateau_value([4.0, 4.0, 4.0, 4.0, 4.2]), 4.04, places=9
        )

    def test_a_pulse_that_never_holds_is_rejected(self):
        with self.assertRaises(ValueError):
            plateau_value([0.1, 5.0, 0.1])

    def test_an_empty_sample_set_is_rejected(self):
        with self.assertRaises(ValueError):
            plateau_value([])

    def test_a_non_positive_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            plateau_value([0.0, 0.0, 0.0])

    def test_a_fraction_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            plateau_value([1.0, 1.0, 1.0], 0.0)

    def test_a_non_numeric_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            plateau_value([1.0, "1.0", 1.0])


class TestUncertaintyDirection(unittest.TestCase):
    def test_a_floor_test_takes_the_lowest_credible_reading(self):
        self.assertAlmostEqual(
            apply_uncertainty(4.0, 0.2, TOWARD_FLOOR), 3.8, places=9
        )

    def test_a_ceiling_test_takes_the_highest_credible_reading(self):
        self.assertAlmostEqual(
            apply_uncertainty(4.0, 0.2, TOWARD_CEILING), 4.2, places=9
        )

    def test_zero_uncertainty_leaves_the_reading_alone(self):
        self.assertAlmostEqual(
            apply_uncertainty(4.0, 0.0, TOWARD_FLOOR), 4.0, places=9
        )

    def test_a_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_uncertainty(4.0, -0.1, TOWARD_FLOOR)

    def test_an_unrecognized_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_uncertainty(4.0, 0.1, "whichever-helps")


class TestQuantityGrading(unittest.TestCase):
    def test_a_reading_inside_its_band_is_within_limits(self):
        grade = grade_quantity(4.0, 0.2, 3.5, 8.0)
        self.assertTrue(grade["within_limits"])
        self.assertAlmostEqual(grade["shortfall"], 0.0, places=9)

    def test_a_worst_low_exactly_on_the_floor_is_within_limits(self):
        grade = grade_quantity(3.5, 0.0, 3.5, 8.0)
        self.assertAlmostEqual(grade["worst_low"], 3.5, places=9)
        self.assertAlmostEqual(grade["floor"], 3.5, places=9)
        self.assertTrue(grade["floor_ok"])
        self.assertAlmostEqual(grade["shortfall"], 0.0, places=9)

    def test_uncertainty_can_push_a_passing_reading_under_the_floor(self):
        grade = grade_quantity(3.6, 0.2, 3.5, 8.0)
        self.assertFalse(grade["floor_ok"])
        self.assertAlmostEqual(grade["shortfall"], 0.1, places=9)

    def test_uncertainty_can_push_a_passing_reading_over_the_ceiling(self):
        grade = grade_quantity(7.9, 0.2, 3.5, 8.0)
        self.assertFalse(grade["ceiling_ok"])
        self.assertAlmostEqual(grade["excess"], 0.1, places=9)

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_quantity(4.0, 0.0, 8.0, 3.5)


class TestChannelVerdict(unittest.TestCase):
    def test_a_nominal_channel_is_verified(self):
        result = evaluate_channel(nominal_channel())
        self.assertTrue(result["verified"])
        self.assertEqual(result["dominant_shortfall"], "none")

    def test_the_plateau_feeds_the_current_grade(self):
        result = evaluate_channel(nominal_channel())
        self.assertAlmostEqual(result["firing_current"]["reading"], 4.0, places=9)

    def test_a_voltage_only_failure_is_named_as_such(self):
        channel = roomy_channel()
        channel["output_voltage_v"] = 36.0
        result = evaluate_channel(channel)
        self.assertFalse(result["verified"])
        self.assertEqual(result["dominant_shortfall"], OUTPUT_VOLTAGE)

    def test_a_current_only_failure_is_named_as_such(self):
        channel = roomy_channel()
        channel["firing_current_a"] = 3.0
        result = evaluate_channel(channel)
        self.assertEqual(result["dominant_shortfall"], FIRING_CURRENT)

    def test_the_larger_fractional_miss_wins_when_both_fail(self):
        channel = roomy_channel()
        channel["firing_current_a"] = 3.4
        channel["current_uncertainty_a"] = 0.0
        channel["output_voltage_v"] = 18.0
        channel["voltage_uncertainty_v"] = 0.0
        self.assertEqual(
            evaluate_channel(channel)["dominant_shortfall"], OUTPUT_VOLTAGE
        )

    def test_two_sources_for_one_quantity_are_rejected(self):
        channel = roomy_channel()
        channel["current_samples_a"] = [6.0, 6.0, 6.0]
        with self.assertRaises(ValueError):
            evaluate_channel(channel)

    def test_a_channel_with_no_current_reading_is_rejected(self):
        channel = roomy_channel()
        del channel["firing_current_a"]
        with self.assertRaises(ValueError):
            evaluate_channel(channel)

    def test_a_channel_without_a_name_is_rejected(self):
        channel = roomy_channel()
        channel["name"] = "  "
        with self.assertRaises(ValueError):
            evaluate_channel(channel)

    def test_a_non_mapping_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_channel(["pin-puller-a"])


class TestWorstChannel(unittest.TestCase):
    def test_headroom_is_the_least_fractional_distance(self):
        result = evaluate_channel(nominal_channel())
        self.assertAlmostEqual(
            channel_headroom_fraction(result), 0.3 / 3.5, places=9
        )

    def test_the_worst_channel_is_the_least_headroom(self):
        results = [evaluate_channel(c) for c in nominal_config()["channels"]]
        self.assertEqual(worst_channel(results)["name"], "pin-puller-a")

    def test_worst_channel_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_channel([])

    def test_headroom_rejects_an_incomplete_record(self):
        with self.assertRaises(ValueError):
            channel_headroom_fraction({"firing_current": {}})


class TestEndToEnd(unittest.TestCase):
    def test_a_verified_set_reports_no_findings(self):
        report = evaluate_verification(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "output-performance-verified")
        self.assertTrue(report["verified"])

    def test_one_bad_channel_holds_the_verification(self):
        config = nominal_config()
        config["channels"][1]["firing_current_a"] = 3.0
        report = evaluate_verification(config)
        self.assertFalse(report["verified"])
        self.assertEqual(report["status"], "hold-output-performance")
        self.assertTrue(any("pin-puller-b" in f for f in report["findings"]))

    def test_current_and_voltage_findings_are_reported_separately(self):
        config = nominal_config()
        config["channels"][1]["firing_current_a"] = 3.0
        config["channels"][1]["output_voltage_v"] = 36.0
        report = evaluate_verification(config)
        self.assertEqual(len(report["findings"]), 2)

    def test_the_average_of_the_set_does_not_redeem_a_bad_channel(self):
        config = nominal_config()
        config["channels"][1]["firing_current_a"] = 3.0
        self.assertFalse(evaluate_verification(config)["verified"])

    def test_a_widened_limit_can_requalify_the_set(self):
        config = nominal_config()
        config["channels"][1]["firing_current_a"] = 3.0
        self.assertFalse(evaluate_verification(config)["verified"])
        config["spec"] = {"min_firing_current_a": 2.5}
        self.assertTrue(evaluate_verification(config)["verified"])

    def test_duplicate_channel_names_are_rejected(self):
        config = nominal_config()
        config["channels"][1]["name"] = config["channels"][0]["name"]
        with self.assertRaises(ValueError):
            evaluate_verification(config)

    def test_an_empty_channel_set_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_verification({"channels": []})

    def test_a_missing_channel_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_verification({"spec": {}})

    def test_the_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_verification([("channels", [])])

    def test_the_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            verification_status("hold")

    def test_the_named_tolerance_is_far_below_any_declared_limit(self):
        self.assertLess(LIMIT_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
