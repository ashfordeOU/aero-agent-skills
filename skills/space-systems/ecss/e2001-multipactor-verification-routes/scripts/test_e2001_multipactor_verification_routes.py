"""Contract test for the ECSS-E-ST-20-01C clause 4.5 route-selection leaf.

Offline, deterministic, stdlib unittest. Run: python3 test_e2001_multipactor_verification_routes.py
"""

import unittest

from e2001_multipactor_verification_routes_logic import (
    ANALYSIS_SUPPORT_STATES,
    DEFAULT_ANALYSIS_ONLY_EXTRA_DB,
    GLOBAL_DETECTION_METHODS,
    LOCAL_DETECTION_METHODS,
    MARGIN_TOLERANCE_DB,
    ROUTES,
    build_verification_route_plan,
    check_detection_methods,
    facility_can_reach,
    margin_clears,
    normalize_route_inputs,
    select_verification_route,
    similarity_assessment,
    test_power_w,
    within_limit,
)


def inputs(**overrides):
    """A validated-method case with a comfortable margin, perturbed per test."""
    base = {
        "analysis_support": "validated-method",
        "analysis_margin_db": 12.0,
        "required_margin_db": 6.0,
        "nominal_power_w": 100.0,
        "critical": False,
        "facility_max_power_w": 5000.0,
        "detection_methods": ["forward-reverse-power-nulling", "electron-probe"],
    }
    base.update(overrides)
    return base


def unit(**overrides):
    """A hardware description usable as similarity candidate or reference."""
    base = {
        "gap_mm": 1.0,
        "frequency_ghz": 12.0,
        "power_w": 100.0,
        "surface_treatment": "silver-plated-aluminium",
        "manufacturing_process": "milled-and-brazed",
    }
    base.update(overrides)
    return base


class DemonstrationLevelTests(unittest.TestCase):
    def test_zero_margin_demonstrates_at_nominal(self):
        self.assertAlmostEqual(test_power_w(100.0, 0.0), 100.0)

    def test_three_decibels_is_about_double(self):
        self.assertAlmostEqual(test_power_w(100.0, 3.0), 199.5262, places=4)

    def test_six_decibels_is_about_four_times(self):
        self.assertAlmostEqual(test_power_w(100.0, 6.0), 398.1072, places=4)

    def test_zero_nominal_power_rejected(self):
        with self.assertRaises(ValueError):
            test_power_w(0.0, 6.0)

    def test_non_finite_margin_rejected(self):
        with self.assertRaises(ValueError):
            test_power_w(100.0, float("inf"))


class MarginClearanceTests(unittest.TestCase):
    def test_margin_equal_to_requirement_clears_it(self):
        self.assertTrue(margin_clears(6.0, 6.0))

    def test_representation_error_is_absorbed(self):
        self.assertTrue(margin_clears(6.0 - MARGIN_TOLERANCE_DB / 2.0, 6.0))

    def test_real_shortfall_does_not_clear(self):
        self.assertFalse(margin_clears(5.5, 6.0))

    def test_extra_raises_the_bar(self):
        self.assertFalse(margin_clears(8.0, 6.0, 3.0))
        self.assertTrue(margin_clears(9.0, 6.0, 3.0))

    def test_negative_extra_rejected(self):
        with self.assertRaises(ValueError):
            margin_clears(9.0, 6.0, -1.0)


class CapabilityTests(unittest.TestCase):
    def test_level_below_the_limit_is_reachable(self):
        self.assertTrue(within_limit(100.0, 200.0))

    def test_level_on_the_limit_is_reachable(self):
        self.assertTrue(within_limit(200.0, 200.0))

    def test_level_above_the_limit_is_not(self):
        self.assertFalse(within_limit(300.0, 200.0))

    def test_equal_levels_reached_by_different_arithmetic_still_tie(self):
        self.assertTrue(within_limit(test_power_w(100.0, 6.0), test_power_w(50.0, 6.0) * 2.0))

    def test_facility_wrapper_agrees_with_the_limit_check(self):
        self.assertTrue(facility_can_reach(398.0, 400.0))
        self.assertFalse(facility_can_reach(401.0, 400.0))

    def test_zero_facility_capability_rejected(self):
        with self.assertRaises(ValueError):
            facility_can_reach(100.0, 0.0)


