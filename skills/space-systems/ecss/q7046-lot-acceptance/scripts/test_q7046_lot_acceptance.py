#!/usr/bin/env python3
"""Contract test for fastener lot acceptance sampling (offline)."""

import unittest

from q7046_lot_acceptance_logic import (
    CRITICALITIES,
    LOT_ACCEPT,
    LOT_REJECT,
    SEVERITY_NORMAL,
    SEVERITY_REDUCED,
    SEVERITY_SUSPENDED,
    SEVERITY_TIGHTENED,
    acceptance_plan,
    judge_lot,
    letter_sample_size,
    next_severity,
    resolve_plan,
    sample_code_letter,
)


class CodeLetterTests(unittest.TestCase):
    def test_letter_follows_the_lot_size_bands(self):
        self.assertEqual(sample_code_letter(8), "A")
        self.assertEqual(sample_code_letter(9), "B")
        self.assertEqual(sample_code_letter(900), "J")
        self.assertEqual(sample_code_letter(3200), "K")

    def test_a_lot_beyond_the_table_takes_the_largest_letter(self):
        self.assertEqual(sample_code_letter(900000), "Q")
        self.assertEqual(letter_sample_size("Q"), 1250)

    def test_letter_is_monotone_in_the_lot_size(self):
        previous = 0
        for lot in (2, 9, 16, 26, 51, 91, 151, 281, 501, 1201, 3201, 10001):
            current = letter_sample_size(sample_code_letter(lot))
            self.assertGreater(current, previous)
            previous = current

    def test_a_lot_of_one_cannot_be_sampled(self):
        with self.assertRaises(ValueError):
            sample_code_letter(1)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_code_letter(0)

    def test_unknown_letter_rejected(self):
        with self.assertRaises(ValueError):
            letter_sample_size("Z")


class ResolvePlanTests(unittest.TestCase):
    def test_a_sample_too_small_for_the_limit_steps_up(self):
        plan = resolve_plan(30, "2.5")
        self.assertTrue(plan["stepped_up"])
        self.assertEqual(plan["sample_size"], 13)
        self.assertEqual(plan["accept_number"], 0)

    def test_a_sample_that_discriminates_does_not_step_up(self):
        plan = resolve_plan(900, "2.5")
        self.assertFalse(plan["stepped_up"])
        self.assertEqual(plan["sample_size"], 80)

    def test_a_sample_reaching_the_lot_becomes_whole_lot_inspection(self):
        plan = resolve_plan(10, "2.5")
        self.assertTrue(plan["hundred_percent"])
        self.assertEqual(plan["sample_size"], 10)
        self.assertEqual(plan["accept_number"], 0)

    def test_reject_number_is_always_one_past_accept(self):
        for lot in (30, 200, 900, 5000, 40000):
            for limit in ("0.65", "1.0", "2.5"):
                plan = resolve_plan(lot, limit)
                self.assertEqual(
                    plan["reject_number"], plan["accept_number"] + 1
                )

    def test_a_finer_limit_never_allows_more_than_a_coarser_one(self):
        for lot in (500, 900, 5000, 40000):
            fine = resolve_plan(lot, "0.65")
            coarse = resolve_plan(lot, "2.5")
            self.assertLessEqual(fine["accept_number"], coarse["accept_number"])

    def test_unknown_quality_limit_rejected(self):
        with self.assertRaises(ValueError):
            resolve_plan(900, "4.0")


