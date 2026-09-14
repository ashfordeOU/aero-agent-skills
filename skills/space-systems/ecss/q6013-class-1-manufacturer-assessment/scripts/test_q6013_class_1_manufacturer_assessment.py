"""Contract test for the ECSS-Q-ST-60-13C clause 4.2.3.2 manufacturer leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_1_manufacturer_assessment.py
"""

import unittest

from q6013_class_1_manufacturer_assessment_logic import (
    ACCEPT_THRESHOLD,
    ACTIONS_THRESHOLD,
    ASSESSMENT_VALIDITY_MONTHS,
    DIMENSION_WEIGHTS,
    EVIDENCE_CONFIDENCE,
    RATING_SCORES,
    SCORE_TOLERANCE,
    VERDICTS,
    VETO_DIMENSIONS,
    VETO_EVIDENCE_FLOOR,
    assess_dimension,
    assess_manufacturer,
    assessment_score,
    dimension_weight,
    effective_credit,
    evidence_confidence,
    evidence_in_validity,
    normalize_dimension,
    ranked_actions,
    rating_score,
    verdict_for_score,
)


def full_assessment(**overrides):
    """Every dimension met on an on-site audit, with named exceptions."""
    entries = []
    for name in sorted(DIMENSION_WEIGHTS):
        entry = {
            "dimension": name,
            "rating": "meets-requirement",
            "evidence_basis": "on-site-audit",
        }
        if name in overrides:
            entry.update(overrides[name])
        entries.append(entry)
    return entries


class DimensionWeightTests(unittest.TestCase):
    def test_every_dimension_carries_a_positive_weight(self):
        for name in DIMENSION_WEIGHTS:
            self.assertGreater(dimension_weight(name), 0.0)

    def test_veto_dimensions_carry_the_heaviest_weight(self):
        heaviest = max(DIMENSION_WEIGHTS.values())
        for name in VETO_DIMENSIONS:
            self.assertAlmostEqual(dimension_weight(name), heaviest, places=9)

    def test_unknown_dimension_rejected(self):
        with self.assertRaises(ValueError):
            dimension_weight("general-vibes")


class RatingAndEvidenceTests(unittest.TestCase):
    def test_meeting_the_requirement_scores_full(self):
        self.assertAlmostEqual(rating_score("meets-requirement"), 1.0, places=9)

    def test_not_meeting_the_requirement_scores_nothing(self):
        self.assertAlmostEqual(rating_score("does-not-meet"), 0.0, places=9)

    def test_every_rating_score_sits_between_zero_and_one(self):
        for score in RATING_SCORES.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_unknown_rating_rejected(self):
        with self.assertRaises(ValueError):
            rating_score("looked-alright")

    def test_an_on_site_audit_earns_full_confidence(self):
        self.assertAlmostEqual(evidence_confidence("on-site-audit"), 1.0, places=9)

    def test_an_unevidenced_claim_earns_nothing(self):
        self.assertAlmostEqual(evidence_confidence("no-evidence"), 0.0, places=9)

    def test_a_questionnaire_is_worth_less_than_a_remote_audit(self):
        self.assertLess(
            evidence_confidence("self-declared-questionnaire"),
            evidence_confidence("remote-audit"),
        )

    def test_every_confidence_factor_sits_between_zero_and_one(self):
        for factor in EVIDENCE_CONFIDENCE.values():
            self.assertGreaterEqual(factor, 0.0)
            self.assertLessEqual(factor, 1.0)

    def test_unknown_evidence_basis_rejected(self):
        with self.assertRaises(ValueError):
            evidence_confidence("someone-phoned-them")

    def test_credit_is_the_rating_discounted_by_the_evidence(self):
        self.assertAlmostEqual(
            effective_credit("meets-requirement", "self-declared-questionnaire"),
            EVIDENCE_CONFIDENCE["self-declared-questionnaire"],
            places=9,
        )

    def test_a_perfect_questionnaire_is_worth_less_than_a_perfect_audit(self):
        self.assertLess(
            effective_credit("meets-requirement", "self-declared-questionnaire"),
            effective_credit("meets-requirement", "on-site-audit"),
        )


