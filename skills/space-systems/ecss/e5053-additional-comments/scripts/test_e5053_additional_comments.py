"""Contract tests for the clause 5.2.2.5 additional-comments audit."""

import unittest

from e5053_additional_comments_logic import (
    DUPLICATION_CEILING,
    EMPTY_FORMS,
    WORD_BUDGET,
    assess_additional_comments,
    assess_comment_set,
    duplication_share,
    extract_clause_references,
    find_normative_wording,
    informative_token_set,
    is_explicit_empty,
    normalize_note,
    unresolved_references,
    word_count,
)

INDEX = ("5.2.2.1", "5.2.2.2", "5.2.2.3", "5.2.2.4", "5.2.2.5", "5.3.1")
GOOD_NOTE = "Segmentation behaviour follows 5.3.1; queueing depth stays an implementation matter."


def record(**overrides):
    base = {
        "primitive": "T-Data.request",
        "function": "Requests the conveyance of an application unit to the peer entity.",
        "semantics": "Carries the unit and an optional priority selector.",
        "when_generated": "Issued by the local user while the association is open.",
        "effect_on_receipt": "The provider queues the unit for conveyance.",
        "additional_comments": GOOD_NOTE,
    }
    base.update(overrides)
    return base


class NormalizeTests(unittest.TestCase):
    def test_whitespace_is_collapsed(self):
        self.assertEqual(normalize_note("  a\n  b  "), "a b")

    def test_non_text_note_rejected(self):
        with self.assertRaises(ValueError):
            normalize_note(12)

    def test_word_count_is_on_the_normalised_text(self):
        self.assertEqual(word_count("  one   two \n three "), 3)

    def test_empty_text_has_no_words(self):
        self.assertEqual(word_count("   "), 0)


class EmptyFormTests(unittest.TestCase):
    def test_every_declared_empty_form_is_recognised(self):
        for form in EMPTY_FORMS:
            self.assertTrue(is_explicit_empty(form))

    def test_empty_form_is_recognised_with_case_and_a_full_stop(self):
        self.assertTrue(is_explicit_empty("None."))

    def test_real_note_is_not_an_empty_form(self):
        self.assertFalse(is_explicit_empty(GOOD_NOTE))


class NormativeWordingTests(unittest.TestCase):
    def test_marker_found_mid_sentence(self):
        self.assertIn("shall", find_normative_wording("The provider shall queue the unit."))

    def test_marker_found_regardless_of_case(self):
        self.assertIn("must", find_normative_wording("Implementations MUST retry once."))

    def test_informative_note_has_no_marker(self):
        self.assertEqual(find_normative_wording(GOOD_NOTE), ())


class ReferenceTests(unittest.TestCase):
    def test_dotted_clause_number_extracted(self):
        self.assertEqual(extract_clause_references("see 5.3.1 for detail"), ("5.3.1",))

    def test_repeated_reference_collapsed(self):
        self.assertEqual(extract_clause_references("5.3.1 and again 5.3.1"), ("5.3.1",))

    def test_plain_integer_is_not_a_clause_reference(self):
        self.assertEqual(extract_clause_references("up to 8 units"), ())

    def test_known_reference_resolves(self):
        self.assertEqual(unresolved_references(("5.3.1",), INDEX), ())

    def test_unknown_reference_is_reported(self):
        self.assertEqual(unresolved_references(("9.9.9",), INDEX), ("9.9.9",))

    def test_non_collection_index_rejected(self):
        with self.assertRaises(ValueError):
            unresolved_references(("5.3.1",), 5)


class DuplicationTests(unittest.TestCase):
    def test_stopwords_are_dropped(self):
        self.assertNotIn("the", informative_token_set("the unit"))

    def test_disjoint_note_duplicates_nothing(self):
        self.assertAlmostEqual(duplication_share("gamma delta", ["alpha beta"]), 0.0, places=9)

    def test_fully_repeated_note_duplicates_everything(self):
        self.assertAlmostEqual(duplication_share("alpha beta", ["alpha beta"]), 1.0, places=9)

    def test_note_on_the_ceiling_lands_exactly_on_it(self):
        share = duplication_share("alpha beta gamma delta", ["alpha beta"])
        self.assertAlmostEqual(share, DUPLICATION_CEILING, places=9)

    def test_empty_note_has_no_share(self):
        self.assertAlmostEqual(duplication_share("the", ["alpha"]), 0.0, places=9)

    def test_null_upstream_subclause_is_skipped(self):
        self.assertAlmostEqual(duplication_share("alpha beta", [None, "alpha beta"]), 1.0, places=9)

    def test_non_text_upstream_rejected(self):
        with self.assertRaises(ValueError):
            duplication_share("alpha", [7])

    def test_non_sequence_upstream_rejected(self):
        with self.assertRaises(ValueError):
            duplication_share("alpha", "alpha")


