#!/usr/bin/env python3
"""Contract test for the coupon visual examination process (offline)."""

import copy
import unittest

from e2008_full_visual_inspection_process_logic import (
    EXAMINATION_ADEQUATE,
    EXAMINATION_INADEQUATE,
    ILLUMINATION_ABOVE,
    ILLUMINATION_BELOW,
    ILLUMINATION_WITHIN,
    INSPECTION_STAGES,
    PROCESS_ADEQUATE,
    PROCESS_INADEQUATE,
    REFERENCE_UNAIDED_RESOLUTION_MM,
    VIEWING_ASPECTS,
    aspect_gap,
    evaluate_inspection_requirement,
    governing_requirement,
    illumination_verdict,
    required_magnification,
    resolvable_feature_size_mm,
    run_visual_inspection_process,
)

PROCESS = {
    "magnification": 10.0,
    "illumination_lux": 1200.0,
    "detection_elements": 3.0,
    "viewed_aspects": ["front-face", "coverglass-edge", "interconnect-loop"],
    "stages_performed": ["post-bond", "final"],
}

CHIP_REQUIREMENT = {
    "id": "VI-01",
    "smallest_feature_mm": 0.05,
    "stage": "post-bond",
    "aspects": ["coverglass-edge"],
    "illumination_band_lux": (800.0, 2000.0),
}

INTERCONNECT_REQUIREMENT = {
    "id": "VI-02",
    "smallest_feature_mm": 0.20,
    "stage": "final",
    "aspects": ["front-face", "interconnect-loop"],
    "illumination_band_lux": (800.0, 2000.0),
}


def _with(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


class ResolutionModelTests(unittest.TestCase):
    def test_unaided_view_resolves_the_reference_detail(self):
        self.assertAlmostEqual(
            resolvable_feature_size_mm(1.0), REFERENCE_UNAIDED_RESOLUTION_MM, places=12
        )

    def test_ten_times_magnification_resolves_ten_times_finer(self):
        self.assertAlmostEqual(resolvable_feature_size_mm(10.0), 0.01, places=12)

    def test_magnification_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_size_mm(0.5)

    def test_zero_magnification_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_size_mm(0.0)

    def test_non_numeric_magnification_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_feature_size_mm("10x")

    def test_required_magnification_scales_with_the_element_count(self):
        three = required_magnification(0.05, 3.0)
        six = required_magnification(0.05, 6.0)
        self.assertAlmostEqual(three, 6.0, places=12)
        self.assertAlmostEqual(six, 12.0, places=12)

    def test_a_large_feature_needs_no_magnification(self):
        self.assertLess(required_magnification(2.0, 3.0), 1.0)

    def test_zero_feature_size_rejected(self):
        with self.assertRaises(ValueError):
            required_magnification(0.0)

    def test_negative_element_count_rejected(self):
        with self.assertRaises(ValueError):
            required_magnification(0.05, -3.0)


class IlluminationTests(unittest.TestCase):
    def test_illuminance_inside_the_band_is_within(self):
        self.assertEqual(illumination_verdict(1200.0, 800.0, 2000.0), ILLUMINATION_WITHIN)

    def test_illuminance_under_the_band_is_below(self):
        self.assertEqual(illumination_verdict(400.0, 800.0, 2000.0), ILLUMINATION_BELOW)

    def test_illuminance_over_the_band_is_above(self):
        self.assertEqual(illumination_verdict(3000.0, 800.0, 2000.0), ILLUMINATION_ABOVE)

    def test_illuminance_exactly_on_the_lower_bound_is_within(self):
        value = 800.0
        self.assertAlmostEqual(value, 800.0, places=9)
        self.assertEqual(illumination_verdict(value, 800.0, 2000.0), ILLUMINATION_WITHIN)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            illumination_verdict(1200.0, 2000.0, 800.0)

    def test_negative_illuminance_rejected(self):
        with self.assertRaises(ValueError):
            illumination_verdict(-1200.0, 800.0, 2000.0)


class AspectTests(unittest.TestCase):
    def test_every_named_aspect_is_in_the_vocabulary(self):
        self.assertIn("rear-face", VIEWING_ASPECTS)
        self.assertIn("coverglass-edge", VIEWING_ASPECTS)

    def test_no_gap_when_every_required_aspect_was_viewed(self):
        self.assertEqual(aspect_gap(["front-face"], ["front-face", "rear-face"]), [])

    def test_gap_names_the_aspect_never_viewed(self):
        self.assertEqual(
            aspect_gap(["front-face", "rear-face"], ["front-face"]), ["rear-face"]
        )

    def test_unknown_required_aspect_rejected(self):
        with self.assertRaises(ValueError):
            aspect_gap(["side-face"], ["front-face"])

    def test_empty_required_aspects_rejected(self):
        with self.assertRaises(ValueError):
            aspect_gap([], ["front-face"])


class RequirementEvaluationTests(unittest.TestCase):
    def test_adequate_examination_of_the_chip_requirement(self):
        result = evaluate_inspection_requirement(CHIP_REQUIREMENT, PROCESS)
        self.assertEqual(result["verdict"], EXAMINATION_ADEQUATE)
        self.assertAlmostEqual(result["required_magnification"], 6.0, places=12)
        self.assertAlmostEqual(result["resolvable_feature_size_mm"], 0.01, places=12)
        self.assertEqual(result["findings"], [])

    def test_magnification_exactly_on_the_demand_is_adequate(self):
        # 0.10 mm x 3 elements / 0.03 mm evaluates to ten within a few ULP.
        requirement = _with(CHIP_REQUIREMENT, smallest_feature_mm=0.03)
        result = evaluate_inspection_requirement(requirement, PROCESS)
        self.assertAlmostEqual(result["required_magnification"], 10.0, places=9)
        self.assertAlmostEqual(result["magnification_ratio"], 1.0, places=9)
        self.assertTrue(result["magnification_adequate"])
        self.assertEqual(result["verdict"], EXAMINATION_ADEQUATE)

    def test_a_finer_feature_than_the_optics_can_resolve_is_inadequate(self):
        requirement = _with(CHIP_REQUIREMENT, smallest_feature_mm=0.005)
        result = evaluate_inspection_requirement(requirement, PROCESS)
        self.assertFalse(result["magnification_adequate"])
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)
        self.assertTrue(any("resolve" in f for f in result["findings"]))

    def test_an_aspect_never_viewed_fails_the_requirement(self):
        requirement = _with(CHIP_REQUIREMENT, aspects=["rear-face"])
        result = evaluate_inspection_requirement(requirement, PROCESS)
        self.assertEqual(result["missing_aspects"], ["rear-face"])
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)

    def test_a_stage_the_process_skipped_fails_the_requirement(self):
        requirement = _with(CHIP_REQUIREMENT, stage="pre-bond")
        result = evaluate_inspection_requirement(requirement, PROCESS)
        self.assertFalse(result["stage_covered"])
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)
        self.assertTrue(any("never performed" in f for f in result["findings"]))

    def test_illumination_outside_the_band_fails_the_requirement(self):
        requirement = _with(CHIP_REQUIREMENT, illumination_band_lux=(1500.0, 2500.0))
        result = evaluate_inspection_requirement(requirement, PROCESS)
        self.assertEqual(result["illumination"], ILLUMINATION_BELOW)
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)

    def test_requirement_without_an_identifier_rejected(self):
        requirement = _with(CHIP_REQUIREMENT, id="")
        with self.assertRaises(ValueError):
            evaluate_inspection_requirement(requirement, PROCESS)

    def test_requirement_with_an_unknown_stage_rejected(self):
        requirement = _with(CHIP_REQUIREMENT, stage="post-flight")
        with self.assertRaises(ValueError):
            evaluate_inspection_requirement(requirement, PROCESS)

    def test_requirement_without_an_illumination_band_rejected(self):
        requirement = copy.deepcopy(CHIP_REQUIREMENT)
        del requirement["illumination_band_lux"]
        with self.assertRaises(ValueError):
            evaluate_inspection_requirement(requirement, PROCESS)

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_inspection_requirement("VI-01", PROCESS)

    def test_process_without_a_performed_stage_rejected(self):
        process = _with(PROCESS, stages_performed=[])
        with self.assertRaises(ValueError):
            evaluate_inspection_requirement(CHIP_REQUIREMENT, process)

    def test_process_with_an_unknown_viewed_aspect_rejected(self):
        process = _with(PROCESS, viewed_aspects=["underside"])
        with self.assertRaises(ValueError):
            evaluate_inspection_requirement(CHIP_REQUIREMENT, process)


