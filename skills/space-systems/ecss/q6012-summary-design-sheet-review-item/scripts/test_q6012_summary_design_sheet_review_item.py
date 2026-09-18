#!/usr/bin/env python3
"""Contract test for the microwave die summary design sheet review item (offline)."""

import copy
import unittest

from q6012_summary_design_sheet_review_item_logic import (
    AGREEMENT_BROKEN,
    AGREEMENT_HELD,
    ANNOTATION_COMPLETE,
    ANNOTATION_INCOMPLETE,
    COVERAGE_COMPLETE,
    COVERAGE_INCOMPLETE,
    DEFAULT_ROUNDING_TOLERANCE,
    ISSUE_BEHIND,
    ISSUE_CURRENT,
    PAGE_FITS,
    PAGE_NEARLY_FULL,
    PAGE_OVER,
    REQUIRED_CHARACTERISTICS,
    VERDICT_ACTIONED,
    VERDICT_CLOSED,
    VERDICT_REJECTED,
    assess_agreement,
    assess_annotation,
    assess_coverage,
    assess_issue_currency,
    assess_page_budget,
    canonical_text,
    normalize_entries,
    relative_difference,
    review_summary_design_sheet_item,
    sheet_line_count,
    values_agree,
)

REFERENCE_ENTRIES = [
    {
        "characteristic": "die-outline-dimensions",
        "summary_value": "2.4 mm by 1.8 mm",
        "source_value": "2.4 mm by 1.8 mm",
        "unit": None,
        "source_reference": "DS-001 issue 2",
        "rendered_lines": 2,
    },
    {
        "characteristic": "die-thickness",
        "summary_value": 100.0,
        "source_value": 100.0,
        "unit": "micrometre",
        "source_reference": "DS-001 issue 2",
        "rendered_lines": 1,
    },
    {
        "characteristic": "operating-frequency-band",
        "summary_value": "ka band 27 to 31 ghz",
        "source_value": "Ka band  27 to 31 GHz",
        "unit": None,
        "source_reference": "DS-001 issue 2",
        "rendered_lines": 1,
    },
    {
        "characteristic": "rated-output-power",
        "summary_value": 4.0,
        "source_value": 4.02,
        "unit": "watt",
        "source_reference": "TP-030 issue 3",
        "rendered_lines": 1,
    },
    {
        "characteristic": "maximum-junction-temperature",
        "summary_value": 150.0,
        "source_value": 150.0,
        "unit": "degree-celsius",
        "source_reference": "DS-001 issue 2",
        "rendered_lines": 1,
    },
    {
        "characteristic": "bias-supply-voltage",
        "summary_value": 5.0,
        "source_value": 5.0,
        "unit": "volt",
        "source_reference": "DS-001 issue 2",
        "rendered_lines": 1,
    },
    {
        "characteristic": "backside-metallization",
        "summary_value": "gold",
        "source_value": "Gold",
        "unit": None,
        "source_reference": "PI-020 issue 1",
        "rendered_lines": 1,
    },
    {
        "characteristic": "bond-pad-layout-reference",
        "summary_value": "LD-010 issue 1",
        "source_value": "LD-010 issue 1",
        "unit": None,
        "source_reference": "LD-010 issue 1",
        "rendered_lines": 2,
    },
]

REFERENCE_CASE = {
    "entries": REFERENCE_ENTRIES,
    "sheet_issued_day": 150.0,
    "latest_detail_issued_day": 140.0,
}


def _edit(target, **fields):
    """Reference entries with one named characteristic overridden."""
    rows = copy.deepcopy(REFERENCE_ENTRIES)
    for row in rows:
        if row["characteristic"] == target:
            row.update(fields)
            return rows
    raise AssertionError("no such reference entry")


def _drop(target):
    """Reference entries with one characteristic removed from the sheet."""
    return [
        row for row in copy.deepcopy(REFERENCE_ENTRIES)
        if row["characteristic"] != target
    ]


def _case(**overrides):
    case = copy.deepcopy(REFERENCE_CASE)
    case.update(overrides)
    return case


def _sheet(rows=None):
    return normalize_entries(
        copy.deepcopy(REFERENCE_ENTRIES) if rows is None else rows
    )


class CanonicalTextTests(unittest.TestCase):
    def test_case_is_folded(self):
        self.assertEqual(canonical_text("Gold"), canonical_text("gold"))

    def test_inner_space_is_collapsed(self):
        self.assertEqual(canonical_text("Ka band  27 GHz"), "ka band 27 ghz")

    def test_blank_text_rejected(self):
        with self.assertRaises(ValueError):
            canonical_text("   ")

    def test_non_string_text_rejected(self):
        with self.assertRaises(ValueError):
            canonical_text(4.0)


