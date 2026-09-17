#!/usr/bin/env python3
"""Contract test for class 2 high voltage and high power provisions (offline)."""

import copy
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_2_high_voltage_applications_logic import (  # noqa: E402
    APPLICATION_NOT_ADMISSIBLE,
    DEFAULT_HIGH_VOLTAGE_POLICY,
    DESIGN_NONCONFORMING,
    ENCLOSURE_FORMS,
    MULTIPACTION_BANDS,
    PASCHEN_AIR_A,
    PASCHEN_AIR_B,
    PROVISIONS_OUTSTANDING,
    PROVISIONS_SATISFIED,
    SURFACE_CONDITIONS,
    assess_class2_high_voltage,
    microwave_power_utilisation,
    multipaction_band,
    multipaction_fd_product_ghz_mm,
    paschen_breakdown_voltage_v,
    paschen_margin,
    required_clearance_mm,
    required_creepage_mm,
    required_provisions,
    surface_shortfalls_mm,
    validate_high_voltage_case,
    validate_high_voltage_policy,
    voltage_utilisation,
)

BASE_CASE = {
    "part_reference": "hv-feedthrough-01",
    "rated_voltage_v": 3000.0,
    "working_voltage_v": 1500.0,
    "electrode_gap_mm": 5.0,
    "ambient_pressure_torr": 760.0,
    "clearance_mm": 5.0,
    "creepage_mm": 8.0,
    "surface_condition": "clean-uncoated",
    "enclosure_form": "vented-enclosure",
    "operates_through_ascent": True,
}

CLEAN_CASE = dict(BASE_CASE)
CLEAN_CASE["provisions_held"] = required_provisions(BASE_CASE)


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    if "provisions_held" not in overrides:
        case["provisions_held"] = required_provisions(case)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(
            validate_high_voltage_policy(None), DEFAULT_HIGH_VOLTAGE_POLICY
        )

    def test_policy_override_is_merged(self):
        merged = validate_high_voltage_policy({"max_voltage_utilisation": 0.4})
        self.assertAlmostEqual(merged["max_voltage_utilisation"], 0.4, places=9)
        self.assertAlmostEqual(
            merged["min_paschen_margin"],
            DEFAULT_HIGH_VOLTAGE_POLICY["min_paschen_margin"],
            places=9,
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"max_voltage": 0.4})

    def test_utilisation_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"max_voltage_utilisation": 1.3})

    def test_a_breakdown_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"min_paschen_margin": 0.5})

    def test_non_boolean_vent_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"require_vent_path": "yes"})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy("default")


class UtilisationTests(unittest.TestCase):
    def test_utilisation_is_working_over_rated(self):
        self.assertAlmostEqual(voltage_utilisation(1500.0, 3000.0), 0.5, places=9)

    def test_working_at_the_rating_is_full_utilisation(self):
        self.assertAlmostEqual(voltage_utilisation(3000.0, 3000.0), 1.0, places=9)

    def test_zero_working_voltage_is_allowed(self):
        self.assertAlmostEqual(voltage_utilisation(0.0, 3000.0), 0.0, places=9)

    def test_zero_rated_voltage_rejected(self):
        with self.assertRaises(ValueError):
            voltage_utilisation(1500.0, 0.0)


