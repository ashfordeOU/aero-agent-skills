"""Contract tests for the clause 5.1.3 parts control board route logic.

Each test class follows one step of the SKILL.md workflow: the input
validation, the per-record disposition, the coverage gate and the closing
verdict. Offline, stdlib unittest; run it as the review checklist before
the leaf is issued.
"""

import unittest

from q60_class_2_parts_control_board_logic import (
    BOARD_FUNCTIONS,
    DECISION_LEVELS,
    DECISION_OUTCOMES,
    MANDATORY_FUNCTIONS,
    MANDATORY_REQUEST_ATTRIBUTES,
    PART_CATEGORIES,
    QUORUM_TOLERANCE,
    approval_share,
    assess_parts_control_board,
    board_state,
    decision_turnaround,
    evaluate_request,
    level_rank,
    request_completeness,
    required_decision_level,
    seated_functions,
    validate_part_category,
    validate_request_id,
)


def board(absent=(), chair="product-assurance", minute="PCB-MIN-2026-07"):
    """Return a fully seated board minus the named functions."""
    seats = []
    for function in sorted(BOARD_FUNCTIONS):
        seats.append(
            {
                "function": function,
                "present": function not in absent,
                "proxy_accepted": False,
            }
        )
    return {"seats": seats, "chair_function": chair, "minute_reference": minute}


def request(category="non-standard-part", **overrides):
    """Return one clean submission of the given part category."""
    base = {
        "request_id": "PCB-R-001",
        "part_reference": "CAP-X7R-100N",
        "part_category": category,
        "decision": "approved",
        "route_taken": PART_CATEGORIES[category],
        "submitted_day": 10,
        "decision_day": 24,
        "data_package_complete": True,
        "evaluation_reference": "EVAL-REP-33",
        "customer_agreement_reference": "CUST-AGR-9",
        "procurement_commitment_day": 30,
    }
    base.update(overrides)
    return base


def state(**kwargs):
    return board_state(board(**kwargs))


