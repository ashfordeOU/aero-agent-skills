"""Contract tests for the clause 4.7.3.2 dry-lubrication design logic."""

import math
import unittest

from e3301_dry_lubrication_design_logic import (
    DRY_CYCLE_CEILING,
    DRY_LUBRICANTS,
    DRY_SPEED_CEILING_M_S,
    FLUID_TEMPERATURE_CEILING_C,
    MARGIN_TOLERANCE,
    archard_wear_volume_mm3,
    assess_dry_lubrication,
    at_least,
    deposition_process_findings,
    duty_indication,
    environment_compatibility,
    film_wear_life_cycles,
    sliding_distance_m,
    validate_non_negative,
    validate_positive,
    wear_depth_um,
)

DUTY = {
    "temperature_c": (-100.0, 150.0),
    "sliding_speed_m_s": 0.05,
    "required_cycles": 10000.0,
}

WEAR = {
    "usable_film_thickness_um": 0.8,
    "stroke_mm": 5.0,
    "load_n": 20.0,
    "contact_area_mm2": 4.0,
}

PROCESS = {
    "film_thickness_um": 1.0,
    "deposition_rate_um_per_min": 0.05,
    "substrate_roughness_ra_um": 0.2,
    "batch_thickness_spread_um": 0.1,
}

WINDOW = {
    "film_thickness_um": (0.5, 1.5),
    "deposition_rate_um_per_min": (0.02, 0.1),
    "max_substrate_roughness_ra_um": 0.4,
    "max_batch_uniformity_ratio": 0.15,
}


