"""Contract tests for the clause 12.5.5 qualification sizing and coverage leaf.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused policy, a plan
declaring no minimum quantity, an owed test never booked, a test booked
below its minimum, an allocation booked to a test nobody owed, and a
qualification lot too small to feed the destructive tests plus the largest
non-destructive draw.
"""

import unittest

from e2008_blocking_diode_qualification_testing_logic import (
    ALLOCATION_BOOKED_TO_UNOWED_TEST,
    DEFAULT_QUALIFICATION_POLICY,
    MINIMUM_QUANTITIES_NOT_DECLARED,
    OWED_TEST_NOT_BOOKED,
    QUALIFICATION_LOT_INSUFFICIENT,
    QUALIFICATION_LOT_NOT_DECLARED,
    QUALIFICATION_SAMPLE_SHORTFALL,
    SAMPLE_QUANTITY_SHORT,
    TESTING_MEETS_MINIMUMS,
    allocation_map,
    allocation_shortfall,
    assess_qualification_testing,
    destructive_sample_demand,
    lot_is_sufficient,
    marginal_allocation_advisories,
    minimum_quantity_coverage,
    required_lot_size,
    required_lot_with_reserve,
    shared_sample_demand,
    test_allocation_verdicts,
    unowed_allocations,
    validate_allocation,
    validate_qualification_policy,
    validate_requirements,
    validate_test_requirement,
    worst_shortfall_test,
)

REVERSE_CURRENT = "blocking-diode-reverse-current-measurement"
FORWARD_VOLTAGE = "blocking-diode-forward-voltage-measurement"
THERMAL_CYCLING = "blocking-diode-thermal-cycling"
LIFE_TEST = "blocking-diode-life-test"
BOND_PULL = "blocking-diode-bond-pull"


def _policy(**overrides):
    policy = dict(DEFAULT_QUALIFICATION_POLICY)
    policy.update(overrides)
    return policy


def _requirements():
    return [
        {"test": REVERSE_CURRENT, "minimum_samples": 10, "destructive": False},
        {"test": FORWARD_VOLTAGE, "minimum_samples": 10, "destructive": False},
        {"test": THERMAL_CYCLING, "minimum_samples": 6, "destructive": False},
        {"test": LIFE_TEST, "minimum_samples": 5, "destructive": True},
        {"test": BOND_PULL, "minimum_samples": 4, "destructive": True},
    ]


def _allocations():
    return [
        {"test": REVERSE_CURRENT, "allocated_samples": 12},
        {"test": FORWARD_VOLTAGE, "allocated_samples": 12},
        {"test": THERMAL_CYCLING, "allocated_samples": 8},
        {"test": LIFE_TEST, "allocated_samples": 8},
        {"test": BOND_PULL, "allocated_samples": 7},
    ]


def _case(**overrides):
    case = {
        "test_requirements": _requirements(),
        "allocations": _allocations(),
        "qualification_lot_size": 32,
    }
    case.update(overrides)
    return case


def _verdicts():
    return test_allocation_verdicts(_requirements(), _allocations())


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        checked = validate_qualification_policy(DEFAULT_QUALIFICATION_POLICY)
        self.assertAlmostEqual(checked["lot_reserve_fraction"], 0.1, places=12)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_qualification_policy("lot_reserve_fraction")

    def test_a_reserve_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_qualification_policy(_policy(lot_reserve_fraction=1.5))

    def test_a_negative_reserve_rejected(self):
        with self.assertRaises(ValueError):
            validate_qualification_policy(_policy(lot_reserve_fraction=-0.2))

    def test_a_fractional_marginal_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_qualification_policy(_policy(marginal_allocation_margin=1.5))

    def test_a_zero_reserve_is_a_legitimate_policy(self):
        checked = validate_qualification_policy(_policy(lot_reserve_fraction=0.0))
        self.assertAlmostEqual(checked["lot_reserve_fraction"], 0.0, places=12)


class RequirementTests(unittest.TestCase):
    def test_an_owed_test_validates(self):
        entry = validate_test_requirement(_requirements()[0])
        self.assertEqual(entry["test"], REVERSE_CURRENT)
        self.assertEqual(entry["minimum_samples"], 10)
        self.assertFalse(entry["destructive"])

    def test_a_minimum_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_requirement(
                {"test": LIFE_TEST, "minimum_samples": 0, "destructive": True}
            )

    def test_a_fractional_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_requirement(
                {"test": LIFE_TEST, "minimum_samples": 4.5, "destructive": True}
            )

    def test_a_missing_destructive_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_requirement({"test": LIFE_TEST, "minimum_samples": 5})

    def test_a_blank_test_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_requirement(
                {"test": "  ", "minimum_samples": 5, "destructive": True}
            )

    def test_an_empty_owed_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([])

    def test_a_test_owed_twice_rejected(self):
        requirements = _requirements()
        requirements.append(dict(requirements[0]))
        with self.assertRaises(ValueError):
            validate_requirements(requirements)


