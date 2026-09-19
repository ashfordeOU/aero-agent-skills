#!/usr/bin/env python3
"""Contract tests for the test-centre management system of clause 5.1.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy, a
system never established, a scope that misses an offered service, a
process covering a scoped service without an approval, coverage short of
the required fraction, a stalled continual-improvement loop, a closure
nobody verified, a process past its review age and a management review
that has gone stale.
"""

import unittest

from q2007_management_system_logic import (
    DEFAULT_SYSTEM_POLICY,
    IMPROVEMENT_LOOP_STALLED,
    MANAGEMENT_REVIEW_STALE,
    PROCESS_APPROVAL_BROKEN,
    PROCESS_APPROVED,
    PROCESS_COVERAGE_INSUFFICIENT,
    PROCESS_DRAFT,
    PROCESS_WITHDRAWN,
    SCOPE_INCOMPLETE,
    SYSTEM_ABSENT,
    SYSTEM_ESTABLISHED,
    assess_management_system,
    at_least,
    improvement_closure,
    management_review_is_current,
    open_improvement_actions,
    process_coverage,
    processes_past_review,
    scope_gaps,
    scope_overreach,
    services_in_scope,
    uncovered_services,
    unapproved_processes_in_use,
    unverified_closures,
    validate_improvement_action,
    validate_process,
    validate_system,
    validate_system_policy,
)

SERVICES = ["thermal-vacuum-test", "vibration-test", "emc-test"]


def _process(process_id="PRC-TVAC", covers=None, **overrides):
    record = {
        "process_id": process_id,
        "state": PROCESS_APPROVED,
        "covers_services": list(covers or ["thermal-vacuum-test"]),
        "approved_on_day": 400,
        "last_reviewed_day": 800,
    }
    record.update(overrides)
    return record


def _action(action_id="IMP-01", **overrides):
    record = {
        "action_id": action_id,
        "raised_on_day": 700,
        "closed_on_day": 760,
        "effectiveness_verified": True,
    }
    record.update(overrides)
    return record


def _system(**overrides):
    record = {
        "established": True,
        "declared_scope": list(SERVICES),
        "services_offered": list(SERVICES),
        "processes": [
            _process("PRC-TVAC", ["thermal-vacuum-test"]),
            _process("PRC-VIB", ["vibration-test"]),
            _process("PRC-EMC", ["emc-test"]),
        ],
        "improvement_actions": [_action("IMP-01"), _action("IMP-02")],
        "last_management_review_day": 900,
        "as_of_day": 1000,
    }
    record.update(overrides)
    return record


def _case(**overrides):
    case = {"system": _system(), "policy": dict(DEFAULT_SYSTEM_POLICY)}
    case.update(overrides)
    return case


class SystemPolicyValidation(unittest.TestCase):
    def test_default_policy_round_trips(self):
        rules = validate_system_policy({})
        self.assertAlmostEqual(rules["min_process_coverage"], 1.0, places=9)
        self.assertEqual(rules["management_review_interval_days"], 365)

    def test_unrecognised_policy_key_refused(self):
        with self.assertRaises(ValueError):
            validate_system_policy({"min_coverage": 0.9})

    def test_coverage_outside_zero_to_one_refused(self):
        with self.assertRaises(ValueError):
            validate_system_policy({"min_process_coverage": 1.4})

    def test_non_whole_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_system_policy({"management_review_interval_days": 30.5})

    def test_process_review_shorter_than_management_review_refused(self):
        with self.assertRaises(ValueError):
            validate_system_policy(
                {"process_review_interval_days": 90, "management_review_interval_days": 365}
            )

    def test_non_boolean_verification_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_system_policy({"require_effectiveness_verification": "yes"})


class RecordValidation(unittest.TestCase):
    def test_process_missing_field_refused(self):
        bad = _process()
        del bad["covers_services"]
        with self.assertRaises(ValueError):
            validate_process(bad)

    def test_unrecognised_process_state_refused(self):
        with self.assertRaises(ValueError):
            validate_process(_process(state="in-review"))

    def test_approved_process_without_approval_day_refused(self):
        with self.assertRaises(ValueError):
            validate_process(_process(approved_on_day=None))

    def test_draft_process_without_approval_day_accepted(self):
        record = validate_process(_process(state=PROCESS_DRAFT, approved_on_day=None))
        self.assertEqual(record["state"], PROCESS_DRAFT)

    def test_action_closed_before_raised_refused(self):
        with self.assertRaises(ValueError):
            validate_improvement_action(_action(raised_on_day=700, closed_on_day=650))

    def test_verified_effectiveness_without_closure_refused(self):
        with self.assertRaises(ValueError):
            validate_improvement_action(
                _action(closed_on_day=None, effectiveness_verified=True)
            )

    def test_duplicate_process_id_refused(self):
        system = _system(
            processes=[_process("PRC-TVAC"), _process("PRC-TVAC", ["vibration-test"])]
        )
        with self.assertRaises(ValueError):
            validate_system(system)

    def test_duplicate_service_offered_refused(self):
        with self.assertRaises(ValueError):
            validate_system(_system(services_offered=["emc-test", "emc-test"]))

    def test_management_review_after_assessment_day_refused(self):
        with self.assertRaises(ValueError):
            validate_system(_system(last_management_review_day=1200))

    def test_action_closed_after_assessment_day_refused(self):
        with self.assertRaises(ValueError):
            validate_system(_system(improvement_actions=[_action(closed_on_day=1200)]))

    def test_non_mapping_system_refused(self):
        with self.assertRaises(ValueError):
            validate_system(["established"])


