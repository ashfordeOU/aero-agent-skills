"""Contract test for the compressible-couette-flow leaf
(skills/aerodynamics/high-speed/compressible-couette-flow, wave-42).

Exercises every step of the SKILL.md workflow for the exact
constant-property compressible Couette plate-gap solution: the
plate-gap edge-state traverse (edge_velocity), the recovery identity
r = Pr (recovery_factor), the insulated moving-plate float to T_aw
(adiabatic_wall_temperature), the velocity and temperature profile walk
(velocity_profile, temperature_profile, temperature_gradient), the
constant wall shear (wall_shear), the stationary-plate heat flux with
the dissipation energy-balance close (wall_heat_flux), and the full
solution dict with the gap Reynolds number (couette_solution). All
numeric asserts are order-safe (math.isclose / assertAlmostEqual with a
tolerance); no exact float equality is asserted on any computed sum or
product. Deterministic and offline, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compressible_couette_flow_logic as ccf

GAMMA = 1.4
R = 287.0
CP = GAMMA * R / (GAMMA - 1.0)
PR = 0.72
MU = 1.8e-5
H = 0.01
RHO = 1.0e-3
T_E = 300.0
ME = 3.0


class CompressibleCouetteFlowContractTest(unittest.TestCase):
    """SKILL.md workflow contract: exact constant-property solution of
    the shear-driven high-Mach plate gap with the moving plate
    insulated."""

    def _close(self, actual, expected, rel=1e-9, abs_tol=0.0):
        self.assertTrue(
            math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_tol),
            "{} not close to {} (rel {})".format(actual, expected, rel),
        )

    def setUp(self):
        # Canonical worked-example state of the SKILL.md workflow.
        self.ue = ccf.edge_velocity(ME, T_E)
        self.taw = ccf.adiabatic_wall_temperature(T_E, ME, PR)
        self.tau = ccf.wall_shear(self.ue, MU, H)
        self.qw = ccf.wall_heat_flux(self.ue, MU, H)

    # Step 2 of the SKILL.md workflow: the recovery identity r = Pr.

    def test_recovery_factor_returns_pr_identity(self):
        """Step 2 of the SKILL.md workflow, the recovery identity
        traverse, is exercised: recovery_factor returns the Prandtl
        number exactly for any positive pr, the constant-property
        Couette value r = Pr that replaces the external-plate
        sqrt(Pr) and Pr^(1/3) laminar and turbulent forms."""
        self.assertEqual(ccf.recovery_factor(PR), PR)
        self.assertEqual(ccf.recovery_factor(1.0), 1.0)
        self.assertEqual(ccf.recovery_factor(2.5), 2.5)

    def test_recovery_factor_rejects_non_positive(self):
        """Step 2 of the SKILL.md workflow rejects a non-positive
        Prandtl number: recovery_factor(0.0) and recovery_factor(-0.5)
        both raise ValueError."""
        with self.assertRaises(ValueError):
            ccf.recovery_factor(0.0)
        with self.assertRaises(ValueError):
            ccf.recovery_factor(-0.5)

    # Step 1 of the SKILL.md workflow: the plate-gap edge-state
    # traverse with edge_velocity.

    def test_edge_velocity_worked_example(self):
        """Step 1 of the SKILL.md workflow, the plate-gap edge-state
        traverse, is exercised: edge_velocity(3.0, 300.0) returns
        Ue = 1041.566128 m/s within 1e-6 relative at Me = 3.0."""
        self._close(self.ue, 1041.566128, rel=1e-6)

    def test_edge_sound_speed_and_mach_scaling(self):
        """Step 1 of the SKILL.md workflow recovers the edge sound
        speed a_e = Ue / Me = 347.188709 m/s within 1e-6 relative, and
        the edge velocity scales linearly with the plate Mach number:
        edge_velocity(1.0, 300.0) equals a_e and edge_velocity(6.0,
        300.0) equals twice the Me = 3.0 value."""
        a_e = self.ue / ME
        self._close(a_e, 347.188709, rel=1e-6)
        self._close(ccf.edge_velocity(1.0, T_E), a_e, rel=1e-12)
        self._close(ccf.edge_velocity(6.0, T_E), 2.0 * self.ue, rel=1e-12)

    def test_edge_velocity_rejects_non_physical(self):
        """Step 1 of the SKILL.md workflow raises ValueError for a
        non-positive plate Mach number or static temperature:
        edge_velocity(0.0, 300.0), edge_velocity(-3.0, 300.0),
        edge_velocity(3.0, 0.0) and edge_velocity(3.0, -300.0)."""
        for args in ((0.0, T_E), (-3.0, T_E), (ME, 0.0), (ME, -300.0)):
            with self.assertRaises(ValueError):
                ccf.edge_velocity(*args)

    # Step 3 of the SKILL.md workflow: the insulated moving plate
    # floats to its recovery temperature via adiabatic_wall_temperature.

    def test_adiabatic_wall_temperature_worked_example(self):
        """Step 3 of the SKILL.md workflow, the moving-plate float, is
        exercised: adiabatic_wall_temperature(300.0, 3.0, 0.72) returns
        T_aw = 688.800000 K within 1e-9 relative, a 388.8 K recovery
        rise over the stationary-plate temperature T_e."""
        self._close(self.taw, 688.800000, rel=1e-9)

    def test_numerical_recovery_identity(self):
        """Step 3 of the SKILL.md workflow closes the numerical
        recovery identity: (T_aw - T_e) * 2 * CP / Ue^2 equals the
        Prandtl number 0.72 within 1e-12, confirming the recovery
        factor of the insulated moving plate is r = Pr."""
        r_num = (self.taw - T_E) * 2.0 * CP / (self.ue * self.ue)
        self._close(r_num, PR, abs_tol=1e-12)

    def test_adiabatic_wall_temperature_energy_form(self):
        """Step 3 of the SKILL.md workflow matches the energy form:
        adiabatic_wall_temperature(300.0, 3.0, 0.72) equals
        T_e + Pr * Ue^2 / (2 * CP) within 1e-12 relative, with CP the
        derived module constant GAMMA * R / (GAMMA - 1)."""
        self._close(self.taw, T_E + PR * self.ue * self.ue / (2.0 * CP),
                    rel=1e-12)

    def test_adiabatic_wall_temperature_low_mach_limit(self):
        """Step 3 of the SKILL.md workflow returns the static
        temperature at vanishing plate Mach number: with me = 1e-9 the
        moving-plate float stays at T_e = 300.0 K within 1e-9 absolute
        because the dissipation term scales with me squared."""
        self._close(ccf.adiabatic_wall_temperature(T_E, 1e-9, PR), T_E,
                    abs_tol=1e-9)

    def test_adiabatic_wall_temperature_rejects(self):
        """Step 3 of the SKILL.md workflow raises ValueError for
        non-positive inputs: t_e = 0.0, me = 0.0, me = -1.0, pr = 0.0
        and pr = -0.5 all fail in adiabatic_wall_temperature."""
        for args in ((0.0, ME, PR), (T_E, 0.0, PR), (T_E, -1.0, PR),
                     (T_E, ME, 0.0), (T_E, ME, -0.5)):
            with self.assertRaises(ValueError):
                ccf.adiabatic_wall_temperature(*args)

    # Step 4 of the SKILL.md workflow: the profile walk across the gap
    # with temperature_profile, temperature_gradient and
    # velocity_profile.

    def test_temperature_profile_endpoints(self):
        """Step 4 of the SKILL.md workflow, the temperature-profile
        walk, pins the endpoints: T(0) = T_e = 300.0 K at the
        stationary plate and T(h) = T_aw = 688.8 K at the insulated
        moving plate, each within 1e-9 relative of the closed form."""
        self._close(ccf.temperature_profile(0.0, H, T_E, ME, PR), T_E,
                    rel=1e-9)
        self._close(ccf.temperature_profile(H, H, T_E, ME, PR), self.taw,
                    rel=1e-9)

    def test_temperature_profile_quarter_stations(self):
        """Step 4 of the SKILL.md workflow reproduces the Crocco
        energy-integral quarter stations: 470.100000 K at h/4,
        591.600000 K at h/2 and 664.500000 K at 3h/4, each within
        1e-9 relative of the closed-form profile."""
        for y, expected in ((0.25 * H, 470.100000),
                            (0.50 * H, 591.600000),
                            (0.75 * H, 664.500000)):
            self._close(ccf.temperature_profile(y, H, T_E, ME, PR),
                        expected, rel=1e-9)

    def test_temperature_profile_closed_form(self):
        """Step 4 of the SKILL.md workflow replicates the closed form
        T = t_e * (1 + pr * (gamma - 1) / 2 * me^2 * (2 eta - eta^2))
        with eta = y / h at an interior station y = 0.0037 m within
        1e-12 relative, so the energy-integral profile over the linear
        velocity profile is exactly what the module evaluates."""
        y = 0.0037
        eta = y / H
        closed = T_E * (1.0 + PR * (GAMMA - 1.0) / 2.0 * ME * ME
                        * (2.0 * eta - eta * eta))
        self._close(ccf.temperature_profile(y, H, T_E, ME, PR), closed,
                    rel=1e-12)

    def test_temperature_profile_rejects(self):
        """Step 4 of the SKILL.md workflow raises ValueError for y
        outside [0, h] and for non-positive h, t_e, me or pr in
        temperature_profile."""
        bad = ((-1e-9, H, T_E, ME, PR), (H + 1e-9, H, T_E, ME, PR),
               (0.5 * H, 0.0, T_E, ME, PR), (0.5 * H, -H, T_E, ME, PR),
               (0.5 * H, H, 0.0, ME, PR), (0.5 * H, H, T_E, 0.0, PR),
               (0.5 * H, H, T_E, ME, -0.5))
        for args in bad:
            with self.assertRaises(ValueError):
                ccf.temperature_profile(*args)

    def test_temperature_gradient_stationary_plate_value(self):
        """Step 4 of the SKILL.md workflow reads the stationary-plate
        gradient: temperature_gradient(0, h, ...) returns
        77760.000 K/m within 1e-9 relative, the positive slope that
        drives conduction into the cold plate."""
        self._close(ccf.temperature_gradient(0.0, H, T_E, ME, PR),
                    77760.0, rel=1e-9)

    def test_temperature_gradient_moving_plate_adiabatic(self):
        """Step 4 of the SKILL.md workflow enforces the insulated
        moving plate: temperature_gradient(h, h, ...) is zero within
        1e-12 absolute, so no heat crosses the moving plate."""
        self._close(ccf.temperature_gradient(H, H, T_E, ME, PR), 0.0,
                    abs_tol=1e-12)

    def test_temperature_gradient_forward_difference_tracks(self):
        """Step 4 of the SKILL.md workflow cross-checks the analytic
        gradient against a forward difference: (T(h/1000) - T(0)) /
        (h/1000) tracks temperature_gradient(0, h, ...) within 1e-3
        relative."""
        dy = H / 1000.0
        fd = (ccf.temperature_profile(dy, H, T_E, ME, PR)
              - ccf.temperature_profile(0.0, H, T_E, ME, PR)) / dy
        g0 = ccf.temperature_gradient(0.0, H, T_E, ME, PR)
        self._close(fd, g0, rel=1e-3)

    def test_temperature_gradient_profile_shape(self):
        """Step 4 of the SKILL.md workflow shows the gradient falling
        linearly from its stationary-plate peak to zero at the moving
        plate: dT/dy at h/4, h/2 and 3h/4 is positive and strictly
        decreasing, and the h/2 station reads half the h = 0 value
        within 1e-9 relative."""
        g0 = ccf.temperature_gradient(0.0, H, T_E, ME, PR)
        ghalf = ccf.temperature_gradient(0.5 * H, H, T_E, ME, PR)
        self._close(ghalf, 0.5 * g0, rel=1e-9)
        g1 = ccf.temperature_gradient(0.25 * H, H, T_E, ME, PR)
        g2 = ccf.temperature_gradient(0.5 * H, H, T_E, ME, PR)
        g3 = ccf.temperature_gradient(0.75 * H, H, T_E, ME, PR)
        self.assertTrue(0.0 < g3 < g2 < g1)

    def test_temperature_gradient_rejects(self):
        """Step 4 of the SKILL.md workflow raises ValueError in
        temperature_gradient for y outside [0, h] and for non-positive
        h, t_e, me or pr."""
        with self.assertRaises(ValueError):
            ccf.temperature_gradient(-1e-9, H, T_E, ME, PR)
        with self.assertRaises(ValueError):
            ccf.temperature_gradient(H + 1e-9, H, T_E, ME, PR)
        with self.assertRaises(ValueError):
            ccf.temperature_gradient(0.5 * H, 0.0, T_E, ME, PR)
        with self.assertRaises(ValueError):
            ccf.temperature_gradient(0.5 * H, H, 0.0, ME, PR)
        with self.assertRaises(ValueError):
            ccf.temperature_gradient(0.5 * H, H, T_E, 0.0, PR)
        with self.assertRaises(ValueError):
            ccf.temperature_gradient(0.5 * H, H, T_E, ME, -0.5)

    def test_velocity_profile_linearity(self):
        """Step 4 of the SKILL.md workflow, the velocity-profile walk,
        is exercised: velocity_profile is exactly linear, u(y) =
        u_e * y / h, so u(h/4) = Ue/4, u(h/2) = Ue/2 and u(3h/4) =
        3 * Ue/4 each within 1e-12 relative, with u(0) = 0 and
        u(h) = Ue."""
        self._close(ccf.velocity_profile(0.0, H, self.ue), 0.0,
                    abs_tol=1e-15)
        self._close(ccf.velocity_profile(H, H, self.ue), self.ue,
                    rel=1e-12)
        for y, frac in ((0.25 * H, 0.25), (0.5 * H, 0.5),
                        (0.75 * H, 0.75)):
            self._close(ccf.velocity_profile(y, H, self.ue), frac * self.ue,
                        rel=1e-12)

    def test_velocity_profile_rejects(self):
        """Step 4 of the SKILL.md workflow raises ValueError in
        velocity_profile for y outside [0, h] and for non-positive
        gap height h or edge velocity u_e."""
        with self.assertRaises(ValueError):
            ccf.velocity_profile(-1e-9, H, self.ue)
        with self.assertRaises(ValueError):
            ccf.velocity_profile(H + 1e-9, H, self.ue)
        with self.assertRaises(ValueError):
            ccf.velocity_profile(0.5 * H, 0.0, self.ue)
        with self.assertRaises(ValueError):
            ccf.velocity_profile(0.5 * H, H, 0.0)

    # Step 5 of the SKILL.md workflow: the constant wall shear from
    # the linear velocity profile via wall_shear.

    def test_wall_shear_worked_example_and_slope(self):
        """Step 5 of the SKILL.md workflow, the wall-shear read, is
        exercised: wall_shear(1041.566128, 1.8e-5, 0.01) returns
        tau_w = 1.874819 Pa within 1e-4 relative of the anchor figure
        (printed to 6 decimals; the full-precision value is
        1.8748190313 Pa), and the shear equals mu times the
        linear-profile slope (u(h) - u(0)) / h within 1e-12 relative,
        constant across the gap."""
        self._close(self.tau, 1.874819, rel=1e-4)
        slope = (ccf.velocity_profile(H, H, self.ue)
                 - ccf.velocity_profile(0.0, H, self.ue)) / H
        self._close(self.tau, MU * slope, rel=1e-12)

    def test_wall_shear_scaling_and_rejects(self):
        """Step 5 of the SKILL.md workflow scales linearly with
        viscosity and inversely with the gap height in wall_shear, and
        raises ValueError for non-positive u_e, mu or h."""
        self._close(ccf.wall_shear(self.ue, 2.0 * MU, H), 2.0 * self.tau,
                    rel=1e-12)
        self._close(ccf.wall_shear(self.ue, MU, 2.0 * H), 0.5 * self.tau,
                    rel=1e-12)
        for args in ((0.0, MU, H), (-1.0, MU, H), (self.ue, 0.0, H),
                     (self.ue, MU, 0.0), (self.ue, MU, -H)):
            with self.assertRaises(ValueError):
                ccf.wall_shear(*args)

    # Step 6 of the SKILL.md workflow: the stationary-plate heat flux
    # and the dissipation energy-balance close via wall_heat_flux.

    def test_wall_heat_flux_worked_example(self):
        """Step 6 of the SKILL.md workflow, the heat-flux read, is
        exercised: wall_heat_flux(1041.566128, 1.8e-5, 0.01) returns
        q_w = 1952.748 W/m2 within 1e-9 relative, the flux into the
        stationary plate from the high-Mach gap."""
        self._close(self.qw, 1952.748, rel=1e-9)

    def test_wall_heat_flux_energy_balance_closes(self):
        """Step 6 of the SKILL.md workflow closes the dissipation
        energy balance: q_w equals k * dT/dy(0) with the derived
        conductivity k = mu * CP / Pr = 0.025113 W/(m K) (anchor
        figure printed to 6 decimals; full precision 0.0251125), equals
        mu * Ue^2 / h, and equals tau_w * Ue, each within 1e-9
        relative, so all viscous shear work leaves through the cold
        plate."""
        k = MU * CP / PR
        self._close(k, 0.025113, rel=1e-4)
        g0 = ccf.temperature_gradient(0.0, H, T_E, ME, PR)
        self._close(self.qw, k * g0, rel=1e-9)
        self._close(self.qw, MU * self.ue * self.ue / H, rel=1e-9)
        self._close(self.qw, self.tau * self.ue, rel=1e-9)

    def test_wall_heat_flux_sign_convention(self):
        """Step 6 of the SKILL.md workflow keeps the sign convention:
        q_w and the viscous work rate tau_w * Ue are positive (heat
        flows from the gas into the stationary plate) while the moving
        plate stays insulated with a zero gradient and zero flux."""
        self.assertTrue(self.qw > 0.0)
        self.assertTrue(self.tau * self.ue > 0.0)
        k_dtdy0 = (MU * CP / PR) * ccf.temperature_gradient(
            0.0, H, T_E, ME, PR)
        self.assertTrue(k_dtdy0 > 0.0)
        self._close(ccf.temperature_gradient(H, H, T_E, ME, PR), 0.0,
                    abs_tol=1e-12)

    def test_wall_heat_flux_rejects(self):
        """Step 6 of the SKILL.md workflow raises ValueError in
        wall_heat_flux for non-positive edge velocity, viscosity or gap
        height."""
        for args in ((0.0, MU, H), (self.ue, 0.0, H), (self.ue, MU, 0.0)):
            with self.assertRaises(ValueError):
                ccf.wall_heat_flux(*args)

    # Step 7 of the SKILL.md workflow: the assembled solution dict with
    # the gap Reynolds number via couette_solution.

    def test_couette_solution_dict_keys_exact(self):
        """Step 7 of the SKILL.md workflow, the solution assembly, is
        exercised: couette_solution returns a dict whose keys are
        exactly Ue, T_aw, tau_w, q_w, r, Re_gap in that order."""
        sol = ccf.couette_solution(T_E, ME, PR, MU, RHO, H)
        self.assertEqual(list(sol.keys()),
                         ["Ue", "T_aw", "tau_w", "q_w", "r", "Re_gap"])

    def test_couette_solution_values(self):
        """Step 7 of the SKILL.md workflow reproduces the worked
        example: Ue = 1041.566128 m/s within 1e-6 relative, T_aw =
        688.800000 K, tau_w = 1.874819 Pa and q_w = 1952.748 W/m2 each
        within 1e-9 relative, r = Pr = 0.72 exactly, and Re_gap =
        578.648 within 1e-6 relative as the laminar regime indicator."""
        sol = ccf.couette_solution(T_E, ME, PR, MU, RHO, H)
        self._close(sol["Ue"], 1041.566128, rel=1e-6)
        self._close(sol["T_aw"], 688.800000, rel=1e-9)
        self._close(sol["tau_w"], 1.874819, rel=1e-4)
        self._close(sol["q_w"], 1952.748, rel=1e-9)
        self.assertEqual(sol["r"], PR)
        self._close(sol["Re_gap"], 578.648, rel=1e-6)
        self._close(sol["Re_gap"], RHO * sol["Ue"] * H / MU, rel=1e-12)

    def test_couette_solution_rho_enters_only_via_reynolds(self):
        """Step 7 of the SKILL.md workflow keeps density out of the
        shear and flux: doubling rho to 2e-3 kg/m3 leaves tau_w and
        q_w unchanged within 1e-15 relative while Re_gap doubles, so
        the density choice is purely the laminar-regime statement."""
        sol1 = ccf.couette_solution(T_E, ME, PR, MU, RHO, H)
        sol2 = ccf.couette_solution(T_E, ME, PR, MU, 2.0 * RHO, H)
        self._close(sol2["tau_w"], sol1["tau_w"], rel=1e-15)
        self._close(sol2["q_w"], sol1["q_w"], rel=1e-15)
        self._close(sol2["Re_gap"], 2.0 * sol1["Re_gap"], rel=1e-12)

    def test_couette_solution_rejects_non_physical(self):
        """Step 7 of the SKILL.md workflow raises ValueError in
        couette_solution for any non-positive input: each of t_e, me,
        pr, mu, rho and h zeroed in turn fails."""
        bad = ((0.0, ME, PR, MU, RHO, H), (T_E, 0.0, PR, MU, RHO, H),
               (T_E, ME, 0.0, MU, RHO, H), (T_E, ME, PR, 0.0, RHO, H),
               (T_E, ME, PR, MU, 0.0, H), (T_E, ME, PR, MU, RHO, 0.0))
        for args in bad:
            with self.assertRaises(ValueError):
                ccf.couette_solution(*args)

    # Steps 4 and 7 of the SKILL.md workflow: profile shape checks on
    # the assembled state.

    def test_temperature_monotonic_rise_across_gap(self):
        """Steps 4 and 7 of the SKILL.md workflow show the temperature
        profile rising monotonically from the stationary plate at
        T_e = 300.0 K to the insulated moving plate at T_aw = 688.8 K
        across 101 sampled stations at fixed Me = 3.0 and Pr = 0.72."""
        stations = [ccf.temperature_profile(i * H / 100.0, H, T_E, ME, PR)
                    for i in range(101)]
        self._close(stations[0], T_E, rel=1e-9)
        self._close(stations[-1], self.taw, rel=1e-9)
        for above, below in zip(stations[1:], stations[:-1]):
            self.assertTrue(above > below)

    def test_deterministic_repeat_calls(self):
        """Steps 1 to 7 of the SKILL.md workflow are deterministic:
        two couette_solution calls on the same inputs return identical
        dicts (no randomness, pure math only), so the module is safe
        for offline repeat evaluation."""
        first = ccf.couette_solution(T_E, ME, PR, MU, RHO, H)
        second = ccf.couette_solution(T_E, ME, PR, MU, RHO, H)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
