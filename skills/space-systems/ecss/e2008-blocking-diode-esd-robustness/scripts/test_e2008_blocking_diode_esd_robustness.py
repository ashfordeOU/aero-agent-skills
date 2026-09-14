#!/usr/bin/env python3
"""Contract test for the blocking diode human-contact ESD screen (offline)."""

import copy
import unittest

from e2008_blocking_diode_esd_robustness_logic import (
    ACCEPT,
    DEFAULT_ESD_CRITERIA,
    DEFAULT_NETWORK_SPEC,
    DEFAULT_WITHSTAND_BANDS,
    FORWARD,
    REJECT,
    REVERSE,
    REVIEW,
    STRESS_INCOMPLETE,
    assess_blocking_diode_esd,
    build_step_ladder,
    discharge_pulse,
    esd_withstand_band,
    evaluate_step_observation,
    post_stress_parasitic_loss_w,
    screen_blocking_diode_esd,
    validate_discharge_network,
    validate_esd_criteria,
    validate_network_spec,
    validate_withstand_bands,
)

BASELINE = {"reverse_leakage_na": 50.0, "forward_voltage_v": 0.70}


def _spec(**overrides):
    record = copy.deepcopy(DEFAULT_NETWORK_SPEC)
    record.update(overrides)
    return record


def _criteria(**overrides):
    record = copy.deepcopy(DEFAULT_ESD_CRITERIA)
    record.update(overrides)
    return record


def _network(**overrides):
    record = {
        "capacitance_pf": 100.0,
        "series_resistance_ohm": 1500.0,
        "device_resistance_ohm": 500.0,
    }
    record.update(overrides)
    return record


def _plan(**overrides):
    record = {
        "start_volts": 250.0,
        "step_ratio": 2.0,
        "level_count": 4,
        "pulses_per_level": 3,
        "polarities": [FORWARD, REVERSE],
    }
    record.update(overrides)
    return record


def _observation(polarity, leakage_na=55.0, forward_v=0.70, catastrophic=False):
    return {
        "polarity": polarity,
        "reverse_leakage_na": leakage_na,
        "forward_voltage_v": forward_v,
        "catastrophic_failure": catastrophic,
    }


def _level(volts, plan, leakage_na=55.0, forward_v=0.70, pulses=None):
    count = plan["pulses_per_level"] if pulses is None else pulses
    observations = []
    for polarity in plan["polarities"]:
        for _ in range(count):
            observations.append(_observation(polarity, leakage_na, forward_v))
    return {"step_volts": volts, "observations": observations}


def _device(device_id="BD-001", plan=None, fail_from_index=None,
            handling_environment_v=250.0, pulses=None):
    plan = plan if plan is not None else _plan()
    ladder = build_step_ladder(plan)
    levels = []
    for index, volts in enumerate(ladder):
        failing = fail_from_index is not None and index >= fail_from_index
        levels.append(
            _level(
                volts,
                plan,
                leakage_na=400.0 if failing else 55.0,
                pulses=pulses,
            )
        )
    return {
        "device_id": device_id,
        "baseline": copy.deepcopy(BASELINE),
        "handling_environment_v": handling_environment_v,
        "levels": levels,
    }


def _lot(how_many, population=None, plan=None, fail_from_index=None):
    plan = plan if plan is not None else _plan()
    return {
        "lot_id": "BDL-12",
        "lot_population": population if population is not None else how_many,
        "devices": [
            _device("BD-%03d" % n, plan, fail_from_index)
            for n in range(1, how_many + 1)
        ],
    }


class NetworkSpecTests(unittest.TestCase):
    def test_the_default_spec_validates(self):
        self.assertIs(
            validate_network_spec(DEFAULT_NETWORK_SPEC), DEFAULT_NETWORK_SPEC
        )

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            validate_network_spec(100.0)

    def test_a_tolerance_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_network_spec(_spec(capacitance_tolerance_fraction=1.0))

    def test_a_non_positive_nominal_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_network_spec(_spec(nominal_capacitance_pf=0.0))

    def test_a_negative_resistance_tolerance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_network_spec(_spec(resistance_tolerance_fraction=-0.1))


