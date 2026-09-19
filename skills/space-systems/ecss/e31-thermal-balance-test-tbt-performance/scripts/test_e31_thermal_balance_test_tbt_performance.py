"""Contract tests for the clause 4.5.3.1 thermal balance test logic."""

import unittest

from e31_thermal_balance_test_tbt_performance_logic import (
    CASE_SENSES,
    SECONDS_PER_HOUR,
    STEFAN_BOLTZMANN_W_M2_K4,
    assess_balance_test,
    compensation_heater_power_w,
    drift_rate_k_per_h,
    grade_case_compensation,
    instrumentation_findings,
    shroud_rejection_delta_w,
    steady_state_verdict,
    validate_case,
    validate_case_set,
)

AREA = 1.2
EMITTANCE = 0.86

HOT_CASE = {
    "name": "balance-hot",
    "sense": "hot",
    "flight_sink_k": 250.0,
    "test_sink_k": 100.0,
    "flight_absorbed_w": 180.0,
    "test_absorbed_w": 150.0,
    "dissipation_w": 120.0,
}

COLD_CASE = {
    "name": "balance-cold",
    "sense": "cold",
    "flight_sink_k": 90.0,
    "test_sink_k": 100.0,
    "flight_absorbed_w": 20.0,
    "test_absorbed_w": 10.0,
    "dissipation_w": 40.0,
}


def steady_history(start_k, drift_k_per_h, span_s=7200.0, points=9):
    """Build a clean temperature history with a known drift."""
    step = span_s / (points - 1)
    return [
        (i * step, start_k + drift_k_per_h * (i * step) / SECONDS_PER_HOUR)
        for i in range(points)
    ]


class CaseValidationTests(unittest.TestCase):
    def test_valid_case_round_trips(self):
        case = validate_case(HOT_CASE)
        self.assertEqual(case["name"], "balance-hot")
        self.assertEqual(case["sense"], "hot")

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(dict(HOT_CASE, sense="warm"))

    def test_missing_key_rejected(self):
        case = dict(HOT_CASE)
        del case["test_sink_k"]
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_negative_sink_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(dict(HOT_CASE, test_sink_k=-10.0))

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(dict(HOT_CASE, name=" "))

    def test_case_set_needs_both_senses(self):
        with self.assertRaises(ValueError):
            validate_case_set([HOT_CASE])

    def test_bracketing_case_set_accepted(self):
        self.assertEqual(len(validate_case_set([HOT_CASE, COLD_CASE])), 2)

    def test_duplicate_case_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_case_set([HOT_CASE, dict(COLD_CASE, name="balance-hot")])

    def test_empty_case_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_case_set([])

    def test_sense_vocabulary_is_hot_and_cold(self):
        self.assertEqual(set(CASE_SENSES), {"hot", "cold"})


class CompensationTests(unittest.TestCase):
    def test_shroud_term_matches_the_closed_form(self):
        value = shroud_rejection_delta_w(AREA, EMITTANCE, 250.0, 100.0)
        expected = AREA * EMITTANCE * STEFAN_BOLTZMANN_W_M2_K4 * (
            250.0 ** 4 - 100.0 ** 4
        )
        self.assertAlmostEqual(value, expected, places=9)

    def test_matched_shroud_contributes_nothing(self):
        self.assertAlmostEqual(
            shroud_rejection_delta_w(AREA, EMITTANCE, 100.0, 100.0), 0.0, places=12
        )

    def test_warmer_chamber_than_flight_gives_a_negative_term(self):
        self.assertLess(shroud_rejection_delta_w(AREA, EMITTANCE, 90.0, 250.0), 0.0)

    def test_compensation_sums_both_terms(self):
        demand = compensation_heater_power_w(HOT_CASE, AREA, EMITTANCE)
        expected = 30.0 + shroud_rejection_delta_w(AREA, EMITTANCE, 250.0, 100.0)
        self.assertAlmostEqual(demand, expected, places=9)

    def test_flux_shortfall_alone_would_understate_the_demand(self):
        demand = compensation_heater_power_w(HOT_CASE, AREA, EMITTANCE)
        self.assertGreater(demand, 30.0)

    def test_cold_case_can_be_dominated_by_the_shroud_term(self):
        demand = compensation_heater_power_w(COLD_CASE, AREA, EMITTANCE)
        self.assertLess(demand, 10.0)

    def test_feasible_case_is_graded_clean(self):
        result = grade_case_compensation(HOT_CASE, AREA, EMITTANCE, 300.0)
        self.assertTrue(result["feasible"])
        self.assertEqual(result["findings"], [])

    def test_demand_over_the_installed_power_is_a_finding(self):
        result = grade_case_compensation(HOT_CASE, AREA, EMITTANCE, 10.0)
        self.assertFalse(result["feasible"])
        self.assertIn("installed", result["findings"][0])

    def test_negative_demand_is_refused_not_clamped(self):
        infeasible = dict(COLD_CASE, flight_sink_k=90.0, test_sink_k=260.0)
        result = grade_case_compensation(infeasible, AREA, EMITTANCE, 300.0)
        self.assertFalse(result["feasible"])
        self.assertLess(result["demand_w"], 0.0)
        self.assertIn("cannot deliver", result["findings"][0])

    def test_demand_exactly_matching_the_installed_power_is_feasible(self):
        demand = compensation_heater_power_w(HOT_CASE, AREA, EMITTANCE)
        result = grade_case_compensation(HOT_CASE, AREA, EMITTANCE, demand)
        self.assertTrue(result["feasible"])

    def test_negative_installed_power_rejected(self):
        with self.assertRaises(ValueError):
            grade_case_compensation(HOT_CASE, AREA, EMITTANCE, -5.0)


