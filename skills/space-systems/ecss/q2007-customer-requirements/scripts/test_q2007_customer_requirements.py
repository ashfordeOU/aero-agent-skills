#!/usr/bin/env python3
"""Gate 3 contract test for q2007-customer-requirements.

stdlib unittest, offline, deterministic. Run:
    python3 test_q2007_customer_requirements.py
"""

import unittest

from q2007_customer_requirements_logic import (
    DECISION_ACCEPTED,
    DECISION_ACCEPTED_WITH_ACTIONS,
    DECISION_REFUSED,
    FEASIBLE,
    INFEASIBLE,
    UNCHARACTERISED,
    capacity_is_available,
    commitment_decision,
    evaluate_customer_requirements,
    missing_content,
    parameter_feasibility,
    safety_input_findings,
    validate_envelope,
    validate_request,
)

ENVELOPE = {
    "vibration_grms": (2.0, 20.0),
    "chamber_temperature_c": (-180.0, 150.0),
    "vacuum_pa": (1e-6, 1.0),
}


def good_request(**over):
    record = {
        "request_id": "TR-0041",
        "customer": "prime-contractor",
        "test_objective": "qualification of a deployment hinge",
        "specimen_identification": "hinge assembly, two units",
        "acceptance_criteria": "no loss of deployment torque margin",
        "deliverables": "test report and raw channel data",
        "requested_parameters": {
            "vibration_grms": 12.0,
            "chamber_temperature_c": -120.0,
            "vacuum_pa": 1e-4,
        },
        "requested_weeks": 3.0,
        "window_weeks": 8.0,
        "hazardous_specimen": False,
        "safety_data_supplied": True,
        "safety_measures": [],
        "declared_hazards": [],
    }
    record.update(over)
    return record


class TestRequestValidation(unittest.TestCase):
    def test_good_request_normalizes(self):
        request = validate_request(good_request())
        self.assertEqual(request["request_id"], "TR-0041")
        self.assertAlmostEqual(request["requested_weeks"], 3.0, places=9)

    def test_non_mapping_request_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(["not", "a", "mapping"])

    def test_blank_customer_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(good_request(customer="   "))

    def test_empty_parameter_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(good_request(requested_parameters={}))

    def test_non_numeric_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(
                good_request(requested_parameters={"vibration_grms": "high"})
            )

    def test_zero_requested_weeks_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(good_request(requested_weeks=0.0))

    def test_duration_longer_than_the_window_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(good_request(requested_weeks=9.0, window_weeks=8.0))

    def test_duration_exactly_filling_the_window_is_accepted(self):
        request = validate_request(good_request(requested_weeks=8.0, window_weeks=8.0))
        self.assertAlmostEqual(request["requested_weeks"], request["window_weeks"], places=9)

    def test_non_boolean_hazard_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request(good_request(hazardous_specimen="yes"))

    def test_safety_measures_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_request(good_request(safety_measures="bonded to ground"))


class TestMissingContent(unittest.TestCase):
    def test_complete_request_has_no_gaps(self):
        self.assertEqual(missing_content(validate_request(good_request())), [])

    def test_absent_item_is_reported(self):
        record = good_request()
        del record["deliverables"]
        self.assertEqual(missing_content(validate_request(record)), ["deliverables"])

    def test_whitespace_only_item_counts_as_missing(self):
        gaps = missing_content(validate_request(good_request(test_objective="   ")))
        self.assertEqual(gaps, ["test_objective"])

    def test_gaps_are_returned_sorted(self):
        gaps = missing_content(
            validate_request(good_request(test_objective="", acceptance_criteria=""))
        )
        self.assertEqual(gaps, ["acceptance_criteria", "test_objective"])

    def test_empty_required_set_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_content(validate_request(good_request()), required=[])


class TestEnvelopeFeasibility(unittest.TestCase):
    def test_envelope_pair_must_be_ordered(self):
        with self.assertRaises(ValueError):
            validate_envelope({"vibration_grms": (20.0, 2.0)})

    def test_envelope_entry_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            validate_envelope({"vibration_grms": (2.0, 10.0, 20.0)})

    def test_parameter_inside_the_envelope_is_feasible(self):
        scored = parameter_feasibility({"vibration_grms": 12.0}, ENVELOPE)
        self.assertEqual(scored["vibration_grms"]["status"], FEASIBLE)

    def test_parameter_above_the_envelope_is_infeasible(self):
        scored = parameter_feasibility({"vibration_grms": 24.0}, ENVELOPE)
        self.assertEqual(scored["vibration_grms"]["status"], INFEASIBLE)

    def test_parameter_below_the_envelope_is_infeasible(self):
        scored = parameter_feasibility({"vibration_grms": 0.5}, ENVELOPE)
        self.assertEqual(scored["vibration_grms"]["status"], INFEASIBLE)

    def test_parameter_exactly_on_the_upper_bound_is_feasible_with_zero_margin(self):
        scored = parameter_feasibility({"vibration_grms": 20.0}, ENVELOPE)
        self.assertEqual(scored["vibration_grms"]["status"], FEASIBLE)
        self.assertAlmostEqual(scored["vibration_grms"]["margin_fraction"], 0.0, places=9)

    def test_midpoint_parameter_reports_half_the_span_as_margin(self):
        scored = parameter_feasibility({"vibration_grms": 11.0}, ENVELOPE)
        self.assertAlmostEqual(scored["vibration_grms"]["margin_fraction"], 0.5, places=9)

    def test_unlisted_parameter_is_uncharacterised_not_a_pass(self):
        scored = parameter_feasibility({"acoustic_db": 145.0}, ENVELOPE)
        self.assertEqual(scored["acoustic_db"]["status"], UNCHARACTERISED)
        self.assertIsNone(scored["acoustic_db"]["margin_fraction"])

    def test_empty_request_set_is_rejected(self):
        with self.assertRaises(ValueError):
            parameter_feasibility({}, ENVELOPE)


