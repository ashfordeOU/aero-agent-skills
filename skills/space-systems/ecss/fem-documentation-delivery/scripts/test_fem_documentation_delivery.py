#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C model documentation and delivery
(MMDD) package verification.

Exercises scripts/fem_documentation_delivery_logic.py (stdlib unittest,
offline). Contract: a document type is valid if it appears in the
required or optional set, and unrecognized types raise; metadata field
checking produces one finding per missing required field; document
completeness produces one finding per missing required document type and
raises on unrecognized types; revision consistency passes when all
documents share the same model_revision, produces a mismatch finding
when they differ, and raises when model_revision is absent; file
delivery produces one finding per missing required file type; the full
package assessment aggregates all four checks; and is_delivery_compliant
is True only when every finding list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fem_documentation_delivery_logic as mmdd  # noqa: E402


def _full_doc(document_type, model_revision="A"):
    return {
        "document_type": document_type,
        "document_id": "DOC-" + document_type.upper(),
        "revision": "1",
        "model_id": "FEM-001",
        "model_revision": model_revision,
        "author": "J. Engineer",
        "date": "2026-09-12",
    }


def _complete_package(model_revision="A"):
    documents = [_full_doc(dt, model_revision) for dt in mmdd.REQUIRED_DOCUMENT_TYPES]
    files = [
        {"file_type": "fem_input_file", "name": "model.bdf"},
        {"file_type": "documentation_package", "name": "docs.zip"},
    ]
    return {"documents": documents, "files": files}


class ValidateDocumentTypeTest(unittest.TestCase):
    def test_required_type_returns_required(self):
        self.assertEqual(mmdd.validate_document_type("model_description"), "required")

    def test_another_required_type_returns_required(self):
        self.assertEqual(mmdd.validate_document_type("element_quality_report"), "required")

    def test_optional_type_returns_optional(self):
        self.assertEqual(mmdd.validate_document_type("modal_analysis_summary"), "optional")

    def test_another_optional_type_returns_optional(self):
        self.assertEqual(mmdd.validate_document_type("model_correlation_report"), "optional")

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            mmdd.validate_document_type("mystery_fem_annex")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            mmdd.validate_document_type("")


class CheckMetadataFieldsTest(unittest.TestCase):
    def test_fully_populated_document_has_no_violations(self):
        doc = _full_doc("model_description")
        self.assertEqual(mmdd.check_metadata_fields(doc), [])

    def test_missing_author_flagged(self):
        doc = _full_doc("model_description")
        doc.pop("author")
        violations = mmdd.check_metadata_fields(doc)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_metadata_field")
        self.assertEqual(violations[0]["field"], "author")

    def test_missing_date_flagged(self):
        doc = _full_doc("model_description")
        doc.pop("date")
        violations = mmdd.check_metadata_fields(doc)
        issues = [v["field"] for v in violations]
        self.assertIn("date", issues)

    def test_multiple_missing_fields_all_flagged(self):
        doc = {"document_type": "load_case_list"}
        violations = mmdd.check_metadata_fields(doc)
        missing_fields = {v["field"] for v in violations}
        self.assertTrue(missing_fields.issuperset(mmdd.REQUIRED_METADATA_FIELDS))

    def test_does_not_mutate_document(self):
        doc = _full_doc("mass_properties_check")
        original = dict(doc)
        mmdd.check_metadata_fields(doc)
        self.assertEqual(doc, original)


class CheckDocumentCompletenessTest(unittest.TestCase):
    def test_all_required_types_present_no_violations(self):
        docs = [_full_doc(dt) for dt in mmdd.REQUIRED_DOCUMENT_TYPES]
        self.assertEqual(mmdd.check_document_completeness(docs), [])

    def test_empty_document_list_flags_all_required(self):
        violations = mmdd.check_document_completeness([])
        missing = {v["document_type"] for v in violations}
        self.assertEqual(missing, mmdd.REQUIRED_DOCUMENT_TYPES)

    def test_single_missing_required_type_flagged(self):
        types = mmdd.REQUIRED_DOCUMENT_TYPES - {"load_case_list"}
        docs = [_full_doc(dt) for dt in types]
        violations = mmdd.check_document_completeness(docs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["document_type"], "load_case_list")

    def test_optional_type_does_not_satisfy_required(self):
        docs = [_full_doc("modal_analysis_summary")]
        violations = mmdd.check_document_completeness(docs)
        missing = {v["document_type"] for v in violations}
        self.assertEqual(missing, mmdd.REQUIRED_DOCUMENT_TYPES)

    def test_unrecognized_document_type_raises(self):
        docs = [{"document_type": "unknown_annex_x"}]
        with self.assertRaises(ValueError):
            mmdd.check_document_completeness(docs)


