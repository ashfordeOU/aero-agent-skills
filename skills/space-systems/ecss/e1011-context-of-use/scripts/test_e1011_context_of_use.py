"""
Stdlib unittest for e1011_context_of_use_logic.py — offline, deterministic.

Run:  python3 test_e1011_context_of_use.py

Covers:
  - UserRole validation (valid, missing training pathway, bad experience level,
    inverted experience range, zero count)
  - Task validation (valid, missing owning role, missing phase, bad criticality,
    bad phase label, error-rate out of range)
  - EnvElement validation (valid, bad category, missing phase)
  - ContextRecord gap list (complete record, incomplete record)
  - Cross-reference check (orphaned owning_role)
  - tasks_for_role, tasks_in_phase, env_elements_by_category
  - safety_critical_tasks
  - validate_phase helper
  - is_complete short-circuit
"""

import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from e1011_context_of_use_logic import (
    ContextRecord,
    EnvElement,
    Task,
    UserRole,
    validate_phase,
)

# ---------------------------------------------------------------------------
# Factories for valid objects
# ---------------------------------------------------------------------------

def _role(name="Commander", count=1, min_exp="trained", max_exp="expert",
          training="Basic + advanced sim"):
    return UserRole(name=name, count=count, min_experience=min_exp,
                    max_experience=max_exp, training_pathway=training)


def _task(name="Display check", goal="Confirm status", role="Commander",
          trigger="Post-orbit insertion", steps=5, freq="once-per-day",
          crit="routine", err=0.01, phases=None):
    return Task(name=name, goal=goal, owning_role=role,
                triggering_condition=trigger, nominal_step_count=steps,
                frequency=freq, criticality=crit, max_error_rate=err,
                phases=phases if phases is not None else ["on-orbit-nominal"])


def _env(name="Control station", cat="physical", desc="Fixed console at 1g",
         phases=None):
    return EnvElement(name=name, category=cat, description=desc,
                      phases=phases if phases is not None else ["on-orbit-nominal"])


def _complete_record():
    rec = ContextRecord(product_boundary="Flight console display subsystem")
    rec.roles.append(_role())
    rec.tasks.append(_task())
    rec.env_elements.append(_env())
    return rec


# ---------------------------------------------------------------------------
# Tests — UserRole
# ---------------------------------------------------------------------------

class TestUserRoleValid(unittest.TestCase):
    def test_valid_role_has_no_gaps(self):
        self.assertEqual(_role().validate(), [])


class TestUserRoleMissingTraining(unittest.TestCase):
    def test_missing_training_pathway_flagged(self):
        r = _role(training=None)
        gaps = r.validate()
        self.assertTrue(any("training_pathway" in g for g in gaps),
                        f"Expected training_pathway gap, got: {gaps}")


class TestUserRoleBlankTraining(unittest.TestCase):
    def test_blank_training_pathway_flagged(self):
        r = _role(training="   ")
        gaps = r.validate()
        self.assertTrue(any("training_pathway" in g for g in gaps))


class TestUserRoleBadExperienceLevel(unittest.TestCase):
    def test_unrecognised_min_experience_flagged(self):
        r = _role(min_exp="beginner")
        gaps = r.validate()
        self.assertTrue(any("min_experience" in g for g in gaps))


class TestUserRoleInvertedExperience(unittest.TestCase):
    def test_min_greater_than_max_flagged(self):
        r = _role(min_exp="expert", max_exp="novice")
        gaps = r.validate()
        self.assertTrue(any("min_experience must be <= max_experience" in g for g in gaps))


class TestUserRoleZeroCount(unittest.TestCase):
    def test_zero_count_flagged(self):
        r = _role(count=0)
        gaps = r.validate()
        self.assertTrue(any("count" in g for g in gaps))


# ---------------------------------------------------------------------------
# Tests — Task
# ---------------------------------------------------------------------------

class TestTaskValid(unittest.TestCase):
    def test_valid_task_has_no_gaps(self):
        self.assertEqual(_task().validate(), [])


class TestTaskMissingRole(unittest.TestCase):
    def test_missing_owning_role_flagged(self):
        t = _task(role="")
        gaps = t.validate()
        self.assertTrue(any("owning_role" in g for g in gaps))


class TestTaskMissingPhase(unittest.TestCase):
    def test_empty_phases_flagged(self):
        t = _task(phases=[])
        gaps = t.validate()
        self.assertTrue(any("phase tag" in g for g in gaps))


class TestTaskBadCriticality(unittest.TestCase):
    def test_unrecognised_criticality_flagged(self):
        t = _task(crit="high")
        gaps = t.validate()
        self.assertTrue(any("criticality" in g for g in gaps))


class TestTaskBadPhaseLabel(unittest.TestCase):
    def test_unrecognised_phase_label_flagged(self):
        t = _task(phases=["deep-space"])
        gaps = t.validate()
        self.assertTrue(any("deep-space" in g for g in gaps))


class TestTaskErrorRateOutOfRange(unittest.TestCase):
    def test_error_rate_above_one_flagged(self):
        t = _task(err=1.5)
        gaps = t.validate()
        self.assertTrue(any("max_error_rate" in g for g in gaps))


# ---------------------------------------------------------------------------
# Tests — EnvElement
# ---------------------------------------------------------------------------

class TestEnvElementValid(unittest.TestCase):
    def test_valid_element_has_no_gaps(self):
        self.assertEqual(_env().validate(), [])


