"""Contract test for the ground-station-pass-planning leaf.

Exercises the SKILL.md workflow end to end: step 1 fixes the orbit
state and the planning horizon through the module constants, step 2 the
ground-track propagation traverse computes the orbital period and the
sub-satellite point over the horizon, step 3 the elevation traverse
computes the elevation of the satellite above the station from the
central angle, step 4 the pass-detection traverse finds the contiguous
passes above the elevation mask, step 5 the downlink-gap-analysis
traverse aggregates the daily contact schedule with its downlink gaps
and the maximum downlink gap, step 6 the multi-station-contact-plan
traverse merges the ground station contacts into one plan, and step 7
guard traverses reject non-physical inputs. Pure stdlib unittest,
offline and deterministic, no RNG.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ground_station_pass_planning_logic as logic

# Worked-example orbit and stations from the SKILL.md body: circular
# 550 km LEO, inclination 53 deg, RAAN 0, initial argument of latitude
# 0, Greenwich angle 0, 24 h horizon, 30 s step. Berlin is 52.52 N,
# 13.405 E and Madrid 40.42 N, 3.70 W, both with a 10 deg mask.
ALT = 550.0
INC = 53.0
RAAN = 0.0
U0 = 0.0
G0 = 0.0
HORIZON_H = 24.0
BERLIN = {"lat_deg": 52.52, "lon_deg": 13.405}
MADRID = {"lat_deg": 40.42, "lon_deg": -3.70}
MASK = 10.0


class ModuleConstantsTest(unittest.TestCase):
    def test_step_1_module_constants(self):
        """Step 1 of the SKILL.md workflow fixes the orbit state and the
        planning horizon: the spherical Earth radius is 6371 km, mu is
        398600.4418 km^3/s^2, the Earth rotation rate is 7.2921159e-5
        rad/s, the fixed planner step is 30 s and the downlink gap
        threshold is 600 s."""
        self.assertEqual(logic.RE_KM, 6371.0)
        self.assertEqual(logic.MU, 398600.4418)
        self.assertEqual(logic.OMEGA_E, 7.2921159e-5)
        self.assertEqual(logic.STEP_S, 30.0)
        self.assertEqual(logic.GAP_THRESHOLD_S, 600.0)


class OrbitalPeriodTest(unittest.TestCase):
    def test_orbital_period_550_km_anchor(self):
        """Step 2 of the SKILL.md workflow, the ground-track propagation
        traverse: the orbital period of the 550 km worked example is
        5730.13 s (95.5 min) within 0.1 s."""
        self.assertAlmostEqual(logic.orbital_period_s(ALT), 5730.13,
                               delta=0.1)

    def test_orbital_period_kepler_closed_form(self):
        """Step 2 of the SKILL.md workflow: the orbital period equals
        the two-body closed form 2 pi sqrt(a^3 / mu) with a the orbit
        radius of 6921 km at 550 km altitude."""
        t = logic.orbital_period_s(ALT)
        a_km = logic.RE_KM + ALT
        expected = 2.0 * math.pi * math.sqrt(a_km ** 3 / logic.MU)
        self.assertAlmostEqual(t, expected, delta=1e-9)

    def test_orbital_period_grows_with_altitude(self):
        """Step 2 of the SKILL.md workflow: a higher circular orbit has
        a longer orbital period, so 600 km exceeds the 550 km value."""
        self.assertGreater(logic.orbital_period_s(600.0),
                           logic.orbital_period_s(ALT))

    def test_orbital_period_negative_altitude_raises(self):
        """Step 7 guard traverse: a negative altitude is non-physical
        and the orbital period raises ValueError."""
        with self.assertRaises(ValueError):
            logic.orbital_period_s(-1.0)


class SubsatellitePointTest(unittest.TestCase):
    def test_subsatellite_point_at_epoch(self):
        """Step 2 of the SKILL.md workflow, the sub-satellite point
        traverse: at t = 0 with zero initial argument of latitude, zero
        RAAN and zero Greenwich angle the sub-satellite point of the
        worked example sits on the equator at 0 deg longitude."""
        p = logic.subsatellite_point(ALT, INC, RAAN, U0, G0, 0.0)
        self.assertAlmostEqual(p["lat_deg"], 0.0, delta=1e-9)
        self.assertAlmostEqual(p["lon_deg"], 0.0, delta=1e-9)

    def test_subsatellite_point_latitude_after_quarter_orbit(self):
        """Step 2 of the SKILL.md workflow: after a quarter orbital
        period the argument of latitude reaches 90 deg, so the
        sub-satellite latitude equals the 53 deg inclination."""
        t = logic.orbital_period_s(ALT) / 4.0
        p = logic.subsatellite_point(ALT, INC, RAAN, U0, G0, t)
        self.assertAlmostEqual(p["lat_deg"], INC, delta=0.01)

    def test_subsatellite_point_longitude_drift_after_one_orbit(self):
        """Step 2 of the SKILL.md workflow: after one full orbital
        period the Earth has rotated under the fixed inertial track, so
        the sub-satellite longitude drifts west by OMEGA_E * T."""
        t = logic.orbital_period_s(ALT)
        p = logic.subsatellite_point(ALT, INC, RAAN, U0, G0, t)
        expected = -math.degrees(logic.OMEGA_E * t)
        self.assertAlmostEqual(p["lon_deg"], expected, delta=0.01)

    def test_subsatellite_point_longitude_wrapped(self):
        """Step 2 of the SKILL.md workflow: the sub-satellite longitude
        stays wrapped to [-180, 180] over a long propagation."""
        p = logic.subsatellite_point(ALT, INC, RAAN, U0, G0, 50000.0)
        self.assertGreaterEqual(p["lon_deg"], -180.0)
        self.assertLessEqual(p["lon_deg"], 180.0)

    def test_subsatellite_point_negative_altitude_raises(self):
        """Step 7 guard traverse: the ground-track propagation rejects
        a negative altitude with ValueError."""
        with self.assertRaises(ValueError):
            logic.subsatellite_point(-5.0, INC, RAAN, U0, G0, 0.0)

    def test_subsatellite_point_inclination_out_of_range_raises(self):
        """Step 7 guard traverse: inclinations outside [0, 180] deg are
        non-physical and raise ValueError in the sub-satellite point
        traverse."""
        with self.assertRaises(ValueError):
            logic.subsatellite_point(ALT, 181.0, RAAN, U0, G0, 0.0)
        with self.assertRaises(ValueError):
            logic.subsatellite_point(ALT, -1.0, RAAN, U0, G0, 0.0)

    def test_subsatellite_point_negative_time_raises(self):
        """Step 7 guard traverse: negative propagation time raises
        ValueError in the sub-satellite point traverse."""
        with self.assertRaises(ValueError):
            logic.subsatellite_point(ALT, INC, RAAN, U0, G0, -10.0)


class ElevationAngleTest(unittest.TestCase):
    def test_elevation_at_station_zenith_90_deg(self):
        """Step 3 of the SKILL.md workflow, the elevation traverse: a
        station equal to the sub-satellite point observes the satellite
        at the 90 deg zenith, so the worked example Berlin station at
        its own footprint reads 89.99999 deg within 1e-3."""
        el = logic.elevation_angle(BERLIN["lat_deg"], BERLIN["lon_deg"],
                                   BERLIN["lat_deg"], BERLIN["lon_deg"],
                                   ALT)
        self.assertAlmostEqual(el, 90.0, delta=1e-3)

    def test_elevation_zero_at_horizon_central_angle(self):
        """Step 3 of the SKILL.md workflow: the coverage inverse
        identity holds, a station at the 22.9961 deg horizon central
        angle of the 550 km orbit observes the satellite at 0 deg
        elevation within 1e-3."""
        el = logic.elevation_angle(22.9961, 0.0, 0.0, 0.0, ALT)
        self.assertAlmostEqual(el, 0.0, delta=1e-3)

    def test_elevation_coverage_inverse_identity_mask_10(self):
        """Step 3 of the SKILL.md workflow: the coverage inverse
        identity holds, a station at the 14.9676 deg central angle of
        the 10 deg mask observes the satellite at 10.000 deg elevation
        within 1e-3."""
        el = logic.elevation_angle(14.9676, 0.0, 0.0, 0.0, ALT)
        self.assertAlmostEqual(el, MASK, delta=1e-3)

    def test_elevation_negative_altitude_raises(self):
        """Step 7 guard traverse: the elevation traverse rejects a
        negative altitude with ValueError."""
        with self.assertRaises(ValueError):
            logic.elevation_angle(0.0, 0.0, 0.0, 0.0, -1.0)


class DetectPassesTest(unittest.TestCase):
    def test_detect_passes_berlin_five_passes_anchor(self):
        """Step 4 of the SKILL.md workflow, the pass-detection traverse:
        the Berlin worked example detects 5 passes above the 10 deg
        elevation mask over the 24 h horizon."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)
        self.assertEqual(len(passes_list), 5)
        expected_starts = [6540.0, 12450.0, 18390.0, 24360.0, 30360.0]
        expected_ends = [6900.0, 12900.0, 18870.0, 24840.0, 30720.0]
        for got, want in zip(passes_list, expected_starts):
            self.assertAlmostEqual(got["start_s"], want, delta=1.0)
        for got, want in zip(passes_list, expected_ends):
            self.assertAlmostEqual(got["end_s"], want, delta=1.0)

    def test_detect_passes_pass_one_details(self):
        """Step 4 of the SKILL.md workflow: pass 1 of the daily contact
        window schedule runs 6540 to 6900 s, lasts 390 s and peaks at
        23.350 deg elevation."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)
        p1 = passes_list[0]
        self.assertAlmostEqual(p1["start_s"], 6540.0, delta=1.0)
        self.assertAlmostEqual(p1["end_s"], 6900.0, delta=1.0)
        self.assertAlmostEqual(p1["duration_s"], 390.0, delta=1.0)
        self.assertAlmostEqual(p1["max_elevation_deg"], 23.350,
                               delta=0.01)

    def test_detect_passes_pass_three_peak_anchor(self):
        """Step 4 of the SKILL.md workflow: pass 3 is the highest
        contact of the day, 18390 to 18870 s, 510 s long with an 82.905
        deg maximum elevation."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)
        p3 = passes_list[2]
        self.assertAlmostEqual(p3["start_s"], 18390.0, delta=1.0)
        self.assertAlmostEqual(p3["end_s"], 18870.0, delta=1.0)
        self.assertAlmostEqual(p3["duration_s"], 510.0, delta=1.0)
        self.assertAlmostEqual(p3["max_elevation_deg"], 82.905,
                               delta=0.01)

    def test_detect_passes_duration_identity(self):
        """Step 4 of the SKILL.md workflow: every detected pass obeys
        the duration identity end minus start plus the 30 s planner
        step."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)
        for p in passes_list:
            self.assertAlmostEqual(p["duration_s"],
                                   p["end_s"] - p["start_s"]
                                   + logic.STEP_S, delta=1e-6)

    def test_detect_passes_mask_above_max_elevation_no_passes(self):
        """Step 4 of the SKILL.md workflow: a 90 deg elevation mask sits
        above the highest pass of the day, so the pass-detection
        traverse returns no passes."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], 90.0,
                                          HORIZON_H)
        self.assertEqual(passes_list, [])

    def test_detect_passes_negative_mask_raises(self):
        """Step 7 guard traverse: a negative elevation mask is
        non-physical and the pass-detection traverse raises
        ValueError."""
        with self.assertRaises(ValueError):
            logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                BERLIN["lat_deg"], BERLIN["lon_deg"],
                                -5.0, HORIZON_H)

    def test_detect_passes_nonpositive_horizon_raises(self):
        """Step 7 guard traverse: a non-positive planning horizon raises
        ValueError in the pass-detection traverse."""
        with self.assertRaises(ValueError):
            logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                BERLIN["lat_deg"], BERLIN["lon_deg"],
                                MASK, 0.0)


