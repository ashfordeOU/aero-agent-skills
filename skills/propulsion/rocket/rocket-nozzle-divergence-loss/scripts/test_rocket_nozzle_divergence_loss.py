"""Contract test for rocket-nozzle-divergence-loss (propulsion/rocket).

Exercises the delivered-thrust loss bookkeeping of an attached-flow
rocket nozzle: the conical divergence factor, the bell contour
efficiency and its ratio to the cone, the turbulent boundary-layer
displacement thickness, the momentum loss fraction, the displaced-core
exit area ratio, and the delivered thrust and delivered Isp chain. The
ideal attached-flow state is a module input (nozzle-design domain) and
is never re-derived inside the module. Every SKILL.md workflow step is
covered: step 1 collects the geometry and the ideal state, step 2
chooses the shape factor, step 3 compares the bell contour to the cone,
step 4 grows the boundary layer, step 5 converts to the loss fraction
and the effective area ratio, step 6 assembles the delivered thrust and
Isp, step 7 reads off the delivered fraction of the ideal, and step 8
runs this contract test. All worked-example targets are the real module
outputs for the spec's rounded ideal-state inputs; the prep-anchor
figures are reproduced exactly for every quantity that the input
rounding does not affect (Isp, fractions, thicknesses, area ratios) and
within the input-rounding band for absolute thrust.
"""

import math
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rocket_nozzle_divergence_loss_logic as mdl

# Worked-example scenario: LOX/RP-1 upper stage, pc = 7.0 MPa, area
# ratio 70, throat radius 0.150 m (prep-anchor geometry, rounded inputs).
MDOT = 276.24        # kg/s
VE = 3260.673        # m/s
PE = 6036.738        # Pa, exit static pressure
PA_VAC = 0.0         # Pa, vacuum ambient
RHO_E = 0.017122     # kg/m^3, exit density
MU = 8.0e-5          # Pa s, hot-product viscosity at the exit
R_T = 0.15           # m, throat radius
AREA_RATIO = 70.0    # Ae / At
AT = math.pi * R_T * R_T
AE = AT * AREA_RATIO
R_EXIT = R_T * math.sqrt(AREA_RATIO)
F_IDEAL = MDOT * VE + (PE - PA_VAC) * AE  # ideal vacuum thrust, N


