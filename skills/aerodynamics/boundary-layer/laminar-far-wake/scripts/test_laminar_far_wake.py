"""Contract test for the laminar-far-wake leaf (aerodynamics/
boundary-layer): the two-dimensional incompressible laminar far wake
downstream of a thin flat plate at zero incidence, the Goldstein (1933)
similarity wake that the attached laminar Blasius layers shed from the
trailing edge, in the form Schlichting Boundary-Layer Theory (wakes and
free-shear-layers chapter) and White Viscous Fluid Flow present it.

Workflow coverage (SKILL.md Workflow section, wave-45 builder-kit
value-delta sampler rule): step 1, the trailing-edge momentum state fix
(chord c, freestream U, rho, nu with the chord Reynolds number and the
trailing-edge Blasius momentum thickness), is exercised by
test_reynolds_worked_anchor, test_momentum_thickness_worked_anchor and
test_momentum_thickness_closed_routes; step 2, the plate drag assembly
traverse with plate_drag_per_span and the plate_drag_coefficient
reduction cross-checked three ways, by test_plate_drag_worked_anchor_
magnitude_bound, test_plate_drag_one_sided_two_sided and test_drag_
coefficient_anchor_three_routes; step 3, the spread-parameter traverse
of the Gaussian wake at downstream stations with wake_spread_parameter,
by test_wake_spread_parameter_anchor_and_quarter_law; step 4, the
centerline-defect traverse with centerline_defect_from_drag and its
closed-form twin centerline_defect_blasius, by test_centerline_defect_
from_drag_anchor, test_centerline_defect_blasius_anchor_equivalence and
test_centerline_defect_ratio_of_U; step 5, the Gaussian defect profile
traverse with velocity_defect_gaussian, wake_velocity,
half_defect_width and one_over_e_width, by test_gaussian_shape_half_and_
one_over_e, test_wake_velocity_axis_anchor and test_wake_velocity_far_
edge_freestream; step 6, the decay and spreading law traverse across
stations (the u_c*sqrt(x) invariant and the x^1/2 width growth), by
test_centerline_defect_sqrt_x_invariant, test_centerline_decay_laws,
test_half_defect_width_anchor_and_growth and test_one_over_e_width_
anchor_and_ratio; step 7, the wake-momentum-integral drag identity
traverse with defect_integral and drag_from_wake against the plate
drag, by test_defect_integral_anchor_all_stations, test_defect_integral_
identity_routes and test_drag_from_wake_identity_all_stations; step 8,
the nonlinear momentum-deficit honesty check with full_momentum_deficit
against the linearized drag, by test_full_momentum_deficit_ratio_
convergence and test_full_momentum_deficit_residual_at_100c; step 10,
the deterministic repeat calls and the input-rejection traverse of
non-physical arguments, by test_deterministic_repeat_calls and the
test_valueerror_* methods.

Offline deterministic, stdlib only.  Run:
    python3 scripts/test_laminar_far_wake.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import laminar_far_wake_logic as lw

# Worked-example state (air at standard conditions, worked plate).
NU = 1.46e-5        # m2/s, air kinematic viscosity
RHO = 1.225         # kg/m3, air density
U = 5.0             # m/s, freestream speed
C = 1.0             # m, plate chord
PI = math.pi


def rel_close(x, y, tol):
    """True when x and y agree within the relative tolerance tol."""
    return math.isclose(x, y, rel_tol=tol, abs_tol=0.0)


class MomentumStateTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the trailing-edge state fix."""

    def test_reynolds_worked_anchor(self):
        """Step 1 trailing-edge state: the chord Reynolds number
        Re_c = U*c/nu of the fully laminar worked plate is 342465.7534."""
        self.assertAlmostEqual(lw.reynolds_number(U, C, NU), 342465.7534,
                               delta=342465.7534 * 1e-6)

    def test_momentum_thickness_worked_anchor(self):
        """Step 1 trailing-edge state: the Blasius momentum thickness at
        the trailing edge theta_c = 0.664*sqrt(nu*c/U) is 1.1346436974e-3
        m (between 1.1e-3 and 1.2e-3 m)."""
        theta = lw.momentum_thickness_blasius(U, C, NU)
        self.assertAlmostEqual(theta, 1.1346436974e-3,
                               delta=1.1346436974e-3 * 1e-6)

    def test_momentum_thickness_closed_routes(self):
        """Step 1 trailing-edge state: theta_c equals 0.664*c/sqrt(Re_c)
        and 0.664*sqrt(nu*c/U) to float noise (two closed routes)."""
        theta = lw.momentum_thickness_blasius(U, C, NU)
        rec = lw.reynolds_number(U, C, NU)
        self.assertTrue(rel_close(theta, 0.664 * C / math.sqrt(rec), 1e-9))
        self.assertTrue(rel_close(theta, 0.664 * math.sqrt(NU * C / U), 1e-12))


class PlateDragTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the drag assembly traverse."""

    def test_plate_drag_worked_anchor_magnitude_bound(self):
        """Step 2 drag assembly: the two-sided laminar plate drag per
        span D = 1.328*rho*U^2*sqrt(nu*c/U) is 6.9496926464e-2 N/m,
        inside the 6.5e-2 to 7.5e-2 N/m magnitude bound."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        self.assertAlmostEqual(d, 6.9496926464e-2, delta=6.9496926464e-2 * 1e-6)
        self.assertGreater(d, 6.5e-2)
        self.assertLess(d, 7.5e-2)

    def test_plate_drag_one_sided_two_sided(self):
        """Step 2 drag assembly: one side carries rho*U^2*theta_c and the
        default two-sided plate drag is exactly twice the one-sided value."""
        d2 = lw.plate_drag_per_span(U, RHO, NU, C)
        d1 = lw.plate_drag_per_span(U, RHO, NU, C, sides=1)
        theta = lw.momentum_thickness_blasius(U, C, NU)
        self.assertTrue(rel_close(d1, RHO * U * U * theta, 1e-9))
        self.assertTrue(rel_close(d2, 2.0 * d1, 1e-12))

    def test_drag_coefficient_anchor_three_routes(self):
        """Step 2 drag assembly: the two-sided drag coefficient is
        4.53857479e-3 by the module route, by C_D = 2.656/sqrt(Re_c) and
        by C_D = 4*theta_c/c (three routes agree)."""
        cd = lw.plate_drag_coefficient(U, RHO, NU, C)
        self.assertAlmostEqual(cd, 4.53857479e-3, delta=4.53857479e-3 * 1e-6)
        rec = lw.reynolds_number(U, C, NU)
        theta = lw.momentum_thickness_blasius(U, C, NU)
        self.assertTrue(rel_close(cd, 2.656 / math.sqrt(rec), 1e-9))
        self.assertTrue(rel_close(cd, 4.0 * theta / C, 1e-9))


