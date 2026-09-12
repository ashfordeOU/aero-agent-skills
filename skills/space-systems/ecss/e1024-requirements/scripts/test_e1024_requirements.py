#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-24C §5.3 interface requirements.

Exercises scripts/e1024_requirements_logic.py (stdlib unittest, offline).
Contract: a requirement category is one of functional / physical / environmental
/ data_characteristic and an unrecognized label raises; every requirement must
carry id, text, category, rationale, and verification_method with non-empty
values; an interface must be covered by at least one requirement in each of the
four mandatory categories; duplicate requirement IDs within an interface are
flagged; the aggregated review is compliant only when all three finding lists are
empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1024_requirements_logic as rl  # noqa: E402


class CategorizeRequirementTest(unittest.TestCase):
    def test_functional_accepted(self):
        self.assertEqual(rl.categorize_requirement("functional"), "functional")

    def test_physical_accepted(self):
        self.assertEqual(rl.categorize_requirement("physical"), "physical")

    def test_environmental_accepted(self):
        self.assertEqual(rl.categorize_requirement("environmental"), "environmental")

    def test_data_characteristic_accepted(self):
        self.assertEqual(
            rl.categorize_requirement("data_characteristic"), "data_characteristic"
        )

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            rl.categorize_requirement("thermal_control")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            rl.categorize_requirement("")


class ValidateRequirementFieldsTest(unittest.TestCase):
    def _good_req(self):
        return {
            "id": "IRD-IF1-F-001",
            "text": "The interface shall transfer telemetry at 1 Mbit/s.",
            "category": "functional",
            "rationale": "Mission data rate budget allocation.",
            "verification_method": "test",
        }

    def test_fully_formed_requirement_has_no_issues(self):
        self.assertEqual(rl.validate_requirement_fields(self._good_req()), [])

    def test_missing_id_flagged(self):
        req = self._good_req()
        del req["id"]
        issues = rl.validate_requirement_fields(req)
        self.assertTrue(any(i["field"] == "id" for i in issues))

    def test_missing_rationale_flagged(self):
        req = self._good_req()
        del req["rationale"]
        issues = rl.validate_requirement_fields(req)
        self.assertTrue(any(i["field"] == "rationale" for i in issues))

    def test_empty_text_flagged(self):
        req = self._good_req()
        req["text"] = "   "
        issues = rl.validate_requirement_fields(req)
        self.assertTrue(any(i["field"] == "text" for i in issues))

    def test_missing_verification_method_flagged(self):
        req = self._good_req()
        del req["verification_method"]
        issues = rl.validate_requirement_fields(req)
        self.assertTrue(any(i["field"] == "verification_method" for i in issues))

    def test_invalid_category_flagged(self):
        req = self._good_req()
        req["category"] = "optical"
        issues = rl.validate_requirement_fields(req)
        self.assertTrue(any(i["issue"] == "invalid_category" for i in issues))

    def test_empty_rationale_flagged(self):
        req = self._good_req()
        req["rationale"] = ""
        issues = rl.validate_requirement_fields(req)
        self.assertTrue(any(i["field"] == "rationale" for i in issues))


class CheckCategoryCoverageTest(unittest.TestCase):
    def _all_categories_reqs(self):
        return [
            {"id": "F-001", "category": "functional"},
            {"id": "P-001", "category": "physical"},
            {"id": "E-001", "category": "environmental"},
            {"id": "D-001", "category": "data_characteristic"},
        ]

    def test_full_coverage_has_no_gaps(self):
        self.assertEqual(
            rl.check_category_coverage("IF-1", self._all_categories_reqs()), []
        )

    def test_missing_physical_flagged(self):
        reqs = [
            {"id": "F-001", "category": "functional"},
            {"id": "E-001", "category": "environmental"},
            {"id": "D-001", "category": "data_characteristic"},
        ]
        gaps = rl.check_category_coverage("IF-1", reqs)
        self.assertTrue(any(g["category"] == "physical" for g in gaps))

    def test_empty_requirements_flags_all_four_categories(self):
        gaps = rl.check_category_coverage("IF-1", [])
        categories_flagged = {g["category"] for g in gaps}
        self.assertEqual(categories_flagged, rl.MANDATORY_CATEGORIES)

    def test_single_missing_environmental_flagged(self):
        reqs = [
            {"id": "F-001", "category": "functional"},
            {"id": "P-001", "category": "physical"},
            {"id": "D-001", "category": "data_characteristic"},
        ]
        gaps = rl.check_category_coverage("IF-2", reqs)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["category"], "environmental")


