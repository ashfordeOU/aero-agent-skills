#!/usr/bin/env python3
"""Gate 3 contract test for e2001-test-bed-configuration (offline, stdlib)."""

import math
import unittest

from e2001_test_bed_configuration_logic import (
    GLOBAL_DETECTION,
    LOCAL_DETECTION,
    REL_TOL,
    assess_test_bed_configuration,
    categorize_bed_element,
    check_detection_coverage,
    check_electron_seeding,
    check_instrument_calibration,
    check_rf_chain_capability,
    check_vacuum_readiness,
    days_to_calibration_expiry,
    required_source_rating_w,
    summarize_families,
)

RUN_DATE = "2026-05-20"


def good_record(**overrides):
    record = {
        "elements": [
            "vacuum-chamber",
            "turbomolecular-pump",
            "rf-source",
            "travelling-wave-tube-amplifier",
            "directional-coupler",
            "power-meter",
            "spectrum-analyser",
            "vacuum-gauge",
            "ultraviolet-lamp",
            "forward-reverse-nulling",
            "electron-probe",
        ],
        "measured_pressure_pa": 2.0e-5,
        "required_pressure_pa": 1.0e-4,
        "bakeout_done": True,
        "instruments": [
            {"id": "PM-1", "type": "power-meter", "calibration_due": "2026-11-02"},
            {"id": "SA-1", "type": "spectrum-analyser", "calibration_due": "2026-06-30"},
            {"id": "VG-1", "type": "vacuum-gauge", "calibration_due": "2027-01-15"},
        ],
        "run_date": RUN_DATE,
        "source_rating_w": 400.0,
        "max_applied_power_w": 100.0,
        "run_margin_db": 3.0,
        "seeding_sources": [
            {"type": "ultraviolet-lamp", "active": True, "aimed_at_gap": True}
        ],
        "detection_methods": [
            {"type": "forward-reverse-nulling", "instrument_id": "PM-1"},
            {"type": "electron-probe", "instrument_id": None},
        ],
    }
    record.update(overrides)
    return record


class TestElementCategorization(unittest.TestCase):
    def test_vacuum_chamber_is_vacuum_system(self):
        self.assertEqual(categorize_bed_element("vacuum-chamber"), "vacuum-system")

    def test_amplifier_is_rf_chain(self):
        self.assertEqual(
            categorize_bed_element("travelling-wave-tube-amplifier"), "rf-chain"
        )

    def test_power_meter_is_instrumentation(self):
        self.assertEqual(categorize_bed_element("power-meter"), "instrumentation")

    def test_ultraviolet_lamp_is_electron_seeding(self):
        self.assertEqual(categorize_bed_element("ultraviolet-lamp"), "electron-seeding")

    def test_electron_probe_is_detection_method(self):
        self.assertEqual(categorize_bed_element("electron-probe"), "detection-method")

    def test_case_and_whitespace_are_normalized(self):
        self.assertEqual(categorize_bed_element("  RF-Source "), "rf-chain")

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            categorize_bed_element("coffee-machine")

    def test_blank_element_raises(self):
        with self.assertRaises(ValueError):
            categorize_bed_element("   ")

    def test_non_string_element_raises(self):
        with self.assertRaises(ValueError):
            categorize_bed_element(7)

    def test_summarize_groups_every_family(self):
        summary = summarize_families(["vacuum-chamber", "rf-source", "power-meter"])
        self.assertEqual(summary["vacuum-system"], ["vacuum-chamber"])
        self.assertEqual(summary["rf-chain"], ["rf-source"])
        self.assertEqual(summary["instrumentation"], ["power-meter"])
        self.assertEqual(summary["electron-seeding"], [])

    def test_summarize_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            summarize_families([])

    def test_summarize_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            summarize_families("vacuum-chamber")


