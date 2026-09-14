"""Contract tests for the clause 5.5.5 class 2 lot uniformity demonstration.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a unit with no wafer lot and no
declared equivalence basis, a date-code span wider than one inspection lot may
carry, more sub-lots than the intermediate class admits, an undersized sample,
and a sub-lot drawn short of its proportional target.
"""

import unittest

from q6013_class_2_lot_homogeneity_logic import (
    DATE_CODE_SPAN_EXCEEDED,
    DEFAULT_SAMPLING_POLICY,
    EQUIVALENCE_BASIS_NOT_DECLARED,
    LOT_ADMITTED_FOR_SAMPLING,
    SAMPLE_NOT_PROPORTIONAL,
    SUB_LOT_CAP_EXCEEDED,
    WEEKS_PER_YEAR,
    allocation_shortfalls,
    assess_lot_uniformity,
    date_code_span_weeks,
    date_code_week_index,
    group_units,
    parse_date_code,
    proportional_allocation,
    required_sample_size,
    sub_lot_key,
    validate_population,
    validate_sampling_policy,
    validate_unit,
)


def _unit(identifier, wafer="WL-3301", assembly="AS-1180", site="site-a",
          code="2612", basis=None):
    unit = {
        "id": identifier,
        "wafer_lot": wafer,
        "assembly_lot": assembly,
        "manufacturing_site": site,
        "date_code": code,
    }
    if basis is not None:
        unit["equivalence_basis"] = basis
    return unit


def _uniform_population(count=20):
    return [_unit("u-%02d" % index) for index in range(1, count + 1)]


def _policy(**overrides):
    policy = dict(DEFAULT_SAMPLING_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "units": _uniform_population(),
        "sample": ["u-%02d" % index for index in range(1, 6)],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_sampling_policy(None)
        self.assertEqual(settings["max_sub_lots"], 3)
        self.assertEqual(settings["sample_denominator"], 10)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"sample_percentage": 10})

    def test_non_integer_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"min_sample_units": 5.0})

    def test_zero_sub_lot_cap_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"max_sub_lots": 0})

    def test_sample_ratio_above_the_whole_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"sample_numerator": 11, "sample_denominator": 10})

    def test_max_below_min_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"min_sample_units": 20, "max_sample_units": 10})

    def test_negative_allocation_slack_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_policy({"allocation_slack_units": -1})


class DateCodeTests(unittest.TestCase):
    def test_date_code_parses_year_and_week(self):
        self.assertEqual(parse_date_code("2612"), (26, 12))

    def test_short_date_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("261")

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2600")

    def test_week_index_is_monotone_across_a_year_boundary(self):
        self.assertEqual(date_code_week_index("2601") - date_code_week_index("2552"), 1)

    def test_week_index_uses_the_declared_year_length(self):
        self.assertEqual(
            date_code_week_index("2701") - date_code_week_index("2601"), WEEKS_PER_YEAR
        )

    def test_century_rollover_population_rejected(self):
        units = _uniform_population(4)
        units[0]["date_code"] = "9902"
        units[1]["date_code"] = "0103"
        with self.assertRaises(ValueError):
            validate_population(units)

    def test_span_of_a_single_date_code_is_zero(self):
        self.assertEqual(date_code_span_weeks(validate_population(_uniform_population(4))), 0)


class UnitPlacementTests(unittest.TestCase):
    def test_unit_without_assembly_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(_unit("u-01", assembly="  "))

    def test_unit_without_id_rejected(self):
        unit = _unit("u-01")
        del unit["id"]
        with self.assertRaises(ValueError):
            validate_unit(unit)

    def test_duplicate_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_population([_unit("u-01"), _unit("u-01")])

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_population([])

    def test_a_traced_unit_keys_on_its_wafer_lot(self):
        record = validate_unit(_unit("u-01"))
        self.assertFalse(record["placed_on_basis"])
        self.assertEqual(sub_lot_key(record)[:2], ("traced", "WL-3301"))

    def test_a_unit_without_a_wafer_lot_is_placed_on_its_basis(self):
        record = validate_unit(_unit("u-01", wafer="", basis="same-site-same-window"))
        self.assertTrue(record["placed_on_basis"])
        self.assertEqual(sub_lot_key(record)[:2], ("basis", "same-site-same-window"))

    def test_a_unit_without_a_wafer_lot_is_refused_when_no_basis_is_admitted(self):
        settings = validate_sampling_policy({"allow_equivalence_basis": False})
        with self.assertRaises(ValueError):
            validate_unit(_unit("u-01", wafer=""), settings)


