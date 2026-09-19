"""Contract tests for the clause 5.8.6 ground network availability logic."""

import math
import unittest

from e50_ground_network_availability_logic import (
    COMPLIANT,
    MARGINAL,
    NON_COMPLIANT,
    SECONDS_PER_YEAR,
    allowed_outage_seconds,
    apportion_series_availability,
    assess_ground_network_availability,
    element_availability,
    inherent_availability,
    operational_availability,
    redundant_group_availability,
    required_mttr,
    series_availability,
    unavailability_contributions,
    validate_availability,
    validate_element,
    validate_non_negative,
    validate_positive,
)

HOUR = 3600.0
CHAIN = [
    {"name": "antenna", "availability": 0.999},
    {"name": "modem", "availability": 0.9995},
    {"name": "wan-link", "availability": 0.998},
]


class ValidationTests(unittest.TestCase):
    def test_zero_availability_accepted(self):
        self.assertAlmostEqual(validate_availability(0), 0.0, places=9)

    def test_availability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_availability(1.5)

    def test_boolean_availability_rejected(self):
        with self.assertRaises(ValueError):
            validate_availability(True)

    def test_text_availability_rejected(self):
        with self.assertRaises(ValueError):
            validate_availability("0.999")

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(float("nan"))

    def test_zero_rejected_where_positive_required(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0)

    def test_element_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_element({"availability": 0.99})

    def test_element_without_a_source_of_availability_rejected(self):
        with self.assertRaises(ValueError):
            validate_element({"name": "modem"})

    def test_element_with_fractional_redundancy_rejected(self):
        with self.assertRaises(ValueError):
            validate_element({"name": "modem", "availability": 0.99, "redundancy": 1.5})

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            element_availability(["modem", 0.99])


class ElementTests(unittest.TestCase):
    def test_inherent_availability_from_mtbf_and_mttr(self):
        self.assertAlmostEqual(inherent_availability(99.0, 1.0), 0.99, places=9)

    def test_instant_repair_is_full_availability(self):
        self.assertAlmostEqual(inherent_availability(1000.0, 0.0), 1.0, places=9)

    def test_preventive_downtime_lowers_the_figure(self):
        self.assertLess(
            operational_availability(99.0, 1.0, 1.0), inherent_availability(99.0, 1.0)
        )

    def test_operational_matches_inherent_with_no_preventive(self):
        self.assertAlmostEqual(
            operational_availability(99.0, 1.0, 0.0),
            inherent_availability(99.0, 1.0),
            places=9,
        )

    def test_zero_mtbf_rejected(self):
        with self.assertRaises(ValueError):
            inherent_availability(0.0, 1.0)

    def test_element_from_mtbf_pair(self):
        self.assertAlmostEqual(
            element_availability({"name": "modem", "mtbf_s": 99.0, "mttr_s": 1.0}),
            0.99,
            places=9,
        )

    def test_redundant_element_beats_its_member(self):
        single = element_availability({"name": "modem", "availability": 0.99})
        pair = element_availability(
            {"name": "modem", "availability": 0.99, "redundancy": 2}
        )
        self.assertAlmostEqual(pair, 1.0 - (1.0 - single) ** 2, places=9)


class CompositionTests(unittest.TestCase):
    def test_series_multiplies(self):
        self.assertAlmostEqual(series_availability([0.9, 0.9]), 0.81, places=9)

    def test_series_of_one_is_the_element(self):
        self.assertAlmostEqual(series_availability([0.987]), 0.987, places=9)

    def test_series_is_worse_than_its_worst_member(self):
        self.assertLess(series_availability([0.9, 0.99]), 0.9)

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            series_availability([])

    def test_string_series_rejected(self):
        with self.assertRaises(ValueError):
            series_availability("0.99")

    def test_redundant_group_beats_its_members(self):
        self.assertAlmostEqual(
            redundant_group_availability([0.9, 0.9]), 0.99, places=9
        )

    def test_redundant_group_of_one_is_the_member(self):
        self.assertAlmostEqual(redundant_group_availability([0.9]), 0.9, places=9)

    def test_empty_redundant_group_rejected(self):
        with self.assertRaises(ValueError):
            redundant_group_availability([])


class BudgetTests(unittest.TestCase):
    def test_outage_seconds_follow_the_availability(self):
        self.assertAlmostEqual(allowed_outage_seconds(0.99, 100.0), 1.0, places=9)

    def test_full_availability_allows_no_outage(self):
        self.assertAlmostEqual(allowed_outage_seconds(1.0, HOUR), 0.0, places=9)

    def test_a_year_is_the_default_period(self):
        self.assertAlmostEqual(
            allowed_outage_seconds(0.99), 0.01 * SECONDS_PER_YEAR, places=6
        )

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            allowed_outage_seconds(0.99, 0.0)


