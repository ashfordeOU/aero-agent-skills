"""Contract test for the radiographic-screening-inspection leaf (stdlib unittest)."""

import math
import unittest

from q6005_radiographic_screening_inspection_logic import (
    FAIL,
    INDICATION_GROUPS,
    MATERIAL_ATTENUATION_PER_MM,
    MAX_ACTIVE_AREA_VOID_FRACTION,
    MAX_IMAGE_QUALITY_PERCENT,
    MAX_SINGLE_VOID_FRACTION,
    MAX_TOTAL_VOID_FRACTION,
    PASS,
    USABLE_TRANSMISSION_BAND,
    VIEW_REQUIREMENTS,
    assess_radiograph,
    assess_radiographic_lot,
    attenuation_coefficient,
    categorize_indication,
    check_coverage,
    check_element_placement,
    check_foreign_material,
    check_image_quality,
    check_voids,
    clearance_after_offset,
    grouped_findings,
    image_quality_percent,
    largest_void_fraction,
    particle_can_bridge,
    required_views,
    stack_thickness_mm,
    transmitted_fraction,
    validate_radiograph,
    void_area_fraction,
)

LAYERS = [("kovar-lid", 0.25), ("alumina-substrate", 0.64)]


def radiograph(unit_id="U-1", **kw):
    record = {
        "id": unit_id,
        "build_style": "single-layer-substrate",
        "layers": LAYERS,
        "views_taken": 2,
        "smallest_detail_mm": 0.015,
        "bond_area_mm2": 20.0,
        "void_areas_mm2": [1.0, 0.5],
        "void_under_active_area_mm2": 0.5,
        "particle_dimension_mm": 0.0,
        "conductor_spacing_mm": 0.20,
        "nominal_clearance_mm": 0.50,
        "element_offset_mm": 0.05,
        "minimum_clearance_mm": 0.25,
    }
    record.update(kw)
    return record


class TestViews(unittest.TestCase):
    def test_a_flat_build_owes_two_views(self):
        self.assertEqual(required_views("single-layer-substrate"), 2)

    def test_a_stacked_build_owes_more(self):
        self.assertGreater(
            required_views("stacked-assembly"), required_views("single-layer-substrate")
        )

    def test_every_build_style_is_tabulated(self):
        for name in VIEW_REQUIREMENTS:
            self.assertGreaterEqual(required_views(name), 2)

    def test_unknown_build_style_raises(self):
        with self.assertRaises(ValueError):
            required_views("mystery-stack")

    def test_too_few_views_is_a_finding(self):
        self.assertIn(
            "fewer-views-than-the-build-style-requires",
            check_coverage(radiograph("U-1", views_taken=1)),
        )

    def test_enough_views_carries_no_finding(self):
        self.assertEqual(check_coverage(radiograph()), [])


class TestAttenuation(unittest.TestCase):
    def test_thickness_is_the_sum_of_the_layers(self):
        self.assertAlmostEqual(stack_thickness_mm(LAYERS), 0.89, places=9)

    def test_transmission_follows_the_exponential_law(self):
        expected = math.exp(
            -(
                MATERIAL_ATTENUATION_PER_MM["kovar-lid"] * 0.25
                + MATERIAL_ATTENUATION_PER_MM["alumina-substrate"] * 0.64
            )
        )
        self.assertAlmostEqual(transmitted_fraction(LAYERS), expected, places=12)

    def test_a_denser_lid_passes_less_beam(self):
        self.assertLess(
            transmitted_fraction([("kovar-lid", 0.5)]),
            transmitted_fraction([("aluminium-lid", 0.5)]),
        )

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            attenuation_coefficient("depleted-handwavium")

    def test_an_empty_layer_stack_raises(self):
        with self.assertRaises(ValueError):
            transmitted_fraction([])

    def test_a_malformed_layer_raises(self):
        with self.assertRaises(ValueError):
            transmitted_fraction([("kovar-lid",)])

    def test_a_zero_thickness_layer_raises(self):
        with self.assertRaises(ValueError):
            stack_thickness_mm([("kovar-lid", 0.0)])


