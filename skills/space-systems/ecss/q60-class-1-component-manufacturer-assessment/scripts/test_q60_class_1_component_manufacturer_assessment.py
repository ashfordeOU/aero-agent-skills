"""Contract test for the ECSS-Q-ST-60C clause 4.2.3.2 manufacturer leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_1_component_manufacturer_assessment.py
"""

import unittest

from q60_class_1_component_manufacturer_assessment_logic import (
    APPROVAL_INDEX,
    ASSESSMENT_TOLERANCE,
    AUDIT_VALIDITY_MONTHS,
    BASELINE_CRITERIA,
    BASELINE_MIN_EFFECTIVE,
    CRITERION_WEIGHTS,
    EVIDENCE_SOURCE_FACTOR,
    RATING_VALUE,
    VERDICTS,
    assess_criterion,
    assess_manufacturer,
    blocking_criteria,
    capability_index,
    criterion_weight,
    normalize_criterion,
    rating_value,
    source_factor,
)

TOTAL_WEIGHT = sum(CRITERION_WEIGHTS.values())
SPARE_CRITERION = "electrostatic-discharge-control-programme"


def audited(criterion, rating="fully-compliant", **overrides):
    """One criterion found compliant at an on-site audit inside validity."""
    record = {
        "criterion": criterion,
        "rating": rating,
        "evidence_source": "on-site-audit",
        "evidence_age_months": 6.0,
    }
    record.update(overrides)
    return record


def clean_assessment(**overrides):
    """Every criterion fully compliant at an on-site audit, with exceptions."""
    criteria = []
    for name in sorted(CRITERION_WEIGHTS):
        entry = audited(name)
        if name in overrides:
            entry.update(overrides[name])
        criteria.append(entry)
    return criteria


class CriterionWeightTests(unittest.TestCase):
    def test_every_criterion_carries_a_positive_weight(self):
        for name in CRITERION_WEIGHTS:
            self.assertGreater(criterion_weight(name), 0.1)

    def test_the_baseline_criteria_are_all_known_criteria(self):
        for name in BASELINE_CRITERIA:
            self.assertIn(name, CRITERION_WEIGHTS)

    def test_the_quality_system_carries_the_heaviest_weight(self):
        heaviest = max(CRITERION_WEIGHTS.values())
        self.assertAlmostEqual(
            criterion_weight("quality-management-system-certification"),
            heaviest,
            places=9,
        )

    def test_unknown_criterion_rejected(self):
        with self.assertRaises(ValueError):
            criterion_weight("general-vibes")


class RatingAndSourceTests(unittest.TestCase):
    def test_full_compliance_is_the_top_of_the_rating_scale(self):
        self.assertAlmostEqual(max(RATING_VALUE.values()), 1.0, places=9)
        self.assertAlmostEqual(rating_value("fully-compliant"), 1.0, places=9)

    def test_an_unassessed_criterion_rates_as_nothing(self):
        self.assertAlmostEqual(rating_value("not-assessed"), 0.0, places=9)

    def test_unknown_rating_rejected(self):
        with self.assertRaises(ValueError):
            rating_value("seemed-alright")

    def test_an_on_site_audit_is_worth_the_whole_finding(self):
        factor, findings = source_factor("on-site-audit", 6.0)
        self.assertAlmostEqual(factor, 1.0, places=9)
        self.assertEqual(findings, [])

    def test_a_questionnaire_is_worth_less_than_an_audit(self):
        self.assertLess(
            EVIDENCE_SOURCE_FACTOR["questionnaire-response-only"],
            EVIDENCE_SOURCE_FACTOR["on-site-audit"],
        )

    def test_evidence_at_the_validity_limit_keeps_its_worth(self):
        factor, findings = source_factor("on-site-audit", float(AUDIT_VALIDITY_MONTHS))
        self.assertAlmostEqual(factor, 1.0, places=9)
        self.assertEqual(findings, [])

    def test_evidence_past_the_validity_limit_derates_to_the_weakest_source(self):
        factor, findings = source_factor(
            "on-site-audit", float(AUDIT_VALIDITY_MONTHS) + 1.0
        )
        self.assertAlmostEqual(
            factor, EVIDENCE_SOURCE_FACTOR["questionnaire-response-only"], places=9
        )
        self.assertIn("assessment-evidence-out-of-validity", findings)

    def test_an_already_weak_source_is_not_derated_twice(self):
        factor, findings = source_factor(
            "questionnaire-response-only", float(AUDIT_VALIDITY_MONTHS) + 24.0
        )
        self.assertAlmostEqual(
            factor, EVIDENCE_SOURCE_FACTOR["questionnaire-response-only"], places=9
        )
        self.assertEqual(findings, [])

    def test_negative_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            source_factor("on-site-audit", -1.0)

    def test_unknown_evidence_source_rejected(self):
        with self.assertRaises(ValueError):
            source_factor("a-phone-call", 1.0)


