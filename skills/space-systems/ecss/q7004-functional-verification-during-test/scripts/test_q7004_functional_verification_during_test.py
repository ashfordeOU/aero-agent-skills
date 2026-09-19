"""Contract tests for the ECSS-Q-ST-70-04C at-temperature functional verification."""

import unittest

from q7004_functional_verification_during_test_logic import (
    COMPARISON_TOLERANCE,
    CONDITIONS,
    EXTREME_CONDITIONS,
    ambient_drift,
    assess_functional_verification,
    check_at_condition,
    check_key,
    condition_temperature,
    coverage,
    index_checks,
    parameter_verdicts,
    relative_drift,
    required_check_points,
)

TARGETS = {
    "ambient-pre": 22.0,
    "cold-extreme": -40.0,
    "hot-extreme": 70.0,
    "ambient-post": 22.0,
}

LIMITS = {
    "bus_current_a": (0.80, 1.20),
    "output_voltage_v": (4.75, 5.25),
}


def measurements(current=1.00, voltage=5.00):
    return {"bus_current_a": current, "output_voltage_v": voltage}


def check(condition, cycle, temperature_c, **kwargs):
    return {
        "condition": condition,
        "cycle": cycle,
        "temperature_c": temperature_c,
        "measurements": kwargs.get("measurements", measurements()),
    }


def full_checks(cycle_count=8):
    checks = [check("ambient-pre", 0, 22.0)]
    for cycle in (1, cycle_count):
        checks.append(check("cold-extreme", cycle, -40.0))
        checks.append(check("hot-extreme", cycle, 70.0))
    checks.append(check("ambient-post", cycle_count + 1, 22.0))
    return checks


def spec(**overrides):
    base = {
        "cycle_count": 8,
        "checks": full_checks(),
        "parameter_limits": dict(LIMITS),
        "target_temperatures": dict(TARGETS),
        "band_k": 3.0,
        "allowable_drift_fraction": 0.02,
    }
    base.update(overrides)
    return base


class CheckPointTests(unittest.TestCase):
    def test_a_single_cycle_campaign_owes_four_points(self):
        points = required_check_points(1)
        self.assertEqual(len(points), 4)

    def test_first_and_last_cycle_are_both_exercised(self):
        keys = [check_key(p) for p in required_check_points(8)]
        self.assertIn(("cold-extreme", 1), keys)
        self.assertIn(("hot-extreme", 8), keys)

    def test_ambient_references_bracket_the_campaign(self):
        points = required_check_points(8)
        self.assertEqual(points[0]["condition"], "ambient-pre")
        self.assertEqual(points[-1], {"condition": "ambient-post", "cycle": 9})

    def test_intermediate_interval_adds_cycles(self):
        keys = [check_key(p) for p in required_check_points(8, intermediate_every=4)]
        self.assertIn(("cold-extreme", 4), keys)
        self.assertIn(("hot-extreme", 4), keys)

    def test_intermediate_interval_does_not_duplicate_the_edges(self):
        points = required_check_points(8, intermediate_every=8)
        self.assertEqual(len(points), 6)

    def test_zero_cycles_rejected(self):
        with self.assertRaises(ValueError):
            required_check_points(0)

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            required_check_points(4.5)

    def test_zero_intermediate_interval_rejected(self):
        with self.assertRaises(ValueError):
            required_check_points(8, intermediate_every=0)

    def test_extremes_are_the_two_at_temperature_conditions(self):
        self.assertEqual(set(EXTREME_CONDITIONS), {"cold-extreme", "hot-extreme"})
        self.assertTrue(set(EXTREME_CONDITIONS).issubset(set(CONDITIONS)))


