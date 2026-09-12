import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from pfci_fci_flli_lists_logic import (
    categorize_item,
    build_pfcil,
    build_fcil,
    build_fllil,
    check_documentation,
    check_config_control,
    SAFE_LIFE_RATIO_THRESHOLD,
)


def _make_exempt(**kwargs):
    base = {
        "id": "E-001",
        "fracture_sensitive": False,
        "failure_consequence": "non-critical",
        "compliance_method": None,
        "safe_life_ratio": None,
        "has_life_limit": False,
        "life_limit_cycles": None,
        "docs": [],
    }
    base.update(kwargs)
    return base


def _make_pfci(**kwargs):
    base = {
        "id": "P-001",
        "fracture_sensitive": True,
        "failure_consequence": "critical",
        "compliance_method": "analysis",
        "safe_life_ratio": 5.0,
        "has_life_limit": False,
        "life_limit_cycles": None,
        "docs": ["pfci_screening_record", "fracture_sensitivity_justification"],
    }
    base.update(kwargs)
    return base


def _make_fci(**kwargs):
    base = {
        "id": "F-001",
        "fracture_sensitive": True,
        "failure_consequence": "critical",
        "compliance_method": "analysis",
        "safe_life_ratio": 2.0,
        "has_life_limit": False,
        "life_limit_cycles": None,
        "docs": [
            "pfci_screening_record",
            "fracture_sensitivity_justification",
            "fracture_control_analysis",
            "initial_flaw_assumption",
            "inspection_plan",
        ],
    }
    base.update(kwargs)
    return base


def _make_flli(**kwargs):
    base = {
        "id": "L-001",
        "fracture_sensitive": True,
        "failure_consequence": "critical",
        "compliance_method": "analysis",
        "safe_life_ratio": 3.0,
        "has_life_limit": True,
        "life_limit_cycles": 5000,
        "docs": [
            "pfci_screening_record",
            "fracture_sensitivity_justification",
            "fracture_control_analysis",
            "initial_flaw_assumption",
            "inspection_plan",
            "life_limit_calculation",
            "replacement_or_retirement_plan",
        ],
    }
    base.update(kwargs)
    return base


class TestCategorizeItem(unittest.TestCase):

    def test_exempt_when_not_fracture_sensitive(self):
        self.assertEqual(categorize_item(_make_exempt(fracture_sensitive=False,
                                                      failure_consequence="critical")), "exempt")

    def test_exempt_when_non_critical_consequence(self):
        self.assertEqual(categorize_item(_make_exempt(fracture_sensitive=True,
                                                      failure_consequence="non-critical")), "exempt")

    def test_pfci_when_no_compliance_method(self):
        self.assertEqual(categorize_item(_make_pfci(compliance_method=None,
                                                    safe_life_ratio=None)), "pfci")

    def test_pfci_when_ratio_at_threshold(self):
        self.assertEqual(categorize_item(_make_pfci(
            safe_life_ratio=SAFE_LIFE_RATIO_THRESHOLD)), "pfci")

    def test_pfci_when_ratio_exceeds_threshold(self):
        self.assertEqual(categorize_item(_make_pfci(safe_life_ratio=10.0)), "pfci")

    def test_fci_when_ratio_below_threshold(self):
        self.assertEqual(categorize_item(_make_fci(safe_life_ratio=2.0)), "fci")

    def test_fci_when_ratio_just_below_threshold(self):
        self.assertEqual(categorize_item(_make_fci(safe_life_ratio=3.99)), "fci")

    def test_fci_when_proof_test_insufficient(self):
        self.assertEqual(categorize_item(_make_fci(compliance_method="proof_test",
                                                   safe_life_ratio=1.5)), "fci")

    def test_flli_when_life_limit_set(self):
        self.assertEqual(categorize_item(_make_flli()), "flli")

    def test_flli_with_catastrophic_consequence(self):
        self.assertEqual(categorize_item(_make_flli(failure_consequence="catastrophic")),
                         "flli")

    def test_raises_on_missing_fracture_sensitive_key(self):
        item = {"failure_consequence": "critical"}
        with self.assertRaises(ValueError):
            categorize_item(item)

    def test_raises_on_missing_failure_consequence_key(self):
        item = {"fracture_sensitive": True}
        with self.assertRaises(ValueError):
            categorize_item(item)

    def test_raises_on_invalid_failure_consequence(self):
        with self.assertRaises(ValueError):
            categorize_item(_make_pfci(failure_consequence="unknown"))

    def test_raises_on_invalid_compliance_method(self):
        with self.assertRaises(ValueError):
            categorize_item(_make_pfci(compliance_method="guess", safe_life_ratio=3.0))

    def test_raises_when_compliance_set_but_ratio_absent(self):
        with self.assertRaises(ValueError):
            categorize_item(_make_pfci(compliance_method="analysis", safe_life_ratio=None))

    def test_raises_on_non_dict_input(self):
        with self.assertRaises(TypeError):
            categorize_item("not-a-dict")


