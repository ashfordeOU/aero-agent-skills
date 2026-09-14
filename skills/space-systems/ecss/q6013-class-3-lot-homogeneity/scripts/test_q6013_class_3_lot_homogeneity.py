"""Contract tests for the clause 6.5.5 class 3 batch uniformity assessment.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a delivery carrying two package
codes, a date-code window wider than one batch may cover, a uniformity score
below the applicable threshold, a supplier batch declaration that misses a unit,
an undersized reduced sample, and a sample that never reaches one end of the
window.
"""

import unittest

from q6013_class_3_lot_homogeneity_logic import (
    DATE_CODE_WINDOW_EXCEEDED,
    DECISIVE_ATTRIBUTE_CONFLICT,
    DEFAULT_ATTRIBUTE_WEIGHTS,
    DEFAULT_BATCH_POLICY,
    SAMPLE_DOES_NOT_SPAN_WINDOW,
    UNIFORMITY_BELOW_THRESHOLD,
    UNIFORM_BATCH,
    WEEKS_PER_YEAR,
    assess_batch_uniformity,
    date_code_window_weeks,
    decisive_attribute_conflicts,
    declaration_covers_population,
    parse_date_code,
    reduced_sample_size,
    uniformity_score,
    validate_attribute_weights,
    validate_batch_policy,
    validate_declaration,
    validate_population,
    validate_unit,
    week_index_of,
    window_endpoint_coverage,
)


def _unit(identifier, code="2505", **overrides):
    unit = {
        "id": identifier,
        "part_number": "PN-4471",
        "package_code": "SOIC-8",
        "manufacturer": "maker-one",
        "country_of_origin": "origin-a",
        "marking_style": "laser-mark-b",
        "distributor_reference": "DL-2231",
        "date_code": code,
    }
    unit.update(overrides)
    return unit


def _delivery(count=16):
    units = []
    for i in range(1, count + 1):
        code = "2505" if i <= count // 2 else "2515"
        units.append(_unit("u-%02d" % i, code=code))
    return units


def _sample(count=16):
    return ["u-01", "u-02", "u-%02d" % (count - 1), "u-%02d" % count]