class ValidationTests(unittest.TestCase):
    def test_request_id_is_stripped(self):
        self.assertEqual(validate_request_id("  PCB-R-001 "), "PCB-R-001")

    def test_blank_request_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_request_id("  ")

    def test_category_is_canonicalized(self):
        self.assertEqual(
            validate_part_category("WAIVER-REQUEST"), "waiver-request"
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_category("something-from-the-drawer")

    def test_every_category_maps_to_a_known_level(self):
        for category, level in PART_CATEGORIES.items():
            self.assertIn(level, DECISION_LEVELS)
            self.assertEqual(required_decision_level(category), level)

    def test_level_rank_orders_the_route(self):
        self.assertLess(
            level_rank("chair-delegated"), level_rank("board-decision")
        )
        self.assertLess(
            level_rank("board-decision"),
            level_rank("board-decision-with-customer-agreement"),
        )

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            level_rank("a-quick-word-in-the-corridor")

    def test_mandatory_functions_sit_inside_the_board(self):
        for function in MANDATORY_FUNCTIONS:
            self.assertIn(function, BOARD_FUNCTIONS)

    def test_every_outcome_answers_a_boolean(self):
        for outcome, usable in DECISION_OUTCOMES.items():
            self.assertIsInstance(usable, bool)
            self.assertTrue(outcome.strip())


class BoardStateTests(unittest.TestCase):
    def test_full_board_reaches_quorum_one(self):
        self.assertAlmostEqual(state()["quorum"], 1.0, places=9)

    def test_proxy_counts_as_a_seat(self):
        seats = board()["seats"]
        for seat in seats:
            if seat["function"] == "design-authority":
                seat["present"] = False
                seat["proxy_accepted"] = True
        seated = seated_functions(
            {"seats": seats, "chair_function": "product-assurance"}
        )
        self.assertIn("design-authority", seated)

    def test_absent_mandatory_function_is_named(self):
        current = state(absent=("design-authority",))
        self.assertEqual(
            current["absent_mandatory_functions"], ("design-authority",)
        )
        self.assertAlmostEqual(current["quorum"], 2 / 3, places=9)

    def test_absent_supporting_function_does_not_move_quorum(self):
        self.assertAlmostEqual(state(absent=("procurement",))["quorum"], 1.0, places=9)

    def test_chair_seated_flag_follows_attendance(self):
        self.assertFalse(state(absent=("product-assurance",))["chair_seated"])

    def test_duplicate_seat_rejected(self):
        seats = board()["seats"]
        seats.append(dict(seats[0]))
        with self.assertRaises(ValueError):
            seated_functions({"seats": seats, "chair_function": "product-assurance"})

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            seated_functions(
                {"seats": [{"function": "catering", "present": True}]}
            )

    def test_empty_seat_list_rejected(self):
        with self.assertRaises(ValueError):
            seated_functions({"seats": []})

    def test_unknown_chair_rejected(self):
        with self.assertRaises(ValueError):
            board_state(board(chair="catering"))


class CompletenessAndTurnaroundTests(unittest.TestCase):
    def test_complete_request_scores_one(self):
        missing, fraction = request_completeness(request())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_blank_part_reference_counts_as_missing(self):
        missing, fraction = request_completeness(request(part_reference="  "))
        self.assertIn("part_reference", missing)
        self.assertAlmostEqual(
            fraction,
            (len(MANDATORY_REQUEST_ATTRIBUTES) - 1)
            / len(MANDATORY_REQUEST_ATTRIBUTES),
            places=9,
        )

    def test_turnaround_counts_the_days_waited(self):
        self.assertEqual(decision_turnaround(10, 24), 14)

    def test_same_day_decision_is_zero_days(self):
        self.assertEqual(decision_turnaround(10, 10), 0)

    def test_decision_before_submission_rejected(self):
        with self.assertRaises(ValueError):
            decision_turnaround(24, 10)

    def test_negative_day_rejected(self):
        with self.assertRaises(ValueError):
            decision_turnaround(-1, 10)


class EvaluateRequestTests(unittest.TestCase):
    def setUp(self):
        self.state = state()

    def evaluate(self, entry, current=None, limit=30, floor=1.0, seen=()):
        return evaluate_request(entry, current or self.state, limit, floor, seen)

    def test_clean_board_decision_is_accepted(self):
        record = self.evaluate(request())
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["usable"])

    def test_incomplete_record_stops_before_routing(self):
        record = self.evaluate(request(decision=None))
        self.assertEqual(record["disposition"], "record-incomplete")

    def test_approved_range_part_may_be_chair_delegated(self):
        record = self.evaluate(request("approved-range-part"))
        self.assertEqual(record["disposition"], "accepted")

    def test_chair_delegation_below_the_required_level_is_refused(self):
        record = self.evaluate(
            request("non-standard-part", route_taken="chair-delegated")
        )
        self.assertEqual(record["disposition"], "route-below-required-level")

    def test_a_higher_route_than_needed_is_allowed(self):
        record = self.evaluate(
            request(
                "non-standard-part",
                route_taken="board-decision-with-customer-agreement",
            )
        )
        self.assertEqual(record["disposition"], "accepted")

    def test_board_decision_without_quorum_is_refused(self):
        record = self.evaluate(
            request(), current=state(absent=("design-authority",))
        )
        self.assertEqual(record["disposition"], "quorum-not-met")

    def test_chair_delegation_needs_the_chair_to_have_sat(self):
        record = self.evaluate(
            request("approved-range-part"),
            current=state(absent=("product-assurance",)),
        )
        self.assertEqual(record["disposition"], "quorum-not-met")

    def test_board_decision_without_a_minute_is_refused(self):
        record = self.evaluate(request(), current=state(minute="  "))
        self.assertEqual(record["disposition"], "minute-reference-absent")

    def test_evaluation_category_without_evidence_is_refused(self):
        record = self.evaluate(
            request("part-requiring-evaluation", evaluation_reference="")
        )
        self.assertEqual(record["disposition"], "evaluation-evidence-absent")

    def test_waiver_without_customer_agreement_is_refused(self):
        record = self.evaluate(
            request("waiver-request", customer_agreement_reference=None)
        )
        self.assertEqual(record["disposition"], "customer-agreement-absent")

    def test_incomplete_data_package_is_refused(self):
        record = self.evaluate(request(data_package_complete=False))
        self.assertEqual(record["disposition"], "data-package-incomplete")

    def test_part_committed_before_the_decision_is_refused(self):
        record = self.evaluate(request(procurement_commitment_day=20))
        self.assertEqual(record["disposition"], "committed-before-decision")

    def test_late_decision_is_flagged_against_the_turnaround(self):
        record = self.evaluate(
            request(decision_day=60, procurement_commitment_day=70), limit=30
        )
        self.assertEqual(record["disposition"], "turnaround-exceeded")

    def test_a_rejected_part_closes_without_a_finding(self):
        record = self.evaluate(request(decision="rejected"))
        self.assertEqual(record["disposition"], "closed-not-usable")
        self.assertFalse(record["usable"])

    def test_unrecognised_outcome_is_named(self):
        record = self.evaluate(request(decision="probably-fine"))
        self.assertEqual(record["disposition"], "outcome-unrecognised")

    def test_unrecognised_route_is_named(self):
        record = self.evaluate(request(route_taken="corridor-nod"))
        self.assertEqual(record["disposition"], "route-unrecognised")

    def test_unrecognised_category_is_named(self):
        record = self.evaluate(request(part_category="drawer-stock"))
        self.assertEqual(record["disposition"], "category-unrecognised")

    def test_decision_dated_before_submission_is_named(self):
        record = self.evaluate(request(submitted_day=40, decision_day=12))
        self.assertEqual(record["disposition"], "decision-before-submission")

    def test_repeat_reference_is_a_duplicate(self):
        record = self.evaluate(request(), seen={"PCB-R-001"})
        self.assertEqual(record["disposition"], "duplicate-request")

    def test_non_board_state_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_request(request(), {"not": "a state"}, 30, 1.0)


