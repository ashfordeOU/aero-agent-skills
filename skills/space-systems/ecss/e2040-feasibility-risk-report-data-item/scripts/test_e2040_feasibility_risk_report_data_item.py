"""Contract tests for the Annex F feasibility and risk report data-item logic."""

import unittest

from e2040_feasibility_risk_report_data_item_logic import (
    CONFIDENCE_TOLERANCE,
    DEFAULT_BANDS,
    REQUIRED_SECTIONS,
    assess_feasibility_risk_report,
    band_of,
    close_question,
    grade_risk,
    grade_risks,
    missing_sections,
    residual_band_counts,
    risk_magnitude,
    validate_bands,
    validate_question,
    validate_questions,
    validate_risk,
    validate_scale_index,
    weighted_feasibility_confidence,
)

ALL_SECTIONS = list(REQUIRED_SECTIONS)
ACCEPTED = ["low", "medium"]


def risk(identifier="R-1", severity=4, likelihood=3, res_s=None, res_p=None, mitigation="M-1"):
    entry = {"id": identifier, "severity": severity, "likelihood": likelihood}
    if res_s is not None:
        entry["residual_severity"] = res_s
    if res_p is not None:
        entry["residual_likelihood"] = res_p
    if mitigation is not None:
        entry["mitigation"] = mitigation
    return entry


def question(identifier="Q-1", weight=3.0, evidence="TN-001", links=("R-1",)):
    return {
        "id": identifier,
        "criticality_weight": weight,
        "evidence": evidence,
        "risk_ids": list(links),
    }


class SectionTests(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS), [])

    def test_absent_residual_statement_is_named(self):
        partial = [s for s in ALL_SECTIONS if s != "residual-risk-statement"]
        self.assertEqual(missing_sections(partial), ["residual-risk-statement"])

    def test_section_match_ignores_case(self):
        self.assertEqual(missing_sections([s.upper() for s in ALL_SECTIONS]), [])

    def test_non_sequence_section_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections(42)


class ScaleAndBandTests(unittest.TestCase):
    def test_index_inside_the_scale_accepted(self):
        self.assertEqual(validate_scale_index(3, "severity"), 3)

    def test_index_above_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_scale_index(6, "severity")

    def test_index_below_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_scale_index(0, "likelihood")

    def test_fractional_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_scale_index(3.5, "severity")

    def test_boolean_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_scale_index(True, "severity")

    def test_default_bands_validate(self):
        self.assertEqual(len(validate_bands(DEFAULT_BANDS)), 4)

    def test_non_increasing_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([("low", 9), ("medium", 4), ("high", None)])

    def test_closed_worst_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([("low", 4), ("high", 25)])

    def test_duplicate_band_names_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([("low", 4), ("low", 9), ("high", None)])

    def test_magnitude_is_the_product(self):
        self.assertEqual(risk_magnitude(4, 3), 12)

    def test_band_boundary_belongs_to_the_lower_band(self):
        self.assertEqual(band_of(4), "low")
        self.assertEqual(band_of(5), "medium")

    def test_worst_band_is_open_ended(self):
        self.assertEqual(band_of(25), "unacceptable")

    def test_product_separates_what_an_average_would_collapse(self):
        rare_catastrophe = risk_magnitude(5, 1)
        middling = risk_magnitude(3, 3)
        self.assertAlmostEqual((5 + 1) / 2.0, (3 + 3) / 2.0, places=9)
        self.assertNotEqual(rare_catastrophe, middling)


