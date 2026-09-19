"""Contract test for the on-board-connection-test leaf (stdlib unittest)."""

import unittest

from e7041_perform_an_on_board_connection_test_logic import (
    APID_IDLE,
    ON_BOARD_CONNECTION_TEST_REPORT,
    TIMEOUT_TOLERANCE_S,
    assess_on_board_connection_test,
    evaluate_on_board_connection_test,
    filter_responses,
    round_trip_s,
    sweep_targets,
    target_is_accessible,
    validate_accessible_targets,
    validate_application_process_id,
    validate_request,
    validate_response,
    within_timeout,
)

ACCESSIBLE = [20, 21, 22]


def request(target=20, timeout=3.0, issued=100.0, **kw):
    record = {
        "target_application_process_id": target,
        "timeout_s": timeout,
        "issued_at_s": issued,
        "application_data": b"",
    }
    record.update(kw)
    return record


def report(target=20, received=100.5, report_type=ON_BOARD_CONNECTION_TEST_REPORT):
    return {
        "report_type": report_type,
        "target_application_process_id": target,
        "received_at_s": received,
    }


class TestRequestValidation(unittest.TestCase):
    def test_valid_request_normalises(self):
        norm = validate_request(request())
        self.assertEqual(norm["target_application_process_id"], 20)
        self.assertEqual(norm["timeout_s"], 3.0)

    def test_extra_application_data_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(application_data=b"\x01\x02"))

    def test_idle_target_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(target=APID_IDLE))

    def test_out_of_range_target_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(target=3000))

    def test_negative_timeout_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(timeout=-1.0))

    def test_missing_target_raises(self):
        with self.assertRaises(ValueError):
            validate_request({"timeout_s": 3.0})

    def test_boolean_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(False)

    def test_response_missing_target_raises(self):
        with self.assertRaises(ValueError):
            validate_response(
                {"report_type": ON_BOARD_CONNECTION_TEST_REPORT,
                 "received_at_s": 100.5}
            )


class TestAccessibility(unittest.TestCase):
    def test_declared_target_is_accessible(self):
        self.assertTrue(target_is_accessible(ACCESSIBLE, 21))

    def test_undeclared_target_is_not_accessible(self):
        self.assertFalse(target_is_accessible(ACCESSIBLE, 30))

    def test_duplicate_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_accessible_targets([20, 20])

    def test_inaccessible_target_transmits_nothing(self):
        result = evaluate_on_board_connection_test(
            request(target=30), [report(target=30)], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "target-not-accessible")
        self.assertFalse(result["transmitted"])
        self.assertIn("nothing was learned", result["findings"][0])


class TestResponseFiltering(unittest.TestCase):
    def test_matching_report_is_kept(self):
        matches, mismatches, discards = filter_responses(request(), [report()])
        self.assertEqual(len(matches), 1)
        self.assertEqual(mismatches, [])
        self.assertEqual(discards, [])

    def test_wrong_report_type_is_discarded(self):
        _, _, discards = filter_responses(
            request(), [report(report_type="are-you-alive-connection-test-report")]
        )
        self.assertEqual(discards[0]["reason"], "wrong-report-type")

    def test_report_about_another_target_is_a_mismatch_not_a_discard(self):
        matches, mismatches, discards = filter_responses(
            request(target=20), [report(target=21)]
        )
        self.assertEqual(matches, [])
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(discards, [])

    def test_response_before_the_request_is_discarded(self):
        _, _, discards = filter_responses(request(issued=100.0), [report(received=99.0)])
        self.assertEqual(discards[0]["reason"], "arrived-before-the-request")

    def test_non_sequence_responses_raise(self):
        with self.assertRaises(ValueError):
            filter_responses(request(), report())


class TestTiming(unittest.TestCase):
    def test_round_trip_is_the_difference(self):
        self.assertAlmostEqual(
            round_trip_s(request(issued=100.0), report(received=100.75)), 0.75, places=9
        )

    def test_exact_budget_arrival_is_in_time(self):
        self.assertTrue(within_timeout(3.0, 3.0))

    def test_one_tolerance_past_the_budget_is_in_time(self):
        self.assertTrue(within_timeout(3.0 + TIMEOUT_TOLERANCE_S, 3.0))

    def test_clearly_late_arrival_is_out_of_time(self):
        self.assertFalse(within_timeout(4.0, 3.0))

    def test_response_predating_the_request_raises(self):
        with self.assertRaises(ValueError):
            round_trip_s(request(issued=100.0), report(received=99.5))


