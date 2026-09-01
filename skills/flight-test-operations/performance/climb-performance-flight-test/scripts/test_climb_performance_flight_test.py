#!/usr/bin/env python3
"""Gate 3 contract test: climb performance flight test logic.

Exercises scripts/climb_performance_flight_test_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 - ISA
density ratio and density altitude, measured rate of climb from
pressure altitude, geometric rate conversion, weight and density
corrections, excess power model chain (CL, CD, drag, thrust lapse, rate
of climb, climb gradient), best rate of climb, service and absolute
ceiling, time to climb, and gradient margin checks; invalid inputs
raise ValueError.

Worked scenario (synthetic light jet): W 20000 lbf, S 320 ft^2,
cd0 0.022, AR 7.5 e 0.8 (k = 1/(pi*0.8*7.5)), T0 6500 lbf, thrust
lapse 0.7. Pinned values from the deterministic model: sea level best
rate 6289.174 ft/min at 516.792 ft/s; service ceiling (100 ft/min)
56354 ft; absolute ceiling 57189 ft; time to climb 0 to 30000 ft
6.692 min; one-engine-inoperative gradient at 10000 ft 2.699 percent,
margin +0.299 percent against the 2.4 percent takeoff climb
requirement. ISA anchors: sigma(0) = 1, sigma(10000) = 0.73848,
sigma(36089.24 ft) = 0.29708; density altitude at 10000 ft pressure
altitude on an ISA day (OAT -4.812 C) equals 10000 ft.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import climb_performance_flight_test_logic as cpf  # noqa: E402

W = 20000.0
S = 320.0
CD0 = 0.022
K = 1.0 / (math.pi * 0.8 * 7.5)
T0 = 6500.0


class IsaDensityRatioTest(unittest.TestCase):
    def test_sea_level_is_one(self):
        self.assertAlmostEqual(cpf.isa_density_ratio(0), 1.0, places=6)

    def test_ten_thousand_feet_anchor(self):
        # Standard ISA density ratio at 10000 ft: 0.73848
        self.assertAlmostEqual(cpf.isa_density_ratio(10000), 0.73848, places=4)

    def test_tropopause_anchor(self):
        # Standard ISA density ratio at the tropopause: 0.29708
        self.assertAlmostEqual(cpf.isa_density_ratio(36089.24), 0.29708, places=4)

    def test_above_tropopause_continues_falling(self):
        self.assertLess(cpf.isa_density_ratio(40000), cpf.isa_density_ratio(36089.24))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.isa_density_ratio(-1000)
        with self.assertRaises(ValueError):
            cpf.isa_density_ratio(70000)


class DensityAltitudeTest(unittest.TestCase):
    def test_isa_day_identity(self):
        # 10000 ft pressure altitude, ISA temperature there (-4.812 C):
        # density altitude equals pressure altitude
        isa_oat = cpf.isa_temperature_k(10000) - 273.15
        self.assertAlmostEqual(cpf.density_altitude_ft(10000, isa_oat), 10000.0, places=1)

    def test_warm_day_raises_density_altitude(self):
        # 15 C at 10000 ft (ISA +19.8 C) pushes the density altitude up
        self.assertAlmostEqual(cpf.density_altitude_ft(10000, 15.0), 12248.13, places=1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.density_altitude_ft(-5000, 15.0)
        with self.assertRaises(ValueError):
            cpf.density_altitude_ft(10000, -280.0)


class RateOfClimbFromPressureAltitudeTest(unittest.TestCase):
    def test_analytic_check(self):
        # 2000 ft gained in 60 s = 2000 ft/min
        self.assertAlmostEqual(cpf.rate_of_climb_from_pressure_altitude(5000, 7000, 60), 2000.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_from_pressure_altitude(5000, 7000, 0)
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_from_pressure_altitude(5000, 7000, -60)
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_from_pressure_altitude(7000, 7000, 60)
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_from_pressure_altitude(7000, 5000, 60)


class GeometricRocFromPressureRocTest(unittest.TestCase):
    def test_analytic_check(self):
        # 15 C at 10000 ft pressure altitude: T_amb/T_ISA = 288.15/268.338
        # = 1.07383; 2000 * 1.07383 = 2147.66 ft/min
        self.assertAlmostEqual(cpf.geometric_roc_from_pressure_roc(2000, 15, 10000), 2147.66, places=2)

    def test_isa_day_identity(self):
        isa_oat = cpf.isa_temperature_k(10000) - 273.15
        self.assertAlmostEqual(cpf.geometric_roc_from_pressure_roc(2000, isa_oat, 10000), 2000.0, places=2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.geometric_roc_from_pressure_roc(0, 15, 10000)
        with self.assertRaises(ValueError):
            cpf.geometric_roc_from_pressure_roc(2000, 15, 70000)


class CorrectionsTest(unittest.TestCase):
    def test_weight_correction_analytic(self):
        # 2000 * 20500/20000 = 2050 ft/min
        self.assertAlmostEqual(cpf.weight_corrected_roc(2000, 20500, 20000), 2050.0, places=3)

    def test_weight_correction_unchanged_at_reference(self):
        self.assertAlmostEqual(cpf.weight_corrected_roc(2000, 20000, 20000), 2000.0, places=6)

    def test_density_correction_analytic(self):
        # 2000 * 0.9^0.2 = 2000 * 0.979148 = 1958.30 ft/min
        self.assertAlmostEqual(cpf.density_corrected_roc(2000, 0.9), 1958.30, places=2)

    def test_density_correction_unchanged_at_standard_day(self):
        self.assertAlmostEqual(cpf.density_corrected_roc(2000, 1.0), 2000.0, places=6)

    def test_combined_correction(self):
        # 2050 * 0.9^0.2 = 2050 * 0.979148 = 2007.25 ft/min
        self.assertAlmostEqual(
            cpf.corrected_rate_of_climb(2000, 20500, 20000, 0.9), 2007.25, places=2
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.weight_corrected_roc(0, 20500, 20000)
        with self.assertRaises(ValueError):
            cpf.weight_corrected_roc(2000, 0, 20000)
        with self.assertRaises(ValueError):
            cpf.weight_corrected_roc(2000, 20500, 0)
        with self.assertRaises(ValueError):
            cpf.density_corrected_roc(2000, 0)
        with self.assertRaises(ValueError):
            cpf.density_corrected_roc(2000, 0.9, lapse_exp=1.5)
        with self.assertRaises(ValueError):
            cpf.corrected_rate_of_climb(2000, 0, 20000, 0.9)


class AerodynamicChainTest(unittest.TestCase):
    def test_lift_coefficient_analytic(self):
        # CL = 20000 / (0.5*0.0023769*1.0*400^2*320) = 0.32868
        self.assertAlmostEqual(cpf.lift_coefficient(W, 400, S, 1.0), 0.32868, places=4)

    def test_drag_coefficient_analytic(self):
        # CD = 0.022 + 0.0530516 * 0.32868^2 = 0.02773
        cl = cpf.lift_coefficient(W, 400, S, 1.0)
        self.assertAlmostEqual(cpf.drag_coefficient(CD0, K, cl), 0.02773, places=4)

    def test_drag_force_analytic(self):
        # D = 0.5*0.0023769*400^2*320*0.027731 = 1687.4 lbf
        self.assertAlmostEqual(cpf.drag_force(W, 400, S, 1.0, CD0, K), 1687.42, places=1)

    def test_thrust_lapse_analytic(self):
        self.assertAlmostEqual(cpf.thrust_available(T0, 1.0), 6500.0, places=3)
        # 6500 * 0.5^0.7 = 6500 * 0.615572 = 4001.22 lbf
        self.assertAlmostEqual(cpf.thrust_available(T0, 0.5), 4001.22, places=2)

    def test_excess_thrust_analytic(self):
        self.assertAlmostEqual(cpf.excess_thrust(6500, 1687.415), 4812.585, places=3)

    def test_rate_of_climb_analytic(self):
        # (6500-1687.415)*400/20000*60 = 5775.10 ft/min
        d = cpf.drag_force(W, 400, S, 1.0, CD0, K)
        self.assertAlmostEqual(cpf.rate_of_climb_fpm(T0, d, 400, W), 5775.10, places=2)

    def test_gradient_analytic(self):
        # 100*(6500-1687.415)/20000 = 24.06 percent
        d = cpf.drag_force(W, 400, S, 1.0, CD0, K)
        self.assertAlmostEqual(cpf.climb_gradient_pct(T0, d, W), 24.06, places=2)
        # gradient from ROC: (5775.10/60)/400*100 = 24.06 percent
        self.assertAlmostEqual(cpf.gradient_from_roc(5775.10, 400), 24.06, places=2)

    def test_gradient_margin(self):
        self.assertAlmostEqual(cpf.gradient_margin_pct(3.5, 2.4), 1.1, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.lift_coefficient(0, 400, S, 1.0)
        with self.assertRaises(ValueError):
            cpf.lift_coefficient(W, 0, S, 1.0)
        with self.assertRaises(ValueError):
            cpf.lift_coefficient(W, 400, 0, 1.0)
        with self.assertRaises(ValueError):
            cpf.lift_coefficient(W, 400, S, 0)
        with self.assertRaises(ValueError):
            cpf.drag_coefficient(-0.01, K, 0.5)
        with self.assertRaises(ValueError):
            cpf.drag_coefficient(CD0, -0.01, 0.5)
        with self.assertRaises(ValueError):
            cpf.thrust_available(0, 1.0)
        with self.assertRaises(ValueError):
            cpf.thrust_available(T0, 0)
        with self.assertRaises(ValueError):
            cpf.thrust_available(T0, 1.0, lapse_exp=0)
        with self.assertRaises(ValueError):
            cpf.excess_thrust(-100, 100)
        with self.assertRaises(ValueError):
            cpf.excess_thrust(100, -100)
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_fpm(500, 1687.415, 400, W)
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_fpm(6500, 1687.415, 0, W)
        with self.assertRaises(ValueError):
            cpf.rate_of_climb_fpm(6500, 1687.415, 400, 0)
        with self.assertRaises(ValueError):
            cpf.climb_gradient_pct(500, 1687.415, W)
        with self.assertRaises(ValueError):
            cpf.gradient_from_roc(0, 400)
        with self.assertRaises(ValueError):
            cpf.gradient_margin_pct(3.5, -1.0)


class BestRateOfClimbTest(unittest.TestCase):
    def test_sea_level_worked_case(self):
        roc, v = cpf.best_rate_of_climb_fpm(W, S, 1.0, CD0, K, T0)
        self.assertAlmostEqual(roc, 6289.17, places=1)
        self.assertAlmostEqual(v, 516.79, places=1)

    def test_ten_thousand_feet_worked_case(self):
        sigma = cpf.isa_density_ratio(10000)
        t = cpf.thrust_available(T0, sigma)
        roc, v = cpf.best_rate_of_climb_fpm(W, S, sigma, CD0, K, t)
        self.assertAlmostEqual(roc, 5178.95, places=1)
        self.assertAlmostEqual(v, 544.86, places=1)

    def test_rate_falls_with_altitude(self):
        roc_sl, _ = cpf.best_rate_of_climb_fpm(W, S, 1.0, CD0, K, T0)
        sigma20 = cpf.isa_density_ratio(20000)
        roc20, _ = cpf.best_rate_of_climb_fpm(W, S, sigma20, CD0, K, cpf.thrust_available(T0, sigma20))
        self.assertGreater(roc_sl, roc20)

    def test_no_climb_capability_raises(self):
        with self.assertRaises(ValueError):
            cpf.best_rate_of_climb_fpm(W, S, 1.0, CD0, K, 500.0)
        with self.assertRaises(ValueError):
            cpf.best_rate_of_climb_fpm(W, S, 1.0, CD0, K, T0, v_min_ftps=900.0, v_max_ftps=200.0)
        with self.assertRaises(ValueError):
            cpf.best_rate_of_climb_fpm(0, S, 1.0, CD0, K, T0)


class CeilingTest(unittest.TestCase):
    def test_service_ceiling_worked_case(self):
        # 100 ft/min threshold: 56354 ft
        self.assertAlmostEqual(cpf.service_ceiling_ft(W, S, CD0, K, T0), 56354.05, delta=2.0)

    def test_higher_threshold_lower_ceiling(self):
        # 500 ft/min threshold sits below the 100 ft/min ceiling
        self.assertAlmostEqual(cpf.service_ceiling_ft(W, S, CD0, K, T0, roc_target_fpm=500.0), 52980.08, delta=2.0)
        self.assertLess(
            cpf.service_ceiling_ft(W, S, CD0, K, T0, roc_target_fpm=500.0),
            cpf.service_ceiling_ft(W, S, CD0, K, T0),
        )

    def test_absolute_ceiling_above_service(self):
        self.assertAlmostEqual(cpf.absolute_ceiling_ft(W, S, CD0, K, T0), 57188.84, delta=2.0)
        self.assertGreater(
            cpf.absolute_ceiling_ft(W, S, CD0, K, T0),
            cpf.service_ceiling_ft(W, S, CD0, K, T0),
        )

    def test_no_climb_capability_raises(self):
        with self.assertRaises(ValueError):
            cpf.service_ceiling_ft(W, S, CD0, K, 500.0)
        with self.assertRaises(ValueError):
            cpf.service_ceiling_ft(W, S, CD0, K, T0, roc_target_fpm=-10.0)


class TimeToClimbTest(unittest.TestCase):
    def test_worked_case(self):
        self.assertAlmostEqual(cpf.time_to_climb_min(0, 20000, W, S, CD0, K, T0), 3.911, places=2)
        self.assertAlmostEqual(cpf.time_to_climb_min(0, 30000, W, S, CD0, K, T0), 6.692, places=2)
        self.assertAlmostEqual(cpf.time_to_climb_min(10000, 20000, W, S, CD0, K, T0), 2.160, places=2)

    def test_additivity(self):
        # 0 to 10k plus 10k to 20k equals 0 to 20k
        a = cpf.time_to_climb_min(0, 10000, W, S, CD0, K, T0)
        b = cpf.time_to_climb_min(10000, 20000, W, S, CD0, K, T0)
        c = cpf.time_to_climb_min(0, 20000, W, S, CD0, K, T0)
        self.assertAlmostEqual(a + b, c, places=2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpf.time_to_climb_min(30000, 20000, W, S, CD0, K, T0)
        with self.assertRaises(ValueError):
            cpf.time_to_climb_min(-1000, 20000, W, S, CD0, K, T0)
        with self.assertRaises(ValueError):
            cpf.time_to_climb_min(0, 20000, W, S, CD0, K, T0, step_ft=0)
        with self.assertRaises(ValueError):
            cpf.time_to_climb_min(0, 70000, W, S, CD0, K, T0)
        with self.assertRaises(ValueError):
            cpf.time_to_climb_min(0, 30000, W, S, CD0, K, 500.0)


class GradientCheckTest(unittest.TestCase):
    def test_one_engine_inoperative_worked_case(self):
        # At 10000 ft at the best rate speed: OEI gradient 2.699 percent
        sigma = cpf.isa_density_ratio(10000)
        t = cpf.thrust_available(T0, sigma)
        _, v = cpf.best_rate_of_climb_fpm(W, S, sigma, CD0, K, t)
        d = cpf.drag_force(W, v, S, sigma, CD0, K)
        g = cpf.climb_gradient_pct(t / 2.0, d, W)
        self.assertAlmostEqual(g, 2.699, places=2)
        # margin against the 2.4 percent takeoff climb requirement
        self.assertAlmostEqual(cpf.gradient_margin_pct(g, 2.4), 0.299, places=2)
        self.assertGreater(g, 2.4)


class EndToEndTest(unittest.TestCase):
    def test_measurement_and_model_chain(self):
        # Flight test: 2000 ft gained in 60 s at 10000 ft pressure
        # altitude, test weight 20500 lbf, sigma 0.9 -> corrected ROC
        roc_meas = cpf.rate_of_climb_from_pressure_altitude(5000, 7000, 60)
        self.assertAlmostEqual(roc_meas, 2000.0, places=3)
        roc_std = cpf.corrected_rate_of_climb(roc_meas, 20500, 20000, 0.9)
        self.assertAlmostEqual(roc_std, 2007.25, places=2)
        # Planning model: best rate at sea level and the ceilings
        roc_sl, v_sl = cpf.best_rate_of_climb_fpm(W, S, 1.0, CD0, K, T0)
        self.assertAlmostEqual(roc_sl, 6289.17, places=1)
        self.assertAlmostEqual(v_sl, 516.79, places=1)
        self.assertAlmostEqual(cpf.service_ceiling_ft(W, S, CD0, K, T0), 56354.05, delta=2.0)
        self.assertAlmostEqual(cpf.time_to_climb_min(0, 30000, W, S, CD0, K, T0), 6.692, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
