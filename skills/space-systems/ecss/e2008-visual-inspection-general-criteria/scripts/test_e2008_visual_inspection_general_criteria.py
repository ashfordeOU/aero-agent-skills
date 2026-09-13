#!/usr/bin/env python3
"""Contract test for the supplier visual acceptance criteria (offline)."""

import copy
import unittest

from e2008_visual_inspection_general_criteria_logic import (
    ACCEPT,
    ACCEPT_PENDING_AGREEMENT,
    AGREEMENT_STATES,
    ASSEMBLY_ACCEPTED,
    ASSEMBLY_COMPONENTS,
    ASSEMBLY_REFERRED,
    ASSEMBLY_REJECTED,
    CRITERION_KINDS,
    REFER_TO_CUSTOMER,
    REJECT,
    SET_ADMISSIBLE,
    SET_NOT_ADMISSIBLE,
    adjudicate_criterion,
    criterion_label,
    observed_value,
    screen_assembly,
    validate_criteria_set,
    validate_criterion,
    validate_observation,
)

ASSEMBLY_AREA_MM2 = 1000.0
REQUIRED = ("coverglass", "interconnect")

CHIP_SINGLE = {
    "component": "coverglass",
    "kind": "single-feature-limit",
    "feature": "edge-chip",
    "measure": "major_dimension_mm",
    "method": "10x-stereo-microscope",
    "agreement": "customer-agreed",
    "unit": "mm",
    "limit": 0.5,
    "document_ref": "supplier-visual-criteria rev B",
}

CHIP_AREA = {
    "component": "coverglass",
    "kind": "cumulative-area-fraction",
    "feature": "edge-chip",
    "method": "10x-stereo-microscope",
    "agreement": "customer-agreed",
    "unit": "fraction",
    "limit": 0.02,
    "document_ref": "supplier-visual-criteria rev B",
}

CHIP_COUNT = {
    "component": "coverglass",
    "kind": "count-limit",
    "feature": "edge-chip",
    "method": "10x-stereo-microscope",
    "agreement": "customer-agreed",
    "unit": "count",
    "limit": 4,
    "document_ref": "supplier-visual-criteria rev B",
}

LIFTED_FOOT = {
    "component": "interconnect",
    "kind": "single-feature-limit",
    "feature": "lifted-foot",
    "measure": "length_mm",
    "method": "20x-stereo-microscope",
    "agreement": "customer-agreed",
    "unit": "mm",
    "limit": 0.3,
    "document_ref": "supplier-visual-criteria rev B",
}

CRITERIA = [CHIP_SINGLE, CHIP_AREA, CHIP_COUNT, LIFTED_FOOT]

CLEAN_OBSERVATIONS = [
    {"component": "coverglass", "feature": "edge-chip", "length_mm": 0.4, "width_mm": 0.3},
    {"component": "coverglass", "feature": "edge-chip", "length_mm": 0.2, "width_mm": 0.2},
]


def _with(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


class CriterionValidationTests(unittest.TestCase):
    def test_a_complete_criterion_normalizes(self):
        item = validate_criterion(CHIP_SINGLE)
        self.assertEqual(item["component"], "coverglass")
        self.assertEqual(item["measure"], "major_dimension_mm")
        self.assertAlmostEqual(item["limit"], 0.5, places=12)

    def test_criterion_label_names_component_feature_and_kind(self):
        self.assertEqual(
            criterion_label(validate_criterion(CHIP_SINGLE)),
            "coverglass/edge-chip/single-feature-limit",
        )

    def test_unknown_component_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_SINGLE, component="radiator"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_SINGLE, kind="looks-fine"))

    def test_unit_inconsistent_with_the_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_AREA, unit="mm"))

    def test_area_fraction_limit_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_AREA, limit=1.4))

    def test_fractional_count_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_COUNT, limit=2.5))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_SINGLE, limit=0.0))

    def test_agreed_criterion_without_a_document_reference_rejected(self):
        broken = copy.deepcopy(CHIP_SINGLE)
        del broken["document_ref"]
        with self.assertRaises(ValueError):
            validate_criterion(broken)

    def test_unknown_agreement_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_SINGLE, agreement="verbally-ok"))

    def test_missing_inspection_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion(_with(CHIP_SINGLE, method="  "))

    def test_non_mapping_criterion_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion("coverglass edge chip 0.5 mm")


