"""Contract tests for the clause 5.5.1.5.3 coupon discharge-test run logic."""

import unittest

from e2008_esd_test_process_logic import (
    DEFAULT_MAX_CHAMBER_PRESSURE_PA,
    MIN_SAMPLES_PER_DECAY,
    assess_esd_test_run,
    decay_time_constant_s,
    evaluate_setting,
    peak_arc_current_a,
    probe_spans_peak,
    recorder_resolves_decay,
    samples_per_decay,
    stored_energy_j,
    validate_chamber,
    validate_coupon,
)

CIRCUIT = {"capacitance_f": 1.0e-6, "series_resistance_ohm": 10.0}
INSTRUMENTS = {"sample_rate_hz": 1.0e9, "current_probe_range_a": 1000.0}
CHAMBER = {"pressure_pa": 1.0e-4, "temperature_c": -60.0}


def _setting(bias=-5000.0, planned=10, recorded=10):
    return {
        "bias_voltage_v": bias,
        "discharges_planned": planned,
        "discharges_recorded": recorded,
    }


def _spec(**overrides):
    spec = {
        "coupon": {"cell_count": 6, "active_area_cm2": 120.0},
        "chamber": dict(CHAMBER),
        "discharge_circuit": dict(CIRCUIT),
        "instrumentation": dict(INSTRUMENTS),
        "settings": [_setting(-5000.0), _setting(-8000.0)],
        "required": {"discharge_energy_j": 5.0, "discharges_per_setting": 10},
        "observed": {"sustained_arc": False},
    }
    spec.update(overrides)
    return spec


class StoredEnergyTests(unittest.TestCase):
    def test_energy_follows_half_c_v_squared(self):
        self.assertAlmostEqual(stored_energy_j(1.0e-6, -5000.0), 12.5, places=9)

    def test_energy_is_independent_of_bias_sign(self):
        self.assertAlmostEqual(
            stored_energy_j(1.0e-6, 5000.0), stored_energy_j(1.0e-6, -5000.0), places=9
        )

    def test_doubling_the_bias_quadruples_the_energy(self):
        low = stored_energy_j(2.0e-6, -1000.0)
        high = stored_energy_j(2.0e-6, -2000.0)
        self.assertAlmostEqual(high, 4.0 * low, places=9)

    def test_zero_bias_rejected(self):
        with self.assertRaises(ValueError):
            stored_energy_j(1.0e-6, 0.0)

    def test_negative_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            stored_energy_j(-1.0e-6, -5000.0)

    def test_boolean_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            stored_energy_j(True, -5000.0)


class CircuitTests(unittest.TestCase):
    def test_decay_constant_is_the_rc_product(self):
        self.assertAlmostEqual(decay_time_constant_s(10.0, 1.0e-6), 1.0e-5, places=12)

    def test_peak_current_is_bias_over_resistance(self):
        self.assertAlmostEqual(peak_arc_current_a(-5000.0, 10.0), 500.0, places=9)

    def test_peak_current_uses_the_bias_magnitude(self):
        self.assertAlmostEqual(
            peak_arc_current_a(5000.0, 10.0), peak_arc_current_a(-5000.0, 10.0), places=9
        )

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            peak_arc_current_a(-5000.0, 0.0)

    def test_non_finite_resistance_rejected(self):
        with self.assertRaises(ValueError):
            decay_time_constant_s(float("inf"), 1.0e-6)


class InstrumentationTests(unittest.TestCase):
    def test_sample_count_is_rate_times_decay(self):
        self.assertAlmostEqual(samples_per_decay(1.0e9, 1.0e-5), 1.0e4, places=6)

    def test_exact_minimum_sample_count_resolves(self):
        self.assertAlmostEqual(samples_per_decay(1.0e6, 1.0e-5), MIN_SAMPLES_PER_DECAY,
                               places=9)
        self.assertTrue(recorder_resolves_decay(1.0e6, 1.0e-5))

    def test_slow_recorder_does_not_resolve(self):
        self.assertFalse(recorder_resolves_decay(1.0e5, 1.0e-5))

    def test_fast_recorder_resolves(self):
        self.assertTrue(recorder_resolves_decay(1.0e9, 1.0e-5))

    def test_probe_exactly_at_the_peak_is_accepted(self):
        self.assertTrue(probe_spans_peak(500.0, 500.0))

    def test_probe_below_the_peak_is_rejected(self):
        self.assertFalse(probe_spans_peak(100.0, 500.0))

    def test_probe_range_must_be_positive(self):
        with self.assertRaises(ValueError):
            probe_spans_peak(0.0, 500.0)


class CouponAndChamberTests(unittest.TestCase):
    def test_coupon_is_normalised(self):
        coupon = validate_coupon({"cell_count": 4, "active_area_cm2": 80})
        self.assertEqual(coupon["cell_count"], 4)
        self.assertAlmostEqual(coupon["active_area_cm2"], 80.0, places=9)

    def test_coupon_without_cells_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon({"cell_count": 0, "active_area_cm2": 80.0})

    def test_coupon_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon({"cell_count": 4})

    def test_vacuum_chamber_gives_no_findings(self):
        _, findings = validate_chamber({"pressure_pa": 1.0e-5, "temperature_c": -40.0})
        self.assertEqual(findings, [])

    def test_pressure_exactly_at_the_ceiling_gives_no_finding(self):
        _, findings = validate_chamber(
            {"pressure_pa": DEFAULT_MAX_CHAMBER_PRESSURE_PA, "temperature_c": 20.0}
        )
        self.assertEqual(findings, [])

    def test_soft_vacuum_is_flagged(self):
        _, findings = validate_chamber({"pressure_pa": 1.0, "temperature_c": 20.0})
        self.assertEqual(len(findings), 1)
        self.assertIn("ceiling", findings[0])

    def test_temperature_outside_the_window_is_flagged(self):
        _, findings = validate_chamber({"pressure_pa": 1.0e-5, "temperature_c": 200.0})
        self.assertEqual(len(findings), 1)
        self.assertIn("test window", findings[0])

    def test_inverted_temperature_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_chamber(
                {
                    "pressure_pa": 1.0e-5,
                    "temperature_c": 20.0,
                    "temperature_window_c": (60.0, -20.0),
                }
            )

    def test_malformed_temperature_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_chamber(
                {
                    "pressure_pa": 1.0e-5,
                    "temperature_c": 20.0,
                    "temperature_window_c": (60.0,),
                }
            )


