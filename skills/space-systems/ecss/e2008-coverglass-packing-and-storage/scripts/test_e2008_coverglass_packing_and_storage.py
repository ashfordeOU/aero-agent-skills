#!/usr/bin/env python3
"""Contract test for the coverglass packing and storage pointer, clause 8.11."""

import unittest

from e2008_coverglass_packing_and_storage_logic import (
    ACTIVITY_GOVERNED,
    ACTIVITY_GOVERNED_ON_TAILORING,
    ACTIVITY_NOT_GOVERNED,
    ACTIVITY_SUPERSEDED_ISSUE,
    CONDITIONS_IN_ENVELOPE,
    CONDITIONS_OUT_OF_ENVELOPE,
    DEFAULT_COVERGLASS_STORAGE_POLICY,
    GOVERNED_ACTIVITIES,
    PROTECTED_ACTIVITIES,
    REFERENCE_KINDS,
    RULES_OPEN,
    RULES_RESOLVED,
    STORAGE_LIFE_EXPIRED,
    STORAGE_LIFE_MARGIN_THIN,
    STORAGE_LIFE_OK,
    evaluate_packing_and_storage,
    normalize_activity,
    normalize_reference_kind,
    resolve_activity,
    storage_conditions_state,
    storage_life_state,
    validate_policy,
)


def _declaration(activity, kind="product-assurance-standard", **extra):
    record = {
        "activity": activity,
        "reference_kind": kind,
        "reference_id": "pa-rules-for-coverglasses",
        "reference_issue": 2,
        "governing_issue": 2,
    }
    if activity in PROTECTED_ACTIVITIES:
        record["coated_surface_protection"] = "interleaved separator sheet"
    record.update(extra)
    return record


def _case(**overrides):
    case = {
        "case_id": "cg-store-2026-08",
        "activities": [_declaration(a) for a in GOVERNED_ACTIVITIES],
        "storage_conditions": {
            "temperature_celsius": 20.0,
            "relative_humidity_percent": 40.0,
        },
        "elapsed_storage_days": 100.0,
        "permitted_storage_days": 730.0,
    }
    case.update(overrides)
    return case


class VocabularyTests(unittest.TestCase):
    def test_four_activities_are_handed_over(self):
        self.assertEqual(
            GOVERNED_ACTIVITIES, ("packing", "dispatch", "handling", "storage")
        )

    def test_coated_face_protection_applies_to_packing_and_handling(self):
        self.assertEqual(PROTECTED_ACTIVITIES, ("packing", "handling"))

    def test_activity_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_activity("  Storage "), "storage")

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity("insurance")

    def test_reference_kinds_separate_custom_from_the_standard(self):
        self.assertIn("supplier-instruction", REFERENCE_KINDS)
        self.assertIn("product-assurance-standard", REFERENCE_KINDS)

    def test_unknown_reference_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_reference_kind("warehouse-habit")


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_none_is_declared(self):
        policy = validate_policy(None)
        self.assertAlmostEqual(
            policy["min_storage_life_margin_fraction"],
            DEFAULT_COVERGLASS_STORAGE_POLICY["min_storage_life_margin_fraction"],
            places=9,
        )

    def test_declared_envelope_overrides_only_the_keys_it_names(self):
        policy = validate_policy(
            {"storage_envelope": {"max_relative_humidity_percent": 30.0}}
        )
        self.assertAlmostEqual(
            policy["storage_envelope"]["max_relative_humidity_percent"], 30.0, places=9
        )
        self.assertAlmostEqual(
            policy["storage_envelope"]["max_temperature_celsius"], 25.0, places=9
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"max_shelf_height_m": 2.0})

    def test_inverted_temperature_envelope_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy(
                {
                    "storage_envelope": {
                        "min_temperature_celsius": 30.0,
                        "max_temperature_celsius": 10.0,
                    }
                }
            )

    def test_margin_fraction_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"min_storage_life_margin_fraction": 1.5})


