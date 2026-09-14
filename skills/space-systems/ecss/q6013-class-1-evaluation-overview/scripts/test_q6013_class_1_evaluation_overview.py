"""Contract test for the ECSS-Q-ST-60-13C clause 4.2.3.1 evaluation leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_1_evaluation_overview.py
"""

import unittest

from q6013_class_1_evaluation_overview_logic import (
    COVERAGE_TOLERANCE,
    ELEMENT_STATE_CREDIT,
    ELEMENT_WEIGHTS,
    HERITAGE_VALIDITY_MONTHS,
    MANDATORY_ELEMENTS,
    VERDICTS,
    assess_campaign,
    assess_element,
    campaign_coverage,
    element_weight,
    heritage_admissible,
    normalize_element,
    outstanding_elements,
    state_credit,
)

TOTAL_WEIGHT = sum(ELEMENT_WEIGHTS.values())


def good_claim(**overrides):
    """A heritage claim that satisfies every admissibility rule."""
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

    def test_mandatory_elements_carry_the_heaviest_weight(self):
        heaviest = max(ELEMENT_WEIGHTS.values())
        for name in MANDATORY_ELEMENTS:
            self.assertAlmostEqual(element_weight(name), heaviest, places=9)

    def test_unknown_element_rejected(self):
        with self.assertRaises(ValueError):
            element_weight("vibe-check")


class StateCreditTests(unittest.TestCase):
    def test_performing_on_the_part_type_earns_full_credit(self):
        self.assertAlmostEqual(state_credit("performed-on-this-part-type"), 1.0, places=9)

    def test_similarity_earns_partial_credit_only(self):
        credit = state_credit("performed-on-similar-part-type")
        self.assertGreater(credit, 0.0)
        self.assertLess(credit, 1.0)

    def test_a_plan_earns_nothing(self):
        self.assertAlmostEqual(state_credit("planned-not-yet-performed"), 0.0, places=9)

    def test_every_state_credit_sits_between_zero_and_one(self):
        for credit in ELEMENT_STATE_CREDIT.values():
            self.assertGreaterEqual(credit, 0.0)
            self.assertLessEqual(credit, 1.0)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            state_credit("someone-said-it-was-fine")


class HeritageAdmissibilityTests(unittest.TestCase):
    def test_a_complete_claim_is_admissible(self):
        admissible, reasons = heritage_admissible(good_claim())
        self.assertTrue(admissible)
        self.assertEqual(reasons, [])

    def test_a_different_assembly_site_breaks_the_claim(self):
        admissible, reasons = heritage_admissible(good_claim(same_assembly_site=False))
        self.assertFalse(admissible)
        self.assertIn("heritage-assembly-site-differs", reasons)

    def test_a_notified_process_change_supersedes_the_claim(self):
        admissible, reasons = heritage_admissible(good_claim(process_change_notified=True))
        self.assertFalse(admissible)
        self.assertIn("heritage-superseded-by-process-change", reasons)

    def test_evidence_at_the_validity_limit_still_stands(self):
        admissible, reasons = heritage_admissible(
            good_claim(evidence_age_months=float(HERITAGE_VALIDITY_MONTHS))
        )
        self.assertTrue(admissible)
        self.assertEqual(reasons, [])

    def test_evidence_past_the_validity_limit_falls(self):
        admissible, reasons = heritage_admissible(
            good_claim(evidence_age_months=float(HERITAGE_VALIDITY_MONTHS) + 1.0)
        )
        self.assertFalse(admissible)
        self.assertIn("heritage-evidence-out-of-validity", reasons)

    def test_every_broken_rule_is_named_at_once(self):
        admissible, reasons = heritage_admissible(
            good_claim(same_manufacturer=False, same_part_number=False)
        )
        self.assertFalse(admissible)
        self.assertEqual(len(reasons), 2)

    def test_negative_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            heritage_admissible(good_claim(evidence_age_months=-1.0))

    def test_non_boolean_manufacturer_flag_rejected(self):
        with self.assertRaises(ValueError):
            heritage_admissible(good_claim(same_manufacturer="yes"))

    def test_non_mapping_claim_rejected(self):
        with self.assertRaises(ValueError):
            heritage_admissible(["same manufacturer"])


