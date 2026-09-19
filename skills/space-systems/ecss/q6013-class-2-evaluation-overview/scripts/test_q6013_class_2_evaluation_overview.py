"""Contract test for the ECSS-Q-ST-60-13C clause 5.2.3.1 Class 2 campaign leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_2_evaluation_overview.py
"""

import unittest

from q6013_class_2_evaluation_overview_logic import (
    CLASS_2_COVERAGE_THRESHOLD,
    CONDITIONAL_ELEMENTS,
    COVERAGE_TOLERANCE,
    ELEMENT_STATE_CREDIT,
    ELEMENT_WEIGHTS,
    HERITAGE_OUTCOMES,
    HERITAGE_SITE_DOWNGRADE_CREDIT,
    HERITAGE_VALIDITY_MONTHS,
    UNWAIVABLE_ELEMENTS,
    VERDICTS,
    assess_campaign,
    assess_element,
    campaign_coverage,
    element_applicable,
    element_weight,
    grade_heritage,
    meets_class_2_threshold,
    normalize_element,
    normalize_profile,
    outstanding_elements,
    state_credit,
)

FULL_PROFILE = {"radiation_requirement": True, "non_standard_assembly_process": True}


def good_claim(**overrides):
    """A heritage claim that satisfies every Class 2 admissibility rule."""
    base = {
        "same_manufacturer": True,
        "same_part_number": True,
        "same_assembly_site": True,
        "process_change_notified": False,
        "evidence_age_months": 12.0,
    }
    base.update(overrides)
    return base


def full_campaign(**states):
    """Every element performed on the part type, with named exceptions."""
    elements = []
    for name in sorted(ELEMENT_WEIGHTS):
        entry = {"element": name, "state": "performed-on-this-part-type"}
        if name in states:
            entry.update(states[name])
        elements.append(entry)
    return elements


class ElementWeightTests(unittest.TestCase):
    def test_every_element_carries_a_positive_weight(self):
        for name in ELEMENT_WEIGHTS:
            self.assertGreater(element_weight(name), 0.0)

    def test_the_unwaivable_elements_carry_the_heaviest_weight(self):
        heaviest = max(ELEMENT_WEIGHTS.values())
        for name in UNWAIVABLE_ELEMENTS:
            self.assertAlmostEqual(element_weight(name), heaviest, places=9)

    def test_unknown_element_rejected(self):
        with self.assertRaises(ValueError):
            element_weight("gut-feel-review")


class StateCreditTests(unittest.TestCase):
    def test_performing_on_the_part_type_earns_full_credit(self):
        self.assertAlmostEqual(state_credit("performed-on-this-part-type"), 1.0, places=9)

    def test_the_intermediate_class_credits_similarity_partly(self):
        credit = state_credit("performed-on-similar-part-type")
        self.assertGreater(credit, 0.0)
        self.assertLess(credit, 1.0)

    def test_every_state_credit_sits_between_zero_and_one(self):
        # Declared constants, so both ends of the range are attained
        # exactly rather than approached. Pinning the two extremes proves
        # the bound for every member and avoids a <= whose two operands
        # coincide on the full-credit states.
        credits = list(ELEMENT_STATE_CREDIT.values())
        self.assertEqual(max(credits), 1.0)
        self.assertEqual(min(credits), 0.0)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            state_credit("someone-signed-it-off")


class ApplicabilityTests(unittest.TestCase):
    def test_an_unconditional_element_always_applies(self):
        self.assertTrue(element_applicable("endurance-life-test", normalize_profile(None)))

    def test_a_conditional_element_is_owed_only_when_its_driver_is_raised(self):
        for name, driver in CONDITIONAL_ELEMENTS.items():
            drivers = normalize_profile({driver: True})
            self.assertTrue(element_applicable(name, drivers))
            self.assertFalse(element_applicable(name, normalize_profile({})))

    def test_an_unstated_driver_defaults_to_not_owed(self):
        drivers = normalize_profile(None)
        self.assertFalse(drivers["radiation_requirement"])

    def test_an_unknown_profile_driver_rejected(self):
        with self.assertRaises(ValueError):
            normalize_profile({"vibration_is_scary": True})

    def test_a_non_boolean_driver_rejected(self):
        with self.assertRaises(ValueError):
            normalize_profile({"radiation_requirement": "yes"})

    def test_a_non_mapping_profile_rejected(self):
        with self.assertRaises(ValueError):
            normalize_profile(["radiation_requirement"])


