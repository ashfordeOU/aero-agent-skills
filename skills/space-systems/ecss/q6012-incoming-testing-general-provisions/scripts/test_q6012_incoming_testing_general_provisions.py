"""Contract tests for the clause 10.3.1 receipt testing general provisions."""

import unittest

from q6012_incoming_testing_general_provisions_logic import (
    ACCEPTANCE_QUALITIES,
    CODE_LETTERS,
    INSPECTION_LEVELS,
    REDUCE_AFTER_ACCEPTS,
    RELAX_AFTER_ACCEPTS,
    SEVERITIES,
    TIGHTEN_AFTER_REJECTS,
    TIGHTEN_WINDOW,
    acceptance_number,
    apply_severity,
    assess_receipt_testing,
    base_sample_size,
    code_letter,
    lot_disposition,
    next_severity,
    receipt_findings,
    sampling_plan,
)


class RegistryTests(unittest.TestCase):
    def test_code_letters_are_unique(self):
        self.assertEqual(len(CODE_LETTERS), len(set(CODE_LETTERS)))

    def test_every_code_letter_has_a_size_at_every_level(self):
        for letter in CODE_LETTERS:
            for level in INSPECTION_LEVELS:
                self.assertGreaterEqual(base_sample_size(letter, level), 1)

    def test_sample_size_grows_with_the_inspection_level(self):
        for letter in CODE_LETTERS:
            sizes = [base_sample_size(letter, lvl) for lvl in INSPECTION_LEVELS]
            self.assertEqual(sizes, sorted(sizes))

    def test_acceptance_qualities_are_whole_permille_values(self):
        for value in ACCEPTANCE_QUALITIES.values():
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)

    def test_switching_constants_are_coherent(self):
        self.assertGreaterEqual(TIGHTEN_WINDOW, TIGHTEN_AFTER_REJECTS)
        self.assertGreater(REDUCE_AFTER_ACCEPTS, RELAX_AFTER_ACCEPTS)
        self.assertEqual(SEVERITIES, ("reduced", "normal", "tightened"))


class CodeLetterTests(unittest.TestCase):
    def test_smallest_lot_takes_the_first_band(self):
        self.assertEqual(code_letter(1), "A")

    def test_band_upper_bound_stays_in_its_band(self):
        self.assertEqual(code_letter(8), "A")
        self.assertEqual(code_letter(9), "B")

    def test_a_large_lot_takes_the_open_top_band(self):
        self.assertEqual(code_letter(50000), "G")

    def test_band_is_the_same_across_a_whole_band(self):
        self.assertEqual(code_letter(300), code_letter(1200))
        self.assertNotEqual(code_letter(1200), code_letter(1201))

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            code_letter(0)

    def test_fractional_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            code_letter(300.5)

    def test_boolean_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            code_letter(True)

    def test_unknown_code_letter_rejected(self):
        with self.assertRaises(ValueError):
            base_sample_size("Z", "general-ii")

    def test_unknown_inspection_level_rejected(self):
        with self.assertRaises(ValueError):
            base_sample_size("D", "general-iv")


class AcceptanceNumberTests(unittest.TestCase):
    def test_zero_defect_quality_permits_nothing(self):
        self.assertEqual(acceptance_number(80, "zero-defect"), 0)

    def test_acceptance_number_is_integer_division_of_permille(self):
        self.assertEqual(acceptance_number(80, "major-25"), 2)
        self.assertEqual(acceptance_number(40, "major-25"), 1)
        self.assertEqual(acceptance_number(39, "major-25"), 0)

    def test_a_looser_quality_permits_at_least_as_many(self):
        self.assertGreaterEqual(
            acceptance_number(50, "minor-65"), acceptance_number(50, "major-25")
        )

    def test_unknown_quality_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_number(50, "whatever-is-fine")

    def test_zero_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_number(0, "major-25")


