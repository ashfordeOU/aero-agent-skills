#!/usr/bin/env python3
"""Contract test for the clause 6.8.3 current-path robustness logic."""

import unittest

from e2006_current_path_environmental_robustness_logic import (
    DEFAULT_ALLOWABLE_DRIFT,
    DISCONTINUITY_THRESHOLD_US,
    assess_current_path,
    categorize_environment,
    check_exposure_level,
    count_discontinuity_events,
    evaluate_exposure,
    post_exposure_limit,
    required_exposures,
    resistance_drift,
    summarize_robustness_campaign,
)


def exposure(environment, **overrides):
    record = {
        "environment": environment,
        "applied_level": 14.1,
        "qualification_level": 14.1,
        "duration_s": 120.0,
        "required_duration_s": 120.0,
        "monitored": True,
        "discontinuity_events_us": [],
        "pre_ohm": 1.0e-3,
        "post_ohm": 1.02e-3,
    }
    record.update(overrides)
    return record


def fault_path(**overrides):
    path = {
        "id": "PATH-001",
        "path_class": "fault-current-return-path",
        "exposures": [
            exposure("random-vibration"),
            exposure("mechanical-shock", applied_level=1400.0, qualification_level=1400.0),
            exposure(
                "thermal-cycling",
                applied_level=12.0,
                qualification_level=8.0,
                monitored=False,
                duration_s=None,
                required_duration_s=None,
            ),
        ],
    }
    path.update(overrides)
    return path


class TestCategorizeEnvironment(unittest.TestCase):
    def test_canonical_name_round_trips(self):
        self.assertEqual(categorize_environment("random-vibration"), "random-vibration")

    def test_pyroshock_maps_to_mechanical_shock(self):
        self.assertEqual(categorize_environment("pyroshock"), "mechanical-shock")

    def test_case_and_underscore_normalized(self):
        self.assertEqual(categorize_environment(" TVAC "), "thermal-vacuum")

    def test_acoustic_alias(self):
        self.assertEqual(categorize_environment("diffuse-acoustic-field"), "acoustic-noise")

    def test_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            categorize_environment("solar-illumination")

    def test_blank_environment_raises(self):
        with self.assertRaises(ValueError):
            categorize_environment("   ")

    def test_non_string_environment_raises(self):
        with self.assertRaises(ValueError):
            categorize_environment(3.5)


class TestRequiredExposures(unittest.TestCase):
    def test_fault_path_needs_shock(self):
        self.assertIn("mechanical-shock", required_exposures("fault-current-return-path"))

    def test_signal_reference_does_not_need_shock(self):
        self.assertNotIn("mechanical-shock", required_exposures("signal-reference-bond"))

    def test_bleed_path_needs_humidity(self):
        self.assertIn("humidity-and-corrosion", required_exposures("static-bleed-path"))

    def test_unknown_path_class_raises(self):
        with self.assertRaises(ValueError):
            required_exposures("antenna-feed-path")

    def test_non_string_path_class_raises(self):
        with self.assertRaises(ValueError):
            required_exposures(None)


class TestPostExposureLimit(unittest.TestCase):
    def test_fault_path_carries_the_tightest_limit(self):
        self.assertLess(
            post_exposure_limit("fault-current-return-path"),
            post_exposure_limit("discharge-return-path"),
        )

    def test_bleed_path_limit_is_high(self):
        self.assertGreater(post_exposure_limit("static-bleed-path"), 1.0)

    def test_unknown_path_class_raises(self):
        with self.assertRaises(ValueError):
            post_exposure_limit("thruster-bond")


