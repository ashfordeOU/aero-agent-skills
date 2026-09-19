"""Contract tests for the clauses 4.4.3 to 4.4.5 end-of-life design logic."""

import math
import unittest

from e31_lifetime_degradation_pmp_eee_constraints_logic import (
    DEFAULT_CONDENSABLE_LIMIT_PERCENT,
    DEFAULT_MASS_LOSS_LIMIT_PERCENT,
    DERATING_TOLERANCE_K,
    SOLAR_CONSTANT_W_M2,
    absorbed_power_growth_w,
    absorptance_emittance_ratio,
    age_surface,
    aged_absorptance,
    aged_emittance,
    assess_lifetime_constraints,
    grade_part,
    screen_material,
    usable_part_limit_k,
    validate_unit_property,
)

# A white-paint radiator: low absorptance at delivery, high emittance, and an
# absorptance that roughly doubles over a long ultraviolet exposure.
RADIATOR = {
    "name": "radiator-white-paint",
    "alpha_bol": 0.20,
    "epsilon_bol": 0.88,
    "delta_alpha_saturated": 0.20,
    "dose_constant_esh": 4000.0,
    "exposure_esh": 0.0,
    "area_m2": 1.5,
    "incident_flux_w_m2": 1361.0,
}


def radiator(**overrides):
    surface = dict(RADIATOR)
    surface.update(overrides)
    return surface


class UnitPropertyTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertAlmostEqual(validate_unit_property(0.2, "alpha"), 0.2)

    def test_unity_is_allowed(self):
        self.assertAlmostEqual(validate_unit_property(1.0, "epsilon"), 1.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit_property(0.0, "epsilon")

    def test_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit_property(1.2, "alpha")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit_property(True, "alpha")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit_property(float("nan"), "alpha")


class AgedAbsorptanceTests(unittest.TestCase):
    def test_zero_dose_leaves_the_delivered_value(self):
        self.assertAlmostEqual(aged_absorptance(0.20, 0.20, 0.0, 4000.0), 0.20)

    def test_one_dose_constant_reaches_the_exponential_fraction(self):
        value = aged_absorptance(0.20, 0.20, 4000.0, 4000.0)
        self.assertAlmostEqual(value, 0.20 + 0.20 * (1.0 - math.exp(-1.0)), places=12)

    def test_ageing_saturates_at_long_dose(self):
        value = aged_absorptance(0.20, 0.20, 400000.0, 4000.0)
        self.assertAlmostEqual(value, 0.40, places=9)

    def test_saturation_is_monotone_in_dose(self):
        early = aged_absorptance(0.20, 0.20, 1000.0, 4000.0)
        late = aged_absorptance(0.20, 0.20, 8000.0, 4000.0)
        self.assertGreater(late, early)

    def test_linear_extrapolation_would_overstate_late_life(self):
        early = aged_absorptance(0.20, 0.20, 1000.0, 4000.0)
        linear_at_eight = 0.20 + (early - 0.20) * 8.0
        actual = aged_absorptance(0.20, 0.20, 8000.0, 4000.0)
        self.assertGreater(linear_at_eight, actual)

    def test_non_physical_asymptote_rejected(self):
        with self.assertRaises(ValueError):
            aged_absorptance(0.90, 0.20, 1000.0, 4000.0)

    def test_negative_increment_rejected(self):
        with self.assertRaises(ValueError):
            aged_absorptance(0.20, -0.05, 1000.0, 4000.0)

    def test_zero_dose_constant_rejected(self):
        with self.assertRaises(ValueError):
            aged_absorptance(0.20, 0.20, 1000.0, 0.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            aged_absorptance(0.20, 0.20, -1.0, 4000.0)


class AgedEmittanceTests(unittest.TestCase):
    def test_zero_fluence_leaves_the_delivered_value(self):
        self.assertAlmostEqual(aged_emittance(0.88, -1.0e-22, 0.0), 0.88)

    def test_erosion_can_lower_emittance(self):
        value = aged_emittance(0.88, -1.0e-23, 2.0e21)
        self.assertAlmostEqual(value, 0.88 - 0.02, places=12)

    def test_emittance_may_also_rise(self):
        value = aged_emittance(0.80, 1.0e-23, 1.0e21)
        self.assertAlmostEqual(value, 0.81, places=12)

    def test_erosion_past_zero_rejected(self):
        with self.assertRaises(ValueError):
            aged_emittance(0.10, -1.0e-22, 2.0e21)

    def test_rise_past_unity_rejected(self):
        with self.assertRaises(ValueError):
            aged_emittance(0.95, 1.0e-22, 2.0e21)

    def test_negative_fluence_rejected(self):
        with self.assertRaises(ValueError):
            aged_emittance(0.88, -1.0e-23, -1.0)


class RatioAndPowerTests(unittest.TestCase):
    def test_ratio_is_the_quotient(self):
        self.assertAlmostEqual(absorptance_emittance_ratio(0.44, 0.88), 0.5)

    def test_ratio_rejects_zero_emittance(self):
        with self.assertRaises(ValueError):
            absorptance_emittance_ratio(0.44, 0.0)

    def test_absorbed_growth_is_area_times_flux_times_delta(self):
        value = absorbed_power_growth_w(2.0, 1000.0, 0.20, 0.30)
        self.assertAlmostEqual(value, 200.0, places=9)

    def test_absorbed_growth_is_zero_for_a_stable_coating(self):
        self.assertAlmostEqual(absorbed_power_growth_w(2.0, 1000.0, 0.20, 0.20), 0.0)

    def test_improving_coating_rejected(self):
        with self.assertRaises(ValueError):
            absorbed_power_growth_w(2.0, 1000.0, 0.30, 0.20)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            absorbed_power_growth_w(0.0, 1000.0, 0.20, 0.30)


class AgeSurfaceTests(unittest.TestCase):
    def test_undosed_surface_keeps_its_ratio(self):
        record = age_surface(radiator())
        self.assertAlmostEqual(record["ratio_eol"], record["ratio_bol"], places=12)
        self.assertAlmostEqual(record["ratio_growth"], 0.0, places=12)

    def test_dosed_surface_grows_its_ratio(self):
        record = age_surface(radiator(exposure_esh=40000.0))
        self.assertGreater(record["ratio_growth"], 0.2)

    def test_absorbed_power_growth_is_reported(self):
        record = age_surface(radiator(exposure_esh=400000.0))
        self.assertAlmostEqual(
            record["absorbed_power_growth_w"], 1.5 * 1361.0 * 0.2, places=6
        )

    def test_default_flux_is_the_solar_constant(self):
        surface = radiator(exposure_esh=400000.0)
        del surface["incident_flux_w_m2"]
        record = age_surface(surface)
        self.assertAlmostEqual(
            record["absorbed_power_growth_w"], 1.5 * SOLAR_CONSTANT_W_M2 * 0.2, places=6
        )

    def test_surface_without_area_reports_no_power_growth(self):
        surface = radiator(exposure_esh=4000.0)
        del surface["area_m2"]
        self.assertIsNone(age_surface(surface)["absorbed_power_growth_w"])

    def test_emittance_loss_accelerates_ratio_growth(self):
        stable = age_surface(radiator(exposure_esh=4000.0))
        eroded = age_surface(
            radiator(
                exposure_esh=4000.0,
                delta_epsilon_per_fluence=-1.0e-23,
                atomic_oxygen_fluence=2.0e21,
            )
        )
        self.assertGreater(eroded["ratio_growth"], stable["ratio_growth"])

    def test_missing_key_rejected(self):
        surface = radiator()
        del surface["dose_constant_esh"]
        with self.assertRaises(ValueError):
            age_surface(surface)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            age_surface(radiator(name="  "))

    def test_non_mapping_surface_rejected(self):
        with self.assertRaises(ValueError):
            age_surface(["radiator"])


class MaterialScreeningTests(unittest.TestCase):
    def test_clean_material_is_compliant(self):
        result = screen_material({
            "name": "adhesive-a",
            "vacuum_exposed": True,
            "mass_loss_percent": 0.4,
            "condensable_percent": 0.02,
        })
        self.assertEqual(result["category"], "compliant")
        self.assertTrue(result["acceptable"])

    def test_mass_loss_breach_is_screened_out(self):
        result = screen_material({
            "name": "adhesive-b",
            "vacuum_exposed": True,
            "mass_loss_percent": 1.4,
            "condensable_percent": 0.02,
        })
        self.assertEqual(result["category"], "screened-out")
        self.assertIn("mass loss", result["finding"])

    def test_condensable_breach_alone_is_screened_out(self):
        result = screen_material({
            "name": "tape-c",
            "vacuum_exposed": True,
            "mass_loss_percent": 0.4,
            "condensable_percent": 0.25,
        })
        self.assertFalse(result["acceptable"])
        self.assertIn("condensable", result["finding"])

    def test_material_exactly_on_both_limits_passes(self):
        result = screen_material({
            "name": "paint-d",
            "vacuum_exposed": True,
            "mass_loss_percent": DEFAULT_MASS_LOSS_LIMIT_PERCENT,
            "condensable_percent": DEFAULT_CONDENSABLE_LIMIT_PERCENT,
        })
        self.assertTrue(result["acceptable"])

    def test_tighter_programme_limit_can_screen_it_out(self):
        result = screen_material(
            {
                "name": "paint-d",
                "vacuum_exposed": True,
                "mass_loss_percent": 0.8,
                "condensable_percent": 0.02,
            },
            mass_loss_limit_percent=0.5,
        )
        self.assertEqual(result["category"], "screened-out")

    def test_justified_exemption_is_acceptable(self):
        result = screen_material({
            "name": "internal-potting",
            "vacuum_exposed": False,
            "exemption_reason": "sealed inside a pressurised housing",
        })
        self.assertEqual(result["category"], "exempt")
        self.assertTrue(result["acceptable"])

    def test_unjustified_exemption_is_a_finding(self):
        result = screen_material({"name": "unknown-shim", "vacuum_exposed": False})
        self.assertFalse(result["acceptable"])
        self.assertIn("no recorded reason", result["finding"])

    def test_exposed_material_without_data_rejected(self):
        with self.assertRaises(ValueError):
            screen_material({"name": "mystery", "vacuum_exposed": True})

    def test_non_boolean_exposure_rejected(self):
        with self.assertRaises(ValueError):
            screen_material({"name": "mystery", "vacuum_exposed": "yes"})

    def test_negative_mass_loss_rejected(self):
        with self.assertRaises(ValueError):
            screen_material({
                "name": "mystery",
                "vacuum_exposed": True,
                "mass_loss_percent": -0.1,
                "condensable_percent": 0.01,
            })


class PartDeratingTests(unittest.TestCase):
    def test_usable_limit_subtracts_the_margin(self):
        self.assertAlmostEqual(usable_part_limit_k(398.15, 10.0), 388.15, places=9)

    def test_zero_margin_keeps_the_rated_limit(self):
        self.assertAlmostEqual(usable_part_limit_k(398.15, 0.0), 398.15, places=9)

    def test_margin_consuming_the_limit_rejected(self):
        with self.assertRaises(ValueError):
            usable_part_limit_k(300.0, 300.0)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            usable_part_limit_k(398.15, -5.0)

    def test_part_below_the_usable_limit_passes(self):
        result = grade_part({
            "name": "dc-dc-converter",
            "rated_limit_k": 398.15,
            "predicted_hot_eol_k": 370.0,
            "derating_margin_k": 10.0,
        })
        self.assertTrue(result["acceptable"])
        self.assertIsNone(result["finding"])

    def test_part_exactly_on_the_usable_limit_passes(self):
        result = grade_part({
            "name": "dc-dc-converter",
            "rated_limit_k": 398.15,
            "predicted_hot_eol_k": 388.15,
            "derating_margin_k": 10.0,
        })
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["exceedance_k"], 0.0, places=9)

    def test_part_over_the_usable_limit_is_a_finding(self):
        result = grade_part({
            "name": "power-fet",
            "rated_limit_k": 398.15,
            "predicted_hot_eol_k": 395.0,
            "derating_margin_k": 10.0,
        })
        self.assertFalse(result["acceptable"])
        self.assertIn("usable limit", result["finding"])

    def test_grading_against_the_rated_value_would_have_passed_it(self):
        part = {
            "name": "power-fet",
            "rated_limit_k": 398.15,
            "predicted_hot_eol_k": 395.0,
            "derating_margin_k": 10.0,
        }
        self.assertFalse(grade_part(part)["acceptable"])
        part_no_margin = dict(part, derating_margin_k=0.0)
        self.assertTrue(grade_part(part_no_margin)["acceptable"])

    def test_default_margin_applies_when_the_part_declares_none(self):
        part = {
            "name": "oscillator",
            "rated_limit_k": 358.15,
            "predicted_hot_eol_k": 350.0,
        }
        self.assertTrue(grade_part(part)["acceptable"])
        self.assertFalse(grade_part(part, default_derating_margin_k=15.0)["acceptable"])

    def test_tolerance_is_tight(self):
        self.assertLess(DERATING_TOLERANCE_K, 1.0e-6)

    def test_non_positive_prediction_rejected(self):
        with self.assertRaises(ValueError):
            grade_part({
                "name": "oscillator",
                "rated_limit_k": 358.15,
                "predicted_hot_eol_k": 0.0,
            })


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "surfaces": [radiator(exposure_esh=40000.0)],
            "materials": [{
                "name": "adhesive-a",
                "vacuum_exposed": True,
                "mass_loss_percent": 0.4,
                "condensable_percent": 0.02,
            }],
            "parts": [{
                "name": "dc-dc-converter",
                "rated_limit_k": 398.15,
                "predicted_hot_eol_k": 370.0,
                "derating_margin_k": 10.0,
            }],
        }
        spec.update(overrides)
        return spec

    def test_clean_design_is_compliant(self):
        result = assess_lifetime_constraints(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_aged_surface_is_reported(self):
        result = assess_lifetime_constraints(self._spec())
        self.assertGreater(result["surfaces"][0]["alpha_eol"], 0.20)

    def test_total_absorbed_growth_sums_the_surfaces(self):
        spec = self._spec(surfaces=[
            radiator(exposure_esh=400000.0),
            radiator(name="second-radiator", exposure_esh=400000.0, area_m2=1.0),
        ])
        result = assess_lifetime_constraints(spec)
        self.assertAlmostEqual(
            result["absorbed_power_growth_w"], 2.5 * 1361.0 * 0.2, places=6
        )

    def test_ratio_growth_allowance_can_fail_the_design(self):
        result = assess_lifetime_constraints(self._spec(max_ratio_growth=0.01))
        self.assertFalse(result["compliant"])
        self.assertIn("absorptance-to-emittance", result["findings"][0])

    def test_ratio_growth_exactly_on_the_allowance_passes(self):
        spec = self._spec()
        growth = assess_lifetime_constraints(spec)["surfaces"][0]["ratio_growth"]
        graded = assess_lifetime_constraints(self._spec(max_ratio_growth=growth))
        self.assertTrue(graded["compliant"])

    def test_material_finding_reaches_the_verdict(self):
        spec = self._spec(materials=[{
            "name": "tape-c",
            "vacuum_exposed": True,
            "mass_loss_percent": 0.4,
            "condensable_percent": 0.25,
        }])
        result = assess_lifetime_constraints(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_part_finding_reaches_the_verdict(self):
        spec = self._spec(parts=[{
            "name": "power-fet",
            "rated_limit_k": 398.15,
            "predicted_hot_eol_k": 395.0,
            "derating_margin_k": 10.0,
        }])
        result = assess_lifetime_constraints(spec)
        self.assertFalse(result["compliant"])

    def test_default_derating_margin_flows_to_the_parts(self):
        spec = self._spec(
            parts=[{
                "name": "oscillator",
                "rated_limit_k": 358.15,
                "predicted_hot_eol_k": 350.0,
            }],
            default_derating_margin_k=15.0,
        )
        self.assertFalse(assess_lifetime_constraints(spec)["compliant"])

    def test_empty_surface_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifetime_constraints(self._spec(surfaces=[]))

    def test_missing_section_rejected(self):
        spec = self._spec()
        del spec["materials"]
        with self.assertRaises(ValueError):
            assess_lifetime_constraints(spec)

    def test_non_sequence_section_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifetime_constraints(self._spec(parts={"name": "x"}))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifetime_constraints("surfaces")


if __name__ == "__main__":
    unittest.main()
