#!/usr/bin/env python3
"""Gate 3 contract test for e2040-updated-verification-validation-plans.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_updated_verification_validation_plans.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_updated_verification_validation_plans_logic import (  # noqa: E402
    PLAN_KINDS,
    assess_updated_plans,
    meets_refresh_target,
    normalize_plan_kind,
    plan_delta,
    refresh_ratio,
    revision_is_newer,
    revision_ordinal,
    validate_architecture,
    validate_plan,
)


def base_case():
    return {
        "architecture": {
            "revision": "2.0",
            "blocks": ["BLK-CTRL", "BLK-IO"],
            "requirements": ["R-1", "R-2"],
            "reallocations": {"R-2": "BLK-IO"},
        },
        "plans": [
            {
                "kind": "verification",
                "revision": "1.1",
                "baseline_revision": "1.0",
                "architecture_revision": "2.0",
                "entries": [
                    {
                        "requirement": "R-1",
                        "block": "BLK-CTRL",
                        "method": "test",
                        "level": "device",
                        "touched": True,
                    },
                    {
                        "requirement": "R-2",
                        "block": "BLK-IO",
                        "method": "analysis",
                        "level": "device",
                        "touched": True,
                    },
                ],
            },
            {
                "kind": "validation",
                "revision": "1.1",
                "baseline_revision": "1.0",
                "architecture_revision": "2.0",
                "entries": [
                    {
                        "requirement": "R-1",
                        "block": "BLK-CTRL",
                        "method": "demonstration in the string",
                        "level": "subsystem",
                        "touched": True,
                    },
                    {
                        "requirement": "R-2",
                        "block": "BLK-IO",
                        "method": "operational scenario run",
                        "level": "subsystem",
                        "touched": True,
                    },
                ],
            },
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_short_form_folds_to_verification(self):
        self.assertEqual(normalize_plan_kind("verif"), "verification")

    def test_validation_folds(self):
        self.assertEqual(normalize_plan_kind("Validation"), "validation")

    def test_unknown_plan_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_plan_kind("qualification")

    def test_two_plan_kinds_are_owed(self):
        self.assertEqual(len(PLAN_KINDS), 2)


class TestRevisionOrdering(unittest.TestCase):
    def test_a_later_revision_is_newer(self):
        self.assertTrue(revision_is_newer("1.2", "1.1"))

    def test_the_same_revision_is_not_newer(self):
        self.assertFalse(revision_is_newer("1.1", "1.1"))

    def test_a_double_digit_component_orders_numerically(self):
        self.assertTrue(revision_is_newer("1.10", "1.9"))

    def test_a_letter_component_orders_below_a_number(self):
        self.assertTrue(revision_is_newer("1.1", "1.a"))

    def test_an_empty_component_rejected(self):
        with self.assertRaises(ValueError):
            revision_ordinal("1..2")

    def test_a_blank_revision_rejected(self):
        with self.assertRaises(ValueError):
            revision_ordinal("   ")


class TestValidation(unittest.TestCase):
    def test_the_architecture_resolves(self):
        architecture = validate_architecture(base_case()["architecture"])
        self.assertEqual(architecture["requirements"], ["R-1", "R-2"])

    def test_duplicate_block_rejected(self):
        architecture = base_case()["architecture"]
        architecture["blocks"].append("BLK-IO")
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_unknown_architecture_key_rejected(self):
        architecture = base_case()["architecture"]
        architecture["owner"] = "x"
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_a_reallocation_to_an_unknown_block_rejected(self):
        architecture = base_case()["architecture"]
        architecture["reallocations"] = {"R-1": "BLK-GHOST"}
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_a_reallocation_of_an_unknown_requirement_rejected(self):
        architecture = base_case()["architecture"]
        architecture["reallocations"] = {"R-9": "BLK-IO"}
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_the_plan_resolves_entries_by_requirement(self):
        plan = validate_plan(base_case()["plans"][0])
        self.assertEqual(sorted(plan["entries"]), ["R-1", "R-2"])

    def test_a_repeated_requirement_in_a_plan_rejected(self):
        plan = base_case()["plans"][0]
        plan["entries"].append(dict(plan["entries"][0]))
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_an_unknown_entry_key_rejected(self):
        plan = base_case()["plans"][0]
        plan["entries"][0]["owner"] = "x"
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_a_non_boolean_touched_flag_rejected(self):
        plan = base_case()["plans"][0]
        plan["entries"][0]["touched"] = "yes"
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_a_plan_without_an_architecture_revision_rejected(self):
        plan = base_case()["plans"][0]
        del plan["architecture_revision"]
        with self.assertRaises(ValueError):
            validate_plan(plan)


class TestRefreshArithmetic(unittest.TestCase):
    def test_every_entry_touched_is_a_full_refresh(self):
        plan = validate_plan(base_case()["plans"][0])
        self.assertAlmostEqual(refresh_ratio(plan), 1.0, places=9)

    def test_one_of_three_touched_is_a_third(self):
        plan = base_case()["plans"][0]
        plan["entries"][1]["touched"] = False
        plan["entries"].append({"requirement": "R-3", "method": "test"})
        self.assertAlmostEqual(refresh_ratio(validate_plan(plan)), 1 / 3, places=9)

    def test_refresh_needs_an_entry(self):
        plan = base_case()["plans"][0]
        plan["entries"] = []
        with self.assertRaises(ValueError):
            refresh_ratio(validate_plan(plan))

    def test_a_target_met_exactly_is_met(self):
        self.assertTrue(meets_refresh_target(2 / 4, 0.5))

    def test_a_target_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_refresh_target(1 / 3, 1 / 3))

    def test_a_target_missed_is_missed(self):
        self.assertFalse(meets_refresh_target(0.4, 0.5))

    def test_a_target_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_refresh_target(0.5, 2.0)


class TestPlanDelta(unittest.TestCase):
    def test_an_added_requirement_is_reported(self):
        delta = plan_delta({"R-1": {"block": "A"}}, {"R-1": {"block": "A"}, "R-2": {"block": "B"}})
        self.assertEqual(delta["added"], ["R-2"])

    def test_a_removed_requirement_is_reported(self):
        delta = plan_delta({"R-1": {"block": "A"}, "R-2": {"block": "B"}}, {"R-1": {"block": "A"}})
        self.assertEqual(delta["removed"], ["R-2"])

    def test_a_changed_block_is_reported(self):
        delta = plan_delta({"R-1": {"block": "A"}}, {"R-1": {"block": "B"}})
        self.assertEqual(delta["changed"], ["R-1"])

    def test_an_unchanged_entry_is_not_reported(self):
        delta = plan_delta({"R-1": {"block": "A"}}, {"R-1": {"block": "A"}})
        self.assertEqual(delta, {"added": [], "removed": [], "changed": []})

    def test_delta_needs_two_mappings(self):
        with self.assertRaises(ValueError):
            plan_delta([], {})


class TestAssessUpdatedPlans(unittest.TestCase):
    def test_a_refreshed_pair_is_current(self):
        result = assess_updated_plans(base_case())
        self.assertTrue(result["current"])
        self.assertEqual(result["findings"], [])

    def test_the_refresh_ratio_reaches_the_result(self):
        result = assess_updated_plans(base_case())
        self.assertAlmostEqual(result["plans"]["verification"]["refresh_ratio"], 1.0, places=9)

    def test_a_missing_validation_plan_is_reported(self):
        case = base_case()
        case["plans"] = [case["plans"][0]]
        result = assess_updated_plans(case)
        self.assertIn("plan-not-supplied", codes(result))

    def test_two_plans_of_one_kind_rejected(self):
        case = base_case()
        case["plans"][1]["kind"] = "verification"
        with self.assertRaises(ValueError):
            assess_updated_plans(case)

    def test_a_plan_citing_a_stale_architecture_is_reported(self):
        case = base_case()
        case["plans"][0]["architecture_revision"] = "1.0"
        result = assess_updated_plans(case)
        self.assertIn("plan-cites-stale-architecture", codes(result))

    def test_a_plan_whose_revision_did_not_move_is_reported(self):
        case = base_case()
        case["plans"][1]["revision"] = "1.0"
        result = assess_updated_plans(case)
        self.assertIn("plan-revision-did-not-move", codes(result))

    def test_a_requirement_with_no_entry_is_reported(self):
        case = base_case()
        case["architecture"]["requirements"].append("R-3")
        result = assess_updated_plans(case)
        self.assertIn("requirement-without-updated-entry", codes(result))

    def test_an_entry_for_a_retired_requirement_is_reported(self):
        case = base_case()
        case["plans"][0]["entries"].append(
            {"requirement": "R-9", "block": "BLK-IO", "method": "test", "touched": True}
        )
        result = assess_updated_plans(case)
        self.assertIn("entry-for-retired-requirement", codes(result))

    def test_an_entry_naming_a_retired_block_is_reported(self):
        case = base_case()
        case["plans"][0]["entries"][0]["block"] = "BLK-OLD"
        result = assess_updated_plans(case)
        self.assertIn("entry-references-retired-block", codes(result))

    def test_an_entry_not_refreshed_after_reallocation_is_reported(self):
        case = base_case()
        case["plans"][0]["entries"][1]["block"] = "BLK-CTRL"
        result = assess_updated_plans(case)
        self.assertIn("entry-not-refreshed-after-reallocation", codes(result))

    def test_a_reallocated_entry_pointing_at_the_new_block_is_accepted(self):
        result = assess_updated_plans(base_case())
        self.assertNotIn("entry-not-refreshed-after-reallocation", codes(result))

    def test_an_entry_without_a_method_is_reported(self):
        case = base_case()
        case["plans"][1]["entries"][0]["method"] = ""
        result = assess_updated_plans(case)
        self.assertIn("entry-without-method", codes(result))

    def test_a_refresh_target_met_exactly_does_not_fail(self):
        case = base_case()
        case["refresh_target"] = 2 / 2
        result = assess_updated_plans(case)
        self.assertNotIn("refresh-target-missed", codes(result))

    def test_a_refresh_target_missed_is_reported(self):
        case = base_case()
        case["plans"][0]["entries"][0]["touched"] = False
        case["refresh_target"] = 0.9
        result = assess_updated_plans(case)
        self.assertIn("refresh-target-missed", codes(result))

    def test_unknown_case_key_rejected(self):
        case = base_case()
        case["owner"] = "someone"
        with self.assertRaises(ValueError):
            assess_updated_plans(case)

    def test_missing_plans_rejected(self):
        case = base_case()
        del case["plans"]
        with self.assertRaises(ValueError):
            assess_updated_plans(case)

    def test_non_list_plans_rejected(self):
        case = base_case()
        case["plans"] = {"kind": "verification"}
        with self.assertRaises(ValueError):
            assess_updated_plans(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_updated_plans([("plans", [])])


if __name__ == "__main__":
    unittest.main()
