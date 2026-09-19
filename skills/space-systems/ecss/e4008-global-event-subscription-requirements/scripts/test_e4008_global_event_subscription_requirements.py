"""Contract tests for the clause 5.2.5.2 global-event-subscription logic."""

import unittest

from e4008_global_event_subscription_requirements_logic import (
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    assess_global_event_subscriptions,
    assess_subscription,
    build_dispatch_plan,
    build_event_registry,
    build_instance_registry,
    subscription_key,
)

EVENTS = [
    {"name": "EnterInitialise"},
    {"name": "LeaveInitialise"},
    {"name": "EnterStandby"},
    {"name": "PreSimTimeChange", "subscribable": False},
]

INSTANCES = [
    {
        "path": "Assembly/Gyro",
        "entry_points": [
            {"name": "OnInitialise"},
            {"name": "OnStandby"},
            {"name": "OnSample", "arity": 1},
            {"name": "OnInternal", "published": False},
        ],
    },
    {
        "path": "Assembly/Clock",
        "entry_points": [
            {"name": "OnInitialise"},
        ],
    },
]


def subscribe(event="EnterInitialise", instance="Assembly/Gyro",
              entry_point="OnInitialise"):
    return {"event": event, "instance": instance, "entry_point": entry_point}


class EventRegistryTests(unittest.TestCase):
    def test_registry_is_keyed_by_event_name(self):
        registry = build_event_registry(EVENTS)
        self.assertIn("EnterStandby", registry)

    def test_subscribable_defaults_to_true(self):
        registry = build_event_registry(EVENTS)
        self.assertTrue(registry["EnterInitialise"]["subscribable"])

    def test_closed_event_is_recorded(self):
        registry = build_event_registry(EVENTS)
        self.assertFalse(registry["PreSimTimeChange"]["subscribable"])

    def test_duplicate_event_rejected(self):
        with self.assertRaises(ValueError):
            build_event_registry(EVENTS + [{"name": "EnterStandby"}])

    def test_empty_event_list_rejected(self):
        with self.assertRaises(ValueError):
            build_event_registry([])

    def test_non_boolean_subscribable_rejected(self):
        with self.assertRaises(ValueError):
            build_event_registry([{"name": "E", "subscribable": "yes"}])


class InstanceRegistryTests(unittest.TestCase):
    def test_registry_maps_path_to_entry_points(self):
        registry = build_instance_registry(INSTANCES)
        self.assertIn("OnStandby", registry["Assembly/Gyro"])

    def test_arity_defaults_to_zero(self):
        registry = build_instance_registry(INSTANCES)
        self.assertEqual(registry["Assembly/Gyro"]["OnInitialise"]["arity"], 0)

    def test_duplicate_instance_rejected(self):
        with self.assertRaises(ValueError):
            build_instance_registry(INSTANCES + [INSTANCES[1]])

    def test_duplicate_entry_point_rejected(self):
        with self.assertRaises(ValueError):
            build_instance_registry([
                {"path": "A", "entry_points": [{"name": "X"}, {"name": "X"}]}
            ])

    def test_negative_arity_rejected(self):
        with self.assertRaises(ValueError):
            build_instance_registry([
                {"path": "A", "entry_points": [{"name": "X", "arity": -1}]}
            ])

    def test_empty_instance_list_rejected(self):
        with self.assertRaises(ValueError):
            build_instance_registry([])

    def test_instance_without_entry_points_is_allowed(self):
        registry = build_instance_registry([{"path": "A"}])
        self.assertEqual(registry["A"], {})


class SubscriptionKeyTests(unittest.TestCase):
    def test_key_joins_event_instance_and_entry_point(self):
        self.assertEqual(
            subscription_key("E", "A/B", "OnE"), "E->A/B.OnE"
        )

    def test_blank_component_rejected(self):
        with self.assertRaises(ValueError):
            subscription_key("E", "  ", "OnE")


class SingleSubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.events = build_event_registry(EVENTS)
        self.instances = build_instance_registry(INSTANCES)

    def _assess(self, subscription, seen=None):
        return assess_subscription(subscription, self.events, self.instances, seen)

    def test_clean_subscription_satisfies_all_three_items(self):
        record = self._assess(subscribe())
        self.assertEqual(record["satisfied"], NORMATIVE_ITEM_COUNT)
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_every_normative_item_is_graded(self):
        record = self._assess(subscribe())
        self.assertEqual(sorted(record["items"]), sorted(NORMATIVE_ITEMS))

    def test_unknown_event_is_caught(self):
        record = self._assess(subscribe(event="EnterFlight"))
        self.assertFalse(
            record["items"]["global-event-published-and-open-to-subscription"]
        )

    def test_closed_event_is_caught_separately_from_an_unknown_one(self):
        record = self._assess(subscribe(event="PreSimTimeChange"))
        self.assertFalse(
            record["items"]["global-event-published-and-open-to-subscription"]
        )
        self.assertIn("not open to subscription", record["findings"][0])

    def test_unknown_instance_is_caught(self):
        record = self._assess(subscribe(instance="Assembly/Star"))
        self.assertFalse(record["items"]["entry-point-published-and-argument-free"])

    def test_unknown_entry_point_is_caught(self):
        record = self._assess(subscribe(entry_point="OnLaunch"))
        self.assertFalse(record["items"]["entry-point-published-and-argument-free"])

    def test_unpublished_entry_point_is_caught(self):
        record = self._assess(subscribe(entry_point="OnInternal"))
        self.assertFalse(record["items"]["entry-point-published-and-argument-free"])
        self.assertIn("not published", record["findings"][0])

    def test_entry_point_with_arguments_is_caught(self):
        record = self._assess(subscribe(entry_point="OnSample"))
        self.assertFalse(record["items"]["entry-point-published-and-argument-free"])
        self.assertIn("carries no payload", record["findings"][0])

    def test_repeated_subscription_is_caught(self):
        seen = set()
        self.assertTrue(self._assess(subscribe(), seen)["compliant"])
        second = self._assess(subscribe(), seen)
        self.assertFalse(second["items"]["subscription-not-duplicated"])

    def test_same_entry_point_on_two_events_is_not_a_duplicate(self):
        seen = set()
        self.assertTrue(self._assess(subscribe(), seen)["compliant"])
        other = self._assess(
            subscribe(event="EnterStandby", entry_point="OnStandby"), seen
        )
        self.assertTrue(other["compliant"])

    def test_two_instances_on_one_event_are_not_duplicates(self):
        seen = set()
        self.assertTrue(self._assess(subscribe(), seen)["compliant"])
        other = self._assess(subscribe(instance="Assembly/Clock"), seen)
        self.assertTrue(other["compliant"])

    def test_two_independent_breaches_drop_two_items(self):
        record = self._assess(subscribe(event="EnterFlight", entry_point="OnSample"))
        self.assertEqual(record["satisfied"], NORMATIVE_ITEM_COUNT - 2)

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_subscription(
                {"event": "EnterInitialise", "instance": "Assembly/Gyro"},
                self.events, self.instances,
            )

    def test_non_mapping_subscription_rejected(self):
        with self.assertRaises(ValueError):
            assess_subscription(["EnterInitialise"], self.events, self.instances)

    def test_bad_seen_collection_rejected(self):
        with self.assertRaises(ValueError):
            assess_subscription(subscribe(), self.events, self.instances, [])


class DispatchPlanTests(unittest.TestCase):
    def setUp(self):
        self.events = build_event_registry(EVENTS)
        self.instances = build_instance_registry(INSTANCES)

    def test_plan_keeps_declaration_order(self):
        seen = set()
        records = [
            assess_subscription(subscribe(instance="Assembly/Clock"),
                                self.events, self.instances, seen),
            assess_subscription(subscribe(), self.events, self.instances, seen),
        ]
        plan = build_dispatch_plan(records)
        self.assertEqual(
            plan["EnterInitialise"],
            ["Assembly/Clock.OnInitialise", "Assembly/Gyro.OnInitialise"],
        )

    def test_non_compliant_subscription_is_not_dispatched(self):
        record = assess_subscription(
            subscribe(entry_point="OnSample"), self.events, self.instances
        )
        self.assertEqual(build_dispatch_plan([record]), {})

    def test_empty_record_list_gives_an_empty_plan(self):
        self.assertEqual(build_dispatch_plan([]), {})

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            build_dispatch_plan([{"event": "EnterInitialise"}])

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            build_dispatch_plan({"event": "EnterInitialise"})


class DocumentTests(unittest.TestCase):
    def _spec(self, subscriptions):
        return {
            "global_events": EVENTS,
            "instances": INSTANCES,
            "subscriptions": subscriptions,
        }

    def test_clean_document_is_compliant(self):
        result = assess_global_event_subscriptions(self._spec([
            subscribe(),
            subscribe(instance="Assembly/Clock"),
            subscribe(event="EnterStandby", entry_point="OnStandby"),
        ]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["subscribed_event_count"], 2)

    def test_graded_count_is_three_per_subscription(self):
        result = assess_global_event_subscriptions(self._spec([subscribe()]))
        self.assertEqual(result["graded"], NORMATIVE_ITEM_COUNT)

    def test_dispatch_plan_groups_two_subscribers_under_one_event(self):
        result = assess_global_event_subscriptions(self._spec([
            subscribe(),
            subscribe(instance="Assembly/Clock"),
        ]))
        self.assertEqual(len(result["dispatch_plan"]["EnterInitialise"]), 2)

    def test_duplicate_subscription_is_reported_and_not_dispatched_twice(self):
        result = assess_global_event_subscriptions(self._spec([
            subscribe(), subscribe(),
        ]))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["dispatch_plan"]["EnterInitialise"]), 1)

    def test_satisfied_count_tracks_the_breaches(self):
        result = assess_global_event_subscriptions(self._spec([
            subscribe(),
            subscribe(event="PreSimTimeChange", entry_point="OnStandby"),
        ]))
        self.assertEqual(result["satisfied"], 2 * NORMATIVE_ITEM_COUNT - 1)

    def test_empty_subscription_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_global_event_subscriptions(self._spec([]))

    def test_missing_instances_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_global_event_subscriptions({
                "global_events": EVENTS, "subscriptions": [subscribe()],
            })

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_global_event_subscriptions(EVENTS)


if __name__ == "__main__":
    unittest.main()
