#!/usr/bin/env python3
"""Contract test for the post-exposure mass property checks (offline)."""

import copy
import math
import unittest

from q7004_mass_property_checks_logic import (
    COATING_ITEM,
    DEFAULT_MASS_POLICY,
    ELECTRONIC_ITEM,
    FAIL,
    INDETERMINATE,
    ITEM_CATEGORIES,
    PASS,
    POLYMER_ITEM,
    STRUCTURAL_ITEM,
    category_loss_limit_pct,
    change_is_resolvable,
    evaluate_mass_change,
    evaluate_mass_property_checks,
    measurement_uncertainty_pct,
    relative_mass_change_pct,
    validate_mass_policy,
)

BASE_RECORD = {
    "specimen_id": "SP-01",
    "category": STRUCTURAL_ITEM,
    "initial_mass_g": 200.0,
    "final_mass_g": 199.95,
}


def _record(base, **overrides):
    record = copy.deepcopy(base)
    record.update(overrides)
    return record


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_mass_policy(DEFAULT_MASS_POLICY), DEFAULT_MASS_POLICY)

    def test_policy_carries_a_limit_for_every_category(self):
        for category in ITEM_CATEGORIES:
            self.assertGreater(category_loss_limit_pct(category), 0.0)

    def test_policy_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_MASS_POLICY)
        del broken["max_relative_loss_pct"][COATING_ITEM]
        with self.assertRaises(ValueError):
            validate_mass_policy(broken)

    def test_policy_with_a_zero_balance_resolution_rejected(self):
        broken = copy.deepcopy(DEFAULT_MASS_POLICY)
        broken["balance_resolution_g"] = 0.0
        with self.assertRaises(ValueError):
            validate_mass_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_mass_policy("default")

    def test_an_unknown_category_has_no_limit(self):
        with self.assertRaises(ValueError):
            category_loss_limit_pct("harness-item")


class RelativeChangeTests(unittest.TestCase):
    def test_a_loss_reads_positive(self):
        self.assertAlmostEqual(
            relative_mass_change_pct(200.0, 199.8), 0.1, places=9
        )

    def test_a_gain_reads_negative(self):
        self.assertAlmostEqual(
            relative_mass_change_pct(200.0, 200.2), -0.1, places=9
        )

    def test_an_unchanged_specimen_reads_zero(self):
        self.assertAlmostEqual(relative_mass_change_pct(200.0, 200.0), 0.0, places=9)

    def test_the_same_absolute_loss_is_a_larger_relative_change_on_a_small_item(self):
        big = relative_mass_change_pct(200.0, 199.8)
        small = relative_mass_change_pct(20.0, 19.8)
        self.assertAlmostEqual(small / big, 10.0, places=9)

    def test_a_specimen_below_the_mass_floor_rejected(self):
        with self.assertRaises(ValueError):
            relative_mass_change_pct(0.02, 0.019)

    def test_a_non_numeric_final_mass_rejected(self):
        with self.assertRaises(ValueError):
            relative_mass_change_pct(200.0, "one ninety nine")


class UncertaintyTests(unittest.TestCase):
    def test_uncertainty_combines_both_weighings(self):
        expected = (
            100.0
            * DEFAULT_MASS_POLICY["coverage_factor"]
            * DEFAULT_MASS_POLICY["balance_resolution_g"]
            * math.sqrt(2.0)
            / 200.0
        )
        self.assertAlmostEqual(measurement_uncertainty_pct(200.0), expected, places=12)

    def test_uncertainty_scales_inversely_with_specimen_mass(self):
        heavy = measurement_uncertainty_pct(200.0)
        light = measurement_uncertainty_pct(20.0)
        self.assertAlmostEqual(light / heavy, 10.0, places=9)

    def test_a_change_equal_to_the_uncertainty_is_not_resolvable(self):
        uncertainty = measurement_uncertainty_pct(200.0)
        self.assertFalse(change_is_resolvable(uncertainty, uncertainty))

    def test_a_change_well_above_the_uncertainty_is_resolvable(self):
        uncertainty = measurement_uncertainty_pct(200.0)
        self.assertTrue(change_is_resolvable(0.05, uncertainty))

    def test_a_gain_is_resolved_on_its_magnitude(self):
        uncertainty = measurement_uncertainty_pct(200.0)
        self.assertTrue(change_is_resolvable(-0.05, uncertainty))

    def test_a_zero_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            change_is_resolvable(0.05, 0.0)


