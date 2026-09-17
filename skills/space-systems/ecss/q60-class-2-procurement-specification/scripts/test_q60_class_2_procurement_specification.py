"""Contract tests for the clause 5.3.2 Class 2 purchasing specification logic.

The cases walk the document control chain one step at a time: the revision
ordering and its two incomparable schemes, the mandatory-content score, the
release state and release date of the document the order was raised against,
the revision the order cites against the revision released, one controlled
document per part type, and the two-way reconciliation of ordered part types
against the specification library. Each limit is exercised on both sides, and
a completeness score landing on its threshold is compared with a
representation-sized tolerance.
"""

import datetime
import unittest

from q60_class_2_procurement_specification_logic import (
    BUYABLE_STATUS,
    COMPLETENESS_TOLERANCE,
    REQUIRED_SPECIFICATION_CONTENT,
    SPECIFICATION_STATUSES,
    assess_purchasing_specifications,
    assess_specified_line,
    compare_revisions,
    content_completeness,
    index_specifications,
    normalize_token,
    parse_iso_date,
    revision_findings,
    revision_key,
    status_findings,
)

ORDER_DATE = "2026-05-06"


def _specification(**overrides):
    specification = {
        "part_type": "thick-film-chip-resistor-rcr-series",
        "reference": "PPS-RCR-0042",
        "revision": "C",
        "status": "released",
        "release_date": "2025-11-04",
        "content": list(REQUIRED_SPECIFICATION_CONTENT),
    }
    specification.update(overrides)
    return specification


def _line(**overrides):
    line = {
        "part_type": "thick-film-chip-resistor-rcr-series",
        "cited_revision": "C",
    }
    line.update(overrides)
    return line


def _order(**overrides):
    order = {
        "order_reference": "PO-2026-512",
        "order_date": ORDER_DATE,
        "minimum_completeness": 1.0,
        "specifications": [_specification()],
        "lines": [_line()],
    }
    order.update(overrides)
    return order


def _index(**overrides):
    return index_specifications([_specification(**overrides)], ORDER_DATE)


class TokenAndDateTests(unittest.TestCase):
    def test_token_normalised(self):
        self.assertEqual(normalize_token("Lot_Acceptance And Marking", "item"), "lot-acceptance-and-marking")

    def test_blank_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token("  ", "item")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date(ORDER_DATE, "date"), datetime.date(2026, 5, 6))

    def test_non_calendar_date_refused(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-02-30", "date")


class RevisionTests(unittest.TestCase):
    def test_alphabetic_revision_ranks_in_order(self):
        self.assertLess(revision_key("B")[1], revision_key("C")[1])

    def test_two_letter_revision_outranks_one_letter(self):
        self.assertLess(revision_key("Z")[1], revision_key("AA")[1])

    def test_numeric_revision_ranks_numerically(self):
        self.assertLess(revision_key("9")[1], revision_key("10")[1])

    def test_lower_case_revision_accepted(self):
        self.assertEqual(revision_key("c"), revision_key("C"))

    def test_equal_revisions_compare_equal(self):
        self.assertEqual(compare_revisions("C", "C"), 0)

    def test_earlier_revision_compares_below(self):
        self.assertEqual(compare_revisions("B", "C"), -1)

    def test_later_revision_compares_above(self):
        self.assertEqual(compare_revisions("D", "C"), 1)

    def test_mixed_revision_schemes_refused(self):
        with self.assertRaises(ValueError):
            compare_revisions("3", "C")

    def test_unparseable_revision_refused(self):
        with self.assertRaises(ValueError):
            revision_key("C-draft-2")


class ContentTests(unittest.TestCase):
    def test_full_content_scores_one(self):
        score = content_completeness(REQUIRED_SPECIFICATION_CONTENT)
        self.assertAlmostEqual(score["score"], 1.0, places=9)
        self.assertEqual(score["missing"], [])

    def test_missing_item_is_named(self):
        content = [i for i in REQUIRED_SPECIFICATION_CONTENT if i != "screening-requirements"]
        score = content_completeness(content)
        self.assertEqual(score["missing"], ["screening-requirements"])

    def test_score_is_the_present_fraction(self):
        content = list(REQUIRED_SPECIFICATION_CONTENT)[:-1]
        score = content_completeness(content)
        expected = (len(REQUIRED_SPECIFICATION_CONTENT) - 1) / float(
            len(REQUIRED_SPECIFICATION_CONTENT)
        )
        self.assertAlmostEqual(score["score"], expected, places=9)

    def test_extra_content_does_not_raise_the_score_above_one(self):
        score = content_completeness(list(REQUIRED_SPECIFICATION_CONTENT) + ["obsolescence-plan"])
        self.assertAlmostEqual(score["score"], 1.0, places=9)

    def test_empty_content_scores_zero(self):
        score = content_completeness([])
        self.assertAlmostEqual(score["score"], 0.0, places=9)

    def test_non_collection_content_refused(self):
        with self.assertRaises(ValueError):
            content_completeness("screening-requirements")

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)