class NetworkBandTests(unittest.TestCase):
    def test_a_nominal_bench_is_in_band(self):
        state = validate_discharge_network(_network())
        self.assertTrue(state["in_band"])
        self.assertEqual(state["findings"], [])
        self.assertAlmostEqual(state["total_resistance_ohm"], 2000.0, places=9)

    def test_capacitance_exactly_on_the_band_edge_is_in_band(self):
        state = validate_discharge_network(_network(capacitance_pf=110.0))
        self.assertTrue(state["in_band"])

    def test_capacitance_outside_the_band_is_reported(self):
        state = validate_discharge_network(_network(capacitance_pf=130.0))
        self.assertFalse(state["in_band"])
        self.assertEqual(len(state["findings"]), 1)

    def test_series_resistance_outside_the_band_is_reported(self):
        state = validate_discharge_network(_network(series_resistance_ohm=900.0))
        self.assertFalse(state["in_band"])

    def test_both_drifts_are_reported_together(self):
        state = validate_discharge_network(
            _network(capacitance_pf=40.0, series_resistance_ohm=900.0)
        )
        self.assertEqual(len(state["findings"]), 2)

    def test_a_zero_device_resistance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_discharge_network(_network(device_resistance_ohm=0.0))


class DischargePulseTests(unittest.TestCase):
    def test_the_peak_current_is_the_step_over_the_total_resistance(self):
        pulse = discharge_pulse(2000.0, _network())
        self.assertAlmostEqual(pulse["peak_current_a"], 1.0, places=9)

    def test_the_decay_constant_is_the_total_resistance_times_the_capacitance(self):
        pulse = discharge_pulse(1000.0, _network())
        self.assertAlmostEqual(pulse["decay_constant_s"], 2.0e-7, places=15)

    def test_the_transferred_charge_scales_with_the_step(self):
        low = discharge_pulse(500.0, _network())
        high = discharge_pulse(1000.0, _network())
        self.assertAlmostEqual(
            high["transferred_charge_c"], 2.0 * low["transferred_charge_c"], places=15
        )

    def test_the_stored_energy_goes_as_the_square_of_the_step(self):
        low = discharge_pulse(500.0, _network())
        high = discharge_pulse(1000.0, _network())
        self.assertAlmostEqual(
            high["stored_energy_j"], 4.0 * low["stored_energy_j"], places=15
        )

    def test_a_non_positive_step_voltage_is_refused(self):
        with self.assertRaises(ValueError):
            discharge_pulse(0.0, _network())

    def test_an_out_of_band_bench_is_flagged_on_the_pulse(self):
        pulse = discharge_pulse(1000.0, _network(capacitance_pf=200.0))
        self.assertFalse(pulse["network_in_band"])


class StepLadderTests(unittest.TestCase):
    def test_the_ladder_rises_by_the_declared_ratio(self):
        ladder = build_step_ladder(_plan())
        self.assertEqual(len(ladder), 4)
        self.assertAlmostEqual(ladder[0], 250.0, places=9)
        self.assertAlmostEqual(ladder[3], 2000.0, places=9)

    def test_a_ratio_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            build_step_ladder(_plan(step_ratio=1.0))

    def test_a_zero_level_count_is_refused(self):
        with self.assertRaises(ValueError):
            build_step_ladder(_plan(level_count=0))

    def test_a_zero_pulse_count_is_refused(self):
        with self.assertRaises(ValueError):
            build_step_ladder(_plan(pulses_per_level=0))

    def test_an_unknown_polarity_is_refused(self):
        with self.assertRaises(ValueError):
            build_step_ladder(_plan(polarities=["sideways"]))

    def test_a_repeated_polarity_is_refused(self):
        with self.assertRaises(ValueError):
            build_step_ladder(_plan(polarities=[FORWARD, FORWARD]))


class ParasiticLossTests(unittest.TestCase):
    def test_the_loss_scales_with_the_string_count(self):
        one = post_stress_parasitic_loss_w(100.0, 50.0, 1)
        ten = post_stress_parasitic_loss_w(100.0, 50.0, 10)
        self.assertAlmostEqual(ten, 10.0 * one, places=15)

    def test_no_leakage_costs_nothing(self):
        self.assertAlmostEqual(post_stress_parasitic_loss_w(0.0, 50.0, 8), 0.0, places=15)

    def test_a_negative_leakage_is_refused(self):
        with self.assertRaises(ValueError):
            post_stress_parasitic_loss_w(-1.0, 50.0, 8)

    def test_a_zero_string_count_is_refused(self):
        with self.assertRaises(ValueError):
            post_stress_parasitic_loss_w(100.0, 50.0, 0)


