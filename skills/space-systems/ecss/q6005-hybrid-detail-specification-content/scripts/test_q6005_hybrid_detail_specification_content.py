"""Contract tests for the clause 7.2 hybrid detail-specification content logic."""

import unittest

from q6005_hybrid_detail_specification_content_logic import (
    TEMPLATE_SECTIONS,
    assess_detail_specification,
    completeness_ratio,
    declared_documents,
    empty_sections,
    longest_in_template_order,
    missing_sections,
    normalize_key,
    ordering_displacements,
    unexpected_sections,
    unresolved_references,
    validate_sections,
)

DOCS = ["ECSS-Q-ST-60-05", "PID-4471", "DWG-88012"]


def _full_sections():
    return [
        {"key": "identification", "content": "Hybrid HY-2213, issue B"},
        {"key": "scope", "content": "Thick-film hybrid power conditioner"},
        {"key": "applicable-documents", "content": list(DOCS)},
        {
            "key": "requirements",
            "content": ["Electrical", "Mechanical", "Environmental"],
            "references": ["PID-4471"],
        },
        {
            "key": "verification-and-quality-assurance",
            "content": ["Screening", "Lot acceptance"],
            "references": ["ECSS-Q-ST-60-05"],
        },
        {"key": "delivery-and-packaging", "content": "Dry-pack, humidity indicator"},
        {"key": "notes", "content": "Supersedes issue A", "references": ["DWG-88012"]},
    ]


class NormalizeKeyTests(unittest.TestCase):
    def test_spaces_become_hyphens(self):
        self.assertEqual(normalize_key("Applicable Documents"), "applicable-documents")

    def test_underscores_become_hyphens(self):
        self.assertEqual(normalize_key("delivery_and_packaging"), "delivery-and-packaging")

    def test_repeated_separators_collapse(self):
        self.assertEqual(normalize_key("  notes   "), "notes")

    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError):
            normalize_key("   ")

    def test_non_string_key_rejected(self):
        with self.assertRaises(ValueError):
            normalize_key(7)


class ValidateSectionsTests(unittest.TestCase):
    def test_positions_follow_declaration_order(self):
        records = validate_sections(_full_sections())
        self.assertEqual([r["position"] for r in records], list(range(7)))

    def test_duplicate_section_rejected(self):
        sections = _full_sections()
        sections.append({"key": "Notes", "content": "again"})
        with self.assertRaises(ValueError):
            validate_sections(sections)

    def test_empty_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([])

    def test_section_without_a_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"content": "text"}])

    def test_non_string_content_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"key": "scope", "content": [1, 2]}])

    def test_non_string_citation_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections([{"key": "scope", "content": "x", "references": [4]}])

    def test_repeated_citation_is_collapsed(self):
        records = validate_sections(
            [{"key": "scope", "content": "x", "references": ["A", "A"]}]
        )
        self.assertEqual(records[0]["references"], ("A",))


class CoverageTests(unittest.TestCase):
    def test_full_draft_omits_nothing(self):
        self.assertEqual(missing_sections(_full_sections()), ())

    def test_omitted_section_is_named_in_template_order(self):
        sections = [s for s in _full_sections() if s["key"] not in ("scope", "notes")]
        self.assertEqual(missing_sections(sections), ("scope", "notes"))

    def test_whitespace_content_counts_as_empty(self):
        sections = _full_sections()
        sections[1]["content"] = "   "
        self.assertEqual(empty_sections(sections), ("scope",))

    def test_empty_list_content_counts_as_empty(self):
        sections = _full_sections()
        sections[3]["content"] = []
        self.assertEqual(empty_sections(sections), ("requirements",))

    def test_section_outside_the_template_is_placed(self):
        sections = _full_sections()
        sections.append({"key": "marketing-summary", "content": "blurb"})
        self.assertEqual(unexpected_sections(sections), ("marketing-summary",))

    def test_completeness_is_one_for_a_full_draft(self):
        self.assertAlmostEqual(completeness_ratio(_full_sections()), 1.0, places=9)

    def test_completeness_counts_only_filled_sections(self):
        sections = _full_sections()
        sections[6]["content"] = ""
        self.assertAlmostEqual(completeness_ratio(sections), 6.0 / 7.0, places=9)

    def test_completeness_ignores_sections_outside_the_template(self):
        sections = _full_sections()
        sections.append({"key": "annex-a", "content": "extra"})
        self.assertAlmostEqual(completeness_ratio(sections), 1.0, places=9)


