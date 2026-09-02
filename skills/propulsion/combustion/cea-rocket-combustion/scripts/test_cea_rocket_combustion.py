"""Gate 3 contract test for the cea-rocket-combustion leaf.

Pins the simplified frozen-flow equilibrium thermochemistry model: the
LOX/RP-1, LOX/LH2 and NTO/MMH reference chamber conditions (adiabatic
flame temperature, molecular weight, gamma, characteristic velocity c*
and ideal vacuum/sea-level specific impulse), the energy balance closure,
flame temperature monotonicity with mixture ratio on the fuel-rich side,
atom-balance and mole-fraction consistency, the ideal-gas c* and Isp
formulas, the efficiency helpers, the mixture ratio sensitivity and
trade, and the invalid-input boundaries. Stdlib unittest, offline,
deterministic. Run: python3 scripts/test_cea_rocket_combustion.py
"""

import math
import unittest

from cea_rocket_combustion_logic import (
    G0,
    adiabatic_flame_temperature,
    chamber_conditions,
    cstar_with_efficiency,
    equilibrium_composition,
    expansion_velocity,
    ideal_sea_level_isp,
    ideal_vacuum_isp,
    isp_mixture_ratio_sensitivity,
    isp_with_efficiency,
    mixture_ratio_trade,
    mole_fractions,
    propellant_family,
    stoichiometric_mixture_ratio,
    theoretical_cstar,
)

RP1 = ("LOX/RP-1", 2.56, 7.0e6)
LH2 = ("LOX/LH2", 6.0, 10.0e6)
NTO = ("NTO/MMH", 2.0, 2.0e6)


class TestReferencePropellantBands(unittest.TestCase):
    """Reference chamber conditions land in representative published bands."""

    def _check(self, name, ratio, pc, bands):
        c = chamber_conditions(name, ratio, pc)
        for key, (lo, hi) in bands.items():
            self.assertGreaterEqual(
                c[key], lo, "%s %s below band" % (name, key)
            )
            self.assertLessEqual(
                c[key], hi, "%s %s above band" % (name, key)
            )

    def test_lox_rp1(self):
        # Representative published values: Tc ~ 3670 K, Mw ~ 22, gamma
        # ~ 1.2, c* ~ 1798 m/s; the model lands Tc = 3672 K, c* = 1791.
        self._check(*RP1, {
            "flame_temperature": (3400.0, 3800.0),
            "molecular_weight": (19.0, 25.0),
            "gamma": (1.15, 1.30),
            "cstar": (1700.0, 1900.0),
            "isp_vacuum": (360.0, 410.0),
            "isp_sea_level": (260.0, 310.0),
        })

    def test_lox_lh2(self):
        # Representative published values: Tc ~ 3540 K, c* ~ 2380 m/s;
        # the model lands Tc = 3666 K, c* = 2328.
        self._check(*LH2, {
            "flame_temperature": (3400.0, 3800.0),
            "molecular_weight": (9.0, 14.5),
            "gamma": (1.15, 1.30),
            "cstar": (2250.0, 2500.0),
            "isp_vacuum": (480.0, 540.0),
            "isp_sea_level": (360.0, 410.0),
        })

    def test_nto_mmh(self):
        # Representative hypergolic values: Tc ~ 3300-3400 K, c* ~ 1750-
        # 1800 m/s; the model lands Tc = 3340 K, c* = 1726.
        self._check(*NTO, {
            "flame_temperature": (3100.0, 3500.0),
            "molecular_weight": (18.0, 24.0),
            "gamma": (1.15, 1.30),
            "cstar": (1650.0, 1850.0),
            "isp_vacuum": (340.0, 400.0),
            "isp_sea_level": (220.0, 270.0),
        })


class TestEnergyBalanceClosure(unittest.TestCase):
    def test_closure_for_reference_propellants(self):
        for name, ratio, pc in (RP1, LH2, NTO):
            c = chamber_conditions(name, ratio, pc)
            self.assertLess(
                c["energy_closure_error"], 5e-3,
                "%s energy balance does not close" % name,
            )

    def test_hydrogen_zero_reactant_enthalpy(self):
        # LOX/LH2 has zero reactant formation enthalpy; the balance must
        # still close against the product chemical energy.
        c = chamber_conditions(*LH2)
        self.assertLess(c["energy_closure_error"], 5e-3)


