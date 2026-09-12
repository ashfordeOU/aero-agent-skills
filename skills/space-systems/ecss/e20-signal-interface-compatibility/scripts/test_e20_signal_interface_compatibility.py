#!/usr/bin/env python3
"""Gate 3 contract test for e20-signal-interface-compatibility.

stdlib unittest, offline, deterministic. Run:
    python3 test_e20_signal_interface_compatibility.py
"""

import unittest

from e20_signal_interface_compatibility_logic import (
    assess_interface_set,
    assess_signal_interface,
    categorize_signal_interface,
    check_impedance_relationship,
    divider_voltage,
    loop_current_a,
    noise_margins,
)


def discrete_interface(**overrides):
    """A nominally compatible bi-level discrete interface."""
    iface = {
        "id": "IF-DISC-01",
        "kind": "bi-level-discrete",
        "source": {
            "open_circuit_high_v": 5.0,
            "driven_low_v": 0.2,
            "output_impedance_ohm": 100.0,
            "drive_capability_a": 0.05,
        },
        "load": {
            "input_high_threshold_v": 2.4,
            "input_low_threshold_v": 0.8,
            "input_impedance_ohm": 10000.0,
        },
    }
    for key, value in overrides.items():
        if key in ("source", "load"):
            iface[key].update(value)
        else:
            iface[key] = value
    return iface


def serial_interface(**overrides):
    """A nominally compatible serial data line interface."""
    iface = {
        "id": "IF-SER-01",
        "kind": "serial-data-line",
        "source": {
            "open_circuit_high_v": 2.5,
            "driven_low_v": 0.3,
            "output_impedance_ohm": 50.0,
            "drive_capability_a": 0.05,
        },
        "load": {
            "input_high_threshold_v": 1.0,
            "input_low_threshold_v": 0.9,
            "input_impedance_ohm": 52.0,
        },
    }
    for key, value in overrides.items():
        if key in ("source", "load"):
            iface[key].update(value)
        else:
            iface[key] = value
    return iface


class CategorizeTests(unittest.TestCase):
    def test_canonical_names_round_trip(self):
        for name in (
            "bi-level-discrete",
            "analog-measurement",
            "serial-data-line",
            "pulse-command",
        ):
            self.assertEqual(categorize_signal_interface(name), name)

    def test_aliases_and_whitespace_normalise(self):
        self.assertEqual(categorize_signal_interface("  Discrete "), "bi-level-discrete")
        self.assertEqual(categorize_signal_interface("analog"), "analog-measurement")
        self.assertEqual(categorize_signal_interface("data_line"), "serial-data-line")
        self.assertEqual(categorize_signal_interface("PULSE"), "pulse-command")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_signal_interface("optical-fibre-link")

    def test_empty_and_non_string_kind_raise(self):
        with self.assertRaises(ValueError):
            categorize_signal_interface("   ")
        with self.assertRaises(ValueError):
            categorize_signal_interface(7)


class DividerAndCurrentTests(unittest.TestCase):
    def test_divider_voltage_applies_the_load_ratio(self):
        self.assertAlmostEqual(divider_voltage(5.0, 100.0, 10000.0), 4.9504950, places=6)

    def test_zero_source_impedance_passes_the_full_level(self):
        self.assertAlmostEqual(divider_voltage(3.3, 0.0, 1000.0), 3.3, places=9)

    def test_divider_rejects_bad_impedances(self):
        with self.assertRaises(ValueError):
            divider_voltage(5.0, -1.0, 1000.0)
        with self.assertRaises(ValueError):
            divider_voltage(5.0, 100.0, 0.0)

    def test_divider_rejects_non_numeric_and_bool(self):
        with self.assertRaises(ValueError):
            divider_voltage("5.0", 100.0, 1000.0)
        with self.assertRaises(ValueError):
            divider_voltage(True, 100.0, 1000.0)

    def test_loop_current_uses_the_series_sum(self):
        self.assertAlmostEqual(loop_current_a(5.0, 1.0, 9.0), 0.5, places=9)

    def test_loop_current_rejects_bad_impedances(self):
        with self.assertRaises(ValueError):
            loop_current_a(5.0, -0.1, 10.0)
        with self.assertRaises(ValueError):
            loop_current_a(5.0, 10.0, -10.0)


class NoiseMarginTests(unittest.TestCase):
    def test_margins_are_the_threshold_differences(self):
        margins = noise_margins(4.95, 0.2, 2.4, 0.8)
        self.assertAlmostEqual(margins["high_margin_v"], 2.55, places=6)
        self.assertAlmostEqual(margins["low_margin_v"], 0.6, places=6)

    def test_negative_high_margin_is_reported_not_clamped(self):
        margins = noise_margins(2.0, 0.2, 2.4, 0.8)
        self.assertAlmostEqual(margins["high_margin_v"], -0.4, places=6)

    def test_inverted_levels_and_thresholds_raise(self):
        with self.assertRaises(ValueError):
            noise_margins(0.2, 4.95, 2.4, 0.8)
        with self.assertRaises(ValueError):
            noise_margins(4.95, 0.2, 0.8, 2.4)


