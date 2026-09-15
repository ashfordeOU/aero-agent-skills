#!/usr/bin/env python3
"""Contract test for the Class 1 selection general rules (offline)."""

import copy
import unittest

from q60_class_1_selection_general_rules_logic import (
    CHAIN_BROKEN,
    CHAIN_EXTENDED,
    RULE_STATUSES,
    SELECTION_RULES,
    SUPPLY_TIERS,
    assess_rule_extension,
    chain_coverage,
    flow_down_breaks,
    governing_tier,
    normalise_chain,
    normalise_rule_entry,
    rule_is_covered,
    tier_coverage,
    unenforceable_rules,
    weakest_rule,
)


def _all_applied():
    return {rule: {"status": "applied"} for rule in SELECTION_RULES}


GOOD_CASE = {
    "programme": "class-1-platform-avionics",
    "tiers": {
        "in-house": _all_applied(),
        "tier-1-subcontractor": _all_applied(),
        "tier-2-supplier": _all_applied(),
    },
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class RuleEntryTests(unittest.TestCase):
    def test_bare_status_string_is_accepted(self):
        entry = normalise_rule_entry(
            "in-house", "approved-parts-list-entry", "applied"
        )
        self.assertEqual(entry["status"], "applied")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry("in-house", "approved-parts-list-entry", "probably")

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry("tier-9-broker", "approved-parts-list-entry", "applied")

    def test_unknown_rule_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry("in-house", "favourite-supplier-chosen", "applied")

    def test_waiver_without_an_approval_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry(
                "tier-1-subcontractor",
                "lot-traceability-retained",
                {"status": "waived-with-approval"},
            )

    def test_waiver_with_an_approval_reference_is_covered(self):
        entry = normalise_rule_entry(
            "tier-1-subcontractor",
            "lot-traceability-retained",
            {"status": "waived-with-approval", "approval_reference": "rfd-0184"},
        )
        self.assertTrue(rule_is_covered(entry))
        self.assertEqual(entry["approval_reference"], "rfd-0184")

    def test_not_applied_is_not_covered(self):
        entry = normalise_rule_entry(
            "tier-2-supplier", "lot-traceability-retained", "not-applied"
        )
        self.assertFalse(rule_is_covered(entry))

    def test_every_status_is_either_covered_or_not(self):
        for status in RULE_STATUSES:
            payload = {"status": status}
            if status == "waived-with-approval":
                payload["approval_reference"] = "rfd-0001"
            entry = normalise_rule_entry("in-house", "quality-level-floor-met", payload)
            self.assertIsInstance(rule_is_covered(entry), bool)


class ChainStructureTests(unittest.TestCase):
    def test_full_chain_normalises(self):
        normalised = normalise_chain(GOOD_CASE["tiers"])
        self.assertEqual(len(normalised), 3)

    def test_chain_without_an_in_house_tier_rejected(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        del tiers["in-house"]
        with self.assertRaises(ValueError):
            normalise_chain(tiers)

    def test_chain_with_a_gap_rejected(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        del tiers["tier-1-subcontractor"]
        with self.assertRaises(ValueError):
            normalise_chain(tiers)

    def test_unknown_tier_in_a_chain_rejected(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        tiers["tier-9-broker"] = _all_applied()
        with self.assertRaises(ValueError):
            normalise_chain(tiers)

    def test_tier_missing_a_rule_rejected(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        del tiers["tier-2-supplier"]["lot-traceability-retained"]
        with self.assertRaises(ValueError):
            normalise_chain(tiers)

    def test_tier_declaring_an_unknown_rule_rejected(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        tiers["tier-1-subcontractor"]["favourite-supplier-chosen"] = "applied"
        with self.assertRaises(ValueError):
            normalise_chain(tiers)

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            normalise_chain({})

    def test_in_house_only_chain_is_allowed(self):
        normalised = normalise_chain({"in-house": _all_applied()})
        self.assertEqual(tuple(normalised), ("in-house",))


class CoverageTests(unittest.TestCase):
    def test_full_declaration_is_full_coverage(self):
        self.assertAlmostEqual(tier_coverage(normalise_chain(
            {"in-house": _all_applied()})["in-house"]), 1.0, places=9)

    def test_one_dropped_rule_costs_one_share(self):
        tiers = {"in-house": _all_applied()}
        tiers["in-house"]["lot-traceability-retained"] = "not-applied"
        normalised = normalise_chain(tiers)
        self.assertAlmostEqual(
            tier_coverage(normalised["in-house"]),
            (len(SELECTION_RULES) - 1) / float(len(SELECTION_RULES)),
            places=9,
        )

    def test_chain_takes_the_weakest_tier_not_the_average(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        for rule in SELECTION_RULES[:4]:
            tiers["tier-2-supplier"][rule] = "not-applied"
        self.assertAlmostEqual(chain_coverage(tiers), 0.5, places=9)

    def test_governing_tier_is_the_weakest_one(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        tiers["tier-2-supplier"]["lot-traceability-retained"] = "not-applied"
        self.assertEqual(governing_tier(tiers), "tier-2-supplier")

    def test_governing_tier_ties_go_to_the_nearest_tier(self):
        self.assertEqual(governing_tier(GOOD_CASE["tiers"]), "in-house")

    def test_coverage_of_a_partial_declaration_rejected(self):
        with self.assertRaises(ValueError):
            tier_coverage({"approved-parts-list-entry": {"status": "applied"}})


class FlowDownTests(unittest.TestCase):
    def test_clean_chain_has_no_breaks(self):
        self.assertEqual(flow_down_breaks(GOOD_CASE["tiers"]), ())

    def test_rule_dropped_downstream_is_a_break(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        tiers["tier-2-supplier"]["radiation-capability-demonstrated"] = "not-applied"
        breaks = flow_down_breaks(tiers)
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0]["tier"], "tier-2-supplier")
        self.assertEqual(breaks[0]["rule"], "radiation-capability-demonstrated")

    def test_rule_absent_in_house_is_unenforceable_not_a_break(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        for tier in tiers:
            tiers[tier]["deviation-approved-by-customer"] = "not-applied"
        self.assertEqual(flow_down_breaks(tiers), ())
        self.assertIn("deviation-approved-by-customer", unenforceable_rules(tiers))

    def test_approved_waiver_downstream_is_not_a_break(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        tiers["tier-2-supplier"]["lot-traceability-retained"] = {
            "status": "waived-with-approval",
            "approval_reference": "rfd-0184",
        }
        self.assertEqual(flow_down_breaks(tiers), ())

    def test_weakest_rule_is_the_least_covered_one(self):
        tiers = copy.deepcopy(GOOD_CASE["tiers"])
        tiers["tier-1-subcontractor"]["lot-traceability-retained"] = "not-applied"
        tiers["tier-2-supplier"]["lot-traceability-retained"] = "not-applied"
        self.assertEqual(weakest_rule(tiers), "lot-traceability-retained")


class AssessRuleExtensionTests(unittest.TestCase):
    def test_clean_chain_is_extended(self):
        result = assess_rule_extension(GOOD_CASE)
        self.assertEqual(result["verdict"], CHAIN_EXTENDED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_broken_flow_down_is_reported(self):
        case = _case()
        case["tiers"]["tier-1-subcontractor"]["quality-level-floor-met"] = "not-applied"
        result = assess_rule_extension(case)
        self.assertEqual(result["verdict"], CHAIN_BROKEN)
        self.assertTrue(any("flow-down breaks" in f for f in result["findings"]))

    def test_unenforceable_rule_is_named_as_an_intention(self):
        case = _case()
        for tier in case["tiers"]:
            case["tiers"][tier]["prohibited-material-check-done"] = "not-applied"
        result = assess_rule_extension(case)
        self.assertEqual(result["verdict"], CHAIN_BROKEN)
        self.assertTrue(any("intention rather than a rule" in f for f in result["findings"]))

    def test_coverage_exactly_on_a_relaxed_target_is_compliant_on_coverage(self):
        case = _case()
        for rule in SELECTION_RULES[:2]:
            for tier in case["tiers"]:
                case["tiers"][tier][rule] = "not-applied"
        target = (len(SELECTION_RULES) - 2) / float(len(SELECTION_RULES))
        result = assess_rule_extension(case, minimum_coverage=target)
        self.assertAlmostEqual(result["chain_coverage"], target, places=9)
        self.assertFalse(
            any("sits below" in f for f in result["findings"])
        )

    def test_coverage_below_the_target_is_named_with_its_governing_tier(self):
        case = _case()
        for rule in SELECTION_RULES[:3]:
            case["tiers"]["tier-2-supplier"][rule] = "not-applied"
        result = assess_rule_extension(case)
        self.assertEqual(result["governing_tier"], "tier-2-supplier")
        self.assertTrue(any("sits below" in f for f in result["findings"]))

    def test_missing_programme_rejected(self):
        case = _case()
        del case["programme"]
        with self.assertRaises(ValueError):
            assess_rule_extension(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_rule_extension(["class-1-platform-avionics"])

    def test_minimum_coverage_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_rule_extension(GOOD_CASE, minimum_coverage=1.5)

    def test_minimum_coverage_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            assess_rule_extension(GOOD_CASE, minimum_coverage=0.0)

    def test_boolean_minimum_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_rule_extension(GOOD_CASE, minimum_coverage=True)

    def test_tier_coverage_is_reported_for_every_declared_tier(self):
        result = assess_rule_extension(GOOD_CASE)
        self.assertEqual(set(result["tier_coverage"]), set(GOOD_CASE["tiers"]))

    def test_every_supply_tier_can_govern_the_chain(self):
        for depth in range(1, len(SUPPLY_TIERS) + 1):
            tiers = {tier: _all_applied() for tier in SUPPLY_TIERS[:depth]}
            weak = SUPPLY_TIERS[depth - 1]
            tiers[weak]["lot-traceability-retained"] = "not-applied"
            result = assess_rule_extension(
                {"programme": "class-1-platform-avionics", "tiers": tiers}
            )
            self.assertEqual(result["governing_tier"], weak)


if __name__ == "__main__":
    unittest.main(verbosity=1)
