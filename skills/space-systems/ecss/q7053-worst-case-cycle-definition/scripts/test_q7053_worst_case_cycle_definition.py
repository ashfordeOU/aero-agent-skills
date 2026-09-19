"""Contract tests for the worst-case sterilization cycle definition logic."""

import unittest

from q7053_worst_case_cycle_definition_logic import (
    MARGIN_TOLERANCE,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    assess_worst_case_cycle,
    capability_margin,
    derive_parameter,
    driving_parameter,
    scaled_level,
    validate_campaign,
    validate_parameter,
    worst_corner,
)


def parameter(name, nominal, tolerance, direction=SEVERITY_HIGH, cumulative=False,
              capability=None):
    return {
        "name": name,
        "nominal": nominal,
        "tolerance": tolerance,
        "direction": direction,
        "cumulative": cumulative,
        "capability": capability,
    }


TEMPERATURE = parameter("temperature_c", 125.0, 5.0, SEVERITY_HIGH, False, 150.0)
DWELL = parameter("dwell_h", 30.0, 2.0, SEVERITY_HIGH, True, 400.0)
HUMIDITY_FLOOR = parameter("humidity_pct", 40.0, 5.0, SEVERITY_LOW, False, 30.0)


class CampaignValidationTests(unittest.TestCase):
    def test_campaign_returns_count_and_factor(self):
        self.assertEqual(validate_campaign(3, 1.5), (3, 1.5))

    def test_zero_cycles_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign(0, 1.0)

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign(2.5, 1.0)

    def test_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign(3, 0.9)

    def test_factor_of_exactly_one_is_allowed(self):
        self.assertAlmostEqual(validate_campaign(3, 1.0)[1], 1.0, places=12)


class ParameterValidationTests(unittest.TestCase):
    def test_parameter_is_normalised(self):
        record = validate_parameter(TEMPERATURE)
        self.assertEqual(record["name"], "temperature_c")
        self.assertEqual(record["direction"], SEVERITY_HIGH)

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("x", 1.0, 0.1, "sideways"))

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("x", 1.0, -0.1))

    def test_non_boolean_cumulative_flag_rejected(self):
        bad = parameter("x", 1.0, 0.1)
        bad["cumulative"] = "yes"
        with self.assertRaises(ValueError):
            validate_parameter(bad)

    def test_missing_key_rejected(self):
        bad = parameter("x", 1.0, 0.1)
        del bad["direction"]
        with self.assertRaises(ValueError):
            validate_parameter(bad)

    def test_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter("x", 1.0, 0.1, capability=0.0))

    def test_absent_capability_is_allowed(self):
        self.assertIsNone(validate_parameter(parameter("x", 1.0, 0.1))["capability"])


class WorstCornerTests(unittest.TestCase):
    def test_upward_severity_adds_the_tolerance(self):
        self.assertAlmostEqual(worst_corner(125.0, 5.0, SEVERITY_HIGH), 130.0, places=9)

    def test_downward_severity_subtracts_the_tolerance(self):
        self.assertAlmostEqual(worst_corner(40.0, 5.0, SEVERITY_LOW), 35.0, places=9)

    def test_zero_tolerance_leaves_the_nominal(self):
        self.assertAlmostEqual(worst_corner(125.0, 0.0, SEVERITY_HIGH), 125.0, places=12)

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            worst_corner(125.0, 5.0, "sideways")


class ScalingTests(unittest.TestCase):
    def test_cumulative_parameter_carries_the_cycle_count(self):
        self.assertAlmostEqual(scaled_level(32.0, True, 10, 1.0), 320.0, places=9)

    def test_over_test_factor_multiplies_a_cumulative_parameter(self):
        self.assertAlmostEqual(scaled_level(32.0, True, 10, 1.5), 480.0, places=9)

    def test_instantaneous_parameter_is_not_scaled(self):
        self.assertAlmostEqual(scaled_level(130.0, False, 10, 1.5), 130.0, places=9)

    def test_non_boolean_cumulative_flag_rejected(self):
        with self.assertRaises(ValueError):
            scaled_level(130.0, "yes", 10, 1.0)

    def test_factor_below_one_rejected_by_scaling(self):
        with self.assertRaises(ValueError):
            scaled_level(130.0, True, 10, 0.5)


class MarginTests(unittest.TestCase):
    def test_upward_margin_is_the_unused_headroom(self):
        self.assertAlmostEqual(capability_margin(120.0, 150.0, SEVERITY_HIGH), 0.2, places=12)

    def test_downward_margin_counts_upward_from_the_floor(self):
        self.assertAlmostEqual(capability_margin(36.0, 30.0, SEVERITY_LOW), 0.2, places=12)

    def test_level_exactly_at_capability_is_zero_margin(self):
        self.assertAlmostEqual(capability_margin(150.0, 150.0, SEVERITY_HIGH), 0.0, places=12)

    def test_breach_is_negative(self):
        self.assertAlmostEqual(capability_margin(180.0, 150.0, SEVERITY_HIGH), -0.2, places=12)

    def test_undeclared_capability_leaves_the_margin_undefined(self):
        self.assertIsNone(capability_margin(180.0, None, SEVERITY_HIGH))


