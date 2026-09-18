#!/usr/bin/env python3
"""Gate 3 contract test for e2007-cable-injection-susceptibility-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_cable_injection_susceptibility_equipment.py
"""

import unittest

from e2007_cable_injection_susceptibility_equipment_logic import (
    ADEQUATE,
    CEILING,
    DIRECTIONAL_COUPLER,
    FLOOR,
    INADEQUATE,
    INJECTION_PROBE,
    MARGINAL,
    MONITOR_PROBE,
    POWER_AMPLIFIER,
    PULSE_GENERATOR,
    QUANTITY_SENSE,
    REQUIRED_ITEMS,
    RISE_BANDWIDTH_PRODUCT,
    SIGNAL_GENERATOR,
    VERDICT_FIT,
    VERDICT_FIT_WITH_LIMITATIONS,
    VERDICT_NOT_FIT,
    assess_injection_equipment,
    categorize_capability,
    derive_requirements,
    normalize_inventory,
    required_forward_power_w,
    required_probe_current_rating_a,
    required_pulse_amplitude_v,
    required_pulse_rise_time_s,
    required_transfer_impedance_ohm,
    shortfall_factor,
    validate_target,
)

BAND_HIGH = 1.0e8
TARGET_CURRENT_A = 0.1
LOOP_IMPEDANCE_OHM = 100.0


def target(**over):
    spec = {
        "injection_current_a": TARGET_CURRENT_A,
        "common_mode_impedance_ohm": LOOP_IMPEDANCE_OHM,
        "band_low_hz": 1.0e5,
        "band_high_hz": BAND_HIGH,
        "receiver_sensitivity_v": 1.0e-6,
        "probe_insertion_loss_db": 6.0,
        "drive_headroom_db": 3.0,
        "current_headroom": 1.5,
        "modulation_depth_pct": 80.0,
        "coupler_directivity_db": 20.0,
    }
    spec.update(over)
    return spec


def inventory(**over):
    items = {
        SIGNAL_GENERATOR: {
            "max_frequency_hz": 1.0e9,
            "min_frequency_hz": 1.0e4,
            "modulation_depth_pct": 90.0,
        },
        POWER_AMPLIFIER: {
            "forward_power_w": 25.0,
            "max_frequency_hz": 1.0e9,
            "min_frequency_hz": 1.0e4,
        },
        INJECTION_PROBE: {
            "current_rating_a": 0.5,
            "max_frequency_hz": 4.0e8,
            "min_frequency_hz": 1.0e4,
            "insertion_loss_db": 4.0,
        },
        MONITOR_PROBE: {
            "transfer_impedance_ohm": 1.0,
            "max_frequency_hz": 4.0e8,
        },
        PULSE_GENERATOR: {"rise_time_s": 1.0e-9, "amplitude_v": 50.0},
        DIRECTIONAL_COUPLER: {"directivity_db": 30.0},
    }
    for name, changes in over.items():
        key = name.replace("_", "-")
        if changes is None:
            del items[key]
        else:
            items[key].update(changes)
    return [dict(record, item=name) for name, record in items.items()]


def assess(**over):
    return assess_injection_equipment(target(), inventory(**over))


class TestTargetValidation(unittest.TestCase):
    def test_a_good_target_fills_its_defaults(self):
        spec = target()
        del spec["drive_headroom_db"]
        self.assertAlmostEqual(validate_target(spec)["drive_headroom_db"], 3.0, places=9)

    def test_zero_injection_current_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(injection_current_a=0.0))

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(band_high_hz=1.0e4))

    def test_a_negative_insertion_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(probe_insertion_loss_db=-1.0))

    def test_a_modulation_depth_over_full_scale_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(modulation_depth_pct=120.0))

    def test_a_zero_modulation_depth_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(modulation_depth_pct=0.0))

    def test_current_headroom_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(current_headroom=0.8))

    def test_a_missing_receiver_sensitivity_is_rejected(self):
        spec = target()
        del spec["receiver_sensitivity_v"]
        with self.assertRaises(ValueError):
            validate_target(spec)

    def test_a_boolean_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target(target(common_mode_impedance_ohm=True))