class ActivityResolutionTests(unittest.TestCase):
    def test_product_assurance_reference_governs(self):
        result = resolve_activity(_declaration("dispatch"))
        self.assertEqual(result["state"], ACTIVITY_GOVERNED)
        self.assertTrue(result["governed"])

    def test_undeclared_reference_does_not_govern(self):
        result = resolve_activity(
            {"activity": "dispatch", "reference_kind": "undeclared"}
        )
        self.assertEqual(result["state"], ACTIVITY_NOT_GOVERNED)
        self.assertTrue(result["reasons"])

    def test_supplier_instruction_does_not_govern(self):
        result = resolve_activity(
            {"activity": "dispatch", "reference_kind": "supplier-instruction"}
        )
        self.assertEqual(result["state"], ACTIVITY_NOT_GOVERNED)

    def test_approved_tailoring_governs_on_its_record(self):
        result = resolve_activity(
            _declaration(
                "dispatch", kind="project-tailoring", tailoring_approved=True
            )
        )
        self.assertEqual(result["state"], ACTIVITY_GOVERNED_ON_TAILORING)

    def test_unapproved_tailoring_is_its_own_reason(self):
        result = resolve_activity(
            _declaration(
                "dispatch", kind="project-tailoring", tailoring_approved=False
            )
        )
        self.assertEqual(result["state"], ACTIVITY_NOT_GOVERNED)
        self.assertIn("not approved", result["reasons"][0])

    def test_superseded_issue_governs_in_name_only(self):
        result = resolve_activity(
            _declaration("dispatch", reference_issue=1, governing_issue=4)
        )
        self.assertEqual(result["state"], ACTIVITY_SUPERSEDED_ISSUE)
        self.assertFalse(result["governed"])

    def test_packing_without_a_coated_face_measure_is_reported(self):
        declaration = _declaration("packing")
        del declaration["coated_surface_protection"]
        result = resolve_activity(declaration)
        self.assertEqual(result["state"], ACTIVITY_GOVERNED)
        self.assertTrue(result["reasons"])

    def test_dispatch_is_not_asked_for_a_coated_face_measure(self):
        result = resolve_activity(_declaration("dispatch"))
        self.assertFalse(result["protection_required"])
        self.assertEqual(result["reasons"], ())

    def test_tailoring_without_a_reference_identifier_rejected(self):
        with self.assertRaises(ValueError):
            resolve_activity(
                {"activity": "packing", "reference_kind": "project-tailoring"}
            )

    def test_non_integer_issue_rejected(self):
        with self.assertRaises(ValueError):
            resolve_activity(_declaration("dispatch", reference_issue=2.5))


class StorageConditionTests(unittest.TestCase):
    def test_conditions_inside_the_envelope_pass(self):
        result = storage_conditions_state(
            {"temperature_celsius": 20.0, "relative_humidity_percent": 40.0}
        )
        self.assertEqual(result["state"], CONDITIONS_IN_ENVELOPE)

    def test_reading_exactly_on_the_humidity_ceiling_passes(self):
        result = storage_conditions_state(
            {"temperature_celsius": 20.0, "relative_humidity_percent": 55.0}
        )
        self.assertTrue(result["in_envelope"])
        self.assertAlmostEqual(result["relative_humidity_percent"], 55.0, places=9)

    def test_humidity_above_the_ceiling_is_out_of_envelope(self):
        result = storage_conditions_state(
            {"temperature_celsius": 20.0, "relative_humidity_percent": 70.0}
        )
        self.assertEqual(result["state"], CONDITIONS_OUT_OF_ENVELOPE)

    def test_temperature_below_the_floor_is_out_of_envelope(self):
        result = storage_conditions_state(
            {"temperature_celsius": 4.0, "relative_humidity_percent": 40.0}
        )
        self.assertFalse(result["in_envelope"])

    def test_negative_humidity_rejected(self):
        with self.assertRaises(ValueError):
            storage_conditions_state(
                {"temperature_celsius": 20.0, "relative_humidity_percent": -1.0}
            )

    def test_missing_condition_key_rejected(self):
        with self.assertRaises(ValueError):
            storage_conditions_state({"temperature_celsius": 20.0})


