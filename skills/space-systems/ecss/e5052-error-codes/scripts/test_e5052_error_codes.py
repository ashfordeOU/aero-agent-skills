"""Contract test for the RMAP error-code leaf (stdlib unittest)."""

import unittest

from e5052_error_codes_logic import (
    DETECTION_ORDER,
    FAMILIES,
    FAMILY_AUTHORISATION,
    FAMILY_COMMAND,
    FAMILY_DATA,
    FAMILY_RESERVED,
    FAMILY_ROUTING,
    FAMILY_SUCCESS,
    SILENT_CONDITION,
    STATUS_REGISTRY,
    STATUS_SUCCESS,
    check_reply_consistency,
    detect_status,
    grade_transaction,
    is_reserved_status,
    is_success,
    known_status_codes,
    reply_is_sent,
    status_family,
    status_slug,
    summarise_transactions,
    validate_observation,
)


def observation(**kw):
    return dict(kw)


class TestRegistry(unittest.TestCase):
    def test_every_entry_carries_slug_family_and_wording(self):
        for code, entry in STATUS_REGISTRY.items():
            self.assertEqual(len(entry), 3, "entry %d" % code)

    def test_every_family_is_a_known_family(self):
        for entry in STATUS_REGISTRY.values():
            self.assertIn(entry[1], FAMILIES)

    def test_slugs_are_unique(self):
        slugs = [entry[0] for entry in STATUS_REGISTRY.values()]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_known_codes_are_returned_in_order(self):
        codes = known_status_codes()
        self.assertEqual(list(codes), sorted(codes))

    def test_success_is_the_zero_value(self):
        self.assertEqual(STATUS_SUCCESS, 0)
        self.assertEqual(status_family(0), FAMILY_SUCCESS)

    def test_unlisted_value_is_reserved(self):
        self.assertTrue(is_reserved_status(200))
        self.assertEqual(status_slug(200), "reserved-200")

    def test_listed_reserved_value_is_reserved(self):
        self.assertTrue(is_reserved_status(8))

    def test_routing_family_is_used(self):
        self.assertEqual(status_family(12), FAMILY_ROUTING)

    def test_authorisation_family_is_used(self):
        self.assertEqual(status_family(3), FAMILY_AUTHORISATION)
        self.assertEqual(status_family(10), FAMILY_AUTHORISATION)

    def test_data_family_is_used(self):
        for code in (4, 5, 6, 7):
            self.assertEqual(status_family(code), FAMILY_DATA)

    def test_command_family_is_used(self):
        for code in (1, 2, 9, 11):
            self.assertEqual(status_family(code), FAMILY_COMMAND)

    def test_out_of_range_status_raises(self):
        with self.assertRaises(ValueError):
            status_slug(256)

    def test_boolean_status_raises(self):
        with self.assertRaises(ValueError):
            status_family(True)

    def test_is_success_only_for_zero(self):
        self.assertTrue(is_success(0))
        self.assertFalse(is_success(1))


class TestObservation(unittest.TestCase):
    def test_absent_conditions_default_to_false(self):
        flags = validate_observation({})
        self.assertFalse(any(flags.values()))

    def test_unknown_condition_token_raises(self):
        with self.assertRaises(ValueError):
            validate_observation({"link_disconnected": True})

    def test_non_boolean_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_observation({"rejected_destination_key": 1})

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_observation(["rejected_destination_key"])

    def test_every_detection_token_is_accepted(self):
        flags = validate_observation(dict((name, False) for name, _ in DETECTION_ORDER))
        self.assertEqual(len(flags), len(DETECTION_ORDER))


class TestDetectStatus(unittest.TestCase):
    def test_clean_command_completes(self):
        self.assertEqual(detect_status(observation()), STATUS_SUCCESS)

    def test_single_condition_maps_to_its_code(self):
        self.assertEqual(detect_status(observation(rejected_destination_key=True)), 3)

    def test_header_fault_reports_no_status_at_all(self):
        self.assertIsNone(detect_status(observation(header_check_failed=True)))

    def test_header_fault_outranks_every_later_condition(self):
        self.assertIsNone(detect_status(observation(header_check_failed=True,
                                                    data_check_value_mismatch=True)))

    def test_key_rejection_outranks_a_payload_fault(self):
        self.assertEqual(
            detect_status(observation(rejected_destination_key=True,
                                      data_check_value_mismatch=True)), 3)

    def test_unknown_address_outranks_key_rejection(self):
        self.assertEqual(
            detect_status(observation(unknown_target_address=True,
                                      rejected_destination_key=True)), 12)

    def test_unspecified_failure_is_the_last_resort(self):
        self.assertEqual(detect_status(observation(unspecified_failure=True)), 1)

    def test_verify_overrun_outranks_a_short_payload(self):
        self.assertEqual(
            detect_status(observation(verify_buffer_overrun=True,
                                      payload_shorter_than_declared=True)), 9)

    def test_every_detection_code_is_in_the_registry(self):
        for _, code in DETECTION_ORDER:
            if code is not None:
                self.assertIn(code, STATUS_REGISTRY)


