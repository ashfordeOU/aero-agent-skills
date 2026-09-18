#!/usr/bin/env python3
"""Gate 3 contract test for e2007-low-frequency-conducted-emission-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_low_frequency_conducted_emission_equipment.py
"""

import unittest

from e2007_low_frequency_conducted_emission_equipment_logic import (
    DEFAULT_BAND_HZ,
    DEFAULT_MIN_TRANSFER_IMPEDANCE_OHM,
    REQUIRED_ROLES,
    ROLE_PROBE,
    ROLE_RECEIVER,
    ROLE_SOURCE,
    VERDICT_INCOMPLETE,
    VERDICT_READY,
    assess_equipment_set,
    band_decades,
    band_overlap,
    chain_coverage,
    limiting_instrument,
    meets,
    normalize_role,
    system_check_drive_dbm,
    uncovered_sub_bands,
    validate_band,
    validate_instrument,
)


def receiver(**over):
    record = {
        "role": ROLE_RECEIVER,
        "frequency_min_hz": 10.0,
        "frequency_max_hz": 1.0e6,
        "calibration_days_remaining": 180.0,
    }
    record.update(over)
    return record


def probe(**over):
    record = {
        "role": ROLE_PROBE,
        "frequency_min_hz": 20.0,
        "frequency_max_hz": 2.0e5,
        "calibration_days_remaining": 200.0,
        "transfer_impedance_ohm": 5.0,
        "rated_current_a": 10.0,
    }
    record.update(over)
    return record


def source(**over):
    record = {
        "role": ROLE_SOURCE,
        "frequency_min_hz": 1.0,
        "frequency_max_hz": 1.0e7,
        "calibration_days_remaining": 365.0,
        "max_output_dbm": 13.0,
    }
    record.update(over)
    return record


def full_set(**over):
    records = {"receiver": receiver(), "probe": probe(), "source": source()}
    records.update(over)
    return [records["receiver"], records["probe"], records["source"]]


class TestRoleNormalization(unittest.TestCase):
    def test_every_required_role_normalizes(self):
        for role in REQUIRED_ROLES:
            self.assertEqual(normalize_role(role.upper()), role)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_role("  current-probe "), ROLE_PROBE)

    def test_unrecognized_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role("spectrum-camera")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role(7)


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

    def test_decade_width_of_the_default_band(self):
        self.assertAlmostEqual(band_decades((100.0, 100000.0)), 3.0, places=9)


class TestInstrumentValidation(unittest.TestCase):
    def test_receiver_normalizes(self):
        record = validate_instrument(receiver())
        self.assertEqual(record["role"], ROLE_RECEIVER)
        self.assertTrue(record["calibration_current"])

    def test_probe_carries_its_extra_fields(self):
        record = validate_instrument(probe())
        self.assertAlmostEqual(record["transfer_impedance_ohm"], 5.0)
        self.assertAlmostEqual(record["rated_current_a"], 10.0)

    def test_source_carries_its_output_ceiling(self):
        record = validate_instrument(source())
        self.assertAlmostEqual(record["max_output_dbm"], 13.0)

    def test_lapsed_calibration_is_recorded_not_raised(self):
        record = validate_instrument(receiver(calibration_days_remaining=-4.0))
        self.assertFalse(record["calibration_current"])

    def test_probe_without_transfer_impedance_rejected(self):
        record = probe()
        del record["transfer_impedance_ohm"]
        with self.assertRaises(ValueError):
            validate_instrument(record)

    def test_zero_transfer_impedance_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(probe(transfer_impedance_ohm=0.0))

    def test_negative_rated_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument(probe(rated_current_a=-1.0))

    def test_source_without_output_ceiling_rejected(self):
        record = source()
        del record["max_output_dbm"]
        with self.assertRaises(ValueError):
            validate_instrument(record)

    def test_boolean_field_rejected_as_numeric(self):
        with self.assertRaises(ValueError):
            validate_instrument(receiver(frequency_min_hz=True))

    def test_non_mapping_instrument_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument("an EMI receiver")