class ApportionmentTests(unittest.TestCase):
    def test_apportionment_composes_back_to_the_target(self):
        per = apportion_series_availability(0.99, 4)
        self.assertAlmostEqual(series_availability([per] * 4), 0.99, places=9)

    def test_one_element_takes_the_whole_target(self):
        self.assertAlmostEqual(apportion_series_availability(0.99, 1), 0.99, places=9)

    def test_more_elements_ask_more_of_each(self):
        self.assertGreater(
            apportion_series_availability(0.99, 8),
            apportion_series_availability(0.99, 2),
        )

    def test_zero_element_count_rejected(self):
        with self.assertRaises(ValueError):
            apportion_series_availability(0.99, 0)

    def test_required_mttr_reaches_the_target(self):
        mttr = required_mttr(99.0, 0.99)
        self.assertAlmostEqual(inherent_availability(99.0, mttr), 0.99, places=9)

    def test_a_perfect_target_admits_no_finite_repair_time(self):
        with self.assertRaises(ValueError):
            required_mttr(99.0, 1.0)

    def test_a_zero_target_needs_unbounded_repair_time(self):
        self.assertTrue(math.isinf(required_mttr(99.0, 0.0)))


class ContributionTests(unittest.TestCase):
    def test_worst_element_sorts_first(self):
        rows = unavailability_contributions(CHAIN)
        self.assertEqual(rows[0]["name"], "wan-link")

    def test_shares_sum_to_one(self):
        rows = unavailability_contributions(CHAIN)
        self.assertAlmostEqual(sum(row["share"] for row in rows), 1.0, places=9)

    def test_a_perfect_chain_has_no_shares(self):
        rows = unavailability_contributions([{"name": "a", "availability": 1.0}])
        self.assertAlmostEqual(rows[0]["share"], 0.0, places=9)

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            unavailability_contributions([])


class AssessTests(unittest.TestCase):
    def test_a_chain_with_headroom_is_compliant(self):
        result = assess_ground_network_availability(CHAIN, 0.99)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_a_chain_exactly_on_its_requirement_is_compliant_without_margin(self):
        chain = [{"name": "only", "availability": 0.995}]
        result = assess_ground_network_availability(chain, 0.995)
        self.assertAlmostEqual(
            result["achieved_availability"], result["required_availability"], places=9
        )
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_a_chain_exactly_on_its_requirement_is_marginal_with_margin(self):
        chain = [{"name": "only", "availability": 0.995}]
        result = assess_ground_network_availability(chain, 0.995, margin_factor=2.0)
        self.assertEqual(result["verdict"], MARGINAL)

    def test_a_chain_exactly_on_the_headroom_bound_is_compliant(self):
        chain = [{"name": "only", "availability": 0.9975}]
        result = assess_ground_network_availability(chain, 0.995, margin_factor=2.0)
        self.assertAlmostEqual(
            result["achieved_availability"], result["goal_availability"], places=9
        )
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_a_chain_below_its_requirement_fails(self):
        result = assess_ground_network_availability(CHAIN, 0.9999)
        self.assertEqual(result["verdict"], NON_COMPLIANT)
        self.assertTrue(
            any("does not meet the stated availability" in f for f in result["findings"])
        )

    def test_a_failing_chain_names_where_the_budget_goes(self):
        result = assess_ground_network_availability(CHAIN, 0.9999)
        self.assertEqual(result["worst_element"], "wan-link")
        self.assertTrue(any("budget goes first" in f for f in result["findings"]))

    def test_the_stated_apportionment_actually_meets_the_target(self):
        result = assess_ground_network_availability(CHAIN, 0.9999)
        per = result["per_element_apportionment"]
        fixed = assess_ground_network_availability(
            [{"name": row["name"], "availability": per} for row in result["elements"]],
            0.9999,
        )
        self.assertEqual(fixed["verdict"], COMPLIANT)

    def test_redundancy_rescues_a_failing_element(self):
        bare = assess_ground_network_availability(
            [{"name": "wan-link", "availability": 0.99}], 0.9999
        )
        doubled = assess_ground_network_availability(
            [{"name": "wan-link", "availability": 0.99, "redundancy": 2}], 0.9999
        )
        self.assertEqual(bare["verdict"], NON_COMPLIANT)
        self.assertEqual(doubled["verdict"], COMPLIANT)

    def test_outage_seconds_are_carried_both_ways(self):
        result = assess_ground_network_availability(CHAIN, 0.99, period_s=SECONDS_PER_YEAR)
        self.assertLess(
            result["outage_seconds_per_period"],
            result["allowed_outage_seconds_per_period"],
        )

    def test_period_changes_the_outage_figure_not_the_verdict(self):
        year = assess_ground_network_availability(CHAIN, 0.99)
        day = assess_ground_network_availability(CHAIN, 0.99, period_s=86400.0)
        self.assertEqual(year["verdict"], day["verdict"])
        self.assertGreater(
            year["outage_seconds_per_period"], day["outage_seconds_per_period"]
        )

    def test_bad_margin_factor_rejected(self):
        with self.assertRaises(ValueError):
            assess_ground_network_availability(CHAIN, 0.99, margin_factor=0.5)

    def test_bad_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_ground_network_availability(CHAIN, 1.5)

    def test_bad_element_rejected(self):
        with self.assertRaises(ValueError):
            assess_ground_network_availability([{"name": "x"}], 0.99)


if __name__ == "__main__":
    unittest.main()
