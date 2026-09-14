#!/usr/bin/env python3
"""Contract test for the bare cell qualification schedule (offline)."""

import copy
import unittest

from e2008_bare_cell_qualification_schedule_logic import (
    DEFAULT_BARE_CELL_SCHEDULE_POLICY,
    REQUIRED_BARE_CELL_STEPS,
    SCHEDULE_NOT_RUNNABLE,
    SCHEDULE_RUNNABLE,
    STEP_OUT_OF_ORDER,
    STEP_PREREQUISITE_ABSENT,
    STEP_SAMPLE_UNAVAILABLE,
    STEP_SCHEDULED,
    assess_bare_cell_schedule,
    assess_schedule_step,
    required_bare_cell_steps,
    resolve_step_prerequisites,
    validate_bare_cell_schedule_policy,
    walk_cell_lot,
)

GOOD_SEQUENCE = (
    "cell-lot-manufacture",
    "lot-identification-marking",
    "initial-visual-inspection",
    "dimension-and-thickness-measurement",
    "initial-illuminated-iv-measurement",
    "spectral-response-measurement",
    "bare-cell-thermal-cycling",
    "bare-cell-humidity-exposure",
    "final-illuminated-iv-measurement",
    "final-visual-inspection",
    "bare-cell-particle-irradiation",
    "contact-adhesion-pull-test",
    "reverse-bias-endurance-test",
    "bare-cell-qualification-report",
)

GOOD_LOT = 12


def _plan(sequence=None, lot_size=GOOD_LOT, **overrides):
    plan = {
        "lot_id": "BC-LOT-01",
        "sequence": list(sequence if sequence is not None else GOOD_SEQUENCE),
        "lot_size": lot_size,
    }
    plan.update(overrides)
    return plan


def _swap(sequence, first, second):
    order = list(sequence)
    i, j = order.index(first), order.index(second)
    order[i], order[j] = order[j], order[i]
    return order


def _without(sequence, name):
    return [step for step in sequence if step != name]


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_bare_cell_schedule_policy(DEFAULT_BARE_CELL_SCHEDULE_POLICY),
            DEFAULT_BARE_CELL_SCHEDULE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_bare_cell_schedule_policy("default")

    def test_negative_reserve_rejected(self):
        broken = dict(DEFAULT_BARE_CELL_SCHEDULE_POLICY, retest_reserve_cells=-1)
        with self.assertRaises(ValueError):
            validate_bare_cell_schedule_policy(broken)

    def test_non_boolean_flag_rejected(self):
        broken = dict(DEFAULT_BARE_CELL_SCHEDULE_POLICY, require_report_last="yes")
        with self.assertRaises(ValueError):
            validate_bare_cell_schedule_policy(broken)

    def test_required_steps_copy_is_independent(self):
        first = required_bare_cell_steps()
        first["cell-lot-manufacture"]["sample_size"] = 99
        self.assertEqual(
            REQUIRED_BARE_CELL_STEPS["cell-lot-manufacture"]["sample_size"], 0
        )

    def test_every_prerequisite_names_a_known_step(self):
        for name, spec in REQUIRED_BARE_CELL_STEPS.items():
            for need in spec["prerequisites"]:
                self.assertIn(need, REQUIRED_BARE_CELL_STEPS, "%s -> %s" % (name, need))


class SequenceValidationTests(unittest.TestCase):
    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            resolve_step_prerequisites([])

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            resolve_step_prerequisites(list(GOOD_SEQUENCE) + ["coverglass-bonding"])

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            resolve_step_prerequisites(
                list(GOOD_SEQUENCE) + ["final-visual-inspection"]
            )

    def test_non_string_step_rejected(self):
        with self.assertRaises(ValueError):
            resolve_step_prerequisites([7])

    def test_non_list_sequence_rejected(self):
        with self.assertRaises(ValueError):
            resolve_step_prerequisites("cell-lot-manufacture")


class PrerequisiteResolutionTests(unittest.TestCase):
    def test_good_sequence_has_no_open_prerequisites(self):
        resolved = resolve_step_prerequisites(GOOD_SEQUENCE)
        for name, entry in resolved.items():
            self.assertEqual(entry["absent_prerequisites"], (), name)
            self.assertEqual(entry["late_prerequisites"], (), name)

    def test_absent_and_late_are_separate_lists(self):
        order = _without(GOOD_SEQUENCE, "spectral-response-measurement")
        resolved = resolve_step_prerequisites(order)
        entry = resolved["bare-cell-particle-irradiation"]
        self.assertEqual(entry["absent_prerequisites"], ("spectral-response-measurement",))
        self.assertEqual(entry["late_prerequisites"], ())

    def test_misplaced_prerequisite_reported_as_late(self):
        order = _swap(
            GOOD_SEQUENCE,
            "initial-illuminated-iv-measurement",
            "bare-cell-thermal-cycling",
        )
        resolved = resolve_step_prerequisites(order)
        entry = resolved["bare-cell-thermal-cycling"]
        self.assertEqual(
            entry["late_prerequisites"], ("initial-illuminated-iv-measurement",)
        )
        self.assertEqual(entry["absent_prerequisites"], ())

    def test_positions_follow_the_declared_order(self):
        resolved = resolve_step_prerequisites(GOOD_SEQUENCE)
        self.assertEqual(resolved["cell-lot-manufacture"]["position"], 0)
        self.assertEqual(
            resolved["bare-cell-qualification-report"]["position"],
            len(GOOD_SEQUENCE) - 1,
        )


