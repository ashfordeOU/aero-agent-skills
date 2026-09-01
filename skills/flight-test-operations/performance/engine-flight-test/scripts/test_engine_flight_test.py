#!/usr/bin/env python3
"""Gate 3 contract test: engine flight test thrust and margin logic.

Exercises scripts/engine_flight_test_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - thrust from rate
of climb and level acceleration, fuel flow from TSFC and TSFC from
flight, EGT margin and ISA correction, altitude thrust scaling, and
acceleration and deceleration transient times; invalid inputs raise
ValueError. Analytic checks: W=400000 N, ROC=10 m/s at V=80 m/s and
D=50000 N gives T=100000 N; T = D + (W/g)*a with g=10 gives 70000 N;
TSFC 2.5e-5 at 100000 N gives Wf=2.5 kg/s; EGT 780 against limit 850
gives margin 70 deg C; EGT 800 at 300 K corrects to 757.6 deg C;
T_sl 100000 scaled by 0.5/1.225 gives 40816.3 N; accel 80 to 100 m/s
at 40000 N excess with g=10 takes 20 s; achieved 98000 against
predicted 100000 gives -2.0 percent.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine_flight_test_logic as eft  # noqa: E402


class ThrustFromRateOfClimbTest(unittest.TestCase):
    def test_analytic_check(self):
        # 50000 + 400000 * 10 / 80 = 50000 + 50000 = 100000 N
        self.assertAlmostEqual(eft.thrust_from_rate_of_climb(400000, 10, 80, 50000), 100000.0, places=3)

    def test_level_flight_is_drag_only(self):
        self.assertAlmostEqual(eft.thrust_from_rate_of_climb(400000, 0, 80, 50000), 50000.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.thrust_from_rate_of_climb(0, 10, 80, 50000)
        with self.assertRaises(ValueError):
            eft.thrust_from_rate_of_climb(400000, -10, 80, 50000)
        with self.assertRaises(ValueError):
            eft.thrust_from_rate_of_climb(400000, 10, 0, 50000)
        with self.assertRaises(ValueError):
            eft.thrust_from_rate_of_climb(400000, 10, 80, 0)


class ThrustFromAccelerationTest(unittest.TestCase):
    def test_analytic_check_g10(self):
        # 50000 + (400000 / 10) * 0.5 = 50000 + 20000 = 70000 N
        self.assertAlmostEqual(eft.thrust_from_acceleration(400000, 0.5, 50000, g_m_s2=10), 70000.0, places=3)

    def test_default_gravity_check(self):
        # (400000 / 9.80665) * 0.5 + 50000 = 70394.3 N
        self.assertAlmostEqual(eft.thrust_from_acceleration(400000, 0.5, 50000), 70394.3, places=1)

    def test_zero_acceleration_is_drag_only(self):
        self.assertAlmostEqual(eft.thrust_from_acceleration(400000, 0, 50000), 50000.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.thrust_from_acceleration(0, 0.5, 50000)
        with self.assertRaises(ValueError):
            eft.thrust_from_acceleration(400000, -0.5, 50000)
        with self.assertRaises(ValueError):
            eft.thrust_from_acceleration(400000, 0.5, 0)
        with self.assertRaises(ValueError):
            eft.thrust_from_acceleration(400000, 0.5, 50000, g_m_s2=0)


class FuelFlowFromTSFCTest(unittest.TestCase):
    def test_analytic_check(self):
        # 2.5e-5 * 100000 = 2.5 kg/s
        self.assertAlmostEqual(eft.fuel_flow_from_tsfc(2.5e-5, 100000), 2.5, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.fuel_flow_from_tsfc(0, 100000)
        with self.assertRaises(ValueError):
            eft.fuel_flow_from_tsfc(2.5e-5, 0)


class TSFCFlightTest(unittest.TestCase):
    def test_analytic_check(self):
        # 2.5 / 100000 = 2.5e-5 kg/(N*s)
        self.assertAlmostEqual(eft.tsfc_from_flight(2.5, 100000), 2.5e-5, places=9)

    def test_round_trip(self):
        self.assertAlmostEqual(
            eft.tsfc_from_flight(eft.fuel_flow_from_tsfc(2.5e-5, 100000), 100000), 2.5e-5, places=9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.tsfc_from_flight(0, 100000)
        with self.assertRaises(ValueError):
            eft.tsfc_from_flight(2.5, 0)


class EGTMarginTest(unittest.TestCase):
    def test_analytic_check(self):
        # 850 - 780 = 70 deg C
        self.assertAlmostEqual(eft.egt_margin(780, 850), 70.0, places=3)

    def test_exceeded_limit_is_negative(self):
        # 850 - 900 = -50: a finding, not an error
        self.assertAlmostEqual(eft.egt_margin(900, 850), -50.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.egt_margin(-300, 850)
        with self.assertRaises(ValueError):
            eft.egt_margin(780, 0)


class EGTCorrectedToISATest(unittest.TestCase):
    def test_analytic_check(self):
        # (800 + 273.15) * 288.15 / 300 - 273.15 = 757.6 deg C
        self.assertAlmostEqual(eft.egt_corrected_to_isa(800, 300), 757.6, places=1)

    def test_isa_day_unchanged(self):
        # at 288.15 K the correction is identity
        self.assertAlmostEqual(eft.egt_corrected_to_isa(780, 288.15), 780.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.egt_corrected_to_isa(780, 0)
        with self.assertRaises(ValueError):
            eft.egt_corrected_to_isa(780, -288)


class ThrustAtAltitudeTest(unittest.TestCase):
    def test_analytic_check(self):
        # 100000 * 0.5 / 1.225 = 40816.3 N
        self.assertAlmostEqual(eft.thrust_at_altitude(100000, 0.5, 1.225), 40816.3, places=1)

    def test_same_density_unchanged(self):
        self.assertAlmostEqual(eft.thrust_at_altitude(100000, 1.225, 1.225), 100000.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.thrust_at_altitude(0, 0.5, 1.225)
        with self.assertRaises(ValueError):
            eft.thrust_at_altitude(100000, 0, 1.225)
        with self.assertRaises(ValueError):
            eft.thrust_at_altitude(100000, 0.5, 0)


class AccelTimeBetweenSpeedsTest(unittest.TestCase):
    def test_analytic_check_g10(self):
        # (400000 / 10) * (100 - 80) / 40000 = 20 s
        self.assertAlmostEqual(eft.accel_time_between_speeds(400000, 80, 100, 40000, g_m_s2=10), 20.0, places=3)

    def test_default_gravity_check(self):
        # (400000 / 9.80665) * 20 / 40000 = 20.39 s
        self.assertAlmostEqual(eft.accel_time_between_speeds(400000, 80, 100, 40000), 20.39, places=2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.accel_time_between_speeds(0, 80, 100, 40000)
        with self.assertRaises(ValueError):
            eft.accel_time_between_speeds(400000, 100, 80, 40000)
        with self.assertRaises(ValueError):
            eft.accel_time_between_speeds(400000, 80, 100, 0)
        with self.assertRaises(ValueError):
            eft.accel_time_between_speeds(400000, 80, 100, 40000, g_m_s2=0)


class DecelTimeBetweenSpeedsTest(unittest.TestCase):
    def test_analytic_check_g10(self):
        # (400000 / 10) * (100 - 80) / 40000 = 20 s
        self.assertAlmostEqual(eft.decel_time_between_speeds(400000, 100, 80, 40000, g_m_s2=10), 20.0, places=3)

    def test_default_gravity_check(self):
        # (400000 / 9.80665) * 20 / 40000 = 20.39 s
        self.assertAlmostEqual(eft.decel_time_between_speeds(400000, 100, 80, 40000), 20.39, places=2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.decel_time_between_speeds(0, 100, 80, 40000)
        with self.assertRaises(ValueError):
            eft.decel_time_between_speeds(400000, 80, 100, 40000)
        with self.assertRaises(ValueError):
            eft.decel_time_between_speeds(400000, 100, 80, 0)
        with self.assertRaises(ValueError):
            eft.decel_time_between_speeds(400000, 100, 80, 40000, g_m_s2=0)


class ThrustVerificationErrorTest(unittest.TestCase):
    def test_analytic_check_shortfall(self):
        # (98000 - 100000) / 100000 * 100 = -2.0 percent
        self.assertAlmostEqual(eft.thrust_verification_error(98000, 100000), -2.0, places=3)

    def test_excess_is_positive(self):
        # (102000 - 100000) / 100000 * 100 = 2.0 percent
        self.assertAlmostEqual(eft.thrust_verification_error(102000, 100000), 2.0, places=3)

    def test_match_is_zero(self):
        self.assertAlmostEqual(eft.thrust_verification_error(100000, 100000), 0.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.thrust_verification_error(0, 100000)
        with self.assertRaises(ValueError):
            eft.thrust_verification_error(98000, 0)


class EngineFlightTestEndToEndTest(unittest.TestCase):
    def test_full_measurement_chain(self):
        # Climb test: W 400000 N, ROC 10 m/s at V 80 m/s, D 50000 N.
        thrust = eft.thrust_from_rate_of_climb(400000, 10, 80, 50000)
        self.assertAlmostEqual(thrust, 100000.0, places=3)
        fuel_flow = eft.fuel_flow_from_tsfc(2.5e-5, thrust)
        self.assertAlmostEqual(fuel_flow, 2.5, places=3)
        margin = eft.egt_margin(780, 850)
        self.assertAlmostEqual(margin, 70.0, places=3)
        thrust_alt = eft.thrust_at_altitude(thrust, 0.5, 1.225)
        self.assertAlmostEqual(thrust_alt, 40816.3, places=1)
        err = eft.thrust_verification_error(98000, 100000)
        self.assertAlmostEqual(err, -2.0, places=3)
        t_accel = eft.accel_time_between_speeds(400000, 80, 100, 40000, g_m_s2=10)
        self.assertAlmostEqual(t_accel, 20.0, places=3)
        t_decel = eft.decel_time_between_speeds(400000, 100, 80, 40000, g_m_s2=10)
        self.assertAlmostEqual(t_decel, 20.0, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
