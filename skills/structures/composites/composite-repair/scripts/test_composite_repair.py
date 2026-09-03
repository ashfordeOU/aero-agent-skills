"""Contract test for composite-repair (bonded scarf repair sizing).

Runs offline, deterministic, stdlib only:
    python3 test_composite_repair.py
Covers the worked example of the wave-30 composite-repair spec (3.0 mm
carbon/epoxy parent at 300 MPa, E = 70 GPa, 3 deg scarf, 12 MPa adhesive
allowable), the 2.2 deg passing case, the magnitude bounds, patch
stiffness identity, determinism and ValueError rejection of
non-physical inputs.
"""

import math
import unittest

import composite_repair_logic as cr


class TestScarfLength(unittest.TestCase):
    def test_worked_example_scarf_length_mm(self):
        # 3.0 mm / tan(3 deg) = 57.24 mm, spec bound 50-65 mm.
        self.assertAlmostEqual(cr.scarf_length(3.0, 3.0), 57.2434, places=3)

    def test_scarf_length_si(self):
        self.assertAlmostEqual(cr.scarf_length(0.003, 3.0),
                               0.0572434, places=7)

    def test_scarf_length_bound_50_65_mm(self):
        self.assertTrue(50.0 <= cr.scarf_length(3.0, 3.0) <= 65.0)

    def test_scarf_length_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cr.scarf_length(0.0, 3.0)

    def test_scarf_length_negative_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cr.scarf_length(-1.0, 3.0)

    def test_scarf_length_angle_zero_or_negative_rejected(self):
        with self.assertRaises(ValueError):
            cr.scarf_length(3.0, 0.0)
        with self.assertRaises(ValueError):
            cr.scarf_length(3.0, -2.0)

    def test_scarf_length_right_angle_rejected(self):
        with self.assertRaises(ValueError):
            cr.scarf_length(3.0, 90.0)

    def test_scarf_length_shallower_angle_longer(self):
        # A shallower scarf is longer: monotone in 1/tan on (0, 90).
        self.assertGreater(cr.scarf_length(3.0, 2.0),
                           cr.scarf_length(3.0, 3.0))


class TestAdhesiveShearStress(unittest.TestCase):
    def test_worked_example_shear_mpa(self):
        # 300 * sin(3) * cos(3) = 15.68 MPa, spec bound 14-17 MPa.
        self.assertAlmostEqual(cr.adhesive_shear_stress(300.0, 3.0),
                               15.6793, places=3)

    def test_worked_example_shear_pa(self):
        self.assertAlmostEqual(cr.adhesive_shear_stress(300e6, 3.0),
                               15.67927e6, places=-2)

    def test_shear_bound_14_17_mpa(self):
        tau = cr.adhesive_shear_stress(300.0, 3.0)
        self.assertTrue(14.0 <= tau <= 17.0)

    def test_shear_identity_sin_cos_form(self):
        # tau = sigma * sin * cos equals (sigma / 2) * sin(2 theta).
        theta = 3.0 * cr.DEG2RAD
        self.assertAlmostEqual(
            cr.adhesive_shear_stress(300.0, 3.0),
            150.0 * math.sin(2.0 * theta), places=6)

    def test_shear_zero_stress_zero_tau(self):
        self.assertEqual(cr.adhesive_shear_stress(0.0, 3.0), 0.0)

    def test_shear_negative_stress_rejected(self):
        with self.assertRaises(ValueError):
            cr.adhesive_shear_stress(-1.0, 3.0)

    def test_shear_angle_out_of_range_or_negative_rejected(self):
        with self.assertRaises(ValueError):
            cr.adhesive_shear_stress(300.0, 90.0)
        with self.assertRaises(ValueError):
            cr.adhesive_shear_stress(300.0, -3.0)


class TestRequiredScarfAngle(unittest.TestCase):
    def test_worked_example_required_angle_deg(self):
        # 0.5 * asin(24 / 300) = 2.29 deg, spec bound 2.0-2.6 deg.
        self.assertAlmostEqual(cr.required_scarf_angle(300.0, 12.0),
                               2.2943, places=3)

    def test_required_angle_bound_2_0_2_6_deg(self):
        theta = cr.required_scarf_angle(300.0, 12.0)
        self.assertTrue(2.0 <= theta <= 2.6)

    def test_required_angle_round_trip(self):
        # Scarfing at the required angle exactly clears the allowable:
        # tau(theta_req) == allowable within floating point tolerance.
        theta_req = cr.required_scarf_angle(300.0, 12.0)
        self.assertAlmostEqual(cr.adhesive_shear_stress(300.0, theta_req),
                               12.0, places=6)

    def test_required_angle_nonpositive_stress_rejected(self):
        with self.assertRaises(ValueError):
            cr.required_scarf_angle(0.0, 12.0)
        with self.assertRaises(ValueError):
            cr.required_scarf_angle(-100.0, 12.0)

    def test_required_angle_nonpositive_allowable_rejected(self):
        with self.assertRaises(ValueError):
            cr.required_scarf_angle(300.0, 0.0)
        with self.assertRaises(ValueError):
            cr.required_scarf_angle(300.0, -5.0)

    def test_required_angle_no_real_scarf_raises(self):
        # 2 * 80 / 100 = 1.6 > 1: no real angle carries the load.
        with self.assertRaises(ValueError):
            cr.required_scarf_angle(100.0, 80.0)

    def test_required_angle_exactly_one_edge(self):
        # ratio = 1.0 -> theta = 45 deg, still real.
        self.assertAlmostEqual(cr.required_scarf_angle(200.0, 100.0),
                               45.0, places=9)


