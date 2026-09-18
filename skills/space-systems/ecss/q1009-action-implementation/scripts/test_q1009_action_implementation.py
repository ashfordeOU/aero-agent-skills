#!/usr/bin/env python3
"""Contract test for nonconformance action implementation tracking (offline)."""

import copy
import datetime
import unittest

from q1009_action_implementation_logic import (
    ALLOWED_TRANSITIONS,
    STATUSES,
    TERMINAL_STATUSES,
    VERDICT_HELD_EVIDENCE,
    VERDICT_HELD_OPEN,
    VERDICT_MAY_PROGRESS,
    apply_transition,
    gate_ncr_progression,
    parse_date,
    status_rollup,
    transition_allowed,
    unowned_actions,
    validate_action,
    validate_register,
)

AS_OF = "2026-03-01"

VERIFIED = {
    "id": "ACT-01",
    "description": "fit the alignment jig on the joint assembly bench",
    "owner": "manufacturing engineering",
    "due_date": "2026-02-10",
    "status": "verified",
    "mandatory": True,
    "evidence": "first article on the jig measured inside drawing tolerance",
}

IN_WORK = {
    "id": "ACT-02",
    "description": "update the work order with the torque value",
    "owner": "process engineering",
    "due_date": "2026-03-20",
    "status": "in-work",
    "mandatory": True,
}


def _entry(base, **overrides):
    entry = copy.deepcopy(base)
    entry.update(overrides)
    return entry


class DateTests(unittest.TestCase):
    def test_iso_date_parses(self):
        self.assertEqual(parse_date("due_date", "2026-02-10"), datetime.date(2026, 2, 10))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("due_date", "10 Feb 2026")

    def test_missing_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("due_date", None)


class TransitionTests(unittest.TestCase):
    def test_open_may_start(self):
        self.assertTrue(transition_allowed("open", "in-work"))

    def test_open_may_not_jump_to_verified(self):
        self.assertFalse(transition_allowed("open", "verified"))

    def test_implemented_may_be_verified(self):
        self.assertTrue(transition_allowed("implemented", "verified"))

    def test_verified_may_be_reopened(self):
        self.assertTrue(transition_allowed("verified", "in-work"))

    def test_cancelled_is_final(self):
        self.assertEqual(ALLOWED_TRANSITIONS["cancelled"], ())

    def test_every_status_has_a_transition_rule(self):
        for status in STATUSES:
            self.assertIn(status, ALLOWED_TRANSITIONS)

    def test_apply_transition_returns_the_new_state(self):
        self.assertEqual(apply_transition("in-work", "implemented"), "implemented")

    def test_apply_transition_refuses_a_jump(self):
        with self.assertRaises(ValueError):
            apply_transition("open", "implemented")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            transition_allowed("open", "finished")


class ActionEntryTests(unittest.TestCase):
    def test_verified_entry_with_evidence_is_effective(self):
        result = validate_action(VERIFIED, AS_OF)
        self.assertTrue(result["effectively_verified"])
        self.assertTrue(result["properly_closed"])

    def test_verified_entry_without_evidence_is_not(self):
        entry = _entry(VERIFIED)
        del entry["evidence"]
        result = validate_action(entry, AS_OF)
        self.assertFalse(result["effectively_verified"])
        self.assertTrue(result["findings"])

    def test_overdue_live_action_is_counted_late(self):
        result = validate_action(_entry(IN_WORK, due_date="2026-02-20"), AS_OF)
        self.assertTrue(result["overdue"])
        self.assertEqual(result["days_late"], 9)

    def test_action_due_today_is_not_yet_late(self):
        result = validate_action(_entry(IN_WORK, due_date=AS_OF), AS_OF)
        self.assertFalse(result["overdue"])
        self.assertEqual(result["days_late"], 0)

    def test_closed_action_past_its_date_is_not_overdue(self):
        result = validate_action(_entry(VERIFIED, due_date="2026-01-01"), AS_OF)
        self.assertFalse(result["overdue"])

    def test_missing_owner_is_a_finding(self):
        result = validate_action(_entry(IN_WORK, owner="  "), AS_OF)
        self.assertIsNone(result["owner"])
        self.assertTrue(any("owner" in f for f in result["findings"]))

    def test_cancelled_without_a_reason_is_not_properly_closed(self):
        result = validate_action(_entry(IN_WORK, status="cancelled"), AS_OF)
        self.assertFalse(result["properly_closed"])

    def test_cancelled_with_a_reason_is_properly_closed(self):
        result = validate_action(
            _entry(IN_WORK, status="cancelled", cancellation_reason="superseded by ACT-01"),
            AS_OF,
        )
        self.assertTrue(result["properly_closed"])

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_action(_entry(IN_WORK, status="nearly-done"), AS_OF)

    def test_missing_description_rejected(self):
        entry = _entry(IN_WORK)
        del entry["description"]
        with self.assertRaises(ValueError):
            validate_action(entry, AS_OF)

    def test_non_boolean_mandatory_rejected(self):
        with self.assertRaises(ValueError):
            validate_action(_entry(IN_WORK, mandatory="yes"), AS_OF)

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_action("ACT-02", AS_OF)


