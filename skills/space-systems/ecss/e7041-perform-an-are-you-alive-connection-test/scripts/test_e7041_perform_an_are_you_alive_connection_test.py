"""Contract test for the are-you-alive-connection-test leaf (stdlib unittest)."""

import unittest

from e7041_perform_an_are_you_alive_connection_test_logic import (
    APID_IDLE,
    ARE_YOU_ALIVE_REPORT,
    TIMEOUT_TOLERANCE_S,
    assess_are_you_alive_connection_test,
    candidate_responses,
    census_campaign,
    evaluate_connection_test,
    round_trip_s,
    validate_application_process_id,
    validate_request,
    validate_response,
    validate_timeout,
    within_timeout,
)


def request(apid=42, timeout=2.0, issued=10.0, **kw):
    record = {
        "destination_application_process_id": apid,
        "timeout_s": timeout,
        "issued_at_s": issued,
        "application_data": b"",
    }
    record.update(kw)
    return record


def report(apid=42, received=10.5, report_type=ARE_YOU_ALIVE_REPORT, **kw):
    record = {
        "report_type": report_type,
        "source_application_process_id": apid,
        "received_at_s": received,
        "application_data": b"",
    }
    record.update(kw)
    return record


class TestRequestValidation(unittest.TestCase):
    def test_valid_request_normalises(self):
        norm = validate_request(request())
        self.assertEqual(norm["destination_application_process_id"], 42)
        self.assertEqual(norm["timeout_s"], 2.0)

    def test_populated_data_field_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(application_data=b"\x01"))

    def test_idle_destination_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(apid=APID_IDLE))

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(timeout=0.0))

    def test_negative_issue_time_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(issued=-1.0))

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            validate_request({"destination_application_process_id": 42})

    def test_non_mapping_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request([42, 2.0])

    def test_boolean_application_process_id_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(True)

    def test_infinite_timeout_raises(self):
        with self.assertRaises(ValueError):
            validate_timeout(float("inf"))


class TestResponseValidation(unittest.TestCase):
    def test_valid_response_normalises(self):
        norm = validate_response(report())
        self.assertEqual(norm["report_type"], ARE_YOU_ALIVE_REPORT)
        self.assertEqual(norm["data_units"], 0)

    def test_empty_report_type_raises(self):
        with self.assertRaises(ValueError):
            validate_response(report(report_type="  "))

    def test_missing_arrival_time_raises(self):
        with self.assertRaises(ValueError):
            validate_response(
                {"report_type": ARE_YOU_ALIVE_REPORT,
                 "source_application_process_id": 42}
            )

    def test_negative_arrival_time_raises(self):
        with self.assertRaises(ValueError):
            validate_response(report(received=-0.5))


class TestCandidateFiltering(unittest.TestCase):
    def test_matching_report_is_kept(self):
        matches, discards = candidate_responses(request(), [report()])
        self.assertEqual(len(matches), 1)
        self.assertEqual(discards, [])

    def test_wrong_report_type_is_discarded(self):
        matches, discards = candidate_responses(
            request(), [report(report_type="housekeeping-parameter-report")]
        )
        self.assertEqual(matches, [])
        self.assertEqual(discards[0]["reason"], "wrong-report-type")

    def test_foreign_source_is_discarded(self):
        matches, discards = candidate_responses(request(), [report(apid=43)])
        self.assertEqual(matches, [])
        self.assertEqual(discards[0]["reason"], "foreign-source-application-process")

    def test_report_with_data_is_discarded(self):
        matches, discards = candidate_responses(
            request(), [report(application_data=b"\x00\x01")]
        )
        self.assertEqual(matches, [])
        self.assertEqual(discards[0]["reason"], "report-carries-application-data")

    def test_response_before_the_request_is_discarded(self):
        matches, discards = candidate_responses(request(), [report(received=9.0)])
        self.assertEqual(matches, [])
        self.assertEqual(discards[0]["reason"], "arrived-before-the-request")

    def test_matches_come_back_in_arrival_order(self):
        matches, _ = candidate_responses(
            request(), [report(received=11.0), report(received=10.25)]
        )
        self.assertEqual([m["received_at_s"] for m in matches], [10.25, 11.0])

    def test_non_sequence_responses_raises(self):
        with self.assertRaises(ValueError):
            candidate_responses(request(), report())


