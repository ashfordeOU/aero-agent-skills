"""Contract test for the q2007-competence-training leaf (stdlib unittest)."""

import unittest

from q2007_competence_training_logic import (
    CERTIFICATE_VALIDITY_DAYS,
    GAP_ABSENT,
    GAP_EXPIRED,
    GAP_RECORD_STALE,
    GAP_UNDER_LEVEL,
    GAP_UNTRAINED,
    MAX_LEVEL,
    RECORD_RETENTION_DAYS,
    VALID_COMPETENCES,
    assess_person,
    assess_personnel,
    certificate_state,
    competence_gaps,
    days_to_certificate_expiry,
    is_cleared_for_role,
    record_is_within_retention,
    required_competences,
    role_clearance_ratio,
    training_plan,
    validate_competence_entry,
    validate_person,
)

DAY = 5000


def held(level, trained=True, assessed=DAY - 100, expires=DAY + 300):
    return {
        "level": level,
        "trained": trained,
        "assessed_on_day": assessed,
        "certificate_expires_on_day": expires,
    }


def operator(person_id="P-1", **overrides):
    competences = {
        "test-facility-operation": held(2),
        "test-centre-safety-rules": held(2),
    }
    competences.update(overrides.pop("competences", {}))
    record = {"id": person_id, "role": "test-operator", "competences": competences}
    record.update(overrides)
    return record


def conductor(person_id="C-1", **overrides):
    competences = {
        "test-facility-operation": held(3),
        "test-centre-safety-rules": held(3),
        "test-procedure-authoring": held(2),
        "nonconformance-handling": held(2),
    }
    competences.update(overrides.pop("competences", {}))
    record = {"id": person_id, "role": "test-conductor", "competences": competences}
    record.update(overrides)
    return record


class TestRoleNeeds(unittest.TestCase):
    def test_conductor_needs_four_competences(self):
        self.assertEqual(len(required_competences("test-conductor")), 4)

    def test_safety_officer_needs_the_top_safety_level(self):
        self.assertEqual(
            required_competences("safety-officer")["test-centre-safety-rules"],
            MAX_LEVEL,
        )

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            required_competences("catering")

    def test_returned_need_is_a_copy(self):
        need = required_competences("test-operator")
        need["test-facility-operation"] = 0
        self.assertEqual(
            required_competences("test-operator")["test-facility-operation"], 2
        )


