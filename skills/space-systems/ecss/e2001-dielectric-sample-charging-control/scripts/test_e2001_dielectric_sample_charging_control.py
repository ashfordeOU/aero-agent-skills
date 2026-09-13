#!/usr/bin/env python3
"""Gate 3 contract test for e2001-dielectric-sample-charging-control.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_dielectric_sample_charging_control.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2001_dielectric_sample_charging_control_logic import (  # noqa: E402
    DEFAULT_MAGNITUDE_LIMIT_V,
    DEFAULT_SPREAD_LIMIT_V,
    HARD_REJECT_SPREAD_MULTIPLE,
    NEUTRALIZATION_TECHNIQUES,
    VACUUM_PERMITTIVITY_F_PER_M,
    categorize_precondition_state,
    dielectric_relaxation_time,
    is_within_limit,
    plan_discharge_sequence,
    required_neutralization_dwell,
    residual_voltage_after,
    surface_voltage_magnitude,
    surface_voltage_spread,
    validate_neutralization_technique,
    validate_voltage_map,
    verify_post_neutralization,
)


class TestValidateVoltageMap(unittest.TestCase):
    def test_happy_path_returns_floats(self):
        out = validate_voltage_map([1, -2.5, 0])
        self.assertEqual(len(out), 3)
        for value in out:
            self.assertIsInstance(value, float)

    def test_accepts_tuple(self):
        self.assertEqual(len(validate_voltage_map((1.0, 2.0))), 2)

    def test_rejects_empty_map(self):
        with self.assertRaises(ValueError):
            validate_voltage_map([])

    def test_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            validate_voltage_map(3.0)

    def test_rejects_string(self):
        with self.assertRaises(ValueError):
            validate_voltage_map("1.0,2.0")

    def test_rejects_non_numeric_reading(self):
        with self.assertRaises(ValueError):
            validate_voltage_map([1.0, "hot", 2.0])

    def test_rejects_boolean_reading(self):
        with self.assertRaises(ValueError):
            validate_voltage_map([1.0, True])

    def test_rejects_non_finite_reading(self):
        with self.assertRaises(ValueError):
            validate_voltage_map([1.0, float("nan")])


class TestMapFigures(unittest.TestCase):
    def test_magnitude_takes_largest_absolute_value(self):
        self.assertAlmostEqual(surface_voltage_magnitude([1.0, -7.5, 3.0]), 7.5)

    def test_magnitude_of_single_point(self):
        self.assertAlmostEqual(surface_voltage_magnitude([-2.0]), 2.0)

    def test_spread_is_highest_minus_lowest(self):
        self.assertAlmostEqual(surface_voltage_spread([1.0, -7.5, 3.0]), 10.5)

    def test_spread_of_uniform_map_is_zero(self):
        self.assertAlmostEqual(surface_voltage_spread([4.0, 4.0, 4.0]), 0.0)

    def test_uniform_map_can_have_large_magnitude_and_no_spread(self):
        readings = [40.0, 40.0, 40.0]
        self.assertAlmostEqual(surface_voltage_magnitude(readings), 40.0)
        self.assertAlmostEqual(surface_voltage_spread(readings), 0.0)


class TestIsWithinLimit(unittest.TestCase):
    def test_below_limit(self):
        self.assertTrue(is_within_limit(1.0, 5.0))

    def test_exactly_at_limit_is_inside(self):
        self.assertTrue(is_within_limit(5.0, 5.0))

    def test_above_limit(self):
        self.assertFalse(is_within_limit(5.01, 5.0))

    def test_measured_difference_at_limit_is_absorbed(self):
        # 0.2 - (-0.1) evaluates a few ULPs above the exact 0.3 V limit;
        # that is binary representation error in a measured difference,
        # not a real exceedance, so the logic absorbs it and the
        # acceptance limit stays at 0.3 V.
        spread = surface_voltage_spread([-0.1, 0.2])
        self.assertGreater(spread, 0.3)
        self.assertTrue(is_within_limit(spread, 0.3))

    def test_rejects_negative_value(self):
        with self.assertRaises(ValueError):
            is_within_limit(-1.0, 5.0)

    def test_rejects_zero_limit(self):
        with self.assertRaises(ValueError):
            is_within_limit(1.0, 0.0)


class TestPreconditionState(unittest.TestCase):
    def test_clean_coupon_is_ready(self):
        out = categorize_precondition_state([1.0, 2.0, 0.5])
        self.assertEqual(out["state"], "ready")
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["point_count"], 3)

    def test_magnitude_breach_needs_neutralization(self):
        out = categorize_precondition_state([6.0, 5.5, 5.2])
        self.assertEqual(out["state"], "needs-neutralization")
        self.assertFalse(out["magnitude_within_limit"])
        self.assertTrue(out["spread_within_limit"])

    def test_spread_breach_needs_neutralization(self):
        out = categorize_precondition_state([-2.0, 2.0])
        self.assertTrue(out["magnitude_within_limit"])
        self.assertFalse(out["spread_within_limit"])
        self.assertEqual(out["state"], "needs-neutralization")

    def test_uniform_offset_is_a_magnitude_finding_only(self):
        out = categorize_precondition_state([40.0, 40.0, 40.0])
        self.assertEqual(len(out["findings"]), 1)
        self.assertIn("magnitude", out["findings"][0])

    def test_hard_spread_breach_rejects_the_coupon(self):
        out = categorize_precondition_state([-15.0, 15.0])
        self.assertEqual(out["state"], "reject-coupon")
        self.assertTrue(any("embedded charge" in f for f in out["findings"]))

    def test_boundary_spread_is_inside_the_limit(self):
        out = categorize_precondition_state(
            [-0.1, 0.2], magnitude_limit_v=5.0, spread_limit_v=0.3
        )
        self.assertTrue(out["spread_within_limit"])
        self.assertEqual(out["state"], "ready")

    def test_exact_limits_are_inside(self):
        out = categorize_precondition_state(
            [DEFAULT_MAGNITUDE_LIMIT_V, DEFAULT_MAGNITUDE_LIMIT_V - DEFAULT_SPREAD_LIMIT_V]
        )
        self.assertTrue(out["magnitude_within_limit"])
        self.assertTrue(out["spread_within_limit"])
        self.assertEqual(out["state"], "ready")

    def test_rejects_zero_magnitude_limit(self):
        with self.assertRaises(ValueError):
            categorize_precondition_state([1.0], magnitude_limit_v=0.0)

    def test_rejects_negative_spread_limit(self):
        with self.assertRaises(ValueError):
            categorize_precondition_state([1.0], spread_limit_v=-2.0)

    def test_rejects_empty_map(self):
        with self.assertRaises(ValueError):
            categorize_precondition_state([])


class TestNeutralizationTechnique(unittest.TestCase):
    def test_electron_flood_is_admissible(self):
        self.assertAlmostEqual(
            validate_neutralization_technique("electron-flood"),
            NEUTRALIZATION_TECHNIQUES["electron-flood"],
        )

    def test_technique_is_case_and_space_insensitive(self):
        self.assertAlmostEqual(
            validate_neutralization_technique("  Low-Energy-Plasma "),
            NEUTRALIZATION_TECHNIQUES["low-energy-plasma"],
        )

    def test_passive_grounding_has_no_acceleration(self):
        self.assertAlmostEqual(
            validate_neutralization_technique("passive-grounding"), 1.0
        )

    def test_rejects_surface_altering_solvent_wipe(self):
        with self.assertRaises(ValueError):
            validate_neutralization_technique("solvent-wipe")

    def test_rejects_surface_altering_ion_beam_clean(self):
        with self.assertRaises(ValueError):
            validate_neutralization_technique("ion-beam-clean")

    def test_rejects_unknown_technique(self):
        with self.assertRaises(ValueError):
            validate_neutralization_technique("wave-a-magnet")

    def test_rejects_empty_technique(self):
        with self.assertRaises(ValueError):
            validate_neutralization_technique("   ")

    def test_rejects_non_string_technique(self):
        with self.assertRaises(ValueError):
            validate_neutralization_technique(42)


class TestRelaxationAndDecay(unittest.TestCase):
    def test_relaxation_time_of_a_polymer(self):
        tau = dielectric_relaxation_time(3.0, 1.0e14)
        self.assertAlmostEqual(tau, VACUUM_PERMITTIVITY_F_PER_M * 3.0e14, places=6)

    def test_relaxation_time_scales_with_resistivity(self):
        low = dielectric_relaxation_time(3.0, 1.0e12)
        high = dielectric_relaxation_time(3.0, 1.0e14)
        self.assertAlmostEqual(high / low, 100.0, places=6)

    def test_rejects_permittivity_below_one(self):
        with self.assertRaises(ValueError):
            dielectric_relaxation_time(0.5, 1.0e14)

    def test_rejects_zero_resistivity(self):
        with self.assertRaises(ValueError):
            dielectric_relaxation_time(3.0, 0.0)

    def test_rejects_non_numeric_permittivity(self):
        with self.assertRaises(ValueError):
            dielectric_relaxation_time("three", 1.0e14)

    def test_residual_after_one_time_constant(self):
        self.assertAlmostEqual(
            residual_voltage_after(100.0, 10.0, 10.0), 100.0 / math.e, places=9
        )

    def test_residual_at_zero_elapsed_is_unchanged(self):
        self.assertAlmostEqual(residual_voltage_after(-40.0, 10.0, 0.0), -40.0)

    def test_residual_rejects_negative_elapsed(self):
        with self.assertRaises(ValueError):
            residual_voltage_after(100.0, 10.0, -1.0)

    def test_residual_rejects_zero_relaxation_time(self):
        with self.assertRaises(ValueError):
            residual_voltage_after(100.0, 0.0, 5.0)


class TestRequiredDwell(unittest.TestCase):
    def test_dwell_for_one_decade_of_decay(self):
        dwell = required_neutralization_dwell(50.0, 5.0, 100.0, 1.0)
        self.assertAlmostEqual(dwell, 100.0 * math.log(10.0), places=9)

    def test_effectiveness_divides_the_dwell(self):
        slow = required_neutralization_dwell(50.0, 5.0, 100.0, 1.0)
        fast = required_neutralization_dwell(50.0, 5.0, 100.0, 500.0)
        self.assertAlmostEqual(fast * 500.0, slow, places=9)

    def test_already_at_target_needs_no_dwell(self):
        self.assertAlmostEqual(
            required_neutralization_dwell(5.0, 5.0, 100.0, 1.0), 0.0
        )

    def test_below_target_needs_no_dwell(self):
        self.assertAlmostEqual(
            required_neutralization_dwell(1.0, 5.0, 100.0, 1.0), 0.0
        )

    def test_rejects_negative_initial_magnitude(self):
        with self.assertRaises(ValueError):
            required_neutralization_dwell(-1.0, 5.0, 100.0, 1.0)

    def test_rejects_zero_target(self):
        with self.assertRaises(ValueError):
            required_neutralization_dwell(50.0, 0.0, 100.0, 1.0)

    def test_rejects_zero_effectiveness(self):
        with self.assertRaises(ValueError):
            required_neutralization_dwell(50.0, 5.0, 100.0, 0.0)


class TestVerifyPostNeutralization(unittest.TestCase):
    def test_successful_discharge_is_released(self):
        out = verify_post_neutralization([50.0, -50.0], [1.0, 0.5])
        self.assertTrue(out["released_for_measurement"])
        self.assertAlmostEqual(out["magnitude_drop_v"], 49.0)
        self.assertEqual(out["findings"], [])

    def test_step_that_charged_the_coupon_is_flagged(self):
        out = verify_post_neutralization([1.0, 0.5], [50.0, -50.0])
        self.assertFalse(out["released_for_measurement"])
        self.assertTrue(any("charged the coupon" in f for f in out["findings"]))

    def test_spread_that_refuses_to_close_is_flagged(self):
        out = verify_post_neutralization([60.0, -60.0], [4.0, -4.0])
        self.assertFalse(out["released_for_measurement"])
        self.assertTrue(any("spread" in f for f in out["findings"]))
        self.assertGreater(out["magnitude_drop_v"], 0.0)

    def test_before_and_after_states_are_reported(self):
        out = verify_post_neutralization([50.0, -50.0], [1.0, 0.5])
        self.assertEqual(out["before"]["state"], "reject-coupon")
        self.assertEqual(out["after"]["state"], "ready")

    def test_rejects_mismatched_point_counts(self):
        with self.assertRaises(ValueError):
            verify_post_neutralization([1.0, 2.0, 3.0], [1.0, 2.0])

    def test_rejects_empty_after_map(self):
        with self.assertRaises(ValueError):
            verify_post_neutralization([1.0], [])


class TestPlanDischargeSequence(unittest.TestCase):
    def base_plan(self, **kwargs):
        plan = {
            "readings": [50.0, 40.0],
            "relative_permittivity": 3.0,
            "volume_resistivity_ohm_m": 1.0e14,
            "technique": "electron-flood",
            "available_slot_s": 600.0,
        }
        plan.update(kwargs)
        return plan

    def test_ready_coupon_needs_no_dwell(self):
        out = plan_discharge_sequence(self.base_plan(readings=[1.0, 2.0]))
        self.assertEqual(out["state"]["state"], "ready")
        self.assertAlmostEqual(out["required_dwell_s"], 0.0)
        self.assertTrue(out["proceed_to_measurement"])
        self.assertIsNone(out["technique"])

    def test_charged_coupon_gets_a_sized_dwell(self):
        out = plan_discharge_sequence(self.base_plan())
        tau = dielectric_relaxation_time(3.0, 1.0e14)
        expected = (tau / NEUTRALIZATION_TECHNIQUES["electron-flood"]) * math.log(
            50.0 / DEFAULT_MAGNITUDE_LIMIT_V
        )
        self.assertAlmostEqual(out["required_dwell_s"], expected, places=9)
        self.assertTrue(out["fits_available_slot"])
        self.assertFalse(out["proceed_to_measurement"])

    def test_passive_grounding_does_not_fit_the_slot(self):
        out = plan_discharge_sequence(self.base_plan(technique="passive-grounding"))
        self.assertFalse(out["fits_available_slot"])
        self.assertTrue(any("available slot" in f for f in out["findings"]))

    def test_rejected_coupon_short_circuits_the_plan(self):
        out = plan_discharge_sequence(self.base_plan(readings=[-15.0, 15.0]))
        self.assertIsNone(out["required_dwell_s"])
        self.assertIsNone(out["technique"])
        self.assertFalse(out["proceed_to_measurement"])

    def test_findings_carry_both_limit_breaches(self):
        out = plan_discharge_sequence(self.base_plan())
        self.assertTrue(any("magnitude" in f for f in out["findings"]))
        self.assertTrue(any("spread" in f for f in out["findings"]))

    def test_hard_reject_multiple_is_honoured(self):
        limit = DEFAULT_SPREAD_LIMIT_V
        just_under = limit * HARD_REJECT_SPREAD_MULTIPLE - 0.5
        out = plan_discharge_sequence(
            self.base_plan(readings=[0.0, just_under], available_slot_s=1.0e6)
        )
        self.assertEqual(out["state"]["state"], "needs-neutralization")

    def test_rejects_surface_altering_technique(self):
        with self.assertRaises(ValueError):
            plan_discharge_sequence(self.base_plan(technique="thermal-bake"))

    def test_rejects_non_mapping_plan(self):
        with self.assertRaises(ValueError):
            plan_discharge_sequence(["readings"])

    def test_rejects_missing_plan_key(self):
        plan = self.base_plan()
        del plan["technique"]
        with self.assertRaises(ValueError):
            plan_discharge_sequence(plan)

    def test_rejects_zero_available_slot(self):
        with self.assertRaises(ValueError):
            plan_discharge_sequence(self.base_plan(available_slot_s=0.0))

    def test_rejects_invalid_target_magnitude(self):
        with self.assertRaises(ValueError):
            plan_discharge_sequence(self.base_plan(target_magnitude_v=-1.0))

    def test_custom_target_lengthens_the_dwell(self):
        loose = plan_discharge_sequence(self.base_plan(target_magnitude_v=5.0))
        tight = plan_discharge_sequence(self.base_plan(target_magnitude_v=0.5))
        self.assertGreater(tight["required_dwell_s"], loose["required_dwell_s"])


if __name__ == "__main__":
    unittest.main()
