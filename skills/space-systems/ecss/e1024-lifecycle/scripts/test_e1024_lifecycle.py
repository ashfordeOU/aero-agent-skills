import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1024_lifecycle_logic import (
    INTERFACE_TYPES,
    PROJECT_PHASES,
    MATURITY_LEVELS,
    get_phase_activities,
    get_all_phase_activities,
    check_lifecycle_compliance,
    get_ots_agreements,
    check_ots_compliance,
    determine_maturity_level,
    validate_phase_sequence,
    check_interface_freeze,
)


class TestConstantsAndValidation(unittest.TestCase):

    def test_all_interface_types_present(self):
        for expected in ("generic", "space_launch", "space_ground", "ots"):
            self.assertIn(expected, INTERFACE_TYPES)

    def test_project_phases_ordered_correctly(self):
        self.assertEqual(PROJECT_PHASES, ("0", "A", "B", "C", "D", "E", "F"))

    def test_maturity_levels_keys_match_phases(self):
        self.assertEqual(set(MATURITY_LEVELS.keys()), set(PROJECT_PHASES))

    def test_invalid_interface_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_phase_activities("B", "unknown_type")

    def test_invalid_phase_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_phase_activities("Z", "generic")

    def test_invalid_phase_in_validate_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_phase_sequence(["0", "X"])

    def test_invalid_type_in_freeze_check_raises(self):
        with self.assertRaises(ValueError):
            check_interface_freeze("C", "bad_type")


class TestGetPhaseActivities(unittest.TestCase):

    def test_generic_phase_zero_identifies_interfaces(self):
        acts = get_phase_activities("0", "generic")
        self.assertIn("identify_interfaces", acts)
        self.assertIn("assign_responsibilities", acts)

    def test_generic_phase_b_baselines_icd(self):
        acts = get_phase_activities("B", "generic")
        self.assertIn("baseline_icd", acts)
        self.assertIn("issue_interface_requirement_document", acts)

    def test_space_launch_phase_c_has_service_agreement_and_freeze(self):
        acts = get_phase_activities("C", "space_launch")
        self.assertIn("launch_service_agreement_execution", acts)
        self.assertIn("launch_icd_freeze", acts)

    def test_space_ground_phase_b_baselines_ground_icd(self):
        acts = get_phase_activities("B", "space_ground")
        self.assertIn("ground_segment_icd_baseline", acts)

    def test_ots_phase_b_has_preliminary_agreement_activity(self):
        acts = get_phase_activities("B", "ots")
        self.assertIn("preliminary_ots_technical_agreement", acts)

    def test_missing_stream_phase_returns_empty_list(self):
        acts = get_phase_activities("0", "space_launch")
        self.assertEqual(acts, [])

    def test_all_phase_activities_ots_phase_b_includes_generic(self):
        combined = get_all_phase_activities("B", "ots")
        self.assertIn("baseline_icd", combined)
        self.assertIn("preliminary_ots_technical_agreement", combined)

    def test_all_phase_activities_generic_equals_stream_specific(self):
        generic_all = get_all_phase_activities("C", "generic")
        generic_direct = get_phase_activities("C", "generic")
        self.assertEqual(generic_all, generic_direct)


class TestLifecycleCompliance(unittest.TestCase):

    def test_no_gap_when_all_generic_phase_b_activities_complete(self):
        required = get_all_phase_activities("B", "generic")
        gap = check_lifecycle_compliance("B", "generic", required)
        self.assertEqual(gap, [])

    def test_gap_detected_when_activity_missing(self):
        required = get_all_phase_activities("B", "generic")
        incomplete = [a for a in required if a != "baseline_icd"]
        gap = check_lifecycle_compliance("B", "generic", incomplete)
        self.assertIn("baseline_icd", gap)
        self.assertNotIn("issue_interface_requirement_document", gap)

    def test_space_launch_phase_d_no_gap_when_all_done(self):
        required = get_all_phase_activities("D", "space_launch")
        gap = check_lifecycle_compliance("D", "space_launch", required)
        self.assertEqual(gap, [])

    def test_empty_completed_returns_all_required(self):
        required = get_all_phase_activities("C", "space_ground")
        gap = check_lifecycle_compliance("C", "space_ground", [])
        self.assertEqual(sorted(gap), sorted(required))

    def test_extra_completed_activities_do_not_cause_gap(self):
        required = get_all_phase_activities("A", "ots")
        extra = required + ["some_other_done_activity"]
        gap = check_lifecycle_compliance("A", "ots", extra)
        self.assertEqual(gap, [])


