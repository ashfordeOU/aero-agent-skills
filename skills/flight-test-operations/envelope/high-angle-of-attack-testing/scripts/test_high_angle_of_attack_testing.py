#!/usr/bin/env python3
"""Gate 3 contract test for the high angle of attack testing leaf.

Stdlib unittest only, offline, no network. Run directly:
python3 scripts/test_high_angle_of_attack_testing.py
"""

import math
import unittest

from high_angle_of_attack_testing_logic import (
    PITCH_REF_DEG,
    ROLL_REF_DEG,
    W_PITCH,
    W_ROLL,
    W_YAW,
    YAW_REF_DEG,
    aoa_least_squares_calibration,
    apply_aoa_correction,
    build_test_matrix,
    departure_resistance_index,
    spin_entry_resistance_verdict,
    spin_recovery_verdict,
    stall_margin_deg,
    stall_margin_verdict,
)

# Tower fly-by calibration set from the SKILL.md worked example.
INDICATED = [6.0, 8.0, 10.0, 12.0, 14.0]
REFERENCE = [8.2, 10.1, 12.0, 13.9, 15.8]


class AoACalibrationTests(unittest.TestCase):
    def test_recovers_known_bias(self):
        # reference = indicated + 2.0 deg: pure bias, scale must be 1.
        ind = [5.0, 7.0, 9.0, 11.0]
        ref = [7.0, 9.0, 11.0, 13.0]
        cal = aoa_least_squares_calibration(ind, ref)
        self.assertAlmostEqual(cal["bias_deg"], 2.0, places=6)
        self.assertAlmostEqual(cal["scale"], 1.0, places=6)
        self.assertAlmostEqual(cal["rms_residual_deg"], 0.0, places=6)

    def test_calibration_corrects_known_bias(self):
        # The corrected value must reproduce the reference at each point.
        ind = [5.0, 7.0, 9.0, 11.0]
        ref = [7.0, 9.0, 11.0, 13.0]
        cal = aoa_least_squares_calibration(ind, ref)
        for i, aoa in enumerate(ind):
            self.assertAlmostEqual(
                apply_aoa_correction(aoa, cal), ref[i], places=6
            )

    def test_recovers_known_scale_and_bias(self):
        # reference = 1.1 * indicated - 1.0 deg: scale and bias combined.
        ind = [4.0, 8.0, 12.0, 16.0]
        ref = [3.4, 7.8, 12.2, 16.6]
        cal = aoa_least_squares_calibration(ind, ref)
        self.assertAlmostEqual(cal["scale"], 1.1, places=6)
        self.assertAlmostEqual(cal["bias_deg"], -1.0, places=6)
        self.assertAlmostEqual(apply_aoa_correction(10.0, cal), 10.0, places=6)

    def test_tower_fly_by_worked_example(self):
        cal = aoa_least_squares_calibration(INDICATED, REFERENCE)
        self.assertAlmostEqual(cal["scale"], 0.95, places=6)
        self.assertAlmostEqual(cal["bias_deg"], 2.5, places=6)
        self.assertAlmostEqual(cal["rms_residual_deg"], 0.0, places=3)
        self.assertAlmostEqual(cal["max_residual_deg"], 0.0, places=3)
        self.assertEqual(cal["n"], 5)
        self.assertAlmostEqual(apply_aoa_correction(10.0, cal), 12.0, places=6)

    def test_residual_spread_reported(self):
        # A noisy point set still reports the residual statistics.
        ind = [5.0, 6.0, 7.0, 8.0]
        ref = [7.2, 7.9, 9.1, 10.0]
        cal = aoa_least_squares_calibration(ind, ref)
        self.assertGreaterEqual(cal["max_residual_deg"], cal["rms_residual_deg"])

    def test_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            aoa_least_squares_calibration([5.0, 7.0], [5.0, 7.0, 9.0])

    def test_single_point_raises(self):
        with self.assertRaises(ValueError):
            aoa_least_squares_calibration([5.0], [7.0])

    def test_constant_indicated_raises(self):
        with self.assertRaises(ValueError):
            aoa_least_squares_calibration([5.0, 5.0, 5.0], [7.0, 8.0, 9.0])

    def test_non_finite_data_raises(self):
        with self.assertRaises(ValueError):
            aoa_least_squares_calibration([5.0, float("nan")], [7.0, 8.0])
        with self.assertRaises(ValueError):
            aoa_least_squares_calibration([5.0, 6.0], [7.0, float("inf")])

    def test_apply_correction_invalid_raises(self):
        cal = aoa_least_squares_calibration(INDICATED, REFERENCE)
        with self.assertRaises(ValueError):
            apply_aoa_correction(float("nan"), cal)
        with self.assertRaises(ValueError):
            apply_aoa_correction(10.0, {"scale": 1.0})
        with self.assertRaises(ValueError):
            apply_aoa_correction(10.0, {"bias_deg": 2.0})