class ObservationTests(unittest.TestCase):
    def test_a_sound_reading_passes(self):
        result = evaluate_step_observation(_observation(REVERSE), BASELINE)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["leakage_ratio"], 1.1, places=9)

    def test_a_leakage_exactly_on_the_ceiling_still_passes(self):
        result = evaluate_step_observation(
            _observation(REVERSE, leakage_na=100.0), BASELINE
        )
        self.assertAlmostEqual(result["leakage_ratio"], 2.0, places=9)
        self.assertTrue(result["passed"])

    def test_a_leakage_past_the_ceiling_fails(self):
        result = evaluate_step_observation(
            _observation(REVERSE, leakage_na=200.0), BASELINE
        )
        self.assertFalse(result["passed"])

    def test_a_forward_drift_past_the_ceiling_fails(self):
        result = evaluate_step_observation(
            _observation(FORWARD, forward_v=0.90), BASELINE
        )
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["forward_drift_v"], 0.20, places=9)

    def test_a_catastrophic_failure_fails_whatever_the_drifts_read(self):
        result = evaluate_step_observation(
            _observation(REVERSE, catastrophic=True), BASELINE
        )
        self.assertFalse(result["passed"])

    def test_the_ratio_is_against_the_devices_own_baseline(self):
        hot = evaluate_step_observation(
            _observation(REVERSE, leakage_na=180.0),
            {"reverse_leakage_na": 150.0, "forward_voltage_v": 0.70},
        )
        self.assertTrue(hot["passed"])

    def test_an_unknown_observation_polarity_is_refused(self):
        with self.assertRaises(ValueError):
            evaluate_step_observation(_observation("sideways"), BASELINE)

    def test_a_zero_baseline_leakage_is_refused(self):
        with self.assertRaises(ValueError):
            evaluate_step_observation(
                _observation(REVERSE),
                {"reverse_leakage_na": 0.0, "forward_voltage_v": 0.70},
            )


class CriteriaAndBandTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_esd_criteria(DEFAULT_ESD_CRITERIA), DEFAULT_ESD_CRITERIA
        )

    def test_a_leakage_ceiling_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_esd_criteria(_criteria(max_leakage_ratio=0.5))

    def test_a_margin_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_esd_criteria(_criteria(required_withstand_margin=0.5))

    def test_a_zero_sample_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            validate_esd_criteria(_criteria(min_sample_fraction=0.0))

    def test_the_default_bands_validate(self):
        self.assertIs(
            validate_withstand_bands(DEFAULT_WITHSTAND_BANDS),
            DEFAULT_WITHSTAND_BANDS,
        )

    def test_bands_that_do_not_rise_are_refused(self):
        with self.assertRaises(ValueError):
            validate_withstand_bands((("none", 0.0), ("low", 500.0), ("mid", 400.0)))

    def test_bands_not_starting_at_zero_are_refused(self):
        with self.assertRaises(ValueError):
            validate_withstand_bands((("low", 250.0), ("mid", 500.0)))

    def test_a_withstand_on_a_band_floor_is_grouped_into_that_band(self):
        self.assertEqual(esd_withstand_band(500.0), "band-2")

    def test_a_withstand_below_every_floor_is_grouped_as_none(self):
        self.assertEqual(esd_withstand_band(0.0), "none")

    def test_a_withstand_above_the_top_floor_stays_in_the_top_band(self):
        self.assertEqual(esd_withstand_band(9000.0), "band-4")


