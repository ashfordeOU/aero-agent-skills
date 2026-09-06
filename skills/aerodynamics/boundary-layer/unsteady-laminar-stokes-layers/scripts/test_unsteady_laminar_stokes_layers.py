"""Contract test for the unsteady-laminar-stokes-layers leaf
(aerodynamics/boundary-layer): exact unsteady laminar Stokes layers of
an infinite flat plate, closed-form solutions of the vorticity
diffusion equation u_t = nu * u_yy.

Workflow coverage (SKILL.md Workflow section, wave-43 builder-kit
value-delta sampler rule): step 1, the flow-state fix (uniform nu,
rho, plate speed U and the first-versus-second problem choice), is
exercised by every test through its call arguments; step 2, the
first-problem similarity profile traverse with the erfc Rayleigh-layer
profile u/U = erfc(y/(2*sqrt(nu*t))), by test_wall_velocity_equals_U_
exactly, test_similarity_profile_matches_erfc, test_profile_eta_one_
anchor, test_far_field_decay and test_front_arrival_fixed_station;
step 3, the layer-edge traverse of the rayleigh-layer growth
delta = 3.6428*sqrt(nu*t), by test_layer_edge_anchor_thickness,
test_edge_u_over_U_equals_01, test_layer_growth_sqrt_time_ratio; step
4, the shear-decay traverse of the first-problem wall shear
rho*U*sqrt(nu/(pi*t)) with its 1/sqrt(t) decay, by
test_wall_shear_anchor_decay, test_shear_decade_ratio and
test_shear_sqrt_t_invariant; step 5, the displacement-thickness
traverse of delta* = 2*sqrt(nu*t/pi) with the momentum balance
rho*U*d(delta*)/dt = tau_w, by test_displacement_thickness_anchor,
test_displacement_ratio and test_momentum_balance_identity; step 6,
the penetration-depth traverse of sqrt(2*nu/omega), by
test_penetration_depth_anchor; step 7, the oscillating-field traverse
of the exponential-cosine velocity field with amplitude decay
exp(-y/delta) and phase lag y/delta, by test_wall_no_slip_cosine,
test_phase_zero_gives_local_amplitude, test_velocity_cycle_at_
penetration_depth and test_amplitude_profile_decay; step 8, the
shear-phase traverse of the wall shear amplitude rho*U*sqrt(nu*omega)
with its 45 degree phase lead and one-eighth-period zero crossing, by
test_shear_amplitude_anchor, test_shear_amplitude_mu_identity,
test_shear_waveform_phase_lead, test_shear_zero_crossing_at_pi_over_4
and test_shear_negative_peak; step 9, the input-rejection traverse of
non-physical arguments, by the test_valueerror_* methods.

Offline deterministic, stdlib only.  Run:
    python3 scripts/test_unsteady_laminar_stokes_layers.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unsteady_laminar_stokes_layers_logic as sl

NU = 1.46e-5   # m2/s, air at standard conditions (module constant)
RHO = 1.225    # kg/m3
U = 30.0       # m/s, plate speed
OMEGA = 50.0   # rad/s, plate oscillation frequency


class StokesFirstProblemTests(unittest.TestCase):
    """Stokes first problem (Rayleigh layer), impulsively started plate."""

    def test_wall_velocity_equals_U_exactly(self):
        """Step 2 of the SKILL.md workflow, the similarity profile
        traverse: the no-slip wall value of the erfc Rayleigh layer is
        U exactly for any time (erfc(0) = 1)."""
        for t in (1e-6, 0.001, 1.0, 10.0):
            self.assertEqual(sl.stokes_first_velocity(U, NU, 0.0, t), U)

    def test_similarity_profile_matches_erfc(self):
        """Step 2 of the SKILL.md workflow, the erfc similarity profile
        traverse: u/U at a station y equals math.erfc(y/(2*sqrt(nu*t)))
        and the profile is monotone decreasing from 1 at the wall."""
        t = 0.001
        prev = 1.0
        for eta in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 6.0):
            y = 2.0 * eta * math.sqrt(NU * t)
            ratio = sl.stokes_first_velocity(U, NU, y, t) / U
            self.assertAlmostEqual(ratio, math.erfc(eta), delta=1e-12)
            self.assertLessEqual(ratio, prev)
            prev = ratio

    def test_profile_eta_one_anchor(self):
        """Step 2 of the SKILL.md workflow, the similarity profile
        traverse: at eta = 1 (y = 2*sqrt(nu*t)) the Rayleigh layer
        ratio u/U equals the prep anchor 0.1572992071 within 1e-6."""
        t = 0.001
        y = 2.0 * math.sqrt(NU * t)
        ratio = sl.stokes_first_velocity(U, NU, y, t) / U
        self.assertAlmostEqual(ratio, 0.1572992071, delta=1e-6)

    def test_far_field_decay(self):
        """Step 2 of the SKILL.md workflow, the similarity profile
        traverse: deep in the fluid (y = 1 m at t = 10 s, eta about
        41) the Rayleigh layer velocity ratio falls below 1e-12."""
        ratio = sl.stokes_first_velocity(U, NU, 1.0, 10.0) / U
        self.assertLess(abs(ratio), 1e-12)

    def test_front_arrival_fixed_station(self):
        """Step 2 of the SKILL.md workflow, the similarity profile
        traverse: the front arrival at a fixed station y = 1 mm in air
        matches the anchor history 0.0, 1.926887, 16.752282 and
        25.595499 m/s at 1, 10, 100 ms and 1 s within 1e-3 m/s."""
        y = 0.001
        self.assertAlmostEqual(sl.stokes_first_velocity(U, NU, y, 0.001),
                               0.0, delta=1e-3)
        self.assertAlmostEqual(sl.stokes_first_velocity(U, NU, y, 0.01),
                               1.926887, delta=1e-3)
        self.assertAlmostEqual(sl.stokes_first_velocity(U, NU, y, 0.1),
                               16.752282, delta=1e-3)
        self.assertAlmostEqual(sl.stokes_first_velocity(U, NU, y, 1.0),
                               25.595499, delta=1e-3)

    def test_layer_edge_anchor_thickness(self):
        """Step 3 of the SKILL.md workflow, the layer-edge traverse:
        the Rayleigh layer edge delta = 3.6428*sqrt(nu*t) is
        4.40161e-4 m at t = 0.001 s within 1e-6 m."""
        self.assertAlmostEqual(sl.rayleigh_layer_thickness(NU, 0.001),
                               4.40161e-4, delta=1e-6)

    def test_edge_u_over_U_equals_01(self):
        """Step 3 of the SKILL.md workflow, the layer-edge traverse:
        at y = delta the Rayleigh layer has u/U = 0.0099994, that is
        0.01 within 1e-3, at every time (self-similar collapse)."""
        for t in (0.001, 0.01, 0.1, 1.0, 10.0):
            d = sl.rayleigh_layer_thickness(NU, t)
            ratio = sl.stokes_first_velocity(U, NU, d, t) / U
            self.assertAlmostEqual(ratio, 0.01, delta=1e-3)
            self.assertAlmostEqual(ratio, 0.0099994, delta=1e-6)

    def test_layer_growth_sqrt_time_ratio(self):
        """Step 3 of the SKILL.md workflow, the layer-edge traverse:
        the layer edge grows as sqrt(t), delta(t2)/delta(t1) =
        sqrt(t2/t1), so delta(10 s)/delta(0.001 s) = 100 within
        1e-9."""
        ratio = (sl.rayleigh_layer_thickness(NU, 10.0) /
                 sl.rayleigh_layer_thickness(NU, 0.001))
        self.assertAlmostEqual(ratio, 100.0, delta=1e-6)

    def test_wall_shear_anchor_decay(self):
        """Step 4 of the SKILL.md workflow, the shear-decay traverse:
        the first-problem wall shear rho*U*sqrt(nu/(pi*t)) is
        2.505295 Pa at t = 0.001 s within 1e-3 Pa, inside the
        2.0 to 3.0 Pa magnitude bound."""
        tau = sl.stokes_first_wall_shear(RHO, U, NU, 0.001)
        self.assertAlmostEqual(tau, 2.505295, delta=1e-3)
        self.assertGreater(tau, 2.0)
        self.assertLess(tau, 3.0)

    def test_shear_decade_ratio(self):
        """Step 4 of the SKILL.md workflow, the shear-decay traverse:
        the wall shear decays as 1/sqrt(t), so over the anchor decade
        0.001 to 10 s the ratio tau_w(10)/tau_w(0.001) = 0.01 =
        sqrt(1e-4) within 1e-9."""
        ratio = (sl.stokes_first_wall_shear(RHO, U, NU, 10.0) /
                 sl.stokes_first_wall_shear(RHO, U, NU, 0.001))
        self.assertAlmostEqual(ratio, 0.01, delta=1e-9)

    def test_shear_sqrt_t_invariant(self):
        """Step 4 of the SKILL.md workflow, the shear-decay traverse:
        tau_w*sqrt(t) = rho*U*sqrt(nu/pi) = 0.0792244 Pa sqrt(s) is
        constant across the whole time table within 1e-6."""
        values = [sl.stokes_first_wall_shear(RHO, U, NU, t) * math.sqrt(t)
                  for t in (0.001, 0.01, 0.1, 1.0, 10.0)]
        for v in values:
            self.assertAlmostEqual(v, 0.0792244, delta=1e-6)
        self.assertLess(max(values) - min(values), 1e-12)

    def test_displacement_thickness_anchor(self):
        """Step 5 of the SKILL.md workflow, the displacement-thickness
        traverse: delta* = 2*sqrt(nu*t/pi) is 0.136343 mm at 1 ms and
        grows as sqrt(t) to 13.6343 mm at 10 s."""
        ds1 = sl.stokes_first_displacement_thickness(NU, 0.001)
        self.assertAlmostEqual(ds1, 0.000136343, delta=1e-8)
        ds2 = sl.stokes_first_displacement_thickness(NU, 10.0)
        self.assertAlmostEqual(ds2, 0.0136343, delta=1e-6)
        self.assertAlmostEqual(ds2 / ds1, 100.0, delta=1e-6)

    def test_displacement_ratio(self):
        """Step 5 of the SKILL.md workflow, the displacement-thickness
        traverse: delta*/delta = 2/sqrt(pi)/3.6428 = 0.3098 within
        1e-3 at any time."""
        for t in (0.001, 0.1, 10.0):
            ratio = (sl.stokes_first_displacement_thickness(NU, t) /
                     sl.rayleigh_layer_thickness(NU, t))
            self.assertAlmostEqual(ratio, 0.3098, delta=1e-3)

    def test_momentum_balance_identity(self):
        """Step 5 of the SKILL.md workflow, the momentum balance of
        the growing layer: rho*U*(delta*(1.02) - delta*(1.0))/0.02
        reproduces tau_w(1.01 s) with relative error 1.2e-5, below
        the 1e-3 bound."""
        lhs = RHO * U * (sl.stokes_first_displacement_thickness(NU, 1.02) -
                         sl.stokes_first_displacement_thickness(NU, 1.0)) / 0.02
        rhs = sl.stokes_first_wall_shear(RHO, U, NU, 1.01)
        self.assertLess(abs(lhs - rhs) / rhs, 1e-3)


class StokesSecondProblemTests(unittest.TestCase):
    """Stokes second problem (oscillating plate layer)."""

    def test_penetration_depth_anchor(self):
        """Step 6 of the SKILL.md workflow, the penetration-depth
        traverse: delta = sqrt(2*nu/omega) is 7.64199e-4 m at
        omega = 50 rad/s within 1e-8 m."""
        self.assertAlmostEqual(sl.stokes_penetration_depth(NU, OMEGA),
                               7.64199e-4, delta=1e-8)

    def test_wall_no_slip_cosine(self):
        """Step 7 of the SKILL.md workflow, the oscillating-field
        traverse: the oscillating-plate-layer field obeys no slip,
        u(0, t) = U*cos(omega*t) within 1e-12 relative, and the
        steady-periodic state also holds for negative time."""
        for t in (-0.01, 0.0, 0.01, 0.02, 0.05):
            expect = U * math.cos(OMEGA * t)
            self.assertAlmostEqual(sl.stokes_second_velocity(U, NU, OMEGA,
                                                             0.0, t),
                                   expect, delta=1e-9)

    def test_phase_zero_gives_local_amplitude(self):
        """Step 7 of the SKILL.md workflow, the oscillating-field
        traverse with its phase lag y/delta: where omega*t = y/delta
        the cosine argument vanishes and the velocity equals the local
        amplitude U*exp(-y/delta) within 1e-12 relative."""
        delta = sl.stokes_penetration_depth(NU, OMEGA)
        for frac in (0.0, 0.5, 1.0, 2.0, 3.0):
            y = frac * delta
            u = sl.stokes_second_velocity(U, NU, OMEGA, y, frac / OMEGA)
            expect = U * math.exp(-frac)
            self.assertAlmostEqual(u, expect, delta=1e-9)

    def test_velocity_cycle_at_penetration_depth(self):
        """Step 7 of the SKILL.md workflow, the oscillating-field
        traverse: at y = delta the signal peaks at t = 1/omega
        (11.0364 m/s, one radian after the wall peak) and the cycle
        samples match 5.9630, 9.6853, 11.0364, 9.6853 and 0.7807 m/s
        at t = 0, 0.01, 0.02, 0.03 and 0.05 s within 1e-3 m/s."""
        delta = sl.stokes_penetration_depth(NU, OMEGA)
        samples = (0.0, 0.01, 0.02, 0.03, 0.05)
        anchors = (5.9630, 9.6853, 11.0364, 9.6853, 0.7807)
        for t, anchor in zip(samples, anchors):
            self.assertAlmostEqual(sl.stokes_second_velocity(U, NU, OMEGA,
                                                             delta, t),
                                   anchor, delta=1e-3)
        peak = sl.stokes_second_velocity(U, NU, OMEGA, delta, 1.0 / OMEGA)
        self.assertGreater(peak,
                           sl.stokes_second_velocity(U, NU, OMEGA, delta, 0.0))
        self.assertGreater(peak,
                           sl.stokes_second_velocity(U, NU, OMEGA, delta,
                                                     2.0 / OMEGA))

    def test_amplitude_profile_decay(self):
        """Step 7 of the SKILL.md workflow, the amplitude decay of the
        oscillating field: at y/delta = 0.5, 1, 2 and 3 the local
        amplitudes 18.1959, 11.0364, 4.0601 and 1.4936 m/s match the
        anchors within 1e-3 m/s (exp(-1)*U at the penetration depth)."""
        delta = sl.stokes_penetration_depth(NU, OMEGA)
        for frac, anchor in ((0.5, 18.1959), (1.0, 11.0364),
                             (2.0, 4.0601), (3.0, 1.4936)):
            y = frac * delta
            u = sl.stokes_second_velocity(U, NU, OMEGA, y, frac / OMEGA)
            self.assertAlmostEqual(u, anchor, delta=1e-3)

    def test_shear_amplitude_anchor(self):
        """Step 8 of the SKILL.md workflow, the shear-phase traverse:
        the wall shear amplitude tau_amp = rho*U*sqrt(nu*omega) is
        0.992930 Pa at omega = 50 rad/s within 1e-4 Pa, inside the
        0.9 to 1.1 Pa magnitude bound."""
        amp = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        self.assertAlmostEqual(amp, 0.992930, delta=1e-4)
        self.assertGreater(amp, 0.9)
        self.assertLess(amp, 1.1)

    def test_shear_amplitude_mu_identity(self):
        """Step 8 of the SKILL.md workflow, the shear-phase traverse:
        rho*U*sqrt(nu*omega) equals mu*U*sqrt(omega/nu) with
        mu = rho*nu to float noise, relative difference below
        1e-12."""
        amp = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        mu = RHO * NU
        alt = mu * U * math.sqrt(OMEGA / NU)
        self.assertAlmostEqual(amp, alt, delta=1e-12)

    def test_shear_waveform_phase_lead(self):
        """Step 8 of the SKILL.md workflow, the 45 degree phase lead:
        tau_w(t)/tau_amp = cos(omega*t + pi/4), so at t = 0 the ratio
        is cos(pi/4) = 0.707107 within 1e-6 and the shear waveform
        leads the plate velocity by one-eighth period."""
        amp = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        ratio = sl.stokes_second_wall_shear(RHO, U, NU, OMEGA, 0.0) / amp
        self.assertAlmostEqual(ratio, 0.707107, delta=1e-6)
        self.assertAlmostEqual(ratio, math.cos(math.pi / 4.0), delta=1e-12)

    def test_shear_zero_crossing_at_pi_over_4(self):
        """Step 8 of the SKILL.md workflow, the one-eighth-period zero
        crossing: tau_w vanishes at omega*t = pi/4 (t =
        pi/(4*omega)) with residual below 1e-9 of the amplitude
        (anchor residual 6.08e-17 Pa)."""
        amp = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        t_zero = math.pi / (4.0 * OMEGA)
        residual = abs(sl.stokes_second_wall_shear(RHO, U, NU, OMEGA, t_zero))
        self.assertLess(residual, 1e-9 * amp)

    def test_shear_negative_peak(self):
        """Step 8 of the SKILL.md workflow, the shear-phase traverse:
        tau_w = -tau_amp at omega*t = 3*pi/4 within 1e-12 relative,
        and the sample at t = 0.062832 s (180 deg) is -0.702108 Pa
        within 1e-3 Pa."""
        amp = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        t135 = 3.0 * math.pi / (4.0 * OMEGA)
        self.assertAlmostEqual(sl.stokes_second_wall_shear(RHO, U, NU, OMEGA,
                                                           t135),
                               -amp, delta=1e-12)
        self.assertAlmostEqual(sl.stokes_second_wall_shear(RHO, U, NU, OMEGA,
                                                           0.062832),
                               -0.702108, delta=1e-3)

    def test_zero_crossing_eighth_period_after_peak(self):
        """Step 8 of the SKILL.md workflow, the shear-phase traverse:
        the zero crossing sits exactly T/8 = pi/(4*omega) =
        0.015708 s after the wall velocity peak at t = 0."""
        self.assertAlmostEqual(math.pi / (4.0 * OMEGA), 0.015708,
                               delta=1e-6)
        t_zero = math.pi / (4.0 * OMEGA)
        self.assertAlmostEqual(t_zero, (2.0 * math.pi / OMEGA) / 8.0,
                               delta=1e-12)


class ValidationTests(unittest.TestCase):
    """Input rejection and determinism (workflow step 9)."""

    def test_valueerror_nu_nonpositive(self):
        """Step 9 of the SKILL.md workflow, the input-rejection
        traverse: nu at 0 and -1e-5 raises ValueError on every nu
        argument in the module."""
        for nu_bad in (0.0, -1e-5):
            with self.assertRaises(ValueError):
                sl.stokes_first_velocity(U, nu_bad, 0.0, 0.001)
            with self.assertRaises(ValueError):
                sl.rayleigh_layer_thickness(nu_bad, 0.001)
            with self.assertRaises(ValueError):
                sl.stokes_first_wall_shear(RHO, U, nu_bad, 0.001)
            with self.assertRaises(ValueError):
                sl.stokes_first_displacement_thickness(nu_bad, 0.001)
            with self.assertRaises(ValueError):
                sl.stokes_second_velocity(U, nu_bad, OMEGA, 0.0, 0.0)
            with self.assertRaises(ValueError):
                sl.stokes_penetration_depth(nu_bad, OMEGA)
            with self.assertRaises(ValueError):
                sl.stokes_second_shear_amplitude(RHO, U, nu_bad, OMEGA)
            with self.assertRaises(ValueError):
                sl.stokes_second_wall_shear(RHO, U, nu_bad, OMEGA, 0.0)

    def test_valueerror_time_nonpositive(self):
        """Step 9 of the SKILL.md workflow, the input-rejection
        traverse: t at 0 and -0.1 raises ValueError on every
        first-problem time argument (the impulsive start is singular
        at t = 0)."""
        for t_bad in (0.0, -0.1):
            with self.assertRaises(ValueError):
                sl.stokes_first_velocity(U, NU, 0.0, t_bad)
            with self.assertRaises(ValueError):
                sl.rayleigh_layer_thickness(NU, t_bad)
            with self.assertRaises(ValueError):
                sl.stokes_first_wall_shear(RHO, U, NU, t_bad)
            with self.assertRaises(ValueError):
                sl.stokes_first_displacement_thickness(NU, t_bad)

    def test_valueerror_y_negative(self):
        """Step 9 of the SKILL.md workflow, the input-rejection
        traverse: y at -1e-6 and -0.001 raises ValueError on both
        velocity functions (the fluid occupies y >= 0 only)."""
        for y_bad in (-1e-6, -0.001):
            with self.assertRaises(ValueError):
                sl.stokes_first_velocity(U, NU, y_bad, 0.001)
            with self.assertRaises(ValueError):
                sl.stokes_second_velocity(U, NU, OMEGA, y_bad, 0.0)

    def test_valueerror_rho_nonpositive(self):
        """Step 9 of the SKILL.md workflow, the input-rejection
        traverse: rho at 0 raises ValueError on both shear
        functions."""
        for rho_bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                sl.stokes_first_wall_shear(rho_bad, U, NU, 0.001)
            with self.assertRaises(ValueError):
                sl.stokes_second_shear_amplitude(rho_bad, U, NU, OMEGA)
            with self.assertRaises(ValueError):
                sl.stokes_second_wall_shear(rho_bad, U, NU, OMEGA, 0.0)

    def test_valueerror_omega_nonpositive(self):
        """Step 9 of the SKILL.md workflow, the input-rejection
        traverse: omega at 0 and -50 raises ValueError on every
        second-problem omega argument."""
        for omega_bad in (0.0, -50.0):
            with self.assertRaises(ValueError):
                sl.stokes_second_velocity(U, NU, omega_bad, 0.0, 0.0)
            with self.assertRaises(ValueError):
                sl.stokes_penetration_depth(NU, omega_bad)
            with self.assertRaises(ValueError):
                sl.stokes_second_shear_amplitude(RHO, U, NU, omega_bad)
            with self.assertRaises(ValueError):
                sl.stokes_second_wall_shear(RHO, U, NU, omega_bad, 0.0)

    def test_determinism_repeat_calls(self):
        """Step 9 of the SKILL.md workflow, the determinism traverse:
        repeated calls with identical arguments return bit-identical
        results, and the worked-example numbers reproduce exactly on
        re-evaluation (closed form, no iteration, math only)."""
        first = sl.stokes_first_wall_shear(RHO, U, NU, 0.001)
        second = sl.stokes_first_wall_shear(RHO, U, NU, 0.001)
        self.assertEqual(first, second)
        amp1 = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        amp2 = sl.stokes_second_shear_amplitude(RHO, U, NU, OMEGA)
        self.assertEqual(amp1, amp2)
        # Closed-form identity across problem types: the first-problem
        # wall shear and the second-problem penetration depth both
        # derive from the same diffusion time scale nu.
        self.assertAlmostEqual(sl.stokes_penetration_depth(NU, OMEGA),
                               math.sqrt(2.0 * NU / OMEGA), delta=1e-18)

    def test_module_imports_math_only(self):
        """Step 9 of the SKILL.md workflow, the determinism traverse:
        the logic module depends on the standard library math module
        only (no numpy, scipy, network or randomness)."""
        mod = sys.modules.get("unsteady_laminar_stokes_layers_logic")
        self.assertIsNotNone(mod)
        source_path = getattr(mod, "__file__", None)
        self.assertIsInstance(source_path, str)
        with open(os.path.abspath(source_path)) as fh:
            source = fh.read()
        self.assertIn("import math", source)
        for banned in ("numpy", "scipy", "random", "import urllib",
                       "import requests", "import socket"):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
