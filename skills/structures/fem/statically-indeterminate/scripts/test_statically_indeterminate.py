"""Contract test for the structures/fem/statically-indeterminate leaf.

Exercises every numbered step of the SKILL.md workflow for elastic
redundancy analysis of statically indeterminate beams, continuous beams
and the symmetric no-sway fixed-base frame: step 2 fixed-end moments of
the standard load cases (uniform w*L**2/12 and central P*L/8 hogging at
both fixed ends), step 3 Clapeyron load terms of the simple-span free
moment diagrams, step 4 consistent deformation (force method) on the
propped cantilever with the flexibility coefficient f_BB = L**3/(3*E*I),
the released-cantilever deflections and the carry-over identity of the
released end, step 5 interior support moments by the three-moment
(Clapeyron) equation on the two-span and three-span continuous beams,
step 6 support reactions from the support moments with the equilibrium
sum checks, step 7 the moment distribution (Hardy-Cross) cross-check
with the stiffness distribution factors and the 1/2 carry-over factor,
step 8 slope-deflection member end moments and joint rotations with the
clockwise-positive convention, step 9 the fixed-base portal frame under
a central beam load by moment distribution over the top joints
cross-checked by the direct joint-equation solve, and step 10 the
ValueError rejections and determinism checks.

Pure stdlib unittest, offline and deterministic. Run:
    python3 scripts/test_statically_indeterminate.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import statically_indeterminate_logic as si

EI = 4.0e7


def rel_close(a, b, rel=1e-6):
    """Tolerant compare of two floats, safe for values near zero."""
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


class TestFixedEndMoments(unittest.TestCase):
    """Workflow step 2: fixed-end moment catalog of both-ends-fixed
    members from the standard load cases."""

    def test_fixed_end_moment_uniform_worked_values(self):
        # Step 2 fixed-end moment magnitudes: fem_uniform(12000, 5) =
        # w*L**2/12 = 25000.0 and fem_uniform(10000, 6) = 30000.0.
        self.assertTrue(rel_close(si.fixed_end_moment_uniform(12000.0, 5.0), 25000.0))
        self.assertTrue(rel_close(si.fixed_end_moment_uniform(10000.0, 6.0), 30000.0))

    def test_fixed_end_moment_uniform_closed_form(self):
        # Step 2 closed form w*L**2/12 holds by construction for a set of
        # spans, the hogging fixed-end moment at each fixed end.
        for w in (8000.0, 12000.0, 15000.0):
            for L in (3.0, 4.0, 6.0):
                self.assertTrue(rel_close(si.fixed_end_moment_uniform(w, L),
                                          w * L ** 2 / 12.0, rel=1e-12))

    def test_fixed_end_moment_central_worked_value_and_closed_form(self):
        # Step 2 central load case: fem_central(30000, 4) = P*L/8 =
        # 15000.0 N m hogging at each fixed end, the worked example value.
        self.assertTrue(rel_close(si.fixed_end_moment_central(30000.0, 4.0), 15000.0))
        for P in (20000.0, 30000.0, 60000.0):
            for L in (4.0, 6.0):
                self.assertTrue(rel_close(si.fixed_end_moment_central(P, L),
                                          P * L / 8.0, rel=1e-12))

    def test_clapeyron_term_worked_values(self):
        # Step 3 Clapeyron load terms t = A*xbar/L of the simple-span free
        # bending moment diagrams: 62500.0 (uniform 12000 on 5 m) and
        # 30000.0 (central 30000 on 4 m).
        self.assertTrue(rel_close(si.clapeyron_term_uniform(12000.0, 5.0), 62500.0))
        self.assertTrue(rel_close(si.clapeyron_term_central(30000.0, 4.0), 30000.0))
        self.assertTrue(rel_close(si.clapeyron_term_uniform(12000.0, 5.0),
                                  12000.0 * 5.0 ** 3 / 24.0, rel=1e-12))
        self.assertTrue(rel_close(si.clapeyron_term_central(30000.0, 4.0),
                                  30000.0 * 4.0 ** 2 / 16.0, rel=1e-12))


class TestThreeMomentAndReactions(unittest.TestCase):
    """Workflow steps 5 and 6: Clapeyron interior support moments of
    continuous beams on simple end supports and the reactions that follow
    from the end moments."""

    def test_three_moment_two_span_result(self):
        # Step 5 two-span continuous beam, L1 = 5 m uniform 12000 N/m and
        # L2 = 4 m central 30000 N: M_B = -30833.3333333333 N m, the closed
        # form -3*(t1 + t2)/(L1 + L2) of the single Clapeyron equation.
        m = si.three_moment_support_moments([5.0, 4.0], [62500.0, 30000.0])
        self.assertEqual(len(m), 1)
        self.assertTrue(rel_close(m[0], -30833.3333333333, rel=1e-6))
        self.assertTrue(rel_close(m[0], -3.0 * (62500.0 + 30000.0) / 9.0, rel=1e-9))

    def test_three_moment_three_equal_spans_result(self):
        # Step 5 three equal spans L = 6 m under uniform 10000 N/m: M_1 =
        # M_2 = -36000.0 N m, the Roark/Shigley continuous-beam table value
        # -w*L**2/10 for three equal spans.
        m = si.three_moment_support_moments([6.0, 6.0, 6.0],
                                            [90000.0, 90000.0, 90000.0])
        self.assertEqual(len(m), 2)
        self.assertTrue(rel_close(m[0], -36000.0, rel=1e-9))
        self.assertTrue(rel_close(m[1], -36000.0, rel=1e-9))
        self.assertTrue(rel_close(m[0], -10000.0 * 6.0 ** 2 / 10.0, rel=1e-9))
        self.assertTrue(rel_close(m[1], -10000.0 * 6.0 ** 2 / 10.0, rel=1e-9))

    def test_reactions_two_span_and_equilibrium(self):
        # Step 6 support reactions from the sagging-positive support moments
        # with the span rule R_left = R0 + (M_right - M_left)/L: the two-span
        # reactions 23833.3333333333, 58875.0 and 7291.6666666667 N sum to
        # the applied load 90000.0 N.
        m = si.three_moment_support_moments([5.0, 4.0], [62500.0, 30000.0])
        r = si.support_reactions_continuous([5.0, 4.0],
                                            [("uniform", 12000.0),
                                             ("central", 30000.0)], m)
        self.assertEqual(len(r), 3)
        self.assertTrue(rel_close(r[0], 23833.3333333333))
        self.assertTrue(rel_close(r[1], 58875.0))
        self.assertTrue(rel_close(r[2], 7291.6666666667))
        self.assertTrue(rel_close(sum(r), 90000.0, rel=1e-9))
        self.assertLess(abs(sum(r) - 90000.0), 1e-6)

    def test_reactions_three_span_and_equilibrium(self):
        # Step 6 three-span reactions 24000.0, 66000.0, 66000.0, 24000.0 N
        # (end supports w*L/2 - |M|/L) summing to 180000.0 = 3*w*L with
        # residual 0.0.
        m = si.three_moment_support_moments([6.0, 6.0, 6.0],
                                            [90000.0, 90000.0, 90000.0])
        r = si.support_reactions_continuous([6.0, 6.0, 6.0],
                                            [("uniform", 10000.0)] * 3, m)
        self.assertEqual(len(r), 4)
        expected = [24000.0, 66000.0, 66000.0, 24000.0]
        for got, want in zip(r, expected):
            self.assertTrue(rel_close(got, want))
        self.assertTrue(rel_close(sum(r), 180000.0, rel=1e-9))
        self.assertLess(abs(sum(r) - 180000.0), 1e-6)


class TestHardyCrossBeam(unittest.TestCase):
    """Workflow step 7: the moment distribution (Hardy-Cross) cross-check
    with the stiffness distribution factors and the 1/2 carry-over factor
    reproducing the three-moment support moments."""

    def test_hardycross_two_span_matches_three_moment(self):
        # Step 7 two-span beam: the moment distribution support moment
        # -30833.3333333333 agrees with the three-moment result (anchor
        # residual 0.0) in 23 iterations.
        hc = si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                             ("central", 30000.0)])
        self.assertEqual(hc["iterations"], 23)
        self.assertTrue(rel_close(hc["support_moments"][0], -30833.3333333333,
                                  rel=1e-6))
        tm = si.three_moment_support_moments([5.0, 4.0], [62500.0, 30000.0])
        self.assertTrue(rel_close(hc["support_moments"][0], tm[0], rel=1e-6))

    def test_hardycross_three_span_matches_three_moment(self):
        # Step 7 three equal spans: the moment distribution interior support
        # moments agree with the three-moment values within 3.2e-10 N m in
        # 25 iterations (tolerance 1e-6 relative).
        hc = si.hardycross_beam([6.0, 6.0, 6.0], [("uniform", 10000.0)] * 3)
        self.assertEqual(hc["iterations"], 25)
        tm = si.three_moment_support_moments([6.0, 6.0, 6.0],
                                             [90000.0, 90000.0, 90000.0])
        self.assertEqual(len(hc["support_moments"]), 2)
        for got, want in zip(hc["support_moments"], tm):
            self.assertTrue(rel_close(got, want, rel=1e-6))

    def test_hardycross_simple_end_moments_vanish(self):
        # Step 7 the simple end supports release fully (DF = 1), so the
        # member end moments at the exterior ends sit below 1e-6 N m and
        # the spec bound of 5e-10 N m on the two-span case.
        hc = si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                             ("central", 30000.0)])
        self.assertLess(abs(hc["end_moments"][0][0]), 5e-10)
        self.assertLess(abs(hc["end_moments"][1][1]), 5e-10)
        hc3 = si.hardycross_beam([6.0, 6.0, 6.0], [("uniform", 10000.0)] * 3)
        self.assertLess(abs(hc3["end_moments"][0][0]), 1e-6)
        self.assertLess(abs(hc3["end_moments"][2][1]), 1e-6)

    def test_hardycross_joint_equilibrium_interior(self):
        # Step 7 joint equilibrium: the clockwise-positive member end moments
        # meeting at each interior joint sum to zero within 1e-6 N m, and the
        # sagging-positive support moment equals -end_moments[j-1][1] and
        # end_moments[j][0] of the adjacent spans within 1e-9 relative.
        hc = si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                             ("central", 30000.0)])
        self.assertLess(abs(hc["end_moments"][0][1] + hc["end_moments"][1][0]),
                        1e-6)
        self.assertTrue(rel_close(hc["support_moments"][0],
                                  -hc["end_moments"][0][1], rel=1e-9))
        self.assertTrue(rel_close(hc["support_moments"][0],
                                  hc["end_moments"][1][0], rel=1e-9))
        hc3 = si.hardycross_beam([6.0, 6.0, 6.0], [("uniform", 10000.0)] * 3)
        for s in range(2):
            self.assertLess(abs(hc3["end_moments"][s][1]
                                + hc3["end_moments"][s + 1][0]), 1e-6)
            self.assertTrue(rel_close(hc3["support_moments"][s],
                                      -hc3["end_moments"][s][1], rel=1e-9))

    def test_hardycross_support_reactions_consistency(self):
        # Step 7 cross-check end to end: reactions recovered from the
        # moment-distribution support moments equal the three-moment
        # reaction set within 1e-6 relative.
        hc = si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                             ("central", 30000.0)])
        r = si.support_reactions_continuous([5.0, 4.0],
                                            [("uniform", 12000.0),
                                             ("central", 30000.0)],
                                            hc["support_moments"])
        self.assertTrue(rel_close(r[0], 23833.3333333333))
        self.assertTrue(rel_close(r[1], 58875.0))
        self.assertTrue(rel_close(r[2], 7291.6666666667))


class TestSlopeDeflection(unittest.TestCase):
    """Workflow step 8: slope-deflection member end moments and joint
    rotations in the clockwise-positive convention."""

    def test_slope_deflection_member_propped_identities(self):
        # Step 8 the roller condition of the propped cantilever: theta_right
        # = -2.5e-4 rad with the FEM pair (-10000.0, +10000.0) returns
        # (-15000.0, 0.0) for the central load, and theta_right = -4.0e-4
        # rad with (-16000.0, +16000.0) returns (-24000.0, 0.0) for the
        # uniform load: the prop end moment is exactly the zero of the
        # roller and the fixed end carries the hogging w*L**2/8 moment.
        m = si.slope_deflection_member(EI, 4.0, 0.0, -2.5e-4, -10000.0, 10000.0)
        self.assertTrue(rel_close(m[0], -15000.0, rel=1e-6))
        self.assertLess(abs(m[1]), 1e-6)
        m = si.slope_deflection_member(EI, 4.0, 0.0, -4.0e-4, -16000.0, 16000.0)
        self.assertTrue(rel_close(m[0], -24000.0, rel=1e-6))
        self.assertLess(abs(m[1]), 1e-6)


class TestProppedCantilever(unittest.TestCase):
    """Workflow step 4: the consistent deformation (force method) solution
    of the propped cantilever with the flexibility coefficient and its
    Hardy-Cross and slope-deflection cross-checks."""

    def test_propped_central_consistent_deformation(self):
        # Step 4 propped cantilever under the central load P = 20000 N on
        # L = 4 m: fixed reaction 13750.0 N, prop reaction 6250.0 N
        # (5*P/16 from delta_B/f_BB), fixed-end moment 15000.0 N m,
        # rotation -2.5e-4 rad, flexibility 5.33333333333e-07 m/N,
        # released deflection 3.33333333333e-03 m with the consistency
        # residual 0.0.
        p = si.propped_cantilever("central", 20000.0, 4.0, EI)
        self.assertTrue(rel_close(p["fixed_reaction"], 13750.0))
        self.assertTrue(rel_close(p["prop_reaction"], 6250.0))
        self.assertTrue(rel_close(p["fixed_end_moment"], 15000.0))
        self.assertTrue(rel_close(p["prop_rotation"], -2.5e-4))
        self.assertTrue(rel_close(p["flexibility"], 5.33333333333e-07))
        self.assertTrue(rel_close(p["released_deflection"], 3.33333333333e-03))
        self.assertLess(abs(p["consistency_residual"]), 1e-12)

    def test_propped_uniform_consistent_deformation(self):
        # Step 4 propped cantilever under uniform w = 12000 N/m on L = 4 m:
        # fixed reaction 30000.0 N, prop reaction 18000.0 N (3*w*L/8),
        # fixed-end moment 24000.0 N m, rotation -4.0e-4 rad, released
        # deflection 9.6e-03 m with the consistency residual below 1e-15.
        p = si.propped_cantilever("uniform", 12000.0, 4.0, EI)
        self.assertTrue(rel_close(p["fixed_reaction"], 30000.0))
        self.assertTrue(rel_close(p["prop_reaction"], 18000.0))
        self.assertTrue(rel_close(p["fixed_end_moment"], 24000.0))
        self.assertTrue(rel_close(p["prop_rotation"], -4.0e-4))
        self.assertTrue(rel_close(p["flexibility"], 5.33333333333e-07))
        self.assertTrue(rel_close(p["released_deflection"], 9.6e-03))
        self.assertLess(abs(p["consistency_residual"]), 1e-15)

    def test_propped_carry_over_identity(self):
        # Step 4 carry-over identity of the released end: the propped
        # fixed-end moment equals the both-ends-fixed FEM plus the 1/2
        # carry-over of the released end, 15000.0 = 10000.0 + 5000.0
        # (P*L/8 + P*L/16) for the central load and 24000.0 = 16000.0 +
        # 8000.0 (w*L**2/12 + w*L**2/24) for the uniform load, residual 0.0.
        for config, q in (("central", 20000.0), ("uniform", 12000.0)):
            p = si.propped_cantilever(config, q, 4.0, EI)
            fem = (si.fixed_end_moment_central(q, 4.0) if config == "central"
                   else si.fixed_end_moment_uniform(q, 4.0))
            self.assertLess(abs(p["fixed_end_moment"] - (fem + fem / 2.0)), 1e-6)
            self.assertTrue(rel_close(p["fixed_end_moment"], 1.5 * fem,
                                      rel=1e-9))

    def test_propped_method_agreement(self):
        # Step 4 the three methods agree on the fixed-end moment: the
        # consistent-deformation statics value, the Hardy-Cross FEM plus
        # carry-over value and the slope-deflection value are all 15000.0
        # (central) and 24000.0 (uniform), and the prop end moment of the
        # slope-deflection member is the roller zero 0.0.
        for config, q, want in (("central", 20000.0, 15000.0),
                                ("uniform", 12000.0, 24000.0)):
            p = si.propped_cantilever(config, q, 4.0, EI)
            self.assertTrue(rel_close(p["fixed_end_moment"], want, rel=1e-9))
            self.assertTrue(rel_close(p["hardycross_fixed_end_moment"], want,
                                      rel=1e-9))
            self.assertTrue(rel_close(p["sd_fixed_end_moment"], want, rel=1e-9))
            self.assertEqual(p["sd_prop_end_moment"], 0.0)

    def test_propped_peak_sagging_moments(self):
        # Step 4 peak sagging moments of the propped cantilever: 5*P*L/32 =
        # 12500.0 N m under the central load at x = 2.0 m and 9*w*L**2/128 =
        # 13500.0 N m at x = 5*L/8 = 2.5 m from the fixed end under the
        # uniform load, the fixed-end hogging peaks dominating each elastic
        # moment diagram.
        p = si.propped_cantilever("central", 20000.0, 4.0, EI)
        self.assertTrue(rel_close(p["peak_sagging_moment"], 12500.0))
        self.assertTrue(rel_close(p["peak_sagging_location"], 2.0, rel=1e-9))
        p = si.propped_cantilever("uniform", 12000.0, 4.0, EI)
        self.assertTrue(rel_close(p["peak_sagging_moment"], 13500.0))
        self.assertTrue(rel_close(p["peak_sagging_location"], 2.5, rel=1e-9))


class TestPortalFrame(unittest.TestCase):
    """Workflow step 9: the symmetric fixed-base portal frame under a
    central beam load by moment distribution over the top joints with the
    fixed bases, cross-checked against the direct joint-equation solve."""

    def test_portal_frame_moments(self):
        # Step 9 frame with W = 60000 N, Lb = 6 m, h = 4 m: beam end moment
        # magnitude 33750.0 N m hogging at each end, column top moment
        # 33750.0 N m, column base moment 16875.0 N m (the carry-over half)
        # and beam midspan sagging moment 56250.0 N m (= W*Lb/4 - 33750).
        f = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        self.assertTrue(rel_close(f["beam_end_moment_magnitude"], 33750.0))
        self.assertTrue(rel_close(f["column_top_moment_magnitude"], 33750.0))
        self.assertTrue(rel_close(f["column_base_moment_magnitude"], 16875.0))
        self.assertTrue(rel_close(f["beam_midspan_sagging_moment"], 56250.0))

    def test_portal_frame_rotation_identity(self):
        # Step 9 closed form theta_B = (W*Lb/8)/(4*E*I/h + 2*E*I/Lb) =
        # 8.4375e-4 rad = -theta_C with the antisymmetry residual 0.0.
        f = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        self.assertTrue(rel_close(f["theta_B"], 8.4375e-4))
        self.assertTrue(rel_close(f["theta_C"], -8.4375e-4))
        self.assertLess(abs(f["theta_B"] + f["theta_C"]), 1e-15)

    def test_portal_frame_reactions(self):
        # Step 9 base reactions: 30000.0 N vertical at each base (W/2,
        # sum 60000.0) and zero horizontal reactions by the no-sidesway
        # symmetry of the frame.
        f = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        self.assertTrue(rel_close(f["reaction_vertical_each_base"], 30000.0))
        self.assertEqual(f["reaction_horizontal_each_base"], 0.0)

    def test_portal_hardycross_matches_closed_form(self):
        # Step 9 the moment distribution over joints B and C converges in
        # 12 iterations and every distributed member end moment matches the
        # closed-form slope-deflection member end moments within 1e-6
        # relative; the joint equilibrium residuals at B and C stay below
        # 1e-6 N m.
        f = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        self.assertEqual(f["iterations"], 12)
        mapping = {("col1", "a"): "m_ab", ("col1", "b"): "m_ba",
                   ("beam", "a"): "m_bc", ("beam", "b"): "m_cb",
                   ("col2", "a"): "m_cd", ("col2", "b"): "m_dc"}
        for key, sd_key in mapping.items():
            self.assertTrue(rel_close(f["hardycross"][key],
                                      f["sd"][sd_key], rel=1e-6))
        self.assertLess(abs(f["hardycross"][("col1", "b")]
                            + f["hardycross"][("beam", "a")]), 1e-6)
        self.assertLess(abs(f["hardycross"][("beam", "b")]
                            + f["hardycross"][("col2", "a")]), 1e-6)

    def test_portal_base_carry_over_half_top(self):
        # Step 9 the fixed bases never release, so the column base moment is
        # exactly one half of the column top moment (carry-over), 16875.0
        # from 33750.0 N m.
        f = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        self.assertTrue(rel_close(f["column_base_moment_magnitude"],
                                  f["column_top_moment_magnitude"] / 2.0,
                                  rel=1e-6))

    def test_slope_deflection_frame_solve_cross_check(self):
        # Step 9 direct cross-check: the 2x2 solve of the two joint-
        # equilibrium slope-deflection equations reproduces theta_B =
        # 8.4375e-4 rad and theta_C = -8.4375e-4 rad with a large positive
        # determinant (well conditioned), and every member end moment of
        # the solve matches the moment-distribution end moments within 1e-6
        # relative (anchor max residual 3.5e-10).
        f = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        s = si.slope_deflection_frame_solve(60000.0, 6.0, 4.0, EI)
        self.assertTrue(rel_close(s["theta_B"], 8.4375e-4, rel=1e-9))
        self.assertTrue(rel_close(s["theta_C"], -8.4375e-4, rel=1e-9))
        self.assertGreater(s["det"], 0.0)
        mapping = {("col1", "a"): "m_ab", ("col1", "b"): "m_ba",
                   ("beam", "a"): "m_bc", ("beam", "b"): "m_cb",
                   ("col2", "a"): "m_cd", ("col2", "b"): "m_dc"}
        for key, sd_key in mapping.items():
            self.assertTrue(rel_close(f["hardycross"][key],
                                      s["moments"][sd_key], rel=1e-6))
        # joint equilibrium of the solved member end moments
        self.assertLess(abs(s["moments"]["m_ba"] + s["moments"]["m_bc"]), 1e-6)
        self.assertLess(abs(s["moments"]["m_cb"] + s["moments"]["m_cd"]), 1e-6)


class TestValueErrors(unittest.TestCase):
    """Workflow step 10: every non-physical input raises ValueError, the
    eleven anchor cases of the leaf spec plus the frame and arity checks."""

    def test_value_errors_fixed_end_moments(self):
        # Step 10 nonpositive w on the uniform fixed-end moment and
        # nonpositive L on the central fixed-end moment raise ValueError.
        with self.assertRaises(ValueError):
            si.fixed_end_moment_uniform(0.0, 5.0)
        with self.assertRaises(ValueError):
            si.fixed_end_moment_central(30000.0, 0.0)

    def test_value_errors_clapeyron_negative_load(self):
        # Step 10 the negative load on the uniform Clapeyron term raises
        # ValueError.
        with self.assertRaises(ValueError):
            si.clapeyron_term_uniform(-12000.0, 5.0)
        with self.assertRaises(ValueError):
            si.clapeyron_term_uniform(12000.0, -5.0)

    def test_value_errors_three_moment_arity_and_spans(self):
        # Step 10 a one-span three-moment call and a two-term call on three
        # spans (arity mismatches) raise ValueError, as do a zero length and
        # a zero term.
        with self.assertRaises(ValueError):
            si.three_moment_support_moments([5.0], [62500.0])
        with self.assertRaises(ValueError):
            si.three_moment_support_moments([6.0, 6.0, 6.0],
                                            [90000.0, 90000.0])
        with self.assertRaises(ValueError):
            si.three_moment_support_moments([0.0, 5.0], [62500.0, 30000.0])
        with self.assertRaises(ValueError):
            si.three_moment_support_moments([5.0, 4.0], [0.0, 30000.0])

    def test_value_errors_reactions_kind_and_arity(self):
        # Step 10 wrong loads arity on support_reactions_continuous and the
        # unknown load kind 'triangular' raise ValueError.
        with self.assertRaises(ValueError):
            si.support_reactions_continuous([5.0, 4.0],
                                            [("uniform", 12000.0)],
                                            [-30833.3333333333])
        with self.assertRaises(ValueError):
            si.support_reactions_continuous([5.0, 4.0],
                                            [("uniform", 12000.0),
                                             ("triangular", 30000.0)],
                                            [-30833.3333333333])
        with self.assertRaises(ValueError):
            si.support_reactions_continuous([5.0, 4.0],
                                            [("uniform", 12000.0),
                                             ("central", -30000.0)],
                                            [-30833.3333333333])

    def test_value_errors_hardycross_kind_and_magnitude(self):
        # Step 10 the unknown hardycross load kind 'parabolic' and a
        # nonpositive magnitude raise ValueError.
        with self.assertRaises(ValueError):
            si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                            ("parabolic", 30000.0)])
        with self.assertRaises(ValueError):
            si.hardycross_beam([5.0, 4.0], [("uniform", 0.0),
                                            ("central", 30000.0)])
        with self.assertRaises(ValueError):
            si.hardycross_beam([5.0, 4.0], [("central", 30000.0)])

    def test_value_errors_slope_deflection_member(self):
        # Step 10 ei = 0 and length = 0 on the slope-deflection member
        # raise ValueError.
        with self.assertRaises(ValueError):
            si.slope_deflection_member(0.0, 4.0, 0.0, -2.5e-4, -10000.0, 10000.0)
        with self.assertRaises(ValueError):
            si.slope_deflection_member(EI, 0.0, 0.0, -2.5e-4, -10000.0, 10000.0)

    def test_value_errors_propped_cantilever(self):
        # Step 10 the unknown config 'triangular' and the negative q on the
        # propped cantilever raise ValueError.
        with self.assertRaises(ValueError):
            si.propped_cantilever("triangular", 20000.0, 4.0, EI)
        with self.assertRaises(ValueError):
            si.propped_cantilever("central", -20000.0, 4.0, EI)
        with self.assertRaises(ValueError):
            si.propped_cantilever("uniform", 12000.0, 0.0, EI)
        with self.assertRaises(ValueError):
            si.propped_cantilever("central", 20000.0, 4.0, 0.0)

    def test_value_errors_frame_inputs(self):
        # Step 10 nonpositive load, span, height or ei on the frame solve
        # and the moment distribution raise ValueError.
        with self.assertRaises(ValueError):
            si.portal_frame_fixed_base(0.0, 6.0, 4.0, EI)
        with self.assertRaises(ValueError):
            si.portal_frame_fixed_base(60000.0, 0.0, 4.0, EI)
        with self.assertRaises(ValueError):
            si.portal_frame_fixed_base(60000.0, 6.0, -4.0, EI)
        with self.assertRaises(ValueError):
            si.portal_frame_fixed_base(60000.0, 6.0, 4.0, 0.0)
        with self.assertRaises(ValueError):
            si.slope_deflection_frame_solve(-60000.0, 6.0, 4.0, EI)
        with self.assertRaises(ValueError):
            si.slope_deflection_frame_solve(60000.0, 6.0, 4.0, -EI)


class TestDeterminism(unittest.TestCase):
    """Workflow step 10: the distribution engines are deterministic, pure
    stdlib and repeatable bit for bit."""

    def test_determinism_beam_and_frame(self):
        # Step 10 identical bits on repeated runs: the moment distribution
        # of the two-span beam and of the portal frame return identical
        # member end moments on a second run, with no RNG anywhere.
        first = si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                                ("central", 30000.0)])
        second = si.hardycross_beam([5.0, 4.0], [("uniform", 12000.0),
                                                 ("central", 30000.0)])
        self.assertEqual(first["end_moments"], second["end_moments"])
        self.assertEqual(first["iterations"], second["iterations"])
        f1 = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        f2 = si.portal_frame_fixed_base(60000.0, 6.0, 4.0, EI)
        self.assertEqual(f1["hardycross"], f2["hardycross"])
        self.assertEqual(f1["iterations"], f2["iterations"])
        p1 = si.propped_cantilever("uniform", 12000.0, 4.0, EI)
        p2 = si.propped_cantilever("uniform", 12000.0, 4.0, EI)
        self.assertEqual(p1, p2)


if __name__ == "__main__":
    unittest.main()
