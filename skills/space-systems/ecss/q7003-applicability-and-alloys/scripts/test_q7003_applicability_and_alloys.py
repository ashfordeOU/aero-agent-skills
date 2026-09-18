"""Contract test for the black-anodizing applicability leaf (stdlib unittest)."""

import unittest

from q7003_applicability_and_alloys_logic import (
    COPPER_QUALIFICATION_PERCENT,
    MAX_COATING_THICKNESS_UM,
    MIN_COATING_THICKNESS_UM,
    NOT_PERMITTED,
    OUTWARD_GROWTH_FRACTION,
    PERMITTED,
    QUALIFICATION_REQUIRED,
    SILICON_QUALIFICATION_PERCENT,
    alloy_applicability,
    assess_applicability,
    assess_part,
    dimensional_check,
    feature_growth_um,
    normalize_designation,
    outward_growth_um,
    thickness_findings,
    validate_part,
    wrought_family,
)


def part(pid="P-1", **kw):
    record = {
        "id": pid,
        "base_metal": "aluminium",
        "alloy": "6061-T6",
        "product_form": "wrought",
        "surface_condition": "bare-machined",
        "assembly_state": "single-piece",
        "surface_function": "thermal-optical-control",
        "feature": "surface",
        "coating_thickness_um": 10.0,
        "dimensional_allowance_um": 20.0,
    }
    record.update(kw)
    return record


class TestDesignationParsing(unittest.TestCase):
    def test_registry_prefix_is_stripped(self):
        self.assertEqual(normalize_designation("EN AW-6061"), "6061")
        self.assertEqual(normalize_designation("AA2024-T3"), "2024-T3")

    def test_empty_designation_raises(self):
        with self.assertRaises(ValueError):
            normalize_designation("   ")

    def test_non_string_designation_raises(self):
        with self.assertRaises(ValueError):
            normalize_designation(6061)

    def test_family_digit_is_read_from_the_number(self):
        self.assertEqual(wrought_family("6061-T6"), "6")
        self.assertEqual(wrought_family("EN AW-5083"), "5")

    def test_designation_without_four_digits_raises(self):
        with self.assertRaises(ValueError):
            wrought_family("AlMg3")


class TestAlloyApplicability(unittest.TestCase):
    def test_magnesium_and_silicon_families_are_open(self):
        verdict, reasons = alloy_applicability("6061-T6", "wrought")
        self.assertEqual(verdict, PERMITTED)
        self.assertEqual(reasons, [])

    def test_copper_bearing_family_needs_qualification(self):
        verdict, reasons = alloy_applicability("2024-T3", "wrought")
        self.assertEqual(verdict, QUALIFICATION_REQUIRED)
        self.assertIn("wrought-family-grows-a-poorly-dyeable-coating", reasons)

    def test_cast_product_form_always_needs_qualification(self):
        verdict, reasons = alloy_applicability("44300", "cast")
        self.assertEqual(verdict, QUALIFICATION_REQUIRED)
        self.assertIn("cast-alloy-porosity-needs-a-qualification-programme", reasons)

    def test_copper_content_alone_demotes_an_open_family(self):
        verdict, reasons = alloy_applicability(
            "6061-T6", "wrought", copper_percent=COPPER_QUALIFICATION_PERCENT + 0.2
        )
        self.assertEqual(verdict, QUALIFICATION_REQUIRED)
        self.assertIn("copper-content-above-the-qualification-threshold", reasons)

    def test_copper_content_on_the_threshold_stays_open(self):
        verdict, _ = alloy_applicability(
            "6061-T6", "wrought", copper_percent=COPPER_QUALIFICATION_PERCENT
        )
        self.assertEqual(verdict, PERMITTED)

    def test_silicon_content_alone_demotes_an_open_family(self):
        verdict, reasons = alloy_applicability(
            "6061-T6", "wrought", silicon_percent=SILICON_QUALIFICATION_PERCENT + 1.0
        )
        self.assertEqual(verdict, QUALIFICATION_REQUIRED)
        self.assertIn("silicon-content-above-the-qualification-threshold", reasons)

    def test_unknown_product_form_raises(self):
        with self.assertRaises(ValueError):
            alloy_applicability("6061-T6", "sintered")

    def test_negative_copper_percent_raises(self):
        with self.assertRaises(ValueError):
            alloy_applicability("6061-T6", "wrought", copper_percent=-1.0)


class TestGrowth(unittest.TestCase):
    def test_outward_growth_is_a_fraction_of_the_thickness(self):
        self.assertAlmostEqual(
            outward_growth_um(10.0), OUTWARD_GROWTH_FRACTION * 10.0, places=9
        )

    def test_outside_diameter_takes_growth_on_both_sides(self):
        self.assertAlmostEqual(
            feature_growth_um(10.0, "outside-diameter"),
            2.0 * outward_growth_um(10.0),
            places=9,
        )

    def test_a_bore_closes_instead_of_opening(self):
        self.assertLess(feature_growth_um(10.0, "bore-diameter"), 0.0)

    def test_unknown_feature_raises(self):
        with self.assertRaises(ValueError):
            feature_growth_um(10.0, "chamfer-angle")

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            outward_growth_um(-1.0)

    def test_boolean_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            outward_growth_um(True)


