#!/usr/bin/env python3
"""Contract test for the Annex A EMC control plan contents leaf.

Offline, deterministic, stdlib unittest. Run: python3 this_file.py
"""

import copy
import math
import unittest

from e20_emc_control_plan_contents_logic import (
    CONTROL_MEASURES,
    MECHANISMS,
    REQUIRED_BLOCKS,
    aggregate_emission_dbuv,
    assess_budget_table,
    assess_control_plan,
    check_block_presence,
    check_schedule_milestones,
    evaluate_budget_entry,
    normalize_anchor,
    normalize_block_key,
    normalize_measure,
    normalize_mechanism,
    validate_control_measure_register,
    validate_organisation_block,
)

FULL_REGISTER = [
    {"mechanism": "conducted-emission", "measure": "filtering-scheme",
     "owner": "power-conditioning-engineer"},
    {"mechanism": "conducted-susceptibility", "measure": "galvanic-isolation-scheme",
     "owner": "power-conditioning-engineer"},
    {"mechanism": "radiated-emission", "measure": "shielding-scheme",
     "owner": "harness-engineer"},
    {"mechanism": "radiated-susceptibility", "measure": "cable-category-segregation",
     "owner": "harness-engineer"},
    {"mechanism": "electrostatic-discharge", "measure": "bonding-scheme",
     "owner": "structure-engineer"},
    {"mechanism": "lightning-induced-transient", "measure": "bonding-scheme",
     "owner": "structure-engineer"},
]

GOOD_BUDGET_ROW = {
    "victim": "star-tracker-head",
    "mechanism": "radiated-susceptibility",
    "susceptibility_level_dbuv": 60.0,
    "emitter_levels_dbuv": [40.0, 40.0],
}

TIGHT_BUDGET_ROW = {
    "victim": "magnetometer-boom",
    "mechanism": "radiated-susceptibility",
    "susceptibility_level_dbuv": 40.0,
    "emitter_levels_dbuv": [34.0],
}


def make_plan():
    return copy.deepcopy({
        "organisation-and-responsibility": {
            "responsible_authority": "compatibility-lead-engineer",
            "reporting_path": "compatibility-lead to project-engineering-manager",
            "control_board_interface": "configuration-control-board",
            "delegates": [
                {"name": "harness-engineer", "scope": "cable-category-segregation"},
            ],
        },
        "control-measure-register": FULL_REGISTER,
        "electromagnetic-budget-table": [GOOD_BUDGET_ROW],
        "verification-approach-reference": "verification plan reference vp-001",
        "schedule-and-milestone-list": [
            {"name": "grounding-scheme-frozen", "anchor": "pdr", "lead_days": 45},
            {"name": "budget-table-reissued", "anchor": "cdr", "lead_days": 60},
        ],
        "deviation-handling-route": "deviation raised to the control board",
    })


class NormalizationTests(unittest.TestCase):
    def test_block_synonyms_resolve(self):
        self.assertEqual(normalize_block_key("budgets"),
                         "electromagnetic-budget-table")
        self.assertEqual(normalize_block_key("Responsibilities"),
                         "organisation-and-responsibility")
        self.assertEqual(normalize_block_key("waiver route"),
                         "deviation-handling-route")

    def test_every_required_block_round_trips(self):
        for block in REQUIRED_BLOCKS:
            self.assertEqual(normalize_block_key(block), block)

    def test_unknown_block_rejected(self):
        with self.assertRaises(ValueError):
            normalize_block_key("cost-breakdown")

    def test_mechanism_synonyms_resolve(self):
        self.assertEqual(normalize_mechanism("ce"), "conducted-emission")
        self.assertEqual(normalize_mechanism("ESD"), "electrostatic-discharge")
        self.assertEqual(normalize_mechanism("indirect lightning"),
                         "lightning-induced-transient")

    def test_every_mechanism_round_trips(self):
        for mechanism in MECHANISMS:
            self.assertEqual(normalize_mechanism(mechanism), mechanism)

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mechanism("micrometeoroid-impact")

    def test_measure_synonyms_resolve(self):
        self.assertEqual(normalize_measure("bonding"), "bonding-scheme")
        self.assertEqual(normalize_measure("isolation"),
                         "galvanic-isolation-scheme")
        for measure in CONTROL_MEASURES:
            self.assertEqual(normalize_measure(measure), measure)

    def test_non_string_measure_rejected(self):
        with self.assertRaises(ValueError):
            normalize_measure(None)

    def test_anchor_synonyms_resolve(self):
        self.assertEqual(normalize_anchor("pdr"), "preliminary-design-review")
        self.assertEqual(normalize_anchor("FRR"), "flight-readiness-review")

    def test_unknown_anchor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_anchor("kick-off-meeting")


