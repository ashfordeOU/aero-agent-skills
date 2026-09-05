"""Contract test for the environmental-disturbance-torque-budget leaf.

Exercises every step of the SKILL.md workflow: step 1, the orbit-fix
traverse (mean motion, circular velocity, orbit period); step 2, the
gravity-gradient traverse; step 3, the solar-pressure traverse with the
reflectivity convention; step 4, the residual-dipole traverse; step 5,
the aero-drag traverse at the explicit density input; step 6, the
budget-rollup traverse (per-source torques, aligned-axis worst-case
total, dominant source, per-orbit disturbance impulse); step 7, the
actuator-margin traverse (torque margin and disturbance impulse); step 8,
the contract confirmation. Fact terms: mean motion, circular velocity,
orbit period, gravity-gradient torque, solar pressure torque, residual
magnetic dipole, aero drag torque, per-orbit disturbance impulse,
torque margin, worst-case total, dominant source. Procedure terms:
traverse, budget rollup, actuator margin check, ValueError rejection.
Run offline: python3 test_environmental_disturbance_torque_budget.py
"""

import math
import unittest

from environmental_disturbance_torque_budget_logic import (
    EARTH_MU,
    EARTH_RADIUS_M,
    SOLAR_PRESSURE_PA,
    THETA_WORST_DEG,
    aero_drag_torque,
    disturbance_impulse,
    gravity_gradient_torque,
    magnetic_residual_torque,
    orbit_period_s,
    orbital_mean_motion,
    orbital_velocity,
    solar_pressure_torque,
    torque_margin,
    worst_case_budget,
)

# Worked-example orbit: 400 km LEO radius = Earth radius + 400 km.
R_400KM = 6.778e6
# Per-source magnitudes of the worked example budget.
BUDGET_TOTAL = 1.876372e-4


