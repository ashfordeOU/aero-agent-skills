"""Contract test for the shear-center-analysis leaf (structures/fem).

Exercises the SKILL.md workflow end to end. Step 2 of the SKILL.md
workflow, the section-properties pass (section_properties centroid and
centroidal second moments of the thin-wall contour), is exercised by
test_section_properties_*. Step 3, the free-edge contour walk that
builds the V*Q/I transverse-shear-flow distribution q(s) = vy*Q/ixx by
accumulating the running first moment Q, is exercised by the channel,
Z-section and angle tests through shear_center_channel, shear_center_z
and shear_center_angle. Step 4, the resultant resolution with the
vertical-equilibrium check fy ~ -vy and the vanishing horizontal
resultant fx ~ 0, is exercised by the test_*_equilibrium methods.
Step 5, reporting the shear-center offset from the web centerline,
centroid or corner with the channel closed-form cross-check
3*b**2/(h + 6*b), is exercised by the test_*_offset and
test_*_ratio_to_classical methods. Step 6, the doubly symmetric I-beam
web shear-flow maximum at mid-web from i_beam_web_qmax, is exercised by
test_ibeam_*. Step 7, the deterministic offline run of this contract
test, is the final workflow step.

All numeric asserts are order-safe: assertAlmostEqual with an explicit
delta or math.isclose, never exact float equality on computed sums.
Determinism asserts compare two runs of the identical computation,
which is exact by construction. Worked-example magnitudes come from the
wave-42 prep anchor: channel |e| = 18.750 mm, fy = -999.9 N,
ixx = 6.667333e-07 m^4, I-beam q_max = 9589.0 N/m.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shear_center_analysis_logic import (
    channel_classical_e,
    i_beam_web_qmax,
    section_properties,
    shear_center_angle,
    shear_center_channel,
    shear_center_z,
)

CH_H = 0.100
CH_B = 0.050
CH_T = 0.002
CHANNEL_SEGS = [
    (CH_B, CH_H / 2.0, 0.0, CH_H / 2.0, CH_T),
    (0.0, CH_H / 2.0, 0.0, -CH_H / 2.0, CH_T),
    (0.0, -CH_H / 2.0, CH_B, -CH_H / 2.0, CH_T),
]


class TestSectionProperties(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the section-properties pass."""

    def test_section_properties_horizontal_rect_closed_form(self):
        """Step 2, the section-properties pass, on one horizontal wall:
        centroid at the midpoint and the thin-rectangle closed forms."""
        xb, yb, ixx, iyy, ixy = section_properties(
            [(0.0, 0.0, 0.200, 0.0, 0.002)])
        self.assertAlmostEqual(xb, 0.100, delta=1e-12)
        self.assertAlmostEqual(yb, 0.0, delta=1e-15)
        self.assertAlmostEqual(iyy, 0.002 * 0.200 ** 3 / 12.0, delta=1e-12)
        self.assertAlmostEqual(ixx, 0.200 * 0.002 ** 3 / 12.0, delta=1e-15)
        self.assertAlmostEqual(ixy, 0.0, delta=1e-18)

    def test_section_properties_vertical_rect_closed_form(self):
        """Step 2, the section-properties pass, on one vertical wall:
        the along-length inertia now lands on ixx."""
        xb, yb, ixx, iyy, ixy = section_properties(
            [(0.0, 0.0, 0.0, 0.200, 0.002)])
        self.assertAlmostEqual(xb, 0.0, delta=1e-15)
        self.assertAlmostEqual(yb, 0.100, delta=1e-12)
        self.assertAlmostEqual(ixx, 0.002 * 0.200 ** 3 / 12.0, delta=1e-12)
        self.assertAlmostEqual(iyy, 0.200 * 0.002 ** 3 / 12.0, delta=1e-15)

    def test_section_properties_channel_centroid_midline(self):
        """Step 2, the section-properties pass, on the channel contour:
        the centroid sits b**2/(2*b + h) outboard of the web centerline
        at mid-height."""
        xb, yb, ixx, iyy, ixy = section_properties(CHANNEL_SEGS)
        self.assertAlmostEqual(xb * 1000.0, 12.5, delta=1e-6)
        self.assertAlmostEqual(abs(yb), 0.0, delta=1e-15)

    def test_section_properties_channel_ixx_identity_and_symmetry(self):
        """Step 2, the section-properties pass, on the channel contour:
        ixx matches t*h**2*(h + 6*b)/12 within 2e-4 relative and the
        product of inertia vanishes by symmetry about the vertical axis."""
        xb, yb, ixx, iyy, ixy = section_properties(CHANNEL_SEGS)
        classical = CH_T * CH_H ** 2 * (CH_H + 6.0 * CH_B) / 12.0
        self.assertTrue(math.isclose(ixx, classical, rel_tol=2e-4),
                        "ixx %r vs classical %r" % (ixx, classical))
        self.assertAlmostEqual(ixy, 0.0, delta=1e-15)

    def test_section_properties_angle_ixx_closed_form(self):
        """Step 2, the section-properties pass, on the equal-leg angle:
        ixx approaches 5*a**3*t/24 as the t**3 local terms shrink."""
        a, t = 0.050, 0.003
        xb, yb, ixx, iyy, ixy = section_properties(
            [(0.0, a, 0.0, 0.0, t), (0.0, 0.0, a, 0.0, t)])
        self.assertTrue(math.isclose(ixx, 5.0 * a ** 3 * t / 24.0,
                                     rel_tol=2e-3),
                        "ixx %r vs 5*a^3*t/24 %r" % (ixx, 5.0 * a ** 3 * t / 24.0))

    def test_section_properties_empty_list_raises(self):
        """Step 2 rejects a section with no walls: ValueError on an
        empty segment list (no area to integrate)."""
        with self.assertRaises(ValueError):
            section_properties([])

    def test_section_properties_zero_length_raises(self):
        """Step 2 rejects a degenerate wall: ValueError on a zero-length
        segment (both endpoints coincide)."""
        with self.assertRaises(ValueError):
            section_properties([(0.100, 0.0, 0.100, 0.0, 0.002)])

    def test_section_properties_nonpositive_thickness_raises(self):
        """Step 2 rejects a non-physical wall: ValueError when the wall
        thickness is zero or negative."""
        for bad_t in (0.0, -0.002):
            with self.assertRaises(ValueError):
                section_properties([(0.0, 0.0, 0.100, 0.0, bad_t)])