class TestEnvElementBadCategory(unittest.TestCase):
    def test_unrecognised_category_flagged(self):
        e = _env(cat="technical")
        gaps = e.validate()
        self.assertTrue(any("category" in g for g in gaps))


class TestEnvElementMissingPhase(unittest.TestCase):
    def test_empty_phases_flagged(self):
        e = _env(phases=[])
        gaps = e.validate()
        self.assertTrue(any("phase tag" in g for g in gaps))


# ---------------------------------------------------------------------------
# Tests — ContextRecord
# ---------------------------------------------------------------------------

class TestContextRecordComplete(unittest.TestCase):
    def test_complete_record_has_empty_gap_list(self):
        rec = _complete_record()
        self.assertEqual(rec.build_gap_list(), [])
        self.assertTrue(rec.is_complete())


class TestContextRecordMissingBoundary(unittest.TestCase):
    def test_missing_boundary_is_a_gap(self):
        rec = _complete_record()
        rec.product_boundary = ""
        self.assertTrue(any("product_boundary" in g for g in rec.build_gap_list()))
        self.assertFalse(rec.is_complete())


class TestContextRecordOrphanedRole(unittest.TestCase):
    def test_task_owning_role_not_in_population_is_a_gap(self):
        rec = ContextRecord(product_boundary="Some product")
        rec.roles.append(_role(name="Pilot"))
        rec.tasks.append(_task(role="Flight Engineer"))
        rec.env_elements.append(_env())
        gaps = rec.build_gap_list()
        self.assertTrue(any("Flight Engineer" in g for g in gaps))


class TestContextRecordNoRoles(unittest.TestCase):
    def test_no_roles_is_a_gap(self):
        rec = ContextRecord(product_boundary="Some product")
        rec.tasks.append(_task())
        rec.env_elements.append(_env())
        self.assertTrue(any("no user roles" in g for g in rec.build_gap_list()))


class TestContextRecordNoTasks(unittest.TestCase):
    def test_no_tasks_is_a_gap(self):
        rec = ContextRecord(product_boundary="Some product")
        rec.roles.append(_role())
        rec.env_elements.append(_env())
        self.assertTrue(any("no tasks" in g for g in rec.build_gap_list()))


class TestContextRecordNoEnvElements(unittest.TestCase):
    def test_no_env_elements_is_a_gap(self):
        rec = ContextRecord(product_boundary="Some product")
        rec.roles.append(_role())
        rec.tasks.append(_task())
        self.assertTrue(any("no environment elements" in g for g in rec.build_gap_list()))


# ---------------------------------------------------------------------------
# Tests — query helpers
# ---------------------------------------------------------------------------

class TestTasksForRole(unittest.TestCase):
    def test_returns_only_tasks_for_named_role(self):
        rec = _complete_record()
        rec.roles.append(_role(name="Engineer"))
        rec.tasks.append(_task(name="System check", role="Engineer",
                               phases=["on-orbit-nominal"]))
        result = rec.tasks_for_role("Commander")
        self.assertTrue(all(t.owning_role == "Commander" for t in result))
        self.assertEqual(len(result), 1)


class TestTasksInPhase(unittest.TestCase):
    def test_returns_tasks_tagged_with_phase(self):
        rec = _complete_record()
        rec.roles.append(_role(name="EVA Crew"))
        rec.tasks.append(_task(name="EVA ingress", role="EVA Crew",
                               phases=["eva"]))
        nominal = rec.tasks_in_phase("on-orbit-nominal")
        self.assertTrue(all("on-orbit-nominal" in t.phases or
                            "all-phases" in t.phases for t in nominal))

    def test_invalid_phase_raises(self):
        rec = _complete_record()
        with self.assertRaises(ValueError):
            rec.tasks_in_phase("hyperspace")


class TestEnvByCategory(unittest.TestCase):
    def test_physical_elements_returned(self):
        rec = _complete_record()
        rec.env_elements.append(_env(name="Crew structure", cat="organisational",
                                     desc="Three-person crew", phases=["all-phases"]))
        physical = rec.env_elements_by_category("physical")
        self.assertTrue(all(e.category == "physical" for e in physical))

    def test_invalid_category_raises(self):
        rec = _complete_record()
        with self.assertRaises(ValueError):
            rec.env_elements_by_category("technical")


class TestSafetyCriticalTasks(unittest.TestCase):
    def test_only_safety_critical_tasks_returned(self):
        rec = _complete_record()
        rec.tasks.append(_task(name="Emergency vent", role="Commander",
                               crit="safety-critical", phases=["on-orbit-contingency"]))
        sc = rec.safety_critical_tasks()
        self.assertTrue(all(t.criticality == "safety-critical" for t in sc))
        self.assertEqual(len(sc), 1)


# ---------------------------------------------------------------------------
# Tests — validate_phase helper
# ---------------------------------------------------------------------------

class TestValidatePhase(unittest.TestCase):
    def test_known_phase_returns_true(self):
        self.assertTrue(validate_phase("on-orbit-nominal"))

    def test_all_phases_sentinel_returns_true(self):
        self.assertTrue(validate_phase("all-phases"))

    def test_unknown_phase_returns_false(self):
        self.assertFalse(validate_phase("hyperspace"))

    def test_empty_string_returns_false(self):
        self.assertFalse(validate_phase(""))


if __name__ == "__main__":
    unittest.main()
