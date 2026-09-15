"""Contract tests for the clause 4.5.5 class 1 sample representativeness check.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a part with no stratum label, a
draw that is undersized, a stratum the draw never reached, a draw skewed away
from its proportional allocation, and defectives beyond the acceptance number.
"""

import unittest

from q60_class_1_lot_homogeneity_sampling_logic import (
    ALLOCATION_SKEWED,
    DEFAULT_SAMPLING_PLAN,
    LOT_REJECTED_ON_DEFECTIVES,
    REPRESENTATIVE_SAMPLE,
    SAMPLE_UNDERSIZED,
    STRATUM_UNREPRESENTED,
    allocate_sample,
    allocation_shortfalls,
    assess_sample_representativeness,
    evaluate_acceptance_number,
    largest_stratum_share,
    map_drawn_units,
    required_sample_size,
    stratify_lot,
    stratum_coverage_fraction,
    stratum_sizes,
    validate_lot,
    validate_part,
    validate_sampling_plan,
)


def _part(identifier, stratum="run-a"):
    return {"id": identifier, "stratum": stratum}


def _even_lot(per_stratum=25, strata=("run-a", "run-b")):
    parts = []
    for label in strata:
        for index in range(1, per_stratum + 1):
            parts.append(_part("%s-%02d" % (label, index), label))
    return parts


def _plan(**overrides):
    plan = dict(DEFAULT_SAMPLING_PLAN)
    plan.update(overrides)
    return plan


def _balanced_draw():
    return ["run-a-01", "run-a-02", "run-a-03", "run-b-01", "run-b-02"]


def _case(**overrides):
    case = {"parts": _even_lot(), "sample": _balanced_draw(), "defectives": 0}
    case.update(overrides)
    return case


class PlanTests(unittest.TestCase):
    def test_default_plan_validates(self):
        settings = validate_sampling_plan(None)
        self.assertEqual(settings["sample_denominator"], 10)
        self.assertTrue(settings["require_every_stratum_drawn"])

    def test_unknown_plan_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"sample_percentage": 10})

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan(["sample_numerator", 1])

    def test_boolean_is_not_an_integer_ratio(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"sample_numerator": True})

    def test_ratio_above_the_whole_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"sample_numerator": 11, "sample_denominator": 10})

    def test_cap_below_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"min_sample_units": 9, "max_sample_units": 4})

    def test_negative_acceptance_number_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"acceptance_number": -1})


class PartValidationTests(unittest.TestCase):
    def test_part_is_normalised(self):
        record = validate_part({"id": " p-1 ", "stratum": " run-a "})
        self.assertEqual(record, {"id": "p-1", "stratum": "run-a"})

    def test_part_without_stratum_is_refused(self):
        with self.assertRaises(ValueError):
            validate_part({"id": "p-1"})

    def test_part_without_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            validate_part({"stratum": "run-a"})

    def test_non_mapping_part_is_refused(self):
        with self.assertRaises(ValueError):
            validate_part("p-1")

    def test_duplicate_part_id_refused(self):
        with self.assertRaises(ValueError):
            validate_lot([_part("p-1"), _part("p-1")])

    def test_empty_lot_refused(self):
        with self.assertRaises(ValueError):
            validate_lot([])


class StratificationTests(unittest.TestCase):
    def test_parts_group_on_their_stratum_label(self):
        strata = stratify_lot(validate_lot(_even_lot(per_stratum=3)))
        self.assertEqual(sorted(strata), ["run-a", "run-b"])
        self.assertEqual(len(strata["run-a"]), 3)

    def test_stratum_sizes_count_each_group(self):
        sizes = stratum_sizes(stratify_lot(validate_lot(_even_lot(per_stratum=4))))
        self.assertEqual(sizes, {"run-a": 4, "run-b": 4})

    def test_empty_strata_mapping_refused(self):
        with self.assertRaises(ValueError):
            stratum_sizes({})

    def test_largest_stratum_share_of_an_even_lot(self):
        sizes = {"run-a": 25, "run-b": 25}
        self.assertAlmostEqual(largest_stratum_share(sizes, 50), 0.5, places=9)

    def test_largest_stratum_share_of_a_single_stratum_lot(self):
        self.assertAlmostEqual(largest_stratum_share({"run-a": 30}, 30), 1.0, places=9)


