#!/usr/bin/env python3
"""Contract test for the working standard sensitivity stability (offline)."""

import copy
import unittest

from e2008_working_standard_sensitivity_stability_logic import (
    DAYS_PER_YEAR,
    DEFAULT_STABILITY_CRITERIA,
    DRIFTED,
    GROUP_REFERRED,
    GROUP_STABLE,
    GROUP_UNSTABLE,
    REFER,
    STABLE,
    assess_sensitivity_stability,
    assess_standard_drift,
    drift_metrics,
    least_squares_slope,
    normalize_short_circuit_current,
    session_ratios,
    validate_stability_criteria,
)

STANDARD_IDS = ("WS-1", "WS-2", "WS-3", "WS-4", "WS-5")
SESSION_IDS = ("S1", "S2", "S3")
DAYS = (0.0, 182.625, 365.25)
BASELINE_A = 0.5
ALPHA_PER_C = 0.0005


def _campaign(currents=None, **overrides):
    currents = currents or {}
    sessions = []
    for index, session_id in enumerate(SESSION_IDS):
        readings = []
        for standard_id in STANDARD_IDS:
            series = currents.get(standard_id)
            value = series[index] if series else BASELINE_A
            readings.append(
                {
                    "standard_id": standard_id,
                    "short_circuit_current_a": value,
                    "temperature_c": 25.0,
                }
            )
        sessions.append(
            {
                "session_id": session_id,
                "elapsed_days": DAYS[index],
                "readings": readings,
            }
        )
    campaign = {
        "campaign_id": "WS-GROUP-A",
        "alpha_per_c": ALPHA_PER_C,
        "sessions": sessions,
    }
    campaign.update(overrides)
    return campaign


def _session(values=None, session_id="S1", elapsed_days=0.0):
    values = values or {}
    return {
        "session_id": session_id,
        "elapsed_days": elapsed_days,
        "readings": [
            {
                "standard_id": standard_id,
                "short_circuit_current_a": values.get(standard_id, BASELINE_A),
                "temperature_c": 25.0,
            }
            for standard_id in STANDARD_IDS
        ],
    }


def _series(ratios):
    return list(zip(DAYS, ratios))


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_stability_criteria(DEFAULT_STABILITY_CRITERIA),
            DEFAULT_STABILITY_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_criteria("default")

    def test_missing_limit_rejected(self):
        broken = dict(DEFAULT_STABILITY_CRITERIA)
        del broken["max_annual_drift_fraction"]
        with self.assertRaises(ValueError):
            validate_stability_criteria(broken)

    def test_group_below_five_standards_rejected(self):
        broken = dict(DEFAULT_STABILITY_CRITERIA, min_group_size=4)
        with self.assertRaises(ValueError):
            validate_stability_criteria(broken)

    def test_single_session_campaign_criteria_rejected(self):
        broken = dict(DEFAULT_STABILITY_CRITERIA, min_sessions=1)
        with self.assertRaises(ValueError):
            validate_stability_criteria(broken)

    def test_tolerance_of_a_whole_unit_rejected(self):
        broken = dict(DEFAULT_STABILITY_CRITERIA, max_ratio_drift_fraction=1.0)
        with self.assertRaises(ValueError):
            validate_stability_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_STABILITY_CRITERIA, ratio_drift_review_factor=0.5)
        with self.assertRaises(ValueError):
            validate_stability_criteria(broken)

    def test_drift_allowance_above_the_excursion_allowance_rejected(self):
        broken = dict(
            DEFAULT_STABILITY_CRITERIA,
            max_ratio_drift_fraction=0.02,
            max_ratio_excursion_fraction=0.01,
        )
        with self.assertRaises(ValueError):
            validate_stability_criteria(broken)


