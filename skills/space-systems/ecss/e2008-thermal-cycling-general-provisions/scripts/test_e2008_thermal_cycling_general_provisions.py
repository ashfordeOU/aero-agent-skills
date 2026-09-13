"""Contract tests for the clause 5.5.1.3.2 cycling-continuity evidence logic."""

import unittest

from e2008_thermal_cycling_general_provisions_logic import (
    CATEGORIES,
    CHANNEL_KINDS,
    DRIFT_TOLERANCE,
    REQUIRED_KINDS,
    assess_continuity_evidence,
    categorize_channel,
    drift_fraction,
    is_open,
    kind_findings,
    monitoring_gaps,
    normalize_kind,
    validate_readings,
)

TOTAL = 2000
CHECKPOINTS = (0, 500, 1000, 1500, 2000)


def _channel(identifier, kind, baseline, ohms):
    return {
        "id": identifier,
        "kind": kind,
        "baseline_ohm": baseline,
        "readings": list(zip(CHECKPOINTS, ohms)),
    }


class KindTests(unittest.TestCase):
    def test_kind_is_normalized(self):
        self.assertEqual(normalize_kind(" Cell_String "), "cell-string")

    def test_wiring_kind_is_accepted(self):
        self.assertEqual(normalize_kind("wiring"), "wiring")

    def test_known_kinds_are_three(self):
        self.assertEqual(len(CHANNEL_KINDS), 3)

    def test_required_kinds_are_cells_and_wiring(self):
        self.assertEqual(REQUIRED_KINDS, ("cell-string", "wiring"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kind("thermocouple")

    def test_non_string_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kind(7)


class DriftTests(unittest.TestCase):
    def test_ten_percent_rise(self):
        self.assertAlmostEqual(drift_fraction(0.100, 0.110), 0.1, places=9)

    def test_unchanged_reading_has_no_drift(self):
        self.assertAlmostEqual(drift_fraction(0.250, 0.250), 0.0, places=9)

    def test_fall_gives_a_negative_drift(self):
        self.assertAlmostEqual(drift_fraction(0.200, 0.180), -0.1, places=9)

    def test_zero_baseline_rejected(self):
        with self.assertRaises(ValueError):
            drift_fraction(0.0, 0.110)

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            drift_fraction(0.100, -0.010)

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            drift_fraction(0.100, True)


class OpenDetectionTests(unittest.TestCase):
    def test_reading_above_the_threshold_is_open(self):
        self.assertTrue(is_open(2000.0, 1000.0))

    def test_reading_on_the_threshold_is_open(self):
        self.assertTrue(is_open(1000.0, 1000.0))

    def test_healthy_reading_is_not_open(self):
        self.assertFalse(is_open(0.12, 1000.0))

    def test_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            is_open(0.12, 0.0)

    def test_non_finite_reading_rejected(self):
        with self.assertRaises(ValueError):
            is_open(float("inf"), 1000.0)


class ReadingValidationTests(unittest.TestCase):
    def test_series_is_returned_as_pairs(self):
        series = validate_readings([(0, 0.1), (10, 0.11)], 10)
        self.assertEqual(series, [(0, 0.1), (10, 0.11)])

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([], 10)

    def test_reading_past_the_run_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(0, 0.1), (20, 0.11)], 10)

    def test_out_of_order_series_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(10, 0.1), (5, 0.11)], 10)

    def test_repeated_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(5, 0.1), (5, 0.11)], 10)

    def test_float_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(0.0, 0.1)], 10)

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(0, 0.1, 0.2)], 10)


