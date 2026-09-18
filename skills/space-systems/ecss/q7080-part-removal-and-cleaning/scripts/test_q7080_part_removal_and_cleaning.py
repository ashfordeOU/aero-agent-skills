#!/usr/bin/env python3
"""Contract test for part removal, depowdering and cleaning (offline)."""

import copy
import unittest

from q7080_part_removal_and_cleaning_logic import (
    METHOD_KERF_MM,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    assess_removal_and_cleaning,
    cleanliness,
    passage_depowdering,
    removal_allowance,
    trapped_powder,
)

OPEN_CHANNEL = {
    "id": "coolant-1",
    "bore_mm": 2.0,
    "length_mm": 30.0,
    "particle_d90_um": 45.0,
    "open_port_count": 2,
}

GOOD_CASE = {
    "as_removed_mass_g": 100.4,
    "nominal_solid_mass_g": 100.0,
    "powder_allowance_fraction": 0.01,
    "channels": [OPEN_CHANNEL],
    "removal_method": "wire-edm",
    "declared_allowance_mm": 1.5,
    "distortion_mm": 0.5,
    "datum_uncertainty_mm": 0.1,
    "stress_relief_done": True,
    "residue_mg": 10.0,
    "cleaned_area_cm2": 100.0,
    "residue_limit_mg_per_cm2": 0.5,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


def _channel(**overrides):
    channel = copy.deepcopy(OPEN_CHANNEL)
    channel.update(overrides)
    return channel


class TrappedPowderTests(unittest.TestCase):
    def test_excess_mass_is_reported_as_trapped_powder(self):
        result = trapped_powder(102.0, 100.0, allowance_fraction=0.05)
        self.assertAlmostEqual(result["residual_powder_g"], 2.0, places=9)
        self.assertAlmostEqual(result["residual_fraction"], 0.02, places=9)

    def test_excess_over_the_allowance_rejects(self):
        result = trapped_powder(102.0, 100.0, allowance_fraction=0.01)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_excess_exactly_on_the_allowance_accepts(self):
        result = trapped_powder(102.0, 100.0, allowance_fraction=0.02)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_shortfall_inside_weighing_scatter_reads_as_clean(self):
        result = trapped_powder(99.6, 100.0, allowance_fraction=0.01)
        self.assertAlmostEqual(result["residual_powder_g"], 0.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_shortfall_beyond_scatter_is_an_inconsistent_record(self):
        with self.assertRaises(ValueError):
            trapped_powder(97.0, 100.0, allowance_fraction=0.01)

    def test_zero_nominal_mass_rejected(self):
        with self.assertRaises(ValueError):
            trapped_powder(100.0, 0.0)

    def test_allowance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            trapped_powder(102.0, 100.0, allowance_fraction=1.5)

    def test_non_numeric_mass_rejected(self):
        with self.assertRaises(ValueError):
            trapped_powder("100", 100.0)


class PassageTests(unittest.TestCase):
    def test_wide_short_two_port_passage_accepts(self):
        result = passage_depowdering(_channel())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_bore_ratio_is_bores_per_powder_diameter(self):
        result = passage_depowdering(_channel())
        self.assertAlmostEqual(result["bore_ratio"], 2000.0 / 45.0, places=9)

    def test_aspect_ratio_is_length_over_bore(self):
        result = passage_depowdering(_channel())
        self.assertAlmostEqual(result["aspect_ratio"], 15.0, places=9)

    def test_bore_exactly_on_the_ratio_limit_accepts(self):
        result = passage_depowdering(
            _channel(bore_mm=0.45, length_mm=4.0, particle_d90_um=45.0)
        )
        self.assertAlmostEqual(result["bore_ratio"], 10.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_narrow_bore_rejects_because_powder_bridges(self):
        result = passage_depowdering(_channel(bore_mm=0.30, length_mm=4.0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("bridges" in text for text in result["findings"]))

    def test_blind_passage_rejects(self):
        result = passage_depowdering(_channel(open_port_count=0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_long_single_port_passage_is_a_review(self):
        result = passage_depowdering(_channel(open_port_count=1))
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_short_single_port_passage_accepts(self):
        result = passage_depowdering(
            _channel(open_port_count=1, length_mm=16.0)
        )
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_aspect_exactly_on_the_self_draining_limit_accepts(self):
        result = passage_depowdering(_channel(length_mm=40.0))
        self.assertAlmostEqual(result["aspect_ratio"], 20.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_long_two_port_passage_needs_a_flushing_route(self):
        result = passage_depowdering(_channel(length_mm=60.0))
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_long_blind_passage_rejects(self):
        result = passage_depowdering(_channel(length_mm=60.0, open_port_count=0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_non_integer_port_count_rejected(self):
        with self.assertRaises(ValueError):
            passage_depowdering(_channel(open_port_count=1.5))

    def test_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            passage_depowdering(["coolant-1"])


class RemovalAllowanceTests(unittest.TestCase):
    def test_required_allowance_sums_kerf_distortion_and_datum(self):
        result = removal_allowance("wire-edm", 1.5, 0.5, 0.1)
        self.assertAlmostEqual(
            result["required_allowance_mm"],
            METHOD_KERF_MM["wire-edm"] + 0.5 + 0.1,
            places=9,
        )
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_allowance_on_the_limit_accepts_despite_float_representation(self):
        result = removal_allowance("wire-edm", 0.95, 0.5, 0.1)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_saw_kerf_exceeds_a_wire_allowance(self):
        result = removal_allowance("band-saw", 0.95, 0.5, 0.1)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_cutting_before_stress_relief_rejects(self):
        result = removal_allowance("wire-edm", 1.5, 0.5, 0.1, stress_relief_done=False)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("stress relief" in text for text in result["findings"]))

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            removal_allowance("laser-cut", 1.5, 0.5, 0.1)

    def test_non_boolean_relief_flag_rejected(self):
        with self.assertRaises(ValueError):
            removal_allowance("wire-edm", 1.5, 0.5, 0.1, stress_relief_done="yes")


class CleanlinessTests(unittest.TestCase):
    def test_residue_is_graded_per_unit_area(self):
        result = cleanliness(10.0, 100.0, 0.5)
        self.assertAlmostEqual(result["residue_mg_per_cm2"], 0.1, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_same_mass_on_a_small_part_rejects(self):
        result = cleanliness(10.0, 15.0, 0.5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_residue_near_the_limit_is_a_review(self):
        result = cleanliness(45.0, 100.0, 0.5)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            cleanliness(10.0, 0.0, 0.5)

    def test_negative_residue_rejected(self):
        with self.assertRaises(ValueError):
            cleanliness(-1.0, 100.0, 0.5)


class AssessRemovalAndCleaningTests(unittest.TestCase):
    def test_compliant_part_accepts_with_no_findings(self):
        result = assess_removal_and_cleaning(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["driving_characteristics"], [])

    def test_trapped_powder_drives_the_verdict(self):
        result = assess_removal_and_cleaning(_case(as_removed_mass_g=104.0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("mass-balance", result["driving_characteristics"])

    def test_blind_passage_drives_the_verdict_and_is_named(self):
        blind = _channel(id="coolant-2", open_port_count=0)
        result = assess_removal_and_cleaning(_case(channels=[OPEN_CHANNEL, blind]))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("passages", result["driving_characteristics"])
        self.assertEqual(result["driving_passages"], ["coolant-2"])

    def test_cleaning_residue_drives_the_verdict(self):
        result = assess_removal_and_cleaning(_case(residue_mg=90.0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("cleanliness", result["driving_characteristics"])

    def test_part_with_no_internal_passages_is_still_graded(self):
        result = assess_removal_and_cleaning(_case(channels=[]))
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_non_sequence_channel_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_removal_and_cleaning(_case(channels={"id": "coolant-1"}))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_removal_and_cleaning("coolant-1")


if __name__ == "__main__":
    unittest.main()
