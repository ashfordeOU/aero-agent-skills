import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1024_eicd_subsystem_logic import (
    validate_interface_type,
    check_interface_record,
    check_requirement_traceability,
    check_bidirectional_consistency,
    check_eicd_document,
    assess_eicd,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_interface(
    interface_id="IF-001",
    itype="mechanical",
    sub_a="OBC",
    sub_b="ADCS",
    req_ids=None,
    verification="test",
    description="Mechanical mounting between OBC and ADCS",
):
    return {
        "interface_id": interface_id,
        "interface_type": itype,
        "subsystem_a": sub_a,
        "subsystem_b": sub_b,
        "description": description,
        "requirement_ids": req_ids if req_ids is not None else ["SYS-IF-001"],
        "verification_method": verification,
    }


def _make_eicd(interfaces=None):
    return {
        "document_id": "EICD-SS-001",
        "revision": "A",
        "space_segment_id": "SC-001",
        "interfaces": interfaces if interfaces is not None else [_make_interface()],
        "applicable_documents": ["ECSS-E-ST-10-24C"],
    }


# ---------------------------------------------------------------------------
# validate_interface_type
# ---------------------------------------------------------------------------

class TestValidateInterfaceType(unittest.TestCase):

    def test_mechanical_accepted(self):
        self.assertTrue(validate_interface_type("mechanical"))

    def test_data_accepted(self):
        self.assertTrue(validate_interface_type("data"))

    def test_electrical_power_accepted(self):
        self.assertTrue(validate_interface_type("electrical_power"))

    def test_rf_accepted(self):
        self.assertTrue(validate_interface_type("rf"))

    def test_unknown_type_rejected(self):
        self.assertFalse(validate_interface_type("chemical"))

    def test_empty_string_rejected(self):
        self.assertFalse(validate_interface_type(""))

    def test_none_rejected(self):
        self.assertFalse(validate_interface_type(None))

    def test_integer_rejected(self):
        self.assertFalse(validate_interface_type(42))

    def test_uppercase_accepted(self):
        self.assertTrue(validate_interface_type("MECHANICAL"))

    def test_mixed_case_accepted(self):
        self.assertTrue(validate_interface_type("Thermal"))


# ---------------------------------------------------------------------------
# check_interface_record
# ---------------------------------------------------------------------------

class TestCheckInterfaceRecord(unittest.TestCase):

    def test_valid_record_no_findings(self):
        self.assertEqual(check_interface_record(_make_interface()), [])

    def test_missing_interface_type_flagged(self):
        r = _make_interface()
        del r["interface_type"]
        findings = check_interface_record(r)
        self.assertTrue(any("interface_type" in f for f in findings))

    def test_missing_interface_id_flagged(self):
        r = _make_interface()
        del r["interface_id"]
        findings = check_interface_record(r)
        self.assertTrue(any("interface_id" in f for f in findings))

    def test_empty_requirement_ids_list_flagged(self):
        r = _make_interface(req_ids=[])
        findings = check_interface_record(r)
        self.assertTrue(any("requirement_ids" in f for f in findings))

    def test_same_subsystem_flagged(self):
        r = _make_interface(sub_a="OBC", sub_b="OBC")
        findings = check_interface_record(r)
        self.assertTrue(any("distinct" in f for f in findings))

    def test_unrecognized_interface_type_flagged(self):
        r = _make_interface(itype="quantum_entanglement")
        findings = check_interface_record(r)
        self.assertTrue(any("interface_type" in f for f in findings))

    def test_unrecognized_verification_method_flagged(self):
        r = _make_interface(verification="prototype")
        findings = check_interface_record(r)
        self.assertTrue(any("verification_method" in f for f in findings))

    def test_non_dict_returns_finding(self):
        findings = check_interface_record("not a dict")
        self.assertGreater(len(findings), 0)

    def test_requirement_ids_not_list_flagged(self):
        r = _make_interface()
        r["requirement_ids"] = "SYS-IF-001"
        findings = check_interface_record(r)
        self.assertTrue(any("requirement_ids" in f for f in findings))

    def test_all_valid_verification_methods_pass(self):
        for method in ("test", "analysis", "inspection", "review_of_design", "similarity"):
            with self.subTest(method=method):
                r = _make_interface(verification=method)
                self.assertEqual(check_interface_record(r), [])


# ---------------------------------------------------------------------------
# check_requirement_traceability
# ---------------------------------------------------------------------------

class TestCheckRequirementTraceability(unittest.TestCase):

    def test_all_ids_resolved(self):
        r = _make_interface(req_ids=["SYS-001", "SYS-002"])
        registry = {"SYS-001", "SYS-002", "SYS-003"}
        self.assertEqual(check_requirement_traceability(r, registry), [])

    def test_unresolved_id_returned(self):
        r = _make_interface(req_ids=["SYS-999"])
        unresolved = check_requirement_traceability(r, {"SYS-001"})
        self.assertIn("SYS-999", unresolved)

    def test_empty_registry_all_ids_unresolved(self):
        r = _make_interface(req_ids=["SYS-001", "SYS-002"])
        unresolved = check_requirement_traceability(r, set())
        self.assertEqual(sorted(unresolved), ["SYS-001", "SYS-002"])

    def test_partial_resolution(self):
        r = _make_interface(req_ids=["SYS-001", "SYS-002"])
        unresolved = check_requirement_traceability(r, {"SYS-001"})
        self.assertNotIn("SYS-001", unresolved)
        self.assertIn("SYS-002", unresolved)


# ---------------------------------------------------------------------------
# check_bidirectional_consistency
# ---------------------------------------------------------------------------

class TestCheckBidirectionalConsistency(unittest.TestCase):

    def test_distinct_pairs_no_conflict(self):
        ifaces = [
            _make_interface("IF-001", "mechanical", "OBC", "ADCS"),
            _make_interface("IF-002", "data",       "OBC", "ADCS"),
            _make_interface("IF-003", "mechanical", "OBC", "EPS"),
        ]
        self.assertEqual(check_bidirectional_consistency(ifaces), [])

    def test_same_pair_same_type_conflict(self):
        ifaces = [
            _make_interface("IF-001", "mechanical", "OBC", "ADCS"),
            _make_interface("IF-002", "mechanical", "OBC", "ADCS"),
        ]
        conflicts = check_bidirectional_consistency(ifaces)
        self.assertEqual(len(conflicts), 1)

    def test_reversed_pair_treated_as_same(self):
        ifaces = [
            _make_interface("IF-001", "thermal", "ADCS", "OBC"),
            _make_interface("IF-002", "thermal", "OBC",  "ADCS"),
        ]
        conflicts = check_bidirectional_consistency(ifaces)
        self.assertEqual(len(conflicts), 1)

    def test_empty_list_no_conflict(self):
        self.assertEqual(check_bidirectional_consistency([]), [])

    def test_single_interface_no_conflict(self):
        self.assertEqual(
            check_bidirectional_consistency([_make_interface()]), []
        )


# ---------------------------------------------------------------------------
# check_eicd_document
# ---------------------------------------------------------------------------

class TestCheckEicdDocument(unittest.TestCase):

    def test_valid_document_no_findings(self):
        self.assertEqual(check_eicd_document(_make_eicd()), [])

    def test_missing_document_id_flagged(self):
        doc = _make_eicd()
        del doc["document_id"]
        findings = check_eicd_document(doc)
        self.assertTrue(any("document_id" in f for f in findings))

    def test_missing_revision_flagged(self):
        doc = _make_eicd()
        del doc["revision"]
        findings = check_eicd_document(doc)
        self.assertTrue(any("revision" in f for f in findings))

    def test_empty_interfaces_list_flagged(self):
        doc = _make_eicd(interfaces=[])
        findings = check_eicd_document(doc)
        self.assertTrue(any("interfaces" in f for f in findings))

    def test_non_dict_input_flagged(self):
        findings = check_eicd_document("not a dict")
        self.assertGreater(len(findings), 0)


# ---------------------------------------------------------------------------
# assess_eicd
# ---------------------------------------------------------------------------

class TestAssessEicd(unittest.TestCase):

    def test_fully_compliant_eicd(self):
        result = assess_eicd(_make_eicd(), requirement_registry={"SYS-IF-001"})
        self.assertTrue(result["compliant"])
        self.assertEqual(result["document_findings"], [])
        self.assertEqual(result["interface_findings"], {})
        self.assertEqual(result["traceability_findings"], {})
        self.assertEqual(result["consistency_findings"], [])

    def test_traceability_gap_makes_non_compliant(self):
        result = assess_eicd(_make_eicd(), requirement_registry=set())
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["traceability_findings"]), 0)

    def test_duplicate_interface_makes_non_compliant(self):
        ifaces = [
            _make_interface("IF-001", "mechanical", "OBC", "ADCS"),
            _make_interface("IF-002", "mechanical", "OBC", "ADCS"),
        ]
        result = assess_eicd(_make_eicd(interfaces=ifaces), {"SYS-IF-001"})
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["consistency_findings"]), 0)

    def test_missing_eicd_section_makes_non_compliant(self):
        doc = _make_eicd()
        del doc["revision"]
        result = assess_eicd(doc)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["document_findings"]), 0)

    def test_invalid_interface_record_makes_non_compliant(self):
        r = _make_interface()
        del r["interface_type"]
        result = assess_eicd(_make_eicd(interfaces=[r]), {"SYS-IF-001"})
        self.assertFalse(result["compliant"])
        self.assertIn("IF-001", result["interface_findings"])

    def test_non_dict_eicd_handled_gracefully(self):
        result = assess_eicd("bad input")
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["document_findings"]), 0)

    def test_multiple_valid_interfaces_all_compliant(self):
        registry = {"SYS-IF-001", "SYS-IF-002", "SYS-IF-003"}
        ifaces = [
            _make_interface("IF-001", "mechanical",        "OBC",  "ADCS", ["SYS-IF-001"]),
            _make_interface("IF-002", "data",              "OBC",  "EPS",  ["SYS-IF-002"]),
            _make_interface("IF-003", "thermal",           "ADCS", "EPS",  ["SYS-IF-003"]),
        ]
        result = assess_eicd(_make_eicd(interfaces=ifaces), registry)
        self.assertTrue(result["compliant"])

    def test_default_empty_registry_used_when_none_given(self):
        result = assess_eicd(_make_eicd())
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["traceability_findings"]), 0)


if __name__ == "__main__":
    unittest.main()