class AcceptancePlanTests(unittest.TestCase):
    def test_a_critical_lot_is_inspected_whole(self):
        plan = acceptance_plan(4000, "critical")
        self.assertTrue(plan["hundred_percent"])
        self.assertEqual(plan["sample_size"], 4000)
        self.assertEqual(plan["accept_number"], 0)

    def test_a_critical_lot_of_one_is_still_inspectable(self):
        plan = acceptance_plan(1, "critical")
        self.assertEqual(plan["sample_size"], 1)

    def test_a_sampled_lot_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            acceptance_plan(1, "minor")

    def test_severity_moves_the_quality_limit_in_both_directions(self):
        tight = acceptance_plan(900, "major", SEVERITY_TIGHTENED)
        normal = acceptance_plan(900, "major", SEVERITY_NORMAL)
        reduced = acceptance_plan(900, "major", SEVERITY_REDUCED)
        self.assertLess(tight["accept_number"], normal["accept_number"])
        self.assertLess(normal["accept_number"], reduced["accept_number"])

    def test_a_major_lot_defaults_to_tightened_severity(self):
        self.assertEqual(acceptance_plan(900, "major")["severity"],
                         SEVERITY_TIGHTENED)

    def test_a_minor_lot_defaults_to_normal_severity(self):
        self.assertEqual(acceptance_plan(900, "minor")["severity"],
                         SEVERITY_NORMAL)

    def test_a_suspended_supplier_has_no_plan(self):
        with self.assertRaises(ValueError):
            acceptance_plan(900, "minor", SEVERITY_SUSPENDED)

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_plan(900, "nice-to-have")

    def test_every_criticality_yields_a_usable_plan(self):
        for criticality in CRITICALITIES:
            plan = acceptance_plan(900, criticality)
            self.assertGreaterEqual(plan["sample_size"], 1)
            self.assertLessEqual(plan["sample_size"], 900)


class JudgeLotTests(unittest.TestCase):
    def test_a_clean_sample_accepts(self):
        self.assertEqual(judge_lot(900, "minor", 0)["disposition"], LOT_ACCEPT)

    def test_defectives_on_the_accept_number_still_accept(self):
        plan = acceptance_plan(900, "minor")
        result = judge_lot(900, "minor", plan["accept_number"])
        self.assertEqual(result["disposition"], LOT_ACCEPT)

    def test_defectives_on_the_reject_number_reject(self):
        plan = acceptance_plan(900, "minor")
        result = judge_lot(900, "minor", plan["reject_number"])
        self.assertEqual(result["disposition"], LOT_REJECT)
        self.assertTrue(any("reject number" in f for f in result["findings"]))

    def test_one_defective_rejects_a_critical_lot(self):
        self.assertEqual(judge_lot(4000, "critical", 1)["disposition"], LOT_REJECT)

    def test_a_stepped_up_plan_says_so_in_its_findings(self):
        result = judge_lot(30, "minor", 0)
        self.assertTrue(any("stepped up" in f for f in result["findings"]))

    def test_more_defectives_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            judge_lot(900, "minor", 500)

    def test_negative_defectives_rejected(self):
        with self.assertRaises(ValueError):
            judge_lot(900, "minor", -1)


class SeveritySwitchingTests(unittest.TestCase):
    def test_two_rejects_in_five_lots_tighten_a_normal_supplier(self):
        history = [LOT_ACCEPT, LOT_REJECT, LOT_ACCEPT, LOT_REJECT, LOT_ACCEPT]
        self.assertEqual(next_severity(SEVERITY_NORMAL, history),
                         SEVERITY_TIGHTENED)

    def test_ten_clean_lots_relax_a_normal_supplier(self):
        self.assertEqual(
            next_severity(SEVERITY_NORMAL, [LOT_ACCEPT] * 10), SEVERITY_REDUCED
        )

    def test_five_clean_lots_return_a_tightened_supplier_to_normal(self):
        self.assertEqual(
            next_severity(SEVERITY_TIGHTENED, [LOT_ACCEPT] * 5), SEVERITY_NORMAL
        )

    def test_a_tightened_supplier_that_never_recovers_is_suspended(self):
        self.assertEqual(
            next_severity(SEVERITY_TIGHTENED, [LOT_REJECT] * 5),
            SEVERITY_SUSPENDED,
        )

    def test_one_reject_returns_a_reduced_supplier_to_normal(self):
        history = [LOT_ACCEPT, LOT_ACCEPT, LOT_REJECT]
        self.assertEqual(next_severity(SEVERITY_REDUCED, history),
                         SEVERITY_NORMAL)

    def test_suspension_does_not_lift_itself(self):
        self.assertEqual(
            next_severity(SEVERITY_SUSPENDED, [LOT_ACCEPT] * 20),
            SEVERITY_SUSPENDED,
        )

    def test_an_unknown_disposition_in_the_history_is_rejected(self):
        with self.assertRaises(ValueError):
            next_severity(SEVERITY_NORMAL, [LOT_ACCEPT, "probably-fine"])

    def test_a_non_sequence_history_is_rejected(self):
        with self.assertRaises(ValueError):
            next_severity(SEVERITY_NORMAL, "all good lately")


if __name__ == "__main__":
    unittest.main()