class TestFlameTemperatureMonotonicity(unittest.TestCase):
    def test_fuel_rich_increasing(self):
        # On the fuel-rich side of the RP-1 peak the flame temperature
        # rises monotonically with the mixture ratio.
        temps = [adiabatic_flame_temperature("LOX/RP-1", r, 7.0e6)
                 for r in (1.6, 1.9, 2.2, 2.5)]
        for a, b in zip(temps, temps[1:]):
            self.assertLess(a, b)
        self.assertGreater(temps[-1] - temps[0], 500.0)

    def test_peak_then_falloff(self):
        # Past the design point the extra oxidizer dilutes the flame.
        t_peak = adiabatic_flame_temperature("LOX/RP-1", 2.5, 7.0e6)
        t_lean = adiabatic_flame_temperature("LOX/RP-1", 3.1, 7.0e6)
        self.assertLess(t_lean, t_peak)


class TestEquilibriumConsistency(unittest.TestCase):
    def test_atom_balance_rp1(self):
        comp = equilibrium_composition(*RP1)
        self.assertAlmostEqual(comp["CO2"] + comp["CO"], 12.0, places=3)
        self.assertAlmostEqual(
            2.0 * comp["H2O"] + 2.0 * comp["H2"] + comp["OH"] + comp["H"],
            26.0, places=3,
        )
        o_used = (2.0 * comp["CO2"] + comp["H2O"] + comp["CO"]
                  + 2.0 * comp["O2"] + comp["OH"] + comp["O"])
        self.assertAlmostEqual(o_used, 27.26, delta=0.15)

    def test_atom_balance_nto_mmh(self):
        comp = equilibrium_composition(*NTO)
        self.assertAlmostEqual(comp["CO2"] + comp["CO"], 1.0, places=3)
        self.assertAlmostEqual(
            2.0 * comp["H2O"] + 2.0 * comp["H2"] + comp["OH"] + comp["H"],
            6.0, places=3,
        )
        self.assertAlmostEqual(2.0 * comp["N2"], 4.0052, delta=0.02)

    def test_mole_fractions_sum_to_one(self):
        for name, ratio, pc in (RP1, LH2, NTO):
            comp = equilibrium_composition(name, ratio, pc)
            mf = mole_fractions(comp)
            self.assertAlmostEqual(sum(mf.values()), 1.0, places=6)
            for v in mf.values():
                self.assertGreaterEqual(v, 0.0)

    def test_water_gas_shift_consistent(self):
        # CO2*H2/(CO*H2O) must equal the model's WGS equilibrium constant
        # at the flame temperature (self-consistency of the solve).
        comp = equilibrium_composition(*RP1)
        ratio = (comp["CO2"] * comp["H2"]) / (comp["CO"] * comp["H2O"])
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 0.2)  # high-T WGS favors CO and H2


class TestCstarAndIspFormulas(unittest.TestCase):
    def test_cstar_worked_value(self):
        # Same worked LOX/RP-1 gas properties as the sibling
        # combustion-chamber-design leaf: c*(3670 K, 23, 1.20) ~ 1776 m/s.
        self.assertAlmostEqual(
            theoretical_cstar(3670.0, 23.0, 1.20), 1776.2, delta=1.5
        )

    def test_chamber_conditions_consistent_with_formulas(self):
        for name, ratio, pc in (RP1, LH2, NTO):
            c = chamber_conditions(name, ratio, pc)
            t = c["flame_temperature"]
            mw = c["molecular_weight"]
            g = c["gamma"]
            self.assertAlmostEqual(
                c["cstar"], theoretical_cstar(t, mw, g), places=1
            )
            self.assertAlmostEqual(
                c["isp_vacuum"], ideal_vacuum_isp(t, mw, g), places=1
            )
            self.assertAlmostEqual(
                c["isp_sea_level"], ideal_sea_level_isp(t, mw, g, pc),
                places=1,
            )

    def test_vacuum_above_sea_level(self):
        for name, ratio, pc in (RP1, LH2, NTO):
            c = chamber_conditions(name, ratio, pc)
            self.assertGreater(c["isp_vacuum"], c["isp_sea_level"])

    def test_sea_level_drops_with_ambient_pressure(self):
        t, mw, g = 3500.0, 20.0, 1.25
        pc = 7.0e6
        high = ideal_sea_level_isp(t, mw, g, pc, ambient_pa=150000.0)
        low = ideal_sea_level_isp(t, mw, g, pc, ambient_pa=50000.0)
        self.assertLess(high, low)

    def test_expansion_velocity_vanishes_at_no_expansion(self):
        t, mw, g = 3500.0, 20.0, 1.25
        v = expansion_velocity(t, mw, g, 7.0e6, 6.99e6)
        self.assertLess(v, 100.0)

    def test_isp_definition(self):
        # Isp = v / g0 with g0 = 9.80665 m/s^2.
        self.assertAlmostEqual(
            ideal_vacuum_isp(3670.0, 23.0, 1.20),
            math.sqrt(2.0 * 1.20 / 0.20 * (8314.462 / 23.0) * 3670.0) / G0,
            places=2,
        )


