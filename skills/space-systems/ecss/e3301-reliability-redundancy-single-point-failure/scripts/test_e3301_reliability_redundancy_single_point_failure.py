#!/usr/bin/env python3
"""Contract test for the mechanism reliability and SPF ledger (offline)."""

import copy
import math
import unittest

from e3301_reliability_redundancy_single_point_failure_logic import (
    CRITICALITY_LEVELS,
    DEFAULT_RELIABILITY_POLICY,
    DISPOSITIONS,
    REDUNDANCY_SCHEMES,
    assess_reliability_case,
    block_reliability,
    disposition_of,
    mechanism_reliability,
    redundancy_order,
    reliability_margin,
    single_point_failures,
    validate_block,
    validate_reliability_policy,
)

RATIONALE = "wear-out mode retired by a qualification life test to four times mission"


def block(
    identifier,
    fit=1.0e4,
    scheme="simplex",
    units=1,
    criticality="mission-critical",
    active_element=False,
    disposition="eliminated",
    rationale="",
):
    return {
        "id": identifier,
        "failure_rate_fit": fit,
        "scheme": scheme,
        "units": units,
        "criticality": criticality,
        "active_element": active_element,
        "disposition": disposition,
        "rationale": rationale,
    }


GOOD_CASE = {
    "mission_hours": 5000.0,
    "required_mission_reliability": 0.90,
    "blocks": [
        block("hold-down-release", fit=8.0e3, scheme="active-parallel", units=2,
              active_element=True),
        block("drive-motor", fit=6.0e3, scheme="cold-standby", units=2,
              active_element=True),
        block("harness", fit=1.0e3, criticality="mission-degrading"),
    ],
}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_reliability_policy(DEFAULT_RELIABILITY_POLICY),
            DEFAULT_RELIABILITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability_policy("default")

    def test_out_of_range_required_reliability_rejected(self):
        broken = copy.deepcopy(DEFAULT_RELIABILITY_POLICY)
        broken["required_mission_reliability"] = 1.5
        with self.assertRaises(ValueError):
            validate_reliability_policy(broken)

    def test_non_boolean_redundancy_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_RELIABILITY_POLICY)
        broken["active_elements_require_redundancy"] = "yes"
        with self.assertRaises(ValueError):
            validate_reliability_policy(broken)

    def test_zero_rationale_length_rejected(self):
        broken = copy.deepcopy(DEFAULT_RELIABILITY_POLICY)
        broken["minimum_rationale_characters"] = 0
        with self.assertRaises(ValueError):
            validate_reliability_policy(broken)


class BlockValidationTests(unittest.TestCase):
    def test_every_scheme_is_named(self):
        self.assertEqual(len(REDUNDANCY_SCHEMES), 3)

    def test_every_criticality_level_is_named(self):
        self.assertIn("mission-critical", CRITICALITY_LEVELS)

    def test_every_disposition_is_named(self):
        self.assertEqual(set(DISPOSITIONS), {"eliminated", "accepted", "open"})

    def test_valid_block_is_normalised(self):
        record = validate_block(block("latch"))
        self.assertEqual(record["id"], "latch")
        self.assertEqual(record["units"], 1)

    def test_non_mapping_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_block("latch")

    def test_blank_block_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("   "))

    def test_unknown_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", scheme="hopeful"))

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", criticality="annoying"))

    def test_simplex_with_two_units_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", scheme="simplex", units=2))

    def test_redundant_scheme_with_one_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", scheme="active-parallel", units=1))

    def test_negative_failure_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", fit=-1.0))

    def test_non_boolean_active_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", active_element="yes"))

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_block(block("latch", disposition="probably-fine"))

    def test_redundancy_order_reports_the_unit_count(self):
        self.assertEqual(redundancy_order(block("a", scheme="cold-standby", units=3)), 3)


