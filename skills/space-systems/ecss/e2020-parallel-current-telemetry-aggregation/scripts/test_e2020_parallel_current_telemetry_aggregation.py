"""Contract tests for the clause 5.2.12.5.1 parallel current telemetry logic."""

import math
import unittest

from e2020_parallel_current_telemetry_aggregation_logic import (
    COMBINATION_RULES,
    COMBINE_ROOT_SUM_SQUARE,
    COMBINE_WORST_CASE,
    DEFAULT_TELEMETRY_POLICY,
    TELEMETRY_ACCURACY_SHORTFALL,
    TELEMETRY_MARGIN_SHORTFALL,
    TELEMETRY_OMITS_MEMBER,
    TELEMETRY_REPORTS_GROUP_TOTAL,
    TELEMETRY_SATURATED,
    aggregated_current_a,
    assess_parallel_current_telemetry,
    categorize_combination_rule,
    combined_accuracy_fraction,
    full_scale_margin_fraction,
    group_total_current_a,
    normalize_member,
    normalize_members,
    omitted_members,
    reported_current_a,
    reported_error_fraction,
    validate_telemetry_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_TELEMETRY_POLICY)
    policy.update(overrides)
    return policy


def _member(identifier, current=10.0, accuracy=0.01, aggregated=True):
    return {
        "id": identifier,
        "current_a": current,
        "accuracy_fraction": accuracy,
        "aggregated": aggregated,
    }


def _group(**overrides):
    group = {
        "members": [
            _member("lcl-a"),
            _member("lcl-b"),
            _member("lcl-c"),
        ],
        "full_scale_a": 40.0,
    }
    group.update(overrides)
    return group


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_telemetry_policy(DEFAULT_TELEMETRY_POLICY),
            DEFAULT_TELEMETRY_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_telemetry_policy("total")

    def test_an_error_budget_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_telemetry_policy(_policy(max_reported_error_fraction=1.0))

    def test_a_negative_range_margin_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_telemetry_policy(_policy(min_full_scale_margin_fraction=-0.1))

    def test_a_zero_range_margin_floor_is_allowed(self):
        policy = _policy(min_full_scale_margin_fraction=0.0)
        self.assertIs(validate_telemetry_policy(policy), policy)

    def test_an_unrecognised_combination_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_telemetry_policy(_policy(combination_rule="average-of-two"))

    def test_every_known_combination_rule_round_trips(self):
        for rule in COMBINATION_RULES:
            self.assertEqual(categorize_combination_rule(rule), rule)


class MemberTests(unittest.TestCase):
    def test_a_member_keeps_its_current_accuracy_and_inclusion(self):
        member = normalize_member(_member("lcl-a", current=7.5))
        self.assertEqual(member["id"], "lcl-a")
        self.assertAlmostEqual(member["current_a"], 7.5, places=9)
        self.assertTrue(member["aggregated"])

    def test_a_member_defaults_to_being_aggregated(self):
        member = normalize_member({"id": "lcl-a", "current_a": 4.0})
        self.assertTrue(member["aggregated"])

    def test_a_negative_member_current_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member(_member("lcl-a", current=-1.0))

    def test_a_member_accuracy_of_one_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member(_member("lcl-a", accuracy=1.0))

    def test_a_non_boolean_inclusion_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member(_member("lcl-a", aggregated="yes"))

    def test_a_member_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_member({"current_a": 4.0})

    def test_a_single_limiter_is_not_a_parallel_group(self):
        with self.assertRaises(ValueError):
            normalize_members([_member("lcl-a")])

    def test_a_duplicate_member_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_members([_member("lcl-a"), _member("lcl-a")])

    def test_a_non_sequence_member_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_members({"id": "lcl-a"})