class KeyAndCoverageTests(unittest.TestCase):
    def test_key_is_condition_and_cycle(self):
        self.assertEqual(check_key(check("cold-extreme", 3, -40.0)), ("cold-extreme", 3))

    def test_unknown_condition_rejected(self):
        with self.assertRaises(ValueError):
            check_key({"condition": "vacuum-extreme", "cycle": 1})

    def test_negative_cycle_rejected(self):
        with self.assertRaises(ValueError):
            check_key({"condition": "cold-extreme", "cycle": -1})

    def test_duplicate_check_rejected(self):
        with self.assertRaises(ValueError):
            index_checks([check("cold-extreme", 1, -40.0), check("cold-extreme", 1, -40.0)])

    def test_full_set_is_complete(self):
        result = coverage(required_check_points(8), index_checks(full_checks()))
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_omitted_extreme_is_named(self):
        checks = [c for c in full_checks() if check_key(c) != ("hot-extreme", 8)]
        result = coverage(required_check_points(8), index_checks(checks))
        self.assertEqual(result["missing"], [("hot-extreme", 8)])

    def test_unscheduled_check_is_reported(self):
        checks = full_checks() + [check("cold-extreme", 5, -40.0)]
        result = coverage(required_check_points(8), index_checks(checks))
        self.assertEqual(result["unscheduled"], [("cold-extreme", 5)])


class ConditionTests(unittest.TestCase):
    def test_target_temperature_is_read_from_the_declaration(self):
        self.assertAlmostEqual(condition_temperature("cold-extreme", TARGETS), -40.0, places=9)

    def test_undeclared_condition_temperature_rejected(self):
        with self.assertRaises(ValueError):
            condition_temperature("hot-extreme", {"cold-extreme": -40.0})

    def test_check_inside_the_band_is_at_condition(self):
        result = check_at_condition(check("cold-extreme", 1, -38.0), TARGETS, 3.0)
        self.assertTrue(result["at_condition"])
        self.assertAlmostEqual(result["deviation_k"], 2.0, places=9)

    def test_check_exactly_on_the_band_edge_is_at_condition(self):
        result = check_at_condition(check("cold-extreme", 1, -37.0), TARGETS, 3.0)
        self.assertTrue(result["at_condition"])
        self.assertLessEqual(result["deviation_k"] - 3.0, COMPARISON_TOLERANCE)

    def test_check_outside_the_band_is_off_condition(self):
        result = check_at_condition(check("cold-extreme", 1, -20.0), TARGETS, 3.0)
        self.assertFalse(result["at_condition"])

    def test_check_without_a_temperature_rejected(self):
        bad = {"condition": "cold-extreme", "cycle": 1, "measurements": measurements()}
        with self.assertRaises(ValueError):
            check_at_condition(bad, TARGETS, 3.0)

    def test_zero_band_rejected(self):
        with self.assertRaises(ValueError):
            check_at_condition(check("cold-extreme", 1, -40.0), TARGETS, 0.0)


class ParameterTests(unittest.TestCase):
    def test_in_limit_parameters_pass(self):
        verdicts = parameter_verdicts(check("cold-extreme", 1, -40.0), LIMITS)
        self.assertTrue(all(v["within_limits"] for v in verdicts))

    def test_parameter_on_the_limit_passes(self):
        item = check("cold-extreme", 1, -40.0, measurements=measurements(current=1.20))
        verdicts = parameter_verdicts(item, LIMITS)
        current = [v for v in verdicts if v["parameter"] == "bus_current_a"][0]
        self.assertTrue(current["within_limits"])
        self.assertAlmostEqual(current["measured"], current["upper_limit"], places=9)

    def test_out_of_limit_parameter_fails(self):
        item = check("hot-extreme", 1, 70.0, measurements=measurements(voltage=5.60))
        verdicts = parameter_verdicts(item, LIMITS)
        voltage = [v for v in verdicts if v["parameter"] == "output_voltage_v"][0]
        self.assertFalse(voltage["within_limits"])

    def test_unmeasured_parameter_is_marked_missing(self):
        item = check("hot-extreme", 1, 70.0, measurements={"bus_current_a": 1.0})
        verdicts = parameter_verdicts(item, LIMITS)
        voltage = [v for v in verdicts if v["parameter"] == "output_voltage_v"][0]
        self.assertTrue(voltage["missing"])
        self.assertFalse(voltage["within_limits"])

    def test_check_with_no_measurements_rejected(self):
        bad = {"condition": "hot-extreme", "cycle": 1, "temperature_c": 70.0}
        with self.assertRaises(ValueError):
            parameter_verdicts(bad, LIMITS)

    def test_inverted_parameter_limits_rejected(self):
        with self.assertRaises(ValueError):
            parameter_verdicts(check("hot-extreme", 1, 70.0), {"bus_current_a": (1.2, 0.8)})

    def test_empty_limit_set_rejected(self):
        with self.assertRaises(ValueError):
            parameter_verdicts(check("hot-extreme", 1, 70.0), {})