class CriteriaSetTests(unittest.TestCase):
    def test_a_complete_agreed_set_is_admissible(self):
        review = validate_criteria_set(CRITERIA, REQUIRED)
        self.assertTrue(review["admissible"])
        self.assertEqual(review["verdict"], SET_ADMISSIBLE)
        self.assertAlmostEqual(review["coverage_fraction"], 1.0, places=12)
        self.assertEqual(review["findings"], [])

    def test_a_component_with_no_criteria_is_a_gap(self):
        review = validate_criteria_set(CRITERIA)
        self.assertEqual(review["verdict"], SET_NOT_ADMISSIBLE)
        self.assertIn("solar-cell", review["missing_components"])
        self.assertAlmostEqual(
            review["coverage_fraction"], 2.0 / len(ASSEMBLY_COMPONENTS), places=12
        )

    def test_an_unagreed_criterion_makes_the_set_inadmissible(self):
        criteria = [_with(CHIP_SINGLE, agreement="supplier-only"), CHIP_AREA,
                    CHIP_COUNT, LIFTED_FOOT]
        review = validate_criteria_set(criteria, REQUIRED)
        self.assertFalse(review["admissible"])
        self.assertIn(
            "coverglass/edge-chip/single-feature-limit", review["unagreed_criteria"]
        )

    def test_an_undocumented_criterion_is_reported(self):
        criteria = [
            _with(CHIP_SINGLE, agreement="submitted-for-agreement", document_ref=None),
            CHIP_AREA,
            CHIP_COUNT,
            LIFTED_FOOT,
        ]
        review = validate_criteria_set(criteria, REQUIRED)
        self.assertIn(
            "coverglass/edge-chip/single-feature-limit", review["undocumented_criteria"]
        )

    def test_duplicate_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_set(CRITERIA + [copy.deepcopy(CHIP_SINGLE)], REQUIRED)

    def test_empty_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_set([], REQUIRED)

    def test_unknown_required_component_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_set(CRITERIA, ("gyroscope",))


class ObservationTests(unittest.TestCase):
    def test_an_observation_carries_its_major_dimension_and_area(self):
        obs = validate_observation(CLEAN_OBSERVATIONS[0])
        self.assertAlmostEqual(obs["major_dimension_mm"], 0.4, places=12)
        self.assertAlmostEqual(obs["area_mm2"], 0.12, places=12)

    def test_zero_width_observation_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_with(CLEAN_OBSERVATIONS[0], width_mm=0.0))

    def test_observation_with_an_unknown_component_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_with(CLEAN_OBSERVATIONS[0], component="strut"))

    def test_non_numeric_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_with(CLEAN_OBSERVATIONS[0], length_mm="0.4 mm"))


class ObservedValueTests(unittest.TestCase):
    def setUp(self):
        self.observations = [validate_observation(o) for o in CLEAN_OBSERVATIONS]

    def test_single_feature_value_is_the_largest_major_dimension(self):
        value = observed_value(validate_criterion(CHIP_SINGLE), self.observations)
        self.assertAlmostEqual(value, 0.4, places=12)

    def test_count_value_is_the_number_of_matching_features(self):
        value = observed_value(validate_criterion(CHIP_COUNT), self.observations)
        self.assertAlmostEqual(value, 2.0, places=12)

    def test_area_fraction_sums_the_feature_areas(self):
        value = observed_value(
            validate_criterion(CHIP_AREA), self.observations, ASSEMBLY_AREA_MM2
        )
        self.assertAlmostEqual(value, 0.16 / ASSEMBLY_AREA_MM2, places=12)

    def test_a_feature_never_seen_reads_zero(self):
        value = observed_value(validate_criterion(LIFTED_FOOT), self.observations)
        self.assertAlmostEqual(value, 0.0, places=12)

    def test_area_fraction_without_an_assembly_area_rejected(self):
        with self.assertRaises(ValueError):
            observed_value(validate_criterion(CHIP_AREA), self.observations)


class AdjudicationTests(unittest.TestCase):
    def test_a_feature_inside_an_agreed_limit_is_accepted(self):
        result = adjudicate_criterion(validate_criterion(CHIP_SINGLE), 0.25)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["utilisation"], 0.5, places=12)
        self.assertEqual(result["findings"], [])

    def test_a_feature_exactly_on_an_agreed_limit_is_accepted(self):
        result = adjudicate_criterion(validate_criterion(CHIP_SINGLE), 0.5)
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)
        self.assertTrue(result["within_limit"])
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_feature_outside_an_agreed_limit_is_rejected(self):
        result = adjudicate_criterion(validate_criterion(CHIP_SINGLE), 0.9)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("limit" in f for f in result["findings"]))

    def test_a_feature_inside_an_unagreed_limit_is_accepted_pending_agreement(self):
        criterion = validate_criterion(_with(CHIP_SINGLE, agreement="supplier-only"))
        result = adjudicate_criterion(criterion, 0.25)
        self.assertEqual(result["disposition"], ACCEPT_PENDING_AGREEMENT)

    def test_a_feature_outside_an_unagreed_limit_is_referred(self):
        criterion = validate_criterion(_with(CHIP_SINGLE, agreement="supplier-only"))
        result = adjudicate_criterion(criterion, 0.9)
        self.assertEqual(result["disposition"], REFER_TO_CUSTOMER)

    def test_negative_observed_value_rejected(self):
        with self.assertRaises(ValueError):
            adjudicate_criterion(validate_criterion(CHIP_SINGLE), -0.1)