class TestChannelShearCenter(unittest.TestCase):
    """Steps 3 to 5 of the SKILL.md workflow on the channel spar."""

    def test_channel_anchor_offset_18_75_mm(self):
        """Step 5, the shear-center offset report: the 100 x 50 x 2 mm
        channel gives |e| = 18.750 mm within 1e-3 mm of the web
        centerline at the anchor load vy = 1000 N."""
        e_m, fx, fy, ixx = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertAlmostEqual(abs(e_m) * 1000.0, 18.750, delta=1e-3)

    def test_channel_e_negative_behind_web(self):
        """Step 5, the shear-center offset report: e is negative when
        both flanges extend toward +x, so the shear center sits behind
        the web, opposite the flange direction."""
        e_m, fx, fy, ixx = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertLess(e_m, 0.0)

    def test_channel_ratio_to_classical_closed_form(self):
        """Step 5 cross-check: |e| matches the channel closed form
        e = 3*b**2/(h + 6*b) within 2e-5 relative at n = 400."""
        e_m, fx, fy, ixx = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        e_classical = channel_classical_e(CH_H, CH_B)
        self.assertTrue(math.isclose(abs(e_m), e_classical, rel_tol=2e-5),
                        "|e| %r vs classical %r" % (abs(e_m), e_classical))

    def test_channel_vertical_equilibrium(self):
        """Step 4, the resultant resolution: the integrated vertical
        wall-shear resultant fy equals -vy within 1 N (the contour runs
        down the web) and the horizontal resultant fx vanishes below
        1e-6 N."""
        e_m, fx, fy, ixx = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertAlmostEqual(fy, -1000.0, delta=1.0)
        self.assertLess(abs(fx), 1e-6)

    def test_channel_ixx_anchor_and_identity(self):
        """Step 2 output feeding step 3: the walked channel returns
        ixx = 6.667333e-07 m^4 (the classical t*h**2*(h + 6*b)/12 value
        plus the small flange local terms) within 2e-4 relative."""
        e_m, fx, fy, ixx = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertTrue(math.isclose(ixx, 6.667333e-07, rel_tol=2e-4),
                        "ixx %r" % ixx)
        classical = CH_T * CH_H ** 2 * (CH_H + 6.0 * CH_B) / 12.0
        self.assertTrue(math.isclose(ixx, classical, rel_tol=2e-4))

    def test_channel_finer_steps_convergence(self):
        """Step 3, the free-edge contour walk, converges: the offset at
        n = 4000 differs from n = 400 by less than 1e-4 relative and
        lands within 2e-5 of the classical closed form."""
        e1 = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0, n=400)[0]
        e2 = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0, n=4000)[0]
        self.assertLess(abs(e2 - e1) / abs(e1), 1e-4)
        self.assertTrue(math.isclose(abs(e2), channel_classical_e(CH_H, CH_B),
                                     rel_tol=2e-5))

    def test_channel_vy_scaling_and_geometry_trends(self):
        """Steps 1 and 5: doubling the applied vertical shear doubles
        the resultant but leaves the offset unchanged, and a wider
        flange pushes the shear center farther behind the web."""
        e1, fx1, fy1, ixx1 = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        e2, fx2, fy2, ixx2 = shear_center_channel(CH_H, CH_B, CH_T, vy=2000.0)
        self.assertTrue(math.isclose(fy2, 2.0 * fy1, rel_tol=1e-9))
        self.assertTrue(math.isclose(e2, e1, rel_tol=1e-9))
        e_wide = shear_center_channel(CH_H, 0.060, CH_T, vy=1000.0)[0]
        self.assertGreater(abs(e_wide), abs(e1))

    def test_channel_rejects_nonphysical_inputs(self):
        """Step 1 input guards: ValueError for a non-positive web
        height, flange width or wall thickness and for a non-finite
        applied vertical shear."""
        base = dict(h=CH_H, b=CH_B, t=CH_T, vy=1000.0)
        for bad in ({"h": 0.0}, {"h": -0.1}, {"b": 0.0}, {"b": -0.05},
                    {"t": 0.0}, {"t": -0.002},
                    {"vy": float("inf")}, {"vy": float("nan")}):
            case = dict(base)
            case.update(bad)
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    shear_center_channel(**case)

    def test_channel_junction_shear_stress_below_allowable(self):
        """Worked-example magnitude check: the bending shear stress
        tau = vy*Q/(ixx*t) at the web-flange junction of the prep
        channel is 3.75 MPa (5.62 MPa at mid-web), far below the order
        100 MPa aluminum allowables for the 1000 N load."""
        e_m, fx, fy, ixx = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        q_junction = CH_B * CH_T * (CH_H / 2.0)
        tau_junction = 1000.0 * q_junction / (ixx * CH_T)
        self.assertAlmostEqual(tau_junction / 1e6, 3.75, delta=0.01)
        self.assertLess(tau_junction, 100.0e6)
        q_midweb = CH_T * (CH_H / 2.0) * (CH_H / 4.0) + q_junction
        tau_midweb = 1000.0 * q_midweb / (ixx * CH_T)
        self.assertLess(tau_midweb, 100.0e6)


