"""Contract tests for the clause 5.2.2.1 function-subclause audit."""

import unittest

from e5053_function_logic import (
    MAX_SENTENCES,
    MIN_INFORMATIVE_TOKENS,
    action_terms,
    assess_function_clause,
    assess_primitive_set,
    detect_leakage,
    find_normative_wording,
    informative_tokens,
    is_restatement,
    normalize_statement,
    primitive_name_tokens,
    sentence_count,
    tokenize,
)

GOOD = "Requests the transfer of an application data unit to the peer protocol entity."
ECHO = "Data request primitive."


class NormalizeTests(unittest.TestCase):
    def test_collapses_internal_whitespace(self):
        self.assertEqual(normalize_statement("  a   b \n c "), "a b c")

    def test_non_text_statement_rejected(self):
        with self.assertRaises(ValueError):
            normalize_statement(42)

    def test_none_statement_rejected(self):
        with self.assertRaises(ValueError):
            normalize_statement(None)


class TokenTests(unittest.TestCase):
    def test_tokenize_is_lowercase_words(self):
        self.assertEqual(tokenize("T-Data.request"), ["t", "data", "request"])

    def test_name_tokens_split_the_dotted_suffix(self):
        self.assertIn("request", primitive_name_tokens("T-Data.request"))

    def test_empty_primitive_name_rejected(self):
        with self.assertRaises(ValueError):
            primitive_name_tokens("   ")

    def test_non_text_primitive_name_rejected(self):
        with self.assertRaises(ValueError):
            primitive_name_tokens(["T-Data.request"])


class InformativeContentTests(unittest.TestCase):
    def test_name_tokens_are_subtracted(self):
        tokens = informative_tokens("T-Data.request", GOOD)
        self.assertNotIn("data", tokens)
        self.assertIn("transfer", tokens)

    def test_stopwords_are_subtracted(self):
        self.assertNotIn("the", informative_tokens("T-Data.request", GOOD))

    def test_repeated_tokens_counted_once(self):
        tokens = informative_tokens("X-Ping.request", "Conveys a probe, a probe and a probe.")
        self.assertEqual(tokens.count("probe"), 1)

    def test_echo_of_the_name_is_a_restatement(self):
        self.assertTrue(is_restatement("T-Data.request", ECHO))

    def test_informative_statement_is_not_a_restatement(self):
        self.assertFalse(is_restatement("T-Data.request", GOOD))

    def test_restatement_floor_is_the_declared_constant(self):
        statement = "Conveys alpha beta"
        self.assertEqual(len(informative_tokens("T-Data.request", statement)), MIN_INFORMATIVE_TOKENS)
        self.assertFalse(is_restatement("T-Data.request", statement))


class SentenceAndWordingTests(unittest.TestCase):
    def test_single_sentence(self):
        self.assertEqual(sentence_count(GOOD), 1)

    def test_three_sentences_counted(self):
        self.assertEqual(sentence_count("One. Two. Three."), 3)

    def test_empty_statement_has_no_sentences(self):
        self.assertEqual(sentence_count("   "), 0)

    def test_normative_marker_found(self):
        self.assertIn("shall", find_normative_wording("The entity shall convey the unit."))

    def test_informative_statement_has_no_normative_marker(self):
        self.assertEqual(find_normative_wording(GOOD), ())

    def test_action_terms_are_reported(self):
        self.assertIn("transfer", action_terms(GOOD))

    def test_action_term_matches_a_regular_inflection(self):
        self.assertIn("deliver", action_terms("Delivers the received unit."))

    def test_action_term_does_not_match_an_unrelated_longer_word(self):
        self.assertNotIn("report", action_terms("Reportability of the unit is out of scope."))


