"""Contract test for the hertzian-contact-stress leaf (structures/fem).

Exercises the SKILL.md workflow end to end: step 1 gather the contact
inputs (load, geometry radii with sign convention, axial length, material
properties, yield strength, point versus line contact class); step 2
compute the equivalent elastic modulus; step 3 compute the equivalent
radius of curvature; step 4 solve the contact patch for the patch radius
or half-width and the maximum contact pressure; step 5 read the
subsurface stress state (subsurface shear stress depth and magnitude, von
Mises maximum under the patch); step 6 run the yield-limit load check
(yield-limit pressure, yield-limit load, margin, verdict); step 7 confirm
the deterministic checks offline. The worked-example anchors are the real
outputs of the module on the steel-pair reference materials (E = 210 GPa,
nu = 0.3), which the spec pins as the validation targets. Exact-field
scans of the Huber and plane-strain elastic solutions verify the
subsurface constants, and the full ValueError rejection surface of
non-physical inputs is covered.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)
import hertzian_contact_stress_logic as hcs

E_STEEL = 210e9
NU = 0.3
E_STAR = hcs.equivalent_modulus(E_STEEL, NU, E_STEEL, NU)


def assert_rel(testcase, actual, expected, rel=1e-6):
    """Assert that actual and expected agree to relative tolerance rel."""
    testcase.assertTrue(
        math.isclose(actual, expected, rel_tol=rel, abs_tol=0.0),
        "{} not within {} relative of {}".format(actual, rel, expected),
    )


class TestEquivalentModulus(unittest.TestCase):
    """Workflow step 2: compute the equivalent elastic modulus E*."""

    def test_equivalent_modulus_steel_pair_anchor(self):
        """Step 2 anchor: the steel pair 210 GPa/0.3 twice gives E* = 1.1538461538e11 Pa within 1e-3 relative."""
        assert_rel(self, E_STAR, 1.1538461538e11, rel=1e-3)
        assert_rel(
            self, E_STAR, E_STEEL / (2.0 * (1.0 - NU * NU)), rel=1e-9
        )

    def test_equivalent_modulus_same_material_degeneracy(self):
        """Step 2 identity: E* of identical materials reduces to E/(2*(1-nu**2)) to float noise."""
        for e in (70e9, 105e9, 210e9):
            for nu in (0.25, 0.3, 0.33):
                est = hcs.equivalent_modulus(e, nu, e, nu)
                assert_rel(self, est, e / (2.0 * (1.0 - nu * nu)), rel=1e-12)

    def test_equivalent_modulus_dissimilar_materials_defining_form(self):
        """Step 2 defining relation: E* obeys 1/E* = (1-nu1**2)/E1 + (1-nu2**2)/E2 for a steel-on-aluminum pair."""
        e1, nu1, e2, nu2 = 70e9, 0.33, 210e9, 0.3
        est = hcs.equivalent_modulus(e1, nu1, e2, nu2)
        expected = 1.0 / ((1.0 - nu1 * nu1) / e1 + (1.0 - nu2 * nu2) / e2)
        assert_rel(self, est, expected, rel=1e-12)
        assert_rel(self, est, 5.86052e10, rel=1e-3)


class TestEquivalentRadius(unittest.TestCase):
    """Workflow step 3: compute the equivalent radius of curvature Re."""

    def test_equivalent_radius_flat_limit(self):
        """Step 3 flat limit: a roller on a flat, Re = r1 for the 50 mm roller, matches 0.05 m exactly."""
        assert_rel(self, hcs.equivalent_radius(0.050, math.inf), 0.050, rel=1e-12)

    def test_equivalent_radius_socket_conformal(self):
        """Step 3 concave socket: the 10 mm ball in a 25 mm socket gives Re = 16.666667 mm within 1e-6 relative."""
        assert_rel(
            self, hcs.equivalent_radius(0.010, -0.025), 1.0 / 60.0, rel=1e-9
        )

    def test_equivalent_radius_bore(self):
        """Step 3 concave bore: the 15 mm roller in a 20 mm bore gives Re = 60 mm."""
        assert_rel(self, hcs.equivalent_radius(0.015, -0.020), 0.060, rel=1e-12)

    def test_equivalent_radius_convex_pair(self):
        """Step 3 convex pair: the 450 mm wheel on the 300 mm rail crown gives Re = 180 mm."""
        assert_rel(self, hcs.equivalent_radius(0.450, 0.300), 0.180, rel=1e-12)

    def test_equivalent_radius_concave_identity(self):
        """Step 3 identity: equivalent_radius(r1, -r2) equals 1/(1/r1 - 1/r2) for r2 > r1 to float noise."""
        for r1, r2 in ((0.010, 0.025), (0.015, 0.020), (0.020, 0.050)):
            assert_rel(
                self,
                hcs.equivalent_radius(r1, -r2),
                1.0 / (1.0 / r1 - 1.0 / r2),
                rel=1e-12,
            )


class TestContactPatch(unittest.TestCase):
    """Workflow step 4: solve the contact patch and the maximum contact pressure."""

    def test_crossed_equal_cylinders_matches_sphere_on_flat(self):
        """Step 4 crossed-cylinder equivalence: crossed 10 mm cylinders give the same circular patch as a 10 mm sphere on a flat (a = 0.319125 mm, p0 = 2344.2 MPa) within 1e-9 relative."""
        a_cross, p0_cross = hcs.point_patch(500.0, E_STAR, 0.010)
        a_flat, p0_flat = hcs.point_patch(
            500.0, E_STAR, hcs.equivalent_radius(0.010, math.inf)
        )
        assert_rel(self, a_cross, a_flat, rel=1e-9)
        assert_rel(self, p0_cross, p0_flat, rel=1e-9)
        assert_rel(self, a_cross, 3.19125e-4, rel=1e-3)
        assert_rel(self, p0_cross, 2344.2e6, rel=1e-3)

    def test_case_a_roller_on_flat_patch(self):
        """Step 4 line contact: the 50 kN roller on the flat (Re = 50 mm, L = 100 mm) gives half-width b = 5.25232e-4 m and maximum contact pressure p0 = 6.0603682883e8 Pa within 1e-3 relative, and the strip p0 from 2P/(pi b L) equals the load form sqrt(P E*/(pi Re L)) to 1e-9."""
        b, p0 = hcs.line_patch(50000.0, E_STAR, 0.05, 0.1)
        assert_rel(self, b, 5.25232e-4, rel=1e-3)
        assert_rel(self, p0, 6.0603682883e8, rel=1e-3)
        load_form = math.sqrt(50000.0 * E_STAR / (math.pi * 0.05 * 0.1))
        assert_rel(self, p0, load_form, rel=1e-9)
        assert_rel(self, p0, 2.0 * 50000.0 / (math.pi * b * 0.1), rel=1e-12)

    def test_case_b_ball_in_socket_patch(self):
        """Step 4 point contact: the 700 N ball in the socket (Re = 16.666667 mm) gives circular patch radius a = 4.23272e-4 m and p0 = 1.86552e9 Pa within 1e-3 relative."""
        a, p0 = hcs.point_patch(700.0, E_STAR, 0.0166666667)
        assert_rel(self, a, 4.23272e-4, rel=1e-3)
        assert_rel(self, p0, 1.86552e9, rel=1e-3)

    def test_case_c_wheel_rail_patch(self):
        """Step 4 line contact: the 80 kN wheel-rail pair (Re = 180 mm, L = 15 mm) gives b = 3.2547 mm and p0 = 1043.2 MPa, and p0 = 1.49 sigma_y sits below the 1.6 line yield limit."""
        b, p0 = hcs.line_patch(80000.0, E_STAR, 0.18, 0.015)
        assert_rel(self, b, 3.2547e-3, rel=1e-3)
        assert_rel(self, p0, 1043.2e6, rel=1e-3)
        assert_rel(self, p0 / 700e6, 1.49, rel=1e-2)

    def test_case_e_roller_in_race_patch(self):
        """Step 4 conformal line contact: the 10 kN roller in the 20 mm race (Re = 60 mm, L = 20 mm) gives b = 0.57536 mm and p0 = 553.23 MPa."""
        b, p0 = hcs.line_patch(10000.0, E_STAR, 0.06, 0.02)
        assert_rel(self, b, 5.7536e-4, rel=1e-3)
        assert_rel(self, p0, 553.23e6, rel=1e-3)

    def test_point_mean_pressure_two_thirds_p0(self):
        """Step 4 identity: the mean contact pressure P/(pi a^2) equals 2 p0/3 exactly for the circular patch."""
        a, p0 = hcs.point_patch(1000.0, E_STAR, 0.010)
        assert_rel(self, 1000.0 / (math.pi * a * a), 2.0 * p0 / 3.0, rel=1e-12)

    def test_point_patch_inverse_load_round_trip(self):
        """Step 4 inverse closed form: recovering P = 2 pi a^2 p0 /3 from the patch returns the input 1000.0 N to 1e-9 relative."""
        a, p0 = hcs.point_patch(1000.0, E_STAR, 0.010)
        recovered = 2.0 * math.pi * a * a * p0 / 3.0
        assert_rel(self, recovered, 1000.0, rel=1e-9)

    def test_line_patch_inverse_load_round_trip(self):
        """Step 4 inverse closed form: recovering P = pi b L p0 /2 from the strip returns the input 50000.0 N to 1e-9 relative."""
        b, p0 = hcs.line_patch(50000.0, E_STAR, 0.05, 0.1)
        recovered = math.pi * b * 0.1 * p0 / 2.0
        assert_rel(self, recovered, 50000.0, rel=1e-9)


class TestSubsurfaceState(unittest.TestCase):
    """Workflow step 5: read the subsurface stress state under the patch."""

    def test_case_a_subsurface_state(self):
        """Step 5 strip subsurface: max shear 181.81 MPa at z = 0.4097 mm (0.78 b) and max von Mises 337.56 MPa at z = 0.3677 mm (0.70 b)."""
        b, p0 = hcs.line_patch(50000.0, E_STAR, 0.05, 0.1)
        sub = hcs.line_subsurface(p0, b)
        assert_rel(self, sub["z_tau"], 0.4097e-3, rel=1e-3)
        assert_rel(self, sub["tau_max"], 181.81e6, rel=1e-3)
        assert_rel(self, sub["z_vm"], 0.3677e-3, rel=1e-3)
        assert_rel(self, sub["vm_max"], 337.56e6, rel=1e-3)
        assert_rel(self, sub["z_tau"], 0.78 * b, rel=1e-12)
        assert_rel(self, sub["vm_max"], 0.557 * p0, rel=1e-12)

    def test_case_b_subsurface_state_fully_elastic(self):
        """Step 5 point subsurface: the ball-in-socket max shear 578.31 MPa and max von Mises 1156.62 MPa at z = 0.2032 mm keep the contact fully elastic below sigma_y = 1200 MPa."""
        a, p0 = hcs.point_patch(700.0, E_STAR, 0.0166666667)
        sub = hcs.point_subsurface(p0, a)
        assert_rel(self, sub["z_tau"], 0.2032e-3, rel=1e-3)
        assert_rel(self, sub["tau_max"], 578.31e6, rel=1e-3)
        assert_rel(self, sub["vm_max"], 1156.62e6, rel=1e-3)
        self.assertLess(sub["vm_max"], 1200e6)
        self.assertLess(p0, 1.6 * 1200e6)

    def test_case_c_subsurface_state(self):
        """Step 5 wheel-rail subsurface: max shear 312.96 MPa at z = 2.539 mm and max von Mises 581.06 MPa at z = 2.278 mm."""
        b, p0 = hcs.line_patch(80000.0, E_STAR, 0.18, 0.015)
        sub = hcs.line_subsurface(p0, b)
        assert_rel(self, sub["z_tau"], 2.539e-3, rel=1e-3)
        assert_rel(self, sub["tau_max"], 312.96e6, rel=1e-3)
        assert_rel(self, sub["z_vm"], 2.278e-3, rel=1e-3)
        assert_rel(self, sub["vm_max"], 581.06e6, rel=1e-3)

    def test_case_d_subsurface_regime_between_first_and_full_yield(self):
        """Step 5 point subsurface: the crossed-cylinder max von Mises 1453.39 MPa exceeds sigma_y = 1200 MPa while p0/sigma_y = 1.95 sits between first subsurface yield at 1.6 sigma_y and the 3.3 sigma_y spherical yield-limit pressure."""
        a, p0 = hcs.point_patch(500.0, E_STAR, 0.010)
        sub = hcs.point_subsurface(p0, a)
        assert_rel(self, a, 3.1913e-4, rel=1e-3)
        assert_rel(self, sub["vm_max"], 1453.39e6, rel=1e-3)
        self.assertGreater(sub["vm_max"], 1200e6)
        self.assertGreater(p0 / 1200e6, 1.6)
        self.assertLess(p0 / 1200e6, 3.3)

    def test_point_subsurface_constants_against_axis_scan(self):
        """Step 5 verification: scanning the exact Huber axisymmetric field (sigma_z = -p0/(1+zeta^2), sigma_r = -p0*((1+nu)*(1 - zeta*atan(1/zeta)) - 1/(2*(1+zeta^2)))) reproduces the subsurface-shear-stress constants z/a = 0.4810, tau/p0 = 0.3100 and vm/p0 = 0.6200 within 1e-2."""
        nu = 0.3
        best_z = best_tau = best_vm = 0.0
        n = 40000
        for i in range(n + 1):
            zeta = 4.0 * i / n
            zatan = 0.0 if zeta == 0.0 else zeta * math.atan(1.0 / zeta)
            sz = -1.0 / (1.0 + zeta * zeta)
            sr = -((1.0 + nu) * (1.0 - zatan) - 1.0 / (2.0 * (1.0 + zeta * zeta)))
            tau = abs(sz - sr) / 2.0
            if tau > best_tau:
                best_z, best_tau = zeta, tau
                best_vm = 2.0 * tau
        assert_rel(self, best_tau, 0.31, rel=1e-2)
        assert_rel(self, best_vm, 0.62, rel=1e-2)
        self.assertAlmostEqual(best_z, 0.48, delta=0.01)
        # surface-center state at zeta = 0: tau/p0 = (1 - (0.5 + nu))/2 = 0.1
        self.assertAlmostEqual((1.0 - (0.5 + nu)) / 2.0, 0.1, delta=1e-12)

    def test_line_subsurface_constants_against_centerline_scan(self):
        """Step 5 verification: scanning the exact plane-strain centerline field (sigma_z = -p0/sqrt(1+zeta^2), sigma_y = -p0*((1+2 zeta^2)/sqrt(1+zeta^2) - 2 zeta), sigma_x = -2 nu p0 (sqrt(1+zeta^2) - zeta)) reproduces z/b = 0.7862 with tau/p0 = 0.3003 and z/b = 0.7042 with vm/p0 = 0.5575 within 3e-2."""
        nu = 0.3
        n = 40000
        best_tz = best_tt = best_vz = best_vm = 0.0
        for i in range(n + 1):
            zeta = 4.0 * i / n
            sz = -1.0 / math.sqrt(1.0 + zeta * zeta)
            sy = -((1.0 + 2.0 * zeta * zeta) / math.sqrt(1.0 + zeta * zeta) - 2.0 * zeta)
            sx = -2.0 * nu * (math.sqrt(1.0 + zeta * zeta) - zeta)
            s = sorted((sz, sy, sx))
            tau = (s[2] - s[0]) / 2.0
            vm = math.sqrt(
                0.5 * ((s[0] - s[1]) ** 2 + (s[1] - s[2]) ** 2 + (s[2] - s[0]) ** 2)
            )
            if tau > best_tt:
                best_tz, best_tt = zeta, tau
            if vm > best_vm:
                best_vz, best_vm = zeta, vm
        self.assertAlmostEqual(best_tt, 0.3003, delta=0.01)
        self.assertAlmostEqual(best_tz, 0.7862, delta=0.02)
        self.assertAlmostEqual(best_vm, 0.5575, delta=0.01)
        self.assertAlmostEqual(best_vz, 0.7042, delta=0.02)


class TestYieldLimitCheck(unittest.TestCase):
    """Workflow step 6: run the yield-limit load check."""

    def test_case_a_yield_limit_check(self):
        """Step 6 strip yield check: p0_yield = 1.6*900 = 1440.0 MPa, margin 2.3761, P_yield = 282.291 kN, verdict below the yield limit."""
        b, p0 = hcs.line_patch(50000.0, E_STAR, 0.05, 0.1)
        y = hcs.check_yield_margin(p0, 900e6, point_contact=False)
        assert_rel(self, y["p0_yield"], 1440.0e6, rel=1e-9)
        assert_rel(self, y["margin"], 2.3761, rel=1e-3)
        self.assertTrue(y["below_yield_limit"])
        py = hcs.yield_limit_load(
            900e6, E_STAR, 0.05, point_contact=False, length=0.1
        )
        assert_rel(self, py, 282.291e3, rel=1e-3)
        self.assertGreater(py / 50000.0, 5.6)

    def test_case_b_yield_limit_check(self):
        """Step 6 point yield check: p0_yield = 3.3*1200 = 3960.0 MPa, margin 2.1227, P_yield = 6.696 kN for the conformal socket."""
        a, p0 = hcs.point_patch(700.0, E_STAR, 0.0166666667)
        y = hcs.check_yield_margin(p0, 1200e6)
        assert_rel(self, y["p0_yield"], 3960.0e6, rel=1e-9)
        assert_rel(self, y["margin"], 2.1227, rel=1e-3)
        self.assertTrue(y["below_yield_limit"])
        py = hcs.yield_limit_load(1200e6, E_STAR, 0.0166666667)
        assert_rel(self, py, 6.696e3, rel=1e-3)

    def test_case_c_yield_limit_check(self):
        """Step 6 wheel-rail yield check: p0_yield = 1120.0 MPa, margin 1.0736, P_yield = 92.215 kN, the ~1 GPa rail contact running just under the line limit."""
        b, p0 = hcs.line_patch(80000.0, E_STAR, 0.18, 0.015)
        y = hcs.check_yield_margin(p0, 700e6, point_contact=False)
        assert_rel(self, y["p0_yield"], 1120.0e6, rel=1e-9)
        assert_rel(self, y["margin"], 1.0736, rel=1e-3)
        self.assertTrue(y["below_yield_limit"])
        py = hcs.yield_limit_load(
            700e6, E_STAR, 0.18, point_contact=False, length=0.015
        )
        assert_rel(self, py, 92.215e3, rel=1e-3)

    def test_case_d_yield_limit_check(self):
        """Step 6 crossed-cylinder yield check: p0_yield = 3960.0 MPa, margin 1.6893, P_yield = 2.410 kN in the elastic-plastic growth regime of the standard static check."""
        a, p0 = hcs.point_patch(500.0, E_STAR, 0.010)
        y = hcs.check_yield_margin(p0, 1200e6)
        assert_rel(self, y["p0_yield"], 3960.0e6, rel=1e-9)
        assert_rel(self, y["margin"], 1.6893, rel=1e-3)
        self.assertTrue(y["below_yield_limit"])
        py = hcs.yield_limit_load(1200e6, E_STAR, 0.010)
        assert_rel(self, py, 2.410e3, rel=1e-3)

    def test_case_e_yield_limit_check_fattest_margin(self):
        """Step 6 conformal race yield check: the 10 kN roller in the 20 mm race gives margin 3.4705 and P_yield = 120.444 kN, the fattest margin of the set."""
        b, p0 = hcs.line_patch(10000.0, E_STAR, 0.06, 0.02)
        y = hcs.check_yield_margin(p0, 1200e6, point_contact=False)
        assert_rel(self, y["margin"], 3.4705, rel=1e-3)
        assert_rel(self, y["p0_yield"], 1920.0e6, rel=1e-9)
        self.assertTrue(y["below_yield_limit"])
        py = hcs.yield_limit_load(
            1200e6, E_STAR, 0.06, point_contact=False, length=0.02
        )
        assert_rel(self, py, 120.444e3, rel=1e-3)
        self.assertGreater(y["margin"], 3.0)

    def test_yield_limit_pressure_factors_and_verdict_flip(self):
        """Step 6 factors and verdict: yield_limit_pressure returns 3.3 sigma_y for point and 1.6 sigma_y for line contact, and below_yield_limit turns False with margin below one once p0 passes p0_yield."""
        assert_rel(self, hcs.yield_limit_pressure(900e6), 3.3 * 900e6, rel=1e-12)
        assert_rel(
            self, hcs.yield_limit_pressure(900e6, point_contact=False),
            1.6 * 900e6, rel=1e-12,
        )
        p0_y = hcs.yield_limit_pressure(1200e6)
        over = hcs.check_yield_margin(1.01 * p0_y, 1200e6)
        self.assertFalse(over["below_yield_limit"])
        self.assertLess(over["margin"], 1.0)
        at = hcs.check_yield_margin(p0_y, 1200e6)
        self.assertTrue(at["below_yield_limit"])
        assert_rel(self, at["margin"], 1.0, rel=1e-12)

    def test_yield_limit_load_margin_power_identity(self):
        """Step 6 identity: yield_limit_load equals the applied load times margin**3 (point) or margin**2 (line) to 1e-6, the closed-form inversion check."""
        a, p0b = hcs.point_patch(700.0, E_STAR, 0.0166666667)
        yb = hcs.check_yield_margin(p0b, 1200e6)
        assert_rel(
            self,
            hcs.yield_limit_load(1200e6, E_STAR, 0.0166666667),
            700.0 * yb["margin"] ** 3,
            rel=1e-6,
        )
        b, p0a = hcs.line_patch(50000.0, E_STAR, 0.05, 0.1)
        ya = hcs.check_yield_margin(p0a, 900e6, point_contact=False)
        assert_rel(
            self,
            hcs.yield_limit_load(
                900e6, E_STAR, 0.05, point_contact=False, length=0.1
            ),
            50000.0 * ya["margin"] ** 2,
            rel=1e-6,
        )

class TestValueErrorRejection(unittest.TestCase):
    """Non-physical inputs are rejected across the module."""

    def test_valueerrors_equivalent_modulus(self):
        """Step 2 rejection: zero or negative Young moduli and Poisson ratios at 0.5, 0.6 or negative raise ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                hcs.equivalent_modulus(bad, 0.3, 210e9, 0.3)
            with self.assertRaises(ValueError):
                hcs.equivalent_modulus(210e9, 0.3, bad, 0.3)
        for bad_nu in (0.5, 0.6, -0.1):
            with self.assertRaises(ValueError):
                hcs.equivalent_modulus(210e9, bad_nu, 210e9, 0.3)
            with self.assertRaises(ValueError):
                hcs.equivalent_modulus(210e9, 0.3, 210e9, bad_nu)

    def test_valueerrors_equivalent_radius(self):
        """Step 3 rejection: r1 at zero or negative, r2 at zero or -inf, and a concave partner not larger than the convex body all raise ValueError."""
        with self.assertRaises(ValueError):
            hcs.equivalent_radius(0.0, math.inf)
        with self.assertRaises(ValueError):
            hcs.equivalent_radius(-0.01, math.inf)
        with self.assertRaises(ValueError):
            hcs.equivalent_radius(0.01, 0.0)
        with self.assertRaises(ValueError):
            hcs.equivalent_radius(0.01, float("-inf"))
        with self.assertRaises(ValueError):
            hcs.equivalent_radius(0.025, -0.010)
        with self.assertRaises(ValueError):
            hcs.equivalent_radius(0.010, -0.010)

    def test_valueerrors_patch_functions(self):
        """Step 4 rejection: zero load, zero modulus or zero radius on the patch solvers raise ValueError."""
        with self.assertRaises(ValueError):
            hcs.point_patch(0.0, E_STAR, 0.010)
        with self.assertRaises(ValueError):
            hcs.point_patch(-1.0, E_STAR, 0.010)
        with self.assertRaises(ValueError):
            hcs.point_patch(500.0, 0.0, 0.010)
        with self.assertRaises(ValueError):
            hcs.point_patch(500.0, E_STAR, 0.0)
        with self.assertRaises(ValueError):
            hcs.line_patch(0.0, E_STAR, 0.05, 0.1)
        with self.assertRaises(ValueError):
            hcs.line_patch(50000.0, E_STAR, 0.05, 0.0)
        with self.assertRaises(ValueError):
            hcs.line_patch(50000.0, E_STAR, 0.05, -0.1)

    def test_valueerrors_subsurface(self):
        """Step 5 rejection: zero or negative p0 and zero patch size raise ValueError on both subsurface readers."""
        with self.assertRaises(ValueError):
            hcs.point_subsurface(0.0, 1e-4)
        with self.assertRaises(ValueError):
            hcs.point_subsurface(1e9, 0.0)
        with self.assertRaises(ValueError):
            hcs.line_subsurface(-1e9, 1e-4)
        with self.assertRaises(ValueError):
            hcs.line_subsurface(1e9, 0.0)

    def test_valueerrors_yield_functions(self):
        """Step 6 rejection: zero yield strength, missing or non-positive line length, and negative p0 raise ValueError."""
        with self.assertRaises(ValueError):
            hcs.yield_limit_pressure(0.0)
        with self.assertRaises(ValueError):
            hcs.yield_limit_pressure(-900e6)
        with self.assertRaises(ValueError):
            hcs.yield_limit_load(0.0, E_STAR, 0.05)
        with self.assertRaises(ValueError):
            hcs.yield_limit_load(900e6, E_STAR, 0.05, point_contact=False)
        with self.assertRaises(ValueError):
            hcs.yield_limit_load(900e6, E_STAR, 0.05, point_contact=False, length=0.0)
        with self.assertRaises(ValueError):
            hcs.check_yield_margin(-1.0, 900e6)
        with self.assertRaises(ValueError):
            hcs.check_yield_margin(0.0, 900e6)


class TestDeterminism(unittest.TestCase):
    """Workflow step 7: deterministic offline checks."""

    def test_determinism_repeat_calls(self):
        """Step 7 determinism: repeated patch solves return identical values and no third-party numerical imports appear in the module."""
        r1 = hcs.line_patch(80000.0, E_STAR, 0.18, 0.015)
        r2 = hcs.line_patch(80000.0, E_STAR, 0.18, 0.015)
        self.assertEqual(r1, r2)
        r3 = hcs.point_patch(500.0, E_STAR, 0.010)
        r4 = hcs.point_patch(500.0, E_STAR, 0.010)
        self.assertEqual(r3, r4)
        module_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "hertzian_contact_stress_logic.py",
        )
        with open(module_file) as fh:
            source = fh.read()
        for banned in ("numpy", "scipy", "pandas"):
            self.assertNotIn(banned, source)
        self.assertIn("import math", source)


if __name__ == "__main__":
    unittest.main()
