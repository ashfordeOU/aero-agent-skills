"""
Gate 3 contract tests — ECSS-E-ST-10-11C §4.7.3 labels and cues logic.
stdlib unittest, deterministic, offline. Run: python3 test_e1011_labels_cues.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_labels_cues_logic import (
    validate_label,
    validate_colour_coding,
    validate_warning_cue,
    assess_labels_and_cues,
)


class TestValidateLabel(unittest.TestCase):

    def test_valid_label_passes(self):
        result = validate_label("MAIN POWER", "SW-001")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_empty_label_text_fails(self):
        result = validate_label("", "SW-001")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("empty" in f for f in result["findings"]))

    def test_whitespace_only_label_fails(self):
        result = validate_label("   ", "SW-001")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("empty" in f for f in result["findings"]))

    def test_label_exceeds_default_length_fails(self):
        long_text = "A" * 51
        result = validate_label(long_text, "SW-002")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("limit" in f for f in result["findings"]))

    def test_label_at_exact_limit_passes(self):
        text = "B" * 50
        result = validate_label(text, "SW-003")
        self.assertTrue(result["compliant"])

    def test_label_custom_max_length_tighter(self):
        result = validate_label("HELLO", "SW-004", max_length=4)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("limit" in f for f in result["findings"]))

    def test_empty_item_id_fails(self):
        result = validate_label("POWER", "")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("item_id" in f for f in result["findings"]))

    def test_label_non_str_text_raises(self):
        with self.assertRaises(TypeError):
            validate_label(123, "SW-005")

    def test_label_non_str_item_id_raises(self):
        with self.assertRaises(TypeError):
            validate_label("POWER", None)

    def test_invalid_max_length_raises(self):
        with self.assertRaises(ValueError):
            validate_label("POWER", "SW-006", max_length=0)

    def test_result_contains_required_keys(self):
        result = validate_label("VALVE OPEN", "VLV-001")
        for key in ("item_id", "label_text", "compliant", "findings"):
            self.assertIn(key, result)


class TestValidateColourCoding(unittest.TestCase):

    def test_red_danger_passes(self):
        result = validate_colour_coding("red", "danger", "IND-001")
        self.assertTrue(result["compliant"])

    def test_amber_caution_passes(self):
        result = validate_colour_coding("amber", "caution", "IND-002")
        self.assertTrue(result["compliant"])

    def test_yellow_caution_passes(self):
        result = validate_colour_coding("yellow", "caution", "IND-003")
        self.assertTrue(result["compliant"])

    def test_green_nominal_passes(self):
        result = validate_colour_coding("green", "nominal", "IND-004")
        self.assertTrue(result["compliant"])

    def test_red_nominal_mismatch_fails(self):
        result = validate_colour_coding("red", "nominal", "IND-005")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("maps to" in f for f in result["findings"]))

    def test_green_danger_mismatch_fails(self):
        result = validate_colour_coding("green", "danger", "IND-006")
        self.assertFalse(result["compliant"])

    def test_unknown_colour_fails(self):
        result = validate_colour_coding("purple", "caution", "IND-007")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("approved HFE palette" in f for f in result["findings"]))

    def test_case_insensitive_colour_match(self):
        result = validate_colour_coding("RED", "danger", "IND-008")
        self.assertTrue(result["compliant"])

    def test_non_str_colour_raises(self):
        with self.assertRaises(TypeError):
            validate_colour_coding(1, "danger", "IND-009")

    def test_non_str_status_raises(self):
        with self.assertRaises(TypeError):
            validate_colour_coding("red", 42, "IND-010")


class TestValidateWarningCue(unittest.TestCase):

    def _make_cue(self, **kwargs):
        base = {
            "item_id": "CUE-001",
            "criticality": "non-critical",
            "modalities": ["visual"],
            "detectable": True,
        }
        base.update(kwargs)
        return base

    def test_non_critical_single_visual_passes(self):
        result = validate_warning_cue(self._make_cue())
        self.assertTrue(result["compliant"])

    def test_emergency_two_modalities_passes(self):
        cue = self._make_cue(criticality="emergency", modalities=["visual", "auditory"])
        result = validate_warning_cue(cue)
        self.assertTrue(result["compliant"])

    def test_emergency_single_modality_fails(self):
        cue = self._make_cue(criticality="emergency", modalities=["visual"])
        result = validate_warning_cue(cue)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("redundancy" in f or "modalities" in f for f in result["findings"]))

    def test_warning_single_modality_fails(self):
        cue = self._make_cue(criticality="warning", modalities=["auditory"])
        result = validate_warning_cue(cue)
        self.assertFalse(result["compliant"])

    def test_warning_two_modalities_passes(self):
        cue = self._make_cue(criticality="warning", modalities=["visual", "tactile"])
        result = validate_warning_cue(cue)
        self.assertTrue(result["compliant"])

    def test_non_detectable_cue_fails(self):
        cue = self._make_cue(detectable=False)
        result = validate_warning_cue(cue)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("detectable" in f for f in result["findings"]))

    def test_empty_modalities_fails(self):
        cue = self._make_cue(modalities=[])
        result = validate_warning_cue(cue)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("modality" in f for f in result["findings"]))

    def test_unknown_modality_fails(self):
        cue = self._make_cue(modalities=["visual", "ultrasonic"])
        result = validate_warning_cue(cue)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("unknown modalities" in f for f in result["findings"]))

    def test_missing_required_key_raises(self):
        with self.assertRaises(ValueError):
            validate_warning_cue({"item_id": "X", "criticality": "caution"})

    def test_invalid_criticality_raises(self):
        with self.assertRaises(ValueError):
            validate_warning_cue(self._make_cue(criticality="severe"))

    def test_non_bool_detectable_raises(self):
        with self.assertRaises(TypeError):
            validate_warning_cue(self._make_cue(detectable="yes"))

    def test_non_list_modalities_raises(self):
        with self.assertRaises(TypeError):
            validate_warning_cue(self._make_cue(modalities="visual"))

    def test_caution_single_modality_passes(self):
        cue = self._make_cue(criticality="caution", modalities=["visual"])
        result = validate_warning_cue(cue)
        self.assertTrue(result["compliant"])

    def test_haptic_modality_accepted(self):
        cue = self._make_cue(
            criticality="warning",
            modalities=["visual", "haptic"],
        )
        result = validate_warning_cue(cue)
        self.assertTrue(result["compliant"])


class TestAssessLabelsAndCues(unittest.TestCase):

    def test_all_valid_inputs_overall_compliant(self):
        labels = [{"label_text": "PUMP ON", "item_id": "PMP-001"}]
        colours = [{"colour": "green", "status_intent": "nominal", "item_id": "IND-001"}]
        cues = [{
            "item_id": "CUE-001",
            "criticality": "caution",
            "modalities": ["visual"],
            "detectable": True,
        }]
        result = assess_labels_and_cues(labels, colours, cues)
        self.assertTrue(result["overall_compliant"])
        self.assertEqual(result["total_findings"], 0)

    def test_mixed_inputs_not_overall_compliant(self):
        labels = [{"label_text": "", "item_id": "PMP-002"}]
        colours = [{"colour": "red", "status_intent": "nominal", "item_id": "IND-002"}]
        cues = [{
            "item_id": "CUE-002",
            "criticality": "emergency",
            "modalities": ["visual"],
            "detectable": True,
        }]
        result = assess_labels_and_cues(labels, colours, cues)
        self.assertFalse(result["overall_compliant"])
        self.assertGreater(result["total_findings"], 0)

    def test_empty_inventories_pass(self):
        result = assess_labels_and_cues([], [], [])
        self.assertTrue(result["overall_compliant"])
        self.assertEqual(result["total_findings"], 0)

    def test_result_structure_has_all_keys(self):
        result = assess_labels_and_cues([], [], [])
        for key in ("label_results", "colour_results", "cue_results",
                    "overall_compliant", "total_findings"):
            self.assertIn(key, result)

    def test_non_list_labels_raises(self):
        with self.assertRaises(TypeError):
            assess_labels_and_cues("not-a-list", [], [])


if __name__ == "__main__":
    unittest.main()
