"""Contract tests for the molecular (NVR) cleanliness level-selection logic."""

import unittest

from q7001_molecular_level_selection_logic import (
    LEVEL_TOLERANCE,
    allowable_residue_mg_m2,
    assess_category,
    delivery_allowance_mg_m2,
    level_margin_fraction,
    level_value,
    select_level,
    select_molecular_levels,
    tightest_level,
    validate_level_ladder,
    validate_positive,
)

# Illustrative project ladder of named molecular levels, areal residue density
# in mg/m^2, tightest first. Supplied by the caller, never hard-coded in logic.
LADDER = [
    ("M-A", 0.5),
    ("M-B", 1.0),
    ("M-C", 2.0),
    ("M-D", 5.0),
    ("M-E", 10.0),
]


class ValidatePositiveTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertAlmostEqual(validate_positive(3, "x"), 3.0, places=9)

    def test_zero_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "x")

    def test_zero_allowed_when_requested(self):
        self.assertAlmostEqual(validate_positive(0.0, "x", allow_zero=True), 0.0, places=9)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("nan"), "x")


class LadderTests(unittest.TestCase):
    def test_ladder_returned_as_pairs(self):
        entries = validate_level_ladder(LADDER)
        self.assertEqual(entries[0][0], "M-A")
        self.assertAlmostEqual(entries[-1][1], 10.0, places=9)

    def test_single_level_ladder_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([("M-A", 0.5)])

    def test_non_increasing_ladder_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([("M-A", 2.0), ("M-B", 1.0)])

    def test_duplicate_level_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([("M-A", 0.5), ("M-A", 1.0)])

    def test_empty_level_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([("", 0.5), ("M-B", 1.0)])

    def test_non_positive_level_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_ladder([("M-A", 0.0), ("M-B", 1.0)])

    def test_level_value_lookup(self):
        self.assertAlmostEqual(level_value(LADDER, "M-C"), 2.0, places=9)

    def test_unknown_level_name_rejected(self):
        with self.assertRaises(ValueError):
            level_value(LADDER, "M-Z")


class AllowanceTests(unittest.TestCase):
    def test_allowable_residue_inverts_the_sensitivity(self):
        self.assertAlmostEqual(allowable_residue_mg_m2(0.02, 0.004), 5.0, places=9)

    def test_a_more_sensitive_surface_allows_less_residue(self):
        blunt = allowable_residue_mg_m2(0.02, 0.004)
        sensitive = allowable_residue_mg_m2(0.02, 0.040)
        self.assertAlmostEqual(sensitive, blunt / 10.0, places=9)

    def test_zero_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            allowable_residue_mg_m2(0.02, 0.0)

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            allowable_residue_mg_m2(-0.02, 0.004)

    def test_delivery_allowance_removes_later_accumulation(self):
        self.assertAlmostEqual(delivery_allowance_mg_m2(5.0, 2.0), 3.0, places=9)

    def test_zero_later_accumulation_leaves_the_whole_allowance(self):
        self.assertAlmostEqual(delivery_allowance_mg_m2(5.0, 0.0), 5.0, places=9)

    def test_accumulation_consuming_the_allowance_is_refused(self):
        with self.assertRaises(ValueError):
            delivery_allowance_mg_m2(5.0, 5.0)

    def test_accumulation_over_the_allowance_is_refused(self):
        with self.assertRaises(ValueError):
            delivery_allowance_mg_m2(5.0, 7.0)


class SelectLevelTests(unittest.TestCase):
    def test_least_demanding_level_under_the_allowance_is_taken(self):
        self.assertEqual(select_level(LADDER, 3.0)[0], "M-C")

    def test_allowance_landing_exactly_on_a_level_selects_it(self):
        name, value = select_level(LADDER, 2.0)
        self.assertEqual(name, "M-C")
        self.assertAlmostEqual(value, 2.0, places=9)

    def test_allowance_above_the_ladder_top_selects_the_loosest(self):
        self.assertEqual(select_level(LADDER, 40.0)[0], "M-E")

    def test_allowance_tighter_than_the_ladder_is_refused(self):
        with self.assertRaises(ValueError):
            select_level(LADDER, 0.2)

    def test_non_positive_allowance_rejected(self):
        with self.assertRaises(ValueError):
            select_level(LADDER, 0.0)

    def test_margin_fraction_is_the_unused_share(self):
        self.assertAlmostEqual(level_margin_fraction(2.0, 4.0), 0.5, places=9)

    def test_margin_is_zero_at_an_exact_fit(self):
        self.assertAlmostEqual(level_margin_fraction(2.0, 2.0), 0.0, places=9)
        self.assertLessEqual(abs(level_margin_fraction(2.0, 2.0)), LEVEL_TOLERANCE)

    def test_tightest_level_of_an_enclosure(self):
        name, value = tightest_level(LADDER, ["M-D", "M-B", "M-E"])
        self.assertEqual(name, "M-B")
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_tightest_level_rejects_unknown_name(self):
        with self.assertRaises(ValueError):
            tightest_level(LADDER, ["M-B", "M-Q"])

    def test_tightest_level_rejects_empty_set(self):
        with self.assertRaises(ValueError):
            tightest_level(LADDER, [])


