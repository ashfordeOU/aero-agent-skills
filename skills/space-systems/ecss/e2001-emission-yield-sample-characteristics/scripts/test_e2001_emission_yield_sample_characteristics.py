#!/usr/bin/env python3
"""Gate 3 contract test for e2001-emission-yield-sample-characteristics.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_emission_yield_sample_characteristics.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2001_emission_yield_sample_characteristics_logic import (  # noqa: E402
    DEFAULT_FINISH_TOLERANCE_FRACTION,
    DEFAULT_SHELF_LIFE_DAYS,
    GOVERNING_ATTRIBUTES,
    REQUIRED_ATTRIBUTES,
    SUPPORTING_ATTRIBUTES,
    assess_sample_representativeness,
    compare_governing_attributes,
    compare_supporting_attributes,
    coupon_area_adequate,
    finish_within_tolerance,
    normalize_attribute,
    storage_age_finding,
    surface_finish_deviation,
    validate_definition,
)


def definition(**kwargs):
    base = {
        "base_material": "aluminium-6061-t6",
        "surface_treatment": "alodine-1200-chemical-conversion",
        "production_route": "cnc-machined",
        "cleaning_process": "vapour-degrease",
        "bake_out_state": "vacuum-baked-120c-24h",
        "surface_finish_ra_um": 0.8,
    }
    base.update(kwargs)
    return base


class TestNormalizeAttribute(unittest.TestCase):
    def test_lowercases_and_trims(self):
        self.assertEqual(
            normalize_attribute("  Alodine-1200  ", "surface_treatment"),
            "alodine-1200",
        )

    def test_collapses_internal_whitespace(self):
        self.assertEqual(
            normalize_attribute("silver  plated", "surface_treatment"),
            "silver plated",
        )

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            normalize_attribute(6061, "base_material")

    def test_rejects_blank_value(self):
        with self.assertRaises(ValueError):
            normalize_attribute("   ", "cleaning_process")

    def test_rejects_none(self):
        with self.assertRaises(ValueError):
            normalize_attribute(None, "production_route")


class TestValidateDefinition(unittest.TestCase):
    def test_required_attribute_set(self):
        self.assertEqual(
            set(REQUIRED_ATTRIBUTES),
            set(GOVERNING_ATTRIBUTES) | set(SUPPORTING_ATTRIBUTES),
        )

    def test_happy_path_normalizes(self):
        out = validate_definition(definition(base_material="  ALUMINIUM-6061-T6 "), "coupon")
        self.assertEqual(out["base_material"], "aluminium-6061-t6")
        self.assertAlmostEqual(out["surface_finish_ra_um"], 0.8)

    def test_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            validate_definition(["base_material"], "coupon")

    def test_rejects_missing_attribute(self):
        incomplete = definition()
        del incomplete["cleaning_process"]
        with self.assertRaises(ValueError):
            validate_definition(incomplete, "coupon")

    def test_missing_attribute_is_not_a_match(self):
        incomplete = definition()
        del incomplete["surface_treatment"]
        with self.assertRaises(ValueError) as ctx:
            validate_definition(incomplete, "flight")
        self.assertIn("surface_treatment", str(ctx.exception))

    def test_rejects_zero_surface_finish(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(surface_finish_ra_um=0.0), "coupon")

    def test_rejects_negative_surface_finish(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(surface_finish_ra_um=-0.4), "coupon")

    def test_rejects_non_numeric_surface_finish(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(surface_finish_ra_um="smooth"), "coupon")

    def test_rejects_boolean_surface_finish(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(surface_finish_ra_um=True), "coupon")


class TestGoverningAttributes(unittest.TestCase):
    def test_identical_definitions_have_no_findings(self):
        coupon = validate_definition(definition(), "coupon")
        flight = validate_definition(definition(), "flight")
        self.assertEqual(compare_governing_attributes(coupon, flight), [])

    def test_material_mismatch_is_voiding(self):
        coupon = validate_definition(definition(base_material="titanium-6al-4v"), "coupon")
        flight = validate_definition(definition(), "flight")
        findings = compare_governing_attributes(coupon, flight)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "voiding")
        self.assertEqual(findings[0]["attribute"], "base_material")

    def test_treatment_mismatch_is_voiding(self):
        coupon = validate_definition(definition(surface_treatment="bare-alloy"), "coupon")
        flight = validate_definition(definition(), "flight")
        self.assertEqual(
            compare_governing_attributes(coupon, flight)[0]["attribute"],
            "surface_treatment",
        )

    def test_production_route_mismatch_is_voiding(self):
        coupon = validate_definition(
            definition(production_route="laser-powder-bed-fusion"), "coupon"
        )
        flight = validate_definition(definition(), "flight")
        self.assertEqual(
            compare_governing_attributes(coupon, flight)[0]["attribute"],
            "production_route",
        )

    def test_all_three_can_fail_together(self):
        coupon = validate_definition(
            definition(
                base_material="copper-c101",
                surface_treatment="bare-alloy",
                production_route="laser-powder-bed-fusion",
            ),
            "coupon",
        )
        flight = validate_definition(definition(), "flight")
        self.assertEqual(len(compare_governing_attributes(coupon, flight)), 3)

    def test_case_difference_alone_is_not_a_mismatch(self):
        coupon = validate_definition(definition(base_material="Aluminium-6061-T6"), "coupon")
        flight = validate_definition(definition(), "flight")
        self.assertEqual(compare_governing_attributes(coupon, flight), [])


class TestSurfaceFinish(unittest.TestCase):
    def test_deviation_is_fractional(self):
        self.assertAlmostEqual(surface_finish_deviation(1.2, 1.0), 0.2)

    def test_deviation_is_symmetric_in_direction(self):
        self.assertAlmostEqual(surface_finish_deviation(0.8, 1.0), 0.2)

    def test_identical_finish_has_no_deviation(self):
        self.assertAlmostEqual(surface_finish_deviation(0.8, 0.8), 0.0)

    def test_deviation_rejects_zero_flight_value(self):
        with self.assertRaises(ValueError):
            surface_finish_deviation(1.0, 0.0)

    def test_within_default_tolerance(self):
        self.assertTrue(finish_within_tolerance(0.9, 0.8))

    def test_outside_default_tolerance(self):
        self.assertFalse(finish_within_tolerance(2.0, 0.8))

    def test_exactly_at_tolerance_is_inside(self):
        self.assertTrue(
            finish_within_tolerance(1.25, 1.0, DEFAULT_FINISH_TOLERANCE_FRACTION)
        )

    def test_measured_ratio_at_tolerance_edge_is_absorbed(self):
        # abs(1.3 - 1.0) / 1.0 evaluates a few ULPs above the exact 0.30
        # allowance; that is binary representation error in a ratio of
        # measured values, not a real roughness exceedance, so the logic
        # absorbs it and the 0.30 allowance itself stays put.
        deviation = surface_finish_deviation(1.3, 1.0)
        self.assertGreater(deviation, 0.3)
        self.assertTrue(finish_within_tolerance(1.3, 1.0, 0.3))

    def test_tolerance_rejects_zero_allowance(self):
        with self.assertRaises(ValueError):
            finish_within_tolerance(1.0, 1.0, 0.0)


class TestSupportingAttributes(unittest.TestCase):
    def test_identical_definitions_have_no_findings(self):
        coupon = validate_definition(definition(), "coupon")
        flight = validate_definition(definition(), "flight")
        self.assertEqual(compare_supporting_attributes(coupon, flight), [])

    def test_cleaning_mismatch_needs_justification(self):
        coupon = validate_definition(definition(cleaning_process="solvent-wipe"), "coupon")
        flight = validate_definition(definition(), "flight")
        findings = compare_supporting_attributes(coupon, flight)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "justification-required")

    def test_bake_out_mismatch_needs_justification(self):
        coupon = validate_definition(definition(bake_out_state="not-baked"), "coupon")
        flight = validate_definition(definition(), "flight")
        self.assertEqual(
            compare_supporting_attributes(coupon, flight)[0]["attribute"],
            "bake_out_state",
        )

    def test_roughness_outside_tolerance_needs_justification(self):
        coupon = validate_definition(definition(surface_finish_ra_um=3.2), "coupon")
        flight = validate_definition(definition(), "flight")
        findings = compare_supporting_attributes(coupon, flight)
        self.assertEqual(findings[0]["attribute"], "surface_finish_ra_um")
        self.assertEqual(findings[0]["severity"], "justification-required")

    def test_roughness_inside_tolerance_raises_no_finding(self):
        coupon = validate_definition(definition(surface_finish_ra_um=0.9), "coupon")
        flight = validate_definition(definition(), "flight")
        self.assertEqual(compare_supporting_attributes(coupon, flight), [])


class TestCouponArea(unittest.TestCase):
    def test_ample_coupon_is_adequate(self):
        self.assertTrue(coupon_area_adequate(100.0, 4.0))

    def test_coupon_equal_to_footprint_is_not_adequate(self):
        self.assertFalse(coupon_area_adequate(4.0, 4.0))

    def test_exactly_at_keep_out_requirement_is_adequate(self):
        self.assertTrue(coupon_area_adequate(16.0, 4.0, 4.0))

    def test_float_product_at_keep_out_edge_is_absorbed(self):
        # 0.1 * 3 evaluates a few ULPs above 0.3; a coupon of exactly the
        # required area is adequate, and the keep-out factor is unchanged.
        self.assertGreater(0.1 * 3.0, 0.3)
        self.assertTrue(coupon_area_adequate(0.3, 0.1, 3.0))

    def test_rejects_keep_out_factor_below_one(self):
        with self.assertRaises(ValueError):
            coupon_area_adequate(100.0, 4.0, 0.5)

    def test_rejects_zero_footprint(self):
        with self.assertRaises(ValueError):
            coupon_area_adequate(100.0, 0.0)

    def test_rejects_negative_area(self):
        with self.assertRaises(ValueError):
            coupon_area_adequate(-100.0, 4.0)


class TestStorageAge(unittest.TestCase):
    def test_fresh_coupon_has_no_finding(self):
        self.assertIsNone(storage_age_finding(10.0, False))

    def test_aged_uncontrolled_coupon_has_a_finding(self):
        finding = storage_age_finding(DEFAULT_SHELF_LIFE_DAYS + 30.0, False)
        self.assertIsNotNone(finding)
        self.assertEqual(finding["severity"], "justification-required")

    def test_controlled_storage_clears_the_age(self):
        self.assertIsNone(storage_age_finding(DEFAULT_SHELF_LIFE_DAYS * 5, True))

    def test_exactly_at_shelf_life_has_no_finding(self):
        self.assertIsNone(storage_age_finding(DEFAULT_SHELF_LIFE_DAYS, False))

    def test_zero_age_is_accepted(self):
        self.assertIsNone(storage_age_finding(0, False))

    def test_rejects_negative_age(self):
        with self.assertRaises(ValueError):
            storage_age_finding(-1.0, False)

    def test_rejects_non_numeric_age(self):
        with self.assertRaises(ValueError):
            storage_age_finding("old", False)

    def test_rejects_non_boolean_storage_flag(self):
        with self.assertRaises(ValueError):
            storage_age_finding(10.0, "yes")

    def test_rejects_zero_shelf_life(self):
        with self.assertRaises(ValueError):
            storage_age_finding(10.0, False, 0.0)


class TestAssessSampleRepresentativeness(unittest.TestCase):
    def submission(self, **kwargs):
        base = {
            "coupon": definition(),
            "flight": definition(),
            "measurement_area_mm2": 400.0,
            "beam_footprint_mm2": 4.0,
            "storage_age_days": 30.0,
            "controlled_storage": False,
        }
        base.update(kwargs)
        return base

    def test_matching_coupon_is_representative(self):
        out = assess_sample_representativeness(self.submission())
        self.assertEqual(out["verdict"], "representative")
        self.assertEqual(out["findings"], [])
        self.assertTrue(out["measurement_usable"])
        self.assertAlmostEqual(out["finish_deviation"], 0.0)

    def test_material_mismatch_is_not_representative(self):
        out = assess_sample_representativeness(
            self.submission(coupon=definition(base_material="titanium-6al-4v"))
        )
        self.assertEqual(out["verdict"], "not-representative")
        self.assertEqual(len(out["voiding_findings"]), 1)
        self.assertFalse(out["measurement_usable"])

    def test_justification_cannot_close_a_voiding_finding(self):
        out = assess_sample_representativeness(
            self.submission(
                coupon=definition(base_material="titanium-6al-4v"),
                justifications={"base_material": "similar alloy family"},
            )
        )
        self.assertEqual(out["verdict"], "not-representative")

    def test_unjustified_supporting_mismatch_is_not_representative(self):
        out = assess_sample_representativeness(
            self.submission(coupon=definition(cleaning_process="solvent-wipe"))
        )
        self.assertEqual(out["verdict"], "not-representative")
        self.assertEqual(len(out["unjustified_findings"]), 1)

    def test_justified_supporting_mismatch_is_conditional(self):
        out = assess_sample_representativeness(
            self.submission(
                coupon=definition(cleaning_process="solvent-wipe"),
                justifications={"cleaning_process": "process equivalence report R-12"},
            )
        )
        self.assertEqual(out["verdict"], "conditionally-representative")
        self.assertTrue(out["measurement_usable"])
        self.assertEqual(out["unjustified_findings"], [])

    def test_blank_justification_does_not_close_a_finding(self):
        out = assess_sample_representativeness(
            self.submission(
                coupon=definition(cleaning_process="solvent-wipe"),
                justifications={"cleaning_process": "   "},
            )
        )
        self.assertEqual(out["verdict"], "not-representative")

    def test_undersized_coupon_is_voiding(self):
        out = assess_sample_representativeness(
            self.submission(measurement_area_mm2=6.0, beam_footprint_mm2=4.0)
        )
        self.assertEqual(out["verdict"], "not-representative")
        self.assertTrue(
            any(f["attribute"] == "measurement_area_mm2" for f in out["voiding_findings"])
        )

    def test_aged_coupon_with_justification_is_conditional(self):
        out = assess_sample_representativeness(
            self.submission(
                storage_age_days=DEFAULT_SHELF_LIFE_DAYS + 60.0,
                justifications={"storage_age_days": "re-inspected, nitrogen cabinet"},
            )
        )
        self.assertEqual(out["verdict"], "conditionally-representative")

    def test_controlled_storage_keeps_an_old_coupon_representative(self):
        out = assess_sample_representativeness(
            self.submission(
                storage_age_days=DEFAULT_SHELF_LIFE_DAYS * 3, controlled_storage=True
            )
        )
        self.assertEqual(out["verdict"], "representative")

    def test_custom_tolerance_tightens_the_finish_check(self):
        loose = assess_sample_representativeness(
            self.submission(coupon=definition(surface_finish_ra_um=0.9))
        )
        tight = assess_sample_representativeness(
            self.submission(
                coupon=definition(surface_finish_ra_um=0.9), tolerance_fraction=0.05
            )
        )
        self.assertEqual(loose["verdict"], "representative")
        self.assertEqual(tight["verdict"], "not-representative")

    def test_findings_carry_both_severities(self):
        out = assess_sample_representativeness(
            self.submission(
                coupon=definition(
                    base_material="copper-c101", cleaning_process="solvent-wipe"
                )
            )
        )
        self.assertEqual(len(out["voiding_findings"]), 1)
        self.assertEqual(len(out["justification_required_findings"]), 1)

    def test_rejects_non_mapping_submission(self):
        with self.assertRaises(ValueError):
            assess_sample_representativeness("coupon")

    def test_rejects_missing_submission_key(self):
        payload = self.submission()
        del payload["beam_footprint_mm2"]
        with self.assertRaises(ValueError):
            assess_sample_representativeness(payload)

    def test_rejects_incomplete_flight_definition(self):
        incomplete = definition()
        del incomplete["production_route"]
        with self.assertRaises(ValueError):
            assess_sample_representativeness(self.submission(flight=incomplete))

    def test_rejects_non_mapping_justifications(self):
        with self.assertRaises(ValueError):
            assess_sample_representativeness(
                self.submission(justifications=["cleaning_process"])
            )

    def test_rejects_zero_tolerance_fraction(self):
        with self.assertRaises(ValueError):
            assess_sample_representativeness(self.submission(tolerance_fraction=0.0))

    def test_rejects_invalid_keep_out_factor(self):
        with self.assertRaises(ValueError):
            assess_sample_representativeness(self.submission(keep_out_factor=0.2))


if __name__ == "__main__":
    unittest.main()
