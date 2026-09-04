#!/usr/bin/env python3
"""Contract tests: two-body Keplerian orbit propagation logic.

Stdlib unittest only, offline, deterministic, no external
dependencies. Run with:

    python3 scripts/test_kepler_orbit_propagation.py

Reference orbit (a = 12000 km, e = 0.35, i = 30 deg, RAAN = 45 deg,
argp = 20 deg, from periapsis, Earth mu 398600.4418 km^3/s^2, dt =
3600 s): anchors n = 4.80283e-4 rad/s, T = 13082.262 s, M =
1.729018 rad, E = 2.041030 rad, nu = 2.336674 rad (133.8815 deg),
r = 13902.9969 km, |v| = 4.911570 km/s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kepler_orbit_propagation_logic as kop

MU = 398600.4418
TWO_PI = 2.0 * math.pi
A = 12000.0
E = 0.35
INC = math.radians(30.0)
RAAN = math.radians(45.0)
ARGP = math.radians(20.0)
DT = 3600.0

N_ANCHOR = 4.80283e-4
T_ANCHOR = 13082.262
M_ANCHOR = 1.729018
E_ANCHOR = 2.041030
NU_ANCHOR = 2.336674
R_ANCHOR = 13902.9969
V_ANCHOR = 4.911570


def mag3(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def cross3(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class TestMeanMotionPeriod(unittest.TestCase):
    def test_mean_motion_anchor(self):
        n = kop.mean_motion(A, MU)
        expected = math.sqrt(MU / (A * A * A))
        self.assertAlmostEqual(n, expected, places=15)
        self.assertTrue(abs(n - N_ANCHOR) < 1e-8, "n off anchor %r" % n)

    def test_orbital_period_anchor(self):
        n = kop.mean_motion(A, MU)
        T = kop.orbital_period(A, MU)
        self.assertAlmostEqual(T, TWO_PI / n, places=9)
        self.assertTrue(abs(T - T_ANCHOR) < 0.05, "T off anchor %r" % T)
        self.assertTrue(abs(T / 3600.0 - 3.633962) < 1e-5)

    def test_period_monotonic_and_third_law(self):
        # n^2 a^3 == mu, T == 2 pi / n, and T grows with semimajor axis.
        p1 = kop.orbital_period(7000.0, MU)
        p2 = kop.orbital_period(12000.0, MU)
        p3 = kop.orbital_period(42164.0, MU)
        self.assertLess(p1, p2)
        self.assertLess(p2, p3)
        for a in (7000.0, 12000.0, 42164.0):
            n = kop.mean_motion(a, MU)
            self.assertAlmostEqual(n * n * a * a * a, MU, places=6)
            self.assertAlmostEqual(kop.orbital_period(a, MU),
                                   TWO_PI / n, places=9)


class TestKeplerSolver(unittest.TestCase):
    def test_kepler_solve_worked(self):
        M = kop.mean_motion(A, MU) * DT
        E_sol = kop.kepler_solve(M, E)
        self.assertTrue(abs(E_sol - E_ANCHOR) < 1e-6,
                        "E %r off anchor" % E_sol)

    def test_kepler_residual_worked(self):
        M = kop.mean_motion(A, MU) * DT
        E_sol = kop.kepler_solve(M, E)
        self.assertLess(abs(E_sol - E * math.sin(E_sol) - M), 1e-12)

    def test_kepler_residual_grid(self):
        # Residual below 1e-12 over mean anomalies and eccentricities,
        # including high eccentricity where Newton is hardest.
        for e in (0.0, 0.2, 0.35, 0.6, 0.9, 0.99):
            for M in (0.1, 1.0, math.pi, 3.0, 4.5, 5.9, TWO_PI + 0.5,
                      25.0):
                E_sol = kop.kepler_solve(M, e)
                resid = E_sol - e * math.sin(E_sol) - M
                self.assertLess(abs(resid), 1e-12,
                                "resid %r for e=%r M=%r" % (resid, e, M))

    def test_kepler_circular_exact(self):
        # For e = 0 the Kepler equation reduces to E = M exactly.
        for M in (0.0, 1.729018, -2.0, 4.5, 10.0):
            self.assertEqual(kop.kepler_solve(M, 0.0), M)


class TestAnomalyMaps(unittest.TestCase):
    def test_true_anomaly_worked(self):
        M = kop.mean_motion(A, MU) * DT
        E_sol = kop.kepler_solve(M, E)
        nu = kop.true_anomaly_from_eccentric(E_sol, E)
        self.assertTrue(abs(nu - NU_ANCHOR) < 1e-6, "nu %r" % nu)
        self.assertTrue(abs(math.degrees(nu) - 133.8815) < 1e-3)

    def test_true_anomaly_endpoints_range_and_fold(self):
        # Periapsis E = 0 gives nu = 0; apoapsis E = pi gives nu = pi.
        self.assertEqual(kop.true_anomaly_from_eccentric(0.0, E), 0.0)
        self.assertAlmostEqual(
            kop.true_anomaly_from_eccentric(math.pi, E), math.pi, places=12)
        # nu lands in (-pi, pi]; a full revolution E -> E + 2 pi
        # returns the same folded true anomaly; E = 2 pi closes at 0.
        for E_t in (0.0, 0.5, 1.0, 2.041030, math.pi, 4.0, 4.5, 5.5,
                    5.9, TWO_PI - 0.01, TWO_PI):
            nu = kop.true_anomaly_from_eccentric(E_t, E)
            self.assertGreater(nu, -math.pi - 1e-12)
            self.assertLessEqual(nu, math.pi + 1e-12)
            nu_shift = kop.true_anomaly_from_eccentric(E_t + TWO_PI, E)
            self.assertAlmostEqual(nu_shift, nu, places=9)
        self.assertEqual(kop.true_anomaly_from_eccentric(TWO_PI, E), 0.0)

    def test_eccentric_from_true_worked(self):
        E_back = kop.eccentric_anomaly_from_true(NU_ANCHOR, E)
        self.assertTrue(abs(E_back - E_ANCHOR) < 1e-6, "E %r" % E_back)

    def test_anomaly_map_roundtrip(self):
        for E_t in (0.0, 0.3, 1.5, 2.041030, 4.0, 5.5, TWO_PI - 0.001):
            nu = kop.true_anomaly_from_eccentric(E_t, E)
            E_back = kop.eccentric_anomaly_from_true(nu, E)
            self.assertAlmostEqual(math.sin(E_back), math.sin(E_t),
                                   places=9)
        for nu_t in (-2.5, -1.0, -0.5, 0.0, 0.8, NU_ANCHOR, 3.0):
            E_m = kop.eccentric_anomaly_from_true(nu_t, E)
            nu_back = kop.true_anomaly_from_eccentric(E_m, E)
            self.assertAlmostEqual(math.sin(nu_back), math.sin(nu_t),
                                   places=9)


class TestRadiusTime(unittest.TestCase):
    def test_radius_identity_worked(self):
        M = kop.mean_motion(A, MU) * DT
        E_sol = kop.kepler_solve(M, E)
        nu = kop.true_anomaly_from_eccentric(E_sol, E)
        r_E_form = A * (1.0 - E * math.cos(E_sol))
        r_nu_form = kop.radius_at_anomaly(A, E, nu)
        self.assertAlmostEqual(r_E_form, R_ANCHOR, places=3)
        self.assertLess(abs(r_E_form - r_nu_form) / r_E_form, 1e-9)

    def test_radius_geometry_endpoints_and_identity(self):
        # Periapsis a(1-e), apoapsis a(1+e), latus rectum a(1-e^2),
        # and the conic form r = a(1-e^2)/(1 + e cos nu) matches
        # r = a(1 - e cos E) at the propagated state.
        self.assertAlmostEqual(kop.radius_at_anomaly(A, E, 0.0),
                               A * (1.0 - E), places=9)
        self.assertAlmostEqual(kop.radius_at_anomaly(A, E, math.pi),
                               A * (1.0 + E), places=9)
        self.assertAlmostEqual(kop.radius_at_anomaly(A, E, math.pi / 2.0),
                               A * (1.0 - E * E), places=9)
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        r_e = A * (1.0 - E * math.cos(st["eccentric_anomaly_rad"]))
        r_nu = kop.radius_at_anomaly(A, E, st["true_anomaly_rad"])
        self.assertLess(abs(r_e - r_nu) / r_e, 1e-9)

    def test_time_since_periapsis_endpoints(self):
        # Periapsis t = 0; apoapsis t = T/2.
        self.assertEqual(kop.time_since_periapsis(0.0, A, E, MU), 0.0)
        T = kop.orbital_period(A, MU)
        t_half = kop.time_since_periapsis(math.pi, A, E, MU)
        self.assertLess(abs(t_half - T / 2.0), 1e-6)

    def test_time_since_periapsis_range_monotonic(self):
        # t grows from 0 just after periapsis to T just before the next
        # periapsis, so it is strictly increasing on each side of the
        # nu = 0 (mod 2 pi) fold where it resets to 0.
        T = kop.orbital_period(A, MU)
        seq_after = (0.1, 1.0, 2.0, 2.9)
        seq_before = (-2.9, -2.0, -1.0, -0.1)
        prev = -1.0
        for nu_t in seq_after:
            t = kop.time_since_periapsis(nu_t, A, E, MU)
            self.assertGreater(t, prev)
            prev = t
        self.assertLess(prev, T)
        prev = -1.0
        for nu_t in seq_before:
            t = kop.time_since_periapsis(nu_t, A, E, MU)
            self.assertGreater(t, prev)
            prev = t
        self.assertLess(prev, T)
        # Just before periapsis t is near T; just after it is near 0.
        t_before = kop.time_since_periapsis(-0.1, A, E, MU)
        t_after = kop.time_since_periapsis(0.1, A, E, MU)
        self.assertGreater(t_before, T * 0.99)
        self.assertLess(t_after, T * 0.01)
        # 2 pi periodicity of the anomaly-to-time map.
        for nu_t in (-2.5, -0.5, 0.7, 2.9):
            self.assertAlmostEqual(
                kop.time_since_periapsis(nu_t, A, E, MU),
                kop.time_since_periapsis(nu_t + TWO_PI, A, E, MU),
                places=9)

    def test_inverse_time_of_flight_worked(self):
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        t_inv = kop.time_since_periapsis(
            st["true_anomaly_rad"], A, E, MU)
        self.assertLess(abs(t_inv - DT), 1e-6)

    def test_inverse_time_of_flight_grid(self):
        # For any dt inside one period, the propagated true anomaly
        # maps back to exactly that elapsed time.
        for dt in (100.0, 1000.0, 6000.0, 9000.0, 12000.0):
            st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, dt, MU)
            t_inv = kop.time_since_periapsis(
                st["true_anomaly_rad"], A, E, MU)
            self.assertLess(abs(t_inv - dt) / dt, 1e-9,
                            "TOF inverse %r vs dt %r" % (t_inv, dt))


class TestPropagationState(unittest.TestCase):
    def test_propagate_worked_state(self):
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        self.assertEqual(
            set(st.keys()),
            {"mean_anomaly_rad", "eccentric_anomaly_rad",
             "true_anomaly_rad", "radius_km", "position_km",
             "velocity_kms", "period_s"})
        self.assertTrue(abs(st["mean_anomaly_rad"] - M_ANCHOR) < 1e-6)
        self.assertTrue(abs(st["eccentric_anomaly_rad"] - E_ANCHOR) < 1e-6)
        self.assertTrue(abs(st["true_anomaly_rad"] - NU_ANCHOR) < 1e-6)
        self.assertLess(abs(st["radius_km"] - R_ANCHOR) / R_ANCHOR, 1e-6)
        self.assertAlmostEqual(st["period_s"],
                               kop.orbital_period(A, MU), places=9)

    def test_propagate_velocity_anchor_and_energy(self):
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        vmag = mag3(st["velocity_kms"])
        rmag = mag3(st["position_km"])
        self.assertTrue(abs(vmag - V_ANCHOR) < 1e-5,
                        "|v| %r off anchor" % vmag)
        # Specific orbital energy identity: v^2 = mu (2/r - 1/a).
        self.assertAlmostEqual(vmag * vmag,
                               MU * (2.0 / rmag - 1.0 / A), places=9)
        self.assertAlmostEqual(rmag, st["radius_km"], places=9)

    def test_propagate_dt_zero_unchanged(self):
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, 0.0, MU)
        self.assertEqual(st["mean_anomaly_rad"], 0.0)
        self.assertEqual(st["eccentric_anomaly_rad"], 0.0)
        self.assertEqual(st["true_anomaly_rad"], 0.0)
        self.assertAlmostEqual(st["radius_km"], A * (1.0 - E), places=9)
        self.assertAlmostEqual(mag3(st["position_km"]), A * (1.0 - E),
                               places=6)

    def test_propagate_one_period_return(self):
        T = kop.orbital_period(A, MU)
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, T, MU)
        self.assertLess(abs(st["true_anomaly_rad"]), 1e-9)
        self.assertLess(abs(st["eccentric_anomaly_rad"] - TWO_PI), 1e-9)
        self.assertLess(abs(st["mean_anomaly_rad"] - TWO_PI), 1e-9)
        self.assertLess(abs(st["radius_km"] - A * (1.0 - E)) /
                        (A * (1.0 - E)), 1e-9)
        st0 = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, 0.0, MU)
        for i in range(3):
            self.assertAlmostEqual(st["position_km"][i],
                                   st0["position_km"][i], places=9)
            self.assertAlmostEqual(st["velocity_kms"][i],
                                   st0["velocity_kms"][i], places=9)

    def test_propagate_half_period_apoapsis(self):
        T = kop.orbital_period(A, MU)
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, T / 2.0, MU)
        self.assertLess(abs(math.cos(st["true_anomaly_rad"]) + 1.0), 1e-9)
        self.assertLess(abs(math.sin(st["true_anomaly_rad"])), 1e-9)
        self.assertLess(abs(st["radius_km"] - A * (1.0 + E)) /
                        (A * (1.0 + E)), 1e-9)
        vmag = mag3(st["velocity_kms"])
        self.assertAlmostEqual(vmag * vmag,
                               MU * (2.0 / (A * (1.0 + E)) - 1.0 / A),
                               places=6)

    def test_propagate_deterministic(self):
        s1 = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        s2 = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        for key in s1:
            self.assertEqual(s1[key], s2[key])


class TestRotationMomentum(unittest.TestCase):
    def test_perifocal_closed_form_periapsis_axis(self):
        # First column of the rotation is the periapsis unit vector P.
        p_hat, _ = kop.perifocal_to_inertial(
            [1.0, 0.0, 0.0], [0.0, 0.0, 0.0], RAAN, INC, ARGP)
        px = (math.cos(RAAN) * math.cos(ARGP)
              - math.sin(RAAN) * math.sin(ARGP) * math.cos(INC))
        py = (math.sin(RAAN) * math.cos(ARGP)
              + math.cos(RAAN) * math.sin(ARGP) * math.cos(INC))
        pz = math.sin(ARGP) * math.sin(INC)
        for got, want in zip(p_hat, (px, py, pz)):
            self.assertAlmostEqual(got, want, places=12)

    def test_perifocal_rotation_preserves_norms(self):
        for r_pf, v_pf in (([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
                           ([7800.0, 3000.0, -500.0], [4.0, -2.0, 6.5]),
                           ([-13903.0, 0.0, 0.0], [0.0, 3.0, 2.0])):
            r, v = kop.perifocal_to_inertial(
                r_pf, v_pf, RAAN, INC, ARGP)
            self.assertAlmostEqual(mag3(r), mag3(r_pf), places=9)
            self.assertAlmostEqual(mag3(v), mag3(v_pf), places=9)
            self.assertAlmostEqual(dot3(r, v), dot3(r_pf, v_pf), places=9)

    def test_perifocal_pipeline_dt_zero_crosscheck(self):
        # Independent perifocal construction at periapsis: r = (rp, 0, 0),
        # v = (0, sqrt(mu(2/rp - 1/a)), 0), rotated, must equal the
        # propagate_kepler dt = 0 state.
        rp = A * (1.0 - E)
        vp = math.sqrt(MU * (2.0 / rp - 1.0 / A))
        r, v = kop.perifocal_to_inertial(
            [rp, 0.0, 0.0], [0.0, vp, 0.0], RAAN, INC, ARGP)
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, 0.0, MU)
        for i in range(3):
            self.assertAlmostEqual(r[i], st["position_km"][i], places=9)
            self.assertAlmostEqual(v[i], st["velocity_kms"][i], places=9)

    def test_angular_momentum_direction_and_magnitude(self):
        st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, MU)
        h = cross3(st["position_km"], st["velocity_kms"])
        hmag = mag3(h)
        h_expected = math.sqrt(MU * A * (1.0 - E * E))
        self.assertLess(abs(hmag - h_expected) / h_expected, 1e-9)
        # h is parallel to W hat = (sin RAAN sin i, -cos RAAN sin i,
        # cos i).
        w_hat = [math.sin(RAAN) * math.sin(INC),
                 -math.cos(RAAN) * math.sin(INC),
                 math.cos(INC)]
        self.assertAlmostEqual(dot3([c / hmag for c in h], w_hat),
                               1.0, places=9)

    def test_orbital_plane_membership_in_h_direction(self):
        # Position and velocity lie in the orbital plane: r . h = 0,
        # exercised at periapsis (dt = 0) and at the propagated state.
        for dt in (0.0, DT):
            st = kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, dt, MU)
            h = cross3(st["position_km"], st["velocity_kms"])
            rel = abs(dot3(st["position_km"], h)) / (
                mag3(st["position_km"]) * mag3(h))
            self.assertLess(rel, 1e-9)


class TestValueErrors(unittest.TestCase):
    def test_mean_motion_and_period_valueerrors(self):
        for bad_a in (0.0, -5.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                kop.mean_motion(bad_a, MU)
            with self.assertRaises(ValueError):
                kop.orbital_period(bad_a, MU)
        for bad_mu in (0.0, -1.0, float("nan"), "x"):
            with self.assertRaises(ValueError):
                kop.mean_motion(A, bad_mu)
            with self.assertRaises(ValueError):
                kop.orbital_period(A, bad_mu)

    def test_kepler_solve_valueerrors(self):
        for bad_e in (-0.1, 1.0, 2.0, float("inf")):
            with self.assertRaises(ValueError):
                kop.kepler_solve(1.0, bad_e)
        with self.assertRaises(ValueError):
            kop.kepler_solve("x", 0.2)

    def test_anomaly_maps_valueerrors(self):
        for bad_e in (-0.1, 1.0, 2.0):
            with self.assertRaises(ValueError):
                kop.true_anomaly_from_eccentric(1.0, bad_e)
            with self.assertRaises(ValueError):
                kop.eccentric_anomaly_from_true(1.0, bad_e)

    def test_radius_at_anomaly_valueerrors(self):
        for bad_e in (-0.1, 1.0, 1.5):
            with self.assertRaises(ValueError):
                kop.radius_at_anomaly(A, bad_e, 1.0)
        with self.assertRaises(ValueError):
            kop.radius_at_anomaly(0.0, 0.3, 1.0)

    def test_time_since_periapsis_valueerrors(self):
        with self.assertRaises(ValueError):
            kop.time_since_periapsis(1.0, 0.0, 0.3, MU)
        for bad_e in (-0.1, 1.0):
            with self.assertRaises(ValueError):
                kop.time_since_periapsis(1.0, A, bad_e, MU)
        with self.assertRaises(ValueError):
            kop.time_since_periapsis(1.0, A, 0.3, 0.0)

    def test_propagate_valueerrors(self):
        for bad_a in (0.0, -1.0):
            with self.assertRaises(ValueError):
                kop.propagate_kepler(bad_a, E, INC, RAAN, ARGP, 0.0, DT, MU)
        for bad_e in (-0.5, 1.0, 1.2):
            with self.assertRaises(ValueError):
                kop.propagate_kepler(A, bad_e, INC, RAAN, ARGP, 0.0, DT, MU)
        with self.assertRaises(ValueError):
            kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, -1.0, MU)
        with self.assertRaises(ValueError):
            kop.propagate_kepler(A, E, INC, RAAN, ARGP, 0.0, DT, 0.0)

    def test_perifocal_to_inertial_valueerrors(self):
        with self.assertRaises(ValueError):
            kop.perifocal_to_inertial([1.0, 0.0], [0.0, 0.0, 0.0],
                                      RAAN, INC, ARGP)
        with self.assertRaises(ValueError):
            kop.perifocal_to_inertial([1.0, 0.0, float("nan")],
                                      [0.0, 0.0, 0.0], RAAN, INC, ARGP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