class StallMarginTests(unittest.TestCase):
    def test_margin_positive_when_warning_precedes(self):
        self.assertAlmostEqual(stall_margin_deg(15.5, 12.0), 3.5, places=9)

    def test_margin_negative_when_warning_late(self):
        self.assertAlmostEqual(stall_margin_deg(15.5, 16.0), -0.5, places=9)

    def test_verdict_passes_with_comfortable_margin(self):
        v = stall_margin_verdict(15.5, 12.0, 2.0)
        self.assertAlmostEqual(v["margin_deg"], 3.5, places=9)
        self.assertEqual(v["required_margin_deg"], 2.0)
        self.assertTrue(v["ok"])

    def test_verdict_flips_at_threshold(self):
        # 3.5 deg margin: fails a 4.0 deg requirement, passes at 3.5 and 3.0.
        self.assertFalse(stall_margin_verdict(15.5, 12.0, 4.0)["ok"])
        self.assertTrue(stall_margin_verdict(15.5, 12.0, 3.5)["ok"])
        self.assertTrue(stall_margin_verdict(15.5, 12.0, 3.0)["ok"])

    def test_verdict_late_warning_fails(self):
        v = stall_margin_verdict(15.5, 16.0, 2.0)
        self.assertAlmostEqual(v["margin_deg"], -0.5, places=9)
        self.assertFalse(v["ok"])

    def test_zero_required_margin_passes_at_stall(self):
        self.assertTrue(stall_margin_verdict(15.5, 15.5, 0.0)["ok"])

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            stall_margin_verdict(15.5, 12.0, -0.5)

    def test_non_finite_angles_raise(self):
        with self.assertRaises(ValueError):
            stall_margin_deg(float("nan"), 12.0)
        with self.assertRaises(ValueError):
            stall_margin_verdict(15.5, float("inf"), 2.0)


class DepartureResistanceTests(unittest.TestCase):
    def test_clean_aircraft_high_resistance(self):
        v = departure_resistance_index(2.0, 1.0, 1.0)
        self.assertAlmostEqual(
            v["index"],
            1.0 - (W_ROLL * 2.0 / ROLL_REF_DEG
                   + W_YAW * 1.0 / YAW_REF_DEG
                   + W_PITCH * 1.0 / PITCH_REF_DEG),
            places=9,
        )
        self.assertEqual(v["classification"], "high")

    def test_moderate_departure(self):
        # roll 8, yaw 4, pitch 3 -> penalty 0.38 -> index 0.62.
        v = departure_resistance_index(8.0, 4.0, 3.0)
        self.assertAlmostEqual(v["index"], 0.62, places=9)
        self.assertEqual(v["classification"], "moderate")

    def test_severe_departure_low_resistance(self):
        v = departure_resistance_index(20.0, 10.0, 10.0)
        self.assertAlmostEqual(v["index"], 0.0, places=9)
        self.assertEqual(v["classification"], "low")

    def test_index_stays_in_unit_range(self):
        v = departure_resistance_index(60.0, 40.0, 30.0)
        self.assertGreaterEqual(v["index"], 0.0)
        self.assertLessEqual(v["index"], 1.0)
        self.assertEqual(v["classification"], "low")

    def test_worked_example_high_resistance(self):
        v = departure_resistance_index(4.0, 2.0, 1.0)
        self.assertAlmostEqual(v["index"], 0.82, places=9)
        self.assertEqual(v["classification"], "high")

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            departure_resistance_index(-1.0, 2.0, 1.0)
        with self.assertRaises(ValueError):
            departure_resistance_index(2.0, float("nan"), 1.0)


