"""Contract tests for the clause 5.2.2.4 minor-disposition logic."""

import unittest

from q1009_minor_disposition_logic import (
    AUTHORITY_CUSTOMER,
    AUTHORITY_INTERNAL,
    AUTHORITY_RANK,
    CONTEXT_KEYS,
    DISPOSITIONS,
    PERMANENT_DEPARTURE_DISPOSITIONS,
    REQUIRED_CONDITIONS,
    assess_minor_disposition,
    authority_satisfied,
    eligible_dispositions,
    missing_conditions,
    normalize_token,
    required_authority,
    validate_authority,
    validate_category,
    validate_context,
    validate_disposition,
)


def context(**over):
    base = {
        "departure_reversible": True,
        "item_repairable": True,
        "externally_supplied": False,
        "customer_furnished": False,
        "customer_controlled_requirement": False,
    }
    base.update(over)
    return base


def evidence_for(disposition, drop=None):
    items = list(REQUIRED_CONDITIONS[disposition])
    if drop is not None:
        items = [i for i in items if i != drop]
    return items


class NormalizeTests(unittest.TestCase):
    def test_case_and_spacing_normalised(self):
        self.assertEqual(normalize_token("Use As Is"), "use-as-is")

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(" ")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(2)


class VocabularyTests(unittest.TestCase):
    def test_every_disposition_has_a_condition_set(self):
        for disposition in DISPOSITIONS:
            self.assertIn(disposition, REQUIRED_CONDITIONS)

    def test_disposition_accepted_from_free_text(self):
        self.assertEqual(validate_disposition("Return To Supplier"), "return-to-supplier")

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_disposition("ship-and-hope")

    def test_authority_scale_is_ordered(self):
        self.assertGreater(AUTHORITY_RANK[AUTHORITY_CUSTOMER], AUTHORITY_RANK[AUTHORITY_INTERNAL])

    def test_unknown_authority_rejected(self):
        with self.assertRaises(ValueError):
            validate_authority("project-manager")

    def test_category_accepted(self):
        self.assertEqual(validate_category("Minor"), "minor")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_category("moderate")

    def test_permanent_departure_set_is_repair_and_use_as_is(self):
        self.assertEqual(set(PERMANENT_DEPARTURE_DISPOSITIONS), {"repair", "use-as-is"})


class ContextTests(unittest.TestCase):
    def test_full_context_accepted(self):
        self.assertEqual(len(validate_context(context())), len(CONTEXT_KEYS))

    def test_unanswered_property_rejected(self):
        partial = context()
        del partial["item_repairable"]
        with self.assertRaises(ValueError):
            validate_context(partial)

    def test_unknown_property_rejected(self):
        bad = context()
        bad["looks_fine"] = True
        with self.assertRaises(ValueError):
            validate_context(bad)

    def test_non_boolean_property_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(context(item_repairable="yes"))

    def test_hyphenated_property_names_accepted(self):
        supplied = {k.replace("_", "-"): v for k, v in context().items()}
        self.assertEqual(len(validate_context(supplied)), len(CONTEXT_KEYS))

    def test_non_mapping_context_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(list(CONTEXT_KEYS))


class EligibilityTests(unittest.TestCase):
    def test_in_house_repairable_reversible_item_has_four_dispositions(self):
        self.assertEqual(
            eligible_dispositions(context()),
            ("rework", "repair", "use-as-is", "scrap"),
        )

    def test_irreversible_departure_removes_rework(self):
        self.assertNotIn("rework", eligible_dispositions(context(departure_reversible=False)))

    def test_unrepairable_item_removes_repair(self):
        self.assertNotIn("repair", eligible_dispositions(context(item_repairable=False)))

    def test_externally_supplied_item_gains_return(self):
        self.assertIn("return-to-supplier", eligible_dispositions(context(externally_supplied=True)))

    def test_scrap_is_always_available(self):
        harsh = context(departure_reversible=False, item_repairable=False)
        self.assertIn("scrap", eligible_dispositions(harsh))

    def test_use_as_is_is_always_available(self):
        harsh = context(departure_reversible=False, item_repairable=False)
        self.assertIn("use-as-is", eligible_dispositions(harsh))


class AuthorityTests(unittest.TestCase):
    def test_minor_rework_stays_with_the_internal_board(self):
        result = required_authority("minor", "rework", context())
        self.assertEqual(result["authority"], AUTHORITY_INTERNAL)
        self.assertEqual(result["reasons"], ())

    def test_major_departure_always_needs_the_customer_board(self):
        result = required_authority("major", "rework", context())
        self.assertEqual(result["authority"], AUTHORITY_CUSTOMER)
        self.assertIn("major-departure", result["reasons"])

    def test_use_as_is_against_a_customer_requirement_rises(self):
        result = required_authority(
            "minor", "use-as-is", context(customer_controlled_requirement=True)
        )
        self.assertEqual(result["authority"], AUTHORITY_CUSTOMER)

    def test_repair_against_a_customer_requirement_rises(self):
        result = required_authority(
            "minor", "repair", context(customer_controlled_requirement=True)
        )
        self.assertIn(
            "permanent-departure-against-customer-controlled-requirement", result["reasons"]
        )

    def test_rework_against_a_customer_requirement_does_not_rise(self):
        result = required_authority(
            "minor", "rework", context(customer_controlled_requirement=True)
        )
        self.assertEqual(result["authority"], AUTHORITY_INTERNAL)

    def test_scrapping_customer_furnished_property_rises(self):
        result = required_authority("minor", "scrap", context(customer_furnished=True))
        self.assertIn("scrapping-customer-furnished-property", result["reasons"])

    def test_reworking_customer_furnished_property_does_not_rise(self):
        result = required_authority("minor", "rework", context(customer_furnished=True))
        self.assertEqual(result["authority"], AUTHORITY_INTERNAL)

    def test_customer_board_may_take_an_internal_case(self):
        self.assertTrue(authority_satisfied(AUTHORITY_CUSTOMER, AUTHORITY_INTERNAL))

    def test_internal_board_may_not_take_a_customer_case(self):
        self.assertFalse(authority_satisfied(AUTHORITY_INTERNAL, AUTHORITY_CUSTOMER))

    def test_same_authority_satisfies(self):
        self.assertTrue(authority_satisfied(AUTHORITY_INTERNAL, AUTHORITY_INTERNAL))


