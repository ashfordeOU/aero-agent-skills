"""Contract test for the flat-plate-skin-friction-heating leaf logic.

Deterministic, offline, stdlib only. Covers the module constants, the
recovery factor, adiabatic wall temperature, Eckert reference
temperature, Sutherland viscosity, skin friction coefficient, heat
transfer coefficient and cold-wall heat flux, plus the worked-example
anchor bounds, identities, sign behavior and ValueError rejection of
non-physical inputs. Run with:

    python3 scripts/test_flat_plate_skin_friction_heating.py
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from flat_plate_skin_friction_heating_logic import (
    GAMMA,
    R,
    CP,
    PR,
    MU_REF,
    T_REF,
    SUTH_S,
    recovery_factor,
    adiabatic_wall_temperature,
    reference_temperature,
    sutherland_viscosity,
    skin_friction_coefficient,
    heat_transfer_coefficient,
    cold_wall_heat_flux,
)

# Worked example flight point (spec: M = 3.0 at 11 km-ish static state).
M_WORKED = 3.0
T_INF_WORKED = 223.0     # K
P_INF_WORKED = 10000.0   # Pa
T_WALL_WORKED = 500.0    # K
X_WORKED = 0.5           # m

# Real module outputs at the worked point (spec-prep verified bounds):
# turbulent r = 0.89211, T_aw = 581.09 K, T_star = 447.88 K, rho_star =
# 0.077795, mu_star = 2.4753e-5, Re_star = 1.4111e6, Cf = 0.003487,
# h_c = 122.40, q = 9925.7 W/m2; laminar r = 0.84261, T_aw = 561.23 K,
# Cf = 5.590e-4, q = 1201.4 W/m2.
R_LAM = 0.84261
R_TURB = 0.89211
T_AW_TURB = 581.09
T_AW_LAM = 561.23
T_STAR_WORKED = 447.88
RHO_STAR_WORKED = 0.077795
MU_STAR_WORKED = 2.4753e-5
RE_STAR_WORKED = 1.4111e6
CF_TURB = 0.003487
CF_LAM = 5.590e-4
H_C_TURB = 122.40
Q_TURB = 9925.7
Q_LAM = 1201.4

TOL = 0.01  # 1 percent on the spec anchor bounds


def assert_rel(testcase, actual, expected, tol=TOL):
    """Assert actual within tol (relative) of expected."""
    testcase.assertAlmostEqual(actual, expected, delta=abs(expected) * tol)


def worked_kwargs(regime):
    """Keyword inputs for the worked-example flight point."""
    return dict(M=M_WORKED, T_inf=T_INF_WORKED, p_inf=P_INF_WORKED,
                T_wall=T_WALL_WORKED, x=X_WORKED, regime=regime)


class TestModuleConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(GAMMA, 1.4)
        self.assertEqual(R, 287.0)
        self.assertEqual(CP, 1005.0)
        self.assertEqual(PR, 0.71)
        self.assertEqual(MU_REF, 1.716e-5)
        self.assertEqual(T_REF, 273.15)
        self.assertEqual(SUTH_S, 110.4)

    def test_sutherland_at_reference_temp_equals_mu_ref(self):
        assert_rel(self, sutherland_viscosity(T_REF), MU_REF, 1e-3)


class TestRecoveryFactor(unittest.TestCase):
    def test_recovery_factor_constants(self):
        assert_rel(self, recovery_factor("laminar"), R_LAM)
        assert_rel(self, recovery_factor("turbulent"), R_TURB)
        assert_rel(self, recovery_factor("laminar"), PR ** 0.5, 1e-9)
        assert_rel(self, recovery_factor("turbulent"), PR ** (1.0 / 3.0),
                   1e-9)

    def test_laminar_below_turbulent(self):
        self.assertLess(
            recovery_factor("laminar"), recovery_factor("turbulent"))

    def test_bad_regime_raises_value_error(self):
        for regime in ("transitional", "TURBULENT", "", None):
            with self.assertRaises(ValueError):
                recovery_factor(regime)


class TestAdiabaticWallTemperature(unittest.TestCase):
    def test_worked_turbulent_anchor(self):
        assert_rel(self, adiabatic_wall_temperature(
            M_WORKED, T_INF_WORKED, "turbulent"), T_AW_TURB)

    def test_worked_laminar_anchor(self):
        assert_rel(self, adiabatic_wall_temperature(
            M_WORKED, T_INF_WORKED, "laminar"), T_AW_LAM)

    def test_turbulent_adiabatic_wall_above_laminar(self):
        t_lam = adiabatic_wall_temperature(
            M_WORKED, T_INF_WORKED, "laminar")
        t_turb = adiabatic_wall_temperature(
            M_WORKED, T_INF_WORKED, "turbulent")
        self.assertGreater(t_turb, t_lam)

    def test_zero_mach_equals_static_temperature(self):
        for regime in ("laminar", "turbulent"):
            self.assertAlmostEqual(
                adiabatic_wall_temperature(0.0, T_INF_WORKED, regime),
                T_INF_WORKED, places=9)

    def test_mach_bounds_raise(self):
        for bad_m in (-0.5, 20.0, 30.0):
            with self.assertRaises(ValueError):
                adiabatic_wall_temperature(bad_m, T_INF_WORKED, "turbulent")

    def test_invalid_regime_or_static_temperature_raises(self):
        with self.assertRaises(ValueError):
            adiabatic_wall_temperature(M_WORKED, T_INF_WORKED, "mixed")
        for bad_t in (0.0, -100.0):
            with self.assertRaises(ValueError):
                adiabatic_wall_temperature(M_WORKED, bad_t, "turbulent")


class TestReferenceTemperature(unittest.TestCase):
    def test_worked_anchor(self):
        assert_rel(self, reference_temperature(
            M_WORKED, T_INF_WORKED, T_WALL_WORKED), T_STAR_WORKED)

    def test_heated_wall_lies_between_static_and_wall(self):
        t_star = reference_temperature(
            M_WORKED, T_INF_WORKED, T_WALL_WORKED)
        self.assertGreater(t_star, T_INF_WORKED)
        self.assertLess(t_star, T_WALL_WORKED)

    def test_cold_wall_gives_reference_below_static(self):
        t_star = reference_temperature(0.5, T_INF_WORKED, 100.0)
        self.assertLess(t_star, T_INF_WORKED)

    def test_near_zero_mach_matches_linear_term(self):
        expected = T_INF_WORKED + 0.58 * (T_WALL_WORKED - T_INF_WORKED)
        assert_rel(self,
                   reference_temperature(1e-6, T_INF_WORKED,
                                         T_WALL_WORKED),
                   expected, 1e-9)

    def test_nonphysical_inputs_raise(self):
        for args in ((M_WORKED, 0.0, 300.0),
                     (M_WORKED, 223.0, 0.0),
                     (M_WORKED, 223.0, -50.0),
                     (-1.0, 223.0, 300.0),
                     (25.0, 223.0, 300.0)):
            with self.assertRaises(ValueError):
                reference_temperature(*args)


class TestSutherlandViscosity(unittest.TestCase):
    def test_worked_star_viscosity_anchor(self):
        assert_rel(self, sutherland_viscosity(T_STAR_WORKED), MU_STAR_WORKED)

    def test_monotonic_increase_with_temperature(self):
        self.assertLess(sutherland_viscosity(200.0),
                        sutherland_viscosity(300.0))
        self.assertLess(sutherland_viscosity(300.0),
                        sutherland_viscosity(1000.0))

    def test_nonpositive_temperature_raises(self):
        for bad in (0.0, -10.0):
            with self.assertRaises(ValueError):
                sutherland_viscosity(bad)


class TestSkinFrictionCoefficient(unittest.TestCase):
    def test_worked_turbulent_anchors(self):
        res = skin_friction_coefficient(**worked_kwargs("turbulent"))
        self.assertEqual(
            sorted(res.keys()),
            ["Cf", "Re_star", "T_star", "mu_star", "rho_star"])
        assert_rel(self, res["T_star"], T_STAR_WORKED)
        assert_rel(self, res["rho_star"], RHO_STAR_WORKED)
        assert_rel(self, res["mu_star"], MU_STAR_WORKED)
        assert_rel(self, res["Re_star"], RE_STAR_WORKED)
        assert_rel(self, res["Cf"], CF_TURB)

    def test_worked_laminar_cf_anchor_and_blasius_form(self):
        res = skin_friction_coefficient(**worked_kwargs("laminar"))
        assert_rel(self, res["Re_star"], RE_STAR_WORKED)
        assert_rel(self, res["Cf"], CF_LAM)
        assert_rel(self, res["Cf"], 0.664 / res["Re_star"] ** 0.5, 1e-9)

    def test_turbulent_cf_exceeds_laminar_at_same_re(self):
        for x in (0.5, 1.0, 5.0):
            lam = skin_friction_coefficient(
                M_WORKED, T_INF_WORKED, P_INF_WORKED, T_WALL_WORKED,
                x, "laminar")
            turb = skin_friction_coefficient(
                M_WORKED, T_INF_WORKED, P_INF_WORKED, T_WALL_WORKED,
                x, "turbulent")
            self.assertEqual(lam["Re_star"], turb["Re_star"])
            self.assertGreater(turb["Cf"], lam["Cf"])

    def test_reynolds_number_proportional_to_length(self):
        res_half = skin_friction_coefficient(**worked_kwargs("turbulent"))
        res_double = skin_friction_coefficient(
            M_WORKED, T_INF_WORKED, P_INF_WORKED, T_WALL_WORKED,
            1.0, "turbulent")
        assert_rel(self, res_double["Re_star"],
                   2.0 * res_half["Re_star"], 1e-9)

    def test_nonphysical_inputs_raise(self):
        cases = [dict(M=0.0), dict(M=20.0), dict(T_inf=0.0),
                 dict(p_inf=-1.0), dict(T_wall=0.0), dict(x=-0.5),
                 dict(regime="transitional")]
        base = worked_kwargs("turbulent")
        for over in cases:
            kwargs = dict(base)
            kwargs.update(over)
            with self.assertRaises(ValueError):
                skin_friction_coefficient(**kwargs)


class TestHeatTransferCoefficient(unittest.TestCase):
    def test_worked_turbulent_anchor(self):
        sf = skin_friction_coefficient(**worked_kwargs("turbulent"))
        u_e = M_WORKED * (GAMMA * R * T_INF_WORKED) ** 0.5
        h_c = heat_transfer_coefficient(sf["Cf"], sf["rho_star"], u_e)
        assert_rel(self, h_c, H_C_TURB)
        assert_rel(self, h_c,
                   0.5 * sf["Cf"] * sf["rho_star"] * u_e * CP, 1e-9)

    def test_nonphysical_inputs_raise(self):
        with self.assertRaises(ValueError):
            heat_transfer_coefficient(0.0, 0.1, 300.0)
        with self.assertRaises(ValueError):
            heat_transfer_coefficient(0.003, 0.0, 300.0)
        with self.assertRaises(ValueError):
            heat_transfer_coefficient(0.003, 0.1, -300.0)


class TestColdWallHeatFlux(unittest.TestCase):
    def test_worked_turbulent_anchors(self):
        res = cold_wall_heat_flux(**worked_kwargs("turbulent"))
        self.assertEqual(
            sorted(res.keys()),
            ["Cf", "Re_star", "T_aw", "T_star", "h_c", "q_cold_wall", "r"])
        assert_rel(self, res["r"], R_TURB)
        assert_rel(self, res["T_aw"], T_AW_TURB)
        assert_rel(self, res["Re_star"], RE_STAR_WORKED)
        assert_rel(self, res["Cf"], CF_TURB)
        assert_rel(self, res["q_cold_wall"], Q_TURB)

    def test_worked_laminar_anchors(self):
        res = cold_wall_heat_flux(**worked_kwargs("laminar"))
        assert_rel(self, res["r"], R_LAM)
        assert_rel(self, res["T_aw"], T_AW_LAM)
        assert_rel(self, res["Cf"], CF_LAM)
        assert_rel(self, res["q_cold_wall"], Q_LAM)

    def test_flux_positive_for_cold_wall(self):
        res = cold_wall_heat_flux(
            M_WORKED, T_INF_WORKED, P_INF_WORKED, 300.0,
            X_WORKED, "turbulent")
        self.assertGreater(res["q_cold_wall"], 0.0)
        self.assertGreater(res["T_aw"], 300.0)

    def test_wall_heating_sign_flip(self):
        res_hot = cold_wall_heat_flux(
            M_WORKED, T_INF_WORKED, P_INF_WORKED, 1200.0,
            X_WORKED, "turbulent")
        self.assertLess(res_hot["q_cold_wall"], 0.0)

    def test_zero_flux_at_adiabatic_wall(self):
        t_aw = adiabatic_wall_temperature(
            M_WORKED, T_INF_WORKED, "turbulent")
        res = cold_wall_heat_flux(
            M_WORKED, T_INF_WORKED, P_INF_WORKED, t_aw,
            X_WORKED, "turbulent")
        assert_rel(self, res["q_cold_wall"], 0.0, 1e-6)

    def test_turbulent_flux_exceeds_laminar(self):
        q_turb = cold_wall_heat_flux(
            **worked_kwargs("turbulent"))["q_cold_wall"]
        q_lam = cold_wall_heat_flux(
            **worked_kwargs("laminar"))["q_cold_wall"]
        self.assertGreater(q_turb, 8.0 * q_lam)

    def test_nonphysical_inputs_raise(self):
        cases = [dict(M=-3.0), dict(M=20.0), dict(T_inf=0.0),
                 dict(p_inf=0.0), dict(T_wall=-500.0), dict(x=0.0),
                 dict(regime="rough")]
        base = worked_kwargs("laminar")
        for over in cases:
            kwargs = dict(base)
            kwargs.update(over)
            with self.assertRaises(ValueError):
                cold_wall_heat_flux(**kwargs)

    def test_determinism(self):
        first = cold_wall_heat_flux(**worked_kwargs("turbulent"))
        second = cold_wall_heat_flux(**worked_kwargs("turbulent"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