class SpecimenVerdictTests(unittest.TestCase):
    def test_a_compliant_structural_specimen_passes(self):
        result = evaluate_mass_change(BASE_RECORD)
        self.assertEqual(result["verdict"], PASS)
        self.assertAlmostEqual(result["change_pct"], 0.025, places=9)
        self.assertAlmostEqual(result["mass_change_g"], 0.05, places=9)

    def test_a_loss_landing_on_the_limit_passes(self):
        limit = category_loss_limit_pct(STRUCTURAL_ITEM)
        initial = 200.0
        final = initial * (1.0 - limit / 100.0)
        result = evaluate_mass_change(
            _record(BASE_RECORD, initial_mass_g=initial, final_mass_g=final)
        )
        self.assertAlmostEqual(result["change_pct"], limit, places=9)
        self.assertEqual(result["verdict"], PASS)

    def test_a_loss_above_the_limit_fails(self):
        result = evaluate_mass_change(
            _record(BASE_RECORD, final_mass_g=199.0)
        )
        self.assertEqual(result["verdict"], FAIL)
        self.assertTrue(any("exceeds" in reason for reason in result["reasons"]))

    def test_a_gain_beyond_the_allowance_fails_as_uptake(self):
        result = evaluate_mass_change(
            _record(BASE_RECORD, final_mass_g=200.6)
        )
        self.assertEqual(result["verdict"], FAIL)
        self.assertTrue(any("gained" in reason for reason in result["reasons"]))

    def test_a_polymer_item_tolerates_what_fails_a_structural_item(self):
        loose = evaluate_mass_change(
            _record(BASE_RECORD, category=POLYMER_ITEM, final_mass_g=199.0)
        )
        tight = evaluate_mass_change(_record(BASE_RECORD, final_mass_g=199.0))
        self.assertEqual(loose["verdict"], PASS)
        self.assertEqual(tight["verdict"], FAIL)

    def test_a_specimen_the_balance_cannot_judge_is_indeterminate(self):
        result = evaluate_mass_change(
            _record(
                BASE_RECORD,
                category=ELECTRONIC_ITEM,
                initial_mass_g=0.1,
                final_mass_g=0.0999,
            )
        )
        self.assertEqual(result["verdict"], INDETERMINATE)
        self.assertTrue(any("cannot demonstrate" in r for r in result["reasons"]))

    def test_an_unresolvable_pass_says_so(self):
        result = evaluate_mass_change(
            _record(BASE_RECORD, final_mass_g=199.9999)
        )
        self.assertEqual(result["verdict"], PASS)
        self.assertFalse(result["resolvable"])
        self.assertTrue(any("no measurable change" in r for r in result["reasons"]))

    def test_a_blank_specimen_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mass_change(_record(BASE_RECORD, specimen_id="   "))

    def test_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mass_change(_record(BASE_RECORD, category="harness-item"))

    def test_a_missing_final_mass_rejected(self):
        record = _record(BASE_RECORD)
        del record["final_mass_g"]
        with self.assertRaises(ValueError):
            evaluate_mass_change(record)


class BatchTests(unittest.TestCase):
    def test_a_clean_batch_passes(self):
        batch = evaluate_mass_property_checks(
            {
                "specimens": [
                    BASE_RECORD,
                    _record(BASE_RECORD, specimen_id="SP-02", final_mass_g=199.9),
                ]
            }
        )
        self.assertEqual(batch["verdict"], PASS)
        self.assertEqual(batch["specimen_count"], 2)
        self.assertEqual(batch["failed_count"], 0)

    def test_one_failing_specimen_fails_the_batch(self):
        batch = evaluate_mass_property_checks(
            {
                "specimens": [
                    BASE_RECORD,
                    _record(BASE_RECORD, specimen_id="SP-02", final_mass_g=198.0),
                ]
            }
        )
        self.assertEqual(batch["verdict"], FAIL)
        self.assertEqual(batch["failed_count"], 1)
        self.assertEqual(batch["worst_specimen_id"], "SP-02")

    def test_an_unjudgeable_specimen_makes_the_batch_indeterminate(self):
        batch = evaluate_mass_property_checks(
            {
                "specimens": [
                    BASE_RECORD,
                    _record(
                        BASE_RECORD,
                        specimen_id="SP-02",
                        initial_mass_g=0.1,
                        final_mass_g=0.0999,
                    ),
                ]
            }
        )
        self.assertEqual(batch["verdict"], INDETERMINATE)
        self.assertEqual(batch["indeterminate_count"], 1)

    def test_a_batch_with_a_gain_carries_the_gain_duty(self):
        batch = evaluate_mass_property_checks(
            {
                "specimens": [
                    BASE_RECORD,
                    _record(BASE_RECORD, specimen_id="SP-02", final_mass_g=200.01),
                ]
            }
        )
        self.assertTrue(any("mass gain" in duty for duty in batch["duties"]))

    def test_every_batch_carries_the_same_balance_duty(self):
        batch = evaluate_mass_property_checks({"specimens": [BASE_RECORD]})
        self.assertTrue(any("same balance" in duty for duty in batch["duties"]))

    def test_a_duplicated_specimen_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mass_property_checks(
                {"specimens": [BASE_RECORD, copy.deepcopy(BASE_RECORD)]}
            )

    def test_an_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mass_property_checks({"specimens": []})

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mass_property_checks("two coupons weighed after bake-out")


if __name__ == "__main__":
    unittest.main()
