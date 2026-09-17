#!/usr/bin/env python3
"""Contract test for the Class 2 part and material restrictions leaf (offline)."""

import copy
import unittest

from q60_class_2_part_material_restrictions_logic import (
    AXIS_ACCEPTED,
    AXIS_INCOMPLETE,
    AXIS_MITIGATION,
    AXIS_REFUSED,
    DEFAULT_DAMP_LIFE_MARGIN,
    DEFAULT_MOISTURE_SENSITIVITY_CEILING,
    FINISHES,
    MIN_LEAD_MASS_FRACTION,
    PACKAGE_STYLES,
    PART_ACCEPTED,
    PART_INCOMPLETE,
    PART_MITIGATION,
    PART_REFUSED,
    RESTRICTED_METAL_TRACE_LIMITS,
    TIN_BEARING_FINISHES,
    WHISKER_MITIGATIONS,
    assess_finish,
    assess_packaging,
    assess_part,
    assess_restricted_metal,
    required_damp_life_hours,
    validate_material_policy,
)

HERMETIC_PART = {
    "part_reference": "u-1001",
    "package_style": "hermetic",
    "mission_humid_hours": 800.0,
    "finishes": [{"surface": "lead-frame", "material": "gold"}],
    "declared_metals": [{"metal": "magnesium", "mass_fraction": 0.004}],
}

PLASTIC_PART = {
    "part_reference": "u-1002",
    "package_style": "non-hermetic",
    "mission_humid_hours": 1000.0,
    "moisture_sensitivity_level": 2,
    "demonstrated_damp_life_hours": 2000.0,
    "finishes": [
        {"surface": "lead-frame", "material": "tin-lead", "lead_mass_fraction": 0.37}
    ],
    "declared_metals": [],
}


def _part(base, **overrides):
    part = copy.deepcopy(dict(base))
    part.update(overrides)
    return part


