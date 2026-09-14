"""Contract tests for the clause 5.3.1 class 2 purchasing-control logic."""

import unittest

from q6013_class_2_procurement_overview_logic import (
    BASE_CONTROLS,
    CHANNEL_EXTRA_CONTROLS,
    COVERAGE_TOLERANCE,
    PROJECT_ROLES,
    SUPPLY_CHANNELS,
    assess_procurement_overview,
    collect_assignments,
    control_register,
    coverage_figures,
    grade_control,
    validate_channel,
    validate_control_assignment,
    validate_coverage_policy,
)

POLICY = {"coverage_floor": 0.8, "delegation_credit": 0.7}


def _held(control, owner="procurement-officer", evidence="PO-2291 file note"):
    return {"control": control, "owner": owner, "evidence": evidence}


def _delegated(control, clause="order clause 12", certificate="CoC 44817"):
    return {
        "control": control,
        "owner": "supplier",
        "flow_down_clause": clause,
        "supplier_certificate": certificate,
    }


def _assignments(channel="manufacturer-direct"):
    return [_held(name) for name in control_register(channel)]


def _case(**overrides):
    case = {
        "policy": dict(POLICY),
        "supply_channel": "manufacturer-direct",
        "assignments": _assignments(),
    }
    case.update(overrides)
    return case


class ChannelTests(unittest.TestCase):
    def test_channel_returned_normalized(self):
        self.assertEqual(validate_channel("Open Market Broker"), "open-market-broker")

    def test_undeclared_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(None)

    def test_unrecognized_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel("somebody on an auction site")

    def test_blank_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel("   ")

    def test_every_channel_has_a_register_entry(self):
        for channel in SUPPLY_CHANNELS:
            self.assertIn(channel, CHANNEL_EXTRA_CONTROLS)


class RegisterTests(unittest.TestCase):
    def test_direct_channel_carries_the_base_register_only(self):
        self.assertEqual(control_register("manufacturer-direct"), tuple(BASE_CONTROLS))

    def test_independent_distributor_adds_two_controls(self):
        register = control_register("independent-distributor")
        self.assertEqual(len(register), len(BASE_CONTROLS) + 2)
        self.assertIn("counterfeit-avoidance-screening", register)

    def test_open_market_register_is_the_largest(self):
        sizes = {c: len(control_register(c)) for c in SUPPLY_CHANNELS}
        self.assertEqual(max(sizes, key=lambda c: sizes[c]), "open-market-broker")

    def test_franchised_channel_adds_the_franchise_check(self):
        self.assertIn(
            "franchise-status-confirmed-at-the-order-date",
            control_register("franchised-distributor"),
        )

    def test_register_has_no_repeated_control(self):
        for channel in SUPPLY_CHANNELS:
            register = control_register(channel)
            self.assertEqual(len(set(register)), len(register), channel)


class PolicyTests(unittest.TestCase):
    def test_policy_returned_as_floats(self):
        policy = validate_coverage_policy(dict(POLICY))
        self.assertAlmostEqual(policy["delegation_credit"], 0.7, places=9)

    def test_full_delegation_credit_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverage_policy(dict(POLICY, delegation_credit=1.0))

    def test_zero_delegation_credit_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverage_policy(dict(POLICY, delegation_credit=0.0))

    def test_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverage_policy(dict(POLICY, coverage_floor=-0.1))

    def test_missing_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverage_policy({"coverage_floor": 0.8})


class AssignmentTests(unittest.TestCase):
    def test_assignment_returned_normalized(self):
        record = validate_control_assignment(
            {"control": "Lot Traceability Recorded", "owner": "Procurement Officer",
             "evidence": "PO-2291"}
        )
        self.assertEqual(record["control"], "lot-traceability-recorded")
        self.assertEqual(record["owner"], "procurement-officer")

    def test_missing_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_assignment({"control": "lot-traceability-recorded"})

    def test_non_string_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_assignment(
                {"control": "lot-traceability-recorded", "owner": "procurement-officer",
                 "evidence": 7}
            )

    def test_repeated_assignment_rejected(self):
        with self.assertRaises(ValueError):
            collect_assignments([_held("lot-traceability-recorded"),
                                 _held("lot-traceability-recorded")])

    def test_non_sequence_assignments_rejected(self):
        with self.assertRaises(ValueError):
            collect_assignments(_held("lot-traceability-recorded"))


