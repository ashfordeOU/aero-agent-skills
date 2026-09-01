#!/usr/bin/env python3
"""Gate 3 contract test: phase lead and lag compensation.

Exercises scripts/lead_lag_compensation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (plant transfer
function evaluation at jw, gain crossover frequency, phase margin,
lead compensator synthesis from the required phase boost, lag
compensator synthesis below crossover, error constants and steady
state error, invalid inputs raise ValueError.

Anchors (plant G(s) = 1/(s(s + 1)), num [1], den [1, 1, 0]):
- magnitude at w = 1: 20*log10(1/sqrt(2)) = -3.0103 dB
- phase at w = 1: -135 degrees
- gain crossover: 0.7862 rad/s, phase margin 51.8273 degrees
- lead alpha for 30 degree boost: 1/3; max phase of alpha 1/3: 30 deg
- lead gain boost at alpha 1/3: 4.7712 dB; at alpha 0.5: 3.0103 dB
- lead zero/pole at (alpha 1/3, omega_m 1): T sqrt(3), zero 0.5774,
  pole 1.7321; lead phase at omega_m: 30 degrees
- design for 60 degree spec with 5 degree margin: boost 13.1727 deg,
  alpha 0.6288, omega_m 0.9255, compensated phase margin 60.39 deg
- lag at (omega_gc 1, beta 10): zero 0.1, pole 0.01, phase at w 1:
  -5.1377 degrees; dc gain 10, high frequency gain 1
- Kv of 1/(s(s + 1)): 1.0; with lag beta 10: 10.0 (ramp error 0.1)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lead_lag_compensation_logic as llc  # noqa: E402

PLANT_NUM = [1.0]
PLANT_DEN = [1.0, 1.0, 0.0]


class TfEvalTest(unittest.TestCase):
    def test_anchor_magnitude_db_at_one(self):
        self.assertAlmostEqual(llc.magnitude_db(PLANT_NUM, PLANT_DEN, 1.0), -3.0103, places=4)

    def test_anchor_phase_deg_at_one(self):
        self.assertAlmostEqual(llc.phase_deg(PLANT_NUM, PLANT_DEN, 1.0), -135.0, places=4)

    def test_magnitude_monotone_decreasing(self):
        high = llc.magnitude_db(PLANT_NUM, PLANT_DEN, 2.0)
        low = llc.magnitude_db(PLANT_NUM, PLANT_DEN, 0.5)
        self.assertLess(high, low)

    def test_invalid_omega_raises(self):
        with self.assertRaises(ValueError):
            llc.magnitude_db(PLANT_NUM, PLANT_DEN, -1.0)
        with self.assertRaises(ValueError):
            llc.phase_deg(PLANT_NUM, PLANT_DEN, -1.0)


class GainCrossoverTest(unittest.TestCase):
    def test_anchor_crossover_plant(self):
        self.assertAlmostEqual(llc.gain_crossover_frequency(PLANT_NUM, PLANT_DEN), 0.7862, places=3)

    def test_anchor_crossover_gain_ten(self):
        self.assertAlmostEqual(llc.gain_crossover_frequency([10.0], [1.0, 1.0]), 9.9499, places=3)

    def test_no_crossover_raises(self):
        with self.assertRaises(ValueError):
            llc.gain_crossover_frequency([0.5], [1.0, 1.0])


class PhaseMarginTest(unittest.TestCase):
    def test_anchor_pm_plant(self):
        self.assertAlmostEqual(llc.phase_margin_degrees(PLANT_NUM, PLANT_DEN), 51.8273, places=3)

    def test_anchor_pm_gain_ten(self):
        self.assertAlmostEqual(llc.phase_margin_degrees([10.0], [1.0, 1.0]), 95.7392, places=3)

    def test_positive_pm_means_stable(self):
        self.assertGreater(llc.phase_margin_degrees(PLANT_NUM, PLANT_DEN), 0.0)


class LeadAlphaTest(unittest.TestCase):
    def test_anchor_alpha_thirty(self):
        self.assertAlmostEqual(llc.lead_alpha_from_phase_boost(30.0), 1.0 / 3.0, places=6)

    def test_anchor_alpha_forty_five(self):
        s = (1.0 - 2.0**-0.5) / (1.0 + 2.0**-0.5)
        self.assertAlmostEqual(llc.lead_alpha_from_phase_boost(45.0), s, places=6)

    def test_smaller_alpha_larger_boost(self):
        small = llc.lead_alpha_from_phase_boost(50.0)
        large = llc.lead_alpha_from_phase_boost(20.0)
        self.assertLess(small, large)

    def test_invalid_boost_raises(self):
        for bad in (0.0, -5.0, 90.0, 120.0):
            with self.assertRaises(ValueError):
                llc.lead_alpha_from_phase_boost(bad)


class LeadMaxPhaseTest(unittest.TestCase):
    def test_anchor_max_phase_one_third(self):
        self.assertAlmostEqual(llc.lead_max_phase_deg(1.0 / 3.0), 30.0, places=6)

    def test_roundtrip_alpha_phase(self):
        alpha = llc.lead_alpha_from_phase_boost(25.0)
        self.assertAlmostEqual(llc.lead_max_phase_deg(alpha), 25.0, places=6)

    def test_invalid_alpha_raises(self):
        for bad in (0.0, -1.0, 1.0, 2.0):
            with self.assertRaises(ValueError):
                llc.lead_max_phase_deg(bad)


class LeadGainBoostTest(unittest.TestCase):
    def test_anchor_boost_one_third(self):
        self.assertAlmostEqual(llc.lead_gain_boost_db(1.0 / 3.0), 4.7712, places=4)

    def test_anchor_boost_half(self):
        self.assertAlmostEqual(llc.lead_gain_boost_db(0.5), 3.0103, places=4)

    def test_smaller_alpha_higher_boost(self):
        self.assertGreater(llc.lead_gain_boost_db(0.2), llc.lead_gain_boost_db(0.8))

    def test_invalid_alpha_raises(self):
        with self.assertRaises(ValueError):
            llc.lead_gain_boost_db(1.0)


class LeadZeroPoleTest(unittest.TestCase):
    def test_anchor_components(self):
        t, zero, pole = llc.lead_zero_pole(1.0 / 3.0, 1.0)
        self.assertAlmostEqual(t, 3.0**0.5, places=6)
        self.assertAlmostEqual(zero, 1.0 / 3.0**0.5, places=6)
        self.assertAlmostEqual(pole, 3.0**0.5, places=6)

    def test_zero_below_pole(self):
        _, zero, pole = llc.lead_zero_pole(0.5, 10.0)
        self.assertLess(zero, pole)

    def test_higher_omega_moves_pair_up(self):
        _, z1, p1 = llc.lead_zero_pole(0.5, 1.0)
        _, z2, p2 = llc.lead_zero_pole(0.5, 10.0)
        self.assertGreater(z2, z1)
        self.assertGreater(p2, p1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            llc.lead_zero_pole(1.0, 1.0)
        with self.assertRaises(ValueError):
            llc.lead_zero_pole(0.5, 0.0)
        with self.assertRaises(ValueError):
            llc.lead_zero_pole(0.5, -1.0)


class LeadPhaseTest(unittest.TestCase):
    def test_anchor_phase_at_omega_m(self):
        t = 3.0**0.5
        self.assertAlmostEqual(llc.lead_phase_deg(1.0 / 3.0, t, 1.0), 30.0, places=6)

    def test_phase_zero_at_dc(self):
        self.assertAlmostEqual(llc.lead_phase_deg(0.5, 1.0, 0.0), 0.0, places=6)

    def test_phase_below_peak_elsewhere(self):
        t = 3.0**0.5
        off = llc.lead_phase_deg(1.0 / 3.0, t, 3.0)
        self.assertLess(off, 30.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            llc.lead_phase_deg(1.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            llc.lead_phase_deg(0.5, 0.0, 1.0)
        with self.assertRaises(ValueError):
            llc.lead_phase_deg(0.5, 1.0, -1.0)


class LeadTransferFunctionTest(unittest.TestCase):
    def test_dc_gain_one(self):
        num, den = llc.lead_transfer_function(0.5, 1.0)
        self.assertAlmostEqual(num[-1] / den[-1], 1.0, places=6)

    def test_high_frequency_gain_one_over_alpha(self):
        num, den = llc.lead_transfer_function(0.5, 1.0)
        self.assertAlmostEqual(num[0] / den[0], 2.0, places=6)


class DesignLeadTest(unittest.TestCase):
    def test_anchor_design_parameters(self):
        d = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=5.0)
        self.assertAlmostEqual(d["pm_plant"], 51.8273, places=3)
        self.assertAlmostEqual(d["boost_deg"], 13.1727, places=3)
        self.assertAlmostEqual(d["alpha"], 0.6288, places=3)
        self.assertAlmostEqual(d["omega_m"], 0.9255, places=3)

    def test_design_meets_spec(self):
        d = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=5.0)
        cpm = llc.compensated_phase_margin(PLANT_NUM, PLANT_DEN, d["num"], d["den"])
        self.assertAlmostEqual(cpm, 60.39, places=1)
        self.assertGreater(cpm, 60.0)

    def test_design_places_crossover_at_omega_m(self):
        d = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=5.0)
        pnum, pden = llc.series_tf(PLANT_NUM, PLANT_DEN, d["num"], d["den"])
        self.assertAlmostEqual(llc.gain_crossover_frequency(pnum, pden), d["omega_m"], places=6)

    def test_design_plant_gain_at_omega_m_is_sqrt_alpha(self):
        d = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=5.0)
        self.assertAlmostEqual(
            llc.magnitude_db(PLANT_NUM, PLANT_DEN, d["omega_m"]),
            -llc.lead_gain_boost_db(d["alpha"]),
            places=4,
        )

    def test_design_crossover_higher_than_plant(self):
        d = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=5.0)
        self.assertGreater(d["omega_m"], llc.gain_crossover_frequency(PLANT_NUM, PLANT_DEN))

    def test_tighter_spec_larger_boost(self):
        tight = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 75.0, boost_margin=5.0)
        loose = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=5.0)
        self.assertGreater(tight["boost_deg"], loose["boost_deg"])
        self.assertLess(tight["alpha"], loose["alpha"])

    def test_invalid_spec_raises(self):
        with self.assertRaises(ValueError):
            llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 0.0)
        with self.assertRaises(ValueError):
            llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0, boost_margin=0.0)

    def test_spec_already_met_raises(self):
        with self.assertRaises(ValueError):
            llc.design_lead_compensator([10.0], [1.0, 1.0], 60.0, boost_margin=5.0)


class LagZeroPoleTest(unittest.TestCase):
    def test_anchor_components(self):
        zero, pole = llc.lag_zero_pole(1.0, 10.0)
        self.assertAlmostEqual(zero, 0.1, places=6)
        self.assertAlmostEqual(pole, 0.01, places=6)

    def test_zero_one_decade_below_crossover(self):
        zero, _ = llc.lag_zero_pole(5.0, 10.0)
        self.assertAlmostEqual(zero, 0.5, places=6)

    def test_pole_below_zero(self):
        zero, pole = llc.lag_zero_pole(1.0, 10.0)
        self.assertLess(pole, zero)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            llc.lag_zero_pole(0.0, 10.0)
        with self.assertRaises(ValueError):
            llc.lag_zero_pole(1.0, 1.0)
        with self.assertRaises(ValueError):
            llc.lag_zero_pole(1.0, 0.5)
        with self.assertRaises(ValueError):
            llc.lag_zero_pole(1.0, 10.0, decades_below=0.0)


class LagPhaseTest(unittest.TestCase):
    def test_anchor_phase_at_crossover(self):
        self.assertAlmostEqual(llc.lag_phase_deg(0.1, 0.01, 1.0), -5.1377, places=4)

    def test_phase_negative_below_crossover(self):
        self.assertLess(llc.lag_phase_deg(0.1, 0.01, 1.0), 0.0)

    def test_small_phase_at_high_omega(self):
        self.assertLess(abs(llc.lag_phase_deg(0.1, 0.01, 1000.0)), 0.01)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            llc.lag_phase_deg(0.0, 0.01, 1.0)
        with self.assertRaises(ValueError):
            llc.lag_phase_deg(0.1, 0.0, 1.0)
        with self.assertRaises(ValueError):
            llc.lag_phase_deg(0.1, 0.01, -1.0)


class LagTransferFunctionTest(unittest.TestCase):
    def test_dc_gain_equals_beta(self):
        zero, pole = llc.lag_zero_pole(1.0, 10.0)
        num, den = llc.lag_transfer_function(zero, pole, 10.0)
        self.assertAlmostEqual(num[-1] / den[-1], 10.0, places=6)

    def test_high_frequency_gain_one(self):
        zero, pole = llc.lag_zero_pole(1.0, 10.0)
        num, den = llc.lag_transfer_function(zero, pole, 10.0)
        self.assertAlmostEqual(num[0] / den[0], 1.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            llc.lag_transfer_function(0.0, 0.01, 10.0)
        with self.assertRaises(ValueError):
            llc.lag_transfer_function(0.1, 0.0, 10.0)
        with self.assertRaises(ValueError):
            llc.lag_transfer_function(0.1, 0.01, 0.0)


class ErrorConstantTest(unittest.TestCase):
    def test_anchor_kv_type_one(self):
        self.assertAlmostEqual(llc.velocity_error_constant(PLANT_NUM, PLANT_DEN), 1.0, places=6)

    def test_anchor_kp_type_zero(self):
        self.assertAlmostEqual(llc.position_error_constant([1.0], [1.0, 2.0]), 0.5, places=6)

    def test_kp_infinite_for_type_one(self):
        self.assertEqual(llc.position_error_constant(PLANT_NUM, PLANT_DEN), float("inf"))

    def test_step_error_finite_kp(self):
        self.assertAlmostEqual(llc.steady_state_error_step(4.0), 0.2, places=6)

    def test_step_error_zero_for_type_one(self):
        kp = llc.position_error_constant(PLANT_NUM, PLANT_DEN)
        self.assertAlmostEqual(llc.steady_state_error_step(kp), 0.0, places=6)

    def test_ramp_error_anchors(self):
        self.assertAlmostEqual(llc.steady_state_error_ramp(1.0), 1.0, places=6)
        self.assertAlmostEqual(llc.steady_state_error_ramp(10.0), 0.1, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            llc.velocity_error_constant([1.0], [1.0, 1.0])
        with self.assertRaises(ValueError):
            llc.steady_state_error_ramp(0.0)
        with self.assertRaises(ValueError):
            llc.steady_state_error_step(-1.0)


class DesignLagTest(unittest.TestCase):
    def test_anchor_kv_improvement(self):
        d = llc.design_lag_compensator(PLANT_NUM, PLANT_DEN, 10.0)
        self.assertAlmostEqual(d["kv_before"], 1.0, places=6)
        self.assertAlmostEqual(d["kv_after"], 10.0, places=6)
        self.assertAlmostEqual(d["dc_gain"], 10.0, places=6)

    def test_zero_placed_below_crossover(self):
        d = llc.design_lag_compensator(PLANT_NUM, PLANT_DEN, 10.0)
        self.assertAlmostEqual(d["zero"], d["omega_gc"] / 10.0, places=6)

    def test_ramp_error_improved_by_beta(self):
        d = llc.design_lag_compensator(PLANT_NUM, PLANT_DEN, 10.0)
        before = llc.steady_state_error_ramp(d["kv_before"])
        after = llc.steady_state_error_ramp(d["kv_after"])
        self.assertAlmostEqual(after, before / 10.0, places=6)

    def test_loop_stays_stable(self):
        d = llc.design_lag_compensator(PLANT_NUM, PLANT_DEN, 10.0)
        pnum, pden = llc.series_tf(PLANT_NUM, PLANT_DEN, d["num"], d["den"])
        pm = llc.phase_margin_degrees(pnum, pden)
        self.assertGreater(pm, 40.0)

    def test_larger_beta_larger_kv(self):
        d10 = llc.design_lag_compensator(PLANT_NUM, PLANT_DEN, 10.0)
        d20 = llc.design_lag_compensator(PLANT_NUM, PLANT_DEN, 20.0)
        self.assertGreater(d20["kv_after"], d10["kv_after"])


class SeriesTfTest(unittest.TestCase):
    def test_series_multiplication(self):
        num, den = llc.series_tf([1.0], [1.0, 1.0], [1.0, 0.0], [1.0, 2.0])
        self.assertEqual(num, [1.0, 0.0])
        self.assertEqual(den, [1.0, 3.0, 2.0])

    def test_lead_then_lag_equals_compensated_loop(self):
        lead = llc.design_lead_compensator(PLANT_NUM, PLANT_DEN, 60.0)
        zero, pole = llc.lag_zero_pole(lead["omega_m"], 2.0)
        lnum, lden = llc.lag_transfer_function(zero, pole, 2.0)
        combined, _ = llc.series_tf(lead["num"], lead["den"], lnum, lden)
        direct = llc.polmul(lead["num"], lnum)
        self.assertEqual(combined, direct)


if __name__ == "__main__":
    unittest.main(verbosity=2)
