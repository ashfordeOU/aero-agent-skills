"""Contract tests for the applicability and contamination-sensitivity banding."""

import unittest

from q7001_applicability_and_cleanliness_categories_logic import (
    BANDS,
    MOLECULAR_THRESHOLDS_NG_PER_CM2,
    PARTICULATE_THRESHOLDS_PERCENT,
    band_rank,
    categorize_inventory,
    categorize_item,
    is_applicable,
    molecular_band,
    more_demanding_band,
    particulate_band,
    validate_item,
    validate_positive,
)

MIRROR = {
    "name": "optical-bench-mirror",
    "flight_hardware": True,
    "allowed_obscuration_percent": 0.005,
    "allowed_deposition_ng_per_cm2": 5.0,
    "environment": "cleanroom-A",
}
RADIATOR = {
    "name": "radiator-panel",
    "flight_hardware": True,
    "allowed_obscuration_percent": 0.5,
    "allowed_deposition_ng_per_cm2": 50.0,
    "environment": "cleanroom-A",
}
FIXTURE = {
    "name": "handling-fixture",
    "contacts_flight_hardware": True,
    "allowed_obscuration_percent": 2.0,
    "allowed_deposition_ng_per_cm2": 5000.0,
    "environment": "cleanroom-A",
}
OFFICE_ITEM = {
    "name": "programme-documentation-cabinet",
    "exclusion_justification": "never enters a controlled environment",
}


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(4, "x"), 4.0)

    def test_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "allowed_obscuration_percent")

    def test_boolean_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "allowed_obscuration_percent")

    def test_unnamed_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"flight_hardware": True})

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(["optical-bench-mirror"])

    def test_item_name_is_stripped(self):
        self.assertEqual(validate_item({"name": "  mirror  "})["name"], "mirror")


class ApplicabilityTests(unittest.TestCase):
    def test_flight_hardware_is_in_scope(self):
        decision = is_applicable(MIRROR)
        self.assertTrue(decision["applicable"])
        self.assertEqual(decision["reason"], "flight hardware")

    def test_contact_with_flight_hardware_brings_an_item_in_scope(self):
        decision = is_applicable(FIXTURE)
        self.assertTrue(decision["applicable"])
        self.assertIn("contacts", decision["reason"])

    def test_sharing_the_controlled_environment_brings_an_item_in_scope(self):
        decision = is_applicable(
            {"name": "trolley", "shares_controlled_environment": True}
        )
        self.assertTrue(decision["applicable"])

    def test_out_of_scope_item_needs_a_justification(self):
        decision = is_applicable(OFFICE_ITEM)
        self.assertFalse(decision["applicable"])
        self.assertIn("controlled environment", decision["reason"])

    def test_unjustified_exclusion_rejected(self):
        with self.assertRaises(ValueError):
            is_applicable({"name": "mystery-box"})

    def test_blank_justification_rejected(self):
        with self.assertRaises(ValueError):
            is_applicable({"name": "mystery-box", "exclusion_justification": "   "})


class BandLadderTests(unittest.TestCase):
    def test_band_order_runs_from_tolerant_to_highly_sensitive(self):
        self.assertEqual(BANDS[0], "tolerant")
        self.assertEqual(BANDS[-1], "highly-sensitive")
        self.assertLess(band_rank("moderate"), band_rank("sensitive"))

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            band_rank("pristine")

    def test_more_demanding_band_wins(self):
        self.assertEqual(more_demanding_band("moderate", "sensitive"), "sensitive")
        self.assertEqual(more_demanding_band("sensitive", "sensitive"), "sensitive")

    def test_tight_obscuration_budget_is_highly_sensitive(self):
        self.assertEqual(particulate_band(0.005), "highly-sensitive")

    def test_loose_obscuration_budget_is_tolerant(self):
        self.assertEqual(particulate_band(5.0), "tolerant")

    def test_budget_exactly_on_a_breakpoint_takes_the_more_demanding_band(self):
        bound, band = PARTICULATE_THRESHOLDS_PERCENT[1]
        self.assertEqual(particulate_band(bound), band)

    def test_molecular_breakpoint_behaves_the_same_way(self):
        bound, band = MOLECULAR_THRESHOLDS_NG_PER_CM2[0]
        self.assertEqual(molecular_band(bound), band)

    def test_molecular_budget_above_the_ladder_is_tolerant(self):
        self.assertEqual(molecular_band(50000.0), "tolerant")

    def test_full_surface_obscuration_budget_rejected(self):
        with self.assertRaises(ValueError):
            particulate_band(100.0)

    def test_declared_ladder_overrides_the_default(self):
        ladder = ((1.0, "highly-sensitive"), (2.0, "sensitive"), (3.0, "moderate"))
        self.assertEqual(particulate_band(2.5, ladder), "moderate")

    def test_non_increasing_ladder_rejected(self):
        ladder = ((2.0, "highly-sensitive"), (1.0, "sensitive"))
        with self.assertRaises(ValueError):
            particulate_band(1.5, ladder)

    def test_ladder_naming_an_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            particulate_band(0.5, ((1.0, "ultra"),))


