"""Gate 3 contract test for e2006-charging-standard-cross-references.

Offline, deterministic, stdlib unittest. Exercises the identifier
parser, the round trip, the issue comparison, the branch and discipline
placement check, the topic registry, the applicable-document audit and
every ValueError path.
"""

import unittest

import e2006_charging_standard_cross_references_logic as logic


CHARGING_TOPICS = [
    "space-plasma-environment-definition",
    "electromagnetic-compatibility-interface",
    "surface-material-and-treatment-selection",
]


class IdentifierParserTests(unittest.TestCase):

    def test_parses_the_charging_standard(self):
        parsed = logic.parse_ecss_identifier("ECSS-E-ST-20-06C")
        self.assertEqual(parsed["branch"], "E")
        self.assertEqual(parsed["kind"], "ST")
        self.assertEqual(parsed["discipline"], "20")
        self.assertEqual(parsed["subdiscipline"], "06")
        self.assertEqual(parsed["issue"], "C")
        self.assertEqual(parsed["revision"], 0)

    def test_names_the_engineering_branch(self):
        parsed = logic.parse_ecss_identifier("ECSS-E-ST-20-06C")
        self.assertEqual(parsed["branch_name"], "engineering")
        self.assertEqual(parsed["discipline_name"],
                         "electrical-and-electromagnetic")

    def test_parses_a_document_without_a_subdiscipline(self):
        parsed = logic.parse_ecss_identifier("ECSS-Q-ST-70C")
        self.assertIsNone(parsed["subdiscipline"])
        self.assertEqual(parsed["branch_name"], "product-assurance")

    def test_parses_a_revision_suffix(self):
        parsed = logic.parse_ecss_identifier("ECSS-E-ST-10C-Rev.1")
        self.assertEqual(parsed["revision"], 1)
        self.assertEqual(parsed["issue"], "C")

    def test_parses_a_handbook_kind(self):
        parsed = logic.parse_ecss_identifier("ECSS-E-HB-20-07A")
        self.assertEqual(parsed["kind_name"], "handbook")

    def test_unmapped_discipline_is_uncategorized(self):
        parsed = logic.parse_ecss_identifier("ECSS-E-ST-99C")
        self.assertEqual(parsed["discipline_name"], "uncategorized-discipline")

    def test_malformed_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.parse_ecss_identifier("ECSS-X-ST-20-06C")

    def test_missing_issue_letter_raises(self):
        with self.assertRaises(ValueError):
            logic.parse_ecss_identifier("ECSS-E-ST-20-06")

    def test_empty_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.parse_ecss_identifier("   ")

    def test_non_string_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.parse_ecss_identifier(2006)


class RoundTripTests(unittest.TestCase):

    def test_round_trip_with_subdiscipline(self):
        text = "ECSS-E-ST-20-06C"
        self.assertEqual(
            logic.format_ecss_identifier(logic.parse_ecss_identifier(text)),
            text)

    def test_round_trip_without_subdiscipline(self):
        text = "ECSS-Q-ST-60C"
        self.assertEqual(
            logic.format_ecss_identifier(logic.parse_ecss_identifier(text)),
            text)

    def test_round_trip_with_revision(self):
        text = "ECSS-E-ST-10C-Rev.1"
        self.assertEqual(
            logic.format_ecss_identifier(logic.parse_ecss_identifier(text)),
            text)

    def test_format_requires_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.format_ecss_identifier("ECSS-E-ST-20-06C")

    def test_format_requires_the_issue_field(self):
        parsed = logic.parse_ecss_identifier("ECSS-E-ST-20-06C")
        del parsed["issue"]
        with self.assertRaises(ValueError):
            logic.format_ecss_identifier(parsed)


class IssueComparisonTests(unittest.TestCase):

    def test_newer_issue_letter_wins(self):
        self.assertEqual(
            logic.compare_issue("ECSS-E-ST-20-07C", "ECSS-E-ST-20-07B"), 1)

    def test_older_issue_letter_loses(self):
        self.assertEqual(
            logic.compare_issue("ECSS-E-ST-20-07A", "ECSS-E-ST-20-07C"), -1)

    def test_identical_issue_and_revision_compare_equal(self):
        self.assertEqual(
            logic.compare_issue("ECSS-Q-ST-70C", "ECSS-Q-ST-70C"), 0)

    def test_revision_breaks_a_tied_issue_letter(self):
        self.assertEqual(
            logic.compare_issue("ECSS-E-ST-10C-Rev.1", "ECSS-E-ST-10C"), 1)

    def test_comparing_two_different_documents_raises(self):
        with self.assertRaises(ValueError):
            logic.compare_issue("ECSS-E-ST-10C", "ECSS-Q-ST-70C")


class PlacementTests(unittest.TestCase):

    def test_charging_standard_is_placed_in_the_electrical_discipline(self):
        result = logic.check_placement(logic.CHARGING_STANDARD)
        self.assertTrue(result["placed"])
        self.assertEqual(result["findings"], [])

    def test_product_assurance_document_is_off_branch(self):
        result = logic.check_placement("ECSS-Q-ST-70C")
        self.assertFalse(result["placed"])
        self.assertEqual(len(result["findings"]), 2)

    def test_engineering_document_in_another_discipline(self):
        result = logic.check_placement("ECSS-E-ST-31C")
        self.assertFalse(result["placed"])
        self.assertEqual(len(result["findings"]), 1)

    def test_placement_accepts_an_explicit_expectation(self):
        result = logic.check_placement("ECSS-Q-ST-70C", branch="Q",
                                       discipline="70")
        self.assertTrue(result["placed"])

    def test_unknown_expected_branch_raises(self):
        with self.assertRaises(ValueError):
            logic.check_placement("ECSS-E-ST-20-06C", branch="X")


