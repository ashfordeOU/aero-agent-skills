"""Contract tests for the Annex F justification-document data-item logic."""

import datetime
import unittest

from q6013_justification_document_drd_logic import (
    COVERAGE_TOLERANCE,
    MAX_RISK_ACCEPT_AS_IS,
    OPTIONAL_SECTIONS,
    RECOGNIZED_EVIDENCE,
    RECOGNIZED_SECTIONS,
    REQUIRED_EVIDENCE,
    REQUIRED_SECTIONS,
    RISK_RANK,
    USAGE_DECISIONS,
    absent_sections,
    assess_entry,
    assess_justification_document,
    missing_evidence_types,
    normalize_token,
    reconcile_usage_list,
    section_coverage,
    validate_decision,
    validate_entry,
    validate_evidence_item,
    validate_identity,
    validate_iso_date,
    validate_risk_level,
    validate_section,
)

IDENTITY = {
    "project": "commercial payload demonstrator",
    "document_identifier": "JD-CP-0042",
    "issue": "issue 2",
    "date": "2026-05-14",
}


def _evidence(decision="accept-as-is"):
    return [
        {"evidence_type": t, "reference": "%s ref 1" % t}
        for t in REQUIRED_EVIDENCE[decision]
    ]


def _entry(**overrides):
    entry = {
        "part_number": "CM-7781-B",
        "intended_application": "payload data handling board",
        "decision": "accept-as-is",
        "rationale": "three flight lots with equivalent screening and no alerts",
        "residual_risk": "low",
        "approved_by": "component engineering authority",
        "evidence": _evidence("accept-as-is"),
        "mitigations": [],
    }
    entry.update(overrides)
    return entry


def _document(**overrides):
    document = {
        "identity": dict(IDENTITY),
        "sections": list(REQUIRED_SECTIONS),
        "usage_list": ["CM-7781-B"],
        "entries": [_entry()],
    }
    document.update(overrides)
    return document


class IdentityTests(unittest.TestCase):
    def test_identity_is_returned_stripped(self):
        identity = validate_identity(dict(IDENTITY, project="  demo project "))
        self.assertEqual(identity["project"], "demo project")

    def test_identity_date_becomes_a_calendar_day(self):
        identity = validate_identity(dict(IDENTITY))
        self.assertEqual(identity["date"], datetime.date(2026, 5, 14))

    def test_missing_document_identifier_is_rejected(self):
        bad = dict(IDENTITY)
        del bad["document_identifier"]
        with self.assertRaises(ValueError):
            validate_identity(bad)

    def test_blank_issue_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_identity(dict(IDENTITY, issue="   "))

    def test_non_mapping_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_identity("JD-CP-0042")

    def test_malformed_date_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("14-05-2026", "document date")

    def test_normalize_token_folds_case_and_underscores(self):
        self.assertEqual(normalize_token("Accept_As_Is"), "accept-as-is")


