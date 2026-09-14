#!/usr/bin/env python3
"""Contract test for the measurement equipment set-up leaf (offline)."""

import copy
import unittest

from e2008_measurement_equipment_set_up_logic import (
    BIAS_SUPPLY,
    CONNECTION_SEQUENCE,
    EXCITATION_SOURCE,
    GUARDED_FIXTURE,
    MAX_BIAS_RESOLUTION_FRACTION,
    MAX_FIXTURE_STRAY_FRACTION,
    MAX_QUANTISATION_FRACTION,
    MAX_TEMPERATURE_DEVIATION_K,
    MIN_SAMPLES_PER_TRANSIENT,
    REFERENCE_TEMPERATURE_K,
    REQUIRED_STATIONS,
    SETUP_NOT_READY,
    SETUP_READY,
    SHIELD_AND_GROUND,
    TEMPERATURE_STAGE,
    TRANSIENT_RECORDER,
    assess_equipment_setup,
    bias_resolution_fraction,
    bias_supply_covers,
    bias_supply_span_v,
    calibration_valid,
    fixture_stray_fraction,
    missing_stations,
    overdue_calibrations,
    quantisation_fraction,
    quantisation_step_v,
    samples_per_transient,
    sequence_findings,
    setup_sequence,
    temperature_deviation_k,
    validate_chain,
)

CELL_CAPACITANCE_F = 2.0e-8
TRANSIENT_S = 1.0e-5

BASE_CHAIN = {
    BIAS_SUPPLY: {
        "minimum_v": -5.0,
        "maximum_v": 1.0,
        "resolution_v": 0.001,
        "days_since_calibration": 120.0,
        "calibration_interval_days": 365.0,
    },
    EXCITATION_SOURCE: {
        "days_since_calibration": 90.0,
        "calibration_interval_days": 365.0,
    },
    GUARDED_FIXTURE: {
        "stray_capacitance_f": 2.0e-10,
        "four_terminal": True,
        "compensation_run": True,
    },
    TRANSIENT_RECORDER: {
        "sample_rate_hz": 1.0e7,
        "full_scale_v": 1.0,
        "resolution_bits": 14,
        "days_since_calibration": 200.0,
        "calibration_interval_days": 365.0,
    },
    SHIELD_AND_GROUND: {"single_point": True},
    TEMPERATURE_STAGE: {
        "setpoint_k": REFERENCE_TEMPERATURE_K,
        "days_since_calibration": 30.0,
        "calibration_interval_days": 365.0,
    },
}

