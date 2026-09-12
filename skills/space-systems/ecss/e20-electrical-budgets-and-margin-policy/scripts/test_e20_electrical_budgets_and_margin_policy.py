#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.2.2.2 electrical
budgets and margin policy.

Exercises scripts/e20_electrical_budgets_and_margin_policy_logic.py
(stdlib unittest, offline). Contract: a budget type categorizes into
exactly one domain and an unrecognized type raises; maturity resolves
to an item contingency and phase to a system margin, both raising on
an unknown key; a line item is loaded with its maturity contingency
unless its nominal already carries one, then duty-cycled, with a
negative nominal or an out-of-range duty cycle raising; an item that
declares contingency at both places is flagged rather than reconciled;
modes roll up independently and the worst case is selected
deterministically, an empty mode set raising; the required capability
is the worst-case demand loaded with the phase system margin; achieved
margin is (capability - demand) / demand graded against the policy
floor and reported with its absolute shortfall; the harness voltage
drop is graded against an allowable fraction of bus voltage; and the
aggregated review is compliant only when it carries no findings.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_budgets_and_margin_policy_logic as bm  # noqa: E402


class CategorizeBudgetTest(unittest.TestCase):
    def test_power_is_power_domain(self):
        self.assertEqual(bm.categorize_budget("power"), "power")

    def test_voltage_drop_is_power_domain(self):
        self.assertEqual(bm.categorize_budget("voltage_drop"), "power")

    def test_data_bus_bandwidth_is_signal_domain(self):
        self.assertEqual(bm.categorize_budget("data_bus_bandwidth"), "signal")

    def test_harness_mass_is_physical_domain(self):
        self.assertEqual(bm.categorize_budget("harness_mass"), "physical")

    def test_every_known_budget_type_resolves_to_a_domain(self):
        for domain, members in bm.BUDGET_DOMAINS.items():
            for budget_type in members:
                self.assertEqual(bm.categorize_budget(budget_type), domain)

    def test_unrecognized_budget_type_raises(self):
        with self.assertRaises(ValueError):
            bm.categorize_budget("crew_workload")


class MarginPolicyTableTest(unittest.TestCase):
    def test_flight_measured_carries_no_contingency(self):
        self.assertAlmostEqual(bm.maturity_contingency("flight_measured"), 0.0)

    def test_new_development_carries_the_largest_contingency(self):
        largest = max(bm.MATURITY_CONTINGENCY.values())
        self.assertAlmostEqual(
            bm.maturity_contingency("new_development"), largest
        )

    def test_contingency_never_decreases_with_less_maturity(self):
        order = [
            "flight_measured",
            "qualified_off_the_shelf",
            "modified_design",
            "new_development",
        ]
        values = [bm.maturity_contingency(m) for m in order]
        self.assertEqual(values, sorted(values))

    def test_system_margin_shrinks_towards_flight(self):
        self.assertGreater(
            bm.phase_system_margin("phase_b"), bm.phase_system_margin("phase_d")
        )

    def test_unrecognized_maturity_raises(self):
        with self.assertRaises(ValueError):
            bm.maturity_contingency("breadboard_sketch")

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            bm.phase_system_margin("phase_z")


class ItemDemandTest(unittest.TestCase):
    def test_new_development_item_is_loaded_by_its_contingency(self):
        item = {"item_id": "payload", "nominal": 100.0, "maturity": "new_development"}
        self.assertAlmostEqual(bm.item_demand(item), 120.0)

    def test_flight_measured_item_is_not_loaded(self):
        item = {"item_id": "tx", "nominal": 100.0, "maturity": "flight_measured"}
        self.assertAlmostEqual(bm.item_demand(item), 100.0)

    def test_duty_cycle_scales_the_contribution(self):
        item = {
            "item_id": "heater",
            "nominal": 100.0,
            "maturity": "new_development",
            "duty_cycle": 0.25,
        }
        self.assertAlmostEqual(bm.item_demand(item), 30.0)

    def test_zero_duty_cycle_contributes_nothing(self):
        item = {
            "item_id": "heater",
            "nominal": 100.0,
            "maturity": "new_development",
            "duty_cycle": 0.0,
        }
        self.assertAlmostEqual(bm.item_demand(item), 0.0)

    def test_nominal_already_carrying_contingency_is_not_loaded_again(self):
        item = {
            "item_id": "payload",
            "nominal": 120.0,
            "maturity": "new_development",
            "nominal_includes_contingency": True,
        }
        self.assertAlmostEqual(bm.item_demand(item), 120.0)

    def test_negative_nominal_raises(self):
        item = {"item_id": "bad", "nominal": -1.0, "maturity": "flight_measured"}
        with self.assertRaises(ValueError):
            bm.item_demand(item)

    def test_duty_cycle_above_one_raises(self):
        item = {
            "item_id": "bad",
            "nominal": 10.0,
            "maturity": "flight_measured",
            "duty_cycle": 1.2,
        }
        with self.assertRaises(ValueError):
            bm.item_demand(item)

    def test_negative_duty_cycle_raises(self):
        item = {
            "item_id": "bad",
            "nominal": 10.0,
            "maturity": "flight_measured",
            "duty_cycle": -0.1,
        }
        with self.assertRaises(ValueError):
            bm.item_demand(item)

    def test_unrecognized_maturity_on_an_item_raises(self):
        item = {"item_id": "bad", "nominal": 10.0, "maturity": "vibes"}
        with self.assertRaises(ValueError):
            bm.item_demand(item)