class SpinEntryResistanceTests(unittest.TestCase):
    def test_high_resistance_within_half_limits(self):
        v = spin_entry_resistance_verdict(4.0, 5.0, 20.0, 20.0)
        self.assertAlmostEqual(v["ratio"], 0.25, places=9)
        self.assertEqual(v["resistance"], "high")
        self.assertTrue(v["ok"])

    def test_moderate_resistance_within_limits(self):
        v = spin_entry_resistance_verdict(12.0, 15.0, 20.0, 20.0)
        self.assertAlmostEqual(v["ratio"], 0.75, places=9)
        self.assertEqual(v["resistance"], "moderate")
        self.assertTrue(v["ok"])

    def test_low_resistance_exceeds_limits(self):
        v = spin_entry_resistance_verdict(20.0, 25.0, 20.0, 20.0)
        self.assertAlmostEqual(v["ratio"], 1.25, places=9)
        self.assertEqual(v["resistance"], "low")
        self.assertFalse(v["ok"])

    def test_boundary_at_limit_still_ok(self):
        v = spin_entry_resistance_verdict(20.0, 10.0, 20.0, 20.0)
        self.assertAlmostEqual(v["ratio"], 1.0, places=9)
        self.assertEqual(v["resistance"], "moderate")
        self.assertTrue(v["ok"])

    def test_uses_worst_axis(self):
        v = spin_entry_resistance_verdict(5.0, 18.0, 20.0, 20.0)
        self.assertAlmostEqual(v["ratio"], 0.9, places=9)
        self.assertEqual(v["resistance"], "moderate")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            spin_entry_resistance_verdict(-1.0, 5.0, 20.0, 20.0)
        with self.assertRaises(ValueError):
            spin_entry_resistance_verdict(4.0, 5.0, 0.0, 20.0)
        with self.assertRaises(ValueError):
            spin_entry_resistance_verdict(4.0, 5.0, 20.0, -20.0)


