#!/usr/bin/env python3
"""Contract test for the PVA purpose-and-objective work scope (offline)."""

import copy
import unittest

from e2008_photovoltaic_assembly_purpose_and_objective_logic import (
    DEFAULT_OBJECTIVE_POLICY,
    LIMIT_CATEGORIES,
    LIMIT_SENSES,
    OBJECTIVE_ESTABLISHED,
    OBJECTIVE_INCOMPLETE,
    RESPONSIBLE_PARTIES,
    WORK_ITEM_KINDS,
    establish_pva_objective,
    evaluate_design_limit,
    evaluate_work_item,
    limit_margin_fraction,
    missing_limit_categories,
    required_margin_fraction,
    responsibility_coverage,
    validate_objective_policy,
    worst_design_limit,
)

ESTABLISHED_CASE = {
    "design_limits": [
        {
            "name": "cell junction temperature",
            "category": "thermal",
            "sense": "not-to-exceed",
            "limit_value": 383.15,
            "predicted_value": 333.15,
        },
        {
            "name": "string open-circuit voltage",
            "category": "electrical",
            "sense": "not-to-exceed",
            "limit_value": 100.0,
            "predicted_value": 70.0,
        },
        {
            "name": "interconnect pull strength",
            "category": "mechanical",
            "sense": "not-to-fall-below",
            "limit_value": 0.8,
            "predicted_value": 1.6,
        },
    ],
    "work_items": [
        {"name": "coupon design", "kind": "design", "responsible_party": "supplier"},
        {"name": "cell laydown", "kind": "manufacturing", "responsible_party": "supplier"},
        {
            "name": "acceptance review",
            "kind": "verification",
            "responsible_party": "shared-under-agreement",
            "agreement_reference": "PVA statement of work section 14",
        },
    ],
}

OPEN_CASE = {
    "design_limits": [
        {
            "name": "cell junction temperature",
            "category": "thermal",
            "sense": "not-to-exceed",
            "limit_value": 383.15,
            "predicted_value": 378.15,
        },
        {
            "name": "string open-circuit voltage",
            "category": "electrical",
            "sense": "not-to-exceed",
            "limit_value": 100.0,
            "predicted_value": 95.0,
        },
    ],
    "work_items": [
        {"name": "coupon design", "kind": "design", "responsible_party": "customer"},
        {"name": "cell laydown", "kind": "manufacturing", "responsible_party": None},
        {"name": "acceptance review", "kind": "verification", "responsible_party": "supplier"},
    ],
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_objective_policy(DEFAULT_OBJECTIVE_POLICY), DEFAULT_OBJECTIVE_POLICY
        )

    def test_policy_covers_every_limit_category(self):
        for category in LIMIT_CATEGORIES:
            self.assertIn(category, DEFAULT_OBJECTIVE_POLICY["required_margin_fraction"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective_policy("default")

    def test_policy_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_OBJECTIVE_POLICY)
        del broken["required_margin_fraction"]["optical"]
        with self.assertRaises(ValueError):
            validate_objective_policy(broken)

    def test_policy_with_negative_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_OBJECTIVE_POLICY)
        broken["required_margin_fraction"]["thermal"] = -0.1
        with self.assertRaises(ValueError):
            validate_objective_policy(broken)

    def test_policy_margin_of_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_OBJECTIVE_POLICY)
        broken["required_margin_fraction"]["thermal"] = 1.0
        with self.assertRaises(ValueError):
            validate_objective_policy(broken)

    def test_policy_with_unknown_work_item_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_OBJECTIVE_POLICY)
        broken["required_work_item_kinds"] = ["design", "packaging"]
        with self.assertRaises(ValueError):
            validate_objective_policy(broken)

    def test_required_margin_reads_the_policy(self):
        self.assertAlmostEqual(required_margin_fraction("electrical"), 0.20, places=9)
        self.assertAlmostEqual(required_margin_fraction("mechanical"), 0.25, places=9)


