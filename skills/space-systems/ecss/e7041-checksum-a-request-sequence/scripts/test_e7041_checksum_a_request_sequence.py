"""Contract test for the e7041 checksum-a-request-sequence leaf."""

import unittest

from e7041_checksum_a_request_sequence_logic import (
    ALGORITHM_CRC16,
    ALGORITHM_ISO8,
    ALGORITHMS,
    REFUSAL_EMPTY_SEQUENCE,
    REFUSAL_UNDER_LOAD,
    REFUSAL_UNKNOWN_ALGORITHM,
    REFUSAL_UNKNOWN_SEQUENCE,
    VERDICT_CORRUPT,
    VERDICT_INTACT,
    VERDICT_REFUSED,
    VERDICT_UNVERIFIED,
    assess_checksum,
    body_octets,
    checksum_refusals,
    checksum_report,
    compute_over_octets,
    compute_sequence_checksum,
    crc16_ccitt,
    find_sequence,
    iso_checksum_8,
    validate_request_record,
    validate_sequence,
    validate_store,
)


def request_record(index=1, octets=(0x11, 0x22, 0x33)):
    return {"index": index, "octets": list(octets)}


def sequence(sid="RS-SLEW", load_state="loaded", execution_state="inactive",
             body=None, **kw):
    if body is None:
        body = [request_record(1, (0x11, 0x22)), request_record(2, (0x33, 0x44))]
    record = {
        "id": sid,
        "load_state": load_state,
        "execution_state": execution_state,
        "body": body,
    }
    record.update(kw)
    return record


def store():
    return [
        sequence("RS-SLEW"),
        sequence("RS-RUNNING", execution_state="executing"),
        sequence("RS-BLANK", load_state="empty", body=[]),
        sequence("RS-ARRIVING", load_state="under-load",
                 body=[request_record(1, (0x01,))]),
    ]


class TestAlgorithms(unittest.TestCase):
    def test_the_crc_matches_its_published_check_value(self):
        octets = [ord(character) for character in "123456789"]
        self.assertEqual(crc16_ccitt(octets), 0x29B1)

    def test_the_crc_of_an_empty_run_is_the_seed(self):
        self.assertEqual(crc16_ccitt([]), 0xFFFF)

    def test_the_crc_depends_on_octet_order(self):
        self.assertNotEqual(crc16_ccitt([0x01, 0x02]), crc16_ccitt([0x02, 0x01]))

    def test_the_crc_rejects_an_octet_above_the_range(self):
        with self.assertRaises(ValueError):
            crc16_ccitt([256])

    def test_the_crc_rejects_a_non_integer_octet(self):
        with self.assertRaises(ValueError):
            crc16_ccitt(["ff"])

    def test_the_modular_checksum_completes_the_sum_to_zero(self):
        octets = [0x11, 0x22, 0x33]
        self.assertEqual((sum(octets) + iso_checksum_8(octets)) & 0xFF, 0)

    def test_the_modular_checksum_of_an_empty_run_is_zero(self):
        self.assertEqual(iso_checksum_8([]), 0)

    def test_the_modular_checksum_rejects_a_negative_octet(self):
        with self.assertRaises(ValueError):
            iso_checksum_8([-1])

    def test_the_algorithm_selector_dispatches_the_crc(self):
        self.assertEqual(compute_over_octets([0x01], ALGORITHM_CRC16),
                         crc16_ccitt([0x01]))

    def test_the_algorithm_selector_dispatches_the_modular_checksum(self):
        self.assertEqual(compute_over_octets([0x01], ALGORITHM_ISO8),
                         iso_checksum_8([0x01]))

    def test_an_unknown_algorithm_raises(self):
        with self.assertRaises(ValueError):
            compute_over_octets([0x01], "md5")

    def test_both_declared_algorithms_are_dispatchable(self):
        for name in ALGORITHMS:
            self.assertIsInstance(compute_over_octets([0x05, 0x06], name), int)


