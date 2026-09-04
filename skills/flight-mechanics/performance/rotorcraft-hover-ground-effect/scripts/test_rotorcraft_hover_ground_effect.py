"""Contract test for rotorcraft-hover-ground-effect logic.

Deterministic stdlib unittest, offline, runs via
`python3 scripts/test_rotorcraft_hover_ground_effect.py` and exits 0.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rotorcraft_hover_ground_effect_logic import (
    G0,
    K_DEFAULT,
    MIN_Z_RATIO,
    RHO_SL,
    disk_area,
    ground_effect_factor,
    hover_ground_effect,
    hover_induced_velocity,
    ige_induced_power,
    ige_total_power,
    max_hover_height,
    oge_total_power,
    power_margin,
)

# Worked-example operating point (module real outputs, 4 significant
# figures): R = 5.0 m, m = 2200 kg, z = 5.0 m (z/R = 1.0), rho = 1.225,
# sigma = 0.08, Cd0 = 0.012, Vtip = 220 m/s, k = 1.15.
R = 5.0
MASS = 2200.0
HEIGHT = 5.0
RHO = 1.225
SOLIDITY = 0.08
CD0 = 0.012
TIP_SPEED = 220.0
K = 1.15

AREA = math.pi * R ** 2                      # 78.53981633974483
THRUST = MASS * G0                           # 21574.63 N
V_H = 10.588725632796958                     # hover induced velocity, m/s
P_IDEAL = 228447.8376991102                  # ideal induced power, W
P_PROFILE = 122934.91876468362               # profile power, W
P_OGE = 385649.9321186603                    # OGE total power, W


class TestDiskArea(unittest.TestCase):
    def test_area_known_value_and_formula(self):
        self.assertAlmostEqual(disk_area(R), 78.5398, places=3)
        self.assertAlmostEqual(disk_area(3.0), math.pi * 9.0, places=12)

    def test_rejects_nonpositive_radius(self):
        for bad in (0.0, -1.0, -5.0):
            with self.assertRaises(ValueError):
                disk_area(bad)


class TestHoverInducedVelocity(unittest.TestCase):
    def test_anchor_within_band_and_value(self):
        v = hover_induced_velocity(THRUST, AREA, RHO)
        self.assertTrue(9.5 <= v <= 11.5, "v_h %s outside 9.5-11.5 m/s" % v)
        self.assertAlmostEqual(v, V_H, places=4)

    def test_closed_form_and_density_scaling(self):
        v = hover_induced_velocity(20000.0, 60.0, 1.2)
        self.assertAlmostEqual(v, math.sqrt(20000.0 / (2.0 * 1.2 * 60.0)),
                               places=12)
        thin = hover_induced_velocity(THRUST, AREA, 0.9)
        self.assertGreater(thin, hover_induced_velocity(THRUST, AREA, RHO))

    def test_rejects_nonpositive_inputs(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                hover_induced_velocity(bad, AREA, RHO)
            with self.assertRaises(ValueError):
                hover_induced_velocity(THRUST, bad, RHO)
            with self.assertRaises(ValueError):
                hover_induced_velocity(THRUST, AREA, bad)


class TestGroundEffectFactor(unittest.TestCase):
    def test_exact_anchors(self):
        self.assertEqual(ground_effect_factor(5.0, 5.0), 0.9375)   # z/R = 1
        self.assertEqual(ground_effect_factor(2.5, 5.0), 0.75)     # z/R = 0.5
        self.assertAlmostEqual(ground_effect_factor(10.0, 5.0), 0.984375,
                               places=10)                          # z/R = 2

    def test_cheeseman_formula_and_monotonicity(self):
        factors = []
        for h in (2.5, 3.0, 4.0, 6.0, 8.0, 25.0):
            expected = 1.0 - (R / (4.0 * h)) ** 2
            self.assertAlmostEqual(ground_effect_factor(h, R), expected,
                                   places=12)
            factors.append(ground_effect_factor(h, R))
        for low, high in zip(factors, factors[1:]):
            self.assertGreater(high, low)
        for f in factors:
            self.assertLess(f, 1.0)

    def test_rejects_below_floor_and_bad_radius(self):
        for h in (0.0, 1.0, 2.4, 2.49):
            with self.assertRaises(ValueError):
                ground_effect_factor(h, R)
        for r in (0.0, -5.0):
            with self.assertRaises(ValueError):
                ground_effect_factor(5.0, r)


class TestIgeInducedPower(unittest.TestCase):
    def test_product_and_identity(self):
        got = ige_induced_power(P_IDEAL, 0.9375)
        self.assertAlmostEqual(got, P_IDEAL * 0.9375, places=6)
        self.assertAlmostEqual(got, 214169.8478, places=1)
        self.assertAlmostEqual(ige_induced_power(P_IDEAL, 1.0), P_IDEAL,
                               places=9)

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            ige_induced_power(-1.0, 0.9)
        for bad in (0.0, -0.1, 1.0 + 1e-9, 1.5):
            with self.assertRaises(ValueError):
                ige_induced_power(P_IDEAL, bad)


class TestIgeTotalPower(unittest.TestCase):
    def test_anchor_within_band_and_value(self):
        p = ige_total_power(P_IDEAL, P_PROFILE, 0.9375, K)
        self.assertTrue(350000.0 <= p <= 390000.0,
                        "P_ige %s outside 350000-390000 W" % p)
        self.assertAlmostEqual(p, 369230.2438, places=1)

    def test_decomposition_profile_unchanged(self):
        expected = K * P_IDEAL * 0.9375 + P_PROFILE
        p = ige_total_power(P_IDEAL, P_PROFILE, 0.9375, K)
        self.assertAlmostEqual(p, expected, places=6)
        self.assertAlmostEqual(p - P_PROFILE, K * P_IDEAL * 0.9375,
                               places=6)

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            ige_total_power(-1.0, P_PROFILE, 0.9375, K)
        with self.assertRaises(ValueError):
            ige_total_power(P_IDEAL, -1.0, 0.9375, K)
        for bad_f in (0.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                ige_total_power(P_IDEAL, P_PROFILE, bad_f, K)
        for bad_k in (0.0, -1.15):
            with self.assertRaises(ValueError):
                ige_total_power(P_IDEAL, P_PROFILE, 0.9375, bad_k)


class TestPowerMargin(unittest.TestCase):
    def test_margin_values(self):
        self.assertAlmostEqual(power_margin(400000.0, P_OGE),
                               400000.0 - P_OGE, places=6)
        self.assertAlmostEqual(power_margin(360000.0, 369230.2438),
                               -9230.2438, places=1)
        self.assertEqual(power_margin(50000.0, 30000.0), 20000.0)

    def test_rejects_negative_inputs(self):
        with self.assertRaises(ValueError):
            power_margin(-1.0, 100.0)
        with self.assertRaises(ValueError):
            power_margin(100.0, -1.0)


class TestOgeTotalPower(unittest.TestCase):
    def test_anchor_within_band_and_value(self):
        p = oge_total_power(P_IDEAL, P_PROFILE, K)
        self.assertTrue(350000.0 <= p <= 430000.0,
                        "P_oge %s outside 350000-430000 W" % p)
        self.assertAlmostEqual(p, P_OGE, places=6)

    def test_ordering_and_unit_factor_recovery(self):
        ige = ige_total_power(P_IDEAL, P_PROFILE, 0.9375, K)
        self.assertLess(ige, oge_total_power(P_IDEAL, P_PROFILE, K))
        self.assertAlmostEqual(
            ige_total_power(P_IDEAL, P_PROFILE, 1.0, K),
            oge_total_power(P_IDEAL, P_PROFILE, K), places=9)

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            oge_total_power(-1.0, P_PROFILE, K)
        with self.assertRaises(ValueError):
            oge_total_power(P_IDEAL, -1.0, K)
        for bad_k in (0.0, -1.0):
            with self.assertRaises(ValueError):
                oge_total_power(P_IDEAL, P_PROFILE, bad_k)


class TestMaxHoverHeight(unittest.TestCase):
    def test_ceiling_anchor_360kw(self):
        z = max_hover_height(MASS, R, 360000.0, RHO, SOLIDITY, CD0,
                             TIP_SPEED, K)
        self.assertTrue(3.0 <= z <= 5.0, "ceiling %s outside 3-5 m" % z)
        self.assertAlmostEqual(z, 4.0004546, places=3)

    def test_none_at_and_above_oge_total(self):
        self.assertIsNone(max_hover_height(MASS, R, P_OGE))
        self.assertIsNone(max_hover_height(MASS, R, 400000.0, RHO, SOLIDITY,
                                           CD0, TIP_SPEED, K))
        self.assertIsNone(max_hover_height(MASS, R, 500000.0))

    def test_rejects_hover_impossible(self):
        # Below the IGE total at the lowest valid height (0.75 * k * P_ideal
        # + P_profile ~= 319972 W) hover is impossible even in ground effect.
        for avail in (0.0, 100000.0, 300000.0):
            with self.assertRaises(ValueError):
                max_hover_height(MASS, R, avail)

    def test_ceiling_grows_with_available_power(self):
        z1 = max_hover_height(MASS, R, 330000.0)
        z2 = max_hover_height(MASS, R, 350000.0)
        z3 = max_hover_height(MASS, R, 370000.0)
        self.assertGreater(z2, z1)
        self.assertGreater(z3, z2)

    def test_root_consistency(self):
        avail = 340000.0
        z = max_hover_height(MASS, R, avail)
        f = ground_effect_factor(z, R)
        self.assertAlmostEqual(
            ige_total_power(P_IDEAL, P_PROFILE, f, K), avail, delta=1.0)

    def test_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            max_hover_height(0.0, R, 360000.0)
        with self.assertRaises(ValueError):
            max_hover_height(-MASS, R, 360000.0)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, 0.0, 360000.0)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, R, -1.0)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, R, 360000.0, rho=-1.0)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, R, 360000.0, solidity=0.0)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, R, 360000.0, drag_coefficient=-0.1)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, R, 360000.0, tip_speed=0.0)
        with self.assertRaises(ValueError):
            max_hover_height(MASS, R, 360000.0, k=0.0)


class TestConvenienceChain(unittest.TestCase):
    def test_dict_exact_keys_and_primitive_values(self):
        res = hover_ground_effect(MASS, R, HEIGHT)
        self.assertEqual(
            set(res.keys()),
            {"thrust_N", "area_m2", "hover_induced_velocity",
             "ideal_induced_power_W", "profile_power_W",
             "ground_effect_factor", "ige_induced_power_W",
             "ige_total_power_W", "oge_total_power_W", "power_margin_W",
             "max_hover_height"},
        )
        self.assertAlmostEqual(res["thrust_N"], THRUST, places=6)
        self.assertAlmostEqual(res["area_m2"], AREA, places=9)
        self.assertAlmostEqual(res["hover_induced_velocity"], V_H, places=6)
        self.assertAlmostEqual(res["ideal_induced_power_W"], P_IDEAL,
                               places=4)
        self.assertAlmostEqual(res["profile_power_W"], P_PROFILE, places=4)
        self.assertEqual(res["ground_effect_factor"], 0.9375)
        self.assertAlmostEqual(res["ige_induced_power_W"], P_IDEAL * 0.9375,
                               places=4)
        self.assertAlmostEqual(res["ige_total_power_W"], 369230.2438,
                               places=1)
        self.assertAlmostEqual(res["oge_total_power_W"], P_OGE, places=4)

    def test_none_fields_without_available_power(self):
        res = hover_ground_effect(MASS, R, HEIGHT)
        self.assertIsNone(res["power_margin_W"])
        self.assertIsNone(res["max_hover_height"])

    def test_fields_with_available_power(self):
        res = hover_ground_effect(MASS, R, HEIGHT, available_power=360000.0)
        self.assertAlmostEqual(res["power_margin_W"], 360000.0 - 369230.2438,
                               places=1)
        self.assertTrue(3.0 <= res["max_hover_height"] <= 5.0)

    def test_above_oge_no_ceiling_positive_margin(self):
        res = hover_ground_effect(MASS, R, HEIGHT, available_power=400000.0)
        self.assertGreater(res["power_margin_W"], 0.0)
        self.assertIsNone(res["max_hover_height"])

    def test_lowest_valid_height_and_floor_rejection(self):
        low = hover_ground_effect(MASS, R, MIN_Z_RATIO * R)
        self.assertEqual(low["ground_effect_factor"], 0.75)
        for h in (0.0, 1.0, 2.49):
            with self.assertRaises(ValueError):
                hover_ground_effect(MASS, R, h)

    def test_rejects_bad_geometry_and_power(self):
        with self.assertRaises(ValueError):
            hover_ground_effect(0.0, R, HEIGHT)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, 0.0, HEIGHT)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, R, HEIGHT, rho=-1.0)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, R, HEIGHT, solidity=0.0)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, R, HEIGHT, drag_coefficient=-1.0)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, R, HEIGHT, tip_speed=0.0)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, R, HEIGHT, k=-1.0)
        with self.assertRaises(ValueError):
            hover_ground_effect(MASS, R, HEIGHT, available_power=-1.0)


class TestDeterminismAndPurity(unittest.TestCase):
    def test_run_to_run_identical(self):
        a = hover_ground_effect(MASS, R, HEIGHT, available_power=360000.0)
        b = hover_ground_effect(MASS, R, HEIGHT, available_power=360000.0)
        self.assertEqual(a, b)
        self.assertEqual(max_hover_height(MASS, R, 360000.0),
                         max_hover_height(MASS, R, 360000.0))

    def test_no_random_or_third_party_imports(self):
        logic_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "rotorcraft_hover_ground_effect_logic.py",
        )
        with open(logic_path) as fh:
            source = fh.read()
        for banned in ("random", "numpy", "scipy", "pandas"):
            self.assertNotIn(banned, source)
        self.assertIn("import math", source)


if __name__ == "__main__":
    unittest.main()
