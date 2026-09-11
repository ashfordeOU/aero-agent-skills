"""
test_e1011_verif_sim.py
Offline deterministic unit tests for e1011_verif_sim_logic.py.
stdlib unittest only. Run: python3 test_e1011_verif_sim.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_verif_sim_logic import (
    Scenario,
    Participant,
    ScenarioResult,
    SimulationError,
    check_participant_qualifications,
    check_scenario_coverage,
    count_qualified_in_result,
    evaluate_scenario_result,
    run_simulation_verification,
)


def _make_scenario(sid="S1", tasks=None, req=2, min_tc=0.90, max_er=0.10, max_wl=7.0):
    return Scenario(
        sid,
        tasks or ["task-a", "task-b"],
        req,
        min_task_completion=min_tc,
        max_error_rate=max_er,
        max_workload_rating=max_wl,
    )


def _make_participant(pid="P1", role="commander", qualified=True):
    return Participant(pid, role, qualified)


def _make_result(sid="S1", pids=None, tc=0.95, er=0.05, wl=None):
    return ScenarioResult(
        sid,
        pids or ["P1", "P2"],
        tc,
        er,
        wl or [5.0, 6.0],
    )


class TestScenarioConstruction(unittest.TestCase):
    def test_valid_scenario_constructs(self):
        s = _make_scenario()
        self.assertEqual(s.scenario_id, "S1")
        self.assertEqual(s.required_participant_count, 2)

    def test_empty_scenario_id_raises(self):
        with self.assertRaises(SimulationError):
            Scenario("", ["task"], 1)

    def test_empty_task_list_raises(self):
        with self.assertRaises(SimulationError):
            Scenario("S1", [], 1)

    def test_zero_participant_count_raises(self):
        with self.assertRaises(SimulationError):
            Scenario("S1", ["t"], 0)

    def test_defaults_applied_when_criteria_omitted(self):
        s = Scenario("S1", ["t"], 1)
        self.assertEqual(s.min_task_completion, 0.90)
        self.assertEqual(s.max_error_rate, 0.10)
        self.assertEqual(s.max_workload_rating, 7.0)


class TestParticipantConstruction(unittest.TestCase):
    def test_valid_participant_constructs(self):
        p = _make_participant("P1", "pilot")
        self.assertTrue(p.qualified)

    def test_unknown_role_raises(self):
        with self.assertRaises(SimulationError):
            Participant("P1", "tourist", True)

    def test_non_bool_qualified_raises(self):
        with self.assertRaises(SimulationError):
            Participant("P1", "commander", "yes")

    def test_empty_participant_id_raises(self):
        with self.assertRaises(SimulationError):
            Participant("", "commander", True)


class TestScenarioResultConstruction(unittest.TestCase):
    def test_valid_result_constructs(self):
        r = _make_result()
        self.assertEqual(r.scenario_id, "S1")

    def test_task_completion_above_one_raises(self):
        with self.assertRaises(SimulationError):
            _make_result(tc=1.01)

    def test_error_rate_below_zero_raises(self):
        with self.assertRaises(SimulationError):
            _make_result(er=-0.01)

    def test_workload_rating_out_of_range_raises(self):
        with self.assertRaises(SimulationError):
            _make_result(wl=[11.0])

    def test_workload_rating_zero_raises(self):
        with self.assertRaises(SimulationError):
            _make_result(wl=[0.0])

    def test_empty_participant_ids_raises(self):
        with self.assertRaises(SimulationError):
            ScenarioResult("S1", [], 0.9, 0.05, [5.0])


class TestParticipantQualifications(unittest.TestCase):
    def test_all_qualified_returns_empty(self):
        ps = [_make_participant("P1"), _make_participant("P2")]
        self.assertEqual(check_participant_qualifications(ps), [])

    def test_unqualified_participant_detected(self):
        ps = [
            _make_participant("P1", qualified=True),
            _make_participant("P2", qualified=False),
        ]
        self.assertIn("P2", check_participant_qualifications(ps))

    def test_all_unqualified_returns_all_ids(self):
        ps = [_make_participant(f"P{i}", qualified=False) for i in range(3)]
        result = check_participant_qualifications(ps)
        self.assertEqual(len(result), 3)


class TestScenarioCoverage(unittest.TestCase):
    def test_all_covered_returns_empty(self):
        scenarios = [_make_scenario("S1"), _make_scenario("S2")]
        results = [_make_result("S1"), _make_result("S2")]
        self.assertEqual(check_scenario_coverage(scenarios, results), [])

    def test_missing_result_detected(self):
        scenarios = [_make_scenario("S1"), _make_scenario("S2")]
        results = [_make_result("S1")]
        self.assertIn("S2", check_scenario_coverage(scenarios, results))

    def test_no_results_all_uncovered(self):
        scenarios = [_make_scenario("S1"), _make_scenario("S2")]
        self.assertEqual(
            set(check_scenario_coverage(scenarios, [])), {"S1", "S2"}
        )


class TestQualifiedCountInResult(unittest.TestCase):
    def test_counts_only_qualified_ids(self):
        result = _make_result(pids=["P1", "P2", "P3"])
        qualified_ids = frozenset(["P1", "P3"])
        self.assertEqual(count_qualified_in_result(result, qualified_ids), 2)

    def test_no_overlap_returns_zero(self):
        result = _make_result(pids=["P1", "P2"])
        self.assertEqual(count_qualified_in_result(result, frozenset(["P9"])), 0)


class TestEvaluateScenarioResult(unittest.TestCase):
    def test_passing_result_no_findings(self):
        scenario = _make_scenario(req=2, min_tc=0.90, max_er=0.10, max_wl=7.0)
        result = _make_result(pids=["P1", "P2"], tc=0.95, er=0.05, wl=[5.0, 6.0])
        qualified_ids = frozenset(["P1", "P2"])
        out = evaluate_scenario_result(scenario, result, qualified_ids)
        self.assertTrue(out["passed"])
        self.assertEqual(out["findings"], [])

    def test_low_task_completion_fails(self):
        scenario = _make_scenario(min_tc=0.90)
        result = _make_result(tc=0.80)
        out = evaluate_scenario_result(scenario, result, frozenset(["P1", "P2"]))
        self.assertFalse(out["passed"])
        self.assertTrue(any("completion" in f.lower() for f in out["findings"]))

    def test_high_error_rate_fails(self):
        scenario = _make_scenario(max_er=0.10)
        result = _make_result(er=0.20)
        out = evaluate_scenario_result(scenario, result, frozenset(["P1", "P2"]))
        self.assertFalse(out["passed"])
        self.assertTrue(any("error rate" in f.lower() for f in out["findings"]))

    def test_high_workload_fails(self):
        scenario = _make_scenario(max_wl=7.0)
        result = _make_result(wl=[8.0, 9.0])
        out = evaluate_scenario_result(scenario, result, frozenset(["P1", "P2"]))
        self.assertFalse(out["passed"])
        self.assertTrue(any("workload" in f.lower() for f in out["findings"]))

    def test_insufficient_qualified_participants_fails(self):
        scenario = _make_scenario(req=3)
        result = _make_result(pids=["P1", "P2"])
        qualified_ids = frozenset(["P1", "P2"])
        out = evaluate_scenario_result(scenario, result, qualified_ids)
        self.assertFalse(out["passed"])
        self.assertTrue(any("qualified" in f.lower() for f in out["findings"]))

    def test_multiple_failures_produce_multiple_findings(self):
        scenario = _make_scenario(min_tc=0.90, max_er=0.10, max_wl=7.0, req=2)
        result = _make_result(tc=0.70, er=0.30, wl=[9.0, 9.0])
        out = evaluate_scenario_result(scenario, result, frozenset(["P1", "P2"]))
        self.assertFalse(out["passed"])
        self.assertGreaterEqual(len(out["findings"]), 3)

    def test_mean_workload_calculated_correctly(self):
        scenario = _make_scenario(max_wl=10.0)
        result = _make_result(wl=[4.0, 6.0])
        out = evaluate_scenario_result(scenario, result, frozenset(["P1", "P2"]))
        self.assertAlmostEqual(out["mean_workload"], 5.0)


class TestRunSimulationVerification(unittest.TestCase):
    def _passing_inputs(self):
        scenarios = [_make_scenario("S1"), _make_scenario("S2")]
        participants = [
            _make_participant("P1", "commander", True),
            _make_participant("P2", "pilot", True),
        ]
        results = [
            _make_result("S1", ["P1", "P2"], 0.95, 0.05, [5.0, 6.0]),
            _make_result("S2", ["P1", "P2"], 0.92, 0.08, [4.0, 5.0]),
        ]
        return scenarios, participants, results

    def test_fully_passing_simulation(self):
        s, p, r = self._passing_inputs()
        report = run_simulation_verification(s, p, r)
        self.assertTrue(report["overall_passed"])
        self.assertEqual(report["unqualified_participants"], [])
        self.assertEqual(report["uncovered_scenarios"], [])
        self.assertTrue(all(sr["passed"] for sr in report["scenario_reports"]))

    def test_unqualified_participant_causes_overall_failure(self):
        s, p, r = self._passing_inputs()
        p.append(_make_participant("P3", "mission-specialist", False))
        report = run_simulation_verification(s, p, r)
        self.assertFalse(report["overall_passed"])
        self.assertIn("P3", report["unqualified_participants"])

    def test_uncovered_scenario_causes_overall_failure(self):
        s, p, r = self._passing_inputs()
        s.append(_make_scenario("S3"))
        report = run_simulation_verification(s, p, r)
        self.assertFalse(report["overall_passed"])
        self.assertIn("S3", report["uncovered_scenarios"])

    def test_scenario_metric_failure_causes_overall_failure(self):
        scenarios = [_make_scenario("S1", min_tc=0.95)]
        participants = [
            _make_participant("P1", "commander", True),
            _make_participant("P2", "pilot", True),
        ]
        results = [_make_result("S1", ["P1", "P2"], tc=0.80, er=0.05, wl=[5.0, 5.0])]
        report = run_simulation_verification(scenarios, participants, results)
        self.assertFalse(report["overall_passed"])

    def test_empty_scenarios_raises(self):
        with self.assertRaises(SimulationError):
            run_simulation_verification([], [_make_participant()], [_make_result()])

    def test_empty_participants_raises(self):
        with self.assertRaises(SimulationError):
            run_simulation_verification([_make_scenario()], [], [_make_result()])

    def test_empty_results_raises(self):
        with self.assertRaises(SimulationError):
            run_simulation_verification(
                [_make_scenario()], [_make_participant()], []
            )

    def test_duplicate_scenario_ids_raises(self):
        scenarios = [_make_scenario("S1"), _make_scenario("S1")]
        participants = [_make_participant("P1")]
        results = [_make_result("S1")]
        with self.assertRaises(SimulationError):
            run_simulation_verification(scenarios, participants, results)

    def test_scenario_report_count_matches_covered_scenarios(self):
        s, p, r = self._passing_inputs()
        report = run_simulation_verification(s, p, r)
        self.assertEqual(len(report["scenario_reports"]), 2)

    def test_boundary_task_completion_exactly_at_threshold_passes(self):
        scenario = _make_scenario("S1", min_tc=0.90, req=2)
        participants = [
            _make_participant("P1", "commander", True),
            _make_participant("P2", "pilot", True),
        ]
        result = _make_result("S1", ["P1", "P2"], tc=0.90, er=0.05, wl=[5.0, 5.0])
        report = run_simulation_verification([scenario], participants, [result])
        self.assertTrue(report["overall_passed"])

    def test_boundary_error_rate_exactly_at_threshold_passes(self):
        scenario = _make_scenario("S1", max_er=0.10, req=2)
        participants = [
            _make_participant("P1", "commander", True),
            _make_participant("P2", "pilot", True),
        ]
        result = _make_result("S1", ["P1", "P2"], tc=0.95, er=0.10, wl=[5.0, 5.0])
        report = run_simulation_verification([scenario], participants, [result])
        self.assertTrue(report["overall_passed"])


if __name__ == "__main__":
    unittest.main()
