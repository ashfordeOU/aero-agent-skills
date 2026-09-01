#!/usr/bin/env python3
"""Gate 3 contract test: control surface sizing.

Exercises scripts/control_surface_sizing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - control surface
sizing from control power: aileron area from the target roll rate
with the roll damping derivative, elevator area from the pitch moment
requirement, rudder area from the yaw moment requirement, hinge
moment for actuator sizing, and deflection limit checks; invalid
inputs raise ValueError. Units: SI, angles in rad (deg where noted).

Analytic anchors (hand-computed):
  p = -2*85*0.1032*0.436/(34*(-0.45)) = 0.4999 rad/s
  C_l_delta_a = 2*0.5*5.5*13.5*5.67/(120*34) = 0.1032 per rad
  S_a = 5.6714 m^2 (both wings) for p_req = 0.5 rad/s
  C_m_delta_e = -0.9*0.7*4.5*0.6 = -1.701 per rad
  S_e = 0.22*21/(0.9*0.7*4.5*0.6*0.436) = 6.2295 m^2
  C_n_delta_r = -0.9*0.06*3.5*0.6 = -0.1134 per rad
  S_r = 0.022*18.83/(0.9*0.06*3.5*0.6*0.524) = 6.9715 m^2
  control power = 1.701*0.436 = 0.7416
  H = 0.1526*4425.31*6.22*0.35 = 1470.13 N m
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import control_surface_sizing_logic as csl  # noqa: E402


class RollRateAchievedTest(unittest.TestCase):
    def test_analytic_roll_rate(self):
        # -2*85*0.1032*0.436/(34*(-0.45)) = 0.4999 rad/s
        self.assertAlmostEqual(
            csl.roll_rate_achieved(0.1032, 0.436, 85.0, 34.0, -0.45),
            0.4999,
            places=4,
        )

    def test_round_trip_with_aileron_area(self):
        # S_a = 5.6714 m^2 gives C_l_delta_a = 0.1032, which must
        # reproduce the 0.5 rad/s target at the maximum deflection
        c_l_delta = csl.aileron_control_derivative(
            5.6714, 0.5, 5.5, 13.5, 120.0, 34.0
        )
        self.assertAlmostEqual(
            csl.roll_rate_achieved(c_l_delta, 0.436, 85.0, 34.0, -0.45),
            0.5,
            places=4,
        )

    def test_higher_deflection_raises_roll_rate(self):
        self.assertGreater(
            csl.roll_rate_achieved(0.1032, 0.5, 85.0, 34.0, -0.45),
            csl.roll_rate_achieved(0.1032, 0.436, 85.0, 34.0, -0.45),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.roll_rate_achieved(0, 0.436, 85.0, 34.0, -0.45)
        with self.assertRaises(ValueError):
            csl.roll_rate_achieved(0.1032, 0, 85.0, 34.0, -0.45)
        with self.assertRaises(ValueError):
            csl.roll_rate_achieved(0.1032, 0.436, 0, 34.0, -0.45)
        with self.assertRaises(ValueError):
            csl.roll_rate_achieved(0.1032, 0.436, 85.0, 0, -0.45)
        with self.assertRaises(ValueError):
            csl.roll_rate_achieved(0.1032, 0.436, 85.0, 34.0, 0.45)


class AileronControlDerivativeTest(unittest.TestCase):
    def test_analytic_derivative(self):
        # 2*0.5*5.5*13.5*5.67/(120*34) = 420.9975/4080 = 0.1032
        self.assertAlmostEqual(
            csl.aileron_control_derivative(5.67, 0.5, 5.5, 13.5, 120.0, 34.0),
            0.1032,
            places=4,
        )

    def test_more_area_raises_derivative(self):
        self.assertGreater(
            csl.aileron_control_derivative(6.5, 0.5, 5.5, 13.5, 120.0, 34.0),
            csl.aileron_control_derivative(5.67, 0.5, 5.5, 13.5, 120.0, 34.0),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.aileron_control_derivative(0, 0.5, 5.5, 13.5, 120.0, 34.0)
        with self.assertRaises(ValueError):
            csl.aileron_control_derivative(5.67, 1.5, 5.5, 13.5, 120.0, 34.0)
        with self.assertRaises(ValueError):
            csl.aileron_control_derivative(5.67, 0.5, 0, 13.5, 120.0, 34.0)
        with self.assertRaises(ValueError):
            csl.aileron_control_derivative(5.67, 0.5, 5.5, 0, 120.0, 34.0)
        with self.assertRaises(ValueError):
            csl.aileron_control_derivative(5.67, 0.5, 5.5, 13.5, 0, 34.0)
        with self.assertRaises(ValueError):
            csl.aileron_control_derivative(5.67, 0.5, 5.5, 13.5, 120.0, 0)


class AileronAreaRequiredTest(unittest.TestCase):
    def test_analytic_area(self):
        # p_req = 0.5 rad/s at V = 85 m/s -> S_a = 5.6714 m^2
        self.assertAlmostEqual(
            csl.aileron_area_required(
                0.5, 85.0, 34.0, -0.45, 0.436, 0.5, 5.5, 13.5, 120.0
            ),
            5.6714,
            places=4,
        )

    def test_higher_roll_rate_requires_more_area(self):
        self.assertGreater(
            csl.aileron_area_required(
                0.6, 85.0, 34.0, -0.45, 0.436, 0.5, 5.5, 13.5, 120.0
            ),
            csl.aileron_area_required(
                0.5, 85.0, 34.0, -0.45, 0.436, 0.5, 5.5, 13.5, 120.0
            ),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.aileron_area_required(
                0, 85.0, 34.0, -0.45, 0.436, 0.5, 5.5, 13.5, 120.0
            )
        with self.assertRaises(ValueError):
            csl.aileron_area_required(
                0.5, 85.0, 34.0, 0.45, 0.436, 0.5, 5.5, 13.5, 120.0
            )
        with self.assertRaises(ValueError):
            csl.aileron_area_required(
                0.5, 85.0, 34.0, -0.45, 0, 0.5, 5.5, 13.5, 120.0
            )


class ElevatorPitchDerivativeTest(unittest.TestCase):
    def test_analytic_derivative(self):
        # -0.9*0.7*4.5*0.6 = -1.701 per rad
        self.assertAlmostEqual(
            csl.elevator_pitch_derivative(0.9, 0.7, 4.5, 0.6), -1.701, places=6
        )

    def test_negative_for_aft_tail(self):
        self.assertLess(csl.elevator_pitch_derivative(0.9, 0.7, 4.5, 0.6), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.elevator_pitch_derivative(0, 0.7, 4.5, 0.6)
        with self.assertRaises(ValueError):
            csl.elevator_pitch_derivative(0.9, 0, 4.5, 0.6)
        with self.assertRaises(ValueError):
            csl.elevator_pitch_derivative(0.9, 0.7, 0, 0.6)
        with self.assertRaises(ValueError):
            csl.elevator_pitch_derivative(0.9, 0.7, 4.5, 1.5)


class ElevatorAreaRequiredTest(unittest.TestCase):
    def test_analytic_area(self):
        # 0.22*21/(0.9*0.7*4.5*0.6*0.436) = 4.62/0.741636 = 6.2295 m^2
        self.assertAlmostEqual(
            csl.elevator_area_required(0.22, 21.0, 0.9, 0.7, 4.5, 0.6, 0.436),
            6.2295,
            places=4,
        )

    def test_control_power_covers_requirement(self):
        # |C_m_delta_e| * delta_max = 0.7416 >= C_m_req = 0.22
        c_m_de = csl.elevator_pitch_derivative(0.9, 0.7, 4.5, 0.6)
        power = csl.control_power(c_m_de, 0.436)
        self.assertGreaterEqual(power, 0.22)

    def test_larger_requirement_needs_more_area(self):
        self.assertGreater(
            csl.elevator_area_required(0.3, 21.0, 0.9, 0.7, 4.5, 0.6, 0.436),
            csl.elevator_area_required(0.22, 21.0, 0.9, 0.7, 4.5, 0.6, 0.436),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.elevator_area_required(0, 21.0, 0.9, 0.7, 4.5, 0.6, 0.436)
        with self.assertRaises(ValueError):
            csl.elevator_area_required(0.22, 0, 0.9, 0.7, 4.5, 0.6, 0.436)
        with self.assertRaises(ValueError):
            csl.elevator_area_required(0.22, 21.0, 0.9, 0.7, 0, 0.6, 0.436)
        with self.assertRaises(ValueError):
            csl.elevator_area_required(0.22, 21.0, 0.9, 0.7, 4.5, 0.6, 0)


class RudderYawDerivativeTest(unittest.TestCase):
    def test_analytic_derivative(self):
        # -0.9*0.06*3.5*0.6 = -0.1134 per rad
        self.assertAlmostEqual(
            csl.rudder_yaw_derivative(0.9, 0.06, 3.5, 0.6), -0.1134, places=6
        )

    def test_negative_for_aft_fin(self):
        self.assertLess(csl.rudder_yaw_derivative(0.9, 0.06, 3.5, 0.6), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.rudder_yaw_derivative(0, 0.06, 3.5, 0.6)
        with self.assertRaises(ValueError):
            csl.rudder_yaw_derivative(0.9, 0, 3.5, 0.6)
        with self.assertRaises(ValueError):
            csl.rudder_yaw_derivative(0.9, 0.06, 0, 0.6)
        with self.assertRaises(ValueError):
            csl.rudder_yaw_derivative(0.9, 0.06, 3.5, 0)


class RudderAreaRequiredTest(unittest.TestCase):
    def test_analytic_area(self):
        # 0.022*18.83/(0.9*0.06*3.5*0.6*0.524) = 0.41426/0.0594216
        # = 6.9715 m^2
        self.assertAlmostEqual(
            csl.rudder_area_required(0.022, 18.83, 0.9, 0.06, 3.5, 0.6, 0.524),
            6.9715,
            places=4,
        )

    def test_yaw_authority_covers_requirement(self):
        # |C_n_delta_r| * delta_max = 0.0594 >= C_n_req = 0.022
        c_n_dr = csl.rudder_yaw_derivative(0.9, 0.06, 3.5, 0.6)
        power = csl.control_power(c_n_dr, 0.524)
        self.assertGreaterEqual(power, 0.022)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.rudder_area_required(0, 18.83, 0.9, 0.06, 3.5, 0.6, 0.524)
        with self.assertRaises(ValueError):
            csl.rudder_area_required(0.022, 0, 0.9, 0.06, 3.5, 0.6, 0.524)
        with self.assertRaises(ValueError):
            csl.rudder_area_required(0.022, 18.83, 0.9, 0.06, 0, 0.6, 0.524)
        with self.assertRaises(ValueError):
            csl.rudder_area_required(0.022, 18.83, 0.9, 0.06, 3.5, 0.6, 0)


class ControlPowerTest(unittest.TestCase):
    def test_analytic_power(self):
        # |(-1.701)|*0.436 = 0.7416
        self.assertAlmostEqual(csl.control_power(-1.701, 0.436), 0.7416, places=4)

    def test_sign_independent(self):
        self.assertEqual(
            csl.control_power(-1.701, 0.436), csl.control_power(1.701, 0.436)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.control_power(-1.701, 0)


class HingeMomentTest(unittest.TestCase):
    def test_analytic_hinge_moment(self):
        # 0.1526*4425.31*6.22*0.35 = 1470.13 N m
        self.assertAlmostEqual(
            csl.hinge_moment(0.1526, 4425.31, 6.22, 0.35), 1470.13, places=2
        )

    def test_dynamic_pressure_scales_hinge_moment(self):
        self.assertGreater(
            csl.hinge_moment(0.1526, 6000.0, 6.22, 0.35),
            csl.hinge_moment(0.1526, 4425.31, 6.22, 0.35),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.hinge_moment(0, 4425.31, 6.22, 0.35)
        with self.assertRaises(ValueError):
            csl.hinge_moment(0.1526, 0, 6.22, 0.35)
        with self.assertRaises(ValueError):
            csl.hinge_moment(0.1526, 4425.31, 0, 0.35)
        with self.assertRaises(ValueError):
            csl.hinge_moment(0.1526, 4425.31, 6.22, 0)


class DeflectionLimitCheckTest(unittest.TestCase):
    def test_elevator_20_deg_within(self):
        result = csl.deflection_limit_check(20.0, -15.0, 25.0)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["margin_deg"], 5.0, places=6)

    def test_elevator_26_deg_outside_upper(self):
        result = csl.deflection_limit_check(26.0, -15.0, 25.0)
        self.assertFalse(result["within"])
        self.assertAlmostEqual(result["margin_deg"], -1.0, places=6)
        self.assertIn("above upper limit", result["verdict"])

    def test_elevator_minus_16_deg_outside_lower(self):
        result = csl.deflection_limit_check(-16.0, -15.0, 25.0)
        self.assertFalse(result["within"])
        self.assertIn("below lower limit", result["verdict"])

    def test_aileron_limits_are_symmetric(self):
        self.assertTrue(csl.deflection_limit_check(25.0, -25.0, 25.0)["within"])
        self.assertFalse(csl.deflection_limit_check(25.5, -25.0, 25.0)["within"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            csl.deflection_limit_check(10.0, 30.0, 25.0)
        with self.assertRaises(ValueError):
            csl.deflection_limit_check(10.0, 25.0, 25.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