class NormalizationTests(unittest.TestCase):
    def test_reading_at_the_reference_temperature_is_unchanged(self):
        self.assertAlmostEqual(
            normalize_short_circuit_current(0.5, 25.0, ALPHA_PER_C, 25.0),
            0.5,
            places=12,
        )

    def test_warm_reading_is_corrected_down(self):
        corrected = normalize_short_circuit_current(0.5, 45.0, ALPHA_PER_C, 25.0)
        self.assertAlmostEqual(corrected, 0.5 / 1.01, places=12)

    def test_cold_reading_is_corrected_up(self):
        corrected = normalize_short_circuit_current(0.5, 5.0, ALPHA_PER_C, 25.0)
        self.assertAlmostEqual(corrected, 0.5 / 0.99, places=12)

    def test_non_physical_temperature_factor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_short_circuit_current(0.5, 30.0, -0.5, 25.0)

    def test_non_positive_current_rejected(self):
        with self.assertRaises(ValueError):
            normalize_short_circuit_current(0.0, 25.0, ALPHA_PER_C, 25.0)

    def test_coefficient_of_a_whole_unit_rejected(self):
        with self.assertRaises(ValueError):
            normalize_short_circuit_current(0.5, 25.0, 1.5, 25.0)


class SessionTests(unittest.TestCase):
    def test_agreeing_group_gives_unit_ratios(self):
        resolved = session_ratios(_session(), ALPHA_PER_C)
        for ratio in resolved["ratios"].values():
            self.assertAlmostEqual(ratio, 1.0, places=12)
        self.assertAlmostEqual(resolved["max_scatter_fraction"], 0.0, places=12)
        self.assertFalse(resolved["scatter_flagged"])

    def test_median_does_not_move_for_one_high_device(self):
        resolved = session_ratios(_session({"WS-2": 0.6}), ALPHA_PER_C)
        self.assertAlmostEqual(
            resolved["median_normalized_current_a"], BASELINE_A, places=12
        )
        self.assertAlmostEqual(resolved["ratios"]["WS-2"], 1.2, places=9)
        self.assertAlmostEqual(resolved["ratios"]["WS-1"], 1.0, places=12)

    def test_session_below_the_group_size_rejected(self):
        session = _session()
        session["readings"] = session["readings"][:4]
        with self.assertRaises(ValueError):
            session_ratios(session, ALPHA_PER_C)

    def test_duplicate_standard_in_a_session_rejected(self):
        session = _session()
        session["readings"][1]["standard_id"] = "WS-1"
        with self.assertRaises(ValueError):
            session_ratios(session, ALPHA_PER_C)

    def test_wild_reading_flags_the_session(self):
        resolved = session_ratios(_session({"WS-2": 0.56}), ALPHA_PER_C)
        self.assertTrue(resolved["scatter_flagged"])
        self.assertAlmostEqual(resolved["max_scatter_fraction"], 0.12, places=9)

    def test_non_list_readings_rejected(self):
        session = _session()
        session["readings"] = "five readings"
        with self.assertRaises(ValueError):
            session_ratios(session, ALPHA_PER_C)

    def test_session_without_an_id_rejected(self):
        session = _session()
        session["session_id"] = "  "
        with self.assertRaises(ValueError):
            session_ratios(session, ALPHA_PER_C)


class SlopeTests(unittest.TestCase):
    def test_slope_of_a_straight_line_recovered(self):
        self.assertAlmostEqual(
            least_squares_slope([(0.0, 1.0), (1.0, 3.0), (2.0, 5.0)]), 2.0, places=9
        )

    def test_slope_with_one_point_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_slope([(1.0, 2.0)])

    def test_slope_with_a_single_x_value_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_slope([(1.0, 2.0), (1.0, 3.0)])


