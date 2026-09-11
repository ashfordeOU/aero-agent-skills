"""
test_e1012_sensor_bg_margin.py

Offline deterministic unittest for radiation-induced sensor background
margin logic. Anchor: ECSS-E-ST-10C §5.5.4.

Run: python3 test_e1012_sensor_bg_margin.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_sensor_bg_margin_logic import (
    assess_sensor_background,
    compute_population_background,
    validate_population,
    VALID_PARTICLE_TYPES,
)


class TestValidParticleTypes(unittest.TestCase):
    def test_proton_is_valid(self):
        self.assertIn("proton", VALID_PARTICLE_TYPES)

    def test_electron_is_valid(self):
        self.assertIn("electron", VALID_PARTICLE_TYPES)

    def test_cosmic_ray_is_valid(self):
        self.assertIn("cosmic-ray", VALID_PARTICLE_TYPES)

    def test_neutrino_not_valid(self):
        self.assertNotIn("neutrino", VALID_PARTICLE_TYPES)


class TestValidatePopulation(unittest.TestCase):
    def _base_pop(self):
        return {
            "particle_type": "proton",
            "flux": 1000.0,
            "sensitive_area": 1.0,
            "bg_conversion": 0.01,
        }

    def test_valid_population_no_error(self):
        validate_population(self._base_pop())  # must not raise

    def test_invalid_particle_type_raises(self):
        pop = self._base_pop()
        pop["particle_type"] = "neutrino"
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_negative_flux_raises(self):
        pop = self._base_pop()
        pop["flux"] = -0.1
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_zero_sensitive_area_raises(self):
        pop = self._base_pop()
        pop["sensitive_area"] = 0.0
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_negative_sensitive_area_raises(self):
        pop = self._base_pop()
        pop["sensitive_area"] = -2.0
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_negative_bg_conversion_raises(self):
        pop = self._base_pop()
        pop["bg_conversion"] = -0.001
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_missing_flux_key_raises(self):
        pop = self._base_pop()
        del pop["flux"]
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_missing_particle_type_raises(self):
        pop = self._base_pop()
        del pop["particle_type"]
        with self.assertRaises(ValueError):
            validate_population(pop)

    def test_zero_flux_is_valid(self):
        pop = self._base_pop()
        pop["flux"] = 0.0
        validate_population(pop)  # must not raise

    def test_zero_bg_conversion_is_valid(self):
        pop = self._base_pop()
        pop["bg_conversion"] = 0.0
        validate_population(pop)  # must not raise

    def test_sep_proton_is_valid_type(self):
        pop = self._base_pop()
        pop["particle_type"] = "sep-proton"
        validate_population(pop)  # must not raise


class TestComputePopulationBackground(unittest.TestCase):
    def test_nominal_single_population(self):
        pop = {
            "particle_type": "proton",
            "flux": 100.0,
            "sensitive_area": 2.0,
            "bg_conversion": 0.05,
        }
        result = compute_population_background(pop, integration_time=10.0)
        self.assertAlmostEqual(result, 100.0)  # 100 * 2.0 * 0.05 * 10

    def test_zero_flux_gives_zero_background(self):
        pop = {
            "particle_type": "electron",
            "flux": 0.0,
            "sensitive_area": 1.0,
            "bg_conversion": 0.1,
        }
        self.assertEqual(compute_population_background(pop, 100.0), 0.0)

    def test_zero_integration_time_gives_zero(self):
        pop = {
            "particle_type": "cosmic-ray",
            "flux": 5000.0,
            "sensitive_area": 0.5,
            "bg_conversion": 0.02,
        }
        self.assertEqual(compute_population_background(pop, 0.0), 0.0)

    def test_linear_scaling_with_flux(self):
        pop_base = {
            "particle_type": "proton",
            "flux": 200.0,
            "sensitive_area": 1.0,
            "bg_conversion": 0.01,
        }
        pop_double = dict(pop_base)
        pop_double["flux"] = 400.0
        r_base = compute_population_background(pop_base, 10.0)
        r_double = compute_population_background(pop_double, 10.0)
        self.assertAlmostEqual(r_double, 2 * r_base)

    def test_linear_scaling_with_integration_time(self):
        pop = {
            "particle_type": "alpha",
            "flux": 50.0,
            "sensitive_area": 0.5,
            "bg_conversion": 0.1,
        }
        r1 = compute_population_background(pop, 30.0)
        r2 = compute_population_background(pop, 60.0)
        self.assertAlmostEqual(r2, 2 * r1)


class TestAssessSensorBackground(unittest.TestCase):
    def _proton_pop(self, flux=500.0, area=1.0, conv=0.01):
        return {
            "particle_type": "proton",
            "flux": flux,
            "sensitive_area": area,
            "bg_conversion": conv,
        }

    def test_compliant_single_population(self):
        result = assess_sensor_background(
            sensor_id="CCD-01",
            populations=[self._proton_pop(flux=100.0)],
            integration_time=10.0,
            margin_factor=2.0,
            budget=100.0,
        )
        # raw = 100 * 1 * 0.01 * 10 = 10; margined = 20; budget = 100 → compliant
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["raw_background"], 10.0)
        self.assertAlmostEqual(result["margined_background"], 20.0)
        self.assertAlmostEqual(result["exceedance"], 0.0)

    def test_non_compliant_single_population(self):
        result = assess_sensor_background(
            sensor_id="CCD-02",
            populations=[self._proton_pop(flux=10000.0)],
            integration_time=100.0,
            margin_factor=2.0,
            budget=500.0,
        )
        # raw = 10000 * 1 * 0.01 * 100 = 10000; margined = 20000; budget = 500
        self.assertFalse(result["compliant"])
        self.assertGreater(result["exceedance"], 0.0)
        self.assertAlmostEqual(result["exceedance"], 19500.0)

    def test_multi_population_sum_compliant(self):
        populations = [
            {"particle_type": "proton", "flux": 200.0, "sensitive_area": 1.0, "bg_conversion": 0.01},
            {"particle_type": "electron", "flux": 500.0, "sensitive_area": 1.0, "bg_conversion": 0.002},
        ]
        result = assess_sensor_background(
            sensor_id="STAR-01",
            populations=populations,
            integration_time=10.0,
            margin_factor=1.5,
            budget=200.0,
        )
        # proton raw = 200*1*0.01*10 = 20; electron raw = 500*1*0.002*10 = 10
        # total raw = 30; margined = 45; budget = 200 → compliant
        self.assertAlmostEqual(result["raw_background"], 30.0)
        self.assertAlmostEqual(result["margined_background"], 45.0)
        self.assertTrue(result["compliant"])

    def test_multi_population_sum_non_compliant(self):
        populations = [
            {"particle_type": "proton", "flux": 1000.0, "sensitive_area": 2.0, "bg_conversion": 0.05},
            {"particle_type": "cosmic-ray", "flux": 10.0, "sensitive_area": 2.0, "bg_conversion": 1.0},
        ]
        result = assess_sensor_background(
            sensor_id="SPEC-01",
            populations=populations,
            integration_time=60.0,
            margin_factor=2.0,
            budget=5000.0,
        )
        # proton raw = 1000*2*0.05*60 = 6000; gcr raw = 10*2*1.0*60 = 1200; total = 7200
        # margined = 14400; budget = 5000 → non-compliant; exceedance = 9400
        self.assertAlmostEqual(result["raw_background"], 7200.0)
        self.assertAlmostEqual(result["margined_background"], 14400.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["exceedance"], 9400.0)

    def test_empty_populations_zero_background_compliant(self):
        result = assess_sensor_background(
            sensor_id="SEN-EMPTY",
            populations=[],
            integration_time=100.0,
            margin_factor=2.0,
            budget=50.0,
        )
        self.assertAlmostEqual(result["raw_background"], 0.0)
        self.assertAlmostEqual(result["margined_background"], 0.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["population_details"], [])

    def test_budget_exactly_at_margined_background_is_compliant(self):
        result = assess_sensor_background(
            sensor_id="SEN-EXACT",
            populations=[self._proton_pop(flux=1000.0)],
            integration_time=5.0,
            margin_factor=1.0,
            budget=50.0,
        )
        # raw = 1000*1*0.01*5 = 50; margined = 50; budget = 50 → compliant (<=)
        self.assertAlmostEqual(result["margined_background"], 50.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["exceedance"], 0.0)

    def test_margin_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background(
                sensor_id="SEN-BAD",
                populations=[self._proton_pop()],
                integration_time=10.0,
                margin_factor=0.9,
                budget=100.0,
            )

    def test_negative_integration_time_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background(
                sensor_id="SEN-NEG-T",
                populations=[self._proton_pop()],
                integration_time=-1.0,
                margin_factor=2.0,
                budget=100.0,
            )

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background(
                sensor_id="SEN-ZB",
                populations=[self._proton_pop()],
                integration_time=10.0,
                margin_factor=2.0,
                budget=0.0,
            )

    def test_negative_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background(
                sensor_id="SEN-NB",
                populations=[self._proton_pop()],
                integration_time=10.0,
                margin_factor=2.0,
                budget=-100.0,
            )

    def test_empty_sensor_id_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background(
                sensor_id="",
                populations=[self._proton_pop()],
                integration_time=10.0,
                margin_factor=2.0,
                budget=100.0,
            )

    def test_population_details_count_matches_input(self):
        populations = [
            {"particle_type": "proton", "flux": 100.0, "sensitive_area": 1.0, "bg_conversion": 0.01},
            {"particle_type": "electron", "flux": 200.0, "sensitive_area": 1.0, "bg_conversion": 0.005},
            {"particle_type": "cosmic-ray", "flux": 5.0, "sensitive_area": 1.0, "bg_conversion": 0.1},
        ]
        result = assess_sensor_background(
            sensor_id="SEN-3POP",
            populations=populations,
            integration_time=60.0,
            margin_factor=2.0,
            budget=10000.0,
        )
        self.assertEqual(len(result["population_details"]), 3)
        types_returned = [d["particle_type"] for d in result["population_details"]]
        self.assertIn("proton", types_returned)
        self.assertIn("electron", types_returned)
        self.assertIn("cosmic-ray", types_returned)

    def test_exceedance_equals_margined_minus_budget(self):
        result = assess_sensor_background(
            sensor_id="SEN-EXC",
            populations=[self._proton_pop(flux=5000.0)],
            integration_time=10.0,
            margin_factor=2.0,
            budget=100.0,
        )
        # raw = 5000*1*0.01*10 = 500; margined = 1000; budget = 100; exceedance = 900
        self.assertAlmostEqual(result["exceedance"], 900.0)
        self.assertFalse(result["compliant"])

    def test_large_margin_factor_pushes_over_budget(self):
        result_no_margin = assess_sensor_background(
            sensor_id="SEN-MX1",
            populations=[self._proton_pop(flux=100.0)],
            integration_time=10.0,
            margin_factor=1.0,
            budget=10.0,
        )
        result_high_margin = assess_sensor_background(
            sensor_id="SEN-MX2",
            populations=[self._proton_pop(flux=100.0)],
            integration_time=10.0,
            margin_factor=5.0,
            budget=10.0,
        )
        # raw = 10; at margin 1.0 → margined = 10 → compliant; at 5.0 → margined = 50 → non-compliant
        self.assertTrue(result_no_margin["compliant"])
        self.assertFalse(result_high_margin["compliant"])

    def test_return_dict_contains_all_required_keys(self):
        result = assess_sensor_background(
            sensor_id="SEN-KEYS",
            populations=[self._proton_pop()],
            integration_time=10.0,
            margin_factor=1.0,
            budget=1000.0,
        )
        for key in (
            "sensor_id", "raw_background", "margined_background",
            "margin_factor", "budget", "compliant", "exceedance",
            "population_details",
        ):
            self.assertIn(key, result)

    def test_zero_integration_time_always_compliant(self):
        result = assess_sensor_background(
            sensor_id="SEN-ZT",
            populations=[self._proton_pop(flux=1e9)],
            integration_time=0.0,
            margin_factor=100.0,
            budget=1.0,
        )
        self.assertAlmostEqual(result["raw_background"], 0.0)
        self.assertAlmostEqual(result["margined_background"], 0.0)
        self.assertTrue(result["compliant"])

    def test_sep_proton_population(self):
        pop = {
            "particle_type": "sep-proton",
            "flux": 1e6,
            "sensitive_area": 0.1,
            "bg_conversion": 0.005,
        }
        result = assess_sensor_background(
            sensor_id="SEN-SEP",
            populations=[pop],
            integration_time=3600.0,
            margin_factor=2.0,
            budget=4e9,
        )
        # raw = 1e6 * 0.1 * 0.005 * 3600 = 1800000; margined = 3600000 → compliant
        self.assertAlmostEqual(result["raw_background"], 1800000.0)
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
