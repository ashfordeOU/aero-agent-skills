"""
Gate 3 contract tests — load event identification logic.
Run: python3 test_load_event_identification.py
Expects: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from load_event_identification_logic import (
    validate_event,
    categorize_events_by_phase,
    find_missing_phases,
    find_missing_flight_subtypes,
    identify_load_events,
    VALID_PHASES,
    REQUIRED_PHASES,
    VALID_LOAD_TYPES,
    MANDATORY_FLIGHT_SUBTYPES,
)


def _full_event_set():
    """Return a minimal valid set of events covering all required phases."""
    return [
        {"name": "assembly-mate", "phase": "assembly", "load_types": ["quasi_static"]},
        {"name": "acoustic-test", "phase": "test", "load_types": ["acoustic", "dynamic"]},
        {"name": "launch-liftoff", "phase": "flight", "load_types": ["quasi_static", "acoustic"]},
        {"name": "ascent-maxq", "phase": "flight", "load_types": ["quasi_static", "dynamic"]},
        {"name": "on_orbit-deploy", "phase": "flight", "load_types": ["quasi_static"]},
        {"name": "separation-pyro", "phase": "flight", "load_types": ["shock"]},
        {"name": "transportation-road", "phase": "ground_ops", "load_types": ["dynamic", "shock"]},
    ]


class TestValidateEvent(unittest.TestCase):

    def test_valid_event_returns_no_errors(self):
        event = {"name": "launch-liftoff", "phase": "flight", "load_types": ["quasi_static"]}
        self.assertEqual(validate_event(event), [])

    def test_missing_name_key_flagged(self):
        event = {"phase": "flight", "load_types": ["quasi_static"]}
        errors = validate_event(event)
        self.assertTrue(any("name" in e for e in errors))

    def test_missing_phase_key_flagged(self):
        event = {"name": "some-event", "load_types": ["dynamic"]}
        errors = validate_event(event)
        self.assertTrue(any("phase" in e for e in errors))

    def test_missing_load_types_key_flagged(self):
        event = {"name": "some-event", "phase": "assembly"}
        errors = validate_event(event)
        self.assertTrue(any("load_types" in e for e in errors))

    def test_unknown_phase_flagged(self):
        event = {"name": "bad-event", "phase": "orbit", "load_types": ["quasi_static"]}
        errors = validate_event(event)
        self.assertTrue(any("unknown phase" in e for e in errors))

    def test_unknown_load_type_flagged(self):
        event = {"name": "bad-loads", "phase": "test", "load_types": ["gravity_wave"]}
        errors = validate_event(event)
        self.assertTrue(any("unknown load types" in e for e in errors))

    def test_empty_load_types_list_flagged(self):
        event = {"name": "empty-loads", "phase": "assembly", "load_types": []}
        errors = validate_event(event)
        self.assertTrue(any("non-empty" in e for e in errors))

    def test_blank_name_flagged(self):
        event = {"name": "   ", "phase": "assembly", "load_types": ["thermal"]}
        errors = validate_event(event)
        self.assertTrue(any("blank" in e for e in errors))

    def test_non_dict_event_flagged(self):
        errors = validate_event("not-a-dict")
        self.assertTrue(len(errors) > 0)

    def test_multiple_valid_load_types_accepted(self):
        event = {
            "name": "combined-test",
            "phase": "test",
            "load_types": ["quasi_static", "dynamic", "acoustic", "shock"],
        }
        self.assertEqual(validate_event(event), [])


class TestCategorizeEventsByPhase(unittest.TestCase):

    def test_events_grouped_by_phase(self):
        events = [
            {"name": "a", "phase": "assembly", "load_types": ["quasi_static"]},
            {"name": "b", "phase": "flight", "load_types": ["dynamic"]},
            {"name": "c", "phase": "assembly", "load_types": ["thermal"]},
        ]
        result = categorize_events_by_phase(events)
        self.assertEqual(len(result["assembly"]), 2)
        self.assertEqual(len(result["flight"]), 1)
        self.assertEqual(len(result["test"]), 0)
        self.assertEqual(len(result["ground_ops"]), 0)

    def test_events_with_invalid_phase_excluded(self):
        events = [
            {"name": "bad", "phase": "orbit", "load_types": ["dynamic"]},
            {"name": "good", "phase": "test", "load_types": ["thermal"]},
        ]
        result = categorize_events_by_phase(events)
        self.assertEqual(len(result["test"]), 1)
        self.assertNotIn("orbit", result)


class TestFindMissingPhases(unittest.TestCase):

    def test_all_phases_present_returns_empty_set(self):
        events = _full_event_set()
        self.assertEqual(find_missing_phases(events), set())

    def test_missing_test_phase_detected(self):
        events = [e for e in _full_event_set() if e["phase"] != "test"]
        missing = find_missing_phases(events)
        self.assertIn("test", missing)

    def test_missing_assembly_phase_detected(self):
        events = [e for e in _full_event_set() if e["phase"] != "assembly"]
        missing = find_missing_phases(events)
        self.assertIn("assembly", missing)

    def test_missing_ground_ops_phase_detected(self):
        events = [e for e in _full_event_set() if e["phase"] != "ground_ops"]
        missing = find_missing_phases(events)
        self.assertIn("ground_ops", missing)

    def test_empty_event_list_reports_all_phases_missing(self):
        missing = find_missing_phases([])
        self.assertEqual(missing, REQUIRED_PHASES)


class TestFindMissingFlightSubtypes(unittest.TestCase):

    def test_all_flight_subtypes_present_returns_empty_set(self):
        events = _full_event_set()
        self.assertEqual(find_missing_flight_subtypes(events), set())

    def test_missing_separation_subtype_detected(self):
        events = [e for e in _full_event_set() if "separation" not in e["name"]]
        missing = find_missing_flight_subtypes(events)
        self.assertIn("separation", missing)

    def test_no_flight_events_returns_all_subtypes_missing(self):
        events = [e for e in _full_event_set() if e["phase"] != "flight"]
        missing = find_missing_flight_subtypes(events)
        self.assertEqual(missing, MANDATORY_FLIGHT_SUBTYPES)

    def test_subtype_matching_is_case_insensitive(self):
        events = [
            {"name": "LAUNCH-phase", "phase": "flight", "load_types": ["quasi_static"]},
            {"name": "ASCENT-maxq", "phase": "flight", "load_types": ["dynamic"]},
            {"name": "ON_ORBIT-ops", "phase": "flight", "load_types": ["quasi_static"]},
            {"name": "SEPARATION-event", "phase": "flight", "load_types": ["shock"]},
        ]
        self.assertEqual(find_missing_flight_subtypes(events), set())


class TestIdentifyLoadEvents(unittest.TestCase):

    def test_full_valid_set_returns_valid_true(self):
        result = identify_load_events(_full_event_set())
        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_phases"], set())
        self.assertEqual(result["validation_errors"], [])

    def test_invalid_event_in_list_reduces_valid_count(self):
        events = _full_event_set() + [{"name": "bad", "phase": "UNKNOWN", "load_types": []}]
        result = identify_load_events(events)
        self.assertEqual(result["total_events"], len(events))
        self.assertEqual(result["valid_event_count"], len(events) - 1)
        self.assertFalse(result["valid"])

    def test_non_list_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            identify_load_events({"not": "a list"})

    def test_empty_list_reports_all_phases_missing(self):
        result = identify_load_events([])
        self.assertFalse(result["valid"])
        self.assertEqual(result["missing_phases"], REQUIRED_PHASES)
        self.assertEqual(result["total_events"], 0)

    def test_events_by_phase_keys_match_valid_phases(self):
        result = identify_load_events(_full_event_set())
        self.assertEqual(set(result["events_by_phase"].keys()), VALID_PHASES)

    def test_validation_error_index_maps_to_original_event(self):
        bad_event = {"name": "", "phase": "assembly", "load_types": ["quasi_static"]}
        events = [_full_event_set()[0], bad_event]
        result = identify_load_events(events)
        error_indices = [idx for idx, _ in result["validation_errors"]]
        self.assertIn(1, error_indices)

    def test_missing_phase_makes_result_invalid(self):
        events = [e for e in _full_event_set() if e["phase"] != "assembly"]
        result = identify_load_events(events)
        self.assertFalse(result["valid"])
        self.assertIn("assembly", result["missing_phases"])

    def test_missing_flight_subtypes_reported_in_result(self):
        events = [e for e in _full_event_set() if "ascent" not in e["name"]]
        result = identify_load_events(events)
        self.assertIn("ascent", result["missing_flight_subtypes"])

    def test_multiple_load_types_per_event_accepted(self):
        events = _full_event_set()
        events[1]["load_types"] = ["dynamic", "acoustic", "thermal"]
        result = identify_load_events(events)
        self.assertTrue(result["valid"])

    def test_all_valid_phases_represented_in_events_by_phase(self):
        result = identify_load_events(_full_event_set())
        for phase in VALID_PHASES:
            self.assertIn(phase, result["events_by_phase"])

    def test_total_events_count_matches_input_length(self):
        events = _full_event_set()
        result = identify_load_events(events)
        self.assertEqual(result["total_events"], len(events))


if __name__ == "__main__":
    unittest.main()