class BlockReliabilityTests(unittest.TestCase):
    def test_zero_failure_rate_is_certain(self):
        self.assertAlmostEqual(block_reliability(block("a", fit=0.0), 5000.0), 1.0,
                               places=12)

    def test_zero_mission_hours_is_certain(self):
        self.assertAlmostEqual(block_reliability(block("a", fit=1.0e6), 0.0), 1.0,
                               places=12)

    def test_simplex_follows_the_exponential_law(self):
        value = block_reliability(block("a", fit=2.0e4), 5000.0)
        self.assertAlmostEqual(value, math.exp(-0.1), places=12)

    def test_active_parallel_beats_simplex(self):
        simplex = block_reliability(block("a", fit=2.0e4), 5000.0)
        parallel = block_reliability(
            block("a", fit=2.0e4, scheme="active-parallel", units=2), 5000.0
        )
        self.assertGreater(parallel, simplex)

    def test_cold_standby_with_a_perfect_switch_beats_active_parallel(self):
        parallel = block_reliability(
            block("a", fit=2.0e4, scheme="active-parallel", units=2), 5000.0
        )
        standby = block_reliability(
            block("a", fit=2.0e4, scheme="cold-standby", units=2), 5000.0,
            switch_reliability=1.0,
        )
        self.assertGreater(standby, parallel)

    def test_an_imperfect_switch_lowers_cold_standby(self):
        perfect = block_reliability(
            block("a", fit=2.0e4, scheme="cold-standby", units=2), 5000.0,
            switch_reliability=1.0,
        )
        lossy = block_reliability(
            block("a", fit=2.0e4, scheme="cold-standby", units=2), 5000.0,
            switch_reliability=0.5,
        )
        self.assertGreater(perfect, lossy)

    def test_negative_mission_hours_rejected(self):
        with self.assertRaises(ValueError):
            block_reliability(block("a"), -1.0)

    def test_out_of_range_switch_reliability_rejected(self):
        with self.assertRaises(ValueError):
            block_reliability(block("a", scheme="cold-standby", units=2), 100.0,
                              switch_reliability=1.4)


class MechanismReliabilityTests(unittest.TestCase):
    def test_series_chain_multiplies_the_blocks(self):
        chain = [block("a", fit=2.0e4), block("b", fit=3.0e4)]
        value = mechanism_reliability(chain, 5000.0)
        self.assertAlmostEqual(value, math.exp(-0.1) * math.exp(-0.15), places=12)

    def test_adding_a_block_never_raises_the_chain(self):
        short = mechanism_reliability([block("a", fit=2.0e4)], 5000.0)
        longer = mechanism_reliability(
            [block("a", fit=2.0e4), block("b", fit=3.0e4)], 5000.0
        )
        self.assertGreater(short, longer)

    def test_duplicate_block_id_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_reliability([block("a"), block("a")], 100.0)

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_reliability([], 100.0)


class SinglePointFailureTests(unittest.TestCase):
    def test_redundant_critical_block_is_not_a_single_point_failure(self):
        found = single_point_failures(
            [block("a", scheme="active-parallel", units=2, active_element=True)]
        )
        self.assertEqual(found, [])

    def test_simplex_critical_block_is_a_single_point_failure(self):
        found = single_point_failures([block("a")])
        self.assertEqual(len(found), 1)
        self.assertTrue(any("mission-critical" in r for r in found[0]["reasons"]))

    def test_simplex_active_element_is_flagged_even_when_degrading_only(self):
        found = single_point_failures(
            [block("a", criticality="mission-degrading", active_element=True)]
        )
        self.assertEqual(len(found), 1)
        self.assertTrue(any("active element" in r for r in found[0]["reasons"]))

    def test_benign_passive_simplex_block_is_not_flagged(self):
        self.assertEqual(
            single_point_failures([block("a", criticality="benign")]), []
        )

    def test_active_element_rule_can_be_switched_off_by_policy(self):
        policy = copy.deepcopy(DEFAULT_RELIABILITY_POLICY)
        policy["active_elements_require_redundancy"] = False
        found = single_point_failures(
            [block("a", criticality="benign", active_element=True)], policy
        )
        self.assertEqual(found, [])