class TestRequirementDerivation(unittest.TestCase):
    def test_a_lossless_bench_owes_the_dissipated_power_alone(self):
        self.assertAlmostEqual(
            required_forward_power_w(TARGET_CURRENT_A, LOOP_IMPEDANCE_OHM, 0.0, 0.0),
            1.0,
            places=9,
        )

    def test_ten_more_decibels_of_loss_costs_ten_times_the_power(self):
        base = required_forward_power_w(TARGET_CURRENT_A, LOOP_IMPEDANCE_OHM, 0.0, 0.0)
        lossy = required_forward_power_w(TARGET_CURRENT_A, LOOP_IMPEDANCE_OHM, 10.0, 0.0)
        self.assertAlmostEqual(lossy / base, 10.0, places=9)

    def test_zero_current_cannot_size_an_amplifier(self):
        with self.assertRaises(ValueError):
            required_forward_power_w(0.0, LOOP_IMPEDANCE_OHM, 6.0, 3.0)

    def test_the_probe_rating_is_the_current_times_its_headroom(self):
        self.assertAlmostEqual(
            required_probe_current_rating_a(TARGET_CURRENT_A, 1.5), 0.15, places=9
        )

    def test_a_headroom_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            required_probe_current_rating_a(TARGET_CURRENT_A, 0.9)

    def test_the_transfer_impedance_floor_lifts_the_target_off_the_noise_floor(self):
        self.assertAlmostEqual(
            required_transfer_impedance_ohm(1.0e-6, TARGET_CURRENT_A), 1.0e-5, places=12
        )

    def test_a_zero_receiver_sensitivity_is_rejected(self):
        with self.assertRaises(ValueError):
            required_transfer_impedance_ohm(0.0, TARGET_CURRENT_A)

    def test_the_pulse_edge_ceiling_follows_the_band_ceiling(self):
        self.assertAlmostEqual(
            required_pulse_rise_time_s(BAND_HIGH),
            RISE_BANDWIDTH_PRODUCT / BAND_HIGH,
            places=15,
        )

    def test_the_pulse_amplitude_floor_is_the_current_in_the_loop(self):
        self.assertAlmostEqual(
            required_pulse_amplitude_v(TARGET_CURRENT_A, LOOP_IMPEDANCE_OHM),
            10.0,
            places=9,
        )

    def test_every_quantity_the_sense_table_names_gets_a_requirement(self):
        _, requirements = derive_requirements(target())
        self.assertEqual(set(requirements), set(QUANTITY_SENSE))


class TestCapabilityGrading(unittest.TestCase):
    def test_a_capability_well_past_a_floor_is_adequate(self):
        self.assertEqual(categorize_capability(25.0, 8.0, FLOOR), ADEQUATE)

    def test_a_capability_landing_on_a_floor_is_marginal(self):
        self.assertEqual(categorize_capability(8.0, 8.0, FLOOR), MARGINAL)

    def test_a_capability_under_a_floor_is_inadequate(self):
        self.assertEqual(categorize_capability(6.0, 8.0, FLOOR), INADEQUATE)

    def test_a_value_well_under_a_ceiling_is_adequate(self):
        self.assertEqual(categorize_capability(1.0e-9, 3.5e-9, CEILING), ADEQUATE)

    def test_a_value_landing_on_a_ceiling_is_marginal(self):
        self.assertEqual(categorize_capability(3.5e-9, 3.5e-9, CEILING), MARGINAL)

    def test_a_value_over_a_ceiling_is_inadequate(self):
        self.assertEqual(categorize_capability(1.0e-8, 3.5e-9, CEILING), INADEQUATE)

    def test_an_unknown_comparison_sense_is_rejected(self):
        with self.assertRaises(ValueError):
            shortfall_factor(1.0, 2.0, "about-right")

    def test_a_marginal_ratio_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_capability(25.0, 8.0, FLOOR, 0.5)

    def test_a_shortfall_factor_past_one_means_it_does_not_reach(self):
        self.assertGreater(shortfall_factor(4.0, 8.0, FLOOR), 1.0)


