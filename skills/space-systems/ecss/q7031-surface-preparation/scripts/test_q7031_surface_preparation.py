"""Contract tests for the ECSS-Q-ST-70-31C surface-preparation sequence logic."""

import unittest

from q7031_surface_preparation_logic import (
    CONVERSION_COATED_SUBSTRATES,
    DEFAULT_PREP_WINDOW_H,
    DISPOSITIONS,
    PREP_STEPS,
    PREP_WINDOW_H,
    REPEATABLE_STEPS,
    assess_preparation,
    masking_findings,
    normalize_key,
    normalize_sequence,
    prep_window_h,
    required_sequence,
    sequence_findings,
    window_finding,
)

ALUMINIUM_STEPS = ["degrease", "abrade", "rinse", "conversion-coat", "rinse", "dry"]
LAMINATE_STEPS = ["degrease", "abrade", "rinse", "dry"]


def record(**overrides):
    base = {
        "substrate": "aluminium-alloy",
        "performed_steps": list(ALUMINIUM_STEPS),
        "elapsed_since_prep_h": 3.0,
    }
    base.update(overrides)
    return base


class NormalisationTests(unittest.TestCase):
    def test_step_is_trimmed_and_case_folded(self):
        self.assertEqual(normalize_sequence([" Degrease "]), ["degrease"])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sequence([])

    def test_non_string_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sequence([3])

    def test_key_helper_rejects_blank(self):
        with self.assertRaises(ValueError):
            normalize_key("  ", "substrate")


class RequiredSequenceTests(unittest.TestCase):
    def test_metallic_substrate_owes_a_conversion_treatment(self):
        got = required_sequence("aluminium-alloy")
        self.assertIn("conversion-coat", got)

    def test_laminate_owes_no_conversion_treatment(self):
        got = required_sequence("cfrp-laminate")
        self.assertNotIn("conversion-coat", got)

    def test_keep_out_area_adds_masking(self):
        self.assertIn("mask", required_sequence("cfrp-laminate", ["connector-face"]))

    def test_no_keep_out_area_adds_no_masking(self):
        self.assertNotIn("mask", required_sequence("cfrp-laminate"))

    def test_degrease_is_always_first(self):
        self.assertEqual(required_sequence("titanium-alloy")[0], "degrease")

    def test_conversion_coated_list_is_populated(self):
        self.assertIn("magnesium-alloy", CONVERSION_COATED_SUBSTRATES)

    def test_keep_out_areas_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            required_sequence("cfrp-laminate", "connector-face")


class WindowTests(unittest.TestCase):
    def test_window_looked_up_per_substrate(self):
        self.assertAlmostEqual(prep_window_h("magnesium-alloy"),
                               PREP_WINDOW_H["magnesium-alloy"])

    def test_unknown_substrate_falls_back_to_the_default(self):
        self.assertAlmostEqual(prep_window_h("beryllium-billet"), DEFAULT_PREP_WINDOW_H)

    def test_inside_the_window_is_clean(self):
        self.assertIsNone(window_finding(3.0, 8.0))

    def test_exactly_at_the_window_is_clean(self):
        self.assertIsNone(window_finding(8.0, 8.0))

    def test_past_the_window_is_a_finding(self):
        self.assertEqual(window_finding(9.0, 8.0), "prepared-to-coat-window-exceeded")

    def test_negative_elapsed_time_rejected(self):
        with self.assertRaises(ValueError):
            window_finding(-1.0, 8.0)