class TestValidation(unittest.TestCase):
    def test_a_valid_request_record_normalizes(self):
        self.assertEqual(validate_request_record(request_record(), "RS-SLEW", 1)["index"], 1)

    def test_a_request_out_of_stored_order_raises(self):
        with self.assertRaises(ValueError):
            validate_request_record(request_record(index=4), "RS-SLEW", 1)

    def test_a_request_with_no_octets_raises(self):
        with self.assertRaises(ValueError):
            validate_request_record({"index": 1, "octets": []}, "RS-SLEW", 1)

    def test_a_request_with_an_out_of_range_octet_raises(self):
        with self.assertRaises(ValueError):
            validate_request_record({"index": 1, "octets": [300]}, "RS-SLEW", 1)

    def test_a_non_mapping_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request_record("0x11", "RS-SLEW", 1)

    def test_a_valid_sequence_normalizes(self):
        self.assertEqual(validate_sequence(sequence())["request_count"], 2)

    def test_a_body_with_a_gap_in_its_indices_raises(self):
        broken = sequence(body=[request_record(1, (1,)), request_record(3, (2,))])
        with self.assertRaises(ValueError):
            validate_sequence(broken)

    def test_an_empty_slot_carrying_a_body_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="empty"))

    def test_a_loaded_slot_with_no_body_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(body=[]))

    def test_executing_while_not_loaded_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="under-load",
                                       execution_state="executing"))

    def test_a_non_integer_declared_checksum_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(declared_checksum="0x29B1"))

    def test_a_negative_declared_checksum_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(declared_checksum=-2))

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence("RS-A"), sequence("RS-A")])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(sequence())


class TestBody(unittest.TestCase):
    def test_the_body_flattens_in_stored_order(self):
        self.assertEqual(body_octets(sequence()), (0x11, 0x22, 0x33, 0x44))

    def test_an_empty_slot_flattens_to_nothing(self):
        self.assertEqual(body_octets(sequence(load_state="empty", body=[])), ())

    def test_the_checksum_reads_the_stored_body(self):
        expected = crc16_ccitt([0x11, 0x22, 0x33, 0x44])
        self.assertEqual(compute_sequence_checksum(sequence(), ALGORITHM_CRC16), expected)

    def test_a_changed_octet_changes_the_checksum(self):
        altered = sequence(body=[request_record(1, (0x11, 0x22)),
                                 request_record(2, (0x33, 0x45))])
        self.assertNotEqual(compute_sequence_checksum(sequence(), ALGORITHM_CRC16),
                            compute_sequence_checksum(altered, ALGORITHM_CRC16))

    def test_a_reordered_body_changes_the_checksum(self):
        swapped = sequence(body=[request_record(1, (0x33, 0x44)),
                                 request_record(2, (0x11, 0x22))])
        self.assertNotEqual(compute_sequence_checksum(sequence(), ALGORITHM_CRC16),
                            compute_sequence_checksum(swapped, ALGORITHM_CRC16))

    def test_checksumming_an_empty_body_raises(self):
        with self.assertRaises(ValueError):
            compute_sequence_checksum(sequence(load_state="empty", body=[]),
                                      ALGORITHM_CRC16)

    def test_a_held_sequence_is_found(self):
        self.assertEqual(find_sequence(store(), "RS-RUNNING")["request_count"], 2)

    def test_an_absent_sequence_is_not_found(self):
        self.assertIsNone(find_sequence(store(), "RS-GHOST"))


class TestRefusals(unittest.TestCase):
    def test_a_loaded_sequence_raises_no_refusal(self):
        self.assertEqual(checksum_refusals(store(), "RS-SLEW", ALGORITHM_CRC16), [])

    def test_an_unknown_identifier_is_refused(self):
        refusals = checksum_refusals(store(), "RS-GHOST", ALGORITHM_CRC16)
        self.assertIn(REFUSAL_UNKNOWN_SEQUENCE, [item["code"] for item in refusals])

    def test_an_empty_sequence_is_refused(self):
        refusals = checksum_refusals(store(), "RS-BLANK", ALGORITHM_CRC16)
        self.assertEqual(refusals[0]["code"], REFUSAL_EMPTY_SEQUENCE)

    def test_a_sequence_under_load_is_refused(self):
        refusals = checksum_refusals(store(), "RS-ARRIVING", ALGORITHM_CRC16)
        self.assertEqual(refusals[0]["code"], REFUSAL_UNDER_LOAD)

    def test_an_unknown_algorithm_is_refused(self):
        refusals = checksum_refusals(store(), "RS-SLEW", "md5")
        self.assertEqual(refusals[0]["code"], REFUSAL_UNKNOWN_ALGORITHM)

    def test_an_executing_sequence_is_not_refused(self):
        self.assertEqual(checksum_refusals(store(), "RS-RUNNING", ALGORITHM_CRC16), [])


