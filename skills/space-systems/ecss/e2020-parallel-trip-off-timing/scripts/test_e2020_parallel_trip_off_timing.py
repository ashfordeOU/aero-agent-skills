"""Contract tests for the clause 5.2.12.3.1 paralleled trip-off timing logic."""

import unittest

from e2020_parallel_trip_off_timing_logic import (
    DEFAULT_TRIP_TIMING_POLICY,
    DRIVEN_BY_OWN_CURRENT,
    DRIVEN_BY_REDISTRIBUTION,
    FOLDBACK_LIMITER,
    HIGH_POWER_LIMITER,
    LATCHING_CURRENT_LIMITER,
    MEMBER_HOLDS,
    MEMBER_TRIP_UNCHARACTERIZED,
    MEMBER_TRIPS_ON_OWN_CURRENT,
    MEMBER_TRIPS_ON_REDISTRIBUTION,
    RETRIGGERABLE_LIMITER,
    TRIP_CASCADE_TOO_FAST,
    TRIP_GROUP_FULLY_TRIPS,
    TRIP_GROUP_TOO_SLOW,
    TRIP_NONE,
    TRIP_NOT_CHARACTERIZED,
    TRIP_PARTIAL_HOLD,
    TRIP_UNINTENDED_DISCONNECTION,
    assess_group_trip_timing,
    cascade_margin_respected,
    cascade_trip_sequence,
    categorize_limiter_type,
    redistribute_current,
    trip_time_s,
    validate_trip_timing_policy,
    worst_member_standing,
)


def _policy(**overrides):
    policy = dict(DEFAULT_TRIP_TIMING_POLICY)
    policy.update(overrides)
    return policy


def _member(identifier="lcl-a", current=2.0, threshold=3.0, constant=1.0, **overrides):
    member = {
        "id": identifier,
        "limiter_type": LATCHING_CURRENT_LIMITER,
        "branch_current_a": current,
        "trip_threshold_a": threshold,
        "trip_time_constant_s": constant,
        "trip_characteristic_declared": True,
    }
    member.update(overrides)
    return member


def _group(members=None, **overrides):
    group = {
        "members": members
        if members is not None
        else [_member("lcl-a"), _member("lcl-b")],
    }
    group.update(overrides)
    return group


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_trip_timing_policy(DEFAULT_TRIP_TIMING_POLICY),
            DEFAULT_TRIP_TIMING_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_trip_timing_policy("fast")

    def test_a_zero_cascade_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_trip_timing_policy(_policy(min_cascade_margin_s=0.0))

    def test_a_negative_group_trip_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_trip_timing_policy(_policy(max_group_trip_time_s=-1.0))

    def test_a_non_boolean_characteristic_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_trip_timing_policy(_policy(require_trip_characteristic="yes"))


