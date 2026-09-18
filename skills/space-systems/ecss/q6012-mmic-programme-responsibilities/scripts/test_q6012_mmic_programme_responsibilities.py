"""Contract tests for the clause 6 MMIC programme responsibility allocation."""

import unittest

from q6012_mmic_programme_responsibilities_logic import (
    CATALOGUE_BASED,
    CUSTOMER,
    DUTY_ACCOUNTABILITY_CONFLICT,
    DUTY_CATALOGUE,
    DUTY_NOT_APPLICABLE_TO_MODE,
    DUTY_UNASSIGNED,
    FOUNDRY_LED,
    NON_TRANSFERABLE_DUTY_MISALLOCATED,
    RESPONSIBILITY_MATRIX_COMPLETE,
    SUPPLIER,
    UNRECORDED_RESPONSIBILITY_DEVIATION,
    applicable_duties,
    assess_duty,
    assess_responsibility_matrix,
    default_owner,
    duty_coverage,
    group_assignments,
    is_transferable,
    party_share,
    unassigned_duties,
    validate_allocation_policy,
    validate_assignment_entry,
    validate_mode,
    validate_party,
)


def default_matrix(mode):
    """Return the responsibility matrix every duty defaults to in a mode."""
    return [{"duty": duty, "owner": default_owner(duty, mode)} for duty in applicable_duties(mode)]


def matrix_without(mode, dropped):
    return [entry for entry in default_matrix(mode) if entry["duty"] != dropped]


def matrix_with_owner(mode, duty, owner, deviation_recorded=False):
    matrix = []
    for entry in default_matrix(mode):
        if entry["duty"] == duty:
            matrix.append(
                {"duty": duty, "owner": owner, "deviation_recorded": deviation_recorded}
            )
        else:
            matrix.append(entry)
    return matrix


class ModeAndPartyTests(unittest.TestCase):
    def test_foundry_led_mode_is_accepted(self):
        self.assertEqual(validate_mode(" foundry-led "), FOUNDRY_LED)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_mode("distributor-stock")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_mode(2)

    def test_party_is_normalized(self):
        self.assertEqual(validate_party(" supplier"), SUPPLIER)

    def test_unknown_party_rejected(self):
        with self.assertRaises(ValueError):
            validate_party("integrator")


