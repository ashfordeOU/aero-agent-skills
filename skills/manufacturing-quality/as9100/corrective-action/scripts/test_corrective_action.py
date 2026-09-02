#!/usr/bin/env python3
"""Gate 3 contract test: corrective action (CAPA) closure stages.

Exercises scripts/corrective_action_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3: the record
state machine (containment-missing, root-cause-incomplete,
corrective-action-missing, effectiveness-pending, closed), the
five-whys chain check (depth, empty answers, circular repetition),
the placeholder answer rejection, the circular-evidence check, the
closure verdict with the missing items, and the stage field map;
invalid inputs raise ValueError. The physically meaningful invariant:
a closed record always carries a containment action, a sufficient
root cause chain, a corrective action, and distinct effectiveness
evidence.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corrective_action_logic as cal  # noqa: E402


class ContainmentTest(unittest.TestCase):
    def test_recorded_containment_ok(self):
        self.assertTrue(cal.containment_ok("quarantine the suspect batch"))

    def test_placeholder_containment_rejected(self):
        for value in ("none", "n/a", "na", "no", "unknown", "not-applicable"):
            self.assertFalse(cal.containment_ok(value), value)

    def test_empty_containment_rejected(self):
        self.assertFalse(cal.containment_ok(""))
        self.assertFalse(cal.containment_ok(None))
        self.assertFalse(cal.containment_ok("   "))

    def test_case_insensitive_placeholder(self):
        self.assertFalse(cal.containment_ok("N/A"))


class RootCauseChainTest(unittest.TestCase):
    def test_three_distinct_levels_ok(self):
        whys = ["drill wandered", "clamp worn", "maintenance skipped"]
        self.assertTrue(cal.root_cause_chain_ok(whys))

    def test_default_min_depth_is_three(self):
        self.assertEqual(cal.MIN_WHY_DEPTH, 3)
        self.assertFalse(cal.root_cause_chain_ok(["drill wandered", "clamp worn"]))
        self.assertTrue(
            cal.root_cause_chain_ok(["a", "b", "c"], min_depth=2)
        )

    def test_short_chain_incomplete(self):
        self.assertFalse(cal.root_cause_chain_ok(["drill wandered", "clamp worn"]))

    def test_circular_adjacent_answers_rejected(self):
        whys = ["clamp worn", "clamp worn", "maintenance skipped"]
        self.assertFalse(cal.root_cause_chain_ok(whys))

    def test_circularity_is_case_insensitive(self):
        whys = ["Clamp worn", "clamp worn", "maintenance skipped"]
        self.assertFalse(cal.root_cause_chain_ok(whys))

    def test_empty_answer_rejected(self):
        self.assertFalse(cal.root_cause_chain_ok(["a", "", "c"]))
        self.assertFalse(cal.root_cause_chain_ok(["a", "none", "c"]))

    def test_non_list_chain_rejected(self):
        self.assertFalse(cal.root_cause_chain_ok("clamp worn"))
        self.assertFalse(cal.root_cause_chain_ok(None))

    def test_tuple_chain_accepted(self):
        self.assertTrue(cal.root_cause_chain_ok(("a", "b", "c")))


class CorrectiveActionTest(unittest.TestCase):
    def test_recorded_action_ok(self):
        self.assertTrue(cal.corrective_action_ok("replace the worn clamp"))

    def test_placeholder_action_rejected(self):
        for value in ("none", "n/a", "unknown"):
            self.assertFalse(cal.corrective_action_ok(value), value)

    def test_empty_action_rejected(self):
        self.assertFalse(cal.corrective_action_ok(""))
        self.assertFalse(cal.corrective_action_ok(None))


class EffectivenessTest(unittest.TestCase):
    def test_distinct_evidence_ok(self):
        self.assertTrue(
            cal.effectiveness_evidence_ok(
                "no drill wander in 90 days", "clamp worn"
            )
        )

    def test_circular_evidence_rejected(self):
        self.assertFalse(
            cal.effectiveness_evidence_ok("clamp worn", "clamp worn")
        )

    def test_circular_evidence_case_insensitive(self):
        self.assertFalse(
            cal.effectiveness_evidence_ok("Clamp worn", "clamp worn")
        )

    def test_missing_evidence_rejected(self):
        self.assertFalse(cal.effectiveness_evidence_ok(""))
        self.assertFalse(cal.effectiveness_evidence_ok(None))
        self.assertFalse(cal.effectiveness_evidence_ok("n/a"))

    def test_evidence_without_root_cause_statement_ok(self):
        self.assertTrue(cal.effectiveness_evidence_ok("no recurrence in 90 days"))


class RecordStatusTest(unittest.TestCase):
    CLOSED = {
        "problem": "holes out of position",
        "containment": "quarantine batch 4",
        "whys": ["drill wandered", "clamp worn", "maintenance skipped"],
        "corrective_action": "replace clamp and add daily check",
        "effectiveness_evidence": "no out-of-position holes in 90 days",
        "root_cause_statement": "worn clamp",
    }

    def test_closed_record(self):
        self.assertEqual(cal.record_status(self.CLOSED), "closed")

    def test_missing_containment(self):
        rec = dict(self.CLOSED)
        rec["containment"] = ""
        self.assertEqual(cal.record_status(rec), "containment-missing")

    def test_placeholder_containment(self):
        rec = dict(self.CLOSED)
        rec["containment"] = "none"
        self.assertEqual(cal.record_status(rec), "containment-missing")

    def test_short_whys_chain(self):
        rec = dict(self.CLOSED)
        rec["whys"] = ["drill wandered", "clamp worn"]
        self.assertEqual(cal.record_status(rec), "root-cause-incomplete")

    def test_circular_whys_chain(self):
        rec = dict(self.CLOSED)
        rec["whys"] = ["clamp worn", "clamp worn", "maintenance skipped"]
        self.assertEqual(cal.record_status(rec), "root-cause-incomplete")

    def test_missing_corrective_action(self):
        rec = dict(self.CLOSED)
        rec["corrective_action"] = ""
        self.assertEqual(cal.record_status(rec), "corrective-action-missing")

    def test_effectiveness_pending(self):
        rec = dict(self.CLOSED)
        rec["effectiveness_evidence"] = None
        self.assertEqual(cal.record_status(rec), "effectiveness-pending")

    def test_circular_evidence_pending(self):
        rec = dict(self.CLOSED)
        rec["effectiveness_evidence"] = "worn clamp"
        self.assertEqual(cal.record_status(rec), "effectiveness-pending")

    def test_non_dict_record_raises(self):
        with self.assertRaises(ValueError):
            cal.record_status("closed")

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            cal.record_status({"problem": "holes out of position"})


class ClosureVerdictTest(unittest.TestCase):
    def test_verdict_missing_items(self):
        self.assertEqual(
            cal.closure_verdict({"problem": "x", "containment": "", "whys": [], "corrective_action": ""}),
            {"status": "containment-missing", "missing": ["containment"]},
        )
        rec = {
            "problem": "x",
            "containment": "quarantine",
            "whys": ["a"],
            "corrective_action": "fix",
        }
        self.assertEqual(
            cal.closure_verdict(rec),
            {"status": "root-cause-incomplete", "missing": ["whys (at least 3 distinct levels)"]},
        )

    def test_closed_verdict_no_missing(self):
        rec = {
            "problem": "x",
            "containment": "quarantine",
            "whys": ["a", "b", "c"],
            "corrective_action": "fix",
            "effectiveness_evidence": "observed",
        }
        verdict = cal.closure_verdict(rec)
        self.assertEqual(verdict["status"], "closed")
        self.assertEqual(verdict["missing"], [])


class StageFieldsTest(unittest.TestCase):
    def test_stage_field_progression(self):
        self.assertEqual(
            cal.stage_required_fields("containment"), ["problem"]
        )
        self.assertEqual(
            cal.stage_required_fields("root-cause"), ["problem", "containment"]
        )
        self.assertEqual(
            cal.stage_required_fields("corrective-action"),
            ["problem", "containment", "whys"],
        )
        self.assertEqual(
            cal.stage_required_fields("effectiveness"),
            ["problem", "containment", "whys", "corrective_action"],
        )

    def test_unknown_stage_raises(self):
        with self.assertRaises(ValueError):
            cal.stage_required_fields("closure")


class InvariantTest(unittest.TestCase):
    def test_closed_record_has_all_stages(self):
        """Physically meaningful invariant: closure requires a recorded
        containment action, a sufficient root cause chain, a corrective
        action, and effectiveness evidence distinct from the root cause."""
        closed = {
            "problem": "cracked lug",
            "containment": "quarantine",
            "whys": ["overload", "wrong torque", "torque chart outdated"],
            "corrective_action": "update torque chart",
            "effectiveness_evidence": "no cracked lugs in 90 days",
            "root_cause_statement": "torque chart outdated",
        }
        self.assertEqual(cal.record_status(closed), "closed")
        self.assertTrue(cal.containment_ok(closed["containment"]))
        self.assertTrue(cal.root_cause_chain_ok(closed["whys"]))
        self.assertTrue(cal.corrective_action_ok(closed["corrective_action"]))
        self.assertTrue(
            cal.effectiveness_evidence_ok(
                closed["effectiveness_evidence"], closed["root_cause_statement"]
            )
        )

    def test_every_status_has_a_missing_label(self):
        rec = {
            "problem": "x",
            "containment": "quarantine",
            "whys": ["a", "b", "c"],
            "corrective_action": "fix",
        }
        statuses = {"containment-missing", "root-cause-incomplete",
                    "corrective-action-missing", "effectiveness-pending", "closed"}
        self.assertIn(cal.record_status(rec), statuses)


if __name__ == "__main__":
    unittest.main(verbosity=2)