class HeritageTests(unittest.TestCase):
    def test_a_complete_claim_stands_whole(self):
        outcome, factor, reasons = grade_heritage(good_claim())
        self.assertEqual(outcome, "heritage-claim-stands")
        self.assertAlmostEqual(factor, 1.0, places=9)
        self.assertEqual(reasons, [])

    def test_a_different_assembly_site_downgrades_rather_than_breaks(self):
        outcome, factor, reasons = grade_heritage(good_claim(same_assembly_site=False))
        self.assertEqual(outcome, "heritage-claim-downgraded")
        self.assertAlmostEqual(factor, HERITAGE_SITE_DOWNGRADE_CREDIT, places=9)
        self.assertIn("heritage-assembly-site-differs", reasons)

    def test_a_different_part_number_breaks_the_claim(self):
        outcome, factor, reasons = grade_heritage(good_claim(same_part_number=False))
        self.assertEqual(outcome, "heritage-claim-inadmissible")
        self.assertAlmostEqual(factor, 0.0, places=9)
        self.assertIn("heritage-part-number-differs", reasons)

    def test_a_notified_process_change_breaks_the_claim(self):
        outcome, _factor, reasons = grade_heritage(good_claim(process_change_notified=True))
        self.assertEqual(outcome, "heritage-claim-inadmissible")
        self.assertIn("heritage-superseded-by-process-change", reasons)

    def test_evidence_at_the_validity_limit_still_stands(self):
        outcome, _factor, reasons = grade_heritage(
            good_claim(evidence_age_months=float(HERITAGE_VALIDITY_MONTHS))
        )
        self.assertEqual(outcome, "heritage-claim-stands")
        self.assertEqual(reasons, [])

    def test_evidence_past_the_validity_limit_falls(self):
        outcome, _factor, reasons = grade_heritage(
            good_claim(evidence_age_months=float(HERITAGE_VALIDITY_MONTHS) + 1.0)
        )
        self.assertEqual(outcome, "heritage-claim-inadmissible")
        self.assertIn("heritage-evidence-out-of-validity", reasons)

    def test_a_broken_claim_still_names_the_site_difference(self):
        _outcome, _factor, reasons = grade_heritage(
            good_claim(same_manufacturer=False, same_assembly_site=False)
        )
        self.assertIn("heritage-manufacturer-differs", reasons)
        self.assertIn("heritage-assembly-site-differs", reasons)

    def test_every_outcome_name_is_one_the_module_publishes(self):
        seen = {
            grade_heritage(good_claim())[0],
            grade_heritage(good_claim(same_assembly_site=False))[0],
            grade_heritage(good_claim(same_part_number=False))[0],
        }
        self.assertEqual(seen, set(HERITAGE_OUTCOMES))

    def test_negative_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            grade_heritage(good_claim(evidence_age_months=-1.0))

    def test_non_mapping_claim_rejected(self):
        with self.assertRaises(ValueError):
            grade_heritage(["same manufacturer"])


class NormaliseElementTests(unittest.TestCase):
    def test_state_defaults_to_absent(self):
        element = normalize_element({"element": "materials-and-finish-review"})
        self.assertEqual(element["state"], "element-absent")

    def test_heritage_state_without_a_claim_rejected(self):
        with self.assertRaises(ValueError):
            normalize_element(
                {"element": "endurance-life-test", "state": "covered-by-heritage-claim"}
            )

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            normalize_element("endurance-life-test")


