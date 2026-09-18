#!/usr/bin/env python3
"""Contract tests for the clause 5.4.14.2 contact-discharge generator logic."""

import math
import unittest

from e2007_contact_discharge_test_equipment_logic import (
    APPLICATION_MODES,
    DEFAULT_MARGINAL_FRACTION,
    GROUP_ADEQUATE,
    GROUP_INADEQUATE,
    GROUP_MARGINAL,
    TIP_TYPES,
    assess_contact_discharge_equipment,
    assess_decay_checkpoints,
    current_at_ns,
    decay_fraction,
    decay_peak_current_a,
    deviation_fraction,
    governing_deviation,
    group_ceiling,
    group_floor,
    group_tolerance,
    stored_energy_mj,
    time_constant_ns,
    transferred_charge_uc,
    validate_generator,
    validate_requirement,
)


def a_generator(**overrides):
    spec = {
        "storage_capacitance_pf": 150.0,
        "discharge_resistance_ohm": 330.0,
        "charge_resistance_mohm": 100.0,
        "min_charge_voltage_kv": 0.5,
        "max_charge_voltage_kv": 8.0,
        "tip": "contact-pointed-tip",
        "application_mode": "contact-direct",
        "return_cable_length_m": 1.0,
    }
    spec.update(overrides)
    return spec


def a_requirement(**overrides):
    requirement = {
        "nominal_capacitance_pf": 150.0,
        "nominal_resistance_ohm": 330.0,
        "capacitance_tolerance": 0.30,
        "resistance_tolerance": 0.10,
        "time_constant_tolerance": 0.10,
        "min_charge_resistance_mohm": 50.0,
        "max_return_cable_m": 2.0,
        "required_levels_kv": [2.0, 4.0, 6.0],
        "decay_checkpoints": [(30.0, 0.545, 0.05), (60.0, 0.297, 0.05)],
        "required_tip": "contact-pointed-tip",
    }
    requirement.update(overrides)
    return requirement


class PulseArithmeticTests(unittest.TestCase):
    def test_time_constant_is_capacitance_times_resistance(self):
        self.assertAlmostEqual(time_constant_ns(150.0, 330.0), 49.5, places=9)

    def test_halving_the_capacitance_halves_the_time_constant(self):
        self.assertAlmostEqual(time_constant_ns(75.0, 330.0), 24.75, places=9)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            time_constant_ns(0.0, 330.0)

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            time_constant_ns(150.0, -330.0)

    def test_tail_amplitude_is_voltage_over_resistance(self):
        self.assertAlmostEqual(decay_peak_current_a(3.3, 330.0), 10.0, places=9)

    def test_tail_amplitude_scales_with_the_charge_voltage(self):
        low = decay_peak_current_a(2.0, 330.0)
        high = decay_peak_current_a(4.0, 330.0)
        self.assertAlmostEqual(high, 2.0 * low, places=9)

    def test_decay_fraction_is_unity_at_the_strike(self):
        self.assertAlmostEqual(decay_fraction(0.0, 49.5), 1.0, places=9)

    def test_decay_fraction_at_one_time_constant(self):
        self.assertAlmostEqual(decay_fraction(49.5, 49.5), math.exp(-1.0), places=9)

    def test_decay_fraction_rejects_a_negative_delay(self):
        with self.assertRaises(ValueError):
            decay_fraction(-1.0, 49.5)

    def test_decay_fraction_rejects_a_zero_time_constant(self):
        with self.assertRaises(ValueError):
            decay_fraction(10.0, 0.0)

    def test_current_at_delay_combines_amplitude_and_decay(self):
        expected = decay_peak_current_a(4.0, 330.0) * decay_fraction(30.0, 49.5)
        self.assertAlmostEqual(current_at_ns(4.0, 150.0, 330.0, 30.0), expected, places=9)

    def test_stored_energy_in_millijoules(self):
        self.assertAlmostEqual(stored_energy_mj(150.0, 4.0), 1.2, places=9)

    def test_stored_energy_grows_with_the_square_of_the_voltage(self):
        self.assertAlmostEqual(stored_energy_mj(150.0, 8.0),
                               4.0 * stored_energy_mj(150.0, 4.0), places=9)

    def test_transferred_charge_in_microcoulombs(self):
        self.assertAlmostEqual(transferred_charge_uc(150.0, 4.0), 0.6, places=9)


