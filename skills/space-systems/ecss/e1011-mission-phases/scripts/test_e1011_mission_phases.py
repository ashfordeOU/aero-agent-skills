#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.3.6 mission-phase mapping and
human-in-the-loop activity identification for HFE requirements capture.

Exercises scripts/e1011_mission_phases_logic.py (stdlib unittest, offline).
Contract: every canonical phase code is accepted; unknown phase codes raise;
unknown activity types raise; unknown criticality levels raise; a
human-in-the-loop activity is categorized correctly and generates one HFE
requirement with the correct structured ID and HFE driver; an automated
activity generates no requirement; a critical automated activity in a
mandatory-human phase is flagged as a finding; a phase with no
human-in-the-loop activities is flagged; phases absent from the inventory
appear in completeness findings; the full map covers all canonical phases
and aggregates findings correctly; HFE coverage counts are correct.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_mission_phases_logic as mp


def _act(
    activity_id="ACT-001",
    activity_type="monitoring",
    is_human_in_loop=True,
    criticality="routine",
):
    return {
        "activity_id": activity_id,
        "activity_type": activity_type,
        "is_human_in_loop": is_human_in_loop,
        "criticality": criticality,
    }


class ValidatePhaseCodeTest(unittest.TestCase):
    def test_all_canonical_phases_accepted(self):
        for phase in mp.CANONICAL_PHASES:
            mp.validate_phase_code(phase)  # must not raise

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            mp.validate_phase_code("REENTRY")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            mp.validate_phase_code("")


class ValidateActivityTypeTest(unittest.TestCase):
    def test_all_known_types_accepted(self):
        for act_type in mp.VALID_ACTIVITY_TYPES:
            mp.validate_activity_type(act_type)  # must not raise

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            mp.validate_activity_type("hacking")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            mp.validate_activity_type("")


class ValidateCriticalityTest(unittest.TestCase):
    def test_all_known_levels_accepted(self):
        for level in mp.VALID_CRITICALITY_LEVELS:
            mp.validate_criticality(level)  # must not raise

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            mp.validate_criticality("extreme")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            mp.validate_criticality("")


class CategorizeActivityTest(unittest.TestCase):
    def test_human_activity_returns_human_in_loop(self):
        self.assertEqual(mp.categorize_activity("monitoring", True), "human_in_loop")

    def test_automated_activity_returns_automated(self):
        self.assertEqual(mp.categorize_activity("commanding", False), "automated")

    def test_unknown_activity_type_raises(self):
        with self.assertRaises(ValueError):
            mp.categorize_activity("surfing", True)

    def test_human_flag_drives_result_not_activity_type(self):
        self.assertEqual(mp.categorize_activity("emergency_response", False), "automated")
        self.assertEqual(mp.categorize_activity("configuration", True), "human_in_loop")


class DetermineHFEDriverTest(unittest.TestCase):
    def test_emergency_response_maps_to_safety(self):
        self.assertEqual(mp.determine_hfe_driver("emergency_response"), "safety")

    def test_monitoring_maps_to_cognitive(self):
        self.assertEqual(mp.determine_hfe_driver("monitoring"), "cognitive")

    def test_commanding_maps_to_workload(self):
        self.assertEqual(mp.determine_hfe_driver("commanding"), "workload")

    def test_procedure_execution_maps_to_workload(self):
        self.assertEqual(mp.determine_hfe_driver("procedure_execution"), "workload")

    def test_decision_making_maps_to_cognitive(self):
        self.assertEqual(mp.determine_hfe_driver("decision_making"), "cognitive")

    def test_communication_maps_to_communication(self):
        self.assertEqual(mp.determine_hfe_driver("communication"), "communication")

    def test_maintenance_maps_to_anthropometry(self):
        self.assertEqual(mp.determine_hfe_driver("maintenance"), "anthropometry")

    def test_configuration_maps_to_workload(self):
        self.assertEqual(mp.determine_hfe_driver("configuration"), "workload")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            mp.determine_hfe_driver("guessing")