class TestPatchThickness(unittest.TestCase):
    def test_patch_identity_same_material(self):
        # Stiffness match with E_patch == E_parent returns t_parent.
        self.assertEqual(cr.patch_thickness_for_stiffness(3.0, 70.0, 70.0),
                         3.0)

    def test_patch_identity_si(self):
        self.assertEqual(cr.patch_thickness_for_stiffness(0.003, 70e9, 70e9),
                         0.003)

    def test_patch_stiffness_trends(self):
        # A stiffer patch needs less thickness; a softer patch more.
        self.assertLess(
            cr.patch_thickness_for_stiffness(3.0, 70.0, 140.0), 1.6)
        self.assertGreater(
            cr.patch_thickness_for_stiffness(3.0, 70.0, 35.0), 5.9)

    def test_patch_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cr.patch_thickness_for_stiffness(0.0, 70.0, 70.0)

    def test_patch_zero_modulus_rejected(self):
        with self.assertRaises(ValueError):
            cr.patch_thickness_for_stiffness(3.0, 0.0, 70.0)

    def test_patch_zero_patch_modulus_rejected(self):
        with self.assertRaises(ValueError):
            cr.patch_thickness_for_stiffness(3.0, 70.0, 0.0)


class TestRepairSizing(unittest.TestCase):
    def test_worked_example_sizing_dict(self):
        s = cr.repair_sizing(0.003, 300e6, 70e9, 70e9, 3.0, 12e6)
        self.assertEqual(
            set(s.keys()),
            {"scarf_length_m", "scarf_angle_deg", "adhesive_shear_Pa",
             "required_scarf_angle_deg", "patch_thickness_m", "margin"})
        self.assertAlmostEqual(s["scarf_length_m"], 0.0572434, places=7)
        self.assertAlmostEqual(s["adhesive_shear_Pa"],
                               15.67927e6, places=-2)
        self.assertAlmostEqual(s["required_scarf_angle_deg"],
                               2.2943, places=3)
        self.assertEqual(s["patch_thickness_m"], 0.003)
        self.assertEqual(s["scarf_angle_deg"], 3.0)

    def test_margin_negative_three_degree_case(self):
        # Chosen 3 deg scarf against a 12 MPa allowable FAILS.
        s = cr.repair_sizing(0.003, 300e6, 70e9, 70e9, 3.0, 12e6)
        self.assertLess(s["margin"], 0.0)
        self.assertTrue(-0.35 <= s["margin"] <= -0.15)
        self.assertAlmostEqual(s["margin"], -0.2347, places=3)

    def test_margin_positive_two_two_degree_case(self):
        # 2.2 deg scarf: tau = 11.51 MPa < 12 MPa allowable, margin > 0.
        tau22 = cr.adhesive_shear_stress(300.0, 2.2)
        self.assertAlmostEqual(tau22, 11.5079, places=3)
        self.assertTrue(11.0 <= tau22 <= 12.0)
        margin22 = 12.0 / tau22 - 1.0
        self.assertGreater(margin22, 0.0)
        self.assertAlmostEqual(margin22, 0.0428, places=3)
        s22 = cr.repair_sizing(0.003, 300e6, 70e9, 70e9, 2.2, 12e6)
        self.assertGreater(s22["margin"], 0.0)
        self.assertAlmostEqual(s22["margin"], 0.0428, places=3)

    def test_sizing_propagates_value_error(self):
        with self.assertRaises(ValueError):
            cr.repair_sizing(0.003, 300e6, 70e9, 70e9, 3.0, 0.0)


class TestDeterminism(unittest.TestCase):
    def test_module_deterministic(self):
        a = cr.repair_sizing(0.003, 300e6, 70e9, 70e9, 3.0, 12e6)
        b = cr.repair_sizing(0.003, 300e6, 70e9, 70e9, 3.0, 12e6)
        self.assertEqual(a, b)

    def test_deg2rad_constant(self):
        self.assertAlmostEqual(cr.DEG2RAD, math.pi / 180.0, places=15)


if __name__ == "__main__":
    unittest.main()