class BlockPresenceTests(unittest.TestCase):
    def test_full_plan_is_complete(self):
        out = check_block_presence(make_plan())
        self.assertTrue(out["complete"])
        self.assertEqual(out["missing"], [])
        self.assertEqual(len(out["declared"]), len(REQUIRED_BLOCKS))

    def test_missing_block_is_reported(self):
        plan = make_plan()
        del plan["deviation-handling-route"]
        out = check_block_presence(plan)
        self.assertFalse(out["complete"])
        self.assertEqual(out["missing"], ["deviation-handling-route"])

    def test_declared_but_empty_block_counts_as_missing(self):
        plan = make_plan()
        plan["electromagnetic-budget-table"] = []
        out = check_block_presence(plan)
        self.assertIn("electromagnetic-budget-table", out["missing"])

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            check_block_presence(["organisation"])

    def test_unknown_block_key_rejected(self):
        plan = make_plan()
        plan["cost-breakdown"] = "n/a"
        with self.assertRaises(ValueError):
            check_block_presence(plan)


class OrganisationBlockTests(unittest.TestCase):
    def test_complete_block_has_no_finding(self):
        self.assertEqual(
            validate_organisation_block(
                make_plan()["organisation-and-responsibility"]), [])

    def test_unnamed_owner_is_a_finding(self):
        block = make_plan()["organisation-and-responsibility"]
        block["responsible_authority"] = "  "
        findings = validate_organisation_block(block)
        self.assertEqual(findings[0]["finding"], "compatibility-owner-unnamed")

    def test_missing_route_and_forum_are_both_findings(self):
        block = make_plan()["organisation-and-responsibility"]
        del block["reporting_path"]
        del block["control_board_interface"]
        findings = validate_organisation_block(block)
        self.assertEqual(len(findings), 2)

    def test_delegate_without_scope_is_a_finding(self):
        block = make_plan()["organisation-and-responsibility"]
        block["delegates"] = [{"name": "harness-engineer"}]
        findings = validate_organisation_block(block)
        self.assertEqual(findings[0]["finding"], "delegate-scope-undeclared")

    def test_delegates_as_bare_string_rejected(self):
        block = make_plan()["organisation-and-responsibility"]
        block["delegates"] = "harness-engineer"
        with self.assertRaises(ValueError):
            validate_organisation_block(block)

    def test_non_mapping_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_organisation_block("compatibility-lead-engineer")