class SingleRecordTests(unittest.TestCase):
    def test_good_note_is_compliant(self):
        result = assess_additional_comments(record(), INDEX)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_absent_subclause_is_a_finding(self):
        result = assess_additional_comments(record(additional_comments=None), INDEX)
        self.assertFalse(result["present"])
        self.assertEqual(len(result["findings"]), 1)

    def test_whitespace_only_note_is_the_same_defect(self):
        result = assess_additional_comments(record(additional_comments="   "), INDEX)
        self.assertFalse(result["present"])

    def test_explicit_empty_note_is_compliant(self):
        result = assess_additional_comments(record(additional_comments="None."), INDEX)
        self.assertTrue(result["explicit_empty"])
        self.assertTrue(result["compliant"])

    def test_normative_wording_is_a_finding(self):
        result = assess_additional_comments(
            record(additional_comments="The provider shall retry once before reporting."), INDEX
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("normative wording" in f for f in result["findings"]))

    def test_unresolved_reference_is_a_finding(self):
        result = assess_additional_comments(
            record(additional_comments="Queueing detail is covered by 9.9.9 of this document."),
            INDEX,
        )
        self.assertTrue(any("clause index" in f for f in result["findings"]))

    def test_note_exactly_on_the_ceiling_is_compliant(self):
        result = assess_additional_comments(
            {
                "primitive": "T-Data.request",
                "function": "alpha beta",
                "additional_comments": "alpha beta gamma delta",
            },
            INDEX,
        )
        self.assertAlmostEqual(result["duplication_share"], DUPLICATION_CEILING, places=9)
        self.assertTrue(result["compliant"])

    def test_note_above_the_ceiling_is_a_finding(self):
        result = assess_additional_comments(
            {
                "primitive": "T-Data.request",
                "function": "alpha beta",
                "additional_comments": "alpha beta gamma",
            },
            INDEX,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("informative tokens" in f for f in result["findings"]))

    def test_over_budget_note_is_a_finding(self):
        long_note = " ".join("token%d" % i for i in range(WORD_BUDGET + 1))
        result = assess_additional_comments(
            {"primitive": "T-Data.request", "additional_comments": long_note}, INDEX
        )
        self.assertTrue(any("budget" in f for f in result["findings"]))

    def test_note_at_the_budget_is_not_flagged_for_length(self):
        exact = " ".join("token%d" % i for i in range(WORD_BUDGET))
        result = assess_additional_comments(
            {"primitive": "T-Data.request", "additional_comments": exact}, INDEX
        )
        self.assertEqual(result["word_count"], WORD_BUDGET)
        self.assertFalse(any("budget" in f for f in result["findings"]))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_additional_comments(["T-Data.request"], INDEX)

    def test_record_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_additional_comments({"additional_comments": GOOD_NOTE}, INDEX)

    def test_non_text_note_rejected(self):
        with self.assertRaises(ValueError):
            assess_additional_comments(record(additional_comments=7), INDEX)


class CommentSetTests(unittest.TestCase):
    def _records(self):
        return [
            record(),
            record(primitive="T-Data.indication", additional_comments="No additional comments"),
        ]

    def test_clean_set_is_compliant(self):
        result = assess_comment_set(self._records(), INDEX)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["compliant_count"], 2)

    def test_explicit_empties_are_counted(self):
        self.assertEqual(assess_comment_set(self._records(), INDEX)["explicit_empty_count"], 1)

    def test_total_counts_every_primitive(self):
        self.assertEqual(assess_comment_set(self._records(), INDEX)["total"], 2)

    def test_absent_note_lowers_the_compliant_count(self):
        records = self._records()
        records[1]["additional_comments"] = None
        result = assess_comment_set(records, INDEX)
        self.assertEqual(result["compliant_count"], 1)
        self.assertFalse(result["compliant"])

    def test_duplicate_primitive_name_rejected(self):
        records = self._records()
        records[1]["primitive"] = "t-data.request"
        with self.assertRaises(ValueError):
            assess_comment_set(records, INDEX)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_comment_set([], INDEX)

    def test_non_sequence_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_comment_set(record(), INDEX)


if __name__ == "__main__":
    unittest.main()
