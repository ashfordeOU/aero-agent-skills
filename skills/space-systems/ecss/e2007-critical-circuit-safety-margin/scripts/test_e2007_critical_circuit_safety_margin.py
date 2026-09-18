#!/usr/bin/env python3
"""Gate 3 contract test for e2007-critical-circuit-safety-margin.

Stdlib unittest only, offline, deterministic. Every decibel boundary case is
asserted with assertAlmostEqual against the bound and on the decision the
logic then takes, never with a strict inequality that depends on which side
of the last bit a base-ten logarithm lands.
"""

import unittest

from e2007_critical_circuit_safety_margin_logic import (
    AMPLITUDE,
    DEFAULT_MARGIN_SPEC,
    EED_FIRING_LINE,
    MARGIN_EPS,
    POWER,
    derated_threshold,
    evaluate_campaign,
    evaluate_circuit,
    margin_db,
    quantity_multiplier,
    remaining_margin_db,
    required_margin_db,
    resolve_spec,
    verification_status,
    worst_case_circuit,
)


def nominal_circuits():
    return [
        {"name": "separation-initiator-line", "category": "eed-firing-line",
         "quantity_kind": "amplitude", "threshold": 1.0, "induced": 0.005},
        {"name": "arm-enable-command", "category": "safety-critical-circuit",
         "quantity_kind": "amplitude", "threshold": 2.0, "induced": 0.02},
        {"name": "attitude-sensor-return", "category": "mission-critical-circuit",
         "quantity_kind": "amplitude", "threshold": 1.0, "induced": 0.1},
        {"name": "housekeeping-telemetry", "category": "non-critical-circuit",
         "quantity_kind": "power", "threshold": 1.0, "induced": 0.1},
    ]


def nominal_config():
    return {"circuits": nominal_circuits()}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["required_margin_db_eed_firing_line"], 20.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_MARGIN_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"required_margin_db_eed_firing_line": 26.0})
        self.assertAlmostEqual(spec["required_margin_db_eed_firing_line"], 26.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"required_margin_db_eed_firing_line": 26.0})
        self.assertAlmostEqual(
            DEFAULT_MARGIN_SPEC["required_margin_db_eed_firing_line"], 20.0, places=9
        )

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"required_margin_db_coffee_line": 3.0})

    def test_negative_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"required_margin_db_non_critical_circuit": -1.0})

    def test_derating_factor_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"eed_no_fire_derating_factor": 1.5})

    def test_zero_derating_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"eed_no_fire_derating_factor": 0.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("eed_no_fire_derating_factor", 0.5)])


class TestQuantityKind(unittest.TestCase):
    def test_amplitude_uses_the_twenty_multiplier(self):
        self.assertAlmostEqual(quantity_multiplier(AMPLITUDE), 20.0, places=9)

    def test_power_uses_the_ten_multiplier(self):
        self.assertAlmostEqual(quantity_multiplier(POWER), 10.0, places=9)

    def test_unrecognized_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            quantity_multiplier("field-strength-squared")


class TestMarginArithmetic(unittest.TestCase):
    def test_a_decade_of_amplitude_is_twenty_decibels(self):
        self.assertAlmostEqual(margin_db(1.0, 0.1, AMPLITUDE), 20.0, places=9)

    def test_a_decade_of_power_is_ten_decibels(self):
        self.assertAlmostEqual(margin_db(1.0, 0.1, POWER), 10.0, places=9)

    def test_an_induced_level_at_the_threshold_is_zero_margin(self):
        self.assertAlmostEqual(margin_db(0.4, 0.4, AMPLITUDE), 0.0, places=9)

    def test_an_induced_level_above_the_threshold_is_a_negative_margin(self):
        self.assertAlmostEqual(margin_db(0.1, 1.0, AMPLITUDE), -20.0, places=9)

    def test_zero_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(0.0, 0.1, AMPLITUDE)

    def test_zero_induced_level_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(1.0, 0.0, AMPLITUDE)

    def test_non_numeric_level_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_db("1.0", 0.1, AMPLITUDE)

    def test_infinite_level_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(float("inf"), 0.1, AMPLITUDE)


class TestDerating(unittest.TestCase):
    def test_half_derating_halves_the_threshold(self):
        self.assertAlmostEqual(derated_threshold(1.0, 0.5), 0.5, places=9)

    def test_unit_factor_leaves_the_threshold_alone(self):
        self.assertAlmostEqual(derated_threshold(0.75, 1.0), 0.75, places=9)

    def test_factor_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_threshold(1.0, 1.2)

    def test_negative_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_threshold(-1.0, 0.5)


class TestRequiredMargin(unittest.TestCase):
    def test_a_firing_line_carries_the_largest_requirement(self):
        self.assertAlmostEqual(required_margin_db(EED_FIRING_LINE), 20.0, places=9)

    def test_a_non_critical_circuit_carries_the_smallest(self):
        self.assertAlmostEqual(required_margin_db("non-critical-circuit"), 6.0, places=9)

    def test_unrecognized_category_is_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("nice-to-have-circuit")


