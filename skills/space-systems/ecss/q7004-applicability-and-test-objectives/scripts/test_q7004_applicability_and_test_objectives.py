#!/usr/bin/env python3
"""Contract test for the thermal test applicability decision (offline)."""

import copy
import unittest

from q7004_applicability_and_test_objectives_logic import (
    ACCEPTANCE_VERIFICATION,
    DEFAULT_APPLICABILITY_POLICY,
    HERITAGE_LEVELS,
    ITEM_CATEGORIES,
    NO_NEW_TEST,
    PROGRAMME_PHASES,
    QUALIFICATION,
    SCREENING,
    THERMAL_CYCLING,
    THERMAL_VACUUM,
    applicable_test_types,
    assess_applicability,
    campaign_sizing,
    cycling_is_applicable,
    heritage_shortfalls,
    predicted_span_k,
    select_objective,
    vacuum_is_applicable,
    validate_applicability_policy,
)

DEVELOPMENT_CASE = {
    "item_category": "material",
    "programme_phase": "development",
    "heritage": "none",
    "pressure_environment": "vacuum",
    "operating_pressure_pa": 1.0e-4,
    "predicted_min_k": 233.15,
    "predicted_max_k": 353.15,
}

QUALIFICATION_CASE = {
    "item_category": "assembly",
    "programme_phase": "qualification",
    "heritage": "similar-item",
    "pressure_environment": "vacuum-and-ambient",
    "operating_pressure_pa": 1.0e-3,
    "predicted_min_k": 213.15,
    "predicted_max_k": 373.15,
}