class RelativeDifferenceTests(unittest.TestCase):
    def test_identical_values_differ_by_nothing(self):
        self.assertAlmostEqual(relative_difference(100.0, 100.0), 0.0, places=9)

    def test_difference_is_scaled_on_the_source(self):
        self.assertAlmostEqual(relative_difference(102.0, 100.0), 0.02, places=9)

    def test_difference_is_unsigned(self):
        self.assertAlmostEqual(
            relative_difference(98.0, 100.0),
            relative_difference(102.0, 100.0),
            places=9,
        )

    def test_a_small_source_uses_a_unit_denominator(self):
        self.assertAlmostEqual(relative_difference(0.2, 0.0), 0.2, places=9)

    def test_non_numeric_summary_rejected(self):
        with self.assertRaises(ValueError):
            relative_difference("one hundred", 100.0)

    def test_a_value_inside_the_tolerance_agrees(self):
        self.assertTrue(values_agree(100.2, 100.0, 0.005))

    def test_a_value_outside_the_tolerance_does_not_agree(self):
        self.assertFalse(values_agree(105.0, 100.0, 0.005))

    def test_a_value_exactly_on_the_tolerance_agrees(self):
        # (3.015 - 3.0) / 3.0 evaluates just above 0.005, so a strict
        # comparison would report a disagreement on a value that sits exactly
        # on the stated rounding tolerance.
        self.assertGreater(relative_difference(3.015, 3.0), 0.0)
        self.assertAlmostEqual(
            relative_difference(3.015, 3.0), DEFAULT_ROUNDING_TOLERANCE, places=9
        )
        self.assertTrue(values_agree(3.015, 3.0, DEFAULT_ROUNDING_TOLERANCE))

    def test_a_tolerance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            values_agree(100.0, 100.0, 1.5)


class NormalizeEntryTests(unittest.TestCase):
    def test_entries_come_back_in_characteristic_order(self):
        names = [entry["characteristic"] for entry in _sheet()]
        self.assertEqual(names, sorted(names))

    def test_numeric_and_textual_entries_are_marked_apart(self):
        kinds = {entry["characteristic"]: entry["kind"] for entry in _sheet()}
        self.assertEqual(kinds["die-thickness"], "numeric")
        self.assertEqual(kinds["backside-metallization"], "text")

    def test_rendered_lines_default_to_one(self):
        rows = _edit("die-thickness")
        for row in rows:
            if row["characteristic"] == "die-thickness":
                del row["rendered_lines"]
        entries = normalize_entries(rows)
        thickness = [e for e in entries if e["characteristic"] == "die-thickness"][0]
        self.assertEqual(thickness["rendered_lines"], 1)

    def test_empty_sheet_rejected(self):
        with self.assertRaises(ValueError):
            normalize_entries([])

    def test_characteristic_stated_twice_rejected(self):
        rows = copy.deepcopy(REFERENCE_ENTRIES)
        rows.append(copy.deepcopy(REFERENCE_ENTRIES[1]))
        with self.assertRaises(ValueError):
            normalize_entries(rows)

    def test_characteristic_outside_the_programme_set_rejected(self):
        rows = _edit("die-thickness", characteristic="favourite-colour")
        with self.assertRaises(ValueError):
            normalize_entries(rows)

    def test_a_number_summarising_a_text_source_rejected(self):
        rows = _edit("backside-metallization", summary_value=4.0)
        with self.assertRaises(ValueError):
            normalize_entries(rows)

    def test_a_missing_source_value_rejected(self):
        rows = _edit("die-thickness", source_value=None)
        with self.assertRaises(ValueError):
            normalize_entries(rows)

    def test_zero_rendered_lines_rejected(self):
        with self.assertRaises(ValueError):
            normalize_entries(_edit("die-thickness", rendered_lines=0))

    def test_blank_unit_rejected(self):
        with self.assertRaises(ValueError):
            normalize_entries(_edit("die-thickness", unit="  "))

    def test_unknown_entry_field_rejected(self):
        rows = copy.deepcopy(REFERENCE_ENTRIES)
        rows[0]["font"] = "the small one"
        with self.assertRaises(ValueError):
            normalize_entries(rows)


