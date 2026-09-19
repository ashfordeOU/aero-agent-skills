"""Contract tests for the clause 6.22.7.2 sub-schedule enable/disable logic."""

import unittest

from e7041_enabling_and_disabling_position_based_sub_schedules_logic import (
    ACTIONS,
    DEFAULT_IMMINENT_ARC_DEG,
    FULL_REVOLUTION_DEG,
    apply_status_instructions,
    assess_status_request,
    effective_status,
    forward_arc_deg,
    imminent_on_enable,
    missed_releases,
    normalize_position_deg,
    position_in_arc,
    rearm_arcs,
    status_report,
    validate_activities,
    validate_instruction,
    validate_status_map,
)

STATUS = {"routine": True, "eclipse": False, "contingency": False}


def activities():
    return [
        {"activity_id": "a1", "sub_schedule": "routine", "release_position_deg": 30.0},
        {"activity_id": "a2", "sub_schedule": "eclipse", "release_position_deg": 80.0},
        {"activity_id": "a3", "sub_schedule": "eclipse", "release_position_deg": 200.0},
        {"activity_id": "a4", "sub_schedule": "contingency", "release_position_deg": 355.0},
    ]


def enable(name):
    return {"action": "enable", "sub_schedule": name}


def disable(name):
    return {"action": "disable", "sub_schedule": name}


class ArcTests(unittest.TestCase):
    def test_position_wraps_into_one_revolution(self):
        self.assertAlmostEqual(normalize_position_deg(365.0), 5.0, places=9)

    def test_forward_arc_crosses_the_wrap_point(self):
        self.assertAlmostEqual(forward_arc_deg(300.0, 20.0), 80.0, places=9)

    def test_position_inside_a_swept_arc(self):
        self.assertTrue(position_in_arc(50.0, 10.0, 90.0))

    def test_position_outside_a_swept_arc(self):
        self.assertFalse(position_in_arc(120.0, 10.0, 90.0))

    def test_position_exactly_on_the_arc_end_counts_as_swept(self):
        self.assertTrue(position_in_arc(90.0, 10.0, 90.0))

    def test_swept_arc_wraps_past_the_revolution_boundary(self):
        self.assertTrue(position_in_arc(355.0, 340.0, 20.0))


class ValidationTests(unittest.TestCase):
    def test_status_map_is_returned_validated(self):
        self.assertEqual(validate_status_map(STATUS), STATUS)

    def test_empty_status_map_rejected(self):
        with self.assertRaises(ValueError):
            validate_status_map({})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_status_map({"routine": 1})

    def test_activity_in_an_undeclared_sub_schedule_rejected(self):
        bad = activities() + [
            {"activity_id": "a9", "sub_schedule": "ghost", "release_position_deg": 1.0}
        ]
        with self.assertRaises(ValueError):
            validate_activities(bad, STATUS)

    def test_duplicate_activity_id_rejected(self):
        bad = activities() + [dict(activities()[0])]
        with self.assertRaises(ValueError):
            validate_activities(bad, STATUS)

    def test_activities_are_ordered_by_release_position(self):
        positions = [rec["release_position_deg"] for rec in validate_activities(activities(), STATUS)]
        self.assertEqual(positions, sorted(positions))

    def test_instruction_action_is_normalized(self):
        record = validate_instruction({"action": " Enable ", "sub_schedule": "routine"})
        self.assertEqual(record["action"], "enable")

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_instruction({"action": "toggle", "sub_schedule": "routine"})

    def test_declared_actions_are_exactly_two(self):
        self.assertEqual(set(ACTIONS), {"enable", "disable"})


