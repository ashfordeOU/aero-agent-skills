"""Contract tests for the clause 4.4.2 requirement-consolidation logic."""

import unittest

from q6015_phase_b_radiation_requirements_consolidation_logic import (
    ALLOCATION_LEVELS,
    MIN_DESIGN_FACTOR_BY_LEVEL,
    RDM_ACCEPT_THRESHOLD,
    consolidate_requirements,
    dose_at_thickness,
    grade_requirement,
    grade_requirement_set,
    radiation_design_margin,
    screen_part,
    screen_part_list,
    sector_shielded_dose,
    validate_sector_model,
)

CURVE = [
    (0.5, 200.0),
    (1.0, 100.0),
    (2.0, 50.0),
    (4.0, 25.0),
    (10.0, 10.0),
]

FLAT_SECTORS = [(0.25, 2.0), (0.25, 2.0), (0.25, 2.0), (0.25, 2.0)]


def requirement(**overrides):
    record = {
        "id": "RAD-010",
        "environment_source": "mission-environment-specification",
        "design_factor": 2.0,
        "allocation_level": "part",
        "verification_method": "test",
    }
    record.update(overrides)
    return record


class RequirementGradingTests(unittest.TestCase):
    def test_complete_requirement_is_consolidated(self):
        graded = grade_requirement(requirement())
        self.assertTrue(graded["consolidated"])
        self.assertEqual(graded["findings"], [])

    def test_absent_environment_source_is_reported(self):
        graded = grade_requirement(requirement(environment_source=None))
        self.assertIn("environment_source", graded["missing_attributes"])
        self.assertFalse(graded["consolidated"])

    def test_design_factor_below_the_level_floor_is_reported(self):
        graded = grade_requirement(requirement(allocation_level="part", design_factor=1.5))
        self.assertFalse(graded["consolidated"])
        self.assertTrue(any("floor" in f for f in graded["findings"]))

    def test_design_factor_exactly_on_the_floor_passes(self):
        floor = MIN_DESIGN_FACTOR_BY_LEVEL["equipment"]
        graded = grade_requirement(
            requirement(allocation_level="equipment", design_factor=floor)
        )
        self.assertTrue(graded["consolidated"])

    def test_every_allocation_level_has_a_floor(self):
        for level in ALLOCATION_LEVELS:
            self.assertIn(level, MIN_DESIGN_FACTOR_BY_LEVEL)

    def test_unknown_allocation_level_rejected(self):
        with self.assertRaises(ValueError):
            grade_requirement(requirement(allocation_level="constellation"))

    def test_unknown_verification_method_rejected(self):
        with self.assertRaises(ValueError):
            grade_requirement(requirement(verification_method="hope"))

    def test_record_without_id_rejected(self):
        with self.assertRaises(ValueError):
            grade_requirement(requirement(id="  "))

    def test_set_is_ordered_by_id(self):
        graded = grade_requirement_set(
            [requirement(id="RAD-020"), requirement(id="RAD-005")]
        )
        self.assertEqual([item["id"] for item in graded], ["RAD-005", "RAD-020"])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            grade_requirement_set([requirement(), requirement()])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            grade_requirement_set([])


class SectorShieldingTests(unittest.TestCase):
    def test_fractions_must_sum_to_unity(self):
        with self.assertRaises(ValueError):
            validate_sector_model([(0.5, 2.0), (0.2, 4.0)])

    def test_validated_model_returns_float_pairs(self):
        model = validate_sector_model([(0.5, 2.0), (0.5, 4.0)])
        self.assertEqual(model, [(0.5, 2.0), (0.5, 4.0)])

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_sector_model([(1.0, 0.0)])

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_sector_model([(1.5, 2.0)])

    def test_empty_model_rejected(self):
        with self.assertRaises(ValueError):
            validate_sector_model([])

    def test_curve_hits_a_tabulated_point(self):
        self.assertAlmostEqual(dose_at_thickness(CURVE, 2.0), 50.0, places=9)

    def test_curve_interpolates_between_points(self):
        value = dose_at_thickness([(1.0, 100.0), (4.0, 25.0)], 2.0)
        self.assertAlmostEqual(value, 50.0, places=9)

    def test_thickness_outside_the_span_refused(self):
        with self.assertRaises(ValueError):
            dose_at_thickness(CURVE, 20.0)

    def test_non_monotone_curve_rejected(self):
        with self.assertRaises(ValueError):
            dose_at_thickness([(1.0, 100.0), (1.0, 50.0)], 1.0)

    def test_uniform_sectors_give_the_single_thickness_dose(self):
        self.assertAlmostEqual(
            sector_shielded_dose(FLAT_SECTORS, CURVE),
            dose_at_thickness(CURVE, 2.0),
            places=9,
        )

    def test_a_thin_sector_dominates_the_weighted_dose(self):
        thin = sector_shielded_dose([(0.1, 0.5), (0.9, 10.0)], CURVE)
        thick = sector_shielded_dose([(0.1, 10.0), (0.9, 10.0)], CURVE)
        self.assertGreater(thin, thick)