class TestCoverage(unittest.TestCase):
    def test_overlap_of_two_bands(self):
        low, high = band_overlap((10.0, 1.0e6), (30.0, 1.0e5))
        self.assertAlmostEqual(low, 30.0)
        self.assertAlmostEqual(high, 1.0e5)

    def test_disjoint_bands_have_no_overlap(self):
        self.assertIsNone(band_overlap((10.0, 100.0), (200.0, 300.0)))

    def test_touching_bands_have_no_usable_overlap(self):
        self.assertIsNone(band_overlap((10.0, 100.0), (100.0, 300.0)))

    def test_full_chain_covers_the_required_band(self):
        report = chain_coverage(full_set())
        self.assertEqual(report["gaps_hz"], [])
        self.assertAlmostEqual(
            report["covered_decades"], report["required_decades"], places=9
        )

    def test_probe_that_starts_late_opens_a_low_gap(self):
        report = chain_coverage(full_set(probe=probe(frequency_min_hz=150.0)))
        self.assertEqual(len(report["gaps_hz"]), 1)
        self.assertAlmostEqual(report["gaps_hz"][0][0], 30.0)
        self.assertAlmostEqual(report["gaps_hz"][0][1], 150.0)

    def test_receiver_that_stops_early_opens_a_high_gap(self):
        report = chain_coverage(full_set(receiver=receiver(frequency_max_hz=5.0e4)))
        self.assertEqual(len(report["gaps_hz"]), 1)
        self.assertAlmostEqual(report["gaps_hz"][0][0], 5.0e4)

    def test_both_edges_can_be_uncovered_at_once(self):
        report = chain_coverage(
            full_set(probe=probe(frequency_min_hz=100.0, frequency_max_hz=5.0e4))
        )
        self.assertEqual(len(report["gaps_hz"]), 2)

    def test_disjoint_instrument_leaves_the_whole_band_uncovered(self):
        report = chain_coverage(
            full_set(probe=probe(frequency_min_hz=1.0e6, frequency_max_hz=1.0e7))
        )
        self.assertIsNone(report["coverage_hz"])
        self.assertAlmostEqual(report["covered_decades"], 0.0)

    def test_uncovered_sub_bands_of_a_missing_coverage(self):
        gaps = uncovered_sub_bands((30.0, 1.0e5), None)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1], 1.0e5)

    def test_empty_instrument_list_rejected(self):
        with self.assertRaises(ValueError):
            chain_coverage([])


class TestLimitingInstrument(unittest.TestCase):
    def test_narrowest_instrument_is_the_limit(self):
        report = limiting_instrument(
            full_set(probe=probe(frequency_min_hz=300.0, frequency_max_hz=3.0e4))
        )
        self.assertEqual(report["role"], ROLE_PROBE)

    def test_a_chain_with_no_loss_reports_zero_lost_decades(self):
        report = limiting_instrument(full_set())
        self.assertAlmostEqual(report["lost_decades"], 0.0, places=9)

    def test_tie_resolves_to_the_clause_role_order(self):
        report = limiting_instrument(
            full_set(
                receiver=receiver(frequency_min_hz=300.0),
                probe=probe(frequency_min_hz=300.0),
            )
        )
        self.assertEqual(report["role"], ROLE_RECEIVER)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            limiting_instrument([])


class TestDriveLevel(unittest.TestCase):
    def test_drive_level_of_a_ten_milliamp_check(self):
        # 0.01 A through 5 ohm is 50 mV, which is 0.05 mW in 50 ohm.
        self.assertAlmostEqual(system_check_drive_dbm(0.01, 5.0), -13.0102999566, places=7)

    def test_doubling_the_current_adds_six_decibels(self):
        low = system_check_drive_dbm(0.01, 5.0)
        high = system_check_drive_dbm(0.02, 5.0)
        self.assertAlmostEqual(high - low, 6.02059991328, places=7)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            system_check_drive_dbm(0.0, 5.0)

    def test_zero_transfer_impedance_rejected(self):
        with self.assertRaises(ValueError):
            system_check_drive_dbm(0.01, 0.0)

    def test_zero_system_impedance_rejected(self):
        with self.assertRaises(ValueError):
            system_check_drive_dbm(0.01, 5.0, system_impedance_ohm=0.0)

    def test_meets_absorbs_float_error_only(self):
        self.assertTrue(meets(13.0, 13.0))
        self.assertFalse(meets(12.0, 13.0))


