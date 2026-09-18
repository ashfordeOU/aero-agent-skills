#!/usr/bin/env python3
"""Contract test for the die application-approval route choice (offline)."""

import copy
import unittest

from q6012_application_approval_general_requirements_logic import (
    APPROVAL_PENDING_EVALUATION,
    APPROVAL_REUSE,
    APPROVED_FOR_INTENDED_USE,
    BOUND_DIRECTIONS,
    DEFAULT_APPROVAL_POLICY,
    DELTA_APPROVAL,
    FULL_APPLICATION_APPROVAL,
    MANDATORY_CONDITION_DIRECTIONS,
    approval_covers_usage,
    assess_condition,
    assess_usage,
    condition_margin,
    plan_application_approval,
    select_approval_route,
    validate_approval_policy,
    validate_usage_envelope,
    worst_case_value,
)

BASE_ENVELOPE = {
    "junction-temperature-c": {"limit": 125.0, "direction": "upper", "span": 100.0},
    "rf-input-power-dbm": {"limit": 20.0, "direction": "upper", "span": 20.0},
    "bias-voltage-v": {"limit": 8.0, "direction": "upper", "span": 8.0},
    "operating-frequency-max-ghz": {"limit": 40.0, "direction": "upper", "span": 20.0},
    "operating-frequency-min-ghz": {"limit": 20.0, "direction": "lower", "span": 20.0},
}

INSIDE_USAGE = {
    "junction-temperature-c": {"value": 95.0, "uncertainty": 10.0},
    "rf-input-power-dbm": {"value": 15.0, "uncertainty": 1.0},
    "bias-voltage-v": {"value": 6.0, "uncertainty": 0.2},
    "operating-frequency-max-ghz": {"value": 38.0, "uncertainty": 0.5},
    "operating-frequency-min-ghz": {"value": 23.0, "uncertainty": 0.5},
}

DIE = {"die_id": "mmic-die-1", "process_id": "process-a"}
PRIOR = {"process_id": "process-a", "envelope_id": "envelope-1"}

BASE_CASE = {
    "die": DIE,
    "approved_envelope": BASE_ENVELOPE,
    "intended_usage": INSIDE_USAGE,
    "prior_approval": PRIOR,
}


def _usage(**overrides):
    usage = copy.deepcopy(INSIDE_USAGE)
    for name, value in overrides.items():
        usage[name.replace("_", "-")] = value
    return usage


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_approval_policy(DEFAULT_APPROVAL_POLICY), DEFAULT_APPROVAL_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy("default")

    def test_policy_fraction_of_one_rejected(self):
        broken = dict(DEFAULT_APPROVAL_POLICY, delta_excursion_fraction=1.0)
        with self.assertRaises(ValueError):
            validate_approval_policy(broken)

    def test_policy_negative_fraction_rejected(self):
        broken = dict(DEFAULT_APPROVAL_POLICY, delta_excursion_fraction=-0.1)
        with self.assertRaises(ValueError):
            validate_approval_policy(broken)

    def test_policy_non_integer_condition_count_rejected(self):
        broken = dict(DEFAULT_APPROVAL_POLICY, max_delta_conditions=1.5)
        with self.assertRaises(ValueError):
            validate_approval_policy(broken)

    def test_policy_non_boolean_process_rule_rejected(self):
        broken = dict(DEFAULT_APPROVAL_POLICY, reuse_requires_same_process="yes")
        with self.assertRaises(ValueError):
            validate_approval_policy(broken)


class EnvelopeTests(unittest.TestCase):
    def test_base_envelope_validates(self):
        self.assertIs(validate_usage_envelope(BASE_ENVELOPE), BASE_ENVELOPE)

    def test_every_mandatory_condition_is_bound(self):
        for name in MANDATORY_CONDITION_DIRECTIONS:
            self.assertIn(name, BASE_ENVELOPE)

    def test_missing_mandatory_condition_rejected(self):
        broken = copy.deepcopy(BASE_ENVELOPE)
        del broken["bias-voltage-v"]
        with self.assertRaises(ValueError):
            validate_usage_envelope(broken)

    def test_wrong_direction_on_mandatory_condition_rejected(self):
        broken = copy.deepcopy(BASE_ENVELOPE)
        broken["operating-frequency-min-ghz"]["direction"] = "upper"
        with self.assertRaises(ValueError):
            validate_usage_envelope(broken)

    def test_non_positive_span_rejected(self):
        broken = copy.deepcopy(BASE_ENVELOPE)
        broken["rf-input-power-dbm"]["span"] = 0.0
        with self.assertRaises(ValueError):
            validate_usage_envelope(broken)

    def test_empty_envelope_rejected(self):
        with self.assertRaises(ValueError):
            validate_usage_envelope({})

    def test_unknown_direction_rejected(self):
        broken = copy.deepcopy(BASE_ENVELOPE)
        broken["bias-voltage-v"]["direction"] = "sideways"
        with self.assertRaises(ValueError):
            validate_usage_envelope(broken)


