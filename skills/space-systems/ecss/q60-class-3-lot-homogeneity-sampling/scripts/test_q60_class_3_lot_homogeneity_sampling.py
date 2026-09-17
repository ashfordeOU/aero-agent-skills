"""Contract tests for the clause 6.5.5 class 3 radiation sample set logic."""

import unittest

from q60_class_3_lot_homogeneity_sampling_logic import (
    PER_GROUP_IRRADIATED_MINIMUM,
    RADIATION_TEST_METHODS,
    SPECIMEN_ROLES,
    UNIFORMITY_AXES,
    assess_class_3_sample_set,
    group_codes,
    group_gaps,
    off_reference_specimens,
    parse_date_code,
    population_coverage,
    population_groups,
    required_sample_size,
    role_counts,
    specimen_axis_mismatches,
    supported_population,
    validate_bias_conditions,
    window_endpoints_covered,
)


def reference():
    return {
        "part_number": "LMV321-SOT23",
        "manufacturer": "Northgate Semiconductor",
        "package_code": "SOT23-5",
        "date_code": "2412",
    }


def population():
    units = []
    for index, code in enumerate(("2412", "2412", "2412", "2426", "2426", "2451")):
        units.append(
            dict(reference(), unit_id="FU-%03d" % (index + 1), date_code=code)
        )
    return units


def specimens(codes=None, role="irradiated", start=1):
    """Return specimens of one role drawn from the given date codes."""
    codes = codes or []
    drawn = []
    for offset, code in enumerate(codes):
        drawn.append(
            dict(
                reference(),
                specimen_id="SP-%s-%03d" % (role[:3].upper(), start + offset),
                role=role,
                date_code=code,
            )
        )
    return drawn


def full_set():
    """Return a set that covers every group and every role for a TID run."""
    irradiated_codes = ["2412"] * 4 + ["2426"] * 3 + ["2451"] * 3
    drawn = specimens(irradiated_codes, "irradiated", 1)
    drawn += specimens(["2412", "2426", "2451"], "control", 1)
    drawn += specimens(["2412", "2426"], "spare", 1)
    return drawn


class DateCodeTests(unittest.TestCase):
    def test_a_four_digit_code_becomes_an_ordered_pair(self):
        self.assertEqual(parse_date_code("2426"), (2024, 26))

    def test_a_week_of_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2400")

    def test_a_non_numeric_code_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("24W2")

    def test_codes_order_by_year_then_week(self):
        self.assertLess(parse_date_code("2451"), parse_date_code("2501"))


class GroupingTests(unittest.TestCase):
    def test_the_population_is_grouped_on_its_date_codes(self):
        groups = population_groups(population())
        self.assertEqual(groups, {"2412": 3, "2426": 2, "2451": 1})

    def test_the_groups_order_oldest_to_newest(self):
        self.assertEqual(group_codes(population_groups(population())), ("2412", "2426", "2451"))

    def test_an_empty_population_is_rejected(self):
        with self.assertRaises(ValueError):
            population_groups([])

    def test_a_unit_missing_a_uniformity_axis_is_rejected(self):
        unit = dict(reference())
        del unit["manufacturer"]
        with self.assertRaises(ValueError):
            population_groups([unit])

    def test_a_unit_with_an_unreadable_date_code_is_rejected(self):
        with self.assertRaises(ValueError):
            population_groups([dict(reference(), date_code="Q2-24")])

    def test_an_empty_grouping_is_rejected(self):
        with self.assertRaises(ValueError):
            group_codes({})


