"""Contract tests for the clause 5.7.4.3 network management service logic."""

import unittest

from e50_inter_spacecraft_network_management_service_logic import (
    COMPLETE,
    DEFICIENT,
    REQUIRED_FUNCTIONS,
    assess_management_service,
    convergence_time_s,
    detection_time_s,
    function_coverage,
    management_overhead_bps,
    max_managed_members,
    max_poll_period_s,
    overhead_fraction,
    validate_count,
    validate_nonnegative,
    validate_positive,
)

FULL = sorted(REQUIRED_FUNCTIONS)
CAPACITY = 1000000.0
EXCHANGE = 2048.0
PERIOD = 4.0
MEMBERS = 8


def service(**override):
    args = {
        "declared_functions": FULL,
        "members": MEMBERS,
        "exchange_bits": EXCHANGE,
        "poll_period_s": PERIOD,
        "capacity_bps": CAPACITY,
        "overhead_allowance": 0.02,
        "miss_threshold": 3,
        "diameter_hops": 5,
        "hop_latency_s": 0.5,
        "reconfiguration_s": 2.0,
        "required_convergence_s": 20.0,
    }
    args.update(override)
    return assess_management_service(**args)


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
            validate_positive("4")

    def test_infinite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"))

    def test_fractional_member_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(2.5, "members")

    def test_zero_member_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0, "members")

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(True, "members")

    def test_declared_functions_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            function_coverage("route-maintenance")

    def test_blank_declared_function_rejected(self):
        with self.assertRaises(ValueError):
            function_coverage(["route-maintenance", "  "])


class CoverageTests(unittest.TestCase):
    def test_a_full_declaration_is_complete(self):
        self.assertTrue(function_coverage(FULL)["complete"])

    def test_a_dropped_function_is_named(self):
        partial = [f for f in FULL if f != "route-maintenance"]
        self.assertEqual(function_coverage(partial)["missing"], ["route-maintenance"])

    def test_a_dropped_function_is_not_complete(self):
        partial = [f for f in FULL if f != "address-assignment"]
        self.assertFalse(function_coverage(partial)["complete"])

    def test_an_unrecognised_name_is_reported_not_ignored(self):
        coverage = function_coverage(FULL + ["telemetry-downlink"])
        self.assertEqual(coverage["unrecognised"], ["telemetry-downlink"])

    def test_case_and_padding_do_not_hide_a_function(self):
        coverage = function_coverage([" Route-Maintenance "] + FULL[1:])
        self.assertNotIn("route-maintenance", coverage["missing"])

    def test_an_extra_name_does_not_substitute_for_a_missing_one(self):
        partial = [f for f in FULL if f != "route-maintenance"] + ["route-fixing"]
        self.assertEqual(function_coverage(partial)["missing"], ["route-maintenance"])


class OverheadTests(unittest.TestCase):
    def test_overhead_scales_with_membership(self):
        self.assertAlmostEqual(
            management_overhead_bps(8, EXCHANGE, PERIOD),
            2.0 * management_overhead_bps(4, EXCHANGE, PERIOD),
            places=6,
        )

    def test_overhead_falls_with_a_longer_period(self):
        slow = management_overhead_bps(MEMBERS, EXCHANGE, 8.0)
        fast = management_overhead_bps(MEMBERS, EXCHANGE, 2.0)
        self.assertLess(slow, fast)

    def test_overhead_fraction_is_overhead_over_capacity(self):
        overhead = management_overhead_bps(MEMBERS, EXCHANGE, PERIOD)
        self.assertAlmostEqual(
            overhead_fraction(overhead, CAPACITY), overhead / CAPACITY, places=12
        )

    def test_zero_capacity_rejected(self):
        with self.assertRaises(ValueError):
            overhead_fraction(1000.0, 0.0)

    def test_largest_membership_fits_the_allowance(self):
        largest = max_managed_members(EXCHANGE, PERIOD, CAPACITY, 0.02)
        fraction = overhead_fraction(
            management_overhead_bps(largest, EXCHANGE, PERIOD), CAPACITY
        )
        self.assertLessEqual(fraction, 0.02)

    def test_one_member_past_the_largest_breaks_the_allowance(self):
        largest = max_managed_members(EXCHANGE, PERIOD, CAPACITY, 0.02)
        fraction = overhead_fraction(
            management_overhead_bps(largest + 1, EXCHANGE, PERIOD), CAPACITY
        )
        self.assertGreater(fraction, 0.02)

    def test_an_allowance_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            max_managed_members(EXCHANGE, PERIOD, CAPACITY, 1.5)


