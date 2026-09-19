#!/usr/bin/env python3
"""Contract test for explosive pullers and pushers (offline)."""

import copy
import math
import unittest

from e3311_pullers_pushers_logic import (
    DEFAULT_ACTUATOR_POLICY,
    DEVICE_KINDS,
    END_STOP_MET,
    END_STOP_NOT_MET,
    STROKE_MET,
    STROKE_NOT_MET,
    WORK_MET,
    WORK_NOT_MET,
    bore_area_m2,
    delivered_work_j,
    end_stop_energy_j,
    end_stop_velocity_m_s,
    margin_ratio,
    mean_effective_pressure_pa,
    piston_force_n,
    plan_actuator,
    required_stroke_m,
    required_work_j,
    resisting_force_n,
    validate_actuator_policy,
)

GOOD_PULLER = {
    "device_kind": "pin-puller",
    "peak_pressure_pa": 20.0e6,
    "bore_diameter_m": 0.008,
    "available_stroke_m": 0.012,
    "effective_pressure_fraction": 0.45,
    "external_load_n": 300.0,
    "side_load_n": 400.0,
    "friction_coefficient": 0.2,
    "engagement_depth_m": 0.006,
    "misalignment_allowance_m": 0.001,
    "moving_mass_kg": 0.03,
}

WEAK_PUSHER = {
    "device_kind": "pin-pusher",
    "peak_pressure_pa": 6.0e6,
    "bore_diameter_m": 0.006,
    "available_stroke_m": 0.008,
    "effective_pressure_fraction": 0.40,
    "external_load_n": 900.0,
    "side_load_n": 1200.0,
    "friction_coefficient": 0.25,
    "engagement_depth_m": 0.006,
    "misalignment_allowance_m": 0.001,
    "moving_mass_kg": 0.05,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_actuator_policy(DEFAULT_ACTUATOR_POLICY), DEFAULT_ACTUATOR_POLICY
        )

    def test_policy_covers_both_device_kinds(self):
        for kind in DEVICE_KINDS:
            self.assertIn(kind, DEFAULT_ACTUATOR_POLICY["min_work_margin"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_actuator_policy("default")

    def test_policy_missing_a_device_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACTUATOR_POLICY)
        del broken["min_work_margin"]["pin-pusher"]
        with self.assertRaises(ValueError):
            validate_actuator_policy(broken)

    def test_policy_work_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACTUATOR_POLICY)
        broken["min_work_margin"]["pin-puller"] = 0.9
        with self.assertRaises(ValueError):
            validate_actuator_policy(broken)

    def test_policy_stroke_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACTUATOR_POLICY)
        broken["min_stroke_margin"] = 0.5
        with self.assertRaises(ValueError):
            validate_actuator_policy(broken)


class PressureAndForceTests(unittest.TestCase):
    def test_bore_area_follows_the_circle(self):
        self.assertAlmostEqual(
            bore_area_m2(0.010), math.pi * 0.010 * 0.010 / 4.0, places=15
        )

    def test_force_scales_with_the_square_of_the_bore(self):
        small = piston_force_n(10.0e6, 0.005)
        large = piston_force_n(10.0e6, 0.010)
        self.assertAlmostEqual(large / small, 4.0, places=9)

    def test_mean_effective_pressure_is_below_the_peak(self):
        self.assertAlmostEqual(
            mean_effective_pressure_pa(20.0e6, 0.45), 9.0e6, places=3
        )

    def test_a_pressure_fraction_of_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            mean_effective_pressure_pa(20.0e6, 1.0)

    def test_zero_bore_rejected(self):
        with self.assertRaises(ValueError):
            bore_area_m2(0.0)

    def test_non_numeric_pressure_rejected(self):
        with self.assertRaises(ValueError):
            piston_force_n("20 MPa", 0.008)

    def test_delivered_work_is_mean_pressure_times_swept_volume(self):
        expected = 9.0e6 * bore_area_m2(0.008) * 0.012
        self.assertAlmostEqual(
            delivered_work_j(20.0e6, 0.008, 0.012, 0.45), expected, places=9
        )

    def test_peak_pressure_would_overstate_the_delivered_work(self):
        on_mean = delivered_work_j(20.0e6, 0.008, 0.012, 0.45)
        on_peak = piston_force_n(20.0e6, 0.008) * 0.012
        self.assertGreater(on_peak, on_mean)


class ResistanceTests(unittest.TestCase):
    def test_side_load_friction_adds_to_the_external_load(self):
        self.assertAlmostEqual(resisting_force_n(300.0, 400.0, 0.2), 380.0, places=9)

    def test_friction_can_exceed_the_axial_load(self):
        axial_only = resisting_force_n(100.0, 0.0, 0.0)
        with_side = resisting_force_n(100.0, 1000.0, 0.3)
        self.assertGreater(with_side - axial_only, axial_only)

    def test_a_case_with_no_resistance_at_all_is_rejected(self):
        with self.assertRaises(ValueError):
            resisting_force_n(0.0, 0.0, 0.0)

    def test_negative_side_load_rejected(self):
        with self.assertRaises(ValueError):
            resisting_force_n(300.0, -400.0, 0.2)

    def test_required_stroke_adds_the_misalignment_allowance(self):
        self.assertAlmostEqual(required_stroke_m(0.006, 0.001), 0.007, places=12)

    def test_engagement_depth_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            required_stroke_m(0.0, 0.001)

    def test_required_work_is_force_times_needed_stroke(self):
        self.assertAlmostEqual(required_work_j(380.0, 0.007), 2.66, places=9)


