#!/usr/bin/env python3
"""Contract test for Class 3 high voltage and high power provisions (offline)."""

import copy
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_3_high_voltage_applications_logic import (  # noqa: E402
    APPLICATION_NOT_ADMISSIBLE,
    DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY,
    DESIGN_NONCONFORMING,
    ENCLOSURE_FORMS,
    MULTIPACTION_BANDS,
    PROVISIONS_OUTSTANDING,
    PROVISIONS_SATISFIED,
    SURFACE_CONDITIONS,
    assess_class3_high_voltage,
    microwave_power_utilisation,
    multipaction_band,
    multipaction_fd_product_ghz_mm,
    outstanding_provisions,
    paschen_breakdown_voltage_v,
    paschen_margin,
    pressure_regime,
    required_clearance_mm,
    required_creepage_mm,
    required_provisions,
    surface_shortfalls_mm,
    validate_high_voltage_case,
    validate_high_voltage_policy,
    voltage_utilisation,
)

BASE_PROVISIONS = [
    "high-voltage-design-review",
    "insulation-coordination-analysis",
    "partial-discharge-measurement",
]

CLEAN_CASE = {
    "working_voltage_v": 800.0,
    "rated_voltage_v": 1500.0,
    "electrode_gap_mm": 3.0,
    "ambient_pressure_pa": 101325.0,
    "clearance_mm": 3.0,
    "creepage_mm": 5.0,
    "surface_condition": "clean-uncoated",
    "enclosure_form": "vented-enclosure",
    "provisions_held": list(BASE_PROVISIONS),
}


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_defaults_are_returned_when_no_policy_is_given(self):
        self.assertEqual(
            validate_high_voltage_policy(), DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY
        )

    def test_an_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"max_altitude_km": 400.0})

    def test_a_utilisation_limit_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"max_voltage_utilisation": 1.4})

    def test_a_partial_discharge_threshold_below_the_hv_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"partial_discharge_threshold_v": 50.0})

    def test_a_thermal_trigger_above_the_power_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy(
                {"thermal_analysis_power_utilisation": 0.9}
            )

    def test_a_non_boolean_vent_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_policy({"require_vent_path": "yes"})

    def test_class_3_allows_more_of_the_rating_than_two_thirds(self):
        self.assertGreater(
            DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY["max_voltage_utilisation"], 0.65
        )


class RegimeTests(unittest.TestCase):
    def test_hard_vacuum_is_the_vacuum_regime(self):
        self.assertEqual(pressure_regime(1.0e-5), "vacuum-regime")

    def test_a_few_hundred_pascals_is_the_critical_band(self):
        self.assertEqual(pressure_regime(500.0), "critical-pressure-band")

    def test_sea_level_is_the_near_ambient_regime(self):
        self.assertEqual(pressure_regime(101325.0), "near-ambient-regime")

    def test_a_pressure_exactly_on_a_regime_edge_takes_that_regime(self):
        self.assertEqual(pressure_regime(1.0e4), "critical-pressure-band")

    def test_a_negative_pressure_is_rejected(self):
        with self.assertRaises(ValueError):
            pressure_regime(-1.0)


class PaschenTests(unittest.TestCase):
    def test_a_gap_at_sea_level_breaks_down_in_the_kilovolts(self):
        self.assertGreater(paschen_breakdown_voltage_v(101325.0, 3.0), 5000.0)

    def test_the_critical_band_breaks_down_far_lower_than_sea_level(self):
        self.assertLess(
            paschen_breakdown_voltage_v(500.0, 3.0),
            paschen_breakdown_voltage_v(101325.0, 3.0),
        )

    def test_below_the_paschen_minimum_no_gas_breakdown_is_reported(self):
        self.assertEqual(paschen_breakdown_voltage_v(1.0e-4, 3.0), math.inf)

    def test_a_zero_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            paschen_breakdown_voltage_v(101325.0, 0.0)

    def test_an_unbounded_breakdown_gives_an_unbounded_margin(self):
        self.assertEqual(paschen_margin(math.inf, 800.0), math.inf)

    def test_the_margin_is_breakdown_over_working(self):
        self.assertAlmostEqual(paschen_margin(1600.0, 800.0), 2.0, places=9)

    def test_a_zero_working_voltage_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            paschen_margin(1600.0, 0.0)


