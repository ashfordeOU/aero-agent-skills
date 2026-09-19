#!/usr/bin/env python3
"""Contract test for explosive cutters and actuated valves (offline)."""

import copy
import math
import unittest

from e3311_cutters_explosively_actuated_valves_logic import (
    CUT_MET,
    CUT_NOT_MET,
    DEFAULT_SEVERANCE_POLICY,
    DEVICE_KINDS,
    LEAK_MET,
    LEAK_NOT_MET,
    MEMBER_SECTIONS,
    RAM_MET,
    RAM_NOT_MET,
    VALVE_ACTIONS,
    assess_cutter,
    assess_leak_rate,
    assess_valve,
    delivered_cut_energy_j,
    margin_ratio,
    plan_severance_device,
    required_cut_energy_j,
    shear_area_m2,
    valve_ram_force_n,
    validate_severance_policy,
)

GOOD_CUTTER = {
    "device_kind": "cable-cutter",
    "section": "cable-bundle",
    "strand_count": 19,
    "strand_diameter_m": 0.0008,
    "shear_strength_pa": 400.0e6,
    "blade_travel_m": 0.004,
    "cartridge_energy_j": 120.0,
    "conversion_efficiency": 0.35,
    "anvil_supported": True,
}

WEAK_PIPE_CUTTER = {
    "device_kind": "pipe-cutter",
    "section": "tube",
    "outer_diameter_m": 0.012,
    "wall_thickness_m": 0.0015,
    "shear_strength_pa": 350.0e6,
    "blade_travel_m": 0.010,
    "cartridge_energy_j": 60.0,
    "conversion_efficiency": 0.30,
    "anvil_supported": False,
}

GOOD_VALVE = {
    "device_kind": "explosive-valve",
    "action": "normally-closed-to-open",
    "line_pressure_pa": 22.0e6,
    "seat_diameter_m": 0.006,
    "seal_friction_n": 150.0,
    "delivered_ram_force_n": 2400.0,
    "post_actuation_leak_scc_s": 1.0e-5,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_severance_policy(DEFAULT_SEVERANCE_POLICY),
            DEFAULT_SEVERANCE_POLICY,
        )

    def test_policy_covers_both_valve_actions(self):
        for action in VALVE_ACTIONS:
            self.assertIn(action, DEFAULT_SEVERANCE_POLICY["seal_break_friction_factor"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_severance_policy("default")

    def test_policy_engagement_factor_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_SEVERANCE_POLICY)
        broken["progressive_engagement_factor"] = 1.4
        with self.assertRaises(ValueError):
            validate_severance_policy(broken)

    def test_policy_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_SEVERANCE_POLICY)
        broken["min_cut_energy_margin"] = 0.8
        with self.assertRaises(ValueError):
            validate_severance_policy(broken)

    def test_policy_missing_a_valve_action_rejected(self):
        broken = copy.deepcopy(DEFAULT_SEVERANCE_POLICY)
        del broken["seal_break_friction_factor"]["normally-open-to-closed"]
        with self.assertRaises(ValueError):
            validate_severance_policy(broken)


class ShearAreaTests(unittest.TestCase):
    def test_solid_round_shears_the_full_circle(self):
        self.assertAlmostEqual(
            shear_area_m2("solid-round", outer_diameter_m=0.010),
            math.pi * 0.010 * 0.010 / 4.0,
            places=15,
        )

    def test_a_bundle_shears_its_strands_not_its_envelope(self):
        strands = shear_area_m2(
            "cable-bundle", strand_count=19, strand_diameter_m=0.0008
        )
        envelope = shear_area_m2("solid-round", outer_diameter_m=0.0048)
        self.assertLess(strands, envelope)

    def test_bundle_area_is_the_sum_of_the_strands(self):
        self.assertAlmostEqual(
            shear_area_m2("cable-bundle", strand_count=19, strand_diameter_m=0.0008),
            19 * math.pi * 0.0008 * 0.0008 / 4.0,
            places=15,
        )

    def test_a_tube_shears_an_annulus_not_a_disc(self):
        annulus = shear_area_m2(
            "tube", outer_diameter_m=0.012, wall_thickness_m=0.0015
        )
        disc = shear_area_m2("solid-round", outer_diameter_m=0.012)
        self.assertLess(annulus, disc)

    def test_tube_area_matches_the_outer_minus_inner_circles(self):
        expected = math.pi * (0.012 ** 2 - 0.009 ** 2) / 4.0
        self.assertAlmostEqual(
            shear_area_m2("tube", outer_diameter_m=0.012, wall_thickness_m=0.0015),
            expected,
            places=15,
        )

    def test_a_wall_that_leaves_no_bore_is_rejected(self):
        with self.assertRaises(ValueError):
            shear_area_m2("tube", outer_diameter_m=0.012, wall_thickness_m=0.006)

    def test_a_bundle_without_a_strand_count_is_rejected(self):
        with self.assertRaises(ValueError):
            shear_area_m2("cable-bundle", strand_diameter_m=0.0008)

    def test_a_fractional_strand_count_is_rejected(self):
        with self.assertRaises(ValueError):
            shear_area_m2("cable-bundle", strand_count=19.5, strand_diameter_m=0.0008)

    def test_an_unknown_section_is_rejected(self):
        with self.assertRaises(ValueError):
            shear_area_m2("braided-guess", outer_diameter_m=0.010)

    def test_every_declared_section_resolves_to_an_area(self):
        self.assertEqual(len(MEMBER_SECTIONS), 3)