class SummationTests(unittest.TestCase):
    def test_the_group_total_counts_every_member(self):
        self.assertAlmostEqual(
            group_total_current_a(_group()["members"]), 30.0, places=9
        )

    def test_the_aggregated_reading_counts_only_the_included_members(self):
        members = [_member("lcl-a"), _member("lcl-b", aggregated=False)]
        self.assertAlmostEqual(aggregated_current_a(members), 10.0, places=9)
        self.assertAlmostEqual(group_total_current_a(members), 20.0, places=9)

    def test_an_omitted_member_is_named(self):
        members = [_member("lcl-a"), _member("lcl-b", aggregated=False)]
        self.assertEqual(omitted_members(members), ("lcl-b",))

    def test_a_fully_aggregated_group_omits_nobody(self):
        self.assertEqual(omitted_members(_group()["members"]), ())

    def test_an_empty_group_has_no_total(self):
        with self.assertRaises(ValueError):
            group_total_current_a([])

    def test_a_negative_current_rejected_by_the_sum(self):
        with self.assertRaises(ValueError):
            group_total_current_a([{"id": "lcl-a", "current_a": -3.0}])


class RangeTests(unittest.TestCase):
    def test_a_reading_inside_the_range_passes_through(self):
        self.assertAlmostEqual(reported_current_a(30.0, 40.0), 30.0, places=9)

    def test_a_reading_above_the_range_is_held_at_full_scale(self):
        self.assertAlmostEqual(reported_current_a(48.0, 40.0), 40.0, places=9)

    def test_a_reading_exactly_at_full_scale_is_not_clipped(self):
        self.assertAlmostEqual(reported_current_a(40.0, 40.0), 40.0, places=9)

    def test_a_zero_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            reported_current_a(30.0, 0.0)

    def test_margin_is_the_headroom_over_the_group_total(self):
        self.assertAlmostEqual(
            full_scale_margin_fraction(40.0, 30.0), 10.0 / 30.0, places=9
        )

    def test_an_under_ranged_channel_has_a_negative_margin(self):
        self.assertLess(full_scale_margin_fraction(25.0, 30.0), 0.0)

    def test_a_zero_group_total_has_no_margin_to_report(self):
        with self.assertRaises(ValueError):
            full_scale_margin_fraction(40.0, 0.0)

    def test_the_reported_error_is_measured_against_the_group_total(self):
        self.assertAlmostEqual(
            reported_error_fraction(25.0, 30.0), 5.0 / 30.0, places=9
        )

    def test_a_reading_on_the_total_has_no_error(self):
        self.assertAlmostEqual(reported_error_fraction(30.0, 30.0), 0.0, places=9)


class AccuracyTests(unittest.TestCase):
    def test_root_sum_square_beats_the_worst_case_sum(self):
        members = _group()["members"]
        rss = combined_accuracy_fraction(members, COMBINE_ROOT_SUM_SQUARE)
        worst = combined_accuracy_fraction(members, COMBINE_WORST_CASE)
        self.assertLess(rss, worst)

    def test_root_sum_square_of_three_equal_members(self):
        members = _group()["members"]
        expected = math.sqrt(3.0 * (0.1 * 0.1)) / 30.0
        self.assertAlmostEqual(
            combined_accuracy_fraction(members, COMBINE_ROOT_SUM_SQUARE),
            expected,
            places=9,
        )

    def test_the_worst_case_sum_of_equal_members_is_the_member_accuracy(self):
        members = _group()["members"]
        self.assertAlmostEqual(
            combined_accuracy_fraction(members, COMBINE_WORST_CASE),
            0.01,
            places=9,
        )

    def test_a_group_passing_no_current_has_no_fractional_accuracy(self):
        members = [_member("lcl-a", current=0.0), _member("lcl-b", current=0.0)]
        with self.assertRaises(ValueError):
            combined_accuracy_fraction(members)

    def test_an_unrecognised_rule_rejected_by_the_combination(self):
        with self.assertRaises(ValueError):
            combined_accuracy_fraction(_group()["members"], "mean-of-members")


