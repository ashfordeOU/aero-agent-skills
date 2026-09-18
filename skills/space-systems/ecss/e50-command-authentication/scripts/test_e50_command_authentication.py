#!/usr/bin/env python3
"""Gate 3 contract test for e50-command-authentication.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_command_authentication.py
"""

import unittest

from e50_command_authentication_logic import (
    ACCEPTED,
    ACCEPTED_UNAUTHENTICATED,
    COUNTER_OUT_OF_WINDOW,
    DEFAULT_TAG_OCTETS,
    KEY_NOT_VALID,
    MIN_TAG_OCTETS,
    MISSING_AUTHENTICATION,
    REPLAYED_COUNTER,
    TAG_MISMATCH,
    UNKNOWN_KEY,
    assess_command_authentication,
    authentication_required,
    counter_freshness,
    derive_tag,
    key_is_valid_for,
    validate_key,
    validate_octets,
    validate_tag_octets,
    verify_tag,
)

SECRET = bytes(range(32))
KEY = {
    "id": "uplink-key-2",
    "secret": SECRET,
    "valid_from_counter": 0,
    "valid_to_counter": 100000,
}
PROTECTED = ("pyro-fire", "tank-vent", "safe-mode-exit")
COMMAND = bytes((0x18, 0x0A, 0xC0, 0x00, 0x00, 0x05, 0x02, 0x01))


class TestValidation(unittest.TestCase):
    def test_bytes_are_accepted_as_octets(self):
        self.assertEqual(validate_octets([1, 2, 3]), b"\x01\x02\x03")

    def test_an_out_of_range_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets([1, 256])

    def test_text_is_not_octets(self):
        with self.assertRaises(ValueError):
            validate_octets("0102")

    def test_a_short_secret_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_key(dict(KEY, secret=b"\x01\x02"))

    def test_an_inverted_validity_range_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_key(dict(KEY, valid_from_counter=50, valid_to_counter=10))

    def test_a_missing_key_field_is_rejected(self):
        broken = dict(KEY)
        del broken["valid_to_counter"]
        with self.assertRaises(ValueError):
            validate_key(broken)

    def test_a_tag_shorter_than_the_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tag_octets(MIN_TAG_OCTETS - 1)

    def test_a_tag_wider_than_the_digest_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tag_octets(64, "sha256")

    def test_the_default_tag_width_is_accepted(self):
        self.assertEqual(validate_tag_octets(), DEFAULT_TAG_OCTETS)


class TestKeyValidity(unittest.TestCase):
    def test_a_counter_inside_the_validity_range_is_allowed(self):
        self.assertTrue(key_is_valid_for(KEY, 500))

    def test_a_counter_on_the_lower_bound_is_allowed(self):
        self.assertTrue(key_is_valid_for(KEY, 0))

    def test_a_counter_past_the_upper_bound_is_refused(self):
        self.assertFalse(key_is_valid_for(KEY, 100001))

    def test_a_negative_counter_is_rejected(self):
        with self.assertRaises(ValueError):
            key_is_valid_for(KEY, -1)


class TestFreshness(unittest.TestCase):
    def test_the_next_counter_is_fresh(self):
        self.assertEqual(counter_freshness(11, 10), ACCEPTED)

    def test_a_repeated_counter_is_a_replay(self):
        self.assertEqual(counter_freshness(10, 10), REPLAYED_COUNTER)

    def test_an_older_counter_is_a_replay(self):
        self.assertEqual(counter_freshness(4, 10), REPLAYED_COUNTER)

    def test_a_counter_on_the_window_edge_is_still_fresh(self):
        self.assertEqual(counter_freshness(42, 10, window=32), ACCEPTED)

    def test_a_counter_past_the_window_is_refused(self):
        self.assertEqual(counter_freshness(43, 10, window=32), COUNTER_OUT_OF_WINDOW)

    def test_a_zero_window_is_rejected(self):
        with self.assertRaises(ValueError):
            counter_freshness(11, 10, window=0)


class TestTags(unittest.TestCase):
    def test_the_tag_is_the_requested_width(self):
        self.assertEqual(len(derive_tag(KEY, 7, COMMAND)), DEFAULT_TAG_OCTETS)

    def test_the_tag_is_stable_for_the_same_inputs(self):
        self.assertEqual(derive_tag(KEY, 7, COMMAND), derive_tag(KEY, 7, COMMAND))

    def test_a_different_counter_gives_a_different_tag(self):
        self.assertNotEqual(derive_tag(KEY, 7, COMMAND), derive_tag(KEY, 8, COMMAND))

    def test_a_changed_command_octet_gives_a_different_tag(self):
        altered = bytearray(COMMAND)
        altered[-1] ^= 0x01
        self.assertNotEqual(derive_tag(KEY, 7, COMMAND), derive_tag(KEY, 7, bytes(altered)))

    def test_a_different_key_gives_a_different_tag(self):
        other = dict(KEY, id="uplink-key-3", secret=bytes(range(1, 33)))
        self.assertNotEqual(derive_tag(KEY, 7, COMMAND), derive_tag(other, 7, COMMAND))

    def test_a_correct_tag_verifies(self):
        tag = derive_tag(KEY, 7, COMMAND)
        self.assertTrue(verify_tag(KEY, 7, COMMAND, tag))

    def test_a_truncated_tag_does_not_verify(self):
        tag = derive_tag(KEY, 7, COMMAND)[:-1]
        self.assertFalse(verify_tag(KEY, 7, COMMAND, tag))

    def test_a_tag_from_another_counter_does_not_verify(self):
        self.assertFalse(verify_tag(KEY, 7, COMMAND, derive_tag(KEY, 8, COMMAND)))


