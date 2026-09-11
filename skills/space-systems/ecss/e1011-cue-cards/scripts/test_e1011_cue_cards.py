"""
Gate 3 contract tests — e1011-cue-cards.
Run: python3 test_e1011_cue_cards.py
Stdlib unittest only; deterministic; offline.
"""

import unittest
import sys
import os

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(__file__))

from e1011_cue_cards_logic import (
    audit_card,
    categorize_card,
    check_action_verb,
    check_card_set_coverage,
    check_step_count,
    check_step_length,
    compute_card_metrics,
    validate_card_structure,
    validate_severity,
    CueCardError,
    MAX_STEPS_PER_FACE,
    MAX_STEP_CHARS,
    SEVERITY_LEVELS,
    SCENARIO_TYPES,
)


# ---------------------------------------------------------------------------
# validate_card_structure
# ---------------------------------------------------------------------------

class TestValidateCardStructure(unittest.TestCase):

    def test_complete_card_returns_no_findings(self):
        card = {
            "title": "Depressurization Response",
            "scenario_type": "emergency",
            "severity": "CRITICAL",
            "steps": ["Close hatch immediately."],
        }
        self.assertEqual(validate_card_structure(card), [])

    def test_empty_dict_returns_four_findings(self):
        findings = validate_card_structure({})
        self.assertEqual(len(findings), 4)

    def test_missing_steps_field_reported(self):
        card = {"title": "T", "scenario_type": "emergency", "severity": "HIGH"}
        findings = validate_card_structure(card)
        self.assertIn("missing required field: 'steps'", findings)

    def test_missing_title_field_reported(self):
        card = {"scenario_type": "contingency", "severity": "MEDIUM", "steps": []}
        findings = validate_card_structure(card)
        self.assertIn("missing required field: 'title'", findings)


# ---------------------------------------------------------------------------
# check_step_count
# ---------------------------------------------------------------------------

class TestCheckStepCount(unittest.TestCase):

    def test_within_limit_passes(self):
        self.assertEqual(check_step_count(["step"] * 5), [])

    def test_exactly_at_limit_passes(self):
        self.assertEqual(check_step_count(["step"] * MAX_STEPS_PER_FACE), [])

    def test_one_over_limit_returns_finding(self):
        findings = check_step_count(["step"] * (MAX_STEPS_PER_FACE + 1))
        self.assertTrue(any("exceeds maximum" in f for f in findings))

    def test_empty_list_returns_finding(self):
        findings = check_step_count([])
        self.assertTrue(any("at least one step" in f for f in findings))

    def test_non_list_returns_finding(self):
        findings = check_step_count("not a list")
        self.assertTrue(any("must be a list" in f for f in findings))

    def test_custom_max_respected(self):
        findings = check_step_count(["step"] * 5, max_steps=4)
        self.assertTrue(any("exceeds maximum" in f for f in findings))


# ---------------------------------------------------------------------------
# check_step_length
# ---------------------------------------------------------------------------

class TestCheckStepLength(unittest.TestCase):

    def test_short_step_passes(self):
        self.assertEqual(check_step_length("Close valve A."), [])

    def test_exactly_at_limit_passes(self):
        self.assertEqual(check_step_length("x" * MAX_STEP_CHARS), [])

    def test_one_over_limit_returns_finding(self):
        findings = check_step_length("x" * (MAX_STEP_CHARS + 1))
        self.assertTrue(any("exceeds maximum" in f for f in findings))

    def test_blank_step_returns_finding(self):
        findings = check_step_length("   ")
        self.assertTrue(any("must not be blank" in f for f in findings))

    def test_non_string_returns_finding(self):
        findings = check_step_length(42)
        self.assertTrue(any("must be a string" in f for f in findings))


# ---------------------------------------------------------------------------
# check_action_verb
# ---------------------------------------------------------------------------