class OrderingTests(unittest.TestCase):
    def test_template_order_run_covers_a_clean_draft(self):
        self.assertEqual(longest_in_template_order(_full_sections()), list(TEMPLATE_SECTIONS))

    def test_clean_draft_has_no_displacement(self):
        self.assertEqual(ordering_displacements(_full_sections()), ())

    def test_one_moved_section_is_the_only_displacement(self):
        sections = _full_sections()
        moved = sections.pop(6)
        sections.insert(0, moved)
        self.assertEqual(ordering_displacements(sections), ("notes",))

    def test_reversed_draft_keeps_only_one_section_in_order(self):
        sections = list(reversed(_full_sections()))
        self.assertEqual(len(longest_in_template_order(sections)), 1)

    def test_run_ignores_sections_outside_the_template(self):
        sections = _full_sections()
        sections.insert(3, {"key": "annex-b", "content": "extra"})
        self.assertEqual(longest_in_template_order(sections), list(TEMPLATE_SECTIONS))


class ReferenceTests(unittest.TestCase):
    def test_listed_documents_are_read_from_the_applicable_section(self):
        self.assertEqual(declared_documents(_full_sections()), tuple(DOCS))

    def test_every_citation_resolves_in_a_clean_draft(self):
        self.assertEqual(unresolved_references(_full_sections()), [])

    def test_citation_of_an_unlisted_document_is_reported(self):
        sections = _full_sections()
        sections[3]["references"] = ["PID-4471", "STD-9999"]
        self.assertIn(("requirements", "STD-9999"), unresolved_references(sections))

    def test_absent_applicable_section_lists_no_documents(self):
        sections = [s for s in _full_sections() if s["key"] != "applicable-documents"]
        self.assertEqual(declared_documents(sections), ())


class AssessmentTests(unittest.TestCase):
    def test_clean_draft_is_acceptable(self):
        result = assess_detail_specification({"sections": _full_sections()})
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)

    def test_missing_section_holds_the_draft(self):
        sections = [s for s in _full_sections() if s["key"] != "notes"]
        result = assess_detail_specification({"sections": sections})
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["missing_sections"], ("notes",))

    def test_extra_section_holds_unless_explicitly_allowed(self):
        sections = _full_sections()
        sections.append({"key": "annex-c", "content": "extra"})
        held = assess_detail_specification({"sections": sections})
        self.assertFalse(held["acceptable"])
        allowed = assess_detail_specification(
            {"sections": sections, "allow_additional_sections": True}
        )
        self.assertTrue(allowed["acceptable"])

    def test_unresolved_citation_holds_the_draft(self):
        sections = _full_sections()
        sections[6]["references"] = ["DWG-00000"]
        result = assess_detail_specification({"sections": sections})
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("no listed applicable document" in f for f in result["findings"]))

    def test_several_defects_are_all_reported(self):
        sections = [s for s in _full_sections() if s["key"] != "scope"]
        sections[0]["content"] = ""
        result = assess_detail_specification({"sections": sections})
        self.assertEqual(len(result["findings"]), 2)

    def test_non_boolean_allowance_rejected(self):
        with self.assertRaises(ValueError):
            assess_detail_specification(
                {"sections": _full_sections(), "allow_additional_sections": "yes"}
            )

    def test_missing_sections_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_detail_specification({"draft": _full_sections()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_detail_specification(["sections"])

    def test_template_has_seven_ordered_sections(self):
        self.assertEqual(len(TEMPLATE_SECTIONS), 7)
        self.assertEqual(TEMPLATE_SECTIONS[0], "identification")
        self.assertEqual(TEMPLATE_SECTIONS[-1], "notes")


if __name__ == "__main__":
    unittest.main()
