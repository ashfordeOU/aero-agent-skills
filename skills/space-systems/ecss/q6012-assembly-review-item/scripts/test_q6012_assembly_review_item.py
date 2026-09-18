#!/usr/bin/env python3
"""Contract test for the microwave die assembly review item (offline)."""

import copy
import unittest

from q6012_assembly_review_item_logic import (
    ATTACH_MISMATCH_ALLOWANCE_PPM,
    DIE_ATTACH_METHODS,
    VERDICT_ACTIONED,
    VERDICT_CLOSED,
    VERDICT_REJECTED,
    assess_attach_stress,
    assess_interconnect,
    assess_thermal_path,
    attach_mismatch_allowance_ppm,
    bond_wire_count_required,
    derated_junction_limit_c,
    die_attach_thermal_resistance_k_per_w,
    expansion_mismatch_ppm,
    junction_temperature_c,
    review_assembly_item,
)

REFERENCE_CASE = {
    "integration_state": "module-integration-defined",
    "die_attach_method": "eutectic-die-attach",
    "die_cte_ppm_per_k": 5.7,
    "carrier_cte_ppm_per_k": 7.0,
    "delta_t_k": 100.0,
    "case_temperature_c": 70.0,
    "dissipated_power_w": 5.0,
    "bondline_thickness_m": 25.0e-6,
    "conductivity_w_per_m_k": 50.0,
    "attached_area_m2": 4.0e-6,
    "spreading_rth_k_per_w": 2.0,
    "rated_max_junction_c": 175.0,
    "total_current_a": 1.2,
    "per_wire_rating_a": 0.8,
    "derating_factor": 0.5,
    "provided_wire_count": 4,
}


def _case(**overrides):
    case = copy.deepcopy(REFERENCE_CASE)
    case.update(overrides)
    return case


class ExpansionMismatchTests(unittest.TestCase):
    def test_mismatch_is_the_magnitude_of_the_difference(self):
        self.assertAlmostEqual(
            expansion_mismatch_ppm(5.7, 7.0, 100.0), 130.0, places=9
        )

    def test_mismatch_does_not_depend_on_which_side_expands_more(self):
        self.assertAlmostEqual(
            expansion_mismatch_ppm(7.0, 5.7, 100.0),
            expansion_mismatch_ppm(5.7, 7.0, 100.0),
            places=9,
        )

    def test_mismatch_scales_with_the_temperature_swing(self):
        narrow = expansion_mismatch_ppm(5.7, 7.0, 50.0)
        wide = expansion_mismatch_ppm(5.7, 7.0, 150.0)
        self.assertAlmostEqual(wide, 3.0 * narrow, places=9)

    def test_zero_temperature_swing_rejected(self):
        with self.assertRaises(ValueError):
            expansion_mismatch_ppm(5.7, 7.0, 0.0)

    def test_negative_die_expansion_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            expansion_mismatch_ppm(-5.7, 7.0, 100.0)

    def test_non_numeric_carrier_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            expansion_mismatch_ppm(5.7, "7 ppm", 100.0)


class AllowanceTests(unittest.TestCase):
    def test_allowance_table_covers_every_attach_method(self):
        for method in DIE_ATTACH_METHODS:
            self.assertIn(method, ATTACH_MISMATCH_ALLOWANCE_PPM)

    def test_compliant_media_absorb_more_than_rigid_media(self):
        self.assertGreater(
            attach_mismatch_allowance_ppm("conductive-epoxy-die-attach"),
            attach_mismatch_allowance_ppm("eutectic-die-attach"),
        )

    def test_unknown_attach_method_rejected(self):
        with self.assertRaises(ValueError):
            attach_mismatch_allowance_ppm("glued-on")

    def test_allowance_table_missing_a_method_rejected(self):
        broken = dict(ATTACH_MISMATCH_ALLOWANCE_PPM)
        del broken["solder-die-attach"]
        with self.assertRaises(ValueError):
            attach_mismatch_allowance_ppm("eutectic-die-attach", broken)

    def test_non_mapping_allowance_table_rejected(self):
        with self.assertRaises(ValueError):
            attach_mismatch_allowance_ppm("eutectic-die-attach", 300.0)


