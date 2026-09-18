"""Contract tests for the clause 7.3.3 MMIC schematic review item logic."""

import copy
import unittest

from q6012_schematic_review_item_logic import (
    COMPARISON_TOLERANCE,
    bias_operating_point,
    check_bias_arrangement,
    check_connectivity,
    check_device_sizing,
    review_device,
    review_schematic,
    total_gate_periphery_mm,
)

# Representative foundry scalable-model window for a power pHEMT process.
MODEL_LIMITS = {
    "unit_gate_width_um": (25.0, 125.0),
    "finger_count": (2, 16),
    "total_periphery_mm": (0.05, 2.0),
}

# Class-AB bias policy: 0.8 derating on a 12 V rated drain, 100-250 mA/mm
# quiescent window, 2000 mW/mm thermal ceiling.
BIAS_POLICY = {
    "max_drain_voltage_v": 12.0,
    "derating_factor": 0.8,
    "current_density_window_ma_per_mm": (100.0, 250.0),
    "max_dissipation_mw_per_mm": 2000.0,
}

DEVICE = {
    "reference": "Q1",
    "unit_gate_width_um": 75.0,
    "finger_count": 8,
    "supply_v": 8.0,
    "feed_resistance_ohm": 2.0,
    "drain_current_ma": 120.0,
    "terminals": ["gate", "drain", "source"],
}

NETS = [
    {"name": "rf_in", "kind": "signal", "connections": ["P1.a", "Q1.gate"]},
    {"name": "rf_out", "kind": "signal", "connections": ["Q1.drain", "P2.a"]},
    {"name": "vdd", "kind": "bias", "connections": ["Q1.drain", "L1.a"], "decoupled": True},
    {"name": "gnd", "kind": "ground", "connections": ["Q1.source", "P1.b", "P2.b"]},
]


def package(**overrides):
    """Return a clean schematic package with the given overrides applied."""
    base = {
        "devices": [copy.deepcopy(DEVICE)],
        "nets": copy.deepcopy(NETS),
        "model_limits": copy.deepcopy(MODEL_LIMITS),
        "bias_policy": copy.deepcopy(BIAS_POLICY),
    }
    base.update(copy.deepcopy(overrides))
    return base


class TotalGatePeripheryTests(unittest.TestCase):
    def test_periphery_converts_microns_to_millimetres(self):
        self.assertAlmostEqual(total_gate_periphery_mm(75.0, 8), 0.6, places=9)

    def test_periphery_scales_with_finger_count(self):
        single = total_gate_periphery_mm(50.0, 1)
        quad = total_gate_periphery_mm(50.0, 4)
        self.assertAlmostEqual(quad, 4.0 * single, places=9)

    def test_zero_finger_count_rejected(self):
        with self.assertRaises(ValueError):
            total_gate_periphery_mm(75.0, 0)

    def test_fractional_finger_count_rejected(self):
        with self.assertRaises(ValueError):
            total_gate_periphery_mm(75.0, 8.5)

    def test_boolean_finger_count_rejected(self):
        with self.assertRaises(ValueError):
            total_gate_periphery_mm(75.0, True)

    def test_non_positive_width_rejected(self):
        with self.assertRaises(ValueError):
            total_gate_periphery_mm(0.0, 8)


class DeviceSizingTests(unittest.TestCase):
    def test_in_window_device_is_gradeable(self):
        record = check_device_sizing(DEVICE, MODEL_LIMITS)
        self.assertTrue(record["sizing_gradeable"])
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["total_periphery_mm"], 0.6, places=9)

    def test_width_above_window_is_a_finding(self):
        device = dict(DEVICE, unit_gate_width_um=200.0)
        record = check_device_sizing(device, MODEL_LIMITS)
        self.assertFalse(record["sizing_gradeable"])
        self.assertTrue(any("unit gate width" in item for item in record["findings"]))

    def test_finger_count_above_window_is_a_finding(self):
        device = dict(DEVICE, finger_count=24, unit_gate_width_um=25.0)
        record = check_device_sizing(device, MODEL_LIMITS)
        self.assertTrue(any("finger count" in item for item in record["findings"]))

    def test_periphery_above_window_is_a_finding_even_with_legal_parts(self):
        device = dict(DEVICE, unit_gate_width_um=125.0, finger_count=16)
        record = check_device_sizing(device, MODEL_LIMITS)
        self.assertAlmostEqual(record["total_periphery_mm"], 2.0, places=9)
        self.assertTrue(record["sizing_gradeable"])

    def test_value_landing_exactly_on_a_bound_counts_as_inside(self):
        device = dict(DEVICE, unit_gate_width_um=25.0, finger_count=2)
        record = check_device_sizing(device, MODEL_LIMITS)
        self.assertAlmostEqual(record["total_periphery_mm"], 0.05, places=9)
        self.assertTrue(record["sizing_gradeable"])

    def test_missing_reference_rejected(self):
        device = dict(DEVICE)
        device.pop("reference")
        with self.assertRaises(ValueError):
            check_device_sizing(device, MODEL_LIMITS)

    def test_inverted_model_bounds_rejected(self):
        limits = dict(MODEL_LIMITS, unit_gate_width_um=(125.0, 25.0))
        with self.assertRaises(ValueError):
            check_device_sizing(DEVICE, limits)

    def test_non_integer_finger_bound_rejected(self):
        limits = dict(MODEL_LIMITS, finger_count=(2.0, 16))
        with self.assertRaises(ValueError):
            check_device_sizing(DEVICE, limits)


