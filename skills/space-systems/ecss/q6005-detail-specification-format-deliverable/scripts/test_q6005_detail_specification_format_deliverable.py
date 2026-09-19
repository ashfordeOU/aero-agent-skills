"""Contract tests for the Annex B hybrid detail specification layout."""

import copy
import unittest

from q6005_detail_specification_format_deliverable_logic import (
    MANDATED_ENTRIES,
    MAX_HEADING_DEPTH,
    TEMPLATE_SECTIONS,
    assess_detail_specification_format,
    clause_tree_findings,
    entry_placement,
    format_clause_number,
    layout_conformance_ratio,
    parse_clause_number,
    parse_headings,
    section_coverage,
)

SECTION_TOTAL = len(TEMPLATE_SECTIONS)
ENTRY_TOTAL = sum(len(v) for v in MANDATED_ENTRIES.values())


def full_headings():
    return [{"number": number, "title": key.replace("_", " ")}
            for number, key in TEMPLATE_SECTIONS]


def full_entries():
    return {key: list(entries) for key, entries in MANDATED_ENTRIES.items() if entries}


def full_draft():
    return {"headings": full_headings(), "entries": full_entries()}


class ParseClauseNumberTests(unittest.TestCase):
    def test_single_level_number(self):
        self.assertEqual(parse_clause_number("4"), (4,))

    def test_two_level_number(self):
        self.assertEqual(parse_clause_number("3.2"), (3, 2))

    def test_trailing_dot_is_tolerated(self):
        self.assertEqual(parse_clause_number("5.1."), (5, 1))

    def test_alphabetic_component_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause_number("3.a")

    def test_padded_component_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause_number("3.02")

    def test_zero_component_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause_number("3.0")

    def test_blank_number_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause_number("   ")

    def test_non_string_number_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause_number(3.2)

    def test_format_round_trips(self):
        self.assertEqual(format_clause_number(parse_clause_number("4.3")), "4.3")

    def test_format_rejects_empty_path(self):
        with self.assertRaises(ValueError):
            format_clause_number(())

    def test_format_rejects_zero_component(self):
        with self.assertRaises(ValueError):
            format_clause_number((3, 0))


class ParseHeadingsTests(unittest.TestCase):
    def test_records_carry_depth_and_section(self):
        records = parse_headings([{"number": "3.2"}])
        self.assertEqual(records[0]["depth"], 2)
        self.assertEqual(records[0]["section"], "design_and_construction")

    def test_heading_outside_template_has_no_section(self):
        self.assertIsNone(parse_headings([{"number": "9"}])[0]["section"])

    def test_duplicate_number_rejected(self):
        with self.assertRaises(ValueError):
            parse_headings([{"number": "3"}, {"number": "3."}])

    def test_heading_without_number_rejected(self):
        with self.assertRaises(ValueError):
            parse_headings([{"title": "Scope"}])

    def test_empty_heading_list_rejected(self):
        with self.assertRaises(ValueError):
            parse_headings([])

    def test_non_text_title_rejected(self):
        with self.assertRaises(ValueError):
            parse_headings([{"number": "1", "title": 12}])


class ClauseTreeTests(unittest.TestCase):
    def test_complete_template_has_no_tree_fault(self):
        tree = clause_tree_findings(parse_headings(full_headings()))
        self.assertEqual(tree["orphan_headings"], ())
        self.assertEqual(tree["sibling_numbering_breaks"], ())
        self.assertEqual(tree["over_deep_headings"], ())

    def test_subclause_without_its_parent_is_an_orphan(self):
        tree = clause_tree_findings(parse_headings([{"number": "1"}, {"number": "2.1"}]))
        self.assertEqual(tree["orphan_headings"], ("2.1",))

    def test_skipped_sibling_is_reported(self):
        headings = [h for h in full_headings() if h["number"] != "3.3"]
        tree = clause_tree_findings(parse_headings(headings))
        self.assertIn("3.4", tree["sibling_numbering_breaks"])

    def test_nesting_beyond_the_layout_depth_is_reported(self):
        headings = full_headings() + [{"number": "3.2.1"}]
        tree = clause_tree_findings(parse_headings(headings))
        self.assertEqual(tree["over_deep_headings"], ("3.2.1",))

    def test_layout_depth_is_two(self):
        self.assertEqual(MAX_HEADING_DEPTH, 2)


class SectionCoverageTests(unittest.TestCase):
    def test_full_draft_covers_every_template_section(self):
        coverage = section_coverage(parse_headings(full_headings()))
        self.assertEqual(coverage["absent_sections"], ())
        self.assertEqual(coverage["headings_outside_template"], ())

    def test_dropped_clause_is_reported_absent(self):
        headings = [h for h in full_headings() if h["number"] != "4.2"]
        coverage = section_coverage(parse_headings(headings))
        self.assertEqual(coverage["absent_sections"], ("lot_acceptance",))

    def test_invented_clause_is_reported_outside_the_template(self):
        coverage = section_coverage(parse_headings(full_headings() + [{"number": "6"}]))
        self.assertEqual(coverage["headings_outside_template"], ("6",))


