#!/usr/bin/env python3
"""Gate 3 contract test: lamina failure criteria (Tsai-Wu, Tsai-Hill,
max-stress).

Exercises scripts/failure_criteria_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3: per-criterion failure
indices, the combined failure verdict, and ValueError on invalid
allowables. Units: MPa everywhere.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import failure_criteria_logic as fc  # noqa: E402

# Unidirectional carbon/epoxy ply allowables (MPa), typical textbook
# values for a 1500 MPa-class fiber (paraphrase, common knowledge).
XT = 1500.0
XC = 1200.0
YT = 50.0
YC = 200.0
S = 70.0

ALLOWABLES = {"Xt": XT, "Xc": XC, "Yt": YT, "Yc": YC, "S": S}


class TsaiWuTest(unittest.TestCase):
    def test_uniaxial_tension_at_allowable_gives_one(self):
        # Physical check: pure fiber tension at Xt gives F.I. = 1 exactly.
        fi = fc.tsai_wu_index(XT, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 1.0, delta=1e-9)

    def test_pure_shear_at_allowable_gives_one(self):
        fi = fc.tsai_wu_index(0.0, 0.0, S, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 1.0, delta=1e-9)

    def test_low_stress_below_failure(self):
        fi = fc.tsai_wu_index(0.6 * XT, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertLess(fi, 1.0)

    def test_overload_fails(self):
        fi = fc.tsai_wu_index(1.1 * XT, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertGreaterEqual(fi, 1.0)

    def test_invalid_allowable_raises(self):
        with self.assertRaises(ValueError):
            fc.tsai_wu_index(0.0, 0.0, 0.0, 0.0, XC, YT, YC, S)
        with self.assertRaises(ValueError):
            fc.tsai_wu_index(0.0, 0.0, 0.0, XT, XC, YT, -YC, S)


class TsaiHillTest(unittest.TestCase):
    def test_uniaxial_tension_is_squared_ratio(self):
        fi = fc.tsai_hill_index(0.6 * XT, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 0.36, delta=1e-9)

    def test_pure_shear_at_allowable_gives_one(self):
        fi = fc.tsai_hill_index(0.0, 0.0, S, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 1.0, delta=1e-9)

    def test_overload_fails(self):
        fi = fc.tsai_hill_index(1.1 * XT, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertGreaterEqual(fi, 1.0)

    def test_invalid_allowable_raises(self):
        with self.assertRaises(ValueError):
            fc.tsai_hill_index(0.0, 0.0, 0.0, XT, XC, 0.0, YC, S)


class MaxStressTest(unittest.TestCase):
    def test_tension_uses_xt(self):
        fi = fc.max_stress_index(0.6 * XT, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 0.6, delta=1e-9)

    def test_compression_uses_xc(self):
        fi = fc.max_stress_index(-0.5 * XC, 0.0, 0.0, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 0.5, delta=1e-9)

    def test_transverse_compression_uses_yc(self):
        fi = fc.max_stress_index(0.0, -0.25 * YC, 0.0, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 0.25, delta=1e-9)

    def test_pure_shear_at_allowable_gives_one(self):
        fi = fc.max_stress_index(0.0, 0.0, S, XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 1.0, delta=1e-9)

    def test_takes_max_of_components(self):
        fi = fc.max_stress_index(0.2 * XT, 0.8 * YT, 0.5 * S,
                                 XT, XC, YT, YC, S)
        self.assertAlmostEqual(fi, 0.8, delta=1e-9)

    def test_invalid_allowable_raises(self):
        with self.assertRaises(ValueError):
            fc.max_stress_index(0.0, 0.0, 0.0, XT, XC, YT, YC, 0.0)


class VerdictTest(unittest.TestCase):
    def test_all_pass_under_load(self):
        v = fc.failure_verdict(0.6 * XT, 0.0, 0.0, ALLOWABLES)
        self.assertFalse(v["failure"])
        self.assertAlmostEqual(v["tsai_hill"], 0.36, delta=1e-9)
        self.assertAlmostEqual(v["max_stress"], 0.6, delta=1e-9)

    def test_boundary_index_of_one_is_failure(self):
        v = fc.failure_verdict(XT, 0.0, 0.0, ALLOWABLES)
        self.assertTrue(v["failure"])
        self.assertAlmostEqual(v["tsai_wu"], 1.0, delta=1e-9)

    def test_any_criterion_over_one_is_failure(self):
        v = fc.failure_verdict(0.0, 0.0, 2.0 * S, ALLOWABLES)
        self.assertTrue(v["failure"])
        self.assertAlmostEqual(v["tsai_wu"], 4.0, delta=1e-9)
        self.assertAlmostEqual(v["tsai_hill"], 4.0, delta=1e-9)
        self.assertAlmostEqual(v["max_stress"], 2.0, delta=1e-9)
        # Tie at the top resolves to the first criterion in the tuple.
        self.assertEqual(v["governing"], "tsai-wu")

    def test_invalid_allowables_dict_raises(self):
        bad = dict(ALLOWABLES)
        bad["S"] = -1.0
        with self.assertRaises(ValueError):
            fc.failure_verdict(0.0, 0.0, 0.0, bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