class GroupingTests(unittest.TestCase):
    def test_deviation_of_an_exact_match_is_zero(self):
        self.assertAlmostEqual(deviation_fraction(150.0, 150.0), 0.0, places=9)

    def test_deviation_is_symmetric(self):
        self.assertAlmostEqual(deviation_fraction(165.0, 150.0),
                               deviation_fraction(135.0, 150.0), places=9)

    def test_deviation_rejects_a_zero_nominal(self):
        with self.assertRaises(ValueError):
            deviation_fraction(150.0, 0.0)

    def test_value_on_nominal_is_adequate(self):
        group, deviation, factor = group_tolerance(150.0, 150.0, 0.30)
        self.assertEqual(group, GROUP_ADEQUATE)
        self.assertAlmostEqual(deviation, 0.0, places=9)
        self.assertAlmostEqual(factor, 1.0, places=9)

    def test_value_exactly_on_the_tolerance_edge_stays_inside_it(self):
        group, deviation, _ = group_tolerance(195.0, 150.0, 0.30)
        self.assertEqual(group, GROUP_MARGINAL)
        self.assertAlmostEqual(deviation, 0.30, places=9)

    def test_value_past_the_tolerance_is_inadequate(self):
        group, deviation, factor = group_tolerance(300.0, 150.0, 0.30)
        self.assertEqual(group, GROUP_INADEQUATE)
        self.assertAlmostEqual(deviation, 1.0, places=9)
        self.assertGreater(factor, 3.0)

    def test_marginal_fraction_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            group_tolerance(150.0, 150.0, 0.30, 0.0)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            group_tolerance(150.0, 150.0, -0.1)

    def test_floor_comfortably_cleared_is_adequate(self):
        group, ratio, _ = group_floor(100.0, 50.0)
        self.assertEqual(group, GROUP_ADEQUATE)
        self.assertAlmostEqual(ratio, 2.0, places=9)

    def test_value_sitting_on_the_floor_is_marginal(self):
        group, ratio, _ = group_floor(50.0, 50.0)
        self.assertEqual(group, GROUP_MARGINAL)
        self.assertAlmostEqual(ratio, 1.0, places=9)

    def test_value_under_the_floor_is_inadequate(self):
        group, _, factor = group_floor(10.0, 50.0)
        self.assertEqual(group, GROUP_INADEQUATE)
        self.assertAlmostEqual(factor, 5.0, places=9)

    def test_ceiling_comfortably_cleared_is_adequate(self):
        group, ratio, _ = group_ceiling(1.0, 2.0)
        self.assertEqual(group, GROUP_ADEQUATE)
        self.assertAlmostEqual(ratio, 0.5, places=9)

    def test_value_sitting_on_the_ceiling_is_marginal(self):
        group, _, _ = group_ceiling(2.0, 2.0)
        self.assertEqual(group, GROUP_MARGINAL)

    def test_value_over_the_ceiling_is_inadequate(self):
        group, _, factor = group_ceiling(6.0, 2.0)
        self.assertEqual(group, GROUP_INADEQUATE)
        self.assertAlmostEqual(factor, 3.0, places=9)

    def test_default_marginal_fraction_is_four_fifths(self):
        self.assertAlmostEqual(DEFAULT_MARGINAL_FRACTION, 0.8, places=9)