class SpinRecoveryTests(unittest.TestCase):
    def test_nominal_recovery_passes(self):
        v = spin_recovery_verdict(120.0, 300.0, 1.5, 2.0)
        self.assertTrue(v["altitude_loss_ok"])
        self.assertTrue(v["turns_ok"])
        self.assertTrue(v["ok"])

    def test_excessive_altitude_loss_fails(self):
        v = spin_recovery_verdict(400.0, 300.0, 1.5, 2.0)
        self.assertFalse(v["altitude_loss_ok"])
        self.assertFalse(v["ok"])

    def test_excessive_turns_fail(self):
        v = spin_recovery_verdict(120.0, 300.0, 2.5, 2.0)
        self.assertFalse(v["turns_ok"])
        self.assertFalse(v["ok"])

    def test_boundary_values_pass(self):
        v = spin_recovery_verdict(300.0, 300.0, 2.0, 2.0)
        self.assertTrue(v["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            spin_recovery_verdict(-10.0, 300.0, 1.5, 2.0)
        with self.assertRaises(ValueError):
            spin_recovery_verdict(120.0, 0.0, 1.5, 2.0)
        with self.assertRaises(ValueError):
            spin_recovery_verdict(120.0, 300.0, -1.0, 2.0)
        with self.assertRaises(ValueError):
            spin_recovery_verdict(120.0, 300.0, 1.5, 0.0)


class TestMatrixTests(unittest.TestCase):
    def test_matrix_covers_the_envelope(self):
        points = build_test_matrix(
            ["clean", "takeoff"], ["fwd", "aft"],
            12.0, 15.5, 21.0, 1.5,
        )
        regions = {p["region"] for p in points}
        self.assertEqual(
            regions, {"warning", "stall", "post-stall", "deep-stall"}
        )
        # 2 configs x 2 c.g. x 6 AoA values = 24 points.
        self.assertEqual(len(points), 24)
        max_aoa = max(p["aoa_deg"] for p in points)
        self.assertAlmostEqual(max_aoa, 21.0, places=6)
        deep = [p for p in points if p["region"] == "deep-stall"]
        self.assertEqual(len(deep), 4)
        for p in deep:
            self.assertAlmostEqual(p["aoa_deg"], 21.0, places=6)

    def test_every_combination_present(self):
        points = build_test_matrix(
            ["clean", "takeoff"], ["fwd", "aft"],
            12.0, 15.5, 21.0, 1.5,
        )
        combos = {(p["config"], p["cg"]) for p in points}
        self.assertEqual(
            combos, {("clean", "fwd"), ("clean", "aft"),
                     ("takeoff", "fwd"), ("takeoff", "aft")}
        )

    def test_step_reaching_max_aoa_exactly(self):
        # stall 15.5 + step 1.5 lands exactly on max 18.5.
        points = build_test_matrix(
            ["clean"], ["fwd"], 12.0, 15.5, 18.5, 1.5,
        )
        aoas = [p["aoa_deg"] for p in points]
        self.assertEqual(len(aoas), 4)
        self.assertAlmostEqual(aoas[-1], 18.5, places=6)
        self.assertEqual(points[-1]["region"], "deep-stall")

    def test_post_stall_progression_is_stepped(self):
        points = build_test_matrix(
            ["clean"], ["fwd"], 12.0, 15.5, 21.0, 1.5,
        )
        post = [p["aoa_deg"] for p in points if p["region"] == "post-stall"]
        # 17.0, 18.5, 20.0 are the stepped post-stall points.
        self.assertEqual(len(post), 3)
        for a, b in zip(post, post[1:]):
            self.assertAlmostEqual(b - a, 1.5, places=6)

    def test_point_ids_are_unique(self):
        points = build_test_matrix(
            ["clean", "takeoff"], ["fwd", "aft"],
            12.0, 15.5, 21.0, 1.5,
        )
        ids = [p["point_id"] for p in points]
        self.assertEqual(len(ids), len(set(ids)))

    def test_warning_and_stall_points_present(self):
        points = build_test_matrix(
            ["clean"], ["fwd"], 12.0, 15.5, 21.0, 1.5,
        )
        self.assertAlmostEqual(points[0]["aoa_deg"], 12.0, places=6)
        self.assertEqual(points[0]["region"], "warning")
        self.assertAlmostEqual(points[1]["aoa_deg"], 15.5, places=6)
        self.assertEqual(points[1]["region"], "stall")

    def test_empty_configs_raise(self):
        with self.assertRaises(ValueError):
            build_test_matrix([], ["fwd"], 12.0, 15.5, 21.0, 1.5)

    def test_empty_cg_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix(["clean"], [], 12.0, 15.5, 21.0, 1.5)

    def test_non_increasing_angles_raise(self):
        with self.assertRaises(ValueError):
            build_test_matrix(["clean"], ["fwd"], 15.5, 12.0, 21.0, 1.5)
        with self.assertRaises(ValueError):
            build_test_matrix(["clean"], ["fwd"], 12.0, 21.0, 15.5, 1.5)

    def test_non_positive_step_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix(["clean"], ["fwd"], 12.0, 15.5, 21.0, 0.0)


if __name__ == "__main__":
    unittest.main()
