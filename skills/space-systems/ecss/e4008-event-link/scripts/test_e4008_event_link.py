"""Contract tests for the clause 5.2.7.3 event-link logic."""

import unittest

from e4008_event_link_logic import (
    EVENT_ROLES,
    VOID_ARGUMENT,
    EventLinkError,
    argument_compatible,
    assess_event_links,
    event_signature,
    fan_out_map,
    resolve_event,
)

CATALOGUE = {
    "Clock": {
        "events": {
            "tick": {"role": "source", "argument": VOID_ARGUMENT},
            "epoch_changed": {"role": "source", "argument": "Duration"},
        }
    },
    "Recorder": {
        "events": {
            "on_tick": {"role": "sink", "argument": VOID_ARGUMENT},
            "on_epoch": {"role": "sink", "argument": "Duration"},
            "on_count": {"role": "sink", "argument": "Int32"},
        }
    },
    "Heater": {
        "events": {
            "on_tick": {"role": "sink", "argument": VOID_ARGUMENT},
            "overheated": {"role": "source", "argument": "Float64"},
        }
    },
}

INSTANCES = {
    "sat.clock": "Clock",
    "sat.recorder": "Recorder",
    "sat.thermal.heater": "Heater",
}


def base_links():
    return [
        {
            "name": "tick_to_recorder",
            "source": "sat.clock",
            "source_event": "tick",
            "sink": "sat.recorder",
            "sink_event": "on_tick",
        },
        {
            "name": "epoch_to_recorder",
            "source": "sat.clock",
            "source_event": "epoch_changed",
            "sink": "sat.recorder",
            "sink_event": "on_epoch",
        },
    ]


class ResolveTests(unittest.TestCase):
    def test_declared_source_resolves(self):
        resolved = resolve_event(CATALOGUE, INSTANCES, "sat.clock", "tick", "source")
        self.assertEqual(resolved["argument"], VOID_ARGUMENT)

    def test_declared_sink_resolves(self):
        resolved = resolve_event(CATALOGUE, INSTANCES, "sat.recorder", "on_epoch", "sink")
        self.assertEqual(resolved["argument"], "Duration")

    def test_sink_used_as_a_source_refused(self):
        with self.assertRaises(EventLinkError):
            resolve_event(CATALOGUE, INSTANCES, "sat.recorder", "on_tick", "source")

    def test_source_used_as_a_sink_refused(self):
        with self.assertRaises(EventLinkError):
            resolve_event(CATALOGUE, INSTANCES, "sat.clock", "tick", "sink")

    def test_undeclared_event_refused(self):
        with self.assertRaises(EventLinkError):
            resolve_event(CATALOGUE, INSTANCES, "sat.clock", "chime", "source")

    def test_unknown_instance_refused(self):
        with self.assertRaises(EventLinkError):
            resolve_event(CATALOGUE, INSTANCES, "sat.payload", "tick", "source")

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            resolve_event(CATALOGUE, INSTANCES, "sat.clock", "tick", "emitter")

    def test_two_roles_are_declared(self):
        self.assertEqual(set(EVENT_ROLES), {"source", "sink"})


class ArgumentTests(unittest.TestCase):
    def test_identical_arguments_are_compatible(self):
        self.assertTrue(argument_compatible("Duration", "Duration"))

    def test_void_pair_is_compatible(self):
        self.assertTrue(argument_compatible(VOID_ARGUMENT, VOID_ARGUMENT))

    def test_different_arguments_are_not_compatible(self):
        self.assertFalse(argument_compatible("Duration", "Int32"))

    def test_void_sink_refuses_a_carried_argument_by_default(self):
        self.assertFalse(argument_compatible("Int32", VOID_ARGUMENT))

    def test_void_sink_accepts_when_discarding_is_permitted(self):
        self.assertTrue(argument_compatible("Int32", VOID_ARGUMENT, allow_discard=True))

    def test_void_source_into_a_typed_sink_stays_incompatible(self):
        self.assertFalse(argument_compatible(VOID_ARGUMENT, "Int32", allow_discard=True))

    def test_empty_argument_type_rejected(self):
        with self.assertRaises(ValueError):
            argument_compatible("", "Int32")


