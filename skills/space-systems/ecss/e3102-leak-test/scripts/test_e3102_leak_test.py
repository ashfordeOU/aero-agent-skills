"""Contract test for the leak-test leaf (stdlib unittest)."""

import math
import unittest

from e3102_leak_test_logic import (
    DEFAULT_SENSITIVITY_RATIO,
    HELIUM_MOLAR_MASS_KG_PER_MOL,
    LEAK_TOLERANCE,
    METHOD_SENSITIVITY_PA_M3_PER_S,
    UNIVERSAL_GAS_CONSTANT,
    allowable_leak_rate_pa_m3_per_s,
    assess_leak_test,
    assess_measured_rate,
    assess_sensitivity,
    method_sensitivity,
    require_positive,
    require_real,
    specific_gas_constant,
    tracer_to_service_rate,
    validate_method,
)

AMMONIA_MOLAR_MASS = 0.017031
MASS_LOSS = 1.0e-3
TEMPERATURE = 293.15
LIFETIME = 15.0 * 365.25 * 24.0 * 3600.0


def good_spec(**overrides):
    spec = {
        "method": "helium-mass-spectrometer-vacuum-chamber",
        "allowed_mass_loss_kg": MASS_LOSS,
        "molar_mass_kg_per_mol": AMMONIA_MOLAR_MASS,
        "reference_temperature_k": TEMPERATURE,
        "lifetime_s": LIFETIME,
        "measured_tracer_rate": 1.0e-7,
    }
    spec.update(overrides)
    return spec