class CutEnergyTests(unittest.TestCase):
    def test_required_energy_is_strength_times_area_times_travel(self):
        self.assertAlmostEqual(
            required_cut_energy_j(1.0e-5, 400.0e6, 0.004, 0.5), 8.0, places=9
        )

    def test_progressive_engagement_lowers_the_required_energy(self):
        full = required_cut_energy_j(1.0e-5, 400.0e6, 0.004, 1.0)
        partial = required_cut_energy_j(1.0e-5, 400.0e6, 0.004, 0.5)
        self.assertAlmostEqual(full / partial, 2.0, places=9)

    def test_engagement_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_cut_energy_j(1.0e-5, 400.0e6, 0.004, 1.2)

    def test_delivered_energy_applies_the_conversion_efficiency(self):
        self.assertAlmostEqual(delivered_cut_energy_j(120.0, 0.35), 42.0, places=9)

    def test_conversion_efficiency_of_unity_rejected(self):
        with self.assertRaises(ValueError):
            delivered_cut_energy_j(120.0, 1.0)

    def test_margin_is_a_ratio(self):
        self.assertAlmostEqual(margin_ratio(42.0, 14.0), 3.0, places=12)


class ValveForceTests(unittest.TestCase):
    def test_ram_force_carries_pressure_across_the_seat_plus_friction(self):
        expected = 22.0e6 * math.pi * 0.006 * 0.006 / 4.0 + 1.0 * 150.0
        self.assertAlmostEqual(
            valve_ram_force_n(22.0e6, 0.006, 150.0, "normally-open-to-closed"),
            expected,
            places=6,
        )

    def test_breaking_a_seated_seal_costs_more_friction(self):
        closing = valve_ram_force_n(22.0e6, 0.006, 150.0, "normally-open-to-closed")
        opening = valve_ram_force_n(22.0e6, 0.006, 150.0, "normally-closed-to-open")
        self.assertGreater(opening, closing)

    def test_an_unknown_valve_action_is_rejected(self):
        with self.assertRaises(ValueError):
            valve_ram_force_n(22.0e6, 0.006, 150.0, "normally-maybe")

    def test_negative_seal_friction_rejected(self):
        with self.assertRaises(ValueError):
            valve_ram_force_n(22.0e6, 0.006, -150.0, "normally-open-to-closed")

    def test_a_leak_inside_the_allowance_passes(self):
        result = assess_leak_rate(1.0e-5)
        self.assertEqual(result["verdict"], LEAK_MET)

    def test_a_leak_exactly_on_the_allowance_passes(self):
        result = assess_leak_rate(DEFAULT_SEVERANCE_POLICY["max_leak_rate_scc_s"])
        self.assertAlmostEqual(
            result["measured_scc_s"], result["allowance_scc_s"], places=15
        )
        self.assertEqual(result["verdict"], LEAK_MET)

    def test_a_leak_above_the_allowance_fails(self):
        self.assertEqual(assess_leak_rate(1.0e-3)["verdict"], LEAK_NOT_MET)

    def test_a_negative_leak_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_leak_rate(-1.0e-5)


