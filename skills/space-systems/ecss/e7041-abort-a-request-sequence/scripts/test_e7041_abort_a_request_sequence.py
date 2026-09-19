"""Contract test for the e7041 abort-a-request-sequence leaf."""

import unittest

from e7041_abort_a_request_sequence_logic import (
    REFUSAL_ALREADY_ABORTED,
    REFUSAL_ALREADY_COMPLETED,
    REFUSAL_NOT_EXECUTING,
    REFUSAL_UNKNOWN_SEQUENCE,
    VERDICT_ABORTED,
    VERDICT_REFUSED,
    abort_refusals,
    abort_report,
    apply_abort,
    assess_abort,
    find_sequence,
    progress,
    validate_sequence,
    validate_store,
)


def sequence(sid="RS-SLEW", load_state="loaded", execution_state="executing",
             request_count=10, released_count=4):
    return {
        "id": sid,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "released_count": released_count,
    }


def store():
    return [
        sequence("RS-SLEW"),
        sequence("RS-IDLE", execution_state="inactive", request_count=5,
                 released_count=0),
        sequence("RS-DONE", execution_state="completed", request_count=3,
                 released_count=3),
        sequence("RS-STOPPED", execution_state="aborted", request_count=8,
                 released_count=2),
    ]


class TestValidation(unittest.TestCase):
    def test_a_valid_sequence_normalizes(self):
        record = validate_sequence(sequence())
        self.assertEqual(record["released_count"], 4)

    def test_a_non_mapping_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(["RS-SLEW"])

    def test_a_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(sid=""))

    def test_an_unknown_execution_state_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(execution_state="paused"))

    def test_releasing_more_than_the_body_holds_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(request_count=3, released_count=4))

    def test_executing_while_not_loaded_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="under-load"))

    def test_an_inactive_sequence_with_released_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(execution_state="inactive", released_count=2))

    def test_a_completed_sequence_with_pending_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(
                sequence(execution_state="completed", request_count=6,
                         released_count=4)
            )

    def test_a_negative_released_count_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(released_count=-1))

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence("RS-A"), sequence("RS-A")])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(sequence())


class TestProgress(unittest.TestCase):
    def test_pending_is_the_body_less_what_went_out(self):
        self.assertEqual(progress(sequence())["pending_count"], 6)

    def test_the_step_reached_is_the_released_count(self):
        self.assertEqual(progress(sequence())["step_reached"], 4)

    def test_a_sequence_with_nothing_left_is_at_the_last_boundary(self):
        reached = progress(sequence(request_count=4, released_count=4))
        self.assertTrue(reached["at_last_boundary"])

    def test_a_sequence_with_work_left_is_not_at_the_last_boundary(self):
        self.assertFalse(progress(sequence())["at_last_boundary"])

    def test_a_held_sequence_is_found(self):
        self.assertEqual(find_sequence(store(), "RS-DONE")["request_count"], 3)

    def test_an_absent_sequence_is_not_found(self):
        self.assertIsNone(find_sequence(store(), "RS-GHOST"))


class TestRefusals(unittest.TestCase):
    def test_an_executing_sequence_raises_no_refusal(self):
        self.assertEqual(abort_refusals(store(), "RS-SLEW"), [])

    def test_an_unknown_identifier_is_refused(self):
        refusals = abort_refusals(store(), "RS-GHOST")
        self.assertEqual(refusals[0]["code"], REFUSAL_UNKNOWN_SEQUENCE)

    def test_an_inactive_sequence_is_refused_not_absorbed(self):
        refusals = abort_refusals(store(), "RS-IDLE")
        self.assertEqual(refusals[0]["code"], REFUSAL_NOT_EXECUTING)

    def test_a_second_abort_is_refused(self):
        refusals = abort_refusals(store(), "RS-STOPPED")
        self.assertEqual(refusals[0]["code"], REFUSAL_ALREADY_ABORTED)

    def test_a_completed_sequence_is_refused_with_its_own_code(self):
        refusals = abort_refusals(store(), "RS-DONE")
        self.assertEqual(refusals[0]["code"], REFUSAL_ALREADY_COMPLETED)

    def test_a_refusal_names_the_sequence(self):
        self.assertEqual(abort_refusals(store(), "RS-IDLE")[0]["sequence_id"], "RS-IDLE")


