"""Contract tests for the clause 6.14.3.3 forwarding control processing logic."""

import unittest

from e7041_forwarding_control_processing_logic import (
    DOWNLINK,
    REASON_DISABLED,
    REASON_FORWARDED,
    REASON_NO_DEFINITION,
    REASON_SUBSAMPLED,
    STORAGE,
    matching_level,
    process_stream,
    route_report,
    validate_rates,
    validate_report,
    validate_store,
)


def store_with(**kwargs):
    return kwargs


WHOLE_APID = {10: {"whole": True, "service_types": {}}}
WHOLE_SERVICE = {
    10: {"whole": False, "service_types": {3: {"whole": True, "subtypes": []}}}
}
SUBTYPE_ONLY = {
    10: {"whole": False, "service_types": {3: {"whole": False, "subtypes": [25]}}}
}


def report(apid=10, stype=3, subtype=25):
    return {
        "application_process": apid,
        "service_type": stype,
        "message_subtype": subtype,
    }


class StoreValidationTests(unittest.TestCase):
    def test_a_well_formed_store_validates(self):
        self.assertIs(validate_store(SUBTYPE_ONLY), SUBTYPE_ONLY)

    def test_an_empty_store_validates(self):
        self.assertEqual(validate_store({}), {})

    def test_a_non_mapping_store_is_refused(self):
        with self.assertRaises(ValueError):
            validate_store([10])

    def test_an_entry_without_the_whole_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_store({10: {"service_types": {}}})

    def test_a_non_boolean_whole_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_store({10: {"whole": 1, "service_types": {}}})

    def test_a_zero_service_type_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_store({10: {"whole": False,
                                 "service_types": {0: {"whole": True, "subtypes": []}}}})

    def test_a_non_collection_subtype_list_is_refused(self):
        with self.assertRaises(ValueError):
            validate_store({10: {"whole": False,
                                 "service_types": {3: {"whole": False, "subtypes": 25}}}})


class RateValidationTests(unittest.TestCase):
    def test_absent_rates_give_an_empty_mapping(self):
        self.assertEqual(validate_rates(None), {})

    def test_a_rate_of_one_is_accepted(self):
        self.assertEqual(validate_rates({(10, 3, 25): 1}), {(10, 3, 25): 1})

    def test_a_rate_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_rates({(10, 3, 25): 0})

    def test_a_malformed_rate_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_rates({10: 2})

    def test_a_non_mapping_rate_table_is_refused(self):
        with self.assertRaises(ValueError):
            validate_rates([2])


class ReportValidationTests(unittest.TestCase):
    def test_a_well_formed_report_validates(self):
        self.assertEqual(validate_report(report()), (10, 3, 25))

    def test_a_missing_field_is_refused(self):
        with self.assertRaises(ValueError):
            validate_report({"application_process": 10, "service_type": 3})

    def test_a_non_integer_subtype_is_refused(self):
        with self.assertRaises(ValueError):
            validate_report(report(subtype="25"))

    def test_a_non_mapping_report_is_refused(self):
        with self.assertRaises(ValueError):
            validate_report([10, 3, 25])


class MatchingLevelTests(unittest.TestCase):
    def test_wholesale_application_process_matches_at_its_own_level(self):
        self.assertEqual(matching_level(WHOLE_APID, 10, 5, 4), (10, None, None))

    def test_whole_service_type_matches_at_service_level(self):
        self.assertEqual(matching_level(WHOLE_SERVICE, 10, 3, 99), (10, 3, None))

    def test_subtype_entry_matches_at_subtype_level(self):
        self.assertEqual(matching_level(SUBTYPE_ONLY, 10, 3, 25), (10, 3, 25))

    def test_an_uncovered_subtype_does_not_match(self):
        self.assertIsNone(matching_level(SUBTYPE_ONLY, 10, 3, 26))

    def test_an_unknown_application_process_does_not_match(self):
        self.assertIsNone(matching_level(SUBTYPE_ONLY, 11, 3, 25))

    def test_an_uncovered_service_type_does_not_match(self):
        self.assertIsNone(matching_level(WHOLE_SERVICE, 10, 5, 4))