class MarginTests(unittest.TestCase):
    def test_margin_is_a_ratio_not_a_difference(self):
        self.assertAlmostEqual(margin_ratio(8.0, 2.0), 4.0, places=12)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            margin_ratio(8.0, 0.0)

    def test_surplus_work_becomes_end_stop_energy(self):
        self.assertAlmostEqual(end_stop_energy_j(8.0, 2.5), 5.5, places=12)

    def test_no_surplus_when_the_load_takes_everything(self):
        self.assertAlmostEqual(end_stop_energy_j(2.5, 8.0), 0.0, places=12)

    def test_impact_velocity_follows_the_kinetic_energy(self):
        self.assertAlmostEqual(end_stop_velocity_m_s(2.0, 0.04), 10.0, places=9)

    def test_zero_moving_mass_rejected(self):
        with self.assertRaises(ValueError):
            end_stop_velocity_m_s(2.0, 0.0)


class PlanTests(unittest.TestCase):
    def test_good_puller_is_acceptable(self):
        result = plan_actuator(GOOD_PULLER)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["verdict"], "actuator-acceptable")
        self.assertEqual(result["work_verdict"], WORK_MET)
        self.assertEqual(result["stroke_verdict"], STROKE_MET)
        self.assertEqual(result["end_stop_verdict"], END_STOP_MET)

    def test_good_puller_reports_its_resisting_force(self):
        result = plan_actuator(GOOD_PULLER)
        self.assertAlmostEqual(result["resisting_force_n"], 380.0, places=9)
        self.assertAlmostEqual(result["required_stroke_m"], 0.007, places=12)

    def test_weak_pusher_fails_work_and_stroke(self):
        result = plan_actuator(WEAK_PUSHER)
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["work_verdict"], WORK_NOT_MET)
        self.assertEqual(result["stroke_verdict"], STROKE_NOT_MET)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_an_oversized_actuator_is_reported_at_the_end_stop(self):
        result = plan_actuator(_case(GOOD_PULLER, bore_diameter_m=0.012))
        self.assertEqual(result["work_verdict"], WORK_MET)
        self.assertEqual(result["end_stop_verdict"], END_STOP_NOT_MET)
        self.assertEqual(result["verdict"], "actuator-rework")

    def test_a_stroke_margin_exactly_on_the_floor_passes(self):
        case = _case(
            GOOD_PULLER,
            engagement_depth_m=0.008,
            misalignment_allowance_m=0.002,
            available_stroke_m=0.015,
        )
        result = plan_actuator(case)
        self.assertAlmostEqual(result["stroke_margin"], 1.5, places=9)
        self.assertEqual(result["stroke_verdict"], STROKE_MET)

    def test_a_work_margin_exactly_on_the_floor_passes(self):
        needed_stroke = required_stroke_m(0.006, 0.001)
        delivered = delivered_work_j(20.0e6, 0.008, 0.012, 0.45)
        target_resistance = delivered / (2.0 * needed_stroke)
        case = _case(
            GOOD_PULLER,
            external_load_n=target_resistance - 0.2 * 400.0,
            side_load_n=400.0,
            friction_coefficient=0.2,
        )
        result = plan_actuator(case)
        self.assertAlmostEqual(result["work_margin"], 2.0, places=9)
        self.assertEqual(result["work_verdict"], WORK_MET)

    def test_the_two_device_kinds_share_the_same_work_floor_by_default(self):
        puller = plan_actuator(GOOD_PULLER)["required_work_margin"]
        pusher = plan_actuator(_case(GOOD_PULLER, device_kind="pin-pusher"))[
            "required_work_margin"
        ]
        self.assertAlmostEqual(puller, pusher, places=12)

    def test_a_missing_moving_mass_leaves_the_impact_velocity_underived(self):
        case = _case(GOOD_PULLER)
        del case["moving_mass_kg"]
        result = plan_actuator(case)
        self.assertIsNone(result["end_stop_velocity_m_s"])
        self.assertTrue(any("impact velocity" in f for f in result["findings"]))

    def test_a_tighter_policy_can_fail_a_passing_actuator(self):
        policy = copy.deepcopy(DEFAULT_ACTUATOR_POLICY)
        policy["min_work_margin"]["pin-puller"] = 6.0
        result = plan_actuator(GOOD_PULLER, policy)
        self.assertFalse(result["acceptable"])

    def test_plan_rejects_an_unknown_device_kind(self):
        with self.assertRaises(ValueError):
            plan_actuator(_case(GOOD_PULLER, device_kind="spring-plunger"))

    def test_plan_rejects_a_pressure_fraction_of_unity(self):
        with self.assertRaises(ValueError):
            plan_actuator(_case(GOOD_PULLER, effective_pressure_fraction=1.0))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_actuator("a pin puller")

    def test_plan_rejects_a_missing_engagement_depth(self):
        case = _case(GOOD_PULLER)
        del case["engagement_depth_m"]
        with self.assertRaises(ValueError):
            plan_actuator(case)


if __name__ == "__main__":
    unittest.main()
