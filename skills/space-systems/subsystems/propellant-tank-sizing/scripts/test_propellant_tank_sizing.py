"""Contract tests for propellant-tank-sizing (space-systems/subsystems).

Offline, deterministic, stdlib only. Run from the repo root:

    python3 skills/space-systems/subsystems/propellant-tank-sizing/scripts/test_propellant_tank_sizing.py

Asserts the wave-28 spec worked example (100 kg hydrazine at 1008
kg/m3, ullage 0.06, MEOP 2.0 MPa, burst factor 2.0, Ti ultimate 900
MPa, rho 4430 kg/m3, helium at 293 K) within the stated tolerances,
the blowdown pressure range, the fail-verdict construction, and
ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from propellant_tank_sizing_logic import (  # noqa: E402
    DEFAULT_BOSS_FACTOR,
    DEFAULT_ULLAGE_FRACTION,
    GAS_CONSTANT_HE,
    analyze,
    blowdown_pressure_range,
    burst_pressure_pa,
    pressurant_mass_kg,
    propellant_volume_m3,
    shell_mass_kg,
    sphere_radius_m,
    tank_volume_m3,
    ullage_volume_m3,
    wall_thickness_m,
)

# Worked-example inputs (wave-28 spec).
MASS = 100.0
DENSITY = 1008.0
ULLAGE = 0.06
MEOP = 2.0e6
BURST_FACTOR = 2.0
ULTIMATE = 900.0e6
MAT_DENSITY = 4430.0
TEMP = 293.0


def example_inputs(**overrides):
    """Return a regulated-scheme analyze() inputs dict for the example."""
    base = {
        "propellant_mass_kg": MASS,
        "propellant_density_kg_m3": DENSITY,
        "ullage_fraction": ULLAGE,
        "pressurization": "regulated",
        "meop_pa": MEOP,
        "burst_factor": BURST_FACTOR,
        "material_ultimate_pa": ULTIMATE,
        "material_density_kg_m3": MAT_DENSITY,
        "boss_factor": DEFAULT_BOSS_FACTOR,
        "pressurant_temperature_K": TEMP,
        "gas_constant": GAS_CONSTANT_HE,
    }
    base.update(overrides)
    return base


class PropellantVolumeTests(unittest.TestCase):
    """Propellant volume from mass and density."""

    def test_propellant_volume_worked_example(self):
        vol = propellant_volume_m3(MASS, DENSITY)
        self.assertAlmostEqual(vol, 0.099206, delta=1e-5)

    def test_propellant_volume_scales_with_mass(self):
        vol = propellant_volume_m3(200.0, DENSITY)
        self.assertAlmostEqual(vol, 2.0 * propellant_volume_m3(MASS, DENSITY))

    def test_propellant_volume_density_inverse(self):
        vol = propellant_volume_m3(MASS, 2016.0)
        self.assertAlmostEqual(vol, 0.5 * propellant_volume_m3(MASS, DENSITY))

    def test_propellant_volume_valueerror_mass_zero(self):
        with self.assertRaises(ValueError):
            propellant_volume_m3(0.0, DENSITY)

    def test_propellant_volume_valueerror_density_zero(self):
        with self.assertRaises(ValueError):
            propellant_volume_m3(MASS, 0.0)


class UllageVolumeTests(unittest.TestCase):
    """Ullage volume as a fraction of the TOTAL tank volume."""

    def test_ullage_volume_worked_example(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        ullage = ullage_volume_m3(prop_vol, ULLAGE)
        self.assertAlmostEqual(ullage, 0.0063323, delta=1e-5)
        self.assertAlmostEqual(
            ullage, prop_vol * ULLAGE / (1.0 - ULLAGE), delta=1e-12
        )

    def test_ullage_volume_zero_approaching_fraction(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        tiny = ullage_volume_m3(prop_vol, 1e-6)
        self.assertLess(tiny, 1e-4 * prop_vol)

    def test_ullage_volume_grows_with_fraction(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        self.assertLess(
            ullage_volume_m3(prop_vol, 0.1),
            ullage_volume_m3(prop_vol, 0.2),
        )

    def test_ullage_volume_valueerror_out_of_range(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        for bad in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                ullage_volume_m3(prop_vol, bad)


class TankVolumeTests(unittest.TestCase):
    """Total tank volume from propellant volume and ullage fraction."""

    def test_tank_volume_worked_example(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        tank = tank_volume_m3(prop_vol, ULLAGE)
        self.assertAlmostEqual(tank, 0.105539, delta=1e-4)
        self.assertAlmostEqual(tank, prop_vol / (1.0 - ULLAGE), delta=1e-12)

    def test_tank_volume_is_prop_plus_ullage(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        tank = tank_volume_m3(prop_vol, ULLAGE)
        ullage = ullage_volume_m3(prop_vol, ULLAGE)
        self.assertAlmostEqual(tank, prop_vol + ullage, delta=1e-12)

    def test_tank_volume_valueerror_fraction_one(self):
        with self.assertRaises(ValueError):
            tank_volume_m3(0.1, 1.0)


class SphereRadiusTests(unittest.TestCase):
    """Sphere radius from tank volume."""

    def test_sphere_radius_worked_example(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        radius = sphere_radius_m(tank_volume_m3(prop_vol, ULLAGE))
        self.assertAlmostEqual(radius, 0.29319, delta=1e-4)

    def test_sphere_radius_volume_roundtrip(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        volume = tank_volume_m3(prop_vol, ULLAGE)
        radius = sphere_radius_m(volume)
        self.assertAlmostEqual(4.0 / 3.0 * math.pi * radius**3, volume)

    def test_sphere_radius_valueerror_nonpositive(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                sphere_radius_m(bad)


class BurstPressureTests(unittest.TestCase):
    """Burst pressure from MEOP and burst factor."""

    def test_burst_pressure_worked_example(self):
        self.assertAlmostEqual(burst_pressure_pa(MEOP, BURST_FACTOR), 4.0e6)

    def test_burst_pressure_scaling(self):
        self.assertAlmostEqual(burst_pressure_pa(MEOP, 2.5), 5.0e6)

    def test_burst_pressure_valueerror_meop_zero(self):
        with self.assertRaises(ValueError):
            burst_pressure_pa(0.0, BURST_FACTOR)

    def test_burst_pressure_valueerror_factor_le_one(self):
        with self.assertRaises(ValueError):
            burst_pressure_pa(MEOP, 1.0)


class WallThicknessTests(unittest.TestCase):
    """Thin-walled sphere membrane thickness."""

    def test_wall_thickness_worked_example(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        radius = sphere_radius_m(tank_volume_m3(prop_vol, ULLAGE))
        burst = burst_pressure_pa(MEOP, BURST_FACTOR)
        thickness = wall_thickness_m(burst, radius, ULTIMATE)
        self.assertAlmostEqual(thickness, 6.5153e-4, delta=1e-6)
        self.assertAlmostEqual(
            thickness, burst * radius / (2.0 * ULTIMATE), delta=1e-12
        )

    def test_wall_thickness_half_for_double_strength(self):
        radius = 0.3
        burst = 4.0e6
        t_900 = wall_thickness_m(burst, radius, 900.0e6)
        t_1800 = wall_thickness_m(burst, radius, 1800.0e6)
        self.assertAlmostEqual(t_1800, 0.5 * t_900)

    def test_wall_thickness_valueerror_nonpositive(self):
        with self.assertRaises(ValueError):
            wall_thickness_m(0.0, 0.3, ULTIMATE)
        with self.assertRaises(ValueError):
            wall_thickness_m(4.0e6, 0.0, ULTIMATE)
        with self.assertRaises(ValueError):
            wall_thickness_m(4.0e6, 0.3, 0.0)


class ShellMassTests(unittest.TestCase):
    """Tank shell mass with boss factor."""

    def test_shell_mass_worked_example(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        radius = sphere_radius_m(tank_volume_m3(prop_vol, ULLAGE))
        burst = burst_pressure_pa(MEOP, BURST_FACTOR)
        thickness = wall_thickness_m(burst, radius, ULTIMATE)
        shell = shell_mass_kg(radius, thickness, MAT_DENSITY, DEFAULT_BOSS_FACTOR)
        self.assertAlmostEqual(shell, 3.4296, delta=0.01)

    def test_shell_mass_boss_factor_effect(self):
        radius, thickness = 0.3, 1.0e-3
        plain = shell_mass_kg(radius, thickness, MAT_DENSITY, 1.0)
        bossed = shell_mass_kg(radius, thickness, MAT_DENSITY, 1.10)
        self.assertAlmostEqual(bossed, 1.10 * plain)

    def test_shell_mass_scales_with_density(self):
        radius, thickness = 0.3, 1.0e-3
        light = shell_mass_kg(radius, thickness, 1000.0, 1.0)
        heavy = shell_mass_kg(radius, thickness, 2000.0, 1.0)
        self.assertAlmostEqual(heavy, 2.0 * light)

    def test_shell_mass_valueerror_nonpositive(self):
        with self.assertRaises(ValueError):
            shell_mass_kg(0.0, 1.0e-3, MAT_DENSITY, 1.0)
        with self.assertRaises(ValueError):
            shell_mass_kg(0.3, -1.0e-3, MAT_DENSITY, 1.0)


class PressurantMassTests(unittest.TestCase):
    """Pressurant gas mass from the ideal gas law."""

    def test_pressurant_mass_regulated_worked_example(self):
        prop_vol = propellant_volume_m3(MASS, DENSITY)
        ullage = ullage_volume_m3(prop_vol, ULLAGE)
        mass = pressurant_mass_kg(MEOP, ullage, TEMP, GAS_CONSTANT_HE)
        self.assertAlmostEqual(mass, 0.020811, delta=1e-4)
        self.assertAlmostEqual(
            mass, MEOP * ullage / (GAS_CONSTANT_HE * TEMP), delta=1e-12
        )

    def test_pressurant_mass_inverse_temperature(self):
        ullage = 0.01
        cold = pressurant_mass_kg(MEOP, ullage, 293.0, GAS_CONSTANT_HE)
        hot = pressurant_mass_kg(MEOP, ullage, 586.0, GAS_CONSTANT_HE)
        self.assertAlmostEqual(hot, 0.5 * cold)

    def test_pressurant_mass_valueerror_nonpositive(self):
        with self.assertRaises(ValueError):
            pressurant_mass_kg(0.0, 0.01, TEMP, GAS_CONSTANT_HE)
        with self.assertRaises(ValueError):
            pressurant_mass_kg(MEOP, 0.01, 0.0, GAS_CONSTANT_HE)
        with self.assertRaises(ValueError):
            pressurant_mass_kg(MEOP, 0.01, TEMP, 0.0)


class BlowdownRangeTests(unittest.TestCase):
    """Blowdown pressure range."""

    def test_blowdown_pressure_range_worked_example(self):
        rng = blowdown_pressure_range(MEOP, 2.5)
        self.assertEqual(rng["p_initial_pa"], 2.0e6)
        self.assertAlmostEqual(rng["p_final_pa"], 0.8e6)

    def test_blowdown_pressure_range_ratio_four(self):
        rng = blowdown_pressure_range(4.0e6, 4.0)
        self.assertEqual(rng["p_initial_pa"], 4.0e6)
        self.assertAlmostEqual(rng["p_final_pa"], 1.0e6)

    def test_blowdown_pressure_range_valueerror_ratio_le_one(self):
        for bad in (1.0, 0.5):
            with self.assertRaises(ValueError):
                blowdown_pressure_range(MEOP, bad)


class AnalyzeTests(unittest.TestCase):
    """Full analyze() sizing pipeline."""

    def test_analyze_regulated_worked_example(self):
        result = analyze(example_inputs())
        self.assertAlmostEqual(result["propellant_volume_m3"], 0.099206, delta=1e-5)
        self.assertAlmostEqual(result["ullage_volume_m3"], 0.0063323, delta=1e-5)
        self.assertAlmostEqual(result["tank_volume_m3"], 0.105539, delta=1e-4)
        self.assertAlmostEqual(result["radius_m"], 0.29319, delta=1e-4)
        self.assertEqual(result["burst_pressure_pa"], 4.0e6)
        self.assertAlmostEqual(result["wall_thickness_m"], 6.5153e-4, delta=1e-6)
        self.assertAlmostEqual(result["shell_mass_kg"], 3.4296, delta=0.01)
        self.assertAlmostEqual(result["pressurant_mass_kg"], 0.020811, delta=1e-4)
        self.assertAlmostEqual(
            result["tank_mass_fraction"], result["shell_mass_kg"] / MASS
        )

    def test_analyze_regulated_verdict_pass(self):
        result = analyze(example_inputs())
        self.assertLess(result["tank_mass_fraction"], 0.05)
        self.assertEqual(result["verdict"], "tank-sizing-pass")

    def test_analyze_regulated_no_blowdown_range_key(self):
        result = analyze(example_inputs())
        self.assertNotIn("blowdown_pressure_range", result)

    def test_analyze_blowdown_worked_example(self):
        result = analyze(example_inputs(pressurization="blowdown", blowdown_ratio=2.5))
        self.assertAlmostEqual(result["pressurant_mass_kg"], 0.020811, delta=1e-4)
        rng = result["blowdown_pressure_range"]
        self.assertEqual(rng["p_initial_pa"], 2.0e6)
        self.assertAlmostEqual(rng["p_final_pa"], 0.8e6)
        self.assertEqual(result["verdict"], "tank-sizing-pass")

    def test_analyze_defaults_are_documented_typical(self):
        inputs = example_inputs()
        inputs.pop("ullage_fraction")
        inputs.pop("burst_factor")
        inputs.pop("material_density_kg_m3")
        inputs.pop("boss_factor")
        inputs.pop("pressurant_temperature_K")
        inputs.pop("gas_constant")
        result = analyze(inputs)
        self.assertAlmostEqual(result["tank_volume_m3"], 0.105539, delta=1e-4)
        self.assertAlmostEqual(result["shell_mass_kg"], 3.4296, delta=0.01)

    def test_analyze_fail_verdict_construction(self):
        result = analyze(example_inputs(material_density_kg_m3=30000.0))
        self.assertAlmostEqual(result["shell_mass_kg"], 23.2, delta=0.5)
        self.assertGreater(result["tank_mass_fraction"], 0.20)
        self.assertEqual(result["verdict"], "tank-sizing-fail")

    def test_analyze_verdict_boundary_at_020(self):
        pass_inputs = example_inputs(material_density_kg_m3=25000.0)
        fail_inputs = example_inputs(material_density_kg_m3=27000.0)
        self.assertEqual(analyze(pass_inputs)["verdict"], "tank-sizing-pass")
        self.assertEqual(analyze(fail_inputs)["verdict"], "tank-sizing-fail")
        self.assertLessEqual(
            analyze(pass_inputs)["tank_mass_fraction"], 0.20
        )
        self.assertGreater(
            analyze(fail_inputs)["tank_mass_fraction"], 0.20
        )

    def test_analyze_valueerror_zero_mass(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(propellant_mass_kg=0.0))

    def test_analyze_valueerror_zero_density(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(propellant_density_kg_m3=0.0))

    def test_analyze_valueerror_zero_meop(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(meop_pa=0.0))

    def test_analyze_valueerror_zero_material_ultimate(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(material_ultimate_pa=0.0))

    def test_analyze_valueerror_burst_factor_one(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(burst_factor=1.0))

    def test_analyze_valueerror_zero_temperature(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(pressurant_temperature_K=0.0))

    def test_analyze_valueerror_unknown_pressurization(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(pressurization="self-pressurized"))

    def test_analyze_valueerror_blowdown_without_ratio(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(pressurization="blowdown"))

    def test_analyze_valueerror_blowdown_ratio_one(self):
        with self.assertRaises(ValueError):
            analyze(
                example_inputs(
                    pressurization="blowdown", blowdown_ratio=1.0
                )
            )

    def test_analyze_valueerror_ullage_out_of_range(self):
        with self.assertRaises(ValueError):
            analyze(example_inputs(ullage_fraction=0.0))
        with self.assertRaises(ValueError):
            analyze(example_inputs(ullage_fraction=1.0))


if __name__ == "__main__":
    unittest.main()
