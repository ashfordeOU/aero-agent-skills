"""Contract tests for the clause 5.5.5.2a heat pipe performance logic."""

import unittest

from e3102_heat_pipe_performance_verification_logic import (
    assess_heat_pipe_performance,
    bend_knockdown_factor,
    capability_at_temperature,
    capability_margin,
    interpolate_curve,
    power_from_power_length,
    predicted_capability_w,
    tilt_penalty_w,
    validate_curve,
)

# Ammonia-grooved shape: the power-length rating (W*m) rises with temperature
# across the operating range and falls away at the cold end.
CURVE = [
    (-30.0, 90.0),
    (0.0, 180.0),
    (20.0, 240.0),
    (40.0, 280.0),
    (60.0, 250.0),
]

BASE = {
    "capability_curve": CURVE,
    "effective_length_m": 1.2,
    "tilt_sensitivity_w_per_mm": 12.0,
    "bend_count": 0,
    "minimum_bend_radius_mm": 40.0,
    "knockdown_per_bend": 0.05,
}


def spec(**overrides):
    out = dict(BASE)
    out.update(overrides)
    return out


class CurveTests(unittest.TestCase):
    def test_validate_returns_float_points(self):
        self.assertEqual(validate_curve([(-10, 50), (10, 70)]), [(-10.0, 50.0), (10.0, 70.0)])

    def test_single_point_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.0, 100.0)])

    def test_non_monotone_temperatures_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(20.0, 100.0), (0.0, 80.0)])

    def test_repeated_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(20.0, 100.0), (20.0, 80.0)])

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.0, -5.0), (20.0, 80.0)])

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.0, 100.0), (20.0,)])

    def test_interpolation_hits_a_tabulated_point(self):
        self.assertAlmostEqual(interpolate_curve(CURVE, 20.0), 240.0, places=9)

    def test_interpolation_is_linear_between_points(self):
        self.assertAlmostEqual(interpolate_curve(CURVE, 10.0), 210.0, places=9)

    def test_cold_end_is_reachable(self):
        self.assertAlmostEqual(capability_at_temperature(CURVE, -30.0), 90.0, places=9)

    def test_below_the_curve_refused(self):
        with self.assertRaises(ValueError):
            capability_at_temperature(CURVE, -50.0)

    def test_above_the_curve_refused(self):
        with self.assertRaises(ValueError):
            capability_at_temperature(CURVE, 80.0)

    def test_capability_falls_back_at_the_hot_end(self):
        self.assertLess(
            capability_at_temperature(CURVE, 60.0), capability_at_temperature(CURVE, 40.0)
        )


class PowerLengthTests(unittest.TestCase):
    def test_rating_divides_by_the_effective_length(self):
        self.assertAlmostEqual(power_from_power_length(240.0, 1.2), 200.0, places=9)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            power_from_power_length(240.0, 0.0)

    def test_negative_rating_rejected(self):
        with self.assertRaises(ValueError):
            power_from_power_length(-1.0, 1.2)


class TiltTests(unittest.TestCase):
    def test_adverse_tilt_costs_the_sensitivity_times_the_elevation(self):
        self.assertAlmostEqual(tilt_penalty_w(12.0, 3.0), 36.0, places=9)

    def test_level_pipe_costs_nothing(self):
        self.assertAlmostEqual(tilt_penalty_w(12.0, 0.0), 0.0, places=9)

    def test_favourable_tilt_is_not_credited(self):
        self.assertAlmostEqual(tilt_penalty_w(12.0, -5.0), 0.0, places=9)

    def test_negative_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            tilt_penalty_w(-1.0, 3.0)

    def test_non_numeric_elevation_rejected(self):
        with self.assertRaises(ValueError):
            tilt_penalty_w(12.0, "3")


class BendTests(unittest.TestCase):
    def test_no_bends_is_unity(self):
        self.assertAlmostEqual(bend_knockdown_factor(0, 60.0, 40.0, 0.05), 1.0, places=12)

    def test_bend_at_the_minimum_radius_costs_the_full_knockdown(self):
        self.assertAlmostEqual(bend_knockdown_factor(1, 40.0, 40.0, 0.05), 0.95, places=12)

    def test_generous_radius_costs_proportionally_less(self):
        self.assertAlmostEqual(bend_knockdown_factor(1, 80.0, 40.0, 0.05), 0.975, places=12)

    def test_two_bends_compound(self):
        one = bend_knockdown_factor(1, 40.0, 40.0, 0.05)
        self.assertAlmostEqual(
            bend_knockdown_factor(2, 40.0, 40.0, 0.05), one * one, places=12
        )

    def test_radius_tighter_than_the_minimum_refused(self):
        with self.assertRaises(ValueError):
            bend_knockdown_factor(1, 30.0, 40.0, 0.05)

    def test_negative_bend_count_rejected(self):
        with self.assertRaises(ValueError):
            bend_knockdown_factor(-1, 60.0, 40.0, 0.05)

    def test_float_bend_count_rejected(self):
        with self.assertRaises(ValueError):
            bend_knockdown_factor(1.5, 60.0, 40.0, 0.05)

    def test_knockdown_of_one_rejected(self):
        with self.assertRaises(ValueError):
            bend_knockdown_factor(1, 60.0, 40.0, 1.0)


