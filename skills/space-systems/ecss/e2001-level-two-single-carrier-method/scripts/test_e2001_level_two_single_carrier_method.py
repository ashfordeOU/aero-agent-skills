#!/usr/bin/env python3
"""Gate 3 contract test for e2001-level-two-single-carrier-method.

stdlib unittest, offline, deterministic.  Run: python3 test_...py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2001_level_two_single_carrier_method_logic as L  # noqa: E402

GAP_M = 1.0e-3
FREQ_HZ = 1.0e9
CURVE = {"sigma_max": 2.22, "e_max_ev": 165.0, "threshold_energy_ev": 12.5}
PHASES = L.seed_phases(16)


def run_record(**over):
    record = {
        "item_id": "WG-01",
        "gap_m": GAP_M,
        "frequency_hz": FREQ_HZ,
        "reference_field_v_per_m": 1.0e5,
        "reference_power_w": 100.0,
        "operating_power_w": 50.0,
        "required_margin_db": 3.0,
        "yield_curve": dict(CURVE),
        "seed_phase_count": 16,
        "tracked_periods": 6,
        "mesh_convergence_delta": 0.01,
        "seed_sensitivity": 0.02,
    }
    record.update(over)
    return record


class TestFieldScaling(unittest.TestCase):
    def test_doubling_power_scales_the_field_by_root_two(self):
        self.assertAlmostEqual(
            L.scale_field_to_power(1000.0, 50.0, 100.0), 1000.0 * math.sqrt(2.0), places=6
        )

    def test_equal_power_is_the_identity(self):
        self.assertAlmostEqual(L.scale_field_to_power(1000.0, 50.0, 50.0), 1000.0, places=9)

    def test_quarter_power_halves_the_field(self):
        self.assertAlmostEqual(L.scale_field_to_power(800.0, 100.0, 25.0), 400.0, places=9)

    def test_zero_reference_field_raises(self):
        with self.assertRaises(ValueError):
            L.scale_field_to_power(0.0, 50.0, 100.0)

    def test_negative_target_power_raises(self):
        with self.assertRaises(ValueError):
            L.scale_field_to_power(1000.0, 50.0, -100.0)

    def test_non_numeric_power_raises(self):
        with self.assertRaises(ValueError):
            L.scale_field_to_power(1000.0, "50 W", 100.0)


class TestGapVoltage(unittest.TestCase):
    def test_uniform_field_voltage(self):
        self.assertAlmostEqual(L.gap_voltage(1.0e5, 1.0e-3), 100.0, places=9)

    def test_zero_gap_raises(self):
        with self.assertRaises(ValueError):
            L.gap_voltage(1.0e5, 0.0)

    def test_negative_field_raises(self):
        with self.assertRaises(ValueError):
            L.gap_voltage(-1.0, 1.0e-3)


class TestElectronKinematics(unittest.TestCase):
    def test_seed_energy_speed(self):
        self.assertAlmostEqual(L.energy_to_speed(2.0), 838765.76, delta=1.0)

    def test_zero_energy_gives_zero_speed(self):
        self.assertAlmostEqual(L.energy_to_speed(0.0), 0.0, places=12)

    def test_round_trip_energy_speed(self):
        self.assertAlmostEqual(
            L.speed_to_energy_ev(L.energy_to_speed(137.0)), 137.0, places=9
        )

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            L.energy_to_speed(-1.0)

    def test_non_numeric_speed_raises(self):
        with self.assertRaises(ValueError):
            L.speed_to_energy_ev("fast")


class TestSecondaryYield(unittest.TestCase):
    def test_peak_value_at_peak_energy(self):
        self.assertAlmostEqual(L.secondary_yield(CURVE, 165.0), 2.22, places=9)

    def test_below_threshold_no_secondaries(self):
        self.assertAlmostEqual(L.secondary_yield(CURVE, 5.0), 0.0, places=12)

    def test_mid_band_exceeds_unity(self):
        self.assertGreater(L.secondary_yield(CURVE, 100.0), 1.0)

    def test_far_tail_falls_below_unity(self):
        self.assertLess(L.secondary_yield(CURVE, 6000.0), 1.0)

    def test_negative_impact_energy_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield(CURVE, -10.0)

    def test_curve_missing_key_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield({"sigma_max": 2.0}, 100.0)

    def test_peak_yield_at_unity_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield({"sigma_max": 1.0, "e_max_ev": 165.0}, 100.0)

    def test_threshold_above_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield(
                {"sigma_max": 2.0, "e_max_ev": 100.0, "threshold_energy_ev": 200.0}, 50.0
            )

    def test_non_mapping_curve_raises(self):
        with self.assertRaises(ValueError):
            L.secondary_yield("silver", 100.0)


class TestSeedPhases(unittest.TestCase):
    def test_count_and_first_phase(self):
        phases = L.seed_phases(16)
        self.assertEqual(len(phases), 16)
        self.assertAlmostEqual(phases[0], 0.0, places=12)

    def test_phases_stay_inside_one_cycle(self):
        phases = L.seed_phases(8)
        self.assertLess(phases[-1], 2.0 * math.pi)
        self.assertEqual(phases, sorted(phases))

    def test_zero_count_raises(self):
        with self.assertRaises(ValueError):
            L.seed_phases(0)

    def test_non_integer_count_raises(self):
        with self.assertRaises(ValueError):
            L.seed_phases(12.5)


class TestTrackElectron(unittest.TestCase):
    def test_negligible_field_crosses_at_the_seed_energy(self):
        outcome = L.track_electron(GAP_M, 1.0, FREQ_HZ, 0.0)
        self.assertTrue(outcome["impacted"])
        self.assertEqual(outcome["wall"], "opposite")
        self.assertAlmostEqual(outcome["impact_energy_ev"], 2.0, delta=0.01)
        self.assertAlmostEqual(outcome["transit_periods"], 1.2, delta=0.02)

    def test_too_few_tracked_periods_leaves_the_electron_in_flight(self):
        outcome = L.track_electron(GAP_M, 1.0, FREQ_HZ, 0.0, tracked_periods=1)
        self.assertFalse(outcome["impacted"])
        self.assertIsNone(outcome["wall"])
        self.assertAlmostEqual(outcome["impact_energy_ev"], 0.0, places=12)

    def test_reversed_phase_returns_the_electron_to_its_launch_wall(self):
        outcome = L.track_electron(GAP_M, 2.0e5, FREQ_HZ, math.pi)
        self.assertEqual(outcome["wall"], "launch")
        self.assertAlmostEqual(outcome["impact_energy_ev"], 8.31, delta=0.05)

    def test_in_band_field_delivers_a_high_impact_energy(self):
        outcome = L.track_electron(GAP_M, 2.0e5, FREQ_HZ, 0.0)
        self.assertEqual(outcome["wall"], "opposite")
        self.assertAlmostEqual(outcome["impact_energy_ev"], 176.73, delta=0.5)

    def test_stronger_field_raises_the_impact_energy(self):
        weak = L.track_electron(GAP_M, 1.0e5, FREQ_HZ, 0.0)["impact_energy_ev"]
        strong = L.track_electron(GAP_M, 3.0e5, FREQ_HZ, 0.0)["impact_energy_ev"]
        self.assertGreater(strong, weak)

    def test_zero_gap_raises(self):
        with self.assertRaises(ValueError):
            L.track_electron(0.0, 1.0e5, FREQ_HZ, 0.0)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            L.track_electron(GAP_M, 1.0e5, 0.0, 0.0)

    def test_coarse_step_count_raises(self):
        with self.assertRaises(ValueError):
            L.track_electron(GAP_M, 1.0e5, FREQ_HZ, 0.0, steps_per_period=4)

    def test_non_integer_step_count_raises(self):
        with self.assertRaises(ValueError):
            L.track_electron(GAP_M, 1.0e5, FREQ_HZ, 0.0, steps_per_period=120.0)

    def test_zero_tracked_periods_raises(self):
        with self.assertRaises(ValueError):
            L.track_electron(GAP_M, 1.0e5, FREQ_HZ, 0.0, tracked_periods=0)

    def test_negative_seed_energy_raises(self):
        with self.assertRaises(ValueError):
            L.track_electron(GAP_M, 1.0e5, FREQ_HZ, 0.0, initial_energy_ev=-2.0)


class TestEffectiveYield(unittest.TestCase):
    def test_weak_field_produces_no_secondaries(self):
        self.assertAlmostEqual(
            L.effective_yield(GAP_M, 1.0e4, FREQ_HZ, CURVE, phases=PHASES), 0.0, places=12
        )

    def test_in_band_field_sustains_the_population(self):
        self.assertGreater(
            L.effective_yield(GAP_M, 2.0e5, FREQ_HZ, CURVE, phases=PHASES), 1.0
        )

    def test_above_the_band_the_population_decays_again(self):
        self.assertLess(
            L.effective_yield(GAP_M, 2.0e6, FREQ_HZ, CURVE, phases=PHASES), 1.0
        )

    def test_empty_phase_set_raises(self):
        with self.assertRaises(ValueError):
            L.effective_yield(GAP_M, 2.0e5, FREQ_HZ, CURVE, phases=[])

    def test_invalid_curve_raises(self):
        with self.assertRaises(ValueError):
            L.effective_yield(GAP_M, 2.0e5, FREQ_HZ, {"sigma_max": 2.0}, phases=PHASES)


class TestThresholdSearch(unittest.TestCase):
    def test_threshold_field_is_reproducible(self):
        solved = L.single_carrier_threshold_field(
            GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES
        )
        self.assertAlmostEqual(solved["threshold_field_v_per_m"], 108151.5, delta=300.0)

    def test_threshold_gap_voltage_is_reproducible(self):
        solved = L.single_carrier_threshold_field(
            GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES
        )
        self.assertAlmostEqual(solved["threshold_gap_voltage_v"], 108.15, delta=0.5)

    def test_bracket_encloses_the_threshold(self):
        solved = L.single_carrier_threshold_field(
            GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES
        )
        lo, hi = solved["bracket_v_per_m"]
        self.assertLessEqual(lo, solved["threshold_field_v_per_m"])
        self.assertLessEqual(solved["threshold_field_v_per_m"], hi)

    def test_the_bracket_edges_straddle_unity(self):
        solved = L.single_carrier_threshold_field(
            GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES
        )
        lo, hi = solved["bracket_v_per_m"]
        self.assertLess(L.effective_yield(GAP_M, lo, FREQ_HZ, CURVE, phases=PHASES), 1.0)
        self.assertGreaterEqual(
            L.effective_yield(GAP_M, hi, FREQ_HZ, CURVE, phases=PHASES), 1.0
        )

    def test_a_wider_gap_at_higher_frequency_raises_the_threshold_voltage(self):
        narrow = L.single_carrier_threshold_field(
            GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES
        )["threshold_gap_voltage_v"]
        wide = L.single_carrier_threshold_field(
            2.0e-3, 2.0e9, CURVE, 1.0e3, 1.0e7, phases=PHASES
        )["threshold_gap_voltage_v"]
        self.assertGreater(wide, narrow)

    def test_inverted_bracket_raises(self):
        with self.assertRaises(ValueError):
            L.single_carrier_threshold_field(
                GAP_M, FREQ_HZ, CURVE, 1.0e7, 1.0e3, phases=PHASES
            )

    def test_lower_bracket_already_in_the_band_raises(self):
        with self.assertRaises(ValueError):
            L.single_carrier_threshold_field(
                GAP_M, FREQ_HZ, CURVE, 2.0e5, 1.0e7, phases=PHASES
            )

    def test_range_without_any_growth_raises(self):
        with self.assertRaises(ValueError):
            L.single_carrier_threshold_field(
                GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e4, phases=PHASES
            )

    def test_too_few_scan_points_raises(self):
        with self.assertRaises(ValueError):
            L.single_carrier_threshold_field(
                GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES, scan_points=2
            )

    def test_non_positive_tolerance_raises(self):
        with self.assertRaises(ValueError):
            L.single_carrier_threshold_field(
                GAP_M, FREQ_HZ, CURVE, 1.0e3, 1.0e7, phases=PHASES, relative_tolerance=0.0
            )


class TestPowerAndMargin(unittest.TestCase):
    def test_threshold_power_scales_with_the_field_squared(self):
        self.assertAlmostEqual(
            L.threshold_power_w(2.0e5, 1.0e5, 100.0), 400.0, places=6
        )

    def test_equal_fields_return_the_reference_power(self):
        self.assertAlmostEqual(L.threshold_power_w(1.0e5, 1.0e5, 100.0), 100.0, places=9)

    def test_zero_reference_power_raises(self):
        with self.assertRaises(ValueError):
            L.threshold_power_w(2.0e5, 1.0e5, 0.0)

    def test_doubled_power_is_three_decibel(self):
        self.assertAlmostEqual(L.multipactor_margin_db(100.0, 50.0), 3.0103, places=4)

    def test_equal_power_is_zero_decibel(self):
        self.assertAlmostEqual(L.multipactor_margin_db(50.0, 50.0), 0.0, places=12)

    def test_negative_operating_power_raises(self):
        with self.assertRaises(ValueError):
            L.multipactor_margin_db(100.0, -1.0)


class TestConvergence(unittest.TestCase):
    def test_converged_run(self):
        report = L.check_convergence(
            {
                "seed_phase_count": 16,
                "tracked_periods": 6,
                "mesh_convergence_delta": 0.01,
                "seed_sensitivity": 0.02,
            }
        )
        self.assertTrue(report["converged"])
        self.assertEqual(report["findings"], [])

    def test_too_few_seed_phases(self):
        report = L.check_convergence(
            {
                "seed_phase_count": 4,
                "tracked_periods": 6,
                "mesh_convergence_delta": 0.01,
                "seed_sensitivity": 0.02,
            }
        )
        self.assertIn("seed-phase-count-below-minimum", report["findings"])

    def test_too_few_tracked_periods(self):
        report = L.check_convergence(
            {
                "seed_phase_count": 16,
                "tracked_periods": 2,
                "mesh_convergence_delta": 0.01,
                "seed_sensitivity": 0.02,
            }
        )
        self.assertIn("tracked-periods-below-minimum", report["findings"])

    def test_unconverged_field_mesh(self):
        report = L.check_convergence(
            {
                "seed_phase_count": 16,
                "tracked_periods": 6,
                "mesh_convergence_delta": 0.20,
                "seed_sensitivity": 0.02,
            }
        )
        self.assertIn("field-mesh-not-converged", report["findings"])

    def test_threshold_still_moving_with_seed_count(self):
        report = L.check_convergence(
            {
                "seed_phase_count": 16,
                "tracked_periods": 6,
                "mesh_convergence_delta": 0.01,
                "seed_sensitivity": -0.30,
            }
        )
        self.assertIn("threshold-still-moving-with-seed-count", report["findings"])

    def test_exact_mesh_limit_is_accepted(self):
        report = L.check_convergence(
            {
                "seed_phase_count": 16,
                "tracked_periods": 6,
                "mesh_convergence_delta": L.MAX_MESH_DELTA,
                "seed_sensitivity": 0.02,
            }
        )
        self.assertTrue(report["converged"])

    def test_one_ulp_over_the_mesh_limit_is_absorbed(self):
        just_over = math.nextafter(L.MAX_MESH_DELTA, 1.0)
        self.assertGreater(just_over, L.MAX_MESH_DELTA)
        report = L.check_convergence(
            {
                "seed_phase_count": 16,
                "tracked_periods": 6,
                "mesh_convergence_delta": just_over,
                "seed_sensitivity": 0.02,
            }
        )
        self.assertTrue(report["converged"])

    def test_missing_records_are_each_a_finding(self):
        report = L.check_convergence({})
        self.assertEqual(len(report["findings"]), 4)

    def test_zero_seed_phase_count_raises(self):
        with self.assertRaises(ValueError):
            L.check_convergence({"seed_phase_count": 0})

    def test_non_mapping_run_raises(self):
        with self.assertRaises(ValueError):
            L.check_convergence("WG-01")


class TestAssessSingleCarrierRun(unittest.TestCase):
    def test_compliant_run(self):
        report = L.assess_single_carrier_run(run_record())
        self.assertEqual(report["item_id"], "WG-01")
        self.assertAlmostEqual(report["threshold_gap_voltage_v"], 108.15, delta=0.5)
        self.assertAlmostEqual(report["threshold_power_w"], 116.97, delta=1.0)
        self.assertAlmostEqual(report["margin_db"], 3.69, delta=0.05)
        self.assertTrue(report["converged"])
        self.assertTrue(report["compliant"])

    def test_margin_shortfall_is_a_finding(self):
        report = L.assess_single_carrier_run(run_record(required_margin_db=6.0))
        self.assertIn("single-carrier-margin-shortfall", report["findings"])
        self.assertFalse(report["compliant"])

    def test_requirement_exactly_at_the_achieved_margin_passes(self):
        achieved = L.assess_single_carrier_run(run_record())["margin_db"]
        report = L.assess_single_carrier_run(run_record(required_margin_db=achieved))
        self.assertNotIn("single-carrier-margin-shortfall", report["findings"])

    def test_unrecorded_convergence_evidence_is_a_finding(self):
        record = run_record()
        del record["mesh_convergence_delta"]
        report = L.assess_single_carrier_run(record)
        self.assertIn("field-mesh-convergence-not-recorded", report["findings"])
        self.assertFalse(report["converged"])

    def test_thin_seeding_is_a_finding(self):
        report = L.assess_single_carrier_run(run_record(seed_phase_count=8))
        self.assertIn("seed-phase-count-below-minimum", report["findings"])

    def test_missing_key_raises(self):
        record = run_record()
        del record["operating_power_w"]
        with self.assertRaises(ValueError):
            L.assess_single_carrier_run(record)

    def test_blank_item_id_raises(self):
        with self.assertRaises(ValueError):
            L.assess_single_carrier_run(run_record(item_id="  "))

    def test_non_mapping_run_raises(self):
        with self.assertRaises(ValueError):
            L.assess_single_carrier_run(["WG-01"])

    def test_non_positive_operating_power_raises(self):
        with self.assertRaises(ValueError):
            L.assess_single_carrier_run(run_record(operating_power_w=0.0))


if __name__ == "__main__":
    unittest.main()
