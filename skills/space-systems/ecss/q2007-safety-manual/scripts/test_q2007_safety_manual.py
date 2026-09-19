"""Contract tests for the clause 5.9.3 safety-manual content and update logic."""

import unittest

from q2007_safety_manual_logic import (
    FRACTION_TOLERANCE,
    REQUIRED_CHAPTERS,
    assess_chapter,
    assess_safety_manual,
    compare_revisions,
    distribution_acknowledgement,
    missing_chapters,
    parse_revision,
    revision_key,
    stale_hazard_changes,
    update_currency,
    validate_chapter,
)


def chapter(name, revision="C.2", approved_by="centre director", pages=6):
    return {
        "name": name,
        "revision": revision,
        "approved_by": approved_by,
        "pages": pages,
    }


def full_chapters():
    return [chapter(name) for name in REQUIRED_CHAPTERS]


class RevisionParsingTests(unittest.TestCase):
    def test_parses_issue_and_number(self):
        self.assertEqual(parse_revision("B.3"), ("B", 3))

    def test_lowercase_is_normalised(self):
        self.assertEqual(parse_revision("b.3"), ("B", 3))

    def test_surrounding_space_is_ignored(self):
        self.assertEqual(parse_revision("  C.0 "), ("C", 0))

    def test_multi_letter_issue_accepted(self):
        self.assertEqual(parse_revision("AA.1"), ("AA", 1))

    def test_missing_separator_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("B3")

    def test_two_separators_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("B.3.1")

    def test_transposed_parts_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("3.B")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("   ")

    def test_negative_revision_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("B.-1")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision(3)


class RevisionOrderingTests(unittest.TestCase):
    def test_same_issue_orders_by_number(self):
        self.assertEqual(compare_revisions("B.2", "B.3"), -1)

    def test_later_issue_outranks_a_higher_number(self):
        self.assertEqual(compare_revisions("C.0", "B.9"), 1)

    def test_equal_identifiers_compare_equal(self):
        self.assertEqual(compare_revisions("B.3", "b.3"), 0)

    def test_two_letter_issue_outranks_one_letter(self):
        self.assertEqual(compare_revisions("AA.0", "Z.9"), 1)

    def test_key_is_sortable(self):
        keys = sorted([revision_key("B.10"), revision_key("B.2"), revision_key("A.9")])
        self.assertEqual(keys[0], revision_key("A.9"))
        self.assertEqual(keys[-1], revision_key("B.10"))


class ChapterTests(unittest.TestCase):
    def test_complete_manual_misses_nothing(self):
        self.assertEqual(missing_chapters(full_chapters()), ())

    def test_absent_chapter_is_named(self):
        chapters = [c for c in full_chapters() if c["name"] != "emergency-plans"]
        self.assertEqual(missing_chapters(chapters), ("emergency-plans",))

    def test_plain_name_list_is_accepted(self):
        self.assertEqual(missing_chapters(list(REQUIRED_CHAPTERS)), ())

    def test_blank_chapter_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_chapters([{"name": "  "}])

    def test_valid_chapter_normalises(self):
        record = validate_chapter(chapter("hazard-inventory", "B.4"))
        self.assertEqual(record["revision"], "B.4")
        self.assertEqual(record["issue"], "B")

    def test_zero_page_chapter_rejected(self):
        with self.assertRaises(ValueError):
            validate_chapter(chapter("hazard-inventory", pages=0))

    def test_non_integer_pages_rejected(self):
        with self.assertRaises(ValueError):
            validate_chapter(chapter("hazard-inventory", pages=6.0))

    def test_missing_revision_rejected(self):
        bad = chapter("hazard-inventory")
        del bad["revision"]
        with self.assertRaises(ValueError):
            validate_chapter(bad)

    def test_unapproved_chapter_is_a_finding(self):
        record = assess_chapter(chapter("hazard-controls", approved_by=None), "C.2")
        self.assertFalse(record["controlled"])

    def test_chapter_ahead_of_the_manual_is_a_finding(self):
        record = assess_chapter(chapter("hazard-controls", "D.0"), "C.2")
        self.assertIn("ahead of the manual", " ".join(record["findings"]))

    def test_chapter_behind_the_manual_is_controlled(self):
        record = assess_chapter(chapter("hazard-controls", "B.9"), "C.2")
        self.assertTrue(record["controlled"])