class SizingTests(unittest.TestCase):
    def test_bias_conditions_scale_a_method_that_says_they_do(self):
        one = required_sample_size("total-ionising-dose", 1, 1)
        two = required_sample_size("total-ionising-dose", 1, 2)
        self.assertEqual(two["irradiated"], 2 * one["irradiated"])

    def test_bias_conditions_do_not_scale_a_method_that_says_they_do_not(self):
        one = required_sample_size("displacement-damage", 1, 1)
        three = required_sample_size("displacement-damage", 1, 3)
        self.assertEqual(one["irradiated"], three["irradiated"])

    def test_a_wider_population_raises_the_irradiated_floor(self):
        narrow = required_sample_size("single-event-effects", 1, 1)
        wide = required_sample_size("single-event-effects", 8, 1)
        self.assertEqual(wide["irradiated"], PER_GROUP_IRRADIATED_MINIMUM * 8)
        self.assertGreater(wide["irradiated"], narrow["irradiated"])

    def test_one_control_is_owed_per_group_once_groups_outnumber_the_base(self):
        sized = required_sample_size("single-event-effects", 5, 1)
        self.assertEqual(sized["control"], 5)

    def test_the_total_is_the_sum_of_the_roles(self):
        sized = required_sample_size("total-ionising-dose", 3, 2)
        self.assertEqual(
            sized["total"], sized["irradiated"] + sized["control"] + sized["spare"]
        )

    def test_zero_bias_conditions_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_conditions(0)

    def test_a_boolean_bias_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_conditions(True)

    def test_an_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size("proton-ish", 1, 1)

    def test_a_group_count_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size("total-ionising-dose", 0, 1)

    def test_every_method_declares_all_three_role_bases(self):
        for spec in RADIATION_TEST_METHODS.values():
            self.assertIn("base_irradiated", spec)
            self.assertIn("base_controls", spec)
            self.assertIn("base_spares", spec)


class RoleTests(unittest.TestCase):
    def test_the_offered_roles_are_counted(self):
        counts = role_counts(full_set())
        self.assertEqual(counts["irradiated"], 10)
        self.assertEqual(counts["control"], 3)
        self.assertEqual(counts["spare"], 2)

    def test_every_role_appears_in_the_count_even_at_zero(self):
        counts = role_counts(specimens(["2412"], "irradiated"))
        for role in SPECIMEN_ROLES:
            self.assertIn(role, counts)

    def test_an_unknown_role_is_rejected(self):
        bad = specimens(["2412"], "irradiated")
        bad[0]["role"] = "witness"
        with self.assertRaises(ValueError):
            role_counts(bad)

    def test_one_specimen_cannot_fill_two_roles(self):
        duplicated = specimens(["2412"], "irradiated") + specimens(["2412"], "irradiated")
        with self.assertRaises(ValueError):
            role_counts(duplicated)


class UniformityTests(unittest.TestCase):
    def test_a_matching_specimen_has_no_mismatched_axis(self):
        self.assertEqual(specimen_axis_mismatches(dict(reference()), reference()), ())

    def test_a_different_package_is_a_mismatch(self):
        specimen = dict(reference(), package_code="SOIC-8")
        self.assertEqual(specimen_axis_mismatches(specimen, reference()), ("package_code",))

    def test_a_second_source_specimen_is_a_mismatch(self):
        specimen = dict(reference(), manufacturer="Southbank Devices")
        self.assertIn("manufacturer", specimen_axis_mismatches(specimen, reference()))

    def test_the_date_code_is_not_a_uniformity_axis(self):
        self.assertNotIn("date_code", UNIFORMITY_AXES)
        specimen = dict(reference(), date_code="2451")
        self.assertEqual(specimen_axis_mismatches(specimen, reference()), ())

    def test_off_reference_specimens_are_named_individually(self):
        drawn = specimens(["2412"], "irradiated")
        drawn[0]["part_number"] = "OPA333-SOT23"
        offenders = off_reference_specimens(drawn, reference())
        self.assertEqual(len(offenders), 1)
        self.assertIn("part_number", offenders[0])


