"""Contract tests for the clause 5.2.12.1.1 parallel-operation allowance."""

import unittest

from e2020_parallel_limiter_operation_allowance_logic import (
    DEFAULT_PARALLEL_ALLOWANCE_POLICY,
    FOLDBACK_LIMITER,
    GROUP_ALLOWANCE_MET,
    GROUP_CAPABILITY_SHORT,
    GROUP_DEPARTURE_ARGUED,
    GROUP_OUTSIDE_ALLOWANCE,
    HIGH_POWER_LIMITER,
    LATCHING_CURRENT_LIMITER,
    MEMBER_COMMAND_NOT_COMMON,
    MEMBER_ELIGIBLE,
    MEMBER_FAMILY_MISMATCH,
    MEMBER_PART_MISMATCH,
    MEMBER_STATUS_NOT_READABLE,
    MEMBER_THRESHOLD_OUT_OF_TOLERANCE,
    RETRIGGERABLE_LIMITER,
    SERIES_FUSE,
    assess_member_eligibility,
    assess_parallel_allowance,
    categorize_limiter_type,
    departure_is_argued,
    group_reference,
    threshold_spread_fraction,
    usable_group_limit_a,
    validate_parallel_allowance_policy,
    worst_member_standing,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PARALLEL_ALLOWANCE_POLICY)
    policy.update(overrides)
    return policy


def _member(identifier="lcl-a", **overrides):
    member = {
        "id": identifier,
        "limiter_type": LATCHING_CURRENT_LIMITER,
        "part_reference": "lcl-3a-flight",
        "limiting_threshold_a": 3.0,
        "common_command": True,
        "status_readable": True,
    }
    member.update(overrides)
    return member


def _group(members=None, **overrides):
    group = {
        "members": members
        if members is not None
        else [_member("lcl-a"), _member("lcl-b")],
        "load_demand_a": 4.0,
        "departure_rationale": "",
        "verification_activities": [],
    }
    group.update(overrides)
    return group


def _reference():
    return group_reference([_member("lcl-a"), _member("lcl-b")])


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_parallel_allowance_policy(DEFAULT_PARALLEL_ALLOWANCE_POLICY),
            DEFAULT_PARALLEL_ALLOWANCE_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_parallel_allowance_policy("parallel")

    def test_a_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_parallel_allowance_policy(
                _policy(threshold_spread_tolerance_fraction=1.0)
            )

    def test_a_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_parallel_allowance_policy(_policy(group_limit_margin_fraction=-0.1))

    def test_a_group_ceiling_below_a_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_parallel_allowance_policy(_policy(max_members_per_group=1))

    def test_a_non_boolean_command_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_parallel_allowance_policy(_policy(require_common_command="yes"))


