#!/usr/bin/env python3
"""Gate 3 contract test: DO-297 IMA architecture allocation logic.

Exercises scripts/do297_logic.py (stdlib unittest, offline). Contract:
docs/harness-contract.md gate 3 - allocation of applications to
partitions with CPU, memory, and I/O budgets, contention flagging,
integrity and availability mapping, acceptance criteria generation, and
budget tolerance behavior.

Hand-computed analytic references:
- Severity mapping: catastrophic -> A, hazardous -> B, major -> C,
  minor -> D, no-effect -> E.
- Availability mapping: A -> class 1, C -> class 2, D -> class 3.
- Module IMA-1 with 100 CPU units, 1,000,000 bytes, 16 I/O ports.
- Applications FMS (A, class 1, 40/400000/6), ADIRU (B, class 1,
  30/300000/4), Display (C, class 2, 20/200000/3): totals 90 CPU,
  900,000 bytes, 13 ports. All dimensions fit, slack 10/100000/3.
- Over-budget case: FMS at 60 CPU makes the module total 110 CPU
  against a 100 budget; the contention report flags FMS (application
  issue, demanded 60, budget 100) and the cpu dimension (module issue,
  demanded 110, budget 100), and allocation raises ValueError.
- Exact-fit case: apps at 40/30/30 CPU sum to exactly 100, accepted
  within ALLOCATION_TOLERANCE = 1e-9.
- Acceptance criteria: exactly 6 deterministic statements, including a
  "module acceptance" resource-usage statement and an incremental
  certification credit statement.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import do297_logic as dq  # noqa: E402

MODULE = {"name": "IMA-1", "cpu_units": 100, "memory_bytes": 1_000_000,
          "io_ports": 16}

APPS = [
    {"name": "FMS", "integrity": "A", "availability": 1,
     "cpu_units": 40, "memory_bytes": 400_000, "io_ports": 6},
    {"name": "ADIRU", "integrity": "B", "availability": 1,
     "cpu_units": 30, "memory_bytes": 300_000, "io_ports": 4},
    {"name": "Display", "integrity": "C", "availability": 2,
     "cpu_units": 20, "memory_bytes": 200_000, "io_ports": 3},
]


class TestSeverityIntegrityMapping(unittest.TestCase):
    def test_severity_to_integrity(self):
        cases = {"catastrophic": "A", "hazardous": "B", "major": "C",
                 "minor": "D", "no-effect": "E"}
        for severity, level in cases.items():
            self.assertEqual(dq.severity_to_integrity(severity), level)

    def test_severity_to_integrity_case_insensitive(self):
        self.assertEqual(dq.severity_to_integrity("Catastrophic"), "A")

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            dq.severity_to_integrity("obscure")

    def test_availability_mapping(self):
        self.assertEqual(dq.availability_class("A"), 1)
        self.assertEqual(dq.availability_class("B"), 1)
        self.assertEqual(dq.availability_class("C"), 2)
        self.assertEqual(dq.availability_class("D"), 3)
        self.assertEqual(dq.availability_class("E"), 3)

    def test_unknown_integrity_raises(self):
        with self.assertRaises(ValueError):
            dq.availability_class("F")


class TestAllocationFitsBudgets(unittest.TestCase):
    def test_module_totals(self):
        cpu, mem, io = dq.resource_totals(APPS)
        self.assertAlmostEqual(cpu, 90.0, places=9)
        self.assertAlmostEqual(mem, 900_000.0, places=9)
        self.assertAlmostEqual(io, 13.0, places=9)

    def test_allocation_fits_budgets(self):
        result = dq.allocate_applications(MODULE, APPS)
        self.assertEqual(result["module"], "IMA-1")
        self.assertEqual(len(result["allocations"]), 3)
        cpu, mem, io = result["module_totals"]
        self.assertLessEqual(cpu, MODULE["cpu_units"])
        self.assertLessEqual(mem, MODULE["memory_bytes"])
        self.assertLessEqual(io, MODULE["io_ports"])
        # One partition per application by default.
        self.assertEqual(
            sorted(result["partition_budgets"].keys()),
            sorted("P-%s" % a["name"] for a in APPS),
        )
        # FMS partition budget equals its own demand.
        self.assertAlmostEqual(result["partition_budgets"]["P-FMS"][0], 40.0)

    def test_explicit_partition_grouping(self):
        grouped = {"FMS": "P-G1", "ADIRU": "P-G1", "Display": "P-G2"}
        result = dq.allocate_applications(MODULE, APPS, partitions=grouped)
        self.assertEqual(len(result["allocations"]), 3)
        cpu_g1 = result["partition_budgets"]["P-G1"][0]
        self.assertAlmostEqual(cpu_g1, 70.0)  # 40 + 30
        self.assertAlmostEqual(result["partition_budgets"]["P-G1"][1], 700_000.0)
        self.assertAlmostEqual(result["partition_budgets"]["P-G1"][2], 10.0)  # 6 + 4

    def test_exact_fit_within_tolerance(self):
        exact = [
            {"name": "A1", "integrity": "C", "availability": 2,
             "cpu_units": 40, "memory_bytes": 500_000, "io_ports": 8},
            {"name": "A2", "integrity": "D", "availability": 3,
             "cpu_units": 30, "memory_bytes": 300_000, "io_ports": 5},
            {"name": "A3", "integrity": "E", "availability": 3,
             "cpu_units": 30, "memory_bytes": 200_000, "io_ports": 3},
        ]
        # 40 + 30 + 30 = 100 CPU exactly at budget; accepted.
        result = dq.allocate_applications(MODULE, exact)
        self.assertAlmostEqual(result["module_totals"][0], 100.0)
        # A tiny excess within ALLOCATION_TOLERANCE is still accepted.
        near = [
            {"name": "B1", "integrity": "D", "availability": 3,
             "cpu_units": 40 + 5e-11, "memory_bytes": 500_000, "io_ports": 8},
            {"name": "B2", "integrity": "E", "availability": 3,
             "cpu_units": 30, "memory_bytes": 300_000, "io_ports": 5},
            {"name": "B3", "integrity": "C", "availability": 2,
             "cpu_units": 30, "memory_bytes": 200_000, "io_ports": 3},
        ]
        dq.allocate_applications(MODULE, near)  # must not raise


class TestContentionFlagsOverBudgetApp(unittest.TestCase):
    def test_contention_report_flags_over_budget_app(self):
        over = [
            {"name": "FMS", "integrity": "A", "availability": 1,
             "cpu_units": 60, "memory_bytes": 400_000, "io_ports": 6},
            {"name": "ADIRU", "integrity": "B", "availability": 1,
             "cpu_units": 30, "memory_bytes": 300_000, "io_ports": 4},
            {"name": "Display", "integrity": "C", "availability": 2,
             "cpu_units": 20, "memory_bytes": 200_000, "io_ports": 3},
        ]
        issues = dq.contention_report(MODULE, over)
        app_issues = [i for i in issues if i["kind"] == "application"]
        module_issues = [i for i in issues if i["kind"] == "module"]
        self.assertTrue(any(i["name"] == "FMS" for i in app_issues))
        fms = [i for i in app_issues if i["name"] == "FMS"][0]
        self.assertEqual(fms["resource"], "cpu")
        self.assertAlmostEqual(fms["demanded"], 60.0)
        self.assertAlmostEqual(fms["budget"], 100.0)
        self.assertTrue(
            any(i["resource"] == "cpu" and i["kind"] == "module"
                and abs(i["demanded"] - 110.0) < 1e-9 for i in module_issues)
        )

    def test_allocation_raises_when_over_budget(self):
        over = [
            {"name": "FMS", "integrity": "A", "availability": 1,
             "cpu_units": 60, "memory_bytes": 400_000, "io_ports": 6},
            {"name": "ADIRU", "integrity": "B", "availability": 1,
             "cpu_units": 30, "memory_bytes": 300_000, "io_ports": 4},
            {"name": "Display", "integrity": "C", "availability": 2,
             "cpu_units": 20, "memory_bytes": 200_000, "io_ports": 3},
        ]
        with self.assertRaises(ValueError) as ctx:
            dq.allocate_applications(MODULE, over)
        self.assertIn("FMS", str(ctx.exception))

    def test_clean_allocation_has_no_contention(self):
        self.assertEqual(dq.contention_report(MODULE, APPS), [])


class TestAcceptanceCriteria(unittest.TestCase):
    def test_criteria_present_and_deterministic(self):
        criteria = dq.acceptance_criteria(MODULE, APPS)
        self.assertEqual(len(criteria), 6)
        joined = "\n".join(criteria)
        self.assertIn("module acceptance", joined.lower())
        self.assertIn("incremental certification credit", joined)
        self.assertIn("resource usage", joined.lower())
        self.assertIn("IMA-1", joined)
        # Deterministic: same input, same output.
        self.assertEqual(criteria, dq.acceptance_criteria(MODULE, APPS))

    def test_criteria_reflect_integrity_and_availability(self):
        criteria = dq.acceptance_criteria(MODULE, APPS)
        joined = "\n".join(criteria)
        self.assertIn("A/B/C", joined)  # integrity levels present
        self.assertIn("1/2", joined)  # availability classes present


class TestDevelopmentAssuranceSteps(unittest.TestCase):
    def test_level_a_steps(self):
        steps = dq.development_assurance_steps("A")
        self.assertGreaterEqual(len(steps), 6)
        self.assertTrue(any("rigorous coverage" in s for s in steps))
        self.assertTrue(any("Liaise" in s for s in steps))

    def test_level_e_steps_minimal(self):
        steps = dq.development_assurance_steps("E")
        self.assertTrue(any("minimal activity" in s for s in steps))
        self.assertFalse(any("Liaise" in s for s in steps))

    def test_level_c_focused(self):
        steps = dq.development_assurance_steps("C")
        self.assertTrue(any("focused coverage" in s for s in steps))
        self.assertTrue(any("Liaise" in s for s in steps))

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            dq.development_assurance_steps("Z")


class TestValidation(unittest.TestCase):
    def test_invalid_module_rejected(self):
        with self.assertRaises(ValueError):
            dq.allocate_applications({"name": "X", "cpu_units": -1}, APPS)

    def test_invalid_application_rejected(self):
        bad = dict(APPS[0], availability=9)
        with self.assertRaises(ValueError):
            dq.allocate_applications(MODULE, [bad])

    def test_unassigned_application_rejected(self):
        with self.assertRaises(ValueError):
            dq.allocate_applications(MODULE, APPS, partitions={"P-1": ["FMS"]})


if __name__ == "__main__":
    unittest.main()
