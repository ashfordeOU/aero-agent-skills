#!/usr/bin/env python3
"""Gate 3 contract test for e20-telemetry-monitoring-coverage.

stdlib unittest, offline, deterministic. Run:
    python3 test_e20_telemetry_monitoring_coverage.py
"""

import copy
import unittest

from e20_telemetry_monitoring_coverage_logic import (
    assess_telemetry_coverage,
    categorize_telemetry_parameter,
    check_function_coverage,
    check_limit_monitoring,
    check_sampling_adequacy,
    compute_downlink_budget,
    parameter_bit_rate_bps,
    required_sample_rate_hz,
)

TEMPERATURE = {
    "id": "TM-TEMP",
    "kind": "housekeeping",
    "bandwidth_hz": 0.1,
    "sample_rate_hz": 1.0,
    "bits_per_sample": 12,
    "limit_checked": True,
    "limits": {
        "low_alarm": -40.0,
        "low_warning": -20.0,
        "high_warning": 50.0,
        "high_alarm": 70.0,
    },
    "sensor_range": (-60.0, 125.0),
    "functions_covered": ["F-THERM"],
}

RELAY = {
    "id": "TM-RELAY",
    "kind": "discrete",
    "bandwidth_hz": 1.0,
    "sample_rate_hz": 4.0,
    "bits_per_sample": 1,
    "limit_checked": False,
    "functions_covered": ["F-SWITCH"],
}


def subsystem(**overrides):
    sub = {
        "id": "AOCS",
        "parameters": [copy.deepcopy(TEMPERATURE), copy.deepcopy(RELAY)],
        "functions": [
            {"id": "F-THERM", "critical": True},
            {"id": "F-SWITCH", "critical": False},
        ],
        "downlink_allocation_bps": 100.0,
    }
    sub.update(overrides)
    return sub


class CategorizationTests(unittest.TestCase):
    def test_every_family_round_trips(self):
        for name in (
            "housekeeping-analog",
            "discrete-status",
            "payload-measurement",
            "event-diagnostic",
        ):
            self.assertEqual(categorize_telemetry_parameter(name), name)

    def test_aliases_and_spacing_normalise(self):
        self.assertEqual(categorize_telemetry_parameter(" Housekeeping "), "housekeeping-analog")
        self.assertEqual(categorize_telemetry_parameter("status"), "discrete-status")
        self.assertEqual(categorize_telemetry_parameter("science"), "payload-measurement")
        self.assertEqual(categorize_telemetry_parameter("event"), "event-diagnostic")

    def test_unrecognised_kinds_raise(self):
        with self.assertRaises(ValueError):
            categorize_telemetry_parameter("engineering-guess")
        with self.assertRaises(ValueError):
            categorize_telemetry_parameter(" ")
        with self.assertRaises(ValueError):
            categorize_telemetry_parameter(None)


class RequiredRateTests(unittest.TestCase):
    def test_required_rate_is_nyquist_times_the_family_factor(self):
        self.assertAlmostEqual(
            required_sample_rate_hz(0.1, "housekeeping-analog"), 0.25, places=9
        )
        self.assertAlmostEqual(required_sample_rate_hz(1.0, "discrete-status"), 4.0, places=9)
        self.assertAlmostEqual(
            required_sample_rate_hz(1000.0, "payload-measurement"), 2000.0, places=6
        )
        self.assertAlmostEqual(
            required_sample_rate_hz(100.0, "event-diagnostic"), 500.0, places=6
        )

    def test_discrete_status_demands_more_than_a_payload_measurement(self):
        self.assertGreater(
            required_sample_rate_hz(5.0, "discrete-status"),
            required_sample_rate_hz(5.0, "payload-measurement"),
        )

    def test_required_rate_rejects_bad_family_and_bandwidth(self):
        with self.assertRaises(ValueError):
            required_sample_rate_hz(1.0, "telemetry")
        with self.assertRaises(ValueError):
            required_sample_rate_hz(0.0, "housekeeping-analog")
        with self.assertRaises(ValueError):
            required_sample_rate_hz("1.0", "housekeeping-analog")