class DeviceLadderTests(unittest.TestCase):
    def test_a_device_clearing_the_whole_ladder_is_accepted(self):
        result = assess_blocking_diode_esd(_device(), _plan(), _network())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["withstand_volts"], 2000.0, places=9)
        self.assertEqual(result["withstand_band"], "band-4")

    def test_the_withstand_is_the_last_level_before_the_first_failure(self):
        result = assess_blocking_diode_esd(
            _device(fail_from_index=2), _plan(), _network()
        )
        self.assertAlmostEqual(result["withstand_volts"], 500.0, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_device_failing_the_lowest_level_is_rejected(self):
        result = assess_blocking_diode_esd(
            _device(fail_from_index=0), _plan(), _network()
        )
        self.assertAlmostEqual(result["withstand_volts"], 0.0, places=9)
        self.assertEqual(result["verdict"], REJECT)

    def test_a_withstand_under_the_handling_environment_is_rejected(self):
        result = assess_blocking_diode_esd(
            _device(fail_from_index=1, handling_environment_v=1000.0),
            _plan(),
            _network(),
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_withstand_clearing_the_environment_but_not_the_margin_is_reviewed(self):
        result = assess_blocking_diode_esd(
            _device(fail_from_index=2, handling_environment_v=500.0),
            _plan(),
            _network(),
        )
        self.assertAlmostEqual(result["withstand_volts"], 500.0, places=9)
        self.assertEqual(result["verdict"], REVIEW)

    def test_a_pass_above_an_earlier_failure_is_not_credited(self):
        plan = _plan()
        device = _device(plan=plan, fail_from_index=1)
        device["levels"][3] = _level(build_step_ladder(plan)[3], plan, leakage_na=55.0)
        result = assess_blocking_diode_esd(device, plan, _network())
        self.assertTrue(result["inconsistent_ladder"])
        self.assertAlmostEqual(result["withstand_volts"], 250.0, places=9)

    def test_a_missing_ladder_level_leaves_the_device_open(self):
        plan = _plan()
        device = _device(plan=plan)
        del device["levels"][2]
        result = assess_blocking_diode_esd(device, plan, _network())
        self.assertEqual(result["verdict"], STRESS_INCOMPLETE)
        self.assertEqual(result["incomplete_level_count"], 1)

    def test_a_level_short_of_its_planned_pulses_is_not_credited(self):
        plan = _plan()
        device = _device(plan=plan, pulses=1)
        result = assess_blocking_diode_esd(device, plan, _network())
        self.assertEqual(result["verdict"], STRESS_INCOMPLETE)

    def test_an_out_of_band_bench_leaves_the_device_open(self):
        result = assess_blocking_diode_esd(
            _device(), _plan(), _network(capacitance_pf=300.0)
        )
        self.assertEqual(result["verdict"], STRESS_INCOMPLETE)
        self.assertTrue(result["findings"])

    def test_two_records_for_one_level_are_refused(self):
        plan = _plan()
        device = _device(plan=plan)
        device["levels"].append(_level(build_step_ladder(plan)[0], plan))
        with self.assertRaises(ValueError):
            assess_blocking_diode_esd(device, plan, _network())

    def test_a_device_without_a_levels_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_esd(
                {"device_id": "BD-9", "baseline": BASELINE, "levels": "none"},
                _plan(),
                _network(),
            )

    def test_the_worst_leakage_ratio_is_carried_on_the_record(self):
        result = assess_blocking_diode_esd(
            _device(fail_from_index=3), _plan(), _network()
        )
        self.assertAlmostEqual(result["worst_leakage_ratio"], 8.0, places=9)


class LotScreenTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        result = screen_blocking_diode_esd(_lot(10), _plan(), _network())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["stressed_count"], 10)
        self.assertEqual(result["lot_withstand_band"], "band-4")

    def test_a_sample_too_thin_is_referred_to_review(self):
        result = screen_blocking_diode_esd(
            _lot(5, population=200), _plan(), _network()
        )
        self.assertEqual(result["verdict"], REVIEW)
        self.assertAlmostEqual(result["sample_fraction"], 0.025, places=9)

    def test_a_sample_exactly_on_the_floor_is_accepted(self):
        result = screen_blocking_diode_esd(
            _lot(10, population=100), _plan(), _network()
        )
        self.assertAlmostEqual(result["sample_fraction"], 0.10, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_lot_with_a_rejected_device_is_rejected(self):
        lot = _lot(10)
        lot["devices"][4] = _device("BD-005", _plan(), fail_from_index=0)
        result = screen_blocking_diode_esd(lot, _plan(), _network())
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(result["lowest_withstand_volts"], 0.0, places=9)

    def test_more_stressed_devices_than_the_population_is_refused(self):
        with self.assertRaises(ValueError):
            screen_blocking_diode_esd(_lot(10, population=4), _plan(), _network())

    def test_a_duplicate_device_id_is_refused(self):
        lot = _lot(3)
        lot["devices"][2]["device_id"] = "BD-001"
        with self.assertRaises(ValueError):
            screen_blocking_diode_esd(lot, _plan(), _network())

    def test_a_non_integer_population_is_refused(self):
        lot = _lot(3)
        lot["lot_population"] = "many"
        with self.assertRaises(ValueError):
            screen_blocking_diode_esd(lot, _plan(), _network())

    def test_an_open_device_keeps_the_lot_open(self):
        lot = _lot(6)
        del lot["devices"][2]["levels"][1]
        result = screen_blocking_diode_esd(lot, _plan(), _network())
        self.assertEqual(result["verdict"], STRESS_INCOMPLETE)
        self.assertEqual(result["open_device_ids"], ["BD-003"])

    def test_the_report_carries_the_lot_it_answered_to(self):
        result = screen_blocking_diode_esd(_lot(8, population=40), _plan(), _network())
        self.assertEqual(result["lot_id"], "BDL-12")
        self.assertEqual(result["lot_population"], 40)
        self.assertEqual(result["counts"][ACCEPT], 8)


if __name__ == "__main__":
    unittest.main()