class CoverageTests(unittest.TestCase):
    def test_a_full_sheet_carries_every_characteristic(self):
        result = assess_coverage(_sheet())
        self.assertEqual(result["status"], COVERAGE_COMPLETE)
        self.assertEqual(result["absent"], ())
        self.assertAlmostEqual(result["coverage_share"], 1.0, places=9)

    def test_a_missing_characteristic_is_reported(self):
        result = assess_coverage(_sheet(_drop("bias-supply-voltage")))
        self.assertEqual(result["status"], COVERAGE_INCOMPLETE)
        self.assertEqual(result["absent"], ("bias-supply-voltage",))

    def test_coverage_share_is_counted_over_the_required_set(self):
        result = assess_coverage(_sheet(_drop("bias-supply-voltage")))
        expected = float(len(REQUIRED_CHARACTERISTICS) - 1) / float(
            len(REQUIRED_CHARACTERISTICS)
        )
        self.assertAlmostEqual(result["coverage_share"], expected, places=9)

    def test_an_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverage(_sheet(), [])


class AgreementTests(unittest.TestCase):
    def test_the_reference_sheet_agrees_with_its_sources(self):
        result = assess_agreement(_sheet())
        self.assertEqual(result["status"], AGREEMENT_HELD)
        self.assertEqual(result["disagreements"], ())
        self.assertEqual(result["findings"], [])

    def test_a_rounded_value_is_recorded_without_being_a_disagreement(self):
        result = assess_agreement(_sheet())
        self.assertIn("rated-output-power", result["rounded_within_tolerance"])

    def test_a_value_beyond_the_tolerance_contradicts_the_source(self):
        result = assess_agreement(_sheet(_edit("rated-output-power", summary_value=4.5)))
        self.assertEqual(result["status"], AGREEMENT_BROKEN)
        self.assertEqual(result["disagreements"], ("rated-output-power",))

    def test_a_textual_value_matches_across_case_and_space(self):
        result = assess_agreement(_sheet())
        self.assertNotIn("operating-frequency-band", result["disagreements"])

    def test_a_textual_value_that_says_something_else_contradicts(self):
        result = assess_agreement(
            _sheet(_edit("backside-metallization", summary_value="tin"))
        )
        self.assertEqual(result["status"], AGREEMENT_BROKEN)
        self.assertIn("backside-metallization", result["disagreements"])

    def test_a_tighter_tolerance_turns_a_rounding_into_a_disagreement(self):
        result = assess_agreement(_sheet(), 0.001)
        self.assertEqual(result["status"], AGREEMENT_BROKEN)
        self.assertIn("rated-output-power", result["disagreements"])

    def test_a_value_on_the_tolerance_is_not_a_disagreement(self):
        result = assess_agreement(
            _sheet(_edit("die-thickness", summary_value=3.015, source_value=3.0))
        )
        self.assertEqual(result["status"], AGREEMENT_HELD)
        self.assertIn("die-thickness", result["rounded_within_tolerance"])


