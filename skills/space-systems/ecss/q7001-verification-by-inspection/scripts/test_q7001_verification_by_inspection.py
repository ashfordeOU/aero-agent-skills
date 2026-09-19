"""Contract tests for the ECSS-Q-ST-70-01C inspection-verification logic."""

import math
import unittest

from q7001_verification_by_inspection_logic import (
    MIN_DARK_ADAPTATION_MIN,
    MIN_UV_IRRADIANCE_W_PER_M2,
    REFERENCE_ILLUMINANCE_LUX,
    angle_derating,
    assess_inspection,
    can_substantiate,
    dark_adaptation_ok,
    detectable_size_um,
    grade_inspection,
    illuminance_derating,
    inspected_fraction,
    inspection_duration_min,
    resolvable_particle_um,
    uv_band_ok,
    uv_irradiance_ok,
)


class ResolvableSizeTests(unittest.TestCase):
    def test_matches_the_chord_formula(self):
        expected = 2.0 * 300.0 * math.tan(math.radians(1.0 / 60.0) / 2.0) * 1000.0
        self.assertAlmostEqual(resolvable_particle_um(300.0, 1.0), expected, places=9)

    def test_size_grows_with_distance(self):
        near = resolvable_particle_um(300.0, 1.0)
        far = resolvable_particle_um(600.0, 1.0)
        self.assertAlmostEqual(far, 2.0 * near, places=6)

    def test_sharper_acuity_resolves_smaller(self):
        coarse = resolvable_particle_um(300.0, 2.0)
        fine = resolvable_particle_um(300.0, 1.0)
        self.assertLess(fine, coarse)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_particle_um(0.0, 1.0)

    def test_negative_acuity_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_particle_um(300.0, -1.0)

    def test_acuity_beyond_a_degree_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_particle_um(300.0, 90.0)

    def test_boolean_distance_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_particle_um(True, 1.0)


class DeratingTests(unittest.TestCase):
    def test_reference_illuminance_is_not_derated(self):
        self.assertAlmostEqual(
            illuminance_derating(REFERENCE_ILLUMINANCE_LUX), 1.0, places=9
        )

    def test_brighter_than_reference_is_not_credited(self):
        self.assertAlmostEqual(illuminance_derating(5000.0), 1.0, places=9)

    def test_quarter_illuminance_doubles_the_size(self):
        self.assertAlmostEqual(
            illuminance_derating(REFERENCE_ILLUMINANCE_LUX / 4.0), 2.0, places=9
        )

    def test_zero_illuminance_rejected(self):
        with self.assertRaises(ValueError):
            illuminance_derating(0.0)

    def test_normal_viewing_is_not_derated(self):
        self.assertAlmostEqual(angle_derating(0.0), 1.0, places=9)

    def test_sixty_degrees_doubles_the_size(self):
        self.assertAlmostEqual(angle_derating(60.0), 2.0, places=9)

    def test_grazing_angle_rejected(self):
        with self.assertRaises(ValueError):
            angle_derating(90.0)

    def test_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            angle_derating(-10.0)

    def test_detectable_size_combines_both_deratings(self):
        base = resolvable_particle_um(300.0, 1.0)
        combined = detectable_size_um(300.0, 1.0, REFERENCE_ILLUMINANCE_LUX / 4.0, 60.0)
        self.assertAlmostEqual(combined, base * 4.0, places=6)


class BlackLightTests(unittest.TestCase):
    def test_wavelength_inside_the_band(self):
        self.assertTrue(uv_band_ok(365.0))

    def test_wavelength_below_the_band(self):
        self.assertFalse(uv_band_ok(254.0))

    def test_wavelength_above_the_band(self):
        self.assertFalse(uv_band_ok(420.0))

    def test_zero_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            uv_band_ok(0.0)

    def test_irradiance_at_the_minimum_is_accepted(self):
        self.assertTrue(uv_irradiance_ok(MIN_UV_IRRADIANCE_W_PER_M2))

    def test_irradiance_below_the_minimum_is_refused(self):
        self.assertFalse(uv_irradiance_ok(MIN_UV_IRRADIANCE_W_PER_M2 / 2.0))

    def test_negative_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            uv_irradiance_ok(-1.0)

    def test_dark_adaptation_at_the_minimum_is_accepted(self):
        self.assertTrue(dark_adaptation_ok(MIN_DARK_ADAPTATION_MIN))

    def test_short_dark_adaptation_is_refused(self):
        self.assertFalse(dark_adaptation_ok(1.0))

    def test_negative_dark_adaptation_rejected(self):
        with self.assertRaises(ValueError):
            dark_adaptation_ok(-2.0)


