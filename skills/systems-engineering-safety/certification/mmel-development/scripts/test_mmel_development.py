"""Contract test for the MMEL development logic (offline, deterministic).

Run: python3 scripts/test_mmel_development.py
Covers the spec worked-example anchors (YD-1 yaw damper, FCS-1 primary
flight computer, ENT-1 cabin entertainment, the brake safety-function
pair), the eligibility branches, interval categories per severity and
redundancy, the O/M/placard flag rules, the interaction group logic,
the proposal verdict branches and the ValueError rejections.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mmel_development_logic import (  # noqa: E402
    INTERVAL_DAYS,
    CATEGORIES,
    eligibility,
    interval_category,
    o_m_flags,
    interaction_check,
    build_mmel_proposal,
    proposal_verdict,
    group_of,
    interval_days,
)


def item(**overrides):
    """Build a valid item dict; override any field for the case at hand."""
    base = {
        "item_id": "IT-1",
        "name": "test item",
        "function": "test function",
        "severity_if_inoperative": "minor",
        "redundancy": "dual",
        "safety_function": False,
        "crew_action_available": False,
        "maintenance_required": False,
        "placard_required": False,
    }
    base.update(overrides)
    return base


def yd1_item():
    return item(item_id="YD-1", name="yaw damper", function="dutch roll damping",
                severity_if_inoperative="hazardous", redundancy="dual",
                safety_function=False, crew_action_available=True,
                maintenance_required=True, placard_required=True)


def ent1_item():
    return item(item_id="ENT-1", name="cabin entertainment",
                function="passenger media", severity_if_inoperative="minor",
                redundancy="single-string")


def brake_item(item_id, safety=True):
    return item(item_id=item_id, name="brake system %s" % item_id,
                severity_if_inoperative="major", redundancy="dual",
                safety_function=safety)


class TestEligibility(unittest.TestCase):
    def test_hazardous_single_string_not_eligible(self):
        ok, reason = eligibility(item(severity_if_inoperative="hazardous",
                                     redundancy="single-string"))
        self.assertFalse(ok)
        self.assertIn("single-string", reason)

    def test_catastrophic_single_string_not_eligible(self):
        ok, reason = eligibility(item(severity_if_inoperative="catastrophic",
                                     redundancy="single-string"))
        self.assertFalse(ok)
        self.assertIn("single-string", reason)

    def test_mitigation_item_not_eligible(self):
        for severity in ("hazardous", "catastrophic"):
            ok, reason = eligibility(item(severity_if_inoperative=severity,
                                         redundancy="dual",
                                         safety_function=True))
            self.assertFalse(ok)
            self.assertIn("mitigation", reason)

    def test_redundant_non_mitigation_eligible(self):
        ok, reason = eligibility(item(severity_if_inoperative="hazardous",
                                     redundancy="dual",
                                     safety_function=False))
        self.assertTrue(ok)
        self.assertIn("redundancy", reason)
        ok, _reason = eligibility(item(severity_if_inoperative="catastrophic",
                                       redundancy="multi",
                                       safety_function=False))
        self.assertTrue(ok)

    def test_low_severity_eligible(self):
        for severity in ("major", "minor", "none"):
            ok, _reason = eligibility(item(severity_if_inoperative=severity,
                                           redundancy="single-string"))
            self.assertTrue(ok)


class TestIntervalCategory(unittest.TestCase):
    def test_none_and_convenience_minor_category_d(self):
        category, _reason = interval_category(item(
            severity_if_inoperative="none", redundancy="dual"))
        self.assertEqual(category, "D")
        category, _reason = interval_category(ent1_item())
        self.assertEqual(category, "D")

    def test_minor_crew_or_redundant_category_d(self):
        category, _reason = interval_category(item(
            severity_if_inoperative="minor", redundancy="single-string",
            crew_action_available=True))
        self.assertEqual(category, "D")
        category, _reason = interval_category(item(
            severity_if_inoperative="minor", redundancy="dual"))
        self.assertEqual(category, "D")

    def test_minor_single_string_flight_relevant_category_c(self):
        category, _reason = interval_category(item(
            item_id="YD-2", name="yaw damper indicator",
            severity_if_inoperative="minor", redundancy="single-string"))
        self.assertEqual(category, "C")

    def test_major_redundant_category_c(self):
        category, _reason = interval_category(item(
            severity_if_inoperative="major", redundancy="dual"))
        self.assertEqual(category, "C")

    def test_major_single_string_crew_action_category_b(self):
        category, _reason = interval_category(item(
            severity_if_inoperative="major", redundancy="single-string",
            crew_action_available=True))
        self.assertEqual(category, "B")

    def test_major_single_string_no_crew_category_a(self):
        category, _reason = interval_category(item(
            severity_if_inoperative="major", redundancy="single-string",
            crew_action_available=False))
        self.assertEqual(category, "A")

    def test_hazardous_and_catastrophic_redundant_categories(self):
        category, _reason = interval_category(item(
            severity_if_inoperative="hazardous", redundancy="dual"))
        self.assertEqual(category, "B")
        category, _reason = interval_category(item(
            severity_if_inoperative="catastrophic", redundancy="multi"))
        self.assertEqual(category, "A")

    def test_not_eligible_item_raises_value_error(self):
        with self.assertRaises(ValueError):
            interval_category(item(severity_if_inoperative="catastrophic",
                                   redundancy="single-string"))

    def test_interval_days_table(self):
        self.assertEqual(INTERVAL_DAYS,
                         {"A": 3, "B": 10, "C": 120, "D": None})
        self.assertEqual(CATEGORIES, ("A", "B", "C", "D"))
        self.assertEqual(interval_days("B"), 10)
        self.assertIsNone(interval_days("D"))
        with self.assertRaises(ValueError):
            interval_days("E")


class TestOMFlags(unittest.TestCase):
    def test_o_flag_triggers(self):
        o, _m, _p = o_m_flags(item(crew_action_available=True), "C")
        self.assertTrue(o)
        o, _m, _p = o_m_flags(item(crew_action_available=False), "B")
        self.assertTrue(o)
        o, _m, _p = o_m_flags(item(safety_function=True), "C")
        self.assertTrue(o)

    def test_m_flag_triggers(self):
        _o, m, _p = o_m_flags(item(maintenance_required=True), "C")
        self.assertTrue(m)
        _o, m, _p = o_m_flags(item(maintenance_required=False), "A")
        self.assertTrue(m)
        _o, m, _p = o_m_flags(item(severity_if_inoperative="hazardous",
                                   redundancy="dual",
                                   maintenance_required=False), "B")
        self.assertTrue(m)

    def test_placard_triggers(self):
        _o, _m, p = o_m_flags(item(placard_required=True), "D")
        self.assertTrue(p)
        _o, _m, p = o_m_flags(item(placard_required=False), "A")
        self.assertTrue(p)

    def test_entertainment_anchor_no_flags(self):
        o, m, p = o_m_flags(ent1_item(), "D")
        self.assertFalse(o)
        self.assertFalse(m)
        self.assertFalse(p)

    def test_yaw_damper_anchor_flags(self):
        o, m, p = o_m_flags(yd1_item(), "B")
        self.assertTrue(o)
        self.assertTrue(m)
        self.assertTrue(p)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            o_m_flags(item(), "E")


class TestInteractionCheck(unittest.TestCase):
    def test_double_relief_brake_pair_raises_issue(self):
        issues = interaction_check([brake_item("BRK-1"), brake_item("BRK-2")])
        self.assertTrue(any("double-relief" in i for i in issues))
        self.assertTrue(any("brake" in i for i in issues))

    def test_single_safety_function_pair_no_double_relief(self):
        issues = interaction_check([brake_item("BRK-1", safety=True),
                                    brake_item("BRK-2", safety=False)])
        self.assertFalse(any("double-relief" in i for i in issues))

    def test_different_groups_no_issue(self):
        yaw = item(item_id="YD-1", name="yaw damper", safety_function=True)
        issues = interaction_check([yaw, brake_item("BRK-1")])
        self.assertEqual(issues, [])

    def test_more_than_max_shared_group_raises_issue(self):
        issues = interaction_check([brake_item("B1", safety=False),
                                    brake_item("B2", safety=False),
                                    brake_item("B3", safety=False)])
        self.assertTrue(any("max 1" in i for i in issues))
        issues = interaction_check([brake_item("B1", safety=False),
                                    brake_item("B2", safety=False)],
                                   allowed_combination_max=2)
        self.assertEqual(issues, [])

    def test_group_of_keyword_detection(self):
        self.assertEqual(group_of("yaw damper"), "yaw")
        self.assertEqual(group_of("brake system channel 1"), "brake")
        self.assertEqual(group_of("Flight Guidance computer"), "flight-guidance")
        self.assertIsNone(group_of("cabin entertainment"))


class TestProposalBuildAndVerdict(unittest.TestCase):
    def test_worked_example_mixed_proposal(self):
        fcs1 = item(item_id="FCS-1", name="primary flight computer",
                    function="flight control",
                    severity_if_inoperative="catastrophic",
                    redundancy="single-string", maintenance_required=True)
        proposal = build_mmel_proposal([yd1_item(), fcs1, ent1_item()])
        self.assertEqual(proposal["rows"], [
            {"item_id": "YD-1", "category": "B", "o_flag": True,
             "m_flag": True, "placard": True, "eligible": True},
            {"item_id": "ENT-1", "category": "D", "o_flag": False,
             "m_flag": False, "placard": False, "eligible": True}])
        self.assertEqual([f["item_id"] for f in proposal["forbidden"]],
                         ["FCS-1"])
        self.assertIn("single-string", proposal["forbidden"][0]["reason"])
        self.assertEqual(proposal["issues"], [])
        self.assertEqual(proposal_verdict(proposal), ("PASS", []))

    def test_brake_safety_pair_fails_verdict(self):
        proposal = build_mmel_proposal([brake_item("BRK-1"),
                                        brake_item("BRK-2")])
        self.assertEqual(len(proposal["rows"]), 2)
        self.assertTrue(proposal["issues"])
        verdict, reasons = proposal_verdict(proposal)
        self.assertEqual(verdict, "FAIL")
        self.assertTrue(any("double-relief" in r for r in reasons))

    def test_verdict_fails_on_missing_o_for_category_a(self):
        proposal = {"rows": [{"item_id": "X-1", "category": "A",
                              "o_flag": False, "m_flag": True,
                              "placard": True, "eligible": True}],
                    "forbidden": [], "issues": []}
        verdict, reasons = proposal_verdict(proposal)
        self.assertEqual(verdict, "FAIL")
        self.assertTrue(any("operating procedure" in r for r in reasons))

    def test_verdict_fails_on_hazardous_single_string_row(self):
        proposal = {"rows": [{"item_id": "X-2", "category": "A",
                              "o_flag": True, "m_flag": True,
                              "placard": True, "eligible": True,
                              "severity_if_inoperative": "hazardous",
                              "redundancy": "single-string"}],
                    "forbidden": [], "issues": []}
        self.assertEqual(proposal_verdict(proposal)[0], "FAIL")

    def test_verdict_passes_clean_proposal(self):
        proposal = {"rows": [{"item_id": "X-3", "category": "C",
                              "o_flag": False, "m_flag": False,
                              "placard": False, "eligible": True}],
                    "forbidden": [], "issues": []}
        self.assertEqual(proposal_verdict(proposal), ("PASS", []))

    def test_repeated_build_is_deterministic(self):
        items = [yd1_item(), ent1_item()]
        self.assertEqual(build_mmel_proposal(items),
                         build_mmel_proposal(items))


class TestValueErrors(unittest.TestCase):
    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            eligibility(item(severity_if_inoperative="very-bad"))
        with self.assertRaises(ValueError):
            build_mmel_proposal([item(severity_if_inoperative="very-bad")])

    def test_unknown_redundancy_raises(self):
        with self.assertRaises(ValueError):
            interval_category(item(redundancy="quad"))

    def test_empty_or_non_list_item_input_raises(self):
        with self.assertRaises(ValueError):
            build_mmel_proposal([])
        with self.assertRaises(ValueError):
            build_mmel_proposal({"item_id": "X"})

    def test_missing_required_key_raises(self):
        bad = item()
        del bad["function"]
        with self.assertRaises(ValueError):
            eligibility(bad)
        with self.assertRaises(ValueError):
            build_mmel_proposal([bad])


if __name__ == "__main__":
    unittest.main()
