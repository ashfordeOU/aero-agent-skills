#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.2.2.2 power demand
versus availability.

Exercises scripts/e20_power_demand_versus_availability_analysis_logic.py
(stdlib unittest, offline). Contract: docs/harness-contract.md gate 3 -
a load declares one of the recognized categories and an uncategorized
one raises; a load's averaged draw is its peak times its duty cycle,
with a duty outside [0, 1] raising; a phase's averaged demand sums
every load while its coincident-peak demand takes the full peak of the
loads that fire together; generated power decays with the annual
degradation over the phase epoch; a deficit is a finding only when the
store cannot cover it, either at all or within its discharge limit; a
phase without generation is graded on unused discharge depth instead of
a power ratio; and the mission is power positive only when every phase
carries no finding.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_power_demand_versus_availability_analysis_logic as pa  # noqa: E402


def _load(load_id, category, peak_power_w, duty_cycle):
    return {
        "load_id": load_id,
        "category": category,
        "peak_power_w": peak_power_w,
        "duty_cycle": duty_cycle,
    }


# Averaged demand 50 + 100 + 30 = 180 W; coincident-peak demand
# 50 + 100 + 120 = 270 W.
STANDARD_LOADS = [
    _load("obc", "continuous", 50.0, 0.25),
    _load("payload", "duty_cycled", 200.0, 0.5),
    _load("transmitter", "coincident_peak", 120.0, 0.25),
]


def _phase(**overrides):
    phase = {
        "phase_id": "nominal_operations",
        "loads": STANDARD_LOADS,
        "bol_power_w": 500.0,
        "annual_degradation_fraction": 0.0,
        "years_at_phase": 0.0,
        "duration_s": 3600.0,
        "battery_capacity_wh": 100.0,
        "max_depth_of_discharge": 0.6,
        "battery_discharge_capability_w": 100.0,
        "required_margin": 0.20,
    }
    phase.update(overrides)
    return phase


class LoadCategoryTest(unittest.TestCase):
    def test_continuous_is_recognized(self):
        self.assertEqual(pa.load_category(STANDARD_LOADS[0]), "continuous")

    def test_duty_cycled_is_recognized(self):
        self.assertEqual(pa.load_category(STANDARD_LOADS[1]), "duty_cycled")

    def test_coincident_peak_is_recognized(self):
        self.assertEqual(pa.load_category(STANDARD_LOADS[2]), "coincident_peak")

    def test_missing_category_raises(self):
        with self.assertRaises(ValueError):
            pa.load_category({"load_id": "heater", "peak_power_w": 10.0})

    def test_uncategorized_load_raises(self):
        with self.assertRaises(ValueError):
            pa.load_category(_load("heater", "occasional", 10.0, 0.1))


class LoadAveragePowerTest(unittest.TestCase):
    def test_average_is_peak_times_duty(self):
        self.assertAlmostEqual(pa.load_average_power(200.0, 0.5), 100.0)

    def test_zero_duty_draws_nothing(self):
        self.assertAlmostEqual(pa.load_average_power(200.0, 0.0), 0.0)

    def test_full_duty_draws_the_peak(self):
        self.assertAlmostEqual(pa.load_average_power(200.0, 1.0), 200.0)

    def test_negative_peak_raises(self):
        with self.assertRaises(ValueError):
            pa.load_average_power(-1.0, 0.5)

    def test_duty_above_unity_raises(self):
        with self.assertRaises(ValueError):
            pa.load_average_power(100.0, 1.5)

    def test_negative_duty_raises(self):
        with self.assertRaises(ValueError):
            pa.load_average_power(100.0, -0.1)


class PhaseDemandTest(unittest.TestCase):
    def test_averaged_demand_sums_every_load(self):
        demand = pa.phase_demand(STANDARD_LOADS)
        self.assertAlmostEqual(demand["average_w"], 180.0)
        self.assertEqual(demand["load_count"], 3)

    def test_coincident_peak_takes_full_peak_of_peaking_loads(self):
        demand = pa.phase_demand(STANDARD_LOADS)
        self.assertAlmostEqual(demand["peak_w"], 270.0)

    def test_continuous_load_ignores_its_duty_field(self):
        demand = pa.phase_demand([_load("obc", "continuous", 50.0, 0.25)])
        self.assertAlmostEqual(demand["average_w"], 50.0)

    def test_empty_load_list_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_demand([])

    def test_duplicate_load_id_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_demand(
                [_load("obc", "continuous", 10.0, 1.0), _load("obc", "continuous", 20.0, 1.0)]
            )

    def test_blank_load_id_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_demand([_load("", "continuous", 10.0, 1.0)])


