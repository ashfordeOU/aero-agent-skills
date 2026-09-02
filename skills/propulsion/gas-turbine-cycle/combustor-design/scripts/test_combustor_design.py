#!/usr/bin/env python3
"""Gate 3 contract test for combustor_design_logic.py (stdlib unittest only).

Run directly:
    python3 scripts/test_combustor_design.py
No network, no third-party imports. Asserts the worked anchors of the
combustor design block: stoichiometric and operating fuel-air ratio,
equivalence ratio, combustion efficiency, heat release, temperature rise
across the combustor, and the adiabatic flame temperature estimate, plus
trend properties and non-physical input rejection.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import combustor_design_logic as cdl

# Kerosene-class fuel anchors (c = 0.86, h = 0.14, LHV = 43.2 MJ/kg).
C = 0.86
H = 0.14
LHV = 43.2e6
MF = 2.0      # kg/s fuel flow
MA = 100.0    # kg/s air flow
CP_AIR = 1150.0
CP_PROD = 1300.0
ETA = 0.99


class StoichiometricFarTest(unittest.TestCase):
    def test_kerosene_anchor(self):
        self.assertAlmostEqual(cdl.stoichiometric_far(C, H), 0.0680, places=4)

    def test_methane_anchor(self):
        # CH4: c = 12/16 = 0.75, h = 4/16 = 0.25 -> 0.232 / (2.6667*0.75 + 8*0.25)
        self.assertAlmostEqual(cdl.stoichiometric_far(0.75, 0.25), 0.0580, places=4)

    def test_more_carbon_means_higher_far_st(self):
        # Carbon needs less oxygen per kg (32/12) than hydrogen (8), so a
        # carbon-rich fuel has a HIGHER stoichiometric fuel-air ratio.
        lean_h2 = cdl.stoichiometric_far(0.88, 0.12)   # carbon-rich
        rich_h2 = cdl.stoichiometric_far(0.82, 0.18)   # hydrogen-rich
        self.assertGreater(lean_h2, rich_h2)

    def test_rejects_non_physical_composition(self):
        with self.assertRaises(ValueError):
            cdl.stoichiometric_far(0.86, 0.20)  # c + h = 1.06
        with self.assertRaises(ValueError):
            cdl.stoichiometric_far(-0.1, 1.1)
        with self.assertRaises(ValueError):
            cdl.stoichiometric_far(0.86, 0.0)


class OperatingFarTest(unittest.TestCase):
    def test_operating_far_anchor(self):
        self.assertAlmostEqual(cdl.operating_far(MF, MA), 0.0200, places=6)

    def test_operating_far_scales_with_fuel_flow(self):
        self.assertGreater(cdl.operating_far(3.0, MA), cdl.operating_far(MF, MA))

    def test_rejects_non_positive_flows(self):
        with self.assertRaises(ValueError):
            cdl.operating_far(0.0, MA)
        with self.assertRaises(ValueError):
            cdl.operating_far(MF, -5.0)


class EquivalenceRatioTest(unittest.TestCase):
    def test_equivalence_ratio_anchor(self):
        self.assertAlmostEqual(
            cdl.equivalence_ratio(0.0200, 0.0680), 0.2941, places=3)

    def test_lean_and_rich_verdict(self):
        self.assertLess(cdl.equivalence_ratio(0.03, 0.0680), 1.0)
        self.assertGreater(cdl.equivalence_ratio(0.08, 0.0680), 1.0)
        self.assertAlmostEqual(cdl.equivalence_ratio(0.0680, 0.0680), 1.0, places=9)

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            cdl.equivalence_ratio(0.0, 0.0680)
        with self.assertRaises(ValueError):
            cdl.equivalence_ratio(0.02, -1.0)


class CombustionEfficiencyTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(
            cdl.combustion_efficiency(706.563, 713.7), 0.99, places=6)

    def test_complete_combustion_is_one(self):
        self.assertEqual(cdl.combustion_efficiency(713.7, 713.7), 1.0)

    def test_rejects_actual_above_ideal(self):
        with self.assertRaises(ValueError):
            cdl.combustion_efficiency(750.0, 713.7)
        with self.assertRaises(ValueError):
            cdl.combustion_efficiency(0.0, 713.7)


class HeatReleaseTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(
            cdl.heat_release(MF, LHV, ETA), 85.536e6, places=0)

    def test_full_efficiency_recovers_mf_lhv(self):
        self.assertEqual(cdl.heat_release(MF, LHV, 1.0), MF * LHV)

    def test_more_fuel_more_heat(self):
        self.assertGreater(cdl.heat_release(3.0, LHV, ETA),
                           cdl.heat_release(MF, LHV, ETA))

    def test_rejects_bad_efficiency(self):
        with self.assertRaises(ValueError):
            cdl.heat_release(MF, LHV, 1.5)
        with self.assertRaises(ValueError):
            cdl.heat_release(MF, LHV, 0.0)


class TemperatureRiseTest(unittest.TestCase):
    def test_anchor(self):
        q = cdl.heat_release(MF, LHV, ETA)
        self.assertAlmostEqual(
            cdl.temperature_rise(q, MA, CP_AIR), 743.79, places=2)

    def test_more_air_means_smaller_rise(self):
        q = cdl.heat_release(MF, LHV, ETA)
        self.assertGreater(cdl.temperature_rise(q, MA, CP_AIR),
                           cdl.temperature_rise(q, MA * 2.0, CP_AIR))

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            cdl.temperature_rise(0.0, MA, CP_AIR)
        with self.assertRaises(ValueError):
            cdl.temperature_rise(1e6, MA, 0.0)


class AdiabaticFlameTemperatureTest(unittest.TestCase):
    def test_lean_anchor(self):
        far_op = cdl.operating_far(MF, MA)
        self.assertAlmostEqual(
            cdl.adiabatic_flame_temperature(700.0, far_op, LHV, ETA, CP_PROD),
            1345.1, places=1)

    def test_stoichiometric_anchor(self):
        far_st = cdl.stoichiometric_far(C, H)
        self.assertAlmostEqual(
            cdl.adiabatic_flame_temperature(700.0, far_st, LHV, ETA, CP_PROD),
            2793.8, places=1)

    def test_stoichiometric_hotter_than_lean(self):
        t_lean = cdl.adiabatic_flame_temperature(
            700.0, cdl.operating_far(MF, MA), LHV, ETA, CP_PROD)
        t_st = cdl.adiabatic_flame_temperature(
            700.0, cdl.stoichiometric_far(C, H), LHV, ETA, CP_PROD)
        self.assertGreater(t_st, t_lean)

    def test_higher_inlet_raises_flame_temperature(self):
        low = cdl.adiabatic_flame_temperature(500.0, 0.02, LHV, ETA, CP_PROD)
        high = cdl.adiabatic_flame_temperature(800.0, 0.02, LHV, ETA, CP_PROD)
        self.assertGreater(high, low)
        self.assertAlmostEqual(high - low, 300.0, places=6)

    def test_rejects_non_physical_inputs(self):
        with self.assertRaises(ValueError):
            cdl.adiabatic_flame_temperature(-300.0, 0.02, LHV, ETA, CP_PROD)
        with self.assertRaises(ValueError):
            cdl.adiabatic_flame_temperature(700.0, 0.02, LHV, 1.2, CP_PROD)


class EndToEndCombustorBlockTest(unittest.TestCase):
    def test_full_design_point_chain(self):
        """Kerosene burner at the design point: lean burn, ~744 K rise."""
        far_st = cdl.stoichiometric_far(C, H)
        far_op = cdl.operating_far(MF, MA)
        phi = cdl.equivalence_ratio(far_op, far_st)
        eta = cdl.combustion_efficiency(706.563, 713.7)
        q = cdl.heat_release(MF, LHV, eta)
        dt = cdl.temperature_rise(q, MA, CP_AIR)
        t_exit = 700.0 + dt
        self.assertLess(phi, 1.0)                 # lean burn
        self.assertAlmostEqual(dt, 743.79, places=2)
        self.assertGreater(t_exit, 1400.0)        # ~1444 K combustor exit
        self.assertLess(t_exit, 1500.0)


if __name__ == "__main__":
    unittest.main()