class DriftTests(unittest.TestCase):
    def test_relative_drift_is_a_fraction_of_the_reference(self):
        self.assertAlmostEqual(relative_drift(1.00, 1.05), 0.05, places=9)

    def test_drift_is_signless(self):
        self.assertAlmostEqual(relative_drift(1.00, 0.95), 0.05, places=9)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_drift(0.0, 0.05)

    def test_unchanged_parameters_show_no_drift(self):
        results = ambient_drift(
            check("ambient-pre", 0, 22.0), check("ambient-post", 9, 22.0), LIMITS, 0.02
        )
        self.assertTrue(all(r["acceptable"] for r in results))
        self.assertAlmostEqual(results[0]["drift"], 0.0, places=12)

    def test_drift_exactly_on_the_allowance_is_acceptable(self):
        post = check("ambient-post", 9, 22.0, measurements=measurements(current=1.02))
        results = ambient_drift(check("ambient-pre", 0, 22.0), post, LIMITS, 0.02)
        current = [r for r in results if r["parameter"] == "bus_current_a"][0]
        self.assertTrue(current["acceptable"])
        self.assertAlmostEqual(current["drift"], 0.02, places=9)

    def test_excessive_drift_is_refused(self):
        post = check("ambient-post", 9, 22.0, measurements=measurements(current=1.20))
        results = ambient_drift(check("ambient-pre", 0, 22.0), post, LIMITS, 0.02)
        current = [r for r in results if r["parameter"] == "bus_current_a"][0]
        self.assertFalse(current["acceptable"])

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            ambient_drift(
                check("ambient-pre", 0, 22.0), check("ambient-post", 9, 22.0), LIMITS, -0.01
            )


class AssessmentTests(unittest.TestCase):
    def test_complete_campaign_verifies(self):
        result = assess_functional_verification(spec())
        self.assertTrue(result["verified"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["extremes_exercised"])

    def test_missing_hot_extreme_is_a_finding(self):
        checks = [c for c in full_checks() if check_key(c) != ("hot-extreme", 1)]
        result = assess_functional_verification(spec(checks=checks))
        self.assertFalse(result["verified"])
        self.assertFalse(result["extremes_exercised"])
        self.assertIn("no functional check at hot-extreme of cycle 1", result["findings"])

    def test_check_taken_off_condition_is_a_finding(self):
        checks = full_checks()
        checks[1] = check("cold-extreme", 1, -10.0)
        result = assess_functional_verification(spec(checks=checks))
        self.assertFalse(result["verified"])
        self.assertTrue(any("off its condition" in f for f in result["findings"]))

    def test_out_of_limit_reading_at_an_extreme_is_a_finding(self):
        checks = full_checks()
        checks[2] = check("hot-extreme", 1, 70.0, measurements=measurements(voltage=5.90))
        result = assess_functional_verification(spec(checks=checks))
        self.assertFalse(result["verified"])
        self.assertTrue(any("outside its limits" in f for f in result["findings"]))

    def test_campaign_drift_is_a_finding(self):
        checks = full_checks()
        checks[-1] = check(
            "ambient-post", 9, 22.0, measurements=measurements(current=1.15)
        )
        result = assess_functional_verification(spec(checks=checks))
        self.assertFalse(result["verified"])
        self.assertTrue(any("drifted" in f for f in result["findings"]))

    def test_drift_is_not_computed_without_both_references(self):
        checks = [c for c in full_checks() if check_key(c) != ("ambient-post", 9)]
        result = assess_functional_verification(spec(checks=checks))
        self.assertIsNone(result["drift"])

    def test_intermediate_cycles_extend_the_required_set(self):
        result = assess_functional_verification(spec(intermediate_every=4))
        self.assertFalse(result["verified"])
        self.assertIn("no functional check at cold-extreme of cycle 4", result["findings"])

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["band_k"]
        with self.assertRaises(ValueError):
            assess_functional_verification(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_functional_verification("checks")


if __name__ == "__main__":
    unittest.main()
