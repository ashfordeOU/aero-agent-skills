#!/usr/bin/env python3
"""Gate 3 contract test for the clause 8.2 tailoring-category logic."""

import unittest

from e20_inclusive_and_exclusive_category_use_logic import (
    applicability,
    assess_inclusive_and_exclusive_category_use,
    build_matrix_column,
    check_tailoring_record,
    normalize_product_roles,
    normalize_requirement,
    ratio_within_ceiling,
    tailoring_action,
    validate_catalogue,
)

ROLES = ["antenna", "passive-rf-unit"]

EXCLUSIVE = {
    "id": "r-1",
    "clause": "5.3.2",
    "category": "exclusive",
    "product_types": ["antenna"],
}

INCLUSIVE = {
    "id": "r-2",
    "clause": "6.1.1",
    "category": "inclusive",
    "excepted_types": ["harness"],
}


def _exclusive(**overrides):
    entry = dict(EXCLUSIVE)
    entry.update(overrides)
    return entry


def _inclusive(**overrides):
    entry = dict(INCLUSIVE)
    entry.update(overrides)
    return entry


class TestRoleNormalization(unittest.TestCase):
    def test_roles_happy_path(self):
        self.assertEqual(normalize_product_roles(ROLES), ("antenna", "passive-rf-unit"))

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_roles(["antenna", "gyroscope"])

    def test_duplicate_role_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_roles(["antenna", "antenna"])

    def test_empty_role_set_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_roles([])

    def test_missing_role_set_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_roles(None)

    def test_non_list_role_set_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_product_roles("antenna")


class TestRequirementNormalization(unittest.TestCase):
    def test_exclusive_entry_happy_path(self):
        entry = normalize_requirement(_exclusive())
        self.assertEqual(entry["category"], "exclusive")
        self.assertEqual(entry["product_types"], ("antenna",))
        self.assertEqual(entry["excepted_types"], ())
        self.assertAlmostEqual(entry["weight"], 1.0)

    def test_inclusive_entry_happy_path(self):
        entry = normalize_requirement(_inclusive())
        self.assertEqual(entry["product_types"], ())
        self.assertEqual(entry["excepted_types"], ("harness",))

    def test_inclusive_entry_without_exceptions(self):
        entry = normalize_requirement(
            {"id": "r-9", "clause": "7.1", "category": "inclusive"}
        )
        self.assertEqual(entry["excepted_types"], ())

    def test_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            normalize_requirement(["r-1"])

    def test_rejects_blank_identifier(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(id=" "))

    def test_rejects_missing_clause_anchor(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(clause=""))

    def test_rejects_unknown_category(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(category="optional"))

    def test_exclusive_entry_must_name_a_product_type(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(product_types=[]))

    def test_exclusive_entry_may_not_carry_exceptions(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(excepted_types=["harness"]))

    def test_inclusive_entry_may_not_name_product_types(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_inclusive(product_types=["antenna"]))

    def test_rejects_unknown_product_type_in_a_list(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(product_types=["reaction-wheel"]))

    def test_rejects_duplicate_product_type_in_a_list(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(product_types=["antenna", "antenna"]))

    def test_rejects_non_positive_weight(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(weight=0.0))

    def test_rejects_boolean_weight(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(weight=True))

    def test_rejects_non_finite_weight(self):
        with self.assertRaises(ValueError):
            normalize_requirement(_exclusive(weight=float("inf")))

    def test_normalization_is_idempotent(self):
        once = normalize_requirement(_exclusive())
        self.assertEqual(once, normalize_requirement(once))


class TestCatalogueValidation(unittest.TestCase):
    def test_catalogue_happy_path(self):
        entries = validate_catalogue([_exclusive(), _inclusive()])
        self.assertEqual([e["id"] for e in entries], ["r-1", "r-2"])

    def test_rejects_empty_catalogue(self):
        with self.assertRaises(ValueError):
            validate_catalogue([])

    def test_rejects_non_list_catalogue(self):
        with self.assertRaises(ValueError):
            validate_catalogue(_exclusive())

    def test_rejects_duplicate_requirement_identifier(self):
        with self.assertRaises(ValueError):
            validate_catalogue([_exclusive(), _exclusive()])


