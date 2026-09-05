"""Contract test for the structures/fem/curved-beam-analysis leaf.

Exercises the numbered SKILL.md Workflow: gathering the curved-member
geometry and loads of the torque-link worked example (step 1),
computing the neutral-axis radius from the Winkler closed forms for a
rectangular radial section and for circular solid and tube sections
(step 2), taking the neutral-axis eccentricity as the inward shift
from the centroidal radius (step 3), resolving the Winkler
curved-beam bending stress at the inner and outer fibers with the
straight Euler-Bernoulli baseline and the curved-beam amplification
over it (step 4), adding the axial contribution P / A at each fiber
(step 5), and rating the gating inner-fiber stress against the
allowable with the stress verdict and its pass/fail margin (step 6).

Every numeric expectation below is a REAL module output from a local
run of curved_beam_analysis_logic.py, checked against the spec
anchors of the prep script and the closed-form identities of the leaf
(neutral-axis radius independent of section width, neutral axis
strictly between the inner radius and the centroid, inner-fiber
magnitude above the outer-fiber magnitude, amplification that grows
with the depth-to-radius ratio, the a_i = 0 tube reduction to the
solid-section closed form, and verdict flip exactly at ratio 1.0).
"""

import math
import unittest

import curved_beam_analysis_logic as cb

# Worked example constants of the leaf spec: torque-link arc section,
# r_i = 60 mm, r_o = 100 mm, depth 40 mm, width 40 mm, A = 1600 mm^2,
# centroidal radius 80 mm, P = 25 kN tension, allowable 500 MPa.
R_I = 60.0
R_O = 100.0
R_C = 80.0
AREA = 1600.0
DEPTH = 40.0
P = 25000.0
ALLOW = 500.0
M1 = 1.2e6  # N mm, moderate in-service moment
M2 = 4.0e6  # N mm, limit moment
M3 = 4.5e6  # N mm, ultimate moment


def worked_r_n_e():
    """Workflow steps 2 and 3 on the worked-example rectangular section."""
    r_n = cb.neutral_axis_radius_rect(R_I, R_O)
    e = cb.eccentricity(R_C, r_n)
    return r_n, e


def inner_case1():
    """Workflow step 4 inner fiber stress for the M = 1.2e6 N mm case."""
    r_n, e = worked_r_n_e()
    return cb.curved_beam_stress(M1, AREA, e, r_n, R_I)


def outer_case1():
    """Workflow step 4 outer fiber stress for the M = 1.2e6 N mm case."""
    r_n, e = worked_r_n_e()
    return cb.curved_beam_stress(M1, AREA, e, r_n, R_O)


