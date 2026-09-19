"""Contract tests for the clause 5.4.6 simulator event logic."""

import unittest

from e4008_event_logic import (
    ARGUMENT_TYPES,
    EMISSION_PERMITTED_STATES,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    SIMULATOR_STATES,
    EventRegistry,
    argument_matches_type,
    assess_event_conformance,
    normalise_sink_token,
    validate_argument_type,
    validate_event_name,
    validate_simulator_state,
)


def clean_spec():
    """A design that exercises every one of the fourteen normative items."""
    return {
        "sources": [
            {"name": "TimeUpdated", "argument_type": "datetime", "max_subscribers": 2},
            {"name": "EpochChanged", "argument_type": "void"},
        ],
        "subscriptions": [
            {"source": "TimeUpdated", "sink": "logger"},
            {"source": "TimeUpdated", "sink": "recorder"},
            {"source": "TimeUpdated", "sink": "logger"},
            {"source": "EpochChanged", "sink": "scheduler"},
        ],
        "unsubscriptions": [
            {"source": "EpochChanged", "sink": "never_subscribed"},
        ],
        "emissions": [
            {"source": "TimeUpdated", "argument": 1200, "state": "executing",
             "failing_sinks": ["recorder"]},
            {"source": "TimeUpdated", "argument": 3.5, "state": "executing"},
            {"source": "TimeUpdated", "argument": 1300, "state": "building"},
            {"source": "EpochChanged", "argument": 7, "state": "standby"},
            {"source": "EpochChanged", "state": "standby"},
        ],
        "unsubscribe_during_delivery": True,
    }


class NameValidationTests(unittest.TestCase):
    def test_plain_name_accepted(self):
        self.assertEqual(validate_event_name("TimeUpdated"), "TimeUpdated")

    def test_underscore_and_digits_accepted(self):
        self.assertEqual(validate_event_name("Step_2_Done"), "Step_2_Done")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_name("")

    def test_padded_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_name(" TimeUpdated")

    def test_leading_digit_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_name("2ndPass")

    def test_punctuation_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_name("Time.Updated")

    def test_over_long_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_name("E" * 65)

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_name(17)


class ArgumentTypeTests(unittest.TestCase):
    def test_type_set_is_lower_case(self):
        for name in ARGUMENT_TYPES:
            self.assertEqual(name, name.lower())

    def test_case_is_folded(self):
        self.assertEqual(validate_argument_type("Float64"), "float64")

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_argument_type("complex128")

    def test_non_string_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_argument_type(None)

    def test_void_accepts_only_absence(self):
        self.assertTrue(argument_matches_type("void", None))
        self.assertFalse(argument_matches_type("void", 0))

    def test_bool_is_not_an_integer_argument(self):
        self.assertFalse(argument_matches_type("int32", True))
        self.assertTrue(argument_matches_type("bool", True))

    def test_int32_range_is_enforced(self):
        self.assertTrue(argument_matches_type("int32", 2 ** 31 - 1))
        self.assertFalse(argument_matches_type("int32", 2 ** 31))
        self.assertTrue(argument_matches_type("int64", 2 ** 31))

    def test_duration_may_be_negative_but_datetime_may_not(self):
        self.assertTrue(argument_matches_type("duration", -50))
        self.assertFalse(argument_matches_type("datetime", -50))

    def test_float_argument_accepts_an_integer(self):
        self.assertTrue(argument_matches_type("float64", 4))
        self.assertFalse(argument_matches_type("float64", "4"))

    def test_string_argument_rejects_bytes(self):
        self.assertTrue(argument_matches_type("string", "ok"))
        self.assertFalse(argument_matches_type("string", b"ok"))


class StateTests(unittest.TestCase):
    def test_permitted_states_are_a_subset(self):
        for state in EMISSION_PERMITTED_STATES:
            self.assertIn(state, SIMULATOR_STATES)

    def test_building_is_not_permitted(self):
        self.assertNotIn("building", EMISSION_PERMITTED_STATES)

    def test_state_case_is_folded(self):
        self.assertEqual(validate_simulator_state("Standby"), "standby")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_simulator_state("paused")


