#!/usr/bin/env python3
"""Gate 3 contract test for e2006-surface-material-control-applicability."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2006_surface_material_control_applicability_logic import (  # noqa: E402
    BLEED_PATH_RESISTANCE_CEILING_OHM,
    EXPOSURE_CATEGORIES,
    ORBIT_REGIME_SEVERITY,
    REQUIREMENT_LEVELS,
    SURFACE_RESISTIVITY_CEILING_OHM_PER_SQUARE,
    assess_inventory,
    assess_item,
    at_or_below_ceiling,
    bleed_path_resistance,
    categorize_exposure,
    regime_severity,
    required_volume_resistivity,
    requirement_level,
    screen_surface,
)


def good_item(**over):
    item = {
        "name": "radiator-panel-outer-coating",
        "outer_material": "conductive-white-paint",
        "external": True,
        "shield_coverage_fraction": 0.0,
        "ambient_plasma_view": True,
        "surface_resistivity_ohm_per_square": 1.0e7,
        "volume_resistivity_ohm_m": 1.0e5,
        "thickness_m": 1.0e-4,
        "contact_area_m2": 1.0e-2,
        "bonded_to_structure_ground": True,
    }
    item.update(over)
    return item


class TestRegimeSeverity(unittest.TestCase):
    def test_geostationary_orbit_is_severe(self):
        self.assertEqual(regime_severity("geostationary-orbit"), 4)

    def test_equatorial_low_earth_orbit_is_mild(self):
        self.assertEqual(regime_severity("equatorial-low-earth-orbit"), 1)

    def test_polar_low_earth_orbit_outranks_equatorial(self):
        self.assertGreater(
            regime_severity("polar-low-earth-orbit"),
            regime_severity("equatorial-low-earth-orbit"),
        )

    def test_regime_lookup_is_case_and_space_insensitive(self):
        self.assertEqual(regime_severity("  Geostationary-Orbit "), 4)

    def test_every_mapped_regime_ranks_within_one_to_four(self):
        for regime, rank in ORBIT_REGIME_SEVERITY.items():
            self.assertIn(rank, (1, 2, 3, 4), regime)

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            regime_severity("selenocentric-orbit")

    def test_blank_regime_raises(self):
        with self.assertRaises(ValueError):
            regime_severity("   ")

    def test_non_string_regime_raises(self):
        with self.assertRaises(ValueError):
            regime_severity(4)


class TestExposureCategory(unittest.TestCase):
    def test_uncovered_external_item_is_plasma_exposed(self):
        self.assertEqual(categorize_exposure(good_item()), "plasma-exposed")

    def test_partially_covered_item_is_partially_shielded(self):
        self.assertEqual(
            categorize_exposure(good_item(shield_coverage_fraction=0.4)),
            "partially-shielded",
        )

    def test_fully_covered_item_is_internal(self):
        self.assertEqual(
            categorize_exposure(good_item(shield_coverage_fraction=1.0)), "internal"
        )

    def test_non_external_item_is_internal(self):
        self.assertEqual(categorize_exposure({"external": False}), "internal")

    def test_external_item_without_ambient_view_is_internal(self):
        self.assertEqual(
            categorize_exposure(good_item(ambient_plasma_view=False)), "internal"
        )

    def test_every_category_is_a_declared_category(self):
        for item in (
            good_item(),
            good_item(shield_coverage_fraction=0.5),
            good_item(shield_coverage_fraction=1.0),
        ):
            self.assertIn(categorize_exposure(item), EXPOSURE_CATEGORIES)

    def test_missing_external_flag_raises(self):
        with self.assertRaises(ValueError):
            categorize_exposure({"name": "strut"})

    def test_missing_coverage_fraction_raises(self):
        item = good_item()
        del item["shield_coverage_fraction"]
        with self.assertRaises(ValueError):
            categorize_exposure(item)

    def test_coverage_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            categorize_exposure(good_item(shield_coverage_fraction=1.2))

    def test_negative_coverage_fraction_raises(self):
        with self.assertRaises(ValueError):
            categorize_exposure(good_item(shield_coverage_fraction=-0.01))

    def test_non_numeric_coverage_fraction_raises(self):
        with self.assertRaises(ValueError):
            categorize_exposure(good_item(shield_coverage_fraction="half"))

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            categorize_exposure(["external"])


class TestRequirementLevel(unittest.TestCase):
    def test_plasma_exposed_in_severe_regime_is_full(self):
        self.assertEqual(requirement_level("plasma-exposed", 4), "full")

    def test_plasma_exposed_in_intermediate_regime_is_full(self):
        self.assertEqual(requirement_level("plasma-exposed", 3), "full")

    def test_plasma_exposed_in_mild_regime_is_reduced(self):
        self.assertEqual(requirement_level("plasma-exposed", 1), "reduced")

    def test_partially_shielded_is_always_reduced(self):
        for rank in (1, 2, 3, 4):
            self.assertEqual(requirement_level("partially-shielded", rank), "reduced")

    def test_internal_item_carries_no_requirement(self):
        self.assertEqual(requirement_level("internal", 4), "none")

    def test_levels_are_declared_levels(self):
        self.assertIn(requirement_level("plasma-exposed", 2), REQUIREMENT_LEVELS)

    def test_unknown_exposure_category_raises(self):
        with self.assertRaises(ValueError):
            requirement_level("buried", 3)

    def test_out_of_range_severity_raises(self):
        with self.assertRaises(ValueError):
            requirement_level("plasma-exposed", 5)

    def test_boolean_severity_raises(self):
        with self.assertRaises(ValueError):
            requirement_level("plasma-exposed", True)


class TestBleedPath(unittest.TestCase):
    def test_resistance_follows_rho_times_t_over_area(self):
        self.assertAlmostEqual(
            bleed_path_resistance(1.0e5, 1.0e-4, 1.0e-2), 1.0e3, places=6
        )

    def test_resistance_scales_linearly_with_thickness(self):
        r1 = bleed_path_resistance(1.0e6, 1.0e-4, 2.0e-3)
        r2 = bleed_path_resistance(1.0e6, 2.0e-4, 2.0e-3)
        self.assertAlmostEqual(r2 / r1, 2.0, places=9)

    def test_required_volume_resistivity_inverts_the_resistance(self):
        rho = required_volume_resistivity(1.0e9, 2.5e-4, 3.0e-3)
        self.assertAlmostEqual(
            bleed_path_resistance(rho, 2.5e-4, 3.0e-3), 1.0e9, delta=1.0
        )

    def test_zero_contact_area_raises(self):
        with self.assertRaises(ValueError):
            bleed_path_resistance(1.0e6, 1.0e-4, 0.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            bleed_path_resistance(1.0e6, -1.0e-4, 1.0e-2)

    def test_non_finite_resistivity_raises(self):
        with self.assertRaises(ValueError):
            bleed_path_resistance(float("inf"), 1.0e-4, 1.0e-2)

    def test_non_numeric_resistivity_raises(self):
        with self.assertRaises(ValueError):
            bleed_path_resistance("conductive", 1.0e-4, 1.0e-2)

    def test_required_volume_resistivity_rejects_zero_target(self):
        with self.assertRaises(ValueError):
            required_volume_resistivity(0.0, 1.0e-4, 1.0e-2)


class TestCeilingComparison(unittest.TestCase):
    def test_value_below_ceiling_passes(self):
        self.assertTrue(at_or_below_ceiling(9.0e8, 1.0e9))

    def test_value_above_ceiling_fails(self):
        self.assertFalse(at_or_below_ceiling(2.0e9, 1.0e9))

    def test_exact_ceiling_passes_despite_representation_error(self):
        # rho * t / A lands a few ULPs over the ceiling for these inputs.
        value = bleed_path_resistance(1.0e9, 3.0e-4, 3.0e-4)
        self.assertTrue(at_or_below_ceiling(value, BLEED_PATH_RESISTANCE_CEILING_OHM))
        self.assertAlmostEqual(value / BLEED_PATH_RESISTANCE_CEILING_OHM, 1.0, places=9)

    def test_ceiling_itself_is_not_widened(self):
        just_over = BLEED_PATH_RESISTANCE_CEILING_OHM * 1.001
        self.assertFalse(at_or_below_ceiling(just_over, BLEED_PATH_RESISTANCE_CEILING_OHM))

    def test_non_finite_value_raises(self):
        with self.assertRaises(ValueError):
            at_or_below_ceiling(float("nan"), 1.0e9)


class TestScreening(unittest.TestCase):
    def test_controlled_surface_has_no_findings(self):
        self.assertEqual(screen_surface(good_item()), [])

    def test_high_surface_resistivity_is_a_finding(self):
        findings = screen_surface(
            good_item(surface_resistivity_ohm_per_square=1.0e14)
        )
        self.assertTrue(any("surface-resistivity" in f for f in findings))

    def test_surface_resistivity_exactly_at_ceiling_passes(self):
        findings = screen_surface(
            good_item(
                surface_resistivity_ohm_per_square=SURFACE_RESISTIVITY_CEILING_OHM_PER_SQUARE
            )
        )
        self.assertEqual(findings, [])

    def test_absent_surface_resistivity_is_its_own_finding(self):
        item = good_item()
        del item["surface_resistivity_ohm_per_square"]
        findings = screen_surface(item)
        self.assertTrue(any("not on record" in f for f in findings))

    def test_incomplete_bleed_path_data_is_a_finding(self):
        item = good_item()
        del item["contact_area_m2"]
        findings = screen_surface(item)
        self.assertTrue(any("bleed-path data incomplete" in f for f in findings))

    def test_high_bleed_path_resistance_is_a_finding(self):
        findings = screen_surface(
            good_item(volume_resistivity_ohm_m=1.0e14, thickness_m=1.0e-3)
        )
        self.assertTrue(any("bleed-path resistance" in f for f in findings))

    def test_missing_structure_ground_bond_is_a_finding(self):
        findings = screen_surface(good_item(bonded_to_structure_ground=False))
        self.assertTrue(any("structure-ground" in f for f in findings))

    def test_two_failure_modes_produce_two_separate_findings(self):
        findings = screen_surface(
            good_item(
                surface_resistivity_ohm_per_square=1.0e15,
                bonded_to_structure_ground=False,
            )
        )
        self.assertEqual(len(findings), 2)


class TestAssessItem(unittest.TestCase):
    def test_exposed_controlled_item_is_applicable_and_clean(self):
        result = assess_item(good_item(), "geostationary-orbit")
        self.assertTrue(result["applicable"])
        self.assertEqual(result["requirement_level"], "full")
        self.assertEqual(result["surface_category"], "controlled-conductive")
        self.assertEqual(result["findings"], [])

    def test_exposed_insulating_item_is_a_floating_dielectric_surface(self):
        result = assess_item(
            good_item(surface_resistivity_ohm_per_square=1.0e16),
            "geostationary-orbit",
        )
        self.assertEqual(result["surface_category"], "floating-dielectric")
        self.assertTrue(result["findings"])

    def test_internal_item_is_out_of_scope_not_compliant(self):
        result = assess_item(
            good_item(external=False, name="harness-bracket"), "geostationary-orbit"
        )
        self.assertFalse(result["applicable"])
        self.assertEqual(result["surface_category"], "out-of-scope")
        self.assertEqual(result["requirement_level"], "none")

    def test_internal_item_is_not_screened(self):
        result = assess_item(
            good_item(
                external=False,
                name="inner-panel",
                surface_resistivity_ohm_per_square=1.0e18,
            ),
            "geostationary-orbit",
        )
        self.assertEqual(result["findings"], [])

    def test_mild_regime_downgrades_an_exposed_item_to_reduced(self):
        result = assess_item(good_item(), "equatorial-low-earth-orbit")
        self.assertEqual(result["requirement_level"], "reduced")

    def test_item_without_name_raises(self):
        item = good_item()
        del item["name"]
        with self.assertRaises(ValueError):
            assess_item(item, "geostationary-orbit")

    def test_item_without_outer_material_raises(self):
        with self.assertRaises(ValueError):
            assess_item(good_item(outer_material=""), "geostationary-orbit")

    def test_item_with_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            assess_item(good_item(), "halo-orbit")

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            assess_item("radiator", "geostationary-orbit")


class TestAssessInventory(unittest.TestCase):
    def setUp(self):
        self.items = [
            good_item(),
            good_item(name="mli-outer-layer", shield_coverage_fraction=0.3),
            good_item(name="inner-shelf", external=False),
            good_item(
                name="optical-solar-reflector",
                surface_resistivity_ohm_per_square=1.0e15,
            ),
        ]

    def test_counts_split_in_scope_and_out_of_scope(self):
        summary = assess_inventory(self.items, "geostationary-orbit")
        self.assertEqual(summary["item_count"], 4)
        self.assertEqual(summary["in_scope_count"], 3)
        self.assertEqual(summary["out_of_scope_count"], 1)

    def test_requirement_levels_are_counted(self):
        summary = assess_inventory(self.items, "geostationary-orbit")
        self.assertEqual(summary["full_level_count"], 2)
        self.assertEqual(summary["reduced_level_count"], 1)

    def test_inventory_with_a_finding_is_not_complete(self):
        summary = assess_inventory(self.items, "geostationary-orbit")
        self.assertFalse(summary["applicability_complete"])
        self.assertTrue(summary["open_findings"])

    def test_clean_inventory_is_complete(self):
        summary = assess_inventory(
            [good_item(), good_item(name="second-panel")], "medium-earth-orbit"
        )
        self.assertTrue(summary["applicability_complete"])
        self.assertEqual(summary["open_findings"], [])

    def test_severity_is_reported_with_the_regime(self):
        summary = assess_inventory([good_item()], "polar-low-earth-orbit")
        self.assertEqual(summary["regime"], "polar-low-earth-orbit")
        self.assertEqual(summary["severity"], 3)

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_inventory([], "geostationary-orbit")

    def test_duplicate_item_name_raises(self):
        with self.assertRaises(ValueError):
            assess_inventory([good_item(), good_item()], "geostationary-orbit")

    def test_non_list_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_inventory(good_item(), "geostationary-orbit")


if __name__ == "__main__":
    unittest.main()
