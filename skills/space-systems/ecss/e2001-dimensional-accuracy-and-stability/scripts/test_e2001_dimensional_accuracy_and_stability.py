#!/usr/bin/env python3
"""Contract test for the clause 5.3.3.2 worst case gap dimension logic."""

import unittest

from e2001_dimensional_accuracy_and_stability_logic import (
    assess_gap_dimension,
    assess_gap_set,
    categorize_mechanism,
    combine_contributions,
    contributions_missing_evidence,
    derive_worst_case_gap,
    excursion_within_allowance,
    frequency_gap_product_interval,
    interval_reaches_band,
    validate_contribution,
)


def machining(minus=0.02, plus=0.02, evidence="measured", distribution="systematic"):
    return {
        "mechanism": "machining-tolerance",
        "minus_mm": minus,
        "plus_mm": plus,
        "evidence": evidence,
        "distribution": distribution,
    }


def thermal(minus=0.03, plus=0.01, evidence="analysis", distribution="systematic"):
    return {
        "mechanism": "thermo-elastic-expansion",
        "minus_mm": minus,
        "plus_mm": plus,
        "evidence": evidence,
        "distribution": distribution,
    }


class MechanismCategoryTests(unittest.TestCase):
    def test_machining_tolerance_is_manufacturing_accuracy(self):
        self.assertEqual(
            categorize_mechanism("machining-tolerance"), "manufacturing-accuracy"
        )

    def test_thermo_elastic_expansion_is_in_service_stability(self):
        self.assertEqual(
            categorize_mechanism("thermo-elastic-expansion"), "in-service-stability"
        )

    def test_mechanism_lookup_is_case_and_space_insensitive(self):
        self.assertEqual(
            categorize_mechanism("  Material-Creep "), "in-service-stability"
        )

    def test_unknown_mechanism_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_mechanism("gremlin-drift")

    def test_empty_mechanism_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_mechanism("   ")


class ContributionValidationTests(unittest.TestCase):
    def test_valid_contribution_is_normalized_with_family(self):
        entry = validate_contribution(machining())
        self.assertEqual(entry["family"], "manufacturing-accuracy")
        self.assertAlmostEqual(entry["minus_mm"], 0.02)

    def test_distribution_defaults_to_systematic(self):
        entry = validate_contribution(
            {"mechanism": "joint-settling", "minus_mm": 0.01, "evidence": "analysis"}
        )
        self.assertEqual(entry["distribution"], "systematic")

    def test_non_mapping_contribution_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_contribution(["machining-tolerance", 0.02])

    def test_negative_excursion_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_contribution(machining(minus=-0.01))

    def test_zero_excursion_contribution_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_contribution(machining(minus=0.0, plus=0.0))

    def test_non_numeric_excursion_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_contribution(machining(minus="0.02"))

    def test_bad_distribution_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_contribution(machining(distribution="gaussian-ish"))

    def test_bad_evidence_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_contribution(machining(evidence="rumour"))

    def test_absent_evidence_is_allowed_but_recorded_as_none(self):
        entry = validate_contribution(
            {"mechanism": "material-creep", "minus_mm": 0.004, "plus_mm": 0.0}
        )
        self.assertIsNone(entry["evidence"])