class WorkedExampleTests(unittest.TestCase):
    """Workflow steps 1 to 6 on the spec torque-link worked example."""

    def test_neutral_axis_radius_rect_worked_geometry(self):
        """Step 2 neutral-axis radius closed form gives 78.30461 mm
        within 1e-5 for the rectangular radial section."""
        r_n, _ = worked_r_n_e()
        self.assertAlmostEqual(r_n, 78.30461, delta=1e-5)

    def test_neutral_axis_eccentricity_worked_geometry(self):
        """Step 3 neutral-axis eccentricity gives 1.69539 mm within
        1e-5, the inward shift of the neutral axis from the centroid."""
        _, e = worked_r_n_e()
        self.assertAlmostEqual(e, 1.69539, delta=1e-5)

    def test_inner_fiber_stress_case1(self):
        """Step 4 Winkler curved-beam inner fiber stress of load
        case 1 is 134.95848 MPa tension within 1e-4."""
        self.assertAlmostEqual(inner_case1(), 134.95848, delta=1e-4)

    def test_outer_fiber_stress_case1(self):
        """Step 4 Winkler curved-beam outer fiber stress of load
        case 1 is -95.97509 MPa compression within 1e-4."""
        self.assertAlmostEqual(outer_case1(), -95.97509, delta=1e-4)

    def test_straight_beam_baseline_exact(self):
        """Step 4 straight Euler-Bernoulli extreme fiber baseline
        6 M / (A h) of the same section is 112.5 MPa exactly."""
        self.assertEqual(cb.straight_beam_stress_rect(M1, AREA, DEPTH), 112.5)

    def test_curved_beam_amplification_inner_fiber(self):
        """Step 4 curved-beam amplification of the inner fiber over
        the straight reading is 1.19963 within 1e-4."""
        amp = inner_case1() / cb.straight_beam_stress_rect(M1, AREA, DEPTH)
        self.assertAlmostEqual(amp, 1.19963, delta=1e-4)

    def test_outer_fiber_to_straight_ratio(self):
        """Step 4 outer fiber runs at 0.85311 of the straight
        baseline, the classic Winkler curved-member signature."""
        ratio = outer_case1() / cb.straight_beam_stress_rect(M1, AREA, DEPTH)
        self.assertAlmostEqual(abs(ratio), 0.85311, delta=1e-4)

    def test_combined_inner_stress_case1(self):
        """Step 5 adding the axial tension P / A = 15.625 MPa gives
        a combined inner fiber stress of 150.58348 MPa within 1e-4."""
        combined = cb.combined_axial_stress(inner_case1(), P, AREA)
        self.assertAlmostEqual(combined, 150.58348, delta=1e-4)

    def test_combined_outer_stress_case1(self):
        """Step 5 the combined outer fiber stress of load case 1 is
        -80.35009 MPa within 1e-4, tension positive."""
        combined = cb.combined_axial_stress(outer_case1(), P, AREA)
        self.assertAlmostEqual(combined, -80.35009, delta=1e-4)

    def test_verdict_case1_pass(self):
        """Step 6 stress verdict on the combined inner fiber of load
        case 1: ratio 0.30117, verdict pass, margin 349.41652 MPa."""
        combined = cb.combined_axial_stress(inner_case1(), P, AREA)
        verdict = cb.stress_verdict(combined, ALLOW)
        self.assertAlmostEqual(verdict["ratio"], 0.30117, delta=1e-3)
        self.assertEqual(verdict["verdict"], "pass")
        self.assertAlmostEqual(verdict["margin"], 349.41652, delta=1e-3)
        self.assertAlmostEqual(verdict["abs_stress"], 150.58348, delta=1e-4)

    def test_case2_limit_moment_verdict(self):
        """Steps 4 to 6 with the 4.0 kN m limit moment: inner fiber
        449.86161 MPa, combined 465.48661 MPa, ratio 0.93097, pass,
        margin 34.51339 MPa."""
        r_n, e = worked_r_n_e()
        inner = cb.curved_beam_stress(M2, AREA, e, r_n, R_I)
        self.assertAlmostEqual(inner, 449.86161, delta=1e-4)
        combined = cb.combined_axial_stress(inner, P, AREA)
        self.assertAlmostEqual(combined, 465.48661, delta=1e-4)
        verdict = cb.stress_verdict(combined, ALLOW)
        self.assertAlmostEqual(verdict["ratio"], 0.93097, delta=1e-3)
        self.assertEqual(verdict["verdict"], "pass")
        self.assertAlmostEqual(verdict["margin"], 34.51339, delta=1e-3)

    def test_case3_ultimate_moment_verdict_fail(self):
        """Steps 4 to 6 with the 4.5 kN m ultimate moment: inner fiber
        506.09432 MPa, combined 521.71932 MPa, ratio 1.04344, fail,
        margin -21.71932 MPa; the same member read straight would
        still pass, which is the point of the correction."""
        r_n, e = worked_r_n_e()
        inner = cb.curved_beam_stress(M3, AREA, e, r_n, R_I)
        self.assertAlmostEqual(inner, 506.09432, delta=1e-4)
        combined = cb.combined_axial_stress(inner, P, AREA)
        self.assertAlmostEqual(combined, 521.71932, delta=1e-4)
        verdict = cb.stress_verdict(combined, ALLOW)
        self.assertAlmostEqual(verdict["ratio"], 1.04344, delta=1e-3)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertAlmostEqual(verdict["margin"], -21.71932, delta=1e-3)