class TestVacuumReadiness(unittest.TestCase):
    def test_pressure_below_limit_is_compliant(self):
        result = check_vacuum_readiness(1.0e-5, 1.0e-4, True)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_pressure_above_limit_is_a_finding(self):
        result = check_vacuum_readiness(5.0e-4, 1.0e-4, True)
        self.assertFalse(result["compliant"])
        self.assertIn("exceeds required level", result["findings"][0])

    def test_exact_limit_pressure_is_compliant(self):
        result = check_vacuum_readiness(1.0e-4, 1.0e-4, True)
        self.assertTrue(result["pressure_ok"])

    def test_limit_reached_as_a_sum_of_partial_pressures_is_compliant(self):
        # Summed residual-gas partial pressures land a few ULPs above 1e-4 in
        # binary floating point although the total is physically at the limit.
        measured = 1.0e-5 + 2.0e-5 + 3.0e-5 + 4.0e-5
        self.assertGreater(measured, 1.0e-4)
        result = check_vacuum_readiness(measured, 1.0e-4, True)
        self.assertTrue(result["pressure_ok"])
        self.assertTrue(result["compliant"])

    def test_missing_bakeout_is_a_finding_even_when_pressure_is_low(self):
        result = check_vacuum_readiness(1.0e-7, 1.0e-4, False)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["pressure_ok"])
        self.assertIn("bake-out", result["findings"][0])

    def test_measured_pressure_stored_as_float(self):
        result = check_vacuum_readiness(3.0e-5, 1.0e-4, True)
        self.assertAlmostEqual(result["measured_pressure_pa"], 3.0e-5, places=12)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_readiness(0.0, 1.0e-4, True)

    def test_negative_required_pressure_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_readiness(1.0e-5, -1.0e-4, True)

    def test_non_numeric_pressure_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_readiness("low", 1.0e-4, True)

    def test_non_boolean_bakeout_raises(self):
        with self.assertRaises(ValueError):
            check_vacuum_readiness(1.0e-5, 1.0e-4, "yes")


class TestCalibrationValidity(unittest.TestCase):
    def test_days_remaining_is_positive_before_expiry(self):
        self.assertEqual(days_to_calibration_expiry("2026-05-30", RUN_DATE), 10)

    def test_due_on_run_date_gives_zero_days(self):
        self.assertEqual(days_to_calibration_expiry(RUN_DATE, RUN_DATE), 0)

    def test_expired_certificate_gives_negative_days(self):
        self.assertEqual(days_to_calibration_expiry("2026-05-18", RUN_DATE), -2)

    def test_malformed_due_date_raises(self):
        with self.assertRaises(ValueError):
            days_to_calibration_expiry("20-05-2026", RUN_DATE)

    def test_non_string_run_date_raises(self):
        with self.assertRaises(ValueError):
            days_to_calibration_expiry("2026-05-30", 20260520)

    def test_all_in_date_instruments_are_compliant(self):
        result = check_instrument_calibration(good_record()["instruments"], RUN_DATE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["expired"], [])

    def test_certificate_expiring_on_the_run_date_is_still_valid(self):
        rows = [{"id": "PM-1", "type": "power-meter", "calibration_due": RUN_DATE}]
        result = check_instrument_calibration(rows, RUN_DATE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["instruments"][0]["days_remaining"], 0)

    def test_expired_instrument_is_named_in_the_finding(self):
        rows = [{"id": "SA-9", "type": "spectrum-analyser", "calibration_due": "2026-04-01"}]
        result = check_instrument_calibration(rows, RUN_DATE)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["expired"], ["SA-9"])
        self.assertIn("SA-9", result["findings"][0])

    def test_empty_instrument_list_raises(self):
        with self.assertRaises(ValueError):
            check_instrument_calibration([], RUN_DATE)

    def test_duplicate_instrument_id_raises(self):
        rows = [
            {"id": "PM-1", "type": "power-meter", "calibration_due": "2026-09-01"},
            {"id": "PM-1", "type": "power-meter", "calibration_due": "2026-10-01"},
        ]
        with self.assertRaises(ValueError):
            check_instrument_calibration(rows, RUN_DATE)

    def test_blank_instrument_id_raises(self):
        rows = [{"id": "  ", "type": "power-meter", "calibration_due": "2026-09-01"}]
        with self.assertRaises(ValueError):
            check_instrument_calibration(rows, RUN_DATE)

    def test_non_instrumentation_family_raises(self):
        rows = [{"id": "X-1", "type": "circulator", "calibration_due": "2026-09-01"}]
        with self.assertRaises(ValueError):
            check_instrument_calibration(rows, RUN_DATE)