class DetectionTests(unittest.TestCase):
    def test_one_global_and_one_local_is_adequate(self):
        report = check_detection_methods(
            ["third-harmonic-detection", "optical-emission-monitoring"]
        )
        self.assertTrue(report["adequate"])
        self.assertEqual(report["global_count"], 1)
        self.assertEqual(report["local_count"], 1)

    def test_two_global_methods_lack_a_local_observer(self):
        report = check_detection_methods(
            ["third-harmonic-detection", "forward-reverse-power-nulling"]
        )
        self.assertEqual(report["findings"], ["no-local-detection-method"])

    def test_two_local_methods_lack_a_global_observer(self):
        report = check_detection_methods(["electron-probe", "close-electron-detection"])
        self.assertEqual(report["findings"], ["no-global-detection-method"])

    def test_single_method_is_never_enough(self):
        report = check_detection_methods(["electron-probe"])
        self.assertIn("fewer-than-two-detection-methods", report["findings"])

    def test_repeated_method_does_not_count_twice(self):
        report = check_detection_methods(["electron-probe", "electron-probe"])
        self.assertEqual(report["methods"], ["electron-probe"])
        self.assertIn("fewer-than-two-detection-methods", report["findings"])

    def test_empty_set_raises_every_finding(self):
        report = check_detection_methods([])
        self.assertEqual(len(report["findings"]), 3)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            check_detection_methods(["listening-carefully"])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            check_detection_methods("electron-probe")

    def test_the_two_method_families_do_not_overlap(self):
        self.assertFalse(set(GLOBAL_DETECTION_METHODS) & set(LOCAL_DETECTION_METHODS))


class SimilarityTests(unittest.TestCase):
    def test_identical_qualified_unit_is_eligible(self):
        report = similarity_assessment(unit(), unit(qualified=True))
        self.assertTrue(report["eligible"])
        self.assertAlmostEqual(report["gap_delta_fraction"], 0.0)
        self.assertAlmostEqual(report["power_ratio"], 1.0)

    def test_small_gap_delta_stays_eligible(self):
        report = similarity_assessment(unit(gap_mm=1.04), unit(qualified=True))
        self.assertTrue(report["eligible"])

    def test_large_gap_delta_breaks_similarity(self):
        report = similarity_assessment(unit(gap_mm=1.2), unit(qualified=True))
        self.assertIn("gap-geometry-delta-too-large", report["shortfalls"])

    def test_large_frequency_delta_breaks_similarity(self):
        report = similarity_assessment(unit(frequency_ghz=14.0), unit(qualified=True))
        self.assertIn("frequency-delta-too-large", report["shortfalls"])

    def test_running_harder_than_the_reference_breaks_similarity(self):
        report = similarity_assessment(unit(power_w=150.0), unit(qualified=True))
        self.assertIn("candidate-run-harder-than-reference", report["shortfalls"])
        self.assertAlmostEqual(report["power_ratio"], 1.5)

    def test_equal_power_is_still_eligible(self):
        report = similarity_assessment(unit(power_w=100.0), unit(qualified=True))
        self.assertTrue(report["eligible"])

    def test_different_surface_treatment_breaks_similarity(self):
        report = similarity_assessment(
            unit(surface_treatment="alodine-aluminium"), unit(qualified=True)
        )
        self.assertIn("surface-treatment-differs", report["shortfalls"])

    def test_different_manufacturing_process_breaks_similarity(self):
        report = similarity_assessment(
            unit(manufacturing_process="additively-built"), unit(qualified=True)
        )
        self.assertIn("manufacturing-process-differs", report["shortfalls"])

    def test_unqualified_reference_breaks_similarity(self):
        report = similarity_assessment(unit(), unit())
        self.assertIn("reference-not-qualified", report["shortfalls"])

    def test_tighter_tolerance_can_be_imposed(self):
        report = similarity_assessment(
            unit(gap_mm=1.04),
            unit(qualified=True),
            {"max_gap_delta_fraction": 0.01},
        )
        self.assertFalse(report["eligible"])

    def test_unknown_tolerance_key_rejected(self):
        with self.assertRaises(ValueError):
            similarity_assessment(unit(), unit(qualified=True), {"max_mass_delta": 0.1})

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            similarity_assessment(["gap_mm", 1.0], unit(qualified=True))

    def test_missing_gap_rejected(self):
        candidate = unit()
        del candidate["gap_mm"]
        with self.assertRaises(ValueError):
            similarity_assessment(candidate, unit(qualified=True))

    def test_negative_reference_power_rejected(self):
        with self.assertRaises(ValueError):
            similarity_assessment(unit(), unit(qualified=True, power_w=-10.0))


