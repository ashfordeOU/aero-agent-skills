"""test_control_force_flight_test.py

Offline deterministic contract test for the control force flight test
reduction leaf (flight-test-operations/stability/control-force-flight-
test). Runs with: python3 scripts/test_control_force_flight_test.py

Covers the worked-example anchors of the spec (force transducer
calibration, stick force gradient with stability verdict, stick force
per g, breakout force, centering check), the regression identities
(calibration reproduces applied loads to 1e-9, r2 = 1.0 on perfectly
linear data), boundary cases and ValueError rejection of non-physical
inputs.
"""

import unittest

from control_force_flight_test_logic import (
    calibrate_force_transducer,
    centering_check,
    breakout_force,
    control_force_report,
    force_per_g,
    stick_force_gradient,
)

# Worked example, reference transport pitch-force flight test.
CAL_LOADS = [20.0, 60.0]          # lbf applied
CAL_COUNTS = [1230.0, 3250.0]     # recorded counts
PREDICT_COUNT = 2100.0

SWEEP_SPEEDS = [120.0, 130.0, 140.0, 150.0]   # KCAS
SWEEP_FORCES = [-3.8, -1.6, 0.5, 2.9]         # lbf, pull positive

PULL_LOAD_FACTORS = [1.0, 1.5, 2.0, 2.5]      # g
PULL_FORCES = [1.2, 7.4, 14.3, 20.8]          # lbf

PUSH_FORCE = -4.2                              # lbf
PULL_FORCE = 6.4                               # lbf

RESIDUAL_DEG = 0.42
LIMIT_DEG = 0.50


class TestCalibration(unittest.TestCase):
    def test_calibration_two_point_slope(self):
        cal = calibrate_force_transducer(CAL_LOADS, CAL_COUNTS)
        self.assertAlmostEqual(cal["slope_lbf_per_count"], 0.019802, places=6)

    def test_calibration_two_point_intercept(self):
        cal = calibrate_force_transducer(CAL_LOADS, CAL_COUNTS)
        self.assertAlmostEqual(cal["intercept_lbf"], -4.35644, places=5)

    def test_calibration_reproduces_applied_loads(self):
        cal = calibrate_force_transducer(CAL_LOADS, CAL_COUNTS)
        for applied, predicted in zip(CAL_LOADS, cal["predicted_lbf"]):
            self.assertAlmostEqual(predicted, applied, places=9)

    def test_calibration_third_collinear_point_zero_residual(self):
        x = [1000.0, 2000.0, 3000.0]
        y = [15.0, 35.0, 55.0]  # y = 0.02 * x - 5 exactly
        cal = calibrate_force_transducer(y, x)
        self.assertAlmostEqual(cal["slope_lbf_per_count"], 0.02, places=9)
        for applied, predicted in zip(y, cal["predicted_lbf"]):
            self.assertAlmostEqual(predicted, applied, places=9)

    def test_calibration_predicted_force_at_2100_counts(self):
        cal = calibrate_force_transducer(CAL_LOADS, CAL_COUNTS)
        predicted = cal["slope_lbf_per_count"] * PREDICT_COUNT + cal[
            "intercept_lbf"
        ]
        self.assertAlmostEqual(predicted, 37.2277, places=4)

    def test_calibration_fewer_than_two_points_valueerror(self):
        with self.assertRaises(ValueError):
            calibrate_force_transducer([20.0], [1230.0])
        with self.assertRaises(ValueError):
            calibrate_force_transducer([20.0], [1230.0, 3250.0])

    def test_calibration_length_mismatch_valueerror(self):
        with self.assertRaises(ValueError):
            calibrate_force_transducer([20.0, 60.0], [1230.0])

    def test_calibration_negative_counts_valueerror(self):
        with self.assertRaises(ValueError):
            calibrate_force_transducer([20.0, 60.0], [1230.0, -5.0])