class SampleSizeTests(unittest.TestCase):
    def test_proportional_size_for_a_round_lot(self):
        self.assertEqual(required_sample_size(200), 20)

    def test_ratio_boundary_is_exact_in_integers(self):
        # 50 against one tenth lands exactly on 5; the floor is also 5, so the
        # answer must not drift with the platform's float rounding.
        self.assertEqual(required_sample_size(50), 5)

    def test_floor_lifts_a_small_lot(self):
        self.assertEqual(required_sample_size(12), 5)

    def test_cap_holds_a_large_lot(self):
        self.assertEqual(required_sample_size(5000), 45)

    def test_lot_smaller_than_the_floor_bounds_the_count(self):
        self.assertEqual(required_sample_size(3), 3)

    def test_non_integer_lot_size_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(20.0)

    def test_zero_lot_size_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(0)


class AllocationTests(unittest.TestCase):
    def test_even_strata_split_the_sample_evenly(self):
        self.assertEqual(allocate_sample({"run-a": 25, "run-b": 25}, 6),
                         {"run-a": 3, "run-b": 3})

    def test_allocation_always_sums_to_the_sample(self):
        allocation = allocate_sample({"a": 7, "b": 11, "c": 13}, 8)
        self.assertEqual(sum(allocation.values()), 8)

    def test_largest_remainder_favours_the_bigger_stratum(self):
        allocation = allocate_sample({"a": 90, "b": 10}, 5)
        self.assertEqual(allocation["a"], 5)
        self.assertEqual(allocation["b"], 0)

    def test_tie_is_broken_on_the_stratum_label(self):
        allocation = allocate_sample({"b": 10, "a": 10}, 3)
        self.assertEqual(allocation, {"a": 2, "b": 1})

    def test_sample_larger_than_the_lot_refused(self):
        with self.assertRaises(ValueError):
            allocate_sample({"a": 4}, 5)

    def test_empty_stratum_population_refused(self):
        with self.assertRaises(ValueError):
            allocate_sample({"a": 0}, 0)


class DrawMappingTests(unittest.TestCase):
    def test_drawn_units_land_in_their_strata(self):
        strata = stratify_lot(validate_lot(_even_lot(per_stratum=5)))
        mapped = map_drawn_units(strata, ["run-a-01", "run-b-02"])
        self.assertEqual(mapped["counts"], {"run-a": 1, "run-b": 1})

    def test_unit_outside_the_lot_refused(self):
        strata = stratify_lot(validate_lot(_even_lot(per_stratum=5)))
        with self.assertRaises(ValueError):
            map_drawn_units(strata, ["run-c-01"])

    def test_unit_drawn_twice_refused(self):
        strata = stratify_lot(validate_lot(_even_lot(per_stratum=5)))
        with self.assertRaises(ValueError):
            map_drawn_units(strata, ["run-a-01", "run-a-01"])

    def test_shortfall_is_zero_when_the_draw_meets_its_allocation(self):
        shortfalls = allocation_shortfalls({"a": 2, "b": 2}, {"a": 2, "b": 3})
        self.assertEqual(shortfalls, {"a": 0, "b": 0})

    def test_shortfall_counts_the_missing_units(self):
        shortfalls = allocation_shortfalls({"a": 4, "b": 2}, {"a": 1, "b": 2})
        self.assertEqual(shortfalls["a"], 3)

    def test_missing_draw_count_refused(self):
        with self.assertRaises(ValueError):
            allocation_shortfalls({"a": 1, "b": 1}, {"a": 1})

    def test_coverage_fraction_of_a_half_reached_lot(self):
        self.assertAlmostEqual(
            stratum_coverage_fraction({"a": 3, "b": 0}), 0.5, places=9
        )

    def test_coverage_fraction_of_a_fully_reached_lot(self):
        self.assertAlmostEqual(
            stratum_coverage_fraction({"a": 1, "b": 2}), 1.0, places=9
        )


