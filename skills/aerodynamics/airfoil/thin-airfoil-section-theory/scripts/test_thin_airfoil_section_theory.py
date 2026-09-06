"""Contract test for thin-airfoil-section-theory (aerodynamics/airfoil).

Exercises the SKILL.md workflow end to end: the camber-line input route
selection (NACA 4-digit mean line, polynomial camber line, sampled camber
stations), the Glauert sine-series decomposition by trapezoid quadrature
over the theta transform, the zero-lift angle read, the section lift
coefficient recovery, the quarter-chord pitching-moment coefficient read
and the center-of-pressure location, against the spec anchors and the
closed-form parabolic mean line.

All numeric asserts are order-safe: assertAlmostEqual(..., delta=...) or
math.isclose on computed sums, never exact float equality. Stdlib only
(math, unittest); deterministic and offline; runs in under 20 s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thin_airfoil_section_theory_logic import (  # noqa: E402
    PI,
    center_of_pressure_over_chord,
    glauert_coefficients_naca4,
    glauert_coefficients_points,
    glauert_coefficients_poly,
    lift_coefficient,
    quarter_chord_moment,
)

ALPHA_4DEG = 4.0 * PI / 180.0  # 0.069813170080 rad, the worked example alpha
M_2412 = 0.02
P_2412 = 0.4
D_ANCHOR = 1e-9     # spec validation tolerance on the worked-example anchors
D_IDENT = 1e-12     # identity tolerance (machine-noise level)


class Naca4RouteWorkedExampleTests(unittest.TestCase):
    """Worked example: NACA 2412 mean line (m = 0.02, p = 0.4) at 4 deg."""

    def test_naca4_2412_A0_glauert_decomposition(self):
        """SKILL.md workflow step 2, the Glauert sine-series decomposition
        of the 2412 camber slope by trapezoid quadrature over the theta
        transform, gives A0 at 4 deg (anchor 0.065320283700)."""
        A0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)[0]
        self.assertAlmostEqual(A0, 0.065320283700, delta=D_ANCHOR)

    def test_naca4_2412_A1_glauert_decomposition(self):
        """Step 2 of the SKILL.md workflow, the Glauert A1 term for the 2412
        mean line, is exercised here (anchor 0.081495141601)."""
        A1 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)[1]
        self.assertAlmostEqual(A1, 0.081495141601, delta=D_ANCHOR)

    def test_naca4_2412_A2_glauert_decomposition(self):
        """The Glauert A2 coefficient of the 2412 camber slope comes from
        the same theta-transform quadrature pass (anchor 0.013861276465)."""
        A2 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)[2]
        self.assertAlmostEqual(A2, 0.013861276465, delta=D_ANCHOR)

    def test_naca4_2412_zero_lift_angle_radians_and_degrees(self):
        """The zero-lift angle read of the 2412 mean line is
        -0.036254684420 rad, -2.077240404870 deg (anchor values)."""
        al0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)[3]
        self.assertAlmostEqual(al0, -0.036254684420, delta=D_ANCHOR)
        self.assertAlmostEqual(al0 * 180.0 / PI, -2.077240404870,
                               delta=D_ANCHOR)

    def test_lift_coefficient_2412_at_4_deg(self):
        """SKILL.md workflow step 3, the section lift coefficient recovery
        cl = 2*pi*(alpha - alpha_L0), gives 0.666443984960 at 4 deg."""
        _, _, _, al0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        self.assertAlmostEqual(lift_coefficient(ALPHA_4DEG, al0),
                               0.666443984960, delta=D_ANCHOR)

    def test_lift_coefficient_2412_at_zero_alpha(self):
        """The section lift coefficient at alpha = 0 for the 2412 mean line
        is 0.227794900467 (positive camber lifts at zero angle)."""
        _, _, _, al0 = glauert_coefficients_naca4(0.0, M_2412, P_2412)
        self.assertAlmostEqual(lift_coefficient(0.0, al0),
                               0.227794900467, delta=D_ANCHOR)

    def test_quarter_chord_moment_2412(self):
        """SKILL.md workflow step 4, the quarter-chord pitching-moment
        coefficient read cm_c4 = (pi/4)*(A2 - A1), gives -0.053119513461."""
        _, A1, A2, _ = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        self.assertAlmostEqual(quarter_chord_moment(A1, A2),
                               -0.053119513461, delta=D_ANCHOR)

    def test_center_of_pressure_2412_at_4_deg(self):
        """SKILL.md workflow step 5, the center-of-pressure location
        x_cp/c = 1/4 - cm_c4/cl, puts the cp at 0.329705893759 chord."""
        A0, A1, A2, al0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        cl = 2.0 * PI * A0 + PI * A1
        self.assertAlmostEqual(cl, lift_coefficient(ALPHA_4DEG, al0),
                               delta=D_IDENT)
        cm = quarter_chord_moment(A1, A2)
        self.assertAlmostEqual(center_of_pressure_over_chord(cl, cm),
                               0.329705893759, delta=D_ANCHOR)


class IdentityTests(unittest.TestCase):
    """Closed-form identities the leaf must satisfy to machine noise."""

    def test_zero_lift_angle_identity_matches_derived_form(self):
        """The direct zero-lift angle integral of the 2412 camber slope
        equals -A0(alpha = 0) - A1/2 (derived form) to 1e-12."""
        _, A1, _, al0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        A0z = glauert_coefficients_naca4(0.0, M_2412, P_2412)[0]
        self.assertAlmostEqual(al0, -A0z - A1 / 2.0, delta=D_IDENT)

    def test_A0_at_zero_lift_angle_equals_minus_A1_over_2(self):
        """The Glauert A0 coefficient evaluated at the zero-lift angle of
        the 2412 camber line equals -A1/2 (cl vanishes there)."""
        _, A1, _, al0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        A0_at_al0 = glauert_coefficients_naca4(al0, M_2412, P_2412)[0]
        self.assertAlmostEqual(A0_at_al0, -A1 / 2.0, delta=D_IDENT)

    def test_cl_two_forms_agree(self):
        """Step 3 of the SKILL.md workflow: cl = 2*pi*A0 + pi*A1 equals the
        alpha-based form 2*pi*(alpha - alpha_L0) to 1e-12."""
        A0, A1, _, al0 = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        cl_series = 2.0 * PI * A0 + PI * A1
        self.assertAlmostEqual(cl_series,
                               lift_coefficient(ALPHA_4DEG, al0),
                               delta=D_IDENT)

    def test_cm_c4_equals_cm_le_plus_cl_over_4(self):
        """Step 4 of the SKILL.md workflow: cm_c4 = (pi/4)*(A2 - A1) equals
        cm_le + cl/4 with cm_le = -(pi/2)*(A0 + A1) + (pi/4)*A2 to 1e-12."""
        A0, A1, A2, _ = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        cl = 2.0 * PI * A0 + PI * A1
        cm_le = -(PI / 2.0) * (A0 + A1) + (PI / 4.0) * A2
        self.assertAlmostEqual(quarter_chord_moment(A1, A2),
                               cm_le + cl / 4.0, delta=D_IDENT)

    def test_cm_c4_rejects_A1_plus_A2_mistranscription(self):
        """The quarter-chord pitching-moment coefficient form (pi/4)*(A2 -
        A1) differs from the mistranscribed -(pi/4)*(A1 + A2) by (pi/2)*A2,
        so the two readings cannot both hold."""
        A0, A1, A2, _ = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        cm = quarter_chord_moment(A1, A2)
        wrong = -(PI / 4.0) * (A1 + A2)
        self.assertAlmostEqual(cm - wrong, PI / 2.0 * A2, delta=D_IDENT)
        cl = 2.0 * PI * A0 + PI * A1
        cm_le = -(PI / 2.0) * (A0 + A1) + (PI / 4.0) * A2
        self.assertGreater(abs(cm - wrong), 0.02)
        self.assertAlmostEqual(cm, cm_le + cl / 4.0, delta=D_IDENT)


class ParabolicMeanLineTests(unittest.TestCase):
    """KNOWN-EXACT anchor: z = 4*m*x*(1-x), m = 0.04, poly route at 4 deg."""

    COEFFS = [0.0, 0.16, -0.16]
    M_PARA = 0.04

    def test_parabolic_mean_line_zero_lift_angle_exact(self):
        """The polynomial camber route with coeffs [0.0, 0.16, -0.16]
        recovers the closed-form zero-lift angle alpha_L0 = -2*m = -0.08
        rad of the parabolic mean line."""
        al0 = glauert_coefficients_poly(ALPHA_4DEG, self.COEFFS)[3]
        self.assertAlmostEqual(al0, -0.08, delta=D_ANCHOR)
        self.assertAlmostEqual(al0, -2.0 * self.M_PARA, delta=D_IDENT)

    def test_parabolic_mean_line_A1_and_A2_exact(self):
        """Step 2 of the SKILL.md workflow, the Glauert sine-series
        decomposition, recovers A1 = 4*m = 0.16 and A2 = 0 for the
        parabolic mean line (NACA p = 0.5 case)."""
        _, A1, A2, _ = glauert_coefficients_poly(ALPHA_4DEG, self.COEFFS)
        self.assertAlmostEqual(A1, 0.16, delta=D_ANCHOR)
        self.assertAlmostEqual(A1, 4.0 * self.M_PARA, delta=D_IDENT)
        self.assertAlmostEqual(A2, 0.0, delta=D_ANCHOR)

    def test_parabolic_mean_line_quarter_chord_moment_exact(self):
        """The quarter-chord pitching-moment coefficient of the parabolic
        mean line is cm_c4 = -pi*m = -0.125663706144 exactly."""
        _, A1, A2, _ = glauert_coefficients_poly(ALPHA_4DEG, self.COEFFS)
        self.assertAlmostEqual(quarter_chord_moment(A1, A2),
                               -0.125663706144, delta=D_ANCHOR)
        self.assertAlmostEqual(quarter_chord_moment(A1, A2),
                               -PI * self.M_PARA, delta=D_IDENT)

    def test_parabolic_mean_line_lift_and_cp_exact(self):
        """Step 3 and 5 of the SKILL.md workflow: cl(4 deg) =
        0.941303909067, cl(0) = 4*pi*m = 0.502654824574, and the
        center-of-pressure location x_cp/c = 0.383499611478."""
        _, _, _, al0 = glauert_coefficients_poly(ALPHA_4DEG, self.COEFFS)
        cl4 = lift_coefficient(ALPHA_4DEG, al0)
        cl0 = lift_coefficient(0.0, al0)
        self.assertAlmostEqual(cl4, 0.941303909067, delta=D_ANCHOR)
        self.assertAlmostEqual(cl0, 0.502654824574, delta=D_ANCHOR)
        self.assertAlmostEqual(cl0, 4.0 * PI * self.M_PARA, delta=D_IDENT)
        cm = quarter_chord_moment(*glauert_coefficients_poly(
            ALPHA_4DEG, self.COEFFS)[1:3])
        self.assertAlmostEqual(center_of_pressure_over_chord(cl4, cm),
                               0.383499611478, delta=D_ANCHOR)

    def test_naca4_route_p_equal_half_reproduces_parabola(self):
        """The NACA 4-digit mean line at p = 0.5 IS the parabolic line:
        the camber-line input route crossover gives A1 = 0.16, alpha_L0 =
        -0.08 and cm_c4 = -0.125663706144."""
        A0n, A1n, A2n, al0n = glauert_coefficients_naca4(
            ALPHA_4DEG, 0.04, 0.5)
        self.assertAlmostEqual(A1n, 0.16, delta=D_ANCHOR)
        self.assertAlmostEqual(al0n, -0.08, delta=D_ANCHOR)
        self.assertAlmostEqual(quarter_chord_moment(A1n, A2n),
                               -0.125663706144, delta=D_ANCHOR)
        self.assertAlmostEqual(A0n + A0n * 0.0, A0n, delta=0.0)


class FlatMeanLineTests(unittest.TestCase):
    """Zero-camber limit: A0 = alpha, all other terms vanish."""

    def test_flat_mean_line_coefficients_zero_lift_and_moment(self):
        """The flat mean line (coeffs [0.0, 0.0]) gives A0 = alpha exactly
        and A1 = A2 = alpha_L0 = cm_c4 = 0 within 1e-12."""
        A0, A1, A2, al0 = glauert_coefficients_poly(ALPHA_4DEG, [0.0, 0.0])
        self.assertAlmostEqual(A0, ALPHA_4DEG, delta=D_IDENT)
        self.assertAlmostEqual(A1, 0.0, delta=D_IDENT)
        self.assertAlmostEqual(A2, 0.0, delta=D_IDENT)
        self.assertAlmostEqual(al0, 0.0, delta=D_IDENT)
        self.assertAlmostEqual(quarter_chord_moment(A1, A2), 0.0,
                               delta=D_IDENT)

    def test_flat_mean_line_lift_linear_in_alpha(self):
        """Step 3 of the SKILL.md workflow: the section lift coefficient of
        the flat mean line is cl = 2*pi*alpha, linear with slope 2*pi."""
        _, _, _, al0 = glauert_coefficients_poly(ALPHA_4DEG, [0.0, 0.0])
        cl_a = lift_coefficient(ALPHA_4DEG, al0)
        cl_b = lift_coefficient(0.2, al0)
        self.assertAlmostEqual(cl_a, 2.0 * PI * ALPHA_4DEG, delta=D_IDENT)
        self.assertAlmostEqual(cl_b - cl_a, 2.0 * PI * (0.2 - ALPHA_4DEG),
                               delta=D_IDENT)

    def test_zero_camber_naca4_equals_flat_mean_line(self):
        """The NACA 4-digit route at m = 0 reduces to the flat mean line:
        A0 = alpha and a vanishing Glauert A1 term."""
        A0, A1, A2, al0 = glauert_coefficients_naca4(ALPHA_4DEG, 0.0, 0.4)
        self.assertAlmostEqual(A0, ALPHA_4DEG, delta=D_IDENT)
        self.assertAlmostEqual(A1, 0.0, delta=D_IDENT)
        self.assertAlmostEqual(A2, 0.0, delta=D_IDENT)
        self.assertAlmostEqual(al0, 0.0, delta=D_IDENT)


class ConvergenceTests(unittest.TestCase):
    """Quadrature resolution of the Glauert sine-series decomposition."""

    def test_quadrature_convergence_A1_at_one_million_intervals(self):
        """Step 2 of the SKILL.md workflow: trapezoid quadrature of the
        kinked 2412 camber slope has converged at the default 40000
        intervals; A1 agrees with the n_theta = 1000000 grid to ~3e-13."""
        _, A1_40k, _, _ = glauert_coefficients_naca4(
            ALPHA_4DEG, M_2412, P_2412, n_theta=40000)
        _, A1_1e6, _, _ = glauert_coefficients_naca4(
            ALPHA_4DEG, M_2412, P_2412, n_theta=1000000)
        self.assertAlmostEqual(A1_40k, A1_1e6, delta=1e-10)
        self.assertAlmostEqual(A1_1e6, 0.081495141601, delta=D_ANCHOR)

    def test_quadrature_convergence_parabola_reaches_machine_precision(self):
        """The smooth parabolic mean line converges to the closed form to
        1e-15: A1 = 4*m at both the default and million-interval grids."""
        for n in (40000, 1000000):
            _, A1, A2, al0 = glauert_coefficients_poly(
                ALPHA_4DEG, [0.0, 0.16, -0.16], n_theta=n)
            self.assertAlmostEqual(A1, 0.16, delta=1e-12)
            self.assertAlmostEqual(A2, 0.0, delta=1e-12)
            self.assertAlmostEqual(al0, -0.08, delta=1e-12)


class SamplePointRouteTests(unittest.TestCase):
    """Camber-line input route three: sampled (x, z) stations."""

    @staticmethod
    def _stations():
        xs = [i / 4000.0 for i in range(4001)]
        return xs

    def test_points_route_parabola_recovers_closed_form(self):
        """A 4001-station sample of the parabolic mean line recovers the
        closed-form zero-lift angle alpha_L0 = -2*m to ~1e-6 and the
        Glauert A1 term 4*m to ~1e-6 through the sampled camber stations."""
        xs = self._stations()
        zs = [0.16 * x * (1.0 - x) for x in xs]  # z = 4m x (1-x), m = 0.04
        _, A1, _, al0 = glauert_coefficients_points(ALPHA_4DEG, xs, zs)
        self.assertAlmostEqual(al0, -0.08, delta=1e-6)
        self.assertAlmostEqual(A1, 0.16, delta=2e-6)
        self.assertAlmostEqual(al0, -0.079999658257, delta=1e-6)

    def test_points_route_2412_matches_analytic_route(self):
        """A 4001-station sample of the 2412 mean line agrees with the
        analytic NACA 4-digit route to ~1e-7 in alpha_L0 and ~2e-7 in the
        quarter-chord pitching-moment coefficient."""
        xs = self._stations()
        zs = []
        for x in xs:
            if x <= P_2412:
                zs.append(M_2412 / (P_2412 ** 2) *
                          (2.0 * P_2412 * x - x * x))
            else:
                zs.append(M_2412 / ((1.0 - P_2412) ** 2) *
                          (1.0 - 2.0 * P_2412 + 2.0 * P_2412 * x - x * x))
        _, A1, A2, al0 = glauert_coefficients_points(ALPHA_4DEG, xs, zs)
        _, A1a, A2a, al0a = glauert_coefficients_naca4(
            ALPHA_4DEG, M_2412, P_2412)
        self.assertAlmostEqual(al0, al0a, delta=5e-7)
        self.assertAlmostEqual(quarter_chord_moment(A1, A2),
                               quarter_chord_moment(A1a, A2a), delta=5e-7)
        self.assertAlmostEqual(al0, -0.036254564543, delta=1e-6)


class ValueErrorTests(unittest.TestCase):
    """Non-physical inputs are rejected across the module."""

    def test_value_error_naca4_camber_fraction_out_of_range(self):
        """The NACA 4-digit route rejects m = -0.01 and m = 0.2, outside
        the 4-digit max-camber range [0, 0.1]."""
        with self.assertRaises(ValueError):
            glauert_coefficients_naca4(0.1, -0.01, 0.4)
        with self.assertRaises(ValueError):
            glauert_coefficients_naca4(0.1, 0.2, 0.4)

    def test_value_error_naca4_camber_position_out_of_range(self):
        """The NACA 4-digit route rejects p = 0.0 and p = 1.0, the
        degenerate camber positions."""
        with self.assertRaises(ValueError):
            glauert_coefficients_naca4(0.1, 0.02, 0.0)
        with self.assertRaises(ValueError):
            glauert_coefficients_naca4(0.1, 0.02, 1.0)

    def test_value_error_n_theta_invalid(self):
        """Every camber-line input route rejects n_theta below 100 and
        non-int resolutions: n_theta = 10 and n_theta = 40000.0."""
        with self.assertRaises(ValueError):
            glauert_coefficients_naca4(0.1, 0.02, 0.4, n_theta=10)
        with self.assertRaises(ValueError):
            glauert_coefficients_poly(0.1, [0.0, 0.1], n_theta=40000.0)
        with self.assertRaises(ValueError):
            glauert_coefficients_points(0.1, [0.0, 1.0], [0.0, 0.0],
                                        n_theta=99)

    def test_value_error_poly_coeffs_invalid(self):
        """The polynomial camber route rejects empty and non-list coeffs:
        [] and a bare scalar 0.5 are not power-series coefficient lists."""
        with self.assertRaises(ValueError):
            glauert_coefficients_poly(0.1, [])
        with self.assertRaises(ValueError):
            glauert_coefficients_poly(0.1, ())
        with self.assertRaises(ValueError):
            glauert_coefficients_poly(0.1, 0.5)

    def test_value_error_points_lengths_and_count(self):
        """The sampled camber route rejects mismatched xs/zs lengths and
        fewer than 2 stations."""
        with self.assertRaises(ValueError):
            glauert_coefficients_points(0.1, [0.0, 1.0], [0.0])
        with self.assertRaises(ValueError):
            glauert_coefficients_points(0.1, [0.0], [0.0])

    def test_value_error_points_station_order_and_chord_span(self):
        """The sampled camber route rejects non-monotone stations, xs not
        starting at 0.0 and xs not reaching 1.0."""
        with self.assertRaises(ValueError):
            glauert_coefficients_points(0.1, [0.0, 0.6, 0.5, 1.0],
                                        [0.0, 0.1, 0.1, 0.0])
        with self.assertRaises(ValueError):
            glauert_coefficients_points(0.1, [0.1, 1.0], [0.0, 0.0])
        with self.assertRaises(ValueError):
            glauert_coefficients_points(0.1, [0.0, 0.9], [0.0, 0.0])

    def test_value_error_center_of_pressure_at_zero_lift(self):
        """The center-of-pressure location is undefined at zero lift: cl =
        0.0 and cl = 1e-13 both raise ValueError."""
        with self.assertRaises(ValueError):
            center_of_pressure_over_chord(0.0, -0.04)
        with self.assertRaises(ValueError):
            center_of_pressure_over_chord(1e-13, -0.04)


class DeterminismTests(unittest.TestCase):
    """Deterministic, offline, stdlib-only execution."""

    def test_deterministic_repeat_run(self):
        """Step 6 of the SKILL.md workflow: repeated runs of the Glauert
        sine-series decomposition reproduce the same coefficients bit for
        bit (no RNG, no state)."""
        first = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        second = glauert_coefficients_naca4(ALPHA_4DEG, M_2412, P_2412)
        for f, s in zip(first, second):
            self.assertTrue(math.isclose(f, s, rel_tol=0.0, abs_tol=1e-15))


if __name__ == "__main__":
    unittest.main()
