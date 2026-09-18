#!/usr/bin/env python3
"""Contract test for the inductive-current freewheeling provision (offline)."""

import copy
import math
import unittest

from e2020_inductive_current_freewheeling_provision_logic import (
    CIRCULATING_PROVISIONS,
    DEFAULT_RESIDUAL_FRACTION,
    PROVISIONS,
    VERDICT_COMPLIANT,
    VERDICT_MARGINAL,
    VERDICT_NON_COMPLIANT,
    assess_freewheeling_provision,
    circuit_inductance_h,
    clamp_decay_time_s,
    diode_decay_time_s,
    path_decay,
    peak_switch_voltage_v,
    standoff_margin,
    stored_energy_j,
)

CLAMP_CASE = {
    "provision": "switch-clamp",
    "load_inductance_h": 1.0e-3,
    "harness_length_m": 10.0,
    "harness_inductance_h_per_m": 5.0e-7,
    "limitation_current_a": 4.0,
    "bus_voltage_v": 28.0,
    "clamp_voltage_v": 22.0,
    "switch_standoff_rating_v": 100.0,
    "required_standoff_margin": 1.5,
    "reclosure_dead_time_s": 1.0e-3,
}

DIODE_CASE = {
    "provision": "load-freewheel-diode",
    "load_inductance_h": 1.0e-3,
    "harness_length_m": 10.0,
    "harness_inductance_h_per_m": 5.0e-7,
    "load_resistance_ohm": 7.0,
    "diode_drop_v": 1.0,
    "limitation_current_a": 4.0,
    "bus_voltage_v": 28.0,
    "switch_standoff_rating_v": 100.0,
    "required_standoff_margin": 1.5,
    "reclosure_dead_time_s": 1.0e-2,
}

NO_PATH_CASE = {
    "provision": "no-path",
    "load_inductance_h": 1.0e-3,
    "harness_length_m": 10.0,
    "harness_inductance_h_per_m": 5.0e-7,
    "limitation_current_a": 4.0,
    "bus_voltage_v": 28.0,
    "switch_standoff_rating_v": 100.0,
    "required_standoff_margin": 1.5,
    "reclosure_dead_time_s": 1.0e-3,
}

TOTAL_L_H = 1.0e-3 + 10.0 * 5.0e-7


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class InductanceTests(unittest.TestCase):
    def test_load_and_harness_add_in_series(self):
        self.assertAlmostEqual(
            circuit_inductance_h(1.0e-3, 10.0, 5.0e-7), TOTAL_L_H, places=12
        )

    def test_harness_alone_is_a_valid_branch(self):
        self.assertAlmostEqual(
            circuit_inductance_h(0.0, 20.0, 5.0e-7), 1.0e-5, places=12
        )

    def test_zero_total_inductance_rejected(self):
        with self.assertRaises(ValueError):
            circuit_inductance_h(0.0, 0.0, 5.0e-7)

    def test_negative_load_inductance_rejected(self):
        with self.assertRaises(ValueError):
            circuit_inductance_h(-1.0e-3, 10.0, 5.0e-7)

    def test_non_finite_harness_length_rejected(self):
        with self.assertRaises(ValueError):
            circuit_inductance_h(1.0e-3, float("inf"), 5.0e-7)


class StoredEnergyTests(unittest.TestCase):
    def test_energy_follows_half_l_i_squared(self):
        self.assertAlmostEqual(
            stored_energy_j(1.0e-3, 4.0), 0.5 * 1.0e-3 * 16.0, places=12
        )

    def test_energy_quadruples_when_current_doubles(self):
        single = stored_energy_j(2.0e-3, 3.0)
        double = stored_energy_j(2.0e-3, 6.0)
        self.assertAlmostEqual(double, 4.0 * single, places=12)

    def test_zero_current_stores_nothing(self):
        self.assertAlmostEqual(stored_energy_j(1.0e-3, 0.0), 0.0, places=12)

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            stored_energy_j(1.0e-3, True)