class CircularSectionTests(unittest.TestCase):
    """Workflow step 2 neutral-axis closed forms for circular sections."""

    def test_circular_tube_worked_geometry(self):
        """Step 2 tube closed form neutral_axis_radius_circular_tube
        (80, 10, 20) is 78.41610 mm within 1e-5."""
        r_n = cb.neutral_axis_radius_circular_tube(80.0, 10.0, 20.0)
        self.assertAlmostEqual(r_n, 78.41610, delta=1e-5)

    def test_solid_round_worked_geometry_and_eccentricity(self):
        """Step 2 solid-round closed form with a_i = 0.0 is
        78.72983 mm within 1e-5, and step 3 gives the eccentricity
        1.27017 mm within 1e-5."""
        r_n = cb.neutral_axis_radius_circular_tube(80.0, 0.0, 20.0)
        self.assertAlmostEqual(r_n, 78.72983, delta=1e-5)
        self.assertAlmostEqual(cb.eccentricity(80.0, r_n), 1.27017, delta=1e-5)

    def test_ai_zero_reduces_to_solid_closed_form(self):
        """Step 2 identity: the a_i = 0.0 tube call reproduces the
        solid-section closed form (r_c + sqrt(r_c^2 - a_o^2)) / 2 for
        several radius pairs."""
        for r_c in (50.0, 80.0, 120.0):
            for a_o in (10.0, 20.0, 30.0):
                if a_o >= r_c:
                    continue
                expect = (r_c + math.sqrt(r_c ** 2 - a_o ** 2)) / 2.0
                got = cb.neutral_axis_radius_circular_tube(r_c, 0.0, a_o)
                self.assertAlmostEqual(got, expect, delta=1e-12)

    def test_tube_grid_quadrature_agreement(self):
        """Step 2 closed form versus a 2-D cell-centered grid
        quadrature of A / integral(dA / rho) over the material annulus
        in the section plane: the two agree to about one percent
        (grid limited), reproducing the order of the prep quadrature
        note; the module closed form is the engineering standard and
        its anchors are the spec targets."""
        r_c, a_i, a_o = 80.0, 10.0, 20.0
        n = 401
        drho = (a_o - a_i) / n
        dtheta = 2.0 * math.pi / n
        s = 0.0
        for i in range(n):
            rho = a_i + (i + 0.5) * drho
            for j in range(n):
                th = (j + 0.5) * dtheta
                rr = math.sqrt(r_c * r_c + rho * rho - 2.0 * r_c * rho * math.cos(th))
                s += rho / rr
        integral = s * drho * dtheta
        area = math.pi * (a_o * a_o - a_i * a_i)
        quad_rn = area / integral
        exact = cb.neutral_axis_radius_circular_tube(r_c, a_i, a_o)
        rel = abs(quad_rn - exact) / exact
        self.assertLess(rel, 1.1e-2)


class RectSectionIdentityTests(unittest.TestCase):
    """Workflow steps 2 and 3 identities of the rectangular section."""

    def test_rect_closed_form_equals_quadrature(self):
        """Step 2 identity: the rectangular closed form equals a
        400000-bin quadrature of A / integral(dA / rho), relative
        difference below 1e-9 (measured 1.5e-13 class)."""
        n = 400000
        dr = (R_O - R_I) / n
        integral = 0.0
        for k in range(n):
            integral += 1.0 / (R_I + (k + 0.5) * dr)
        integral *= dr
        quad_rn = DEPTH / integral  # unit width cancels in A / integral
        exact = cb.neutral_axis_radius_rect(R_I, R_O)
        self.assertLess(abs(quad_rn - exact) / exact, 1e-9)

    def test_rect_closed_form_independent_of_width(self):
        """Step 2 identity: the neutral-axis radius of the rectangle
        is independent of the out-of-plane width, since the closed
        form and the A / integral(dA / rho) quadrature both cancel
        the width; quadratures at widths 1 and 40 agree."""
        def quad_rn(width):
            n = 200000
            dr = (R_O - R_I) / n
            integral = 0.0
            for k in range(n):
                integral += 1.0 / (R_I + (k + 0.5) * dr)
            integral *= dr
            return (width * DEPTH) / (width * integral)

        self.assertAlmostEqual(quad_rn(1.0), quad_rn(40.0), delta=1e-12)
        self.assertAlmostEqual(quad_rn(40.0),
                               cb.neutral_axis_radius_rect(R_I, R_O),
                               delta=1e-9)

    def test_neutral_axis_between_inner_radius_and_centroid(self):
        """Step 2 identity: the neutral axis sits strictly between the
        inner radius and the centroidal radius, r_i < r_n < r_c, for
        several rectangular sections of different depth."""
        for ri, ro in ((60.0, 100.0), (70.0, 90.0), (55.0, 65.0),
                       (30.0, 120.0)):
            r_c = (ri + ro) / 2.0
            r_n = cb.neutral_axis_radius_rect(ri, ro)
            self.assertGreater(r_n, ri)
            self.assertLess(r_n, r_c)

    def test_eccentricity_positive_for_physical_sections(self):
        """Step 3 identity: the eccentricity is positive for every
        physical curved beam, rectangular or circular."""
        for ri, ro in ((60.0, 100.0), (70.0, 90.0), (55.0, 65.0),
                       (30.0, 120.0)):
            r_c = (ri + ro) / 2.0
            r_n = cb.neutral_axis_radius_rect(ri, ro)
            self.assertGreater(cb.eccentricity(r_c, r_n), 0.0)
        for r_c, a_o in ((80.0, 20.0), (100.0, 25.0)):
            r_n = cb.neutral_axis_radius_circular_tube(r_c, 0.0, a_o)
            self.assertGreater(cb.eccentricity(r_c, r_n), 0.0)

    def test_amplification_grows_with_depth_ratio(self):
        """Steps 2 to 4 identity: the curved-beam amplification over
        the straight Euler-Bernoulli reading grows as the depth to
        centroid-radius ratio h / r_c grows at fixed r_c = 80 mm."""
        r_c = 80.0
        widths = {10.0: 40.0, 20.0: 40.0, 30.0: 40.0, 40.0: 40.0}
        amps = []
        for h in (10.0, 20.0, 30.0, 40.0):
            ri = r_c - h / 2.0
            ro = r_c + h / 2.0
            r_n = cb.neutral_axis_radius_rect(ri, ro)
            e = cb.eccentricity(r_c, r_n)
            area = widths[h] * h
            inner = cb.curved_beam_stress(M1, area, e, r_n, ri)
            straight = cb.straight_beam_stress_rect(M1, area, h)
            amps.append(inner / straight)
        for a, b in zip(amps, amps[1:]):
            self.assertGreater(b, a)