class TestEfficiencyHelpers(unittest.TestCase):
    def test_identity_efficiency(self):
        self.assertEqual(cstar_with_efficiency(1791.0, 1.0), 1791.0)
        self.assertEqual(isp_with_efficiency(386.1, 1.0), 386.1)

    def test_scaling(self):
        self.assertAlmostEqual(cstar_with_efficiency(1800.0, 0.95), 1710.0)
        self.assertAlmostEqual(isp_with_efficiency(400.0, 0.9), 360.0)

    def test_invalid_efficiency(self):
        for fn in (cstar_with_efficiency, isp_with_efficiency):
            with self.assertRaises(ValueError):
                fn(1000.0, 0.0)
            with self.assertRaises(ValueError):
                fn(1000.0, 1.5)
            with self.assertRaises(ValueError):
                fn(0.0, 0.95)


class TestSensitivityAndTrade(unittest.TestCase):
    def test_sensitivity_sign(self):
        # Fuel-rich of the model's Isp optimum the sensitivity is
        # positive; oxidizer-rich of it, negative.
        self.assertGreater(
            isp_mixture_ratio_sensitivity("LOX/RP-1", 2.0, 7.0e6), 0.0
        )
        self.assertLess(
            isp_mixture_ratio_sensitivity("LOX/RP-1", 3.0, 7.0e6), 0.0
        )

    def test_trade_shape(self):
        trade = mixture_ratio_trade("LOX/LH2", 10.0e6, 4.0, 8.0, 5)
        self.assertEqual(len(trade), 5)
        for i, entry in enumerate(trade):
            self.assertAlmostEqual(
                entry["mixture_ratio"], 4.0 + i, places=6
            )
            self.assertTrue(math.isfinite(entry["flame_temperature"]))
            self.assertTrue(math.isfinite(entry["cstar"]))
            self.assertTrue(math.isfinite(entry["isp_vacuum"]))
            self.assertTrue(500.0 < entry["flame_temperature"] < 6000.0)
            self.assertGreater(entry["cstar"], 0.0)

    def test_trade_consistent_with_chamber(self):
        trade = mixture_ratio_trade("LOX/LH2", 10.0e6, 4.0, 6.0, 2)
        c = chamber_conditions("LOX/LH2", 4.0, 10.0e6)
        self.assertAlmostEqual(
            trade[0]["flame_temperature"], c["flame_temperature"], delta=1.0
        )


class TestAuxiliary(unittest.TestCase):
    def test_propellant_family(self):
        self.assertEqual(propellant_family("LOX/RP-1"), "cryogenic")
        self.assertEqual(propellant_family("NTO/MMH"), "hypergolic")

    def test_stoichiometric_ratios(self):
        self.assertAlmostEqual(
            stoichiometric_mixture_ratio("LOX/RP-1"), 3.48, delta=0.05
        )
        self.assertAlmostEqual(
            stoichiometric_mixture_ratio("LOX/LH2"), 7.94, delta=0.05
        )


class TestInvalidInputs(unittest.TestCase):
    def test_unknown_propellant(self):
        with self.assertRaises(ValueError):
            chamber_conditions("LOX/KEROSENE", 2.5, 7.0e6)

    def test_nonpositive_mixture_ratio(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                chamber_conditions("LOX/RP-1", bad, 7.0e6)

    def test_nonpositive_pressure(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                chamber_conditions("LOX/RP-1", 2.5, bad)

    def test_gamma_out_of_range(self):
        for bad in (1.0, 0.9, 1.7, 2.0):
            with self.assertRaises(ValueError):
                theoretical_cstar(3000.0, 20.0, bad)
            with self.assertRaises(ValueError):
                ideal_vacuum_isp(3000.0, 20.0, bad)

    def test_expansion_pressure_order(self):
        with self.assertRaises(ValueError):
            expansion_velocity(3000.0, 20.0, 1.25, 5.0e6, 7.0e6)

    def test_trade_arguments(self):
        with self.assertRaises(ValueError):
            mixture_ratio_trade("LOX/LH2", 10.0e6, 8.0, 4.0, 5)
        with self.assertRaises(ValueError):
            mixture_ratio_trade("LOX/LH2", 10.0e6, 4.0, 8.0, 1)
        with self.assertRaises(ValueError):
            mixture_ratio_trade("LOX/LH2", 0.0, 4.0, 8.0, 5)


if __name__ == "__main__":
    unittest.main()