class DerivationTests(unittest.TestCase):
    def test_temperature_is_pushed_but_not_scaled(self):
        record = derive_parameter(TEMPERATURE, 10, 1.5)
        self.assertAlmostEqual(record["worst_case_level"], 130.0, places=9)

    def test_dwell_is_pushed_and_scaled(self):
        record = derive_parameter(DWELL, 10, 1.5)
        self.assertAlmostEqual(record["worst_case_level"], 480.0, places=9)

    def test_scaled_dwell_can_breach_its_capability(self):
        record = derive_parameter(DWELL, 10, 1.5)
        self.assertFalse(record["within_capability"])

    def test_humidity_floor_uses_the_downward_sense(self):
        record = derive_parameter(HUMIDITY_FLOOR, 3, 1.0)
        self.assertAlmostEqual(record["worst_case_level"], 35.0, places=9)
        self.assertTrue(record["within_capability"])

    def test_margin_exactly_zero_is_within_capability(self):
        at_limit = parameter("temperature_c", 145.0, 5.0, SEVERITY_HIGH, False, 150.0)
        record = derive_parameter(at_limit, 1, 1.0)
        self.assertAlmostEqual(record["margin"], 0.0, places=12)
        self.assertTrue(record["within_capability"])

    def test_undeclared_capability_leaves_the_verdict_undefined(self):
        record = derive_parameter(parameter("agent_ppm", 600.0, 50.0), 1, 1.0)
        self.assertIsNone(record["within_capability"])


class DrivingParameterTests(unittest.TestCase):
    def test_least_margin_drives(self):
        records = [
            {"name": "a", "margin": 0.4},
            {"name": "b", "margin": 0.1},
        ]
        self.assertEqual(driving_parameter(records)["name"], "b")

    def test_tie_is_broken_on_the_name(self):
        records = [
            {"name": "b", "margin": 0.1},
            {"name": "a", "margin": 0.1},
        ]
        self.assertEqual(driving_parameter(records)["name"], "a")

    def test_undefined_margins_are_skipped(self):
        records = [
            {"name": "a", "margin": None},
            {"name": "b", "margin": 0.3},
        ]
        self.assertEqual(driving_parameter(records)["name"], "b")

    def test_all_undefined_margins_give_no_driver(self):
        self.assertIsNone(driving_parameter([{"name": "a", "margin": None}]))

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            driving_parameter([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            driving_parameter([{"name": "a"}])


class WorstCaseCycleTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "method": "dry-heat",
            "parameters": [
                TEMPERATURE,
                parameter("dwell_h", 30.0, 2.0, SEVERITY_HIGH, True, 400.0),
                HUMIDITY_FLOOR,
            ],
            "cycle_count": 3,
            "over_test_factor": 1.0,
        }
        spec.update(overrides)
        return spec

    def test_acceptable_definition_has_no_findings(self):
        result = assess_worst_case_cycle(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_derived_dwell_carries_the_cycle_count(self):
        result = assess_worst_case_cycle(self._spec())
        dwell = [p for p in result["parameters"] if p["name"] == "dwell_h"][0]
        self.assertAlmostEqual(dwell["worst_case_level"], 96.0, places=9)

    def test_driving_parameter_is_reported(self):
        result = assess_worst_case_cycle(self._spec())
        self.assertEqual(result["driving_parameter"], "temperature_c")

    def test_more_cycles_can_break_the_definition(self):
        result = assess_worst_case_cycle(self._spec(cycle_count=20))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("dwell_h" in f for f in result["findings"]))

    def test_over_test_factor_raises_the_cumulative_level(self):
        plain = assess_worst_case_cycle(self._spec())
        over = assess_worst_case_cycle(self._spec(over_test_factor=2.0))
        plain_dwell = [p for p in plain["parameters"] if p["name"] == "dwell_h"][0]
        over_dwell = [p for p in over["parameters"] if p["name"] == "dwell_h"][0]
        self.assertAlmostEqual(
            over_dwell["worst_case_level"] / plain_dwell["worst_case_level"], 2.0, places=9
        )

    def test_undeclared_capability_is_a_finding(self):
        spec = self._spec(
            parameters=[TEMPERATURE, parameter("agent_ppm", 600.0, 50.0)]
        )
        result = assess_worst_case_cycle(spec)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("agent_ppm" in f for f in result["findings"]))

    def test_duplicated_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_worst_case_cycle(self._spec(parameters=[TEMPERATURE, TEMPERATURE]))

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_worst_case_cycle(self._spec(parameters=[]))

    def test_unnamed_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_worst_case_cycle(self._spec(method=""))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["cycle_count"]
        with self.assertRaises(ValueError):
            assess_worst_case_cycle(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_worst_case_cycle(["method"])

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertAlmostEqual(MARGIN_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