class SamplingAdequacyTests(unittest.TestCase):
    def test_rate_exactly_at_the_requirement_is_adequate(self):
        result = check_sampling_adequacy(1.0, 4.0, "discrete-status")
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["ratio"], 1.0, places=9)

    def test_rate_below_the_requirement_is_flagged(self):
        result = check_sampling_adequacy(1.0, 3.0, "discrete-status")
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["ratio"], 0.75, places=9)
        self.assertEqual(len(result["findings"]), 1)

    def test_non_positive_allocated_rate_raises(self):
        with self.assertRaises(ValueError):
            check_sampling_adequacy(1.0, 0.0, "discrete-status")


class LimitMonitoringTests(unittest.TestCase):
    def test_ordered_thresholds_inside_the_range_pass(self):
        result = check_limit_monitoring(TEMPERATURE["limits"], TEMPERATURE["sensor_range"])
        self.assertTrue(result["ordered"])
        self.assertEqual(result["findings"], [])

    def test_inverted_thresholds_are_flagged(self):
        limits = dict(TEMPERATURE["limits"], high_warning=80.0)
        result = check_limit_monitoring(limits, TEMPERATURE["sensor_range"])
        self.assertFalse(result["ordered"])
        self.assertTrue(any("order broken" in f for f in result["findings"]))

    def test_threshold_outside_the_sensor_range_is_flagged(self):
        limits = dict(TEMPERATURE["limits"], low_alarm=-200.0)
        result = check_limit_monitoring(limits, TEMPERATURE["sensor_range"])
        self.assertFalse(result["ordered"])
        self.assertTrue(any("outside the sensor range" in f for f in result["findings"]))

    def test_malformed_limits_and_ranges_raise(self):
        with self.assertRaises(ValueError):
            check_limit_monitoring(["low_alarm"], TEMPERATURE["sensor_range"])
        with self.assertRaises(ValueError):
            check_limit_monitoring({"low_alarm": -40.0}, TEMPERATURE["sensor_range"])
        with self.assertRaises(ValueError):
            check_limit_monitoring(
                dict(TEMPERATURE["limits"], high_alarm="70"), TEMPERATURE["sensor_range"]
            )
        with self.assertRaises(ValueError):
            check_limit_monitoring(TEMPERATURE["limits"], (-60.0,))
        with self.assertRaises(ValueError):
            check_limit_monitoring(TEMPERATURE["limits"], (125.0, -60.0))


class BitRateTests(unittest.TestCase):
    def test_bit_rate_is_bits_times_rate(self):
        self.assertAlmostEqual(parameter_bit_rate_bps(12, 1.0), 12.0, places=9)
        self.assertAlmostEqual(parameter_bit_rate_bps(1, 4.0), 4.0, places=9)

    def test_bit_rate_rejects_bad_word_length_and_rate(self):
        with self.assertRaises(ValueError):
            parameter_bit_rate_bps(12.5, 1.0)
        with self.assertRaises(ValueError):
            parameter_bit_rate_bps(True, 1.0)
        with self.assertRaises(ValueError):
            parameter_bit_rate_bps(0, 1.0)
        with self.assertRaises(ValueError):
            parameter_bit_rate_bps(12, -1.0)

    def test_budget_sums_the_set_and_reports_the_margin(self):
        budget = compute_downlink_budget([TEMPERATURE, RELAY], 100.0)
        self.assertAlmostEqual(budget["total_bps"], 16.0, places=9)
        self.assertAlmostEqual(budget["margin_fraction"], 0.84, places=9)
        self.assertTrue(budget["within_allocation"])

    def test_budget_overrun_is_flagged_with_a_negative_margin(self):
        budget = compute_downlink_budget([TEMPERATURE, RELAY], 10.0)
        self.assertFalse(budget["within_allocation"])
        self.assertAlmostEqual(budget["margin_fraction"], -0.6, places=9)

    def test_budget_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            compute_downlink_budget({}, 100.0)
        with self.assertRaises(ValueError):
            compute_downlink_budget([], 100.0)
        with self.assertRaises(ValueError):
            compute_downlink_budget([TEMPERATURE], 0.0)
        with self.assertRaises(ValueError):
            compute_downlink_budget(["TM-TEMP"], 100.0)
        with self.assertRaises(ValueError):
            compute_downlink_budget([{"bits_per_sample": 8}], 100.0)