class AnnotationTests(unittest.TestCase):
    def test_the_reference_sheet_is_fully_annotated(self):
        result = assess_annotation(_sheet())
        self.assertEqual(result["status"], ANNOTATION_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_a_numeric_value_with_no_unit_is_reported(self):
        result = assess_annotation(_sheet(_edit("die-thickness", unit=None)))
        self.assertEqual(result["status"], ANNOTATION_INCOMPLETE)
        self.assertEqual(result["without_unit"], ("die-thickness",))

    def test_a_textual_value_needs_no_unit(self):
        result = assess_annotation(_sheet())
        self.assertNotIn("backside-metallization", result["without_unit"])

    def test_a_value_with_no_source_reference_is_reported(self):
        result = assess_annotation(
            _sheet(_edit("bias-supply-voltage", source_reference=None))
        )
        self.assertEqual(result["status"], ANNOTATION_INCOMPLETE)
        self.assertEqual(result["without_source_reference"], ("bias-supply-voltage",))


class PageBudgetTests(unittest.TestCase):
    def test_line_count_includes_the_header(self):
        self.assertEqual(sheet_line_count(_sheet(), 6), 16)

    def test_a_short_sheet_fits_the_page(self):
        result = assess_page_budget(_sheet())
        self.assertEqual(result["status"], PAGE_FITS)
        self.assertEqual(result["rendered_lines"], 16)

    def test_a_page_filled_exactly_to_the_caution_share_still_fits(self):
        result = assess_page_budget(_sheet(), 9, 20, 0.95)
        self.assertEqual(result["rendered_lines"], 19)
        self.assertAlmostEqual(result["fill_share"], 0.95, places=9)
        self.assertEqual(result["status"], PAGE_FITS)

    def test_a_page_above_the_caution_share_is_nearly_full(self):
        result = assess_page_budget(_sheet(), 10, 20, 0.95)
        self.assertEqual(result["status"], PAGE_NEARLY_FULL)

    def test_a_sheet_past_the_budget_is_over_one_page(self):
        result = assess_page_budget(_sheet(), 11, 20, 0.95)
        self.assertEqual(result["status"], PAGE_OVER)
        self.assertTrue(any("one page budget" in f for f in result["findings"]))

    def test_a_zero_page_budget_rejected(self):
        with self.assertRaises(ValueError):
            assess_page_budget(_sheet(), 6, 0, 0.95)

    def test_a_caution_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_page_budget(_sheet(), 6, 56, 1.4)


class IssueCurrencyTests(unittest.TestCase):
    def test_a_sheet_issued_after_the_detail_is_current(self):
        result = assess_issue_currency(150.0, 140.0)
        self.assertEqual(result["status"], ISSUE_CURRENT)
        self.assertAlmostEqual(result["lag_days"], -10.0, places=9)

    def test_a_sheet_issued_with_the_detail_is_current(self):
        result = assess_issue_currency(140.0, 140.0)
        self.assertEqual(result["status"], ISSUE_CURRENT)

    def test_a_sheet_issued_before_the_detail_is_behind(self):
        result = assess_issue_currency(130.0, 140.0)
        self.assertEqual(result["status"], ISSUE_BEHIND)
        self.assertAlmostEqual(result["lag_days"], 10.0, places=9)

    def test_an_inexact_detail_day_does_not_make_a_matching_sheet_behind(self):
        # 0.1 + 0.2 lands just above 0.3, so a strict comparison would call a
        # sheet issued on the same day as its detail behind it.
        result = assess_issue_currency(0.3, 0.1 + 0.2)
        self.assertEqual(result["status"], ISSUE_CURRENT)

    def test_a_negative_issue_day_rejected(self):
        with self.assertRaises(ValueError):
            assess_issue_currency(-1.0, 140.0)


class ReviewItemTests(unittest.TestCase):
    def test_reference_sheet_closes_the_item(self):
        result = review_summary_design_sheet_item(REFERENCE_CASE)
        self.assertEqual(result["verdict"], VERDICT_CLOSED)
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["findings"], [])

    def test_a_missing_characteristic_rejects_the_item(self):
        result = review_summary_design_sheet_item(
            _case(entries=_drop("bias-supply-voltage"))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["coverage"]["status"], COVERAGE_INCOMPLETE)

    def test_a_value_contradicting_the_detail_rejects_the_item(self):
        result = review_summary_design_sheet_item(
            _case(entries=_edit("rated-output-power", summary_value=4.5))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["agreement"]["status"], AGREEMENT_BROKEN)

    def test_a_sheet_past_the_page_budget_rejects_the_item(self):
        result = review_summary_design_sheet_item(
            _case(page_line_budget=20, header_lines=11)
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["page"]["status"], PAGE_OVER)

    def test_a_bare_number_leaves_an_action(self):
        result = review_summary_design_sheet_item(
            _case(entries=_edit("die-thickness", unit=None))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("unit" in action for action in result["actions"]))

    def test_a_missing_source_reference_leaves_an_action(self):
        result = review_summary_design_sheet_item(
            _case(entries=_edit("die-thickness", source_reference=None))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("detail document" in a for a in result["actions"]))

    def test_a_nearly_full_page_leaves_an_action(self):
        result = review_summary_design_sheet_item(
            _case(page_line_budget=20, header_lines=10)
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertEqual(result["page"]["status"], PAGE_NEARLY_FULL)

    def test_a_sheet_behind_the_detail_leaves_an_action(self):
        result = review_summary_design_sheet_item(_case(sheet_issued_day=130.0))
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertEqual(result["currency"]["status"], ISSUE_BEHIND)

    def test_a_tighter_rounding_tolerance_rejects_the_item(self):
        result = review_summary_design_sheet_item(_case(rounding_tolerance=0.001))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_several_findings_are_reported_together(self):
        rows = _edit("rated-output-power", summary_value=4.5)
        rows = [row for row in rows if row["characteristic"] != "die-thickness"]
        result = review_summary_design_sheet_item(_case(entries=rows))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            review_summary_design_sheet_item("die-thickness")

    def test_missing_sheet_issue_day_rejected(self):
        case = _case()
        del case["sheet_issued_day"]
        with self.assertRaises(ValueError):
            review_summary_design_sheet_item(case)

    def test_missing_entries_rejected(self):
        with self.assertRaises(ValueError):
            review_summary_design_sheet_item(
                {"sheet_issued_day": 150.0, "latest_detail_issued_day": 140.0}
            )


if __name__ == "__main__":
    unittest.main()