class SurfaceTests(unittest.TestCase):
    def test_clearance_scales_with_the_working_voltage(self):
        self.assertAlmostEqual(required_clearance_mm(2000.0), 2.0, places=9)

    def test_a_coated_surface_needs_less_creepage_than_a_bare_one(self):
        self.assertLess(
            required_creepage_mm(1000.0, "conformally-coated"),
            required_creepage_mm(1000.0, "clean-uncoated"),
        )

    def test_a_contaminated_surface_needs_more_creepage_than_a_bare_one(self):
        self.assertGreater(
            required_creepage_mm(1000.0, "contamination-exposed"),
            required_creepage_mm(1000.0, "clean-uncoated"),
        )

    def test_an_unknown_surface_condition_is_rejected(self):
        with self.assertRaises(ValueError):
            required_creepage_mm(1000.0, "painted")

    def test_a_surface_exactly_on_its_requirement_is_acceptable(self):
        needed = required_creepage_mm(800.0, "clean-uncoated")
        result = surface_shortfalls_mm(800.0, 5.0, needed, "clean-uncoated")
        self.assertTrue(result["creepage_ok"])
        self.assertAlmostEqual(result["creepage_shortfall_mm"], 0.0, places=9)

    def test_a_short_creepage_reports_how_far_it_is_short(self):
        result = surface_shortfalls_mm(800.0, 5.0, 1.0, "clean-uncoated")
        self.assertFalse(result["creepage_ok"])
        self.assertAlmostEqual(result["creepage_shortfall_mm"], 1.0, places=9)

    def test_a_negative_built_clearance_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_shortfalls_mm(800.0, -1.0, 5.0, "clean-uncoated")

    def test_every_catalogued_surface_condition_is_priced(self):
        for condition in SURFACE_CONDITIONS:
            self.assertGreater(required_creepage_mm(1000.0, condition), 0.0)


class MultipactionTests(unittest.TestCase):
    def test_the_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(
            multipaction_fd_product_ghz_mm(2.0, 3.0), 6.0, places=9
        )

    def test_a_small_product_lands_deep_in_the_susceptibility_band(self):
        self.assertEqual(multipaction_band(6.0), "multipaction-deep-susceptibility")

    def test_a_product_exactly_on_a_band_edge_takes_that_band(self):
        self.assertEqual(multipaction_band(10.0), "multipaction-deep-susceptibility")

    def test_a_large_product_sits_above_the_susceptibility_band(self):
        self.assertEqual(
            multipaction_band(500.0), "multipaction-above-susceptibility-band"
        )

    def test_the_bands_are_stated_in_ascending_order(self):
        bounds = [bound for bound, _ in MULTIPACTION_BANDS]
        self.assertEqual(bounds, sorted(bounds))

    def test_a_zero_product_is_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_band(0.0)

    def test_power_utilisation_is_peak_over_rated(self):
        self.assertAlmostEqual(
            microwave_power_utilisation(300.0, 1000.0), 0.3, places=9
        )

    def test_a_zero_rated_power_is_rejected(self):
        with self.assertRaises(ValueError):
            microwave_power_utilisation(300.0, 0.0)


