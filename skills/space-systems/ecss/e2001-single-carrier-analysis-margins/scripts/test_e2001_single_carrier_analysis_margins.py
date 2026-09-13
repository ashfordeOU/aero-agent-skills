#!/usr/bin/env python3
"""Gate 3 contract test -- single-carrier nominal analysis margins.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_single_carrier_analysis_margins.py
"""

import unittest

from e2001_single_carrier_analysis_margins_logic import (
    LEVEL_ONE,
    LEVEL_TWO,
    MARGIN_CONTRIBUTIONS,
    achieved_analysis_margin_db,
    assess_analysis_margin_case,
    contribution_adder_db,
    contribution_budget_db,
    equipment_type_adder_db,
    heritage_credit_db,
    nominal_base_margin_db,
    power_limit_for_required_margin_w,
    required_analysis_margin_db,
    summarize_margin_register,
)


def coverage(**overrides):
    """Coverage statements for every contribution, unbounded by default."""
    stated = {c: False for c in MARGIN_CONTRIBUTIONS}
    for key, value in overrides.items():
        stated[key.replace("_", "-")] = value
    return stated


def baseline_case(**overrides):
    """A level-two case with nothing bounded and no heritage credit."""
    case = {
        "identifier": "waveguide-step",
        "analysis_level": LEVEL_TWO,
        "coverage": coverage(),
        "equipment_type": "waveguide-passive-unit",
        "heritage": "new-design",
        "threshold_power_w": 1000.0,
        "operating_power_w": 100.0,
    }
    case.update(overrides)
    return case


class TestBaseMargin(unittest.TestCase):
    def test_chart_route_carries_the_larger_base(self):
        self.assertGreater(
            nominal_base_margin_db(LEVEL_ONE), nominal_base_margin_db(LEVEL_TWO)
        )

    def test_default_base_values(self):
        self.assertAlmostEqual(nominal_base_margin_db(LEVEL_ONE), 6.0)
        self.assertAlmostEqual(nominal_base_margin_db(LEVEL_TWO), 4.0)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            nominal_base_margin_db("level-three")

    def test_policy_without_the_level_entry_rejected(self):
        with self.assertRaises(ValueError):
            nominal_base_margin_db(LEVEL_TWO, {"base_margin_db": {LEVEL_ONE: 6.0}})

    def test_negative_base_value_rejected(self):
        with self.assertRaises(ValueError):
            nominal_base_margin_db(LEVEL_TWO, {"base_margin_db": {LEVEL_TWO: -1.0}})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            nominal_base_margin_db(LEVEL_TWO, "the-usual-numbers")


class TestContributionAdders(unittest.TestCase):
    def test_known_adder(self):
        self.assertAlmostEqual(
            contribution_adder_db("secondary-emission-yield-scatter"), 1.5
        )

    def test_unknown_contribution_rejected(self):
        with self.assertRaises(ValueError):
            contribution_adder_db("launch-vibration-spread")

    def test_policy_without_the_adder_rejected(self):
        with self.assertRaises(ValueError):
            contribution_adder_db(
                "power-measurement-uncertainty",
                {"contribution_adder_db": {"manufacturing-tolerance-spread": 1.0}},
            )