class PolicyTests(unittest.TestCase):
    def test_defaults_require_a_deviation_record(self):
        self.assertTrue(validate_allocation_policy()["require_deviation_record"])

    def test_override_is_merged(self):
        rules = validate_allocation_policy({"allow_non_applicable_duties": True})
        self.assertTrue(rules["allow_non_applicable_duties"])
        self.assertTrue(rules["require_deviation_record"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_allocation_policy({"allow_subcontracting": True})

    def test_non_boolean_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_allocation_policy({"require_deviation_record": "yes"})


class DutyCatalogueTests(unittest.TestCase):
    def test_every_duty_carries_an_owner_map_for_both_modes(self):
        for duty, entry in DUTY_CATALOGUE.items():
            self.assertIn(FOUNDRY_LED, entry["owner"], duty)
            self.assertIn(CATALOGUE_BASED, entry["owner"], duty)

    def test_design_duties_do_not_arise_for_a_catalogue_part(self):
        duties = applicable_duties(CATALOGUE_BASED)
        self.assertNotIn("circuit-design", duties)
        self.assertNotIn("mask-set-procurement", duties)

    def test_a_catalogue_purchase_carries_fewer_duties(self):
        self.assertLess(
            len(applicable_duties(CATALOGUE_BASED)), len(applicable_duties(FOUNDRY_LED))
        )

    def test_evaluation_testing_changes_hands_with_the_mode(self):
        self.assertEqual(default_owner("evaluation-testing", FOUNDRY_LED), CUSTOMER)
        self.assertEqual(default_owner("evaluation-testing", CATALOGUE_BASED), SUPPLIER)

    def test_process_qualification_stays_with_the_supplier(self):
        self.assertEqual(default_owner("process-qualification", FOUNDRY_LED), SUPPLIER)
        self.assertFalse(is_transferable("process-qualification"))

    def test_flight_approval_stays_with_the_customer(self):
        self.assertEqual(default_owner("part-approval-for-flight", CATALOGUE_BASED), CUSTOMER)
        self.assertFalse(is_transferable("part-approval-for-flight"))

    def test_owner_of_a_duty_absent_from_the_mode_is_refused(self):
        with self.assertRaises(ValueError):
            default_owner("circuit-design", CATALOGUE_BASED)

    def test_unknown_duty_has_no_default_owner(self):
        with self.assertRaises(ValueError):
            default_owner("marketing-approval", FOUNDRY_LED)

    def test_transferability_of_an_unknown_duty_is_refused(self):
        with self.assertRaises(ValueError):
            is_transferable("marketing-approval")


class AssignmentEntryTests(unittest.TestCase):
    def test_entry_is_normalized(self):
        record = validate_assignment_entry({"duty": "delivery-documentation", "owner": "supplier"})
        self.assertEqual(record["owner"], SUPPLIER)
        self.assertFalse(record["deviation_recorded"])

    def test_unknown_duty_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment_entry({"duty": "packaging-artwork", "owner": "supplier"})

    def test_unknown_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment_entry({"duty": "circuit-design", "owner": "design-house"})

    def test_missing_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment_entry({"duty": "circuit-design"})

    def test_non_boolean_deviation_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment_entry(
                {"duty": "circuit-design", "owner": "supplier", "deviation_recorded": "waiver-7"}
            )

    def test_repeated_identical_entry_is_collapsed(self):
        grouped = group_assignments(
            [
                {"duty": "circuit-design", "owner": "supplier"},
                {"duty": "circuit-design", "owner": "supplier", "deviation_recorded": True},
            ]
        )
        self.assertEqual(len(grouped["circuit-design"]), 1)
        self.assertTrue(grouped["circuit-design"][0]["deviation_recorded"])

    def test_two_owners_of_one_duty_are_both_kept(self):
        grouped = group_assignments(
            [
                {"duty": "circuit-design", "owner": "supplier"},
                {"duty": "circuit-design", "owner": "customer"},
            ]
        )
        self.assertEqual(len(grouped["circuit-design"]), 2)

    def test_non_sequence_assignment_list_rejected(self):
        with self.assertRaises(ValueError):
            group_assignments({"duty": "circuit-design", "owner": "supplier"})


class CoverageTests(unittest.TestCase):
    def test_complete_matrix_covers_every_duty(self):
        grouped = group_assignments(default_matrix(FOUNDRY_LED))
        self.assertAlmostEqual(duty_coverage(grouped, FOUNDRY_LED), 1.0, places=9)

    def test_dropping_one_duty_lowers_the_coverage(self):
        grouped = group_assignments(matrix_without(FOUNDRY_LED, "radiation-characterization"))
        total = len(applicable_duties(FOUNDRY_LED))
        self.assertAlmostEqual(
            duty_coverage(grouped, FOUNDRY_LED), (total - 1) / float(total), places=9
        )

    def test_the_dropped_duty_is_named(self):
        grouped = group_assignments(matrix_without(FOUNDRY_LED, "radiation-characterization"))
        self.assertEqual(unassigned_duties(grouped, FOUNDRY_LED), ("radiation-characterization",))

    def test_the_two_shares_account_for_every_owned_duty(self):
        grouped = group_assignments(default_matrix(FOUNDRY_LED))
        total = party_share(grouped, FOUNDRY_LED, CUSTOMER) + party_share(
            grouped, FOUNDRY_LED, SUPPLIER
        )
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_share_of_a_party_holding_nothing_is_zero(self):
        grouped = group_assignments(
            [{"duty": "delivery-documentation", "owner": "supplier"}]
        )
        self.assertAlmostEqual(party_share(grouped, FOUNDRY_LED, CUSTOMER), 0.0, places=9)

    def test_share_is_zero_when_nothing_is_owned(self):
        self.assertAlmostEqual(party_share({}, FOUNDRY_LED, SUPPLIER), 0.0, places=9)

    def test_non_mapping_group_rejected(self):
        with self.assertRaises(ValueError):
            unassigned_duties(["circuit-design"], FOUNDRY_LED)


class DutyAssessmentTests(unittest.TestCase):
    def _records(self, duty, owner, deviation_recorded=False):
        return group_assignments(
            [{"duty": duty, "owner": owner, "deviation_recorded": deviation_recorded}]
        )[duty]

    def test_default_allocation_is_acceptable(self):
        record = assess_duty(
            "circuit-design", self._records("circuit-design", SUPPLIER), FOUNDRY_LED
        )
        self.assertTrue(record["acceptable"])

    def test_non_transferable_duty_moved_is_flagged(self):
        record = assess_duty(
            "process-qualification",
            self._records("process-qualification", CUSTOMER, True),
            FOUNDRY_LED,
        )
        self.assertIn(NON_TRANSFERABLE_DUTY_MISALLOCATED, record["statuses"])

    def test_transferred_duty_without_a_record_is_flagged(self):
        record = assess_duty(
            "evaluation-testing", self._records("evaluation-testing", SUPPLIER), FOUNDRY_LED
        )
        self.assertIn(UNRECORDED_RESPONSIBILITY_DEVIATION, record["statuses"])

    def test_transferred_duty_with_a_record_is_acceptable(self):
        record = assess_duty(
            "evaluation-testing",
            self._records("evaluation-testing", SUPPLIER, True),
            FOUNDRY_LED,
        )
        self.assertTrue(record["acceptable"])

    def test_deviation_record_requirement_can_be_waived_by_policy(self):
        record = assess_duty(
            "evaluation-testing",
            self._records("evaluation-testing", SUPPLIER),
            FOUNDRY_LED,
            {"require_deviation_record": False},
        )
        self.assertTrue(record["acceptable"])

    def test_two_accountable_parties_are_flagged(self):
        grouped = group_assignments(
            [
                {"duty": "screening-and-lot-acceptance", "owner": "supplier"},
                {"duty": "screening-and-lot-acceptance", "owner": "customer",
                 "deviation_recorded": True},
            ]
        )
        record = assess_duty(
            "screening-and-lot-acceptance", grouped["screening-and-lot-acceptance"], FOUNDRY_LED
        )
        self.assertIn(DUTY_ACCOUNTABILITY_CONFLICT, record["statuses"])

    def test_duty_from_the_other_mode_is_flagged(self):
        record = assess_duty(
            "circuit-design", self._records("circuit-design", SUPPLIER), CATALOGUE_BASED
        )
        self.assertIn(DUTY_NOT_APPLICABLE_TO_MODE, record["statuses"])
        self.assertIsNone(record["expected_owner"])

    def test_non_applicable_duty_can_be_allowed_by_policy(self):
        record = assess_duty(
            "circuit-design",
            self._records("circuit-design", SUPPLIER),
            CATALOGUE_BASED,
            {"allow_non_applicable_duties": True},
        )
        self.assertTrue(record["acceptable"])

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_duty("circuit-design", [], FOUNDRY_LED)

    def test_unknown_duty_rejected(self):
        with self.assertRaises(ValueError):
            assess_duty("marketing-approval", [{"owner": CUSTOMER}], FOUNDRY_LED)


class MatrixTests(unittest.TestCase):
    def test_complete_foundry_led_matrix_passes(self):
        result = assess_responsibility_matrix(
            {"mode": FOUNDRY_LED, "assignments": default_matrix(FOUNDRY_LED)}
        )
        self.assertEqual(result["verdict"], RESPONSIBILITY_MATRIX_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_complete_catalogue_matrix_passes(self):
        result = assess_responsibility_matrix(
            {"mode": CATALOGUE_BASED, "assignments": default_matrix(CATALOGUE_BASED)}
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["unassigned"], ())

    def test_missing_duty_is_reported_as_unassigned(self):
        result = assess_responsibility_matrix(
            {
                "mode": FOUNDRY_LED,
                "assignments": matrix_without(FOUNDRY_LED, "nonconformance-disposition"),
            }
        )
        self.assertEqual(result["verdict"], DUTY_UNASSIGNED)
        self.assertIn("nonconformance-disposition", result["unassigned"])

    def test_a_misallocated_non_transferable_duty_outranks_a_gap(self):
        assignments = matrix_with_owner(
            FOUNDRY_LED, "design-rule-compliance", CUSTOMER, deviation_recorded=True
        )
        assignments = [e for e in assignments if e["duty"] != "delivery-documentation"]
        result = assess_responsibility_matrix({"mode": FOUNDRY_LED, "assignments": assignments})
        self.assertEqual(result["verdict"], NON_TRANSFERABLE_DUTY_MISALLOCATED)
        self.assertEqual(len(result["findings"]), 2)

    def test_unrecorded_deviation_is_the_mildest_verdict(self):
        assignments = matrix_with_owner(FOUNDRY_LED, "radiation-characterization", SUPPLIER)
        result = assess_responsibility_matrix({"mode": FOUNDRY_LED, "assignments": assignments})
        self.assertEqual(result["verdict"], UNRECORDED_RESPONSIBILITY_DEVIATION)

    def test_shares_move_when_a_duty_changes_hands(self):
        base = assess_responsibility_matrix(
            {"mode": FOUNDRY_LED, "assignments": default_matrix(FOUNDRY_LED)}
        )
        moved = assess_responsibility_matrix(
            {
                "mode": FOUNDRY_LED,
                "assignments": matrix_with_owner(
                    FOUNDRY_LED, "radiation-characterization", SUPPLIER, True
                ),
            }
        )
        total = len(applicable_duties(FOUNDRY_LED))
        self.assertAlmostEqual(
            base["customer_share"] - moved["customer_share"], 1.0 / total, places=9
        )

    def test_catalogue_matrix_carrying_a_design_duty_is_flagged(self):
        assignments = default_matrix(CATALOGUE_BASED) + [
            {"duty": "circuit-design", "owner": SUPPLIER}
        ]
        result = assess_responsibility_matrix(
            {"mode": CATALOGUE_BASED, "assignments": assignments}
        )
        self.assertEqual(result["verdict"], DUTY_NOT_APPLICABLE_TO_MODE)

    def test_empty_matrix_reports_every_duty_unassigned(self):
        result = assess_responsibility_matrix({"mode": CATALOGUE_BASED, "assignments": []})
        self.assertEqual(len(result["unassigned"]), len(applicable_duties(CATALOGUE_BASED)))
        self.assertAlmostEqual(result["duty_coverage"], 0.0, places=9)

    def test_missing_assignments_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_responsibility_matrix({"mode": FOUNDRY_LED})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_responsibility_matrix([{"duty": "circuit-design", "owner": "supplier"}])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_responsibility_matrix({"mode": "broker", "assignments": []})


if __name__ == "__main__":
    unittest.main()