class MarginFractionTests(unittest.TestCase):
    def test_not_to_exceed_margin(self):
        self.assertAlmostEqual(
            limit_margin_fraction("not-to-exceed", 100.0, 70.0), 0.30, places=9
        )

    def test_not_to_fall_below_margin(self):
        self.assertAlmostEqual(
            limit_margin_fraction("not-to-fall-below", 0.8, 1.6), 1.0, places=9
        )

    def test_predicted_on_the_limit_gives_zero_margin(self):
        self.assertAlmostEqual(
            limit_margin_fraction("not-to-exceed", 100.0, 100.0), 0.0, places=9
        )

    def test_exceeding_the_limit_gives_a_negative_margin(self):
        self.assertAlmostEqual(
            limit_margin_fraction("not-to-exceed", 100.0, 120.0), -0.20, places=9
        )

    def test_negative_limit_is_normalized_on_its_magnitude(self):
        self.assertAlmostEqual(
            limit_margin_fraction("not-to-fall-below", -100.0, -80.0), 0.20, places=9
        )

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            limit_margin_fraction("not-to-exceed", 0.0, 10.0)

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            limit_margin_fraction("roughly-around", 100.0, 70.0)

    def test_non_numeric_prediction_rejected(self):
        with self.assertRaises(ValueError):
            limit_margin_fraction("not-to-exceed", 100.0, "70 V")

    def test_every_sense_is_accepted(self):
        for sense in LIMIT_SENSES:
            self.assertIsInstance(limit_margin_fraction(sense, 10.0, 12.0), float)


class DesignLimitTests(unittest.TestCase):
    def test_comfortable_limit_is_compliant(self):
        record = evaluate_design_limit(ESTABLISHED_CASE["design_limits"][1])
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["margin_fraction"], 0.30, places=9)
        self.assertAlmostEqual(record["shortfall_fraction"], 0.0, places=9)

    def test_margin_exactly_on_the_policy_is_compliant(self):
        record = evaluate_design_limit(
            {
                "name": "coverglass absorptance",
                "category": "thermal",
                "sense": "not-to-exceed",
                "limit_value": 100.0,
                "predicted_value": 90.0,
            }
        )
        self.assertAlmostEqual(record["margin_fraction"], 0.10, places=9)
        self.assertAlmostEqual(record["required_margin_fraction"], 0.10, places=9)
        self.assertTrue(record["compliant"])

    def test_mechanical_margin_exactly_on_the_policy_is_compliant(self):
        record = evaluate_design_limit(
            {
                "name": "bond-line shear strength",
                "category": "mechanical",
                "sense": "not-to-fall-below",
                "limit_value": 8.0,
                "predicted_value": 10.0,
            }
        )
        self.assertAlmostEqual(record["margin_fraction"], 0.25, places=9)
        self.assertTrue(record["compliant"])

    def test_thin_margin_is_not_compliant_and_reports_a_shortfall(self):
        record = evaluate_design_limit(
            {
                "name": "string open-circuit voltage",
                "category": "electrical",
                "sense": "not-to-exceed",
                "limit_value": 100.0,
                "predicted_value": 95.0,
            }
        )
        self.assertFalse(record["compliant"])
        self.assertAlmostEqual(record["shortfall_fraction"], 0.15, places=9)

    def test_limit_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_design_limit(
                {
                    "name": "  ",
                    "category": "thermal",
                    "sense": "not-to-exceed",
                    "limit_value": 100.0,
                    "predicted_value": 70.0,
                }
            )

    def test_limit_with_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_design_limit(
                {
                    "name": "creep",
                    "category": "chemical",
                    "sense": "not-to-exceed",
                    "limit_value": 100.0,
                    "predicted_value": 70.0,
                }
            )

    def test_non_mapping_limit_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_design_limit("cell junction temperature")

    def test_worst_limit_is_the_one_nearest_its_requirement(self):
        evaluations = [
            evaluate_design_limit(limit) for limit in ESTABLISHED_CASE["design_limits"]
        ]
        self.assertEqual(worst_design_limit(evaluations)["name"], "cell junction temperature")

    def test_worst_limit_needs_a_non_empty_sequence(self):
        with self.assertRaises(ValueError):
            worst_design_limit([])


class LimitCoverageTests(unittest.TestCase):
    def test_full_set_has_no_missing_category(self):
        self.assertEqual(missing_limit_categories(ESTABLISHED_CASE["design_limits"]), [])

    def test_missing_mechanical_limit_is_reported(self):
        self.assertEqual(
            missing_limit_categories(OPEN_CASE["design_limits"]), ["mechanical"]
        )

    def test_empty_limit_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_limit_categories([])


