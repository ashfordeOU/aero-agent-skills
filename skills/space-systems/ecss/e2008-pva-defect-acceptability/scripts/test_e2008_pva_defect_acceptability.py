#!/usr/bin/env python3
"""Contract test for the photovoltaic-assembly defect acceptability rules (offline)."""

import copy
import math
import unittest

from e2008_pva_defect_acceptability_logic import (
    ACCEPTABILITY_ESTABLISHED,
    ACCEPTABILITY_NOT_ESTABLISHED,
    ACCEPTABILITY_PROVISIONAL,
    AGREEMENT_BASES,
    QUALIFICATION_BASES,
    VERDICT_RANK,
    allowable_defect_count,
    assess_agreement,
    assess_assembly_defect_acceptability,
    assess_defect_rule,
    defect_utilisation,
    governing_defect,
    qualification_coverage_ratio,
)

AGREED_RULE = {
    "defect_type": "cell-edge-chip",
    "allowable_fraction": 0.02,
    "observed_count": 2,
    "agreement_basis": "customer-agreed",
    "agreement_record": "PVA-DCL-014",
    "qualification_basis": "qualification-demonstrated",
    "demonstrated_fraction": 0.025,
}

WEAK_RULE = {
    "defect_type": "interconnector-fracture",
    "allowable_fraction": 0.01,
    "observed_count": 4,
    "agreement_basis": "undocumented",
    "qualification_basis": "none",
}

GOOD_CASE = {"population": 150, "rules": [AGREED_RULE]}


def _rule(base, **overrides):
    rule = copy.deepcopy(base)
    for key, value in overrides.items():
        if value is None and key in rule:
            del rule[key]
        else:
            rule[key] = value
    return rule


class AllowableCountTests(unittest.TestCase):
    def test_fraction_of_a_population_becomes_whole_defects(self):
        self.assertEqual(allowable_defect_count(150, 0.02), 3)

    def test_product_landing_on_an_integer_is_not_lost_to_rounding(self):
        # 0.02 * 150 evaluates a hair above three on some platforms.
        self.assertEqual(allowable_defect_count(150, 0.02), 3)
        self.assertEqual(allowable_defect_count(400, 0.07), 28)

    def test_partial_defect_is_not_allowed(self):
        self.assertEqual(allowable_defect_count(10, 0.15), 1)

    def test_whole_population_fraction_allows_every_item(self):
        self.assertEqual(allowable_defect_count(96, 1.0), 96)

    def test_zero_population_rejected(self):
        with self.assertRaises(ValueError):
            allowable_defect_count(0, 0.02)

    def test_non_integer_population_rejected(self):
        with self.assertRaises(ValueError):
            allowable_defect_count(150.0, 0.02)

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            allowable_defect_count(150, 0.0)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            allowable_defect_count(150, 1.4)


class UtilisationTests(unittest.TestCase):
    def test_utilisation_is_the_share_of_the_allowance_used(self):
        self.assertAlmostEqual(defect_utilisation(2, 4), 0.5, places=9)

    def test_full_allowance_is_unity(self):
        self.assertAlmostEqual(defect_utilisation(3, 3), 1.0, places=9)

    def test_no_allowance_and_no_defect_is_zero(self):
        self.assertAlmostEqual(defect_utilisation(0, 0), 0.0, places=9)

    def test_defect_against_a_zero_allowance_is_unbounded(self):
        self.assertTrue(math.isinf(defect_utilisation(1, 0)))

    def test_negative_observed_count_rejected(self):
        with self.assertRaises(ValueError):
            defect_utilisation(-1, 3)


class CoverageTests(unittest.TestCase):
    def test_qualification_above_the_agreed_level_covers_it(self):
        self.assertAlmostEqual(
            qualification_coverage_ratio(0.025, 0.02), 1.25, places=9
        )

    def test_qualification_exactly_at_the_agreed_level_is_unity(self):
        self.assertAlmostEqual(qualification_coverage_ratio(0.02, 0.02), 1.0, places=9)

    def test_qualification_below_the_agreed_level_falls_short(self):
        self.assertAlmostEqual(qualification_coverage_ratio(0.01, 0.02), 0.5, places=9)

    def test_non_numeric_demonstrated_fraction_rejected(self):
        with self.assertRaises(ValueError):
            qualification_coverage_ratio("2 percent", 0.02)


