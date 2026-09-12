import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from e1024_iid_guide_logic import (
    VALID_INTERFACE_TYPES,
    VALID_MATURITY_LEVELS,
    IIDValidationError,
    categorize_interface_type,
    assign_maturity_level,
    check_icd_linkage,
    validate_interface_entry,
    validate_iid_collection,
    compute_iid_summary,
    identify_completeness_gaps,
)


def _make_entry(**overrides):
    base = {
        "id": "IF-001",
        "name": "Power bus interface",
        "type": "electrical",
        "maturity": "agreed",
        "side_a": "OBC",
        "side_b": "PDU",
        "icd_ref": "ICD-EPS-001",
    }
    base.update(overrides)
    return base


class TestCategorizeInterfaceType(unittest.TestCase):

    def test_electrical_accepted(self):
        self.assertEqual(categorize_interface_type("electrical"), "electrical")

    def test_rf_uppercase_normalized(self):
        self.assertEqual(categorize_interface_type("RF"), "rf")

    def test_physical_mixed_case(self):
        self.assertEqual(categorize_interface_type("Physical"), "physical")

    def test_all_seven_types_accepted(self):
        for t in VALID_INTERFACE_TYPES:
            self.assertEqual(categorize_interface_type(t), t)

    def test_unrecognized_type_raises(self):
        with self.assertRaises(IIDValidationError):
            categorize_interface_type("mechanical")

    def test_empty_string_raises(self):
        with self.assertRaises(IIDValidationError):
            categorize_interface_type("")

    def test_none_raises(self):
        with self.assertRaises(IIDValidationError):
            categorize_interface_type(None)


class TestAssignMaturityLevel(unittest.TestCase):

    def test_proposed_accepted(self):
        self.assertEqual(assign_maturity_level("proposed"), "proposed")

    def test_agreed_accepted(self):
        self.assertEqual(assign_maturity_level("agreed"), "agreed")

    def test_baselined_accepted(self):
        self.assertEqual(assign_maturity_level("baselined"), "baselined")

    def test_uppercase_normalized(self):
        self.assertEqual(assign_maturity_level("AGREED"), "agreed")

    def test_unrecognized_level_raises(self):
        with self.assertRaises(IIDValidationError):
            assign_maturity_level("draft")

    def test_none_raises(self):
        with self.assertRaises(IIDValidationError):
            assign_maturity_level(None)

    def test_all_valid_levels_accepted(self):
        for level in VALID_MATURITY_LEVELS:
            self.assertEqual(assign_maturity_level(level), level)


class TestCheckIcdLinkage(unittest.TestCase):

    def test_valid_icd_ref_returns_true(self):
        self.assertTrue(check_icd_linkage(_make_entry(icd_ref="ICD-EPS-001")))

    def test_tbd_ref_returns_false(self):
        self.assertFalse(check_icd_linkage(_make_entry(icd_ref="TBD")))

    def test_tbd_lowercase_returns_false(self):
        self.assertFalse(check_icd_linkage(_make_entry(icd_ref="tbd")))

    def test_empty_ref_returns_false(self):
        self.assertFalse(check_icd_linkage(_make_entry(icd_ref="")))

    def test_whitespace_only_ref_returns_false(self):
        self.assertFalse(check_icd_linkage(_make_entry(icd_ref="   ")))

    def test_missing_key_returns_false(self):
        entry = {k: v for k, v in _make_entry().items() if k != "icd_ref"}
        self.assertFalse(check_icd_linkage(entry))


class TestValidateInterfaceEntry(unittest.TestCase):

    def test_valid_entry_returns_empty_issues(self):
        self.assertEqual(validate_interface_entry(_make_entry()), [])

    def test_missing_icd_ref_flagged(self):
        entry = {k: v for k, v in _make_entry().items() if k != "icd_ref"}
        issues = validate_interface_entry(entry)
        self.assertTrue(any("icd_ref" in i for i in issues))

    def test_invalid_type_flagged(self):
        issues = validate_interface_entry(_make_entry(type="mechanical"))
        self.assertTrue(any("invalid interface type" in i for i in issues))

    def test_invalid_maturity_flagged(self):
        issues = validate_interface_entry(_make_entry(maturity="draft"))
        self.assertTrue(any("invalid maturity level" in i for i in issues))

    def test_tbd_icd_ref_flagged(self):
        issues = validate_interface_entry(_make_entry(icd_ref="TBD"))
        self.assertTrue(any("TBD" in i for i in issues))

    def test_empty_name_flagged(self):
        issues = validate_interface_entry(_make_entry(name=""))
        self.assertTrue(any("empty required field" in i for i in issues))

    def test_missing_side_a_flagged(self):
        entry = {k: v for k, v in _make_entry().items() if k != "side_a"}
        issues = validate_interface_entry(entry)
        self.assertTrue(any("side_a" in i for i in issues))

    def test_none_maturity_flagged(self):
        issues = validate_interface_entry(_make_entry(maturity=None))
        self.assertTrue(any("maturity" in i for i in issues))