class SectionTests(unittest.TestCase):
    def test_required_sections_are_all_recognized(self):
        for section in REQUIRED_SECTIONS:
            self.assertIn(section, RECOGNIZED_SECTIONS)

    def test_optional_sections_are_not_required(self):
        for section in OPTIONAL_SECTIONS:
            self.assertNotIn(section, REQUIRED_SECTIONS)

    def test_unknown_section_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_section("executive-summary")

    def test_duplicate_section_is_rejected(self):
        doubled = list(REQUIRED_SECTIONS) + ["usage-decision"]
        with self.assertRaises(ValueError):
            absent_sections(doubled)

    def test_absent_sections_are_named_individually(self):
        present = [s for s in REQUIRED_SECTIONS
                   if s not in ("mitigation-actions", "approval-record")]
        absent = absent_sections(present)
        self.assertEqual(absent, ["mitigation-actions", "approval-record"])

    def test_full_section_set_scores_unity_within_tolerance(self):
        self.assertAlmostEqual(section_coverage(list(REQUIRED_SECTIONS)), 1.0, places=9)

    def test_optional_sections_do_not_raise_coverage_above_unity(self):
        present = list(REQUIRED_SECTIONS) + list(OPTIONAL_SECTIONS)
        self.assertAlmostEqual(section_coverage(present), 1.0, places=9)

    def test_partial_section_set_scores_below_unity(self):
        present = list(REQUIRED_SECTIONS)[:-1]
        expected = (len(REQUIRED_SECTIONS) - 1) / float(len(REQUIRED_SECTIONS))
        self.assertAlmostEqual(section_coverage(present), expected, places=9)

    def test_section_collection_type_is_validated(self):
        with self.assertRaises(ValueError):
            absent_sections("usage-decision")

    def test_coverage_tolerance_is_small_and_positive(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class DecisionAndEvidenceTests(unittest.TestCase):
    def test_every_decision_has_an_evidence_demand(self):
        for decision in USAGE_DECISIONS:
            self.assertIn(decision, REQUIRED_EVIDENCE)
            self.assertTrue(REQUIRED_EVIDENCE[decision])

    def test_all_demanded_evidence_is_recognized(self):
        for types in REQUIRED_EVIDENCE.values():
            for evidence_type in types:
                self.assertIn(evidence_type, RECOGNIZED_EVIDENCE)

    def test_unknown_decision_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_decision("accept-under-waiver")

    def test_unknown_risk_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_risk_level("severe")

    def test_risk_levels_are_ordered(self):
        self.assertLess(RISK_RANK["low"], RISK_RANK["medium"])
        self.assertLess(RISK_RANK["medium"], RISK_RANK["high"])

    def test_unknown_evidence_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item(
                {"evidence_type": "verbal-assurance", "reference": "call notes"}
            )

    def test_evidence_item_without_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item({"evidence_type": "derating-analysis"})

    def test_missing_evidence_is_named_per_type(self):
        absent = missing_evidence_types("accept-as-is", ["manufacturer-datasheet"])
        self.assertIn("flight-heritage-record", absent)
        self.assertNotIn("manufacturer-datasheet", absent)

    def test_decisions_demand_different_evidence(self):
        as_is = set(REQUIRED_EVIDENCE["accept-as-is"])
        tested = set(REQUIRED_EVIDENCE["accept-with-additional-testing"])
        self.assertNotEqual(as_is, tested)


class EntryTests(unittest.TestCase):
    def test_valid_entry_is_justified(self):
        assessed = assess_entry(_entry())
        self.assertTrue(assessed["justified"])
        self.assertEqual(assessed["findings"], [])

    def test_entry_missing_a_required_key_is_rejected(self):
        bad = _entry()
        del bad["residual_risk"]
        with self.assertRaises(ValueError):
            validate_entry(bad)

    def test_token_rationale_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(rationale="fine"))

    def test_duplicate_evidence_type_on_one_entry_is_rejected(self):
        doubled = _evidence("accept-as-is") + [
            {"evidence_type": "derating-analysis", "reference": "again"}
        ]
        with self.assertRaises(ValueError):
            validate_entry(_entry(evidence=doubled))

    def test_duplicate_mitigation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(
                _entry(
                    decision="accept-with-mitigation",
                    evidence=_evidence("accept-with-mitigation"),
                    mitigations=["add a series resistor", "add a series resistor"],
                )
            )

    def test_high_risk_on_accept_as_is_is_a_finding(self):
        assessed = assess_entry(_entry(residual_risk="high"))
        self.assertFalse(assessed["justified"])
        self.assertTrue(
            any("accept-as-is" in f for f in assessed["findings"])
        )

    def test_medium_risk_on_accept_as_is_is_allowed(self):
        assessed = assess_entry(_entry(residual_risk=MAX_RISK_ACCEPT_AS_IS))
        self.assertTrue(assessed["justified"])

    def test_mitigation_decision_without_actions_is_a_finding(self):
        assessed = assess_entry(
            _entry(
                decision="accept-with-mitigation",
                evidence=_evidence("accept-with-mitigation"),
                mitigations=[],
            )
        )
        self.assertFalse(assessed["justified"])

    def test_rejection_carrying_mitigations_is_a_finding(self):
        assessed = assess_entry(
            _entry(
                decision="reject",
                evidence=_evidence("reject"),
                mitigations=["screen the next lot"],
            )
        )
        self.assertFalse(assessed["justified"])

    def test_thin_evidence_is_named_type_by_type(self):
        assessed = assess_entry(
            _entry(evidence=[{"evidence_type": "manufacturer-datasheet",
                              "reference": "rev C"}])
        )
        self.assertEqual(len(assessed["missing_evidence"]), 3)
        self.assertEqual(len(assessed["findings"]), 3)

    def test_non_mapping_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(["CM-7781-B"])


