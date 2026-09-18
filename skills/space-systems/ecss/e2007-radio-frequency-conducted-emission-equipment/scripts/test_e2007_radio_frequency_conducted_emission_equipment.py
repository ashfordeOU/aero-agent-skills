#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radio-frequency-conducted-emission-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radio_frequency_conducted_emission_equipment.py
"""

import unittest

from e2007_radio_frequency_conducted_emission_equipment_logic import (
    DEFAULT_CAMPAIGN_DAYS,
    DEFAULT_METHOD_BAND_HZ,
    REQUIRED_ROLES,
    STATUS_NOT_READY,
    STATUS_READY,
    apply_probe_factor,
    assess_equipment_set,
    bounding_instruments,
    injection_margin_db,
    instrument_covers_band,
    missing_roles,
    normalize_role,
    span_intersection,
    validate_instrument,
    validate_method_band,
)

SPANS = {
    "measurement-receiver": (9.0e3, 1.0e9),
    "current-probe": (1.0e6, 400.0e6),
    "signal-generator": (1.0e5, 3.0e9),
    "data-recorder": (1.0e3, 2.0e9),
    "oscilloscope": (1.0e2, 5.0e8),
}


def full_set(**over):
    items = []
    for role in REQUIRED_ROLES:
        low, high = SPANS[role]
        record = {
            "role": role,
            "identifier": "%s-01" % role,
            "span_low_hz": low,
            "span_high_hz": high,
            "calibration_valid_days": 180.0,
        }
        record.update(over.get(role, {}))
        items.append(record)
    return items


class TestMethodBand(unittest.TestCase):
    def test_default_band_validates(self):
        low, high = validate_method_band()
        self.assertAlmostEqual(low, DEFAULT_METHOD_BAND_HZ[0], places=9)
        self.assertAlmostEqual(high, DEFAULT_METHOD_BAND_HZ[1], places=9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((100.0e6, 2.0e6))

    def test_zero_low_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((0.0, 100.0e6))


class TestRoleNormalization(unittest.TestCase):
    def test_every_required_role_normalizes(self):
        for role in REQUIRED_ROLES:
            self.assertEqual(normalize_role(" %s " % role.upper()), role)

    def test_unrecognized_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role("anechoic-chamber")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_role(None)


class TestInstrumentValidation(unittest.TestCase):
    def test_good_instrument_normalizes(self):
        record = validate_instrument(full_set()[0])
        self.assertEqual(record["role"], "measurement-receiver")
        self.assertAlmostEqual(record["span_hz"][0], 9.0e3, places=9)
        self.assertAlmostEqual(record["calibration_valid_days"], 180.0, places=9)

    def test_inverted_span_rejected(self):
        item = full_set()[0]
        item["span_high_hz"] = item["span_low_hz"] / 2.0
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_zero_span_low_rejected(self):
        item = full_set()[0]
        item["span_low_hz"] = 0.0
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_negative_calibration_days_rejected(self):
        item = full_set()[0]
        item["calibration_valid_days"] = -1.0
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_blank_identifier_rejected(self):
        item = full_set()[0]
        item["identifier"] = "   "
        with self.assertRaises(ValueError):
            validate_instrument(item)

    def test_non_mapping_instrument_rejected(self):
        with self.assertRaises(ValueError):
            validate_instrument("a spectrum analyser")

    def test_missing_span_field_rejected(self):
        item = full_set()[0]
        del item["span_high_hz"]
        with self.assertRaises(ValueError):
            validate_instrument(item)


class TestBandCoverage(unittest.TestCase):
    def test_wide_instrument_covers_the_band(self):
        receiver = [i for i in full_set() if i["role"] == "measurement-receiver"][0]
        self.assertTrue(instrument_covers_band(receiver))

    def test_narrow_instrument_does_not_cover_the_band(self):
        probe = [i for i in full_set() if i["role"] == "current-probe"][0]
        probe["span_high_hz"] = 30.0e6
        self.assertFalse(instrument_covers_band(probe))

    def test_span_edge_equal_to_the_band_edge_still_covers(self):
        probe = [i for i in full_set() if i["role"] == "current-probe"][0]
        probe["span_low_hz"] = DEFAULT_METHOD_BAND_HZ[0]
        probe["span_high_hz"] = DEFAULT_METHOD_BAND_HZ[1]
        record = validate_instrument(probe)
        self.assertAlmostEqual(
            record["span_hz"][0], DEFAULT_METHOD_BAND_HZ[0], places=9
        )
        self.assertTrue(instrument_covers_band(probe))


class TestSpanIntersection(unittest.TestCase):
    def test_intersection_is_the_tightest_pair_of_edges(self):
        records = [validate_instrument(i) for i in full_set()]
        low, high = span_intersection(records)
        self.assertAlmostEqual(low, 1.0e6, places=9)
        self.assertAlmostEqual(high, 400.0e6, places=9)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            span_intersection([])

    def test_disjoint_spans_rejected(self):
        records = [validate_instrument(i) for i in full_set()]
        records[0]["span_hz"] = (1.0e9, 2.0e9)
        with self.assertRaises(ValueError):
            span_intersection(records)

    def test_bounding_instruments_name_both_edges(self):
        records = [validate_instrument(i) for i in full_set()]
        bounds = bounding_instruments(records)
        self.assertEqual(bounds["sets_low_edge"], "current-probe")
        self.assertEqual(bounds["sets_high_edge"], "current-probe")

    def test_bounding_instrument_changes_with_a_narrower_item(self):
        items = full_set(oscilloscope={"span_high_hz": 100.0e6})
        records = [validate_instrument(i) for i in items]
        bounds = bounding_instruments(records)
        self.assertEqual(bounds["sets_high_edge"], "oscilloscope")


class TestProbeFactorAndInjection(unittest.TestCase):
    def test_probe_factor_converts_a_reading_to_a_current(self):
        self.assertAlmostEqual(apply_probe_factor(60.0, 14.0), 46.0, places=9)

    def test_cable_loss_is_added_back(self):
        self.assertAlmostEqual(
            apply_probe_factor(60.0, 14.0, cable_loss_db=1.5), 47.5, places=9
        )

    def test_negative_cable_loss_rejected(self):
        with self.assertRaises(ValueError):
            apply_probe_factor(60.0, 14.0, cable_loss_db=-1.0)

    def test_non_numeric_transfer_impedance_rejected(self):
        with self.assertRaises(ValueError):
            apply_probe_factor(60.0, "fourteen")

    def test_injection_margin_is_output_minus_requirement(self):
        self.assertAlmostEqual(injection_margin_db(-10.0, -20.0), 10.0, places=9)

    def test_injection_margin_can_be_negative(self):
        self.assertAlmostEqual(injection_margin_db(-30.0, -20.0), -10.0, places=9)


class TestRoleCompleteness(unittest.TestCase):
    def test_full_set_has_no_missing_roles(self):
        records = [validate_instrument(i) for i in full_set()]
        self.assertEqual(missing_roles(records), ())

    def test_dropped_role_is_reported(self):
        records = [
            validate_instrument(i) for i in full_set() if i["role"] != "oscilloscope"
        ]
        self.assertEqual(missing_roles(records), ("oscilloscope",))


class TestEquipmentAssessment(unittest.TestCase):
    def test_full_valid_set_is_ready(self):
        report = assess_equipment_set(full_set())
        self.assertEqual(report["status"], STATUS_READY)
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["instruments"]), len(REQUIRED_ROLES))

    def test_missing_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(
                [i for i in full_set() if i["role"] != "data-recorder"]
            )

    def test_duplicate_role_rejected(self):
        items = full_set()
        items.append(dict(items[0]))
        with self.assertRaises(ValueError):
            assess_equipment_set(items)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set([])

    def test_non_list_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set({"role": "current-probe"})

    def test_narrow_probe_blocks_readiness(self):
        report = assess_equipment_set(full_set(**{"current-probe": {"span_high_hz": 30.0e6}}))
        self.assertEqual(report["status"], STATUS_NOT_READY)
        self.assertTrue(any("current-probe span" in f for f in report["findings"]))

    def test_lapsing_calibration_blocks_readiness(self):
        report = assess_equipment_set(
            full_set(**{"oscilloscope": {"calibration_valid_days": 5.0}})
        )
        self.assertEqual(report["status"], STATUS_NOT_READY)
        self.assertTrue(any("calibration lapses" in f for f in report["findings"]))

    def test_calibration_valid_through_the_campaign_is_accepted(self):
        report = assess_equipment_set(
            full_set(
                **{
                    "oscilloscope": {
                        "calibration_valid_days": float(DEFAULT_CAMPAIGN_DAYS)
                    }
                }
            )
        )
        self.assertEqual(report["status"], STATUS_READY)
        self.assertEqual(report["limitations"], [])

    def test_zero_campaign_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(full_set(), campaign_days=0)

    def test_bounds_name_the_limiting_instrument(self):
        report = assess_equipment_set(full_set())
        self.assertEqual(report["bounds"]["sets_low_edge"], "current-probe")

    def test_instruments_are_reported_in_a_stable_order(self):
        report = assess_equipment_set(full_set())
        self.assertEqual(
            [i["role"] for i in report["instruments"]], sorted(REQUIRED_ROLES)
        )

    def test_weak_generator_is_a_finding(self):
        report = assess_equipment_set(
            full_set(), generator_output_dbm=-30.0, required_injection_dbm=-20.0
        )
        self.assertEqual(report["status"], STATUS_NOT_READY)
        self.assertAlmostEqual(report["injection"]["margin_db"], -10.0, places=9)

    def test_generator_with_no_headroom_is_a_limitation(self):
        report = assess_equipment_set(
            full_set(), generator_output_dbm=-20.0, required_injection_dbm=-20.0
        )
        self.assertEqual(report["status"], STATUS_READY)
        self.assertAlmostEqual(report["injection"]["margin_db"], 0.0, places=9)
        self.assertTrue(any("no headroom" in l for l in report["limitations"]))

    def test_half_declared_injection_check_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(full_set(), generator_output_dbm=-20.0)

    def test_narrower_declared_band_can_rescue_a_narrow_probe(self):
        report = assess_equipment_set(
            full_set(**{"current-probe": {"span_high_hz": 30.0e6}}),
            band=(2.0e6, 30.0e6),
        )
        self.assertEqual(report["status"], STATUS_READY)


if __name__ == "__main__":
    unittest.main()