class TestApplicability(unittest.TestCase):
    def test_exclusive_applies_to_a_named_role(self):
        verdict = applicability(_exclusive(), ROLES)
        self.assertTrue(verdict["applicable"])
        self.assertIn("antenna", verdict["reason"])

    def test_exclusive_does_not_apply_to_an_unnamed_role(self):
        verdict = applicability(_exclusive(product_types=["harness"]), ROLES)
        self.assertFalse(verdict["applicable"])

    def test_exclusive_applies_through_the_second_role(self):
        verdict = applicability(_exclusive(product_types=["passive-rf-unit"]), ROLES)
        self.assertTrue(verdict["applicable"])

    def test_inclusive_applies_by_default(self):
        verdict = applicability(_inclusive(), ROLES)
        self.assertTrue(verdict["applicable"])

    def test_inclusive_is_deleted_only_when_every_role_is_excepted(self):
        verdict = applicability(
            _inclusive(excepted_types=["antenna", "passive-rf-unit"]), ROLES
        )
        self.assertFalse(verdict["applicable"])
        self.assertIn("excepts every product role", verdict["reason"])

    def test_inclusive_survives_a_partial_exception(self):
        verdict = applicability(_inclusive(excepted_types=["antenna"]), ROLES)
        self.assertTrue(verdict["applicable"])
        self.assertIn("passive-rf-unit", verdict["reason"])

    def test_verdict_carries_the_clause_anchor(self):
        self.assertEqual(applicability(_exclusive(), ROLES)["clause"], "5.3.2")

    def test_applicability_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            applicability(_exclusive(), ["propellant-tank"])


class TestTailoringAction(unittest.TestCase):
    def test_applicable_kept_is_keep(self):
        self.assertEqual(tailoring_action(_exclusive(), ROLES, "keep"), "keep")

    def test_applicable_deleted_needs_a_deviation(self):
        self.assertEqual(
            tailoring_action(_exclusive(), ROLES, "delete"), "deviation-required"
        )

    def test_not_applicable_deleted_is_delete(self):
        self.assertEqual(
            tailoring_action(_exclusive(product_types=["harness"]), ROLES, "delete"),
            "delete",
        )

    def test_not_applicable_kept_is_keep(self):
        self.assertEqual(
            tailoring_action(_exclusive(product_types=["harness"]), ROLES, "keep"),
            "keep",
        )

    def test_unknown_decision_is_rejected(self):
        with self.assertRaises(ValueError):
            tailoring_action(_exclusive(), ROLES, "waive")


class TestTailoringRecord(unittest.TestCase):
    def test_clean_deletion_of_a_non_applicable_requirement(self):
        checked = check_tailoring_record(
            _exclusive(product_types=["harness"]),
            ROLES,
            {"decision": "delete", "rationale": "no named role on this product"},
        )
        self.assertEqual(checked["findings"], [])
        self.assertEqual(checked["action"], "delete")

    def test_deletion_without_a_rationale_is_a_finding(self):
        checked = check_tailoring_record(
            _exclusive(product_types=["harness"]), ROLES, {"decision": "delete"}
        )
        self.assertTrue(any("rationale" in f for f in checked["findings"]))

    def test_deleting_an_applicable_requirement_needs_a_deviation(self):
        checked = check_tailoring_record(
            _exclusive(), ROLES, {"decision": "delete", "rationale": "cost"}
        )
        self.assertTrue(any("deviation" in f for f in checked["findings"]))
        self.assertEqual(checked["action"], "deviation-required")

    def test_approved_deviation_clears_the_deletion(self):
        checked = check_tailoring_record(
            _exclusive(),
            ROLES,
            {"decision": "delete", "deviation_ref": "DEV-014", "rationale": "agreed"},
        )
        self.assertEqual(checked["findings"], [])

    def test_keeping_a_non_applicable_requirement_needs_a_rationale(self):
        checked = check_tailoring_record(
            _exclusive(product_types=["harness"]), ROLES, {"decision": "keep"}
        )
        self.assertTrue(any("not applicable" in f for f in checked["findings"]))

    def test_keeping_an_applicable_requirement_is_clean(self):
        checked = check_tailoring_record(_exclusive(), ROLES, {"decision": "keep"})
        self.assertEqual(checked["findings"], [])

    def test_rejects_non_mapping_record(self):
        with self.assertRaises(ValueError):
            check_tailoring_record(_exclusive(), ROLES, "delete")

    def test_rejects_unknown_decision_in_a_record(self):
        with self.assertRaises(ValueError):
            check_tailoring_record(_exclusive(), ROLES, {"decision": "defer"})


