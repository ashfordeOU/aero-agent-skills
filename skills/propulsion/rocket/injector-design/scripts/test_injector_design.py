"""Contract test for rocket engine injector element design logic.

Offline deterministic stdlib unittest. Run from the repo root:

    python3 skills/propulsion/rocket/injector-design/scripts/test_injector_design.py

Covers the worked-example anchors (Cd 0.8, dP 2.0 MPa, 2.5 mm orifices,
RP-1 at 820 kg/m3, LOX at 1140 kg/m3, chamber flow 70.686 kg/s at
O/F 2.56), the discharge and momentum-flux identities, ceil behavior of
orifice counts, the element flow balance, layout summary coverage and
ValueError rejection of every non-physical input.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from injector_design_logic import (
    PI,
    element_mass_flow,
    injection_velocity,
    injector_layout_summary,
    momentum_flux_ratio,
    orifice_area,
    orifice_count,
    orifice_mass_flow,
)

# Worked-example operating point (wave-34 spec anchors).
DISCHARGE_COEFFICIENT = 0.8
PRESSURE_DROP_PA = 2.0e6
FUEL_DENSITY = 820.0       # RP-1, kg/m3
OXIDIZER_DENSITY = 1140.0  # LOX, kg/m3
ORIFICE_DIAMETER_M = 0.0025
CHAMBER_MASS_FLOW_KGS = 70.686
MIXTURE_RATIO = 2.56

EXPECTED_KEYS = [
    "fuel_mass_flow_kgs", "oxidizer_mass_flow_kgs",
    "fuel_area_m2", "oxidizer_area_m2",
    "fuel_injection_velocity_m_s", "oxidizer_injection_velocity_m_s",
    "fuel_per_orifice_mass_flow_kgs", "oxidizer_per_orifice_mass_flow_kgs",
    "momentum_flux_ratio", "fuel_orifice_count", "oxidizer_orifice_count",
    "element_count", "per_element_fuel_kgs", "per_element_oxidizer_kgs",
    "per_element_total_kgs",
]


def worked_summary():
    """Layout summary for the spec worked example: 1 fuel + 2 LOX element."""
    return injector_layout_summary(
        CHAMBER_MASS_FLOW_KGS, MIXTURE_RATIO,
        FUEL_DENSITY, OXIDIZER_DENSITY,
        PRESSURE_DROP_PA, PRESSURE_DROP_PA,
        DISCHARGE_COEFFICIENT, ORIFICE_DIAMETER_M, ORIFICE_DIAMETER_M,
        1, 2)


class TestOrificeGeometry(unittest.TestCase):
    """Orifice area geometry."""

    def test_orifice_area_anchor_matches_formula(self):
        area = orifice_area(ORIFICE_DIAMETER_M)
        self.assertAlmostEqual(area, 4.909e-6, delta=5e-9)
        self.assertTrue(math.isclose(area,
                                     PI * ORIFICE_DIAMETER_M ** 2 / 4.0,
                                     rel_tol=1e-12))

    def test_orifice_area_scales_quadratically(self):
        small = orifice_area(0.001)
        large = orifice_area(0.002)
        self.assertAlmostEqual(large, 4.0 * small, places=12)

    def test_orifice_area_rejects_non_positive(self):
        for bad in (0.0, -0.001):
            with self.assertRaises(ValueError):
                orifice_area(bad)


class TestInjectionVelocity(unittest.TestCase):
    """Bernoulli-head injection velocity with the discharge coefficient."""

    def test_injection_velocity_fuel_anchor(self):
        v = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                               FUEL_DENSITY)
        self.assertAlmostEqual(v, 55.87, delta=0.005)

    def test_injection_velocity_lox_anchor_and_density_trend(self):
        v = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                               OXIDIZER_DENSITY)
        self.assertAlmostEqual(v, 47.39, delta=0.005)
        v_light = injection_velocity(0.8, 2.0e6, 400.0)
        self.assertGreater(v_light, v)

    def test_injection_velocity_law_identity(self):
        v = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                               FUEL_DENSITY)
        expected = (DISCHARGE_COEFFICIENT
                    * math.sqrt(2.0 * PRESSURE_DROP_PA / FUEL_DENSITY))
        self.assertAlmostEqual(v, expected, places=12)
        half = injection_velocity(0.4, PRESSURE_DROP_PA, FUEL_DENSITY)
        self.assertAlmostEqual(half, 0.5 * v, places=12)

    def test_injection_velocity_rejects_non_positive(self):
        for cd in (0.0, -0.8):
            with self.assertRaises(ValueError):
                injection_velocity(cd, PRESSURE_DROP_PA, FUEL_DENSITY)
        for dp in (0.0, -2.0e6):
            with self.assertRaises(ValueError):
                injection_velocity(DISCHARGE_COEFFICIENT, dp, FUEL_DENSITY)
        for rho in (0.0, -820.0):
            with self.assertRaises(ValueError):
                injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                   rho)


class TestOrificeMassFlow(unittest.TestCase):
    """Per-orifice discharge: m_dot = rho * A * v with v = Cd sqrt(2 dP/rho)."""

    def test_orifice_mass_flow_dict_keys_exact(self):
        result = orifice_mass_flow(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                   FUEL_DENSITY, ORIFICE_DIAMETER_M)
        self.assertEqual(set(result.keys()),
                         {"area_m2", "velocity_m_s", "mass_flow_kgs"})

    def test_orifice_mass_flow_discharge_identities(self):
        result = orifice_mass_flow(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                   FUEL_DENSITY, ORIFICE_DIAMETER_M)
        # m_dot equals density * area * velocity to 1e-12...
        self.assertAlmostEqual(result["mass_flow_kgs"],
                               FUEL_DENSITY * result["area_m2"]
                               * result["velocity_m_s"], places=12)
        # ...and matches the standard law Cd * A * sqrt(2 rho dP).
        area = PI * ORIFICE_DIAMETER_M ** 2 / 4.0
        standard = (DISCHARGE_COEFFICIENT * area
                    * math.sqrt(2.0 * FUEL_DENSITY * PRESSURE_DROP_PA))
        self.assertTrue(math.isclose(result["mass_flow_kgs"], standard,
                                     rel_tol=1e-9))

    def test_orifice_mass_flow_anchor_values(self):
        fuel = orifice_mass_flow(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                 FUEL_DENSITY, ORIFICE_DIAMETER_M)
        lox = orifice_mass_flow(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                OXIDIZER_DENSITY, ORIFICE_DIAMETER_M)
        self.assertAlmostEqual(fuel["mass_flow_kgs"], 0.2249, delta=5e-5)
        self.assertAlmostEqual(lox["mass_flow_kgs"], 0.2652, delta=5e-5)

    def test_orifice_mass_flow_rejects_non_positive(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                orifice_mass_flow(bad, PRESSURE_DROP_PA, FUEL_DENSITY,
                                  ORIFICE_DIAMETER_M)
            with self.assertRaises(ValueError):
                orifice_mass_flow(DISCHARGE_COEFFICIENT, bad, FUEL_DENSITY,
                                  ORIFICE_DIAMETER_M)
            with self.assertRaises(ValueError):
                orifice_mass_flow(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                  bad, ORIFICE_DIAMETER_M)
            with self.assertRaises(ValueError):
                orifice_mass_flow(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                  FUEL_DENSITY, bad)


class TestMomentumFluxRatio(unittest.TestCase):
    """Doublet momentum flux ratio and its equal-dP identity."""

    def test_momentum_flux_ratio_equal_dp_identity(self):
        v_f = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                 FUEL_DENSITY)
        v_o = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                 OXIDIZER_DENSITY)
        j = momentum_flux_ratio(OXIDIZER_DENSITY, v_o, FUEL_DENSITY, v_f)
        self.assertAlmostEqual(j, 1.0, places=9)
        direct = ((OXIDIZER_DENSITY * v_o * v_o)
                  / (FUEL_DENSITY * v_f * v_f))
        self.assertAlmostEqual(j, direct, places=12)

    def test_momentum_flux_ratio_unequal_dp_scaling(self):
        # dP_o 2.5 MPa against dP_f 2.0 MPa gives J = dP_o / dP_f = 1.25
        # because the Cd and density cancel inside each momentum term.
        v_f = injection_velocity(DISCHARGE_COEFFICIENT, 2.0e6, FUEL_DENSITY)
        v_o = injection_velocity(DISCHARGE_COEFFICIENT, 2.5e6, OXIDIZER_DENSITY)
        j = momentum_flux_ratio(OXIDIZER_DENSITY, v_o, FUEL_DENSITY, v_f)
        self.assertAlmostEqual(j, 1.25, places=9)

    def test_momentum_flux_ratio_rejects_non_positive(self):
        v_f = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                 FUEL_DENSITY)
        v_o = injection_velocity(DISCHARGE_COEFFICIENT, PRESSURE_DROP_PA,
                                 OXIDIZER_DENSITY)
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                momentum_flux_ratio(bad, v_o, FUEL_DENSITY, v_f)
            with self.assertRaises(ValueError):
                momentum_flux_ratio(OXIDIZER_DENSITY, bad, FUEL_DENSITY, v_f)
            with self.assertRaises(ValueError):
                momentum_flux_ratio(OXIDIZER_DENSITY, v_o, bad, v_f)
            with self.assertRaises(ValueError):
                momentum_flux_ratio(OXIDIZER_DENSITY, v_o, FUEL_DENSITY, bad)


class TestOrificeCount(unittest.TestCase):
    """Integer orifice counts round up on fractional requirements."""

    def test_orifice_count_ceil_anchors(self):
        self.assertEqual(orifice_count(88.28, 1.0), 89)
        self.assertEqual(orifice_count(191.68, 1.0), 192)

    def test_orifice_count_integral_requirements_not_bumped(self):
        self.assertEqual(orifice_count(88.0, 1.0), 88)
        self.assertEqual(orifice_count(4.0, 0.5), 8)
        self.assertEqual(orifice_count(0.2249, 0.2249), 1)
        self.assertEqual(orifice_count(0.0, 0.5), 0)

    def test_orifice_count_rounds_up_on_tiny_excess(self):
        self.assertEqual(orifice_count(88.0001, 1.0), 89)

    def test_orifice_count_rejects_invalid(self):
        with self.assertRaises(ValueError):
            orifice_count(10.0, 0.0)
        with self.assertRaises(ValueError):
            orifice_count(10.0, -0.5)
        with self.assertRaises(ValueError):
            orifice_count(-1.0, 0.5)


class TestElementMassFlow(unittest.TestCase):
    """Per-element flow balance for a fixed orifice layout."""

    def test_element_mass_flow_anchor_balance_and_keys(self):
        result = element_mass_flow(1, 2, 0.2249, 0.2652)
        self.assertEqual(set(result.keys()),
                         {"fuel_kgs", "oxidizer_kgs", "total_kgs"})
        self.assertAlmostEqual(result["fuel_kgs"], 0.2249, places=10)
        self.assertAlmostEqual(result["oxidizer_kgs"], 0.5304, places=10)
        self.assertAlmostEqual(result["total_kgs"], 0.7553, delta=1e-4)

    def test_element_mass_flow_is_orifice_sum(self):
        result = element_mass_flow(1, 2, 0.2249, 0.2652)
        self.assertAlmostEqual(result["total_kgs"],
                               result["fuel_kgs"] + result["oxidizer_kgs"],
                               places=12)

    def test_element_mass_flow_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            element_mass_flow(0, 2, 0.2249, 0.2652)
        with self.assertRaises(ValueError):
            element_mass_flow(1, -2, 0.2249, 0.2652)
        with self.assertRaises(ValueError):
            element_mass_flow(1, 2, 0.0, 0.2652)
        with self.assertRaises(ValueError):
            element_mass_flow(1, 2, 0.2249, -0.2652)


class TestInjectorLayoutSummary(unittest.TestCase):
    """Whole-face summary: mass split, counts, coverage, determinism."""

    def test_layout_summary_mass_split_and_ratio(self):
        s = worked_summary()
        self.assertAlmostEqual(s["fuel_mass_flow_kgs"], 19.86, delta=0.005)
        self.assertAlmostEqual(s["oxidizer_mass_flow_kgs"], 50.83,
                               delta=0.005)
        ratio = s["oxidizer_mass_flow_kgs"] / s["fuel_mass_flow_kgs"]
        self.assertAlmostEqual(ratio, MIXTURE_RATIO, places=9)
        self.assertAlmostEqual(s["fuel_mass_flow_kgs"]
                               + s["oxidizer_mass_flow_kgs"],
                               CHAMBER_MASS_FLOW_KGS, places=9)

    def test_layout_summary_orifice_count_anchors(self):
        s = worked_summary()
        self.assertEqual(s["fuel_orifice_count"], 89)
        self.assertEqual(s["oxidizer_orifice_count"], 192)

    def test_layout_summary_velocity_flow_area_anchors(self):
        s = worked_summary()
        self.assertAlmostEqual(s["fuel_area_m2"], 4.909e-6, delta=5e-9)
        self.assertAlmostEqual(s["oxidizer_area_m2"], s["fuel_area_m2"],
                               places=15)
        self.assertAlmostEqual(s["fuel_injection_velocity_m_s"], 55.87,
                               delta=0.005)
        self.assertAlmostEqual(s["oxidizer_injection_velocity_m_s"], 47.39,
                               delta=0.005)
        self.assertAlmostEqual(s["fuel_per_orifice_mass_flow_kgs"], 0.2249,
                               delta=5e-5)
        self.assertAlmostEqual(s["oxidizer_per_orifice_mass_flow_kgs"],
                               0.2652, delta=5e-5)

    def test_layout_summary_momentum_flux_ratio_identity(self):
        s = worked_summary()
        self.assertAlmostEqual(s["momentum_flux_ratio"], 1.0, places=9)

    def test_layout_summary_element_count_and_chamber_coverage(self):
        s = worked_summary()
        # Binding side: LOX needs ceil(192 / 2) = 96 elements, fuel
        # ceil(89 / 1) = 89; 96 whole elements cover the full chamber flow.
        self.assertEqual(s["element_count"], 96)
        delivered = s["element_count"] * s["per_element_total_kgs"]
        self.assertGreaterEqual(delivered, CHAMBER_MASS_FLOW_KGS)
        # Six-element groups of the element type: 16 groups of 6 carry
        # the whole chamber flow within the round-up excess.
        six_group = 6 * s["per_element_total_kgs"]
        self.assertAlmostEqual(six_group, 4.5316, delta=1e-3)
        self.assertGreaterEqual(16 * six_group, CHAMBER_MASS_FLOW_KGS)

    def test_layout_summary_element_balance_anchor(self):
        s = worked_summary()
        self.assertAlmostEqual(s["per_element_fuel_kgs"], 0.2249, delta=5e-5)
        self.assertAlmostEqual(s["per_element_oxidizer_kgs"], 0.5304,
                               delta=1e-4)
        self.assertAlmostEqual(s["per_element_total_kgs"], 0.7553, delta=1e-4)
        self.assertAlmostEqual(s["per_element_total_kgs"],
                               s["per_element_fuel_kgs"]
                               + s["per_element_oxidizer_kgs"], places=12)

    def test_layout_summary_dict_keys_exact(self):
        s = worked_summary()
        self.assertEqual(list(s.keys()), EXPECTED_KEYS)

    def test_layout_summary_deterministic(self):
        self.assertEqual(worked_summary(), worked_summary())

    def test_layout_summary_rejects_non_physical_inputs(self):
        for chamber in (0.0, -70.686):
            with self.assertRaises(ValueError):
                injector_layout_summary(chamber, MIXTURE_RATIO, FUEL_DENSITY,
                                        OXIDIZER_DENSITY, PRESSURE_DROP_PA,
                                        PRESSURE_DROP_PA,
                                        DISCHARGE_COEFFICIENT,
                                        ORIFICE_DIAMETER_M,
                                        ORIFICE_DIAMETER_M, 1, 2)
        for of in (0.0, -2.56):
            with self.assertRaises(ValueError):
                injector_layout_summary(CHAMBER_MASS_FLOW_KGS, of,
                                        FUEL_DENSITY, OXIDIZER_DENSITY,
                                        PRESSURE_DROP_PA, PRESSURE_DROP_PA,
                                        DISCHARGE_COEFFICIENT,
                                        ORIFICE_DIAMETER_M,
                                        ORIFICE_DIAMETER_M, 1, 2)
        with self.assertRaises(ValueError):
            injector_layout_summary(CHAMBER_MASS_FLOW_KGS, MIXTURE_RATIO,
                                    FUEL_DENSITY, OXIDIZER_DENSITY, 0.0,
                                    PRESSURE_DROP_PA, DISCHARGE_COEFFICIENT,
                                    ORIFICE_DIAMETER_M, ORIFICE_DIAMETER_M, 1,
                                    2)
        for rho in (0.0, -820.0):
            with self.assertRaises(ValueError):
                injector_layout_summary(CHAMBER_MASS_FLOW_KGS, MIXTURE_RATIO,
                                        rho, OXIDIZER_DENSITY,
                                        PRESSURE_DROP_PA, PRESSURE_DROP_PA,
                                        DISCHARGE_COEFFICIENT,
                                        ORIFICE_DIAMETER_M,
                                        ORIFICE_DIAMETER_M, 1, 2)
        with self.assertRaises(ValueError):
            injector_layout_summary(CHAMBER_MASS_FLOW_KGS, MIXTURE_RATIO,
                                    FUEL_DENSITY, OXIDIZER_DENSITY,
                                    PRESSURE_DROP_PA, PRESSURE_DROP_PA,
                                    DISCHARGE_COEFFICIENT, 0.0,
                                    ORIFICE_DIAMETER_M, 1, 2)
        with self.assertRaises(ValueError):
            injector_layout_summary(CHAMBER_MASS_FLOW_KGS, MIXTURE_RATIO,
                                    FUEL_DENSITY, OXIDIZER_DENSITY,
                                    PRESSURE_DROP_PA, PRESSURE_DROP_PA,
                                    DISCHARGE_COEFFICIENT, ORIFICE_DIAMETER_M,
                                    ORIFICE_DIAMETER_M, 0, 2)
        with self.assertRaises(ValueError):
            injector_layout_summary(CHAMBER_MASS_FLOW_KGS, MIXTURE_RATIO,
                                    FUEL_DENSITY, OXIDIZER_DENSITY,
                                    PRESSURE_DROP_PA, PRESSURE_DROP_PA, 0.0,
                                    ORIFICE_DIAMETER_M, ORIFICE_DIAMETER_M, 1,
                                    2)


if __name__ == "__main__":
    unittest.main()
