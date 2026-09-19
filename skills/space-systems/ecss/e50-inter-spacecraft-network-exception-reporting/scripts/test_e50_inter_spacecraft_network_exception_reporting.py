"""Contract tests for the clause 5.7.4.4 exception reporting logic."""

import unittest

from e50_inter_spacecraft_network_exception_reporting_logic import (
    LOST,
    REPORTED,
    assess_exception_reporting,
    highest_severity,
    reporting_latency_s,
    retention_bits,
    suppressed_per_s,
    sustainable_rate_per_s,
    validate_count,
    validate_flow,
    validate_nonnegative,
    validate_positive,
    validate_severity,
)

ALARM = {
    "severity": "alarm",
    "rate_per_s": 0.5,
    "record_bits": 512.0,
    "detection_s": 0.2,
    "queueing_s": 0.1,
    "hops": 3,
    "hop_latency_s": 0.4,
    "forwarding_s": 0.5,
    "required_latency_s": 5.0,
}
NOTICE = dict(ALARM, severity="notice", rate_per_s=4.0, required_latency_s=60.0)
OUTAGE = 600.0
STORE = 2000000.0


def graded(flows=None, **override):
    args = {
        "flows": flows if flows is not None else [ALARM, NOTICE],
        "outage_s": OUTAGE,
        "store_bits": STORE,
        "limit_per_s": 10.0,
        "limiter_per_severity": False,
    }
    args.update(override)
    return assess_exception_reporting(**args)


class ValidationTests(unittest.TestCase):
    def test_zero_is_a_valid_nonnegative(self):
        self.assertAlmostEqual(validate_nonnegative(0), 0.0, places=9)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1.0)

    def test_boolean_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive(True)

    def test_text_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive("5")

    def test_not_a_number_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(float("nan"))

    def test_fractional_hop_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(2.5, "hops")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity("critical")

    def test_severity_case_and_padding_tolerated(self):
        self.assertEqual(validate_severity("  Alarm "), "alarm")

    def test_flow_with_an_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow(dict(ALARM, priority=1))

    def test_flow_without_a_latency_allowance_rejected(self):
        bad = {k: v for k, v in ALARM.items() if k != "required_latency_s"}
        with self.assertRaises(ValueError):
            validate_flow(bad)

    def test_flow_with_a_zero_record_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow(dict(ALARM, record_bits=0.0))

    def test_empty_flow_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_exception_reporting([], OUTAGE, STORE, 10.0)

    def test_non_boolean_limiter_mode_rejected(self):
        with self.assertRaises(ValueError):
            graded(limiter_per_severity="shared")


class LatencyTests(unittest.TestCase):
    def test_latency_sums_every_stage(self):
        self.assertAlmostEqual(reporting_latency_s(0.2, 0.1, 3, 0.4, 0.5), 2.0, places=9)

    def test_latency_grows_with_the_hop_count(self):
        near = reporting_latency_s(0.2, 0.1, 1, 0.4, 0.5)
        far = reporting_latency_s(0.2, 0.1, 6, 0.4, 0.5)
        self.assertGreater(far, near)

    def test_a_flow_inside_its_allowance_passes(self):
        self.assertTrue(graded([ALARM])["latency_ok"])

    def test_a_flow_past_its_allowance_fails(self):
        self.assertFalse(graded([dict(ALARM, required_latency_s=1.0)])["latency_ok"])

    def test_latency_landing_on_the_allowance_passes(self):
        exact = reporting_latency_s(0.2, 0.1, 3, 0.4, 0.5)
        self.assertTrue(graded([dict(ALARM, required_latency_s=exact)])["latency_ok"])

    def test_a_late_flow_is_reported_with_its_severity(self):
        result = graded([dict(ALARM, required_latency_s=1.0)])
        self.assertTrue(any("alarm exceptions reach" in f for f in result["findings"]))


