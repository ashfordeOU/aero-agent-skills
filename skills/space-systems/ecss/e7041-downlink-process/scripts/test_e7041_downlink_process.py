"""Contract tests for the clause 6.13.3.3 downlink process logic."""

import unittest

from e7041_downlink_process_logic import (
    ABORT_REASONS,
    FIRST_PART,
    INTERMEDIATE_PART,
    LAST_PART,
    MIN_PARTS,
    abort_downlink,
    assess_downlink_process,
    claim_transaction_identifier,
    plan_parts,
    report_counts,
    verify_part_run,
)

PART = 1000


class PlanPartsTests(unittest.TestCase):
    def test_exact_multiple_gives_whole_parts(self):
        run = plan_parts(4000, PART)
        self.assertEqual(len(run), 4)
        self.assertEqual([r["octets"] for r in run], [1000, 1000, 1000, 1000])

    def test_remainder_lands_in_the_last_part(self):
        run = plan_parts(4200, PART)
        self.assertEqual(len(run), 5)
        self.assertEqual(run[-1]["octets"], 200)

    def test_roles_are_first_intermediate_last(self):
        run = plan_parts(4200, PART)
        self.assertEqual(run[0]["part_type"], FIRST_PART)
        self.assertEqual(run[1]["part_type"], INTERMEDIATE_PART)
        self.assertEqual(run[-1]["part_type"], LAST_PART)

    def test_numbering_starts_at_one_and_is_contiguous(self):
        run = plan_parts(3500, PART)
        self.assertEqual([r["sequence"] for r in run], [1, 2, 3, 4])

    def test_offsets_are_contiguous(self):
        run = plan_parts(2500, PART)
        self.assertEqual([r["offset"] for r in run], [0, 1000, 2000])

    def test_two_part_transfer_has_no_intermediate(self):
        run = plan_parts(1500, PART)
        self.assertEqual(len(run), MIN_PARTS)
        self.assertEqual(run[0]["part_type"], FIRST_PART)
        self.assertEqual(run[1]["part_type"], LAST_PART)

    def test_message_that_fits_one_part_is_refused(self):
        with self.assertRaises(ValueError):
            plan_parts(900, PART)

    def test_message_exactly_one_part_is_refused(self):
        with self.assertRaises(ValueError):
            plan_parts(1000, PART)

    def test_zero_length_message_is_refused(self):
        with self.assertRaises(ValueError):
            plan_parts(0, PART)

    def test_non_integer_part_size_is_refused(self):
        with self.assertRaises(ValueError):
            plan_parts(4000, 1000.0)


class VerifyRunTests(unittest.TestCase):
    def test_a_planned_run_verifies_clean(self):
        run = plan_parts(4200, PART)
        self.assertEqual(verify_part_run(run, 4200, PART), [])

    def test_a_numbering_gap_is_reported(self):
        run = plan_parts(4000, PART)
        run[2]["sequence"] = 9
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("breaks the numbering" in f for f in findings))

    def test_a_short_intermediate_part_is_reported(self):
        run = plan_parts(4000, PART)
        run[1]["octets"] = 400
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("is short" in f for f in findings))

    def test_an_oversized_part_is_reported(self):
        run = plan_parts(4000, PART)
        run[1]["octets"] = 1400
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("above the" in f for f in findings))

    def test_a_missing_last_part_is_reported(self):
        run = plan_parts(4000, PART)
        run[-1]["part_type"] = INTERMEDIATE_PART
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("last parts" in f for f in findings))

    def test_two_first_parts_are_reported(self):
        run = plan_parts(4000, PART)
        run[1]["part_type"] = FIRST_PART
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("first parts" in f for f in findings))

    def test_an_unrecognised_role_is_reported(self):
        run = plan_parts(4000, PART)
        run[1]["part_type"] = "middle"
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("unrecognised role" in f for f in findings))

    def test_a_run_that_undercovers_the_message_is_reported(self):
        run = plan_parts(4000, PART)
        del run[2]
        findings = verify_part_run(run, 4000, PART)
        self.assertTrue(any("covers" in f for f in findings))

    def test_a_single_part_run_is_reported(self):
        findings = verify_part_run(
            [{"sequence": 1, "part_type": FIRST_PART, "offset": 0, "octets": 1000}],
            1000,
            PART,
        )
        self.assertTrue(any("at least" in f for f in findings))

    def test_empty_run_is_refused(self):
        with self.assertRaises(ValueError):
            verify_part_run([], 4000, PART)

    def test_malformed_record_is_refused(self):
        with self.assertRaises(ValueError):
            verify_part_run([{"sequence": 1}], 4000, PART)


