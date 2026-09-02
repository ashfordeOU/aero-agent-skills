#!/usr/bin/env python3
"""Gate 3 contract test: low-thrust spiral transfer (Edelbaum).

Exercises scripts/low_thrust_spiral_logic.py (stdlib unittest,
offline). Contract: circular orbit velocity, the Edelbaum delta-v for
a continuous-thrust transfer with a total inclination change, the
no-plane-change spiral case, rocket-equation propellant mass and
transfer time for constant thrust and specific impulse, the impulsive
Hohmann comparison budget, and the packed transfer summary; invalid
inputs raise ValueError.

Anchors (LEO at 6878 km radius to GEO at 42164 km radius, mu =
3.986004418e14 m^3/s^2, di = 28.5 deg, m0 = 2000 kg, T = 0.5 N, I_sp =
3000 s):
- circular_velocity(6878e3) = 7612.68 m/s (low earth orbit)
- circular_velocity(42164e3) = 3074.67 m/s (geostationary orbit)
- edelbaum_delta_v(6878e3, 42164e3, 28.5) = 5845.58 m/s
- edelbaum_delta_v with di = 0 = 4538.02 m/s = |v_i - v_f|
- spiral_no_plane_change_delta_v = 4538.02 m/s
- hohmann_delta_v = 3816.09 m/s (impulsive comparison, no plane change)
- m_prop = 360.40 kg, mf = 1639.60 kg, t_transfer = 21205870.71 s
  (245.44 days)
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import low_thrust_spiral_logic as lt  # noqa: E402

R1 = 6878.0e3   # low earth orbit at 500 km altitude, m
R2 = 42164.0e3  # geostationary orbit, m
R_MOON = 384400.0e3  # lunar distance, m

# Worked-example thruster and bus
M0 = 2000.0   # initial mass, kg
THRUST = 0.5  # constant thrust, N
ISP = 3000.0  # specific impulse, s
DI = 28.5     # total inclination change, deg
C_EXH = lt.G0 * ISP  # exhaust velocity, m/s


class CircularVelocityTest(unittest.TestCase):
    def test_anchor_leo(self):
        self.assertAlmostEqual(lt.circular_velocity(R1), 7612.684, places=3)

    def test_anchor_geo(self):
        self.assertAlmostEqual(lt.circular_velocity(R2), 3074.666, places=3)

    def test_decreases_with_radius(self):
        self.assertGreater(lt.circular_velocity(R1), lt.circular_velocity(R2))

    def test_scale_with_mu(self):
        v = lt.circular_velocity(R1, mu=4 * lt.MU_EARTH)
        self.assertAlmostEqual(v, 2 * lt.circular_velocity(R1))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lt.circular_velocity(0)
        with self.assertRaises(ValueError):
            lt.circular_velocity(-R1)
        with self.assertRaises(ValueError):
            lt.circular_velocity(R1, mu=0)


class EdelbaumDeltaVTest(unittest.TestCase):
    def test_anchor_leo_geo_with_plane_change(self):
        self.assertAlmostEqual(lt.edelbaum_delta_v(R1, R2, DI), 5845.584, places=3)

    def test_zero_plane_change_matches_spiral_helper(self):
        # Edelbaum with di = 0 reduces to the pure spiral budget,
        # which is |v_i - v_f| (both paths stay consistent).
        dv0 = lt.edelbaum_delta_v(R1, R2, 0.0)
        self.assertAlmostEqual(dv0, lt.spiral_no_plane_change_delta_v(R1, R2), places=6)
        self.assertAlmostEqual(
            dv0, abs(lt.circular_velocity(R1) - lt.circular_velocity(R2)), places=6
        )

    def test_anchor_zero_plane_change(self):
        self.assertAlmostEqual(lt.edelbaum_delta_v(R1, R2, 0.0), 4538.018, places=3)

    def test_delta_v_grows_with_inclination_change(self):
        self.assertGreater(lt.edelbaum_delta_v(R1, R2, 90.0), lt.edelbaum_delta_v(R1, R2, DI))

    def test_plane_change_only_equal_radii(self):
        # Same radius both ends: the budget is a pure inclination
        # change; at di = 0 the same-radius budget is exactly zero.
        self.assertAlmostEqual(lt.edelbaum_delta_v(R1, R1, DI), 5797.968, places=3)
        self.assertAlmostEqual(lt.edelbaum_delta_v(R1, R1, 0.0), 0.0, places=6)

    def test_inclination_boundaries_accepted(self):
        lt.edelbaum_delta_v(R1, R2, 0.0)
        lt.edelbaum_delta_v(R1, R2, 180.0)

    def test_inclination_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            lt.edelbaum_delta_v(R1, R2, -1.0)
        with self.assertRaises(ValueError):
            lt.edelbaum_delta_v(R1, R2, 180.5)

    def test_invalid_radii_raise(self):
        with self.assertRaises(ValueError):
            lt.edelbaum_delta_v(0, R2, DI)
        with self.assertRaises(ValueError):
            lt.edelbaum_delta_v(R1, -R2, DI)

    def test_invalid_mu_raises(self):
        with self.assertRaises(ValueError):
            lt.edelbaum_delta_v(R1, R2, DI, mu=0)


class SpiralNoPlaneChangeTest(unittest.TestCase):
    def test_anchor_leo_geo(self):
        self.assertAlmostEqual(lt.spiral_no_plane_change_delta_v(R1, R2), 4538.018, places=3)

    def test_zero_when_radii_equal(self):
        self.assertAlmostEqual(lt.spiral_no_plane_change_delta_v(R1, R1), 0.0, places=6)

    def test_matches_velocity_difference(self):
        self.assertAlmostEqual(
            lt.spiral_no_plane_change_delta_v(R1, R2),
            abs(lt.circular_velocity(R1) - lt.circular_velocity(R2)),
            places=6,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lt.spiral_no_plane_change_delta_v(0, R2)
        with self.assertRaises(ValueError):
            lt.spiral_no_plane_change_delta_v(R1, R2, mu=-1.0)


class TransferMassTimeTest(unittest.TestCase):
    def test_anchor_propellant_mass(self):
        dv = lt.edelbaum_delta_v(R1, R2, DI)
        m_prop, m_final, _ = lt.transfer_mass_and_time(dv, M0, THRUST, ISP)
        self.assertAlmostEqual(m_prop, 360.400, places=3)

    def test_anchor_final_mass(self):
        dv = lt.edelbaum_delta_v(R1, R2, DI)
        _, m_final, _ = lt.transfer_mass_and_time(dv, M0, THRUST, ISP)
        self.assertAlmostEqual(m_final, 1639.600, places=3)

    def test_anchor_transfer_time(self):
        dv = lt.edelbaum_delta_v(R1, R2, DI)
        _, _, t = lt.transfer_mass_and_time(dv, M0, THRUST, ISP)
        self.assertAlmostEqual(t, 21205870.713, places=3)

    def test_rocket_equation_round_trip(self):
        dv = lt.edelbaum_delta_v(R1, R2, DI)
        m_prop, m_final, _ = lt.transfer_mass_and_time(dv, M0, THRUST, ISP)
        self.assertAlmostEqual(M0, m_prop + m_final, places=6)
        self.assertAlmostEqual(m_final, M0 * math.exp(-dv / C_EXH), places=6)

    def test_time_equals_propellant_exhaust_ratio(self):
        dv = lt.edelbaum_delta_v(R1, R2, DI)
        m_prop, _, t = lt.transfer_mass_and_time(dv, M0, THRUST, ISP)
        self.assertAlmostEqual(t, m_prop * C_EXH / THRUST, places=6)

    def test_zero_delta_v_costs_nothing(self):
        m_prop, m_final, t = lt.transfer_mass_and_time(0.0, M0, THRUST, ISP)
        self.assertAlmostEqual(m_prop, 0.0, places=6)
        self.assertAlmostEqual(m_final, M0, places=6)
        self.assertAlmostEqual(t, 0.0, places=6)

    def test_more_delta_v_needs_more_propellant(self):
        dv1 = lt.edelbaum_delta_v(R1, R2, 0.0)
        dv2 = lt.edelbaum_delta_v(R1, R2, DI)
        m1 = lt.transfer_mass_and_time(dv1, M0, THRUST, ISP)[0]
        m2 = lt.transfer_mass_and_time(dv2, M0, THRUST, ISP)[0]
        self.assertGreater(m2, m1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lt.transfer_mass_and_time(-1.0, M0, THRUST, ISP)
        with self.assertRaises(ValueError):
            lt.transfer_mass_and_time(1000.0, 0, THRUST, ISP)
        with self.assertRaises(ValueError):
            lt.transfer_mass_and_time(1000.0, M0, 0.0, ISP)
        with self.assertRaises(ValueError):
            lt.transfer_mass_and_time(1000.0, M0, THRUST, -3000.0)


class HohmannComparisonTest(unittest.TestCase):
    def test_anchor_leo_geo(self):
        self.assertAlmostEqual(lt.hohmann_delta_v(R1, R2), 3816.093, places=3)

    def test_spiral_costs_more_than_impulsive(self):
        # Continuous thrust on a spiral pays more than the impulsive
        # Hohmann budget for the same coplanar end orbits.
        self.assertGreater(
            lt.spiral_no_plane_change_delta_v(R1, R2), lt.hohmann_delta_v(R1, R2)
        )

    def test_symmetric_in_radii(self):
        self.assertAlmostEqual(lt.hohmann_delta_v(R1, R2), lt.hohmann_delta_v(R2, R1), places=6)

    def test_farther_target_needs_more_delta_v(self):
        self.assertGreater(lt.hohmann_delta_v(R1, R_MOON), lt.hohmann_delta_v(R1, R2))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lt.hohmann_delta_v(R1, R1)
        with self.assertRaises(ValueError):
            lt.hohmann_delta_v(0, R2)
        with self.assertRaises(ValueError):
            lt.hohmann_delta_v(R1, R2, mu=0)


class SummaryTest(unittest.TestCase):
    def test_anchor_summary_values(self):
        s = lt.low_thrust_transfer_summary(R1, R2, DI, THRUST, ISP, M0)
        self.assertEqual(
            set(s.keys()), {"v_i", "v_f", "delta_v", "m_prop", "mf", "t_transfer"}
        )
        self.assertAlmostEqual(s["v_i"], 7612.684, places=3)
        self.assertAlmostEqual(s["v_f"], 3074.666, places=3)
        self.assertAlmostEqual(s["delta_v"], 5845.584, places=3)
        self.assertAlmostEqual(s["m_prop"], 360.400, places=3)
        self.assertAlmostEqual(s["mf"], 1639.600, places=3)
        self.assertAlmostEqual(s["t_transfer"], 21205870.713, places=3)

    def test_summary_consistent_with_parts(self):
        s = lt.low_thrust_transfer_summary(R1, R2, DI, THRUST, ISP, M0)
        dv = lt.edelbaum_delta_v(R1, R2, DI)
        m_prop, m_final, t = lt.transfer_mass_and_time(dv, M0, THRUST, ISP)
        self.assertAlmostEqual(s["delta_v"], dv, places=6)
        self.assertAlmostEqual(s["m_prop"], m_prop, places=6)
        self.assertAlmostEqual(s["mf"], m_final, places=6)
        self.assertAlmostEqual(s["t_transfer"], t, places=6)

    def test_invalid_thruster_raises(self):
        with self.assertRaises(ValueError):
            lt.low_thrust_transfer_summary(R1, R2, DI, 0.0, ISP, M0)
        with self.assertRaises(ValueError):
            lt.low_thrust_transfer_summary(R1, R2, DI, THRUST, 0.0, M0)
        with self.assertRaises(ValueError):
            lt.low_thrust_transfer_summary(R1, R2, DI, THRUST, ISP, 0.0)

    def test_invalid_geometry_raises(self):
        with self.assertRaises(ValueError):
            lt.low_thrust_transfer_summary(R1, R2, 200.0, THRUST, ISP, M0)
        with self.assertRaises(ValueError):
            lt.low_thrust_transfer_summary(0, R2, DI, THRUST, ISP, M0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