class TestRatioCeiling(unittest.TestCase):
    def test_ratio_at_the_ceiling_is_within_it(self):
        self.assertTrue(ratio_within_ceiling(0.5, 0.5))

    def test_representation_error_does_not_breach_the_ceiling(self):
        drifted = 0.1 + 0.2  # 0.30000000000000004
        self.assertGreater(drifted, 0.3)
        self.assertTrue(ratio_within_ceiling(drifted, 0.3))

    def test_a_real_overshoot_still_breaches_the_ceiling(self):
        self.assertFalse(ratio_within_ceiling(0.31, 0.3))

    def test_ratio_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            ratio_within_ceiling(1.5, 0.3)

    def test_ceiling_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            ratio_within_ceiling(0.3, -0.1)

    def test_non_numeric_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            ratio_within_ceiling("0.3", 0.3)

    def test_boolean_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            ratio_within_ceiling(0.3, True)


class TestMatrixColumn(unittest.TestCase):
    def test_column_counts_applicable_and_deleted_rows(self):
        column = build_matrix_column(
            [_exclusive(), _inclusive(), _exclusive(id="r-3", product_types=["harness"])],
            ROLES,
        )
        self.assertEqual(column["requirement_count"], 3)
        self.assertEqual(column["applicable_count"], 2)
        self.assertEqual(column["not_applicable_count"], 1)
        self.assertAlmostEqual(column["applicable_fraction"], 2.0 / 3.0, places=9)

    def test_column_echoes_the_product_roles(self):
        column = build_matrix_column([_exclusive()], ROLES)
        self.assertEqual(column["roles"], ("antenna", "passive-rf-unit"))

    def test_column_rejects_an_unknown_role(self):
        with self.assertRaises(ValueError):
            build_matrix_column([_exclusive()], ["solar-panel"])


class TestAssessment(unittest.TestCase):
    def test_default_records_are_derived_and_clean(self):
        result = assess_inclusive_and_exclusive_category_use(
            [_exclusive(), _inclusive(), _exclusive(id="r-3", product_types=["harness"])],
            ROLES,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["deleted_count"], 1)
        self.assertEqual(result["kept_count"], 2)

    def test_deleted_weight_ratio_uses_the_weights(self):
        result = assess_inclusive_and_exclusive_category_use(
            [
                _exclusive(weight=1.0),
                _exclusive(id="r-3", product_types=["harness"], weight=3.0),
            ],
            ROLES,
        )
        self.assertAlmostEqual(result["deleted_weight_ratio"], 0.75, places=9)

    def test_deletion_ceiling_breach_is_a_finding(self):
        result = assess_inclusive_and_exclusive_category_use(
            [
                _exclusive(weight=1.0),
                _exclusive(id="r-3", product_types=["harness"], weight=3.0),
            ],
            ROLES,
            deletion_ceiling=0.5,
        )
        self.assertFalse(result["within_deletion_ceiling"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("deletion-ceiling" in f for f in result["findings"]))

    def test_deletion_ceiling_exactly_met_is_within(self):
        result = assess_inclusive_and_exclusive_category_use(
            [
                _exclusive(weight=1.0),
                _exclusive(id="r-3", product_types=["harness"], weight=1.0),
            ],
            ROLES,
            deletion_ceiling=0.5,
        )
        self.assertTrue(result["within_deletion_ceiling"])
        self.assertAlmostEqual(result["deleted_weight_ratio"], 0.5, places=9)

    def test_explicit_record_without_a_deviation_is_a_finding(self):
        result = assess_inclusive_and_exclusive_category_use(
            [_exclusive()],
            ROLES,
            records={"r-1": {"decision": "delete", "rationale": "schedule"}},
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("deviation" in f for f in result["findings"]))

    def test_explicit_record_with_a_deviation_is_compliant(self):
        result = assess_inclusive_and_exclusive_category_use(
            [_exclusive()],
            ROLES,
            records={
                "r-1": {
                    "decision": "delete",
                    "rationale": "agreed at the review",
                    "deviation_ref": "DEV-014",
                }
            },
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["deleted_count"], 1)

    def test_record_for_an_unknown_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_inclusive_and_exclusive_category_use(
                [_exclusive()], ROLES, records={"r-99": {"decision": "keep"}}
            )

    def test_non_mapping_records_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_inclusive_and_exclusive_category_use(
                [_exclusive()], ROLES, records=[{"decision": "keep"}]
            )

    def test_empty_catalogue_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_inclusive_and_exclusive_category_use([], ROLES)

    def test_column_is_returned_with_the_assessment(self):
        result = assess_inclusive_and_exclusive_category_use([_exclusive()], ROLES)
        self.assertEqual(result["column"]["requirement_count"], 1)
        self.assertAlmostEqual(result["column"]["applicable_fraction"], 1.0)


if __name__ == "__main__":
    unittest.main()
