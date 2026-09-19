"""Contract test for the e3311 laser/mechanical/packaged-charge leaf (stdlib unittest)."""

import math
import unittest

from e3311_laser_mechanical_initiators_packaged_charges_logic import (
    DEFAULT_ENERGETIC_DEVICE_POLICY,
    DEVICE_KINDS,
    STANDARD_GRAVITY_M_S2,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_device_set,
    assess_energetic_device,
    assess_laser_initiator,
    assess_mechanical_initiator,
    assess_packaged_charge,
    drop_impact_energy_j,
    firing_pin_energy_j,
    mass_deviation,
    optical_loss_budget_db,
    optical_transmission,
    validate_energetic_device_policy,
)


def laser(**kw):
    properties = {
        "wavelength_nm": 1064.0,
        "source_pulse_energy_j": 1.0,
        "segment_losses_db": [4.0, 3.0, 3.0],
        "all_fire_energy_j": 0.05,
        "no_fire_power_w": 0.1,
        "monitor_power_w": 0.01,
    }
    properties.update(kw)
    return {"kind": "laser-initiator", "properties": properties}


def mechanical(**kw):
    properties = {
        "firing_pin_force_n": 40.0,
        "firing_pin_stroke_m": 0.01,
        "all_fire_energy_j": 0.1,
        "no_fire_impact_energy_j": 0.05,
        "handling_mass_kg": 0.05,
        "drop_height_m": 0.05,
    }
    properties.update(kw)
    return {"kind": "mechanical-initiator", "properties": properties}


def charge(**kw):
    properties = {
        "nominal_explosive_mass_kg": 0.010,
        "actual_explosive_mass_kg": 0.0102,
        "delivered_output": 5.0,
        "required_output": 3.0,
        "autoignition_temperature_c": 200.0,
        "max_operating_temperature_c": 70.0,
    }
    properties.update(kw)
    return {"kind": "packaged-charge", "properties": properties}


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_energetic_device_policy(DEFAULT_ENERGETIC_DEVICE_POLICY),
            DEFAULT_ENERGETIC_DEVICE_POLICY,
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_energetic_device_policy(["charge_mass_tolerance", 0.05])

    def test_an_inverted_wavelength_band_raises(self):
        policy = dict(
            DEFAULT_ENERGETIC_DEVICE_POLICY, laser_wavelength_band_nm=(1100.0, 800.0)
        )
        with self.assertRaises(ValueError):
            validate_energetic_device_policy(policy)

    def test_a_fire_margin_below_unity_raises(self):
        policy = dict(DEFAULT_ENERGETIC_DEVICE_POLICY, min_optical_fire_margin=0.5)
        with self.assertRaises(ValueError):
            validate_energetic_device_policy(policy)

    def test_a_mass_tolerance_at_unity_raises(self):
        policy = dict(DEFAULT_ENERGETIC_DEVICE_POLICY, charge_mass_tolerance=1.0)
        with self.assertRaises(ValueError):
            validate_energetic_device_policy(policy)


class TestOpticalArithmetic(unittest.TestCase):
    def test_ten_decibel_of_loss_leaves_a_tenth(self):
        self.assertAlmostEqual(optical_transmission(10.0), 0.1, places=12)

    def test_no_loss_leaves_everything(self):
        self.assertAlmostEqual(optical_transmission(0.0), 1.0, places=12)

    def test_twenty_decibel_of_loss_leaves_a_hundredth(self):
        self.assertAlmostEqual(optical_transmission(20.0), 0.01, places=12)

    def test_a_negative_loss_raises(self):
        with self.assertRaises(ValueError):
            optical_transmission(-3.0)

    def test_the_loss_budget_is_the_sum_of_its_segments(self):
        self.assertAlmostEqual(optical_loss_budget_db([4.0, 3.0, 3.0]), 10.0, places=12)

    def test_an_empty_loss_budget_raises(self):
        with self.assertRaises(ValueError):
            optical_loss_budget_db([])

    def test_a_negative_segment_loss_raises(self):
        with self.assertRaises(ValueError):
            optical_loss_budget_db([4.0, -1.0])


