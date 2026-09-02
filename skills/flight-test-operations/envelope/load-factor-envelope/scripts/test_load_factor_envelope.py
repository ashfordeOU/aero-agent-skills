#!/usr/bin/env python3
"""Gate 3 contract test for the load factor envelope (V-n diagram) leaf.

Stdlib unittest only, offline, no network. Run directly:
python3 scripts/test_load_factor_envelope.py
"""

import math
import unittest

from load_factor_envelope import (
    SEA_LEVEL_DENSITY,
    TRANSPORT_NEGATIVE_LIMIT,
    TRANSPORT_POSITIVE_LIMIT,
    corner_speed,
    envelope_verdict,
    gust_load_factor_increment,
    gust_load_factor_increment_si,
    stall_speed_boundary,
)

# Reference case: W/S = 6000 Pa, CL_max = 1.8, rho = 1.225 kg/m^3.
W_S = 6000.0
CL_MAX = 1.8
RHO = SEA_LEVEL_DENSITY


class StallSpeedBoundaryTests(unittest.TestCase):
    def test_reference_case(self):
        # V = sqrt(2 * 1 * 6000 / (1.225 * 1.8)) = sqrt(5442.18) ~ 73.77 m/s.
        self.assertAlmostEqual(
            stall_speed_boundary(W_S, CL_MAX, 1.0, RHO), 73.771, places=2
        )

    def test_scales_with_sqrt_load_factor(self):
        v1 = stall_speed_boundary(W_S, CL_MAX, 1.0, RHO)
        v25 = stall_speed_boundary(W_S, CL_MAX, 2.5, RHO)
        self.assertAlmostEqual(v25 / v1, math.sqrt(2.5), places=4)

    def test_density_variation_increases_speed(self):
        # Thinner air stalls faster: V(rho=0.5) / V(rho=1.225) = sqrt(1.225/0.5).
        v_sl = stall_speed_boundary(W_S, CL_MAX, 1.0, RHO)
        v_hi = stall_speed_boundary(W_S, CL_MAX, 1.0, 0.5)
        self.assertAlmostEqual(v_hi / v_sl, math.sqrt(1.225 / 0.5), places=4)
        self.assertAlmostEqual(v_hi, 115.47, places=2)

    def test_wing_loading_scaling(self):
        # Doubling the wing loading raises the stall speed by sqrt(2).
        v1 = stall_speed_boundary(W_S, CL_MAX, 1.0, RHO)
        v2 = stall_speed_boundary(2.0 * W_S, CL_MAX, 1.0, RHO)
        self.assertAlmostEqual(v2 / v1, math.sqrt(2.0), places=4)

    def test_cl_max_scaling(self):
        # Halving CL_max raises the stall speed by sqrt(2).
        v1 = stall_speed_boundary(W_S, CL_MAX, 1.0, RHO)
        v_half = stall_speed_boundary(W_S, 0.5 * CL_MAX, 1.0, RHO)
        self.assertAlmostEqual(v_half / v1, math.sqrt(2.0), places=4)

    def test_zero_wing_loading_raises(self):
        with self.assertRaises(ValueError):
            stall_speed_boundary(0.0, CL_MAX, 1.0, RHO)

    def test_negative_cl_max_raises(self):
        with self.assertRaises(ValueError):
            stall_speed_boundary(W_S, -1.8, 1.0, RHO)

    def test_zero_density_raises(self):
        with self.assertRaises(ValueError):
            stall_speed_boundary(W_S, CL_MAX, 1.0, 0.0)

    def test_nonpositive_load_factor_raises(self):
        with self.assertRaises(ValueError):
            stall_speed_boundary(W_S, CL_MAX, 0.0, RHO)
        with self.assertRaises(ValueError):
            stall_speed_boundary(W_S, CL_MAX, -1.0, RHO)


class CornerSpeedTests(unittest.TestCase):
    def test_corner_at_transport_limit(self):
        # V_A = 73.771 * sqrt(2.5) ~ 116.64 m/s.
        self.assertAlmostEqual(
            corner_speed(W_S, CL_MAX, TRANSPORT_POSITIVE_LIMIT, RHO),
            116.64,
            places=2,
        )

    def test_corner_matches_stall_boundary_at_limit(self):
        va = corner_speed(W_S, CL_MAX, 2.5, RHO)
        v_bound = stall_speed_boundary(W_S, CL_MAX, 2.5, RHO)
        self.assertAlmostEqual(va, v_bound, places=9)

    def test_limit_below_one_raises(self):
        with self.assertRaises(ValueError):
            corner_speed(W_S, CL_MAX, 1.0, RHO)


