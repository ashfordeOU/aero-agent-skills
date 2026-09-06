"""Contract test for the stokes-creeping-flow-drag leaf
(aerodynamics/boundary-layer): steady creeping (Stokes, 1851) flow of
a viscous fluid past a sphere at Reynolds number well below one, in
the form Schlichting Boundary-Layer Theory section 4 presents it.

Workflow coverage (SKILL.md Workflow section, wave-44 builder-kit
value-delta sampler rule): step 1, the creeping-flow state fix (sphere
radius a, stream speed U, fluid rho and nu, mu = rho*nu derived) with
the radius-based and diameter-based Reynolds number check, is exercised
by test_radius_reynolds_worked_anchor, test_diameter_reynolds_
worked_anchor_and_twice_radius, test_terminal_creeping_reynolds_check
and by every test through its call arguments; step 2, the streamfunction
and velocity field traverse of the Stokes solution (stokes_streamfunction,
radial_velocity, tangential_velocity with the no-slip surface values and
the fore-aft symmetric far field), by test_no_slip_surface_velocities,
test_surface_streamline_zero_identity, test_far_field_axial_fore_aft_
symmetry, test_far_field_equator_radial_zero, test_tangential_far_field_
equator_and_quarter and test_streamfunction_far_field_anchors; step 3,
the surface pressure traverse with surface_pressure_delta, by
test_surface_pressure_windward_leeward_antisymmetry and
test_surface_pressure_equator_zero; step 4, the wall shear traverse with
wall_shear_stress, by test_wall_shear_peak_anchor_and_mu_identity,
test_wall_shear_zero_at_stagnation_points and test_wall_shear_quarter_
anchor_symmetry; step 5, the drag assembly of the total Stokes drag with
the pressure_drag and friction_drag one-third two-thirds split, by
test_stokes_drag_worked_anchor_and_magnitude_bound,
test_pressure_drag_anchor, test_friction_drag_anchor_and_split_ratio,
test_split_sum_identity_closed_form and test_creeping_linearity_drag_
doubles; step 6, the drag coefficient traverse with drag_coefficient
cross-checked against 24/Re_D, by test_drag_coefficient_anchor and
test_drag_coefficient_cross_routes; step 7, the Oseen correction
traverse with oseen_correction and oseen_drag, by test_oseen_correction_
worked_anchor, test_oseen_correction_half_and_Re_D_equivalence and
test_oseen_drag_anchor_and_ratio; step 8, the settling balance traverse
of the terminal velocity with the creeping Reynolds check, by
test_terminal_velocity_anchor_and_bound and test_terminal_balance_
identity; step 9, the Oseen-corrected terminal velocity traverse, by
test_oseen_terminal_velocity_anchor_and_ordering and test_oseen_terminal_
reproduces_corrected_balance; step 10, the deterministic contract
checks and the input-rejection traverse of non-physical arguments, by
test_deterministic_repeat_calls and the test_valueerror_* methods.

Offline deterministic, stdlib only.  Run:
    python3 scripts/test_stokes_creeping_flow_drag.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stokes_creeping_flow_drag_logic as sl

# Worked-example state (air at standard conditions).
NU = 1.46e-5        # m2/s, air kinematic viscosity
RHO = 1.225         # kg/m3, air density
MU = 1.7885e-5      # Pa s, air dynamic viscosity = RHO * NU
A = 1.0e-4          # m, worked sphere radius (0.1 mm)
U = 0.01            # m/s, stream speed
RHO_P = 1000.0      # kg/m3, water droplet density
AP = 1.0e-5         # m, settling droplet radius (10 microns)
PI = math.pi


def rel_close(x, y, tol):
    """True when x and y agree within the relative tolerance tol."""
    return math.isclose(x, y, rel_tol=tol, abs_tol=0.0)


class ReynoldsNumberTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the creeping-flow state fix."""

    def test_radius_reynolds_worked_anchor(self):
        """Step 1 creeping-flow state check: the radius-based Reynolds
        number Re_a = U*a/nu of the worked sphere is 0.068493151 (low
        end of the creeping range where the Oseen correction matters)."""
        self.assertAlmostEqual(sl.radius_reynolds(U, A, NU), 0.068493151,
                               delta=1e-6)

    def test_diameter_reynolds_worked_anchor_and_twice_radius(self):
        """Step 1 creeping-flow state check: the diameter-based Reynolds
        number Re_D = U*2a/nu is 0.1369863 and exactly twice the
        radius-based value (Cd = 24/Re_D convention)."""
        re_a = sl.radius_reynolds(U, A, NU)
        re_d = sl.diameter_reynolds(U, A, NU)
        self.assertAlmostEqual(re_d, 0.1369863, delta=1e-6)
        self.assertAlmostEqual(re_d, 2.0 * re_a, delta=1e-9)


