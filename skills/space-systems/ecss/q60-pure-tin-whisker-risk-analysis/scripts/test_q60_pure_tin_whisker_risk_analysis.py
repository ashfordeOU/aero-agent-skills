"""Contract tests for the clause 9.2 whisker risk analysis content review."""

import unittest

from q60_pure_tin_whisker_risk_analysis_logic import (
    ACTIONS_SCORE_FLOOR,
    COMPLIANT_SCORE_FLOOR,
    MIN_EVIDENCE_REFS_FOR_SUBSTANTIATION,
    REQUIRED_ITEM_COVERAGE,
    REQUIRED_SECTIONS,
    SCORE_TOLERANCE,
    SECTION_STATES,
    STATE_CREDIT,
    VERDICTS,
    assess_whisker_risk_analysis,
    content_score,
    content_verdict,
    effective_state,
    item_coverage,
    mandatory_sections,
    missing_mandatory_sections,
    normalize_token,
    section_credit,
    total_section_weight,
    validate_section,
    validate_sections,
)


def _full_sections(**overrides):
    """Every required section substantiated, before any override is applied."""
    sections = []
    for token in sorted(REQUIRED_SECTIONS):
        state = overrides.get(token, "substantiated")
        refs = 0 if state == "absent" else 2
        if state == "absent":
            continue
        sections.append(
            {"section": token, "state": state, "evidence_refs": refs}
        )
    return sections


def _analysis(**overrides):
    analysis = {
        "document_id": "CCP-WHISK-014",
        "pure_tin_item_count": 11,
        "items_addressed": 11,
        "sections": _full_sections(),
    }
    analysis.update(overrides)
    return analysis


class TokenTests(unittest.TestCase):
    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(
            normalize_token("Residual_Risk Acceptance_Statement"),
            "residual-risk-acceptance-statement",
        )

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "section")

    def test_non_text_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(17, "section")


class SectionCatalogueTests(unittest.TestCase):
    def test_every_mandatory_section_is_a_required_section(self):
        for token in mandatory_sections():
            self.assertIn(token, REQUIRED_SECTIONS)

    def test_mandatory_sections_are_a_strict_subset(self):
        self.assertLess(len(mandatory_sections()), len(REQUIRED_SECTIONS))

    def test_total_weight_sums_the_catalogue(self):
        self.assertAlmostEqual(
            total_section_weight(),
            sum(v["weight"] for v in REQUIRED_SECTIONS.values()),
            places=9,
        )

    def test_every_state_carries_a_credit(self):
        for state in SECTION_STATES:
            self.assertIn(state, STATE_CREDIT)

    def test_verdict_vocabulary_is_fixed(self):
        self.assertEqual(
            VERDICTS, ("compliant", "compliant-with-actions", "not-compliant")
        )


class EffectiveStateTests(unittest.TestCase):
    def test_substantiated_with_evidence_stays_substantiated(self):
        self.assertEqual(effective_state("substantiated", 3), "substantiated")

    def test_substantiated_on_the_minimum_reference_count_stands(self):
        self.assertEqual(
            effective_state("substantiated", MIN_EVIDENCE_REFS_FOR_SUBSTANTIATION),
            "substantiated",
        )

    def test_substantiated_without_evidence_is_demoted(self):
        self.assertEqual(effective_state("substantiated", 0), "asserted")

    def test_asserted_is_not_promoted_by_evidence(self):
        self.assertEqual(effective_state("asserted", 9), "asserted")

    def test_absent_stays_absent(self):
        self.assertEqual(effective_state("absent", 4), "absent")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            effective_state("partially-drafted", 1)

    def test_negative_evidence_count_rejected(self):
        with self.assertRaises(ValueError):
            effective_state("substantiated", -1)

    def test_non_integer_evidence_count_rejected(self):
        with self.assertRaises(ValueError):
            effective_state("substantiated", 2.5)

    def test_boolean_evidence_count_rejected(self):
        with self.assertRaises(ValueError):
            effective_state("substantiated", True)

    def test_credit_follows_the_effective_state(self):
        self.assertAlmostEqual(section_credit("substantiated", 0), 0.5, places=9)
        self.assertAlmostEqual(section_credit("substantiated", 1), 1.0, places=9)
        self.assertAlmostEqual(section_credit("absent", 0), 0.0, places=9)


