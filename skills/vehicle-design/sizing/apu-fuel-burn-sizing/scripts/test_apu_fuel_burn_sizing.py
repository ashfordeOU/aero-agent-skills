"""Contract tests for the APU fuel burn sizing module (offline, deterministic).

Run with: python3 scripts/test_apu_fuel_burn_sizing.py
Covers the reference load point (30 kW electrical, 0.40 kg/s bleed at
pressure ratio 3.5), the spec worked-example magnitude bounds, the
load and fuel identities (p_elec/eta_gen, kg/h = 3600 * kg/s, doubling
the load doubles the fuel flow), the zero-work continuous limit of the
pressure ratio term, dict key contracts, determinism, and ValueError
rejection of every non-physical input in the spec validation list.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import apu_fuel_burn_sizing_logic as afb

P_ELEC = 30000.0        # W, reference electrical load
M_BLEED = 0.40          # kg/s, reference bleed flow
PR = 3.5                # absolute total-pressure ratio across the load compressor


class TestGeneratorShaftPower(unittest.TestCase):
    def test_reference_generator_shaft_power_35294(self):
        self.assertAlmostEqual(afb.generator_shaft_power(P_ELEC), 35294.1, delta=0.1)

    def test_generator_shaft_is_electrical_over_eta_identity(self):
        self.assertAlmostEqual(afb.generator_shaft_power(P_ELEC),
                               P_ELEC / afb.ETA_GEN_DEFAULT, delta=1e-9)

    def test_custom_efficiency_applied(self):
        self.assertAlmostEqual(afb.generator_shaft_power(85000.0, eta_gen=0.5),
                               170000.0, delta=1e-9)

    def test_efficiency_of_one_is_lossless(self):
        self.assertAlmostEqual(afb.generator_shaft_power(P_ELEC, eta_gen=1.0),
                               P_ELEC, delta=1e-9)

    def test_negative_load_raises_value_error(self):
        with self.assertRaises(ValueError):
            afb.generator_shaft_power(-1.0)

    def test_eta_gen_out_of_range_raises_value_error(self):
        for eta in (0.0, -0.2, 1.1):
            with self.assertRaises(ValueError):
                afb.generator_shaft_power(P_ELEC, eta_gen=eta)


class TestBleedPumpingPower(unittest.TestCase):
    def test_reference_bleed_pumping_66435(self):
        self.assertAlmostEqual(afb.bleed_pumping_power(M_BLEED, PR), 66435.2, delta=0.1)

    def test_unit_pressure_ratio_zero_work_limit(self):
        # PR = 1 makes the adiabatic term (PR^((gamma-1)/gamma) - 1) vanish;
        # exactly 1 is rejected as non-physical, so the continuous limit
        # just above 1 must be essentially zero work.
        power = afb.bleed_pumping_power(M_BLEED, 1.0 + 1e-9)
        self.assertLess(power, 1e-3)
        self.assertGreater(power, 0.0)

    def test_pressure_ratio_of_one_raises_value_error(self):
        with self.assertRaises(ValueError):
            afb.bleed_pumping_power(M_BLEED, 1.0)

    def test_pressure_ratio_below_one_raises_value_error(self):
        with self.assertRaises(ValueError):
            afb.bleed_pumping_power(M_BLEED, 0.9)

    def test_nonpositive_bleed_flow_raises_value_error(self):
        for flow in (0.0, -0.1):
            with self.assertRaises(ValueError):
                afb.bleed_pumping_power(flow, PR)

    def test_nonpositive_inlet_temperature_raises_value_error(self):
        for t_inlet in (0.0, -288.0):
            with self.assertRaises(ValueError):
                afb.bleed_pumping_power(M_BLEED, PR, t_inlet_k=t_inlet)

    def test_eta_comp_out_of_range_raises_value_error(self):
        for eta in (0.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                afb.bleed_pumping_power(M_BLEED, PR, eta_comp=eta)

    def test_pumping_scales_linearly_with_mass_flow(self):
        base = afb.bleed_pumping_power(M_BLEED, PR)
        doubled = afb.bleed_pumping_power(2.0 * M_BLEED, PR)
        self.assertAlmostEqual(doubled, 2.0 * base, delta=1e-9)

    def test_default_inlet_temperature_matches_explicit_288(self):
        self.assertAlmostEqual(afb.bleed_pumping_power(M_BLEED, PR),
                               afb.bleed_pumping_power(M_BLEED, PR, t_inlet_k=288.0),
                               delta=1e-9)

    def test_higher_pressure_ratio_increases_power(self):
        self.assertGreater(afb.bleed_pumping_power(M_BLEED, 4.0),
                           afb.bleed_pumping_power(M_BLEED, PR))


class TestTotalShaftLoad(unittest.TestCase):
    def test_reference_total_is_sum_of_parts(self):
        loads = afb.total_shaft_load(P_ELEC, M_BLEED, PR)
        self.assertAlmostEqual(loads["total_shaft_w"],
                               loads["generator_shaft_w"] + loads["bleed_pumping_w"],
                               delta=1e-9)

    def test_reference_total_magnitude_101729(self):
        loads = afb.total_shaft_load(P_ELEC, M_BLEED, PR)
        self.assertAlmostEqual(loads["total_shaft_w"], 101729.3, delta=0.1)

    def test_dict_keys_exactly_as_documented(self):
        keys = list(afb.total_shaft_load(P_ELEC, M_BLEED, PR).keys())
        self.assertEqual(keys, ["generator_shaft_w", "bleed_pumping_w", "total_shaft_w"])

    def test_nonpositive_bleed_propagates_value_error(self):
        with self.assertRaises(ValueError):
            afb.total_shaft_load(P_ELEC, 0.0, PR)


class TestApuFuelBurn(unittest.TestCase):
    def test_reference_fuel_kg_s_0_013082(self):
        fuel = afb.apu_fuel_burn(afb.total_shaft_load(P_ELEC, M_BLEED, PR)["total_shaft_w"])
        self.assertAlmostEqual(fuel["fuel_kg_s"], 0.013082, delta=1e-6)

    def test_reference_fuel_kg_h_47_10(self):
        fuel = afb.apu_fuel_burn(afb.total_shaft_load(P_ELEC, M_BLEED, PR)["total_shaft_w"])
        self.assertAlmostEqual(fuel["fuel_kg_h"], 47.10, delta=1e-2)

    def test_fuel_kg_h_equals_kg_s_times_3600(self):
        fuel = afb.apu_fuel_burn(101729.28052695909)
        self.assertAlmostEqual(fuel["fuel_kg_h"], fuel["fuel_kg_s"] * 3600.0, delta=1e-9)

    def test_doubling_load_doubles_fuel_flow(self):
        base = afb.apu_fuel_burn(100000.0)
        doubled = afb.apu_fuel_burn(200000.0)
        self.assertAlmostEqual(doubled["fuel_kg_s"], 2.0 * base["fuel_kg_s"], delta=1e-12)

    def test_dict_keys_exactly_as_documented(self):
        keys = list(afb.apu_fuel_burn(100000.0).keys())
        self.assertEqual(keys, ["fuel_kg_s", "fuel_kg_h"])

    def test_zero_or_negative_shaft_load_raises_value_error(self):
        for load in (0.0, -1.0):
            with self.assertRaises(ValueError):
                afb.apu_fuel_burn(load)

    def test_eta_th_out_of_range_raises_value_error(self):
        for eta in (0.0, -0.1, 1.0 + 1e-9):
            with self.assertRaises(ValueError):
                afb.apu_fuel_burn(100000.0, eta_th=eta)

    def test_nonpositive_lhv_raises_value_error(self):
        for lhv in (0.0, -43.2e6):
            with self.assertRaises(ValueError):
                afb.apu_fuel_burn(100000.0, lhv_j_kg=lhv)


class TestApuSummary(unittest.TestCase):
    def test_summary_matches_component_calls(self):
        summary = afb.apu_summary(P_ELEC, M_BLEED, PR)
        loads = afb.total_shaft_load(P_ELEC, M_BLEED, PR)
        fuel = afb.apu_fuel_burn(loads["total_shaft_w"])
        self.assertAlmostEqual(summary["generator_shaft_w"], loads["generator_shaft_w"], delta=1e-9)
        self.assertAlmostEqual(summary["bleed_pumping_w"], loads["bleed_pumping_w"], delta=1e-9)
        self.assertAlmostEqual(summary["total_shaft_w"], loads["total_shaft_w"], delta=1e-9)
        self.assertAlmostEqual(summary["fuel_kg_s"], fuel["fuel_kg_s"], delta=1e-12)
        self.assertAlmostEqual(summary["fuel_kg_h"], fuel["fuel_kg_h"], delta=1e-9)

    def test_summary_dict_keys_exactly_as_documented(self):
        keys = list(afb.apu_summary(P_ELEC, M_BLEED, PR).keys())
        self.assertEqual(keys, ["generator_shaft_w", "bleed_pumping_w",
                                "total_shaft_w", "fuel_kg_s", "fuel_kg_h"])

    def test_summary_reference_magnitude_bounds(self):
        s = afb.apu_summary(P_ELEC, M_BLEED, PR)
        self.assertAlmostEqual(s["generator_shaft_w"], 35294.1, delta=0.1)
        self.assertAlmostEqual(s["bleed_pumping_w"], 66435.2, delta=0.1)
        self.assertAlmostEqual(s["total_shaft_w"], 101729.3, delta=0.1)
        self.assertAlmostEqual(s["fuel_kg_s"], 0.013082, delta=1e-6)
        self.assertAlmostEqual(s["fuel_kg_h"], 47.10, delta=1e-2)

    def test_summary_negative_power_raises_value_error(self):
        with self.assertRaises(ValueError):
            afb.apu_summary(-1.0, M_BLEED, PR)

    def test_summary_bad_bleed_raises_value_error(self):
        with self.assertRaises(ValueError):
            afb.apu_summary(P_ELEC, 0.0, PR)

    def test_summary_thermal_efficiency_out_of_range_raises_value_error(self):
        with self.assertRaises(ValueError):
            afb.apu_summary(P_ELEC, M_BLEED, PR, eta_th=1.5)


class TestDeterminism(unittest.TestCase):
    def test_repeated_calls_are_identical(self):
        first = afb.apu_summary(P_ELEC, M_BLEED, PR)
        second = afb.apu_summary(P_ELEC, M_BLEED, PR)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
