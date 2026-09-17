#!/usr/bin/env python3
"""Contract test for the Class 3 selection rule extension (offline)."""

import copy
import unittest

from q60_class_3_selection_general_rules_logic import (
    BINDING_RULES,
    CHAIN_BROKEN,
    CHAIN_EXTENDED,
    CHAIN_PARTIAL,
    DECLARATION_CREDIT,
    RULE_WEIGHTS,
    SELECTION_RULES,
    SUPPLY_TIERS,
    assess_rule_extension,
    chain_coverage,
    flow_down_breaks,
    governing_tier,
    in_house_gaps,
    inadmissible_claims,
    normalise_chain,
    normalise_rule_entry,
    rule_is_binding,
    rule_is_covered,
    tier_coverage,
    weakest_rule,
)

APPLIED = {"status": "applied-with-evidence"}


def _all_applied():
    return {rule: dict(APPLIED) for rule in SELECTION_RULES}


def _clean_case():
    return {
        "project": "class-3-cubesat-avionics",
        "tiers": {
            "in-house": _all_applied(),
            "prime-subcontractor": _all_applied(),
            "equipment-supplier": _all_applied(),
        },
    }


def _case(**overrides):
    case = copy.deepcopy(_clean_case())
    case.update(overrides)
    return case


class RuleTableTests(unittest.TestCase):
    def test_every_rule_carries_a_weight(self):
        self.assertEqual(set(RULE_WEIGHTS), set(SELECTION_RULES))

    def test_binding_rules_are_a_subset_of_the_rule_set(self):
        self.assertTrue(BINDING_RULES.issubset(set(SELECTION_RULES)))

    def test_component_class_matching_is_binding(self):
        self.assertTrue(rule_is_binding("component-class-matched-to-application"))

    def test_lead_time_check_is_not_binding(self):
        self.assertFalse(rule_is_binding("obsolescence-and-lead-time-checked"))

    def test_unknown_rule_rejected(self):
        with self.assertRaises(ValueError):
            rule_is_binding("paint-colour-agreed")

    def test_in_house_is_the_first_tier(self):
        self.assertEqual(SUPPLY_TIERS[0], "in-house")