class TestReport(unittest.TestCase):
    def test_the_report_names_the_sequence_and_algorithm(self):
        report = checksum_report(store(), "RS-SLEW", ALGORITHM_CRC16)
        self.assertEqual(report["sequence_id"], "RS-SLEW")
        self.assertEqual(report["algorithm"], ALGORITHM_CRC16)

    def test_the_report_carries_the_body_length(self):
        report = checksum_report(store(), "RS-SLEW", ALGORITHM_CRC16)
        self.assertEqual(report["octet_count"], 4)
        self.assertEqual(report["request_count"], 2)

    def test_the_report_carries_the_computed_value(self):
        report = checksum_report(store(), "RS-SLEW", ALGORITHM_ISO8)
        self.assertEqual(report["checksum"], iso_checksum_8([0x11, 0x22, 0x33, 0x44]))

    def test_reporting_on_an_absent_sequence_raises(self):
        with self.assertRaises(ValueError):
            checksum_report(store(), "RS-GHOST", ALGORITHM_CRC16)


class TestAssessment(unittest.TestCase):
    def test_a_matching_declared_checksum_reads_intact(self):
        records = [sequence("RS-SLEW", declared_checksum=crc16_ccitt([0x11, 0x22, 0x33, 0x44]))]
        result = assess_checksum(records, "RS-SLEW", ALGORITHM_CRC16)
        self.assertEqual(result["verdict"], VERDICT_INTACT)

    def test_a_drifted_declared_checksum_reads_corrupt(self):
        records = [sequence("RS-SLEW", declared_checksum=1)]
        result = assess_checksum(records, "RS-SLEW", ALGORITHM_CRC16)
        self.assertEqual(result["verdict"], VERDICT_CORRUPT)

    def test_a_corruption_finding_names_both_values(self):
        records = [sequence("RS-SLEW", declared_checksum=1)]
        findings = assess_checksum(records, "RS-SLEW", ALGORITHM_CRC16)["findings"]
        self.assertTrue(any("computes" in text for text in findings))

    def test_a_corrupt_report_still_carries_the_computed_value(self):
        records = [sequence("RS-SLEW", declared_checksum=1)]
        result = assess_checksum(records, "RS-SLEW", ALGORITHM_CRC16)
        self.assertNotEqual(result["report"]["checksum"], 1)
        self.assertEqual(result["declared_checksum"], 1)

    def test_no_declared_checksum_reads_unverified(self):
        result = assess_checksum(store(), "RS-SLEW", ALGORITHM_CRC16)
        self.assertEqual(result["verdict"], VERDICT_UNVERIFIED)

    def test_an_unverified_result_says_so_in_its_findings(self):
        findings = assess_checksum(store(), "RS-SLEW", ALGORITHM_CRC16)["findings"]
        self.assertTrue(any("rather than verifying" in text for text in findings))

    def test_a_refused_request_carries_no_report(self):
        result = assess_checksum(store(), "RS-BLANK", ALGORITHM_CRC16)
        self.assertEqual(result["verdict"], VERDICT_REFUSED)
        self.assertIsNone(result["report"])

    def test_a_refused_request_notifies_with_its_code(self):
        result = assess_checksum(store(), "RS-ARRIVING", ALGORITHM_CRC16)
        self.assertIn(REFUSAL_UNDER_LOAD, result["notification"]["codes"])

    def test_an_executing_sequence_can_be_checksummed_while_it_runs(self):
        result = assess_checksum(store(), "RS-RUNNING", ALGORITHM_CRC16)
        self.assertTrue(result["accepted"])

    def test_the_checksum_changes_no_sequence_state(self):
        before = validate_store(store())
        result = assess_checksum(store(), "RS-RUNNING", ALGORITHM_CRC16)
        self.assertTrue(result["state_unchanged"])
        self.assertEqual(result["resulting_store"], before)

    def test_the_two_algorithms_give_different_reports(self):
        crc = assess_checksum(store(), "RS-SLEW", ALGORITHM_CRC16)
        iso = assess_checksum(store(), "RS-SLEW", ALGORITHM_ISO8)
        self.assertNotEqual(crc["computed_checksum"], iso["computed_checksum"])

    def test_an_invalid_store_raises_before_any_checksum(self):
        broken = store()
        broken[0]["body"][1]["index"] = 5
        with self.assertRaises(ValueError):
            assess_checksum(broken, "RS-RUNNING", ALGORITHM_CRC16)


if __name__ == "__main__":
    unittest.main()