class TestContributionBudget(unittest.TestCase):
    def test_nothing_bounded_sums_every_adder(self):
        out = contribution_budget_db(coverage(), LEVEL_TWO)
        self.assertAlmostEqual(out["total_db"], 4.5, places=12)
        self.assertEqual(out["rejected_coverage_claims"], [])

    def test_everything_bounded_costs_nothing(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        out = contribution_budget_db(stated, LEVEL_TWO)
        self.assertAlmostEqual(out["total_db"], 0.0, places=12)

    def test_partial_coverage_drops_only_the_bounded_adders(self):
        out = contribution_budget_db(
            coverage(manufacturing_tolerance_spread=True), LEVEL_TWO
        )
        self.assertAlmostEqual(out["total_db"], 3.5, places=12)
        self.assertAlmostEqual(
            out["breakdown"]["manufacturing-tolerance-spread"], 0.0
        )
        self.assertAlmostEqual(
            out["breakdown"]["temperature-induced-gap-change"], 0.5
        )

    def test_missing_coverage_statement_rejected(self):
        stated = coverage()
        del stated["power-measurement-uncertainty"]
        with self.assertRaises(ValueError):
            contribution_budget_db(stated, LEVEL_TWO)

    def test_unknown_contribution_in_coverage_rejected(self):
        stated = coverage()
        stated["solar-array-shadowing"] = True
        with self.assertRaises(ValueError):
            contribution_budget_db(stated, LEVEL_TWO)

    def test_non_boolean_statement_rejected(self):
        stated = coverage()
        stated["power-measurement-uncertainty"] = "mostly"
        with self.assertRaises(ValueError):
            contribution_budget_db(stated, LEVEL_TWO)

    def test_non_mapping_coverage_rejected(self):
        with self.assertRaises(ValueError):
            contribution_budget_db(list(MARGIN_CONTRIBUTIONS), LEVEL_TWO)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            contribution_budget_db(coverage(), "level-zero")

    def test_chart_route_rejects_a_yield_scatter_coverage_claim(self):
        out = contribution_budget_db(
            coverage(secondary_emission_yield_scatter=True), LEVEL_ONE
        )
        self.assertAlmostEqual(out["total_db"], 4.5, places=12)
        self.assertEqual(
            out["rejected_coverage_claims"], ["secondary-emission-yield-scatter"]
        )

    def test_chart_route_rejects_a_field_model_coverage_claim(self):
        out = contribution_budget_db(
            coverage(electromagnetic_field_model_error=True), LEVEL_ONE
        )
        self.assertAlmostEqual(
            out["breakdown"]["electromagnetic-field-model-error"], 1.0
        )

    def test_chart_route_accepts_a_tolerance_coverage_claim(self):
        out = contribution_budget_db(
            coverage(manufacturing_tolerance_spread=True), LEVEL_ONE
        )
        self.assertAlmostEqual(out["total_db"], 3.5, places=12)
        self.assertEqual(out["rejected_coverage_claims"], [])


class TestEquipmentAndHeritage(unittest.TestCase):
    def test_sealed_waveguide_run_is_the_reference(self):
        self.assertAlmostEqual(equipment_type_adder_db("waveguide-passive-unit"), 0.0)

    def test_radiating_element_carries_more(self):
        self.assertGreater(
            equipment_type_adder_db("antenna-feed-radiating-element"),
            equipment_type_adder_db("coaxial-passive-unit"),
        )

    def test_unknown_equipment_type_rejected(self):
        with self.assertRaises(ValueError):
            equipment_type_adder_db("deployable-boom-hinge")

    def test_non_string_equipment_type_rejected(self):
        with self.assertRaises(ValueError):
            equipment_type_adder_db(7)

    def test_new_design_earns_no_credit(self):
        credit, finding = heritage_credit_db("new-design")
        self.assertAlmostEqual(credit, 0.0)
        self.assertEqual(finding, "")

    def test_qualified_recurring_design_earns_credit(self):
        credit, finding = heritage_credit_db("qualified-identical-design")
        self.assertAlmostEqual(credit, 1.0)
        self.assertEqual(finding, "")

    def test_credit_withheld_when_the_manufacturing_route_changed(self):
        credit, finding = heritage_credit_db(
            "qualified-identical-design", same_manufacturing_route=False
        )
        self.assertAlmostEqual(credit, 0.0)
        self.assertTrue(finding)

    def test_no_finding_when_there_was_no_credit_to_withhold(self):
        credit, finding = heritage_credit_db(
            "new-design", same_manufacturing_route=False
        )
        self.assertAlmostEqual(credit, 0.0)
        self.assertEqual(finding, "")

    def test_unknown_heritage_category_rejected(self):
        with self.assertRaises(ValueError):
            heritage_credit_db("flown-on-something-similar")

    def test_non_boolean_route_flag_rejected(self):
        with self.assertRaises(ValueError):
            heritage_credit_db("new-design", same_manufacturing_route="yes")


class TestRequirementAssembly(unittest.TestCase):
    def test_unbounded_detailed_route_case(self):
        out = required_analysis_margin_db(baseline_case())
        self.assertAlmostEqual(out["required_margin_db"], 8.5, places=12)
        self.assertFalse(out["floor_applied"])
        self.assertEqual(out["findings"], [])

    def test_chart_route_case_owes_more(self):
        out = required_analysis_margin_db(baseline_case(analysis_level=LEVEL_ONE))
        self.assertAlmostEqual(out["required_margin_db"], 10.5, places=12)

    def test_full_coverage_leaves_only_the_base(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        out = required_analysis_margin_db(baseline_case(coverage=stated))
        self.assertAlmostEqual(out["required_margin_db"], 4.0, places=12)

    def test_equipment_adder_raises_the_requirement(self):
        out = required_analysis_margin_db(
            baseline_case(equipment_type="antenna-feed-radiating-element")
        )
        self.assertAlmostEqual(out["required_margin_db"], 9.5, places=12)

    def test_heritage_credit_lowers_the_requirement(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        out = required_analysis_margin_db(
            baseline_case(coverage=stated, heritage="qualified-identical-design")
        )
        self.assertAlmostEqual(out["required_margin_db"], 3.0, places=12)
        self.assertFalse(out["floor_applied"])

    def test_result_exactly_at_the_floor_is_not_floor_driven(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        out = required_analysis_margin_db(
            baseline_case(coverage=stated, heritage="qualified-identical-design")
        )
        self.assertAlmostEqual(out["assembled_margin_db"], out["floor_db"], places=12)
        self.assertFalse(out["floor_applied"])

    def test_credits_cannot_drive_the_requirement_below_the_floor(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        policy = {"heritage_credit_db": {"qualified-identical-design": 2.0}}
        out = required_analysis_margin_db(
            baseline_case(coverage=stated, heritage="qualified-identical-design"),
            policy,
        )
        self.assertAlmostEqual(out["assembled_margin_db"], 2.0, places=12)
        self.assertAlmostEqual(out["required_margin_db"], 3.0, places=12)
        self.assertTrue(out["floor_applied"])

    def test_rejected_coverage_claim_is_reported(self):
        out = required_analysis_margin_db(
            baseline_case(
                analysis_level=LEVEL_ONE,
                coverage=coverage(secondary_emission_yield_scatter=True),
            )
        )
        self.assertEqual(len(out["findings"]), 1)
        self.assertAlmostEqual(out["required_margin_db"], 10.5, places=12)

    def test_withheld_credit_is_reported(self):
        out = required_analysis_margin_db(
            baseline_case(
                heritage="qualified-identical-design",
                same_manufacturing_route=False,
            )
        )
        self.assertAlmostEqual(out["heritage_credit_db"], 0.0)
        self.assertEqual(len(out["findings"]), 1)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            required_analysis_margin_db([LEVEL_TWO])

    def test_missing_analysis_level_rejected(self):
        case = baseline_case()
        del case["analysis_level"]
        with self.assertRaises(ValueError):
            required_analysis_margin_db(case)


class TestAchievedMargin(unittest.TestCase):
    def test_factor_of_ten_is_ten_decibel(self):
        self.assertAlmostEqual(achieved_analysis_margin_db(1000.0, 100.0), 10.0, places=12)

    def test_operating_above_threshold_is_negative(self):
        self.assertLess(achieved_analysis_margin_db(100.0, 1000.0), 0.0)

    def test_non_positive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            achieved_analysis_margin_db(0.0, 100.0)

    def test_non_positive_operating_level_rejected(self):
        with self.assertRaises(ValueError):
            achieved_analysis_margin_db(1000.0, 0.0)

    def test_power_limit_inverts_the_requirement(self):
        limit = power_limit_for_required_margin_w(1000.0, 10.0)
        self.assertAlmostEqual(limit, 100.0, places=9)

    def test_negative_requirement_rejected(self):
        with self.assertRaises(ValueError):
            power_limit_for_required_margin_w(1000.0, -1.0)


class TestCaseAssessment(unittest.TestCase):
    def test_case_above_its_requirement_is_compliant(self):
        rec = assess_analysis_margin_case(baseline_case())
        self.assertTrue(rec["compliant"])
        self.assertAlmostEqual(rec["achieved_margin_db"], 10.0, places=12)
        self.assertAlmostEqual(rec["shortfall_db"], 0.0)
        self.assertEqual(rec["findings"], [])

    def test_case_below_its_requirement_reports_the_shortfall(self):
        rec = assess_analysis_margin_case(baseline_case(operating_power_w=300.0))
        self.assertFalse(rec["compliant"])
        self.assertAlmostEqual(rec["shortfall_db"], 3.2712125, places=6)
        self.assertEqual(len(rec["findings"]), 1)

    def test_case_sitting_exactly_on_its_requirement_is_compliant(self):
        # The operating level is derived from the assembled requirement, so the
        # achieved value round-trips through a power and a logarithm and can
        # land either side of it by a few units in the last place.
        requirement = required_analysis_margin_db(baseline_case())
        operating = power_limit_for_required_margin_w(
            1000.0, requirement["required_margin_db"]
        )
        rec = assess_analysis_margin_case(
            baseline_case(operating_power_w=operating)
        )
        self.assertTrue(rec["compliant"])
        self.assertAlmostEqual(rec["shortfall_db"], 0.0)
        self.assertAlmostEqual(rec["achieved_margin_db"], 8.5, places=9)

    def test_allowed_operating_level_matches_the_requirement(self):
        rec = assess_analysis_margin_case(baseline_case())
        self.assertAlmostEqual(rec["allowed_power_w"], 141.2537545, places=6)

    def test_chart_route_findings_survive_into_the_case_record(self):
        rec = assess_analysis_margin_case(
            baseline_case(
                analysis_level=LEVEL_ONE,
                coverage=coverage(electromagnetic_field_model_error=True),
                operating_power_w=300.0,
            )
        )
        self.assertEqual(len(rec["findings"]), 2)

    def test_missing_threshold_rejected(self):
        case = baseline_case()
        del case["threshold_power_w"]
        with self.assertRaises(ValueError):
            assess_analysis_margin_case(case)


class TestMarginRegister(unittest.TestCase):
    def _cases(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        return [
            baseline_case(identifier="comfortable-gap"),
            baseline_case(identifier="tight-gap", operating_power_w=300.0),
            baseline_case(
                identifier="floor-driven-gap",
                coverage=stated,
                heritage="qualified-identical-design",
                operating_power_w=10.0,
            ),
        ]

    def test_register_counts_and_worst_shortfall(self):
        out = summarize_margin_register(self._cases())
        self.assertEqual(out["case_count"], 3)
        self.assertEqual(out["compliant_count"], 2)
        self.assertEqual(out["non_compliant"], ["tight-gap"])
        self.assertFalse(out["unit_compliant"])
        self.assertAlmostEqual(out["worst_shortfall_db"], 3.2712125, places=6)

    def test_register_reports_the_highest_requirement(self):
        out = summarize_margin_register(self._cases())
        self.assertAlmostEqual(out["highest_requirement_db"], 8.5, places=12)

    def test_floor_driven_cases_are_named(self):
        stated = {c: True for c in MARGIN_CONTRIBUTIONS}
        policy = {"heritage_credit_db": {"qualified-identical-design": 2.0}}
        cases = [
            baseline_case(
                identifier="credit-heavy-gap",
                coverage=stated,
                heritage="qualified-identical-design",
            )
        ]
        out = summarize_margin_register(cases, policy)
        self.assertEqual(out["floor_driven"], ["credit-heavy-gap"])
        self.assertTrue(out["unit_compliant"])

    def test_clean_register_rolls_up_compliant(self):
        out = summarize_margin_register(self._cases()[:1])
        self.assertTrue(out["unit_compliant"])
        self.assertEqual(out["floor_driven"], [])

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            summarize_margin_register([])

    def test_non_list_register_rejected(self):
        with self.assertRaises(ValueError):
            summarize_margin_register(baseline_case())


if __name__ == "__main__":
    unittest.main()