class TestValidateIidCollection(unittest.TestCase):

    def test_valid_two_entry_collection(self):
        entries = [
            _make_entry(id="IF-001"),
            _make_entry(id="IF-002", type="data", icd_ref="ICD-DH-001"),
        ]
        result = validate_iid_collection(entries)
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_duplicate_id_caught(self):
        entries = [_make_entry(id="IF-001"), _make_entry(id="IF-001")]
        result = validate_iid_collection(entries)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("duplicate" in e["issue"] for e in result["errors"]))

    def test_non_list_raises(self):
        with self.assertRaises(IIDValidationError):
            validate_iid_collection({"id": "IF-001"})

    def test_all_proposed_generates_warning(self):
        entries = [_make_entry(id="IF-001", maturity="proposed")]
        result = validate_iid_collection(entries)
        self.assertTrue(any("proposed" in w for w in result["warnings"]))

    def test_mixed_maturity_no_all_proposed_warning(self):
        entries = [
            _make_entry(id="IF-001", maturity="proposed"),
            _make_entry(id="IF-002", maturity="agreed"),
        ]
        result = validate_iid_collection(entries)
        self.assertFalse(any("all interfaces" in w for w in result["warnings"]))

    def test_summary_total_correct(self):
        entries = [
            _make_entry(id="IF-001"),
            _make_entry(id="IF-002", icd_ref="ICD-DH-001"),
        ]
        result = validate_iid_collection(entries)
        self.assertEqual(result["summary"]["total"], 2)

    def test_empty_collection_is_valid(self):
        result = validate_iid_collection([])
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["summary"]["total"], 0)


class TestComputeIidSummary(unittest.TestCase):

    def test_by_type_counts_correct(self):
        entries = [
            _make_entry(id="IF-001", type="electrical"),
            _make_entry(id="IF-002", type="data", icd_ref="ICD-DH-001"),
            _make_entry(id="IF-003", type="electrical", icd_ref="ICD-EPS-002"),
        ]
        summary = compute_iid_summary(entries)
        self.assertEqual(summary["by_type"]["electrical"], 2)
        self.assertEqual(summary["by_type"]["data"], 1)

    def test_by_maturity_counts_correct(self):
        entries = [
            _make_entry(id="IF-001", maturity="proposed"),
            _make_entry(id="IF-002", maturity="agreed"),
            _make_entry(id="IF-003", maturity="baselined"),
        ]
        summary = compute_iid_summary(entries)
        self.assertEqual(summary["by_maturity"]["proposed"], 1)
        self.assertEqual(summary["by_maturity"]["agreed"], 1)
        self.assertEqual(summary["by_maturity"]["baselined"], 1)

    def test_icd_gap_count_and_ids(self):
        entries = [
            _make_entry(id="IF-001", icd_ref="TBD"),
            _make_entry(id="IF-002", icd_ref="ICD-001"),
        ]
        summary = compute_iid_summary(entries)
        self.assertEqual(summary["icd_gap_count"], 1)
        self.assertIn("IF-001", summary["icd_gap_ids"])
        self.assertNotIn("IF-002", summary["icd_gap_ids"])

    def test_empty_collection_summary(self):
        summary = compute_iid_summary([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["icd_gap_count"], 0)
        self.assertEqual(summary["by_type"], {})
        self.assertEqual(summary["by_maturity"], {})


class TestIdentifyCompletenessGaps(unittest.TestCase):

    def test_no_icd_linkage_gap_detected(self):
        entries = [_make_entry(id="IF-001", icd_ref="")]
        gaps = identify_completeness_gaps(entries)
        self.assertIn("IF-001", gaps["no_icd_linkage"])

    def test_proposed_maturity_gap_detected(self):
        entries = [_make_entry(id="IF-001", maturity="proposed")]
        gaps = identify_completeness_gaps(entries)
        self.assertIn("IF-001", gaps["proposed_maturity"])

    def test_missing_side_a_detected(self):
        entries = [_make_entry(id="IF-001", side_a="")]
        gaps = identify_completeness_gaps(entries)
        self.assertIn("IF-001", gaps["no_side_a_responsible"])

    def test_missing_side_b_detected(self):
        entries = [_make_entry(id="IF-001", side_b="")]
        gaps = identify_completeness_gaps(entries)
        self.assertIn("IF-001", gaps["no_side_b_responsible"])

    def test_fully_valid_entry_produces_no_gaps(self):
        entries = [_make_entry(id="IF-001", maturity="baselined")]
        gaps = identify_completeness_gaps(entries)
        self.assertEqual(gaps["no_icd_linkage"], [])
        self.assertEqual(gaps["proposed_maturity"], [])
        self.assertEqual(gaps["no_side_a_responsible"], [])
        self.assertEqual(gaps["no_side_b_responsible"], [])

    def test_tbd_icd_ref_counted_as_gap(self):
        entries = [_make_entry(id="IF-001", icd_ref="TBD")]
        gaps = identify_completeness_gaps(entries)
        self.assertIn("IF-001", gaps["no_icd_linkage"])

    def test_multiple_gaps_across_entries(self):
        entries = [
            _make_entry(id="IF-001", icd_ref="TBD", maturity="proposed"),
            _make_entry(id="IF-002", side_b=""),
            _make_entry(id="IF-003", maturity="baselined"),
        ]
        gaps = identify_completeness_gaps(entries)
        self.assertIn("IF-001", gaps["no_icd_linkage"])
        self.assertIn("IF-001", gaps["proposed_maturity"])
        self.assertIn("IF-002", gaps["no_side_b_responsible"])
        self.assertNotIn("IF-003", gaps["no_icd_linkage"])


if __name__ == "__main__":
    unittest.main()
