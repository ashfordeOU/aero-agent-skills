#!/usr/bin/env python3
"""Contract test for the visible defect applicability envelope (offline)."""

import copy
import unittest

from e2008_visual_defect_requirement_applicability_logic import (
    ASSEMBLY_CATEGORIES,
    DEFAULT_APPLICABILITY_POLICY,
    ENVELOPE_ESTABLISHED,
    ENVELOPE_INCOMPLETE,
    EXTENSION,
    GOVERNED,
    OUT_OF_SCOPE,
    REFER,
    SUBMISSION_PURPOSES,
    assess_assembly_applicability,
    map_qualification_applicability,
    validate_applicability_policy,
)

BASE_ITEM = {
    "assembly_id": "SCA-001",
    "category": "coverglassed-assembly",
    "purpose": "qualification-approval",
    "build_standard": "BS-QUAL-A",
    "process_representativeness": 1.0,
    "sample_count": 4,
}


def _item(**overrides):
    item = copy.deepcopy(BASE_ITEM)
    item.update(overrides)
    return item


def _full_population():
    return [
        _item(assembly_id="SCA-001", category="coverglassed-assembly"),
        _item(assembly_id="SCA-002", category="interconnected-assembly"),
        _item(assembly_id="SCA-003", category="diode-equipped-assembly"),
    ]


def _submission(items, **overrides):
    submission = {"submission_id": "QUAL-2026-01", "assemblies": items}
    submission.update(overrides)
    return submission


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_applicability_policy(DEFAULT_APPLICABILITY_POLICY),
            DEFAULT_APPLICABILITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_applicability_policy("default")

    def test_empty_category_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["applicable_categories"] = []
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_repeated_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["applicable_categories"] = [
            "coverglassed-assembly",
            "coverglassed-assembly",
        ]
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_unknown_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["applicable_categories"] = ["laminated-panel"]
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_information_only_cannot_be_an_approval_purpose(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["approval_purposes"] = ["information-only"]
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_representativeness_floor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["min_process_representativeness"] = 1.4
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_zero_items_per_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["min_items_per_category"] = 0
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)


class ItemApplicabilityTests(unittest.TestCase):
    def test_representative_in_category_item_is_governed(self):
        result = assess_assembly_applicability(_item())
        self.assertEqual(result["state"], GOVERNED)
        self.assertTrue(result["counts_toward_coverage"])

    def test_information_only_item_is_outside_the_envelope(self):
        result = assess_assembly_applicability(_item(purpose="information-only"))
        self.assertEqual(result["state"], OUT_OF_SCOPE)
        self.assertFalse(result["governed"])
        self.assertTrue(
            any("no approval turns on it" in reason for reason in result["reasons"])
        )

    def test_lot_acceptance_item_is_governed_by_a_different_clause(self):
        result = assess_assembly_applicability(_item(purpose="lot-acceptance"))
        self.assertEqual(result["state"], OUT_OF_SCOPE)
        self.assertTrue(
            any("inherits the approval" in reason for reason in result["reasons"])
        )

    def test_extension_purpose_is_still_governed(self):
        result = assess_assembly_applicability(
            _item(purpose="qualification-extension")
        )
        self.assertEqual(result["state"], GOVERNED)
        self.assertTrue(
            any("extension to an existing approval" in r for r in result["reasons"])
        )

    def test_out_of_list_category_is_not_reached(self):
        result = assess_assembly_applicability(
            _item(category="assembly-on-substrate-coupon")
        )
        self.assertEqual(result["state"], OUT_OF_SCOPE)

    def test_unqualified_build_points_at_an_extension_not_a_failure(self):
        result = assess_assembly_applicability(_item(build_standard="BS-DEV-C"))
        self.assertEqual(result["state"], EXTENSION)
        self.assertTrue(result["governed"])
        self.assertFalse(result["counts_toward_coverage"])

    def test_non_representative_sample_goes_to_review(self):
        result = assess_assembly_applicability(
            _item(process_representativeness=0.5)
        )
        self.assertEqual(result["state"], REFER)
        self.assertFalse(result["counts_toward_coverage"])

    def test_representativeness_exactly_on_the_floor_is_governed(self):
        floor = DEFAULT_APPLICABILITY_POLICY["min_process_representativeness"]
        result = assess_assembly_applicability(
            _item(process_representativeness=floor)
        )
        self.assertAlmostEqual(
            result["process_representativeness"], floor, places=9
        )
        self.assertEqual(result["state"], GOVERNED)

    def test_purpose_is_checked_before_the_category(self):
        result = assess_assembly_applicability(
            _item(purpose="information-only", category="assembly-on-substrate-coupon")
        )
        self.assertTrue(
            any("no approval turns on it" in reason for reason in result["reasons"])
        )

    def test_unknown_purpose_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_applicability(_item(purpose="flight-spare"))

    def test_blank_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_applicability(_item(assembly_id="   "))

    def test_zero_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_applicability(_item(sample_count=0))

    def test_representativeness_outside_the_unit_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_applicability(_item(process_representativeness=1.2))

    def test_every_declared_category_and_purpose_is_recognised(self):
        self.assertEqual(len(ASSEMBLY_CATEGORIES), 5)
        self.assertEqual(len(SUBMISSION_PURPOSES), 4)