class ConditionTests(unittest.TestCase):
    def test_complete_evidence_leaves_no_gap(self):
        self.assertEqual(missing_conditions("repair", evidence_for("repair")), ())

    def test_missing_limitation_record_reported(self):
        gaps = missing_conditions("use-as-is", evidence_for("use-as-is", drop="limitation-record"))
        self.assertEqual(gaps, ("limitation-record",))

    def test_each_disposition_owes_a_different_set(self):
        self.assertNotEqual(REQUIRED_CONDITIONS["rework"], REQUIRED_CONDITIONS["scrap"])

    def test_mapping_form_with_false_flag_counts_as_missing(self):
        supplied = {i: True for i in REQUIRED_CONDITIONS["scrap"]}
        supplied["replacement-plan"] = False
        self.assertEqual(missing_conditions("scrap", supplied), ("replacement-plan",))

    def test_evidence_names_are_normalised(self):
        supplied = [i.replace("-", " ").title() for i in REQUIRED_CONDITIONS["rework"]]
        self.assertEqual(missing_conditions("rework", supplied), ())

    def test_empty_evidence_reports_the_whole_set(self):
        self.assertEqual(missing_conditions("scrap", []), REQUIRED_CONDITIONS["scrap"])

    def test_non_boolean_evidence_flag_rejected(self):
        supplied = {i: True for i in REQUIRED_CONDITIONS["scrap"]}
        supplied["scrap-authorization"] = "signed"
        with self.assertRaises(ValueError):
            missing_conditions("scrap", supplied)

    def test_non_collection_evidence_rejected(self):
        with self.assertRaises(ValueError):
            missing_conditions("scrap", "scrap-authorization")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "category": "minor",
            "disposition": "rework",
            "context": context(),
            "evidence": evidence_for("rework"),
            "approved_by": AUTHORITY_INTERNAL,
        }
        spec.update(over)
        return spec

    def test_clean_minor_rework_is_authorized(self):
        result = assess_minor_disposition(self._spec())
        self.assertTrue(result["authorized"])
        self.assertEqual(result["findings"], [])

    def test_unavailable_disposition_is_refused(self):
        result = assess_minor_disposition(
            self._spec(context=context(departure_reversible=False))
        )
        self.assertFalse(result["authorized"])
        self.assertTrue(any("not available" in f for f in result["findings"]))

    def test_internal_approval_of_a_customer_case_is_refused(self):
        result = assess_minor_disposition(
            self._spec(
                disposition="use-as-is",
                context=context(customer_controlled_requirement=True),
                evidence=evidence_for("use-as-is"),
            )
        )
        self.assertFalse(result["authority_satisfied"])
        self.assertFalse(result["authorized"])

    def test_customer_approval_of_the_same_case_is_accepted(self):
        result = assess_minor_disposition(
            self._spec(
                disposition="use-as-is",
                context=context(customer_controlled_requirement=True),
                evidence=evidence_for("use-as-is"),
                approved_by=AUTHORITY_CUSTOMER,
            )
        )
        self.assertTrue(result["authorized"])

    def test_missing_condition_blocks_an_otherwise_clean_case(self):
        result = assess_minor_disposition(
            self._spec(evidence=evidence_for("rework", drop="re-inspection-record"))
        )
        self.assertFalse(result["authorized"])
        self.assertEqual(result["missing_conditions"], ("re-inspection-record",))

    def test_permanent_departure_flagged_for_use_as_is(self):
        result = assess_minor_disposition(
            self._spec(disposition="use-as-is", evidence=evidence_for("use-as-is"))
        )
        self.assertTrue(result["leaves_permanent_departure"])

    def test_rework_leaves_no_permanent_departure(self):
        self.assertFalse(assess_minor_disposition(self._spec())["leaves_permanent_departure"])

    def test_scrapping_customer_property_needs_the_customer_board(self):
        result = assess_minor_disposition(
            self._spec(
                disposition="scrap",
                context=context(customer_furnished=True),
                evidence=evidence_for("scrap"),
            )
        )
        self.assertEqual(result["required_authority"], AUTHORITY_CUSTOMER)
        self.assertFalse(result["authorized"])

    def test_available_dispositions_reported(self):
        result = assess_minor_disposition(self._spec())
        self.assertIn("scrap", result["available_dispositions"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["approved_by"]
        with self.assertRaises(ValueError):
            assess_minor_disposition(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_minor_disposition(["category"])

    def test_major_case_cannot_be_taken_internally_whatever_the_evidence(self):
        result = assess_minor_disposition(self._spec(category="major"))
        self.assertFalse(result["authorized"])
        self.assertIn("major-departure", result["escalation_reasons"])


if __name__ == "__main__":
    unittest.main()
