"""Contract tests for the clause 6.2.3.3 Class 3 constructional-analysis logic."""

import copy
import unittest

from q60_class_3_constructional_analysis_logic import (
    ATTRIBUTE_CRITICALITY,
    CONFORMANCE_FLOOR,
    CONSTRUCTION_ANALYSIS_INCOMPLETE,
    CONSTRUCTION_CONFORMS,
    CONSTRUCTION_DEVIATION,
    CRITICALITY_WEIGHTS,
    NUMERIC_ATTRIBUTES,
    NUMERIC_MATCH_TOLERANCE,
    assess_constructional_analysis,
    assess_sample_coverage,
    attribute_criticality,
    attribute_values_match,
    attribute_weight,
    compare_to_baseline,
    conformance_index,
    cross_group_consistency,
    sample_plan,
    validate_attribute,
    validate_baseline,
    validate_date_code_groups,
)

BASELINE = {
    "die-metallization": "aluminium",
    "die-attach": "epoxy",
    "wire-bond-material": "gold",
    "passivation": "silicon nitride",
    "wire-bond-diameter-um": 25.0,
    "lead-finish": "tin-lead",
}


def _observed(**overrides):
    observed = {
        "die-metallization": "aluminium",
        "die-attach": "epoxy",
        "wire-bond-material": "gold",
        "passivation": "silicon nitride",
        "wire-bond-diameter-um": 25.4,
        "lead-finish": "tin-lead",
    }
    observed.update(overrides)
    return observed


def _groups():
    return [
        {
            "date_code": "2431",
            "population": 50,
            "samples_examined": 5,
            "observed": _observed(),
        },
        {
            "date_code": "2508",
            "population": 50,
            "samples_examined": 5,
            "observed": _observed(),
        },
    ]


def _case(**overrides):
    case = {
        "manufacturer": "Example Microelectronics",
        "part_number": "EX-2210-C3",
        "baseline": dict(BASELINE),
        "date_code_groups": _groups(),
    }
    case.update(overrides)
    return case


class AttributeCatalogueTests(unittest.TestCase):
    def test_every_attribute_has_a_known_criticality(self):
        for attribute in ATTRIBUTE_CRITICALITY:
            self.assertIn(attribute_criticality(attribute), CRITICALITY_WEIGHTS)

    def test_a_critical_attribute_outweighs_a_minor_one(self):
        self.assertGreater(
            attribute_weight("wire-bond-material"), attribute_weight("lead-finish")
        )

    def test_bond_metal_is_critical(self):
        self.assertEqual(attribute_criticality("wire-bond-material"), "critical")

    def test_lead_finish_is_minor(self):
        self.assertEqual(attribute_criticality("lead-finish"), "minor")

    def test_unknown_attribute_rejected(self):
        with self.assertRaises(ValueError):
            validate_attribute("package-colour")

    def test_blank_attribute_rejected(self):
        with self.assertRaises(ValueError):
            validate_attribute("  ")

    def test_every_numeric_attribute_is_in_the_catalogue(self):
        for attribute in NUMERIC_ATTRIBUTES:
            self.assertIn(attribute, ATTRIBUTE_CRITICALITY)


class AttributeMatchTests(unittest.TestCase):
    def test_identical_material_matches(self):
        self.assertTrue(attribute_values_match("wire-bond-material", "gold", "gold"))

    def test_material_match_is_case_and_space_insensitive(self):
        self.assertTrue(
            attribute_values_match("passivation", "Silicon  Nitride", "silicon nitride")
        )

    def test_a_different_bond_metal_does_not_match(self):
        self.assertFalse(attribute_values_match("wire-bond-material", "gold", "copper"))

    def test_numeric_value_inside_the_band_matches(self):
        self.assertTrue(
            attribute_values_match("wire-bond-diameter-um", 25.0, 25.4)
        )

    def test_numeric_value_exactly_on_the_band_edge_matches(self):
        edge = 25.0 * (1.0 + NUMERIC_MATCH_TOLERANCE)
        self.assertTrue(attribute_values_match("wire-bond-diameter-um", 25.0, edge))

    def test_numeric_value_outside_the_band_does_not_match(self):
        self.assertFalse(
            attribute_values_match("wire-bond-diameter-um", 25.0, 30.0)
        )

    def test_numeric_attribute_given_a_string_rejected(self):
        with self.assertRaises(ValueError):
            attribute_values_match("wire-bond-diameter-um", 25.0, "twenty five")

    def test_material_attribute_given_a_number_rejected(self):
        with self.assertRaises(ValueError):
            attribute_values_match("wire-bond-material", "gold", 79)

    def test_non_positive_dimension_rejected(self):
        with self.assertRaises(ValueError):
            attribute_values_match("wire-bond-diameter-um", 25.0, 0.0)