class NormaliseDimensionTests(unittest.TestCase):
    def test_rating_and_basis_default_to_the_weakest_values(self):
        entry = normalize_dimension({"dimension": "subcontracted-assembly-control"})
        self.assertEqual(entry["rating"], "does-not-meet")
        self.assertEqual(entry["evidence_basis"], "no-evidence")

    def test_non_mapping_dimension_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dimension("quality-management-system")

    def test_unknown_rating_inside_a_dimension_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dimension(
                {"dimension": "quality-management-system", "rating": "fine-probably"}
            )


class VetoTests(unittest.TestCase):
    def test_a_veto_dimension_that_is_not_met_breaches(self):
        record = assess_dimension(
            {
                "dimension": "quality-management-system",
                "rating": "does-not-meet",
                "evidence_basis": "on-site-audit",
            }
        )
        self.assertEqual(record["veto_breach"], "veto-dimension-not-met")

    def test_a_questionnaire_under_a_veto_dimension_breaches_the_floor(self):
        record = assess_dimension(
            {
                "dimension": "lot-traceability-to-wafer-and-assembly",
                "rating": "meets-requirement",
                "evidence_basis": "self-declared-questionnaire",
            }
        )
        self.assertEqual(record["veto_breach"], "veto-dimension-evidence-below-floor")

    def test_evidence_landing_exactly_on_the_floor_does_not_breach(self):
        basis = "third-party-certificate"
        self.assertAlmostEqual(
            EVIDENCE_CONFIDENCE[basis], VETO_EVIDENCE_FLOOR, places=9
        )
        record = assess_dimension(
            {
                "dimension": "process-change-notification-commitment",
                "rating": "meets-requirement",
                "evidence_basis": basis,
            }
        )
        self.assertIsNone(record["veto_breach"])

    def test_a_spare_dimension_on_a_questionnaire_does_not_breach(self):
        record = assess_dimension(
            {
                "dimension": "component-change-history-availability",
                "rating": "meets-requirement",
                "evidence_basis": "self-declared-questionnaire",
            }
        )
        self.assertIsNone(record["veto_breach"])
        self.assertIn("dimension-action-owed", record["findings"])

    def test_an_unevidenced_dimension_is_named_as_such(self):
        record = assess_dimension({"dimension": "reliability-monitoring-programme"})
        self.assertIn("dimension-unevidenced", record["findings"])
        self.assertAlmostEqual(record["credit"], 0.0, places=9)

    def test_a_fully_met_audited_dimension_owes_nothing(self):
        record = assess_dimension(
            {
                "dimension": "reliability-monitoring-programme",
                "rating": "meets-requirement",
                "evidence_basis": "on-site-audit",
            }
        )
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["shortfall"], 0.0, places=9)


class ScoreTests(unittest.TestCase):
    def test_a_fully_met_audited_assessment_scores_one(self):
        report = assess_manufacturer("mfr-a", full_assessment(), 6.0)
        self.assertAlmostEqual(report["score"], 1.0, places=9)

    def test_a_weaker_basis_lowers_the_score(self):
        weaker = assess_manufacturer(
            "mfr-a",
            full_assessment(
                **{
                    "component-change-history-availability": {
                        "evidence_basis": "remote-audit"
                    }
                }
            ),
            6.0,
        )
        self.assertLess(weaker["score"], 1.0)

    def test_score_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            assessment_score([])

    def test_score_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            assessment_score({"weight": 1.0, "weighted_credit": 1.0})

    def test_score_rejects_a_non_numeric_weight(self):
        with self.assertRaises(ValueError):
            assessment_score([{"weight": "heavy", "weighted_credit": 1.0}])


class ValidityTests(unittest.TestCase):
    def test_evidence_at_the_validity_limit_still_counts(self):
        self.assertTrue(evidence_in_validity(float(ASSESSMENT_VALIDITY_MONTHS)))

    def test_evidence_past_the_validity_limit_does_not(self):
        self.assertFalse(evidence_in_validity(float(ASSESSMENT_VALIDITY_MONTHS) + 1.0))

    def test_negative_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            evidence_in_validity(-1.0)

    def test_non_numeric_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            evidence_in_validity("last spring")