def _policy(**overrides):
    policy = dict(DEFAULT_BATCH_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {"units": _delivery(), "sample": _sample()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_batch_policy(None)
        self.assertEqual(settings["uniformity_threshold_percent"], 75)
        self.assertTrue(settings["require_window_endpoints"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_batch_policy({"sample_percentage": 10})

    def test_relief_threshold_above_the_plain_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_batch_policy({"declared_threshold_percent": 90})

    def test_threshold_outside_a_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_batch_policy({"uniformity_threshold_percent": 140})

    def test_max_below_min_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_batch_policy({"min_sample_units": 9, "max_sample_units": 4})

    def test_non_integer_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_batch_policy({"min_sample_units": 3.0})


class WeightTests(unittest.TestCase):
    def test_default_weights_sum_to_a_round_total(self):
        self.assertEqual(sum(DEFAULT_ATTRIBUTE_WEIGHTS.values()), 100)

    def test_decisive_attribute_cannot_be_given_a_weight(self):
        with self.assertRaises(ValueError):
            validate_attribute_weights({"package_code": 10})

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_attribute_weights({"manufacturer": 0})

    def test_empty_weight_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_attribute_weights({})


class DateCodeTests(unittest.TestCase):
    def test_date_code_parses_year_and_week(self):
        self.assertEqual(parse_date_code("2515"), (25, 15))

    def test_short_date_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("251")

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2500")

    def test_week_index_is_monotone_across_a_year_boundary(self):
        self.assertEqual(week_index_of("2601") - week_index_of("2552"), 1)

    def test_week_index_uses_the_declared_year_length(self):
        self.assertEqual(week_index_of("2601") - week_index_of("2501"), WEEKS_PER_YEAR)

    def test_century_rollover_delivery_rejected(self):
        units = _delivery(4)
        units[0]["date_code"] = "9901"
        units[1]["date_code"] = "0102"
        with self.assertRaises(ValueError):
            validate_population(units)

    def test_window_of_the_default_delivery_is_ten_weeks(self):
        self.assertEqual(date_code_window_weeks(validate_population(_delivery())), 10)


class UnitValidationTests(unittest.TestCase):
    def test_unit_without_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(_unit("u-01", manufacturer="  "))

    def test_unit_without_id_rejected(self):
        unit = _unit("u-01")
        del unit["id"]
        with self.assertRaises(ValueError):
            validate_unit(unit)

    def test_duplicate_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_population([_unit("u-01"), _unit("u-01")])

    def test_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            validate_population([])


class DecisiveAttributeTests(unittest.TestCase):
    def test_uniform_delivery_has_no_decisive_conflict(self):
        self.assertEqual(decisive_attribute_conflicts(validate_population(_delivery())), {})

    def test_two_package_codes_are_a_decisive_conflict(self):
        units = _delivery()
        units[0]["package_code"] = "TSSOP-8"
        conflicts = decisive_attribute_conflicts(validate_population(units))
        self.assertIn("package_code", conflicts)
        self.assertEqual(len(conflicts["package_code"]), 2)

    def test_two_part_numbers_are_a_decisive_conflict(self):
        units = _delivery()
        units[3]["part_number"] = "PN-9900"
        self.assertIn("part_number", decisive_attribute_conflicts(validate_population(units)))


class ScoringTests(unittest.TestCase):
    def test_fully_uniform_delivery_scores_the_whole_weight(self):
        score = uniformity_score(validate_population(_delivery()))
        self.assertEqual(score["matched_weight"], score["total_weight"])
        self.assertAlmostEqual(score["fraction"], 1.0, places=9)

    def test_one_varying_attribute_removes_exactly_its_weight(self):
        units = _delivery()
        units[0]["marking_style"] = "ink-mark-c"
        score = uniformity_score(validate_population(units))
        self.assertEqual(score["matched_weight"], 80)
        self.assertAlmostEqual(score["fraction"], 0.8, places=9)
        self.assertEqual(score["attributes_varying"], ["marking_style"])

    def test_empty_record_sequence_rejected(self):
        with self.assertRaises(ValueError):
            uniformity_score([])


class DeclarationTests(unittest.TestCase):
    def test_declaration_without_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration({"covers": ["u-01"]})

    def test_declaration_covering_nothing_rejected(self):
        with self.assertRaises(ValueError):
            validate_declaration({"reference": "SBD-1", "covers": []})

    def test_declaration_naming_every_unit_covers_the_delivery(self):
        records = validate_population(_delivery())
        declaration = {"reference": "SBD-1", "covers": [r["id"] for r in records]}
        self.assertTrue(declaration_covers_population(declaration, records)["covers"])

    def test_declaration_missing_one_unit_does_not_cover(self):
        records = validate_population(_delivery())
        declaration = {"reference": "SBD-1", "covers": [r["id"] for r in records[:-1]]}
        coverage = declaration_covers_population(declaration, records)
        self.assertFalse(coverage["covers"])
        self.assertEqual(coverage["missing"], ["u-16"])

    def test_absent_declaration_covers_nothing(self):
        records = validate_population(_delivery())
        self.assertFalse(declaration_covers_population(None, records)["covers"])


class SampleSizeTests(unittest.TestCase):
    def test_perfect_square_delivery_takes_its_exact_root(self):
        self.assertEqual(reduced_sample_size(16), 4)

    def test_non_square_delivery_takes_the_floor_of_the_root(self):
        self.assertEqual(reduced_sample_size(99), 9)

    def test_small_delivery_takes_the_sample_floor(self):
        self.assertEqual(reduced_sample_size(5), 3)

    def test_sample_never_exceeds_the_delivery(self):
        self.assertEqual(reduced_sample_size(2), 2)

    def test_large_delivery_takes_the_cap(self):
        self.assertEqual(reduced_sample_size(10000), 20)

    def test_zero_delivery_rejected(self):
        with self.assertRaises(ValueError):
            reduced_sample_size(0)

    def test_float_delivery_rejected(self):
        with self.assertRaises(ValueError):
            reduced_sample_size(16.0)


class EndpointTests(unittest.TestCase):
    def test_unit_drawn_twice_rejected(self):
        records = validate_population(_delivery())
        with self.assertRaises(ValueError):
            window_endpoint_coverage(records, ["u-01", "u-01"])

    def test_unit_outside_the_delivery_rejected(self):
        records = validate_population(_delivery())
        with self.assertRaises(ValueError):
            window_endpoint_coverage(records, ["u-99"])

    def test_sample_from_the_old_end_only_misses_the_new_end(self):
        records = validate_population(_delivery())
        coverage = window_endpoint_coverage(records, ["u-01", "u-02"])
        self.assertTrue(coverage["oldest_covered"])
        self.assertFalse(coverage["newest_covered"])


class AssessmentTests(unittest.TestCase):
    def test_uniform_delivery_with_a_spanning_sample_passes(self):
        result = assess_batch_uniformity(_case())
        self.assertEqual(result["verdict"], UNIFORM_BATCH)
        self.assertTrue(result["uniform"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["uniformity_fraction"], 1.0, places=9)

    def test_package_code_conflict_outranks_a_wide_window(self):
        units = _delivery()
        units[0]["package_code"] = "TSSOP-8"
        units[0]["date_code"] = "2401"
        result = assess_batch_uniformity(_case(units=units))
        self.assertEqual(result["verdict"], DECISIVE_ATTRIBUTE_CONFLICT)

    def test_wide_date_code_window_outranks_a_low_score(self):
        units = _delivery()
        units[0]["date_code"] = "2401"
        units[0]["marking_style"] = "ink-mark-c"
        units[0]["distributor_reference"] = "DL-9999"
        result = assess_batch_uniformity(_case(units=units))
        self.assertEqual(result["verdict"], DATE_CODE_WINDOW_EXCEEDED)
        self.assertGreater(result["date_code_window_weeks"], 26)

    def test_score_below_the_threshold_stops_the_delivery(self):
        units = _delivery()
        units[0]["marking_style"] = "ink-mark-c"
        units[0]["distributor_reference"] = "DL-9999"
        result = assess_batch_uniformity(_case(units=units))
        self.assertEqual(result["verdict"], UNIFORMITY_BELOW_THRESHOLD)
        self.assertEqual(result["uniformity_matched_weight"], 65)

    def test_score_landing_exactly_on_the_threshold_is_admitted(self):
        units = _delivery()
        units[0]["marking_style"] = "ink-mark-c"
        result = assess_batch_uniformity(
            _case(units=units, policy=_policy(uniformity_threshold_percent=80))
        )
        self.assertEqual(result["verdict"], UNIFORM_BATCH)

    def test_supplier_declaration_relaxes_the_threshold(self):
        units = _delivery()
        units[0]["marking_style"] = "ink-mark-c"
        units[0]["distributor_reference"] = "DL-9999"
        declaration = {"reference": "SBD-7", "covers": [u["id"] for u in units]}
        result = assess_batch_uniformity(_case(units=units, declaration=declaration))
        self.assertEqual(result["verdict"], UNIFORM_BATCH)
        self.assertTrue(result["declaration_relief_applied"])
        self.assertEqual(result["threshold_percent"], 50)

    def test_declaration_missing_a_unit_gives_no_relief(self):
        units = _delivery()
        units[0]["marking_style"] = "ink-mark-c"
        units[0]["distributor_reference"] = "DL-9999"
        declaration = {"reference": "SBD-7", "covers": [u["id"] for u in units[:-1]]}
        result = assess_batch_uniformity(_case(units=units, declaration=declaration))
        self.assertEqual(result["verdict"], UNIFORMITY_BELOW_THRESHOLD)
        self.assertFalse(result["declaration_relief_applied"])
        self.assertEqual(result["declaration_missing_units"], ["u-16"])

    def test_undersized_sample_does_not_span_the_window(self):
        result = assess_batch_uniformity(_case(sample=["u-01", "u-16"]))
        self.assertEqual(result["verdict"], SAMPLE_DOES_NOT_SPAN_WINDOW)
        self.assertEqual(result["required_sample_size"], 4)

    def test_sample_clustered_at_one_end_misses_the_other(self):
        result = assess_batch_uniformity(
            _case(sample=["u-01", "u-02", "u-03", "u-04"])
        )
        self.assertEqual(result["verdict"], SAMPLE_DOES_NOT_SPAN_WINDOW)
        self.assertEqual(result["window_endpoints_missed"], ["newest"])

    def test_endpoint_requirement_can_be_stood_down(self):
        result = assess_batch_uniformity(
            _case(
                sample=["u-01", "u-02", "u-03", "u-04"],
                policy=_policy(require_window_endpoints=False),
            )
        )
        self.assertEqual(result["verdict"], UNIFORM_BATCH)

    def test_missing_units_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_batch_uniformity({"sample": ["u-01"]})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_batch_uniformity(["units"])


if __name__ == "__main__":
    unittest.main()