class NormaliseCriterionTests(unittest.TestCase):
    def test_rating_defaults_to_not_assessed(self):
        record = normalize_criterion({"criterion": SPARE_CRITERION})
        self.assertEqual(record["rating"], "not-assessed")
        self.assertEqual(record["evidence_source"], "no-evidence-supplied")

    def test_a_rating_without_an_evidence_source_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion(
                {"criterion": SPARE_CRITERION, "rating": "fully-compliant"}
            )

    def test_non_mapping_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion(SPARE_CRITERION)

    def test_non_numeric_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion(audited(SPARE_CRITERION, evidence_age_months="recent"))


class AssessCriterionTests(unittest.TestCase):
    def test_a_fully_compliant_audit_earns_the_whole_weight(self):
        record = assess_criterion(audited(SPARE_CRITERION))
        self.assertAlmostEqual(record["weighted_rating"], record["weight"], places=9)
        self.assertEqual(record["findings"], [])
        self.assertFalse(record["blocking"])

    def test_the_evidence_source_derates_the_rating_rather_than_sitting_beside_it(self):
        record = assess_criterion(
            audited(SPARE_CRITERION, evidence_source="third-party-audit-report")
        )
        self.assertAlmostEqual(
            record["effective_rating"],
            EVIDENCE_SOURCE_FACTOR["third-party-audit-report"],
            places=9,
        )

    def test_an_observation_on_a_baseline_criterion_still_clears_the_baseline(self):
        record = assess_criterion(
            audited(
                "traceability-and-lot-identification", rating="compliant-with-observation"
            )
        )
        self.assertAlmostEqual(
            record["effective_rating"], BASELINE_MIN_EFFECTIVE, places=9
        )
        self.assertFalse(record["blocking"])
        self.assertIn("criterion-observation-open", record["findings"])

    def test_a_baseline_criterion_on_paper_evidence_alone_blocks(self):
        record = assess_criterion(
            audited(
                "change-notification-procedure",
                evidence_source="questionnaire-response-only",
            )
        )
        self.assertTrue(record["blocking"])
        self.assertIn("baseline-criterion-blocking", record["findings"])
        self.assertIn("rating-rests-on-questionnaire-only", record["findings"])

    def test_a_partially_compliant_baseline_criterion_blocks(self):
        record = assess_criterion(
            audited(
                "process-control-and-statistical-monitoring", rating="partially-compliant"
            )
        )
        self.assertTrue(record["blocking"])
        self.assertIn("criterion-partially-compliant", record["findings"])

    def test_a_weak_rating_on_a_spare_criterion_does_not_block(self):
        record = assess_criterion(audited(SPARE_CRITERION, rating="non-compliant"))
        self.assertFalse(record["blocking"])
        self.assertIn("criterion-non-compliant", record["findings"])


