"""Contract test for added-mass-coefficients-potential-flow
(aerodynamics/aeroelasticity).  The value-delta sampler recomputes the
eval record from term presence here: this module docstring and every test
method docstring name the SKILL.md workflow steps they exercise.  Step 2
of the SKILL.md workflow, the catalog coefficient lookup of the added
mass (virtual mass, apparent mass) catalog per shape, is exercised by
the 2-D and 3-D catalog tests (cylinder, normal flat plate with its
exactly zero tangential coefficient, elliptic cylinder, sphere, prolate
and oblate spheroids with the displaced fluid mass ratio); step 3, the
energy picture with the fluid kinetic energy of translation, by the
kinetic-energy tests; step 4, the inertia model with the virtual mass
and the added-mass fraction against the body mass, by the virtual-mass
tests; step 5, the acceleration-reaction check of the body accelerating
in the fluid, by the reaction-force tests; step 6, the deterministic
offline check, by the ValueError rejection tests and the repeat-run
determinism test.  Pure stdlib unittest, offline, deterministic, no RNG.
"""

import math
import os
import sys
import unittest

# Portable sibling import (never a machine-local absolute sys.path).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import added_mass_coefficients_potential_flow_logic as am

RHO_WATER = 1000.0
RHO_AIR = 1.225


class TestEnergyPictureStep3(unittest.TestCase):
    """SKILL.md workflow step 3, the energy picture: the fluid kinetic
    energy of translation (1/2)*m_a*U^2 at a translation speed."""

    def test_kinetic_energy_worked_example_sphere(self):
        """Step 3 energy picture: the sphere of R = 0.5 m at rho = 1000
        carries m_a = 261.799388 kg, so the fluid kinetic energy at 4 m/s
        is 2094.395102 J."""
        m_added = am.sphere_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(am.kinetic_energy_of_translation(m_added, 4.0),
                               2094.395102, delta=1e-3)

    def test_kinetic_energy_zero_speed_is_zero_exact(self):
        """Step 3 energy picture: at translation speed 0 the fluid
        kinetic energy is exactly 0.0 (a body at rest sets up no flow)."""
        self.assertEqual(am.kinetic_energy_of_translation(100.0, 0.0), 0.0)

    def test_kinetic_energy_surface_integral_cylinder_anchor(self):
        """Step 3 energy picture against the surface-integral anchor of
        the SKILL.md: at R = 1 m, rho = 1000, U = 2 m/s the translating
        circle dipole potential integral gives T = 6283.185307 J/m,
        matching (1/2)*cylinder_added_mass(1000, 1)*4 to the 1.546e-11
        residual."""
        m_a = am.cylinder_added_mass(RHO_WATER, 1.0)
        self.assertAlmostEqual(m_a, 3141.592654, delta=1e-3)
        self.assertAlmostEqual(am.kinetic_energy_of_translation(m_a, 2.0),
                               6283.185307, delta=1e-3)

    def test_kinetic_energy_surface_integral_sphere_anchor(self):
        """Step 3 energy picture against the surface-integral anchor: the
        translating sphere doublet integral gives T = 4188.790205 J,
        matching (1/2)*sphere_added_mass(1000, 1)*4 to the 1.819e-12
        residual."""
        m_a = am.sphere_added_mass(RHO_WATER, 1.0)
        self.assertAlmostEqual(am.kinetic_energy_of_translation(m_a, 2.0),
                               4188.790205, delta=1e-3)

    def test_kinetic_energy_scales_with_speed_squared(self):
        """Step 3 energy picture: doubling the translation speed of the
        airship hull quadruples its axial fluid kinetic energy (T = 0.5
        *m_a*U^2 exactly by construction)."""
        m_a = am.prolate_spheroid_added_masses(RHO_AIR, 35.0, 7.0)['axial']
        t1 = am.kinetic_energy_of_translation(m_a, 2.0)
        t2 = am.kinetic_energy_of_translation(m_a, 4.0)
        self.assertAlmostEqual(t2, 4.0 * t1, delta=1e-9)