class TestRfChainSizing(unittest.TestCase):
    def test_three_db_margin_doubles_the_required_rating(self):
        self.assertAlmostEqual(required_source_rating_w(100.0, 3.0), 199.526231, places=5)

    def test_zero_margin_returns_the_applied_power(self):
        self.assertAlmostEqual(required_source_rating_w(250.0, 0.0), 250.0, places=9)

    def test_ten_db_margin_is_a_factor_of_ten(self):
        self.assertAlmostEqual(required_source_rating_w(50.0, 10.0), 500.0, places=6)

    def test_sufficient_rating_is_compliant(self):
        result = check_rf_chain_capability(400.0, 100.0, 3.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["shortfall_w"], 0.0, places=9)

    def test_rating_exactly_at_the_requirement_is_compliant(self):
        required = required_source_rating_w(100.0, 3.0)
        result = check_rf_chain_capability(required, 100.0, 3.0)
        self.assertTrue(result["compliant"])

    def test_rating_a_few_ulps_under_the_requirement_is_still_compliant(self):
        required = required_source_rating_w(100.0, 3.0)
        nudged = math.nextafter(math.nextafter(required, 0.0), 0.0)
        self.assertLess(nudged, required)
        self.assertTrue(check_rf_chain_capability(nudged, 100.0, 3.0)["compliant"])

    def test_undersized_source_reports_the_shortfall(self):
        result = check_rf_chain_capability(150.0, 100.0, 3.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["shortfall_w"], 49.526231, places=5)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            required_source_rating_w(100.0, -1.0)

    def test_zero_applied_power_raises(self):
        with self.assertRaises(ValueError):
            required_source_rating_w(0.0, 3.0)

    def test_boolean_applied_power_raises(self):
        with self.assertRaises(ValueError):
            required_source_rating_w(True, 3.0)

    def test_infinite_margin_raises(self):
        with self.assertRaises(ValueError):
            required_source_rating_w(100.0, float("inf"))

    def test_negative_source_rating_raises(self):
        with self.assertRaises(ValueError):
            check_rf_chain_capability(-10.0, 100.0, 3.0)


class TestElectronSeeding(unittest.TestCase):
    def test_active_aimed_source_is_compliant(self):
        result = check_electron_seeding(
            [{"type": "radioactive-source", "active": True, "aimed_at_gap": True}]
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["active_sources"], ["radioactive-source"])

    def test_inactive_source_is_not_counted(self):
        result = check_electron_seeding(
            [{"type": "ultraviolet-lamp", "active": False, "aimed_at_gap": True}]
        )
        self.assertFalse(result["compliant"])
        self.assertIn("no active electron-seeding source", result["findings"][0])

    def test_source_not_aimed_at_the_gap_is_not_counted(self):
        result = check_electron_seeding(
            [{"type": "electron-gun", "active": True, "aimed_at_gap": False}]
        )
        self.assertFalse(result["compliant"])

    def test_empty_seeding_list_is_a_finding_not_an_error(self):
        result = check_electron_seeding([])
        self.assertFalse(result["compliant"])

    def test_wrong_family_source_raises(self):
        with self.assertRaises(ValueError):
            check_electron_seeding(
                [{"type": "power-meter", "active": True, "aimed_at_gap": True}]
            )

    def test_non_boolean_active_flag_raises(self):
        with self.assertRaises(ValueError):
            check_electron_seeding(
                [{"type": "ultraviolet-lamp", "active": 1, "aimed_at_gap": True}]
            )

    def test_non_mapping_source_raises(self):
        with self.assertRaises(ValueError):
            check_electron_seeding(["ultraviolet-lamp"])