class TestValidation(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_person({"id": "P-9", "role": "test-operator"})
        self.assertEqual(norm["competences"], {})

    def test_non_mapping_person_raises(self):
        with self.assertRaises(ValueError):
            validate_person(["P-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_person(operator(""))

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            validate_person(operator(role="astrologer"))

    def test_unknown_competence_name_raises(self):
        with self.assertRaises(ValueError):
            validate_person(operator(competences={"welding": held(3)}))

    def test_level_above_scale_raises(self):
        with self.assertRaises(ValueError):
            validate_competence_entry("P-1", VALID_COMPETENCES[0], {"level": 9})

    def test_negative_level_raises(self):
        with self.assertRaises(ValueError):
            validate_competence_entry("P-1", VALID_COMPETENCES[0], {"level": -1})

    def test_non_integer_day_raises(self):
        with self.assertRaises(ValueError):
            validate_competence_entry(
                "P-1", VALID_COMPETENCES[0], {"level": 2, "assessed_on_day": 12.5}
            )

    def test_non_boolean_trained_raises(self):
        with self.assertRaises(ValueError):
            validate_competence_entry(
                "P-1", VALID_COMPETENCES[0], {"level": 2, "trained": "yes"}
            )


class TestCertificates(unittest.TestCase):
    def test_future_expiry_is_valid(self):
        self.assertEqual(
            certificate_state(operator(), "test-facility-operation", DAY), "valid"
        )

    def test_expiry_on_the_evaluation_day_is_still_valid(self):
        person = operator(
            competences={"test-facility-operation": held(2, expires=DAY)}
        )
        self.assertEqual(
            certificate_state(person, "test-facility-operation", DAY), "valid"
        )

    def test_expiry_before_the_evaluation_day_is_expired(self):
        person = operator(
            competences={"test-facility-operation": held(2, expires=DAY - 1)}
        )
        self.assertEqual(
            certificate_state(person, "test-facility-operation", DAY), "expired"
        )

    def test_no_certificate_is_uncertificated_not_expired(self):
        person = operator(
            competences={"test-facility-operation": held(2, expires=None)}
        )
        self.assertEqual(
            certificate_state(person, "test-facility-operation", DAY),
            "uncertificated",
        )

    def test_unheld_competence_reports_absent(self):
        self.assertEqual(certificate_state(operator(), "hazard-analysis", DAY),
                         "absent")

    def test_days_to_expiry_counts_forward(self):
        self.assertEqual(
            days_to_certificate_expiry(operator(), "test-facility-operation", DAY),
            300,
        )

    def test_days_to_expiry_without_a_certificate_raises(self):
        with self.assertRaises(ValueError):
            days_to_certificate_expiry(operator(), "hazard-analysis", DAY)

    def test_validity_window_is_two_years(self):
        self.assertEqual(CERTIFICATE_VALIDITY_DAYS, 730)


class TestRetention(unittest.TestCase):
    def test_recent_assessment_is_within_retention(self):
        self.assertTrue(
            record_is_within_retention(operator(), "test-facility-operation", DAY)
        )

    def test_assessment_exactly_at_the_window_edge_is_retained(self):
        person = operator(
            competences={
                "test-facility-operation": held(
                    2, assessed=DAY - RECORD_RETENTION_DAYS
                )
            }
        )
        self.assertTrue(
            record_is_within_retention(person, "test-facility-operation", DAY)
        )

    def test_assessment_past_the_window_is_not_retained(self):
        person = operator(
            competences={
                "test-facility-operation": held(
                    2, assessed=DAY - RECORD_RETENTION_DAYS - 1
                )
            }
        )
        self.assertFalse(
            record_is_within_retention(person, "test-facility-operation", DAY)
        )


class TestGaps(unittest.TestCase):
    def test_a_fully_qualified_operator_has_no_gap(self):
        self.assertEqual(competence_gaps(operator(), DAY), [])

    def test_missing_competence_is_reported_absent(self):
        person = operator()
        del person["competences"]["test-centre-safety-rules"]
        reasons = [g["reason"] for g in competence_gaps(person, DAY)]
        self.assertEqual(reasons, [GAP_ABSENT])

    def test_absent_competence_shortfall_is_the_full_requirement(self):
        person = operator()
        del person["competences"]["test-centre-safety-rules"]
        self.assertEqual(competence_gaps(person, DAY)[0]["shortfall"], 2)

    def test_under_level_is_reported_with_its_shortfall(self):
        person = operator(competences={"test-facility-operation": held(1)})
        gap = [
            g for g in competence_gaps(person, DAY) if g["reason"] == GAP_UNDER_LEVEL
        ][0]
        self.assertEqual(gap["shortfall"], 1)

    def test_expired_certificate_is_its_own_gap(self):
        person = operator(
            competences={"test-facility-operation": held(2, expires=DAY - 1)}
        )
        reasons = [g["reason"] for g in competence_gaps(person, DAY)]
        self.assertIn(GAP_EXPIRED, reasons)
        self.assertNotIn(GAP_UNDER_LEVEL, reasons)

    def test_untrained_level_is_its_own_gap(self):
        person = operator(
            competences={"test-facility-operation": held(2, trained=False)}
        )
        reasons = [g["reason"] for g in competence_gaps(person, DAY)]
        self.assertIn(GAP_UNTRAINED, reasons)

    def test_stale_record_is_its_own_gap(self):
        person = operator(
            competences={
                "test-facility-operation": held(
                    2, assessed=DAY - RECORD_RETENTION_DAYS - 10
                )
            }
        )
        reasons = [g["reason"] for g in competence_gaps(person, DAY)]
        self.assertIn(GAP_RECORD_STALE, reasons)

    def test_clearance_follows_the_gap_list(self):
        self.assertTrue(is_cleared_for_role(conductor(), DAY))
        person = conductor(competences={"hazard-analysis": held(4)})
        person["competences"]["test-procedure-authoring"]["level"] = 1
        self.assertFalse(is_cleared_for_role(person, DAY))


class TestTrainingPlan(unittest.TestCase):
    def test_a_cleared_person_has_an_empty_plan(self):
        self.assertEqual(training_plan(conductor(), DAY), [])

    def test_plan_is_ordered_worst_shortfall_first(self):
        person = conductor()
        person["competences"]["test-facility-operation"]["level"] = 0
        person["competences"]["test-procedure-authoring"]["level"] = 1
        names = [item["competence"] for item in training_plan(person, DAY)]
        self.assertEqual(names[0], "test-facility-operation")
        self.assertEqual(names[1], "test-procedure-authoring")

    def test_equal_shortfalls_break_alphabetically(self):
        person = conductor()
        person["competences"]["test-facility-operation"]["level"] = 2
        person["competences"]["test-centre-safety-rules"]["level"] = 2
        names = [item["competence"] for item in training_plan(person, DAY)]
        self.assertEqual(names, ["test-centre-safety-rules", "test-facility-operation"])

    def test_one_competence_failing_twice_appears_once_with_both_reasons(self):
        person = operator(
            competences={
                "test-facility-operation": held(1, trained=False)
            }
        )
        plan = [
            item
            for item in training_plan(person, DAY)
            if item["competence"] == "test-facility-operation"
        ]
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["reasons"], sorted([GAP_UNDER_LEVEL, GAP_UNTRAINED]))


class TestRollUp(unittest.TestCase):
    def test_assess_person_reports_role_and_clearance(self):
        result = assess_person(operator(), DAY)
        self.assertEqual(result["role"], "test-operator")
        self.assertTrue(result["cleared"])

    def test_clearance_ratio_is_a_fraction_of_the_role_population(self):
        weak = operator("P-2", competences={"test-facility-operation": held(0)})
        ratio = role_clearance_ratio([operator(), weak], "test-operator", DAY)
        self.assertAlmostEqual(ratio, 0.5, places=9)

    def test_clearance_ratio_for_an_unstaffed_role_raises(self):
        with self.assertRaises(ValueError):
            role_clearance_ratio([operator()], "safety-officer", DAY)

    def test_register_is_compliant_when_everyone_is_cleared(self):
        report = assess_personnel([operator(), conductor()], DAY)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["blocked_ids"], [])

    def test_one_blocked_person_blocks_the_register(self):
        weak = operator("P-2", competences={"test-centre-safety-rules": held(0)})
        report = assess_personnel([operator(), weak], DAY)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["blocked_ids"], ["P-2"])

    def test_duplicate_person_id_raises(self):
        with self.assertRaises(ValueError):
            assess_personnel([operator("P-1"), operator("P-1")], DAY)

    def test_empty_register_raises(self):
        with self.assertRaises(ValueError):
            assess_personnel([], DAY)

    def test_non_list_register_raises(self):
        with self.assertRaises(ValueError):
            assess_personnel(operator(), DAY)

    def test_non_integer_evaluation_day_raises(self):
        with self.assertRaises(ValueError):
            assess_personnel([operator()], "2026-09-19")


if __name__ == "__main__":
    unittest.main()
