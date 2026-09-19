"""Contract tests for the particle counter and microscope control logic."""

import unittest

from q7050_instrument_control_logic import (
    CALIBRATION_STATES,
    assess_instrument_control,
    calibration_status,
    concentration_bias_fraction,
    flow_deviation_fraction,
    grade_background,
    grade_counting_efficiency,
    grade_flow,
    grade_microscope_sizing,
    require_int,
    require_real,
    zero_count_rate_per_m3,
)


def counter(**overrides):
    spec = {
        "instrument_id": "opc-01",
        "kind": "particle-counter",
        "calibration": {"days_since": 120, "interval_days": 365},
        "flow": {"measured_lpm": 28.3, "nominal_lpm": 28.3},
        "efficiency": {"value": 0.52},
        "background": {"counts": 0, "volume_litres": 28.3, "allowed_per_m3": 350.0},
    }
    spec.update(overrides)
    return spec


def microscope(**overrides):
    spec = {
        "instrument_id": "mic-02",
        "kind": "sizing-microscope",
        "calibration": {"days_since": 30, "interval_days": 365},
        "sizing": {"measured_um": 100.4, "certified_um": 100.0, "tolerance_um": 1.0},
    }
    spec.update(overrides)
    return spec


class GuardTests(unittest.TestCase):
    def test_real_accepts_an_int(self):
        self.assertAlmostEqual(require_real(3, "x"), 3.0, places=12)

    def test_real_rejects_a_boolean(self):
        with self.assertRaises(ValueError):
            require_real(True, "x")

    def test_real_rejects_a_string(self):
        with self.assertRaises(ValueError):
            require_real("3", "x")

    def test_real_rejects_a_non_finite(self):
        with self.assertRaises(ValueError):
            require_real(float("nan"), "x")

    def test_int_rejects_a_float(self):
        with self.assertRaises(ValueError):
            require_int(3.0, "n")

    def test_int_rejects_a_boolean(self):
        with self.assertRaises(ValueError):
            require_int(False, "n")


class CalibrationTests(unittest.TestCase):
    def test_mid_interval_is_current(self):
        result = calibration_status(120, 365)
        self.assertEqual(result["state"], "current")
        self.assertTrue(result["conforming"])

    def test_state_is_from_the_declared_set(self):
        self.assertIn(calibration_status(120, 365)["state"], CALIBRATION_STATES)

    def test_inside_the_warning_band_is_due_soon(self):
        result = calibration_status(350, 365, 30)
        self.assertEqual(result["state"], "due-soon")
        self.assertTrue(result["conforming"])

    def test_exactly_at_the_interval_is_still_conforming(self):
        result = calibration_status(365, 365)
        self.assertEqual(result["days_remaining"], 0)
        self.assertTrue(result["conforming"])

    def test_past_the_interval_is_expired(self):
        result = calibration_status(400, 365)
        self.assertEqual(result["state"], "expired")
        self.assertFalse(result["conforming"])

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(-1, 365)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(10, 0)

    def test_warning_longer_than_the_interval_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(10, 30, 60)


class FlowTests(unittest.TestCase):
    def test_nominal_flow_has_zero_deviation(self):
        self.assertAlmostEqual(flow_deviation_fraction(28.3, 28.3), 0.0, places=12)

    def test_deviation_is_signed(self):
        self.assertAlmostEqual(flow_deviation_fraction(27.0, 30.0), -0.1, places=12)

    def test_low_flow_over_reports_concentration(self):
        self.assertAlmostEqual(concentration_bias_fraction(25.0, 50.0), 1.0, places=12)

    def test_high_flow_under_reports_concentration(self):
        self.assertAlmostEqual(
            concentration_bias_fraction(50.0, 25.0), -0.5, places=12
        )

    def test_flow_inside_tolerance_conforms(self):
        self.assertTrue(grade_flow(29.0, 28.3, 0.05)["conforming"])

    def test_flow_exactly_at_tolerance_conforms(self):
        result = grade_flow(31.5, 30.0, 0.05)
        self.assertAlmostEqual(result["deviation_fraction"], 0.05, places=9)
        self.assertTrue(result["conforming"])

    def test_flow_outside_tolerance_fails(self):
        self.assertFalse(grade_flow(34.0, 30.0, 0.05)["conforming"])

    def test_zero_flow_rejected(self):
        with self.assertRaises(ValueError):
            grade_flow(0.0, 30.0)

    def test_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_flow(30.0, 30.0, 1.0)


class EfficiencyTests(unittest.TestCase):
    def test_on_target_conforms(self):
        self.assertTrue(grade_counting_efficiency(0.5)["conforming"])

    def test_at_the_window_edge_conforms(self):
        result = grade_counting_efficiency(0.7, 0.5, 0.2)
        self.assertAlmostEqual(result["deviation"], 0.2, places=9)
        self.assertTrue(result["conforming"])

    def test_below_the_window_fails(self):
        self.assertFalse(grade_counting_efficiency(0.2, 0.5, 0.2)["conforming"])

    def test_efficiency_above_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_counting_efficiency(1.4)

    def test_negative_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            grade_counting_efficiency(-0.1)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            grade_counting_efficiency(0.5, 0.5, 0.0)


