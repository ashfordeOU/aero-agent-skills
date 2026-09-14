#!/usr/bin/env python3
"""Contract test for the protection diode qualification programme, clause 9.5.3 (offline)."""

import copy
import unittest

from e2008_external_diode_qualification_plan_logic import (
    ACTIVITY_OUT_OF_SEQUENCE,
    ACTIVITY_PROVENANCE_MISMATCH,
    ACTIVITY_SOUND,
    ACTIVITY_SPECIMENS_SHORT,
    DEFAULT_DIODE_PLAN_POLICY,
    PROGRAMME_COMPLETE,
    PROGRAMME_INCOMPLETE,
    QUALIFICATION_LEVELS,
    REQUIRED_LEVEL_ACTIVITIES,
    activity_level,
    assembly_start_barrier,
    assess_diode_qualification_plan,
    assess_planned_activity,
    level_coverage,
    min_specimens_for_level,
    qualification_levels,
    required_level_activities,
    specimen_provenance,
    specimen_sufficiency,
    validate_diode_plan_policy,
    worst_arm,
)

BARE = "bare-protection-diode"
ASSEMBLY = "protection-diode-assembly"
LOTS = ["lot-d1", "lot-d2"]


def _entry(activity, sequence, specimens=None, lots=None, **overrides):
    level = activity_level(activity)
    entry = {
        "activity": activity,
        "level": level,
        "sequence": sequence,
        "specimen_count": specimens
        if specimens is not None
        else (8 if level == BARE else 6),
        "specimen_lot_ids": list(lots if lots is not None else LOTS),
    }
    entry.update(overrides)
    return entry


def _activities():
    entries = []
    step = 1
    for activity in REQUIRED_LEVEL_ACTIVITIES[BARE]:
        entries.append(_entry(activity, step))
        step += 1
    for activity in REQUIRED_LEVEL_ACTIVITIES[ASSEMBLY]:
        entries.append(_entry(activity, step))
        step += 1
    return entries


def _plan(activities=None, **overrides):
    plan = {
        "programme_id": "qp-diode-2026",
        "diode_lot_ids": list(LOTS),
        "activities": activities if activities is not None else _activities(),
    }
    plan.update(overrides)
    return plan


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_plan_policy(DEFAULT_DIODE_PLAN_POLICY),
            DEFAULT_DIODE_PLAN_POLICY,
        )

    def test_default_policy_asks_for_more_bare_diodes_than_assemblies(self):
        self.assertGreater(
            DEFAULT_DIODE_PLAN_POLICY["min_bare_diode_specimens"],
            DEFAULT_DIODE_PLAN_POLICY["min_assembly_specimens"],
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_plan_policy("test everything twice")

    def test_zero_specimen_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_PLAN_POLICY)
        broken["min_assembly_specimens"] = 0
        with self.assertRaises(ValueError):
            validate_diode_plan_policy(broken)

    def test_out_of_range_planned_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_PLAN_POLICY)
        broken["min_planned_activity_fraction"] = 2.0
        with self.assertRaises(ValueError):
            validate_diode_plan_policy(broken)

    def test_non_boolean_sequence_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_PLAN_POLICY)
        broken["require_bare_level_before_assembly"] = "later"
        with self.assertRaises(ValueError):
            validate_diode_plan_policy(broken)


class LevelTests(unittest.TestCase):
    def test_both_levels_are_offered(self):
        self.assertEqual(qualification_levels(), QUALIFICATION_LEVELS)
        self.assertIn(ASSEMBLY, qualification_levels())

    def test_each_level_owns_its_activity_set(self):
        bare = set(required_level_activities(BARE))
        assembly = set(required_level_activities(ASSEMBLY))
        self.assertEqual(bare & assembly, set())

    def test_an_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            required_level_activities("coverglass")

    def test_an_activity_resolves_to_its_level(self):
        self.assertEqual(activity_level("diode-assembly-thermal-cycling"), ASSEMBLY)
        self.assertEqual(activity_level("bare-diode-thermal-cycling"), BARE)

    def test_an_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            activity_level("diode-smoke-test")

    def test_the_specimen_minimum_follows_the_level(self):
        self.assertEqual(
            min_specimens_for_level(BARE),
            DEFAULT_DIODE_PLAN_POLICY["min_bare_diode_specimens"],
        )
        self.assertEqual(
            min_specimens_for_level(ASSEMBLY),
            DEFAULT_DIODE_PLAN_POLICY["min_assembly_specimens"],
        )

    def test_an_unknown_level_has_no_specimen_minimum(self):
        with self.assertRaises(ValueError):
            min_specimens_for_level("diode-drawing")


