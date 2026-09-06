"""Contract test for metallic-fastener-joints (structures/fem).

Exercises the SKILL.md metallic multi-fastener joint workflow end to end:
step 1 (split the symmetric pattern into per-fastener shares), step 2
(shear-check the fasteners in single or double shear), step 3
(bearing-check the sheet), step 4 (net-section tension check across the
fastener row), step 5 (shear-out check at the sheet edge), step 6 (apply
the margin of safety with the 1.5 ultimate factor), step 7 (resolve the
eccentric bolt group by the polar moment method) and step 8 (size the
bracket fasteners from the max-loaded fastener). All worked-example
values are real module outputs against the spec magnitude bounds;
every numeric assert is order-safe and tolerance-based so the suite
passes identically under /usr/bin/python3 and the pyenv 3.13.12 hook
interpreter.
"""

import math
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metallic_fastener_joints_logic as m

# Worked example A: four 1/4-in MS bolts (D = 6.35 mm) in a symmetric row
# across a 2024-T3 sheet, t = 2.5 mm, w = 90 mm, e = 12.7 mm, limit 20000 N.
D_BOLT = 6.35
T_SHEET = 2.5
W_JOINT = 90.0
E_EDGE = 12.7
P_LIMIT = 20000.0
N_FAST = 4

# Worked example B: eccentric bracket group, four bolts at (+/-25, +/-25),
# 27000 N in +x applied at (0, +100) mm, 100 mm off the pattern centroid.
SQUARE_BOLTS = [(25, 25), (-25, 25), (-25, -25), (25, -25)]
COINCIDENT_BOLTS = [(10, 10), (10, 10), (10, 10), (10, 10)]


class FastenerAreaTests(unittest.TestCase):
    """Step 2 helpers: fastener shear area from the bolt diameter."""

    def test_fastener_area_worked_example(self):
        # Step 2, fastener shear area: pi*D^2/4 of the 1/4-in MS bolt.
        self.assertAlmostEqual(m.fastener_area(D_BOLT), 31.669217, delta=1e-3)

    def test_fastener_area_rejects_nonpositive_diameter(self):
        # Step 2 input guard: a zero diameter must be rejected.
        with self.assertRaises(ValueError):
            m.fastener_area(0)
        with self.assertRaises(ValueError):
            m.fastener_area(-6.35)


class FastenerShearTests(unittest.TestCase):
    """Step 2 of the workflow: shear-check the fasteners in single or
    double shear over the fastener shear area."""

    def test_single_shear_stress_worked_example(self):
        # Step 2 single shear: tau = P_f/(1*A) = 157.882019 MPa at 5000 N.
        self.assertAlmostEqual(
            m.fastener_shear_stress(P_LIMIT / N_FAST, D_BOLT, 1),
            157.882019, delta=1e-3)

    def test_double_shear_halves_the_single_shear_stress(self):
        # Step 2 double shear: two planes halve the stress exactly, so
        # 2*tau_double equals tau_single within 1e-9 relative.
        tau_single = m.fastener_shear_stress(5000.0, D_BOLT, 1)
        tau_double = m.fastener_shear_stress(5000.0, D_BOLT, 2)
        self.assertAlmostEqual(tau_double, 78.941010, delta=1e-3)
        self.assertTrue(math.isclose(2.0 * tau_double, tau_single, rel_tol=1e-9))

    def test_shear_stress_rejects_nonpositive_diameter(self):
        # Step 2 input guard on the fastener diameter.
        with self.assertRaises(ValueError):
            m.fastener_shear_stress(5000.0, 0.0, 1)

    def test_shear_stress_rejects_planes_outside_one_two(self):
        # Step 2 input guard: only single (1) and double (2) shear exist.
        with self.assertRaises(ValueError):
            m.fastener_shear_stress(1000.0, D_BOLT, 3)
        with self.assertRaises(ValueError):
            m.fastener_shear_stress(1000.0, D_BOLT, 0)

    def test_shear_stress_rejects_negative_fastener_load(self):
        # Step 2 input guard: a negative fastener share is non-physical.
        with self.assertRaises(ValueError):
            m.fastener_shear_stress(-1.0, D_BOLT, 1)


