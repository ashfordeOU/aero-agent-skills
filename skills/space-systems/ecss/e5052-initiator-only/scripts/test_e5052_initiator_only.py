"""Contract test for the RMAP initiator-only leaf (stdlib unittest)."""

import unittest

from e5052_initiator_only_logic import (
    ALL_CAPABILITIES,
    BITS_PER_CHARACTER,
    INITIATOR_DUTIES,
    ROLE_INITIATOR_AND_TARGET,
    ROLE_INITIATOR_ONLY,
    ROLE_TARGET_ONLY,
    TARGET_DUTIES,
    assess_initiator_only,
    grade_identifier_budget,
    grade_reply_timeout,
    identifier_space,
    missing_capabilities,
    out_of_scope_capabilities,
    owed_capabilities,
    round_trip_estimate_ms,
    surplus_capabilities,
    validate_profile,
)


def profile(**kw):
    record = {
        "role": ROLE_INITIATOR_ONLY,
        "capabilities": list(INITIATOR_DUTIES),
        "transaction_identifier_bits": 16,
        "max_outstanding_transactions": 8,
        "issues_acknowledged_commands": True,
    }
    record.update(kw)
    return record


class TestValidateProfile(unittest.TestCase):
    def test_normalised_capabilities_are_sorted_and_deduplicated(self):
        norm = validate_profile(profile(capabilities=[
            "reply-reception", "command-transmission", "reply-reception"]))
        self.assertEqual(norm["capabilities"], ["command-transmission", "reply-reception"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(["initiator-only"])

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(role="router-only"))

    def test_unknown_capability_token_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(capabilities=["packet-routing"]))

    def test_capability_string_instead_of_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(capabilities="command-transmission"))

    def test_negative_identifier_width_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(transaction_identifier_bits=-1))

    def test_boolean_identifier_width_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(transaction_identifier_bits=True))

    def test_zero_outstanding_transactions_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(max_outstanding_transactions=0))

    def test_non_boolean_acknowledged_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(issues_acknowledged_commands="yes"))

    def test_optional_timing_keys_are_carried_through(self):
        norm = validate_profile(profile(link_rate_mbit_s=10.0, command_bytes=32.0,
                                        reply_bytes=16.0, reply_timeout_ms=5.0))
        self.assertIn("link_rate_mbit_s", norm)
        self.assertIn("reply_timeout_ms", norm)


class TestRoleDuties(unittest.TestCase):
    def test_initiator_only_owes_the_initiator_duties(self):
        self.assertEqual(set(owed_capabilities(ROLE_INITIATOR_ONLY)), set(INITIATOR_DUTIES))

    def test_target_only_owes_the_target_duties(self):
        self.assertEqual(set(owed_capabilities(ROLE_TARGET_ONLY)), set(TARGET_DUTIES))

    def test_dual_role_owes_every_capability(self):
        self.assertEqual(set(owed_capabilities(ROLE_INITIATOR_AND_TARGET)),
                         set(ALL_CAPABILITIES))

    def test_dual_role_has_nothing_out_of_scope(self):
        self.assertEqual(out_of_scope_capabilities(ROLE_INITIATOR_AND_TARGET), ())

    def test_initiator_only_out_of_scope_is_the_target_side(self):
        self.assertEqual(set(out_of_scope_capabilities(ROLE_INITIATOR_ONLY)),
                         set(TARGET_DUTIES) - set(INITIATOR_DUTIES))

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            owed_capabilities("bridge")


class TestCapabilityGrading(unittest.TestCase):
    def test_complete_profile_has_no_missing_duties(self):
        self.assertEqual(missing_capabilities(profile()), ())

    def test_dropped_duty_is_reported(self):
        trimmed = [c for c in INITIATOR_DUTIES if c != "reply-reception"]
        self.assertIn("reply-reception", missing_capabilities(profile(capabilities=trimmed)))

    def test_target_duty_claim_is_surplus(self):
        claims = list(INITIATOR_DUTIES) + ["memory-access-execution"]
        self.assertEqual(surplus_capabilities(profile(capabilities=claims)),
                         ("memory-access-execution",))

    def test_clean_profile_has_no_surplus(self):
        self.assertEqual(surplus_capabilities(profile()), ())


