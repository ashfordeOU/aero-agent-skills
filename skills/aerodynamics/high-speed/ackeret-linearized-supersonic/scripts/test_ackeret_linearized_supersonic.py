"""Contract test for aerodynamics/high-speed/ackeret-linearized-supersonic.

Deterministic stdlib unittest for the ackeret linearized supersonic
thin-airfoil leaf: the ackeret parameter traverse, the ackeret surface
pressure law evaluation and pressure reconstruction, the section lift
and supersonic lift curve slope computation, the flat plate reference
set, the biconvex and cambered plate wave drag sizing from the closed
forms, the general section_coefficients Simpson quadrature of the
linearized pressure integral over the surface slopes, the leading edge
moment coefficients, and the ValueError rejection of non-physical
mach, thickness, camber, chord, panel count and gamma inputs. Every
numeric assertion is order-safe/tolerant (delta or isclose); no exact
float equality on computed sums. Step names below mirror the numbered
SKILL.md Workflow section, so the record sampler can tie each test to
the workflow step it exercises. Run: python3
scripts/test_ackeret_linearized_supersonic.py, offline, under 20 s.
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ackeret_linearized_supersonic_logic as al

ALPHA = math.radians(3.0)   # 0.05235987755982989 rad
TAU = 0.06                  # biconvex thickness ratio
CAMBER = 0.02               # cambered plate h/c
M2 = 2.0


def biconvex_u(x, tau=TAU):
    """Upper-surface slope phi_u = 2*tau*(1 - 2*x/c) over chord 1."""
    return 2.0 * tau * (1.0 - 2.0 * x)


def biconvex_l(x, tau=TAU):
    """Lower-surface slope phi_l = -phi_u of the symmetric section."""
    return -biconvex_u(x, tau)


def cambered_u(x, camber=CAMBER):
    """Circular-arc mean line slope phi = 4*(h/c)*(1 - 2*x/c), upper."""
    return 4.0 * camber * (1.0 - 2.0 * x)


def cambered_l(x, camber=CAMBER):
    """Circular-arc mean line slope, lower surface (same mean line)."""
    return cambered_u(x, camber)


def flat_u(x):
    return 0.0


def flat_l(x):
    return 0.0


class TestAckeretParameter(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the ackeret parameter traverse
    beta = sqrt(M^2 - 1) that fixes the supersonic flight condition."""

    def test_ackeret_parameter_table(self):
        # Worked-example values at M = 1.5, 2.0, 3.0 and sqrt(2).
        self.assertAlmostEqual(al.ackeret_parameter(1.5), 1.118033988750, delta=1e-6)
        self.assertAlmostEqual(al.ackeret_parameter(2.0), 1.732050807569, delta=1e-6)
        self.assertAlmostEqual(al.ackeret_parameter(3.0), 2.828427124746, delta=1e-6)
        self.assertAlmostEqual(al.ackeret_parameter(math.sqrt(2.0)), 1.0, delta=1e-12)

    def test_ackeret_parameter_rejects_mach_at_or_below_one(self):
        # The linear coefficients diverge as M -> 1: the traverse must
        # refuse mach 1.0, 0.9, -2.0 and non-finite mach.
        for bad in (1.0, 0.9, -2.0, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                al.ackeret_parameter(bad)


class TestPressureLaw(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the ackeret surface pressure law
    evaluation Cp = +-2*theta/beta for a deflection theta and the
    surface pressure reconstruction p/p_inf = 1 + (gamma/2) M^2 Cp."""

    def test_cp_linear_table_at_mach2(self):
        # Worked-example Cp values at M = 2 for +-0.05 rad and +-2 deg.
        self.assertAlmostEqual(al.cp_linear(0.05, 2.0), 0.057735026919, delta=1e-8)
        self.assertAlmostEqual(al.cp_linear(-0.05, 2.0), -0.057735026919, delta=1e-8)
        two_deg = math.radians(2.0)
        self.assertAlmostEqual(al.cp_linear(two_deg, 2.0), 0.040306652539, delta=1e-8)
        self.assertAlmostEqual(al.cp_linear(-two_deg, 2.0), -0.040306652539, delta=1e-8)

    def test_cp_linear_antisymmetry(self):
        # The linear law is odd in theta: cp(-theta) = -cp(theta) exactly.
        for theta in (0.05, math.radians(2.0), 0.1, math.radians(-4.0)):
            self.assertEqual(al.cp_linear(-theta, 2.0), -al.cp_linear(theta, 2.0))

    def test_cp_linear_rejects_mach(self):
        for bad in (1.0, 0.9):
            with self.assertRaises(ValueError):
                al.cp_linear(0.05, bad)

    def test_surface_pressure_ratio_worked(self):
        # Flat-plate lower surface at alpha = 3 deg, M = 2, gamma 1.4:
        # cp_l = 0.060459978808 reconstructs p/p_inf = 1.169287940662.
        self.assertAlmostEqual(
            al.surface_pressure_ratio(0.060459978808, 2.0), 1.169287940662, delta=1e-9)
        self.assertAlmostEqual(
            al.surface_pressure_ratio(-0.060459978808, 2.0), 0.830712059338, delta=1e-9)

    def test_surface_pressure_ratio_honors_gamma(self):
        # gamma enters only here: at gamma 1.4 against 1.1 the ratio grows.
        self.assertAlmostEqual(
            al.surface_pressure_ratio(0.05, 2.0, gamma=1.1),
            1.0 + 0.5 * 1.1 * 4.0 * 0.05, delta=1e-12)

    def test_surface_pressure_ratio_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            al.surface_pressure_ratio(0.1, 1.0)
        with self.assertRaises(ValueError):
            al.surface_pressure_ratio(0.1, 2.0, gamma=1.0)
        with self.assertRaises(ValueError):
            al.surface_pressure_ratio(0.1, 2.0, gamma=0.95)


class TestLift(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the section lift computation
    cl = 4*alpha/beta of the thin closed section and the supersonic
    lift curve slope 4/beta per radian."""

    def test_lift_coefficient_worked(self):
        # alpha = 3 deg at M = 2: cl = 0.120919957616, the linear value
        # the exact-march sibling quotes as its cross-check. The 1/beta =
        # 0.577350269190 read-off: cl = 4*alpha*1/beta, and cl at M =
        # sqrt(2) doubles to 4*alpha because beta = 1 there.
        self.assertAlmostEqual(al.lift_coefficient(ALPHA, 2.0), 0.120919957616, delta=1e-6)
        self.assertAlmostEqual(
            al.lift_coefficient(ALPHA, math.sqrt(2.0)), 4.0 * ALPHA, delta=1e-12)

    def test_lift_curve_slope_table(self):
        # Supersonic lift-curve slope 4/beta per radian: 2.309401076759 at
        # M = 2, 1.414213562373 at M = 3, 4.0 at M = sqrt(2) (beta = 1).
        self.assertAlmostEqual(al.lift_curve_slope(2.0), 2.309401076759, delta=1e-6)
        self.assertAlmostEqual(al.lift_curve_slope(3.0), 1.414213562373, delta=1e-6)
        self.assertAlmostEqual(al.lift_curve_slope(math.sqrt(2.0)), 4.0, delta=1e-12)

    def test_lift_functions_reject_bad_mach(self):
        for bad in (1.0, 0.9, float("nan")):
            with self.assertRaises(ValueError):
                al.lift_coefficient(ALPHA, bad)
            with self.assertRaises(ValueError):
                al.lift_curve_slope(bad)


class TestFlatPlate(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the flat plate reference set:
    cl = 4a/b, cd_wave = 4a^2/b, cm_le = -2a/b and the mid-chord center
    of pressure x_cp/c = 0.5."""

    def test_flat_plate_worked(self):
        res = al.flat_plate(ALPHA, 2.0)
        self.assertAlmostEqual(res["cl"], 0.120919957616, delta=1e-6)
        self.assertAlmostEqual(res["cd_wave"], 0.006331354175, delta=1e-6)
        self.assertAlmostEqual(res["cm_le"], -0.060459978808, delta=1e-6)
        self.assertAlmostEqual(res["x_cp_over_c"], 0.5, delta=1e-12)

    def test_flat_plate_cd_wave_is_alpha_times_cl(self):
        # cd = alpha*cl at linear order, exact to float noise.
        res = al.flat_plate(ALPHA, 2.0)
        self.assertAlmostEqual(res["cd_wave"], ALPHA * res["cl"], delta=1e-12)

    def test_flat_plate_center_of_pressure(self):
        # x_cp/c = -cm_le/cl = 0.5, the supersonic linear position.
        res = al.flat_plate(ALPHA, 2.0)
        self.assertAlmostEqual(-res["cm_le"] / res["cl"], 0.5, delta=1e-12)

    def test_flat_plate_rejects_bad_mach(self):
        with self.assertRaises(ValueError):
            al.flat_plate(ALPHA, 1.0)
        with self.assertRaises(ValueError):
            al.flat_plate(ALPHA, float("inf"))


class TestBiconvex(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the biconvex section wave drag
    sizing cd_wave = (4a^2 + (16/3) tau^2)/beta with the thickness drag
    additive on the flat-plate alpha drag and cm_le = -2a/b."""

    def test_biconvex_worked(self):
        res = al.biconvex_section(ALPHA, TAU, 2.0)
        self.assertAlmostEqual(res["cl"], 0.120919957616, delta=1e-6)
        self.assertAlmostEqual(res["cd_wave"], 0.017416479344, delta=1e-6)
        self.assertAlmostEqual(res["cm_le"], -0.060459978808, delta=1e-6)

    def test_biconvex_drag_additive(self):
        # cd(3 deg) = flat cd + (16/3) tau^2/beta = 0.006331354175 +
        # 0.011085125168, the thickness wave drag on top of the alpha drag.
        res = al.biconvex_section(ALPHA, TAU, 2.0)
        flat = al.flat_plate(ALPHA, 2.0)
        thickness = (16.0 / 3.0) * TAU * TAU / al.ackeret_parameter(2.0)
        self.assertAlmostEqual(res["cd_wave"], flat["cd_wave"] + thickness, delta=1e-12)
        self.assertAlmostEqual(res["cd_wave"], 0.017416479344, delta=1e-6)

    def test_biconvex_zero_lift(self):
        # Symmetric section at alpha 0: cl = 0, cm_le = 0, cd_wave stays
        # positive at the classic zero-lift wave drag 0.011085125168.
        res = al.biconvex_section(0.0, TAU, 2.0)
        self.assertAlmostEqual(res["cl"], 0.0, delta=1e-12)
        self.assertAlmostEqual(res["cm_le"], 0.0, delta=1e-12)
        self.assertAlmostEqual(res["cd_wave"], 0.011085125168, delta=1e-6)

    def test_biconvex_zero_lift_wave_drag_falls_with_mach(self):
        # M = 3, alpha = 0: cd_wave = 0.006788225099, the M^-2 fall.
        res = al.biconvex_section(0.0, TAU, 3.0)
        self.assertAlmostEqual(res["cd_wave"], 0.006788225099, delta=1e-6)

    def test_biconvex_thickness_drag_grows_quadratically(self):
        # Doubling tau quadruples the zero-lift thickness drag.
        thin = al.biconvex_section(0.0, 0.03, 2.0)
        thick = al.biconvex_section(0.0, 0.06, 2.0)
        self.assertAlmostEqual(thick["cd_wave"], 4.0 * thin["cd_wave"], delta=1e-12)

    def test_biconvex_rejects_bad_thickness(self):
        for bad in (0.0, -0.1, float("nan")):
            with self.assertRaises(ValueError):
                al.biconvex_section(ALPHA, bad, 2.0)


class TestCamberedPlate(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the cambered thin plate sizing
    cd_wave = (4a^2 + (64/3) (h/c)^2)/beta and the nose-down camber
    couple cm_le = -2a/b - (8/3)(h/c)/b."""

    def test_cambered_plate_worked(self):
        res = al.cambered_plate(ALPHA, CAMBER, 2.0)
        self.assertAlmostEqual(res["cl"], 0.120919957616, delta=1e-6)
        self.assertAlmostEqual(res["cd_wave"], 0.011258076472, delta=1e-6)
        self.assertAlmostEqual(res["cm_le"], -0.091251993165, delta=1e-6)

    def test_cambered_plate_couple_split(self):
        # cm_le = flat cm_le - camber couple = -0.060459978808 -
        # 0.030792014357: camber pitches the section nose-down.
        res = al.cambered_plate(ALPHA, CAMBER, 2.0)
        flat = al.flat_plate(ALPHA, 2.0)
        couple = (8.0 / 3.0) * CAMBER / al.ackeret_parameter(2.0)
        self.assertAlmostEqual(couple, 0.030792014357, delta=1e-6)
        self.assertAlmostEqual(res["cm_le"], flat["cm_le"] - couple, delta=1e-12)

    def test_cambered_plate_zero_lift_drag(self):
        # alpha 0: cd_wave = (64/3)(h/c)^2/beta = 0.004926722297.
        res = al.cambered_plate(0.0, CAMBER, 2.0)
        self.assertAlmostEqual(res["cl"], 0.0, delta=1e-12)
        self.assertAlmostEqual(res["cd_wave"], 0.004926722297, delta=1e-6)

    def test_cambered_plate_rejects_bad_camber(self):
        for bad in (0.0, -0.02, float("inf")):
            with self.assertRaises(ValueError):
                al.cambered_plate(ALPHA, bad, 2.0)


class TestShapeIndependence(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: cl of the thin closed section is
    4*alpha/beta for every shape, thickness and camber drop out."""

    def test_cl_identical_across_the_three_families(self):
        flat = al.flat_plate(ALPHA, 2.0)["cl"]
        biconvex = al.biconvex_section(ALPHA, TAU, 2.0)["cl"]
        cambered = al.cambered_plate(ALPHA, CAMBER, 2.0)["cl"]
        self.assertAlmostEqual(biconvex, flat, delta=1e-12)
        self.assertAlmostEqual(cambered, flat, delta=1e-12)


class TestSimpsonEngine(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the section_coefficients engine:
    the linearized pressure integral over the surface slopes phi_u(x)
    and phi_l(x) by deterministic composite Simpson quadrature, which
    must reproduce every closed form of the canonical families."""

    def setUp(self):
        self.fp = al.flat_plate(ALPHA, M2)
        self.bx = al.biconvex_section(ALPHA, TAU, M2)
        self.cp = al.cambered_plate(ALPHA, CAMBER, M2)

    def test_engine_flat_plate_identity(self):
        res = al.section_coefficients(ALPHA, M2, flat_u, flat_l)
        self.assertAlmostEqual(res["cl"], self.fp["cl"], delta=1e-9)
        self.assertAlmostEqual(res["cd_wave"], self.fp["cd_wave"], delta=1e-9)
        self.assertAlmostEqual(res["cm_le"], self.fp["cm_le"], delta=1e-9)

    def test_engine_biconvex_identity(self):
        res = al.section_coefficients(ALPHA, M2, biconvex_u, biconvex_l)
        self.assertAlmostEqual(res["cl"], self.bx["cl"], delta=1e-9)
        self.assertAlmostEqual(res["cd_wave"], self.bx["cd_wave"], delta=1e-9)
        self.assertAlmostEqual(res["cm_le"], self.bx["cm_le"], delta=1e-9)

    def test_engine_cambered_identity(self):
        res = al.section_coefficients(ALPHA, M2, cambered_u, cambered_l)
        self.assertAlmostEqual(res["cl"], self.cp["cl"], delta=1e-9)
        self.assertAlmostEqual(res["cd_wave"], self.cp["cd_wave"], delta=1e-9)
        self.assertAlmostEqual(res["cm_le"], self.cp["cm_le"], delta=1e-9)

    def test_engine_zero_lift_biconvex(self):
        # Engine cl(alpha = 0) for the symmetric biconvex is 0 while the
        # zero-lift wave drag stays positive at 0.011085125168.
        res = al.section_coefficients(0.0, M2, biconvex_u, biconvex_l)
        self.assertAlmostEqual(res["cl"], 0.0, delta=1e-12)
        self.assertAlmostEqual(res["cm_le"], 0.0, delta=1e-12)
        self.assertAlmostEqual(res["cd_wave"], 0.011085125168, delta=1e-6)

    def test_engine_rejects_bad_chord_panels_and_slopes(self):
        with self.assertRaises(ValueError):
            al.section_coefficients(ALPHA, M2, flat_u, flat_l, chord=0.0)
        with self.assertRaises(ValueError):
            al.section_coefficients(ALPHA, M2, flat_u, flat_l, chord=-1.0)
        for bad_panels in (3, 1, -2):
            with self.assertRaises(ValueError):
                al.section_coefficients(ALPHA, M2, flat_u, flat_l,
                                        panels=bad_panels)

        def bad_slope(x):
            return float("inf")

        with self.assertRaises(ValueError):
            al.section_coefficients(ALPHA, M2, bad_slope, flat_l)

    def test_engine_determinism_identical_bits(self):
        # Two identical runs return identical bits: the quadrature is
        # deterministic over the fixed SIMPSON_PANELS even intervals.
        first = al.section_coefficients(ALPHA, M2, biconvex_u, biconvex_l)
        second = al.section_coefficients(ALPHA, M2, biconvex_u, biconvex_l)
        self.assertEqual(first, second)


class TestSiblingCrossCheck(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the cross-check against the exact
    shock-expansion march sibling shock-expansion-airfoil."""

    def test_diamond_zero_lift_wave_drag(self):
        # The eps = 5 deg diamond (tau = tan(5 deg) = 0.087488663526) at
        # M = 2 has linear zero-lift cd = 4 tau^2/beta = 0.017676770709,
        # matching the sibling worked-example cd_wave = 0.0177 inside 0.2%.
        tau_dia = math.tan(math.radians(5.0))
        self.assertAlmostEqual(tau_dia, 0.087488663526, delta=1e-6)
        cd0 = 4.0 * tau_dia * tau_dia / al.ackeret_parameter(2.0)
        self.assertAlmostEqual(cd0, 0.017676770709, delta=1e-6)
        # Sibling march value 0.0177: linear cd0 sits inside its 0.2% band.
        self.assertAlmostEqual(cd0 / 0.0177, 1.0, delta=2e-3)

    def test_cl_ratio_to_exact_march(self):
        # cl(exact = 0.1227)/cl(linear = 0.120919957616) = 1.014720832024,
        # the sibling's quoted "1.5% above" linear handover.
        ratio = 0.1227 / al.lift_coefficient(ALPHA, 2.0)
        self.assertAlmostEqual(ratio, 1.014720832024, delta=1e-6)


class TestModuleDiscipline(unittest.TestCase):
    """The module discipline the workflow closes on: gamma defaults to 1.4
    and is honored by surface_pressure_ratio only, the section
    coefficients are gamma-free, and the constants are pinned."""

    def test_module_constants_and_gamma_scope(self):
        # Gamma defaults to 1.4 and is honored by surface_pressure_ratio
        # only: the ackeret section coefficients are gamma-free, so at
        # fixed alpha the Mach change from 2 to 3 moves the wave drag
        # (the M^-2 fall) with no gamma term anywhere in the producers.
        self.assertAlmostEqual(al.GAMMA, 1.4, delta=1e-12)
        self.assertEqual(al.SIMPSON_PANELS, 2000)
        bx = al.biconvex_section(ALPHA, TAU, 2.0)
        bx3 = al.biconvex_section(ALPHA, TAU, 3.0)
        self.assertNotAlmostEqual(bx["cd_wave"], bx3["cd_wave"], delta=1e-3)
        self.assertAlmostEqual(al.lift_curve_slope(3.0), 1.414213562373, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