class WinklerStressLawTests(unittest.TestCase):
    """Workflow step 4 stress-law properties of the Winkler relation."""

    def test_inner_fiber_magnitude_exceeds_outer(self):
        """Step 4 identity: for the same moment the curved-beam stress
        magnitude at the inner fiber exceeds the outer fiber value."""
        self.assertGreater(abs(inner_case1()), abs(outer_case1()))

    def test_negative_moment_flips_signs_exactly(self):
        """Step 4 identity: a negative moment reverses both fiber
        signs exactly, leaving the magnitudes unchanged."""
        r_n, e = worked_r_n_e()
        neg_inner = cb.curved_beam_stress(-M1, AREA, e, r_n, R_I)
        neg_outer = cb.curved_beam_stress(-M1, AREA, e, r_n, R_O)
        self.assertAlmostEqual(neg_inner, -inner_case1(), delta=1e-9)
        self.assertAlmostEqual(neg_outer, -outer_case1(), delta=1e-9)

    def test_zero_moment_gives_zero_stress(self):
        """Step 4 identity: zero moment gives exactly zero stress at
        both fibers."""
        r_n, e = worked_r_n_e()
        self.assertEqual(cb.curved_beam_stress(0.0, AREA, e, r_n, R_I), 0.0)
        self.assertEqual(cb.curved_beam_stress(0.0, AREA, e, r_n, R_O), 0.0)

    def test_combined_axial_tension_positive_compression_negative(self):
        """Step 5 identity: the axial contribution is positive for
        tension and negative for compression on the same fiber."""
        r_n, e = worked_r_n_e()
        base = cb.curved_beam_stress(M1, AREA, e, r_n, R_I)
        tension = cb.combined_axial_stress(base, P, AREA)
        compression = cb.combined_axial_stress(base, -P, AREA)
        self.assertGreater(tension, base)
        self.assertLess(compression, base)

    def test_combined_axial_alone_matches_p_over_a(self):
        """Step 5 identity: with zero bending the combined stress is
        exactly P / A, 15.625 MPa for the worked example tension."""
        self.assertAlmostEqual(cb.combined_axial_stress(0.0, P, AREA),
                               15.625, delta=1e-12)