class BackgroundTests(unittest.TestCase):
    def test_rate_scales_to_a_cubic_metre(self):
        self.assertAlmostEqual(zero_count_rate_per_m3(2, 100.0), 20.0, places=9)

    def test_zero_counts_give_a_zero_rate(self):
        self.assertAlmostEqual(zero_count_rate_per_m3(0, 28.3), 0.0, places=12)

    def test_rate_at_the_allowance_conforms(self):
        result = grade_background(1, 100.0, 10.0)
        self.assertAlmostEqual(result["rate_per_m3"], 10.0, places=9)
        self.assertTrue(result["conforming"])

    def test_rate_above_the_allowance_fails(self):
        self.assertFalse(grade_background(10, 100.0, 10.0)["conforming"])

    def test_negative_counts_rejected(self):
        with self.assertRaises(ValueError):
            grade_background(-1, 100.0, 10.0)

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            grade_background(1, 0.0, 10.0)


class MicroscopeTests(unittest.TestCase):
    def test_small_bias_conforms(self):
        self.assertTrue(grade_microscope_sizing(100.4, 100.0, 1.0)["conforming"])

    def test_bias_exactly_at_tolerance_conforms(self):
        result = grade_microscope_sizing(101.0, 100.0, 1.0)
        self.assertAlmostEqual(result["bias_um"], 1.0, places=9)
        self.assertTrue(result["conforming"])

    def test_bias_fraction_is_relative_to_the_certified_value(self):
        result = grade_microscope_sizing(102.0, 100.0, 5.0)
        self.assertAlmostEqual(result["bias_fraction"], 0.02, places=12)

    def test_large_negative_bias_fails(self):
        self.assertFalse(grade_microscope_sizing(96.0, 100.0, 1.0)["conforming"])

    def test_zero_certified_value_rejected(self):
        with self.assertRaises(ValueError):
            grade_microscope_sizing(100.0, 0.0, 1.0)


class AssessmentTests(unittest.TestCase):
    def test_controlled_counter_is_fit_for_use(self):
        result = assess_instrument_control(counter())
        self.assertTrue(result["fit_for_use"])
        self.assertEqual(result["failed_checks"], [])
        self.assertEqual(result["findings"], [])

    def test_expired_calibration_withholds_fitness(self):
        result = assess_instrument_control(
            counter(calibration={"days_since": 400, "interval_days": 365})
        )
        self.assertFalse(result["fit_for_use"])
        self.assertIn("calibration", result["failed_checks"])

    def test_due_soon_warns_without_withholding_fitness(self):
        result = assess_instrument_control(
            counter(calibration={"days_since": 350, "interval_days": 365})
        )
        self.assertTrue(result["fit_for_use"])
        self.assertTrue(any("falls due" in f for f in result["findings"]))

    def test_flow_failure_reports_the_induced_bias(self):
        result = assess_instrument_control(
            counter(flow={"measured_lpm": 20.0, "nominal_lpm": 28.3})
        )
        self.assertFalse(result["fit_for_use"])
        self.assertTrue(any("biasing" in f for f in result["findings"]))

    def test_one_failed_check_is_not_averaged_away(self):
        result = assess_instrument_control(counter(efficiency={"value": 0.05}))
        self.assertFalse(result["fit_for_use"])
        self.assertEqual(result["failed_checks"], ["efficiency"])

    def test_dirty_background_withholds_fitness(self):
        result = assess_instrument_control(counter(background={
            "counts": 40, "volume_litres": 28.3, "allowed_per_m3": 350.0,
        }))
        self.assertFalse(result["fit_for_use"])
        self.assertIn("background", result["failed_checks"])

    def test_microscope_path_is_graded_on_sizing(self):
        result = assess_instrument_control(microscope())
        self.assertTrue(result["fit_for_use"])
        self.assertIn("sizing", result["checks"])

    def test_microscope_bias_withholds_fitness(self):
        result = assess_instrument_control(microscope(sizing={
            "measured_um": 110.0, "certified_um": 100.0, "tolerance_um": 1.0,
        }))
        self.assertFalse(result["fit_for_use"])
        self.assertIn("sizing", result["failed_checks"])

    def test_counter_without_a_flow_check_rejected(self):
        spec = counter()
        del spec["flow"]
        with self.assertRaises(ValueError):
            assess_instrument_control(spec)

    def test_microscope_without_a_sizing_check_rejected(self):
        spec = microscope()
        del spec["sizing"]
        with self.assertRaises(ValueError):
            assess_instrument_control(spec)

    def test_unknown_instrument_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument_control(counter(kind="tape-lift-reader"))

    def test_missing_calibration_rejected(self):
        spec = counter()
        del spec["calibration"]
        with self.assertRaises(ValueError):
            assess_instrument_control(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument_control(["kind"])

    def test_malformed_background_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument_control(counter(background={"counts": 0}))


if __name__ == "__main__":
    unittest.main()