class ApplyTests(unittest.TestCase):
    def test_enable_changes_the_flag(self):
        out = apply_status_instructions(STATUS, [enable("eclipse")])
        self.assertTrue(out["status_after"]["eclipse"])

    def test_disable_changes_the_flag(self):
        out = apply_status_instructions(STATUS, [disable("routine")])
        self.assertFalse(out["status_after"]["routine"])

    def test_unknown_sub_schedule_rejected_without_stopping_the_request(self):
        out = apply_status_instructions(STATUS, [enable("ghost"), enable("eclipse")])
        self.assertEqual(out["rejected"][0]["reason"], "unknown-sub-schedule")
        self.assertTrue(out["status_after"]["eclipse"])

    def test_malformed_instruction_rejected_without_stopping_the_request(self):
        out = apply_status_instructions(STATUS, [{"action": "toggle", "sub_schedule": "eclipse"},
                                                 enable("eclipse")])
        self.assertEqual(out["rejected"][0]["reason"], "malformed-instruction")
        self.assertTrue(out["status_after"]["eclipse"])

    def test_restating_the_current_state_is_accepted_and_inert(self):
        out = apply_status_instructions(STATUS, [enable("routine")])
        self.assertEqual(out["applied"], [])
        self.assertEqual(len(out["no_change"]), 1)
        self.assertTrue(out["status_after"]["routine"])

    def test_double_enable_is_idempotent(self):
        once = apply_status_instructions(STATUS, [enable("eclipse")])["status_after"]
        twice = apply_status_instructions(once, [enable("eclipse")])["status_after"]
        self.assertEqual(once, twice)

    def test_last_instruction_on_one_sub_schedule_stands(self):
        out = apply_status_instructions(STATUS, [enable("eclipse"), disable("eclipse")])
        self.assertFalse(out["status_after"]["eclipse"])
        self.assertEqual(out["superseded"][0]["sub_schedule"], "eclipse")

    def test_other_sub_schedules_are_untouched(self):
        out = apply_status_instructions(STATUS, [enable("eclipse")])
        self.assertTrue(out["status_after"]["routine"])
        self.assertFalse(out["status_after"]["contingency"])

    def test_empty_request_rejected(self):
        with self.assertRaises(ValueError):
            apply_status_instructions(STATUS, [])

    def test_input_status_map_is_not_mutated(self):
        apply_status_instructions(STATUS, [disable("routine")])
        self.assertTrue(STATUS["routine"])


class EffectiveStatusTests(unittest.TestCase):
    def test_both_gates_open_permits_release(self):
        self.assertTrue(effective_status(True, STATUS)["routine"])

    def test_disabled_sub_schedule_blocks_release(self):
        self.assertFalse(effective_status(True, STATUS)["eclipse"])

    def test_disabled_schedule_blocks_every_sub_schedule(self):
        self.assertEqual(set(effective_status(False, STATUS).values()), {False})

    def test_non_boolean_schedule_state_rejected(self):
        with self.assertRaises(ValueError):
            effective_status("on", STATUS)


class RetentionTests(unittest.TestCase):
    def test_disabling_does_not_remove_activities(self):
        out = apply_status_instructions(STATUS, [disable("routine")])
        held = validate_activities(activities(), out["status_after"])
        self.assertEqual(len(held), 4)

    def test_release_point_swept_while_disabled_is_missed(self):
        missed = missed_releases(activities(), STATUS, 60.0, 100.0)
        self.assertEqual([rec["activity_id"] for rec in missed], ["a2"])

    def test_release_point_swept_while_enabled_is_not_missed(self):
        missed = missed_releases(activities(), STATUS, 10.0, 50.0)
        self.assertEqual(missed, [])

    def test_disabled_schedule_makes_every_swept_point_missed(self):
        missed = missed_releases(activities(), STATUS, 10.0, 50.0, schedule_enabled=False)
        self.assertEqual([rec["activity_id"] for rec in missed], ["a1"])

    def test_missed_search_wraps_past_the_revolution_boundary(self):
        missed = missed_releases(activities(), STATUS, 340.0, 10.0)
        self.assertEqual([rec["activity_id"] for rec in missed], ["a4"])

    def test_rearm_arc_gives_the_remaining_arc(self):
        arcs = rearm_arcs(activities(), STATUS, 100.0, "eclipse")
        self.assertEqual(arcs[0]["activity_id"], "a3")
        self.assertAlmostEqual(arcs[0]["arc_ahead_deg"], 100.0, places=9)

    def test_rearm_arc_of_a_passed_point_is_nearly_a_revolution(self):
        arcs = rearm_arcs(activities(), STATUS, 90.0, "eclipse")
        passed = [rec for rec in arcs if rec["activity_id"] == "a2"][0]
        self.assertAlmostEqual(passed["arc_ahead_deg"], 350.0, places=9)

    def test_rearm_arc_rejects_an_undeclared_sub_schedule(self):
        with self.assertRaises(ValueError):
            rearm_arcs(activities(), STATUS, 0.0, "ghost")