class AvailablePowerTest(unittest.TestCase):
    def test_no_degradation_returns_bol(self):
        self.assertAlmostEqual(pa.degraded_available_power(1000.0, 0.0, 7.0), 1000.0)

    def test_zero_years_returns_bol(self):
        self.assertAlmostEqual(pa.degraded_available_power(1000.0, 0.02, 0.0), 1000.0)

    def test_power_decays_over_the_epoch(self):
        self.assertAlmostEqual(
            pa.degraded_available_power(1000.0, 0.02, 5.0), 903.9207968, places=5
        )

    def test_negative_bol_raises(self):
        with self.assertRaises(ValueError):
            pa.degraded_available_power(-1.0, 0.02, 1.0)

    def test_total_annual_degradation_raises(self):
        with self.assertRaises(ValueError):
            pa.degraded_available_power(1000.0, 1.0, 1.0)

    def test_negative_years_raises(self):
        with self.assertRaises(ValueError):
            pa.degraded_available_power(1000.0, 0.02, -1.0)


class MarginAndStoreTest(unittest.TestCase):
    def test_margin_is_unspent_fraction(self):
        self.assertAlmostEqual(pa.power_margin_fraction(500.0, 180.0), 0.64)

    def test_overrun_gives_negative_margin(self):
        self.assertAlmostEqual(pa.power_margin_fraction(100.0, 180.0), -0.8)

    def test_zero_availability_margin_raises(self):
        with self.assertRaises(ValueError):
            pa.power_margin_fraction(0.0, 10.0)

    def test_negative_demand_margin_raises(self):
        with self.assertRaises(ValueError):
            pa.power_margin_fraction(100.0, -1.0)

    def test_battery_energy_is_deficit_over_the_hour(self):
        self.assertAlmostEqual(pa.battery_energy_required_wh(80.0, 3600.0), 80.0)

    def test_battery_energy_scales_with_duration(self):
        self.assertAlmostEqual(pa.battery_energy_required_wh(50.0, 2160.0), 30.0)

    def test_negative_deficit_raises(self):
        with self.assertRaises(ValueError):
            pa.battery_energy_required_wh(-1.0, 3600.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            pa.battery_energy_required_wh(10.0, -1.0)

    def test_depth_of_discharge_is_capacity_fraction(self):
        self.assertAlmostEqual(pa.depth_of_discharge(30.0, 100.0), 0.3)

    def test_zero_capacity_raises(self):
        with self.assertRaises(ValueError):
            pa.depth_of_discharge(10.0, 0.0)

    def test_negative_draw_raises(self):
        with self.assertRaises(ValueError):
            pa.depth_of_discharge(-1.0, 100.0)


class PhaseAnalysisTest(unittest.TestCase):
    def test_healthy_phase_is_power_positive(self):
        analysis = pa.phase_analysis(_phase())
        self.assertAlmostEqual(analysis["available_w"], 500.0)
        self.assertAlmostEqual(analysis["achieved_margin"], 0.64)
        self.assertAlmostEqual(analysis["peak_capability_w"], 600.0)
        self.assertTrue(pa.phase_is_power_positive(analysis))

    def test_coincident_peak_shortfall_is_flagged(self):
        analysis = pa.phase_analysis(
            _phase(
                bol_power_w=200.0,
                battery_discharge_capability_w=20.0,
                required_margin=0.05,
            )
        )
        self.assertEqual(analysis["energy_balance"], [])
        self.assertEqual(analysis["margin"], [])
        self.assertEqual(
            analysis["peak_capability"][0]["issue"],
            "coincident_peak_exceeds_supply_capability",
        )
        self.assertFalse(pa.phase_is_power_positive(analysis))

    def test_deficit_beyond_discharge_limit_is_flagged(self):
        analysis = pa.phase_analysis(
            _phase(phase_id="safe_mode", bol_power_w=100.0, battery_discharge_capability_w=500.0)
        )
        self.assertAlmostEqual(analysis["battery_energy_wh"], 80.0)
        self.assertAlmostEqual(analysis["depth_of_discharge"], 0.8)
        self.assertEqual(analysis["energy_balance"], [])
        self.assertEqual(
            analysis["battery_depth"][0]["issue"], "battery_discharge_depth_exceeded"
        )
        self.assertEqual(
            analysis["margin"][0]["issue"], "phase_power_margin_below_requirement"
        )

    def test_deficit_beyond_capacity_does_not_close(self):
        analysis = pa.phase_analysis(
            _phase(
                phase_id="leop",
                bol_power_w=100.0,
                battery_capacity_wh=50.0,
                battery_discharge_capability_w=500.0,
            )
        )
        self.assertEqual(
            analysis["energy_balance"][0]["issue"], "phase_energy_balance_not_closed"
        )
        self.assertEqual(analysis["battery_depth"], [])

    def test_eclipse_without_generation_is_graded_on_discharge_depth(self):
        analysis = pa.phase_analysis(
            _phase(
                phase_id="eclipse",
                loads=[_load("obc", "continuous", 50.0, 1.0)],
                bol_power_w=0.0,
                duration_s=2160.0,
                battery_discharge_capability_w=200.0,
            )
        )
        self.assertAlmostEqual(analysis["available_w"], 0.0)
        self.assertAlmostEqual(analysis["depth_of_discharge"], 0.3)
        self.assertAlmostEqual(analysis["achieved_margin"], 0.5)
        self.assertTrue(pa.phase_is_power_positive(analysis))

    def test_deep_eclipse_flags_the_stored_energy_margin(self):
        analysis = pa.phase_analysis(
            _phase(
                phase_id="eclipse",
                loads=[_load("obc", "continuous", 50.0, 1.0)],
                bol_power_w=0.0,
                duration_s=2160.0,
                battery_capacity_wh=55.0,
                battery_discharge_capability_w=200.0,
                required_margin=0.20,
            )
        )
        self.assertEqual(
            analysis["margin"][0]["issue"], "stored_energy_margin_below_requirement"
        )
        self.assertFalse(pa.phase_is_power_positive(analysis))

    def test_uncategorized_phase_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_analysis(_phase(phase_id="coast_to_mars"))

    def test_required_margin_of_unity_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_analysis(_phase(required_margin=1.0))

    def test_zero_discharge_depth_limit_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_analysis(_phase(max_depth_of_discharge=0.0))

    def test_negative_discharge_capability_raises(self):
        with self.assertRaises(ValueError):
            pa.phase_analysis(_phase(battery_discharge_capability_w=-1.0))


class MissionAnalysisTest(unittest.TestCase):
    def test_mission_keys_every_phase(self):
        analysis = pa.mission_analysis(
            [
                _phase(phase_id="nominal_operations"),
                _phase(
                    phase_id="eclipse",
                    loads=[_load("obc", "continuous", 50.0, 1.0)],
                    bol_power_w=0.0,
                    duration_s=2160.0,
                    battery_discharge_capability_w=200.0,
                ),
            ]
        )
        self.assertEqual(set(analysis), {"nominal_operations", "eclipse"})
        self.assertTrue(pa.is_mission_power_positive(analysis))

    def test_one_failing_phase_sinks_the_mission(self):
        analysis = pa.mission_analysis(
            [
                _phase(phase_id="nominal_operations"),
                _phase(
                    phase_id="safe_mode",
                    bol_power_w=100.0,
                    battery_discharge_capability_w=500.0,
                ),
            ]
        )
        self.assertTrue(pa.phase_is_power_positive(analysis["nominal_operations"]))
        self.assertFalse(pa.is_mission_power_positive(analysis))

    def test_empty_mission_raises(self):
        with self.assertRaises(ValueError):
            pa.mission_analysis([])

    def test_duplicate_phase_raises(self):
        with self.assertRaises(ValueError):
            pa.mission_analysis([_phase(), _phase()])


if __name__ == "__main__":
    unittest.main()
