"""Contract tests for the clause 4.7.8.3-4.7.8.4 bandwidth and damping logic."""

import math
import unittest

from e3301_control_system_bandwidth_damping_logic import (
    COMPARISON_TOLERANCE,
    CREDIBLE_MODAL_DAMPING_CAP,
    amplification_db,
    assess_bandwidth_damping,
    assess_closed_loop_damping,
    assess_mode_separation,
    damping_from_overshoot,
    lowest_mode,
    max_control_bandwidth_hz,
    modal_amplification,
    overshoot_from_damping,
    required_attenuation_db,
    rolloff_attenuation_db,
    separation_ratio,
    settling_time_s,
    validate_damping_ratio,
    validate_modes,
    validate_positive,
)

MODES = [
    {"name": "boom-first-bending", "frequency_hz": 20.0, "damping_ratio": 0.02},
    {"name": "panel-torsion", "frequency_hz": 45.0, "damping_ratio": 0.03},
]


def nominal_spec(**overrides):
    spec = {
        "bandwidth_hz": 2.0,
        "structural_modes": [dict(mode) for mode in MODES],
        "separation_factor": 5.0,
        "rolloff_db_per_octave": 12.0,
        "required_gain_margin_db": 6.0,
        "required_closed_loop_damping": 0.5,
        "closed_loop_damping": 0.7,
        "closed_loop_natural_frequency_hz": 2.0,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(3, "x"), 3.0)

    def test_zero_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "bandwidth_hz")

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "bandwidth_hz")

    def test_non_finite_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("nan"), "bandwidth_hz")

    def test_damping_ratio_at_unity_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_damping_ratio(1.0, "damping_ratio")

    def test_damping_ratio_at_unity_allowed_when_requested(self):
        self.assertAlmostEqual(
            validate_damping_ratio(1.0, "damping_ratio", allow_unity=True), 1.0
        )

    def test_negative_damping_ratio_rejected(self):
        with self.assertRaises(ValueError):
            validate_damping_ratio(-0.01, "damping_ratio")


class ModeSetTests(unittest.TestCase):
    def test_modes_sorted_by_frequency(self):
        unsorted_modes = [
            {"name": "high", "frequency_hz": 80.0, "damping_ratio": 0.02},
            {"name": "low", "frequency_hz": 8.0, "damping_ratio": 0.02},
        ]
        names = [mode["name"] for mode in validate_modes(unsorted_modes)]
        self.assertEqual(names, ["low", "high"])

    def test_lowest_mode_is_the_first_frequency(self):
        self.assertEqual(lowest_mode(MODES)["name"], "boom-first-bending")

    def test_empty_mode_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_modes([])

    def test_duplicate_mode_name_rejected(self):
        duplicated = [
            {"name": "same", "frequency_hz": 10.0, "damping_ratio": 0.02},
            {"name": "same", "frequency_hz": 20.0, "damping_ratio": 0.02},
        ]
        with self.assertRaises(ValueError):
            validate_modes(duplicated)

    def test_missing_mode_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_modes([{"name": "x", "frequency_hz": 10.0}])

    def test_non_mapping_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_modes([("x", 10.0, 0.02)])


class BandwidthPlacementTests(unittest.TestCase):
    def test_separation_ratio_is_the_frequency_quotient(self):
        self.assertAlmostEqual(separation_ratio(20.0, 2.0), 10.0)

    def test_bandwidth_ceiling_divides_the_lowest_mode(self):
        self.assertAlmostEqual(max_control_bandwidth_hz(20.0, 5.0), 4.0)

    def test_separation_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            max_control_bandwidth_hz(20.0, 0.5)

    def test_zero_bandwidth_rejected_by_separation_ratio(self):
        with self.assertRaises(ValueError):
            separation_ratio(20.0, 0.0)


class AmplificationTests(unittest.TestCase):
    def test_amplification_is_the_inverse_of_twice_the_damping(self):
        self.assertAlmostEqual(modal_amplification(0.01), 50.0)

    def test_amplification_in_decibels(self):
        self.assertAlmostEqual(amplification_db(0.005), 20.0 * math.log10(100.0), places=9)

    def test_required_attenuation_adds_the_margin(self):
        demanded = required_attenuation_db(0.02, 6.0)
        self.assertAlmostEqual(demanded, amplification_db(0.02) + 6.0, places=9)

    def test_negative_gain_margin_rejected(self):
        with self.assertRaises(ValueError):
            required_attenuation_db(0.02, -3.0)

    def test_rolloff_counts_octaves_above_the_bandwidth(self):
        self.assertAlmostEqual(rolloff_attenuation_db(2.0, 8.0, 12.0), 24.0, places=9)

    def test_rolloff_is_zero_at_and_below_the_bandwidth(self):
        self.assertAlmostEqual(rolloff_attenuation_db(2.0, 2.0, 12.0), 0.0)
        self.assertAlmostEqual(rolloff_attenuation_db(2.0, 1.0, 12.0), 0.0)


