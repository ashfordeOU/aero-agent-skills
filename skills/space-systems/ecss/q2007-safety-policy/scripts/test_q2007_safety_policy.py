"""Contract tests for the clause 5.9.2 safety policy and objectives logic."""

import unittest

from q2007_safety_policy_logic import (
    FRACTION_TOLERANCE,
    REQUIRED_COMMITMENTS,
    TOP_MANAGEMENT,
    assess_policy,
    assess_safety_policy,
    attainment_fraction,
    missing_commitments,
    objective_progress,
    objective_status,
    policy_currency,
    validate_objective,
    validate_policy,
)

POLICY = {
    "statement": "the centre runs no test whose hazards are not controlled",
    "commitments": list(REQUIRED_COMMITMENTS),
    "approved_by": "Centre Director",
    "issue_day": 100,
    "review_interval_days": 365,
    "communicated": True,
}

OBJECTIVE = {
    "id": "SO-1",
    "metric": "reportable incidents per thousand test hours",
    "unit": "incidents/kh",
    "baseline": 4.0,
    "target": 2.0,
    "direction": "decrease",
    "owner": "centre safety officer",
    "due_day": 400,
    "actual": 2.0,
}


def policy(**overrides):
    out = dict(POLICY)
    out.update(overrides)
    return out


def objective(**overrides):
    out = dict(OBJECTIVE)
    out.update(overrides)
    return out


class CommitmentTests(unittest.TestCase):
    def test_complete_policy_misses_nothing(self):
        self.assertEqual(missing_commitments(list(REQUIRED_COMMITMENTS)), ())

    def test_absent_commitment_is_reported(self):
        held = [c for c in REQUIRED_COMMITMENTS if c != "legal-compliance"]
        self.assertEqual(missing_commitments(held), ("legal-compliance",))

    def test_repeated_commitment_counts_once(self):
        held = list(REQUIRED_COMMITMENTS) + ["legal-compliance"]
        self.assertEqual(missing_commitments(held), ())

    def test_unknown_commitment_rejected(self):
        with self.assertRaises(ValueError):
            missing_commitments(["best-effort"])

    def test_blank_commitment_rejected(self):
        with self.assertRaises(ValueError):
            missing_commitments(["  "])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            missing_commitments("legal-compliance")


class CurrencyTests(unittest.TestCase):
    def test_inside_the_interval_is_current(self):
        self.assertEqual(policy_currency(100, 365, 200), "current")

    def test_exactly_on_the_interval_is_due(self):
        self.assertEqual(policy_currency(100, 365, 465), "due")

    def test_past_the_interval_is_overdue(self):
        self.assertEqual(policy_currency(100, 365, 600), "overdue")

    def test_day_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            policy_currency(100, 365, 50)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            policy_currency(100, 0, 200)

    def test_non_integer_day_rejected(self):
        with self.assertRaises(ValueError):
            policy_currency(100.0, 365, 200)


class PolicyValidationTests(unittest.TestCase):
    def test_valid_policy_normalises(self):
        record = validate_policy(policy())
        self.assertTrue(record["approved_at_top_level"])
        self.assertEqual(record["missing_commitments"], ())

    def test_approval_below_top_management_is_flagged(self):
        record = validate_policy(policy(approved_by="shift supervisor"))
        self.assertFalse(record["approved_at_top_level"])

    def test_every_top_management_title_is_recognised(self):
        for title in TOP_MANAGEMENT:
            self.assertTrue(
                validate_policy(policy(approved_by=title))["approved_at_top_level"]
            )

    def test_blank_statement_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy(policy(statement="   "))

    def test_missing_key_rejected(self):
        bad = policy()
        del bad["approved_by"]
        with self.assertRaises(ValueError):
            validate_policy(bad)

    def test_non_boolean_communication_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy(policy(communicated="yes"))


class PolicyAssessmentTests(unittest.TestCase):
    def test_sound_policy_has_no_findings(self):
        self.assertTrue(assess_policy(policy(), 200)["sound"])

    def test_missing_commitment_is_a_finding(self):
        held = [c for c in REQUIRED_COMMITMENTS if c != "resource-provision"]
        self.assertFalse(assess_policy(policy(commitments=held), 200)["sound"])

    def test_low_level_approval_is_a_finding(self):
        self.assertFalse(assess_policy(policy(approved_by="team lead"), 200)["sound"])

    def test_uncommunicated_policy_is_a_finding(self):
        self.assertFalse(assess_policy(policy(communicated=False), 200)["sound"])

    def test_overdue_review_is_a_finding(self):
        record = assess_policy(policy(), 700)
        self.assertEqual(record["currency"], "overdue")
        self.assertFalse(record["sound"])

    def test_due_review_is_not_yet_a_finding(self):
        record = assess_policy(policy(), 465)
        self.assertEqual(record["currency"], "due")
        self.assertTrue(record["sound"])


