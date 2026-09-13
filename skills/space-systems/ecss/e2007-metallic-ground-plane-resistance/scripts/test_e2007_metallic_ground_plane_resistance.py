"""Gate 3 contract test for e2007-metallic-ground-plane-resistance.

Offline, deterministic, stdlib unittest only.
"""

import unittest

import e2007_metallic_ground_plane_resistance_logic as logic


def plane_baseline(**overrides):
    spec = {
        "material": "aluminium",
        "thickness_mm": 2.0,
        "temperature_c": 20.0,
        "current_path_length_mm": 2400.0,
        "current_path_width_mm": 1800.0,
        "mating_face_finish": "bare",
        "joints": [{"kind": "bolted"}, {"kind": "bolted"}],
    }
    spec.update(overrides)
    return spec


class TestResistivity(unittest.TestCase):
    def test_room_temperature_resistivity_of_aluminium(self):
        self.assertAlmostEqual(
            logic.resistivity_at_temperature("aluminium", 20.0), 2.65e-8, places=12
        )

    def test_case_and_whitespace_are_normalized(self):
        self.assertAlmostEqual(
            logic.resistivity_at_temperature("  Copper  ", 20.0), 1.68e-8, places=12
        )

    def test_resistivity_rises_with_temperature(self):
        hot = logic.resistivity_at_temperature("aluminium", 120.0)
        cold = logic.resistivity_at_temperature("aluminium", 20.0)
        self.assertGreater(hot, cold)
        self.assertAlmostEqual(hot, 3.78685e-8, places=12)

    def test_resistivity_falls_below_room_temperature(self):
        self.assertLess(
            logic.resistivity_at_temperature("copper", -40.0),
            logic.resistivity_at_temperature("copper", 20.0),
        )

    def test_unknown_material_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.resistivity_at_temperature("cardboard", 20.0)

    def test_empty_material_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.resistivity_at_temperature("", 20.0)

    def test_temperature_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.resistivity_at_temperature("aluminium", -300.0)

    def test_non_numeric_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.resistivity_at_temperature("aluminium", "warm")

    def test_temperature_driving_resistivity_non_physical_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.resistivity_at_temperature("aluminium", -260.0)


class TestSheetResistance(unittest.TestCase):
    def test_two_millimetre_aluminium_plane(self):
        self.assertAlmostEqual(
            logic.sheet_resistance_mohm_per_square("aluminium", 2.0), 0.01325, places=9
        )

    def test_thinner_plane_has_higher_sheet_resistance(self):
        self.assertGreater(
            logic.sheet_resistance_mohm_per_square("aluminium", 0.5),
            logic.sheet_resistance_mohm_per_square("aluminium", 2.0),
        )

    def test_stainless_steel_plane_is_far_more_resistive(self):
        self.assertAlmostEqual(
            logic.sheet_resistance_mohm_per_square("stainless-steel", 1.0), 0.72, places=9
        )

    def test_zero_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sheet_resistance_mohm_per_square("aluminium", 0.0)

    def test_negative_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sheet_resistance_mohm_per_square("aluminium", -1.0)

    def test_boolean_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sheet_resistance_mohm_per_square("aluminium", True)

    def test_minimum_thickness_meets_the_cap_exactly(self):
        thickness = logic.minimum_conductive_thickness_mm("aluminium")
        self.assertAlmostEqual(thickness, 0.265, places=9)
        report = logic.check_sheet_resistance("aluminium", thickness)
        self.assertTrue(report["within_cap"])

    def test_minimum_thickness_rejects_a_non_positive_cap(self):
        with self.assertRaises(ValueError):
            logic.minimum_conductive_thickness_mm("aluminium", 20.0, 0.0)

    def test_hot_plane_needs_more_thickness(self):
        self.assertGreater(
            logic.minimum_conductive_thickness_mm("aluminium", 120.0),
            logic.minimum_conductive_thickness_mm("aluminium", 20.0),
        )


class TestPathGeometry(unittest.TestCase):
    def test_squares_count_is_length_over_width(self):
        self.assertAlmostEqual(logic.squares_along_path(2400.0, 1200.0), 2.0, places=9)

    def test_square_plane_is_one_square(self):
        self.assertAlmostEqual(logic.squares_along_path(1500.0, 1500.0), 1.0, places=9)

    def test_zero_width_path_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.squares_along_path(2400.0, 0.0)

    def test_path_resistance_scales_with_squares(self):
        one = logic.path_resistance_mohm("aluminium", 2.0, 1500.0, 1500.0)
        two = logic.path_resistance_mohm("aluminium", 2.0, 3000.0, 1500.0)
        self.assertAlmostEqual(two, 2.0 * one, places=12)


