#!/usr/bin/env python3
"""Gate 3 contract test: stagnation-flow-boundary-layer.

Exercises scripts/stagnation_flow_boundary_layer_logic.py (stdlib
unittest, offline, deterministic). Contract: docs/harness-contract.md
gate 3 and the wave-41 leaf spec naca-tr-824 reference-only summary of
the classical Hiemenz (2-D) and Homann (axisymmetric) exact-similarity
results. The suite covers every numbered step of the SKILL.md Workflow:
step 1 operating-condition and geometry setup, step 2 the
stagnation-velocity-gradient computation from the 2-D and axisymmetric
regime constants, step 3 the laminar-boundary-layer-thickness estimate
2.4 sqrt(nu / a), step 4 the stagnation-wall-shear computation with the
FPP_2D and FPP_AXISYM similarity wall-shear constants, step 5 the
skin-friction-coefficient conversion from the freestream dynamic
pressure, step 6 the swept-leading-edge crossflow-plane reduction with
the normal velocity component, and step 7 the flow-type treatment note
and contract-test closure. Worked-example anchors (standard air
rho = 1.225 kg/m3, u_inf = 30 m/s, nu = 1.5e-5 m2/s, radius 0.15 m and
0.02 m) come from the leaf spec, which was prep-verified with stdlib
math; assert targets are the real module outputs inside spec tolerances.
ValueError rejection of every non-physical input and the closed-form and
ratio identities from the spec validation list are covered.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stagnation_flow_boundary_layer_logic as sf  # noqa: E402

RHO = 1.225      # standard air density, kg/m3
U_INF = 30.0     # freestream speed, m/s
NU = 1.5e-5      # kinematic viscosity, m2/s
R_CYL = 0.15     # cylinder / 2-D leading-edge radius, m


class StagnationVelocityGradientTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the stagnation-velocity-gradient
    computation a = 2 u_inf / R (cylinder) or 1.5 u_inf / R (sphere)."""

    def test_cylinder_gradient_worked_example(self):
        """2-D Hiemenz regime on the circular cylinder: a = 400.0 1/s."""
        self.assertAlmostEqual(
            sf.stagnation_velocity_gradient("cylinder", U_INF, R_CYL),
            400.0, delta=1e-9)

    def test_sphere_gradient_worked_example(self):
        """Axisymmetric Homann regime on the sphere: a = 300.0 1/s."""
        self.assertAlmostEqual(
            sf.stagnation_velocity_gradient("sphere", U_INF, R_CYL),
            300.0, delta=1e-9)

    def test_synonyms_accepted_case_insensitive(self):
        """Flow-type synonyms cylinder/2d/two-dimensional and
        sphere/axisymmetric/axi are accepted case-insensitively."""
        for label in ("cylinder", "2d", "two-dimensional",
                      "Cylinder", "TWO-DIMENSIONAL", "2D"):
            self.assertAlmostEqual(
                sf.stagnation_velocity_gradient(label, U_INF, R_CYL),
                400.0, delta=1e-9)
        for label in ("sphere", "axisymmetric", "axi",
                      "Sphere", "AXISYMMETRIC", "AXI"):
            self.assertAlmostEqual(
                sf.stagnation_velocity_gradient(label, U_INF, R_CYL),
                300.0, delta=1e-9)

    def test_gradient_scales_inversely_with_radius(self):
        """Halving the radius doubles the gradient at fixed speed."""
        a_half = sf.stagnation_velocity_gradient("cylinder", U_INF, 0.075)
        self.assertAlmostEqual(a_half, 800.0, delta=1e-9)
        self.assertAlmostEqual(
            a_half, 2.0 * sf.stagnation_velocity_gradient(
                "cylinder", U_INF, R_CYL), delta=1e-9)

    def test_gradient_valueerror_non_physical_inputs(self):
        """Non-physical speed, radius and flow type raise ValueError."""
        for u in (0.0, -30.0):
            with self.assertRaises(ValueError):
                sf.stagnation_velocity_gradient("cylinder", u, R_CYL)
        for r in (0.0, -0.15):
            with self.assertRaises(ValueError):
                sf.stagnation_velocity_gradient("sphere", U_INF, r)
        with self.assertRaises(ValueError):
            sf.stagnation_velocity_gradient("cone", U_INF, R_CYL)
        with self.assertRaises(ValueError):
            sf.stagnation_velocity_gradient(123, U_INF, R_CYL)


class BoundaryLayerThicknessTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the laminar-boundary-layer-
    thickness estimate delta = 2.4 sqrt(nu / a), constant along the
    attachment region."""

    def test_cylinder_delta_worked_example(self):
        """Cylinder layer at a = 400: delta = 4.647580e-4 m (0.4648 mm)."""
        self.assertAlmostEqual(
            sf.boundary_layer_thickness(NU, 400.0), 4.647580e-4,
            delta=1e-9)

    def test_sphere_delta_worked_example(self):
        """Sphere layer at a = 300: delta = 5.366563e-4 m (0.5367 mm)."""
        self.assertAlmostEqual(
            sf.boundary_layer_thickness(NU, 300.0), 5.366563e-4,
            delta=1e-9)

    def test_delta_ratio_identity_sqrt_two_over_one_point_five(self):
        """Delta ratio identity: delta_sph / delta_cyl = sqrt(2 / 1.5)."""
        d_cyl = sf.boundary_layer_thickness(NU, 400.0)
        d_sph = sf.boundary_layer_thickness(NU, 300.0)
        self.assertAlmostEqual(
            d_sph / d_cyl, math.sqrt(2.0 / 1.5), delta=1e-9)
        self.assertAlmostEqual(d_sph / d_cyl, 1.1547005, delta=1e-7)

    def test_delta_monotone_decreasing_in_gradient(self):
        """The thickness falls as the gradient rises: stronger
        attachment flow gives a thinner layer."""
        d_low = sf.boundary_layer_thickness(NU, 100.0)
        d_mid = sf.boundary_layer_thickness(NU, 400.0)
        d_high = sf.boundary_layer_thickness(NU, 1600.0)
        self.assertGreater(d_low, d_mid)
        self.assertGreater(d_mid, d_high)
        # sqrt(1600 / 100) = 4, so the ratio of the thicknesses is 4.
        self.assertAlmostEqual(d_low, 4.0 * d_high, delta=1e-9)

    def test_delta_scales_with_sqrt_nu(self):
        """Quadrupling nu at fixed gradient doubles the thickness."""
        d1 = sf.boundary_layer_thickness(NU, 400.0)
        d4 = sf.boundary_layer_thickness(4.0 * NU, 400.0)
        self.assertAlmostEqual(d4, 2.0 * d1, delta=1e-12)

    def test_delta_valueerror_non_physical_inputs(self):
        """Non-positive kinematic viscosity or gradient raise ValueError."""
        for nu in (0.0, -1.5e-5):
            with self.assertRaises(ValueError):
                sf.boundary_layer_thickness(nu, 400.0)
        for a in (0.0, -400.0):
            with self.assertRaises(ValueError):
                sf.boundary_layer_thickness(NU, a)


class WallShearStressTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the stagnation-wall-shear
    computation tau_w = mu u_inf sqrt(a / nu) fpp with the FPP_2D
    (Hiemenz) or FPP_AXISYM (Homann) similarity wall-shear constant."""

    def test_cylinder_wall_shear_worked_example(self):
        """Cylinder wall shear at the u_e = u_inf station:
        tau_w = 3.508772 Pa."""
        self.assertAlmostEqual(
            sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder"),
            3.508772, delta=1e-5)

    def test_sphere_wall_shear_worked_example(self):
        """Axisymmetric wall shear: tau_w = 3.234181 Pa."""
        self.assertAlmostEqual(
            sf.wall_shear_stress(RHO, NU, 300.0, U_INF, "sphere"),
            3.234181, delta=1e-5)

    def test_wall_shear_ratio_identity_axisymmetric_over_two_d(self):
        """Ratio identity: tau_sph / tau_cyl = (FPP_AXISYM / FPP_2D)
        sqrt(1.5 / 2) at equal speed and radius (0.9217416)."""
        tau_cyl = sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder")
        tau_sph = sf.wall_shear_stress(RHO, NU, 300.0, U_INF, "sphere")
        expected = (sf.FPP_AXISYM / sf.FPP_2D) * math.sqrt(1.5 / 2.0)
        self.assertAlmostEqual(tau_sph / tau_cyl, expected, delta=1e-9)
        self.assertAlmostEqual(tau_sph / tau_cyl, 0.9217416, delta=1e-7)

    def test_wall_shear_scales_linearly_with_u_inf(self):
        """Doubling u_inf at fixed rho, nu, a doubles tau_w to
        7.017544 Pa (linear similarity-layer scaling)."""
        tau_30 = sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder")
        tau_60 = sf.wall_shear_stress(RHO, NU, 400.0, 60.0, "cylinder")
        self.assertAlmostEqual(tau_60, 2.0 * tau_30, delta=1e-9)
        self.assertAlmostEqual(tau_60, 7.017544, delta=1e-6)

    def test_wall_shear_closed_form_identity_mu_form(self):
        """The mu closed form tau = mu u_inf sqrt(a / nu) fpp equals the
        algebraic identity rho u_inf sqrt(a nu) fpp within 1e-12."""
        fpp = sf.FPP_2D
        mu_form = (RHO * NU) * U_INF * math.sqrt(400.0 / NU) * fpp
        rho_form = RHO * U_INF * math.sqrt(400.0 * NU) * fpp
        self.assertAlmostEqual(mu_form, rho_form, delta=1e-12)
        self.assertAlmostEqual(
            sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder"),
            mu_form, delta=1e-12)

    def test_wall_shear_valueerror_fluid_properties(self):
        """Non-positive density or kinematic viscosity raise ValueError."""
        for rho in (0.0, -1.225):
            with self.assertRaises(ValueError):
                sf.wall_shear_stress(rho, NU, 400.0, U_INF, "cylinder")
        for nu in (0.0, -1.5e-5):
            with self.assertRaises(ValueError):
                sf.wall_shear_stress(RHO, nu, 400.0, U_INF, "cylinder")

    def test_wall_shear_valueerror_gradient_and_speed(self):
        """Non-positive gradient or freestream speed raise ValueError."""
        for a in (0.0, -400.0):
            with self.assertRaises(ValueError):
                sf.wall_shear_stress(RHO, NU, a, U_INF, "cylinder")
        for u in (0.0, -30.0):
            with self.assertRaises(ValueError):
                sf.wall_shear_stress(RHO, NU, 400.0, u, "cylinder")

    def test_wall_shear_valueerror_flow_type(self):
        """An unknown flow type raises ValueError."""
        with self.assertRaises(ValueError):
            sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cone")
        with self.assertRaises(ValueError):
            sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "ogive")


class SkinFrictionCoefficientTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the skin-friction-coefficient
    conversion Cf = 2 tau_w / (rho u_inf^2) from the freestream dynamic
    pressure."""

    def test_cylinder_skin_friction_worked_example(self):
        """Cylinder Cf = 6.365119e-3, in the 5.8e-3 to 6.4e-3 band."""
        cf = sf.skin_friction_coefficient(
            RHO, U_INF,
            sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder"))
        self.assertAlmostEqual(cf, 6.365119e-3, delta=1e-7)
        self.assertGreaterEqual(cf, 5.8e-3)
        self.assertLessEqual(cf, 6.4e-3)

    def test_sphere_skin_friction_worked_example(self):
        """Sphere Cf = 5.866995e-3, inside the same band."""
        cf = sf.skin_friction_coefficient(
            RHO, U_INF,
            sf.wall_shear_stress(RHO, NU, 300.0, U_INF, "sphere"))
        self.assertAlmostEqual(cf, 5.866995e-3, delta=1e-7)
        self.assertGreaterEqual(cf, 5.8e-3)
        self.assertLessEqual(cf, 6.4e-3)

    def test_skin_friction_identity_round_trip(self):
        """Cf = 2 tau / (rho u_inf^2) round-trips: the shear recovered
        from Cf and the dynamic pressure equals the input tau_w."""
        tau = sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder")
        cf = sf.skin_friction_coefficient(RHO, U_INF, tau)
        q = 0.5 * RHO * U_INF * U_INF
        self.assertAlmostEqual(cf, tau / q, delta=1e-12)
        self.assertAlmostEqual(cf * q, tau, delta=1e-12)

    def test_skin_friction_valueerror_non_physical_inputs(self):
        """Non-positive density or speed and negative shear raise
        ValueError."""
        for rho in (0.0, -1.225):
            with self.assertRaises(ValueError):
                sf.skin_friction_coefficient(rho, U_INF, 3.5)
        for u in (0.0, -30.0):
            with self.assertRaises(ValueError):
                sf.skin_friction_coefficient(RHO, u, 3.5)
        with self.assertRaises(ValueError):
            sf.skin_friction_coefficient(RHO, U_INF, -0.1)


class SweptStagnationGradientTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the swept-leading-edge
    crossflow-plane reduction, chordwise gradient 2 u_n / R from the
    velocity component normal to the leading edge."""

    def test_swept_30_deg_worked_example(self):
        """R = 0.02 m at 30 deg sweep: a = 2598.0762 1/s."""
        self.assertAlmostEqual(
            sf.swept_stagnation_gradient(U_INF, 0.02, 30.0),
            2598.0762, delta=1e-4)

    def test_sweep_zero_reproduces_cylinder_gradient(self):
        """Zero sweep reproduces the unswept cylinder gradient
        2 u_inf / R = 3000.0 1/s at R = 0.02 m."""
        a_sw = sf.swept_stagnation_gradient(U_INF, 0.02, 0.0)
        self.assertAlmostEqual(a_sw, 3000.0, delta=1e-9)
        self.assertAlmostEqual(
            a_sw,
            sf.stagnation_velocity_gradient("cylinder", U_INF, 0.02),
            delta=1e-9)

    def test_swept_normal_component_crossflow_worked_example(self):
        """Crossflow-plane 2-D form with u_n = 25.9808 m/s: tau_w =
        7.744292 Pa and Cf = 1.873147e-2."""
        a_sw = sf.swept_stagnation_gradient(U_INF, 0.02, 30.0)
        u_n = U_INF * math.cos(math.radians(30.0))
        tau = sf.wall_shear_stress(RHO, NU, a_sw, u_n, "cylinder")
        cf = sf.skin_friction_coefficient(RHO, u_n, tau)
        self.assertAlmostEqual(u_n, 25.9808, delta=1e-4)
        self.assertAlmostEqual(tau, 7.744292, delta=1e-5)
        self.assertAlmostEqual(cf, 1.873147e-2, delta=1e-7)

    def test_negative_sweep_symmetric(self):
        """Sweep sign flips the crossflow direction only, so the
        chordwise gradient magnitude is unchanged."""
        a_pos = sf.swept_stagnation_gradient(U_INF, 0.02, 30.0)
        a_neg = sf.swept_stagnation_gradient(U_INF, 0.02, -30.0)
        self.assertAlmostEqual(a_pos, a_neg, delta=1e-12)

    def test_swept_valueerror_speed_and_radius(self):
        """Non-positive speed or radius raise ValueError."""
        for u in (0.0, -30.0):
            with self.assertRaises(ValueError):
                sf.swept_stagnation_gradient(u, 0.02, 30.0)
        for r in (0.0, -0.02):
            with self.assertRaises(ValueError):
                sf.swept_stagnation_gradient(U_INF, r, 30.0)

    def test_swept_valueerror_sweep_out_of_range(self):
        """Sweep magnitude beyond 90 degrees raises ValueError."""
        for sweep in (95.0, -95.0, 90.0001, -90.5):
            with self.assertRaises(ValueError):
                sf.swept_stagnation_gradient(U_INF, 0.02, sweep)