HERITAGE_CASE = {
    "item_category": "mechanical-part",
    "programme_phase": "qualification",
    "heritage": "identical-qualified",
    "pressure_environment": "vacuum",
    "operating_pressure_pa": 1.0e-5,
    "predicted_min_k": 233.15,
    "predicted_max_k": 353.15,
    "qualified_min_k": 223.15,
    "qualified_max_k": 363.15,
    "qualified_cycles": 200,
    "same_process": True,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_applicability_policy(DEFAULT_APPLICABILITY_POLICY),
            DEFAULT_APPLICABILITY_POLICY,
        )

    def test_policy_sizes_every_tested_objective(self):
        for objective in (SCREENING, QUALIFICATION, ACCEPTANCE_VERIFICATION):
            self.assertIn(objective, DEFAULT_APPLICABILITY_POLICY["specimen_count"])
            self.assertIn(objective, DEFAULT_APPLICABILITY_POLICY["cycle_count"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_applicability_policy("default")

    def test_policy_missing_an_objective_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        del broken["cycle_count"][SCREENING]
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_policy_with_zero_specimen_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["specimen_count"][QUALIFICATION] = 0
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_policy_with_negative_threshold_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["cycling_delta_t_threshold_k"] = -5.0
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_policy_qualifying_on_fewer_cycles_than_screening_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["cycle_count"][QUALIFICATION] = 2
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)


class PredictedSpanTests(unittest.TestCase):
    def test_span_is_the_difference_of_the_extremes(self):
        self.assertAlmostEqual(predicted_span_k(233.15, 353.15), 120.0, places=9)

    def test_equal_extremes_give_a_zero_span(self):
        self.assertAlmostEqual(predicted_span_k(300.0, 300.0), 0.0, places=9)

    def test_inverted_extremes_rejected(self):
        with self.assertRaises(ValueError):
            predicted_span_k(353.15, 233.15)

    def test_non_absolute_temperature_rejected(self):
        with self.assertRaises(ValueError):
            predicted_span_k(-10.0, 353.15)

    def test_non_numeric_extreme_rejected(self):
        with self.assertRaises(ValueError):
            predicted_span_k("233 K", 353.15)


class CyclingDriverTests(unittest.TestCase):
    def test_a_wide_span_drives_a_cycling_run(self):
        self.assertTrue(cycling_is_applicable(120.0))

    def test_a_narrow_span_drives_no_cycling_run(self):
        self.assertFalse(cycling_is_applicable(4.0))

    def test_a_span_exactly_on_the_threshold_drives_a_cycling_run(self):
        threshold = DEFAULT_APPLICABILITY_POLICY["cycling_delta_t_threshold_k"]
        span = predicted_span_k(280.0, 280.0 + threshold)
        self.assertTrue(cycling_is_applicable(span))

    def test_negative_span_rejected(self):
        with self.assertRaises(ValueError):
            cycling_is_applicable(-1.0)


class VacuumDriverTests(unittest.TestCase):
    def test_an_operating_vacuum_drives_a_vacuum_run(self):
        self.assertTrue(vacuum_is_applicable("vacuum", 1.0e-4))

    def test_ambient_pressure_operation_drives_no_vacuum_run(self):
        self.assertFalse(vacuum_is_applicable("ambient-pressure", 1.0e5))

    def test_a_vacuum_sensitive_mechanism_drives_a_run_at_ambient_pressure(self):
        self.assertTrue(
            vacuum_is_applicable("ambient-pressure", 1.0e5, vacuum_sensitive=True)
        )

    def test_a_pressure_above_the_threshold_drives_no_vacuum_run(self):
        self.assertFalse(vacuum_is_applicable("vacuum-and-ambient", 5.0e4))

    def test_unknown_pressure_environment_rejected(self):
        with self.assertRaises(ValueError):
            vacuum_is_applicable("outer-space-ish", 1.0e-4)

    def test_non_boolean_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            vacuum_is_applicable("vacuum", 1.0e-4, vacuum_sensitive="yes")


class TestTypeSelectionTests(unittest.TestCase):
    def test_a_cycling_and_vacuum_case_drives_both_runs(self):
        self.assertEqual(
            applicable_test_types(DEVELOPMENT_CASE),
            (THERMAL_CYCLING, THERMAL_VACUUM),
        )

    def test_an_ambient_pressure_case_drives_cycling_only(self):
        case = _case(
            DEVELOPMENT_CASE,
            pressure_environment="ambient-pressure",
            operating_pressure_pa=1.0e5,
        )
        self.assertEqual(applicable_test_types(case), (THERMAL_CYCLING,))

    def test_a_narrow_span_vacuum_case_drives_the_vacuum_run_only(self):
        case = _case(DEVELOPMENT_CASE, predicted_min_k=295.0, predicted_max_k=300.0)
        self.assertEqual(applicable_test_types(case), (THERMAL_VACUUM,))

    def test_a_case_with_no_driver_returns_no_test_types(self):
        case = _case(
            DEVELOPMENT_CASE,
            predicted_min_k=295.0,
            predicted_max_k=300.0,
            pressure_environment="ambient-pressure",
            operating_pressure_pa=1.0e5,
        )
        self.assertEqual(applicable_test_types(case), ())

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            applicable_test_types("a bracket")


class HeritageTests(unittest.TestCase):
    def test_a_covering_heritage_claim_has_no_shortfalls(self):
        self.assertEqual(heritage_shortfalls(HERITAGE_CASE), ())

    def test_a_similar_item_is_not_an_identical_item(self):
        shortfalls = heritage_shortfalls(QUALIFICATION_CASE)
        self.assertEqual(len(shortfalls), 1)
        self.assertIn("identical", shortfalls[0])

    def test_a_narrow_qualified_cold_extreme_is_a_shortfall(self):
        case = _case(HERITAGE_CASE, qualified_min_k=232.0)
        self.assertTrue(any("cold extreme" in s for s in heritage_shortfalls(case)))

    def test_a_narrow_qualified_hot_extreme_is_a_shortfall(self):
        case = _case(HERITAGE_CASE, qualified_max_k=354.0)
        self.assertTrue(any("hot extreme" in s for s in heritage_shortfalls(case)))

    def test_a_qualified_envelope_exactly_on_the_margin_is_covering(self):
        margin = DEFAULT_APPLICABILITY_POLICY["heritage_envelope_margin_k"]
        case = _case(
            HERITAGE_CASE,
            qualified_min_k=HERITAGE_CASE["predicted_min_k"] - margin,
            qualified_max_k=HERITAGE_CASE["predicted_max_k"] + margin,
        )
        self.assertEqual(heritage_shortfalls(case), ())

    def test_too_few_qualified_cycles_is_a_shortfall(self):
        case = _case(HERITAGE_CASE, qualified_cycles=12)
        self.assertTrue(any("cycles" in s for s in heritage_shortfalls(case)))

    def test_a_missing_qualified_cycle_count_is_a_shortfall(self):
        case = _case(HERITAGE_CASE)
        del case["qualified_cycles"]
        self.assertTrue(any("cycle count" in s for s in heritage_shortfalls(case)))

    def test_a_changed_process_is_a_shortfall(self):
        case = _case(HERITAGE_CASE, same_process=False)
        self.assertTrue(any("process" in s for s in heritage_shortfalls(case)))

    def test_a_non_integer_qualified_cycle_count_rejected(self):
        case = _case(HERITAGE_CASE, qualified_cycles=200.0)
        with self.assertRaises(ValueError):
            heritage_shortfalls(case)

    def test_unknown_heritage_level_rejected(self):
        with self.assertRaises(ValueError):
            heritage_shortfalls(_case(HERITAGE_CASE, heritage="looks-similar"))


class ObjectiveSelectionTests(unittest.TestCase):
    def test_development_phase_gives_a_screening_objective(self):
        self.assertEqual(select_objective(DEVELOPMENT_CASE)["objective"], SCREENING)

    def test_pre_development_phase_also_gives_a_screening_objective(self):
        case = _case(DEVELOPMENT_CASE, programme_phase="pre-development")
        self.assertEqual(select_objective(case)["objective"], SCREENING)

    def test_qualification_phase_gives_a_qualification_objective(self):
        self.assertEqual(
            select_objective(QUALIFICATION_CASE)["objective"], QUALIFICATION
        )

    def test_acceptance_phase_gives_an_acceptance_objective(self):
        case = _case(QUALIFICATION_CASE, programme_phase="acceptance")
        self.assertEqual(select_objective(case)["objective"], ACCEPTANCE_VERIFICATION)

    def test_a_covering_heritage_claim_beats_the_programme_phase(self):
        decision = select_objective(HERITAGE_CASE)
        self.assertEqual(decision["objective"], NO_NEW_TEST)
        self.assertEqual(decision["heritage_shortfalls"], ())

    def test_unknown_programme_phase_rejected(self):
        with self.assertRaises(ValueError):
            select_objective(_case(DEVELOPMENT_CASE, programme_phase="late"))


class SizingTests(unittest.TestCase):
    def test_qualification_needs_more_specimens_than_screening(self):
        self.assertGreater(
            campaign_sizing(QUALIFICATION)["specimen_count"],
            campaign_sizing(SCREENING)["specimen_count"],
        )

    def test_qualification_needs_more_cycles_than_screening(self):
        self.assertGreater(
            campaign_sizing(QUALIFICATION)["cycle_count"],
            campaign_sizing(SCREENING)["cycle_count"],
        )

    def test_no_new_test_is_sized_at_nothing(self):
        self.assertEqual(
            campaign_sizing(NO_NEW_TEST), {"specimen_count": 0, "cycle_count": 0}
        )

    def test_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            campaign_sizing("smoke-test")


class AssessmentTests(unittest.TestCase):
    def test_development_case_is_a_screening_campaign_on_both_run_types(self):
        result = assess_applicability(DEVELOPMENT_CASE)
        self.assertEqual(result["objective"], SCREENING)
        self.assertEqual(result["test_types"], (THERMAL_CYCLING, THERMAL_VACUUM))
        self.assertEqual(result["specimen_count"], 3)
        self.assertEqual(result["cycle_count"], 10)

    def test_a_screening_campaign_carries_the_qualifies_nothing_duty(self):
        result = assess_applicability(DEVELOPMENT_CASE)
        self.assertTrue(any("qualifies nothing" in duty for duty in result["duties"]))

    def test_qualification_case_is_sized_for_qualification(self):
        result = assess_applicability(QUALIFICATION_CASE)
        self.assertEqual(result["objective"], QUALIFICATION)
        self.assertEqual(result["specimen_count"], 5)
        self.assertEqual(result["cycle_count"], 100)
        self.assertAlmostEqual(result["predicted_span_k"], 160.0, places=9)

    def test_heritage_case_needs_no_new_test_but_owes_a_justification(self):
        result = assess_applicability(HERITAGE_CASE)
        self.assertEqual(result["objective"], NO_NEW_TEST)
        self.assertEqual(result["specimen_count"], 0)
        self.assertTrue(any("heritage justification" in d for d in result["duties"]))

    def test_a_case_with_no_driver_is_closed_with_a_finding(self):
        case = _case(
            DEVELOPMENT_CASE,
            predicted_min_k=295.0,
            predicted_max_k=300.0,
            pressure_environment="ambient-pressure",
            operating_pressure_pa=1.0e5,
        )
        result = assess_applicability(case)
        self.assertEqual(result["objective"], NO_NEW_TEST)
        self.assertEqual(result["test_types"], ())
        self.assertTrue(any("neither" in f for f in result["findings"]))

    def test_every_item_category_is_accepted(self):
        for category in ITEM_CATEGORIES:
            result = assess_applicability(_case(DEVELOPMENT_CASE, item_category=category))
            self.assertEqual(result["item_category"], category)

    def test_every_programme_phase_resolves_to_an_objective(self):
        for phase in PROGRAMME_PHASES:
            result = assess_applicability(_case(DEVELOPMENT_CASE, programme_phase=phase))
            self.assertIn(result["objective"], (SCREENING, QUALIFICATION, ACCEPTANCE_VERIFICATION))

    def test_every_heritage_level_is_accepted(self):
        for level in HERITAGE_LEVELS:
            case = _case(HERITAGE_CASE, heritage=level)
            self.assertIn("objective", assess_applicability(case))

    def test_unknown_item_category_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(_case(DEVELOPMENT_CASE, item_category="widget"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability("a coupon")

    def test_a_qualification_vacuum_case_carries_the_shared_specimen_duty(self):
        result = assess_applicability(QUALIFICATION_CASE)
        self.assertTrue(any("same specimens" in duty for duty in result["duties"]))


if __name__ == "__main__":
    unittest.main()