class TestCheckActionVerb(unittest.TestCase):

    def test_recognized_verb_passes(self):
        self.assertEqual(check_action_verb("Close valve immediately."), [])

    def test_another_recognized_verb_passes(self):
        self.assertEqual(check_action_verb("Report status to ground."), [])

    def test_unrecognized_first_word_returns_finding(self):
        findings = check_action_verb("Carefully inspect the panel.")
        self.assertTrue(any("does not begin with" in f for f in findings))

    def test_empty_step_returns_finding(self):
        findings = check_action_verb("")
        self.assertTrue(len(findings) > 0)

    def test_custom_verb_set_honored(self):
        findings = check_action_verb("Engage thrusters.", action_verbs={"engage"})
        self.assertEqual(findings, [])

    def test_verb_trailing_punctuation_stripped(self):
        # "Close," should still match "close" after stripping punctuation
        self.assertEqual(check_action_verb("Close, then lock hatch."), [])


# ---------------------------------------------------------------------------
# categorize_card
# ---------------------------------------------------------------------------

class TestCategorizeCard(unittest.TestCase):

    def test_emergency_card_returns_emergency(self):
        card = {"scenario_type": "emergency"}
        self.assertEqual(categorize_card(card), "emergency")

    def test_contingency_card_returns_contingency(self):
        card = {"scenario_type": "contingency"}
        self.assertEqual(categorize_card(card), "contingency")

    def test_uppercase_type_raises(self):
        card = {"scenario_type": "EMERGENCY"}
        with self.assertRaises(CueCardError):
            categorize_card(card)

    def test_unknown_type_raises(self):
        card = {"scenario_type": "routine"}
        with self.assertRaises(CueCardError):
            categorize_card(card)

    def test_missing_type_raises(self):
        with self.assertRaises(CueCardError):
            categorize_card({})


# ---------------------------------------------------------------------------
# validate_severity
# ---------------------------------------------------------------------------

class TestValidateSeverity(unittest.TestCase):

    def test_critical_severity_passes(self):
        self.assertEqual(validate_severity({"severity": "CRITICAL"}), [])

    def test_high_severity_passes(self):
        self.assertEqual(validate_severity({"severity": "HIGH"}), [])

    def test_medium_severity_passes(self):
        self.assertEqual(validate_severity({"severity": "MEDIUM"}), [])

    def test_low_severity_returns_finding(self):
        findings = validate_severity({"severity": "LOW"})
        self.assertTrue(any("unrecognized severity" in f for f in findings))

    def test_missing_severity_returns_finding(self):
        findings = validate_severity({})
        self.assertTrue(any("missing or empty" in f for f in findings))

    def test_empty_string_severity_returns_finding(self):
        findings = validate_severity({"severity": ""})
        self.assertTrue(any("missing or empty" in f for f in findings))


# ---------------------------------------------------------------------------
# audit_card
# ---------------------------------------------------------------------------

