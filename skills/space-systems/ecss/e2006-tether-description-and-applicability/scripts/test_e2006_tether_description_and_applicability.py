#!/usr/bin/env python3
"""Contract test for the clause 10.1 tether applicability logic."""

import unittest

from e2006_tether_description_and_applicability_logic import (
    CATEGORY_CONDUCTING,
    CATEGORY_CONNECTING_CABLE,
    CATEGORY_ELECTRODYNAMIC,
    CATEGORY_NON_CONDUCTING,
    CATEGORY_NOT_A_TETHER,
    MIN_DEPLOYED_LENGTH_M,
    SLENDERNESS_THRESHOLD,
    applicability_statement,
    applies_to_element,
    assess_element,
    assess_inventory,
    categorize_element,
    hazard_families,
    is_thin_element,
    slenderness_ratio,
)


def element(**overrides):
    base = {
        "id": "ed-tether-1",
        "deployed_length_m": 5000.0,
        "diameter_mm": 1.5,
        "conductor": "bare-conductor",
        "function": "electrodynamic",
        "connects_two_bodies": True,
        "hazard_controls": [
            "tether-breakage-debris",
            "deployed-dynamics-oscillation",
            "motional-emf-end-potential",
            "plasma-current-collection",
            "exposed-conductor-arcing",
        ],
    }
    base.update(overrides)
    return base


class TestSlenderness(unittest.TestCase):
    def test_ratio_converts_diameter_to_metres(self):
        self.assertAlmostEqual(slenderness_ratio(1000.0, 2.0), 500000.0, places=3)

    def test_ratio_small_element(self):
        self.assertAlmostEqual(slenderness_ratio(0.5, 5.0), 100.0, places=6)

    def test_exact_threshold_counts_as_thin(self):
        # 0.3 m over 3 mm is exactly the 100:1 boundary; the sum-of-powers
        # representation must not push a compliant case below the limit.
        self.assertTrue(is_thin_element(0.3, 3.0))

    def test_below_threshold_is_not_thin(self):
        self.assertFalse(is_thin_element(0.2, 3.0))

    def test_ratio_rejects_zero_length(self):
        with self.assertRaises(ValueError):
            slenderness_ratio(0.0, 2.0)

    def test_ratio_rejects_negative_diameter(self):
        with self.assertRaises(ValueError):
            slenderness_ratio(100.0, -1.0)

    def test_ratio_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            slenderness_ratio("1000", 2.0)

    def test_ratio_rejects_boolean_as_number(self):
        with self.assertRaises(ValueError):
            slenderness_ratio(True, 2.0)

    def test_is_thin_rejects_zero_threshold(self):
        with self.assertRaises(ValueError):
            is_thin_element(1000.0, 2.0, threshold=0.0)

    def test_threshold_constant_is_the_documented_one(self):
        self.assertAlmostEqual(SLENDERNESS_THRESHOLD, 100.0, places=9)


class TestCategorize(unittest.TestCase):
    def test_electrodynamic_tether(self):
        self.assertEqual(categorize_element(element()), CATEGORY_ELECTRODYNAMIC)

    def test_conducting_momentum_exchange_tether(self):
        record = element(function="momentum-exchange", conductor="insulated-conductor")
        self.assertEqual(categorize_element(record), CATEGORY_CONDUCTING)

    def test_non_conducting_tether(self):
        record = element(conductor="dielectric", function="formation-keeping")
        self.assertEqual(categorize_element(record), CATEGORY_NON_CONDUCTING)

    def test_dielectric_wins_over_electrodynamic_function(self):
        record = element(conductor="dielectric")
        self.assertEqual(categorize_element(record), CATEGORY_NON_CONDUCTING)

    def test_connecting_cable(self):
        record = element(function="data-power-umbilical", conductor="insulated-conductor")
        self.assertEqual(categorize_element(record), CATEGORY_CONNECTING_CABLE)

    def test_stubby_item_is_not_a_tether(self):
        record = element(deployed_length_m=0.4, diameter_mm=20.0)
        self.assertEqual(categorize_element(record), CATEGORY_NOT_A_TETHER)

    def test_long_but_fat_item_is_not_a_tether(self):
        record = element(deployed_length_m=10.0, diameter_mm=200.0)
        self.assertEqual(categorize_element(record), CATEGORY_NOT_A_TETHER)

    def test_length_below_minimum_is_not_a_tether_even_if_slender(self):
        record = element(deployed_length_m=0.5, diameter_mm=0.002)
        self.assertLess(record["deployed_length_m"], MIN_DEPLOYED_LENGTH_M)
        self.assertEqual(categorize_element(record), CATEGORY_NOT_A_TETHER)

    def test_unknown_conductor_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element(element(conductor="semiconducting"))

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element(element(function="antenna"))

    def test_missing_field_rejected(self):
        record = element()
        del record["diameter_mm"]
        with self.assertRaises(ValueError):
            categorize_element(record)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element(["not", "a", "mapping"])

    def test_non_boolean_connects_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element(element(connects_two_bodies="yes"))


class TestApplicability(unittest.TestCase):
    def test_spanning_tether_is_in_scope(self):
        self.assertTrue(applies_to_element(element()))

    def test_non_spanning_tether_is_out_of_scope(self):
        self.assertFalse(applies_to_element(element(connects_two_bodies=False)))

    def test_short_item_is_out_of_scope(self):
        self.assertFalse(
            applies_to_element(element(deployed_length_m=0.2, diameter_mm=10.0))
        )


