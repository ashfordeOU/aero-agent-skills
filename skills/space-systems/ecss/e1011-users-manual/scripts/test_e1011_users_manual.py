"""
Gate 3 contract tests — e1011-users-manual (ECSS-E-ST-10-11C §4.3.4).

stdlib unittest, offline, deterministic.  Run:
    python3 test_e1011_users_manual.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_users_manual_logic import (
    ProcedureStep,
    TaskProcedure,
    UserCategory,
    ErrorRecovery,
    UsersManual,
    REQUIRED_SECTION_TYPES,
    VALID_PHASES,
    SKILL_LEVELS,
    validate_phase,
    validate_skill_level,
)


# ---------------------------------------------------------------------------
# Factories for valid objects
# ---------------------------------------------------------------------------

def _step(step_id="S-01", action="Open valve", safety_critical=False, warning_note=""):
    return ProcedureStep(
        step_id=step_id,
        action=action,
        safety_critical=safety_critical,
        warning_note=warning_note,
    )


def _critical_step(step_id="S-02", action="Activate thruster",
                   warning_note="Ensure no crew in thruster plume zone."):
    return ProcedureStep(
        step_id=step_id,
        action=action,
        safety_critical=True,
        warning_note=warning_note,
    )


def _procedure(proc_id="P-001", description="Activate life support",
               phases=None, steps=None):
    if phases is None:
        phases = ["on-orbit"]
    if steps is None:
        steps = [_step()]
    return TaskProcedure(
        procedure_id=proc_id,
        description=description,
        phases=phases,
        steps=steps,
    )


def _user_cat(name="Mission Specialist", skill_level="trained",
              physical_constraints="suited operations",
              cognitive_load_limits="moderate",
              operating_language="English"):
    return UserCategory(
        name=name,
        skill_level=skill_level,
        physical_constraints=physical_constraints,
        cognitive_load_limits=cognitive_load_limits,
        operating_language=operating_language,
    )


def _recovery(proc_id="P-001", desc="Switch to backup life support loop."):
    return ErrorRecovery(procedure_id=proc_id, recovery_description=desc)


def _complete_manual():
    return UsersManual(
        product_name="Life Support Controller",
        user_categories=[_user_cat()],
        task_procedures=[_procedure()],
        interface_description="Panel A: three toggle switches and one alphanumeric display.",
        error_recovery_entries=[
            ErrorRecovery(
                procedure_id="P-001",
                recovery_description=(
                    "If the controller stops responding, transfer control to the "
                    "redundant unit and command the affected loads to a safe state."
                ),
            )
        ],
        mission_phase_applicability="Applies during on-orbit nominal and contingency phases.",
        training_requirements="Crew must complete 40-hour simulator course before first use.",
    )


# ---------------------------------------------------------------------------
# ProcedureStep tests
# ---------------------------------------------------------------------------

class TestProcedureStep(unittest.TestCase):

    def test_valid_step_has_no_issues(self):
        issues = _step().validate()
        self.assertEqual(issues, [])

    def test_safety_critical_step_with_warning_has_no_issues(self):
        issues = _critical_step().validate()
        self.assertEqual(issues, [])

    def test_safety_critical_step_without_warning_raises_issue(self):
        s = ProcedureStep(step_id="S-03", action="Vent atmosphere",
                          safety_critical=True, warning_note="")
        issues = s.validate()
        self.assertTrue(any("warning_note" in i for i in issues))

    def test_empty_action_raises_issue(self):
        s = ProcedureStep(step_id="S-04", action="   ")
        issues = s.validate()
        self.assertTrue(any("action is empty" in i for i in issues))

    def test_empty_step_id_raises_issue(self):
        s = ProcedureStep(step_id="", action="Do something")
        issues = s.validate()
        self.assertTrue(any("step_id is empty" in i for i in issues))


# ---------------------------------------------------------------------------
# TaskProcedure tests
# ---------------------------------------------------------------------------

class TestTaskProcedure(unittest.TestCase):

    def test_valid_procedure_has_no_issues(self):
        issues = _procedure().validate()
        self.assertEqual(issues, [])

    def test_procedure_with_no_steps_raises_issue(self):
        p = _procedure(steps=[])
        issues = p.validate()
        self.assertTrue(any("at least one step" in i for i in issues))

    def test_procedure_with_no_phases_raises_issue(self):
        p = _procedure(phases=[])
        issues = p.validate()
        self.assertTrue(any("mission-phase tag" in i for i in issues))

    def test_procedure_with_invalid_phase_raises_issue(self):
        p = _procedure(phases=["orbital-ballet"])
        issues = p.validate()
        self.assertTrue(any("orbital-ballet" in i for i in issues))

    def test_has_safety_critical_steps_true_when_step_flagged(self):
        p = _procedure(steps=[_step(), _critical_step()])
        self.assertTrue(p.has_safety_critical_steps())

    def test_has_safety_critical_steps_false_when_no_step_flagged(self):
        p = _procedure(steps=[_step("S-01"), _step("S-02")])
        self.assertFalse(p.has_safety_critical_steps())


# ---------------------------------------------------------------------------
# UserCategory tests
# ---------------------------------------------------------------------------

class TestUserCategory(unittest.TestCase):

    def test_valid_user_category_has_no_issues(self):
        issues = _user_cat().validate()
        self.assertEqual(issues, [])

    def test_invalid_skill_level_raises_issue(self):
        uc = _user_cat(skill_level="superhuman")
        issues = uc.validate()
        self.assertTrue(any("skill_level" in i for i in issues))

    def test_empty_physical_constraints_raises_issue(self):
        uc = _user_cat(physical_constraints="")
        issues = uc.validate()
        self.assertTrue(any("physical_constraints" in i for i in issues))

    def test_empty_cognitive_load_limits_raises_issue(self):
        uc = _user_cat(cognitive_load_limits="  ")
        issues = uc.validate()
        self.assertTrue(any("cognitive_load_limits" in i for i in issues))

    def test_empty_operating_language_raises_issue(self):
        uc = _user_cat(operating_language="")
        issues = uc.validate()
        self.assertTrue(any("operating_language" in i for i in issues))


# ---------------------------------------------------------------------------
# ErrorRecovery tests
# ---------------------------------------------------------------------------

class TestErrorRecovery(unittest.TestCase):

    def test_valid_recovery_has_no_issues(self):
        issues = _recovery().validate()
        self.assertEqual(issues, [])

    def test_empty_recovery_description_raises_issue(self):
        er = ErrorRecovery(procedure_id="P-001", recovery_description="")
        issues = er.validate()
        self.assertTrue(any("recovery_description" in i for i in issues))

    def test_empty_procedure_id_raises_issue(self):
        er = ErrorRecovery(procedure_id="", recovery_description="Activate backup.")
        issues = er.validate()
        self.assertTrue(any("procedure_id is empty" in i for i in issues))


# ---------------------------------------------------------------------------
# UsersManual gap list and compliance tests
# ---------------------------------------------------------------------------

class TestUsersManualCompliance(unittest.TestCase):

    def test_complete_manual_is_compliant(self):
        manual = _complete_manual()
        self.assertTrue(manual.is_compliant(), manual.build_gap_list())

    def test_missing_interface_description_makes_manual_non_compliant(self):
        manual = _complete_manual()
        manual.interface_description = ""
        gaps = manual.build_gap_list()
        self.assertFalse(manual.is_compliant())
        self.assertTrue(any("interface-description" in g for g in gaps))

    def test_missing_training_requirements_makes_manual_non_compliant(self):
        manual = _complete_manual()
        manual.training_requirements = ""
        gaps = manual.build_gap_list()
        self.assertFalse(manual.is_compliant())
        self.assertTrue(any("training-requirements" in g for g in gaps))

    def test_missing_mission_phase_applicability_makes_manual_non_compliant(self):
        manual = _complete_manual()
        manual.mission_phase_applicability = "  "
        gaps = manual.build_gap_list()
        self.assertFalse(manual.is_compliant())
        self.assertTrue(any("mission-phase-applicability" in g for g in gaps))

    def test_safety_critical_procedure_without_recovery_makes_manual_non_compliant(self):
        manual = _complete_manual()
        manual.task_procedures = [_procedure(steps=[_step(), _critical_step()])]
        manual.error_recovery_entries = []
        gaps = manual.build_gap_list()
        self.assertFalse(manual.is_compliant())
        self.assertTrue(any("safety-critical steps but no linked error-recovery" in g
                            for g in gaps))

    def test_safety_critical_procedure_with_recovery_is_compliant(self):
        manual = _complete_manual()
        manual.task_procedures = [_procedure(steps=[_step(), _critical_step()])]
        manual.error_recovery_entries = [_recovery("P-001")]
        self.assertTrue(manual.is_compliant(), manual.build_gap_list())

    def test_invalid_user_category_propagates_to_gap_list(self):
        manual = _complete_manual()
        manual.user_categories = [_user_cat(skill_level="wizard")]
        gaps = manual.build_gap_list()
        self.assertTrue(any("skill_level" in g for g in gaps))

    def test_empty_product_name_raises_gap(self):
        manual = _complete_manual()
        manual.product_name = ""
        gaps = manual.build_gap_list()
        self.assertTrue(any("product_name" in g for g in gaps))


# ---------------------------------------------------------------------------
# Query helper tests
# ---------------------------------------------------------------------------

class TestQueryHelpers(unittest.TestCase):

    def test_procedures_in_phase_returns_matching_procedures(self):
        manual = _complete_manual()
        manual.task_procedures = [
            _procedure("P-001", phases=["on-orbit"]),
            _procedure("P-002", phases=["pre-launch"]),
            _procedure("P-003", phases=["all-phases"]),
        ]
        results = manual.procedures_in_phase("on-orbit")
        ids = {p.procedure_id for p in results}
        self.assertIn("P-001", ids)
        self.assertIn("P-003", ids)
        self.assertNotIn("P-002", ids)

    def test_procedures_in_phase_all_phases_returns_all(self):
        manual = _complete_manual()
        manual.task_procedures = [
            _procedure("P-001", phases=["on-orbit"]),
            _procedure("P-002", phases=["pre-launch"]),
        ]
        results = manual.procedures_in_phase("all-phases")
        self.assertEqual(len(results), 2)

    def test_procedures_in_phase_invalid_phase_raises_value_error(self):
        manual = _complete_manual()
        with self.assertRaises(ValueError):
            manual.procedures_in_phase("deep-space-ballet")

    def test_safety_critical_procedures_filter(self):
        manual = _complete_manual()
        manual.task_procedures = [
            _procedure("P-001", steps=[_step()]),
            _procedure("P-002", steps=[_critical_step()]),
        ]
        sc = manual.safety_critical_procedures()
        self.assertEqual(len(sc), 1)
        self.assertEqual(sc[0].procedure_id, "P-002")

    def test_recovery_for_procedure_returns_correct_entry(self):
        manual = _complete_manual()
        manual.error_recovery_entries = [
            _recovery("P-001", "Use backup circuit."),
            _recovery("P-002", "Notify ground control."),
        ]
        er = manual.recovery_for_procedure("P-002")
        self.assertIsNotNone(er)
        self.assertEqual(er.recovery_description, "Notify ground control.")

    def test_recovery_for_procedure_returns_none_when_not_found(self):
        manual = _complete_manual()
        manual.error_recovery_entries = []
        self.assertIsNone(manual.recovery_for_procedure("P-999"))


# ---------------------------------------------------------------------------
# Standalone helper tests
# ---------------------------------------------------------------------------

class TestStandaloneHelpers(unittest.TestCase):

    def test_validate_phase_accepts_valid_phases(self):
        for ph in VALID_PHASES:
            self.assertTrue(validate_phase(ph), f"Expected {ph} to be valid")

    def test_validate_phase_rejects_unknown_phase(self):
        self.assertFalse(validate_phase("interstellar-cruise"))

    def test_validate_skill_level_accepts_valid_levels(self):
        for lvl in SKILL_LEVELS:
            self.assertTrue(validate_skill_level(lvl))

    def test_validate_skill_level_rejects_unknown_level(self):
        self.assertFalse(validate_skill_level("godlike"))

    def test_required_section_types_count(self):
        self.assertEqual(len(REQUIRED_SECTION_TYPES), 6)

    def test_required_section_types_includes_error_recovery(self):
        self.assertIn("error-recovery", REQUIRED_SECTION_TYPES)

    def test_required_section_types_includes_user_population(self):
        self.assertIn("user-population", REQUIRED_SECTION_TYPES)


if __name__ == "__main__":
    unittest.main()
