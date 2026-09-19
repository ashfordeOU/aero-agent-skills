#!/usr/bin/env python3
"""Contract test for fastener tensile and proof-load acceptance (offline)."""

import copy
import math
import unittest

from q7046_tensile_and_proof_testing_logic import (
    FRACTURE_HEAD_FILLET,
    FRACTURE_IN_GRIPS,
    FRACTURE_SHANK,
    FRACTURE_THREAD_RUNOUT,
    PERMANENT_SET_LIMIT_MM,
    PITCH_FACTOR,
    PROPERTY_CLASSES,
    RESULT_FAIL,
    RESULT_INVALID,
    RESULT_PASS,
    VERDICT_ACCEPT,
    VERDICT_NO_VALID_SPECIMEN,
    VERDICT_REJECT,
    assess_tensile_programme,
    class_stresses,
    evaluate_proof_test,
    evaluate_tensile_test,
    fracture_is_valid,
    min_ultimate_load_n,
    permanent_set_mm,
    proof_load_n,
    thread_stress_area,
)

M8 = {"nominal_diameter_mm": 8.0, "pitch_mm": 1.25, "property_class": "10.9"}
M8_PROOF = proof_load_n(8.0, 1.25, "10.9")
M8_ULTIMATE = min_ultimate_load_n(8.0, 1.25, "10.9")