class TestMechanicalArithmetic(unittest.TestCase):
    def test_firing_pin_energy_is_force_times_stroke(self):
        self.assertAlmostEqual(firing_pin_energy_j(40.0, 0.01), 0.4, places=12)

    def test_firing_pin_energy_rejects_a_zero_stroke(self):
        with self.assertRaises(ValueError):
            firing_pin_energy_j(40.0, 0.0)

    def test_drop_energy_uses_standard_gravity(self):
        self.assertAlmostEqual(
            drop_impact_energy_j(2.0, 1.0), 2.0 * STANDARD_GRAVITY_M_S2, places=12
        )

    def test_a_zero_drop_height_puts_in_no_energy(self):
        self.assertAlmostEqual(drop_impact_energy_j(2.0, 0.0), 0.0, places=12)

    def test_drop_energy_rejects_a_negative_height(self):
        with self.assertRaises(ValueError):
            drop_impact_energy_j(2.0, -1.0)

    def test_mass_deviation_is_symmetric_in_sign(self):
        self.assertAlmostEqual(mass_deviation(0.01, 0.011), 0.1, places=12)
        self.assertAlmostEqual(mass_deviation(0.01, 0.009), 0.1, places=12)

    def test_mass_deviation_rejects_a_zero_nominal(self):
        with self.assertRaises(ValueError):
            mass_deviation(0.0, 0.01)