class BearingTests(unittest.TestCase):
    """Step 3 of the workflow: bearing-check the sheet under each fastener."""

    def test_bearing_stress_worked_example(self):
        # Step 3 bearing: sigma_b = 5000/(6.35*2.5) = 314.960630 MPa.
        self.assertAlmostEqual(
            m.bearing_stress(P_LIMIT / N_FAST, D_BOLT, T_SHEET),
            314.960630, delta=1e-3)

    def test_bearing_stress_rejects_nonphysical_inputs(self):
        # Step 3 input guards on load, diameter and sheet thickness.
        with self.assertRaises(ValueError):
            m.bearing_stress(1000.0, D_BOLT, 0)
        with self.assertRaises(ValueError):
            m.bearing_stress(1000.0, 0.0, T_SHEET)
        with self.assertRaises(ValueError):
            m.bearing_stress(-5.0, D_BOLT, T_SHEET)


class NetSectionTests(unittest.TestCase):
    """Step 4 of the workflow: net-section tension check across the
    fastener row on the net width w - holes*D."""

    def test_net_section_stress_worked_example(self):
        # Step 4 net section: 20000/((90 - 4*6.35)*2.5) = 123.839009 MPa,
        # net width 64.6 mm, the full row load across the net section.
        self.assertAlmostEqual(
            m.net_section_stress(P_LIMIT, W_JOINT, N_FAST, D_BOLT, T_SHEET),
            123.839009, delta=1e-3)

    def test_net_section_rejects_destroyed_net_section(self):
        # Step 4 input guard: net width w - holes*D must stay positive.
        with self.assertRaises(ValueError):
            m.net_section_stress(10000.0, 25.4, 4, D_BOLT, T_SHEET)

    def test_net_section_rejects_nonpositive_holes(self):
        # Step 4 input guard: a fastener row needs at least one hole.
        with self.assertRaises(ValueError):
            m.net_section_stress(10000.0, W_JOINT, 0, D_BOLT, T_SHEET)
        with self.assertRaises(ValueError):
            m.net_section_stress(10000.0, W_JOINT, -2, D_BOLT, T_SHEET)

    def test_net_section_rejects_bad_dimensions(self):
        # Step 4 input guards on width and thickness.
        with self.assertRaises(ValueError):
            m.net_section_stress(10000.0, -90.0, N_FAST, D_BOLT, T_SHEET)
        with self.assertRaises(ValueError):
            m.net_section_stress(-1.0, W_JOINT, N_FAST, D_BOLT, T_SHEET)


class ShearOutTests(unittest.TestCase):
    """Step 5 of the workflow: shear-out check at the sheet edge on the
    two shear planes of length e."""

    def test_shear_out_stress_worked_example(self):
        # Step 5 shear-out: 5000/(2*12.7*2.5) = 78.740157 MPa.
        self.assertAlmostEqual(
            m.shear_out_stress(P_LIMIT / N_FAST, E_EDGE, T_SHEET),
            78.740157, delta=1e-3)

    def test_bearing_to_shear_out_ratio_is_two_e_over_d(self):
        # Steps 3 and 5 together: bearing/shear-out = 2e/D; at e = 2D the
        # ratio is exactly 4 (the 2e/D relation anchor).
        bearing = m.bearing_stress(5000.0, D_BOLT, T_SHEET)
        shear_out = m.shear_out_stress(5000.0, 2.0 * D_BOLT, T_SHEET)
        self.assertTrue(math.isclose(bearing / shear_out, 4.0, rel_tol=1e-9))

    def test_shear_out_rejects_bad_inputs(self):
        # Step 5 input guards on load, edge distance and thickness.
        with self.assertRaises(ValueError):
            m.shear_out_stress(1000.0, 0.0, T_SHEET)
        with self.assertRaises(ValueError):
            m.shear_out_stress(1000.0, E_EDGE, 0.0)
        with self.assertRaises(ValueError):
            m.shear_out_stress(-3.0, E_EDGE, T_SHEET)