class PaschenTests(unittest.TestCase):
    def test_the_curve_collapses_to_its_analytic_minimum(self):
        sustain = math.log(1.0 + 1.0 / 0.01)
        product_at_minimum = math.e / PASCHEN_AIR_A * sustain
        expected = math.e * PASCHEN_AIR_B / PASCHEN_AIR_A * sustain
        self.assertAlmostEqual(
            paschen_breakdown_voltage_v(product_at_minimum, 1.0), expected, places=9
        )

    def test_breakdown_rises_to_the_right_of_the_minimum(self):
        sustain = math.log(1.0 + 1.0 / 0.01)
        product_at_minimum = math.e / PASCHEN_AIR_A * sustain
        at_minimum = paschen_breakdown_voltage_v(product_at_minimum, 1.0)
        far_right = paschen_breakdown_voltage_v(product_at_minimum * 100.0, 1.0)
        self.assertGreater(far_right, at_minimum * 10.0)

    def test_breakdown_rises_again_towards_the_left_asymptote(self):
        sustain = math.log(1.0 + 1.0 / 0.01)
        product_at_minimum = math.e / PASCHEN_AIR_A * sustain
        at_minimum = paschen_breakdown_voltage_v(product_at_minimum, 1.0)
        near_left = paschen_breakdown_voltage_v(sustain / PASCHEN_AIR_A * 1.02, 1.0)
        self.assertGreater(near_left, at_minimum * 5.0)

    def test_a_product_left_of_the_branch_has_no_root(self):
        with self.assertRaises(ValueError):
            paschen_breakdown_voltage_v(1.0e-4, 0.5)

    def test_non_positive_pressure_rejected(self):
        with self.assertRaises(ValueError):
            paschen_breakdown_voltage_v(0.0, 0.5)

    def test_margin_is_breakdown_over_working(self):
        self.assertAlmostEqual(paschen_margin(6000.0, 1500.0), 4.0, places=9)

    def test_margin_against_a_zero_working_voltage_rejected(self):
        with self.assertRaises(ValueError):
            paschen_margin(6000.0, 0.0)


class SurfaceTests(unittest.TestCase):
    def test_clearance_scales_with_the_working_voltage(self):
        self.assertAlmostEqual(required_clearance_mm(1500.0), 1.5, places=9)

    def test_creepage_is_longer_than_clearance_on_a_clean_surface(self):
        self.assertAlmostEqual(
            required_creepage_mm(1500.0, "clean-uncoated"), 3.75, places=9
        )

    def test_a_coated_surface_buys_creepage_back(self):
        self.assertLess(
            required_creepage_mm(1500.0, "conformally-coated"),
            required_creepage_mm(1500.0, "clean-uncoated"),
        )

    def test_a_contaminated_surface_spends_creepage(self):
        self.assertGreater(
            required_creepage_mm(1500.0, "contamination-exposed"),
            required_creepage_mm(1500.0, "clean-uncoated"),
        )

    def test_an_unknown_surface_condition_rejected(self):
        with self.assertRaises(ValueError):
            required_creepage_mm(1500.0, "painted")

    def test_a_built_distance_exactly_on_the_requirement_passes(self):
        shortfalls = surface_shortfalls_mm(1500.0, "clean-uncoated", 1.5, 3.75)
        self.assertTrue(shortfalls["clearance_ok"])
        self.assertTrue(shortfalls["creepage_ok"])
        self.assertAlmostEqual(shortfalls["clearance_shortfall_mm"], 0.0, places=9)

    def test_a_short_clearance_reports_its_shortfall(self):
        shortfalls = surface_shortfalls_mm(1500.0, "clean-uncoated", 1.0, 8.0)
        self.assertFalse(shortfalls["clearance_ok"])
        self.assertAlmostEqual(shortfalls["clearance_shortfall_mm"], 0.5, places=9)

    def test_a_short_creepage_reports_its_shortfall(self):
        shortfalls = surface_shortfalls_mm(1500.0, "clean-uncoated", 5.0, 3.0)
        self.assertFalse(shortfalls["creepage_ok"])
        self.assertAlmostEqual(shortfalls["creepage_shortfall_mm"], 0.75, places=9)

    def test_a_non_positive_built_clearance_rejected(self):
        with self.assertRaises(ValueError):
            surface_shortfalls_mm(1500.0, "clean-uncoated", 0.0, 8.0)


