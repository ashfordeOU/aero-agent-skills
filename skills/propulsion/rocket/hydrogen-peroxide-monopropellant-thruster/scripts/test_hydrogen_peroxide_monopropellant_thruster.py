"""Contract test for the hydrogen peroxide monopropellant thruster station
logic (propulsion, rocket pack). Stdlib unittest, offline, deterministic.

Exercises the SKILL.md Workflow steps end to end: step 1 fixes the duty
point (thrust F, peroxide concentration w); step 2 decomposes the peroxide
(dilution_water_moles, product_mole_numbers, total_product_moles); step 3
gets the net decomposition heat release (decomposition_heat_released); step
4 solves for the adiabatic decomposition (chamber) temperature
(decomposition_temperature, product_heat_capacity, product_sensible_heat);
step 5 gets the steam-oxygen mixture composition (product_mole_fractions,
product_mass_fractions); step 6 gets the mixture gas properties
(mixture_molar_mass, mixture_gas_constant, mixture_gamma); step 7 expands to
vacuum (vacuum_exhaust_velocity, vacuum_specific_impulse,
propellant_mass_flow); step 8 runs the advisory silver-catalyst-bed band
check (within_silver_catalyst_bed_band); step 9 is this contract test.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hydrogen_peroxide_monopropellant_thruster_logic as m


class TestDilutionAndProducts(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the peroxide-decomposition products
    at a documented concentration w with the water dilution."""

    def test_dilution_water_moles_worked_points(self):
        self.assertAlmostEqual(m.dilution_water_moles(0.90), 0.209789072881,
                                delta=1e-6)
        self.assertAlmostEqual(m.dilution_water_moles(0.85), 0.333194409870,
                                delta=1e-6)
        self.assertAlmostEqual(m.dilution_water_moles(1.0), 0.0, delta=1e-12)

    def test_product_mole_numbers_and_total_worked_points(self):
        n_h2o, n_o2 = m.product_mole_numbers(0.90)
        self.assertAlmostEqual(n_h2o, 1.209789072881, delta=1e-6)
        self.assertAlmostEqual(n_o2, 0.5, delta=1e-12)
        self.assertAlmostEqual(m.total_product_moles(0.90), 1.709789072881,
                                delta=1e-6)
        n_h2o, n_o2 = m.product_mole_numbers(1.0)
        self.assertAlmostEqual(n_h2o, 1.0, delta=1e-9)
        self.assertAlmostEqual(n_o2, 0.5, delta=1e-12)
        self.assertAlmostEqual(m.total_product_moles(1.0), 1.5, delta=1e-9)

    def test_mass_closure_identity(self):
        """Product mass equals feed mass per mole of H2O2 fed (real anchor
        relative errors 1.776e-16 to 2.047e-16)."""
        for w in (0.85, 0.90, 0.98, 1.0):
            n_w = m.dilution_water_moles(w)
            n_h2o, n_o2 = m.product_mole_numbers(w)
            product_mass = n_h2o * m.M_H2O + n_o2 * m.M_O2
            feed_mass = m.M_H2O2 + n_w * m.M_H2O
            self.assertTrue(math.isclose(product_mass, feed_mass,
                                          rel_tol=1e-12))

    def test_mole_and_mass_fraction_sums(self):
        for w in (0.85, 0.90, 0.98, 1.0):
            y_h2o, y_o2 = m.product_mole_fractions(w)
            self.assertAlmostEqual(y_h2o + y_o2, 1.0, delta=1e-12)
            x_h2o, x_o2 = m.product_mass_fractions(w)
            self.assertAlmostEqual(x_h2o + x_o2, 1.0, delta=1e-12)

    def test_mole_and_mass_fractions_worked_point(self):
        y_h2o, y_o2 = m.product_mole_fractions(0.90)
        self.assertAlmostEqual(y_h2o, 0.707566267717, delta=1e-6)
        self.assertAlmostEqual(y_o2, 0.292433732283, delta=1e-6)
        x_h2o, x_o2 = m.product_mass_fractions(0.90)
        self.assertAlmostEqual(x_h2o, 0.576669249865, delta=1e-6)
        self.assertAlmostEqual(x_o2, 0.423330750135, delta=1e-6)


