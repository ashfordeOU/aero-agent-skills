#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-emission-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_emission_equipment.py
"""

import unittest

from e2007_radiated_electric_emission_equipment_logic import (
    ANTENNA_ROLE,
    DEFAULT_CAMPAIGN_DAYS,
    DEFAULT_METHOD_BAND_HZ,
    POLARIZATIONS,
    ROLES,
    SINGLETON_ROLES,
    STATUS_NOT_READY,
    STATUS_READY,
    antennas_for_polarization,
    assess_equipment_set,
    band_gaps,
    bounding_antennas,
    calibration_shortfall_days,
    field_strength_dbuv_m,
    missing_roles,
    normalize_polarization,
    normalize_role,
    validate_instrument,
    validate_instrument_set,
    validate_method_band,
)

BOTH = list(POLARIZATIONS)


def antenna(identifier, low, high, planes=None, factor=12.0, days=90.0):
    return {
        "id": identifier,
        "role": ANTENNA_ROLE,
        "span_low_hz": low,
        "span_high_hz": high,
        "polarizations": list(BOTH if planes is None else planes),
        "antenna_factor_db_per_m": factor,
        "calibration_valid_days": days,
    }


def clean_set():
    return [
        {
            "id": "RX-1",
            "role": "measurement-receiver",
            "span_low_hz": 20.0e6,
            "span_high_hz": 26.0e9,
            "calibration_valid_days": 120.0,
        },
        {
            "id": "REC-1",
            "role": "data-recorder",
            "span_low_hz": 20.0e6,
            "span_high_hz": 26.0e9,
            "calibration_valid_days": 120.0,
        },
        antenna("BICON-1", 25.0e6, 300.0e6),
        antenna("LOGP-1", 300.0e6, 2.0e9),
        antenna("HORN-1", 2.0e9, 20.0e9),
    ]


class TestMethodBand(unittest.TestCase):
    def test_default_band_validates(self):
        low, high = validate_method_band()
        self.assertAlmostEqual(low, DEFAULT_METHOD_BAND_HZ[0], places=9)
        self.assertAlmostEqual(high, DEFAULT_METHOD_BAND_HZ[1], places=9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((18.0e9, 30.0e6))

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band("30MHz-18GHz")


class TestRolesAndPolarizations(unittest.TestCase):
    def test_every_recognized_role_normalizes(self):
        for role in ROLES:
            self.assertEqual(normalize_role(role.upper()), role)

    def test_unrecognized_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role("current-probe")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role(None)

    def test_polarization_normalizes(self):
        self.assertEqual(normalize_polarization(" Vertical "), "vertical")

    def test_unrecognized_polarization_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarization("slant-45")


class TestInstrumentValidation(unittest.TestCase):
    def test_clean_receiver_validates(self):
        record = validate_instrument(clean_set()[0])
        self.assertEqual(record["role"], "measurement-receiver")
        self.assertAlmostEqual(record["span_high_hz"], 26.0e9, places=9)

    def test_antenna_keeps_its_polarizations_in_canonical_order(self):
        record = validate_instrument(antenna("A", 1.0e8, 2.0e8, ["horizontal", "vertical"]))
        self.assertEqual(record["polarizations"], POLARIZATIONS)

    def test_antenna_without_polarizations_rejected(self):
        item = antenna("A", 1.0e8, 2.0e8)
        item["polarizations"] = []
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_antenna_without_antenna_factor_rejected(self):
        item = antenna("A", 1.0e8, 2.0e8)
        del item["antenna_factor_db_per_m"]
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_duplicate_polarization_on_one_antenna_rejected(self):
        item = antenna("A", 1.0e8, 2.0e8, ["vertical", "vertical"])
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_blank_identifier_rejected(self):
        item = antenna("   ", 1.0e8, 2.0e8)
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_inverted_span_rejected(self):
        item = antenna("A", 2.0e8, 1.0e8)
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_negative_calibration_window_rejected(self):
        item = antenna("A", 1.0e8, 2.0e8)
        item["calibration_valid_days"] = -1.0
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_boolean_span_rejected(self):
        item = antenna("A", 1.0e8, 2.0e8)
        item["span_low_hz"] = True
        with self.assertRaises(ValueError):
            validate_instrument(item)


class TestSetValidation(unittest.TestCase):
    def test_clean_set_validates(self):
        self.assertEqual(len(validate_instrument_set(clean_set())), 5)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument_set([])

    def test_duplicate_singleton_role_rejected(self):
        items = clean_set()
        extra = dict(items[0])
        extra["id"] = "RX-2"
        items.append(extra)
        with self.assertRaises(ValueError):
            validate_instrument_set(items)

    def test_duplicate_identifier_rejected(self):
        items = clean_set()
        items.append(antenna("HORN-1", 2.0e9, 20.0e9))
        with self.assertRaises(ValueError):
            validate_instrument_set(items)

    def test_several_antennas_are_allowed(self):
        records = validate_instrument_set(clean_set())
        self.assertEqual(
            len([r for r in records if r["role"] == ANTENNA_ROLE]), 3
        )

    def test_missing_roles_reports_what_is_absent(self):
        records = validate_instrument_set(clean_set()[:1])
        self.assertIn("data-recorder", missing_roles(records))
        self.assertIn(ANTENNA_ROLE, missing_roles(records))

    def test_complete_set_is_missing_nothing(self):
        self.assertEqual(missing_roles(validate_instrument_set(clean_set())), ())

    def test_singleton_roles_are_a_subset_of_roles(self):
        for role in SINGLETON_ROLES:
            self.assertIn(role, ROLES)


class TestBandTiling(unittest.TestCase):
    def test_contiguous_antennas_leave_no_gap(self):
        records = validate_instrument_set(clean_set())
        usable = antennas_for_polarization(records, "vertical")
        self.assertEqual(band_gaps(usable), ())

    def test_a_hole_between_antennas_is_reported(self):
        items = clean_set()
        items[3]["span_low_hz"] = 500.0e6
        records = validate_instrument_set(items)
        gaps = band_gaps(antennas_for_polarization(records, "vertical"))
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 300.0e6, places=9)
        self.assertAlmostEqual(gaps[0][1], 500.0e6, places=9)

    def test_set_stopping_below_the_upper_edge_is_reported(self):
        items = clean_set()
        items[4]["span_high_hz"] = 10.0e9
        records = validate_instrument_set(items)
        gaps = band_gaps(antennas_for_polarization(records, "vertical"))
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1], 18.0e9, places=9)

    def test_set_starting_above_the_lower_edge_is_reported(self):
        items = clean_set()
        items[2]["span_low_hz"] = 80.0e6
        records = validate_instrument_set(items)
        gaps = band_gaps(antennas_for_polarization(records, "vertical"))
        self.assertAlmostEqual(gaps[0][0], 30.0e6, places=9)

    def test_spans_meeting_exactly_leave_no_gap(self):
        records = validate_instrument_set(
            [antenna("A", 30.0e6, 1.0e9), antenna("B", 1.0e9, 18.0e9)]
        )
        self.assertEqual(band_gaps(records), ())

    def test_overlapping_antennas_leave_no_gap(self):
        records = validate_instrument_set(
            [antenna("A", 20.0e6, 2.0e9), antenna("B", 1.0e9, 20.0e9)]
        )
        self.assertEqual(band_gaps(records), ())

    def test_bounding_antennas_name_both_edges(self):
        records = validate_instrument_set(clean_set())
        bounds = bounding_antennas(antennas_for_polarization(records, "horizontal"))
        self.assertEqual(bounds["low_edge_item"], "BICON-1")
        self.assertEqual(bounds["high_edge_item"], "HORN-1")

    def test_bounding_antennas_needs_at_least_one(self):
        with self.assertRaises(ValueError):
            bounding_antennas([])

    def test_one_polarization_only_narrows_the_usable_set(self):
        items = clean_set()
        items[4]["polarizations"] = ["vertical"]
        records = validate_instrument_set(items)
        self.assertEqual(len(antennas_for_polarization(records, "horizontal")), 2)


class TestAntennaFactor(unittest.TestCase):
    def test_factor_and_cable_loss_are_added_to_the_reading(self):
        self.assertAlmostEqual(
            field_strength_dbuv_m(30.0, 12.5, 1.5), 44.0, places=9
        )

    def test_cable_loss_defaults_to_zero(self):
        self.assertAlmostEqual(field_strength_dbuv_m(30.0, 12.5), 42.5, places=9)

    def test_negative_cable_loss_rejected(self):
        with self.assertRaises(ValueError):
            field_strength_dbuv_m(30.0, 12.5, -1.0)

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            field_strength_dbuv_m("30 dBuV", 12.5)


class TestCalibration(unittest.TestCase):
    def test_certificate_outlasting_the_campaign_has_no_shortfall(self):
        self.assertAlmostEqual(calibration_shortfall_days(120.0, 30.0), 0.0, places=9)

    def test_certificate_expiring_early_reports_the_shortfall(self):
        self.assertAlmostEqual(calibration_shortfall_days(18.0, 30.0), 12.0, places=9)

    def test_certificate_ending_on_the_last_day_has_no_shortfall(self):
        self.assertAlmostEqual(
            calibration_shortfall_days(DEFAULT_CAMPAIGN_DAYS, DEFAULT_CAMPAIGN_DAYS),
            0.0,
            places=9,
        )

    def test_non_positive_campaign_rejected(self):
        with self.assertRaises(ValueError):
            calibration_shortfall_days(30.0, 0.0)


class TestReadiness(unittest.TestCase):
    def test_clean_set_is_ready(self):
        report = assess_equipment_set(clean_set())
        self.assertEqual(report["status"], STATUS_READY)
        self.assertEqual(report["findings"], [])

    def test_report_names_the_receiver_and_the_recorder(self):
        report = assess_equipment_set(clean_set())
        self.assertEqual(report["receiver"], "RX-1")
        self.assertEqual(report["recorder"], "REC-1")

    def test_missing_recorder_is_refused_outright(self):
        items = [item for item in clean_set() if item["id"] != "REC-1"]
        with self.assertRaises(ValueError):
            assess_equipment_set(items)

    def test_missing_antenna_is_refused_outright(self):
        items = [item for item in clean_set() if item["role"] != ANTENNA_ROLE]
        with self.assertRaises(ValueError):
            assess_equipment_set(items)

    def test_antenna_hole_blocks_readiness(self):
        items = clean_set()
        items[3]["span_low_hz"] = 500.0e6
        report = assess_equipment_set(items)
        self.assertEqual(report["status"], STATUS_NOT_READY)
        self.assertEqual(len(report["findings"]), 2)

    def test_one_plane_left_uncovered_blocks_readiness(self):
        items = clean_set()
        for item in items:
            if item["role"] == ANTENNA_ROLE:
                item["polarizations"] = ["vertical"]
        report = assess_equipment_set(items)
        self.assertEqual(report["status"], STATUS_NOT_READY)
        self.assertTrue(
            any("horizontal" in finding for finding in report["findings"])
        )

    def test_receiver_short_of_the_band_blocks_readiness(self):
        items = clean_set()
        items[0]["span_high_hz"] = 3.0e9
        report = assess_equipment_set(items)
        self.assertEqual(report["status"], STATUS_NOT_READY)

    def test_lapsing_calibration_blocks_readiness(self):
        items = clean_set()
        items[2]["calibration_valid_days"] = 10.0
        report = assess_equipment_set(items)
        self.assertEqual(report["status"], STATUS_NOT_READY)

    def test_calibration_ending_on_the_last_day_is_a_limitation(self):
        items = clean_set()
        items[2]["calibration_valid_days"] = DEFAULT_CAMPAIGN_DAYS
        report = assess_equipment_set(items)
        self.assertEqual(report["status"], STATUS_READY)
        self.assertEqual(len(report["limitations"]), 1)

    def test_coverage_is_reported_for_both_planes(self):
        report = assess_equipment_set(clean_set())
        self.assertEqual(sorted(report["polarization_coverage"]), sorted(POLARIZATIONS))

    def test_longer_campaign_can_turn_a_ready_set_not_ready(self):
        report = assess_equipment_set(clean_set(), campaign_days=200.0)
        self.assertEqual(report["status"], STATUS_NOT_READY)

    def test_non_positive_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(clean_set(), campaign_days=0.0)


if __name__ == "__main__":
    unittest.main()
