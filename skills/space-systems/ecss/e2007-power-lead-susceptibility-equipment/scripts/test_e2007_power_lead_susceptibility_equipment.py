#!/usr/bin/env python3
"""Contract test for the power-lead susceptibility equipment leaf."""

import unittest

from e2007_power_lead_susceptibility_equipment_logic import (
    AMPLIFIER_HEADROOM_DB,
    INJECTION_BAND_LOWER_HZ,
    INJECTION_BAND_UPPER_HZ,
    ITEM_ROLES,
    RESISTOR_DERATING_FRACTION,
    RESISTOR_REACTANCE_RATIO_LIMIT,
    amplifier_margin_db,
    assess_injection_equipment,
    check_amplifier,
    check_generator_span,
    check_injection_resistor,
    drive_power_w,
    normalize_item,
    resistor_reactance_ohm,
)

# 2*pi*5e7*1.5915494309189535e-10 == 0.05 ohm, exactly a tenth of a 0.5 ohm
# series resistor: the inductance that sits the reactance ratio on its bound.
INDUCTANCE_AT_RATIO_LIMIT_H = 1.5915494309189535e-10


def generator(**overrides):
    item = {
        "id": "GEN-1",
        "role": "generator",
        "lower_hz": 10.0,
        "upper_hz": 8.0e7,
    }
    item.update(overrides)
    return item


def amplifier(**overrides):
    item = {
        "id": "AMP-1",
        "role": "amplifier",
        "lower_hz": 10.0,
        "upper_hz": 8.0e7,
        "rated_power_w": 200.0,
    }
    item.update(overrides)
    return item


def resistor(**overrides):
    item = {
        "id": "RES-1",
        "role": "injection-resistor",
        "resistance_ohm": 0.5,
        "inductance_h": 1.0e-10,
        "rating_w": 25.0,
    }
    item.update(overrides)
    return item


def inventory(**overrides):
    items = {
        "generator": generator(),
        "amplifier": amplifier(),
        "resistor": resistor(),
    }
    for key in overrides:
        if key not in items:
            raise KeyError(key)
    items.update(overrides)
    order = ("generator", "amplifier", "resistor")
    return [items[key] for key in order if items.get(key) is not None]


def requirement(**overrides):
    needs = {
        "required_lower_hz": 30.0,
        "required_upper_hz": 5.0e7,
        "injection_voltage_v": 3.0,
        "load_ohm": 0.5,
        "cable_loss_db": 0.0,
        "headroom_db": 0.0,
        "lead_current_a": 2.0,
    }
    needs.update(overrides)
    return needs


class TestDrivePower(unittest.TestCase):
    def test_lossless_case_is_the_delivered_power(self):
        self.assertAlmostEqual(
            drive_power_w(3.0, 0.5, 0.0, 0.0), 18.0, places=9
        )

    def test_headroom_raises_the_drive_power(self):
        self.assertAlmostEqual(
            drive_power_w(3.0, 0.5, 0.0, 3.0), 35.91472166943983, places=9
        )

    def test_loss_and_headroom_add_as_decibels(self):
        self.assertAlmostEqual(
            drive_power_w(3.0, 0.5, 4.0, 6.0), 180.0, places=9
        )

    def test_default_headroom_is_the_module_constant(self):
        self.assertAlmostEqual(
            drive_power_w(3.0, 0.5),
            drive_power_w(3.0, 0.5, 0.0, AMPLIFIER_HEADROOM_DB),
            places=9,
        )

    def test_zero_voltage_raises(self):
        with self.assertRaises(ValueError):
            drive_power_w(0.0, 0.5)

    def test_negative_loss_raises(self):
        with self.assertRaises(ValueError):
            drive_power_w(3.0, 0.5, -1.0)

    def test_boolean_voltage_raises(self):
        with self.assertRaises(ValueError):
            drive_power_w(True, 0.5)