class BiasOperatingPointTests(unittest.TestCase):
    def test_feed_resistance_drops_the_rail(self):
        point = bias_operating_point(8.0, 2.0, 120.0, 0.6)
        self.assertAlmostEqual(point["feed_drop_v"], 0.24, places=9)
        self.assertAlmostEqual(point["drain_voltage_v"], 7.76, places=9)

    def test_current_density_is_per_millimetre_of_periphery(self):
        point = bias_operating_point(8.0, 0.0, 120.0, 0.6)
        self.assertAlmostEqual(point["current_density_ma_per_mm"], 200.0, places=9)

    def test_dissipation_density_uses_the_dropped_drain_voltage(self):
        point = bias_operating_point(8.0, 2.0, 120.0, 0.6)
        self.assertAlmostEqual(point["dissipation_mw"], 7.76 * 120.0, places=9)
        self.assertAlmostEqual(
            point["dissipation_density_mw_per_mm"], 7.76 * 120.0 / 0.6, places=9
        )

    def test_zero_feed_resistance_is_allowed(self):
        point = bias_operating_point(8.0, 0.0, 120.0, 0.6)
        self.assertAlmostEqual(point["drain_voltage_v"], 8.0, places=9)

    def test_negative_feed_resistance_rejected(self):
        with self.assertRaises(ValueError):
            bias_operating_point(8.0, -1.0, 120.0, 0.6)

    def test_feed_that_collapses_the_drain_node_rejected(self):
        with self.assertRaises(ValueError):
            bias_operating_point(1.0, 20.0, 120.0, 0.6)

    def test_non_numeric_supply_rejected(self):
        with self.assertRaises(ValueError):
            bias_operating_point("8", 2.0, 120.0, 0.6)


class BiasArrangementTests(unittest.TestCase):
    def test_compliant_point_raises_no_finding(self):
        point = bias_operating_point(8.0, 2.0, 120.0, 0.6)
        verdict = check_bias_arrangement(point, BIAS_POLICY, "Q1")
        self.assertTrue(verdict["bias_acceptable"])
        self.assertAlmostEqual(verdict["derated_drain_voltage_v"], 9.6, places=9)

    def test_drain_voltage_above_derated_rating_is_a_finding(self):
        point = bias_operating_point(11.0, 2.0, 120.0, 0.6)
        verdict = check_bias_arrangement(point, BIAS_POLICY, "Q1")
        self.assertFalse(verdict["bias_acceptable"])
        self.assertTrue(any("derated maximum" in item for item in verdict["findings"]))

    def test_drain_voltage_exactly_on_the_derated_limit_passes(self):
        point = bias_operating_point(9.6, 0.0, 120.0, 0.6)
        verdict = check_bias_arrangement(point, BIAS_POLICY, "Q1")
        self.assertAlmostEqual(
            point["drain_voltage_v"], verdict["derated_drain_voltage_v"], places=9
        )
        self.assertTrue(verdict["bias_acceptable"])

    def test_current_density_below_the_class_window_is_a_finding(self):
        point = bias_operating_point(8.0, 2.0, 30.0, 0.6)
        verdict = check_bias_arrangement(point, BIAS_POLICY, "Q1")
        self.assertTrue(any("current density" in item for item in verdict["findings"]))

    def test_dissipation_density_above_the_thermal_limit_is_a_finding(self):
        policy = dict(BIAS_POLICY, max_dissipation_mw_per_mm=500.0)
        point = bias_operating_point(8.0, 2.0, 120.0, 0.6)
        verdict = check_bias_arrangement(point, policy, "Q1")
        self.assertTrue(any("dissipation density" in item for item in verdict["findings"]))

    def test_derating_factor_above_one_rejected(self):
        policy = dict(BIAS_POLICY, derating_factor=1.2)
        point = bias_operating_point(8.0, 2.0, 120.0, 0.6)
        with self.assertRaises(ValueError):
            check_bias_arrangement(point, policy, "Q1")

    def test_point_without_required_keys_rejected(self):
        with self.assertRaises(ValueError):
            check_bias_arrangement({"drain_voltage_v": 8.0}, BIAS_POLICY, "Q1")

    def test_comparison_tolerance_is_small_and_positive(self):
        self.assertGreater(COMPARISON_TOLERANCE, 0.0)
        self.assertLess(COMPARISON_TOLERANCE, 1e-6)