class VerdictTests(unittest.TestCase):
    def test_a_score_on_the_acceptance_threshold_is_accepted(self):
        self.assertEqual(
            verdict_for_score(ACCEPT_THRESHOLD, False, True),
            "manufacturer-assessment-accepted",
        )

    def test_a_score_on_the_actions_threshold_needs_actions(self):
        self.assertEqual(
            verdict_for_score(ACTIONS_THRESHOLD, False, True),
            "manufacturer-assessment-actions-required",
        )

    def test_a_score_below_the_actions_threshold_is_rejected(self):
        self.assertEqual(
            verdict_for_score(ACTIONS_THRESHOLD - 0.05, False, True),
            "manufacturer-assessment-rejected",
        )

    def test_a_veto_breach_rejects_a_perfect_score(self):
        self.assertEqual(
            verdict_for_score(1.0, True, True), "manufacturer-assessment-rejected"
        )

    def test_stale_evidence_blocks_outright_acceptance(self):
        self.assertEqual(
            verdict_for_score(1.0, False, False),
            "manufacturer-assessment-actions-required",
        )

    def test_representation_error_under_the_threshold_still_accepts(self):
        self.assertEqual(
            verdict_for_score(ACCEPT_THRESHOLD - SCORE_TOLERANCE / 2.0, False, True),
            "manufacturer-assessment-accepted",
        )

    def test_non_boolean_veto_flag_rejected(self):
        with self.assertRaises(ValueError):
            verdict_for_score(1.0, "no", True)


class AssessManufacturerTests(unittest.TestCase):
    def test_a_clean_audited_manufacturer_is_acceptable(self):
        report = assess_manufacturer("mfr-a", full_assessment(), 6.0)
        self.assertEqual(report["verdict"], "manufacturer-assessment-accepted")
        self.assertTrue(report["acceptable_for_class_1"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["actions"], [])

    def test_an_undeclared_dimension_is_graded_unevidenced(self):
        report = assess_manufacturer("mfr-b", [], 6.0)
        self.assertEqual(len(report["records"]), len(DIMENSION_WEIGHTS))
        self.assertAlmostEqual(report["score"], 0.0, places=9)
        self.assertEqual(report["verdict"], "manufacturer-assessment-rejected")

    def test_a_traceability_questionnaire_sinks_an_otherwise_strong_case(self):
        report = assess_manufacturer(
            "mfr-c",
            full_assessment(
                **{
                    "lot-traceability-to-wafer-and-assembly": {
                        "evidence_basis": "self-declared-questionnaire"
                    }
                }
            ),
            6.0,
        )
        self.assertIn("lot-traceability-to-wafer-and-assembly", report["veto_breaches"])
        self.assertEqual(report["verdict"], "manufacturer-assessment-rejected")

    def test_stale_evidence_keeps_a_perfect_manufacturer_out_of_acceptance(self):
        report = assess_manufacturer(
            "mfr-a", full_assessment(), float(ASSESSMENT_VALIDITY_MONTHS) + 12.0
        )
        self.assertFalse(report["evidence_in_validity"])
        self.assertEqual(report["verdict"], "manufacturer-assessment-actions-required")
        self.assertIn(
            {"dimension": "assessment-evidence", "finding": "evidence-out-of-validity"},
            report["findings"],
        )

    def test_actions_come_back_heaviest_shortfall_first(self):
        report = assess_manufacturer(
            "mfr-d",
            full_assessment(
                **{
                    "reliability-monitoring-programme": {"rating": "partially-meets"},
                    "component-change-history-availability": {"rating": "partially-meets"},
                }
            ),
            6.0,
        )
        self.assertEqual(
            report["actions"][:2],
            [
                "reliability-monitoring-programme",
                "component-change-history-availability",
            ],
        )

    def test_ranked_actions_ignores_a_shortfall_inside_tolerance(self):
        record = {
            "dimension": "subcontracted-assembly-control",
            "shortfall": SCORE_TOLERANCE / 2.0,
        }
        self.assertEqual(ranked_actions([record]), [])

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = {
            assess_manufacturer("mfr-a", full_assessment(), 6.0)["verdict"],
            assess_manufacturer("mfr-b", [], 6.0)["verdict"],
            assess_manufacturer(
                "mfr-a", full_assessment(), float(ASSESSMENT_VALIDITY_MONTHS) + 1.0
            )["verdict"],
        }
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_dimension_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer(
                "mfr-a",
                [
                    {"dimension": "quality-management-system"},
                    {"dimension": "quality-management-system"},
                ],
                6.0,
            )

    def test_empty_manufacturer_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer("   ", full_assessment(), 6.0)

    def test_non_sequence_dimension_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer("mfr-a", {"dimension": "quality-management-system"}, 6.0)


if __name__ == "__main__":
    unittest.main()
