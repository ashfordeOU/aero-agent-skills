"""Contract test for the radiation property-measurement leaf (stdlib unittest)."""

import unittest

from q7006_property_measurement_before_during_after_logic import (
    BASELINE_FRACTION,
    FINAL_FRACTION,
    MAX_DOSE_GAP,
    PROPERTY_FAMILIES,
    RESOLUTION_FACTOR,
    assess_measurement_plan,
    change_resolvable,
    intermediate_points,
    known_property,
    largest_dose_gap,
    normalize_schedule,
    point_at,
    properties_missing_at,
    property_direction,
    replicate_shortfalls,
    validate_point,
)

OPTICAL = ["solar-absorptance", "infrared-emittance"]


def point(label, fraction, properties=None, replicates=3):
    return {
        "label": label,
        "dose_fraction": fraction,
        "properties": list(OPTICAL if properties is None else properties),
        "replicates": replicates,
    }


def plan(**kw):
    record = {
        "plan_id": "UV-2026-012",
        "property_families": list(OPTICAL),
        "points": [
            point("pristine", 0.0),
            point("quarter", 0.25),
            point("half", 0.5),
            point("full", 1.0),
        ],
        "expected_change": {
            "solar-absorptance": 0.060,
            "infrared-emittance": 0.020,
        },
        "expanded_uncertainty": {
            "solar-absorptance": 0.010,
            "infrared-emittance": 0.008,
        },
    }
    record.update(kw)
    return record


class TestPropertyFamilies(unittest.TestCase):
    def test_a_thermo_optical_family_is_known(self):
        self.assertTrue(known_property("solar-absorptance"))

    def test_an_unlisted_property_is_not_known(self):
        self.assertFalse(known_property("dielectric-constant"))

    def test_darkening_is_an_increase_in_solar_absorptance(self):
        self.assertEqual(
            property_direction("solar-absorptance"), "increase-is-degradation"
        )

    def test_loss_of_transmittance_is_a_decrease(self):
        self.assertEqual(
            property_direction("optical-transmittance"), "decrease-is-degradation"
        )

    def test_a_mechanical_family_needs_more_replicates_than_an_optical_one(self):
        self.assertGreater(
            PROPERTY_FAMILIES["tensile-strength"]["min_replicates"],
            PROPERTY_FAMILIES["solar-absorptance"]["min_replicates"],
        )

    def test_an_unknown_direction_request_raises(self):
        with self.assertRaises(ValueError):
            property_direction("dielectric-constant")


class TestPointValidation(unittest.TestCase):
    def test_a_well_formed_point_normalizes(self):
        normalized = validate_point(point("pristine", 0.0))
        self.assertEqual(normalized["label"], "pristine")
        self.assertAlmostEqual(normalized["dose_fraction"], 0.0, places=9)

    def test_a_dose_fraction_above_the_planned_total_raises(self):
        with self.assertRaises(ValueError):
            validate_point(point("overrun", 1.4))

    def test_a_point_measuring_nothing_raises(self):
        with self.assertRaises(ValueError):
            validate_point(point("empty", 0.5, properties=[]))

    def test_a_repeated_property_at_one_point_raises(self):
        with self.assertRaises(ValueError):
            validate_point(
                point("dup", 0.5, properties=["solar-absorptance", "solar-absorptance"])
            )

    def test_a_fractional_replicate_count_raises(self):
        with self.assertRaises(ValueError):
            validate_point(point("half-specimen", 0.5, replicates=2.5))

    def test_a_non_mapping_point_raises(self):
        with self.assertRaises(ValueError):
            validate_point("pristine")


class TestSchedule(unittest.TestCase):
    def test_a_schedule_is_ordered_by_accumulated_exposure(self):
        points = normalize_schedule(
            [point("full", 1.0), point("pristine", 0.0), point("half", 0.5)]
        )
        self.assertEqual([p["label"] for p in points], ["pristine", "half", "full"])

    def test_two_points_at_the_same_exposure_raise(self):
        with self.assertRaises(ValueError):
            normalize_schedule([point("a", 0.5), point("b", 0.5)])

    def test_an_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            normalize_schedule([])

    def test_the_baseline_point_is_found_at_zero_exposure(self):
        points = normalize_schedule(plan()["points"])
        self.assertIsNotNone(point_at(points, BASELINE_FRACTION))
        self.assertIsNotNone(point_at(points, FINAL_FRACTION))

    def test_intermediate_points_exclude_the_two_ends(self):
        points = normalize_schedule(plan()["points"])
        labels = [p["label"] for p in intermediate_points(points)]
        self.assertEqual(labels, ["quarter", "half"])

    def test_the_largest_gap_is_the_widest_unmeasured_stretch(self):
        points = normalize_schedule(plan()["points"])
        self.assertAlmostEqual(largest_dose_gap(points), 0.5, places=9)

    def test_a_single_point_has_no_gap_to_report(self):
        with self.assertRaises(ValueError):
            largest_dose_gap(normalize_schedule([point("only", 1.0)]))