class SinkTokenTests(unittest.TestCase):
    def test_hyphen_and_space_fold_to_underscore(self):
        self.assertEqual(normalise_sink_token("Data-Logger"), "data_logger")
        self.assertEqual(normalise_sink_token("Data Logger"), "data_logger")

    def test_empty_sink_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sink_token("   ")

    def test_non_string_sink_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sink_token(3.5)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.reg = EventRegistry()
        self.reg.declare_source("TimeUpdated", "datetime")

    def test_declaration_is_recorded_in_order(self):
        self.reg.declare_source("EpochChanged", "void")
        self.assertEqual(self.reg.source_names(), ["TimeUpdated", "EpochChanged"])

    def test_duplicate_declaration_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.declare_source("TimeUpdated", "void")

    def test_bad_max_subscribers_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.declare_source("Other", "void", max_subscribers=0)

    def test_subscription_order_is_preserved(self):
        self.reg.subscribe("TimeUpdated", "a")
        self.reg.subscribe("TimeUpdated", "b")
        self.assertEqual(self.reg.subscribers("TimeUpdated"), ["a", "b"])

    def test_duplicate_subscription_rejected(self):
        self.reg.subscribe("TimeUpdated", "a")
        with self.assertRaises(ValueError):
            self.reg.subscribe("TimeUpdated", "a")

    def test_aliased_sink_name_rejected(self):
        self.reg.subscribe("TimeUpdated", "Data-Logger")
        with self.assertRaises(ValueError):
            self.reg.subscribe("TimeUpdated", "data logger")

    def test_subscriber_limit_enforced(self):
        self.reg.declare_source("Bounded", "void", max_subscribers=1)
        self.reg.subscribe("Bounded", "only")
        with self.assertRaises(ValueError):
            self.reg.subscribe("Bounded", "second")

    def test_unsubscribe_of_a_stranger_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.unsubscribe("TimeUpdated", "ghost")

    def test_unsubscribe_removes_only_that_sink(self):
        self.reg.subscribe("TimeUpdated", "a")
        self.reg.subscribe("TimeUpdated", "b")
        self.assertEqual(self.reg.unsubscribe("TimeUpdated", "a"), ["b"])

    def test_subscribe_to_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.subscribe("Missing", "a")

    def test_emission_sequence_is_monotonic(self):
        first = self.reg.emit("TimeUpdated", 10)
        second = self.reg.emit("TimeUpdated", 20)
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(self.reg.sequence, 2)

    def test_emission_from_a_forbidden_state_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.emit("TimeUpdated", 10, state="building")

    def test_emission_with_a_mistyped_argument_rejected(self):
        with self.assertRaises(ValueError):
            self.reg.emit("TimeUpdated", "10")

    def test_void_source_refuses_an_argument(self):
        self.reg.declare_source("EpochChanged", "void")
        with self.assertRaises(ValueError):
            self.reg.emit("EpochChanged", 1)

    def test_void_source_emits_without_argument(self):
        self.reg.declare_source("EpochChanged", "void")
        record = self.reg.emit("EpochChanged")
        self.assertIsNone(record["argument"])

    def test_failing_sink_does_not_suppress_the_others(self):
        for sink in ("a", "b", "c"):
            self.reg.subscribe("TimeUpdated", sink)
        record = self.reg.emit("TimeUpdated", 5, failing_sinks=["b"])
        self.assertEqual(record["delivered"], ["a", "c"])
        self.assertEqual(record["failed"], ["b"])
        self.assertEqual(record["notified"], ["a", "b", "c"])

    def test_failing_sinks_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            self.reg.emit("TimeUpdated", 5, failing_sinks="b")

    def test_subscribers_view_is_a_copy(self):
        self.reg.subscribe("TimeUpdated", "a")
        view = self.reg.subscribers("TimeUpdated")
        view.append("b")
        self.assertEqual(self.reg.subscribers("TimeUpdated"), ["a"])


class ConformanceTests(unittest.TestCase):
    def test_item_catalogue_has_fourteen_entries(self):
        self.assertEqual(len(NORMATIVE_ITEMS), NORMATIVE_ITEM_COUNT)
        self.assertEqual(len(set(i for i, _ in NORMATIVE_ITEMS)), NORMATIVE_ITEM_COUNT)

    def test_clean_spec_is_compliant(self):
        result = assess_event_conformance(clean_spec())
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["not_exercised"], [])
        self.assertTrue(result["compliant"])

    def test_clean_spec_reaches_full_coverage(self):
        result = assess_event_conformance(clean_spec())
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_duplicate_source_name_is_a_violation(self):
        spec = clean_spec()
        spec["sources"].append({"name": "TimeUpdated", "argument_type": "void"})
        result = assess_event_conformance(spec)
        self.assertIn("EV-01", [v["id"] for v in result["violations"]])

    def test_missing_argument_type_is_a_violation(self):
        spec = clean_spec()
        spec["sources"].append({"name": "Untyped"})
        result = assess_event_conformance(spec)
        self.assertIn("EV-02", [v["id"] for v in result["violations"]])

    def test_undocumented_emitter_is_a_violation(self):
        spec = clean_spec()
        spec["sources"][0]["documented_emitter"] = False
        result = assess_event_conformance(spec)
        self.assertIn("EV-14", [v["id"] for v in result["violations"]])

    def test_aliased_sink_is_a_violation(self):
        spec = clean_spec()
        spec["subscriptions"].append({"source": "EpochChanged", "sink": "Scheduler"})
        result = assess_event_conformance(spec)
        self.assertIn("EV-10", [v["id"] for v in result["violations"]])

    def test_mutating_delivery_is_a_violation(self):
        spec = clean_spec()
        spec["unsubscribe_during_delivery"] = False
        result = assess_event_conformance(spec)
        self.assertIn("EV-13", [v["id"] for v in result["violations"]])

    def test_absent_delivery_flag_leaves_the_item_unexercised(self):
        spec = clean_spec()
        del spec["unsubscribe_during_delivery"]
        result = assess_event_conformance(spec)
        self.assertIn("EV-13", [r["id"] for r in result["not_exercised"]])
        self.assertFalse(result["compliant"])

    def test_coverage_drops_when_an_item_is_unexercised(self):
        spec = clean_spec()
        del spec["unsubscribe_during_delivery"]
        result = assess_event_conformance(spec)
        self.assertAlmostEqual(result["coverage"], 13.0 / 14.0, places=9)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_event_conformance(["TimeUpdated"])

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_event_conformance({"sources": []})

    def test_source_without_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_event_conformance({"sources": [{"argument_type": "void"}]})

    def test_malformed_subscription_rejected(self):
        spec = clean_spec()
        spec["subscriptions"].append({"source": "TimeUpdated"})
        with self.assertRaises(ValueError):
            assess_event_conformance(spec)

    def test_non_boolean_delivery_flag_rejected(self):
        spec = clean_spec()
        spec["unsubscribe_during_delivery"] = "yes"
        with self.assertRaises(ValueError):
            assess_event_conformance(spec)

    def test_registry_is_returned_for_inspection(self):
        result = assess_event_conformance(clean_spec())
        self.assertEqual(result["registry"].source_names(), ["TimeUpdated", "EpochChanged"])


if __name__ == "__main__":
    unittest.main()