class AgreementTests(unittest.TestCase):
    def test_customer_agreed_basis_carries_its_record(self):
        result = assess_agreement("customer-agreed", "PVA-DCL-014")
        self.assertTrue(result["agreed"])
        self.assertEqual(result["record"], "PVA-DCL-014")
        self.assertEqual(result["findings"], [])

    def test_customer_agreed_basis_without_a_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_agreement("customer-agreed")

    def test_supplier_proposed_basis_is_documented_but_not_agreed(self):
        result = assess_agreement("supplier-proposed", "SUP-NOTE-7")
        self.assertFalse(result["agreed"])
        self.assertTrue(any("not agreed" in f for f in result["findings"]))

    def test_undocumented_basis_reports_shop_practice(self):
        result = assess_agreement("undocumented")
        self.assertFalse(result["agreed"])
        self.assertIsNone(result["record"])
        self.assertTrue(any("shop practice" in f for f in result["findings"]))

    def test_undocumented_basis_citing_a_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_agreement("undocumented", "PVA-DCL-014")

    def test_unknown_agreement_basis_rejected(self):
        with self.assertRaises(ValueError):
            assess_agreement("verbally-blessed")

    def test_every_declared_agreement_basis_is_handled(self):
        for basis in AGREEMENT_BASES:
            record = "REC-1" if basis == "customer-agreed" else None
            self.assertIn("agreed", assess_agreement(basis, record))


class DefectRuleTests(unittest.TestCase):
    def test_agreed_and_qualified_rule_is_established(self):
        result = assess_defect_rule(AGREED_RULE, 150)
        self.assertEqual(result["verdict"], ACCEPTABILITY_ESTABLISHED)
        self.assertEqual(result["allowed_count"], 3)
        self.assertTrue(result["within_allowance"])
        self.assertTrue(result["qualification_confirms"])

    def test_analysis_only_confirmation_is_provisional(self):
        rule = _rule(
            AGREED_RULE,
            qualification_basis="analysis-supported",
            demonstrated_fraction=None,
        )
        result = assess_defect_rule(rule, 150)
        self.assertEqual(result["verdict"], ACCEPTABILITY_PROVISIONAL)
        self.assertTrue(any("rests on analysis" in f for f in result["findings"]))

    def test_unconfirmed_level_is_not_established(self):
        result = assess_defect_rule(WEAK_RULE, 150)
        self.assertEqual(result["verdict"], ACCEPTABILITY_NOT_ESTABLISHED)
        self.assertFalse(result["within_allowance"])

    def test_qualification_short_of_the_agreed_level_is_provisional(self):
        rule = _rule(AGREED_RULE, demonstrated_fraction=0.012)
        result = assess_defect_rule(rule, 150)
        self.assertEqual(result["verdict"], ACCEPTABILITY_PROVISIONAL)
        self.assertAlmostEqual(result["qualification_coverage"], 0.6, places=9)

    def test_qualification_exactly_on_the_agreed_level_still_confirms(self):
        rule = _rule(AGREED_RULE, demonstrated_fraction=3.0 * 0.02 / 3.0)
        result = assess_defect_rule(rule, 150)
        self.assertAlmostEqual(result["qualification_coverage"], 1.0, places=9)
        self.assertTrue(result["qualification_confirms"])
        self.assertEqual(result["verdict"], ACCEPTABILITY_ESTABLISHED)

    def test_supplier_proposed_level_cannot_reach_established(self):
        rule = _rule(
            AGREED_RULE, agreement_basis="supplier-proposed", agreement_record="SUP-7"
        )
        self.assertEqual(
            assess_defect_rule(rule, 150)["verdict"], ACCEPTABILITY_PROVISIONAL
        )

    def test_observed_defects_over_the_allowance_are_reported(self):
        rule = _rule(AGREED_RULE, observed_count=5)
        result = assess_defect_rule(rule, 150)
        self.assertFalse(result["within_allowance"])
        self.assertTrue(any("allowance of 3" in f for f in result["findings"]))

    def test_utilisation_is_carried_on_the_rule(self):
        result = assess_defect_rule(AGREED_RULE, 150)
        self.assertAlmostEqual(result["utilisation"], 2.0 / 3.0, places=9)

    def test_missing_defect_type_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect_rule(_rule(AGREED_RULE, defect_type=None), 150)

    def test_unknown_qualification_basis_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect_rule(_rule(AGREED_RULE, qualification_basis="hoped"), 150)

    def test_demonstrated_basis_without_a_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect_rule(_rule(AGREED_RULE, demonstrated_fraction=None), 150)

    def test_non_mapping_rule_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect_rule("cell-edge-chip", 150)

    def test_every_qualification_basis_is_handled(self):
        for basis in QUALIFICATION_BASES:
            rule = _rule(AGREED_RULE, qualification_basis=basis)
            if basis != "qualification-demonstrated":
                rule.pop("demonstrated_fraction", None)
            self.assertIn(assess_defect_rule(rule, 150)["verdict"], VERDICT_RANK)


