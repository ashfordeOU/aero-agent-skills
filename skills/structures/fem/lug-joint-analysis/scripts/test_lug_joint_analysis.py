#!/usr/bin/env python3
"""Contract test for lug_joint_analysis_logic (deterministic, offline).

Run: python3 test_lug_joint_analysis.py
Covers the wave-34 spec anchors for the 7075-T6 worked lug, the
geometry identity at e/D = 1, the per-mode allowable-capacity margin
identities, the three-mode governing sweep over e/D and the full
ValueError validation list.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lug_joint_analysis_logic as lug

# 7075-T6 worked lug (SI).
D = 0.020          # hole diameter, m
T = 0.012          # lug thickness, m
E = 0.024          # edge distance, m (e/D = 1.2)
W = 0.048          # lug width, m (w = 2e round-end convention)
FTU = 572e6        # ultimate tension allowable, Pa
FSU = 331e6        # ultimate shear allowable, Pa
FBRU = 1050e6      # lug bearing ultimate allowable, Pa
P90 = 90000.0      # 90 kN working load
P200 = 200000.0    # 200 kN high load


def assert_rel(testcase, actual, expected, tol):
    """Assert relative closeness |actual - expected| <= tol * |expected|."""
    testcase.assertAlmostEqual(actual, expected,
                               delta=max(abs(expected) * tol, 1e-15))


def worked_stresses():
    """Stresses at the worked 90 kN anchor geometry."""
    return lug.lug_stresses(P90, D, T, W, E)


class WorkedExampleTests(unittest.TestCase):
    """Spec anchors: 7075-T6 lug at P = 90 kN."""

    def setUp(self):
        self.s = worked_stresses()
        self.m = lug.lug_margins(self.s, FTU, FSU, FBRU)
        self.a = lug.lug_analysis(P90, D, T, W, E, FTU, FSU, FBRU)

    def test_worked_bearing_stress(self):
        assert_rel(self, self.s["bearing_pa"], 375.0e6, 1e-6)

    def test_worked_net_tension_stress(self):
        assert_rel(self, self.s["net_tension_pa"], 267.857e6, 1e-6)

    def test_worked_tearout_stress(self):
        assert_rel(self, self.s["tearout_pa"], 171.881e6, 1e-6)

    def test_worked_tearout_plane_length(self):
        # Exact value 21.817424 mm; spec prints it rounded to 21.817 mm.
        assert_rel(self, self.s["tearout_plane_length_m"],
                   math.sqrt(E ** 2 - (D / 2.0) ** 2), 1e-12)
        self.assertAlmostEqual(self.s["tearout_plane_length_m"],
                               21.817e-3, delta=5e-7)

    def test_worked_margins_spec_rounded(self):
        self.assertAlmostEqual(self.m["bearing_margin"], 1.800, delta=5e-4)
        self.assertAlmostEqual(self.m["net_tension_margin"], 1.135,
                               delta=5e-4)
        self.assertAlmostEqual(self.m["tearout_margin"], 0.926, delta=5e-4)

    def test_worked_governing_mode_tearout(self):
        self.assertEqual(self.a["governing_mode"], "tearout")

    def test_worked_min_margin_matches_smallest_margin(self):
        smallest = min(self.m["bearing_margin"],
                       self.m["net_tension_margin"],
                       self.m["tearout_margin"])
        assert_rel(self, self.a["min_margin"], smallest, 1e-12)
        self.assertAlmostEqual(self.a["min_margin"], 0.926, delta=5e-4)

    def test_worked_passes_true(self):
        self.assertTrue(self.a["passes"])

    def test_worked_aux_fields(self):
        assert_rel(self, self.a["e_over_d"], 1.2, 1e-12)
        assert_rel(self, self.a["d_over_t"], 20.0 / 12.0, 1e-12)
        assert_rel(self, self.a["net_section_width_m"], 0.028, 1e-12)

    def test_high_load_200kn_fails(self):
        a = lug.lug_analysis(P200, D, T, W, E, FTU, FSU, FBRU)
        assert_rel(self, a["tearout_stress_pa"], 381.958e6, 1e-6)
        self.assertAlmostEqual(a["tearout_margin"], -0.133, delta=5e-4)
        self.assertEqual(a["governing_mode"], "tearout")
        self.assertFalse(a["passes"])
        self.assertLess(a["min_margin"], 0.0)


class GeometryAndValidationTests(unittest.TestCase):
    """Geometry identity, boundary behavior and ValueError rejections."""

    def test_geometry_identity_e_over_d_one(self):
        s = lug.lug_stresses(P90, D, T, 2.0 * D, D)
        assert_rel(self, s["tearout_plane_length_m"],
                   0.8660254037844386 * D, 1e-9)
        assert_rel(self, s["tearout_plane_length_m"],
                   math.sqrt(3.0) / 2.0 * D, 1e-12)
        assert_rel(self, s["net_section_width_m"], 2.0 * D - D, 1e-12)

    def test_negative_load_raises(self):
        with self.assertRaises(ValueError):
            lug.lug_stresses(-1.0, D, T, W, E)
        with self.assertRaises(ValueError):
            lug.lug_analysis(-5.0, D, T, W, E, FTU, FSU, FBRU)

    def test_non_positive_dimensions_raise(self):
        for name, value in (("diameter", D), ("thickness", T),
                            ("width", W), ("edge", E)):
            for bad in (0.0, -D):
                with self.subTest(name=name, bad=bad):
                    args = dict(diameter=D, thickness=T, width=W, edge=E)
                    args[name] = bad
                    with self.assertRaises(ValueError):
                        lug.lug_stresses(P90, args["diameter"],
                                         args["thickness"], args["width"],
                                         args["edge"])

    def test_degenerate_geometry_raises(self):
        with self.assertRaises(ValueError):
            lug.lug_stresses(P90, D, T, W, D / 2.0)      # e == D/2
        with self.assertRaises(ValueError):
            lug.lug_stresses(P90, D, T, W, D / 2.0 - 1e-3)
        with self.assertRaises(ValueError):
            lug.lug_stresses(P90, D, T, D, E)            # w == D
        with self.assertRaises(ValueError):
            lug.lug_stresses(P90, D, T, D - 1e-3, E)

    def test_geometry_just_past_degenerate_ok(self):
        s = lug.lug_stresses(P90, D, T, D + 1e-3, D / 2.0 + 1e-3)
        self.assertGreater(s["net_section_width_m"], 0.0)
        self.assertGreater(s["tearout_plane_length_m"], 0.0)

    def test_margins_reject_non_positive_allowables(self):
        for name, good in (("f_tu", FTU), ("f_su", FSU), ("f_bru", FBRU)):
            for bad in (0.0, -1.0):
                with self.subTest(name=name, bad=bad):
                    allow = {"f_tu": FTU, "f_su": FSU, "f_bru": FBRU}
                    allow[name] = bad
                    with self.assertRaises(ValueError):
                        lug.lug_margins(worked_stresses(), allow["f_tu"],
                                        allow["f_su"], allow["f_bru"])

    def test_capacity_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            lug.lug_allowable_capacity(0.0, T, E, FTU, FSU, FBRU)
        with self.assertRaises(ValueError):
            lug.lug_allowable_capacity(D, -T, E, FTU, FSU, FBRU)
        with self.assertRaises(ValueError):
            lug.lug_allowable_capacity(D, T, D / 2.0, FTU, FSU, FBRU)
        with self.assertRaises(ValueError):
            lug.lug_allowable_capacity(D, T, E, 0.0, FSU, FBRU)
        with self.assertRaises(ValueError):
            lug.lug_allowable_capacity(D, T, E, FTU, -FSU, FBRU)
        with self.assertRaises(ValueError):
            lug.lug_allowable_capacity(D, T, E, FTU, FSU, 0.0)

    def test_map_rejects_invalid_sweep_bounds(self):
        with self.assertRaises(ValueError):
            lug.lug_governing_map(D, T, FTU, FSU, FBRU, e_over_d_lo=0.5)
        with self.assertRaises(ValueError):
            lug.lug_governing_map(D, T, FTU, FSU, FBRU, steps=0)
        with self.assertRaises(ValueError):
            lug.lug_governing_map(D, T, 0.0, FSU, FBRU)

    def test_margins_are_allowable_over_applied_minus_one(self):
        s = worked_stresses()
        m = lug.lug_margins(s, FTU, FSU, FBRU)
        assert_rel(self, m["bearing_margin"],
                   FBRU / s["bearing_pa"] - 1.0, 1e-12)
        assert_rel(self, m["net_tension_margin"],
                   FTU / s["net_tension_pa"] - 1.0, 1e-12)
        assert_rel(self, m["tearout_margin"],
                   FSU / s["tearout_pa"] - 1.0, 1e-12)


class AnalysisDictTests(unittest.TestCase):
    """Convenience dict contract and cross-function consistency."""

    def test_convenience_dict_keys_exact(self):
        s_keys = set(worked_stresses().keys())
        self.assertEqual(s_keys, {"bearing_pa", "net_tension_pa",
                                  "tearout_pa", "tearout_plane_length_m",
                                  "net_section_width_m"})
        m_keys = set(lug.lug_margins(worked_stresses(), FTU, FSU,
                                     FBRU).keys())
        self.assertEqual(m_keys, {"bearing_margin", "net_tension_margin",
                                  "tearout_margin"})
        a = lug.lug_analysis(P90, D, T, W, E, FTU, FSU, FBRU)
        self.assertEqual(set(a.keys()), {
            "bearing_stress_pa", "net_tension_stress_pa",
            "tearout_stress_pa", "bearing_margin", "net_tension_margin",
            "tearout_margin", "governing_mode", "min_margin", "passes",
            "e_over_d", "d_over_t", "tearout_plane_length_m",
            "net_section_width_m"})

    def test_analysis_consistent_with_stresses_and_margins(self):
        a = lug.lug_analysis(P90, D, T, W, E, FTU, FSU, FBRU)
        s = worked_stresses()
        m = lug.lug_margins(s, FTU, FSU, FBRU)
        assert_rel(self, a["bearing_stress_pa"], s["bearing_pa"], 1e-15)
        assert_rel(self, a["net_tension_stress_pa"],
                   s["net_tension_pa"], 1e-15)
        assert_rel(self, a["tearout_stress_pa"], s["tearout_pa"], 1e-15)
        assert_rel(self, a["bearing_margin"], m["bearing_margin"], 1e-15)
        assert_rel(self, a["net_tension_margin"],
                   m["net_tension_margin"], 1e-15)
        assert_rel(self, a["tearout_margin"], m["tearout_margin"], 1e-15)


class AllowableCapacityTests(unittest.TestCase):
    """Per-mode capacities and the margin-zero identity."""

    def test_capacity_values_worked_geometry(self):
        cap = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        assert_rel(self, cap["bearing_capacity_n"], 252000.0, 1e-9)
        assert_rel(self, cap["net_tension_capacity_n"], 192192.0, 1e-9)
        assert_rel(self, cap["tearout_capacity_n"], 173317.6, 1e-5)
        self.assertEqual(cap["limiting_mode"], "tearout")
        assert_rel(self, cap["limiting_capacity_n"],
                   cap["tearout_capacity_n"], 1e-15)

    def test_capacity_equals_allowable_times_geometry_term(self):
        cap = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        l_te = math.sqrt(E ** 2 - (D / 2.0) ** 2)
        assert_rel(self, cap["bearing_capacity_n"],
                   FBRU * D * T, 1e-12)
        assert_rel(self, cap["net_tension_capacity_n"],
                   FTU * (2.0 * E - D) * T, 1e-12)
        assert_rel(self, cap["tearout_capacity_n"],
                   FSU * 2.0 * T * l_te, 1e-12)

    def test_bearing_capacity_margin_identity(self):
        cap = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        a = lug.lug_analysis(cap["bearing_capacity_n"], D, T, W, E,
                             FTU, FSU, FBRU)
        assert_rel(self, a["bearing_margin"], 0.0, 1e-9)

    def test_net_tension_capacity_margin_identity(self):
        cap = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        a = lug.lug_analysis(cap["net_tension_capacity_n"], D, T, W, E,
                             FTU, FSU, FBRU)
        assert_rel(self, a["net_tension_margin"], 0.0, 1e-9)

    def test_tearout_capacity_margin_identity(self):
        cap = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        a = lug.lug_analysis(cap["tearout_capacity_n"], D, T, W, E,
                             FTU, FSU, FBRU)
        assert_rel(self, a["tearout_margin"], 0.0, 1e-9)

    def test_limiting_mode_matches_analysis_governing_mode(self):
        cap = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        a = lug.lug_analysis(P90, D, T, W, E, FTU, FSU, FBRU)
        self.assertEqual(cap["limiting_mode"], a["governing_mode"])
        self.assertEqual(cap["limiting_mode"], "tearout")


class GoverningMapTests(unittest.TestCase):
    """Three-mode e/D sweep: short-lug tension, tearout, long-lug bearing."""

    def _rows(self):
        return lug.lug_governing_map(D, T, FTU, FSU, FBRU)

    def test_map_length_and_ratio_range(self):
        rows = self._rows()
        self.assertEqual(len(rows), 21)
        assert_rel(self, rows[0]["e_over_d"], 0.6, 1e-12)
        assert_rel(self, rows[-1]["e_over_d"], 2.5, 1e-12)

    def test_map_all_three_modes_govern(self):
        governing = {row["governing_mode"] for row in self._rows()}
        self.assertEqual(governing, {"net_tension", "tearout", "bearing"})

    def test_map_mode_bands_match_spec_ranges(self):
        rows = self._rows()
        seq = [row["governing_mode"] for row in rows]
        idx_tearout = seq.index("tearout")
        idx_bearing = seq.index("bearing")
        self.assertTrue(all(m == "net_tension" for m in seq[:idx_tearout]))
        self.assertTrue(all(m == "tearout"
                            for m in seq[idx_tearout:idx_bearing]))
        self.assertTrue(all(m == "bearing" for m in seq[idx_bearing:]))
        # Transition straddles e/D 1.03 (net below, tearout at 1.075) and
        # bearing appears at e/D 1.74 as the spec sweep states.
        self.assertLess(rows[idx_tearout - 1]["e_over_d"], 1.03)
        self.assertGreater(rows[idx_tearout]["e_over_d"], 1.03)
        self.assertAlmostEqual(rows[idx_bearing]["e_over_d"], 1.74,
                               delta=1e-9)

    def test_map_capacity_monotonic_non_decreasing(self):
        caps = [row["capacity_n"] for row in self._rows()]
        self.assertTrue(all(b >= a for a, b in zip(caps, caps[1:])))

    def test_map_bearing_capacity_constant_in_e_over_d(self):
        c1 = lug.lug_allowable_capacity(D, T, E, FTU, FSU, FBRU)
        c2 = lug.lug_allowable_capacity(D, T, 2.5 * D, FTU, FSU, FBRU)
        self.assertEqual(c1["bearing_capacity_n"],
                         c2["bearing_capacity_n"])
        assert_rel(self, self._rows()[-1]["capacity_n"], 252000.0, 1e-9)

    def test_map_tearout_sample_at_e_over_d_1_17(self):
        row = next(r for r in self._rows() if r["e_over_d"] == 1.17)
        self.assertEqual(row["governing_mode"], "tearout")
        assert_rel(self, row["capacity_n"], 168060.0, 1e-5)

    def test_map_deterministic_run_to_run(self):
        self.assertEqual(self._rows(), self._rows())
        self.assertEqual(lug.lug_analysis(P90, D, T, W, E, FTU, FSU,
                                          FBRU),
                         lug.lug_analysis(P90, D, T, W, E, FTU, FSU,
                                          FBRU))


if __name__ == "__main__":
    unittest.main()