class GenerateHFEReqIdTest(unittest.TestCase):
    def test_id_format_is_correct(self):
        self.assertEqual(mp.generate_hfe_req_id("NOM", "A001"), "HFE-NOM-A001")

    def test_id_is_deterministic(self):
        id1 = mp.generate_hfe_req_id("LCH", "A002")
        id2 = mp.generate_hfe_req_id("LCH", "A002")
        self.assertEqual(id1, id2)

    def test_different_phases_produce_different_ids(self):
        id_nom = mp.generate_hfe_req_id("NOM", "A001")
        id_lch = mp.generate_hfe_req_id("LCH", "A001")
        self.assertNotEqual(id_nom, id_lch)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            mp.generate_hfe_req_id("GHOST_PHASE", "A001")


class AnalysePhaseTest(unittest.TestCase):
    def test_human_activity_generates_one_requirement(self):
        acts = [_act(activity_id="A001", is_human_in_loop=True)]
        result = mp.analyse_phase("NOM", acts)
        self.assertEqual(len(result["hfe_requirements"]), 1)
        self.assertEqual(result["hfe_requirements"][0]["req_id"], "HFE-NOM-A001")

    def test_automated_activity_generates_no_requirement(self):
        acts = [_act(activity_id="A002", is_human_in_loop=False)]
        result = mp.analyse_phase("NOM", acts)
        self.assertEqual(len(result["hfe_requirements"]), 0)

    def test_phase_with_no_human_activities_flagged(self):
        acts = [_act(is_human_in_loop=False)]
        result = mp.analyse_phase("NOM", acts)
        self.assertTrue(any("no human-in-the-loop" in f for f in result["findings"]))

    def test_phase_with_human_activities_not_flagged_for_absence(self):
        acts = [_act(is_human_in_loop=True)]
        result = mp.analyse_phase("NOM", acts)
        self.assertFalse(any("no human-in-the-loop" in f for f in result["findings"]))

    def test_critical_automated_in_mandatory_phase_flagged(self):
        acts = [_act(activity_id="E001", activity_type="emergency_response",
                     is_human_in_loop=False, criticality="critical")]
        result = mp.analyse_phase("CTG", acts)
        self.assertTrue(any("critical activity" in f for f in result["findings"]))

    def test_critical_automated_in_non_mandatory_phase_not_flagged(self):
        acts = [_act(activity_id="D001", is_human_in_loop=False, criticality="critical")]
        result = mp.analyse_phase("DPS", acts)
        self.assertFalse(any("critical activity" in f for f in result["findings"]))

    def test_hfe_driver_set_correctly_on_requirement(self):
        acts = [_act(activity_id="C001", activity_type="communication",
                     is_human_in_loop=True)]
        result = mp.analyse_phase("NOM", acts)
        self.assertEqual(result["hfe_requirements"][0]["driver"], "communication")

    def test_phase_code_propagated_to_requirements(self):
        acts = [_act(activity_id="X001", is_human_in_loop=True)]
        result = mp.analyse_phase("CHK", acts)
        self.assertEqual(result["hfe_requirements"][0]["phase"], "CHK")

    def test_unknown_phase_code_raises(self):
        with self.assertRaises(ValueError):
            mp.analyse_phase("BADPHASE", [])

    def test_unknown_activity_type_in_phase_raises(self):
        acts = [_act(activity_type="surfing")]
        with self.assertRaises(ValueError):
            mp.analyse_phase("NOM", acts)

    def test_unknown_criticality_in_phase_raises(self):
        acts = [_act(criticality="catastrophic")]
        with self.assertRaises(ValueError):
            mp.analyse_phase("NOM", acts)

    def test_multiple_human_activities_generate_multiple_requirements(self):
        acts = [
            _act(activity_id="H1", is_human_in_loop=True),
            _act(activity_id="H2", is_human_in_loop=True),
            _act(activity_id="A1", is_human_in_loop=False),
        ]
        result = mp.analyse_phase("NOM", acts)
        self.assertEqual(len(result["hfe_requirements"]), 2)
        ids = {r["req_id"] for r in result["hfe_requirements"]}
        self.assertEqual(ids, {"HFE-NOM-H1", "HFE-NOM-H2"})

    def test_empty_activity_list_flagged(self):
        result = mp.analyse_phase("GRD", [])
        self.assertTrue(any("no human-in-the-loop" in f for f in result["findings"]))