class SequenceFindingTests(unittest.TestCase):
    def test_correct_sequence_is_clean(self):
        required = required_sequence("aluminium-alloy")
        self.assertEqual(sequence_findings(required, ALUMINIUM_STEPS), [])

    def test_missing_step_reported(self):
        required = required_sequence("cfrp-laminate")
        got = sequence_findings(required, ["degrease", "rinse", "dry"])
        self.assertIn("missing-step-abrade", got)

    def test_out_of_order_step_reported(self):
        required = required_sequence("cfrp-laminate")
        got = sequence_findings(required, ["abrade", "degrease", "rinse", "dry"])
        self.assertIn("steps-out-of-order", got)

    def test_repeated_non_repeatable_step_reported(self):
        required = required_sequence("cfrp-laminate")
        got = sequence_findings(required, ["degrease", "abrade", "abrade", "rinse", "dry"])
        self.assertIn("repeated-step-abrade", got)

    def test_repeated_rinse_is_allowed(self):
        required = required_sequence("cfrp-laminate")
        got = sequence_findings(required, ["degrease", "abrade", "rinse", "rinse", "dry"])
        self.assertEqual(got, [])

    def test_unrecognised_step_reported(self):
        required = required_sequence("cfrp-laminate")
        got = sequence_findings(required, ["degrease", "flame-polish", "abrade", "rinse", "dry"])
        self.assertIn("unrecognised-step-flame-polish", got)

    def test_step_vocabulary_and_repeatable_set_agree(self):
        for step in REPEATABLE_STEPS:
            self.assertIn(step, PREP_STEPS)

    def test_empty_required_sequence_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings([], LAMINATE_STEPS)


class MaskingTests(unittest.TestCase):
    def test_fully_masked_item_is_clean(self):
        self.assertEqual(masking_findings(["connector-face"], ["connector-face"]), [])

    def test_unmasked_keep_out_area_reported(self):
        got = masking_findings(["connector-face", "bond-strap-land"], ["connector-face"])
        self.assertIn("keep-out-area-unmasked-bond-strap-land", got)

    def test_undeclared_masked_area_reported(self):
        got = masking_findings(["connector-face"], ["connector-face", "radiator-panel"])
        self.assertIn("masked-area-not-declared-radiator-panel", got)

    def test_no_keep_out_areas_is_clean(self):
        self.assertEqual(masking_findings(None, None), [])

    def test_blank_area_name_rejected(self):
        with self.assertRaises(ValueError):
            masking_findings(["  "], [])


class DispositionTests(unittest.TestCase):
    def test_correctly_prepared_surface_is_ready(self):
        out = assess_preparation(record())
        self.assertEqual(out["disposition"], "ready-to-coat")
        self.assertEqual(out["findings"], [])

    def test_stale_surface_must_be_re_prepared(self):
        out = assess_preparation(record(elapsed_since_prep_h=40.0))
        self.assertEqual(out["disposition"], "re-prepare")
        self.assertIn("prepared-to-coat-window-exceeded", out["findings"])

    def test_missing_step_forces_re_preparation(self):
        out = assess_preparation(record(performed_steps=["degrease", "rinse", "dry"]))
        self.assertEqual(out["disposition"], "re-prepare")

    def test_masking_gap_alone_is_rework(self):
        out = assess_preparation(
            record(
                performed_steps=ALUMINIUM_STEPS + ["mask"],
                keep_out_areas=["connector-face", "bond-strap-land"],
                masked_areas=["connector-face"],
            )
        )
        self.assertEqual(out["disposition"], "rework-required")

    def test_window_may_be_overridden_per_item(self):
        out = assess_preparation(record(elapsed_since_prep_h=10.0, window_h=12.0))
        self.assertEqual(out["disposition"], "ready-to-coat")
        self.assertAlmostEqual(out["window_h"], 12.0)

    def test_required_steps_are_reported_back(self):
        out = assess_preparation(record())
        self.assertEqual(out["required_steps"], list(required_sequence("aluminium-alloy")))

    def test_missing_record_key_rejected(self):
        spec = record()
        del spec["elapsed_since_prep_h"]
        with self.assertRaises(ValueError):
            assess_preparation(spec)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_preparation(["aluminium-alloy"])

    def test_every_disposition_is_a_declared_one(self):
        for spec in (record(), record(elapsed_since_prep_h=40.0),
                     record(performed_steps=["degrease"])):
            self.assertIn(assess_preparation(spec)["disposition"], DISPOSITIONS)


if __name__ == "__main__":
    unittest.main()
