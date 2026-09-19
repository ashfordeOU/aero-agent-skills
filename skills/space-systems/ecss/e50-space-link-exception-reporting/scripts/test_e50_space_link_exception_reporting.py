"""Contract tests for the clause 5.6.14.9 space link exception reporting logic."""

import copy
import unittest

from e50_space_link_exception_reporting_logic import (
    COMPLIANT,
    EXCEPTIONS_UNREPORTED,
    REPORTS_NOT_IDENTIFIABLE,
    REPORT_CHANNEL_SATURATED,
    REQUIRED_REPORT_FIELDS,
    aggregated_load_bps,
    aggregation_required,
    assess_exception_reporting,
    max_unaggregated_occurrences,
    orphan_routes,
    report_gaps,
    report_load_bps,
    unreported_exception_types,
    validate_counts,
    validate_routes,
    validate_types,
)

DETECTABLE = ["frame-sync-loss", "bit-error-burst", "carrier-lock-loss"]
REPORT_BITS = 512.0
WINDOW = 1.0
BUDGET = 4096.0


def report(name, **overrides):
    base = {
        "exception_type": name,
        "occurrence_time_s": 10.0,
        "link_identifier": "x-band-1",
        "occurrence_count": 1,
    }
    base.update(overrides)
    return base


FULL_ROUTES = {name: report(name) for name in DETECTABLE}


def assess(**overrides):
    args = dict(
        detectable_types=DETECTABLE,
        routes=copy.deepcopy(FULL_ROUTES),
        report_bits=REPORT_BITS,
        window_s=WINDOW,
        channel_budget_bps=BUDGET,
        observed_counts={"frame-sync-loss": 1},
    )
    args.update(overrides)
    return assess_exception_reporting(**args)


class ValidationTests(unittest.TestCase):
    def test_type_list_validates(self):
        self.assertEqual(len(validate_types(DETECTABLE)), 3)

    def test_empty_type_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_types([])

    def test_blank_type_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_types(["frame-sync-loss", "  "])

    def test_repeated_type_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_types(["frame-sync-loss", "frame-sync-loss"])

    def test_string_instead_of_type_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_types("frame-sync-loss")

    def test_route_to_a_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_routes({"frame-sync-loss": "report it"})

    def test_non_integer_occurrence_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({"frame-sync-loss": 1.5})

    def test_negative_occurrence_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({"frame-sync-loss": -1})

    def test_boolean_occurrence_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({"frame-sync-loss": True})


class ReportFieldTests(unittest.TestCase):
    def test_a_full_report_has_no_gaps(self):
        self.assertEqual(report_gaps(report("frame-sync-loss")), [])

    def test_every_required_field_is_checked(self):
        self.assertEqual(len(report_gaps({})), len(REQUIRED_REPORT_FIELDS))

    def test_an_absent_field_is_a_gap(self):
        partial = report("frame-sync-loss")
        del partial["link_identifier"]
        self.assertEqual(report_gaps(partial), ["link_identifier absent"])

    def test_an_empty_string_field_is_a_gap_not_a_value(self):
        self.assertEqual(
            report_gaps(report("frame-sync-loss", link_identifier="   ")),
            ["link_identifier empty"],
        )

    def test_a_none_field_is_a_gap(self):
        self.assertEqual(
            report_gaps(report("frame-sync-loss", occurrence_time_s=None)),
            ["occurrence_time_s empty"],
        )

    def test_a_zero_occurrence_count_contradicts_the_report(self):
        self.assertEqual(
            report_gaps(report("frame-sync-loss", occurrence_count=0)),
            ["occurrence_count reports no occurrence"],
        )

    def test_a_non_integer_occurrence_count_is_a_gap(self):
        self.assertEqual(
            report_gaps(report("frame-sync-loss", occurrence_count="many")),
            ["occurrence_count is not a count"],
        )

    def test_a_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            report_gaps("frame-sync-loss")


class CoverageTests(unittest.TestCase):
    def test_full_coverage_leaves_nothing_unreported(self):
        self.assertEqual(unreported_exception_types(DETECTABLE, FULL_ROUTES), [])

    def test_an_unrouted_condition_is_a_silent_failure(self):
        routes = dict(FULL_ROUTES)
        del routes["carrier-lock-loss"]
        self.assertEqual(
            unreported_exception_types(DETECTABLE, routes), ["carrier-lock-loss"]
        )

    def test_a_route_for_nothing_detectable_is_an_orphan(self):
        routes = dict(FULL_ROUTES)
        routes["solar-array-arc"] = report("solar-array-arc")
        self.assertEqual(orphan_routes(DETECTABLE, routes), ["solar-array-arc"])

    def test_full_coverage_has_no_orphans(self):
        self.assertEqual(orphan_routes(DETECTABLE, FULL_ROUTES), [])