class WorstCaseTests(unittest.TestCase):
    def test_upper_bound_widens_upward(self):
        self.assertAlmostEqual(worst_case_value(95.0, 10.0, "upper"), 105.0, places=9)

    def test_lower_bound_widens_downward(self):
        self.assertAlmostEqual(worst_case_value(23.0, 0.5, "lower"), 22.5, places=9)

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_value(95.0, -1.0, "upper")

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_value("hot", 1.0, "upper")

    def test_direction_choice_is_closed(self):
        self.assertEqual(tuple(BOUND_DIRECTIONS), ("upper", "lower"))
        with self.assertRaises(ValueError):
            worst_case_value(1.0, 0.0, "outer")

    def test_margin_signs_follow_the_direction(self):
        self.assertAlmostEqual(condition_margin(105.0, 125.0, "upper"), 20.0, places=9)
        self.assertAlmostEqual(condition_margin(21.5, 20.0, "lower"), 1.5, places=9)


class ConditionAssessmentTests(unittest.TestCase):
    def test_inside_condition_reports_a_positive_margin(self):
        result = assess_condition(
            "junction-temperature-c",
            {"value": 95.0, "uncertainty": 10.0},
            BASE_ENVELOPE["junction-temperature-c"],
        )
        self.assertTrue(result["inside_envelope"])
        self.assertAlmostEqual(result["normalised_margin"], 0.2, places=9)
        self.assertAlmostEqual(result["excursion_fraction"], 0.0, places=9)

    def test_condition_exactly_on_the_limit_stays_inside(self):
        result = assess_condition(
            "junction-temperature-c",
            {"value": 125.0, "uncertainty": 0.0},
            BASE_ENVELOPE["junction-temperature-c"],
        )
        self.assertAlmostEqual(result["normalised_margin"], 0.0, places=9)
        self.assertTrue(result["inside_envelope"])

    def test_excursion_is_normalised_on_the_span(self):
        result = assess_condition(
            "junction-temperature-c",
            {"value": 129.0, "uncertainty": 0.0},
            BASE_ENVELOPE["junction-temperature-c"],
        )
        self.assertFalse(result["inside_envelope"])
        self.assertAlmostEqual(result["excursion_fraction"], 0.04, places=9)

    def test_missing_declared_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_condition(
                "bias-voltage-v", {}, BASE_ENVELOPE["bias-voltage-v"]
            )

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_condition("bias-voltage-v", 6.0, BASE_ENVELOPE["bias-voltage-v"])

    def test_empty_condition_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_condition(
                "", {"value": 6.0}, BASE_ENVELOPE["bias-voltage-v"]
            )


class UsageAssessmentTests(unittest.TestCase):
    def test_inside_usage_has_no_breach_and_no_gap(self):
        result = assess_usage(INSIDE_USAGE, BASE_ENVELOPE)
        self.assertEqual(result["breaches"], [])
        self.assertEqual(result["uncovered_conditions"], [])
        self.assertEqual(result["undeclared_conditions"], [])

    def test_an_unbound_condition_is_reported_as_uncovered(self):
        usage = _usage(**{"total-ionising-dose-krad": {"value": 30.0}})
        result = assess_usage(usage, BASE_ENVELOPE)
        self.assertIn("total-ionising-dose-krad", result["uncovered_conditions"])

    def test_a_missing_mandatory_condition_is_reported_as_undeclared(self):
        usage = copy.deepcopy(INSIDE_USAGE)
        del usage["bias-voltage-v"]
        result = assess_usage(usage, BASE_ENVELOPE)
        self.assertEqual(result["undeclared_conditions"], ["bias-voltage-v"])

    def test_tightest_condition_is_the_smallest_normalised_margin(self):
        result = assess_usage(INSIDE_USAGE, BASE_ENVELOPE)
        self.assertEqual(
            result["tightest"]["condition"], "operating-frequency-max-ghz"
        )

    def test_non_mapping_usage_rejected(self):
        with self.assertRaises(ValueError):
            assess_usage("hot", BASE_ENVELOPE)