class TestImageQuality(unittest.TestCase):
    def test_quality_is_detail_over_thickness(self):
        self.assertAlmostEqual(
            image_quality_percent(0.015, 0.89), 100.0 * 0.015 / 0.89, places=12
        )

    def test_a_finer_detail_gives_a_smaller_percentage(self):
        self.assertLess(
            image_quality_percent(0.005, 0.89), image_quality_percent(0.015, 0.89)
        )

    def test_a_coarse_image_is_a_finding(self):
        self.assertIn(
            "image-quality-coarser-than-the-requirement",
            check_image_quality(radiograph("U-1", smallest_detail_mm=0.10)),
        )

    def test_a_quality_exactly_on_the_requirement_is_accepted(self):
        detail = MAX_IMAGE_QUALITY_PERCENT * 0.89 / 100.0
        findings = check_image_quality(radiograph("U-1", smallest_detail_mm=detail))
        self.assertNotIn("image-quality-coarser-than-the-requirement", findings)

    def test_an_opaque_stack_is_a_finding(self):
        self.assertIn(
            "beam-transmission-outside-the-usable-band",
            check_image_quality(
                radiograph("U-1", layers=[("gold-plated-copper", 2.0)])
            ),
        )

    def test_a_transparent_stack_is_a_finding(self):
        self.assertIn(
            "beam-transmission-outside-the-usable-band",
            check_image_quality(
                radiograph("U-1", layers=[("moulding-epoxy", 0.1)],
                           smallest_detail_mm=0.001)
            ),
        )

    def test_a_usable_stack_carries_no_finding(self):
        low, high = USABLE_TRANSMISSION_BAND
        transmission = transmitted_fraction(LAYERS)
        self.assertGreater(transmission, low)
        self.assertLess(transmission, high)
        self.assertEqual(check_image_quality(radiograph()), [])


class TestVoids(unittest.TestCase):
    def test_total_fraction_sums_the_voids(self):
        self.assertAlmostEqual(
            void_area_fraction([1.0, 0.5], 20.0), 0.075, places=12
        )

    def test_largest_fraction_takes_the_worst_one(self):
        self.assertAlmostEqual(largest_void_fraction([1.0, 0.5], 20.0), 0.05, places=12)

    def test_a_bond_with_no_voids_reports_zero(self):
        self.assertAlmostEqual(void_area_fraction([], 20.0), 0.0, places=12)
        self.assertAlmostEqual(largest_void_fraction([], 20.0), 0.0, places=12)

    def test_voids_larger_than_the_bond_raise(self):
        with self.assertRaises(ValueError):
            void_area_fraction([25.0], 20.0)

    def test_a_negative_void_raises(self):
        with self.assertRaises(ValueError):
            void_area_fraction([-1.0], 20.0)

    def test_total_voiding_above_the_limit_is_a_finding(self):
        areas = [MAX_TOTAL_VOID_FRACTION * 20.0 + 1.0]
        self.assertIn(
            "total-void-area-above-the-limit",
            check_voids(radiograph("U-1", void_areas_mm2=areas)),
        )

    def test_a_single_large_void_fails_a_lightly_voided_bond(self):
        areas = [MAX_SINGLE_VOID_FRACTION * 20.0 + 0.5]
        findings = check_voids(radiograph("U-1", void_areas_mm2=areas))
        self.assertNotIn("total-void-area-above-the-limit", findings)
        self.assertIn("single-void-above-the-limit", findings)

    def test_a_void_under_the_active_area_is_its_own_finding(self):
        record = radiograph(
            "U-1",
            void_areas_mm2=[1.0],
            void_under_active_area_mm2=MAX_ACTIVE_AREA_VOID_FRACTION * 20.0 + 0.5,
        )
        self.assertIn(
            "void-under-the-active-area-above-the-limit", check_voids(record)
        )

    def test_voiding_exactly_on_the_limit_is_absorbed(self):
        areas = [MAX_SINGLE_VOID_FRACTION * 20.0]
        findings = check_voids(radiograph("U-1", void_areas_mm2=areas))
        self.assertNotIn("single-void-above-the-limit", findings)

    def test_a_clean_bond_carries_no_finding(self):
        self.assertEqual(check_voids(radiograph()), [])


class TestForeignMaterial(unittest.TestCase):
    def test_a_particle_longer_than_the_spacing_bridges(self):
        self.assertTrue(particle_can_bridge(0.30, 0.20))

    def test_a_short_particle_does_not_bridge(self):
        self.assertFalse(particle_can_bridge(0.05, 0.20))

    def test_a_particle_exactly_on_the_spacing_bridges(self):
        self.assertTrue(particle_can_bridge(0.20, 0.20))

    def test_a_bridging_particle_is_a_finding(self):
        self.assertIn(
            "foreign-material-can-bridge-the-conductor-spacing",
            check_foreign_material(radiograph("U-1", particle_dimension_mm=0.30)),
        )

    def test_no_particle_carries_no_finding(self):
        self.assertEqual(check_foreign_material(radiograph()), [])

    def test_a_zero_spacing_raises(self):
        with self.assertRaises(ValueError):
            particle_can_bridge(0.30, 0.0)


