#!/usr/bin/env python3
"""Gate 3 contract test: landing gear sizing logic.

Exercises scripts/landing_gear_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - static load per strut,
nose/main gear load share from CG and wheelbase, shock stroke from
sink speed and load factor, tire rating margin, combined verdict,
and ValueError on invalid inputs (non-positive weight, no main
struts, non-positive wheelbase, CG aft of wheelbase, negative sink
speed, non-positive load factor, non-positive tire rating).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import landing_gear_logic as lg  # noqa: E402


class StaticLoadPerStrutTest(unittest.TestCase):
    def test_known_two_main_struts(self):
        self.assertEqual(lg.static_load_per_strut(25000.0, 2, 0), 12500.0)

    def test_nose_strut_shares_load(self):
        self.assertEqual(lg.static_load_per_strut(30000.0, 2, 1), 10000.0)

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            lg.static_load_per_strut(0.0, 2, 0)
        with self.assertRaises(ValueError):
            lg.static_load_per_strut(-1000.0, 2, 0)

    def test_no_main_struts_raises(self):
        with self.assertRaises(ValueError):
            lg.static_load_per_strut(25000.0, 0, 0)
        with self.assertRaises(ValueError):
            lg.static_load_per_strut(25000.0, -1, 0)

    def test_negative_nose_strut_raises(self):
        with self.assertRaises(ValueError):
            lg.static_load_per_strut(25000.0, 2, -1)


class MainGearLoadShareTest(unittest.TestCase):
    def test_known_share(self):
        share = lg.main_gear_load_share(25000.0, 0.5, 6.0)
        self.assertAlmostEqual(share["nose_load"], 2083.33, places=2)
        self.assertAlmostEqual(share["main_load"], 22916.67, places=2)

    def test_cg_at_main_gear(self):
        share = lg.main_gear_load_share(25000.0, 0.0, 6.0)
        self.assertAlmostEqual(share["nose_load"], 0.0)
        self.assertAlmostEqual(share["main_load"], 25000.0)

    def test_cg_at_wheelbase(self):
        share = lg.main_gear_load_share(25000.0, 6.0, 6.0)
        self.assertAlmostEqual(share["nose_load"], 25000.0)
        self.assertAlmostEqual(share["main_load"], 0.0)

    def test_zero_wheelbase_raises(self):
        with self.assertRaises(ValueError):
            lg.main_gear_load_share(25000.0, 0.5, 0.0)

    def test_cg_aft_of_wheelbase_raises(self):
        with self.assertRaises(ValueError):
            lg.main_gear_load_share(25000.0, 6.5, 6.0)

    def test_negative_cg_raises(self):
        with self.assertRaises(ValueError):
            lg.main_gear_load_share(25000.0, -0.5, 6.0)


class RequiredShockStrokeTest(unittest.TestCase):
    def test_known_transport_case(self):
        self.assertAlmostEqual(
            lg.required_shock_stroke(3.05, 1.5), 0.3162, places=4
        )

    def test_zero_sink_speed(self):
        self.assertAlmostEqual(lg.required_shock_stroke(0.0, 1.5), 0.0)

    def test_negative_sink_speed_raises(self):
        with self.assertRaises(ValueError):
            lg.required_shock_stroke(-1.0, 1.5)

    def test_nonpositive_load_factor_raises(self):
        with self.assertRaises(ValueError):
            lg.required_shock_stroke(3.05, 0.0)
        with self.assertRaises(ValueError):
            lg.required_shock_stroke(3.05, -1.0)


class TireRatingMarginTest(unittest.TestCase):
    def test_known_margin(self):
        self.assertAlmostEqual(
            lg.tire_rating_margin(12500.0, 18000.0), 0.6944, places=4
        )

    def test_rating_exactly_covers_load(self):
        self.assertAlmostEqual(lg.tire_rating_margin(12500.0, 12500.0), 1.0)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            lg.tire_rating_margin(0.0, 18000.0)
        with self.assertRaises(ValueError):
            lg.tire_rating_margin(12500.0, 0.0)
        with self.assertRaises(ValueError):
            lg.tire_rating_margin(12500.0, -1000.0)


class LandingGearVerdictTest(unittest.TestCase):
    def test_gear_sized(self):
        verdict = lg.landing_gear_verdict(12500.0, 18000.0, 3.05, 1.5)
        self.assertAlmostEqual(verdict["tire_margin"], 0.6944, places=4)
        self.assertTrue(verdict["tire_ok"])
        self.assertEqual(verdict["stroke_m"], 0.3162)
        self.assertEqual(verdict["verdict"], "gear sized")
        self.assertEqual(verdict["static_load"], 12500.0)

    def test_tire_overloaded(self):
        verdict = lg.landing_gear_verdict(15000.0, 12000.0, 3.05, 1.5)
        self.assertAlmostEqual(verdict["tire_margin"], 1.25, places=4)
        self.assertFalse(verdict["tire_ok"])
        self.assertEqual(verdict["verdict"], "tire overloaded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