class DispositionTests(unittest.TestCase):
    def test_eliminated_stays_eliminated(self):
        self.assertEqual(
            disposition_of(block("a", disposition="eliminated"))["disposition"],
            "eliminated",
        )

    def test_acceptance_with_a_rationale_stands(self):
        result = disposition_of(
            block("a", disposition="accepted", rationale=RATIONALE)
        )
        self.assertEqual(result["disposition"], "accepted")
        self.assertEqual(result["findings"], [])

    def test_acceptance_without_a_rationale_is_open(self):
        result = disposition_of(block("a", disposition="accepted", rationale="ok"))
        self.assertEqual(result["disposition"], "open")
        self.assertTrue(result["findings"])

    def test_policy_can_waive_the_rationale_requirement(self):
        policy = copy.deepcopy(DEFAULT_RELIABILITY_POLICY)
        policy["acceptance_requires_rationale"] = False
        result = disposition_of(block("a", disposition="accepted"), policy)
        self.assertEqual(result["disposition"], "accepted")


class MarginTests(unittest.TestCase):
    def test_margin_is_positive_above_the_requirement(self):
        self.assertAlmostEqual(reliability_margin(0.995, 0.99), 0.005, places=12)

    def test_margin_is_negative_below_the_requirement(self):
        self.assertLess(reliability_margin(0.95, 0.99), 0.0)

    def test_margin_rejects_a_value_outside_the_unit_interval(self):
        with self.assertRaises(ValueError):
            reliability_margin(1.2, 0.99)


class AssessmentTests(unittest.TestCase):
    def test_good_case_closes(self):
        result = assess_reliability_case(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "reliability-case-closed")
        self.assertEqual(result["open_single_point_failures"], 0)

    def test_undispositioned_single_point_failure_holds_the_case_open(self):
        case = copy.deepcopy(GOOD_CASE)
        case["blocks"].append(block("gearbox", disposition="open"))
        result = assess_reliability_case(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "single-point-failures-open")
        self.assertEqual(result["open_single_point_failures"], 1)

    def test_accepted_single_point_failure_with_a_rationale_closes(self):
        case = copy.deepcopy(GOOD_CASE)
        case["blocks"].append(
            block("gearbox", fit=5.0e2, disposition="accepted", rationale=RATIONALE)
        )
        result = assess_reliability_case(case)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["accepted_single_point_failures"], 1)

    def test_figure_below_the_apportionment_fails_even_with_a_clean_ledger(self):
        case = copy.deepcopy(GOOD_CASE)
        case["required_mission_reliability"] = 0.9999999
        result = assess_reliability_case(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "reliability-figure-not-met")
        self.assertTrue(any("below the apportioned" in f for f in result["findings"]))

    def test_reliability_exactly_on_the_requirement_is_compliant(self):
        # exp(-a) * exp(-b) and exp(-(a + b)) are equal in mathematics and
        # can differ by one unit in the last place in floating point.
        chain = [block("a", fit=1.0e5), block("b", fit=2.0e5)]
        required = math.exp(-(1.0e5 + 2.0e5) * 1.0e-9 * 1000.0)
        result = assess_reliability_case(
            {
                "mission_hours": 1000.0,
                "required_mission_reliability": required,
                "blocks": chain,
            }
        )
        self.assertAlmostEqual(result["achieved_reliability"], required, places=12)
        self.assertTrue(result["figure_met"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_reliability_case("mechanism")

    def test_missing_mission_hours_rejected(self):
        case = copy.deepcopy(GOOD_CASE)
        del case["mission_hours"]
        with self.assertRaises(ValueError):
            assess_reliability_case(case)

    def test_zero_mission_hours_rejected(self):
        case = copy.deepcopy(GOOD_CASE)
        case["mission_hours"] = 0.0
        with self.assertRaises(ValueError):
            assess_reliability_case(case)


if __name__ == "__main__":
    unittest.main()
