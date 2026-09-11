import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1011_maint_stations_logic import (
    AccessZone,
    MaintenanceStation,
    MaintenanceTask,
    MaintenanceZoneType,
    StationAssessmentResult,
    TaskFrequency,
    Tool,
    assess_multiple_stations,
    assess_station,
    categorize_tasks,
    check_access_zone,
    check_lighting,
    check_tooling,
    EVA_MIN_LATERAL_CLEARANCE_MM,
    EVA_MIN_REACH_DEPTH_MM,
    EVA_MIN_VERTICAL_CLEARANCE_MM,
    IVA_MIN_LATERAL_CLEARANCE_MM,
    IVA_MIN_REACH_DEPTH_MM,
    IVA_MIN_VERTICAL_CLEARANCE_MM,
    MAX_SINGLE_HAND_TOOL_ENVELOPE_MM,
    MIN_LIGHTING_EVA_LUX,
    MIN_LIGHTING_IVA_LUX,
)


def _make_iva_station(station_id="S1", reach=500.0, lat=500.0, vert=550.0,
                      lighting=200.0):
    return MaintenanceStation(
        station_id=station_id,
        name="Test IVA Station",
        access_zone=AccessZone(
            reach_depth_mm=reach,
            lateral_clearance_mm=lat,
            vertical_clearance_mm=vert,
            zone_type=MaintenanceZoneType.IVA,
        ),
        lighting_lux=lighting,
    )


def _make_eva_station(station_id="S2", reach=700.0, lat=750.0, vert=800.0,
                      lighting=120.0):
    return MaintenanceStation(
        station_id=station_id,
        name="Test EVA Station",
        access_zone=AccessZone(
            reach_depth_mm=reach,
            lateral_clearance_mm=lat,
            vertical_clearance_mm=vert,
            zone_type=MaintenanceZoneType.EVA,
        ),
        lighting_lux=lighting,
    )


def _make_hybrid_station(station_id="S3"):
    return MaintenanceStation(
        station_id=station_id,
        name="Hybrid Station",
        access_zone=AccessZone(
            reach_depth_mm=700.0,
            lateral_clearance_mm=750.0,
            vertical_clearance_mm=800.0,
            zone_type=MaintenanceZoneType.HYBRID,
        ),
        lighting_lux=160.0,
    )


class TestAccessZoneIVA(unittest.TestCase):

    def test_iva_all_axes_compliant(self):
        station = _make_iva_station()
        findings = check_access_zone(station)
        self.assertEqual(len(findings), 3)
        self.assertTrue(all(f.compliant for f in findings))

    def test_iva_reach_below_minimum(self):
        station = _make_iva_station(reach=IVA_MIN_REACH_DEPTH_MM - 1)
        findings = check_access_zone(station)
        reach_f = next(f for f in findings if f.axis == "reach")
        self.assertFalse(reach_f.compliant)

    def test_iva_lateral_below_minimum(self):
        station = _make_iva_station(lat=IVA_MIN_LATERAL_CLEARANCE_MM - 1)
        findings = check_access_zone(station)
        lat_f = next(f for f in findings if f.axis == "lateral")
        self.assertFalse(lat_f.compliant)

    def test_iva_vertical_below_minimum(self):
        station = _make_iva_station(vert=IVA_MIN_VERTICAL_CLEARANCE_MM - 1)
        findings = check_access_zone(station)
        vert_f = next(f for f in findings if f.axis == "vertical")
        self.assertFalse(vert_f.compliant)

    def test_iva_exact_minimum_is_compliant(self):
        station = _make_iva_station(
            reach=IVA_MIN_REACH_DEPTH_MM,
            lat=IVA_MIN_LATERAL_CLEARANCE_MM,
            vert=IVA_MIN_VERTICAL_CLEARANCE_MM,
        )
        findings = check_access_zone(station)
        self.assertTrue(all(f.compliant for f in findings))


class TestAccessZoneEVA(unittest.TestCase):

    def test_eva_all_axes_compliant(self):
        station = _make_eva_station()
        findings = check_access_zone(station)
        self.assertTrue(all(f.compliant for f in findings))

    def test_eva_reach_below_minimum(self):
        station = _make_eva_station(reach=EVA_MIN_REACH_DEPTH_MM - 1)
        findings = check_access_zone(station)
        reach_f = next(f for f in findings if f.axis == "reach")
        self.assertFalse(reach_f.compliant)

    def test_hybrid_uses_eva_thresholds(self):
        station = _make_hybrid_station()
        findings = check_access_zone(station)
        reach_f = next(f for f in findings if f.axis == "reach")
        self.assertEqual(reach_f.required_mm, EVA_MIN_REACH_DEPTH_MM)


class TestToolingChecks(unittest.TestCase):

    def test_iva_compatible_tool_no_finding(self):
        station = _make_iva_station()
        station.tools_on_record = [
            Tool("T1", "Socket Driver", 200.0, False, True, False)
        ]
        findings = check_tooling(station)
        self.assertEqual(findings, [])

    def test_eva_incompatible_tool_in_iva_flagged(self):
        station = _make_iva_station()
        station.tools_on_record = [
            Tool("T2", "EVA-Only Wrench", 250.0, False, False, True)
        ]
        findings = check_tooling(station)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].tool_id, "T2")

    def test_large_envelope_single_hand_flagged(self):
        station = _make_iva_station()
        big_envelope = MAX_SINGLE_HAND_TOOL_ENVELOPE_MM + 50
        station.tools_on_record = [
            Tool("T3", "Large Torque Bar", big_envelope, False, True, False)
        ]
        findings = check_tooling(station)
        self.assertTrue(any(f.tool_id == "T3" for f in findings))

    def test_large_envelope_two_hand_not_flagged_for_arc(self):
        station = _make_iva_station()
        big_envelope = MAX_SINGLE_HAND_TOOL_ENVELOPE_MM + 50
        station.tools_on_record = [
            Tool("T4", "Large Two-Hand Wrench", big_envelope, True, True, False)
        ]
        # Only IVA-compatible check; envelope check should not fire
        findings = check_tooling(station)
        self.assertEqual(findings, [])

    def test_hybrid_tool_missing_iva_compat_flagged(self):
        station = _make_hybrid_station()
        station.tools_on_record = [
            Tool("T5", "EVA Ratchet", 200.0, False, False, True)
        ]
        findings = check_tooling(station)
        self.assertEqual(len(findings), 1)
        self.assertIn("HYBRID", findings[0].issue)