class TestStickForceGradient(unittest.TestCase):
    def test_gradient_worked_slope(self):
        grad = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        self.assertAlmostEqual(grad["slope_lbf_per_kt"], 0.222, places=4)

    def test_gradient_worked_intercept(self):
        grad = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        self.assertAlmostEqual(grad["intercept_lbf"], -30.47, places=4)

    def test_gradient_worked_r2(self):
        grad = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        self.assertAlmostEqual(grad["r2"], 0.99927, places=4)

    def test_gradient_verdict_stable_gradient(self):
        grad = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        self.assertEqual(grad["verdict"], "stable-gradient")

    def test_gradient_reversed_sweep_unstable_gradient(self):
        reversed_forces = [2.9, 0.5, -1.6, -3.8]  # pull decays with speed
        grad = stick_force_gradient(SWEEP_SPEEDS, reversed_forces)
        self.assertLess(grad["slope_lbf_per_kt"], 0.0)
        self.assertEqual(grad["verdict"], "unstable-gradient")

    def test_gradient_flat_slope_verdict_unstable_gradient(self):
        grad = stick_force_gradient(SWEEP_SPEEDS, [0.5, 0.5, 0.5, 0.5])
        self.assertEqual(grad["slope_lbf_per_kt"], 0.0)
        self.assertEqual(grad["verdict"], "unstable-gradient")

    def test_gradient_perfect_linear_r2_one(self):
        speeds = [100.0, 110.0, 120.0, 130.0, 140.0]
        forces = [2.0 * v + 1.0 for v in speeds]
        grad = stick_force_gradient(speeds, forces)
        self.assertAlmostEqual(grad["slope_lbf_per_kt"], 2.0, places=9)
        self.assertAlmostEqual(grad["r2"], 1.0, places=12)
        self.assertEqual(grad["verdict"], "stable-gradient")

    def test_gradient_fewer_than_three_points_valueerror(self):
        with self.assertRaises(ValueError):
            stick_force_gradient([120.0, 130.0], [-3.8, -1.6])

    def test_gradient_length_mismatch_valueerror(self):
        with self.assertRaises(ValueError):
            stick_force_gradient([120.0, 130.0, 140.0], [-3.8, -1.6])

    def test_gradient_nonpositive_speed_valueerror(self):
        with self.assertRaises(ValueError):
            stick_force_gradient([120.0, 130.0, 0.0], [-3.8, -1.6, 0.5])
        with self.assertRaises(ValueError):
            stick_force_gradient([120.0, 130.0, -10.0], [-3.8, -1.6, 0.5])


class TestForcePerG(unittest.TestCase):
    def test_force_per_g_worked_slope(self):
        per_g = force_per_g(PULL_LOAD_FACTORS, PULL_FORCES)
        self.assertAlmostEqual(per_g["slope_lbf_per_g"], 13.14, places=4)

    def test_force_per_g_worked_intercept(self):
        per_g = force_per_g(PULL_LOAD_FACTORS, PULL_FORCES)
        self.assertAlmostEqual(per_g["intercept_lbf"], -12.07, places=4)

    def test_force_per_g_worked_r2(self):
        per_g = force_per_g(PULL_LOAD_FACTORS, PULL_FORCES)
        self.assertAlmostEqual(per_g["r2"], 0.99962, places=4)

    def test_force_per_g_linear_identity_r2_one(self):
        load_factors = [1.0, 1.5, 2.0, 2.5, 3.0]
        forces = [13.14 * n - 12.07 for n in load_factors]
        per_g = force_per_g(load_factors, forces)
        self.assertAlmostEqual(per_g["r2"], 1.0, places=12)
        self.assertAlmostEqual(per_g["slope_lbf_per_g"], 13.14, places=9)

    def test_force_per_g_fewer_than_three_points_valueerror(self):
        with self.assertRaises(ValueError):
            force_per_g([1.0, 1.5], [1.2, 7.4])

    def test_force_per_g_length_mismatch_valueerror(self):
        with self.assertRaises(ValueError):
            force_per_g([1.0, 1.5, 2.0], [1.2, 7.4, 14.3, 20.8])


class TestBreakout(unittest.TestCase):
    def test_breakout_worked_values(self):
        b = breakout_force(PUSH_FORCE, PULL_FORCE)
        self.assertAlmostEqual(b["hysteresis_width_lbf"], 10.6, delta=1e-9)
        self.assertAlmostEqual(b["breakout_lbf"], 5.3, delta=1e-9)

    def test_breakout_symmetric_half_width(self):
        b = breakout_force(-5.0, 5.0)
        self.assertAlmostEqual(b["hysteresis_width_lbf"], 10.0, delta=1e-9)
        self.assertAlmostEqual(b["breakout_lbf"], 5.0, delta=1e-9)

    def test_breakout_pull_equals_push_valueerror(self):
        with self.assertRaises(ValueError):
            breakout_force(5.0, 5.0)

    def test_breakout_pull_less_than_push_valueerror(self):
        with self.assertRaises(ValueError):
            breakout_force(6.4, -4.2)


