"""Contract tests for the clause 4.7-4.8 in-service and PA interface logic."""

import unittest

from e31_in_service_product_assurance_requirements_logic import (
    MIN_SAMPLES_PER_TIME_CONSTANT,
    SEVERITIES,
    TEMPERATURE_TOLERANCE_K,
    alarm_band_findings,
    alarm_margin_fraction,
    assess_in_service_pa,
    criticality_score,
    drift_acceptable,
    evaluate_failure_mode,
    evaluate_monitored_item,
    in_service_margin_k,
    model_drift_k,
    required_sampling_interval_s,
    sampling_adequate,
    sensor_coverage_findings,
    severity_rank,
    validate_severity,
    validate_temperature_k,
)


def _item(**overrides):
    item = {
        "id": "BAT-PACK",
        "sensors": 4,
        "required_sensors": 2,
        "independent_chains": 2,
        "required_chains": 2,
        "time_constant_s": 1200.0,
        "samples_per_time_constant": 4,
        "telemetry_interval_s": 120.0,
        "operational_limit_k": 298.0,
        "alarm_limit_k": 305.0,
        "design_limit_k": 313.0,
        "predicted_maximum_k": 296.0,
        "flight_maximum_k": 299.0,
        "drift_tolerance_k": 5.0,
    }
    item.update(overrides)
    return item


def _mode(**overrides):
    mode = {
        "id": "FM-HEATER-OPEN",
        "severity": "critical",
        "telemetry_detectable": True,
        "mitigated": True,
    }
    mode.update(overrides)
    return mode


class SeverityTests(unittest.TestCase):
    def test_catastrophic_is_the_most_severe(self):
        self.assertEqual(severity_rank("catastrophic"), 0)

    def test_severity_is_normalised(self):
        self.assertEqual(validate_severity(" Major "), "major")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity("annoying")

    def test_non_string_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity(1)

    def test_vocabulary_is_ordered_most_severe_first(self):
        self.assertEqual(SEVERITIES[0], "catastrophic")
        self.assertEqual(SEVERITIES[-1], "minor")


class SamplingTests(unittest.TestCase):
    def test_interval_is_the_time_constant_over_the_sample_count(self):
        self.assertAlmostEqual(required_sampling_interval_s(1200.0, 4), 300.0, places=9)

    def test_more_samples_shorten_the_interval(self):
        self.assertAlmostEqual(required_sampling_interval_s(1200.0, 10), 120.0, places=9)

    def test_single_sample_per_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            required_sampling_interval_s(1200.0, 1)

    def test_sample_count_must_be_an_integer(self):
        with self.assertRaises(ValueError):
            required_sampling_interval_s(1200.0, 4.5)

    def test_zero_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            required_sampling_interval_s(0.0, 4)

    def test_faster_sampling_is_adequate(self):
        self.assertTrue(sampling_adequate(120.0, 300.0))

    def test_sampling_exactly_at_the_required_interval_is_adequate(self):
        self.assertTrue(sampling_adequate(300.0, 300.0))

    def test_slower_sampling_is_inadequate(self):
        self.assertFalse(sampling_adequate(600.0, 300.0))

    def test_minimum_sample_count_is_at_least_two(self):
        self.assertGreaterEqual(MIN_SAMPLES_PER_TIME_CONSTANT, 2)


class SensorCoverageTests(unittest.TestCase):
    def test_adequate_fit_raises_nothing(self):
        self.assertEqual(sensor_coverage_findings("BAT", 4, 2, 2, 2), [])

    def test_too_few_sensors_is_a_finding(self):
        self.assertEqual(len(sensor_coverage_findings("BAT", 1, 2, 1, 1)), 1)

    def test_all_sensors_on_one_chain_is_a_finding(self):
        self.assertEqual(len(sensor_coverage_findings("BAT", 4, 2, 1, 2)), 1)

    def test_both_shortfalls_give_two_findings(self):
        self.assertEqual(len(sensor_coverage_findings("BAT", 1, 3, 1, 2)), 2)

    def test_more_chains_than_sensors_rejected(self):
        with self.assertRaises(ValueError):
            sensor_coverage_findings("BAT", 2, 2, 3, 2)

    def test_zero_required_sensors_rejected(self):
        with self.assertRaises(ValueError):
            sensor_coverage_findings("BAT", 4, 0, 2, 2)

    def test_non_integer_sensor_count_rejected(self):
        with self.assertRaises(ValueError):
            sensor_coverage_findings("BAT", 4.0, 2, 2, 2)