class RegisterTests(unittest.TestCase):
    def test_full_register_has_no_finding(self):
        out = validate_control_measure_register(FULL_REGISTER)
        self.assertEqual(out["findings"], [])
        self.assertEqual(len(out["covered"]), len(MECHANISMS))

    def test_measure_that_does_not_act_on_the_path_is_a_finding(self):
        register = copy.deepcopy(FULL_REGISTER)
        register[2]["measure"] = "filtering-scheme"
        out = validate_control_measure_register(register)
        kinds = [f["finding"] for f in out["findings"]]
        self.assertIn("measure-does-not-act-on-mechanism", kinds)
        self.assertIn("mechanism-uncontrolled", kinds)

    def test_uncovered_mechanism_is_a_finding(self):
        out = validate_control_measure_register(FULL_REGISTER[:-1])
        self.assertEqual(out["findings"][0]["finding"], "mechanism-uncontrolled")
        self.assertEqual(out["findings"][0]["mechanism"],
                         "lightning-induced-transient")

    def test_unowned_measure_is_a_finding(self):
        register = copy.deepcopy(FULL_REGISTER)
        register[0]["owner"] = ""
        out = validate_control_measure_register(register)
        self.assertEqual(out["findings"][0]["finding"], "measure-owner-unnamed")

    def test_narrowed_scope_drops_the_coverage_demand(self):
        out = validate_control_measure_register(
            FULL_REGISTER[:1], ["conducted-emission"])
        self.assertEqual(out["findings"], [])

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_measure_register([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_measure_register(["filtering-scheme"])


class AggregateEmissionTests(unittest.TestCase):
    def test_single_emitter_returns_its_own_level(self):
        self.assertAlmostEqual(aggregate_emission_dbuv([44.0]), 44.0, places=9)

    def test_two_equal_emitters_add_about_three_decibels(self):
        self.assertAlmostEqual(aggregate_emission_dbuv([20.0, 20.0]),
                               23.010299956639813, places=9)

    def test_dominant_emitter_dominates_the_sum(self):
        aggregate = aggregate_emission_dbuv([50.0, 30.0])
        self.assertAlmostEqual(aggregate, 50.04321373782642, places=9)

    def test_levels_combine_by_power_not_by_addition(self):
        self.assertLess(aggregate_emission_dbuv([20.0, 20.0]), 40.0)

    def test_empty_emitter_set_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_emission_dbuv([])

    def test_non_numeric_level_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_emission_dbuv([20.0, "30"])

    def test_bare_string_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_emission_dbuv("20")

    def test_infinite_level_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_emission_dbuv([float("inf")])


class BudgetTests(unittest.TestCase):
    def test_compliant_row_reports_no_shortfall(self):
        row = evaluate_budget_entry(GOOD_BUDGET_ROW)
        self.assertTrue(row["compliant"])
        self.assertEqual(row["shortfall_db"], 0.0)
        self.assertAlmostEqual(row["aggregate_emission_dbuv"],
                               43.010299956639813, places=9)
        self.assertAlmostEqual(row["margin_db"], 16.989700043360187, places=9)

    def test_short_margin_row_reports_the_shortfall(self):
        entry = dict(GOOD_BUDGET_ROW, susceptibility_level_dbuv=45.0)
        row = evaluate_budget_entry(entry)
        self.assertFalse(row["compliant"])
        self.assertAlmostEqual(row["shortfall_db"], 4.010299956639813, places=9)

    def test_requirement_met_within_representation_error_stays_compliant(self):
        # The margin is physically exactly at the requirement; the declared
        # requirement is then nudged one ULP above the computed margin. The
        # engineering requirement is not widened -- only the float
        # representation error of the power sum is absorbed.
        row = evaluate_budget_entry(TIGHT_BUDGET_ROW, 6.0)
        required = math.nextafter(row["margin_db"], math.inf)
        self.assertFalse(row["margin_db"] >= required)
        tight = evaluate_budget_entry(TIGHT_BUDGET_ROW, required)
        self.assertTrue(tight["compliant"])
        self.assertEqual(tight["shortfall_db"], 0.0)

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_budget_entry(GOOD_BUDGET_ROW, -1.0)

    def test_unnamed_victim_rejected(self):
        entry = dict(GOOD_BUDGET_ROW, victim="")
        with self.assertRaises(ValueError):
            evaluate_budget_entry(entry)

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_budget_entry("star-tracker-head")

    def test_table_reports_the_worst_row(self):
        table = assess_budget_table([
            GOOD_BUDGET_ROW,
            dict(GOOD_BUDGET_ROW, victim="reaction-wheel-driver",
                 susceptibility_level_dbuv=46.0),
        ])
        self.assertEqual(table["worst_victim"], "reaction-wheel-driver")
        self.assertAlmostEqual(table["worst_margin_db"], 2.989700043360187,
                               places=9)
        self.assertEqual(len(table["breaches"]), 1)
        self.assertEqual(table["findings"][0]["finding"], "margin-shortfall")

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            assess_budget_table([])


class ScheduleTests(unittest.TestCase):
    def test_good_schedule_has_no_finding(self):
        out = check_schedule_milestones(make_plan()["schedule-and-milestone-list"])
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["anchored"],
                         ["critical-design-review", "preliminary-design-review"])

    def test_short_lead_is_a_finding(self):
        milestones = make_plan()["schedule-and-milestone-list"]
        milestones[0]["lead_days"] = 5
        out = check_schedule_milestones(milestones)
        self.assertEqual(out["findings"][0]["finding"], "milestone-lead-too-short")

    def test_milestone_after_its_review_is_a_finding(self):
        milestones = make_plan()["schedule-and-milestone-list"]
        milestones[1]["lead_days"] = -3
        out = check_schedule_milestones(milestones)
        self.assertEqual(out["findings"][0]["finding"],
                         "milestone-lands-after-its-review")

    def test_unserved_review_anchor_is_a_finding(self):
        milestones = make_plan()["schedule-and-milestone-list"][:1]
        out = check_schedule_milestones(milestones)
        self.assertEqual(out["findings"][0]["anchor"], "critical-design-review")
        self.assertEqual(out["findings"][0]["finding"], "review-anchor-unserved")

    def test_non_integer_lead_rejected(self):
        milestones = make_plan()["schedule-and-milestone-list"]
        milestones[0]["lead_days"] = 30.5
        with self.assertRaises(ValueError):
            check_schedule_milestones(milestones)

    def test_unnamed_milestone_rejected(self):
        milestones = make_plan()["schedule-and-milestone-list"]
        milestones[0]["name"] = ""
        with self.assertRaises(ValueError):
            check_schedule_milestones(milestones)

    def test_empty_schedule_rejected(self):
        with self.assertRaises(ValueError):
            check_schedule_milestones([])

    def test_negative_minimum_lead_rejected(self):
        with self.assertRaises(ValueError):
            check_schedule_milestones(
                make_plan()["schedule-and-milestone-list"], -1)


class ControlPlanAssessmentTests(unittest.TestCase):
    def test_complete_plan_is_acceptable(self):
        out = assess_control_plan(make_plan())
        self.assertTrue(out["acceptable"])
        self.assertEqual(out["findings"], [])
        self.assertTrue(out["presence"]["complete"])

    def test_missing_block_makes_the_plan_unacceptable(self):
        plan = make_plan()
        del plan["verification-approach-reference"]
        out = assess_control_plan(plan)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["findings"][0]["finding"], "content-block-undeclared")

    def test_budget_breach_reaches_the_verdict(self):
        plan = make_plan()
        plan["electromagnetic-budget-table"] = [
            dict(GOOD_BUDGET_ROW, susceptibility_level_dbuv=44.0)]
        out = assess_control_plan(plan)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["budget"]["findings"][0]["finding"],
                         "margin-shortfall")

    def test_register_gap_reaches_the_verdict(self):
        plan = make_plan()
        plan["control-measure-register"] = FULL_REGISTER[:2]
        out = assess_control_plan(plan)
        self.assertFalse(out["acceptable"])
        kinds = {f["finding"] for f in out["register"]["findings"]}
        self.assertEqual(kinds, {"mechanism-uncontrolled"})

    def test_narrowed_mechanism_scope_accepts_a_short_register(self):
        plan = make_plan()
        plan["control-measure-register"] = FULL_REGISTER[:1]
        out = assess_control_plan(plan, mechanisms_in_scope=["conducted-emission"])
        self.assertTrue(out["acceptable"])

    def test_organisation_gap_reaches_the_verdict(self):
        plan = make_plan()
        plan["organisation-and-responsibility"]["control_board_interface"] = ""
        out = assess_control_plan(plan)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["organisation_findings"][0]["finding"],
                         "control-board-interface-undeclared")


if __name__ == "__main__":
    unittest.main()
