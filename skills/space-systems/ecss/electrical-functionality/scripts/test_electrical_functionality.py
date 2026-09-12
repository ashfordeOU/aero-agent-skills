import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from electrical_functionality_logic import (
    check_bond_resistance,
    categorize_joints,
    check_lightning_zone_assignment,
    check_lightning_provisions,
    check_emc_bond,
    check_aperture,
    PRIMARY_BOND_LIMIT_OHMS,
    SECONDARY_BOND_LIMIT_OHMS,
    EMC_BOND_LIMIT_OHMS,
    APERTURE_SCREEN_THRESHOLD_MM,
    SCREEN_MESH_LIMIT_MM,
)


class TestBondResistance(unittest.TestCase):

    def test_primary_joint_within_limit(self):
        r = check_bond_resistance("J1", 1.0e-3, "primary")
        self.assertTrue(r["compliant"])
        self.assertEqual(r["limit_ohms"], PRIMARY_BOND_LIMIT_OHMS)
        self.assertAlmostEqual(r["margin_ohms"], 1.5e-3, places=9)

    def test_primary_joint_at_limit(self):
        r = check_bond_resistance("J2", PRIMARY_BOND_LIMIT_OHMS, "primary")
        self.assertTrue(r["compliant"])
        self.assertAlmostEqual(r["margin_ohms"], 0.0, places=9)

    def test_primary_joint_exceeds_limit(self):
        r = check_bond_resistance("J3", 5.0e-3, "primary")
        self.assertFalse(r["compliant"])
        self.assertLess(r["margin_ohms"], 0.0)

    def test_secondary_joint_within_limit(self):
        r = check_bond_resistance("J4", 8.0e-3, "secondary")
        self.assertTrue(r["compliant"])
        self.assertEqual(r["limit_ohms"], SECONDARY_BOND_LIMIT_OHMS)

    def test_secondary_joint_at_limit(self):
        r = check_bond_resistance("J5", SECONDARY_BOND_LIMIT_OHMS, "secondary")
        self.assertTrue(r["compliant"])

    def test_secondary_joint_exceeds_limit(self):
        r = check_bond_resistance("J6", 15.0e-3, "secondary")
        self.assertFalse(r["compliant"])
        self.assertLess(r["margin_ohms"], 0.0)

    def test_unknown_structure_class_raises(self):
        with self.assertRaises(ValueError) as ctx:
            check_bond_resistance("J7", 1.0e-3, "tertiary")
        self.assertIn("tertiary", str(ctx.exception))

    def test_categorize_joints_splits_correctly(self):
        j1 = check_bond_resistance("J1", 1.0e-3, "primary")    # compliant
        j2 = check_bond_resistance("J2", 5.0e-3, "primary")    # non-compliant
        j3 = check_bond_resistance("J3", 9.0e-3, "secondary")  # compliant
        groups = categorize_joints([j1, j2, j3])
        self.assertEqual(len(groups["compliant"]), 2)
        self.assertEqual(len(groups["non_compliant"]), 1)
        self.assertEqual(groups["non_compliant"][0]["joint_id"], "J2")

    def test_categorize_empty_list(self):
        groups = categorize_joints([])
        self.assertEqual(groups["compliant"], [])
        self.assertEqual(groups["non_compliant"], [])


class TestLightningZoneAssignment(unittest.TestCase):

    def test_all_external_surfaces_have_zones_no_findings(self):
        surfaces = [
            {"id": "S1", "is_external": True, "lightning_zone": "1A"},
            {"id": "S2", "is_external": True, "lightning_zone": "2B"},
            {"id": "S3", "is_external": False, "lightning_zone": None},
        ]
        self.assertEqual(check_lightning_zone_assignment(surfaces), [])

    def test_external_surface_missing_zone_is_flagged(self):
        surfaces = [{"id": "S4", "is_external": True, "lightning_zone": None}]
        findings = check_lightning_zone_assignment(surfaces)
        self.assertEqual(len(findings), 1)
        self.assertIn("S4", findings[0])

    def test_internal_surface_without_zone_is_not_flagged(self):
        surfaces = [{"id": "S5", "is_external": False, "lightning_zone": None}]
        self.assertEqual(check_lightning_zone_assignment(surfaces), [])

    def test_multiple_surfaces_only_unassigned_external_flagged(self):
        surfaces = [
            {"id": "S6", "is_external": True, "lightning_zone": "3"},
            {"id": "S7", "is_external": True, "lightning_zone": None},
            {"id": "S8", "is_external": False, "lightning_zone": None},
        ]
        findings = check_lightning_zone_assignment(surfaces)
        self.assertEqual(len(findings), 1)
        self.assertIn("S7", findings[0])