class ScopeAndCoverage(unittest.TestCase):
    def test_scope_gap_named_when_a_service_is_outside_scope(self):
        system = _system(declared_scope=["thermal-vacuum-test", "vibration-test"])
        self.assertEqual(scope_gaps(system), ["emc-test"])

    def test_scope_overreach_named_when_scope_claims_an_unoffered_service(self):
        system = _system(declared_scope=SERVICES + ["shock-test"])
        self.assertEqual(scope_overreach(system), ["shock-test"])

    def test_services_in_scope_is_the_intersection(self):
        system = _system(declared_scope=["vibration-test", "shock-test"])
        self.assertEqual(services_in_scope(system), ["vibration-test"])

    def test_full_coverage_is_exactly_one(self):
        self.assertAlmostEqual(process_coverage(_system()), 1.0, places=9)

    def test_partial_coverage_names_the_uncovered_service(self):
        system = _system(
            processes=[
                _process("PRC-TVAC", ["thermal-vacuum-test"]),
                _process("PRC-VIB", ["vibration-test"]),
            ]
        )
        self.assertAlmostEqual(process_coverage(system), 2.0 / 3.0, places=9)
        self.assertEqual(uncovered_services(system), ["emc-test"])

    def test_a_draft_process_does_not_cover_a_service(self):
        system = _system(
            processes=[
                _process("PRC-TVAC", ["thermal-vacuum-test"]),
                _process("PRC-VIB", ["vibration-test"]),
                _process("PRC-EMC", ["emc-test"], state=PROCESS_DRAFT, approved_on_day=None),
            ]
        )
        self.assertEqual(uncovered_services(system), ["emc-test"])
        self.assertEqual(unapproved_processes_in_use(system), ["PRC-EMC"])

    def test_a_withdrawn_process_is_not_carried_as_in_use(self):
        system = _system(
            processes=[
                _process("PRC-TVAC", ["thermal-vacuum-test"]),
                _process("PRC-VIB", ["vibration-test"]),
                _process("PRC-EMC", ["emc-test"]),
                _process("PRC-OLD", ["emc-test"], state=PROCESS_WITHDRAWN, approved_on_day=None),
            ]
        )
        self.assertEqual(unapproved_processes_in_use(system), [])

    def test_coverage_of_an_empty_scope_is_zero_not_one(self):
        system = _system(declared_scope=[], services_offered=[])
        self.assertAlmostEqual(process_coverage(system), 0.0, places=9)

    def test_process_never_reviewed_is_past_review(self):
        system = _system(
            processes=[_process("PRC-TVAC", ["thermal-vacuum-test"], last_reviewed_day=None)]
        )
        self.assertIn("PRC-TVAC", processes_past_review(system, {}))

    def test_process_exactly_at_the_review_interval_is_not_past_review(self):
        system = _system(
            as_of_day=1000,
            processes=[_process("PRC-TVAC", ["thermal-vacuum-test"], last_reviewed_day=270)],
        )
        self.assertEqual(processes_past_review(system, {}), [])