class WakeStateTests(unittest.TestCase):
    """Steps 3 and 4 of the SKILL.md workflow: the spread-parameter and
    centerline-defect traverses at downstream stations."""

    def test_wake_spread_parameter_anchor_and_quarter_law(self):
        """Step 3 spread-parameter traverse: B = U/(4*nu*x) is
        8.5616438356e2 1/m2 at x = 100 m and 2.1404109589e2 at x = 400 m,
        exactly one quarter of the x = 100 value."""
        b100 = lw.wake_spread_parameter(U, NU, 100.0)
        b400 = lw.wake_spread_parameter(U, NU, 400.0)
        self.assertAlmostEqual(b100, 8.5616438356e2, delta=8.5616438356e2 * 1e-6)
        self.assertAlmostEqual(b400, 2.1404109589e2, delta=2.1404109589e2 * 1e-6)
        self.assertTrue(rel_close(b400, 0.25 * b100, 1e-12))

    def test_centerline_defect_from_drag_anchor(self):
        """Step 4 centerline-defect traverse: u_c = (D/(rho*U))*sqrt(B/pi)
        at x = 100 m is 0.18731094174 m/s from the drag normalization."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_from_drag(d, RHO, U, b)
        self.assertAlmostEqual(uc, 0.18731094174, delta=0.18731094174 * 1e-6)

    def test_centerline_defect_blasius_anchor_equivalence(self):
        """Step 4 centerline-defect traverse: the closed form
        u_c = (0.664*U/sqrt(pi))*sqrt(c/x) at x = 100 m is
        0.18731094174 m/s and agrees with centerline_defect_from_drag to
        float noise."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc_drag = lw.centerline_defect_from_drag(d, RHO, U, b)
        uc_blas = lw.centerline_defect_blasius(U, C, 100.0)
        self.assertAlmostEqual(uc_blas, 0.18731094174, delta=0.18731094174 * 1e-6)
        self.assertTrue(rel_close(uc_drag, uc_blas, 1e-12))

    def test_centerline_defect_ratio_of_U(self):
        """Step 4 centerline-defect traverse: the small-defect ratio
        u_c/U is 0.03746218835 (3.746 percent) at x = 100 m, solidly in
        the linearized regime."""
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        self.assertTrue(rel_close(uc / U, 0.03746218835, 1e-6))

    def test_centerline_defect_sqrt_x_invariant(self):
        """Step 6 decay traverse: the invariant u_c*sqrt(x) is
        1.8731094174 m/s*sqrt(m) at x = 25, 100 and 400 m (x^-1/2
        centerline-defect decay)."""
        for x in (25.0, 100.0, 400.0):
            uc = lw.centerline_defect_blasius(U, C, x)
            self.assertTrue(rel_close(uc * math.sqrt(x), 1.8731094174, 1e-6))

    def test_centerline_decay_laws(self):
        """Step 6 decay traverse: u_c(4x)/u_c(x) = 0.5 and
        u_c(2x)/u_c(x) = 1/sqrt(2) = 0.707106781186548 exactly."""
        u100 = lw.centerline_defect_blasius(U, C, 100.0)
        u400 = lw.centerline_defect_blasius(U, C, 400.0)
        u200 = lw.centerline_defect_blasius(U, C, 200.0)
        self.assertTrue(rel_close(u400 / u100, 0.5, 1e-12))
        self.assertTrue(rel_close(u200 / u100, 0.707106781186548, 1e-12))


class WidthAndProfileTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the profile and width traverse."""

    def test_half_defect_width_anchor_and_growth(self):
        """Step 5 profile traverse: the half-defect width sqrt(ln(2)/B) is
        2.8453398864e-2 m at x = 100 m, and quadrupling x doubles it
        (x^1/2 wake spreading)."""
        b100 = lw.wake_spread_parameter(U, NU, 100.0)
        b400 = lw.wake_spread_parameter(U, NU, 400.0)
        yh100 = lw.half_defect_width(b100)
        yh400 = lw.half_defect_width(b400)
        self.assertAlmostEqual(yh100, 2.8453398864e-2,
                               delta=2.8453398864e-2 * 1e-6)
        self.assertTrue(rel_close(yh400 / yh100, 2.0, 1e-12))

    def test_one_over_e_width_anchor_and_ratio(self):
        """Step 5 profile traverse: the one-over-e width sqrt(1/B) is
        3.4176014981e-2 m at x = 100 m and the ratio y_e/y_half equals
        sqrt(1/ln(2)) = 1.2011224087."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        ye = lw.one_over_e_width(b)
        yh = lw.half_defect_width(b)
        self.assertAlmostEqual(ye, 3.4176014981e-2, delta=3.4176014981e-2 * 1e-6)
        self.assertTrue(rel_close(ye / yh, 1.2011224087, 1e-9))
        self.assertTrue(rel_close(ye / yh, math.sqrt(1.0 / math.log(2.0)), 1e-12))

    def test_gaussian_shape_half_and_one_over_e(self):
        """Step 5 profile traverse: the Gaussian defect shape gives
        u1(y_half)/u_c = 0.5 exactly and u1(y_e)/u_c = 1/e =
        0.367879441171442 exactly at the characteristic widths."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        yh = lw.half_defect_width(b)
        ye = lw.one_over_e_width(b)
        self.assertTrue(rel_close(
            lw.velocity_defect_gaussian(uc, b, yh) / uc, 0.5, 1e-12))
        self.assertTrue(rel_close(
            lw.velocity_defect_gaussian(uc, b, ye) / uc,
            0.367879441171442, 1e-12))

    def test_wake_velocity_axis_anchor(self):
        """Step 5 profile traverse: the recovered wake-axis velocity
        u(0) = U - u_c is 4.8126890583 m/s at x = 100 m."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        u0 = lw.wake_velocity(U, uc, b, 0.0)
        self.assertAlmostEqual(u0, 4.8126890583, delta=4.8126890583 * 1e-6)

    def test_wake_velocity_far_edge_freestream(self):
        """Step 5 profile traverse: at y = 6*y_half the recovered wake
        velocity is indistinguishable from the freestream, within 1e-9
        relative of U at x = 100 m (u/U = 0.999999999999455)."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        yh = lw.half_defect_width(b)
        u_far = lw.wake_velocity(U, uc, b, 6.0 * yh)
        self.assertTrue(rel_close(u_far / U, 0.999999999999455, 1e-9))


class MomentumIdentityTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the wake-momentum-integral drag
    identity traverse."""

    def test_defect_integral_anchor_all_stations(self):
        """Step 7 momentum identity: the cross-stream integral of the
        Gaussian defect u_c*sqrt(pi/B) is 1.1346436974e-2 m2/s at
        x = 25, 100 and 400 m (station-independent momentum deficit)."""
        for x in (25.0, 100.0, 400.0):
            b = lw.wake_spread_parameter(U, NU, x)
            uc = lw.centerline_defect_blasius(U, C, x)
            integ = lw.defect_integral(uc, b)
            self.assertAlmostEqual(integ, 1.1346436974e-2,
                                   delta=1.1346436974e-2 * 1e-6)

    def test_defect_integral_identity_routes(self):
        """Step 7 momentum identity: the integral equals 2*U*theta_c and
        D/(rho*U), the closed routes of the same momentum conservation."""
        theta = lw.momentum_thickness_blasius(U, C, NU)
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        integ = lw.defect_integral(uc, b)
        self.assertTrue(rel_close(integ, 2.0 * U * theta, 1e-9))
        self.assertTrue(rel_close(integ, d / (RHO * U), 1e-12))

    def test_drag_from_wake_identity_all_stations(self):
        """Step 7 momentum identity: the wake-survey drag
        rho*U*integral u1 dy is 6.9496926464e-2 N/m and equals the plate
        drag per span at x = 25, 100 and 400 m (D_wake/D_plate = 1.0)."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        for x in (25.0, 100.0, 400.0):
            b = lw.wake_spread_parameter(U, NU, x)
            uc = lw.centerline_defect_blasius(U, C, x)
            dw = lw.drag_from_wake(uc, b, RHO, U)
            self.assertAlmostEqual(dw, 6.9496926464e-2,
                                   delta=6.9496926464e-2 * 1e-6)
            self.assertTrue(rel_close(dw, d, 1e-9))


class NonlinearDeficitTests(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the nonlinear honesty check."""

    def test_full_momentum_deficit_ratio_convergence(self):
        """Step 8 nonlinear check: the full deficit rho*integral u*(U-u)
        dy over the plate drag rises from 0.94702046516 at x = 25 m
        through 0.97351023258 at x = 100 m to 0.98675511629 at x = 400 m,
        monotone toward one."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        ratios = []
        for x in (25.0, 100.0, 400.0):
            b = lw.wake_spread_parameter(U, NU, x)
            uc = lw.centerline_defect_blasius(U, C, x)
            full = lw.full_momentum_deficit(RHO, U, uc, b)
            ratios.append(full / d)
        for r, target in zip(ratios, (0.94702046516, 0.97351023258,
                                      0.98675511629)):
            self.assertTrue(rel_close(r, target, 1e-6))
        self.assertLess(ratios[0], ratios[1])
        self.assertLess(ratios[1], ratios[2])
        self.assertLess(ratios[2], 1.0)

    def test_full_momentum_deficit_residual_at_100c(self):
        """Step 8 nonlinear check: the linearized residual
        drag_from_wake - full_momentum_deficit at x = 100 m is
        1.8409574184e-3 N/m (2.649 percent of the plate drag)."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        dw = lw.drag_from_wake(uc, b, RHO, U)
        full = lw.full_momentum_deficit(RHO, U, uc, b)
        residual = dw - full
        self.assertTrue(rel_close(residual, 1.8409574184e-3, 1e-6))
        self.assertTrue(rel_close(residual / d, 2.649e-2, 1e-3))


