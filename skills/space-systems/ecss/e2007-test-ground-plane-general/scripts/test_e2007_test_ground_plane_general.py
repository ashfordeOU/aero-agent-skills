"""Gate 3 contract test for e2007-test-ground-plane-general.

Offline, deterministic, stdlib unittest only.
"""

import unittest

import e2007_test_ground_plane_general_logic as logic


def flight_baseline(**overrides):
    spec = {
        "arrangement_known": True,
        "panel_material": "aluminium",
        "interface_kind": "hard-mounted",
        "bond_points": 4,
    }
    spec.update(overrides)
    return spec


def setup_baseline(**overrides):
    spec = {
        "plane_material": "aluminium",
        "plane_length_mm": 2400.0,
        "plane_width_mm": 1800.0,
        "unit_length_mm": 400.0,
        "unit_width_mm": 300.0,
        "front_setback_mm": 100.0,
        "interface_kind": "hard-mounted",
        "bond_points": 4,
        "bond_resistance_mohm": 1.0,
    }
    spec.update(overrides)
    return spec


class TestPrimitives(unittest.TestCase):
    def test_resolve_family_metallic(self):
        self.assertEqual(logic.resolve_plane_family("Aluminium"), "metallic")

    def test_resolve_family_composite(self):
        self.assertEqual(logic.resolve_plane_family("cfrp-honeycomb"), "composite")

    def test_resolve_family_dielectric(self):
        self.assertEqual(logic.resolve_plane_family("gfrp"), "dielectric")

    def test_resolve_family_rejects_unknown_material(self):
        with self.assertRaises(ValueError):
            logic.resolve_plane_family("unobtanium-sheet")

    def test_resolve_family_rejects_empty_material(self):
        with self.assertRaises(ValueError):
            logic.resolve_plane_family("   ")

    def test_normalize_interface_kind_trims_and_lowers(self):
        self.assertEqual(logic.normalize_interface_kind("  Isolator-Mounted "), "isolator-mounted")

    def test_normalize_interface_kind_rejects_unknown(self):
        with self.assertRaises(ValueError):
            logic.normalize_interface_kind("glued")

    def test_plane_area_conversion(self):
        self.assertAlmostEqual(logic.plane_area_m2(1500.0, 1500.0), 2.25, places=9)

    def test_plane_area_rejects_zero_edge(self):
        with self.assertRaises(ValueError):
            logic.plane_area_m2(0.0, 1500.0)

    def test_plane_area_rejects_non_numeric_edge(self):
        with self.assertRaises(ValueError):
            logic.plane_area_m2("1500", 1500.0)

    def test_side_extension_is_symmetric_half(self):
        self.assertAlmostEqual(logic.side_extension_mm(1800.0, 800.0), 500.0, places=9)

    def test_side_extension_rejects_unit_wider_than_plane(self):
        with self.assertRaises(ValueError):
            logic.side_extension_mm(600.0, 900.0)

    def test_series_bond_resistance_sums_chain(self):
        self.assertAlmostEqual(
            logic.series_bond_resistance_mohm([0.4, 0.5, 0.3]), 1.2, places=9
        )

    def test_series_bond_resistance_rejects_empty_chain(self):
        with self.assertRaises(ValueError):
            logic.series_bond_resistance_mohm([])

    def test_series_bond_resistance_rejects_negative_segment(self):
        with self.assertRaises(ValueError):
            logic.series_bond_resistance_mohm([0.4, -0.1])

    def test_series_bond_resistance_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            logic.series_bond_resistance_mohm(0.4)


class TestInstallationKnowledge(unittest.TestCase):
    def test_known_arrangement_is_clean(self):
        self.assertEqual(logic.check_installation_knowledge(flight_baseline()), [])

    def test_unknown_arrangement_is_major(self):
        findings = logic.check_installation_knowledge(
            flight_baseline(arrangement_known=False)
        )
        self.assertEqual([f["code"] for f in findings], ["GP-ARRANGEMENT-UNKNOWN"])
        self.assertEqual(findings[0]["severity"], "major")

    def test_declared_worst_case_downgrades_to_minor(self):
        findings = logic.check_installation_knowledge(
            flight_baseline(arrangement_known=False, worst_case_declared=True)
        )
        self.assertEqual([f["code"] for f in findings], ["GP-ARRANGEMENT-BOUNDED"])
        self.assertEqual(findings[0]["severity"], "minor")

    def test_non_boolean_known_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_installation_knowledge(flight_baseline(arrangement_known="yes"))

    def test_non_mapping_flight_installation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_installation_knowledge(["arrangement_known"])