class EntryGradingTests(unittest.TestCase):
    def test_evidenced_rule_earns_full_credit(self):
        record = normalise_rule_entry("in-house", "derating-rules-applied", APPLIED)
        self.assertAlmostEqual(record["credit"], 1.0, places=9)
        self.assertTrue(rule_is_covered(record))

    def test_bare_supplier_declaration_earns_partial_credit(self):
        record = normalise_rule_entry(
            "equipment-supplier",
            "derating-rules-applied",
            {"status": "supplier-declared-only"},
        )
        self.assertAlmostEqual(record["credit"], DECLARATION_CREDIT, places=9)
        self.assertFalse(rule_is_covered(record))

    def test_absent_entry_is_undeclared_and_stays_counted(self):
        record = normalise_rule_entry("in-house", "derating-rules-applied", None)
        self.assertEqual(record["status"], "undeclared")
        self.assertTrue(record["counted"])
        self.assertAlmostEqual(record["credit"], 0.0, places=9)

    def test_waiver_without_an_approval_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry(
                "in-house",
                "obsolescence-and-lead-time-checked",
                {"status": "waived-with-approval"},
            )

    def test_waiver_on_a_non_binding_rule_is_admissible(self):
        record = normalise_rule_entry(
            "in-house",
            "obsolescence-and-lead-time-checked",
            {"status": "waived-with-approval", "approval_reference": "PCB-2026-014"},
        )
        self.assertTrue(record["admissible"])
        self.assertTrue(rule_is_covered(record))

    def test_waiver_on_a_binding_rule_is_inadmissible(self):
        record = normalise_rule_entry(
            "component-distributor",
            "radiation-tolerance-matched-to-mission",
            {"status": "waived-with-approval", "approval_reference": "PCB-2026-015"},
        )
        self.assertFalse(record["admissible"])
        self.assertAlmostEqual(record["credit"], 0.0, places=9)
        self.assertTrue(record["counted"])

    def test_not_applicable_needs_a_justification(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry(
                "component-distributor",
                "derating-rules-applied",
                {"status": "not-applicable-at-tier"},
            )

    def test_justified_not_applicable_leaves_the_denominator(self):
        record = normalise_rule_entry(
            "component-distributor",
            "derating-rules-applied",
            {
                "status": "not-applicable-at-tier",
                "justification": "the distributor never sets an operating point",
            },
        )
        self.assertTrue(record["admissible"])
        self.assertFalse(record["counted"])

    def test_not_applicable_on_a_binding_rule_stays_in_the_denominator(self):
        record = normalise_rule_entry(
            "component-distributor",
            "packaging-and-material-limits-applied",
            {"status": "not-applicable-at-tier", "justification": "catalogue part"},
        )
        self.assertFalse(record["admissible"])
        self.assertTrue(record["counted"])

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry("in-house", "derating-rules-applied", {"status": "maybe"})

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_rule_entry("orbit", "derating-rules-applied", APPLIED)


class ChainTests(unittest.TestCase):
    def test_chain_expands_every_rule_at_every_declared_tier(self):
        chain = normalise_chain({"in-house": {}})
        self.assertEqual(set(chain["in-house"]), set(SELECTION_RULES))

    def test_chain_without_an_in_house_tier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_chain({"equipment-supplier": _all_applied()})

    def test_unknown_tier_in_the_chain_rejected(self):
        with self.assertRaises(ValueError):
            normalise_chain({"in-house": {}, "launch-site": {}})

    def test_unknown_rule_in_a_tier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_chain({"in-house": {"paint-colour-agreed": APPLIED}})

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            normalise_chain({})

    def test_fully_applied_tier_covers_the_whole_rule_set(self):
        coverage = chain_coverage(_clean_case()["tiers"])
        for value in coverage.values():
            self.assertAlmostEqual(value, 1.0, places=9)

    def test_declaration_only_tier_lands_on_the_partial_credit(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"] = {
            rule: {"status": "supplier-declared-only"} for rule in SELECTION_RULES
        }
        coverage = chain_coverage(tiers)
        self.assertAlmostEqual(
            coverage["equipment-supplier"], DECLARATION_CREDIT, places=9
        )

    def test_a_tier_with_no_applicable_rules_reads_as_covered(self):
        records = normalise_chain(
            {
                "in-house": {
                    rule: {
                        "status": "not-applicable-at-tier",
                        "justification": "nothing is selected here",
                    }
                    for rule in SELECTION_RULES
                    if rule not in BINDING_RULES
                }
            }
        )["in-house"]
        subset = {
            rule: record
            for rule, record in records.items()
            if rule not in BINDING_RULES
        }
        self.assertAlmostEqual(tier_coverage(subset), 1.0, places=9)

    def test_reach_is_the_weakest_tier_not_the_average(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"] = {
            rule: {"status": "supplier-declared-only"} for rule in SELECTION_RULES
        }
        governing = governing_tier(tiers)
        self.assertEqual(governing["tier"], "equipment-supplier")
        self.assertAlmostEqual(governing["coverage"], DECLARATION_CREDIT, places=9)


class DefectSeparationTests(unittest.TestCase):
    def test_missing_in_house_rule_is_a_project_defect(self):
        tiers = _clean_case()["tiers"]
        del tiers["in-house"]["derating-rules-applied"]
        self.assertIn("derating-rules-applied", in_house_gaps(tiers))

    def test_a_rule_lost_downstream_is_a_flow_down_defect(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"]["derating-rules-applied"] = {"status": "not-applied"}
        breaks = flow_down_breaks(tiers)
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0]["tier"], "equipment-supplier")

    def test_a_rule_missing_in_house_is_not_also_reported_as_a_break(self):
        tiers = _clean_case()["tiers"]
        tiers["in-house"]["derating-rules-applied"] = {"status": "not-applied"}
        tiers["equipment-supplier"]["derating-rules-applied"] = {"status": "not-applied"}
        self.assertEqual(flow_down_breaks(tiers), [])

    def test_justified_not_applicable_downstream_is_not_a_break(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"]["obsolescence-and-lead-time-checked"] = {
            "status": "not-applicable-at-tier",
            "justification": "the supplier does not own the procurement schedule",
        }
        self.assertEqual(flow_down_breaks(tiers), [])

    def test_inadmissible_claims_are_listed_with_their_tier(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"]["radiation-tolerance-matched-to-mission"] = {
            "status": "waived-with-approval",
            "approval_reference": "PCB-2026-021",
        }
        claims = inadmissible_claims(tiers)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["tier"], "equipment-supplier")

    def test_weakest_rule_is_the_one_surviving_fewest_tiers(self):
        tiers = _clean_case()["tiers"]
        tiers["prime-subcontractor"]["preferred-source-order-respected"] = {
            "status": "not-applied"
        }
        tiers["equipment-supplier"]["preferred-source-order-respected"] = {
            "status": "not-applied"
        }
        weakest = weakest_rule(tiers)
        self.assertEqual(weakest["rule"], "preferred-source-order-respected")
        self.assertAlmostEqual(weakest["survival"], 1.0 / 3.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_clean_chain_is_extended(self):
        result = assess_rule_extension(_case())
        self.assertEqual(result["verdict"], CHAIN_EXTENDED)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_coverage_exactly_on_the_floor_passes(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"] = {
            rule: {"status": "supplier-declared-only"} for rule in SELECTION_RULES
        }
        result = assess_rule_extension(_case(tiers=tiers), minimum_coverage=DECLARATION_CREDIT)
        self.assertAlmostEqual(result["chain_reach"], DECLARATION_CREDIT, places=9)
        floor_findings = [f for f in result["findings"] if "against a floor" in f]
        self.assertEqual(floor_findings, [])

    def test_declaration_only_chain_falls_under_the_default_floor(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"] = {
            rule: {"status": "supplier-declared-only"} for rule in SELECTION_RULES
        }
        result = assess_rule_extension(_case(tiers=tiers))
        self.assertEqual(result["verdict"], CHAIN_BROKEN)
        self.assertTrue(any("against a floor" in f for f in result["findings"]))

    def test_a_soft_break_only_makes_the_chain_partial(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"]["obsolescence-and-lead-time-checked"] = {
            "status": "supplier-declared-only"
        }
        result = assess_rule_extension(_case(tiers=tiers), minimum_coverage=0.9)
        self.assertEqual(result["verdict"], CHAIN_PARTIAL)
        self.assertTrue(result["acceptable"])

    def test_a_binding_rule_lost_downstream_breaks_the_chain(self):
        tiers = _clean_case()["tiers"]
        tiers["equipment-supplier"]["packaging-and-material-limits-applied"] = {
            "status": "supplier-declared-only"
        }
        result = assess_rule_extension(_case(tiers=tiers))
        self.assertEqual(result["verdict"], CHAIN_BROKEN)
        self.assertFalse(result["acceptable"])

    def test_every_finding_comes_with_an_action(self):
        tiers = _clean_case()["tiers"]
        tiers["in-house"]["derating-rules-applied"] = {"status": "not-applied"}
        result = assess_rule_extension(_case(tiers=tiers))
        self.assertTrue(result["actions"])

    def test_missing_project_name_rejected(self):
        case = _case()
        del case["project"]
        with self.assertRaises(ValueError):
            assess_rule_extension(case)

    def test_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_rule_extension(_case(), minimum_coverage=1.4)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_rule_extension(["in-house"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