class TestValidators(unittest.TestCase):
    def test_require_real_rejects_boolean(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            require_positive("x", 0.0)

    def test_require_real_rejects_nan(self):
        with self.assertRaises(ValueError):
            require_real("x", float("nan"))


class TestGasConstants(unittest.TestCase):
    def test_specific_constant_is_universal_over_molar_mass(self):
        self.assertAlmostEqual(
            specific_gas_constant(AMMONIA_MOLAR_MASS),
            UNIVERSAL_GAS_CONSTANT / AMMONIA_MOLAR_MASS, places=9,
        )

    def test_gram_per_mole_input_is_refused(self):
        with self.assertRaises(ValueError):
            specific_gas_constant(17.031)

    def test_zero_molar_mass_raises(self):
        with self.assertRaises(ValueError):
            specific_gas_constant(0.0)


class TestAcceptanceDerivation(unittest.TestCase):
    def test_acceptance_rate_matches_the_throughput_relation(self):
        expected = MASS_LOSS * (UNIVERSAL_GAS_CONSTANT / AMMONIA_MOLAR_MASS) \
            * TEMPERATURE / LIFETIME
        self.assertAlmostEqual(
            allowable_leak_rate_pa_m3_per_s(MASS_LOSS, AMMONIA_MOLAR_MASS,
                                            TEMPERATURE, LIFETIME),
            expected, places=15,
        )

    def test_longer_life_tightens_the_acceptance_rate(self):
        short = allowable_leak_rate_pa_m3_per_s(MASS_LOSS, AMMONIA_MOLAR_MASS,
                                                TEMPERATURE, LIFETIME)
        long = allowable_leak_rate_pa_m3_per_s(MASS_LOSS, AMMONIA_MOLAR_MASS,
                                               TEMPERATURE, 2.0 * LIFETIME)
        self.assertLess(long, short)

    def test_larger_allowed_loss_relaxes_the_acceptance_rate(self):
        small = allowable_leak_rate_pa_m3_per_s(MASS_LOSS, AMMONIA_MOLAR_MASS,
                                                TEMPERATURE, LIFETIME)
        large = allowable_leak_rate_pa_m3_per_s(2.0 * MASS_LOSS, AMMONIA_MOLAR_MASS,
                                                TEMPERATURE, LIFETIME)
        self.assertGreater(large, small)

    def test_zero_lifetime_raises(self):
        with self.assertRaises(ValueError):
            allowable_leak_rate_pa_m3_per_s(MASS_LOSS, AMMONIA_MOLAR_MASS,
                                            TEMPERATURE, 0.0)

    def test_negative_mass_loss_raises(self):
        with self.assertRaises(ValueError):
            allowable_leak_rate_pa_m3_per_s(-1.0, AMMONIA_MOLAR_MASS,
                                            TEMPERATURE, LIFETIME)


class TestMethods(unittest.TestCase):
    def test_every_recognised_method_validates(self):
        for name in METHOD_SENSITIVITY_PA_M3_PER_S:
            self.assertEqual(validate_method(name.upper()), name)

    def test_unrecognised_method_raises(self):
        with self.assertRaises(ValueError):
            validate_method("listen-for-hissing")

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            validate_method("")

    def test_default_sensitivity_is_the_method_best(self):
        name, value = method_sensitivity("pressure-decay")
        self.assertEqual(name, "pressure-decay")
        self.assertAlmostEqual(
            value, METHOD_SENSITIVITY_PA_M3_PER_S["pressure-decay"], places=15
        )

    def test_coarser_declared_sensitivity_is_honoured(self):
        _, value = method_sensitivity("helium-mass-spectrometer-vacuum-chamber",
                                      declared_sensitivity=1.0e-9)
        self.assertAlmostEqual(value, 1.0e-9, places=15)

    def test_declared_sensitivity_finer_than_the_method_is_refused(self):
        with self.assertRaises(ValueError):
            method_sensitivity("pressure-decay", declared_sensitivity=1.0e-11)

    def test_declared_sensitivity_equal_to_the_method_best_is_accepted(self):
        _, value = method_sensitivity(
            "pressure-decay",
            declared_sensitivity=METHOD_SENSITIVITY_PA_M3_PER_S["pressure-decay"],
        )
        self.assertAlmostEqual(value, 1.0e-5, places=15)


class TestTracerConversion(unittest.TestCase):
    def test_helium_over_reads_against_a_heavier_fluid(self):
        converted = tracer_to_service_rate(1.0e-7, AMMONIA_MOLAR_MASS)
        self.assertLess(converted, 1.0e-7)

    def test_conversion_matches_the_inverse_root_mass_law(self):
        expected = 1.0e-7 * math.sqrt(HELIUM_MOLAR_MASS_KG_PER_MOL / AMMONIA_MOLAR_MASS)
        self.assertAlmostEqual(tracer_to_service_rate(1.0e-7, AMMONIA_MOLAR_MASS),
                               expected, places=15)

    def test_same_gas_leaves_the_rate_unchanged(self):
        self.assertAlmostEqual(
            tracer_to_service_rate(1.0e-7, HELIUM_MOLAR_MASS_KG_PER_MOL),
            1.0e-7, places=15,
        )

    def test_gram_per_mole_input_is_refused(self):
        with self.assertRaises(ValueError):
            tracer_to_service_rate(1.0e-7, 17.031)

    def test_zero_rate_raises(self):
        with self.assertRaises(ValueError):
            tracer_to_service_rate(0.0, AMMONIA_MOLAR_MASS)


class TestSensitivityGrading(unittest.TestCase):
    def test_mass_spectrometer_resolves_the_acceptance_rate(self):
        result = assess_sensitivity("helium-mass-spectrometer-vacuum-chamber", 3.0e-7)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_sensitivity_pa_m3_per_s"],
                               3.0e-8, places=15)

    def test_pressure_decay_cannot_demonstrate_a_fine_acceptance_rate(self):
        result = assess_sensitivity("pressure-decay", 3.0e-7)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_sensitivity_exactly_at_the_required_value_is_accepted(self):
        acceptance = METHOD_SENSITIVITY_PA_M3_PER_S["pressure-decay"] \
            * DEFAULT_SENSITIVITY_RATIO
        result = assess_sensitivity("pressure-decay", acceptance)
        self.assertTrue(result["compliant"])

    def test_a_looser_resolution_ratio_changes_the_requirement(self):
        result = assess_sensitivity("pressure-decay", 3.0e-5, ratio=1.0)
        self.assertTrue(result["compliant"])

    def test_zero_acceptance_rate_raises(self):
        with self.assertRaises(ValueError):
            assess_sensitivity("pressure-decay", 0.0)


