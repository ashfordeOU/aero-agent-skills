"""Contract tests for the clause 4.7.5.4.10 threaded-part logic."""

import math
import unittest

from e3301_threaded_parts_locating_devices_logic import (
    DEFAULT_EMBEDMENT_FRACTION,
    DEFAULT_THERMAL_RELAXATION_FRACTION,
    FASTENER_MATERIALS,
    MARGIN_TOLERANCE,
    REQUIRED_SCC_CATEGORY,
    SCC_CATEGORY_ORDER,
    assess_threaded_part,
    effective_torque_nm,
    fastener_material,
    gapping_margin,
    locking_feature,
    preload_band_n,
    preload_from_torque_n,
    preload_losses_n,
    residual_preload_n,
    slip_margin,
    tensile_stress_area_mm2,
    validate_positive,
    yield_margin,
)


def base_spec(**overrides):
    spec = {
        "material": "a286",
        "nominal_diameter_mm": 6.0,
        "pitch_mm": 1.0,
        "applied_torque_nm": 9.0,
        "torque_tolerance_fraction": 0.1,
        "nut_factor_min": 0.16,
        "nut_factor_max": 0.24,
        "locking": "prevailing-torque-nut",
        "external_tensile_load_n": 1500.0,
        "shear_load_n": 600.0,
        "load_factor": 1.25,
        "stiffness_ratio": 0.25,
        "friction_coefficient": 0.2,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 9), 9.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", -2.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))


class StockTests(unittest.TestCase):
    def test_required_category_is_the_most_resistant(self):
        self.assertEqual(REQUIRED_SCC_CATEGORY, SCC_CATEGORY_ORDER[0])

    def test_a286_is_category_one(self):
        self.assertEqual(fastener_material("a286")["scc_category"], "I")

    def test_martensitic_steel_is_a_lower_category(self):
        self.assertNotEqual(fastener_material("aisi-410")["scc_category"], "I")

    def test_record_is_a_copy(self):
        record = fastener_material("inconel-718")
        record["yield_mpa"] = 1.0
        self.assertAlmostEqual(FASTENER_MATERIALS["inconel-718"]["yield_mpa"], 1030.0)

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            fastener_material("pewter")

    def test_lockwire_is_a_positive_feature(self):
        self.assertTrue(locking_feature("lockwire")["positive"])

    def test_spring_washer_is_not_a_positive_feature(self):
        self.assertFalse(locking_feature("spring-washer")["positive"])

    def test_unknown_locking_feature_rejected(self):
        with self.assertRaises(ValueError):
            locking_feature("hope")


class ThreadGeometryTests(unittest.TestCase):
    def test_stress_area_matches_the_iso_form(self):
        expected = math.pi * 0.25 * (6.0 - 0.9382 * 1.0) ** 2
        self.assertAlmostEqual(tensile_stress_area_mm2(6.0, 1.0), expected, places=9)

    def test_larger_diameter_gives_a_larger_area(self):
        self.assertGreater(
            tensile_stress_area_mm2(8.0, 1.25), tensile_stress_area_mm2(6.0, 1.0)
        )

    def test_pitch_at_or_above_the_diameter_rejected(self):
        with self.assertRaises(ValueError):
            tensile_stress_area_mm2(6.0, 6.0)

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            tensile_stress_area_mm2(0.0, 1.0)


class TorqueAndPreloadTests(unittest.TestCase):
    def test_prevailing_torque_is_subtracted(self):
        self.assertAlmostEqual(effective_torque_nm(9.0, 0.4), 8.6, places=9)

    def test_prevailing_torque_swallowing_the_applied_torque_rejected(self):
        with self.assertRaises(ValueError):
            effective_torque_nm(0.3, 0.4)

    def test_preload_matches_the_short_form_relation(self):
        self.assertAlmostEqual(
            preload_from_torque_n(8.6, 6.0, 0.2), 1000.0 * 8.6 / (0.2 * 6.0), places=9
        )

    def test_higher_nut_factor_gives_less_preload(self):
        self.assertLess(
            preload_from_torque_n(8.6, 6.0, 0.24), preload_from_torque_n(8.6, 6.0, 0.16)
        )

    def test_nut_factor_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            preload_from_torque_n(8.6, 6.0, 1.0)

    def test_band_min_uses_the_high_nut_factor(self):
        low, high = preload_band_n(9.0, 0.1, 6.0, 0.16, 0.24, 0.4)
        self.assertLess(low, high)
        self.assertAlmostEqual(
            low, preload_from_torque_n(9.0 * 0.9 - 0.4, 6.0, 0.24), places=9
        )

    def test_zero_tolerance_narrows_the_band_to_the_friction_spread(self):
        low, high = preload_band_n(9.0, 0.0, 6.0, 0.2, 0.2, 0.0)
        self.assertAlmostEqual(low, high, places=9)

    def test_inverted_nut_factor_band_rejected(self):
        with self.assertRaises(ValueError):
            preload_band_n(9.0, 0.1, 6.0, 0.3, 0.2)

    def test_tolerance_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            preload_band_n(9.0, 1.0, 6.0, 0.16, 0.24)


