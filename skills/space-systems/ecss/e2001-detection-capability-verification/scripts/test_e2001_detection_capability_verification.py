#!/usr/bin/env python3
"""Gate 3 contract test for e2001-detection-capability-verification.

Offline, deterministic, stdlib unittest. Exercises the clause 7.3.1
demonstration logic: record normalization, signal-to-noise-ratio,
the boundary tolerance, evidence ordering in time, the validity-window,
reconciliation against the declared channel set and the derived
minimum-detectable-amplitude.
"""

import datetime
import unittest

from e2001_detection_capability_verification_logic import (
    DEFAULT_REQUIRED_RATIO_DB,
    DEFAULT_VALIDITY_WINDOW_DAYS,
    assess_detection_capability,
    evaluate_record,
    format_capability_report,
    minimum_detectable_amplitude_dbm,
    normalize_record_set,
    parse_timestamp,
    record_age_days,
    signal_to_noise_db,
    validate_demonstration_record,
)

CAMPAIGN_START = "2026-05-20T09:00:00"
BEFORE = "2026-05-18T09:00:00"


def record(**kw):
    entry = {
        "channel_id": "gx-1",
        "response_dbm": -50.0,
        "noise_floor_dbm": -70.0,
        "timestamp": BEFORE,
    }
    entry.update(kw)
    return entry


def second_record(**kw):
    entry = {
        "channel_id": "lx-1",
        "response_dbm": -45.0,
        "noise_floor_dbm": -62.0,
        "timestamp": BEFORE,
    }
    entry.update(kw)
    return entry