class PartScreeningTests(unittest.TestCase):
    def test_margin_is_a_ratio(self):
        self.assertAlmostEqual(radiation_design_margin(300.0, 100.0), 3.0, places=9)

    def test_zero_specified_level_rejected(self):
        with self.assertRaises(ValueError):
            radiation_design_margin(300.0, 0.0)

    def test_comfortable_part_is_accepted(self):
        result = screen_part({"reference": "P1", "capability_krad": 300.0}, 100.0)
        self.assertEqual(result["disposition"], "accept")

    def test_part_exactly_on_the_acceptance_factor_is_accepted(self):
        result = screen_part(
            {"reference": "P1", "capability_krad": RDM_ACCEPT_THRESHOLD * 100.0}, 100.0
        )
        self.assertEqual(result["disposition"], "accept")
        self.assertAlmostEqual(result["margin"], RDM_ACCEPT_THRESHOLD, places=9)

    def test_part_between_unity_and_the_factor_needs_shielding(self):
        result = screen_part({"reference": "P1", "capability_krad": 150.0}, 100.0)
        self.assertEqual(result["disposition"], "shield-or-relocate")

    def test_part_exactly_at_the_specified_level_needs_shielding(self):
        result = screen_part({"reference": "P1", "capability_krad": 100.0}, 100.0)
        self.assertEqual(result["disposition"], "shield-or-relocate")
        self.assertAlmostEqual(result["margin"], 1.0, places=9)

    def test_part_below_the_specified_level_is_rejected(self):
        result = screen_part({"reference": "P1", "capability_krad": 40.0}, 100.0)
        self.assertEqual(result["disposition"], "reject")

    def test_part_without_capability_owes_a_test(self):
        result = screen_part({"reference": "P1"}, 100.0)
        self.assertEqual(result["disposition"], "test-required")
        self.assertIsNone(result["margin"])

    def test_similarity_capability_owes_a_test_even_with_margin(self):
        result = screen_part(
            {"reference": "P1", "capability_krad": 900.0, "capability_basis": "similarity"},
            100.0,
        )
        self.assertEqual(result["disposition"], "test-required")

    def test_part_without_reference_rejected(self):
        with self.assertRaises(ValueError):
            screen_part({"capability_krad": 300.0}, 100.0)

    def test_screened_list_is_ordered_by_reference(self):
        screened = screen_part_list(
            [
                {"reference": "P9", "capability_krad": 300.0},
                {"reference": "P2", "capability_krad": 300.0},
            ],
            100.0,
        )
        self.assertEqual([item["reference"] for item in screened], ["P2", "P9"])

    def test_empty_part_list_rejected(self):
        with self.assertRaises(ValueError):
            screen_part_list([], 100.0)


class ConsolidationTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "requirements": [requirement()],
            "sectors": FLAT_SECTORS,
            "dose_depth_curve": CURVE,
            "design_factor": 2.0,
            "parts": [{"reference": "P1", "capability_krad": 1000.0}],
            "open_shielding_actions": [],
        }
        spec.update(overrides)
        return spec

    def test_settled_baseline_reports_no_findings(self):
        result = consolidate_requirements(self._spec())
        self.assertTrue(result["baseline_settled"])
        self.assertEqual(result["findings"], [])

    def test_specified_level_is_the_location_dose_times_the_factor(self):
        result = consolidate_requirements(self._spec())
        self.assertAlmostEqual(
            result["specified_level_krad"], result["location_dose_krad"] * 2.0, places=9
        )

    def test_rejected_part_blocks_the_baseline(self):
        result = consolidate_requirements(
            self._spec(parts=[{"reference": "P1", "capability_krad": 10.0}])
        )
        self.assertFalse(result["baseline_settled"])
        self.assertTrue(any("cannot be carried" in f for f in result["findings"]))

    def test_open_shielding_action_blocks_the_baseline(self):
        result = consolidate_requirements(
            self._spec(open_shielding_actions=["spot shield on the receiver box"])
        )
        self.assertFalse(result["baseline_settled"])

    def test_incomplete_requirement_blocks_the_baseline(self):
        result = consolidate_requirements(
            self._spec(requirements=[requirement(verification_method=None)])
        )
        self.assertFalse(result["baseline_settled"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["sectors"]
        with self.assertRaises(ValueError):
            consolidate_requirements(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            consolidate_requirements([requirement()])

    def test_non_sequence_open_actions_rejected(self):
        with self.assertRaises(ValueError):
            consolidate_requirements(self._spec(open_shielding_actions="spot shield"))


if __name__ == "__main__":
    unittest.main()
