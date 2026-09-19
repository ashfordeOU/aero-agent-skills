"""Contract test for the OBCP engine-control leaf (stdlib unittest)."""

import unittest

from e7041_controlling_the_obcp_engine_logic import (
    COMMAND_ACTIVATE,
    COMMAND_HOLD_ENGINE,
    COMMAND_HOLD_PROCEDURE,
    COMMAND_LOAD,
    COMMAND_RESUME_ENGINE,
    COMMAND_RESUME_PROCEDURE,
    COMMAND_START_ENGINE,
    COMMAND_STOP_ENGINE,
    COMMAND_TERMINATE,
    ENGINE_HELD,
    ENGINE_RUNNING,
    ENGINE_STOPPED,
    FINDING_ACTIVATION_WHILE_NOT_RUNNING,
    FINDING_ALREADY_ACTIVE,
    FINDING_CAPACITY_REACHED,
    FINDING_HOLD_SUSPENDED_PROCEDURES,
    FINDING_ILLEGAL_ENGINE_TRANSITION,
    FINDING_NOTHING_TO_HOLD,
    FINDING_NOTHING_TO_RESUME,
    FINDING_RESUME_LEFT_OWN_HOLDS,
    FINDING_STOP_TERMINATED_PROCEDURES,
    FINDING_TERMINATED_CANNOT_RESUME,
    FINDING_UNKNOWN_PROCEDURE,
    PROCEDURE_HELD,
    PROCEDURE_RUNNING,
    PROCEDURE_TERMINATED,
    apply_command,
    assess_engine_control,
    live_procedures,
    new_engine,
    procedure_states,
    run_commands,
)


def engine_cmd(name):
    return {"command": name}


def proc_cmd(name, procedure_id):
    return {"command": name, "procedure_id": procedure_id}


def started_with(*procedure_ids):
    commands = [engine_cmd(COMMAND_START_ENGINE)]
    for procedure_id in procedure_ids:
        commands.append(proc_cmd(COMMAND_LOAD, procedure_id))
        commands.append(proc_cmd(COMMAND_ACTIVATE, procedure_id))
    return commands


def findings_of(result):
    return [f["finding"] for f in result["findings"]]


class TestEngineConstruction(unittest.TestCase):
    def test_a_new_engine_starts_stopped_and_empty(self):
        engine = new_engine()
        self.assertEqual(engine["state"], ENGINE_STOPPED)
        self.assertEqual(live_procedures(engine), [])

    def test_a_zero_capacity_engine_raises(self):
        with self.assertRaises(ValueError):
            new_engine(capacity=0)

    def test_a_boolean_capacity_raises(self):
        with self.assertRaises(ValueError):
            new_engine(capacity=True)

    def test_an_unknown_engine_state_raises(self):
        with self.assertRaises(ValueError):
            new_engine(state="idling")


class TestCommandValidation(unittest.TestCase):
    def test_an_unknown_command_raises(self):
        with self.assertRaises(ValueError):
            apply_command(new_engine(), {"command": "reboot-engine"})

    def test_a_procedure_command_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            apply_command(new_engine(), {"command": COMMAND_ACTIVATE})

    def test_an_engine_command_naming_a_procedure_raises(self):
        with self.assertRaises(ValueError):
            apply_command(
                new_engine(), {"command": COMMAND_START_ENGINE, "procedure_id": "P-1"}
            )

    def test_commands_must_be_a_list(self):
        with self.assertRaises(ValueError):
            run_commands(new_engine(), engine_cmd(COMMAND_START_ENGINE))

    def test_apply_command_needs_an_engine(self):
        with self.assertRaises(ValueError):
            apply_command({"state": ENGINE_RUNNING}, engine_cmd(COMMAND_STOP_ENGINE))


class TestEngineTransitions(unittest.TestCase):
    def test_starting_a_stopped_engine_runs_it(self):
        report = assess_engine_control([engine_cmd(COMMAND_START_ENGINE)])
        self.assertEqual(report["engine_state"], ENGINE_RUNNING)
        self.assertTrue(report["sequence_clean"])

    def test_starting_a_running_engine_is_refused(self):
        report = assess_engine_control(
            [engine_cmd(COMMAND_START_ENGINE), engine_cmd(COMMAND_START_ENGINE)]
        )
        self.assertIn(FINDING_ILLEGAL_ENGINE_TRANSITION, findings_of(report))
        self.assertEqual(report["engine_state"], ENGINE_RUNNING)

    def test_resuming_a_running_engine_is_refused(self):
        report = assess_engine_control(
            [engine_cmd(COMMAND_START_ENGINE), engine_cmd(COMMAND_RESUME_ENGINE)]
        )
        self.assertIn(FINDING_ILLEGAL_ENGINE_TRANSITION, findings_of(report))

    def test_a_held_engine_can_be_stopped_without_being_resumed_first(self):
        report = assess_engine_control(
            [
                engine_cmd(COMMAND_START_ENGINE),
                engine_cmd(COMMAND_HOLD_ENGINE),
                engine_cmd(COMMAND_STOP_ENGINE),
            ]
        )
        self.assertEqual(report["engine_state"], ENGINE_STOPPED)

    def test_holding_a_stopped_engine_is_refused(self):
        report = assess_engine_control([engine_cmd(COMMAND_HOLD_ENGINE)])
        self.assertEqual(report["engine_state"], ENGINE_STOPPED)
        self.assertIn(FINDING_ILLEGAL_ENGINE_TRANSITION, findings_of(report))


