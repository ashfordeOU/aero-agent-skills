"""
Offline deterministic tests for e1024_ird_drd_logic.
Run: python3 test_e1024_ird_drd.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1024_ird_drd_logic import (
    categorize_interface_type,
    validate_requirement_id,
    validate_requirement,
    check_duplicate_ids,
    validate_ird_structure,
    check_interface_party_completeness,
    check_verifiability,
    build_ird_summary,
    generate_ird_findings,
    VALID_INTERFACE_TYPES,
    VALID_VERIFICATION_METHODS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_req(req_id="IRD-MECH-001", itype="mechanical", method="T"):
    return {
        "id": req_id,
        "title": "Mounting bracket load limit",
        "description": "The mounting bracket shall withstand a proof load of 500 N.",
        "interface_type": itype,
        "verification_method": method,
    }


def make_valid_ird():
    return {
        "document_id": "PRJ-IRD-001",
        "issue_date": "2026-01-15",
        "project": "DEMO-SAT",
        "item_a": "Payload Unit A",
        "item_b": "Platform Bus B",
        "requirements": [make_valid_req()],
    }


# ---------------------------------------------------------------------------
# categorize_interface_type
# ---------------------------------------------------------------------------

class TestCategorizeInterfaceType(unittest.TestCase):

    def test_mechanical_accepted(self):
        self.assertEqual(categorize_interface_type("mechanical"), "mechanical")

    def test_electrical_accepted(self):
        self.assertEqual(categorize_interface_type("electrical"), "electrical")

    def test_rf_accepted(self):
        self.assertEqual(categorize_interface_type("rf"), "rf")

    def test_thermal_accepted(self):
        self.assertEqual(categorize_interface_type("thermal"), "thermal")

    def test_data_accepted(self):
        self.assertEqual(categorize_interface_type("data"), "data")

    def test_environmental_accepted(self):
        self.assertEqual(categorize_interface_type("environmental"), "environmental")

    def test_human_accepted(self):
        self.assertEqual(categorize_interface_type("human"), "human")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(categorize_interface_type("  thermal  "), "thermal")

    def test_unrecognized_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_interface_type("optical")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_interface_type("")


# ---------------------------------------------------------------------------
# validate_requirement_id
# ---------------------------------------------------------------------------

class TestValidateRequirementId(unittest.TestCase):

    def test_standard_three_segment_id_valid(self):
        self.assertTrue(validate_requirement_id("IRD-MECH-001"))

    def test_two_segment_id_valid(self):
        self.assertTrue(validate_requirement_id("IRD-001"))

    def test_four_digit_suffix_valid(self):
        self.assertTrue(validate_requirement_id("IRD-DATA-0042"))

    def test_lowercase_id_invalid(self):
        self.assertFalse(validate_requirement_id("ird-mech-001"))

    def test_missing_digit_suffix_invalid(self):
        self.assertFalse(validate_requirement_id("IRD-MECH"))

    def test_two_digit_suffix_invalid(self):
        self.assertFalse(validate_requirement_id("IRD-MECH-01"))

    def test_empty_string_invalid(self):
        self.assertFalse(validate_requirement_id(""))

    def test_non_string_invalid(self):
        self.assertFalse(validate_requirement_id(123))

    def test_mixed_case_invalid(self):
        self.assertFalse(validate_requirement_id("Ird-Mech-001"))

    def test_four_segment_id_valid(self):
        self.assertTrue(validate_requirement_id("IRD-DATA-PROTO-042"))


# ---------------------------------------------------------------------------
# validate_requirement
# ---------------------------------------------------------------------------

class TestValidateRequirement(unittest.TestCase):

    def test_fully_valid_requirement_has_no_findings(self):
        self.assertEqual(validate_requirement(make_valid_req()), [])

    def test_missing_title_produces_finding(self):
        req = make_valid_req()
        del req["title"]
        findings = validate_requirement(req)
        self.assertTrue(any("title" in f for f in findings))

    def test_missing_description_produces_finding(self):
        req = make_valid_req()
        del req["description"]
        findings = validate_requirement(req)
        self.assertTrue(any("description" in f for f in findings))

    def test_invalid_interface_type_produces_finding(self):
        req = make_valid_req(itype="optical")
        findings = validate_requirement(req)
        self.assertGreater(len(findings), 0)

    def test_invalid_verification_method_produces_finding(self):
        req = make_valid_req(method="X")
        findings = validate_requirement(req)
        self.assertGreater(len(findings), 0)

    def test_bad_id_format_produces_finding(self):
        req = make_valid_req(req_id="bad-id-format")
        findings = validate_requirement(req)
        self.assertGreater(len(findings), 0)

    def test_all_five_verification_methods_are_valid(self):
        for method in ["T", "A", "I", "R", "D"]:
            req = make_valid_req(method=method)
            self.assertEqual(validate_requirement(req), [],
                             msg=f"method '{method}' should be valid")

    def test_all_seven_interface_types_are_valid(self):
        valid_types = [
            "mechanical", "electrical", "thermal",
            "data", "rf", "environmental", "human",
        ]
        for itype in valid_types:
            req = make_valid_req(
                req_id=f"IRD-{itype[:4].upper()}-001",
                itype=itype,
            )
            self.assertEqual(validate_requirement(req), [],
                             msg=f"type '{itype}' should be valid")


# ---------------------------------------------------------------------------
# check_duplicate_ids
# ---------------------------------------------------------------------------

class TestCheckDuplicateIds(unittest.TestCase):

    def test_two_distinct_ids_no_findings(self):
        req1 = make_valid_req("IRD-MECH-001")
        req2 = make_valid_req("IRD-ELEC-002")
        self.assertEqual(check_duplicate_ids([req1, req2]), [])

    def test_duplicate_id_detected(self):
        req1 = make_valid_req("IRD-MECH-001")
        req2 = make_valid_req("IRD-MECH-001")
        findings = check_duplicate_ids([req1, req2])
        self.assertGreater(len(findings), 0)
        self.assertIn("IRD-MECH-001", findings[0])

    def test_empty_list_has_no_findings(self):
        self.assertEqual(check_duplicate_ids([]), [])

    def test_three_reqs_one_duplicate_one_finding(self):
        reqs = [
            make_valid_req("IRD-MECH-001"),
            make_valid_req("IRD-ELEC-002"),
            make_valid_req("IRD-MECH-001"),
        ]
        findings = check_duplicate_ids(reqs)
        self.assertEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# validate_ird_structure
# ---------------------------------------------------------------------------

class TestValidateIrdStructure(unittest.TestCase):

    def test_valid_ird_has_no_findings(self):
        self.assertEqual(validate_ird_structure(make_valid_ird()), [])

    def test_missing_document_id_produces_finding(self):
        ird = make_valid_ird()
        del ird["document_id"]
        findings = validate_ird_structure(ird)
        self.assertTrue(any("document_id" in f for f in findings))

    def test_missing_project_produces_finding(self):
        ird = make_valid_ird()
        del ird["project"]
        findings = validate_ird_structure(ird)
        self.assertTrue(any("project" in f for f in findings))

    def test_empty_requirements_list_produces_finding(self):
        ird = make_valid_ird()
        ird["requirements"] = []
        findings = validate_ird_structure(ird)
        self.assertGreater(len(findings), 0)

    def test_requirements_not_list_produces_finding(self):
        ird = make_valid_ird()
        ird["requirements"] = "not-a-list"
        findings = validate_ird_structure(ird)
        self.assertGreater(len(findings), 0)

    def test_invalid_req_inside_ird_propagates_finding(self):
        ird = make_valid_ird()
        ird["requirements"][0]["interface_type"] = "unknown"
        findings = validate_ird_structure(ird)
        self.assertGreater(len(findings), 0)

    def test_duplicate_req_ids_propagate(self):
        ird = make_valid_ird()
        ird["requirements"].append(make_valid_req("IRD-MECH-001"))
        findings = validate_ird_structure(ird)
        self.assertTrue(any("Duplicate" in f for f in findings))


# ---------------------------------------------------------------------------
# check_interface_party_completeness
# ---------------------------------------------------------------------------

class TestCheckInterfacePartyCompleteness(unittest.TestCase):

    def test_distinct_valid_parties_no_findings(self):
        self.assertEqual(check_interface_party_completeness(make_valid_ird()), [])

    def test_empty_item_a_produces_finding(self):
        ird = make_valid_ird()
        ird["item_a"] = ""
        findings = check_interface_party_completeness(ird)
        self.assertTrue(any("item_a" in f for f in findings))

    def test_missing_item_b_produces_finding(self):
        ird = make_valid_ird()
        del ird["item_b"]
        findings = check_interface_party_completeness(ird)
        self.assertTrue(any("item_b" in f for f in findings))

    def test_identical_parties_produces_finding(self):
        ird = make_valid_ird()
        ird["item_a"] = "Unit Alpha"
        ird["item_b"] = "Unit Alpha"
        findings = check_interface_party_completeness(ird)
        self.assertGreater(len(findings), 0)

    def test_case_insensitive_identity_check(self):
        ird = make_valid_ird()
        ird["item_a"] = "unit alpha"
        ird["item_b"] = "UNIT ALPHA"
        findings = check_interface_party_completeness(ird)
        self.assertGreater(len(findings), 0)


# ---------------------------------------------------------------------------
# check_verifiability
# ---------------------------------------------------------------------------

class TestCheckVerifiability(unittest.TestCase):

    def test_test_method_is_verifiable(self):
        self.assertTrue(check_verifiability(make_valid_req(method="T")))

    def test_analysis_method_is_verifiable(self):
        self.assertTrue(check_verifiability(make_valid_req(method="A")))

    def test_inspection_method_is_verifiable(self):
        self.assertTrue(check_verifiability(make_valid_req(method="I")))

    def test_review_of_design_is_verifiable(self):
        self.assertTrue(check_verifiability(make_valid_req(method="R")))

    def test_demonstration_is_verifiable(self):
        self.assertTrue(check_verifiability(make_valid_req(method="D")))

    def test_unknown_method_is_not_verifiable(self):
        self.assertFalse(check_verifiability(make_valid_req(method="X")))

    def test_missing_method_is_not_verifiable(self):
        req = make_valid_req()
        del req["verification_method"]
        self.assertFalse(check_verifiability(req))


# ---------------------------------------------------------------------------
# build_ird_summary
# ---------------------------------------------------------------------------

class TestBuildIrdSummary(unittest.TestCase):

    def test_single_requirement_totals(self):
        summary = build_ird_summary(make_valid_ird())
        self.assertEqual(summary["total_requirements"], 1)
        self.assertEqual(summary["interface_type_counts"]["mechanical"], 1)
        self.assertEqual(summary["unverifiable_count"], 0)

    def test_multiple_interface_types_counted(self):
        ird = make_valid_ird()
        ird["requirements"].append(make_valid_req("IRD-ELEC-001", "electrical", "A"))
        ird["requirements"].append(make_valid_req("IRD-THRM-001", "thermal", "I"))
        summary = build_ird_summary(ird)
        self.assertEqual(summary["total_requirements"], 3)
        self.assertIn("electrical", summary["interface_type_counts"])
        self.assertIn("thermal", summary["interface_type_counts"])

    def test_unverifiable_requirement_counted(self):
        ird = make_valid_ird()
        ird["requirements"][0]["verification_method"] = "Z"
        summary = build_ird_summary(ird)
        self.assertEqual(summary["unverifiable_count"], 1)

    def test_verification_method_counts_populated(self):
        ird = make_valid_ird()
        ird["requirements"].append(make_valid_req("IRD-ELEC-001", "electrical", "A"))
        summary = build_ird_summary(ird)
        self.assertEqual(summary["verification_method_counts"]["T"], 1)
        self.assertEqual(summary["verification_method_counts"]["A"], 1)

    def test_non_list_requirements_raises(self):
        ird = make_valid_ird()
        ird["requirements"] = "not-a-list"
        with self.assertRaises(ValueError):
            build_ird_summary(ird)


# ---------------------------------------------------------------------------
# generate_ird_findings
# ---------------------------------------------------------------------------

class TestGenerateIrdFindings(unittest.TestCase):

    def test_fully_valid_ird_is_valid(self):
        result = generate_ird_findings(make_valid_ird())
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["structural_findings"], [])
        self.assertEqual(result["party_findings"], [])

    def test_empty_requirements_makes_ird_invalid(self):
        ird = make_valid_ird()
        ird["requirements"] = []
        result = generate_ird_findings(ird)
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["structural_findings"]), 0)

    def test_identical_parties_makes_ird_invalid(self):
        ird = make_valid_ird()
        ird["item_a"] = "Same Unit"
        ird["item_b"] = "Same Unit"
        result = generate_ird_findings(ird)
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["party_findings"]), 0)

    def test_invalid_req_inside_valid_shell_makes_ird_invalid(self):
        ird = make_valid_ird()
        ird["requirements"][0]["verification_method"] = "Q"
        result = generate_ird_findings(ird)
        self.assertFalse(result["is_valid"])


if __name__ == "__main__":
    unittest.main()