class SectionValidationTests(unittest.TestCase):
    def test_validated_section_carries_weight_and_mandatory_flag(self):
        item = validate_section(
            {
                "section": "finish-composition-evidence",
                "state": "substantiated",
                "evidence_refs": 2,
            }
        )
        self.assertAlmostEqual(item["weight"], 3.0, places=9)
        self.assertTrue(item["mandatory"])
        self.assertFalse(item["demoted"])

    def test_demotion_is_reported_on_the_entry(self):
        item = validate_section(
            {"section": "whisker-length-bounding-basis", "state": "substantiated"}
        )
        self.assertTrue(item["demoted"])
        self.assertEqual(item["state"], "asserted")
        self.assertEqual(item["declared_state"], "substantiated")

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_section({"section": "cost-breakdown", "state": "asserted"})

    def test_section_without_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_section({"section": "finish-composition-evidence"})

    def test_non_mapping_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_section(["finish-composition-evidence", "asserted"])

    def test_unsubmitted_sections_come_back_absent(self):
        validated = validate_sections(
            [{"section": "part-and-finish-identification", "state": "asserted"}]
        )
        self.assertEqual(len(validated), len(REQUIRED_SECTIONS))
        self.assertEqual(
            validated["mitigation-selection-and-justification"]["state"], "absent"
        )

    def test_duplicate_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(
                [
                    {"section": "finish-composition-evidence", "state": "asserted"},
                    {
                        "section": "finish-composition-evidence",
                        "state": "substantiated",
                        "evidence_refs": 1,
                    },
                ]
            )

    def test_non_list_sections_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections({"section": "finish-composition-evidence"})


class ItemCoverageTests(unittest.TestCase):
    def test_every_item_addressed_is_full_coverage(self):
        self.assertAlmostEqual(item_coverage(11, 11), REQUIRED_ITEM_COVERAGE, places=9)

    def test_partial_coverage_is_the_fraction(self):
        self.assertAlmostEqual(item_coverage(10, 9), 0.9, places=9)

    def test_no_items_addressed_is_zero_coverage(self):
        self.assertAlmostEqual(item_coverage(4, 0), 0.0, places=9)

    def test_addressing_more_items_than_declared_rejected(self):
        with self.assertRaises(ValueError):
            item_coverage(5, 6)

    def test_zero_declared_items_rejected(self):
        with self.assertRaises(ValueError):
            item_coverage(0, 0)

    def test_negative_addressed_count_rejected(self):
        with self.assertRaises(ValueError):
            item_coverage(5, -2)


class ContentScoreTests(unittest.TestCase):
    def test_every_section_substantiated_scores_one(self):
        validated = validate_sections(_full_sections())
        self.assertAlmostEqual(content_score(validated), 1.0, places=9)

    def test_every_section_absent_scores_zero(self):
        validated = validate_sections([])
        self.assertAlmostEqual(content_score(validated), 0.0, places=9)

    def test_an_asserted_section_costs_half_its_weight(self):
        validated = validate_sections(
            _full_sections(**{"circuit-consequence-and-arc-evaluation": "asserted"})
        )
        expected = (total_section_weight() - 1.0) / total_section_weight()
        self.assertAlmostEqual(content_score(validated), expected, places=9)

    def test_empty_mapping_rejected(self):
        with self.assertRaises(ValueError):
            content_score({})

    def test_missing_mandatory_listed_when_absent(self):
        validated = validate_sections(
            _full_sections(**{"mitigation-selection-and-justification": "absent"})
        )
        self.assertEqual(
            missing_mandatory_sections(validated),
            ["mitigation-selection-and-justification"],
        )

    def test_no_missing_mandatory_when_all_present(self):
        validated = validate_sections(_full_sections())
        self.assertEqual(missing_mandatory_sections(validated), [])

    def test_absent_optional_section_is_not_a_mandatory_shortfall(self):
        validated = validate_sections(
            _full_sections(**{"whisker-growth-driver-discussion": "absent"})
        )
        self.assertEqual(missing_mandatory_sections(validated), [])