class ConnectivityTests(unittest.TestCase):
    def test_clean_diagram_has_no_findings(self):
        verdict = check_connectivity([DEVICE], NETS)
        self.assertTrue(verdict["connectivity_clean"])
        self.assertEqual(verdict["net_count"], 4)

    def test_terminal_absent_from_every_net_is_a_finding(self):
        nets = [net for net in NETS if net["name"] != "gnd"]
        nets.append({"name": "gnd", "kind": "ground", "connections": ["P1.b", "P2.b"]})
        verdict = check_connectivity([DEVICE], nets)
        self.assertFalse(verdict["connectivity_clean"])
        self.assertTrue(any("Q1.source" in item for item in verdict["findings"]))

    def test_single_connection_net_is_a_finding(self):
        nets = copy.deepcopy(NETS)
        nets.append({"name": "stub", "kind": "signal", "connections": ["Q1.gate"]})
        verdict = check_connectivity([DEVICE], nets)
        self.assertTrue(any("goes nowhere" in item for item in verdict["findings"]))

    def test_undecoupled_bias_net_is_a_finding(self):
        nets = copy.deepcopy(NETS)
        for net in nets:
            if net["name"] == "vdd":
                net["decoupled"] = False
        verdict = check_connectivity([DEVICE], nets)
        self.assertTrue(any("decoupling" in item for item in verdict["findings"]))

    def test_bias_net_without_a_decoupling_declaration_rejected(self):
        nets = copy.deepcopy(NETS)
        for net in nets:
            if net["name"] == "vdd":
                net.pop("decoupled")
        with self.assertRaises(ValueError):
            check_connectivity([DEVICE], nets)

    def test_duplicate_net_name_rejected(self):
        nets = copy.deepcopy(NETS) + [copy.deepcopy(NETS[0])]
        with self.assertRaises(ValueError):
            check_connectivity([DEVICE], nets)

    def test_duplicate_device_reference_rejected(self):
        with self.assertRaises(ValueError):
            check_connectivity([DEVICE, dict(DEVICE)], NETS)

    def test_unknown_net_kind_rejected(self):
        nets = copy.deepcopy(NETS)
        nets[0]["kind"] = "power-ish"
        with self.assertRaises(ValueError):
            check_connectivity([DEVICE], nets)

    def test_empty_net_list_rejected(self):
        with self.assertRaises(ValueError):
            check_connectivity([DEVICE], [])


class ReviewSchematicTests(unittest.TestCase):
    def test_clean_package_passes_the_item(self):
        result = review_schematic(package())
        self.assertTrue(result["item_passed"])
        self.assertEqual(result["findings"], [])

    def test_worst_dissipation_density_is_reported(self):
        result = review_schematic(package())
        self.assertAlmostEqual(
            result["worst_dissipation_density_mw_per_mm"], 7.76 * 120.0 / 0.6, places=9
        )

    def test_sizing_and_bias_findings_are_both_collected(self):
        device = dict(DEVICE, unit_gate_width_um=200.0, supply_v=11.0)
        result = review_schematic(package(devices=[device]))
        self.assertFalse(result["item_passed"])
        self.assertTrue(any("unit gate width" in item for item in result["findings"]))
        self.assertTrue(any("derated maximum" in item for item in result["findings"]))

    def test_connectivity_finding_fails_an_otherwise_clean_package(self):
        nets = copy.deepcopy(NETS)
        for net in nets:
            if net["name"] == "vdd":
                net["decoupled"] = False
        result = review_schematic(package(nets=nets))
        self.assertFalse(result["item_passed"])

    def test_review_device_reports_both_sub_records(self):
        record = review_device(DEVICE, MODEL_LIMITS, BIAS_POLICY)
        self.assertTrue(record["acceptable"])
        self.assertIn("sizing", record)
        self.assertIn("operating_point", record)

    def test_missing_package_key_rejected(self):
        broken = package()
        broken.pop("bias_policy")
        with self.assertRaises(ValueError):
            review_schematic(broken)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            review_schematic(["devices"])

    def test_empty_device_list_rejected(self):
        with self.assertRaises(ValueError):
            review_schematic(package(devices=[]))


if __name__ == "__main__":
    unittest.main()