class CheckRevisionConsistencyTest(unittest.TestCase):
    def test_all_same_revision_no_violations(self):
        docs = [_full_doc(dt, "B") for dt in mmdd.REQUIRED_DOCUMENT_TYPES]
        self.assertEqual(mmdd.check_revision_consistency(docs), [])

    def test_empty_document_list_returns_empty(self):
        self.assertEqual(mmdd.check_revision_consistency([]), [])

    def test_revision_mismatch_flagged(self):
        docs = [
            _full_doc("model_description", "A"),
            _full_doc("element_quality_report", "B"),
        ]
        violations = mmdd.check_revision_consistency(docs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "revision_mismatch")
        self.assertIn("A", violations[0]["revisions_found"])
        self.assertIn("B", violations[0]["revisions_found"])

    def test_missing_model_revision_raises(self):
        doc = _full_doc("model_description")
        doc.pop("model_revision")
        with self.assertRaises(ValueError):
            mmdd.check_revision_consistency([doc])

    def test_three_way_mismatch_all_revisions_listed(self):
        docs = [
            _full_doc("model_description", "A"),
            _full_doc("element_quality_report", "B"),
            _full_doc("load_case_list", "C"),
        ]
        violations = mmdd.check_revision_consistency(docs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(sorted(violations[0]["revisions_found"]), ["A", "B", "C"])


class CheckFileDeliveryTest(unittest.TestCase):
    def test_all_required_file_types_no_violations(self):
        files = [
            {"file_type": "fem_input_file"},
            {"file_type": "documentation_package"},
        ]
        self.assertEqual(mmdd.check_file_delivery(files), [])

    def test_empty_file_list_flags_all_required(self):
        violations = mmdd.check_file_delivery([])
        missing = {v["file_type"] for v in violations}
        self.assertEqual(missing, mmdd.REQUIRED_FILE_TYPES)

    def test_missing_fem_input_file_flagged(self):
        files = [{"file_type": "documentation_package"}]
        violations = mmdd.check_file_delivery(files)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["file_type"], "fem_input_file")

    def test_extra_file_types_do_not_cause_violations(self):
        files = [
            {"file_type": "fem_input_file"},
            {"file_type": "documentation_package"},
            {"file_type": "fem_output_file"},
        ]
        self.assertEqual(mmdd.check_file_delivery(files), [])


class AssessDeliveryPackageTest(unittest.TestCase):
    def test_fully_compliant_package_all_empty(self):
        assessment = mmdd.assess_delivery_package(_complete_package())
        self.assertEqual(assessment["completeness"], [])
        self.assertEqual(assessment["metadata"], [])
        self.assertEqual(assessment["consistency"], [])
        self.assertEqual(assessment["file_delivery"], [])

    def test_missing_document_type_appears_in_completeness(self):
        pkg = _complete_package()
        pkg["documents"] = [
            d for d in pkg["documents"]
            if d["document_type"] != "mass_properties_check"
        ]
        assessment = mmdd.assess_delivery_package(pkg)
        missing = {v["document_type"] for v in assessment["completeness"]}
        self.assertIn("mass_properties_check", missing)

    def test_revision_mismatch_appears_in_consistency(self):
        pkg = _complete_package()
        pkg["documents"][0]["model_revision"] = "Z"
        assessment = mmdd.assess_delivery_package(pkg)
        self.assertTrue(assessment["consistency"])

    def test_missing_file_appears_in_file_delivery(self):
        pkg = _complete_package()
        pkg["files"] = [{"file_type": "fem_input_file"}]
        assessment = mmdd.assess_delivery_package(pkg)
        missing = {v["file_type"] for v in assessment["file_delivery"]}
        self.assertIn("documentation_package", missing)

    def test_unrecognized_document_type_raises(self):
        pkg = _complete_package()
        pkg["documents"].append({"document_type": "unobtainium_annex"})
        with self.assertRaises(ValueError):
            mmdd.assess_delivery_package(pkg)


class IsDeliveryCompliantTest(unittest.TestCase):
    def test_all_empty_is_compliant(self):
        assessment = {
            "completeness": [],
            "metadata": [],
            "consistency": [],
            "file_delivery": [],
        }
        self.assertTrue(mmdd.is_delivery_compliant(assessment))

    def test_one_non_empty_category_is_not_compliant(self):
        assessment = {
            "completeness": [{"issue": "missing_required_document_type"}],
            "metadata": [],
            "consistency": [],
            "file_delivery": [],
        }
        self.assertFalse(mmdd.is_delivery_compliant(assessment))

    def test_full_compliant_package_is_compliant(self):
        assessment = mmdd.assess_delivery_package(_complete_package())
        self.assertTrue(mmdd.is_delivery_compliant(assessment))

    def test_package_with_missing_doc_is_not_compliant(self):
        pkg = _complete_package()
        pkg["documents"] = [
            d for d in pkg["documents"]
            if d["document_type"] != "load_case_list"
        ]
        assessment = mmdd.assess_delivery_package(pkg)
        self.assertFalse(mmdd.is_delivery_compliant(assessment))


if __name__ == "__main__":
    unittest.main(verbosity=2)
