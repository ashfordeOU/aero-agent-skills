import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1011_crew_provisions_logic import (
    SeatSpec,
    ConsoleSpec,
    StationProvision,
    CrewProvisionError,
    check_seat_geometry,
    check_restraint_loads,
    check_console_envelope,
    check_egress_clearance,
    assess_station,
    assess_all_stations,
    categorize_stations_by_type,
    SEAT_WIDTH_MIN_MM,
    SEAT_DEPTH_MIN_MM,
    RESTRAINT_SHOULDER_MIN_N,
    RESTRAINT_LAP_MIN_N,
    RESTRAINT_FOOTREST_MIN_N,
    REACH_ENVELOPE_MM,
    CONSOLE_HEIGHT_MAX_MM,
    CONSOLE_HEIGHT_MIN_MM,
    EGRESS_MIN_CLEARANCE_MM,
)


def _seat(seat_id="S1", width=500, depth=420,
          shoulder=9000, lap=13000, footrest=5000):
    return SeatSpec(seat_id, width, depth, shoulder, lap, footrest)


def _console(console_id="C1", station_type="piloting",
             h_min=700, h_max=1200, reach=600):
    return ConsoleSpec(console_id, station_type, h_min, h_max, reach)


def _station(station_id="ST1", station_type="piloting",
             seat=None, console=None, egress=700):
    return StationProvision(
        station_id,
        station_type,
        seat if seat is not None else _seat(),
        console if console is not None else _console(),
        egress,
    )


class TestSeatGeometry(unittest.TestCase):

    def test_compliant_seat_returns_no_findings(self):
        seat = _seat(width=SEAT_WIDTH_MIN_MM, depth=SEAT_DEPTH_MIN_MM)
        self.assertEqual(check_seat_geometry(seat), [])

    def test_width_below_minimum_produces_one_finding(self):
        seat = _seat(width=SEAT_WIDTH_MIN_MM - 1)
        findings = check_seat_geometry(seat)
        self.assertEqual(len(findings), 1)
        self.assertIn("width", findings[0])

    def test_depth_below_minimum_produces_one_finding(self):
        seat = _seat(depth=SEAT_DEPTH_MIN_MM - 1)
        findings = check_seat_geometry(seat)
        self.assertEqual(len(findings), 1)
        self.assertIn("depth", findings[0])

    def test_both_dimensions_below_minimum_produces_two_findings(self):
        seat = _seat(width=300, depth=300)
        self.assertEqual(len(check_seat_geometry(seat)), 2)

    def test_width_exactly_at_minimum_passes(self):
        seat = _seat(width=SEAT_WIDTH_MIN_MM, depth=SEAT_DEPTH_MIN_MM + 50)
        self.assertEqual(check_seat_geometry(seat), [])


class TestRestraintLoads(unittest.TestCase):

    def test_compliant_restraints_return_no_findings(self):
        seat = _seat(
            shoulder=RESTRAINT_SHOULDER_MIN_N,
            lap=RESTRAINT_LAP_MIN_N,
            footrest=RESTRAINT_FOOTREST_MIN_N,
        )
        self.assertEqual(check_restraint_loads(seat), [])

    def test_shoulder_below_minimum_flagged(self):
        seat = _seat(shoulder=RESTRAINT_SHOULDER_MIN_N - 1)
        findings = check_restraint_loads(seat)
        self.assertEqual(len(findings), 1)
        self.assertIn("shoulder", findings[0])

    def test_lap_belt_below_minimum_flagged(self):
        seat = _seat(lap=RESTRAINT_LAP_MIN_N - 1)
        findings = check_restraint_loads(seat)
        self.assertEqual(len(findings), 1)
        self.assertIn("lap", findings[0])

    def test_footrest_below_minimum_flagged(self):
        seat = _seat(footrest=RESTRAINT_FOOTREST_MIN_N - 1)
        findings = check_restraint_loads(seat)
        self.assertEqual(len(findings), 1)
        self.assertIn("footrest", findings[0])

    def test_all_restraints_below_minimum_produce_three_findings(self):
        seat = _seat(shoulder=1, lap=1, footrest=1)
        self.assertEqual(len(check_restraint_loads(seat)), 3)