class TestAmplifier(unittest.TestCase):
    def test_margin_of_a_doubled_rating(self):
        self.assertAlmostEqual(
            amplifier_margin_db(36.0, 18.0), 3.0102999566398116, places=9
        )

    def test_margin_is_negative_when_underpowered(self):
        self.assertAlmostEqual(
            amplifier_margin_db(9.0, 18.0), -3.0102999566398116, places=9
        )

    def test_rating_equal_to_the_need_is_sufficient(self):
        check = check_amplifier(18.0, 18.0)
        self.assertTrue(check["sufficient"])
        self.assertAlmostEqual(check["margin_db"], 0.0, places=9)

    def test_rating_below_the_need_is_insufficient(self):
        self.assertFalse(check_amplifier(12.0, 18.0)["sufficient"])

    def test_non_numeric_rating_raises(self):
        with self.assertRaises(ValueError):
            check_amplifier("200", 18.0)


class TestInjectionResistor(unittest.TestCase):
    def test_reactance_of_a_residual_inductance(self):
        self.assertAlmostEqual(
            resistor_reactance_ohm(1.0e-10, 5.0e7),
            0.031415926535897934,
            places=9,
        )

    def test_zero_inductance_has_no_reactance(self):
        self.assertAlmostEqual(resistor_reactance_ohm(0.0, 5.0e7), 0.0, places=12)

    def test_ratio_on_its_bound_still_counts_as_low_inductance(self):
        check = check_injection_resistor(
            0.5, INDUCTANCE_AT_RATIO_LIMIT_H, 25.0, 1.0, 5.0e7
        )
        self.assertAlmostEqual(
            check["reactance_ratio"], RESISTOR_REACTANCE_RATIO_LIMIT, places=9
        )
        self.assertTrue(check["low_inductance"])

    def test_ratio_well_above_the_bound_fails(self):
        check = check_injection_resistor(0.5, 1.0e-8, 25.0, 1.0, 5.0e7)
        self.assertFalse(check["low_inductance"])
        self.assertGreater(check["reactance_ratio"], 1.0)

    def test_dissipation_on_the_derated_bound_is_within(self):
        check = check_injection_resistor(0.5, 1.0e-10, 4.0, 2.0, 5.0e7)
        self.assertAlmostEqual(check["dissipated_w"], 2.0, places=9)
        self.assertAlmostEqual(
            check["allowed_w"], 4.0 * RESISTOR_DERATING_FRACTION, places=9
        )
        self.assertTrue(check["power_within"])

    def test_dissipation_far_over_the_derated_bound_fails(self):
        check = check_injection_resistor(0.5, 1.0e-10, 1.0, 5.0, 5.0e7)
        self.assertFalse(check["power_within"])

    def test_derating_above_one_raises(self):
        with self.assertRaises(ValueError):
            check_injection_resistor(0.5, 1.0e-10, 25.0, 1.0, 5.0e7, derating=1.5)

    def test_negative_inductance_raises(self):
        with self.assertRaises(ValueError):
            check_injection_resistor(0.5, -1.0e-10, 25.0, 1.0, 5.0e7)


class TestGeneratorSpan(unittest.TestCase):
    def test_a_wider_span_covers_the_band(self):
        span = check_generator_span(10.0, 8.0e7, 30.0, 5.0e7)
        self.assertTrue(span["covers"])
        self.assertEqual(span["uncovered_hz"], ())

    def test_edges_met_exactly_still_cover(self):
        span = check_generator_span(30.0, 5.0e7, 30.0, 5.0e7)
        self.assertTrue(span["covers"])

    def test_a_short_top_leaves_an_uncovered_stretch(self):
        span = check_generator_span(30.0, 1.0e7, 30.0, 5.0e7)
        self.assertFalse(span["covers"])
        self.assertFalse(span["reaches_top"])
        self.assertEqual(span["uncovered_hz"], ((1.0e7, 5.0e7),))

    def test_a_high_bottom_leaves_an_uncovered_stretch(self):
        span = check_generator_span(1.0e3, 5.0e7, 30.0, 5.0e7)
        self.assertFalse(span["reaches_bottom"])
        self.assertEqual(span["uncovered_hz"], ((30.0, 1.0e3),))

    def test_a_span_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            check_generator_span(5.0e7, 30.0)

    def test_a_required_band_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            check_generator_span(30.0, 5.0e7, 5.0e7, 30.0)

    def test_module_default_band_is_used_when_none_is_given(self):
        span = check_generator_span(10.0, 8.0e7)
        self.assertAlmostEqual(span["required_lower_hz"], INJECTION_BAND_LOWER_HZ)
        self.assertAlmostEqual(span["required_upper_hz"], INJECTION_BAND_UPPER_HZ)


