"""Offline deterministic unit tests for e1006_char_cm_trace_logic.

Run with: python3 test_e1006_char_cm_trace.py
Expected output ends with: OK
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1006_char_cm_trace_logic import (
    REQUIRED_FIELDS,
    SOURCE_TYPES,
    audit_requirement_set,
    audit_single_requirement,
    check_cm_baseline,
    check_source_trace,
    validate_identity,
)


def _make_req(
    req_id="REQ-001",
    title="Sample requirement",
    source_type="parent-req",
    source_ref="SYS-REQ-100",
    baseline="BL-A",
):
    return {
        "id": req_id,
        "title": title,
        "source_type": source_type,
        "source_ref": source_ref,
        "baseline": baseline,
    }


class TestValidateIdentity(unittest.TestCase):
    def test_valid_alphanumeric_id(self):
        self.assertTrue(validate_identity("REQ-001"))

    def test_valid_long_id(self):
        self.assertTrue(validate_identity("SYS-FUNC-REQ-0042"))

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            validate_identity("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            validate_identity("   ")

    def test_integer_raises(self):
        with self.assertRaises(ValueError):
            validate_identity(42)

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            validate_identity(None)


class TestCheckSourceTrace(unittest.TestCase):
    def test_valid_parent_req(self):
        self.assertEqual(check_source_trace("parent-req", "SYS-REQ-100"), [])

    def test_valid_standard(self):
        self.assertEqual(
            check_source_trace("standard", "ECSS-E-ST-10C §8.2.3"), []
        )

    def test_valid_customer_spec(self):
        self.assertEqual(
            check_source_trace("customer-spec", "CUS-SPEC §4.1.2"), []
        )

    def test_valid_interface_req(self):
        self.assertEqual(
            check_source_trace("interface-req", "ICD-001 §3.2"), []
        )

    def test_empty_source_type_flagged(self):
        findings = check_source_trace("", "SYS-REQ-100")
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(any("source_type" in f for f in findings))

    def test_unrecognized_source_type_flagged(self):
        findings = check_source_trace("legacy-doc", "OLD-SPEC §1")
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(any("not a recognised" in f for f in findings))

    def test_empty_source_ref_flagged(self):
        findings = check_source_trace("standard", "")
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(any("source_ref" in f for f in findings))

    def test_both_fields_invalid_gives_two_findings(self):
        findings = check_source_trace("", "")
        self.assertEqual(len(findings), 2)

    def test_non_string_source_type_raises(self):
        with self.assertRaises(ValueError):
            check_source_trace(None, "SYS-REQ-100")

    def test_non_string_source_ref_raises(self):
        with self.assertRaises(ValueError):
            check_source_trace("standard", 42)


class TestCheckCMBaseline(unittest.TestCase):
    def test_valid_baseline(self):
        self.assertEqual(check_cm_baseline("BL-A"), [])

    def test_empty_baseline_flagged(self):
        findings = check_cm_baseline("")
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(any("baseline" in f for f in findings))

    def test_whitespace_only_flagged(self):
        findings = check_cm_baseline("   ")
        self.assertTrue(len(findings) >= 1)

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            check_cm_baseline(None)


class TestAuditSingleRequirement(unittest.TestCase):
    def test_fully_compliant_requirement(self):
        result = audit_single_requirement(_make_req())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["req_id"], "REQ-001")

    def test_empty_baseline_non_compliant(self):
        result = audit_single_requirement(_make_req(baseline=""))
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) >= 1)

    def test_empty_id_non_compliant(self):
        result = audit_single_requirement(_make_req(req_id=""))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("identity" in f for f in result["findings"]))

    def test_invalid_source_type_non_compliant(self):
        result = audit_single_requirement(_make_req(source_type="unknown"))
        self.assertFalse(result["compliant"])

    def test_empty_source_ref_non_compliant(self):
        result = audit_single_requirement(_make_req(source_ref=""))
        self.assertFalse(result["compliant"])

    def test_non_dict_input_raises(self):
        with self.assertRaises(ValueError):
            audit_single_requirement("not-a-dict")

    def test_missing_field_raises(self):
        with self.assertRaises(ValueError):
            audit_single_requirement({"id": "REQ-001", "title": "T"})

    def test_multiple_fields_invalid_gives_multiple_findings(self):
        result = audit_single_requirement(
            _make_req(source_type="", source_ref="", baseline="")
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) >= 3)


class TestAuditRequirementSet(unittest.TestCase):
    def test_all_compliant_set(self):
        reqs = [_make_req("REQ-001"), _make_req("REQ-002")]
        result = audit_requirement_set(reqs)
        self.assertTrue(result["set_compliant"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["compliant"], 2)
        self.assertEqual(result["non_compliant"], 0)
        self.assertEqual(result["duplicate_ids"], [])

    def test_duplicate_ids_flagged(self):
        reqs = [_make_req("REQ-001"), _make_req("REQ-001")]
        result = audit_requirement_set(reqs)
        self.assertIn("REQ-001", result["duplicate_ids"])
        self.assertFalse(result["set_compliant"])
        self.assertEqual(result["non_compliant"], 2)

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            audit_requirement_set("not-a-list")

    def test_non_tuple_dict_raises(self):
        with self.assertRaises(ValueError):
            audit_requirement_set({"id": "REQ-001"})

    def test_empty_set_not_compliant(self):
        result = audit_requirement_set([])
        self.assertEqual(result["total"], 0)
        self.assertFalse(result["set_compliant"])

    def test_mixed_compliant_and_non_compliant(self):
        reqs = [
            _make_req("REQ-001"),
            _make_req("REQ-002", source_type="", source_ref=""),
        ]
        result = audit_requirement_set(reqs)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["compliant"], 1)
        self.assertEqual(result["non_compliant"], 1)
        self.assertFalse(result["set_compliant"])

    def test_single_compliant_requirement(self):
        result = audit_requirement_set([_make_req()])
        self.assertTrue(result["set_compliant"])
        self.assertEqual(result["total"], 1)

    def test_tuple_input_accepted(self):
        result = audit_requirement_set((_make_req("REQ-001"),))
        self.assertTrue(result["set_compliant"])

    def test_three_unique_compliant_requirements(self):
        reqs = [_make_req(f"REQ-{i:03d}") for i in range(1, 4)]
        result = audit_requirement_set(reqs)
        self.assertEqual(result["total"], 3)
        self.assertTrue(result["set_compliant"])

    def test_duplicate_among_non_compliant_still_flagged(self):
        reqs = [
            _make_req("REQ-001", baseline=""),
            _make_req("REQ-001", baseline=""),
        ]
        result = audit_requirement_set(reqs)
        self.assertIn("REQ-001", result["duplicate_ids"])
        for r in result["per_requirement"]:
            self.assertFalse(r["compliant"])


if __name__ == "__main__":
    unittest.main()