class CoverageTests(unittest.TestCase):
    def test_fraction_is_the_ratio(self):
        self.assertAlmostEqual(inspected_fraction(0.5, 2.0), 0.25, places=9)

    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(inspected_fraction(2.0, 2.0), 1.0, places=9)

    def test_inspected_area_above_the_total_rejected(self):
        with self.assertRaises(ValueError):
            inspected_fraction(3.0, 2.0)

    def test_zero_total_area_rejected(self):
        with self.assertRaises(ValueError):
            inspected_fraction(0.0, 0.0)

    def test_duration_is_area_over_rate(self):
        self.assertAlmostEqual(inspection_duration_min(3.0, 0.25), 12.0, places=9)

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            inspection_duration_min(3.0, 0.0)


class SubstantiationTests(unittest.TestCase):
    def test_finer_conditions_substantiate(self):
        self.assertTrue(can_substantiate(50.0, 100.0))

    def test_coarser_conditions_do_not(self):
        self.assertFalse(can_substantiate(150.0, 100.0))

    def test_exact_equality_substantiates(self):
        self.assertTrue(can_substantiate(100.0, 100.0))

    def test_zero_required_size_rejected(self):
        with self.assertRaises(ValueError):
            can_substantiate(50.0, 0.0)


class GradeTests(unittest.TestCase):
    def test_clean_and_substantiated_is_accepted(self):
        self.assertEqual(grade_inspection(True, False), "accept")

    def test_contamination_on_a_recleanable_surface_is_recleaned(self):
        self.assertEqual(grade_inspection(True, True), "reclean-and-reinspect")

    def test_contamination_on_a_closed_surface_escalates(self):
        self.assertEqual(
            grade_inspection(True, True, False), "escalate-to-instrumented-method"
        )

    def test_unsubstantiated_conditions_always_escalate(self):
        self.assertEqual(
            grade_inspection(False, False), "escalate-to-instrumented-method"
        )

    def test_non_boolean_observation_rejected(self):
        with self.assertRaises(ValueError):
            grade_inspection(True, "yes")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "distance_mm": 300.0,
            "acuity_arcmin": 1.0,
            "illuminance_lux": 1000.0,
            "required_um": 200.0,
            "inspected_area_m2": 2.0,
            "total_area_m2": 2.0,
            "contamination_seen": False,
        }
        spec.update(overrides)
        return spec

    def test_good_conditions_accept(self):
        result = assess_inspection(self._spec())
        self.assertTrue(result["substantiated"])
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])

    def test_tight_requirement_cannot_be_substantiated(self):
        result = assess_inspection(self._spec(required_um=10.0))
        self.assertFalse(result["substantiated"])
        self.assertEqual(result["disposition"], "escalate-to-instrumented-method")

    def test_dim_light_can_lose_substantiation(self):
        bright = assess_inspection(self._spec(required_um=100.0))
        dim = assess_inspection(self._spec(required_um=100.0, illuminance_lux=40.0))
        self.assertTrue(bright["substantiated"])
        self.assertFalse(dim["substantiated"])

    def test_contamination_seen_triggers_a_reclean(self):
        result = assess_inspection(self._spec(contamination_seen=True))
        self.assertEqual(result["disposition"], "reclean-and-reinspect")

    def test_partial_coverage_is_flagged(self):
        result = assess_inspection(self._spec(inspected_area_m2=1.0))
        self.assertFalse(result["substantiated"])
        self.assertTrue(any("inspected" in item for item in result["findings"]))

    def test_declared_partial_coverage_target_is_respected(self):
        result = assess_inspection(
            self._spec(inspected_area_m2=1.0, coverage_required=0.5)
        )
        self.assertTrue(result["substantiated"])

    def test_out_of_band_lamp_is_flagged(self):
        result = assess_inspection(
            self._spec(
                black_light={
                    "wavelength_nm": 254.0,
                    "irradiance_w_per_m2": 20.0,
                    "dark_adaptation_min": 10.0,
                }
            )
        )
        self.assertTrue(any("ultraviolet band" in item for item in result["findings"]))

    def test_weak_lamp_and_short_adaptation_are_both_flagged(self):
        result = assess_inspection(
            self._spec(
                black_light={
                    "wavelength_nm": 365.0,
                    "irradiance_w_per_m2": 2.0,
                    "dark_adaptation_min": 1.0,
                }
            )
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_compliant_black_light_adds_no_finding(self):
        result = assess_inspection(
            self._spec(
                black_light={
                    "wavelength_nm": 365.0,
                    "irradiance_w_per_m2": 20.0,
                    "dark_adaptation_min": 10.0,
                }
            )
        )
        self.assertEqual(result["findings"], [])

    def test_black_light_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection(self._spec(black_light={"wavelength_nm": 365.0}))

    def test_duration_is_reported_when_a_rate_is_given(self):
        result = assess_inspection(self._spec(rate_m2_per_min=0.5))
        self.assertAlmostEqual(result["duration_min"], 4.0, places=9)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["required_um"]
        with self.assertRaises(ValueError):
            assess_inspection(spec)

    def test_non_boolean_contamination_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection(self._spec(contamination_seen="none"))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection(["distance_mm"])

    def test_coverage_target_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection(self._spec(coverage_required=1.5))


if __name__ == "__main__":
    unittest.main()