class TestInventoryNormalization(unittest.TestCase):
    def test_a_good_inventory_normalizes_to_every_required_item(self):
        self.assertEqual(set(normalize_inventory(inventory())), set(REQUIRED_ITEMS))

    def test_an_unrecognized_item_is_refused(self):
        items = inventory()
        items.append({"item": "spectrum-painter", "max_frequency_hz": 1.0e9})
        with self.assertRaises(ValueError):
            normalize_inventory(items)

    def test_a_duplicate_declaration_is_refused(self):
        items = inventory()
        items.append(dict(items[0]))
        with self.assertRaises(ValueError):
            normalize_inventory(items)

    def test_an_item_record_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_inventory([(POWER_AMPLIFIER, 25.0)])

    def test_an_empty_inventory_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_inventory([])

    def test_an_inventory_handed_over_as_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_inventory({POWER_AMPLIFIER: {"forward_power_w": 25.0}})

    def test_an_item_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_inventory([{"forward_power_w": 25.0}])


class TestEquipmentAssessment(unittest.TestCase):
    def test_a_complete_bench_is_fit(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_FIT)
        self.assertEqual(report["missing_items"], [])

    def test_a_missing_amplifier_is_a_finding(self):
        report = assess(power_amplifier=None)
        self.assertEqual(report["verdict"], VERDICT_NOT_FIT)
        self.assertEqual(report["missing_items"], [POWER_AMPLIFIER])

    def test_an_underpowered_amplifier_governs_the_shortfall(self):
        report = assess(power_amplifier={"forward_power_w": 1.0})
        self.assertEqual(report["verdict"], VERDICT_NOT_FIT)
        self.assertEqual(
            report["governing_shortfall"], (POWER_AMPLIFIER, "forward_power_w")
        )

    def test_an_amplifier_sitting_on_the_requirement_is_only_a_limitation(self):
        needed = required_forward_power_w(
            TARGET_CURRENT_A, LOOP_IMPEDANCE_OHM, 6.0, 3.0
        )
        report = assess(power_amplifier={"forward_power_w": needed})
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_FIT_WITH_LIMITATIONS)
        self.assertEqual(
            report["checks"][(POWER_AMPLIFIER, "forward_power_w")]["category"], MARGINAL
        )

    def test_a_pulse_generator_edge_slower_than_the_band_is_a_finding(self):
        report = assess(pulse_generator={"rise_time_s": 5.0e-8})
        self.assertEqual(
            report["checks"][(PULSE_GENERATOR, "rise_time_s")]["category"], INADEQUATE
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_FIT)

    def test_a_probe_lossier_than_the_sizing_assumed_is_a_finding(self):
        report = assess(injection_probe={"insertion_loss_db": 12.0})
        self.assertEqual(
            report["checks"][(INJECTION_PROBE, "insertion_loss_db")]["category"],
            INADEQUATE,
        )

    def test_a_probe_that_stops_below_the_band_ceiling_is_a_finding(self):
        report = assess(injection_probe={"max_frequency_hz": 1.0e6})
        self.assertEqual(report["verdict"], VERDICT_NOT_FIT)

    def test_a_quantity_left_undeclared_is_a_finding(self):
        items = inventory()
        for record in items:
            if record["item"] == DIRECTIONAL_COUPLER:
                del record["directivity_db"]
        report = assess_injection_equipment(target(), items)
        self.assertEqual(report["verdict"], VERDICT_NOT_FIT)
        self.assertNotIn((DIRECTIONAL_COUPLER, "directivity_db"), report["checks"])

    def test_the_governing_shortfall_is_the_largest_one_not_the_first(self):
        report = assess(
            directional_coupler={"directivity_db": 18.0},
            power_amplifier={"forward_power_w": 0.5},
        )
        self.assertEqual(
            report["governing_shortfall"], (POWER_AMPLIFIER, "forward_power_w")
        )
        self.assertGreater(report["governing_shortfall_factor"], 10.0)

    def test_a_non_positive_declared_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            assess(current_monitor_probe={"transfer_impedance_ohm": 0.0})

    def test_a_marginal_monitor_probe_leaves_the_bench_usable(self):
        report = assess(current_monitor_probe={"transfer_impedance_ohm": 1.0e-5})
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_FIT_WITH_LIMITATIONS)


if __name__ == "__main__":
    unittest.main()