class DragTests(unittest.TestCase):
    """Steps 5 of the SKILL.md workflow: the drag assembly traverse."""

    def test_stokes_drag_worked_anchor_and_magnitude_bound(self):
        """Step 5 drag assembly: the total Stokes drag of the worked
        sphere is 6*pi*mu*a*U = 3.3712431e-10 N, inside the 3.0e-10 to
        4.0e-10 N magnitude bound."""
        f = sl.stokes_drag(MU, A, U)
        self.assertAlmostEqual(f, 3.3712431e-10, delta=1e-13)
        self.assertGreater(f, 3.0e-10)
        self.assertLess(f, 4.0e-10)

    def test_pressure_drag_anchor(self):
        """Step 5 drag assembly: the pressure (form) drag
        2*pi*mu*a*U = 1.1237477e-10 N is one third of the total."""
        self.assertAlmostEqual(sl.pressure_drag(MU, A, U), 1.1237477e-10,
                               delta=1e-13)

    def test_friction_drag_anchor_and_split_ratio(self):
        """Step 5 drag assembly: the friction drag 4*pi*mu*a*U =
        2.2474954e-10 N is two thirds of the total and exactly twice
        the pressure drag (the 1:2 form-to-friction split)."""
        self.assertAlmostEqual(sl.friction_drag(MU, A, U), 2.2474954e-10,
                               delta=1e-13)
        self.assertAlmostEqual(sl.friction_drag(MU, A, U)
                               / sl.pressure_drag(MU, A, U), 2.0, delta=1e-9)

    def test_split_sum_identity_closed_form(self):
        """Step 5 drag assembly: the closed-form split identity
        pressure_drag + friction_drag - stokes_drag vanishes to float
        noise (relative residual below 1e-12)."""
        residual = (sl.pressure_drag(MU, A, U) + sl.friction_drag(MU, A, U)
                    - sl.stokes_drag(MU, A, U))
        self.assertLess(abs(residual) / sl.stokes_drag(MU, A, U), 1e-12)

    def test_creeping_linearity_drag_doubles(self):
        """Step 5 drag assembly: creeping linearity of the Stokes law,
        the drag at double speed is exactly twice the drag at U (zero
        Reynolds number, no inertia terms)."""
        self.assertAlmostEqual(sl.stokes_drag(MU, A, 2.0 * U)
                               / sl.stokes_drag(MU, A, U), 2.0, delta=1e-9)


class DragCoefficientTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the drag coefficient traverse."""

    def test_drag_coefficient_anchor(self):
        """Step 6 drag coefficient traverse: Cd = 12*mu/(rho*U*a) of the
        worked sphere is 175.2."""
        self.assertAlmostEqual(sl.drag_coefficient(RHO, MU, U, A), 175.2,
                               delta=0.1)

    def test_drag_coefficient_cross_routes(self):
        """Step 6 drag coefficient traverse: 12*mu/(rho*U*a) equals
        24/Re_D and F/(0.5*rho*U^2*pi*a^2), the three independent
        routes to the creeping drag coefficient agree."""
        cd = sl.drag_coefficient(RHO, MU, U, A)
        self.assertTrue(rel_close(cd, 24.0 / sl.diameter_reynolds(U, A, NU),
                                  1e-6))
        f = sl.stokes_drag(MU, A, U)
        self.assertTrue(rel_close(cd, f / (0.5 * RHO * U * U * PI * A * A),
                                  1e-6))


class SurfacePressureShearTests(unittest.TestCase):
    """Steps 3 and 4 of the SKILL.md workflow: the surface pressure and
    wall shear traverses."""

    def test_surface_pressure_windward_leeward_antisymmetry(self):
        """Step 3 surface pressure traverse: p - p_inf is +2.68275e-03 Pa
        at the windward stagnation point (theta = pi) and -2.68275e-03 Pa
        at the downstream pole (theta = 0), the high-pressure-facing-
        the-stream signature; the two sum to zero (antisymmetry)."""
        p_wind = sl.surface_pressure_delta(MU, U, A, PI)
        p_lee = sl.surface_pressure_delta(MU, U, A, 0.0)
        self.assertAlmostEqual(p_wind, 2.68275e-03, delta=1e-6)
        self.assertAlmostEqual(p_lee, -2.68275e-03, delta=1e-6)
        self.assertAlmostEqual(p_wind + p_lee, 0.0, delta=1e-9)

    def test_surface_pressure_equator_zero(self):
        """Step 3 surface pressure traverse: p - p_inf vanishes at the
        equator theta = pi/2 to float noise (anchor residual
        -1.64271060e-19 Pa)."""
        self.assertAlmostEqual(sl.surface_pressure_delta(MU, U, A, PI / 2.0),
                               0.0, delta=1e-12)

    def test_wall_shear_peak_anchor_and_mu_identity(self):
        """Step 4 wall shear traverse: tau_w peaks at 2.68275e-03 Pa at
        the equator theta = pi/2, equal to 1.5*mu*U/a."""
        tau = sl.wall_shear_stress(MU, U, A, PI / 2.0)
        self.assertAlmostEqual(tau, 2.68275e-03, delta=1e-6)
        self.assertAlmostEqual(tau, 1.5 * MU * U / A, delta=1e-9)

    def test_wall_shear_zero_at_stagnation_points(self):
        """Step 4 wall shear traverse: tau_w = 1.5*(mu*U/a)*sin(theta)
        vanishes at the stagnation points theta = 0 and theta = pi to
        float noise."""
        self.assertAlmostEqual(sl.wall_shear_stress(MU, U, A, 0.0), 0.0,
                               delta=1e-12)
        self.assertAlmostEqual(sl.wall_shear_stress(MU, U, A, PI), 0.0,
                               delta=1e-12)

    def test_wall_shear_quarter_anchor_symmetry(self):
        """Step 4 wall shear traverse: tau_w = 1.89699072e-03 Pa at
        theta = pi/4, symmetric about the equator at theta = 3*pi/4."""
        self.assertAlmostEqual(sl.wall_shear_stress(MU, U, A, PI / 4.0),
                               1.89699072e-03, delta=1e-6)
        self.assertAlmostEqual(sl.wall_shear_stress(MU, U, A, 3.0 * PI / 4.0),
                               1.89699072e-03, delta=1e-6)


class VelocityFieldTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the streamfunction and velocity
    field traverse about the sphere."""

    def test_no_slip_surface_velocities(self):
        """Step 2 velocity field traverse: both velocity components
        vanish on the sphere surface r = a at any polar angle (no
        penetration and no slip; anchor residuals at theta = pi/3 are
        0.000e+00 and -0.000e+00)."""
        for theta in (0.0, PI / 3.0, PI / 2.0, PI):
            self.assertAlmostEqual(sl.radial_velocity(U, A, A, theta), 0.0,
                                   delta=1e-12)
            self.assertAlmostEqual(sl.tangential_velocity(U, A, A, theta),
                                   0.0, delta=1e-12)

    def test_surface_streamline_zero_identity(self):
        """Step 2 streamfunction traverse: the Stokes streamfunction is
        identically zero on the sphere surface (the psi = 0 streamline
        is the body)."""
        for theta in (0.0, PI / 3.0, PI / 2.0, PI):
            self.assertAlmostEqual(sl.stokes_streamfunction(U, A, A, theta),
                                   0.0, delta=1e-15)

    def test_far_field_axial_fore_aft_symmetry(self):
        """Step 2 velocity field traverse: on the axis at r = 2a the
        radial velocity is +0.3125*U downstream (theta = 0) and
        -0.3125*U upstream (theta = pi), the fore-aft symmetric field
        with no wake of creeping flow."""
        u_down = sl.radial_velocity(U, A, 2.0 * A, 0.0)
        u_up = sl.radial_velocity(U, A, 2.0 * A, PI)
        self.assertAlmostEqual(u_down, 3.125e-03, delta=1e-9)
        self.assertAlmostEqual(u_down, 0.3125 * U, delta=1e-9)
        self.assertAlmostEqual(u_up, -3.125e-03, delta=1e-9)
        self.assertAlmostEqual(abs(u_down), abs(u_up), delta=1e-9)

    def test_far_field_equator_radial_zero(self):
        """Step 2 velocity field traverse: the radial velocity vanishes
        at the equator theta = pi/2 on r = 2a (anchor residual
        1.91351062e-19 m/s)."""
        self.assertAlmostEqual(sl.radial_velocity(U, A, 2.0 * A, PI / 2.0),
                               0.0, delta=1e-15)

    def test_tangential_far_field_equator_and_quarter(self):
        """Step 2 velocity field traverse: u_theta at r = 2a is
        -0.59375*U = -5.9375e-03 m/s at the equator and
        -4.19844651e-03 m/s at theta = pi/4."""
        self.assertAlmostEqual(sl.tangential_velocity(U, A, 2.0 * A,
                                                      PI / 2.0),
                               -5.9375e-03, delta=1e-9)
        self.assertAlmostEqual(sl.tangential_velocity(U, A, 2.0 * A,
                                                      PI / 2.0),
                               -0.59375 * U, delta=1e-9)
        self.assertAlmostEqual(sl.tangential_velocity(U, A, 2.0 * A,
                                                      PI / 4.0),
                               -4.19844651e-03, delta=1e-6)

    def test_streamfunction_far_field_anchors(self):
        """Step 2 streamfunction traverse: psi(2a, pi/2) = 6.25e-11 m3/s
        (0.625*U*a^2) and psi(2a, pi/4) = 3.125e-11 m3/s, approaching
        the uniform-stream value 0.5*U*r^2*sin(theta)^2 far away."""
        self.assertAlmostEqual(sl.stokes_streamfunction(U, A, 2.0 * A,
                                                        PI / 2.0),
                               6.25e-11, delta=1e-13)
        self.assertAlmostEqual(sl.stokes_streamfunction(U, A, 2.0 * A,
                                                        PI / 2.0),
                               0.625 * U * A * A, delta=1e-13)
        self.assertAlmostEqual(sl.stokes_streamfunction(U, A, 2.0 * A,
                                                        PI / 4.0),
                               3.125e-11, delta=1e-13)


class OseenCorrectionTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the Oseen correction traverse."""

    def test_oseen_correction_worked_anchor(self):
        """Step 7 Oseen correction: the factor 1 + (3/8)*Re_a at the
        worked sphere Re_a = 0.068493151 is 1.025684932, a 2.56849
        percent drag increase."""
        self.assertAlmostEqual(sl.oseen_correction(0.068493151),
                               1.025684932, delta=1e-6)

    def test_oseen_correction_half_and_Re_D_equivalence(self):
        """Step 7 Oseen correction: the factor is 1.1875 at Re_a = 0.5,
        identical to 1 + (3/16)*Re_D at Re_D = 1.0 (the two Reynolds
        conventions give the same first-order correction)."""
        self.assertAlmostEqual(sl.oseen_correction(0.5), 1.1875, delta=1e-12)
        re_d_one = sl.diameter_reynolds(0.5, 1.0e-4, 1.0e-4)
        self.assertAlmostEqual(re_d_one, 1.0, delta=1e-12)
        self.assertAlmostEqual(sl.oseen_correction(0.5),
                               1.0 + (3.0 / 16.0) * re_d_one, delta=1e-12)

    def test_oseen_drag_anchor_and_ratio(self):
        """Step 7 Oseen correction: the Oseen-corrected drag of the
        worked sphere is 3.45783322e-10 N and oseen_drag/stokes_drag
        equals the oseen_correction at Re_a to float noise."""
        f_oseen = sl.oseen_drag(MU, A, U, NU)
        self.assertAlmostEqual(f_oseen, 3.45783322e-10, delta=1e-13)
        ratio = f_oseen / sl.stokes_drag(MU, A, U)
        self.assertAlmostEqual(ratio, sl.oseen_correction(
            sl.radius_reynolds(U, A, NU)), delta=1e-9)


class TerminalVelocityTests(unittest.TestCase):
    """Steps 8 and 9 of the SKILL.md workflow: the settling balance and
    Oseen-corrected terminal velocity traverses."""

    def test_terminal_velocity_anchor_and_bound(self):
        """Step 8 settling balance traverse: the Stokes terminal
        velocity of a 10 micron water droplet in still air is
        (2/9)*(rho_p - rho_f)*g*a^2/mu = 1.21740537e-02 m/s, inside the
        1.1e-2 to 1.3e-2 m/s magnitude bound."""
        ut = sl.terminal_velocity(RHO_P, RHO, MU, AP)
        self.assertAlmostEqual(ut, 1.21740537e-02, delta=1e-6)
        self.assertGreater(ut, 1.1e-2)
        self.assertLess(ut, 1.3e-2)

    def test_terminal_balance_identity(self):
        """Step 8 settling balance traverse: at U_t the Stokes drag
        exactly balances the buoyancy-adjusted weight
        (4/3)*pi*a^3*(rho_p - rho_f)*g (ratio 1 to float noise), the
        closed-form balance with no iteration."""
        ut = sl.terminal_velocity(RHO_P, RHO, MU, AP)
        weight = (4.0 / 3.0) * PI * AP ** 3 * (RHO_P - RHO) * sl.G
        self.assertAlmostEqual(sl.stokes_drag(MU, AP, ut) / weight, 1.0,
                               delta=1e-9)

    def test_terminal_creeping_reynolds_check(self):
        """Step 8 settling balance traverse: the creeping Reynolds check
        at U_t gives Re_D = 0.016676786, below about 0.1 so the pure
        Stokes balance is operative."""
        ut = sl.terminal_velocity(RHO_P, RHO, MU, AP)
        self.assertAlmostEqual(sl.diameter_reynolds(ut, AP, NU),
                               0.016676786, delta=1e-6)
        self.assertLess(sl.diameter_reynolds(ut, AP, NU), 0.1)

    def test_oseen_terminal_velocity_anchor_and_ordering(self):
        """Step 9 Oseen-corrected terminal velocity traverse: the
        corrected value 1.21362229e-02 m/s lies below the Stokes
        terminal velocity 1.21740537e-02 m/s (Oseen drag is higher, so
        the settling speed is lower)."""
        ut = sl.terminal_velocity(RHO_P, RHO, MU, AP)
        ut_o = sl.oseen_terminal_velocity(RHO_P, RHO, MU, AP, NU)
        self.assertAlmostEqual(ut_o, 1.21362229e-02, delta=1e-6)
        self.assertLess(ut_o, ut)

    def test_oseen_terminal_reproduces_corrected_balance(self):
        """Step 9 Oseen-corrected terminal velocity traverse: the closed
        root U satisfies the corrected balance
        U*(1 + (3/8)*U*a/nu) = U_t to float noise, with the Oseen
        factor 1.003126897 at U_t."""
        ut = sl.terminal_velocity(RHO_P, RHO, MU, AP)
        ut_o = sl.oseen_terminal_velocity(RHO_P, RHO, MU, AP, NU)
        self.assertAlmostEqual(
            ut_o * (1.0 + (3.0 / 8.0) * ut_o * AP / NU), ut, delta=1e-9)
        self.assertAlmostEqual(sl.oseen_correction(
            sl.radius_reynolds(ut, AP, NU)), 1.003126897, delta=1e-6)


class DeterminismTests(unittest.TestCase):
    """Step 10 of the SKILL.md workflow: the deterministic contract."""

    def test_deterministic_repeat_calls(self):
        """Step 10 deterministic checks: repeat calls with the same
        arguments return identical values (closed form, no iteration,
        no state)."""
        for fn, args in ((sl.stokes_drag, (MU, A, U)),
                         (sl.oseen_drag, (MU, A, U, NU)),
                         (sl.terminal_velocity, (RHO_P, RHO, MU, AP)),
                         (sl.oseen_terminal_velocity, (RHO_P, RHO, MU, AP,
                                                       NU)),
                         (sl.surface_pressure_delta, (MU, U, A, PI / 3.0))):
            self.assertEqual(fn(*args), fn(*args))


class ValueErrorTests(unittest.TestCase):
    """Step 10 of the SKILL.md workflow: the input-rejection traverse of
    non-physical arguments."""

    def test_valueerror_mu_nonpositive(self):
        """Step 10 input-rejection traverse: every mu argument rejects
        mu = 0 and mu = -1e-5 (no fluid, or negative viscosity)."""
        mu_calls = (
            (sl.stokes_drag, (0.0, A, U)), (sl.stokes_drag, (-1e-5, A, U)),
            (sl.pressure_drag, (0.0, A, U)), (sl.pressure_drag, (-1e-5, A, U)),
            (sl.friction_drag, (0.0, A, U)), (sl.friction_drag, (-1e-5, A, U)),
            (sl.surface_pressure_delta, (0.0, U, A, PI / 2.0)),
            (sl.surface_pressure_delta, (-1e-5, U, A, PI / 2.0)),
            (sl.wall_shear_stress, (0.0, U, A, PI / 2.0)),
            (sl.wall_shear_stress, (-1e-5, U, A, PI / 2.0)),
            (sl.drag_coefficient, (RHO, 0.0, U, A)),
            (sl.drag_coefficient, (RHO, -1e-5, U, A)),
            (sl.oseen_drag, (0.0, A, U, NU)),
            (sl.terminal_velocity, (RHO_P, RHO, 0.0, AP)),
            (sl.oseen_terminal_velocity, (RHO_P, RHO, 0.0, AP, NU)),
        )
        for fn, args in mu_calls:
            with self.assertRaises(ValueError, msg="%s%s" % (fn.__name__,
                                                             args)):
                fn(*args)

    def test_valueerror_a_nonpositive(self):
        """Step 10 input-rejection traverse: every radius argument
        rejects a = 0 and a = -1e-4 (no sphere, or negative radius)."""
        a_calls = (
            (sl.stokes_drag, (MU, 0.0, U)), (sl.stokes_drag, (MU, -1e-4, U)),
            (sl.pressure_drag, (MU, 0.0, U)),
            (sl.friction_drag, (MU, 0.0, U)),
            (sl.surface_pressure_delta, (MU, U, 0.0, PI / 2.0)),
            (sl.wall_shear_stress, (MU, U, 0.0, PI / 2.0)),
            (sl.drag_coefficient, (RHO, MU, U, 0.0)),
            (sl.oseen_drag, (MU, 0.0, U, NU)),
            (sl.terminal_velocity, (RHO_P, RHO, MU, 0.0)),
            (sl.stokes_streamfunction, (U, 0.0, 2.0 * A, PI / 2.0)),
            (sl.stokes_streamfunction, (U, -1e-4, 2.0 * A, PI / 2.0)),
            (sl.radial_velocity, (U, 0.0, 2.0 * A, PI / 2.0)),
            (sl.tangential_velocity, (U, 0.0, 2.0 * A, PI / 2.0)),
        )
        for fn, args in a_calls:
            with self.assertRaises(ValueError, msg="%s%s" % (fn.__name__,
                                                             args)):
                fn(*args)

    def test_valueerror_U_nonpositive(self):
        """Step 10 input-rejection traverse: every stream-speed argument
        rejects U = 0 and U = -0.01 (no stream, or reversed flow)."""
        u_calls = (
            (sl.stokes_drag, (MU, A, 0.0)), (sl.stokes_drag, (MU, A, -0.01)),
            (sl.pressure_drag, (MU, A, 0.0)),
            (sl.friction_drag, (MU, A, 0.0)),
            (sl.surface_pressure_delta, (MU, 0.0, A, PI / 2.0)),
            (sl.surface_pressure_delta, (MU, -0.01, A, PI / 2.0)),
            (sl.wall_shear_stress, (MU, 0.0, A, PI / 2.0)),
            (sl.radius_reynolds, (0.0, A, NU)),
            (sl.radius_reynolds, (-0.01, A, NU)),
            (sl.diameter_reynolds, (0.0, A, NU)),
            (sl.drag_coefficient, (RHO, MU, 0.0, A)),
            (sl.oseen_drag, (MU, A, 0.0, NU)),
        )
        for fn, args in u_calls:
            with self.assertRaises(ValueError, msg="%s%s" % (fn.__name__,
                                                             args)):
                fn(*args)

    def test_valueerror_rho_and_nu_nonpositive(self):
        """Step 10 input-rejection traverse: drag_coefficient rejects
        rho = 0; both Reynolds numbers and both Oseen functions reject
        nu = 0 and nu = -1e-5 (no diffusion)."""
        for rho_bad in (0.0,):
            with self.assertRaises(ValueError):
                sl.drag_coefficient(rho_bad, MU, U, A)
        for nu_bad in (0.0, -1e-5):
            with self.assertRaises(ValueError):
                sl.radius_reynolds(U, A, nu_bad)
            with self.assertRaises(ValueError):
                sl.diameter_reynolds(U, A, nu_bad)
            with self.assertRaises(ValueError):
                sl.oseen_drag(MU, A, U, nu_bad)
            with self.assertRaises(ValueError):
                sl.oseen_terminal_velocity(RHO_P, RHO, MU, AP, nu_bad)

    def test_valueerror_field_functions_r_below_a(self):
        """Step 10 input-rejection traverse: the three field functions
        reject r = 0.5*a inside the sphere (the flow occupies r >= a);
        oseen_correction rejects a negative radius-based Reynolds
        number (Re_a = -0.1)."""
        for theta in (0.0, PI / 3.0, PI / 2.0):
            with self.assertRaises(ValueError):
                sl.stokes_streamfunction(U, A, 0.5 * A, theta)
            with self.assertRaises(ValueError):
                sl.radial_velocity(U, A, 0.5 * A, theta)
            with self.assertRaises(ValueError):
                sl.tangential_velocity(U, A, 0.5 * A, theta)
        with self.assertRaises(ValueError):
            sl.oseen_correction(-0.1)

    def test_valueerror_terminal_buoyancy_rho_particle(self):
        """Step 10 input-rejection traverse: both terminal-velocity
        functions reject a neutrally buoyant (rho_particle =
        rho_fluid) or positively buoyant (rho_particle below
        rho_fluid) sphere, which does not settle."""
        with self.assertRaises(ValueError):
            sl.terminal_velocity(RHO, RHO, MU, AP)
        with self.assertRaises(ValueError):
            sl.terminal_velocity(0.5 * RHO, RHO, MU, AP)
        with self.assertRaises(ValueError):
            sl.oseen_terminal_velocity(RHO, RHO, MU, AP, NU)
        with self.assertRaises(ValueError):
            sl.oseen_terminal_velocity(0.5 * RHO, RHO, MU, AP, NU)
        with self.assertRaises(ValueError):
            sl.terminal_velocity(0.0, RHO, MU, AP)
        with self.assertRaises(ValueError):
            sl.terminal_velocity(RHO_P, 0.0, MU, AP)


if __name__ == "__main__":
    unittest.main()
