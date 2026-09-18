#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-magnetic-susceptibility-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_magnetic_susceptibility_equipment.py
"""

import math
import unittest

from e2007_radiated_magnetic_susceptibility_equipment_logic import (
    DEFAULT_BAND_HZ,
    DEFAULT_LOOP_DIAMETER_M,
    DEFAULT_LOOP_TURNS,
    DEFAULT_STANDOFF_M,
    MU0,
    REQUIRED_ROLES,
    ROLE_AMPLIFIER,
    ROLE_LOOP,
    ROLE_SOURCE,
    VERDICT_INCOMPLETE,
    VERDICT_READY,
    assess_equipment_set,
    axial_flux_density_tesla,
    band_decades,
    band_overlap,
    chain_coverage,
    drive_level_dbm,
    limiting_equipment,
    loop_current_for_flux_density,
    loop_impedance_ohm,
    loop_turns_area_m2,
    meets,
    normalize_role,
    required_gain_db,
    uncovered_sub_bands,
    validate_band,
    validate_equipment,
)


def source(**over):
    record = {
        "role": ROLE_SOURCE,
        "frequency_min_hz": 1.0,
        "frequency_max_hz": 1.0e7,
        "calibration_days_remaining": 300.0,
        "max_output_dbm": 10.0,
    }
    record.update(over)
    return record


def amplifier(**over):
    record = {
        "role": ROLE_AMPLIFIER,
        "frequency_min_hz": 10.0,
        "frequency_max_hz": 1.0e6,
        "calibration_days_remaining": 220.0,
        "gain_db": 40.0,
        "max_output_dbm": 50.0,
    }
    record.update(over)
    return record


def loop(**over):
    record = {
        "role": ROLE_LOOP,
        "frequency_min_hz": 20.0,
        "frequency_max_hz": 5.0e5,
        "calibration_days_remaining": 400.0,
        "diameter_m": DEFAULT_LOOP_DIAMETER_M,
        "turns": DEFAULT_LOOP_TURNS,
        "dc_resistance_ohm": 0.5,
        "inductance_h": 2.0e-4,
        "rated_current_a": 5.0,
    }
    record.update(over)
    return record


def full_chain(**over):
    records = {"source": source(), "amplifier": amplifier(), "loop": loop()}
    records.update(over)
    return [records["source"], records["amplifier"], records["loop"]]


class TestRoleNormalization(unittest.TestCase):
    def test_every_required_role_normalizes(self):
        for role in REQUIRED_ROLES:
            self.assertEqual(normalize_role(role.upper()), role)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_role("  radiating-loop "), ROLE_LOOP)

    def test_unrecognized_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role("helmholtz-cage")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role(11)


class TestBandValidation(unittest.TestCase):
    def test_default_band_validates(self):
        low, high = validate_band(DEFAULT_BAND_HZ)
        self.assertAlmostEqual(low, 30.0)
        self.assertAlmostEqual(high, 100.0e3)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((1.0e5, 30.0))

    def test_zero_low_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((0.0, 1.0e5))

    def test_degenerate_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((100.0, 100.0))

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band([30.0, 1.0e5, 1.0e6])

    def test_decade_width_of_a_three_decade_band(self):
        self.assertAlmostEqual(band_decades((100.0, 100000.0)), 3.0, places=9)


class TestEquipmentValidation(unittest.TestCase):
    def test_source_normalizes(self):
        record = validate_equipment(source())
        self.assertEqual(record["role"], ROLE_SOURCE)
        self.assertTrue(record["calibration_current"])

    def test_amplifier_carries_gain_and_ceiling(self):
        record = validate_equipment(amplifier())
        self.assertAlmostEqual(record["gain_db"], 40.0)
        self.assertAlmostEqual(record["max_output_dbm"], 50.0)

    def test_loop_carries_its_geometry(self):
        record = validate_equipment(loop())
        self.assertAlmostEqual(record["diameter_m"], DEFAULT_LOOP_DIAMETER_M)
        self.assertAlmostEqual(record["turns"], DEFAULT_LOOP_TURNS)

    def test_lapsed_calibration_is_recorded_not_raised(self):
        record = validate_equipment(source(calibration_days_remaining=-9.0))
        self.assertFalse(record["calibration_current"])

    def test_fractional_turn_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment(loop(turns=19.5))

    def test_zero_turn_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment(loop(turns=0.0))

    def test_negative_loop_diameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment(loop(diameter_m=-0.12))

    def test_zero_loop_inductance_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment(loop(inductance_h=0.0))

    def test_loop_without_rated_current_rejected(self):
        record = loop()
        del record["rated_current_a"]
        with self.assertRaises(ValueError):
            validate_equipment(record)

    def test_amplifier_with_zero_gain_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment(amplifier(gain_db=0.0))

    def test_boolean_field_rejected_as_numeric(self):
        with self.assertRaises(ValueError):
            validate_equipment(source(frequency_min_hz=True))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment("a radiating loop")


class TestCoverage(unittest.TestCase):
    def test_overlap_of_two_bands(self):
        low, high = band_overlap((10.0, 1.0e6), (30.0, 1.0e5))
        self.assertAlmostEqual(low, 30.0)
        self.assertAlmostEqual(high, 1.0e5)

    def test_disjoint_bands_have_no_overlap(self):
        self.assertIsNone(band_overlap((10.0, 100.0), (200.0, 300.0)))

    def test_touching_bands_have_no_usable_overlap(self):
        self.assertIsNone(band_overlap((10.0, 100.0), (100.0, 300.0)))

    def test_full_chain_covers_the_exposure_band(self):
        report = chain_coverage(full_chain())
        self.assertEqual(report["gaps_hz"], [])
        self.assertAlmostEqual(
            report["covered_decades"], report["required_decades"], places=9
        )

    def test_loop_that_starts_late_opens_a_low_gap(self):
        report = chain_coverage(full_chain(loop=loop(frequency_min_hz=200.0)))
        self.assertEqual(len(report["gaps_hz"]), 1)
        self.assertAlmostEqual(report["gaps_hz"][0][0], 30.0)
        self.assertAlmostEqual(report["gaps_hz"][0][1], 200.0)

    def test_amplifier_that_stops_early_opens_a_high_gap(self):
        report = chain_coverage(full_chain(amplifier=amplifier(frequency_max_hz=4.0e4)))
        self.assertEqual(len(report["gaps_hz"]), 1)
        self.assertAlmostEqual(report["gaps_hz"][0][0], 4.0e4)

    def test_both_edges_can_be_uncovered_at_once(self):
        report = chain_coverage(
            full_chain(loop=loop(frequency_min_hz=100.0, frequency_max_hz=4.0e4))
        )
        self.assertEqual(len(report["gaps_hz"]), 2)

    def test_disjoint_item_leaves_the_whole_band_uncovered(self):
        report = chain_coverage(
            full_chain(loop=loop(frequency_min_hz=1.0e6, frequency_max_hz=1.0e7))
        )
        self.assertIsNone(report["coverage_hz"])
        self.assertAlmostEqual(report["covered_decades"], 0.0)

    def test_uncovered_sub_bands_of_a_missing_coverage(self):
        gaps = uncovered_sub_bands((30.0, 1.0e5), None)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1], 1.0e5)

    def test_empty_equipment_list_rejected(self):
        with self.assertRaises(ValueError):
            chain_coverage([])


class TestLimitingEquipment(unittest.TestCase):
    def test_narrowest_item_is_the_limit(self):
        report = limiting_equipment(
            full_chain(loop=loop(frequency_min_hz=300.0, frequency_max_hz=3.0e4))
        )
        self.assertEqual(report["role"], ROLE_LOOP)

    def test_a_chain_with_no_loss_reports_zero_lost_decades(self):
        report = limiting_equipment(full_chain())
        self.assertAlmostEqual(report["lost_decades"], 0.0, places=9)

    def test_tie_resolves_to_the_clause_role_order(self):
        report = limiting_equipment(
            full_chain(
                source=source(frequency_min_hz=300.0),
                amplifier=amplifier(frequency_min_hz=300.0),
            )
        )
        self.assertEqual(report["role"], ROLE_SOURCE)

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            limiting_equipment([])


class TestLoopGeometry(unittest.TestCase):
    def test_turns_area_product_of_the_nominal_loop(self):
        radius = DEFAULT_LOOP_DIAMETER_M / 2.0
        self.assertAlmostEqual(
            loop_turns_area_m2(),
            DEFAULT_LOOP_TURNS * math.pi * radius * radius,
            places=12,
        )

    def test_doubling_the_diameter_quadruples_the_area(self):
        one = loop_turns_area_m2(0.1, 10.0)
        two = loop_turns_area_m2(0.2, 10.0)
        self.assertAlmostEqual(two / one, 4.0, places=9)

    def test_turns_area_rejects_a_zero_diameter(self):
        with self.assertRaises(ValueError):
            loop_turns_area_m2(0.0, 10.0)

    def test_turns_area_rejects_a_sub_unit_turn_count(self):
        with self.assertRaises(ValueError):
            loop_turns_area_m2(0.1, 0.0)

    def test_field_at_the_loop_centre_matches_the_closed_form(self):
        expected = MU0 * DEFAULT_LOOP_TURNS * 1.0 / (2.0 * (DEFAULT_LOOP_DIAMETER_M / 2.0))
        self.assertAlmostEqual(
            axial_flux_density_tesla(1.0, standoff_m=0.0), expected, places=12
        )

    def test_field_falls_off_with_standoff(self):
        near = axial_flux_density_tesla(1.0, standoff_m=0.01)
        far = axial_flux_density_tesla(1.0, standoff_m=0.30)
        self.assertLess(far, near / 100.0)

    def test_field_is_linear_in_current(self):
        one = axial_flux_density_tesla(1.0)
        two = axial_flux_density_tesla(2.0)
        self.assertAlmostEqual(two / one, 2.0, places=9)

    def test_current_and_field_are_exact_inverses(self):
        current = loop_current_for_flux_density(1.0e-6)
        self.assertAlmostEqual(
            axial_flux_density_tesla(current), 1.0e-6, places=15
        )

    def test_negative_standoff_rejected(self):
        with self.assertRaises(ValueError):
            axial_flux_density_tesla(1.0, standoff_m=-0.01)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            axial_flux_density_tesla(0.0)

    def test_zero_wanted_field_rejected(self):
        with self.assertRaises(ValueError):
            loop_current_for_flux_density(0.0)


class TestDriveLevel(unittest.TestCase):
    def test_impedance_is_resistive_well_below_the_corner(self):
        # The corner sits near R / (2*pi*L); a decade under it the reactive
        # term is a part per million of the total, so the comparison is on
        # the physics, not on float representation.
        value = loop_impedance_ohm(0.5, 2.0e-4, 1.0)
        self.assertAlmostEqual(value, 0.5, places=5)

    def test_impedance_is_reactive_well_above_the_corner(self):
        frequency = 1.0e5
        value = loop_impedance_ohm(0.5, 2.0e-4, frequency)
        reactance = 2.0 * math.pi * frequency * 2.0e-4
        self.assertAlmostEqual(value / reactance, 1.0, places=4)

    def test_impedance_rejects_a_zero_frequency(self):
        with self.assertRaises(ValueError):
            loop_impedance_ohm(0.5, 2.0e-4, 0.0)

    def test_impedance_rejects_a_zero_resistance(self):
        with self.assertRaises(ValueError):
            loop_impedance_ohm(0.0, 2.0e-4, 1.0e3)

    def test_one_watt_into_the_loop_is_thirty_dbm(self):
        self.assertAlmostEqual(drive_level_dbm(1.0, 1.0), 30.0, places=9)

    def test_doubling_the_current_adds_six_decibels(self):
        low = drive_level_dbm(0.01, 50.0)
        high = drive_level_dbm(0.02, 50.0)
        self.assertAlmostEqual(high - low, 6.02059991328, places=7)

    def test_drive_level_rejects_a_zero_current(self):
        with self.assertRaises(ValueError):
            drive_level_dbm(0.0, 50.0)

    def test_required_gain_is_the_level_difference(self):
        self.assertAlmostEqual(required_gain_db(11.0, 10.0), 1.0, places=9)

    def test_meets_absorbs_float_error_only(self):
        self.assertTrue(meets(40.0, 40.0))
        self.assertFalse(meets(39.0, 40.0))


class TestAssessment(unittest.TestCase):
    def test_complete_chain_is_ready(self):
        report = assess_equipment_set(full_chain())
        self.assertEqual(report["verdict"], VERDICT_READY)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["missing_roles"], [])

    def test_missing_amplifier_is_a_finding(self):
        report = assess_equipment_set([source(), loop()])
        self.assertEqual(report["verdict"], VERDICT_INCOMPLETE)
        self.assertEqual(report["missing_roles"], [ROLE_AMPLIFIER])
        self.assertIsNone(report["coverage"])

    def test_duplicate_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set([source(), source(), amplifier(), loop()])

    def test_lapsed_calibration_is_a_finding(self):
        report = assess_equipment_set(
            full_chain(amplifier=amplifier(calibration_days_remaining=-3.0))
        )
        self.assertEqual(report["verdict"], VERDICT_INCOMPLETE)
        self.assertTrue(any("calibration lapsed" in f for f in report["findings"]))

    def test_calibration_expiring_soon_is_a_limitation(self):
        report = assess_equipment_set(
            full_chain(loop=loop(calibration_days_remaining=8.0))
        )
        self.assertEqual(report["verdict"], VERDICT_READY)
        self.assertTrue(any("expires in" in n for n in report["limitations"]))

    def test_band_gap_is_a_finding(self):
        report = assess_equipment_set(full_chain(loop=loop(frequency_min_hz=500.0)))
        self.assertEqual(report["verdict"], VERDICT_INCOMPLETE)
        self.assertTrue(any("not covered" in f for f in report["findings"]))

    def test_loop_current_reaches_the_wanted_flux_density(self):
        report = assess_equipment_set(full_chain(), required_flux_density_t=1.0e-6)
        self.assertAlmostEqual(
            axial_flux_density_tesla(
                report["loop_current_a"], standoff_m=DEFAULT_STANDOFF_M
            ),
            1.0e-6,
            places=15,
        )

    def test_loop_under_rated_for_the_wanted_field_is_a_finding(self):
        report = assess_equipment_set(
            full_chain(loop=loop(rated_current_a=1.0e-4)),
            required_flux_density_t=1.0e-6,
        )
        self.assertTrue(any("cannot carry" in f for f in report["findings"]))

    def test_weak_amplifier_gain_is_a_finding(self):
        report = assess_equipment_set(
            full_chain(amplifier=amplifier(gain_db=0.01)),
            required_flux_density_t=1.0e-4,
        )
        self.assertTrue(any("falls short" in f for f in report["findings"]))

    def test_amplifier_ceiling_below_the_drive_is_a_finding(self):
        report = assess_equipment_set(
            full_chain(amplifier=amplifier(max_output_dbm=-40.0)),
            required_flux_density_t=1.0e-4,
        )
        self.assertTrue(any("tops out" in f for f in report["findings"]))

    def test_thin_amplifier_headroom_is_a_limitation(self):
        chain = full_chain()
        baseline = assess_equipment_set(chain)
        tight = assess_equipment_set(
            full_chain(
                amplifier=amplifier(max_output_dbm=baseline["loop_drive_dbm"] + 1.0)
            )
        )
        self.assertEqual(tight["verdict"], VERDICT_READY)
        self.assertTrue(any("headroom" in n for n in tight["limitations"]))

    def test_drive_level_is_derived_at_the_top_of_the_band(self):
        report = assess_equipment_set(full_chain())
        self.assertAlmostEqual(
            report["loop_geometry"]["tune_frequency_hz"], DEFAULT_BAND_HZ[1], places=9
        )

    def test_an_explicit_worst_case_frequency_is_honoured(self):
        report = assess_equipment_set(full_chain(), worst_case_frequency_hz=1.0e3)
        self.assertAlmostEqual(
            report["loop_geometry"]["tune_frequency_hz"], 1.0e3, places=9
        )

    def test_required_gain_is_reported(self):
        report = assess_equipment_set(full_chain())
        self.assertAlmostEqual(
            report["required_gain_db"], report["loop_drive_dbm"] - 10.0, places=9
        )

    def test_roles_present_are_reported_in_a_stable_order(self):
        report = assess_equipment_set(full_chain())
        self.assertEqual(
            report["roles_present"], sorted([ROLE_SOURCE, ROLE_AMPLIFIER, ROLE_LOOP])
        )

    def test_zero_wanted_flux_density_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(full_chain(), required_flux_density_t=0.0)

    def test_negative_standoff_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(full_chain(), standoff_m=-0.05)

    def test_non_list_chain_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set({"role": ROLE_SOURCE})


if __name__ == "__main__":
    unittest.main()
