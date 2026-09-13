#!/usr/bin/env python3
"""Contract test for PVA packing, dispatch, handling and storage (offline)."""

import copy
import unittest

from e2008_pva_packaging_and_storage_logic import (
    ACTIVITY_CONDITIONS_OUT_OF_ENVELOPE,
    ACTIVITY_GOVERNED,
    ACTIVITY_GOVERNED_ON_TAILORING,
    ACTIVITY_NOT_GOVERNED,
    DEFAULT_PACKAGING_POLICY,
    GOVERNED_ACTIVITIES,
    REFERENCE_KINDS,
    RULES_OPEN,
    RULES_RESOLVED,
    assess_activity,
    assess_packaging_and_storage,
    governed_activities,
    resolve_reference_disposition,
    storage_envelope_status,
    storage_life_margin,
    validate_packaging_policy,
)

PA_REFERENCE = "product assurance standard issue b"


def _declaration(activity, **overrides):
    entry = {
        "activity": activity,
        "reference_kind": "product-assurance-standard",
        "reference": PA_REFERENCE,
        "tailoring_approved": False,
    }
    if activity == "storage":
        entry["conditions"] = {
            "temperature_celsius": 20.0,
            "relative_humidity_percent": 40.0,
        }
        entry["permitted_storage_days"] = 500.0
        entry["elapsed_storage_days"] = 100.0
    entry.update(overrides)
    return entry


def _case(**overrides):
    case = {
        "declarations": [_declaration(activity) for activity in GOVERNED_ACTIVITIES]
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_packaging_policy(DEFAULT_PACKAGING_POLICY),
            DEFAULT_PACKAGING_POLICY,
        )

    def test_policy_covers_every_reference_kind(self):
        for kind in REFERENCE_KINDS:
            self.assertIn(kind, DEFAULT_PACKAGING_POLICY["reference_disposition"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_packaging_policy("product assurance")

    def test_policy_with_inverted_temperature_envelope_rejected(self):
        broken = copy.deepcopy(DEFAULT_PACKAGING_POLICY)
        broken["storage_envelope"]["max_temperature_celsius"] = 5.0
        with self.assertRaises(ValueError):
            validate_packaging_policy(broken)

    def test_policy_with_impossible_humidity_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_PACKAGING_POLICY)
        broken["storage_envelope"]["max_relative_humidity_percent"] = 140.0
        with self.assertRaises(ValueError):
            validate_packaging_policy(broken)

    def test_policy_with_full_storage_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_PACKAGING_POLICY)
        broken["min_storage_life_margin_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_packaging_policy(broken)

    def test_policy_missing_a_reference_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_PACKAGING_POLICY)
        del broken["reference_disposition"]["supplier-instruction"]
        with self.assertRaises(ValueError):
            validate_packaging_policy(broken)


class ReferenceResolutionTests(unittest.TestCase):
    def test_the_four_activities_are_the_governed_set(self):
        self.assertEqual(governed_activities(), GOVERNED_ACTIVITIES)
        self.assertEqual(len(governed_activities()), 4)

    def test_product_assurance_reference_governs(self):
        self.assertEqual(
            resolve_reference_disposition("product-assurance-standard"),
            ACTIVITY_GOVERNED,
        )

    def test_approved_tailoring_governs(self):
        self.assertEqual(
            resolve_reference_disposition("project-tailoring", True),
            ACTIVITY_GOVERNED_ON_TAILORING,
        )

    def test_unapproved_tailoring_does_not_govern(self):
        self.assertEqual(
            resolve_reference_disposition("project-tailoring", False),
            ACTIVITY_NOT_GOVERNED,
        )

    def test_supplier_instruction_does_not_govern(self):
        self.assertEqual(
            resolve_reference_disposition("supplier-instruction"),
            ACTIVITY_NOT_GOVERNED,
        )

    def test_undeclared_reference_does_not_govern(self):
        self.assertEqual(
            resolve_reference_disposition("undeclared"), ACTIVITY_NOT_GOVERNED
        )

    def test_policy_may_accept_tailoring_without_approval(self):
        policy = copy.deepcopy(DEFAULT_PACKAGING_POLICY)
        policy["require_approved_tailoring"] = False
        self.assertEqual(
            resolve_reference_disposition("project-tailoring", False, policy),
            ACTIVITY_GOVERNED_ON_TAILORING,
        )

    def test_unknown_reference_kind_rejected(self):
        with self.assertRaises(ValueError):
            resolve_reference_disposition("word-of-mouth")

    def test_non_boolean_tailoring_flag_rejected(self):
        with self.assertRaises(ValueError):
            resolve_reference_disposition("project-tailoring", "yes")


