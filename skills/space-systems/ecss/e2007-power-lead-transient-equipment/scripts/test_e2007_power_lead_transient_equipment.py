#!/usr/bin/env python3
"""Gate 3 contract test for e2007-power-lead-transient-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_power_lead_transient_equipment.py
"""

import copy
import unittest

from e2007_power_lead_transient_equipment_logic import (
    FITNESS_ADEQUATE,
    FITNESS_INADEQUATE,
    FITNESS_MARGINAL,
    ITEM_COUPLING,
    ITEM_DECOUPLING,
    ITEM_GENERATOR,
    ITEM_OSCILLOSCOPE,
    ITEM_VOLTAGE_PROBE,
    REQUIRED_ITEMS,
    SENSE_CEILING,
    SENSE_FLOOR,
    VERDICT_FIT,
    VERDICT_UNFIT,
    assess_transient_bench,
    categorize_capability,
    chain_bandwidth_hz,
    chain_rise_time_ceiling_s,
    coupling_impedance_ceiling_ohm,
    decoupling_impedance_floor_ohm,
    delivered_energy_j,
    derive_requirements,
    generator_open_circuit_v,
    generator_rise_time_ceiling_s,
    normalize_inventory,
    probe_rating_v,
    record_depth_samples,
    repetition_interval_floor_s,
    sample_rate_hz,
    shortfall_factor,
    terminal_amplitude_v,
)


def pulse(**over):
    record = {
        "terminal_v": 200.0,
        "rise_time_s": 1.0e-6,
        "width_s": 50.0e-6,
        "window_s": 500.0e-6,
        "source_impedance_ohm": 50.0,
        "load_impedance_ohm": 50.0,
        "eut_impedance_ohm": 5.0,
        "allowed_diversion_fraction": 0.1,
        "allowed_coupling_loss_fraction": 0.1,
        "duty_fraction": 0.01,
    }
    record.update(over)
    return record


def bench():
    return [
        {
            "item": ITEM_GENERATOR,
            "open_circuit_v": 600.0,
            "rise_time_s": 0.5e-6,
            "repetition_interval_s": 10.0e-3,
        },
        {"item": ITEM_COUPLING, "series_impedance_ohm": 2.0},
        {"item": ITEM_DECOUPLING, "impedance_ohm": 100.0},
        {
            "item": ITEM_OSCILLOSCOPE,
            "bandwidth_hz": 100.0e6,
            "sample_rate_hz": 1.0e9,
            "record_depth_samples": 1.0e6,
        },
        {"item": ITEM_VOLTAGE_PROBE, "rating_v": 1000.0, "rise_time_s": 1.0e-9},
    ]


def bench_with(item, **over):
    declared = copy.deepcopy(bench())
    for record in declared:
        if record["item"] == item:
            record.update(over)
    return declared


class TestGeneratorDivider(unittest.TestCase):
    def test_matched_impedances_double_the_open_circuit_setting(self):
        self.assertAlmostEqual(generator_open_circuit_v(200.0, 50.0, 50.0), 400.0, places=9)

    def test_a_stiff_source_needs_almost_no_uplift(self):
        self.assertAlmostEqual(
            generator_open_circuit_v(200.0, 0.0, 50.0), 200.0, places=9
        )

    def test_divider_round_trips_to_the_terminal_amplitude(self):
        open_circuit = generator_open_circuit_v(200.0, 50.0, 25.0)
        self.assertAlmostEqual(
            terminal_amplitude_v(open_circuit, 50.0, 25.0), 200.0, places=9
        )

    def test_negative_source_impedance_rejected(self):
        with self.assertRaises(ValueError):
            generator_open_circuit_v(200.0, -1.0, 50.0)

    def test_zero_load_impedance_rejected(self):
        with self.assertRaises(ValueError):
            generator_open_circuit_v(200.0, 50.0, 0.0)


class TestEdgeRequirements(unittest.TestCase):
    def test_generator_edge_ceiling_is_the_specified_edge(self):
        self.assertAlmostEqual(
            generator_rise_time_ceiling_s(1.0e-6), 1.0e-6, places=12
        )

    def test_generator_edge_ceiling_admits_a_stated_tolerance(self):
        self.assertAlmostEqual(
            generator_rise_time_ceiling_s(1.0e-6, 0.2), 1.2e-6, places=12
        )

    def test_chain_must_be_several_times_faster_than_the_pulse(self):
        self.assertAlmostEqual(chain_rise_time_ceiling_s(1.0e-6, 5.0), 2.0e-7, places=15)

    def test_chain_speed_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            chain_rise_time_ceiling_s(1.0e-6, 0.5)

    def test_bandwidth_follows_the_rise_time_bandwidth_product(self):
        self.assertAlmostEqual(chain_bandwidth_hz(2.0e-7), 1.75e6, places=3)

    def test_zero_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            chain_bandwidth_hz(0.0)


