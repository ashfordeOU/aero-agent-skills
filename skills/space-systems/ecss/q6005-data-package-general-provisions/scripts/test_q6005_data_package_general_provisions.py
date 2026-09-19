#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 13.2.1 data-package-provisions leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_data_package_general_provisions.py
"""

import unittest

from q6005_data_package_general_provisions_logic import (
    ACCEPTANCE_PROVISION_INDEX,
    DOCUMENT_CATEGORIES,
    IDENTIFICATION_FIELDS,
    MANDATORY_PROVISIONS,
    MEDIUM_GRADE,
    PROVISION_STATE_CREDIT,
    PROVISION_TOLERANCE,
    PROVISION_WEIGHTS,
    VERDICTS,
    assess_data_package_provisions,
    assess_document,
    assess_provision,
    category_requirements,
    identification_findings,
    medium_grade,
    medium_is_acceptable,
    normalize_provision,
    page_reconciliation,
    provision_compliance_index,
    provision_state_credit,
    provision_weight,
    retention_shortfall_years,
)

SPARE_PROVISION = "delivery-route-and-recipient"


def document(**overrides):
    """A signed conformity original, complete and fully identified."""
    record = {
        "document_id": "DOC-001",
        "category": "certification-and-conformity",
        "medium": "signed-paper-original",
        "retention_years": 20.0,
        "declared_pages": 4,
        "supplied_pages": 4,
        "illegible_pages": 0,
        "carries_lot_reference": True,
        "carries_document_number": True,
        "carries_issue_status": True,
        "carries_page_totals": True,
    }
    record.update(overrides)
    return record


def met_provisions(**states):
    """Every package-level provision met, with named exceptions."""
    provisions = []
    for name in sorted(PROVISION_WEIGHTS):
        entry = {"provision": name, "state": "met"}
        if name in states:
            entry["state"] = states[name]
        provisions.append(entry)
    return provisions


def run(**overrides):
    """Grade one delivery data package against the general provisions."""
    case = {
        "package_id": "HYB-1234-DP-07",
        "documents": [document(), document(document_id="DOC-002", category="acceptance-test-data",
                               medium="signed-scan-pdf", declared_pages=12, supplied_pages=12)],
        "provisions": met_provisions(),
    }
    case.update(overrides)
    return assess_data_package_provisions(**case)


class MediumTests(unittest.TestCase):
    def test_a_signed_original_outranks_a_plain_scan(self):
        self.assertGreater(medium_grade("signed-paper-original"), medium_grade("plain-scan-image"))

    def test_an_editable_file_is_not_a_record(self):
        self.assertEqual(medium_grade("editable-office-file"), 0)

    def test_an_unknown_delivery_medium_is_rejected(self):
        with self.assertRaises(ValueError):
            medium_grade("a-photograph-of-a-screen")

    def test_an_unknown_document_category_is_rejected(self):
        with self.assertRaises(ValueError):
            category_requirements("the-covering-email")

    def test_a_conformity_document_needs_the_top_medium_grade(self):
        self.assertEqual(
            category_requirements("certification-and-conformity")["medium_grade"],
            max(MEDIUM_GRADE.values()),
        )

    def test_a_scan_is_refused_for_a_conformity_document(self):
        self.assertFalse(medium_is_acceptable("plain-scan-image", "certification-and-conformity"))

    def test_a_scan_is_accepted_for_supporting_information(self):
        self.assertTrue(medium_is_acceptable("plain-scan-image", "supporting-information"))

    def test_a_medium_meeting_the_demand_exactly_is_accepted(self):
        self.assertTrue(medium_is_acceptable("signed-scan-pdf", "acceptance-test-data"))


class RetentionTests(unittest.TestCase):
    def test_a_period_matching_the_demand_leaves_no_shortfall(self):
        self.assertAlmostEqual(
            retention_shortfall_years("acceptance-test-data", 20.0), 0.0, places=9
        )

    def test_a_longer_period_leaves_no_shortfall(self):
        self.assertAlmostEqual(
            retention_shortfall_years("supporting-information", 12.0), 0.0, places=9
        )

    def test_a_short_period_reports_the_years_it_is_short_by(self):
        self.assertAlmostEqual(
            retention_shortfall_years("process-and-inspection-records", 6.5), 3.5, places=9
        )

    def test_a_negative_retention_period_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_shortfall_years("supporting-information", -1.0)

    def test_a_retention_period_that_is_not_a_number_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_shortfall_years("supporting-information", "twenty")


class PageReconciliationTests(unittest.TestCase):
    def test_a_matching_page_count_reconciles(self):
        result = page_reconciliation(10, 10, 0)
        self.assertTrue(result["reconciled"])
        self.assertAlmostEqual(result["usable_page_ratio"], 1.0, places=9)

    def test_a_short_delivery_names_the_missing_pages(self):
        result = page_reconciliation(10, 7, 0)
        self.assertEqual(result["missing_pages"], 3)
        self.assertIn("pages-missing-from-the-document", result["findings"])

    def test_more_pages_than_declared_is_also_a_finding(self):
        result = page_reconciliation(10, 12, 0)
        self.assertIn("more-pages-supplied-than-the-document-declares", result["findings"])

    def test_unreadable_pages_cut_the_usable_ratio(self):
        result = page_reconciliation(10, 10, 2)
        self.assertEqual(result["usable_pages"], 8)
        self.assertAlmostEqual(result["usable_page_ratio"], 0.8, places=9)

    def test_a_document_declaring_no_pages_is_rejected(self):
        with self.assertRaises(ValueError):
            page_reconciliation(0, 0, 0)

    def test_more_unreadable_pages_than_supplied_is_rejected(self):
        with self.assertRaises(ValueError):
            page_reconciliation(10, 4, 5)

    def test_a_fractional_page_count_is_rejected(self):
        with self.assertRaises(ValueError):
            page_reconciliation(10, 9.5, 0)


class IdentificationTests(unittest.TestCase):
    def test_a_fully_identified_document_raises_nothing(self):
        self.assertEqual(identification_findings(document()), [])

    def test_every_identification_field_has_a_finding_behind_it(self):
        for field in IDENTIFICATION_FIELDS:
            findings = identification_findings(document(**{field: False}))
            self.assertEqual(len(findings), 1, field)

    def test_a_document_without_an_issue_status_is_reported(self):
        self.assertIn(
            "document-without-an-issue-status",
            identification_findings(document(carries_issue_status=False)),
        )

    def test_an_identification_flag_that_is_not_a_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            identification_findings(document(carries_lot_reference="yes"))


class DocumentTests(unittest.TestCase):
    def test_a_conforming_document_raises_nothing(self):
        record = assess_document(document())
        self.assertTrue(record["conforming"])
        self.assertEqual(record["findings"], [])

    def test_a_conformity_document_on_a_plain_scan_is_reported(self):
        record = assess_document(document(medium="plain-scan-image"))
        self.assertFalse(record["medium_acceptable"])
        self.assertIn("delivery-medium-below-the-grade-the-category-demands", record["findings"])

    def test_a_short_retention_period_is_reported_on_the_document(self):
        record = assess_document(document(retention_years=5.0))
        self.assertAlmostEqual(record["retention_shortfall_years"], 15.0, places=9)
        self.assertIn("retention-period-short-of-the-demand", record["findings"])

    def test_a_blank_document_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_document(document(document_id="  "))

    def test_a_document_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_document(["DOC-001"])


class ProvisionTests(unittest.TestCase):
    def test_every_mandatory_provision_carries_a_published_weight(self):
        for name in MANDATORY_PROVISIONS:
            self.assertIn(name, PROVISION_WEIGHTS)

    def test_an_unknown_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_weight("a-nice-ring-binder")

    def test_an_unknown_provision_state_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_state_credit("broadly-fine")

    def test_a_provision_nobody_mentioned_defaults_to_not_declared(self):
        self.assertEqual(
            normalize_provision({"provision": SPARE_PROVISION})["state"], "not-declared"
        )

    def test_a_met_provision_earns_its_full_weight(self):
        record = assess_provision({"provision": SPARE_PROVISION, "state": "met"})
        self.assertAlmostEqual(
            record["weighted_credit"], PROVISION_WEIGHTS[SPARE_PROVISION], places=9
        )

    def test_a_missing_mandatory_provision_is_marked_missing(self):
        self.assertTrue(assess_provision({"provision": "index-of-contents"})["mandatory_missing"])

    def test_a_fully_declared_package_reaches_a_full_index(self):
        records = [assess_provision(entry) for entry in met_provisions()]
        self.assertAlmostEqual(provision_compliance_index(records), 1.0, places=9)

    def test_an_empty_provision_set_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_compliance_index([])


class WholePackageTests(unittest.TestCase):
    def test_a_sound_package_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "data-package-provisions-met")
        self.assertTrue(result["package_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["provision_compliance_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_package_missing_a_mandatory_provision_is_incomplete(self):
        result = run(provisions=met_provisions(**{"index-of-contents": "not-declared"}))
        self.assertEqual(result["verdict"], "data-package-provisions-assessment-incomplete")

    def test_a_document_on_the_wrong_medium_fails_the_package(self):
        result = run(documents=[document(medium="editable-office-file")])
        self.assertEqual(result["verdict"], "data-package-provisions-not-met")
        self.assertFalse(result["package_accepted"])

    def test_a_short_retention_period_is_carried_up_to_the_package(self):
        result = run(documents=[document(retention_years=8.0)])
        self.assertAlmostEqual(result["worst_retention_shortfall_years"], 12.0, places=9)
        self.assertEqual(result["verdict"], "data-package-provisions-not-met")

    def test_a_missing_page_fails_the_package(self):
        result = run(documents=[document(supplied_pages=3)])
        self.assertIn("pages-missing-from-the-document", [f["finding"] for f in result["findings"]])
        self.assertEqual(result["verdict"], "data-package-provisions-not-met")

    def test_an_observation_on_an_optional_provision_leaves_open_actions(self):
        result = run(provisions=met_provisions(**{SPARE_PROVISION: "met-with-observation"}))
        self.assertEqual(result["verdict"], "data-package-provisions-met-with-open-actions")
        self.assertTrue(result["package_accepted"])

    def test_a_provision_nobody_listed_is_graded_as_not_declared(self):
        result = run(provisions=[{"provision": SPARE_PROVISION, "state": "met"}])
        states = {r["provision"]: r["state"] for r in result["provisions"]}
        self.assertEqual(states["language-declared"], "not-declared")
        self.assertEqual(len(result["provisions"]), len(PROVISION_WEIGHTS))

    def test_a_repeated_document_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(documents=[document(), document()])

    def test_a_repeated_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            run(provisions=met_provisions() + [{"provision": SPARE_PROVISION, "state": "met"}])

    def test_a_package_with_no_documents_is_rejected(self):
        with self.assertRaises(ValueError):
            run(documents=[])

    def test_a_blank_package_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(package_id=" ")


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(PROVISION_TOLERANCE, 1e-6)

    def test_the_provision_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(PROVISION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(PROVISION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_fully_declared_package(self):
        self.assertLess(ACCEPTANCE_PROVISION_INDEX, 1.0)

    def test_every_category_demands_a_grade_some_medium_can_reach(self):
        best = max(MEDIUM_GRADE.values())
        for name in DOCUMENT_CATEGORIES:
            self.assertLessEqual(DOCUMENT_CATEGORIES[name]["medium_grade"], best, name)


if __name__ == "__main__":
    unittest.main()
