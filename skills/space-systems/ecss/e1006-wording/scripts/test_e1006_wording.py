"""
test_e1006_wording.py
stdlib unittest for e1006_wording_logic.py — ECSS-E-ST-10C §8.3 wording rules.
Run: python3 test_e1006_wording.py
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from e1006_wording_logic import (
    detect_verbal_form,
    count_obligations,
    check_forbidden_terms,
    check_embedded_rationale,
    audit_requirement,
    FORBIDDEN_TERMS,
    RATIONALE_MARKERS,
)


class TestVerbalFormDetection(unittest.TestCase):

    def test_shall_categorized_as_mandatory(self):
        result = detect_verbal_form("The system shall provide telemetry at 1 Hz.")
        self.assertEqual(result["form"], "shall")
        self.assertEqual(result["category"], "mandatory")
        self.assertTrue(result["compliant"])

    def test_should_categorized_as_recommendation(self):
        result = detect_verbal_form("The system should log all errors to persistent storage.")
        self.assertEqual(result["form"], "should")
        self.assertEqual(result["category"], "recommendation")
        self.assertTrue(result["compliant"])

    def test_may_categorized_as_permission(self):
        result = detect_verbal_form("The operator may override the default safe-hold mode.")
        self.assertEqual(result["form"], "may")
        self.assertEqual(result["category"], "permission")
        self.assertTrue(result["compliant"])

    def test_will_non_standard_not_compliant(self):
        result = detect_verbal_form("The system will transmit data at 10 Mbps.")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["category"], "non-standard")
        self.assertEqual(result["form"], "will")

    def test_must_non_standard_not_compliant(self):
        result = detect_verbal_form("The module must complete boot sequence within 5 s.")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["category"], "non-standard")
        self.assertEqual(result["form"], "must")

    def test_is_required_to_non_standard_not_compliant(self):
        result = detect_verbal_form("The unit is required to maintain voltage above 24 V.")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["category"], "non-standard")

    def test_no_verbal_form_categorized_as_missing(self):
        result = detect_verbal_form("The system transmits data at 10 Mbps.")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["category"], "missing")
        self.assertIsNone(result["form"])

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            detect_verbal_form(42)


class TestObligationCount(unittest.TestCase):

    def test_single_shall_returns_one(self):
        self.assertEqual(
            count_obligations("The unit shall power on within 3 s."), 1
        )

    def test_compound_shall_returns_two(self):
        self.assertEqual(
            count_obligations(
                "The unit shall boot within 3 s and shall reach operational mode within 10 s."
            ),
            2,
        )

    def test_triple_shall_returns_three(self):
        self.assertEqual(
            count_obligations(
                "The system shall boot, shall self-test, and shall transmit a heartbeat."
            ),
            3,
        )

    def test_no_shall_returns_zero(self):
        self.assertEqual(count_obligations("The unit may reboot at any time."), 0)

    def test_case_insensitive_count(self):
        self.assertEqual(count_obligations("The unit SHALL respond within 1 s."), 1)

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            count_obligations(None)


class TestForbiddenTerms(unittest.TestCase):

    def test_adequate_flagged(self):
        found = check_forbidden_terms("The margin shall be adequate for the mission.")
        self.assertIn("adequate", found)

    def test_appropriate_flagged(self):
        found = check_forbidden_terms("The system shall use appropriate interfaces.")
        self.assertIn("appropriate", found)

    def test_etc_flagged(self):
        found = check_forbidden_terms(
            "The system shall handle data, commands, telemetry, etc."
        )
        self.assertIn("etc.", found)

    def test_user_friendly_flagged(self):
        found = check_forbidden_terms("The interface shall be user-friendly.")
        self.assertIn("user-friendly", found)

    def test_and_or_flagged(self):
        found = check_forbidden_terms("The system shall store and/or forward packets.")
        self.assertIn("and/or", found)

    def test_sufficient_flagged(self):
        found = check_forbidden_terms("The buffer shall have sufficient capacity.")
        self.assertIn("sufficient", found)

    def test_clean_text_returns_empty(self):
        found = check_forbidden_terms(
            "The system shall maintain supply voltage above 27.0 V under all operating modes."
        )
        self.assertEqual(found, [])

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_forbidden_terms(123)


class TestEmbeddedRationale(unittest.TestCase):

    def test_in_order_to_flagged(self):
        text = "The system shall cache telemetry in order to reduce downlink latency."
        found = check_embedded_rationale(text)
        self.assertIn("in order to", found)

    def test_because_flagged(self):
        text = "The system shall use AES-256 because it meets the mission security policy."
        found = check_embedded_rationale(text)
        self.assertIn("because", found)

    def test_so_that_flagged(self):
        text = "The unit shall enter safe mode so that power consumption is reduced."
        found = check_embedded_rationale(text)
        self.assertIn("so that", found)

    def test_clean_requirement_no_rationale(self):
        text = "The system shall encrypt all stored payload data with AES-256."
        found = check_embedded_rationale(text)
        self.assertEqual(found, [])

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_embedded_rationale(None)


class TestAuditRequirement(unittest.TestCase):

    def test_clean_requirement_is_compliant(self):
        result = audit_requirement(
            "The payload shall transmit telemetry at 1 Hz ± 0.01 Hz."
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_compound_requirement_not_compliant(self):
        result = audit_requirement(
            "The system shall boot within 3 s and shall reach operational mode within 10 s."
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Compound" in f for f in result["findings"]))

    def test_forbidden_term_makes_not_compliant(self):
        result = audit_requirement(
            "The interface shall provide adequate bandwidth for all operating modes."
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("adequate" in f for f in result["findings"]))

    def test_rationale_makes_not_compliant(self):
        result = audit_requirement(
            "The system shall cache data in order to reduce ground-station load."
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("in order to" in f for f in result["findings"]))

    def test_non_standard_form_makes_not_compliant(self):
        result = audit_requirement("The system will provide 100 W of regulated power.")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("will" in f for f in result["findings"]))

    def test_multiple_findings_accumulated(self):
        text = (
            "The system shall provide adequate and user-friendly telemetry display "
            "in order to satisfy mission operators."
        )
        result = audit_requirement(text)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 1)

    def test_empty_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            audit_requirement("")

    def test_whitespace_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            audit_requirement("   ")

    def test_audit_result_keys_present(self):
        result = audit_requirement("The system shall operate at nominal voltage.")
        for key in ("verbal_form", "obligation_count", "forbidden_terms",
                    "rationale_markers", "compliant", "findings"):
            self.assertIn(key, result)

    def test_should_form_is_compliant_with_no_other_violations(self):
        result = audit_requirement(
            "The system should log telemetry errors to persistent storage."
        )
        self.assertTrue(result["compliant"])

    def test_may_form_is_compliant_with_no_other_violations(self):
        result = audit_requirement(
            "The ground operator may initiate an emergency shutdown at any time."
        )
        self.assertTrue(result["compliant"])


class TestDataIntegrity(unittest.TestCase):

    def test_forbidden_terms_list_non_empty(self):
        self.assertGreater(len(FORBIDDEN_TERMS), 0)

    def test_rationale_markers_list_non_empty(self):
        self.assertGreater(len(RATIONALE_MARKERS), 0)

    def test_forbidden_terms_are_lowercase(self):
        for term in FORBIDDEN_TERMS:
            self.assertEqual(term, term.lower(), f"Term not lowercase: {term}")

    def test_rationale_markers_are_lowercase(self):
        for marker in RATIONALE_MARKERS:
            self.assertEqual(marker, marker.lower(), f"Marker not lowercase: {marker}")


if __name__ == "__main__":
    unittest.main()
