#!/usr/bin/env python3
"""Gate 3 contract test: bypass-ratio-trade logic (stdlib unittest).

Exercises scripts/bypass_ratio_trade_logic.py offline with the
stdlib unittest runner only. Covers happy path, the BPR=0 turbojet
boundary, invalid-input raises, and hand-computed physically
meaningful values (mdot_total=100 kg/s, BPR=8, Vj_core=600 m/s,
Vj_fan=300 m/s, V0=250 m/s, f=0.02).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bypass_ratio_trade_logic as brt


class ThrustSplitTest(unittest.TestCase):
    def test_hand_computed_split(self):
        # mdot_core = 100/9, mdot_fan = 800/9 kg/s
        # F_core = (100/9)*350, F_fan = (800/9)*50, F_total = 75000/9 N
        split = brt.thrust_split(8.0, 100.0, 600.0, 300.0, 250.0)
        self.assertAlmostEqual(split["mdot_core"], 100.0 / 9.0, delta=1e-9)
        self.assertAlmostEqual(split["mdot_fan"], 800.0 / 9.0, delta=1e-9)
        self.assertAlmostEqual(split["F_core"], 35000.0 / 9.0, delta=1e-9)
        self.assertAlmostEqual(split["F_fan"], 40000.0 / 9.0, delta=1e-9)
        self.assertAlmostEqual(split["F_total"], 75000.0 / 9.0, delta=1e-9)

    def test_turbojet_limit_bpr_zero(self):
        # BPR = 0 sends all flow through the core: a turbojet limit.
        split = brt.thrust_split(0.0, 100.0, 600.0, 300.0, 250.0)
        self.assertAlmostEqual(split["mdot_fan"], 0.0, delta=1e-9)
        self.assertAlmostEqual(split["F_fan"], 0.0, delta=1e-9)
        self.assertAlmostEqual(split["F_total"], 100.0 * 350.0, delta=1e-9)


class SpecificThrustTest(unittest.TestCase):
    def test_hand_computed(self):
        # F_total = 75000/9 N over mdot_total = 100 kg/s -> 750/9 m/s
        self.assertAlmostEqual(
            brt.specific_thrust(75000.0 / 9.0, 100.0), 750.0 / 9.0, delta=1e-9
        )


class TsfcTest(unittest.TestCase):
    def test_hand_computed(self):
        # f = 0.02, mdot_core = 100/9 kg/s -> mdot_fuel = 2/9 kg/s
        # F_total = 75000/9 N -> tsfc = 1e6*(2/9)/(75000/9) g/(kN*s)
        self.assertAlmostEqual(
            brt.tsfc(8.0, 100.0, 600.0, 300.0, 250.0, 0.02),
            2000000.0 / 75000.0,
            delta=1e-6,
        )

    def test_trend_monotone_decrease(self):
        # Fixed core conditions: TSFC falls as BPR rises.
        trend = brt.bpr_trend([2.0, 4.0, 8.0], 100.0, 600.0, 300.0, 250.0, 0.02)
        self.assertEqual(len(trend), 3)
        self.assertLess(trend[2]["tsfc"], trend[1]["tsfc"])
        self.assertLess(trend[1]["tsfc"], trend[0]["tsfc"])
        self.assertGreater(trend[0]["specific_thrust"], trend[2]["specific_thrust"])


class PropulsiveEfficiencyTest(unittest.TestCase):
    def test_values(self):
        # eta_p = 2/(1 + vj/v0); unity when vj = v0.
        self.assertAlmostEqual(
            brt.propulsive_efficiency(300.0, 250.0),
            2.0 / (1.0 + 300.0 / 250.0),
            delta=1e-9,
        )
        self.assertAlmostEqual(
            brt.propulsive_efficiency(250.0, 250.0), 1.0, delta=1e-9
        )
        self.assertLess(brt.propulsive_efficiency(600.0, 250.0), 1.0)


class FanPressureRatioNoteTest(unittest.TestCase):
    def test_verdicts(self):
        self.assertIn("low fan jet velocity", brt.fan_pressure_ratio_note(1.2))
        self.assertIn("moderate fan pressure ratio", brt.fan_pressure_ratio_note(1.45))
        self.assertIn("high fan pressure ratio", brt.fan_pressure_ratio_note(1.8))


class InvalidInputTest(unittest.TestCase):
    def test_raises(self):
        with self.assertRaises(ValueError):
            brt.thrust_split(-1.0, 100.0, 600.0, 300.0, 250.0)  # negative bpr
        with self.assertRaises(ValueError):
            brt.thrust_split(8.0, 0.0, 600.0, 300.0, 250.0)  # zero mass flow
        with self.assertRaises(ValueError):
            brt.thrust_split(8.0, 100.0, 0.0, 300.0, 250.0)  # zero core jet
        with self.assertRaises(ValueError):
            brt.thrust_split(8.0, 100.0, 200.0, 300.0, 250.0)  # core slower than flight
        with self.assertRaises(ValueError):
            brt.thrust_split(8.0, 100.0, 600.0, 200.0, 250.0)  # fan slower than flight
        with self.assertRaises(ValueError):
            brt.specific_thrust(100.0, 0.0)
        with self.assertRaises(ValueError):
            brt.tsfc(8.0, 100.0, 600.0, 300.0, 250.0, 0.0)  # f = 0
        with self.assertRaises(ValueError):
            brt.tsfc(8.0, 100.0, 600.0, 300.0, 250.0, 1.0)  # f = 1
        with self.assertRaises(ValueError):
            brt.propulsive_efficiency(0.0, 250.0)
        with self.assertRaises(ValueError):
            brt.bpr_trend([], 100.0, 600.0, 300.0, 250.0, 0.02)  # empty sweep
        with self.assertRaises(ValueError):
            brt.fan_pressure_ratio_note(1.0)  # not a working fan


if __name__ == "__main__":
    unittest.main()