class DeterminismTests(unittest.TestCase):
    """Step 10 of the SKILL.md workflow: deterministic repeat calls."""

    def test_deterministic_repeat_calls(self):
        """Step 10 deterministic checks: every function called twice with
        identical arguments returns bit-identical values (closed form, no
        iteration, no randomness)."""
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        b = lw.wake_spread_parameter(U, NU, 100.0)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        pairs = [
            (lambda: lw.reynolds_number(U, C, NU)),
            (lambda: lw.momentum_thickness_blasius(U, C, NU)),
            (lambda: lw.plate_drag_per_span(U, RHO, NU, C)),
            (lambda: lw.plate_drag_coefficient(U, RHO, NU, C)),
            (lambda: lw.wake_spread_parameter(U, NU, 100.0)),
            (lambda: lw.centerline_defect_from_drag(d, RHO, U, b)),
            (lambda: lw.centerline_defect_blasius(U, C, 100.0)),
            (lambda: lw.velocity_defect_gaussian(uc, b, 0.02)),
            (lambda: lw.wake_velocity(U, uc, b, 0.02)),
            (lambda: lw.defect_integral(uc, b)),
            (lambda: lw.drag_from_wake(uc, b, RHO, U)),
            (lambda: lw.half_defect_width(b)),
            (lambda: lw.one_over_e_width(b)),
            (lambda: lw.full_momentum_deficit(RHO, U, uc, b)),
        ]
        for fn in pairs:
            self.assertEqual(fn(), fn())


