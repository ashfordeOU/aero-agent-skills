"""Contract test for the black-anodizing pre-treatment leaf (stdlib unittest)."""

import unittest

from q7003_pre_treatment_requirements_logic import (
    MAX_TRANSFER_MINUTES,
    MIN_ETCH_REMOVAL_UM,
    MIN_RINSE_RESISTIVITY_MOHM_CM,
    MIN_RINSE_STAGES,
    assess_pre_treatment,
    assess_pre_treatment_lines,
    check_etch,
    check_maskant,
    check_order,
    check_rinse_quality,
    check_rinses,
    check_transfer,
    etch_metal_loss_um,
    etch_minutes_for_removal,
    validate_line,
    validate_steps,
)

GOOD_STEPS = [
    "solvent-degrease",
    "alkaline-clean",
    "rinse",
    "alkaline-etch",
    "rinse",
    "deoxidize",
    "rinse",
    "mask",
]


def line(lid="L-1", **kw):
    record = {
        "id": lid,
        "steps": list(GOOD_STEPS),
        "etch_rate_um_per_min": 0.5,
        "etch_minutes": 4.0,
        "allowance_um": 25.0,
        "rinse_stages": 3,
        "rinse_resistivity_mohm_cm": 0.2,
        "transfer_minutes": 5.0,
        "maskant": "ptfe-tape",
    }
    record.update(kw)
    return record