class GoverningDefectTests(unittest.TestCase):
    def test_weakest_verdict_governs(self):
        assessments = [
            assess_defect_rule(AGREED_RULE, 150),
            assess_defect_rule(WEAK_RULE, 150),
        ]
        self.assertEqual(
            governing_defect(assessments)["defect_type"], "interconnector-fracture"
        )

    def test_equal_verdicts_are_broken_by_utilisation(self):
        hot = _rule(AGREED_RULE, defect_type="coverglass-chip", observed_count=3)
        cool = _rule(AGREED_RULE, defect_type="solder-void", observed_count=1)
        assessments = [
            assess_defect_rule(cool, 150),
            assess_defect_rule(hot, 150),
        ]
        self.assertEqual(governing_defect(assessments)["defect_type"], "coverglass-chip")

    def test_empty_assessment_list_rejected(self):
        with self.assertRaises(ValueError):
            governing_defect([])


class AssemblyRollUpTests(unittest.TestCase):
    def test_single_established_rule_gives_an_established_assembly(self):
        result = assess_assembly_defect_acceptability(GOOD_CASE)
        self.assertEqual(result["verdict"], ACCEPTABILITY_ESTABLISHED)
        self.assertTrue(result["article_conforms"])
        self.assertAlmostEqual(result["established_share"], 1.0, places=9)

    def test_one_weak_rule_drags_the_assembly_down(self):
        case = {"population": 150, "rules": [AGREED_RULE, WEAK_RULE]}
        result = assess_assembly_defect_acceptability(case)
        self.assertEqual(result["verdict"], ACCEPTABILITY_NOT_ESTABLISHED)
        self.assertEqual(
            result["governing_defect_type"], "interconnector-fracture"
        )
        self.assertAlmostEqual(result["established_share"], 0.5, places=9)

    def test_article_conformance_is_separate_from_the_criterion(self):
        over = _rule(AGREED_RULE, observed_count=9)
        result = assess_assembly_defect_acceptability(
            {"population": 150, "rules": [over]}
        )
        self.assertEqual(result["verdict"], ACCEPTABILITY_ESTABLISHED)
        self.assertFalse(result["article_conforms"])

    def test_duplicate_defect_type_rejected(self):
        case = {"population": 150, "rules": [AGREED_RULE, copy.deepcopy(AGREED_RULE)]}
        with self.assertRaises(ValueError):
            assess_assembly_defect_acceptability(case)

    def test_empty_rule_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_defect_acceptability({"population": 150, "rules": []})

    def test_missing_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_defect_acceptability({"rules": [AGREED_RULE]})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_defect_acceptability("cell-edge-chip")

    def test_findings_are_collected_from_every_rule(self):
        case = {"population": 150, "rules": [AGREED_RULE, WEAK_RULE]}
        result = assess_assembly_defect_acceptability(case)
        self.assertTrue(any("shop practice" in f for f in result["findings"]))
        self.assertTrue(any("nothing confirms" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
