"""Contract tests for the ECSS-E-ST-31 cryogenic-range design logic."""

import unittest

from e31_cryogenic_range_design_requirements_logic import (
    CONTROL_ELECTRONIC,
    CONTROL_MECHANICAL,
    CRYOGENIC_SCATTER_FACTOR,
    CRYOGENIC_UPPER_K,
    assess_cryogenic_item,
    assess_gradient,
    assess_sensor,
    assess_thermostat,
    conduction_heat_leak_band,
    property_scatter_band,
    size_cooler,
    validate_operating_range,
)

RANGE = validate_operating_range(80.0, 150.0)

SENSOR = {
    "usable_min_k": 20.0,
    "usable_max_k": 320.0,
    "required_margin_k": 10.0,
    "sensitivity_v_per_k": 0.004,
    "min_sensitivity_v_per_k": 0.001,
}

ELECTRONIC = {"kind": CONTROL_ELECTRONIC, "deadband_k": 0.5}
MECHANICAL = {
    "kind": CONTROL_MECHANICAL,
    "deadband_k": 2.0,
    "qualification_floor_k": 220.0,
}


def spec(**over):
    base = {
        "minimum_k": 80.0,
        "maximum_k": 150.0,
        "sensor": dict(SENSOR),
        "controller": dict(ELECTRONIC),
        "setpoint_k": 100.0,
        "allowable_band_k": 1.0,
        "gradient_k": 0.5,
        "allowable_gradient_k": 2.0,
        "conductivity_w_mk": 10.0,
        "conductivity_scatter_fraction": 0.1,
        "area_m2": 1.0e-4,
        "length_m": 0.2,
        "delta_t_k": 200.0,
    }
    base.update(over)
    return base


class OperatingRangeTests(unittest.TestCase):
    def test_cold_range_is_admitted(self):
        rng = validate_operating_range(80.0, 150.0)
        self.assertAlmostEqual(rng["minimum_k"], 80.0, places=9)

    def test_range_entirely_above_the_boundary_is_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_range(250.0, 300.0)

    def test_range_starting_exactly_on_the_boundary_is_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_range(CRYOGENIC_UPPER_K, 300.0)

    def test_range_straddling_the_boundary_is_admitted(self):
        rng = validate_operating_range(150.0, 300.0)
        self.assertAlmostEqual(rng["maximum_k"], 300.0, places=9)

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_range(150.0, 80.0)

    def test_non_positive_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_range(0.0, 150.0)


class SensorTests(unittest.TestCase):
    def test_wide_sensitive_sensor_is_acceptable(self):
        result = assess_sensor(dict(SENSOR), RANGE)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_sensor_span_exactly_meeting_the_margin_is_acceptable(self):
        sensor = dict(SENSOR, usable_min_k=70.0, usable_max_k=160.0)
        result = assess_sensor(sensor, RANGE)
        self.assertTrue(result["covers_range"])

    def test_sensor_too_warm_at_the_cold_end_is_a_finding(self):
        sensor = dict(SENSOR, usable_min_k=120.0)
        result = assess_sensor(sensor, RANGE)
        self.assertFalse(result["covers_range"])
        self.assertFalse(result["acceptable"])

    def test_in_range_but_insensitive_sensor_is_rejected(self):
        sensor = dict(SENSOR, sensitivity_v_per_k=0.0001)
        result = assess_sensor(sensor, RANGE)
        self.assertTrue(result["covers_range"])
        self.assertFalse(result["resolves_cold_end"])
        self.assertFalse(result["acceptable"])

    def test_sensitivity_exactly_on_the_floor_resolves(self):
        sensor = dict(SENSOR, sensitivity_v_per_k=0.001, min_sensitivity_v_per_k=0.001)
        self.assertTrue(assess_sensor(sensor, RANGE)["resolves_cold_end"])

    def test_inverted_sensor_span_rejected(self):
        with self.assertRaises(ValueError):
            assess_sensor(dict(SENSOR, usable_min_k=400.0), RANGE)

    def test_non_mapping_sensor_rejected(self):
        with self.assertRaises(ValueError):
            assess_sensor(["usable_min_k"], RANGE)