class TestStoppingIsDestructive(unittest.TestCase):
    def test_stopping_the_engine_terminates_its_live_procedures(self):
        report = assess_engine_control(
            started_with("OBCP-A", "OBCP-B") + [engine_cmd(COMMAND_STOP_ENGINE)]
        )
        self.assertEqual(report["terminated"], ["OBCP-A", "OBCP-B"])
        self.assertIn(FINDING_STOP_TERMINATED_PROCEDURES, findings_of(report))

    def test_a_terminated_procedure_does_not_come_back_when_the_engine_restarts(self):
        report = assess_engine_control(
            started_with("OBCP-A")
            + [engine_cmd(COMMAND_STOP_ENGINE), engine_cmd(COMMAND_START_ENGINE)]
        )
        self.assertEqual(report["running"], [])
        self.assertEqual(report["procedure_states"]["OBCP-A"], PROCEDURE_TERMINATED)

    def test_resuming_a_terminated_procedure_is_refused(self):
        report = assess_engine_control(
            started_with("OBCP-A")
            + [
                engine_cmd(COMMAND_STOP_ENGINE),
                engine_cmd(COMMAND_START_ENGINE),
                proc_cmd(COMMAND_RESUME_PROCEDURE, "OBCP-A"),
            ]
        )
        self.assertIn(FINDING_TERMINATED_CANNOT_RESUME, findings_of(report))

    def test_stopping_an_engine_with_nothing_live_reports_no_termination(self):
        report = assess_engine_control(
            [engine_cmd(COMMAND_START_ENGINE), engine_cmd(COMMAND_STOP_ENGINE)]
        )
        self.assertNotIn(FINDING_STOP_TERMINATED_PROCEDURES, findings_of(report))


class TestHoldingIsReversible(unittest.TestCase):
    def test_holding_the_engine_suspends_what_was_running(self):
        report = assess_engine_control(
            started_with("OBCP-A", "OBCP-B") + [engine_cmd(COMMAND_HOLD_ENGINE)]
        )
        self.assertEqual(report["held"], ["OBCP-A", "OBCP-B"])
        self.assertIn(FINDING_HOLD_SUSPENDED_PROCEDURES, findings_of(report))

    def test_resuming_the_engine_releases_exactly_what_the_engine_held(self):
        report = assess_engine_control(
            started_with("OBCP-A", "OBCP-B")
            + [engine_cmd(COMMAND_HOLD_ENGINE), engine_cmd(COMMAND_RESUME_ENGINE)]
        )
        self.assertEqual(report["running"], ["OBCP-A", "OBCP-B"])
        self.assertEqual(report["engine_state"], ENGINE_RUNNING)

    def test_an_individually_held_procedure_stays_held_across_the_engine_resume(self):
        report = assess_engine_control(
            started_with("OBCP-A", "OBCP-B")
            + [
                proc_cmd(COMMAND_HOLD_PROCEDURE, "OBCP-B"),
                engine_cmd(COMMAND_HOLD_ENGINE),
                engine_cmd(COMMAND_RESUME_ENGINE),
            ]
        )
        self.assertEqual(report["running"], ["OBCP-A"])
        self.assertEqual(report["held"], ["OBCP-B"])
        self.assertIn(FINDING_RESUME_LEFT_OWN_HOLDS, findings_of(report))

    def test_holding_a_procedure_that_is_not_running_is_refused(self):
        report = assess_engine_control(
            [
                engine_cmd(COMMAND_START_ENGINE),
                proc_cmd(COMMAND_LOAD, "OBCP-A"),
                proc_cmd(COMMAND_HOLD_PROCEDURE, "OBCP-A"),
            ]
        )
        self.assertIn(FINDING_NOTHING_TO_HOLD, findings_of(report))

    def test_resuming_a_procedure_that_is_not_held_is_refused(self):
        report = assess_engine_control(
            started_with("OBCP-A") + [proc_cmd(COMMAND_RESUME_PROCEDURE, "OBCP-A")]
        )
        self.assertIn(FINDING_NOTHING_TO_RESUME, findings_of(report))