class DriftMetricTests(unittest.TestCase):
    def test_metrics_report_total_annual_and_excursion(self):
        metrics = drift_metrics([(0.0, 1.0), (DAYS_PER_YEAR, 1.01)])
        self.assertAlmostEqual(metrics["total_drift_fraction"], 0.01, places=9)
        self.assertAlmostEqual(metrics["annual_drift_fraction"], 0.01, places=9)
        self.assertAlmostEqual(metrics["max_excursion_fraction"], 0.01, places=9)
        self.assertAlmostEqual(metrics["span_days"], DAYS_PER_YEAR, places=9)

    def test_excursion_catches_a_device_that_came_back(self):
        metrics = drift_metrics(_series([1.0, 1.012, 1.0]))
        self.assertAlmostEqual(metrics["total_drift_fraction"], 0.0, places=12)
        self.assertAlmostEqual(metrics["max_excursion_fraction"], 0.012, places=9)

    def test_out_of_order_sessions_rejected(self):
        with self.assertRaises(ValueError):
            drift_metrics([(100.0, 1.0), (50.0, 1.0)])

    def test_single_session_series_rejected(self):
        with self.assertRaises(ValueError):
            drift_metrics([(0.0, 1.0)])

    def test_non_positive_ratio_rejected(self):
        with self.assertRaises(ValueError):
            drift_metrics([(0.0, 1.0), (10.0, 0.0)])


class StandardDriftTests(unittest.TestCase):
    def test_flat_device_is_stable(self):
        result = assess_standard_drift("WS-1", _series([1.0, 1.0, 1.0]))
        self.assertEqual(result["disposition"], STABLE)
        self.assertEqual(result["reasons"], [])

    def test_drift_exactly_on_the_allowance_is_stable(self):
        result = assess_standard_drift("WS-3", _series([1.0, 1.0025, 1.005]))
        self.assertAlmostEqual(
            result["total_drift_fraction"],
            DEFAULT_STABILITY_CRITERIA["max_ratio_drift_fraction"],
            places=9,
        )
        self.assertAlmostEqual(
            result["annual_drift_fraction"],
            DEFAULT_STABILITY_CRITERIA["max_annual_drift_fraction"],
            places=9,
        )
        self.assertEqual(result["disposition"], STABLE)

    def test_drift_past_the_allowance_is_referred(self):
        result = assess_standard_drift("WS-3", _series([1.0, 1.0035, 1.007]))
        self.assertEqual(result["disposition"], REFER)

    def test_large_drift_is_reported_as_drifted(self):
        result = assess_standard_drift("WS-3", _series([1.0, 1.01, 1.02]))
        self.assertEqual(result["disposition"], DRIFTED)

    def test_excursion_alone_refers_a_device_that_ended_where_it_started(self):
        result = assess_standard_drift("WS-3", _series([1.0, 1.012, 1.0]))
        self.assertAlmostEqual(result["total_drift_fraction"], 0.0, places=12)
        self.assertAlmostEqual(result["annual_drift_fraction"], 0.0, places=9)
        self.assertEqual(result["disposition"], REFER)

    def test_downward_drift_is_judged_on_magnitude(self):
        result = assess_standard_drift("WS-3", _series([1.0, 0.99, 0.98]))
        self.assertLess(result["total_drift_fraction"], 0.0)
        self.assertEqual(result["disposition"], DRIFTED)

    def test_standard_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_standard_drift("", _series([1.0, 1.0, 1.0]))