class CellWalkTests(unittest.TestCase):
    def test_walk_retires_only_at_destructive_steps(self):
        walk = walk_cell_lot(GOOD_SEQUENCE, GOOD_LOT)
        by_step = dict((entry["step"], entry) for entry in walk["steps"])
        self.assertEqual(by_step["initial-visual-inspection"]["cells_retired"], 0)
        self.assertEqual(by_step["contact-adhesion-pull-test"]["cells_retired"], 3)
        self.assertEqual(by_step["reverse-bias-endurance-test"]["cells_retired"], 2)

    def test_walk_totals_match_the_closing_balance(self):
        walk = walk_cell_lot(GOOD_SEQUENCE, GOOD_LOT)
        self.assertEqual(walk["cells_retired_total"], 9)
        self.assertEqual(walk["cells_remaining"], GOOD_LOT - 9)
        self.assertIsNone(walk["exhausted_at"])

    def test_walk_names_the_step_the_lot_cannot_supply(self):
        walk = walk_cell_lot(GOOD_SEQUENCE, 8)
        self.assertEqual(walk["exhausted_at"], "reverse-bias-endurance-test")

    def test_order_decides_where_the_lot_empties(self):
        early_destructive = [
            "cell-lot-manufacture",
            "lot-identification-marking",
            "initial-visual-inspection",
            "dimension-and-thickness-measurement",
            "initial-illuminated-iv-measurement",
            "spectral-response-measurement",
            "bare-cell-particle-irradiation",
            "contact-adhesion-pull-test",
            "reverse-bias-endurance-test",
            "bare-cell-thermal-cycling",
            "bare-cell-humidity-exposure",
            "final-illuminated-iv-measurement",
            "final-visual-inspection",
            "bare-cell-qualification-report",
        ]
        same_total = walk_cell_lot(early_destructive, 10)
        other = walk_cell_lot(GOOD_SEQUENCE, 10)
        self.assertEqual(same_total["cells_retired_total"], other["cells_retired_total"])
        self.assertEqual(same_total["exhausted_at"], "bare-cell-thermal-cycling")
        self.assertIsNone(other["exhausted_at"])

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            walk_cell_lot(GOOD_SEQUENCE, 0)

    def test_non_integer_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            walk_cell_lot(GOOD_SEQUENCE, 12.5)

    def test_boolean_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            walk_cell_lot(GOOD_SEQUENCE, True)


class StepVerdictTests(unittest.TestCase):
    def test_absent_prerequisite_outranks_a_shortfall(self):
        resolution = {
            "position": 4,
            "absent_prerequisites": ("initial-visual-inspection",),
            "late_prerequisites": (),
        }
        entry = {"sample_size": 4, "opening_cells": 0, "sample_available": False}
        result = assess_schedule_step("bare-cell-thermal-cycling", resolution, entry)
        self.assertEqual(result["verdict"], STEP_PREREQUISITE_ABSENT)

    def test_late_prerequisite_outranks_a_shortfall(self):
        resolution = {
            "position": 4,
            "absent_prerequisites": (),
            "late_prerequisites": ("initial-visual-inspection",),
        }
        entry = {"sample_size": 4, "opening_cells": 0, "sample_available": False}
        result = assess_schedule_step("bare-cell-thermal-cycling", resolution, entry)
        self.assertEqual(result["verdict"], STEP_OUT_OF_ORDER)

    def test_shortfall_reported_when_order_is_sound(self):
        resolution = {
            "position": 4,
            "absent_prerequisites": (),
            "late_prerequisites": (),
        }
        entry = {"sample_size": 4, "opening_cells": 1, "sample_available": False}
        result = assess_schedule_step("bare-cell-thermal-cycling", resolution, entry)
        self.assertEqual(result["verdict"], STEP_SAMPLE_UNAVAILABLE)
        self.assertTrue(result["findings"])

    def test_clean_step_carries_no_findings(self):
        resolution = {
            "position": 4,
            "absent_prerequisites": (),
            "late_prerequisites": (),
        }
        entry = {"sample_size": 4, "opening_cells": 9, "sample_available": True}
        result = assess_schedule_step("bare-cell-thermal-cycling", resolution, entry)
        self.assertEqual(result["verdict"], STEP_SCHEDULED)
        self.assertEqual(result["findings"], [])

    def test_unknown_step_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_schedule_step("coverglass-bonding", {}, {})


