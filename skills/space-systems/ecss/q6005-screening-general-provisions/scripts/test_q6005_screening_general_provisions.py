#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.3.1 provisions leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_screening_general_provisions.py
"""

import unittest

from q6005_screening_general_provisions_logic import (
    ACCEPTANCE_INDEX,
    DEFAULT_REJECT_ALLOWANCE,
    MANDATORY_PROVISIONS,
    MAXIMUM_RESCREEN_CYCLES,
    PROVISION_STATE_CREDIT,
    PROVISION_TOLERANCE,
    SCREENING_PROVISIONS,
    VERDICTS,
    assess_provision,
    assess_screening_provisions,
    batch_reject_fraction,
    batch_within_reject_allowance,
    provision_index,
    provision_state_credit,
    provision_weight,
    rescreen_within_limit,
    surviving_units,
)

BATCH_SIZE = 100
OPTIONAL_PROVISION = "operator-qualification-recorded"
MANDATORY_PROVISION = "screening-applied-to-every-delivered-unit"


def every_provision(state="satisfied-and-evidenced", **overrides):
    """Every governing provision in one state, with named exceptions."""
    states = {name: state for name in SCREENING_PROVISIONS}
    states.update(overrides)
    return states


def run(**overrides):
    """Grade one screening programme."""
    case = {
        "batch_id": "BATCH-01",
        "batch_size": BATCH_SIZE,
        "rejected_units": 5,
        "rescreen_cycles": 0,
        "provisions": every_provision(),
        "reject_allowance": None,
    }
    case.update(overrides)
    return assess_screening_provisions(**case)


class ProvisionCatalogueTests(unittest.TestCase):
    def test_every_provision_carries_a_positive_weight(self):
        for name in SCREENING_PROVISIONS:
            self.assertGreater(provision_weight(name), 0.0)

    def test_every_mandatory_provision_is_a_published_provision(self):
        for name in MANDATORY_PROVISIONS:
            self.assertIn(name, SCREENING_PROVISIONS)

    def test_an_unknown_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_weight("everyone-knows-how-we-do-it")

    def test_an_unknown_provision_state_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_state_credit("basically-fine")

    def test_a_satisfied_provision_earns_its_full_weight(self):
        record = assess_provision(OPTIONAL_PROVISION, "satisfied-and-evidenced")
        self.assertAlmostEqual(
            record["weighted_credit"], SCREENING_PROVISIONS[OPTIONAL_PROVISION], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_an_unsatisfied_mandatory_provision_is_marked_missing(self):
        record = assess_provision(MANDATORY_PROVISION, "not-satisfied")
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-provision-not-satisfied", record["findings"])

    def test_a_partly_satisfied_mandatory_provision_is_still_missing(self):
        record = assess_provision(MANDATORY_PROVISION, "partially-satisfied")
        self.assertTrue(record["mandatory_missing"])

    def test_an_unevidenced_mandatory_provision_is_an_open_action_not_a_miss(self):
        record = assess_provision(MANDATORY_PROVISION, "satisfied-not-evidenced")
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("provision-not-evidenced", record["findings"])

    def test_an_unsatisfied_optional_provision_is_not_a_missing_mandatory(self):
        record = assess_provision(OPTIONAL_PROVISION, "not-satisfied")
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("provision-not-satisfied", record["findings"])

    def test_a_full_provision_set_reaches_a_full_index(self):
        records = [
            assess_provision(name, "satisfied-and-evidenced") for name in SCREENING_PROVISIONS
        ]
        self.assertAlmostEqual(provision_index(records), 1.0, places=9)

    def test_an_empty_provision_set_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_index([])


class BatchYieldTests(unittest.TestCase):
    def test_a_clean_batch_loses_nothing_to_screening(self):
        self.assertAlmostEqual(batch_reject_fraction(0, BATCH_SIZE), 0.0, places=9)

    def test_the_reject_fraction_is_rejects_over_the_batch(self):
        self.assertAlmostEqual(batch_reject_fraction(7, BATCH_SIZE), 0.07, places=9)

    def test_more_rejects_than_units_is_rejected_as_an_input_error(self):
        with self.assertRaises(ValueError):
            batch_reject_fraction(BATCH_SIZE + 1, BATCH_SIZE)

    def test_a_negative_reject_count_is_rejected(self):
        with self.assertRaises(ValueError):
            batch_reject_fraction(-1, BATCH_SIZE)

    def test_a_batch_exactly_on_the_allowance_is_inside_it(self):
        rejects = int(round(DEFAULT_REJECT_ALLOWANCE * BATCH_SIZE))
        self.assertAlmostEqual(
            batch_reject_fraction(rejects, BATCH_SIZE), DEFAULT_REJECT_ALLOWANCE, places=9
        )
        self.assertTrue(batch_within_reject_allowance(rejects, BATCH_SIZE))

    def test_a_batch_one_unit_past_the_allowance_is_outside_it(self):
        rejects = int(round(DEFAULT_REJECT_ALLOWANCE * BATCH_SIZE)) + 1
        self.assertFalse(batch_within_reject_allowance(rejects, BATCH_SIZE))

    def test_a_tighter_allowance_can_be_named_for_a_programme(self):
        self.assertFalse(batch_within_reject_allowance(5, BATCH_SIZE, 0.02))
        self.assertTrue(batch_within_reject_allowance(1, BATCH_SIZE, 0.02))

    def test_an_allowance_outside_zero_to_one_is_rejected(self):
        with self.assertRaises(ValueError):
            batch_within_reject_allowance(1, BATCH_SIZE, 1.5)

    def test_the_survivors_are_the_batch_less_its_rejects(self):
        self.assertEqual(surviving_units(5, BATCH_SIZE), BATCH_SIZE - 5)

    def test_a_first_rescreen_pass_is_within_the_limit(self):
        self.assertTrue(rescreen_within_limit(MAXIMUM_RESCREEN_CYCLES))

    def test_a_pass_beyond_the_limit_is_outside_it(self):
        self.assertFalse(rescreen_within_limit(MAXIMUM_RESCREEN_CYCLES + 1))

    def test_a_fractional_rescreen_count_is_rejected(self):
        with self.assertRaises(ValueError):
            rescreen_within_limit(1.5)


class WholeProgrammeTests(unittest.TestCase):
    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_complete_programme_on_a_healthy_batch_is_satisfied(self):
        result = run()
        self.assertEqual(result["verdict"], "screening-provisions-satisfied")
        self.assertTrue(result["batch_releasable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["provision_index"], 1.0, places=9)

    def test_a_sample_only_screen_fails_the_mandatory_provision(self):
        result = run(
            provisions=every_provision(
                **{"screening-applied-to-every-delivered-unit": "not-satisfied"}
            )
        )
        self.assertEqual(result["verdict"], "screening-provisions-not-satisfied")
        self.assertFalse(result["batch_releasable"])

    def test_a_criterion_settled_after_the_run_fails_the_mandatory_provision(self):
        result = run(
            provisions=every_provision(
                **{"reject-criteria-fixed-before-the-run": "partially-satisfied"}
            )
        )
        self.assertEqual(result["verdict"], "screening-provisions-not-satisfied")

    def test_an_unsatisfied_optional_provision_leaves_the_programme_open(self):
        result = run(provisions=every_provision(**{OPTIONAL_PROVISION: "not-satisfied"}))
        self.assertEqual(
            result["verdict"], "screening-provisions-satisfied-with-open-actions"
        )
        self.assertTrue(result["batch_releasable"])

    def test_a_low_index_denies_the_programme_even_with_the_mandatory_four_held(self):
        result = run(
            provisions=every_provision(
                **{
                    "screening-equipment-calibration-current": "not-satisfied",
                    "rework-and-rescreen-rules-defined": "not-satisfied",
                    "screening-results-named-in-the-delivery-record": "not-satisfied",
                    OPTIONAL_PROVISION: "not-satisfied",
                }
            )
        )
        self.assertLess(result["provision_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "screening-provisions-not-satisfied")

    def test_a_batch_over_the_reject_allowance_is_rejected_on_yield(self):
        rejects = int(round(DEFAULT_REJECT_ALLOWANCE * BATCH_SIZE)) + 1
        result = run(rejected_units=rejects)
        self.assertEqual(result["verdict"], "batch-rejected-on-screening-yield")
        self.assertFalse(result["within_reject_allowance"])

    def test_a_batch_exactly_on_the_allowance_is_not_rejected_on_yield(self):
        rejects = int(round(DEFAULT_REJECT_ALLOWANCE * BATCH_SIZE))
        result = run(rejected_units=rejects)
        self.assertEqual(result["verdict"], "screening-provisions-satisfied")

    def test_a_batch_rescreened_past_the_limit_is_rejected_on_yield(self):
        result = run(rescreen_cycles=MAXIMUM_RESCREEN_CYCLES + 1)
        self.assertEqual(result["verdict"], "batch-rejected-on-screening-yield")
        self.assertFalse(result["within_rescreen_limit"])

    def test_a_batch_with_no_survivor_is_rejected_on_yield(self):
        result = run(batch_size=4, rejected_units=4)
        self.assertEqual(result["verdict"], "batch-rejected-on-screening-yield")
        self.assertEqual(result["surviving_units"], 0)

    def test_yield_rejection_outranks_a_perfect_provision_set(self):
        result = run(rejected_units=BATCH_SIZE // 2)
        self.assertAlmostEqual(result["provision_index"], 1.0, places=9)
        self.assertEqual(result["verdict"], "batch-rejected-on-screening-yield")

    def test_a_provision_nobody_mentioned_is_graded_as_not_satisfied(self):
        result = run(provisions={MANDATORY_PROVISION: "satisfied-and-evidenced"})
        states = {r["provision"]: r["state"] for r in result["provision_records"]}
        self.assertEqual(states[OPTIONAL_PROVISION], "not-satisfied")
        self.assertEqual(len(result["provision_records"]), len(SCREENING_PROVISIONS))

    def test_an_unknown_provision_in_the_input_is_rejected(self):
        with self.assertRaises(ValueError):
            run(provisions={"we-always-do-it-this-way": "satisfied-and-evidenced"})

    def test_a_non_mapping_provision_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(provisions=[MANDATORY_PROVISION])

    def test_a_blank_batch_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(batch_id=" ")

    def test_a_zero_batch_size_is_rejected(self):
        with self.assertRaises(ValueError):
            run(batch_size=0)


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(PROVISION_TOLERANCE, 1e-6)

    def test_the_provision_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(PROVISION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(PROVISION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_full_provision_set(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)

    def test_the_reject_allowance_is_a_minority_of_the_batch(self):
        self.assertLess(DEFAULT_REJECT_ALLOWANCE, 0.5)


if __name__ == "__main__":
    unittest.main()
