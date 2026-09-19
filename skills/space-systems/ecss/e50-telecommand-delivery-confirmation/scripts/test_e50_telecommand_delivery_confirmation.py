"""Contract tests for the clause 5.7.2.7 delivery confirmation logic."""

import unittest

from e50_telecommand_delivery_confirmation_logic import (
    CONFIRMED,
    LATE,
    UNCONFIRMED,
    assess_delivery_confirmation,
    confirmation_deadline,
    match_confirmations,
    normalise_command,
    normalise_confirmation,
    validate_bound,
    validate_identifier,
    validate_time,
)

TRANSIT = 0.2
CONFIRM_BOUND = 0.3
COMMANDS = [
    {"id": "tc-1", "dispatch_s": 100.0, "destination": "aocs"},
    {"id": "tc-2", "dispatch_s": 101.0, "destination": "power"},
    {"id": "tc-3", "dispatch_s": 102.0, "destination": "payload"},
]
ALL_GOOD = [
    {"command_id": "tc-1", "time_s": 100.3},
    {"command_id": "tc-2", "time_s": 101.1},
    {"command_id": "tc-3", "time_s": 102.4},
]


def normalised(commands):
    return [normalise_command(c) for c in commands]


def normalised_confirmations(confirmations):
    return [normalise_confirmation(c) for c in confirmations]


class ValidationTests(unittest.TestCase):
    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(1)

    def test_identifier_is_trimmed(self):
        self.assertEqual(validate_identifier(" tc-1 "), "tc-1")

    def test_a_negative_epoch_is_allowed(self):
        self.assertAlmostEqual(validate_time(-5.0), -5.0, places=9)

    def test_boolean_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(True)

    def test_infinite_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(float("inf"))

    def test_negative_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_bound(-0.1)

    def test_zero_bound_accepted(self):
        self.assertAlmostEqual(validate_bound(0.0), 0.0, places=9)

    def test_non_mapping_command_rejected(self):
        with self.assertRaises(ValueError):
            normalise_command(["tc-1", 100.0])

    def test_command_destination_defaults(self):
        self.assertEqual(
            normalise_command({"id": "tc-1", "dispatch_s": 1.0})["destination"],
            "unspecified",
        )

    def test_non_mapping_confirmation_rejected(self):
        with self.assertRaises(ValueError):
            normalise_confirmation("tc-1")

    def test_duplicate_command_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_confirmation(
                COMMANDS + [dict(COMMANDS[0])], ALL_GOOD, TRANSIT, CONFIRM_BOUND
            )

    def test_empty_dispatch_log_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_confirmation([], ALL_GOOD, TRANSIT, CONFIRM_BOUND)

    def test_non_list_confirmations_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_confirmation(COMMANDS, ALL_GOOD[0], TRANSIT, CONFIRM_BOUND)


class DeadlineTests(unittest.TestCase):
    def test_deadline_is_dispatch_plus_both_bounds(self):
        self.assertAlmostEqual(
            confirmation_deadline(100.0, TRANSIT, CONFIRM_BOUND), 100.5, places=9
        )

    def test_zero_bounds_make_the_deadline_the_dispatch_time(self):
        self.assertAlmostEqual(confirmation_deadline(100.0, 0.0, 0.0), 100.0, places=9)

    def test_a_negative_transit_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_deadline(100.0, -0.1, CONFIRM_BOUND)


class MatchingTests(unittest.TestCase):
    def test_each_confirmation_finds_its_command(self):
        earliest, strays, duplicates = match_confirmations(
            normalised(COMMANDS), normalised_confirmations(ALL_GOOD)
        )
        self.assertEqual(sorted(earliest), ["tc-1", "tc-2", "tc-3"])
        self.assertEqual(strays, [])
        self.assertEqual(duplicates, [])

    def test_a_confirmation_for_nothing_is_a_stray(self):
        log = ALL_GOOD + [{"command_id": "tc-9", "time_s": 110.0}]
        _, strays, _ = match_confirmations(
            normalised(COMMANDS), normalised_confirmations(log)
        )
        self.assertEqual([s["command_id"] for s in strays], ["tc-9"])

    def test_a_second_confirmation_is_a_duplicate(self):
        log = ALL_GOOD + [{"command_id": "tc-1", "time_s": 100.9}]
        _, _, duplicates = match_confirmations(
            normalised(COMMANDS), normalised_confirmations(log)
        )
        self.assertEqual([d["command_id"] for d in duplicates], ["tc-1"])

    def test_the_earliest_confirmation_is_the_one_kept(self):
        log = [
            {"command_id": "tc-1", "time_s": 100.9},
            {"command_id": "tc-1", "time_s": 100.3},
        ]
        earliest, _, duplicates = match_confirmations(
            normalised(COMMANDS), normalised_confirmations(log)
        )
        self.assertAlmostEqual(earliest["tc-1"]["time_s"], 100.3, places=9)
        self.assertAlmostEqual(duplicates[0]["time_s"], 100.9, places=9)

    def test_a_confirmation_before_its_dispatch_is_refused(self):
        log = [{"command_id": "tc-1", "time_s": 99.0}]
        with self.assertRaises(ValueError):
            match_confirmations(normalised(COMMANDS), normalised_confirmations(log))