class CoverageTests(unittest.TestCase):
    def test_a_group_under_the_floor_is_a_gap(self):
        drawn = specimens(["2412", "2412", "2426"], "irradiated")
        self.assertEqual(group_gaps(("2412", "2426", "2451"), drawn), ("2426", "2451"))

    def test_a_fully_covered_population_has_no_gap(self):
        self.assertEqual(group_gaps(("2412", "2426", "2451"), full_set()), ())

    def test_control_specimens_do_not_close_a_gap(self):
        drawn = specimens(["2451", "2451"], "control")
        self.assertIn("2451", group_gaps(("2451",), drawn))

    def test_both_window_ends_are_reported(self):
        endpoints = window_endpoints_covered(("2412", "2426", "2451"), full_set())
        self.assertEqual(endpoints["oldest"], "2412")
        self.assertEqual(endpoints["newest"], "2451")
        self.assertTrue(endpoints["both_covered"])

    def test_a_missing_newest_group_shows_at_the_endpoint_check(self):
        drawn = specimens(["2412", "2412", "2426", "2426"], "irradiated")
        endpoints = window_endpoints_covered(("2412", "2426", "2451"), drawn)
        self.assertTrue(endpoints["oldest_covered"])
        self.assertFalse(endpoints["newest_covered"])
        self.assertFalse(endpoints["both_covered"])

    def test_an_empty_code_list_is_rejected(self):
        with self.assertRaises(ValueError):
            window_endpoints_covered((), full_set())

    def test_the_result_reaches_only_the_represented_units(self):
        drawn = specimens(["2412", "2412"], "irradiated")
        reached = supported_population(population(), drawn)
        self.assertEqual(len(reached), 3)

    def test_the_coverage_share_is_exact_and_also_a_fraction(self):
        drawn = specimens(["2412", "2412"], "irradiated")
        share = population_coverage(population(), drawn)
        self.assertEqual(share["numerator"], 3)
        self.assertEqual(share["denominator"], 6)
        self.assertAlmostEqual(share["fraction"], 0.5, places=9)

    def test_full_coverage_is_the_whole_population(self):
        share = population_coverage(population(), full_set())
        self.assertAlmostEqual(share["fraction"], 1.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_a_well_composed_set_carries_the_whole_population(self):
        result = assess_class_3_sample_set(
            "total-ionising-dose", 1, population(), full_set(), reference()
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["composed"])
        self.assertEqual(result["result_scope"], "whole-flight-population")

    def test_a_second_bias_condition_makes_the_same_set_short(self):
        result = assess_class_3_sample_set(
            "total-ionising-dose", 2, population(), full_set(), reference()
        )
        self.assertGreater(result["shortfalls"]["irradiated"], 0)
        self.assertTrue(any("against the" in f for f in result["findings"]))

    def test_an_unrepresented_group_limits_where_the_result_may_be_written(self):
        drawn = specimens(["2412"] * 4 + ["2426"] * 3, "irradiated")
        drawn += specimens(["2412", "2426", "2451"], "control")
        drawn += specimens(["2412", "2426"], "spare")
        result = assess_class_3_sample_set(
            "total-ionising-dose", 1, population(), drawn, reference()
        )
        self.assertEqual(result["result_scope"], "represented-groups-only")
        self.assertIn("2451", result["group_gaps"])

    def test_an_empty_beam_leaves_the_result_with_no_population(self):
        drawn = specimens(["2412", "2426", "2451"], "control")
        result = assess_class_3_sample_set(
            "single-event-effects", 1, population(), drawn, reference()
        )
        self.assertEqual(result["result_scope"], "no-population")

    def test_an_off_reference_specimen_is_a_finding(self):
        drawn = full_set()
        drawn[0] = dict(drawn[0], package_code="SOIC-8")
        result = assess_class_3_sample_set(
            "total-ionising-dose", 1, population(), drawn, reference()
        )
        self.assertTrue(any("differs from the flight parts" in f for f in result["findings"]))

    def test_the_window_ends_are_checked_separately_from_the_gaps(self):
        drawn = specimens(["2412"] * 5 + ["2426"] * 5, "irradiated")
        drawn += specimens(["2412", "2426", "2451"], "control")
        drawn += specimens(["2412", "2426"], "spare")
        result = assess_class_3_sample_set(
            "total-ionising-dose", 1, population(), drawn, reference()
        )
        self.assertFalse(result["window_endpoints"]["newest_covered"])
        self.assertTrue(any("window ends" in f for f in result["findings"]))

    def test_the_grouping_and_the_sizing_are_both_reported(self):
        result = assess_class_3_sample_set(
            "total-ionising-dose", 1, population(), full_set(), reference()
        )
        self.assertEqual(result["group_codes"], ("2412", "2426", "2451"))
        self.assertEqual(result["required"]["group_count"], 3)

    def test_a_reference_missing_an_axis_is_rejected(self):
        bad = dict(reference())
        del bad["package_code"]
        with self.assertRaises(ValueError):
            assess_class_3_sample_set(
                "total-ionising-dose", 1, population(), full_set(), bad
            )

    def test_an_unknown_method_is_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_class_3_sample_set(
                "gamma-ish", 1, population(), full_set(), reference()
            )

    def test_a_population_that_is_not_a_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_sample_set(
                "total-ionising-dose", 1, "FU-001", full_set(), reference()
            )


if __name__ == "__main__":
    unittest.main()
