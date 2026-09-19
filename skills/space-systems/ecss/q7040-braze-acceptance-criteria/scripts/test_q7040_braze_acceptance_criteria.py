#!/usr/bin/env python3
"""Contract test for brazement acceptance criteria (offline)."""

import copy
import unittest

from q7040_braze_acceptance_criteria_logic import (
    ACCEPT,
    BRAZE_CLASSES,
    CEILING,
    CRITERION_SENSE,
    FLOOR,
    REJECT,
    acceptance_limits,
    assess_brazement,
    fill_fraction_from_areas,
    grade_criterion,
    grade_lot,
    non_gradeable_findings,
    normalise_measurement,
)

SOUND_JOINT = {
    "id": "J-001",
    "braze_class": "class-a",
    "joint_area_mm2": 400.0,
    "voided_area_mm2": 16.0,
    "total_void_area_fraction": 0.04,
    "largest_single_void_fraction": 0.02,
    "longest_linear_void_fraction": 0.05,
    "indication_count": 2,
    "defect_types": ["scattered-porosity"],
}

ON_LIMIT_JOINT = {
    "id": "J-002",
    "braze_class": "class-a",
    "joint_area_mm2": 100.0,
    "voided_area_mm2": 10.0,
    "total_void_area_fraction": 0.10,
    "largest_single_void_fraction": 0.05,
    "longest_linear_void_fraction": 0.10,
    "indication_count": 3,
}


def _joint(base, **overrides):
    joint = copy.deepcopy(base)
    joint.update(overrides)
    return joint


class LimitTableTests(unittest.TestCase):
    def test_every_class_carries_every_criterion(self):
        for braze_class in BRAZE_CLASSES:
            limits = acceptance_limits(braze_class)
            self.assertEqual(sorted(limits), sorted(CRITERION_SENSE))

    def test_fill_is_a_floor_and_voids_are_ceilings(self):
        limits = acceptance_limits("class-a")
        self.assertEqual(limits["fill_fraction"]["sense"], FLOOR)
        self.assertEqual(limits["total_void_area_fraction"]["sense"], CEILING)

    def test_a_looser_class_demands_less_fill(self):
        self.assertLess(
            acceptance_limits("class-c")["fill_fraction"]["limit"],
            acceptance_limits("class-a")["fill_fraction"]["limit"],
        )

    def test_a_looser_class_tolerates_a_bigger_void(self):
        self.assertGreater(
            acceptance_limits("class-c")["largest_single_void_fraction"]["limit"],
            acceptance_limits("class-a")["largest_single_void_fraction"]["limit"],
        )

    def test_an_unknown_class_is_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_limits("class-d")


class FillComputationTests(unittest.TestCase):
    def test_fill_is_the_unvoided_share_of_the_joint(self):
        self.assertAlmostEqual(fill_fraction_from_areas(100.0, 10.0), 0.9, places=12)

    def test_an_unvoided_joint_is_fully_filled(self):
        self.assertAlmostEqual(fill_fraction_from_areas(250.0, 0.0), 1.0, places=12)

    def test_a_voided_area_over_the_joint_area_is_rejected(self):
        with self.assertRaises(ValueError):
            fill_fraction_from_areas(100.0, 120.0)

    def test_a_negative_voided_area_is_rejected(self):
        with self.assertRaises(ValueError):
            fill_fraction_from_areas(100.0, -5.0)

    def test_a_zero_joint_area_is_rejected(self):
        with self.assertRaises(ValueError):
            fill_fraction_from_areas(0.0, 0.0)


class CriterionGradingTests(unittest.TestCase):
    def test_a_floor_criterion_passes_when_it_is_reached(self):
        result = grade_criterion("fill_fraction", 0.95, 0.90)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 0.05, places=12)

    def test_a_floor_criterion_fails_when_it_is_not_reached(self):
        self.assertFalse(grade_criterion("fill_fraction", 0.85, 0.90)["compliant"])

    def test_a_ceiling_criterion_passes_under_its_limit(self):
        self.assertTrue(
            grade_criterion("largest_single_void_fraction", 0.02, 0.05)["compliant"]
        )

    def test_a_ceiling_criterion_fails_over_its_limit(self):
        self.assertFalse(
            grade_criterion("largest_single_void_fraction", 0.08, 0.05)["compliant"]
        )

    def test_a_value_exactly_on_a_floor_is_compliant(self):
        result = grade_criterion("fill_fraction", 0.90, 0.90)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["relative_margin"], 0.0, places=12)

    def test_a_value_exactly_on_a_ceiling_is_compliant(self):
        self.assertTrue(
            grade_criterion("longest_linear_void_fraction", 0.10, 0.10)["compliant"]
        )

    def test_an_unknown_criterion_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_criterion("fillet_radius", 1.0, 2.0)


class NonGradeableDefectTests(unittest.TestCase):
    def test_a_crack_is_rejected_in_every_class(self):
        for braze_class in BRAZE_CLASSES:
            self.assertTrue(non_gradeable_findings(["crack"], braze_class))

    def test_a_loaded_edge_disbond_is_rejected_in_the_structural_classes(self):
        self.assertTrue(non_gradeable_findings(["loaded-edge-disbond"], "class-a"))
        self.assertTrue(non_gradeable_findings(["loaded-edge-disbond"], "class-b"))

    def test_a_loaded_edge_disbond_is_gradeable_in_the_lowest_class(self):
        self.assertEqual(non_gradeable_findings(["loaded-edge-disbond"], "class-c"), [])

    def test_ordinary_porosity_raises_no_non_gradeable_finding(self):
        self.assertEqual(non_gradeable_findings(["scattered-porosity"], "class-a"), [])

    def test_an_unknown_defect_type_is_rejected(self):
        with self.assertRaises(ValueError):
            non_gradeable_findings(["cold-shut"], "class-a")

    def test_a_non_sequence_defect_list_is_rejected(self):
        with self.assertRaises(ValueError):
            non_gradeable_findings("crack", "class-a")