class MultipactionTests(unittest.TestCase):
    def test_the_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(
            multipaction_fd_product_ghz_mm(12.0, 5.0), 60.0, places=9
        )

    def test_a_narrow_gap_at_low_frequency_is_deeply_susceptible(self):
        self.assertEqual(multipaction_band(4.0), "multipaction-deep-susceptibility")

    def test_the_deep_band_edge_belongs_to_the_deep_band(self):
        self.assertEqual(multipaction_band(10.0), "multipaction-deep-susceptibility")

    def test_the_susceptibility_band_edge_belongs_to_that_band(self):
        self.assertEqual(multipaction_band(30.0), "multipaction-susceptibility-band")

    def test_a_wide_gap_at_high_frequency_is_above_the_band(self):
        self.assertEqual(
            multipaction_band(500.0), "multipaction-above-susceptibility-band"
        )

    def test_a_non_positive_product_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_band(0.0)

    def test_a_non_positive_gap_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_fd_product_ghz_mm(12.0, 0.0)

    def test_power_utilisation_is_applied_over_rated(self):
        self.assertAlmostEqual(
            microwave_power_utilisation(100.0, 400.0), 0.25, places=9
        )

    def test_a_zero_rated_peak_power_rejected(self):
        with self.assertRaises(ValueError):
            microwave_power_utilisation(100.0, 0.0)

    def test_every_band_bound_is_reachable(self):
        for bound, name in MULTIPACTION_BANDS:
            probe = bound if math.isfinite(bound) else 1.0e6
            self.assertIn(multipaction_band(probe), [n for _, n in MULTIPACTION_BANDS])


class ProvisionTests(unittest.TestCase):
    def test_a_high_voltage_case_owes_the_core_provisions(self):
        provisions = required_provisions(BASE_CASE)
        self.assertIn("high-voltage-derating-review", provisions)
        self.assertIn(
            "insulation-resistance-and-dielectric-withstanding-test", provisions
        )

    def test_partial_discharge_attaches_above_its_threshold(self):
        self.assertIn("partial-discharge-measurement", required_provisions(BASE_CASE))

    def test_partial_discharge_does_not_attach_below_its_threshold(self):
        provisions = required_provisions(
            dict(BASE_CASE, working_voltage_v=300.0, creepage_mm=8.0)
        )
        self.assertNotIn("partial-discharge-measurement", provisions)

    def test_a_low_voltage_application_owes_nothing_extra(self):
        self.assertEqual(
            required_provisions(dict(BASE_CASE, working_voltage_v=50.0)), ()
        )

    def test_ascent_operation_attaches_corona_inception(self):
        self.assertIn("corona-inception-demonstration", required_provisions(BASE_CASE))

    def test_a_sealed_cavity_attaches_hermeticity_evidence(self):
        provisions = required_provisions(
            dict(BASE_CASE, enclosure_form="hermetically-sealed")
        )
        self.assertIn("cavity-hermeticity-and-fill-gas-demonstration", provisions)

    def test_a_microwave_chain_attaches_multipaction_work(self):
        provisions = required_provisions(
            dict(
                BASE_CASE,
                frequency_ghz=12.0,
                applied_peak_power_w=100.0,
                rated_peak_power_w=400.0,
            )
        )
        self.assertIn("multipaction-analysis", provisions)
        self.assertIn("multipaction-margin-test", provisions)

    def test_a_wide_gap_chain_needs_no_multipaction_margin_test(self):
        provisions = required_provisions(
            dict(
                BASE_CASE,
                electrode_gap_mm=40.0,
                frequency_ghz=12.0,
                applied_peak_power_w=100.0,
                rated_peak_power_w=400.0,
            )
        )
        self.assertIn("multipaction-analysis", provisions)
        self.assertNotIn("multipaction-margin-test", provisions)

    def test_a_microwave_case_missing_its_power_fields_rejected(self):
        with self.assertRaises(ValueError):
            required_provisions(dict(BASE_CASE, frequency_ghz=12.0))