class TestConsoleEnvelope(unittest.TestCase):

    def test_compliant_console_returns_no_findings(self):
        console = _console(
            h_min=CONSOLE_HEIGHT_MIN_MM,
            h_max=CONSOLE_HEIGHT_MAX_MM,
            reach=REACH_ENVELOPE_MM,
        )
        self.assertEqual(check_console_envelope(console), [])

    def test_lower_edge_below_minimum_flagged(self):
        console = _console(h_min=CONSOLE_HEIGHT_MIN_MM - 1)
        findings = check_console_envelope(console)
        self.assertEqual(len(findings), 1)
        self.assertIn("lower edge", findings[0])

    def test_upper_edge_above_maximum_flagged(self):
        console = _console(h_max=CONSOLE_HEIGHT_MAX_MM + 1)
        findings = check_console_envelope(console)
        self.assertEqual(len(findings), 1)
        self.assertIn("upper edge", findings[0])

    def test_reach_exceeds_envelope_flagged(self):
        console = _console(reach=REACH_ENVELOPE_MM + 1)
        findings = check_console_envelope(console)
        self.assertEqual(len(findings), 1)
        self.assertIn("reach", findings[0])

    def test_unknown_station_type_raises(self):
        console = _console(station_type="unknown_type")
        with self.assertRaises(CrewProvisionError):
            check_console_envelope(console)


class TestEgressClearance(unittest.TestCase):

    def test_sufficient_clearance_returns_no_findings(self):
        st = _station(egress=EGRESS_MIN_CLEARANCE_MM)
        self.assertEqual(check_egress_clearance(st), [])

    def test_insufficient_clearance_produces_one_finding(self):
        st = _station(egress=EGRESS_MIN_CLEARANCE_MM - 1)
        findings = check_egress_clearance(st)
        self.assertEqual(len(findings), 1)
        self.assertIn("egress", findings[0])

    def test_clearance_well_below_minimum_still_one_finding(self):
        st = _station(egress=100)
        self.assertEqual(len(check_egress_clearance(st)), 1)


class TestAssessStation(unittest.TestCase):

    def test_fully_conformant_station_reports_compliant(self):
        result = assess_station(_station())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_bad_seat_propagates_to_overall_result(self):
        seat = _seat(width=200, depth=200)
        result = assess_station(_station(seat=seat))
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_station_type_console_mismatch_raises(self):
        console = _console(station_type="maintenance")
        with self.assertRaises(CrewProvisionError):
            assess_station(_station(station_type="piloting", console=console))

    def test_unrecognized_station_type_raises(self):
        with self.assertRaises(CrewProvisionError):
            assess_station(_station(station_type="orbital_habitat"))

    def test_result_keys_present(self):
        result = assess_station(_station())
        for key in ("station_id", "seat_geometry_findings", "restraint_findings",
                    "console_findings", "egress_findings", "compliant", "findings"):
            self.assertIn(key, result)


class TestAssessAllStations(unittest.TestCase):

    def test_two_conformant_stations_all_compliant(self):
        stations = [_station("A"), _station("B")]
        report = assess_all_stations(stations)
        self.assertTrue(report["all_compliant"])
        self.assertEqual(report["station_count"], 2)
        self.assertEqual(report["non_compliant_count"], 0)
        self.assertEqual(report["compliant_count"], 2)

    def test_empty_station_list_raises(self):
        with self.assertRaises(CrewProvisionError):
            assess_all_stations([])

    def test_one_bad_station_counted_correctly(self):
        good = _station("GOOD")
        bad_seat = _seat(seat_id="BS", width=100, depth=100,
                         shoulder=1, lap=1, footrest=1)
        bad = _station("BAD", seat=bad_seat)
        report = assess_all_stations([good, bad])
        self.assertFalse(report["all_compliant"])
        self.assertEqual(report["non_compliant_count"], 1)
        self.assertEqual(report["compliant_count"], 1)


class TestCategorizeByType(unittest.TestCase):

    def test_stations_grouped_into_correct_type_buckets(self):
        st_pilot = _station("P1", station_type="piloting")
        st_mission = _station("M1", station_type="mission",
                              console=_console(station_type="mission"))
        grouped = categorize_stations_by_type([st_pilot, st_mission])
        self.assertIn("P1", grouped["piloting"])
        self.assertIn("M1", grouped["mission"])
        self.assertEqual(grouped["payload"], [])
        self.assertEqual(grouped["maintenance"], [])

    def test_unrecognized_type_raises(self):
        st = _station("X")
        st.station_type = "orbital_lab"
        with self.assertRaises(CrewProvisionError):
            categorize_stations_by_type([st])

    def test_all_four_types_appear_as_keys(self):
        grouped = categorize_stations_by_type([_station("ST1")])
        for t in ("piloting", "mission", "payload", "maintenance"):
            self.assertIn(t, grouped)


if __name__ == "__main__":
    unittest.main()