class DoubleDeclaredContingencyTest(unittest.TestCase):
    def test_double_declaration_is_flagged(self):
        items = [
            {
                "item_id": "payload",
                "nominal": 120.0,
                "maturity": "new_development",
                "nominal_includes_contingency": True,
            }
        ]
        found = bm.item_contingency_findings(items)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "item_contingency_double_declared")
        self.assertEqual(found[0]["item"], "payload")

    def test_included_contingency_on_a_flight_measured_item_is_clean(self):
        items = [
            {
                "item_id": "tx",
                "nominal": 100.0,
                "maturity": "flight_measured",
                "nominal_includes_contingency": True,
            }
        ]
        self.assertEqual(bm.item_contingency_findings(items), [])

    def test_plain_items_are_clean(self):
        items = [{"item_id": "tx", "nominal": 100.0, "maturity": "new_development"}]
        self.assertEqual(bm.item_contingency_findings(items), [])


class WorstCaseModeTest(unittest.TestCase):
    def _modes(self):
        return {
            "safe": [{"item_id": "tx", "nominal": 20.0, "maturity": "flight_measured"}],
            "science": [
                {"item_id": "pl", "nominal": 100.0, "maturity": "new_development"},
                {
                    "item_id": "htr",
                    "nominal": 40.0,
                    "maturity": "flight_measured",
                    "duty_cycle": 0.5,
                },
            ],
        }

    def test_mode_demand_sums_loaded_duty_cycled_items(self):
        self.assertAlmostEqual(bm.mode_demand(self._modes()["science"]), 140.0)

    def test_worst_case_selects_the_driving_mode(self):
        name, demand = bm.worst_case_mode(self._modes())
        self.assertEqual(name, "science")
        self.assertAlmostEqual(demand, 140.0)

    def test_tie_resolves_to_the_first_mode_name(self):
        modes = {
            "beta": [{"item_id": "a", "nominal": 10.0, "maturity": "flight_measured"}],
            "alpha": [{"item_id": "b", "nominal": 10.0, "maturity": "flight_measured"}],
        }
        name, demand = bm.worst_case_mode(modes)
        self.assertEqual(name, "alpha")
        self.assertAlmostEqual(demand, 10.0)

    def test_empty_mode_set_raises(self):
        with self.assertRaises(ValueError):
            bm.worst_case_mode({})


class RequiredCapabilityTest(unittest.TestCase):
    def test_phase_c_loads_the_demand_by_its_system_margin(self):
        self.assertAlmostEqual(bm.required_capability(140.0, "phase_c"), 154.0)

    def test_phase_e_adds_nothing(self):
        self.assertAlmostEqual(bm.required_capability(140.0, "phase_e"), 140.0)

    def test_negative_demand_raises(self):
        with self.assertRaises(ValueError):
            bm.required_capability(-1.0, "phase_c")

    def test_unrecognized_phase_in_required_capability_raises(self):
        with self.assertRaises(ValueError):
            bm.required_capability(140.0, "phase_q")


class AchievedMarginTest(unittest.TestCase):
    def test_margin_is_the_surplus_over_demand(self):
        self.assertAlmostEqual(bm.achieved_margin(200.0, 160.0), 0.25)

    def test_capability_equal_to_demand_is_zero_margin(self):
        self.assertAlmostEqual(bm.achieved_margin(160.0, 160.0), 0.0)

    def test_margin_at_the_policy_floor_is_compliant(self):
        self.assertEqual(bm.margin_violations("pwr", 176.0, 160.0, 0.10), [])

    def test_margin_below_the_policy_floor_reports_the_shortfall(self):
        found = bm.margin_violations("pwr", 160.0, 160.0, 0.10)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["issue"], "achieved_margin_below_policy")
        self.assertAlmostEqual(found[0]["shortfall"], 16.0)

    def test_surplus_margin_is_still_graded_against_the_floor(self):
        found = bm.margin_violations("pwr", 168.0, 160.0, 0.10)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["achieved_margin"], 0.05)

    def test_zero_demand_raises(self):
        with self.assertRaises(ValueError):
            bm.achieved_margin(100.0, 0.0)

    def test_negative_capability_raises(self):
        with self.assertRaises(ValueError):
            bm.achieved_margin(-1.0, 160.0)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            bm.margin_violations("pwr", 200.0, 160.0, -0.01)


