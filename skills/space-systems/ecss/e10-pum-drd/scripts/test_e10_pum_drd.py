#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-pum-drd (stdlib unittest, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_pum_drd_logic import (  # noqa: E402
    HAZARD_CLASSES, REQUIRED_SECTIONS, configuration_violations,
    hazard_warning_violations, is_pum_deliverable, maintenance_violations,
    missing_sections, pum_review, step_numbering_violations,
    validate_hazard_class,
)

CFG = "RW-100 Build 3"


def sections(**over):
    s = {name: "text for %s" % name for name in REQUIRED_SECTIONS}
    s.update(over)
    return s


def procedure():
    return {"procedure_id": "OPS-1", "steps": [
        {"number": 1, "hazard": None, "warning_before": False},
        {"number": 2, "hazard": "pressure", "warning_before": True},
        {"number": 3, "hazard": None, "warning_before": False}]}


def manual(**over):
    m = {"configuration": CFG, "sections": sections(),
         "procedures": [procedure()],
         "maintenance_tasks": [{"task_id": "M1", "interval": "12 months",
                                "resources": ["torque wrench"]}]}
    m.update(over)
    return m


class HazardTest(unittest.TestCase):
    def test_every_hazard_class_validates(self):
        for h in HAZARD_CLASSES:
            self.assertEqual(validate_hazard_class(h), h)

    def test_unknown_hazard_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard_class("spooky")


class SectionTest(unittest.TestCase):
    def test_complete_manual_has_no_missing_sections(self):
        self.assertEqual(missing_sections(manual()), [])

    def test_absent_section_is_reported(self):
        s = sections()
        del s["safety"]
        self.assertEqual(missing_sections({"sections": s}), ["safety"])

    def test_empty_section_is_the_same_defect_as_an_absent_one(self):
        self.assertEqual(missing_sections({"sections": sections(safety="   ")}),
                         ["safety"])

    def test_sections_reported_in_declared_order(self):
        s = sections()
        del s["handling"]
        del s["product_description"]
        self.assertEqual(missing_sections({"sections": s}),
                         ["product_description", "handling"])


class ConfigurationTest(unittest.TestCase):
    def test_matching_configuration_is_clean(self):
        self.assertEqual(configuration_violations(manual(), CFG), [])

    def test_absent_configuration_is_reported(self):
        f = configuration_violations({"configuration": ""}, CFG)
        self.assertEqual(f[0]["issue"], "no_declared_configuration")

    def test_mismatched_configuration_is_reported(self):
        f = configuration_violations(manual(), "RW-100 Build 4")
        self.assertEqual(f[0]["issue"], "configuration_mismatch")
        self.assertEqual(f[0]["declared"], CFG)


class StepTest(unittest.TestCase):
    def test_contiguous_numbering_is_clean(self):
        self.assertEqual(step_numbering_violations(procedure()["steps"]), [])

    def test_duplicate_step_number_is_reported(self):
        steps = procedure()["steps"]
        steps[2]["number"] = 2
        issues = [f["issue"] for f in step_numbering_violations(steps)]
        self.assertIn("duplicate_step_number", issues)

    def test_gap_in_numbering_is_reported(self):
        steps = procedure()["steps"]
        steps[2]["number"] = 9
        issues = [f["issue"] for f in step_numbering_violations(steps)]
        self.assertIn("step_numbering_not_contiguous", issues)

    def test_empty_procedure_has_no_numbering_findings(self):
        self.assertEqual(step_numbering_violations([]), [])


class WarningTest(unittest.TestCase):
    def test_hazard_warned_before_the_step_is_clean(self):
        self.assertEqual(hazard_warning_violations(procedure()), [])

    def test_hazard_without_a_preceding_warning_is_reported(self):
        p = procedure()
        p["steps"][1]["warning_before"] = False
        f = hazard_warning_violations(p)
        self.assertEqual(f[0]["issue"], "hazard_warning_not_before_step")
        self.assertEqual(f[0]["number"], 2)

    def test_non_hazardous_step_needs_no_warning(self):
        p = {"procedure_id": "X", "steps": [
            {"number": 1, "hazard": None, "warning_before": False}]}
        self.assertEqual(hazard_warning_violations(p), [])

    def test_unknown_hazard_class_raises(self):
        p = procedure()
        p["steps"][1]["hazard"] = "vibes"
        with self.assertRaises(ValueError):
            hazard_warning_violations(p)


class MaintenanceTest(unittest.TestCase):
    def test_complete_task_is_clean(self):
        self.assertEqual(maintenance_violations(manual()["maintenance_tasks"]), [])

    def test_task_without_interval_is_reported(self):
        f = maintenance_violations([{"task_id": "M1", "interval": "",
                                     "resources": ["x"]}])
        self.assertEqual(f[0]["issue"], "no_maintenance_interval")

    def test_task_without_resources_is_reported(self):
        f = maintenance_violations([{"task_id": "M1", "interval": "6 months",
                                     "resources": []}])
        self.assertEqual(f[0]["issue"], "no_required_resources")

    def test_task_without_id_raises(self):
        with self.assertRaises(ValueError):
            maintenance_violations([{"interval": "6 months", "resources": ["x"]}])


class ReviewTest(unittest.TestCase):
    def test_complete_manual_is_deliverable(self):
        r = pum_review(manual(), CFG)
        self.assertEqual(r["configuration"], CFG)
        self.assertTrue(is_pum_deliverable(r))

    def test_configuration_mismatch_blocks_delivery(self):
        self.assertFalse(is_pum_deliverable(pum_review(manual(), "OTHER")))

    def test_missing_section_blocks_delivery(self):
        s = sections()
        del s["limitations"]
        self.assertFalse(is_pum_deliverable(pum_review(manual(sections=s), CFG)))

    def test_numbering_finding_carries_its_procedure_id(self):
        p = procedure()
        p["steps"][2]["number"] = 2
        r = pum_review(manual(procedures=[p]), CFG)
        nf = [f for f in r["findings"] if f["issue"] == "duplicate_step_number"]
        self.assertEqual(nf[0]["procedure_id"], "OPS-1")

    def test_review_does_not_mutate_input(self):
        m = manual()
        before = copy.deepcopy(m)
        pum_review(m, CFG)
        self.assertEqual(m, before)


if __name__ == "__main__":
    unittest.main()