class RocketNozzleDivergenceLossTest(unittest.TestCase):

    # --- module constants and profile shape (workflow step 4 basis) ----

    def test_module_constants_and_profile_shape(self):
        # Step 4 of the SKILL.md workflow, the turbulent boundary-layer
        # growth, rests on the module constants: the flat-plate growth
        # coefficient and the 1/7-power profile shape ratios.
        self.assertAlmostEqual(mdl.G0, 9.80665, delta=1e-12)
        self.assertAlmostEqual(mdl.ETA_BELL_DEFAULT, 0.98, delta=1e-12)
        self.assertAlmostEqual(mdl.ALPHA_REF_DEG, 15.0, delta=1e-12)
        self.assertAlmostEqual(mdl.TURB_COEFF, 0.37, delta=1e-12)
        self.assertAlmostEqual(mdl.DELTA_STAR_OVER_DELTA, 0.125, delta=1e-12)
        self.assertAlmostEqual(mdl.THETA_OVER_DELTA, 7.0 / 72.0, delta=1e-12)
        # Profile identity: theta/delta* = (7/72)/(1/8) = 7/9 = 0.777778.
        ratio = mdl.THETA_OVER_DELTA / mdl.DELTA_STAR_OVER_DELTA
        self.assertAlmostEqual(ratio, 7.0 / 9.0, delta=1e-12)
        self.assertAlmostEqual(ratio, 0.777778, delta=1e-5)

    # --- conical divergence factor (workflow step 2, conical branch) ----

    def test_conical_divergence_factor_reference_values(self):
        # Step 2 of the SKILL.md workflow, the conical shape-factor
        # choice, pins lambda = (1 + cos(alpha))/2 at the reference
        # half-angles: 0.982963 at 15 deg and exactly 0.75 at 60 deg.
        lam15 = mdl.conical_divergence_factor(15.0)
        self.assertAlmostEqual(lam15, 0.982963, delta=1e-5)
        lam60 = mdl.conical_divergence_factor(60.0)
        self.assertAlmostEqual(lam60, 0.75, delta=1e-9)
        # cos 60 = 1/2 makes lambda(60) = 3/4 exactly by construction.
        self.assertEqual(lam60, 0.75)

    def test_conical_divergence_factor_monotonic_decreasing(self):
        # Step 2 of the SKILL.md workflow: the axial projection falls
        # monotonically as the half-angle grows from 8 to 30 deg, so
        # the steep cone always carries the larger divergence loss.
        values = [mdl.conical_divergence_factor(a)
                  for a in (8.0, 10.0, 12.0, 15.0, 20.0, 25.0, 28.0, 30.0)]
        for higher, lower in zip(values, values[1:]):
            self.assertGreater(higher, lower)

    def test_conical_divergence_factor_rejects_out_of_range_alpha(self):
        # Workflow step 2 input validation: the half-angle must lie in
        # (0, 90) deg; a zero, right-angle, negative or past-90 cone is
        # non-physical and raises ValueError.
        for bad in (0.0, 90.0, -5.0, 95.0, 180.0):
            with self.assertRaises(ValueError):
                mdl.conical_divergence_factor(bad)

    # --- bell contour efficiency (workflow step 2, bell branch) ---------

    def test_bell_contour_efficiency_default_and_passthrough(self):
        # Step 2 of the SKILL.md workflow, the bell shape-factor
        # choice: the default contour efficiency is the documented 0.98
        # of the equivalent 80-percent-length Rao-class bell, and an
        # explicit parameter is returned validated.
        self.assertEqual(mdl.bell_contour_efficiency(), 0.98)
        self.assertEqual(mdl.bell_contour_efficiency(0.95), 0.95)
        self.assertEqual(mdl.bell_contour_efficiency(1.0), 1.0)

    def test_bell_contour_efficiency_rejects_out_of_range(self):
        # Workflow step 2 validation: the contour efficiency parameter
        # must lie in (0, 1]; values at or above 1 and negative values
        # are rejected as non-physical.
        for bad in (0.0, 1.1, 2.0, -0.5):
            with self.assertRaises(ValueError):
                mdl.bell_contour_efficiency(bad)

    # --- bell to conical comparison (workflow step 3) -------------------

    def test_bell_relative_to_conical_default_ratio(self):
        # Step 3 of the SKILL.md workflow, the bell-to-conical contour
        # comparison: at the defaults the 0.98 contour of the
        # 80-percent-length bell is 0.996986 of the 15-degree cone.
        ratio = mdl.bell_relative_to_conical()
        self.assertAlmostEqual(ratio, 0.996986, delta=1e-5)
        self.assertAlmostEqual(ratio, 0.98 / 0.982963, delta=1e-5)

    def test_bell_relative_to_conical_unit_ratio_identity(self):
        # Step 3 of the SKILL.md workflow: at eta_bell equal to
        # lambda(15 deg) the contour-only ratio is exactly 1, the
        # degenerate identity that closes the bell equivalence.
        lam15 = mdl.conical_divergence_factor(15.0)
        ratio = mdl.bell_relative_to_conical(lam15, 15.0)
        self.assertAlmostEqual(ratio, 1.0, delta=1e-9)

    def test_bell_relative_to_conical_rejects_invalid_arguments(self):
        # Workflow step 3 validation: the ratio inherits both callers'
        # checks, rejecting an out-of-range contour efficiency and an
        # out-of-range comparison half-angle alike.
        with self.assertRaises(ValueError):
            mdl.bell_relative_to_conical(0.0)
        with self.assertRaises(ValueError):
            mdl.bell_relative_to_conical(1.1)
        with self.assertRaises(ValueError):
            mdl.bell_relative_to_conical(0.98, 90.0)

    # --- turbulent boundary-layer growth (workflow step 4) --------------

    def test_turbulent_displacement_thickness_worked_conical_value(self):
        # Step 4 of the SKILL.md workflow, the boundary-layer growth
        # over the divergent length: the spec check at L = 4.124 m with
        # the worked-example edge conditions returns delta* = 0.00974 m
        # within 1e-4 (Re_L of order 2.9e6).
        ds = mdl.turbulent_displacement_thickness(4.124, VE, RHO_E, MU)
        self.assertAlmostEqual(ds, 0.00974, delta=1e-4)
        # The 1/7-power profile ratio delta*/delta = 1/8 = 0.125.
        delta = ds / mdl.DELTA_STAR_OVER_DELTA
        self.assertAlmostEqual(ds / delta, 0.125, delta=1e-12)

    def test_turbulent_displacement_thickness_growth_scaling(self):
        # Step 4 of the SKILL.md workflow: over a longer divergent wall
        # the layer is thicker, with the flat-plate exponent making
        # delta* scale as L**0.8 at fixed edge conditions, and a lower
        # viscosity (higher Re_L) thins it as Re_L**(-0.2).
        ds_long = mdl.turbulent_displacement_thickness(6.0, VE, RHO_E, MU)
        ds_short = mdl.turbulent_displacement_thickness(3.0, VE, RHO_E, MU)
        self.assertGreater(ds_long, ds_short)
        self.assertAlmostEqual(ds_long / ds_short, 2.0 ** 0.8, delta=1e-9)
        ds_base = mdl.turbulent_displacement_thickness(4.124, VE, RHO_E, MU)
        ds_mu2 = mdl.turbulent_displacement_thickness(4.124, VE, RHO_E, 2.0 * MU)
        # Doubling the viscosity halves Re_L and thickens the layer by
        # the factor 2**0.2 (delta* grows as Re_L**(-0.2)).
        self.assertGreater(ds_mu2, ds_base)
        self.assertAlmostEqual(ds_mu2 / ds_base, 2.0 ** 0.2, delta=1e-9)

    def test_turbulent_displacement_thickness_rejects_nonpositive_inputs(self):
        # Workflow step 4 validation: every argument (divergent length,
        # exit velocity, exit density, viscosity) must be positive for
        # the Reynolds-number growth law to be physical.
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                mdl.turbulent_displacement_thickness(bad, VE, RHO_E, MU)
            with self.assertRaises(ValueError):
                mdl.turbulent_displacement_thickness(4.124, bad, RHO_E, MU)
            with self.assertRaises(ValueError):
                mdl.turbulent_displacement_thickness(4.124, VE, bad, MU)
            with self.assertRaises(ValueError):
                mdl.turbulent_displacement_thickness(4.124, VE, RHO_E, bad)

    # --- loss fraction and displaced-core area (workflow step 5) --------

    def test_boundary_layer_loss_fraction_worked_value(self):
        # Step 5 of the SKILL.md workflow, the 1-D mass-flux correction:
        # the momentum loss fraction is xi = (14/9)*delta*/r_exit, which
        # at the worked-example values (0.00974 m over 1.2550 m) gives
        # xi_bl = 0.01207, about 1.21 percent of the momentum term.
        xi = mdl.boundary_layer_loss_fraction(0.00974, 1.2550)
        self.assertAlmostEqual(xi, 0.01207, delta=1e-4)
        self.assertAlmostEqual(xi, (14.0 / 9.0) * 0.00974 / 1.2550, delta=1e-9)

    def test_boundary_layer_loss_fraction_profile_identity_theta(self):
        # Step 5 of the SKILL.md workflow: with theta = (7/9)*delta*
        # from the 1/7-power profile, the annulus momentum removal
        # 2*theta/r_exit equals the closed-form (14/9)*delta*/r_exit.
        ds = 0.01
        r = 0.5
        theta = (7.0 / 9.0) * ds
        xi = mdl.boundary_layer_loss_fraction(ds, r)
        self.assertAlmostEqual(xi, 2.0 * theta / r, delta=1e-12)

    def test_boundary_layer_loss_fraction_thin_layer_limit(self):
        # Step 5 of the SKILL.md workflow: as the layer thins the
        # fractional loss tends to zero, the thin-layer boundary of the
        # correction.
        r = 1.0
        xi = mdl.boundary_layer_loss_fraction(r * 1e-9, r)
        self.assertGreater(xi, 0.0)
        self.assertLess(xi, 1e-8)

    def test_boundary_layer_loss_fraction_rejects_invalid_thicknesses(self):
        # Workflow step 5 validation: the displacement thickness must be
        # positive and strictly below the exit radius for the thin-layer
        # expansion to hold.
        with self.assertRaises(ValueError):
            mdl.boundary_layer_loss_fraction(0.0, 1.0)
        with self.assertRaises(ValueError):
            mdl.boundary_layer_loss_fraction(1.0, 1.0)
        with self.assertRaises(ValueError):
            mdl.boundary_layer_loss_fraction(2.0, 1.0)
        with self.assertRaises(ValueError):
            mdl.boundary_layer_loss_fraction(0.01, 0.0)
        with self.assertRaises(ValueError):
            mdl.boundary_layer_loss_fraction(0.01, -1.0)

    def test_effective_exit_area_ratio_worked_displaced_core(self):
        # Step 5 of the SKILL.md workflow, the displaced-core area: the
        # inviscid core shrinks to pi*(r_exit - delta*)**2, so the
        # effective area ratio 70*(1 - 0.00974/1.2550)**2 = 68.9176.
        eps_eff = mdl.effective_exit_area_ratio(70.0, 0.00974, 1.2550)
        self.assertAlmostEqual(eps_eff, 68.9176, delta=0.01)
        self.assertLess(eps_eff, 70.0)

    def test_effective_exit_area_ratio_thin_and_thick_limits(self):
        # Step 5 of the SKILL.md workflow: a vanishing layer leaves the
        # geometric expansion ratio (eps_eff tends to eps), while a
        # layer that nearly fills the exit collapses the core area.
        eps = 70.0
        r = 1.2550
        eps_thin = mdl.effective_exit_area_ratio(eps, r * 1e-9, r)
        self.assertAlmostEqual(eps_thin, eps, delta=1e-6)
        eps_thick = mdl.effective_exit_area_ratio(eps, 0.999 * r, r)
        self.assertAlmostEqual(eps_thick, eps * (0.001 ** 2), delta=1e-6)

    def test_effective_exit_area_ratio_rejects_invalid_inputs(self):
        # Workflow step 5 validation: the expansion ratio must exceed 1
        # (a real nozzle), and the layer checks mirror the loss
        # fraction: positive thickness strictly below the exit radius.
        with self.assertRaises(ValueError):
            mdl.effective_exit_area_ratio(1.0, 0.001, 1.0)
        with self.assertRaises(ValueError):
            mdl.effective_exit_area_ratio(0.5, 0.001, 1.0)
        with self.assertRaises(ValueError):
            mdl.effective_exit_area_ratio(70.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            mdl.effective_exit_area_ratio(70.0, 1.0, 1.0)

    # --- no-loss identities (workflow step 6, degenerate) ---------------

    def test_delivered_thrust_no_loss_identity(self):
        # Step 6 of the SKILL.md workflow, the delivered thrust
        # assembly: at shape_factor 1 and zero boundary-layer loss the
        # chain must reproduce the ideal thrust mdot*ve + (pe - pa)*Ae
        # of the same state with a residual below 1e-6 N (the anchor
        # residual is 0.000e+00 N).
        f_del = mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE, 1.0, 0.0)
        residual = abs(f_del - (MDOT * VE + (PE - PA_VAC) * AE))
        self.assertLess(residual, 1e-6)
        self.assertAlmostEqual(f_del, F_IDEAL, delta=1e-6)

    def test_delivered_isp_matched_expansion_identity(self):
        # Step 6 of the SKILL.md workflow, the delivered Isp assembly:
        # at pe = pa with shape 1 and no loss the delivered Isp is
        # exactly ve/g0 = 332.496090 s, the matched-expansion identity.
        isp = mdl.delivered_isp(MDOT, VE, PE, PE, AE, 1.0, 0.0)
        self.assertAlmostEqual(isp, VE / mdl.G0, delta=1e-9)
        self.assertAlmostEqual(isp, 332.496090, delta=1e-3)

    # --- worked example chains (workflow steps 1-7) ---------------------

    def _conical_delivered(self, alpha_deg):
        """Conical delivered chain: shape factor, wall growth, loss
        fraction, delivered thrust and delivered fraction of ideal."""
        lam = mdl.conical_divergence_factor(alpha_deg)
        length = (R_EXIT - R_T) / math.tan(math.radians(alpha_deg))
        ds = mdl.turbulent_displacement_thickness(length, VE, RHO_E, MU)
        xi = mdl.boundary_layer_loss_fraction(ds, R_EXIT)
        f_del = mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE, lam, xi)
        return lam, length, ds, xi, f_del, f_del / F_IDEAL

    def test_worked_example_conical_15deg_delivered_chain(self):
        # Workflow steps 2, 4, 5 and 6 on the worked example: the
        # 15-degree conical nozzle over its 4.124 m divergent length
        # delivers 904562.3 N, Isp_del = 333.911 s and a fraction
        # 0.97202 of the ideal, inside the [0.93, 0.98] plausibility
        # band. The prep anchor reports 904558.9 N from the unrounded
        # internal ideal state; the module fed the spec's rounded
        # inputs sits 3.4 N higher, inside the input-rounding band.
        lam, length, ds, xi, f_del, frac = self._conical_delivered(15.0)
        self.assertAlmostEqual(lam, 0.982963, delta=1e-5)
        self.assertAlmostEqual(length, 4.124, delta=0.01)
        self.assertAlmostEqual(ds, 0.00974, delta=1e-4)
        self.assertAlmostEqual(xi, 0.01207, delta=1e-4)
        self.assertAlmostEqual(f_del, 904562.3, delta=1.0)
        self.assertAlmostEqual(f_del, 904558.9, delta=5.0)
        isp = mdl.delivered_isp(MDOT, VE, PE, PA_VAC, AE, lam, xi)
        self.assertAlmostEqual(isp, 333.911, delta=0.05)
        self.assertAlmostEqual(frac, 0.97202, delta=1e-4)
        self.assertTrue(0.93 <= frac <= 0.98)

    def test_worked_example_bell_80pct_delivered_chain(self):
        # Workflow steps 2 (bell branch), 4, 5 and 6: the equivalent
        # Rao-class bell at 80 percent of the conical length (3.299 m)
        # with the 0.98 contour efficiency delivers 903668.2 N,
        # Isp_del = 333.581 s and a fraction 0.97106 of the ideal. The
        # shorter wall grows a thinner layer (delta* = 0.00815 m), so
        # its loss fraction is 0.01010 against the cone's 0.01207.
        lam, length, ds, xi, f_del, frac = self._conical_delivered(15.0)
        l_bell = 0.8 * length
        self.assertAlmostEqual(l_bell, 3.299, delta=0.01)
        ds_b = mdl.turbulent_displacement_thickness(l_bell, VE, RHO_E, MU)
        self.assertAlmostEqual(ds_b, 0.00815, delta=1e-4)
        xi_b = mdl.boundary_layer_loss_fraction(ds_b, R_EXIT)
        self.assertAlmostEqual(xi_b, 0.01010, delta=1e-4)
        self.assertLess(xi_b, xi)
        eps_eff_b = mdl.effective_exit_area_ratio(AREA_RATIO, ds_b, R_EXIT)
        self.assertAlmostEqual(eps_eff_b, 69.0940, delta=0.01)
        f_b = mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE,
                                   mdl.bell_contour_efficiency(), xi_b)
        self.assertAlmostEqual(f_b, 903668.2, delta=1.0)
        self.assertAlmostEqual(f_b, 903664.7, delta=5.0)
        isp_b = mdl.delivered_isp(MDOT, VE, PE, PA_VAC, AE,
                                  mdl.bell_contour_efficiency(), xi_b)
        self.assertAlmostEqual(isp_b, 333.581, delta=0.05)
        frac_b = f_b / F_IDEAL
        self.assertAlmostEqual(frac_b, 0.97106, delta=1e-4)
        self.assertTrue(0.93 <= frac_b <= 0.98)

    def test_bell_conical_delivered_ratio_verdict(self):
        # Step 7 of the SKILL.md workflow, the delivered-fraction
        # read-off: the 80-percent-length bell delivers 0.99901 of the
        # full-length 15-degree conical (within 0.10 percent), so the
        # bell's benefit is its length and mass saving, not an Isp gain.
        _, _, _, _, f15, frac15 = self._conical_delivered(15.0)
        length = (R_EXIT - R_T) / math.tan(math.radians(15.0))
        ds_b = mdl.turbulent_displacement_thickness(0.8 * length, VE, RHO_E, MU)
        xi_b = mdl.boundary_layer_loss_fraction(ds_b, R_EXIT)
        f_b = mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE,
                                   mdl.bell_contour_efficiency(), xi_b)
        frac_b = f_b / F_IDEAL
        self.assertAlmostEqual(frac_b / frac15, 0.99901, delta=1e-4)
        self.assertAlmostEqual(f_b / f15, 0.99901, delta=1e-4)
        # The bell contour alone is 0.996986 of the cone; the shorter
        # wall's smaller loss closes most of the remaining gap.
        self.assertAlmostEqual(mdl.bell_relative_to_conical(), 0.996986,
                               delta=1e-5)

    def test_half_angle_sensitivity_peak_near_10deg(self):
        # Step 7 of the SKILL.md workflow, the read-off sweep at fixed
        # area ratio: the delivered fraction peaks near 10 deg where
        # the shallow cone's longer wall starts to cost more boundary
        # layer than the divergence saves (0.97644 at 10 deg above
        # 0.97580 at 8 deg and 0.97551 at 12 deg).
        _, _, _, _, _, f8 = self._conical_delivered(8.0)
        _, _, _, _, _, f10 = self._conical_delivered(10.0)
        _, _, _, _, _, f12 = self._conical_delivered(12.0)
        self.assertAlmostEqual(f8, 0.97580, delta=1e-4)
        self.assertAlmostEqual(f10, 0.97644, delta=1e-4)
        self.assertAlmostEqual(f12, 0.97551, delta=1e-4)
        self.assertGreater(f10, f8)
        self.assertGreater(f10, f12)

    def test_half_angle_sensitivity_design_band_and_steep_edge(self):
        # Step 7 of the SKILL.md workflow, the design band: the typical
        # 12-25 deg band spans 0.94751 to 0.97551 inside [0.93, 0.98],
        # and only the steep 30 deg cone (0.92926) dips below the band.
        _, _, _, _, _, f25 = self._conical_delivered(25.0)
        _, _, _, _, _, f30 = self._conical_delivered(30.0)
        _, _, _, _, _, f12 = self._conical_delivered(12.0)
        self.assertAlmostEqual(f25, 0.94751, delta=1e-4)
        self.assertAlmostEqual(f30, 0.92926, delta=1e-4)
        self.assertTrue(0.93 <= f25 <= 0.98)
        self.assertTrue(0.93 <= f12 <= 0.98)
        self.assertLess(f30, 0.93)

    # --- input validation (workflow steps 2, 5 and 6) -------------------

    def test_delivered_thrust_rejects_nonphysical_inputs(self):
        # Workflow step 6 validation: the mass flow, exit velocity and
        # exit area must be positive, the shape factor must lie in
        # (0, 1] and the boundary-layer loss fraction in [0, 1).
        for bad in (0.0, -2.0):
            with self.assertRaises(ValueError):
                mdl.delivered_thrust(bad, VE, PE, PA_VAC, AE, 1.0, 0.0)
        with self.assertRaises(ValueError):
            mdl.delivered_thrust(MDOT, -1.0, PE, PA_VAC, AE, 1.0, 0.0)
        with self.assertRaises(ValueError):
            mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, 0.0, 1.0, 0.0)
        for bad_shape in (0.0, 1.5):
            with self.assertRaises(ValueError):
                mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE, bad_shape, 0.0)
        for bad_xi in (-0.1, 1.0, 2.0):
            with self.assertRaises(ValueError):
                mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE, 1.0, bad_xi)

    def test_delivered_isp_rejects_nonphysical_inputs(self):
        # Workflow step 6 validation, the Isp assembly: the standard
        # gravity must be positive, and the thrust-input checks apply
        # unchanged through the chain.
        with self.assertRaises(ValueError):
            mdl.delivered_isp(MDOT, VE, PE, PA_VAC, AE, 1.0, 0.0, g0=0.0)
        with self.assertRaises(ValueError):
            mdl.delivered_isp(MDOT, VE, PE, PA_VAC, AE, 1.0, 0.0, g0=-9.8)
        with self.assertRaises(ValueError):
            mdl.delivered_isp(0.0, VE, PE, PA_VAC, AE, 1.0, 0.0)

    # --- determinism and purity -----------------------------------------

    def test_repeat_calls_deterministic(self):
        # Workflow steps 4 to 6: repeated evaluation of the loss chain
        # returns bit-identical results (no RNG, no state), so the
        # bookkeeping is deterministic and reproducible offline.
        args = (4.124, VE, RHO_E, MU)
        self.assertEqual(mdl.turbulent_displacement_thickness(*args),
                         mdl.turbulent_displacement_thickness(*args))
        self.assertEqual(mdl.conical_divergence_factor(15.0),
                         mdl.conical_divergence_factor(15.0))
        f1 = mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE, 0.98, 0.01)
        f2 = mdl.delivered_thrust(MDOT, VE, PE, PA_VAC, AE, 0.98, 0.01)
        self.assertEqual(f1, f2)

    def test_logic_module_imports_math_only(self):
        # Workflow step 8: the module stays pure stdlib with no imports
        # beyond math, keeping the offline contract deterministic.
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "rocket_nozzle_divergence_loss_logic.py")
        with open(logic_path, "r") as handle:
            source = handle.read()
        for line in source.splitlines():
            stripped = line.strip()
            match = re.match(r"^(?:import|from)\s+([A-Za-z0-9_.]+)", stripped)
            if match:
                self.assertEqual(match.group(1), "math",
                                 "unexpected import: %s" % stripped)


if __name__ == "__main__":
    unittest.main()
