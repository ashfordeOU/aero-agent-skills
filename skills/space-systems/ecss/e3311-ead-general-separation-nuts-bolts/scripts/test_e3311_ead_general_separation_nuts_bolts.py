#!/usr/bin/env python3
"""Contract test for EAD general, separation nuts and bolts (offline)."""

import copy
import unittest

from e3311_ead_general_separation_nuts_bolts_logic import (
    DEFAULT_EAD_POLICY,
    DEVICE_KINDS,
    FUNCTION_MET,
    FUNCTION_NOT_MET,
    assess_containment,
    assess_redundancy,
    delivered_work_j,
    function_margin,
    plan_ead_assessment,
    preload_from_torque_n,
    required_release_work_j,
    validate_ead_policy,
)

GOOD_NUT = {
    "device_kind": "separation-nut",
    "torque_nm": 30.0,
    "nut_factor": 0.2,
    "bolt_diameter_m": 0.008,
    "stroke_m": 0.004,
    "friction_coefficient": 0.15,
    "cartridge_energy_j": 120.0,
    "conversion_efficiency": 0.35,
    "initiator_count": 2,
    "firing_circuit_count": 2,
    "fragments_contained": True,
    "gas_path_sealed": True,
    "release_time_ms": 8.0,
}

WEAK_BOLT = {
    "device_kind": "explosive-bolt",
    "preload_n": 25000.0,
    "stroke_m": 0.003,
    "notch_fracture_energy_j": 40.0,
    "cartridge_energy_j": 100.0,
    "conversion_efficiency": 0.30,
    "initiator_count": 1,
    "firing_circuit_count": 1,
    "fragments_contained": False,
    "gas_path_sealed": False,
    "release_time_ms": 35.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_ead_policy(DEFAULT_EAD_POLICY), DEFAULT_EAD_POLICY)

    def test_policy_covers_every_device_kind(self):
        for kind in DEVICE_KINDS:
            self.assertIn(kind, DEFAULT_EAD_POLICY["min_function_margin"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_ead_policy("default")

    def test_policy_missing_a_device_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_EAD_POLICY)
        del broken["min_function_margin"]["explosive-bolt"]
        with self.assertRaises(ValueError):
            validate_ead_policy(broken)

    def test_policy_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_EAD_POLICY)
        broken["min_function_margin"]["generic-ead"] = 0.8
        with self.assertRaises(ValueError):
            validate_ead_policy(broken)

    def test_policy_with_fractional_initiator_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_EAD_POLICY)
        broken["min_initiator_count"] = 1.5
        with self.assertRaises(ValueError):
            validate_ead_policy(broken)


class PreloadTests(unittest.TestCase):
    def test_preload_follows_the_torque_relation(self):
        self.assertAlmostEqual(
            preload_from_torque_n(30.0, 0.2, 0.008), 18750.0, places=6
        )

    def test_a_higher_nut_factor_lowers_the_recovered_preload(self):
        low = preload_from_torque_n(30.0, 0.15, 0.008)
        high = preload_from_torque_n(30.0, 0.25, 0.008)
        self.assertLess(high, low)

    def test_zero_nut_factor_rejected(self):
        with self.assertRaises(ValueError):
            preload_from_torque_n(30.0, 0.0, 0.008)

    def test_negative_diameter_rejected(self):
        with self.assertRaises(ValueError):
            preload_from_torque_n(30.0, 0.2, -0.008)

    def test_non_numeric_torque_rejected(self):
        with self.assertRaises(ValueError):
            preload_from_torque_n("30 Nm", 0.2, 0.008)


class RequiredWorkTests(unittest.TestCase):
    def test_separation_nut_pays_friction_work_against_the_preload(self):
        self.assertAlmostEqual(
            required_release_work_j(
                "separation-nut", 10000.0, 0.004, friction_coefficient=0.15
            ),
            6.0,
            places=9,
        )

    def test_explosive_bolt_pays_fracture_plus_released_strain_energy(self):
        self.assertAlmostEqual(
            required_release_work_j(
                "explosive-bolt", 20000.0, 0.003, notch_fracture_energy_j=40.0
            ),
            70.0,
            places=9,
        )

    def test_generic_device_pays_direct_work_against_the_load(self):
        self.assertAlmostEqual(
            required_release_work_j("generic-ead", 5000.0, 0.002), 10.0, places=9
        )

    def test_the_two_device_models_do_not_agree_on_the_same_joint(self):
        nut = required_release_work_j(
            "separation-nut", 20000.0, 0.003, friction_coefficient=0.15
        )
        bolt = required_release_work_j(
            "explosive-bolt", 20000.0, 0.003, notch_fracture_energy_j=40.0
        )
        self.assertGreater(bolt, nut)

    def test_separation_nut_without_a_friction_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            required_release_work_j("separation-nut", 10000.0, 0.004)

    def test_explosive_bolt_without_a_fracture_energy_rejected(self):
        with self.assertRaises(ValueError):
            required_release_work_j("explosive-bolt", 20000.0, 0.003)

    def test_unknown_device_kind_rejected(self):
        with self.assertRaises(ValueError):
            required_release_work_j("frangible-wish", 10000.0, 0.004)

    def test_zero_stroke_rejected(self):
        with self.assertRaises(ValueError):
            required_release_work_j("generic-ead", 5000.0, 0.0)