class AssessCategoryTests(unittest.TestCase):
    def _category(self, **overrides):
        category = {
            "name": "radiator",
            "degradation_budget": 0.02,
            "sensitivity_per_mg_m2": 0.004,
            "post_delivery_accumulation": 2.0,
        }
        category.update(overrides)
        return category

    def test_selection_uses_the_delivery_allowance(self):
        record = assess_category(self._category(), LADDER)
        self.assertAlmostEqual(record["delivery_allowance_mg_m2"], 3.0, places=9)
        self.assertEqual(record["selected_level"], "M-C")

    def test_clean_category_reports_no_findings(self):
        self.assertEqual(assess_category(self._category(), LADDER)["findings"], [])

    def test_imposed_floor_overrides_a_looser_performance_choice(self):
        record = assess_category(
            self._category(imposed_floor_level="M-B"), LADDER
        )
        self.assertEqual(record["selected_level"], "M-B")
        self.assertEqual(len(record["findings"]), 1)

    def test_imposed_floor_looser_than_the_choice_does_not_relax_it(self):
        record = assess_category(
            self._category(imposed_floor_level="M-E"), LADDER
        )
        self.assertEqual(record["selected_level"], "M-C")
        self.assertEqual(record["findings"], [])

    def test_unknown_imposed_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_category(self._category(imposed_floor_level="M-Q"), LADDER)

    def test_missing_key_rejected(self):
        category = self._category()
        del category["sensitivity_per_mg_m2"]
        with self.assertRaises(ValueError):
            assess_category(category, LADDER)

    def test_non_mapping_category_rejected(self):
        with self.assertRaises(ValueError):
            assess_category(["radiator"], LADDER)

    def test_blank_category_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_category(self._category(name="  "), LADDER)

    def test_sensitive_optic_is_driven_off_the_ladder(self):
        with self.assertRaises(ValueError):
            assess_category(
                self._category(
                    name="cold optic",
                    sensitivity_per_mg_m2=0.2,
                    post_delivery_accumulation=0.05,
                ),
                LADDER,
            )


class SelectMolecularLevelsTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "ladder": LADDER,
            "categories": [
                {
                    "name": "radiator",
                    "degradation_budget": 0.02,
                    "sensitivity_per_mg_m2": 0.004,
                    "post_delivery_accumulation": 2.0,
                },
                {
                    "name": "star tracker baffle",
                    "degradation_budget": 0.01,
                    "sensitivity_per_mg_m2": 0.008,
                    "post_delivery_accumulation": 0.2,
                },
                {
                    "name": "structure panel",
                    "degradation_budget": 0.40,
                    "sensitivity_per_mg_m2": 0.004,
                    "post_delivery_accumulation": 5.0,
                },
            ],
        }
        spec.update(overrides)
        return spec

    def test_one_record_per_category(self):
        result = select_molecular_levels(self._spec())
        self.assertEqual(len(result["records"]), 3)

    def test_driving_category_is_the_tightest_selection(self):
        result = select_molecular_levels(self._spec())
        self.assertEqual(result["driving_category"], "star tracker baffle")
        self.assertEqual(result["driving_level"], "M-B")

    def test_structure_panel_takes_a_looser_level(self):
        result = select_molecular_levels(self._spec())
        panel = [r for r in result["records"] if r["category"] == "structure panel"][0]
        self.assertEqual(panel["selected_level"], "M-E")

    def test_enclosure_inherits_the_tightest_contained_level(self):
        spec = self._spec(
            enclosures={"payload bay": ["radiator", "star tracker baffle"]}
        )
        result = select_molecular_levels(spec)
        self.assertEqual(result["enclosures"][0]["inherited_level"], "M-B")
        self.assertAlmostEqual(
            result["enclosures"][0]["inherited_mg_m2"], 1.0, places=9
        )

    def test_enclosure_referencing_an_unknown_category_rejected(self):
        spec = self._spec(enclosures={"payload bay": ["radiator", "antenna"]})
        with self.assertRaises(ValueError):
            select_molecular_levels(spec)

    def test_empty_enclosure_rejected(self):
        spec = self._spec(enclosures={"payload bay": []})
        with self.assertRaises(ValueError):
            select_molecular_levels(spec)

    def test_duplicate_category_rejected(self):
        spec = self._spec()
        spec["categories"] = list(spec["categories"]) + [spec["categories"][0]]
        with self.assertRaises(ValueError):
            select_molecular_levels(spec)

    def test_empty_category_set_rejected(self):
        with self.assertRaises(ValueError):
            select_molecular_levels(self._spec(categories=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["ladder"]
        with self.assertRaises(ValueError):
            select_molecular_levels(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            select_molecular_levels(["ladder"])

    def test_imposed_floor_surfaces_in_the_rolled_up_findings(self):
        spec = self._spec()
        spec["categories"][2]["imposed_floor_level"] = "M-C"
        result = select_molecular_levels(spec)
        self.assertEqual(len(result["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
