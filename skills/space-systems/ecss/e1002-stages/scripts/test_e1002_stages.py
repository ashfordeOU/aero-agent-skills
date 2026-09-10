#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.4.1 verification stages.

Exercises scripts/e1002_stages_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the five stages
(qualification, acceptance, pre_launch, in_orbit, post_landing) each
carry a distinct objective; stage applicability follows the product's
launched/recovered life profile; a recovered-but-not-launched product is
rejected; stage sequences are checked against the canonical order; and
missing-stage detection finds gaps between what a product's profile
requires and what has actually been completed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_stages_logic as st  # noqa: E402


class StageObjectiveTest(unittest.TestCase):
    def test_every_stage_has_an_objective(self):
        for stage in st.STAGES:
            objective = st.stage_objective(stage)
            self.assertIsInstance(objective, str)
            self.assertTrue(objective)

    def test_unknown_stage_raises(self):
        with self.assertRaises(ValueError):
            st.stage_objective("disposal")


class DetermineApplicableStagesTest(unittest.TestCase):
    def test_ground_only_product(self):
        self.assertEqual(
            st.determine_applicable_stages(launched=False, recovered=False),
            ["qualification", "acceptance"],
        )

    def test_launched_expendable_product(self):
        self.assertEqual(
            st.determine_applicable_stages(launched=True, recovered=False),
            ["qualification", "acceptance", "pre_launch", "in_orbit"],
        )

    def test_launched_and_recovered_product(self):
        self.assertEqual(
            st.determine_applicable_stages(launched=True, recovered=True),
            ["qualification", "acceptance", "pre_launch", "in_orbit", "post_landing"],
        )

    def test_recovered_without_launched_raises(self):
        with self.assertRaises(ValueError):
            st.determine_applicable_stages(launched=False, recovered=True)


class BuildStagePlanTest(unittest.TestCase):
    def test_full_plan_for_recovered_product(self):
        product = {"id": "PROD-001", "launched": True, "recovered": True}
        plan = st.build_stage_plan(product)
        self.assertEqual(
            [entry["stage"] for entry in plan],
            ["qualification", "acceptance", "pre_launch", "in_orbit", "post_landing"],
        )
        for entry in plan:
            self.assertEqual(entry["objective"], st.stage_objective(entry["stage"]))

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            st.build_stage_plan({"launched": True, "recovered": False})

    def test_does_not_mutate_input(self):
        product = {"id": "PROD-001", "launched": True, "recovered": False}
        before = dict(product)
        st.build_stage_plan(product)
        self.assertEqual(product, before)


class CheckStageOrderTest(unittest.TestCase):
    def test_canonical_order_has_no_violations(self):
        sequence = ["qualification", "acceptance", "pre_launch", "in_orbit", "post_landing"]
        self.assertEqual(st.check_stage_order(sequence), [])

    def test_repeated_stage_is_not_a_violation(self):
        self.assertEqual(st.check_stage_order(["acceptance", "acceptance"]), [])

    def test_out_of_order_stage_is_flagged(self):
        sequence = ["acceptance", "qualification", "pre_launch"]
        self.assertEqual(st.check_stage_order(sequence), ["qualification"])

    def test_unknown_stage_raises(self):
        with self.assertRaises(ValueError):
            st.check_stage_order(["qualification", "disposal"])


class MissingStagesTest(unittest.TestCase):
    def test_detects_gap(self):
        applicable = ["qualification", "acceptance", "pre_launch", "in_orbit"]
        completed = ["qualification", "acceptance"]
        self.assertEqual(
            st.missing_stages(applicable, completed),
            ["pre_launch", "in_orbit"],
        )

    def test_no_gap(self):
        applicable = ["qualification", "acceptance"]
        self.assertEqual(st.missing_stages(applicable, applicable), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