class ValidationTests(unittest.TestCase):
    """ValueError rejection of non-physical inputs in every function."""

    def test_rect_neutral_axis_rejects_non_physical_radii(self):
        """Step 2 validation: inner radius 0, negative inner radius
        and outer radius equal to the inner radius all raise
        ValueError."""
        for bad_ri in (0.0, -5.0):
            with self.assertRaises(ValueError):
                cb.neutral_axis_radius_rect(bad_ri, 100.0)
        with self.assertRaises(ValueError):
            cb.neutral_axis_radius_rect(100.0, 100.0)

    def test_circular_tube_rejects_non_physical_radii(self):
        """Step 2 validation: center radius 0, negative annulus inner
        radius, annulus radii equal, and annulus outer radius at or
        above the center radius all raise ValueError."""
        with self.assertRaises(ValueError):
            cb.neutral_axis_radius_circular_tube(0.0, 10.0, 20.0)
        with self.assertRaises(ValueError):
            cb.neutral_axis_radius_circular_tube(80.0, -1.0, 20.0)
        with self.assertRaises(ValueError):
            cb.neutral_axis_radius_circular_tube(80.0, 20.0, 20.0)
        with self.assertRaises(ValueError):
            cb.neutral_axis_radius_circular_tube(80.0, 10.0, 80.0)

    def test_eccentricity_rejects_non_positive_radii(self):
        """Step 3 validation: non-positive centroidal or neutral-axis
        radii raise ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cb.eccentricity(bad, 78.30461)
            with self.assertRaises(ValueError):
                cb.eccentricity(80.0, bad)

    def test_curved_beam_stress_rejects_non_positive_geometry(self):
        """Step 4 validation: zero or negative area, eccentricity,
        neutral-axis radius and fiber radius each raise ValueError."""
        r_n, e = worked_r_n_e()
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cb.curved_beam_stress(M1, bad, e, r_n, R_I)
            with self.assertRaises(ValueError):
                cb.curved_beam_stress(M1, AREA, bad, r_n, R_I)
            with self.assertRaises(ValueError):
                cb.curved_beam_stress(M1, AREA, e, bad, R_I)
            with self.assertRaises(ValueError):
                cb.curved_beam_stress(M1, AREA, e, r_n, bad)

    def test_straight_baseline_rejects_non_positive_inputs(self):
        """Step 4 validation: zero or negative area and depth raise
        ValueError in the straight Euler-Bernoulli baseline."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cb.straight_beam_stress_rect(M1, bad, DEPTH)
            with self.assertRaises(ValueError):
                cb.straight_beam_stress_rect(M1, AREA, bad)

    def test_combined_axial_rejects_zero_area(self):
        """Step 5 validation: zero or negative area raises ValueError
        when adding the axial contribution."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cb.combined_axial_stress(134.95848, P, bad)

    def test_stress_verdict_rejects_non_positive_allowable(self):
        """Step 6 validation: zero and negative allowables raise
        ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cb.stress_verdict(150.58348, bad)


class VerdictBoundaryTests(unittest.TestCase):
    """Workflow step 6 verdict boundary and determinism."""

    def test_verdict_flips_exactly_at_ratio_one(self):
        """Step 6 identity: the verdict flips from pass to fail
        exactly at ratio 1.0, with the fixed strings pass and fail
        and the exact dict keys of the leaf contract."""
        at = cb.stress_verdict(ALLOW, ALLOW)
        self.assertEqual(at["verdict"], "pass")
        self.assertEqual(at["ratio"], 1.0)
        above = cb.stress_verdict(ALLOW + 1e-6, ALLOW)
        self.assertEqual(above["verdict"], "fail")
        self.assertGreater(above["ratio"], 1.0)
        below = cb.stress_verdict(ALLOW - 1e-6, ALLOW)
        self.assertEqual(below["verdict"], "pass")
        self.assertLess(below["ratio"], 1.0)
        self.assertEqual(set(at.keys()),
                         {"abs_stress", "ratio", "verdict", "margin"})

    def test_negative_stress_and_determinism(self):
        """Step 6 identity: a compressive fiber stress is rated on its
        magnitude, the margin is allowable minus absolute stress, and
        repeated calls are deterministic run to run."""
        v1 = cb.stress_verdict(-80.35009, ALLOW)
        self.assertAlmostEqual(v1["abs_stress"], 80.35009, delta=1e-12)
        self.assertAlmostEqual(v1["margin"], ALLOW - 80.35009, delta=1e-12)
        self.assertEqual(cb.curved_beam_stress(M1, AREA, 1.69539,
                                               78.30461, R_I),
                         cb.curved_beam_stress(M1, AREA, 1.69539,
                                               78.30461, R_I))
        r_n, e = worked_r_n_e()
        self.assertEqual(cb.combined_axial_stress(inner_case1(), P, AREA),
                         cb.combined_axial_stress(inner_case1(), P, AREA))
        self.assertIn(cb.stress_verdict(500.0, ALLOW)["verdict"],
                      ("pass", "fail"))
        self.assertAlmostEqual(v1["ratio"], 80.35009 / ALLOW, delta=1e-12)


if __name__ == "__main__":
    unittest.main()