class ProvisionTests(unittest.TestCase):
    def test_a_low_voltage_application_owes_nothing_extra(self):
        owed = required_provisions(_case(working_voltage_v=24.0, creepage_mm=5.0))
        self.assertEqual(owed, ())

    def test_a_voltage_exactly_on_the_threshold_attaches_the_review(self):
        owed = required_provisions(_case(working_voltage_v=100.0))
        self.assertIn("high-voltage-design-review", owed)

    def test_partial_discharge_attaches_above_its_own_threshold(self):
        owed = required_provisions(_case(working_voltage_v=800.0))
        self.assertIn("partial-discharge-measurement", owed)

    def test_the_critical_band_attaches_a_corona_inception_test(self):
        owed = required_provisions(_case(ambient_pressure_pa=500.0))
        self.assertIn("corona-inception-test", owed)

    def test_the_vacuum_regime_attaches_no_corona_test(self):
        owed = required_provisions(_case(ambient_pressure_pa=1.0e-5))
        self.assertNotIn("corona-inception-test", owed)

    def test_a_sealed_cavity_attaches_a_vent_path_analysis(self):
        owed = required_provisions(_case(enclosure_form="sealed-unvented"))
        self.assertIn("vent-path-analysis", owed)

    def test_a_contaminated_surface_attaches_outgassing_data(self):
        owed = required_provisions(
            _case(surface_condition="contamination-exposed", creepage_mm=9.0)
        )
        self.assertIn("insulation-material-outgassing-data", owed)

    def test_a_susceptible_microwave_gap_attaches_analysis_and_test(self):
        owed = required_provisions(
            _case(
                microwave_chain=True,
                frequency_ghz=2.0,
                peak_power_w=300.0,
                rated_peak_power_w=1000.0,
            )
        )
        self.assertIn("multipaction-analysis", owed)
        self.assertIn("multipaction-test", owed)

    def test_a_wide_microwave_gap_attaches_neither(self):
        owed = required_provisions(
            _case(
                microwave_chain=True,
                frequency_ghz=40.0,
                peak_power_w=300.0,
                rated_peak_power_w=1000.0,
            )
        )
        self.assertNotIn("multipaction-analysis", owed)

    def test_a_hard_driven_stage_attaches_a_thermal_analysis(self):
        owed = required_provisions(
            _case(
                microwave_chain=True,
                frequency_ghz=40.0,
                peak_power_w=500.0,
                rated_peak_power_w=1000.0,
            )
        )
        self.assertIn("high-power-thermal-analysis", owed)

    def test_no_provision_is_listed_twice(self):
        owed = required_provisions(_case(ambient_pressure_pa=500.0))
        self.assertEqual(len(owed), len(set(owed)))

    def test_held_provisions_are_subtracted(self):
        self.assertEqual(outstanding_provisions(CLEAN_CASE), ())

    def test_a_missing_provision_is_reported_outstanding(self):
        case = _case(provisions_held=["high-voltage-design-review"])
        self.assertIn("partial-discharge-measurement", outstanding_provisions(case))

    def test_a_non_string_held_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            outstanding_provisions(_case(provisions_held=[7]))


class CaseValidationTests(unittest.TestCase):
    def test_a_missing_field_is_rejected(self):
        case = _case()
        del case["clearance_mm"]
        with self.assertRaises(ValueError):
            validate_high_voltage_case(case)

    def test_an_unknown_enclosure_form_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_case(_case(enclosure_form="potted"))

    def test_a_microwave_case_without_a_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_case(_case(microwave_chain=True))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_high_voltage_case(["working_voltage_v"])

    def test_every_catalogued_enclosure_form_validates(self):
        for form in ENCLOSURE_FORMS:
            self.assertIs(
                validate_high_voltage_case(_case(enclosure_form=form))["enclosure_form"],
                form,
            )