class GroupAssessmentTests(unittest.TestCase):
    def test_a_well_ranged_fully_summed_group_reports_the_total(self):
        result = assess_parallel_current_telemetry(_group())
        self.assertEqual(result["verdict"], TELEMETRY_REPORTS_GROUP_TOTAL)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["reported_a"], 30.0, places=9)

    def test_an_omitted_member_outranks_everything_else(self):
        result = assess_parallel_current_telemetry(
            _group(
                members=[
                    _member("lcl-a"),
                    _member("lcl-b"),
                    _member("lcl-c", aggregated=False),
                ],
                full_scale_a=22.0,
            )
        )
        self.assertEqual(result["verdict"], TELEMETRY_OMITS_MEMBER)
        self.assertEqual(result["omitted_members"], ("lcl-c",))

    def test_a_range_sized_for_one_member_saturates_on_the_group(self):
        result = assess_parallel_current_telemetry(_group(full_scale_a=12.0))
        self.assertEqual(result["verdict"], TELEMETRY_SATURATED)
        self.assertTrue(result["saturated"])
        self.assertAlmostEqual(result["reported_a"], 12.0, places=9)

    def test_a_full_scale_exactly_on_the_group_total_does_not_saturate(self):
        result = assess_parallel_current_telemetry(_group(full_scale_a=30.0))
        self.assertFalse(result["saturated"])
        self.assertAlmostEqual(result["full_scale_margin_fraction"], 0.0, places=9)
        self.assertEqual(result["verdict"], TELEMETRY_MARGIN_SHORTFALL)

    def test_a_margin_exactly_on_the_floor_still_reports_the_total(self):
        result = assess_parallel_current_telemetry(_group(full_scale_a=36.0))
        self.assertAlmostEqual(
            result["full_scale_margin_fraction"],
            float(DEFAULT_TELEMETRY_POLICY["min_full_scale_margin_fraction"]),
            places=9,
        )
        self.assertEqual(result["verdict"], TELEMETRY_REPORTS_GROUP_TOTAL)

    def test_coarse_member_sensors_show_up_as_an_accuracy_shortfall(self):
        result = assess_parallel_current_telemetry(
            _group(
                members=[
                    _member("lcl-a", accuracy=0.10),
                    _member("lcl-b", accuracy=0.10),
                    _member("lcl-c", accuracy=0.10),
                ]
            )
        )
        self.assertEqual(result["verdict"], TELEMETRY_ACCURACY_SHORTFALL)

    def test_a_saturated_range_outranks_an_accuracy_shortfall(self):
        result = assess_parallel_current_telemetry(
            _group(
                members=[
                    _member("lcl-a", accuracy=0.10),
                    _member("lcl-b", accuracy=0.10),
                    _member("lcl-c", accuracy=0.10),
                ],
                full_scale_a=12.0,
            )
        )
        self.assertEqual(result["verdict"], TELEMETRY_SATURATED)

    def test_the_worst_case_rule_can_turn_a_pass_into_a_shortfall(self):
        group = _group(
            members=[
                _member("lcl-a", accuracy=0.06),
                _member("lcl-b", accuracy=0.06),
                _member("lcl-c", accuracy=0.06),
            ]
        )
        self.assertEqual(
            assess_parallel_current_telemetry(group)["verdict"],
            TELEMETRY_REPORTS_GROUP_TOTAL,
        )
        self.assertEqual(
            assess_parallel_current_telemetry(
                group, _policy(combination_rule=COMBINE_WORST_CASE)
            )["verdict"],
            TELEMETRY_ACCURACY_SHORTFALL,
        )

    def test_a_group_passing_no_current_cannot_demonstrate_the_clause(self):
        with self.assertRaises(ValueError):
            assess_parallel_current_telemetry(
                _group(
                    members=[
                        _member("lcl-a", current=0.0),
                        _member("lcl-b", current=0.0),
                    ]
                )
            )

    def test_a_group_without_a_full_scale_rejected(self):
        group = _group()
        del group["full_scale_a"]
        with self.assertRaises(ValueError):
            assess_parallel_current_telemetry(group)

    def test_a_non_mapping_group_rejected(self):
        with self.assertRaises(ValueError):
            assess_parallel_current_telemetry(["lcl-a", "lcl-b"])

    def test_an_omitted_member_is_a_fixed_under_report_not_an_error_budget(self):
        result = assess_parallel_current_telemetry(
            _group(
                members=[
                    _member("lcl-a"),
                    _member("lcl-b"),
                    _member("lcl-c", aggregated=False),
                ]
            )
        )
        self.assertAlmostEqual(result["aggregated_a"], 20.0, places=9)
        self.assertAlmostEqual(result["group_total_a"], 30.0, places=9)
        self.assertAlmostEqual(
            result["reported_error_fraction"], 10.0 / 30.0, places=9
        )

    def test_every_finding_is_a_readable_sentence(self):
        result = assess_parallel_current_telemetry(_group(full_scale_a=12.0))
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