class TestCentering(unittest.TestCase):
    def test_centering_worked_values(self):
        c = centering_check(RESIDUAL_DEG, LIMIT_DEG)
        self.assertAlmostEqual(c["margin_deg"], 0.08, delta=1e-9)
        self.assertEqual(c["residual_deg"], RESIDUAL_DEG)
        self.assertEqual(c["limit_deg"], LIMIT_DEG)
        self.assertEqual(c["verdict"], "centered")

    def test_centering_exceeds_limit(self):
        c = centering_check(0.60, 0.50)
        self.assertAlmostEqual(c["margin_deg"], -0.1, delta=1e-9)
        self.assertEqual(c["verdict"], "exceeds-limit")

    def test_centering_negative_residual_valueerror(self):
        with self.assertRaises(ValueError):
            centering_check(-0.1, 0.5)

    def test_centering_nonpositive_limit_valueerror(self):
        with self.assertRaises(ValueError):
            centering_check(0.42, 0.0)
        with self.assertRaises(ValueError):
            centering_check(0.42, -0.5)


class TestReportAndDeterminism(unittest.TestCase):
    def test_report_combines_all_outputs(self):
        report = control_force_report(
            CAL_LOADS,
            CAL_COUNTS,
            PREDICT_COUNT,
            SWEEP_SPEEDS,
            SWEEP_FORCES,
            PULL_LOAD_FACTORS,
            PULL_FORCES,
            PUSH_FORCE,
            PULL_FORCE,
            RESIDUAL_DEG,
            LIMIT_DEG,
        )
        self.assertEqual(
            sorted(report.keys()),
            [
                "breakout",
                "calibration",
                "centering",
                "force_per_g",
                "predicted_force_lbf",
                "stick_force_gradient",
            ],
        )
        self.assertEqual(
            sorted(report["calibration"].keys()),
            ["intercept_lbf", "predicted_lbf", "slope_lbf_per_count"],
        )
        self.assertEqual(
            sorted(report["stick_force_gradient"].keys()),
            ["intercept_lbf", "r2", "slope_lbf_per_kt", "verdict"],
        )
        self.assertEqual(
            sorted(report["force_per_g"].keys()),
            ["intercept_lbf", "r2", "slope_lbf_per_g"],
        )
        self.assertEqual(
            sorted(report["breakout"].keys()),
            ["breakout_lbf", "hysteresis_width_lbf"],
        )
        self.assertEqual(
            sorted(report["centering"].keys()),
            ["limit_deg", "margin_deg", "residual_deg", "verdict"],
        )
        # Report agrees with the individual reductions.
        grad = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        per_g = force_per_g(PULL_LOAD_FACTORS, PULL_FORCES)
        self.assertAlmostEqual(
            report["stick_force_gradient"]["slope_lbf_per_kt"],
            grad["slope_lbf_per_kt"],
            places=12,
        )
        self.assertAlmostEqual(
            report["force_per_g"]["slope_lbf_per_g"],
            per_g["slope_lbf_per_g"],
            places=12,
        )
        self.assertAlmostEqual(report["predicted_force_lbf"], 37.2277, places=4)
        self.assertEqual(report["stick_force_gradient"]["verdict"], "stable-gradient")
        self.assertEqual(report["centering"]["verdict"], "centered")

    def test_report_negative_predict_count_valueerror(self):
        with self.assertRaises(ValueError):
            control_force_report(
                CAL_LOADS,
                CAL_COUNTS,
                -1.0,
                SWEEP_SPEEDS,
                SWEEP_FORCES,
                PULL_LOAD_FACTORS,
                PULL_FORCES,
                PUSH_FORCE,
                PULL_FORCE,
                RESIDUAL_DEG,
                LIMIT_DEG,
            )

    def test_determinism_identical_floats_run_to_run(self):
        first = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        second = stick_force_gradient(SWEEP_SPEEDS, SWEEP_FORCES)
        self.assertEqual(first["slope_lbf_per_kt"], second["slope_lbf_per_kt"])
        self.assertEqual(first["intercept_lbf"], second["intercept_lbf"])
        self.assertEqual(first["r2"], second["r2"])
        cal_first = calibrate_force_transducer(CAL_LOADS, CAL_COUNTS)
        cal_second = calibrate_force_transducer(CAL_LOADS, CAL_COUNTS)
        self.assertEqual(
            cal_first["predicted_lbf"], cal_second["predicted_lbf"]
        )


if __name__ == "__main__":
    unittest.main()