class TestActivation(unittest.TestCase):
    def test_activation_into_a_stopped_engine_is_refused(self):
        report = assess_engine_control(
            [proc_cmd(COMMAND_LOAD, "OBCP-A"), proc_cmd(COMMAND_ACTIVATE, "OBCP-A")]
        )
        self.assertIn(FINDING_ACTIVATION_WHILE_NOT_RUNNING, findings_of(report))
        self.assertEqual(report["running"], [])

    def test_activation_into_a_held_engine_is_refused(self):
        report = assess_engine_control(
            [
                engine_cmd(COMMAND_START_ENGINE),
                engine_cmd(COMMAND_HOLD_ENGINE),
                proc_cmd(COMMAND_LOAD, "OBCP-A"),
                proc_cmd(COMMAND_ACTIVATE, "OBCP-A"),
            ]
        )
        self.assertIn(FINDING_ACTIVATION_WHILE_NOT_RUNNING, findings_of(report))
        self.assertEqual(report["engine_state"], ENGINE_HELD)

    def test_activating_a_procedure_that_was_never_loaded_is_refused(self):
        report = assess_engine_control(
            [engine_cmd(COMMAND_START_ENGINE), proc_cmd(COMMAND_ACTIVATE, "OBCP-GHOST")]
        )
        self.assertIn(FINDING_UNKNOWN_PROCEDURE, findings_of(report))

    def test_activating_a_live_procedure_twice_is_refused(self):
        report = assess_engine_control(
            started_with("OBCP-A") + [proc_cmd(COMMAND_ACTIVATE, "OBCP-A")]
        )
        self.assertIn(FINDING_ALREADY_ACTIVE, findings_of(report))

    def test_activation_past_the_engine_limit_is_refused_not_queued(self):
        report = assess_engine_control(started_with("OBCP-A", "OBCP-B"), capacity=1)
        self.assertIn(FINDING_CAPACITY_REACHED, findings_of(report))
        self.assertEqual(report["running"], ["OBCP-A"])

    def test_a_held_procedure_still_counts_against_the_engine_limit(self):
        report = assess_engine_control(
            started_with("OBCP-A")
            + [
                proc_cmd(COMMAND_HOLD_PROCEDURE, "OBCP-A"),
                proc_cmd(COMMAND_LOAD, "OBCP-B"),
                proc_cmd(COMMAND_ACTIVATE, "OBCP-B"),
            ],
            capacity=1,
        )
        self.assertIn(FINDING_CAPACITY_REACHED, findings_of(report))

    def test_terminating_a_procedure_frees_its_capacity(self):
        report = assess_engine_control(
            started_with("OBCP-A")
            + [
                proc_cmd(COMMAND_TERMINATE, "OBCP-A"),
                proc_cmd(COMMAND_LOAD, "OBCP-B"),
                proc_cmd(COMMAND_ACTIVATE, "OBCP-B"),
            ],
            capacity=1,
        )
        self.assertEqual(report["running"], ["OBCP-B"])
        self.assertEqual(report["spare_capacity"], 0)


class TestReporting(unittest.TestCase):
    def test_every_finding_carries_the_index_of_the_command_that_raised_it(self):
        report = assess_engine_control(
            [engine_cmd(COMMAND_START_ENGINE), engine_cmd(COMMAND_START_ENGINE)]
        )
        self.assertEqual(report["findings"][0]["index"], 1)

    def test_procedure_states_show_every_procedure_the_engine_knows(self):
        engine = new_engine()
        run_commands(
            engine,
            [proc_cmd(COMMAND_LOAD, "OBCP-A"), proc_cmd(COMMAND_LOAD, "OBCP-B")],
        )
        self.assertEqual(sorted(procedure_states(engine)), ["OBCP-A", "OBCP-B"])

    def test_spare_capacity_falls_as_procedures_go_live(self):
        report = assess_engine_control(started_with("OBCP-A"), capacity=3)
        self.assertEqual(report["spare_capacity"], 2)
        self.assertEqual(report["procedure_states"]["OBCP-A"], PROCEDURE_RUNNING)

    def test_a_held_procedure_is_reported_as_held_not_running(self):
        report = assess_engine_control(
            started_with("OBCP-A") + [proc_cmd(COMMAND_HOLD_PROCEDURE, "OBCP-A")]
        )
        self.assertEqual(report["procedure_states"]["OBCP-A"], PROCEDURE_HELD)
        self.assertEqual(report["held"], ["OBCP-A"])


if __name__ == "__main__":
    unittest.main()