class StorageEnvelopeTests(unittest.TestCase):
    def test_nominal_conditions_sit_inside_the_envelope(self):
        status = storage_envelope_status(
            {"temperature_celsius": 20.0, "relative_humidity_percent": 40.0}
        )
        self.assertTrue(status["within_envelope"])
        self.assertEqual(status["findings"], [])

    def test_conditions_exactly_on_both_bounds_are_inside(self):
        status = storage_envelope_status(
            {"temperature_celsius": 25.0, "relative_humidity_percent": 55.0}
        )
        self.assertAlmostEqual(status["temperature_celsius"], 25.0, places=9)
        self.assertAlmostEqual(status["relative_humidity_percent"], 55.0, places=9)
        self.assertTrue(status["within_envelope"])

    def test_conditions_exactly_on_the_lower_bound_are_inside(self):
        status = storage_envelope_status(
            {"temperature_celsius": 15.0, "relative_humidity_percent": 30.0}
        )
        self.assertAlmostEqual(status["temperature_celsius"], 15.0, places=9)
        self.assertTrue(status["temperature_ok"])

    def test_cold_store_falls_outside_the_envelope(self):
        status = storage_envelope_status(
            {"temperature_celsius": 4.0, "relative_humidity_percent": 40.0}
        )
        self.assertFalse(status["temperature_ok"])
        self.assertTrue(status["humidity_ok"])
        self.assertTrue(any("temperature" in f for f in status["findings"]))

    def test_damp_store_falls_outside_the_envelope(self):
        status = storage_envelope_status(
            {"temperature_celsius": 20.0, "relative_humidity_percent": 78.0}
        )
        self.assertTrue(status["temperature_ok"])
        self.assertFalse(status["humidity_ok"])
        self.assertTrue(any("humidity" in f for f in status["findings"]))

    def test_impossible_humidity_reading_rejected(self):
        with self.assertRaises(ValueError):
            storage_envelope_status(
                {"temperature_celsius": 20.0, "relative_humidity_percent": 130.0}
            )

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            storage_envelope_status(
                {"temperature_celsius": "ambient", "relative_humidity_percent": 40.0}
            )

    def test_a_tighter_envelope_can_fail_nominal_conditions(self):
        policy = copy.deepcopy(DEFAULT_PACKAGING_POLICY)
        policy["storage_envelope"]["max_relative_humidity_percent"] = 30.0
        status = storage_envelope_status(
            {"temperature_celsius": 20.0, "relative_humidity_percent": 40.0}, policy
        )
        self.assertFalse(status["within_envelope"])


class StorageLifeTests(unittest.TestCase):
    def test_fresh_storage_keeps_most_of_its_span(self):
        life = storage_life_margin(500.0, 100.0)
        self.assertAlmostEqual(life["remaining_fraction"], 0.8, places=9)
        self.assertTrue(life["sufficient"])
        self.assertFalse(life["exceeded"])

    def test_span_exactly_on_the_required_margin_is_sufficient(self):
        life = storage_life_margin(500.0, 400.0)
        self.assertAlmostEqual(life["remaining_fraction"], 0.20, places=9)
        self.assertAlmostEqual(life["required_fraction"], 0.20, places=9)
        self.assertTrue(life["sufficient"])

    def test_thin_span_is_insufficient_but_not_exceeded(self):
        life = storage_life_margin(500.0, 450.0)
        self.assertFalse(life["sufficient"])
        self.assertFalse(life["exceeded"])
        self.assertTrue(any("storage life" in f for f in life["findings"]))

    def test_overrun_span_is_exceeded(self):
        life = storage_life_margin(500.0, 620.0)
        self.assertTrue(life["exceeded"])
        self.assertAlmostEqual(life["remaining_days"], -120.0, places=9)
        self.assertTrue(any("past the permitted" in f for f in life["findings"]))

    def test_zero_permitted_storage_rejected(self):
        with self.assertRaises(ValueError):
            storage_life_margin(0.0, 10.0)

    def test_negative_elapsed_storage_rejected(self):
        with self.assertRaises(ValueError):
            storage_life_margin(500.0, -10.0)