class TestTimestampParsing(unittest.TestCase):
    def test_parses_iso_like_stamp(self):
        stamp = parse_timestamp(CAMPAIGN_START)
        self.assertEqual(stamp.year, 2026)
        self.assertEqual(stamp.hour, 9)

    def test_datetime_passes_through(self):
        now = datetime.datetime(2026, 5, 20, 9, 0, 0)
        self.assertEqual(parse_timestamp(now), now)

    def test_date_only_stamp_raises(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-05-20")

    def test_garbage_stamp_raises(self):
        with self.assertRaises(ValueError):
            parse_timestamp("last Tuesday")

    def test_empty_stamp_raises(self):
        with self.assertRaises(ValueError):
            parse_timestamp("   ")

    def test_non_string_stamp_raises(self):
        with self.assertRaises(ValueError):
            parse_timestamp(20260520)


class TestSignalToNoise(unittest.TestCase):
    def test_ratio_is_a_difference(self):
        self.assertAlmostEqual(signal_to_noise_db(-50.0, -70.0), 20.0)

    def test_zero_ratio_when_response_sits_on_the_floor(self):
        self.assertAlmostEqual(signal_to_noise_db(-70.0, -70.0), 0.0)

    def test_non_numeric_response_raises(self):
        with self.assertRaises(ValueError):
            signal_to_noise_db("-50 dBm", -70.0)

    def test_non_finite_floor_raises(self):
        with self.assertRaises(ValueError):
            signal_to_noise_db(-50.0, float("nan"))


class TestRecordValidation(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        item = validate_demonstration_record(record())
        self.assertEqual(item["channel_id"], "gx-1")
        self.assertAlmostEqual(item["response_dbm"], -50.0)
        self.assertIsInstance(item["timestamp"], datetime.datetime)

    def test_optional_reference_amplitude_is_kept(self):
        item = validate_demonstration_record(record(reference_event_dbm=-30.0))
        self.assertAlmostEqual(item["reference_event_dbm"], -30.0)

    def test_response_below_own_floor_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration_record(record(response_dbm=-80.0))

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration_record(("gx-1", -50.0))

    def test_blank_channel_id_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration_record(record(channel_id=""))

    def test_boolean_level_raises(self):
        with self.assertRaises(ValueError):
            validate_demonstration_record(record(noise_floor_dbm=False))

    def test_empty_record_set_raises(self):
        with self.assertRaises(ValueError):
            normalize_record_set([])

    def test_duplicate_record_raises(self):
        with self.assertRaises(ValueError):
            normalize_record_set([record(), record(response_dbm=-49.0)])


class TestAgeAndOrdering(unittest.TestCase):
    def test_age_is_positive_for_earlier_evidence(self):
        item = validate_demonstration_record(record())
        self.assertAlmostEqual(record_age_days(item, CAMPAIGN_START), 2.0)

    def test_age_is_negative_for_late_evidence(self):
        item = validate_demonstration_record(record(timestamp="2026-05-21T09:00:00"))
        self.assertAlmostEqual(record_age_days(item, CAMPAIGN_START), -1.0)

    def test_fractional_age_is_carried(self):
        item = validate_demonstration_record(record(timestamp="2026-05-19T21:00:00"))
        self.assertAlmostEqual(record_age_days(item, CAMPAIGN_START), 0.5)


class TestRecordEvaluation(unittest.TestCase):
    def test_healthy_record_is_demonstrated(self):
        item = validate_demonstration_record(record())
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertTrue(result["demonstrated"])
        self.assertEqual(result["reasons"], [])
        self.assertAlmostEqual(result["snr_db"], 20.0)

    def test_thin_ratio_is_not_demonstrated(self):
        item = validate_demonstration_record(record(response_dbm=-67.0))
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertFalse(result["ratio_ok"])
        self.assertIn("signal-to-noise-ratio", result["reasons"][0])

    def test_exact_ratio_boundary_is_demonstrated(self):
        # -59.88 - (-65.88) is a physically exact 6.00 dB ratio, but in
        # binary floating point it lands a few ULPs BELOW 6.0. The
        # compliant boundary case must pass with the error absorbed in
        # the comparison, not by relaxing the required ratio.
        raw = -59.88 - (-65.88)
        self.assertLess(raw, DEFAULT_REQUIRED_RATIO_DB)
        item = validate_demonstration_record(
            record(response_dbm=-59.88, noise_floor_dbm=-65.88)
        )
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertTrue(result["ratio_ok"])
        self.assertAlmostEqual(result["snr_db"], 6.0)

    def test_one_tenth_below_the_ratio_boundary_still_fails(self):
        item = validate_demonstration_record(
            record(response_dbm=-59.98, noise_floor_dbm=-65.88)
        )
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertFalse(result["ratio_ok"])

    def test_late_evidence_is_rejected(self):
        item = validate_demonstration_record(record(timestamp="2026-05-22T09:00:00"))
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertFalse(result["in_order"])
        self.assertFalse(result["demonstrated"])
        self.assertIn("after the first campaign-run", result["reasons"][0])

    def test_evidence_recorded_at_the_campaign_start_is_in_order(self):
        item = validate_demonstration_record(record(timestamp=CAMPAIGN_START))
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertTrue(result["in_order"])
        self.assertTrue(result["demonstrated"])

    def test_evidence_on_the_validity_window_edge_is_fresh(self):
        item = validate_demonstration_record(record(timestamp="2026-04-20T09:00:00"))
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertAlmostEqual(result["age_days"], DEFAULT_VALIDITY_WINDOW_DAYS)
        self.assertTrue(result["fresh"])

    def test_evidence_one_second_past_the_window_is_stale(self):
        item = validate_demonstration_record(record(timestamp="2026-04-20T08:59:59"))
        result = evaluate_record(item, CAMPAIGN_START)
        self.assertFalse(result["fresh"])
        self.assertIn("validity-window", result["reasons"][0])

    def test_zero_required_ratio_raises(self):
        item = validate_demonstration_record(record())
        with self.assertRaises(ValueError):
            evaluate_record(item, CAMPAIGN_START, 0.0)

    def test_zero_validity_window_raises(self):
        item = validate_demonstration_record(record())
        with self.assertRaises(ValueError):
            evaluate_record(item, CAMPAIGN_START, 6.0, 0.0)


class TestMinimumDetectableAmplitude(unittest.TestCase):
    def test_worst_floor_sets_the_capability(self):
        passing = normalize_record_set([record(), second_record()])
        self.assertAlmostEqual(
            minimum_detectable_amplitude_dbm(passing, 6.0), -56.0
        )

    def test_single_channel_capability(self):
        passing = normalize_record_set([record()])
        self.assertAlmostEqual(
            minimum_detectable_amplitude_dbm(passing, 6.0), -64.0
        )

    def test_no_passing_channel_raises(self):
        with self.assertRaises(ValueError):
            minimum_detectable_amplitude_dbm([], 6.0)


class TestCapabilityAssessment(unittest.TestCase):
    def test_complete_evidence_is_verified(self):
        report = assess_detection_capability(
            ["gx-1", "lx-1"], [record(), second_record()], CAMPAIGN_START
        )
        self.assertTrue(report["verified"], report["findings"])
        self.assertEqual(report["passing_channels"], ["gx-1", "lx-1"])
        self.assertAlmostEqual(report["minimum_detectable_amplitude_dbm"], -56.0)

    def test_missing_record_is_a_finding(self):
        report = assess_detection_capability(
            ["gx-1", "lx-1"], [record()], CAMPAIGN_START
        )
        self.assertFalse(report["verified"])
        self.assertEqual(report["missing_records"], ["lx-1"])
        self.assertTrue(
            any("no demonstration record" in f for f in report["findings"]),
            report["findings"],
        )

    def test_orphan_record_is_a_finding(self):
        report = assess_detection_capability(
            ["gx-1"], [record(), second_record()], CAMPAIGN_START
        )
        self.assertEqual(report["orphan_records"], ["lx-1"])
        self.assertTrue(
            any("not a declared channel" in f for f in report["findings"]),
            report["findings"],
        )

    def test_orphan_record_does_not_raise_the_capability(self):
        report = assess_detection_capability(
            ["gx-1"], [record(), second_record()], CAMPAIGN_START
        )
        self.assertEqual(report["passing_channels"], ["gx-1"])
        self.assertAlmostEqual(report["minimum_detectable_amplitude_dbm"], -64.0)

    def test_stale_record_blocks_verification(self):
        report = assess_detection_capability(
            ["gx-1", "lx-1"],
            [record(timestamp="2026-01-10T09:00:00"), second_record()],
            CAMPAIGN_START,
        )
        self.assertFalse(report["verified"])
        self.assertTrue(
            any("validity-window" in f for f in report["findings"]), report["findings"]
        )

    def test_all_channels_failing_leaves_capability_undefined(self):
        report = assess_detection_capability(
            ["gx-1", "lx-1"],
            [record(response_dbm=-68.0), second_record(response_dbm=-60.0)],
            CAMPAIGN_START,
        )
        self.assertIsNone(report["minimum_detectable_amplitude_dbm"])
        self.assertTrue(
            any("capability is undefined" in f for f in report["findings"]),
            report["findings"],
        )

    def test_tighter_required_ratio_can_fail_a_verified_set(self):
        entries = [record(), second_record()]
        self.assertTrue(
            assess_detection_capability(
                ["gx-1", "lx-1"], entries, CAMPAIGN_START
            )["verified"]
        )
        strict = assess_detection_capability(
            ["gx-1", "lx-1"], entries, CAMPAIGN_START, 25.0
        )
        self.assertFalse(strict["verified"])

    def test_empty_declared_set_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_capability([], [record()], CAMPAIGN_START)

    def test_duplicate_declared_channel_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_capability(["gx-1", "gx-1"], [record()], CAMPAIGN_START)

    def test_blank_declared_channel_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_capability(["gx-1", "  "], [record()], CAMPAIGN_START)

    def test_bad_campaign_start_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_capability(["gx-1"], [record()], "2026-05-20")

    def test_evaluations_are_ordered_by_channel(self):
        report = assess_detection_capability(
            ["gx-1", "lx-1"], [second_record(), record()], CAMPAIGN_START
        )
        self.assertEqual(
            [e["channel_id"] for e in report["evaluations"]], ["gx-1", "lx-1"]
        )

    def test_report_text_is_deterministic(self):
        entries = [record(), second_record()]
        first = format_capability_report(
            assess_detection_capability(["gx-1", "lx-1"], entries, CAMPAIGN_START)
        )
        second = format_capability_report(
            assess_detection_capability(["gx-1", "lx-1"], entries, CAMPAIGN_START)
        )
        self.assertEqual(first, second)
        self.assertIn("VERIFIED", first)

    def test_report_text_lists_findings(self):
        text = format_capability_report(
            assess_detection_capability(["gx-1", "lx-1"], [record()], CAMPAIGN_START)
        )
        self.assertIn("NOT VERIFIED", text)
        self.assertIn("FINDING:", text)


if __name__ == "__main__":
    unittest.main()