class TestIdentifierBudget(unittest.TestCase):
    def test_identifier_space_is_a_power_of_two(self):
        self.assertEqual(identifier_space(16), 65536)

    def test_zero_width_separates_one_transaction(self):
        self.assertEqual(identifier_space(0), 1)

    def test_negative_width_raises(self):
        with self.assertRaises(ValueError):
            identifier_space(-4)

    def test_acknowledged_commands_need_a_non_zero_width(self):
        graded = grade_identifier_budget(profile(transaction_identifier_bits=0,
                                                 max_outstanding_transactions=1))
        self.assertTrue(graded["findings"])

    def test_outstanding_budget_beyond_the_identifier_space_is_flagged(self):
        graded = grade_identifier_budget(profile(transaction_identifier_bits=2,
                                                 max_outstanding_transactions=8))
        self.assertTrue(graded["findings"])

    def test_outstanding_budget_equal_to_the_space_is_accepted(self):
        graded = grade_identifier_budget(profile(transaction_identifier_bits=3,
                                                 max_outstanding_transactions=8))
        self.assertEqual(graded["findings"], [])

    def test_unacknowledged_commands_cannot_track_several_transactions(self):
        graded = grade_identifier_budget(profile(issues_acknowledged_commands=False,
                                                 max_outstanding_transactions=4))
        self.assertTrue(graded["findings"])


class TestRoundTrip(unittest.TestCase):
    def test_estimate_matches_the_hand_calculation(self):
        # 48 characters at ten bit times over a 10 Mbit/s link is 48 us.
        value = round_trip_estimate_ms(10.0, 32.0, 16.0, 0.0)
        self.assertAlmostEqual(value, 0.048, places=9)

    def test_turnaround_adds_directly(self):
        value = round_trip_estimate_ms(10.0, 32.0, 16.0, 0.25)
        self.assertAlmostEqual(value, 0.298, places=9)

    def test_zero_link_rate_raises(self):
        with self.assertRaises(ValueError):
            round_trip_estimate_ms(0.0, 32.0, 16.0)

    def test_negative_turnaround_raises(self):
        with self.assertRaises(ValueError):
            round_trip_estimate_ms(10.0, 32.0, 16.0, -1.0)

    def test_bit_times_per_character_is_ten(self):
        self.assertEqual(BITS_PER_CHARACTER, 10)


class TestReplyTimeout(unittest.TestCase):
    def test_timeout_is_not_graded_without_timing_data(self):
        graded = grade_reply_timeout(profile())
        self.assertFalse(graded["evaluated"])

    def test_generous_timeout_passes(self):
        graded = grade_reply_timeout(profile(link_rate_mbit_s=10.0, command_bytes=32.0,
                                             reply_bytes=16.0, reply_timeout_ms=1.0))
        self.assertTrue(graded["adequate"])
        self.assertEqual(graded["findings"], [])

    def test_short_timeout_is_flagged(self):
        graded = grade_reply_timeout(profile(link_rate_mbit_s=10.0, command_bytes=32.0,
                                             reply_bytes=16.0, reply_timeout_ms=0.001))
        self.assertFalse(graded["adequate"])
        self.assertTrue(graded["findings"])

    def test_timeout_exactly_at_the_estimate_is_accepted(self):
        estimate = round_trip_estimate_ms(10.0, 32.0, 16.0, 0.25)
        graded = grade_reply_timeout(profile(link_rate_mbit_s=10.0, command_bytes=32.0,
                                             reply_bytes=16.0, target_turnaround_ms=0.25,
                                             reply_timeout_ms=estimate))
        self.assertTrue(graded["adequate"])


class TestAssessInitiatorOnly(unittest.TestCase):
    def test_clean_profile_is_conformant(self):
        result = assess_initiator_only(profile())
        self.assertTrue(result["conformant"])
        self.assertEqual(result["findings"], [])

    def test_missing_duty_breaks_conformance(self):
        trimmed = [c for c in INITIATOR_DUTIES if c != "status-code-interpretation"]
        result = assess_initiator_only(profile(capabilities=trimmed))
        self.assertFalse(result["conformant"])
        self.assertIn("status-code-interpretation", result["missing_capabilities"])

    def test_target_claim_breaks_conformance(self):
        claims = list(INITIATOR_DUTIES) + ["reply-generation"]
        result = assess_initiator_only(profile(capabilities=claims))
        self.assertFalse(result["conformant"])
        self.assertIn("reply-generation", result["surplus_capabilities"])

    def test_other_role_is_reported_as_not_governed_by_this_clause(self):
        result = assess_initiator_only(profile(role=ROLE_INITIATOR_AND_TARGET,
                                               capabilities=list(ALL_CAPABILITIES)))
        self.assertFalse(result["conformant"])
        self.assertTrue(any("not the governing" in f for f in result["findings"]))

    def test_identifier_space_is_reported(self):
        result = assess_initiator_only(profile(transaction_identifier_bits=8))
        self.assertEqual(result["identifier_space"], 256)


if __name__ == "__main__":
    unittest.main()