class CapabilityIndexTests(unittest.TestCase):
    def test_a_clean_assessment_indexes_at_the_top_of_the_scale(self):
        report = assess_manufacturer("fab-01", clean_assessment())
        self.assertAlmostEqual(report["capability_index"], 1.0, places=9)

    def test_one_unassessed_spare_criterion_removes_exactly_its_weight(self):
        report = assess_manufacturer(
            "fab-01",
            clean_assessment(
                **{SPARE_CRITERION: {"rating": "not-assessed", "evidence_source": "no-evidence-supplied"}}
            ),
        )
        self.assertAlmostEqual(
            report["capability_index"] * TOTAL_WEIGHT,
            TOTAL_WEIGHT - CRITERION_WEIGHTS[SPARE_CRITERION],
            places=9,
        )

    def test_the_index_reads_the_approval_bound_exactly(self):
        records = [
            {"weight": 1.0, "weighted_rating": APPROVAL_INDEX, "blocking": False, "criterion": "a"}
        ]
        self.assertAlmostEqual(capability_index(records), APPROVAL_INDEX, places=9)

    def test_index_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            capability_index([])

    def test_index_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            capability_index({"weight": 1.0, "weighted_rating": 1.0})

    def test_blocking_criteria_come_back_heaviest_first(self):
        report = assess_manufacturer(
            "fab-01",
            clean_assessment(
                **{
                    "change-notification-procedure": {"rating": "non-compliant"},
                    "quality-management-system-certification": {"rating": "non-compliant"},
                }
            ),
        )
        self.assertEqual(
            report["blocking_criteria"],
            [
                "quality-management-system-certification",
                "change-notification-procedure",
            ],
        )

    def test_blocking_list_is_empty_on_a_clean_assessment(self):
        report = assess_manufacturer("fab-01", clean_assessment())
        self.assertEqual(blocking_criteria(report["records"]), [])


class ManufacturerVerdictTests(unittest.TestCase):
    def test_a_clean_assessment_approves_the_manufacturer(self):
        report = assess_manufacturer("fab-01", clean_assessment())
        self.assertEqual(report["verdict"], "manufacturer-approved-for-class-1")
        self.assertTrue(report["approved_for_class_1"])
        self.assertEqual(report["findings"], [])
        self.assertFalse(report["reassessment_due"])

    def test_an_observation_on_a_spare_criterion_leaves_open_actions(self):
        report = assess_manufacturer(
            "fab-01",
            clean_assessment(**{SPARE_CRITERION: {"rating": "compliant-with-observation"}}),
        )
        self.assertEqual(report["verdict"], "manufacturer-approved-with-open-actions")
        self.assertTrue(report["approved_for_class_1"])

    def test_one_blocking_baseline_criterion_fails_an_otherwise_strong_factory(self):
        report = assess_manufacturer(
            "fab-01",
            clean_assessment(
                **{"traceability-and-lot-identification": {"rating": "partially-compliant"}}
            ),
        )
        self.assertEqual(report["verdict"], "manufacturer-not-approved-for-class-1")
        self.assertFalse(report["approved_for_class_1"])
        self.assertIn("traceability-and-lot-identification", report["blocking_criteria"])

    def test_a_thin_report_is_graded_against_the_whole_baseline(self):
        report = assess_manufacturer("fab-01", [])
        self.assertEqual(len(report["records"]), len(CRITERION_WEIGHTS))
        self.assertAlmostEqual(report["capability_index"], 0.0, places=9)
        self.assertEqual(report["verdict"], "manufacturer-not-approved-for-class-1")

    def test_stale_audit_evidence_raises_a_reassessment(self):
        report = assess_manufacturer(
            "fab-01",
            clean_assessment(
                **{
                    SPARE_CRITERION: {
                        "evidence_age_months": float(AUDIT_VALIDITY_MONTHS) + 12.0
                    }
                }
            ),
        )
        self.assertTrue(report["reassessment_due"])
        self.assertIn(
            "assessment-evidence-out-of-validity",
            [f["finding"] for f in report["findings"]],
        )

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(assess_manufacturer("m", clean_assessment())["verdict"])
        seen.add(assess_manufacturer("m", [])["verdict"])
        seen.add(
            assess_manufacturer(
                "m",
                clean_assessment(
                    **{SPARE_CRITERION: {"rating": "compliant-with-observation"}}
                ),
            )["verdict"]
        )
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_criterion_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer(
                "fab-01", [audited(SPARE_CRITERION), audited(SPARE_CRITERION)]
            )

    def test_empty_manufacturer_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer("   ", clean_assessment())

    def test_non_sequence_criteria_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer("fab-01", {"criterion": SPARE_CRITERION})

    def test_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(ASSESSMENT_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