class TimelinessTests(unittest.TestCase):
    def test_detection_is_the_period_times_the_miss_threshold(self):
        self.assertAlmostEqual(detection_time_s(4.0, 3), 12.0, places=9)

    def test_convergence_adds_propagation_and_reconfiguration(self):
        self.assertAlmostEqual(convergence_time_s(4.0, 3, 5, 0.5, 2.0), 16.5, places=9)

    def test_convergence_grows_with_network_diameter(self):
        near = convergence_time_s(4.0, 3, 2, 0.5, 2.0)
        far = convergence_time_s(4.0, 3, 9, 0.5, 2.0)
        self.assertGreater(far, near)

    def test_longest_period_spends_exactly_the_remaining_allowance(self):
        period = max_poll_period_s(3, 5, 0.5, 2.0, 20.0)
        self.assertAlmostEqual(convergence_time_s(period, 3, 5, 0.5, 2.0), 20.0, places=9)

    def test_a_fixed_cost_that_exhausts_the_allowance_returns_zero(self):
        self.assertAlmostEqual(max_poll_period_s(3, 5, 2.0, 12.0, 20.0), 0.0, places=9)

    def test_zero_required_convergence_rejected(self):
        with self.assertRaises(ValueError):
            max_poll_period_s(3, 5, 0.5, 2.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_service_is_complete(self):
        self.assertEqual(service()["verdict"], COMPLETE)

    def test_a_missing_function_makes_it_deficient(self):
        partial = [f for f in FULL if f != "configuration-control"]
        self.assertEqual(service(declared_functions=partial)["verdict"], DEFICIENT)

    def test_a_missing_function_is_reported(self):
        partial = [f for f in FULL if f != "configuration-control"]
        result = service(declared_functions=partial)
        self.assertTrue(any("configuration-control" in f for f in result["findings"]))

    def test_an_overhead_breach_makes_it_deficient(self):
        self.assertEqual(service(members=400)["verdict"], DEFICIENT)

    def test_an_overhead_breach_names_the_membership_that_fits(self):
        result = service(members=400)
        self.assertLess(result["max_members"], 400)

    def test_the_stated_membership_limit_actually_fits(self):
        result = service(members=400)
        fixed = service(members=result["max_members"])
        self.assertTrue(fixed["overhead_within_allowance"])

    def test_a_slow_convergence_makes_it_deficient(self):
        self.assertEqual(service(poll_period_s=20.0)["verdict"], DEFICIENT)

    def test_the_stated_poll_period_actually_converges_in_time(self):
        result = service(poll_period_s=20.0)
        fixed = service(poll_period_s=result["max_poll_period_s"])
        self.assertTrue(fixed["convergence_within_allowance"])

    def test_convergence_landing_on_the_allowance_passes(self):
        result = service(required_convergence_s=convergence_time_s(PERIOD, 3, 5, 0.5, 2.0))
        self.assertTrue(result["convergence_within_allowance"])

    def test_overhead_landing_on_the_allowance_passes(self):
        overhead = management_overhead_bps(MEMBERS, EXCHANGE, PERIOD)
        result = service(overhead_allowance=overhead / CAPACITY)
        self.assertTrue(result["overhead_within_allowance"])

    def test_an_unrecognised_function_is_surfaced_as_a_finding(self):
        result = service(declared_functions=FULL + ["housekeeping-poll"])
        self.assertTrue(any("unrecognised" in f for f in result["findings"]))

    def test_an_unrecognised_function_alone_does_not_fail_coverage(self):
        result = service(declared_functions=FULL + ["housekeeping-poll"])
        self.assertEqual(result["verdict"], COMPLETE)

    def test_a_sound_service_reports_no_findings(self):
        self.assertEqual(service()["findings"], [])

    def test_a_bad_member_count_is_rejected(self):
        with self.assertRaises(ValueError):
            service(members=0)


if __name__ == "__main__":
    unittest.main()
