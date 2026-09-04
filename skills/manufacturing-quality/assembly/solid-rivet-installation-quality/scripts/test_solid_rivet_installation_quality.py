"""Contract test for solid-rivet-installation-quality (stdlib unittest).

Offline deterministic. Covers the worked-example anchors, band edges,
scaling laws, ValueError rejections and the combined verdict.
"""

import math
import unittest

from solid_rivet_installation_quality_logic import (
    COUNTERSUNK_ALLOWANCE_D,
    MAX_HOLE_CLEARANCE_MM,
    PROTRUDING_ALLOWANCE_D,
    SHOP_D_MAX_D,
    SHOP_D_MIN_D,
    SHOP_H_MAX_D,
    SHOP_H_MIN_D,
    SQUEEZE_FACTOR_DEFAULT,
    hole_fill_check,
    installation_verdict,
    select_rivet_length,
    shop_head_verdict,
    squeeze_force,
)


class TestSelectRivetLength(unittest.TestCase):
    def test_protruding_worked_anchor(self):
        res = select_rivet_length(6.0, 4.0, "protruding")
        self.assertAlmostEqual(res["allowance_mm"], 6.0, places=9)
        self.assertAlmostEqual(res["length_mm"], 12.0, places=9)
        self.assertAlmostEqual(res["allowance_mm"],
                               PROTRUDING_ALLOWANCE_D * 4.0, places=9)

    def test_countersunk_worked_anchor(self):
        res = select_rivet_length(6.0, 4.0, "countersunk")
        self.assertAlmostEqual(res["allowance_mm"], 3.2, places=9)
        self.assertAlmostEqual(res["length_mm"], 9.2, places=9)
        self.assertAlmostEqual(res["allowance_mm"],
                               COUNTERSUNK_ALLOWANCE_D * 4.0, places=9)

    def test_doubling_stack_adds_exact_stack_increment(self):
        base = select_rivet_length(6.0, 4.0, "protruding")
        doubled = select_rivet_length(12.0, 4.0, "protruding")
        self.assertAlmostEqual(doubled["length_mm"],
                               base["length_mm"] + 6.0, places=9)

    def test_dict_keys(self):
        self.assertEqual(
            set(select_rivet_length(6.0, 4.0, "protruding").keys()),
            {"allowance_mm", "length_mm"})

    def test_nonpositive_inputs_raise(self):
        for stack, dia in ((0.0, 4.0), (-2.0, 4.0), (6.0, 0.0), (6.0, -1.0)):
            with self.assertRaises(ValueError):
                select_rivet_length(stack, dia, "protruding")

    def test_bad_head_style_raises(self):
        for style in ("", "flush", "PROTRUDING", None):
            with self.assertRaises(ValueError):
                select_rivet_length(6.0, 4.0, style)


