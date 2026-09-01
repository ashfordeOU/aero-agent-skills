"""Contract test for ARP4754A configuration management logic.

Behavior contract (offline, deterministic, stdlib unittest):
  1. A complete trace map passes traceability closure.
  2. A requirement missing its verification mapping fails closure.
  3. Changing a safety-critical requirement classifies as a MAJOR change.
  4. Invalid input raises ValueError.

Run: python3 scripts/test_configuration_management.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from configuration_management_logic import (  # noqa: E402
    check_traceability_closure,
    change_impact_analysis,
    classify_change,
    create_baseline,
    identify_configuration_items,
    record_change,
)

DATE = "2026-09-02"


def complete_trace_map():
    """A closed trace map: two requirements, one derived, all mapped."""
    return {
        "requirements": {
            "REQ-101": {
                "design": ["DES-201"],
                "verification": ["TEST-301"],
                "analyses": ["AN-401"],
                "derived": False,
                "source": None,
                "safety_critical": True,
            },
            "REQ-102": {
                "design": ["DES-202", "DES-203"],
                "verification": ["TEST-302"],
                "analyses": [],
                "derived": True,
                "source": "REQ-101",
                "safety_critical": False,
            },
        }
    }


class TestTraceabilityClosure(unittest.TestCase):
    def test_complete_trace_map_passes_closure(self):
        result = check_traceability_closure(complete_trace_map())
        self.assertTrue(result["closed"])
        self.assertEqual(result["missing_design"], [])
        self.assertEqual(result["missing_verification"], [])
        self.assertEqual(result["missing_source"], [])

    def test_requirement_missing_verification_fails_closure(self):
        trace_map = complete_trace_map()
        del trace_map["requirements"]["REQ-101"]["verification"]
        result = check_traceability_closure(trace_map)
        self.assertFalse(result["closed"])
        self.assertEqual(result["missing_verification"], ["REQ-101"])
        self.assertEqual(result["missing_design"], [])

    def test_requirement_missing_design_fails_closure(self):
        trace_map = complete_trace_map()
        trace_map["requirements"]["REQ-102"]["design"] = []
        result = check_traceability_closure(trace_map)
        self.assertFalse(result["closed"])
        self.assertEqual(result["missing_design"], ["REQ-102"])

    def test_derived_requirement_without_source_fails_closure(self):
        trace_map = complete_trace_map()
        trace_map["requirements"]["REQ-102"]["source"] = None
        result = check_traceability_closure(trace_map)
        self.assertFalse(result["closed"])
        self.assertEqual(result["missing_source"], ["REQ-102"])


class TestChangeControl(unittest.TestCase):
    def test_safety_critical_change_classifies_major(self):
        change = {
            "id": "CR-001",
            "description": "Update REQ-101 braking authority limits",
            "affected": ["REQ-101"],  # REQ-101 is safety_critical
        }
        impact = change_impact_analysis(change, complete_trace_map())
        self.assertTrue(impact["safety_relevant"])
        self.assertEqual(impact["affected_requirements"], ["REQ-101"])
        self.assertEqual(impact["affected_design"], ["DES-201"])
        self.assertEqual(impact["affected_verification"], ["TEST-301"])
        self.assertEqual(impact["affected_analyses"], ["AN-401"])
        self.assertEqual(classify_change(impact, change), "major")

    def test_interface_change_classifies_major(self):
        change = {
            "id": "CR-002",
            "description": "Change ARINC 429 bus word allocation",
            "affected": ["DES-202"],
            "interfaces_changed": True,
        }
        impact = change_impact_analysis(change, complete_trace_map())
        self.assertEqual(impact["affected_requirements"], ["REQ-102"])
        self.assertEqual(classify_change(impact, change), "major")

    def test_certification_data_change_classifies_major(self):
        change = {
            "id": "CR-003",
            "description": "Update certification plan reference",
            "affected": ["REQ-102"],
            "certification_data_changed": True,
        }
        impact = change_impact_analysis(change, complete_trace_map())
        self.assertEqual(classify_change(impact, change), "major")

    def test_non_safety_change_classifies_minor(self):
        change = {
            "id": "CR-004",
            "description": "Clarify wording of REQ-102 note",
            "affected": ["REQ-102"],
        }
        impact = change_impact_analysis(change, complete_trace_map())
        self.assertFalse(impact["safety_relevant"])
        self.assertEqual(classify_change(impact, change), "minor")

    def test_design_element_change_expands_through_trace_map(self):
        change = {"id": "CR-005", "affected": ["TEST-302"]}
        impact = change_impact_analysis(change, complete_trace_map())
        # TEST-302 is REQ-102's verification method; REQ-102 is derived
        # from REQ-101, but impact covers only directly-linked items.
        self.assertEqual(impact["affected_requirements"], ["REQ-102"])


class TestBaseline(unittest.TestCase):
    def test_baseline_snapshot_has_version_and_sorted_items(self):
        baseline = create_baseline(
            [
                {"id": "REQ-101", "type": "requirement", "version": "2.1"},
                {"id": "DES-201", "type": "design"},
                {"id": "TEST-301", "type": "verification"},
                {"id": "AN-401", "type": "analysis"},
            ],
            name="FCS Baseline",
            version="2.0",
            baseline_id="B-2",
            created=DATE,
        )
        self.assertEqual(baseline["baseline_id"], "B-2")
        self.assertEqual(baseline["name"], "FCS Baseline")
        self.assertEqual(baseline["version"], "2.0")
        self.assertEqual(baseline["created"], DATE)
        self.assertEqual(baseline["item_count"], 4)
        self.assertEqual([i["id"] for i in baseline["items"]], ["AN-401", "DES-201", "REQ-101", "TEST-301"])
        self.assertEqual(baseline["items"][2]["version"], "2.1")

    def test_identify_configuration_items(self):
        data = {
            "requirement": ["REQ-101", "REQ-102"],
            "design": ["DES-201"],
            "verification": ["TEST-301"],
            "analysis": ["AN-401"],
            "meeting_minutes": ["MIN-001"],  # not a configuration item
        }
        items = identify_configuration_items(data)
        self.assertEqual(len(items), 5)
        self.assertTrue(all(i["type"] != "meeting_minutes" for i in items))
        self.assertEqual(items[0]["id"], "AN-401")


class TestChangeHistory(unittest.TestCase):
    def test_record_change_appends_to_history(self):
        history = []
        change = {
            "id": "CR-001",
            "description": "Update REQ-101 braking authority limits",
            "classification": "major",
            "status": "APPROVED",
        }
        record = record_change(change, history, date=DATE)
        self.assertEqual(record["record_id"], 1)
        self.assertEqual(record["change_id"], "CR-001")
        self.assertEqual(record["classification"], "major")
        self.assertEqual(record["status"], "APPROVED")
        self.assertEqual(record["date"], DATE)
        self.assertEqual(len(history), 1)
        second = record_change({"id": "CR-002"}, history, date=DATE)
        self.assertEqual(second["record_id"], 2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["change_id"], "CR-001")

    def test_record_change_creates_history_when_none(self):
        record = record_change({"id": "CR-010"}, date=DATE)
        self.assertEqual(record["record_id"], 1)
        self.assertEqual(record["status"], "SUBMITTED")


class TestInvalidInput(unittest.TestCase):
    def test_invalid_input_raises_value_error(self):
        bad_calls = [
            # create_baseline
            lambda: create_baseline([]),
            lambda: create_baseline("REQ-101"),
            lambda: create_baseline([{"version": "1.0"}]),  # missing id
            lambda: create_baseline([{"id": "X", "type": "note"}]),
            # check_traceability_closure
            lambda: check_traceability_closure(None),
            lambda: check_traceability_closure({"requirements": "nope"}),
            lambda: check_traceability_closure({"requirements": {"R1": "not a dict"}}),
            # change_impact_analysis
            lambda: change_impact_analysis({}, complete_trace_map()),  # no id
            lambda: change_impact_analysis({"id": "CR-9"}, complete_trace_map()),  # no affected
            lambda: change_impact_analysis({"id": "CR-9", "affected": []}, complete_trace_map()),
            lambda: change_impact_analysis({"id": "CR-9", "affected": ["R1"]}, {}),  # no trace_map
            lambda: change_impact_analysis({"id": "CR-9", "affected": ["R1"]}, {"requirements": {"R1": []}}),
            # classify_change
            lambda: classify_change(None),
            lambda: classify_change({"safety_relevant": False}, "CR-1"),
            # record_change
            lambda: record_change({}),
            lambda: record_change({"id": "CR-1"}, history="not-a-list"),
            lambda: record_change({"id": "CR-1", "status": "NOPE"}),
            # identify_configuration_items
            lambda: identify_configuration_items(["REQ-101"]),
            lambda: identify_configuration_items({"design": "DES-201"}),
        ]
        for call in bad_calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()


if __name__ == "__main__":
    unittest.main(verbosity=2)