class DecayTests(unittest.TestCase):
    def test_clamp_decay_is_l_i_over_v(self):
        self.assertAlmostEqual(
            clamp_decay_time_s(1.0e-3, 4.0, 20.0), 2.0e-4, places=12
        )

    def test_a_harder_clamp_ends_the_transient_sooner(self):
        soft = clamp_decay_time_s(1.0e-3, 4.0, 10.0)
        hard = clamp_decay_time_s(1.0e-3, 4.0, 40.0)
        self.assertLess(hard, soft)

    def test_zero_clamp_voltage_rejected(self):
        with self.assertRaises(ValueError):
            clamp_decay_time_s(1.0e-3, 4.0, 0.0)

    def test_diode_decay_uses_the_l_over_r_constant(self):
        expected = (1.0e-3 / 5.0) * math.log(1.0 / DEFAULT_RESIDUAL_FRACTION)
        self.assertAlmostEqual(diode_decay_time_s(1.0e-3, 5.0), expected, places=12)

    def test_tighter_residual_takes_longer(self):
        loose = diode_decay_time_s(1.0e-3, 5.0, 0.10)
        tight = diode_decay_time_s(1.0e-3, 5.0, 0.01)
        self.assertGreater(tight, loose)

    def test_residual_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            diode_decay_time_s(1.0e-3, 5.0, 1.0)

    def test_zero_load_resistance_rejected(self):
        with self.assertRaises(ValueError):
            diode_decay_time_s(1.0e-3, 0.0)


class PeakVoltageTests(unittest.TestCase):
    def test_clamp_adds_its_hold_voltage_to_the_bus(self):
        self.assertAlmostEqual(
            peak_switch_voltage_v("switch-clamp", 28.0, clamp_voltage_v=22.0),
            50.0,
            places=9,
        )

    def test_diode_adds_only_its_forward_drop(self):
        self.assertAlmostEqual(
            peak_switch_voltage_v(
                "load-freewheel-diode", 28.0, diode_drop_v=1.0
            ),
            29.0,
            places=9,
        )

    def test_no_path_has_no_defined_peak(self):
        self.assertIsNone(peak_switch_voltage_v("no-path", 28.0))

    def test_clamp_without_a_clamp_voltage_rejected(self):
        with self.assertRaises(ValueError):
            peak_switch_voltage_v("active-clamp", 28.0)

    def test_diode_without_a_forward_drop_rejected(self):
        with self.assertRaises(ValueError):
            peak_switch_voltage_v("load-freewheel-diode", 28.0)

    def test_unknown_provision_rejected(self):
        with self.assertRaises(ValueError):
            peak_switch_voltage_v("snubber", 28.0, clamp_voltage_v=10.0)

    def test_every_circulating_provision_is_a_known_provision(self):
        for provision in CIRCULATING_PROVISIONS:
            self.assertIn(provision, PROVISIONS)


class StandoffMarginTests(unittest.TestCase):
    def test_margin_is_rating_over_peak(self):
        self.assertAlmostEqual(standoff_margin(50.0, 100.0), 2.0, places=9)

    def test_zero_peak_rejected(self):
        with self.assertRaises(ValueError):
            standoff_margin(0.0, 100.0)

    def test_negative_rating_rejected(self):
        with self.assertRaises(ValueError):
            standoff_margin(50.0, -100.0)


class PathDecayTests(unittest.TestCase):
    def test_clamp_path_sends_energy_to_the_clamp(self):
        decay = path_decay(CLAMP_CASE)
        self.assertEqual(decay["energy_destination"], "clamp-element")

    def test_diode_path_sends_energy_to_the_load(self):
        decay = path_decay(DIODE_CASE)
        self.assertEqual(decay["energy_destination"], "load-resistance")

    def test_absent_path_sends_energy_into_the_switch(self):
        decay = path_decay(NO_PATH_CASE)
        self.assertEqual(decay["energy_destination"], "switching-element-avalanche")
        self.assertIsNone(decay["decay_time_s"])

    def test_path_decay_reports_the_series_inductance(self):
        decay = path_decay(CLAMP_CASE)
        self.assertAlmostEqual(decay["inductance_h"], TOTAL_L_H, places=12)

    def test_zero_limitation_current_rejected(self):
        with self.assertRaises(ValueError):
            path_decay(_case(CLAMP_CASE, limitation_current_a=0.0))


