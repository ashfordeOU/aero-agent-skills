"""Contract tests for the clause 4.5.5 class 1 lot homogeneity assessment.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a unit with no traceability, a
date-code span wider than one lot may carry, a population that is really
several sub-lots, an undersized sample, and a sub-lot the sample never reached.
"""

import unittest

from q6013_class_1_lot_homogeneity_logic import (
    DATE_CODE_SPAN_EXCEEDED,
    DEFAULT_SAMPLING_POLICY,
    HOMOGENEOUS_LOT,
    MULTIPLE_SUB_LOTS,
    SAMPLE_NOT_REPRESENTATIVE,
    WEEKS_PER_YEAR,
    assess_lot_homogeneity,
    date_code_span_weeks,
    date_code_week_index,
    group_units,
    largest_sub_lot_share,
    parse_date_code,
    required_sample_size,
    sample_coverage,
    traceability_key,
    validate_population,
    validate_sampling_policy,
    validate_unit,
)


def _unit(identifier, wafer="WL-7741", assembly="AS-2210", site="site-a", code="2508"):
    return {
        "id": identifier,
        "wafer_lot": wafer,
        "assembly_lot": assembly,
        "manufacturing_site": site,
        "date_code": code,
    }


def _uniform_population(count=20):
    return [_unit("u-%02d" % i) for i in range(1, count + 1)]


def _policy(**overrides):
    policy = dict(DEFAULT_SAMPLING_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "units": _uniform_population(),
        "sample": ["u-%02d" % i for i in range(1, 6)],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_sampling_policy(None)
        self.assertEqual(settings["sample_denominator"], 10)
        self.assertFalse(settings["allow_sub_lots"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"sample_percentage": 10})

    def test_non_integer_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"min_sample_units": 5.0})

    def test_sample_ratio_above_the_whole_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"sample_numerator": 11, "sample_denominator": 10})

    def test_max_below_min_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"min_sample_units": 20, "max_sample_units": 10})


class DateCodeTests(unittest.TestCase):
    def test_date_code_parses_year_and_week(self):
        self.assertEqual(parse_date_code("2508"), (25, 8))

    def test_short_date_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("258")

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2500")

    def test_week_index_is_monotone_across_a_year_boundary(self):
        self.assertEqual(
            date_code_week_index("2501") - date_code_week_index("2452"), 1
        )

    def test_week_index_uses_the_declared_year_length(self):
        self.assertEqual(
            date_code_week_index("2601") - date_code_week_index("2501"), WEEKS_PER_YEAR
        )

    def test_century_rollover_population_rejected(self):
        units = _uniform_population(4)
        units[0]["date_code"] = "9902"
        units[1]["date_code"] = "0103"
        with self.assertRaises(ValueError):
            validate_population(units)


class UnitValidationTests(unittest.TestCase):
    def test_unit_without_wafer_lot_rejected(self):
        unit = _unit("u-01")
        unit["wafer_lot"] = "   "
        with self.assertRaises(ValueError):
            validate_unit(unit)

    def test_unit_without_id_rejected(self):
        unit = _unit("u-01")
        del unit["id"]
        with self.assertRaises(ValueError):
            validate_unit(unit)

    def test_duplicate_unit_id_rejected(self):
        units = [_unit("u-01"), _unit("u-01")]
        with self.assertRaises(ValueError):
            validate_population(units)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_population([])

    def test_traceability_key_carries_three_fields(self):
        self.assertEqual(
            traceability_key(validate_unit(_unit("u-01"))),
            ("WL-7741", "AS-2210", "site-a"),
        )


