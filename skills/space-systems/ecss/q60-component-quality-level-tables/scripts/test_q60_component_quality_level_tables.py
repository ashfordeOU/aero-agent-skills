"""Contract tests for the clause 7 quality level and test coverage tables."""

import unittest

from q60_component_quality_level_tables_logic import (
    COVERAGE_TOLERANCE,
    FAMILY_TESTS,
    LEVEL_BASELINE_TESTS,
    LEVEL_INDEPENDENT_FAMILY_TESTS,
    LEVEL_STRINGENCY,
    MAX_UPRATING_STEPS,
    QUALITY_LEVELS,
    QUALITY_LEVEL_TABLE,
    RELIABILITY_CLASSES,
    SUBSTANTIAL_COVERAGE_FLOOR,
    VERDICTS,
    assess_proposed_part,
    baseline_tests_for_level,
    coverage_fraction,
    family_tests_for_level,
    level_stringency,
    missing_tests,
    normalize_token,
    required_quality_level,
    required_test_coverage,
    uprating_steps,
    validate_family,
    validate_quality_level,
    validate_reliability_class,
)


def _part(**overrides):
    part = {
        "part_number": "CN-4408-D",
        "family": "connector",
        "reliability_class": 1,
        "proposed_quality_level": "level-2",
        "tests_performed": required_test_coverage("connector", 1),
        "uprating_permitted": True,
    }
    part.update(overrides)
    return part


class TokenAndValidationTests(unittest.TestCase):
    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(normalize_token("Tantalum_Capacitor"), "tantalum-capacitor")

    def test_every_family_validates(self):
        for token in QUALITY_LEVEL_TABLE:
            self.assertEqual(validate_family(token), token)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            validate_family("photomultiplier")

    def test_blank_family_rejected(self):
        with self.assertRaises(ValueError):
            validate_family("   ")

    def test_every_reliability_class_validates(self):
        for rel_class in RELIABILITY_CLASSES:
            self.assertEqual(validate_reliability_class(rel_class), rel_class)

    def test_reliability_class_outside_the_tables_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability_class(4)

    def test_boolean_reliability_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability_class(True)

    def test_non_integer_reliability_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability_class("1")

    def test_every_quality_level_validates(self):
        for token in QUALITY_LEVELS:
            self.assertEqual(validate_quality_level(token), token)

    def test_unknown_quality_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_quality_level("level-4")


class StringencyTests(unittest.TestCase):
    def test_level_one_is_the_most_demanding(self):
        self.assertGreater(level_stringency("level-1"), level_stringency("level-2"))

    def test_level_three_is_the_least_demanding(self):
        self.assertLess(level_stringency("level-3"), level_stringency("level-2"))

    def test_stringency_does_not_follow_the_level_digit(self):
        self.assertNotEqual(level_stringency("level-1"), 1)

    def test_every_level_has_a_stringency(self):
        for token in QUALITY_LEVELS:
            self.assertIn(token, LEVEL_STRINGENCY)


class TableLookupTests(unittest.TestCase):
    def test_every_family_maps_every_class(self):
        for family, row in QUALITY_LEVEL_TABLE.items():
            for rel_class in RELIABILITY_CLASSES:
                self.assertIn(row[rel_class], QUALITY_LEVELS, family)

    def test_class_one_is_never_less_demanding_than_class_three(self):
        for family in QUALITY_LEVEL_TABLE:
            self.assertGreaterEqual(
                level_stringency(required_quality_level(family, 1)),
                level_stringency(required_quality_level(family, 3)),
                family,
            )

    def test_microcircuit_class_one_needs_the_top_level(self):
        self.assertEqual(required_quality_level("microcircuit", 1), "level-1")

    def test_connector_class_one_needs_the_middle_level(self):
        self.assertEqual(required_quality_level("connector", 1), "level-2")

    def test_every_family_falls_to_the_lowest_level_in_class_three(self):
        for family in QUALITY_LEVEL_TABLE:
            self.assertEqual(required_quality_level(family, 3), "level-3", family)