class SeverityTests(unittest.TestCase):
    def test_normal_severity_changes_nothing(self):
        self.assertEqual(apply_severity(32, 2, "normal"), (32, 2))

    def test_tightened_severity_lowers_the_acceptance_number(self):
        self.assertEqual(apply_severity(32, 2, "tightened"), (32, 1))

    def test_tightened_severity_cannot_go_below_zero(self):
        self.assertEqual(apply_severity(32, 0, "tightened"), (32, 0))

    def test_reduced_severity_halves_the_draw(self):
        self.assertEqual(apply_severity(32, 2, "reduced"), (16, 2))

    def test_reduced_severity_keeps_a_floor_under_the_sample(self):
        sample, _accept = apply_severity(2, 0, "reduced")
        self.assertGreaterEqual(sample, 2)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            apply_severity(32, 2, "relaxed")


class SamplingPlanTests(unittest.TestCase):
    def test_plan_for_a_mid_sized_lot(self):
        plan = sampling_plan(500, "general-ii", "major-25", "normal")
        self.assertEqual(plan["code_letter"], "E")
        self.assertEqual(plan["sample_size"], 20)
        self.assertEqual(plan["acceptance_number"], 0)
        self.assertEqual(plan["rejection_number"], 1)
        self.assertFalse(plan["hundred_percent"])

    def test_small_lot_becomes_hundred_percent_inspection(self):
        plan = sampling_plan(2, "general-iii", "major-25", "normal")
        self.assertTrue(plan["hundred_percent"])
        self.assertEqual(plan["sample_size"], 2)
        self.assertAlmostEqual(plan["sampled_fraction"], 1.0, places=9)

    def test_tightened_plan_is_never_easier_than_normal(self):
        normal = sampling_plan(3000, "general-iii", "minor-65", "normal")
        tight = sampling_plan(3000, "general-iii", "minor-65", "tightened")
        self.assertEqual(normal["sample_size"], tight["sample_size"])
        self.assertLessEqual(tight["acceptance_number"], normal["acceptance_number"])

    def test_reduced_plan_draws_fewer_items(self):
        normal = sampling_plan(3000, "general-iii", "minor-65", "normal")
        light = sampling_plan(3000, "general-iii", "minor-65", "reduced")
        self.assertLess(light["sample_size"], normal["sample_size"])

    def test_sampled_fraction_falls_as_the_lot_grows(self):
        small = sampling_plan(100)
        large = sampling_plan(10000)
        self.assertLess(large["sampled_fraction"], small["sampled_fraction"])

    def test_plan_rejects_an_unknown_level(self):
        with self.assertRaises(ValueError):
            sampling_plan(500, "general-iv")

    def test_plan_rejects_a_zero_lot(self):
        with self.assertRaises(ValueError):
            sampling_plan(0)


class DispositionTests(unittest.TestCase):
    def setUp(self):
        self.plan = sampling_plan(3000, "general-iii", "minor-65", "normal")

    def test_defectives_at_the_acceptance_number_accept(self):
        self.assertEqual(
            lot_disposition(self.plan, self.plan["acceptance_number"]), "accept"
        )

    def test_defectives_at_the_rejection_number_reject(self):
        self.assertEqual(
            lot_disposition(self.plan, self.plan["rejection_number"]), "reject"
        )

    def test_clean_sample_accepts(self):
        self.assertEqual(lot_disposition(self.plan, 0), "accept")

    def test_more_defectives_than_the_sample_rejected_as_an_error(self):
        with self.assertRaises(ValueError):
            lot_disposition(self.plan, self.plan["sample_size"] + 1)

    def test_negative_defectives_rejected(self):
        with self.assertRaises(ValueError):
            lot_disposition(self.plan, -1)

    def test_disposition_rejects_a_foreign_plan(self):
        with self.assertRaises(ValueError):
            lot_disposition({"sample_size": 10}, 0)


