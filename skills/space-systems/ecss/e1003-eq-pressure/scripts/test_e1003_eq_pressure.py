#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.5.3 equipment
structural-integrity-under-pressure tests.

Exercises scripts/e1003_eq_pressure_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - required tests
are derived from pressurization, cyclic service and campaign, with the
burst-margin check selected by article disposition (dedicated
qualification article -> physical burst; flight article -> design
burst analysis); a physical burst test and a design burst analysis
never both appear on one article; a physical burst test, being
destructive, must always be the last test performed; each test type
evaluates pass/fail against its own rule; and an item's pressure-test
set is only reported complete when every required test is closed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_pressure_logic as pl  # noqa: E402


class RequiredTestsTest(unittest.TestCase):
    def test_non_pressurized_has_no_tests(self):
        self.assertEqual(
            pl.required_tests("qualification", False, True, "flight"),
            (),
        )

    def test_pressurized_flight_non_cyclic_gets_leak_proof_design_burst(self):
        self.assertEqual(
            pl.required_tests("acceptance", True, False, "flight"),
            ("leak", "proof_pressure", "design_burst"),
        )

    def test_pressurized_flight_cyclic_adds_pressure_cycling(self):
        self.assertEqual(
            pl.required_tests("protoflight", True, True, "flight"),
            ("leak", "proof_pressure", "pressure_cycling", "design_burst"),
        )

    def test_dedicated_qualification_article_gets_physical_burst(self):
        self.assertEqual(
            pl.required_tests("qualification", True, True, "dedicated_qualification"),
            ("leak", "proof_pressure", "pressure_cycling", "burst"),
        )

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            pl.required_tests("proto", True, False, "flight")

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            pl.required_tests("qualification", True, False, "spare")


class ValidateSequenceTest(unittest.TestCase):
    def test_valid_sequence_with_burst_last_returns_true(self):
        self.assertTrue(
            pl.validate_sequence(["leak", "proof_pressure", "pressure_cycling", "burst"])
        )

    def test_valid_sequence_without_burst_returns_true(self):
        self.assertTrue(pl.validate_sequence(["leak", "proof_pressure", "design_burst"]))

    def test_burst_not_last_raises(self):
        with self.assertRaises(ValueError):
            pl.validate_sequence(["burst", "leak"])

    def test_burst_and_design_burst_together_raises(self):
        with self.assertRaises(ValueError):
            pl.validate_sequence(["leak", "design_burst", "burst"])

    def test_unknown_test_type_raises(self):
        with self.assertRaises(ValueError):
            pl.validate_sequence(["leak", "vacuum_soak"])


class EvaluateLeafFunctionsTest(unittest.TestCase):
    def test_leak_passes_at_or_under_max(self):
        self.assertTrue(pl.evaluate_leak(0.5, 1.0))
        self.assertTrue(pl.evaluate_leak(1.0, 1.0))
        self.assertFalse(pl.evaluate_leak(1.1, 1.0))

    def test_proof_pressure_requires_level_and_no_anomaly(self):
        self.assertTrue(pl.evaluate_proof_pressure(1.5, 1.5, False))
        self.assertFalse(pl.evaluate_proof_pressure(1.4, 1.5, False))
        self.assertFalse(pl.evaluate_proof_pressure(1.5, 1.5, True))

    def test_pressure_cycling_requires_cycles_and_no_failure(self):
        self.assertTrue(pl.evaluate_pressure_cycling(1000, 1000, False))
        self.assertFalse(pl.evaluate_pressure_cycling(999, 1000, False))
        self.assertFalse(pl.evaluate_pressure_cycling(1000, 1000, True))

    def test_design_burst_requires_margin_over_factor(self):
        self.assertTrue(pl.evaluate_design_burst(400.0, 100.0, 4.0))
        self.assertFalse(pl.evaluate_design_burst(399.0, 100.0, 4.0))

    def test_burst_requires_achieved_over_factor(self):
        self.assertTrue(pl.evaluate_burst(400.0, 100.0, 4.0))
        self.assertFalse(pl.evaluate_burst(399.0, 100.0, 4.0))