class MarginOfSafetyTests(unittest.TestCase):
    """Step 6 of the workflow: apply the margin of safety convention
    MoS = allowable/(factor*applied_limit) - 1 with the 1.5 ultimate
    factor on limit stresses (FAR 25.303 style)."""

    def test_margin_zero_when_factored_stress_equals_allowable(self):
        # Step 6: MoS(F, F/1.5) = 0 exactly, the factored applied stress
        # equal to the allowable is zero margin.
        self.assertAlmostEqual(m.margin_of_safety(427.0, 427.0 / 1.5),
                               0.0, delta=1e-12)

    def test_margin_minus_one_third_at_plain_ultimate(self):
        # Step 6: MoS(F, F) = -1/3 under the 1.5 factor, since the
        # allowable carries no ultimate factor of its own.
        self.assertAlmostEqual(m.margin_of_safety(427.0, 427.0),
                               -1.0 / 3.0, delta=1e-9)

    def test_margin_factor_one_recovers_sibling_form(self):
        # Step 6: factor = 1.0 gives the plain allowable/applied - 1 form
        # used by the sibling leaves, MoS(2F, F) = 1 exactly.
        self.assertAlmostEqual(m.margin_of_safety(200.0, 100.0, factor=1.0),
                               1.0, delta=1e-12)

    def test_margin_rejects_bad_inputs(self):
        # Step 6 input guards: positive allowable, applied limit, factor.
        with self.assertRaises(ValueError):
            m.margin_of_safety(0.0, 100.0)
        with self.assertRaises(ValueError):
            m.margin_of_safety(400.0, 0.0)
        with self.assertRaises(ValueError):
            m.margin_of_safety(400.0, 100.0, 0.0)


class SpliceJointTests(unittest.TestCase):
    """Steps 1-6 of the workflow on the one-shot symmetric splice:
    splice_joint_analysis splits the row load into per-fastener shares,
    runs the fastener shear, bearing, net-section and shear-out checks
    and returns the margins, governing mode and pass verdict."""

    def test_splice_report_margins_and_governing_mode(self):
        # Step 1 split: 20000/4 = 5000.0000 N exactly per fastener.
        report = m.splice_joint_analysis(P_LIMIT, N_FAST, D_BOLT, T_SHEET,
                                         W_JOINT, E_EDGE, m.BOLT_F_SU,
                                         m.SHEET_F_BRU, m.SHEET_F_TU,
                                         m.SHEET_F_SU)
        self.assertAlmostEqual(report["per_fastener_load_N"], 5000.0, delta=1e-9)
        margins = report["margins"]
        self.assertAlmostEqual(margins["fastener_shear"], 1.765778, delta=1e-3)
        self.assertAlmostEqual(margins["bearing"], 0.312333, delta=1e-3)
        self.assertAlmostEqual(margins["net_section"], 1.298683, delta=1e-3)
        self.assertAlmostEqual(margins["shear_out"], 1.159000, delta=1e-3)
        # Governing mode is the lowest margin and the joint passes.
        self.assertEqual(report["governing"], "bearing")
        self.assertEqual(report["governing"],
                         min(margins, key=lambda k: margins[k]))
        self.assertAlmostEqual(report["min_margin"], 0.312333, delta=1e-3)
        self.assertTrue(report["min_margin"] >= 0.0)
        self.assertTrue(report["passes"])

    def test_splice_2x_overload_flips_governing_bearing_margin(self):
        # Step 6 verdict at 2.0x limit: 40000 N halves every margin and
        # the bearing-critical joint fails.
        report = m.splice_joint_analysis(2.0 * P_LIMIT, N_FAST, D_BOLT,
                                         T_SHEET, W_JOINT, E_EDGE,
                                         m.BOLT_F_SU, m.SHEET_F_BRU,
                                         m.SHEET_F_TU, m.SHEET_F_SU)
        self.assertAlmostEqual(report["margins"]["bearing"], -0.343833,
                               delta=1e-3)
        self.assertEqual(report["governing"], "bearing")
        self.assertFalse(report["passes"])

    def test_splice_equal_share_identity(self):
        # Step 1 identity: n times the per-fastener share recovers the
        # full row load exactly.
        share = m.splice_joint_analysis(P_LIMIT, N_FAST, D_BOLT, T_SHEET,
                                        W_JOINT, E_EDGE, m.BOLT_F_SU,
                                        m.SHEET_F_BRU, m.SHEET_F_TU,
                                        m.SHEET_F_SU)["per_fastener_load_N"]
        self.assertAlmostEqual(N_FAST * share, P_LIMIT, delta=1e-9)

    def test_splice_rejects_nonphysical_patterns(self):
        # Step 1 input guards: the pattern needs a positive integer count.
        with self.assertRaises(ValueError):
            m.splice_joint_analysis(P_LIMIT, 0, D_BOLT, T_SHEET, W_JOINT,
                                    E_EDGE, 655.0, 620.0, 427.0, 255.0)
        with self.assertRaises(ValueError):
            m.splice_joint_analysis(-100.0, N_FAST, D_BOLT, T_SHEET, W_JOINT,
                                    E_EDGE, 655.0, 620.0, 427.0, 255.0)
        with self.assertRaises(ValueError):
            m.splice_joint_analysis(P_LIMIT, N_FAST, 0.0, T_SHEET, W_JOINT,
                                    E_EDGE, 655.0, 620.0, 427.0, 255.0)
        with self.assertRaises(ValueError):
            m.splice_joint_analysis(P_LIMIT, N_FAST, D_BOLT, T_SHEET, W_JOINT,
                                    E_EDGE, 0.0, 620.0, 427.0, 255.0)


