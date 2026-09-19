"""Contract test for the q2007-qs-reps leaf (stdlib unittest)."""

import unittest

from q2007_qs_reps_logic import (
    APPOINTMENT_NONE,
    APPOINTMENT_VERBAL,
    APPOINTMENT_WRITTEN,
    AUTHORITY_DIRECT_MANAGEMENT_ACCESS,
    AUTHORITY_NONCONFORMANCE,
    AUTHORITY_STOP_TEST,
    FINDING_INDIRECT,
    FINDING_INFORMAL,
    FINDING_INTO_EXECUTION_LINE,
    FINDING_NOT_APPOINTED,
    FINDING_NO_ACTIVITY,
    ROLE_QUALITY,
    ROLE_SAFETY,
    assess_appointment_register,
    assess_representative,
    authority_coverage_ratio,
    can_stop_test,
    coverage_gaps,
    escalation_hops,
    has_direct_management_access,
    is_independent_of_test_execution,
    missing_authorities,
    required_authorities,
    validate_representative,
)


def quality_rep(entry_id="QA-1", **kw):
    record = {
        "id": entry_id,
        "role": ROLE_QUALITY,
        "appointment_form": APPOINTMENT_WRITTEN,
        "authorities": [
            AUTHORITY_STOP_TEST,
            AUTHORITY_DIRECT_MANAGEMENT_ACCESS,
            AUTHORITY_NONCONFORMANCE,
        ],
        "reports_to": "test-centre-director",
        "escalation_chain": [],
        "activities": ["thermal-vacuum-campaign"],
    }
    record.update(kw)
    return record


def safety_rep(entry_id="SA-1", **kw):
    record = {
        "id": entry_id,
        "role": ROLE_SAFETY,
        "appointment_form": APPOINTMENT_WRITTEN,
        "authorities": [AUTHORITY_STOP_TEST, AUTHORITY_DIRECT_MANAGEMENT_ACCESS],
        "reports_to": "test-centre-director",
        "escalation_chain": [],
        "activities": ["thermal-vacuum-campaign"],
    }
    record.update(kw)
    return record


