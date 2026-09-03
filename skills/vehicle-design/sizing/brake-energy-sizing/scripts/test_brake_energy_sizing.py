"""Contract test for brake_energy_sizing_logic (vehicle-design/sizing/brake-energy-sizing).

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/vehicle-design/sizing/brake-energy-sizing/scripts/test_brake_energy_sizing.py

Asserts the wave-28 spec worked example (regional transport): RTO energy
171.5 MJ at V1 = 70 m/s on MTOW 70000 kg, landing energy 122.5 MJ at
65 m/s on MLW 58000 kg, 4 braked wheels, carbon cp 1200 J/(kg K),
allowable rise 300 K, 130 kg heat sink per brake, 0.35 g braking:
per-brake RTO 42.875 MJ, required mass 119.10 kg, rise 274.84 K,
margin 25.16 K, braking distance 713.8 m, verdict brake-energy-pass,
and brake-energy-fail with a 100 kg heat sink (rise 357.29 K).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brake_energy_sizing_logic import (  # noqa: E402
    CP_CARBON,
    G0,
    REVERSE_THRUST_CREDIT_DEFAULT,
    analyze,
    braking_distance_m,
    landing_energy_J,
    per_brake_energy_J,
    required_heat_sink_mass_kg,
    rto_energy_J,
    temperature_rise_K,
)

EXAMPLE = {
    "mtow_kg": 70000.0,
    "v1_m_s": 70.0,
    "mlw_kg": 58000.0,
    "touchdown_speed_m_s": 65.0,
    "n_braked_wheels": 4,
    "delta_t_allowable_K": 300.0,
    "heat_sink_mass_available_kg": 130.0,
    "decel_g": 0.35,
}


class BrakeEnergySizingContractTest(unittest.TestCase):
    """Spec anchors: energies, per-brake split, mass, rise, distance, verdicts."""

    def test_rto_energy_worked_example(self):
        self.assertAlmostEqual(rto_energy_J(70000.0, 70.0), 171.5e6, delta=1e3)

    def test_rto_energy_scales_quadratically_with_speed(self):
        doubled = rto_energy_J(70000.0, 140.0)
        self.assertAlmostEqual(doubled, 4.0 * 171.5e6, delta=1e3)

    def test_landing_energy_worked_example(self):
        self.assertAlmostEqual(landing_energy_J(58000.0, 65.0), 122.525e6, delta=1.0)

    def test_landing_energy_scales_quadratically_with_speed(self):
        doubled = landing_energy_J(58000.0, 130.0)
        self.assertAlmostEqual(doubled, 4.0 * 122.525e6, delta=1.0)

    def test_per_brake_rto_energy_worked_example(self):
        self.assertAlmostEqual(per_brake_energy_J(171.5e6, 4), 42.875e6, delta=1.0)

    def test_per_brake_landing_energy_worked_example(self):
        self.assertAlmostEqual(per_brake_energy_J(122.525e6, 4), 30.63125e6, delta=1.0)

    def test_per_brake_energy_with_reverse_credit(self):
        # 20% reverse-thrust credit removes 20% of the RTO energy.
        self.assertAlmostEqual(
            per_brake_energy_J(171.5e6, 4, reverse_credit=0.2), 34.3e6, delta=1.0
        )

    def test_per_brake_default_credit_is_zero(self):
        self.assertEqual(REVERSE_THRUST_CREDIT_DEFAULT, 0.0)
        self.assertAlmostEqual(
            per_brake_energy_J(171.5e6, 4), per_brake_energy_J(171.5e6, 4, 0.0)
        )

    def test_required_heat_sink_mass_worked_example(self):
        mass = required_heat_sink_mass_kg(42.875e6, CP_CARBON, 300.0)
        self.assertAlmostEqual(mass, 119.10, delta=0.01)

    def test_required_heat_sink_mass_inverse_in_delta_t(self):
        # Half the allowable rise needs twice the heat-sink mass.
        base = required_heat_sink_mass_kg(42.875e6, CP_CARBON, 300.0)
        half = required_heat_sink_mass_kg(42.875e6, CP_CARBON, 150.0)
        self.assertAlmostEqual(half, 2.0 * base, delta=0.01)

    def test_temperature_rise_worked_example_130kg(self):
        rise = temperature_rise_K(42.875e6, 130.0, CP_CARBON)
        self.assertAlmostEqual(rise, 274.84, delta=0.01)

    def test_temperature_rise_with_100kg_heat_sink(self):
        rise = temperature_rise_K(42.875e6, 100.0, CP_CARBON)
        self.assertAlmostEqual(rise, 357.29, delta=0.01)

    def test_delta_t_margin_worked_example(self):
        result = analyze(EXAMPLE)
        self.assertAlmostEqual(result["delta_t_margin_K"], 25.16, delta=0.01)

    def test_verdict_pass_worked_example(self):
        result = analyze(EXAMPLE)
        self.assertEqual(result["verdict"], "brake-energy-pass")

    def test_verdict_fail_with_100kg_heat_sink(self):
        inputs = dict(EXAMPLE, heat_sink_mass_available_kg=100.0)
        result = analyze(inputs)
        self.assertEqual(result["verdict"], "brake-energy-fail")
        self.assertLess(result["delta_t_margin_K"], 0.0)

    def test_governing_case_is_rto_for_example(self):
        result = analyze(EXAMPLE)
        self.assertEqual(result["governing_case"], "rto")
        self.assertAlmostEqual(result["per_brake_governing_J"], 42.875e6, delta=1.0)

    def test_governing_case_landing_when_landing_heavier(self):
        # Light takeoff energy leaves the landing stop governing.
        inputs = dict(EXAMPLE, mtow_kg=40000.0, v1_m_s=60.0)
        result = analyze(inputs)
        self.assertEqual(result["governing_case"], "landing")
        self.assertAlmostEqual(result["per_brake_governing_J"], 30.63125e6, delta=1.0)
        self.assertEqual(result["verdict"], "brake-energy-pass")

    def test_braking_distance_worked_example(self):
        self.assertAlmostEqual(braking_distance_m(70.0, 0.35), 713.8, delta=0.1)

    def test_braking_distance_scales_with_speed_squared(self):
        base = braking_distance_m(70.0, 0.35)
        doubled = braking_distance_m(140.0, 0.35)
        self.assertAlmostEqual(doubled, 4.0 * base, delta=0.1)

    def test_braking_distance_matches_constant_deceleration_kinematics(self):
        distance = braking_distance_m(70.0, 0.35)
        expected = 70.0 * 70.0 / (2.0 * 0.35 * G0)
        self.assertAlmostEqual(distance, expected, delta=1e-9)

    def test_analyze_reports_full_output_set(self):
        result = analyze(EXAMPLE)
        self.assertAlmostEqual(result["E_rto_J"], 171.5e6, delta=1e3)
        self.assertAlmostEqual(result["E_land_J"], 122.525e6, delta=1.0)
        self.assertAlmostEqual(result["per_brake_rto_J"], 42.875e6, delta=1.0)
        self.assertAlmostEqual(result["per_brake_landing_J"], 30.63125e6, delta=1.0)
        self.assertAlmostEqual(result["required_heat_sink_mass_kg"], 119.10, delta=0.01)
        self.assertAlmostEqual(result["actual_temperature_rise_K"], 274.84, delta=0.01)
        self.assertAlmostEqual(result["braking_distance_m"], 713.8, delta=0.1)
        for key in ("governing_case", "verdict"):
            self.assertIn(key, result)

    def test_roundtrip_required_mass_recovers_allowable_rise(self):
        mass = required_heat_sink_mass_kg(42.875e6, CP_CARBON, 300.0)
        rise = temperature_rise_K(42.875e6, mass, CP_CARBON)
        self.assertAlmostEqual(rise, 300.0, places=6)

    def test_valueerror_rto_energy_non_physical(self):
        for mtow, v1 in [(0.0, 70.0), (70000.0, 0.0), (70000.0, -5.0), (-100.0, 70.0)]:
            with self.subTest(mtow=mtow, v1=v1):
                with self.assertRaises(ValueError):
                    rto_energy_J(mtow, v1)

    def test_valueerror_landing_energy_non_physical(self):
        for mlw, v_td in [(0.0, 65.0), (58000.0, -1.0), (-58000.0, 65.0)]:
            with self.subTest(mlw=mlw, v_td=v_td):
                with self.assertRaises(ValueError):
                    landing_energy_J(mlw, v_td)

    def test_valueerror_per_brake_energy_non_physical(self):
        for energy, n, credit in [(0.0, 4, 0.0), (-1e6, 4, 0.0),
                                  (1e6, 0, 0.0), (1e6, -2, 0.0),
                                  (1e6, 4, 1.2), (1e6, 4, -0.1)]:
            with self.subTest(energy=energy, n=n, credit=credit):
                with self.assertRaises(ValueError):
                    per_brake_energy_J(energy, n, credit)

    def test_valueerror_required_mass_non_physical(self):
        for energy, cp, delta_t in [(1e6, 0.0, 300.0), (1e6, CP_CARBON, 0.0),
                                    (1e6, -1200.0, 300.0), (0.0, CP_CARBON, 300.0)]:
            with self.subTest(energy=energy, cp=cp, delta_t=delta_t):
                with self.assertRaises(ValueError):
                    required_heat_sink_mass_kg(energy, cp, delta_t)

    def test_valueerror_temperature_rise_non_physical(self):
        for energy, mass, cp in [(1e6, 0.0, CP_CARBON), (1e6, 130.0, 0.0),
                                 (1e6, -130.0, CP_CARBON), (-1e6, 130.0, CP_CARBON)]:
            with self.subTest(energy=energy, mass=mass, cp=cp):
                with self.assertRaises(ValueError):
                    temperature_rise_K(energy, mass, cp)

    def test_valueerror_braking_distance_non_physical(self):
        for v, decel in [(0.0, 0.35), (70.0, 0.0), (70.0, -0.35)]:
            with self.subTest(v=v, decel=decel):
                with self.assertRaises(ValueError):
                    braking_distance_m(v, decel)

    def test_valueerror_analyze_zero_wheels(self):
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, n_braked_wheels=0))

    def test_valueerror_analyze_non_integer_wheels(self):
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, n_braked_wheels=4.0))

    def test_valueerror_analyze_zero_available_mass(self):
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, heat_sink_mass_available_kg=0.0))

    def test_valueerror_analyze_non_physical_energy_inputs(self):
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, mtow_kg=0.0))
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, v1_m_s=-5.0))
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, mlw_kg=0.0))
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, touchdown_speed_m_s=-1.0))

    def test_valueerror_analyze_zero_deceleration(self):
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, decel_g=0.0))

    def test_valueerror_analyze_out_of_range_reverse_credit(self):
        with self.assertRaises(ValueError):
            analyze(dict(EXAMPLE, reverse_credit=1.5))

    def test_valueerror_analyze_missing_input(self):
        incomplete = dict(EXAMPLE)
        del incomplete["mlw_kg"]
        with self.assertRaises(ValueError):
            analyze(incomplete)


if __name__ == "__main__":
    unittest.main()