class AcceptanceNumberTests(unittest.TestCase):
    def test_a_clean_sample_is_inside_the_acceptance_number(self):
        self.assertTrue(evaluate_acceptance_number(0, 5))

    def test_one_defective_against_a_zero_acceptance_number(self):
        self.assertFalse(evaluate_acceptance_number(1, 5))

    def test_defectives_on_the_acceptance_number_still_accept(self):
        self.assertTrue(evaluate_acceptance_number(2, 10, _plan(acceptance_number=2)))

    def test_more_defectives_than_units_refused(self):
        with self.assertRaises(ValueError):
            evaluate_acceptance_number(6, 5)

    def test_negative_defectives_refused(self):
        with self.assertRaises(ValueError):
            evaluate_acceptance_number(-1, 5)


class AssessmentTests(unittest.TestCase):
    def test_a_balanced_draw_is_representative(self):
        result = assess_sample_representativeness(_case())
        self.assertEqual(result["verdict"], REPRESENTATIVE_SAMPLE)
        self.assertTrue(result["representative"])
        self.assertEqual(result["findings"], [])

    def test_required_size_and_allocation_are_reported(self):
        result = assess_sample_representativeness(_case())
        self.assertEqual(result["required_sample_size"], 5)
        self.assertEqual(sum(result["allocation"].values()), 5)

    def test_an_undersized_draw_is_named(self):
        result = assess_sample_representativeness(
            _case(sample=["run-a-01", "run-b-01"])
        )
        self.assertEqual(result["verdict"], SAMPLE_UNDERSIZED)
        self.assertFalse(result["representative"])

    def test_a_draw_that_misses_a_stratum_is_named(self):
        result = assess_sample_representativeness(
            _case(sample=["run-a-%02d" % i for i in range(1, 6)])
        )
        self.assertEqual(result["verdict"], STRATUM_UNREPRESENTED)
        self.assertEqual(result["unreached_strata"], ["run-b"])

    def test_a_skewed_draw_is_named_when_every_stratum_was_touched(self):
        result = assess_sample_representativeness(
            _case(
                parts=_even_lot(per_stratum=25, strata=("run-a", "run-b", "run-c", "run-d")),
                sample=["run-a-01", "run-a-02", "run-a-03", "run-a-04",
                        "run-b-01", "run-b-02", "run-b-03",
                        "run-c-01", "run-d-01", "run-d-02"],
                plan=_plan(max_allocation_shortfall_units=0),
            )
        )
        self.assertEqual(result["verdict"], ALLOCATION_SKEWED)
        self.assertIn("run-c", result["skewed_strata"])

    def test_defectives_reject_the_lot_even_when_the_draw_is_short(self):
        result = assess_sample_representativeness(
            _case(sample=["run-a-01", "run-b-01"], defectives=1)
        )
        self.assertEqual(result["verdict"], LOT_REJECTED_ON_DEFECTIVES)

    def test_coverage_fraction_travels_with_the_verdict(self):
        result = assess_sample_representativeness(_case())
        self.assertAlmostEqual(result["stratum_coverage_fraction"], 1.0, places=9)

    def test_largest_stratum_share_travels_with_the_verdict(self):
        result = assess_sample_representativeness(_case())
        self.assertAlmostEqual(result["largest_stratum_share"], 0.5, places=9)

    def test_a_part_without_a_stratum_stops_the_assessment(self):
        parts = _even_lot(per_stratum=3)
        parts.append({"id": "loose-1"})
        with self.assertRaises(ValueError):
            assess_sample_representativeness(_case(parts=parts, sample=[]))

    def test_stratum_requirement_can_be_waived(self):
        result = assess_sample_representativeness(
            _case(
                sample=["run-a-%02d" % i for i in range(1, 6)],
                plan=_plan(require_every_stratum_drawn=False,
                           max_allocation_shortfall_units=5),
            )
        )
        self.assertEqual(result["verdict"], REPRESENTATIVE_SAMPLE)
        self.assertEqual(result["unreached_strata"], [])

    def test_missing_parts_key_refused(self):
        with self.assertRaises(ValueError):
            assess_sample_representativeness({"sample": ["run-a-01"]})

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_sample_representativeness(["parts"])


if __name__ == "__main__":
    unittest.main()