class AssessElementTests(unittest.TestCase):
    def test_a_performed_element_earns_its_whole_weight(self):
        record = assess_element(
            {"element": "endurance-life-test", "state": "performed-on-this-part-type"}
        )
        self.assertAlmostEqual(record["weighted_credit"], record["weight"], places=9)
        self.assertEqual(record["findings"], [])

    def test_an_inapplicable_element_leaves_the_denominator(self):
        record = assess_element(
            {"element": "radiation-evaluation", "state": "element-absent"},
            applicable=False,
        )
        self.assertFalse(record["applicable"])
        self.assertAlmostEqual(record["weight"], 0.0, places=9)
        self.assertEqual(record["findings"], [])

    def test_a_downgraded_heritage_claim_keeps_partial_credit(self):
        record = assess_element(
            {
                "element": "endurance-life-test",
                "state": "covered-by-heritage-claim",
                "heritage_claim": good_claim(same_assembly_site=False),
            }
        )
        self.assertAlmostEqual(record["credit"], HERITAGE_SITE_DOWNGRADE_CREDIT, places=9)
        self.assertIn("heritage-claim-downgraded-on-assembly-site", record["findings"])

    def test_a_broken_heritage_claim_earns_nothing_and_names_why(self):
        record = assess_element(
            {
                "element": "endurance-life-test",
                "state": "covered-by-heritage-claim",
                "heritage_claim": good_claim(same_part_number=False),
            }
        )
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertIn("heritage-claim-inadmissible", record["findings"])

    def test_a_waiver_on_an_unwaivable_element_earns_nothing(self):
        record = assess_element(
            {
                "element": "constructional-analysis",
                "state": "waived-with-approved-justification",
            }
        )
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertIn("unwaivable-element-not-covered", record["findings"])

    def test_similarity_on_an_unwaivable_element_earns_nothing(self):
        record = assess_element(
            {
                "element": "manufacturer-assessment",
                "state": "performed-on-similar-part-type",
            }
        )
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertEqual(record["findings"].count("unwaivable-element-not-covered"), 1)

    def test_similarity_on_a_spare_element_keeps_its_partial_credit(self):
        record = assess_element(
            {
                "element": "materials-and-finish-review",
                "state": "performed-on-similar-part-type",
            }
        )
        self.assertAlmostEqual(
            record["credit"], ELEMENT_STATE_CREDIT["performed-on-similar-part-type"], places=9
        )
        self.assertIn("similarity-credit-taken", record["findings"])

    def test_non_boolean_applicability_rejected(self):
        with self.assertRaises(ValueError):
            assess_element(
                {"element": "endurance-life-test", "state": "element-absent"},
                applicable="maybe",
            )


class CoverageTests(unittest.TestCase):
    def test_a_complete_campaign_covers_everything(self):
        report = assess_campaign("cots-ldo-01", full_campaign(), FULL_PROFILE)
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)

    def test_an_inapplicable_element_is_neither_credit_nor_gap(self):
        elements = [
            e for e in full_campaign() if e["element"] != "radiation-evaluation"
        ]
        report = assess_campaign("cots-ldo-01", elements, {"non_standard_assembly_process": True})
        self.assertIn("radiation-evaluation", report["inapplicable_elements"])
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)
        self.assertNotIn("radiation-evaluation", report["outstanding_elements"])

    def test_coverage_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            campaign_coverage([])

    def test_coverage_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            campaign_coverage({"weight": 1.0, "weighted_credit": 1.0})

    def test_coverage_rejects_a_campaign_with_no_applicable_weight(self):
        with self.assertRaises(ValueError):
            campaign_coverage(
                [{"applicable": False, "weight": 0.0, "weighted_credit": 0.0}]
            )

    def test_outstanding_elements_come_back_heaviest_first(self):
        report = assess_campaign(
            "cots-ldo-01",
            full_campaign(
                **{
                    "materials-and-finish-review": {"state": "element-absent"},
                    "endurance-life-test": {"state": "planned-not-yet-performed"},
                }
            ),
            FULL_PROFILE,
        )
        self.assertEqual(
            report["outstanding_elements"],
            ["endurance-life-test", "materials-and-finish-review"],
        )

    def test_outstanding_ignores_credit_a_hair_under_one(self):
        record = {
            "element": "assembly-compatibility-check",
            "applicable": True,
            "weight": 0.5,
            "credit": 1.0 - COVERAGE_TOLERANCE / 2.0,
        }
        self.assertEqual(outstanding_elements([record]), [])