class LimiterTypeTests(unittest.TestCase):
    def test_a_latching_limiter_is_covered(self):
        self.assertEqual(
            categorize_limiter_type(LATCHING_CURRENT_LIMITER),
            LATCHING_CURRENT_LIMITER,
        )

    def test_a_high_power_limiter_is_covered(self):
        self.assertEqual(
            categorize_limiter_type("  high-power-limiter "), HIGH_POWER_LIMITER
        )

    def test_a_retriggerable_limiter_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(RETRIGGERABLE_LIMITER)

    def test_a_foldback_device_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(FOLDBACK_LIMITER)

    def test_a_series_fuse_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(SERIES_FUSE)

    def test_an_empty_limiter_type_rejected(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type("   ")


class ThresholdSpreadTests(unittest.TestCase):
    def test_matched_thresholds_have_no_spread(self):
        self.assertAlmostEqual(threshold_spread_fraction([3.0, 3.0]), 0.0, places=9)

    def test_spread_is_measured_above_the_lowest(self):
        self.assertAlmostEqual(
            threshold_spread_fraction([2.0, 2.5]), 0.25, places=9
        )

    def test_spread_ignores_the_order_of_the_members(self):
        self.assertAlmostEqual(
            threshold_spread_fraction([2.5, 2.0]),
            threshold_spread_fraction([2.0, 2.5]),
            places=9,
        )

    def test_a_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            threshold_spread_fraction([3.0, 0.0])

    def test_an_empty_threshold_set_rejected(self):
        with self.assertRaises(ValueError):
            threshold_spread_fraction([])


class MemberEligibilityTests(unittest.TestCase):
    def test_a_matched_member_is_eligible(self):
        record = assess_member_eligibility(_member("lcl-b"), _reference())
        self.assertEqual(record["standing"], MEMBER_ELIGIBLE)
        self.assertEqual(record["gaps"], [])

    def test_a_different_family_is_a_mismatch(self):
        record = assess_member_eligibility(
            _member("hpl-b", limiter_type=HIGH_POWER_LIMITER), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_FAMILY_MISMATCH)

    def test_a_different_part_reference_is_a_mismatch(self):
        record = assess_member_eligibility(
            _member("lcl-b", part_reference="lcl-3a-eqm"), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_PART_MISMATCH)

    def test_a_threshold_inside_tolerance_stays_eligible(self):
        record = assess_member_eligibility(
            _member("lcl-b", limiting_threshold_a=3.12), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_ELIGIBLE)

    def test_a_threshold_exactly_on_the_tolerance_stays_eligible(self):
        record = assess_member_eligibility(
            _member("lcl-b", limiting_threshold_a=3.15), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_ELIGIBLE)

    def test_a_threshold_beyond_tolerance_is_out_of_tolerance(self):
        record = assess_member_eligibility(
            _member("lcl-b", limiting_threshold_a=3.6), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_THRESHOLD_OUT_OF_TOLERANCE)

    def test_a_member_not_switched_with_the_group_is_flagged(self):
        record = assess_member_eligibility(
            _member("lcl-b", common_command=False), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_COMMAND_NOT_COMMON)

    def test_a_member_without_status_readout_is_flagged(self):
        record = assess_member_eligibility(
            _member("lcl-b", status_readable=False), _reference()
        )
        self.assertEqual(record["standing"], MEMBER_STATUS_NOT_READABLE)

    def test_a_member_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_member_eligibility(_member(""), _reference())

    def test_a_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_member_eligibility(
                _member("lcl-b", limiting_threshold_a=-3.0), _reference()
            )


class GroupLimitTests(unittest.TestCase):
    def test_the_group_limit_is_the_sum_after_margin(self):
        records = [
            assess_member_eligibility(_member("lcl-a"), _reference()),
            assess_member_eligibility(_member("lcl-b"), _reference()),
        ]
        self.assertAlmostEqual(usable_group_limit_a(records, 0.20), 4.8, places=9)

    def test_a_zero_margin_keeps_the_whole_sum(self):
        records = [
            assess_member_eligibility(_member("lcl-a"), _reference()),
            assess_member_eligibility(_member("lcl-b"), _reference()),
        ]
        self.assertAlmostEqual(usable_group_limit_a(records, 0.0), 6.0, places=9)

    def test_an_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            usable_group_limit_a([], 0.20)


class DepartureArgumentTests(unittest.TestCase):
    def test_a_rationale_and_an_activity_make_an_argument(self):
        argument = departure_is_argued(
            {
                "departure_rationale": "mixed lots screened to one trip band",
                "verification_activities": ["paralleled trip test at qualification"],
            }
        )
        self.assertTrue(argument["argued"])
        self.assertEqual(len(argument["activities"]), 1)

    def test_a_bare_declaration_is_not_an_argument(self):
        argument = departure_is_argued(
            {"departure_rationale": "", "verification_activities": []}
        )
        self.assertFalse(argument["argued"])
        self.assertEqual(len(argument["gaps"]), 2)

    def test_a_repeated_verification_activity_rejected(self):
        with self.assertRaises(ValueError):
            departure_is_argued(
                {
                    "departure_rationale": "mixed lots screened to one trip band",
                    "verification_activities": ["trip test", "trip test"],
                }
            )

    def test_an_empty_activity_entry_rejected(self):
        with self.assertRaises(ValueError):
            departure_is_argued(
                {
                    "departure_rationale": "mixed lots screened to one trip band",
                    "verification_activities": ["trip test", "  "],
                }
            )


class GroupAssessmentTests(unittest.TestCase):
    def test_a_matched_pair_meets_the_allowance(self):
        result = assess_parallel_allowance(_group())
        self.assertEqual(result["verdict"], GROUP_ALLOWANCE_MET)
        self.assertTrue(result["homogeneous"])
        self.assertEqual(result["findings"], [])

    def test_a_demand_exactly_on_the_usable_limit_still_fits(self):
        result = assess_parallel_allowance(_group(load_demand_a=4.8))
        self.assertAlmostEqual(result["usable_group_limit_a"], 4.8, places=9)
        self.assertTrue(result["limit_covers_demand"])
        self.assertEqual(result["verdict"], GROUP_ALLOWANCE_MET)

    def test_a_demand_above_the_usable_limit_is_capability_short(self):
        result = assess_parallel_allowance(_group(load_demand_a=5.5))
        self.assertEqual(result["verdict"], GROUP_CAPABILITY_SHORT)

    def test_a_mixed_group_without_an_argument_is_outside_the_allowance(self):
        result = assess_parallel_allowance(
            _group([_member("lcl-a"), _member("lcl-b", part_reference="lcl-3a-eqm")])
        )
        self.assertEqual(result["verdict"], GROUP_OUTSIDE_ALLOWANCE)
        self.assertFalse(result["homogeneous"])

    def test_a_mixed_group_with_an_argument_is_a_departure(self):
        result = assess_parallel_allowance(
            _group(
                [_member("lcl-a"), _member("lcl-b", part_reference="lcl-3a-eqm")],
                departure_rationale="both lots screened into one trip band",
                verification_activities=["paralleled trip test at qualification"],
            )
        )
        self.assertEqual(result["verdict"], GROUP_DEPARTURE_ARGUED)

    def test_a_group_over_the_member_ceiling_is_reported(self):
        members = [_member("lcl-%d" % index) for index in range(5)]
        result = assess_parallel_allowance(
            _group(members, load_demand_a=4.0)
        )
        self.assertEqual(result["verdict"], GROUP_OUTSIDE_ALLOWANCE)
        self.assertTrue(
            any("member ceiling" in f or "allowed to carry" in f for f in result["findings"])
        )

    def test_a_single_member_is_not_a_parallel_group(self):
        with self.assertRaises(ValueError):
            assess_parallel_allowance(_group([_member("lcl-a")]))

    def test_a_duplicate_member_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_parallel_allowance(_group([_member("lcl-a"), _member("lcl-a")]))

    def test_a_missing_load_demand_rejected(self):
        group = _group()
        del group["load_demand_a"]
        with self.assertRaises(ValueError):
            assess_parallel_allowance(group)

    def test_findings_name_the_member_that_produced_them(self):
        result = assess_parallel_allowance(
            _group([_member("lcl-a"), _member("lcl-z", common_command=False)])
        )
        self.assertTrue(result["findings"])
        self.assertTrue(result["findings"][0].startswith("lcl-z:"))

    def test_the_group_spread_is_reported(self):
        result = assess_parallel_allowance(
            _group([_member("lcl-a"), _member("lcl-b", limiting_threshold_a=3.15)])
        )
        self.assertAlmostEqual(
            result["threshold_spread_fraction"], 0.05, places=9
        )

    def test_the_worst_member_standing_is_the_one_reported(self):
        reference = _reference()
        records = [
            assess_member_eligibility(_member("lcl-a"), reference),
            assess_member_eligibility(
                _member("lcl-b", status_readable=False), reference
            ),
            assess_member_eligibility(
                _member("hpl-c", limiter_type=HIGH_POWER_LIMITER), reference
            ),
        ]
        self.assertEqual(worst_member_standing(records), MEMBER_FAMILY_MISMATCH)

    def test_worst_member_standing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_member_standing([])


if __name__ == "__main__":
    unittest.main()