class GustIncrementTests(unittest.TestCase):
    def test_far_mixed_unit_form(self):
        # FAR 25.341 form: k_g * U * V * a / (498 * W/S)
        # 0.7 * 66 * 200 * 5.5 / (498 * 100) ~ 1.0205.
        self.assertAlmostEqual(
            gust_load_factor_increment(0.7, 66.0, 200.0, 5.5, 100.0),
            1.0205,
            places=4,
        )

    def test_si_form_reference_case(self):
        # 0.7 * 1.225 * 20 * 100 * 5.5 / (2 * 6000) ~ 0.7860.
        self.assertAlmostEqual(
            gust_load_factor_increment_si(0.7, RHO, 20.0, 100.0, 5.5, W_S),
            0.7860,
            places=4,
        )

    def test_si_form_matches_mixed_form_after_conversion(self):
        # 66 ft/s = 20.1168 m/s, 200 kt = 102.8889 m/s, 100 psf = 4788.02 Pa.
        si = gust_load_factor_increment_si(
            0.7, RHO, 20.1168, 102.8889, 5.5, 4788.02
        )
        far = gust_load_factor_increment(0.7, 66.0, 200.0, 5.5, 100.0)
        self.assertAlmostEqual(si, far, delta=0.005)

    def test_zero_gust_velocity_gives_zero_increment(self):
        self.assertEqual(
            gust_load_factor_increment(0.7, 0.0, 200.0, 5.5, 100.0), 0.0
        )
        self.assertEqual(
            gust_load_factor_increment_si(0.7, RHO, 0.0, 100.0, 5.5, W_S), 0.0
        )

    def test_higher_wing_loading_reduces_increment(self):
        d1 = gust_load_factor_increment_si(0.7, RHO, 20.0, 100.0, 5.5, W_S)
        d2 = gust_load_factor_increment_si(0.7, RHO, 20.0, 100.0, 5.5, 2.0 * W_S)
        self.assertAlmostEqual(d2 / d1, 0.5, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gust_load_factor_increment(0.0, 66.0, 200.0, 5.5, 100.0)
        with self.assertRaises(ValueError):
            gust_load_factor_increment(0.7, -1.0, 200.0, 5.5, 100.0)
        with self.assertRaises(ValueError):
            gust_load_factor_increment(0.7, 66.0, 0.0, 5.5, 100.0)
        with self.assertRaises(ValueError):
            gust_load_factor_increment(0.7, 66.0, 200.0, 0.0, 100.0)
        with self.assertRaises(ValueError):
            gust_load_factor_increment(0.7, 66.0, 200.0, 5.5, 0.0)
        with self.assertRaises(ValueError):
            gust_load_factor_increment_si(0.7, 0.0, 20.0, 100.0, 5.5, W_S)


class EnvelopeVerdictTests(unittest.TestCase):
    def test_transport_nominal_verdict(self):
        # Corner 116.6 < VNE 220; 1 + 0.79 < 2.5; limits +2.5 / -1.0.
        v = envelope_verdict(116.6, 220.0, 0.79,
                             TRANSPORT_POSITIVE_LIMIT, TRANSPORT_NEGATIVE_LIMIT)
        self.assertTrue(v["corner_within_placard"])
        self.assertTrue(v["gust_within_maneuver"])
        self.assertTrue(v["transport_limits_ok"])
        self.assertTrue(v["ok"])

    def test_corner_above_placard_fails(self):
        v = envelope_verdict(250.0, 220.0, 0.79,
                             TRANSPORT_POSITIVE_LIMIT, TRANSPORT_NEGATIVE_LIMIT)
        self.assertFalse(v["corner_within_placard"])
        self.assertFalse(v["ok"])

    def test_gust_line_above_maneuver_fails(self):
        # 1 + 1.6 = 2.6 > 2.5: the gust case would size the structure.
        v = envelope_verdict(116.6, 220.0, 1.6,
                             TRANSPORT_POSITIVE_LIMIT, TRANSPORT_NEGATIVE_LIMIT)
        self.assertFalse(v["gust_within_maneuver"])
        self.assertFalse(v["ok"])

    def test_non_transport_positive_limit_fails(self):
        v = envelope_verdict(116.6, 220.0, 0.79, 3.8, TRANSPORT_NEGATIVE_LIMIT)
        self.assertFalse(v["transport_limits_ok"])
        self.assertFalse(v["ok"])

    def test_non_transport_negative_limit_fails(self):
        v = envelope_verdict(116.6, 220.0, 0.79, TRANSPORT_POSITIVE_LIMIT, -1.5)
        self.assertFalse(v["transport_limits_ok"])
        self.assertFalse(v["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            envelope_verdict(0.0, 220.0, 0.79,
                             TRANSPORT_POSITIVE_LIMIT, TRANSPORT_NEGATIVE_LIMIT)
        with self.assertRaises(ValueError):
            envelope_verdict(116.6, 0.0, 0.79,
                             TRANSPORT_POSITIVE_LIMIT, TRANSPORT_NEGATIVE_LIMIT)
        with self.assertRaises(ValueError):
            envelope_verdict(116.6, 220.0, -0.1,
                             TRANSPORT_POSITIVE_LIMIT, TRANSPORT_NEGATIVE_LIMIT)
        with self.assertRaises(ValueError):
            envelope_verdict(116.6, 220.0, 0.79, 1.0, TRANSPORT_NEGATIVE_LIMIT)
        with self.assertRaises(ValueError):
            envelope_verdict(116.6, 220.0, 0.79, TRANSPORT_POSITIVE_LIMIT, 0.0)


if __name__ == "__main__":
    unittest.main()