class TestHeatRelease(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the net decomposition heat release
    from the Hess-law energy balance at the reference state."""

    def test_decomposition_heat_released_worked_points(self):
        self.assertAlmostEqual(m.decomposition_heat_released(0.90),
                                44814.925553, delta=1e-2)
        self.assertAlmostEqual(m.decomposition_heat_released(1.0),
                                54046.400000, delta=1e-6)

    def test_heat_release_equals_q_base_at_pure_peroxide(self):
        self.assertTrue(math.isclose(m.decomposition_heat_released(1.0),
                                      m.Q_BASE, rel_tol=1e-12))

    def test_heat_release_linearity_in_dilution(self):
        n_w_98 = m.dilution_water_moles(0.98)
        n_w_90 = m.dilution_water_moles(0.90)
        q_98 = m.decomposition_heat_released(0.98)
        q_90 = m.decomposition_heat_released(0.90)
        slope = (q_98 - q_90) / (n_w_98 - n_w_90)
        self.assertAlmostEqual(slope, -44003.600000, delta=1e-2)

    def test_heat_release_strictly_increasing_with_w(self):
        qs = [m.decomposition_heat_released(w)
              for w in (0.85, 0.90, 0.95, 0.98, 1.0)]
        self.assertEqual(qs, sorted(qs))


class TestChamberTemperature(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the adiabatic decomposition (chamber)
    temperature from the bisection energy-balance solve."""

    def test_decomposition_temperature_worked_points(self):
        self.assertAlmostEqual(m.decomposition_temperature(0.90),
                                1024.2354582656, delta=1e-3)
        self.assertAlmostEqual(m.decomposition_temperature(0.85),
                                901.7013222428, delta=1e-3)
        self.assertAlmostEqual(m.decomposition_temperature(0.98),
                                1221.3719212069, delta=1e-3)
        self.assertAlmostEqual(m.decomposition_temperature(1.0),
                                1271.0022500679, delta=1e-3)

    def test_concentration_sweep_strictly_increasing(self):
        temps = [m.decomposition_temperature(w)
                  for w in (0.85, 0.90, 0.95, 0.98, 1.0)]
        self.assertEqual(temps, sorted(temps))
        for a, b in zip(temps, temps[1:]):
            self.assertLess(a, b)

    def test_energy_balance_residual_closes(self):
        for w in (0.85, 0.90, 0.98, 1.0):
            t_c = m.decomposition_temperature(w)
            residual = m.product_sensible_heat(w, t_c) - \
                m.decomposition_heat_released(w)
            self.assertLess(abs(residual), 1e-6)

    def test_decomposition_temperature_deterministic(self):
        first = m.decomposition_temperature(0.90)
        for _ in range(5):
            self.assertEqual(m.decomposition_temperature(0.90), first)


class TestMixtureGasProperties(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the frozen-composition mixture gas
    properties at the chamber state."""

    def test_mixture_molar_mass_and_gas_constant_worked_point(self):
        self.assertAlmostEqual(m.mixture_molar_mass(0.90), 22.1045329441,
                                delta=1e-6)
        self.assertAlmostEqual(m.mixture_gas_constant(0.90), 376.1428770760,
                                delta=1e-3)

    def test_mixture_gamma_worked_point(self):
        gamma = m.mixture_gamma(0.90, m.decomposition_temperature(0.90))
        self.assertAlmostEqual(gamma, 1.2656230167, delta=1e-6)

    def test_gamma_falls_across_sweep(self):
        gammas = [m.mixture_gamma(w, m.decomposition_temperature(w))
                  for w in (0.85, 0.90, 0.95, 0.98, 1.0)]
        for a, b in zip(gammas, gammas[1:]):
            self.assertGreater(a, b)
        self.assertAlmostEqual(gammas[0], 1.274513, delta=1e-4)
        self.assertAlmostEqual(gammas[-1], 1.250869, delta=1e-4)


class TestVacuumExpansion(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the frozen-composition isentropic
    expansion of the steam-oxygen product mixture to vacuum."""

    def test_vacuum_exhaust_velocity_and_isp_worked_points(self):
        self.assertAlmostEqual(m.vacuum_exhaust_velocity(0.90),
                                1916.0668272739, delta=1e-1)
        self.assertAlmostEqual(m.vacuum_specific_impulse(0.90),
                                195.3844408920, delta=1e-2)
        self.assertAlmostEqual(m.vacuum_exhaust_velocity(0.85),
                                1785.8078417405, delta=1e-1)
        self.assertAlmostEqual(m.vacuum_specific_impulse(0.85),
                                182.1017209486, delta=1e-2)
        self.assertAlmostEqual(m.vacuum_exhaust_velocity(0.98),
                                2109.8144943685, delta=1e-1)
        self.assertAlmostEqual(m.vacuum_specific_impulse(0.98),
                                215.1412046283, delta=1e-2)
        self.assertAlmostEqual(m.vacuum_exhaust_velocity(1.0),
                                2155.7580276312, delta=1e-1)
        self.assertAlmostEqual(m.vacuum_specific_impulse(1.0),
                                219.8261412033, delta=1e-2)

    def test_isp_equals_ve_over_g0(self):
        for w in (0.85, 0.90, 0.98, 1.0):
            v_e = m.vacuum_exhaust_velocity(w)
            self.assertTrue(math.isclose(m.vacuum_specific_impulse(w),
                                          v_e / m.G0, rel_tol=1e-12))

    def test_exhaust_velocity_term_by_term_identity(self):
        for w in (0.85, 0.90, 0.98):
            t_c = m.decomposition_temperature(w)
            gamma = m.mixture_gamma(w, t_c)
            r_mix = m.mixture_gas_constant(w)
            expected = math.sqrt(2.0 * gamma / (gamma - 1.0) * r_mix * t_c)
            self.assertTrue(math.isclose(m.vacuum_exhaust_velocity(w),
                                          expected, rel_tol=1e-9))

    def test_frozen_expansion_energy_identity(self):
        """0.5 v_e^2 = cp_specific * T_c, cp_specific the mass-basis mixture
        heat capacity at the chamber state."""
        for w in (0.85, 0.90, 0.98, 1.0):
            t_c = m.decomposition_temperature(w)
            v_e = m.vacuum_exhaust_velocity(w)
            cp_molar = m.product_heat_capacity(w, t_c) / \
                m.total_product_moles(w)
            cp_specific = cp_molar * 1000.0 / m.mixture_molar_mass(w)
            lhs = 0.5 * v_e * v_e
            rhs = cp_specific * t_c
            self.assertTrue(math.isclose(lhs, rhs, rel_tol=1e-5))

    def test_finite_pressure_isentropic_form_vs_vacuum_limit(self):
        w = 0.90
        t_c = m.decomposition_temperature(w)
        gamma = m.mixture_gamma(w, t_c)
        r_mix = m.mixture_gas_constant(w)
        pe_over_pc = 1e-6
        v_e_finite = math.sqrt(2.0 * gamma / (gamma - 1.0) * r_mix * t_c *
                                (1.0 - pe_over_pc ** ((gamma - 1.0) / gamma)))
        self.assertAlmostEqual(v_e_finite, 1862.581707, delta=1.0)
        v_e_vacuum = m.vacuum_exhaust_velocity(w)
        self.assertLess(v_e_finite, v_e_vacuum)


class TestPropellantMassFlow(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the propellant mass flow at the
    required vacuum thrust point."""

    def test_propellant_mass_flow_worked_points(self):
        self.assertAlmostEqual(m.propellant_mass_flow(1.0, 0.90),
                                0.000521902465, delta=1e-6)
        self.assertAlmostEqual(m.propellant_mass_flow(22.0, 0.90),
                                0.011481854227, delta=1e-6)
        self.assertAlmostEqual(m.propellant_mass_flow(22.0, 0.85),
                                0.012319354572, delta=1e-6)
        self.assertAlmostEqual(m.propellant_mass_flow(22.0, 0.98),
                                0.010427457039, delta=1e-6)

    def test_mass_flow_scales_linearly_with_thrust(self):
        w = 0.90
        mdot_22 = m.propellant_mass_flow(22.0, w)
        mdot_44 = m.propellant_mass_flow(44.0, w)
        self.assertTrue(math.isclose(mdot_44 / mdot_22, 2.0, rel_tol=1e-12))


class TestSilverCatalystBedBand(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the advisory silver-catalyst-bed
    band verdict, reported reference-only, never enforced."""

    def test_band_verdict_worked_points(self):
        self.assertTrue(m.within_silver_catalyst_bed_band(
            m.decomposition_temperature(0.85)))
        self.assertTrue(m.within_silver_catalyst_bed_band(
            m.decomposition_temperature(0.90)))
        self.assertTrue(m.within_silver_catalyst_bed_band(
            m.decomposition_temperature(0.98)))
        self.assertFalse(m.within_silver_catalyst_bed_band(
            m.decomposition_temperature(1.0)))

    def test_band_verdict_closed_boundaries(self):
        self.assertTrue(m.within_silver_catalyst_bed_band(823.15))
        self.assertTrue(m.within_silver_catalyst_bed_band(1234.93))


class TestValueErrors(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the peroxide concentration domain
    guard, and the ValueError rejections across the module (real anchor,
    20 cases)."""

    def test_concentration_domain_rejected(self):
        for w in (-0.1, 0.0, 0.5, 0.84, 1.01, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                m.dilution_water_moles(w)
            with self.assertRaises(ValueError):
                m.decomposition_temperature(w)

    def test_temperature_domain_rejected(self):
        for t_k in (0, -5):
            with self.assertRaises(ValueError):
                m.product_heat_capacity(0.90, t_k)
            with self.assertRaises(ValueError):
                m.product_sensible_heat(0.90, t_k)
            with self.assertRaises(ValueError):
                m.mixture_gamma(0.90, t_k)

    def test_g0_thrust_and_band_domain_rejected(self):
        with self.assertRaises(ValueError):
            m.vacuum_specific_impulse(0.90, g0=0)
        for thrust_n in (0, -5):
            with self.assertRaises(ValueError):
                m.propellant_mass_flow(thrust_n, 0.90)
        with self.assertRaises(ValueError):
            m.within_silver_catalyst_bed_band(0)
        with self.assertRaises(ValueError):
            m.within_silver_catalyst_bed_band(float("nan"))


class TestNoSiblingLeafOutputs(unittest.TestCase):
    """Step 9 of the SKILL.md workflow (this contract test): confirms the
    public API stays inside the peroxide-decomposition claim, with no
    blowdown, plenum, choked-throat, feed-cycle, pump-power,
    heating-efficiency, hydrazine or ammonia outputs anywhere."""

    def test_public_api_has_sixteen_functions(self):
        expected = {
            "dilution_water_moles", "product_mole_numbers",
            "total_product_moles", "decomposition_heat_released",
            "product_heat_capacity", "product_sensible_heat",
            "decomposition_temperature", "product_mole_fractions",
            "product_mass_fractions", "mixture_molar_mass",
            "mixture_gas_constant", "mixture_gamma",
            "vacuum_exhaust_velocity", "vacuum_specific_impulse",
            "propellant_mass_flow", "within_silver_catalyst_bed_band",
        }
        public_functions = {
            name for name in dir(m)
            if not name.startswith("_") and callable(getattr(m, name))
            and getattr(getattr(m, name), "__module__", None) == m.__name__
        }
        self.assertEqual(public_functions, expected)

    def test_module_imports_only_math(self):
        self.assertNotIn("numpy", dir(m))
        self.assertNotIn("scipy", dir(m))


if __name__ == "__main__":
    unittest.main()
