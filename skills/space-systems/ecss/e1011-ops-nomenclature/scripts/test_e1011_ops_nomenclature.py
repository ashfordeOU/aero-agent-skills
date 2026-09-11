import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_ops_nomenclature_logic import (
    CANONICAL_CREW_ROLES,
    CANONICAL_MISSION_PHASES,
    CANONICAL_COMMAND_TYPES,
    NomenclatureViolation,
    check_crew_roles,
    check_mission_phases,
    check_command_types,
    check_synonym_conflicts,
    assess_document,
)


class TestCanonicalVocabulary(unittest.TestCase):
    def test_crew_roles_set_is_frozen(self):
        self.assertIsInstance(CANONICAL_CREW_ROLES, frozenset)

    def test_mission_phases_set_is_frozen(self):
        self.assertIsInstance(CANONICAL_MISSION_PHASES, frozenset)

    def test_command_types_set_is_frozen(self):
        self.assertIsInstance(CANONICAL_COMMAND_TYPES, frozenset)

    def test_canonical_crew_roles_nonempty(self):
        self.assertGreater(len(CANONICAL_CREW_ROLES), 0)

    def test_canonical_phases_nonempty(self):
        self.assertGreater(len(CANONICAL_MISSION_PHASES), 0)


class TestCrewRoleChecks(unittest.TestCase):
    def test_valid_roles_produce_no_violations(self):
        roles = [("commander", "§3.1"), ("pilot", "§3.2"), ("flight engineer", "§3.3")]
        self.assertEqual(check_crew_roles(roles), [])

    def test_abbreviation_flagged_with_canonical_replacement(self):
        violations = check_crew_roles([("cdr", "§3.1")])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "crew_role")
        self.assertIn("commander", violations[0].detail)

    def test_unknown_role_flagged_as_unrecognized(self):
        violations = check_crew_roles([("spacewalker", "§5")])
        self.assertEqual(len(violations), 1)
        self.assertIn("Unrecognized", violations[0].detail)

    def test_multiple_bad_roles_all_flagged(self):
        roles = [("cdr", "§1"), ("plt", "§2"), ("unknown_role", "§3")]
        self.assertEqual(len(check_crew_roles(roles)), 3)

    def test_mixed_valid_and_invalid_only_flags_invalid(self):
        roles = [("commander", "§1"), ("fe", "§2"), ("pilot", "§3")]
        violations = check_crew_roles(roles)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].term, "fe")

    def test_case_insensitive_canonical_match(self):
        roles = [("Commander", "§1"), ("PILOT", "§2")]
        self.assertEqual(check_crew_roles(roles), [])


class TestMissionPhaseChecks(unittest.TestCase):
    def test_valid_phases_produce_no_violations(self):
        phases = [("launch", "§2.1"), ("docking", "§2.2"), ("reentry", "§2.3")]
        self.assertEqual(check_mission_phases(phases), [])

    def test_liftoff_synonym_flagged_with_canonical(self):
        violations = check_mission_phases([("liftoff", "§2.1")])
        self.assertEqual(len(violations), 1)
        self.assertIn("launch", violations[0].detail)

    def test_deorbit_synonym_flagged(self):
        violations = check_mission_phases([("deorbit", "§4")])
        self.assertEqual(len(violations), 1)
        self.assertIn("de-orbit", violations[0].detail)

    def test_unknown_phase_flagged_as_unrecognized(self):
        violations = check_mission_phases([("cruise phase", "§3")])
        self.assertEqual(len(violations), 1)
        self.assertIn("Unrecognized", violations[0].detail)

    def test_reentry_variant_flagged(self):
        violations = check_mission_phases([("re-entry", "§6")])
        self.assertEqual(len(violations), 1)
        self.assertIn("reentry", violations[0].detail)


class TestCommandTypeChecks(unittest.TestCase):
    def test_valid_command_types_produce_no_violations(self):
        cmds = [("nominal command", "§5.1"), ("emergency command", "§5.2")]
        self.assertEqual(check_command_types(cmds), [])

    def test_unknown_command_type_flagged(self):
        violations = check_command_types([("arbitrary command", "§5.3")])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "command_type")

    def test_empty_command_list_returns_empty(self):
        self.assertEqual(check_command_types([]), [])


class TestSynonymConflicts(unittest.TestCase):
    def test_no_conflict_when_canonical_terms_only(self):
        term_locs = {"commander": ["§1"], "pilot": ["§2"]}
        self.assertEqual(check_synonym_conflicts(term_locs), [])

    def test_conflict_detected_when_abbreviation_and_canonical_both_present(self):
        # "commander" and "cdr" both used — conflict
        term_locs = {"commander": ["§1"], "cdr": ["§3"]}
        violations = check_synonym_conflicts(term_locs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "synonym_conflict")

    def test_phase_conflict_detected(self):
        # "launch" and "liftoff" both used
        term_locs = {"launch": ["§1"], "liftoff": ["§2"]}
        violations = check_synonym_conflicts(term_locs)
        self.assertEqual(len(violations), 1)
        self.assertIn("launch", violations[0].term)

    def test_no_conflict_for_unknown_terms(self):
        # Unknown terms are not in any canonical set; no conflict raised
        term_locs = {"unknown_a": ["§1"], "unknown_b": ["§2"]}
        self.assertEqual(check_synonym_conflicts(term_locs), [])

    def test_multiple_conflicts_all_reported(self):
        # Two separate conflicts: commander/cdr and launch/liftoff
        term_locs = {
            "commander": ["§1"],
            "cdr": ["§2"],
            "launch": ["§3"],
            "liftoff": ["§4"],
        }
        violations = check_synonym_conflicts(term_locs)
        self.assertEqual(len(violations), 2)


class TestAssessDocument(unittest.TestCase):
    def test_clean_document_is_compliant(self):
        result = assess_document(
            crew_roles=[("commander", "§1"), ("pilot", "§2")],
            mission_phases=[("launch", "§3"), ("docking", "§4")],
            command_types=[("nominal command", "§5")],
            term_locations={"commander": ["§1"], "pilot": ["§2"], "launch": ["§3"]},
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total_violations"], 0)

    def test_document_with_violations_is_not_compliant(self):
        result = assess_document(
            crew_roles=[("cdr", "§1")],
            mission_phases=[("liftoff", "§2")],
            command_types=[],
            term_locations={"cdr": ["§1"], "liftoff": ["§2"]},
        )
        self.assertFalse(result["compliant"])
        self.assertGreater(result["total_violations"], 0)

    def test_result_contains_all_required_keys(self):
        result = assess_document([], [], [], {})
        for key in (
            "crew_role_violations",
            "mission_phase_violations",
            "command_type_violations",
            "synonym_conflicts",
            "total_violations",
            "compliant",
        ):
            self.assertIn(key, result)

    def test_empty_document_is_compliant(self):
        result = assess_document([], [], [], {})
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total_violations"], 0)

    def test_none_term_locations_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_document([], [], [], None)

    def test_violation_counts_match_lists(self):
        result = assess_document(
            crew_roles=[("cdr", "§1"), ("unknown_person", "§2")],
            mission_phases=[("liftoff", "§3")],
            command_types=[("bad cmd", "§4")],
            term_locations={"cdr": ["§1"]},
        )
        total = (
            len(result["crew_role_violations"])
            + len(result["mission_phase_violations"])
            + len(result["command_type_violations"])
            + len(result["synonym_conflicts"])
        )
        self.assertEqual(result["total_violations"], total)


if __name__ == "__main__":
    unittest.main()