class TestCheckExposureLevel(unittest.TestCase):
    def test_over_level_run_is_adequate(self):
        result = check_exposure_level("random-vibration", 16.0, 14.1)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["ratio"], 16.0 / 14.1)

    def test_under_level_run_is_flagged(self):
        result = check_exposure_level("random-vibration", 10.0, 14.1)
        self.assertFalse(result["adequate"])
        self.assertEqual(len(result["findings"]), 1)

    def test_exact_level_is_adequate(self):
        self.assertTrue(check_exposure_level("random-vibration", 14.1, 14.1)["adequate"])

    def test_accumulated_level_at_the_requirement_is_adequate(self):
        # A run level assembled from eight equal band contributions lands a
        # few ULPs below the qualification level; that is representation
        # error, not an under-run.
        applied = 0.0
        for _ in range(8):
            applied += 14.1 / 8.0
        self.assertLess(applied, 14.1)
        self.assertTrue(check_exposure_level("random-vibration", applied, 14.1)["adequate"])

    def test_unit_is_reported(self):
        self.assertEqual(check_exposure_level("mechanical-shock", 1400.0, 1400.0)["unit"], "g-srs-peak")

    def test_wrong_unit_raises(self):
        with self.assertRaises(ValueError):
            check_exposure_level("random-vibration", 14.1, 14.1, unit="g-srs-peak")

    def test_matching_unit_is_accepted(self):
        self.assertTrue(check_exposure_level("random-vibration", 14.1, 14.1, unit="grms")["adequate"])

    def test_zero_level_raises(self):
        with self.assertRaises(ValueError):
            check_exposure_level("random-vibration", 0.0, 14.1)

    def test_negative_qualification_level_raises(self):
        with self.assertRaises(ValueError):
            check_exposure_level("random-vibration", 14.1, -1.0)

    def test_non_numeric_level_raises(self):
        with self.assertRaises(ValueError):
            check_exposure_level("random-vibration", "14.1 grms", 14.1)


class TestCountDiscontinuityEvents(unittest.TestCase):
    def test_no_events_counts_zero(self):
        self.assertEqual(count_discontinuity_events([]), 0)

    def test_short_glitch_below_threshold_is_not_counted(self):
        self.assertEqual(count_discontinuity_events([0.2, 0.5]), 0)

    def test_event_at_the_threshold_is_counted(self):
        self.assertEqual(count_discontinuity_events([DISCONTINUITY_THRESHOLD_US]), 1)

    def test_long_events_are_counted(self):
        self.assertEqual(count_discontinuity_events([0.1, 5.0, 12.0]), 2)

    def test_custom_threshold_is_honoured(self):
        self.assertEqual(count_discontinuity_events([5.0, 12.0], threshold_us=10.0), 1)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            count_discontinuity_events([-1.0])

    def test_non_numeric_duration_raises(self):
        with self.assertRaises(ValueError):
            count_discontinuity_events(["brief"])

    def test_non_list_events_raises(self):
        with self.assertRaises(ValueError):
            count_discontinuity_events(5.0)

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            count_discontinuity_events([1.0], threshold_us=0.0)


class TestResistanceDrift(unittest.TestCase):
    def test_upward_drift_is_positive(self):
        drift = resistance_drift(1.0e-3, 1.1e-3)
        self.assertAlmostEqual(drift["fraction"], 0.1)
        self.assertGreater(drift["delta_ohm"], 0.0)

    def test_downward_drift_is_negative(self):
        self.assertLess(resistance_drift(1.0e-3, 0.9e-3)["fraction"], 0.0)

    def test_unchanged_resistance_gives_zero_drift(self):
        self.assertAlmostEqual(resistance_drift(2.0e-3, 2.0e-3)["fraction"], 0.0)

    def test_zero_pre_resistance_raises(self):
        with self.assertRaises(ValueError):
            resistance_drift(0.0, 1.0e-3)

    def test_negative_post_resistance_raises(self):
        with self.assertRaises(ValueError):
            resistance_drift(1.0e-3, -1.0e-3)

    def test_non_finite_post_resistance_raises(self):
        with self.assertRaises(ValueError):
            resistance_drift(1.0e-3, float("inf"))