class TestVerdicts(unittest.TestCase):
    def test_prompt_correct_report_is_reached(self):
        result = evaluate_on_board_connection_test(
            request(), [report(received=100.5)], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "reached")
        self.assertTrue(result["reached"])
        self.assertAlmostEqual(result["round_trip_s"], 0.5, places=9)

    def test_silence_is_no_response(self):
        result = evaluate_on_board_connection_test(request(), [], ACCESSIBLE)
        self.assertEqual(result["verdict"], "no-response")
        self.assertIsNone(result["round_trip_s"])

    def test_arrival_exactly_on_the_budget_is_reached(self):
        result = evaluate_on_board_connection_test(
            request(), [report(received=103.0)], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "reached")
        self.assertAlmostEqual(result["round_trip_s"], 3.0, places=9)

    def test_late_report_is_its_own_verdict(self):
        result = evaluate_on_board_connection_test(
            request(), [report(received=105.0)], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "late-response")
        self.assertFalse(result["reached"])

    def test_fast_mismatch_outranks_the_timing(self):
        result = evaluate_on_board_connection_test(
            request(target=20), [report(target=21, received=100.01)], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "target-identifier-mismatch")
        self.assertEqual(result["reported_target_application_process_ids"], [21])

    def test_two_answers_are_a_duplicate_finding(self):
        result = evaluate_on_board_connection_test(
            request(), [report(received=100.4), report(received=100.6)], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "duplicate-response")
        self.assertEqual(len(result["duplicate_arrival_times_s"]), 2)

    def test_only_foreign_report_types_leave_the_target_silent(self):
        result = evaluate_on_board_connection_test(
            request(), [report(report_type="event-report")], ACCESSIBLE
        )
        self.assertEqual(result["verdict"], "no-response")
        self.assertEqual(len(result["discarded"]), 1)


class TestSweep(unittest.TestCase):
    def _sweep(self):
        return assess_on_board_connection_test(
            {
                "accessible_targets": ACCESSIBLE,
                "tests": [
                    {"request": request(20), "responses": [report(20, 100.5)]},
                    {"request": request(21), "responses": []},
                    {"request": request(22), "responses": [report(22, 101.5)]},
                    {"request": request(30), "responses": []},
                ],
            }
        )

    def test_three_groups_are_kept_apart(self):
        sweep = self._sweep()["sweep"]
        self.assertEqual(sweep["reached_application_process_ids"], [20, 22])
        self.assertEqual(sweep["silent_application_process_ids"], [21])
        self.assertEqual(sweep["refused_application_process_ids"], [30])

    def test_refused_target_is_out_of_the_reachability_fraction(self):
        sweep = self._sweep()["sweep"]
        self.assertEqual(sweep["asked_count"], 3)
        self.assertAlmostEqual(sweep["reached_fraction_of_asked"], 2.0 / 3.0, places=9)

    def test_worst_round_trip_comes_from_the_reached_group(self):
        sweep = self._sweep()["sweep"]
        self.assertAlmostEqual(sweep["worst_reached_round_trip_s"], 1.5, places=9)

    def test_clean_sweep_reports_all_reached(self):
        report_out = assess_on_board_connection_test(
            {
                "accessible_targets": ACCESSIBLE,
                "tests": [{"request": request(20), "responses": [report(20, 100.2)]}],
            }
        )
        self.assertTrue(report_out["all_asked_targets_reached"])
        self.assertEqual(report_out["findings"], [])

    def test_mismatch_lands_in_the_defective_group(self):
        report_out = assess_on_board_connection_test(
            {
                "accessible_targets": ACCESSIBLE,
                "tests": [{"request": request(20), "responses": [report(21, 100.2)]}],
            }
        )
        self.assertEqual(
            report_out["sweep"]["defective_application_process_ids"], [20]
        )
        self.assertFalse(report_out["all_asked_targets_reached"])

    def test_unknown_verdict_raises(self):
        with self.assertRaises(ValueError):
            sweep_targets([{"verdict": "maybe", "target_application_process_id": 20}])

    def test_empty_sweep_raises(self):
        with self.assertRaises(ValueError):
            sweep_targets([])

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_on_board_connection_test({"accessible_targets": ACCESSIBLE})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_on_board_connection_test([request()])


if __name__ == "__main__":
    unittest.main()