class TestNormalizeItem(unittest.TestCase):
    def test_a_good_generator_normalizes(self):
        item = normalize_item(generator())
        self.assertEqual(item["id"], "GEN-1")
        self.assertAlmostEqual(item["upper_hz"], 8.0e7, places=9)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(generator(role="coupler"))

    def test_unknown_key_raises(self):
        item = generator()
        item["gain_db"] = 20.0
        with self.assertRaises(ValueError):
            normalize_item(item)

    def test_missing_key_raises(self):
        item = generator()
        del item["upper_hz"]
        with self.assertRaises(ValueError):
            normalize_item(item)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(generator(id="   "))

    def test_span_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(generator(lower_hz=8.0e7, upper_hz=10.0))

    def test_a_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            normalize_item("GEN-1")

    def test_zero_inductance_is_accepted_on_a_resistor(self):
        item = normalize_item(resistor(inductance_h=0.0))
        self.assertAlmostEqual(item["inductance_h"], 0.0, places=12)


class TestAssessInjectionEquipment(unittest.TestCase):
    def test_a_complete_chain_is_ready(self):
        report = assess_injection_equipment(inventory(), requirement())
        self.assertTrue(report["ready"])
        self.assertEqual(report["verdict"], "chain-ready")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["roles_present"], ITEM_ROLES)

    def test_required_power_matches_the_delivered_power_when_nothing_is_added(self):
        report = assess_injection_equipment(inventory(), requirement())
        self.assertAlmostEqual(report["required_power_w"], 18.0, places=9)

    def test_a_missing_role_is_reported(self):
        items = [item for item in inventory() if item["role"] != "amplifier"]
        report = assess_injection_equipment(items, requirement())
        self.assertFalse(report["ready"])
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("role-missing", codes)

    def test_an_underpowered_amplifier_is_reported(self):
        items = inventory(amplifier=amplifier(rated_power_w=1.0))
        report = assess_injection_equipment(items, requirement())
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("amplifier-underpowered", codes)

    def test_a_short_generator_span_is_reported(self):
        items = inventory(generator=generator(upper_hz=1.0e6))
        report = assess_injection_equipment(items, requirement())
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("generator-span-short", codes)

    def test_an_inductive_series_resistor_is_reported(self):
        items = inventory(resistor=resistor(inductance_h=1.0e-7))
        report = assess_injection_equipment(items, requirement())
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("resistor-not-low-inductance", codes)

    def test_an_over_dissipated_resistor_is_reported(self):
        items = inventory(resistor=resistor(rating_w=0.5))
        report = assess_injection_equipment(items, requirement(lead_current_a=6.0))
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("resistor-over-dissipation", codes)

    def test_a_duplicate_identifier_raises(self):
        items = inventory()
        items[1]["id"] = items[0]["id"]
        with self.assertRaises(ValueError):
            assess_injection_equipment(items, requirement())

    def test_a_duplicated_role_raises(self):
        items = inventory() + [amplifier(id="AMP-2")]
        with self.assertRaises(ValueError):
            assess_injection_equipment(items, requirement())

    def test_an_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_injection_equipment([], requirement())

    def test_a_string_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_injection_equipment("GEN-1", requirement())

    def test_an_unknown_requirement_key_raises(self):
        needs = requirement()
        needs["duty_cycle"] = 0.5
        with self.assertRaises(ValueError):
            assess_injection_equipment(inventory(), needs)

    def test_a_requirement_without_a_load_raises(self):
        needs = requirement()
        del needs["load_ohm"]
        with self.assertRaises(ValueError):
            assess_injection_equipment(inventory(), needs)

    def test_findings_carry_code_subject_and_detail(self):
        items = inventory(amplifier=amplifier(rated_power_w=1.0))
        report = assess_injection_equipment(items, requirement())
        for finding in report["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


if __name__ == "__main__":
    unittest.main()