class TestLightingChecks(unittest.TestCase):

    def test_iva_lighting_compliant(self):
        station = _make_iva_station(lighting=200.0)
        findings = check_lighting(station)
        self.assertTrue(findings[0].compliant)

    def test_iva_lighting_below_minimum(self):
        station = _make_iva_station(lighting=MIN_LIGHTING_IVA_LUX - 1)
        findings = check_lighting(station)
        self.assertFalse(findings[0].compliant)

    def test_eva_lighting_compliant(self):
        station = _make_eva_station(lighting=MIN_LIGHTING_EVA_LUX)
        findings = check_lighting(station)
        self.assertTrue(findings[0].compliant)

    def test_lighting_missing_is_non_compliant(self):
        station = _make_iva_station()
        station.lighting_lux = None
        findings = check_lighting(station)
        self.assertFalse(findings[0].compliant)
        self.assertIsNone(findings[0].actual_lux)


class TestTaskCategorization(unittest.TestCase):

    def test_task_with_all_tools_on_record(self):
        station = _make_iva_station()
        station.tools_on_record = [Tool("T1", "Driver", 100.0, False, True, False)]
        station.tasks = [
            MaintenanceTask("TK1", "Replace filter", TaskFrequency.ROUTINE,
                            ["T1"], MaintenanceZoneType.IVA, 30.0, True)
        ]
        cats = categorize_tasks(station)
        self.assertEqual(len(cats), 1)
        self.assertEqual(cats[0].unresolved_tools, [])

    def test_task_with_missing_tool_flagged(self):
        station = _make_iva_station()
        station.tasks = [
            MaintenanceTask("TK2", "Replace bearing", TaskFrequency.CORRECTIVE,
                            ["T99"], MaintenanceZoneType.IVA, 60.0, False)
        ]
        cats = categorize_tasks(station)
        self.assertIn("T99", cats[0].unresolved_tools)

    def test_task_frequency_preserved(self):
        station = _make_iva_station()
        station.tasks = [
            MaintenanceTask("TK3", "Inspect seals", TaskFrequency.ON_CONDITION,
                            [], MaintenanceZoneType.IVA, 15.0, True)
        ]
        cats = categorize_tasks(station)
        self.assertEqual(cats[0].frequency, "on_condition")

    def test_empty_task_list_returns_empty(self):
        station = _make_iva_station()
        cats = categorize_tasks(station)
        self.assertEqual(cats, [])


class TestAssessStation(unittest.TestCase):

    def test_fully_compliant_station(self):
        station = _make_iva_station()
        station.tools_on_record = [Tool("T1", "Driver", 100.0, False, True, False)]
        station.tasks = [
            MaintenanceTask("TK1", "Check valve", TaskFrequency.ROUTINE,
                            ["T1"], MaintenanceZoneType.IVA, 20.0, True)
        ]
        result = assess_station(station)
        self.assertTrue(result.compliant)

    def test_station_non_compliant_due_to_access(self):
        station = _make_iva_station(reach=100.0)
        result = assess_station(station)
        self.assertFalse(result.compliant)

    def test_station_non_compliant_due_to_tooling(self):
        station = _make_iva_station()
        station.tools_on_record = [
            Tool("T2", "Bad Tool", 100.0, False, False, True)
        ]
        result = assess_station(station)
        self.assertFalse(result.compliant)

    def test_station_non_compliant_due_to_lighting(self):
        station = _make_iva_station(lighting=50.0)
        result = assess_station(station)
        self.assertFalse(result.compliant)

    def test_station_non_compliant_due_to_unresolved_tool_in_task(self):
        station = _make_iva_station()
        station.tasks = [
            MaintenanceTask("TK4", "Repair pump", TaskFrequency.CORRECTIVE,
                            ["MISSING_TOOL"], MaintenanceZoneType.IVA, 45.0, False)
        ]
        result = assess_station(station)
        self.assertFalse(result.compliant)

    def test_result_as_dict_structure(self):
        station = _make_iva_station()
        result = assess_station(station)
        d = result.as_dict()
        self.assertIn("station_id", d)
        self.assertIn("access_findings", d)
        self.assertIn("tooling_findings", d)
        self.assertIn("lighting_findings", d)
        self.assertIn("task_categorizations", d)
        self.assertIn("compliant", d)


class TestAssessMultipleStations(unittest.TestCase):

    def test_multiple_stations_keyed_by_id(self):
        s1 = _make_iva_station("S1")
        s2 = _make_eva_station("S2")
        results = assess_multiple_stations([s1, s2])
        self.assertIn("S1", results)
        self.assertIn("S2", results)
        self.assertIsInstance(results["S1"], StationAssessmentResult)

    def test_empty_list_returns_empty_dict(self):
        results = assess_multiple_stations([])
        self.assertEqual(results, {})


if __name__ == "__main__":
    unittest.main()
