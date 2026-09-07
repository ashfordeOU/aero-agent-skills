"""Contract test: hydrazine monopropellant thruster station sizing.

Exercises every numbered step of the SKILL.md workflow for the
hydrazine-monopropellant-thruster leaf: step 1 fixes the vacuum thrust duty
point and the ammonia dissociation fraction input; step 2 computes the
catalytic decomposition products and total moles per mole N2H4 fed; step 3
computes the net decomposition heat release of the Hess-law energy balance;
step 4 solves the hydrazine decomposition energy balance by bisection for the
adiabatic decomposition temperature T_c and samples the product heat
capacity; step 5 forms the mixture gas constant and the frozen-composition
isentropic exponent at the chamber state; step 6 expands the decomposed gas
to the vacuum exhaust velocity, the vacuum specific impulse and the
propellant mass flow at the thrust point; step 7 runs the advisory
catalyst-bed temperature band verdict; step 8 confirms the deterministic
checks. All numeric asserts are order-safe tolerances (isclose / abs bounds),
never exact equality on computed sums, so the file passes identically under
/usr/bin/python3 3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hydrazine_monopropellant_thruster_logic as hmt


def _sensible_heat_balance(x, t_k):
    """Independent recomputation of the product sensible heat integral used by
    the decomposition energy balance closure check (per product i, n_i times
    the integral of cp_i = a + b T + c T^2 from T_REF to t_k)."""
    n_nh3, n_n2, n_h2 = hmt.decomposition_products(x)
    total = 0.0
    for n, coeff in ((n_nh3, hmt.CP_NH3), (n_n2, hmt.CP_N2), (n_h2, hmt.CP_H2)):
        a, b, c = coeff
        total += n * (a * (t_k - hmt.T_REF)
                      + 0.5 * b * (t_k * t_k - hmt.T_REF * hmt.T_REF)
                      + (c / 3.0) * (t_k ** 3 - hmt.T_REF ** 3))
    return total


class TestDecompositionProducts(unittest.TestCase):
    """SKILL.md workflow step 2 (catalytic decomposition products of the
    hydrazine decomposition energy balance) is exercised here."""

    def test_products_frozen_x_zero(self):
        """Frozen limit x = 0: (4/3) NH3 + (1/3) N2, no H2."""
        n_nh3, n_n2, n_h2 = hmt.decomposition_products(0.0)
        self.assertTrue(math.isclose(n_nh3, 1.333333333333, rel_tol=1e-9))
        self.assertTrue(math.isclose(n_n2, 0.333333333333, rel_tol=1e-9))
        self.assertEqual(n_h2, 0.0)

    def test_products_x_four_tenths(self):
        """Worked 5 N point x = 0.4: 0.8 NH3 + 0.6 N2 + 0.8 H2."""
        n_nh3, n_n2, n_h2 = hmt.decomposition_products(0.4)
        self.assertTrue(math.isclose(n_nh3, 0.8, rel_tol=1e-9))
        self.assertTrue(math.isclose(n_n2, 0.6, rel_tol=1e-9))
        self.assertTrue(math.isclose(n_h2, 0.8, rel_tol=1e-9))

    def test_products_x_six_tenths(self):
        """Worked 22 N point x = 0.6: 0.533333 NH3 + 0.733333 N2 + 1.2 H2."""
        n_nh3, n_n2, n_h2 = hmt.decomposition_products(0.6)
        self.assertTrue(math.isclose(n_nh3, 0.533333333333, rel_tol=1e-9))
        self.assertTrue(math.isclose(n_n2, 0.733333333333, rel_tol=1e-9))
        self.assertTrue(math.isclose(n_h2, 1.2, rel_tol=1e-9))

    def test_products_fully_dissociated_x_one(self):
        """Fully dissociated limit x = 1: N2 + 2 H2, no NH3."""
        n_nh3, n_n2, n_h2 = hmt.decomposition_products(1.0)
        self.assertEqual(n_nh3, 0.0)
        self.assertTrue(math.isclose(n_n2, 1.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(n_h2, 2.0, rel_tol=1e-9))

    def test_product_mass_closure(self):
        """Products of the decomposition weigh exactly one mole of N2H4
        (32.04516 g) at every dissociation fraction, rel err 2.2e-16."""
        for x in (0.0, 0.4, 0.6, 1.0):
            n_nh3, n_n2, n_h2 = hmt.decomposition_products(x)
            mass = (n_nh3 * hmt.NH3_MOLAR_MASS + n_n2 * hmt.N2_MOLAR_MASS
                    + n_h2 * hmt.H2_MOLAR_MASS)
            self.assertTrue(math.isclose(mass, hmt.HYDRAZINE_MOLAR_MASS,
                                         rel_tol=1e-12))


class TestTotalMolesAndHeat(unittest.TestCase):
    """SKILL.md workflow steps 2 and 3 (product totals, net decomposition
    heat release of the hydrazine decomposition energy balance)."""

    def test_total_product_moles_values(self):
        """Mole totals 5/3 + (4/3)x: 1.666667 frozen, 2.2 at x = 0.4,
        2.466667 at x = 0.6, 3.0 fully dissociated."""
        for x, expected in ((0.0, 1.666666666667), (0.4, 2.2),
                            (0.6, 2.466666666667), (1.0, 3.0)):
            self.assertTrue(math.isclose(hmt.total_product_moles(x), expected,
                                         rel_tol=1e-12))

    def test_mole_sum_identity(self):
        """Closed-form mole-sum identity n_tot = 5/3 + (4/3)x holds."""
        for x in (0.0, 0.4, 0.6, 1.0):
            n_tot = hmt.total_product_moles(x)
            self.assertTrue(math.isclose(n_tot, 5.0 / 3.0 + 4.0 * x / 3.0,
                                         rel_tol=1e-12, abs_tol=1e-15))

    def test_heat_released_endpoints(self):
        """Q(0) = 111883.333333 J/mol frozen; Q(1) = 50630.000000 J/mol,
        the N2H4(l) -> N2 + 2 H2 limit releasing the liquid formation
        enthalpy magnitude (zero-enthalpy products)."""
        self.assertTrue(math.isclose(hmt.decomposition_heat_released(0.0),
                                     111883.333333, rel_tol=1e-9))
        q_one = hmt.decomposition_heat_released(1.0)
        self.assertTrue(math.isclose(q_one, 50630.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(q_one, abs(hmt.DELTA_HF_N2H4_LIQ),
                                     rel_tol=1e-12))

    def test_heat_released_linearity(self):
        """Q is linear in x: Q(0.6) - Q(0.4) = -12250.666667 J equals
        -(4/3)(0.2) DELTA_H_DISS_NH3 (endothermic ammonia dissociation)."""
        dq = hmt.decomposition_heat_released(0.6) - hmt.decomposition_heat_released(0.4)
        expect = -(4.0 / 3.0) * 0.2 * hmt.DELTA_H_DISS_NH3
        self.assertTrue(math.isclose(dq, expect, rel_tol=1e-9, abs_tol=1e-6))


class TestDecompositionTemperature(unittest.TestCase):
    """SKILL.md workflow step 4 (the adiabatic decomposition temperature
    T_c from the Hess-law energy balance by bisection)."""

    def test_temperature_worked_points(self):
        """Worked chamber temperatures: 1377.055452 K at x = 0.4 and
        1201.560097 K at x = 0.6."""
        self.assertTrue(math.isclose(hmt.decomposition_temperature(0.4),
                                     1377.0554521168, rel_tol=1e-9))
        self.assertTrue(math.isclose(hmt.decomposition_temperature(0.6),
                                     1201.5600973905, rel_tol=1e-9))

    def test_temperature_endpoints(self):
        """Published band reproduction: 1733.582996 K frozen, 864.824582 K
        fully dissociated, span 868.76 K, bracketing the reported 900 to
        1700 K decomposition-temperature band class (reference-only)."""
        self.assertTrue(math.isclose(hmt.decomposition_temperature(0.0),
                                     1733.5829956423, rel_tol=1e-9))
        self.assertTrue(math.isclose(hmt.decomposition_temperature(1.0),
                                     864.8245821564, rel_tol=1e-9))
        span = hmt.decomposition_temperature(0.0) - hmt.decomposition_temperature(1.0)
        self.assertTrue(math.isclose(span, 868.758413, rel_tol=1e-6))

    def test_temperature_monotone_sweep(self):
        """Seven-point dissociation sweep is strictly decreasing: 1733.583,
        1510.170, 1377.055, 1288.942, 1201.560, 1072.411, 864.825 K - the
        endothermic dissociation cools the products."""
        grid = (0.0, 0.25, 0.4, 0.5, 0.6, 0.75, 1.0)
        expected = (1733.583, 1510.170, 1377.055, 1288.942,
                    1201.560, 1072.411, 864.825)
        temps = [hmt.decomposition_temperature(x) for x in grid]
        for t_lo, t_hi in zip(temps, temps[1:]):
            self.assertLess(t_hi, t_lo)
        for t_c, exp in zip(temps, expected):
            self.assertTrue(math.isclose(t_c, exp, rel_tol=1e-9, abs_tol=5e-4))

    def test_energy_balance_closure(self):
        """Sensible-heat residual of the decomposition energy balance at the
        solved T_c is below 1e-9 J at x = 0.0, 0.4, 0.6, 1.0."""
        for x in (0.0, 0.4, 0.6, 1.0):
            t_c = hmt.decomposition_temperature(x)
            residual = (_sensible_heat_balance(x, t_c)
                        - hmt.decomposition_heat_released(x))
            self.assertLess(abs(residual), 1e-9)

    def test_product_heat_capacity_sample(self):
        """Workflow step 4 heat capacity sample at the chamber state of the
        5 N point is positive and matches the mole-weighted sum."""
        t_c = hmt.decomposition_temperature(0.4)
        n_nh3, n_n2, n_h2 = hmt.decomposition_products(0.4)
        manual = (n_nh3 * hmt.product_heat_capacity(0.4, t_c)
                  / hmt.total_product_moles(0.4) * hmt.total_product_moles(0.4))
        self.assertGreater(manual, 0.0)
        self.assertGreater(hmt.product_heat_capacity(0.4, t_c),
                           hmt.product_heat_capacity(0.4, 300.0))


class TestMixtureGas(unittest.TestCase):
    """SKILL.md workflow step 5 (mixture molar mass, mixture gas constant,
    frozen-composition isentropic exponent at the chamber state)."""

    def test_mixture_molar_mass_values(self):
        """14.565982 g/mol at x = 0.4, 12.991281 g/mol at x = 0.6."""
        self.assertTrue(math.isclose(hmt.mixture_molar_mass(0.4),
                                     14.5659818182, rel_tol=1e-9))
        self.assertTrue(math.isclose(hmt.mixture_molar_mass(0.6),
                                     12.9912810811, rel_tol=1e-9))

    def test_mixture_gas_constant_values(self):
        """570.813744 J/(kg K) at x = 0.4, 640.003289 J/(kg K) at x = 0.6."""
        self.assertTrue(math.isclose(hmt.mixture_gas_constant(0.4),
                                     570.81374409, rel_tol=1e-9))
        self.assertTrue(math.isclose(hmt.mixture_gas_constant(0.6),
                                     640.00328883, rel_tol=1e-9))

    def test_gamma_at_chamber_state(self):
        """Isentropic exponent of the frozen mixture at T_c: 1.251756670 at
        x = 0.4, 1.293281188 at x = 0.6."""
        self.assertTrue(math.isclose(hmt.mixture_gamma(0.4,
                                                       hmt.decomposition_temperature(0.4)),
                                     1.2517566697, rel_tol=1e-9))
        self.assertTrue(math.isclose(hmt.mixture_gamma(0.6,
                                                       hmt.decomposition_temperature(0.6)),
                                     1.2932811881, rel_tol=1e-9))

    def test_gamma_rises_with_dissociation(self):
        """Gamma at the chamber state rises from 1.175568175 (NH3-rich frozen
        mix) to 1.372593435 (fully dissociated N2 + 2 H2)."""
        t0 = hmt.decomposition_temperature(0.0)
        t1 = hmt.decomposition_temperature(1.0)
        self.assertTrue(math.isclose(hmt.mixture_gamma(0.0, t0),
                                     1.1755681751, rel_tol=1e-9))
        self.assertTrue(math.isclose(hmt.mixture_gamma(1.0, t1),
                                     1.3725934345, rel_tol=1e-9))
        self.assertLess(hmt.mixture_gamma(0.0, t0), hmt.mixture_gamma(1.0, t1))


class TestVacuumExpansion(unittest.TestCase):
    """SKILL.md workflow step 6 (frozen-composition isentropic expansion of
    the decomposed gas to the vacuum exhaust velocity, vacuum specific
    impulse and propellant mass flow at the thrust point)."""

    def test_exhaust_velocity_worked_points(self):
        """2795.808286 m/s at x = 0.4, 2604.253318 m/s at x = 0.6."""
        self.assertTrue(math.isclose(hmt.vacuum_exhaust_velocity(0.4),
                                     2795.8082861530, rel_tol=1e-6))
        self.assertTrue(math.isclose(hmt.vacuum_exhaust_velocity(0.6),
                                     2604.2533178836, rel_tol=1e-6))

    def test_specific_impulse_worked_points(self):
        """285.093104 s at x = 0.4, 265.559933 s at x = 0.6."""
        self.assertTrue(math.isclose(hmt.vacuum_specific_impulse(0.4),
                                     285.0931037768, rel_tol=1e-6))
        self.assertTrue(math.isclose(hmt.vacuum_specific_impulse(0.6),
                                     265.5599330947, rel_tol=1e-6))

    def test_impulse_equals_velocity_over_g0(self):
        """Isp = v_e / G0 exactly at x = 0.4."""
        self.assertTrue(math.isclose(
            hmt.vacuum_specific_impulse(0.4),
            hmt.vacuum_exhaust_velocity(0.4) / hmt.G0, rel_tol=1e-12))

    def test_exhaust_velocity_term_by_term_identity(self):
        """v_e reproduces sqrt(2 gamma/(gamma-1) R_mix T_c) evaluated term by
        term at the chamber state, zero difference at x = 0.4."""
        x = 0.4
        t_c = hmt.decomposition_temperature(x)
        gamma = hmt.mixture_gamma(x, t_c)
        r_mix = hmt.mixture_gas_constant(x)
        direct = math.sqrt(2.0 * gamma / (gamma - 1.0) * r_mix * t_c)
        self.assertTrue(math.isclose(hmt.vacuum_exhaust_velocity(x), direct,
                                     rel_tol=1e-12, abs_tol=1e-12))

    def test_frozen_impulse_exceeds_fully_dissociated(self):
        """Frozen 323.093261 s exceeds the fully dissociated 227.095324 s;
        the cooling dominates the lightening of the mixture."""
        self.assertTrue(math.isclose(hmt.vacuum_specific_impulse(0.0),
                                     323.0932607158, rel_tol=1e-6))
        self.assertTrue(math.isclose(hmt.vacuum_specific_impulse(1.0),
                                     227.0953242569, rel_tol=1e-6))
        self.assertGreater(hmt.vacuum_specific_impulse(0.0),
                           hmt.vacuum_specific_impulse(1.0))

    def test_propellant_mass_flow_worked_points(self):
        """mdot = F / v_e: 0.001788392 kg/s at 5 N / x = 0.4 (1.788 g/s),
        0.008447719 kg/s at 22 N / x = 0.6 (8.448 g/s)."""
        self.assertTrue(math.isclose(hmt.propellant_mass_flow(5.0, 0.4),
                                     0.001788391581, rel_tol=1e-6))
        self.assertTrue(math.isclose(hmt.propellant_mass_flow(22.0, 0.6),
                                     0.008447718910, rel_tol=1e-6))

    def test_mass_flow_linear_in_thrust(self):
        """Propellant mass flow scales linearly with thrust at fixed x."""
        ratio = hmt.propellant_mass_flow(10.0, 0.4) / hmt.propellant_mass_flow(5.0, 0.4)
        self.assertTrue(math.isclose(ratio, 2.0, rel_tol=1e-12))


class TestCatalystBedBand(unittest.TestCase):
    """SKILL.md workflow step 7 (advisory catalyst-bed temperature band
    verdict; the published band is reported reference-only, never enforced)."""

    def test_band_verdict_worked_points(self):
        """Chamber states of the 5 N (1377.055 K) and 22 N (1201.560 K)
        points sit inside [1073.15, 1423.15] K; the frozen 1733.583 K and
        fully dissociated 864.825 K points sit outside."""
        self.assertTrue(hmt.within_catalyst_bed_band(hmt.decomposition_temperature(0.4)))
        self.assertTrue(hmt.within_catalyst_bed_band(hmt.decomposition_temperature(0.6)))
        self.assertFalse(hmt.within_catalyst_bed_band(hmt.decomposition_temperature(0.0)))
        self.assertFalse(hmt.within_catalyst_bed_band(hmt.decomposition_temperature(1.0)))

    def test_band_boundaries_closed(self):
        """The band boundaries are closed: 1073.15 K and 1423.15 K are
        inside, just outside is False."""
        self.assertTrue(hmt.within_catalyst_bed_band(hmt.CATALYST_BED_BAND_LO))
        self.assertTrue(hmt.within_catalyst_bed_band(hmt.CATALYST_BED_BAND_HI))
        self.assertFalse(hmt.within_catalyst_bed_band(hmt.CATALYST_BED_BAND_LO - 0.1))
        self.assertFalse(hmt.within_catalyst_bed_band(hmt.CATALYST_BED_BAND_HI + 0.1))
        self.assertTrue(hmt.within_catalyst_bed_band(1200.0))


class TestDomainGuards(unittest.TestCase):
    """SKILL.md workflow steps 1 to 8: every non-physical input is rejected
    with ValueError, so a mis-set duty point can never silently run."""

    def test_valueerror_dissociation_fraction(self):
        """x outside [0, 1] or not finite raises ValueError across the
        decomposition functions."""
        for x in (-0.01, 1.01, float("nan")):
            with self.subTest(x=x):
                with self.assertRaises(ValueError):
                    hmt.decomposition_products(x)
        for x in (-0.01, 1.5):
            with self.subTest(x=x):
                with self.assertRaises(ValueError):
                    hmt.decomposition_temperature(x)
                with self.assertRaises(ValueError):
                    hmt.decomposition_heat_released(x)

    def test_valueerror_temperature_domain(self):
        """Non-positive sample temperatures raise ValueError for the product
        heat capacity and the isentropic exponent."""
        for t_k in (0.0, -5.0):
            with self.subTest(t_k=t_k):
                with self.assertRaises(ValueError):
                    hmt.product_heat_capacity(0.4, t_k)
                with self.assertRaises(ValueError):
                    hmt.mixture_gamma(0.4, t_k)

    def test_valueerror_g0_and_thrust(self):
        """Non-positive gravity and non-positive thrust raise ValueError."""
        with self.assertRaises(ValueError):
            hmt.vacuum_specific_impulse(0.4, g0=0.0)
        for thrust in (0.0, -5.0):
            with self.subTest(thrust=thrust):
                with self.assertRaises(ValueError):
                    hmt.propellant_mass_flow(thrust, 0.4)

    def test_valueerror_band_nan(self):
        """A non-finite temperature raises ValueError on the band verdict."""
        with self.assertRaises(ValueError):
            hmt.within_catalyst_bed_band(float("nan"))


class TestDeterminismAndApi(unittest.TestCase):
    """SKILL.md workflow step 8 (deterministic checks and the leaf boundary:
    the module never emits cold-gas, feed-cycle or electrical-heating
    outputs, never solves an equilibrium, never enforces the band)."""

    def test_determinism_bit_identical(self):
        """decomposition_temperature(0.4) returns 1377.055452116803281 on
        every call, bit-identical."""
        first = hmt.decomposition_temperature(0.4)
        second = hmt.decomposition_temperature(0.4)
        self.assertEqual(first, second)
        self.assertTrue(math.isclose(first, 1377.055452116803281, rel_tol=1e-12))

    def test_public_api_has_no_sibling_tokens(self):
        """The public API exposes no blowdown, plenum, choked-throat,
        feed-cycle, pump-power or heating-efficiency outputs."""
        module_text = "\n".join(dir(hmt))
        for token in ("blowdown", "plenum", "choked", "feed_cycle",
                      "pump_power", "heating_efficiency", "resistojet",
                      "arcjet", "equilibrium", "tank_volume", "ullage"):
            self.assertNotIn(token, module_text)

    def test_public_api_function_set(self):
        """The 12 documented station functions are present and callable."""
        expected = ("decomposition_products", "total_product_moles",
                    "decomposition_heat_released", "product_heat_capacity",
                    "decomposition_temperature", "mixture_molar_mass",
                    "mixture_gas_constant", "mixture_gamma",
                    "vacuum_exhaust_velocity", "vacuum_specific_impulse",
                    "propellant_mass_flow", "within_catalyst_bed_band")
        for name in expected:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(hmt, name)))


if __name__ == "__main__":
    unittest.main()
