"""Contract tests for the clause 5.6.2 failed-qualification-coupon treatment."""

import unittest

from e2008_failed_qualification_coupons_logic import (
    CAUSE_CATEGORIES,
    FAILURE_MODES,
    RETEST_SCOPES,
    UNDETERMINED_CAUSE,
    assess_failed_coupon,
    governing_failure,
    normalize_cause,
    normalize_mode,
    qualification_status_for_scope,
    retest_scope_for_cause,
    scope_rank,
    validate_corrective_action,
    validate_failure_record,
    widest_scope,
)

DONE = {"implemented": True, "verified": True}
STARTED = {"implemented": True, "verified": False}
NOT_STARTED = {"implemented": False, "verified": False}


def _failure(mode="interconnect-fracture", cause="isolated-build-escape"):
    return {"mode": mode, "cause": cause}


class ModeAndCauseTests(unittest.TestCase):
    def test_recognized_mode_is_returned(self):
        self.assertEqual(normalize_mode("open-circuit"), "open-circuit")

    def test_case_and_space_are_absorbed_in_a_mode(self):
        self.assertEqual(normalize_mode(" Cell-Cracking "), "cell-cracking")

    def test_unrecognized_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode("looked-wrong")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode(None)

    def test_recognized_cause_is_returned(self):
        self.assertEqual(
            normalize_cause("design-inherent-cause"), "design-inherent-cause"
        )

    def test_unrecognized_cause_rejected(self):
        with self.assertRaises(ValueError):
            normalize_cause("bad-luck")

    def test_undetermined_is_a_recognized_cause(self):
        self.assertIn(UNDETERMINED_CAUSE, CAUSE_CATEGORIES)

    def test_catalogue_covers_the_listed_modes(self):
        self.assertGreaterEqual(len(FAILURE_MODES), 8)


class ScopeTests(unittest.TestCase):
    def test_scopes_are_ordered_narrowest_first(self):
        ranks = [scope_rank(scope) for scope in RETEST_SCOPES]
        self.assertEqual(ranks, sorted(ranks))

    def test_test_installation_artefact_repeats_only_the_coupon(self):
        self.assertEqual(
            retest_scope_for_cause("test-installation-artefact"),
            "repeat-affected-coupon",
        )

    def test_isolated_build_escape_repeats_the_subgroup(self):
        self.assertEqual(
            retest_scope_for_cause("isolated-build-escape"), "repeat-affected-subgroup"
        )

    def test_systematic_process_cause_reaches_the_whole_qualification(self):
        self.assertEqual(
            retest_scope_for_cause("systematic-process-cause"),
            "requalify-full-programme",
        )

    def test_design_inherent_cause_reaches_the_whole_qualification(self):
        self.assertEqual(
            retest_scope_for_cause("design-inherent-cause"), "requalify-full-programme"
        )

    def test_undetermined_cause_forces_no_scope(self):
        with self.assertRaises(ValueError):
            retest_scope_for_cause(UNDETERMINED_CAUSE)

    def test_unrecognized_scope_rejected(self):
        with self.assertRaises(ValueError):
            scope_rank("repeat-a-bit")

    def test_widest_scope_governs_a_mixed_set(self):
        self.assertEqual(
            widest_scope(["repeat-affected-coupon", "requalify-full-programme"]),
            "requalify-full-programme",
        )

    def test_widest_scope_of_one_is_that_scope(self):
        self.assertEqual(widest_scope(["repeat-affected-coupon"]),
                         "repeat-affected-coupon")

    def test_empty_scope_set_rejected(self):
        with self.assertRaises(ValueError):
            widest_scope([])

    def test_full_requalification_voids_the_qualification(self):
        self.assertEqual(
            qualification_status_for_scope("requalify-full-programme"),
            "qualification-invalidated",
        )

    def test_coupon_repeat_voids_only_the_coupon_result(self):
        self.assertEqual(
            qualification_status_for_scope("repeat-affected-coupon"),
            "coupon-result-void",
        )


