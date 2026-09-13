#!/usr/bin/env python3
"""Gate 3 contract test for e2001-detection-sensitivity-tuning.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_detection_sensitivity_tuning.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2001_detection_sensitivity_tuning_logic import (  # noqa: E402
    assess_detection_sensitivity_tuning,
    categorize_drift_driver,
    evaluate_tuning_schedule,
    imbalance_at_elapsed,
    max_tuning_interval_s,
    meets_floor,
    null_depth_at_elapsed,
    null_depth_db,
    null_depth_from_imbalance,
    residual_fraction,
    sensitivity_margin_db,
)

# Imbalance that halves the reference arm: a = 0.5 exactly.
HALF_ARM_DB = 20.0 * math.log10(2.0)
# Amplitude imbalance that alone caps the null at 30 dB, derived by
# inverting -20 log10(1 - a) = 30 independently of the module.
IMBALANCE_FOR_30DB = -20.0 * math.log10(1.0 - 10.0 ** (-1.5))
# Phase error that alone caps the null at 30 dB: 2 - 2 cos(phi) = 1e-3.
PHASE_FOR_30DB = math.acos(1.0 - 0.5e-3)


class TestNullDepthFromPower(unittest.TestCase):
    def test_forty_db_null(self):
        self.assertAlmostEqual(null_depth_db(100.0, 0.01), 40.0, places=9)

    def test_equal_power_is_zero_db(self):
        self.assertAlmostEqual(null_depth_db(12.5, 12.5), 0.0, places=12)

    def test_residual_above_incident_rejected(self):
        with self.assertRaises(ValueError):
            null_depth_db(1.0, 2.0)

    def test_zero_residual_rejected(self):
        with self.assertRaises(ValueError):
            null_depth_db(1.0, 0.0)

    def test_negative_incident_rejected(self):
        with self.assertRaises(ValueError):
            null_depth_db(-1.0, 0.1)

    def test_non_numeric_power_rejected(self):
        with self.assertRaises(ValueError):
            null_depth_db("100", 0.1)

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            null_depth_db(True, 0.1)


class TestResidualFraction(unittest.TestCase):
    def test_perfect_match_is_unbounded_null(self):
        self.assertTrue(math.isinf(null_depth_from_imbalance(0.0, 0.0)))

    def test_half_amplitude_arm_leaves_quarter_power(self):
        self.assertAlmostEqual(residual_fraction(0.0, HALF_ARM_DB), 0.25, places=12)

    def test_half_amplitude_arm_null_depth(self):
        self.assertAlmostEqual(
            null_depth_from_imbalance(0.0, HALF_ARM_DB), HALF_ARM_DB, places=9
        )

    def test_antiphase_arms_add_instead_of_cancel(self):
        self.assertAlmostEqual(
            null_depth_from_imbalance(math.pi, 0.0), -10.0 * math.log10(4.0), places=9
        )

    def test_quadrature_arms(self):
        self.assertAlmostEqual(
            null_depth_from_imbalance(math.pi / 2.0, 0.0),
            -10.0 * math.log10(2.0),
            places=9,
        )

    def test_phase_only_thirty_db_cap(self):
        self.assertAlmostEqual(
            null_depth_from_imbalance(PHASE_FOR_30DB, 0.0), 30.0, places=6
        )

    def test_amplitude_only_thirty_db_cap(self):
        self.assertAlmostEqual(
            null_depth_from_imbalance(0.0, IMBALANCE_FOR_30DB), 30.0, places=6
        )

    def test_phase_beyond_pi_rejected(self):
        with self.assertRaises(ValueError):
            residual_fraction(math.pi + 0.1, 0.0)

    def test_non_numeric_imbalance_rejected(self):
        with self.assertRaises(ValueError):
            residual_fraction(0.0, None)


class TestDrift(unittest.TestCase):
    def test_linear_growth_of_both_mismatches(self):
        phi, imbalance = imbalance_at_elapsed(100.0, 1e-4, 2e-3, 0.001, 0.02)
        self.assertAlmostEqual(phi, 0.001 + 1e-2, places=12)
        self.assertAlmostEqual(imbalance, 0.02 + 0.2, places=12)

    def test_phase_error_clamps_at_pi(self):
        phi, _ = imbalance_at_elapsed(1.0e6, 1.0, 0.0)
        self.assertAlmostEqual(phi, math.pi, places=12)

    def test_zero_elapsed_returns_initial_state(self):
        phi, imbalance = imbalance_at_elapsed(0.0, 1.0, 1.0, 0.05, 0.3)
        self.assertAlmostEqual(phi, 0.05, places=12)
        self.assertAlmostEqual(imbalance, 0.3, places=12)

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            imbalance_at_elapsed(-1.0, 1e-4, 1e-4)

    def test_negative_drift_rate_rejected(self):
        with self.assertRaises(ValueError):
            imbalance_at_elapsed(10.0, -1e-4, 1e-4)

    def test_initial_phase_beyond_pi_rejected(self):
        with self.assertRaises(ValueError):
            imbalance_at_elapsed(10.0, 1e-4, 1e-4, 4.0, 0.0)

    def test_null_depth_decays_monotonically(self):
        depths = [
            null_depth_at_elapsed(t, 1e-5, 1e-4, 0.0, 0.0)
            for t in (1.0, 10.0, 100.0, 1000.0)
        ]
        for earlier, later in zip(depths, depths[1:]):
            self.assertLess(later, earlier)


class TestFloorComparison(unittest.TestCase):
    def test_exact_equality_meets_floor(self):
        self.assertTrue(meets_floor(30.0, 30.0))

    def test_representation_error_absorbed(self):
        drifted = 30.0 - (0.1 + 0.2 - 0.3)
        self.assertTrue(meets_floor(drifted, 30.0))

    def test_real_shortfall_fails(self):
        self.assertFalse(meets_floor(29.9, 30.0))

    def test_unbounded_null_meets_any_floor(self):
        self.assertTrue(meets_floor(float("inf"), 60.0))

    def test_margin_is_signed(self):
        self.assertAlmostEqual(sensitivity_margin_db(34.5, 30.0), 4.5, places=12)
        self.assertAlmostEqual(sensitivity_margin_db(27.0, 30.0), -3.0, places=12)

    def test_margin_of_perfect_null_is_unbounded(self):
        self.assertTrue(math.isinf(sensitivity_margin_db(float("inf"), 30.0)))

    def test_zero_required_floor_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_margin_db(30.0, 0.0)


class TestTuningInterval(unittest.TestCase):
    def test_no_drift_gives_unbounded_interval(self):
        self.assertTrue(math.isinf(max_tuning_interval_s(30.0, 0.0, 0.0)))

    def test_amplitude_drift_interval_matches_closed_form(self):
        rate = 1e-3
        interval = max_tuning_interval_s(30.0, 0.0, rate)
        self.assertAlmostEqual(interval, IMBALANCE_FOR_30DB / rate, delta=1e-3)

    def test_phase_drift_interval_matches_closed_form(self):
        rate = 1e-5
        interval = max_tuning_interval_s(30.0, rate, 0.0)
        self.assertAlmostEqual(interval, PHASE_FOR_30DB / rate, delta=1e-3)

    def test_depth_holds_at_interval_and_fails_just_after(self):
        interval = max_tuning_interval_s(30.0, 0.0, 1e-3)
        self.assertTrue(meets_floor(null_depth_at_elapsed(interval, 0.0, 1e-3), 30.0))
        self.assertFalse(
            meets_floor(null_depth_at_elapsed(interval + 1.0, 0.0, 1e-3), 30.0)
        )

    def test_slow_drift_returns_horizon(self):
        self.assertAlmostEqual(
            max_tuning_interval_s(30.0, 1e-12, 0.0, horizon_s=3600.0),
            3600.0,
            places=9,
        )

    def test_floor_unreachable_after_tuning_rejected(self):
        with self.assertRaises(ValueError):
            max_tuning_interval_s(60.0, 1e-5, 1e-4, 0.0, 0.5)

    def test_negative_horizon_rejected(self):
        with self.assertRaises(ValueError):
            max_tuning_interval_s(30.0, 1e-5, 0.0, horizon_s=-10.0)


class TestDriftDriver(unittest.TestCase):
    def test_phase_dominated(self):
        self.assertEqual(categorize_drift_driver(1e-3, 1e-9, 100.0), "phase-dominated")

    def test_amplitude_dominated(self):
        self.assertEqual(
            categorize_drift_driver(1e-9, 1e-2, 100.0), "amplitude-dominated"
        )

    def test_no_drift(self):
        self.assertEqual(categorize_drift_driver(0.0, 0.0, 100.0), "no-drift")

    def test_balanced_when_both_cost_the_same(self):
        self.assertEqual(
            categorize_drift_driver(
                PHASE_FOR_30DB / 100.0, IMBALANCE_FOR_30DB / 100.0, 100.0
            ),
            "balanced",
        )

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            categorize_drift_driver(1e-4, 1e-4, 0.0)


class TestSchedule(unittest.TestCase):
    def test_covered_schedule_has_no_findings(self):
        self.assertEqual(evaluate_tuning_schedule([0.0, 250.0, 500.0], 600.0, 300.0), [])

    def test_gap_exactly_at_interval_is_covered(self):
        self.assertEqual(evaluate_tuning_schedule([0.0, 300.0, 600.0], 600.0, 300.0), [])

    def test_representation_error_in_gap_is_absorbed(self):
        epochs = [0.0, 0.1 + 0.2]
        self.assertGreater(epochs[1], 0.3)
        self.assertEqual(evaluate_tuning_schedule(epochs, 0.6, 0.3), [])

    def test_long_gap_flagged(self):
        findings = evaluate_tuning_schedule([0.0, 400.0], 400.0, 300.0)
        self.assertEqual([f["code"] for f in findings], ["tuning-gap-exceeded"])
        self.assertAlmostEqual(findings[0]["gap_s"], 400.0, places=9)

    def test_uncovered_run_end_flagged(self):
        findings = evaluate_tuning_schedule([0.0, 300.0], 900.0, 300.0)
        self.assertEqual([f["code"] for f in findings], ["run-end-uncovered"])

    def test_late_first_tuning_flagged(self):
        findings = evaluate_tuning_schedule([500.0, 520.0], 600.0, 30.0)
        self.assertIn("no-tuning-at-run-start", [f["code"] for f in findings])

    def test_unbounded_interval_never_flags(self):
        self.assertEqual(
            evaluate_tuning_schedule([0.0], 10000.0, float("inf")),
            [],
        )

    def test_empty_schedule_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_schedule([], 600.0, 300.0)

    def test_non_sequence_schedule_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_schedule(300.0, 600.0, 300.0)

    def test_non_increasing_epochs_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_schedule([0.0, 300.0, 300.0], 600.0, 300.0)

    def test_epoch_after_run_end_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_schedule([0.0, 700.0], 600.0, 300.0)

    def test_negative_epoch_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_schedule([-1.0, 300.0], 600.0, 300.0)


class TestAssessment(unittest.TestCase):
    def base_config(self):
        return {
            "required_null_depth_db": 30.0,
            "phase_drift_rad_per_s": 1e-5,
            "amplitude_drift_db_per_s": 0.0,
            "tuning_times_s": [0.0, 300.0],
            "run_duration_s": 600.0,
        }

    def test_compliant_run(self):
        result = assess_detection_sensitivity_tuning(self.base_config())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["max_tuning_interval_s"], PHASE_FOR_30DB / 1e-5, delta=1e-3
        )
        self.assertEqual(result["drift_driver"], "phase-dominated")

    def test_fast_drift_run_is_not_compliant(self):
        config = self.base_config()
        config["phase_drift_rad_per_s"] = 1e-3
        result = assess_detection_sensitivity_tuning(config)
        self.assertFalse(result["compliant"])
        self.assertIn("tuning-gap-exceeded", [f["code"] for f in result["findings"]])

    def test_chain_that_cannot_reach_the_floor(self):
        config = self.base_config()
        config["required_null_depth_db"] = 60.0
        config["initial_amplitude_imbalance_db"] = 0.5
        result = assess_detection_sensitivity_tuning(config)
        self.assertFalse(result["compliant"])
        self.assertEqual(
            [f["code"] for f in result["findings"]],
            ["floor-unreachable-after-tuning"],
        )
        self.assertIsNone(result["max_tuning_interval_s"])
        self.assertEqual(result["drift_driver"], "not-evaluated")
        self.assertLess(result["sensitivity_margin_db"], 0.0)

    def test_still_run_gives_unbounded_interval(self):
        config = self.base_config()
        config["phase_drift_rad_per_s"] = 0.0
        result = assess_detection_sensitivity_tuning(config)
        self.assertTrue(math.isinf(result["max_tuning_interval_s"]))
        self.assertTrue(result["compliant"])

    def test_unknown_key_rejected(self):
        config = self.base_config()
        config["chamber_pressure_pa"] = 1e-5
        with self.assertRaises(ValueError):
            assess_detection_sensitivity_tuning(config)

    def test_missing_key_rejected(self):
        config = self.base_config()
        del config["run_duration_s"]
        with self.assertRaises(ValueError):
            assess_detection_sensitivity_tuning(config)

    def test_non_mapping_config_rejected(self):
        with self.assertRaises(ValueError):
            assess_detection_sensitivity_tuning(["required_null_depth_db", 30.0])


if __name__ == "__main__":
    unittest.main()