class BoltGroupPropertiesTests(unittest.TestCase):
    """Step 7 of the workflow: the polar moment method starts from the
    bolt group centroid and polar moment J."""

    def test_square_group_centroid_and_polar_moment(self):
        # Step 7 centroid and polar moment of the 50 mm square: J = n*r^2
        # = 4*(25^2 + 25^2) = 5000 mm^2.
        x_c, y_c, j_polar = m.bolt_group_properties(SQUARE_BOLTS)
        self.assertAlmostEqual(x_c, 0.0, delta=1e-9)
        self.assertAlmostEqual(y_c, 0.0, delta=1e-9)
        self.assertAlmostEqual(j_polar, 5000.0, delta=1e-9)

    def test_empty_group_rejected(self):
        # Step 7 input guard: the group needs bolts to have a centroid.
        with self.assertRaises(ValueError):
            m.bolt_group_properties([])


class EccentricGroupTests(unittest.TestCase):
    """Step 7 of the workflow: resolve the eccentric bolt group by the
    polar moment method, adding the equal direct share to the torque-
    driven secondary share M*r_i/J on each bolt."""

    def test_torque_about_centroid(self):
        # Step 7 torque: M = (ax - x_c)*fy - (ay - y_c)*fx = -100*27000
        # = -2700000 N*mm, clockwise about the group centroid.
        result = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                              SQUARE_BOLTS)
        self.assertAlmostEqual(result["torque_Nmm"], -2700000.0, delta=1.0)
        self.assertAlmostEqual(result["polar_moment_mm2"], 5000.0, delta=1e-9)
        dx, dy = result["direct_per_fastener_N"]
        self.assertAlmostEqual(dx, 6750.0, delta=1e-9)
        self.assertAlmostEqual(dy, 0.0, delta=1e-9)

    def test_per_bolt_direct_and_secondary_resultants(self):
        # Step 7 per-bolt loads: direct (6750, 0) plus secondary
        # (M/J)*(-dy, dx); the two top bolts carry 24337.471109 N and the
        # two bottom bolts 15093.458848 N.
        result = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                              SQUARE_BOLTS)
        magnitudes = [f["magnitude_N"] for f in result["fasteners"]]
        self.assertAlmostEqual(magnitudes[0], 24337.471109, delta=0.01)
        self.assertAlmostEqual(magnitudes[1], 24337.471109, delta=0.01)
        self.assertAlmostEqual(magnitudes[2], 15093.458848, delta=0.01)
        self.assertAlmostEqual(magnitudes[3], 15093.458848, delta=0.01)
        # The radius of every corner bolt is sqrt(2)*25 mm.
        self.assertAlmostEqual(result["fasteners"][0]["r_mm"],
                               35.355339, delta=1e-3)

    def test_max_loaded_fastener_ties_by_mirror_symmetry(self):
        # Step 7 max-loaded fastener: 24337.471109 N on indices [0, 1],
        # the two top bolts tying by mirror symmetry about the load plane.
        result = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                              SQUARE_BOLTS)
        self.assertAlmostEqual(result["max_magnitude_N"], 24337.471109,
                               delta=0.01)
        self.assertEqual(result["max_indices"], [0, 1])
        self.assertEqual(result["max_fastener"]["x"], 25)
        self.assertEqual(result["max_fastener"]["y"], 25)

    def test_eccentric_equilibrium_sums(self):
        # Step 7 equilibrium: the per-bolt total forces sum to the applied
        # force and their moments sum exactly to the applied torque.
        result = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                              SQUARE_BOLTS)
        sum_x = sum(f["total_N"][0] for f in result["fasteners"])
        sum_y = sum(f["total_N"][1] for f in result["fasteners"])
        sum_moment = sum(f["x"] * f["total_N"][1]
                         - f["y"] * f["total_N"][0]
                         for f in result["fasteners"])
        self.assertTrue(math.isclose(sum_x, 27000.0, rel_tol=1e-6))
        self.assertTrue(abs(sum_y) < 1e-9)
        self.assertTrue(math.isclose(sum_moment, -2700000.0, rel_tol=1e-6))

    def test_force_line_through_centroid_gives_equal_share(self):
        # Step 7 zero-torque case: with the force line through the group
        # centroid (M = 0) every bolt carries exactly P/n = 6750 N.
        result = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 0.0,
                                              SQUARE_BOLTS)
        for fastener in result["fasteners"]:
            self.assertAlmostEqual(fastener["magnitude_N"], 6750.0, delta=1e-9)
        self.assertEqual(result["max_indices"], [0, 1, 2, 3])

    def test_rejects_unresolvable_groups(self):
        # Step 7 input guards: a zero applied force has no direct share,
        # coincident bolts collapse the polar moment to zero, and an
        # empty group has no centroid.
        with self.assertRaises(ValueError):
            m.eccentric_bolt_group_loads(0.0, 0.0, 0.0, 100.0, SQUARE_BOLTS)
        with self.assertRaises(ValueError):
            m.eccentric_bolt_group_loads(1000.0, 0.0, 0.0, 100.0,
                                         COINCIDENT_BOLTS)
        with self.assertRaises(ValueError):
            m.eccentric_bolt_group_loads(1000.0, 0.0, 0.0, 100.0, [])