class ItemBandingTests(unittest.TestCase):
    def test_mirror_is_highly_sensitive_on_both_axes(self):
        record = categorize_item(MIRROR)
        self.assertEqual(record["particulate_band"], "highly-sensitive")
        self.assertEqual(record["molecular_band"], "highly-sensitive")
        self.assertEqual(record["overall_band"], "highly-sensitive")
        self.assertEqual(record["driving_axis"], "both")

    def test_radiator_is_driven_by_its_molecular_axis(self):
        record = categorize_item(RADIATOR)
        self.assertEqual(record["particulate_band"], "moderate")
        self.assertEqual(record["molecular_band"], "sensitive")
        self.assertEqual(record["overall_band"], "sensitive")
        self.assertEqual(record["driving_axis"], "molecular")

    def test_particulate_axis_can_drive_the_overall_band(self):
        item = dict(RADIATOR, allowed_obscuration_percent=0.005, name="baffle")
        record = categorize_item(item)
        self.assertEqual(record["driving_axis"], "particulate")
        self.assertEqual(record["overall_band"], "highly-sensitive")

    def test_missing_axis_budget_is_recorded_not_assumed(self):
        item = {"name": "bracket", "flight_hardware": True,
                "allowed_obscuration_percent": 0.5}
        record = categorize_item(item)
        self.assertEqual(record["unbudgeted_axes"], ["molecular"])
        self.assertIsNone(record["molecular_band"])
        self.assertEqual(record["overall_band"], "moderate")

    def test_out_of_scope_item_gets_no_band(self):
        record = categorize_item(OFFICE_ITEM)
        self.assertFalse(record["applicable"])
        self.assertIsNone(record["overall_band"])

    def test_in_scope_item_with_no_budget_at_all_has_no_band(self):
        record = categorize_item({"name": "strut", "flight_hardware": True})
        self.assertIsNone(record["overall_band"])
        self.assertEqual(sorted(record["unbudgeted_axes"]), ["molecular", "particulate"])


class InventoryTests(unittest.TestCase):
    def test_inventory_groups_every_banded_item(self):
        result = categorize_inventory([MIRROR, RADIATOR, FIXTURE])
        self.assertEqual(result["grouped"]["highly-sensitive"], ["optical-bench-mirror"])
        self.assertEqual(result["grouped"]["sensitive"], ["radiator-panel"])
        self.assertEqual(result["grouped"]["tolerant"], ["handling-fixture"])

    def test_counts_match_the_grouping(self):
        result = categorize_inventory([MIRROR, RADIATOR, FIXTURE])
        self.assertEqual(result["counts"]["highly-sensitive"], 1)
        self.assertEqual(sum(result["counts"].values()), 3)

    def test_driving_item_is_the_most_demanding_one(self):
        result = categorize_inventory([RADIATOR, MIRROR, FIXTURE])
        self.assertEqual(result["driving_item"], "optical-bench-mirror")
        self.assertEqual(result["driving_band"], "highly-sensitive")

    def test_shared_environment_pulls_the_looser_item_up(self):
        result = categorize_inventory([MIRROR, RADIATOR, FIXTURE])
        self.assertTrue(
            any("shares environment" in finding for finding in result["findings"])
        )

    def test_out_of_scope_item_is_reported_as_a_finding(self):
        result = categorize_inventory([MIRROR, OFFICE_ITEM])
        self.assertEqual(result["applicable_count"], 1)
        self.assertTrue(
            any("outside the applicability" in f for f in result["findings"])
        )

    def test_unbudgeted_axis_is_reported_as_a_finding(self):
        item = {"name": "bracket", "flight_hardware": True,
                "allowed_obscuration_percent": 0.5}
        result = categorize_inventory([MIRROR, item])
        self.assertTrue(any("no budget on the" in f for f in result["findings"]))

    def test_duplicate_item_name_rejected(self):
        with self.assertRaises(ValueError):
            categorize_inventory([MIRROR, dict(MIRROR)])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            categorize_inventory([])


if __name__ == "__main__":
    unittest.main()