class DeterminismConstantsBoundsTest(unittest.TestCase):
    """Step 7 closure: flow-type treatment note (Hiemenz vs Homann
    constants), magnitude bounds and deterministic contract."""

    def test_module_constants_match_standard_tabulations(self):
        """The module carries the classical similarity constants
        FPP_2D = 1.2326, FPP_AXISYM = 1.3119 and BL_DELTA_COEF = 2.4."""
        self.assertEqual(sf.FPP_2D, 1.2326)
        self.assertEqual(sf.FPP_AXISYM, 1.3119)
        self.assertEqual(sf.BL_DELTA_COEF, 2.4)

    def test_worked_example_magnitude_bounds(self):
        """Worked-example magnitudes: delta in 4.6e-4 to 5.4e-4 m and
        Cf in 5.8e-3 to 6.4e-3 for the cylinder and sphere cases."""
        for a in (400.0, 300.0):
            d = sf.boundary_layer_thickness(NU, a)
            self.assertGreaterEqual(d, 4.6e-4)
            self.assertLessEqual(d, 5.4e-4)
        tau_cyl = sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder")
        tau_sph = sf.wall_shear_stress(RHO, NU, 300.0, U_INF, "sphere")
        for tau in (tau_cyl, tau_sph):
            cf = sf.skin_friction_coefficient(RHO, U_INF, tau)
            self.assertGreaterEqual(cf, 5.8e-3)
            self.assertLessEqual(cf, 6.4e-3)

    def test_low_speed_leading_edge_parametric_bounds(self):
        """At low-speed leading edges (radius 0.02 to 0.5 m, speed 20 to
        100 m/s) the layer stays sub-millimeter (0.1 to 1 mm) and Cf
        stays in 1e-3 to 2e-2, an order of magnitude above the smooth
        surface value at a comparable length scale."""
        for radius, speed in ((0.1, 50.0), (0.02, 60.0), (0.3, 40.0)):
            a = sf.stagnation_velocity_gradient("cylinder", speed, radius)
            d = sf.boundary_layer_thickness(NU, a)
            self.assertGreaterEqual(d, 1.0e-4)
            self.assertLessEqual(d, 1.0e-3)
            tau = sf.wall_shear_stress(RHO, NU, a, speed, "cylinder")
            cf = sf.skin_friction_coefficient(RHO, speed, tau)
            self.assertGreaterEqual(cf, 1.0e-3)
            self.assertLessEqual(cf, 2.0e-2)

    def test_deterministic_no_rng_no_ode_integration(self):
        """Repeated calls are bit-identical, and the module source
        contains no random import and no ODE integration call."""
        for _ in range(3):
            self.assertEqual(
                sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder"),
                sf.wall_shear_stress(RHO, NU, 400.0, U_INF, "cylinder"))
            self.assertEqual(
                sf.boundary_layer_thickness(NU, 400.0),
                sf.boundary_layer_thickness(NU, 400.0))
        logic_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "stagnation_flow_boundary_layer_logic.py")
        with open(logic_path, "r") as handle:
            source = handle.read()
        self.assertNotIn("import random", source)
        self.assertNotIn("odeint", source)
        self.assertNotIn("solve_ivp", source)
        self.assertNotIn("integrate.", source)
        self.assertNotIn("quad(", source)
        self.assertNotIn("numpy", source)
        self.assertNotIn("scipy", source)


if __name__ == "__main__":
    unittest.main()