class EvaluateTestDispatchTest(unittest.TestCase):
    def test_dispatches_to_leak(self):
        self.assertTrue(
            pl.evaluate_test(
                "leak", {"measured_leak_rate": 0.2, "max_allowable_leak_rate": 0.5}
            )
        )

    def test_dispatches_to_burst(self):
        self.assertFalse(
            pl.evaluate_test(
                "burst",
                {"achieved_burst_pressure": 350.0, "meop": 100.0, "required_burst_factor": 4.0},
            )
        )

    def test_unknown_test_type_raises(self):
        with self.assertRaises(ValueError):
            pl.evaluate_test("thermal_vacuum", {})


class BuildPressureTestRecordTest(unittest.TestCase):
    def test_all_required_tests_closed_when_all_pass(self):
        record = pl.build_pressure_test_record(
            "EQ-001",
            "protoflight",
            True,
            True,
            "flight",
            {
                "leak": {"measured_leak_rate": 0.1, "max_allowable_leak_rate": 0.5},
                "proof_pressure": {
                    "held_pressure": 150.0,
                    "required_proof_pressure": 150.0,
                    "anomaly_detected": False,
                },
                "pressure_cycling": {
                    "cycles_completed": 500,
                    "required_cycles": 500,
                    "failure_detected": False,
                },
                "design_burst": {
                    "predicted_burst_pressure": 420.0,
                    "meop": 100.0,
                    "required_burst_factor": 4.0,
                },
            },
        )
        self.assertEqual(
            record["required_tests"],
            ("leak", "proof_pressure", "pressure_cycling", "design_burst"),
        )
        self.assertTrue(pl.item_complete(record))
        self.assertEqual(pl.open_or_failed_tests(record), [])

    def test_missing_test_is_left_open(self):
        record = pl.build_pressure_test_record(
            "EQ-002",
            "acceptance",
            True,
            False,
            "flight",
            {
                "leak": {"measured_leak_rate": 0.1, "max_allowable_leak_rate": 0.5},
            },
        )
        self.assertEqual(record["statuses"]["leak"], "closed")
        self.assertEqual(record["statuses"]["proof_pressure"], "open")
        self.assertFalse(pl.item_complete(record))
        self.assertEqual(pl.open_or_failed_tests(record), ["proof_pressure", "design_burst"])

    def test_failing_result_marks_test_failed_not_complete(self):
        record = pl.build_pressure_test_record(
            "EQ-003",
            "qualification",
            True,
            False,
            "dedicated_qualification",
            {
                "leak": {"measured_leak_rate": 0.1, "max_allowable_leak_rate": 0.5},
                "proof_pressure": {
                    "held_pressure": 150.0,
                    "required_proof_pressure": 150.0,
                    "anomaly_detected": False,
                },
                "burst": {
                    "achieved_burst_pressure": 350.0,
                    "meop": 100.0,
                    "required_burst_factor": 4.0,
                },
            },
        )
        self.assertEqual(record["statuses"]["burst"], "failed")
        self.assertFalse(pl.item_complete(record))
        self.assertEqual(pl.open_or_failed_tests(record), ["burst"])

    def test_burst_out_of_order_raises(self):
        with self.assertRaises(ValueError):
            pl.build_pressure_test_record(
                "EQ-004",
                "qualification",
                True,
                False,
                "dedicated_qualification",
                {
                    "burst": {
                        "achieved_burst_pressure": 500.0,
                        "meop": 100.0,
                        "required_burst_factor": 4.0,
                    },
                    "leak": {"measured_leak_rate": 0.1, "max_allowable_leak_rate": 0.5},
                },
            )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            pl.build_pressure_test_record("", "acceptance", True, False, "flight", {})

    def test_does_not_mutate_results(self):
        results = {
            "leak": {"measured_leak_rate": 0.1, "max_allowable_leak_rate": 0.5},
        }
        before = dict(results)
        pl.build_pressure_test_record("EQ-005", "acceptance", True, False, "flight", results)
        self.assertEqual(results, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