class RiskGradingTests(unittest.TestCase):
    def test_residual_defaults_to_the_initial_scores(self):
        record = validate_risk({"id": "R-1", "severity": 4, "likelihood": 3})
        self.assertEqual(record["residual_severity"], 4)
        self.assertEqual(record["residual_likelihood"], 3)

    def test_mitigation_reduction_is_the_magnitude_difference(self):
        record = grade_risk(risk(res_p=1))
        self.assertEqual(record["initial_magnitude"], 12)
        self.assertEqual(record["residual_magnitude"], 4)
        self.assertEqual(record["reduction"], 8)

    def test_mitigation_moving_a_band_is_credited(self):
        record = grade_risk(risk(res_p=1))
        self.assertEqual(record["initial_band"], "high")
        self.assertEqual(record["residual_band"], "low")
        self.assertTrue(record["mitigation_credited"])

    def test_mitigation_moving_no_index_is_empty(self):
        record = grade_risk(risk())
        self.assertTrue(record["empty_mitigation"])
        self.assertEqual(record["reduction"], 0)

    def test_residual_worse_than_initial_is_inconsistent(self):
        record = grade_risk(risk(severity=2, likelihood=2, res_s=4, res_p=4))
        self.assertTrue(record["inconsistent"])

    def test_risk_without_mitigation_is_not_an_empty_mitigation(self):
        record = grade_risk(risk(mitigation=None))
        self.assertFalse(record["empty_mitigation"])

    def test_duplicate_risk_identifier_rejected(self):
        with self.assertRaises(ValueError):
            grade_risks([risk("R-1"), risk("R-1")])

    def test_residual_band_counts_cover_every_band(self):
        counts = residual_band_counts(grade_risks([risk("R-1", res_p=1), risk("R-2")]))
        self.assertEqual(counts["low"], 1)
        self.assertEqual(counts["high"], 1)
        self.assertEqual(counts["unacceptable"], 0)


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.graded = grade_risks([risk("R-1", res_p=1), risk("R-2", severity=5, likelihood=5)])
        self.by_id = dict((r["id"], r) for r in self.graded)

    def test_links_are_deduplicated(self):
        record = validate_question(question(links=("R-1", "R-1")), set(self.by_id))
        self.assertEqual(record["risk_ids"], ["R-1"])

    def test_link_to_an_unregistered_risk_rejected(self):
        with self.assertRaises(ValueError):
            validate_question(question(links=("R-404",)), set(self.by_id))

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_question(question(weight=0.0), set(self.by_id))

    def test_duplicate_question_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_questions([question("Q-1"), question("Q-1")], set(self.by_id))

    def test_evidence_and_accepted_residual_closes_the_question(self):
        record = close_question(
            validate_question(question(), set(self.by_id)), self.by_id, ACCEPTED
        )
        self.assertTrue(record["closed"])
        self.assertEqual(record["open_reasons"], [])

    def test_missing_evidence_keeps_the_question_open(self):
        record = close_question(
            validate_question(question(evidence=None), set(self.by_id)), self.by_id, ACCEPTED
        )
        self.assertFalse(record["closed"])
        self.assertIn("no evidence reference", record["open_reasons"])

    def test_evidence_does_not_close_over_an_unacceptable_residual(self):
        record = close_question(
            validate_question(question(links=("R-2",)), set(self.by_id)), self.by_id, ACCEPTED
        )
        self.assertFalse(record["closed"])
        self.assertEqual(record["blocking_risk_ids"], ["R-2"])

    def test_empty_accepted_band_list_rejected(self):
        with self.assertRaises(ValueError):
            close_question(
                validate_question(question(), set(self.by_id)), self.by_id, []
            )

    def test_confidence_is_weighted_not_counted(self):
        records = [
            {"id": "Q-1", "criticality_weight": 9.0, "closed": False},
            {"id": "Q-2", "criticality_weight": 1.0, "closed": True},
        ]
        self.assertAlmostEqual(weighted_feasibility_confidence(records), 0.1, places=9)

    def test_confidence_of_a_fully_closed_set_is_one(self):
        records = [{"id": "Q-1", "criticality_weight": 2.0, "closed": True}]
        self.assertAlmostEqual(weighted_feasibility_confidence(records), 1.0, places=9)

    def test_empty_question_set_rejected(self):
        with self.assertRaises(ValueError):
            weighted_feasibility_confidence([])


class AssessmentTests(unittest.TestCase):
    def _report(self, **overrides):
        report = {
            "sections": list(ALL_SECTIONS),
            "risks": [risk("R-1", res_p=1)],
            "questions": [question("Q-1")],
            "accepted_bands": list(ACCEPTED),
            "required_confidence": 1.0,
        }
        report.update(overrides)
        return report

    def test_complete_report_is_compliant(self):
        result = assess_feasibility_risk_report(self._report())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["feasibility_confidence"], 1.0, places=9)

    def test_open_question_is_a_finding(self):
        result = assess_feasibility_risk_report(
            self._report(
                risks=[risk("R-1", severity=5, likelihood=5, mitigation=None)],
                required_confidence=0.0,
            )
        )
        self.assertEqual(result["open_questions"], ["Q-1"])
        self.assertFalse(result["compliant"])

    def test_empty_mitigation_is_a_finding(self):
        result = assess_feasibility_risk_report(
            self._report(
                risks=[risk("R-1", severity=2, likelihood=2)],
                questions=[question("Q-1")],
            )
        )
        self.assertTrue(any("neither index" in f for f in result["findings"]))

    def test_inconsistent_residual_is_a_finding(self):
        result = assess_feasibility_risk_report(
            self._report(risks=[risk("R-1", severity=2, likelihood=2, res_s=4, res_p=4)])
        )
        self.assertTrue(any("above its initial" in f for f in result["findings"]))

    def test_confidence_exactly_at_the_required_level_is_met(self):
        result = assess_feasibility_risk_report(
            self._report(
                risks=[risk("R-1", res_p=1), risk("R-2", severity=5, likelihood=5, mitigation=None)],
                questions=[question("Q-1", 1.0, "TN-001", ("R-1",)),
                           question("Q-2", 1.0, "TN-002", ("R-2",))],
                required_confidence=0.5,
            )
        )
        self.assertTrue(result["confidence_met"])
        self.assertLessEqual(
            abs(result["feasibility_confidence"] - result["required_confidence"]),
            CONFIDENCE_TOLERANCE,
        )

    def test_confidence_below_the_required_level_is_a_finding(self):
        result = assess_feasibility_risk_report(
            self._report(
                risks=[risk("R-1", severity=5, likelihood=5, mitigation=None)],
                required_confidence=0.9,
            )
        )
        self.assertFalse(result["confidence_met"])
        self.assertTrue(any("below the required" in f for f in result["findings"]))

    def test_absent_section_is_a_finding(self):
        sections = [s for s in ALL_SECTIONS if s != "risk-register"]
        result = assess_feasibility_risk_report(self._report(sections=sections))
        self.assertEqual(result["missing_sections"], ["risk-register"])

    def test_required_confidence_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_feasibility_risk_report(self._report(required_confidence=1.5))

    def test_missing_report_key_rejected(self):
        report = self._report()
        del report["risks"]
        with self.assertRaises(ValueError):
            assess_feasibility_risk_report(report)

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            assess_feasibility_risk_report(["sections"])


if __name__ == "__main__":
    unittest.main()