class TestAuditCard(unittest.TestCase):

    def _make_valid_card(self):
        return {
            "title": "Smoke Detection Response",
            "scenario_type": "emergency",
            "severity": "CRITICAL",
            "steps": [
                "Report smoke location to ground control.",
                "Activate fire suppression system.",
                "Seal off the affected module.",
                "Monitor air quality readings.",
            ],
        }

    def test_valid_card_passes(self):
        result = audit_card(self._make_valid_card())
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_empty_card_fails(self):
        result = audit_card({})
        self.assertFalse(result["passed"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_title_in_result(self):
        result = audit_card(self._make_valid_card())
        self.assertEqual(result["title"], "Smoke Detection Response")

    def test_no_title_returns_placeholder(self):
        result = audit_card({})
        self.assertEqual(result["title"], "<no title>")

    def test_too_many_steps_fails(self):
        card = self._make_valid_card()
        card["steps"] = [f"Check panel {i}." for i in range(MAX_STEPS_PER_FACE + 2)]
        result = audit_card(card)
        self.assertFalse(result["passed"])

    def test_overlong_step_fails(self):
        card = self._make_valid_card()
        card["steps"] = ["Close " + "x" * MAX_STEP_CHARS + "."]
        result = audit_card(card)
        self.assertFalse(result["passed"])

    def test_bad_verb_step_fails(self):
        card = self._make_valid_card()
        card["steps"] = ["The hatch must be closed immediately."]
        result = audit_card(card)
        self.assertFalse(result["passed"])

    def test_invalid_scenario_type_fails(self):
        card = self._make_valid_card()
        card["scenario_type"] = "routine"
        result = audit_card(card)
        self.assertFalse(result["passed"])


# ---------------------------------------------------------------------------
# check_card_set_coverage
# ---------------------------------------------------------------------------

class TestCheckCardSetCoverage(unittest.TestCase):

    def test_full_coverage_returns_no_findings(self):
        cards = [
            {"title": "Fire Response"},
            {"title": "Depressurization"},
        ]
        findings = check_card_set_coverage(
            cards, ["Fire Response", "Depressurization"]
        )
        self.assertEqual(findings, [])

    def test_missing_scenario_returns_finding(self):
        cards = [{"title": "Fire Response"}]
        findings = check_card_set_coverage(
            cards, ["Fire Response", "Depressurization"]
        )
        self.assertTrue(any("Depressurization" in f for f in findings))

    def test_coverage_check_is_case_insensitive(self):
        cards = [{"title": "fire response"}]
        findings = check_card_set_coverage(cards, ["Fire Response"])
        self.assertEqual(findings, [])

    def test_empty_card_set_flags_all_scenarios(self):
        required = ["Fire Response", "Depressurization", "Toxic Release"]
        findings = check_card_set_coverage([], required)
        self.assertEqual(len(findings), len(required))

    def test_empty_required_list_passes(self):
        cards = [{"title": "Fire Response"}]
        findings = check_card_set_coverage(cards, [])
        self.assertEqual(findings, [])


# ---------------------------------------------------------------------------
# compute_card_metrics
# ---------------------------------------------------------------------------

class TestComputeCardMetrics(unittest.TestCase):

    def test_metrics_computed_correctly(self):
        s1, s2 = "Close valve.", "Report status."
        card = {"steps": [s1, s2]}
        metrics = compute_card_metrics(card)
        self.assertEqual(metrics["step_count"], 2)
        self.assertAlmostEqual(
            metrics["avg_step_chars"], (len(s1) + len(s2)) / 2
        )
        self.assertEqual(metrics["max_step_chars"], max(len(s1), len(s2)))

    def test_empty_steps_returns_zeros(self):
        metrics = compute_card_metrics({"steps": []})
        self.assertEqual(metrics["step_count"], 0)
        self.assertEqual(metrics["avg_step_chars"], 0.0)
        self.assertEqual(metrics["max_step_chars"], 0)

    def test_missing_steps_key_returns_zeros(self):
        metrics = compute_card_metrics({"title": "T"})
        self.assertEqual(metrics["step_count"], 0)

    def test_single_step_avg_equals_length(self):
        step = "Activate backup power."
        metrics = compute_card_metrics({"steps": [step]})
        self.assertEqual(metrics["step_count"], 1)
        self.assertAlmostEqual(metrics["avg_step_chars"], len(step))
        self.assertEqual(metrics["max_step_chars"], len(step))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):

    def test_max_steps_per_face_is_nine(self):
        self.assertEqual(MAX_STEPS_PER_FACE, 9)

    def test_max_step_chars_is_eighty(self):
        self.assertEqual(MAX_STEP_CHARS, 80)

    def test_severity_levels_contains_expected_values(self):
        self.assertIn("CRITICAL", SEVERITY_LEVELS)
        self.assertIn("HIGH", SEVERITY_LEVELS)
        self.assertIn("MEDIUM", SEVERITY_LEVELS)

    def test_scenario_types_contains_expected_values(self):
        self.assertIn("emergency", SCENARIO_TYPES)
        self.assertIn("contingency", SCENARIO_TYPES)


if __name__ == "__main__":
    unittest.main()