class SamplePlanTests(unittest.TestCase):
    def test_population_floor_is_the_whole_root(self):
        plan = sample_plan(_groups())
        self.assertEqual(plan["total_population"], 100)
        self.assertEqual(plan["population_floor"], 10)

    def test_population_floor_rounds_up_off_a_square(self):
        groups = _groups()
        groups[0]["population"] = 51
        plan = sample_plan(groups)
        self.assertEqual(plan["population_floor"], 11)

    def test_per_date_code_minimum_can_dominate(self):
        groups = [
            {"date_code": "dc%d" % i, "population": 2, "samples_examined": 2,
             "observed": {}}
            for i in range(5)
        ]
        plan = sample_plan(groups)
        self.assertEqual(plan["required_total"], 10)

    def test_required_total_never_exceeds_the_population(self):
        groups = [
            {"date_code": "dc1", "population": 1, "samples_examined": 1,
             "observed": {}}
        ]
        plan = sample_plan(groups)
        self.assertEqual(plan["required_total"], 1)

    def test_minimum_per_date_code_must_be_whole(self):
        with self.assertRaises(ValueError):
            sample_plan(_groups(), 1.5)

    def test_empty_group_list_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan([])


class GroupValidationTests(unittest.TestCase):
    def test_duplicate_date_code_rejected(self):
        groups = _groups()
        groups[1]["date_code"] = "2431"
        with self.assertRaises(ValueError):
            validate_date_code_groups(groups)

    def test_more_sections_than_parts_rejected(self):
        groups = _groups()
        groups[0]["samples_examined"] = 51
        with self.assertRaises(ValueError):
            validate_date_code_groups(groups)

    def test_zero_population_rejected(self):
        groups = _groups()
        groups[0]["population"] = 0
        with self.assertRaises(ValueError):
            validate_date_code_groups(groups)

    def test_non_mapping_group_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code_groups(["2431"])

    def test_unknown_observed_attribute_rejected(self):
        groups = _groups()
        groups[0]["observed"]["package-colour"] = "black"
        with self.assertRaises(ValueError):
            validate_date_code_groups(groups)

    def test_empty_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline({})


class CoverageTests(unittest.TestCase):
    def test_a_complete_sample_set_is_complete(self):
        coverage = assess_sample_coverage(_groups())
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["findings"], [])

    def test_a_date_code_never_sectioned_is_a_finding(self):
        groups = _groups()
        groups[1]["samples_examined"] = 0
        coverage = assess_sample_coverage(groups)
        self.assertFalse(coverage["complete"])
        self.assertFalse(coverage["groups"][1]["met"])

    def test_a_thin_total_is_a_finding_of_its_own(self):
        groups = _groups()
        groups[0]["samples_examined"] = 3
        groups[1]["samples_examined"] = 3
        coverage = assess_sample_coverage(groups)
        self.assertEqual(coverage["total_shortfall"], 4)
        self.assertTrue(all(item["met"] for item in coverage["groups"]))

    def test_both_shortfalls_are_reported_together(self):
        groups = _groups()
        groups[0]["samples_examined"] = 0
        groups[1]["samples_examined"] = 1
        coverage = assess_sample_coverage(groups)
        self.assertEqual(len(coverage["findings"]), 3)


class BaselineComparisonTests(unittest.TestCase):
    def test_a_matching_section_reports_no_mismatch(self):
        result = compare_to_baseline(BASELINE, _observed())
        self.assertTrue(all(item["matches"] for item in result["attributes"]))

    def test_an_attribute_not_sectioned_is_named(self):
        observed = _observed()
        del observed["passivation"]
        result = compare_to_baseline(BASELINE, observed)
        self.assertEqual(result["not_examined"], ["passivation"])

    def test_an_attribute_absent_from_the_baseline_is_rejected(self):
        baseline = dict(BASELINE)
        del baseline["lead-finish"]
        with self.assertRaises(ValueError):
            compare_to_baseline(baseline, _observed())

    def test_a_mismatch_carries_its_criticality(self):
        result = compare_to_baseline(
            BASELINE, _observed(**{"wire-bond-material": "copper"})
        )
        bad = [item for item in result["attributes"] if not item["matches"]]
        self.assertEqual(bad[0]["criticality"], "critical")

    def test_non_mapping_observation_rejected(self):
        with self.assertRaises(ValueError):
            compare_to_baseline(BASELINE, ["gold"])


class ConsistencyTests(unittest.TestCase):
    def test_one_sectioned_group_is_not_comparable(self):
        groups = _groups()
        groups[1]["observed"] = {}
        result = cross_group_consistency(groups)
        self.assertFalse(result["comparable"])

    def test_agreeing_groups_report_no_difference(self):
        result = cross_group_consistency(_groups())
        self.assertTrue(result["comparable"])
        self.assertEqual(result["differences"], [])

    def test_a_changed_bond_metal_between_date_codes_is_named(self):
        groups = _groups()
        groups[1]["observed"]["wire-bond-material"] = "copper"
        result = cross_group_consistency(groups)
        self.assertEqual(result["differences"][0]["attribute"], "wire-bond-material")
        self.assertEqual(result["differences"][0]["date_codes"], ["2431", "2508"])

    def test_a_dimension_inside_the_band_is_not_a_difference(self):
        groups = _groups()
        groups[1]["observed"]["wire-bond-diameter-um"] = 25.8
        result = cross_group_consistency(groups)
        self.assertEqual(result["differences"], [])

    def test_every_differing_attribute_is_named(self):
        groups = _groups()
        groups[1]["observed"]["wire-bond-material"] = "copper"
        groups[1]["observed"]["lead-finish"] = "pure tin"
        result = cross_group_consistency(groups)
        self.assertEqual(len(result["differences"]), 2)