class CategorizationTests(unittest.TestCase):
    def _record(self, ohms, kind="cell-string", limit=0.10):
        return categorize_channel(
            _channel("S1", kind, 0.100, ohms), TOTAL, limit, 1000.0
        )

    def test_steady_channel_is_continuous(self):
        record = self._record([0.100, 0.101, 0.102, 0.103, 0.104])
        self.assertEqual(record["category"], "continuous")

    def test_drift_on_the_limit_stays_continuous(self):
        record = self._record([0.100, 0.102, 0.105, 0.108, 0.110])
        self.assertAlmostEqual(record["max_drift_fraction"], 0.10, places=9)
        self.assertEqual(record["category"], "continuous")

    def test_drift_past_the_limit_is_grouped_as_drifting(self):
        record = self._record([0.100, 0.105, 0.115, 0.130, 0.150])
        self.assertEqual(record["category"], "drifting")

    def test_open_at_the_end_is_grouped_as_open(self):
        record = self._record([0.100, 0.101, 0.102, 0.103, 5000.0])
        self.assertEqual(record["category"], "open")
        self.assertEqual(record["open_cycles"], [2000])

    def test_open_that_closed_again_is_intermittent(self):
        record = self._record([0.100, 0.101, 5000.0, 0.103, 0.104])
        self.assertEqual(record["category"], "intermittent")
        self.assertEqual(record["open_cycles"], [1000])

    def test_record_carries_the_checkpoint_cycles(self):
        record = self._record([0.100, 0.101, 0.102, 0.103, 0.104])
        self.assertEqual(record["cycles"], list(CHECKPOINTS))

    def test_categories_are_four(self):
        self.assertEqual(len(CATEGORIES), 4)

    def test_threshold_below_the_baseline_rejected(self):
        with self.assertRaises(ValueError):
            categorize_channel(
                _channel("S1", "wiring", 0.100, [0.1] * 5), TOTAL, 0.10, 0.05
            )

    def test_missing_channel_key_rejected(self):
        channel = _channel("S1", "wiring", 0.100, [0.1] * 5)
        del channel["baseline_ohm"]
        with self.assertRaises(ValueError):
            categorize_channel(channel, TOTAL, 0.10, 1000.0)

    def test_blank_channel_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize_channel(
                _channel("  ", "wiring", 0.100, [0.1] * 5), TOTAL, 0.10, 1000.0
            )

    def test_zero_drift_limit_rejected(self):
        with self.assertRaises(ValueError):
            categorize_channel(
                _channel("S1", "wiring", 0.100, [0.1] * 5), TOTAL, 0.0, 1000.0
            )


class MonitoringGapTests(unittest.TestCase):
    def test_full_coverage_has_no_finding(self):
        self.assertEqual(monitoring_gaps(CHECKPOINTS, TOTAL, 500), [])

    def test_missing_start_reading_is_flagged(self):
        findings = monitoring_gaps([500, 1000, 1500, 2000], TOTAL, 500)
        self.assertEqual(len(findings), 1)
        self.assertIn("before the run", findings[0])

    def test_missing_end_reading_is_flagged(self):
        findings = monitoring_gaps([0, 500, 1000], TOTAL, 500)
        self.assertEqual(len(findings), 1)
        self.assertIn("end of the run", findings[0])

    def test_wide_gap_is_flagged(self):
        findings = monitoring_gaps([0, 1800, 2000], TOTAL, 500)
        self.assertEqual(len(findings), 1)
        self.assertIn("unwitnessed", findings[0])

    def test_gap_exactly_on_the_allowance_is_accepted(self):
        self.assertEqual(monitoring_gaps([0, 500, 1000, 1500, 2000], TOTAL, 500), [])

    def test_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_gaps(CHECKPOINTS, TOTAL, 0)

    def test_empty_checkpoint_set_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_gaps([], TOTAL, 500)