class TestCoverage(unittest.TestCase):
    def test_a_covered_family_is_missing_nowhere(self):
        points = normalize_schedule(plan()["points"])
        self.assertEqual(properties_missing_at(points, 0.0, OPTICAL), [])

    def test_a_family_absent_from_the_baseline_is_reported(self):
        points = normalize_schedule(
            [
                point("pristine", 0.0, properties=["solar-absorptance"]),
                point("full", 1.0),
            ]
        )
        self.assertEqual(
            properties_missing_at(points, 0.0, OPTICAL), ["infrared-emittance"]
        )

    def test_a_fraction_with_no_point_misses_every_family(self):
        points = normalize_schedule(plan()["points"])
        self.assertEqual(
            sorted(properties_missing_at(points, 0.75, OPTICAL)), sorted(OPTICAL)
        )

    def test_a_mechanical_point_with_three_replicates_falls_short(self):
        points = normalize_schedule(
            [point("full", 1.0, properties=["tensile-strength"], replicates=3)]
        )
        shortfalls = replicate_shortfalls(points)
        self.assertEqual(len(shortfalls), 1)
        self.assertEqual(shortfalls[0][2], 5)

    def test_an_optical_point_with_three_replicates_is_enough(self):
        points = normalize_schedule([point("full", 1.0)])
        self.assertEqual(replicate_shortfalls(points), [])


class TestResolvability(unittest.TestCase):
    def test_a_change_well_clear_of_its_uncertainty_is_resolvable(self):
        self.assertTrue(change_resolvable(0.06, 0.01))

    def test_a_change_exactly_on_the_resolution_factor_is_resolvable(self):
        self.assertTrue(change_resolvable(RESOLUTION_FACTOR * 0.01, 0.01))

    def test_a_change_inside_its_uncertainty_is_not_resolvable(self):
        self.assertFalse(change_resolvable(0.005, 0.01))

    def test_a_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            change_resolvable(0.06, -0.01)


class TestAssessment(unittest.TestCase):
    def test_a_sound_plan_is_executable(self):
        assessment = assess_measurement_plan(plan())
        self.assertEqual(assessment["findings"], [])
        self.assertTrue(assessment["executable"])
        self.assertEqual(assessment["intermediate_point_count"], 2)

    def test_a_plan_without_a_baseline_is_not_executable(self):
        assessment = assess_measurement_plan(
            plan(points=[point("half", 0.5), point("full", 1.0)])
        )
        self.assertIn("no-pristine-baseline-measurement", assessment["findings"])
        self.assertFalse(assessment["executable"])

    def test_a_before_and_after_only_plan_has_no_intermediate_point(self):
        assessment = assess_measurement_plan(
            plan(points=[point("pristine", 0.0), point("full", 1.0)])
        )
        self.assertIn("no-intermediate-measurement-point", assessment["findings"])
        self.assertIn("exposure-axis-undersampled", assessment["findings"])
        self.assertAlmostEqual(assessment["largest_dose_gap"], 1.0, places=9)

    def test_a_gap_exactly_on_the_limit_is_accepted(self):
        assessment = assess_measurement_plan(
            plan(
                points=[
                    point("pristine", 0.0),
                    point("half", MAX_DOSE_GAP),
                    point("full", 1.0),
                ]
            )
        )
        self.assertNotIn("exposure-axis-undersampled", assessment["findings"])

    def test_a_family_read_out_only_at_the_end_lacks_a_pre_exposure_value(self):
        assessment = assess_measurement_plan(
            plan(
                points=[
                    point("pristine", 0.0, properties=["solar-absorptance"]),
                    point("half", 0.5),
                    point("full", 1.0),
                ]
            )
        )
        self.assertIn("property-without-a-pre-exposure-value", assessment["findings"])
        self.assertEqual(assessment["missing_at_baseline"], ["infrared-emittance"])

    def test_an_unresolvable_expected_change_is_a_finding(self):
        assessment = assess_measurement_plan(
            plan(expanded_uncertainty={
                "solar-absorptance": 0.05,
                "infrared-emittance": 0.008,
            })
        )
        self.assertIn(
            "expected-change-inside-the-measurement-uncertainty",
            assessment["findings"],
        )
        self.assertEqual(assessment["unresolvable_properties"], ["solar-absorptance"])

    def test_a_plan_with_no_uncertainty_budget_cannot_show_resolvability(self):
        assessment = assess_measurement_plan(plan(expanded_uncertainty={}))
        self.assertIn("resolvability-not-demonstrated", assessment["findings"])

    def test_an_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_plan(plan(property_families=["dielectric-constant"]))

    def test_a_non_mapping_plan_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_plan(["UV-2026-012"])


if __name__ == "__main__":
    unittest.main()
