#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.5.5 equipment
electrical/RF tests.

Exercises scripts/e1003_eq_electrical_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - equipment with
no electrical interfaces is not applicable for the whole 5.5.5 set;
EMC is always applicable once electrical interfaces exist while the
other five tests follow their own risk/requirement flag; an
applicable test with no recorded result is 'missing', distinct from
'not_applicable' and 'failed'; one failed test fails the equipment
item's overall status regardless of other results; and campaign
closure requires every equipment item in the set to be dispositioned
and complete.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_electrical_logic as elec  # noqa: E402


class DetermineApplicabilityTest(unittest.TestCase):
    def test_no_electrical_interfaces_is_out_of_scope(self):
        equipment = {"id": "EQ-001", "has_electrical_interfaces": False}
        result = elec.determine_applicability(equipment)
        self.assertEqual(result, {test: False for test in elec.TEST_TYPES})

    def test_electrical_equipment_always_needs_emc(self):
        equipment = {"id": "EQ-002", "has_electrical_interfaces": True}
        result = elec.determine_applicability(equipment)
        self.assertTrue(result["emc"])
        self.assertFalse(result["magnetic"])
        self.assertFalse(result["esd"])
        self.assertFalse(result["pim"])
        self.assertFalse(result["multipactor"])
        self.assertFalse(result["corona_arc"])

    def test_flags_drive_the_other_five_tests(self):
        equipment = {
            "id": "EQ-003",
            "has_electrical_interfaces": True,
            "magnetic_cleanliness_required": True,
            "esd_susceptible": True,
            "pim_risk_present": True,
            "multipactor_risk_present": True,
            "corona_arc_risk_present": True,
        }
        result = elec.determine_applicability(equipment)
        self.assertTrue(all(result.values()))


class TestStatusTest(unittest.TestCase):
    def test_not_applicable_when_not_applicable(self):
        self.assertEqual(elec.test_status(False, None), "not_applicable")

    def test_not_applicable_ignores_a_result(self):
        self.assertEqual(elec.test_status(False, "passed"), "not_applicable")

    def test_missing_when_applicable_with_no_result(self):
        self.assertEqual(elec.test_status(True, None), "missing")

    def test_passed_result_passes_through(self):
        self.assertEqual(elec.test_status(True, "passed"), "passed")

    def test_failed_result_passes_through(self):
        self.assertEqual(elec.test_status(True, "failed"), "failed")

    def test_unknown_result_raises(self):
        with self.assertRaises(ValueError):
            elec.test_status(True, "inconclusive")


class RollUpOverallStatusTest(unittest.TestCase):
    def test_all_passed_is_complete(self):
        statuses = {test: "passed" for test in elec.TEST_TYPES}
        self.assertEqual(elec.roll_up_overall_status(statuses), "complete")

    def test_not_applicable_tests_do_not_block_complete(self):
        statuses = {test: "not_applicable" for test in elec.TEST_TYPES}
        statuses["emc"] = "passed"
        self.assertEqual(elec.roll_up_overall_status(statuses), "complete")

    def test_missing_test_is_incomplete(self):
        statuses = {test: "passed" for test in elec.TEST_TYPES}
        statuses["esd"] = "missing"
        self.assertEqual(elec.roll_up_overall_status(statuses), "incomplete")

    def test_failed_test_fails_even_with_others_passed(self):
        statuses = {test: "passed" for test in elec.TEST_TYPES}
        statuses["pim"] = "failed"
        self.assertEqual(elec.roll_up_overall_status(statuses), "failed")

    def test_failed_beats_missing(self):
        statuses = {test: "passed" for test in elec.TEST_TYPES}
        statuses["pim"] = "failed"
        statuses["esd"] = "missing"
        self.assertEqual(elec.roll_up_overall_status(statuses), "failed")