class ThresholdTests(unittest.TestCase):
    def test_coverage_exactly_at_the_threshold_meets_it(self):
        self.assertTrue(meets_class_2_threshold(CLASS_2_COVERAGE_THRESHOLD))

    def test_coverage_a_hair_under_the_threshold_still_meets_it(self):
        self.assertTrue(
            meets_class_2_threshold(CLASS_2_COVERAGE_THRESHOLD - COVERAGE_TOLERANCE / 2.0)
        )

    def test_coverage_materially_under_the_threshold_misses_it(self):
        self.assertFalse(meets_class_2_threshold(CLASS_2_COVERAGE_THRESHOLD - 0.05))

    def test_the_threshold_is_below_total_coverage(self):
        self.assertLess(CLASS_2_COVERAGE_THRESHOLD, 1.0)

    def test_non_numeric_coverage_rejected(self):
        with self.assertRaises(ValueError):
            meets_class_2_threshold("most of it")


class CampaignVerdictTests(unittest.TestCase):
    def test_a_complete_campaign_is_suitable_for_the_intermediate_class(self):
        report = assess_campaign("cots-ldo-01", full_campaign(), FULL_PROFILE)
        self.assertEqual(report["verdict"], "evaluation-campaign-complete")
        self.assertTrue(report["suitable_for_class_2"])
        self.assertEqual(report["findings"], [])

    def test_a_spare_element_waiver_leaves_open_actions(self):
        report = assess_campaign(
            "cots-ldo-01",
            full_campaign(
                **{
                    "materials-and-finish-review": {
                        "state": "waived-with-approved-justification"
                    }
                }
            ),
            FULL_PROFILE,
        )
        self.assertEqual(report["verdict"], "evaluation-campaign-open-actions")
        self.assertFalse(report["suitable_for_class_2"])

    def test_an_unwaivable_shortfall_beats_a_healthy_coverage_fraction(self):
        report = assess_campaign(
            "cots-ldo-01",
            full_campaign(
                **{
                    "constructional-analysis": {
                        "state": "waived-with-approved-justification"
                    }
                }
            ),
            FULL_PROFILE,
        )
        self.assertEqual(report["unwaivable_shortfalls"], ["constructional-analysis"])
        self.assertEqual(report["verdict"], "evaluation-campaign-incomplete")

    def test_an_undeclared_element_is_graded_as_absent(self):
        report = assess_campaign("cots-ldo-01", [], FULL_PROFILE)
        self.assertEqual(report["verdict"], "evaluation-campaign-incomplete")
        self.assertEqual(len(report["records"]), len(ELEMENT_WEIGHTS))
        self.assertAlmostEqual(report["coverage_fraction"], 0.0, places=9)

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = {
            assess_campaign("p", full_campaign(), FULL_PROFILE)["verdict"],
            assess_campaign("p", [], FULL_PROFILE)["verdict"],
            assess_campaign(
                "p",
                full_campaign(
                    **{
                        "materials-and-finish-review": {
                            "state": "waived-with-approved-justification"
                        }
                    }
                ),
                FULL_PROFILE,
            )["verdict"],
        }
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_element_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(
                "cots-ldo-01",
                [
                    {"element": "radiation-evaluation", "state": "element-absent"},
                    {"element": "radiation-evaluation", "state": "element-absent"},
                ],
                FULL_PROFILE,
            )

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign("  ", full_campaign(), FULL_PROFILE)

    def test_non_sequence_element_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign("cots-ldo-01", {"element": "radiation-evaluation"}, FULL_PROFILE)


if __name__ == "__main__":
    unittest.main()
