"""Contract test for the e3311 low/high-voltage initiator leaf (stdlib unittest)."""

import unittest

from e3311_low_high_voltage_initiators_logic import (
    DEFAULT_INITIATOR_POLICY,
    ESD_PATHS,
    HIGH_VOLTAGE_PROPERTIES,
    INITIATOR_CATEGORIES,
    LOW_VOLTAGE_PROPERTIES,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_esd_withstand,
    assess_high_voltage_initiator,
    assess_initiator,
    assess_initiator_population,
    assess_insulation_resistance,
    assess_low_voltage_initiator,
    category_properties,
    fire_separation_ratio,
    stored_energy_j,
    validate_initiator_policy,
)


def esd(**kw):
    block = {"pin-to-pin": 0.2, "pin-to-case": 0.2}
    block.update(kw)
    return block


def low_device(**kw):
    properties = {
        "no-fire-current": 1.0,
        "all-fire-current": 3.5,
        "bridge-resistance": 1.05,
        "esd-withstand": esd(),
        "insulation-resistance": 1.0e7,
    }
    properties.update(kw)
    return {"category": "low-voltage", "properties": properties}


def high_device(**kw):
    properties = {
        "no-fire-voltage": 1000.0,
        "no-fire-energy": 2.0e-3,
        "all-fire-energy": 4.0e-3,
        "firing-set": {"capacitance_f": 1.0e-6, "voltage_v": 2000.0},
        "esd-withstand": esd(),
        "insulation-resistance": 1.0e7,
    }
    properties.update(kw)
    return {"category": "high-voltage", "properties": properties}


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_initiator_policy(DEFAULT_INITIATOR_POLICY),
            DEFAULT_INITIATOR_POLICY,
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_initiator_policy(["min_no_fire_current_a", 1.0])

    def test_a_separation_ratio_of_one_raises(self):
        policy = dict(DEFAULT_INITIATOR_POLICY, min_fire_separation_ratio=1.0)
        with self.assertRaises(ValueError):
            validate_initiator_policy(policy)

    def test_an_inverted_resistance_band_raises(self):
        policy = dict(DEFAULT_INITIATOR_POLICY, bridge_resistance_band_ohm=(1.3, 0.9))
        with self.assertRaises(ValueError):
            validate_initiator_policy(policy)

    def test_a_firing_margin_below_unity_raises(self):
        policy = dict(DEFAULT_INITIATOR_POLICY, min_firing_energy_margin=0.8)
        with self.assertRaises(ValueError):
            validate_initiator_policy(policy)


class TestArithmetic(unittest.TestCase):
    def test_stored_energy_is_half_c_v_squared(self):
        self.assertAlmostEqual(stored_energy_j(1.0e-6, 2000.0), 2.0, places=12)

    def test_stored_energy_rejects_zero_capacitance(self):
        with self.assertRaises(ValueError):
            stored_energy_j(0.0, 2000.0)

    def test_separation_ratio_is_the_quotient(self):
        self.assertAlmostEqual(fire_separation_ratio(3.5, 1.0), 3.5, places=12)

    def test_separation_ratio_rejects_a_zero_no_fire(self):
        with self.assertRaises(ValueError):
            fire_separation_ratio(3.5, 0.0)

    def test_separation_ratio_rejects_a_boolean(self):
        with self.assertRaises(ValueError):
            fire_separation_ratio(True, 1.0)


class TestCategoryTables(unittest.TestCase):
    def test_the_low_voltage_table_names_currents_and_resistance(self):
        self.assertEqual(
            sorted(category_properties("low-voltage")), sorted(LOW_VOLTAGE_PROPERTIES)
        )

    def test_the_high_voltage_table_names_voltage_and_energy(self):
        self.assertEqual(
            sorted(category_properties("high-voltage")), sorted(HIGH_VOLTAGE_PROPERTIES)
        )

    def test_the_two_tables_differ(self):
        self.assertNotEqual(
            set(category_properties("low-voltage")),
            set(category_properties("high-voltage")),
        )

    def test_every_category_resolves(self):
        for category in INITIATOR_CATEGORIES:
            self.assertTrue(category_properties(category))

    def test_an_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            category_properties("laser")


class TestEsdAndInsulation(unittest.TestCase):
    def test_both_paths_are_graded(self):
        result = assess_esd_withstand(esd())
        self.assertEqual(sorted(result["paths"]), sorted(ESD_PATHS))
        self.assertTrue(result["compliant"])

    def test_a_withstand_exactly_on_the_requirement_passes(self):
        result = assess_esd_withstand(
            esd(**{"pin-to-pin": 0.15625, "pin-to-case": 0.15625})
        )
        self.assertAlmostEqual(
            result["paths"]["pin-to-pin"]["withstand_energy_j"], 0.15625, places=12
        )
        self.assertTrue(result["compliant"])

    def test_a_weak_pin_to_case_path_fails_alone(self):
        result = assess_esd_withstand(esd(**{"pin-to-case": 0.01}))
        self.assertFalse(result["compliant"])
        self.assertTrue(result["paths"]["pin-to-pin"]["compliant"])
        self.assertFalse(result["paths"]["pin-to-case"]["compliant"])

    def test_a_missing_esd_path_raises(self):
        with self.assertRaises(ValueError):
            assess_esd_withstand({"pin-to-pin": 0.2})

    def test_an_unknown_esd_path_raises(self):
        with self.assertRaises(ValueError):
            assess_esd_withstand(esd(**{"pin-to-shield": 0.2}))

    def test_a_healthy_insulation_passes(self):
        self.assertTrue(assess_insulation_resistance(1.0e7)["compliant"])

    def test_a_low_insulation_fails(self):
        self.assertFalse(assess_insulation_resistance(1.0e5)["compliant"])


