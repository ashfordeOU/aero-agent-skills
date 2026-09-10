#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.6.4 simulator
qualification for verification.

Exercises scripts/e1002_simulators_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 -- capability classification
requires at least one asserted capability; required evidence is the
union of the evidence obligations of every asserted capability;
qualification status is 'qualified' only when nothing is missing;
verification credit is gated on qualified status; a qualified
simulator needs re-qualification after a model or interface change,
and an unqualified simulator always needs qualification.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_simulators_logic as sim  # noqa: E402


class ClassifySimulatorTest(unittest.TestCase):
    def test_single_capability(self):
        self.assertEqual(
            sim.classify_simulator(True, False, False),
            ("functional",),
        )

    def test_multiple_capabilities_in_fixed_order(self):
        self.assertEqual(
            sim.classify_simulator(True, True, True),
            ("functional", "real_time", "closed_loop"),
        )

    def test_real_time_only(self):
        self.assertEqual(
            sim.classify_simulator(False, True, False),
            ("real_time",),
        )

    def test_no_capability_raises(self):
        with self.assertRaises(ValueError):
            sim.classify_simulator(False, False, False)


class RequiredEvidenceTest(unittest.TestCase):
    def test_functional_only(self):
        self.assertEqual(
            sim.required_evidence(("functional",)),
            ("functional_correctness_validation",),
        )

    def test_real_time_adds_timing_evidence(self):
        self.assertEqual(
            sim.required_evidence(("real_time",)),
            ("functional_correctness_validation", "timing_performance_validation"),
        )

    def test_closed_loop_adds_interface_and_stability_evidence(self):
        self.assertEqual(
            sim.required_evidence(("closed_loop",)),
            (
                "functional_correctness_validation",
                "interface_representativeness_validation",
                "loop_stability_validation",
            ),
        )

    def test_union_is_deduplicated_across_capabilities(self):
        self.assertEqual(
            sim.required_evidence(("functional", "real_time", "closed_loop")),
            (
                "functional_correctness_validation",
                "interface_representativeness_validation",
                "loop_stability_validation",
                "timing_performance_validation",
            ),
        )

    def test_unknown_capability_raises(self):
        with self.assertRaises(ValueError):
            sim.required_evidence(("thermal",))


class AssessQualificationTest(unittest.TestCase):
    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            sim.assess_qualification({
                "is_functional": True,
                "is_real_time": False,
                "is_closed_loop": False,
            })

    def test_functional_qualified_with_evidence(self):
        assessment = sim.assess_qualification({
            "id": "SIM-001",
            "is_functional": True,
            "is_real_time": False,
            "is_closed_loop": False,
            "evidence": ["functional_correctness_validation"],
        })
        self.assertEqual(assessment["status"], "qualified")
        self.assertEqual(assessment["missing_evidence"], ())

    def test_no_evidence_key_defaults_to_none_provided(self):
        assessment = sim.assess_qualification({
            "id": "SIM-002",
            "is_functional": True,
            "is_real_time": False,
            "is_closed_loop": False,
        })
        self.assertEqual(assessment["status"], "not_qualified")
        self.assertEqual(
            assessment["missing_evidence"],
            ("functional_correctness_validation",),
        )

    def test_real_time_missing_timing_evidence_is_not_qualified(self):
        assessment = sim.assess_qualification({
            "id": "SIM-003",
            "is_functional": True,
            "is_real_time": True,
            "is_closed_loop": False,
            "evidence": ["functional_correctness_validation"],
        })
        self.assertEqual(assessment["status"], "not_qualified")
        self.assertEqual(
            assessment["missing_evidence"],
            ("timing_performance_validation",),
        )

    def test_closed_loop_fully_qualified(self):
        assessment = sim.assess_qualification({
            "id": "SIM-004",
            "is_functional": False,
            "is_real_time": False,
            "is_closed_loop": True,
            "evidence": [
                "functional_correctness_validation",
                "interface_representativeness_validation",
                "loop_stability_validation",
            ],
        })
        self.assertEqual(assessment["status"], "qualified")

    def test_extra_unrequired_evidence_does_not_affect_status(self):
        assessment = sim.assess_qualification({
            "id": "SIM-005",
            "is_functional": True,
            "is_real_time": False,
            "is_closed_loop": False,
            "evidence": ["functional_correctness_validation", "extra_report"],
        })
        self.assertEqual(assessment["status"], "qualified")


class BuildQualificationRegisterTest(unittest.TestCase):
    SIMULATORS = [
        {
            "id": "SIM-001",
            "is_functional": True,
            "is_real_time": False,
            "is_closed_loop": False,
            "evidence": ["functional_correctness_validation"],
        },
        {
            "id": "SIM-002",
            "is_functional": False,
            "is_real_time": True,
            "is_closed_loop": False,
            "evidence": ["functional_correctness_validation"],
        },
    ]

    def test_register_order_and_content(self):
        register = sim.build_qualification_register(self.SIMULATORS)
        self.assertEqual([entry["id"] for entry in register], ["SIM-001", "SIM-002"])
        self.assertEqual(register[0]["status"], "qualified")
        self.assertEqual(register[1]["status"], "not_qualified")

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            sim.build_qualification_register(self.SIMULATORS + [self.SIMULATORS[0]])

    def test_does_not_mutate_input(self):
        before = [dict(s) for s in self.SIMULATORS]
        sim.build_qualification_register(self.SIMULATORS)
        self.assertEqual(self.SIMULATORS, before)


class CanCreditVerificationTest(unittest.TestCase):
    def test_qualified_can_credit(self):
        assessment = {"status": "qualified"}
        self.assertTrue(sim.can_credit_verification(assessment))

    def test_not_qualified_cannot_credit(self):
        assessment = {"status": "not_qualified"}
        self.assertFalse(sim.can_credit_verification(assessment))


class NeedsRequalificationTest(unittest.TestCase):
    def test_not_qualified_always_needs_requalification(self):
        assessment = {"status": "not_qualified"}
        self.assertTrue(sim.needs_requalification(assessment, {}))

    def test_qualified_no_change_does_not_need_requalification(self):
        assessment = {"status": "qualified"}
        self.assertFalse(sim.needs_requalification(assessment, {}))

    def test_qualified_model_change_triggers_requalification(self):
        assessment = {"status": "qualified"}
        self.assertTrue(
            sim.needs_requalification(assessment, {"model_changed": True})
        )

    def test_qualified_interface_change_triggers_requalification(self):
        assessment = {"status": "qualified"}
        self.assertTrue(
            sim.needs_requalification(
                assessment, {"unit_under_test_interface_changed": True}
            )
        )

    def test_qualified_unrelated_flag_does_not_trigger(self):
        assessment = {"status": "qualified"}
        self.assertFalse(
            sim.needs_requalification(assessment, {"schedule_slipped": True})
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