class PredictionTests(unittest.TestCase):
    def test_level_straight_pipe_is_the_bare_rating(self):
        out = predicted_capability_w(spec(), 20.0, 0.0)
        self.assertAlmostEqual(out["capability_w"], 200.0, places=9)
        self.assertFalse(out["capillary_limit_exhausted"])

    def test_adverse_tilt_reduces_the_capability(self):
        out = predicted_capability_w(spec(), 20.0, 5.0)
        self.assertAlmostEqual(out["capability_w"], 140.0, places=9)

    def test_bends_reduce_the_capability_further(self):
        out = predicted_capability_w(spec(bend_count=2, bend_radius_mm=40.0), 20.0, 0.0)
        self.assertAlmostEqual(out["capability_w"], 200.0 * 0.95 * 0.95, places=9)

    def test_excess_tilt_exhausts_the_capillary_limit(self):
        out = predicted_capability_w(spec(), 20.0, 40.0)
        self.assertTrue(out["capillary_limit_exhausted"])
        self.assertAlmostEqual(out["capability_w"], 0.0, places=12)

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["effective_length_m"]
        with self.assertRaises(ValueError):
            predicted_capability_w(broken, 20.0, 0.0)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            predicted_capability_w(["capability_curve"], 20.0, 0.0)


class MarginTests(unittest.TestCase):
    def test_exact_equality_is_compliant(self):
        out = capability_margin(150.0, 150.0)
        self.assertAlmostEqual(out["ratio"], 1.0, places=9)
        self.assertTrue(out["compliant"])

    def test_shortfall_is_not_compliant(self):
        self.assertFalse(capability_margin(120.0, 150.0)["compliant"])

    def test_surplus_is_compliant(self):
        self.assertTrue(capability_margin(300.0, 150.0)["compliant"])

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            capability_margin(150.0, 0.0)

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            capability_margin(-1.0, 150.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        out = spec(
            operating_points=[
                {"name": "hot-case", "temperature_c": 40.0,
                 "adverse_elevation_mm": 2.0, "required_w": 150.0},
                {"name": "cold-case", "temperature_c": -20.0,
                 "adverse_elevation_mm": 2.0, "required_w": 60.0},
            ]
        )
        out.update(overrides)
        return out

    def test_clean_case_is_compliant(self):
        out = assess_heat_pipe_performance(self._spec())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_worst_point_is_the_lowest_ratio(self):
        out = assess_heat_pipe_performance(self._spec())
        ratios = [r["ratio"] for r in out["records"]]
        self.assertAlmostEqual(out["worst_point"]["ratio"], min(ratios), places=12)

    def test_the_cold_end_can_govern(self):
        out = assess_heat_pipe_performance(self._spec())
        self.assertEqual(out["worst_point"]["name"], "cold-case")

    def test_tilt_shortfall_is_reported(self):
        out = assess_heat_pipe_performance(
            self._spec(
                operating_points=[
                    {"name": "tilted", "temperature_c": 20.0,
                     "adverse_elevation_mm": 12.0, "required_w": 150.0}
                ]
            )
        )
        self.assertFalse(out["compliant"])
        self.assertTrue(any("required transport" in f for f in out["findings"]))

    def test_exhausted_capillary_limit_is_reported_separately(self):
        out = assess_heat_pipe_performance(
            self._spec(
                operating_points=[
                    {"name": "vertical", "temperature_c": 20.0,
                     "adverse_elevation_mm": 40.0, "required_w": 50.0}
                ]
            )
        )
        self.assertTrue(any("capillary limit" in f for f in out["findings"]))

    def test_empty_operating_points_rejected(self):
        with self.assertRaises(ValueError):
            assess_heat_pipe_performance(self._spec(operating_points=[]))

    def test_operating_point_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_heat_pipe_performance(
                self._spec(operating_points=[{"temperature_c": 20.0, "required_w": 100.0}])
            )

    def test_bend_tighter_than_the_minimum_refuses_the_whole_assessment(self):
        with self.assertRaises(ValueError):
            assess_heat_pipe_performance(self._spec(bend_count=1, bend_radius_mm=10.0))


if __name__ == "__main__":
    unittest.main()