class TestValidateRepresentative(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_representative({"id": "QA-9", "role": ROLE_QUALITY})
        self.assertEqual(norm["appointment_form"], APPOINTMENT_NONE)
        self.assertEqual(norm["authorities"], [])
        self.assertEqual(norm["escalation_chain"], [])
        self.assertEqual(norm["activities"], [])
        self.assertIsNone(norm["reports_to"])

    def test_authorities_are_deduplicated_and_ordered(self):
        norm = validate_representative(
            quality_rep(authorities=[AUTHORITY_STOP_TEST, AUTHORITY_STOP_TEST])
        )
        self.assertEqual(norm["authorities"], [AUTHORITY_STOP_TEST])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(["QA-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(quality_rep(""))

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(quality_rep(role="configuration-management"))

    def test_unknown_appointment_form_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(quality_rep(appointment_form="implied"))

    def test_unknown_authority_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(quality_rep(authorities=["budget-approval"]))

    def test_string_authorities_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(quality_rep(authorities=AUTHORITY_STOP_TEST))

    def test_non_string_escalation_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_representative(quality_rep(escalation_chain=[7]))


class TestAuthorities(unittest.TestCase):
    def test_quality_role_needs_three_authorities(self):
        self.assertEqual(len(required_authorities(ROLE_QUALITY)), 3)

    def test_safety_role_needs_two_authorities(self):
        self.assertEqual(len(required_authorities(ROLE_SAFETY)), 2)

    def test_unknown_role_has_no_required_authorities(self):
        with self.assertRaises(ValueError):
            required_authorities("procurement")

    def test_complete_appointment_misses_nothing(self):
        self.assertEqual(missing_authorities(quality_rep()), ())

    def test_missing_nonconformance_authority_is_named(self):
        rep = quality_rep(
            authorities=[AUTHORITY_STOP_TEST, AUTHORITY_DIRECT_MANAGEMENT_ACCESS]
        )
        self.assertEqual(missing_authorities(rep), (AUTHORITY_NONCONFORMANCE,))

    def test_safety_rep_is_not_graded_on_nonconformance_authority(self):
        self.assertEqual(missing_authorities(safety_rep()), ())


class TestStopTestAndAccess(unittest.TestCase):
    def test_written_appointment_with_stop_authority_can_stop(self):
        self.assertTrue(can_stop_test(quality_rep()))

    def test_verbal_appointment_cannot_stop_a_test(self):
        self.assertFalse(can_stop_test(quality_rep(appointment_form=APPOINTMENT_VERBAL)))

    def test_appointment_without_stop_authority_cannot_stop(self):
        rep = quality_rep(
            authorities=[AUTHORITY_DIRECT_MANAGEMENT_ACCESS, AUTHORITY_NONCONFORMANCE]
        )
        self.assertFalse(can_stop_test(rep))

    def test_empty_chain_is_zero_hops(self):
        self.assertEqual(escalation_hops(quality_rep()), 0)

    def test_two_intermediaries_are_two_hops(self):
        rep = quality_rep(escalation_chain=["section-head", "division-head"])
        self.assertEqual(escalation_hops(rep), 2)

    def test_direct_access_needs_both_chain_and_authority(self):
        self.assertTrue(has_direct_management_access(quality_rep()))
        self.assertFalse(
            has_direct_management_access(quality_rep(escalation_chain=["section-head"]))
        )


class TestIndependence(unittest.TestCase):
    def test_director_reporting_line_is_independent(self):
        self.assertTrue(is_independent_of_test_execution(quality_rep()))

    def test_test_conductor_reporting_line_is_not_independent(self):
        rep = quality_rep(reports_to="test-conductor")
        self.assertFalse(is_independent_of_test_execution(rep))

    def test_unstated_reporting_line_is_not_a_finding(self):
        self.assertTrue(is_independent_of_test_execution(quality_rep(reports_to=None)))


class TestAssessRepresentative(unittest.TestCase):
    def test_sound_appointment_carries_no_finding(self):
        result = assess_representative(quality_rep())
        self.assertTrue(result["sound"])
        self.assertEqual(result["findings"], [])

    def test_unappointed_entry_is_flagged(self):
        result = assess_representative(quality_rep(appointment_form=APPOINTMENT_NONE))
        self.assertIn(FINDING_NOT_APPOINTED, result["findings"])

    def test_verbal_appointment_is_flagged(self):
        result = assess_representative(quality_rep(appointment_form=APPOINTMENT_VERBAL))
        self.assertIn(FINDING_INFORMAL, result["findings"])

    def test_execution_line_reporting_is_flagged(self):
        result = assess_representative(quality_rep(reports_to="test-conductor"))
        self.assertIn(FINDING_INTO_EXECUTION_LINE, result["findings"])

    def test_indirect_chain_is_flagged_separately(self):
        result = assess_representative(quality_rep(escalation_chain=["section-head"]))
        self.assertIn(FINDING_INDIRECT, result["findings"])
        self.assertNotIn(FINDING_INTO_EXECUTION_LINE, result["findings"])

    def test_appointment_covering_nothing_is_flagged(self):
        result = assess_representative(quality_rep(activities=[]))
        self.assertIn(FINDING_NO_ACTIVITY, result["findings"])

    def test_missing_authority_finding_names_the_token(self):
        rep = safety_rep(authorities=[AUTHORITY_STOP_TEST])
        result = assess_representative(rep)
        self.assertIn(
            "missing-authority-%s" % AUTHORITY_DIRECT_MANAGEMENT_ACCESS,
            result["findings"],
        )


class TestCoverageRatio(unittest.TestCase):
    def test_full_register_scores_one(self):
        ratio = authority_coverage_ratio([quality_rep(), safety_rep()])
        self.assertAlmostEqual(ratio, 1.0, places=9)

    def test_one_missing_authority_of_five_scores_four_fifths(self):
        rep = safety_rep(authorities=[AUTHORITY_STOP_TEST])
        ratio = authority_coverage_ratio([quality_rep(), rep])
        self.assertAlmostEqual(ratio, 4.0 / 5.0, places=9)

    def test_empty_register_raises(self):
        with self.assertRaises(ValueError):
            authority_coverage_ratio([])


class TestCoverageGaps(unittest.TestCase):
    def test_both_roles_present_leaves_no_gap(self):
        gaps = coverage_gaps(
            [quality_rep(), safety_rep()], ["thermal-vacuum-campaign"]
        )
        self.assertEqual(gaps, {})

    def test_missing_safety_role_is_a_gap(self):
        gaps = coverage_gaps([quality_rep()], ["thermal-vacuum-campaign"])
        self.assertEqual(gaps, {"thermal-vacuum-campaign": [ROLE_SAFETY]})

    def test_deficient_appointment_does_not_provide_cover(self):
        weak = safety_rep(appointment_form=APPOINTMENT_VERBAL)
        gaps = coverage_gaps([quality_rep(), weak], ["thermal-vacuum-campaign"])
        self.assertEqual(gaps, {"thermal-vacuum-campaign": [ROLE_SAFETY]})

    def test_activity_outside_the_scope_list_raises(self):
        with self.assertRaises(ValueError):
            coverage_gaps(
                [quality_rep(activities=["acoustic-campaign"])],
                ["thermal-vacuum-campaign"],
            )

    def test_duplicate_activity_in_scope_raises(self):
        with self.assertRaises(ValueError):
            coverage_gaps([quality_rep()], ["a-campaign", "a-campaign"])

    def test_empty_scope_raises(self):
        with self.assertRaises(ValueError):
            coverage_gaps([quality_rep()], [])


class TestAssessRegister(unittest.TestCase):
    def test_sound_register_is_reported_sound(self):
        report = assess_appointment_register(
            [quality_rep(), safety_rep()], ["thermal-vacuum-campaign"]
        )
        self.assertTrue(report["sound"])
        self.assertEqual(report["deficient_ids"], [])
        self.assertEqual(
            report["stop_test_capable_ids"], ["QA-1", "SA-1"]
        )

    def test_deficient_entry_makes_the_register_unsound(self):
        report = assess_appointment_register(
            [quality_rep(), safety_rep(appointment_form=APPOINTMENT_VERBAL)],
            ["thermal-vacuum-campaign"],
        )
        self.assertFalse(report["sound"])
        self.assertEqual(report["deficient_ids"], ["SA-1"])

    def test_duplicate_entry_id_raises(self):
        with self.assertRaises(ValueError):
            assess_appointment_register(
                [quality_rep("QA-1"), quality_rep("QA-1")],
                ["thermal-vacuum-campaign"],
            )

    def test_empty_register_raises(self):
        with self.assertRaises(ValueError):
            assess_appointment_register([], ["thermal-vacuum-campaign"])

    def test_non_list_register_raises(self):
        with self.assertRaises(ValueError):
            assess_appointment_register(quality_rep(), ["thermal-vacuum-campaign"])


if __name__ == "__main__":
    unittest.main()