class RouteTests(unittest.TestCase):
    def test_usage_inside_a_held_approval_is_reused(self):
        usage = assess_usage(INSIDE_USAGE, BASE_ENVELOPE)
        route = select_approval_route(usage, PRIOR, DIE)
        self.assertEqual(route["route"], APPROVAL_REUSE)

    def test_no_held_approval_forces_a_full_approval(self):
        usage = assess_usage(INSIDE_USAGE, BASE_ENVELOPE)
        route = select_approval_route(usage, None, DIE)
        self.assertEqual(route["route"], FULL_APPLICATION_APPROVAL)

    def test_a_different_process_forces_a_full_approval(self):
        usage = assess_usage(INSIDE_USAGE, BASE_ENVELOPE)
        route = select_approval_route(
            usage, {"process_id": "process-b"}, DIE
        )
        self.assertEqual(route["route"], FULL_APPLICATION_APPROVAL)

    def test_a_small_excursion_takes_the_delta_route(self):
        usage = assess_usage(
            _usage(junction_temperature_c={"value": 129.0, "uncertainty": 0.0}),
            BASE_ENVELOPE,
        )
        route = select_approval_route(usage, PRIOR, DIE)
        self.assertEqual(route["route"], DELTA_APPROVAL)

    def test_a_large_excursion_falls_back_to_a_full_approval(self):
        usage = assess_usage(
            _usage(junction_temperature_c={"value": 140.0, "uncertainty": 0.0}),
            BASE_ENVELOPE,
        )
        route = select_approval_route(usage, PRIOR, DIE)
        self.assertEqual(route["route"], FULL_APPLICATION_APPROVAL)

    def test_too_many_small_excursions_fall_back_to_a_full_approval(self):
        usage = assess_usage(
            _usage(
                junction_temperature_c={"value": 129.0, "uncertainty": 0.0},
                rf_input_power_dbm={"value": 20.5, "uncertainty": 0.0},
                bias_voltage_v={"value": 8.2, "uncertainty": 0.0},
            ),
            BASE_ENVELOPE,
        )
        self.assertEqual(len(usage["breaches"]), 3)
        route = select_approval_route(usage, PRIOR, DIE)
        self.assertEqual(route["route"], FULL_APPLICATION_APPROVAL)

    def test_an_uncovered_condition_blocks_reuse(self):
        usage = assess_usage(
            _usage(**{"total-ionising-dose-krad": {"value": 30.0}}), BASE_ENVELOPE
        )
        route = select_approval_route(usage, PRIOR, DIE)
        self.assertEqual(route["route"], FULL_APPLICATION_APPROVAL)
        self.assertTrue(any("total-ionising-dose-krad" in d for d in route["duties"]))

    def test_non_mapping_die_rejected(self):
        usage = assess_usage(INSIDE_USAGE, BASE_ENVELOPE)
        with self.assertRaises(ValueError):
            select_approval_route(usage, PRIOR, "mmic-die-1")


class TransferabilityTests(unittest.TestCase):
    def test_an_approval_covers_a_usage_inside_its_envelope(self):
        self.assertTrue(approval_covers_usage(BASE_ENVELOPE, INSIDE_USAGE))

    def test_an_approval_does_not_transfer_to_a_harsher_usage(self):
        harsher = _usage(junction_temperature_c={"value": 140.0, "uncertainty": 0.0})
        self.assertFalse(approval_covers_usage(BASE_ENVELOPE, harsher))

    def test_an_approval_does_not_transfer_to_a_new_condition(self):
        wider = _usage(**{"total-ionising-dose-krad": {"value": 30.0}})
        self.assertFalse(approval_covers_usage(BASE_ENVELOPE, wider))


class PlanTests(unittest.TestCase):
    def test_a_covered_application_is_approved_without_evaluation(self):
        result = plan_application_approval(BASE_CASE)
        self.assertEqual(result["verdict"], APPROVED_FOR_INTENDED_USE)
        self.assertFalse(result["evaluation_required"])
        self.assertEqual(result["open_items"], [])
        self.assertEqual(result["die_id"], "mmic-die-1")

    def test_an_excursion_leaves_the_approval_pending(self):
        case = _case(
            intended_usage=_usage(
                junction_temperature_c={"value": 129.0, "uncertainty": 0.0}
            )
        )
        result = plan_application_approval(case)
        self.assertEqual(result["verdict"], APPROVAL_PENDING_EVALUATION)
        self.assertEqual(result["route"], DELTA_APPROVAL)
        self.assertTrue(result["evaluation_required"])
        self.assertEqual(len(result["open_items"]), 1)

    def test_an_undeclared_condition_is_an_open_item_not_a_pass(self):
        usage = copy.deepcopy(INSIDE_USAGE)
        del usage["rf-input-power-dbm"]
        result = plan_application_approval(_case(intended_usage=usage))
        self.assertEqual(result["route"], FULL_APPLICATION_APPROVAL)
        self.assertTrue(any("rf-input-power-dbm" in i for i in result["open_items"]))

    def test_plan_reports_the_tightest_condition(self):
        result = plan_application_approval(BASE_CASE)
        self.assertEqual(result["tightest_condition"], "operating-frequency-max-ghz")
        self.assertAlmostEqual(
            result["tightest_normalised_margin"], 0.075, places=9
        )

    def test_plan_rejects_a_case_without_a_die_identifier(self):
        with self.assertRaises(ValueError):
            plan_application_approval(_case(die={"process_id": "process-a"}))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_application_approval("mmic-die-1")

    def test_a_weaker_data_set_never_produces_a_lighter_route(self):
        strong = plan_application_approval(BASE_CASE)
        weak = plan_application_approval(_case(prior_approval=None))
        self.assertEqual(strong["route"], APPROVAL_REUSE)
        self.assertEqual(weak["route"], FULL_APPLICATION_APPROVAL)


if __name__ == "__main__":
    unittest.main()