class TestRecordingRequirements(unittest.TestCase):
    def test_sample_rate_oversamples_the_bandwidth(self):
        self.assertAlmostEqual(sample_rate_hz(1.75e6, 5.0), 8.75e6, places=3)

    def test_oversampling_below_one_rejected(self):
        with self.assertRaises(ValueError):
            sample_rate_hz(1.75e6, 0.5)

    def test_record_depth_is_a_whole_number_of_samples(self):
        self.assertEqual(record_depth_samples(0.5, 1024.0), 512)

    def test_partial_sample_rounds_up(self):
        self.assertEqual(record_depth_samples(0.5, 1025.0), 513)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            record_depth_samples(0.0, 1024.0)


class TestIsolationRequirements(unittest.TestCase):
    def test_decoupling_floor_rises_as_the_allowed_diversion_falls(self):
        loose = decoupling_impedance_floor_ohm(5.0, 0.5)
        tight = decoupling_impedance_floor_ohm(5.0, 0.05)
        self.assertGreater(tight, loose)

    def test_decoupling_floor_for_a_tenth_diversion(self):
        self.assertAlmostEqual(decoupling_impedance_floor_ohm(5.0, 0.1), 45.0, places=9)

    def test_diversion_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            decoupling_impedance_floor_ohm(5.0, 1.0)

    def test_coupling_ceiling_for_a_tenth_loss(self):
        self.assertAlmostEqual(
            coupling_impedance_ceiling_ohm(50.0, 0.1), 50.0 / 9.0, places=9
        )

    def test_coupling_ceiling_rises_as_more_loss_is_allowed(self):
        self.assertGreater(
            coupling_impedance_ceiling_ohm(50.0, 0.3),
            coupling_impedance_ceiling_ohm(50.0, 0.1),
        )


class TestSupportingQuantities(unittest.TestCase):
    def test_probe_rating_carries_headroom(self):
        self.assertAlmostEqual(probe_rating_v(200.0, 1.5), 300.0, places=9)

    def test_probe_headroom_below_one_rejected(self):
        with self.assertRaises(ValueError):
            probe_rating_v(200.0, 0.9)

    def test_repetition_interval_follows_the_duty(self):
        self.assertAlmostEqual(repetition_interval_floor_s(50.0e-6, 0.01), 5.0e-3, places=12)

    def test_duty_fraction_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            repetition_interval_floor_s(50.0e-6, 0.0)

    def test_delivered_energy_scales_with_the_square_of_amplitude(self):
        single = delivered_energy_j(200.0, 50.0, 50.0e-6)
        double = delivered_energy_j(400.0, 50.0, 50.0e-6)
        self.assertAlmostEqual(double / single, 4.0, places=9)

    def test_delivered_energy_value(self):
        self.assertAlmostEqual(delivered_energy_j(200.0, 50.0, 50.0e-6), 0.04, places=12)


class TestCategorization(unittest.TestCase):
    def test_floor_met_with_room_is_adequate(self):
        self.assertEqual(
            categorize_capability(100.0, 50.0, SENSE_FLOOR), FITNESS_ADEQUATE
        )

    def test_floor_met_exactly_is_marginal(self):
        self.assertEqual(
            categorize_capability(50.0, 50.0, SENSE_FLOOR), FITNESS_MARGINAL
        )

    def test_floor_missed_is_inadequate(self):
        self.assertEqual(
            categorize_capability(40.0, 50.0, SENSE_FLOOR), FITNESS_INADEQUATE
        )

    def test_ceiling_met_with_room_is_adequate(self):
        self.assertEqual(
            categorize_capability(10.0, 50.0, SENSE_CEILING), FITNESS_ADEQUATE
        )

    def test_ceiling_met_exactly_is_marginal(self):
        self.assertEqual(
            categorize_capability(50.0, 50.0, SENSE_CEILING), FITNESS_MARGINAL
        )

    def test_ceiling_exceeded_is_inadequate(self):
        self.assertEqual(
            categorize_capability(60.0, 50.0, SENSE_CEILING), FITNESS_INADEQUATE
        )

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            categorize_capability(50.0, 50.0, "either-way")

    def test_shortfall_factor_of_a_met_floor_is_one(self):
        self.assertAlmostEqual(shortfall_factor(100.0, 50.0, SENSE_FLOOR), 1.0, places=12)

    def test_shortfall_factor_of_a_missed_floor(self):
        self.assertAlmostEqual(shortfall_factor(10.0, 50.0, SENSE_FLOOR), 5.0, places=12)

    def test_shortfall_factor_of_an_exceeded_ceiling(self):
        self.assertAlmostEqual(
            shortfall_factor(150.0, 50.0, SENSE_CEILING), 3.0, places=12
        )