class TestShopHeadVerdict(unittest.TestCase):
    def test_good_head_worked_anchor(self):
        res = shop_head_verdict(5.8, 1.8, 4.0)
        self.assertAlmostEqual(res["d_over_d"], 1.45, places=12)
        self.assertAlmostEqual(res["h_over_d"], 0.45, places=12)
        self.assertTrue(res["ok"])

    def test_underdriven_head_worked_anchor(self):
        res = shop_head_verdict(5.0, 1.2, 4.0)
        self.assertAlmostEqual(res["d_over_d"], 1.25, places=12)
        self.assertAlmostEqual(res["h_over_d"], 0.30, places=12)
        self.assertFalse(res["ok"])

    def test_out_of_band_shapes_fail(self):
        wide = shop_head_verdict(1.6 * 4.0, 1.8, 4.0)
        tall = shop_head_verdict(5.8, 0.55 * 4.0, 4.0)
        low = shop_head_verdict(1.3 * 4.0, 0.35 * 4.0, 4.0)
        self.assertGreater(wide["d_over_d"], SHOP_D_MAX_D)
        self.assertGreater(tall["h_over_d"], SHOP_H_MAX_D)
        self.assertFalse(wide["ok"])
        self.assertFalse(tall["ok"])
        self.assertFalse(low["ok"])

    def test_band_edges_pass_inclusive(self):
        lo = shop_head_verdict(SHOP_D_MIN_D * 4.0, SHOP_H_MIN_D * 4.0, 4.0)
        hi = shop_head_verdict(SHOP_D_MAX_D * 4.0, SHOP_H_MAX_D * 4.0, 4.0)
        self.assertTrue(lo["ok"])
        self.assertTrue(hi["ok"])
        self.assertAlmostEqual(lo["d_over_d"], SHOP_D_MIN_D, places=12)
        self.assertAlmostEqual(lo["h_over_d"], SHOP_H_MIN_D, places=12)
        self.assertAlmostEqual(hi["d_over_d"], SHOP_D_MAX_D, places=12)
        self.assertAlmostEqual(hi["h_over_d"], SHOP_H_MAX_D, places=12)

    def test_band_symmetry_identity(self):
        # The band is symmetric around 1.45 d and 0.45 d; a head driven to
        # the exact midpoints passes with zero margin on both ratios.
        mid = shop_head_verdict(1.45 * 4.0, 0.45 * 4.0, 4.0)
        self.assertAlmostEqual(
            (SHOP_D_MIN_D + SHOP_D_MAX_D) / 2.0, 1.45, places=12)
        self.assertAlmostEqual(
            (SHOP_H_MIN_D + SHOP_H_MAX_D) / 2.0, 0.45, places=12)
        self.assertTrue(mid["ok"])
        self.assertAlmostEqual(mid["d_over_d"], 1.45, places=12)
        self.assertAlmostEqual(mid["h_over_d"], 0.45, places=12)

    def test_dict_keys(self):
        self.assertEqual(
            set(shop_head_verdict(5.8, 1.8, 4.0).keys()),
            {"d_over_d", "h_over_d", "ok"})

    def test_nonpositive_dimensions_raise(self):
        cases = ((0.0, 1.8, 4.0), (5.8, -0.5, 4.0), (5.8, 0.0, 4.0),
                 (5.8, 1.8, 0.0), (5.8, 1.8, -4.0))
        for args in cases:
            with self.assertRaises(ValueError):
                shop_head_verdict(*args)


class TestSqueezeForce(unittest.TestCase):
    def test_worked_anchor(self):
        res = squeeze_force(4.0, 275)
        self.assertAlmostEqual(res["area_mm2"], math.pi * 4.0, places=9)
        self.assertAlmostEqual(res["force_n"], 5183.6, delta=0.1)
        self.assertAlmostEqual(
            res["force_n"],
            SQUEEZE_FACTOR_DEFAULT * 275 * math.pi * 4.0, places=6)

    def test_scaling_laws(self):
        base = squeeze_force(4.0, 275)
        d2 = squeeze_force(8.0, 275)
        stress = squeeze_force(4.0, 550)
        factor = squeeze_force(4.0, 275, factor=3.0)
        self.assertAlmostEqual(d2["force_n"], 4.0 * base["force_n"],
                               places=6)
        self.assertAlmostEqual(d2["area_mm2"], 4.0 * base["area_mm2"],
                               places=9)
        self.assertAlmostEqual(stress["force_n"], 2.0 * base["force_n"],
                               places=6)
        self.assertAlmostEqual(factor["force_n"],
                               2.0 * base["force_n"], places=6)

    def test_default_factor_matches_constant(self):
        self.assertEqual(SQUEEZE_FACTOR_DEFAULT, 1.5)
        self.assertEqual(
            squeeze_force(4.0, 275)["force_n"],
            squeeze_force(4.0, 275, factor=1.5)["force_n"])

    def test_dict_keys(self):
        self.assertEqual(
            set(squeeze_force(4.0, 275).keys()),
            {"area_mm2", "force_n"})

    def test_nonpositive_inputs_raise(self):
        for args in ((0.0, 275), (-4.0, 275), (4.0, 0.0), (4.0, -275)):
            with self.assertRaises(ValueError):
                squeeze_force(*args)
        for factor in (0.0, -1.5):
            with self.assertRaises(ValueError):
                squeeze_force(4.0, 275, factor=factor)