class ReconciliationTests(unittest.TestCase):
    def test_matching_lists_reconcile_clean(self):
        result = reconcile_usage_list(["CM-7781-B"], [assess_entry(_entry())])
        self.assertEqual(result["unjustified_parts"], [])
        self.assertEqual(result["unlisted_parts"], [])

    def test_used_part_with_no_entry_is_reported(self):
        result = reconcile_usage_list(
            ["CM-7781-B", "CM-9002-A"], [assess_entry(_entry())]
        )
        self.assertEqual(result["unjustified_parts"], ["CM-9002-A"])

    def test_justified_part_absent_from_the_usage_list_is_reported(self):
        result = reconcile_usage_list(
            ["CM-9002-A"],
            [assess_entry(_entry()), assess_entry(_entry(part_number="CM-9002-A"))],
        )
        self.assertEqual(result["unlisted_parts"], ["CM-7781-B"])

    def test_empty_usage_list_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_usage_list([], [assess_entry(_entry())])

    def test_duplicate_part_on_the_usage_list_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_usage_list(["CM-7781-B", "CM-7781-B"], [])


class DocumentTests(unittest.TestCase):
    def test_complete_document_is_fit_to_issue(self):
        result = assess_justification_document(_document())
        self.assertTrue(result["fit_to_issue"])
        self.assertTrue(result["sections_complete"])
        self.assertAlmostEqual(result["section_coverage"], 1.0, places=9)

    def test_absent_section_reaches_the_verdict(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "approval-record"]
        result = assess_justification_document(_document(sections=sections))
        self.assertFalse(result["fit_to_issue"])
        self.assertIn("approval-record", result["absent_sections"])
        self.assertFalse(result["sections_complete"])

    def test_part_justified_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_justification_document(_document(entries=[_entry(), _entry()]))

    def test_empty_entry_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_justification_document(_document(entries=[]))

    def test_document_missing_a_required_key_is_rejected(self):
        bad = _document()
        del bad["usage_list"]
        with self.assertRaises(ValueError):
            assess_justification_document(bad)

    def test_non_mapping_document_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_justification_document(["identity"])

    def test_unjustified_used_part_reaches_the_verdict(self):
        result = assess_justification_document(
            _document(usage_list=["CM-7781-B", "CM-9002-A"])
        )
        self.assertFalse(result["fit_to_issue"])

    def test_every_finding_is_named_not_only_the_first(self):
        sections = [s for s in REQUIRED_SECTIONS
                    if s not in ("mitigation-actions", "open-actions")]
        thin = _entry(
            residual_risk="high",
            evidence=[{"evidence_type": "manufacturer-datasheet",
                       "reference": "rev C"}],
        )
        result = assess_justification_document(
            _document(
                sections=sections,
                entries=[thin],
                usage_list=["CM-7781-B", "CM-9002-A"],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 6)

    def test_entry_order_is_preserved_in_the_report(self):
        result = assess_justification_document(
            _document(
                usage_list=["CM-7781-B", "CM-9002-A"],
                entries=[_entry(), _entry(part_number="CM-9002-A")],
            )
        )
        self.assertEqual(
            [e["part_number"] for e in result["entries"]],
            ["CM-7781-B", "CM-9002-A"],
        )


if __name__ == "__main__":
    unittest.main()
