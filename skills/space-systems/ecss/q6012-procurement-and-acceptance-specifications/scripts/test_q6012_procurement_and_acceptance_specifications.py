#!/usr/bin/env python3
"""Contract test for the procurement and acceptance document pair (offline)."""

import copy
import unittest

from q6012_procurement_and_acceptance_specifications_logic import (
    ACCEPTANCE_CONTENT_ITEMS,
    DEFAULT_SPECIFICATION_POLICY,
    PROCUREMENT_CONTENT_ITEMS,
    SHARED_CONTENT_ITEMS,
    SPECIFICATION_SET_INCOMPLETE,
    SPECIFICATION_SET_RELEASABLE,
    assess_specification_set,
    conflicting_shared_items,
    content_gaps,
    cross_reference_findings,
    is_stated,
    misallocated_items,
    required_sample_size,
    sampling_plan_findings,
    validate_document,
    validate_sampling_plan,
    validate_specification_policy,
)

PROCUREMENT = {
    "document_id": "procurement-spec-1",
    "content": {
        "die-identification": "die-type-x-rev-b",
        "electrical-parameter-limits": "limit-table-a",
        "usage-condition-envelope": "usage-envelope-1",
        "approved-application-reference": "application-approval-1",
        "marking-and-traceability": "lot-and-date-code",
        "packing-and-handling": "waffle-pack-with-esd-control",
        "acceptance-specification-reference": "acceptance-spec-1",
        "nonconformance-handling": "quarantine-and-report",
    },
}

ACCEPTANCE = {
    "document_id": "acceptance-spec-1",
    "content": {
        "die-identification": "die-type-x-rev-b",
        "lot-definition": "single-diffusion-lot",
        "sampling-plan": "attribute-sample-per-lot",
        "electrical-acceptance-tests": "dc-and-rf-parameters",
        "environmental-acceptance-tests": "thermal-and-mechanical-screen",
        "accept-reject-criteria": "per-parameter-limit-table",
        "acceptance-test-sequence": "electrical-then-environmental",
        "data-package-content": "measured-data-and-certificate",
        "lot-rejection-handling": "segregate-and-notify",
    },
}

SAMPLING_PLAN = {"lot_size": 200, "sample_size": 10, "accept_number": 1}

BASE_CASE = {
    "procurement": PROCUREMENT,
    "acceptance": ACCEPTANCE,
    "sampling_plan": SAMPLING_PLAN,
}


def _doc(base, **content):
    document = copy.deepcopy(base)
    document["content"].update(content)
    return document


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class StatedTests(unittest.TestCase):
    def test_a_filled_string_is_stated(self):
        self.assertTrue(is_stated("lot-and-date-code"))

    def test_an_empty_string_is_not_stated(self):
        self.assertFalse(is_stated(""))

    def test_a_whitespace_string_is_not_stated(self):
        self.assertFalse(is_stated("   "))

    def test_an_absent_value_is_not_stated(self):
        self.assertFalse(is_stated(None))

    def test_an_empty_list_is_not_stated(self):
        self.assertFalse(is_stated([]))

    def test_a_number_is_stated(self):
        self.assertTrue(is_stated(0))


class DocumentValidationTests(unittest.TestCase):
    def test_a_well_formed_document_normalises(self):
        result = validate_document(PROCUREMENT, "procurement specification")
        self.assertEqual(result["document_id"], "procurement-spec-1")

    def test_a_document_without_an_identifier_is_rejected(self):
        broken = copy.deepcopy(PROCUREMENT)
        del broken["document_id"]
        with self.assertRaises(ValueError):
            validate_document(broken, "procurement specification")

    def test_a_document_without_content_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_document(
                {"document_id": "procurement-spec-1"}, "procurement specification"
            )

    def test_a_non_mapping_document_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_document("procurement-spec-1", "procurement specification")