class TestPlaneGeometry(unittest.TestCase):
    def test_compliant_plane_has_no_geometry_finding(self):
        self.assertEqual(logic.check_plane_geometry(setup_baseline()), [])

    def test_small_plane_flags_area_and_edge(self):
        codes = [
            f["code"]
            for f in logic.check_plane_geometry(
                setup_baseline(plane_length_mm=700.0, plane_width_mm=700.0)
            )
        ]
        self.assertIn("GP-AREA", codes)
        self.assertIn("GP-EDGE", codes)

    def test_area_exactly_at_floor_passes(self):
        codes = [
            f["code"]
            for f in logic.check_plane_geometry(
                setup_baseline(plane_length_mm=2500.0, plane_width_mm=900.0, unit_width_mm=300.0)
            )
        ]
        self.assertNotIn("GP-AREA", codes)

    def test_narrow_plane_flags_lateral_extension(self):
        codes = [
            f["code"]
            for f in logic.check_plane_geometry(
                setup_baseline(plane_width_mm=1000.0, unit_width_mm=900.0)
            )
        ]
        self.assertIn("GP-EXTENT", codes)

    def test_lateral_extension_exactly_at_floor_passes(self):
        codes = [
            f["code"]
            for f in logic.check_plane_geometry(
                setup_baseline(plane_width_mm=1800.0, unit_width_mm=800.0)
            )
        ]
        self.assertNotIn("GP-EXTENT", codes)

    def test_setback_within_tolerance_passes(self):
        codes = [
            f["code"] for f in logic.check_plane_geometry(setup_baseline(front_setback_mm=120.0))
        ]
        self.assertNotIn("GP-SETBACK", codes)

    def test_setback_outside_tolerance_is_minor(self):
        findings = logic.check_plane_geometry(setup_baseline(front_setback_mm=250.0))
        self.assertEqual([f["code"] for f in findings], ["GP-SETBACK"])
        self.assertEqual(findings[0]["severity"], "minor")

    def test_missing_plane_dimension_is_rejected(self):
        spec = setup_baseline()
        del spec["plane_width_mm"]
        with self.assertRaises(ValueError):
            logic.check_plane_geometry(spec)

    def test_negative_setback_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_plane_geometry(setup_baseline(front_setback_mm=-5.0))


class TestMaterialRepresentativeness(unittest.TestCase):
    def test_identical_material_is_clean(self):
        self.assertEqual(
            logic.check_material_representativeness(flight_baseline(), setup_baseline()), []
        )

    def test_same_family_other_grade_is_minor(self):
        findings = logic.check_material_representativeness(
            flight_baseline(panel_material="magnesium"), setup_baseline()
        )
        self.assertEqual([f["code"] for f in findings], ["GP-MATERIAL-GRADE"])
        self.assertEqual(findings[0]["severity"], "minor")

    def test_family_mismatch_is_major(self):
        findings = logic.check_material_representativeness(
            flight_baseline(panel_material="cfrp"), setup_baseline()
        )
        self.assertEqual([f["code"] for f in findings], ["GP-MATERIAL-FAMILY"])
        self.assertEqual(findings[0]["severity"], "major")

    def test_unknown_test_plane_material_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_material_representativeness(
                flight_baseline(), setup_baseline(plane_material="plywood")
            )


class TestBondRepresentativeness(unittest.TestCase):
    def test_compliant_bonding_is_clean(self):
        self.assertEqual(
            logic.check_bond_representativeness(flight_baseline(), setup_baseline()), []
        )

    def test_single_bond_point_is_major(self):
        codes = [
            f["code"]
            for f in logic.check_bond_representativeness(
                flight_baseline(), setup_baseline(bond_points=1)
            )
        ]
        self.assertIn("GP-BOND-POINTS", codes)

    def test_high_bond_resistance_is_major(self):
        findings = logic.check_bond_representativeness(
            flight_baseline(), setup_baseline(bond_resistance_mohm=4.0)
        )
        self.assertEqual([f["code"] for f in findings], ["GP-BOND-RESISTANCE"])
        self.assertEqual(findings[0]["severity"], "major")

    def test_bond_chain_exactly_at_cap_passes(self):
        # 0.8 + 0.9 + 0.8 sums a few ULPs above 2.5 in binary floating point;
        # the chain is physically at the cap and has to read as compliant.
        spec = setup_baseline()
        spec.pop("bond_resistance_mohm")
        spec["bond_segments_mohm"] = [0.8, 0.9, 0.8]
        self.assertEqual(logic.check_bond_representativeness(flight_baseline(), spec), [])

    def test_fewer_bond_points_than_flight_is_minor(self):
        findings = logic.check_bond_representativeness(
            flight_baseline(bond_points=6), setup_baseline(bond_points=2)
        )
        self.assertEqual([f["code"] for f in findings], ["GP-BOND-UNDER-REPRESENTED"])

    def test_non_integer_bond_point_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_bond_representativeness(
                flight_baseline(), setup_baseline(bond_points=2.5)
            )

    def test_negative_bond_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_bond_representativeness(
                flight_baseline(), setup_baseline(bond_resistance_mohm=-0.2)
            )