class TestRoundTrip(unittest.TestCase):
    def test_round_trip_is_the_difference(self):
        self.assertAlmostEqual(
            round_trip_s(request(issued=10.0), report(received=10.5)), 0.5, places=9
        )

    def test_response_predating_the_request_raises(self):
        with self.assertRaises(ValueError):
            round_trip_s(request(issued=10.0), report(received=9.5))

    def test_exact_budget_arrival_is_in_time(self):
        self.assertTrue(within_timeout(2.0, 2.0))

    def test_arrival_one_tolerance_past_the_budget_is_in_time(self):
        self.assertTrue(within_timeout(2.0 + TIMEOUT_TOLERANCE_S, 2.0))

    def test_clearly_late_arrival_is_out_of_time(self):
        self.assertFalse(within_timeout(2.5, 2.0))

    def test_negative_round_trip_raises(self):
        with self.assertRaises(ValueError):
            within_timeout(-0.1, 2.0)


class TestVerdicts(unittest.TestCase):
    def test_single_prompt_report_is_alive(self):
        result = evaluate_connection_test(request(), [report(received=10.5)])
        self.assertEqual(result["verdict"], "alive")
        self.assertTrue(result["alive"])
        self.assertAlmostEqual(result["round_trip_s"], 0.5, places=9)

    def test_no_report_is_no_response(self):
        result = evaluate_connection_test(request(), [])
        self.assertEqual(result["verdict"], "no-response")
        self.assertIsNone(result["round_trip_s"])

    def test_late_report_is_its_own_verdict(self):
        result = evaluate_connection_test(request(), [report(received=13.0)])
        self.assertEqual(result["verdict"], "late-response")
        self.assertFalse(result["alive"])
        self.assertAlmostEqual(result["round_trip_s"], 3.0, places=9)

    def test_arrival_exactly_on_the_budget_is_alive(self):
        result = evaluate_connection_test(request(), [report(received=12.0)])
        self.assertEqual(result["verdict"], "alive")
        self.assertAlmostEqual(result["round_trip_s"], 2.0, places=9)

    def test_two_reports_are_a_duplicate_finding_not_a_better_pass(self):
        result = evaluate_connection_test(
            request(), [report(received=10.4), report(received=10.6)]
        )
        self.assertEqual(result["verdict"], "duplicate-response")
        self.assertFalse(result["alive"])
        self.assertEqual(len(result["duplicate_arrival_times_s"]), 2)

    def test_discarded_traffic_does_not_make_a_pass(self):
        result = evaluate_connection_test(
            request(), [report(apid=43), report(report_type="event-report")]
        )
        self.assertEqual(result["verdict"], "no-response")
        self.assertEqual(len(result["discarded"]), 2)

    def test_pass_states_what_it_covers(self):
        result = evaluate_connection_test(request(), [report()])
        self.assertIn("no other service", result["covers"])


class TestCampaignCensus(unittest.TestCase):
    def test_availability_of_a_mixed_campaign(self):
        report_out = assess_are_you_alive_connection_test(
            {
                "tests": [
                    {"request": request(apid=42), "responses": [report(42, 10.5)]},
                    {"request": request(apid=43), "responses": []},
                    {"request": request(apid=44), "responses": [report(44, 10.25)]},
                    {"request": request(apid=45), "responses": [report(45, 14.0)]},
                ]
            }
        )
        census = report_out["census"]
        self.assertEqual(census["test_count"], 4)
        self.assertEqual(census["alive_count"], 2)
        self.assertAlmostEqual(census["availability"], 0.5, places=9)
        self.assertAlmostEqual(census["worst_alive_round_trip_s"], 0.5, places=9)
        self.assertEqual(census["silent_application_process_ids"], [43])
        self.assertFalse(report_out["all_alive"])

    def test_all_alive_campaign(self):
        report_out = assess_are_you_alive_connection_test(
            {"tests": [{"request": request(), "responses": [report()]}]}
        )
        self.assertTrue(report_out["all_alive"])
        self.assertEqual(report_out["findings"], [])

    def test_empty_campaign_raises(self):
        with self.assertRaises(ValueError):
            assess_are_you_alive_connection_test({"tests": []})

    def test_test_without_request_raises(self):
        with self.assertRaises(ValueError):
            assess_are_you_alive_connection_test({"tests": [{"responses": []}]})

    def test_unknown_verdict_raises(self):
        with self.assertRaises(ValueError):
            census_campaign([{"verdict": "probably-alive"}])

    def test_empty_result_set_raises(self):
        with self.assertRaises(ValueError):
            census_campaign([])

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_are_you_alive_connection_test(["tests"])


if __name__ == "__main__":
    unittest.main()
