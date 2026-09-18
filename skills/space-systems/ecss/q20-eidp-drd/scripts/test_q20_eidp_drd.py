"""Contract tests for the Annex B end item data package DRD logic."""

import unittest

from q20_eidp_drd_logic import (
    CATEGORY_DOCUMENTS,
    DOCUMENT_CATEGORY,
    DRD_CATEGORIES,
    assess_eidp_drd,
    category_findings,
    category_of,
    drd_table_of_contents,
    group_submission,
    misfiled_findings,
    normalise_identifier,
    package_completeness,
    validate_documents,
)


def full_submission(**changes):
    """Return a package carrying every document the DRD asks for."""
    items = []
    for category in DRD_CATEGORIES:
        for document in CATEGORY_DOCUMENTS[category]:
            items.append(
                {
                    "document": document,
                    "identifier": "doc-%s" % document[:6],
                    "issue": 1,
                    "category": category,
                }
            )
    for key, replacement in changes.items():
        name = key.replace("_", "-")
        items = [item for item in items if item["document"] != name]
        if replacement is not None:
            items.append(replacement)
    return items


class VocabularyTests(unittest.TestCase):
    def test_four_categories_in_drd_order(self):
        self.assertEqual(DRD_CATEGORIES, ("design", "manufacturing", "test", "acceptance"))

    def test_every_category_owns_documents(self):
        self.assertEqual(set(CATEGORY_DOCUMENTS), set(DRD_CATEGORIES))

    def test_reverse_lookup_covers_every_document(self):
        total = sum(len(CATEGORY_DOCUMENTS[c]) for c in DRD_CATEGORIES)
        self.assertEqual(len(DOCUMENT_CATEGORY), total)

    def test_as_built_list_is_manufacturing_data(self):
        self.assertEqual(category_of("as-built-configuration-list"), "manufacturing")

    def test_as_designed_list_is_design_data(self):
        self.assertEqual(category_of("as-designed-configuration-list"), "design")

    def test_certificate_is_acceptance_data(self):
        self.assertEqual(category_of("certificate-of-conformity"), "acceptance")

    def test_unrecognised_document_has_no_category(self):
        self.assertIsNone(category_of("packing-crate-photo"))

    def test_identifier_normalises_underscores(self):
        self.assertEqual(normalise_identifier(" Test_Data_Log ", "d"), "test-data-log")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("   ", "d")


class TableOfContentsTests(unittest.TestCase):
    def test_contents_follow_the_category_order(self):
        contents = drd_table_of_contents()
        self.assertEqual(tuple(item["category"] for item in contents), DRD_CATEGORIES)

    def test_categories_numbered_from_one(self):
        contents = drd_table_of_contents()
        self.assertEqual(contents[0]["number"], "1")
        self.assertEqual(contents[-1]["number"], str(len(DRD_CATEGORIES)))

    def test_documents_numbered_inside_their_category(self):
        contents = drd_table_of_contents()
        self.assertEqual(contents[1]["documents"][0]["number"], "2.1")

    def test_contents_carry_every_document(self):
        contents = drd_table_of_contents()
        listed = [e["document"] for item in contents for e in item["documents"]]
        self.assertEqual(len(listed), len(DOCUMENT_CATEGORY))


class ValidationTests(unittest.TestCase):
    def test_clean_submission_validates(self):
        entries = validate_documents(full_submission())
        self.assertEqual(len(entries), len(DOCUMENT_CATEGORY))

    def test_empty_submission_rejected(self):
        with self.assertRaises(ValueError):
            validate_documents([])

    def test_duplicate_document_rejected(self):
        items = full_submission()
        items.append({"document": "delivery-note", "identifier": "dn-1", "issue": 1})
        with self.assertRaises(ValueError):
            validate_documents(items)

    def test_missing_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_documents([{"document": "delivery-note", "identifier": "dn-1"}])

    def test_zero_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_documents(
                [{"document": "delivery-note", "identifier": "dn-1", "issue": 0}]
            )

    def test_boolean_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_documents(
                [{"document": "delivery-note", "identifier": "dn-1", "issue": True}]
            )

    def test_missing_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_documents([{"document": "delivery-note", "issue": 1}])


class GroupingTests(unittest.TestCase):
    def test_full_package_groups_into_four_categories(self):
        grouped = group_submission(validate_documents(full_submission()))
        for category in DRD_CATEGORIES:
            self.assertEqual(len(grouped[category]), len(CATEGORY_DOCUMENTS[category]))

    def test_unrecognised_document_lands_in_unassigned(self):
        items = full_submission()
        items.append({"document": "packing-crate-photo", "identifier": "ph-1", "issue": 1})
        grouped = group_submission(validate_documents(items))
        self.assertEqual(grouped["unassigned"], ["packing-crate-photo"])

    def test_grouping_rejects_a_raw_list(self):
        with self.assertRaises(ValueError):
            group_submission(["delivery-note"])


