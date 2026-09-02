#!/usr/bin/env python3
"""Gate 3 contract test: design mission profile and block fuel/time.

Exercises scripts/mission_profile_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - segment fuel models
(taxi/takeoff, climb, cruise, descent, loiter, reserve), the Breguet
range equation for cruise fuel, Breguet endurance for loiter and hold
fuel, block fuel and block time summation with chained segment weights,
reserve fuel rules (45 minute hold at 1500 ft plus 5 percent
contingency, FAR 121 alternate plus hold), mission fuel fraction,
payload-range trade point, and required fuel including reserves.
Reference values are hand-computed analytic results; invalid inputs
raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mission_profile_logic as mp  # noqa: E402


class BreguetCruiseTest(unittest.TestCase):
    def test_cruise_fuel_matches_hand_breguet_calc(self):
        # Turbofan: R = 3000 nm, L/D = 18, TSFC = 0.6 lb/lbf/hr,
        # V = 450 kt, W0 = 150000 lb. Hand Breguet range equation:
        # W_fuel = W0 * (1 - exp(-R / (V * TSFC * (L/D)))).
        expected = 150000.0 * (1.0 - math.exp(-3000.0 / (450.0 * 0.6 * 18.0)))
        got = mp.breguet_cruise_fuel(3000.0, 450.0, 0.6, 18.0, 150000.0)
        self.assertAlmostEqual(got, expected, places=6)
        # Hard reference value from the analytic expression: 69088.87 lb.
        self.assertLess(abs(got - 69088.87) / 69088.87, 0.01)

    def test_cruise_fuel_scales_with_range(self):
        # Doubling the range at fixed speed, TSFC, and L/D burns more
        # fuel, and the extra burn is sub-exponential.
        short = mp.breguet_cruise_fuel(1500.0, 450.0, 0.6, 18.0, 150000.0)
        long = mp.breguet_cruise_fuel(3000.0, 450.0, 0.6, 18.0, 150000.0)
        self.assertLess(short, long)
        self.assertLess(long, 2.0 * short)

    def test_cruise_fuel_never_exceeds_start_weight(self):
        # The exponential form keeps the fuel fraction below 1 even for
        # very long ranges.
        got = mp.breguet_cruise_fuel(20000.0, 450.0, 0.6, 18.0, 150000.0)
        self.assertLess(got, 150000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mp.breguet_cruise_fuel(0.0, 450.0, 0.6, 18.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_cruise_fuel(3000.0, -450.0, 0.6, 18.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_cruise_fuel(3000.0, 450.0, 0.0, 18.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_cruise_fuel(3000.0, 450.0, 0.6, 0.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_cruise_fuel(3000.0, 450.0, 0.6, 18.0, 0.0)


class BreguetLoiterTest(unittest.TestCase):
    def test_loiter_fuel_45_min_reserve(self):
        # 45 minute hold at 1500 ft: E = 0.75 hr, TSFC = 0.6 lb/lbf/hr,
        # L/D = 18, W0 = 150000 lb. Breguet endurance:
        # W_fuel = W0 * (1 - exp(-E * TSFC / (L/D))) = 3703.51 lb.
        expected = 150000.0 * (1.0 - math.exp(-0.75 * 0.6 / 18.0))
        got = mp.breguet_loiter_fuel(0.75, 0.6, 18.0, 150000.0)
        self.assertAlmostEqual(got, expected, places=6)
        self.assertLess(abs(got - 3703.51) / 3703.51, 0.01)

    def test_loiter_fuel_grows_sublinearly_with_endurance(self):
        # Breguet endurance is exponential: doubling the hold time
        # gives more fuel but less than double (sub-linear saturation).
        half = mp.breguet_loiter_fuel(0.5, 0.6, 18.0, 150000.0)
        full = mp.breguet_loiter_fuel(1.0, 0.6, 18.0, 150000.0)
        self.assertGreater(full, half)
        self.assertLess(full, 2.0 * half)

    def test_loiter_fuel_zero_endurance_rejected(self):
        # Zero hold time is degenerate; the module rejects it rather
        # than silently reporting a zero burn.
        with self.assertRaises(ValueError):
            mp.breguet_loiter_fuel(0.0, 0.6, 18.0, 150000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mp.breguet_loiter_fuel(-0.5, 0.6, 18.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_loiter_fuel(0.75, 0.0, 18.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_loiter_fuel(0.75, 0.6, 0.0, 150000.0)
        with self.assertRaises(ValueError):
            mp.breguet_loiter_fuel(0.75, 0.6, 18.0, -10.0)


class SegmentFuelTest(unittest.TestCase):
    def test_taxi_takeoff_descent_fuel_flow_times_time(self):
        # Taxi at 1200 lb/hr for 0.25 hr: 300 lb.
        self.assertAlmostEqual(
            mp.segment_fuel("taxi", 150000.0,
                            {"fuel_flow": 1200.0, "time": 0.25}), 300.0)
        # Takeoff at 18000 lb/hr for 0.05 hr: 900 lb.
        self.assertAlmostEqual(
            mp.segment_fuel("takeoff", 149700.0,
                            {"fuel_flow": 18000.0, "time": 0.05}), 900.0)
        # Descent at 2500 lb/hr for 0.30 hr: 750 lb.
        self.assertAlmostEqual(
            mp.segment_fuel("descent", 77000.0,
                            {"fuel_flow": 2500.0, "time": 0.30}), 750.0)

    def test_climb_fuel_flow_model(self):
        # Climb at 24000 lb/hr for 0.25 hr: 6000 lb.
        self.assertAlmostEqual(
            mp.segment_fuel("climb", 148800.0,
                            {"fuel_flow": 24000.0, "time": 0.25}), 6000.0)

    def test_climb_fuel_fraction_model(self):
        # Climb fuel as 3 percent of the segment start weight.
        self.assertAlmostEqual(
            mp.segment_fuel("climb", 150000.0, {"fraction": 0.03}), 4500.0)

    def test_climb_fraction_must_be_below_one(self):
        with self.assertRaises(ValueError):
            mp.segment_fuel("climb", 150000.0, {"fraction": 1.0})
        with self.assertRaises(ValueError):
            mp.segment_fuel("climb", 150000.0, {"fraction": 0.0})

    def test_cruise_segment_uses_breguet(self):
        # The cruise segment delegates to the Breguet range equation.
        self.assertAlmostEqual(
            mp.segment_fuel("cruise", 150000.0,
                            {"R_nm": 3000.0, "V_kt": 450.0,
                             "TSFC": 0.6, "LD": 18.0}),
            mp.breguet_cruise_fuel(3000.0, 450.0, 0.6, 18.0, 150000.0))

    def test_loiter_and_reserve_segments_use_breguet_endurance(self):
        # Both the loiter and the reserve hold burn by Breguet endurance.
        loiter = mp.segment_fuel("loiter", 150000.0,
                                 {"E_hr": 0.75, "TSFC": 0.6, "LD": 18.0})
        reserve = mp.segment_fuel("reserve", 150000.0,
                                  {"E_hr": 0.75, "TSFC": 0.6, "LD": 18.0})
        self.assertAlmostEqual(loiter,
                               mp.breguet_loiter_fuel(0.75, 0.6, 18.0, 150000.0))
        self.assertAlmostEqual(reserve, loiter)

    def test_invalid_segment_type_raises(self):
        # An unknown segment type must fail loudly, not silently burn 0.
        with self.assertRaises(ValueError):
            mp.segment_fuel("hover", 150000.0, {"fuel_flow": 1000.0,
                                                "time": 0.5})
        with self.assertRaises(ValueError):
            mp.segment_fuel("cruise", 150000.0, {})

    def test_missing_params_raise(self):
        with self.assertRaises(ValueError):
            mp.segment_fuel("cruise", 150000.0,
                            {"R_nm": 3000.0, "V_kt": 450.0, "TSFC": 0.6})
        with self.assertRaises(ValueError):
            mp.segment_fuel("taxi", 150000.0, {"fuel_flow": 1200.0})


class BlockFuelAndTimeTest(unittest.TestCase):
    def full_mission(self):
        # Design mission: taxi, takeoff, climb, cruise, descent, loiter.
        return [
            {"type": "taxi",
             "params": {"fuel_flow": 1200.0, "time": 0.25}},
            {"type": "takeoff",
             "params": {"fuel_flow": 18000.0, "time": 0.05}},
            {"type": "climb",
             "params": {"fuel_flow": 24000.0, "time": 0.25}},
            {"type": "cruise",
             "params": {"R_nm": 3000.0, "V_kt": 450.0,
                        "TSFC": 0.6, "LD": 18.0}},
            {"type": "descent",
             "params": {"fuel_flow": 2500.0, "time": 0.30}},
            {"type": "loiter",
             "params": {"E_hr": 0.5, "TSFC": 0.6, "LD": 15.0}},
        ]

    def test_block_fuel_sums_chained_segment_fuels(self):
        # Chain the segment weights by hand: each segment burns from the
        # weight remaining after all earlier segments.
        segments = self.full_mission()
        w = 150000.0
        fuels = []
        for seg in segments:
            f = mp.segment_fuel(seg["type"], w, seg["params"])
            fuels.append(f)
            w -= f
        result = mp.block_fuel_and_time(segments, 150000.0)
        self.assertEqual(len(result["segment_fuels"]), 6)
        for got, expected in zip(result["segment_fuels"], fuels):
            self.assertAlmostEqual(got, expected, places=6)
        self.assertAlmostEqual(result["block_fuel_lb"], sum(fuels), places=6)
        # Hand reference: 75233.00 lb block fuel for this mission.
        self.assertLess(abs(result["block_fuel_lb"] - 75233.00) / 75233.00, 0.01)

    def test_block_time_sums_explicit_and_derived_times(self):
        # Cruise time derives from R/V = 3000/450 = 6.6667 hr, loiter
        # time is E_hr = 0.5 hr, the rest are explicit.
        result = mp.block_fuel_and_time(self.full_mission(), 150000.0)
        expected = 0.25 + 0.05 + 0.25 + 3000.0 / 450.0 + 0.30 + 0.5
        self.assertAlmostEqual(result["block_time_hr"], expected, places=6)
        self.assertAlmostEqual(result["block_time_hr"], 8.0166667, places=4)

    def test_end_weight_is_start_minus_block_fuel(self):
        result = mp.block_fuel_and_time(self.full_mission(), 150000.0)
        self.assertAlmostEqual(
            result["end_weight_lb"], 150000.0 - result["block_fuel_lb"], places=6)

    def test_empty_segments_raise(self):
        with self.assertRaises(ValueError):
            mp.block_fuel_and_time([], 150000.0)

    def test_missing_time_raises_for_flow_segments(self):
        segments = [
            {"type": "taxi", "params": {"fuel_flow": 1200.0, "time": 0.25}},
            {"type": "climb", "params": {"fuel_flow": 24000.0}},  # no time
        ]
        with self.assertRaises(ValueError):
            mp.block_fuel_and_time(segments, 150000.0)

    def test_unknown_segment_in_block_raises(self):
        segments = [{"type": "hover", "params": {"fuel_flow": 1000.0,
                                                 "time": 0.5}}]
        with self.assertRaises(ValueError):
            mp.block_fuel_and_time(segments, 150000.0)


class ReserveFuelTest(unittest.TestCase):
    def test_hold45_5pct_rule(self):
        # 45 minute hold at 1500 ft plus 5 percent contingency on trip
        # fuel. Landing weight 74767 lb, trip fuel 75233 lb:
        # hold = 74767 * (1 - exp(-0.75*0.6/18)) = 1846.00 lb, plus
        # 0.05 * 75233 = 3761.65 lb, total 5607.65 lb.
        got = mp.reserve_fuel(
            74766.998, rule="hold45_5pct",
            params={"TSFC": 0.6, "LD": 18.0, "trip_fuel": 75233.0})
        expected_hold = 74766.998 * (1.0 - math.exp(-0.75 * 0.6 / 18.0))
        expected = expected_hold + 0.05 * 75233.0
        self.assertAlmostEqual(got, expected, places=3)
        self.assertLess(abs(got - 5607.65) / 5607.65, 0.01)

    def test_far121_rule(self):
        # FAR 121 style: alternate fuel plus 30 minute hold at 1500 ft.
        # Alternate 8000 lb plus hold 74767 * (1 - exp(-0.5*0.6/18)).
        got = mp.reserve_fuel(
            74766.998, rule="far121",
            params={"alternate_fuel": 8000.0, "TSFC": 0.6, "LD": 18.0})
        expected_hold = 74766.998 * (1.0 - math.exp(-0.5 * 0.6 / 18.0))
        self.assertAlmostEqual(got, 8000.0 + expected_hold, places=3)

    def test_hold_fuel_matches_breguet_endurance(self):
        # The 45 minute hold leg is exactly the endurance equation.
        hold = mp.reserve_fuel(150000.0, rule="hold45_5pct",
                               params={"TSFC": 0.6, "LD": 18.0,
                                       "trip_fuel": 50000.0})
        expected = (150000.0 * (1.0 - math.exp(-0.75 * 0.6 / 18.0))
                    + 0.05 * 50000.0)
        self.assertAlmostEqual(hold, expected, places=6)

    def test_invalid_rule_raises(self):
        with self.assertRaises(ValueError):
            mp.reserve_fuel(150000.0, rule="no_rule", params={})

    def test_missing_params_raise(self):
        with self.assertRaises(ValueError):
            mp.reserve_fuel(150000.0, rule="hold45_5pct",
                            params={"TSFC": 0.6, "LD": 18.0})
        with self.assertRaises(ValueError):
            mp.reserve_fuel(150000.0, rule="far121",
                            params={"TSFC": 0.6, "LD": 18.0})


class MissionFractionTest(unittest.TestCase):
    def test_mission_fuel_fraction(self):
        segments = [
            {"type": "climb", "params": {"fuel_flow": 24000.0, "time": 0.25}},
            {"type": "cruise",
             "params": {"R_nm": 3000.0, "V_kt": 450.0,
                        "TSFC": 0.6, "LD": 18.0}},
            {"type": "descent", "params": {"fuel_flow": 2500.0, "time": 0.30}},
        ]
        block = mp.block_fuel_and_time(segments, 150000.0)
        frac = mp.mission_fuel_fraction(segments, 150000.0)
        self.assertAlmostEqual(frac, block["block_fuel_lb"] / 150000.0, places=9)
        self.assertGreater(frac, 0.0)
        self.assertLess(frac, 1.0)

    def test_empty_segments_raise(self):
        with self.assertRaises(ValueError):
            mp.mission_fuel_fraction([], 150000.0)


class PayloadRangeTradePointTest(unittest.TestCase):
    def test_trade_point_is_fuel_capacity_limited(self):
        # W_TO = 150000, OEW = 90000, payload = 20000 lb leaves 40000 lb
        # for fuel, less than a 50000 lb tank: the trade point flies at
        # the capacity of the payload-fuel envelope, 40000 lb.
        got = mp.payload_range_trade_point(150000.0, 90000.0, 20000.0,
                                           50000.0, 450.0, 0.6, 18.0)
        self.assertAlmostEqual(got["fuel_lb"], 40000.0, places=6)
        expected_range = 450.0 * 0.6 * 18.0 * math.log(150000.0 / 110000.0)
        self.assertAlmostEqual(got["range_nm"], expected_range, places=6)
        self.assertAlmostEqual(got["range_nm"], 1507.35, delta=15.1)

    def test_trade_point_respects_tank_capacity(self):
        # With a small tank the trade point is tank-limited, not
        # payload-envelope limited.
        got = mp.payload_range_trade_point(150000.0, 90000.0, 20000.0,
                                           20000.0, 450.0, 0.6, 18.0)
        self.assertAlmostEqual(got["fuel_lb"], 20000.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mp.payload_range_trade_point(150000.0, 90000.0, 60000.0,
                                         50000.0, 450.0, 0.6, 18.0)
        with self.assertRaises(ValueError):
            mp.payload_range_trade_point(150000.0, 90000.0, 20000.0,
                                         0.0, 450.0, 0.6, 18.0)


class RequiredFuelTest(unittest.TestCase):
    def test_required_fuel_includes_reserves(self):
        segments = [
            {"type": "climb", "params": {"fuel_flow": 24000.0, "time": 0.25}},
            {"type": "cruise",
             "params": {"R_nm": 3000.0, "V_kt": 450.0,
                        "TSFC": 0.6, "LD": 18.0}},
            {"type": "descent", "params": {"fuel_flow": 2500.0, "time": 0.30}},
        ]
        got = mp.required_fuel(segments, 150000.0, reserve_rule="hold45_5pct",
                               reserve_params={"TSFC": 0.6, "LD": 18.0})
        block = mp.block_fuel_and_time(segments, 150000.0)
        landing = block["end_weight_lb"]
        expected_reserve = mp.reserve_fuel(
            landing, rule="hold45_5pct",
            params={"TSFC": 0.6, "LD": 18.0,
                    "trip_fuel": block["block_fuel_lb"]})
        self.assertAlmostEqual(got["block_fuel_lb"], block["block_fuel_lb"],
                               places=6)
        self.assertAlmostEqual(got["landing_weight_lb"], landing, places=6)
        self.assertAlmostEqual(got["reserve_fuel_lb"], expected_reserve,
                               places=6)
        self.assertAlmostEqual(got["required_fuel_lb"],
                               block["block_fuel_lb"] + expected_reserve,
                               places=6)

    def test_required_fuel_far121(self):
        segments = [
            {"type": "climb", "params": {"fuel_flow": 24000.0, "time": 0.25}},
            {"type": "cruise",
             "params": {"R_nm": 3000.0, "V_kt": 450.0,
                        "TSFC": 0.6, "LD": 18.0}},
        ]
        got = mp.required_fuel(segments, 150000.0, reserve_rule="far121",
                               reserve_params={"alternate_fuel": 8000.0,
                                               "TSFC": 0.6, "LD": 18.0})
        landing = got["landing_weight_lb"]
        expected_hold = landing * (1.0 - math.exp(-0.5 * 0.6 / 18.0))
        self.assertAlmostEqual(got["reserve_fuel_lb"], 8000.0 + expected_hold,
                               places=6)
        self.assertGreater(got["required_fuel_lb"], got["block_fuel_lb"])

    def test_invalid_segments_raise(self):
        with self.assertRaises(ValueError):
            mp.required_fuel([{"type": "hover", "params": {}}], 150000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