class EntryPlacementTests(unittest.TestCase):
    def test_full_entry_set_is_clean(self):
        placement = entry_placement(full_entries())
        self.assertEqual(placement["missing_entries"], ())
        self.assertEqual(placement["misfiled_entries"], ())
        self.assertEqual(placement["unknown_entries"], ())

    def test_dropped_entry_is_reported_missing(self):
        entries = full_entries()
        entries["marking"] = ["marking_content"]
        self.assertEqual(entry_placement(entries)["missing_entries"], ("marking_location",))

    def test_entry_under_the_wrong_clause_is_reported_misfiled(self):
        entries = full_entries()
        entries["design_and_construction"].remove("sealing_method")
        entries["scope"].append("sealing_method")
        misfiled = entry_placement(entries)["misfiled_entries"]
        self.assertEqual(len(misfiled), 1)
        self.assertEqual(misfiled[0]["entry"], "sealing_method")
        self.assertEqual(misfiled[0]["owning_clause"], "3.2")

    def test_extra_entry_is_grouped_as_unknown(self):
        entries = full_entries()
        entries["scope"].append("supplier_logo")
        self.assertEqual(entry_placement(entries)["unknown_entries"], ("supplier_logo",))

    def test_same_entry_under_two_clauses_rejected(self):
        entries = full_entries()
        entries["marking"].append("limit_table")
        with self.assertRaises(ValueError):
            entry_placement(entries)

    def test_non_mapping_entries_rejected(self):
        with self.assertRaises(ValueError):
            entry_placement([("scope", ["circuit_designation"])])

    def test_blank_entry_name_rejected(self):
        with self.assertRaises(ValueError):
            entry_placement({"scope": ["  "]})

    def test_non_sequence_entry_list_rejected(self):
        with self.assertRaises(ValueError):
            entry_placement({"scope": "circuit_designation"})


class ConformanceRatioTests(unittest.TestCase):
    def test_full_draft_scores_one(self):
        ratio = layout_conformance_ratio(parse_headings(full_headings()), full_entries())
        self.assertAlmostEqual(ratio, 1.0, places=9)

    def test_one_missing_entry_costs_one_obligation(self):
        entries = full_entries()
        entries["packaging"] = []
        ratio = layout_conformance_ratio(parse_headings(full_headings()), entries)
        expected = (SECTION_TOTAL + ENTRY_TOTAL - 1) / (SECTION_TOTAL + ENTRY_TOTAL)
        self.assertAlmostEqual(ratio, expected, places=9)

    def test_ratio_never_falls_below_zero(self):
        headings = [{"number": "9"}, {"number": "9.9"}]
        ratio = layout_conformance_ratio(parse_headings(headings), {})
        self.assertAlmostEqual(ratio, 0.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_conformant_draft_is_accepted(self):
        result = assess_detail_specification_format(full_draft())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["conformant"])
        self.assertAlmostEqual(result["layout_conformance_ratio"], 1.0, places=9)

    def test_missing_clause_holds_the_draft(self):
        draft = full_draft()
        draft["headings"] = [h for h in draft["headings"] if h["number"] != "5.2"]
        result = assess_detail_specification_format(draft)
        self.assertEqual(result["verdict"], "hold")
        self.assertIn("documentation", result["coverage"]["absent_sections"])

    def test_orphan_heading_holds_the_draft(self):
        draft = full_draft()
        draft["headings"] = [h for h in draft["headings"] if h["number"] != "4"]
        result = assess_detail_specification_format(draft)
        self.assertEqual(result["verdict"], "hold")
        self.assertIn("4.1", result["tree"]["orphan_headings"])

    def test_extra_entry_only_earns_a_remark(self):
        draft = full_draft()
        draft["entries"]["scope"].append("supplier_logo")
        result = assess_detail_specification_format(draft)
        self.assertEqual(result["verdict"], "accept-with-remarks")

    def test_misfiled_entry_names_its_owning_clause_in_the_finding(self):
        draft = full_draft()
        draft["entries"]["electrical_characteristics"].remove("test_conditions")
        draft["entries"]["marking"].append("test_conditions")
        findings = assess_detail_specification_format(draft)["findings"]
        self.assertTrue(any("3.3" in f for f in findings))

    def test_missing_headings_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_detail_specification_format({"entries": {}})

    def test_non_mapping_draft_rejected(self):
        with self.assertRaises(ValueError):
            assess_detail_specification_format("draft")

    def test_original_draft_is_not_mutated(self):
        draft = full_draft()
        snapshot = copy.deepcopy(draft)
        assess_detail_specification_format(draft)
        self.assertEqual(draft, snapshot)


if __name__ == "__main__":
    unittest.main()