class TestEvaluateExposure(unittest.TestCase):
    def test_clean_exposure_passes(self):
        result = evaluate_exposure("fault-current-return-path", exposure("random-vibration"))
        self.assertTrue(result["passed"], result["findings"])
        self.assertEqual(result["discontinuity_events"], 0)

    def test_under_level_run_fails(self):
        result = evaluate_exposure(
            "fault-current-return-path", exposure("random-vibration", applied_level=9.0)
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["level_adequate"])

    def test_short_duration_fails(self):
        result = evaluate_exposure(
            "fault-current-return-path", exposure("random-vibration", duration_s=60.0)
        )
        self.assertFalse(result["passed"])
        self.assertTrue(any("held for" in f for f in result["findings"]))

    def test_unmonitored_vibration_fails(self):
        result = evaluate_exposure(
            "fault-current-return-path", exposure("random-vibration", monitored=False)
        )
        self.assertFalse(result["passed"])
        self.assertTrue(any("live continuity monitoring" in f for f in result["findings"]))

    def test_unmonitored_thermal_cycling_is_accepted(self):
        result = evaluate_exposure(
            "fault-current-return-path",
            exposure("thermal-cycling", monitored=False, duration_s=None, required_duration_s=None),
        )
        self.assertTrue(result["passed"], result["findings"])

    def test_monitored_open_fails_even_when_the_post_reading_is_good(self):
        result = evaluate_exposure(
            "fault-current-return-path",
            exposure("random-vibration", discontinuity_events_us=[4.0], post_ohm=1.0e-3),
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["discontinuity_events"], 1)

    def test_drift_beyond_the_allowance_fails(self):
        result = evaluate_exposure(
            "fault-current-return-path", exposure("random-vibration", post_ohm=1.5e-3)
        )
        self.assertFalse(result["passed"])
        self.assertTrue(any("drifted" in f for f in result["findings"]))

    def test_drift_exactly_at_the_allowance_passes(self):
        # (1.1e-3 - 1.0e-3) / 1.0e-3 evaluates a few ULPs above 0.10.
        fraction = (1.1e-3 - 1.0e-3) / 1.0e-3
        self.assertGreater(fraction, DEFAULT_ALLOWABLE_DRIFT)
        result = evaluate_exposure(
            "fault-current-return-path", exposure("random-vibration", post_ohm=1.1e-3)
        )
        self.assertTrue(result["passed"], result["findings"])

    def test_post_reading_at_the_class_limit_passes(self):
        # Ten 0.25 mohm segment drops sum to the 2.5 mohm limit but land a few
        # ULPs above it in binary floating point.
        post = 0.0
        for _ in range(10):
            post += 2.5e-4
        self.assertGreater(post, post_exposure_limit("fault-current-return-path"))
        result = evaluate_exposure(
            "fault-current-return-path",
            exposure("random-vibration", pre_ohm=2.4e-3, post_ohm=post),
        )
        self.assertTrue(result["passed"], result["findings"])

    def test_post_reading_above_the_class_limit_fails(self):
        result = evaluate_exposure(
            "fault-current-return-path",
            exposure("random-vibration", pre_ohm=2.9e-3, post_ohm=3.0e-3),
        )
        self.assertFalse(result["passed"])
        self.assertTrue(any("exceeds" in f for f in result["findings"]))

    def test_tighter_allowance_turns_a_pass_into_a_finding(self):
        record = exposure("random-vibration", post_ohm=1.05e-3)
        self.assertTrue(evaluate_exposure("fault-current-return-path", record)["passed"])
        self.assertFalse(
            evaluate_exposure("fault-current-return-path", record, allowable_drift=0.01)["passed"]
        )

    def test_non_boolean_monitored_flag_raises(self):
        with self.assertRaises(ValueError):
            evaluate_exposure("fault-current-return-path", exposure("random-vibration", monitored="yes"))

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            evaluate_exposure("fault-current-return-path", ["random-vibration"])

    def test_missing_pre_resistance_raises(self):
        record = exposure("random-vibration")
        del record["pre_ohm"]
        with self.assertRaises(ValueError):
            evaluate_exposure("fault-current-return-path", record)

    def test_duration_without_a_requirement_raises(self):
        with self.assertRaises(ValueError):
            evaluate_exposure(
                "fault-current-return-path",
                exposure("random-vibration", required_duration_s=None),
            )

    def test_zero_allowable_drift_raises(self):
        with self.assertRaises(ValueError):
            evaluate_exposure("fault-current-return-path", exposure("random-vibration"), allowable_drift=0.0)