class MisfilingTests(unittest.TestCase):
    def test_correctly_filed_package_is_clean(self):
        self.assertEqual(misfiled_findings(validate_documents(full_submission())), [])

    def test_document_under_the_wrong_category_is_a_finding(self):
        items = full_submission(
            as_built_configuration_list={
                "document": "as-built-configuration-list",
                "identifier": "abcl-1",
                "issue": 2,
                "category": "design",
            }
        )
        findings = misfiled_findings(validate_documents(items))
        self.assertIn("belongs to the manufacturing data", findings[0])

    def test_unknown_declared_category_is_a_finding(self):
        items = full_submission()
        items.append(
            {
                "document": "packing-crate-photo",
                "identifier": "ph-1",
                "issue": 1,
                "category": "shipping",
            }
        )
        findings = misfiled_findings(validate_documents(items))
        self.assertIn("not a package category", findings[0])

    def test_undeclared_category_is_not_a_finding(self):
        items = full_submission()
        for item in items:
            item.pop("category", None)
        self.assertEqual(misfiled_findings(validate_documents(items)), [])


class CategoryCompletenessTests(unittest.TestCase):
    def test_full_package_has_no_gap(self):
        result = category_findings(validate_documents(full_submission()))
        self.assertEqual(result["findings"], [])

    def test_absent_document_is_named_in_its_category(self):
        result = category_findings(validate_documents(full_submission(test_data_log=None)))
        self.assertEqual(result["categories"]["test"]["missing"], ["test-data-log"])
        self.assertIn("test data is short of", result["findings"][0])

    def test_category_fraction_reflects_the_gap(self):
        result = category_findings(validate_documents(full_submission(test_data_log=None)))
        owed = len(CATEGORY_DOCUMENTS["test"])
        self.assertAlmostEqual(
            result["categories"]["test"]["fraction"], (owed - 1) / float(owed), places=9
        )

    def test_untouched_category_stays_whole(self):
        result = category_findings(validate_documents(full_submission(test_data_log=None)))
        self.assertAlmostEqual(result["categories"]["design"]["fraction"], 1.0, places=9)

    def test_extra_document_does_not_reduce_completeness(self):
        items = full_submission()
        items.append({"document": "packing-crate-photo", "identifier": "ph-1", "issue": 1})
        result = category_findings(validate_documents(items))
        self.assertAlmostEqual(package_completeness(result), 1.0, places=9)
        self.assertEqual(result["extras"], ["packing-crate-photo"])


class CompletenessTests(unittest.TestCase):
    def test_full_package_is_one(self):
        result = category_findings(validate_documents(full_submission()))
        self.assertAlmostEqual(package_completeness(result), 1.0, places=9)

    def test_one_absent_document_lowers_the_fraction(self):
        result = category_findings(validate_documents(full_submission(delivery_note=None)))
        total = len(DOCUMENT_CATEGORY)
        self.assertAlmostEqual(
            package_completeness(result), (total - 1) / float(total), places=9
        )

    def test_zero_required_count_rejected(self):
        with self.assertRaises(ValueError):
            package_completeness({"required_count": 0, "present_count": 0})

    def test_malformed_result_rejected(self):
        with self.assertRaises(ValueError):
            package_completeness({"present_count": 4})


class AssessmentTests(unittest.TestCase):
    def test_full_package_is_conformant(self):
        result = assess_eidp_drd(full_submission())
        self.assertEqual(result["verdict"], "package-drd-conformant")
        self.assertAlmostEqual(result["completeness_fraction"], 1.0, places=9)

    def test_absent_document_makes_it_nonconformant(self):
        result = assess_eidp_drd(full_submission(drawing_and_part_list=None))
        self.assertEqual(result["verdict"], "package-drd-nonconformant")
        self.assertEqual(result["categories"]["design"]["missing"], ["drawing-and-part-list"])

    def test_misfiled_document_makes_it_nonconformant(self):
        items = full_submission(
            calibration_certificate_set={
                "document": "calibration-certificate-set",
                "identifier": "cal-1",
                "issue": 3,
                "category": "acceptance",
            }
        )
        result = assess_eidp_drd(items)
        self.assertEqual(result["verdict"], "package-drd-nonconformant")

    def test_grouping_is_reported_for_evidence(self):
        result = assess_eidp_drd(full_submission())
        self.assertIn("manufacturing", result["grouped"])
        self.assertEqual(result["grouped"]["unassigned"], [])

    def test_counts_are_reported_for_evidence(self):
        result = assess_eidp_drd(full_submission())
        self.assertEqual(result["required_count"], len(DOCUMENT_CATEGORY))
        self.assertEqual(result["present_count"], result["required_count"])

    def test_empty_package_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_eidp_drd([])


if __name__ == "__main__":
    unittest.main()