class StackingTests(unittest.TestCase):
    def test_arithmetic_stack_sums_every_term_linearly(self):
        stack = combine_contributions([machining(), thermal()], method="arithmetic")
        self.assertAlmostEqual(stack["minus_mm"], 0.05)
        self.assertAlmostEqual(stack["plus_mm"], 0.03)

    def test_statistical_stack_root_sum_squares_random_terms(self):
        stack = combine_contributions(
            [
                machining(minus=0.03, plus=0.03, distribution="random"),
                thermal(minus=0.04, plus=0.0, distribution="random"),
            ],
            method="statistical",
        )
        self.assertAlmostEqual(stack["minus_mm"], 0.05)
        self.assertAlmostEqual(stack["plus_mm"], 0.03)

    def test_statistical_stack_keeps_systematic_terms_linear(self):
        stack = combine_contributions(
            [
                machining(minus=0.03, plus=0.0, distribution="systematic"),
                thermal(minus=0.04, plus=0.0, distribution="random"),
            ],
            method="statistical",
        )
        self.assertAlmostEqual(stack["minus_mm"], 0.07)
        self.assertAlmostEqual(stack["systematic_minus_mm"], 0.03)
        self.assertAlmostEqual(stack["random_minus_mm"], 0.04)

    def test_arithmetic_stack_ignores_the_random_marking(self):
        stack = combine_contributions(
            [
                machining(minus=0.03, plus=0.0, distribution="random"),
                thermal(minus=0.04, plus=0.0, distribution="random"),
            ],
            method="arithmetic",
        )
        self.assertAlmostEqual(stack["minus_mm"], 0.07)

    def test_unknown_stack_method_is_rejected(self):
        with self.assertRaises(ValueError):
            combine_contributions([machining()], method="monte-carlo")

    def test_empty_contribution_list_is_rejected(self):
        with self.assertRaises(ValueError):
            combine_contributions([], method="arithmetic")


class WorstCaseGapTests(unittest.TestCase):
    def test_bounds_are_nominal_minus_and_plus_the_stack(self):
        worst = derive_worst_case_gap(1.0, [machining(), thermal()])
        self.assertAlmostEqual(worst["minimum_mm"], 0.95)
        self.assertAlmostEqual(worst["maximum_mm"], 1.03)
        self.assertAlmostEqual(worst["excursion_mm"], 0.08)

    def test_both_families_are_counted(self):
        worst = derive_worst_case_gap(1.0, [machining(), thermal()])
        self.assertEqual(worst["families"]["manufacturing-accuracy"], 1)
        self.assertEqual(worst["families"]["in-service-stability"], 1)

    def test_non_positive_nominal_is_rejected(self):
        with self.assertRaises(ValueError):
            derive_worst_case_gap(0.0, [machining()])

    def test_stack_up_that_closes_the_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            derive_worst_case_gap(0.05, [machining(minus=0.05, plus=0.01)])

    def test_stack_up_beyond_closure_is_rejected(self):
        with self.assertRaises(ValueError):
            derive_worst_case_gap(0.05, [machining(minus=0.20, plus=0.01)])

    def test_missing_evidence_is_reported_per_mechanism(self):
        worst = derive_worst_case_gap(
            1.0,
            [machining(evidence=None), thermal()],
        )
        self.assertEqual(contributions_missing_evidence(worst), ["machining-tolerance"])


class AllowanceTests(unittest.TestCase):
    def test_excursion_inside_the_allowance_passes(self):
        worst = derive_worst_case_gap(1.0, [machining(), thermal()])
        self.assertTrue(excursion_within_allowance(worst, 0.10))

    def test_excursion_exactly_on_the_allowance_passes_despite_float_error(self):
        worst = derive_worst_case_gap(
            1.0, [machining(minus=0.15, plus=0.15), thermal(minus=0.15, plus=0.15)]
        )
        self.assertGreater(worst["excursion_mm"], 0.6)
        self.assertTrue(excursion_within_allowance(worst, 0.6))

    def test_excursion_beyond_the_allowance_fails(self):
        worst = derive_worst_case_gap(1.0, [machining(), thermal()])
        self.assertFalse(excursion_within_allowance(worst, 0.05))

    def test_negative_allowance_is_rejected(self):
        worst = derive_worst_case_gap(1.0, [machining()])
        with self.assertRaises(ValueError):
            excursion_within_allowance(worst, -0.01)


