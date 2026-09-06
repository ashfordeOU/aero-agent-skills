"""Contract test for the shrink-fit-analysis leaf (structures/fem).

Exercises the SKILL.md workflow end to end. Step 1 of the SKILL.md
workflow, fixing the assembly geometry, materials and the total radial
interference, is exercised by the module constants used throughout. Step
2, converting the radial interference into the interface contact
pressure with the contact_pressure Lame radial-compliance pass, is
exercised by the TestContactPressure methods. Step 3, recovering the
critical bore stress state with the stress_distributions bore-stress
pass, is exercised by TestStressDistributions. Step 4, forming the
von-Mises yield margins of both bores with the von_mises_margin
yield-margin pass, is exercised by TestVonMisesMargin. Step 5, closing
with the governing member and the allowable radial interference via the
allowable_interference governing-member pass, is exercised by
TestAllowableInterference. Step 6, verifying the closed-form identities
(compatibility delta = u_outer - u_inner at the returned contact
pressure and linear p-delta scaling), is exercised by the identity
methods in every class. Step 7, confirming the deterministic offline
contract test run, is this module itself.

All numeric asserts are order-safe: assertAlmostEqual with an explicit
delta or math.isclose, never exact float equality on computed sums.
Exact equality is used only for literal constants (the free-surface
inner bore sigma_r of 0.0, fixed dict keys, fixed governing-member
strings) and the bit-identical determinism pair, which is exact by
construction. Worked-example magnitudes come from the wave-42 prep
anchor: contact pressure 56.91381 MPa, inner bore hoop -260.17743 MPa,
outer bore hoop 94.85635 MPa, allowable interference 0.04157 mm,
governing member outer.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shrink_fit_analysis_logic import (
    allowable_interference,
    contact_pressure,
    stress_distributions,
    von_mises_margin,
)

# Worked-example geometry (mm) and materials (MPa): steel bushing in an
# aluminum lug, corpus geometry from the wave-42 spec.
R_I = 6.0
R_C = 8.0
R_O = 16.0
E_I = 207000.0
NU_I = 0.30
E_O = 71000.0
NU_O = 0.33
SY_I = 620.0
SY_O = 276.0
DELTA = 0.02

# Prep-verified anchors (real module outputs at full precision).
P_ANCHOR = 56.913811912628034
INNER_THETA_ANCHOR = -260.1774258862996
OUTER_SIGMA_R_ANCHOR = -56.913811912628034
OUTER_THETA_ANCHOR = 94.8563531877134


def _u_inner(p, r_i, r_c, e_i, nu_i):
    """Inward interface displacement of the compressed inner member."""
    return -(p * r_c / e_i) * (
        (r_c ** 2 + r_i ** 2) / (r_c ** 2 - r_i ** 2) - nu_i
    )


def _u_outer(p, r_i, r_c, r_o, e_o, nu_o):
    """Outward bore displacement of the expanded outer member."""
    return +(p * r_c / e_o) * (
        (r_o ** 2 + r_c ** 2) / (r_o ** 2 - r_c ** 2) + nu_o
    )


def _interface_hoop_inner(p, r_i, r_c):
    """Interface hoop of the inner member at r_c (not the critical plane)."""
    return -p * (r_c ** 2 + r_i ** 2) / (r_c ** 2 - r_i ** 2)


class TestContactPressure(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the contact_pressure Lame radial
    compliance pass that converts the radial interference into the
    interference-fit contact pressure."""

    def test_worked_example_contact_pressure_anchor(self):
        """Step 2 on the worked geometry: contact_pressure(0.02, 6.0,
        8.0, 16.0, 207000.0, 0.30, 71000.0, 0.33) returns the anchor
        interference-fit contact pressure 56.91381 MPa within 1e-4."""
        p = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        self.assertAlmostEqual(p, P_ANCHOR, delta=1e-4)
        self.assertAlmostEqual(p, 56.91381, delta=1e-4)

    def test_contact_pressure_sanity_band(self):
        """Step 2 sanity band from the spec: the 0.02 mm radial
        interference over 6 to 16 mm radii in steel on aluminum holds
        the contact pressure inside 50 to 150 MPa."""
        p = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        self.assertGreaterEqual(p, 50.0)
        self.assertLessEqual(p, 150.0)

    def test_contact_pressure_linear_in_delta(self):
        """Step 6 identity, linear p-delta scaling at fixed geometry and
        materials: doubling the radial interference doubles the contact
        pressure and halving it halves the pressure, so p/delta is
        constant across the interference range."""
        base = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        doubled = contact_pressure(2.0 * DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        halved = contact_pressure(0.5 * DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        self.assertTrue(math.isclose(doubled, 2.0 * base, rel_tol=1e-12))
        self.assertTrue(math.isclose(halved, 0.5 * base, rel_tol=1e-12))
        for d in (0.005, 0.01, 0.04, 0.08):
            ratio = contact_pressure(d, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O) / d
            self.assertTrue(math.isclose(ratio, base / DELTA, rel_tol=1e-9))

    def test_sign_convention_swapped_nu_variant(self):
        """Step 2 sign-convention guard: the derived compliance carries
        -nu_i on the compressed bushing and +nu_o on the expanded lug; a
        swapped-sign variant over-reads the contact pressure to about
        66.6 MPa, a 17 percent over-read."""
        p = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        inner_c = (R_C / E_I) * (
            (R_C ** 2 + R_I ** 2) / (R_C ** 2 - R_I ** 2) + NU_I
        )
        outer_c = (R_C / E_O) * (
            (R_O ** 2 + R_C ** 2) / (R_O ** 2 - R_C ** 2) - NU_O
        )
        p_swapped = DELTA / (inner_c + outer_c)
        self.assertTrue(math.isclose(p_swapped, 66.615427, rel_tol=1e-3))
        self.assertGreater(p_swapped, 1.15 * p)

    def test_valueerror_nonpositive_delta(self):
        """Step 2 rejection: contact_pressure raises ValueError for a
        radial interference delta of zero or negative."""
        for d in (0.0, -1e-3, -0.02):
            with self.assertRaises(ValueError):
                contact_pressure(d, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)

    def test_valueerror_nonpositive_inner_bore(self):
        """Step 2 rejection: a zero or negative inner bore r_i raises
        ValueError from contact_pressure."""
        for ri in (0.0, -2.0):
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, ri, R_C, R_O, E_I, NU_I, E_O, NU_O)

    def test_valueerror_interface_radius_bounds(self):
        """Step 2 rejection: an interface radius r_c at or below the
        bore r_i raises ValueError from contact_pressure."""
        for rc in (R_I, R_I - 1.0):
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, R_I, rc, R_O, E_I, NU_I, E_O, NU_O)

    def test_valueerror_outer_radius_bounds(self):
        """Step 2 rejection: an outer radius r_o at or below the
        interface radius r_c raises ValueError from contact_pressure."""
        for ro in (R_C, R_C - 1.0):
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, R_I, R_C, ro, E_I, NU_I, E_O, NU_O)

    def test_valueerror_nonpositive_moduli(self):
        """Step 2 rejection: zero or negative member moduli raise
        ValueError from contact_pressure."""
        for e_i in (0.0, -1.0):
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, R_I, R_C, R_O, e_i, NU_I, E_O, NU_O)
        for e_o in (0.0, -1.0):
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, e_o, NU_O)

    def test_valueerror_poisson_out_of_range(self):
        """Step 2 rejection: any Poisson ratio outside (0, 0.5), at the
        0, 0.5 and 0.6 stations, raises ValueError from
        contact_pressure."""
        for nu in (0.0, 0.5, 0.6):
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, R_I, R_C, R_O, E_I, nu, E_O, NU_O)
            with self.assertRaises(ValueError):
                contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, nu)