class ApprovalShareTests(unittest.TestCase):
    def setUp(self):
        self.state = state()

    def test_all_approved_gives_one(self):
        records = [
            evaluate_request(request(), self.state, 30, 1.0),
            evaluate_request(
                request("approved-range-part", request_id="PCB-R-002"),
                self.state,
                30,
                1.0,
            ),
        ]
        self.assertAlmostEqual(approval_share(records), 1.0, places=9)

    def test_a_rejection_lowers_the_share(self):
        records = [
            evaluate_request(request(), self.state, 30, 1.0),
            evaluate_request(
                request(request_id="PCB-R-002", decision="rejected"),
                self.state,
                30,
                1.0,
            ),
        ]
        self.assertAlmostEqual(approval_share(records), 0.5, places=9)

    def test_unroutable_records_leave_the_denominator(self):
        records = [
            evaluate_request(request(), self.state, 30, 1.0),
            evaluate_request(request(decision=None), self.state, 30, 1.0),
        ]
        self.assertAlmostEqual(approval_share(records), 1.0, places=9)

    def test_no_routable_record_is_refused(self):
        records = [evaluate_request(request(decision=None), self.state, 30, 1.0)]
        with self.assertRaises(ValueError):
            approval_share(records)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            approval_share([])


class AssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        base = {
            "board": board(),
            "requests": [request()],
            "turnaround_days": 30,
            "required_quorum": 1.0,
        }
        base.update(overrides)
        return base

    def test_clean_board_route_is_sound(self):
        result = assess_parts_control_board(self.spec())
        self.assertTrue(result["route_sound"])
        self.assertEqual(result["verdict"], "board route sound")
        self.assertEqual(result["approved_parts"], ("CAP-X7R-100N",))

    def test_a_short_route_stops_the_verdict(self):
        result = assess_parts_control_board(
            self.spec(requests=[request(route_taken="chair-delegated")])
        )
        self.assertFalse(result["route_sound"])
        self.assertEqual(
            result["findings"][0]["disposition"], "route-below-required-level"
        )

    def test_findings_are_ranked_most_severe_first(self):
        requests = [
            request(request_id="PCB-R-001", data_package_complete=False),
            request(request_id="PCB-R-002", decision=None),
            request(request_id="PCB-R-003", decision_day=90),
        ]
        result = assess_parts_control_board(self.spec(requests=requests))
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_reduced_quorum_floor_admits_a_missing_seat(self):
        result = assess_parts_control_board(
            self.spec(board=board(absent=("design-authority",)), required_quorum=2 / 3)
        )
        self.assertTrue(result["route_sound"])
        self.assertAlmostEqual(
            result["board"]["quorum"], result["required_quorum"], places=9
        )

    def test_empty_request_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(self.spec(requests=[]))

    def test_missing_key_rejected(self):
        spec = self.spec()
        del spec["board"]
        with self.assertRaises(ValueError):
            assess_parts_control_board(spec)

    def test_out_of_range_quorum_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(self.spec(required_quorum=1.5))

    def test_negative_turnaround_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(self.spec(turnaround_days=-5))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board("the board met on Tuesday")

    def test_tolerance_is_small_enough_to_be_representation_error(self):
        self.assertLess(QUORUM_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