class GroupingTests(unittest.TestCase):
    def test_uniform_population_forms_one_sub_lot(self):
        self.assertEqual(len(group_units(validate_population(_uniform_population(6)))), 1)

    def test_a_second_wafer_lot_opens_a_second_sub_lot(self):
        units = _uniform_population(6)
        units[0]["wafer_lot"] = "WL-9002"
        self.assertEqual(len(group_units(validate_population(units))), 2)

    def test_a_second_site_opens_a_second_sub_lot(self):
        units = _uniform_population(6)
        units[0]["manufacturing_site"] = "site-b"
        self.assertEqual(len(group_units(validate_population(units))), 2)

    def test_traced_and_basis_units_never_share_a_sub_lot(self):
        units = _uniform_population(6)
        units[0]["wafer_lot"] = ""
        units[0]["equivalence_basis"] = "same-site-same-window"
        self.assertEqual(len(group_units(validate_population(units))), 2)


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


class AllocationTests(unittest.TestCase):
    def test_one_sub_lot_takes_the_whole_sample(self):
        groups = group_units(validate_population(_uniform_population(20)))
        allocation = proportional_allocation(groups, 5)
        self.assertEqual(sum(allocation.values()), 5)
        self.assertEqual(len(allocation), 1)

    def test_two_equal_sub_lots_split_the_sample(self):
        units = _uniform_population(20)
        for unit in units[:10]:
            unit["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        allocation = proportional_allocation(groups, 5)
        self.assertEqual(sum(allocation.values()), 5)
        self.assertEqual(sorted(allocation.values()), [2, 3])

    def test_allocation_follows_sub_lot_size(self):
        units = _uniform_population(20)
        units[0]["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        allocation = proportional_allocation(groups, 10)
        big = max(allocation.values())
        small = min(allocation.values())
        self.assertEqual(big + small, 10)
        self.assertGreater(big, small)

    def test_allocation_never_exceeds_a_sub_lot(self):
        units = _uniform_population(20)
        units[0]["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        allocation = proportional_allocation(groups, 20)
        for key, count in allocation.items():
            self.assertLessEqual(count, len(groups[key]))

    def test_allocating_more_than_the_lot_rejected(self):
        groups = group_units(validate_population(_uniform_population(6)))
        with self.assertRaises(ValueError):
            proportional_allocation(groups, 7)

    def test_allocation_is_reproducible(self):
        units = _uniform_population(21)
        for unit in units[:7]:
            unit["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        first = proportional_allocation(groups, 7)
        second = proportional_allocation(groups, 7)
        self.assertEqual(first, second)


class CoverageTests(unittest.TestCase):
    def test_specimen_outside_the_population_rejected(self):
        groups = group_units(validate_population(_uniform_population(5)))
        with self.assertRaises(ValueError):
            allocation_shortfalls(groups, proportional_allocation(groups, 5), ["u-99"])

    def test_specimen_drawn_twice_rejected(self):
        groups = group_units(validate_population(_uniform_population(5)))
        with self.assertRaises(ValueError):
            allocation_shortfalls(
                groups, proportional_allocation(groups, 5), ["u-01", "u-01"]
            )

    def test_a_sub_lot_with_no_specimen_is_named(self):
        units = _uniform_population(20)
        for unit in units[:10]:
            unit["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        allocation = proportional_allocation(groups, 5)
        report = allocation_shortfalls(groups, allocation, ["u-01", "u-02", "u-03"])
        self.assertEqual(len(report["untouched_sub_lots"]), 1)

    def test_slack_absorbs_a_single_specimen_shortfall(self):
        units = _uniform_population(20)
        for unit in units[:10]:
            unit["wafer_lot"] = "WL-9002"
        groups = group_units(validate_population(units))
        allocation = proportional_allocation(groups, 5)
        drawn = ["u-01", "u-02", "u-11", "u-12"]
        strict = allocation_shortfalls(groups, allocation, drawn, 0)
        loose = allocation_shortfalls(groups, allocation, drawn, 1)
        self.assertTrue(strict["short_sub_lots"])
        self.assertEqual(loose["short_sub_lots"], [])


class AssessmentTests(unittest.TestCase):
    def test_a_uniform_lot_is_admitted(self):
        result = assess_lot_uniformity(_case())
        self.assertEqual(result["verdict"], LOT_ADMITTED_FOR_SAMPLING)
        self.assertTrue(result["admitted"])
        self.assertEqual(result["findings"], [])

    def test_a_unit_without_wafer_lot_or_basis_closes_the_assessment(self):
        units = _uniform_population(20)
        units[0]["wafer_lot"] = ""
        result = assess_lot_uniformity(_case(units=units))
        self.assertEqual(result["verdict"], EQUIVALENCE_BASIS_NOT_DECLARED)
        self.assertEqual(result["undeclared_basis_units"], ["u-01"])

    def test_a_declared_basis_keeps_the_assessment_open(self):
        units = _uniform_population(20)
        units[0]["wafer_lot"] = ""
        units[0]["equivalence_basis"] = "same-site-same-window"
        result = assess_lot_uniformity(
            _case(units=units, sample=["u-01", "u-02", "u-03", "u-04", "u-05"])
        )
        self.assertNotEqual(result["verdict"], EQUIVALENCE_BASIS_NOT_DECLARED)
        self.assertEqual(result["units_on_equivalence_basis"], ["u-01"])

    def test_a_wide_date_code_span_outranks_the_sub_lot_cap(self):
        units = _uniform_population(20)
        units[0]["date_code"] = "2601"
        units[1]["date_code"] = "2650"
        for index, unit in enumerate(units[:4]):
            unit["wafer_lot"] = "WL-90%02d" % index
        result = assess_lot_uniformity(_case(units=units))
        self.assertEqual(result["verdict"], DATE_CODE_SPAN_EXCEEDED)
        self.assertEqual(result["date_code_span_weeks"], 49)
        self.assertGreater(result["sub_lot_count"], DEFAULT_SAMPLING_POLICY["max_sub_lots"])

    def test_more_sub_lots_than_the_cap_closes_on_the_cap(self):
        units = _uniform_population(20)
        for index, unit in enumerate(units[:4]):
            unit["wafer_lot"] = "WL-90%02d" % index
        result = assess_lot_uniformity(_case(units=units))
        self.assertEqual(result["verdict"], SUB_LOT_CAP_EXCEEDED)
        self.assertEqual(result["sub_lot_count"], 5)

    def test_three_sub_lots_are_still_one_inspection_lot(self):
        units = _uniform_population(21)
        for unit in units[7:14]:
            unit["wafer_lot"] = "WL-9002"
        for unit in units[14:]:
            unit["wafer_lot"] = "WL-9003"
        sample = ["u-01", "u-02", "u-03", "u-08", "u-09", "u-15", "u-16"]
        result = assess_lot_uniformity(_case(units=units, sample=sample))
        self.assertEqual(result["sub_lot_count"], 3)
        self.assertEqual(result["verdict"], LOT_ADMITTED_FOR_SAMPLING)

    def test_an_undersized_sample_is_not_proportional(self):
        result = assess_lot_uniformity(_case(sample=["u-01", "u-02"]))
        self.assertEqual(result["verdict"], SAMPLE_NOT_PROPORTIONAL)
        self.assertEqual(result["required_sample_size"], 5)

    def test_a_sample_clustered_in_one_sub_lot_is_not_proportional(self):
        units = _uniform_population(20)
        for unit in units[:10]:
            unit["wafer_lot"] = "WL-9002"
        result = assess_lot_uniformity(
            _case(units=units, sample=["u-01", "u-02", "u-03", "u-04", "u-05"])
        )
        self.assertEqual(result["verdict"], SAMPLE_NOT_PROPORTIONAL)
        self.assertTrue(result["short_sub_lots"])

    def test_the_report_carries_the_allocation_it_judged_against(self):
        result = assess_lot_uniformity(_case())
        self.assertEqual(sum(result["allocation"].values()), result["required_sample_size"])

    def test_case_without_units_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_uniformity({"sample": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_uniformity(["units"])

    def test_no_sample_drawn_is_reported_as_undersized(self):
        result = assess_lot_uniformity(_case(sample=[]))
        self.assertEqual(result["verdict"], SAMPLE_NOT_PROPORTIONAL)
        self.assertEqual(result["sample_size"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=0)