class NormalizeInputsTests(unittest.TestCase):
    def test_defaults_are_filled(self):
        record = normalize_route_inputs(
            {
                "analysis_support": "validated-method",
                "required_margin_db": 6.0,
                "nominal_power_w": 100.0,
            }
        )
        self.assertAlmostEqual(
            record["analysis_only_extra_db"], DEFAULT_ANALYSIS_ONLY_EXTRA_DB
        )
        self.assertFalse(record["critical"])
        self.assertIsNone(record["facility_max_power_w"])
        self.assertEqual(record["detection_methods"], [])
        self.assertIsNone(record["similarity"])

    def test_every_support_state_normalizes(self):
        for state in ANALYSIS_SUPPORT_STATES:
            record = normalize_route_inputs(inputs(analysis_support=state))
            self.assertEqual(record["analysis_support"], state)

    def test_unknown_support_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(analysis_support="expert-judgement"))

    def test_missing_required_margin_rejected(self):
        raw = inputs()
        del raw["required_margin_db"]
        with self.assertRaises(ValueError):
            normalize_route_inputs(raw)

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(required_margin_db=-1.0))

    def test_missing_nominal_power_rejected(self):
        raw = inputs()
        del raw["nominal_power_w"]
        with self.assertRaises(ValueError):
            normalize_route_inputs(raw)

    def test_zero_nominal_power_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(nominal_power_w=0.0))

    def test_negative_analysis_only_extra_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(analysis_only_extra_db=-2.0))

    def test_zero_facility_capability_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(facility_max_power_w=0.0))

    def test_detection_methods_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(detection_methods="electron-probe"))

    def test_similarity_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs(inputs(similarity=["candidate"]))

    def test_non_mapping_inputs_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route_inputs("validated-method")


class RouteSelectionTests(unittest.TestCase):
    def test_every_selected_route_is_a_permitted_one(self):
        for state in ANALYSIS_SUPPORT_STATES:
            decision = select_verification_route(inputs(analysis_support=state))
            self.assertIn(decision["route"], ROUTES)

    def test_validated_method_with_room_to_spare_stands_alone(self):
        decision = select_verification_route(inputs())
        self.assertEqual(decision["route"], "analysis-only")

    def test_margin_exactly_on_the_analysis_only_bar_stands_alone(self):
        decision = select_verification_route(inputs(analysis_margin_db=9.0))
        self.assertEqual(decision["route"], "analysis-only")

    def test_margin_only_meeting_the_requirement_needs_a_campaign(self):
        decision = select_verification_route(inputs(analysis_margin_db=6.0))
        self.assertEqual(decision["route"], "analysis-and-test")

    def test_critical_equipment_never_rides_on_analysis_alone(self):
        decision = select_verification_route(inputs(critical=True))
        self.assertEqual(decision["route"], "analysis-and-test")
        self.assertIn("critical", decision["rationale"])

    def test_engineering_estimate_cannot_stand_alone(self):
        decision = select_verification_route(
            inputs(analysis_support="engineering-estimate")
        )
        self.assertEqual(decision["route"], "analysis-and-test")

    def test_no_applicable_method_forces_the_campaign_route(self):
        decision = select_verification_route(
            inputs(analysis_support="no-applicable-method", analysis_margin_db=30.0)
        )
        self.assertEqual(decision["route"], "test-only")

    def test_analysis_below_the_requirement_is_a_finding(self):
        decision = select_verification_route(inputs(analysis_margin_db=4.0))
        self.assertEqual(decision["route"], "test-only")
        self.assertIn("analysis-below-required-margin", decision["findings"])

    def test_eligible_similarity_wins_over_the_analysis_route(self):
        decision = select_verification_route(
            inputs(
                similarity={"candidate": unit(), "reference": unit(qualified=True)},
                analysis_support="no-applicable-method",
            )
        )
        self.assertEqual(decision["route"], "similarity")
        self.assertTrue(decision["similarity"]["eligible"])

    def test_ineligible_similarity_falls_through(self):
        decision = select_verification_route(
            inputs(similarity={"candidate": unit(), "reference": unit()})
        )
        self.assertEqual(decision["route"], "analysis-only")
        self.assertFalse(decision["similarity"]["eligible"])