class SpecimenTests(unittest.TestCase):
    def test_a_full_activity_carries_enough_specimens(self):
        result = specimen_sufficiency(_entry("bare-diode-thermal-cycling", 4))
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["shortfall"], 0)

    def test_a_short_bare_activity_reports_its_shortfall(self):
        result = specimen_sufficiency(
            _entry("bare-diode-thermal-cycling", 4, specimens=2)
        )
        self.assertFalse(result["sufficient"])
        self.assertEqual(result["shortfall"], 4)

    def test_an_assembly_activity_is_judged_on_the_assembly_minimum(self):
        result = specimen_sufficiency(
            _entry("diode-assembly-thermal-cycling", 9, specimens=5)
        )
        self.assertTrue(result["sufficient"])

    def test_a_negative_specimen_count_rejected(self):
        entry = _entry("bare-diode-thermal-cycling", 4, specimens=0)
        entry["specimen_count"] = -1
        with self.assertRaises(ValueError):
            specimen_sufficiency(entry)

    def test_a_non_integer_specimen_count_rejected(self):
        entry = _entry("bare-diode-thermal-cycling", 4)
        entry["specimen_count"] = "eight"
        with self.assertRaises(ValueError):
            specimen_sufficiency(entry)

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            specimen_sufficiency("bare-diode-thermal-cycling")


class ProvenanceTests(unittest.TestCase):
    def test_specimens_from_the_named_lots_are_traceable(self):
        result = specimen_provenance(_entry("bare-diode-thermal-cycling", 4), LOTS)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["foreign_lot_ids"], [])

    def test_an_assembly_built_from_a_foreign_lot_is_named(self):
        entry = _entry("diode-assembly-thermal-cycling", 9, lots=["lot-d1", "lot-x9"])
        result = specimen_provenance(entry, LOTS)
        self.assertFalse(result["traceable"])
        self.assertEqual(result["foreign_lot_ids"], ["lot-x9"])

    def test_an_empty_specimen_lot_list_rejected(self):
        entry = _entry("bare-diode-thermal-cycling", 4)
        entry["specimen_lot_ids"] = []
        with self.assertRaises(ValueError):
            specimen_provenance(entry, LOTS)

    def test_an_empty_programme_lot_list_rejected(self):
        with self.assertRaises(ValueError):
            specimen_provenance(_entry("bare-diode-thermal-cycling", 4), [])


class SequenceTests(unittest.TestCase):
    def test_the_barrier_is_the_last_bare_level_step(self):
        self.assertEqual(assembly_start_barrier(_activities()), 5)

    def test_a_plan_with_no_bare_level_has_no_barrier(self):
        entries = [
            _entry(a, i + 1)
            for i, a in enumerate(REQUIRED_LEVEL_ACTIVITIES[ASSEMBLY])
        ]
        self.assertIsNone(assembly_start_barrier(entries))

    def test_a_zero_sequence_rejected(self):
        entry = _entry("bare-diode-thermal-cycling", 1)
        entry["sequence"] = 0
        with self.assertRaises(ValueError):
            assembly_start_barrier([entry])

    def test_non_sequence_entries_rejected(self):
        with self.assertRaises(ValueError):
            assembly_start_barrier("activities")