class DeliveredWorkTests(unittest.TestCase):
    def test_delivered_work_applies_the_conversion_efficiency(self):
        self.assertAlmostEqual(delivered_work_j(120.0, 0.35), 42.0, places=9)

    def test_efficiency_of_unity_rejected(self):
        with self.assertRaises(ValueError):
            delivered_work_j(120.0, 1.0)

    def test_negative_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            delivered_work_j(120.0, -0.35)

    def test_margin_is_a_ratio(self):
        self.assertAlmostEqual(function_margin(42.0, 14.0), 3.0, places=9)

    def test_zero_required_work_rejected(self):
        with self.assertRaises(ValueError):
            function_margin(42.0, 0.0)


class RedundancyTests(unittest.TestCase):
    def test_dual_initiators_on_dual_circuits_are_redundant(self):
        result = assess_redundancy(2, 2)
        self.assertTrue(result["redundant"])
        self.assertEqual(result["findings"], [])

    def test_a_single_initiator_is_a_single_point_of_failure(self):
        result = assess_redundancy(1, 2)
        self.assertFalse(result["redundant"])
        self.assertTrue(any("initiator" in f for f in result["findings"]))

    def test_two_initiators_on_one_circuit_are_not_redundant(self):
        result = assess_redundancy(2, 1)
        self.assertFalse(result["redundant"])
        self.assertTrue(any("firing circuit" in f for f in result["findings"]))

    def test_fractional_initiator_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_redundancy(1.5, 2)

    def test_negative_circuit_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_redundancy(2, -1)


class ContainmentTests(unittest.TestCase):
    def test_a_contained_sealed_device_is_acceptable(self):
        result = assess_containment(True, True)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_released_fragments_are_reported(self):
        result = assess_containment(False, True)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("debris" in f for f in result["findings"]))

    def test_an_unsealed_gas_path_is_reported(self):
        result = assess_containment(True, False)
        self.assertTrue(any("vent" in f for f in result["findings"]))

    def test_a_non_boolean_containment_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_containment("yes", True)


class PlanTests(unittest.TestCase):
    def test_good_separation_nut_is_acceptable(self):
        result = plan_ead_assessment(GOOD_NUT)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["verdict"], "ead-acceptable")
        self.assertEqual(result["margin_verdict"], FUNCTION_MET)

    def test_a_torque_derived_preload_is_flagged_as_an_estimate(self):
        result = plan_ead_assessment(GOOD_NUT)
        self.assertEqual(result["preload_basis"], "torque-derived")
        self.assertTrue(any("nut factor" in f for f in result["findings"]))

    def test_a_declared_preload_is_used_as_given(self):
        case = _case(GOOD_NUT, preload_n=10000.0)
        result = plan_ead_assessment(case)
        self.assertEqual(result["preload_basis"], "declared")
        self.assertAlmostEqual(result["preload_n"], 10000.0, places=9)

    def test_weak_bolt_fails_on_every_axis(self):
        result = plan_ead_assessment(WEAK_BOLT)
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["margin_verdict"], FUNCTION_NOT_MET)
        self.assertFalse(result["redundancy"]["redundant"])
        self.assertFalse(result["containment"]["acceptable"])
        self.assertFalse(result["release_time_met"])
        self.assertGreaterEqual(len(result["findings"]), 5)

    def test_a_margin_exactly_on_the_floor_passes(self):
        case = _case(
            GOOD_NUT,
            preload_n=10000.0,
            stroke_m=0.004,
            friction_coefficient=0.15,
            cartridge_energy_j=30.0,
            conversion_efficiency=0.4,
        )
        result = plan_ead_assessment(case)
        self.assertAlmostEqual(result["function_margin"], 2.0, places=9)
        self.assertEqual(result["margin_verdict"], FUNCTION_MET)

    def test_a_release_time_exactly_on_the_allowance_passes(self):
        result = plan_ead_assessment(_case(GOOD_NUT, release_time_ms=20.0))
        self.assertTrue(result["release_time_met"])

    def test_a_missing_release_time_leaves_the_sequence_undemonstrated(self):
        case = _case(GOOD_NUT)
        del case["release_time_ms"]
        result = plan_ead_assessment(case)
        self.assertIsNone(result["release_time_met"])
        self.assertFalse(result["acceptable"])

    def test_a_working_device_that_vents_is_still_rework(self):
        result = plan_ead_assessment(_case(GOOD_NUT, gas_path_sealed=False))
        self.assertEqual(result["margin_verdict"], FUNCTION_MET)
        self.assertEqual(result["verdict"], "ead-rework")

    def test_a_generic_device_carries_a_lower_floor(self):
        nut_floor = DEFAULT_EAD_POLICY["min_function_margin"]["separation-nut"]
        generic_floor = DEFAULT_EAD_POLICY["min_function_margin"]["generic-ead"]
        self.assertGreater(nut_floor, generic_floor)

    def test_plan_rejects_an_unknown_device_kind(self):
        with self.assertRaises(ValueError):
            plan_ead_assessment(_case(GOOD_NUT, device_kind="shape-charge-guess"))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_ead_assessment("a separation nut")

    def test_plan_rejects_a_case_with_neither_preload_nor_torque(self):
        case = _case(GOOD_NUT)
        del case["torque_nm"]
        with self.assertRaises(ValueError):
            plan_ead_assessment(case)


if __name__ == "__main__":
    unittest.main()