class ConformanceIndexTests(unittest.TestCase):
    def test_all_matching_gives_a_unit_index(self):
        records = [{"weight": 1.0, "matches": True}, {"weight": 0.2, "matches": True}]
        self.assertAlmostEqual(conformance_index(records), 1.0, places=9)

    def test_index_lands_exactly_on_the_floor(self):
        records = [{"weight": 0.9, "matches": True}, {"weight": 0.1, "matches": False}]
        self.assertAlmostEqual(conformance_index(records), CONFORMANCE_FLOOR, places=9)

    def test_a_critical_mismatch_moves_the_index_further(self):
        heavy = conformance_index(
            [{"weight": 1.0, "matches": False}, {"weight": 1.0, "matches": True}]
        )
        light = conformance_index(
            [{"weight": 0.2, "matches": False}, {"weight": 1.0, "matches": True}]
        )
        self.assertLess(heavy, light)

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            conformance_index([])

    def test_record_without_a_weight_rejected(self):
        with self.assertRaises(ValueError):
            conformance_index([{"matches": True}])


class AnalysisTests(unittest.TestCase):
    def test_a_clean_analysis_conforms(self):
        result = assess_constructional_analysis(_case())
        self.assertEqual(result["verdict"], CONSTRUCTION_CONFORMS)
        self.assertAlmostEqual(result["conformance_index"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_critical_deviation_blocks_the_verdict(self):
        case = _case()
        case["date_code_groups"][1]["observed"]["wire-bond-material"] = "copper"
        result = assess_constructional_analysis(case)
        self.assertEqual(result["verdict"], CONSTRUCTION_DEVIATION)
        self.assertTrue(result["blocking_deviations"])

    def test_a_thin_sample_set_leaves_the_analysis_incomplete(self):
        case = _case()
        case["date_code_groups"][1]["samples_examined"] = 0
        result = assess_constructional_analysis(case)
        self.assertEqual(result["verdict"], CONSTRUCTION_ANALYSIS_INCOMPLETE)

    def test_a_deviation_outranks_a_thin_sample_set(self):
        case = _case()
        case["date_code_groups"][1]["samples_examined"] = 0
        case["date_code_groups"][1]["observed"]["die-attach"] = "solder"
        result = assess_constructional_analysis(case)
        self.assertEqual(result["verdict"], CONSTRUCTION_DEVIATION)

    def test_an_attribute_no_section_reached_leaves_it_incomplete(self):
        case = _case()
        for group in case["date_code_groups"]:
            del group["observed"]["passivation"]
        result = assess_constructional_analysis(case)
        self.assertEqual(result["attributes_never_examined"], ["passivation"])
        self.assertEqual(result["verdict"], CONSTRUCTION_ANALYSIS_INCOMPLETE)

    def test_an_attribute_reached_by_one_section_is_not_unexamined(self):
        case = _case()
        del case["date_code_groups"][0]["observed"]["passivation"]
        result = assess_constructional_analysis(case)
        self.assertEqual(result["attributes_never_examined"], [])

    def test_minor_deviations_can_pull_the_index_under_the_floor(self):
        case = _case(
            baseline={"lead-finish": "tin-lead", "die-dimensions-mm": 3.0},
            date_code_groups=[
                {
                    "date_code": "2431",
                    "population": 50,
                    "samples_examined": 5,
                    "observed": {"lead-finish": "pure tin", "die-dimensions-mm": 3.0},
                },
                {
                    "date_code": "2508",
                    "population": 50,
                    "samples_examined": 5,
                    "observed": {"lead-finish": "tin-lead", "die-dimensions-mm": 3.0},
                },
            ],
        )
        result = assess_constructional_analysis(case)
        self.assertLess(result["conformance_index"], CONFORMANCE_FLOOR)
        self.assertEqual(result["verdict"], CONSTRUCTION_DEVIATION)

    def test_a_group_with_no_observation_at_all_is_a_finding(self):
        case = _case()
        case["date_code_groups"][1]["observed"] = {}
        result = assess_constructional_analysis(case)
        self.assertTrue(any("2508" in item for item in result["findings"]))

    def test_no_observation_anywhere_grades_nothing(self):
        case = _case()
        for group in case["date_code_groups"]:
            group["observed"] = {}
        result = assess_constructional_analysis(case)
        self.assertEqual(result["verdict"], CONSTRUCTION_ANALYSIS_INCOMPLETE)
        self.assertEqual(result["attributes"], [])

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_constructional_analysis(_case(part_number="  "))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_constructional_analysis(["EX-2210-C3"])

    def test_the_fixture_is_not_mutated_between_runs(self):
        case = _case()
        snapshot = copy.deepcopy(case)
        assess_constructional_analysis(case)
        self.assertEqual(case, snapshot)


if __name__ == "__main__":
    unittest.main()