class TestValidateSteps(unittest.TestCase):
    def test_known_steps_pass_through(self):
        self.assertEqual(validate_steps(["rinse", "dry"]), ("rinse", "dry"))

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            validate_steps(["rinse", "chromate-conversion"])

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_steps([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_steps("rinse")


class TestOrder(unittest.TestCase):
    def test_correct_order_is_clean(self):
        self.assertEqual(check_order(GOOD_STEPS), [])

    def test_etch_before_clean_is_found(self):
        steps = ["alkaline-etch", "rinse", "alkaline-clean", "rinse", "deoxidize",
                 "rinse"]
        findings = check_order(steps)
        self.assertTrue(
            any(f.startswith("chemical-step-out-of-order") for f in findings)
        )

    def test_deoxidize_not_last_is_found(self):
        steps = ["alkaline-clean", "rinse", "deoxidize", "rinse", "alkaline-etch",
                 "rinse"]
        self.assertIn("deoxidize-is-not-the-last-chemical-step", check_order(steps))

    def test_missing_deoxidize_is_found(self):
        steps = ["alkaline-clean", "rinse", "alkaline-etch", "rinse"]
        findings = check_order(steps)
        self.assertIn("no-deoxidizing-step-before-anodizing", findings)
        self.assertIn("etch-without-a-deoxidizing-step", findings)

    def test_masking_before_a_chemical_attack_is_found(self):
        steps = ["alkaline-clean", "rinse", "mask", "alkaline-etch", "rinse",
                 "deoxidize", "rinse"]
        self.assertIn("maskant-applied-before-a-chemical-attack",
                      check_order(steps))


class TestRinses(unittest.TestCase):
    def test_fully_rinsed_line_is_clean(self):
        self.assertEqual(check_rinses(GOOD_STEPS), [])

    def test_missing_rinse_between_two_baths_is_found(self):
        steps = ["alkaline-clean", "alkaline-etch", "rinse", "deoxidize", "rinse"]
        self.assertIn("no-rinse-between-alkaline-clean-and-alkaline-etch",
                      check_rinses(steps))

    def test_solvent_degrease_needs_no_rinse_behind_it(self):
        steps = ["solvent-degrease", "alkaline-clean", "rinse", "deoxidize",
                 "rinse"]
        self.assertEqual(check_rinses(steps), [])

    def test_missing_final_rinse_is_found(self):
        steps = ["alkaline-clean", "rinse", "deoxidize"]
        self.assertIn("no-final-rinse-after-deoxidize", check_rinses(steps))


class TestRinseQuality(unittest.TestCase):
    def test_cascade_alone_is_enough(self):
        self.assertEqual(check_rinse_quality(MIN_RINSE_STAGES, 0.0), [])

    def test_resistivity_alone_is_enough(self):
        self.assertEqual(
            check_rinse_quality(1, MIN_RINSE_RESISTIVITY_MOHM_CM), []
        )

    def test_single_poor_stage_is_found(self):
        self.assertIn(
            "rinse-neither-cascaded-nor-of-adequate-resistivity",
            check_rinse_quality(1, MIN_RINSE_RESISTIVITY_MOHM_CM / 2.0),
        )

    def test_no_stage_is_found(self):
        self.assertIn("no-rinse-stage-declared", check_rinse_quality(0, 0.0))

    def test_non_integer_stage_count_raises(self):
        with self.assertRaises(ValueError):
            check_rinse_quality(2.5, 0.2)


class TestTransfer(unittest.TestCase):
    def test_transfer_inside_the_bound_is_clean(self):
        self.assertEqual(check_transfer(MAX_TRANSFER_MINUTES), [])

    def test_transfer_beyond_the_bound_is_found(self):
        self.assertIn(
            "deoxidized-surface-held-too-long-before-anodizing",
            check_transfer(MAX_TRANSFER_MINUTES + 1.0),
        )

    def test_negative_transfer_raises(self):
        with self.assertRaises(ValueError):
            check_transfer(-1.0)


class TestEtchArithmetic(unittest.TestCase):
    def test_metal_loss_is_rate_times_time(self):
        self.assertAlmostEqual(etch_metal_loss_um(0.5, 4.0), 2.0, places=9)

    def test_time_for_a_target_removal_inverts_the_rate(self):
        self.assertAlmostEqual(etch_minutes_for_removal(0.5, 2.0), 4.0, places=9)

    def test_zero_rate_raises_when_inverted(self):
        with self.assertRaises(ValueError):
            etch_minutes_for_removal(0.0, 2.0)

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            etch_metal_loss_um(0.5, -1.0)

    def test_removal_exactly_on_the_minimum_is_accepted(self):
        findings, loss = check_etch(MIN_ETCH_REMOVAL_UM, 1.0, 25.0)
        self.assertEqual(findings, [])
        self.assertAlmostEqual(loss, MIN_ETCH_REMOVAL_UM, places=9)

    def test_light_etch_is_found(self):
        findings, _ = check_etch(0.1, 1.0, 25.0)
        self.assertIn("etch-too-light-to-remove-the-worked-surface-layer", findings)

    def test_deep_etch_beyond_the_allowance_is_found(self):
        findings, _ = check_etch(2.0, 20.0, 25.0)
        self.assertIn("etch-removal-exceeds-the-dimensional-allowance", findings)

    def test_removal_exactly_on_the_allowance_is_accepted(self):
        findings, loss = check_etch(2.0, 10.0, 20.0)
        self.assertEqual(findings, [])
        self.assertAlmostEqual(loss, 20.0, places=9)


class TestMaskant(unittest.TestCase):
    def test_resistant_maskant_is_clean(self):
        self.assertEqual(check_maskant("ptfe-tape", GOOD_STEPS), [])

    def test_maskant_meeting_an_etch_it_cannot_take_is_found(self):
        steps = ["alkaline-clean", "rinse", "mask", "alkaline-etch", "rinse",
                 "deoxidize", "rinse"]
        self.assertIn("maskant-not-resistant-to-alkaline-etch",
                      check_maskant("silicone-plug", steps))

    def test_maskant_without_a_masking_step_is_found(self):
        steps = ["alkaline-clean", "rinse", "deoxidize", "rinse"]
        self.assertIn("maskant-declared-but-no-masking-step-in-the-line",
                      check_maskant("ptfe-tape", steps))

    def test_unknown_maskant_raises(self):
        with self.assertRaises(ValueError):
            check_maskant("wax-crayon", GOOD_STEPS)

    def test_no_maskant_is_clean(self):
        self.assertEqual(check_maskant(None, GOOD_STEPS), [])


class TestValidateLine(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_line({"id": "L-9", "steps": ["rinse"]})
        self.assertEqual(norm["rinse_stages"], 0)
        self.assertIsNone(norm["maskant"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_line(["L-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_line(line(""))

    def test_boolean_stage_count_raises(self):
        with self.assertRaises(ValueError):
            validate_line(line(rinse_stages=True))


class TestAssessLine(unittest.TestCase):
    def test_well_formed_line_is_compliant(self):
        result = assess_pre_treatment(line())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["etch_removal_um"], 2.0, places=9)

    def test_broken_line_collects_several_findings(self):
        result = assess_pre_treatment(
            line(steps=["alkaline-etch", "alkaline-clean"],
                 rinse_stages=0,
                 rinse_resistivity_mohm_cm=0.0,
                 transfer_minutes=40.0,
                 maskant=None)
        )
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_batch_reports_the_failing_lines(self):
        report = assess_pre_treatment_lines([
            line("L-1"),
            line("L-2", transfer_minutes=60.0),
        ])
        self.assertEqual(report["non_compliant_ids"], ["L-2"])
        self.assertFalse(report["compliant"])

    def test_duplicate_line_id_raises(self):
        with self.assertRaises(ValueError):
            assess_pre_treatment_lines([line("L-1"), line("L-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_pre_treatment_lines([])


if __name__ == "__main__":
    unittest.main()
