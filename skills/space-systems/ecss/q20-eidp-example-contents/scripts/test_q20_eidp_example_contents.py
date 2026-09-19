"""Contract tests for the data package contents-list checklist logic."""

import unittest

from q20_eidp_example_contents_logic import (
    FIRST_PAGE,
    MANDATORY_SECTIONS,
    SECTION_ORDER,
    SECTION_SLOTS,
    assess_contents_list,
    completion_fraction,
    mandatory_section_findings,
    normalise_identifier,
    order_findings,
    page_range_findings,
    placement_findings,
    render_contents,
    section_for_document,
    section_index,
    validate_contents,
    validate_line,
)


def _line(document, section, pages=4, ticked=True, **extra):
    line = {"document": document, "section": section, "ticked": ticked}
    if ticked:
        line["document_number"] = "doc-" + document[:6]
        line["issue"] = "1"
        line["pages"] = pages
    line.update(extra)
    return line


def _package():
    return [
        _line("eidp-contents-list", "cover-and-contents", pages=2),
        _line("certificate-of-conformity", "conformity-declarations", pages=1),
        _line("as-built-configuration-list", "configuration-records", pages=6),
        _line("acceptance-test-report", "acceptance-test-documentation", pages=20),
    ]


class NormaliseIdentifierTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(
            normalise_identifier(" Item-Logbook ", "document"), "item-logbook"
        )

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("  ", "document")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(3, "document")


class SectionTests(unittest.TestCase):
    def test_index_follows_the_fixed_order(self):
        self.assertEqual(section_index("cover-and-contents"), 0)

    def test_later_section_has_a_higher_index(self):
        self.assertGreater(
            section_index("open-work-and-constraints"),
            section_index("configuration-records"),
        )

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            section_index("appendix-of-hope")

    def test_every_slot_points_at_a_real_section(self):
        for document, section in SECTION_SLOTS.items():
            self.assertIn(section, SECTION_ORDER, document)

    def test_every_mandatory_section_is_in_the_order(self):
        for section in MANDATORY_SECTIONS:
            self.assertIn(section, SECTION_ORDER)

    def test_document_slot_resolved(self):
        self.assertEqual(
            section_for_document("Item-Logbook"), "limited-life-and-logbook-records"
        )

    def test_unplaceable_document_rejected(self):
        with self.assertRaises(ValueError):
            section_for_document("holiday-photographs")


class ValidateLineTests(unittest.TestCase):
    def test_ticked_line_normalised(self):
        record = validate_line(_line("item-logbook",
                                     "limited-life-and-logbook-records"))
        self.assertTrue(record["ticked"])
        self.assertEqual(record["pages"], 4)

    def test_unticked_line_carries_no_page_count(self):
        record = validate_line(
            _line("open-work-list", "open-work-and-constraints", ticked=False)
        )
        self.assertIsNone(record["pages"])

    def test_ticked_line_without_a_number_rejected(self):
        bad = _line("item-logbook", "limited-life-and-logbook-records")
        del bad["document_number"]
        with self.assertRaises(ValueError):
            validate_line(bad)

    def test_ticked_line_without_an_issue_rejected(self):
        bad = _line("item-logbook", "limited-life-and-logbook-records")
        del bad["issue"]
        with self.assertRaises(ValueError):
            validate_line(bad)

    def test_zero_page_count_rejected(self):
        bad = _line("item-logbook", "limited-life-and-logbook-records", pages=0)
        with self.assertRaises(ValueError):
            validate_line(bad)

    def test_float_page_count_rejected(self):
        bad = _line("item-logbook", "limited-life-and-logbook-records")
        bad["pages"] = 4.0
        with self.assertRaises(ValueError):
            validate_line(bad)

    def test_unknown_section_on_a_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_line(_line("item-logbook", "annex-of-wishes"))

    def test_tab_page_on_an_undelivered_line_rejected(self):
        bad = _line("open-work-list", "open-work-and-constraints", ticked=False)
        bad["declared_first_page"] = 30
        with self.assertRaises(ValueError):
            validate_line(bad)

    def test_non_mapping_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_line("certificate-of-conformity")


class ValidateContentsTests(unittest.TestCase):
    def test_package_normalised_in_listed_order(self):
        records = validate_contents(_package())
        self.assertEqual(records[0]["document"], "eidp-contents-list")
        self.assertEqual(len(records), 4)

    def test_duplicate_document_rejected(self):
        lines = _package()
        lines.append(_line("certificate-of-conformity", "conformity-declarations"))
        with self.assertRaises(ValueError):
            validate_contents(lines)

    def test_empty_contents_rejected(self):
        with self.assertRaises(ValueError):
            validate_contents([])


class OrderFindingTests(unittest.TestCase):
    def test_ordered_package_is_silent(self):
        self.assertEqual(order_findings(validate_contents(_package())), [])

    def test_two_lines_in_one_section_stay_silent(self):
        lines = _package()
        lines.insert(1, _line("eidp-cover-sheet", "cover-and-contents", pages=1))
        self.assertEqual(order_findings(validate_contents(lines)), [])

    def test_out_of_order_section_reported(self):
        lines = _package()
        lines.reverse()
        self.assertTrue(order_findings(validate_contents(lines)))