class DriftTests(unittest.TestCase):
    def test_flat_history_has_no_drift(self):
        self.assertAlmostEqual(
            drift_rate_k_per_h(steady_history(300.0, 0.0)), 0.0, places=9
        )

    def test_known_slope_is_recovered(self):
        self.assertAlmostEqual(
            drift_rate_k_per_h(steady_history(300.0, 0.4)), 0.4, places=9
        )

    def test_falling_history_reports_a_negative_rate(self):
        self.assertAlmostEqual(
            drift_rate_k_per_h(steady_history(300.0, -0.25)), -0.25, places=9
        )

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            drift_rate_k_per_h([(0.0, 300.0)])

    def test_non_increasing_times_rejected(self):
        with self.assertRaises(ValueError):
            drift_rate_k_per_h([(0.0, 300.0), (0.0, 301.0)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            drift_rate_k_per_h([(0.0, 300.0), (60.0,)])

    def test_non_absolute_temperature_rejected(self):
        with self.assertRaises(ValueError):
            drift_rate_k_per_h([(0.0, 300.0), (60.0, -1.0)])


class SteadyStateTests(unittest.TestCase):
    def test_settled_article_is_steady(self):
        verdict = steady_state_verdict(
            {"trp-a": steady_history(300.0, 0.1), "trp-b": steady_history(280.0, 0.05)},
            0.5, 3600.0,
        )
        self.assertTrue(verdict["steady"])
        self.assertEqual(verdict["findings"], [])

    def test_the_slowest_point_sets_the_verdict(self):
        verdict = steady_state_verdict(
            {"trp-a": steady_history(300.0, 0.1), "trp-b": steady_history(280.0, 2.0)},
            0.5, 3600.0,
        )
        self.assertFalse(verdict["steady"])
        self.assertEqual(verdict["worst_point"], "trp-b")

    def test_short_window_cannot_demonstrate_steady_state(self):
        verdict = steady_state_verdict(
            {"trp-a": steady_history(300.0, 0.0, span_s=600.0)}, 0.5, 3600.0
        )
        self.assertFalse(verdict["steady"])
        self.assertIn("window", verdict["findings"][0])

    def test_drift_exactly_on_the_criterion_is_steady(self):
        verdict = steady_state_verdict(
            {"trp-a": steady_history(300.0, 0.5)}, 0.5, 3600.0
        )
        self.assertTrue(verdict["steady"])

    def test_negative_drift_is_graded_on_magnitude(self):
        verdict = steady_state_verdict(
            {"trp-a": steady_history(300.0, -2.0)}, 0.5, 3600.0
        )
        self.assertFalse(verdict["steady"])

    def test_empty_history_set_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_verdict({}, 0.5, 3600.0)

    def test_zero_criterion_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_verdict({"trp-a": steady_history(300.0, 0.0)}, 0.0, 3600.0)


class InstrumentationTests(unittest.TestCase):
    SENSORS = [
        {"name": "tc-01", "at": "trp-a", "accuracy_k": 0.5},
        {"name": "tc-02", "at": "trp-b", "accuracy_k": 0.8},
    ]

    def test_fully_instrumented_configuration_is_clean(self):
        self.assertEqual(
            instrumentation_findings(["trp-a", "trp-b"], self.SENSORS, 1.0), []
        )

    def test_missing_sensor_is_a_finding(self):
        findings = instrumentation_findings(
            ["trp-a", "trp-b", "trp-c"], self.SENSORS, 1.0
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("trp-c", findings[0])

    def test_coarse_sensor_is_a_finding(self):
        findings = instrumentation_findings(["trp-a", "trp-b"], self.SENSORS, 0.6)
        self.assertEqual(len(findings), 1)
        self.assertIn("trp-b", findings[0])

    def test_best_sensor_at_a_point_is_the_one_graded(self):
        sensors = list(self.SENSORS) + [
            {"name": "tc-03", "at": "trp-b", "accuracy_k": 0.2}
        ]
        self.assertEqual(instrumentation_findings(["trp-b"], sensors, 0.5), [])

    def test_sensor_exactly_on_the_accuracy_requirement_passes(self):
        self.assertEqual(
            instrumentation_findings(["trp-a"], self.SENSORS, 0.5), []
        )

    def test_empty_reference_point_list_rejected(self):
        with self.assertRaises(ValueError):
            instrumentation_findings([], self.SENSORS, 1.0)

    def test_duplicate_reference_point_rejected(self):
        with self.assertRaises(ValueError):
            instrumentation_findings(["trp-a", "trp-a"], self.SENSORS, 1.0)

    def test_sensor_without_accuracy_rejected(self):
        with self.assertRaises(ValueError):
            instrumentation_findings(["trp-a"], [{"name": "tc", "at": "trp-a"}], 1.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "cases": [HOT_CASE, COLD_CASE],
            "radiator_area_m2": AREA,
            "emittance": EMITTANCE,
            "installed_heater_w": 400.0,
            "reference_points": ["trp-a", "trp-b"],
            "sensors": [
                {"name": "tc-01", "at": "trp-a", "accuracy_k": 0.5},
                {"name": "tc-02", "at": "trp-b", "accuracy_k": 0.5},
            ],
            "required_accuracy_k": 1.0,
            "histories": {
                "trp-a": steady_history(300.0, 0.1),
                "trp-b": steady_history(280.0, 0.05),
            },
            "drift_limit_k_per_h": 0.5,
            "min_window_s": 3600.0,
        }
        spec.update(overrides)
        return spec

    def test_well_specified_campaign_is_ready(self):
        result = assess_balance_test(self._spec())
        self.assertTrue(result["ready"])
        self.assertTrue(result["feasible"])

    def test_total_compensation_sums_the_cases(self):
        result = assess_balance_test(self._spec())
        expected = (
            compensation_heater_power_w(HOT_CASE, AREA, EMITTANCE)
            + compensation_heater_power_w(COLD_CASE, AREA, EMITTANCE)
        )
        self.assertAlmostEqual(result["total_compensation_w"], expected, places=9)

    def test_single_case_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            assess_balance_test(self._spec(cases=[HOT_CASE]))

    def test_short_heater_bank_is_a_finding(self):
        result = assess_balance_test(self._spec(installed_heater_w=5.0))
        self.assertFalse(result["ready"])
        self.assertFalse(result["feasible"])

    def test_unsettled_article_is_a_finding(self):
        result = assess_balance_test(self._spec(histories={
            "trp-a": steady_history(300.0, 3.0),
            "trp-b": steady_history(280.0, 0.05),
        }))
        self.assertFalse(result["ready"])
        self.assertFalse(result["steady_state"]["steady"])

    def test_campaign_without_histories_skips_the_steady_check(self):
        spec = self._spec()
        del spec["histories"]
        result = assess_balance_test(spec)
        self.assertIsNone(result["steady_state"])
        self.assertTrue(result["ready"])

    def test_instrumentation_gap_is_a_finding(self):
        result = assess_balance_test(self._spec(
            reference_points=["trp-a", "trp-b", "trp-c"]
        ))
        self.assertFalse(result["ready"])
        self.assertEqual(len(result["instrumentation_findings"]), 1)

    def test_coarse_sensor_requirement_is_a_finding(self):
        result = assess_balance_test(self._spec(required_accuracy_k=0.2))
        self.assertEqual(len(result["instrumentation_findings"]), 2)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["emittance"]
        with self.assertRaises(ValueError):
            assess_balance_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_balance_test(["cases"])

    def test_findings_accumulate_across_sections(self):
        result = assess_balance_test(self._spec(
            installed_heater_w=1.0,
            required_accuracy_k=0.2,
            histories={"trp-a": steady_history(300.0, 5.0)},
        ))
        self.assertGreaterEqual(len(result["findings"]), 3)
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