class ChannelTests(unittest.TestCase):
    def test_load_scales_with_the_occurrence_count(self):
        self.assertAlmostEqual(report_load_bps(4, REPORT_BITS, WINDOW), 2048.0, places=9)

    def test_no_occurrences_cost_nothing(self):
        self.assertAlmostEqual(report_load_bps(0, REPORT_BITS, WINDOW), 0.0, places=9)

    def test_aggregating_costs_one_report_per_window(self):
        self.assertAlmostEqual(aggregated_load_bps(REPORT_BITS, WINDOW), 512.0, places=9)

    def test_the_budget_carries_a_whole_number_of_reports(self):
        self.assertEqual(max_unaggregated_occurrences(BUDGET, REPORT_BITS, WINDOW), 8)

    def test_a_burst_exactly_filling_the_budget_needs_no_aggregation(self):
        self.assertFalse(aggregation_required(8, REPORT_BITS, WINDOW, BUDGET))

    def test_one_occurrence_past_the_budget_needs_aggregation(self):
        self.assertTrue(aggregation_required(9, REPORT_BITS, WINDOW, BUDGET))

    def test_negative_occurrences_rejected(self):
        with self.assertRaises(ValueError):
            report_load_bps(-1, REPORT_BITS, WINDOW)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            report_load_bps(1, REPORT_BITS, 0.0)


class AssessTests(unittest.TestCase):
    def test_a_complete_design_satisfies_both_items(self):
        result = assess()
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertTrue(result["item_reported"])
        self.assertTrue(result["item_identifiable"])
        self.assertEqual(result["findings"], [])

    def test_an_unrouted_condition_fails_the_first_item_only(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["carrier-lock-loss"]
        result = assess(routes=routes)
        self.assertEqual(result["verdict"], EXCEPTIONS_UNREPORTED)
        self.assertFalse(result["item_reported"])
        self.assertTrue(result["item_identifiable"])

    def test_the_silent_failure_is_named(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["carrier-lock-loss"]
        findings = assess(routes=routes)["findings"]
        self.assertTrue(any("nobody is told" in f for f in findings))

    def test_a_thin_report_fails_the_second_item_only(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["bit-error-burst"]["link_identifier"]
        result = assess(routes=routes)
        self.assertEqual(result["verdict"], REPORTS_NOT_IDENTIFIABLE)
        self.assertTrue(result["item_reported"])
        self.assertFalse(result["item_identifiable"])

    def test_the_thin_report_says_which_field_is_missing(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["bit-error-burst"]["link_identifier"]
        findings = assess(routes=routes)["findings"]
        self.assertTrue(any("link_identifier absent" in f for f in findings))

    def test_the_two_items_fail_independently(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["carrier-lock-loss"]
        del routes["bit-error-burst"]["occurrence_time_s"]
        result = assess(routes=routes)
        self.assertFalse(result["item_reported"])
        self.assertFalse(result["item_identifiable"])

    def test_a_burst_can_saturate_the_report_channel(self):
        result = assess(observed_counts={"bit-error-burst": 9})
        self.assertEqual(result["verdict"], REPORT_CHANNEL_SATURATED)
        self.assertFalse(result["item_reported"])

    def test_saturation_still_leaves_the_reports_identifiable(self):
        self.assertTrue(assess(observed_counts={"bit-error-burst": 9})["item_identifiable"])

    def test_saturation_names_the_aggregated_alternative(self):
        findings = assess(observed_counts={"bit-error-burst": 9})["findings"]
        self.assertTrue(any("carrying a count" in f for f in findings))

    def test_the_saturating_condition_is_named(self):
        result = assess(observed_counts={"bit-error-burst": 9})
        self.assertEqual(result["saturating_types"], ["bit-error-burst"])

    def test_a_burst_exactly_at_the_budget_stays_compliant(self):
        result = assess(observed_counts={"bit-error-burst": 8})
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_a_silent_failure_outranks_a_saturated_channel(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["carrier-lock-loss"]
        result = assess(routes=routes, observed_counts={"bit-error-burst": 9})
        self.assertEqual(result["verdict"], EXCEPTIONS_UNREPORTED)

    def test_an_orphan_route_is_reported_without_failing_either_item(self):
        routes = copy.deepcopy(FULL_ROUTES)
        routes["solar-array-arc"] = report("solar-array-arc")
        result = assess(routes=routes)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertTrue(any("can never be raised" in f for f in result["findings"]))

    def test_the_stated_aggregation_limit_actually_fits_the_budget(self):
        limit = assess()["max_unaggregated_occurrences"]
        self.assertEqual(
            assess(observed_counts={"bit-error-burst": limit})["verdict"], COMPLIANT
        )

    def test_unreported_occurrences_do_not_load_the_report_channel(self):
        routes = copy.deepcopy(FULL_ROUTES)
        del routes["bit-error-burst"]
        result = assess(routes=routes, observed_counts={"bit-error-burst": 99})
        self.assertAlmostEqual(result["report_load_bps"], 0.0, places=9)

    def test_bad_report_size_rejected(self):
        with self.assertRaises(ValueError):
            assess(report_bits=0.0)

    def test_bad_channel_budget_rejected(self):
        with self.assertRaises(ValueError):
            assess(channel_budget_bps=-1.0)


if __name__ == "__main__":
    unittest.main()
