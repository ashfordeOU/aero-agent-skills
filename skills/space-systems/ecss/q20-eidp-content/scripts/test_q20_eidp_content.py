"""Contract tests for the clause 5.7.2 end item data package logic."""

import unittest

from q20_eidp_content_logic import (
    COMMON_DOCUMENTS,
    CORE_DOCUMENTS,
    PRODUCT_TYPES,
    TYPE_DOCUMENTS,
    assemble_eidp,
    completeness_fraction,
    conformity_reference_findings,
    document_findings,
    normalise_identifier,
    required_documents,
    validate_submission,
)

AS_BUILT_REVISION = "c"


def full_submission(product_type="equipment", **changes):
    """Return an approved submission covering everything the type owes."""
    items = []
    for doc in required_documents(product_type):
        entry = {"document": doc, "revision": "a", "approved": True}
        if doc == "certificate-of-conformity":
            entry["references"] = {"as-built-configuration-list": AS_BUILT_REVISION}
        if doc == "as-built-configuration-list":
            entry["revision"] = AS_BUILT_REVISION
        items.append(entry)
    for doc, replacement in changes.items():
        name = doc.replace("_", "-")
        items = [item for item in items if item["document"] != name]
        if replacement is not None:
            items.append(replacement)
    return items


class VocabularyTests(unittest.TestCase):
    def test_product_types(self):
        self.assertEqual(len(PRODUCT_TYPES), 5)
        self.assertIn("software", PRODUCT_TYPES)

    def test_common_documents_are_shared(self):
        for product_type in PRODUCT_TYPES:
            for doc in COMMON_DOCUMENTS:
                self.assertIn(doc, required_documents(product_type))

    def test_core_documents_sit_inside_the_common_set(self):
        self.assertTrue(set(CORE_DOCUMENTS).issubset(set(COMMON_DOCUMENTS)))

    def test_each_type_adds_its_own_records(self):
        self.assertEqual(set(TYPE_DOCUMENTS), set(PRODUCT_TYPES))

    def test_software_owes_its_version_description(self):
        self.assertIn("software-version-description", required_documents("software"))

    def test_software_does_not_owe_mass_properties(self):
        self.assertNotIn("mass-properties-record", required_documents("software"))

    def test_equipment_owes_mass_properties(self):
        self.assertIn("mass-properties-record", required_documents("equipment"))

    def test_unknown_product_type_rejected(self):
        with self.assertRaises(ValueError):
            required_documents("launcher")

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" EIDP-Index ", "doc"), "eidp-index")


class SubmissionValidationTests(unittest.TestCase):
    def test_clean_submission_validates(self):
        entries = validate_submission(full_submission())
        self.assertEqual(len(entries), len(required_documents("equipment")))

    def test_empty_submission_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission([])

    def test_duplicate_document_rejected(self):
        items = full_submission()
        items.append({"document": "eidp-index", "revision": "a", "approved": True})
        with self.assertRaises(ValueError):
            validate_submission(items)

    def test_missing_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission([{"document": "eidp-index", "approved": True}])

    def test_blank_justification_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(
                [{"document": "mass-properties-record", "not_applicable": True, "justification": "  "}]
            )

    def test_non_mapping_references_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(
                [{"document": "eidp-index", "revision": "a", "approved": True, "references": ["x"]}]
            )


class DocumentGradingTests(unittest.TestCase):
    def test_full_package_has_no_finding(self):
        result = document_findings("equipment", validate_submission(full_submission()))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing"], [])

    def test_missing_record_is_reported(self):
        items = full_submission(open_work_list=None)
        result = document_findings("equipment", validate_submission(items))
        self.assertEqual(result["missing"], ["open-work-list"])
        self.assertIn("does not carry", result["findings"][0])

    def test_unapproved_record_is_reported(self):
        items = full_submission(
            open_work_list={"document": "open-work-list", "revision": "a", "approved": False}
        )
        result = document_findings("equipment", validate_submission(items))
        self.assertEqual(result["unapproved"], ["open-work-list"])

    def test_accepted_not_applicable_counts_as_satisfied(self):
        items = full_submission(
            limited_life_item_list={
                "document": "limited-life-item-list",
                "not_applicable": True,
                "justification": "no limited life items in the build standard",
                "approved_by": "product-assurance",
            }
        )
        result = document_findings("equipment", validate_submission(items))
        self.assertEqual(result["accepted_not_applicable"], ["limited-life-item-list"])
        self.assertEqual(result["findings"], [])

    def test_not_applicable_on_a_core_record_is_refused(self):
        items = full_submission(
            certificate_of_conformity={
                "document": "certificate-of-conformity",
                "not_applicable": True,
                "justification": "covered by the delivery note",
                "approved_by": "product-assurance",
            }
        )
        result = document_findings("equipment", validate_submission(items))
        self.assertIn("core record", result["findings"][0])

    def test_not_applicable_without_justification_is_refused(self):
        items = full_submission(
            mass_properties_record={
                "document": "mass-properties-record",
                "not_applicable": True,
                "approved_by": "product-assurance",
            }
        )
        result = document_findings("equipment", validate_submission(items))
        self.assertIn("no justification", result["findings"][0])

    def test_not_applicable_without_approver_is_refused(self):
        items = full_submission(
            mass_properties_record={
                "document": "mass-properties-record",
                "not_applicable": True,
                "justification": "mass recorded in the subsystem package",
            }
        )
        result = document_findings("equipment", validate_submission(items))
        self.assertIn("no approver", result["findings"][0])

    def test_undemanded_record_is_listed_as_an_extra(self):
        items = full_submission()
        items.append({"document": "packing-list", "revision": "a", "approved": True})
        result = document_findings("equipment", validate_submission(items))
        self.assertEqual(result["extras"], ["packing-list"])
        self.assertEqual(result["findings"], [])

    def test_grading_a_package_against_the_wrong_type_shows_the_gap(self):
        result = document_findings("software", validate_submission(full_submission("equipment")))
        self.assertIn("software-version-description", result["missing"])


