"""Contract tests for the clause 5.8.1 test-activity monitoring logic."""

import unittest

from q2007_monitoring_logic import (
    COVERAGE_TOLERANCE,
    MAX_DROPOUT_FRACTION,
    MIN_NYQUIST_RATIO,
    RECOMMENDED_SAMPLE_RATIO,
    acquisition_ratio,
    assess_channel,
    assess_hold_point,
    assess_monitoring,
    coverage_gaps,
    merge_intervals,
    surveillance_coverage,
    validate_window,
)

GOOD_CHANNEL = {
    "name": "AX-01 accelerometer",
    "sample_rate_hz": 2000.0,
    "max_frequency_hz": 200.0,
    "dropout_fraction": 0.001,
    "calibration_days_remaining": 45,
}


def channel(**overrides):
    out = dict(GOOD_CHANNEL)
    out.update(overrides)
    return out


class ValidateWindowTests(unittest.TestCase):
    def test_returns_float_pair(self):
        self.assertEqual(validate_window(0, 6), (0.0, 6.0))

    def test_zero_length_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(3.0, 3.0)

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(6.0, 1.0)

    def test_negative_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(-1.0, 6.0)

    def test_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_window("0", 6.0)

    def test_non_finite_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(0.0, float("inf"))


class AcquisitionRatioTests(unittest.TestCase):
    def test_ratio_is_the_quotient(self):
        self.assertAlmostEqual(acquisition_ratio(1000.0, 100.0), 10.0)

    def test_ratio_at_the_nyquist_bound(self):
        self.assertAlmostEqual(acquisition_ratio(400.0, 200.0), MIN_NYQUIST_RATIO, places=9)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            acquisition_ratio(1000.0, 0.0)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            acquisition_ratio(-1000.0, 100.0)

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            acquisition_ratio(True, 100.0)


class ChannelAssessmentTests(unittest.TestCase):
    def test_fit_channel_has_no_findings(self):
        record = assess_channel(channel())
        self.assertTrue(record["fit"])
        self.assertEqual(record["findings"], [])

    def test_under_nyquist_is_a_finding(self):
        record = assess_channel(channel(sample_rate_hz=300.0))
        self.assertFalse(record["fit"])
        self.assertIn("under", record["findings"][0])

    def test_exactly_at_the_recommended_ratio_is_accepted(self):
        record = assess_channel(channel(sample_rate_hz=1000.0))
        self.assertAlmostEqual(record["ratio"], RECOMMENDED_SAMPLE_RATIO, places=9)
        self.assertTrue(record["fit"])

    def test_between_nyquist_and_recommended_is_a_resolution_finding(self):
        record = assess_channel(channel(sample_rate_hz=600.0))
        self.assertFalse(record["fit"])
        self.assertIn("resolved", record["findings"][0])

    def test_dropout_exactly_on_the_limit_is_accepted(self):
        record = assess_channel(channel(dropout_fraction=MAX_DROPOUT_FRACTION))
        self.assertTrue(record["fit"])

    def test_dropout_above_the_limit_is_a_finding(self):
        record = assess_channel(channel(dropout_fraction=0.10))
        self.assertFalse(record["fit"])

    def test_expired_calibration_is_a_finding(self):
        record = assess_channel(channel(calibration_days_remaining=0))
        self.assertFalse(record["fit"])

    def test_dropout_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel(channel(dropout_fraction=1.5))

    def test_missing_key_rejected(self):
        bad = channel()
        del bad["sample_rate_hz"]
        with self.assertRaises(ValueError):
            assess_channel(bad)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel(channel(name="   "))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel(["AX-01", 2000.0])