class TestAssessment(unittest.TestCase):
    def test_complete_set_is_ready(self):
        report = assess_equipment_set(full_set())
        self.assertEqual(report["verdict"], VERDICT_READY)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["missing_roles"], [])

    def test_missing_probe_is_a_finding(self):
        report = assess_equipment_set([receiver(), source()])
        self.assertEqual(report["verdict"], VERDICT_INCOMPLETE)
        self.assertEqual(report["missing_roles"], [ROLE_PROBE])
        self.assertIsNone(report["coverage"])

    def test_duplicate_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set([receiver(), receiver(), probe(), source()])

    def test_lapsed_calibration_is_a_finding(self):
        report = assess_equipment_set(
            full_set(receiver=receiver(calibration_days_remaining=-2.0))
        )
        self.assertEqual(report["verdict"], VERDICT_INCOMPLETE)
        self.assertTrue(any("calibration lapsed" in f for f in report["findings"]))

    def test_calibration_expiring_soon_is_a_limitation(self):
        report = assess_equipment_set(
            full_set(probe=probe(calibration_days_remaining=12.0))
        )
        self.assertEqual(report["verdict"], VERDICT_READY)
        self.assertTrue(any("expires in" in l for l in report["limitations"]))

    def test_band_gap_is_a_finding(self):
        report = assess_equipment_set(full_set(probe=probe(frequency_min_hz=400.0)))
        self.assertEqual(report["verdict"], VERDICT_INCOMPLETE)
        self.assertTrue(
            any("not covered" in f for f in report["findings"])
        )

    def test_weak_transfer_impedance_is_a_finding(self):
        report = assess_equipment_set(
            full_set(probe=probe(transfer_impedance_ohm=0.2))
        )
        self.assertTrue(
            any("transfer impedance" in f for f in report["findings"])
        )

    def test_transfer_impedance_exactly_at_the_floor_is_accepted(self):
        report = assess_equipment_set(
            full_set(
                probe=probe(transfer_impedance_ohm=DEFAULT_MIN_TRANSFER_IMPEDANCE_OHM),
                source=source(max_output_dbm=30.0),
            )
        )
        self.assertFalse(
            any("transfer impedance" in f for f in report["findings"])
        )

    def test_probe_under_rated_for_the_harness_is_a_finding(self):
        report = assess_equipment_set(full_set(), harness_current_a=25.0)
        self.assertTrue(any("cannot clamp" in f for f in report["findings"]))

    def test_source_too_weak_for_the_system_check_is_a_finding(self):
        report = assess_equipment_set(
            full_set(source=source(max_output_dbm=-60.0)),
            system_check_current_a=0.1,
        )
        self.assertTrue(any("tops out" in f for f in report["findings"]))

    def test_drive_level_is_reported_for_a_complete_set(self):
        report = assess_equipment_set(full_set(), system_check_current_a=0.01)
        self.assertAlmostEqual(
            report["system_check_drive_dbm"], -13.0102999566, places=7
        )

    def test_roles_present_are_reported_in_a_stable_order(self):
        report = assess_equipment_set(full_set())
        self.assertEqual(
            report["roles_present"],
            sorted([ROLE_RECEIVER, ROLE_PROBE, ROLE_SOURCE]),
        )

    def test_zero_harness_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(full_set(), harness_current_a=0.0)

    def test_zero_system_check_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(full_set(), system_check_current_a=0.0)

    def test_non_list_instrument_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set({"role": ROLE_RECEIVER})


if __name__ == "__main__":
    unittest.main()
