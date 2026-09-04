"""Contract test for the bi-elliptic three-impulse transfer logic.

Deterministic, offline, stdlib only. Run: python3 test_bi_elliptic_transfer.py
Covers: worked-example anchors and magnitude bounds from the spec, all
ValueError rejections (mu <= 0, r1 <= 0, r2 <= 0, r1 == r2, r_b <= r2,
inward transfer), the small-radius-ratio sanity check (hohmann wins), the
degenerate r_b -> r2 limit, vis-viva round trips, exact dict keys,
determinism, and the transfer-time coast model.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bi_elliptic_transfer_logic import (  # noqa: E402
    MU_EARTH,
    bi_elliptic_delta_v,
    circular_speed,
    hohmann_delta_v,
    transfer_comparison,
    transfer_time_bi_elliptic,
)


class BiEllipticTransferContractTest(unittest.TestCase):
    """Contract: spec model, worked example (r2 = 30*r1, r_b = 2*r2)."""

    def setUp(self):
        self.mu = MU_EARTH
        self.r1 = 6578e3          # 300 km circular orbit radius
        self.r2 = 30.0 * self.r1   # 197 340 km radius
        self.r_b = 2.0 * self.r2   # 394 680 km intermediate apogee

    # --- circular_speed -------------------------------------------------

    def test_circular_speed_known_value(self):
        v = circular_speed(self.mu, self.r1)
        self.assertAlmostEqual(v, 7784.3428095, places=4)

    def test_circular_speed_matches_sqrt_mu_over_r(self):
        for r in (self.r1, self.r2, 42164e3):
            self.assertAlmostEqual(
                circular_speed(self.mu, r), math.sqrt(self.mu / r), places=6
            )

    def test_circular_speed_rejects_zero_radius(self):
        with self.assertRaises(ValueError):
            circular_speed(self.mu, 0.0)

    def test_circular_speed_rejects_negative_radius(self):
        with self.assertRaises(ValueError):
            circular_speed(self.mu, -1000.0)

    def test_circular_speed_rejects_nonpositive_mu(self):
        for bad_mu in (0.0, -3.986e14):
            with self.assertRaises(ValueError):
                circular_speed(bad_mu, self.r1)

    # --- hohmann baseline ----------------------------------------------

    def test_hohmann_worked_example_anchors(self):
        h = hohmann_delta_v(self.mu, self.r1, self.r2)
        self.assertAlmostEqual(h["dv1"], 3045.3648066, places=2)
        self.assertAlmostEqual(h["dv2"], 1060.2297968, places=2)
        self.assertAlmostEqual(h["total"], 4105.5946035, places=2)

    def test_hohmann_total_within_spec_bounds(self):
        h = hohmann_delta_v(self.mu, self.r1, self.r2)
        self.assertTrue(3900.0 <= h["total"] <= 4300.0, h["total"])

    def test_hohmann_dict_exact_keys(self):
        h = hohmann_delta_v(self.mu, self.r1, self.r2)
        self.assertEqual(set(h.keys()), {"dv1", "dv2", "total"})

    def test_hohmann_vis_viva_round_trip(self):
        h = hohmann_delta_v(self.mu, self.r1, self.r2)
        v_c1 = math.sqrt(self.mu / self.r1)
        v_c2 = math.sqrt(self.mu / self.r2)
        v_t1 = math.sqrt(self.mu * (2.0 / self.r1 - 2.0 / (self.r1 + self.r2)))
        v_t2 = math.sqrt(self.mu * (2.0 / self.r2 - 2.0 / (self.r1 + self.r2)))
        self.assertAlmostEqual(h["dv1"], v_t1 - v_c1, places=6)
        self.assertAlmostEqual(h["dv2"], v_c2 - v_t2, places=6)
        self.assertAlmostEqual(h["total"], h["dv1"] + h["dv2"], places=9)

    def test_hohmann_rejects_identical_orbits(self):
        with self.assertRaises(ValueError):
            hohmann_delta_v(self.mu, self.r1, self.r1)

    def test_hohmann_rejects_nonpositive_radii(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                hohmann_delta_v(self.mu, bad, self.r2)
            with self.assertRaises(ValueError):
                hohmann_delta_v(self.mu, self.r1, bad)

    def test_hohmann_rejects_nonpositive_mu(self):
        for bad_mu in (0.0, -1.0):
            with self.assertRaises(ValueError):
                hohmann_delta_v(bad_mu, self.r1, self.r2)

    # --- bi-elliptic three-burn ----------------------------------------

    def test_bi_worked_example_anchors(self):
        b = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        self.assertAlmostEqual(b["dv1"], 3133.7720499, places=2)
        self.assertAlmostEqual(b["dv2"], 638.5731979, places=2)
        self.assertAlmostEqual(b["dv3"], 219.8635070, places=2)
        self.assertAlmostEqual(b["total"], 3992.2087548, places=2)

    def test_bi_total_within_spec_bounds(self):
        b = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        self.assertTrue(3850.0 <= b["total"] <= 4150.0, b["total"])

    def test_bi_all_impulse_magnitudes_positive(self):
        b = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        self.assertGreater(b["dv1"], 0.0)
        self.assertGreater(b["dv2"], 0.0)
        self.assertGreater(b["dv3"], 0.0)

    def test_bi_dict_exact_keys(self):
        b = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        self.assertEqual(set(b.keys()), {"dv1", "dv2", "dv3", "total"})

    def test_bi_vis_viva_round_trip(self):
        b = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        v_c1 = math.sqrt(self.mu / self.r1)
        v_c2 = math.sqrt(self.mu / self.r2)
        v_e1_r1 = math.sqrt(self.mu * (2.0 / self.r1 - 2.0 / (self.r1 + self.r_b)))
        v_e1_rb = math.sqrt(self.mu * (2.0 / self.r_b - 2.0 / (self.r1 + self.r_b)))
        v_e2_rb = math.sqrt(self.mu * (2.0 / self.r_b - 2.0 / (self.r_b + self.r2)))
        v_e2_r2 = math.sqrt(self.mu * (2.0 / self.r2 - 2.0 / (self.r_b + self.r2)))
        self.assertAlmostEqual(b["dv1"], v_e1_r1 - v_c1, places=6)
        self.assertAlmostEqual(b["dv2"], v_e2_rb - v_e1_rb, places=6)
        self.assertAlmostEqual(b["dv3"], v_e2_r2 - v_c2, places=6)
        self.assertAlmostEqual(b["total"], b["dv1"] + b["dv2"] + b["dv3"], places=9)

    def test_bi_rejects_rb_equal_r2(self):
        with self.assertRaises(ValueError):
            bi_elliptic_delta_v(self.mu, self.r1, self.r2, self.r2)

    def test_bi_rejects_rb_below_r2(self):
        with self.assertRaises(ValueError):
            bi_elliptic_delta_v(self.mu, self.r1, 0.5 * self.r2, self.r2)

    def test_bi_rejects_inward_transfer(self):
        with self.assertRaises(ValueError):
            bi_elliptic_delta_v(self.mu, self.r2, self.r_b, self.r1)

    def test_bi_rejects_identical_orbits(self):
        with self.assertRaises(ValueError):
            bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r1)

    def test_bi_rejects_nonpositive_radii(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                bi_elliptic_delta_v(self.mu, bad, self.r_b, self.r2)
            with self.assertRaises(ValueError):
                bi_elliptic_delta_v(self.mu, self.r1, self.r_b, bad)

    def test_bi_rejects_nonpositive_mu(self):
        for bad_mu in (0.0, -1.0):
            with self.assertRaises(ValueError):
                bi_elliptic_delta_v(bad_mu, self.r1, self.r_b, self.r2)

    # --- comparison verdict --------------------------------------------

    def test_comparison_worked_example_saving(self):
        c = transfer_comparison(self.mu, self.r1, self.r2, self.r_b)
        self.assertAlmostEqual(c["hohmann_dv1"], 3045.3648066, places=2)
        self.assertAlmostEqual(c["hohmann_dv2"], 1060.2297968, places=2)
        self.assertAlmostEqual(c["hohmann_total"], 4105.5946035, places=2)
        self.assertAlmostEqual(c["bi_dv1"], 3133.7720499, places=2)
        self.assertAlmostEqual(c["bi_dv2"], 638.5731979, places=2)
        self.assertAlmostEqual(c["bi_dv3"], 219.8635070, places=2)
        self.assertAlmostEqual(c["bi_total"], 3992.2087548, places=2)
        self.assertAlmostEqual(c["saving"], 113.3858486, places=2)

    def test_comparison_saving_within_spec_bounds(self):
        c = transfer_comparison(self.mu, self.r1, self.r2, self.r_b)
        self.assertTrue(50.0 <= c["saving"] <= 180.0, c["saving"])
        self.assertLess(c["bi_total"], c["hohmann_total"])
        self.assertEqual(c["verdict"], "bi-elliptic")

    def test_comparison_dict_exact_keys(self):
        c = transfer_comparison(self.mu, self.r1, self.r2, self.r_b)
        self.assertEqual(
            set(c.keys()),
            {"hohmann_dv1", "hohmann_dv2", "hohmann_total", "bi_dv1",
             "bi_dv2", "bi_dv3", "bi_total", "saving", "verdict"},
        )

    def test_comparison_small_ratio_hohmann_wins(self):
        r2 = 2.0 * self.r1
        r_b = 1.5 * r2  # moderate intermediate apogee
        c = transfer_comparison(self.mu, self.r1, r2, r_b)
        self.assertLess(c["hohmann_total"], c["bi_total"])
        self.assertLess(c["saving"], 0.0)
        self.assertEqual(c["verdict"], "hohmann")

    def test_comparison_degenerate_rb_near_r2(self):
        r2 = 2.0 * self.r1
        r_b = r2 * 1.01  # very close to the target radius
        c = transfer_comparison(self.mu, self.r1, r2, r_b)
        self.assertGreater(c["bi_total"], c["hohmann_total"] - 1.0)
        self.assertEqual(c["verdict"], "hohmann")

    # --- transfer time --------------------------------------------------

    def test_time_worked_example(self):
        t = transfer_time_bi_elliptic(self.mu, self.r1, self.r_b, self.r2)
        self.assertAlmostEqual(t, 1248552.6555, places=0)
        days = t / 86400.0
        self.assertTrue(10.0 <= days <= 40.0, days)

    def test_time_equals_half_period_sum(self):
        t = transfer_time_bi_elliptic(self.mu, self.r1, self.r_b, self.r2)
        t1 = math.pi * math.sqrt((self.r1 + self.r_b) ** 3 / (8.0 * self.mu))
        t2 = math.pi * math.sqrt((self.r_b + self.r2) ** 3 / (8.0 * self.mu))
        self.assertAlmostEqual(t, t1 + t2, places=6)

    def test_time_rejects_invalid_args(self):
        with self.assertRaises(ValueError):
            transfer_time_bi_elliptic(self.mu, self.r1, self.r2, self.r2)
        with self.assertRaises(ValueError):
            transfer_time_bi_elliptic(self.mu, 0.0, self.r_b, self.r2)
        with self.assertRaises(ValueError):
            transfer_time_bi_elliptic(self.mu, self.r1, self.r_b, self.r1)

    # --- determinism ----------------------------------------------------

    def test_run_to_run_identical_floats(self):
        a = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        b = bi_elliptic_delta_v(self.mu, self.r1, self.r_b, self.r2)
        self.assertEqual(a, b)
        c1 = transfer_comparison(self.mu, self.r1, self.r2, self.r_b)
        c2 = transfer_comparison(self.mu, self.r1, self.r2, self.r_b)
        self.assertEqual(c1, c2)

    def test_mu_earth_constant(self):
        self.assertEqual(MU_EARTH, 3.986004418e14)


if __name__ == "__main__":
    unittest.main(verbosity=2)