class GradingTests(unittest.TestCase):
    def test_evidenced_project_owner_is_held(self):
        graded = grade_control(
            "lot-traceability-recorded",
            validate_control_assignment(_held("lot-traceability-recorded")),
            POLICY,
        )
        self.assertEqual(graded["state"], "held")
        self.assertAlmostEqual(graded["weight"], 1.0, places=9)

    def test_unassigned_control_is_open_for_that_reason(self):
        graded = grade_control("lot-traceability-recorded", None, POLICY)
        self.assertEqual(graded["state"], "open")
        self.assertEqual(graded["reason"], "no owner assigned")

    def test_owner_outside_the_arrangement_is_open(self):
        graded = grade_control(
            "lot-traceability-recorded",
            validate_control_assignment(
                _held("lot-traceability-recorded", owner="the shipping agent")
            ),
            POLICY,
        )
        self.assertEqual(graded["state"], "open")
        self.assertIn("no standing", graded["reason"])

    def test_assigned_without_evidence_is_open(self):
        graded = grade_control(
            "lot-traceability-recorded",
            validate_control_assignment(
                _held("lot-traceability-recorded", evidence="")
            ),
            POLICY,
        )
        self.assertEqual(graded["reason"], "assigned with no evidence cited")

    def test_delegated_control_is_credited_below_one(self):
        graded = grade_control(
            "counterfeit-avoidance-screening",
            validate_control_assignment(_delegated("counterfeit-avoidance-screening")),
            POLICY,
        )
        self.assertEqual(graded["state"], "delegated")
        self.assertAlmostEqual(graded["weight"], 0.7, places=9)

    def test_delegation_without_a_flow_down_clause_is_open(self):
        graded = grade_control(
            "counterfeit-avoidance-screening",
            validate_control_assignment(
                _delegated("counterfeit-avoidance-screening", clause="")
            ),
            POLICY,
        )
        self.assertEqual(graded["state"], "open")
        self.assertIn("flow-down", graded["reason"])

    def test_delegation_without_a_certificate_is_open(self):
        graded = grade_control(
            "counterfeit-avoidance-screening",
            validate_control_assignment(
                _delegated("counterfeit-avoidance-screening", certificate="")
            ),
            POLICY,
        )
        self.assertIn("certificate", graded["reason"])

    def test_every_project_role_can_hold_a_control(self):
        for role in PROJECT_ROLES:
            graded = grade_control(
                "lot-traceability-recorded",
                validate_control_assignment(
                    _held("lot-traceability-recorded", owner=role)
                ),
                POLICY,
            )
            self.assertEqual(graded["state"], "held", role)

    def test_empty_graded_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_figures([])


class AssessmentTests(unittest.TestCase):
    def test_fully_held_direct_buy_is_acceptable(self):
        result = assess_procurement_overview(_case())
        self.assertEqual(result["verdict"], "purchasing controls meet class 2 expectations")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["figures"]["weighted_coverage"], 1.0, places=9)

    def test_direct_register_applied_to_an_open_market_buy_leaves_controls_open(self):
        result = assess_procurement_overview(
            _case(supply_channel="open-market-broker",
                  assignments=_assignments("manufacturer-direct"))
        )
        self.assertEqual(result["verdict"], "purchasing control open")
        self.assertEqual(len(result["open_controls"]), 4)

    def test_undeclared_channel_refused_rather_than_defaulted(self):
        with self.assertRaises(ValueError):
            assess_procurement_overview(_case(supply_channel=None))

    def test_no_assignment_at_all_closes_on_not_established(self):
        result = assess_procurement_overview(_case(assignments=[]))
        self.assertEqual(result["verdict"], "purchasing controls not established")

    def test_extraneous_assignment_is_its_own_finding(self):
        assignments = _assignments() + [_held("counterfeit-avoidance-screening")]
        result = assess_procurement_overview(_case(assignments=assignments))
        self.assertEqual(result["extraneous_assignments"],
                         ["counterfeit-avoidance-screening"])
        self.assertTrue(any("does not carry" in f for f in result["findings"]))

    def test_all_controls_delegated_falls_below_the_floor_with_none_open(self):
        register = control_register("manufacturer-direct")
        result = assess_procurement_overview(
            _case(assignments=[_delegated(name) for name in register])
        )
        self.assertEqual(result["open_controls"], [])
        self.assertAlmostEqual(result["figures"]["covered_share"], 1.0, places=9)
        self.assertAlmostEqual(result["figures"]["weighted_coverage"], 0.7, places=9)
        self.assertEqual(result["verdict"], "purchasing coverage below the declared floor")

    def test_weighted_coverage_exactly_on_the_floor_passes(self):
        register = control_register("manufacturer-direct")
        result = assess_procurement_overview(
            _case(policy={"coverage_floor": 0.7, "delegation_credit": 0.7},
                  assignments=[_delegated(name) for name in register])
        )
        self.assertAlmostEqual(result["figures"]["weighted_coverage"],
                               result["policy"]["coverage_floor"], places=9)
        self.assertTrue(result["acceptable"])

    def test_mixed_held_and_delegated_buy_reports_both_lists(self):
        register = control_register("independent-distributor")
        assignments = [_held(name) for name in register[:4]] + \
                      [_delegated(name) for name in register[4:]]
        result = assess_procurement_overview(
            _case(supply_channel="independent-distributor", assignments=assignments)
        )
        self.assertEqual(len(result["delegated_controls"]), 2)
        self.assertEqual(result["open_controls"], [])

    def test_register_size_follows_the_channel(self):
        result = assess_procurement_overview(
            _case(supply_channel="open-market-broker",
                  assignments=_assignments("open-market-broker"))
        )
        self.assertEqual(result["figures"]["register_size"], 8)

    def test_every_open_control_is_named_not_only_the_first(self):
        result = assess_procurement_overview(
            _case(supply_channel="open-market-broker", assignments=[])
        )
        self.assertEqual(len(result["open_controls"]), 8)
        self.assertGreaterEqual(len(result["findings"]), 9)
        result = assess_procurement_overview(
            _case(supply_channel="open-market-broker",
                  assignments=[_held(control_register("open-market-broker")[0])])
        )
        self.assertGreaterEqual(len(result["findings"]), 7)

    def test_missing_case_key_rejected(self):
        case = _case()
        del case["assignments"]
        with self.assertRaises(ValueError):
            assess_procurement_overview(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_overview(["policy"])

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