class AssessmentTests(unittest.TestCase):
    def test_a_clean_log_is_compliant(self):
        result = assess_delivery_confirmation(COMMANDS, ALL_GOOD, TRANSIT, CONFIRM_BOUND)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_confirmation_is_unconfirmed(self):
        result = assess_delivery_confirmation(
            COMMANDS, ALL_GOOD[:2], TRANSIT, CONFIRM_BOUND
        )
        self.assertEqual(result["unconfirmed"], ["tc-3"])
        self.assertFalse(result["service_confirmed"])

    def test_an_unconfirmed_command_carries_no_latency(self):
        result = assess_delivery_confirmation(
            COMMANDS, ALL_GOOD[:2], TRANSIT, CONFIRM_BOUND
        )
        last = result["per_command"][-1]
        self.assertEqual(last["verdict"], UNCONFIRMED)
        self.assertIsNone(last["latency_s"])

    def test_a_confirmation_past_the_deadline_is_late(self):
        log = list(ALL_GOOD)
        log[1] = {"command_id": "tc-2", "time_s": 105.0}
        result = assess_delivery_confirmation(COMMANDS, log, TRANSIT, CONFIRM_BOUND)
        self.assertEqual(result["late"], ["tc-2"])

    def test_a_confirmation_exactly_on_the_deadline_is_confirmed(self):
        log = [{"command_id": "tc-1", "time_s": 100.5}]
        result = assess_delivery_confirmation(
            COMMANDS[:1], log, TRANSIT, CONFIRM_BOUND
        )
        self.assertAlmostEqual(
            result["per_command"][0]["confirmed_at_s"],
            result["per_command"][0]["deadline_s"],
            places=9,
        )
        self.assertEqual(result["per_command"][0]["verdict"], CONFIRMED)

    def test_a_stray_breaks_the_log_even_when_every_command_is_confirmed(self):
        log = ALL_GOOD + [{"command_id": "tc-9", "time_s": 110.0}]
        result = assess_delivery_confirmation(COMMANDS, log, TRANSIT, CONFIRM_BOUND)
        self.assertTrue(result["service_confirmed"])
        self.assertFalse(result["log_clean"])
        self.assertFalse(result["compliant"])

    def test_a_duplicate_is_named_in_the_findings(self):
        log = ALL_GOOD + [{"command_id": "tc-1", "time_s": 100.4}]
        result = assess_delivery_confirmation(COMMANDS, log, TRANSIT, CONFIRM_BOUND)
        self.assertTrue(any("more than one confirmation" in f for f in result["findings"]))

    def test_latency_is_measured_from_dispatch(self):
        result = assess_delivery_confirmation(COMMANDS, ALL_GOOD, TRANSIT, CONFIRM_BOUND)
        self.assertAlmostEqual(result["per_command"][0]["latency_s"], 0.3, places=9)

    def test_margin_is_reported(self):
        result = assess_delivery_confirmation(COMMANDS, ALL_GOOD, TRANSIT, CONFIRM_BOUND)
        self.assertAlmostEqual(result["per_command"][0]["margin_s"], 0.2, places=9)

    def test_worst_observed_latency_is_the_bound_that_would_have_held(self):
        result = assess_delivery_confirmation(COMMANDS, ALL_GOOD, TRANSIT, CONFIRM_BOUND)
        self.assertAlmostEqual(result["worst_observed_latency_s"], 0.4, places=9)

    def test_a_log_with_no_confirmations_reports_no_observed_latency(self):
        result = assess_delivery_confirmation(COMMANDS, [], TRANSIT, CONFIRM_BOUND)
        self.assertIsNone(result["worst_observed_latency_s"])
        self.assertAlmostEqual(result["confirmation_ratio"], 0.0, places=9)

    def test_the_confirmation_ratio_counts_the_dispatch_log(self):
        result = assess_delivery_confirmation(
            COMMANDS, ALL_GOOD[:2], TRANSIT, CONFIRM_BOUND
        )
        self.assertAlmostEqual(result["confirmation_ratio"], 2.0 / 3.0, places=9)

    def test_widening_the_bound_turns_late_into_confirmed(self):
        log = list(ALL_GOOD)
        log[1] = {"command_id": "tc-2", "time_s": 105.0}
        tight = assess_delivery_confirmation(COMMANDS, log, TRANSIT, CONFIRM_BOUND)
        wide = assess_delivery_confirmation(COMMANDS, log, TRANSIT, 4.0)
        self.assertEqual(tight["late"], ["tc-2"])
        self.assertEqual(wide["late"], [])

    def test_the_worst_observed_latency_would_have_confirmed_everything(self):
        log = list(ALL_GOOD)
        log[1] = {"command_id": "tc-2", "time_s": 105.0}
        first = assess_delivery_confirmation(COMMANDS, log, TRANSIT, CONFIRM_BOUND)
        widened = assess_delivery_confirmation(
            COMMANDS, log, 0.0, first["worst_observed_latency_s"]
        )
        self.assertEqual(widened["late"], [])

    def test_a_bad_confirmation_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_confirmation(COMMANDS, ALL_GOOD, TRANSIT, -1.0)

    def test_the_destination_is_carried_through_to_the_report(self):
        result = assess_delivery_confirmation(COMMANDS, ALL_GOOD, TRANSIT, CONFIRM_BOUND)
        self.assertEqual(result["per_command"][0]["destination"], "aocs")


if __name__ == "__main__":
    unittest.main()