class TestCircuitEvaluation(unittest.TestCase):
    def test_a_firing_line_is_graded_on_the_derated_threshold(self):
        result = evaluate_circuit(nominal_circuits()[0])
        self.assertAlmostEqual(result["applied_threshold"], 0.5, places=9)
        self.assertAlmostEqual(result["margin_db"], 40.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_firing_line_exactly_on_its_requirement_is_compliant(self):
        circuit = nominal_circuits()[0]
        circuit["induced"] = 0.05
        result = evaluate_circuit(circuit)
        self.assertAlmostEqual(result["margin_db"], 20.0, places=9)
        self.assertAlmostEqual(result["required_margin_db"], 20.0, places=9)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["shortfall_db"], 0.0, places=9)

    def test_a_firing_line_short_of_its_requirement_is_not_compliant(self):
        circuit = nominal_circuits()[0]
        circuit["induced"] = 0.5
        result = evaluate_circuit(circuit)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["shortfall_db"], 20.0, places=9)

    def test_a_non_derated_category_keeps_its_threshold(self):
        result = evaluate_circuit(nominal_circuits()[1])
        self.assertAlmostEqual(result["derating_factor"], 1.0, places=9)
        self.assertAlmostEqual(result["applied_threshold"], 2.0, places=9)

    def test_the_power_form_does_not_borrow_the_amplitude_multiplier(self):
        result = evaluate_circuit(nominal_circuits()[3])
        self.assertAlmostEqual(result["multiplier"], 10.0, places=9)
        self.assertAlmostEqual(result["margin_db"], 10.0, places=9)

    def test_derating_override_changes_the_applied_threshold(self):
        result = evaluate_circuit(
            nominal_circuits()[0], {"eed_no_fire_derating_factor": 0.25}
        )
        self.assertAlmostEqual(result["applied_threshold"], 0.25, places=9)

    def test_unrecognized_category_on_a_circuit_is_rejected(self):
        circuit = nominal_circuits()[0]
        circuit["category"] = "spare-line"
        with self.assertRaises(ValueError):
            evaluate_circuit(circuit)

    def test_circuit_without_a_name_is_rejected(self):
        circuit = nominal_circuits()[0]
        circuit["name"] = "  "
        with self.assertRaises(ValueError):
            evaluate_circuit(circuit)

    def test_non_positive_induced_level_is_rejected(self):
        circuit = nominal_circuits()[0]
        circuit["induced"] = 0.0
        with self.assertRaises(ValueError):
            evaluate_circuit(circuit)

    def test_circuit_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_circuit(["separation-initiator-line"])


class TestWorstCase(unittest.TestCase):
    def test_remaining_margin_is_the_distance_above_the_requirement(self):
        result = evaluate_circuit(nominal_circuits()[0])
        self.assertAlmostEqual(remaining_margin_db(result), 20.0, places=9)

    def test_the_worst_case_is_the_least_remaining_margin(self):
        results = [evaluate_circuit(c) for c in nominal_circuits()]
        self.assertEqual(worst_case_circuit(results)["name"], "housekeeping-telemetry")

    def test_worst_case_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_case_circuit([])

    def test_remaining_margin_rejects_an_incomplete_record(self):
        with self.assertRaises(ValueError):
            remaining_margin_db({"margin_db": 3.0})


class TestEndToEnd(unittest.TestCase):
    def test_a_compliant_set_demonstrates_the_margin(self):
        report = evaluate_campaign(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "margin-demonstrated")
        self.assertTrue(report["demonstrated"])

    def test_one_short_line_holds_the_verification(self):
        config = nominal_config()
        config["circuits"][1]["induced"] = 1.0
        report = evaluate_campaign(config)
        self.assertFalse(report["demonstrated"])
        self.assertEqual(report["status"], "hold-margin-verification")
        self.assertTrue(any("arm-enable-command" in f for f in report["findings"]))

    def test_the_report_names_the_worst_case_circuit(self):
        config = nominal_config()
        config["circuits"][2]["induced"] = 0.5
        report = evaluate_campaign(config)
        self.assertEqual(report["worst_case"]["name"], "attitude-sensor-return")

    def test_a_record_without_a_firing_line_is_a_finding(self):
        config = nominal_config()
        config["circuits"] = [c for c in config["circuits"]
                              if c["category"] != "eed-firing-line"]
        report = evaluate_campaign(config)
        self.assertTrue(any("firing line" in f for f in report["findings"]))

    def test_a_vehicle_without_initiators_needs_no_firing_line(self):
        config = nominal_config()
        config["circuits"] = [c for c in config["circuits"]
                              if c["category"] != "eed-firing-line"]
        config["eed_installed"] = False
        self.assertTrue(evaluate_campaign(config)["demonstrated"])

    def test_non_boolean_initiator_flag_is_rejected(self):
        config = nominal_config()
        config["eed_installed"] = "no"
        with self.assertRaises(ValueError):
            evaluate_campaign(config)

    def test_spec_override_can_requalify_a_campaign(self):
        config = nominal_config()
        config["circuits"][2]["induced"] = 0.5
        self.assertFalse(evaluate_campaign(config)["demonstrated"])
        config["spec"] = {"required_margin_db_mission_critical_circuit": 6.0}
        self.assertTrue(evaluate_campaign(config)["demonstrated"])

    def test_duplicate_circuit_names_are_rejected(self):
        config = nominal_config()
        config["circuits"][1]["name"] = config["circuits"][0]["name"]
        with self.assertRaises(ValueError):
            evaluate_campaign(config)

    def test_empty_circuit_set_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign({"circuits": []})

    def test_missing_required_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign({"spec": {}})

    def test_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_campaign([("circuits", [])])

    def test_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            verification_status("hold")

    def test_named_tolerance_is_far_below_any_decibel_requirement(self):
        self.assertLess(MARGIN_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