class TestHoleFillCheck(unittest.TestCase):
    def test_ok_worked_anchor(self):
        res = hole_fill_check(4.08, 4.0)
        self.assertAlmostEqual(res["clearance_mm"], 0.08, places=9)
        self.assertTrue(res["ok"])

    def test_fail_worked_anchor(self):
        res = hole_fill_check(4.15, 4.0)
        self.assertAlmostEqual(res["clearance_mm"], 0.15, places=9)
        self.assertFalse(res["ok"])

    def test_exact_max_clearance_boundary_passes(self):
        res = hole_fill_check(4.1, 4.0)
        self.assertLessEqual(res["clearance_mm"], MAX_HOLE_CLEARANCE_MM)
        self.assertTrue(res["ok"])

    def test_custom_max_clearance(self):
        self.assertTrue(hole_fill_check(4.15, 4.0, max_clearance_mm=0.2)["ok"])
        self.assertFalse(hole_fill_check(4.15, 4.0)["ok"])
        self.assertFalse(
            hole_fill_check(4.3, 4.0, max_clearance_mm=0.25)["ok"])
        self.assertEqual(MAX_HOLE_CLEARANCE_MM, 0.1)

    def test_dict_keys(self):
        self.assertEqual(
            set(hole_fill_check(4.08, 4.0).keys()),
            {"clearance_mm", "ok"})

    def test_invalid_inputs_raise(self):
        # Interference (rivet > hole) is out of scope and must raise.
        with self.assertRaises(ValueError):
            hole_fill_check(4.0, 4.2)
        for args in ((0.0, 4.0), (4.0, 0.0), (-4.1, 4.0), (4.0, -1.0)):
            with self.assertRaises(ValueError):
                hole_fill_check(*args)
        with self.assertRaises(ValueError):
            hole_fill_check(4.08, 4.0, max_clearance_mm=-0.05)


class TestInstallationVerdict(unittest.TestCase):
    def test_good_installation_verdict(self):
        res = installation_verdict(6.0, 4.0, "protruding", 5.8, 1.8,
                                   5200.0, 275, 4.08)
        self.assertTrue(res["overall_ok"])
        self.assertAlmostEqual(
            res["selected_length"]["length_mm"], 12.0, places=9)
        self.assertTrue(res["shop_head"]["ok"])
        self.assertAlmostEqual(
            res["squeeze"]["force_n"], 5183.6, delta=0.1)
        self.assertAlmostEqual(
            res["squeeze"]["applied_force_n"], 5200.0, places=9)
        self.assertTrue(res["hole_fill"]["ok"])

    def test_bad_shop_head_fails_overall(self):
        res = installation_verdict(6.0, 4.0, "protruding", 5.0, 1.2,
                                   5200.0, 275, 4.08)
        self.assertFalse(res["overall_ok"])
        self.assertFalse(res["shop_head"]["ok"])

    def test_oversized_hole_fails_overall(self):
        res = installation_verdict(6.0, 4.0, "protruding", 5.8, 1.8,
                                   5200.0, 275, 4.15)
        self.assertFalse(res["overall_ok"])
        self.assertFalse(res["hole_fill"]["ok"])

    def test_subdict_keys_documented(self):
        res = installation_verdict(6.0, 4.0, "protruding", 5.8, 1.8,
                                   5200.0, 275, 4.08)
        self.assertEqual(
            set(res.keys()),
            {"selected_length", "shop_head", "squeeze", "hole_fill",
             "overall_ok"})
        self.assertEqual(
            set(res["squeeze"].keys()),
            {"area_mm2", "force_n", "applied_force_n"})

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            installation_verdict(6.0, 4.0, "flush", 5.8, 1.8,
                                 5200.0, 275, 4.08)
        with self.assertRaises(ValueError):
            installation_verdict(6.0, 4.0, "protruding", 5.8, 1.8,
                                 0.0, 275, 4.08)
        with self.assertRaises(ValueError):
            installation_verdict(6.0, 4.0, "protruding", 5.8, 1.8,
                                 5200.0, 275, 3.9)


class TestDeterminism(unittest.TestCase):
    def test_identical_floats_run_to_run(self):
        args = (6.0, 4.0, "protruding", 5.8, 1.8, 5200.0, 275, 4.08)
        self.assertEqual(installation_verdict(*args),
                         installation_verdict(*args))
        self.assertEqual(squeeze_force(4.0, 275), squeeze_force(4.0, 275))
        self.assertEqual(shop_head_verdict(5.8, 1.8, 4.0),
                         shop_head_verdict(5.8, 1.8, 4.0))


if __name__ == "__main__":
    unittest.main()