class SwitchingTests(unittest.TestCase):
    def test_two_rejects_in_the_window_tighten_from_normal(self):
        history = ["accept", "reject", "accept", "reject", "accept"]
        self.assertEqual(next_severity("normal", history), "tightened")

    def test_two_rejects_outside_the_window_do_not_tighten(self):
        history = ["reject", "reject"] + ["accept"] * TIGHTEN_WINDOW
        self.assertEqual(next_severity("normal", history), "normal")

    def test_a_long_clean_run_reduces_from_normal(self):
        history = ["accept"] * REDUCE_AFTER_ACCEPTS
        self.assertEqual(next_severity("normal", history), "reduced")

    def test_a_clean_run_relaxes_tightened_back_to_normal(self):
        history = ["accept"] * RELAX_AFTER_ACCEPTS
        self.assertEqual(next_severity("tightened", history), "normal")

    def test_tightened_stays_tightened_on_a_short_clean_run(self):
        history = ["accept"] * (RELAX_AFTER_ACCEPTS - 1)
        self.assertEqual(next_severity("tightened", history), "tightened")

    def test_a_single_reject_ends_reduced_inspection(self):
        self.assertEqual(next_severity("reduced", ["accept", "reject"]), "normal")

    def test_reduced_survives_a_clean_lot(self):
        self.assertEqual(next_severity("reduced", ["accept"]), "reduced")

    def test_unknown_lot_result_rejected(self):
        with self.assertRaises(ValueError):
            next_severity("normal", ["accept", "maybe"])

    def test_non_sequence_history_rejected(self):
        with self.assertRaises(ValueError):
            next_severity("normal", "accept")


class AssessmentTests(unittest.TestCase):
    def test_clean_lot_is_released(self):
        result = assess_receipt_testing({"lot_size": 3000, "defectives": 0,
                                         "level": "general-iii",
                                         "quality": "minor-65"})
        self.assertEqual(result["disposition"], "accept")
        self.assertTrue(result["released_to_production"])

    def test_rejected_lot_is_not_released_and_says_why(self):
        result = assess_receipt_testing({"lot_size": 500, "defectives": 3})
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["released_to_production"])
        self.assertTrue(any("lot rejected" in f for f in result["findings"]))

    def test_zero_acceptance_number_is_called_out(self):
        result = assess_receipt_testing({"lot_size": 500, "defectives": 0,
                                         "quality": "zero-defect"})
        self.assertTrue(
            any("acceptance number is zero" in f for f in result["findings"])
        )

    def test_hundred_percent_inspection_is_called_out(self):
        result = assess_receipt_testing({"lot_size": 2, "defectives": 0})
        self.assertTrue(
            any("one hundred percent" in f for f in result["findings"])
        )

    def test_accepted_lot_with_defectives_still_warns(self):
        result = assess_receipt_testing({"lot_size": 3000, "defectives": 1,
                                         "level": "general-iii",
                                         "quality": "minor-65"})
        self.assertEqual(result["disposition"], "accept")
        self.assertTrue(any("still" in f for f in result["findings"]))

    def test_a_rejection_after_a_prior_one_tightens_the_next_lot(self):
        result = assess_receipt_testing(
            {"lot_size": 500, "defectives": 3, "history": ["reject", "accept"]}
        )
        self.assertEqual(result["next_severity"], "tightened")
        self.assertTrue(any("severity moves" in f for f in result["findings"]))

    def test_assessment_rejects_an_unknown_key(self):
        with self.assertRaises(ValueError):
            assess_receipt_testing({"lot_size": 500, "defectives": 0,
                                    "levle": "general-ii"})

    def test_assessment_requires_defectives(self):
        with self.assertRaises(ValueError):
            assess_receipt_testing({"lot_size": 500})

    def test_findings_reject_a_foreign_plan(self):
        with self.assertRaises(ValueError):
            receipt_findings({"sample_size": 10}, 0, "accept", "normal")


if __name__ == "__main__":
    unittest.main()