class ScheduleRollupTests(unittest.TestCase):
    def test_good_schedule_is_runnable(self):
        result = assess_bare_cell_schedule(_plan())
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["undeclared_steps"], ())
        self.assertAlmostEqual(result["declared_fraction"], 1.0, places=9)

    def test_missing_step_is_reported_and_blocks_the_schedule(self):
        order = _without(GOOD_SEQUENCE, "spectral-response-measurement")
        result = assess_bare_cell_schedule(_plan(order))
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertIn("spectral-response-measurement", result["undeclared_steps"])
        self.assertAlmostEqual(
            result["declared_fraction"],
            (len(GOOD_SEQUENCE) - 1) / float(len(REQUIRED_BARE_CELL_STEPS)),
            places=9,
        )

    def test_out_of_order_schedule_is_not_runnable(self):
        order = _swap(
            GOOD_SEQUENCE,
            "initial-illuminated-iv-measurement",
            "bare-cell-thermal-cycling",
        )
        result = assess_bare_cell_schedule(_plan(order))
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(result["worst_step_verdict"], STEP_OUT_OF_ORDER)

    def test_short_lot_fails_on_supply_not_on_order(self):
        result = assess_bare_cell_schedule(_plan(lot_size=8))
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(result["worst_step_verdict"], STEP_SAMPLE_UNAVAILABLE)
        self.assertEqual(result["cell_walk"]["exhausted_at"], "reverse-bias-endurance-test")

    def test_reserve_shortfall_caught_although_every_step_ran(self):
        result = assess_bare_cell_schedule(_plan(lot_size=10))
        self.assertEqual(result["worst_step_verdict"], STEP_SCHEDULED)
        self.assertFalse(result["retest_reserve_met"])
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)

    def test_reserve_can_be_waived_by_policy(self):
        policy = dict(DEFAULT_BARE_CELL_SCHEDULE_POLICY, retest_reserve_cells=0)
        result = assess_bare_cell_schedule(_plan(lot_size=10), policy)
        self.assertTrue(result["retest_reserve_met"])
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)

    def test_report_must_close_the_sequence(self):
        order = list(GOOD_SEQUENCE)
        order.remove("bare-cell-qualification-report")
        order.insert(-1, "bare-cell-qualification-report")
        result = assess_bare_cell_schedule(_plan(order))
        self.assertFalse(result["report_closes_schedule"])
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)

    def test_report_placement_waiver_is_read_from_policy(self):
        order = list(GOOD_SEQUENCE)
        order.remove("bare-cell-qualification-report")
        order.insert(-1, "bare-cell-qualification-report")
        policy = dict(DEFAULT_BARE_CELL_SCHEDULE_POLICY, require_report_last=False)
        strict = assess_bare_cell_schedule(_plan(order))
        waived = assess_bare_cell_schedule(_plan(order), policy)
        self.assertFalse(strict["report_closes_schedule"])
        self.assertTrue(waived["report_closes_schedule"])
        self.assertTrue(
            any("not the last step" in finding for finding in strict["findings"])
        )
        self.assertFalse(
            any("not the last step" in finding for finding in waived["findings"])
        )

    def test_report_placement_rule_is_silent_when_no_report_is_declared(self):
        order = _without(GOOD_SEQUENCE, "bare-cell-qualification-report")
        result = assess_bare_cell_schedule(_plan(order))
        self.assertTrue(result["report_closes_schedule"])
        self.assertIn("bare-cell-qualification-report", result["undeclared_steps"])

    def test_measurement_before_marking_breaks_traceability(self):
        order = _swap(
            GOOD_SEQUENCE, "lot-identification-marking", "initial-visual-inspection"
        )
        result = assess_bare_cell_schedule(_plan(order))
        self.assertFalse(result["marking_precedes_measurement"])
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)

    def test_step_verdict_counts_cover_every_declared_step(self):
        result = assess_bare_cell_schedule(_plan())
        self.assertEqual(sum(result["step_verdict_counts"].values()), len(GOOD_SEQUENCE))

    def test_plan_without_lot_id_rejected(self):
        plan = _plan()
        plan["lot_id"] = "   "
        with self.assertRaises(ValueError):
            assess_bare_cell_schedule(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_schedule("BC-LOT-01")

    def test_plan_is_not_mutated_by_the_assessment(self):
        plan = _plan()
        before = copy.deepcopy(plan)
        assess_bare_cell_schedule(plan)
        self.assertEqual(plan, before)


if __name__ == "__main__":
    unittest.main()
