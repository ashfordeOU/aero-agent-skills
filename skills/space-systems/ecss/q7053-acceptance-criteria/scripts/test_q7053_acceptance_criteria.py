"""Contract tests for the ECSS-Q-ST-70-53C acceptance decision."""

import unittest

from q7053_acceptance_criteria_logic import (
    ACCEPT,
    ACCEPT_WITH_DEVIATION,
    CEILING,
    DEFAULT_ACCEPTANCE_CRITERIA,
    DEFAULT_CATEGORY_SEVERITY,
    FLOOR,
    LIMIT_TOLERANCE,
    REJECT,
    apply_criterion,
    criteria_for_category,
    criterion_utilisation,
    decide_acceptance,
    governing_criterion,
    resolve_assembly_category,
    validate_criterion,
)

CEILING_CRITERION = {"direction": CEILING, "limit": 0.02, "deviation_band": 0.005}
FLOOR_CRITERION = {"direction": FLOOR, "limit": 0.80, "deviation_band": 0.05}


class ValidateCriterionTests(unittest.TestCase):
    def test_ceiling_criterion_normalises(self):
        spec = validate_criterion(CEILING_CRITERION)
        self.assertEqual(spec["direction"], CEILING)
        self.assertAlmostEqual(spec["limit"], 0.02)

    def test_deviation_band_defaults_to_zero(self):
        spec = validate_criterion({"direction": FLOOR, "limit": 1.0})
        self.assertAlmostEqual(spec["deviation_band"], 0.0)

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"direction": "either", "limit": 1.0})

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"direction": FLOOR})

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"direction": FLOOR, "limit": 0.0})

    def test_negative_deviation_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"direction": FLOOR, "limit": 1.0, "deviation_band": -0.1})

    def test_non_mapping_criterion_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(["floor", 1.0])


class CategoryTests(unittest.TestCase):
    def test_every_default_category_has_a_usable_set(self):
        for category in DEFAULT_ACCEPTANCE_CRITERIA:
            self.assertTrue(criteria_for_category(category))

    def test_polymer_set_differs_from_the_metal_set(self):
        polymer = criteria_for_category("polymer")
        metal = criteria_for_category("metal")
        self.assertNotEqual(sorted(polymer), sorted(metal))

    def test_retention_floor_is_tighter_for_metal_than_for_polymer(self):
        polymer = criteria_for_category("polymer")["mechanical-retention-fraction"]
        metal = criteria_for_category("metal")["mechanical-retention-fraction"]
        self.assertGreater(metal["limit"], polymer["limit"])

    def test_unknown_category_refused(self):
        with self.assertRaises(ValueError):
            criteria_for_category("ceramic-foam")

    def test_empty_category_name_refused(self):
        with self.assertRaises(ValueError):
            criteria_for_category("   ")

    def test_custom_table_is_honoured(self):
        table = {"seal": {"leak-rate": {"direction": CEILING, "limit": 1.0e-6}}}
        self.assertIn("leak-rate", criteria_for_category("seal", table))

    def test_severity_order_covers_the_default_table(self):
        self.assertEqual(sorted(DEFAULT_CATEGORY_SEVERITY),
                         sorted(DEFAULT_ACCEPTANCE_CRITERIA))

    def test_most_severe_constituent_governs(self):
        self.assertEqual(resolve_assembly_category(["metal", "polymer"]), "polymer")

    def test_electronic_assembly_outranks_a_polymer_insert(self):
        self.assertEqual(
            resolve_assembly_category(["polymer", "electronic-assembly"]),
            "electronic-assembly",
        )

    def test_single_constituent_resolves_to_itself(self):
        self.assertEqual(resolve_assembly_category(["adhesive"]), "adhesive")

    def test_constituent_outside_the_severity_order_rejected(self):
        with self.assertRaises(ValueError):
            resolve_assembly_category(["metal", "ceramic-foam"])

    def test_empty_constituent_list_rejected(self):
        with self.assertRaises(ValueError):
            resolve_assembly_category([])

    def test_repeated_category_in_severity_order_rejected(self):
        with self.assertRaises(ValueError):
            resolve_assembly_category(["metal"], severity=("metal", "metal"))