class RetentionTests(unittest.TestCase):
    def test_retention_scales_with_the_outage(self):
        short = retention_bits(0.5, 300.0, 512.0)
        long = retention_bits(0.5, 600.0, 512.0)
        self.assertAlmostEqual(long, 2.0 * short, places=6)

    def test_retention_scales_with_the_record_size(self):
        self.assertAlmostEqual(retention_bits(1.0, 10.0, 512.0), 5120.0, places=6)

    def test_a_silent_flow_needs_no_store(self):
        self.assertAlmostEqual(retention_bits(0.0, 600.0, 512.0), 0.0, places=9)

    def test_zero_outage_rejected(self):
        with self.assertRaises(ValueError):
            retention_bits(0.5, 0.0, 512.0)

    def test_sustainable_rate_inverts_the_retention_model(self):
        rate = sustainable_rate_per_s(153600.0, 600.0, 512.0)
        self.assertAlmostEqual(retention_bits(rate, 600.0, 512.0), 153600.0, places=6)

    def test_a_store_that_holds_the_outage_passes(self):
        self.assertTrue(graded()["retention_ok"])

    def test_a_store_that_cannot_hold_the_outage_fails(self):
        self.assertFalse(graded(store_bits=1000.0)["retention_ok"])

    def test_a_store_landing_exactly_on_the_need_passes(self):
        needed = graded()["required_store_bits"]
        self.assertTrue(graded(store_bits=needed)["retention_ok"])

    def test_a_short_store_is_offered_a_rate_remedy(self):
        result = graded(store_bits=1000.0)
        self.assertTrue(any("hold the offered rate at" in f for f in result["findings"]))


class SuppressionTests(unittest.TestCase):
    def test_a_limiter_above_the_offered_rate_discards_nothing(self):
        self.assertAlmostEqual(suppressed_per_s(3.0, 10.0), 0.0, places=9)

    def test_a_limiter_below_the_offered_rate_discards_the_excess(self):
        self.assertAlmostEqual(suppressed_per_s(14.0, 10.0), 4.0, places=9)

    def test_a_limiter_equal_to_the_offered_rate_discards_nothing(self):
        self.assertAlmostEqual(suppressed_per_s(10.0, 10.0), 0.0, places=9)

    def test_a_shared_limiter_sees_the_aggregate_offered_load(self):
        result = graded(limit_per_s=1.0)
        self.assertAlmostEqual(result["offered_per_s"], 4.5, places=9)

    def test_a_shared_limiter_below_the_aggregate_loses_exceptions(self):
        self.assertEqual(graded(limit_per_s=1.0)["verdict"], LOST)

    def test_a_shared_limiter_names_the_severity_it_can_crowd_out(self):
        result = graded(limit_per_s=1.0)
        self.assertTrue(any("alarm report" in f for f in result["findings"]))

    def test_a_per_group_limiter_grades_each_group_on_its_own_rate(self):
        result = graded(limit_per_s=1.0, limiter_per_severity=True)
        alarm = [f for f in result["flows"] if f["severity"] == "alarm"][0]
        self.assertAlmostEqual(alarm["suppressed_per_s"], 0.0, places=9)

    def test_a_per_group_limiter_still_reports_a_group_it_starves(self):
        result = graded(limit_per_s=1.0, limiter_per_severity=True)
        notice = [f for f in result["flows"] if f["severity"] == "notice"][0]
        self.assertAlmostEqual(notice["suppressed_per_s"], 3.0, places=9)

    def test_splitting_the_limiter_per_group_rescues_the_urgent_flow(self):
        shared = graded(limit_per_s=1.0)
        split = graded(flows=[ALARM], limit_per_s=1.0, limiter_per_severity=True)
        self.assertEqual(shared["verdict"], LOST)
        self.assertEqual(split["verdict"], REPORTED)


class SeverityTests(unittest.TestCase):
    def test_the_most_urgent_group_present_is_reported(self):
        self.assertEqual(highest_severity([NOTICE, ALARM]), "alarm")

    def test_ordering_does_not_depend_on_the_input_order(self):
        self.assertEqual(highest_severity([ALARM, NOTICE]), highest_severity([NOTICE, ALARM]))

    def test_a_warning_outranks_a_notice(self):
        warning = dict(ALARM, severity="warning")
        self.assertEqual(highest_severity([NOTICE, warning]), "warning")


class VerdictTests(unittest.TestCase):
    def test_a_sound_design_reports_its_exceptions(self):
        self.assertEqual(graded()["verdict"], REPORTED)

    def test_a_sound_design_raises_no_findings(self):
        self.assertEqual(graded()["findings"], [])

    def test_a_late_flow_alone_loses_exceptions(self):
        result = graded(flows=[dict(ALARM, required_latency_s=1.0)])
        self.assertEqual(result["verdict"], LOST)

    def test_a_short_store_alone_loses_exceptions(self):
        self.assertEqual(graded(store_bits=1000.0)["verdict"], LOST)

    def test_the_required_store_is_the_sum_over_the_flows(self):
        result = graded()
        self.assertAlmostEqual(
            result["required_store_bits"],
            sum(f["retention_bits"] for f in result["flows"]),
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