class SignatureTests(unittest.TestCase):
    def test_signature_pairs_source_and_sink_paths(self):
        source = resolve_event(CATALOGUE, INSTANCES, "sat.clock", "tick", "source")
        sink = resolve_event(CATALOGUE, INSTANCES, "sat.recorder", "on_tick", "sink")
        self.assertEqual(event_signature(source, sink), ("sat.clock.tick", "sat.recorder.on_tick"))

    def test_malformed_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            event_signature({"instance": "sat.clock"}, {"instance": "x", "element": "y"})

    def test_fan_out_map_groups_by_source(self):
        result = assess_event_links(
            {
                "catalogue": CATALOGUE,
                "instances": INSTANCES,
                "links": base_links()
                + [
                    {
                        "name": "tick_to_heater",
                        "source": "sat.clock",
                        "source_event": "tick",
                        "sink": "sat.thermal.heater",
                        "sink_event": "on_tick",
                    }
                ],
            }
        )
        self.assertEqual(len(result["fan_out"]["sat.clock.tick"]), 2)

    def test_fan_out_map_rejects_a_malformed_link(self):
        with self.assertRaises(ValueError):
            fan_out_map([{"source": {"instance": "a", "element": "b"}}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, links=None, **overrides):
        spec = {
            "catalogue": CATALOGUE,
            "instances": INSTANCES,
            "links": base_links() if links is None else links,
        }
        spec.update(overrides)
        return spec

    def test_clean_event_link_set_is_compliant(self):
        result = assess_event_links(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["accepted"]), 2)

    def test_argument_mismatch_is_flagged(self):
        links = base_links()
        links[1]["sink_event"] = "on_count"
        result = assess_event_links(self._spec(links=links))
        self.assertFalse(result["compliant"])
        self.assertIn("the sink expects", result["findings"][0])

    def test_argument_mismatch_clears_when_discarding_is_permitted(self):
        links = base_links()
        links[1]["sink_event"] = "on_tick"
        result = assess_event_links(self._spec(links=links, allow_argument_discard=True))
        self.assertTrue(result["compliant"])

    def test_reversed_roles_are_flagged(self):
        links = [
            {
                "name": "backwards",
                "source": "sat.recorder",
                "source_event": "on_tick",
                "sink": "sat.clock",
                "sink_event": "tick",
            }
        ]
        result = assess_event_links(self._spec(links=links))
        self.assertIn("cannot act as", result["findings"][0])

    def test_duplicate_event_link_is_flagged(self):
        links = base_links()
        links.append(dict(links[0], name="tick_again"))
        result = assess_event_links(self._spec(links=links))
        self.assertIn("duplicates event link", result["findings"][0])

    def test_fan_in_raises_an_ordering_advisory_without_failing(self):
        links = base_links()
        links.append(
            {
                "name": "overheat_to_recorder",
                "source": "sat.thermal.heater",
                "source_event": "overheated",
                "sink": "sat.recorder",
                "sink_event": "on_tick",
            }
        )
        result = assess_event_links(self._spec(links=links, allow_argument_discard=True))
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_self_link_is_refused_by_default(self):
        catalogue = dict(CATALOGUE)
        catalogue["Heater"] = {
            "events": {
                "overheated": {"role": "source", "argument": "Float64"},
                "on_overheat": {"role": "sink", "argument": "Float64"},
            }
        }
        links = [
            {
                "name": "heater_self",
                "source": "sat.thermal.heater",
                "source_event": "overheated",
                "sink": "sat.thermal.heater",
                "sink_event": "on_overheat",
            }
        ]
        result = assess_event_links(self._spec(links=links, catalogue=catalogue))
        self.assertIn("self-link", result["findings"][0])

    def test_empty_link_set_is_vacuously_compliant(self):
        result = assess_event_links(self._spec(links=[]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["fan_out"], {})

    def test_link_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_event_links(self._spec(links=[{"name": "x", "source": "sat.clock"}]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_event_links(["catalogue"])

    def test_spec_missing_links_rejected(self):
        with self.assertRaises(ValueError):
            assess_event_links({"catalogue": CATALOGUE, "instances": INSTANCES})


if __name__ == "__main__":
    unittest.main()
