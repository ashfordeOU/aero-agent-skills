#!/usr/bin/env python3
"""Gate 3 contract test for e2001-detection-method-overview.

Offline, deterministic, stdlib unittest. Exercises the clause 7.1
arrangement logic: channel normalization, coverage mix, observable-family
independence, sensitivity-margin, response-time and aggregation.
"""

import unittest

from e2001_detection_method_overview_logic import (
    DEFAULT_REQUIRED_MARGIN_DB,
    MIN_CHANNEL_COUNT,
    MIN_INDEPENDENT_FAMILIES,
    assess_detection_arrangement,
    coverage_summary,
    duplicated_families,
    evaluate_channel_registration,
    format_arrangement_report,
    independent_families,
    normalize_channel_set,
    normalize_coverage_scope,
    normalize_observable_family,
    sensitivity_margin_db,
    validate_detection_channel,
)


def global_channel(**kw):
    entry = {
        "channel_id": "gx-1",
        "coverage_scope": "global",
        "observable_family": "rf-power-balance",
        "threshold_dbm": -60.0,
        "response_time_ms": 0.5,
        "calibrated": True,
    }
    entry.update(kw)
    return entry


def local_channel(**kw):
    entry = {
        "channel_id": "lx-1",
        "coverage_scope": "local",
        "observable_family": "electron-probe",
        "threshold_dbm": -55.0,
        "response_time_ms": 0.2,
        "calibrated": True,
    }
    entry.update(kw)
    return entry


class TestScopeNormalization(unittest.TestCase):
    def test_global_aliases_normalize(self):
        for alias in ("global", "GLOBAL-COVERAGE", " rf-chain ", "chain-wide"):
            self.assertEqual(normalize_coverage_scope(alias), "global-coverage")

    def test_local_aliases_normalize(self):
        for alias in ("local", "Local-Coverage", "gap-local", "region"):
            self.assertEqual(normalize_coverage_scope(alias), "local-coverage")

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            normalize_coverage_scope("everywhere")

    def test_empty_scope_raises(self):
        with self.assertRaises(ValueError):
            normalize_coverage_scope("   ")

    def test_non_string_scope_raises(self):
        with self.assertRaises(ValueError):
            normalize_coverage_scope(7)


class TestFamilyNormalization(unittest.TestCase):
    def test_family_aliases_normalize(self):
        self.assertEqual(
            normalize_observable_family("forward-reflected"), "rf-power-balance"
        )
        self.assertEqual(
            normalize_observable_family("close-to-carrier-noise"), "spectral-sideband"
        )
        self.assertEqual(
            normalize_observable_family("ELECTRON-PROBE"), "charged-particle"
        )
        self.assertEqual(
            normalize_observable_family("pressure-rise"), "gas-pressure"
        )
        self.assertEqual(normalize_observable_family("calorimetric"), "thermal-rise")

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            normalize_observable_family("gut-feel")

    def test_non_string_family_raises(self):
        with self.assertRaises(ValueError):
            normalize_observable_family(None)


class TestChannelValidation(unittest.TestCase):
    def test_valid_channel_is_normalized(self):
        channel = validate_detection_channel(global_channel())
        self.assertEqual(channel["coverage_scope"], "global-coverage")
        self.assertEqual(channel["observable_family"], "rf-power-balance")
        self.assertAlmostEqual(channel["threshold_dbm"], -60.0)
        self.assertTrue(channel["calibrated"])

    def test_calibrated_defaults_to_false(self):
        entry = global_channel()
        del entry["calibrated"]
        self.assertFalse(validate_detection_channel(entry)["calibrated"])

    def test_non_mapping_channel_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(["gx-1"])

    def test_blank_channel_id_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(global_channel(channel_id="  "))

    def test_zero_response_time_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(global_channel(response_time_ms=0.0))

    def test_negative_response_time_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(global_channel(response_time_ms=-1.0))

    def test_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(global_channel(threshold_dbm="-60 dBm"))

    def test_boolean_threshold_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(global_channel(threshold_dbm=True))

    def test_non_boolean_calibrated_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(global_channel(calibrated="yes"))

    def test_region_bound_family_cannot_be_global(self):
        with self.assertRaises(ValueError):
            validate_detection_channel(
                global_channel(observable_family="optical-emission")
            )

    def test_empty_channel_set_raises(self):
        with self.assertRaises(ValueError):
            normalize_channel_set([])

    def test_duplicate_channel_id_raises(self):
        with self.assertRaises(ValueError):
            normalize_channel_set([global_channel(), global_channel()])


