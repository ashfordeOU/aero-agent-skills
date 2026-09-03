"""Contract tests for orbit-determination (gnc-autonomy/space).

Deterministic, offline, stdlib only. Runs the worked example: a known
LEO with a = 7000 km, e = 0.01, i = 98 deg, RAAN = 45 deg, argp = 30
deg; three position vectors on the two-body arc 60 s apart.
"""

import math
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orbit_determination_logic import (
    MU, cross3, norm3, gibbs_velocity, herrick_gibbs_velocity,
    rv_to_elements, choose_method, orbit_determination,
    DEFAULT_AREA_THRESHOLD,
)

A = 7000.0e3
ECC = 0.01
INC_DEG = 98.0
RAAN_DEG = 45.0
ARGP_DEG = 30.0
DT = 60.0


def kepler_solve(M, e):
    E = M
    for _ in range(40):
        E = E - (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
    return E


def state_at_mean_anomaly(M):
    """Position and velocity vectors on the generating LEO at anomaly M."""
    E = kepler_solve(M, ECC)
    xp = A * (math.cos(E) - ECC)
    yp = A * math.sqrt(1.0 - ECC * ECC) * math.sin(E)
    p = A * (1.0 - ECC * ECC)
    cos_nu = (math.cos(E) - ECC) / (1.0 - ECC * math.cos(E))
    sin_nu = (math.sqrt(1.0 - ECC * ECC) * math.sin(E)) / (1.0 - ECC * math.cos(E))
    vxp = -math.sqrt(MU / p) * sin_nu
    vyp = math.sqrt(MU / p) * (ECC + cos_nu)
    co, so = math.cos(math.radians(ARGP_DEG)), math.sin(math.radians(ARGP_DEG))
    cO, sO = math.cos(math.radians(RAAN_DEG)), math.sin(math.radians(RAAN_DEG))
    ci, si = math.cos(math.radians(INC_DEG)), math.sin(math.radians(INC_DEG))
    r_eci = [
        (cO * co - sO * so * ci) * xp + (-cO * so - sO * co * ci) * yp,
        (sO * co + cO * so * ci) * xp + (-sO * so + cO * co * ci) * yp,
        (so * si) * xp + (co * si) * yp,
    ]
    v_eci = [
        (cO * co - sO * so * ci) * vxp + (-cO * so - sO * co * ci) * vyp,
        (sO * co + cO * so * ci) * vxp + (-sO * so + cO * co * ci) * vyp,
        (so * si) * vxp + (co * si) * vyp,
    ]
    return r_eci, v_eci


def leo_triplet(M0, dt=DT):
    n = math.sqrt(MU / A ** 3)
    r1, _ = state_at_mean_anomaly(M0)
    r2, _ = state_at_mean_anomaly(M0 + n * dt)
    r3, _ = state_at_mean_anomaly(M0 + 2.0 * n * dt)
    return r1, r2, r3, 0.0, dt, 2.0 * dt


class TestVectors(unittest.TestCase):
    def test_cross3_known_value(self):
        self.assertEqual(cross3([1, 0, 0], [0, 1, 0]), [0, 0, 1])
        self.assertEqual(cross3([0, 1, 0], [1, 0, 0]), [0, 0, -1])

    def test_norm3_known_value(self):
        self.assertEqual(norm3([3, 4, 0]), 5.0)
        self.assertEqual(norm3([0, 0, 0]), 0.0)

    def test_mu_constant(self):
        self.assertEqual(MU, 3.986004418e14)


class TestGibbs(unittest.TestCase):
    def setUp(self):
        self.r1, self.r2, self.r3, self.t1, self.t2, self.t3 = leo_triplet(
            math.radians(10.0))

    def test_gibbs_recovers_semimajor_axis(self):
        v2 = gibbs_velocity(self.r1, self.r2, self.r3)
        el = rv_to_elements(self.r2, v2)
        self.assertLess(abs(el["a"] - A) / A, 0.01)

    def test_gibbs_recovers_eccentricity(self):
        v2 = gibbs_velocity(self.r1, self.r2, self.r3)
        el = rv_to_elements(self.r2, v2)
        self.assertLess(abs(el["e"] - ECC), 0.01)

    def test_gibbs_recovers_inclination(self):
        v2 = gibbs_velocity(self.r1, self.r2, self.r3)
        el = rv_to_elements(self.r2, v2)
        self.assertLess(abs(el["i_deg"] - INC_DEG), 1.0)

    def test_gibbs_recovers_raan_and_argp(self):
        v2 = gibbs_velocity(self.r1, self.r2, self.r3)
        el = rv_to_elements(self.r2, v2)
        self.assertLess(abs(el["raan_deg"] - RAAN_DEG), 1.0)
        self.assertLess(abs(el["argp_deg"] - ARGP_DEG), 1.0)

    def test_gibbs_velocity_magnitude_near_circular_speed(self):
        v2 = gibbs_velocity(self.r1, self.r2, self.r3)
        v_circ = math.sqrt(MU / norm3(self.r2))
        self.assertLess(abs(norm3(v2) - v_circ) / v_circ, 0.02)

    def test_collinear_raises(self):
        with self.assertRaises(ValueError):
            gibbs_velocity([7.0e6, 0, 0], [7.1e6, 0, 0], [7.2e6, 0, 0])

    def test_zero_radius_raises(self):
        with self.assertRaises(ValueError):
            gibbs_velocity([7.0e6, 0, 0], [0, 0, 0], [0, 7.0e6, 0])

    def test_nonfinite_position_raises(self):
        with self.assertRaises(ValueError):
            gibbs_velocity([7.0e6, 0, 0], [float("inf"), 1, 1], [0, 7.0e6, 0])


class TestHerrickGibbs(unittest.TestCase):
    def setUp(self):
        self.r1, self.r2, self.r3, self.t1, self.t2, self.t3 = leo_triplet(
            math.radians(10.0))

    def test_hg_agrees_with_gibbs(self):
        vg = gibbs_velocity(self.r1, self.r2, self.r3)
        vh = herrick_gibbs_velocity(self.r1, self.r2, self.r3,
                                    self.t1, self.t2, self.t3)
        rel = abs(norm3(vh) - norm3(vg)) / norm3(vg)
        self.assertLess(rel, 1.0e-2)  # observed band ~4e-7 on the LEO case

    def test_hg_recovers_elements(self):
        vh = herrick_gibbs_velocity(self.r1, self.r2, self.r3,
                                    self.t1, self.t2, self.t3)
        el = rv_to_elements(self.r2, vh)
        self.assertLess(abs(el["a"] - A) / A, 0.01)
        self.assertLess(abs(el["i_deg"] - INC_DEG), 1.0)

    def test_repeated_time_tags_raise(self):
        with self.assertRaises(ValueError):
            herrick_gibbs_velocity(self.r1, self.r2, self.r3,
                                   0.0, 0.0, 60.0)

    def test_decreasing_time_tags_raise(self):
        with self.assertRaises(ValueError):
            herrick_gibbs_velocity(self.r1, self.r2, self.r3,
                                   120.0, 60.0, 0.0)

    def test_nonfinite_time_raises(self):
        with self.assertRaises(ValueError):
            herrick_gibbs_velocity(self.r1, self.r2, self.r3,
                                   0.0, float("nan"), 60.0)


class TestElements(unittest.TestCase):
    def test_circular_equatorial_gives_zero_inclination(self):
        n = math.sqrt(MU / A ** 3)
        # equatorial circular arc in the xy plane
        p1 = [A * math.cos(0.0), A * math.sin(0.0), 0.0]
        p2 = [A * math.cos(n * 60.0), A * math.sin(n * 60.0), 0.0]
        p3 = [A * math.cos(2.0 * n * 60.0), A * math.sin(2.0 * n * 60.0), 0.0]
        vg = gibbs_velocity(p1, p2, p3)
        el = rv_to_elements(p2, vg)
        self.assertLess(el["i_deg"], 1.0e-9)
        self.assertLess(abs(el["a"] - A) / A, 1.0e-9)
        self.assertEqual(el["raan_deg"], 0.0)
        self.assertLess(el["e"], 1.0e-9)

    def test_period_matches_kepler(self):
        v2 = gibbs_velocity(*leo_triplet(math.radians(10.0))[:3])
        el = rv_to_elements(leo_triplet(math.radians(10.0))[1], v2)
        expect = 2.0 * math.pi * math.sqrt(A ** 3 / MU)
        self.assertLess(abs(el["period_s"] - expect) / expect, 0.01)

    def test_elements_keys_present(self):
        r1, r2, r3, _, _, _ = leo_triplet(math.radians(10.0))
        el = rv_to_elements(r2, gibbs_velocity(r1, r2, r3))
        for key in ("a", "e", "i_deg", "raan_deg", "argp_deg", "nu_deg",
                    "period_s"):
            self.assertIn(key, el)

    def test_vis_viva_consistency(self):
        r1, r2, r3, _, _, _ = leo_triplet(math.radians(10.0))
        v2 = gibbs_velocity(r1, r2, r3)
        el = rv_to_elements(r2, v2)
        lhs = 0.5 * norm3(v2) ** 2 - MU / norm3(r2)
        rhs = -MU / (2.0 * el["a"])
        self.assertLess(abs(lhs - rhs) / abs(rhs), 1.0e-6)

    def test_degenerate_state_raises(self):
        with self.assertRaises(ValueError):
            rv_to_elements([7.0e6, 0, 0], [1.0e4, 0, 0])


class TestChooserAndSummary(unittest.TestCase):
    def setUp(self):
        self.r1, self.r2, self.r3, self.t1, self.t2, self.t3 = leo_triplet(
            math.radians(10.0))

    def test_default_chooses_hg_for_close_leo_vectors(self):
        self.assertEqual(choose_method(self.r1, self.r2, self.r3,
                                       self.t1, self.t2, self.t3), "hg")

    def test_wide_spacing_chooses_gibbs(self):
        # 600 s spacing: triangle area far above the default threshold
        n = math.sqrt(MU / A ** 3)
        M0 = math.radians(10.0)
        w1, _ = state_at_mean_anomaly(M0)
        w2, _ = state_at_mean_anomaly(M0 + n * 600.0)
        w3, _ = state_at_mean_anomaly(M0 + n * 1200.0)
        self.assertEqual(choose_method(w1, w2, w3, 0.0, 600.0, 1200.0), "gibbs")

    def test_threshold_switch(self):
        low = choose_method(self.r1, self.r2, self.r3, self.t1, self.t2,
                            self.t3, area_threshold=1.0e8)
        high = choose_method(self.r1, self.r2, self.r3, self.t1, self.t2,
                             self.t3, area_threshold=1.0e14)
        self.assertEqual(low, "gibbs")
        self.assertEqual(high, "hg")

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            choose_method(self.r1, self.r2, self.r3, self.t1, self.t2,
                          self.t3, area_threshold=-1.0)

    def test_summary_fields(self):
        s = orbit_determination(self.r1, self.r2, self.r3,
                                self.t1, self.t2, self.t3)
        self.assertIn("method", s)
        self.assertIn("v2", s)
        self.assertIn("elements", s)
        self.assertIn("energy_check", s)
        self.assertIn("verdict", s)
        self.assertEqual(s["verdict"], "consistent")

    def test_summary_energy_check_matches_vis_viva(self):
        s = orbit_determination(self.r1, self.r2, self.r3,
                                self.t1, self.t2, self.t3)
        lhs = 0.5 * norm3(s["v2"]) ** 2 - MU / norm3(self.r2)
        self.assertLess(abs(lhs - s["energy_check"]) / abs(lhs), 1.0e-9)

    def test_summary_gibbs_path(self):
        s = orbit_determination(self.r1, self.r2, self.r3,
                                self.t1, self.t2, self.t3,
                                area_threshold=1.0e8)
        self.assertEqual(s["method"], "gibbs")
        self.assertEqual(s["verdict"], "consistent")

    def test_default_area_threshold_is_positive(self):
        self.assertGreater(DEFAULT_AREA_THRESHOLD, 0.0)


if __name__ == "__main__":
    unittest.main()
