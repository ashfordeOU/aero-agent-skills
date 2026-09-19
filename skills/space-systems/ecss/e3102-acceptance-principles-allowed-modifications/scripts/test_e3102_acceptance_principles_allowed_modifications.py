#!/usr/bin/env python3
"""Contract test for the two-phase acceptance principles (offline)."""

import copy
import unittest

from e3102_acceptance_principles_allowed_modifications_logic import (
    ACCEPT_AS_IS,
    BASELINE_ACCEPTANCE_TESTS,
    DELTA_ACCEPTANCE,
    DISPOSITION_ORDER,
    MODIFICATION_POLICY,
    MODIFICATION_TYPES,
    REQUALIFICATION,
    acceptance_test_set,
    apply_acceptance_principles,
    audit_acceptance_levels,
    disposition_for,
    most_onerous,
    validate_modification,
    within_qualified_span,
)

SHORTER_ADIABATIC = {
    "type": "adiabatic-length-change",
    "value": 0.42,
    "qualified_min": 0.30,
    "qualified_max": 0.60,
}

LONGER_EVAPORATOR = {
    "type": "evaporator-length-change",
    "value": 0.18,
    "qualified_min": 0.10,
    "qualified_max": 0.25,
}

OVERLONG_EVAPORATOR = {
    "type": "evaporator-length-change",
    "value": 0.40,
    "qualified_min": 0.10,
    "qualified_max": 0.25,
}

NEW_WICK = {"type": "wick-structure-change"}
NEW_FINISH = {"type": "external-finish-change"}

ACCEPTANCE_LEVELS = {"min_k": 258.0, "max_k": 328.0, "asd_g2_per_hz": 0.04}
QUALIFICATION_LEVELS = {"min_k": 248.0, "max_k": 338.0, "asd_g2_per_hz": 0.08}