class EnvironmentalDisturbanceTorqueBudgetTest(unittest.TestCase):

    def test_mean_motion_400km_anchor(self):
        """Step 1 of the SKILL.md workflow, the orbit-fix traverse, gives
        mean motion n = 1.131401e-3 rad/s at the 400 km worked example."""
        n = orbital_mean_motion(R_400KM)
        self.assertAlmostEqual(n, 1.131401e-3, delta=1e-9)

    def test_orbital_velocity_400km_anchor(self):
        """Step 1 of the SKILL.md workflow, the orbit-fix traverse, gives
        circular velocity v = 7668.635675 m/s at 400 km for the aero drag
        term."""
        v = orbital_velocity(R_400KM)
        self.assertAlmostEqual(v, 7668.635675, delta=1e-3)

    def test_orbit_period_400km_anchor(self):
        """Step 1 of the SKILL.md workflow, the orbit-fix traverse, gives
        orbit period 5553.455897 s (92.56 min) as the per-orbit horizon
        for the disturbance impulse."""
        period = orbit_period_s(R_400KM)
        self.assertAlmostEqual(period, 5553.455897, delta=1e-3)

    def test_circular_orbit_identities_hold(self):
        """Step 1 of the SKILL.md workflow: the circular-orbit closed forms
        agree, period = 2 * pi / n and v = n * radius."""
        n = orbital_mean_motion(R_400KM)
        v = orbital_velocity(R_400KM)
        period = orbit_period_s(R_400KM)
        self.assertAlmostEqual(period, 2.0 * math.pi / n, places=12)
        self.assertAlmostEqual(v, n * R_400KM, places=9)

    def test_orbit_functions_reject_at_or_below_earth_surface(self):
        """Step 1 of the SKILL.md workflow: every orbit-fix function raises
        ValueError at a radius exactly at EARTH_RADIUS_M and below."""
        for bad_radius in (EARTH_RADIUS_M, EARTH_RADIUS_M - 1.0, 1000.0):
            with self.assertRaises(ValueError):
                orbital_mean_motion(bad_radius)
            with self.assertRaises(ValueError):
                orbital_velocity(bad_radius)
            with self.assertRaises(ValueError):
                orbit_period_s(bad_radius)

    def test_gravity_gradient_45deg_anchor(self):
        """Step 2 of the SKILL.md workflow, the gravity-gradient traverse,
        gives 7.680409e-5 N m at the worst-case 45 degree offset of the
        400 km worked example."""
        n = orbital_mean_motion(R_400KM)
        torque = gravity_gradient_torque(n, 60.0, 20.0, 45.0)
        self.assertAlmostEqual(torque, 7.680409e-5, delta=1e-9)

    def test_gravity_gradient_exactly_zero_at_zero_degrees(self):
        """Step 2 of the SKILL.md workflow: the gravity-gradient magnitude
        is exactly 0.0 at a zero attitude offset."""
        n = orbital_mean_motion(R_400KM)
        self.assertEqual(gravity_gradient_torque(n, 60.0, 20.0, 0.0), 0.0)

    def test_gravity_gradient_below_1e15_at_90_degrees(self):
        """Step 2 of the SKILL.md workflow: the gravity-gradient magnitude
        vanishes at +-90 degrees, with only the floating-point sin of pi
        residue (9.4e-21 N m at the worked example)."""
        n = orbital_mean_motion(R_400KM)
        torque = gravity_gradient_torque(n, 60.0, 20.0, 90.0)
        self.assertGreater(torque, 0.0)
        self.assertLess(torque, 1e-15)

    def test_gravity_gradient_sign_free_at_minus_45_degrees(self):
        """Step 2 of the SKILL.md workflow: the absolute-value form makes
        the magnitude equal at theta -45 and +45 degrees."""
        n = orbital_mean_motion(R_400KM)
        self.assertEqual(gravity_gradient_torque(n, 60.0, 20.0, -45.0),
                         gravity_gradient_torque(n, 60.0, 20.0, 45.0))

    def test_gravity_gradient_doubling_spread_doubles_torque(self):
        """Step 2 of the SKILL.md workflow: doubling the inertia spread
        |I_zz - I_yy| from 20 to 40 doubles the gravity-gradient torque."""
        n = orbital_mean_motion(R_400KM)
        base = gravity_gradient_torque(n, 60.0, 40.0, 45.0)
        doubled = gravity_gradient_torque(n, 60.0, 20.0, 45.0)
        self.assertAlmostEqual(doubled, 2.0 * base, places=12)

    def test_gravity_gradient_500km_reproduces_sibling_anchor(self):
        """Step 2 of the SKILL.md workflow: the same closed form reproduces
        the gravity-gradient-stabilization restoring-torque anchor
        3.675e-5 N m at its 500 km, spread-20 example."""
        n = orbital_mean_motion(6.878e6)
        torque = gravity_gradient_torque(n, 60.0, 40.0, 45.0)
        self.assertAlmostEqual(torque, 3.675e-5, delta=1e-7)

    def test_gravity_gradient_value_errors(self):
        """Step 2 of the SKILL.md workflow: gravity_gradient_torque raises
        ValueError for non-positive mean motion, zero inertia or an offset
        magnitude above 90 degrees."""
        with self.assertRaises(ValueError):
            gravity_gradient_torque(0.0, 60.0, 20.0, 45.0)
        with self.assertRaises(ValueError):
            gravity_gradient_torque(1.131401e-3, 0.0, 20.0, 45.0)
        with self.assertRaises(ValueError):
            gravity_gradient_torque(1.131401e-3, 60.0, 0.0, 45.0)
        for bad_theta in (90.1, -90.1, 180.0):
            with self.assertRaises(ValueError):
                gravity_gradient_torque(1.131401e-3, 60.0, 20.0, bad_theta)

    def test_solar_pressure_fully_reflective_anchor(self):
        """Step 3 of the SKILL.md workflow, the solar-pressure traverse,
        gives 1.08e-5 N m for a 2 m2 sun-normal area at lever 0.6 m with
        the worst-case reflectivity 1.0."""
        torque = solar_pressure_torque(2.0, 1.0, 0.6, 1.0)
        self.assertAlmostEqual(torque, 1.08e-5, delta=1e-10)

    def test_solar_pressure_absorbing_surface_is_exactly_half(self):
        """Step 3 of the SKILL.md workflow: the reflectivity convention
        makes the absorbing surface (r = 0) torque exactly half of the
        fully specular (r = 1) value."""
        specular = solar_pressure_torque(2.0, 1.0, 0.6, 1.0)
        absorbing = solar_pressure_torque(2.0, 1.0, 0.6, 0.0)
        self.assertAlmostEqual(absorbing, 5.4e-6, delta=1e-12)
        self.assertEqual(absorbing, 0.5 * specular)

    def test_solar_pressure_linear_in_cosine_and_area(self):
        """Step 3 of the SKILL.md workflow: the solar torque is linear in
        cos_incidence (0.5 halves, 0 zeroes the torque) and in the sunlit
        area."""
        half = solar_pressure_torque(2.0, 0.5, 0.6, 1.0)
        full = solar_pressure_torque(2.0, 1.0, 0.6, 1.0)
        self.assertEqual(half, 0.5 * full)
        self.assertEqual(solar_pressure_torque(2.0, 0.0, 0.6, 1.0), 0.0)
        doubled_area = solar_pressure_torque(4.0, 1.0, 0.6, 1.0)
        self.assertEqual(doubled_area, 2.0 * full)

    def test_solar_pressure_value_errors(self):
        """Step 3 of the SKILL.md workflow: solar_pressure_torque raises
        ValueError for non-positive area or lever, cos_incidence outside
        [0, 1] and reflectivity outside [0, 1]."""
        with self.assertRaises(ValueError):
            solar_pressure_torque(0.0, 1.0, 0.6, 1.0)
        with self.assertRaises(ValueError):
            solar_pressure_torque(2.0, -0.1, 0.6, 1.0)
        with self.assertRaises(ValueError):
            solar_pressure_torque(2.0, 1.1, 0.6, 1.0)
        with self.assertRaises(ValueError):
            solar_pressure_torque(2.0, 1.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            solar_pressure_torque(2.0, 1.0, 0.6, -0.1)
        with self.assertRaises(ValueError):
            solar_pressure_torque(2.0, 1.0, 0.6, 1.2)

    def test_magnetic_residual_anchor(self):
        """Step 4 of the SKILL.md workflow, the residual-dipole traverse,
        gives 3.0e-6 N m for a 0.1 A m2 dipole against B = 3.0e-5 T at the
        worst-case orthogonal geometry."""
        torque = magnetic_residual_torque(0.1, 3.0e-5)
        self.assertAlmostEqual(torque, 3.0e-6, delta=1e-10)

    def test_magnetic_residual_zero_dipole_and_linearity(self):
        """Step 4 of the SKILL.md workflow: a zero residual dipole returns
        0.0 and doubling the dipole doubles the magnetic torque."""
        self.assertEqual(magnetic_residual_torque(0.0, 3.0e-5), 0.0)
        doubled = magnetic_residual_torque(0.2, 3.0e-5)
        self.assertEqual(doubled, 2.0 * magnetic_residual_torque(0.1, 3.0e-5))

    def test_magnetic_residual_value_errors(self):
        """Step 4 of the SKILL.md workflow: magnetic_residual_torque raises
        ValueError for a negative dipole or a non-positive field."""
        with self.assertRaises(ValueError):
            magnetic_residual_torque(-0.1, 3.0e-5)
        with self.assertRaises(ValueError):
            magnetic_residual_torque(0.1, 0.0)

    def test_aero_drag_anchor(self):
        """Step 5 of the SKILL.md workflow, the aero-drag traverse at the
        explicit density input, gives 9.703316e-5 N m for rho = 3.0e-12
        kg/m3, Cd = 2.2, area 1.0 m2 and lever 0.5 m at the 400 km
        circular velocity."""
        v = orbital_velocity(R_400KM)
        torque = aero_drag_torque(3.0e-12, v, 2.2, 1.0, 0.5)
        self.assertAlmostEqual(torque, 9.703316e-5, delta=1e-9)

    def test_aero_drag_velocity_squared_scaling(self):
        """Step 5 of the SKILL.md workflow: the free-molecular drag torque
        scales with velocity squared, so doubling v quadruples the
        torque."""
        v = orbital_velocity(R_400KM)
        base = aero_drag_torque(3.0e-12, v, 2.2, 1.0, 0.5)
        doubled_v = aero_drag_torque(3.0e-12, 2.0 * v, 2.2, 1.0, 0.5)
        self.assertAlmostEqual(doubled_v, 4.0 * base, places=12)

    def test_aero_drag_value_errors(self):
        """Step 5 of the SKILL.md workflow: aero_drag_torque raises
        ValueError for a zero density and for any non-positive input."""
        with self.assertRaises(ValueError):
            aero_drag_torque(0.0, 7668.635675, 2.2, 1.0, 0.5)
        with self.assertRaises(ValueError):
            aero_drag_torque(3.0e-12, 0.0, 2.2, 1.0, 0.5)
        with self.assertRaises(ValueError):
            aero_drag_torque(3.0e-12, 7668.635675, 0.0, 1.0, 0.5)
        with self.assertRaises(ValueError):
            aero_drag_torque(3.0e-12, 7668.635675, 2.2, 0.0, 0.5)
        with self.assertRaises(ValueError):
            aero_drag_torque(3.0e-12, 7668.635675, 2.2, 1.0, 0.0)

    def test_budget_worked_example_rollup(self):
        """Step 6 of the SKILL.md workflow, the budget-rollup traverse:
        the 400 km worked example rolls up to total 1.876372e-4 N m with
        aero_drag dominant and a per-orbit impulse of 1.042035 N m s."""
        budget = worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5)
        self.assertAlmostEqual(budget["gravity_gradient"], 7.680409e-5,
                               delta=1e-9)
        self.assertAlmostEqual(budget["solar_pressure"], 1.08e-5,
                               delta=1e-10)
        self.assertAlmostEqual(budget["magnetic_residual"], 3.0e-6,
                               delta=1e-10)
        self.assertAlmostEqual(budget["aero_drag"], 9.703316e-5, delta=1e-9)
        self.assertAlmostEqual(budget["total_worst_case"], BUDGET_TOTAL,
                               delta=1e-8)
        self.assertEqual(budget["dominant_source"], "aero_drag")
        self.assertAlmostEqual(budget["disturbance_impulse_per_orbit"],
                               1.042035, delta=1e-6)

    def test_budget_total_is_exact_sum_of_per_source_keys(self):
        """Step 6 of the SKILL.md workflow: the aligned-axis worst-case
        total equals the sum of the four per-source magnitudes."""
        budget = worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5)
        summed = (budget["gravity_gradient"] + budget["solar_pressure"]
                  + budget["magnetic_residual"] + budget["aero_drag"])
        self.assertAlmostEqual(budget["total_worst_case"], summed,
                               places=15)

    def test_budget_dict_keys_are_the_ten_documented_keys(self):
        """Step 6 of the SKILL.md workflow: the budget dict carries exactly
        the ten documented keys, no more and no fewer."""
        budget = worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5)
        self.assertEqual(
            list(budget.keys()),
            ["mean_motion_rad_s", "orbital_velocity_m_s", "orbit_period_s",
             "gravity_gradient", "solar_pressure", "magnetic_residual",
             "aero_drag", "total_worst_case", "dominant_source",
             "disturbance_impulse_per_orbit"])

    def test_budget_impulse_equals_total_times_period(self):
        """Step 6 of the SKILL.md workflow: the per-orbit disturbance
        impulse equals the worst-case total times the orbit period."""
        budget = worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5)
        expected = (budget["total_worst_case"] * budget["orbit_period_s"])
        self.assertAlmostEqual(budget["disturbance_impulse_per_orbit"],
                               expected, places=12)

    def test_budget_defaults_theta_worst_and_fully_reflective(self):
        """Step 6 of the SKILL.md workflow: the theta_deg default is the
        worst-case 45.0 degrees and the reflectivity default is the
        worst-case 1.0, so an explicit call with both reproduces the
        default call."""
        base = worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5)
        explicit = worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5, theta_deg=THETA_WORST_DEG, reflectivity=1.0)
        self.assertEqual(base, explicit)

    def test_budget_deterministic_across_calls(self):
        """Step 6 of the SKILL.md workflow: repeated budget-rollup calls
        return identical dicts, and a budget at or below the Earth radius
        raises ValueError."""
        call = lambda: worst_case_budget(
            R_400KM, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5, 3.0e-12,
            2.2, 1.0, 0.5)
        self.assertEqual(call(), call())
        with self.assertRaises(ValueError):
            worst_case_budget(
                EARTH_RADIUS_M, 60.0, 20.0, 2.0, 1.0, 0.6, 0.1, 3.0e-5,
                3.0e-12, 2.2, 1.0, 0.5)

    def test_disturbance_impulse_anchor(self):
        """Step 7 of the SKILL.md workflow, the actuator-margin traverse:
        disturbance_impulse(1.876372e-4, 5553.455897) returns
        1.042035 N m s, the wheel momentum the cluster must absorb each
        orbit and the desaturation demand."""
        impulse = disturbance_impulse(1.876372e-4, 5553.455897)
        self.assertAlmostEqual(impulse, 1.042035, delta=1e-6)

    def test_disturbance_impulse_zero_torque_and_value_errors(self):
        """Step 7 of the SKILL.md workflow: a zero disturbance torque gives
        a zero impulse, while negative torque or non-positive period raise
        ValueError."""
        self.assertEqual(disturbance_impulse(0.0, 5553.455897), 0.0)
        with self.assertRaises(ValueError):
            disturbance_impulse(-1.0e-6, 5553.455897)
        with self.assertRaises(ValueError):
            disturbance_impulse(1.876372e-4, 0.0)

    def test_torque_margin_wheel_anchor(self):
        """Step 7 of the SKILL.md workflow: a 0.2 N m reaction wheel torque
        capability against the worked-example worst-case total gives a
        torque margin of 1065.886."""
        margin = torque_margin(0.2, BUDGET_TOTAL)
        self.assertAlmostEqual(margin, 1065.886, delta=1e-3)

    def test_torque_margin_magnetorquer_anchor(self):
        """Step 7 of the SKILL.md workflow: a 30 A m2 magnetorquer dipole
        in B = 3.0e-5 T achieves 9.0e-4 N m and a torque margin of 4.796
        against the worked-example worst-case total."""
        achievable = 30.0 * 3.0e-5
        self.assertAlmostEqual(achievable, 9.0e-4, places=15)
        margin = torque_margin(achievable, BUDGET_TOTAL)
        self.assertAlmostEqual(margin, 4.796, delta=1e-3)

    def test_torque_margin_exactly_one_when_capability_equals(self):
        """Step 7 of the SKILL.md workflow: torque_margin returns exactly
        1.0 when the available torque equals the disturbance torque, and
        raises ValueError for non-positive capability or disturbance."""
        self.assertEqual(torque_margin(1.876372e-4, 1.876372e-4), 1.0)
        with self.assertRaises(ValueError):
            torque_margin(0.0, BUDGET_TOTAL)
        with self.assertRaises(ValueError):
            torque_margin(0.2, 0.0)

    def test_module_constants_match_documented_values(self):
        """Step 8 of the SKILL.md workflow, the contract confirmation:
        the module constants are the documented solar pressure, Earth
        parameter, Earth radius and worst-case theta values."""
        self.assertEqual(SOLAR_PRESSURE_PA, 4.5e-6)
        self.assertEqual(EARTH_MU, 3.986004418e14)
        self.assertEqual(EARTH_RADIUS_M, 6378.0e3)
        self.assertEqual(THETA_WORST_DEG, 45.0)


if __name__ == "__main__":
    unittest.main()