class KindFindingTests(unittest.TestCase):
    def test_both_kinds_present_gives_no_finding(self):
        records = [{"kind": "cell-string"}, {"kind": "wiring"}]
        self.assertEqual(kind_findings(records), [])

    def test_wiring_only_flags_the_cells(self):
        findings = kind_findings([{"kind": "wiring"}])
        self.assertEqual(len(findings), 1)
        self.assertIn("cell-string", findings[0])

    def test_interconnect_alone_flags_both(self):
        self.assertEqual(len(kind_findings([{"kind": "interconnect"}])), 2)

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            kind_findings([{"id": "S1"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, channels=None, **overrides):
        spec = {
            "total_cycles": TOTAL,
            "drift_limit_fraction": 0.10,
            "open_threshold_ohm": 1000.0,
            "max_gap_cycles": 500,
            "channels": channels if channels is not None else [
                _channel("string-1", "cell-string", 0.100,
                         [0.100, 0.101, 0.102, 0.103, 0.104]),
                _channel("harness-1", "wiring", 0.050,
                         [0.050, 0.050, 0.051, 0.051, 0.052]),
            ],
        }
        spec.update(overrides)
        return spec

    def test_clean_run_maintains_continuity(self):
        result = assess_continuity_evidence(self._spec())
        self.assertTrue(result["continuity_maintained"])
        self.assertEqual(result["findings"], [])

    def test_summary_counts_every_channel(self):
        result = assess_continuity_evidence(self._spec())
        self.assertEqual(result["summary"]["continuous"], 2)
        self.assertEqual(result["summary"]["open"], 0)

    def test_open_channel_breaks_the_evidence(self):
        channels = [
            _channel("string-1", "cell-string", 0.100,
                     [0.100, 0.101, 0.102, 0.103, 4000.0]),
            _channel("harness-1", "wiring", 0.050, [0.050] * 5),
        ]
        result = assess_continuity_evidence(self._spec(channels))
        self.assertFalse(result["continuity_maintained"])
        self.assertEqual(result["summary"]["open"], 1)

    def test_intermittent_open_is_reported_not_absorbed(self):
        channels = [
            _channel("string-1", "cell-string", 0.100,
                     [0.100, 4000.0, 0.102, 0.103, 0.104]),
            _channel("harness-1", "wiring", 0.050, [0.050] * 5),
        ]
        result = assess_continuity_evidence(self._spec(channels))
        self.assertEqual(result["summary"]["intermittent"], 1)
        self.assertTrue(any("closed again" in f for f in result["findings"]))

    def test_drifting_channel_is_reported(self):
        channels = [
            _channel("string-1", "cell-string", 0.100,
                     [0.100, 0.110, 0.130, 0.160, 0.200]),
            _channel("harness-1", "wiring", 0.050, [0.050] * 5),
        ]
        result = assess_continuity_evidence(self._spec(channels))
        self.assertEqual(result["summary"]["drifting"], 1)
        self.assertFalse(result["continuity_maintained"])

    def test_unwitnessed_stretch_is_reported(self):
        channel = {
            "id": "string-1",
            "kind": "cell-string",
            "baseline_ohm": 0.100,
            "readings": [(0, 0.100), (1800, 0.104), (2000, 0.104)],
        }
        result = assess_continuity_evidence(
            self._spec([channel,
                        _channel("harness-1", "wiring", 0.050, [0.050] * 5)])
        )
        self.assertFalse(result["continuity_maintained"])
        self.assertTrue(any("unwitnessed" in f for f in result["findings"]))

    def test_wiring_only_evidence_is_incomplete(self):
        channels = [_channel("harness-1", "wiring", 0.050, [0.050] * 5)]
        result = assess_continuity_evidence(self._spec(channels))
        self.assertFalse(result["continuity_maintained"])
        self.assertTrue(any("cell-string" in f for f in result["findings"]))

    def test_duplicate_channel_id_rejected(self):
        channels = [
            _channel("string-1", "cell-string", 0.100, [0.100] * 5),
            _channel("string-1", "wiring", 0.050, [0.050] * 5),
        ]
        with self.assertRaises(ValueError):
            assess_continuity_evidence(self._spec(channels))

    def test_empty_channel_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_continuity_evidence(self._spec([]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["open_threshold_ohm"]
        with self.assertRaises(ValueError):
            assess_continuity_evidence(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_continuity_evidence(["channels"])

    def test_drift_tolerance_is_small(self):
        self.assertAlmostEqual(DRIFT_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