class TestJointsAndChain(unittest.TestCase):
    def test_joint_kind_default_is_used(self):
        self.assertAlmostEqual(logic.joint_resistance_mohm({"kind": "welded"}), 0.05, places=9)

    def test_measured_joint_resistance_overrides_the_kind_default(self):
        self.assertAlmostEqual(
            logic.joint_resistance_mohm({"kind": "riveted", "resistance_mohm": 0.12}),
            0.12,
            places=9,
        )

    def test_unknown_joint_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.joint_resistance_mohm({"kind": "taped"})

    def test_joint_without_kind_or_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.joint_resistance_mohm({})

    def test_negative_joint_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.joint_resistance_mohm({"resistance_mohm": -0.1})

    def test_chain_sums_segments_and_joints(self):
        segments = [
            {"material": "aluminium", "thickness_mm": 2.0, "length_mm": 1500.0, "width_mm": 1500.0},
            {"material": "aluminium", "thickness_mm": 2.0, "length_mm": 1500.0, "width_mm": 1500.0},
        ]
        total = logic.chain_resistance_mohm(segments, [{"kind": "bolted"}])
        self.assertAlmostEqual(total, 2.0 * 0.01325 + 0.30, places=9)

    def test_chain_rejects_empty_segments(self):
        with self.assertRaises(ValueError):
            logic.chain_resistance_mohm([])

    def test_chain_rejects_non_sequence_joints(self):
        segments = [
            {"material": "aluminium", "thickness_mm": 2.0, "length_mm": 1500.0, "width_mm": 1500.0}
        ]
        with self.assertRaises(ValueError):
            logic.chain_resistance_mohm(segments, {"kind": "bolted"})

    def test_chain_rejects_a_non_mapping_segment(self):
        with self.assertRaises(ValueError):
            logic.chain_resistance_mohm(["aluminium"])


class TestSurfaceFinish(unittest.TestCase):
    def test_bare_face_adds_nothing(self):
        self.assertAlmostEqual(logic.finish_contact_resistance_mohm("bare"), 0.0, places=9)

    def test_conversion_coating_adds_a_small_penalty(self):
        self.assertAlmostEqual(
            logic.finish_contact_resistance_mohm("chemical-conversion"), 0.10, places=9
        )

    def test_anodized_face_is_not_conductive(self):
        self.assertIsNone(logic.finish_contact_resistance_mohm("anodized"))

    def test_painted_face_is_not_conductive(self):
        self.assertIsNone(logic.finish_contact_resistance_mohm("Painted"))

    def test_unknown_finish_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.finish_contact_resistance_mohm("shot-peened")

    def test_non_string_finish_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.finish_contact_resistance_mohm(7)