class ImminentOnEnableTests(unittest.TestCase):
    def test_newly_enabled_sub_schedule_reports_an_imminent_release(self):
        after = apply_status_instructions(STATUS, [enable("eclipse")])["status_after"]
        ahead = imminent_on_enable(activities(), STATUS, after, 75.0, 10.0)
        self.assertEqual([rec["activity_id"] for rec in ahead], ["a2"])

    def test_already_enabled_sub_schedule_is_not_reported(self):
        after = apply_status_instructions(STATUS, [enable("routine")])["status_after"]
        self.assertEqual(imminent_on_enable(activities(), STATUS, after, 25.0, 10.0), [])

    def test_distant_activity_in_a_newly_enabled_sub_schedule_is_not_imminent(self):
        after = apply_status_instructions(STATUS, [enable("eclipse")])["status_after"]
        self.assertEqual(imminent_on_enable(activities(), STATUS, after, 120.0, 10.0), [])

    def test_nothing_is_imminent_while_the_schedule_is_disabled(self):
        after = apply_status_instructions(STATUS, [enable("eclipse")])["status_after"]
        self.assertEqual(
            imminent_on_enable(activities(), STATUS, after, 75.0, 10.0, schedule_enabled=False),
            [],
        )

    def test_negative_arc_rejected(self):
        after = apply_status_instructions(STATUS, [enable("eclipse")])["status_after"]
        with self.assertRaises(ValueError):
            imminent_on_enable(activities(), STATUS, after, 75.0, -1.0)

    def test_default_imminent_arc_is_a_small_fraction_of_a_revolution(self):
        self.assertLess(DEFAULT_IMMINENT_ARC_DEG, FULL_REVOLUTION_DEG / 12.0)


class ReportTests(unittest.TestCase):
    def test_report_covers_every_declared_sub_schedule(self):
        rows = status_report(activities(), STATUS)
        self.assertEqual([row["sub_schedule"] for row in rows],
                         ["contingency", "eclipse", "routine"])

    def test_report_counts_the_load_of_each_sub_schedule(self):
        rows = status_report(activities(), STATUS)
        eclipse = [row for row in rows if row["sub_schedule"] == "eclipse"][0]
        self.assertEqual(eclipse["activity_count"], 2)

    def test_report_separates_the_flag_from_the_effective_gate(self):
        rows = status_report(activities(), STATUS, schedule_enabled=False)
        routine = [row for row in rows if row["sub_schedule"] == "routine"][0]
        self.assertTrue(routine["enabled"])
        self.assertFalse(routine["releasable"])


class AssessmentTests(unittest.TestCase):
    def base(self, **extra):
        spec = {"status": STATUS, "instructions": [enable("eclipse")],
                "activities": activities()}
        spec.update(extra)
        return spec

    def test_activities_are_retained_across_the_request(self):
        result = assess_status_request(self.base(instructions=[disable("routine")]))
        self.assertEqual(result["activities_retained"], 4)

    def test_disabling_a_loaded_sub_schedule_reports_retention(self):
        result = assess_status_request(self.base(instructions=[disable("routine")]))
        self.assertTrue(any("retained, not deleted" in note for note in result["findings"]))

    def test_rejected_instruction_is_reported_as_partial(self):
        result = assess_status_request(self.base(instructions=[enable("ghost"), enable("eclipse")]))
        self.assertTrue(any("rest of the request" in note for note in result["findings"]))
        self.assertTrue(result["status_after"]["eclipse"])

    def test_inert_instruction_is_reported(self):
        result = assess_status_request(self.base(instructions=[enable("routine")]))
        self.assertTrue(any("already in the requested state" in note for note in result["findings"]))

    def test_double_instruction_is_reported(self):
        result = assess_status_request(
            self.base(instructions=[enable("eclipse"), disable("eclipse")])
        )
        self.assertTrue(any("acted on twice" in note for note in result["findings"]))

    def test_missed_releases_reported_over_a_swept_arc(self):
        result = assess_status_request(
            self.base(instructions=[disable("routine")], swept_from_deg=20.0,
                      current_position_deg=40.0)
        )
        self.assertTrue(any("swept while their sub-schedule was disabled" in note
                            for note in result["findings"]))

    def test_imminent_release_reported_on_enable(self):
        result = assess_status_request(
            self.base(current_position_deg=75.0, imminent_arc_deg=10.0)
        )
        self.assertEqual([rec["activity_id"] for rec in result["imminent_on_enable"]], ["a2"])

    def test_disabled_schedule_is_reported(self):
        result = assess_status_request(self.base(schedule_enabled=False))
        self.assertTrue(any("schedule itself is disabled" in note for note in result["findings"]))

    def test_effective_status_combines_both_gates(self):
        result = assess_status_request(self.base())
        self.assertTrue(result["effective_status"]["eclipse"])
        self.assertFalse(result["effective_status"]["contingency"])

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_status_request({"status": STATUS, "instructions": [enable("eclipse")]})


if __name__ == "__main__":
    unittest.main()
