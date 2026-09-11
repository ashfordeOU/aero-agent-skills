#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §7 pre-launch testing at launch site.

Exercises scripts/e1003_pre_launch_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 -- a health check category is
one of six recognized values and an unrecognized category raises; a health
check result of fail is a launch hold, marginal is advisory, pass is clear,
and an unrecognized result raises; a pressurized-system leak rate is compared
against its allowable limit and an exceedance is a launch hold while negative
rates raise; a functional test failure on a critical subsystem is a launch
hold and on a non-critical subsystem is advisory while a pass produces no
finding; a campaign constraint value is checked against its lower and upper
bounds and an out-of-bounds value is flagged while an unrecognized constraint
type raises; the aggregated launch-readiness review is launch-ready only
when all four categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_pre_launch_logic as pl  # noqa: E402


class CategorizeHealthCheckTest(unittest.TestCase):
    def test_structural_is_recognized(self):
        self.assertEqual(pl.categorize_health_check("structural"), "structural")

    def test_electrical_is_recognized(self):
        self.assertEqual(pl.categorize_health_check("electrical"), "electrical")

    def test_thermal_is_recognized(self):
        self.assertEqual(pl.categorize_health_check("thermal"), "thermal")

    def test_propulsion_is_recognized(self):
        self.assertEqual(pl.categorize_health_check("propulsion"), "propulsion")

    def test_software_is_recognized(self):
        self.assertEqual(pl.categorize_health_check("software"), "software")

    def test_mechanical_is_recognized(self):
        self.assertEqual(pl.categorize_health_check("mechanical"), "mechanical")

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            pl.categorize_health_check("biological")


class EvaluateHealthCheckTest(unittest.TestCase):
    def test_pass_result_no_violation(self):
        self.assertEqual(
            pl.evaluate_health_check("hc-01", "electrical", "pass"), []
        )

    def test_fail_result_is_launch_hold(self):
        violations = pl.evaluate_health_check("hc-02", "structural", "fail")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "health_check_failed_launch_hold")
        self.assertEqual(violations[0]["check_id"], "hc-02")

    def test_marginal_result_is_advisory(self):
        violations = pl.evaluate_health_check("hc-03", "thermal", "marginal")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "health_check_marginal_advisory")
        self.assertEqual(violations[0]["check_id"], "hc-03")

    def test_unknown_result_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_health_check("hc-04", "mechanical", "uncertain")

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_health_check("hc-05", "biological", "pass")


class EvaluateLeakCheckTest(unittest.TestCase):
    def test_within_limit_no_violation(self):
        self.assertEqual(
            pl.evaluate_leak_check("lc-01", "propulsion_system", 0.5, 1.0), []
        )

    def test_at_limit_exact_no_violation(self):
        self.assertEqual(
            pl.evaluate_leak_check("lc-02", "pressurized_vessel", 1.0, 1.0), []
        )

    def test_exceeds_limit_is_launch_hold(self):
        violations = pl.evaluate_leak_check(
            "lc-03", "pneumatic_line", 2.5, 1.0
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "leak_rate_exceeded_launch_hold")
        self.assertAlmostEqual(violations[0]["measured_rate_sccm"], 2.5)
        self.assertAlmostEqual(violations[0]["allowable_rate_sccm"], 1.0)

    def test_negative_measured_rate_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_leak_check("lc-04", "thruster_valve", -0.1, 1.0)

    def test_negative_allowable_rate_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_leak_check("lc-05", "thruster_valve", 0.1, -1.0)

    def test_unknown_leak_type_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_leak_check("lc-06", "magical_seal", 0.1, 1.0)


class EvaluateFunctionalTestTest(unittest.TestCase):
    def test_passed_critical_no_violation(self):
        self.assertEqual(
            pl.evaluate_functional_test("ft-01", "attitude_control", True, True), []
        )

    def test_passed_noncritical_no_violation(self):
        self.assertEqual(
            pl.evaluate_functional_test(
                "ft-02", "housekeeping_telemetry", True, False
            ),
            [],
        )

    def test_failed_critical_is_launch_hold(self):
        violations = pl.evaluate_functional_test(
            "ft-03", "propulsion_valve", False, True
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"],
            "functional_test_failed_critical_launch_hold",
        )
        self.assertEqual(violations[0]["subsystem"], "propulsion_valve")

    def test_failed_noncritical_is_advisory(self):
        violations = pl.evaluate_functional_test(
            "ft-04", "auxiliary_heater", False, False
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"],
            "functional_test_failed_noncritical_advisory",
        )