class ValueErrorTests(unittest.TestCase):
    """Step 10 of the SKILL.md workflow: the input-rejection traverse."""

    def test_valueerror_U_zero_and_negative(self):
        """Step 10 input rejection: U at 0 and -0.01 raises ValueError on
        every U argument (reynolds_number, momentum_thickness_blasius,
        plate_drag_per_span, plate_drag_coefficient, centerline_defect_
        from_drag, centerline_defect_blasius, wake_velocity,
        drag_from_wake, full_momentum_deficit)."""
        for bad in (0.0, -0.01):
            with self.assertRaises(ValueError):
                lw.reynolds_number(bad, C, NU)
            with self.assertRaises(ValueError):
                lw.momentum_thickness_blasius(bad, C, NU)
            with self.assertRaises(ValueError):
                lw.plate_drag_per_span(bad, RHO, NU, C)
            with self.assertRaises(ValueError):
                lw.plate_drag_coefficient(bad, RHO, NU, C)
            b = lw.wake_spread_parameter(U, NU, 100.0)
            d = lw.plate_drag_per_span(U, RHO, NU, C)
            with self.assertRaises(ValueError):
                lw.centerline_defect_from_drag(d, RHO, bad, b)
            with self.assertRaises(ValueError):
                lw.centerline_defect_blasius(bad, C, 100.0)
            uc = lw.centerline_defect_blasius(U, C, 100.0)
            with self.assertRaises(ValueError):
                lw.wake_velocity(bad, uc, b, 0.0)
            with self.assertRaises(ValueError):
                lw.drag_from_wake(uc, b, RHO, bad)
            with self.assertRaises(ValueError):
                lw.full_momentum_deficit(RHO, bad, uc, b)

    def test_valueerror_nu_zero_and_negative(self):
        """Step 10 input rejection: nu at 0 and -1e-5 raises ValueError on
        reynolds_number, momentum_thickness_blasius, plate_drag_per_span,
        plate_drag_coefficient and wake_spread_parameter."""
        for bad in (0.0, -1e-5):
            with self.assertRaises(ValueError):
                lw.reynolds_number(U, C, bad)
            with self.assertRaises(ValueError):
                lw.momentum_thickness_blasius(U, C, bad)
            with self.assertRaises(ValueError):
                lw.plate_drag_per_span(U, RHO, bad, C)
            with self.assertRaises(ValueError):
                lw.plate_drag_coefficient(U, RHO, bad, C)
            with self.assertRaises(ValueError):
                lw.wake_spread_parameter(U, bad, 100.0)

    def test_valueerror_rho_zero(self):
        """Step 10 input rejection: rho at 0 raises ValueError on
        plate_drag_per_span, plate_drag_coefficient, centerline_defect_
        from_drag, drag_from_wake and full_momentum_deficit."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        d = lw.plate_drag_per_span(U, RHO, NU, C)
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        for fn in (
            lambda: lw.plate_drag_per_span(U, 0.0, NU, C),
            lambda: lw.plate_drag_coefficient(U, 0.0, NU, C),
            lambda: lw.centerline_defect_from_drag(d, 0.0, U, b),
            lambda: lw.drag_from_wake(uc, b, 0.0, U),
            lambda: lw.full_momentum_deficit(0.0, U, uc, b),
        ):
            with self.assertRaises(ValueError):
                fn()

    def test_valueerror_c_zero_and_negative(self):
        """Step 10 input rejection: c at 0 and -1.0 raises ValueError on
        plate_drag_per_span, plate_drag_coefficient and
        centerline_defect_blasius."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                lw.plate_drag_per_span(U, RHO, NU, bad)
            with self.assertRaises(ValueError):
                lw.plate_drag_coefficient(U, RHO, NU, bad)
            with self.assertRaises(ValueError):
                lw.centerline_defect_blasius(U, bad, 100.0)

    def test_valueerror_x_zero(self):
        """Step 10 input rejection: x at 0 raises ValueError on
        reynolds_number, wake_spread_parameter and
        centerline_defect_blasius."""
        with self.assertRaises(ValueError):
            lw.reynolds_number(U, 0.0, NU)
        with self.assertRaises(ValueError):
            lw.wake_spread_parameter(U, NU, 0.0)
        with self.assertRaises(ValueError):
            lw.centerline_defect_blasius(U, C, 0.0)

    def test_valueerror_D_zero_and_negative(self):
        """Step 10 input rejection: D at 0 and -1.0 raises ValueError on
        centerline_defect_from_drag."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                lw.centerline_defect_from_drag(bad, RHO, U, b)

    def test_valueerror_B_zero_and_negative(self):
        """Step 10 input rejection: B at 0 and -2.0 raises ValueError on
        every B argument (velocity_defect_gaussian, wake_velocity,
        defect_integral, drag_from_wake, half_defect_width,
        one_over_e_width, full_momentum_deficit)."""
        uc = lw.centerline_defect_blasius(U, C, 100.0)
        for bad in (0.0, -2.0):
            with self.assertRaises(ValueError):
                lw.velocity_defect_gaussian(uc, bad, 0.0)
            with self.assertRaises(ValueError):
                lw.wake_velocity(U, uc, bad, 0.0)
            with self.assertRaises(ValueError):
                lw.defect_integral(uc, bad)
            with self.assertRaises(ValueError):
                lw.drag_from_wake(uc, bad, RHO, U)
            with self.assertRaises(ValueError):
                lw.half_defect_width(bad)
            with self.assertRaises(ValueError):
                lw.one_over_e_width(bad)
            with self.assertRaises(ValueError):
                lw.full_momentum_deficit(RHO, U, uc, bad)

    def test_valueerror_u_centerline_negative(self):
        """Step 10 input rejection: u_centerline at -0.1 raises ValueError
        on velocity_defect_gaussian, wake_velocity, defect_integral,
        drag_from_wake and full_momentum_deficit."""
        b = lw.wake_spread_parameter(U, NU, 100.0)
        with self.assertRaises(ValueError):
            lw.velocity_defect_gaussian(-0.1, b, 0.0)
        with self.assertRaises(ValueError):
            lw.wake_velocity(U, -0.1, b, 0.0)
        with self.assertRaises(ValueError):
            lw.defect_integral(-0.1, b)
        with self.assertRaises(ValueError):
            lw.drag_from_wake(-0.1, b, RHO, U)
        with self.assertRaises(ValueError):
            lw.full_momentum_deficit(RHO, U, -0.1, b)

    def test_valueerror_sides_zero(self):
        """Step 10 input rejection: sides at 0 raises ValueError on
        plate_drag_per_span."""
        with self.assertRaises(ValueError):
            lw.plate_drag_per_span(U, RHO, NU, C, sides=0)


if __name__ == "__main__":
    unittest.main()