class TestAccelerationReactionStep5(unittest.TestCase):
    """SKILL.md workflow step 5, the acceleration-reaction check: the
    force m_a*acceleration the accelerating body must supply to the
    fluid."""

    def test_acceleration_reaction_worked_example_sphere(self):
        """Step 5 acceleration-reaction check: the sphere of R = 0.5 m at
        rho = 1000 has m_a = 261.799388 kg, so sustaining 4 m/s^2 needs
        1047.197551 N, the negative of the reaction on the body."""
        m_added = am.sphere_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(am.acceleration_reaction_force(m_added, 4.0),
                               1047.197551, delta=1e-3)

    def test_acceleration_reaction_airship_gap(self):
        """Step 5 acceleration-reaction check: at 0.2 m/s^2 the airship
        hull needs 104.054734 N axial but 1573.920839 N transverse, the
        15.1 times gap the inertia model of a pitch or heave must carry."""
        masses = am.prolate_spheroid_added_masses(RHO_AIR, 35.0, 7.0)
        axial_f = am.acceleration_reaction_force(masses['axial'], 0.2)
        transv_f = am.acceleration_reaction_force(masses['transverse'], 0.2)
        self.assertAlmostEqual(axial_f, 104.054734, delta=1e-3)
        self.assertAlmostEqual(transv_f, 1573.920839, delta=1e-3)
        self.assertGreater(transv_f / axial_f, 15.0)


class TestInertiaModelStep4(unittest.TestCase):
    """SKILL.md workflow step 4, the inertia model: the virtual mass
    m_body + m_a and the added-mass fraction m_a/(m_body + m_a)."""

    def test_virtual_mass_worked_example_sphere(self):
        """Step 4 inertia model: the 261.799388 kg added mass of the
        water sphere on a 200 kg body gives a 461.799388 kg virtual
        mass."""
        m_added = am.sphere_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(am.virtual_mass(200.0, m_added),
                               461.799388, delta=1e-3)

    def test_added_mass_fraction_worked_example_sphere(self):
        """Step 4 inertia model: the added-mass fraction 261.799388/(200
        + 261.799388) = 0.566912 shows the fluid inertia is the larger
        half of the virtual mass in water."""
        m_added = am.sphere_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(am.added_mass_fraction(m_added, 200.0),
                               0.566912, delta=1e-5)

    def test_airship_axial_virtual_mass_and_fraction(self):
        """Step 4 inertia model: the airship hull on a 6000 kg structure
        has an axial virtual mass of 6520.273672 kg and an axial
        added-mass fraction of 0.079793, under 8 percent."""
        m_axial = am.prolate_spheroid_added_masses(RHO_AIR, 35.0, 7.0)['axial']
        self.assertAlmostEqual(am.virtual_mass(6000.0, m_axial),
                               6520.273672, delta=1e-3)
        self.assertAlmostEqual(am.added_mass_fraction(m_axial, 6000.0),
                               0.079793, delta=1e-5)


class TestCylinderCatalogStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: the 2-D
    circular cylinder added mass rho*pi*R^2 per unit span, any in-plane
    direction."""

    def test_cylinder_worked_example_half_metre(self):
        """Step 2 catalog lookup: the circular float cylinder R = 0.5 m
        in fresh water carries 785.398163 kg/m per unit span."""
        self.assertAlmostEqual(am.cylinder_added_mass(RHO_WATER, 0.5),
                               785.398163, delta=1e-3)

    def test_cylinder_one_metre_value(self):
        """Step 2 catalog lookup: at R = 1 m, rho = 1000 the cylinder
        coefficient is 3141.592654 kg/m, the m_a behind the 6283.185307
        J/m kinetic-energy anchor."""
        self.assertAlmostEqual(am.cylinder_added_mass(RHO_WATER, 1.0),
                               3141.592654, delta=1e-3)

    def test_cylinder_radius_scaling_quadratic(self):
        """Step 2 catalog lookup: doubling the radius of the cylinder
        quadruples its per-unit-span added mass (rho*pi*R^2)."""
        m1 = am.cylinder_added_mass(RHO_WATER, 0.5)
        m2 = am.cylinder_added_mass(RHO_WATER, 1.0)
        self.assertAlmostEqual(m2, 4.0 * m1, delta=1e-9)


class TestFlatPlateCatalogStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: the 2-D
    normal flat plate of half-width a with its exactly zero tangential
    coefficient."""

    def test_flat_plate_normal_coefficient_worked_example(self):
        """Step 2 catalog lookup: the ditching plate of half-width a =
        0.75 m (1.5 m wide) in water carries 1767.145868 kg/m normal,
        the per-unit-span inertia the ditching impact load sees."""
        normal, tangential = am.flat_plate_added_masses(RHO_WATER, 0.75)
        self.assertAlmostEqual(normal, 1767.145868, delta=1e-3)

    def test_flat_plate_tangential_exactly_zero(self):
        """Step 2 catalog lookup: the tangential coefficient of the
        normal flat plate is EXACTLY 0.0, the plate sliding in its own
        plane disturbs no irrotational flow."""
        _, tangential = am.flat_plate_added_masses(RHO_WATER, 0.75)
        self.assertEqual(tangential, 0.0)

    def test_flat_plate_normal_scaling(self):
        """Step 2 catalog lookup: the plate normal coefficient scales
        with a^2 (rho*pi*a^2), reaching 3141.592654 kg/m at a = 1 m."""
        normal, _ = am.flat_plate_added_masses(RHO_WATER, 1.0)
        self.assertAlmostEqual(normal, 3141.592654, delta=1e-3)


class TestEllipticCylinderCatalogStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: the 2-D
    elliptic cylinder, motion along a semi-axis couples to the other
    semi-axis squared."""

    def test_elliptic_cylinder_worked_example(self):
        """Step 2 catalog lookup: the elliptic float section a = 1.0 m,
        b = 0.5 m in water has m_along_a = 785.398163 kg/m (coupling to
        the short semi-axis b) and m_along_b = 3141.592654 kg/m."""
        masses = am.elliptic_cylinder_added_masses(RHO_WATER, 1.0, 0.5)
        self.assertAlmostEqual(masses['m_along_a'], 785.398163, delta=1e-3)
        self.assertAlmostEqual(masses['m_along_b'], 3141.592654, delta=1e-3)

    def test_elliptic_cylinder_circle_limit(self):
        """Step 2 catalog lookup: at a = b = R = 0.5 m both elliptic
        entries equal the cylinder value 785.398163 kg/m with difference
        0.000e+00, the circle limit of the section."""
        masses = am.elliptic_cylinder_added_masses(RHO_WATER, 0.5, 0.5)
        cyl = am.cylinder_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(masses['m_along_a'], cyl, delta=1e-9)
        self.assertAlmostEqual(masses['m_along_b'], cyl, delta=1e-9)

    def test_elliptic_cylinder_plate_limit(self):
        """Step 2 catalog lookup: as b collapses to a thin section the
        elliptic cylinder returns the plate limit (0, rho*pi*a^2)."""
        masses = am.elliptic_cylinder_added_masses(RHO_WATER, 0.75, 1e-9)
        self.assertAlmostEqual(masses['m_along_b'], 1767.145868, delta=1e-3)
        self.assertLess(masses['m_along_a'], 1e-9)


class TestSphereCatalogStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: the 3-D
    sphere at (2/3)*rho*pi*R^3, half its displaced fluid mass."""

    def test_sphere_worked_example(self):
        """Step 2 catalog lookup: the sphere R = 0.5 m in water carries
        261.799388 kg added mass."""
        self.assertAlmostEqual(am.sphere_added_mass(RHO_WATER, 0.5),
                               261.799388, delta=1e-3)

    def test_sphere_half_displaced_mass_identity(self):
        """Step 2 catalog lookup: the sphere added mass over half its
        displaced fluid mass (4/3)*rho*pi*R^3 is 1.000000000 exactly,
        the classical half-mass identity."""
        m_a = am.sphere_added_mass(RHO_WATER, 0.5)
        half_disp = 0.5 * (4.0 / 3.0) * RHO_WATER * math.pi * 0.5 ** 3
        self.assertAlmostEqual(m_a / half_disp, 1.0, delta=1e-9)


class TestProlateCatalogStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: the 3-D
    prolate spheroid axial and transverse added masses through the Lamb
    coefficient reduction."""

    def test_prolate_airship_hull_worked_example(self):
        """Step 2 catalog lookup: the airship hull a = 35 m, b = 7 m in
        air displaces 8800.124621 kg and carries axial m_a =
        520.273672 kg (k = 0.059121, under 6 percent) and transverse m_a
        = 7869.604193 kg (k = 0.894261)."""
        masses = am.prolate_spheroid_added_masses(RHO_AIR, 35.0, 7.0)
        m_disp = (4.0 / 3.0) * RHO_AIR * math.pi * 35.0 * 7.0 * 7.0
        self.assertAlmostEqual(m_disp, 8800.124621, delta=1e-3)
        self.assertAlmostEqual(masses['axial'], 520.273672, delta=1e-2)
        self.assertAlmostEqual(masses['transverse'], 7869.604193, delta=1e-2)
        self.assertAlmostEqual(masses['axial'] / m_disp, 0.059121, delta=1e-5)
        self.assertAlmostEqual(masses['transverse'] / m_disp, 0.894261,
                               delta=1e-5)

    def test_prolate_slender_ratio_ten_ratios(self):
        """Step 2 catalog lookup: at a/b = 10 the k pair 0.020706 axial /
        0.960235 transverse brackets the sphere's 0.5 as the slender-body
        limits predict."""
        masses = am.prolate_spheroid_added_masses(RHO_AIR, 10.0, 1.0)
        m_disp = (4.0 / 3.0) * RHO_AIR * math.pi * 10.0
        self.assertAlmostEqual(masses['axial'] / m_disp, 0.020706, delta=1e-5)
        self.assertAlmostEqual(masses['transverse'] / m_disp, 0.960235,
                               delta=1e-5)
        self.assertLess(masses['axial'] / m_disp, 0.5)
        self.assertGreater(masses['transverse'] / m_disp, 0.5)

    def test_prolate_sphere_branch(self):
        """Step 2 catalog lookup: prolate_spheroid_added_masses(rho, R,
        R) equals sphere_added_mass(rho, R) on both entries with
        difference 0.000e+00, the exact e = 0 branch."""
        masses = am.prolate_spheroid_added_masses(RHO_WATER, 0.5, 0.5)
        sphere = am.sphere_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(masses['axial'], sphere, delta=1e-9)
        self.assertAlmostEqual(masses['transverse'], sphere, delta=1e-9)

    def test_prolate_sphere_limit_continuity(self):
        """Step 2 catalog lookup: alpha0 of the prolate spheroid at a/b =
        1 + 1e-6 is 0.666666133, within 1e-5 of the sphere value 2/3."""
        alpha0, _ = am._prolate_lamb_coefficients(1.0 + 1e-6, 1.0)
        self.assertAlmostEqual(alpha0, 2.0 / 3.0, delta=1e-5)


class TestOblateCatalogStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: the 3-D
    oblate spheroid polar and equatorial added masses through the Lamb
    coefficient reduction."""

    def test_oblate_underwater_housing_worked_example(self):
        """Step 2 catalog lookup: the oblate underwater housing a = 1.0
        m, c = 0.35 m displaces 1466.076572 kg of water yet carries a
        polar m_a = 2422.924052 kg with k = 1.652659 ABOVE unity (the
        flat dome carries more fluid inertia than the fluid it displaces)
        and an equatorial m_a = 340.526959 kg with k = 0.232271."""
        masses = am.oblate_spheroid_added_masses(RHO_WATER, 1.0, 0.35)
        m_disp = (4.0 / 3.0) * RHO_WATER * math.pi * 0.35
        self.assertAlmostEqual(m_disp, 1466.076572, delta=1e-3)
        self.assertAlmostEqual(masses['polar'], 2422.924052, delta=1e-2)
        self.assertAlmostEqual(masses['equatorial'], 340.526959, delta=1e-2)
        k_polar = masses['polar'] / m_disp
        k_eq = masses['equatorial'] / m_disp
        self.assertAlmostEqual(k_polar, 1.652659, delta=1e-5)
        self.assertGreater(k_polar, 1.0)
        self.assertAlmostEqual(k_eq, 0.232271, delta=1e-5)

    def test_oblate_sphere_branch(self):
        """Step 2 catalog lookup: oblate_spheroid_added_masses(rho, R, R)
        equals sphere_added_mass(rho, R) on both entries with difference
        0.000e+00, the exact e = 0 branch."""
        masses = am.oblate_spheroid_added_masses(RHO_WATER, 0.5, 0.5)
        sphere = am.sphere_added_mass(RHO_WATER, 0.5)
        self.assertAlmostEqual(masses['polar'], sphere, delta=1e-9)
        self.assertAlmostEqual(masses['equatorial'], sphere, delta=1e-9)

    def test_oblate_thin_disk_asymptote(self):
        """Step 2 catalog lookup: at c/a = 1e-4 the polar coefficient is
        0.999970 of the classical thin-disk (8/3)*rho*a^3 value and gamma0
        = 1.999685881 approaches 2, while the equatorial coefficient
        vanishes with the thickness."""
        masses = am.oblate_spheroid_added_masses(RHO_WATER, 1.0, 1e-4)
        disk_value = (8.0 / 3.0) * RHO_WATER
        ratio = masses['polar'] / disk_value
        self.assertAlmostEqual(ratio, 0.999970, delta=1e-5)
        self.assertAlmostEqual(masses['polar'], disk_value, delta=1e-1)
        gamma0, alpha0 = am._oblate_lamb_coefficients(1.0, 1e-4)
        self.assertAlmostEqual(gamma0, 1.999685881, delta=1e-6)
        self.assertLess(masses['equatorial'], 1e-2)

    def test_oblate_sphere_limit_continuity(self):
        """Step 2 catalog lookup: gamma0 of the oblate spheroid at a/c =
        1 + 1e-6 is 0.666667200, within 1e-5 of the sphere value 2/3."""
        gamma0, _ = am._oblate_lamb_coefficients(1.0 + 1e-6, 1.0)
        self.assertAlmostEqual(gamma0, 2.0 / 3.0, delta=1e-5)