class TestLaserInitiator(unittest.TestCase):
    def test_a_sound_optical_chain_passes(self):
        report = assess_laser_initiator(laser())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_the_delivered_energy_is_the_source_after_the_budget(self):
        report = assess_laser_initiator(laser())
        self.assertAlmostEqual(report["total_loss_db"], 10.0, places=12)
        self.assertAlmostEqual(report["delivered_energy_j"], 0.1, places=12)

    def test_a_chain_exactly_on_the_required_energy_passes(self):
        report = assess_laser_initiator(laser(all_fire_energy_j=0.05))
        self.assertAlmostEqual(report["required_energy_j"], 0.1, places=9)
        self.assertAlmostEqual(report["delivered_energy_j"], 0.1, places=9)
        self.assertTrue(report["compliant"])

    def test_an_extra_connector_breaks_the_energy_margin(self):
        report = assess_laser_initiator(
            laser(segment_losses_db=[4.0, 3.0, 3.0, 6.0])
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("fibre path delivers" in f for f in report["findings"]))

    def test_a_wavelength_outside_the_band_is_a_finding(self):
        report = assess_laser_initiator(laser(wavelength_nm=532.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("wavelength" in f for f in report["findings"]))

    def test_a_wavelength_on_the_band_edge_passes(self):
        report = assess_laser_initiator(laser(wavelength_nm=800.0))
        self.assertTrue(report["compliant"])

    def test_a_bright_monitor_beam_breaks_the_no_fire_ratio(self):
        report = assess_laser_initiator(laser(monitor_power_w=1.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("monitor power" in f for f in report["findings"]))

    def test_no_monitor_beam_reports_an_infinite_ratio(self):
        report = assess_laser_initiator(laser(monitor_power_w=0.0))
        self.assertTrue(math.isinf(report["no_fire_ratio"]))
        self.assertTrue(report["compliant"])

    def test_a_mechanical_device_cannot_be_graded_here(self):
        with self.assertRaises(ValueError):
            assess_laser_initiator(mechanical())

    def test_a_missing_source_energy_raises(self):
        device = laser()
        del device["properties"]["source_pulse_energy_j"]
        with self.assertRaises(ValueError):
            assess_laser_initiator(device)


class TestMechanicalInitiator(unittest.TestCase):
    def test_a_sound_percussion_device_passes(self):
        report = assess_mechanical_initiator(mechanical())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_a_firing_pin_exactly_on_the_required_energy_passes(self):
        report = assess_mechanical_initiator(
            mechanical(firing_pin_force_n=20.0, firing_pin_stroke_m=0.01)
        )
        self.assertAlmostEqual(report["delivered_energy_j"], 0.2, places=9)
        self.assertAlmostEqual(report["required_energy_j"], 0.2, places=9)
        self.assertTrue(report["compliant"])

    def test_a_weak_firing_pin_fails(self):
        report = assess_mechanical_initiator(mechanical(firing_pin_force_n=4.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("firing pin delivers" in f for f in report["findings"]))

    def test_a_tall_drop_exceeds_the_no_fire_impact_energy(self):
        report = assess_mechanical_initiator(mechanical(drop_height_m=2.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("handling drop" in f for f in report["findings"]))

    def test_a_thin_impact_separation_fails(self):
        report = assess_mechanical_initiator(
            mechanical(all_fire_energy_j=0.1, no_fire_impact_energy_j=0.08)
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("times the no-fire" in f for f in report["findings"]))

    def test_a_charge_cannot_be_graded_here(self):
        with self.assertRaises(ValueError):
            assess_mechanical_initiator(charge())

    def test_a_missing_drop_height_raises(self):
        device = mechanical()
        del device["properties"]["drop_height_m"]
        with self.assertRaises(ValueError):
            assess_mechanical_initiator(device)


class TestPackagedCharge(unittest.TestCase):
    def test_a_sound_charge_passes(self):
        report = assess_packaged_charge(charge())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_a_mass_exactly_on_the_tolerance_passes(self):
        report = assess_packaged_charge(charge(actual_explosive_mass_kg=0.0105))
        self.assertAlmostEqual(report["mass_deviation"], 0.05, places=9)
        self.assertTrue(report["compliant"])

    def test_an_overfilled_charge_fails(self):
        report = assess_packaged_charge(charge(actual_explosive_mass_kg=0.012))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("explosive mass" in f for f in report["findings"]))

    def test_an_output_exactly_on_the_margin_passes(self):
        report = assess_packaged_charge(charge(delivered_output=3.6))
        self.assertAlmostEqual(report["required_output_with_margin"], 3.6, places=9)
        self.assertTrue(report["compliant"])

    def test_a_weak_output_fails(self):
        report = assess_packaged_charge(charge(delivered_output=2.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("delivers an output" in f for f in report["findings"]))

    def test_a_narrow_autoignition_separation_fails(self):
        report = assess_packaged_charge(charge(autoignition_temperature_c=90.0))
        self.assertFalse(report["compliant"])
        self.assertAlmostEqual(report["autoignition_separation_k"], 20.0, places=12)

    def test_a_separation_exactly_on_the_margin_passes(self):
        report = assess_packaged_charge(charge(autoignition_temperature_c=120.0))
        self.assertAlmostEqual(report["autoignition_separation_k"], 50.0, places=9)
        self.assertTrue(report["compliant"])

    def test_a_laser_device_cannot_be_graded_here(self):
        with self.assertRaises(ValueError):
            assess_packaged_charge(laser())


class TestDispatchAndSet(unittest.TestCase):
    def test_dispatch_reaches_every_kind(self):
        kinds = {
            assess_energetic_device(laser())["kind"],
            assess_energetic_device(mechanical())["kind"],
            assess_energetic_device(charge())["kind"],
        }
        self.assertEqual(sorted(kinds), sorted(DEVICE_KINDS))

    def test_dispatch_rejects_an_unknown_kind(self):
        with self.assertRaises(ValueError):
            assess_energetic_device({"kind": "squib", "properties": {"a": 1}})

    def test_a_sound_mixed_set_is_met(self):
        report = assess_device_set(
            {"las-1": laser(), "mech-1": mechanical(), "pc-1": charge()}
        )
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_devices"], [])

    def test_one_bad_device_is_named_in_the_set(self):
        report = assess_device_set(
            {"las-1": laser(wavelength_nm=532.0), "pc-1": charge()}
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_devices"], ["las-1"])
        self.assertTrue(report["findings"][0].startswith("las-1:"))

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_device_set({})

    def test_a_non_mapping_set_raises(self):
        with self.assertRaises(ValueError):
            assess_device_set(["las-1"])


if __name__ == "__main__":
    unittest.main()