class TestReplyIsSent(unittest.TestCase):
    def test_acknowledged_clean_command_gets_a_reply(self):
        self.assertTrue(reply_is_sent(observation(), True))

    def test_unacknowledged_command_gets_none(self):
        self.assertFalse(reply_is_sent(observation(), False))

    def test_untrusted_header_silences_even_an_acknowledged_command(self):
        self.assertFalse(reply_is_sent(observation(header_check_failed=True), True))

    def test_silent_condition_token_is_a_detection_token(self):
        self.assertIn(SILENT_CONDITION, [name for name, _ in DETECTION_ORDER])

    def test_non_boolean_acknowledge_raises(self):
        with self.assertRaises(ValueError):
            reply_is_sent(observation(), "yes")


class TestReplyConsistency(unittest.TestCase):
    def test_successful_reply_with_data_is_clean(self):
        self.assertEqual(check_reply_consistency(0, 64), [])

    def test_failed_reply_with_no_data_is_clean(self):
        self.assertEqual(check_reply_consistency(4, 0), [])

    def test_failed_reply_carrying_data_is_flagged(self):
        self.assertTrue(check_reply_consistency(4, 16))

    def test_reserved_status_is_flagged(self):
        self.assertTrue(check_reply_consistency(8, 0))

    def test_negative_returned_length_raises(self):
        with self.assertRaises(ValueError):
            check_reply_consistency(0, -1)


class TestGradeTransaction(unittest.TestCase):
    def test_matching_report_is_consistent(self):
        result = grade_transaction({"observation": observation(rejected_destination_key=True),
                                    "reported_status": 3})
        self.assertTrue(result["consistent"])
        self.assertEqual(result["expected_slug"], "rejected-destination-key")

    def test_wrong_report_is_flagged(self):
        result = grade_transaction({"observation": observation(rejected_destination_key=True),
                                    "reported_status": 1})
        self.assertFalse(result["consistent"])
        self.assertTrue(any("call" in f for f in result["findings"]))

    def test_missing_report_on_an_owed_reply_is_flagged(self):
        result = grade_transaction({"observation": observation()})
        self.assertTrue(any("no status was captured" in f for f in result["findings"]))

    def test_reply_captured_after_a_header_fault_is_flagged(self):
        result = grade_transaction({"observation": observation(header_check_failed=True),
                                    "reported_status": 1})
        self.assertTrue(any("none should have been sent" in f for f in result["findings"]))

    def test_dropped_command_reports_no_family(self):
        result = grade_transaction({"observation": observation(header_check_failed=True)})
        self.assertIsNone(result["family"])
        self.assertFalse(result["reply_sent"])

    def test_unacknowledged_command_owes_no_status(self):
        result = grade_transaction({"observation": observation(),
                                    "acknowledge_requested": False})
        self.assertTrue(result["consistent"])

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            grade_transaction([3])


class TestSummarise(unittest.TestCase):
    def test_families_are_counted(self):
        summary = summarise_transactions([
            {"observation": observation(), "reported_status": 0, "returned_data_length": 8},
            {"observation": observation(rejected_destination_key=True), "reported_status": 3},
            {"observation": observation(data_check_value_mismatch=True), "reported_status": 4},
        ])
        self.assertEqual(summary["family_counts"][FAMILY_SUCCESS], 1)
        self.assertEqual(summary["family_counts"][FAMILY_AUTHORISATION], 1)
        self.assertEqual(summary["family_counts"][FAMILY_DATA], 1)

    def test_dropped_commands_are_counted_separately(self):
        summary = summarise_transactions([
            {"observation": observation(header_check_failed=True)},
            {"observation": observation(), "reported_status": 0},
        ])
        self.assertEqual(summary["dropped_without_reply"], 1)

    def test_findings_carry_the_record_index(self):
        summary = summarise_transactions([
            {"observation": observation(), "reported_status": 0},
            {"observation": observation(unused_command_code=True), "reported_status": 1},
        ])
        self.assertTrue(any(f.startswith("record 1:") for f in summary["findings"]))

    def test_clean_run_is_consistent(self):
        summary = summarise_transactions([
            {"observation": observation(), "reported_status": 0},
        ])
        self.assertTrue(summary["consistent"])

    def test_empty_run_raises(self):
        with self.assertRaises(ValueError):
            summarise_transactions([])

    def test_reserved_family_is_available_for_counting(self):
        self.assertIn(FAMILY_RESERVED, FAMILIES)


if __name__ == "__main__":
    unittest.main()