BASE_CASE = {
    "article": "loop heat pipe flight unit 004",
    "modifications": (SHORTER_ADIABATIC, NEW_FINISH),
    "acceptance_levels": ACCEPTANCE_LEVELS,
    "qualification_levels": QUALIFICATION_LEVELS,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _mod(base, **overrides):
    mod = copy.deepcopy(base)
    mod.update(overrides)
    return mod


class ModificationValidationTests(unittest.TestCase):
    def test_every_policy_entry_is_gradeable(self):
        for kind in MODIFICATION_TYPES:
            policy = MODIFICATION_POLICY[kind]
            if policy["range_relevant"]:
                self.assertIn(policy["within"], DISPOSITION_ORDER)
                self.assertIn(policy["outside"], DISPOSITION_ORDER)
            else:
                self.assertIn(policy["fixed"], DISPOSITION_ORDER)

    def test_a_range_graded_change_validates(self):
        self.assertIs(validate_modification(SHORTER_ADIABATIC), SHORTER_ADIABATIC)

    def test_an_unknown_change_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_modification({"type": "repainted-in-house-colours"})

    def test_a_range_graded_change_without_a_value_rejected(self):
        broken = _mod(SHORTER_ADIABATIC)
        del broken["value"]
        with self.assertRaises(ValueError):
            validate_modification(broken)

    def test_an_inverted_qualified_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_modification(
                _mod(SHORTER_ADIABATIC, qualified_min=0.60, qualified_max=0.30)
            )

    def test_a_non_mapping_change_rejected(self):
        with self.assertRaises(ValueError):
            validate_modification("adiabatic-length-change")

    def test_asking_for_a_span_on_a_fixed_grade_change_rejected(self):
        with self.assertRaises(ValueError):
            within_qualified_span(NEW_WICK)


class SpanTests(unittest.TestCase):
    def test_a_value_inside_the_span_is_inside(self):
        self.assertTrue(within_qualified_span(SHORTER_ADIABATIC))

    def test_a_value_above_the_span_is_outside(self):
        self.assertFalse(within_qualified_span(OVERLONG_EVAPORATOR))

    def test_a_value_exactly_on_the_lower_bound_is_inside(self):
        self.assertTrue(
            within_qualified_span(_mod(SHORTER_ADIABATIC, value=0.30))
        )

    def test_a_value_exactly_on_the_upper_bound_is_inside(self):
        self.assertTrue(
            within_qualified_span(_mod(SHORTER_ADIABATIC, value=0.60))
        )

    def test_a_value_a_representation_error_past_the_bound_is_inside(self):
        # 0.1 + 0.2 lands one unit in the last place above 0.3.
        drifted = _mod(SHORTER_ADIABATIC, value=0.1 + 0.2, qualified_max=0.3)
        self.assertTrue(within_qualified_span(drifted))


class DispositionTests(unittest.TestCase):
    def test_an_in_span_adiabatic_change_is_accepted_as_is(self):
        graded = disposition_for(SHORTER_ADIABATIC)
        self.assertEqual(graded["disposition"], ACCEPT_AS_IS)
        self.assertEqual(graded["added_tests"], ())

    def test_an_in_span_evaporator_change_takes_a_delta_acceptance(self):
        graded = disposition_for(LONGER_EVAPORATOR)
        self.assertEqual(graded["disposition"], DELTA_ACCEPTANCE)
        self.assertIn("transport-capability-test", graded["added_tests"])

    def test_an_out_of_span_evaporator_change_returns_to_qualification(self):
        graded = disposition_for(OVERLONG_EVAPORATOR)
        self.assertEqual(graded["disposition"], REQUALIFICATION)
        self.assertEqual(graded["added_tests"], ())

    def test_a_wick_change_returns_to_qualification_whatever_the_numbers(self):
        self.assertEqual(disposition_for(NEW_WICK)["disposition"], REQUALIFICATION)

    def test_a_fluid_change_returns_to_qualification(self):
        self.assertEqual(
            disposition_for({"type": "working-fluid-change"})["disposition"],
            REQUALIFICATION,
        )

    def test_a_finish_change_is_accepted_as_is(self):
        self.assertEqual(disposition_for(NEW_FINISH)["disposition"], ACCEPT_AS_IS)

    def test_a_mounting_interface_change_adds_a_conductance_test(self):
        graded = disposition_for({"type": "mounting-interface-change"})
        self.assertEqual(graded["disposition"], DELTA_ACCEPTANCE)
        self.assertIn("interface-conductance-test", graded["added_tests"])

    def test_a_fixed_grade_change_reports_no_span_verdict(self):
        self.assertIsNone(disposition_for(NEW_FINISH)["within_span"])


class MostOnerousTests(unittest.TestCase):
    def test_an_empty_set_is_accepted_as_is(self):
        self.assertEqual(most_onerous(()), ACCEPT_AS_IS)

    def test_a_delta_beats_an_accept_as_is(self):
        self.assertEqual(
            most_onerous((ACCEPT_AS_IS, DELTA_ACCEPTANCE)), DELTA_ACCEPTANCE
        )

    def test_a_requalification_beats_everything(self):
        self.assertEqual(
            most_onerous((DELTA_ACCEPTANCE, REQUALIFICATION, ACCEPT_AS_IS)),
            REQUALIFICATION,
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            most_onerous((ACCEPT_AS_IS, "waived"))

    def test_a_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            most_onerous(ACCEPT_AS_IS)


class TestSetTests(unittest.TestCase):
    def test_the_baseline_survives_with_no_modification(self):
        self.assertEqual(
            acceptance_test_set(()), tuple(sorted(BASELINE_ACCEPTANCE_TESTS))
        )

    def test_a_delta_change_adds_its_test(self):
        graded = [disposition_for(LONGER_EVAPORATOR)]
        self.assertIn("transport-capability-test", acceptance_test_set(graded))

    def test_an_added_test_already_in_the_baseline_is_not_duplicated(self):
        graded = [
            disposition_for(
                {
                    "type": "envelope-wall-thickness-change",
                    "value": 0.8e-3,
                    "qualified_min": 0.6e-3,
                    "qualified_max": 1.2e-3,
                }
            )
        ]
        tests = acceptance_test_set(graded)
        self.assertEqual(len(tests), len(set(tests)))

    def test_a_requalification_change_adds_no_acceptance_test(self):
        graded = [disposition_for(OVERLONG_EVAPORATOR)]
        self.assertEqual(
            acceptance_test_set(graded), tuple(sorted(BASELINE_ACCEPTANCE_TESTS))
        )

    def test_an_empty_baseline_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_test_set((), baseline=())


class AcceptanceLevelTests(unittest.TestCase):
    def test_levels_inside_the_qualified_envelope_pass(self):
        audit = audit_acceptance_levels(ACCEPTANCE_LEVELS, QUALIFICATION_LEVELS)
        self.assertTrue(audit["inside_qualified_envelope"])
        self.assertEqual(audit["findings"], [])

    def test_levels_exactly_on_the_qualified_envelope_pass(self):
        audit = audit_acceptance_levels(QUALIFICATION_LEVELS, QUALIFICATION_LEVELS)
        self.assertTrue(audit["inside_qualified_envelope"])

    def test_a_colder_acceptance_limit_is_a_finding(self):
        acceptance = dict(ACCEPTANCE_LEVELS)
        acceptance["min_k"] = 240.0
        audit = audit_acceptance_levels(acceptance, QUALIFICATION_LEVELS)
        self.assertTrue(any("cold limit" in f for f in audit["findings"]))

    def test_an_acceptance_density_above_the_qualified_one_is_a_finding(self):
        acceptance = dict(ACCEPTANCE_LEVELS)
        acceptance["asd_g2_per_hz"] = 0.12
        audit = audit_acceptance_levels(acceptance, QUALIFICATION_LEVELS)
        self.assertTrue(any("density" in f for f in audit["findings"]))

    def test_a_missing_acceptance_density_rejected(self):
        acceptance = dict(ACCEPTANCE_LEVELS)
        del acceptance["asd_g2_per_hz"]
        with self.assertRaises(ValueError):
            audit_acceptance_levels(acceptance, QUALIFICATION_LEVELS)

    def test_non_mapping_levels_rejected(self):
        with self.assertRaises(ValueError):
            audit_acceptance_levels("258 to 328 K", QUALIFICATION_LEVELS)


class ApplyTests(unittest.TestCase):
    def test_a_permitted_set_delivers_as_acceptance_hardware(self):
        result = apply_acceptance_principles(BASE_CASE)
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)
        self.assertTrue(result["deliverable_as_acceptance_hardware"])
        self.assertEqual(result["findings"], [])

    def test_a_delta_change_raises_the_disposition_but_stays_deliverable(self):
        result = apply_acceptance_principles(
            _case(BASE_CASE, modifications=(SHORTER_ADIABATIC, LONGER_EVAPORATOR))
        )
        self.assertEqual(result["disposition"], DELTA_ACCEPTANCE)
        self.assertTrue(result["deliverable_as_acceptance_hardware"])
        self.assertIn("transport-capability-test", result["acceptance_tests"])

    def test_a_wick_change_blocks_delivery_as_acceptance_hardware(self):
        result = apply_acceptance_principles(
            _case(BASE_CASE, modifications=(NEW_WICK,))
        )
        self.assertEqual(result["disposition"], REQUALIFICATION)
        self.assertFalse(result["deliverable_as_acceptance_hardware"])
        self.assertTrue(any("wick-structure-change" in f for f in result["findings"]))

    def test_an_out_of_envelope_acceptance_level_blocks_delivery(self):
        acceptance = dict(ACCEPTANCE_LEVELS)
        acceptance["max_k"] = 345.0
        result = apply_acceptance_principles(
            _case(BASE_CASE, acceptance_levels=acceptance)
        )
        self.assertFalse(result["deliverable_as_acceptance_hardware"])
        self.assertTrue(any("hot limit" in f for f in result["findings"]))

    def test_an_article_with_no_modification_keeps_the_baseline_tests(self):
        result = apply_acceptance_principles(_case(BASE_CASE, modifications=()))
        self.assertEqual(
            result["acceptance_tests"], tuple(sorted(BASELINE_ACCEPTANCE_TESTS))
        )

    def test_a_missing_article_name_rejected(self):
        case = _case(BASE_CASE)
        del case["article"]
        with self.assertRaises(ValueError):
            apply_acceptance_principles(case)

    def test_an_unknown_modification_type_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_principles(
                _case(BASE_CASE, modifications=({"type": "polished"},))
            )

    def test_a_non_sequence_modification_list_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_principles(
                _case(BASE_CASE, modifications="wick-structure-change")
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_principles("flight unit 004")


if __name__ == "__main__":
    unittest.main()