class TestLambIntegralReductionStep2(unittest.TestCase):
    """SKILL.md workflow step 2, the catalog coefficient lookup: every
    closed-form Lamb coefficient agrees with the independently
    quadrature-pinned rows of the spec and obeys its sum rule."""

    def test_lamb_prolate_table_and_sum_rule(self):
        """Step 2 catalog lookup: the closed-form prolate alpha0/beta0
        match the quadrature rows 0.347127995/0.826436002 (a/b = 2),
        0.111641940/0.944179030 (a/b = 5) and 0.040571761/0.979714120
        (a/b = 10) within 1e-9, and alpha0 + 2*beta0 = 2.000000000."""
        expected = {2.0: (0.347127995, 0.826436002),
                    5.0: (0.111641940, 0.944179030),
                    10.0: (0.040571761, 0.979714120)}
        for ratio, (alpha_pin, beta_pin) in expected.items():
            alpha0, beta0 = am._prolate_lamb_coefficients(ratio, 1.0)
            self.assertAlmostEqual(alpha0, alpha_pin, delta=1e-9)
            self.assertAlmostEqual(beta0, beta_pin, delta=1e-9)
            self.assertAlmostEqual(alpha0 + 2.0 * beta0, 2.0, delta=1e-9)

    def test_lamb_oblate_table_and_sum_rule(self):
        """Step 2 catalog lookup: the closed-form oblate gamma0/alpha0
        match the quadrature rows 1.054400565/0.472799717 (a/c = 2),
        1.500967825/0.249516088 (a/c = 5) and 1.721608553/0.139195723
        (a/c = 10) within 1e-9, and gamma0 + 2*alpha0 = 2.000000000."""
        expected = {2.0: (1.054400565, 0.472799717),
                    5.0: (1.500967825, 0.249516088),
                    10.0: (1.721608553, 0.139195723)}
        for ratio, (gamma_pin, alpha_pin) in expected.items():
            gamma0, alpha0 = am._oblate_lamb_coefficients(ratio, 1.0)
            self.assertAlmostEqual(gamma0, gamma_pin, delta=1e-9)
            self.assertAlmostEqual(alpha0, alpha_pin, delta=1e-9)
            self.assertAlmostEqual(gamma0 + 2.0 * alpha0, 2.0, delta=1e-9)