class TestHazardFamilies(unittest.TestCase):
    def test_bare_conductor_in_leo_carries_every_family(self):
        families = hazard_families(CATEGORY_ELECTRODYNAMIC, "leo", "bare-conductor")
        self.assertIn("motional-emf-end-potential", families)
        self.assertIn("plasma-current-collection", families)
        self.assertIn("exposed-conductor-arcing", families)
        self.assertIn("tether-breakage-debris", families)
        self.assertIn("deployed-dynamics-oscillation", families)

    def test_insulated_conductor_swaps_arcing_for_continuity(self):
        families = hazard_families(CATEGORY_CONDUCTING, "leo", "insulated-conductor")
        self.assertIn("insulation-continuity-loss", families)
        self.assertNotIn("exposed-conductor-arcing", families)

    def test_geo_drops_the_current_collection_family(self):
        families = hazard_families(CATEGORY_CONDUCTING, "geo", "insulated-conductor")
        self.assertNotIn("plasma-current-collection", families)
        self.assertNotIn("motional-emf-end-potential", families)

    def test_meo_keeps_motional_emf_without_current_collection(self):
        families = hazard_families(CATEGORY_CONDUCTING, "meo", "bare-conductor")
        self.assertIn("motional-emf-end-potential", families)
        self.assertNotIn("plasma-current-collection", families)

    def test_dielectric_tether_keeps_only_structural_families(self):
        families = hazard_families(CATEGORY_NON_CONDUCTING, "leo", "dielectric")
        self.assertEqual(
            families, ["deployed-dynamics-oscillation", "tether-breakage-debris"]
        )

    def test_out_of_scope_category_has_no_families(self):
        self.assertEqual(hazard_families(CATEGORY_NOT_A_TETHER, "leo", "bare-conductor"), [])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            hazard_families("space-elevator", "leo", "bare-conductor")

    def test_unknown_regime_rejected(self):
        with self.assertRaises(ValueError):
            hazard_families(CATEGORY_ELECTRODYNAMIC, "cislunar", "bare-conductor")

    def test_unknown_conductor_rejected(self):
        with self.assertRaises(ValueError):
            hazard_families(CATEGORY_ELECTRODYNAMIC, "leo", "plasma")


class TestAssessElement(unittest.TestCase):
    def test_fully_controlled_element_is_compliant(self):
        record = assess_element(element(), "leo")
        self.assertTrue(record["in_scope"])
        self.assertTrue(record["compliant"])
        self.assertEqual(record["uncontrolled_hazards"], [])
        self.assertEqual(record["findings"], [])

    def test_missing_control_is_reported(self):
        record = assess_element(element(hazard_controls=["tether-breakage-debris"]), "leo")
        self.assertFalse(record["compliant"])
        self.assertIn("plasma-current-collection", record["uncontrolled_hazards"])
        self.assertTrue(any("no control on record" in f for f in record["findings"]))

    def test_slenderness_reported_on_the_record(self):
        record = assess_element(element(), "leo")
        self.assertAlmostEqual(record["slenderness"], 5000.0 / 0.0015, places=3)

    def test_non_spanning_slender_item_is_flagged_not_silently_dropped(self):
        record = assess_element(element(connects_two_bodies=False), "leo")
        self.assertFalse(record["in_scope"])
        self.assertTrue(any("two bodies" in f for f in record["findings"]))

    def test_empty_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_element(element(id="  "), "leo")

    def test_non_list_controls_rejected(self):
        with self.assertRaises(ValueError):
            assess_element(element(hazard_controls="all-of-them"), "leo")

    def test_non_string_control_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_element(element(hazard_controls=[7]), "leo")


class TestAssessInventory(unittest.TestCase):
    def test_mixed_inventory_summary(self):
        items = [
            element(),
            element(
                id="drag-sail-line",
                conductor="dielectric",
                function="formation-keeping",
                hazard_controls=[
                    "tether-breakage-debris",
                    "deployed-dynamics-oscillation",
                ],
            ),
            element(id="hinge-pin", deployed_length_m=0.1, diameter_mm=8.0),
        ]
        summary = assess_inventory(items, "leo")
        self.assertEqual(summary["element_count"], 3)
        self.assertEqual(summary["in_scope_ids"], ["ed-tether-1", "drag-sail-line"])
        self.assertEqual(summary["out_of_scope_ids"], ["hinge-pin"])
        self.assertTrue(summary["clause_applicable"])
        self.assertTrue(summary["compliant"])

    def test_inventory_without_a_tether_is_not_applicable(self):
        summary = assess_inventory(
            [element(id="hinge-pin", deployed_length_m=0.1, diameter_mm=8.0)], "geo"
        )
        self.assertFalse(summary["clause_applicable"])
        self.assertEqual(summary["hazard_families"], [])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_inventory([element(), element()], "leo")

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_inventory([], "leo")

    def test_non_list_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_inventory(element(), "leo")

    def test_bad_regime_propagates(self):
        with self.assertRaises(ValueError):
            assess_inventory([element()], "heliocentric")

    def test_findings_aggregate_across_elements(self):
        items = [
            element(hazard_controls=[]),
            element(id="second", hazard_controls=[]),
        ]
        summary = assess_inventory(items, "leo")
        self.assertFalse(summary["compliant"])
        self.assertGreaterEqual(len(summary["findings"]), 10)


class TestApplicabilityStatement(unittest.TestCase):
    def test_statement_lists_in_scope_elements(self):
        summary = assess_inventory([element()], "leo")
        self.assertIn("ed-tether-1", applicability_statement(summary))

    def test_statement_for_empty_scope(self):
        summary = assess_inventory(
            [element(id="hinge-pin", deployed_length_m=0.1, diameter_mm=8.0)], "geo"
        )
        self.assertIn("do not apply", applicability_statement(summary))

    def test_statement_rejects_foreign_input(self):
        with self.assertRaises(ValueError):
            applicability_statement({"unrelated": True})


if __name__ == "__main__":
    unittest.main()