class DailyContactScheduleTest(unittest.TestCase):
    def setUp(self):
        self.passes = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)

    def test_daily_contact_schedule_berlin_anchor(self):
        """Step 5 of the SKILL.md workflow, the downlink-gap-analysis
        traverse: the Berlin daily contact schedule holds 5 passes and
        2280 s of total contact time."""
        sched = logic.daily_contact_schedule(self.passes)
        self.assertEqual(sched["n_passes"], 5)
        self.assertAlmostEqual(sched["total_contact_s"], 2280.0,
                               delta=1.0)

    def test_daily_contact_schedule_gap_durations(self):
        """Step 5 of the SKILL.md workflow: the downlink gap analysis
        lists the four inter-pass gaps of the Berlin day at 5520, 5460,
        5460 and 5490 s, all above the 600 s gap threshold."""
        sched = logic.daily_contact_schedule(self.passes)
        self.assertEqual(len(sched["gaps"]), 4)
        expected = [5520.0, 5460.0, 5460.0, 5490.0]
        for got, want in zip(sched["gaps"], expected):
            self.assertAlmostEqual(got["duration_s"], want, delta=1.0)
        self.assertAlmostEqual(sched["gaps"][0]["start_s"], 6930.0,
                               delta=1.0)
        self.assertAlmostEqual(sched["gaps"][0]["end_s"], 12450.0,
                               delta=1.0)

    def test_daily_contact_schedule_total_equals_pass_sum(self):
        """Step 5 of the SKILL.md workflow: the daily contact schedule
        total equals the sum of the detected pass durations."""
        sched = logic.daily_contact_schedule(self.passes)
        total = sum(p["duration_s"] for p in self.passes)
        self.assertAlmostEqual(sched["total_contact_s"], total,
                               delta=1e-6)

    def test_daily_contact_schedule_empty_pass_list(self):
        """Step 5 of the SKILL.md workflow: a satellite with no detected
        passes yields an empty daily contact schedule with no downlink
        gaps."""
        sched = logic.daily_contact_schedule([])
        self.assertEqual(sched["n_passes"], 0)
        self.assertEqual(sched["total_contact_s"], 0.0)
        self.assertEqual(sched["gaps"], [])


