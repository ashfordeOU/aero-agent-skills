#!/usr/bin/env python3
"""Gate 3 contract test for e2007-interface-loads-and-terminations.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_interface_loads_and_terminations_logic import (
    DEFAULT_TERMINATION_SPEC,
    EQUIVALENT_LOAD,
    REAL_HARDWARE,
    TERM_EPS,
    UNTERMINATED,
    categorize_interfaces,
    categorize_termination,
    check_equivalent_load,
    check_power_interface,
    evaluate_terminations,
    impedance_deviation_percent,
    load_rating_margin,
    real_hardware_fraction,
    resolve_spec,
    termination_readiness,
    unterminated_interfaces,
)


def nominal_interfaces():
    return [
        {
            "name": "primary-power-in",
            "kind": "power",
            "termination": "resistive-load-bank",
            "reference_impedance_ohm": 28.0,
            "actual_impedance_ohm": 28.0,
            "flight_load_current_a": 4.0,
            "simulated_load_current_a": 4.0,
            "interface_voltage_v": 28.0,
            "load_rating_w": 250.0,
        },
        {
            "name": "telemetry-bus",
            "kind": "data-bus",
            "termination": "data-bus-terminator",
            "reference_impedance_ohm": 78.0,
            "actual_impedance_ohm": 78.0,
            "reference_phase_deg": 0.0,
            "actual_phase_deg": 0.0,
        },
        {
            "name": "payload-rf-out",
            "kind": "rf",
            "termination": "rf-termination",
            "reference_impedance_ohm": 50.0,
            "actual_impedance_ohm": 50.5,
        },
        {"name": "thermistor-harness", "kind": "signal", "termination": "flight-unit"},
    ]


def nominal_config():
    return {"interfaces": nominal_interfaces()}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["impedance_tolerance_percent"], 10.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_TERMINATION_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"impedance_tolerance_percent": 2.0})
        self.assertAlmostEqual(spec["impedance_tolerance_percent"], 2.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"impedance_tolerance_percent": 2.0})
        self.assertAlmostEqual(
            DEFAULT_TERMINATION_SPEC["impedance_tolerance_percent"], 10.0, places=9
        )

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"bench_colour": 3.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("impedance_tolerance_percent", 2.0)])

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"phase_tolerance_deg": -1.0})


class TestCategorization(unittest.TestCase):
    def test_flight_unit_is_real_hardware(self):
        item = {"name": "a", "kind": "signal", "termination": "flight-unit"}
        self.assertEqual(categorize_termination(item), REAL_HARDWARE)

    def test_load_simulator_is_an_equivalent_load(self):
        item = {"name": "a", "kind": "power", "termination": "load-simulator"}
        self.assertEqual(categorize_termination(item), EQUIVALENT_LOAD)

    def test_open_circuit_is_unterminated(self):
        item = {"name": "a", "kind": "rf", "termination": "open-circuit"}
        self.assertEqual(categorize_termination(item), UNTERMINATED)

    def test_unknown_termination_is_rejected(self):
        item = {"name": "a", "kind": "rf", "termination": "a-bit-of-wire"}
        with self.assertRaises(ValueError):
            categorize_termination(item)

    def test_unknown_interface_kind_is_rejected(self):
        item = {"name": "a", "kind": "pneumatic", "termination": "flight-unit"}
        with self.assertRaises(ValueError):
            categorize_termination(item)

    def test_blank_name_is_rejected(self):
        item = {"name": "  ", "kind": "rf", "termination": "flight-unit"}
        with self.assertRaises(ValueError):
            categorize_termination(item)

    def test_empty_interface_list_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_interfaces([])

    def test_duplicate_interface_names_are_rejected(self):
        items = [
            {"name": "a", "kind": "rf", "termination": "flight-unit"},
            {"name": "a", "kind": "rf", "termination": "flight-unit"},
        ]
        with self.assertRaises(ValueError):
            categorize_interfaces(items)

    def test_every_interface_is_categorized(self):
        categorized = categorize_interfaces(nominal_interfaces())
        self.assertEqual(len(categorized), 4)
        self.assertEqual(categorized[3]["category"], REAL_HARDWARE)


class TestImpedanceDeviation(unittest.TestCase):
    def test_exact_match_has_no_deviation(self):
        self.assertAlmostEqual(impedance_deviation_percent(50.0, 50.0), 0.0, places=9)

    def test_ten_percent_high_is_ten_percent(self):
        self.assertAlmostEqual(impedance_deviation_percent(55.0, 50.0), 10.0, places=9)

    def test_deviation_is_unsigned(self):
        self.assertAlmostEqual(impedance_deviation_percent(45.0, 50.0), 10.0, places=9)

    def test_zero_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            impedance_deviation_percent(50.0, 0.0)

    def test_negative_actual_is_rejected(self):
        with self.assertRaises(ValueError):
            impedance_deviation_percent(-50.0, 50.0)

    def test_non_numeric_is_rejected(self):
        with self.assertRaises(ValueError):
            impedance_deviation_percent("50", 50.0)


class TestEquivalentLoadCheck(unittest.TestCase):
    def test_matching_load_passes_both_checks(self):
        check = check_equivalent_load(
            {
                "name": "rf",
                "reference_impedance_ohm": 50.0,
                "actual_impedance_ohm": 50.0,
            }
        )
        self.assertTrue(check["impedance_ok"])
        self.assertTrue(check["phase_ok"])

    def test_deviation_exactly_on_the_tolerance_is_accepted(self):
        check = check_equivalent_load(
            {
                "name": "rf",
                "reference_impedance_ohm": 50.0,
                "actual_impedance_ohm": 55.0,
            }
        )
        self.assertAlmostEqual(check["impedance_deviation_percent"], 10.0, places=9)
        self.assertTrue(check["impedance_ok"])

    def test_deviation_beyond_the_tolerance_fails(self):
        check = check_equivalent_load(
            {
                "name": "rf",
                "reference_impedance_ohm": 50.0,
                "actual_impedance_ohm": 60.0,
            }
        )
        self.assertFalse(check["impedance_ok"])

    def test_matching_magnitude_with_wrong_phase_fails(self):
        check = check_equivalent_load(
            {
                "name": "bus",
                "reference_impedance_ohm": 78.0,
                "actual_impedance_ohm": 78.0,
                "reference_phase_deg": 0.0,
                "actual_phase_deg": 35.0,
            }
        )
        self.assertTrue(check["impedance_ok"])
        self.assertFalse(check["phase_ok"])
        self.assertAlmostEqual(check["phase_deviation_deg"], 35.0, places=9)

    def test_phase_beyond_a_quarter_turn_is_rejected(self):
        with self.assertRaises(ValueError):
            check_equivalent_load(
                {
                    "name": "bus",
                    "reference_impedance_ohm": 78.0,
                    "actual_impedance_ohm": 78.0,
                    "actual_phase_deg": 120.0,
                }
            )

    def test_tighter_spec_rejects_a_load_the_default_accepts(self):
        record = {
            "name": "rf",
            "reference_impedance_ohm": 50.0,
            "actual_impedance_ohm": 53.0,
        }
        self.assertTrue(check_equivalent_load(record)["impedance_ok"])
        tight = check_equivalent_load(record, {"impedance_tolerance_percent": 2.0})
        self.assertFalse(tight["impedance_ok"])


class TestPowerInterfaceCheck(unittest.TestCase):
    def test_matching_load_current_passes(self):
        check = check_power_interface(nominal_interfaces()[0])
        self.assertTrue(check["current_ok"])
        self.assertTrue(check["rating_ok"])
        self.assertAlmostEqual(check["dissipated_w"], 112.0, places=9)

    def test_current_off_by_a_fifth_fails(self):
        record = dict(nominal_interfaces()[0])
        record["simulated_load_current_a"] = 4.8
        check = check_power_interface(record)
        self.assertFalse(check["current_ok"])
        self.assertAlmostEqual(check["current_deviation_percent"], 20.0, places=9)

    def test_underrated_load_bank_fails_the_margin(self):
        record = dict(nominal_interfaces()[0])
        record["load_rating_w"] = 120.0
        check = check_power_interface(record)
        self.assertFalse(check["rating_ok"])

    def test_rating_margin_exactly_on_the_requirement_is_accepted(self):
        record = dict(nominal_interfaces()[0])
        record["load_rating_w"] = 140.0
        check = check_power_interface(record)
        self.assertAlmostEqual(check["rating_margin"], 1.25, places=9)
        self.assertTrue(check["rating_ok"])

    def test_zero_flight_current_is_rejected(self):
        record = dict(nominal_interfaces()[0])
        record["flight_load_current_a"] = 0.0
        with self.assertRaises(ValueError):
            check_power_interface(record)

    def test_missing_voltage_is_rejected(self):
        record = dict(nominal_interfaces()[0])
        del record["interface_voltage_v"]
        with self.assertRaises(ValueError):
            check_power_interface(record)

    def test_rating_margin_is_a_ratio(self):
        self.assertAlmostEqual(load_rating_margin(250.0, 100.0), 2.5, places=9)

    def test_zero_dissipation_is_rejected(self):
        with self.assertRaises(ValueError):
            load_rating_margin(250.0, 0.0)


class TestAggregation(unittest.TestCase):
    """End-to-end workflow: every step of the termination review feeds one gate token."""

    def test_nominal_unit_is_ready(self):
        result = evaluate_terminations(nominal_config())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["status"], "ready-for-measurement")
        self.assertTrue(result["ready"])

    def test_an_open_interface_holds_the_run(self):
        config = nominal_config()
        config["interfaces"][2]["termination"] = "open-circuit"
        result = evaluate_terminations(config)
        self.assertFalse(result["ready"])
        self.assertEqual(result["unterminated"], ["payload-rf-out"])
        self.assertEqual(result["status"], "hold-terminations")

    def test_an_open_interface_is_not_impedance_checked(self):
        config = nominal_config()
        config["interfaces"][2]["termination"] = "left-disconnected"
        result = evaluate_terminations(config)
        names = [c["name"] for c in result["equivalent_load_checks"]]
        self.assertNotIn("payload-rf-out", names)

    def test_a_mismatched_equivalent_load_holds_the_run(self):
        config = nominal_config()
        config["interfaces"][1]["actual_impedance_ohm"] = 120.0
        result = evaluate_terminations(config)
        self.assertFalse(result["ready"])
        self.assertTrue(
            any("impedance tolerance" in f for f in result["findings"]),
            result["findings"],
        )

    def test_a_drifting_power_load_holds_the_run(self):
        config = nominal_config()
        config["interfaces"][0]["simulated_load_current_a"] = 6.0
        result = evaluate_terminations(config)
        self.assertFalse(result["ready"])
        self.assertTrue(
            any("flight load current" in f for f in result["findings"]), result["findings"]
        )

    def test_power_checks_only_run_on_power_interfaces(self):
        result = evaluate_terminations(nominal_config())
        self.assertEqual(
            [c["name"] for c in result["power_interface_checks"]], ["primary-power-in"]
        )

    def test_real_hardware_fraction_is_reported(self):
        result = evaluate_terminations(nominal_config())
        self.assertAlmostEqual(result["real_hardware_fraction"], 0.25, places=9)

    def test_a_real_hardware_floor_can_hold_the_run(self):
        config = nominal_config()
        config["spec"] = {"min_real_hardware_fraction": 0.5}
        result = evaluate_terminations(config)
        self.assertFalse(result["ready"])

    def test_missing_interfaces_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_terminations({})

    def test_non_mapping_config_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_terminations(["primary-power-in"])

    def test_unterminated_helper_needs_a_sequence(self):
        with self.assertRaises(ValueError):
            unterminated_interfaces("primary-power-in")

    def test_real_hardware_fraction_needs_a_non_empty_sequence(self):
        with self.assertRaises(ValueError):
            real_hardware_fraction([])

    def test_gate_token_needs_a_sequence(self):
        with self.assertRaises(ValueError):
            termination_readiness("no findings")

    def test_gate_token_reflects_the_finding_list(self):
        self.assertEqual(termination_readiness([]), "ready-for-measurement")
        self.assertEqual(termination_readiness(["one"]), "hold-terminations")

    def test_named_tolerance_is_far_below_any_engineering_limit(self):
        self.assertLess(TERM_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