class AttachStressTests(unittest.TestCase):
    def test_mismatch_inside_the_allowance_is_accepted(self):
        result = assess_attach_stress("eutectic-die-attach", 5.7, 7.0, 100.0)
        self.assertEqual(result["status"], "attach-mismatch-within-allowance")
        self.assertTrue(result["within_allowance"])
        self.assertEqual(result["findings"], [])

    def test_mismatch_exactly_on_the_allowance_is_accepted(self):
        # 8.7 - 5.7 does not evaluate to exactly 3.0 ppm/K, so the product
        # misses the 300 ppm allowance by a few units in the last place and a
        # strict comparison would decide the case on representation error.
        result = assess_attach_stress("eutectic-die-attach", 5.7, 8.7, 100.0)
        self.assertNotEqual(result["mismatch_ppm"], 300.0)
        self.assertAlmostEqual(result["mismatch_ppm"], 300.0, places=9)
        self.assertTrue(result["within_allowance"])
        self.assertEqual(result["status"], "attach-mismatch-within-allowance")

    def test_mismatch_beyond_the_allowance_without_a_case_is_unsupported(self):
        result = assess_attach_stress("eutectic-die-attach", 5.7, 17.0, 100.0)
        self.assertEqual(result["status"], "attach-mismatch-unsupported")
        self.assertFalse(result["within_allowance"])
        self.assertTrue(any("no joint stress case" in f for f in result["findings"]))

    def test_mismatch_beyond_the_allowance_with_a_case_is_covered(self):
        result = assess_attach_stress(
            "eutectic-die-attach", 5.7, 17.0, 100.0, "TN-0042 joint stress"
        )
        self.assertEqual(result["status"], "attach-mismatch-covered-by-analysis")
        self.assertTrue(any("TN-0042" in f for f in result["findings"]))


class ThermalPathTests(unittest.TestCase):
    def test_resistance_is_thickness_over_the_conductance(self):
        self.assertAlmostEqual(
            die_attach_thermal_resistance_k_per_w(25.0e-6, 50.0, 4.0e-6),
            0.125,
            places=9,
        )

    def test_a_thicker_bondline_raises_the_resistance(self):
        thin = die_attach_thermal_resistance_k_per_w(10.0e-6, 50.0, 4.0e-6)
        thick = die_attach_thermal_resistance_k_per_w(40.0e-6, 50.0, 4.0e-6)
        self.assertGreater(thick, thin)

    def test_zero_attached_area_rejected(self):
        with self.assertRaises(ValueError):
            die_attach_thermal_resistance_k_per_w(25.0e-6, 50.0, 0.0)

    def test_junction_temperature_adds_the_dissipation_rise(self):
        self.assertAlmostEqual(
            junction_temperature_c(70.0, 5.0, 2.125), 80.625, places=9
        )

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(70.0, -5.0, 2.125)

    def test_derated_limit_subtracts_the_programme_margin(self):
        self.assertAlmostEqual(derated_junction_limit_c(175.0, 20.0), 155.0, places=9)

    def test_reference_thermal_path_has_adequate_margin(self):
        result = assess_thermal_path(
            70.0, 5.0, 25.0e-6, 50.0, 4.0e-6, 175.0, 20.0, 2.0
        )
        self.assertEqual(result["status"], "junction-margin-adequate")
        self.assertAlmostEqual(result["junction_temperature_c"], 80.625, places=9)
        self.assertAlmostEqual(result["margin_k"], 74.375, places=9)

    def test_thin_margin_is_flagged_without_being_a_breach(self):
        result = assess_thermal_path(
            140.0, 5.0, 25.0e-6, 50.0, 4.0e-6, 175.0, 20.0, 2.0
        )
        self.assertEqual(result["status"], "junction-margin-thin")
        self.assertGreater(result["margin_k"], 0.0)

    def test_junction_above_the_derated_limit_is_a_breach(self):
        result = assess_thermal_path(
            150.0, 10.0, 25.0e-6, 50.0, 4.0e-6, 175.0, 20.0, 2.0
        )
        self.assertEqual(result["status"], "junction-over-derated-limit")
        self.assertLess(result["margin_k"], 0.0)

    def test_junction_exactly_on_the_derated_limit_is_not_a_breach(self):
        result = assess_thermal_path(
            120.0, 10.0, 25.0e-6, 50.0, 4.0e-6, 175.0, 20.0, 3.375
        )
        self.assertAlmostEqual(result["margin_k"], 0.0, places=9)
        self.assertEqual(result["status"], "junction-margin-thin")

    def test_negative_spreading_resistance_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_path(
                70.0, 5.0, 25.0e-6, 50.0, 4.0e-6, 175.0, 20.0, -2.0
            )