class IntervalTests(unittest.TestCase):
    def test_overlapping_intervals_merge(self):
        self.assertEqual(merge_intervals([(0.0, 2.0), (1.0, 3.0)]), [(0.0, 3.0)])

    def test_touching_intervals_merge(self):
        self.assertEqual(merge_intervals([(0.0, 2.0), (2.0, 4.0)]), [(0.0, 4.0)])

    def test_disjoint_intervals_stay_apart(self):
        self.assertEqual(
            merge_intervals([(3.0, 4.0), (0.0, 1.0)]), [(0.0, 1.0), (3.0, 4.0)]
        )

    def test_zero_length_interval_rejected(self):
        with self.assertRaises(ValueError):
            merge_intervals([(1.0, 1.0)])

    def test_malformed_interval_rejected(self):
        with self.assertRaises(ValueError):
            merge_intervals([(1.0,)])

    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(surveillance_coverage([(0.0, 6.0)], (0.0, 6.0)), 1.0, places=9)

    def test_half_coverage(self):
        self.assertAlmostEqual(surveillance_coverage([(0.0, 3.0)], (0.0, 6.0)), 0.5, places=9)

    def test_double_logged_stretch_is_not_double_counted(self):
        value = surveillance_coverage([(0.0, 3.0), (1.0, 3.0)], (0.0, 6.0))
        self.assertAlmostEqual(value, 0.5, places=9)

    def test_interval_outside_the_window_rejected(self):
        with self.assertRaises(ValueError):
            surveillance_coverage([(7.0, 8.0)], (0.0, 6.0))

    def test_gaps_report_the_unwatched_stretches(self):
        gaps = coverage_gaps([(0.0, 2.0), (4.0, 6.0)], (0.0, 6.0))
        self.assertEqual(gaps, [(2.0, 4.0)])

    def test_no_gaps_when_fully_covered(self):
        self.assertEqual(coverage_gaps([(0.0, 6.0)], (0.0, 6.0)), [])


class HoldPointTests(unittest.TestCase):
    def test_clean_release_is_adjudicated(self):
        record = assess_hold_point(
            {
                "id": "HP-3",
                "time_h": 2.0,
                "released": True,
                "witness_required": True,
                "witness_present": True,
                "release_authority": "test conductor",
            }
        )
        self.assertTrue(record["adjudicated"])

    def test_release_without_required_witness_is_a_finding(self):
        record = assess_hold_point(
            {
                "id": "HP-4",
                "time_h": 3.0,
                "released": True,
                "witness_required": True,
                "witness_present": False,
                "release_authority": "test conductor",
            }
        )
        self.assertFalse(record["adjudicated"])

    def test_release_without_authority_is_a_finding(self):
        record = assess_hold_point({"id": "HP-5", "time_h": 1.0, "released": True})
        self.assertFalse(record["adjudicated"])

    def test_execution_past_an_open_hold_point_is_a_finding(self):
        record = assess_hold_point(
            {
                "id": "HP-6",
                "time_h": 1.0,
                "released": False,
                "execution_continued": True,
            }
        )
        self.assertFalse(record["adjudicated"])

    def test_open_hold_point_without_continuation_is_clean(self):
        record = assess_hold_point({"id": "HP-7", "time_h": 1.0, "released": False})
        self.assertTrue(record["adjudicated"])

    def test_non_boolean_released_rejected(self):
        with self.assertRaises(ValueError):
            assess_hold_point({"id": "HP-8", "time_h": 1.0, "released": "yes"})

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_hold_point({"time_h": 1.0, "released": True})


class CampaignAssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        out = {
            "window": (0.0, 10.0),
            "channels": [channel()],
            "hold_points": [
                {
                    "id": "HP-1",
                    "time_h": 4.0,
                    "released": True,
                    "witness_required": False,
                    "release_authority": "test conductor",
                }
            ],
            "surveillance": [(0.0, 10.0)],
            "required_coverage": 0.9,
        }
        out.update(overrides)
        return out

    def test_clean_campaign_is_adequate(self):
        result = assess_monitoring(self.spec())
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_coverage_exactly_on_the_requirement_is_met(self):
        result = assess_monitoring(
            self.spec(surveillance=[(0.0, 9.0)], required_coverage=0.9)
        )
        self.assertAlmostEqual(result["coverage"], 0.9, places=9)
        self.assertTrue(result["adequate"])

    def test_short_coverage_is_a_finding(self):
        result = assess_monitoring(self.spec(surveillance=[(0.0, 5.0)]))
        self.assertFalse(result["adequate"])
        self.assertEqual(result["gaps"], [(5.0, 10.0)])

    def test_channel_finding_propagates(self):
        result = assess_monitoring(self.spec(channels=[channel(sample_rate_hz=100.0)]))
        self.assertFalse(result["adequate"])

    def test_hold_point_finding_propagates(self):
        result = assess_monitoring(
            self.spec(
                hold_points=[{"id": "HP-2", "time_h": 4.0, "released": True}]
            )
        )
        self.assertFalse(result["adequate"])

    def test_empty_channel_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring(self.spec(channels=[]))

    def test_required_coverage_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring(self.spec(required_coverage=1.4))

    def test_missing_spec_key_rejected(self):
        bad = self.spec()
        del bad["surveillance"]
        with self.assertRaises(ValueError):
            assess_monitoring(bad)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertAlmostEqual(COVERAGE_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
