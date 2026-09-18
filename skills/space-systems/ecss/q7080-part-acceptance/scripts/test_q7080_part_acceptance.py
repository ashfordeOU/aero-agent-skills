#!/usr/bin/env python3
"""Contract test for part acceptance by part class (offline)."""

import copy
import unittest

from q7080_part_acceptance_logic import (
    ACCEPTED,
    DEFAULT_ACCEPTANCE_POLICY,
    PART_CLASSES,
    REJECTED,
    assess_part_acceptance,
    consumer_risk,
    evaluate_attributes,
    limiting_quality_count,
    probability_of_acceptance,
    protective_sample_size,
    sampling_plan,
    screening_gap,
    validate_acceptance_policy,
)

GOOD_MEASUREMENTS = {
    "density_fraction": 0.9995,
    "porosity_fraction": 0.0005,
    "surface_roughness_um": 3.2,
}

GOOD_CASE = {
    "part_class": "class-b",
    "lot_size": 100,
    "observed_non_conforming": 0,
    "measurements": GOOD_MEASUREMENTS,
    "screening_performed": ("volumetric-ndt", "dimensional-check"),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_acceptance_policy(DEFAULT_ACCEPTANCE_POLICY),
            DEFAULT_ACCEPTANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy("default")

    def test_policy_covers_every_part_class(self):
        for part_class in PART_CLASSES:
            self.assertIn(part_class, DEFAULT_ACCEPTANCE_POLICY["class_plan"])
            self.assertIn(part_class, DEFAULT_ACCEPTANCE_POLICY["attribute_limits"])

    def test_policy_missing_a_class_plan_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        del broken["class_plan"]["class-c"]
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_full_examination_class_with_a_tolerated_finding_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["class_plan"]["class-a"]["acceptance_number"] = 1
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_zero_limiting_quality_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["class_plan"]["class-b"]["limiting_quality_fraction"] = 0.0
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)


class ProbabilityTests(unittest.TestCase):
    def test_examining_the_whole_lot_finds_every_bad_part(self):
        self.assertAlmostEqual(probability_of_acceptance(20, 1, 20, 0), 0.0, places=12)

    def test_a_clean_lot_is_always_accepted(self):
        self.assertAlmostEqual(probability_of_acceptance(20, 0, 5, 0), 1.0, places=12)

    def test_probability_falls_as_the_sample_grows(self):
        small = probability_of_acceptance(100, 5, 10, 0)
        large = probability_of_acceptance(100, 5, 40, 0)
        self.assertLess(large, small)

    def test_known_hypergeometric_value(self):
        self.assertAlmostEqual(
            probability_of_acceptance(20, 1, 18, 0), 19.0 / 190.0, places=12
        )

    def test_more_bad_parts_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(10, 11, 5, 0)

    def test_drawing_more_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(10, 1, 11, 0)

    def test_non_integer_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            probability_of_acceptance(10.5, 1, 5, 0)


class LimitingQualityTests(unittest.TestCase):
    def test_count_rounds_up_to_a_whole_part(self):
        self.assertEqual(limiting_quality_count(20, 0.05), 1)
        self.assertEqual(limiting_quality_count(100, 0.05), 5)

    def test_count_never_exceeds_the_lot(self):
        self.assertEqual(limiting_quality_count(4, 0.9), 4)

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            limiting_quality_count(100, 0.0)

    def test_consumer_risk_is_the_acceptance_probability_at_that_level(self):
        risk = consumer_risk(100, 37, 0, 0.05)
        direct = probability_of_acceptance(100, 5, 37, 0)
        self.assertAlmostEqual(risk, direct, places=12)


class PlanSearchTests(unittest.TestCase):
    def test_search_finds_the_smallest_protective_sample(self):
        needed = protective_sample_size(100, 0, 0.05, 0.10)
        self.assertEqual(needed, 37)
        self.assertTrue(consumer_risk(100, needed, 0, 0.05) <= 0.10)
        self.assertGreater(consumer_risk(100, needed - 1, 0, 0.05), 0.10)

    def test_unreachable_protection_returns_nothing(self):
        self.assertIsNone(protective_sample_size(10, 1, 0.05, 0.10))

    def test_risk_exactly_on_the_limit_counts_as_protective(self):
        risk = consumer_risk(20, 18, 0, 0.05)
        self.assertAlmostEqual(risk, 0.10, places=9)
        self.assertEqual(protective_sample_size(20, 0, 0.05, 0.10), 18)

    def test_negative_acceptance_number_rejected(self):
        with self.assertRaises(ValueError):
            protective_sample_size(100, -1, 0.05, 0.10)


