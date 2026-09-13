#!/usr/bin/env python3
"""Contract test for the solar cell assembly cycling process (offline).

This is the gate 3 behaviour contract. Every workflow step of the leaf is
exercised: the control drawing validation, the acceptance bands it fixes,
the disposition of a single recorded cycle, the run reconciliation, and
the verdict a test review reads.
"""

import copy
import unittest

from e2008_sca_thermal_cycling_process_logic import (
    CYCLE_COLD_DWELL_SHORT,
    CYCLE_COLD_NOT_REACHED,
    CYCLE_CREDITED,
    CYCLE_HOT_DWELL_SHORT,
    CYCLE_HOT_NOT_REACHED,
    CYCLE_OVERSTRESS,
    RUN_MEETS_CONTROL_DRAWING,
    RUN_OUTSIDE_DRAWING_EXTREMES,
    RUN_SHORT_OF_DRAWING_CYCLES,
    assess_sca_thermal_cycling_process,
    audit_cycling_run,
    cycle_disposition,
    drawing_temperature_bands,
    validate_control_drawing,
)

DRAWING = {
    "drawing_number": "SCA-PV-4471",
    "issue": "C",
    "cycle_count": 4,
    "hot_extreme_c": 100.0,
    "cold_extreme_c": -140.0,
    "dwell_minutes": 5.0,
    "tolerance_k": 5.0,
}

GOOD_CYCLE = {
    "peak_hot_c": 101.0,
    "peak_cold_c": -141.0,
    "hot_dwell_minutes": 6.0,
    "cold_dwell_minutes": 6.0,
}


def _cycles(count, **overrides):
    run = []
    for _ in range(count):
        cycle = dict(GOOD_CYCLE)
        cycle.update(overrides)
        run.append(cycle)
    return run


class DrawingTests(unittest.TestCase):
    def test_a_complete_drawing_validates(self):
        record = validate_control_drawing(DRAWING)
        self.assertEqual(record["drawing_number"], "SCA-PV-4471")
        self.assertEqual(record["cycle_count"], 4)

    def test_a_missing_cycle_count_is_not_a_default(self):
        broken = copy.deepcopy(DRAWING)
        del broken["cycle_count"]
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_a_missing_issue_is_rejected(self):
        broken = copy.deepcopy(DRAWING)
        del broken["issue"]
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_a_blank_drawing_number_is_rejected(self):
        broken = dict(DRAWING, drawing_number="   ")
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_a_fractional_cycle_count_is_rejected(self):
        broken = dict(DRAWING, cycle_count=4.5)
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_a_zero_cycle_count_is_rejected(self):
        broken = dict(DRAWING, cycle_count=0)
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_inverted_extremes_are_rejected(self):
        broken = dict(DRAWING, hot_extreme_c=-140.0, cold_extreme_c=100.0)
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_a_tolerance_that_merges_the_bands_is_rejected(self):
        broken = dict(DRAWING, tolerance_k=200.0)
        with self.assertRaises(ValueError):
            validate_control_drawing(broken)

    def test_a_non_mapping_drawing_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_drawing("SCA-PV-4471 issue C")


class BandTests(unittest.TestCase):
    def test_bands_sit_symmetrically_about_each_extreme(self):
        bands = drawing_temperature_bands(DRAWING)
        self.assertAlmostEqual(bands["hot_minimum_c"], 95.0, places=9)
        self.assertAlmostEqual(bands["hot_maximum_c"], 105.0, places=9)
        self.assertAlmostEqual(bands["cold_maximum_c"], -135.0, places=9)
        self.assertAlmostEqual(bands["cold_minimum_c"], -145.0, places=9)

    def test_the_drawing_range_is_the_full_swing(self):
        self.assertAlmostEqual(
            drawing_temperature_bands(DRAWING)["range_k"], 240.0, places=9
        )