class PolicyTests(unittest.TestCase):
    def test_empty_policy_takes_the_defaults(self):
        settings = validate_material_policy({})
        self.assertEqual(
            settings["moisture_sensitivity_ceiling"],
            DEFAULT_MOISTURE_SENSITIVITY_CEILING,
        )
        self.assertAlmostEqual(
            settings["damp_life_margin"], DEFAULT_DAMP_LIFE_MARGIN, places=9
        )

    def test_policy_carries_the_default_trace_limits(self):
        settings = validate_material_policy({})
        self.assertEqual(
            settings["restricted_metal_trace_limits"], RESTRICTED_METAL_TRACE_LIMITS
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_material_policy("default")

    def test_moisture_ceiling_outside_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_material_policy({"moisture_sensitivity_ceiling": 9})

    def test_damp_life_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_material_policy({"damp_life_margin": 0.8})

    def test_trace_limit_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_material_policy({"restricted_metal_trace_limits": {"zinc": 1.4}})

    def test_empty_trace_limit_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_material_policy({"restricted_metal_trace_limits": {}})

    def test_barred_metals_carry_a_zero_allowance(self):
        for metal in ("cadmium", "zinc", "mercury"):
            self.assertAlmostEqual(RESTRICTED_METAL_TRACE_LIMITS[metal], 0.0, places=9)


class DampLifeTests(unittest.TestCase):
    def test_required_life_applies_the_margin(self):
        self.assertAlmostEqual(
            required_damp_life_hours(1000.0, 1.5), 1500.0, places=9
        )

    def test_unit_margin_leaves_the_hours_alone(self):
        self.assertAlmostEqual(required_damp_life_hours(640.0, 1.0), 640.0, places=9)

    def test_negative_humid_hours_rejected(self):
        with self.assertRaises(ValueError):
            required_damp_life_hours(-1.0)

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_damp_life_hours(1000.0, 0.9)


class PackagingTests(unittest.TestCase):
    def test_hermetic_case_needs_no_further_argument(self):
        result = assess_packaging(HERMETIC_PART)
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_plastic_case_with_both_numbers_accepted(self):
        result = assess_packaging(PLASTIC_PART)
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_damp_life_exactly_on_the_requirement_is_accepted(self):
        part = _part(PLASTIC_PART, demonstrated_damp_life_hours=1500.0)
        result = assess_packaging(part)
        self.assertAlmostEqual(
            result["demonstrated_damp_life_hours"],
            result["required_damp_life_hours"],
            places=9,
        )
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_short_damp_life_refused(self):
        part = _part(PLASTIC_PART, demonstrated_damp_life_hours=900.0)
        result = assess_packaging(part)
        self.assertEqual(result["verdict"], AXIS_REFUSED)
        self.assertTrue(any("damp life" in f for f in result["findings"]))

    def test_moisture_level_above_the_ceiling_refused(self):
        part = _part(PLASTIC_PART, moisture_sensitivity_level=5)
        result = assess_packaging(part)
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_plastic_case_without_numbers_is_incomplete_not_refused(self):
        part = _part(PLASTIC_PART)
        del part["demonstrated_damp_life_hours"]
        result = assess_packaging(part)
        self.assertEqual(result["verdict"], AXIS_INCOMPLETE)

    def test_unknown_package_style_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging(_part(PLASTIC_PART, package_style="potted"))

    def test_package_styles_are_the_two_the_clause_separates(self):
        self.assertEqual(set(PACKAGE_STYLES), {"hermetic", "non-hermetic"})

    def test_headroom_is_reported_in_hours(self):
        result = assess_packaging(PLASTIC_PART)
        self.assertAlmostEqual(result["damp_life_headroom_hours"], 500.0, places=9)


class FinishTests(unittest.TestCase):
    def test_gold_finish_accepted(self):
        result = assess_finish({"surface": "lead-frame", "material": "gold"})
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_leaded_tin_finish_accepted(self):
        result = assess_finish(
            {
                "surface": "lead-frame",
                "material": "tin-lead",
                "lead_mass_fraction": 0.37,
            }
        )
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_lead_exactly_on_the_threshold_accepted(self):
        result = assess_finish(
            {
                "surface": "lead-frame",
                "material": "tin-lead",
                "lead_mass_fraction": MIN_LEAD_MASS_FRACTION,
            }
        )
        self.assertAlmostEqual(
            result["lead_mass_fraction"], MIN_LEAD_MASS_FRACTION, places=9
        )
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_near_pure_tin_without_a_mitigation_refused(self):
        result = assess_finish(
            {
                "surface": "lead-frame",
                "material": "pure-tin",
                "lead_mass_fraction": 0.001,
            }
        )
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_near_pure_tin_with_an_agreed_mitigation_carried(self):
        result = assess_finish(
            {
                "surface": "lead-frame",
                "material": "pure-tin",
                "lead_mass_fraction": 0.001,
                "mitigation": "hot-solder-dip-retinning",
            }
        )
        self.assertEqual(result["verdict"], AXIS_MITIGATION)

    def test_a_mitigation_that_only_records_the_finish_refused(self):
        result = assess_finish(
            {
                "surface": "lead-frame",
                "material": "pure-tin",
                "lead_mass_fraction": 0.001,
                "mitigation": "noted-in-the-parts-list",
            }
        )
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_tin_finish_with_no_lead_figure_is_incomplete(self):
        result = assess_finish({"surface": "lead-frame", "material": "pure-tin"})
        self.assertEqual(result["verdict"], AXIS_INCOMPLETE)

    def test_cadmium_finish_refused_even_with_a_mitigation(self):
        result = assess_finish(
            {
                "surface": "case",
                "material": "cadmium",
                "mitigation": "conformal-coat-over-finish",
            }
        )
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_zinc_finish_refused(self):
        result = assess_finish({"surface": "case", "material": "zinc"})
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_unknown_finish_material_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish({"surface": "case", "material": "anodised-unobtainium"})

    def test_finish_without_a_surface_rejected(self):
        with self.assertRaises(ValueError):
            assess_finish({"surface": "  ", "material": "gold"})

    def test_every_tin_bearing_finish_is_in_the_finish_table(self):
        for material in TIN_BEARING_FINISHES:
            self.assertIn(material, FINISHES)

    def test_whisker_mitigations_are_a_closed_set(self):
        self.assertIn("hot-solder-dip-retinning", WHISKER_MITIGATIONS)
        self.assertNotIn("noted-in-the-parts-list", WHISKER_MITIGATIONS)


class RestrictedMetalTests(unittest.TestCase):
    def test_metal_inside_its_trace_allowance_accepted(self):
        result = assess_restricted_metal(
            {"metal": "magnesium", "mass_fraction": 0.010}
        )
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_metal_exactly_on_its_trace_allowance_accepted(self):
        result = assess_restricted_metal(
            {"metal": "magnesium", "mass_fraction": 0.020}
        )
        self.assertAlmostEqual(result["mass_fraction"], result["trace_limit"], places=9)
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)

    def test_metal_over_its_trace_allowance_refused(self):
        result = assess_restricted_metal(
            {"metal": "magnesium", "mass_fraction": 0.080}
        )
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_a_barred_metal_at_any_trace_refused(self):
        result = assess_restricted_metal({"metal": "cadmium", "mass_fraction": 1e-6})
        self.assertEqual(result["verdict"], AXIS_REFUSED)

    def test_an_unrestricted_metal_passes_untouched(self):
        result = assess_restricted_metal({"metal": "copper", "mass_fraction": 0.6})
        self.assertEqual(result["verdict"], AXIS_ACCEPTED)
        self.assertIsNone(result["trace_limit"])

    def test_mass_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_restricted_metal({"metal": "zinc", "mass_fraction": 1.2})

    def test_missing_mass_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_restricted_metal({"metal": "zinc"})


