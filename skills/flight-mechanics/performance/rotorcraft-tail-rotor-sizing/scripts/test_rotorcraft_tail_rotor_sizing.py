"""Contract test for rotorcraft-tail-rotor-sizing (flight-mechanics).

Deterministic, offline, stdlib unittest. Run:
    python3 scripts/test_rotorcraft_tail_rotor_sizing.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rotorcraft_tail_rotor_sizing_logic as tr


class TestWorkedExample(unittest.TestCase):
    """Wave-31 worked example: 400 kW at 27 rad/s, 8 m arm, 300 Pa ceiling."""

    def setUp(self):
        self.r = tr.tail_rotor_sizing(
            400000.0, 27.0, 8.0, max_disk_loading=300.0, rho=1.225,
            margin_factor=1.0, solidity=0.10, drag_coefficient=0.012,
            tip_speed=200.0, k=1.15)

    def test_torque_anchor(self):
        self.assertAlmostEqual(self.r["main_rotor_torque_nm"], 14815.0,
                               delta=7.5)

    def test_thrust_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_thrust_N"], 1851.9,
                               delta=0.95)

    def test_area_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_area_m2"], 6.1728,
                               delta=0.005)

    def test_radius_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_radius_m"], 1.4017,
                               delta=0.0008)

    def test_disk_loading_at_ceiling(self):
        self.assertAlmostEqual(self.r["tail_rotor_disk_loading_Pa"], 300.0,
                               delta=1e-6)

    def test_induced_velocity_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_induced_velocity"], 11.066,
                               delta=0.006)

    def test_ideal_power_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_ideal_power_W"], 20492.0,
                               delta=11.0)

    def test_profile_power_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_profile_power_W"], 9074.1,
                               delta=5.0)

    def test_total_power_anchor(self):
        self.assertAlmostEqual(self.r["tail_rotor_total_power_W"], 32640.0,
                               delta=17.0)

    def test_magnitude_bounds(self):
        self.assertTrue(13000.0 <= self.r["main_rotor_torque_nm"] <= 17000.0)
        self.assertTrue(1500.0 <= self.r["tail_rotor_thrust_N"] <= 2200.0)
        self.assertTrue(5.0 <= self.r["tail_rotor_area_m2"] <= 7.5)
        self.assertTrue(1.2 <= self.r["tail_rotor_radius_m"] <= 1.6)
        self.assertTrue(9.0 <= self.r["tail_rotor_induced_velocity"] <= 13.0)
        self.assertTrue(15000.0 <= self.r["tail_rotor_ideal_power_W"]
                        <= 26000.0)
        self.assertTrue(22000.0 <= self.r["tail_rotor_total_power_W"]
                        <= 36000.0)

    def test_total_power_formula(self):
        expected = (tr.K_DEFAULT * self.r["tail_rotor_ideal_power_W"]
                    + self.r["tail_rotor_profile_power_W"])
        self.assertAlmostEqual(self.r["tail_rotor_total_power_W"], expected,
                               places=6)


class TestFunctions(unittest.TestCase):

    def test_main_rotor_torque(self):
        self.assertAlmostEqual(tr.main_rotor_torque(400000.0, 27.0),
                               14814.8148, places=3)

    def test_main_rotor_torque_zero_power(self):
        self.assertEqual(tr.main_rotor_torque(0.0, 27.0), 0.0)

    def test_main_rotor_torque_negative_power_raises(self):
        with self.assertRaises(ValueError):
            tr.main_rotor_torque(-1.0, 27.0)

    def test_main_rotor_torque_nonpositive_omega_raises(self):
        with self.assertRaises(ValueError):
            tr.main_rotor_torque(100.0, 0.0)
        with self.assertRaises(ValueError):
            tr.main_rotor_torque(100.0, -5.0)

    def test_tail_rotor_thrust_basic(self):
        self.assertAlmostEqual(tr.tail_rotor_thrust(14814.8148, 8.0),
                               1851.8519, places=3)

    def test_tail_rotor_thrust_margin_scales(self):
        base = tr.tail_rotor_thrust(14814.8148, 8.0, margin_factor=1.0)
        marg = tr.tail_rotor_thrust(14814.8148, 8.0, margin_factor=1.2)
        self.assertAlmostEqual(marg, 1.2 * base, places=9)

    def test_tail_rotor_thrust_zero_torque_ok(self):
        self.assertEqual(tr.tail_rotor_thrust(0.0, 8.0), 0.0)

    def test_tail_rotor_thrust_valueerrors(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_thrust(-1.0, 8.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_thrust(100.0, 0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_thrust(100.0, -2.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_thrust(100.0, 8.0, margin_factor=0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_thrust(100.0, 8.0, margin_factor=-0.5)

    def test_tail_rotor_area_basic(self):
        self.assertAlmostEqual(tr.tail_rotor_area(1851.8519, 300.0),
                               6.1728, places=3)

    def test_tail_rotor_area_zero_thrust_ok(self):
        self.assertEqual(tr.tail_rotor_area(0.0, 300.0), 0.0)

    def test_tail_rotor_area_valueerrors(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_area(-5.0, 300.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_area(100.0, 0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_area(100.0, -300.0)

    def test_tail_rotor_radius_basic(self):
        self.assertAlmostEqual(tr.tail_rotor_radius(6.1728),
                               math.sqrt(6.1728 / math.pi), places=9)

    def test_tail_rotor_radius_area_roundtrip(self):
        area = 6.1728
        radius = tr.tail_rotor_radius(area)
        self.assertAlmostEqual(math.pi * radius ** 2, area, places=6)

    def test_tail_rotor_radius_valueerror(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_radius(0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_radius(-1.0)

    def test_tail_rotor_disk_loading_basic(self):
        self.assertAlmostEqual(tr.tail_rotor_disk_loading(1851.8519, 6.1728),
                               300.0, places=2)

    def test_tail_rotor_disk_loading_valueerrors(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_disk_loading(100.0, 0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_disk_loading(-100.0, 6.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_disk_loading(100.0, -6.0)

    def test_induced_velocity_manual(self):
        expected = math.sqrt(1851.8519 / (2.0 * 1.225 * 6.1728))
        self.assertAlmostEqual(
            tr.tail_rotor_induced_velocity(1851.8519, 6.1728), expected,
            places=9)

    def test_induced_velocity_density_scaling(self):
        v_std = tr.tail_rotor_induced_velocity(1851.8519, 6.1728, rho=1.225)
        v_dense = tr.tail_rotor_induced_velocity(1851.8519, 6.1728, rho=2.0)
        self.assertLess(v_dense, v_std)

    def test_induced_velocity_valueerrors(self):
        for args in [(0.0, 6.0), (-1.0, 6.0), (100.0, 0.0), (100.0, -6.0),
                     (100.0, 6.0, 0.0), (100.0, 6.0, -1.225)]:
            with self.assertRaises(ValueError):
                tr.tail_rotor_induced_velocity(*args)

    def test_ideal_power_basic(self):
        self.assertAlmostEqual(tr.tail_rotor_ideal_power(1851.8519, 11.0657),
                               20492.0, delta=1.0)

    def test_ideal_power_zero_thrust_ok(self):
        self.assertEqual(tr.tail_rotor_ideal_power(0.0, 11.0), 0.0)

    def test_ideal_power_valueerrors(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_ideal_power(-1.0, 11.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_ideal_power(100.0, -0.5)

    def test_profile_power_manual(self):
        expected = (0.125 * 1.225 * 0.10 * 0.012 * 6.1728 * 200.0 ** 3)
        self.assertAlmostEqual(
            tr.tail_rotor_profile_power(1.225, 6.1728), expected, places=6)

    def test_profile_power_tip_speed_cubed(self):
        p200 = tr.tail_rotor_profile_power(1.225, 6.1728, tip_speed=200.0)
        p100 = tr.tail_rotor_profile_power(1.225, 6.1728, tip_speed=100.0)
        self.assertAlmostEqual(p200, 8.0 * p100, places=6)

    def test_profile_power_valueerrors(self):
        cases = [(0.0, 6.0), (-1.0, 6.0), (1.225, 0.0), (1.225, -6.0),
                 (1.225, 6.0, 0.0), (1.225, 6.0, 0.1, 0.0),
                 (1.225, 6.0, 0.1, 0.012, -200.0)]
        for args in cases:
            with self.assertRaises(ValueError):
                tr.tail_rotor_profile_power(*args)

    def test_total_power_basic(self):
        self.assertAlmostEqual(tr.tail_rotor_total_power(20491.9754,
                                                         9074.0741),
                               1.15 * 20491.9754 + 9074.0741, places=6)

    def test_total_power_valueerrors(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_total_power(-1.0, 100.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_total_power(100.0, -1.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_total_power(100.0, 100.0, k=0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_total_power(100.0, 100.0, k=-1.15)

    def test_zero_power_chain_zero_thrust(self):
        self.assertEqual(tr.main_rotor_torque(0.0, 27.0), 0.0)
        self.assertEqual(tr.tail_rotor_thrust(0.0, 8.0), 0.0)


class TestSizingChain(unittest.TestCase):

    def test_dict_keys_exact(self):
        r = tr.tail_rotor_sizing(400000.0, 27.0, 8.0)
        self.assertEqual(
            sorted(r.keys()),
            sorted(["main_rotor_torque_nm", "tail_rotor_thrust_N",
                    "tail_rotor_area_m2", "tail_rotor_radius_m",
                    "tail_rotor_disk_loading_Pa", "tail_rotor_induced_velocity",
                    "tail_rotor_ideal_power_W", "tail_rotor_profile_power_W",
                    "tail_rotor_total_power_W"]))

    def test_chain_matches_individual_functions(self):
        r = tr.tail_rotor_sizing(400000.0, 27.0, 8.0)
        q = tr.main_rotor_torque(400000.0, 27.0)
        t = tr.tail_rotor_thrust(q, 8.0)
        a = tr.tail_rotor_area(t, 300.0)
        self.assertAlmostEqual(r["main_rotor_torque_nm"], q, places=9)
        self.assertAlmostEqual(r["tail_rotor_thrust_N"], t, places=9)
        self.assertAlmostEqual(r["tail_rotor_area_m2"], a, places=9)
        self.assertAlmostEqual(
            r["tail_rotor_disk_loading_Pa"], tr.tail_rotor_disk_loading(t, a),
            places=9)

    def test_disk_loading_at_or_below_ceiling(self):
        for margin in (1.0, 1.15, 1.3):
            r = tr.tail_rotor_sizing(400000.0, 27.0, 8.0,
                                     max_disk_loading=250.0,
                                     margin_factor=margin)
            self.assertLessEqual(r["tail_rotor_disk_loading_Pa"], 250.0 + 1e-9)

    def test_roundtrip_thrust_times_arm_equals_torque(self):
        r = tr.tail_rotor_sizing(400000.0, 27.0, 8.0, margin_factor=1.0)
        self.assertAlmostEqual(r["tail_rotor_thrust_N"] * 8.0,
                               r["main_rotor_torque_nm"], places=6)

    def test_margin_factor_propagates(self):
        r1 = tr.tail_rotor_sizing(400000.0, 27.0, 8.0, margin_factor=1.0)
        r2 = tr.tail_rotor_sizing(400000.0, 27.0, 8.0, margin_factor=1.25)
        self.assertAlmostEqual(r2["tail_rotor_thrust_N"],
                               1.25 * r1["tail_rotor_thrust_N"], places=9)
        self.assertAlmostEqual(r2["tail_rotor_area_m2"],
                               1.25 * r1["tail_rotor_area_m2"], places=9)

    def test_sizing_valueerror_propagates(self):
        with self.assertRaises(ValueError):
            tr.tail_rotor_sizing(-400000.0, 27.0, 8.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_sizing(400000.0, 0.0, 8.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_sizing(400000.0, 27.0, 0.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_sizing(400000.0, 27.0, 8.0, max_disk_loading=-300.0)
        with self.assertRaises(ValueError):
            tr.tail_rotor_sizing(400000.0, 27.0, 8.0, rho=0.0)

    def test_determinism(self):
        r1 = tr.tail_rotor_sizing(400000.0, 27.0, 8.0, margin_factor=1.15,
                                  rho=0.9, max_disk_loading=350.0)
        r2 = tr.tail_rotor_sizing(400000.0, 27.0, 8.0, margin_factor=1.15,
                                  rho=0.9, max_disk_loading=350.0)
        self.assertEqual(r1, r2)

    def test_torque_balance_identity_margin_one(self):
        q = tr.main_rotor_torque(400000.0, 27.0)
        t = tr.tail_rotor_thrust(q, 8.0)
        self.assertAlmostEqual(t * 8.0, q, places=9)


if __name__ == "__main__":
    unittest.main()
