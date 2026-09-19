#!/usr/bin/env python3
"""Gate 3 contract test for e2040-preliminary-support-maintenance-plan.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_preliminary_support_maintenance_plan.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_preliminary_support_maintenance_plan_logic import (  # noqa: E402
    MAINTENANCE_SKILLS,
    MITIGATIONS,
    at_least,
    at_risk_parts,
    evaluate_support_maintenance_plan,
    expected_demand,
    maintenance_occurrences,
    meets_mitigation_target,
    mitigation_coverage,
    normalize_mitigation,
    normalize_skill,
    support_end_year,
    support_period_months,
    total_operating_hours,
    validate_maintenance_tasks,
    validate_obsolescence,
    validate_spares,
    validate_support,
)


def base_plan():
    return {
        "support": {
            "period_years": 5.0,
            "operating_hours_per_year": 2000.0,
            "units_in_service": 2,
            "delivery_year": 2030,
        },
        "maintenance_tasks": [
            {
                "name": "calibration check",
                "interval_months": 12.0,
                "duration_hours": 4.0,
                "skill": "technician",
            },
            {
                "name": "connector inspection",
                "interval_months": 24.0,
                "duration_hours": 2.0,
                "skill": "operator",
            },
        ],
        "spares": [
            {"part": "power switch", "quantity_held": 1, "mtbf_hours": 20000.0},
            {"part": "sensor", "quantity_held": 1, "mtbf_hours": 40000.0},
        ],
        "obsolescence": [
            {
                "part": "power switch",
                "end_of_life_year": 2032,
                "mitigation": "lifetime-buy",
                "lifetime_buy_quantity": 1,
                "mtbf_hours": 20000.0,
            },
            {
                "part": "sensor",
                "end_of_life_year": 2040,
                "mitigation": "none",
            },
        ],
        "mitigation_target": 1.0,
    }


def codes(result):
    return sorted({finding["code"] for finding in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_mitigation_alias_folds(self):
        self.assertEqual(normalize_mitigation("last-time-buy"), "lifetime-buy")

    def test_second_source_folds(self):
        self.assertEqual(normalize_mitigation("Second Source"), "alternate-source")

    def test_unmitigated_folds_to_none(self):
        self.assertEqual(normalize_mitigation("unmitigated"), "none")

    def test_unknown_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mitigation("hope")

    def test_skill_alias_folds(self):
        self.assertEqual(normalize_skill("Maintainer"), "technician")

    def test_unknown_skill_rejected(self):
        with self.assertRaises(ValueError):
            normalize_skill("intern")

    def test_vocabularies_are_closed(self):
        self.assertEqual(len(MITIGATIONS), 4)
        self.assertEqual(len(MAINTENANCE_SKILLS), 3)


class TestSupportWindow(unittest.TestCase):
    def test_period_converts_to_months(self):
        self.assertAlmostEqual(support_period_months(5.0), 60.0, places=9)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            support_period_months(0.0)

    def test_negative_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_support(
                {
                    "period_years": -1.0,
                    "operating_hours_per_year": 100.0,
                    "units_in_service": 1,
                }
            )

    def test_support_end_year_follows_delivery(self):
        support = validate_support(base_plan()["support"])
        self.assertAlmostEqual(support_end_year(support), 2035.0, places=9)

    def test_unknown_support_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_support(
                {
                    "period_years": 1.0,
                    "operating_hours_per_year": 1.0,
                    "units_in_service": 1,
                    "warranty": True,
                }
            )

    def test_missing_units_rejected(self):
        with self.assertRaises(ValueError):
            validate_support(
                {"period_years": 1.0, "operating_hours_per_year": 1.0}
            )

    def test_fleet_hours_multiply_out(self):
        self.assertAlmostEqual(
            total_operating_hours(2000.0, 2, 5.0), 20000.0, places=9
        )

    def test_no_unit_in_service_rejected(self):
        plan = base_plan()
        plan["support"]["units_in_service"] = 0
        with self.assertRaises(ValueError):
            evaluate_support_maintenance_plan(plan)


class TestMaintenanceIntervals(unittest.TestCase):
    def test_occurrences_of_a_yearly_task(self):
        self.assertEqual(maintenance_occurrences(12.0, 60.0), 5)

    def test_partial_interval_is_not_counted(self):
        self.assertEqual(maintenance_occurrences(24.0, 60.0), 2)

    def test_exact_division_counts_the_last_occurrence(self):
        self.assertEqual(maintenance_occurrences(1.2, 6.0), 5)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_occurrences(0.0, 60.0)

    def test_task_longer_than_the_window_never_falls_due(self):
        plan = base_plan()
        plan["maintenance_tasks"][1]["interval_months"] = 72.0
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("maintenance-task-never-due", codes(result))

    def test_task_exactly_the_window_length_still_falls_due(self):
        plan = base_plan()
        plan["maintenance_tasks"][1]["interval_months"] = 60.0
        result = evaluate_support_maintenance_plan(plan)
        self.assertNotIn("maintenance-task-never-due", codes(result))

    def test_schedule_reports_occurrences_per_task(self):
        result = evaluate_support_maintenance_plan(base_plan())
        schedule = {row["task"]: row["occurrences"] for row in
                    result["maintenance_schedule"]}
        self.assertEqual(schedule["calibration check"], 5)
        self.assertEqual(schedule["connector inspection"], 2)

    def test_duplicate_task_rejected(self):
        tasks = base_plan()["maintenance_tasks"]
        tasks.append(dict(tasks[0]))
        with self.assertRaises(ValueError):
            validate_maintenance_tasks(tasks)

    def test_unknown_task_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_tasks(
                [{"name": "a", "interval_months": 1.0, "crew": 2}]
            )


class TestSparesDemand(unittest.TestCase):
    def test_demand_from_mean_time_between_failures(self):
        self.assertAlmostEqual(expected_demand(20000.0, 20000.0), 1.0, places=9)

    def test_fractional_demand_is_kept(self):
        self.assertAlmostEqual(expected_demand(20000.0, 40000.0), 0.5, places=9)

    def test_zero_mtbf_rejected(self):
        with self.assertRaises(ValueError):
            expected_demand(100.0, 0.0)

    def test_holding_exactly_on_the_demand_is_sufficient(self):
        self.assertTrue(at_least(1, 20000.0 / 20000.0))

    def test_holding_below_demand_is_a_finding(self):
        plan = base_plan()
        plan["spares"][0]["quantity_held"] = 0
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("spares-below-expected-demand", codes(result))

    def test_demand_reported_per_part(self):
        result = evaluate_support_maintenance_plan(base_plan())
        demand = {row["part"]: row["demand"] for row in result["spares_demand"]}
        self.assertAlmostEqual(demand["sensor"], 0.5, places=9)

    def test_duplicate_spare_rejected(self):
        spares = base_plan()["spares"]
        spares.append(dict(spares[0]))
        with self.assertRaises(ValueError):
            validate_spares(spares)

    def test_negative_holding_rejected(self):
        with self.assertRaises(ValueError):
            validate_spares(
                [{"part": "x", "quantity_held": -1, "mtbf_hours": 10.0}]
            )

    def test_boolean_holding_rejected(self):
        with self.assertRaises(ValueError):
            validate_spares(
                [{"part": "x", "quantity_held": True, "mtbf_hours": 10.0}]
            )


class TestObsolescence(unittest.TestCase):
    def test_part_outside_the_window_is_not_at_risk(self):
        parts = validate_obsolescence(base_plan()["obsolescence"])
        self.assertEqual([p["part"] for p in at_risk_parts(parts, 2035.0)],
                         ["power switch"])

    def test_part_ending_exactly_at_the_window_edge_is_at_risk(self):
        parts = validate_obsolescence(
            [{"part": "x", "end_of_life_year": 2035, "mitigation": "none"}]
        )
        self.assertEqual(len(at_risk_parts(parts, 2035.0)), 1)

    def test_unmitigated_at_risk_part_is_a_finding(self):
        plan = base_plan()
        plan["obsolescence"][0]["mitigation"] = "none"
        del plan["obsolescence"][0]["lifetime_buy_quantity"]
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("obsolescence-unmitigated", codes(result))

    def test_lifetime_buy_short_of_demand_is_a_finding(self):
        plan = base_plan()
        plan["obsolescence"][0]["lifetime_buy_quantity"] = 0
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("lifetime-buy-quantity-short", codes(result))

    def test_lifetime_buy_without_failure_rate_cannot_be_sized(self):
        plan = base_plan()
        del plan["obsolescence"][0]["mtbf_hours"]
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("lifetime-buy-unsized", codes(result))

    def test_alternate_source_needs_no_sizing(self):
        plan = base_plan()
        plan["obsolescence"][0] = {
            "part": "power switch",
            "end_of_life_year": 2032,
            "mitigation": "alternate-source",
        }
        result = evaluate_support_maintenance_plan(plan)
        self.assertEqual(result["findings"], [])

    def test_spare_with_no_obsolescence_entry_is_a_finding(self):
        plan = base_plan()
        plan["spares"].append(
            {"part": "relay", "quantity_held": 2, "mtbf_hours": 90000.0}
        )
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("spare-without-obsolescence-assessment", codes(result))

    def test_duplicate_obsolescence_entry_rejected(self):
        parts = base_plan()["obsolescence"]
        parts.append(dict(parts[0]))
        with self.assertRaises(ValueError):
            validate_obsolescence(parts)

    def test_implausible_end_of_life_year_rejected(self):
        with self.assertRaises(ValueError):
            validate_obsolescence([{"part": "x", "end_of_life_year": 32}])


class TestCoveragePortability(unittest.TestCase):
    def test_coverage_of_a_single_mitigated_part(self):
        parts = validate_obsolescence(base_plan()["obsolescence"])
        self.assertAlmostEqual(mitigation_coverage(parts, 2035.0), 1.0, places=9)

    def test_coverage_is_one_in_two(self):
        plan = base_plan()
        plan["obsolescence"][1]["end_of_life_year"] = 2033
        parts = validate_obsolescence(plan["obsolescence"])
        self.assertAlmostEqual(mitigation_coverage(parts, 2035.0), 0.5, places=9)

    def test_coverage_below_target_is_a_finding(self):
        plan = base_plan()
        plan["obsolescence"][1]["end_of_life_year"] = 2033
        result = evaluate_support_maintenance_plan(plan)
        self.assertIn("mitigation-coverage-below-target", codes(result))

    def test_coverage_exactly_on_a_relaxed_target_passes(self):
        plan = base_plan()
        plan["obsolescence"][1]["end_of_life_year"] = 2033
        plan["mitigation_target"] = 0.5
        result = evaluate_support_maintenance_plan(plan)
        self.assertNotIn("mitigation-coverage-below-target", codes(result))

    def test_target_exactly_met_by_a_third(self):
        self.assertTrue(meets_mitigation_target(1.0 / 3.0, 1.0 / 3.0))

    def test_target_outside_unit_interval_rejected(self):
        plan = base_plan()
        plan["mitigation_target"] = 1.5
        with self.assertRaises(ValueError):
            evaluate_support_maintenance_plan(plan)

    def test_coverage_needs_an_at_risk_part(self):
        with self.assertRaises(ValueError):
            mitigation_coverage([], 2035.0)


class TestPlanAssessment(unittest.TestCase):
    def test_clean_plan_is_sufficient(self):
        result = evaluate_support_maintenance_plan(base_plan())
        self.assertTrue(result["sufficient"])
        self.assertAlmostEqual(result["support_period_months"], 60.0, places=9)
        self.assertAlmostEqual(result["fleet_operating_hours"], 20000.0, places=9)
        self.assertEqual(result["at_risk_parts"], ["power switch"])

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["warranty_terms"] = "none"
        with self.assertRaises(ValueError):
            evaluate_support_maintenance_plan(plan)

    def test_missing_support_block_rejected(self):
        plan = base_plan()
        del plan["support"]
        with self.assertRaises(ValueError):
            evaluate_support_maintenance_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_support_maintenance_plan([("support", {})])

    def test_coverage_is_absent_when_no_part_is_at_risk(self):
        plan = base_plan()
        plan["obsolescence"][0]["end_of_life_year"] = 2041
        result = evaluate_support_maintenance_plan(plan)
        self.assertIsNone(result["mitigation_coverage"])


if __name__ == "__main__":
    unittest.main()