class CycleDispositionTests(unittest.TestCase):
    def test_a_cycle_inside_both_bands_is_credited(self):
        result = cycle_disposition(GOOD_CYCLE, DRAWING)
        self.assertEqual(result["disposition"], CYCLE_CREDITED)
        self.assertTrue(result["credited"])
        self.assertEqual(result["detail"], "")

    def test_a_cycle_exactly_on_the_band_edges_is_credited(self):
        cycle = dict(GOOD_CYCLE, peak_hot_c=95.0, peak_cold_c=-135.0)
        result = cycle_disposition(cycle, DRAWING)
        self.assertEqual(result["disposition"], CYCLE_CREDITED)

    def test_a_dwell_exactly_on_the_drawing_value_is_credited(self):
        cycle = dict(GOOD_CYCLE, hot_dwell_minutes=5.0, cold_dwell_minutes=5.0)
        self.assertTrue(cycle_disposition(cycle, DRAWING)["credited"])

    def test_a_hot_peak_above_the_band_is_an_excursion(self):
        cycle = dict(GOOD_CYCLE, peak_hot_c=112.0)
        result = cycle_disposition(cycle, DRAWING)
        self.assertEqual(result["disposition"], CYCLE_OVERSTRESS)
        self.assertTrue(result["overstress"])

    def test_a_cold_peak_below_the_band_is_an_excursion(self):
        cycle = dict(GOOD_CYCLE, peak_cold_c=-160.0)
        self.assertEqual(
            cycle_disposition(cycle, DRAWING)["disposition"], CYCLE_OVERSTRESS
        )

    def test_a_hot_peak_short_of_the_band_is_not_reached(self):
        cycle = dict(GOOD_CYCLE, peak_hot_c=80.0)
        self.assertEqual(
            cycle_disposition(cycle, DRAWING)["disposition"], CYCLE_HOT_NOT_REACHED
        )

    def test_a_cold_peak_short_of_the_band_is_not_reached(self):
        cycle = dict(GOOD_CYCLE, peak_cold_c=-120.0)
        self.assertEqual(
            cycle_disposition(cycle, DRAWING)["disposition"], CYCLE_COLD_NOT_REACHED
        )

    def test_a_short_hot_dwell_is_not_credited(self):
        cycle = dict(GOOD_CYCLE, hot_dwell_minutes=2.0)
        result = cycle_disposition(cycle, DRAWING)
        self.assertEqual(result["disposition"], CYCLE_HOT_DWELL_SHORT)
        self.assertFalse(result["credited"])

    def test_a_short_cold_dwell_is_not_credited(self):
        cycle = dict(GOOD_CYCLE, cold_dwell_minutes=0.0)
        self.assertEqual(
            cycle_disposition(cycle, DRAWING)["disposition"], CYCLE_COLD_DWELL_SHORT
        )

    def test_an_excursion_outranks_a_short_dwell(self):
        cycle = dict(GOOD_CYCLE, peak_hot_c=130.0, hot_dwell_minutes=1.0)
        self.assertEqual(
            cycle_disposition(cycle, DRAWING)["disposition"], CYCLE_OVERSTRESS
        )

    def test_the_achieved_range_is_reported(self):
        self.assertAlmostEqual(
            cycle_disposition(GOOD_CYCLE, DRAWING)["achieved_range_k"],
            242.0,
            places=9,
        )

    def test_an_inverted_cycle_record_is_rejected(self):
        cycle = dict(GOOD_CYCLE, peak_hot_c=-200.0)
        with self.assertRaises(ValueError):
            cycle_disposition(cycle, DRAWING)

    def test_a_negative_dwell_is_rejected(self):
        cycle = dict(GOOD_CYCLE, hot_dwell_minutes=-1.0)
        with self.assertRaises(ValueError):
            cycle_disposition(cycle, DRAWING)

    def test_a_non_mapping_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            cycle_disposition("cycle 1", DRAWING)


class RunAuditTests(unittest.TestCase):
    def test_a_complete_run_credits_every_cycle(self):
        audit = audit_cycling_run(DRAWING, _cycles(4))
        self.assertEqual(audit["credited_cycles"], 4)
        self.assertEqual(audit["shortfall_cycles"], 0)
        self.assertEqual(audit["findings"], [])

    def test_an_extra_cycle_does_not_create_a_shortfall(self):
        audit = audit_cycling_run(DRAWING, _cycles(6))
        self.assertEqual(audit["recorded_cycles"], 6)
        self.assertEqual(audit["shortfall_cycles"], 0)

    def test_an_uncredited_cycle_becomes_a_shortfall(self):
        run = _cycles(4)
        run[2]["hot_dwell_minutes"] = 1.0
        audit = audit_cycling_run(DRAWING, run)
        self.assertEqual(audit["credited_cycles"], 3)
        self.assertEqual(audit["shortfall_cycles"], 1)

    def test_the_drawing_identity_travels_with_the_audit(self):
        audit = audit_cycling_run(DRAWING, _cycles(4))
        self.assertEqual(audit["drawing_number"], "SCA-PV-4471")
        self.assertEqual(audit["issue"], "C")

    def test_an_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_cycling_run(DRAWING, [])


class VerdictTests(unittest.TestCase):
    def test_a_run_to_the_drawing_meets_it(self):
        result = assess_sca_thermal_cycling_process(
            {"control_drawing": DRAWING, "recorded_cycles": _cycles(4)}
        )
        self.assertEqual(result["verdict"], RUN_MEETS_CONTROL_DRAWING)
        self.assertTrue(result["meets_drawing"])

    def test_a_short_run_is_short_of_the_drawing(self):
        result = assess_sca_thermal_cycling_process(
            {"control_drawing": DRAWING, "recorded_cycles": _cycles(2)}
        )
        self.assertEqual(result["verdict"], RUN_SHORT_OF_DRAWING_CYCLES)
        self.assertEqual(result["shortfall_cycles"], 2)

    def test_an_excursion_outranks_a_complete_count(self):
        run = _cycles(4)
        run[1]["peak_hot_c"] = 140.0
        result = assess_sca_thermal_cycling_process(
            {"control_drawing": DRAWING, "recorded_cycles": run}
        )
        self.assertEqual(result["verdict"], RUN_OUTSIDE_DRAWING_EXTREMES)
        self.assertEqual(result["overstress_cycles"], 1)
        self.assertFalse(result["meets_drawing"])

    def test_a_missing_control_drawing_stops_the_audit(self):
        with self.assertRaises(ValueError):
            assess_sca_thermal_cycling_process({"recorded_cycles": _cycles(4)})

    def test_a_missing_cycle_log_stops_the_audit(self):
        with self.assertRaises(ValueError):
            assess_sca_thermal_cycling_process({"control_drawing": DRAWING})

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_thermal_cycling_process("run to SCA-PV-4471")


if __name__ == "__main__":
    unittest.main()