class TestPlacement(unittest.TestCase):
    def test_clearance_falls_by_the_offset(self):
        self.assertAlmostEqual(clearance_after_offset(0.50, 0.05), 0.45, places=12)

    def test_a_large_offset_is_a_finding(self):
        self.assertIn(
            "element-offset-closes-the-minimum-clearance",
            check_element_placement(radiograph("U-1", element_offset_mm=0.40)),
        )

    def test_an_offset_leaving_exactly_the_minimum_is_accepted(self):
        record = radiograph("U-1", element_offset_mm=0.25)
        self.assertEqual(check_element_placement(record), [])

    def test_a_negative_offset_raises(self):
        with self.assertRaises(ValueError):
            clearance_after_offset(0.50, -0.05)


class TestIndicationGrouping(unittest.TestCase):
    def test_no_indication_groups_as_such(self):
        self.assertEqual(categorize_indication(None), "no-indication")

    def test_a_known_indication_keeps_its_group(self):
        for name in INDICATION_GROUPS:
            self.assertEqual(categorize_indication(name), name)

    def test_an_unknown_indication_raises(self):
        with self.assertRaises(ValueError):
            categorize_indication("interesting-smudge")

    def test_an_empty_indication_raises(self):
        with self.assertRaises(ValueError):
            categorize_indication("   ")


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_radiograph(["U-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_radiograph(radiograph(""))

    def test_zero_views_raises(self):
        with self.assertRaises(ValueError):
            validate_radiograph(radiograph("U-1", views_taken=0))

    def test_non_sequence_voids_raise(self):
        with self.assertRaises(ValueError):
            validate_radiograph(radiograph("U-1", void_areas_mm2=1.0))

    def test_defaults_fill_the_optional_fields(self):
        norm = validate_radiograph(
            {
                "id": "U-9",
                "build_style": "stacked-assembly",
                "layers": LAYERS,
                "views_taken": 3,
                "smallest_detail_mm": 0.01,
                "bond_area_mm2": 10.0,
                "conductor_spacing_mm": 0.2,
                "nominal_clearance_mm": 0.4,
                "minimum_clearance_mm": 0.2,
            }
        )
        self.assertEqual(norm["void_areas_mm2"], [])
        self.assertAlmostEqual(norm["particle_dimension_mm"], 0.0, places=12)


class TestAssessRadiograph(unittest.TestCase):
    def test_a_sound_radiograph_is_accepted(self):
        result = assess_radiograph(radiograph())
        self.assertEqual(result["disposition"], PASS)
        self.assertEqual(result["findings"], [])

    def test_any_finding_rejects_the_unit(self):
        result = assess_radiograph(radiograph("U-1", views_taken=1))
        self.assertEqual(result["disposition"], FAIL)

    def test_the_report_carries_the_measured_quantities(self):
        result = assess_radiograph(radiograph())
        self.assertAlmostEqual(result["stack_thickness_mm"], 0.89, places=9)
        self.assertAlmostEqual(result["total_void_fraction"], 0.075, places=12)
        self.assertAlmostEqual(result["remaining_clearance_mm"], 0.45, places=12)


class TestLot(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        report = assess_radiographic_lot([radiograph("U-1"), radiograph("U-2")])
        self.assertTrue(report["lot_accepted"])
        self.assertAlmostEqual(report["reject_fraction"], 0.0, places=12)

    def test_one_bad_unit_fails_the_lot(self):
        report = assess_radiographic_lot(
            [radiograph("U-1"), radiograph("U-2", particle_dimension_mm=0.5)]
        )
        self.assertFalse(report["lot_accepted"])
        self.assertEqual(report["rejected_ids"], ["U-2"])
        self.assertAlmostEqual(report["reject_fraction"], 0.5, places=12)

    def test_the_worst_void_fraction_is_reported(self):
        report = assess_radiographic_lot(
            [radiograph("U-1"), radiograph("U-2", void_areas_mm2=[2.0])]
        )
        self.assertAlmostEqual(report["worst_void_fraction"], 0.1, places=12)

    def test_findings_are_grouped_by_unit(self):
        grouped = grouped_findings(
            [radiograph("U-1"), radiograph("U-2", views_taken=1)]
        )
        self.assertEqual(list(grouped), ["U-2"])
        self.assertIn("fewer-views-than-the-build-style-requires", grouped["U-2"])

    def test_duplicate_unit_id_raises(self):
        with self.assertRaises(ValueError):
            assess_radiographic_lot([radiograph("U-1"), radiograph("U-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_radiographic_lot([])

    def test_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_radiographic_lot(radiograph())


if __name__ == "__main__":
    unittest.main()