class VerdictBoundaryTests(unittest.TestCase):
    def test_a_score_exactly_on_the_compliant_floor_is_compliant(self):
        validated = validate_sections(
            _full_sections(
                **{
                    "whisker-length-bounding-basis": "asserted",
                    "residual-risk-acceptance-statement": "asserted",
                }
            )
        )
        score = content_score(validated)
        self.assertAlmostEqual(score, COMPLIANT_SCORE_FLOOR, places=9)
        self.assertEqual(content_verdict(score, [], 1.0), "compliant")

    def test_a_score_just_under_the_compliant_floor_falls_to_actions(self):
        self.assertEqual(
            content_verdict(COMPLIANT_SCORE_FLOOR - 0.01, [], 1.0),
            "compliant-with-actions",
        )

    def test_a_score_exactly_on_the_actions_floor_still_earns_actions(self):
        self.assertEqual(
            content_verdict(ACTIONS_SCORE_FLOOR, [], 1.0), "compliant-with-actions"
        )

    def test_a_score_under_the_actions_floor_is_not_compliant(self):
        self.assertEqual(
            content_verdict(ACTIONS_SCORE_FLOOR - 0.05, [], 1.0), "not-compliant"
        )

    def test_a_mandatory_shortfall_blocks_compliant_at_any_score(self):
        self.assertEqual(
            content_verdict(1.0, ["mitigation-selection-and-justification"], 1.0),
            "compliant-with-actions",
        )

    def test_incomplete_item_coverage_blocks_compliant(self):
        self.assertEqual(content_verdict(1.0, [], 0.8), "compliant-with-actions")

    def test_the_boundary_tolerance_is_far_below_a_percentage_point(self):
        self.assertLess(SCORE_TOLERANCE, 1e-6)

    def test_score_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            content_verdict(1.2, [], 1.0)

    def test_non_list_missing_rejected(self):
        with self.assertRaises(ValueError):
            content_verdict(0.95, "mitigation-selection-and-justification", 1.0)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_analysis_is_acceptable_as_submitted(self):
        result = assess_whisker_risk_analysis(_analysis())
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["acceptable_as_submitted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["actions"], [])

    def test_a_missing_mandatory_section_raises_a_finding_and_an_action(self):
        result = assess_whisker_risk_analysis(
            _analysis(
                sections=_full_sections(
                    **{"mitigation-selection-and-justification": "absent"}
                )
            )
        )
        self.assertIn("mitigation-selection-and-justification", result["missing_mandatory"])
        self.assertFalse(result["acceptable_as_submitted"])
        self.assertIn(
            "write-the-missing-section-mitigation-selection-and-justification",
            result["actions"],
        )

    def test_uncovered_items_are_reported_with_both_counts(self):
        result = assess_whisker_risk_analysis(
            _analysis(pure_tin_item_count=11, items_addressed=8)
        )
        self.assertAlmostEqual(result["item_coverage"], 8 / 11, places=9)
        self.assertTrue(
            any("8 of 11" in f for f in result["findings"]),
            result["findings"],
        )
        self.assertIn(
            "extend-the-analysis-to-every-declared-pure-tin-item", result["actions"]
        )

    def test_an_uncited_substantiation_is_demoted_and_reported(self):
        sections = _full_sections()
        for entry in sections:
            if entry["section"] == "whisker-length-bounding-basis":
                entry["evidence_refs"] = 0
        result = assess_whisker_risk_analysis(_analysis(sections=sections))
        self.assertIn("whisker-length-bounding-basis", result["demoted_sections"])
        self.assertIn(
            "cite-evidence-for-section-whisker-length-bounding-basis",
            result["actions"],
        )

    def test_an_empty_analysis_is_not_compliant(self):
        result = assess_whisker_risk_analysis(_analysis(sections=[]))
        self.assertEqual(result["verdict"], "not-compliant")
        self.assertAlmostEqual(result["content_score"], 0.0, places=9)

    def test_blank_document_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_whisker_risk_analysis(_analysis(document_id="  "))

    def test_missing_key_rejected(self):
        analysis = _analysis()
        del analysis["items_addressed"]
        with self.assertRaises(ValueError):
            assess_whisker_risk_analysis(analysis)

    def test_non_mapping_analysis_rejected(self):
        with self.assertRaises(ValueError):
            assess_whisker_risk_analysis(["CCP-WHISK-014"])

    def test_every_required_section_appears_in_the_result(self):
        result = assess_whisker_risk_analysis(_analysis(sections=[]))
        self.assertEqual(set(result["sections"]), set(REQUIRED_SECTIONS))

    def test_verdict_is_always_from_the_fixed_vocabulary(self):
        for addressed in (0, 5, 11):
            result = assess_whisker_risk_analysis(
                _analysis(items_addressed=addressed)
            )
            self.assertIn(result["verdict"], VERDICTS)


if __name__ == "__main__":
    unittest.main()