class RecordValidationTests(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        record = validate_failure_record(_failure(mode=" Open-Circuit "))
        self.assertEqual(record["mode"], "open-circuit")

    def test_evidence_reference_is_kept(self):
        record = _failure()
        record["evidence"] = " NCR-118 "
        self.assertEqual(validate_failure_record(record)["evidence"], "NCR-118")

    def test_missing_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record({"cause": "isolated-build-escape"})

    def test_missing_cause_rejected_rather_than_defaulted(self):
        with self.assertRaises(ValueError):
            validate_failure_record({"mode": "open-circuit"})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_failure_record(["open-circuit"])

    def test_blank_evidence_reference_rejected(self):
        record = _failure()
        record["evidence"] = "  "
        with self.assertRaises(ValueError):
            validate_failure_record(record)

    def test_governing_failure_picks_the_widest_cause(self):
        governing = governing_failure([
            _failure("cell-cracking", "test-installation-artefact"),
            _failure("short-circuit", "design-inherent-cause"),
        ])
        self.assertEqual(governing["mode"], "short-circuit")

    def test_governing_failure_needs_one_attributed_cause(self):
        with self.assertRaises(ValueError):
            governing_failure([_failure("open-circuit", UNDETERMINED_CAUSE)])


class CorrectiveActionTests(unittest.TestCase):
    def test_absent_action_is_neither_implemented_nor_verified(self):
        state = validate_corrective_action(None)
        self.assertFalse(state["implemented"])
        self.assertFalse(state["verified"])

    def test_complete_action_is_kept(self):
        self.assertTrue(validate_corrective_action(DONE)["verified"])

    def test_missing_flag_rejected_rather_than_defaulted(self):
        with self.assertRaises(ValueError):
            validate_corrective_action({"implemented": True})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrective_action({"implemented": 1, "verified": 0})

    def test_verified_without_implemented_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrective_action({"implemented": False, "verified": True})

    def test_non_mapping_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_corrective_action("done")


class DispositionTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "coupon_id": "q-07",
            "failures": [_failure()],
            "corrective_action": dict(DONE),
        }
        spec.update(overrides)
        return spec

    def test_evidence_is_withdrawn_whatever_the_cause(self):
        result = assess_failed_coupon(self._spec())
        self.assertTrue(result["qualification_evidence_withdrawn"])

    def test_evidence_is_withdrawn_before_the_investigation_closes(self):
        result = assess_failed_coupon(
            self._spec(failures=[_failure(cause=UNDETERMINED_CAUSE)])
        )
        self.assertTrue(result["qualification_evidence_withdrawn"])

    def test_unattributed_cause_holds_the_disposition_open(self):
        result = assess_failed_coupon(
            self._spec(failures=[_failure(cause=UNDETERMINED_CAUSE)])
        )
        self.assertEqual(result["disposition"], "investigation-open")
        self.assertEqual(result["retest_scope"], "none")
        self.assertFalse(result["retest_authorized"])

    def test_one_unattributed_mode_among_several_holds_the_disposition(self):
        failures = [
            _failure("cell-cracking", "design-inherent-cause"),
            _failure("open-circuit", UNDETERMINED_CAUSE),
        ]
        result = assess_failed_coupon(self._spec(failures=failures))
        self.assertEqual(result["disposition"], "investigation-open")
        self.assertEqual(result["unattributed_modes"], ("open-circuit",))

    def test_attributed_cause_with_a_closed_action_authorizes_the_retest(self):
        result = assess_failed_coupon(self._spec())
        self.assertEqual(result["disposition"], "retest-authorized")
        self.assertEqual(result["findings"], [])

    def test_unimplemented_corrective_action_blocks_the_retest(self):
        result = assess_failed_coupon(
            self._spec(corrective_action=dict(NOT_STARTED))
        )
        self.assertEqual(result["disposition"], "retest-blocked")
        self.assertIn("not implemented", result["findings"][0])

    def test_unverified_corrective_action_blocks_the_retest(self):
        result = assess_failed_coupon(self._spec(corrective_action=dict(STARTED)))
        self.assertEqual(result["disposition"], "retest-blocked")
        self.assertIn("unverified", result["findings"][0])

    def test_widest_cause_governs_the_retest_scope(self):
        failures = [
            _failure("cell-cracking", "test-installation-artefact"),
            _failure("short-circuit", "systematic-process-cause"),
        ]
        result = assess_failed_coupon(self._spec(failures=failures))
        self.assertEqual(result["retest_scope"], "requalify-full-programme")
        self.assertEqual(result["governing_mode"], "short-circuit")

    def test_design_cause_invalidates_the_qualification(self):
        result = assess_failed_coupon(
            self._spec(failures=[_failure(cause="design-inherent-cause")])
        )
        self.assertEqual(result["qualification_status"], "qualification-invalidated")

    def test_test_installation_artefact_keeps_the_scope_on_the_coupon(self):
        result = assess_failed_coupon(
            self._spec(failures=[_failure(cause="test-installation-artefact")])
        )
        self.assertEqual(result["retest_scope"], "repeat-affected-coupon")
        self.assertEqual(result["qualification_status"], "coupon-result-void")

    def test_every_failure_mode_is_counted(self):
        failures = [_failure("cell-cracking"), _failure("open-circuit")]
        self.assertEqual(
            assess_failed_coupon(self._spec(failures=failures))["failure_mode_count"], 2
        )

    def test_empty_failure_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_coupon(self._spec(failures=[]))

    def test_duplicate_failure_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_coupon(
                self._spec(failures=[_failure("open-circuit"), _failure("open-circuit")])
            )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["failures"]
        with self.assertRaises(ValueError):
            assess_failed_coupon(spec)

    def test_blank_coupon_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_coupon(self._spec(coupon_id="   "))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_failed_coupon(["q-07"])

    def test_absent_corrective_action_blocks_the_retest(self):
        spec = self._spec()
        del spec["corrective_action"]
        self.assertEqual(assess_failed_coupon(spec)["disposition"], "retest-blocked")


if __name__ == "__main__":
    unittest.main()