class ApplyCriterionTests(unittest.TestCase):
    def test_ceiling_inside_the_limit_passes(self):
        record = apply_criterion(CEILING_CRITERION, 0.01)
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["exceedance"], 0.0)

    def test_ceiling_exactly_on_the_limit_passes(self):
        record = apply_criterion(CEILING_CRITERION, 0.02)
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["utilisation"], 1.0, places=9)

    def test_ceiling_inside_the_deviation_band_is_a_breach_but_reopenable(self):
        record = apply_criterion(CEILING_CRITERION, 0.023)
        self.assertFalse(record["within_limit"])
        self.assertTrue(record["within_deviation_band"])

    def test_ceiling_beyond_the_band_is_not_reopenable(self):
        record = apply_criterion(CEILING_CRITERION, 0.03)
        self.assertFalse(record["within_deviation_band"])

    def test_floor_above_the_limit_passes(self):
        self.assertTrue(apply_criterion(FLOOR_CRITERION, 0.90)["within_limit"])

    def test_floor_exactly_on_the_limit_passes(self):
        record = apply_criterion(FLOOR_CRITERION, 0.80)
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["utilisation"], 1.0, places=9)

    def test_floor_inside_the_band_is_a_reopenable_breach(self):
        record = apply_criterion(FLOOR_CRITERION, 0.77)
        self.assertFalse(record["within_limit"])
        self.assertTrue(record["within_deviation_band"])

    def test_floor_beyond_the_band_is_not_reopenable(self):
        self.assertFalse(apply_criterion(FLOOR_CRITERION, 0.60)["within_deviation_band"])

    def test_floor_exceedance_is_the_shortfall(self):
        self.assertAlmostEqual(apply_criterion(FLOOR_CRITERION, 0.75)["exceedance"], 0.05)

    def test_utilisation_of_a_ceiling_is_the_ratio_to_the_limit(self):
        self.assertAlmostEqual(criterion_utilisation(CEILING_CRITERION, 0.01), 0.5)

    def test_utilisation_of_a_floor_inverts_the_ratio(self):
        self.assertAlmostEqual(criterion_utilisation(FLOOR_CRITERION, 1.60), 0.5)

    def test_zero_measurement_on_a_floor_rejected(self):
        with self.assertRaises(ValueError):
            criterion_utilisation(FLOOR_CRITERION, 0.0)

    def test_negative_measurement_on_a_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            criterion_utilisation(CEILING_CRITERION, -0.01)

    def test_governing_is_the_highest_utilisation(self):
        graded = [
            apply_criterion(CEILING_CRITERION, 0.01, "mass-loss-fraction"),
            apply_criterion(FLOOR_CRITERION, 0.90, "mechanical-retention-fraction"),
        ]
        self.assertEqual(
            governing_criterion(graded)["name"], "mechanical-retention-fraction"
        )

    def test_governing_tie_breaks_on_name(self):
        graded = [
            apply_criterion(CEILING_CRITERION, 0.01, "zeta"),
            apply_criterion(CEILING_CRITERION, 0.01, "alpha"),
        ]
        self.assertEqual(governing_criterion(graded)["name"], "alpha")

    def test_governing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            governing_criterion([])


class DecisionTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "item_id": "SEAL-3308-viton-o-ring",
            "category": "polymer",
            "measurements": {
                "mass-loss-fraction": 0.01,
                "mechanical-retention-fraction": 0.90,
                "dimensional-change-fraction": 0.005,
            },
        }
        spec.update(overrides)
        return spec

    def test_everything_inside_its_limit_accepts(self):
        result = decide_acceptance(self._spec())
        self.assertEqual(result["decision"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_category_and_item_id_are_reported(self):
        result = decide_acceptance(self._spec())
        self.assertEqual(result["category"], "polymer")
        self.assertEqual(result["item_id"], "SEAL-3308-viton-o-ring")

    def test_governing_criterion_is_named(self):
        result = decide_acceptance(self._spec())
        self.assertEqual(
            result["governing_criterion"]["name"], "mechanical-retention-fraction"
        )

    def test_breach_inside_the_band_with_a_reference_accepts_with_deviation(self):
        spec = self._spec(deviation_reference="NCR-2026-0142")
        spec["measurements"]["mass-loss-fraction"] = 0.023
        result = decide_acceptance(spec)
        self.assertEqual(result["decision"], ACCEPT_WITH_DEVIATION)
        self.assertEqual(result["deviation_reference"], "NCR-2026-0142")

    def test_breach_inside_the_band_without_a_reference_rejects(self):
        spec = self._spec()
        spec["measurements"]["mass-loss-fraction"] = 0.023
        result = decide_acceptance(spec)
        self.assertEqual(result["decision"], REJECT)
        self.assertTrue(any("no deviation reference" in f for f in result["findings"]))

    def test_breach_beyond_the_band_rejects_even_with_a_reference(self):
        spec = self._spec(deviation_reference="NCR-2026-0142")
        spec["measurements"]["mass-loss-fraction"] = 0.05
        result = decide_acceptance(spec)
        self.assertEqual(result["decision"], REJECT)
        self.assertEqual(result["beyond_deviation_band"], ["mass-loss-fraction"])

    def test_unevidenced_criterion_blocks_the_accept(self):
        spec = self._spec()
        del spec["measurements"]["dimensional-change-fraction"]
        result = decide_acceptance(spec)
        self.assertEqual(result["decision"], REJECT)
        self.assertEqual(result["unevidenced_criteria"], ["dimensional-change-fraction"])

    def test_unclaimed_measurement_is_reported_without_blocking(self):
        spec = self._spec()
        spec["measurements"]["colour-shift-delta-e"] = 1.2
        result = decide_acceptance(spec)
        self.assertEqual(result["decision"], ACCEPT)
        self.assertEqual(result["unclaimed_measurements"], ["colour-shift-delta-e"])

    def test_metal_limits_are_applied_to_a_metal_item(self):
        spec = {
            "category": "metal",
            "measurements": {
                "mass-change-fraction": 0.0005,
                "mechanical-retention-fraction": 0.90,
            },
        }
        result = decide_acceptance(spec)
        self.assertEqual(result["decision"], REJECT)

    def test_same_numbers_pass_as_a_polymer_and_fail_as_a_metal(self):
        numbers = {"mechanical-retention-fraction": 0.90}
        as_metal = decide_acceptance(
            {"category": "metal",
             "measurements": dict(numbers, **{"mass-change-fraction": 0.0005})}
        )
        as_polymer = decide_acceptance(
            {"category": "polymer",
             "measurements": dict(numbers, **{"mass-loss-fraction": 0.01,
                                              "dimensional-change-fraction": 0.005})}
        )
        self.assertEqual(as_metal["decision"], REJECT)
        self.assertEqual(as_polymer["decision"], ACCEPT)

    def test_mixed_assembly_resolves_before_grading(self):
        spec = {
            "constituent_categories": ["metal", "polymer"],
            "measurements": {
                "mass-loss-fraction": 0.01,
                "mechanical-retention-fraction": 0.90,
                "dimensional-change-fraction": 0.005,
            },
        }
        result = decide_acceptance(spec)
        self.assertEqual(result["category"], "polymer")
        self.assertEqual(result["decision"], ACCEPT)

    def test_both_category_forms_at_once_rejected(self):
        spec = self._spec(constituent_categories=["metal", "polymer"])
        with self.assertRaises(ValueError):
            decide_acceptance(spec)

    def test_no_category_at_all_rejected(self):
        with self.assertRaises(ValueError):
            decide_acceptance({"measurements": {}})

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            decide_acceptance(self._spec(category="ceramic-foam"))

    def test_non_mapping_measurements_rejected(self):
        with self.assertRaises(ValueError):
            decide_acceptance(self._spec(measurements=[0.01]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            decide_acceptance(["polymer"])

    def test_limit_tolerance_is_small_and_positive(self):
        self.assertGreater(LIMIT_TOLERANCE, 0.0)
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