class SettingEvaluationTests(unittest.TestCase):
    def test_conforming_setting_reports_no_findings(self):
        record = evaluate_setting(_setting(), CIRCUIT, INSTRUMENTS, 5.0, 10)
        self.assertTrue(record["conforms"])
        self.assertEqual(record["findings"], [])

    def test_record_carries_the_circuit_quantities(self):
        record = evaluate_setting(_setting(), CIRCUIT, INSTRUMENTS, 5.0, 10)
        self.assertAlmostEqual(record["stored_energy_j"], 12.5, places=9)
        self.assertAlmostEqual(record["peak_arc_current_a"], 500.0, places=9)
        self.assertAlmostEqual(record["time_constant_s"], 1.0e-5, places=12)

    def test_energy_exactly_at_the_requirement_is_adequate(self):
        needed = stored_energy_j(CIRCUIT["capacitance_f"], -5000.0)
        record = evaluate_setting(_setting(), CIRCUIT, INSTRUMENTS, needed, 10)
        self.assertTrue(record["energy_adequate"])
        self.assertTrue(record["conforms"])

    def test_energy_below_the_requirement_is_flagged(self):
        record = evaluate_setting(_setting(), CIRCUIT, INSTRUMENTS, 50.0, 10)
        self.assertFalse(record["energy_adequate"])
        self.assertFalse(record["conforms"])

    def test_undersized_probe_is_flagged(self):
        instruments = {"sample_rate_hz": 1.0e9, "current_probe_range_a": 50.0}
        record = evaluate_setting(_setting(), CIRCUIT, instruments, 5.0, 10)
        self.assertFalse(record["probe_adequate"])

    def test_slow_recorder_is_flagged(self):
        instruments = {"sample_rate_hz": 1.0e4, "current_probe_range_a": 1000.0}
        record = evaluate_setting(_setting(), CIRCUIT, instruments, 5.0, 10)
        self.assertFalse(record["recorder_adequate"])

    def test_short_discharge_plan_is_flagged(self):
        record = evaluate_setting(_setting(planned=3, recorded=3), CIRCUIT,
                                  INSTRUMENTS, 5.0, 10)
        self.assertFalse(record["conforms"])
        self.assertTrue(any("fewer than the 10 required" in f for f in record["findings"]))

    def test_missing_discharges_are_flagged(self):
        record = evaluate_setting(_setting(recorded=4), CIRCUIT, INSTRUMENTS, 5.0, 10)
        self.assertTrue(any("recorded 4 of 10" in f for f in record["findings"]))

    def test_zero_planned_discharges_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_setting(_setting(planned=0), CIRCUIT, INSTRUMENTS, 5.0, 10)

    def test_fractional_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_setting(_setting(planned=2.5), CIRCUIT, INSTRUMENTS, 5.0, 10)

    def test_zero_bias_setting_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_setting(_setting(bias=0.0), CIRCUIT, INSTRUMENTS, 5.0, 10)


class AssessmentTests(unittest.TestCase):
    def test_conforming_run_is_valid(self):
        result = assess_esd_test_run(_spec())
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_totals_sum_across_settings(self):
        result = assess_esd_test_run(_spec())
        self.assertEqual(result["total_discharges_planned"], 20)
        self.assertEqual(result["total_discharges_recorded"], 20)

    def test_one_record_per_setting(self):
        result = assess_esd_test_run(_spec())
        self.assertEqual(len(result["setting_records"]), 2)

    def test_sustained_arc_invalidates_the_run(self):
        result = assess_esd_test_run(_spec(observed={"sustained_arc": True}))
        self.assertFalse(result["valid"])
        self.assertTrue(result["sustained_arc"])
        self.assertTrue(any("sustained arc" in f for f in result["findings"]))

    def test_soft_vacuum_invalidates_the_run(self):
        result = assess_esd_test_run(
            _spec(chamber={"pressure_pa": 10.0, "temperature_c": -40.0})
        )
        self.assertFalse(result["valid"])

    def test_missing_discharges_invalidate_the_run(self):
        result = assess_esd_test_run(
            _spec(settings=[_setting(-5000.0, 10, 2), _setting(-8000.0)])
        )
        self.assertFalse(result["valid"])

    def test_duplicate_bias_setting_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_test_run(_spec(settings=[_setting(-5000.0), _setting(-5000.0)]))

    def test_empty_setting_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_test_run(_spec(settings=[]))

    def test_missing_required_block_rejected(self):
        spec = _spec()
        del spec["required"]
        with self.assertRaises(ValueError):
            assess_esd_test_run(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_test_run(["coupon"])

    def test_non_boolean_sustained_arc_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_test_run(_spec(observed={"sustained_arc": "yes"}))

    def test_observed_block_is_optional(self):
        spec = _spec()
        del spec["observed"]
        result = assess_esd_test_run(spec)
        self.assertFalse(result["sustained_arc"])
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