class ImprovementLoop(unittest.TestCase):
    def test_all_actions_closed_and_verified_gives_full_closure(self):
        self.assertAlmostEqual(improvement_closure(_system(), {}), 1.0, places=9)

    def test_an_open_action_halves_the_closure(self):
        system = _system(
            improvement_actions=[
                _action("IMP-01"),
                _action("IMP-02", closed_on_day=None, effectiveness_verified=False),
            ]
        )
        self.assertAlmostEqual(improvement_closure(system, {}), 0.5, places=9)
        self.assertEqual([a["action_id"] for a in open_improvement_actions(system)], ["IMP-02"])

    def test_an_unverified_closure_does_not_count_as_closed(self):
        system = _system(
            improvement_actions=[_action("IMP-01", effectiveness_verified=False)]
        )
        self.assertAlmostEqual(improvement_closure(system, {}), 0.0, places=9)
        self.assertEqual(unverified_closures(system), ["IMP-01"])

    def test_an_unverified_closure_counts_when_verification_is_not_demanded(self):
        system = _system(
            improvement_actions=[_action("IMP-01", effectiveness_verified=False)]
        )
        closure = improvement_closure(system, {"require_effectiveness_verification": False})
        self.assertAlmostEqual(closure, 1.0, places=9)

    def test_an_empty_improvement_register_is_zero_closure(self):
        self.assertAlmostEqual(improvement_closure(_system(improvement_actions=[]), {}), 0.0,
                               places=9)

    def test_management_review_exactly_at_the_interval_is_current(self):
        system = _system(as_of_day=1000, last_management_review_day=635)
        self.assertTrue(management_review_is_current(system, {}))

    def test_management_review_one_day_past_the_interval_is_stale(self):
        system = _system(as_of_day=1000, last_management_review_day=634)
        self.assertFalse(management_review_is_current(system, {}))

    def test_a_centre_that_never_reviewed_is_not_current(self):
        system = _system(last_management_review_day=None)
        self.assertFalse(management_review_is_current(system, {}))


class ToleranceHelper(unittest.TestCase):
    def test_at_least_accepts_an_exact_equality(self):
        self.assertTrue(at_least(2.0 / 3.0, 2.0 / 3.0))

    def test_at_least_rejects_a_real_shortfall(self):
        self.assertFalse(at_least(0.5, 0.75))

    def test_at_least_refuses_a_non_number(self):
        with self.assertRaises(ValueError):
            at_least("0.9", 0.5)


class Verdicts(unittest.TestCase):
    def test_a_complete_system_is_established(self):
        result = assess_management_system(_case())
        self.assertEqual(result["verdict"], SYSTEM_ESTABLISHED)
        self.assertEqual(result["findings"], [])

    def test_a_system_never_established_short_circuits(self):
        result = assess_management_system(_case(system=_system(established=False)))
        self.assertEqual(result["verdict"], SYSTEM_ABSENT)

    def test_a_scope_gap_outranks_a_coverage_shortfall(self):
        system = _system(
            declared_scope=["thermal-vacuum-test"],
            processes=[_process("PRC-TVAC", ["thermal-vacuum-test"])],
        )
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], SCOPE_INCOMPLETE)

    def test_an_unapproved_process_outranks_a_coverage_shortfall(self):
        system = _system(
            processes=[
                _process("PRC-TVAC", ["thermal-vacuum-test"]),
                _process("PRC-VIB", ["vibration-test"]),
                _process("PRC-EMC", ["emc-test"], state=PROCESS_DRAFT, approved_on_day=None),
            ]
        )
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], PROCESS_APPROVAL_BROKEN)

    def test_a_coverage_shortfall_with_no_draft_process_is_reported_as_coverage(self):
        system = _system(
            processes=[
                _process("PRC-TVAC", ["thermal-vacuum-test"]),
                _process("PRC-VIB", ["vibration-test"]),
            ]
        )
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], PROCESS_COVERAGE_INSUFFICIENT)
        self.assertEqual(result["uncovered_services"], ["emc-test"])

    def test_a_stalled_improvement_loop_is_reported(self):
        system = _system(
            improvement_actions=[
                _action("IMP-01", closed_on_day=None, effectiveness_verified=False),
                _action("IMP-02", closed_on_day=None, effectiveness_verified=False),
            ]
        )
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], IMPROVEMENT_LOOP_STALLED)

    def test_a_stale_management_review_is_the_last_verdict_before_pass(self):
        system = _system(last_management_review_day=100)
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], MANAGEMENT_REVIEW_STALE)

    def test_scope_overreach_is_an_advisory_not_a_verdict(self):
        system = _system(declared_scope=SERVICES + ["shock-test"])
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], SYSTEM_ESTABLISHED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_unverified_closure_is_advised_when_the_loop_still_passes(self):
        system = _system(
            improvement_actions=[
                _action("IMP-01"),
                _action("IMP-02", effectiveness_verified=False),
            ]
        )
        result = assess_management_system(_case(system=system))
        self.assertEqual(result["verdict"], SYSTEM_ESTABLISHED)
        self.assertEqual(result["unverified_closures"], ["IMP-02"])

    def test_a_case_without_a_system_is_refused(self):
        with self.assertRaises(ValueError):
            assess_management_system({"policy": {}})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_management_system(("system",))


if __name__ == "__main__":
    unittest.main()