class EvaluateCampaignConstraintTest(unittest.TestCase):
    def test_within_bounds_no_violation(self):
        self.assertEqual(
            pl.evaluate_campaign_constraint(
                "cc-01", "temperature_c", 20.0, 15.0, 25.0
            ),
            [],
        )

    def test_below_lower_bound_flagged(self):
        violations = pl.evaluate_campaign_constraint(
            "cc-02", "relative_humidity_pct", 10.0, 20.0, 60.0
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"], "campaign_constraint_below_lower_bound"
        )

    def test_above_upper_bound_flagged(self):
        violations = pl.evaluate_campaign_constraint(
            "cc-03", "temperature_c", 35.0, 15.0, 25.0
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"], "campaign_constraint_above_upper_bound"
        )

    def test_at_exact_lower_bound_no_violation(self):
        self.assertEqual(
            pl.evaluate_campaign_constraint(
                "cc-04", "battery_charge_duration_h", 5.0, 5.0, 24.0
            ),
            [],
        )

    def test_at_exact_upper_bound_no_violation(self):
        self.assertEqual(
            pl.evaluate_campaign_constraint(
                "cc-05", "shelf_life_days", 365.0, 0.0, 365.0
            ),
            [],
        )

    def test_unknown_constraint_type_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_campaign_constraint(
                "cc-06", "cosmic_ray_flux", 42.0, 0.0, 100.0
            )

    def test_cleanliness_level_numeric_recognized(self):
        self.assertEqual(
            pl.evaluate_campaign_constraint(
                "cc-07", "cleanliness_level_numeric", 500.0, 0.0, 1000.0
            ),
            [],
        )


class LaunchReadinessReviewTest(unittest.TestCase):
    def test_all_clear_is_launch_ready(self):
        review = pl.launch_readiness_review(
            health_checks=[
                {
                    "check_id": "hc-01",
                    "check_category": "electrical",
                    "result": "pass",
                }
            ],
            leak_checks=[
                {
                    "check_id": "lc-01",
                    "leak_type": "propulsion_system",
                    "measured_rate_sccm": 0.5,
                    "allowable_rate_sccm": 1.0,
                }
            ],
            functional_tests=[
                {
                    "test_id": "ft-01",
                    "subsystem": "attitude_control",
                    "passed": True,
                    "is_critical": True,
                }
            ],
            campaign_constraints=[
                {
                    "constraint_id": "cc-01",
                    "constraint_type": "temperature_c",
                    "measured_value": 20.0,
                    "lower_bound": 15.0,
                    "upper_bound": 25.0,
                }
            ],
        )
        self.assertEqual(
            review,
            {"health": [], "leak": [], "functional": [], "constraints": []},
        )
        self.assertTrue(pl.is_launch_ready(review))

    def test_mixed_findings_not_launch_ready(self):
        review = pl.launch_readiness_review(
            health_checks=[
                {
                    "check_id": "hc-01",
                    "check_category": "structural",
                    "result": "fail",
                }
            ],
            leak_checks=[
                {
                    "check_id": "lc-01",
                    "leak_type": "pressurized_vessel",
                    "measured_rate_sccm": 3.0,
                    "allowable_rate_sccm": 1.0,
                }
            ],
            functional_tests=[
                {
                    "test_id": "ft-01",
                    "subsystem": "propulsion",
                    "passed": False,
                    "is_critical": True,
                }
            ],
            campaign_constraints=[
                {
                    "constraint_id": "cc-01",
                    "constraint_type": "relative_humidity_pct",
                    "measured_value": 80.0,
                    "lower_bound": 20.0,
                    "upper_bound": 60.0,
                }
            ],
        )
        self.assertTrue(review["health"])
        self.assertTrue(review["leak"])
        self.assertTrue(review["functional"])
        self.assertTrue(review["constraints"])
        self.assertFalse(pl.is_launch_ready(review))

    def test_empty_inputs_is_launch_ready(self):
        review = pl.launch_readiness_review([], [], [], [])
        self.assertEqual(
            review,
            {"health": [], "leak": [], "functional": [], "constraints": []},
        )
        self.assertTrue(pl.is_launch_ready(review))

    def test_advisory_only_is_not_launch_ready(self):
        review = pl.launch_readiness_review(
            health_checks=[
                {
                    "check_id": "hc-01",
                    "check_category": "thermal",
                    "result": "marginal",
                }
            ],
            leak_checks=[],
            functional_tests=[],
            campaign_constraints=[],
        )
        self.assertFalse(pl.is_launch_ready(review))

    def test_review_result_has_all_four_keys(self):
        review = pl.launch_readiness_review([], [], [], [])
        self.assertIn("health", review)
        self.assertIn("leak", review)
        self.assertIn("functional", review)
        self.assertIn("constraints", review)


if __name__ == "__main__":
    unittest.main()