class TestIsolatorRepresentation(unittest.TestCase):
    def test_matching_interface_is_clean(self):
        self.assertEqual(
            logic.check_isolator_representation(flight_baseline(), setup_baseline()), []
        )

    def test_missing_isolator_is_major(self):
        findings = logic.check_isolator_representation(
            flight_baseline(interface_kind="isolator-mounted"), setup_baseline()
        )
        self.assertEqual([f["code"] for f in findings], ["GP-ISOLATOR-MISSING"])
        self.assertEqual(findings[0]["severity"], "major")

    def test_added_isolator_is_major(self):
        findings = logic.check_isolator_representation(
            flight_baseline(), setup_baseline(interface_kind="isolator-mounted")
        )
        self.assertEqual([f["code"] for f in findings], ["GP-ISOLATOR-ADDED"])

    def test_stand_off_substitution_is_minor(self):
        findings = logic.check_isolator_representation(
            flight_baseline(interface_kind="stand-off-mounted"), setup_baseline()
        )
        self.assertEqual([f["code"] for f in findings], ["GP-INTERFACE-DEVIATION"])
        self.assertEqual(findings[0]["severity"], "minor")

    def test_missing_interface_kind_is_rejected(self):
        spec = setup_baseline()
        del spec["interface_kind"]
        with self.assertRaises(ValueError):
            logic.check_isolator_representation(flight_baseline(), spec)


class TestSummaryAndAssessment(unittest.TestCase):
    def test_summarize_counts_by_severity(self):
        findings = [
            {"code": "A", "severity": "major", "detail": ""},
            {"code": "B", "severity": "minor", "detail": ""},
            {"code": "C", "severity": "minor", "detail": ""},
        ]
        self.assertEqual(logic.summarize_findings(findings), {"major": 1, "minor": 2})

    def test_summarize_rejects_unknown_severity(self):
        with self.assertRaises(ValueError):
            logic.summarize_findings([{"code": "A", "severity": "critical", "detail": ""}])

    def test_summarize_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            logic.summarize_findings({"code": "A"})

    def test_representative_setup_is_fully_representative(self):
        report = logic.assess_test_ground_plane(flight_baseline(), setup_baseline())
        self.assertTrue(report["compliant"])
        self.assertTrue(report["fully_representative"])
        self.assertEqual(report["codes"], [])
        self.assertAlmostEqual(report["plane_area_m2"], 4.32, places=9)
        self.assertAlmostEqual(report["lateral_extension_mm"], 750.0, places=9)

    def test_minor_only_setup_is_compliant_but_not_fully_representative(self):
        report = logic.assess_test_ground_plane(
            flight_baseline(panel_material="magnesium"), setup_baseline()
        )
        self.assertTrue(report["compliant"])
        self.assertFalse(report["fully_representative"])
        self.assertEqual(report["counts"], {"major": 0, "minor": 1})

    def test_multiple_defects_aggregate_into_one_report(self):
        report = logic.assess_test_ground_plane(
            flight_baseline(arrangement_known=False, interface_kind="isolator-mounted"),
            setup_baseline(
                plane_length_mm=900.0,
                plane_width_mm=700.0,
                unit_width_mm=600.0,
                plane_material="cfrp",
                bond_points=1,
                bond_resistance_mohm=9.0,
            ),
        )
        self.assertFalse(report["compliant"])
        for code in (
            "GP-ARRANGEMENT-UNKNOWN",
            "GP-AREA",
            "GP-EDGE",
            "GP-EXTENT",
            "GP-MATERIAL-FAMILY",
            "GP-BOND-POINTS",
            "GP-BOND-RESISTANCE",
            "GP-ISOLATOR-MISSING",
        ):
            self.assertIn(code, report["codes"])
        self.assertGreaterEqual(report["counts"]["major"], 8)

    def test_assessment_rejects_non_mapping_setup(self):
        with self.assertRaises(ValueError):
            logic.assess_test_ground_plane(flight_baseline(), "plane")

    def test_assessment_is_deterministic(self):
        first = logic.assess_test_ground_plane(flight_baseline(), setup_baseline())
        second = logic.assess_test_ground_plane(flight_baseline(), setup_baseline())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