class TestStressDistributions(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the stress_distributions
    bore-stress pass that recovers the bore radial and hoop stresses of
    both members at the interface contact pressure."""

    def test_worked_example_bore_stress_anchor(self):
        """Step 3 on the worked geometry at p = 56.91381 MPa: the inner
        member bore hoop is -260.17743 MPa (compression), the outer
        member bore carries sigma_r = -56.91381 MPa and the maximum
        tensile hoop +94.85635 MPa, all within 1e-4."""
        s = stress_distributions(P_ANCHOR, R_I, R_C, R_O)
        self.assertAlmostEqual(
            s["inner_bore_sigma_theta"], INNER_THETA_ANCHOR, delta=1e-4
        )
        self.assertAlmostEqual(
            s["outer_bore_sigma_r"], OUTER_SIGMA_R_ANCHOR, delta=1e-4
        )
        self.assertAlmostEqual(
            s["outer_bore_sigma_theta"], OUTER_THETA_ANCHOR, delta=1e-4
        )

    def test_stress_distributions_exact_keys(self):
        """Step 3 output contract: stress_distributions returns exactly
        the four documented bore-stress dict keys."""
        s = stress_distributions(P_ANCHOR, R_I, R_C, R_O)
        self.assertEqual(
            set(s.keys()),
            {
                "inner_bore_sigma_r",
                "inner_bore_sigma_theta",
                "outer_bore_sigma_r",
                "outer_bore_sigma_theta",
            },
        )

    def test_inner_bore_free_surface_sigma_r_zero(self):
        """Step 3 result: the inner member bore is a free surface, so
        its radial stress is the literal 0.0."""
        s = stress_distributions(P_ANCHOR, R_I, R_C, R_O)
        self.assertEqual(s["inner_bore_sigma_r"], 0.0)

    def test_inner_bore_hoop_most_compressive_in_assembly(self):
        """Step 3 result: the compressed inner member bore hoop is
        negative and is the largest hoop magnitude in the assembly,
        exceeding the inner member interface hoop at r_c and the outer
        member bore hoop."""
        s = stress_distributions(P_ANCHOR, R_I, R_C, R_O)
        inner_theta = s["inner_bore_sigma_theta"]
        self.assertLess(inner_theta, 0.0)
        interface_hoop = _interface_hoop_inner(P_ANCHOR, R_I, R_C)
        self.assertGreater(abs(inner_theta), abs(interface_hoop))
        self.assertGreater(abs(inner_theta), abs(s["outer_bore_sigma_theta"]))

    def test_outer_bore_sigma_r_minus_p_continuity(self):
        """Step 3 result: sigma_r is continuous across the interface at
        -p, so the outer member bore radial stress equals minus the
        interface contact pressure."""
        s = stress_distributions(P_ANCHOR, R_I, R_C, R_O)
        self.assertAlmostEqual(s["outer_bore_sigma_r"], -P_ANCHOR, delta=1e-12)

    def test_stress_linear_in_p(self):
        """Step 6 identity, elastic linearity: doubling the interface
        contact pressure doubles every bore stress at fixed geometry."""
        s1 = stress_distributions(P_ANCHOR, R_I, R_C, R_O)
        s2 = stress_distributions(2.0 * P_ANCHOR, R_I, R_C, R_O)
        for key in s1:
            self.assertTrue(math.isclose(s2[key], 2.0 * s1[key], rel_tol=1e-12))

    def test_valueerror_nonpositive_p(self):
        """Step 3 rejection: a contact pressure p of zero or negative
        raises ValueError from stress_distributions."""
        for p in (0.0, -10.0):
            with self.assertRaises(ValueError):
                stress_distributions(p, R_I, R_C, R_O)

    def test_valueerror_degenerate_radii(self):
        """Step 3 rejection: radii violating 0 < r_i < r_c < r_o raise
        ValueError from stress_distributions."""
        for bad in ((0.0, R_C, R_O), (R_I, R_I, R_O), (R_I, R_C, R_C)):
            with self.assertRaises(ValueError):
                stress_distributions(P_ANCHOR, *bad)


class TestVonMisesMargin(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the von_mises_margin yield-margin
    pass that forms the von-Mises yield margin of each bore against its
    yield strength."""

    def test_worked_example_inner_bore_margin(self):
        """Step 4 on the steel bushing bore: von_mises_margin(620.0,
        0.0, -260.17743) returns sigma_vm 260.17743 MPa and margin
        359.82257 MPa within 1e-3."""
        vm = von_mises_margin(SY_I, 0.0, -260.17743)
        self.assertAlmostEqual(vm["sigma_vm"], 260.17743, delta=1e-3)
        self.assertAlmostEqual(vm["margin"], 359.82257, delta=1e-3)

    def test_worked_example_outer_bore_margin(self):
        """Step 4 on the aluminum lug bore: von_mises_margin(276.0,
        -56.91381, 94.85635) returns sigma_vm 132.79889 MPa and margin
        143.20111 MPa within 1e-3."""
        vm = von_mises_margin(SY_O, -56.91381, 94.85635)
        self.assertAlmostEqual(vm["sigma_vm"], 132.79889, delta=1e-3)
        self.assertAlmostEqual(vm["margin"], 143.20111, delta=1e-3)

    def test_uniaxial_identity_sigma_r_zero(self):
        """Step 4 uniaxial identity: with sigma_r = 0 the von-Mises
        equivalent equals the absolute value of the hoop stress for both
        tension and compression."""
        for theta in (120.0, -120.0):
            vm = von_mises_margin(SY_I, 0.0, theta)
            self.assertAlmostEqual(vm["sigma_vm"], abs(theta), delta=1e-9)

    def test_equibiaxial_identity(self):
        """Step 4 equibiaxial identity: with sigma_r equal to
        sigma_theta the von-Mises equivalent equals that stress
        magnitude."""
        vm = von_mises_margin(SY_I, 100.0, 100.0)
        self.assertAlmostEqual(vm["sigma_vm"], 100.0, delta=1e-9)

    def test_zero_stress_margin_equals_yield_strength(self):
        """Step 4 zero-stress limit: an unstressed bore returns a
        von-Mises equivalent of 0 and a margin equal to the yield
        strength."""
        vm = von_mises_margin(SY_O, 0.0, 0.0)
        self.assertAlmostEqual(vm["sigma_vm"], 0.0, delta=1e-12)
        self.assertAlmostEqual(vm["margin"], SY_O, delta=1e-9)

    def test_valueerror_nonpositive_yield_strength(self):
        """Step 4 rejection: a yield strength sy of zero or negative
        raises ValueError from von_mises_margin."""
        for sy in (0.0, -1.0):
            with self.assertRaises(ValueError):
                von_mises_margin(sy, 0.0, 100.0)


class TestAllowableInterference(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the allowable_interference
    governing-member pass that closes with the governing member and the
    allowable radial interference before that bore yields."""

    def test_worked_example_governing_outer_anchor(self):
        """Step 5 on the worked geometry: the aluminum lug bore governs,
        with governing_member \"outer\", governing contact pressure
        118.28571 MPa within 1e-3 and allowable interference 0.04157 mm
        within 1e-5."""
        a = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
        )
        self.assertEqual(a["governing_member"], "outer")
        self.assertAlmostEqual(a["governing_contact_pressure"], 118.28571, delta=1e-3)
        self.assertAlmostEqual(a["allowable_interference"], 0.04157, delta=1e-5)

    def test_identical_members_governing_inner(self):
        """Step 5 governing flip: with identical members (E_i = E_o,
        nu_i = nu_o, sy_i = sy_o = 620.0) the governing member flips
        from outer to inner, because the inner bore hoop factor
        2*r_c**2/(r_c**2 - r_i**2) = 4.5714 exceeds the outer bore
        von-Mises factor sqrt(1.6667**2 + 1.6667 + 1) = 2.3333."""
        a = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_I, NU_I, 620.0, 620.0
        )
        self.assertEqual(a["governing_member"], "inner")

    def test_yield_crossing_identity(self):
        """Step 5 yield-crossing identity: at a radial interference
        equal to the returned allowable interference the governing bore
        margin returns 0 within 1e-9."""
        a = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
        )
        p_allow = contact_pressure(
            a["allowable_interference"], R_I, R_C, R_O, E_I, NU_I, E_O, NU_O
        )
        s = stress_distributions(p_allow, R_I, R_C, R_O)
        if a["governing_member"] == "outer":
            vm = von_mises_margin(
                SY_O, s["outer_bore_sigma_r"], s["outer_bore_sigma_theta"]
            )
        else:
            vm = von_mises_margin(
                SY_I, s["inner_bore_sigma_r"], s["inner_bore_sigma_theta"]
            )
        self.assertAlmostEqual(vm["margin"], 0.0, delta=1e-9)

    def test_governing_pressure_linear_scale_crosscheck(self):
        """Step 5 linear-scaling cross-check: the governing contact
        pressure equals the design contact pressure times
        sy_gov/sigma_vm_gov of the governing bore within 1e-9
        relative."""
        a = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
        )
        p = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        s = stress_distributions(p, R_I, R_C, R_O)
        if a["governing_member"] == "outer":
            vm_gov = von_mises_margin(
                SY_O, s["outer_bore_sigma_r"], s["outer_bore_sigma_theta"]
            )["sigma_vm"]
            sy_gov = SY_O
        else:
            vm_gov = von_mises_margin(
                SY_I, s["inner_bore_sigma_r"], s["inner_bore_sigma_theta"]
            )["sigma_vm"]
            sy_gov = SY_I
        self.assertTrue(
            math.isclose(
                a["governing_contact_pressure"],
                p * sy_gov / vm_gov,
                rel_tol=1e-9,
            )
        )

    def test_valueerror_nonpositive_yield_strengths(self):
        """Step 5 rejection: a non-positive inner or outer yield
        strength raises ValueError from allowable_interference."""
        with self.assertRaises(ValueError):
            allowable_interference(
                DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, 0.0, SY_O
            )
        with self.assertRaises(ValueError):
            allowable_interference(
                DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, -1.0
            )

    def test_valueerror_geometry_forwarded(self):
        """Step 5 rejection forwarding: the contact_pressure geometry
        and material checks apply unchanged through
        allowable_interference."""
        with self.assertRaises(ValueError):
            allowable_interference(
                0.0, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
            )
        with self.assertRaises(ValueError):
            allowable_interference(
                DELTA, R_I, R_C, R_O, E_I, 0.5, E_O, NU_O, SY_I, SY_O
            )


class TestIdentitiesAndDeterminism(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the closed-form identity checks
    (compatibility delta = u_outer - u_inner and the fixed governing
    strings), and step 7, the deterministic offline contract run."""

    def test_compatibility_identity_u_outer_minus_u_inner(self):
        """Step 6 compatibility identity: u_outer - u_inner, evaluated
        from the Lame displacement closed forms at the returned contact
        pressure, reproduces the input radial interference delta within
        1e-12."""
        p = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        u_outer = _u_outer(p, R_I, R_C, R_O, E_O, NU_O)
        u_inner = _u_inner(p, R_I, R_C, E_I, NU_I)
        self.assertAlmostEqual(u_outer - u_inner, DELTA, delta=1e-12)
        # u_outer is outward positive and u_inner inward negative.
        self.assertGreater(u_outer, 0.0)
        self.assertLess(u_inner, 0.0)

    def test_governing_member_fixed_strings(self):
        """Step 5 output contract: governing_member is always exactly
        the fixed string \"inner\" or \"outer\"."""
        a = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
        )
        self.assertIn(a["governing_member"], ("inner", "outer"))
        b = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_I, NU_I, 620.0, 620.0
        )
        self.assertIn(b["governing_member"], ("inner", "outer"))

    def test_determinism_bit_identical(self):
        """Step 7 determinism: two runs of the identical closed-form
        computation return bit-identical values (exact by
        construction)."""
        p1 = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        p2 = contact_pressure(DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O)
        self.assertEqual(p1, p2)
        a1 = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
        )
        a2 = allowable_interference(
            DELTA, R_I, R_C, R_O, E_I, NU_I, E_O, NU_O, SY_I, SY_O
        )
        self.assertEqual(a1, a2)


if __name__ == "__main__":
    unittest.main()