class AlarmBandTests(unittest.TestCase):
    def test_alarm_inside_the_band_raises_nothing(self):
        self.assertEqual(alarm_band_findings("BAT", 298.0, 305.0, 313.0), [])

    def test_alarm_below_the_operational_limit_is_a_finding(self):
        self.assertEqual(len(alarm_band_findings("BAT", 298.0, 290.0, 313.0)), 1)

    def test_alarm_at_the_design_limit_leaves_no_reaction_time(self):
        self.assertEqual(len(alarm_band_findings("BAT", 298.0, 320.0, 313.0)), 1)

    def test_design_limit_below_operational_limit_rejected(self):
        with self.assertRaises(ValueError):
            alarm_band_findings("BAT", 313.0, 305.0, 298.0)

    def test_placement_fraction_is_dimensionless(self):
        self.assertAlmostEqual(alarm_margin_fraction(300.0, 310.0, 320.0), 0.5, places=9)

    def test_alarm_at_the_operational_limit_gives_zero_placement(self):
        self.assertAlmostEqual(alarm_margin_fraction(300.0, 300.0, 320.0), 0.0, places=9)

    def test_zero_band_span_rejected(self):
        with self.assertRaises(ValueError):
            alarm_margin_fraction(300.0, 300.0, 300.0)


