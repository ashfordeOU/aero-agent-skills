#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multipactor-verification-plan-content.

Anchor: ECSS-E-ST-20-01C clause 4.2.2. Stdlib unittest, offline,
deterministic. Run: python3 test_e2001_multipactor_verification_plan_content.py
"""

import unittest

from e2001_multipactor_verification_plan_content_logic import (
    CONTENT_ITEMS,
    VACUUM_CEILING_MBAR,
    VERIFICATION_METHODS,
    assess_plan_content,
    audit_content_coverage,
    audit_item_entry,
    canonical_content_key,
    canonical_method,
    evaluate_content_entry,
    meets_threshold,
    required_fields_for_method,
    validate_detection_methods,
    validate_seeding_source,
)


def _entries(omit=(), states=None):
    states = states or {}
    return [
        {"key": key, "state": states.get(key, "detailed")}
        for key in CONTENT_ITEMS
        if key not in omit
    ]


def _test_item(**overrides):
    fields = {
        "test-power-level-dbm": 43.0,
        "dwell-duration-minutes": 30.0,
        "vacuum-pressure-mbar": 1.0e-6,
        "electron-seeding-source": "radioactive-source",
        "detection-methods": ["forward-reverse-power-nulling", "third-harmonic-detection"],
    }
    fields.update(overrides)
    return {"id": "wg-flange-01", "method": "multipactor-test", "fields": fields}


def _analysis_item(**overrides):
    fields = {
        "susceptibility-model": "parallel-plate-chart-fit",
        "secondary-electron-yield-source": "silver-yield-dataset-rev-c",
        "gap-geometry-source": "cad-model-b7",
        "analysis-margin-db": 8.0,
    }
    fields.update(overrides)
    return {"id": "iris-02", "method": "multipactor-analysis", "fields": fields}


def _similarity_item(**overrides):
    fields = {
        "reference-equipment-id": "omux-flight-model-3",
        "delta-justification": "identical gap and material, lower drive level",
        "heritage-evidence-ref": "qual-report-2024-118",
    }
    fields.update(overrides)
    return {"id": "coax-03", "method": "similarity", "fields": fields}


def _plan(**overrides):
    plan = {
        "content_entries": _entries(),
        "items": [_test_item(), _analysis_item(), _similarity_item()],
    }
    plan.update(overrides)
    return plan


class TestThresholdComparison(unittest.TestCase):
    def test_value_above_minimum_passes(self):
        self.assertTrue(meets_threshold(0.95, 0.9))

    def test_value_below_minimum_fails(self):
        self.assertFalse(meets_threshold(0.79, 0.8))

    def test_representation_error_at_the_boundary_is_absorbed(self):
        value = 0.7 + 0.1
        self.assertLess(value, 0.8)
        self.assertTrue(meets_threshold(value, 0.8))

    def test_exact_equality_passes(self):
        self.assertTrue(meets_threshold(1.0, 1.0))

    def test_non_numeric_value_raises(self):
        with self.assertRaises(ValueError):
            meets_threshold("0.9", 0.8)

    def test_non_numeric_minimum_raises(self):
        with self.assertRaises(ValueError):
            meets_threshold(0.9, None)


class TestContentKeys(unittest.TestCase):
    def test_catalogue_key_resolves_to_itself(self):
        self.assertEqual(
            canonical_content_key("multipactor-critical-item-list"),
            "multipactor-critical-item-list",
        )

    def test_alias_resolves_to_the_catalogue_key(self):
        self.assertEqual(
            canonical_content_key("critical-item-list"), "multipactor-critical-item-list"
        )

    def test_spaces_and_underscores_normalize(self):
        self.assertEqual(canonical_content_key("Pass Fail Criteria"), "pass-fail-criteria")
        self.assertEqual(canonical_content_key("pass_fail_criteria"), "pass-fail-criteria")

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            canonical_content_key("cover-page")

    def test_empty_key_raises(self):
        with self.assertRaises(ValueError):
            canonical_content_key("  ")

    def test_non_string_key_raises(self):
        with self.assertRaises(ValueError):
            canonical_content_key(7)

    def test_every_catalogue_key_carries_weight_and_purpose(self):
        for key, (weight, purpose) in CONTENT_ITEMS.items():
            self.assertGreater(weight, 0.0, key)
            self.assertTrue(purpose, key)


class TestContentEntries(unittest.TestCase):
    def test_detailed_entry_adds_content(self):
        result = evaluate_content_entry({"key": "pass-fail-criteria", "state": "detailed"})
        self.assertTrue(result["adds_content"])
        self.assertEqual(result["findings"], [])

    def test_state_defaults_to_detailed(self):
        self.assertTrue(evaluate_content_entry({"key": "pass-fail-criteria"})["adds_content"])

    def test_placeholder_entry_adds_nothing(self):
        result = evaluate_content_entry({"key": "pass-fail-criteria", "state": "placeholder"})
        self.assertFalse(result["adds_content"])
        self.assertEqual(len(result["findings"]), 1)

    def test_parent_cross_reference_is_not_an_addition(self):
        result = evaluate_content_entry(
            {"key": "non-conformance-route", "state": "parent-cross-reference"}
        )
        self.assertFalse(result["adds_content"])
        self.assertIn("parent verification plan", result["findings"][0])

    def test_to_be_defined_entry_adds_nothing(self):
        result = evaluate_content_entry(
            {"key": "verification-schedule-and-facility", "state": "to-be-defined"}
        )
        self.assertFalse(result["adds_content"])

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            evaluate_content_entry({"key": "pass-fail-criteria", "state": "nearly-written"})

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            evaluate_content_entry("pass-fail-criteria")

    def test_non_string_state_raises(self):
        with self.assertRaises(ValueError):
            evaluate_content_entry({"key": "pass-fail-criteria", "state": 1})


class TestContentCoverage(unittest.TestCase):
    def test_complete_plan_reaches_full_coverage(self):
        result = audit_content_coverage(_entries())
        self.assertAlmostEqual(result["fraction"], 1.0)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["findings"], [])

    def test_missing_addition_is_reported_and_weighted_out(self):
        result = audit_content_coverage(_entries(omit=("verification-schedule-and-facility",)))
        self.assertEqual(result["missing"], ["verification-schedule-and-facility"])
        expected = (result["total_weight"] - 0.7) / result["total_weight"]
        self.assertAlmostEqual(result["fraction"], expected)
        self.assertEqual(len(result["findings"]), 1)

    def test_name_only_entry_is_separated_from_present(self):
        result = audit_content_coverage(
            _entries(states={"non-conformance-route": "placeholder"})
        )
        self.assertEqual(result["name_only"], ["non-conformance-route"])
        self.assertNotIn("non-conformance-route", result["present"])
        self.assertLess(result["fraction"], 1.0)

    def test_heavier_addition_costs_more_coverage(self):
        light = audit_content_coverage(_entries(omit=("verification-schedule-and-facility",)))
        heavy = audit_content_coverage(_entries(omit=("multipactor-critical-item-list",)))
        self.assertLess(heavy["fraction"], light["fraction"])

    def test_duplicate_content_key_raises(self):
        entries = _entries() + [{"key": "pass-fail-criteria", "state": "detailed"}]
        with self.assertRaises(ValueError):
            audit_content_coverage(entries)

    def test_unknown_entry_reports_its_position(self):
        entries = _entries() + [{"key": "appendix-z"}]
        with self.assertRaises(ValueError) as caught:
            audit_content_coverage(entries)
        self.assertIn("content entry[", str(caught.exception))

    def test_non_list_entries_raise(self):
        with self.assertRaises(ValueError):
            audit_content_coverage({"key": "pass-fail-criteria"})

    def test_empty_plan_misses_every_addition(self):
        result = audit_content_coverage([])
        self.assertEqual(len(result["missing"]), len(CONTENT_ITEMS))
        self.assertAlmostEqual(result["fraction"], 0.0)


class TestMethodResolution(unittest.TestCase):
    def test_short_route_name_resolves(self):
        self.assertEqual(canonical_method("test"), "multipactor-test")
        self.assertEqual(canonical_method("analysis"), "multipactor-analysis")

    def test_heritage_alias_resolves_to_similarity(self):
        self.assertEqual(canonical_method("heritage-similarity"), "similarity")

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            canonical_method("engineering-judgement")

    def test_empty_route_raises(self):
        with self.assertRaises(ValueError):
            canonical_method("")

    def test_non_string_route_raises(self):
        with self.assertRaises(ValueError):
            canonical_method(None)

    def test_each_route_owes_distinct_fields(self):
        route_fields = {m: set(required_fields_for_method(m)) for m in VERIFICATION_METHODS}
        self.assertNotEqual(
            route_fields["multipactor-test"], route_fields["multipactor-analysis"]
        )
        self.assertIn("electron-seeding-source", route_fields["multipactor-test"])
        self.assertIn("delta-justification", route_fields["similarity"])


class TestSeedingAndDetection(unittest.TestCase):
    def test_recognized_seeding_source_resolves(self):
        self.assertEqual(validate_seeding_source("Electron-Gun"), "electron-gun")

    def test_unknown_seeding_source_raises(self):
        with self.assertRaises(ValueError):
            validate_seeding_source("ambient-electrons")

    def test_non_string_seeding_source_raises(self):
        with self.assertRaises(ValueError):
            validate_seeding_source(["electron-gun"])

    def test_mixed_detection_pair_has_no_finding(self):
        result = validate_detection_methods(
            ["forward-reverse-power-nulling", "electron-current-probe"]
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["scopes"], ["global", "local"])

    def test_single_detection_method_is_flagged(self):
        result = validate_detection_methods(["third-harmonic-detection"])
        self.assertEqual(len(result["findings"]), 1)

    def test_repeated_method_still_counts_once(self):
        result = validate_detection_methods(
            ["third-harmonic-detection", "third-harmonic-detection"]
        )
        self.assertEqual(result["methods"], ["third-harmonic-detection"])
        self.assertEqual(len(result["findings"]), 1)

    def test_two_local_methods_are_flagged_as_unmixed(self):
        result = validate_detection_methods(
            ["third-harmonic-detection", "electron-current-probe"]
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("local", result["findings"][0])

    def test_unknown_detection_method_raises(self):
        with self.assertRaises(ValueError):
            validate_detection_methods(["listening-carefully"])

    def test_non_list_detection_methods_raise(self):
        with self.assertRaises(ValueError):
            validate_detection_methods("third-harmonic-detection")


class TestItemAudit(unittest.TestCase):
    def test_complete_test_item_is_compliant(self):
        result = audit_item_entry(_test_item())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing_fields"], [])

    def test_complete_analysis_item_is_compliant(self):
        self.assertTrue(audit_item_entry(_analysis_item())["compliant"])

    def test_complete_similarity_item_is_compliant(self):
        self.assertTrue(audit_item_entry(_similarity_item())["compliant"])

    def test_missing_seeding_source_is_a_finding(self):
        item = _test_item()
        del item["fields"]["electron-seeding-source"]
        result = audit_item_entry(item)
        self.assertIn("electron-seeding-source", result["missing_fields"])
        self.assertFalse(result["compliant"])

    def test_none_valued_field_counts_as_missing(self):
        result = audit_item_entry(_test_item(**{"dwell-duration-minutes": None}))
        self.assertIn("dwell-duration-minutes", result["missing_fields"])

    def test_pressure_above_the_vacuum_ceiling_is_a_finding(self):
        result = audit_item_entry(
            _test_item(**{"vacuum-pressure-mbar": VACUUM_CEILING_MBAR * 10.0})
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("gas breakdown" in f for f in result["findings"]))

    def test_pressure_exactly_at_the_ceiling_is_accepted(self):
        result = audit_item_entry(_test_item(**{"vacuum-pressure-mbar": VACUUM_CEILING_MBAR}))
        self.assertTrue(result["compliant"])

    def test_zero_dwell_is_a_finding(self):
        result = audit_item_entry(_test_item(**{"dwell-duration-minutes": 0.0}))
        self.assertFalse(result["compliant"])

    def test_negative_dwell_raises(self):
        with self.assertRaises(ValueError):
            audit_item_entry(_test_item(**{"dwell-duration-minutes": -5.0}))

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            audit_item_entry(_test_item(**{"vacuum-pressure-mbar": 0.0}))

    def test_non_numeric_power_level_raises(self):
        with self.assertRaises(ValueError):
            audit_item_entry(_test_item(**{"test-power-level-dbm": "43 dBm"}))

    def test_infinite_power_level_raises(self):
        with self.assertRaises(ValueError):
            audit_item_entry(_test_item(**{"test-power-level-dbm": float("inf")}))

    def test_non_positive_analysis_margin_is_a_finding(self):
        result = audit_item_entry(_analysis_item(**{"analysis-margin-db": 0.0}))
        self.assertFalse(result["compliant"])

    def test_blank_similarity_justification_raises(self):
        with self.assertRaises(ValueError):
            audit_item_entry(_similarity_item(**{"delta-justification": "   "}))

    def test_missing_similarity_reference_is_a_finding(self):
        item = _similarity_item()
        del item["fields"]["reference-equipment-id"]
        result = audit_item_entry(item)
        self.assertIn("reference-equipment-id", result["missing_fields"])

    def test_item_without_identifier_raises(self):
        item = _test_item()
        del item["id"]
        with self.assertRaises(ValueError):
            audit_item_entry(item)

    def test_item_with_non_mapping_fields_raises(self):
        item = _test_item()
        item["fields"] = ["everything"]
        with self.assertRaises(ValueError):
            audit_item_entry(item)

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            audit_item_entry("wg-flange-01")


class TestPlanAssessment(unittest.TestCase):
    def test_complete_plan_is_compliant(self):
        result = assess_plan_content(_plan())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["completeness"], 1.0)
        self.assertEqual(result["item_count"], 3)
        self.assertEqual(result["findings"], [])

    def test_plan_missing_an_addition_is_not_compliant(self):
        plan = _plan(content_entries=_entries(omit=("detection-method-pair",)))
        result = assess_plan_content(plan)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["meets_completeness"])

    def test_graded_minimum_accepts_a_partial_plan_but_keeps_the_finding(self):
        plan = _plan(content_entries=_entries(omit=("verification-schedule-and-facility",)))
        result = assess_plan_content(plan, minimum_completeness=0.9)
        self.assertTrue(result["meets_completeness"])
        self.assertFalse(result["compliant"])

    def test_plan_without_items_is_flagged(self):
        result = assess_plan_content(_plan(items=[]))
        self.assertEqual(result["item_count"], 0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("item list" in f for f in result["findings"]))

    def test_item_finding_propagates_to_the_plan(self):
        plan = _plan(items=[_test_item(**{"dwell-duration-minutes": 0.0})])
        result = assess_plan_content(plan)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("zero dwell" in f for f in result["findings"]))

    def test_duplicate_item_identifier_raises(self):
        plan = _plan(items=[_test_item(), _test_item()])
        with self.assertRaises(ValueError):
            assess_plan_content(plan)

    def test_non_list_items_raise(self):
        with self.assertRaises(ValueError):
            assess_plan_content(_plan(items={"id": "wg-flange-01"}))

    def test_non_mapping_plan_raises(self):
        with self.assertRaises(ValueError):
            assess_plan_content("plan")

    def test_minimum_completeness_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            assess_plan_content(_plan(), minimum_completeness=1.2)

    def test_non_numeric_minimum_completeness_raises(self):
        with self.assertRaises(ValueError):
            assess_plan_content(_plan(), minimum_completeness="full")


if __name__ == "__main__":
    unittest.main()
