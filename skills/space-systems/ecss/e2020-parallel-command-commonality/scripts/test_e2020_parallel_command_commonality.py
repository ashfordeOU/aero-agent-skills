"""Contract tests for the clause 5.2.12.4.1 parallel command commonality logic."""

import unittest

from e2020_parallel_command_commonality_logic import (
    BINDING_SHARED,
    BINDING_SPLIT,
    BINDING_UNBOUND,
    COMMAND_LINES,
    COMMONALITY_HELD,
    COMMONALITY_SKEWED,
    COMMONALITY_SPLIT,
    COMMONALITY_UNBOUND,
    DEFAULT_COMMAND_POLICY,
    OFF_COMMAND,
    ON_COMMAND,
    assess_parallel_command_commonality,
    categorize_command_line,
    command_skew_us,
    line_binding,
    normalize_member,
    normalize_members,
    validate_command_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_COMMAND_POLICY)
    policy.update(overrides)
    return policy


def _member(identifier, on="grp-on-1", off="grp-off-1", delay=10.0):
    return {
        "id": identifier,
        ON_COMMAND: on,
        OFF_COMMAND: off,
        "propagation_delay_us": delay,
    }


def _group(**overrides):
    group = {
        "members": [
            _member("lcl-a", delay=10.0),
            _member("lcl-b", delay=14.0),
            _member("lcl-c", delay=12.0),
        ]
    }
    group.update(overrides)
    return group


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_command_policy(DEFAULT_COMMAND_POLICY),
            DEFAULT_COMMAND_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_policy("shared")

    def test_a_group_minimum_below_two_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_policy(_policy(min_group_members=1))

    def test_a_fanout_below_the_group_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_policy(_policy(min_group_members=4, max_line_fanout=3))

    def test_a_zero_skew_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_policy(_policy(max_command_skew_us=0.0))

    def test_a_float_member_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_command_policy(_policy(min_group_members=2.5))


class VocabularyTests(unittest.TestCase):
    def test_both_command_lines_round_trip(self):
        for line in COMMAND_LINES:
            self.assertEqual(categorize_command_line(line), line)

    def test_a_padded_command_line_is_accepted(self):
        self.assertEqual(categorize_command_line("  off-command "), OFF_COMMAND)

    def test_an_unrecognised_command_line_rejected(self):
        with self.assertRaises(ValueError):
            categorize_command_line("reset-command")

    def test_an_empty_command_line_rejected(self):
        with self.assertRaises(ValueError):
            categorize_command_line("   ")


class MemberTests(unittest.TestCase):
    def test_a_member_keeps_both_sources_and_its_delay(self):
        member = normalize_member(_member("lcl-a", delay=7.5))
        self.assertEqual(member["id"], "lcl-a")
        self.assertEqual(member["sources"][ON_COMMAND], "grp-on-1")
        self.assertAlmostEqual(member["propagation_delay_us"], 7.5, places=9)

    def test_a_missing_source_reads_as_unbound_not_as_zero(self):
        member = normalize_member(_member("lcl-a", off=None))
        self.assertIsNone(member["sources"][OFF_COMMAND])

    def test_a_member_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member({ON_COMMAND: "grp-on-1"})

    def test_a_negative_propagation_delay_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member(_member("lcl-a", delay=-1.0))

    def test_a_non_mapping_member_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member("lcl-a")

    def test_a_missing_delay_defaults_to_zero(self):
        member = normalize_member({"id": "lcl-a", ON_COMMAND: "x", OFF_COMMAND: "y"})
        self.assertAlmostEqual(member["propagation_delay_us"], 0.0, places=9)

    def test_a_single_limiter_is_not_a_parallel_group(self):
        with self.assertRaises(ValueError):
            normalize_members([_member("lcl-a")])

    def test_a_duplicate_member_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_members([_member("lcl-a"), _member("lcl-a")])

    def test_a_group_wider_than_the_line_fanout_rejected(self):
        members = [_member("lcl-%d" % index) for index in range(9)]
        with self.assertRaises(ValueError):
            normalize_members(members)

    def test_a_non_sequence_member_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_members({"id": "lcl-a"})