class ObjectiveValidationTests(unittest.TestCase):
    def test_valid_objective_normalises(self):
        record = validate_objective(objective())
        self.assertAlmostEqual(record["target"], 2.0)

    def test_target_equal_to_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective(objective(target=4.0))

    def test_decrease_with_a_higher_target_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective(objective(target=6.0))

    def test_increase_with_a_lower_target_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective(objective(direction="increase", target=1.0))

    def test_increase_objective_accepted(self):
        record = validate_objective(
            objective(direction="increase", baseline=0.6, target=0.9)
        )
        self.assertEqual(record["direction"], "increase")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective(objective(direction="hold"))

    def test_missing_unit_rejected(self):
        bad = objective()
        del bad["unit"]
        with self.assertRaises(ValueError):
            validate_objective(bad)

    def test_blank_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective(objective(owner=" "))

    def test_non_numeric_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_objective(objective(baseline="four"))


class ObjectiveGradingTests(unittest.TestCase):
    def test_progress_at_the_baseline_is_zero(self):
        self.assertAlmostEqual(objective_progress(4.0, 2.0, 4.0), 0.0, places=9)

    def test_progress_at_the_target_is_one(self):
        self.assertAlmostEqual(objective_progress(4.0, 2.0, 2.0), 1.0, places=9)

    def test_progress_halfway(self):
        self.assertAlmostEqual(objective_progress(4.0, 2.0, 3.0), 0.5, places=9)

    def test_progress_beyond_the_target_exceeds_one(self):
        self.assertAlmostEqual(objective_progress(4.0, 2.0, 1.0), 1.5, places=9)

    def test_progress_with_coincident_bounds_rejected(self):
        with self.assertRaises(ValueError):
            objective_progress(4.0, 4.0, 3.0)

    def test_value_exactly_on_a_decrease_target_is_met(self):
        record = objective_status(objective(), 2.0)
        self.assertAlmostEqual(record["progress"], 1.0, places=9)
        self.assertTrue(record["met"])

    def test_value_above_a_decrease_target_is_not_met(self):
        self.assertFalse(objective_status(objective(), 3.0)["met"])

    def test_value_exactly_on_an_increase_target_is_met(self):
        record = objective_status(
            objective(direction="increase", baseline=0.6, target=0.9), 0.9
        )
        self.assertTrue(record["met"])

    def test_movement_away_from_the_target_is_a_finding(self):
        record = objective_status(objective(), 5.0)
        self.assertTrue(record["regressed"])
        self.assertEqual(len(record["findings"]), 1)

    def test_no_movement_is_not_a_regression(self):
        record = objective_status(objective(), 4.0)
        self.assertFalse(record["regressed"])


class AttainmentTests(unittest.TestCase):
    def test_all_met_is_one(self):
        records = [objective_status(objective(), 2.0)]
        self.assertAlmostEqual(attainment_fraction(records), 1.0, places=9)

    def test_half_met(self):
        records = [
            objective_status(objective(), 2.0),
            objective_status(objective(id="SO-2"), 3.0),
        ]
        self.assertAlmostEqual(attainment_fraction(records), 0.5, places=9)

    def test_attainment_over_no_objectives_rejected(self):
        with self.assertRaises(ValueError):
            attainment_fraction([])


class FullAssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        out = {
            "policy": policy(),
            "objectives": [objective()],
            "today": 300,
            "required_attainment": 1.0,
        }
        out.update(overrides)
        return out

    def test_sound_policy_and_met_objectives_stand(self):
        result = assess_safety_policy(self.spec())
        self.assertTrue(result["policy_stands"])
        self.assertAlmostEqual(result["attainment"], 1.0, places=9)

    def test_attainment_exactly_on_the_requirement_passes(self):
        result = assess_safety_policy(
            self.spec(
                objectives=[objective(), objective(id="SO-3", actual=3.0)],
                required_attainment=0.5,
            )
        )
        self.assertAlmostEqual(
            result["attainment"], result["required_attainment"], places=9
        )
        self.assertTrue(result["policy_stands"])

    def test_short_attainment_is_a_finding(self):
        result = assess_safety_policy(
            self.spec(objectives=[objective(actual=3.0)], required_attainment=1.0)
        )
        self.assertFalse(result["policy_stands"])

    def test_unmet_objective_past_its_due_day_is_counted(self):
        result = assess_safety_policy(
            self.spec(objectives=[objective(actual=3.0, due_day=200)], today=300)
        )
        self.assertEqual(result["overdue_count"], 1)

    def test_policy_finding_propagates(self):
        result = assess_safety_policy(self.spec(policy=policy(communicated=False)))
        self.assertFalse(result["policy_stands"])

    def test_objective_without_a_measured_value_rejected(self):
        bare = objective()
        del bare["actual"]
        with self.assertRaises(ValueError):
            assess_safety_policy(self.spec(objectives=[bare]))

    def test_duplicate_objective_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_policy(self.spec(objectives=[objective(), objective()]))

    def test_policy_with_no_objectives_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_policy(self.spec(objectives=[]))

    def test_required_attainment_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_policy(self.spec(required_attainment=1.5))

    def test_tolerance_is_representation_sized(self):
        self.assertAlmostEqual(FRACTION_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