class LimiterTypeTests(unittest.TestCase):
    def test_a_latching_limiter_is_governed(self):
        self.assertEqual(
            categorize_limiter_type(LATCHING_CURRENT_LIMITER),
            LATCHING_CURRENT_LIMITER,
        )

    def test_a_high_power_limiter_is_governed(self):
        self.assertEqual(
            categorize_limiter_type("high-power-limiter "), HIGH_POWER_LIMITER
        )

    def test_a_retriggerable_limiter_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(RETRIGGERABLE_LIMITER)

    def test_a_foldback_device_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(FOLDBACK_LIMITER)

    def test_an_unrecognised_limiter_type_rejected(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type("bus-switch")


class TripTimeTests(unittest.TestCase):
    def test_twice_the_threshold_trips_in_one_time_constant(self):
        self.assertAlmostEqual(trip_time_s(6.0, 3.0, 1.0), 1.0, places=9)

    def test_a_larger_overload_trips_sooner(self):
        self.assertAlmostEqual(trip_time_s(9.0, 3.0, 1.0), 0.5, places=9)

    def test_a_current_exactly_on_the_threshold_does_not_trip(self):
        self.assertIsNone(trip_time_s(3.0, 3.0, 1.0))

    def test_a_current_below_the_threshold_does_not_trip(self):
        self.assertIsNone(trip_time_s(2.0, 3.0, 1.0))

    def test_a_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            trip_time_s(4.0, 0.0, 1.0)

    def test_a_zero_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            trip_time_s(4.0, 3.0, 0.0)

    def test_a_negative_branch_current_rejected(self):
        with self.assertRaises(ValueError):
            trip_time_s(-1.0, 3.0, 1.0)


class RedistributionTests(unittest.TestCase):
    def test_a_single_survivor_takes_the_whole_shed_current(self):
        parts = redistribute_current(3.6, [{"trip_threshold_a": 3.0}])
        self.assertAlmostEqual(parts[0], 3.6, places=9)

    def test_equal_survivors_split_the_shed_current_evenly(self):
        parts = redistribute_current(
            4.0, [{"trip_threshold_a": 3.0}, {"trip_threshold_a": 3.0}]
        )
        self.assertAlmostEqual(parts[0], 2.0, places=9)
        self.assertAlmostEqual(parts[1], 2.0, places=9)

    def test_the_split_follows_the_survivor_thresholds(self):
        parts = redistribute_current(
            4.0, [{"trip_threshold_a": 3.0}, {"trip_threshold_a": 1.0}]
        )
        self.assertAlmostEqual(parts[0], 3.0, places=9)
        self.assertAlmostEqual(parts[1], 1.0, places=9)

    def test_the_shed_current_is_conserved(self):
        parts = redistribute_current(
            5.0,
            [
                {"trip_threshold_a": 2.0},
                {"trip_threshold_a": 3.0},
                {"trip_threshold_a": 5.0},
            ],
        )
        self.assertAlmostEqual(sum(parts), 5.0, places=9)

    def test_redistribution_without_a_survivor_rejected(self):
        with self.assertRaises(ValueError):
            redistribute_current(4.0, [])


class CascadeMarginTests(unittest.TestCase):
    def test_a_single_event_always_respects_the_margin(self):
        self.assertTrue(cascade_margin_respected([0.4], 0.05))

    def test_a_gap_exactly_on_the_margin_is_respected(self):
        self.assertTrue(cascade_margin_respected([0.10, 0.15], 0.05))

    def test_a_gap_below_the_margin_is_not_respected(self):
        self.assertFalse(cascade_margin_respected([0.10, 0.12], 0.05))

    def test_the_margin_is_checked_on_every_consecutive_pair(self):
        self.assertFalse(cascade_margin_respected([0.10, 0.20, 0.21], 0.05))

    def test_a_zero_margin_rejected(self):
        with self.assertRaises(ValueError):
            cascade_margin_respected([0.10, 0.20], 0.0)


class CascadeWalkTests(unittest.TestCase):
    def test_a_group_inside_its_thresholds_produces_no_event(self):
        walk = cascade_trip_sequence(
            [
                {
                    "id": "lcl-a",
                    "initial_current_a": 2.0,
                    "trip_threshold_a": 3.0,
                    "trip_time_constant_s": 1.0,
                },
                {
                    "id": "lcl-b",
                    "initial_current_a": 2.0,
                    "trip_threshold_a": 3.0,
                    "trip_time_constant_s": 1.0,
                },
            ]
        )
        self.assertEqual(walk["events"], [])
        self.assertFalse(walk["fully_tripped"])

    def test_a_shed_current_can_trip_a_member_that_was_safe(self):
        walk = cascade_trip_sequence(
            [
                {
                    "id": "lcl-a",
                    "initial_current_a": 3.6,
                    "trip_threshold_a": 3.0,
                    "trip_time_constant_s": 0.02,
                },
                {
                    "id": "lcl-b",
                    "initial_current_a": 2.0,
                    "trip_threshold_a": 3.0,
                    "trip_time_constant_s": 0.02,
                },
            ]
        )
        self.assertTrue(walk["fully_tripped"])
        self.assertEqual(walk["events"][0]["id"], "lcl-a")
        self.assertEqual(walk["events"][0]["driven_by"], DRIVEN_BY_OWN_CURRENT)
        self.assertEqual(walk["events"][1]["id"], "lcl-b")
        self.assertEqual(
            walk["events"][1]["driven_by"], DRIVEN_BY_REDISTRIBUTION
        )

    def test_the_first_event_lands_at_its_own_trip_time(self):
        walk = cascade_trip_sequence(
            [
                {
                    "id": "lcl-a",
                    "initial_current_a": 6.0,
                    "trip_threshold_a": 3.0,
                    "trip_time_constant_s": 1.0,
                },
                {
                    "id": "lcl-b",
                    "initial_current_a": 0.5,
                    "trip_threshold_a": 30.0,
                    "trip_time_constant_s": 1.0,
                },
            ]
        )
        self.assertAlmostEqual(walk["events"][0]["at_s"], 1.0, places=9)
        self.assertEqual(walk["survivors"], ("lcl-b",))

    def test_a_single_member_is_not_a_cascade(self):
        with self.assertRaises(ValueError):
            cascade_trip_sequence(
                [
                    {
                        "id": "lcl-a",
                        "initial_current_a": 6.0,
                        "trip_threshold_a": 3.0,
                        "trip_time_constant_s": 1.0,
                    }
                ]
            )


class GroupAssessmentTests(unittest.TestCase):
    def test_a_group_inside_its_thresholds_does_not_trip(self):
        result = assess_group_trip_timing(_group())
        self.assertEqual(result["verdict"], TRIP_NONE)
        self.assertEqual(result["findings"], [])
        self.assertIsNone(result["first_trip_time_s"])

    def test_a_redistribution_driven_full_trip_is_unintended(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=3.6, constant=0.02),
                    _member("lcl-b", current=2.0, constant=0.02),
                ]
            )
        )
        self.assertEqual(result["verdict"], TRIP_UNINTENDED_DISCONNECTION)
        self.assertIn(
            "lcl-b", result["standings"][MEMBER_TRIPS_ON_REDISTRIBUTION]
        )
        self.assertTrue(result["fully_tripped"])

    def test_a_survivor_that_holds_is_a_partial_trip(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=6.0, threshold=3.0, constant=1.0),
                    _member("lcl-b", current=0.5, threshold=30.0, constant=1.0),
                ]
            )
        )
        self.assertEqual(result["verdict"], TRIP_PARTIAL_HOLD)
        self.assertEqual(result["survivors"], ("lcl-b",))
        self.assertIn("lcl-b", result["standings"][MEMBER_HOLDS])

    def test_a_group_that_trips_on_its_own_currents_is_reported_as_such(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=3.6, constant=1.0),
                    _member("lcl-b", current=4.5, constant=1.0),
                ]
            )
        )
        self.assertEqual(result["verdict"], TRIP_GROUP_FULLY_TRIPS)
        self.assertEqual(
            sorted(result["standings"][MEMBER_TRIPS_ON_OWN_CURRENT]),
            ["lcl-a", "lcl-b"],
        )

    def test_a_slow_full_trip_is_reported_against_the_ceiling(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=3.6, constant=1.0),
                    _member("lcl-b", current=4.5, constant=1.0),
                ]
            ),
            _policy(max_group_trip_time_s=1.0),
        )
        self.assertEqual(result["verdict"], TRIP_GROUP_TOO_SLOW)

    def test_a_trip_time_exactly_on_the_ceiling_is_accepted(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=6.0, threshold=3.0, constant=1.0),
                    _member("lcl-b", current=4.5, threshold=3.0, constant=1.0),
                ]
            ),
            _policy(max_group_trip_time_s=1.4, min_cascade_margin_s=0.3),
        )
        self.assertAlmostEqual(result["group_trip_time_s"], 1.4, places=9)
        self.assertEqual(result["verdict"], TRIP_GROUP_FULLY_TRIPS)

    def test_a_tight_cascade_is_reported_when_nothing_was_redistributed(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=6.0, threshold=3.0, constant=1.0),
                    _member("lcl-b", current=0.5, threshold=30.0, constant=1.0),
                    _member("lcl-c", current=6.1, threshold=3.0, constant=1.0),
                ]
            ),
            _policy(min_cascade_margin_s=1.0),
        )
        self.assertEqual(result["verdict"], TRIP_CASCADE_TOO_FAST)
        self.assertFalse(result["cascade_margin_respected"])

    def test_an_undeclared_characteristic_stops_the_group(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=3.6, constant=0.02),
                    _member(
                        "lcl-b",
                        current=2.0,
                        trip_characteristic_declared=False,
                        trip_time_constant_s=None,
                    ),
                ]
            )
        )
        self.assertEqual(result["verdict"], TRIP_NOT_CHARACTERIZED)
        self.assertIsNone(result["group_trip_time_s"])
        self.assertIn("lcl-b", result["standings"][MEMBER_TRIP_UNCHARACTERIZED])

    def test_an_assumed_never_tripping_member_keeps_the_group_partial(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=3.6, constant=0.02),
                    _member(
                        "lcl-b",
                        current=2.0,
                        trip_characteristic_declared=False,
                        trip_time_constant_s=None,
                    ),
                ]
            ),
            _policy(require_trip_characteristic=False),
        )
        self.assertEqual(result["verdict"], TRIP_PARTIAL_HOLD)
        self.assertIn("lcl-b", result["standings"][MEMBER_TRIP_UNCHARACTERIZED])

    def test_a_single_member_group_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_trip_timing(_group([_member("lcl-a")]))

    def test_a_duplicate_member_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_trip_timing(_group([_member("lcl-a"), _member("lcl-a")]))

    def test_a_member_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_trip_timing(_group([_member(""), _member("lcl-b")]))

    def test_an_out_of_scope_member_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_trip_timing(
                _group(
                    [
                        _member("lcl-a", limiter_type=FOLDBACK_LIMITER),
                        _member("lcl-b"),
                    ]
                )
            )

    def test_findings_name_the_member_that_produced_them(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-x", current=3.6, constant=0.02),
                    _member("lcl-y", current=2.0, constant=0.02),
                ]
            )
        )
        self.assertTrue(result["findings"])
        self.assertTrue(result["findings"][0].startswith("lcl-y:"))

    def test_the_trip_spread_is_the_distance_between_first_and_last(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=6.0, threshold=3.0, constant=1.0),
                    _member("lcl-b", current=6.0, threshold=3.0, constant=1.0),
                ]
            ),
            _policy(min_cascade_margin_s=0.3),
        )
        self.assertAlmostEqual(result["trip_spread_s"], 1.0 / 3.0, places=9)

    def test_the_worst_member_standing_is_the_one_reported(self):
        result = assess_group_trip_timing(
            _group(
                [
                    _member("lcl-a", current=3.6, constant=0.02),
                    _member("lcl-b", current=2.0, constant=0.02),
                ]
            )
        )
        self.assertEqual(
            worst_member_standing(result["members"]),
            MEMBER_TRIPS_ON_REDISTRIBUTION,
        )

    def test_worst_member_standing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_member_standing([])


if __name__ == "__main__":
    unittest.main()
