"""Contract test for the ECSS-Q-ST-60-13C clause 6.2.3.1 reduced-evaluation leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_3_evaluation_overview.py
"""

import unittest

from q6013_class_3_evaluation_overview_logic import (
    ELEMENT_WEIGHTS,
    ENVIRONMENT_GATED_ELEMENT,
    EXTENT_RETENTION,
    IRREDUCIBLE_ELEMENTS,
    SEVERITY_ALLOWANCE,
    VERDICTS,
    WEIGHT_TOLERANCE,
    assess_element,
    assess_reduced_campaign,
    element_weight,
    extent_retention,
    normalize_element,
    reduction_budget,
    retained_fraction,
    severity_allowance,
)

TOTAL_WEIGHT = sum(ELEMENT_WEIGHTS.values())


def full_campaign(**extents):
    """Every element performed in full, with named exceptions."""
    elements = []
    for name in sorted(ELEMENT_WEIGHTS):
        entry = {"element": name, "extent": "performed-in-full"}
        if name in extents:
            entry.update(extents[name])
        elements.append(entry)
    return elements


class ElementWeightTests(unittest.TestCase):
    def test_every_element_carries_a_positive_weight(self):
        for name in ELEMENT_WEIGHTS:
            self.assertGreater(element_weight(name), 0.0)

    def test_irreducible_elements_carry_the_heaviest_weight(self):
        heaviest = max(ELEMENT_WEIGHTS.values())
        for name in IRREDUCIBLE_ELEMENTS:
            self.assertAlmostEqual(element_weight(name), heaviest, places=9)

    def test_unknown_element_rejected(self):
        with self.assertRaises(ValueError):
            element_weight("looks-fine-to-me")


class ExtentRetentionTests(unittest.TestCase):
    def test_performing_in_full_retains_the_whole_weight(self):
        self.assertAlmostEqual(extent_retention("performed-in-full"), 1.0, places=9)

    def test_a_silent_omission_retains_nothing(self):
        self.assertAlmostEqual(extent_retention("omitted-silently"), 0.0, places=9)

    def test_similarity_retains_less_than_manufacturer_data(self):
        self.assertLess(
            extent_retention("covered-by-similar-part-family"),
            extent_retention("covered-by-manufacturer-data"),
        )

    def test_every_retention_sits_between_zero_and_one(self):
        for retention in EXTENT_RETENTION.values():
            self.assertGreaterEqual(retention, 0.0)
            self.assertLessEqual(retention, 1.0)

    def test_unknown_extent_rejected(self):
        with self.assertRaises(ValueError):
            extent_retention("someone-looked-at-it")


class SeverityAllowanceTests(unittest.TestCase):
    def test_a_benign_environment_buys_the_largest_reduction(self):
        self.assertAlmostEqual(
            severity_allowance("benign"), max(SEVERITY_ALLOWANCE.values()), places=9
        )

    def test_a_severe_environment_buys_the_smallest_reduction(self):
        self.assertAlmostEqual(
            severity_allowance("severe"), min(SEVERITY_ALLOWANCE.values()), places=9
        )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            severity_allowance("probably-fine")

    def test_budget_is_the_allowance_share_of_the_total_weight(self):
        self.assertAlmostEqual(
            reduction_budget(TOTAL_WEIGHT, "moderate"),
            TOTAL_WEIGHT * SEVERITY_ALLOWANCE["moderate"],
            places=9,
        )

    def test_budget_rejects_a_non_positive_total_weight(self):
        with self.assertRaises(ValueError):
            reduction_budget(0.0, "benign")

    def test_budget_rejects_a_non_numeric_total_weight(self):
        with self.assertRaises(ValueError):
            reduction_budget("six", "benign")


class NormaliseElementTests(unittest.TestCase):
    def test_extent_defaults_to_a_silent_omission(self):
        entry = normalize_element({"element": "endurance-sample"})
        self.assertEqual(entry["extent"], "omitted-silently")

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            normalize_element("endurance-sample")


class AssessElementTests(unittest.TestCase):
    def test_a_full_element_drops_nothing_and_leaves_no_finding(self):
        record = assess_element(
            {"element": "endurance-sample", "extent": "performed-in-full"}, "moderate"
        )
        self.assertAlmostEqual(record["dropped_weight"], 0.0, places=9)
        self.assertEqual(record["findings"], [])
        self.assertFalse(record["blocking"])

    def test_manufacturer_data_drops_half_the_weight_and_is_flagged(self):
        record = assess_element(
            {
                "element": "electrical-characterisation-over-temperature",
                "extent": "covered-by-manufacturer-data",
            },
            "moderate",
        )
        self.assertAlmostEqual(
            record["dropped_weight"],
            ELEMENT_WEIGHTS["electrical-characterisation-over-temperature"] * 0.5,
            places=9,
        )
        self.assertIn("manufacturer-data-credit-taken", record["findings"])
        self.assertFalse(record["blocking"])

    def test_reducing_an_irreducible_element_blocks(self):
        record = assess_element(
            {"element": "manufacturer-assessment", "extent": "performed-reduced"},
            "benign",
        )
        self.assertIn("irreducible-element-reduced", record["findings"])
        self.assertTrue(record["blocking"])

    def test_the_gated_element_may_be_reduced_in_a_benign_environment(self):
        record = assess_element(
            {"element": ENVIRONMENT_GATED_ELEMENT, "extent": "performed-reduced"},
            "benign",
        )
        self.assertNotIn("environment-gated-element-reduced", record["findings"])
        self.assertFalse(record["blocking"])

    def test_the_gated_element_may_not_be_reduced_in_a_severe_environment(self):
        record = assess_element(
            {"element": ENVIRONMENT_GATED_ELEMENT, "extent": "performed-reduced"},
            "severe",
        )
        self.assertIn("environment-gated-element-reduced", record["findings"])
        self.assertTrue(record["blocking"])

    def test_a_silent_omission_blocks_but_a_reasoned_one_does_not(self):
        silent = assess_element(
            {"element": "materials-and-outgassing-review", "extent": "omitted-silently"},
            "benign",
        )
        reasoned = assess_element(
            {
                "element": "materials-and-outgassing-review",
                "extent": "omitted-with-rationale",
            },
            "benign",
        )
        self.assertTrue(silent["blocking"])
        self.assertFalse(reasoned["blocking"])
        self.assertIn("element-omitted-under-rationale", reasoned["findings"])

    def test_unknown_severity_rejected_at_element_level(self):
        with self.assertRaises(ValueError):
            assess_element(
                {"element": "endurance-sample", "extent": "performed-in-full"}, "spicy"
            )