class TestPolicy(unittest.TestCase):
    def test_a_protected_command_needs_authentication(self):
        self.assertTrue(authentication_required("pyro-fire", PROTECTED))

    def test_an_ordinary_command_does_not(self):
        self.assertFalse(authentication_required("report-housekeeping", PROTECTED))

    def test_a_blank_command_name_is_rejected(self):
        with self.assertRaises(ValueError):
            authentication_required("   ", PROTECTED)

    def test_a_string_in_place_of_a_policy_list_is_rejected(self):
        with self.assertRaises(ValueError):
            authentication_required("pyro-fire", "pyro-fire")


class TestAssessment(unittest.TestCase):
    def test_a_correctly_authenticated_protected_command_is_acted_on(self):
        report = assess_command_authentication(
            "pyro-fire",
            COMMAND,
            PROTECTED,
            key=KEY,
            counter=11,
            carried_tag=derive_tag(KEY, 11, COMMAND),
            last_accepted_counter=10,
        )
        self.assertEqual(report["outcome"], ACCEPTED)
        self.assertTrue(report["act_on_command"])
        self.assertEqual(report["next_last_accepted_counter"], 11)

    def test_a_protected_command_with_no_tag_is_refused(self):
        report = assess_command_authentication("pyro-fire", COMMAND, PROTECTED)
        self.assertEqual(report["outcome"], MISSING_AUTHENTICATION)
        self.assertFalse(report["act_on_command"])

    def test_an_ordinary_command_with_no_tag_is_still_acted_on(self):
        report = assess_command_authentication(
            "report-housekeeping", COMMAND, PROTECTED
        )
        self.assertEqual(report["outcome"], ACCEPTED_UNAUTHENTICATED)
        self.assertTrue(report["act_on_command"])

    def test_a_replayed_command_is_refused_even_with_a_valid_tag(self):
        report = assess_command_authentication(
            "pyro-fire",
            COMMAND,
            PROTECTED,
            key=KEY,
            counter=10,
            carried_tag=derive_tag(KEY, 10, COMMAND),
            last_accepted_counter=10,
        )
        self.assertEqual(report["outcome"], REPLAYED_COUNTER)
        self.assertEqual(report["next_last_accepted_counter"], 10)

    def test_a_wrong_tag_is_refused_as_a_mismatch(self):
        report = assess_command_authentication(
            "pyro-fire",
            COMMAND,
            PROTECTED,
            key=KEY,
            counter=11,
            carried_tag=derive_tag(KEY, 12, COMMAND),
            last_accepted_counter=10,
        )
        self.assertEqual(report["outcome"], TAG_MISMATCH)

    def test_an_expired_key_is_refused_before_the_tag_is_compared(self):
        expiring = dict(KEY, valid_to_counter=10)
        report = assess_command_authentication(
            "pyro-fire",
            COMMAND,
            PROTECTED,
            key=expiring,
            counter=11,
            carried_tag=derive_tag(expiring, 11, COMMAND),
            last_accepted_counter=10,
        )
        self.assertEqual(report["outcome"], KEY_NOT_VALID)

    def test_a_tag_with_no_key_is_refused_as_unknown(self):
        report = assess_command_authentication(
            "pyro-fire",
            COMMAND,
            PROTECTED,
            carried_tag=derive_tag(KEY, 11, COMMAND),
            counter=11,
            last_accepted_counter=10,
        )
        self.assertEqual(report["outcome"], UNKNOWN_KEY)
        self.assertIsNone(report["key_id"])

    def test_a_counter_far_ahead_is_refused_as_out_of_window(self):
        report = assess_command_authentication(
            "pyro-fire",
            COMMAND,
            PROTECTED,
            key=KEY,
            counter=900,
            carried_tag=derive_tag(KEY, 900, COMMAND),
            last_accepted_counter=10,
            window=32,
        )
        self.assertEqual(report["outcome"], COUNTER_OUT_OF_WINDOW)

    def test_an_authenticated_command_without_a_counter_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_command_authentication(
                "pyro-fire",
                COMMAND,
                PROTECTED,
                key=KEY,
                carried_tag=derive_tag(KEY, 11, COMMAND),
            )

    def test_an_authenticated_ordinary_command_records_the_key(self):
        report = assess_command_authentication(
            "report-housekeeping",
            COMMAND,
            PROTECTED,
            key=KEY,
            counter=11,
            carried_tag=derive_tag(KEY, 11, COMMAND),
            last_accepted_counter=10,
        )
        self.assertEqual(report["outcome"], ACCEPTED)
        self.assertEqual(report["key_id"], "uplink-key-2")


if __name__ == "__main__":
    unittest.main()