class ReportCountTests(unittest.TestCase):
    def test_counts_match_the_run_shape(self):
        counts = report_counts(plan_parts(4200, PART))
        self.assertEqual(counts[FIRST_PART], 1)
        self.assertEqual(counts[LAST_PART], 1)
        self.assertEqual(counts[INTERMEDIATE_PART], 3)

    def test_unrecognised_role_is_refused(self):
        with self.assertRaises(ValueError):
            report_counts([{"part_type": "middle"}])


class IdentifierTests(unittest.TestCase):
    def test_a_free_identifier_is_claimed(self):
        self.assertIn(7, claim_transaction_identifier({1, 2}, 7))

    def test_reusing_an_open_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            claim_transaction_identifier({1, 7}, 7)

    def test_a_missing_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            claim_transaction_identifier(set(), None)

    def test_non_collection_open_set_is_refused(self):
        with self.assertRaises(ValueError):
            claim_transaction_identifier(7, 8)


class AbortTests(unittest.TestCase):
    def test_parts_before_the_failure_stay_sent(self):
        run = plan_parts(4200, PART)
        result = abort_downlink(run, 7, 3, "store-read-failure")
        self.assertEqual(len(result["parts_sent"]), 2)
        self.assertEqual(result["octets_sent"], 2000)

    def test_abort_report_names_the_transaction_and_reason(self):
        run = plan_parts(4200, PART)
        result = abort_downlink(run, 7, 3, "store-read-failure")
        self.assertEqual(result["abort_report"]["transaction_id"], 7)
        self.assertEqual(result["abort_report"]["reason"], "store-read-failure")

    def test_failure_on_the_first_part_sends_nothing(self):
        run = plan_parts(4200, PART)
        result = abort_downlink(run, 7, 1, "resource-exhausted")
        self.assertEqual(result["parts_sent"], [])
        self.assertEqual(result["octets_sent"], 0)

    def test_unknown_reason_is_refused(self):
        run = plan_parts(4200, PART)
        with self.assertRaises(ValueError):
            abort_downlink(run, 7, 2, "because")

    def test_sequence_past_the_run_is_refused(self):
        run = plan_parts(4200, PART)
        with self.assertRaises(ValueError):
            abort_downlink(run, 7, 99, "transfer-cancelled")

    def test_every_recognised_reason_is_accepted(self):
        run = plan_parts(4200, PART)
        for reason in ABORT_REASONS:
            result = abort_downlink(run, 7, 2, reason)
            self.assertEqual(result["abort_report"]["reason"], reason)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "message_octets": 4200,
            "part_octets": PART,
            "transaction_id": 7,
            "open_identifiers": {1, 2},
        }
        spec.update(overrides)
        return spec

    def test_nominal_transfer_completes(self):
        result = assess_downlink_process(self._spec())
        self.assertTrue(result["completed"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["part_count"], 5)

    def test_identifier_is_added_to_the_open_set(self):
        result = assess_downlink_process(self._spec())
        self.assertIn(7, result["open_identifiers"])

    def test_reused_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_process(self._spec(open_identifiers={7}))

    def test_failure_truncates_the_run_and_is_flagged(self):
        result = assess_downlink_process(
            self._spec(failure={"sequence": 3, "reason": "part-generation-failure"})
        )
        self.assertFalse(result["completed"])
        self.assertEqual(len(result["aborted"]["parts_sent"]), 2)
        self.assertTrue(any("aborted at part" in f for f in result["findings"]))

    def test_malformed_failure_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_process(self._spec(failure={"sequence": 3}))

    def test_missing_key_is_refused(self):
        spec = self._spec()
        del spec["part_octets"]
        with self.assertRaises(ValueError):
            assess_downlink_process(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_process(["message_octets"])


if __name__ == "__main__":
    unittest.main()