class TestMarginAndCoverage(unittest.TestCase):
    def test_sensitivity_margin_is_a_difference(self):
        self.assertAlmostEqual(sensitivity_margin_db(-50.0, -60.0), 10.0)

    def test_negative_margin_when_signature_below_threshold(self):
        self.assertAlmostEqual(sensitivity_margin_db(-65.0, -60.0), -5.0)

    def test_margin_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            sensitivity_margin_db(float("inf"), -60.0)

    def test_coverage_summary_counts_both_scopes(self):
        channels = normalize_channel_set([global_channel(), local_channel()])
        self.assertEqual(
            coverage_summary(channels),
            {"global-coverage": 1, "local-coverage": 1},
        )

    def test_independent_families_are_distinct(self):
        channels = normalize_channel_set([global_channel(), local_channel()])
        self.assertEqual(
            independent_families(channels),
            ["charged-particle", "rf-power-balance"],
        )

    def test_duplicated_family_is_reported(self):
        channels = normalize_channel_set(
            [
                global_channel(),
                global_channel(channel_id="gx-2", observable_family="power-balance"),
                local_channel(),
            ]
        )
        self.assertEqual(duplicated_families(channels), ["rf-power-balance"])


class TestChannelRegistration(unittest.TestCase):
    def test_healthy_channel_registers(self):
        channel = validate_detection_channel(global_channel())
        report = evaluate_channel_registration(channel, -50.0, 1.0)
        self.assertTrue(report["registers"])
        self.assertAlmostEqual(report["margin_db"], 10.0)
        self.assertEqual(report["reasons"], [])

    def test_thin_margin_does_not_register(self):
        channel = validate_detection_channel(global_channel(threshold_dbm=-51.0))
        report = evaluate_channel_registration(channel, -50.0, 1.0)
        self.assertFalse(report["margin_ok"])
        self.assertFalse(report["registers"])
        self.assertIn("sensitivity-margin", report["reasons"][0])

    def test_exact_margin_boundary_registers(self):
        # -31.94 - (-34.94) is a physically exact 3.00 dB margin, but in
        # binary floating point the subtraction lands a few ULPs BELOW
        # 3.0. The compliant boundary case must still register, with the
        # error absorbed in the comparison and not in the required limit.
        raw = -31.94 - (-34.94)
        self.assertLess(raw, DEFAULT_REQUIRED_MARGIN_DB)
        channel = validate_detection_channel(global_channel(threshold_dbm=-34.94))
        report = evaluate_channel_registration(
            channel, -31.94, 1.0, DEFAULT_REQUIRED_MARGIN_DB
        )
        self.assertTrue(report["margin_ok"])
        self.assertAlmostEqual(report["margin_db"], 3.0)

    def test_one_step_below_the_margin_boundary_still_fails(self):
        channel = validate_detection_channel(global_channel(threshold_dbm=-34.84))
        report = evaluate_channel_registration(
            channel, -31.94, 1.0, DEFAULT_REQUIRED_MARGIN_DB
        )
        self.assertFalse(report["margin_ok"])
        self.assertAlmostEqual(report["margin_db"], 2.9, places=6)

    def test_exact_response_time_boundary_registers(self):
        channel = validate_detection_channel(
            global_channel(response_time_ms=0.1 + 0.2)
        )
        report = evaluate_channel_registration(channel, -50.0, 0.3)
        self.assertTrue(report["speed_ok"])
        self.assertTrue(report["registers"])

    def test_slow_channel_does_not_register(self):
        channel = validate_detection_channel(global_channel(response_time_ms=5.0))
        report = evaluate_channel_registration(channel, -50.0, 1.0)
        self.assertFalse(report["speed_ok"])
        self.assertIn("response-time", report["reasons"][0])

    def test_both_failures_are_reported(self):
        channel = validate_detection_channel(
            global_channel(threshold_dbm=-49.0, response_time_ms=9.0)
        )
        report = evaluate_channel_registration(channel, -50.0, 1.0)
        self.assertEqual(len(report["reasons"]), 2)

    def test_zero_event_duration_raises(self):
        channel = validate_detection_channel(global_channel())
        with self.assertRaises(ValueError):
            evaluate_channel_registration(channel, -50.0, 0.0)

    def test_negative_required_margin_raises(self):
        channel = validate_detection_channel(global_channel())
        with self.assertRaises(ValueError):
            evaluate_channel_registration(channel, -50.0, 1.0, -1.0)