class TestAssessment(unittest.TestCase):
    def test_compliant_plane_is_clean(self):
        report = logic.assess_metallic_ground_plane(plane_baseline())
        self.assertTrue(report["compliant"])
        self.assertTrue(report["clean"])
        self.assertEqual(report["codes"], [])
        self.assertAlmostEqual(report["squares"], 4.0 / 3.0, places=9)
        self.assertAlmostEqual(report["joint_resistance_mohm"], 0.60, places=9)
        self.assertAlmostEqual(report["path_resistance_mohm"], 0.6176666666666666, places=9)

    def test_resistive_plane_breaches_the_sheet_cap(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(material="stainless-steel", thickness_mm=1.0, joints=[])
        )
        self.assertIn("MG-SHEET-CAP", report["codes"])
        self.assertFalse(report["compliant"])
        self.assertAlmostEqual(report["minimum_thickness_mm"], 7.2, places=9)

    def test_plane_at_the_minimum_thickness_passes_the_cap_with_a_margin_note(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(thickness_mm=logic.minimum_conductive_thickness_mm("aluminium"), joints=[])
        )
        self.assertNotIn("MG-SHEET-CAP", report["codes"])
        self.assertIn("MG-THICKNESS-MARGIN", report["codes"])
        self.assertTrue(report["compliant"])

    def test_anodized_mating_face_is_major(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(mating_face_finish="hard-anodized")
        )
        self.assertIn("MG-FINISH-NON-CONDUCTIVE", report["codes"])
        self.assertFalse(report["compliant"])
        self.assertAlmostEqual(report["contact_resistance_mohm"], 0.0, places=9)

    def test_plated_mating_face_adds_contact_resistance(self):
        report = logic.assess_metallic_ground_plane(plane_baseline(mating_face_finish="tin-plated"))
        self.assertAlmostEqual(report["contact_resistance_mohm"], 0.05, places=9)
        self.assertTrue(report["compliant"])

    def test_high_joint_resistance_is_major(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(joints=[{"resistance_mohm": 1.8}])
        )
        self.assertIn("MG-JOINT-CAP", report["codes"])

    def test_joint_exactly_at_the_per_joint_cap_passes(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(joints=[{"resistance_mohm": logic.MAX_JOINT_RESISTANCE_MOHM}])
        )
        self.assertNotIn("MG-JOINT-CAP", report["codes"])

    def test_long_joint_chain_breaches_the_path_cap(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(joints=[{"kind": "bond-strap"} for _ in range(5)])
        )
        self.assertIn("MG-PATH-CAP", report["codes"])
        self.assertFalse(report["compliant"])

    def test_measured_value_within_tolerance_is_clean(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(measured_sheet_resistance_mohm_per_square=0.0140)
        )
        self.assertNotIn("MG-MEASURED-DEVIATION", report["codes"])

    def test_measured_value_far_from_computed_is_minor(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(measured_sheet_resistance_mohm_per_square=0.0250)
        )
        self.assertIn("MG-MEASURED-DEVIATION", report["codes"])
        self.assertTrue(report["compliant"])

    def test_measured_value_over_the_cap_is_major(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(measured_sheet_resistance_mohm_per_square=0.40)
        )
        self.assertIn("MG-MEASURED-CAP", report["codes"])
        self.assertFalse(report["compliant"])

    def test_measured_deviation_exactly_at_tolerance_passes(self):
        # A 0.44 mm aluminium plane computes 0.06022727272727272 mohm/square;
        # a reading exactly 30% above it evaluates to 0.3000000000000001 in
        # binary floating point. The reading sits on the tolerance and has to
        # read as compliant, so the comparison absorbs the representation
        # error instead of the tolerance being widened.
        computed = 0.06022727272727272
        measured = 0.07829545454545454
        self.assertGreater(abs(measured - computed) / computed, logic.MEASURED_DEVIATION_FRACTION)
        report = logic.assess_metallic_ground_plane(
            plane_baseline(
                thickness_mm=0.44,
                joints=[],
                measured_sheet_resistance_mohm_per_square=measured,
            )
        )
        self.assertNotIn("MG-MEASURED-DEVIATION", report["codes"])
        self.assertTrue(report["clean"])

    def test_missing_thickness_is_rejected(self):
        spec = plane_baseline()
        del spec["thickness_mm"]
        with self.assertRaises(ValueError):
            logic.assess_metallic_ground_plane(spec)

    def test_non_mapping_plane_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metallic_ground_plane(["aluminium"])

    def test_non_sequence_joints_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metallic_ground_plane(plane_baseline(joints={"kind": "bolted"}))

    def test_negative_measured_value_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metallic_ground_plane(
                plane_baseline(measured_sheet_resistance_mohm_per_square=-0.01)
            )

    def test_hot_plane_is_more_resistive_than_the_same_cold_plane(self):
        hot = logic.assess_metallic_ground_plane(plane_baseline(temperature_c=125.0))
        cold = logic.assess_metallic_ground_plane(plane_baseline(temperature_c=-40.0))
        self.assertGreater(
            hot["sheet_resistance_mohm_per_square"], cold["sheet_resistance_mohm_per_square"]
        )

    def test_assessment_is_deterministic(self):
        self.assertEqual(
            logic.assess_metallic_ground_plane(plane_baseline()),
            logic.assess_metallic_ground_plane(plane_baseline()),
        )

    def test_counts_match_the_finding_list(self):
        report = logic.assess_metallic_ground_plane(
            plane_baseline(
                material="stainless-steel",
                thickness_mm=0.5,
                mating_face_finish="anodized",
                joints=[{"resistance_mohm": 2.0}],
                measured_sheet_resistance_mohm_per_square=0.05,
            )
        )
        self.assertEqual(
            report["counts"]["major"] + report["counts"]["minor"], len(report["findings"])
        )
        self.assertFalse(report["compliant"])
        for code in ("MG-SHEET-CAP", "MG-FINISH-NON-CONDUCTIVE", "MG-JOINT-CAP", "MG-PATH-CAP"):
            self.assertIn(code, report["codes"])


if __name__ == "__main__":
    unittest.main()
