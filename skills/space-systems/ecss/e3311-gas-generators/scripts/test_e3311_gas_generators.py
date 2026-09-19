"""Contract test for the e3311 gas generators leaf (stdlib unittest)."""

import unittest

from e3311_gas_generators_logic import (
    DEFAULT_GAS_GENERATOR_POLICY,
    UNIVERSAL_GAS_CONSTANT_J_PER_MOL_K,
    VERDICT_MET,
    VERDICT_NOT_MET,
    actuation_verdict,
    assess_gas_generator,
    delivered_gas_temperature_k,
    delivered_pressure_mpa,
    generated_moles,
    particulate_verdict,
    rise_time_verdict,
    structural_verdict,
    thermal_verdict,
    validate_conditioning_case,
    validate_gas_generator_policy,
    validate_generator,
    validate_receiver,
    worst_case_output,
)


def generator(gid="GG-1", **kw):
    record = {
        "id": gid,
        "grain_mass_g": 2.00,
        "mass_tolerance_fraction": 0.02,
        "gas_yield_mol_per_g": 0.030,
        "flame_temperature_k": 1500.0,
        "temperature_sensitivity_k_per_k": 0.20,
        "reference_conditioning_k": 293.0,
        "measured_rise_time_s": 0.020,
        "particulate_mg": 12.0,
    }
    record.update(kw)
    return record


def receiver(rid="ACT-1", **kw):
    record = {
        "id": rid,
        "free_volume_m3": 1.0e-4,
        "volume_tolerance_fraction": 0.05,
        "required_actuation_pressure_mpa": 3.00,
        "max_allowable_working_pressure_mpa": 12.00,
        "burst_pressure_mpa": 20.00,
        "max_rise_time_s": 0.050,
        "max_gas_temperature_k": 1800.0,
        "max_particulate_mg": 50.0,
    }
    record.update(kw)
    return record


def case(**kw):
    record = {"cold_conditioning_k": 233.0, "hot_conditioning_k": 344.0}
    record.update(kw)
    return record


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_gas_generator_policy(DEFAULT_GAS_GENERATOR_POLICY),
            DEFAULT_GAS_GENERATOR_POLICY,
        )

    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_gas_generator_policy(1.25)

    def test_an_actuation_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_gas_generator_policy(
                dict(DEFAULT_GAS_GENERATOR_POLICY, min_actuation_margin=0.9)
            )

    def test_a_burst_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_gas_generator_policy(
                dict(DEFAULT_GAS_GENERATOR_POLICY, min_burst_margin=0.5)
            )


class TestRecordValidation(unittest.TestCase):
    def test_a_valid_generator_normalizes(self):
        record = validate_generator(generator())
        self.assertAlmostEqual(record["grain_mass_g"], 2.00, places=9)

    def test_a_zero_grain_mass_raises(self):
        with self.assertRaises(ValueError):
            validate_generator(generator(grain_mass_g=0.0))

    def test_a_mass_tolerance_of_one_raises(self):
        with self.assertRaises(ValueError):
            validate_generator(generator(mass_tolerance_fraction=1.0))

    def test_a_negative_mass_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_generator(generator(mass_tolerance_fraction=-0.1))

    def test_a_burst_pressure_below_the_working_pressure_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(burst_pressure_mpa=5.0))

    def test_a_zero_free_volume_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(free_volume_m3=0.0))

    def test_an_inverted_conditioning_case_raises(self):
        with self.assertRaises(ValueError):
            validate_conditioning_case(case(hot_conditioning_k=200.0))

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            validate_conditioning_case([233.0, 344.0])


class TestOutputComputation(unittest.TestCase):
    def test_moles_are_mass_times_specific_yield(self):
        self.assertAlmostEqual(generated_moles(generator()), 0.060, places=12)

    def test_an_explicit_mass_overrides_the_nominal(self):
        self.assertAlmostEqual(
            generated_moles(generator(), 1.50), 0.045, places=12
        )

    def test_pressure_follows_the_ideal_gas_expression(self):
        expected = (
            0.060 * UNIVERSAL_GAS_CONSTANT_J_PER_MOL_K * 1500.0 / 1.0e-4
        ) / 1.0e6
        self.assertAlmostEqual(
            delivered_pressure_mpa(0.060, 1500.0, 1.0e-4), expected, places=9
        )

    def test_a_zero_volume_raises_from_the_pressure_expression(self):
        with self.assertRaises(ValueError):
            delivered_pressure_mpa(0.060, 1500.0, 0.0)

    def test_gas_temperature_shifts_with_conditioning(self):
        self.assertAlmostEqual(
            delivered_gas_temperature_k(generator(), 233.0), 1488.0, places=9
        )

    def test_gas_temperature_at_the_reference_is_the_flame_temperature(self):
        self.assertAlmostEqual(
            delivered_gas_temperature_k(generator(), 293.0), 1500.0, places=9
        )

    def test_the_cold_corner_is_lighter_larger_and_cooler(self):
        corners = worst_case_output(generator(), receiver(), case())
        self.assertAlmostEqual(corners["cold_mass_g"], 1.96, places=9)
        self.assertAlmostEqual(corners["large_volume_m3"], 1.05e-4, places=12)
        self.assertLess(corners["cold_pressure_mpa"], corners["hot_pressure_mpa"])

    def test_the_hot_corner_is_heavier_smaller_and_warmer(self):
        corners = worst_case_output(generator(), receiver(), case())
        self.assertAlmostEqual(corners["hot_mass_g"], 2.04, places=9)
        self.assertAlmostEqual(corners["small_volume_m3"], 0.95e-4, places=12)
        self.assertGreater(
            corners["hot_gas_temperature_k"], corners["cold_gas_temperature_k"]
        )

    def test_zero_tolerances_collapse_the_two_corners(self):
        corners = worst_case_output(
            generator(mass_tolerance_fraction=0.0, temperature_sensitivity_k_per_k=0.0),
            receiver(volume_tolerance_fraction=0.0),
            case(),
        )
        self.assertAlmostEqual(
            corners["cold_pressure_mpa"], corners["hot_pressure_mpa"], places=9
        )


