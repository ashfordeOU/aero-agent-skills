#!/usr/bin/env python3
"""Gate 3 contract test: landing performance.

Exercises scripts/landing_performance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (reference approach
speed from the stall speed; flare radius, height, and distance from the
approach speed and load factor; air distance over the 50 foot obstacle;
landing ground roll from the touchdown speed, braking coefficient, lift
and drag ratios, and reverse thrust; certified landing field length per
the FAR 25.125 / CS 25.125 landing distance check; invalid inputs raise
ValueError).

Anchors:
- stall_speed(3910, 1.225, 2.0) = 56.4963 m/s (transport wing loading
  at CL_max 2.0, sea level)
- approach_speed(70.0, 1.3) = 91.0 m/s; (70.0, 1.23) = 86.1 m/s
- touchdown_speed(91.0, 0.95) = 86.45 m/s
- flare_radius(70.0, 1.2) = 2498.3047 m; flare_height(70.0, 3.0, 1.2)
  = 3.4238 m; flare_distance(70.0, 3.0, 1.2) = 130.7512 m
- air_distance(70.0, 3.0, 15.24, 1.2) = 356.2169 m (50 ft obstacle)
- ground_roll_distance(70.0, 3.0) = 816.6667 m
- average_deceleration(0.45, 0.3, 0.05, 0.1) = 0.465 g
- ground_roll_from_forces(70.0, 0.45, 0.3, 0.05, 0.1) = 537.2698 m
- certified_landing_distance(1000.0) = 1670.0 m (1.67 factor)
- required_braking_coefficient(70.0, 600.0, 0.0, 0.05, 0.0) = 0.3664
- stop_time(70.0, 3.0) = 23.3333 s
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import landing_performance_logic as lp  # noqa: E402


class StallSpeedTest(unittest.TestCase):
    def test_anchor_transport_wing_loading(self):
        self.assertAlmostEqual(lp.stall_speed(3910, 1.225, 2.0), 56.4963, places=4)

    def test_anchor_round_wing_loading(self):
        self.assertAlmostEqual(lp.stall_speed(4800, 1.225, 2.4), 57.1429, places=4)

    def test_higher_cl_max_lowers_stall_speed(self):
        high_cl = lp.stall_speed(3910, 1.225, 2.4)
        low_cl = lp.stall_speed(3910, 1.225, 2.0)
        self.assertLess(high_cl, low_cl)

    def test_higher_density_lowers_stall_speed(self):
        sea = lp.stall_speed(3910, 1.225, 2.0)
        high = lp.stall_speed(3910, 1.5, 2.0)
        self.assertLess(high, sea)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.stall_speed(0, 1.225, 2.0)
        with self.assertRaises(ValueError):
            lp.stall_speed(-3910, 1.225, 2.0)
        with self.assertRaises(ValueError):
            lp.stall_speed(3910, 0, 2.0)
        with self.assertRaises(ValueError):
            lp.stall_speed(3910, 1.225, 0)


class ApproachSpeedTest(unittest.TestCase):
    def test_anchor_factor_130(self):
        self.assertAlmostEqual(lp.approach_speed(70.0, 1.3), 91.0)

    def test_anchor_factor_123(self):
        self.assertAlmostEqual(lp.approach_speed(70.0, 1.23), 86.1)

    def test_anchor_from_stall(self):
        vs = lp.stall_speed(3910, 1.225, 2.0)
        self.assertAlmostEqual(lp.approach_speed(vs, 1.3), 73.4452, places=4)

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            lp.approach_speed(70.0, 0.95)

    def test_invalid_stall_speed_raises(self):
        with self.assertRaises(ValueError):
            lp.approach_speed(0, 1.3)
        with self.assertRaises(ValueError):
            lp.approach_speed(-70.0, 1.3)


class TouchdownSpeedTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(lp.touchdown_speed(91.0, 0.95), 86.45)

    def test_touchdown_below_approach(self):
        td = lp.touchdown_speed(91.0)
        self.assertLess(td, 91.0)

    def test_anchor_from_approach(self):
        self.assertAlmostEqual(lp.touchdown_speed(73.445, 0.95), 69.773, places=3)

    def test_invalid_factors_raise(self):
        with self.assertRaises(ValueError):
            lp.touchdown_speed(91.0, 1.05)
        with self.assertRaises(ValueError):
            lp.touchdown_speed(91.0, 0.0)
        with self.assertRaises(ValueError):
            lp.touchdown_speed(-91.0, 0.95)


class FlareGeometryTest(unittest.TestCase):
    def test_radius_anchor(self):
        self.assertAlmostEqual(lp.flare_radius(70.0, 1.2), 2498.3047, places=4)

    def test_radius_anchor_higher_load_factor(self):
        self.assertAlmostEqual(lp.flare_radius(70.0, 1.3), 1665.5365, places=4)

    def test_higher_load_factor_smaller_radius(self):
        gentle = lp.flare_radius(70.0, 1.2)
        firm = lp.flare_radius(70.0, 1.3)
        self.assertLess(firm, gentle)

    def test_height_anchor(self):
        self.assertAlmostEqual(lp.flare_height(70.0, 3.0, 1.2), 3.4238, places=4)

    def test_distance_anchor(self):
        self.assertAlmostEqual(lp.flare_distance(70.0, 3.0, 1.2), 130.7512, places=4)

    def test_steeper_angle_raises_flare_height(self):
        steep = lp.flare_height(70.0, 4.0, 1.2)
        shallow = lp.flare_height(70.0, 2.0, 1.2)
        self.assertGreater(steep, shallow)

    def test_faster_approach_extends_flare_distance(self):
        fast = lp.flare_distance(80.0, 3.0, 1.2)
        slow = lp.flare_distance(70.0, 3.0, 1.2)
        self.assertGreater(fast, slow)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.flare_radius(70.0, 1.0)
        with self.assertRaises(ValueError):
            lp.flare_radius(0.0, 1.2)
        with self.assertRaises(ValueError):
            lp.flare_height(70.0, 0.0, 1.2)
        with self.assertRaises(ValueError):
            lp.flare_distance(70.0, -3.0, 1.2)


class AirDistanceTest(unittest.TestCase):
    def test_anchor_50ft_obstacle(self):
        self.assertAlmostEqual(
            lp.air_distance(70.0, 3.0, 15.24, 1.2), 356.2169, places=4
        )

    def test_anchor_shallower_angle(self):
        self.assertAlmostEqual(
            lp.air_distance(70.0, 2.5, 15.24, 1.2), 403.5666, places=4
        )

    def test_anchor_taller_obstacle(self):
        self.assertAlmostEqual(
            lp.air_distance(70.0, 3.0, 50.0, 1.2), 1019.4772, places=4
        )

    def test_steeper_angle_shortens_air_distance(self):
        steep = lp.air_distance(70.0, 3.5, 15.24, 1.2)
        shallow = lp.air_distance(70.0, 2.5, 15.24, 1.2)
        self.assertLess(steep, shallow)

    def test_air_distance_exceeds_flare_distance(self):
        air = lp.air_distance(70.0, 3.0, 15.24, 1.2)
        s_flare = lp.flare_distance(70.0, 3.0, 1.2)
        self.assertGreater(air, s_flare)

    def test_obstacle_below_flare_height_raises(self):
        with self.assertRaises(ValueError):
            lp.air_distance(70.0, 3.0, 1.0, 1.2)

    def test_invalid_angle_raises(self):
        with self.assertRaises(ValueError):
            lp.air_distance(70.0, 0.0, 15.24, 1.2)
        with self.assertRaises(ValueError):
            lp.air_distance(70.0, 90.0, 15.24, 1.2)


class GroundRollTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(lp.ground_roll_distance(70.0, 3.0), 816.6667, places=4)

    def test_anchor_touchdown_speed(self):
        self.assertAlmostEqual(lp.ground_roll_distance(69.77, 3.0), 811.3088, places=4)

    def test_higher_deceleration_shortens_roll(self):
        hard = lp.ground_roll_distance(70.0, 4.0)
        soft = lp.ground_roll_distance(70.0, 3.0)
        self.assertLess(hard, soft)

    def test_speed_squared_scaling(self):
        double_speed = lp.ground_roll_distance(140.0, 3.0)
        single_speed = lp.ground_roll_distance(70.0, 3.0)
        self.assertAlmostEqual(double_speed, 4.0 * single_speed)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.ground_roll_distance(70.0, 0.0)
        with self.assertRaises(ValueError):
            lp.ground_roll_distance(70.0, -3.0)
        with self.assertRaises(ValueError):
            lp.ground_roll_distance(-70.0, 3.0)


class DecelerationTest(unittest.TestCase):
    def test_anchor_full_force_balance(self):
        self.assertAlmostEqual(
            lp.average_deceleration(0.45, 0.3, 0.05, 0.1), 0.465, places=6
        )

    def test_anchor_mu_only(self):
        self.assertAlmostEqual(lp.average_deceleration(0.3), 0.3)

    def test_lift_unloads_brakes(self):
        loaded = lp.average_deceleration(0.45, 0.0, 0.05, 0.0)
        unloaded = lp.average_deceleration(0.45, 0.3, 0.05, 0.0)
        self.assertLess(unloaded, loaded)

    def test_reverse_thrust_adds_deceleration(self):
        plain = lp.average_deceleration(0.45, 0.0, 0.05, 0.0)
        reversed_ = lp.average_deceleration(0.45, 0.0, 0.05, 0.1)
        self.assertAlmostEqual(reversed_, plain + 0.1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.average_deceleration(-0.3)
        with self.assertRaises(ValueError):
            lp.average_deceleration(0.45, lift_to_weight=-0.1)
        with self.assertRaises(ValueError):
            lp.average_deceleration(0.45, drag_to_weight=-0.05)
        with self.assertRaises(ValueError):
            lp.average_deceleration(0.45, reverse_thrust_to_weight=-0.1)


class ForcesGroundRollTest(unittest.TestCase):
    def test_anchor_full_force_balance(self):
        self.assertAlmostEqual(
            lp.ground_roll_from_forces(70.0, 0.45, 0.3, 0.05, 0.1),
            537.2698,
            places=4,
        )

    def test_anchor_mu_only(self):
        self.assertAlmostEqual(lp.ground_roll_from_forces(70.0, 0.45), 555.1788, places=4)

    def test_reverse_thrust_shortens_roll(self):
        plain = lp.ground_roll_from_forces(70.0, 0.45, 0.0, 0.05, 0.0)
        reversed_ = lp.ground_roll_from_forces(70.0, 0.45, 0.0, 0.05, 0.1)
        self.assertLess(reversed_, plain)

    def test_lift_lengthens_roll(self):
        loaded = lp.ground_roll_from_forces(70.0, 0.45, 0.0, 0.05, 0.0)
        unloaded = lp.ground_roll_from_forces(70.0, 0.45, 0.3, 0.05, 0.0)
        self.assertGreater(unloaded, loaded)

    def test_braking_only_model_matches_simple_roll(self):
        simple = lp.ground_roll_distance(70.0, 0.3 * lp.G0)
        forced = lp.ground_roll_from_forces(70.0, 0.3)
        self.assertAlmostEqual(simple, forced)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.ground_roll_from_forces(70.0, -0.3)
        with self.assertRaises(ValueError):
            lp.ground_roll_from_forces(70.0, 0.45, reverse_thrust_to_weight=-0.1)


class LandingDistanceTest(unittest.TestCase):
    def test_total_landing_distance_sum(self):
        self.assertAlmostEqual(lp.landing_distance(356.24, 816.67), 1172.91, places=2)

    def test_certified_factor_167_anchor(self):
        self.assertAlmostEqual(lp.certified_landing_distance(1000.0), 1670.0)

    def test_certified_factor_143(self):
        self.assertAlmostEqual(lp.certified_landing_distance(1000.0, 1.43), 1430.0)

    def test_certified_exceeds_actual(self):
        actual = lp.landing_distance(356.2169, 816.6667)
        certified = lp.certified_landing_distance(actual)
        self.assertGreater(certified, actual)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.landing_distance(-1.0, 100.0)
        with self.assertRaises(ValueError):
            lp.landing_distance(100.0, -1.0)
        with self.assertRaises(ValueError):
            lp.certified_landing_distance(1000.0, 0.9)
        with self.assertRaises(ValueError):
            lp.certified_landing_distance(-1000.0)


class RequiredMuTest(unittest.TestCase):
    def test_anchor_with_drag(self):
        self.assertAlmostEqual(
            lp.required_braking_coefficient(70.0, 600.0, 0.0, 0.05, 0.0),
            0.3664,
            places=4,
        )

    def test_anchor_with_lift(self):
        self.assertAlmostEqual(
            lp.required_braking_coefficient(70.0, 600.0, 0.3, 0.05, 0.0),
            0.5234,
            places=4,
        )

    def test_reverse_thrust_cuts_required_mu(self):
        plain = lp.required_braking_coefficient(70.0, 600.0, 0.0, 0.05, 0.0)
        reversed_ = lp.required_braking_coefficient(70.0, 600.0, 0.0, 0.05, 0.1)
        self.assertAlmostEqual(reversed_, plain - 0.1, places=6)

    def test_roundtrip_with_ground_roll(self):
        s = lp.ground_roll_from_forces(70.0, 0.45)
        mu = lp.required_braking_coefficient(70.0, s, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(mu, 0.45, places=6)

    def test_longer_target_roll_needs_less_mu(self):
        short = lp.required_braking_coefficient(70.0, 500.0, 0.0, 0.0, 0.0)
        long = lp.required_braking_coefficient(70.0, 800.0, 0.0, 0.0, 0.0)
        self.assertLess(long, short)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.required_braking_coefficient(70.0, 0.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            lp.required_braking_coefficient(70.0, 600.0, 1.0, 0.05, 0.0)
        with self.assertRaises(ValueError):
            lp.required_braking_coefficient(70.0, 600.0, 0.0, -0.05, 0.0)
        with self.assertRaises(ValueError):
            lp.required_braking_coefficient(70.0, 600.0, 0.0, 1.0, 0.0)


class StopTimeTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(lp.stop_time(70.0, 3.0), 23.3333, places=4)

    def test_higher_deceleration_shortens_time(self):
        hard = lp.stop_time(70.0, 4.0)
        soft = lp.stop_time(70.0, 3.0)
        self.assertLess(hard, soft)

    def test_linear_in_speed(self):
        fast = lp.stop_time(140.0, 3.0)
        slow = lp.stop_time(70.0, 3.0)
        self.assertAlmostEqual(fast, 2.0 * slow)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lp.stop_time(70.0, 0.0)
        with self.assertRaises(ValueError):
            lp.stop_time(-70.0, 3.0)


class LandingScenarioTest(unittest.TestCase):
    def test_transport_landing_over_50ft(self):
        # Transport airplane, W/S = 3910 N/m^2, CL_max = 2.0 at sea
        # level. Approach at 1.3 V_s on a 3 degree glideslope, flare at
        # n = 1.2, touchdown at 0.95 V_app, then brake at 0.45 g with
        # drag ratio 0.05. Air distance plus ground roll, then the 1.67
        # certified field length.
        vs = lp.stall_speed(3910, 1.225, 2.0)
        v_app = lp.approach_speed(vs, 1.3)
        v_td = lp.touchdown_speed(v_app, 0.95)
        air = lp.air_distance(v_app, 3.0, 15.24, 1.2)
        s_g = lp.ground_roll_from_forces(v_td, 0.45, 0.0, 0.05, 0.0)
        total = lp.landing_distance(air, s_g)
        certified = lp.certified_landing_distance(total)
        self.assertAlmostEqual(v_app, 73.4452, places=4)
        self.assertAlmostEqual(v_td, 69.7730, places=4)
        self.assertGreater(total, 800.0)
        self.assertLess(total, 950.0)
        self.assertGreater(certified, total)

    def test_contaminated_runway_requires_more_distance(self):
        # Same touchdown speed, dry braking mu 0.5 versus wet mu 0.3.
        dry = lp.ground_roll_from_forces(70.0, 0.5)
        wet = lp.ground_roll_from_forces(70.0, 0.3)
        self.assertLess(dry, wet)

    def test_reverse_thrust_recovers_field_length(self):
        # A short runway: reverse thrust at 0.15 of weight with mu 0.4
        # must stop the airplane in less distance than mu 0.4 alone.
        plain = lp.ground_roll_from_forces(70.0, 0.4, 0.0, 0.05, 0.0)
        assisted = lp.ground_roll_from_forces(70.0, 0.4, 0.0, 0.05, 0.15)
        self.assertLess(assisted, plain)
        self.assertLess(assisted, 500.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