class AllocationTests(unittest.TestCase):
    def test_an_allocation_validates(self):
        entry = validate_allocation(_allocations()[0])
        self.assertEqual(entry["allocated_samples"], 12)

    def test_a_negative_allocation_rejected(self):
        with self.assertRaises(ValueError):
            validate_allocation({"test": LIFE_TEST, "allocated_samples": -2})

    def test_a_test_booked_twice_rejected(self):
        allocations = _allocations()
        allocations.append({"test": LIFE_TEST, "allocated_samples": 3})
        with self.assertRaises(ValueError):
            allocation_map(allocations)

    def test_a_shortfall_is_the_missing_sample_count(self):
        self.assertEqual(allocation_shortfall(10, 7), 3)

    def test_a_surplus_is_not_a_negative_shortfall(self):
        self.assertEqual(allocation_shortfall(10, 14), 0)

    def test_an_allocation_exactly_on_the_minimum_is_admitted(self):
        self.assertEqual(allocation_shortfall(10, 10), 0)

    def test_an_allocation_to_an_unowed_test_is_named(self):
        allocations = _allocations()
        allocations.append(
            {"test": "blocking-diode-solderability", "allocated_samples": 3}
        )
        self.assertEqual(
            unowed_allocations(_requirements(), allocations),
            ("blocking-diode-solderability",),
        )


class VerdictTests(unittest.TestCase):
    def test_a_well_fed_campaign_meets_every_minimum(self):
        verdicts = _verdicts()
        self.assertTrue(all(v["meets_minimum"] for v in verdicts))
        self.assertAlmostEqual(minimum_quantity_coverage(verdicts), 1.0, places=12)

    def test_an_owed_test_never_booked_is_its_own_finding(self):
        allocations = [a for a in _allocations() if a["test"] != BOND_PULL]
        verdicts = test_allocation_verdicts(_requirements(), allocations)
        pulled = [v for v in verdicts if v["test"] == BOND_PULL][0]
        self.assertIn(OWED_TEST_NOT_BOOKED, pulled["reasons"])
        self.assertNotIn(SAMPLE_QUANTITY_SHORT, pulled["reasons"])
        self.assertEqual(pulled["shortfall"], 4)

    def test_an_underfed_test_is_short_rather_than_unbooked(self):
        allocations = _allocations()
        allocations[3]["allocated_samples"] = 2
        verdicts = test_allocation_verdicts(_requirements(), allocations)
        life = [v for v in verdicts if v["test"] == LIFE_TEST][0]
        self.assertIn(SAMPLE_QUANTITY_SHORT, life["reasons"])
        self.assertEqual(life["shortfall"], 3)

    def test_coverage_is_the_share_of_tests_reaching_their_minimum(self):
        allocations = _allocations()
        allocations[3]["allocated_samples"] = 2
        verdicts = test_allocation_verdicts(_requirements(), allocations)
        self.assertAlmostEqual(minimum_quantity_coverage(verdicts), 0.8, places=12)

    def test_the_worst_shortfall_test_is_the_furthest_short(self):
        allocations = _allocations()
        allocations[0]["allocated_samples"] = 9
        allocations[3]["allocated_samples"] = 1
        verdicts = test_allocation_verdicts(_requirements(), allocations)
        self.assertEqual(worst_shortfall_test(verdicts)["test"], LIFE_TEST)

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_shortfall_test([])