class TestOTSAgreements(unittest.TestCase):

    def test_no_agreements_required_at_phase_zero(self):
        self.assertEqual(get_ots_agreements("0"), [])

    def test_no_agreements_required_at_phase_a(self):
        self.assertEqual(get_ots_agreements("A"), [])

    def test_preliminary_agreement_required_by_phase_b(self):
        agreements = get_ots_agreements("B")
        self.assertIn("preliminary_technical_interface_agreement", agreements)

    def test_formal_agreement_required_by_phase_c(self):
        agreements = get_ots_agreements("C")
        self.assertIn("formal_technical_interface_agreement", agreements)
        self.assertIn("preliminary_technical_interface_agreement", agreements)

    def test_acceptance_agreement_required_by_phase_d(self):
        agreements = get_ots_agreements("D")
        self.assertIn("acceptance_agreement", agreements)

    def test_phase_d_agreements_carry_forward_to_phase_e(self):
        self.assertEqual(get_ots_agreements("D"), get_ots_agreements("E"))

    def test_check_ots_compliance_missing_formal_at_phase_c(self):
        signed = ["preliminary_technical_interface_agreement"]
        missing = check_ots_compliance("C", signed)
        self.assertIn("formal_technical_interface_agreement", missing)
        self.assertNotIn("preliminary_technical_interface_agreement", missing)

    def test_check_ots_compliance_all_signed_at_phase_d(self):
        all_signed = get_ots_agreements("D")
        missing = check_ots_compliance("D", all_signed)
        self.assertEqual(missing, [])

    def test_check_ots_compliance_none_signed_at_phase_c(self):
        missing = check_ots_compliance("C", [])
        self.assertIn("preliminary_technical_interface_agreement", missing)
        self.assertIn("formal_technical_interface_agreement", missing)


class TestMaturityLevel(unittest.TestCase):

    def test_phases_zero_and_a_are_preliminary_definition(self):
        self.assertEqual(determine_maturity_level("0"), "preliminary_definition")
        self.assertEqual(determine_maturity_level("A"), "preliminary_definition")

    def test_phase_b_is_initial_icd_baseline(self):
        self.assertEqual(determine_maturity_level("B"), "initial_icd_baseline")

    def test_phase_c_is_frozen_icd(self):
        self.assertEqual(determine_maturity_level("C"), "frozen_icd")

    def test_phases_d_and_e_are_verified_icd(self):
        self.assertEqual(determine_maturity_level("D"), "verified_icd")
        self.assertEqual(determine_maturity_level("E"), "verified_icd")

    def test_phase_f_is_closed_out(self):
        self.assertEqual(determine_maturity_level("F"), "closed_out")


class TestPhaseSequenceValidation(unittest.TestCase):

    def test_empty_input_returns_empty(self):
        self.assertEqual(validate_phase_sequence([]), [])

    def test_complete_sequence_to_phase_c_returns_empty(self):
        missing = validate_phase_sequence(["0", "A", "B", "C"])
        self.assertEqual(missing, [])

    def test_skipped_phase_a_detected(self):
        missing = validate_phase_sequence(["0", "B", "C"])
        self.assertIn("A", missing)
        self.assertNotIn("0", missing)

    def test_multiple_skipped_phases_all_detected(self):
        missing = validate_phase_sequence(["0", "D"])
        self.assertIn("A", missing)
        self.assertIn("B", missing)
        self.assertIn("C", missing)

    def test_single_phase_zero_no_missing(self):
        self.assertEqual(validate_phase_sequence(["0"]), [])

    def test_duplicate_phases_handled_gracefully(self):
        missing = validate_phase_sequence(["0", "A", "A", "B"])
        self.assertEqual(missing, [])


class TestInterfaceFreeze(unittest.TestCase):

    def test_generic_not_frozen_at_phase_c(self):
        self.assertFalse(check_interface_freeze("C", "generic"))

    def test_generic_frozen_at_phase_d(self):
        self.assertTrue(check_interface_freeze("D", "generic"))

    def test_generic_frozen_after_phase_d(self):
        self.assertTrue(check_interface_freeze("E", "generic"))
        self.assertTrue(check_interface_freeze("F", "generic"))

    def test_space_launch_frozen_at_phase_c(self):
        self.assertTrue(check_interface_freeze("C", "space_launch"))

    def test_space_launch_not_frozen_at_phase_b(self):
        self.assertFalse(check_interface_freeze("B", "space_launch"))

    def test_space_ground_frozen_at_phase_c(self):
        self.assertTrue(check_interface_freeze("C", "space_ground"))

    def test_ots_frozen_at_phase_c(self):
        self.assertTrue(check_interface_freeze("C", "ots"))

    def test_ots_not_frozen_at_phase_b(self):
        self.assertFalse(check_interface_freeze("B", "ots"))


if __name__ == "__main__":
    unittest.main()