class AssessmentTests(unittest.TestCase):
    def test_clamped_case_is_adequate(self):
        result = assess_freewheeling_provision(CLAMP_CASE)
        self.assertEqual(result["verdict"], VERDICT_COMPLIANT)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_diode_case_is_adequate(self):
        result = assess_freewheeling_provision(DIODE_CASE)
        self.assertEqual(result["verdict"], VERDICT_COMPLIANT)
        self.assertAlmostEqual(result["peak_switch_voltage_v"], 29.0, places=9)

    def test_absent_path_is_inadequate_and_says_why(self):
        result = assess_freewheeling_provision(NO_PATH_CASE)
        self.assertEqual(result["verdict"], VERDICT_NON_COMPLIANT)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("no circulating path" in f for f in result["findings"])
        )

    def test_margin_exactly_on_the_requirement_still_passes(self):
        # peak is 28 + 22 = 50 V, so a 75 V rating lands the margin on 1.5.
        result = assess_freewheeling_provision(
            _case(CLAMP_CASE, switch_standoff_rating_v=75.0)
        )
        self.assertAlmostEqual(result["standoff_margin"], 1.5, places=9)
        self.assertEqual(result["verdict"], VERDICT_COMPLIANT)

    def test_thin_standoff_is_reported_as_inadequate(self):
        result = assess_freewheeling_provision(
            _case(CLAMP_CASE, switch_standoff_rating_v=60.0)
        )
        self.assertEqual(result["verdict"], VERDICT_NON_COMPLIANT)
        self.assertTrue(
            any("standoff margin" in f for f in result["findings"])
        )

    def test_decay_exactly_on_the_dead_time_still_passes(self):
        decay = clamp_decay_time_s(TOTAL_L_H, 4.0, 22.0)
        result = assess_freewheeling_provision(
            _case(CLAMP_CASE, reclosure_dead_time_s=decay)
        )
        self.assertAlmostEqual(result["decay_time_s"], decay, places=12)
        self.assertTrue(result["decay_fits_dead_time"])
        self.assertEqual(result["verdict"], VERDICT_COMPLIANT)

    def test_decay_outlasting_the_dead_time_is_inadequate(self):
        result = assess_freewheeling_provision(
            _case(CLAMP_CASE, reclosure_dead_time_s=1.0e-6)
        )
        self.assertEqual(result["verdict"], VERDICT_NON_COMPLIANT)
        self.assertFalse(result["decay_fits_dead_time"])

    def test_missing_dead_time_is_marginal_not_a_pass(self):
        case = _case(CLAMP_CASE)
        del case["reclosure_dead_time_s"]
        result = assess_freewheeling_provision(case)
        self.assertEqual(result["verdict"], VERDICT_MARGINAL)
        self.assertIsNone(result["compliant"])

    def test_a_softer_clamp_trades_decay_time_for_standoff(self):
        soft = assess_freewheeling_provision(
            _case(CLAMP_CASE, clamp_voltage_v=10.0)
        )
        hard = assess_freewheeling_provision(
            _case(CLAMP_CASE, clamp_voltage_v=40.0, switch_standoff_rating_v=200.0)
        )
        self.assertGreater(soft["decay_time_s"], hard["decay_time_s"])
        self.assertGreater(hard["peak_switch_voltage_v"], soft["peak_switch_voltage_v"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_freewheeling_provision("switch-clamp")

    def test_missing_standoff_rating_rejected(self):
        case = _case(CLAMP_CASE)
        del case["switch_standoff_rating_v"]
        with self.assertRaises(ValueError):
            assess_freewheeling_provision(case)

    def test_result_is_deterministic(self):
        first = assess_freewheeling_provision(CLAMP_CASE)
        second = assess_freewheeling_provision(CLAMP_CASE)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=1)