class StorageLifeTests(unittest.TestCase):
    def test_fresh_stock_has_an_adequate_margin(self):
        result = storage_life_state(100.0, 730.0)
        self.assertEqual(result["state"], STORAGE_LIFE_OK)

    def test_margin_exactly_on_its_floor_is_adequate(self):
        result = storage_life_state(80.0, 100.0)
        self.assertAlmostEqual(result["unspent_fraction"], 0.20, places=9)
        self.assertEqual(result["state"], STORAGE_LIFE_OK)

    def test_thin_margin_is_told_apart_from_an_overrun(self):
        thin = storage_life_state(95.0, 100.0)
        overrun = storage_life_state(120.0, 100.0)
        self.assertEqual(thin["state"], STORAGE_LIFE_MARGIN_THIN)
        self.assertEqual(overrun["state"], STORAGE_LIFE_EXPIRED)

    def test_zero_permitted_life_rejected(self):
        with self.assertRaises(ValueError):
            storage_life_state(10.0, 0.0)

    def test_negative_elapsed_days_rejected(self):
        with self.assertRaises(ValueError):
            storage_life_state(-5.0, 100.0)


class CaseVerdictTests(unittest.TestCase):
    def test_all_four_governed_and_in_bounds_resolves(self):
        result = evaluate_packing_and_storage(_case())
        self.assertEqual(result["verdict"], RULES_RESOLVED)
        self.assertEqual(result["findings"], ())
        self.assertAlmostEqual(result["resolved_fraction"], 1.0, places=9)

    def test_an_activity_nobody_declared_is_an_open_activity(self):
        case = _case(
            activities=[_declaration(a) for a in ("packing", "handling", "storage")]
        )
        result = evaluate_packing_and_storage(case)
        self.assertEqual(result["undeclared_activities"], ("dispatch",))
        self.assertEqual(result["verdict"], RULES_OPEN)

    def test_activities_are_resolved_independently(self):
        case = _case(
            activities=[
                _declaration("packing"),
                _declaration("dispatch", kind="supplier-instruction",
                             reference_id="carrier handbook"),
                _declaration("handling"),
                _declaration("storage"),
            ]
        )
        result = evaluate_packing_and_storage(case)
        states = {e["activity"]: e["state"] for e in result["activities"]}
        self.assertEqual(states["packing"], ACTIVITY_GOVERNED)
        self.assertEqual(states["dispatch"], ACTIVITY_NOT_GOVERNED)
        self.assertAlmostEqual(result["resolved_fraction"], 0.75, places=9)

    def test_storage_numbers_are_not_measured_on_an_ungoverned_storage(self):
        case = _case(
            activities=[
                _declaration("packing"),
                _declaration("dispatch"),
                _declaration("handling"),
                _declaration("storage", kind="undeclared", reference_id=None),
            ],
            storage_conditions={
                "temperature_celsius": 45.0,
                "relative_humidity_percent": 95.0,
            },
        )
        result = evaluate_packing_and_storage(case)
        self.assertIsNone(result["storage_conditions"])
        self.assertFalse(result["storage_numbers_measured"])
        self.assertEqual(len(result["findings"]), 1)

    def test_out_of_envelope_storage_opens_the_case(self):
        case = _case(
            storage_conditions={
                "temperature_celsius": 20.0,
                "relative_humidity_percent": 80.0,
            }
        )
        result = evaluate_packing_and_storage(case)
        self.assertEqual(result["verdict"], RULES_OPEN)
        self.assertEqual(result["storage_conditions"]["state"],
                         CONDITIONS_OUT_OF_ENVELOPE)

    def test_storage_overrun_is_reported_as_a_finding(self):
        case = _case(elapsed_storage_days=800.0)
        result = evaluate_packing_and_storage(case)
        self.assertEqual(result["storage_life"]["state"], STORAGE_LIFE_EXPIRED)
        self.assertEqual(result["verdict"], RULES_OPEN)

    def test_repeated_activity_rejected(self):
        case = _case(
            activities=[_declaration("packing"), _declaration("packing")]
        )
        with self.assertRaises(ValueError):
            evaluate_packing_and_storage(case)

    def test_empty_activity_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_packing_and_storage(_case(activities=[]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_packing_and_storage("pack it well")

    def test_activities_are_reported_in_clause_order(self):
        case = _case(
            activities=[_declaration(a) for a in
                        ("storage", "handling", "dispatch", "packing")]
        )
        result = evaluate_packing_and_storage(case)
        self.assertEqual(
            tuple(e["activity"] for e in result["activities"]), GOVERNED_ACTIVITIES
        )


if __name__ == "__main__":
    unittest.main()