class DispositionEquipmentTest(unittest.TestCase):
    EQUIPMENT = {
        "id": "EQ-010",
        "has_electrical_interfaces": True,
        "magnetic_cleanliness_required": False,
        "esd_susceptible": True,
        "pim_risk_present": False,
        "multipactor_risk_present": False,
        "corona_arc_risk_present": False,
    }

    def test_complete_when_all_applicable_tests_pass(self):
        results = {"emc": "passed", "esd": "passed"}
        result = elec.disposition_equipment(self.EQUIPMENT, results)
        self.assertEqual(result["id"], "EQ-010")
        self.assertEqual(result["overall"], "complete")
        self.assertEqual(result["tests"]["magnetic"], "not_applicable")
        self.assertEqual(result["tests"]["emc"], "passed")
        self.assertEqual(result["tests"]["esd"], "passed")

    def test_missing_result_makes_it_incomplete(self):
        results = {"emc": "passed"}
        result = elec.disposition_equipment(self.EQUIPMENT, results)
        self.assertEqual(result["tests"]["esd"], "missing")
        self.assertEqual(result["overall"], "incomplete")

    def test_failed_result_makes_it_failed(self):
        results = {"emc": "passed", "esd": "failed"}
        result = elec.disposition_equipment(self.EQUIPMENT, results)
        self.assertEqual(result["overall"], "failed")

    def test_no_electrical_interfaces_is_complete_with_nothing_applicable(self):
        equipment = {"id": "EQ-011", "has_electrical_interfaces": False}
        result = elec.disposition_equipment(equipment, {})
        self.assertTrue(all(v == "not_applicable" for v in result["tests"].values()))
        self.assertEqual(result["overall"], "complete")

    def test_missing_id_raises(self):
        equipment = dict(self.EQUIPMENT)
        del equipment["id"]
        with self.assertRaises(ValueError):
            elec.disposition_equipment(equipment, {})


class BuildCampaignDispositionTest(unittest.TestCase):
    EQUIPMENT_LIST = [
        {
            "id": "EQ-020",
            "has_electrical_interfaces": True,
            "pim_risk_present": True,
        },
        {
            "id": "EQ-021",
            "has_electrical_interfaces": True,
        },
    ]

    def test_disposition_order_and_content(self):
        results_by_id = {
            "EQ-020": {"emc": "passed", "pim": "passed"},
            "EQ-021": {"emc": "passed"},
        }
        result = elec.build_campaign_disposition(self.EQUIPMENT_LIST, results_by_id)
        self.assertEqual(result[0]["id"], "EQ-020")
        self.assertEqual(result[0]["overall"], "complete")
        self.assertEqual(result[1]["id"], "EQ-021")
        self.assertEqual(result[1]["overall"], "complete")

    def test_missing_results_entry_treated_as_no_results(self):
        result = elec.build_campaign_disposition(self.EQUIPMENT_LIST, {})
        self.assertEqual(result[0]["overall"], "incomplete")
        self.assertEqual(result[0]["tests"]["emc"], "missing")

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            elec.build_campaign_disposition(
                self.EQUIPMENT_LIST + [self.EQUIPMENT_LIST[0]], {}
            )

    def test_does_not_mutate_input(self):
        before = [dict(e) for e in self.EQUIPMENT_LIST]
        elec.build_campaign_disposition(self.EQUIPMENT_LIST, {})
        self.assertEqual(self.EQUIPMENT_LIST, before)


class MissingDispositionsTest(unittest.TestCase):
    def test_detects_gap(self):
        dispositions = [{"id": "EQ-020", "tests": {}, "overall": "complete"}]
        self.assertEqual(
            elec.missing_dispositions(["EQ-020", "EQ-021", "EQ-022"], dispositions),
            ["EQ-021", "EQ-022"],
        )

    def test_no_gap(self):
        dispositions = [{"id": "EQ-020", "tests": {}, "overall": "complete"}]
        self.assertEqual(elec.missing_dispositions(["EQ-020"], dispositions), [])


class CloseOutCampaignTest(unittest.TestCase):
    def test_all_complete_closes_clean(self):
        dispositions = [
            {"id": "EQ-020", "tests": {}, "overall": "complete"},
            {"id": "EQ-021", "tests": {}, "overall": "complete"},
        ]
        self.assertEqual(elec.close_out_campaign(dispositions), (True, []))

    def test_open_items_block_closure(self):
        dispositions = [
            {"id": "EQ-020", "tests": {}, "overall": "complete"},
            {"id": "EQ-021", "tests": {}, "overall": "failed"},
        ]
        self.assertEqual(
            elec.close_out_campaign(dispositions),
            (False, [{"id": "EQ-021", "overall": "failed"}]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