class VoltageDropBudgetTest(unittest.TestCase):
    def test_drop_is_current_times_resistance(self):
        self.assertAlmostEqual(bm.harness_voltage_drop(10.0, 0.05), 0.5)

    def test_drop_within_allowance_is_compliant(self):
        self.assertEqual(
            bm.voltage_drop_violations("hv", 10.0, 0.05, 28.0, 0.02), []
        )

    def test_drop_above_allowance_is_flagged(self):
        found = bm.voltage_drop_violations("hv", 10.0, 0.05, 28.0, 0.01)
        self.assertEqual(found[0]["issue"], "harness_voltage_drop_above_allowance")
        self.assertAlmostEqual(found[0]["allowable_v"], 0.28)

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            bm.harness_voltage_drop(-1.0, 0.05)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            bm.harness_voltage_drop(10.0, -0.05)

    def test_non_positive_bus_voltage_raises(self):
        with self.assertRaises(ValueError):
            bm.voltage_drop_violations("hv", 10.0, 0.05, 0.0, 0.02)

    def test_allowable_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            bm.voltage_drop_violations("hv", 10.0, 0.05, 28.0, 1.5)


class BudgetReviewTest(unittest.TestCase):
    def _budget(self):
        return {
            "budget_id": "platform-power",
            "budget_type": "power",
            "project_phase": "phase_c",
            "modes": {
                "safe": [
                    {"item_id": "tx", "nominal": 20.0, "maturity": "flight_measured"}
                ],
                "science": [
                    {"item_id": "pl", "nominal": 100.0, "maturity": "new_development"},
                    {
                        "item_id": "htr",
                        "nominal": 40.0,
                        "maturity": "flight_measured",
                        "duty_cycle": 0.5,
                    },
                ],
            },
            "capability": 200.0,
        }

    def test_healthy_budget_is_compliant(self):
        review = bm.budget_review(self._budget())
        self.assertEqual(review["findings"], [])
        self.assertTrue(bm.is_budget_compliant(review))

    def test_review_names_the_driving_mode_and_demand(self):
        review = bm.budget_review(self._budget())
        self.assertEqual(review["driving_mode"], "science")
        self.assertAlmostEqual(review["demand"], 140.0)
        self.assertAlmostEqual(review["required_capability"], 154.0)

    def test_review_reports_the_achieved_margin(self):
        review = bm.budget_review(self._budget())
        self.assertAlmostEqual(review["achieved_margin"], 60.0 / 140.0)

    def test_review_reports_the_domain(self):
        self.assertEqual(bm.budget_review(self._budget())["domain"], "power")

    def test_thin_capability_is_flagged(self):
        budget = self._budget()
        budget["capability"] = 150.0
        review = bm.budget_review(budget)
        self.assertEqual(
            [f["issue"] for f in review["findings"]], ["achieved_margin_below_policy"]
        )
        self.assertFalse(bm.is_budget_compliant(review))

    def test_review_surfaces_a_double_declared_item(self):
        budget = self._budget()
        budget["modes"]["science"][0]["nominal_includes_contingency"] = True
        review = bm.budget_review(budget)
        self.assertIn(
            "item_contingency_double_declared",
            [f["issue"] for f in review["findings"]],
        )

    def test_review_does_not_mutate_the_input_budget(self):
        budget = self._budget()
        before = repr(budget)
        bm.budget_review(budget)
        self.assertEqual(repr(budget), before)

    def test_zero_demand_budget_reports_no_margin_rather_than_dividing(self):
        budget = self._budget()
        budget["modes"] = {
            "off": [{"item_id": "idle", "nominal": 0.0, "maturity": "flight_measured"}]
        }
        review = bm.budget_review(budget)
        self.assertIsNone(review["achieved_margin"])
        self.assertEqual(review["findings"], [])

    def test_explicit_required_margin_overrides_the_phase_default(self):
        budget = self._budget()
        budget["required_margin"] = 0.50
        review = bm.budget_review(budget)
        self.assertEqual(
            [f["issue"] for f in review["findings"]], ["achieved_margin_below_policy"]
        )

    def test_unrecognized_budget_type_in_review_raises(self):
        budget = self._budget()
        budget["budget_type"] = "crew_workload"
        with self.assertRaises(ValueError):
            bm.budget_review(budget)


if __name__ == "__main__":
    unittest.main()