class ProcessRunTests(unittest.TestCase):
    def test_a_compliant_run_covers_every_requirement(self):
        report = run_visual_inspection_process(
            [CHIP_REQUIREMENT, INTERCONNECT_REQUIREMENT], PROCESS
        )
        self.assertEqual(report["verdict"], PROCESS_ADEQUATE)
        self.assertEqual(report["requirement_count"], 2)
        self.assertEqual(report["adequate_count"], 2)
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=12)

    def test_the_finest_feature_governs_the_magnification(self):
        report = run_visual_inspection_process(
            [CHIP_REQUIREMENT, INTERCONNECT_REQUIREMENT], PROCESS
        )
        self.assertEqual(report["governing_requirement"], "VI-01")

    def test_one_failing_requirement_fails_the_run(self):
        report = run_visual_inspection_process(
            [_with(CHIP_REQUIREMENT, smallest_feature_mm=0.004), INTERCONNECT_REQUIREMENT],
            PROCESS,
        )
        self.assertEqual(report["verdict"], PROCESS_INADEQUATE)
        self.assertEqual(report["adequate_count"], 1)
        self.assertAlmostEqual(report["coverage_fraction"], 0.5, places=12)

    def test_an_aspect_no_requirement_asks_for_is_reported(self):
        process = _with(
            PROCESS,
            viewed_aspects=[
                "front-face",
                "coverglass-edge",
                "interconnect-loop",
                "rear-face",
            ],
        )
        report = run_visual_inspection_process([CHIP_REQUIREMENT], process)
        self.assertIn("rear-face", report["unused_aspects"])
        self.assertTrue(any("no requirement asks" in f for f in report["findings"]))

    def test_duplicate_requirement_identifiers_rejected(self):
        with self.assertRaises(ValueError):
            run_visual_inspection_process(
                [CHIP_REQUIREMENT, copy.deepcopy(CHIP_REQUIREMENT)], PROCESS
            )

    def test_empty_requirement_list_rejected(self):
        with self.assertRaises(ValueError):
            run_visual_inspection_process([], PROCESS)

    def test_governing_requirement_needs_results(self):
        with self.assertRaises(ValueError):
            governing_requirement([])

    def test_every_stage_name_is_in_the_vocabulary(self):
        self.assertIn("pre-bond", INSPECTION_STAGES)
        self.assertIn("post-cure", INSPECTION_STAGES)


if __name__ == "__main__":
    unittest.main()