class FrequencyGapProductTests(unittest.TestCase):
    def test_interval_scales_both_bounds_by_frequency(self):
        worst = derive_worst_case_gap(1.0, [machining(), thermal()])
        low, high = frequency_gap_product_interval(worst, 12.0)
        self.assertAlmostEqual(low, 11.4)
        self.assertAlmostEqual(high, 12.36)

    def test_non_positive_frequency_is_rejected(self):
        worst = derive_worst_case_gap(1.0, [machining()])
        with self.assertRaises(ValueError):
            frequency_gap_product_interval(worst, 0.0)

    def test_inverted_gap_band_is_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_interval({"minimum_mm": 2.0, "maximum_mm": 1.0}, 10.0)

    def test_interval_inside_the_band_reaches_it(self):
        self.assertTrue(interval_reaches_band((5.0, 8.0), (1.0, 20.0)))

    def test_interval_entirely_above_the_band_does_not_reach_it(self):
        self.assertFalse(interval_reaches_band((40.0, 45.0), (1.0, 20.0)))

    def test_interval_entirely_below_the_band_does_not_reach_it(self):
        self.assertFalse(interval_reaches_band((0.1, 0.4), (1.0, 20.0)))

    def test_interval_touching_the_band_edge_reaches_it(self):
        self.assertTrue(interval_reaches_band((20.0, 31.0), (1.0, 20.0)))

    def test_inverted_susceptibility_band_is_rejected(self):
        with self.assertRaises(ValueError):
            interval_reaches_band((5.0, 8.0), (20.0, 1.0))


class GapAssessmentTests(unittest.TestCase):
    def base_gap(self, **over):
        gap = {
            "name": "filter-post-to-lid",
            "nominal_mm": 1.0,
            "frequency_ghz": 12.0,
            "contributions": [machining(), thermal()],
            "method": "arithmetic",
            "stability_allowance_mm": 0.10,
            "susceptibility_band": (1.0, 20.0),
        }
        gap.update(over)
        return gap

    def test_complete_gap_is_accepted_and_flagged_critical(self):
        result = assess_gap_dimension(self.base_gap())
        self.assertTrue(result["dimension_accepted"])
        self.assertEqual(result["verdict"], "multipactor-critical")
        self.assertEqual(result["findings"], [])

    def test_gap_above_the_band_is_outside_the_susceptible_region(self):
        result = assess_gap_dimension(
            self.base_gap(nominal_mm=4.0, frequency_ghz=30.0, susceptibility_band=(1.0, 20.0))
        )
        self.assertEqual(result["verdict"], "outside-susceptibility-band")

    def test_missing_stability_family_is_a_finding(self):
        result = assess_gap_dimension(self.base_gap(contributions=[machining()]))
        self.assertIn("in-service-stability-family-absent", result["findings"])
        self.assertFalse(result["dimension_accepted"])

    def test_missing_manufacturing_family_is_a_finding(self):
        result = assess_gap_dimension(self.base_gap(contributions=[thermal()]))
        self.assertIn("manufacturing-accuracy-family-absent", result["findings"])

    def test_absent_susceptibility_band_is_a_finding_and_stays_critical(self):
        gap = self.base_gap()
        del gap["susceptibility_band"]
        result = assess_gap_dimension(gap)
        self.assertIn("susceptibility-band-absent", result["findings"])
        self.assertEqual(result["verdict"], "multipactor-critical")

    def test_allowance_exceedance_is_a_finding(self):
        result = assess_gap_dimension(self.base_gap(stability_allowance_mm=0.01))
        self.assertIn("stability-allowance-exceeded", result["findings"])

    def test_unnamed_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_dimension(self.base_gap(name="  "))

    def test_non_mapping_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_dimension(["filter-post-to-lid"])

    def test_set_is_accepted_when_every_gap_is_clean(self):
        summary = assess_gap_set([self.base_gap(), self.base_gap(name="iris-to-wall")])
        self.assertTrue(summary["set_accepted"])
        self.assertEqual(len(summary["critical_gaps"]), 2)

    def test_set_carries_findings_prefixed_by_gap_name(self):
        summary = assess_gap_set(
            [self.base_gap(), self.base_gap(name="iris-to-wall", contributions=[machining()])]
        )
        self.assertFalse(summary["set_accepted"])
        self.assertIn(
            "iris-to-wall:in-service-stability-family-absent", summary["open_findings"]
        )

    def test_duplicate_gap_names_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_set([self.base_gap(), self.base_gap()])

    def test_empty_gap_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_set([])


if __name__ == "__main__":
    unittest.main()
