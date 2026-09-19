#!/usr/bin/env python3
"""Contract test for the mechanism flushing and purging plan (offline)."""

import copy
import math
import unittest

from e3301_flushing_purging_logic import (
    DEFAULT_PURGE_POLICY,
    DEGRADATION_DRIVERS,
    GROUND_PHASES,
    INERT_GASES,
    PURGE_GASES,
    assess_gas_quality,
    cycles_to_target,
    dilution_volumes_required,
    gas_is_admissible,
    phase_coverage_gaps,
    plan_purge,
    pressure_cycle_residual_ppm,
    purge_duration_s,
    purge_required,
    residual_concentration_ppm,
    validate_purge_policy,
)

FLUSH_CASE = {
    "degradation_drivers": ["lubricant-oxidation", "moisture-uptake"],
    "route": "continuous-flush",
    "gas": "dry-nitrogen",
    "dew_point_c": -55.0,
    "purity_percent": 99.999,
    "initial_ppm": 209000.0,
    "target_residual_ppm": 100.0,
    "enclosure_volume_m3": 0.25,
    "flow_rate_m3_per_s": 1.0e-3,
    "available_duration_s": 7200.0,
    "covered_phases": list(GROUND_PHASES),
}

BACKFILL_CASE = {
    "degradation_drivers": ["corrosion"],
    "route": "pump-and-backfill",
    "gas": "dry-argon",
    "dew_point_c": -60.0,
    "purity_percent": 99.999,
    "initial_ppm": 209000.0,
    "target_residual_ppm": 209.0,
    "low_pressure_pa": 1.0e4,
    "high_pressure_pa": 1.0e5,
    "planned_cycles": 4,
    "covered_phases": list(GROUND_PHASES),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_purge_policy(DEFAULT_PURGE_POLICY), DEFAULT_PURGE_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purge_policy("default")

    def test_purity_above_one_hundred_percent_rejected(self):
        broken = copy.deepcopy(DEFAULT_PURGE_POLICY)
        broken["required_purity_percent"] = 101.0
        with self.assertRaises(ValueError):
            validate_purge_policy(broken)

    def test_empty_phase_coverage_rejected(self):
        broken = copy.deepcopy(DEFAULT_PURGE_POLICY)
        broken["required_phase_coverage"] = []
        with self.assertRaises(ValueError):
            validate_purge_policy(broken)

    def test_unknown_phase_in_policy_rejected(self):
        broken = copy.deepcopy(DEFAULT_PURGE_POLICY)
        broken["required_phase_coverage"] = ["orbit"]
        with self.assertRaises(ValueError):
            validate_purge_policy(broken)


class DriverTests(unittest.TestCase):
    def test_no_driver_means_no_purge(self):
        result = purge_required([])
        self.assertFalse(result["required"])
        self.assertEqual(result["drivers"], [])

    def test_a_declared_driver_calls_for_a_purge(self):
        self.assertTrue(purge_required(["moisture-uptake"])["required"])

    def test_oxidising_drivers_are_singled_out(self):
        result = purge_required(["moisture-uptake", "lubricant-oxidation"])
        self.assertEqual(result["oxidising_drivers"], ["lubricant-oxidation"])

    def test_repeated_drivers_are_collapsed(self):
        result = purge_required(["corrosion", "corrosion"])
        self.assertEqual(result["drivers"], ["corrosion"])

    def test_unknown_driver_rejected(self):
        with self.assertRaises(ValueError):
            purge_required(["looks-dusty"])

    def test_non_sequence_drivers_rejected(self):
        with self.assertRaises(ValueError):
            purge_required("corrosion")

    def test_every_driver_name_is_available(self):
        self.assertIn("friction-rise-in-air", DEGRADATION_DRIVERS)


class GasTests(unittest.TestCase):
    def test_inert_gas_answers_an_oxidising_driver(self):
        result = gas_is_admissible("dry-nitrogen", ["lubricant-oxidation"])
        self.assertTrue(result["admissible"])

    def test_clean_dry_air_fails_against_an_oxidising_driver(self):
        result = gas_is_admissible("clean-dry-air", ["corrosion"])
        self.assertFalse(result["admissible"])
        self.assertTrue(result["findings"])

    def test_clean_dry_air_is_allowed_against_moisture_alone(self):
        result = gas_is_admissible("clean-dry-air", ["moisture-uptake"])
        self.assertTrue(result["admissible"])

    def test_clean_dry_air_is_not_counted_as_inert(self):
        self.assertNotIn("clean-dry-air", INERT_GASES)
        self.assertIn("clean-dry-air", PURGE_GASES)

    def test_unknown_gas_rejected(self):
        with self.assertRaises(ValueError):
            gas_is_admissible("shop-air", ["moisture-uptake"])


class DilutionTests(unittest.TestCase):
    def test_one_exchange_leaves_one_over_e(self):
        self.assertAlmostEqual(
            residual_concentration_ppm(1000.0, 1.0), 1000.0 / math.e, places=9
        )

    def test_zero_exchanges_leave_the_initial_charge(self):
        self.assertAlmostEqual(residual_concentration_ppm(1000.0, 0.0), 1000.0,
                               places=9)

    def test_exchanges_and_residual_are_inverses(self):
        exchanges = dilution_volumes_required(209000.0, 100.0)
        self.assertAlmostEqual(
            residual_concentration_ppm(209000.0, exchanges), 100.0, places=6
        )

    def test_a_decade_of_dilution_costs_about_two_and_a_third_exchanges(self):
        self.assertAlmostEqual(dilution_volumes_required(1000.0, 100.0), math.log(10.0),
                               places=12)

    def test_target_at_or_above_the_initial_charge_rejected(self):
        with self.assertRaises(ValueError):
            dilution_volumes_required(100.0, 100.0)

    def test_zero_initial_charge_rejected(self):
        with self.assertRaises(ValueError):
            dilution_volumes_required(0.0, 10.0)

    def test_negative_exchange_count_rejected(self):
        with self.assertRaises(ValueError):
            residual_concentration_ppm(1000.0, -1.0)

    def test_duration_scales_with_the_enclosure_volume(self):
        small = purge_duration_s(0.1, 1.0e-3, 1000.0, 100.0)
        large = purge_duration_s(0.2, 1.0e-3, 1000.0, 100.0)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_duration_matches_volume_over_flow_times_exchanges(self):
        self.assertAlmostEqual(
            purge_duration_s(0.25, 1.0e-3, 1000.0, 100.0),
            0.25 / 1.0e-3 * math.log(10.0),
            places=9,
        )

    def test_zero_flow_rate_rejected(self):
        with self.assertRaises(ValueError):
            purge_duration_s(0.25, 0.0, 1000.0, 100.0)


class PressureCycleTests(unittest.TestCase):
    def test_one_cycle_divides_by_the_pressure_ratio(self):
        self.assertAlmostEqual(
            pressure_cycle_residual_ppm(1000.0, 1.0e4, 1.0e5, 1), 100.0, places=9
        )

    def test_zero_cycles_leave_the_initial_charge(self):
        self.assertAlmostEqual(
            pressure_cycle_residual_ppm(1000.0, 1.0e4, 1.0e5, 0), 1000.0, places=9
        )

    def test_three_decades_need_three_cycles_at_a_decade_each(self):
        self.assertEqual(cycles_to_target(1000.0, 1.0, 1.0e4, 1.0e5), 3)

    def test_a_partial_decade_rounds_up_to_a_whole_cycle(self):
        self.assertEqual(cycles_to_target(1000.0, 0.9, 1.0e4, 1.0e5), 4)

    def test_a_shallower_vacuum_needs_more_cycles(self):
        deep = cycles_to_target(209000.0, 100.0, 1.0e3, 1.0e5)
        shallow = cycles_to_target(209000.0, 100.0, 5.0e4, 1.0e5)
        self.assertGreater(shallow, deep)

    def test_backfill_pressure_at_or_below_the_vacuum_rejected(self):
        with self.assertRaises(ValueError):
            pressure_cycle_residual_ppm(1000.0, 1.0e5, 1.0e5, 2)

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            pressure_cycle_residual_ppm(1000.0, 1.0e4, 1.0e5, 2.5)

    def test_cycles_to_target_rejects_an_inverted_pressure_pair(self):
        with self.assertRaises(ValueError):
            cycles_to_target(1000.0, 10.0, 1.0e5, 1.0e4)


class GasQualityTests(unittest.TestCase):
    def test_dry_high_purity_gas_passes(self):
        result = assess_gas_quality(-55.0, 99.999)
        self.assertTrue(result["dew_point_ok"])
        self.assertTrue(result["purity_ok"])
        self.assertEqual(result["findings"], [])

    def test_dew_point_exactly_on_the_limit_passes(self):
        result = assess_gas_quality(DEFAULT_PURGE_POLICY["required_dew_point_c"],
                                    99.999)
        self.assertTrue(result["dew_point_ok"])

    def test_damp_gas_fails_on_dew_point(self):
        result = assess_gas_quality(-10.0, 99.999)
        self.assertFalse(result["dew_point_ok"])
        self.assertTrue(any("dew point" in f for f in result["findings"]))

    def test_low_purity_gas_fails_on_purity(self):
        result = assess_gas_quality(-55.0, 99.5)
        self.assertFalse(result["purity_ok"])

    def test_purity_above_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            assess_gas_quality(-55.0, 100.5)

    def test_non_numeric_dew_point_rejected(self):
        with self.assertRaises(ValueError):
            assess_gas_quality("minus fifty", 99.999)


class PhaseCoverageTests(unittest.TestCase):
    def test_full_coverage_leaves_no_gap(self):
        self.assertEqual(phase_coverage_gaps(list(GROUND_PHASES)), [])

    def test_a_missing_phase_is_reported(self):
        covered = [p for p in GROUND_PHASES if p != "transport"]
        self.assertEqual(phase_coverage_gaps(covered), ["transport"])

    def test_unknown_covered_phase_rejected(self):
        with self.assertRaises(ValueError):
            phase_coverage_gaps(["orbit"])


class PlanTests(unittest.TestCase):
    def test_no_driver_closes_the_clause_without_a_purge(self):
        result = plan_purge({"degradation_drivers": []})
        self.assertFalse(result["purge_required"])
        self.assertEqual(result["verdict"], "purge-not-required")
        self.assertTrue(result["adequate"])

    def test_flush_case_is_adequate(self):
        result = plan_purge(FLUSH_CASE)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["verdict"], "purge-plan-adequate")
        self.assertIn("duration_s", result["sizing"])

    def test_flush_sizing_matches_the_closed_form(self):
        result = plan_purge(FLUSH_CASE)
        self.assertAlmostEqual(
            result["sizing"]["volume_exchanges"],
            math.log(209000.0 / 100.0),
            places=12,
        )

    def test_a_short_window_makes_the_flush_deficient(self):
        result = plan_purge(_case(FLUSH_CASE, available_duration_s=60.0))
        self.assertFalse(result["adequate"])
        self.assertTrue(any("available" in f for f in result["findings"]))

    def test_a_lapsed_phase_makes_the_plan_deficient(self):
        covered = [p for p in GROUND_PHASES if p != "storage"]
        result = plan_purge(_case(FLUSH_CASE, covered_phases=covered))
        self.assertFalse(result["adequate"])
        self.assertEqual(result["phase_coverage_gaps"], ["storage"])

    def test_non_inert_gas_makes_the_plan_deficient(self):
        result = plan_purge(_case(FLUSH_CASE, gas="clean-dry-air"))
        self.assertFalse(result["gas_admissible"])
        self.assertEqual(result["verdict"], "purge-plan-deficient")

    def test_backfill_case_is_adequate(self):
        result = plan_purge(BACKFILL_CASE)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["sizing"]["cycles_required"], 3)

    def test_too_few_planned_cycles_are_reported(self):
        result = plan_purge(_case(BACKFILL_CASE, planned_cycles=2))
        self.assertFalse(result["adequate"])
        self.assertTrue(any("cycles" in f for f in result["findings"]))

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge(_case(FLUSH_CASE, route="hope"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            plan_purge("flush it")

    def test_missing_initial_charge_rejected(self):
        case = copy.deepcopy(FLUSH_CASE)
        del case["initial_ppm"]
        with self.assertRaises(ValueError):
            plan_purge(case)


if __name__ == "__main__":
    unittest.main()