class RetainedFractionTests(unittest.TestCase):
    def test_a_full_campaign_retains_everything(self):
        report = assess_reduced_campaign("cots-ldo-03", "moderate", full_campaign())
        self.assertAlmostEqual(report["retained_fraction"], 1.0, places=9)

    def test_one_reasoned_omission_removes_exactly_its_weight(self):
        report = assess_reduced_campaign(
            "cots-ldo-03",
            "moderate",
            full_campaign(
                **{"materials-and-outgassing-review": {"extent": "omitted-with-rationale"}}
            ),
        )
        self.assertAlmostEqual(
            report["retained_fraction"] * TOTAL_WEIGHT,
            TOTAL_WEIGHT - ELEMENT_WEIGHTS["materials-and-outgassing-review"],
            places=9,
        )

    def test_retained_fraction_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            retained_fraction([])

    def test_retained_fraction_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            retained_fraction({"weight": 1.0, "retained_weight": 1.0})


class CampaignVerdictTests(unittest.TestCase):
    def test_a_full_campaign_is_sufficient_at_the_lowest_class(self):
        report = assess_reduced_campaign("cots-ldo-03", "severe", full_campaign())
        self.assertEqual(report["verdict"], "reduced-evaluation-sufficient")
        self.assertTrue(report["suitable_at_class_3"])
        self.assertEqual(report["findings"], [])

    def test_a_reduction_inside_the_allowance_is_conditional(self):
        report = assess_reduced_campaign(
            "cots-ldo-03",
            "benign",
            full_campaign(
                **{"endurance-sample": {"extent": "covered-by-manufacturer-data"}}
            ),
        )
        self.assertEqual(report["verdict"], "reduced-evaluation-conditional")
        self.assertFalse(report["allowance_exceeded"])
        self.assertTrue(report["suitable_at_class_3"])

    def test_spending_past_the_allowance_over_reduces_the_campaign(self):
        report = assess_reduced_campaign(
            "cots-ldo-03",
            "severe",
            full_campaign(
                **{
                    "electrical-characterisation-over-temperature": {
                        "extent": "omitted-with-rationale"
                    },
                    "assembly-and-mounting-compatibility": {
                        "extent": "omitted-with-rationale"
                    },
                }
            ),
        )
        self.assertTrue(report["allowance_exceeded"])
        self.assertEqual(report["verdict"], "reduced-evaluation-over-reduced")
        self.assertFalse(report["suitable_at_class_3"])

    def test_a_campaign_landing_on_its_allowance_has_not_exceeded_it(self):
        report = assess_reduced_campaign(
            "cots-ldo-03",
            "severe",
            full_campaign(
                **{
                    "assembly-and-mounting-compatibility": {
                        "extent": "omitted-with-rationale"
                    },
                    "materials-and-outgassing-review": {
                        "extent": "omitted-with-rationale"
                    },
                }
            ),
        )
        self.assertAlmostEqual(
            report["dropped_weight"], report["reduction_allowance"], places=9
        )
        self.assertFalse(report["allowance_exceeded"])
        self.assertEqual(report["verdict"], "reduced-evaluation-conditional")

    def test_an_undeclared_element_is_graded_as_a_silent_omission(self):
        report = assess_reduced_campaign("cots-ldo-03", "benign", [])
        self.assertEqual(report["verdict"], "reduced-evaluation-over-reduced")
        self.assertEqual(len(report["records"]), len(ELEMENT_WEIGHTS))
        self.assertAlmostEqual(report["retained_fraction"], 0.0, places=9)

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(
            assess_reduced_campaign("p", "severe", full_campaign())["verdict"]
        )
        seen.add(assess_reduced_campaign("p", "benign", [])["verdict"])
        seen.add(
            assess_reduced_campaign(
                "p",
                "benign",
                full_campaign(
                    **{"endurance-sample": {"extent": "covered-by-manufacturer-data"}}
                ),
            )["verdict"]
        )
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_element_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_reduced_campaign(
                "cots-ldo-03",
                "benign",
                [
                    {"element": "endurance-sample", "extent": "performed-in-full"},
                    {"element": "endurance-sample", "extent": "performed-in-full"},
                ],
            )

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_reduced_campaign("   ", "benign", full_campaign())

    def test_non_sequence_element_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_reduced_campaign("cots-ldo-03", "benign", {"element": "endurance-sample"})

    def test_tolerance_is_small_enough_to_leave_the_allowance_meaningful(self):
        self.assertGreater(WEIGHT_TOLERANCE, 0.0)
        self.assertLess(WEIGHT_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
