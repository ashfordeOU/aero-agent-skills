"""Contract tests for the clause 7.3.6 derating review item logic."""

import unittest

from q6012_derating_review_item_logic import (
    LIMIT_TOLERANCE,
    assess_derating_review,
    assess_stress_item,
    derated_limit,
    is_within_derated_limit,
    stress_margin,
    undeclared_stresses,
    utilisation_ratio,
    validate_rule,
    worst_case_stress,
)

VOLTAGE_RULE = {"mode": "fraction", "value": 0.6, "direction": "upper"}
POWER_RULE = {"mode": "fraction", "value": 0.5, "direction": "upper"}
JUNCTION_RULE = {"mode": "offset", "value": 40.0, "direction": "upper"}
HOLDUP_RULE = {"mode": "fraction", "value": 0.8, "direction": "lower"}

RULES = {
    "applied-voltage": VOLTAGE_RULE,
    "power-dissipation": POWER_RULE,
    "junction-temperature": JUNCTION_RULE,
}


def voltage_item(nominal=18.0, uncertainty=0.0, rating=50.0, device="U1"):
    return {
        "device": device,
        "parameter": "applied-voltage",
        "rating": rating,
        "nominal_stress": nominal,
        "uncertainty": uncertainty,
    }


class ValidateRuleTests(unittest.TestCase):
    def test_returns_normalised_triple(self):
        self.assertEqual(validate_rule(VOLTAGE_RULE), ("fraction", 0.6, "upper"))

    def test_direction_case_is_normalised(self):
        rule = {"mode": "Fraction", "value": 0.5, "direction": "UPPER"}
        self.assertEqual(validate_rule(rule), ("fraction", 0.5, "upper"))

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule({"mode": "percent", "value": 0.5, "direction": "upper"})

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule({"mode": "fraction", "value": 0.5, "direction": "sideways"})

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule({"mode": "fraction", "value": 1.4, "direction": "upper"})

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule({"mode": "fraction", "value": 0.0, "direction": "upper"})

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule({"mode": "offset", "value": -5.0, "direction": "upper"})

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule({"mode": "fraction", "value": 0.5})

    def test_non_mapping_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule(["fraction", 0.5, "upper"])


class DeratedLimitTests(unittest.TestCase):
    def test_upper_fraction_scales_the_rating_down(self):
        self.assertAlmostEqual(derated_limit(50.0, VOLTAGE_RULE), 30.0, places=9)

    def test_upper_offset_steps_below_the_rating(self):
        self.assertAlmostEqual(derated_limit(125.0, JUNCTION_RULE), 85.0, places=9)

    def test_lower_fraction_raises_the_floor(self):
        self.assertAlmostEqual(derated_limit(10.0, HOLDUP_RULE), 12.5, places=9)

    def test_lower_offset_steps_above_the_rating(self):
        rule = {"mode": "offset", "value": 3.0, "direction": "lower"}
        self.assertAlmostEqual(derated_limit(10.0, rule), 13.0, places=9)

    def test_offset_mode_accepts_a_negative_rating_scale(self):
        rule = {"mode": "offset", "value": 10.0, "direction": "upper"}
        self.assertAlmostEqual(derated_limit(-20.0, rule), -30.0, places=9)

    def test_fraction_mode_refuses_a_non_positive_rating(self):
        with self.assertRaises(ValueError):
            derated_limit(0.0, VOLTAGE_RULE)

    def test_non_numeric_rating_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit("50", VOLTAGE_RULE)

    def test_boolean_rating_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit(True, VOLTAGE_RULE)


class WorstCaseStressTests(unittest.TestCase):
    def test_upper_bound_widens_upwards(self):
        self.assertAlmostEqual(worst_case_stress(20.0, 0.1, "upper"), 22.0, places=9)

    def test_lower_bound_widens_downwards(self):
        self.assertAlmostEqual(worst_case_stress(20.0, 0.1, "lower"), 18.0, places=9)

    def test_negative_nominal_still_widens_away_from_an_upper_bound(self):
        self.assertAlmostEqual(worst_case_stress(-40.0, 0.25, "upper"), -30.0, places=9)

    def test_zero_uncertainty_returns_the_nominal(self):
        self.assertAlmostEqual(worst_case_stress(7.5, 0.0, "upper"), 7.5, places=9)

    def test_uncertainty_above_one_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_stress(20.0, 1.5, "upper")

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_stress(20.0, -0.1, "upper")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_stress(20.0, 0.1, "outward")