class DispositionTests(unittest.TestCase):
    def test_a_complete_application_is_provisions_satisfied(self):
        result = assess_class2_high_voltage(CLEAN_CASE)
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_provision_is_outstanding(self):
        result = assess_class2_high_voltage(
            _case(provisions_held=["high-voltage-derating-review"])
        )
        self.assertEqual(result["disposition"], PROVISIONS_OUTSTANDING)
        self.assertIn("partial-discharge-measurement", result["outstanding_provisions"])

    def test_a_part_run_above_its_rating_is_not_admissible(self):
        result = assess_class2_high_voltage(_case(working_voltage_v=3500.0))
        self.assertEqual(result["disposition"], APPLICATION_NOT_ADMISSIBLE)
        self.assertFalse(result["admissible"])

    def test_utilisation_exactly_on_the_limit_is_compliant(self):
        result = assess_class2_high_voltage(_case(working_voltage_v=1800.0))
        self.assertAlmostEqual(result["voltage_utilisation"], 0.6, places=9)
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_utilisation_over_the_limit_is_nonconforming(self):
        result = assess_class2_high_voltage(_case(working_voltage_v=2400.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_a_clearance_exactly_on_the_requirement_is_compliant(self):
        result = assess_class2_high_voltage(_case(clearance_mm=1.5))
        self.assertAlmostEqual(result["clearance_shortfall_mm"], 0.0, places=9)
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_a_short_creepage_is_nonconforming(self):
        result = assess_class2_high_voltage(_case(creepage_mm=2.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertGreater(result["creepage_shortfall_mm"], 0.0)

    def test_a_sealed_unvented_cavity_is_nonconforming(self):
        result = assess_class2_high_voltage(_case(enclosure_form="sealed-unvented"))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_policy_may_waive_the_vent_path_requirement(self):
        result = assess_class2_high_voltage(
            _case(enclosure_form="sealed-unvented"), {"require_vent_path": False}
        )
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_a_hard_vacuum_gap_cannot_sustain_a_discharge(self):
        result = assess_class2_high_voltage(_case(ambient_pressure_torr=1.0e-6))
        self.assertFalse(result["gap_sustains_a_discharge"])
        self.assertIsNone(result["breakdown_voltage_v"])

    def test_a_gap_near_the_corona_minimum_is_nonconforming(self):
        result = assess_class2_high_voltage(
            _case(ambient_pressure_torr=1.5, electrode_gap_mm=5.0)
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertLess(result["paschen_margin"], 2.0)

    def test_an_overdriven_microwave_stage_is_nonconforming(self):
        result = assess_class2_high_voltage(
            _case(
                frequency_ghz=12.0,
                applied_peak_power_w=300.0,
                rated_peak_power_w=400.0,
            )
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertAlmostEqual(result["microwave_power_utilisation"], 0.75, places=9)

    def test_a_compliant_microwave_stage_reports_its_band(self):
        result = assess_class2_high_voltage(
            _case(
                frequency_ghz=12.0,
                applied_peak_power_w=100.0,
                rated_peak_power_w=400.0,
            )
        )
        self.assertEqual(result["multipaction_band"], "multipaction-marginal-band")
        self.assertAlmostEqual(
            result["multipaction_fd_product_ghz_mm"], 60.0, places=9
        )

    def test_a_low_voltage_application_carries_no_provisions(self):
        result = assess_class2_high_voltage(_case(working_voltage_v=50.0))
        self.assertFalse(result["high_voltage_application"])
        self.assertEqual(result["required_provisions"], ())
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_inadmissibility_outranks_a_design_finding(self):
        result = assess_class2_high_voltage(
            _case(working_voltage_v=3500.0, creepage_mm=1.0)
        )
        self.assertEqual(result["disposition"], APPLICATION_NOT_ADMISSIBLE)

    def test_a_design_finding_outranks_an_outstanding_provision(self):
        result = assess_class2_high_voltage(
            _case(creepage_mm=2.0, provisions_held=[])
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_a_case_without_a_part_reference_rejected(self):
        case = _case()
        case["part_reference"] = "   "
        with self.assertRaises(ValueError):
            assess_class2_high_voltage(case)

    def test_an_unknown_enclosure_form_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_high_voltage(_case(enclosure_form="potted-block"))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_high_voltage("hv-feedthrough-01")

    def test_case_validation_accepts_the_reference_case(self):
        self.assertIs(validate_high_voltage_case(CLEAN_CASE), CLEAN_CASE)

    def test_every_enclosure_form_is_routable(self):
        for form in ENCLOSURE_FORMS:
            result = assess_class2_high_voltage(
                _case(enclosure_form=form), {"require_vent_path": False}
            )
            self.assertIn(
                result["disposition"], (PROVISIONS_SATISFIED, PROVISIONS_OUTSTANDING)
            )

    def test_every_surface_condition_is_routable(self):
        for condition in SURFACE_CONDITIONS:
            result = assess_class2_high_voltage(_case(surface_condition=condition))
            self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)


if __name__ == "__main__":
    unittest.main()