class NormaliseElementTests(unittest.TestCase):
    def test_state_defaults_to_absent(self):
        element = normalize_element({"element": "assembly-compatibility-check"})
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

    def test_an_admissible_heritage_claim_earns_full_credit(self):
        record = assess_element(
            {
                "element": "endurance-life-test",
                "state": "covered-by-heritage-claim",
                "heritage_claim": good_claim(),
            }
        )
        self.assertAlmostEqual(record["credit"], 1.0, places=9)
        self.assertEqual(record["findings"], [])

    def test_an_inadmissible_heritage_claim_earns_nothing_and_names_why(self):
        record = assess_element(
            {
                "element": "endurance-life-test",
                "state": "covered-by-heritage-claim",
                "heritage_claim": good_claim(same_part_number=False),
            }
        )
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertIn("heritage-claim-inadmissible", record["findings"])
        self.assertIn("heritage-part-number-differs", record["heritage_reasons"])

    def test_similarity_on_a_spare_element_leaves_a_finding(self):
        record = assess_element(
            {
                "element": "materials-and-outgassing-review",
                "state": "performed-on-similar-part-type",
            }
        )
        self.assertIn("similarity-credit-taken", record["findings"])

    def test_a_waiver_on_a_mandatory_element_earns_nothing(self):
        record = assess_element(
            {
                "element": "radiation-evaluation",
                "state": "waived-with-approved-justification",
            }
        )
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertIn("mandatory-element-not-covered", record["findings"])

    def test_similarity_on_a_mandatory_element_earns_nothing(self):
        record = assess_element(
            {
                "element": "construction-analysis",
                "state": "performed-on-similar-part-type",
            }
        )
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertEqual(record["findings"].count("mandatory-element-not-covered"), 1)

    def test_an_approved_waiver_on_a_spare_element_keeps_its_credit(self):
        record = assess_element(
            {
                "element": "materials-and-outgassing-review",
                "state": "waived-with-approved-justification",
            }
        )
        self.assertAlmostEqual(record["credit"], 1.0, places=9)
        self.assertIn("element-waived-under-justification", record["findings"])


class CoverageTests(unittest.TestCase):
    def test_a_complete_campaign_covers_everything(self):
        report = assess_campaign("cots-adc-01", full_campaign())
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)

    def test_one_missing_light_element_removes_exactly_its_weight(self):
        report = assess_campaign(
            "cots-adc-01",
            full_campaign(**{"materials-and-outgassing-review": {"state": "element-absent"}}),
        )
        self.assertAlmostEqual(
            report["coverage_fraction"] * TOTAL_WEIGHT,
            TOTAL_WEIGHT - ELEMENT_WEIGHTS["materials-and-outgassing-review"],
            places=9,
        )

    def test_coverage_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            campaign_coverage([])

    def test_coverage_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            campaign_coverage({"weight": 1.0, "weighted_credit": 1.0})

    def test_outstanding_elements_come_back_heaviest_first(self):
        report = assess_campaign(
            "cots-adc-01",
            full_campaign(
                **{
                    "materials-and-outgassing-review": {"state": "element-absent"},
                    "endurance-life-test": {"state": "planned-not-yet-performed"},
                }
            ),
        )
        self.assertEqual(
            report["outstanding_elements"],
            ["endurance-life-test", "materials-and-outgassing-review"],
        )

    def test_outstanding_ignores_credit_a_hair_under_one(self):
        record = {
            "element": "assembly-compatibility-check",
            "weight": 0.6,
            "credit": 1.0 - COVERAGE_TOLERANCE / 2.0,
        }
        self.assertEqual(outstanding_elements([record]), [])


class CampaignVerdictTests(unittest.TestCase):
    def test_a_complete_campaign_is_suitable_for_the_highest_class(self):
        report = assess_campaign("cots-adc-01", full_campaign())
        self.assertEqual(report["verdict"], "evaluation-campaign-complete")
        self.assertTrue(report["suitable_for_class_1"])
        self.assertEqual(report["findings"], [])

    def test_a_spare_element_waiver_leaves_open_actions(self):
        report = assess_campaign(
            "cots-adc-01",
            full_campaign(
                **{
                    "materials-and-outgassing-review": {
                        "state": "waived-with-approved-justification"
                    }
                }
            ),
        )
        self.assertEqual(report["verdict"], "evaluation-campaign-open-actions")
        self.assertFalse(report["suitable_for_class_1"])

    def test_an_undeclared_element_is_graded_as_absent(self):
        report = assess_campaign("cots-adc-01", [])
        self.assertEqual(report["verdict"], "evaluation-campaign-incomplete")
        self.assertEqual(len(report["records"]), len(ELEMENT_WEIGHTS))
        self.assertAlmostEqual(report["coverage_fraction"], 0.0, places=9)

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(assess_campaign("p", full_campaign())["verdict"])
        seen.add(assess_campaign("p", [])["verdict"])
        seen.add(
            assess_campaign(
                "p",
                full_campaign(
                    **{
                        "materials-and-outgassing-review": {
                            "state": "waived-with-approved-justification"
                        }
                    }
                ),
            )["verdict"]
        )
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_element_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(
                "cots-adc-01",
                [
                    {"element": "radiation-evaluation", "state": "element-absent"},
                    {"element": "radiation-evaluation", "state": "element-absent"},
                ],
            )

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign("  ", full_campaign())

    def test_non_sequence_element_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign("cots-adc-01", {"element": "radiation-evaluation"})


if __name__ == "__main__":
    unittest.main()