class MarginAndUtilisationTests(unittest.TestCase):
    def test_upper_margin_is_headroom(self):
        self.assertAlmostEqual(stress_margin(25.0, 30.0, "upper"), 5.0, places=9)

    def test_lower_margin_is_overhead(self):
        self.assertAlmostEqual(stress_margin(14.0, 12.5, "lower"), 1.5, places=9)

    def test_upper_utilisation_is_the_consumed_fraction(self):
        self.assertAlmostEqual(utilisation_ratio(24.0, 30.0, "upper"), 0.8, places=9)

    def test_lower_utilisation_passes_one_when_the_floor_is_met(self):
        self.assertAlmostEqual(utilisation_ratio(12.5, 12.5, "lower"), 1.0, places=9)

    def test_utilisation_above_one_is_an_exceedance(self):
        self.assertGreater(utilisation_ratio(36.0, 30.0, "upper"), 1.0)

    def test_utilisation_refuses_a_non_positive_denominator(self):
        with self.assertRaises(ValueError):
            utilisation_ratio(-50.0, -30.0, "upper")

    def test_stress_exactly_on_the_limit_is_inside(self):
        self.assertTrue(is_within_derated_limit(30.0, 30.0, "upper"))

    def test_stress_one_tolerance_inside_the_limit_is_inside(self):
        self.assertTrue(is_within_derated_limit(30.0 - LIMIT_TOLERANCE, 30.0, "upper"))

    def test_clear_exceedance_is_outside(self):
        self.assertFalse(is_within_derated_limit(31.0, 30.0, "upper"))


class AssessStressItemTests(unittest.TestCase):
    def test_compliant_voltage_item(self):
        record = assess_stress_item(voltage_item(), RULES)
        self.assertTrue(record["compliant"])
        self.assertTrue(record["covered"])
        self.assertAlmostEqual(record["derated_limit"], 30.0, places=9)
        self.assertAlmostEqual(record["utilisation"], 0.6, places=9)

    def test_uncertainty_can_push_an_item_over(self):
        record = assess_stress_item(voltage_item(nominal=28.0, uncertainty=0.1), RULES)
        self.assertFalse(record["compliant"])
        self.assertAlmostEqual(record["worst_case_stress"], 30.8, places=9)

    def test_item_landing_exactly_on_the_limit_stays_compliant(self):
        record = assess_stress_item(voltage_item(nominal=30.0), RULES)
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["margin"], 0.0, places=9)
        self.assertAlmostEqual(record["utilisation"], 1.0, places=9)

    def test_offset_rule_item_uses_the_stepped_limit(self):
        item = {
            "device": "U2",
            "parameter": "junction-temperature",
            "rating": 125.0,
            "nominal_stress": 80.0,
        }
        record = assess_stress_item(item, RULES)
        self.assertAlmostEqual(record["derated_limit"], 85.0, places=9)
        self.assertTrue(record["compliant"])

    def test_stress_without_a_rule_is_not_a_pass(self):
        item = voltage_item()
        item["parameter"] = "reverse-current"
        record = assess_stress_item(item, RULES)
        self.assertFalse(record["covered"])
        self.assertFalse(record["compliant"])
        self.assertIn("no derating rule", record["advisories"][0])

    def test_rule_with_no_reduction_raises_an_advisory(self):
        rules = dict(RULES)
        rules["applied-voltage"] = {"mode": "fraction", "value": 1.0, "direction": "upper"}
        record = assess_stress_item(voltage_item(), rules)
        self.assertTrue(record["compliant"])
        self.assertTrue(any("no reduction" in a for a in record["advisories"]))

    def test_missing_item_key_rejected(self):
        item = voltage_item()
        del item["rating"]
        with self.assertRaises(ValueError):
            assess_stress_item(item, RULES)

    def test_empty_device_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_stress_item(voltage_item(device="   "), RULES)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_stress_item(["U1", "applied-voltage"], RULES)