class ValidationTests(unittest.TestCase):
    def test_generator_is_normalized_with_its_time_constant(self):
        record = validate_generator(a_generator())
        self.assertAlmostEqual(record["time_constant_ns"], 49.5, places=9)

    def test_generator_tokens_are_lowercased(self):
        record = validate_generator(a_generator(tip="Contact-Pointed-Tip"))
        self.assertEqual(record["tip"], "contact-pointed-tip")

    def test_unrecognized_tip_rejected(self):
        with self.assertRaises(ValueError):
            validate_generator(a_generator(tip="screwdriver"))

    def test_unrecognized_application_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_generator(a_generator(application_mode="thrown"))

    def test_inverted_voltage_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_generator(a_generator(min_charge_voltage_kv=8.0,
                                           max_charge_voltage_kv=0.5))

    def test_missing_capacitance_rejected(self):
        spec = a_generator()
        del spec["storage_capacitance_pf"]
        with self.assertRaises(ValueError):
            validate_generator(spec)

    def test_boolean_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_generator(a_generator(discharge_resistance_ohm=True))

    def test_requirement_derives_its_nominal_time_constant(self):
        needed = validate_requirement(a_requirement())
        self.assertAlmostEqual(needed["nominal_time_constant_ns"], 49.5, places=9)

    def test_requirement_levels_are_sorted(self):
        needed = validate_requirement(a_requirement(required_levels_kv=[6.0, 2.0, 4.0]))
        self.assertEqual(needed["required_levels_kv"], [2.0, 4.0, 6.0])

    def test_repeated_required_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(a_requirement(required_levels_kv=[4.0, 4.0]))

    def test_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(a_requirement(capacitance_tolerance=1.0))

    def test_malformed_checkpoint_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(a_requirement(decay_checkpoints=[(30.0, 0.5)]))

    def test_checkpoint_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(a_requirement(decay_checkpoints=[(30.0, 1.5, 0.05)]))

    def test_empty_required_level_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(a_requirement(required_levels_kv=[]))


class DecayCheckpointTests(unittest.TestCase):
    def test_a_nominal_generator_meets_both_checkpoints(self):
        generator = validate_generator(a_generator())
        needed = validate_requirement(a_requirement())
        points = assess_decay_checkpoints(generator, needed["decay_checkpoints"])
        self.assertEqual([p["group"] for p in points],
                         [GROUP_ADEQUATE, GROUP_ADEQUATE])

    def test_achieved_fraction_matches_the_exponential(self):
        generator = validate_generator(a_generator())
        points = assess_decay_checkpoints(generator, [(49.5, 0.368, 0.05)])
        self.assertAlmostEqual(points[0]["achieved_fraction"], math.exp(-1.0), places=9)

    def test_a_slow_generator_misses_the_late_checkpoint(self):
        generator = validate_generator(
            a_generator(storage_capacitance_pf=600.0, discharge_resistance_ohm=330.0)
        )
        needed = validate_requirement(a_requirement())
        points = assess_decay_checkpoints(generator, needed["decay_checkpoints"])
        self.assertEqual(points[1]["group"], GROUP_INADEQUATE)

    def test_no_checkpoints_gives_no_results(self):
        generator = validate_generator(a_generator())
        self.assertEqual(assess_decay_checkpoints(generator, []), [])

    def test_checkpoints_need_a_normalized_generator(self):
        with self.assertRaises(ValueError):
            assess_decay_checkpoints({"c": 1}, [(30.0, 0.5, 0.05)])


class GoverningDeviationTests(unittest.TestCase):
    def test_no_inadequate_check_gives_none(self):
        report = assess_contact_discharge_equipment(a_generator(), a_requirement())
        self.assertIsNone(report["governing_deviation"])

    def test_the_largest_shortfall_governs(self):
        checks = [
            {"item": "a", "group": GROUP_INADEQUATE, "shortfall_factor": 2.0},
            {"item": "b", "group": GROUP_INADEQUATE, "shortfall_factor": 7.0},
            {"item": "c", "group": GROUP_ADEQUATE, "shortfall_factor": 1.0},
        ]
        self.assertEqual(governing_deviation(checks)["item"], "b")

    def test_governing_deviation_rejects_a_malformed_check(self):
        with self.assertRaises(ValueError):
            governing_deviation([{"item": "a"}])