class CoverageBuildTests(unittest.TestCase):
    def test_baseline_is_cumulative_upwards(self):
        self.assertTrue(
            baseline_tests_for_level("level-3").issubset(
                baseline_tests_for_level("level-2")
            )
        )
        self.assertTrue(
            baseline_tests_for_level("level-2").issubset(
                baseline_tests_for_level("level-1")
            )
        )

    def test_top_level_baseline_holds_every_declared_baseline_test(self):
        every = set()
        for tests in LEVEL_BASELINE_TESTS.values():
            every |= set(tests)
        self.assertEqual(baseline_tests_for_level("level-1"), every)

    def test_family_tests_survive_in_full_at_the_middle_level(self):
        self.assertEqual(
            family_tests_for_level("microcircuit", "level-2"),
            set(FAMILY_TESTS["microcircuit"]),
        )

    def test_only_level_independent_family_tests_survive_at_the_lowest_level(self):
        self.assertEqual(family_tests_for_level("microcircuit", "level-3"), set())
        self.assertEqual(
            family_tests_for_level("tantalum-capacitor", "level-3"),
            {"tantalum-capacitor-surge-current-test"},
        )

    def test_every_level_independent_test_belongs_to_some_family(self):
        every = set()
        for tests in FAMILY_TESTS.values():
            every |= set(tests)
        self.assertTrue(set(LEVEL_INDEPENDENT_FAMILY_TESTS).issubset(every))

    def test_required_coverage_is_sorted_and_duplicate_free(self):
        coverage = required_test_coverage("microcircuit", 1)
        self.assertEqual(coverage, sorted(set(coverage)))

    def test_class_one_coverage_is_never_smaller_than_class_three(self):
        for family in QUALITY_LEVEL_TABLE:
            self.assertGreaterEqual(
                len(required_test_coverage(family, 1)),
                len(required_test_coverage(family, 3)),
                family,
            )

    def test_a_fuse_keeps_its_interruption_test_in_every_class(self):
        for rel_class in RELIABILITY_CLASSES:
            self.assertIn(
                "fuse-current-interruption-test",
                required_test_coverage("fuse", rel_class),
            )