class SamplingPlanTests(unittest.TestCase):
    def test_class_a_examines_the_whole_lot(self):
        plan = sampling_plan(50, "class-a")
        self.assertTrue(plan["full_examination"])
        self.assertEqual(plan["drawn"], 50)
        self.assertAlmostEqual(plan["consumer_risk"], 0.0, places=12)

    def test_class_b_plan_is_protective_and_smaller_than_the_lot(self):
        plan = sampling_plan(100, "class-b")
        self.assertTrue(plan["protective"])
        self.assertLess(plan["drawn"], 100)
        self.assertEqual(plan["acceptance_number"], 0)

    def test_sample_grows_far_more_slowly_than_the_lot(self):
        small = sampling_plan(100, "class-b")["drawn"]
        large = sampling_plan(500, "class-b")["drawn"]
        self.assertGreater(large, small)
        self.assertLess(large, 100)

    def test_class_minimum_floors_a_tiny_lot(self):
        plan = sampling_plan(3, "class-c")
        self.assertEqual(plan["drawn"], 3)

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            sampling_plan(100, "class-z")

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            sampling_plan(0, "class-b")

    def test_lot_above_the_search_bound_rejected(self):
        with self.assertRaises(ValueError):
            sampling_plan(DEFAULT_ACCEPTANCE_POLICY["max_lot_size"] + 1, "class-b")

    def test_unprotectable_acceptance_number_is_reported(self):
        policy = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        policy["class_plan"]["class-c"]["acceptance_number"] = 3
        plan = sampling_plan(20, "class-c", policy)
        self.assertFalse(plan["protective"])
        self.assertTrue(any("acceptance number" in f for f in plan["findings"]))

    def test_every_class_yields_a_plan(self):
        for part_class in PART_CLASSES:
            plan = sampling_plan(200, part_class)
            self.assertEqual(plan["part_class"], part_class)
            self.assertGreaterEqual(plan["drawn"], 1)


class AttributeTests(unittest.TestCase):
    def test_good_measurements_conform(self):
        result = evaluate_attributes(GOOD_MEASUREMENTS, "class-b")
        self.assertTrue(result["conforming"])
        self.assertEqual(result["missing"], [])

    def test_class_a_limits_are_tighter_than_class_c(self):
        marginal = {
            "density_fraction": 0.995,
            "porosity_fraction": 0.005,
            "surface_roughness_um": 20.0,
        }
        self.assertFalse(evaluate_attributes(marginal, "class-a")["conforming"])
        self.assertTrue(evaluate_attributes(marginal, "class-c")["conforming"])

    def test_value_exactly_on_a_limit_conforms(self):
        limits = DEFAULT_ACCEPTANCE_POLICY["attribute_limits"]["class-b"]
        on_limit = {
            "density_fraction": limits["min_density_fraction"],
            "porosity_fraction": limits["max_porosity_fraction"],
            "surface_roughness_um": limits["max_surface_roughness_um"],
        }
        self.assertAlmostEqual(
            on_limit["porosity_fraction"], limits["max_porosity_fraction"], places=12
        )
        self.assertTrue(evaluate_attributes(on_limit, "class-b")["conforming"])

    def test_unmeasured_attribute_is_open_not_passed(self):
        partial = dict(GOOD_MEASUREMENTS)
        del partial["porosity_fraction"]
        result = evaluate_attributes(partial, "class-b")
        self.assertFalse(result["conforming"])
        self.assertIn("porosity_fraction", result["missing"])

    def test_out_of_range_fraction_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attributes({"density_fraction": 1.4}, "class-b")

    def test_non_mapping_measurements_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attributes("dense", "class-b")


class ScreeningTests(unittest.TestCase):
    def test_no_gap_when_every_screen_ran(self):
        self.assertEqual(
            screening_gap("class-b", ("volumetric-ndt", "dimensional-check")), []
        )

    def test_missing_screen_is_reported(self):
        self.assertEqual(
            screening_gap("class-a", ("volumetric-ndt", "dimensional-check")),
            ["proof-test"],
        )

    def test_non_sequence_performed_rejected(self):
        with self.assertRaises(ValueError):
            screening_gap("class-b", "volumetric-ndt-and-dimensional")


class AcceptanceTests(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        result = assess_part_acceptance(GOOD_CASE)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], ACCEPTED)

    def test_finding_beyond_the_acceptance_number_rejects_the_lot(self):
        result = assess_part_acceptance(_case(GOOD_CASE, observed_non_conforming=1))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict"], REJECTED)
        self.assertFalse(result["lot_within_acceptance_number"])

    def test_missing_mandatory_screen_rejects_the_lot(self):
        result = assess_part_acceptance(
            _case(GOOD_CASE, screening_performed=("dimensional-check",))
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["screening_gap"], ["volumetric-ndt"])

    def test_bad_attribute_rejects_the_lot(self):
        poor = dict(GOOD_MEASUREMENTS)
        poor["porosity_fraction"] = 0.02
        result = assess_part_acceptance(_case(GOOD_CASE, measurements=poor))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("porosity" in f for f in result["findings"]))

    def test_more_findings_than_parts_examined_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_acceptance(_case(GOOD_CASE, observed_non_conforming=999))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_acceptance("class-b")

    def test_class_c_tolerates_one_finding(self):
        case = _case(
            GOOD_CASE,
            part_class="class-c",
            observed_non_conforming=1,
            screening_performed=("dimensional-check",),
        )
        result = assess_part_acceptance(case)
        self.assertTrue(result["lot_within_acceptance_number"])
        self.assertTrue(result["accepted"])


if __name__ == "__main__":
    unittest.main()