class MaxDownlinkGapTest(unittest.TestCase):
    def test_max_downlink_gap_berlin_anchor(self):
        """Step 5 of the SKILL.md workflow: the maximum downlink gap of
        the Berlin day is 55650 s (15.46 h), the trailing horizon
        interval after the last pass at 30720 s."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)
        self.assertAlmostEqual(logic.max_downlink_gap(passes_list,
                                                      HORIZON_H),
                               55650.0, delta=1.0)

    def test_max_downlink_gap_empty_returns_full_horizon(self):
        """Step 5 of the SKILL.md workflow: with no passes at all the
        maximum downlink gap is the whole 24 h horizon, 86400 s."""
        self.assertAlmostEqual(logic.max_downlink_gap([], HORIZON_H),
                               86400.0, delta=1e-6)

    def test_max_downlink_gap_trailing_boundary_identity(self):
        """Step 5 of the SKILL.md workflow: the maximum downlink gap
        covers the horizon boundary after the last pass, horizon minus
        the last pass end minus the 30 s planner step."""
        passes_list = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                          BERLIN["lat_deg"],
                                          BERLIN["lon_deg"], MASK,
                                          HORIZON_H)
        trailing = (HORIZON_H * 3600.0 - passes_list[-1]["end_s"]
                    - logic.STEP_S)
        self.assertAlmostEqual(logic.max_downlink_gap(passes_list,
                                                      HORIZON_H),
                               trailing, delta=1e-6)


class GroundStationContactPlanTest(unittest.TestCase):
    def _berlin_passes(self):
        return logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                   BERLIN["lat_deg"], BERLIN["lon_deg"],
                                   MASK, HORIZON_H)

    def _stations(self):
        return [{"lat_deg": BERLIN["lat_deg"],
                 "lon_deg": BERLIN["lon_deg"],
                 "min_elevation_deg": MASK},
                {"lat_deg": MADRID["lat_deg"],
                 "lon_deg": MADRID["lon_deg"],
                 "min_elevation_deg": MASK}]

    def test_contact_plan_berlin_madrid_anchor(self):
        """Step 6 of the SKILL.md workflow, the multi-station-contact-
        plan traverse: merging the Berlin and Madrid stations yields 6
        merged contacts, 3540 s of total contact and a 49680 s maximum
        downlink gap."""
        plan = logic.ground_station_contact_plan(self._stations(), ALT,
                                                 INC, RAAN, U0, G0,
                                                 HORIZON_H)
        self.assertEqual(len(plan["contacts"]), 6)
        self.assertAlmostEqual(plan["total_contact_s"], 3540.0,
                               delta=1.0)
        self.assertAlmostEqual(plan["max_gap_s"], 49680.0, delta=1.0)

    def test_contact_plan_first_merged_contact(self):
        """Step 6 of the SKILL.md workflow: the first merged contact of
        the multi-station plan opens at 6270 s, lasts 660 s, peaks at
        24.381 deg and carries the Madrid station index."""
        plan = logic.ground_station_contact_plan(self._stations(), ALT,
                                                 INC, RAAN, U0, G0,
                                                 HORIZON_H)
        first = plan["contacts"][0]
        self.assertAlmostEqual(first["start_s"], 6270.0, delta=1.0)
        self.assertAlmostEqual(first["duration_s"], 660.0, delta=1.0)
        self.assertAlmostEqual(first["max_elevation_deg"], 24.381,
                               delta=0.01)
        self.assertEqual(first["station_idx"], 1)

    def test_contact_plan_merged_total_bounds(self):
        """Step 6 of the SKILL.md workflow: the merged contact total
        never drops below either single-station total and never exceeds
        the sum of the station totals."""
        plan = logic.ground_station_contact_plan(self._stations(), ALT,
                                                 INC, RAAN, U0, G0,
                                                 HORIZON_H)
        berlin_total = sum(p["duration_s"] for p in self._berlin_passes())
        madrid_passes = logic.detect_passes(ALT, INC, RAAN, U0, G0,
                                            MADRID["lat_deg"],
                                            MADRID["lon_deg"], MASK,
                                            HORIZON_H)
        madrid_total = sum(p["duration_s"] for p in madrid_passes)
        self.assertGreaterEqual(plan["total_contact_s"], berlin_total)
        self.assertGreaterEqual(plan["total_contact_s"], madrid_total)
        self.assertLessEqual(plan["total_contact_s"],
                             berlin_total + madrid_total)

    def test_contact_plan_contacts_sorted_by_start(self):
        """Step 6 of the SKILL.md workflow: the merged contact list is
        sorted by start time for the downlink gap readout."""
        plan = logic.ground_station_contact_plan(self._stations(), ALT,
                                                 INC, RAAN, U0, G0,
                                                 HORIZON_H)
        starts = [c["start_s"] for c in plan["contacts"]]
        self.assertEqual(starts, sorted(starts))

    def test_contact_plan_deterministic(self):
        """Step 7 guard traverse: identical station inputs return
        identical merged plans, the fixed-step propagation uses no
        RNG."""
        a = logic.ground_station_contact_plan(self._stations(), ALT, INC,
                                              RAAN, U0, G0, HORIZON_H)
        b = logic.ground_station_contact_plan(self._stations(), ALT, INC,
                                              RAAN, U0, G0, HORIZON_H)
        self.assertEqual(a["total_contact_s"], b["total_contact_s"])
        self.assertEqual(a["max_gap_s"], b["max_gap_s"])
        self.assertEqual([c["start_s"] for c in a["contacts"]],
                         [c["start_s"] for c in b["contacts"]])


if __name__ == "__main__":
    unittest.main()