class LotSizingTests(unittest.TestCase):
    def test_destructive_allocations_add_up(self):
        self.assertEqual(destructive_sample_demand(_verdicts()), 15)

    def test_non_destructive_allocations_do_not_add_up(self):
        self.assertEqual(shared_sample_demand(_verdicts()), 12)

    def test_a_campaign_with_no_surviving_test_needs_no_shared_draw(self):
        requirements = [
            {"test": LIFE_TEST, "minimum_samples": 5, "destructive": True},
        ]
        allocations = [{"test": LIFE_TEST, "allocated_samples": 5}]
        verdicts = test_allocation_verdicts(requirements, allocations)
        self.assertEqual(shared_sample_demand(verdicts), 0)

    def test_the_required_lot_is_destructive_plus_the_largest_shared_draw(self):
        self.assertEqual(required_lot_size(_verdicts()), 27)

    def test_the_reserve_is_applied_on_top_of_the_required_lot(self):
        self.assertAlmostEqual(
            required_lot_with_reserve(_verdicts()), 29.7, places=9
        )

    def test_a_lot_exactly_on_the_requirement_is_sufficient_without_reserve(self):
        self.assertTrue(
            lot_is_sufficient(27, _verdicts(), _policy(lot_reserve_fraction=0.0))
        )

    def test_a_lot_one_part_short_is_insufficient(self):
        self.assertFalse(
            lot_is_sufficient(26, _verdicts(), _policy(lot_reserve_fraction=0.0))
        )

    def test_a_fractional_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            lot_is_sufficient(27.5, _verdicts())

    def test_a_test_booked_at_its_bare_minimum_raises_an_advisory(self):
        allocations = _allocations()
        allocations[4]["allocated_samples"] = 4
        verdicts = test_allocation_verdicts(_requirements(), allocations)
        advisories = marginal_allocation_advisories(verdicts)
        self.assertEqual(len(advisories), 1)
        self.assertIn(BOND_PULL, advisories[0])

    def test_a_comfortable_campaign_raises_no_advisory(self):
        self.assertEqual(marginal_allocation_advisories(_verdicts()), ())


class AssessmentTests(unittest.TestCase):
    def test_a_sized_campaign_meets_the_minimums(self):
        result = assess_qualification_testing(_case())
        self.assertEqual(result["verdict"], TESTING_MEETS_MINIMUMS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["tests_meeting_minimum"]), 5)

    def test_no_declared_minimum_closes_the_assessment(self):
        case = _case()
        del case["test_requirements"]
        result = assess_qualification_testing(case)
        self.assertEqual(result["verdict"], MINIMUM_QUANTITIES_NOT_DECLARED)
        self.assertTrue(result["findings"])

    def test_an_underfed_test_fails_the_campaign(self):
        allocations = _allocations()
        allocations[3]["allocated_samples"] = 2
        result = assess_qualification_testing(_case(allocations=allocations))
        self.assertEqual(result["verdict"], QUALIFICATION_SAMPLE_SHORTFALL)
        self.assertIn(LIFE_TEST, result["tests_short"])

    def test_every_short_test_is_reported_not_only_the_first(self):
        allocations = _allocations()
        allocations[0]["allocated_samples"] = 3
        allocations[3]["allocated_samples"] = 1
        result = assess_qualification_testing(_case(allocations=allocations))
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_an_unowed_allocation_is_reported(self):
        allocations = _allocations()
        allocations.append(
            {"test": "blocking-diode-solderability", "allocated_samples": 3}
        )
        result = assess_qualification_testing(_case(allocations=allocations))
        self.assertEqual(
            result["unowed_allocations"], ("blocking-diode-solderability",)
        )
        self.assertTrue(
            any(
                ALLOCATION_BOOKED_TO_UNOWED_TEST in line
                for line in result["findings"]
            )
        )

    def test_a_missing_lot_size_closes_the_assessment(self):
        case = _case()
        del case["qualification_lot_size"]
        result = assess_qualification_testing(case)
        self.assertEqual(result["verdict"], QUALIFICATION_LOT_NOT_DECLARED)

    def test_a_lot_too_small_to_feed_the_campaign_fails(self):
        result = assess_qualification_testing(_case(qualification_lot_size=18))
        self.assertEqual(result["verdict"], QUALIFICATION_LOT_INSUFFICIENT)
        self.assertEqual(result["required_lot_size"], 27)

    def test_the_lot_arithmetic_travels_with_the_verdict(self):
        result = assess_qualification_testing(_case())
        self.assertEqual(result["destructive_sample_demand"], 15)
        self.assertEqual(result["shared_sample_demand"], 12)
        self.assertAlmostEqual(
            result["required_lot_with_reserve"], 29.7, places=9
        )

    def test_advisories_do_not_move_the_verdict(self):
        allocations = _allocations()
        allocations[4]["allocated_samples"] = 4
        result = assess_qualification_testing(_case(allocations=allocations))
        self.assertEqual(result["verdict"], TESTING_MEETS_MINIMUMS)
        self.assertEqual(len(result["advisories"]), 1)

    def test_coverage_is_reported(self):
        result = assess_qualification_testing(_case())
        self.assertAlmostEqual(result["minimum_quantity_coverage"], 1.0, places=12)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_testing(["test_requirements"])


if __name__ == "__main__":
    unittest.main()