class TestGates(unittest.TestCase):
    def test_a_healthy_generator_clears_the_actuation_margin(self):
        verdict = actuation_verdict(generator(), receiver(), case())
        self.assertTrue(verdict["compliant"])
        self.assertGreater(verdict["actuation_margin"], 1.25)

    def test_an_actuation_margin_landing_exactly_on_the_requirement_passes(self):
        corners = worst_case_output(generator(), receiver(), case())
        needed = corners["cold_pressure_mpa"] / 1.25
        verdict = actuation_verdict(
            generator(), receiver(required_actuation_pressure_mpa=needed), case()
        )
        self.assertAlmostEqual(verdict["actuation_margin"], 1.25, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_demanding_actuator_fails_the_cold_corner(self):
        verdict = actuation_verdict(
            generator(), receiver(required_actuation_pressure_mpa=6.50), case()
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("cold corner" in f for f in verdict["findings"]))

    def test_a_low_working_pressure_fails_the_hot_corner(self):
        verdict = structural_verdict(
            generator(),
            receiver(max_allowable_working_pressure_mpa=6.0),
            case(),
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("allowed to work" in f for f in verdict["findings"]))

    def test_a_burst_margin_landing_exactly_on_the_requirement_passes(self):
        corners = worst_case_output(generator(), receiver(), case())
        burst = 2.0 * corners["hot_pressure_mpa"]
        verdict = structural_verdict(
            generator(), receiver(burst_pressure_mpa=burst), case()
        )
        self.assertAlmostEqual(verdict["burst_margin"], 2.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_thin_housing_fails_the_burst_margin(self):
        verdict = structural_verdict(
            generator(),
            receiver(burst_pressure_mpa=12.0, max_allowable_working_pressure_mpa=12.0),
            case(),
        )
        self.assertFalse(verdict["compliant"])
        self.assertLess(verdict["burst_margin"], 2.0)

    def test_a_slow_rise_fails(self):
        self.assertFalse(
            rise_time_verdict(generator(measured_rise_time_s=0.090), receiver())[
                "compliant"
            ]
        )

    def test_a_rise_time_exactly_on_the_limit_passes(self):
        self.assertTrue(
            rise_time_verdict(generator(measured_rise_time_s=0.050), receiver())[
                "compliant"
            ]
        )

    def test_hot_gas_above_the_seal_limit_fails(self):
        verdict = thermal_verdict(
            generator(), receiver(max_gas_temperature_k=900.0), case()
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("seals tolerate" in f for f in verdict["findings"]))

    def test_excess_solid_products_fail(self):
        self.assertFalse(
            particulate_verdict(generator(particulate_mg=90.0), receiver())[
                "compliant"
            ]
        )


class TestAssessment(unittest.TestCase):
    def test_a_sound_generator_meets_the_clause(self):
        report = assess_gas_generator(generator(), receiver(), case())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_gates"], [])

    def test_a_failing_generator_names_every_failed_gate(self):
        report = assess_gas_generator(
            generator(measured_rise_time_s=0.200, particulate_mg=400.0),
            receiver(),
            case(),
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertIn("rise-time", report["failed_gates"])
        self.assertIn("particulate", report["failed_gates"])

    def test_the_report_carries_both_corners(self):
        report = assess_gas_generator(generator(), receiver(), case())
        self.assertIn("cold_pressure_mpa", report["corners"])
        self.assertIn("hot_pressure_mpa", report["corners"])

    def test_a_bad_conditioning_case_raises_from_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_gas_generator(
                generator(), receiver(), case(cold_conditioning_k=-10.0)
            )


if __name__ == "__main__":
    unittest.main()