class ShortfallTests(unittest.TestCase):
    def test_full_coverage_is_one(self):
        required = required_test_coverage("connector", 1)
        self.assertAlmostEqual(coverage_fraction(required, required), 1.0, places=9)

    def test_no_coverage_is_zero(self):
        required = required_test_coverage("connector", 1)
        self.assertAlmostEqual(coverage_fraction([], required), 0.0, places=9)

    def test_half_the_required_tests_sits_exactly_on_the_floor(self):
        required = required_test_coverage("connector", 1)
        self.assertEqual(len(required), 4)
        fraction = coverage_fraction(required[:2], required)
        self.assertAlmostEqual(fraction, SUBSTANTIAL_COVERAGE_FLOOR, places=9)

    def test_unrelated_tests_do_not_earn_coverage(self):
        required = required_test_coverage("connector", 1)
        self.assertAlmostEqual(
            coverage_fraction(["solar-array-thermal-cycling"], required), 0.0, places=9
        )

    def test_empty_required_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(["lot-acceptance-electrical-test"], [])

    def test_non_list_proposed_tests_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction("lot-acceptance-electrical-test", ["a-test"])

    def test_missing_tests_names_the_gap(self):
        required = required_test_coverage("microcircuit", 1)
        gap = missing_tests(required[1:], required)
        self.assertEqual(gap, [required[0]])

    def test_missing_tests_is_empty_when_covered(self):
        required = required_test_coverage("microcircuit", 1)
        self.assertEqual(missing_tests(required, required), [])

    def test_uprating_steps_is_zero_when_the_level_is_met(self):
        self.assertEqual(uprating_steps("level-1", "level-2"), 0)

    def test_uprating_steps_counts_stringency_not_level_numbers(self):
        self.assertEqual(uprating_steps("level-3", "level-1"), 2)
        self.assertEqual(uprating_steps("level-2", "level-1"), 1)

    def test_the_boundary_tolerance_is_far_below_a_percentage_point(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class AssessmentTests(unittest.TestCase):
    def test_a_part_at_its_level_with_full_coverage_is_usable(self):
        result = assess_proposed_part(_part())
        self.assertEqual(result["verdict"], "meets-required-level")
        self.assertTrue(result["usable_as_proposed"])
        self.assertEqual(result["findings"], [])

    def test_a_better_level_than_required_still_meets_the_requirement(self):
        result = assess_proposed_part(_part(proposed_quality_level="level-1"))
        self.assertEqual(result["uprating_steps"], 0)
        self.assertEqual(result["verdict"], "meets-required-level")

    def test_one_step_below_with_substantial_coverage_can_be_uprated(self):
        required = required_test_coverage("connector", 1)
        result = assess_proposed_part(
            _part(
                proposed_quality_level="level-3",
                tests_performed=required[:2],
            )
        )
        self.assertEqual(result["uprating_steps"], 1)
        self.assertAlmostEqual(
            result["coverage_fraction"], SUBSTANTIAL_COVERAGE_FLOOR, places=9
        )
        self.assertEqual(result["verdict"], "uprating-required")

    def test_two_steps_below_cannot_be_uprated(self):
        result = assess_proposed_part(
            _part(
                family="microcircuit",
                proposed_quality_level="level-3",
                tests_performed=required_test_coverage("microcircuit", 1),
            )
        )
        self.assertEqual(result["uprating_steps"], 2)
        self.assertEqual(result["verdict"], "not-acceptable")

    def test_uprating_refused_on_the_project_blocks_the_part(self):
        required = required_test_coverage("connector", 1)
        result = assess_proposed_part(
            _part(
                proposed_quality_level="level-3",
                tests_performed=required[:3],
                uprating_permitted=False,
            )
        )
        self.assertEqual(result["verdict"], "not-acceptable")
        self.assertTrue(
            any("uprating is not permitted" in f for f in result["findings"]),
            result["findings"],
        )

    def test_coverage_below_the_floor_blocks_an_uprating(self):
        required = required_test_coverage("connector", 1)
        result = assess_proposed_part(
            _part(
                proposed_quality_level="level-3",
                tests_performed=required[:1],
            )
        )
        self.assertEqual(result["verdict"], "not-acceptable")

    def test_a_missing_test_at_the_right_level_is_still_a_shortfall(self):
        required = required_test_coverage("connector", 1)
        result = assess_proposed_part(_part(tests_performed=required[:3]))
        self.assertEqual(result["uprating_steps"], 0)
        self.assertEqual(result["missing_tests"], [required[3]])
        self.assertNotEqual(result["verdict"], "meets-required-level")

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_proposed_part(_part(part_number="   "))

    def test_missing_key_rejected(self):
        part = _part()
        del part["reliability_class"]
        with self.assertRaises(ValueError):
            assess_proposed_part(part)

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_proposed_part(["CN-4408-D"])

    def test_non_boolean_uprating_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_proposed_part(_part(uprating_permitted="yes"))

    def test_uprating_flag_defaults_to_permitted(self):
        part = _part()
        del part["uprating_permitted"]
        self.assertTrue(assess_proposed_part(part)["uprating_permitted"])

    def test_verdict_is_always_from_the_fixed_vocabulary(self):
        for level in QUALITY_LEVELS:
            result = assess_proposed_part(_part(proposed_quality_level=level))
            self.assertIn(result["verdict"], VERDICTS)

    def test_the_uprating_step_limit_is_a_single_step(self):
        self.assertEqual(MAX_UPRATING_STEPS, 1)


if __name__ == "__main__":
    unittest.main()