class UndeclaredStressTests(unittest.TestCase):
    def test_reports_the_parameter_a_device_never_declared(self):
        items = [voltage_item()]
        gaps = undeclared_stresses(items, ["applied-voltage", "junction-temperature"])
        self.assertEqual(gaps, [("U1", "junction-temperature")])

    def test_no_gap_when_every_required_stress_is_declared(self):
        items = [
            voltage_item(),
            {
                "device": "U1",
                "parameter": "junction-temperature",
                "rating": 125.0,
                "nominal_stress": 80.0,
            },
        ]
        self.assertEqual(
            undeclared_stresses(items, ["applied-voltage", "junction-temperature"]), []
        )

    def test_gaps_are_reported_per_device(self):
        items = [voltage_item(device="U1"), voltage_item(device="U2")]
        gaps = undeclared_stresses(items, ["power-dissipation"])
        self.assertEqual(gaps, [("U1", "power-dissipation"), ("U2", "power-dissipation")])

    def test_non_sequence_items_rejected(self):
        with self.assertRaises(ValueError):
            undeclared_stresses("U1", ["applied-voltage"])


class AssessDeratingReviewTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "items": [
                voltage_item(nominal=18.0),
                {
                    "device": "U1",
                    "parameter": "junction-temperature",
                    "rating": 125.0,
                    "nominal_stress": 70.0,
                },
            ],
            "rules": RULES,
            "required_parameters": ["applied-voltage", "junction-temperature"],
        }
        spec.update(overrides)
        return spec

    def test_clean_review_item_closes(self):
        result = assess_derating_review(self._spec())
        self.assertEqual(result["disposition"], "closed")
        self.assertEqual(result["findings"], [])

    def test_exceedance_opens_the_item_and_is_named(self):
        spec = self._spec()
        spec["items"][0]["nominal_stress"] = 42.0
        result = assess_derating_review(spec)
        self.assertEqual(result["disposition"], "open")
        self.assertEqual(len(result["exceedances"]), 1)
        self.assertIn("U1 applied-voltage", result["findings"][0])

    def test_uncovered_stress_opens_the_item(self):
        spec = self._spec()
        spec["items"][1]["parameter"] = "reverse-current"
        result = assess_derating_review(spec)
        self.assertEqual(result["disposition"], "open")
        self.assertEqual(len(result["uncovered"]), 1)

    def test_undeclared_required_stress_opens_the_item(self):
        spec = self._spec()
        spec["items"] = [voltage_item(nominal=18.0)]
        result = assess_derating_review(spec)
        self.assertEqual(result["disposition"], "open")
        self.assertEqual(result["undeclared"], [("U1", "junction-temperature")])

    def test_worst_case_item_is_the_tightest_normalised_margin(self):
        spec = self._spec()
        spec["items"][0]["nominal_stress"] = 29.5
        result = assess_derating_review(spec)
        self.assertEqual(result["worst_case_item"]["parameter"], "applied-voltage")

    def test_every_exceedance_is_reported_not_just_the_first(self):
        spec = self._spec()
        spec["items"][0]["nominal_stress"] = 45.0
        spec["items"][1]["nominal_stress"] = 120.0
        result = assess_derating_review(spec)
        self.assertEqual(len(result["exceedances"]), 2)

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_derating_review(self._spec(items=[]))

    def test_empty_rule_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_derating_review(self._spec(rules={}))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["rules"]
        with self.assertRaises(ValueError):
            assess_derating_review(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_derating_review(["items"])

    def test_malformed_rule_in_the_set_rejected(self):
        spec = self._spec()
        spec["rules"] = dict(RULES)
        spec["rules"]["applied-voltage"] = {"mode": "fraction", "value": 2.0, "direction": "upper"}
        with self.assertRaises(ValueError):
            assess_derating_review(spec)


if __name__ == "__main__":
    unittest.main()