class CheckPhaseCompletenessTest(unittest.TestCase):
    def test_all_phases_present_returns_empty(self):
        full_map = {phase: [] for phase in mp.CANONICAL_PHASES}
        findings = mp.check_phase_completeness(full_map)
        self.assertEqual(findings, [])

    def test_missing_phase_generates_finding(self):
        partial_map = {p: [] for p in mp.CANONICAL_PHASES if p != "CTG"}
        findings = mp.check_phase_completeness(partial_map)
        self.assertEqual(len(findings), 1)
        self.assertIn("CTG", findings[0])

    def test_empty_map_generates_finding_for_every_phase(self):
        findings = mp.check_phase_completeness({})
        self.assertEqual(len(findings), len(mp.CANONICAL_PHASES))


class MapMissionPhasesTest(unittest.TestCase):
    def test_all_canonical_phases_present_in_output(self):
        result = mp.map_mission_phases({"NOM": [_act()]})
        for phase in mp.CANONICAL_PHASES:
            self.assertIn(phase, result["phase_results"])

    def test_absent_phase_gets_absence_finding(self):
        result = mp.map_mission_phases({"NOM": [_act()]})
        for phase in mp.CANONICAL_PHASES:
            if phase != "NOM":
                findings = result["phase_results"][phase]["findings"]
                self.assertTrue(
                    any("absent" in f or "no activities" in f for f in findings),
                    "Phase {} missing absence finding".format(phase),
                )

    def test_unknown_phase_in_map_raises(self):
        with self.assertRaises(ValueError):
            mp.map_mission_phases({"INVALID_PHASE": []})

    def test_hfe_requirements_populated_for_human_activities(self):
        result = mp.map_mission_phases({
            "NOM": [_act(activity_id="H1", is_human_in_loop=True)],
        })
        self.assertEqual(len(result["phase_results"]["NOM"]["hfe_requirements"]), 1)

    def test_completeness_findings_populated_for_absent_phases(self):
        result = mp.map_mission_phases({"NOM": [_act()]})
        self.assertEqual(
            len(result["completeness_findings"]),
            len(mp.CANONICAL_PHASES) - 1,
        )

    def test_all_findings_aggregates_across_phases(self):
        result = mp.map_mission_phases({"NOM": [_act(is_human_in_loop=True)]})
        self.assertGreater(len(result["all_findings"]), 0)

    def test_fully_covered_map_has_no_completeness_findings(self):
        full_map = {phase: [_act(is_human_in_loop=True)] for phase in mp.CANONICAL_PHASES}
        result = mp.map_mission_phases(full_map)
        self.assertEqual(result["completeness_findings"], [])


class SummariseHFECoverageTest(unittest.TestCase):
    def test_coverage_counts_per_phase(self):
        result = mp.map_mission_phases({
            "NOM": [
                _act(activity_id="H1", is_human_in_loop=True),
                _act(activity_id="H2", is_human_in_loop=True),
                _act(activity_id="A1", is_human_in_loop=False),
            ],
            "LCH": [_act(activity_id="H3", is_human_in_loop=True)],
        })
        coverage = mp.summarise_hfe_coverage(result)
        self.assertEqual(coverage["NOM"], 2)
        self.assertEqual(coverage["LCH"], 1)
        self.assertEqual(coverage["ASC"], 0)

    def test_coverage_zero_for_all_automated_phase(self):
        result = mp.map_mission_phases({
            "GRD": [_act(is_human_in_loop=False)],
        })
        coverage = mp.summarise_hfe_coverage(result)
        self.assertEqual(coverage["GRD"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