class CutterAssessmentTests(unittest.TestCase):
    def test_good_cutter_is_acceptable(self):
        result = assess_cutter(GOOD_CUTTER)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["energy_verdict"], CUT_MET)
        self.assertEqual(result["findings"], [])

    def test_a_missing_anvil_fails_an_energetic_cutter(self):
        result = assess_cutter(_case(GOOD_CUTTER, anvil_supported=False))
        self.assertEqual(result["energy_verdict"], CUT_MET)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("anvil" in f for f in result["findings"]))

    def test_weak_pipe_cutter_fails_on_energy_and_anvil(self):
        result = assess_cutter(WEAK_PIPE_CUTTER)
        self.assertEqual(result["energy_verdict"], CUT_NOT_MET)
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 2)

    def test_a_cut_margin_exactly_on_the_floor_passes(self):
        area = shear_area_m2("cable-bundle", strand_count=19, strand_diameter_m=0.0008)
        required = required_cut_energy_j(area, 400.0e6, 0.004, 0.5)
        case = _case(
            GOOD_CUTTER,
            cartridge_energy_j=2.0 * required / 0.35,
            conversion_efficiency=0.35,
        )
        result = assess_cutter(case)
        self.assertAlmostEqual(result["cut_energy_margin"], 2.0, places=9)
        self.assertEqual(result["energy_verdict"], CUT_MET)

    def test_a_non_boolean_anvil_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_cutter(_case(GOOD_CUTTER, anvil_supported="yes"))


class ValveAssessmentTests(unittest.TestCase):
    def test_good_valve_is_acceptable(self):
        result = assess_valve(GOOD_VALVE)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["force_verdict"], RAM_MET)
        self.assertEqual(result["leak"]["verdict"], LEAK_MET)

    def test_an_underpowered_ram_is_reported(self):
        result = assess_valve(_case(GOOD_VALVE, delivered_ram_force_n=900.0))
        self.assertEqual(result["force_verdict"], RAM_NOT_MET)
        self.assertFalse(result["acceptable"])

    def test_a_valve_that_moves_but_seeps_is_not_acceptable(self):
        result = assess_valve(_case(GOOD_VALVE, post_actuation_leak_scc_s=2.0e-3))
        self.assertEqual(result["force_verdict"], RAM_MET)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("changed the failure" in f for f in result["findings"]))

    def test_a_missing_leak_rate_leaves_the_seat_undemonstrated(self):
        case = _case(GOOD_VALVE)
        del case["post_actuation_leak_scc_s"]
        result = assess_valve(case)
        self.assertIsNone(result["leak"])
        self.assertFalse(result["acceptable"])

    def test_a_ram_margin_exactly_on_the_floor_passes(self):
        required = valve_ram_force_n(
            22.0e6, 0.006, 150.0, "normally-closed-to-open"
        )
        result = assess_valve(
            _case(GOOD_VALVE, delivered_ram_force_n=2.0 * required)
        )
        self.assertAlmostEqual(result["ram_force_margin"], 2.0, places=9)
        self.assertEqual(result["force_verdict"], RAM_MET)


class PlanTests(unittest.TestCase):
    def test_plan_dispatches_a_cutter_case(self):
        result = plan_severance_device(GOOD_CUTTER)
        self.assertEqual(result["device_kind"], "cable-cutter")
        self.assertEqual(result["verdict"], "severance-acceptable")

    def test_plan_dispatches_a_valve_case(self):
        result = plan_severance_device(GOOD_VALVE)
        self.assertEqual(result["device_kind"], "explosive-valve")
        self.assertEqual(result["verdict"], "severance-acceptable")

    def test_plan_marks_a_weak_cutter_for_rework(self):
        result = plan_severance_device(WEAK_PIPE_CUTTER)
        self.assertEqual(result["verdict"], "severance-rework")
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_a_valve_case_carrying_a_member_section_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_severance_device(_case(GOOD_VALVE, section="solid-round"))

    def test_a_cutter_case_carrying_a_valve_action_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_severance_device(
                _case(GOOD_CUTTER, action="normally-open-to-closed")
            )

    def test_a_pipe_cutter_cannot_declare_a_cable_bundle(self):
        with self.assertRaises(ValueError):
            plan_severance_device(_case(GOOD_CUTTER, device_kind="pipe-cutter"))

    def test_plan_rejects_an_unknown_device_kind(self):
        with self.assertRaises(ValueError):
            plan_severance_device(_case(GOOD_CUTTER, device_kind="scissors"))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_severance_device("a cable cutter")

    def test_every_device_kind_is_reachable(self):
        self.assertEqual(len(DEVICE_KINDS), 3)


if __name__ == "__main__":
    unittest.main()