class SubmissionTests(unittest.TestCase):
    def test_a_complete_population_establishes_the_envelope(self):
        result = map_qualification_applicability(_submission(_full_population()))
        self.assertEqual(result["verdict"], ENVELOPE_ESTABLISHED)
        self.assertEqual(result["uncovered_categories"], [])
        self.assertAlmostEqual(result["governed_sample_fraction"], 1.0, places=9)

    def test_a_missing_category_leaves_the_envelope_incomplete(self):
        items = _full_population()[:2]
        result = map_qualification_applicability(_submission(items))
        self.assertEqual(result["verdict"], ENVELOPE_INCOMPLETE)
        self.assertEqual(result["uncovered_categories"], ["diode-equipped-assembly"])

    def test_an_extension_item_does_not_cover_its_category(self):
        items = _full_population()
        items[2]["build_standard"] = "BS-DEV-C"
        result = map_qualification_applicability(_submission(items))
        self.assertEqual(result["extension_required_ids"], ["SCA-003"])
        self.assertEqual(result["uncovered_categories"], ["diode-equipped-assembly"])

    def test_a_review_item_keeps_the_envelope_open(self):
        items = _full_population()
        items[1]["process_representativeness"] = 0.4
        result = map_qualification_applicability(_submission(items))
        self.assertEqual(result["verdict"], ENVELOPE_INCOMPLETE)
        self.assertEqual(result["review_ids"], ["SCA-002"])

    def test_out_of_scope_samples_reduce_the_governed_fraction(self):
        items = _full_population()
        items.append(
            _item(
                assembly_id="SCA-004",
                purpose="information-only",
                sample_count=12,
            )
        )
        result = map_qualification_applicability(_submission(items))
        self.assertEqual(result["total_sample_count"], 24)
        self.assertEqual(result["governed_sample_count"], 12)
        self.assertAlmostEqual(result["governed_sample_fraction"], 0.5, places=9)
        self.assertEqual(result["out_of_scope_ids"], ["SCA-004"])

    def test_two_items_per_category_can_be_demanded(self):
        policy = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        policy["min_items_per_category"] = 2
        result = map_qualification_applicability(
            _submission(_full_population()), policy
        )
        self.assertEqual(len(result["uncovered_categories"]), 3)

    def test_duplicate_assembly_ids_rejected(self):
        items = _full_population()
        items[1]["assembly_id"] = "SCA-001"
        with self.assertRaises(ValueError):
            map_qualification_applicability(_submission(items))

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            map_qualification_applicability(_submission([]))

    def test_non_list_assemblies_rejected(self):
        with self.assertRaises(ValueError):
            map_qualification_applicability(_submission("SCA-001"))

    def test_non_mapping_submission_rejected(self):
        with self.assertRaises(ValueError):
            map_qualification_applicability("QUAL-2026-01")

    def test_state_counts_add_up_to_the_population(self):
        items = _full_population()
        items.append(_item(assembly_id="SCA-004", purpose="information-only"))
        result = map_qualification_applicability(_submission(items))
        self.assertEqual(sum(result["state_counts"].values()), 4)


if __name__ == "__main__":
    unittest.main()
