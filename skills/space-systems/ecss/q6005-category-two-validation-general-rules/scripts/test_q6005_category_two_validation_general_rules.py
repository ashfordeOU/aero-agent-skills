#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 6.3.1 general-rules leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_category_two_validation_general_rules.py
"""

import unittest

from q6005_category_two_validation_general_rules_logic import (
    ADMISSIBILITY_INDEX,
    BASE_VALIDITY_MONTHS,
    CONDITION_STATE_CREDIT,
    ENTRY_CONDITION_WEIGHTS,
    LINE_STABILITY_WINDOW_MONTHS,
    MANDATORY_ENTRY_CONDITIONS,
    MINIMUM_VALIDITY_MONTHS,
    TECHNOLOGY_FAMILIES,
    VALIDATION_ELEMENTS,
    VALIDATION_TOLERANCE,
    VALIDITY_PENALTY_PER_RESERVATION_MONTHS,
    VERDICTS,
    assess_category_two_validation,
    assess_condition,
    condition_weight,
    element_coverage,
    line_is_stable,
    normalize_condition,
    readiness_index,
    scope_envelope,
    state_credit,
    technology_family_in_scope,
    validity_months,
)

FAMILY = "thick-film-hybrid"
DECLARED_RANGE = ["ceramic-flatpack-24", "ceramic-flatpack-40"]
SPARE_CONDITION = "previous-validation-history-disclosed"
STABLE_MONTHS = 18.0


def all_elements():
    """Every element a category two validation is made of."""
    return list(VALIDATION_ELEMENTS)


def met_conditions(**states):
    """Every entry condition met, with named exceptions."""
    records = []
    for name in sorted(ENTRY_CONDITION_WEIGHTS):
        entry = {"condition": name, "state": "met"}
        if name in states:
            entry["state"] = states[name]
        records.append(entry)
    return records


def clean_case(**overrides):
    """Arguments of a validation that nothing is outstanding on."""
    case = {
        "supplier_id": "SUP-01",
        "technology_family": FAMILY,
        "declared_scope": list(DECLARED_RANGE),
        "examined_scope": list(DECLARED_RANGE),
        "conditions": met_conditions(),
        "planned_elements": all_elements(),
        "months_since_last_line_change": STABLE_MONTHS,
    }
    case.update(overrides)
    return case


def run(**overrides):
    """Grade one validation case."""
    return assess_category_two_validation(**clean_case(**overrides))


class TechnologyFamilyTests(unittest.TestCase):
    def test_a_known_family_is_in_scope_for_the_route(self):
        for family in TECHNOLOGY_FAMILIES:
            self.assertTrue(technology_family_in_scope(family))

    def test_an_unlisted_family_is_out_of_scope_rather_than_an_error(self):
        self.assertFalse(technology_family_in_scope("monolithic-microwave-die"))

    def test_an_empty_family_name_is_rejected(self):
        with self.assertRaises(ValueError):
            technology_family_in_scope("   ")


class EntryConditionTests(unittest.TestCase):
    def test_every_mandatory_condition_carries_a_published_weight(self):
        for name in MANDATORY_ENTRY_CONDITIONS:
            self.assertIn(name, ENTRY_CONDITION_WEIGHTS)

    def test_an_unknown_condition_name_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_weight("line-smells-clean")

    def test_an_unknown_condition_state_is_rejected(self):
        with self.assertRaises(ValueError):
            state_credit("probably-fine")

    def test_a_condition_defaults_to_not_assessed_when_nobody_named_a_state(self):
        record = normalize_condition({"condition": SPARE_CONDITION})
        self.assertEqual(record["state"], "not-assessed")

    def test_a_condition_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_condition(["supplier-quality-system-certified", "met"])

    def test_a_met_condition_earns_its_full_weight(self):
        record = assess_condition(
            {"condition": "supplier-quality-system-certified", "state": "met"}
        )
        self.assertAlmostEqual(
            record["weighted_credit"],
            ENTRY_CONDITION_WEIGHTS["supplier-quality-system-certified"],
            places=9,
        )
        self.assertEqual(record["findings"], [])

    def test_a_reservation_is_a_finding_but_not_a_mandatory_breach(self):
        record = assess_condition(
            {
                "condition": "production-line-identified-and-frozen",
                "state": "met-with-reservation",
            }
        )
        self.assertIn("condition-met-with-reservation", record["findings"])
        self.assertFalse(record["mandatory_unmet"])

    def test_an_unmet_mandatory_condition_is_marked_as_such(self):
        record = assess_condition(
            {"condition": "validation-authority-nominated", "state": "not-met"}
        )
        self.assertTrue(record["mandatory_unmet"])
        self.assertIn("mandatory-entry-condition-unmet", record["findings"])

    def test_an_unassessed_optional_condition_is_not_a_mandatory_breach(self):
        record = assess_condition({"condition": SPARE_CONDITION, "state": "not-assessed"})
        self.assertFalse(record["mandatory_unmet"])
        self.assertIn("entry-condition-not-assessed", record["findings"])


class ReadinessIndexTests(unittest.TestCase):
    def test_all_conditions_met_gives_a_full_index(self):
        records = [assess_condition(entry) for entry in met_conditions()]
        self.assertAlmostEqual(readiness_index(records), 1.0, places=9)

    def test_an_empty_condition_set_is_rejected(self):
        with self.assertRaises(ValueError):
            readiness_index([])

    def test_a_non_sequence_condition_set_is_rejected(self):
        with self.assertRaises(ValueError):
            readiness_index({"condition": "x"})

    def test_a_reservation_lowers_the_index_below_the_full_value(self):
        records = [
            assess_condition(entry)
            for entry in met_conditions(**{SPARE_CONDITION: "met-with-reservation"})
        ]
        self.assertLess(readiness_index(records), 1.0 - 1e-6)


class LineStabilityTests(unittest.TestCase):
    def test_a_line_unchanged_beyond_the_window_is_stable(self):
        self.assertTrue(line_is_stable(LINE_STABILITY_WINDOW_MONTHS + 1.0))

    def test_a_line_exactly_on_the_window_is_stable(self):
        self.assertTrue(line_is_stable(LINE_STABILITY_WINDOW_MONTHS))

    def test_a_line_changed_inside_the_window_is_not_stable(self):
        self.assertFalse(line_is_stable(LINE_STABILITY_WINDOW_MONTHS - 1.0))

    def test_a_negative_age_since_the_last_line_change_is_rejected(self):
        with self.assertRaises(ValueError):
            line_is_stable(-1.0)

    def test_a_non_numeric_age_is_rejected(self):
        with self.assertRaises(ValueError):
            line_is_stable("six months")


class ScopeEnvelopeTests(unittest.TestCase):
    def test_an_examined_range_equal_to_the_declared_range_leaves_nothing_outside(self):
        envelope = scope_envelope(DECLARED_RANGE, DECLARED_RANGE)
        self.assertEqual(envelope["inside_envelope"], sorted(DECLARED_RANGE))
        self.assertEqual(envelope["declared_not_examined"], [])
        self.assertEqual(envelope["examined_not_declared"], [])

    def test_a_declared_item_nobody_examined_sits_outside_the_envelope(self):
        envelope = scope_envelope(DECLARED_RANGE, ["ceramic-flatpack-24"])
        self.assertEqual(envelope["declared_not_examined"], ["ceramic-flatpack-40"])

    def test_an_examined_item_nobody_declared_is_reported_too(self):
        envelope = scope_envelope(["ceramic-flatpack-24"], ["ceramic-flatpack-24", "metal-can-8"])
        self.assertEqual(envelope["examined_not_declared"], ["metal-can-8"])

    def test_a_repeated_range_item_is_rejected(self):
        with self.assertRaises(ValueError):
            scope_envelope(["ceramic-flatpack-24", "ceramic-flatpack-24"], DECLARED_RANGE)

    def test_an_empty_examined_range_is_rejected(self):
        with self.assertRaises(ValueError):
            scope_envelope(DECLARED_RANGE, [])


class ElementCoverageTests(unittest.TestCase):
    def test_a_plan_naming_every_element_leaves_none_missing(self):
        self.assertEqual(element_coverage(all_elements()), [])

    def test_a_plan_missing_the_audit_reports_it(self):
        planned = [name for name in VALIDATION_ELEMENTS if "audit" not in name]
        self.assertEqual(element_coverage(planned), ["supplier-quality-and-technical-audit"])

    def test_an_unknown_element_name_is_rejected(self):
        with self.assertRaises(ValueError):
            element_coverage(list(VALIDATION_ELEMENTS) + ["lunch-with-the-supplier"])


class ValidityTermTests(unittest.TestCase):
    def test_a_validation_with_no_reservation_gets_the_full_term(self):
        self.assertAlmostEqual(validity_months(0), BASE_VALIDITY_MONTHS, places=9)

    def test_each_reservation_strikes_its_penalty_off_the_term(self):
        self.assertAlmostEqual(
            validity_months(2),
            BASE_VALIDITY_MONTHS - 2.0 * VALIDITY_PENALTY_PER_RESERVATION_MONTHS,
            places=9,
        )

    def test_a_term_falling_under_the_floor_is_not_worth_issuing(self):
        too_many = int(BASE_VALIDITY_MONTHS // VALIDITY_PENALTY_PER_RESERVATION_MONTHS)
        self.assertAlmostEqual(validity_months(too_many), 0.0, places=9)

    def test_a_negative_reservation_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validity_months(-1)

    def test_a_boolean_reservation_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validity_months(True)


class WholeValidationTests(unittest.TestCase):
    def test_a_clean_case_is_admissible_with_nothing_outstanding(self):
        result = run()
        self.assertEqual(result["verdict"], "category-two-validation-admissible")
        self.assertTrue(result["may_proceed"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["readiness_index"], 1.0, places=9)
        self.assertAlmostEqual(result["validity_months"], BASE_VALIDITY_MONTHS, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_an_unplanned_element_makes_the_preconditions_incomplete(self):
        planned = [name for name in VALIDATION_ELEMENTS if "evaluation" not in name]
        result = run(planned_elements=planned)
        self.assertEqual(result["verdict"], "category-two-validation-preconditions-incomplete")
        self.assertFalse(result["may_proceed"])
        self.assertIn("evaluation-testing-of-sample-units", result["missing_elements"])

    def test_an_unmet_mandatory_condition_makes_the_preconditions_incomplete(self):
        result = run(conditions=met_conditions(**{"validation-authority-nominated": "not-met"}))
        self.assertEqual(result["verdict"], "category-two-validation-preconditions-incomplete")

    def test_a_line_changed_inside_the_window_blocks_an_otherwise_clean_case(self):
        result = run(months_since_last_line_change=LINE_STABILITY_WINDOW_MONTHS - 2.0)
        self.assertEqual(result["verdict"], "category-two-validation-not-admissible")
        self.assertFalse(result["line_stable"])
        self.assertIn(
            "line-changed-inside-stability-window",
            [f["finding"] for f in result["findings"]],
        )

    def test_a_family_outside_the_route_blocks_the_validation(self):
        result = run(technology_family="monolithic-microwave-die")
        self.assertEqual(result["verdict"], "category-two-validation-not-admissible")

    def test_a_declared_item_never_examined_is_a_reservation_not_a_pass(self):
        result = run(examined_scope=["ceramic-flatpack-24"])
        self.assertEqual(
            result["verdict"], "category-two-validation-admissible-with-reservations"
        )
        self.assertEqual(result["envelope"]["declared_not_examined"], ["ceramic-flatpack-40"])

    def test_a_single_reservation_shortens_the_term_and_keeps_the_route_open(self):
        result = run(conditions=met_conditions(**{SPARE_CONDITION: "met-with-reservation"}))
        self.assertEqual(result["reservation_count"], 1)
        self.assertAlmostEqual(
            result["validity_months"],
            BASE_VALIDITY_MONTHS - VALIDITY_PENALTY_PER_RESERVATION_MONTHS,
            places=9,
        )
        self.assertTrue(result["may_proceed"])

    def test_an_unassessed_optional_condition_can_drop_the_index_below_the_bound(self):
        result = run(
            conditions=met_conditions(
                **{
                    "customer-agreement-recorded": "not-met",
                    "product-range-declared": "not-met",
                    "process-documentation-released": "not-met",
                    SPARE_CONDITION: "not-met",
                }
            )
        )
        self.assertLess(result["readiness_index"], ADMISSIBILITY_INDEX)
        self.assertEqual(result["verdict"], "category-two-validation-not-admissible")

    def test_a_repeated_entry_condition_is_rejected(self):
        conditions = met_conditions() + [{"condition": SPARE_CONDITION, "state": "met"}]
        with self.assertRaises(ValueError):
            run(conditions=conditions)

    def test_a_blank_supplier_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(supplier_id="  ")

    def test_a_non_sequence_condition_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(conditions={"condition": SPARE_CONDITION})

    def test_a_condition_nobody_mentioned_is_graded_as_not_assessed(self):
        result = run(conditions=[{"condition": SPARE_CONDITION, "state": "met"}])
        states = {r["condition"]: r["state"] for r in result["condition_records"]}
        self.assertEqual(states["customer-agreement-recorded"], "not-assessed")
        self.assertEqual(len(result["condition_records"]), len(ENTRY_CONDITION_WEIGHTS))


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(VALIDATION_TOLERANCE, 1e-6)

    def test_the_condition_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(CONDITION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(CONDITION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_validity_floor_sits_under_the_full_term(self):
        self.assertLess(MINIMUM_VALIDITY_MONTHS, BASE_VALIDITY_MONTHS)


if __name__ == "__main__":
    unittest.main()