class CheckDuplicateIdsTest(unittest.TestCase):
    def test_unique_ids_no_finding(self):
        reqs = [{"id": "R-001"}, {"id": "R-002"}]
        self.assertEqual(rl.check_duplicate_ids("IF-1", reqs), [])

    def test_duplicate_id_flagged(self):
        reqs = [{"id": "R-001"}, {"id": "R-001"}, {"id": "R-002"}]
        findings = rl.check_duplicate_ids("IF-1", reqs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["req_id"], "R-001")
        self.assertEqual(findings[0]["issue"], "duplicate_requirement_id")

    def test_no_id_field_ignored(self):
        reqs = [{"text": "no id here"}, {"text": "also no id"}]
        self.assertEqual(rl.check_duplicate_ids("IF-1", reqs), [])


class InterfaceRequirementsReviewTest(unittest.TestCase):
    def _compliant_interface(self):
        return {
            "interface_id": "IF-OBC-PLM-001",
            "requirements": [
                {
                    "id": "F-001",
                    "text": "Transfer housekeeping at 10 kbit/s.",
                    "category": "functional",
                    "rationale": "Housekeeping data rate budget.",
                    "verification_method": "test",
                },
                {
                    "id": "P-001",
                    "text": "38-way D-sub connector on panel A.",
                    "category": "physical",
                    "rationale": "Connector heritage from PDR baseline.",
                    "verification_method": "inspection",
                },
                {
                    "id": "E-001",
                    "text": "Operate across -40 deg C to +80 deg C at the connector.",
                    "category": "environmental",
                    "rationale": "Thermal analysis worst-case envelope.",
                    "verification_method": "analysis",
                },
                {
                    "id": "D-001",
                    "text": "CCSDS Space Packet Protocol, version 1.",
                    "category": "data_characteristic",
                    "rationale": "Mission data standard.",
                    "verification_method": "review",
                },
            ],
        }

    def test_compliant_interface_has_no_findings(self):
        review = rl.interface_requirements_review(self._compliant_interface())
        self.assertEqual(review["field_issues"], [])
        self.assertEqual(review["coverage_gaps"], [])
        self.assertEqual(review["duplicate_ids"], [])
        self.assertTrue(rl.is_ird_compliant(review))

    def test_missing_category_flagged_in_review(self):
        iface = self._compliant_interface()
        iface["requirements"] = [
            r for r in iface["requirements"] if r["category"] != "physical"
        ]
        review = rl.interface_requirements_review(iface)
        self.assertTrue(
            any(g["category"] == "physical" for g in review["coverage_gaps"])
        )
        self.assertFalse(rl.is_ird_compliant(review))

    def test_field_issue_flagged_in_review(self):
        iface = self._compliant_interface()
        iface["requirements"][0]["text"] = ""
        review = rl.interface_requirements_review(iface)
        self.assertTrue(review["field_issues"])
        self.assertFalse(rl.is_ird_compliant(review))

    def test_unrecognized_category_raises(self):
        iface = {
            "interface_id": "IF-BAD",
            "requirements": [
                {
                    "id": "X-001",
                    "text": "Some requirement.",
                    "category": "optical_link",
                    "rationale": "Unknown origin.",
                    "verification_method": "test",
                }
            ],
        }
        with self.assertRaises(ValueError):
            rl.interface_requirements_review(iface)

    def test_duplicate_id_flagged_in_review(self):
        iface = self._compliant_interface()
        dup = dict(iface["requirements"][0])
        dup["text"] = "Duplicate entry with same id."
        iface["requirements"].append(dup)
        review = rl.interface_requirements_review(iface)
        self.assertTrue(
            any(d["req_id"] == "F-001" for d in review["duplicate_ids"])
        )
        self.assertFalse(rl.is_ird_compliant(review))

    def test_empty_interface_has_coverage_gaps_only(self):
        iface = {"interface_id": "IF-EMPTY", "requirements": []}
        review = rl.interface_requirements_review(iface)
        self.assertEqual(review["field_issues"], [])
        self.assertEqual(len(review["coverage_gaps"]), 4)
        self.assertEqual(review["duplicate_ids"], [])
        self.assertFalse(rl.is_ird_compliant(review))


if __name__ == "__main__":
    unittest.main()