class AssessmentTests(unittest.TestCase):
    def test_the_reference_case_satisfies_its_provisions(self):
        result = assess_class3_high_voltage(CLEAN_CASE)
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)
        self.assertEqual(result["findings"], [])

    def test_a_working_voltage_above_the_rating_is_not_admissible(self):
        result = assess_class3_high_voltage(_case(working_voltage_v=2000.0))
        self.assertEqual(result["disposition"], APPLICATION_NOT_ADMISSIBLE)

    def test_a_peak_power_above_the_rating_is_not_admissible(self):
        result = assess_class3_high_voltage(
            _case(
                microwave_chain=True,
                frequency_ghz=40.0,
                peak_power_w=1400.0,
                rated_peak_power_w=1000.0,
            )
        )
        self.assertEqual(result["disposition"], APPLICATION_NOT_ADMISSIBLE)

    def test_a_utilisation_above_the_class_limit_is_nonconforming(self):
        result = assess_class3_high_voltage(
            _case(working_voltage_v=1400.0, clearance_mm=9.0, creepage_mm=9.0)
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_a_utilisation_exactly_on_the_class_limit_is_not_a_finding(self):
        rated = CLEAN_CASE["rated_voltage_v"]
        working = rated * DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY[
            "max_voltage_utilisation"
        ]
        result = assess_class3_high_voltage(
            _case(working_voltage_v=working, clearance_mm=9.0, creepage_mm=9.0)
        )
        self.assertAlmostEqual(
            result["voltage_utilisation"],
            DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY["max_voltage_utilisation"],
            places=9,
        )
        self.assertNotEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_the_critical_band_turns_a_good_design_nonconforming(self):
        result = assess_class3_high_voltage(_case(ambient_pressure_pa=500.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["paschen_margin_ok"])

    def test_the_vacuum_regime_does_not_run_the_gas_check(self):
        result = assess_class3_high_voltage(
            _case(
                ambient_pressure_pa=1.0e-5,
                provisions_held=list(BASE_PROVISIONS),
            )
        )
        self.assertFalse(result["gas_breakdown_governs"])
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_a_short_creepage_is_a_design_finding(self):
        result = assess_class3_high_voltage(_case(creepage_mm=0.5))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["creepage_ok"])

    def test_a_sealed_cavity_is_a_design_finding(self):
        result = assess_class3_high_voltage(
            _case(
                enclosure_form="sealed-unvented",
                provisions_held=BASE_PROVISIONS + ["vent-path-analysis"],
            )
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["vent_path_ok"])

    def test_policy_can_drop_the_vent_path_requirement(self):
        result = assess_class3_high_voltage(
            _case(
                enclosure_form="sealed-unvented",
                provisions_held=BASE_PROVISIONS + ["vent-path-analysis"],
            ),
            {"require_vent_path": False},
        )
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_a_sound_design_missing_a_provision_is_outstanding(self):
        result = assess_class3_high_voltage(
            _case(provisions_held=["high-voltage-design-review"])
        )
        self.assertEqual(result["disposition"], PROVISIONS_OUTSTANDING)

    def test_a_not_admissible_case_outranks_a_design_finding(self):
        result = assess_class3_high_voltage(
            _case(working_voltage_v=2000.0, creepage_mm=0.1)
        )
        self.assertEqual(result["disposition"], APPLICATION_NOT_ADMISSIBLE)

    def test_a_design_finding_outranks_an_outstanding_provision(self):
        result = assess_class3_high_voltage(
            _case(creepage_mm=0.5, provisions_held=[])
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_the_microwave_band_is_reported_for_a_microwave_chain(self):
        result = assess_class3_high_voltage(
            _case(
                microwave_chain=True,
                frequency_ghz=2.0,
                peak_power_w=300.0,
                rated_peak_power_w=1000.0,
                provisions_held=BASE_PROVISIONS
                + ["multipaction-analysis", "multipaction-test"],
            )
        )
        self.assertEqual(
            result["multipaction_band"], "multipaction-deep-susceptibility"
        )
        self.assertEqual(result["disposition"], PROVISIONS_SATISFIED)

    def test_no_microwave_chain_leaves_the_band_unreported(self):
        result = assess_class3_high_voltage(CLEAN_CASE)
        self.assertIsNone(result["multipaction_band"])


if __name__ == "__main__":
    unittest.main()