class StatusTests(unittest.TestCase):
    def test_released_document_raises_nothing(self):
        self.assertEqual(status_findings(_specification(), ORDER_DATE), [])

    def test_buyable_status_is_one_of_the_known_states(self):
        self.assertIn(BUYABLE_STATUS, SPECIFICATION_STATUSES)

    def test_draft_document_reported(self):
        findings = status_findings(_specification(status="draft"), ORDER_DATE)
        self.assertTrue(any("uncontrolled issue" in f for f in findings))

    def test_superseded_document_reported(self):
        findings = status_findings(_specification(status="superseded"), ORDER_DATE)
        self.assertTrue(findings)

    def test_document_released_after_the_order_reported(self):
        findings = status_findings(_specification(release_date="2026-07-01"), ORDER_DATE)
        self.assertTrue(any("after the order date" in f for f in findings))

    def test_document_released_on_the_order_date_accepted(self):
        self.assertEqual(status_findings(_specification(release_date=ORDER_DATE), ORDER_DATE), [])

    def test_unknown_status_refused(self):
        with self.assertRaises(ValueError):
            status_findings(_specification(status="pending-signature"), ORDER_DATE)

    def test_missing_status_key_refused(self):
        specification = _specification()
        del specification["status"]
        with self.assertRaises(ValueError):
            status_findings(specification, ORDER_DATE)


class CitedRevisionTests(unittest.TestCase):
    def test_matching_revision_raises_nothing(self):
        self.assertEqual(revision_findings("C", _specification()), [])

    def test_superseded_revision_cited_reported(self):
        findings = revision_findings("B", _specification())
        self.assertTrue(any("where revision 'C' is released" in f for f in findings))

    def test_unreleased_revision_cited_reported(self):
        findings = revision_findings("D", _specification())
        self.assertTrue(any("ahead of the released" in f for f in findings))

    def test_no_revision_cited_reported(self):
        findings = revision_findings(None, _specification())
        self.assertTrue(any("no revision" in f for f in findings))


class LibraryTests(unittest.TestCase):
    def test_library_indexed_by_part_type(self):
        index = _index()
        self.assertIn("thick-film-chip-resistor-rcr-series", index)

    def test_two_documents_for_one_part_type_refused(self):
        with self.assertRaises(ValueError):
            index_specifications([_specification(), _specification(reference="PPS-RCR-0043")], ORDER_DATE)

    def test_missing_specification_key_refused(self):
        specification = _specification()
        del specification["content"]
        with self.assertRaises(ValueError):
            index_specifications([specification], ORDER_DATE)

    def test_empty_library_refused(self):
        with self.assertRaises(ValueError):
            index_specifications([], ORDER_DATE)

    def test_unparseable_revision_in_the_library_refused(self):
        with self.assertRaises(ValueError):
            index_specifications([_specification(revision="issue 2 rev C")], ORDER_DATE)