class ActivityVerdictTests(unittest.TestCase):
    def test_a_sound_activity_reads_back_sound(self):
        result = assess_planned_activity(
            _entry("bare-diode-thermal-cycling", 4), LOTS, 5
        )
        self.assertEqual(result["verdict"], ACTIVITY_SOUND)
        self.assertTrue(result["sound"])

    def test_a_foreign_lot_outranks_a_short_campaign(self):
        entry = _entry(
            "diode-assembly-thermal-cycling", 9, specimens=1, lots=["lot-x9"]
        )
        result = assess_planned_activity(entry, LOTS, 5)
        self.assertEqual(result["verdict"], ACTIVITY_PROVENANCE_MISMATCH)

    def test_a_short_campaign_outranks_a_sequence_error(self):
        entry = _entry("diode-assembly-thermal-cycling", 2, specimens=1)
        result = assess_planned_activity(entry, LOTS, 5)
        self.assertEqual(result["verdict"], ACTIVITY_SPECIMENS_SHORT)

    def test_an_assembly_activity_before_the_barrier_is_out_of_sequence(self):
        entry = _entry("diode-assembly-thermal-cycling", 3)
        result = assess_planned_activity(entry, LOTS, 5)
        self.assertEqual(result["verdict"], ACTIVITY_OUT_OF_SEQUENCE)

    def test_an_assembly_activity_on_the_barrier_step_is_out_of_sequence(self):
        entry = _entry("diode-assembly-thermal-cycling", 5)
        result = assess_planned_activity(entry, LOTS, 5)
        self.assertEqual(result["verdict"], ACTIVITY_OUT_OF_SEQUENCE)

    def test_a_bare_activity_is_never_held_by_the_barrier(self):
        entry = _entry("bare-diode-thermal-cycling", 2)
        result = assess_planned_activity(entry, LOTS, 5)
        self.assertEqual(result["verdict"], ACTIVITY_SOUND)

    def test_the_sequence_rule_can_be_relaxed_by_policy(self):
        policy = copy.deepcopy(DEFAULT_DIODE_PLAN_POLICY)
        policy["require_bare_level_before_assembly"] = False
        entry = _entry("diode-assembly-thermal-cycling", 3)
        result = assess_planned_activity(entry, LOTS, 5, policy)
        self.assertEqual(result["verdict"], ACTIVITY_SOUND)

    def test_the_provenance_rule_can_be_relaxed_by_policy(self):
        policy = copy.deepcopy(DEFAULT_DIODE_PLAN_POLICY)
        policy["require_specimen_provenance"] = False
        entry = _entry("diode-assembly-thermal-cycling", 9, lots=["lot-x9"])
        result = assess_planned_activity(entry, LOTS, 5, policy)
        self.assertEqual(result["verdict"], ACTIVITY_SOUND)

    def test_a_mislabelled_level_rejected(self):
        entry = _entry("diode-assembly-thermal-cycling", 9, level=BARE)
        with self.assertRaises(ValueError):
            assess_planned_activity(entry, LOTS, 5)

    def test_findings_name_the_activity(self):
        entry = _entry("diode-assembly-thermal-cycling", 9, specimens=1)
        result = assess_planned_activity(entry, LOTS, 5)
        self.assertTrue(
            any("diode-assembly-thermal-cycling" in f for f in result["findings"])
        )


class CoverageTests(unittest.TestCase):
    def test_a_full_plan_covers_both_levels(self):
        entries = _activities()
        self.assertTrue(level_coverage(entries, BARE)["complete"])
        self.assertTrue(level_coverage(entries, ASSEMBLY)["complete"])

    def test_a_dropped_assembly_activity_is_named(self):
        entries = [
            e
            for e in _activities()
            if e["activity"] != "diode-assembly-humidity-exposure"
        ]
        result = level_coverage(entries, ASSEMBLY)
        self.assertEqual(
            result["missing_activities"], ["diode-assembly-humidity-exposure"]
        )

    def test_a_bare_only_plan_leaves_the_assembly_level_empty(self):
        entries = [e for e in _activities() if e["level"] == BARE]
        result = level_coverage(entries, ASSEMBLY)
        self.assertEqual(result["planned_activities"], [])
        self.assertFalse(result["complete"])

    def test_non_sequence_entries_rejected_for_coverage(self):
        with self.assertRaises(ValueError):
            level_coverage("activities", BARE)


class WorstArmTests(unittest.TestCase):
    def test_provenance_outranks_everything(self):
        self.assertEqual(
            worst_arm([ACTIVITY_OUT_OF_SEQUENCE, ACTIVITY_PROVENANCE_MISMATCH]),
            ACTIVITY_PROVENANCE_MISMATCH,
        )

    def test_a_sound_plan_has_no_arm_to_close(self):
        self.assertIsNone(worst_arm([ACTIVITY_SOUND, ACTIVITY_SOUND]))

    def test_non_sequence_verdicts_rejected(self):
        with self.assertRaises(ValueError):
            worst_arm(42)