class LeakageTests(unittest.TestCase):
    def test_parameter_detail_is_grouped_under_semantics(self):
        grouped = detect_leakage("Conveys a unit and carries the length parameter as two octets.")
        self.assertIn("semantics", grouped)

    def test_timing_detail_is_grouped_under_when_generated(self):
        grouped = detect_leakage("Conveys a unit and is issued when the retry timer expires.")
        self.assertIn("when generated", grouped)

    def test_receipt_detail_is_grouped_under_effect_on_receipt(self):
        grouped = detect_leakage("Conveys a unit; on receipt the peer enters the open condition.")
        self.assertIn("effect on receipt", grouped)

    def test_clean_statement_leaks_nothing(self):
        self.assertEqual(detect_leakage(GOOD), {})


class SingleClauseAssessmentTests(unittest.TestCase):
    def test_good_statement_is_compliant(self):
        result = assess_function_clause({"primitive": "T-Data.request", "function": GOOD})
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_missing_subclause_is_reported_absent(self):
        result = assess_function_clause({"primitive": "T-Data.request"})
        self.assertFalse(result["present"])
        self.assertEqual(len(result["findings"]), 1)

    def test_null_subclause_is_the_same_defect_as_missing(self):
        result = assess_function_clause({"primitive": "T-Data.request", "function": None})
        self.assertFalse(result["present"])

    def test_whitespace_only_subclause_is_the_same_defect(self):
        result = assess_function_clause({"primitive": "T-Data.request", "function": "   "})
        self.assertFalse(result["present"])

    def test_name_echo_is_flagged(self):
        result = assess_function_clause({"primitive": "T-Data.request", "function": ECHO})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("restates" in f for f in result["findings"]))

    def test_leakage_finding_names_the_owning_subclause(self):
        result = assess_function_clause(
            {
                "primitive": "T-Data.request",
                "function": "Conveys an application unit and carries the length parameter.",
            }
        )
        self.assertTrue(any("semantics" in f for f in result["findings"]))

    def test_over_budget_statement_is_flagged(self):
        long_statement = " ".join([GOOD] * (MAX_SENTENCES + 1))
        result = assess_function_clause({"primitive": "T-Data.request", "function": long_statement})
        self.assertTrue(any("sentences" in f for f in result["findings"]))

    def test_statement_without_a_service_action_is_flagged(self):
        result = assess_function_clause(
            {"primitive": "T-Data.request", "function": "Covers the application unit exchange path."}
        )
        self.assertTrue(any("service action" in f for f in result["findings"]))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_function_clause(["T-Data.request"])

    def test_record_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_function_clause({"function": GOOD})

    def test_non_text_subclause_rejected(self):
        with self.assertRaises(ValueError):
            assess_function_clause({"primitive": "T-Data.request", "function": 7})


class PrimitiveSetTests(unittest.TestCase):
    def _records(self):
        return [
            {"primitive": "T-Data.request", "function": GOOD},
            {
                "primitive": "T-Data.indication",
                "function": "Delivers a received application unit to the local user entity.",
            },
        ]

    def test_clean_set_is_compliant(self):
        result = assess_primitive_set(self._records())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["compliant_count"], 2)

    def test_total_counts_every_primitive(self):
        self.assertEqual(assess_primitive_set(self._records())["total"], 2)

    def test_shared_statement_is_a_set_level_finding(self):
        records = self._records()
        records[1]["function"] = GOOD
        result = assess_primitive_set(records)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["shared_statements"]), 1)

    def test_shared_statement_marks_both_owners_non_compliant(self):
        records = self._records()
        records[1]["function"] = GOOD.upper()
        result = assess_primitive_set(records)
        self.assertEqual(result["compliant_count"], 0)

    def test_duplicate_primitive_name_rejected(self):
        records = self._records()
        records[1]["primitive"] = "t-data.request"
        with self.assertRaises(ValueError):
            assess_primitive_set(records)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_primitive_set([])

    def test_non_sequence_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_primitive_set({"primitive": "T-Data.request"})

    def test_absent_subclause_lowers_the_compliant_count(self):
        records = self._records()
        del records[1]["function"]
        result = assess_primitive_set(records)
        self.assertEqual(result["compliant_count"], 1)
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()