class TestLightningProvisions(unittest.TestCase):

    def test_zone_1a_with_all_provisions_adequate(self):
        r = check_lightning_provisions(
            "S1", "1A",
            ["strike_receptor", "down_conductor", "diverter_strip"]
        )
        self.assertTrue(r["adequate"])
        self.assertEqual(r["missing"], [])

    def test_zone_1a_extra_provision_still_adequate(self):
        r = check_lightning_provisions(
            "S2", "1A",
            ["strike_receptor", "down_conductor", "diverter_strip", "bond_jumper"]
        )
        self.assertTrue(r["adequate"])

    def test_zone_1a_missing_diverter_strip_flagged(self):
        r = check_lightning_provisions("S3", "1A", ["strike_receptor", "down_conductor"])
        self.assertFalse(r["adequate"])
        self.assertIn("diverter_strip", r["missing"])

    def test_zone_1b_requires_only_receptor_and_conductor(self):
        r = check_lightning_provisions(
            "S4", "1B", ["strike_receptor", "down_conductor"]
        )
        self.assertTrue(r["adequate"])
        self.assertEqual(r["missing"], [])

    def test_zone_2b_requires_only_diverter_strip(self):
        r = check_lightning_provisions("S5", "2B", ["diverter_strip"])
        self.assertTrue(r["adequate"])

    def test_zone_3_requires_no_provisions(self):
        r = check_lightning_provisions("S6", "3", [])
        self.assertTrue(r["adequate"])
        self.assertEqual(r["missing"], [])

    def test_unknown_zone_raises(self):
        with self.assertRaises(ValueError) as ctx:
            check_lightning_provisions("S7", "4C", [])
        self.assertIn("4C", str(ctx.exception))


class TestEmcBond(unittest.TestCase):

    def test_emc_bond_within_limit(self):
        r = check_emc_bond("E1", 1.0e-3)
        self.assertTrue(r["compliant"])
        self.assertEqual(r["limit_ohms"], EMC_BOND_LIMIT_OHMS)
        self.assertGreater(r["margin_ohms"], 0.0)

    def test_emc_bond_at_limit(self):
        r = check_emc_bond("E2", EMC_BOND_LIMIT_OHMS)
        self.assertTrue(r["compliant"])

    def test_emc_bond_exceeds_limit(self):
        r = check_emc_bond("E3", 5.0e-3)
        self.assertFalse(r["compliant"])
        self.assertLess(r["margin_ohms"], 0.0)

    def test_secondary_bond_passes_structural_but_fails_emc(self):
        # 8 mΩ: within secondary limit (10 mΩ) but above EMC limit (2.5 mΩ)
        structural = check_bond_resistance("J1", 8.0e-3, "secondary")
        emc = check_emc_bond("J1", 8.0e-3)
        self.assertTrue(structural["compliant"])
        self.assertFalse(emc["compliant"])


class TestApertureControl(unittest.TestCase):

    def test_small_aperture_needs_no_screen(self):
        r = check_aperture("A1", 20.0, False)
        self.assertFalse(r["needs_screen"])
        self.assertTrue(r["compliant"])
        self.assertIsNone(r["finding"])
        self.assertIsNone(r["has_adequate_screen"])

    def test_aperture_at_threshold_does_not_need_screen(self):
        r = check_aperture("A2", APERTURE_SCREEN_THRESHOLD_MM, False)
        self.assertFalse(r["needs_screen"])
        self.assertTrue(r["compliant"])

    def test_large_aperture_without_screen_noncompliant(self):
        r = check_aperture("A3", 50.0, False)
        self.assertTrue(r["needs_screen"])
        self.assertFalse(r["compliant"])
        self.assertIn("A3", r["finding"])

    def test_large_aperture_with_adequate_screen_compliant(self):
        r = check_aperture("A4", 50.0, True, screen_mesh_mm=2.0)
        self.assertTrue(r["compliant"])
        self.assertTrue(r["has_adequate_screen"])
        self.assertIsNone(r["finding"])

    def test_large_aperture_screen_at_mesh_limit_compliant(self):
        r = check_aperture("A5", 50.0, True, screen_mesh_mm=SCREEN_MESH_LIMIT_MM)
        self.assertTrue(r["compliant"])

    def test_large_aperture_with_coarse_screen_noncompliant(self):
        r = check_aperture("A6", 50.0, True, screen_mesh_mm=5.0)
        self.assertFalse(r["compliant"])
        self.assertFalse(r["has_adequate_screen"])
        self.assertIn("A6", r["finding"])

    def test_large_aperture_screen_present_mesh_unspecified_noncompliant(self):
        r = check_aperture("A7", 50.0, True, screen_mesh_mm=None)
        self.assertFalse(r["compliant"])
        self.assertFalse(r["has_adequate_screen"])
        self.assertIn("A7", r["finding"])


if __name__ == "__main__":
    unittest.main()