class TestAssessCurrentPath(unittest.TestCase):
    def test_complete_campaign_is_robust(self):
        result = assess_current_path(fault_path())
        self.assertEqual(result["status"], "robust")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing_exposures"], [])

    def test_missing_shock_exposure_is_reported(self):
        path = fault_path()
        path["exposures"] = [e for e in path["exposures"] if e["environment"] != "mechanical-shock"]
        result = assess_current_path(path)
        self.assertEqual(result["missing_exposures"], ["mechanical-shock"])
        self.assertEqual(result["status"], "not-demonstrated")

    def test_worst_post_reading_is_tracked(self):
        path = fault_path()
        path["exposures"][1]["post_ohm"] = 1.05e-3
        result = assess_current_path(path)
        self.assertAlmostEqual(result["worst_post_ohm"], 1.05e-3)

    def test_max_drift_is_tracked(self):
        result = assess_current_path(fault_path())
        self.assertAlmostEqual(result["max_drift_fraction"], 0.02, places=6)

    def test_signal_reference_path_needs_fewer_exposures(self):
        path = {
            "id": "PATH-SIG",
            "path_class": "signal-reference-bond",
            "exposures": [
                exposure("random-vibration"),
                exposure(
                    "thermal-cycling",
                    applied_level=10.0,
                    qualification_level=8.0,
                    monitored=False,
                    duration_s=None,
                    required_duration_s=None,
                ),
            ],
        }
        self.assertEqual(assess_current_path(path)["status"], "robust")

    def test_one_failing_exposure_opens_the_path(self):
        path = fault_path()
        path["exposures"][0]["discontinuity_events_us"] = [3.0]
        result = assess_current_path(path)
        self.assertEqual(result["status"], "not-demonstrated")
        self.assertTrue(any("discontinuity" in f for f in result["findings"]))

    def test_environments_covered_are_sorted(self):
        result = assess_current_path(fault_path())
        self.assertEqual(
            result["environments_covered"],
            ["mechanical-shock", "random-vibration", "thermal-cycling"],
        )

    def test_duplicate_exposure_raises(self):
        path = fault_path()
        path["exposures"].append(exposure("random-vibration"))
        with self.assertRaises(ValueError):
            assess_current_path(path)

    def test_empty_exposure_list_raises(self):
        with self.assertRaises(ValueError):
            assess_current_path(fault_path(exposures=[]))

    def test_blank_path_id_raises(self):
        with self.assertRaises(ValueError):
            assess_current_path(fault_path(id="  "))

    def test_unknown_path_class_raises(self):
        with self.assertRaises(ValueError):
            assess_current_path(fault_path(path_class="umbilical-bond"))

    def test_non_mapping_path_raises(self):
        with self.assertRaises(ValueError):
            assess_current_path("PATH-001")


class TestSummarizeRobustnessCampaign(unittest.TestCase):
    def test_clean_campaign_closes(self):
        summary = summarize_robustness_campaign([fault_path()])
        self.assertTrue(summary["campaign_closed"])
        self.assertEqual(summary["robust_count"], 1)

    def test_one_open_path_opens_the_campaign(self):
        weak = fault_path(id="PATH-002")
        weak["exposures"][0]["monitored"] = False
        summary = summarize_robustness_campaign([fault_path(), weak])
        self.assertFalse(summary["campaign_closed"])
        self.assertEqual(summary["open_ids"], ["PATH-002"])

    def test_counts_add_up(self):
        summary = summarize_robustness_campaign([fault_path(), fault_path(id="PATH-003")])
        self.assertEqual(summary["robust_count"] + len(summary["open_ids"]), 2)

    def test_allowance_is_passed_through_to_every_path(self):
        summary = summarize_robustness_campaign([fault_path()], allowable_drift=0.001)
        self.assertFalse(summary["campaign_closed"])

    def test_empty_campaign_raises(self):
        with self.assertRaises(ValueError):
            summarize_robustness_campaign([])

    def test_non_list_campaign_raises(self):
        with self.assertRaises(ValueError):
            summarize_robustness_campaign(fault_path())


if __name__ == "__main__":
    unittest.main()