class CurrencyTests(unittest.TestCase):
    def test_inside_the_interval_is_current(self):
        self.assertEqual(update_currency(100, 730, 400), "current")

    def test_exactly_on_the_interval_is_due(self):
        self.assertEqual(update_currency(100, 730, 830), "due")

    def test_past_the_interval_is_overdue(self):
        self.assertEqual(update_currency(100, 730, 900), "overdue")

    def test_day_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            update_currency(100, 730, 50)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            update_currency(100, 0, 400)

    def test_hazard_change_after_issue_is_returned(self):
        self.assertEqual(stale_hazard_changes(100, [50, 150, 120]), [120, 150])

    def test_hazard_change_on_the_issue_day_is_not_stale(self):
        self.assertEqual(stale_hazard_changes(100, [100]), [])

    def test_negative_change_day_rejected(self):
        with self.assertRaises(ValueError):
            stale_hazard_changes(100, [-5])


class DistributionTests(unittest.TestCase):
    def test_all_acknowledged_is_one(self):
        self.assertAlmostEqual(distribution_acknowledgement(12, 12), 1.0, places=9)

    def test_partial_acknowledgement(self):
        self.assertAlmostEqual(distribution_acknowledgement(9, 12), 0.75, places=9)

    def test_no_copies_issued_rejected(self):
        with self.assertRaises(ValueError):
            distribution_acknowledgement(0, 0)

    def test_more_acknowledgements_than_copies_rejected(self):
        with self.assertRaises(ValueError):
            distribution_acknowledgement(13, 12)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            distribution_acknowledgement(-1, 12)


class ManualAssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        out = {
            "revision": "C.2",
            "issue_day": 100,
            "review_interval_days": 730,
            "today": 400,
            "chapters": full_chapters(),
            "copies_issued": 12,
            "copies_acknowledged": 12,
            "hazard_change_days": [80],
            "obsolete_copies_withdrawn": True,
            "required_acknowledgement": 1.0,
        }
        out.update(overrides)
        return out

    def test_controlled_manual_has_no_findings(self):
        result = assess_safety_manual(self.spec())
        self.assertTrue(result["manual_controlled"])
        self.assertEqual(result["missing_chapters"], ())

    def test_missing_chapter_is_a_finding(self):
        chapters = [c for c in full_chapters() if c["name"] != "responsibilities"]
        result = assess_safety_manual(self.spec(chapters=chapters))
        self.assertFalse(result["manual_controlled"])
        self.assertEqual(result["missing_chapters"], ("responsibilities",))

    def test_chapter_ahead_of_the_manual_blocks(self):
        chapters = full_chapters()
        chapters[0] = chapter("hazard-inventory", "D.1")
        self.assertFalse(assess_safety_manual(self.spec(chapters=chapters))["manual_controlled"])

    def test_overdue_review_is_a_finding(self):
        result = assess_safety_manual(self.spec(today=900))
        self.assertEqual(result["currency"], "overdue")
        self.assertFalse(result["manual_controlled"])

    def test_hazard_change_after_issue_makes_it_stale(self):
        result = assess_safety_manual(self.spec(hazard_change_days=[80, 250]))
        self.assertEqual(result["stale_hazard_changes"], [250])
        self.assertFalse(result["manual_controlled"])

    def test_acknowledgement_exactly_on_the_requirement_passes(self):
        result = assess_safety_manual(
            self.spec(copies_acknowledged=9, required_acknowledgement=0.75)
        )
        self.assertAlmostEqual(result["acknowledgement"], 0.75, places=9)
        self.assertTrue(result["manual_controlled"])

    def test_short_acknowledgement_is_a_finding(self):
        result = assess_safety_manual(self.spec(copies_acknowledged=6))
        self.assertFalse(result["manual_controlled"])

    def test_obsolete_copies_left_out_is_a_finding(self):
        result = assess_safety_manual(self.spec(obsolete_copies_withdrawn=False))
        self.assertFalse(result["manual_controlled"])

    def test_duplicate_chapter_rejected(self):
        chapters = full_chapters() + [chapter("responsibilities")]
        with self.assertRaises(ValueError):
            assess_safety_manual(self.spec(chapters=chapters))

    def test_empty_chapter_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_manual(self.spec(chapters=[]))

    def test_missing_spec_key_rejected(self):
        bad = self.spec()
        del bad["copies_issued"]
        with self.assertRaises(ValueError):
            assess_safety_manual(bad)

    def test_bad_manual_revision_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_manual(self.spec(revision="rev 2"))

    def test_tolerance_is_representation_sized(self):
        self.assertAlmostEqual(FRACTION_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