class RoutePlanTests(unittest.TestCase):
    def test_analysis_only_plan_asks_for_no_demonstration_level(self):
        plan = build_verification_route_plan(inputs())
        self.assertEqual(plan["route"], "analysis-only")
        self.assertIsNone(plan["required_test_power_w"])
        self.assertIsNone(plan["detection"])
        self.assertTrue(plan["executable"])
        self.assertIn("record-the-analysis-method-validation-evidence", plan["actions"])

    def test_campaign_plan_prices_the_demonstration_level(self):
        plan = build_verification_route_plan(inputs(critical=True))
        self.assertEqual(plan["route"], "analysis-and-test")
        self.assertAlmostEqual(plan["required_test_power_w"], 398.1072, places=4)
        self.assertTrue(plan["detection"]["adequate"])
        self.assertTrue(plan["executable"])

    def test_facility_exactly_at_the_demonstration_level_is_accepted(self):
        plan = build_verification_route_plan(
            inputs(critical=True, facility_max_power_w=test_power_w(100.0, 6.0))
        )
        self.assertNotIn("facility-power-shortfall", plan["findings"])
        self.assertTrue(plan["executable"])

    def test_facility_short_of_the_level_is_flagged(self):
        plan = build_verification_route_plan(
            inputs(critical=True, facility_max_power_w=200.0)
        )
        self.assertIn("facility-power-shortfall", plan["findings"])
        self.assertIn(
            "use-a-dedicated-article-or-an-alternative-demonstration", plan["actions"]
        )
        self.assertFalse(plan["executable"])

    def test_undeclared_facility_is_flagged(self):
        raw = inputs(critical=True)
        del raw["facility_max_power_w"]
        plan = build_verification_route_plan(raw)
        self.assertIn("facility-capability-not-declared", plan["findings"])

    def test_single_detection_method_blocks_the_plan(self):
        plan = build_verification_route_plan(
            inputs(critical=True, detection_methods=["third-harmonic-detection"])
        )
        self.assertIn("fewer-than-two-detection-methods", plan["findings"])
        self.assertIn("no-local-detection-method", plan["findings"])
        self.assertIn("add-an-independent-detection-method", plan["actions"])
        self.assertFalse(plan["executable"])

    def test_similarity_plan_asks_for_the_justification_dossier(self):
        plan = build_verification_route_plan(
            inputs(similarity={"candidate": unit(), "reference": unit(qualified=True)})
        )
        self.assertEqual(plan["route"], "similarity")
        self.assertIsNone(plan["required_test_power_w"])
        self.assertEqual(plan["actions"], ["record-the-similarity-justification-dossier"])
        self.assertTrue(plan["executable"])

    def test_rejected_similarity_is_reported_without_blocking_the_route(self):
        plan = build_verification_route_plan(
            inputs(similarity={"candidate": unit(gap_mm=1.5), "reference": unit(qualified=True)})
        )
        self.assertEqual(plan["route"], "analysis-only")
        self.assertIn("gap-geometry-delta-too-large", plan["similarity_shortfalls"])
        self.assertTrue(plan["executable"])

    def test_analysis_shortfall_plan_is_not_executable_as_declared(self):
        plan = build_verification_route_plan(inputs(analysis_margin_db=2.0))
        self.assertEqual(plan["route"], "test-only")
        self.assertIn("analysis-below-required-margin", plan["findings"])
        self.assertFalse(plan["executable"])

    def test_campaign_route_always_carries_a_demonstration_action(self):
        for state in ("engineering-estimate", "no-applicable-method"):
            plan = build_verification_route_plan(inputs(analysis_support=state))
            self.assertIn("run-the-campaign-at-the-demonstration-level", plan["actions"])
            self.assertIsNotNone(plan["required_test_power_w"])


if __name__ == "__main__":
    unittest.main()