class TestDimensionalCheck(unittest.TestCase):
    def test_growth_inside_the_allowance_is_clean(self):
        result = dimensional_check(part(coating_thickness_um=10.0,
                                        dimensional_allowance_um=20.0))
        self.assertEqual(result["findings"], [])

    def test_growth_exactly_on_the_allowance_is_accepted(self):
        allowance = OUTWARD_GROWTH_FRACTION * 10.0
        result = dimensional_check(part(coating_thickness_um=10.0,
                                        dimensional_allowance_um=allowance))
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["growth_um"], allowance, places=9)

    def test_growth_beyond_the_allowance_is_found(self):
        result = dimensional_check(part(coating_thickness_um=20.0,
                                        dimensional_allowance_um=1.0))
        self.assertIn("coating-growth-exceeds-the-drawing-allowance",
                      result["findings"])


class TestThicknessBand(unittest.TestCase):
    def test_thickness_inside_the_band_is_clean(self):
        self.assertEqual(thickness_findings(10.0), [])

    def test_thickness_on_the_lower_bound_is_clean(self):
        self.assertEqual(thickness_findings(MIN_COATING_THICKNESS_UM), [])

    def test_thin_coating_is_flagged_as_undyeable(self):
        self.assertIn("specified-thickness-below-the-dyeable-band",
                      thickness_findings(MIN_COATING_THICKNESS_UM - 0.5))

    def test_thick_coating_is_flagged_above_the_band(self):
        self.assertIn("specified-thickness-above-the-process-band",
                      thickness_findings(MAX_COATING_THICKNESS_UM + 1.0))


class TestValidatePart(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_part({"id": "P-9"})
        self.assertEqual(norm["product_form"], "wrought")
        self.assertEqual(norm["surface_condition"], "bare-machined")
        self.assertFalse(norm["bonding_face_masked"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_part(["P-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part(""))

    def test_unknown_surface_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part(surface_condition="anodized-blue"))

    def test_unknown_assembly_state_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part(assembly_state="welded-and-sealed"))

    def test_unknown_surface_function_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part(surface_function="ornament"))

    def test_non_boolean_mask_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_part(part(bonding_face_masked="yes"))


class TestAssessPart(unittest.TestCase):
    def test_open_family_single_piece_is_permitted(self):
        result = assess_part(part())
        self.assertEqual(result["verdict"], PERMITTED)
        self.assertEqual(result["reasons"], [])

    def test_non_aluminium_base_metal_is_out(self):
        result = assess_part(part(base_metal="titanium"))
        self.assertEqual(result["verdict"], NOT_PERMITTED)
        self.assertIn("base-metal-is-not-aluminium", result["reasons"])

    def test_closed_assembly_is_out_on_entrapment(self):
        result = assess_part(part(assembly_state="closed-assembly"))
        self.assertEqual(result["verdict"], NOT_PERMITTED)
        self.assertIn("closed-assembly-traps-process-chemistry", result["reasons"])

    def test_vented_assembly_carries_a_duty_but_stays_open(self):
        result = assess_part(part(assembly_state="vented-assembly"))
        self.assertEqual(result["verdict"], PERMITTED)
        self.assertIn("vented-assembly-needs-a-drain-and-rinse-route",
                      result["duties"])

    def test_unmasked_bonding_face_is_out(self):
        result = assess_part(part(surface_function="electrical-bonding-face"))
        self.assertEqual(result["verdict"], NOT_PERMITTED)
        self.assertIn("unmasked-bonding-face-would-be-insulated", result["reasons"])

    def test_masked_bonding_face_is_open_with_a_duty(self):
        result = assess_part(
            part(surface_function="electrical-bonding-face",
                 bonding_face_masked=True)
        )
        self.assertEqual(result["verdict"], PERMITTED)
        self.assertIn("bonding-face-to-be-masked-or-the-part-is-out",
                      result["duties"])

    def test_previously_anodized_part_carries_a_strip_duty(self):
        result = assess_part(part(surface_condition="previously-anodized"))
        self.assertIn("existing-anodic-coating-to-be-stripped", result["duties"])

    def test_tolerance_overrun_overrides_an_open_alloy(self):
        result = assess_part(part(feature="outside-diameter",
                                  coating_thickness_um=20.0,
                                  dimensional_allowance_um=5.0))
        self.assertEqual(result["verdict"], NOT_PERMITTED)

    def test_thin_specification_demotes_an_open_part(self):
        result = assess_part(part(coating_thickness_um=1.0))
        self.assertEqual(result["verdict"], QUALIFICATION_REQUIRED)


class TestAssessApplicability(unittest.TestCase):
    def test_batch_groups_the_three_verdicts(self):
        report = assess_applicability([
            part("P-1"),
            part("P-2", alloy="2024-T3"),
            part("P-3", assembly_state="closed-assembly"),
        ])
        self.assertEqual(report["permitted_ids"], ["P-1"])
        self.assertEqual(report["qualification_ids"], ["P-2"])
        self.assertEqual(report["rejected_ids"], ["P-3"])
        self.assertFalse(report["batch_clear"])

    def test_all_open_parts_clear_the_batch(self):
        report = assess_applicability([part("P-1"), part("P-2")])
        self.assertTrue(report["batch_clear"])

    def test_duplicate_part_id_raises(self):
        with self.assertRaises(ValueError):
            assess_applicability([part("P-1"), part("P-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_applicability([])


if __name__ == "__main__":
    unittest.main()