class TestListBuilders(unittest.TestCase):

    def setUp(self):
        self.items = [
            _make_exempt(id="E-001"),
            _make_pfci(id="P-001"),
            _make_fci(id="F-001"),
            _make_flli(id="L-001"),
        ]

    def test_pfcil_excludes_exempt(self):
        ids = [e["id"] for e in build_pfcil(self.items)]
        self.assertNotIn("E-001", ids)

    def test_pfcil_includes_pfci_fci_flli(self):
        ids = [e["id"] for e in build_pfcil(self.items)]
        self.assertIn("P-001", ids)
        self.assertIn("F-001", ids)
        self.assertIn("L-001", ids)

    def test_fcil_excludes_exempt_and_pfci_only(self):
        ids = [e["id"] for e in build_fcil(self.items)]
        self.assertNotIn("E-001", ids)
        self.assertNotIn("P-001", ids)

    def test_fcil_includes_fci_and_flli(self):
        ids = [e["id"] for e in build_fcil(self.items)]
        self.assertIn("F-001", ids)
        self.assertIn("L-001", ids)

    def test_fllil_contains_only_flli(self):
        result = build_fllil(self.items)
        self.assertEqual([e["id"] for e in result], ["L-001"])

    def test_pfcil_category_annotations(self):
        cats = {e["id"]: e["_category"] for e in build_pfcil(self.items)}
        self.assertEqual(cats["P-001"], "pfci")
        self.assertEqual(cats["F-001"], "fci")
        self.assertEqual(cats["L-001"], "flli")

    def test_fllil_empty_when_no_flli_items(self):
        items = [_make_exempt(), _make_pfci(), _make_fci()]
        self.assertEqual(build_fllil(items), [])

    def test_list_builders_do_not_mutate_originals(self):
        original = _make_pfci(id="P-002")
        build_pfcil([original])
        self.assertNotIn("_category", original)


class TestDocumentationCheck(unittest.TestCase):

    def test_exempt_item_requires_no_docs(self):
        self.assertEqual(check_documentation(_make_exempt()), [])

    def test_pfci_with_all_docs_has_no_gaps(self):
        self.assertEqual(check_documentation(_make_pfci()), [])

    def test_pfci_missing_screening_record(self):
        item = _make_pfci(docs=["fracture_sensitivity_justification"])
        self.assertIn("pfci_screening_record", check_documentation(item))

    def test_fci_with_all_docs_has_no_gaps(self):
        self.assertEqual(check_documentation(_make_fci()), [])

    def test_fci_missing_fracture_analysis(self):
        item = _make_fci(docs=[
            "pfci_screening_record",
            "fracture_sensitivity_justification",
            "initial_flaw_assumption",
            "inspection_plan",
        ])
        self.assertIn("fracture_control_analysis", check_documentation(item))

    def test_flli_with_all_docs_has_no_gaps(self):
        self.assertEqual(check_documentation(_make_flli()), [])

    def test_flli_missing_life_limit_calculation(self):
        item = _make_flli(docs=[
            "pfci_screening_record",
            "fracture_sensitivity_justification",
            "fracture_control_analysis",
            "initial_flaw_assumption",
            "inspection_plan",
            "replacement_or_retirement_plan",
        ])
        self.assertIn("life_limit_calculation", check_documentation(item))

    def test_check_documentation_result_is_sorted(self):
        item = _make_fci(docs=[])
        missing = check_documentation(item)
        self.assertEqual(missing, sorted(missing))

    def test_fci_no_docs_returns_all_required(self):
        item = _make_fci(docs=[])
        missing = check_documentation(item)
        self.assertGreater(len(missing), 0)


class TestConfigControl(unittest.TestCase):

    def _valid_meta(self):
        return {
            "issue_number": "Rev-A",
            "approval_date": "2026-01-15",
            "approved_by": "Chief Structures Engineer",
        }

    def _valid_entries(self):
        return [
            {"id": "S-001", "status": "active"},
            {"id": "S-002", "status": "active"},
        ]

    def test_no_findings_on_valid_list(self):
        self.assertEqual(check_config_control(self._valid_meta(), self._valid_entries()), [])

    def test_missing_issue_number_flagged(self):
        meta = self._valid_meta()
        del meta["issue_number"]
        self.assertIn("list_missing_issue_number", check_config_control(meta, self._valid_entries()))

    def test_missing_approval_date_flagged(self):
        meta = self._valid_meta()
        del meta["approval_date"]
        self.assertIn("list_missing_approval_date", check_config_control(meta, self._valid_entries()))

    def test_missing_approved_by_flagged(self):
        meta = self._valid_meta()
        del meta["approved_by"]
        self.assertIn("list_missing_approved_by", check_config_control(meta, self._valid_entries()))

    def test_duplicate_item_id_flagged(self):
        entries = [{"id": "S-001", "status": "active"}, {"id": "S-001", "status": "active"}]
        findings = check_config_control(self._valid_meta(), entries)
        self.assertTrue(any("duplicate_item_id" in f for f in findings))

    def test_entry_missing_id_flagged(self):
        entries = [{"status": "active"}]
        findings = check_config_control(self._valid_meta(), entries)
        self.assertTrue(any("missing_item_id" in f for f in findings))

    def test_removed_item_without_justification_flagged(self):
        entries = [{"id": "S-001", "status": "removed"}]
        findings = check_config_control(self._valid_meta(), entries)
        self.assertTrue(any("removed_without_justification" in f for f in findings))

    def test_removed_item_with_justification_passes(self):
        entries = [{"id": "S-001", "status": "removed",
                    "removal_justification": "Redesigned per DR-001"}]
        findings = check_config_control(self._valid_meta(), entries)
        self.assertNotIn("item:S-001:removed_without_justification", findings)

    def test_empty_entries_list_is_valid(self):
        self.assertEqual(check_config_control(self._valid_meta(), []), [])

    def test_raises_when_metadata_not_dict(self):
        with self.assertRaises(TypeError):
            check_config_control("not-a-dict", [])

    def test_raises_when_entries_not_list(self):
        with self.assertRaises(TypeError):
            check_config_control(self._valid_meta(), "not-a-list")

    def test_result_is_sorted(self):
        meta = {}
        findings = check_config_control(meta, [])
        self.assertEqual(findings, sorted(findings))


if __name__ == "__main__":
    unittest.main()