class TestArrangementAssessment(unittest.TestCase):
    def test_minimum_adequate_arrangement(self):
        report = assess_detection_arrangement(
            [global_channel(), local_channel()], -50.0, 1.0
        )
        self.assertTrue(report["adequate"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["families"]), MIN_INDEPENDENT_FAMILIES)

    def test_single_channel_is_below_minimum(self):
        report = assess_detection_arrangement([global_channel()], -50.0, 1.0)
        self.assertFalse(report["adequate"])
        self.assertTrue(
            any("channel-count" in f for f in report["findings"]),
            report["findings"],
        )
        self.assertEqual(MIN_CHANNEL_COUNT, 2)

    def test_all_global_arrangement_flags_missing_local(self):
        report = assess_detection_arrangement(
            [
                global_channel(),
                global_channel(
                    channel_id="gx-2", observable_family="spectral-sideband"
                ),
            ],
            -50.0,
            1.0,
        )
        self.assertIn("no local-coverage channel declared", report["findings"])

    def test_all_local_arrangement_flags_missing_global(self):
        report = assess_detection_arrangement(
            [
                local_channel(),
                local_channel(channel_id="lx-2", observable_family="gas-pressure"),
            ],
            -50.0,
            1.0,
        )
        self.assertIn("no global-coverage channel declared", report["findings"])

    def test_duplicated_family_breaks_independence(self):
        report = assess_detection_arrangement(
            [
                global_channel(),
                global_channel(channel_id="gx-2", observable_family="power-balance"),
            ],
            -50.0,
            1.0,
        )
        self.assertTrue(
            any("independent observable-family" in f for f in report["findings"]),
            report["findings"],
        )
        self.assertEqual(report["duplicated_families"], ["rf-power-balance"])

    def test_slow_sole_global_channel_is_not_rescued_by_local(self):
        report = assess_detection_arrangement(
            [global_channel(response_time_ms=9.0), local_channel()], -50.0, 1.0
        )
        self.assertIn("no registering global-coverage channel remains", report["findings"])

    def test_uncalibrated_channel_is_a_finding(self):
        report = assess_detection_arrangement(
            [global_channel(calibrated=False), local_channel()], -50.0, 1.0
        )
        self.assertFalse(report["adequate"])
        self.assertTrue(
            any("calibration traceability" in f for f in report["findings"]),
            report["findings"],
        )

    def test_required_margin_is_carried_into_the_report(self):
        report = assess_detection_arrangement(
            [global_channel(), local_channel()], -50.0, 1.0, 6.0
        )
        self.assertAlmostEqual(report["required_margin_db"], 6.0)

    def test_tighter_required_margin_can_fail_an_adequate_set(self):
        entries = [global_channel(), local_channel()]
        self.assertTrue(assess_detection_arrangement(entries, -50.0, 1.0)["adequate"])
        strict = assess_detection_arrangement(entries, -50.0, 1.0, 12.0)
        self.assertFalse(strict["adequate"])

    def test_report_is_deterministic(self):
        entries = [global_channel(), local_channel()]
        first = format_arrangement_report(
            assess_detection_arrangement(entries, -50.0, 1.0)
        )
        second = format_arrangement_report(
            assess_detection_arrangement(entries, -50.0, 1.0)
        )
        self.assertEqual(first, second)
        self.assertIn("ADEQUATE", first)

    def test_report_lists_findings(self):
        text = format_arrangement_report(
            assess_detection_arrangement([global_channel()], -50.0, 1.0)
        )
        self.assertIn("NOT ADEQUATE", text)
        self.assertIn("FINDING:", text)


if __name__ == "__main__":
    unittest.main()