GOOD_CASE = {
    "nominal_diameter_mm": 8.0,
    "pitch_mm": 1.25,
    "property_class": "10.9",
    "proof_specimens": [
        {
            "applied_load_n": M8_PROOF * 1.01,
            "length_before_mm": 40.0,
            "length_after_mm": 40.0,
        }
    ],
    "tensile_specimens": [
        {
            "breaking_load_n": M8_ULTIMATE * 1.05,
            "fracture_location": "free-threaded-length",
        }
    ],
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class StressAreaTests(unittest.TestCase):
    def test_area_matches_the_diameter_minus_pitch_formula(self):
        expected = math.pi / 4.0 * (8.0 - PITCH_FACTOR * 1.25) ** 2
        self.assertAlmostEqual(thread_stress_area(8.0, 1.25), expected, places=9)

    def test_area_is_smaller_than_the_nominal_shank_area(self):
        nominal = math.pi / 4.0 * 8.0 ** 2
        self.assertLess(thread_stress_area(8.0, 1.25), nominal)

    def test_area_grows_with_diameter(self):
        self.assertGreater(
            thread_stress_area(10.0, 1.5), thread_stress_area(8.0, 1.25)
        )

    def test_coarser_pitch_reduces_the_area_at_the_same_diameter(self):
        self.assertLess(thread_stress_area(8.0, 1.25), thread_stress_area(8.0, 1.0))

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            thread_stress_area(0.0, 1.25)

    def test_negative_pitch_rejected(self):
        with self.assertRaises(ValueError):
            thread_stress_area(8.0, -1.25)

    def test_pitch_coarser_than_the_thread_rejected(self):
        with self.assertRaises(ValueError):
            thread_stress_area(2.0, 4.0)

    def test_non_numeric_diameter_rejected(self):
        with self.assertRaises(ValueError):
            thread_stress_area("M8", 1.25)


class PropertyClassTests(unittest.TestCase):
    def test_every_listed_class_has_both_stresses(self):
        for name in PROPERTY_CLASSES:
            stresses = class_stresses(name, 8.0)
            self.assertGreater(stresses["proof_mpa"], 0.0)
            self.assertGreater(stresses["ultimate_mpa"], stresses["proof_mpa"])

    def test_diameter_split_raises_the_proof_stress_of_a_large_size(self):
        small = class_stresses("8.8", 12.0)
        large = class_stresses("8.8", 20.0)
        self.assertGreater(large["proof_mpa"], small["proof_mpa"])
        self.assertTrue(large["diameter_split_applied"])

    def test_class_without_a_split_is_size_independent(self):
        self.assertEqual(
            class_stresses("12.9", 6.0)["proof_mpa"],
            class_stresses("12.9", 24.0)["proof_mpa"],
        )

    def test_unlisted_class_rejected(self):
        with self.assertRaises(ValueError):
            class_stresses("14.9", 8.0)


class AcceptanceLoadTests(unittest.TestCase):
    def test_proof_load_is_the_stress_area_times_the_proof_stress(self):
        area = thread_stress_area(8.0, 1.25)
        expected = area * class_stresses("10.9", 8.0)["proof_mpa"]
        self.assertAlmostEqual(proof_load_n(8.0, 1.25, "10.9"), expected, places=9)

    def test_ultimate_load_exceeds_the_proof_load(self):
        self.assertGreater(M8_ULTIMATE, M8_PROOF)

    def test_stronger_class_gives_a_higher_ultimate_load(self):
        self.assertGreater(
            min_ultimate_load_n(8.0, 1.25, "12.9"),
            min_ultimate_load_n(8.0, 1.25, "8.8"),
        )

    def test_unlisted_class_rejected_at_load_level(self):
        with self.assertRaises(ValueError):
            proof_load_n(8.0, 1.25, "stainless-ish")


class PermanentSetTests(unittest.TestCase):
    def test_unchanged_length_leaves_no_permanent_set(self):
        self.assertAlmostEqual(permanent_set_mm(40.0, 40.0), 0.0, places=9)

    def test_permanent_set_is_the_length_difference(self):
        self.assertAlmostEqual(permanent_set_mm(40.0, 40.02), 0.02, places=9)

    def test_a_specimen_shorter_than_it_started_rejected(self):
        with self.assertRaises(ValueError):
            permanent_set_mm(40.0, 39.5)

    def test_zero_starting_length_rejected(self):
        with self.assertRaises(ValueError):
            permanent_set_mm(0.0, 40.0)


class ProofTestTests(unittest.TestCase):
    def test_load_reached_and_no_set_passes(self):
        outcome = evaluate_proof_test(M8_PROOF * 1.01, M8_PROOF, 40.0, 40.0)
        self.assertEqual(outcome["result"], RESULT_PASS)

    def test_load_landing_exactly_on_the_proof_load_passes(self):
        outcome = evaluate_proof_test(M8_PROOF, M8_PROOF, 40.0, 40.0)
        self.assertEqual(outcome["result"], RESULT_PASS)
        self.assertAlmostEqual(
            outcome["applied_load_n"], outcome["required_proof_load_n"], places=9
        )

    def test_set_landing_exactly_on_the_limit_passes(self):
        outcome = evaluate_proof_test(
            M8_PROOF, M8_PROOF, 40.0, 40.0 + PERMANENT_SET_LIMIT_MM
        )
        self.assertEqual(outcome["result"], RESULT_PASS)
        self.assertAlmostEqual(
            outcome["permanent_set_mm"], PERMANENT_SET_LIMIT_MM, places=9
        )

    def test_yielded_specimen_fails_even_at_full_load(self):
        outcome = evaluate_proof_test(M8_PROOF * 1.2, M8_PROOF, 40.0, 40.1)
        self.assertEqual(outcome["result"], RESULT_FAIL)
        self.assertTrue(any("permanent set" in f for f in outcome["findings"]))

    def test_load_never_reached_fails_with_a_named_finding(self):
        outcome = evaluate_proof_test(M8_PROOF * 0.5, M8_PROOF, 40.0, 40.0)
        self.assertEqual(outcome["result"], RESULT_FAIL)
        self.assertTrue(any("proof load" in f for f in outcome["findings"]))

    def test_negative_applied_load_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_proof_test(-1.0, M8_PROOF, 40.0, 40.0)


class TensileTestTests(unittest.TestCase):
    def test_break_in_the_free_thread_above_the_minimum_passes(self):
        outcome = evaluate_tensile_test(
            M8_ULTIMATE * 1.1, M8_ULTIMATE, "free-threaded-length"
        )
        self.assertEqual(outcome["result"], RESULT_PASS)

    def test_break_exactly_on_the_minimum_load_passes(self):
        outcome = evaluate_tensile_test(M8_ULTIMATE, M8_ULTIMATE, FRACTURE_SHANK)
        self.assertEqual(outcome["result"], RESULT_PASS)
        self.assertAlmostEqual(
            outcome["breaking_load_n"],
            outcome["required_ultimate_load_n"],
            places=9,
        )

    def test_break_below_the_minimum_load_fails(self):
        outcome = evaluate_tensile_test(
            M8_ULTIMATE * 0.9, M8_ULTIMATE, FRACTURE_SHANK
        )
        self.assertEqual(outcome["result"], RESULT_FAIL)

    def test_break_in_the_grips_is_invalid_not_a_failure(self):
        outcome = evaluate_tensile_test(
            M8_ULTIMATE * 0.4, M8_ULTIMATE, FRACTURE_IN_GRIPS
        )
        self.assertEqual(outcome["result"], RESULT_INVALID)

    def test_head_fillet_break_fails_at_any_load(self):
        outcome = evaluate_tensile_test(
            M8_ULTIMATE * 2.0, M8_ULTIMATE, FRACTURE_HEAD_FILLET
        )
        self.assertEqual(outcome["result"], RESULT_FAIL)

    def test_thread_runout_break_fails_at_any_load(self):
        outcome = evaluate_tensile_test(
            M8_ULTIMATE * 1.5, M8_ULTIMATE, FRACTURE_THREAD_RUNOUT
        )
        self.assertEqual(outcome["result"], RESULT_FAIL)

    def test_only_thread_and_shank_breaks_are_valid(self):
        self.assertTrue(fracture_is_valid("free-threaded-length"))
        self.assertTrue(fracture_is_valid(FRACTURE_SHANK))
        self.assertFalse(fracture_is_valid(FRACTURE_HEAD_FILLET))

    def test_unknown_fracture_location_rejected(self):
        with self.assertRaises(ValueError):
            fracture_is_valid("somewhere-near-the-middle")


class ProgrammeTests(unittest.TestCase):
    def test_clean_programme_accepts_the_lot(self):
        result = assess_tensile_programme(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_one_weak_tensile_specimen_rejects_the_lot(self):
        case = _case(
            tensile_specimens=[
                {
                    "breaking_load_n": M8_ULTIMATE * 1.2,
                    "fracture_location": "free-threaded-length",
                },
                {
                    "breaking_load_n": M8_ULTIMATE * 0.8,
                    "fracture_location": "free-threaded-length",
                },
            ]
        )
        self.assertEqual(assess_tensile_programme(case)["verdict"], VERDICT_REJECT)

    def test_worst_specimen_is_reported_not_the_mean(self):
        case = _case(
            tensile_specimens=[
                {
                    "breaking_load_n": M8_ULTIMATE * 1.4,
                    "fracture_location": "free-threaded-length",
                },
                {
                    "breaking_load_n": M8_ULTIMATE * 1.05,
                    "fracture_location": FRACTURE_SHANK,
                },
            ]
        )
        result = assess_tensile_programme(case)
        self.assertAlmostEqual(
            result["worst_breaking_load_n"], M8_ULTIMATE * 1.05, places=6
        )

    def test_in_grip_specimen_is_counted_as_owed_not_as_a_failure(self):
        case = _case(
            tensile_specimens=[
                {
                    "breaking_load_n": M8_ULTIMATE * 1.1,
                    "fracture_location": "free-threaded-length",
                },
                {
                    "breaking_load_n": M8_ULTIMATE * 0.3,
                    "fracture_location": FRACTURE_IN_GRIPS,
                },
            ]
        )
        result = assess_tensile_programme(case)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["invalid_specimens"], 1)

    def test_a_set_of_only_invalid_specimens_yields_no_verdict(self):
        case = _case(
            proof_specimens=[],
            tensile_specimens=[
                {
                    "breaking_load_n": M8_ULTIMATE * 0.3,
                    "fracture_location": FRACTURE_IN_GRIPS,
                }
            ],
        )
        result = assess_tensile_programme(case)
        self.assertEqual(result["verdict"], VERDICT_NO_VALID_SPECIMEN)

    def test_programme_reports_both_acceptance_loads(self):
        result = assess_tensile_programme(_case())
        self.assertAlmostEqual(result["required_proof_load_n"], M8_PROOF, places=9)
        self.assertAlmostEqual(
            result["required_ultimate_load_n"], M8_ULTIMATE, places=9
        )

    def test_missing_pitch_rejected(self):
        case = _case()
        del case["pitch_mm"]
        with self.assertRaises(ValueError):
            assess_tensile_programme(case)

    def test_specimen_list_given_as_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_tensile_programme(_case(tensile_specimens={"one": 1}))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_tensile_programme("pull the M8 bolts")


if __name__ == "__main__":
    unittest.main()