def _spec(**overrides):
    spec = {
        "material": "mos2",
        "duty": dict(DUTY),
        "wear": dict(WEAR),
        "process": dict(PROCESS),
        "window": dict(WINDOW),
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_validator_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 2), 2.0)

    def test_positive_validator_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_non_negative_validator_accepts_zero(self):
        self.assertAlmostEqual(validate_non_negative("x", 0), 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_at_least_accepts_exact_equality(self):
        self.assertTrue(at_least(16000.0, 16000.0))

    def test_at_least_rejects_a_shortfall(self):
        self.assertFalse(at_least(9999.0, 10000.0))


class WearModelTests(unittest.TestCase):
    def test_sliding_distance_is_two_strokes_per_cycle(self):
        self.assertAlmostEqual(sliding_distance_m(5.0, 1000.0), 10.0, places=12)

    def test_zero_cycles_gives_zero_distance(self):
        self.assertAlmostEqual(sliding_distance_m(5.0, 0.0), 0.0)

    def test_zero_stroke_rejected(self):
        with self.assertRaises(ValueError):
            sliding_distance_m(0.0, 1000.0)

    def test_archard_volume_is_linear_in_load(self):
        single = archard_wear_volume_mm3(1.0e-6, 20.0, 10.0)
        double = archard_wear_volume_mm3(1.0e-6, 40.0, 10.0)
        self.assertAlmostEqual(double / single, 2.0, places=12)

    def test_archard_volume_matches_the_closed_form(self):
        self.assertAlmostEqual(
            archard_wear_volume_mm3(1.0e-6, 20.0, 10.0), 2.0e-4, places=12
        )

    def test_zero_load_rejected_by_archard(self):
        with self.assertRaises(ValueError):
            archard_wear_volume_mm3(1.0e-6, 0.0, 10.0)

    def test_wear_depth_spreads_the_volume_over_the_area(self):
        self.assertAlmostEqual(wear_depth_um(2.0e-4, 4.0), 0.05, places=12)

    def test_zero_contact_area_rejected(self):
        with self.assertRaises(ValueError):
            wear_depth_um(2.0e-4, 0.0)

    def test_film_life_matches_the_hand_calculation(self):
        spec = dict(WEAR)
        spec["wear_coefficient_mm3_per_nm"] = 1.0e-6
        self.assertAlmostEqual(film_wear_life_cycles(spec), 16000.0, delta=1e-6)

    def test_thicker_film_lasts_proportionally_longer(self):
        thin = dict(WEAR)
        thin["wear_coefficient_mm3_per_nm"] = 1.0e-6
        thick = dict(thin)
        thick["usable_film_thickness_um"] = 1.6
        self.assertAlmostEqual(
            film_wear_life_cycles(thick) / film_wear_life_cycles(thin), 2.0, places=9
        )

    def test_missing_wear_key_rejected(self):
        spec = dict(WEAR)
        spec["wear_coefficient_mm3_per_nm"] = 1.0e-6
        del spec["stroke_mm"]
        with self.assertRaises(ValueError):
            film_wear_life_cycles(spec)


class DutyIndicationTests(unittest.TestCase):
    def test_slow_low_cycle_duty_is_indicated(self):
        self.assertTrue(duty_indication(DUTY)["indicated"])

    def test_hot_duty_is_indicated_even_when_fast(self):
        duty = dict(DUTY)
        duty["temperature_c"] = (-100.0, 300.0)
        duty["sliding_speed_m_s"] = 5.0
        duty["required_cycles"] = 1.0e7
        result = duty_indication(duty)
        self.assertTrue(result["indicated"])
        self.assertTrue(result["hot_duty"])

    def test_fast_high_cycle_cool_duty_is_counter_indicated(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = 3.0
        duty["required_cycles"] = 1.0e7
        result = duty_indication(duty)
        self.assertFalse(result["indicated"])
        self.assertIn("fluid lubricant", result["findings"][0])

    def test_speed_exactly_on_the_ceiling_counts_as_slow(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = DRY_SPEED_CEILING_M_S
        self.assertTrue(duty_indication(duty)["slow_duty"])

    def test_cycles_exactly_on_the_ceiling_count_as_low(self):
        duty = dict(DUTY)
        duty["required_cycles"] = DRY_CYCLE_CEILING
        self.assertTrue(duty_indication(duty)["low_cycle_duty"])

    def test_inverted_duty_temperature_rejected(self):
        duty = dict(DUTY)
        duty["temperature_c"] = (150.0, -100.0)
        with self.assertRaises(ValueError):
            duty_indication(duty)

    def test_missing_duty_key_rejected(self):
        duty = dict(DUTY)
        del duty["sliding_speed_m_s"]
        with self.assertRaises(ValueError):
            duty_indication(duty)

    def test_fluid_ceiling_is_above_normal_orbit_temperatures(self):
        self.assertGreater(FLUID_TEMPERATURE_CEILING_C, 100.0)


class EnvironmentTests(unittest.TestCase):
    def test_mos2_in_vacuum_is_compatible(self):
        result = environment_compatibility("mos2", (-100.0, 150.0))
        self.assertTrue(result["compatible"])

    def test_graphite_in_vacuum_is_flagged(self):
        result = environment_compatibility("graphite", (-50.0, 150.0))
        self.assertFalse(result["compatible"])
        self.assertIn("adsorbed moisture", result["findings"][0])

    def test_graphite_in_air_is_acceptable(self):
        result = environment_compatibility(
            "graphite", (-50.0, 150.0), operates_in_vacuum=False
        )
        self.assertTrue(result["compatible"])

    def test_mos2_in_humid_ground_air_needs_a_purge(self):
        result = environment_compatibility(
            "mos2", (-100.0, 150.0), ground_humidity_pct=50.0
        )
        self.assertFalse(result["compatible"])

    def test_a_declared_purge_clears_the_humidity_finding(self):
        result = environment_compatibility(
            "mos2", (-100.0, 150.0), ground_humidity_pct=50.0, ground_purge=True
        )
        self.assertTrue(result["compatible"])

    def test_ptfe_above_its_rating_is_flagged(self):
        result = environment_compatibility("ptfe", (-100.0, 300.0))
        self.assertFalse(result["compatible"])
        self.assertTrue(any("hot" in finding for finding in result["findings"]))

    def test_duty_exactly_on_the_rated_limit_passes(self):
        result = environment_compatibility("ptfe", (-200.0, 260.0))
        self.assertTrue(result["compatible"])

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            environment_compatibility("indium", (-100.0, 150.0))

    def test_humidity_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            environment_compatibility("mos2", (-100.0, 150.0), ground_humidity_pct=150.0)

    def test_registry_covers_the_four_common_solids(self):
        self.assertEqual(set(DRY_LUBRICANTS), {"mos2", "ws2", "graphite", "ptfe"})


class ProcessWindowTests(unittest.TestCase):
    def test_in_window_process_is_in_control(self):
        self.assertTrue(deposition_process_findings(PROCESS, WINDOW)["in_control"])

    def test_thin_film_is_outside_the_window(self):
        parameters = dict(PROCESS)
        parameters["film_thickness_um"] = 0.2
        result = deposition_process_findings(parameters, WINDOW)
        self.assertFalse(result["in_control"])
        self.assertIn("film thickness", result["findings"][0])

    def test_fast_deposition_rate_is_outside_the_window(self):
        parameters = dict(PROCESS)
        parameters["deposition_rate_um_per_min"] = 0.5
        self.assertFalse(deposition_process_findings(parameters, WINDOW)["in_control"])

    def test_rough_substrate_is_flagged(self):
        parameters = dict(PROCESS)
        parameters["substrate_roughness_ra_um"] = 0.9
        result = deposition_process_findings(parameters, WINDOW)
        self.assertFalse(result["in_control"])
        self.assertTrue(any("roughness" in finding for finding in result["findings"]))

    def test_batch_spread_is_reported_as_a_ratio(self):
        result = deposition_process_findings(PROCESS, WINDOW)
        self.assertAlmostEqual(result["uniformity_ratio"], 0.1, places=12)

    def test_spread_exactly_on_the_uniformity_limit_passes(self):
        parameters = dict(PROCESS)
        parameters["batch_thickness_spread_um"] = 0.15
        self.assertTrue(deposition_process_findings(parameters, WINDOW)["in_control"])

    def test_spread_above_the_uniformity_limit_is_flagged(self):
        parameters = dict(PROCESS)
        parameters["batch_thickness_spread_um"] = 0.4
        self.assertFalse(deposition_process_findings(parameters, WINDOW)["in_control"])

    def test_value_exactly_on_the_window_edge_passes(self):
        parameters = dict(PROCESS)
        parameters["film_thickness_um"] = 1.5
        parameters["batch_thickness_spread_um"] = 0.15
        self.assertTrue(deposition_process_findings(parameters, WINDOW)["in_control"])

    def test_inverted_window_rejected(self):
        window = dict(WINDOW)
        window["film_thickness_um"] = (1.5, 0.5)
        with self.assertRaises(ValueError):
            deposition_process_findings(PROCESS, window)

    def test_missing_process_parameter_rejected(self):
        parameters = dict(PROCESS)
        del parameters["substrate_roughness_ra_um"]
        with self.assertRaises(ValueError):
            deposition_process_findings(parameters, WINDOW)


class AssessmentTests(unittest.TestCase):
    def test_sound_design_is_compliant(self):
        result = assess_dry_lubrication(_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_wear_life_and_margin_are_reported(self):
        result = assess_dry_lubrication(_spec())
        self.assertAlmostEqual(result["wear_life_cycles"], 16000.0, delta=1e-6)
        self.assertAlmostEqual(result["wear_margin"], 1.6, places=9)

    def test_material_wear_coefficient_is_taken_from_the_registry(self):
        result = assess_dry_lubrication(_spec(material="ptfe"))
        self.assertLess(result["wear_life_cycles"], 16000.0)

    def test_thin_film_short_of_the_required_cycles_is_flagged(self):
        wear = dict(WEAR)
        wear["usable_film_thickness_um"] = 0.1
        result = assess_dry_lubrication(_spec(wear=wear))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("consumed after" in finding for finding in result["findings"]))

    def test_counter_indicated_duty_reaches_the_findings(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = 4.0
        duty["required_cycles"] = 1.0e6
        result = assess_dry_lubrication(_spec(duty=duty))
        self.assertFalse(result["compliant"])

    def test_graphite_in_vacuum_reaches_the_findings(self):
        result = assess_dry_lubrication(_spec(material="graphite"))
        self.assertFalse(result["compliant"])

    def test_process_findings_are_merged_with_the_rest(self):
        process = dict(PROCESS)
        process["substrate_roughness_ra_um"] = 1.2
        result = assess_dry_lubrication(_spec(process=process))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("roughness" in finding for finding in result["findings"]))

    def test_static_interface_leaves_the_wear_margin_unbounded(self):
        duty = dict(DUTY)
        duty["required_cycles"] = 0.0
        result = assess_dry_lubrication(_spec(duty=duty))
        self.assertTrue(math.isinf(result["wear_margin"]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["window"]
        with self.assertRaises(ValueError):
            assess_dry_lubrication(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_dry_lubrication(["material"])

    def test_margin_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