class TestMeasuredRate(unittest.TestCase):
    def test_rate_inside_the_acceptance_passes(self):
        result = assess_measured_rate(5.0e-8, 3.0e-7)
        self.assertTrue(result["compliant"])
        self.assertGreater(result["margin"], 0.0)

    def test_rate_exactly_at_the_acceptance_passes(self):
        result = assess_measured_rate(3.0e-7, 3.0e-7)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 0.0, places=15)

    def test_rate_above_the_acceptance_fails(self):
        result = assess_measured_rate(1.0e-6, 3.0e-7)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_reading_below_the_instrument_floor_is_a_non_detection(self):
        result = assess_measured_rate(1.0e-13, 3.0e-7, sensitivity=1.0e-11)
        self.assertTrue(result["within_acceptance"])
        self.assertFalse(result["above_instrument_floor"])
        self.assertTrue(any("non-detection" in f for f in result["findings"]))

    def test_reading_at_the_instrument_floor_counts_as_measured(self):
        result = assess_measured_rate(1.0e-11, 3.0e-7, sensitivity=1.0e-11)
        self.assertTrue(result["above_instrument_floor"])

    def test_zero_measured_rate_raises(self):
        with self.assertRaises(ValueError):
            assess_measured_rate(0.0, 3.0e-7)


class TestWholeTest(unittest.TestCase):
    def test_good_leak_test_is_compliant(self):
        report = assess_leak_test(good_spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_acceptance_rate_is_derived_from_the_inventory(self):
        report = assess_leak_test(good_spec())
        expected = allowable_leak_rate_pa_m3_per_s(MASS_LOSS, AMMONIA_MOLAR_MASS,
                                                   TEMPERATURE, LIFETIME)
        self.assertAlmostEqual(report["derived_acceptance_rate_pa_m3_per_s"],
                               expected, places=15)

    def test_service_rate_is_the_converted_tracer_reading(self):
        report = assess_leak_test(good_spec())
        expected = tracer_to_service_rate(1.0e-7, AMMONIA_MOLAR_MASS)
        self.assertAlmostEqual(report["service_leak_rate_pa_m3_per_s"],
                               expected, places=15)

    def test_coarse_method_names_the_failed_check(self):
        report = assess_leak_test(good_spec(method="pressure-decay"))
        self.assertFalse(report["compliant"])
        self.assertIn("sensitivity", report["failed_checks"])

    def test_leaky_article_names_the_failed_check(self):
        report = assess_leak_test(good_spec(measured_tracer_rate=1.0e-5))
        self.assertFalse(report["compliant"])
        self.assertIn("measurement", report["failed_checks"])

    def test_explicit_acceptance_rate_overrides_the_derivation(self):
        report = assess_leak_test(good_spec(acceptance_rate_pa_m3_per_s=1.0e-9))
        self.assertAlmostEqual(report["acceptance_rate_pa_m3_per_s"], 1.0e-9,
                               places=15)
        self.assertNotEqual(report["acceptance_rate_pa_m3_per_s"],
                            report["derived_acceptance_rate_pa_m3_per_s"])
        self.assertFalse(report["compliant"])

    def test_missing_key_raises(self):
        spec = good_spec()
        del spec["lifetime_s"]
        with self.assertRaises(ValueError):
            assess_leak_test(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_leak_test("helium")

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertLess(LEAK_TOLERANCE, 1e-9)


if __name__ == "__main__":
    unittest.main()