class TestValueErrorRejectionStep6(unittest.TestCase):
    """SKILL.md workflow step 6, the deterministic offline check: every
    non-physical input is rejected with ValueError."""

    def test_value_errors_shape_functions(self):
        """Step 6 offline check: rho 0 and negative rho raise on every
        shape catalog function; R 0 on the cylinder and sphere; a 0 on
        the flat plate; b 0 on the elliptic cylinder; b 0 and b > a on
        the prolate spheroid; c 0 and c > a on the oblate spheroid."""
        shape_fns = [
            (am.cylinder_added_mass, (1.0,)),
            (am.sphere_added_mass, (1.0,)),
            (am.flat_plate_added_masses, (1.0,)),
            (am.elliptic_cylinder_added_masses, (1.0, 0.5)),
            (am.prolate_spheroid_added_masses, (1.0, 0.5)),
            (am.oblate_spheroid_added_masses, (1.0, 0.35)),
        ]
        for fn, args in shape_fns:
            with self.subTest(fn=fn.__name__, rho=0):
                self.assertRaises(ValueError, fn, 0.0, *args)
            with self.subTest(fn=fn.__name__, rho_neg=-1.0):
                self.assertRaises(ValueError, fn, -1.0, *args)
        self.assertRaises(ValueError, am.cylinder_added_mass, RHO_WATER, 0.0)
        self.assertRaises(ValueError, am.sphere_added_mass, RHO_WATER, 0.0)
        self.assertRaises(ValueError, am.flat_plate_added_masses,
                          RHO_WATER, 0.0)
        self.assertRaises(ValueError, am.elliptic_cylinder_added_masses,
                          RHO_WATER, 1.0, 0.0)
        self.assertRaises(ValueError, am.prolate_spheroid_added_masses,
                          RHO_WATER, 1.0, 0.0)
        self.assertRaises(ValueError, am.prolate_spheroid_added_masses,
                          RHO_WATER, 1.0, 2.0)
        self.assertRaises(ValueError, am.oblate_spheroid_added_masses,
                          RHO_WATER, 1.0, 0.0)
        self.assertRaises(ValueError, am.oblate_spheroid_added_masses,
                          RHO_WATER, 1.0, 2.0)

    def test_value_errors_negative_axes(self):
        """Step 6 offline check: negative axes and a negative half-width
        raise on the shape catalog functions."""
        self.assertRaises(ValueError, am.cylinder_added_mass, RHO_WATER, -0.5)
        self.assertRaises(ValueError, am.sphere_added_mass, RHO_WATER, -0.5)
        self.assertRaises(ValueError, am.flat_plate_added_masses,
                          RHO_WATER, -0.5)
        self.assertRaises(ValueError, am.elliptic_cylinder_added_masses,
                          RHO_WATER, -1.0, 0.5)
        self.assertRaises(ValueError, am.prolate_spheroid_added_masses,
                          RHO_WATER, -1.0, 0.5)
        self.assertRaises(ValueError, am.oblate_spheroid_added_masses,
                          RHO_WATER, -1.0, 0.35)

    def test_value_errors_energy_relations(self):
        """Step 6 offline check: kinetic_energy_of_translation raises at
        m_added 0 and at speed -1, acceleration_reaction_force at m_added
        0, virtual_mass and added_mass_fraction at m_body 0 and at m_added
        0, the guard rails of the energy picture and the inertia model."""
        self.assertRaises(ValueError, am.kinetic_energy_of_translation,
                          0.0, 4.0)
        self.assertRaises(ValueError, am.kinetic_energy_of_translation,
                          100.0, -1.0)
        self.assertRaises(ValueError, am.acceleration_reaction_force,
                          0.0, 4.0)
        self.assertRaises(ValueError, am.virtual_mass, 0.0, 100.0)
        self.assertRaises(ValueError, am.virtual_mass, 200.0, 0.0)
        self.assertRaises(ValueError, am.added_mass_fraction, 100.0, 0.0)
        self.assertRaises(ValueError, am.added_mass_fraction, 0.0, 200.0)


class TestDeterminismStep6(unittest.TestCase):
    """SKILL.md workflow step 6, the deterministic offline check: no RNG,
    repeat runs reproduce bit-identical catalog values."""

    def test_repeat_runs_identical(self):
        """Step 6 offline check: rerunning the full catalog at the worked
        example points reproduces the coefficients exactly, so the module
        is deterministic."""
        first = am.prolate_spheroid_added_masses(RHO_AIR, 35.0, 7.0)
        second = am.prolate_spheroid_added_masses(RHO_AIR, 35.0, 7.0)
        self.assertEqual(first['axial'], second['axial'])
        self.assertEqual(first['transverse'], second['transverse'])
        self.assertEqual(am.oblate_spheroid_added_masses(RHO_WATER, 1.0,
                                                         0.35),
                         am.oblate_spheroid_added_masses(RHO_WATER, 1.0,
                                                         0.35))


if __name__ == '__main__':
    unittest.main()