class ThermostatTests(unittest.TestCase):
    def test_electronic_controller_keeps_its_deadband(self):
        result = assess_thermostat(dict(ELECTRONIC), 100.0, 1.0)
        self.assertAlmostEqual(result["growth_factor"], 1.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_mechanical_thermostat_above_its_floor_keeps_its_deadband(self):
        result = assess_thermostat(dict(MECHANICAL), 250.0, 3.0)
        self.assertAlmostEqual(result["effective_deadband_k"], 2.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_mechanical_thermostat_in_the_cold_widens_its_deadband(self):
        result = assess_thermostat(dict(MECHANICAL), 200.0, 10.0)
        self.assertAlmostEqual(result["growth_factor"], 2.0, places=9)
        self.assertAlmostEqual(result["effective_deadband_k"], 4.0, places=9)

    def test_widened_deadband_forces_an_electronic_controller(self):
        result = assess_thermostat(dict(MECHANICAL), 100.0, 5.0)
        self.assertTrue(result["electronic_controller_required"])
        self.assertFalse(result["acceptable"])

    def test_deadband_growth_is_capped(self):
        result = assess_thermostat(dict(MECHANICAL), 4.0, 100.0)
        self.assertAlmostEqual(result["growth_factor"], 6.0, places=9)

    def test_deadband_exactly_on_the_allowable_band_holds(self):
        result = assess_thermostat(dict(ELECTRONIC), 100.0, 0.5)
        self.assertAlmostEqual(
            result["effective_deadband_k"], result["allowable_band_k"], places=9
        )
        self.assertTrue(result["acceptable"])

    def test_unknown_controller_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermostat({"kind": "wax-actuator", "deadband_k": 1.0}, 100.0, 2.0)

    def test_mechanical_controller_without_a_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermostat({"kind": CONTROL_MECHANICAL, "deadband_k": 2.0}, 100.0, 5.0)


class GradientTests(unittest.TestCase):
    def test_gradient_inside_its_allowable_is_acceptable(self):
        result = assess_gradient(0.5, 2.0)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["margin_k"], 1.5, places=9)

    def test_gradient_exactly_on_its_allowable_is_acceptable(self):
        result = assess_gradient(2.0, 2.0)
        self.assertAlmostEqual(result["margin_k"], 0.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_gradient_above_its_allowable_is_a_finding(self):
        result = assess_gradient(3.0, 2.0)
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 1)

    def test_negative_gradient_rejected(self):
        with self.assertRaises(ValueError):
            assess_gradient(-1.0, 2.0)


class ScatterAndLeakTests(unittest.TestCase):
    def test_warm_property_keeps_its_declared_scatter(self):
        band = property_scatter_band(10.0, 0.1, 300.0)
        self.assertAlmostEqual(band["effective_scatter"], 0.1, places=9)
        self.assertAlmostEqual(band["high"], 11.0, places=9)

    def test_cold_property_scatter_is_widened(self):
        band = property_scatter_band(10.0, 0.1, 80.0)
        self.assertAlmostEqual(
            band["effective_scatter"], 0.1 * CRYOGENIC_SCATTER_FACTOR, places=9
        )
        self.assertAlmostEqual(band["low"], 7.5, places=9)
        self.assertAlmostEqual(band["high"], 12.5, places=9)

    def test_widened_scatter_is_kept_below_unity(self):
        band = property_scatter_band(10.0, 0.9, 80.0)
        self.assertLess(band["effective_scatter"], 1.0)
        self.assertGreater(band["low"], 0.0)

    def test_scatter_of_one_rejected(self):
        with self.assertRaises(ValueError):
            property_scatter_band(10.0, 1.0, 80.0)

    def test_heat_leak_band_follows_the_conductivity_band(self):
        band = property_scatter_band(10.0, 0.1, 80.0)
        leak = conduction_heat_leak_band(band, 1.0e-4, 0.2, 200.0)
        self.assertAlmostEqual(leak["low_w"], 0.75, places=9)
        self.assertAlmostEqual(leak["high_w"], 1.25, places=9)

    def test_zero_delta_t_gives_no_heat_leak(self):
        band = property_scatter_band(10.0, 0.1, 80.0)
        leak = conduction_heat_leak_band(band, 1.0e-4, 0.2, 0.0)
        self.assertAlmostEqual(leak["high_w"], 0.0, places=9)

    def test_inverted_conductivity_band_rejected(self):
        with self.assertRaises(ValueError):
            conduction_heat_leak_band({"low": 12.0, "high": 8.0}, 1.0e-4, 0.2, 200.0)

    def test_cooler_is_sized_on_the_high_end_not_the_nominal(self):
        band = property_scatter_band(10.0, 0.1, 80.0)
        leak = conduction_heat_leak_band(band, 1.0e-4, 0.2, 200.0)
        self.assertAlmostEqual(size_cooler(leak), 1.25, places=9)

    def test_parasitic_load_and_contingency_add_to_the_capacity(self):
        capacity = size_cooler({"high_w": 1.0}, parasitic_w=0.5, contingency_fraction=0.2)
        self.assertAlmostEqual(capacity, 1.8, places=9)

    def test_contingency_of_one_rejected(self):
        with self.assertRaises(ValueError):
            size_cooler({"high_w": 1.0}, contingency_fraction=1.0)


class AssessCryogenicItemTests(unittest.TestCase):
    def test_well_designed_item_passes_every_constraint(self):
        result = assess_cryogenic_item(spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["failed_constraints"], [])
        self.assertEqual(result["findings"], [])

    def test_cooler_capacity_uses_the_widened_conductivity(self):
        result = assess_cryogenic_item(spec())
        self.assertAlmostEqual(result["required_cooler_capacity_w"], 1.25, places=9)
        self.assertAlmostEqual(result["heat_leak_band_w"]["low_w"], 0.75, places=9)

    def test_mechanical_thermostat_in_the_cold_fails_only_the_controller(self):
        result = assess_cryogenic_item(spec(controller=dict(MECHANICAL)))
        self.assertEqual(result["failed_constraints"], ["controller"])
        self.assertTrue(result["constraints"]["sensor"])

    def test_insensitive_sensor_fails_only_the_sensor(self):
        result = assess_cryogenic_item(
            spec(sensor=dict(SENSOR, sensitivity_v_per_k=1e-5))
        )
        self.assertEqual(result["failed_constraints"], ["sensor"])

    def test_gradient_breach_fails_only_the_gradient(self):
        result = assess_cryogenic_item(spec(gradient_k=5.0))
        self.assertEqual(result["failed_constraints"], ["gradient"])

    def test_item_above_the_cryogenic_boundary_is_refused(self):
        with self.assertRaises(ValueError):
            assess_cryogenic_item(spec(minimum_k=250.0, maximum_k=300.0))

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["allowable_gradient_k"]
        with self.assertRaises(ValueError):
            assess_cryogenic_item(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cryogenic_item(["minimum_k"])


if __name__ == "__main__":
    unittest.main()