class NormalisationTests(unittest.TestCase):
    def test_areas_are_preferred_over_a_declared_fill(self):
        record = normalise_measurement(_joint(SOUND_JOINT, fill_fraction=0.10))
        self.assertEqual(record["fill_source"], "computed-from-areas")
        self.assertAlmostEqual(record["fill_fraction"], 0.96, places=12)

    def test_a_declared_fill_is_used_when_no_areas_are_given(self):
        record = normalise_measurement(
            {"braze_class": "class-b", "fill_fraction": 0.85}
        )
        self.assertEqual(record["fill_source"], "declared")

    def test_a_measurement_with_neither_fill_nor_areas_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measurement({"braze_class": "class-b"})

    def test_a_single_void_larger_than_the_total_void_area_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measurement(
                _joint(SOUND_JOINT, largest_single_void_fraction=0.30)
            )

    def test_void_area_with_no_indications_counted_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measurement(_joint(SOUND_JOINT, indication_count=0))

    def test_a_fraction_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measurement(_joint(SOUND_JOINT, total_void_area_fraction=1.4))

    def test_a_non_integer_indication_count_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measurement(_joint(SOUND_JOINT, indication_count=2.5))

    def test_a_non_mapping_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_measurement("class-a")


class AssessmentTests(unittest.TestCase):
    def test_a_sound_joint_is_accepted(self):
        result = assess_brazement(SOUND_JOINT)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_a_joint_exactly_on_every_limit_is_accepted(self):
        result = assess_brazement(ON_LIMIT_JOINT)
        self.assertTrue(result["accepted"])
        for criterion in result["criteria"].values():
            self.assertTrue(criterion["compliant"])

    def test_a_poorly_filled_joint_is_rejected_on_fill(self):
        result = assess_brazement(
            _joint(SOUND_JOINT, joint_area_mm2=400.0, voided_area_mm2=60.0)
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["binding_criterion"], "fill_fraction")

    def test_an_oversized_single_void_is_rejected_despite_good_fill(self):
        result = assess_brazement(
            _joint(
                SOUND_JOINT,
                total_void_area_fraction=0.09,
                largest_single_void_fraction=0.09,
            )
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["binding_criterion"], "largest_single_void_fraction")

    def test_a_long_void_run_is_rejected_on_its_own(self):
        result = assess_brazement(
            _joint(SOUND_JOINT, longest_linear_void_fraction=0.40)
        )
        self.assertEqual(result["binding_criterion"], "longest_linear_void_fraction")

    def test_too_many_indications_reject_the_joint(self):
        result = assess_brazement(_joint(SOUND_JOINT, indication_count=9))
        self.assertEqual(result["binding_criterion"], "indication_count")

    def test_a_crack_rejects_a_joint_that_grades_cleanly(self):
        result = assess_brazement(
            _joint(SOUND_JOINT, defect_types=["scattered-porosity", "crack"])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["binding_criterion"], "non-gradeable-defect")
        for criterion in result["criteria"].values():
            self.assertTrue(criterion["compliant"])

    def test_a_looser_class_accepts_what_the_tight_class_rejects(self):
        loose = assess_brazement(
            _joint(SOUND_JOINT, braze_class="class-c", voided_area_mm2=60.0)
        )
        tight = assess_brazement(_joint(SOUND_JOINT, voided_area_mm2=60.0))
        self.assertTrue(loose["accepted"])
        self.assertFalse(tight["accepted"])

    def test_the_binding_criterion_is_the_thinnest_margin_on_an_accept(self):
        result = assess_brazement(SOUND_JOINT)
        thinnest = min(
            result["criteria"].values(), key=lambda c: c["relative_margin"]
        )["criterion"]
        self.assertEqual(result["binding_criterion"], thinnest)

    def test_a_reject_carries_a_finding_for_every_failed_criterion(self):
        result = assess_brazement(
            _joint(SOUND_JOINT, voided_area_mm2=200.0, indication_count=20)
        )
        self.assertGreaterEqual(len(result["findings"]), 2)


class LotTests(unittest.TestCase):
    def test_the_lot_roll_up_counts_both_outcomes(self):
        summary = grade_lot(
            [SOUND_JOINT, _joint(SOUND_JOINT, id="J-003", voided_area_mm2=200.0)]
        )
        self.assertEqual(summary["accepted"], 1)
        self.assertEqual(summary["rejected"], 1)
        self.assertAlmostEqual(summary["acceptance_fraction"], 0.5, places=12)

    def test_the_roll_up_counts_the_binding_criteria(self):
        summary = grade_lot(
            [_joint(SOUND_JOINT, id="J-004", voided_area_mm2=200.0)]
        )
        self.assertEqual(summary["binding_criterion_counts"]["fill_fraction"], 1)

    def test_an_empty_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_lot([])


if __name__ == "__main__":
    unittest.main()
