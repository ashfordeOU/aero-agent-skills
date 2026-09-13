#!/usr/bin/env python3
"""Gate 3 contract test for e2001-incident-electron-dose-limits.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_incident_electron_dose_limits.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2001_incident_electron_dose_limits_logic import (  # noqa: E402
    CAUTION_FRACTION,
    COUPON_CATEGORIES,
    MAX_LANDING_ENERGY_EV,
    accumulated_spot_dose,
    allowable_spot_dose,
    assess_incident_dose_plan,
    categorize_dose_margin,
    fresh_spots_required,
    incident_charge_density,
    is_within_allowance,
    landing_energy_derating,
    max_dwell_time,
    max_points_per_spot,
    spots_available_on_coupon,
    validate_beam_settings,
)


def beam(current=10.0, dwell=1.0, spot=1.0, energy=1000.0):
    return {
        "beam_current_na": current,
        "dwell_time_s": dwell,
        "spot_area_mm2": spot,
        "landing_energy_ev": energy,
    }


class TestValidateBeamSettings(unittest.TestCase):
    def test_happy_path_returns_floats(self):
        out = validate_beam_settings(beam())
        self.assertEqual(sorted(out), [
            "beam_current_na", "dwell_time_s", "landing_energy_ev", "spot_area_mm2"
        ])
        for value in out.values():
            self.assertIsInstance(value, float)

    def test_integer_inputs_are_normalized(self):
        out = validate_beam_settings(beam(current=5, dwell=2, spot=3, energy=400))
        self.assertAlmostEqual(out["beam_current_na"], 5.0)
        self.assertAlmostEqual(out["landing_energy_ev"], 400.0)

    def test_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(["not", "a", "mapping"])

    def test_rejects_missing_key(self):
        settings = beam()
        del settings["dwell_time_s"]
        with self.assertRaises(ValueError):
            validate_beam_settings(settings)

    def test_rejects_zero_current(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(current=0.0))

    def test_rejects_negative_dwell(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(dwell=-1.0))

    def test_rejects_non_numeric_spot_area(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(spot="wide"))

    def test_rejects_boolean_current(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(current=True))

    def test_rejects_non_finite_dwell(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(dwell=float("inf")))

    def test_rejects_energy_below_band(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(energy=0.5))

    def test_rejects_energy_above_band(self):
        with self.assertRaises(ValueError):
            validate_beam_settings(beam(energy=MAX_LANDING_ENERGY_EV + 1.0))


class TestChargeDensity(unittest.TestCase):
    def test_single_point_dose(self):
        # 10 nA * 1 s over 1 mm^2 -> 1.0 uC/cm^2
        self.assertAlmostEqual(incident_charge_density(beam()), 1.0)

    def test_dose_scales_linearly_with_dwell(self):
        self.assertAlmostEqual(incident_charge_density(beam(dwell=2.5)), 2.5)

    def test_dose_scales_inversely_with_spot_area(self):
        self.assertAlmostEqual(incident_charge_density(beam(spot=4.0)), 0.25)

    def test_dose_scales_linearly_with_current(self):
        self.assertAlmostEqual(incident_charge_density(beam(current=2.0)), 0.2)

    def test_accumulated_dose_over_points(self):
        self.assertAlmostEqual(accumulated_spot_dose(beam(), 12), 12.0)

    def test_accumulated_dose_rejects_zero_points(self):
        with self.assertRaises(ValueError):
            accumulated_spot_dose(beam(), 0)

    def test_accumulated_dose_rejects_boolean_points(self):
        with self.assertRaises(ValueError):
            accumulated_spot_dose(beam(), True)

    def test_accumulated_dose_rejects_float_points(self):
        with self.assertRaises(ValueError):
            accumulated_spot_dose(beam(), 3.5)


class TestLandingEnergyDerating(unittest.TestCase):
    def test_shallow_band_is_halved(self):
        self.assertAlmostEqual(landing_energy_derating(30.0), 0.5)

    def test_lower_mid_band(self):
        self.assertAlmostEqual(landing_energy_derating(50.0), 0.75)
        self.assertAlmostEqual(landing_energy_derating(199.9), 0.75)

    def test_full_allowance_band(self):
        self.assertAlmostEqual(landing_energy_derating(200.0), 1.0)
        self.assertAlmostEqual(landing_energy_derating(2000.0), 1.0)

    def test_implantation_band_is_derated(self):
        self.assertAlmostEqual(landing_energy_derating(2000.1), 0.8)
        self.assertAlmostEqual(landing_energy_derating(4500.0), 0.8)

    def test_rejects_zero_energy(self):
        with self.assertRaises(ValueError):
            landing_energy_derating(0.0)

    def test_rejects_energy_above_band(self):
        with self.assertRaises(ValueError):
            landing_energy_derating(MAX_LANDING_ENERGY_EV + 10.0)


class TestAllowableSpotDose(unittest.TestCase):
    def test_grounded_metal_full_band(self):
        self.assertAlmostEqual(
            allowable_spot_dose("grounded-metal", 1000.0),
            COUPON_CATEGORIES["grounded-metal"],
        )

    def test_floating_dielectric_is_most_restrictive(self):
        self.assertLess(
            allowable_spot_dose("floating-dielectric", 1000.0),
            allowable_spot_dose("rear-grounded-dielectric", 1000.0),
        )

    def test_derating_is_applied(self):
        self.assertAlmostEqual(allowable_spot_dose("coated-conductor", 30.0), 1.0)

    def test_category_is_case_and_space_insensitive(self):
        self.assertAlmostEqual(
            allowable_spot_dose("  Grounded-Metal ", 1000.0), 5.0
        )

    def test_rejects_unknown_category(self):
        with self.assertRaises(ValueError):
            allowable_spot_dose("anodized-mystery", 1000.0)

    def test_rejects_empty_category(self):
        with self.assertRaises(ValueError):
            allowable_spot_dose("   ", 1000.0)

    def test_rejects_non_string_category(self):
        with self.assertRaises(ValueError):
            allowable_spot_dose(7, 1000.0)


class TestDoseMarginCategorization(unittest.TestCase):
    def test_well_below_is_compliant(self):
        self.assertEqual(categorize_dose_margin(1.0, 5.0), "compliant")

    def test_inside_caution_band_is_marginal(self):
        self.assertEqual(categorize_dose_margin(4.5, 5.0), "marginal")

    def test_above_allowance_is_exceeded(self):
        self.assertEqual(categorize_dose_margin(5.5, 5.0), "exceeded")

    def test_exactly_at_allowance_is_not_an_exceedance(self):
        self.assertTrue(is_within_allowance(5.0, 5.0))
        self.assertEqual(categorize_dose_margin(5.0, 5.0), "marginal")

    def test_just_above_allowance_is_an_exceedance(self):
        self.assertFalse(is_within_allowance(5.01, 5.0))

    def test_is_within_allowance_rejects_zero_allowance(self):
        with self.assertRaises(ValueError):
            is_within_allowance(1.0, 0.0)

    def test_exactly_at_caution_edge_is_compliant(self):
        self.assertEqual(
            categorize_dose_margin(5.0 * CAUTION_FRACTION, 5.0), "compliant"
        )

    def test_float_sum_at_allowance_edge_is_absorbed(self):
        # 0.1 + 0.2 lands a few ULPs above the exact 0.3 uC/cm^2 allowance;
        # that is binary representation error, not an engineering
        # exceedance, so the comparison absorbs it and the limit stays put.
        accumulated = 0.1 + 0.2
        self.assertGreater(accumulated, 0.3)
        self.assertTrue(is_within_allowance(accumulated, 0.3))
        self.assertEqual(categorize_dose_margin(accumulated, 0.3), "marginal")

    def test_rejects_zero_dose(self):
        with self.assertRaises(ValueError):
            categorize_dose_margin(0.0, 5.0)

    def test_rejects_negative_allowance(self):
        with self.assertRaises(ValueError):
            categorize_dose_margin(1.0, -5.0)


class TestCorrectiveNumbers(unittest.TestCase):
    def test_max_dwell_time_for_single_point(self):
        self.assertAlmostEqual(max_dwell_time(beam(), 5.0, 1), 5.0)

    def test_max_dwell_time_shrinks_with_point_count(self):
        self.assertAlmostEqual(max_dwell_time(beam(), 5.0, 10), 0.5)

    def test_max_dwell_time_rejects_zero_points(self):
        with self.assertRaises(ValueError):
            max_dwell_time(beam(), 5.0, 0)

    def test_max_dwell_time_rejects_zero_allowance(self):
        with self.assertRaises(ValueError):
            max_dwell_time(beam(), 0.0, 4)

    def test_max_points_per_spot_exact(self):
        self.assertEqual(max_points_per_spot(beam(), 5.0), 5)

    def test_max_points_per_spot_recovers_representation_error(self):
        # 0.9 / 0.3 evaluates just under 3.0 in binary floating point; the
        # third point is physically inside the allowance and is kept.
        settings = beam(current=3.0, dwell=1.0, spot=1.0)
        self.assertAlmostEqual(incident_charge_density(settings), 0.3)
        self.assertEqual(max_points_per_spot(settings, 0.9), 3)

    def test_max_points_per_spot_zero_when_one_point_exceeds(self):
        settings = beam(current=100.0, dwell=1.0, spot=1.0)
        self.assertEqual(max_points_per_spot(settings, 5.0), 0)

    def test_fresh_spots_rounds_up(self):
        self.assertEqual(fresh_spots_required(41, 5), 9)

    def test_fresh_spots_exact_division(self):
        self.assertEqual(fresh_spots_required(40, 5), 8)

    def test_fresh_spots_single_spot(self):
        self.assertEqual(fresh_spots_required(3, 5), 1)

    def test_fresh_spots_rejects_zero_allowed(self):
        with self.assertRaises(ValueError):
            fresh_spots_required(40, 0)

    def test_fresh_spots_rejects_negative_allowed(self):
        with self.assertRaises(ValueError):
            fresh_spots_required(40, -2)

    def test_fresh_spots_rejects_non_integer_allowed(self):
        with self.assertRaises(ValueError):
            fresh_spots_required(40, 2.5)

    def test_fresh_spots_rejects_zero_total(self):
        with self.assertRaises(ValueError):
            fresh_spots_required(0, 5)


class TestCouponCapacity(unittest.TestCase):
    def test_spots_available_default_packing(self):
        self.assertEqual(spots_available_on_coupon(400.0, 1.0), 200)

    def test_spots_available_full_packing(self):
        self.assertEqual(spots_available_on_coupon(400.0, 1.0, 1.0), 400)

    def test_spots_available_rejects_packing_above_one(self):
        with self.assertRaises(ValueError):
            spots_available_on_coupon(400.0, 1.0, 1.5)

    def test_spots_available_rejects_zero_packing(self):
        with self.assertRaises(ValueError):
            spots_available_on_coupon(400.0, 1.0, 0.0)

    def test_spots_available_rejects_spot_larger_than_coupon(self):
        with self.assertRaises(ValueError):
            spots_available_on_coupon(2.0, 5.0)


class TestAssessIncidentDosePlan(unittest.TestCase):
    def base_plan(self, **kwargs):
        plan = {
            "coupon_category": "grounded-metal",
            "beam": beam(current=1.0, dwell=0.5, spot=1.0, energy=800.0),
            "points_per_spot": 20,
            "total_points": 80,
            "coupon_area_mm2": 400.0,
        }
        plan.update(kwargs)
        return plan

    def test_compliant_plan_is_acceptable(self):
        report = self.base_plan()
        out = assess_incident_dose_plan(report)
        self.assertAlmostEqual(out["per_point_dose_uc_cm2"], 0.05)
        self.assertAlmostEqual(out["accumulated_spot_dose_uc_cm2"], 1.0)
        self.assertAlmostEqual(out["allowance_uc_cm2"], 5.0)
        self.assertEqual(out["status"], "compliant")
        self.assertTrue(out["acceptable"])
        self.assertEqual(out["findings"], [])

    def test_derating_factor_is_reported(self):
        out = assess_incident_dose_plan(
            self.base_plan(beam=beam(current=1.0, dwell=0.5, spot=1.0, energy=30.0))
        )
        self.assertAlmostEqual(out["derating_factor"], 0.5)
        self.assertAlmostEqual(out["allowance_uc_cm2"], 2.5)

    def test_fresh_spot_count_is_derived(self):
        out = assess_incident_dose_plan(self.base_plan())
        self.assertEqual(out["max_points_per_spot"], 100)
        self.assertEqual(out["fresh_spots_required"], 1)
        self.assertEqual(out["fresh_spots_available"], 200)

    def test_exceeded_dose_raises_a_finding(self):
        out = assess_incident_dose_plan(
            self.base_plan(
                coupon_category="floating-dielectric",
                beam=beam(current=1.0, dwell=0.5, spot=1.0, energy=800.0),
            )
        )
        self.assertEqual(out["status"], "exceeded")
        self.assertFalse(out["acceptable"])
        self.assertTrue(any("exceeds allowance" in f for f in out["findings"]))

    def test_single_point_exceedance_reports_no_spot_count(self):
        out = assess_incident_dose_plan(
            self.base_plan(
                coupon_category="floating-dielectric",
                beam=beam(current=100.0, dwell=1.0, spot=1.0, energy=800.0),
            )
        )
        self.assertEqual(out["max_points_per_spot"], 0)
        self.assertIsNone(out["fresh_spots_required"])
        self.assertTrue(
            any("single measurement point" in f for f in out["findings"])
        )

    def test_coupon_too_small_for_required_spots(self):
        out = assess_incident_dose_plan(
            self.base_plan(
                coupon_category="rear-grounded-dielectric",
                beam=beam(current=1.0, dwell=0.5, spot=4.0, energy=800.0),
                points_per_spot=10,
                total_points=400,
                coupon_area_mm2=40.0,
            )
        )
        self.assertTrue(any("fresh spots" in f for f in out["findings"]))
        self.assertFalse(out["acceptable"])

    def test_max_dwell_time_is_reported(self):
        out = assess_incident_dose_plan(self.base_plan())
        self.assertAlmostEqual(out["max_dwell_time_s"], 2.5)

    def test_rejects_non_mapping_plan(self):
        with self.assertRaises(ValueError):
            assess_incident_dose_plan("plan")

    def test_rejects_missing_plan_key(self):
        plan = self.base_plan()
        del plan["coupon_area_mm2"]
        with self.assertRaises(ValueError):
            assess_incident_dose_plan(plan)

    def test_rejects_total_points_below_points_per_spot(self):
        with self.assertRaises(ValueError):
            assess_incident_dose_plan(
                self.base_plan(points_per_spot=20, total_points=5)
            )

    def test_rejects_unknown_category_in_plan(self):
        with self.assertRaises(ValueError):
            assess_incident_dose_plan(self.base_plan(coupon_category="kapton-ish"))

    def test_rejects_invalid_beam_in_plan(self):
        with self.assertRaises(ValueError):
            assess_incident_dose_plan(self.base_plan(beam=beam(current=-1.0)))


if __name__ == "__main__":
    unittest.main()
