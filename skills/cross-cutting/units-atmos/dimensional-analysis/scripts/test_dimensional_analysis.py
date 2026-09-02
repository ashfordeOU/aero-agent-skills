#!/usr/bin/env python3
"""Gate 3 contract test: dimensional analysis logic.

Exercises scripts/dimensional_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - equation
homogeneity checking, the Buckingham Pi theorem (rank, group count,
null-space groups, span against the classic sphere-drag groups Re and
C_D), the similarity numbers (Reynolds, Mach, Froude) with worked SI
values, dynamic similarity scaling (required model speed and full-scale
force), and ValueError on invalid inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dimensional_analysis_logic as da  # noqa: E402


def _rank(rows, tol=1e-9):
    """Rank of a list of row vectors (test-local Gaussian elimination)."""
    rows = [list(r) for r in rows]
    r = 0
    cols = len(rows[0]) if rows else 0
    for c in range(cols):
        pivot = None
        for i in range(r, len(rows)):
            if abs(rows[i][c]) > tol:
                pivot = i
                break
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        pv = rows[r][c]
        rows[r] = [x / pv for x in rows[r]]
        for i in range(len(rows)):
            if i != r and abs(rows[i][c]) > tol:
                f = rows[i][c]
                rows[i] = [x - f * y for x, y in zip(rows[i], rows[r])]
        r += 1
        if r == len(rows):
            break
    return r


class HomogeneityTest(unittest.TestCase):
    def test_bernoulli_terms_homogeneous(self):
        terms = [
            ("p", (1, -1, -2)),
            ("0.5 rho v^2", (1, -1, -2)),
            ("rho g h", (1, -1, -2)),
        ]
        ok, dims = da.check_homogeneity(terms)
        self.assertTrue(ok)
        self.assertEqual(dims, (1.0, -1.0, -2.0))

    def test_mixed_dimensions_not_homogeneous(self):
        terms = [
            ("p", (1, -1, -2)),
            ("rho v", (1, -2, -1)),
        ]
        ok, dims = da.check_homogeneity(terms)
        self.assertFalse(ok)
        self.assertEqual(dims, (1.0, -1.0, -2.0))

    def test_empty_terms_raise(self):
        with self.assertRaises(ValueError):
            da.check_homogeneity([])

    def test_ragged_exponents_raise(self):
        with self.assertRaises(ValueError):
            da.check_homogeneity([("a", (1,)), ("b", (1, 2))])

    def test_non_numeric_exponents_raise(self):
        with self.assertRaises(ValueError):
            da.check_homogeneity([("a", ("x", "y"))])

    def test_malformed_term_raises(self):
        with self.assertRaises(ValueError):
            da.check_homogeneity([("a",)])


class BuckinghamPiTest(unittest.TestCase):
    # Sphere drag: F, D, rho, V, mu over base dims M, L, T.
    SPHERE = {
        "F": (1, 1, -2),
        "D": (0, 1, 0),
        "rho": (1, -3, 0),
        "V": (0, 1, -1),
        "mu": (1, -1, -1),
    }
    NAMES = ["F", "D", "rho", "V", "mu"]

    def test_sphere_drag_group_count(self):
        res = da.buckingham_pi(self.SPHERE, base_dims=("M", "L", "T"))
        self.assertEqual(res["rank"], 3)
        self.assertEqual(res["n_variables"], 5)
        self.assertEqual(res["n_pi"], 2)
        self.assertEqual(res["base_dims"], ["M", "L", "T"])
        self.assertEqual(len(res["pi_groups"]), 2)

    def test_sphere_drag_groups_are_dimensionless(self):
        res = da.buckingham_pi(self.SPHERE, base_dims=("M", "L", "T"))
        a = [
            [self.SPHERE[n][b] for n in self.NAMES]
            for b in range(3)
        ]
        for group in res["pi_groups"]:
            vec = [group.get(n, 0.0) for n in self.NAMES]
            for row in a:
                self.assertAlmostEqual(
                    sum(x * y for x, y in zip(row, vec)), 0.0, places=9
                )

    def test_sphere_drag_span_contains_re_and_cd(self):
        res = da.buckingham_pi(self.SPHERE, base_dims=("M", "L", "T"))
        basis = [[g.get(n, 0.0) for n in self.NAMES] for g in res["pi_groups"]]
        self.assertEqual(_rank(basis), 2)
        # Re = rho V D / mu  ->  (F, D, rho, V, mu) exponents
        re_vec = [0.0, 1.0, 1.0, 1.0, -1.0]
        # C_D-like = F / (rho V^2 D^2) -> exponents (1, -2, -1, -2, 0)
        cd_vec = [1.0, -2.0, -1.0, -2.0, 0.0]
        for known in (re_vec, cd_vec):
            self.assertEqual(_rank(basis + [known]), 2)

    def test_single_variable_no_groups(self):
        res = da.buckingham_pi({"x": (1,)}, base_dims=("M",))
        self.assertEqual(res["rank"], 1)
        self.assertEqual(res["n_pi"], 0)
        self.assertEqual(res["pi_groups"], [])

    def test_two_variables_one_group(self):
        res = da.buckingham_pi({"a": (1,), "b": (2,)}, base_dims=("M",))
        self.assertEqual(res["rank"], 1)
        self.assertEqual(res["n_pi"], 1)
        self.assertEqual(res["pi_groups"], [{"a": 2.0, "b": -1.0}])

    def test_empty_variables_raise(self):
        with self.assertRaises(ValueError):
            da.buckingham_pi({})

    def test_base_dims_length_mismatch_raise(self):
        with self.assertRaises(ValueError):
            da.buckingham_pi({"x": (1, 1)}, base_dims=("M",))

    def test_non_numeric_exponents_raise(self):
        with self.assertRaises(ValueError):
            da.buckingham_pi({"x": ("a",)}, base_dims=("M",))


class SimilarityNumbersTest(unittest.TestCase):
    def test_reynolds_worked_case(self):
        # Sea level: rho 1.225 kg/m3, V 80 m/s, chord 2.0 m,
        # mu 1.781e-5 Pa.s -> Re about 1.10e7.
        re = da.reynolds_number(1.225, 80.0, 2.0, 1.781e-5)
        self.assertAlmostEqual(re, 11005053.0, delta=1.0)

    def test_mach_worked_case(self):
        m = da.mach_number(80.0, 340.3)
        self.assertAlmostEqual(m, 0.2350867, places=6)

    def test_mach_default_speed_of_sound(self):
        self.assertAlmostEqual(da.mach_number(da.SPEED_OF_SOUND_SL), 1.0,
                               places=12)

    def test_froude_worked_case(self):
        fr = da.froude_number(5.0, 2.5)
        self.assertAlmostEqual(fr, 1.00981, places=5)

    def test_reynolds_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            da.reynolds_number(1.225, 80.0, 2.0, 0.0)
        with self.assertRaises(ValueError):
            da.reynolds_number(-1.0, 80.0, 2.0, 1.781e-5)

    def test_mach_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            da.mach_number(80.0, 0.0)
        with self.assertRaises(ValueError):
            da.mach_number(-1.0, 340.3)

    def test_froude_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            da.froude_number(5.0, 0.0)
        with self.assertRaises(ValueError):
            da.froude_number(5.0, 2.5, 0.0)
        with self.assertRaises(ValueError):
            da.froude_number(-1.0, 2.5)


class SimilarityScalingTest(unittest.TestCase):
    def test_required_model_speed_same_fluid(self):
        # 1:10 model, same fluid: V_model = 10 * V_proto.
        self.assertAlmostEqual(da.required_model_speed(10.0, 80.0), 800.0,
                               places=9)

    def test_required_model_speed_with_viscosity_ratio(self):
        # nu_model / nu_proto = 15 adds another factor of 15.
        self.assertAlmostEqual(
            da.required_model_speed(10.0, 80.0, 15.0), 12000.0, places=6
        )

    def test_force_scaling_re_matched_same_fluid(self):
        # Model drag 12.5 N, 1:10 scale, V_model = 10 * V_proto, same
        # fluid: full-scale drag equals the model drag (12.5 N).
        self.assertAlmostEqual(
            da.force_scaling(12.5, 10.0, 1.0, 0.1), 12.5, places=9
        )

    def test_force_scaling_general_case(self):
        self.assertAlmostEqual(
            da.force_scaling(2.0, 5.0, 1.2, 0.5), 15.0, places=9
        )

    def test_required_model_speed_invalid_raise(self):
        with self.assertRaises(ValueError):
            da.required_model_speed(0.0, 80.0)
        with self.assertRaises(ValueError):
            da.required_model_speed(10.0, 80.0, -1.0)

    def test_force_scaling_invalid_raise(self):
        with self.assertRaises(ValueError):
            da.force_scaling(12.5, 0.0, 1.0, 0.1)
        with self.assertRaises(ValueError):
            da.force_scaling(-1.0, 10.0, 1.0, 0.1)
        with self.assertRaises(ValueError):
            da.force_scaling(12.5, 10.0, 1.0, 0.0)


if __name__ == "__main__":
    unittest.main()
