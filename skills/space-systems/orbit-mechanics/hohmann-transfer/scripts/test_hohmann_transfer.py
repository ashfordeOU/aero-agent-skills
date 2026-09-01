#!/usr/bin/env python3
"""Gate 3 contract test: Hohmann transfer.

Exercises scripts/hohmann_transfer_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (circular orbit velocity,
transfer-orbit semimajor axis, transfer period and transfer time,
vis-viva velocities on the transfer ellipse, departure and arrival burn
impulses, total delta-v budget, orbit period, specific orbital energy,
rendezvous phase angle; invalid inputs raise ValueError.

Anchors (LEO at 6878 km radius to GEO at 42164 km radius, mu =
3.986004418e14 m^3/s^2):
- circular_velocity(6878e3) = 7612.68 m/s (low earth orbit)
- circular_velocity(42164e3) = 3074.67 m/s (geostationary orbit)
- transfer_semimajor_axis = 24521000 m
- transfer_period = 38213.63 s; transfer_time = 19106.81 s (5.31 h)
- vis_viva at perigee = 9982.51 m/s; at apogee = 1628.40 m/s
- departure_delta_v = 2369.82 m/s; arrival_delta_v = 1446.27 m/s
- total_delta_v = 3816.09 m/s (about 3.9 km/s, the classic LEO-GEO
  coplanar budget)
- orbit_period(42164e3) = 86163.57 s (one sidereal day)
- rendezvous_phase_angle = 100.17 degrees
- specific_orbital_energy = -8127736.26 J/kg
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hohmann_transfer_logic as ht  # noqa: E402

R1 = 6878.0e3   # low earth orbit at 500 km altitude, m
R2 = 42164.0e3  # geostationary orbit, m
R_MOON = 384400.0e3  # lunar distance, m


class CircularVelocityTest(unittest.TestCase):
    def test_anchor_leo(self):
        self.assertAlmostEqual(ht.circular_velocity(R1), 7612.684, places=3)

    def test_anchor_geo(self):
        self.assertAlmostEqual(ht.circular_velocity(R2), 3074.666, places=3)

    def test_decreases_with_radius(self):
        self.assertGreater(ht.circular_velocity(R1), ht.circular_velocity(R2))

    def test_scale_with_mu(self):
        v = ht.circular_velocity(R1, mu=4 * ht.MU_EARTH)
        self.assertAlmostEqual(v, 2 * ht.circular_velocity(R1))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.circular_velocity(0)
        with self.assertRaises(ValueError):
            ht.circular_velocity(-R1)
        with self.assertRaises(ValueError):
            ht.circular_velocity(R1, mu=0)


class TransferSemimajorAxisTest(unittest.TestCase):
    def test_anchor_leo_geo(self):
        self.assertAlmostEqual(ht.transfer_semimajor_axis(R1, R2), 24521000.0, places=1)

    def test_mean_of_radii(self):
        self.assertAlmostEqual(
            ht.transfer_semimajor_axis(1.0e6, 3.0e6), 2.0e6, places=1
        )

    def test_symmetric(self):
        self.assertAlmostEqual(
            ht.transfer_semimajor_axis(R1, R2), ht.transfer_semimajor_axis(R2, R1)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.transfer_semimajor_axis(0, R2)
        with self.assertRaises(ValueError):
            ht.transfer_semimajor_axis(R1, -R2)
        with self.assertRaises(ValueError):
            ht.transfer_semimajor_axis(R1, R1)


class TransferTimeTest(unittest.TestCase):
    def test_anchor_leo_geo(self):
        self.assertAlmostEqual(ht.transfer_time(R1, R2), 19106.813, places=3)

    def test_anchor_full_period(self):
        self.assertAlmostEqual(
            ht.transfer_period(ht.transfer_semimajor_axis(R1, R2)), 38213.626, places=3
        )

    def test_time_is_half_period(self):
        a = ht.transfer_semimajor_axis(R1, R2)
        self.assertAlmostEqual(ht.transfer_time(R1, R2), ht.transfer_period(a) / 2.0)

    def test_longer_transfer_for_distant_target(self):
        near = ht.transfer_time(R1, R2)
        far = ht.transfer_time(R1, R_MOON)
        self.assertGreater(far, near)

    def test_anchor_leo_moon(self):
        self.assertAlmostEqual(ht.transfer_time(R1, R_MOON), 430590.195, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.transfer_time(0, R2)
        with self.assertRaises(ValueError):
            ht.transfer_time(R1, R2, mu=-1.0)


class VisVivaTest(unittest.TestCase):
    def test_anchor_perigee(self):
        a = ht.transfer_semimajor_axis(R1, R2)
        self.assertAlmostEqual(ht.vis_viva_velocity(R1, a), 9982.507, places=3)

    def test_anchor_apogee(self):
        a = ht.transfer_semimajor_axis(R1, R2)
        self.assertAlmostEqual(ht.vis_viva_velocity(R2, a), 1628.396, places=3)

    def test_circular_when_radius_equals_semimajor_axis(self):
        v = ht.vis_viva_velocity(R2, R2)
        self.assertAlmostEqual(v, ht.circular_velocity(R2))

    def test_perigee_faster_than_apogee(self):
        a = ht.transfer_semimajor_axis(R1, R2)
        self.assertGreater(ht.vis_viva_velocity(R1, a), ht.vis_viva_velocity(R2, a))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.vis_viva_velocity(0, 2.0e7)
        with self.assertRaises(ValueError):
            ht.vis_viva_velocity(R1, 0)
        with self.assertRaises(ValueError):
            ht.vis_viva_velocity(R1, 2.0e7, mu=0)


class DeltaVTest(unittest.TestCase):
    def test_anchor_departure(self):
        self.assertAlmostEqual(ht.departure_delta_v(R1, R2), 2369.823, places=3)

    def test_anchor_arrival(self):
        self.assertAlmostEqual(ht.arrival_delta_v(R1, R2), 1446.270, places=3)

    def test_anchor_total(self):
        self.assertAlmostEqual(ht.total_delta_v(R1, R2), 3816.093, places=3)

    def test_total_is_sum_of_impulses(self):
        self.assertAlmostEqual(
            ht.total_delta_v(R1, R2),
            ht.departure_delta_v(R1, R2) + ht.arrival_delta_v(R1, R2),
        )

    def test_outward_and_inward_symmetric(self):
        self.assertAlmostEqual(ht.total_delta_v(R1, R2), ht.total_delta_v(R2, R1))
        self.assertAlmostEqual(
            ht.departure_delta_v(R1, R2), ht.arrival_delta_v(R2, R1)
        )

    def test_farther_target_needs_more_delta_v(self):
        self.assertGreater(ht.total_delta_v(R1, R_MOON), ht.total_delta_v(R1, R2))

    def test_anchor_leo_moon_total(self):
        self.assertAlmostEqual(ht.total_delta_v(R1, R_MOON), 3885.604, places=3)

    def test_delta_v_positive_for_both_directions(self):
        self.assertGreater(ht.departure_delta_v(R1, R2), 0.0)
        self.assertGreater(ht.arrival_delta_v(R1, R2), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.departure_delta_v(0, R2)
        with self.assertRaises(ValueError):
            ht.arrival_delta_v(R1, R1)
        with self.assertRaises(ValueError):
            ht.total_delta_v(R1, R2, mu=0)


class OrbitPeriodTest(unittest.TestCase):
    def test_anchor_geo_sidereal_day(self):
        self.assertAlmostEqual(ht.orbit_period(R2), 86163.571, places=3)

    def test_anchor_leo(self):
        self.assertAlmostEqual(ht.orbit_period(R1), 5676.808, places=3)

    def test_kepler_third_law_scaling(self):
        # Doubling the radius scales the period by sqrt(2^3) = 2.828.
        p1 = ht.orbit_period(1.0e7)
        p2 = ht.orbit_period(2.0e7)
        self.assertAlmostEqual(p2 / p1, math.sqrt(8.0), places=4)


class RendezvousPhaseAngleTest(unittest.TestCase):
    def test_anchor_leo_geo(self):
        self.assertAlmostEqual(ht.rendezvous_phase_angle(R1, R2), 100.170, places=3)

    def test_lead_angle_less_than_180(self):
        self.assertLess(ht.rendezvous_phase_angle(R1, R2), 180.0)

    def test_in_range(self):
        angle = ht.rendezvous_phase_angle(R1, R_MOON)
        self.assertGreaterEqual(angle, 0.0)
        self.assertLess(angle, 360.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.rendezvous_phase_angle(R1, R1)
        with self.assertRaises(ValueError):
            ht.rendezvous_phase_angle(-R1, R2)


class SpecificOrbitalEnergyTest(unittest.TestCase):
    def test_anchor_transfer_energy(self):
        a = ht.transfer_semimajor_axis(R1, R2)
        self.assertAlmostEqual(ht.specific_orbital_energy(a), -8127736.263, places=3)

    def test_energy_is_negative(self):
        self.assertLess(ht.specific_orbital_energy(2.0e7), 0.0)

    def test_energy_increases_with_semimajor_axis(self):
        e_low = ht.specific_orbital_energy(1.0e7)
        e_high = ht.specific_orbital_energy(2.0e7)
        self.assertGreater(e_high, e_low)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.specific_orbital_energy(0)
        with self.assertRaises(ValueError):
            ht.specific_orbital_energy(2.0e7, mu=-1.0)


class ScenarioTest(unittest.TestCase):
    def test_leo_to_geo_scenario(self):
        # Full sequence: circular speeds, transfer ellipse speeds,
        # impulses, time, and phase angle for the LEO-to-GEO case.
        a = ht.transfer_semimajor_axis(R1, R2)
        v1 = ht.circular_velocity(R1)
        v2 = ht.circular_velocity(R2)
        vp = ht.vis_viva_velocity(R1, a)
        va = ht.vis_viva_velocity(R2, a)
        dv1 = ht.departure_delta_v(R1, R2)
        dv2 = ht.arrival_delta_v(R1, R2)
        self.assertAlmostEqual(vp - v1, dv1, places=3)
        self.assertAlmostEqual(v2 - va, dv2, places=3)
        self.assertAlmostEqual(ht.total_delta_v(R1, R2) / 1000.0, 3.816, places=3)
        self.assertAlmostEqual(ht.transfer_time(R1, R2) / 3600.0, 5.3074, places=3)

    def test_transfer_ellipse_tangency(self):
        # The transfer ellipse is tangent to both circular orbits:
        # perigee radius equals r1 and apogee radius equals r2.
        a = ht.transfer_semimajor_axis(R1, R2)
        e = 1.0 - R1 / a
        perigee = a * (1.0 - e)
        apogee = a * (1.0 + e)
        self.assertAlmostEqual(perigee, R1, places=1)
        self.assertAlmostEqual(apogee, R2, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