class TestApply(unittest.TestCase):
    def test_the_abort_marks_the_sequence_aborted(self):
        updated = apply_abort(store(), "RS-SLEW")
        self.assertEqual(updated[0]["execution_state"], "aborted")

    def test_the_pending_requests_are_discarded(self):
        updated = apply_abort(store(), "RS-SLEW")
        self.assertEqual(updated[0]["discarded_count"], 6)

    def test_the_released_count_is_not_rewound(self):
        updated = apply_abort(store(), "RS-SLEW")
        self.assertEqual(updated[0]["released_count"], 4)

    def test_the_body_stays_loaded_and_reactivatable(self):
        updated = apply_abort(store(), "RS-SLEW")
        self.assertEqual(updated[0]["load_state"], "loaded")
        self.assertTrue(updated[0]["reactivatable"])

    def test_the_other_sequences_are_untouched(self):
        updated = apply_abort(store(), "RS-SLEW")
        self.assertEqual(updated[1]["execution_state"], "inactive")

    def test_aborting_an_absent_sequence_raises(self):
        with self.assertRaises(ValueError):
            apply_abort(store(), "RS-GHOST")


class TestReport(unittest.TestCase):
    def test_the_report_names_the_step_reached(self):
        self.assertEqual(abort_report(store(), "RS-SLEW")["step_reached"], 4)

    def test_the_report_counts_what_was_discarded(self):
        self.assertEqual(abort_report(store(), "RS-SLEW")["discarded_count"], 6)

    def test_the_report_says_the_body_was_retained(self):
        self.assertTrue(abort_report(store(), "RS-SLEW")["body_retained"])

    def test_the_report_flags_requests_already_gone(self):
        self.assertTrue(
            abort_report(store(), "RS-SLEW")["released_requests_not_recalled"]
        )

    def test_an_abort_before_the_first_release_recalls_nothing(self):
        records = [sequence("RS-EARLY", released_count=0)]
        self.assertFalse(
            abort_report(records, "RS-EARLY")["released_requests_not_recalled"]
        )

    def test_reporting_on_an_absent_sequence_raises(self):
        with self.assertRaises(ValueError):
            abort_report(store(), "RS-GHOST")


class TestAssessment(unittest.TestCase):
    def test_an_executing_sequence_is_aborted(self):
        result = assess_abort(store(), "RS-SLEW")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], VERDICT_ABORTED)

    def test_an_accepted_abort_carries_its_report(self):
        result = assess_abort(store(), "RS-SLEW")
        self.assertEqual(result["report"]["sequence_id"], "RS-SLEW")

    def test_an_accepted_abort_warns_about_released_requests(self):
        result = assess_abort(store(), "RS-SLEW")
        self.assertTrue(any("recall" in text for text in result["findings"]))

    def test_an_abort_with_nothing_released_raises_no_recovery_finding(self):
        records = [sequence("RS-EARLY", released_count=0)]
        self.assertEqual(assess_abort(records, "RS-EARLY")["findings"], [])

    def test_a_refused_abort_leaves_the_store_unchanged(self):
        result = assess_abort(store(), "RS-IDLE")
        self.assertTrue(result["store_unchanged"])
        self.assertEqual(result["resulting_store"][1]["execution_state"], "inactive")

    def test_a_refused_abort_discards_nothing(self):
        self.assertEqual(assess_abort(store(), "RS-DONE")["discarded_count"], 0)

    def test_a_refused_abort_notifies_with_its_code(self):
        result = assess_abort(store(), "RS-STOPPED")
        self.assertEqual(result["verdict"], VERDICT_REFUSED)
        self.assertIn(REFUSAL_ALREADY_ABORTED, result["notification"]["codes"])

    def test_an_accepted_abort_raises_no_notification(self):
        self.assertIsNone(assess_abort(store(), "RS-SLEW")["notification"])

    def test_an_invalid_store_raises_before_any_decision(self):
        broken = store()
        broken[0]["released_count"] = 99
        with self.assertRaises(ValueError):
            assess_abort(broken, "RS-IDLE")


if __name__ == "__main__":
    unittest.main()