class ResponsibilityTests(unittest.TestCase):
    def test_supplier_owned_item_is_assigned(self):
        record = evaluate_work_item(
            {"name": "cell laydown", "kind": "manufacturing", "responsible_party": "supplier"}
        )
        self.assertTrue(record["assigned"])
        self.assertEqual(record["findings"], [])

    def test_shared_item_needs_an_agreement_reference(self):
        with self.assertRaises(ValueError):
            evaluate_work_item(
                {
                    "name": "acceptance review",
                    "kind": "verification",
                    "responsible_party": "shared-under-agreement",
                }
            )

    def test_unowned_item_is_flagged_rather_than_defaulted(self):
        record = evaluate_work_item(
            {"name": "cell laydown", "kind": "manufacturing", "responsible_party": None}
        )
        self.assertFalse(record["assigned"])
        self.assertIsNone(record["responsible_party"])
        self.assertTrue(any("no accountable party" in f for f in record["findings"]))

    def test_unknown_party_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_work_item(
                {"name": "cell laydown", "kind": "manufacturing", "responsible_party": "whoever"}
            )

    def test_unknown_work_item_kind_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_work_item(
                {"name": "shipping", "kind": "logistics", "responsible_party": "supplier"}
            )

    def test_every_party_and_kind_is_accepted(self):
        for kind in WORK_ITEM_KINDS:
            for party in RESPONSIBLE_PARTIES:
                item = {"name": "item", "kind": kind, "responsible_party": party}
                if party == "shared-under-agreement":
                    item["agreement_reference"] = "agreement 1"
                self.assertTrue(evaluate_work_item(item)["assigned"])

    def test_full_coverage_reports_no_gap(self):
        coverage = responsibility_coverage(ESTABLISHED_CASE["work_items"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=9)
        self.assertEqual(coverage["unassigned"], [])
        self.assertEqual(coverage["missing_work_item_kinds"], [])

    def test_partial_coverage_names_the_open_item_and_the_open_activity(self):
        coverage = responsibility_coverage(OPEN_CASE["work_items"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 2.0 / 3.0, places=9)
        self.assertEqual(coverage["unassigned"], ["cell laydown"])
        self.assertEqual(coverage["missing_work_item_kinds"], ["manufacturing"])

    def test_empty_work_item_list_rejected(self):
        with self.assertRaises(ValueError):
            responsibility_coverage([])


class ObjectiveTests(unittest.TestCase):
    def test_complete_scope_establishes_the_objective(self):
        result = establish_pva_objective(ESTABLISHED_CASE)
        self.assertEqual(result["verdict"], OBJECTIVE_ESTABLISHED)
        self.assertTrue(result["established"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["governing_limit"], "cell junction temperature")

    def test_open_scope_leaves_the_objective_incomplete(self):
        result = establish_pva_objective(OPEN_CASE)
        self.assertEqual(result["verdict"], OBJECTIVE_INCOMPLETE)
        self.assertFalse(result["established"])
        self.assertEqual(result["missing_limit_categories"], ["mechanical"])
        self.assertEqual(result["unassigned_work_items"], ["cell laydown"])
        self.assertIn("string open-circuit voltage", result["non_compliant_limits"])

    def test_open_scope_findings_name_every_defect(self):
        findings = establish_pva_objective(OPEN_CASE)["findings"]
        self.assertTrue(any("no accountable party" in f for f in findings))
        self.assertTrue(any("mechanical design limit" in f for f in findings))
        self.assertTrue(any("string open-circuit voltage" in f for f in findings))

    def test_a_single_open_owner_is_enough_to_hold_the_verdict(self):
        case = copy.deepcopy(ESTABLISHED_CASE)
        case["work_items"][0]["responsible_party"] = None
        result = establish_pva_objective(case)
        self.assertEqual(result["verdict"], OBJECTIVE_INCOMPLETE)
        self.assertEqual(result["unassigned_work_items"], ["coupon design"])

    def test_a_stricter_policy_can_reopen_an_established_scope(self):
        policy = copy.deepcopy(DEFAULT_OBJECTIVE_POLICY)
        policy["required_margin_fraction"]["thermal"] = 0.50
        result = establish_pva_objective(ESTABLISHED_CASE, policy)
        self.assertEqual(result["verdict"], OBJECTIVE_INCOMPLETE)
        self.assertEqual(result["non_compliant_limits"], ["cell junction temperature"])

    def test_case_without_design_limits_rejected(self):
        case = _case(ESTABLISHED_CASE, design_limits=[])
        with self.assertRaises(ValueError):
            establish_pva_objective(case)

    def test_case_without_work_items_rejected(self):
        case = copy.deepcopy(ESTABLISHED_CASE)
        del case["work_items"]
        with self.assertRaises(ValueError):
            establish_pva_objective(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            establish_pva_objective(["design_limits"])


if __name__ == "__main__":
    unittest.main()