class TestInventory(unittest.TestCase):
    def test_every_required_item_normalizes(self):
        declared = normalize_inventory(bench())
        self.assertEqual(sorted(declared), sorted(REQUIRED_ITEMS))

    def test_unrecognized_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_inventory(bench() + [{"item": "antenna-mast"}])

    def test_duplicate_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_inventory(bench() + [{"item": ITEM_DECOUPLING, "impedance_ohm": 1.0}])

    def test_item_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_inventory([{"impedance_ohm": 1.0}])

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_inventory(["transient-generator"])


class TestRequirementDerivation(unittest.TestCase):
    def test_requirements_are_derived_from_the_pulse(self):
        req = derive_requirements(pulse())
        self.assertAlmostEqual(req["open_circuit_v"], 400.0, places=9)
        self.assertAlmostEqual(req["decoupling_impedance_floor_ohm"], 45.0, places=9)
        self.assertAlmostEqual(req["bandwidth_hz"], 1.75e6, places=3)
        self.assertAlmostEqual(req["sample_rate_hz"], 8.75e6, places=3)
        self.assertEqual(req["record_depth_samples"], 4375)
        self.assertAlmostEqual(req["probe_rating_v"], 300.0, places=9)

    def test_a_width_shorter_than_the_edge_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements(pulse(width_s=0.5e-6))

    def test_a_window_shorter_than_the_pulse_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements(pulse(window_s=1.0e-6))

    def test_missing_pulse_field_rejected(self):
        broken = pulse()
        del broken["duty_fraction"]
        with self.assertRaises(ValueError):
            derive_requirements(broken)

    def test_non_mapping_pulse_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements([200.0])


class TestBenchAssessment(unittest.TestCase):
    def test_a_capable_bench_is_fit(self):
        report = assess_transient_bench(pulse(), bench())
        self.assertEqual(report["verdict"], VERDICT_FIT)
        self.assertEqual(report["findings"], [])
        self.assertIsNone(report["governing_shortfall"])

    def test_every_check_is_reported(self):
        report = assess_transient_bench(pulse(), bench())
        self.assertEqual(len(report["checks"]), 10)
        self.assertTrue(
            all(c["fitness"] == FITNESS_ADEQUATE for c in report["checks"])
        )

    def test_a_generator_that_cannot_reach_the_amplitude_is_a_finding(self):
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_GENERATOR, open_circuit_v=250.0)
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertTrue(any("open_circuit_v" in f for f in report["findings"]))

    def test_a_slow_generator_edge_is_a_finding(self):
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_GENERATOR, rise_time_s=5.0e-6)
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_a_decoupling_sitting_on_its_floor_is_a_limitation(self):
        floor = decoupling_impedance_floor_ohm(5.0, 0.1)
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_DECOUPLING, impedance_ohm=floor)
        )
        self.assertEqual(report["verdict"], VERDICT_FIT)
        self.assertTrue(any("decoupling-network" in l for l in report["limitations"]))

    def test_the_largest_shortfall_governs_not_the_first_listed(self):
        declared = bench_with(ITEM_OSCILLOSCOPE, bandwidth_hz=1.0e6)
        for record in declared:
            if record["item"] == ITEM_DECOUPLING:
                record["impedance_ohm"] = 4.5
        report = assess_transient_bench(pulse(), declared)
        self.assertEqual(report["governing_shortfall"]["item"], ITEM_DECOUPLING)
        self.assertAlmostEqual(
            report["governing_shortfall"]["shortfall_factor"], 10.0, places=9
        )

    def test_a_missing_item_is_a_finding(self):
        declared = [r for r in bench() if r["item"] != ITEM_VOLTAGE_PROBE]
        report = assess_transient_bench(pulse(), declared)
        self.assertEqual(report["missing_items"], [ITEM_VOLTAGE_PROBE])
        self.assertTrue(any("never declared" in f for f in report["findings"]))

    def test_a_declared_item_missing_a_quantity_is_a_finding(self):
        declared = copy.deepcopy(bench())
        for record in declared:
            if record["item"] == ITEM_OSCILLOSCOPE:
                del record["record_depth_samples"]
        report = assess_transient_bench(pulse(), declared)
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertTrue(any("declares no" in f for f in report["findings"]))

    def test_a_shallow_memory_is_a_finding(self):
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_OSCILLOSCOPE, record_depth_samples=1000.0)
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertTrue(any("record_depth_samples" in f for f in report["findings"]))

    def test_a_coupling_path_that_eats_the_pulse_is_a_finding(self):
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_COUPLING, series_impedance_ohm=40.0)
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_a_probe_slower_than_the_chain_is_a_finding(self):
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_VOLTAGE_PROBE, rise_time_s=1.0e-6)
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_a_short_repetition_interval_is_a_finding(self):
        report = assess_transient_bench(
            pulse(), bench_with(ITEM_GENERATOR, repetition_interval_s=1.0e-4)
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)


if __name__ == "__main__":
    unittest.main()