class PlacementFindingTests(unittest.TestCase):
    def test_correctly_filed_package_is_silent(self):
        self.assertEqual(placement_findings(validate_contents(_package())), [])

    def test_misfiled_document_reported(self):
        lines = _package()
        lines[1] = _line("certificate-of-conformity", "configuration-records", pages=1)
        findings = placement_findings(validate_contents(lines))
        self.assertEqual(len(findings), 1)
        self.assertIn("conformity-declarations", findings[0])

    def test_unplaceable_document_reported_not_raised(self):
        lines = _package()
        lines.append(_line("holiday-photographs", "open-work-and-constraints"))
        findings = placement_findings(validate_contents(lines))
        self.assertTrue(any("holiday-photographs" in f for f in findings))


class MandatorySectionTests(unittest.TestCase):
    def test_full_package_is_silent(self):
        self.assertEqual(mandatory_section_findings(validate_contents(_package())), [])

    def test_missing_mandatory_section_reported(self):
        lines = [line for line in _package()
                 if line["section"] != "configuration-records"]
        findings = mandatory_section_findings(validate_contents(lines))
        self.assertEqual(len(findings), 1)

    def test_unticked_line_does_not_fill_a_mandatory_section(self):
        lines = _package()
        lines[2] = _line("as-built-configuration-list", "configuration-records",
                         ticked=False)
        self.assertEqual(len(mandatory_section_findings(validate_contents(lines))), 1)


class PageRangeTests(unittest.TestCase):
    def test_ranges_run_on_from_the_first_sheet(self):
        paging = page_range_findings(validate_contents(_package()))
        self.assertEqual(paging["ranges"][0]["first_page"], FIRST_PAGE)
        self.assertEqual(paging["ranges"][0]["last_page"], 2)
        self.assertEqual(paging["ranges"][1]["first_page"], 3)

    def test_total_pages_is_the_last_sheet(self):
        paging = page_range_findings(validate_contents(_package()))
        self.assertEqual(paging["total_pages"], 29)

    def test_undelivered_line_takes_no_pages(self):
        lines = _package()
        lines.append(_line("open-work-list", "open-work-and-constraints",
                           ticked=False))
        paging = page_range_findings(validate_contents(lines))
        self.assertEqual(paging["total_pages"], 29)

    def test_matching_tab_page_is_silent(self):
        lines = _package()
        lines[2]["declared_first_page"] = 4
        self.assertEqual(page_range_findings(validate_contents(lines))["findings"], [])

    def test_wrong_tab_page_reported(self):
        lines = _package()
        lines[2]["declared_first_page"] = 11
        findings = page_range_findings(validate_contents(lines))["findings"]
        self.assertEqual(len(findings), 1)
        self.assertIn("as-built-configuration-list", findings[0])


class CompletionFractionTests(unittest.TestCase):
    def test_full_package_is_one(self):
        self.assertAlmostEqual(
            completion_fraction(validate_contents(_package())), 1.0, places=12
        )

    def test_one_open_line_of_four_is_three_quarters(self):
        lines = _package()
        lines.append(_line("open-work-list", "open-work-and-constraints",
                           ticked=False))
        self.assertAlmostEqual(
            completion_fraction(validate_contents(lines)), 0.8, places=12
        )

    def test_empty_records_rejected(self):
        with self.assertRaises(ValueError):
            completion_fraction([])


class RenderTests(unittest.TestCase):
    def test_one_rendered_line_per_record(self):
        records = validate_contents(_package())
        self.assertEqual(len(render_contents(records)), len(records))

    def test_undelivered_line_says_so(self):
        lines = _package()
        lines.append(_line("open-work-list", "open-work-and-constraints",
                           ticked=False))
        rendered = render_contents(validate_contents(lines))
        self.assertIn("not delivered", rendered[-1])

    def test_render_is_deterministic(self):
        records = validate_contents(_package())
        self.assertEqual(render_contents(records), render_contents(records))


class AssessContentsListTests(unittest.TestCase):
    def test_complete_package_passes(self):
        result = assess_contents_list(_package(), declared_total_pages=29)
        self.assertEqual(result["verdict"], "contents-list-complete")
        self.assertEqual(result["findings"], [])

    def test_declared_page_count_mismatch_reported(self):
        result = assess_contents_list(_package(), declared_total_pages=31)
        self.assertEqual(result["verdict"], "contents-list-open")
        self.assertTrue(any("cover declares" in f for f in result["findings"]))

    def test_declared_page_count_is_optional(self):
        result = assess_contents_list(_package())
        self.assertEqual(result["verdict"], "contents-list-complete")

    def test_open_line_is_listed_and_fails_the_package(self):
        lines = _package()
        lines.append(_line("open-work-list", "open-work-and-constraints",
                           ticked=False))
        result = assess_contents_list(lines)
        self.assertEqual(result["open_lines"], ["open-work-list"])
        self.assertEqual(result["verdict"], "contents-list-open")

    def test_page_ranges_are_reported(self):
        result = assess_contents_list(_package())
        self.assertEqual(len(result["page_ranges"]), 4)
        self.assertEqual(result["total_pages"], 29)

    def test_misfiled_document_fails_the_package(self):
        lines = _package()
        lines[3] = _line("acceptance-test-report", "open-work-and-constraints",
                         pages=20)
        result = assess_contents_list(lines)
        self.assertEqual(result["verdict"], "contents-list-open")

    def test_zero_declared_page_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_contents_list(_package(), declared_total_pages=0)

    def test_non_sequence_contents_rejected(self):
        with self.assertRaises(ValueError):
            assess_contents_list({"document": "certificate-of-conformity"})


if __name__ == "__main__":
    unittest.main()