class PartRollupTests(unittest.TestCase):
    def test_clean_hermetic_part_accepted(self):
        result = assess_part(HERMETIC_PART)
        self.assertEqual(result["verdict"], PART_ACCEPTED)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["required_mitigations"], [])

    def test_mitigated_finish_rolls_up_to_mitigation_required(self):
        part = _part(
            PLASTIC_PART,
            finishes=[
                {
                    "surface": "lead-frame",
                    "material": "pure-tin",
                    "lead_mass_fraction": 0.002,
                    "mitigation": "hot-solder-dip-retinning",
                }
            ],
        )
        result = assess_part(part)
        self.assertEqual(result["verdict"], PART_MITIGATION)
        self.assertTrue(result["allowed"])
        self.assertEqual(len(result["required_mitigations"]), 1)

    def test_open_evidence_rolls_up_to_incomplete(self):
        part = _part(PLASTIC_PART)
        del part["moisture_sensitivity_level"]
        result = assess_part(part)
        self.assertEqual(result["verdict"], PART_INCOMPLETE)
        self.assertFalse(result["allowed"])
        self.assertIn("packaging", result["open_evidence"])

    def test_a_refusal_outranks_a_mitigation(self):
        part = _part(
            PLASTIC_PART,
            finishes=[
                {
                    "surface": "lead-frame",
                    "material": "pure-tin",
                    "lead_mass_fraction": 0.002,
                    "mitigation": "hot-solder-dip-retinning",
                },
                {"surface": "case", "material": "zinc"},
            ],
        )
        result = assess_part(part)
        self.assertEqual(result["verdict"], PART_REFUSED)
        self.assertFalse(result["allowed"])

    def test_a_refusal_outranks_open_evidence(self):
        part = _part(PLASTIC_PART, finishes=[{"surface": "case", "material": "cadmium"}])
        del part["demonstrated_damp_life_hours"]
        result = assess_part(part)
        self.assertEqual(result["verdict"], PART_REFUSED)

    def test_findings_name_the_offending_surface(self):
        part = _part(PLASTIC_PART, finishes=[{"surface": "case", "material": "zinc"}])
        result = assess_part(part)
        self.assertTrue(any("case" in finding for finding in result["findings"]))

    def test_a_surface_declared_twice_rejected(self):
        part = _part(
            PLASTIC_PART,
            finishes=[
                {"surface": "lead-frame", "material": "gold"},
                {"surface": "lead-frame", "material": "gold"},
            ],
        )
        with self.assertRaises(ValueError):
            assess_part(part)

    def test_part_without_finishes_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(HERMETIC_PART, finishes=[]))

    def test_part_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(HERMETIC_PART, part_reference=""))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_part("u-1001")

    def test_declared_metals_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_part(_part(HERMETIC_PART, declared_metals={"metal": "zinc"}))

    def test_a_tighter_project_ceiling_can_refuse_an_otherwise_clean_part(self):
        result = assess_part(PLASTIC_PART, {"moisture_sensitivity_ceiling": 1})
        self.assertEqual(result["verdict"], PART_REFUSED)


if __name__ == "__main__":
    unittest.main(verbosity=1)