BASE_CASE = {
    "chain": BASE_CHAIN,
    "required_bias_span_v": 5.0,
    "smallest_bias_step_v": 0.05,
    "cell_capacitance_f": CELL_CAPACITANCE_F,
    "transient_duration_s": TRANSIENT_S,
    "expected_signal_v": 0.5,
    "proposed_order": list(CONNECTION_SEQUENCE),
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


def _chain(station, **settings):
    chain = copy.deepcopy(BASE_CHAIN)
    chain[station].update(settings)
    return chain


class ChainValidationTests(unittest.TestCase):
    def test_a_complete_chain_is_missing_no_station(self):
        self.assertEqual(missing_stations(BASE_CHAIN), ())

    def test_a_dropped_station_is_named(self):
        chain = copy.deepcopy(BASE_CHAIN)
        del chain[TEMPERATURE_STAGE]
        self.assertEqual(missing_stations(chain), (TEMPERATURE_STAGE,))

    def test_an_invented_station_is_refused(self):
        with self.assertRaises(ValueError):
            validate_chain({"spectrum-analyser": {}})

    def test_a_station_without_settings_is_refused(self):
        with self.assertRaises(ValueError):
            validate_chain({BIAS_SUPPLY: "minus five to one volt"})

    def test_an_empty_chain_is_refused(self):
        with self.assertRaises(ValueError):
            validate_chain({})

    def test_every_required_station_appears_once(self):
        self.assertEqual(len(REQUIRED_STATIONS), len(set(REQUIRED_STATIONS)))


class BiasSupplyTests(unittest.TestCase):
    def test_the_span_is_the_distance_between_the_supply_limits(self):
        self.assertAlmostEqual(
            bias_supply_span_v(BASE_CHAIN[BIAS_SUPPLY]), 6.0, places=12
        )

    def test_an_inverted_supply_range_is_refused(self):
        with self.assertRaises(ValueError):
            bias_supply_span_v({"minimum_v": 1.0, "maximum_v": -5.0})

    def test_a_supply_reaching_exactly_the_required_span_covers_it(self):
        settings = {"minimum_v": -4.0, "maximum_v": 1.0, "resolution_v": 0.001}
        self.assertTrue(bias_supply_covers(settings, 5.0))

    def test_a_supply_short_of_the_required_span_does_not_cover_it(self):
        settings = {"minimum_v": -1.0, "maximum_v": 1.0, "resolution_v": 0.001}
        self.assertFalse(bias_supply_covers(settings, 5.0))

    def test_the_resolution_is_read_against_the_smallest_bias_step(self):
        self.assertAlmostEqual(
            bias_resolution_fraction(BASE_CHAIN[BIAS_SUPPLY], 0.05), 0.02, places=9
        )

    def test_a_zero_bias_step_cannot_scale_the_resolution(self):
        with self.assertRaises(ValueError):
            bias_resolution_fraction(BASE_CHAIN[BIAS_SUPPLY], 0.0)


class RecorderTests(unittest.TestCase):
    def test_the_sample_count_is_the_rate_across_the_response(self):
        self.assertAlmostEqual(
            samples_per_transient(1.0e7, TRANSIENT_S), 100.0, places=6
        )

    def test_a_zero_sample_rate_is_refused(self):
        with self.assertRaises(ValueError):
            samples_per_transient(0.0, TRANSIENT_S)

    def test_one_bit_halves_with_every_added_bit(self):
        self.assertAlmostEqual(
            quantisation_step_v(1.0, 8) / quantisation_step_v(1.0, 9), 2.0, places=12
        )

    def test_a_fractional_bit_count_is_refused(self):
        with self.assertRaises(ValueError):
            quantisation_step_v(1.0, 12.5)

    def test_a_bit_count_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            quantisation_step_v(1.0, 0)

    def test_the_bit_is_expressed_against_the_expected_signal(self):
        self.assertAlmostEqual(
            quantisation_fraction(1.0, 10, 0.5), (1.0 / 1024.0) / 0.5, places=12
        )


class FixtureAndEnvironmentTests(unittest.TestCase):
    def test_the_stray_share_is_the_fixture_over_the_cell(self):
        self.assertAlmostEqual(
            fixture_stray_fraction(2.0e-10, CELL_CAPACITANCE_F), 0.01, places=12
        )

    def test_a_zero_cell_capacitance_carries_no_stray_share(self):
        with self.assertRaises(ValueError):
            fixture_stray_fraction(2.0e-10, 0.0)

    def test_a_stage_at_the_reference_temperature_has_no_deviation(self):
        self.assertAlmostEqual(
            temperature_deviation_k(REFERENCE_TEMPERATURE_K), 0.0, places=12
        )

    def test_the_deviation_ignores_which_side_of_the_reference_it_sits(self):
        self.assertAlmostEqual(
            temperature_deviation_k(REFERENCE_TEMPERATURE_K + 3.0),
            temperature_deviation_k(REFERENCE_TEMPERATURE_K - 3.0),
            places=9,
        )

    def test_an_instrument_on_its_interval_day_is_still_valid(self):
        self.assertTrue(calibration_valid(365.0, 365.0))

    def test_an_instrument_past_its_interval_is_not_valid(self):
        self.assertFalse(calibration_valid(400.0, 365.0))

    def test_an_overdue_station_is_named(self):
        chain = _chain(TRANSIENT_RECORDER, days_since_calibration=400.0)
        self.assertEqual(overdue_calibrations(chain), (TRANSIENT_RECORDER,))


class SequenceTests(unittest.TestCase):
    def test_the_canonical_order_bonds_ground_first_and_powers_last(self):
        sequence = setup_sequence()
        self.assertEqual(sequence[0], "bond-the-shield-and-ground")
        self.assertEqual(sequence[-1], "energise-the-bias-supply")

    def test_the_canonical_order_produces_no_findings(self):
        self.assertEqual(sequence_findings(list(CONNECTION_SEQUENCE)), ())

    def test_an_omitted_step_is_reported(self):
        proposed = [
            step
            for step in CONNECTION_SEQUENCE
            if step != "run-open-and-short-compensation"
        ]
        findings = sequence_findings(proposed)
        self.assertEqual(len(findings), 1)
        self.assertIn("omits", findings[0])

    def test_grounding_after_the_fixture_is_reported(self):
        proposed = list(CONNECTION_SEQUENCE)
        proposed[0], proposed[1] = proposed[1], proposed[0]
        findings = sequence_findings(proposed)
        self.assertTrue(any("ground is not bonded first" in f for f in findings))

    def test_energising_before_the_chain_is_complete_is_reported(self):
        proposed = list(CONNECTION_SEQUENCE)
        proposed[-1], proposed[-2] = proposed[-2], proposed[-1]
        findings = sequence_findings(proposed)
        self.assertTrue(any("energised before" in f for f in findings))

    def test_an_invented_step_is_refused(self):
        with self.assertRaises(ValueError):
            sequence_findings(["polish-the-coverglass"])

    def test_a_repeated_step_is_refused(self):
        with self.assertRaises(ValueError):
            sequence_findings(list(CONNECTION_SEQUENCE) + [CONNECTION_SEQUENCE[0]])


class ReadinessTests(unittest.TestCase):
    def test_a_complete_arrangement_is_ready(self):
        result = assess_equipment_setup(BASE_CASE)
        self.assertEqual(result["verdict"], SETUP_READY)
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing_stations"], ())

    def test_a_missing_station_stops_the_arrangement(self):
        chain = copy.deepcopy(BASE_CHAIN)
        del chain[SHIELD_AND_GROUND]
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertTrue(any("incomplete without" in f for f in result["findings"]))

    def test_a_supply_that_cannot_reach_the_sweep_is_a_finding(self):
        chain = _chain(BIAS_SUPPLY, minimum_v=-1.0, maximum_v=1.0)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertTrue(any("bias supply spans" in f for f in result["findings"]))

    def test_a_coarse_bias_resolution_is_a_finding(self):
        chain = _chain(BIAS_SUPPLY, resolution_v=0.02)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertGreater(
            result["detail"]["bias_resolution_fraction"], MAX_BIAS_RESOLUTION_FRACTION
        )

    def test_a_slow_recorder_cannot_reconstruct_the_response(self):
        chain = _chain(TRANSIENT_RECORDER, sample_rate_hz=1.0e6)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertTrue(any("samples in the response" in f for f in result["findings"]))

    def test_a_sample_count_landing_exactly_on_the_floor_is_accepted(self):
        chain = _chain(
            TRANSIENT_RECORDER,
            sample_rate_hz=MIN_SAMPLES_PER_TRANSIENT / TRANSIENT_S,
        )
        result = assess_equipment_setup(_case(chain=chain))
        self.assertAlmostEqual(
            result["detail"]["samples_per_transient"],
            MIN_SAMPLES_PER_TRANSIENT,
            places=9,
        )
        self.assertEqual(result["verdict"], SETUP_READY)

    def test_a_coarse_vertical_scale_is_a_finding(self):
        chain = _chain(TRANSIENT_RECORDER, resolution_bits=6)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertGreater(
            result["detail"]["quantisation_fraction"], MAX_QUANTISATION_FRACTION
        )

    def test_a_dominant_fixture_stray_is_a_finding(self):
        chain = _chain(GUARDED_FIXTURE, stray_capacitance_f=2.0e-9)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertTrue(any("fixture stray" in f for f in result["findings"]))

    def test_a_stray_landing_exactly_on_the_ceiling_is_accepted(self):
        chain = _chain(
            GUARDED_FIXTURE,
            stray_capacitance_f=MAX_FIXTURE_STRAY_FRACTION * CELL_CAPACITANCE_F,
        )
        result = assess_equipment_setup(_case(chain=chain))
        self.assertAlmostEqual(
            result["detail"]["fixture_stray_fraction"],
            MAX_FIXTURE_STRAY_FRACTION,
            places=9,
        )
        self.assertEqual(result["verdict"], SETUP_READY)

    def test_a_two_terminal_fixture_is_a_finding(self):
        chain = _chain(GUARDED_FIXTURE, four_terminal=False)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertTrue(any("four-terminal" in f for f in result["findings"]))

    def test_uncompensated_fixture_is_a_finding(self):
        chain = _chain(GUARDED_FIXTURE, compensation_run=False)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertTrue(any("compensation" in f for f in result["findings"]))

    def test_a_ground_loop_is_a_finding(self):
        chain = _chain(SHIELD_AND_GROUND, single_point=False)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertFalse(result["detail"]["single_point_ground"])

    def test_a_stage_off_the_reference_temperature_is_a_finding(self):
        chain = _chain(TEMPERATURE_STAGE, setpoint_k=REFERENCE_TEMPERATURE_K + 7.0)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertTrue(any("reference temperature" in f for f in result["findings"]))

    def test_a_stage_on_the_edge_of_the_band_is_accepted(self):
        chain = _chain(
            TEMPERATURE_STAGE,
            setpoint_k=REFERENCE_TEMPERATURE_K + MAX_TEMPERATURE_DEVIATION_K,
        )
        result = assess_equipment_setup(_case(chain=chain))
        self.assertAlmostEqual(
            result["detail"]["temperature_deviation_k"],
            MAX_TEMPERATURE_DEVIATION_K,
            places=9,
        )
        self.assertEqual(result["verdict"], SETUP_READY)

    def test_an_overdue_instrument_stops_the_arrangement(self):
        chain = _chain(BIAS_SUPPLY, days_since_calibration=400.0)
        result = assess_equipment_setup(_case(chain=chain))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertEqual(result["overdue_calibrations"], (BIAS_SUPPLY,))

    def test_an_out_of_order_assembly_is_carried_into_the_verdict(self):
        proposed = list(CONNECTION_SEQUENCE)
        proposed[0], proposed[1] = proposed[1], proposed[0]
        result = assess_equipment_setup(_case(proposed_order=proposed))
        self.assertEqual(result["verdict"], SETUP_NOT_READY)
        self.assertTrue(result["sequence_findings"])

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_equipment_setup("bias-supply")

    def test_a_missing_cell_capacitance_stops_the_arrangement(self):
        case = _case()
        del case["cell_capacitance_f"]
        with self.assertRaises(ValueError):
            assess_equipment_setup(case)


if __name__ == "__main__":
    unittest.main()