class RegisterTests(unittest.TestCase):
    def test_register_validates_every_entry(self):
        self.assertEqual(len(validate_register([VERIFIED, IN_WORK], AS_OF)), 2)

    def test_duplicate_action_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_register([IN_WORK, _entry(IN_WORK)], AS_OF)

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            validate_register([], AS_OF)

    def test_non_list_register_rejected(self):
        with self.assertRaises(ValueError):
            validate_register({"id": "ACT-02"}, AS_OF)

    def test_rollup_counts_each_state(self):
        rollup = status_rollup(validate_register([VERIFIED, IN_WORK], AS_OF))
        self.assertEqual(rollup["counts"]["verified"], 1)
        self.assertEqual(rollup["counts"]["in-work"], 1)
        self.assertEqual(rollup["open_count"], 1)

    def test_rollup_orders_the_overdue_worst_first(self):
        late_a = _entry(IN_WORK, id="ACT-03", due_date="2026-02-25")
        late_b = _entry(IN_WORK, id="ACT-04", due_date="2026-01-25")
        rollup = status_rollup(validate_register([late_a, late_b], AS_OF))
        self.assertEqual(rollup["overdue_ids"][0], "ACT-04")
        self.assertEqual(rollup["worst_days_late"], 35)

    def test_verified_fraction_is_a_proportion(self):
        rollup = status_rollup(validate_register([VERIFIED, IN_WORK], AS_OF))
        self.assertAlmostEqual(rollup["verified_fraction"], 0.5, places=9)

    def test_unowned_actions_are_listed(self):
        checked = validate_register([VERIFIED, _entry(IN_WORK, owner="")], AS_OF)
        self.assertEqual(unowned_actions(checked), ("ACT-02",))

    def test_terminal_states_are_the_two_resting_ones(self):
        self.assertEqual(set(TERMINAL_STATUSES), {"verified", "cancelled"})


class ProgressionTests(unittest.TestCase):
    def test_all_mandatory_verified_lets_the_ncr_progress(self):
        result = gate_ncr_progression([VERIFIED], AS_OF)
        self.assertEqual(result["verdict"], VERDICT_MAY_PROGRESS)
        self.assertTrue(result["progression_permitted"])

    def test_an_open_mandatory_action_holds_the_ncr(self):
        result = gate_ncr_progression([VERIFIED, IN_WORK], AS_OF)
        self.assertEqual(result["verdict"], VERDICT_HELD_OPEN)
        self.assertIn("ACT-02", result["open_mandatory"])

    def test_implemented_but_unverified_holds_on_evidence(self):
        result = gate_ncr_progression([_entry(IN_WORK, status="implemented")], AS_OF)
        self.assertEqual(result["verdict"], VERDICT_HELD_EVIDENCE)
        self.assertIn("ACT-02", result["implemented_not_verified"])

    def test_verified_without_evidence_holds_the_ncr(self):
        entry = _entry(VERIFIED)
        del entry["evidence"]
        result = gate_ncr_progression([entry], AS_OF)
        self.assertEqual(result["verdict"], VERDICT_HELD_EVIDENCE)
        self.assertIn("ACT-01", result["closed_without_record"])

    def test_cancelled_without_a_reason_holds_the_ncr(self):
        result = gate_ncr_progression([_entry(VERIFIED, status="cancelled")], AS_OF)
        self.assertEqual(result["verdict"], VERDICT_HELD_EVIDENCE)

    def test_cancelled_with_a_reason_does_not_hold_the_ncr(self):
        entry = _entry(
            VERIFIED, status="cancelled", cancellation_reason="duplicate of ACT-07"
        )
        self.assertTrue(gate_ncr_progression([entry], AS_OF)["progression_permitted"])

    def test_an_open_optional_action_does_not_hold_the_ncr(self):
        optional = _entry(IN_WORK, mandatory=False)
        result = gate_ncr_progression([VERIFIED, optional], AS_OF)
        self.assertTrue(result["progression_permitted"])

    def test_overdue_actions_are_reported_even_when_progression_is_held(self):
        late = _entry(IN_WORK, due_date="2026-01-15")
        result = gate_ncr_progression([VERIFIED, late], AS_OF)
        self.assertTrue(any("past their due date" in f for f in result["findings"]))

    def test_unowned_action_is_reported(self):
        result = gate_ncr_progression([VERIFIED, _entry(IN_WORK, owner="")], AS_OF)
        self.assertTrue(any("no owner" in f for f in result["findings"]))

    def test_register_without_a_mandatory_action_rejected(self):
        with self.assertRaises(ValueError):
            gate_ncr_progression([_entry(VERIFIED, mandatory=False)], AS_OF)

    def test_bad_as_of_date_rejected(self):
        with self.assertRaises(ValueError):
            gate_ncr_progression([VERIFIED], "01/03/2026")


if __name__ == "__main__":
    unittest.main()