class GroupingTests(unittest.TestCase):
    def test_uniform_population_forms_one_group(self):
        groups = group_units(validate_population(_uniform_population(6)))
        self.assertEqual(len(groups), 1)

    def test_a_second_wafer_lot_opens_a_second_group(self):
        units = _uniform_population(6)
        units[0]["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        self.assertEqual(len(groups), 2)

    def test_span_of_a_single_date_code_is_zero(self):
        self.assertEqual(date_code_span_weeks(validate_population(_uniform_population(4))), 0)

    def test_largest_sub_lot_share_is_reported(self):
        units = _uniform_population(4)
        units[0]["assembly_lot"] = "AS-9999"
        groups = group_units(validate_population(units))
        self.assertAlmostEqual(largest_sub_lot_share(groups, 4), 0.75, places=9)

    def test_largest_share_of_a_uniform_lot_is_one(self):
        groups = group_units(validate_population(_uniform_population(8)))
        self.assertAlmostEqual(largest_sub_lot_share(groups, 8), 1.0, places=9)


class SampleSizeTests(unittest.TestCase):
    def test_proportional_sample_is_rounded_up(self):
        self.assertEqual(required_sample_size(101), 11)

    def test_exact_ratio_lands_on_the_whole_number(self):
        self.assertEqual(required_sample_size(200), 20)

    def test_small_lot_takes_the_floor(self):
        self.assertEqual(required_sample_size(20), 5)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_size(3), 3)

    def test_large_lot_takes_the_cap(self):
        self.assertEqual(required_sample_size(10000), 45)

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(0)

    def test_float_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(50.0)


class CoverageTests(unittest.TestCase):
    def test_specimen_outside_the_population_rejected(self):
        groups = group_units(validate_population(_uniform_population(5)))
        with self.assertRaises(ValueError):
            sample_coverage(groups, ["u-99"])

    def test_specimen_drawn_twice_rejected(self):
        groups = group_units(validate_population(_uniform_population(5)))
        with self.assertRaises(ValueError):
            sample_coverage(groups, ["u-01", "u-01"])

    def test_untouched_sub_lot_is_named(self):
        units = _uniform_population(6)
        units[5]["assembly_lot"] = "AS-9999"
        groups = group_units(validate_population(units))
        coverage = sample_coverage(groups, ["u-01", "u-02"])
        self.assertEqual(len(coverage["unsampled_sub_lots"]), 1)


class AssessmentTests(unittest.TestCase):
    def test_uniform_lot_with_a_full_sample_is_homogeneous(self):
        result = assess_lot_homogeneity(_case())
        self.assertEqual(result["verdict"], HOMOGENEOUS_LOT)
        self.assertTrue(result["homogeneous"])
        self.assertEqual(result["findings"], [])

    def test_mixed_wafer_lots_give_the_sub_lot_verdict(self):
        units = _uniform_population()
        units[0]["wafer_lot"] = "WL-9002"
        result = assess_lot_homogeneity(_case(units=units))
        self.assertEqual(result["verdict"], MULTIPLE_SUB_LOTS)
        self.assertEqual(result["sub_lot_count"], 2)

    def test_wide_date_code_span_outranks_the_sub_lot_finding(self):
        units = _uniform_population()
        units[0]["date_code"] = "2401"
        units[0]["wafer_lot"] = "WL-9002"
        result = assess_lot_homogeneity(_case(units=units))
        self.assertEqual(result["verdict"], DATE_CODE_SPAN_EXCEEDED)
        self.assertGreater(result["date_code_span_weeks"], 13)

    def test_undersized_sample_is_not_representative(self):
        result = assess_lot_homogeneity(_case(sample=["u-01", "u-02"]))
        self.assertEqual(result["verdict"], SAMPLE_NOT_REPRESENTATIVE)
        self.assertEqual(result["required_sample_size"], 5)

    def test_permitted_sub_lots_still_need_a_specimen_each(self):
        units = _uniform_population()
        units[19]["assembly_lot"] = "AS-9999"
        result = assess_lot_homogeneity(
            _case(units=units, policy=_policy(allow_sub_lots=True))
        )
        self.assertEqual(result["verdict"], SAMPLE_NOT_REPRESENTATIVE)
        self.assertEqual(len(result["unsampled_sub_lots"]), 1)

    def test_permitted_sub_lots_each_sampled_pass(self):
        units = _uniform_population()
        units[19]["assembly_lot"] = "AS-9999"
        result = assess_lot_homogeneity(
            _case(
                units=units,
                sample=["u-01", "u-02", "u-03", "u-04", "u-20"],
                policy=_policy(allow_sub_lots=True),
            )
        )
        self.assertEqual(result["verdict"], HOMOGENEOUS_LOT)

    def test_share_of_the_largest_sub_lot_is_reported(self):
        result = assess_lot_homogeneity(_case())
        self.assertAlmostEqual(result["largest_sub_lot_share"], 1.0, places=9)

    def test_missing_units_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_homogeneity({"sample": ["u-01"]})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_homogeneity(["units"])


if __name__ == "__main__":
    unittest.main()