class ContentGapTests(unittest.TestCase):
    def test_the_base_documents_have_no_gaps(self):
        proc = content_gaps(PROCUREMENT, PROCUREMENT_CONTENT_ITEMS, "procurement")
        acc = content_gaps(ACCEPTANCE, ACCEPTANCE_CONTENT_ITEMS, "acceptance")
        self.assertEqual(proc["absent"], [])
        self.assertEqual(acc["absent"], [])
        self.assertEqual(proc["unstated"], [])

    def test_an_omitted_item_is_reported_absent(self):
        broken = copy.deepcopy(PROCUREMENT)
        del broken["content"]["marking-and-traceability"]
        gaps = content_gaps(broken, PROCUREMENT_CONTENT_ITEMS, "procurement")
        self.assertEqual(gaps["absent"], ["marking-and-traceability"])

    def test_a_listed_but_empty_item_is_reported_unstated(self):
        broken = _doc(PROCUREMENT, **{"packing-and-handling": "  "})
        gaps = content_gaps(broken, PROCUREMENT_CONTENT_ITEMS, "procurement")
        self.assertEqual(gaps["unstated"], ["packing-and-handling"])
        self.assertEqual(gaps["absent"], [])

    def test_every_shared_item_is_required_by_the_buying_document(self):
        for item in SHARED_CONTENT_ITEMS:
            self.assertIn(item, PROCUREMENT_CONTENT_ITEMS)


class AllocationTests(unittest.TestCase):
    def test_the_base_pair_is_correctly_allocated(self):
        self.assertEqual(misallocated_items(PROCUREMENT, ACCEPTANCE), [])

    def test_an_acceptance_item_in_the_buying_document_is_reported(self):
        broken = _doc(PROCUREMENT, **{"lot-definition": "single-diffusion-lot"})
        findings = misallocated_items(broken, ACCEPTANCE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["item"], "lot-definition")
        self.assertEqual(findings[0]["belongs_to"], "acceptance")

    def test_a_buying_item_in_the_acceptance_document_is_reported(self):
        broken = _doc(ACCEPTANCE, **{"packing-and-handling": "waffle-pack"})
        findings = misallocated_items(PROCUREMENT, broken)
        self.assertEqual(findings[0]["found_in"], "acceptance")
        self.assertEqual(findings[0]["belongs_to"], "procurement")

    def test_a_shared_item_in_both_documents_is_not_a_misallocation(self):
        both = _doc(ACCEPTANCE, **{"usage-condition-envelope": "usage-envelope-1"})
        self.assertEqual(misallocated_items(PROCUREMENT, both), [])


class ConsistencyTests(unittest.TestCase):
    def test_agreeing_shared_items_raise_nothing(self):
        self.assertEqual(conflicting_shared_items(PROCUREMENT, ACCEPTANCE), [])

    def test_a_shared_item_stated_differently_is_a_conflict(self):
        broken = _doc(ACCEPTANCE, **{"die-identification": "die-type-x-rev-a"})
        conflicts = conflicting_shared_items(PROCUREMENT, broken)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["item"], "die-identification")

    def test_a_shared_item_only_one_document_carries_is_not_a_conflict(self):
        reduced = copy.deepcopy(ACCEPTANCE)
        del reduced["content"]["die-identification"]
        self.assertEqual(conflicting_shared_items(PROCUREMENT, reduced), [])


class CrossReferenceTests(unittest.TestCase):
    def test_a_matching_reference_raises_nothing(self):
        self.assertEqual(cross_reference_findings(PROCUREMENT, ACCEPTANCE), [])

    def test_a_missing_reference_is_reported(self):
        broken = copy.deepcopy(PROCUREMENT)
        del broken["content"]["acceptance-specification-reference"]
        self.assertEqual(len(cross_reference_findings(broken, ACCEPTANCE)), 1)

    def test_a_reference_to_another_document_is_reported(self):
        broken = _doc(
            PROCUREMENT, **{"acceptance-specification-reference": "acceptance-spec-9"}
        )
        findings = cross_reference_findings(broken, ACCEPTANCE)
        self.assertEqual(len(findings), 1)
        self.assertIn("acceptance-spec-9", findings[0])


class SamplingTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_specification_policy(DEFAULT_SPECIFICATION_POLICY),
            DEFAULT_SPECIFICATION_POLICY,
        )

    def test_a_fraction_of_one_is_rejected(self):
        broken = dict(DEFAULT_SPECIFICATION_POLICY, min_sample_fraction=1.0)
        with self.assertRaises(ValueError):
            validate_specification_policy(broken)

    def test_a_non_integer_floor_is_rejected(self):
        broken = dict(DEFAULT_SPECIFICATION_POLICY, min_sample_count=5.5)
        with self.assertRaises(ValueError):
            validate_specification_policy(broken)

    def test_the_proportional_rule_governs_a_large_lot(self):
        self.assertEqual(required_sample_size(200), 10)
        self.assertEqual(required_sample_size(1000), 50)

    def test_the_floor_governs_a_small_lot(self):
        self.assertEqual(required_sample_size(20), 5)

    def test_the_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_size(3), 3)

    def test_a_coherent_plan_normalises(self):
        plan = validate_sampling_plan(SAMPLING_PLAN)
        self.assertAlmostEqual(plan["sampling_fraction"], 0.05, places=9)
        self.assertAlmostEqual(plan["accept_fraction"], 0.1, places=9)

    def test_a_sample_larger_than_the_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan(
                {"lot_size": 10, "sample_size": 20, "accept_number": 0}
            )

    def test_an_accept_number_covering_the_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan(
                {"lot_size": 200, "sample_size": 10, "accept_number": 10}
            )

    def test_a_zero_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan(
                {"lot_size": 0, "sample_size": 1, "accept_number": 0}
            )

    def test_the_base_plan_raises_no_policy_finding(self):
        self.assertEqual(sampling_plan_findings(SAMPLING_PLAN), [])

    def test_an_undersized_sample_is_reported(self):
        findings = sampling_plan_findings(
            {"lot_size": 200, "sample_size": 8, "accept_number": 0}
        )
        self.assertEqual(len(findings), 1)

    def test_an_accept_fraction_above_the_ceiling_is_reported(self):
        findings = sampling_plan_findings(
            {"lot_size": 200, "sample_size": 10, "accept_number": 3}
        )
        self.assertTrue(any("ceiling" in f for f in findings))


class AssessmentTests(unittest.TestCase):
    def test_a_complete_pair_is_releasable(self):
        result = assess_specification_set(BASE_CASE)
        self.assertEqual(result["verdict"], SPECIFICATION_SET_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_fraction"], 1.0, places=9)

    def test_one_omitted_item_lowers_the_completeness_fraction(self):
        broken = copy.deepcopy(PROCUREMENT)
        del broken["content"]["nonconformance-handling"]
        result = assess_specification_set(_case(procurement=broken))
        self.assertEqual(result["verdict"], SPECIFICATION_SET_INCOMPLETE)
        self.assertAlmostEqual(
            result["completeness_fraction"], 16.0 / 17.0, places=9
        )

    def test_a_missing_sampling_plan_is_a_finding_not_a_pass(self):
        case = _case()
        del case["sampling_plan"]
        result = assess_specification_set(case)
        self.assertEqual(result["verdict"], SPECIFICATION_SET_INCOMPLETE)
        self.assertIsNone(result["sampling_plan"])

    def test_a_broken_cross_reference_blocks_release(self):
        broken = _doc(
            PROCUREMENT, **{"acceptance-specification-reference": "acceptance-spec-9"}
        )
        result = assess_specification_set(_case(procurement=broken))
        self.assertEqual(result["verdict"], SPECIFICATION_SET_INCOMPLETE)

    def test_a_shared_item_conflict_blocks_release(self):
        broken = _doc(ACCEPTANCE, **{"die-identification": "die-type-x-rev-a"})
        result = assess_specification_set(_case(acceptance=broken))
        self.assertEqual(len(result["conflicting_items"]), 1)
        self.assertEqual(result["verdict"], SPECIFICATION_SET_INCOMPLETE)

    def test_an_unstated_item_counts_against_completeness(self):
        broken = _doc(ACCEPTANCE, **{"data-package-content": ""})
        result = assess_specification_set(_case(acceptance=broken))
        self.assertIn("data-package-content", result["acceptance_gaps"]["unstated"])
        self.assertAlmostEqual(
            result["completeness_fraction"], 16.0 / 17.0, places=9
        )

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_specification_set(PROCUREMENT["content"]["die-identification"])

    def test_every_required_item_is_counted_once(self):
        self.assertEqual(
            len(PROCUREMENT_CONTENT_ITEMS) + len(ACCEPTANCE_CONTENT_ITEMS), 17
        )
        self.assertEqual(len(set(PROCUREMENT_CONTENT_ITEMS)), 8)
        self.assertEqual(len(set(ACCEPTANCE_CONTENT_ITEMS)), 9)


if __name__ == "__main__":
    unittest.main()
