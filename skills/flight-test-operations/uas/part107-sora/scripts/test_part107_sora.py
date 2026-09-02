#!/usr/bin/env python3
"""Behavior contract test for the Part 107 / SORA risk assessment logic.

Stdlib unittest, offline, deterministic. Exercises
scripts/part107_sora_logic.py: Part 107 applicability checks, SORA
operational category from kinetic energy and population density, ground
risk class table lookup, air risk class from airspace, robustness levels
and containment, BVLOS waiver considerations, and the operational safety
case summary. Every invalid input must raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import part107_sora_logic as p107  # noqa: E402


class Part107ApplicabilityTest(unittest.TestCase):
    def test_weight_over_55lb_fails(self):
        res = p107.part107_applicable(weight_lb=60.0)
        self.assertFalse(res["applicable"])
        self.assertFalse(res["checks"]["weight"])
        self.assertTrue(any("55 lb" in w for w in res["waivers_required"]))

    def test_weight_55lb_boundary_passes(self):
        res = p107.part107_applicable(weight_lb=55.0)
        self.assertTrue(res["checks"]["weight"])
        self.assertTrue(res["applicable"])

    def test_nominal_2kg_operation_applicable(self):
        res = p107.part107_applicable(weight_lb=4.4)
        self.assertTrue(res["applicable"])
        self.assertTrue(all(res["checks"].values()))
        self.assertEqual(res["waivers_required"], [])

    def test_bvlos_fails(self):
        res = p107.part107_applicable(weight_lb=4.4, vlos=False)
        self.assertFalse(res["applicable"])
        self.assertFalse(res["checks"]["vlos"])
        self.assertTrue(any("107.31" in w for w in res["waivers_required"]))

    def test_night_ops_fail(self):
        res = p107.part107_applicable(weight_lb=4.4, daylight=False)
        self.assertFalse(res["applicable"])
        self.assertFalse(res["checks"]["daylight"])

    def test_altitude_over_400ft_fails(self):
        res = p107.part107_applicable(weight_lb=4.4, altitude_agl_ft=500.0)
        self.assertFalse(res["applicable"])
        self.assertFalse(res["checks"]["altitude"])

    def test_controlled_airspace_needs_authorization(self):
        no_auth = p107.part107_applicable(weight_lb=4.4, airspace_class="c",
                                          airspace_authorization=False)
        self.assertFalse(no_auth["applicable"])
        self.assertFalse(no_auth["checks"]["airspace"])
        with_auth = p107.part107_applicable(weight_lb=4.4, airspace_class="c",
                                            airspace_authorization=True)
        self.assertTrue(with_auth["applicable"])

    def test_class_g_needs_no_authorization(self):
        res = p107.part107_applicable(weight_lb=4.4, airspace_class="g")
        self.assertTrue(res["checks"]["airspace"])
        self.assertTrue(res["applicable"])

    def test_remote_pilot_cert_required(self):
        res = p107.part107_applicable(weight_lb=4.4, remote_pilot_cert=False)
        self.assertFalse(res["applicable"])
        self.assertFalse(res["checks"]["remote_pilot_cert"])

    def test_airspace_aliases(self):
        self.assertTrue(p107.part107_applicable(4.4, airspace_class="Class G")["applicable"])
        self.assertTrue(p107.part107_applicable(4.4, airspace_class="class-g")["applicable"])
        self.assertTrue(p107.part107_applicable(4.4, airspace_class="G")["applicable"])


class SoraOperationalCategoryTest(unittest.TestCase):
    def test_2kg_sparse_open_low_grc(self):
        res = p107.sora_operational_category(mass_kg=2.0, population_density=0.5)
        self.assertEqual(res["category"], "open")
        self.assertLessEqual(res["grc"], 3)  # low GRC
        self.assertAlmostEqual(res["ke_j"], 400.0, places=6)
        self.assertEqual(res["grc"], 3)

    def test_25kg_city_boundary_high_grc(self):
        res = p107.sora_operational_category(mass_kg=25.0, population_density=500.0)
        self.assertIn(res["category"], ("specific", "certified"))
        self.assertGreaterEqual(res["grc"], 7)  # high GRC
        self.assertGreater(res["ke_j"], 2400.0)
        self.assertEqual(res["grc"], 9)

    def test_mid_risk_is_specific(self):
        res = p107.sora_operational_category(mass_kg=10.0, population_density=50.0)
        self.assertEqual(res["category"], "specific")
        self.assertEqual(res["grc"], 6)

    def test_25kg_open_ceiling(self):
        # 25 kg at low speed over empty terrain stays inside the open
        # ceiling only while GRC stays <= 3.
        res = p107.sora_operational_category(mass_kg=25.0, population_density=0.1,
                                             speed_mps=5.0)
        # KE = 0.5*25*25 = 312.5 J -> band 108-700, density <1 -> GRC 3.
        self.assertEqual(res["grc"], 3)
        self.assertEqual(res["category"], "open")

    def test_kinetic_energy_formula(self):
        self.assertAlmostEqual(p107.kinetic_energy(2.0, 20.0), 400.0, places=9)
        self.assertAlmostEqual(p107.kinetic_energy(25.0, 20.0), 5000.0, places=9)


class GroundRiskClassTest(unittest.TestCase):
    def test_low_energy_grc1_everywhere(self):
        for density in (0.1, 5.0, 50.0, 200.0, 500.0):
            self.assertEqual(p107.ground_risk_class(5.0, density), 1)

    def test_table_spot_checks(self):
        self.assertEqual(p107.ground_risk_class(20.0, 50.0), 3)    # 7-34 J x 25-100
        self.assertEqual(p107.ground_risk_class(100.0, 10.0), 3)   # 34-108 J x 1-25
        self.assertEqual(p107.ground_risk_class(400.0, 0.5), 3)    # 108-700 J x <1
        self.assertEqual(p107.ground_risk_class(500.0, 200.0), 6)  # 108-700 J x 100-250
        self.assertEqual(p107.ground_risk_class(2000.0, 50.0), 6)  # 700-2400 J x 25-100
        self.assertEqual(p107.ground_risk_class(3000.0, 300.0), 9)  # >2400 J x >250

    def test_band_edges(self):
        self.assertEqual(p107.ground_risk_class(7.0, 1.0), 2)      # edge into 7-34 / 1-25
        self.assertEqual(p107.ground_risk_class(6.999, 0.999), 1)
        self.assertEqual(p107.ground_risk_class(2400.0, 250.0), 9)


class ArcFromAirspaceTest(unittest.TestCase):
    def test_arc_mapping(self):
        self.assertEqual(p107.arc_from_airspace("b")["arc"], "d")
        self.assertEqual(p107.arc_from_airspace("c")["arc"], "c")
        self.assertEqual(p107.arc_from_airspace("d")["arc"], "c")
        self.assertEqual(p107.arc_from_airspace("e")["arc"], "b")
        self.assertEqual(p107.arc_from_airspace("g")["arc"], "a")

    def test_altitude_escalation(self):
        self.assertEqual(p107.arc_from_airspace("g", 500.0)["arc"], "b")
        self.assertEqual(p107.arc_from_airspace("e", 500.0)["arc"], "c")
        self.assertEqual(p107.arc_from_airspace("g", 400.0)["arc"], "a")

    def test_arc_aliases(self):
        self.assertEqual(p107.arc_from_airspace("Class G")["arc"], "a")
        self.assertEqual(p107.arc_from_airspace("class-b")["arc"], "d")


class RobustnessLevelTest(unittest.TestCase):
    def test_none_no_reduction(self):
        res = p107.robustness_level(5, "none")
        self.assertEqual(res["grc_reduction"], 0)
        self.assertEqual(res["final_grc"], 5)
        self.assertFalse(res["containment_required"])

    def test_high_reduction(self):
        res = p107.robustness_level(9, "high")
        self.assertEqual(res["grc_reduction"], 3)
        self.assertEqual(res["final_grc"], 6)
        self.assertTrue(res["containment_required"])

    def test_floor_at_one(self):
        res = p107.robustness_level(2, "high")
        self.assertEqual(res["final_grc"], 1)

    def test_medium(self):
        res = p107.robustness_level(6, "medium")
        self.assertEqual(res["final_grc"], 4)
        self.assertTrue(res["containment_required"])


class BvlosWaiverTest(unittest.TestCase):
    def test_vlos_no_waiver(self):
        res = p107.bvlos_waiver_considerations(vlos=True)
        self.assertFalse(res["waiver_required"])

    def test_bvlos_requires_waiver(self):
        res = p107.bvlos_waiver_considerations(vlos=False)
        self.assertTrue(res["waiver_required"])
        self.assertIn("107.31", res["regulatory_basis"])
        self.assertGreater(len(res["considerations"]), 3)


class OpsSummaryTest(unittest.TestCase):
    def test_summary_2kg_sparse(self):
        res = p107.ops_summary(weight_lb=4.4, population_density=0.5)
        self.assertTrue(res["part107"]["applicable"])
        self.assertEqual(res["sora_category"], "open")
        self.assertEqual(res["grc"], 3)
        self.assertEqual(res["arc"], "a")
        self.assertIn("OPEN", res["summary"])
        self.assertIn("APPLICABLE", res["summary"])

    def test_summary_25kg_city_bvlos(self):
        res = p107.ops_summary(weight_lb=55.0, population_density=500.0,
                               bvlos=True, airspace_class="c",
                               airspace_authorization=True)
        self.assertTrue(res["part107"]["applicable"])
        self.assertIn(res["sora_category"], ("specific", "certified"))
        self.assertGreaterEqual(res["grc"], 7)
        self.assertEqual(res["arc"], "c")
        self.assertTrue(res["bvlos"]["waiver_required"])

    def test_summary_mass_kg_override(self):
        res = p107.ops_summary(weight_lb=10.0, mass_kg=2.0,
                               population_density=0.5)
        self.assertEqual(res["ke_j"], 400.0)
        self.assertEqual(res["sora_category"], "open")


class InvalidInputTest(unittest.TestCase):
    def test_part107_invalid(self):
        for bad in (0, -5, "heavy", None, True):
            with self.assertRaises(ValueError):
                p107.part107_applicable(weight_lb=bad)
        with self.assertRaises(ValueError):
            p107.part107_applicable(4.4, vlos="yes")
        with self.assertRaises(ValueError):
            p107.part107_applicable(4.4, daylight=1)
        with self.assertRaises(ValueError):
            p107.part107_applicable(4.4, airspace_class="z")
        with self.assertRaises(ValueError):
            p107.part107_applicable(4.4, altitude_agl_ft=-1)
        with self.assertRaises(ValueError):
            p107.part107_applicable(4.4, remote_pilot_cert="yes")

    def test_ground_risk_class_invalid(self):
        for ke, den in ((-1.0, 5.0), (100.0, -1.0), ("high", 5.0),
                        (100.0, "dense"), (True, 5.0)):
            with self.assertRaises(ValueError):
                p107.ground_risk_class(ke, den)

    def test_sora_category_invalid(self):
        for mass, den in ((0.0, 1.0), (-2.0, 1.0), ("two", 1.0), (2.0, -1.0)):
            with self.assertRaises(ValueError):
                p107.sora_operational_category(mass, den)
        with self.assertRaises(ValueError):
            p107.sora_operational_category(2.0, 1.0, speed_mps=0.0)
        with self.assertRaises(ValueError):
            p107.kinetic_energy(0.0, 5.0)

    def test_arc_invalid(self):
        for airspace in ("z", "class x", "", 7, None):
            with self.assertRaises(ValueError):
                p107.arc_from_airspace(airspace)
        with self.assertRaises(ValueError):
            p107.arc_from_airspace("g", altitude_agl_ft=-5.0)

    def test_robustness_invalid(self):
        for grc in (0, 10, 3.5, "high"):
            with self.assertRaises(ValueError):
                p107.robustness_level(grc, "none")
        with self.assertRaises(ValueError):
            p107.robustness_level(3, "extreme")
        with self.assertRaises(ValueError):
            p107.robustness_level(3, None)

    def test_bvlos_invalid(self):
        with self.assertRaises(ValueError):
            p107.bvlos_waiver_considerations(vlos="yes")

    def test_ops_summary_invalid(self):
        with self.assertRaises(ValueError):
            p107.ops_summary(weight_lb=0, population_density=0.5)
        with self.assertRaises(ValueError):
            p107.ops_summary(weight_lb=4.4, population_density=-1.0)
        with self.assertRaises(ValueError):
            p107.ops_summary(weight_lb=4.4, population_density=0.5,
                             mass_kg=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