class CompletenessTests(unittest.TestCase):
    def test_full_package_is_one(self):
        result = document_findings("equipment", validate_submission(full_submission()))
        self.assertAlmostEqual(completeness_fraction(result), 1.0, places=9)

    def test_one_missing_record_lowers_the_fraction(self):
        items = full_submission(open_work_list=None)
        result = document_findings("equipment", validate_submission(items))
        total = len(required_documents("equipment"))
        self.assertAlmostEqual(
            completeness_fraction(result), (total - 1) / float(total), places=9
        )

    def test_malformed_result_rejected(self):
        with self.assertRaises(ValueError):
            completeness_fraction({"required_count": 4})

    def test_zero_required_count_rejected(self):
        with self.assertRaises(ValueError):
            completeness_fraction({"required_count": 0, "satisfied_count": 0})


class ConformityReferenceTests(unittest.TestCase):
    def test_matching_reference_is_clean(self):
        entries = validate_submission(full_submission())
        self.assertEqual(conformity_reference_findings(entries), [])

    def test_absent_reference_is_a_finding(self):
        items = full_submission(
            certificate_of_conformity={
                "document": "certificate-of-conformity",
                "revision": "a",
                "approved": True,
            }
        )
        findings = conformity_reference_findings(validate_submission(items))
        self.assertIn("cites no as-built", findings[0])

    def test_stale_reference_is_a_finding(self):
        items = full_submission(
            certificate_of_conformity={
                "document": "certificate-of-conformity",
                "revision": "a",
                "approved": True,
                "references": {"as-built-configuration-list": "b"},
            }
        )
        findings = conformity_reference_findings(validate_submission(items))
        self.assertIn("while the package carries c", findings[0])

    def test_absent_as_built_list_gives_no_reference_finding(self):
        items = full_submission(as_built_configuration_list=None)
        self.assertEqual(conformity_reference_findings(validate_submission(items)), [])


class AssemblyTests(unittest.TestCase):
    def test_full_equipment_package_is_complete(self):
        result = assemble_eidp("equipment", full_submission())
        self.assertEqual(result["verdict"], "package-complete")
        self.assertAlmostEqual(result["completeness_fraction"], 1.0, places=9)

    def test_full_software_package_is_complete(self):
        result = assemble_eidp("software", full_submission("software"))
        self.assertEqual(result["verdict"], "package-complete")

    def test_missing_record_makes_the_package_incomplete(self):
        result = assemble_eidp("equipment", full_submission(nonconformance_summary=None))
        self.assertEqual(result["verdict"], "package-incomplete")
        self.assertEqual(result["missing"], ["nonconformance-summary"])

    def test_stale_certificate_reference_makes_the_package_incomplete(self):
        items = full_submission(
            certificate_of_conformity={
                "document": "certificate-of-conformity",
                "revision": "a",
                "approved": True,
                "references": {"as-built-configuration-list": "b"},
            }
        )
        result = assemble_eidp("equipment", items)
        self.assertEqual(result["verdict"], "package-incomplete")

    def test_counts_are_reported_for_evidence(self):
        result = assemble_eidp("system", full_submission("system"))
        self.assertEqual(result["required_count"], len(required_documents("system")))
        self.assertEqual(result["satisfied_count"], result["required_count"])

    def test_unknown_type_rejected_by_the_assembly(self):
        with self.assertRaises(ValueError):
            assemble_eidp("launcher", full_submission())


if __name__ == "__main__":
    unittest.main()