class DampingTests(unittest.TestCase):
    def test_overshoot_round_trips_through_damping(self):
        zeta = 0.5
        self.assertAlmostEqual(
            damping_from_overshoot(overshoot_from_damping(zeta)), zeta, places=9
        )

    def test_higher_damping_gives_smaller_overshoot(self):
        self.assertLess(overshoot_from_damping(0.7), overshoot_from_damping(0.3))

    def test_overshoot_outside_the_open_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            damping_from_overshoot(0.0)
        with self.assertRaises(ValueError):
            damping_from_overshoot(1.0)

    def test_settling_time_shortens_with_a_faster_loop(self):
        slow = settling_time_s(0.7, 1.0)
        fast = settling_time_s(0.7, 4.0)
        self.assertAlmostEqual(slow / fast, 4.0, places=9)

    def test_settling_band_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            settling_time_s(0.7, 2.0, band_fraction=1.5)

    def test_damping_recovered_from_a_measured_overshoot(self):
        spec = nominal_spec()
        del spec["closed_loop_damping"]
        spec["measured_overshoot"] = overshoot_from_damping(0.6)
        record = assess_closed_loop_damping(spec)
        self.assertEqual(record["damping_source"], "recovered-from-overshoot")
        self.assertAlmostEqual(record["achieved_damping_ratio"], 0.6, places=9)

    def test_no_damping_evidence_rejected(self):
        spec = nominal_spec()
        del spec["closed_loop_damping"]
        with self.assertRaises(ValueError):
            assess_closed_loop_damping(spec)

    def test_damping_exactly_at_the_requirement_is_met(self):
        record = assess_closed_loop_damping(
            nominal_spec(closed_loop_damping=0.5, required_closed_loop_damping=0.5)
        )
        self.assertTrue(record["damping_met"])
        self.assertAlmostEqual(
            record["achieved_damping_ratio"],
            record["required_damping_ratio"],
            places=9,
        )


class ModeSeparationScreenTests(unittest.TestCase):
    def test_nominal_modes_are_separated_and_attenuated(self):
        records = assess_mode_separation(MODES, 2.0, 5.0, 12.0, 6.0)
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertTrue(record["separation_met"])
            self.assertTrue(record["attenuation_met"])
            self.assertFalse(record["inside_bandwidth"])

    def test_mode_inside_the_bandwidth_is_flagged(self):
        close_modes = [
            {"name": "gearbox-torsion", "frequency_hz": 1.5, "damping_ratio": 0.02}
        ]
        record = assess_mode_separation(close_modes, 2.0, 5.0, 12.0, 6.0)[0]
        self.assertTrue(record["inside_bandwidth"])
        self.assertFalse(record["separation_met"])
        self.assertFalse(record["attenuation_met"])

    def test_shallow_rolloff_leaves_a_mode_under_attenuated(self):
        record = assess_mode_separation(MODES, 2.0, 5.0, 6.0, 6.0)[0]
        self.assertFalse(record["attenuation_met"])
        self.assertLess(
            record["supplied_attenuation_db"], record["required_attenuation_db"]
        )

    def test_optimistic_modal_damping_is_not_credible_without_evidence(self):
        optimistic = [
            {
                "name": "harness-stiffened-panel",
                "frequency_hz": 30.0,
                "damping_ratio": CREDIBLE_MODAL_DAMPING_CAP + 0.02,
            }
        ]
        record = assess_mode_separation(optimistic, 2.0, 5.0, 12.0, 6.0)[0]
        self.assertFalse(record["damping_assumption_credible"])

    def test_measured_modal_damping_is_credible_above_the_cap(self):
        measured = [
            {
                "name": "harness-stiffened-panel",
                "frequency_hz": 30.0,
                "damping_ratio": CREDIBLE_MODAL_DAMPING_CAP + 0.02,
                "damping_measured": True,
            }
        ]
        record = assess_mode_separation(measured, 2.0, 5.0, 12.0, 6.0)[0]
        self.assertTrue(record["damping_assumption_credible"])


class AssessmentTests(unittest.TestCase):
    def test_nominal_specification_is_compliant(self):
        result = assess_bandwidth_damping(nominal_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_bandwidth_ceiling_reported_from_the_lowest_mode(self):
        result = assess_bandwidth_damping(nominal_spec())
        self.assertAlmostEqual(result["bandwidth_ceiling_hz"], 4.0, places=9)

    def test_bandwidth_exactly_on_the_ceiling_is_accepted(self):
        result = assess_bandwidth_damping(nominal_spec(bandwidth_hz=4.0))
        self.assertTrue(result["bandwidth_within_ceiling"])
        self.assertAlmostEqual(
            result["bandwidth_hz"], result["bandwidth_ceiling_hz"], places=9
        )

    def test_bandwidth_above_the_ceiling_is_a_finding(self):
        result = assess_bandwidth_damping(nominal_spec(bandwidth_hz=6.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("ceiling" in f for f in result["findings"]))

    def test_damping_shortfall_is_a_finding(self):
        result = assess_bandwidth_damping(nominal_spec(closed_loop_damping=0.2))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("closed-loop damping" in f for f in result["findings"]))

    def test_missing_specification_key_rejected(self):
        spec = nominal_spec()
        del spec["separation_factor"]
        with self.assertRaises(ValueError):
            assess_bandwidth_damping(spec)

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            assess_bandwidth_damping(["bandwidth_hz"])

    def test_tolerance_is_small_enough_to_be_a_representation_allowance(self):
        self.assertLess(COMPARISON_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