class FunctionCoverageTests(unittest.TestCase):
    def test_fully_covered_functions_report_clean(self):
        result = check_function_coverage(
            [{"id": "F-THERM", "critical": True}, {"id": "F-SWITCH", "critical": False}],
            [TEMPERATURE, RELAY],
        )
        self.assertTrue(result["covered"])

    def test_function_without_a_parameter_is_flagged(self):
        result = check_function_coverage(
            [{"id": "F-POWER", "critical": False}], [TEMPERATURE, RELAY]
        )
        self.assertFalse(result["covered"])
        self.assertIn("no telemetry parameter", result["findings"][0])

    def test_critical_function_without_an_onboard_monitor_is_flagged(self):
        result = check_function_coverage(
            [{"id": "F-SWITCH", "critical": True}], [TEMPERATURE, RELAY]
        )
        self.assertFalse(result["covered"])
        self.assertIn("no limit-checked parameter", result["findings"][0])

    def test_coverage_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            check_function_coverage([], [TEMPERATURE])
        with self.assertRaises(ValueError):
            check_function_coverage([{"id": "F-THERM", "critical": True}], [])
        with self.assertRaises(ValueError):
            check_function_coverage([{"id": "F-THERM", "critical": True}], ["TM-TEMP"])
        with self.assertRaises(ValueError):
            check_function_coverage(
                [{"id": "F-THERM", "critical": True}],
                [dict(TEMPERATURE, functions_covered="F-THERM")],
            )
        with self.assertRaises(ValueError):
            check_function_coverage(
                [{"id": "F-THERM", "critical": True}],
                [dict(TEMPERATURE, functions_covered=[7])],
            )
        with self.assertRaises(ValueError):
            check_function_coverage(["F-THERM"], [TEMPERATURE])
        with self.assertRaises(ValueError):
            check_function_coverage([{"id": "F-THERM"}], [TEMPERATURE])
        with self.assertRaises(ValueError):
            check_function_coverage(
                [{"id": "F-THERM", "critical": "yes"}], [TEMPERATURE]
            )
        with self.assertRaises(ValueError):
            check_function_coverage(
                [{"id": "F-THERM", "critical": True}],
                [dict(TEMPERATURE, limit_checked="yes")],
            )


class AssessCoverageTests(unittest.TestCase):
    def test_nominal_telemetry_set_is_sufficient(self):
        result = assess_telemetry_coverage(subsystem())
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["total_bps"], 16.0, places=9)
        self.assertAlmostEqual(result["margin_fraction"], 0.84, places=9)
        self.assertEqual(result["parameters"][0]["family"], "housekeeping-analog")
        self.assertAlmostEqual(result["parameters"][1]["ratio"], 1.0, places=9)

    def test_undersampled_parameter_is_attributed_to_its_id(self):
        sub = subsystem()
        sub["parameters"][1]["sample_rate_hz"] = 2.0
        result = assess_telemetry_coverage(sub)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any(f.startswith("TM-RELAY:") for f in result["findings"]))

    def test_limit_and_budget_findings_accumulate_together(self):
        sub = subsystem(downlink_allocation_bps=10.0)
        sub["parameters"][0]["limits"]["high_alarm"] = 40.0
        result = assess_telemetry_coverage(sub)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("order broken" in f for f in result["findings"]))
        self.assertTrue(any("downlink allocation" in f for f in result["findings"]))

    def test_uncovered_function_is_reported(self):
        sub = subsystem()
        sub["functions"].append({"id": "F-POWER", "critical": True})
        result = assess_telemetry_coverage(sub)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("F-POWER" in f for f in result["findings"]))

    def test_structural_errors_raise(self):
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(["AOCS"])
        broken = subsystem()
        del broken["functions"]
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(broken)
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(subsystem(parameters=[]))
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(subsystem(parameters=["TM-TEMP"]))
        stripped = subsystem()
        del stripped["parameters"][0]["bits_per_sample"]
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(stripped)

    def test_duplicate_parameter_ids_raise(self):
        sub = subsystem()
        sub["parameters"][1]["id"] = "TM-TEMP"
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(sub)

    def test_limit_checked_parameter_without_limits_raises(self):
        sub = subsystem()
        del sub["parameters"][0]["limits"]
        with self.assertRaises(ValueError):
            assess_telemetry_coverage(sub)


if __name__ == "__main__":
    unittest.main()