class TestZSectionShearCenter(unittest.TestCase):
    """Steps 3 to 5 of the SKILL.md workflow on the Z-section."""

    def test_z_offset_from_centroid_zero(self):
        """Step 5, the shear-center offset report: the doubly symmetric
        Z-section places its shear center at the centroid, offset from
        it within 1e-3 mm."""
        e_centroid, xbar, fy, ixx = shear_center_z(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertLess(abs(e_centroid) * 1000.0, 1e-3)

    def test_z_vertical_equilibrium(self):
        """Step 4, the resultant resolution: the Z-section contour walk
        returns fy within 1 N of the applied vertical shear -1000 N."""
        e_centroid, xbar, fy, ixx = shear_center_z(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertAlmostEqual(fy, -1000.0, delta=1.0)

    def test_z_centroid_on_web_centerline(self):
        """Step 2 output: the Z-section centroid lies on the web
        centerline (xbar vanishes) by the 180-degree symmetry of the
        top and bottom flanges."""
        e_centroid, xbar, fy, ixx = shear_center_z(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertLess(abs(xbar), 1e-12)

    def test_z_ixx_matches_channel_contour(self):
        """Step 2 output feeding step 3: the Z-section and channel share
        the same wall lengths, so their ixx values agree to 1e-9
        relative."""
        e_centroid, xbar, fy, ixx = shear_center_z(CH_H, CH_B, CH_T, vy=1000.0)
        e_ch = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)[3]
        self.assertTrue(math.isclose(ixx, e_ch, rel_tol=1e-9))

    def test_z_rejects_nonphysical_inputs(self):
        """Step 1 input guards: ValueError for a non-positive dimension
        of the Z-section or a non-finite shear load."""
        base = dict(h=CH_H, b=CH_B, t=CH_T, vy=1000.0)
        for bad in ({"h": 0.0}, {"b": -0.05}, {"t": 0.0},
                    {"vy": float("inf")}):
            case = dict(base)
            case.update(bad)
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    shear_center_z(**case)


class TestAngleShearCenter(unittest.TestCase):
    """Steps 3 to 5 of the SKILL.md workflow on the equal-leg angle."""

    def test_angle_offset_from_corner_zero(self):
        """Step 5, the shear-center offset report: the shear center of
        an equal-leg angle sits at the intersection of the leg
        centerlines, the corner, so the offset from the corner is
        within 1e-3 mm of zero."""
        a, t = 0.050, 0.003
        e_corner, xbar, ybar, fy, ixx = shear_center_angle(a, t, vy=1000.0)
        self.assertLess(abs(e_corner) * 1000.0, 1e-3)

    def test_angle_centroid_at_a_quarter(self):
        """Step 2 output: the equal-leg angle centroid lies at
        (a/4, a/4) = (12.5, 12.5) mm for the 50 mm leg."""
        a, t = 0.050, 0.003
        e_corner, xbar, ybar, fy, ixx = shear_center_angle(a, t, vy=1000.0)
        self.assertTrue(math.isclose(xbar, a / 4.0, rel_tol=1e-6))
        self.assertTrue(math.isclose(ybar, a / 4.0, rel_tol=1e-6))

    def test_angle_distance_from_centroid_diagonal(self):
        """Step 5 context: with the shear center at the corner and the
        centroid at (a/4, a/4), the shear center lies 17.678 mm from
        the centroid along the diagonal."""
        a, t = 0.050, 0.003
        e_corner, xbar, ybar, fy, ixx = shear_center_angle(a, t, vy=1000.0)
        diag_mm = math.hypot(xbar, ybar) * 1000.0
        self.assertAlmostEqual(diag_mm, 17.678, delta=1e-3)

    def test_angle_rejects_nonphysical_inputs(self):
        """Step 1 input guards: ValueError for a non-positive leg
        length or wall thickness and for a non-finite shear load."""
        base = dict(a=0.050, t=0.003, vy=1000.0)
        for bad in ({"a": 0.0}, {"a": -0.05}, {"t": 0.0},
                    {"t": -0.003}, {"vy": float("nan")}):
            case = dict(base)
            case.update(bad)
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    shear_center_angle(**case)


class TestIBeamWebQmax(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the doubly symmetric I-beam."""

    def test_ibeam_web_qmax_anchor(self):
        """Step 6, the web shear-flow maximum: the 60 x 4 mm flanges on
        a 100 x 3 mm web at vy = 1000 N give q_max = 9589.0 N/m at
        mid-web within 1 N/m."""
        q_max, ixx = i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 1000.0)
        self.assertAlmostEqual(q_max, 9589.0, delta=1.0)

    def test_ibeam_ixx_anchor(self):
        """Step 6 section term: the flange-web assembly second moment is
        ixx = 1.692560e-06 m^4 within 1e-9."""
        q_max, ixx = i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 1000.0)
        self.assertAlmostEqual(ixx, 1.692560e-06, delta=1e-9)

    def test_ibeam_vy_scaling_and_zero_load(self):
        """Step 6 linearity: the web shear-flow maximum scales exactly
        with the applied vertical shear and vanishes at vy = 0."""
        q1, ixx1 = i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 1000.0)
        q2, ixx2 = i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 2000.0)
        self.assertTrue(math.isclose(q2, 2.0 * q1, rel_tol=1e-9))
        q0, ixx0 = i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 0.0)
        self.assertAlmostEqual(q0, 0.0, delta=1e-9)
        self.assertTrue(math.isclose(ixx0, ixx1, rel_tol=1e-12))

    def test_ibeam_thicker_web_higher_qmax(self):
        """Step 6 trend: a thicker web carries more of the vertical
        shear, so the mid-web shear-flow maximum rises."""
        q_thin, ixx_thin = i_beam_web_qmax(0.004, 0.060, 0.003, 0.100, 1000.0)
        q_thick, ixx_thick = i_beam_web_qmax(0.004, 0.060, 0.005, 0.100, 1000.0)
        self.assertGreater(q_thick, q_thin)

    def test_ibeam_rejects_nonphysical_inputs(self):
        """Step 6 input guards: ValueError for a non-positive flange
        thickness, flange width, web thickness or web height and for a
        non-finite applied vertical shear."""
        bad_cases = [
            dict(t_f=0.0, b_f=0.060, t_w=0.003, h=0.100, vy=1000.0),
            dict(t_f=0.004, b_f=-0.060, t_w=0.003, h=0.100, vy=1000.0),
            dict(t_f=0.004, b_f=0.060, t_w=0.0, h=0.100, vy=1000.0),
            dict(t_f=0.004, b_f=0.060, t_w=0.003, h=-0.100, vy=1000.0),
            dict(t_f=0.004, b_f=0.060, t_w=0.003, h=0.100, vy=float("inf")),
        ]
        for case in bad_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    i_beam_web_qmax(**case)


class TestDeterminism(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the deterministic offline run."""

    def test_deterministic_bit_identical_runs(self):
        """Step 7 determinism: two runs of the channel walk produce
        bit-identical offsets, resultants and second moments."""
        first = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        second = shear_center_channel(CH_H, CH_B, CH_T, vy=1000.0)
        self.assertEqual(first, second)

    def test_no_rng_no_numpy_in_module(self):
        """Step 7 determinism: the logic module imports math only, so no
        random generator and no numeric package exist in its namespace."""
        import shear_center_analysis_logic as logic_mod
        self.assertFalse(hasattr(logic_mod, "random"))
        self.assertFalse(hasattr(logic_mod, "numpy"))
        self.assertFalse(hasattr(logic_mod, "scipy"))


if __name__ == "__main__":
    unittest.main()