class InServiceTests(unittest.TestCase):
    def test_margin_is_design_minus_flight(self):
        self.assertAlmostEqual(in_service_margin_k(313.0, 299.0), 14.0, places=9)

    def test_exceedance_gives_a_negative_margin(self):
        self.assertAlmostEqual(in_service_margin_k(313.0, 320.0), -7.0, places=9)

    def test_drift_is_signed_flight_minus_predicted(self):
        self.assertAlmostEqual(model_drift_k(296.0, 299.0), 3.0, places=9)
        self.assertAlmostEqual(model_drift_k(299.0, 296.0), -3.0, places=9)

    def test_drift_inside_tolerance_is_acceptable(self):
        self.assertTrue(drift_acceptable(3.0, 5.0))

    def test_cold_drift_is_graded_the_same_as_hot(self):
        self.assertFalse(drift_acceptable(-9.0, 5.0))

    def test_drift_exactly_on_the_tolerance_is_acceptable(self):
        self.assertTrue(drift_acceptable(5.0, 5.0))

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            drift_acceptable(1.0, 0.0)

    def test_kelvin_validation_rejects_absolute_zero(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(0.0, "limit")


class CriticalityTests(unittest.TestCase):
    def test_mitigated_detectable_minor_scores_lowest(self):
        self.assertEqual(criticality_score("minor", True, True), 1)

    def test_catastrophic_scores_above_minor(self):
        self.assertGreater(
            criticality_score("catastrophic", True, True),
            criticality_score("minor", True, True),
        )

    def test_undetectable_and_unmitigated_each_add_one(self):
        base = criticality_score("major", True, True)
        self.assertEqual(criticality_score("major", False, True), base + 1)
        self.assertEqual(criticality_score("major", False, False), base + 2)

    def test_unmitigated_critical_mode_is_a_single_point_failure(self):
        record = evaluate_failure_mode(_mode(mitigated=False))
        self.assertTrue(record["single_point_failure"])

    def test_mitigated_critical_mode_is_not_a_single_point_failure(self):
        self.assertFalse(evaluate_failure_mode(_mode())["single_point_failure"])

    def test_unmitigated_minor_mode_is_not_a_single_point_failure(self):
        record = evaluate_failure_mode(_mode(severity="minor", mitigated=False))
        self.assertFalse(record["single_point_failure"])

    def test_invisible_severe_mode_is_a_finding(self):
        record = evaluate_failure_mode(_mode(telemetry_detectable=False))
        self.assertEqual(len(record["findings"]), 1)

    def test_missing_mode_key_rejected(self):
        mode = _mode()
        del mode["mitigated"]
        with self.assertRaises(ValueError):
            evaluate_failure_mode(mode)

    def test_blank_mode_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_failure_mode(_mode(id="  "))


class ItemEvaluationTests(unittest.TestCase):
    def test_nominal_item_is_monitored(self):
        record = evaluate_monitored_item(_item())
        self.assertTrue(record["monitored"])
        self.assertAlmostEqual(record["required_interval_s"], 300.0, places=9)

    def test_slow_telemetry_is_a_finding(self):
        record = evaluate_monitored_item(_item(telemetry_interval_s=900.0))
        self.assertFalse(record["sampling_adequate"])
        self.assertFalse(record["monitored"])

    def test_exceeded_design_limit_is_a_finding(self):
        record = evaluate_monitored_item(_item(flight_maximum_k=320.0))
        self.assertFalse(record["margin_positive"])

    def test_large_cold_drift_is_a_finding(self):
        record = evaluate_monitored_item(
            _item(predicted_maximum_k=320.0, flight_maximum_k=299.0)
        )
        self.assertFalse(record["drift_acceptable"])

    def test_single_chain_item_is_a_finding(self):
        record = evaluate_monitored_item(_item(independent_chains=1))
        self.assertFalse(record["monitored"])

    def test_missing_item_key_rejected(self):
        item = _item()
        del item["alarm_limit_k"]
        with self.assertRaises(ValueError):
            evaluate_monitored_item(item)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "items": [_item(), _item(id="PROP-TANK", time_constant_s=6000.0,
                                     telemetry_interval_s=600.0)],
            "failure_modes": [
                _mode(),
                _mode(id="FM-THERMOSTAT-STUCK", severity="major"),
                _mode(id="FM-MLI-TEAR", severity="minor", mitigated=False),
            ],
        }
        spec.update(overrides)
        return spec

    def test_nominal_programme_is_compliant(self):
        result = assess_in_service_pa(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["single_point_failures"], [])

    def test_single_point_failure_is_named(self):
        spec = self._spec()
        spec["failure_modes"] = list(spec["failure_modes"]) + [
            _mode(id="FM-LOOP-DRYOUT", severity="catastrophic", mitigated=False)
        ]
        result = assess_in_service_pa(spec)
        self.assertIn("FM-LOOP-DRYOUT", result["single_point_failures"])
        self.assertFalse(result["compliant"])

    def test_worst_criticality_mode_is_reported(self):
        spec = self._spec()
        spec["failure_modes"] = list(spec["failure_modes"]) + [
            _mode(id="FM-LOOP-DRYOUT", severity="catastrophic",
                  mitigated=False, telemetry_detectable=False)
        ]
        self.assertEqual(
            assess_in_service_pa(spec)["worst_criticality_mode"], "FM-LOOP-DRYOUT"
        )

    def test_tightest_margin_item_is_reported(self):
        spec = self._spec()
        spec["items"] = [_item(), _item(id="PROP-TANK", flight_maximum_k=310.0)]
        self.assertEqual(assess_in_service_pa(spec)["tightest_margin_item"], "PROP-TANK")

    def test_monitored_fraction_reflects_the_failures(self):
        spec = self._spec()
        spec["items"] = [_item(), _item(id="PROP-TANK", independent_chains=1)]
        self.assertAlmostEqual(
            assess_in_service_pa(spec)["monitored_fraction"], 0.5, places=12
        )

    def test_duplicate_item_id_rejected(self):
        spec = self._spec()
        spec["items"] = [_item(), _item()]
        with self.assertRaises(ValueError):
            assess_in_service_pa(spec)

    def test_duplicate_mode_id_rejected(self):
        spec = self._spec()
        spec["failure_modes"] = [_mode(), _mode()]
        with self.assertRaises(ValueError):
            assess_in_service_pa(spec)

    def test_empty_failure_mode_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_in_service_pa(self._spec(failure_modes=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["items"]
        with self.assertRaises(ValueError):
            assess_in_service_pa(spec)

    def test_tolerance_relaxes_nothing_measurable(self):
        self.assertLess(TEMPERATURE_TOLERANCE_K, 1e-6)


if __name__ == "__main__":
    unittest.main()