class ScreeningTests(unittest.TestCase):
    def test_a_clean_coupon_against_an_agreed_set_is_accepted(self):
        report = screen_assembly(
            CRITERIA, CLEAN_OBSERVATIONS, ASSEMBLY_AREA_MM2, REQUIRED
        )
        self.assertEqual(report["verdict"], ASSEMBLY_ACCEPTED)
        self.assertEqual(report["worst_disposition"], ACCEPT)
        self.assertEqual(report["findings"], [])

    def test_the_largest_utilisation_names_the_governing_criterion(self):
        report = screen_assembly(
            CRITERIA, CLEAN_OBSERVATIONS, ASSEMBLY_AREA_MM2, REQUIRED
        )
        self.assertEqual(
            report["governing_criterion"], "coverglass/edge-chip/single-feature-limit"
        )

    def test_an_oversize_chip_rejects_the_assembly(self):
        observations = CLEAN_OBSERVATIONS + [
            {
                "component": "coverglass",
                "feature": "edge-chip",
                "length_mm": 0.9,
                "width_mm": 0.4,
            }
        ]
        report = screen_assembly(
            CRITERIA, observations, ASSEMBLY_AREA_MM2, REQUIRED
        )
        self.assertEqual(report["verdict"], ASSEMBLY_REJECTED)

    def test_too_many_chips_rejects_the_assembly(self):
        observations = CLEAN_OBSERVATIONS + [
            dict(CLEAN_OBSERVATIONS[1]) for _ in range(4)
        ]
        report = screen_assembly(
            CRITERIA, observations, ASSEMBLY_AREA_MM2, REQUIRED
        )
        self.assertEqual(report["verdict"], ASSEMBLY_REJECTED)
        self.assertEqual(
            report["governing_criterion"], "coverglass/edge-chip/count-limit"
        )

    def test_cumulative_area_exactly_on_its_limit_is_accepted(self):
        criteria = [
            {
                "component": "adhesive-fillet",
                "kind": "cumulative-area-fraction",
                "feature": "void",
                "method": "10x-stereo-microscope",
                "agreement": "customer-agreed",
                "unit": "fraction",
                "limit": 0.02,
                "document_ref": "supplier-visual-criteria rev B",
            }
        ]
        observations = [
            {
                "component": "adhesive-fillet",
                "feature": "void",
                "length_mm": 5.0,
                "width_mm": 4.0,
            }
        ]
        report = screen_assembly(
            criteria, observations, ASSEMBLY_AREA_MM2, ("adhesive-fillet",)
        )
        self.assertAlmostEqual(report["results"][0]["utilisation"], 1.0, places=9)
        self.assertTrue(report["results"][0]["within_limit"])
        self.assertEqual(report["verdict"], ASSEMBLY_ACCEPTED)

    def test_a_feature_no_criterion_covers_is_referred(self):
        observations = CLEAN_OBSERVATIONS + [
            {
                "component": "coverglass",
                "feature": "coating-blemish",
                "length_mm": 0.3,
                "width_mm": 0.2,
            }
        ]
        report = screen_assembly(
            CRITERIA, observations, ASSEMBLY_AREA_MM2, REQUIRED
        )
        self.assertEqual(report["verdict"], ASSEMBLY_REFERRED)
        self.assertIn("coverglass/coating-blemish", report["uncovered_features"])

    def test_an_unagreed_set_never_returns_a_plain_acceptance(self):
        criteria = [_with(CHIP_SINGLE, agreement="supplier-only"), CHIP_AREA,
                    CHIP_COUNT, LIFTED_FOOT]
        report = screen_assembly(
            criteria, CLEAN_OBSERVATIONS, ASSEMBLY_AREA_MM2, REQUIRED
        )
        self.assertEqual(report["verdict"], ASSEMBLY_REFERRED)
        self.assertEqual(report["worst_disposition"], ACCEPT_PENDING_AGREEMENT)

    def test_observations_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            screen_assembly(CRITERIA, "one chip", ASSEMBLY_AREA_MM2, REQUIRED)

    def test_every_agreement_state_and_kind_is_in_the_vocabulary(self):
        self.assertIn("customer-agreed", AGREEMENT_STATES)
        self.assertIn("cumulative-area-fraction", CRITERION_KINDS)


if __name__ == "__main__":
    unittest.main()