class TopicRegistryTests(unittest.TestCase):

    def test_plasma_environment_resolves_to_the_environment_standard(self):
        self.assertEqual(
            logic.resolve_topic("space-plasma-environment-definition"),
            "ECSS-E-ST-10-04C")

    def test_every_registered_topic_resolves_to_a_parsable_identifier(self):
        for topic in logic.TOPIC_REFERENCES:
            parsed = logic.parse_ecss_identifier(logic.resolve_topic(topic))
            self.assertIn(parsed["branch"], logic.BRANCH_NAMES)

    def test_uncategorized_topic_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_topic("orbit-determination")

    def test_non_string_topic_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_topic(None)

    def test_required_reference_set_is_sorted_and_deduplicated(self):
        references = logic.required_reference_set([
            "space-plasma-environment-definition",
            "space-plasma-environment-definition",
            "electromagnetic-compatibility-interface",
        ])
        self.assertEqual(references,
                         ["ECSS-E-ST-10-04C", "ECSS-E-ST-20-07C"])

    def test_empty_topic_list_raises(self):
        with self.assertRaises(ValueError):
            logic.required_reference_set([])


class DeclaredDocumentAuditTests(unittest.TestCase):

    def test_complete_tree_has_no_gaps(self):
        audit = logic.audit_declared_documents(
            CHARGING_TOPICS,
            ["ECSS-E-ST-10-04C", "ECSS-E-ST-20-07C", "ECSS-Q-ST-70C"])
        self.assertEqual(audit["missing"], [])
        self.assertEqual(audit["superseded"], [])
        self.assertEqual(audit["malformed"], [])
        self.assertEqual(audit["duplicates"], [])

    def test_missing_reference_is_reported(self):
        audit = logic.audit_declared_documents(
            CHARGING_TOPICS,
            ["ECSS-E-ST-10-04C", "ECSS-E-ST-20-07C"])
        self.assertEqual(audit["missing"], ["ECSS-Q-ST-70C"])

    def test_older_declared_issue_is_superseded(self):
        audit = logic.audit_declared_documents(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07B"])
        self.assertEqual(len(audit["superseded"]), 1)
        self.assertEqual(audit["superseded"][0]["declared"],
                         "ECSS-E-ST-20-07B")

    def test_newer_declared_issue_is_noted_not_missing(self):
        audit = logic.audit_declared_documents(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07C-Rev.1"])
        self.assertEqual(audit["missing"], [])
        self.assertEqual(len(audit["newer_issue"]), 1)

    def test_repeated_root_counts_as_a_duplicate(self):
        audit = logic.audit_declared_documents(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07C", "ECSS-E-ST-20-07B"])
        self.assertEqual(audit["duplicates"], ["ECSS-E-ST-20-07B"])

    def test_malformed_entry_is_isolated(self):
        audit = logic.audit_declared_documents(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07C", "EMC-spec-rev2"])
        self.assertEqual(audit["malformed"], ["EMC-spec-rev2"])

    def test_extra_entry_is_supplementary(self):
        audit = logic.audit_declared_documents(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07C", "ECSS-E-ST-32C"])
        self.assertEqual(audit["supplementary"], ["ECSS-E-ST-32C"])

    def test_declared_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.audit_declared_documents(CHARGING_TOPICS,
                                           "ECSS-E-ST-10-04C")


class CrossReferenceReportTests(unittest.TestCase):

    def test_clean_tree_is_compliant(self):
        report = logic.build_cross_reference_report(
            CHARGING_TOPICS,
            ["ECSS-E-ST-10-04C", "ECSS-E-ST-20-07C", "ECSS-Q-ST-70C"])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["standard"], "ECSS-E-ST-20-06C")

    def test_gapped_tree_reports_each_defect_once(self):
        report = logic.build_cross_reference_report(
            CHARGING_TOPICS,
            ["ECSS-E-ST-20-07B", "not-a-standard"])
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["findings"]), 4)

    def test_supplementary_entry_is_a_note_not_a_finding(self):
        report = logic.build_cross_reference_report(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07C", "ECSS-E-ST-32C"])
        self.assertTrue(report["compliant"])
        self.assertEqual(len(report["notes"]), 1)

    def test_off_branch_anchor_standard_is_a_finding(self):
        report = logic.build_cross_reference_report(
            ["electromagnetic-compatibility-interface"],
            ["ECSS-E-ST-20-07C"], standard="ECSS-Q-ST-70C")
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["findings"]), 2)

    def test_report_is_deterministic(self):
        first = logic.build_cross_reference_report(
            CHARGING_TOPICS, ["ECSS-E-ST-10-04C", "ECSS-Q-ST-70C"])
        second = logic.build_cross_reference_report(
            CHARGING_TOPICS, ["ECSS-E-ST-10-04C", "ECSS-Q-ST-70C"])
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(first["missing"], second["missing"])


if __name__ == "__main__":
    unittest.main()