class LineTests(unittest.TestCase):
    def test_clean_line_is_acceptable(self):
        record = assess_specified_line(_line(), _index(), 1.0)
        self.assertTrue(record["acceptable"])
        self.assertAlmostEqual(record["completeness_score"], 1.0, places=9)

    def test_line_without_a_specification_reported(self):
        record = assess_specified_line(_line(part_type="tantalum-capacitor"), _index(), 1.0)
        self.assertFalse(record["specified"])
        self.assertTrue(any("no controlled purchasing specification" in f for f in record["findings"]))

    def test_incomplete_specification_reported(self):
        content = [i for i in REQUIRED_SPECIFICATION_CONTENT if i != "screening-requirements"]
        record = assess_specified_line(_line(), _index(content=content), 1.0)
        self.assertTrue(any("mandatory content items" in f for f in record["findings"]))

    def test_score_landing_on_the_threshold_is_accepted(self):
        content = list(REQUIRED_SPECIFICATION_CONTENT)[:-1]
        threshold = (len(REQUIRED_SPECIFICATION_CONTENT) - 1) / float(
            len(REQUIRED_SPECIFICATION_CONTENT)
        )
        record = assess_specified_line(_line(), _index(content=content), threshold)
        self.assertEqual(record["findings"], [])

    def test_threshold_outside_the_unit_range_refused(self):
        with self.assertRaises(ValueError):
            assess_specified_line(_line(), _index(), 1.4)

    def test_missing_line_key_refused(self):
        with self.assertRaises(ValueError):
            assess_specified_line({"cited_revision": "C"}, _index(), 1.0)

    def test_non_mapping_line_refused(self):
        with self.assertRaises(ValueError):
            assess_specified_line(["rcr"], _index(), 1.0)


class OrderTests(unittest.TestCase):
    def test_clean_order_is_controlled(self):
        verdict = assess_purchasing_specifications(_order())
        self.assertTrue(verdict["specifications_controlled"])
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["specified_fraction"], 1.0, places=9)

    def test_specified_fraction_counts_only_clean_lines(self):
        order = _order(
            specifications=[_specification(), _specification(part_type="tantalum-capacitor-cwr-series", reference="PPS-CWR-0007")],
            lines=[_line(), _line(part_type="tantalum-capacitor-cwr-series", cited_revision="A")],
        )
        verdict = assess_purchasing_specifications(order)
        self.assertAlmostEqual(verdict["specified_fraction"], 0.5, places=9)

    def test_specification_cited_by_no_line_reported(self):
        order = _order(
            specifications=[_specification(), _specification(part_type="tantalum-capacitor-cwr-series", reference="PPS-CWR-0007")]
        )
        verdict = assess_purchasing_specifications(order)
        self.assertEqual(verdict["uncited_specifications"], ["tantalum-capacitor-cwr-series"])

    def test_part_type_on_two_lines_refused(self):
        with self.assertRaises(ValueError):
            assess_purchasing_specifications(_order(lines=[_line(), _line()]))

    def test_every_finding_is_carried_not_only_the_first(self):
        content = [i for i in REQUIRED_SPECIFICATION_CONTENT if i != "packaging-and-handling"]
        order = _order(
            specifications=[_specification(status="draft", content=content)],
            lines=[_line(cited_revision="B")],
        )
        verdict = assess_purchasing_specifications(order)
        self.assertGreaterEqual(len(verdict["findings"]), 3)

    def test_empty_line_list_refused(self):
        with self.assertRaises(ValueError):
            assess_purchasing_specifications(_order(lines=[]))

    def test_missing_order_key_refused(self):
        order = _order()
        del order["minimum_completeness"]
        with self.assertRaises(ValueError):
            assess_purchasing_specifications(order)

    def test_non_mapping_order_refused(self):
        with self.assertRaises(ValueError):
            assess_purchasing_specifications("PO-2026-512")

    def test_order_reference_and_date_echoed(self):
        verdict = assess_purchasing_specifications(_order())
        self.assertEqual(verdict["order_reference"], "PO-2026-512")
        self.assertEqual(verdict["order_date"], ORDER_DATE)


if __name__ == "__main__":
    unittest.main()
