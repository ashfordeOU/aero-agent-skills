"""Contract test for in_service_safety_assessment_logic (offline, stdlib).

Run:  python3 test_in_service_safety_assessment.py
All expected values below were read from real module outputs; Poisson
tail anchors assert the spec worked-example values within 1e-3.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import in_service_safety_assessment_logic as m


def _fcs1_events():
    return [
        {"event_id": "e1", "condition_id": "FCS-1", "severity": "hazardous", "description": "dual channel loss reported"},
        {"event_id": "e2", "condition_id": "FCS-1", "severity": "hazardous", "description": "pitch control anomaly"},
        {"event_id": "e3", "condition_id": "PP-1", "severity": "major", "description": "pump wear"},
        {"event_id": "e4", "condition_id": "PP-1", "severity": "major", "description": "pump wear"},
        {"event_id": "e5", "condition_id": "PP-1", "severity": "major", "description": "pump seal leak"},
    ]


def _fcs1_predictions():
    return {
        "FCS-1": {"predicted_rate": 3e-7, "severity": "hazardous", "note": "SSA objective"},
        "PP-1": {"predicted_rate": 2e-6, "severity": "major", "note": "SSA objective"},
    }


class ExposureGroupingTests(unittest.TestCase):
    def test_group_events_counts_per_condition(self):
        counts = m.group_events(_fcs1_events())
        self.assertEqual(counts, {"FCS-1": 2, "PP-1": 3})
        self.assertEqual(m.group_events([]), {})

    def test_exposure_summary_total_and_per_aircraft(self):
        summary = m.exposure_summary(1_000_000, 200)
        self.assertEqual(summary["total"], 1_000_000)
        self.assertEqual(summary["per_aircraft"], 5_000.0)

    def test_exposure_summary_non_physical_raises(self):
        with self.assertRaises(ValueError):
            m.exposure_summary(-1.0, 200)
        with self.assertRaises(ValueError):
            m.exposure_summary(1e6, 0)

    def test_observed_rate_worked_example_two_per_million(self):
        self.assertAlmostEqual(m.observed_rate(2, 1_000_000), 2e-6)

    def test_observed_rate_round_trip_identity(self):
        exposure = 850_000.0
        count = 17
        self.assertAlmostEqual(m.observed_rate(count, exposure) * exposure, count)

    def test_observed_rate_non_physical_raises(self):
        with self.assertRaises(ValueError):
            m.observed_rate(-1, 1e6)
        with self.assertRaises(ValueError):
            m.observed_rate(1, 0.0)

    def test_expected_events_worked_example_values(self):
        self.assertAlmostEqual(m.expected_events(3e-7, 1e6), 0.3)
        self.assertAlmostEqual(m.expected_events(2e-6, 1e6), 2.0)

    def test_adequacy_inadequate_below_threshold(self):
        adequate, note = m.adequacy_verdict(0.3)
        self.assertFalse(adequate)
        self.assertIn("inadequate", note)

    def test_adequacy_adequate_at_threshold(self):
        adequate, note = m.adequacy_verdict(5.0)
        self.assertTrue(adequate)
        self.assertIn("adequate", note)


class PoissonExceedanceTests(unittest.TestCase):
    def test_poisson_exceedance_fcs1_anchor(self):
        # Spec anchor: P(X >= 2 | mean 0.3) ~ 0.0369.
        self.assertAlmostEqual(m.poisson_exceedance_p(2, 0.3), 0.0369, delta=1e-3)

    def test_poisson_exceedance_pp1_anchor(self):
        # Spec anchor: P(X >= 3 | mean 2.0) ~ 0.3233.
        self.assertAlmostEqual(m.poisson_exceedance_p(3, 2.0), 0.3233, delta=1e-3)

    def test_poisson_exceedance_boundary_zero_cases(self):
        # P(X >= 0 | mean 2) = 1; P(X >= 1 | mean 0) = 0; P(X >= 0 | 0) = 1.
        self.assertEqual(m.poisson_exceedance_p(0, 2.0), 1.0)
        self.assertEqual(m.poisson_exceedance_p(1, 0.0), 0.0)
        self.assertEqual(m.poisson_exceedance_p(0, 0.0), 1.0)

    def test_poisson_exceedance_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            m.poisson_exceedance_p(2, -0.3)
        with self.assertRaises(ValueError):
            m.poisson_exceedance_p(-2, 0.3)


class SignificanceTests(unittest.TestCase):
    def test_significance_fcs1_anchor(self):
        verdict = m.significance_verdict("FCS-1", 2, 0.3, "hazardous")
        self.assertTrue(verdict["significant"])
        self.assertAlmostEqual(verdict["poisson_exceedance_p"], 0.0369, delta=1e-3)
        self.assertLessEqual(verdict["poisson_exceedance_p"], m.SIGNIFICANCE_ALPHA)

    def test_significance_pp1_anchor_not_significant(self):
        verdict = m.significance_verdict("PP-1", 3, 2.0, "major")
        self.assertFalse(verdict["significant"])
        self.assertAlmostEqual(verdict["poisson_exceedance_p"], 0.3233, delta=1e-3)
        self.assertGreater(verdict["poisson_exceedance_p"], m.SIGNIFICANCE_ALPHA)
        self.assertEqual(verdict["rate_ratio"], 1.5)

    def test_significance_rate_within_expectation_reason(self):
        verdict = m.significance_verdict("PP-1", 3, 2.0, "major")
        self.assertIn("rate within expectation", verdict["reasons"])

    def test_significance_single_event_rule_catastrophic(self):
        verdict = m.significance_verdict("X-1", 1, 0.02, "catastrophic")
        self.assertTrue(verdict["significant"])
        self.assertTrue(
            any("single-event rule" in reason for reason in verdict["reasons"])
        )

    def test_significance_single_event_rule_hazardous_regardless_of_rate(self):
        # Hazardous event observed against a 10x higher expectation: the
        # single-event rule still fires although tail and rate ratio do not.
        verdict = m.significance_verdict("H-1", 1, 10.0, "hazardous")
        self.assertTrue(verdict["significant"])
        self.assertGreater(verdict["poisson_exceedance_p"], m.SIGNIFICANCE_ALPHA)
        self.assertLess(verdict["rate_ratio"], m.RATE_EXCEEDANCE_MIN)

    def test_significance_rate_exceedance_factor_path(self):
        # 4 observed vs 2.0 expected: tail 0.1429 above alpha but the rate
        # ratio is exactly 2.0, so the exceedance factor decides.
        verdict = m.significance_verdict("Q-1", 4, 2.0, "major")
        self.assertTrue(verdict["significant"])
        self.assertGreater(verdict["poisson_exceedance_p"], m.SIGNIFICANCE_ALPHA)
        self.assertEqual(verdict["rate_ratio"], m.RATE_EXCEEDANCE_MIN)
        self.assertTrue(
            any("times predicted rate" in reason for reason in verdict["reasons"])
        )

    def test_significance_major_low_count_not_significant(self):
        verdict = m.significance_verdict("M-1", 1, 2.0, "major")
        self.assertFalse(verdict["significant"])
        self.assertAlmostEqual(verdict["poisson_exceedance_p"], 0.8647, delta=1e-3)

    def test_significance_zero_observed_not_significant(self):
        verdict = m.significance_verdict("Z-1", 0, 2.0, "major")
        self.assertFalse(verdict["significant"])
        self.assertEqual(verdict["poisson_exceedance_p"], 1.0)

    def test_significance_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            m.significance_verdict("Q-1", 1, 1.0, "severe")


class RoutingTests(unittest.TestCase):
    def test_route_fcs1_service_bulletin_short_term(self):
        verdict = m.significance_verdict("FCS-1", 2, 0.3, "hazardous")
        self.assertEqual(m.corrective_route(verdict, False, 1), ("service-bulletin", "short-term"))

    def test_route_pp1_no_action_routine(self):
        verdict = m.significance_verdict("PP-1", 3, 2.0, "major")
        self.assertEqual(m.corrective_route(verdict, True, 0), ("no-action", "routine"))

    def test_route_single_catastrophic_immediate_ad_request(self):
        verdict = m.significance_verdict("X-1", 1, 0.02, "catastrophic")
        self.assertEqual(
            m.corrective_route(verdict, False, 0),
            ("airworthiness-directive-request", "immediate"),
        )

    def test_route_major_increasing_service_bulletin(self):
        verdict = m.significance_verdict("Q-1", 4, 2.0, "major")
        self.assertEqual(m.corrective_route(verdict, True, 1), ("service-bulletin", "scheduled"))

    def test_route_major_flat_continued_monitoring(self):
        verdict = m.significance_verdict("Q-1", 4, 2.0, "major")
        self.assertEqual(m.corrective_route(verdict, True, 0), ("continued-monitoring", "scheduled"))

    def test_route_minor_significant_continued_monitoring(self):
        verdict = m.significance_verdict("N-1", 3, 0.5, "minor")
        self.assertTrue(verdict["significant"])
        self.assertEqual(m.corrective_route(verdict, True, 0), ("continued-monitoring", "scheduled"))

    def test_route_not_significant_inadequate_exposure_monitoring(self):
        verdict = m.significance_verdict("M-1", 1, 2.0, "major")
        self.assertEqual(m.corrective_route(verdict, False, 0), ("continued-monitoring", "routine"))

    def test_route_not_significant_increasing_trend_monitoring(self):
        verdict = m.significance_verdict("M-1", 1, 2.0, "major")
        self.assertEqual(m.corrective_route(verdict, True, 1), ("continued-monitoring", "routine"))

    def test_route_invalid_trend_raises(self):
        verdict = m.significance_verdict("PP-1", 3, 2.0, "major")
        with self.assertRaises(ValueError):
            m.corrective_route(verdict, True, 2)


class AssessmentSummaryTests(unittest.TestCase):
    def test_summary_worked_example_full(self):
        summary = m.assessment_summary(
            200, 1_000_000, "fh", _fcs1_events(), _fcs1_predictions(), 0
        )
        self.assertEqual(summary["fleet_size"], 200)
        self.assertEqual(summary["exposure_unit"], "fh")
        self.assertEqual(summary["exposure_summary"]["per_aircraft"], 5_000.0)
        self.assertEqual(len(summary["conditions"]), 2)
        rows = {row["condition_id"]: row for row in summary["conditions"]}
        fcs1 = rows["FCS-1"]
        self.assertAlmostEqual(fcs1["observed_rate"], 2e-6)
        self.assertAlmostEqual(fcs1["expected_events"], 0.3)
        self.assertFalse(fcs1["exposure_adequate"])
        self.assertTrue(fcs1["significance"]["significant"])
        self.assertEqual(fcs1["route"], "service-bulletin")
        self.assertEqual(fcs1["urgency"], "short-term")
        pp1 = rows["PP-1"]
        self.assertAlmostEqual(pp1["observed_rate"], 3e-6)
        self.assertAlmostEqual(pp1["expected_events"], 2.0)
        # Expected 2.0 events sits below the 5.0 adequacy threshold, so the
        # exposure is judged inadequate and monitoring continues instead of
        # closing out with no-action (spec anchor: no-action or
        # continued-monitoring).
        self.assertFalse(pp1["exposure_adequate"])
        self.assertIn("inadequate", pp1["adequacy_note"])
        self.assertFalse(pp1["significance"]["significant"])
        self.assertEqual(pp1["route"], "continued-monitoring")
        self.assertEqual(pp1["urgency"], "routine")
        self.assertEqual(summary["safety_significant_conditions"], ["FCS-1"])

    def test_summary_validation_errors(self):
        predictions = _fcs1_predictions()
        events = _fcs1_events()
        with self.assertRaises(ValueError):
            m.assessment_summary(200, 1e6, "fh", events, {})
        bad_events = events + [
            {"event_id": "e9", "condition_id": "ZZ-9", "severity": "minor", "description": "unknown condition"}
        ]
        with self.assertRaises(ValueError):
            m.assessment_summary(200, 1e6, "fh", bad_events, predictions)
        with self.assertRaises(ValueError):
            m.assessment_summary(200, 1e6, "cycles", events, predictions)
        with self.assertRaises(ValueError):
            m.assessment_summary(200, -1e6, "fh", events, predictions)
        bad_pred = {"FCS-1": {"predicted_rate": 3e-7, "severity": "severe", "note": ""}}
        with self.assertRaises(ValueError):
            m.assessment_summary(200, 1e6, "fh", events, bad_pred)
        with self.assertRaises(ValueError):
            m.assessment_summary(200, 1e6, "fh", events, predictions, 2)

    def test_summary_observed_max_severity_reported(self):
        events = _fcs1_events() + [
            {"event_id": "e6", "condition_id": "PP-1", "severity": "minor", "description": "low impact report"}
        ]
        summary = m.assessment_summary(200, 1_000_000, "fh", events, _fcs1_predictions(), 0)
        rows = {row["condition_id"]: row for row in summary["conditions"]}
        self.assertEqual(rows["FCS-1"]["observed_max_event_severity"], "hazardous")
        self.assertEqual(rows["PP-1"]["observed_max_event_severity"], "major")
        self.assertEqual(rows["PP-1"]["observed_count"], 4)

    def test_summary_single_catastrophic_event_route(self):
        predictions = {
            "BC-1": {"predicted_rate": 1e-8, "severity": "catastrophic", "note": "SSA objective"}
        }
        events = [
            {"event_id": "c1", "condition_id": "BC-1", "severity": "catastrophic", "description": "burst event"}
        ]
        summary = m.assessment_summary(200, 1_000_000, "fh", events, predictions, 0)
        row = summary["conditions"][0]
        self.assertTrue(row["significance"]["significant"])
        self.assertEqual(row["route"], "airworthiness-directive-request")
        self.assertEqual(row["urgency"], "immediate")
        self.assertIn("BC-1", summary["safety_significant_conditions"])


if __name__ == "__main__":
    unittest.main()
