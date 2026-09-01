#!/usr/bin/env python3
"""Gate 3 contract test: engine sizing.

Exercises scripts/engine_sizing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (sea level static thrust from
the design thrust to weight ratio; ISA density ratio and thrust lapse
with altitude; installed takeoff thrust; cruise and top of climb thrust
margin; SFC to fuel flow; engine weight from the engine thrust to
weight ratio; thrust split across engines; invalid inputs raise
ValueError.

Anchors (verified by running the module):
- sea_level_static_thrust(500000, 0.25) = 125000 N
- isa_density_ratio(0) = 1.0; (11000) = 0.29708; (10000) = 0.33690
- thrust_at_altitude(125000, 11000) = 53446.2 N (m = 0.7)
- thrust_at_altitude(125000, 11000, 1.0) = 37134.5 N (m = 1.0)
- takeoff_thrust(125000) = 122500 N (2 pct installation loss)
- cruise_thrust_required(500000, 18) = 27777.8 N
- thrust_margin(30000, 27777.8) = 1.08
- top_of_climb_margin(125000, 11000, 470000, 18) = 2.0469
- sfc_from_lb_per_lbf_hr(0.5) = 1.4163e-5 kg/(N*s)
- fuel_flow(1.4163e-5, 27777.8) = 0.3934 kg/s
- engine_weight(125000) = 25000 N (ratio 5)
- thrust_per_engine(125000, 2) = 62500 N
- matched_engine_count(125000, 60000) = 3
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine_sizing_logic as es  # noqa: E402


class SeaLevelStaticThrustTest(unittest.TestCase):
    def test_anchor_500000n_at_025(self):
        self.assertAlmostEqual(es.sea_level_static_thrust(500000, 0.25), 125000.0)

    def test_anchor_700000n_at_03(self):
        self.assertAlmostEqual(es.sea_level_static_thrust(700000, 0.3), 210000.0)

    def test_higher_weight_higher_thrust(self):
        heavy = es.sea_level_static_thrust(600000, 0.25)
        light = es.sea_level_static_thrust(500000, 0.25)
        self.assertGreater(heavy, light)

    def test_higher_ratio_higher_thrust(self):
        high = es.sea_level_static_thrust(500000, 0.3)
        low = es.sea_level_static_thrust(500000, 0.25)
        self.assertGreater(high, low)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.sea_level_static_thrust(0, 0.25)
        with self.assertRaises(ValueError):
            es.sea_level_static_thrust(-500000, 0.25)
        with self.assertRaises(ValueError):
            es.sea_level_static_thrust(500000, 0)
        with self.assertRaises(ValueError):
            es.sea_level_static_thrust(500000, -0.25)


class IsaDensityRatioTest(unittest.TestCase):
    def test_anchor_sea_level(self):
        self.assertAlmostEqual(es.isa_density_ratio(0.0), 1.0)

    def test_anchor_tropopause(self):
        self.assertAlmostEqual(es.isa_density_ratio(11000.0), 0.29708, places=4)

    def test_anchor_10000m(self):
        self.assertAlmostEqual(es.isa_density_ratio(10000.0), 0.33690, places=4)

    def test_anchor_5000m(self):
        self.assertAlmostEqual(es.isa_density_ratio(5000.0), 0.60091, places=4)

    def test_density_falls_with_altitude(self):
        high = es.isa_density_ratio(10000.0)
        low = es.isa_density_ratio(2000.0)
        self.assertLess(high, low)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.isa_density_ratio(-100.0)
        with self.assertRaises(ValueError):
            es.isa_density_ratio(11001.0)


class ThrustAtAltitudeTest(unittest.TestCase):
    def test_anchor_11000m_lapse07(self):
        self.assertAlmostEqual(
            es.thrust_at_altitude(125000, 11000.0), 53446.22, places=2
        )

    def test_anchor_11000m_lapse10(self):
        self.assertAlmostEqual(
            es.thrust_at_altitude(125000, 11000.0, 1.0), 37134.46, places=2
        )

    def test_anchor_10000m_lapse07(self):
        self.assertAlmostEqual(
            es.thrust_at_altitude(125000, 10000.0), 58366.48, places=2
        )

    def test_sea_level_returns_full_thrust(self):
        self.assertAlmostEqual(es.thrust_at_altitude(125000, 0.0), 125000.0)

    def test_altitude_reduces_thrust(self):
        high = es.thrust_at_altitude(125000, 11000.0)
        low = es.thrust_at_altitude(125000, 0.0)
        self.assertLess(high, low)

    def test_higher_lapse_exponent_more_lapse(self):
        steep = es.thrust_at_altitude(125000, 11000.0, 1.0)
        mild = es.thrust_at_altitude(125000, 11000.0, 0.7)
        self.assertLess(steep, mild)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.thrust_at_altitude(0, 10000.0)
        with self.assertRaises(ValueError):
            es.thrust_at_altitude(125000, -1.0)
        with self.assertRaises(ValueError):
            es.thrust_at_altitude(125000, 20000.0)
        with self.assertRaises(ValueError):
            es.thrust_at_altitude(125000, 10000.0, 0)


class TakeoffThrustTest(unittest.TestCase):
    def test_anchor_2pct_loss(self):
        self.assertAlmostEqual(es.takeoff_thrust(125000), 122500.0)

    def test_anchor_4pct_loss(self):
        self.assertAlmostEqual(es.takeoff_thrust(125000, 0.04), 120000.0)

    def test_zero_loss_returns_uninstalled(self):
        self.assertAlmostEqual(es.takeoff_thrust(125000, 0.0), 125000.0)

    def test_installed_below_uninstalled(self):
        installed = es.takeoff_thrust(125000, 0.03)
        uninstalled = es.sea_level_static_thrust(500000, 0.25)
        self.assertLess(installed, uninstalled)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.takeoff_thrust(0)
        with self.assertRaises(ValueError):
            es.takeoff_thrust(125000, -0.02)
        with self.assertRaises(ValueError):
            es.takeoff_thrust(125000, 1.0)


class CruiseThrustRequiredTest(unittest.TestCase):
    def test_anchor_500000n_ld18(self):
        self.assertAlmostEqual(
            es.cruise_thrust_required(500000, 18.0), 27777.78, places=2
        )

    def test_anchor_450000n_ld17(self):
        self.assertAlmostEqual(
            es.cruise_thrust_required(450000, 17.0), 26470.59, places=2
        )

    def test_better_ld_lower_thrust(self):
        good = es.cruise_thrust_required(500000, 20.0)
        poor = es.cruise_thrust_required(500000, 15.0)
        self.assertLess(good, poor)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.cruise_thrust_required(0, 18.0)
        with self.assertRaises(ValueError):
            es.cruise_thrust_required(500000, 0)
        with self.assertRaises(ValueError):
            es.cruise_thrust_required(500000, -18.0)


class ThrustMarginTest(unittest.TestCase):
    def test_anchor_above_one(self):
        self.assertAlmostEqual(
            es.thrust_margin(30000, 27777.78), 1.08, places=4
        )

    def test_equal_thrust_margin_one(self):
        self.assertAlmostEqual(es.thrust_margin(27777.78, 27777.78), 1.0, places=4)

    def test_below_one_is_shortfall(self):
        self.assertLess(es.thrust_margin(20000, 27777.78), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.thrust_margin(30000, 0)
        with self.assertRaises(ValueError):
            es.thrust_margin(30000, -1000)


class TopOfClimbTest(unittest.TestCase):
    def test_anchor_125000n_470000n_ld18(self):
        self.assertAlmostEqual(
            es.top_of_climb_margin(125000, 11000.0, 470000, 18.0),
            2.04688,
            places=4,
        )

    def test_anchor_lower_ld_lower_margin(self):
        self.assertAlmostEqual(
            es.top_of_climb_margin(125000, 11000.0, 470000, 15.0),
            1.70573,
            places=4,
        )

    def test_margin_grows_with_sea_level_thrust(self):
        big = es.top_of_climb_margin(125000, 11000.0, 470000, 18.0)
        small = es.top_of_climb_margin(80000, 11000.0, 470000, 18.0)
        self.assertGreater(big, small)

    def test_margin_falls_with_weight(self):
        light = es.top_of_climb_margin(125000, 11000.0, 400000, 18.0)
        heavy = es.top_of_climb_margin(125000, 11000.0, 520000, 18.0)
        self.assertGreater(light, heavy)

    def test_undersized_engine_fails_toc(self):
        margin = es.top_of_climb_margin(60000, 11000.0, 470000, 18.0)
        self.assertLess(margin, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.top_of_climb_margin(0, 11000.0, 470000, 18.0)
        with self.assertRaises(ValueError):
            es.top_of_climb_margin(125000, 12000.0, 470000, 18.0)
        with self.assertRaises(ValueError):
            es.top_of_climb_margin(125000, 11000.0, 0, 18.0)


class SfcAndFuelFlowTest(unittest.TestCase):
    def test_anchor_sfc_05(self):
        self.assertAlmostEqual(
            es.sfc_from_lb_per_lbf_hr(0.5), 1.4163e-5, places=9
        )

    def test_anchor_sfc_06(self):
        self.assertAlmostEqual(
            es.sfc_from_lb_per_lbf_hr(0.6), 1.6995e-5, places=9
        )

    def test_sfc_linear_in_rate(self):
        six = es.sfc_from_lb_per_lbf_hr(0.6)
        three = es.sfc_from_lb_per_lbf_hr(0.3)
        self.assertAlmostEqual(six, 2.0 * three)

    def test_anchor_fuel_flow_cruise(self):
        self.assertAlmostEqual(
            es.fuel_flow(1.4163e-5, 27777.78), 0.39342, places=4
        )

    def test_anchor_fuel_flow_hourly(self):
        flow = es.fuel_flow(es.sfc_from_lb_per_lbf_hr(0.5), 27777.78)
        self.assertAlmostEqual(flow * 3600.0, 1416.27, places=1)

    def test_more_thrust_more_fuel(self):
        high = es.fuel_flow(1.4163e-5, 30000.0)
        low = es.fuel_flow(1.4163e-5, 20000.0)
        self.assertGreater(high, low)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.sfc_from_lb_per_lbf_hr(0)
        with self.assertRaises(ValueError):
            es.sfc_from_lb_per_lbf_hr(-0.5)
        with self.assertRaises(ValueError):
            es.fuel_flow(0, 27777.78)
        with self.assertRaises(ValueError):
            es.fuel_flow(1.4163e-5, 0)


class EngineWeightTest(unittest.TestCase):
    def test_anchor_ratio5(self):
        self.assertAlmostEqual(es.engine_weight(125000), 25000.0)

    def test_anchor_ratio4(self):
        self.assertAlmostEqual(es.engine_weight(125000, 4.0), 31250.0)

    def test_anchor_mass_kg(self):
        self.assertAlmostEqual(es.engine_weight(125000) / 9.80665, 2549.29, places=2)

    def test_lower_ratio_heavier_engine(self):
        heavy = es.engine_weight(125000, 4.0)
        light = es.engine_weight(125000, 6.0)
        self.assertGreater(heavy, light)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.engine_weight(0)
        with self.assertRaises(ValueError):
            es.engine_weight(125000, 0)


class ThrustPerEngineTest(unittest.TestCase):
    def test_anchor_twin(self):
        self.assertAlmostEqual(es.thrust_per_engine(125000, 2), 62500.0)

    def test_anchor_quad(self):
        self.assertAlmostEqual(es.thrust_per_engine(125000, 4), 31250.0)

    def test_more_engines_less_per_engine(self):
        twin = es.thrust_per_engine(125000, 2)
        quad = es.thrust_per_engine(125000, 4)
        self.assertGreater(twin, quad)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.thrust_per_engine(0, 2)
        with self.assertRaises(ValueError):
            es.thrust_per_engine(125000, 0)


class MatchedEngineCountTest(unittest.TestCase):
    def test_anchor_three_engines(self):
        self.assertEqual(es.matched_engine_count(125000, 60000), 3)

    def test_anchor_single_engine(self):
        self.assertEqual(es.matched_engine_count(125000, 125000), 1)

    def test_anchor_five_engines(self):
        self.assertEqual(es.matched_engine_count(125000, 30000), 5)

    def test_exact_division_no_roundup(self):
        self.assertEqual(es.matched_engine_count(120000, 60000), 2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            es.matched_engine_count(0, 60000)
        with self.assertRaises(ValueError):
            es.matched_engine_count(125000, 0)


class EngineSizingScenarioTest(unittest.TestCase):
    def test_twin_transport_sizing_loop(self):
        # 500000 N takeoff gross weight at 0.25 design thrust to weight
        # gives 125000 N total; two engines split 62500 N each; at an
        # engine thrust to weight ratio of 5 each engine weighs
        # 12500 N, about 1274.6 kg.
        total = es.sea_level_static_thrust(500000, 0.25)
        per_engine = es.thrust_per_engine(total, 2)
        engine_wt = es.engine_weight(per_engine)
        self.assertAlmostEqual(total, 125000.0)
        self.assertAlmostEqual(per_engine, 62500.0)
        self.assertAlmostEqual(engine_wt, 12500.0)
        self.assertAlmostEqual(engine_wt / 9.80665, 1274.65, places=2)

    def test_toc_margin_drives_engine_resize(self):
        # At 11000 m the undersized 60000 N engine cannot hold the top
        # of climb; growing the sea level thrust to 125000 N gives a
        # healthy margin above 1.5.
        undersized = es.top_of_climb_margin(60000, 11000.0, 470000, 18.0)
        sized = es.top_of_climb_margin(125000, 11000.0, 470000, 18.0)
        self.assertLess(undersized, 1.0)
        self.assertGreater(sized, 1.5)

    def test_takeoff_and_cruise_fuel_demand(self):
        # Installed takeoff thrust at 2 pct loss, cruise thrust at 18
        # to 1, and the cruise fuel flow at 0.5 lb/(lbf*h) SFC: about
        # 1416 kg per hour at the cruise thrust point.
        takeoff = es.takeoff_thrust(125000, 0.02)
        cruise = es.cruise_thrust_required(500000, 18.0)
        flow = es.fuel_flow(es.sfc_from_lb_per_lbf_hr(0.5), cruise)
        self.assertAlmostEqual(takeoff, 122500.0)
        self.assertAlmostEqual(cruise, 27777.78, places=2)
        self.assertAlmostEqual(flow * 3600.0, 1416.27, places=1)

    def test_catalogue_match_closes_loop(self):
        # A 65000 N catalogue engine covers the 125000 N demand with
        # two units, matching the twin layout.
        self.assertEqual(es.matched_engine_count(125000, 65000), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
