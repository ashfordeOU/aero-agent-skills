#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.3 screening sequence leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_hybrid_screening_sequence.py
"""

import unittest

from q6005_hybrid_screening_sequence_logic import (
    ACCEPTANCE_INDEX,
    MANDATORY_SCREENING_STEPS,
    POST_SEAL_STAGE,
    PRE_SEAL_STAGE,
    SCREENING_STEPS,
    SCREENING_TOLERANCE,
    SEALING_STEP,
    SEAL_STAGE,
    STEP_OUTCOME_CREDIT,
    VERDICTS,
    assess_screening_sequence,
    batch_coverage_shortfalls,
    canonical_position,
    canonical_sequence,
    grade_step,
    inverted_steps,
    missing_mandatory_steps,
    normalize_sequence,
    outcome_credit,
    sequence_conformity_index,
    stage_violations,
    step_stage,
    step_weight,
)

BATCH_SIZE = 50
OPTIONAL_STEP = "hybrid-radiographic-inspection"


def full_sequence(units=BATCH_SIZE, order=None, drop=()):
    """Every screening step, in canonical order unless told otherwise."""
    names = list(canonical_sequence() if order is None else order)
    return [
        {"step": name, "applied_units": units}
        for name in names
        if name not in drop
    ]


def swapped(first, second):
    """The canonical sequence with two steps exchanged."""
    names = list(canonical_sequence())
    i, j = names.index(first), names.index(second)
    names[i], names[j] = names[j], names[i]
    return names


def run(**overrides):
    """Grade one performed screening sequence."""
    case = {
        "batch_id": "BATCH-01",
        "batch_size": BATCH_SIZE,
        "sequence": full_sequence(),
    }
    case.update(overrides)
    return assess_screening_sequence(**case)


class CanonicalSequenceTests(unittest.TestCase):
    def test_every_step_carries_a_position_a_stage_and_a_weight(self):
        for name in SCREENING_STEPS:
            self.assertIsInstance(canonical_position(name), int)
            self.assertIn(step_stage(name), (PRE_SEAL_STAGE, SEAL_STAGE, POST_SEAL_STAGE))
            self.assertGreater(step_weight(name), 0.0)

    def test_an_unknown_step_name_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical_position("shake-it-and-listen")

    def test_the_canonical_sequence_is_strictly_increasing(self):
        positions = [canonical_position(name) for name in canonical_sequence()]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(set(positions)), len(positions))

    def test_the_seal_is_the_only_step_in_the_sealing_stage(self):
        sealing = [n for n in SCREENING_STEPS if step_stage(n) == SEAL_STAGE]
        self.assertEqual(sealing, [SEALING_STEP])

    def test_every_pre_seal_step_sits_before_the_seal_in_the_canonical_order(self):
        seal = canonical_position(SEALING_STEP)
        for name in SCREENING_STEPS:
            if step_stage(name) == PRE_SEAL_STAGE:
                self.assertLess(canonical_position(name), seal)
            elif step_stage(name) == POST_SEAL_STAGE:
                self.assertGreater(canonical_position(name), seal)

    def test_every_mandatory_step_is_a_published_step(self):
        for name in MANDATORY_SCREENING_STEPS:
            self.assertIn(name, SCREENING_STEPS)

    def test_an_unknown_step_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            outcome_credit("looked-fine-on-the-bench")


class SequenceValidationTests(unittest.TestCase):
    def test_a_repeated_step_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sequence(list(canonical_sequence()) + [SEALING_STEP])

    def test_an_empty_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sequence([])

    def test_a_non_sequence_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sequence({"step": SEALING_STEP})

    def test_a_bare_step_name_is_read_as_a_step_with_no_unit_count(self):
        record = normalize_sequence([SEALING_STEP])[0]
        self.assertEqual(record["step"], SEALING_STEP)
        self.assertIsNone(record["applied_units"])

    def test_a_zero_unit_count_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sequence([{"step": SEALING_STEP, "applied_units": 0}])


class OrderingTests(unittest.TestCase):
    def test_a_canonical_run_has_no_inversion(self):
        self.assertEqual(inverted_steps(full_sequence()), [])

    def test_a_swap_names_both_steps_it_involves(self):
        names = swapped("hybrid-package-thermal-cycling", "hybrid-constant-acceleration-screen")
        self.assertEqual(
            inverted_steps(names),
            sorted(["hybrid-package-thermal-cycling", "hybrid-constant-acceleration-screen"]),
        )

    def test_a_canonical_run_has_no_stage_violation(self):
        self.assertEqual(stage_violations(full_sequence()), [])

    def test_a_pre_seal_step_run_after_the_seal_is_a_stage_violation(self):
        names = [n for n in canonical_sequence() if n != "pre-seal-thermographic-imaging"]
        names.append("pre-seal-thermographic-imaging")
        self.assertIn("pre-seal-thermographic-imaging", stage_violations(names))

    def test_a_post_seal_step_run_before_the_seal_is_a_stage_violation(self):
        names = [n for n in canonical_sequence() if n != "hybrid-seal-fine-and-gross-leak-test"]
        names.insert(0, "hybrid-seal-fine-and-gross-leak-test")
        self.assertIn("hybrid-seal-fine-and-gross-leak-test", stage_violations(names))

    def test_a_sequence_without_the_seal_reports_no_stage_violation(self):
        names = [n for n in canonical_sequence() if n != SEALING_STEP]
        self.assertEqual(stage_violations(names), [])


class BatchCoverageTests(unittest.TestCase):
    def test_a_full_batch_run_has_no_shortfall(self):
        self.assertEqual(batch_coverage_shortfalls(full_sequence(), BATCH_SIZE), [])

    def test_a_step_run_on_part_of_the_batch_is_named(self):
        sequence = full_sequence()
        sequence[3]["applied_units"] = BATCH_SIZE - 1
        self.assertEqual(
            batch_coverage_shortfalls(sequence, BATCH_SIZE), [sequence[3]["step"]]
        )

    def test_a_step_claiming_more_units_than_the_batch_holds_is_rejected(self):
        sequence = full_sequence()
        sequence[0]["applied_units"] = BATCH_SIZE + 1
        with self.assertRaises(ValueError):
            batch_coverage_shortfalls(sequence, BATCH_SIZE)

    def test_a_step_with_no_declared_count_is_read_as_the_whole_batch(self):
        self.assertEqual(batch_coverage_shortfalls([SEALING_STEP], BATCH_SIZE), [])

    def test_a_zero_batch_size_is_rejected(self):
        with self.assertRaises(ValueError):
            batch_coverage_shortfalls(full_sequence(), 0)


class StepGradingTests(unittest.TestCase):
    def test_an_in_order_step_earns_its_full_weight(self):
        record = grade_step(SEALING_STEP, False, False, False, True)
        self.assertAlmostEqual(record["weighted_credit"], step_weight(SEALING_STEP), places=9)
        self.assertEqual(record["findings"], [])

    def test_a_stage_violation_outranks_an_inversion_on_the_same_step(self):
        record = grade_step("pre-seal-burn-in-soak", True, True, True, True)
        self.assertEqual(record["outcome"], "performed-on-the-wrong-side-of-the-seal")

    def test_a_missing_mandatory_step_is_marked_missing(self):
        record = grade_step(SEALING_STEP, False, False, False, False)
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-screening-step-not-performed", record["findings"])

    def test_a_missing_optional_step_is_a_finding_but_not_a_missing_mandatory(self):
        record = grade_step(OPTIONAL_STEP, False, False, False, False)
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("not-performed", record["findings"])

    def test_an_empty_step_set_has_no_index(self):
        with self.assertRaises(ValueError):
            sequence_conformity_index([])

    def test_a_canonical_run_reaches_a_full_index(self):
        records = [grade_step(n, False, False, False, True) for n in canonical_sequence()]
        self.assertAlmostEqual(sequence_conformity_index(records), 1.0, places=9)


class WholeSequenceTests(unittest.TestCase):
    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_canonical_full_batch_run_is_accepted(self):
        result = run()
        self.assertEqual(result["verdict"], "screening-sequence-accepted")
        self.assertTrue(result["sequence_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["sequence_conformity_index"], 1.0, places=9)

    def test_a_dropped_mandatory_step_leaves_the_sequence_incomplete(self):
        result = run(sequence=full_sequence(drop=("final-electrical-measurement",)))
        self.assertEqual(result["verdict"], "screening-sequence-incomplete")
        self.assertIn("final-electrical-measurement", result["missing_mandatory_steps"])

    def test_a_dropped_optional_step_does_not_make_the_sequence_incomplete(self):
        result = run(sequence=full_sequence(drop=(OPTIONAL_STEP,)))
        self.assertNotEqual(result["verdict"], "screening-sequence-incomplete")
        self.assertEqual(result["missing_mandatory_steps"], [])

    def test_a_partial_batch_step_denies_the_sequence(self):
        sequence = full_sequence()
        sequence[-1]["applied_units"] = BATCH_SIZE - 2
        result = run(sequence=sequence)
        self.assertEqual(result["verdict"], "screening-sequence-not-accepted")
        self.assertEqual(result["coverage_shortfalls"], [sequence[-1]["step"]])

    def test_a_step_on_the_wrong_side_of_the_seal_denies_the_sequence(self):
        names = [n for n in canonical_sequence() if n != "internal-circuit-photographic-record"]
        names.append("internal-circuit-photographic-record")
        result = run(sequence=full_sequence(order=names))
        self.assertEqual(result["verdict"], "screening-sequence-not-accepted")
        self.assertIn("internal-circuit-photographic-record", result["stage_violations"])

    def test_a_small_inversion_leaves_the_sequence_open_not_denied(self):
        names = swapped("hybrid-package-thermal-cycling", "hybrid-constant-acceleration-screen")
        result = run(sequence=full_sequence(order=names))
        self.assertEqual(result["verdict"], "screening-sequence-accepted-with-open-actions")
        self.assertGreater(result["sequence_conformity_index"], ACCEPTANCE_INDEX)

    def test_a_wide_inversion_falls_under_the_acceptance_index(self):
        names = swapped("hybrid-package-thermal-cycling", "final-electrical-measurement")
        result = run(sequence=full_sequence(order=names))
        self.assertLess(result["sequence_conformity_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "screening-sequence-not-accepted")

    def test_a_blank_batch_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(batch_id="  ")

    def test_every_published_step_appears_in_the_graded_record(self):
        result = run(sequence=full_sequence(drop=(OPTIONAL_STEP,)))
        self.assertEqual(len(result["step_records"]), len(SCREENING_STEPS))
        outcomes = {r["step"]: r["outcome"] for r in result["step_records"]}
        self.assertEqual(outcomes[OPTIONAL_STEP], "not-performed")


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(SCREENING_TOLERANCE, 1e-6)

    def test_the_step_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(STEP_OUTCOME_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(STEP_OUTCOME_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_canonical_run(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)


if __name__ == "__main__":
    unittest.main()