class TestCapacity(unittest.TestCase):
    def test_enough_free_weeks_is_available(self):
        self.assertTrue(capacity_is_available(3.0, 4.0))

    def test_exactly_enough_free_weeks_is_available(self):
        self.assertTrue(capacity_is_available(3.0, 3.0))

    def test_too_few_free_weeks_is_not_available(self):
        self.assertFalse(capacity_is_available(3.0, 2.0))

    def test_negative_free_weeks_is_rejected(self):
        with self.assertRaises(ValueError):
            capacity_is_available(3.0, -1.0)


class TestSafetyInput(unittest.TestCase):
    def test_non_hazardous_and_consistent_has_no_findings(self):
        self.assertEqual(safety_input_findings(validate_request(good_request())), [])

    def test_hazardous_without_data_is_a_finding(self):
        findings = safety_input_findings(
            validate_request(
                good_request(
                    hazardous_specimen=True,
                    safety_data_supplied=False,
                    safety_measures=["vented enclosure"],
                )
            )
        )
        self.assertEqual(len(findings), 1)

    def test_hazardous_without_measures_is_a_finding(self):
        findings = safety_input_findings(
            validate_request(
                good_request(hazardous_specimen=True, safety_data_supplied=True)
            )
        )
        self.assertEqual(len(findings), 1)

    def test_hazards_against_a_non_hazardous_item_is_a_contradiction(self):
        findings = safety_input_findings(
            validate_request(good_request(declared_hazards=["pyrotechnic initiator"]))
        )
        self.assertEqual(len(findings), 1)


class TestCommitmentDecision(unittest.TestCase):
    def test_clean_review_accepts(self):
        self.assertEqual(commitment_decision([], [], True, []), DECISION_ACCEPTED)

    def test_content_gap_accepts_against_actions(self):
        self.assertEqual(
            commitment_decision(["deliverables"], [], True, []),
            DECISION_ACCEPTED_WITH_ACTIONS,
        )

    def test_infeasible_parameter_refuses(self):
        self.assertEqual(
            commitment_decision([], ["vibration_grms"], True, []), DECISION_REFUSED
        )

    def test_no_capacity_refuses(self):
        self.assertEqual(commitment_decision([], [], False, []), DECISION_REFUSED)

    def test_non_boolean_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            commitment_decision([], [], "yes", [])


class TestFullReview(unittest.TestCase):
    def test_clean_request_is_accepted(self):
        report = evaluate_customer_requirements(good_request(), ENVELOPE, 4.0)
        self.assertEqual(report["decision"], DECISION_ACCEPTED)
        self.assertEqual(report["actions"], [])
        self.assertEqual(report["refusal_reasons"], [])

    def test_missing_content_becomes_a_customer_action(self):
        report = evaluate_customer_requirements(
            good_request(acceptance_criteria=""), ENVELOPE, 4.0
        )
        self.assertEqual(report["decision"], DECISION_ACCEPTED_WITH_ACTIONS)
        self.assertEqual(len(report["actions"]), 1)

    def test_unknown_parameter_becomes_a_centre_action_not_a_refusal(self):
        request = good_request()
        request["requested_parameters"]["acoustic_db"] = 145.0
        report = evaluate_customer_requirements(request, ENVELOPE, 4.0)
        self.assertEqual(report["decision"], DECISION_ACCEPTED_WITH_ACTIONS)
        self.assertEqual(report["uncharacterised_parameters"], ["acoustic_db"])
        self.assertEqual(report["refusal_reasons"], [])

    def test_out_of_envelope_parameter_refuses_with_a_reason(self):
        request = good_request()
        request["requested_parameters"]["vibration_grms"] = 31.0
        report = evaluate_customer_requirements(request, ENVELOPE, 4.0)
        self.assertEqual(report["decision"], DECISION_REFUSED)
        self.assertEqual(report["infeasible_parameters"], ["vibration_grms"])
        self.assertEqual(len(report["refusal_reasons"]), 1)

    def test_capacity_shortfall_refuses_separately_from_capability(self):
        report = evaluate_customer_requirements(good_request(), ENVELOPE, 1.0)
        self.assertEqual(report["decision"], DECISION_REFUSED)
        self.assertEqual(report["infeasible_parameters"], [])
        self.assertFalse(report["capacity_is_available"])

    def test_hazardous_specimen_without_data_carries_a_safety_action(self):
        report = evaluate_customer_requirements(
            good_request(hazardous_specimen=True, safety_data_supplied=False),
            ENVELOPE,
            4.0,
        )
        self.assertEqual(report["decision"], DECISION_ACCEPTED_WITH_ACTIONS)
        self.assertEqual(len(report["safety_findings"]), 2)

    def test_review_propagates_a_request_error(self):
        with self.assertRaises(ValueError):
            evaluate_customer_requirements(good_request(customer=""), ENVELOPE, 4.0)


if __name__ == "__main__":
    unittest.main()