class ImpedanceRelationshipTests(unittest.TestCase):
    def test_level_driven_ratio_boundary_is_inclusive(self):
        result = check_impedance_relationship("bi-level-discrete", 100.0, 1000.0)
        self.assertAlmostEqual(result["ratio"], 10.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_level_driven_ratio_below_minimum_is_flagged(self):
        result = check_impedance_relationship("bi-level-discrete", 100.0, 900.0)
        self.assertEqual(len(result["findings"]), 1)

    def test_analog_demands_a_higher_ratio_than_discrete(self):
        zs, zl = 500.0, 20000.0
        self.assertEqual(check_impedance_relationship("bi-level-discrete", zs, zl)["findings"], [])
        self.assertEqual(len(check_impedance_relationship("analog-measurement", zs, zl)["findings"]), 1)

    def test_serial_line_wants_a_match_not_a_high_impedance(self):
        matched = check_impedance_relationship("serial-data-line", 50.0, 55.0)
        self.assertAlmostEqual(matched["deviation"], 0.10, places=9)
        self.assertEqual(matched["findings"], [])
        open_term = check_impedance_relationship("serial-data-line", 50.0, 10000.0)
        self.assertEqual(len(open_term["findings"]), 1)

    def test_impedance_check_rejects_bad_family_and_values(self):
        with self.assertRaises(ValueError):
            check_impedance_relationship("waveguide", 50.0, 50.0)
        with self.assertRaises(ValueError):
            check_impedance_relationship("bi-level-discrete", 0.0, 50.0)
        with self.assertRaises(ValueError):
            check_impedance_relationship("bi-level-discrete", 50.0, 0.0)


class AssessInterfaceTests(unittest.TestCase):
    def test_nominal_discrete_interface_is_compatible(self):
        result = assess_signal_interface(discrete_interface())
        self.assertTrue(result["compatible"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["family"], "bi-level-discrete")
        self.assertAlmostEqual(result["loaded_high_v"], 4.9504950, places=6)
        self.assertAlmostEqual(result["low_margin_v"], 0.6, places=6)
        self.assertAlmostEqual(result["loop_current_a"], 0.00049504950, places=10)

    def test_nominal_serial_interface_is_compatible(self):
        result = assess_signal_interface(serial_interface())
        self.assertTrue(result["compatible"])
        self.assertAlmostEqual(result["loaded_high_v"], 1.2745098, places=6)

    def test_high_source_impedance_collapses_the_loaded_level(self):
        result = assess_signal_interface(
            discrete_interface(source={"output_impedance_ohm": 20000.0})
        )
        self.assertFalse(result["compatible"])
        self.assertAlmostEqual(result["loaded_high_v"], 1.6666667, places=6)
        self.assertTrue(any("high_margin_v" in f for f in result["findings"]))

    def test_margin_exactly_at_the_floor_passes(self):
        result = assess_signal_interface(discrete_interface(source={"driven_low_v": 0.4}))
        self.assertAlmostEqual(result["low_margin_v"], 0.4, places=9)
        self.assertTrue(result["compatible"])

    def test_margin_just_under_the_floor_is_flagged(self):
        result = assess_signal_interface(discrete_interface(source={"driven_low_v": 0.45}))
        self.assertFalse(result["compatible"])
        self.assertTrue(any("low_margin_v" in f for f in result["findings"]))

    def test_drive_capability_shortfall_is_flagged_even_when_levels_close(self):
        result = assess_signal_interface(
            discrete_interface(
                source={"output_impedance_ohm": 1.0, "drive_capability_a": 0.1},
                load={"input_impedance_ohm": 10.0},
            )
        )
        self.assertFalse(result["compatible"])
        self.assertAlmostEqual(result["loop_current_a"], 0.4545454, places=6)
        self.assertTrue(any("drive capability" in f for f in result["findings"]))

    def test_structural_errors_raise(self):
        with self.assertRaises(ValueError):
            assess_signal_interface(["not", "a", "mapping"])
        broken = discrete_interface()
        del broken["load"]
        with self.assertRaises(ValueError):
            assess_signal_interface(broken)
        no_keys = discrete_interface()
        del no_keys["source"]["drive_capability_a"]
        with self.assertRaises(ValueError):
            assess_signal_interface(no_keys)
        not_mapping = discrete_interface()
        not_mapping["load"] = 42
        with self.assertRaises(ValueError):
            assess_signal_interface(not_mapping)

    def test_non_positive_drive_capability_raises(self):
        with self.assertRaises(ValueError):
            assess_signal_interface(discrete_interface(source={"drive_capability_a": 0.0}))


class AssessSetTests(unittest.TestCase):
    def test_mixed_set_reports_only_the_incompatible_ids(self):
        bad = discrete_interface(id="IF-DISC-02", source={"output_impedance_ohm": 20000.0})
        summary = assess_interface_set([discrete_interface(), serial_interface(), bad])
        self.assertEqual(summary["assessed"], 3)
        self.assertEqual(summary["incompatible"], ["IF-DISC-02"])
        self.assertFalse(summary["all_compatible"])

    def test_all_compatible_set_is_clean(self):
        summary = assess_interface_set([discrete_interface(), serial_interface()])
        self.assertTrue(summary["all_compatible"])
        self.assertEqual(summary["incompatible"], [])

    def test_set_level_errors_raise(self):
        with self.assertRaises(ValueError):
            assess_interface_set({})
        with self.assertRaises(ValueError):
            assess_interface_set([])
        with self.assertRaises(ValueError):
            assess_interface_set([discrete_interface(), discrete_interface()])


if __name__ == "__main__":
    unittest.main()
