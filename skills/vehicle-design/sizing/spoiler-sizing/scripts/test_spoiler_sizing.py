#!/usr/bin/env python3
"""Contract test for the spoiler sizing logic (stdlib, offline).

Covers the transport worked example (S = 122 m^2, b = 34 m, design
roll rate 0.5 rad/s at 85 m/s, aileron share 0.65, 60 percent lift
dump), the roll share split, the flight spoiler area and deflection
sizing from the roll damping requirement, the ground spoiler belt
area from the touchdown lift dump, the lift dump and speed brake
drag increments, the hinge moment, the deflection and geometry limit
checks, the sized verdict, and ValueError rejection of non-physical
inputs. Runs with: python3 scripts/test_spoiler_sizing.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spoiler_sizing_logic as m

Q_MAN = 0.5 * m.RHO_SL * 85.0 ** 2  # 4425.3125 Pa
C_L_REQ = 0.045
C_L_SPOIL_REQ = 0.01575
L_SHARE = 289110.0909375
A_FLIGHT = 15.404076425387577
A_PER_PANEL = 3.8510191063468944
A_DUMP = 56.34938627290747
DCD_SPEED = 0.09642387746042605
DCD_DUMP = 0.108
H_FLIGHT = 5061.186114902643
ALPHA_RAD = 4.0 * math.pi / 180.0
DELTA45_RAD = 45.0 * math.pi / 180.0


class TestRollShareAndCoefficient(unittest.TestCase):
    def test_share_worked_and_complement(self):
        self.assertAlmostEqual(m.roll_spoiler_share(0.65), 0.35, places=12)
        for f in (0.1, 0.6, 0.7, 0.9):
            self.assertAlmostEqual(m.roll_spoiler_share(f) + f, 1.0, places=12)

    def test_share_rejects_out_of_band(self):
        for bad in (0.0, 1.0, -0.1, 1.5, "high"):
            with self.assertRaises((ValueError, TypeError)):
                m.roll_spoiler_share(bad)

    def test_coefficient_worked_example_and_scaling(self):
        self.assertAlmostEqual(
            m.roll_coefficient_required(0.5, 85.0, 34.0, -0.45), C_L_REQ, places=12
        )
        self.assertAlmostEqual(
            m.roll_coefficient_required(1.0, 85.0, 34.0, -0.45),
            2.0 * C_L_REQ,
            places=12,
        )

    def test_coefficient_rejects_invalid(self):
        for bad in (0.0, -0.5):
            with self.assertRaises(ValueError):
                m.roll_coefficient_required(bad, 85.0, 34.0, -0.45)
            with self.assertRaises(ValueError):
                m.roll_coefficient_required(0.5, bad, 34.0, -0.45)
            with self.assertRaises(ValueError):
                m.roll_coefficient_required(0.5, 85.0, bad, -0.45)
        with self.assertRaises(ValueError):
            m.roll_coefficient_required(0.5, 85.0, 34.0, 0.45)

    def test_share_coefficient_and_moment(self):
        self.assertAlmostEqual(
            m.spoiler_share_coefficient(C_L_REQ, 0.35), C_L_SPOIL_REQ, places=12
        )
        l = m.roll_moment_share(C_L_SPOIL_REQ, Q_MAN, 122.0, 34.0)
        self.assertAlmostEqual(l, L_SHARE, places=6)
        self.assertAlmostEqual(l / (Q_MAN * 122.0 * 34.0), C_L_SPOIL_REQ, places=12)

    def test_share_coefficient_and_moment_reject_invalid(self):
        with self.assertRaises(ValueError):
            m.spoiler_share_coefficient(-0.1, 0.35)
        with self.assertRaises(ValueError):
            m.spoiler_share_coefficient(0.045, 1.2)
        with self.assertRaises(ValueError):
            m.roll_moment_share(0.01575, 0.0, 122.0, 34.0)


class TestFlightSpoilerArea(unittest.TestCase):
    def test_area_worked_example(self):
        a = m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, -0.4, 13.5)
        self.assertAlmostEqual(a, A_FLIGHT, places=6)
        self.assertAlmostEqual(a / 4.0, A_PER_PANEL, places=6)

    def test_area_recovers_share_coefficient(self):
        a = m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, -0.4, 13.5)
        c_l_cap = abs(-0.4) * (a / 122.0) * DELTA45_RAD * (13.5 / 34.0)
        self.assertAlmostEqual(c_l_cap, C_L_SPOIL_REQ, places=10)

    def test_area_scaling_with_effectiveness_and_q(self):
        a1 = m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, -0.5, 13.5)
        a2 = m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, -0.25, 13.5)
        self.assertAlmostEqual(a1, 0.5 * a2, places=6)
        a3 = m.flight_spoiler_area(L_SHARE, 2.0 * Q_MAN, 122.0, 34.0, -0.4, 13.5)
        self.assertAlmostEqual(m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, -0.4, 13.5), 2.0 * a3, places=6)

    def test_area_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, 0.4, 13.5)
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.flight_spoiler_area(bad, Q_MAN, 122.0, 34.0, -0.4, 13.5)
            with self.assertRaises(ValueError):
                m.flight_spoiler_area(L_SHARE, bad, 122.0, 34.0, -0.4, 13.5)
            with self.assertRaises(ValueError):
                m.flight_spoiler_area(L_SHARE, Q_MAN, bad, 34.0, -0.4, 13.5)
            with self.assertRaises(ValueError):
                m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, bad, -0.4, 13.5)
            with self.assertRaises(ValueError):
                m.flight_spoiler_area(L_SHARE, Q_MAN, 122.0, 34.0, -0.4, bad)


class TestFlightSpoilerDeflection(unittest.TestCase):
    def test_deflection_worked_example(self):
        d = m.flight_spoiler_deflection(C_L_SPOIL_REQ * 34.0 / 13.5, A_FLIGHT, 122.0, -0.4)
        self.assertAlmostEqual(d, 45.0, places=6)

    def test_deflection_round_trip_and_saturation(self):
        lift_inc = C_L_SPOIL_REQ * 34.0 / 13.5
        loss = abs(-0.4) * (A_FLIGHT / 122.0) * DELTA45_RAD
        self.assertAlmostEqual(loss, lift_inc, places=10)
        self.assertAlmostEqual(
            m.flight_spoiler_deflection(2.0 * lift_inc, A_FLIGHT, 122.0, -0.4),
            m.DELTA_MAX_DEG,
            places=12,
        )

    def test_deflection_linear_scaling_and_rejection(self):
        lift_inc = C_L_SPOIL_REQ * 34.0 / 13.5
        half = m.flight_spoiler_deflection(lift_inc / 2.0, A_FLIGHT, 122.0, -0.4)
        self.assertAlmostEqual(half, 22.5, places=6)
        with self.assertRaises(ValueError):
            m.flight_spoiler_deflection(0.0, A_FLIGHT, 122.0, -0.4)
        with self.assertRaises(ValueError):
            m.flight_spoiler_deflection(0.04, -1.0, 122.0, -0.4)
        with self.assertRaises(ValueError):
            m.flight_spoiler_deflection(0.04, A_FLIGHT, 122.0, 0.4)


class TestGroundSpoilerArea(unittest.TestCase):
    def test_ground_area_worked_example(self):
        a = m.ground_spoiler_area(0.6, 1.0, 122.0, 1.5, 60.0)
        self.assertAlmostEqual(a, A_DUMP, places=6)
        self.assertAlmostEqual(a, 0.6 * 122.0 / (1.5 * math.sin(math.pi / 3.0)), places=6)

    def test_ground_area_round_trip_and_scaling(self):
        a = m.ground_spoiler_area(0.6, 1.0, 122.0, 1.5, 60.0)
        dcl = (a / 122.0) * 1.5 * math.sin(math.pi / 3.0)
        self.assertAlmostEqual(dcl, 0.6, places=10)
        self.assertAlmostEqual(
            2.0 * m.ground_spoiler_area(0.3, 1.0, 122.0, 1.5, 60.0), a, places=6
        )

    def test_ground_area_rejects_invalid_inputs(self):
        for bad in (0.0, -0.5, 1.6, 5.0):
            with self.assertRaises(ValueError):
                m.ground_spoiler_area(0.6, 1.0, 122.0, bad, 60.0)
        for bad in (0.0, 95.0, -10.0):
            with self.assertRaises(ValueError):
                m.ground_spoiler_area(0.6, 1.0, 122.0, 1.5, bad)
        for bad_args in ((1.2, 1.0), (0.6, 0.0), (0.6, -1.0)):
            with self.assertRaises(ValueError):
                m.ground_spoiler_area(bad_args[0], bad_args[1], 122.0, 1.5, 60.0)


class TestDragIncrements(unittest.TestCase):
    def test_speed_brake_worked_example(self):
        d = m.speed_brake_drag_increment(A_FLIGHT, 122.0, 1.2, 45.0)
        self.assertAlmostEqual(d, DCD_SPEED, places=6)
        self.assertAlmostEqual(d, (A_FLIGHT / 122.0) * 1.2 * math.sin(math.pi / 4.0) * m.SPAN_FACTOR_TYP, places=12)

    def test_lift_dump_worked_example(self):
        planform = A_DUMP * m.DUMP_CHORD_FRACTION_TYP
        d = m.lift_dump_drag_increment(planform, 122.0, 1.2, 60.0)
        self.assertAlmostEqual(d, DCD_DUMP, places=12)

    def test_drag_formula_equivalence_and_scaling(self):
        a = m.speed_brake_drag_increment(10.0, 122.0, 1.2, 45.0)
        b = m.lift_dump_drag_increment(10.0, 122.0, 1.2, 45.0)
        self.assertAlmostEqual(a, b, places=12)
        d3 = m.speed_brake_drag_increment(10.0, 122.0, 1.2, 90.0)
        self.assertAlmostEqual(d3 / a, 2.0 / math.sqrt(2.0), places=10)

    def test_drag_rejects_invalid_inputs(self):
        for bad in (0.0, 91.0, -10.0):
            with self.assertRaises(ValueError):
                m.speed_brake_drag_increment(A_FLIGHT, 122.0, 1.2, bad)
        with self.assertRaises(ValueError):
            m.speed_brake_drag_increment(0.0, 122.0, 1.2, 45.0)
        with self.assertRaises(ValueError):
            m.speed_brake_drag_increment(10.0, 0.0, 1.2, 45.0)
        with self.assertRaises(ValueError):
            m.speed_brake_drag_increment(10.0, 122.0, -1.2, 45.0)


class TestHingeMoment(unittest.TestCase):
    def test_hinge_worked_example(self):
        h = m.hinge_moment(Q_MAN, A_PER_PANEL, 1.0, ALPHA_RAD, DELTA45_RAD, (0.02, 0.03, 0.35))
        self.assertAlmostEqual(h, H_FLIGHT, places=6)

    def test_hinge_moment_formula_and_linearity(self):
        h1 = m.hinge_moment(Q_MAN, A_PER_PANEL, 1.0, ALPHA_RAD, DELTA45_RAD, (0.02, 0.03, 0.35))
        bracket = 0.02 + 0.03 * ALPHA_RAD + 0.35 * DELTA45_RAD
        self.assertAlmostEqual(h1, Q_MAN * A_PER_PANEL * 1.0 * bracket, places=10)
        h2 = m.hinge_moment(2.0 * Q_MAN, 2.0 * A_PER_PANEL, 1.0, ALPHA_RAD, DELTA45_RAD, (0.02, 0.03, 0.35))
        self.assertAlmostEqual(4.0 * h1, h2, places=6)

    def test_hinge_moment_rejects_invalid(self):
        with self.assertRaises(ValueError):
            m.hinge_moment(Q_MAN, A_PER_PANEL, 1.0, 0.07, 0.7854, (0.02, 0.03))
        with self.assertRaises(ValueError):
            m.hinge_moment(Q_MAN, A_PER_PANEL, 1.0, 0.07, 0.7854, "high")
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.hinge_moment(bad, A_PER_PANEL, 1.0, 0.07, 0.7854, (0.02, 0.03, 0.35))
            with self.assertRaises(ValueError):
                m.hinge_moment(Q_MAN, bad, 1.0, 0.07, 0.7854, (0.02, 0.03, 0.35))
            with self.assertRaises(ValueError):
                m.hinge_moment(Q_MAN, A_PER_PANEL, bad, 0.07, 0.7854, (0.02, 0.03, 0.35))


class TestLimitChecks(unittest.TestCase):
    def test_deflection_limits_band(self):
        r = m.deflection_limits_check(45.0, 60.0)
        self.assertTrue(r["within"])
        self.assertAlmostEqual(r["margin_deg"], 15.0, places=10)
        self.assertFalse(m.deflection_limits_check(61.0, 60.0)["within"])
        with self.assertRaises(ValueError):
            m.deflection_limits_check(30.0, 0.0)

    def test_geometry_limits_band(self):
        r = m.geometry_limits_check(A_PER_PANEL, 1.0, 34.0)
        self.assertAlmostEqual(r["aspect_ratio"], 3.8510191063468944, places=6)
        self.assertTrue(r["aspect_ratio_ok"])
        self.assertTrue(r["span_fraction_ok"])
        self.assertFalse(m.geometry_limits_check(8.0, 1.0, 34.0)["aspect_ratio_ok"])
        self.assertFalse(m.geometry_limits_check(20.0, 1.0, 34.0)["span_fraction_ok"])
        with self.assertRaises(ValueError):
            m.geometry_limits_check(0.0, 1.0, 34.0)


class TestVerdict(unittest.TestCase):
    def test_verdict_worked_example_values(self):
        v = m.spoiler_verdict(0.5, 85.0, 122.0, 34.0, Q_MAN, 0.65, 13.5, 0.6, 1.0)
        self.assertAlmostEqual(v["roll_spoiler_share"], 0.35, places=12)
        self.assertAlmostEqual(v["c_l_required_total"], C_L_REQ, places=10)
        self.assertAlmostEqual(v["c_l_spoiler_share"], C_L_SPOIL_REQ, places=10)
        self.assertAlmostEqual(v["roll_moment_share_nm"], L_SHARE, places=6)
        self.assertAlmostEqual(v["flight_spoiler_area_m2"], A_FLIGHT, places=6)
        self.assertAlmostEqual(v["flight_area_per_panel_m2"], A_PER_PANEL, places=6)
        self.assertAlmostEqual(v["flight_deflection_deg"], 45.0, places=6)
        self.assertAlmostEqual(v["flight_hinge_moment_nm_per_panel"], H_FLIGHT, places=6)
        self.assertAlmostEqual(v["speed_brake_drag_increment"], DCD_SPEED, places=6)
        self.assertAlmostEqual(v["ground_spoiler_area_m2"], A_DUMP, places=6)
        self.assertAlmostEqual(v["lift_dump_drag_increment"], DCD_DUMP, places=6)

    def test_verdict_keys_and_limits_all_within(self):
        v = m.spoiler_verdict(0.5, 85.0, 122.0, 34.0, Q_MAN, 0.65, 13.5, 0.6, 1.0)
        for key in (
            "flight_panels",
            "flight_deflection_deg",
            "limits",
            "geometry",
            "dump_span_fraction",
            "dump_span_ok",
            "verdict",
        ):
            self.assertIn(key, v)
        self.assertAlmostEqual(v["flight_panels"], 4, places=12)
        self.assertTrue(v["limits"]["within"])
        self.assertTrue(v["geometry"]["aspect_ratio_ok"])
        self.assertTrue(v["geometry"]["span_fraction_ok"])
        self.assertTrue(v["dump_span_ok"])
        self.assertAlmostEqual(v["dump_span_fraction"], 0.4735242543941804, places=6)
        self.assertIn("sized", v["verdict"])

    def test_verdict_drag_consistency_and_rejection(self):
        v = m.spoiler_verdict(0.5, 85.0, 122.0, 34.0, Q_MAN, 0.65, 13.5, 0.6, 1.0)
        manual = (A_FLIGHT / 122.0) * 1.2 * math.sin(math.pi / 4.0) * m.SPAN_FACTOR_TYP
        self.assertAlmostEqual(v["speed_brake_drag_increment"], manual, places=12)
        with self.assertRaises(ValueError):
            m.spoiler_verdict(0.5, 85.0, 122.0, 34.0, Q_MAN, 1.1, 13.5, 0.6, 1.0)


if __name__ == "__main__":
    unittest.main()