class CampaignTests(unittest.TestCase):
    def test_flat_campaign_is_stable(self):
        result = assess_sensitivity_stability(_campaign())
        self.assertEqual(result["verdict"], GROUP_STABLE)
        self.assertEqual(result["group_size"], 5)
        self.assertEqual(result["session_count"], 3)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["not_stable_ids"], [])

    def test_one_drifting_device_is_named_and_makes_the_group_unstable(self):
        result = assess_sensitivity_stability(
            _campaign({"WS-3": [0.5, 0.505, 0.510]})
        )
        self.assertEqual(result["verdict"], GROUP_UNSTABLE)
        self.assertEqual(result["drifted_standard_ids"], ["WS-3"])
        self.assertAlmostEqual(
            [r for r in result["standards"] if r["standard_id"] == "WS-3"][0][
                "total_drift_fraction"
            ],
            0.02,
            places=9,
        )

    def test_the_other_devices_stay_stable_while_one_drifts(self):
        result = assess_sensitivity_stability(
            _campaign({"WS-3": [0.5, 0.505, 0.510]})
        )
        stable = [
            entry["standard_id"]
            for entry in result["standards"]
            if entry["disposition"] == STABLE
        ]
        self.assertEqual(stable, ["WS-1", "WS-2", "WS-4", "WS-5"])

    def test_wild_session_is_flagged_and_refers_the_group(self):
        result = assess_sensitivity_stability(_campaign({"WS-2": [0.5, 0.56, 0.5]}))
        self.assertEqual(result["flagged_session_ids"], ["S2"])
        self.assertEqual(result["verdict"], GROUP_REFERRED)

    def test_common_mode_shift_refers_a_group_of_stable_devices(self):
        result = assess_sensitivity_stability(
            _campaign(
                {
                    standard_id: [0.5, 0.49, 0.485]
                    for standard_id in STANDARD_IDS
                }
            )
        )
        for entry in result["standards"]:
            self.assertEqual(entry["disposition"], STABLE)
        self.assertTrue(result["common_mode_flagged"])
        self.assertAlmostEqual(
            result["common_mode_shift_fraction"], -0.03, places=9
        )
        self.assertEqual(result["verdict"], GROUP_REFERRED)

    def test_common_mode_shift_is_invisible_in_the_ratios(self):
        result = assess_sensitivity_stability(
            _campaign(
                {
                    standard_id: [0.5, 0.49, 0.485]
                    for standard_id in STANDARD_IDS
                }
            )
        )
        for session in result["sessions"]:
            self.assertAlmostEqual(session["max_scatter_fraction"], 0.0, places=12)
        for entry in result["standards"]:
            self.assertAlmostEqual(entry["total_drift_fraction"], 0.0, places=12)

    def test_temperature_spread_does_not_look_like_drift(self):
        campaign = _campaign()
        for session in campaign["sessions"]:
            for reading in session["readings"]:
                reading["temperature_c"] = 45.0
                reading["short_circuit_current_a"] = BASELINE_A * 1.01
        result = assess_sensitivity_stability(campaign)
        self.assertEqual(result["verdict"], GROUP_STABLE)
        self.assertAlmostEqual(
            result["sessions"][0]["median_normalized_current_a"],
            BASELINE_A,
            places=9,
        )

    def test_campaign_with_too_few_sessions_rejected(self):
        campaign = _campaign()
        campaign["sessions"] = campaign["sessions"][:2]
        with self.assertRaises(ValueError):
            assess_sensitivity_stability(campaign)

    def test_standard_missing_from_one_session_rejected(self):
        campaign = _campaign()
        campaign["sessions"][1]["readings"][4]["standard_id"] = "WS-6"
        with self.assertRaises(ValueError):
            assess_sensitivity_stability(campaign)

    def test_sessions_out_of_time_order_rejected(self):
        campaign = _campaign()
        campaign["sessions"][2]["elapsed_days"] = 10.0
        with self.assertRaises(ValueError):
            assess_sensitivity_stability(campaign)

    def test_campaign_without_an_id_rejected(self):
        campaign = _campaign()
        campaign["campaign_id"] = "   "
        with self.assertRaises(ValueError):
            assess_sensitivity_stability(campaign)

    def test_non_list_session_collection_rejected(self):
        campaign = _campaign()
        campaign["sessions"] = campaign["sessions"][0]
        with self.assertRaises(ValueError):
            assess_sensitivity_stability(campaign)

    def test_input_is_not_mutated_by_the_screen(self):
        campaign = _campaign({"WS-3": [0.5, 0.505, 0.510]})
        before = copy.deepcopy(campaign)
        assess_sensitivity_stability(campaign)
        self.assertEqual(campaign, before)


if __name__ == "__main__":
    unittest.main()