class BracketSizingTests(unittest.TestCase):
    """Step 8 of the workflow: size the bracket fasteners from the
    max-loaded fastener shear stress against the fastener allowable."""

    def test_bracket_needs_three_eighth_inch_bolts(self):
        # Step 8 sizing: the max-loaded 24337 N on a 3/8-in MS bolt (D =
        # 9.525 mm, area 71.256 mm^2) gives 341.551030 MPa, margin
        # +0.278481, passing under the 1.5 ultimate factor.
        result = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                              SQUARE_BOLTS)
        max_load = result["max_magnitude_N"]
        area_38 = m.fastener_area(9.525)
        self.assertAlmostEqual(area_38, 71.256, delta=0.01)
        tau_38 = m.fastener_shear_stress(max_load, 9.525, 1)
        self.assertAlmostEqual(tau_38, 341.551030, delta=1e-3)
        self.assertAlmostEqual(m.margin_of_safety(m.BOLT_F_SU, tau_38),
                               0.278481, delta=1e-3)
        self.assertTrue(m.margin_of_safety(m.BOLT_F_SU, tau_38) >= 0.0)
        # The same group with 1/4-in bolts overstresses: -0.431786 fails.
        tau_14 = m.fastener_shear_stress(max_load, D_BOLT, 1)
        self.assertAlmostEqual(tau_14, 768.489817, delta=1e-3)
        self.assertAlmostEqual(m.margin_of_safety(m.BOLT_F_SU, tau_14),
                               -0.431786, delta=1e-3)


class DeterminismTests(unittest.TestCase):
    """Workflow hygiene: pure stdlib, deterministic runs."""

    def test_eccentric_runs_are_bit_identical(self):
        # Determinism: identical floats run to run, no RNG anywhere.
        first = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                             SQUARE_BOLTS)
        second = m.eccentric_bolt_group_loads(27000.0, 0.0, 0.0, 100.0,
                                              SQUARE_BOLTS)
        self.assertEqual(first["max_magnitude_N"], second["max_magnitude_N"])
        self.assertEqual(first["torque_Nmm"], second["torque_Nmm"])
        self.assertEqual([f["magnitude_N"] for f in first["fasteners"]],
                         [f["magnitude_N"] for f in second["fasteners"]])

    def test_module_imports_only_math(self):
        # No imports beyond the standard math module in the logic file.
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "metallic_fastener_joints_logic.py")
        with open(logic_path, "r") as handle:
            source = handle.read()
        imports = re.findall(r"^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)",
                             source, flags=re.MULTILINE)
        self.assertEqual(imports, ["math"])


if __name__ == "__main__":
    unittest.main()