class RouteReportTests(unittest.TestCase):
    def test_a_covered_report_is_forwarded(self):
        decision = route_report(SUBTYPE_ONLY, report(), {10}, {}, {})
        self.assertTrue(decision["forwarded"])
        self.assertEqual(decision["disposition"], DOWNLINK)
        self.assertEqual(decision["reason"], REASON_FORWARDED)

    def test_an_uncovered_report_goes_to_storage(self):
        decision = route_report(SUBTYPE_ONLY, report(subtype=26), {10}, {}, {})
        self.assertEqual(decision["disposition"], STORAGE)
        self.assertEqual(decision["reason"], REASON_NO_DEFINITION)

    def test_a_disabled_application_process_forwards_nothing(self):
        decision = route_report(WHOLE_APID, report(), set(), {}, {})
        self.assertEqual(decision["reason"], REASON_DISABLED)
        self.assertEqual(decision["disposition"], STORAGE)

    def test_a_disabled_application_process_does_not_advance_the_counter(self):
        counters = {}
        route_report(WHOLE_APID, report(), set(), {}, counters)
        self.assertEqual(counters, {})

    def test_an_uncovered_report_does_not_advance_the_counter(self):
        counters = {}
        route_report(SUBTYPE_ONLY, report(subtype=26), {10}, {}, counters)
        self.assertEqual(counters, {})

    def test_non_mapping_counters_are_refused(self):
        with self.assertRaises(ValueError):
            route_report(SUBTYPE_ONLY, report(), {10}, {}, [])


class SubsamplingTests(unittest.TestCase):
    def test_rate_of_three_forwards_the_first_and_every_third(self):
        counters = {}
        rates = {(10, 3, 25): 3}
        outcomes = [
            route_report(SUBTYPE_ONLY, report(), {10}, rates, counters)["forwarded"]
            for _ in range(7)
        ]
        self.assertEqual(outcomes, [True, False, False, True, False, False, True])

    def test_subsampled_report_reports_the_subsampling_reason(self):
        counters = {}
        rates = {(10, 3, 25): 2}
        route_report(SUBTYPE_ONLY, report(), {10}, rates, counters)
        decision = route_report(SUBTYPE_ONLY, report(), {10}, rates, counters)
        self.assertEqual(decision["reason"], REASON_SUBSAMPLED)

    def test_rate_of_one_forwards_every_matching_report(self):
        counters = {}
        outcomes = [
            route_report(SUBTYPE_ONLY, report(), {10}, {}, counters)["forwarded"]
            for _ in range(4)
        ]
        self.assertEqual(outcomes, [True, True, True, True])

    def test_counters_are_kept_per_definition_level(self):
        store = {
            10: {"whole": False, "service_types": {3: {"whole": False, "subtypes": [25]}}},
            11: {"whole": True, "service_types": {}},
        }
        counters = {}
        rates = {(10, 3, 25): 2, (11, None, None): 2}
        route_report(store, report(apid=10), {10, 11}, rates, counters)
        route_report(store, report(apid=11), {10, 11}, rates, counters)
        second_ten = route_report(store, report(apid=10), {10, 11}, rates, counters)
        self.assertFalse(second_ten["forwarded"])
        self.assertEqual(counters[(10, 3, 25)], 2)
        self.assertEqual(counters[(11, None, None)], 1)


class StreamTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "store": SUBTYPE_ONLY,
            "enabled_application_processes": [10],
            "reports": [report(), report(subtype=26), report()],
        }
        spec.update(overrides)
        return spec

    def test_stream_counts_forwarded_and_stored(self):
        result = process_stream(self._spec())
        self.assertEqual(result["forwarded_count"], 2)
        self.assertEqual(result["stored_count"], 1)

    def test_per_application_process_tally_is_reported(self):
        result = process_stream(self._spec())
        self.assertEqual(result["per_application_process"][10]["forwarded"], 2)
        self.assertEqual(result["per_application_process"][10]["stored"], 1)

    def test_a_disabled_application_process_with_definitions_is_flagged(self):
        result = process_stream(self._spec(enabled_application_processes=[]))
        self.assertEqual(result["forwarded_count"], 0)
        self.assertTrue(any("is disabled" in f for f in result["findings"]))

    def test_a_stream_forwarding_nothing_is_flagged(self):
        result = process_stream(self._spec(store={}, reports=[report()]))
        self.assertTrue(any("no report" in f for f in result["findings"]))

    def test_an_empty_stream_raises_no_finding(self):
        result = process_stream(self._spec(reports=[]))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["forwarded_count"], 0)

    def test_subsampling_thins_the_stream(self):
        result = process_stream(
            self._spec(
                reports=[report() for _ in range(6)],
                subsampling_rates={(10, 3, 25): 3},
            )
        )
        self.assertEqual(result["forwarded_count"], 2)

    def test_missing_reports_key_is_refused(self):
        spec = self._spec()
        del spec["reports"]
        with self.assertRaises(ValueError):
            process_stream(spec)

    def test_non_collection_enabled_set_is_refused(self):
        with self.assertRaises(ValueError):
            process_stream(self._spec(enabled_application_processes=10))

    def test_non_sequence_report_stream_is_refused(self):
        with self.assertRaises(ValueError):
            process_stream(self._spec(reports=report()))

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            process_stream(["store"])


if __name__ == "__main__":
    unittest.main()