class BindingTests(unittest.TestCase):
    def test_one_source_across_the_group_is_shared(self):
        members = normalize_members(_group()["members"])
        binding = line_binding(members, ON_COMMAND)
        self.assertEqual(binding["state"], BINDING_SHARED)
        self.assertEqual(binding["shared_source"], "grp-on-1")

    def test_two_sources_across_the_group_are_split(self):
        members = normalize_members(
            [_member("lcl-a"), _member("lcl-b", on="own-on-2")]
        )
        binding = line_binding(members, ON_COMMAND)
        self.assertEqual(binding["state"], BINDING_SPLIT)
        self.assertEqual(binding["distinct_sources"], ("grp-on-1", "own-on-2"))
        self.assertIsNone(binding["shared_source"])

    def test_a_member_naming_no_source_makes_the_line_unbound(self):
        members = normalize_members(
            [_member("lcl-a"), _member("lcl-b", off=None)]
        )
        binding = line_binding(members, OFF_COMMAND)
        self.assertEqual(binding["state"], BINDING_UNBOUND)
        self.assertEqual(binding["unbound_members"], ("lcl-b",))

    def test_an_unbound_member_outranks_a_split_on_the_same_line(self):
        members = normalize_members(
            [_member("lcl-a"), _member("lcl-b", on="own-on-2"), _member("lcl-c", on=None)]
        )
        binding = line_binding(members, ON_COMMAND)
        self.assertEqual(binding["state"], BINDING_UNBOUND)

    def test_the_two_lines_are_graded_apart(self):
        members = normalize_members(
            [_member("lcl-a"), _member("lcl-b", off="own-off-2")]
        )
        self.assertEqual(line_binding(members, ON_COMMAND)["state"], BINDING_SHARED)
        self.assertEqual(line_binding(members, OFF_COMMAND)["state"], BINDING_SPLIT)

    def test_an_empty_group_rejected_by_the_binding(self):
        with self.assertRaises(ValueError):
            line_binding([], ON_COMMAND)

    def test_a_raw_member_that_was_never_normalized_rejected(self):
        with self.assertRaises(ValueError):
            line_binding([_member("lcl-a")], ON_COMMAND)


class SkewTests(unittest.TestCase):
    def test_skew_is_the_spread_not_the_largest_delay(self):
        members = normalize_members(_group()["members"])
        self.assertAlmostEqual(command_skew_us(members), 4.0, places=9)

    def test_identical_delays_give_no_skew(self):
        members = normalize_members(
            [_member("lcl-a", delay=9.0), _member("lcl-b", delay=9.0)]
        )
        self.assertAlmostEqual(command_skew_us(members), 0.0, places=9)

    def test_an_empty_group_has_no_skew_to_report(self):
        with self.assertRaises(ValueError):
            command_skew_us([])

    def test_a_negative_delay_rejected_by_the_skew(self):
        with self.assertRaises(ValueError):
            command_skew_us([{"propagation_delay_us": -2.0}])


class GroupAssessmentTests(unittest.TestCase):
    def test_a_shared_and_prompt_group_holds_commonality(self):
        result = assess_parallel_command_commonality(_group())
        self.assertEqual(result["verdict"], COMMONALITY_HELD)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["skew_within_budget"])

    def test_a_split_off_line_alone_fails_the_group(self):
        result = assess_parallel_command_commonality(
            _group(members=[_member("lcl-a"), _member("lcl-b", off="own-off-2")])
        )
        self.assertEqual(result["verdict"], COMMONALITY_SPLIT)
        self.assertTrue(result["findings"])

    def test_an_unbound_member_outranks_a_split_group(self):
        result = assess_parallel_command_commonality(
            _group(
                members=[
                    _member("lcl-a"),
                    _member("lcl-b", on="own-on-2"),
                    _member("lcl-c", off=None),
                ]
            )
        )
        self.assertEqual(result["verdict"], COMMONALITY_UNBOUND)

    def test_a_shared_line_arriving_too_far_apart_is_a_skew_finding(self):
        result = assess_parallel_command_commonality(
            _group(
                members=[
                    _member("lcl-a", delay=5.0),
                    _member("lcl-b", delay=400.0),
                ]
            )
        )
        self.assertEqual(result["verdict"], COMMONALITY_SKEWED)
        self.assertFalse(result["skew_within_budget"])

    def test_a_skew_exactly_on_the_budget_still_holds(self):
        result = assess_parallel_command_commonality(
            _group(
                members=[
                    _member("lcl-a", delay=10.0),
                    _member("lcl-b", delay=60.0),
                ]
            )
        )
        self.assertAlmostEqual(
            result["skew_us"],
            float(DEFAULT_COMMAND_POLICY["max_command_skew_us"]),
            places=9,
        )
        self.assertEqual(result["verdict"], COMMONALITY_HELD)

    def test_a_split_line_outranks_a_skew_finding(self):
        result = assess_parallel_command_commonality(
            _group(
                members=[
                    _member("lcl-a", delay=5.0),
                    _member("lcl-b", on="own-on-2", delay=900.0),
                ]
            )
        )
        self.assertEqual(result["verdict"], COMMONALITY_SPLIT)

    def test_both_lines_are_reported_for_every_group(self):
        result = assess_parallel_command_commonality(_group())
        self.assertEqual(
            [binding["line"] for binding in result["bindings"]], list(COMMAND_LINES)
        )

    def test_a_non_mapping_group_rejected(self):
        with self.assertRaises(ValueError):
            assess_parallel_command_commonality(["lcl-a", "lcl-b"])

    def test_a_tighter_policy_can_turn_a_held_group_into_a_skew_finding(self):
        result = assess_parallel_command_commonality(
            _group(), _policy(max_command_skew_us=1.0)
        )
        self.assertEqual(result["verdict"], COMMONALITY_SKEWED)

    def test_every_finding_is_a_readable_sentence(self):
        result = assess_parallel_command_commonality(
            _group(members=[_member("lcl-a"), _member("lcl-b", off=None)])
        )
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