class EquipmentAssessmentTests(unittest.TestCase):
    def test_a_conforming_generator_is_fit(self):
        report = assess_contact_discharge_equipment(a_generator(), a_requirement())
        self.assertTrue(report["generator_fit"])
        self.assertEqual(report["findings"], [])

    def test_derived_pulse_quantities_are_reported_at_the_top_level(self):
        report = assess_contact_discharge_equipment(a_generator(), a_requirement())
        self.assertAlmostEqual(report["time_constant_ns"], 49.5, places=9)
        self.assertAlmostEqual(report["stored_energy_mj"], 2.7, places=9)
        self.assertAlmostEqual(report["transferred_charge_uc"], 0.9, places=9)

    def test_two_in_band_parts_can_still_miss_the_time_constant(self):
        report = assess_contact_discharge_equipment(
            a_generator(storage_capacitance_pf=195.0, discharge_resistance_ohm=363.0),
            a_requirement(),
        )
        groups = {check["item"]: check["group"] for check in report["checks"]}
        self.assertEqual(groups["storage-capacitance"], GROUP_MARGINAL)
        self.assertEqual(groups["discharge-resistance"], GROUP_MARGINAL)
        self.assertEqual(groups["discharge-time-constant"], GROUP_INADEQUATE)
        self.assertFalse(report["generator_fit"])

    def test_an_air_tip_fails_direct_application(self):
        report = assess_contact_discharge_equipment(
            a_generator(tip="air-rounded-tip"), a_requirement()
        )
        self.assertFalse(report["generator_fit"])
        self.assertTrue(any("tip" in note for note in report["findings"]))

    def test_an_indirect_arrangement_is_not_this_clause(self):
        report = assess_contact_discharge_equipment(
            a_generator(application_mode="air-indirect", tip="air-rounded-tip"),
            a_requirement(),
        )
        self.assertFalse(report["generator_fit"])
        self.assertEqual(len(report["findings"]), 2)

    def test_a_short_voltage_range_leaves_a_level_uncovered(self):
        report = assess_contact_discharge_equipment(
            a_generator(max_charge_voltage_kv=4.0), a_requirement()
        )
        self.assertEqual(report["uncovered_levels_kv"], [6.0])
        self.assertFalse(report["generator_fit"])

    def test_a_level_exactly_at_the_range_edge_is_covered(self):
        report = assess_contact_discharge_equipment(
            a_generator(max_charge_voltage_kv=6.0), a_requirement()
        )
        self.assertEqual(report["uncovered_levels_kv"], [])

    def test_a_low_charging_resistance_is_a_finding(self):
        report = assess_contact_discharge_equipment(
            a_generator(charge_resistance_mohm=1.0), a_requirement()
        )
        self.assertFalse(report["generator_fit"])
        self.assertEqual(report["governing_deviation"]["item"], "charging-resistance")

    def test_a_long_return_cable_is_a_finding(self):
        report = assess_contact_discharge_equipment(
            a_generator(return_cable_length_m=6.0), a_requirement()
        )
        self.assertFalse(report["generator_fit"])

    def test_a_cable_on_the_ceiling_is_a_limitation_only(self):
        report = assess_contact_discharge_equipment(
            a_generator(return_cable_length_m=2.0), a_requirement()
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["limitations"])

    def test_the_assessment_propagates_a_generator_input_error(self):
        with self.assertRaises(ValueError):
            assess_contact_discharge_equipment(
                a_generator(storage_capacitance_pf=0.0), a_requirement()
            )

    def test_the_assessment_propagates_a_requirement_input_error(self):
        with self.assertRaises(ValueError):
            assess_contact_discharge_equipment(
                a_generator(), a_requirement(nominal_resistance_ohm=-330.0)
            )

    def test_every_recognized_token_set_is_exposed(self):
        self.assertIn("contact-pointed-tip", TIP_TYPES)
        self.assertIn("contact-direct", APPLICATION_MODES)


if __name__ == "__main__":
    unittest.main()