class ActivityTests(unittest.TestCase):
    def test_packing_on_the_product_assurance_rules_is_governed(self):
        record = assess_activity(_declaration("packing"))
        self.assertEqual(record["verdict"], ACTIVITY_GOVERNED)
        self.assertEqual(record["findings"], [])

    def test_dispatch_on_a_supplier_instruction_is_not_governed(self):
        record = assess_activity(
            _declaration(
                "dispatch",
                reference_kind="supplier-instruction",
                reference="carrier handbook",
            )
        )
        self.assertEqual(record["verdict"], ACTIVITY_NOT_GOVERNED)
        self.assertTrue(any("rather than the product assurance" in f for f in record["findings"]))

    def test_handling_with_no_reference_is_not_governed(self):
        record = assess_activity(
            _declaration("handling", reference_kind="undeclared", reference=None)
        )
        self.assertEqual(record["verdict"], ACTIVITY_NOT_GOVERNED)
        self.assertTrue(any("names no governing" in f for f in record["findings"]))

    def test_handling_on_approved_tailoring_is_governed(self):
        record = assess_activity(
            _declaration(
                "handling",
                reference_kind="project-tailoring",
                reference="tailoring record 7",
                tailoring_approved=True,
            )
        )
        self.assertEqual(record["verdict"], ACTIVITY_GOVERNED_ON_TAILORING)

    def test_unapproved_tailoring_is_reported_by_name(self):
        record = assess_activity(
            _declaration(
                "handling",
                reference_kind="project-tailoring",
                reference="tailoring record 7",
                tailoring_approved=False,
            )
        )
        self.assertEqual(record["verdict"], ACTIVITY_NOT_GOVERNED)
        self.assertTrue(any("not approved" in f for f in record["findings"]))

    def test_storage_outside_the_envelope_is_flagged_even_when_governed(self):
        record = assess_activity(
            _declaration(
                "storage",
                conditions={
                    "temperature_celsius": 34.0,
                    "relative_humidity_percent": 40.0,
                },
            )
        )
        self.assertEqual(record["verdict"], ACTIVITY_CONDITIONS_OUT_OF_ENVELOPE)
        self.assertFalse(record["envelope"]["within_envelope"])

    def test_storage_past_its_life_margin_is_flagged(self):
        record = assess_activity(
            _declaration("storage", elapsed_storage_days=470.0)
        )
        self.assertEqual(record["verdict"], ACTIVITY_CONDITIONS_OUT_OF_ENVELOPE)
        self.assertFalse(record["storage_life"]["sufficient"])

    def test_storage_without_declared_numbers_is_still_resolved(self):
        entry = _declaration("storage")
        del entry["conditions"]
        del entry["permitted_storage_days"]
        record = assess_activity(entry)
        self.assertEqual(record["verdict"], ACTIVITY_GOVERNED)
        self.assertIsNone(record["envelope"])
        self.assertIsNone(record["storage_life"])

    def test_declared_kind_without_a_named_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_activity(_declaration("packing", reference="   "))

    def test_unknown_activity_rejected(self):
        entry = _declaration("packing")
        entry["activity"] = "marking"
        with self.assertRaises(ValueError):
            assess_activity(entry)

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_activity("packing")


class CaseTests(unittest.TestCase):
    def test_fully_referenced_case_is_resolved(self):
        result = assess_packaging_and_storage(_case())
        self.assertEqual(result["verdict"], RULES_RESOLVED)
        self.assertEqual(result["open_activities"], [])
        self.assertAlmostEqual(result["resolved_fraction"], 1.0, places=9)

    def test_one_undeclared_activity_opens_the_case(self):
        declarations = [_declaration(a) for a in GOVERNED_ACTIVITIES if a != "dispatch"]
        result = assess_packaging_and_storage({"declarations": declarations})
        self.assertEqual(result["verdict"], RULES_OPEN)
        self.assertEqual(result["uncovered_activities"], ["dispatch"])
        self.assertAlmostEqual(result["resolved_fraction"], 0.75, places=9)

    def test_supplier_governed_activity_opens_the_case(self):
        declarations = [
            _declaration(a) for a in GOVERNED_ACTIVITIES if a != "handling"
        ] + [
            _declaration(
                "handling",
                reference_kind="supplier-instruction",
                reference="carrier handbook",
            )
        ]
        result = assess_packaging_and_storage({"declarations": declarations})
        self.assertEqual(result["verdict"], RULES_OPEN)
        self.assertEqual(result["open_activities"], ["handling"])

    def test_case_groups_activities_by_verdict(self):
        declarations = [
            _declaration(a) for a in GOVERNED_ACTIVITIES if a != "storage"
        ] + [
            _declaration(
                "storage",
                conditions={
                    "temperature_celsius": 34.0,
                    "relative_humidity_percent": 40.0,
                },
            )
        ]
        grouped = assess_packaging_and_storage({"declarations": declarations})[
            "grouped_by_verdict"
        ]
        self.assertEqual(grouped[ACTIVITY_CONDITIONS_OUT_OF_ENVELOPE], ["storage"])
        self.assertEqual(len(grouped[ACTIVITY_GOVERNED]), 3)

    def test_case_collects_every_finding(self):
        declarations = [_declaration(a) for a in GOVERNED_ACTIVITIES if a != "packing"]
        findings = assess_packaging_and_storage({"declarations": declarations})[
            "findings"
        ]
        self.assertTrue(any("packing is not declared" in f for f in findings))

    def test_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging_and_storage(
                {"declarations": [_declaration("packing"), _declaration("packing")]}
            )

    def test_empty_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging_and_storage({"declarations": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging_and_storage([_declaration("packing")])


if __name__ == "__main__":
    unittest.main()