class TestLowVoltageInitiator(unittest.TestCase):
    def test_a_sound_bridgewire_device_passes(self):
        report = assess_low_voltage_initiator(low_device())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_a_separation_exactly_on_the_ratio_passes(self):
        report = assess_low_voltage_initiator(
            low_device(**{"no-fire-current": 1.0, "all-fire-current": 2.0})
        )
        self.assertAlmostEqual(report["separation_ratio"], 2.0, places=9)
        self.assertTrue(report["compliant"])

    def test_a_thin_separation_fails(self):
        report = assess_low_voltage_initiator(
            low_device(**{"no-fire-current": 1.5, "all-fire-current": 2.0})
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("times the no-fire" in f for f in report["findings"]))

    def test_a_sensitive_device_fails_the_no_fire_floor(self):
        report = assess_low_voltage_initiator(
            low_device(**{"no-fire-current": 0.2, "all-fire-current": 1.0})
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("more sensitive" in f for f in report["findings"]))

    def test_an_all_fire_beyond_the_circuit_fails(self):
        report = assess_low_voltage_initiator(
            low_device(**{"all-fire-current": 9.0})
        )
        self.assertFalse(report["compliant"])

    def test_a_resistance_on_the_band_edge_passes(self):
        report = assess_low_voltage_initiator(low_device(**{"bridge-resistance": 0.9}))
        self.assertAlmostEqual(report["bridge_resistance_ohm"], 0.9, places=9)
        self.assertTrue(report["compliant"])

    def test_a_resistance_outside_the_band_fails(self):
        report = assess_low_voltage_initiator(low_device(**{"bridge-resistance": 2.5}))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("band" in f for f in report["findings"]))

    def test_a_high_voltage_device_cannot_be_graded_here(self):
        with self.assertRaises(ValueError):
            assess_low_voltage_initiator(high_device())

    def test_a_missing_low_voltage_property_raises(self):
        device = low_device()
        del device["properties"]["bridge-resistance"]
        with self.assertRaises(ValueError):
            assess_low_voltage_initiator(device)

    def test_a_high_voltage_property_on_a_low_voltage_device_raises(self):
        device = low_device()
        device["properties"]["all-fire-energy"] = 4.0e-3
        with self.assertRaises(ValueError):
            assess_low_voltage_initiator(device)


class TestHighVoltageInitiator(unittest.TestCase):
    def test_a_sound_exploding_bridge_device_passes(self):
        report = assess_high_voltage_initiator(high_device())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_the_firing_set_energy_comes_from_its_capacitor(self):
        report = assess_high_voltage_initiator(high_device())
        self.assertAlmostEqual(report["delivered_energy_j"], 2.0, places=12)

    def test_a_firing_set_exactly_on_the_required_delivery_passes(self):
        device = high_device(
            **{"firing-set": {"capacitance_f": 1.2e-6, "voltage_v": 100.0}}
        )
        report = assess_high_voltage_initiator(device)
        self.assertAlmostEqual(report["delivered_energy_j"], 6.0e-3, places=12)
        self.assertAlmostEqual(report["required_delivery_j"], 6.0e-3, places=12)
        self.assertTrue(report["compliant"])

    def test_a_weak_firing_set_fails(self):
        device = high_device(
            **{"firing-set": {"capacitance_f": 1.0e-9, "voltage_v": 100.0}}
        )
        report = assess_high_voltage_initiator(device)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("firing set delivers" in f for f in report["findings"]))

    def test_a_low_no_fire_voltage_fails(self):
        report = assess_high_voltage_initiator(high_device(**{"no-fire-voltage": 50.0}))
        self.assertFalse(report["compliant"])

    def test_a_thin_energy_separation_fails(self):
        report = assess_high_voltage_initiator(
            high_device(**{"no-fire-energy": 3.0e-3, "all-fire-energy": 4.0e-3})
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("times the no-fire energy" in f for f in report["findings"]))

    def test_an_all_fire_energy_beyond_the_table_fails(self):
        report = assess_high_voltage_initiator(
            high_device(**{"no-fire-energy": 0.1, "all-fire-energy": 0.3})
        )
        self.assertFalse(report["compliant"])

    def test_a_low_voltage_device_cannot_be_graded_here(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_initiator(low_device())

    def test_a_non_mapping_firing_set_raises(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_initiator(high_device(**{"firing-set": "2 kV"}))


class TestDispatchAndPopulation(unittest.TestCase):
    def test_dispatch_sends_a_low_voltage_device_to_the_current_table(self):
        self.assertEqual(assess_initiator(low_device())["category"], "low-voltage")

    def test_dispatch_sends_a_high_voltage_device_to_the_energy_table(self):
        self.assertEqual(assess_initiator(high_device())["category"], "high-voltage")

    def test_dispatch_rejects_an_unknown_category(self):
        with self.assertRaises(ValueError):
            assess_initiator({"category": "laser", "properties": {}})

    def test_a_mixed_population_of_sound_devices_is_met(self):
        report = assess_initiator_population(
            {"lv-1": low_device(), "hv-1": high_device()}
        )
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_devices"], [])

    def test_one_bad_device_is_named_in_the_population(self):
        report = assess_initiator_population(
            {
                "lv-1": low_device(**{"bridge-resistance": 3.0}),
                "hv-1": high_device(),
            }
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_devices"], ["lv-1"])
        self.assertTrue(report["findings"][0].startswith("lv-1:"))

    def test_an_empty_population_raises(self):
        with self.assertRaises(ValueError):
            assess_initiator_population({})


if __name__ == "__main__":
    unittest.main()