class ProgrammeTests(unittest.TestCase):
    def test_a_full_programme_is_complete(self):
        result = assess_diode_qualification_plan(_plan())
        self.assertEqual(result["verdict"], PROGRAMME_COMPLETE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["both_levels_covered"])

    def test_a_bare_only_programme_is_incomplete(self):
        entries = [e for e in _activities() if e["level"] == BARE]
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertEqual(result["verdict"], PROGRAMME_INCOMPLETE)
        self.assertFalse(result["level_coverage"][ASSEMBLY]["complete"])

    def test_an_assembly_only_programme_has_no_barrier(self):
        entries = [
            _entry(a, i + 1)
            for i, a in enumerate(REQUIRED_LEVEL_ACTIVITIES[ASSEMBLY])
        ]
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertIsNone(result["assembly_start_barrier"])
        self.assertTrue(
            any("no bare-diode level" in f for f in result["findings"])
        )

    def test_the_planned_share_is_reported(self):
        entries = [
            e
            for e in _activities()
            if e["activity"] != "diode-assembly-humidity-exposure"
        ]
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertAlmostEqual(
            result["planned_activity_fraction"], 9.0 / 10.0, places=9
        )

    def test_a_full_programme_plans_every_activity(self):
        result = assess_diode_qualification_plan(_plan())
        self.assertAlmostEqual(result["planned_activity_fraction"], 1.0, places=9)

    def test_a_short_campaign_blocks_the_programme(self):
        entries = _activities()
        entries[0]["specimen_count"] = 1
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertEqual(result["verdict"], PROGRAMME_INCOMPLETE)
        self.assertEqual(result["open_activities"], [entries[0]["activity"]])

    def test_activities_are_grouped_by_verdict(self):
        entries = _activities()
        entries[-1]["specimen_lot_ids"] = ["lot-x9"]
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertEqual(
            result["grouped_by_verdict"][ACTIVITY_PROVENANCE_MISMATCH],
            [entries[-1]["activity"]],
        )

    def test_the_arm_to_close_first_is_named(self):
        entries = _activities()
        entries[-1]["specimen_lot_ids"] = ["lot-x9"]
        entries[-2]["specimen_count"] = 1
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertEqual(result["close_first"], ACTIVITY_PROVENANCE_MISMATCH)

    def test_an_assembly_scheduled_inside_the_bare_level_is_caught(self):
        entries = _activities()
        for entry in entries:
            if entry["level"] == ASSEMBLY:
                entry["sequence"] = 2
                break
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertEqual(result["verdict"], PROGRAMME_INCOMPLETE)
        self.assertEqual(result["close_first"], ACTIVITY_OUT_OF_SEQUENCE)

    def test_assessments_come_back_in_level_then_activity_order(self):
        result = assess_diode_qualification_plan(_plan())
        keys = [
            (entry["level"], entry["activity"])
            for entry in result["activity_assessments"]
        ]
        self.assertEqual(keys, sorted(keys))

    def test_a_repeated_activity_rejected(self):
        entries = _activities()
        entries.append(_entry("bare-diode-thermal-cycling", 11))
        with self.assertRaises(ValueError):
            assess_diode_qualification_plan(_plan(entries))

    def test_an_empty_activity_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_qualification_plan(_plan([]))

    def test_a_plan_without_an_identifier_rejected(self):
        plan = _plan()
        del plan["programme_id"]
        with self.assertRaises(ValueError):
            assess_diode_qualification_plan(plan)

    def test_a_plan_without_diode_lots_rejected(self):
        plan = _plan()
        plan["diode_lot_ids"] = []
        with self.assertRaises(ValueError):
            assess_diode_qualification_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_qualification_plan(_activities())

    def test_the_programme_carries_every_activity_finding(self):
        entries = _activities()
        entries[0]["specimen_count"] = 1
        result = assess_diode_qualification_plan(_plan(entries))
        self.assertTrue(any("minimum of" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
