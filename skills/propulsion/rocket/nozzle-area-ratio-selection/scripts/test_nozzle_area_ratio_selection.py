"""Contract test for nozzle_area_ratio_selection_logic (propulsion/rocket/nozzle-area-ratio-selection).

Exercises every numbered workflow step of the SKILL.md body: step 2 (read
the design-altitude ambient pressure from the ISA-76 three-layer model with
ambient_pressure_at_altitude), step 3 (the design-altitude selection solve
with design_altitude_area_ratio and expansion_matched_area_ratio, the
inverse of the nozzle-design forward map), step 4 (the matched flow-state
read-off with exit_mach_from_area_ratio, exit_static_pressure,
exit_velocity and choked_mass_flow), step 5 (the delivered isp triple at
the chosen ratio with delivered_isp and the matched identity), step 6 (the
attached-flow guard decision with attached_flow_guard) and the
deterministic gate-3 behavior contract checklist of step 7. The anchors
are the real prep values of the wave-44 spec (LOX/RP-1 upper-stage
chamber, 7.0 MPa, 3672 K, Mw 22.1 so R = 376.220 J/(kg K), gamma 1.24,
At = 0.070686 m^2, design altitude 20 km) cross-checked against the
wave-43 rocket-nozzle-divergence-loss sibling numbers. All computed
aggregates are asserted with tolerances (isclose / assertAlmostEqual
delta), never exact float equality, so the suite passes identically under
the system and pyenv interpreters.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)
import nozzle_area_ratio_selection_logic as nar

P0 = 7.0e6  # chamber pressure, Pa
T0 = 3672.0  # chamber temperature, K
GAMMA = 1.24  # specific heat ratio
R_GAS = 376.220  # R = 8314.462 / 22.1, J/(kg K)
AT = 0.070686  # throat area, m^2 (0.150 m radius)
SEA_LEVEL = 101325.0  # Pa


def _area_from_mach(mach):
    """Forward area-Mach relation helper for the round-trip identities."""
    return (1.0 / mach) * (
        (2.0 / (GAMMA + 1.0)) * (1.0 + 0.5 * (GAMMA - 1.0) * mach * mach)
    ) ** ((GAMMA + 1.0) / (2.0 * (GAMMA - 1.0)))


class AmbientPressureTests(unittest.TestCase):
    """Workflow step 2 of the SKILL.md body: the design-altitude ambient."""

    def test_ambient_pressure_sea_level_anchor(self):
        """Step 2 read-off at 0 m: the ISA base returns 101325.00 Pa within 0.01 Pa."""
        self.assertAlmostEqual(nar.ambient_pressure_at_altitude(0.0), 101325.00, delta=0.01)

    def test_ambient_pressure_tropopause_anchor(self):
        """Step 2 read-off at 11000 m: the ISA tropopause returns 22632.06 Pa within 0.01 Pa."""
        self.assertAlmostEqual(nar.ambient_pressure_at_altitude(11000.0), 22632.06, delta=0.01)

    def test_ambient_pressure_20km_anchor(self):
        """Step 2 read-off at 20000 m: the isothermal layer base returns 5474.88 Pa within 0.01 Pa."""
        self.assertAlmostEqual(nar.ambient_pressure_at_altitude(20000.0), 5474.88, delta=0.01)

    def test_ambient_pressure_30km_anchor(self):
        """Step 2 read-off at 30000 m: the upper lapse layer returns 1171.87 Pa within 0.01 Pa."""
        self.assertAlmostEqual(nar.ambient_pressure_at_altitude(30000.0), 1171.87, delta=0.01)

    def test_ambient_pressure_negative_altitude_rejected(self):
        """Step 2 guard: an altitude below 0 m is outside the ISA-76 band and raises ValueError."""
        with self.assertRaises(ValueError):
            nar.ambient_pressure_at_altitude(-1.0)

    def test_ambient_pressure_above_model_rejected(self):
        """Step 2 guard: an altitude above 32000 m is outside the ISA-76 band and raises ValueError."""
        with self.assertRaises(ValueError):
            nar.ambient_pressure_at_altitude(40000.0)


class ExitMachTests(unittest.TestCase):
    """Workflow step 4 read-off: the supersonic-branch root of the area-Mach relation."""

    def test_exit_mach_sibling_cross_check(self):
        """Step 4 anchor: at eps = 70.0 the module reproduces the wave-43 sibling Me = 4.931384 within 1e-5."""
        self.assertAlmostEqual(nar.exit_mach_from_area_ratio(70.0, GAMMA), 4.931384, delta=1e-5)

    def test_exit_mach_area_round_trip(self):
        """Step 4 identity: the forward area-Mach map fed with the solved root recovers 70.0 and the 20 km eps* with relative error below 1e-9."""
        mach70 = nar.exit_mach_from_area_ratio(70.0, GAMMA)
        self.assertTrue(math.isclose(_area_from_mach(mach70), 70.0, rel_tol=1e-12, abs_tol=1e-12))
        eps_star = nar.design_altitude_area_ratio(P0, GAMMA, 20000.0)
        self.assertTrue(math.isclose(
            _area_from_mach(nar.exit_mach_from_area_ratio(eps_star, GAMMA)),
            eps_star, rel_tol=1e-9, abs_tol=1e-9,
        ))

    def test_exit_mach_valueerror(self):
        """Step 4 guard: area ratios at or below 1 and gamma at or below 1 raise ValueError (no supersonic root)."""
        with self.assertRaises(ValueError):
            nar.exit_mach_from_area_ratio(1.0, GAMMA)
        with self.assertRaises(ValueError):
            nar.exit_mach_from_area_ratio(0.5, GAMMA)
        with self.assertRaises(ValueError):
            nar.exit_mach_from_area_ratio(70.0, 1.0)


class ExitStaticPressureTests(unittest.TestCase):
    """Workflow step 4 read-off: the exit static pressure branch Pe(eps)."""

    def test_exit_static_pressure_sibling_cross_check(self):
        """Step 4 anchor: Pe(70.0) = 6036.738 Pa within 0.01 Pa, the wave-43 sibling value at the same gas and throat."""
        self.assertAlmostEqual(nar.exit_static_pressure(70.0, P0, GAMMA), 6036.738, delta=0.01)

    def test_throat_plane_ceiling_anchor(self):
        """Step 3 bound: the throat-plane ceiling Pe(1) = 3897668.7 Pa within 0.1 Pa closes the selection domain."""
        ceiling = nar._throat_plane_ceiling(P0, GAMMA)
        self.assertAlmostEqual(ceiling, 3897668.7, delta=0.1)
        closed_form = P0 * (2.0 / (GAMMA + 1.0)) ** (GAMMA / (GAMMA - 1.0))
        self.assertTrue(math.isclose(ceiling, closed_form, rel_tol=1e-12))

    def test_exit_static_pressure_valueerror(self):
        """Step 4 guard: non-positive chamber pressure, gamma at or below 1 and a ratio at or below 1 raise ValueError."""
        with self.assertRaises(ValueError):
            nar.exit_static_pressure(70.0, 0.0, GAMMA)
        with self.assertRaises(ValueError):
            nar.exit_static_pressure(70.0, P0, 1.0)
        with self.assertRaises(ValueError):
            nar.exit_static_pressure(1.0, P0, GAMMA)


class MatchedSelectionTests(unittest.TestCase):
    """Workflow step 3 of the SKILL.md body: the inverse selection solve."""

    def test_expansion_matched_ratio_20km_anchor(self):
        """Step 3 solve at the 20 km ambient: eps* = 75.4961 within 1e-3 with the closure |Pe(eps*) - pa| below 1e-3 Pa."""
        eps_star = nar.expansion_matched_area_ratio(P0, GAMMA, 5474.88)
        self.assertAlmostEqual(eps_star, 75.4961, delta=1e-3)
        residual = nar.exit_static_pressure(eps_star, P0, GAMMA) - 5474.88
        self.assertTrue(abs(residual) < 1e-3)

    def test_expansion_matched_ratio_sea_level_anchor(self):
        """Step 3 solve at the sea-level ambient: eps* = 8.3061 within 1e-3 (the smallest of the altitude sweep)."""
        self.assertAlmostEqual(
            nar.expansion_matched_area_ratio(P0, GAMMA, SEA_LEVEL), 8.3061, delta=1e-3
        )

    def test_expansion_matched_ratio_vacuum_rejected(self):
        """Step 3 guard: pa = 0 (vacuum) has no finite matched ratio and raises ValueError."""
        with self.assertRaises(ValueError):
            nar.expansion_matched_area_ratio(P0, GAMMA, 0.0)

    def test_expansion_matched_ratio_above_ceiling_rejected(self):
        """Step 3 guard: an ambient above the Pe(1) ceiling (81190.5 Pa at p0 = 150000 Pa, gamma 1.4) raises ValueError."""
        with self.assertRaises(ValueError):
            nar.expansion_matched_area_ratio(150000.0, 1.4, 101325.0)

    def test_design_altitude_area_ratio_20km_anchor(self):
        """Step 3 altitude solve: design_altitude_area_ratio(7.0e6, 1.24, 20000.0) = 75.4961 within 1e-3."""
        self.assertAlmostEqual(
            nar.design_altitude_area_ratio(P0, GAMMA, 20000.0), 75.4961, delta=1e-3
        )

    def test_design_altitude_area_ratio_sweep_monotone(self):
        """Step 3 altitude sweep: 0/11/20/30 km return 8.3061 / 25.416 / 75.4961 / 251.1241, strictly increasing, each with closure below 1e-3 Pa."""
        ratios = [
            nar.design_altitude_area_ratio(P0, GAMMA, h)
            for h in (0.0, 11000.0, 20000.0, 30000.0)
        ]
        self.assertAlmostEqual(ratios[0], 8.3061, delta=1e-3)
        self.assertAlmostEqual(ratios[1], 25.416, delta=1e-3)
        self.assertAlmostEqual(ratios[2], 75.4961, delta=1e-3)
        self.assertAlmostEqual(ratios[3], 251.1241, delta=1e-3)
        self.assertTrue(all(b > a for a, b in zip(ratios, ratios[1:])))
        for h in (0.0, 11000.0, 20000.0, 30000.0):
            pa = nar.ambient_pressure_at_altitude(h)
            eps = nar.expansion_matched_area_ratio(P0, GAMMA, pa)
            self.assertTrue(abs(nar.exit_static_pressure(eps, P0, GAMMA) - pa) < 1e-3)

    def test_design_altitude_area_ratio_out_of_band_rejected(self):
        """Step 3 guard: a design altitude outside the ISA-76 band raises ValueError through the ambient caller."""
        with self.assertRaises(ValueError):
            nar.design_altitude_area_ratio(P0, GAMMA, -1.0)
        with self.assertRaises(ValueError):
            nar.design_altitude_area_ratio(P0, GAMMA, 40000.0)


class FlowScaleTests(unittest.TestCase):
    """Workflow step 4 read-off: the choked flow scale, the exit velocity and the expanded ceiling."""

    def test_choked_mass_flow_sibling_cross_check(self):
        """Step 4 anchor: mdot = 276.24 kg/s within 0.01, the wave-43 sibling choked flow at this gas and throat."""
        self.assertAlmostEqual(
            nar.choked_mass_flow(AT, P0, T0, GAMMA, R_GAS), 276.24, delta=0.01
        )

    def test_choked_mass_flow_valueerror(self):
        """Step 4 guard: non-positive throat area and gamma at or below 1 raise ValueError."""
        with self.assertRaises(ValueError):
            nar.choked_mass_flow(0.0, P0, T0, GAMMA, R_GAS)
        with self.assertRaises(ValueError):
            nar.choked_mass_flow(AT, P0, T0, 1.0, R_GAS)

    def test_fully_expanded_ceiling_bound(self):
        """Step 5 ceiling bound: sqrt(2*gamma/(gamma-1) * R * T0) = 3778.266 m/s (Isp 385.276 s) sits above every finite-ratio vacuum value."""
        ceiling_ve = math.sqrt(2.0 * GAMMA / (GAMMA - 1.0) * R_GAS * T0)
        self.assertAlmostEqual(ceiling_ve, 3778.266, delta=0.01)
        ceiling_isp = ceiling_ve / nar.G0
        self.assertAlmostEqual(ceiling_isp, 385.276, delta=0.01)
        for h in (0.0, 20000.0):
            eps = nar.design_altitude_area_ratio(P0, GAMMA, h)
            vac = nar.delivered_isp(eps, P0, T0, GAMMA, R_GAS, 0.0, AT)
            self.assertTrue(vac < ceiling_isp)

    def test_exit_velocity_valueerror(self):
        """Step 4 guard: area ratios at or below 1 and non-positive gas inputs raise ValueError."""
        with self.assertRaises(ValueError):
            nar.exit_velocity(0.5, P0, T0, GAMMA, R_GAS)
        with self.assertRaises(ValueError):
            nar.exit_velocity(70.0, P0, 0.0, GAMMA, R_GAS)


class DeliveredIspTests(unittest.TestCase):
    """Workflow step 5 of the SKILL.md body: the delivered isp triple at the chosen ratio."""

    def test_isp_triple_at_design_ratio(self):
        """Step 5 triple at eps* = 75.4961: design-altitude 333.561 s, vacuum 344.347 s, sea level 144.743 s, each within 0.05 s."""
        eps_star = nar.design_altitude_area_ratio(P0, GAMMA, 20000.0)
        pa_design = nar.ambient_pressure_at_altitude(20000.0)
        isp_design = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, pa_design, AT)
        isp_vacuum = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, 0.0, AT)
        isp_sea = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, SEA_LEVEL, AT)
        self.assertAlmostEqual(isp_design, 333.561, delta=0.05)
        self.assertAlmostEqual(isp_vacuum, 344.347, delta=0.05)
        self.assertAlmostEqual(isp_sea, 144.743, delta=0.05)

    def test_isp_matched_identity_design_altitude(self):
        """Step 5 matched identity: at the solved ratio the design-altitude Isp equals ve / g0 within 1e-9 relative, the pressure term vanishes; ve = 3271.120 m/s."""
        eps_star = nar.design_altitude_area_ratio(P0, GAMMA, 20000.0)
        pa_design = nar.ambient_pressure_at_altitude(20000.0)
        isp_design = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, pa_design, AT)
        ve = nar.exit_velocity(eps_star, P0, T0, GAMMA, R_GAS)
        self.assertAlmostEqual(ve, 3271.120, delta=0.05)
        self.assertTrue(math.isclose(isp_design, ve / nar.G0, rel_tol=1e-9, abs_tol=1e-9))

    def test_isp_sea_level_matched_reference(self):
        """Step 5 reference at the sea-level matched ratio: 288.174 s at sea level (= ve / g0) and 310.134 s in vacuum."""
        eps_sea = nar.design_altitude_area_ratio(P0, GAMMA, 0.0)
        isp_sea = nar.delivered_isp(eps_sea, P0, T0, GAMMA, R_GAS, SEA_LEVEL, AT)
        isp_vac = nar.delivered_isp(eps_sea, P0, T0, GAMMA, R_GAS, 0.0, AT)
        self.assertAlmostEqual(isp_sea, 288.174, delta=0.05)
        self.assertAlmostEqual(isp_vac, 310.134, delta=0.05)
        ve_over_g0 = nar.exit_velocity(eps_sea, P0, T0, GAMMA, R_GAS) / nar.G0
        self.assertTrue(math.isclose(isp_sea, ve_over_g0, rel_tol=1e-9, abs_tol=1e-9))

    def test_isp_pressure_term_split(self):
        """Step 5 pressure-term split: vacuum minus design-altitude is the +10.785 s bonus and sea-level minus design-altitude the -188.818 s penalty of the finite ratio."""
        eps_star = nar.design_altitude_area_ratio(P0, GAMMA, 20000.0)
        pa_design = nar.ambient_pressure_at_altitude(20000.0)
        mdot = nar.choked_mass_flow(AT, P0, T0, GAMMA, R_GAS)
        isp_design = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, pa_design, AT)
        isp_vacuum = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, 0.0, AT)
        isp_sea = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, SEA_LEVEL, AT)
        bonus = isp_vacuum - isp_design
        penalty = isp_sea - isp_design
        self.assertAlmostEqual(bonus, 10.785, delta=0.01)
        self.assertAlmostEqual(penalty, -188.818, delta=0.01)
        # Exact pressure-term identities in real arithmetic: the ambient cancels.
        self.assertTrue(math.isclose(
            bonus, pa_design * eps_star * AT / (mdot * nar.G0), rel_tol=1e-6
        ))
        self.assertTrue(math.isclose(
            penalty, (pa_design - SEA_LEVEL) * eps_star * AT / (mdot * nar.G0),
            rel_tol=1e-6,
        ))

    def test_isp_throat_area_invariance(self):
        """Step 5 invariance: scaling the throat area by 2 leaves every Isp unchanged within 1e-9 relative (the isp is an area ratio property)."""
        eps_star = nar.design_altitude_area_ratio(P0, GAMMA, 20000.0)
        pa_design = nar.ambient_pressure_at_altitude(20000.0)
        isp_a = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, pa_design, AT)
        isp_b = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, pa_design, 2.0 * AT)
        isp_vac_a = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, 0.0, AT)
        isp_vac_b = nar.delivered_isp(eps_star, P0, T0, GAMMA, R_GAS, 0.0, 2.0 * AT)
        self.assertTrue(math.isclose(isp_a, isp_b, rel_tol=1e-9))
        self.assertTrue(math.isclose(isp_vac_a, isp_vac_b, rel_tol=1e-9))

    def test_delivered_isp_valueerror(self):
        """Step 5 guard: a negative ambient, non-positive gravity or chamber inputs raise ValueError (pa = 0 vacuum stays allowed)."""
        with self.assertRaises(ValueError):
            nar.delivered_isp(75.4961, P0, T0, GAMMA, R_GAS, -1.0, AT)
        with self.assertRaises(ValueError):
            nar.delivered_isp(75.4961, P0, T0, GAMMA, R_GAS, 5474.88, AT, g0=0.0)
        with self.assertRaises(ValueError):
            nar.delivered_isp(75.4961, 0.0, T0, GAMMA, R_GAS, 5474.88, AT)


class AttachedFlowGuardTests(unittest.TestCase):
    """Workflow step 6 of the SKILL.md body: the verdict-only attached-flow guard."""

    def test_guard_attached_at_design_ambient(self):
        """Step 6 verdict at the 20 km design ambient: eps* = 75.4961 is attached, Pe stays above 0.4 * 5474.88 = 2190.0 Pa."""
        self.assertTrue(nar.attached_flow_guard(75.4961, P0, GAMMA, 5474.88))

    def test_guard_separated_at_sea_level(self):
        """Step 6 verdict at sea level for the 20 km ratio: the same eps* = 75.4961 is False, Pe falls below 0.4 * 101325 = 40530.0 Pa."""
        self.assertFalse(nar.attached_flow_guard(75.4961, P0, GAMMA, SEA_LEVEL))

    def test_guard_attached_sea_level_matched(self):
        """Step 6 verdict at sea level for the booster ratio: eps* = 8.3061 stays attached at the sea-level ambient."""
        self.assertTrue(nar.attached_flow_guard(8.3061, P0, GAMMA, SEA_LEVEL))

    def test_guard_valueerror(self):
        """Step 6 guard: a non-positive ambient and a guard constant k_sep outside (0, 1) raise ValueError."""
        with self.assertRaises(ValueError):
            nar.attached_flow_guard(75.4961, P0, GAMMA, 0.0)
        with self.assertRaises(ValueError):
            nar.attached_flow_guard(75.4961, P0, GAMMA, SEA_LEVEL, k_sep=0.0)
        with self.assertRaises(ValueError):
            nar.attached_flow_guard(75.4961, P0, GAMMA, SEA_LEVEL, k_sep=1.0)


class ModuleSurfaceTests(unittest.TestCase):
    """Workflow step 7 checklist: determinism, repeatability and the public API surface."""

    def test_determinism_and_api_surface(self):
        """Step 7 checks: repeated calls are bit-identical, public results are floats or the guard bool, never over/under expansion strings."""
        first = nar.design_altitude_area_ratio(P0, GAMMA, 30000.0)
        self.assertEqual(first, nar.design_altitude_area_ratio(P0, GAMMA, 30000.0))
        eps = nar.design_altitude_area_ratio(P0, GAMMA, 20000.0)
        self.assertEqual(
            nar.delivered_isp(eps, P0, T0, GAMMA, R_GAS, 0.0, AT),
            nar.delivered_isp(eps, P0, T0, GAMMA, R_GAS, 0.0, AT),
        )
        self.assertIsInstance(nar.expansion_matched_area_ratio(P0, GAMMA, 5474.88), float)
        self.assertIsInstance(nar.ambient_pressure_at_altitude(20000.0), float)
        self.assertIsInstance(
            nar.delivered_isp(8.3061, P0, T0, GAMMA, R_GAS, SEA_LEVEL, AT), float
        )
        self.assertIsInstance(nar.attached_flow_guard(8.3061, P0, GAMMA, SEA_LEVEL), bool)
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "nozzle_area_ratio_selection_logic.py")
        source = open(logic_path).read()
        for forbidden in ("optimum_expansion", "overexpanded", "separation_station",
                          "separation_altitude", "side_load"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