class InterconnectTests(unittest.TestCase):
    def test_wire_count_rounds_a_partial_wire_up(self):
        self.assertEqual(bond_wire_count_required(1.3, 0.8, 0.5), 4)

    def test_wire_count_on_an_exact_boundary_does_not_round_up(self):
        # 1.2 / 0.4 evaluates one unit in the last place below 3.0.
        self.assertEqual(bond_wire_count_required(1.2, 0.8, 0.5), 3)

    def test_zero_current_needs_no_wire(self):
        self.assertEqual(bond_wire_count_required(0.0, 0.8, 0.5), 0)

    def test_tighter_derating_demands_more_wires(self):
        loose = bond_wire_count_required(1.3, 0.8, 0.8)
        tight = bond_wire_count_required(1.3, 0.8, 0.25)
        self.assertGreater(tight, loose)

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            bond_wire_count_required(1.2, 0.8, 1.4)

    def test_zero_per_wire_rating_rejected(self):
        with self.assertRaises(ValueError):
            bond_wire_count_required(1.2, 0.0, 0.5)

    def test_layout_with_a_spare_wire_is_adequate(self):
        result = assess_interconnect(1.2, 0.8, 4, 0.5)
        self.assertEqual(result["status"], "interconnect-adequate")
        self.assertEqual(result["required_wire_count"], 3)

    def test_layout_exactly_on_the_demand_is_flagged(self):
        result = assess_interconnect(1.2, 0.8, 3, 0.5)
        self.assertEqual(result["status"], "interconnect-without-spare")
        self.assertTrue(any("redundant" in f for f in result["findings"]))

    def test_layout_below_the_demand_is_under_provisioned(self):
        result = assess_interconnect(1.2, 0.8, 2, 0.5)
        self.assertEqual(result["status"], "interconnect-under-provisioned")

    def test_fractional_wire_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_interconnect(1.2, 0.8, 3.5, 0.5)

    def test_negative_wire_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_interconnect(1.2, 0.8, -1, 0.5)


class ReviewItemTests(unittest.TestCase):
    def test_reference_case_closes_the_item(self):
        result = review_assembly_item(REFERENCE_CASE)
        self.assertEqual(result["verdict"], VERDICT_CLOSED)
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["findings"], [])

    def test_undefined_module_integration_rejects_the_item(self):
        result = review_assembly_item(
            _case(integration_state="module-integration-undefined")
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(any("not defined" in f for f in result["findings"]))

    def test_partial_module_integration_leaves_an_action(self):
        result = review_assembly_item(
            _case(integration_state="module-integration-partial")
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("integration" in a for a in result["actions"]))

    def test_unsupported_attach_mismatch_rejects_the_item(self):
        result = review_assembly_item(_case(carrier_cte_ppm_per_k=17.0))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["attach"]["status"], "attach-mismatch-unsupported")

    def test_a_referenced_stress_case_downgrades_the_mismatch_to_an_action(self):
        result = review_assembly_item(
            _case(
                carrier_cte_ppm_per_k=17.0,
                joint_stress_analysis_ref="TN-0042 joint stress",
            )
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("qualification evidence" in a for a in result["actions"]))

    def test_over_temperature_junction_rejects_the_item(self):
        result = review_assembly_item(
            _case(case_temperature_c=150.0, dissipated_power_w=10.0)
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["thermal"]["status"], "junction-over-derated-limit")

    def test_under_provisioned_interconnect_rejects_the_item(self):
        result = review_assembly_item(_case(provided_wire_count=2))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_no_spare_wire_leaves_an_action(self):
        result = review_assembly_item(_case(provided_wire_count=3))
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            review_assembly_item("eutectic-die-attach")

    def test_unknown_integration_state_rejected(self):
        with self.assertRaises(ValueError):
            review_assembly_item(_case(integration_state="probably-fine"))

    def test_missing_attach_method_rejected(self):
        case = _case()
        del case["die_attach_method"]
        with self.assertRaises(ValueError):
            review_assembly_item(case)


if __name__ == "__main__":
    unittest.main()