class TestDetectionCoverage(unittest.TestCase):
    def test_global_plus_local_is_compliant(self):
        result = check_detection_coverage(
            [
                {"type": "third-harmonic-monitor", "instrument_id": "SA-1"},
                {"type": "electron-probe", "instrument_id": None},
            ]
        )
        self.assertTrue(result["compliant"])

    def test_two_global_methods_do_not_cover_the_local_family(self):
        result = check_detection_coverage(
            [
                {"type": "third-harmonic-monitor", "instrument_id": "SA-1"},
                {"type": "close-to-carrier-noise", "instrument_id": "SA-2"},
            ]
        )
        self.assertFalse(result["compliant"])
        self.assertIn("no local multipactor-detection method", result["findings"][0])

    def test_local_only_reports_the_missing_global_family(self):
        result = check_detection_coverage([{"type": "electron-probe", "instrument_id": None}])
        self.assertFalse(result["compliant"])
        self.assertIn("no global multipactor-detection method", result["findings"][0])

    def test_method_on_an_expired_instrument_is_discounted(self):
        result = check_detection_coverage(
            [
                {"type": "forward-reverse-nulling", "instrument_id": "PM-1"},
                {"type": "electron-probe", "instrument_id": None},
            ],
            expired_instruments=["PM-1"],
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["discounted"], ["forward-reverse-nulling"])

    def test_families_are_disjoint(self):
        self.assertEqual(GLOBAL_DETECTION & LOCAL_DETECTION, frozenset())

    def test_empty_method_list_reports_both_families(self):
        result = check_detection_coverage([])
        self.assertEqual(len(result["findings"]), 2)

    def test_non_detection_family_raises(self):
        with self.assertRaises(ValueError):
            check_detection_coverage([{"type": "vacuum-gauge", "instrument_id": "VG-1"}])

    def test_non_string_instrument_id_raises(self):
        with self.assertRaises(ValueError):
            check_detection_coverage(
                [{"type": "electron-probe", "instrument_id": 12}]
            )


class TestAggregateAssessment(unittest.TestCase):
    def test_good_record_is_bed_ready(self):
        result = assess_test_bed_configuration(good_record())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "BED-READY")
        self.assertEqual(result["findings"], [])

    def test_families_are_reported_for_a_good_record(self):
        result = assess_test_bed_configuration(good_record())
        self.assertIn("vacuum-chamber", result["families"]["vacuum-system"])
        self.assertIn("electron-probe", result["families"]["detection-method"])

    def test_high_pressure_makes_the_bed_not_ready(self):
        result = assess_test_bed_configuration(good_record(measured_pressure_pa=1.0e-2))
        self.assertEqual(result["verdict"], "BED-NOT-READY")
        self.assertTrue(any(f.startswith("vacuum:") for f in result["findings"]))

    def test_expired_instrument_also_removes_its_detection_method(self):
        record = good_record(
            instruments=[
                {"id": "PM-1", "type": "power-meter", "calibration_due": "2026-01-05"},
                {"id": "SA-1", "type": "spectrum-analyser", "calibration_due": "2026-06-30"},
                {"id": "VG-1", "type": "vacuum-gauge", "calibration_due": "2027-01-15"},
            ]
        )
        result = assess_test_bed_configuration(record)
        self.assertFalse(result["compliant"])
        labels = [f.split(":")[0] for f in result["findings"]]
        self.assertIn("calibration", labels)
        self.assertIn("detection", labels)

    def test_undersized_source_is_reported_under_rf_chain(self):
        result = assess_test_bed_configuration(good_record(source_rating_w=120.0))
        self.assertTrue(any(f.startswith("rf-chain:") for f in result["findings"]))

    def test_inactive_seeding_is_reported(self):
        record = good_record(
            seeding_sources=[
                {"type": "ultraviolet-lamp", "active": False, "aimed_at_gap": True}
            ]
        )
        result = assess_test_bed_configuration(record)
        self.assertTrue(any(f.startswith("electron-seeding:") for f in result["findings"]))

    def test_missing_key_raises(self):
        record = good_record()
        del record["run_margin_db"]
        with self.assertRaises(ValueError):
            assess_test_bed_configuration(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_test_bed_configuration(["elements"])

    def test_tolerance_is_a_small_relative_value(self):
        self.assertLess(REL_TOL, 1e-6)
        self.assertGreater(REL_TOL, 0.0)


if __name__ == "__main__":
    unittest.main()