class LossAndResidualTests(unittest.TestCase):
    def test_default_loss_fractions_sum_correctly(self):
        losses = preload_losses_n(1000.0)
        self.assertAlmostEqual(
            losses,
            1000.0 * (DEFAULT_EMBEDMENT_FRACTION + DEFAULT_THERMAL_RELAXATION_FRACTION),
            places=9,
        )

    def test_losses_consuming_the_preload_rejected(self):
        with self.assertRaises(ValueError):
            preload_losses_n(1000.0, 0.6, 0.5)

    def test_residual_is_the_preload_less_losses(self):
        self.assertAlmostEqual(residual_preload_n(1000.0, 80.0), 920.0, places=9)

    def test_residual_swallowed_by_losses_rejected(self):
        with self.assertRaises(ValueError):
            residual_preload_n(100.0, 100.0)


class MarginTests(unittest.TestCase):
    def test_gapping_margin_matches_the_closed_form(self):
        value = gapping_margin(1000.0, 500.0, 1.25, 0.25)
        self.assertAlmostEqual(value, (1000.0 / 0.75) / 625.0 - 1.0, places=9)

    def test_no_tensile_load_gives_an_infinite_gapping_margin(self):
        self.assertEqual(gapping_margin(1000.0, 0.0, 1.25, 0.25), float("inf"))

    def test_stiffness_ratio_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            gapping_margin(1000.0, 500.0, 1.25, 1.0)

    def test_slip_margin_matches_the_closed_form(self):
        value = slip_margin(1000.0, 0.2, 100.0, 1.25, 2)
        self.assertAlmostEqual(value, 0.2 * 2 * 1000.0 / 125.0 - 1.0, places=9)

    def test_second_friction_interface_raises_the_slip_margin(self):
        self.assertGreater(
            slip_margin(1000.0, 0.2, 200.0, 1.25, 2),
            slip_margin(1000.0, 0.2, 200.0, 1.25, 1),
        )

    def test_zero_interfaces_rejected(self):
        with self.assertRaises(ValueError):
            slip_margin(1000.0, 0.2, 200.0, 1.25, 0)

    def test_yield_margin_matches_the_closed_form(self):
        value = yield_margin(5000.0, 1000.0, 1.25, 0.25, 20.0, 660.0)
        self.assertAlmostEqual(
            value, 660.0 * 20.0 / (5000.0 + 0.25 * 1250.0) - 1.0, places=9
        )

    def test_higher_preload_lowers_the_yield_margin(self):
        self.assertLess(
            yield_margin(9000.0, 1000.0, 1.25, 0.25, 20.0, 660.0),
            yield_margin(5000.0, 1000.0, 1.25, 0.25, 20.0, 660.0),
        )


class AssessmentTests(unittest.TestCase):
    def test_sound_joint_reports_no_findings(self):
        result = assess_threaded_part(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_prevailing_torque_defaults_to_the_locking_feature(self):
        result = assess_threaded_part(base_spec())
        self.assertAlmostEqual(result["prevailing_torque_nm"], 0.4, places=9)

    def test_lockwire_contributes_no_prevailing_torque(self):
        result = assess_threaded_part(base_spec(locking="lockwire"))
        self.assertAlmostEqual(result["prevailing_torque_nm"], 0.0)

    def test_ignoring_prevailing_torque_overstates_the_preload(self):
        with_lock = assess_threaded_part(base_spec())
        without = assess_threaded_part(base_spec(prevailing_torque_nm=0.0))
        self.assertGreater(without["preload_min_n"], with_lock["preload_min_n"])

    def test_susceptible_material_without_justification_is_flagged(self):
        result = assess_threaded_part(base_spec(material="aluminium-7075-t6"))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no justification" in f for f in result["findings"]))

    def test_susceptible_material_with_justification_is_retained(self):
        result = assess_threaded_part(
            base_spec(material="aluminium-7075-t73", applied_torque_nm=5.0,
                      shear_load_n=300.0, scc_justification_recorded=True)
        )
        self.assertTrue(any("recorded justification" in f for f in result["findings"]))
        self.assertTrue(result["compliant"])

    def test_justification_does_not_excuse_a_negative_margin(self):
        result = assess_threaded_part(
            base_spec(material="aluminium-7075-t73", scc_justification_recorded=True)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("yield margin" in f for f in result["findings"]))

    def test_absent_locking_feature_is_flagged(self):
        result = assess_threaded_part(base_spec(locking="none"))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["positive_locking"])

    def test_spring_washer_is_not_accepted_as_locking(self):
        result = assess_threaded_part(base_spec(locking="spring-washer"))
        self.assertFalse(result["compliant"])

    def test_high_shear_load_fails_the_slip_check(self):
        result = assess_threaded_part(base_spec(shear_load_n=1200.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("slip margin" in f for f in result["findings"]))

    def test_high_tensile_load_fails_the_gapping_check(self):
        result = assess_threaded_part(base_spec(external_tensile_load_n=6000.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("gapping margin" in f for f in result["findings"]))

    def test_slip_margin_exactly_zero_is_accepted(self):
        spec = base_spec()
        probe = assess_threaded_part(spec)
        mu = spec["friction_coefficient"]
        spec["shear_load_n"] = mu * probe["residual_preload_n"] / spec["load_factor"]
        result = assess_threaded_part(spec)
        self.assertAlmostEqual(result["slip_margin"], 0.0, places=9)
        self.assertLessEqual(abs(result["slip_margin"]), MARGIN_TOLERANCE)
        self.assertTrue(result["compliant"])

    def test_weak_material_fails_the_yield_check(self):
        result = assess_threaded_part(base_spec(material="aisi-316"))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("yield margin" in f for f in result["findings"]))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["locking"]
        with self.assertRaises(ValueError):
            assess_threaded_part(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_threaded_part("material")


if __name__ == "__main__":
    unittest.main()
